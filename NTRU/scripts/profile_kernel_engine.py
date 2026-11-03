"""Measure unchanged full-kernel RTL: cycles, logical lane use, waits and bank beats."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import time
from validate_kernel_engine import ROOT,SOURCES,OPS

BUILD=ROOT/'study/build/kernel_profile'
BASE=ROOT/'study/build/kernel_engine'
RESULT=ROOT/'study/results/kernel_profile.json'
STATES=['IDLE','FREAD','FWAIT','PREP','ISSUE','WAITP','COMBINE','FWRITE','ADVANCE',
    'NREAD','NWAIT','NISSUE','NRESULT','NWRITE','NADVANCE','SREAD','SWAIT','SWRITE',
    'COPYREAD','COPYWAIT','COPYWRITE','DONE']
MONITOR=['sim/src/flex_kernel_profile.sv','sim/src/kernel_profile_main.cpp']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(cmd,**kw):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,**kw)
    if p.returncode:raise RuntimeError(p.stdout[-1500:]+'\n'+p.stderr[-5000:])
    return p


def sources():
    files=[*(ROOT/s for s in SOURCES+MONITOR),ROOT/'hdl/proto/mont_reduce16_functions.vh',
        *sorted((ROOT/'hdl/core/rom').glob('*.mem')),ROOT/'hdl/core/rom/ntt_init.vh']
    return {str(p.relative_to(ROOT)):sha(p) for p in files}


def build():
    cmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module flex_kernel_profile -Ihdl/proto --Mdir study/build/kernel_profile/obj -CFLAGS "-D_GLIBCXX_USE_CXX11_ABI=0" -LDFLAGS "-static-libgcc -static-libstdc++" '+' '.join(SOURCES+[MONITOR[0]])+' '+(ROOT/MONITOR[1]).as_posix()
    p=execute(['C:/msys64/usr/bin/bash.exe','-lc',cmd],timeout=1800)
    (BUILD/'build.log').write_text(p.stdout+'\n'+p.stderr)
    (BUILD/'build_manifest.json').write_text(json.dumps({'sha256':sources()},indent=2)+'\n')
    print('Built read-only RTL monitor',flush=True)


def load_stats(path):
    with path.open() as f:return [{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]


def summarize(rows):
    c=[sum(r[f'c{i}'] for r in rows) for i in range(96)]
    cycles=c[0];frames=sum(c[2:6]);fft=c[2];ntt=sum(c[3:6]);n=len(rows)
    pct=lambda x,d:100*x/d if d else None
    return {'kernels':n,'cycles':cycles,'cycles_min':min(r['c0'] for r in rows),'cycles_max':max(r['c0'] for r in rows),
        'pause_cycles':c[1],'fft_real_frames':fft,'ntt_pair_frames':c[3],'ntt_tail_frames':c[4],
        'ntt_scalar_frames':c[5],'frames':frames,'frame_issue_duty_pct':pct(frames,cycles),
        'assigned_leaf_products':c[6],'leaf_use_over_kernel_pct':pct(c[6],64*cycles),
        'leaf_use_per_issued_frame_pct':pct(c[6],64*frames),
        'fft_lane_use_per_fft_frame_pct':pct(c[69],c[70]),
        'ntt_active_tiles_per_frame_pct':pct(c[71],c[72]),
        'input_ready_blocked_cycles':c[7],'waiting_result_empty_cycles':c[8],
        'output_backpressure_cycles':c[9],'array_advance_blocked_cycles':c[10],
        'data_read_bank_beats':c[11],'data_write_bank_beats':c[12],
        'root_bundle_bank_reads':c[13],'fft_root_reads':c[14],'consumed_frames':c[15],
        'fifo_peak':max(r['c60'] for r in rows),'fifo_nonempty_cycles':c[61],
        'read_beats_by_store':c[62:65],'write_beats_by_store':c[65:68],
        'state_cycles':{s:c[16+i] for i,s in enumerate(STATES) if c[16+i]},
        'active_state_cycles':{s:c[38+i] for i,s in enumerate(STATES) if c[38+i]}}


def validate(rows,cases):
    assert len(rows)==len(cases)==5992
    for i,(r,case) in enumerate(zip(rows,cases)):
        assert [r[k] for k in ('id','op','width','logn','profile')]==[i,OPS.index(case['op']),case['width'],case['logn'],case['profile']]
        assert sum(r[f'c{16+j}'] for j in range(22))==r['c0']
        assert sum(r[f'c{38+j}'] for j in range(22))==r['c0']-r['c1']
        assert sum(r[f'c{j}'] for j in range(2,6))==r['c15']
        n=1<<case['logn'];op=case['op']
        if op in ('FFT','IFFT'):
            products=3*(n//4)*(case['logn']-1) if n>=4 else 0
        elif op=='CMUL':products=3*n//2
        elif op in ('SPLIT','MERGE'):products=3*n//4 if n>=4 else 0
        else:products=0
        assert r['c2']==products,(i,'real product count')
        if op in OPS[:5]:assert r['c6']==products*(4<<(2*case['width']))
        else:
            levels=case['logn']-int(case['profile']==1 and n==256)
            warps=max(1,n//64)
            if op in ('NTT','INTT'):
                assert r['c3']==(levels//2)*warps and r['c4']==(levels%2)*warps
                assert r['c5']==(warps if op=='INTT' else 0)
                assert r['c6']==n*levels//2+(n if op=='INTT' else 0)
            else:assert r['c5']==warps and r['c6']==n


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--no-build',action='store_true');args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    baseline=json.loads((ROOT/'study/results/kernel_engine.json').read_text())
    for name,digest in baseline['sha256'].items():assert sha(ROOT/name)==digest,('stale baseline',name)
    cases=json.loads((BASE/'cases.json').read_text());req=BASE/'requests.txt'
    if not args.no_build:build()
    else:assert json.loads((BUILD/'build_manifest.json').read_text())['sha256']==sources()
    runs={};raw=[]
    for name,pause in (('no_pause',0),('random_pause',1)):
        print(f'Profiling {name}: {len(cases)} complete kernels',flush=True)
        actual=BUILD/f'{name}_actual.txt';stats=BUILD/f'{name}.csv'
        p=execute([BUILD/'obj/Vflex_kernel_profile.exe',req,actual,stats,pause],cwd=ROOT,timeout=1200)
        (BUILD/f'{name}.log').write_text(p.stdout+'\n'+p.stderr)
        assert sha(actual)==sha(BASE/'actual.txt'),'monitor/pause changed an output'
        rows=load_stats(stats);validate(rows,cases);raw.append(rows)
        groups=defaultdict(list)
        for r in rows:groups[(r['op'],r['width'],r['logn'],r['profile'])].append(r)
        by_config=[]
        for (op,width,logn,profile),items in sorted(groups.items()):
            summary=summarize(items)
            if not pause:assert summary['cycles_min']==summary['cycles_max'],'data-dependent cycle count'
            by_config.append({'op':OPS[op],'width_bits':(32,64,128)[width] if op<5 else 16,
                'q':None if op<5 else (12289,3329)[profile],'n':1<<logn,**summary})
        origins=defaultdict(list)
        for r,c in zip(rows,cases):origins[c['origin']].append(r)
        runs[name]={'overall':summarize(rows),'by_config':by_config,
            'by_origin':{key:summarize(items) for key,items in origins.items()},
            'simulation':json.loads(p.stdout.strip().splitlines()[-1])}
        print(f'{name}: {runs[name]["overall"]["cycles"]:,} kernel cycles, outputs identical',flush=True)
    # Capacity lower bounds, not RTL measurements of alternative arrays.
    bounds=[]
    for tiles in (1,2,4,8,16,32):
        leaves=tiles*4
        bounds.append({'tiles':tiles,'leaves16x16':leaves,
            'fft32_real_products_per_cycle_capacity':leaves//4,
            'fft64_real_product_min_issue_beats':max(1,(16+leaves-1)//leaves),
            'fft128_real_product_min_issue_beats':max(1,(64+leaves-1)//leaves),
            'ntt_pair_coefficients_per_cycle_capacity':4*tiles,
            'ntt_pair_coefficients_single_read_bound_64banks':min(64,4*tiles)})
    files=[*(ROOT/s for s in SOURCES+MONITOR),ROOT/'scripts/profile_kernel_engine.py',
        ROOT/'hdl/proto/mont_reduce16_functions.vh',ROOT/'hdl/core/rom/ntt_init.vh',
        *sorted((ROOT/'hdl/core/rom').glob('*.mem')),BUILD/'no_pause.csv',BUILD/'random_pause.csv',
        BUILD/'no_pause_actual.txt',BUILD/'random_pause_actual.txt',BUILD/'build_manifest.json',req]
    result={'scope':'Measured unchanged 16-tile RTL; alternative tile counts are analytical capacity bounds only.',
        'tiles':16,'leaf_multipliers_16x16':64,'runs':runs,'capacity_bounds_not_rtl_sweep':bounds,
        'source_and_evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},
        'baseline_result_sha256':sha(ROOT/'study/results/kernel_engine.json'),'seconds':time.monotonic()-start}
    RESULT.write_text(json.dumps(result,indent=2)+'\n');print(f'Saved {RESULT}',flush=True)


if __name__=='__main__':main()
