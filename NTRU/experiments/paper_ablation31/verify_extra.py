"""Additional private four-state/reset checks, without touching pinned evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('--reset-only',action='store_true');args=p.parse_args()
rtl=HERE/'variants'/args.variant/'rtl'
out=ROOT/'study/build/paper_ablation31'/args.variant
fixture=out/'focused.bin'
if args.variant in ['separate_history','sparse_feed','dedicated_mont32'] and not args.reset_only:
    b=fixture.read_bytes();w=struct.unpack('<'+'I'*(len(b)//4),b);pos=2;chosen=[]
    for _ in range(w[1]):
        begin=pos;h=w[pos:pos+13];ns,nr,nw=h[10:];pos+=13+4*ns+16*nr+2*nw
        wanted=h[8] if args.variant!='dedicated_mont32' else not h[0] and not h[8]
        if wanted:chosen.append(w[begin:pos])
    assert pos==len(w) and chosen
    words=[w[0],len(chosen)]+[v for r in chosen for v in r]
    fixture=out/'changed_paths.bin';fixture.write_bytes(struct.pack('<'+'I'*len(words),*words))
checks=[('reset','tb_acg_axil_reset',ROOT/'experiments/a_cg_z020_system160/tb_axil_reset.sv',[])]
if not args.reset_only:
    checks.insert(0,('four_state','tb_four_state',ROOT/'experiments/a_cg_z020_perf160/tb_four_state.sv',
                     ['+FIXTURE='+str(fixture.resolve()).replace('\\','/')]))
results={}
for name,top,tb,runargs in checks:
    exe=out/(name+'.vvp')
    cmd=['C:/iverilog/bin/iverilog.exe','-g2012','-s',top,'-o',str(exe)]+[str(rtl/f) for f in ['mul_ss.v','tile_a.sv','a_cg_fast.sv','a_cg_axil.v']]+[str(tb)]
    with (out/(name+'_compile.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/(name+'.log')).open('w') as f:subprocess.run(['C:/iverilog/bin/vvp.exe',str(exe),*runargs],stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(out/(name+'.log')).read_text()
    assert 'PASS' in log,log[-1000:]
    results[name]=log.splitlines()[-2:]
    print(args.variant,name,'PASS',flush=True)
(out/'extra_verified.json').write_text(json.dumps(results,indent=2)+'\n')
