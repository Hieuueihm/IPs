"""Executable locked-design resource model, not an RTL or cryptographic proof.

Uses the pinned planner's geometry primitives, independently rebuilds times,
reserves physical resources, replays memory versions and storage ownership.
Only writes a new run directory under study/build/flextransform_rebuild.
"""
import argparse
import copy
from collections import defaultdict,Counter,deque
from bisect import bisect_right
from functools import lru_cache
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import re
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parents[2]
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('readonly_geometry',ROOT/'experiments/a_cg_packed4/planner.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
TIM=json.loads((HERE/'microarchitecture/timing.json').read_text())
FSM=json.loads((HERE/'microarchitecture/fsm.json').read_text())

def profile(fmt,inv,native):return TIM['fft'][f'fft{32*(1<<fmt)}_{"gs" if inv else "ct"}'+('_native' if native else '')]

@lru_cache(maxsize=1)
def topology(fft,fmt,ln,hm,inv,pk,jl):
    c=G.config(fft,fmt,ln,hm,pk,jl);n,m=c['n'],c['m'];L=1<<fmt
    labels=list(range(m));layers=[]
    for s in range(c['stages']):
        ip=bool(pk and hm==0 and (s==0 if inv else s==c['stages']-1))
        ws=s-int(pk and hm==0 and inv);f=n-1-ws if inv else ws
        src,dst=(n,n) if ip else (f+1,f) if inv else (f,f+1)
        pairs=defaultdict(list)
        for jb in range(1<<c['bj']):
            for i in range(max(1,m//2)):
                if ip:
                    rp=(2*i,2*i+1 if m>1 else None);wp=rp
                    t=G.bank(rp[0],jb,n,n,c['bj'])>>1 if n<6 else i&15
                    roots=(m+rp[0],m+rp[1] if rp[1] is not None else 0)
                else:
                    far,near=(i,i+m//2),(2*i,2*i+1);rp,wp=(near,far) if inv else (far,near)
                    t=G.bank(i,jb,n,f,c['bj'])&15
                    x,y=(labels[p] for p in rp);h=(1<<ws) if inv else m>>(ws+1)
                    assert y==x+h and (x//h)%2==0
                    roots=((m//h if fft else m//(2*h))+x//(2*h),)
                pairs[t].append((i,jb,rp,wp,roots))
        ev=[]
        for t,ps in sorted(pairs.items()):
            seq=0
            for k,(i,jb,rp,wp,roots) in enumerate(ps):
                for part in range((1<<c['rj']) if fft else c['planes']):
                    jr=part if fft else part>>c['base_log'];bp=0 if fft else part&(c['base']-1)
                    rd=[];wr=[]
                    for j in range(c['base'] if fft else 1):
                        bpl=(j%2)*L+j//2 if fft else bp;opl=j if fft else bp
                        for port,p in enumerate(rp):
                            if p is not None:rd.append((G.addr(c,s&1,p,jb,jr,bpl,src),j if fft else 0,(s-1,(jr<<c['bj'])|jb,p,bpl)))
                        for port,p in enumerate(wp):
                            if p is not None:wr.append((G.addr(c,1-(s&1),p,jb,jr,opl,dst),j if fft else 0,(s,(jr<<c['bj'])|jb,p,opl)))
                    tag=(k<<3)|(jr*c['base'] if fft else part)
                    ev.append(dict(t=t,seq=seq,k=k,part=part,tag=tag,rd=rd,wr=wr,roots=roots,ip=ip,rp=rp,wp=wp,jb=jb,jr=jr,src=src,dst=dst));seq+=1
        if not ip:
            out=[None]*m
            for ps in pairs.values():
                for i,jb,rp,wp,roots in ps:
                    for p,lab in zip(wp,(labels[p] for p in rp)):out[p]=lab
            assert None not in out;labels=out
        layers.append(ev)
    assert labels==list(range(m))
    return c,layers

def host_words(c,fft,fmt,ln,inv,pk,is_read):
    W=1<<c['job_word_log'];M=c['m'];stage=0 if (bool(inv)==bool(is_read)) else c['n']
    buf=(c['stages']&1) if is_read else 0;out=[]
    for job in range(c['jobs']):
        jb=job&((1<<c['bj'])-1);jr=job>>c['bj']
        for w in range(W):
            if fft:
                coeff=w>>fmt;p=coeff%M;bpl=(coeff//M)*(1<<fmt)+(w&((1<<fmt)-1))
            else:p=w//c['base'];bpl=w%c['base']
            out.append((G.addr(c,buf,p,jb,jr,bpl,stage),(c['stages']-1 if is_read else -1,job,p,bpl)))
    return out

def host_gather_trial(words,mutant=False):
    # Independent line oracle versus a one-cycle synchronous bank read/gather.
    phases=[]
    for j,(addr,value) in enumerate(words):
        for phase in phases:
            if all(old_addr[0]!=addr[0] for _,old_addr,_ in phase):break
        else:phase=[];phases.append(phase)
        phase.append((j,addr,value))
    bank_q={};line=[None]*len(words);prev=[]
    for edge in range(len(phases)+1):
        if not mutant or edge==len(phases):
            for j,addr,value in prev:line[j]=bank_q[addr[0]]
        current=phases[edge] if edge<len(phases) else []
        for j,addr,value in current:bank_q[addr[0]]=value
        prev=current
    assert line==[value for addr,value in words],('host gather lost earlier phase',words,line)
    return len(phases)

class Reservations:
    def __init__(self):self.rd=defaultdict(set);self.wr=defaultdict(set);self.rt={};self.wt={};self.last={}
    def take(self,ev,start,P,fft,pk):
        for e in ev:
            for name,latest in [('rd',self.rt),('wr',self.wt)]:
                for addr,off,version in e[name]:
                    edge=start+off;used=getattr(self,name)[addr[0]]
                    assert edge not in used,('bank collision',name,edge,addr)
                    used.add(edge);latest[addr]=max(latest.get(addr,-1),edge)
            self.last[e['t']]=max(self.last.get(e['t'],-1),start+e['a']+(P-1 if fft else 0))
    def earliest(self,ev,lower,P,fft,pk):
        for e in ev:
            lower=max(lower,self.last.get(e['t'],-100000)-e['a']+1)
            for addr,off,_ in e['rd']:lower=max(lower,self.wt.get(addr,-100000)-off+1)
            for addr,off,_ in e['wr']:lower=max(lower,self.rt.get(addr,-100000)-off+1,self.wt.get(addr,-100000)-off+1)
        # First acceptance = start+2, phase0. FFT has no period3 gate.
        modulus=1 if fft else 3;residue=0 if fft else 1
        start=lower+(residue-lower)%modulus
        while any(start+off in getattr(self,name)[addr[0]] for e in ev for name in ('rd','wr') for addr,off,_ in e[name]):start+=modulus
        return start

def schedule(fft,fmt,ln,hm,inv,pk,jl,native=0,overlap=True):
    c,layers=topology(fft,fmt,ln,hm,inv,pk,jl);pr=profile(fmt,inv,native) if fft else None
    P=pr['period'] if fft else 3;book=Reservations();scheduled=[];starts=[];root_base=0
    lastread=lastwrite=-1
    for s,layer in enumerate(layers):
        ev=[];rootseq={}
        for x in layer:
            a=2+(P*x['seq'] if fft else 3*(x['seq']//2)+x['seq']%2 if pk else 3*x['seq'])
            e=dict(x,a=a,stage=s)
            e['rd']=[(addr,a-2+j,version) for addr,j,version in x['rd']]
            e['wr']=[(addr,a+(pr['outputs'][j]['commit'] if fft else TIM['ntt']['commit_gs' if inv else 'commit_ct']),version) for addr,j,version in x['wr']]
            ev.append(e);rootseq[x['t'],x['k']]=x['roots']
        period=1
        while any(v!=rootseq[t,k%period] for (t,k),v in rootseq.items()):period*=2
        assert period<=32
        root_words=period*(c['base'] if fft else 1);assert root_base+root_words<=512
        lo=max(TIM['start']['first_read_min'],lastread+1 if overlap else lastwrite+1)
        # Relative read offset starts at0. Retain monotone stage write order.
        lo=max(lo,lastwrite+1-min(t for e in ev for _,t,_ in e['wr']))
        start=book.earliest(ev,lo,P,fft,pk);book.take(ev,start,P,fft,pk)
        mask=sum(1<<t for t in {e['t'] for e in ev})
        assert mask and start>=1
        tails={}
        for e in ev:
            e['accept']=start+e['a'];e['read_first']=e['accept']-2
            e['rd']=[(addr,start+cy,ver) for addr,cy,ver in e['rd']]
            e['wr']=[(addr,start+cy,ver) for addr,cy,ver in e['wr']]
            e['root_base']=root_base;e['root_period']=period
            e['tag_last']=e['tag']+(2*(1<<fmt)-1 if fft else 0)
            tails[e['t']]=e['tag_last']
        assert len(set(tails.values()))==1,('nonuniform terminal tag',s,tails)
        lastread=max(cy for e in ev for _,cy,_ in e['rd'])
        lastwrite=max(cy for e in ev for _,cy,_ in e['wr'])
        if starts:assert 0<start-starts[-1]<=65535
        assert lastwrite<(1<<20)
        scheduled.append(dict(stage=s,start=start,push=TIM['start']['context0_push'] if s==0 else start-1,mask=mask,owner=(mask&-mask).bit_length()-1,tail_tag=next(iter(tails.values())),tail=lastwrite,events=ev,root_base=root_base,root_words=root_words))
        starts.append(start);root_base+=root_words
    return dict(config=dict(fft=fft,fmt=fmt,logn=ln,hmin=hm,inverse=inv,packed=pk,jobs_log=jl,native=native),c=c,layers=scheduled,starts=starts,
        cycles=lastwrite+1-TIM['start']['start_relative_phase_origin'] if layers else 0,root_words=root_base,profile=pr)

def check_case(plan,mutant=None):
    cfg=plan['config'];fft=cfg['fft'];inv=cfg['inverse'];pk=cfg['packed'];pr=plan['profile'];c=plan['c']
    tl=defaultdict(list);resources={};mem={};rports={};wports={};host_max=0;root_addresses={};read_rows={};write_rows={}
    for read in (False,True):
        words=host_words(c,fft,cfg['fmt'],cfg['logn'],inv,pk,read)
        assert len({a for a,v in words})==len(words),'host alias'
        for line in range(0,len(words),4):
            counts=Counter(a[0] for a,v in words[line:line+4]);host_max=max(host_max,max(counts.values()))
            assert host_gather_trial(words[line:line+4])==max(counts.values())
        if not read:mem.update(words)
    assert host_max<=4
    def put(t,kind,data):tl[t].append((kind,data))
    def use(t,tile,unit,owner):
        key=t,tile,unit;assert key not in resources,('resource collision',key,resources.get(key),owner)
        resources[key]=owner
    ident=0;returns={};group_changes=defaultdict(list)
    for layer in plan['layers']:
        put(layer['push'],'ctx_push',layer)
        for e in layer['events']:
            e=dict(e,id=ident);ident+=1;A=e['accept'];t=e['t'];ID=e['id']
            near=bool(inv or e['ip']);swap=((e['k']>>(c['n']-6))&1) if c['n']>=6 else 0
            # Validate the actual fixed four-source network, not an assumed crossbar.
            for port,p in enumerate(e['rp']):
                if p is None:continue
                bank=G.addr(c,e['stage']&1,p,e['jb'],e['jr'],0,e['src'])[0]
                wanted=((2*t+port)^(16 if swap else 0)) if near else (t+(16 if (e['k']&1)^port else 0))
                assert bank==wanted,('read four-source routing',cfg,e['stage'],t,port,bank,wanted)
            for port,p in enumerate(e['wp']):
                if p is None:continue
                bank=G.addr(c,1-(e['stage']&1),p,e['jb'],e['jr'],0,e['dst'])[0]
                wanted=(t+(16 if (e['k']&1)^port else 0)) if inv and not e['ip'] else 2*(t^(8 if swap else 0))+port
                assert bank==wanted,('write fixed routing',cfg,e['stage'],t,port,bank,wanted)
            if not fft:assert A%3 in ((0,1) if pk else (0,)),('phase',A)
            put(A,'alloc',e)
            for j in range(2*(1<<cfg['fmt']) if fft else 1):
                edge=e['read_first']+j;use(edge,t,'root_read',ID)
                plane=(j%2)*(1<<cfg['fmt'])+j//2 if fft else 0
                addr=e['root_base']+(e['k']&(e['root_period']-1))*(2*(1<<cfg['fmt']) if fft else 1)+plane
                assert 0<=addr<512
                assert root_addresses.setdefault(edge,addr)==addr,('root addresses not shared',edge,addr)
            for addr,cy,version in e['rd']:
                assert (cy,addr[0]) not in rports,('read port',cy,addr)
                rports[cy,addr[0]]=addr;put(cy,'read',(addr,version))
                assert read_rows.setdefault((cy,addr[0]>>4),addr[1])==addr[1],('read row needs extra mux',cy,addr)
            for addr,cy,version in e['wr']:
                assert (cy,addr[0]) not in wports,('write port',cy,addr)
                wports[cy,addr[0]]=addr;put(cy,'write',(addr,version))
                assert write_rows.setdefault((cy,addr[0]>>4),addr[1])==addr[1],('write row needs extra mux',cy,addr)
            if fft:
                for j,cy in enumerate(pr['operand_write_edges']):put(A+cy,'buf_write',(e,j))
                for j,cy in enumerate(pr['sum_write_edges']):use(A+cy,t,'C2_C3',ID);put(A+cy,'sum_write',(e,j))
                if inv:
                    for j in range(2*pr['L']):use(A+j+1,t,'C0_C1',ID)
                for step in pr['steps']:
                    put(A+step['launch'],'operand_fetch',(e,step))
                    for leaf in range(4):use(A+step['launch'],t,('leaf',leaf),ID)
                    use(A+step['mac'],t,'MAC68',ID)
                    if step['emit']:
                        put(A+step['combine'],'psum',(e,step))
                        if step['product']>0:
                            use(A+step['combine'],t,'C5',ID)
                            if step['product']==1:use(A+step['combine'],t,'C4',ID)
                            put(A+step['combine'],'buf_read',(e,step))
                put(A+pr['release_edge'],'free',e)
                for out in pr['outputs']:
                    if not inv:use(A+out['rsp']-1,t,'C0_C1',ID)
                    use(A+out['rsp'],t,'rsp',ID)
                    tag=e['tag']+(pr['L'] if out['product']==2 else 0)+out['limb']
                    put(A+out['commit'],'commit',(e,tag,out==pr['outputs'][-1]))
                put(A+pr['outputs'][-1]['rsp'],'retire',e)
            else:
                g=A%3 if pk else 0
                if mutant=='group0':g=0
                group_changes[t].append((A+2,g))
                for off in TIM['ntt']['launches']:
                    for leaf in ([2*g,2*g+1] if pk else range(4)):use(A+off,t,('leaf',leaf),ID)
                    key=(A+off+5,t,g);assert key not in returns
                    returns[key]=(ID,off)
                use(A+(1 if inv else 20),t,'C0_C1',ID)
                use(A+(2 if inv else 21),t,'C2_C3',ID)
                use(A+19,t,'C4',ID)
                put(A+2,'side_write',e);put(A+19,'side_read',e)
                put(A+8,'history_write',e);put(A+18,'history_read',e)
                put(A+19,'free',e)
                rsp=20 if inv else 21;use(A+rsp,t,'rsp',ID)
                put(A+rsp,'retire',e);put(A+rsp+1,'commit',(e,e['tag'],True))
    for key,addr in rports.items():assert wports.get(key)!=addr,('same-edge RAW',key,addr)
    live=[{} for _ in range(16)];ram=[{} for _ in range(16)];sideptr=[0]*16;outstanding=[set() for _ in range(16)]
    psum=[{} for _ in range(16)];history=[deque([None]*10,maxlen=10) for _ in range(16)]
    queue=deque();tail_seen={};allocslot={};bufword={};sumword={};peaks=Counter();expected_commits=0;actual_commits=0
    group_times={t:[a for a,g in sorted(v)] for t,v in group_changes.items()}
    group_values={t:[g for a,g in sorted(v)] for t,v in group_changes.items()}
    def group_at(t,edge):
        i=bisect_right(group_times[t],edge)-1
        return group_values[t][i] if i>=0 else 0
    for edge in range(max(tl,default=-1)+1):
        events=tl[edge]
        for kind,data in events:
            if kind=='read':addr,version=data;assert mem.get(addr)==version,('stale data',edge,addr,version,mem.get(addr))
            if kind=='history_read':
                e=data;t=e['t'];index=-2 if mutant=='history9' else -1
                assert history[t][index]==e['id'],('wrong shared T history',edge,t,e['id'],history[t][index])
                group=group_at(t,edge-1-(5 if mutant=='mq_group5' else 15)) if pk else 0
                assert returns.get((edge-1,t,group))==(e['id'],12),('wrong mq group selection',edge,t,group)
            if kind=='history_write':
                e=data;t=e['t'];group=group_at(t,edge-1-(15 if mutant=='T_group15' else 5)) if pk else 0
                assert returns.get((edge-1,t,group))==(e['id'],2),('wrong T group selection',edge,t,group)
            if kind in ('buf_read','side_read'):
                if kind=='side_read':
                    e=data;t=e['t'];slot=allocslot[e['id']];assert ram[t].pop(slot,None)==e['id'],('side data overwritten',edge,t,slot)
                else:
                    e,step=data;t=e['t'];slot=allocslot[e['id']];word=(pr['L'] if step['product']==2 else 0)+step['limb']
                    assert bufword.get((t,slot,word))==e['id'],('FFT side overwritten',edge,t,slot,word)
        for kind,data in events:
            if kind=='psum':
                e,step=data;t=e['t'];p=step['product'];j=step['limb'];ID=e['id']
                if p==0:psum[t][j]=(ID,0)
                elif p==1:assert psum[t].get(j)==(ID,0);psum[t][j]=(ID,1)
                else:assert psum[t].get(j)==(ID,1),('partial sum stale',edge,t,j)
        # Commit observes old head; pop before push allows full+pop+push.
        commits=[d for k,d in events if k=='commit']
        if commits:
            assert queue,'response without write context';head=queue[0]
            assert all(e['stage']==head['stage'] for e,tag,last in commits),'interleaved stage output'
            assert sum(1<<e['t'] for e,tag,last in commits)==head['mask'],'response mask mismatch'
            assert len({tag for e,tag,last in commits})==1,'inconsistent cohort tags'
            for e,tag,last in commits:
                actual_commits+=1
                if last and tag==head['tail_tag']:tail_seen[head['stage']]|=1<<e['t']
            if tail_seen[head['stage']]==head['mask']:
                assert edge==head['tail'];queue.popleft()
        for kind,data in events:
            if kind=='ctx_push':
                assert len(queue)<16;queue.append(data);tail_seen[data['stage']]=0
                peaks['contexts']=max(peaks['contexts'],len(queue))
            if kind=='free':
                e=data;assert live[e['t']].pop(allocslot[e['id']],None)==e['id'],'double-free'
            if kind=='retire':
                e=data;assert e['id'] in outstanding[e['t']];outstanding[e['t']].remove(e['id'])
        for kind,data in events:
            if kind=='alloc':
                e=data;t=e['t'];depth=(1 if mutant=='fft_depth1' and fft else pr['buffer_depth']) if fft else (2 if mutant=='side_depth2' else 16)
                slot=sideptr[t]%depth;sideptr[t]+=1
                assert slot not in live[t],('buffer overwrite',edge,t,slot,len(live[t]),depth)
                live[t][slot]=e['id'];allocslot[e['id']]=slot;outstanding[t].add(e['id'])
                peaks['fft_buffers' if fft else 'side_reserved']=max(peaks['fft_buffers' if fft else 'side_reserved'],len(live[t]))
                peaks['outstanding']=max(peaks['outstanding'],len(outstanding[t]))
            if kind=='side_write':
                e=data;t=e['t'];slot=allocslot[e['id']];assert slot not in ram[t];ram[t][slot]=e['id']
                peaks['side_written']=max(peaks['side_written'],len(ram[t]))
            if kind=='buf_write':
                e,j=data;t=e['t'];slot=allocslot[e['id']];L=pr['L'];word=(j%2)*L+j//2
                assert live[t].get(slot)==e['id'];bufword[t,slot,word]=e['id']
            if kind=='sum_write':
                e,j=data;sumword[e['t'],allocslot[e['id']],j]=e['id']
            if kind=='write':addr,version=data;mem[addr]=version
        # LUTRAM fetch is after the launch edge; addresses are registered there.
        for kind,data in events:
            if kind=='operand_fetch':
                e,step=data;t=e['t'];slot=allocslot[e['id']];product=step['product']
                source=sumword if product==2 else bufword
                offset=pr['L'] if product==1 else 0
                for word in (offset+step['i'],offset+step['j']):
                    assert source.get((t,slot,word))==e['id'],('operand/root not ready or overwritten',edge,t,slot,word)
        # A shared fixed-length SRL shifts every edge, including invalid bubbles.
        inserted={e['t']:e['id'] for k,e in events if k=='history_write'}
        assert len(inserted)==sum(k=='history_write' for k,d in events)
        for t in range(16):history[t].appendleft(inserted.get(t))
    assert not queue and all(not x for x in live) and all(not x for x in outstanding) and all(not x for x in ram),'did not drain'
    for addr,version in host_words(c,fft,cfg['fmt'],cfg['logn'],inv,pk,True):
        if plan['layers']:assert mem.get(addr)==version,('wrong output mapping',addr,version,mem.get(addr))
    assert plan['cycles']==0 if not plan['layers'] else plan['cycles']>0
    return dict(**cfg,cycles=plan['cycles'],root_words=plan['root_words'],packets=ident,host_phases_max=host_max,peaks=dict(peaks),bank_accesses=len(rports)+len(wports),resource_slots=len(resources))

def eval_guard(expr,env):
    # Tiny guard language: OR groups separated by |, AND by &, literal !name.
    return any(all((not env.get(x.strip()[1:],False)) if x.strip().startswith('!') else (True if x.strip()=='true' else env.get(x.strip(),False)) for x in term.split('&')) for term in expr.split('|'))
def transition(machine,state,env):
    for r in machine['global_rules']+machine['states'][state]:
        if eval_guard(r['when'],env):return r
    raise AssertionError(('no transition',state,env))
def check_fsms():
    summary={};total=0
    for name,m in FSM['machines'].items():
        assert m['initial'] in m['states'];rows=0;reachable={m['initial']};graph=defaultdict(set)
        for state,rs in m['states'].items():
            assert rs[-1]['when']=='true'
            flags=sorted(set(re.findall(r'\b[a-z][a-z_0-9]*\b',' '.join(x['when'] for x in m['global_rules']+rs)))-{'true'})
            covered=set()
            for bits in itertools.product((False,True),repeat=len(flags)):
                env=dict(zip(flags,bits));r=transition(m,state,env);rows+=1;assert r['to'] in m['states']
                graph[state].add(r['to']);covered.add((r['when'],r['to']))
                if env.get('bus_reset') or env.get('reset'):assert r['to']==m['initial']
                elif env.get('soft_reset') and name=='frontend':assert r['to']=='ABORT_SEND'
                elif env.get('abort_req') and name=='executor':assert r['to']=='RECOVER0'
            assert all((r['when'],r['to']) in covered for r in rs),('unreachable/shadowed rule',name,state)
        changed=True
        while changed:
            new=reachable|set().union(*(graph[s] for s in reachable));changed=new!=reachable;reachable=new
        assert reachable==set(m['states']),('unreachable state',name,set(m['states'])-reachable)
        total+=rows;summary[name]=dict(states=len(m['states']),guard_assignments=rows)
    # Special simultaneous event witnesses: no last-read duplication, no reset deadlock.
    r=transition(FSM['machines']['issue'],'WAIT_DUE',dict(due=True,last_read=True,next_stage_fire=True))
    assert r['to']=='WAIT_DUE' and 'stage_done' in r['actions']
    ex=FSM['machines']['executor'];state='RUN'
    state=transition(ex,state,{'abort_req':True,'fault':True})['to']
    state=transition(ex,state,{})['to'];r=transition(ex,state,{})
    assert r['to']=='IDLE' and 'abort_ack_if_pending' in r['actions']
    return dict(machines=summary,total_guard_assignments=total)

def c4(fft,pk,u,q,a=0,b=0,ci=0):
    if fft:A=a;B=b;cin=ci
    elif pk:
        lo=u&0x1ffff;hi=u>>17
        A=(hi<<18)|(1<<17)|lo
        B=(((~(q>>16))&0x1ffff)<<18)|(1<<17)|((~(q&65535))&0x1ffff);cin=1
    else:A=u&0x1ffffffff;B=(~q)&((1<<36)-1);cin=1
    z=(A+B+cin)&((1<<36)-1)
    if fft:return z&0x1ffffffff
    if not pk:return (u if z>>35 else z)&0xffffffff
    return (((u>>17)&65535) if not (z>>35) else (z>>18)&65535)<<16 | ((u&65535) if not ((z>>17)&1) else z&65535)
def addsub_bits(a,b,q,ci=0,bi=0,split=0,plain=0,fa=0,fb=0,wa=0,wb=0,fci=0,wci=0):
    mask=65535;S=(a+b+ci)&((1<<33)-1)
    D=(((a>>16)<<17)|(1<<16)|(a&mask))+((((~(b>>16))&mask)<<17)|(split<<16)|((~b)&mask))+(1-bi)
    D&=(1<<34)-1
    if plain:
        A=((fa>>16)<<17)|(1<<16)|(fa&mask);B=((fb>>16)<<17)|(fb&mask);sq=A+B+fci
        A=((wa>>16)<<17)|(1<<16)|(wa&mask);B=((wb>>16)<<17)|(wb&mask);dq=A+B+wci
    else:
        A=((S>>16)<<17)|(1<<16)|(S&mask);B=(((~(q>>16))&0x1ffff)<<17)|(split<<16)|((~q)&mask);sq=A+B+1
        A=(((D>>17)&mask)<<17)|((1-split)<<16)|(D&mask);B=((q>>16)<<17)|(q&mask);dq=A+B
    fs=(((sq>>33)&1)<<32)|(((sq>>17)&mask)<<16)|(sq&mask)
    ws=(((dq>>33)&1)<<32)|(((dq>>17)&mask)<<16)|(dq&mask)
    if plain:s=S&0xffffffff;d=(((D>>17)&mask)<<16)|(D&mask)
    else:
        snh=not((sq>>34)&1);snl=not((sq>>16)&1) if split else snh
        dnh=not((D>>33)&1);dnl=not((D>>16)&1) if split else dnh
        s=((((S>>16)&mask) if snh else ((sq>>17)&mask))<<16)|((S&mask) if snl else (sq&mask))
        d=((((dq>>17)&mask) if dnh else ((D>>17)&mask))<<16)|((dq&mask) if dnl else (D&mask))
    return s,d,(S>>32)&1,1-((D>>33)&1),fs,ws

def check_guard_math():
    rng=random.Random(20261105);count=0
    for q in [3,12289,32749,8380417,2147483647]:
        for u in [0,1,q-1,q,2*q-1]+[rng.randrange(2*q) for _ in range(1000)]:
            assert c4(False,False,u,q)==(u-q if u>=q else u);count+=1
    for ql,qh in [(3,32749),(12289,12289),(32749,3)]:
        for _ in range(3000):
            lo=rng.randrange(2*ql);hi=rng.randrange(2*qh)
            got=c4(False,True,lo|(hi<<17),ql|(qh<<16));want=(lo-ql if lo>=ql else lo)|((hi-qh if hi>=qh else hi)<<16)
            assert got==want,(lo,hi,got,want);count+=1
    for _ in range(5000):
        a=rng.getrandbits(32);b=rng.getrandbits(32);ci=rng.randrange(2)
        assert c4(True,False,0,0,a,b,ci)==a+b+ci;count+=1
    n=0
    for q in [3,12289,8380417,2147483647]:
        for _ in range(1500):
            a=rng.randrange(q);b=rng.randrange(q);s,d,*_=addsub_bits(a,b,q)
            assert s==(a+b)%q and d==(a-b)%q;n+=1
    for ql,qh in [(3,32749),(12289,12289),(32749,3)]:
        for _ in range(1500):
            al=rng.randrange(ql);ah=rng.randrange(qh);bl=rng.randrange(ql);bh=rng.randrange(qh)
            s,d,*_=addsub_bits(al|(ah<<16),bl|(bh<<16),ql|(qh<<16),split=1)
            assert s==((al+bl)%ql)|(((ah+bh)%qh)<<16)
            assert d==((al-bl)%ql)|(((ah-bh)%qh)<<16);n+=1
    for _ in range(3000):
        a,b,fa,fb,wa,wb=[rng.getrandbits(32) for _ in range(6)];ci,bi,fci,wci=[rng.randrange(2) for _ in range(4)]
        s,d,co,bo,fs,ws=addsub_bits(a,b,0,ci,bi,plain=1,fa=fa,fb=fb,wa=wa,wb=wb,fci=fci,wci=wci)
        assert s==(a+b+ci)&0xffffffff and d==(a-b-bi)&0xffffffff
        assert co==(a+b+ci)>>32 and bo==int(a<b+bi)
        assert fs==fa+fb+fci and ws==wa+wb+wci;n+=1
    return dict(c4_vectors=count,c2_c3_vectors=n,chain_bits=36)

def reset_trial(latency,cut,packed=False,mutant=False):
    # Data bits are not reset; only all valid stages and in-flight ownership are.
    data=[None]*(latency+1);valid=[False]*(latency+1);pending=set();accepted=retired=0
    origin=cut+4;new_end=origin+10
    for edge in range(new_end+latency+2):
        old_request=edge<cut and (edge%3<2 if packed else edge%3==0)
        new_request=origin<=edge<new_end and ((edge-origin)%3<2 if packed else (edge-origin)%3==0)
        token=(0 if old_request else 1,edge) if old_request or new_request else None
        data=[token]+data[:-1];valid=[token is not None]+valid[:-1]
        if edge==cut:
            pending.clear()
            if mutant:valid[-1]=False
            else:valid=[False]*len(valid)
        elif token is not None:
            pending.add(token)
            if token[0]==1:accepted+=1
        if valid[-1]:
            out=data[-1]
            assert out in pending,('stale response after reset',latency,cut,edge,out)
            pending.remove(out)
            if out[0]==1:retired+=1
    assert not pending and accepted==retired and not any(valid)

class LookaheadFIFO:
    """RAM storage plus head/next FFs; bypass same-edge RAM hazards explicitly."""
    def __init__(self):self.ram=[None]*16;self.rp=self.wp=self.count=0;self.head=self.next=None
    def step(self,push=None,pop=False):
        n=self.count;rp=self.rp;wp=self.wp;head=self.head;nxt=self.next
        assert not pop or n>0 or push is not None,'FIFO underflow'
        assert push is None or n<16 or pop,'FIFO overflow'
        result=head if n else push
        if pop:
            if n>=2:
                self.head=nxt
                # n==2 plus push: read-address old rp+2 equals write address.
                self.next=push if n==2 else self.ram[(rp+2)&15]
            elif n==1:self.head=push;self.next=None
            else:self.head=self.next=None
        elif push is not None:
            if n==0:self.head=push
            elif n==1:self.next=push
        if push is not None:self.ram[wp]=push;self.wp=(wp+1)&15
        # Empty bypass push+pop advances both pointers.
        if pop:self.rp=(rp+1)&15
        self.count=n+int(push is not None)-int(pop)
        assert 0<=self.count<=16
        return result if pop else None

def check_fifo_and_abort():
    # Exhaust all nonempty masks, including masks which do not contain tile0.
    for mask in range(1,1<<16):
        owner=(mask&-mask).bit_length()-1;assert mask&(1<<owner)
        seen=0
        for t in range(16):
            if mask&(1<<t):seen|=1<<t
            if seen==mask:assert all(not(mask&(1<<j)) for j in range(t+1,16))
        assert seen==mask
    q=deque();fifo=LookaheadFIFO();rng=random.Random(36);simultaneous=0
    for i in range(20000):
        pop=bool(rng.randrange(2));push=i if rng.randrange(2) else None
        if not q and push is None:pop=False
        if len(q)==16 and not pop:push=None
        want=q.popleft() if pop and q else push if pop else None
        if push is not None and not(pop and not q and fifo.count==0):q.append(push)
        got=fifo.step(push,pop);assert got==want and fifo.count==len(q)
        if q:assert fifo.head==q[0]
        if len(q)>1:assert fifo.next==q[1]
        simultaneous+=int(pop and push is not None)
    while q:assert fifo.step(None,True)==q.popleft()
    # Flush all validity while leaving data bits flowing, at every cutpoint.
    resets=0
    for latency in [20,21]+[p['outputs'][-1]['rsp'] for p in TIM['fft'].values()]:
        for cut in range(latency+2):
            for packed in (False,True):reset_trial(latency,cut,packed);resets+=1
    return dict(active_masks=65535,fifo_cycles=20000,fifo_simultaneous_cases=simultaneous,abort_cutpoints=resets,
                limitation='Abstract epoch/valid flush control; not RTL reset or AXI electrical simulation.')

def mutation_checks():
    caught=[]
    def reject(name,fn):
        try:fn()
        except AssertionError:caught.append(name)
        else:raise AssertionError(('negative control not caught',name))
    pk=schedule(0,0,8,0,0,1,2)
    reject('packed_groups_aliased',lambda:check_case(pk,'group0'))
    reject('shared_history_delay9',lambda:check_case(pk,'history9'))
    reject('T_select_uses_delay15',lambda:check_case(pk,'T_group15'))
    reject('mq_select_uses_delay5',lambda:check_case(pk,'mq_group5'))
    reject('side_depth2',lambda:check_case(pk,'side_depth2'))
    reject('FFT128_only_one_buffer',lambda:check_case(schedule(1,2,10,0,0,0,0),'fft_depth1'))
    bad=copy.deepcopy(pk);bad['layers'][0]['push']=bad['layers'][0]['tail']+1
    reject('context_after_response',lambda:check_case(bad))
    bad=copy.deepcopy(pk);e=bad['layers'][0]['events'][0]
    addr,cy,ver=e['rd'][0];e['rd'][0]=(addr,cy,(999,*ver[1:]))
    reject('wrong_memory_version',lambda:check_case(bad))
    reject('reset_only_output_valid',lambda:reset_trial(21,10,True,True))
    def lost_split():
        lo=3;hi=12288;qlo=3;qhi=12289
        correct=c4(False,True,lo|(hi<<17),qlo|(qhi<<16))
        wrong=c4(False,False,lo|(hi<<16),qlo|(qhi<<16))
        assert correct==wrong,'packed split guard missing'
    reject('C4_packed_lost_split',lost_split)
    reject('host_gather_only_last_phase',lambda:host_gather_trial([((0,j),j) for j in range(4)],True))
    return caught

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--output',default='study/build/flextransform_rebuild/microarch_0_2');args=ap.parse_args()
    out=(ROOT/args.output).resolve();assert (ROOT/'study/build/flextransform_rebuild').resolve() in out.parents
    out.mkdir(parents=True,exist_ok=True)
    cases=[]
    for fft in (0,1):
        for fmt in ((0,1,2) if fft else (0,)):
            for ln in range(0 if fft else 1,11):
                for hm in ((0,) if fft else range(min(2,ln-1)+1)):
                    for pk in ((0,) if fft else (0,1)):
                        for jl in range(5):
                            try:G.config(fft,fmt,ln,hm,pk,jl)
                            except AssertionError:continue
                            for inv in (0,1):
                                for native in ((0,1) if fft and fmt==1 else (0,)):
                                    if args.quick and (ln not in (1,5,10) or jl not in (0,4)):continue
                                    cases.append((fft,fmt,ln,hm,inv,pk,jl,native))
    results=[]
    for i,key in enumerate(cases):
        result=check_case(schedule(*key));results.append(result)
        if i%50==0:print('LIVENESS_PROGRESS',i,len(cases),flush=True)
    extra=dict(fsm=check_fsms(),guard_math=check_guard_math(),fifo_reset=check_fifo_and_abort(),negative_controls=mutation_checks())
    peak=Counter()
    for r in results:
        for k,v in r['peaks'].items():peak[k]=max(peak[k],v)
    sources=[HERE/'microarchitecture'/f for f in ['ports.json','timing.json','fsm.json']]+[Path(__file__).resolve(),Path(G.__file__),ROOT/'model/cg_bank4_model.py']
    report=dict(status='MODEL_PASS',scope='locked microarchitecture resource/memory-version/finite-control model; no new RTL or PPA',full=not args.quick,cases=len(results),peaks=dict(peak),extra=extra,results=results,
                sha256={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (out/'liveness_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LIVENESS_MODEL_PASS',len(results),dict(peak),flush=True)
if __name__=='__main__':main()
