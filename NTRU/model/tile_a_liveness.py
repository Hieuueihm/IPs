"""Read-only trace of existing tile, followed by a model of A's packed memories.

No RTL implementation change. Generated observation-only testbench goes under study/build.
Checks dense addresses, read ports, interleaved input values and lifetime against an
existing-RTL trace. It does not prove a new RTL pipeline or a LUT reduction.
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'study/build/tile_a_liveness'
MASK=(1 << 32)-1
spec=importlib.util.spec_from_file_location('live_ref',ROOT/'model/fft_core_plan.py')
fp=importlib.util.module_from_spec(spec);spec.loader.exec_module(fp)

PROBE=r'''
module state_probe;
integer owner[0:7]; integer z,ctx,b,k,part,t;
initial for(z=0;z<8;z=z+1) owner[z]=-1;
task ev(input string family, act, input integer bf, pa, li, input reg [63:0] value, input string role);
 $display("EV %0d %s %s %0d %0d %0d %h %s",tb_wide_timing.cyc,family,act,bf,pa,li,value,role);
endtask
always @(posedge tb_wide_timing.clk) begin
 t=tb_wide_timing.cyc;
 if(tb_wide_timing.req_valid && tb_wide_timing.req_ready)
  $display("IN %0d %0d %0d %h %h",t,tb_wide_timing.tag/(2*tb_wide_timing.L),tb_wide_timing.tag%(2*tb_wide_timing.L),tb_wide_timing.dut.req_data,tb_wide_timing.dut.req_root);
 if(tb_wide_timing.dut.ce && tb_wide_timing.dut.v5 && tb_wide_timing.dut.mf) begin
  b=tb_wide_timing.dut.g1/(2*tb_wide_timing.L);
  ctx=tb_wide_timing.dut.wn1;
  if(tb_wide_timing.dut.wb1==0) owner[ctx]=b;
  part=tb_wide_timing.dut.wb1/tb_wide_timing.L;
  k=tb_wide_timing.dut.wb1%tb_wide_timing.L;
  ev("O","W",b,part,k,{tb_wide_timing.dut.ks[0],tb_wide_timing.dut.sc1,tb_wide_timing.dut.g1,tb_wide_timing.dut.s1},"INPUT");
  ev("X","W",b,part,k,tb_wide_timing.dut.a1,"INPUT");
  ev("W","W",b,part,k,tb_wide_timing.dut.w1,"INPUT");
  if(tb_wide_timing.dut.wim1) begin
   ev("X","R",b,0,k,tb_wide_timing.dut.wmx[tb_wide_timing.dut.wir],"PRE");
   ev("W","R",b,0,k,tb_wide_timing.dut.wmw[tb_wide_timing.dut.wir],"PRE");
  end
 end
 if(tb_wide_timing.dut.ce && tb_wide_timing.dut.wsv) begin
  b=owner[tb_wide_timing.dut.wsa>>2];k=tb_wide_timing.dut.wsa&3;
  ev("SX","W",b,0,k,tb_wide_timing.dut.sa5,"PRE");
  ev("SW","W",b,0,k,tb_wide_timing.dut.sw5,"PRE");
 end
 if(tb_wide_timing.dut.ce && tb_wide_timing.dut.mbz) begin
  b=owner[tb_wide_timing.dut.mbn];
  k=tb_wide_timing.dut.mt[7:6];part=tb_wide_timing.dut.mpr;
  if(part==2) ev("SX","R",b,0,k,tb_wide_timing.dut.mopa,"MUL");
  else ev("X","R",b,part,k,tb_wide_timing.dut.mopa,"MUL");
  k=tb_wide_timing.dut.mt[5:4];
  if(part==2) ev("SW","R",b,0,k,tb_wide_timing.dut.mopb,"MUL");
  else ev("W","R",b,part,k,tb_wide_timing.dut.mopb,"MUL");
 end
 if(tb_wide_timing.dut.ce && tb_wide_timing.dut.wpv) begin
  b=owner[tb_wide_timing.dut.wpn];k=tb_wide_timing.dut.wpe;
  part=(tb_wide_timing.dut.wpp==2)?1:0;
  ev("O","R",b,part,k,tb_wide_timing.dut.wma[tb_wide_timing.dut.wadr(tb_wide_timing.dut.w4,tb_wide_timing.dut.l1,tb_wide_timing.dut.wpn,part*tb_wide_timing.L+k)],"POST");
  if(tb_wide_timing.dut.wpp!=0)
   ev("PS","R",b,(tb_wide_timing.dut.wpp==2)?1:0,k,tb_wide_timing.dut.wpr,"POST");
  if(tb_wide_timing.dut.wpp<2)
   ev("PS","W",b,(tb_wide_timing.dut.wpp==1)?1:0,k,(tb_wide_timing.dut.wpp==0)?tb_wide_timing.dut.wpl:tb_wide_timing.dut.wts[31:0],"POST");
 end
 if(tb_wide_timing.rsp_valid)
  $display("RESULT %0d %0d %0d %h",t,tb_wide_timing.rsp_tag/(2*tb_wide_timing.L),tb_wide_timing.rsp_tag%(2*tb_wide_timing.L),tb_wide_timing.rsp_data);
end
endmodule
'''

NTT_PROBE=r'''
module ntt_state_probe;
always @(posedge tb_ntt_state.clk) begin
 if(tb_ntt_state.req_valid && tb_ntt_state.req_ready)
  $display("NIN %0d %0d %h %h",tb_ntt_state.cyc,tb_ntt_state.tag,tb_ntt_state.dut.req_data,tb_ntt_state.dut.req_root);
 if(tb_ntt_state.dut.ce && tb_ntt_state.dut.v1)
  $display("NW %0d %0d %h",tb_ntt_state.cyc,tb_ntt_state.dut.g1,{tb_ntt_state.dut.ks[0],tb_ntt_state.dut.sc1,tb_ntt_state.dut.g1,tb_ntt_state.dut.s1});
 if(tb_ntt_state.dut.ce && tb_ntt_state.dut.vd[tb_ntt_state.dut.E32-1])
  $display("NR %0d %0d %h",tb_ntt_state.cyc,tb_ntt_state.dut.wma[tb_ntt_state.dut.nra][39:32],tb_ntt_state.dut.wma[tb_ntt_state.dut.nra]);
 if(tb_ntt_state.rsp_valid)
  $display("NOUT %0d %0d %h",tb_ntt_state.cyc,tb_ntt_state.rsp_tag,tb_ntt_state.rsp_data);
end
endmodule
'''


def parse(text):
    ev,inputs,outputs=[],{},{}
    for line in text.splitlines():
        a=line.split()
        if a and a[0]=='EV':
            _,t,f,rw,b,p,k,v,role=a
            ev.append(dict(t=int(t),f=f,rw=rw,b=int(b),p=int(p),k=int(k),v=int(v,16),role=role))
        elif a and a[0]=='IN':
            _,t,b,j,d,w=a
            inputs[int(b),int(j)]=(int(t),int(d,16),int(w,16))
        elif a and a[0]=='RESULT':
            _,t,b,j,v=a
            outputs[int(b),int(j)]=(int(t),int(v,16))
    assert ev and inputs and outputs
    assert all(x['b']>=0 for x in ev)
    return ev,inputs,outputs


def numeric(ev,inputs,outputs,l,inverse):
    width=32*l
    bcount=max(b for b,j in inputs)+1
    expected={}
    def assemble(values):
        return fp.wrap(sum(v << (32*k) for k,v in enumerate(values)),width)
    for b in range(bcount):
        ar,ai,br,bi,wr,wi=[assemble([((inputs[b,part*l+k][1] >> shift)&MASK) if field=='d'
                                     else inputs[b,part*l+k][2] for k in range(l)])
                            for part,shift,field in [(0,0,'d'),(1,0,'d'),(0,32,'d'),(1,32,'d'),(0,0,'w'),(1,0,'w')]]
        side=[fp.wrap(ar+br,width),fp.wrap(ai+bi,width)] if inverse else [ar,ai]
        op=[fp.wrap(ar-br,width),fp.wrap(ai-bi,width)] if inverse else [br,bi]
        roots=[wr,wi]
        # Model actual GS carry/borrow in re_k, im_k order, independently for each component.
        cs=[0,0];bs=[0,0]
        for k in range(l):
            for part,(a,bb) in enumerate([(ar,br),(ai,bi)]):
                aa=(a>>(32*k))&MASK;zz=(bb>>(32*k))&MASK
                su=aa+zz+cs[part];di=aa-zz-bs[part]
                cs[part]=su>>32;bs[part]=int(di<0)
                if inverse:
                    assert (su&MASK)==((side[part]>>(32*k))&MASK)
                    assert (di&MASK)==((op[part]>>(32*k))&MASK)
        for part in (0,1):
            for k in range(l):
                expected['O',b,part,k]=(side[part]>>(32*k))&MASK
                expected['X',b,part,k]=(op[part]>>(32*k))&MASK
                expected['W',b,part,k]=(roots[part]>>(32*k))&MASK
        for f,sm in [('SX',fp.wrap(sum(op),width)),('SW',fp.wrap(sum(roots),width))]:
            for k in range(l):expected[f,b,0,k]=(sm>>(32*k))&MASK
        tr,ti=fp.cmul(*op,wr,wi,width)
        vals=[side[0],side[1],tr,ti] if inverse else [fp.wrap(ar+tr,width),fp.wrap(ai+ti,width),fp.wrap(ar-tr,width),fp.wrap(ai-ti,width)]
        if inverse:
            vals=[fp.wrap(v+(1<<4),width)>>5 for v in vals]  # probe cfg shift s=5
        for j in range(2*l):
            part,k=divmod(j,l)
            want=((vals[part]>>(32*k))&MASK) | (((vals[2+part]>>(32*k))&MASK)<<32)
            assert outputs[b,j][1]==want,(width,inverse,b,j)
    for e in ev:
        if e['rw']=='W' and e['f']!='PS':
            assert (e['v']&MASK)==expected[e['f'],e['b'],e['p'],e['k']],e
    return bcount


def audit(ev,l,interleave,slots):
    rows=defaultdict(list)
    pre_removed=0
    for item in ev:
        e=dict(item)
        if interleave:
            if e['role']=='INPUT':
                e['t']+=2*e['k']+e['p']-(e['p']*l+e['k'])
            elif e['role']=='PRE':
                if e['rw']=='R':
                    pre_removed+=1
                    continue
                e['t']+=e['k']+1-l
        if e['f']=='PS':a=e['k']
        elif e['f'] in ('SX','SW'):a=(e['b']%slots)*l+e['k']
        else:a=(e['b']%slots)*2*l+e['p']*l+e['k']
        e['a']=a
        rows[e['t']].append(e)
    memory={};counts=Counter();last_reads={};first_writes={};maxaddr=defaultdict(int)
    holds={}
    for t,events in sorted(rows.items()):
        # LUT RAM style: asynchronous old value sampled at the edge before synchronous write.
        for e in sorted(events,key=lambda e:e['rw']):
            f=e['f'];key=(e['b'],e['p'],e['k']);ma=(f,e['a'])
            maxaddr[f]=max(maxaddr[f],e['a']+1)
            counts[f,e['rw'],t]+=1
            if e['rw']=='R':
                assert memory.get(ma)==(key,e['v']),('alias/stale',l,interleave,t,e,memory.get(ma))
                last_reads[f,*key]=t
            else:
                memory[ma]=(key,e['v'])
                first_writes[f,*key]=t
                if e['role']=='INPUT' and f in ('X','W') and e['p']==0:
                    holds[f,e['b'],e['k']]=(t,e['v'])
    if interleave:
        # Every removed PRE RAM read is supplied by the previous real input register.
        for e in ev:
            if e['role']=='PRE' and e['rw']=='R':
                new_t=e['t']+e['k']+1-l
                assert holds[e['f'],e['b'],e['k']]==(new_t-1,e['v'])
    peaks={f:{rw:max([v for (ff,rr,t),v in counts.items() if ff==f and rr==rw] or [0])
              for rw in ('R','W')} for f in ('O','X','W','SX','SW','PS')}
    if interleave:
        assert all(v['R']<=1 and v['W']<=1 for v in peaks.values()),peaks
    return dict(status='PASS',slots=slots,ports=peaks,max_addressed_entries=dict(maxaddr),
                removed_PRE_reads=pre_removed,
                counted_edges=len(rows),semantic_reads=sum(e['rw']=='R' for v in rows.values() for e in v))


def audit_ntt(iv,vvp,tb):
    tb=tb.replace('module tb_wide_timing;','module tb_ntt_state;')
    tb=tb.replace('reg [63:0] probe_data=0;',
        'reg [31:0] Q=12289, QI=0; integer packed_mode=0;\n'
        '    initial begin if($value$plusargs("Q=%h",Q)) begin end if($value$plusargs("QI=%h",QI)) begin end if($value$plusargs("PACK=%d",packed_mode)) begin end end\n'
        '    function [15:0] rndq; rndq=$unsigned($random)%Q; endfunction\n'
        '    reg [63:0] probe_data=0;')
    tb=tb.replace('probe_data <= {$random,$random}; probe_root <= $random;',
        'if(packed_mode) begin probe_data <= {rndq(),rndq(),rndq(),rndq()}; probe_root <= {rndq(),rndq()}; end '
        'else begin probe_data <= {$unsigned($random)%Q,$unsigned($random)%Q}; probe_root <= $unsigned($random)%Q; end')
    tb=tb.replace('.cfg_qinv(32\'d0)','.cfg_qinv(QI)').replace('.cfg_halve(1\'b0)','.cfg_halve(dir[0])')
    tb=tb.replace(".req_mode(2'd1)",".req_mode(packed_mode ? 2'd2 : 2'd0)")
    tb=tb.replace('nb = 12','nb = 40').replace('nb = 24','nb = 40')
    tb=tb.replace("cfg_q = (L == 1) ? 32'h05 : (L == 2) ? 32'h15 : 32'h25;",'cfg_q = packed_mode ? {Q[15:0],Q[15:0]} : Q;')
    tb=tb.replace('for (b = 0; b < nb; b = b + 1) begin','while(!req_ready) @(negedge clk);\n        for (b = 0; b < nb; b = b + 1) begin')
    tb=tb.replace('k < 2 * L','k < 1').replace('tag = 2 * L * b + k','tag = b').replace('P - 2 * L','P - 1')
    top=BUILD/'ntt_driven.sv';top.write_text(tb,encoding='utf-8')
    probe=BUILD/'ntt_probe.sv';probe.write_text(NTT_PROBE,encoding='utf-8')
    exe=BUILD/'ntt.vvp'
    args=[iv,'-g2012','-DTL_IN_REG=1','-s','tb_ntt_state','-s','ntt_state_probe','-o',str(exe),
          'hdl/mul_ss.v','hdl/tile/tile_thu.sv',str(top),str(probe)]
    proc=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr[-2000:]
    results=[]
    for packed,qs in [(False,[3329,12289,8380417,2147483647]),(True,[3329,12289])]:
        for q in qs:
            bits=16 if packed else 32
            qi=(-pow(q,-1,1 << bits))% (1 << bits)
            cfgqi=(qi<<16)|qi if packed else qi
            for inv in (0,1):
                cmd=[vvp,'-n',str(exe),'+W=1','+P=3',f'+DIR={inv}','+SC=0',f'+Q={q:x}',f'+QI={cfgqi:x}',f'+PACK={int(packed)}']
                p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
                label=f'ntt_q{q}_pack{int(packed)}_dir{inv}'
                (BUILD/f'{label}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
                assert p.returncode==0 and 'not ready 0' in p.stdout,p.stdout[-1000:]
                incoming={};outgoing={};events=[]
                for line in p.stdout.splitlines():
                    a=line.split()
                    if not a:continue
                    if a[0]=='NIN':incoming[int(a[2])]=(int(a[1]),int(a[3],16),int(a[4],16))
                    elif a[0]=='NOUT':outgoing[int(a[2])]=(int(a[1]),int(a[3],16))
                    elif a[0] in ('NW','NR'):events.append((int(a[1]),a[0],int(a[2]),int(a[3],16)))
                assert len(incoming)==len(outgoing)==40,(label,len(incoming),len(outgoing))
                mask=(1 << bits)-1;rinv=pow(1 << bits,-1,q)
                sides={}
                for b,(cyc,d,w) in incoming.items():
                    xs=d&MASK;ys=d>>32;outs=[];side=0
                    for lane in range(2 if packed else 1):
                        x=(xs>>(lane*bits))&mask;y=(ys>>(lane*bits))&mask;ww=(w>>(lane*bits))&mask
                        sm=(x+y)%q
                        if inv:
                            s=(sm+(q if sm&1 else 0))>>1
                            u,v=s,((x-y)%q)*ww*rinv%q
                            stored_side=sm
                        else:
                            t=y*ww*rinv%q;u,v=(x+t)%q,(x-t)%q;s=x
                            stored_side=x
                        side|=stored_side<<(lane*bits)
                        outs.append((u,v))
                    z0=sum(u<<(k*bits) for k,(u,v) in enumerate(outs))
                    z1=sum(v<<(k*bits) for k,(u,v) in enumerate(outs))
                    assert outgoing[b][1]==(z1<<32)|z0,(label,b)
                    sides[b]=side
                mem={};live=set();peak=0;counts=Counter()
                for cyc,kind,b,value in sorted(events,key=lambda a:(a[0],a[1])):
                    counts[kind,cyc]+=1
                    address=b%16
                    if kind=='NR':
                        assert mem.get(address)==(b,value),(label,'FIFO alias',b)
                        live.remove(b)
                    else:
                        assert value&MASK==sides[b],(label,'side',b)
                        mem[address]=(b,value);live.add(b)
                    peak=max(peak,len(live))
                assert not live
                assert max(counts.values())==1
                results.append(dict(q=q,packed=packed,inverse=bool(inv),requests=40,status='PASS',
                                    observed_live_side_words=peak,proposed_entries=16,max_R=1,max_W=1,
                                    max_result_latency=max(outgoing[b][0]-incoming[b][0] for b in incoming)))
    print('NTT side FIFO: scalar/packed,',len(results),'cases PASS; peak',max(r['observed_live_side_words'] for r in results),flush=True)
    return results


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    iv=shutil.which('iverilog') or 'C:/iverilog/bin/iverilog.exe'
    vvp=shutil.which('vvp') or 'C:/iverilog/bin/vvp.exe'
    rtl=ROOT/'hdl/tile/tile_thu.sv'
    original=hashlib.sha256(rtl.read_bytes()).hexdigest()
    probe=BUILD/'probe.sv';probe.write_text(PROBE,encoding='utf-8')
    # The timing-only TB connects $random expressions directly to ports. Use real
    # driven registers in this generated copy so the numeric trace contains no Z/X.
    tb=(ROOT/'sim/tile_thu/tb_wide_timing.sv').read_text()
    tb=tb.replace("reg  [7:0]  tag = 0;", "reg [63:0] probe_data=0; reg [31:0] probe_root=0;\n"
                  "    always @(negedge clk) begin probe_data <= {$random,$random}; probe_root <= $random; end\n"
                  "    reg  [7:0]  tag = 0;")
    tb=tb.replace('.req_data({$random, $random})','.req_data(probe_data)').replace('.req_root($random)','.req_root(probe_root)')
    tb=tb.replace('nb = 12','nb = 24')  # wrap every proposed ring at least twice
    driven=BUILD/'timing_driven.sv';driven.write_text(tb,encoding='utf-8')
    exe=BUILD/'probe.vvp'
    args=[iv,'-g2012','-DTL_IN_REG=1','-s','tb_wide_timing','-s','state_probe','-o',str(exe),
          'hdl/mul_ss.v','hdl/tile/tile_thu.sv',str(driven),str(probe)]
    comp=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    (BUILD/'compile.log').write_text(comp.stdout+comp.stderr,encoding='utf-8')
    assert comp.returncode==0,(comp.stdout+comp.stderr)[-3000:]
    result=dict(date='2026-11-02',kind='existing RTL trace plus memory remapping model, not new RTL',
                cases=[],source_rtl_sha256=original)
    for l,period,slots in [(1,3,8),(2,12,4),(4,48,2)]:
        for inverse in (0,1):
            cmd=[vvp,'-n',str(exe),f'+W={l}',f'+P={period}',f'+DIR={inverse}','+SC=1']
            proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120)
            log=BUILD/f'w{32*l}_dir{inverse}.log'
            log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
            assert proc.returncode==0 and 'not ready 0' in proc.stdout,proc.stdout[-1200:]
            ev,inputs,outputs=parse(proc.stdout)
            bfs=numeric(ev,inputs,outputs,l,inverse)
            old=audit(ev,l,False,{1:8,2:4,4:4}[l])
            dense=audit(ev,l,False,slots)
            inter=audit(ev,l,True,slots)
            lifetime=max(t-inputs[b,0][0] for (b,j),(t,v) in outputs.items())
            row=dict(width=32*l,inverse=bool(inverse),period=period,butterflies=bfs,
                     input_to_last_result=lifetime,observed_old=old,dense=dense,interleaved=inter,
                     log=log.relative_to(ROOT).as_posix())
            result['cases'].append(row)
            print(f'W{32*l} dir{inverse}: {bfs} BF numeric/dense/interleaved PASS; ports old/new '+
                  str(old['ports']['X'])+' / '+str(inter['ports']['X']),flush=True)
    assert hashlib.sha256(rtl.read_bytes()).hexdigest()==original
    result['ntt_cases']=audit_ntt(iv,vvp,tb)
    assert hashlib.sha256(rtl.read_bytes()).hexdigest()==original
    # A deliberately wrong operand value and an undersized BF128 ring must fail.
    mutations=[]
    bad=[dict(e) for e in ev]
    next(e for e in bad if e['f']=='X' and e['rw']=='R' and e['role']=='MUL')['v']^=1
    for label,events,count in [('read_value_flip',bad,slots),('BF128_one_slot',ev,1)]:
        try:
            audit(events,4,False,count)
        except AssertionError:
            mutations.append(label)
        else:
            raise AssertionError('Mutation was not detected: '+label)
    result['mutations_detected']=mutations
    result['limitations']=[
        'Core-like intervals 3/12/48, 24 BF per case, LEAF_PD=2 IN_REG=1, no arbitrary burst acceptance claim.',
        'Dense/interleaved variants are memory event models, not rewritten RTL or a routed netlist.',
        'Interleaving needs two GS carry/borrow contexts, new beat decode and rechecked core bank timing.',
        'The previous real operand/root must be held or reused from an earlier existing pipeline register; register/timing cost not measured.',
        'Single R/W counts are consumed logical accesses; LUTRAM packing and LUT savings still need synthesis.',
        'NTT FIFO checks use fixed phase, one slot, q tests and per-word packed mode; core packed16 bank integration is not modeled.']
    files=[Path(__file__),ROOT/'model/fft_core_plan.py',ROOT/'sim/tile_thu/tb_wide_timing.sv',ROOT/'hdl/mul_ss.v',probe,driven,BUILD/'ntt_probe.sv',BUILD/'ntt_driven.sv']
    result['sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result['logs_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in BUILD.glob('*.log')}
    out=ROOT/'study/results'
    (out/'tile_a_liveness.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# A: liveness, đóng gói địa chỉ và cổng đọc','',
           'Quan sát RTL hiện tại bằng testbench chỉ đọc, rồi kiểm mô hình bộ nhớ mới; chưa sửa RTL.','',
           '| W | Chiều | BF | Slot | X/W: cổng đọc cũ | X/W: xen kẽ mới | Mỗi mảng operand/side | Mỗi mảng tổng |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result['cases']:
        a=r['interleaved']['max_addressed_entries'];old=r['observed_old']['ports'];new=r['interleaved']['ports']
        lines.append(f"| {r['width']} | {'ngược' if r['inverse'] else 'xuôi'} | {r['butterflies']} | {r['interleaved']['slots']} | {old['X']['R']} / {old['W']['R']} | {new['X']['R']} / {new['W']['R']} | {max(a[f] for f in ('O','X','W'))} | {max(a[f] for f in ('SX','SW'))} |")
    lines+=['',f"NTT: {len(result['ntt_cases'])} cấu hình ×40 request PASS, gồm q3329/12289/8380417/2^31−1 và packed16 q3329/12289, hai chiều.",
            f"FIFO side có tối đa {max(r['observed_live_side_words'] for r in result['ntt_cases'])} word sống, ánh xạ vào 16 entry PASS, 1R/1W."]
    lines+=['','## Giới hạn','',*['- '+x for x in result['limitations']], '',
            'Nguồn: [model](../../model/tile_a_liveness.py), [JSON và log](tile_a_liveness.json).']
    (out/'tile_a_liveness.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote study/results/tile_a_liveness.{json,md}',flush=True)


if __name__=='__main__':
    main()
