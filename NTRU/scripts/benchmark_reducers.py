"""Compare exact original/CSA/compact Montgomery in isolation and a shared cluster."""
import argparse
import importlib.util
import json
from pathlib import Path
from random import Random
from arith_experiment_common import ROOT,run,hashes,check_hashes,synthesize

BUILD=ROOT/'study/build/reducer_compare'
RESULT=ROOT/'study/results/reducer_compare.json'
INCLUDE='hdl/proto/mont_reduce16_functions.vh'
SOURCES=['hdl/mul_ss.v','hdl/proto/mont_reduce16_bench.sv','hdl/proto/flex_reduce_cluster.sv']
TBS=['sim/src/tb_mont_reducers.sv','sim/src/tb_reduce_cluster.sv']
TOPS=[f'reduce_{impl}_{profile}' for profile in ('dynamic','q12289','q3329')
      for impl in ('original','csa','compact')]+[f'reduce_cluster_{impl}' for impl in ('original','csa','compact')]

def compile_run(top,tb,vectors,actual=None):
    exe=BUILD/(top+'.vvp')
    run(['iverilog','-g2012','-I',ROOT/'hdl/proto','-s',top,'-o',exe,*[ROOT/s for s in SOURCES],ROOT/tb])
    args=['vvp',exe,f'+vectors={vectors.as_posix()}']
    if actual:args.append(f'+actual={actual.as_posix()}')
    r=run(args,capture_output=True,text=True)
    (BUILD/(top+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    print(r.stdout,flush=True)

def simulate():
    rng=Random(20261026);vectors=[]
    for low in range(65536):
        for profile,q in enumerate((12289,3329)):
            vectors.append((profile,low,low*pow(65536,-1,q)%q))
    for profile,q in enumerate((12289,3329)):
        maximum=(q-1)**2
        cases=[0,1,maximum,maximum-1,65535,65536,65537]
        for high in (0,1,maximum>>16):
            for low in (0,1,65535):
                t=(high<<16)+low
                if t<=maximum:cases.append(t)
        cases.extend(rng.randrange(maximum+1) for _ in range(4096))
        vectors.extend((profile,t,t*pow(65536,-1,q)%q) for t in cases)
    path=BUILD/'reducers.txt'
    path.write_text(''.join(f'{p:x} {t:07x} {e:04x}\n' for p,t,e in vectors))
    compile_run('tb_mont_reducers',TBS[0],path)
    spec=importlib.util.spec_from_file_location('reference',ROOT/'scripts/prototype_ntt_cluster.py')
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    ref.BUILD=BUILD
    vec,cases,counts,groups=ref.generate()
    actual=BUILD/'cluster_actual.txt'
    compile_run('tb_reduce_cluster',TBS[1],BUILD/'vectors.txt',actual)
    outputs={int(i):int(p,16) for i,p in (line.split() for line in actual.read_text().splitlines())}
    assert len(outputs)==len(vec)
    for i,v in enumerate(vec):assert outputs[i]==v[-1]
    for group in groups:
        products=[]
        for partial in group['products']:
            acc=0
            for idx,i,j,a,b in partial:
                p=ref.signed(outputs[idx],64)
                if i<3 and a>>31:p+=ref.signed(b,32)*(1<<32)
                if j<3 and b>>31:p+=ref.signed(a,32)*(1<<32)
                if i<3 and j<3 and a>>31 and b>>31:p+=1<<64
                acc+=p<<(32*(i+j))
            products.append(((acc+(1<<63))>>64)% (1<<128))
        p0,p1,p2=products
        assert (p0-p1)% (1<<128)==group['re']
        assert (p2-p0-p1)% (1<<128)==group['im']
    return {'reducer_transactions':len(vectors),'reducer_configurations':9,
            'exhaustive_tlow_per_q':65536,'cluster_transactions':len(vec),'cluster_configurations':3,
            'transform_traces':len(cases),'r8_composed_complex_products':len(groups),'mismatches':0}

def report(sim,rows):
    result={'simulation':sim,'synthesis':rows,'source_sha256':hashes([*SOURCES,INCLUDE,*TBS]),
            'limits':['Canonical products only; R=2^16, q3329/q12289.',
                      'Original/CSA/compact use the same m generator, pipeline and II.',
                      'Generic GE/depth only, not target-library area/Fmax/energy.']}
    if rows:
        candidates=[r for r in rows if r['top'].startswith('reduce_cluster_')]
        base=next(r for r in candidates if r['top']=='reduce_cluster_original')
        eligible=[r for r in candidates if r['depth_cells']<=base['depth_cells']]
        chosen=min(eligible,key=lambda r:r['total_ge'])
        name=chosen['top'].removeprefix('reduce_cluster_')
        result['selection']={'name':name,'implementation':{'original':0,'csa':1,'compact':2}[name],
                             'rule':'minimum cluster total GE among candidates with generic gate depth no worse than original',
                             'total_ge':chosen['total_ge'],'depth_cells':chosen['depth_cells']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# Controlled reducer comparison','',f'Simulation: `{json.dumps(sim)}`','',
           '| Top | Comb GE | FF bits | Total GE | Gate depth |','|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f'| {r["top"]} | {r["comb_ge"]} | {r["ff"]} | {r["total_ge"]} | {r["depth_cells"]} |')
    if rows:lines+=['',f'Selection: **{name}**, rule: {result["selection"]["rule"]}.']
    lines+=['','Limits','']+['- '+s for s in result['limits']]
    RESULT.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synth-only',action='store_true');parser.add_argument('--synth',action='store_true')
    parser.add_argument('--yosys');args=parser.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    if args.synth_only:
        previous=json.loads(RESULT.read_text(encoding='utf-8'));check_hashes(previous['source_sha256']);sim=previous['simulation']
    else:sim=simulate();report(sim,[])
    if args.synth or args.synth_only:report(sim,synthesize(BUILD,SOURCES,TOPS,args.yosys))

if __name__=='__main__':main()
