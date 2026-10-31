"""Fast arithmetic-bank RTL experiment; simulation plus optional generic synthesis.

python -X utf8 scripts/prototype_arith.py [--synth]
No full transform scheduler, complex-3M issue controller or RAM is implemented.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
from random import Random
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
BUILD=ROOT/'study/build/arith_proto'
RESULT=ROOT/'study/results'
MASK=(1<<128)-1
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_arith_bank.sv']
NTT_LANES={'proto_r32':16,'proto_f16_common':16,'proto_f16_mid':32,'proto_f16_wide':64}
TOPS=list(NTT_LANES)

def run(cmd,**kw):
    return subprocess.run([str(c) for c in cmd],check=True,**kw)

def signed(x,w):
    x%=1<<w
    return x-(1<<w) if x>>(w-1) else x

def pack(vals,w):
    return sum((v% (1<<w))<<(i*w) for i,v in enumerate(vals))

def generate():
    rng=Random(20261025)
    vectors=[]
    c_groups=[]
    counts=Counter()
    def add(mode,x,y,z,p,u,v):
        counts[mode]+=1
        vectors.append((mode,x,y,z,p,u,v))
        return len(vectors)-1
    for iteration in range(192):
        # Alternate all modes to exercise registered control and output packing.
        for mode,w,n in [(0,16,64),(1,32,16),(2,64,4),(3,128,1)]:
            if mode==0:
                q=12289
                a=[rng.randrange(q) for _ in range(n)]
                b=[rng.randrange(q) for _ in range(n)]
                z=[rng.randrange(q) for _ in range(n)]
                if iteration<3:
                    a=[(0,1,q-1)[iteration]]*n
                    b=[(q-1,0,q-1)[iteration]]*n
                p=[x*y*pow(1<<16,-1,q)%q for x,y in zip(a,b)]
                u=[(x+y)%q for x,y in zip(z,p)]
                v=[(x-y)%q for x,y in zip(z,p)]
            else:
                a=[rng.getrandbits(w) for _ in range(n)]
                b=[rng.getrandbits(w) for _ in range(n)]
                z=[rng.getrandbits(w) for _ in range(n)]
                if iteration<8:
                    edge=[0,1,-1,-(1<<(w-1)),(1<<(w-1))-1,1<<(w//2-1),-(1<<(w//2-1)),1<<(w//2)]
                    a=[edge[iteration]]*n; b=[edge[7-iteration]]*n
                p=[signed((signed(x,w)*signed(y,w)+(1<<(w//2-1)))>>(w//2),w) for x,y in zip(a,b)]
                u=[signed(x+y,w) for x,y in zip(z,p)]
                v=[signed(x-y,w) for x,y in zip(z,p)]
            add(mode,*[pack(t,w) for t in (a,b,z,p,u,v)])
    # Real RTL products recombined into 3M and checked against captured C CMUL.
    with gzip.open(ROOT/'study/vectors/r8/synthetic.jsonl.gz','rt') as f:
        for line in f:
            rec=json.loads(line)
            if rec.get('op')!='CMUL':continue
            n=1<<rec['logn']; hn=n//2
            for index in sorted({0,hn//2,hn-1}):
                ar,ai=[signed(int(rec['a'][k],16),128) for k in (index,index+hn)]
                br,bi=[signed(int(rec['b'][k],16),128) for k in (index,index+hn)]
                ids=[]
                for x,y in [(ar,br),(ai,bi),(signed(ar+ai,128),signed(br+bi,128))]:
                    p=signed((x*y+(1<<63))>>64,128)
                    ids.append(add(3,x&MASK,y&MASK,0,p&MASK,p&MASK,(-p)&MASK))
                c_groups.append({'ids':ids,'re':int(rec['out'][index],16),
                                 'im':int(rec['out'][index+hn],16)})
    path=BUILD/'vectors.txt'
    with path.open('w') as f:
        for mode,*values in vectors:
            f.write(str(mode)+' '+' '.join(f'{v:0256x}' for v in values)+'\n')
    return counts,c_groups,len(vectors)

def simulate():
    counts,groups,total=generate()
    exe=BUILD/'sim.vvp'
    run(['iverilog','-g2012','-s','tb_flex_arith_bank','-o',exe,*[ROOT/s for s in SOURCES],ROOT/'sim/src/tb_flex_arith_bank.sv'])
    r=run(['vvp',exe,f'+vectors={(BUILD/"vectors.txt").as_posix()}',f'+actual={(BUILD/"actual.txt").as_posix()}'],capture_output=True,text=True)
    print(r.stdout,flush=True)
    (BUILD/'simulation.log').write_text(r.stdout+r.stderr)
    actual={int(i):int(p,16) for i,p in (line.split() for line in (BUILD/'actual.txt').read_text().splitlines())}
    assert len(actual)==total
    for g in groups:
        p0,p1,p2=[actual[i]&MASK for i in g['ids']]
        assert (p0-p1)&MASK==g['re']
        assert (p2-p0-p1)&MASK==g['im']
    print(f'PASS: {len(groups)} composed RTL 3M results match actual C vectors.',flush=True)
    return {'transactions':total,'configurations':len(TOPS),'by_mode':dict(counts),
            'c_complex_products':len(groups),'mismatches':0,
            'note':'3M sequencing/recombination is performed by the test driver, not a synthesized complex butterfly.'}

def synthesize(yosys=None):
    native=yosys or shutil.which('yosys')
    if native:
        cmd=[native]
    else:
        python=Path('C:/Users/gbmhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
        if not python.exists():raise RuntimeError('Set up native Yosys or the documented local YoWASP environment.')
        cmd=[str(python),'-X','utf8',str(ROOT/'scripts/yosys_local.py')]
    weights={'$_BUF_':.67,'$_NOT_':.67,'$_NAND_':1.,'$_NOR_':1.,'$_AND_':1.33,'$_OR_':1.33,
             '$_ANDNOT_':1.33,'$_ORNOT_':1.33,'$_XOR_':2.33,'$_XNOR_':2.33,'$_MUX_':2.33}
    version=run([*cmd,'-V'],capture_output=True,text=True).stdout.strip()
    def one(top):
        net=BUILD/f'{top}.json'; stat=BUILD/f'{top}_stat.json'; depth=BUILD/f'{top}_ltp.txt'
        script='\n'.join([
            'read_verilog -sv '+' '.join((ROOT/s).as_posix() for s in SOURCES),
            f'hierarchy -check -top {top}',f'synth -flatten -noabc -top {top}',
            'abc -fast -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX','opt_clean -purge',
            f'tee -q -o {stat.as_posix()} stat -json',f'tee -q -o {depth.as_posix()} ltp -noff'])
        ys=BUILD/f'{top}.ys'; ys.write_text(script)
        start=time.monotonic()
        print(f'Synthesizing {top} ...',flush=True)
        log=subprocess.run([*cmd,'-Q','-l',(BUILD/f'{top}_live.log').as_posix(),'-s',ys.as_posix()],capture_output=True,text=True,errors='replace')
        (BUILD/f'{top}.log').write_text(log.stdout+log.stderr,encoding='utf-8')
        if log.returncode:
            raise RuntimeError(f'Yosys failed: {log.stderr[-4000:]} (see {BUILD / (top+".log")})')
        data=json.loads(stat.read_text())
        mod=next(iter(data['modules'].values()))
        cells=mod['num_cells_by_type']; ff=sum(n for k,n in cells.items() if 'DFF' in k)
        unknown={k:v for k,v in cells.items() if k not in weights and 'DFF' not in k}
        assert not unknown,unknown
        comb=sum(weights.get(k,0)*n for k,n in cells.items())
        match=re.search(r'length=(\d+)',depth.read_text())
        row={'top':top,'comb_ge':round(comb,1),'ff':ff,'total_ge':round(comb+4.67*ff,1),
             'depth_cells':int(match.group(1)) if match else None,'unknown':unknown,
             'synthesis_seconds':round(time.monotonic()-start,1),'tool':version,'mapping':'abc -fast -g generic gates'}
        print(json.dumps(row),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(one,TOPS))
    (RESULT/'arith_proto_synth_partial.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows

def report(sim,rows):
    result={'simulation':sim,'synthesis':rows,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                             for name in [*SOURCES,'sim/src/tb_flex_arith_bank.sv']},
            'capacity':{'FFT32_real_products_per_cycle':16,'FFT64_real_products_per_cycle':4,
                        'FFT128_real_products_per_cycle':1,'NTT_lanes':list(NTT_LANES.values())},
            'limits':['Arithmetic bank only; no complex 3M controller, transform memory or scheduler.',
                      'Generic gate depth is not frequency, nanoseconds or target-library STA.',
                      'GE is approximate NAND2 equivalent; no measured power/energy.',
                      'NTT32/64 lane throughput requires 1024/2048 data bits per direction plus twiddle bandwidth.']}
    (RESULT/'arith_proto.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Prototype arithmetic bank: F16 / R32','',
           f'- Simulation: {sim["transactions"]} transactions ×{sim["configurations"]} configurations; 0 mismatches.',
           f'- {sim["c_complex_products"]} complex 3M results recomposed from RTL products match actual C R8.',
           '- Input/output registers: II=1, two sampled clock edges; bubbles and mode changes checked.',
           '', '| Top | Comb GE | FF | Total GE | Longest gate path | NTT16 lanes |',
           '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lanes=NTT_LANES[r['top']]
        lines.append(f'| {r["top"]} | {r["comb_ge"]} | {r["ff"]} | {r["total_ge"]} | {r["depth_cells"]} | {lanes} |')
    if len(rows)==len(TOPS):
        base=rows[0]
        lines += ['', '| Top | Total GE / R32 | Peak NTT capacity / R32 | Peak NTT per GE / R32 |',
                  '|---|---:|---:|---:|']
        for r in rows:
            capacity=NTT_LANES[r['top']]/NTT_LANES[base['top']]
            area=r['total_ge']/base['total_ge']
            lines.append(f'| {r["top"]} | {area:.3f}× | {capacity:.1f}× | {capacity/area:.3f}× |')
        lines += ['', 'Peak capacity assumes equal clock and full bandwidth; it is not measured speedup.',
                  '',f'Tool: `{base["tool"]}`. Flow: `synth -flatten -noabc`, `abc -fast -g` generic gates.',
                  'GE: approximate weights from the tile study; registers counted at 4.67 GE/bit.',
                  '', 'One-bank bandwidth ceilings (data read/write each direction, twiddle separate):',
                  '', '| Data bit/cycle | R32 NTT BF/cycle | F16 common | F16 mid | F16 wide |',
                  '|---:|---:|---:|---:|---:|','| 512 | 16 | 16 | 16 | 16 |',
                  '| 1024 | 16 | 16 | 32 | 32 |','| 2048 | 16 | 16 | 32 | 64 |']
    lines += ['', 'Limits:', '']+[f'- {s}' for s in result['limits']]
    (RESULT/'arith_proto.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synth',action='store_true')
    parser.add_argument('--yosys',help='path to native Yosys')
    parser.add_argument('--synth-only',action='store_true',help='reuse simulation if RTL/testbench have not changed')
    args=parser.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True); RESULT.mkdir(parents=True,exist_ok=True)
    if args.synth_only:
        for file in [*SOURCES,'sim/src/tb_flex_arith_bank.sv']:
            if (ROOT/file).stat().st_mtime>(BUILD/'sim.vvp').stat().st_mtime:
                raise RuntimeError('RTL changed after simulation; run simulation first.')
        sim=json.loads((RESULT/'arith_proto.json').read_text())['simulation']
    else:
        sim=simulate()
        report(sim,[])
    rows=synthesize(args.yosys) if args.synth or args.synth_only else []
    if rows:report(sim,rows)
