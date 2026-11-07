"""Private fixtures: identical math payloads, variant-specific legal schedules."""
import importlib.util
import json
import shutil
import struct
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
name=sys.argv[1]
variant=HERE/'variants'/name
BUILD=ROOT/'study/build/paper_ablation31'/name
BUILD.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(variant))
if name!='dedicated_mont32':
    base=ROOT/('study/build/a_cg_z020_perf160' if name in ['single_stream','sparse_feed'] else 'study/build/a_cg_packed4')
    for f in ['fixtures.bin','fixtures.json','four_state.bin']:shutil.copy2(base/f,BUILD/f)
    print('REUSED_IDENTICAL_VALIDATED_MATH_FIXTURES',name,base,flush=True)
else:
    sp=importlib.util.spec_from_file_location('ablation_build',ROOT/'experiments/a_cg_batch/build.py')
    build=importlib.util.module_from_spec(sp);sp.loader.exec_module(build);build.BUILD=BUILD
    import planner
    assert Path(planner.__file__).resolve().parent==variant
    build.fixtures()
# The focused four-state subset covers changed packed behavior, scalar NTT32
# and all three FFT precisions; this is independent of Verilator's two-state run.
data=(BUILD/'four_state.bin').read_bytes();w=struct.unpack('<'+'I'*(len(data)//4),data)
pos=2;chosen=[];keys=set()
for _ in range(w[1]):
    start=pos
    fft,fmt,ln,hm,inv,q,qi,native,packed,jl,stages,roots,nwords=w[pos:pos+13]
    pos+=13+4*stages+16*roots+2*nwords
    key=(fft,fmt,inv,native,packed,q,hm,jl)
    selected=(packed and jl==0 and ((q==12289 and ln==10) or(q==3329 and ln==8)))
    selected=selected or (not fft and not packed and q==8380417 and ln==8 and jl==1)
    selected=selected or (fft and ln==10 and not native)
    if selected and key not in keys:chosen.append(w[start:pos]);keys.add(key)
assert pos==len(w)
out=[w[0],len(chosen)]+[x for rec in chosen for x in rec]
(BUILD/'focused.bin').write_bytes(struct.pack('<'+'I'*len(out),*out))
print('FOCUSED_CASES',len(chosen),flush=True)
