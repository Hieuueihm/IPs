"""Physical scheduling and numeric replay for packed NTT and homogeneous batches.

Bank jobs occupy unused CG address bits; row jobs occupy extra planes. Includes
the within-word final/first layer of full packed16 NTT. No precision reduction.
"""
import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sp=importlib.util.spec_from_file_location('batch_cg',ROOT/'model/cg_bank4_model.py')
cg=importlib.util.module_from_spec(sp);sp.loader.exec_module(cg)
cg.FFT[4]=(45,cg.FFT[4][1])
CACHE={}
# a_cg_z020_lat1 (03/11/2026): every tile request is registered once more before the operand stage (+1 for every mode), and
# the NTT CT result passes the two-stage add/sub at the output (+1 more for the forward NTT).
TILE_EXTRA=1
NTT_CT_EXTRA=1
# a_cg_z020_system160: FFT results leave the tile in the clock their T limb is made (inverse) or one clock later (forward,
# through the shared add/sub), no longer one limb later. Clocks earlier than the a_cg_batch table, per result j: the gap
# to the next T limb of the same row (the last limb: 1), and one more for the inverse.
FFT_OUT_EARLY={1:[0,0],2:[1,1,1,1],4:[4,3,2,1,4,3,2,1]}


def config(fft,fmt,ln,hm,packed,jl):
    n=max(0,ln-1) if fft else ln-(1 if packed and hm==0 else hm)
    bl=fmt+1 if fft else max(0,hm-packed)
    bj=min(jl,max(0,5-n));rj=jl-bj
    assert bl+rj<=3 and max(0,n-5)+bl+rj<=7
    return dict(n=n,m=1<<n,base_log=bl,base=1<<bl,bj=bj,rj=rj,
                planes=1<<(bl+rj),rows=1<<max(0,n-5),stages=n+int(packed and hm==0),
                jobs=1<<jl,job_word_log=ln+fmt if fft else ln-packed)


def bank(p,jb,n,stage,bj):
    if n>=6:return cg.bank(p,1<<n,stage)
    v=cg.rol(p,-stage,n)<<(5-n) if n else 0
    return cg.rol(v|(jb<<(5-n-bj)),stage,5)


def addr(c,buf,p,jb,jr,bpl,stage):
    pl=(jr<<c['base_log'])|bpl
    return bank(p,jb,c['n'],stage,c['bj']),buf*c['rows']*c['planes']+pl*c['rows']+(p>>5)


def plan(fft,fmt,ln,hm,inv,native,packed,jl):
    key=(fft,fmt,ln,hm,inv,native,packed,jl)
    if key in CACHE:return CACHE[key]
    c=config(fft,fmt,ln,hm,packed,jl);n,m=c['n'],c['m'];fl=(1<<fmt) if fft else 0
    internal=bool(packed and hm==0)
    labels=list(range(m));layers=[]
    for s in range(c['stages']):
        ip=internal and (s==0 if inv else s==c['stages']-1)
        ws=s-int(internal and inv)
        f=n-1-ws if inv else ws
        src,dst=(n,n) if ip else (f+1,f) if inv else (f,f+1)
        h=1<<ws if inv and not ip else m>>(ws+1) if not ip else 0
        pairs=defaultdict(list)
        for jb in range(1<<c['bj']):
            for i in range(max(1,m//2)):
                if ip:
                    rp=(2*i,2*i+1 if m>1 else None);wp=rp
                    t=(bank(rp[0],jb,n,n,c['bj'])>>1) if n<6 else i&15
                    roots=(m+rp[0],m+rp[1] if rp[1] is not None else 0)
                else:
                    far,near=(i,i+m//2),(2*i,2*i+1)
                    rp,wp=(near,far) if inv else (far,near)
                    t=bank(i,jb,n,f,c['bj'])&15
                    x,y=(labels[p] for p in rp)
                    assert y==x+h and (x//h)%2==0
                    roots=((m//h if fft else m//(2*h))+x//(2*h),)
                pairs[t].append((i,jb,rp,wp,roots))
        ev=[]
        for t,ps in sorted(pairs.items()):
            for k,(i,jb,rp,wp,roots) in enumerate(ps):
                for part in range((1<<c['rj']) if fft else c['planes']):
                    jr=part if fft else part>>c['base_log']
                    bpart=0 if fft else part&(c['base']-1)
                    per=cg.FFT[fl][0] if fft else 3
                    seq=k*((1<<c['rj']) if fft else c['planes'])+part
                    a=2+(per*seq)
                    e=dict(t=t,k=k,i=i,jb=jb,jr=jr,job=(jr<<c['bj'])|jb,part=bpart,
                           A=a,per=per,rp=rp,wp=wp,root=roots,internal=ip,s=s,reads=[],writes=[])
                    for j in range(c['base'] if fft else 1):
                        bpl=(j%2)*fl+j//2 if fft else bpart
                        opl=j if fft else bpart
                        rc=a-2+j if fft else a-2
                        wc=a+cg.FFT[fl][1][j]-FFT_OUT_EARLY[fl][j]-int(inv)+1+TILE_EXTRA+(2 if native and inv else 0) if fft else a+21+TILE_EXTRA+(0 if inv else NTT_CT_EXTRA)
                        for port,p in enumerate(rp):
                            a0=addr(c,s&1,p if p is not None else 0,jb,jr,bpl,src)
                            if p is None:a0=(a0[0]^1,a0[1])
                            e['reads'].append((a0,rc,p,bpl,port))
                        for port,p in enumerate(wp):
                            a0=addr(c,1-(s&1),p if p is not None else 0,jb,jr,opl,dst)
                            if p is None:a0=(a0[0]^1,a0[1])
                            e['writes'].append((a0,wc,p,opl,port))
                    ev.append(e)
        if not ip:
            out=[None]*m
            # Every job performs the same permutation; build it once.
            for ps in pairs.values():
                for i,jb,rp,wp,roots in ps:
                    for p,lab in zip(wp,(labels[p] for p in rp)):out[p]=lab
            assert None not in out;labels=out
        layers.append(ev)
    assert labels==list(range(m))
    def schedule(overlap):
        import copy
        events=copy.deepcopy(layers);book=cg.Book();starts=[];lastread=lastwrite=-1
        for ev in events:
            lo=(lastread if overlap else lastwrite)+1-min(x[1] for e in ev for x in e['reads'])
            lo=max(lo,lastwrite+1-min(x[1] for e in ev for x in e['writes']))
            period=cg.FFT[fl][0] if fft else 3
            start=book.earliest(ev,max(0,lo),period if overlap or not fft else 1,0)
            book.take(ev,start);starts.append(start)
            lastread=max(x[1] for e in ev for x in e['reads'])
            lastwrite=max(x[1] for e in ev for x in e['writes'])
        return dict(layers=events,starts=starts,cycles=lastwrite+1+(3 if fft else 4) if events else 0)
    out=min((schedule(False),schedule(True)),key=lambda p:p['cycles'])
    out.update(c);out.update(fft=fft,fmt=fmt,logn=ln,hmin=hm,inverse=inv,native=native,packed=packed,jobs_log=jl)
    CACHE[key]=out
    return out


def replay(pn,data,q,gm,igm):
    c=pn;fft=c['fft'];fl=1<<c['fmt'];n,m=c['n'],c['m'];inv=c['inverse'];pk=c['packed']
    w=32*fl;mask=(1<<w)-1;mem={};states=[];events=[]
    perjob=1<<c['logn'];plane0=n if inv else 0
    for job in range(c['jobs']):
        jb=job&((1<<c['bj'])-1);jr=job>>c['bj']
        for p in range(m):
            for bpl in range(c['base']):
                if fft:
                    local=p+(bpl//fl)*m
                    v=(data[job*perjob+local]>>(32*(bpl%fl)))&0xffffffff if local<perjob else 0
                elif pk:
                    start=job*perjob+2*(p*c['base']+bpl)
                    v=data[start]|(data[start+1]<<16)
                else:v=data[job*perjob+p*c['base']+bpl]
                a=addr(c,0,p,jb,jr,bpl,plane0)
                assert a not in mem,('initial alias',a)
                mem[a]=(v,(-1,job,p,bpl))
    for layer in c['layers']:
        for e in layer:
            idx=len(states);states.append(dict(e=e,got={},out=None))
            for kind in ('reads','writes'):
                for a,cy,p,pl,port in e[kind]:events.append((cy,kind,idx,a,p,pl,port))
    for cy,kind,idx,a,p,pl,port in sorted(events):
        st=states[idx];e=st['e'];job=e['job']
        if kind=='reads':
            if p is None:v=0
            else:
                v,version=mem[a]
                assert version==(e['s']-1,job,p,pl),('stale',cy,a,version,e)
            st['got'][port,pl]=v
            if len(st['got'])==2*(c['base'] if fft else 1):
                roots=(igm if inv else gm)
                if fft:
                    vals=[cg.fp.wrap(sum(st['got'][port,part*fl+k]<<(32*k) for k in range(fl)),w) for port in (0,1) for part in (0,1)]
                    ar,ai,br,bi=vals;wr,wi=roots[e['root'][0]]
                    if c['native']:
                        def mul(x,y):return cg.fp.wrap((cg.fp.wrap(x,64)*cg.fp.wrap(y,64))>>32,64)
                        def cmul(x,y,u,v):
                            a,b=mul(x,u),mul(y,v);z=mul(cg.fp.wrap(x+y,w),cg.fp.wrap(u+v,w))
                            return cg.fp.wrap(a-b,w),cg.fp.wrap(z-a-b,w)
                    else:cmul=lambda x,y,u,v:cg.fp.cmul(x,y,u,v,w)
                    if inv:
                        sr,si,dr,di=[cg.fp.wrap(x,w) for x in (ar+br,ai+bi,ar-br,ai-bi)]
                        if c['native']:sr,si,dr,di=[cg.fp.wrap(x+1,w)>>1 for x in (sr,si,dr,di)]
                        tr,ti=cmul(dr,di,wr,wi);vals=[sr,si,tr,ti]
                        if not c['native'] and e['s']==c['stages']-1:
                            vals=[cg.fp.wrap(x+(1<<(n-1)),w)>>n for x in vals]
                    else:
                        tr,ti=cmul(br,bi,wr,wi);vals=[cg.fp.wrap(x,w) for x in (ar+tr,ai+ti,ar-tr,ai-ti)]
                    st['out']={(port,part*fl+k):(vals[2*port+part]>>(32*k))&0xffffffff for port in (0,1) for part in (0,1) for k in range(fl)}
                else:
                    x,y=(st['got'][port,e['part']] for port in (0,1))
                    def bf(x,y,root):
                        if inv:return ((x+y)*pow(2,-1,q)%q,(x-y)*root*pow(1<<32,-1,q)%q)
                        t=y*root*pow(1<<32,-1,q)%q;return ((x+t)%q,(x-t)%q)
                    if pk and e['internal']:
                        z=[]
                        for port,v in enumerate((x,y)):
                            root=roots[e['root'][port]] if e['root'][port] else 0
                            a0,a1=bf(v&65535,v>>16,root);z.append(a0|(a1<<16))
                    elif pk:
                        zz=[bf((x>>(16*j))&65535,(y>>(16*j))&65535,roots[e['root'][0]]) for j in (0,1)]
                        z=[zz[0][port]|(zz[1][port]<<16) for port in (0,1)]
                    else:z=bf(x,y,roots[e['root'][0]])
                    st['out']={(port,e['part']):z[port] for port in (0,1)}
        else:
            assert st['out'] is not None
            mem[a]=(st['out'][port,pl],(e['s'],job,p,pl))
    result=[];buf=c['stages']&1;laststage=0 if inv else n
    for job in range(c['jobs']):
        jb=job&((1<<c['bj'])-1);jr=job>>c['bj']
        if fft:
            for part in (0,1):
                for p in range(m):
                    result.append(cg.fp.wrap(sum(mem[addr(c,buf,p,jb,jr,part*fl+k,laststage)][0]<<(32*k) for k in range(fl)),w))
            if c['logn']==0:result=result[:-1]
        else:
            for p in range(m):
                for bpl in range(c['base']):
                    v=mem[addr(c,buf,p,jb,jr,bpl,laststage)][0]
                    result.extend((v&65535,v>>16) if pk else (v,))
    return result
