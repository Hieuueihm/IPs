"""Check decoupled AXI channels, strobes, backpressure and complete kernels."""
import hashlib
import json
from pathlib import Path
import subprocess
from validate_kernel_engine import ROOT,BUILD,SOURCES,load_cases,write_requests


def main():
    cases,_=load_cases(True);selected=[]
    for op in ('FFT','IFFT','CMUL','SPLIT','MERGE','NTT','INTT','TOMONT','MODMUL'):
        for width,profile in ((2,0),) if op in ('FFT','IFFT','CMUL','SPLIT','MERGE') else ((0,0),(0,1)):
            selected.append(next(c for c in cases if c['op']==op and c['logn']==3 and c['width']==width and c['profile']==profile))
    for width in (0,1):
        selected.append(next(c for c in cases if c['op']=='FFT' and c['logn']==3 and c['width']==width))
    dest=BUILD/'axil_requests.txt';write_requests(selected,dest)
    files=[*SOURCES,'hdl/core/flex_kernel_axil.sv','sim/src/tb_kernel_axil.sv']
    p=subprocess.run(['iverilog','-g2012','-s','tb_kernel_axil','-I','hdl/proto','-o',str(BUILD/'axil.vvp'),*files],cwd=ROOT,capture_output=True,text=True)
    (BUILD/'axil_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    p=subprocess.run(['vvp',str(BUILD/'axil.vvp'),'+vectors='+str(dest)],cwd=ROOT,capture_output=True,text=True,timeout=240)
    (BUILD/'axil_sim.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
    assert f'PASS AXI kernels={len(selected)}' in p.stdout,p.stdout
    result={'kernels':len(selected),'output':p.stdout.strip(),'sha256':{str((ROOT/f).relative_to(ROOT)):hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in [*files,'hdl/core/rom/ntt_init.vh','scripts/validate_kernel_axil.py']}}
    (ROOT/'study/results/kernel_axil.json').write_text(json.dumps(result,indent=2)+'\n');print(p.stdout,flush=True)


if __name__=='__main__':main()
