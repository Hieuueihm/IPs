"""Reuse frozen independent arithmetic vectors with the candidate's physical schedule."""
import importlib.util
import sys
import struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
sp=importlib.util.spec_from_file_location('packed4_build',ROOT/'experiments/a_cg_batch/build.py')
build=importlib.util.module_from_spec(sp);sp.loader.exec_module(build)
build.BUILD=ROOT/'study/build/paper_ablation31/split_domains'
import planner
assert Path(planner.__file__).resolve().parent==HERE
def focused_four_state():
    """Ten changed-path cases; full FFT/scalar coverage stays in the 1026-case AXI suite."""
    p=build.BUILD
    data=(p/'four_state.bin').read_bytes()
    w=struct.unpack('<'+'I'*(len(data)//4),data)
    pos=2;chosen=[]
    for _ in range(w[1]):
        start=pos
        fft,fmt,ln,hm,inv,q,qi,native,packed,jl,stages,roots,nwords=w[pos:pos+13]
        pos+=13+4*stages+16*roots+2*nwords
        if packed and ((q==12289 and hm==0 and ln in (1,10)) or (q==3329 and ln==8 and hm==1)):
            chosen.append(w[start:pos])
    assert pos==len(w) and len(chosen)==10
    out=[w[0],len(chosen)]+[v for rec in chosen for v in rec]
    (p/'four_state_packed.bin').write_bytes(struct.pack('<'+'I'*len(out),*out))

if __name__=='__main__':
    build.fixtures()
    focused_four_state()
