"""Isolated shared-logic experiment. Does not modify production RTL or ROMs.

Run without arguments to freeze inputs and build three variants under study/build.
Run with --test to simulate selected tile/core suites, or --synth to measure tile/net.
All variants use a commit barrier for FFT, so the comparison starts from correct RTL.
"""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'study/build/shared_logic_experiment'


def replace(s, a, b):
    assert a in s, a[:120]
    return s.replace(a, b)


def dump(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8', newline='\n')


def net32(tab, sums):
    lines=['// Generated isolated experiment: paired word32 routing.',
           'module ntt_bank_net_s (input clk,en, input [1023:0] bank_rd, input [511:0] pack_rd,',
           'input [63:0] sel_xlo,sel_ylo,sel_xhi,sel_yhi, input [15:0] hold_x,',
           'input [31:0] root1, input [63:0] sel_root, input [15:0] load_w,',
           'output reg [511:0] op_x,op_y, output reg [1023:0] op_w,',
           'input [1023:0] tile_z, input [255:0] wsel,input [63:0] wen,',
           'output reg [1023:0] bank_wd,output reg [63:0] bank_we'+
           (',input [255:0] pack_sum, output reg [511:0] op_sum' if sums else '')+');']
    for t in range(16):
        for op in 'xy':
            src=tab['read_lo'][f'{t}{op}']
            assert tab['read_hi'][f'{t}{op}']==[b+1 for b in src]
            lines += [f'reg [31:0] {op}{t}; always @* begin case(sel_{op}lo[{4*t}+:4])']
            lines += [f"4'd{i}: {op}{t}=bank_rd[{16*b}+:32];" for i,b in enumerate(src)]
            lines += [f'default: {op}{t}=0; endcase end']
        port=4*(t//8)
        lines += [f'reg [63:0] w{t};',f'reg [31:0] sx{t},sum{t};',
                  f'always @* begin sum{t}=0; case(sel_root[{4*t}+:4]>>1)']
        for b in range(4):
            lines += [f"3'd{b}: begin w{t}=pack_rd[{64*(port+b)}+:64];"+
                      (f'sum{t}=pack_sum[{32*(port+b)}+:32];' if sums else '')+' end']
        lines += [f'default: w{t}={{32\'d0,root1}}; endcase end',
                  f'always @(posedge clk) if(en) begin sx{t}<=x{t};',
                  f'op_x[{32*t}+:32]<=hold_x[{t}]?sx{t}:x{t}; op_y[{32*t}+:32]<=y{t};',
                  f'if(load_w[{t}]) begin op_w[{64*t}+:64]<=w{t};'+
                  (f'op_sum[{32*t}+:32]<=sum{t};' if sums else '')+' end end']
    for b in range(32):
        src=tab['write'][str(2*b)]
        assert tab['write'][str(2*b+1)]==[x.replace('lo','hi') for x in src]
        lines += [f'reg [31:0] z{b}; always @* begin case(wsel[{8*b}+:4])']
        for i,x in enumerate(src):
            t=int(x[:-3]); offset=64*t+(32 if x[-3]=='y' else 0)
            lines += [f"4'd{i}: z{b}=tile_z[{offset}+:32];"]
        lines += [f'default: z{b}=0; endcase end',
                  f'always @(posedge clk) if(en) begin bank_wd[{32*b}+:32]<=z{b};',
                  f'bank_we[{2*b}+:2]<={{2{{wen[{2*b}]}}}}; end']
    lines += ['endmodule']
    return '\n'.join(lines)+'\n'


def root_tile(s):
    # New side input is the limb of wrap_W(wr+wi), supplied on every beat.
    s=replace(s,'input  wire [31:0]  req_root,','input  wire [31:0]  req_root, req_root_sum,')
    s=replace(s,'wire [31:0] rq_root;', 'wire [31:0] rq_root, rq_root_sum;')
    s=replace(s,'reg [31:0] rroot;', 'reg [31:0] rroot, rroot_sum;')
    s=replace(s,'rroot <= req_root;', 'rroot <= req_root; rroot_sum <= req_root_sum;')
    s=replace(s,'assign rq_root = rroot;', 'assign rq_root_sum = rroot_sum; assign rq_root = rroot;')
    s=replace(s,'assign rq_root = req_root;', 'assign rq_root_sum = req_root_sum; assign rq_root = req_root;')
    s=replace(s,'reg  [31:0] a1, w1, s1;', 'reg [31:0] root_sum1; reg  [31:0] a1, w1, s1;')
    s=replace(s,'w1 <= rq_root;', 'w1 <= rq_root; root_sum1 <= rq_root_sum;')
    s=replace(s,'reg        wcs, wcw, wsv, wsl;', 'reg        wcs, wsv, wsl;')
    s=re.sub(r'    wire \[32:0\] swo = .*?;\n','',s)
    s=replace(s,'sw5 <= swo[31:0];','sw5 <= root_sum1;')
    s=replace(s,'wcw <= swo[32]; ','')
    # Registered measurement wrapper, same new input and alignment.
    s=replace(s,'input  wire [31:0]  req_root_i,','input  wire [31:0]  req_root_i, req_root_sum_i,')
    s=replace(s,'reg [31:0]  req_root;', 'reg [31:0]  req_root, req_root_sum;')
    s=replace(s,'req_root <= req_root_i;', 'req_root <= req_root_i; req_root_sum <= req_root_sum_i;')
    s=replace(s,'.req_root(req_root), .req_tag(req_tag),','.req_root(req_root), .req_root_sum(req_root_sum), .req_tag(req_tag),')
    return s


def barrier(s):
    # Common correctness fix: wait for real stage writes, not the obsolete FFT32 delta.
    s=replace(s,'wire [4:0] nfin = pop16(fin_now);',
        'wire [4:0] nfin = pop16(fin_now);\n'
        'reg [13:0] fft_stage_writes;\n'
        'wire [13:0] fft_stage_total = (14\'d1 << (logn-2)) << fmt;\n'
        'always @(posedge clk) if(rst || state==CFG || layer_sw) fft_stage_writes<=0;\n'
        'else if(state==RUN && fft) fft_stage_writes<=fft_stage_writes+{9\'d0,nfin};')
    return replace(s,"(lt == delta - 10'd1);", "(fft ? (fft_stage_writes == fft_stage_total) : (lt == delta - 10'd1));")


def core_sums(s):
    s=replace(s,'wire [511:0] op_x, op_y;','wire [511:0] op_x, op_y;') if 'wire [511:0] op_x, op_y;' in s else s
    s=replace(s,'wire [16*32-1:0] op_x, op_y;', 'wire [16*32-1:0] op_x, op_y, op_sum;')
    s=replace(s,'wire [8*64-1:0]  pack_rd;', 'wire [8*32-1:0] pack_sum;\n    wire [8*64-1:0]  pack_rd;')
    s=replace(s,'assign pack_rd[64*gb +: 64]', 'assign pack_sum[32*gb+:32]=pack_q[96*gb+:32];\n        assign pack_sum[32*(gb+4)+:32]=pack_q[96*(gb+4)+:32];\n        assign pack_rd[64*gb +: 64]')
    s=replace(s,'.bank_rd(m_rd), .pack_rd(pack_rd),','.bank_rd(m_rd), .pack_rd(pack_rd), .pack_sum(pack_sum), .op_sum(op_sum),')
    s=replace(s,'reg  [31:0] fwi;', 'reg [31:0] fsum; reg  [31:0] fwi;')
    s=replace(s,'fwi <= op_w[64*t+32 +: 32];',
        'begin fwi <= op_w[64*t+32 +: 32]; fsum <= op_sum[32*t+:32]; end')
    s=replace(s,'.req_root(fft ? froot : nroot),',
        '.req_root(fft ? froot : nroot), .req_root_sum(wide ? op_sum[32*st+:32] : (bim ? fsum : op_sum[32*t+:32])),')
    return s


def build():
    source_files=['hdl/mul_ss.v','hdl/tile/tile_thu.sv','hdl/net/ntt_bank_net_s.sv',
      'hdl/core/flex_banked_scratch.sv','hdl/core_ntt/ntt_core_gen.sv','hdl/core_ntt/ntt_core.sv',
      'sim/core_ntt/tb_ntt_core.sv','sim/tile_thu/tb_tile_thu.sv']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_files}
    if (OUT/'inputs.json').exists():
        assert json.loads((OUT/'inputs.json').read_text())==hashes,'Frozen experiment exists with different inputs; use a new experiment directory.'
    dump(OUT/'inputs.json',json.dumps(hashes,indent=2)+'\n')
    tab=json.loads((ROOT/'study/results/structured_net.json').read_text())
    tile=(ROOT/'hdl/tile/tile_thu.sv').read_text()
    core=barrier((ROOT/'hdl/core_ntt/ntt_core.sv').read_text())
    for name in ('baseline','word32','root_sum'):
        d=OUT/name; d.mkdir(parents=True,exist_ok=True)
        for p in source_files:
            dump(d/Path(p).name,(ROOT/p).read_text())
        dump(d/'tile_thu.sv',root_tile(tile) if name=='root_sum' else tile)
        dump(d/'ntt_bank_net_s.sv',net32(tab,name=='root_sum') if name!='baseline' else (ROOT/'hdl/net/ntt_bank_net_s.sv').read_text())
        cs=core_sums(core) if name=='root_sum' else core
        cs=replace(cs,'`define NTT_ROM_DIR "hdl/core_ntt/"',f'`define NTT_ROM_DIR "{d.as_posix()}/"')
        dump(d/'ntt_core.sv',cs)
        banks=[[int(x,16) for x in (ROOT/f'hdl/core_ntt/root_pack_b{b}.mem').read_text().splitlines()] for b in range(4)]
        if name=='root_sum':
            for L,bases in [(1,(384,576)),(2,(768,1152)),(4,(1536,2304))]:
                for base in bases:
                    for k in range(768):
                        b=k%4; row=base+(k//4)*L
                        wr=sum(((banks[b][row+l]>>32)&0xffffffff)<<(32*l) for l in range(L))
                        wi=sum(((banks[b][row+l]>>64)&0xffffffff)<<(32*l) for l in range(L))
                        total=(wr+wi)% (1<<(32*L))
                        for l in range(L):
                            assert banks[b][row+l]&0xffffffff==0
                            banks[b][row+l]|=(total>>(32*l))&0xffffffff
        for b,words in enumerate(banks):dump(d/f'root_pack_b{b}.mem',''.join(f'{x:024x}\n' for x in words))
    print('Built baseline, word32, root_sum; production sources unchanged.',flush=True)


def run(cmd,log,timeout=240):
    with log.open('w',encoding='utf-8') as f:
        p=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    assert p.returncode==0,(cmd,log)
    return log.read_text(encoding='utf-8',errors='replace')


def test(names):
    results=json.loads((OUT/'tests.json').read_text()) if (OUT/'tests.json').exists() else {}
    for name in names:
        d=OUT/name
        files=[d/x for x in ['mul_ss.v','tile_thu.sv','ntt_bank_net_s.sv','flex_banked_scratch.sv','ntt_core_gen.sv','ntt_core.sv','tb_ntt_core.sv']]
        run(['iverilog','-g2012','-o',str(d/'core.vvp'),*[str(p) for p in files]],d/'compile.log')
        results.setdefault(name,{})
        # Full golden transform sets; fail closed by inspecting actual CASE lines and TOTAL.
        for label,extra,count in [('ntt',[],48),('fft',['+FILE=sim/core_ntt/vectors_fft.txt'],54)]:
            text=run(['vvp','-n',str(d/'core.vvp'),*extra],d/f'{label}.log',timeout=600)
            cases=re.findall(r'^CASE .*$',text,re.M)
            assert len(cases)==count and all('err=0 ' in x and 'not_ready=0' in x for x in cases),(name,label,'case mismatch')
            assert re.search(rf'^TOTAL cases={count} err=0 PASS$',text,re.M),(name,label,'not PASS')
            results[name][label]=cases
            dump(OUT/'tests.json',json.dumps(results,indent=2)+'\n')
            print(name,label,count,'PASS',flush=True)


def synth():
    # Compare full feature tile wrappers; root_sum adds a registered32 side input.
    lines=['set root {'+ROOT.as_posix()+'}','cd $root','set_param general.maxThreads 4']
    for name in ('baseline','root_sum'):
        d=OUT/name
        lines += ['create_project -in_memory -part xczu7ev-ffvc1156-2-e',
          f'read_verilog {{{(d/"mul_ss.v").as_posix()}}}',f'read_verilog -sv {{{(d/"tile_thu.sv").as_posix()}}}',
          'synth_design -top tile_thu_top -part xczu7ev-ffvc1156-2-e -mode out_of_context -generic TREN_MANG=1',
          'create_clock -name clk -period 3.000 [get_ports clk]','opt_design',
          f'report_utilization -file {{{(d/"tile_util.rpt").as_posix()}}}',
          f'report_utilization -hierarchical -file {{{(d/"tile_hier.rpt").as_posix()}}}',
          'place_design','route_design',f'report_timing_summary -file {{{(d/"tile_timing.rpt").as_posix()}}}',
          f'report_utilization -file {{{(d/"tile_route_util.rpt").as_posix()}}}','close_project']
    dump(OUT/'measure.tcl','\n'.join(lines)+'\n')
    log=run(['C:/Xilinx/Vivado/2018.1/bin/vivado.bat','-mode','batch','-source',str(OUT/'measure.tcl'),
             '-log',str(OUT/'vivado.log'),'-journal',str(OUT/'vivado.jou')],OUT/'synth_console.log',timeout=1800)
    print('Tile PPA reports written.',flush=True)


def synth_core():
    lines=['cd {'+ROOT.as_posix()+'}','set_param general.maxThreads 4']
    for name in ('baseline','root_sum'):
        d=OUT/name
        lines+=['create_project -in_memory -part xczu7ev-ffvc1156-2-e']
        for f in ('mul_ss.v','tile_thu.sv','ntt_bank_net_s.sv','flex_banked_scratch.sv','ntt_core_gen.sv','ntt_core.sv'):
            lines += [f'read_verilog -sv {{{(d/f).as_posix()}}}']
        lines += ['synth_design -top ntt_core -part xczu7ev-ffvc1156-2-e -mode out_of_context',
          'create_clock -name clk -period 3.000 [get_ports clk]','opt_design',
          f'report_utilization -file {{{(d/"core_util.rpt").as_posix()}}}',
          f'report_utilization -hierarchical -file {{{(d/"core_hier.rpt").as_posix()}}}',
          f'report_timing_summary -file {{{(d/"core_synth_timing.rpt").as_posix()}}}','close_project']
    dump(OUT/'measure_core.tcl','\n'.join(lines)+'\n')
    run(['C:/Xilinx/Vivado/2018.1/bin/vivado.bat','-mode','batch','-source',str(OUT/'measure_core.tcl'),
        '-log',str(OUT/'vivado_core.log'),'-journal',str(OUT/'vivado_core.jou')],OUT/'core_console.log',timeout=2400)
    print('Full-core synthesis comparison written (not routed timing).',flush=True)


def test_network():
    d=OUT/'net_test'; d.mkdir(exist_ok=True)
    for name,module in [('baseline','net_ref'),('root_sum','net_new')]:
        s=(OUT/name/'ntt_bank_net_s.sv').read_text().replace('module ntt_bank_net_s','module '+module)
        dump(d/f'{module}.sv',s)
    tb='''`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg en; reg [1023:0] bank_rd,tile_z; reg [511:0] pack_rd;
reg [255:0] pack_sum,wsel; reg [63:0] sx,sy,sr,wen; reg [15:0] hold_x,load_w;
reg [31:0] root1; wire [511:0] ax,ay,bx,by,bs;
wire [1023:0] aw,bw,az,bz; wire [63:0] ae,be;
net_ref a(.clk(clk),.en(en),.bank_rd(bank_rd),.tile_z(tile_z),.pack_rd(pack_rd),
 .sel_xlo(sx),.sel_xhi(sx),.sel_ylo(sy),.sel_yhi(sy),.hold_x(hold_x),.root1(root1),
 .sel_root(sr),.load_w(load_w),.op_x(ax),.op_y(ay),.op_w(aw),.wsel(wsel),.wen(wen),.bank_wd(az),.bank_we(ae));
net_new b(.clk(clk),.en(en),.bank_rd(bank_rd),.tile_z(tile_z),.pack_rd(pack_rd),
 .sel_xlo(sx),.sel_xhi(sx),.sel_ylo(sy),.sel_yhi(sy),.hold_x(hold_x),.root1(root1),
 .sel_root(sr),.load_w(load_w),.op_x(bx),.op_y(by),.op_w(bw),.wsel(wsel),.wen(wen),.bank_wd(bz),.bank_we(be),
 .pack_sum(pack_sum),.op_sum(bs));
integer i,j,r,seed=20261101;
reg [511:0] expected_sum=0;
initial begin
 for(i=0;i<5000;i=i+1) begin
  @(negedge clk);
  en=(i<3)?1:($random(seed)&3)!=0; hold_x=(i<3)?0:$random(seed); load_w=(i<3)?16'hffff:$random(seed);
  root1=$random(seed); sx={$random(seed),$random(seed)}; sy={$random(seed),$random(seed)}; sr={$random(seed),$random(seed)};
  for(j=0;j<32;j=j+1) begin bank_rd[32*j+:32]=$random(seed); tile_z[32*j+:32]=$random(seed); end
  for(j=0;j<16;j=j+1) pack_rd[32*j+:32]=$random(seed);
  for(j=0;j<8;j=j+1) pack_sum[32*j+:32]=$random(seed);
  for(j=0;j<32;j=j+1) begin r=$random(seed); wsel[8*j+:8]={r[3:0],r[3:0]};wen[2*j+:2]={2{r[4]}};end
  if(en) for(j=0;j<16;j=j+1) if(load_w[j]) begin
    r=(sr[4*j+:4]>>1);
    expected_sum[32*j+:32]=(r<4)?pack_sum[32*(4*(j/8)+r)+:32]:0;
  end
  @(posedge clk); #1;
  if(i>2 && {ax,ay,aw,az,ae} !== {bx,by,bw,bz,be}) $fatal(1,"network mismatch cycle=%0d",i);
  if(i>2 && bs !== expected_sum) $fatal(1,"sum root path mismatch cycle=%0d",i);
 end
 $display("NETWORK 5000 cycles PASS, data/root/write/enable/hold checked");$finish;
end
endmodule
'''
    dump(d/'tb.sv',tb)
    run(['iverilog','-g2012','-o',str(d/'net.vvp'),str(d/'net_ref.sv'),str(d/'net_new.sv'),str(d/'tb.sv')],d/'compile.log')
    text=run(['vvp','-n',str(d/'net.vvp')],d/'result.log')
    assert '5000 cycles PASS' in text
    print(text,flush=True)


def test_tile_sum():
    d=OUT/'root_sum'
    s=(ROOT/'sim/tile_thu/tb_tile_thu.sv').read_text()
    s=replace(s,'reg  [31:0]  req_root;', 'reg [31:0] req_root_sum; reg  [31:0]  req_root;')
    s=replace(s,'.req_root(req_root), .req_tag(req_tag),', '.req_root(req_root), .req_root_sum(req_root_sum), .req_tag(req_tag),')
    s=replace(s,'reg [31:0]  v_r     [0:MAXN-1];','reg [31:0] v_rs [0:MAXN-1]; reg [31:0]  v_r     [0:MAXN-1];')
    s=replace(s,'v_d[n] = 0; v_r[n] = 0;', 'v_rs[n]=0; v_d[n] = 0; v_r[n] = 0;')
    s=replace(s,'v_d[n] = {br, ar}; v_r[n] = wr;', 'v_rs[n]=wr+wi; v_d[n] = {br, ar}; v_r[n] = wr;')
    s=replace(s,'v_d[n] = {bi, ai}; v_r[n] = wi;', 'v_rs[n]=wr+wi; v_d[n] = {bi, ai}; v_r[n] = wi;')
    s=replace(s,'v_mode[n] = 5; v_dir[n] = dr[0]; v_q[n] = {fm[1:0], sh[3:0]};',
        'v_rs[n]=(wwr+wwi) >> (32*(lb%nl)); v_mode[n] = 5; v_dir[n] = dr[0]; v_q[n] = {fm[1:0], sh[3:0]};')
    s=replace(s,"req_root = zero ? 32'd0 : v_r[idx];", "req_root = zero ? 32'd0 : v_r[idx]; req_root_sum=zero?0:v_rs[idx];")
    s=replace(s,'req_data = v_d[idx]; req_root = v_r[idx];', 'req_data = v_d[idx]; req_root = v_r[idx]; req_root_sum=0;')
    s=replace(s,'req_data = 0; req_root = 0;', 'req_root_sum=0; req_data = 0; req_root = 0;')
    dump(d/'tb_tile_sum.sv',s)
    run(['iverilog','-g2012','-P','tb_tile_thu.TREN_MANG=1','-o',str(d/'tile.vvp'),
        str(d/'mul_ss.v'),str(d/'tile_thu.sv'),str(d/'tb_tile_sum.sv')],d/'tile_compile.log')
    for name,kind in [('fft32bf',3),('fftwbf',4),('ntt',2)]:
        for stall in (False,True):
            label=f'tile_{name}_{int(stall)}'
            cmd=['vvp','-n',str(d/'tile.vvp'),f'+FILE=spec/FlexTransform/2.0/assets/tile/{name}.txt',f'+KIND={kind}']
            if stall:cmd+=['+STALL=30','+BURST=1','+SPARSE=25','+SEED=47']
            text=run(cmd,d/f'{label}.log')
            total=re.findall(r'^TOTAL.*$',text,re.M)
            assert len(total)==1 and 'err=0 PASS' in total[0],(label,total)
            print('root_sum',label,total[0],flush=True)


def fast_test(names):
    results=json.loads((OUT/'fast_tests.json').read_text()) if (OUT/'fast_tests.json').exists() else {}
    for name in names:
        d=OUT/name
        files=[str((d/x).relative_to(ROOT)).replace('\\','/') for x in
               ('mul_ss.v','tile_thu.sv','ntt_bank_net_s.sv','flex_banked_scratch.sv','ntt_core_gen.sv','ntt_core.sv')]
        args=['verilator','--cc','--exe','--build','-j','2','-O1','-Wno-fatal','--top-module','ntt_core',
              '--Mdir',str((d/'obj').relative_to(ROOT)).replace('\\','/'),
              '-CFLAGS','-D_GLIBCXX_USE_CXX11_ABI=0','-LDFLAGS','-static-libgcc -static-libstdc++',
              *files,(ROOT/'sim/experiments/shared_core_main.cpp').as_posix()]
        command='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; '+' '.join(shlex.quote(x) for x in args)
        run(['C:/msys64/usr/bin/bash.exe','-lc',command],d/'verilator_build.log',timeout=900)
        exe=d/'obj/Vntt_core.exe'
        results[name]={}
        for label,file,count in [('ntt','vectors.txt',48),('fft','vectors_fft.txt',54)]:
            text=run([str(exe),f'sim/core_ntt/{file}'],d/f'{label}_fast.log',timeout=180)
            cases=re.findall(r'^CASE .*$',text,re.M)
            assert len(cases)==count and all('err=0 ' in c for c in cases)
            assert f'TOTAL cases={count} err=0 PASS' in text
            results[name][label]=dict(cases=count,status='PASS',engine='Verilator',records=cases)
            print(name,label,count,'PASS (Verilator)',flush=True)
        # Check that the independent driver rejects an altered expected word.
        fields=(ROOT/'sim/core_ntt/vectors_fft.txt').read_text().splitlines()[0].split()
        n=(1<<int(fields[1])) << (int(fields[0])-3)
        fields[3+n]=f'{int(fields[3+n],16)^1:x}'
        dump(d/'bad_expected.txt',' '.join(fields)+'\n')
        with (d/'driver_mutation.log').open('w') as f:
            proc=subprocess.run([str(exe),str(d/'bad_expected.txt')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=60)
        assert proc.returncode!=0 and 'FAIL' in (d/'driver_mutation.log').read_text()
        results[name]['driver_mutation']='detected'
    dump(OUT/'fast_tests.json',json.dumps(results,indent=2)+'\n')


def report():
    inputs=json.loads((OUT/'inputs.json').read_text())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in inputs.items()),'Production source changed during experiment'
    for i in range(4):
        name=f'root_pack_b{i}.mem'
        assert (ROOT/'hdl/core_ntt'/name).read_bytes()==(OUT/'baseline'/name).read_bytes(),name
    def metrics(path):
        s=path.read_text()
        result={}
        for label,key in [('CLB LUTs','LUT'),('CLB Registers','FF'),('DSPs','DSP'),('Block RAM Tile','BRAM36_equivalent'),('URAM','URAM')]:
            m=re.search(r'^\|\s*'+label+r'\*?\s*\|\s*(\d+(?:\.\d+)?)\s*\|',s,re.M)
            assert m,(path,label)
            result[key]=float(m[1]) if '.' in m[1] else int(m[1])
        return result
    def hier(path):
        rows={}
        for line in path.read_text().splitlines():
            c=[x.strip() for x in line.split('|')[1:-1]]
            if len(c)==11 and c[2].isdigit():rows[c[0]]=dict(LUT=int(c[2]),FF=int(c[6]),DSP=int(c[10]))
        result={k:v for k,v in rows.items() if k in ('ntt_core','(ntt_core)','u_mem','u_net','u_route','u_sel')}
        for label,pattern in [('tiles',r'g_tile\[\d+\]\.u_tile'),('root_rom',r'g_pack\[\d+\]\.u_rom')]:
            selected=[v for k,v in rows.items() if re.fullmatch(pattern,k)]
            assert len(selected)==(16 if label=='tiles' else 4),(path,label,len(selected))
            result[label]={key:sum(v[key] for v in selected) for key in ('LUT','FF','DSP')}
        return result
    result=dict(production_rtl_changed=False,numeric_contract_changed=False,
                common_fix='All experimental variants wait for FFT stage writes to commit.',
                tools=dict(fpga='Vivado2018.1 / xczu7ev-ffvc1156-2-e',simulation=['Icarus','Verilator']),
                test_results={},core_synthesis={},tile_route={},source_inputs_sha256=inputs,
                limitations=['Full-core PPA is synthesis plus opt_design, not routed timing.',
                             'Tile WNS is OOC with registered ports, not system timing.',
                             'No full signer replay or formal all-input equivalence claim.'])
    for name in ('baseline','word32','root_sum'):
        result['test_results'][name]={}
        for label,count in [('ntt',48),('fft',54)]:
            d=OUT/name
            p=d/f'{label}_fast.log' if (d/f'{label}_fast.log').exists() else d/f'{label}.log'
            s=p.read_text();cases=re.findall(r'^CASE .*$',s,re.M)
            assert len(cases)==count and all('err=0 ' in c for c in cases)
            assert f'TOTAL cases={count} err=0 PASS' in s
            result['test_results'][name][label]=dict(cases=count,status='PASS',log=p.relative_to(ROOT).as_posix())
    assert '5000 cycles PASS' in (OUT/'net_test/result.log').read_text()
    result['network_random_cycles']=5000
    result['tile_test_results']={}
    for label,count in [('fft32bf',2940),('fftwbf',11520),('ntt',8055)]:
        for stalled in (0,1):
            p=OUT/'root_sum'/f'tile_{label}_{stalled}.log'
            s=p.read_text()
            total=re.findall(r'^TOTAL.*$',s,re.M)
            assert len(total)==1 and 'err=0 PASS' in total[0],p
            assert re.search(rf'\b{count}\b',total[0]),(p,total)
            result['tile_test_results'][f'{label}_stall{stalled}']=dict(cases=count,status='PASS',log=p.relative_to(ROOT).as_posix())
    for name in ('word32','root_sum'):
        p=OUT/name/'driver_mutation.log'
        assert 'err=1 FAIL' in p.read_text(),p
        result['test_results'][name]['driver_mutation']='detected'
    for name in ('baseline','root_sum'):
        d=OUT/name
        result['core_synthesis'][name]=metrics(d/'core_util.rpt')
        result['core_synthesis'][name]['hierarchy']=hier(d/'core_hier.rpt')
        result['tile_route'][name]=metrics(d/'tile_route_util.rpt')
        s=(d/'tile_timing.rpt').read_text()
        m=re.search(r'WNS\(ns\).*?\n.*?\n\s*([-\d.]+)',s,re.S)
        result['tile_route'][name]['WNS_ns']=float(m[1])
    a,b=result['core_synthesis']['baseline'],result['core_synthesis']['root_sum']
    result['core_delta']={k:dict(absolute=b[k]-a[k],percent=100*(b[k]-a[k])/a[k] if a[k] else None)
                          for k in ('LUT','FF','DSP','BRAM36_equivalent')}
    files=[p for n in ('baseline','word32','root_sum') for p in (OUT/n).glob('*') if p.suffix in ('.sv','.mem','.rpt')]
    result['artifacts_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result['experiment_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['driver_sha256']=hashlib.sha256((ROOT/'sim/experiments/shared_core_main.cpp').read_bytes()).hexdigest()
    dump(ROOT/'study/results/shared_logic_experiment.json',json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('core_synthesis','core_delta','tile_route')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');p.add_argument('--synth',action='store_true')
    p.add_argument('--synth-core',action='store_true');p.add_argument('--net-test',action='store_true')
    p.add_argument('--tile-test',action='store_true')
    p.add_argument('--variants',nargs='+',choices=['baseline','word32','root_sum'],default=['baseline','word32','root_sum'])
    p.add_argument('--fast-test',action='store_true')
    p.add_argument('--report',action='store_true')
    args=p.parse_args()
    if not args.report:build()
    if args.test:test(args.variants)
    if args.synth:synth()
    if args.synth_core:synth_core()
    if args.net_test:test_network()
    if args.tile_test:test_tile_sum()
    if args.fast_test:fast_test(args.variants)
    if args.report:report()
