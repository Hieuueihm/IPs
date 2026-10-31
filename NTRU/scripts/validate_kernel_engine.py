"""Compile autonomous RTL and compare complete kernels, not host arithmetic frames."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'study/build/kernel_engine'
OPS=('FFT','IFFT','CMUL','SPLIT','MERGE','NTT','INTT','TOMONT','MODMUL')
FP=set(OPS[:5])
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_stream_tile.sv','hdl/proto/flex_stream_array.sv',
    'hdl/proto/ntt_bank_permute64.sv','hdl/core/flex_banked_scratch.sv',
    'hdl/core/flex_kernel_rom.sv','hdl/core/flex_kernel_engine.sv']
sys.path.insert(0,str(ROOT))
from model.r8_golden import Core,parse_word
from model.fixed_kernel_oracle import evaluate as narrow_kernel


def run(args,**kw):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,**kw)
    if p.returncode:raise RuntimeError(f'{args}\n{p.stdout[-2000:]}\n{p.stderr[-5000:]}')
    return p


def build():
    BUILD.mkdir(parents=True,exist_ok=True)
    cmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 4 -O2 -Wno-fatal --top-module flex_kernel_engine -Ihdl/proto --Mdir study/build/kernel_engine/obj -CFLAGS "-D_GLIBCXX_USE_CXX11_ABI=0" -LDFLAGS "-static-libgcc -static-libstdc++" '+ ' '.join(SOURCES)+' '+str(ROOT/'sim/src/kernel_engine_main.cpp').replace('\\','/')
    p=run(['C:/msys64/usr/bin/bash.exe','-lc',cmd],timeout=1800)
    (BUILD/'build.log').write_text(p.stdout+'\n'+p.stderr)
    (BUILD/'build_manifest.json').write_text(json.dumps({'sha256':source_hashes()},indent=2)+'\n')
    print('Built compiled RTL model',flush=True)


def source_hashes():
    files=[*(ROOT/s for s in SOURCES),ROOT/'hdl/proto/mont_reduce16_functions.vh',ROOT/'sim/src/kernel_engine_main.cpp',*sorted((ROOT/'hdl/core/rom').glob('*.mem')),ROOT/'hdl/core/rom/ntt_init.vh']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def load_cases(full=False):
    cases=[];mapping={};rng=random.Random(20261027)
    def add(rec,width=2,profile=0,origin='r8_synthetic'):
        case=dict(rec);case.update(width=width,profile=profile,origin=origin);cases.append(case);return len(cases)-1
    with gzip.open(ROOT/'study/vectors/r8/synthetic.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line)
            if r.get('type')=='kernel':add(r)
    if not full:cases[:]=[c for c in cases if c['logn']<=5][:80]
    fft=json.loads((ROOT/'study/vectors/r8/twiddle_q64_64.json').read_text())
    rom=[parse_word(x) for row in fft['roots'] for x in row['forward'][:2]]
    for code,width in enumerate((32,64)):
        for logn in range(1,11 if full else 6):
            n=1<<logn
            for op in OPS[:5]:
                na=n//2 if op=='MERGE' else n
                nb=na if op in ('MERGE','CMUL') else 0
                a=[rng.getrandbits(width) for _ in range(na)];b=[rng.getrandbits(width) for _ in range(nb)]
                y=narrow_kernel(op,a,b,logn,width,rom)
                add({'op':op,'logn':logn,'a':[f'{v:032x}' for v in a],'b':[f'{v:032x}' for v in b],
                    'out':[f'{v:032x}' for v in y]},code,0,'custom_narrow_contract')
    # Both Montgomery profiles, complete and incomplete transforms. Scalar
    # oracle applies mathematical radix-2 layers, independently of bank mapping.
    with (ROOT/'study/build/pqc_application/N512/capture/trace.jsonl').open() as f:
        nt=next(json.loads(line) for line in f if '"type":"ntt_rom"' in line)
    for profile,q in enumerate((12289,3329)):
        for logn in range(3,(11 if full and not profile else 9 if full else 7)):
            n=1<<logn;inc=profile==1 and n==256
            table=nt['forward'] if profile==0 else [65536*pow(17,int(f'{i:07b}'[::-1],2),q)%q for i in range(128)]
            rinv=pow(65536,-1,q);fw=[];stride=n//2;groups=1
            while stride>=(2 if inc else 1):
                fw.append([(i,i+stride,table[groups+g]*rinv%q) for g in range(groups) for i in range(2*g*stride,(2*g+1)*stride)])
                stride//=2;groups*=2
            bw=[[(i,j,pow(w,-1,q)) for i,j,w in layer] for layer in reversed(fw)]
            for op in OPS[5:]:
                a=[rng.randrange(q) for _ in range(n)];b=[rng.randrange(q) for _ in range(n)] if op=='MODMUL' else []
                y=a[:]
                if op in ('NTT','INTT'):
                    for layer in (bw if op=='INTT' else fw):
                        for i,j,w in layer:
                            u,v=y[i],y[j]
                            y[i],y[j]=((u+v)%q,(u-v)*w%q) if op=='INTT' else ((u+v*w)%q,(u-v*w)%q)
                    if op=='INTT':y=[v*pow(1<<(logn-int(inc)),-1,q)%q for v in y]
                elif op=='TOMONT':y=[v*65536%q for v in a]
                else:y=[v*w*pow(65536,-1,q)%q for v,w in zip(a,b)]
                add({'op':op,'logn':logn,'a':a,'b':b,'out':y},0,profile,'modular_oracle')
    if full:
        for n in (512,1024):
            ids=[]
            with (ROOT/f'study/build/pqc_application/N{n}/capture/trace.jsonl').open() as f:
                for line in f:
                    r=json.loads(line)
                    if r.get('type')=='kernel':ids.append(add(r,2 if r['op'] in FP else 0,0,f'application_N{n}'))
            mapping[n]=ids
    return cases,mapping


def as_ints(case,key):
    return [int(x,16) if isinstance(x,str) else x for x in case.get(key,[])]


def write_requests(cases,path=None):
    p=path or BUILD/'requests.txt'
    with p.open('w') as f:
        for c in cases:
            a=as_ints(c,'a');b=as_ints(c,'b');y=as_ints(c,'out')+as_ints(c,'out1')
            f.write(f'{OPS.index(c["op"])} {c["width"]} {c["logn"]} {c["profile"]} {len(a)} {len(b)} {len(y)}\n')
            for values in (a,b,y):f.write(' '.join(f'{v:032x}' for v in values)+'\n')
    return p


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--full',action='store_true');ap.add_argument('--no-build',action='store_true');args=ap.parse_args()
    start=time.monotonic();BUILD.mkdir(parents=True,exist_ok=True)
    if not args.no_build:build()
    else:assert json.loads((BUILD/'build_manifest.json').read_text())['sha256']==source_hashes(),'RTL changed: rebuild required'
    cases,mapping=load_cases(args.full);req=write_requests(cases)
    print(f'Running {len(cases)} whole kernels',flush=True)
    p=run([BUILD/'obj/Vflex_kernel_engine.exe',req,BUILD/'actual.txt'],cwd=ROOT,timeout=1200)
    (BUILD/'simulation.log').write_text(p.stdout+'\n'+p.stderr)
    result=json.loads(p.stdout.strip().splitlines()[-1]);result['seconds']=time.monotonic()-start
    result['op_counts']=dict(Counter(c['op'] for c in cases));result['full']=args.full
    result['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [*(ROOT/s for s in SOURCES),ROOT/'hdl/proto/mont_reduce16_functions.vh',ROOT/'sim/src/kernel_engine_main.cpp',ROOT/'scripts/validate_kernel_engine.py',ROOT/'model/fixed_kernel_oracle.py',ROOT/'hdl/core/rom/ntt_init.vh',*sorted((ROOT/'hdl/core/rom').glob('*.mem')),req,BUILD/'actual.txt',BUILD/'build_manifest.json']}
    (BUILD/'cases.json').write_text(json.dumps(cases));(BUILD/'mapping.json').write_text(json.dumps(mapping))
    (ROOT/'study/results/kernel_engine.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result|{'sha256':'recorded'},indent=2),flush=True)


if __name__=='__main__':main()
