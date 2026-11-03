"""Four-leaf NTT stage-pair experiment; exact RTL simulation and generic synthesis.

python -X utf8 scripts/prototype_ntt_cluster.py [--synth] [--yosys PATH]
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib
import json
from pathlib import Path
from random import Random
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parent.parent
BUILD=ROOT/'study/build/ntt_cluster'
RESULT=ROOT/'study/results'
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_ntt_cluster.sv']
TB='sim/src/tb_flex_ntt_cluster.sv'
TOPS=['cluster_ntt_parallel','cluster_ntt_pair_only','cluster_ntt_configurable',
      'cluster_flex_parallel','cluster_flex_pair','cluster_ntt_pair_q12289','cluster_ntt_pair_q3329',
      'cluster_ntt_pair_bypass','cluster_ntt_parallel_short']

def run(cmd,**kw):
    return subprocess.run([str(x) for x in cmd],check=True,**kw)

def pack(a,w=16):
    return sum((x% (1<<w))<<(w*k) for k,x in enumerate(a))

def signed(x,w):
    return (x%(1<<w))-(1<<w) if x%(1<<w)>=(1<<(w-1)) else x%(1<<w)

def bf(a,b,w,q,inverse):
    return ((a+b)%q,(a-b)*w%q) if inverse else ((a+b*w)%q,(a-b*w)%q)

def oracle(mode,profile,inverse,data,roots):
    q=(12289,3329)[profile]
    if mode==3:
        return signed(data&0xffffffff,32)*signed((data>>32)&0xffffffff,32) % (1<<64)
    a=[(data>>(16*k))&65535 for k in range(8)]
    w=[((roots>>(16*k))&65535)*pow(65536,-1,q)%q for k in range(4)]
    if mode==1:
        w=[w[1],w[2],w[0],w[0]] if inverse else [w[0],w[0],w[1],w[2]]
    if mode==0:
        return pack([v for k in range(4) for v in bf(a[2*k],a[2*k+1],w[k],q,inverse)])
    pairs=[(0,1),(2,3)] if inverse else [(0,2),(1,3)]
    b=a[:4]
    for k,(i,j) in enumerate(pairs):
        b[i],b[j]=bf(a[i],a[j],w[k],q,inverse)
    if mode==2:return pack(b)
    a=b[:]
    pairs=[(0,2),(1,3)] if inverse else [(0,1),(2,3)]
    for k,(i,j) in enumerate(pairs):
        b[i],b[j]=bf(a[i],a[j],w[k+2],q,inverse)
    return pack(b)

def bitrev(k,bits):
    return int(f'{k:0{bits}b}'[::-1],2)

def encode_roots(mode,inverse,roots,q):
    if mode==1:
        if inverse:
            assert roots[2]==roots[3]
            roots=[roots[2],roots[0],roots[1]]
        else:
            assert roots[0]==roots[1]
            roots=[roots[0],roots[2],roots[3]]
    return pack([w*65536%q for w in roots])

def find_root(q,order):
    assert (q-1)%order==0
    for a in range(2,q):
        r=pow(a,(q-1)//order,q)
        if pow(r,order//2,q)==q-1:return r
    raise AssertionError('root')

def stages(q,n,incomplete=False):
    logn=n.bit_length()-1
    if incomplete:
        assert q==3329 and n==256
        root=17
        gm=[pow(root,bitrev(k,7),q) for k in range(128)]
    else:
        root=find_root(q,2*n)
        gm=[pow(root,bitrev(k,logn),q) for k in range(n)]
    forward=[]
    stride=n//2; groups=1
    while stride>=(2 if incomplete else 1):
        layer=[]
        for g in range(groups):
            for j in range(2*g*stride,(2*g+1)*stride):
                layer.append((j,j+stride,gm[groups+g]))
        forward.append(layer)
        stride//=2; groups*=2
    backward=[[(i,j,pow(w,-1,q)) for i,j,w in layer] for layer in reversed(forward)]
    return forward,backward,root

def apply_layer(a,layer,q,inverse):
    out=a[:]
    for i,j,w in layer:out[i],out[j]=bf(a[i],a[j],w,q,inverse)
    return out

def generate():
    rng=Random(20261026)
    vectors=[]; cases=[]; counts=Counter(); fft_groups=[]
    def add(mode,profile,inverse,data,roots,origin):
        expected=oracle(mode,profile,inverse,data,roots)
        vectors.append((mode,profile,inverse,data,roots,expected))
        counts[(mode,profile,inverse,origin)]+=1
        return len(vectors)-1
    for iteration in range(160):
        for profile,q in enumerate((12289,3329)):
            for inverse in (False,True):
                for mode in (0,1,2):
                    a=[rng.randrange(q) for _ in range(8)]
                    w=[rng.randrange(q) for _ in range(4)]
                    if iteration<5:
                        edge=[0,1,q-1,q//2,q//2+1]
                        a=[edge[(iteration+k)%5] for k in range(8)]
                        w=[edge[(4-iteration+k)%5] for k in range(4)]
                    if mode==1:
                        if inverse:w[3]=w[2]
                        else:w[1]=w[0]
                    add(mode,profile,inverse,pack(a),encode_roots(mode,inverse,w,q),'unit')
        edge=[0,1,-1,-(1<<31),(1<<31)-1,65535,65536,-65536]
        a=edge[iteration] if iteration<8 else signed(rng.getrandbits(32),32)
        b=edge[7-iteration] if iteration<8 else signed(rng.getrandbits(32),32)
        add(3,iteration%2,bool(iteration%3),pack([a,b],32),rng.getrandbits(64),'unit')

    # Build complete transform traces. Expected stages use ordinary modular
    # multiplication; the RTL consumes Montgomery-encoded roots independently.
    for profile,q in enumerate((12289,3329)):
        sizes=(8,16,32,64,128,256,512,1024) if profile==0 else (8,16,32,64,128,256)
        for n in sizes:
            incomplete=q==3329 and n==256
            forward,backward,root=stages(q,n,incomplete)
            for pattern in ('boundary','random'):
                initial=[rng.randrange(q) for _ in range(n)] if pattern=='random' else [0,1,q-1,0]*(n//4)
                current=initial[:]
                for inverse,layers in ((False,forward),(True,backward)):
                    before=current[:]
                    ids=[]
                    for layer_index in range(0,len(layers),2):
                        layer=layers[layer_index]
                        first=apply_layer(current,layer,q,inverse)
                        if layer_index+1==len(layers):
                            # Full single-layer mode fills all four leaves.
                            for start in range(0,len(layer),4):
                                chunk=layer[start:start+4]
                                a=[v for i,j,w in chunk for v in (current[i],current[j])]
                                ws=[w*65536%q for i,j,w in chunk]
                                idx=add(0,profile,inverse,pack(a),pack(ws),'transform')
                                positions=[v for i,j,w in chunk for v in (i,j)]
                                assert vectors[idx][-1]==pack([first[p] for p in positions])
                                ids.append((idx,positions))
                            current=first
                            continue
                        second_layer=layers[layer_index+1]
                        expected=apply_layer(first,second_layer,q,inverse)
                        f={i:(j,w) for i,j,w in layer}
                        s={i:(j,w) for i,j,w in second_layer}
                        used=set()
                        for a in sorted(f):
                            if a in used:continue
                            if inverse:
                                b,w0=f[a]; c,w2=s[a]; d,w1=f[c]; d2,w3=s[b]
                            else:
                                c,w0=f[a]; b,w2=s[a]; d,w1=f[b]; d2,w3=s[c]
                            assert d==d2
                            positions=[a,b,c,d]; used.update(positions)
                            idx=add(1,profile,inverse,pack([current[p] for p in positions]),
                                    encode_roots(1,inverse,[w0,w1,w2,w3],q),'transform')
                            assert vectors[idx][-1]==pack([expected[p] for p in positions])
                            ids.append((idx,positions))
                        current=expected
                    # The trace includes every output group at every pass.
                    cases.append({'q':q,'n':n,'inverse':inverse,'incomplete':incomplete,
                                  'pattern':pattern,'transactions':len(ids)})
                    if not inverse and n<=32 and not incomplete:
                        direct=[sum(before[j]*pow(root,(2*bitrev(k,n.bit_length()-1)+1)*j,q)
                                    for j in range(n))%q for k in range(n)]
                        assert current==direct,'forward transform vs direct evaluation'
                    if inverse:
                        scale=pow(1<<len(layers),-1,q)
                        assert [x*scale%q for x in current]==initial,'roundtrip normalization'

    # Validate exact 128-bit R8 products after decomposing into this tile's
    # exact signed/unsigned 32-bit multiplications (sign fixups in the driver).
    import gzip
    mask=(1<<128)-1
    with gzip.open(ROOT/'study/vectors/r8/synthetic.jsonl.gz','rt') as handle:
        for line in handle:
            rec=json.loads(line)
            if rec.get('op')!='CMUL':continue
            n=1<<rec['logn']; hn=n//2
            k=0
            ar,ai=[signed(int(rec['a'][j],16),128) for j in (k,k+hn)]
            br,bi=[signed(int(rec['b'][j],16),128) for j in (k,k+hn)]
            products=[]
            for x,y in ((ar,br),(ai,bi),(signed(ar+ai,128),signed(br+bi,128))):
                partial=[]
                for i in range(4):
                    for j in range(4):
                        if 32*(i+j)>=192:continue
                        a=(x>>(32*i))&0xffffffff; b=(y>>(32*j))&0xffffffff
                        idx=add(3,0,False,pack([a,b],32),0,'R8_partial')
                        partial.append((idx,i,j,a,b))
                products.append(partial)
            fft_groups.append({'products':products,'re':int(rec['out'][k],16),'im':int(rec['out'][k+hn],16)})
    with (BUILD/'vectors.txt').open('w') as handle:
        for mode,profile,inverse,data,roots,expected in vectors:
            handle.write(f'{mode:x} {profile:x} {int(inverse):x} {data:032x} {roots:016x} {expected:032x}\n')
    assert len(vectors)<65535
    return vectors,cases,counts,fft_groups

def simulate():
    vectors,cases,counts,groups=generate()
    exe=BUILD/'sim.vvp'
    run(['iverilog','-g2012','-s','tb_flex_ntt_cluster','-o',exe,
         *[ROOT/s for s in SOURCES],ROOT/TB])
    result=run(['vvp',exe,f'+vectors={(BUILD/"vectors.txt").as_posix()}',
                f'+actual={(BUILD/"actual.txt").as_posix()}'],capture_output=True,text=True)
    print(result.stdout,flush=True)
    (BUILD/'simulation.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    actual={int(i):int(p,16) for i,p in (line.split() for line in (BUILD/'actual.txt').read_text().splitlines())}
    assert len(actual)==len(vectors)
    for idx,vec in enumerate(vectors):assert actual[idx]==vec[-1],idx
    for group in groups:
        products=[]
        for partial in group['products']:
            acc=0
            for idx,i,j,a,b in partial:
                # Tile accepts signed limbs. Restore unsigned lower limbs with
                # exact identity, outside the RTL; this is not a wider RTL tree.
                p=signed(actual[idx],64)
                if i<3 and a>>31:p+=signed(b,32)*(1<<32)
                if j<3 and b>>31:p+=signed(a,32)*(1<<32)
                if i<3 and j<3 and a>>31 and b>>31:p+=1<<64
                acc+=p<<(32*(i+j))
            products.append(((acc+(1<<63))>>64)% (1<<128))
        p0,p1,p2=products
        assert (p0-p1)% (1<<128)==group['re']
        assert (p2-p0-p1)% (1<<128)==group['im']
    print(f'PASS: {len(cases)} transform traces; {len(groups)} driver-composed R8 complex products.',flush=True)
    return {'transactions':len(vectors),'configurations':len(TOPS),'mismatches':0,
            'coverage':{'/'.join(map(str,k)):v for k,v in sorted(counts.items())},
            'transforms':cases,'r8_driver_composed_complex_products':len(groups),
            'limits':['W64/W128 assembly and sign fixups are in the driver, not synthesized RTL.',
                      'Full transform traces are compared to integer arithmetic, not Falcon/Kyber C.',
                      'q3329 N256 uses seven layers and normalization 128^-1; no BASEMUL implemented.']}

def synthesize(yosys):
    yosys=yosys or shutil.which('yosys')
    if not yosys:raise RuntimeError('Provide native Yosys with --yosys')
    version=run([yosys,'-V'],capture_output=True,text=True).stdout.strip()
    weights={'$_BUF_':.67,'$_NOT_':.67,'$_NAND_':1.,'$_NOR_':1.,'$_AND_':1.33,'$_OR_':1.33,
             '$_ANDNOT_':1.33,'$_ORNOT_':1.33,'$_XOR_':2.33,'$_XNOR_':2.33,'$_MUX_':2.33}
    def one(top):
        stat=BUILD/f'{top}_stat.json'; depth=BUILD/f'{top}_ltp.txt'
        script='\n'.join(['read_verilog -sv '+' '.join((ROOT/s).as_posix() for s in SOURCES),
                         f'hierarchy -check -top {top}',f'synth -flatten -noabc -top {top}',
                         'abc -fast -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX','opt_clean -purge',
                         f'tee -q -o {stat.as_posix()} stat -json',f'tee -q -o {depth.as_posix()} ltp -noff'])
        ys=BUILD/f'{top}.ys'; ys.write_text(script)
        start=time.monotonic(); print(f'Synthesizing {top} ...',flush=True)
        output=run([yosys,'-Q','-s',ys.as_posix()],capture_output=True,text=True)
        (BUILD/f'{top}.log').write_text(output.stdout+output.stderr,encoding='utf-8')
        cells=next(iter(json.loads(stat.read_text())['modules'].values()))['num_cells_by_type']
        ff=sum(n for k,n in cells.items() if 'DFF' in k)
        unknown={k:v for k,v in cells.items() if k not in weights and 'DFF' not in k}
        assert not unknown,unknown
        comb=sum(weights.get(k,0)*v for k,v in cells.items())
        row={'top':top,'comb_ge':round(comb,1),'ff':ff,'total_ge':round(comb+4.67*ff,1),
             'depth_cells':int(re.search(r'length=(\d+)',depth.read_text()).group(1)),
             'tool':version,'unknown':unknown,'seconds':round(time.monotonic()-start,1)}
        print(json.dumps(row),flush=True);return row
    with ThreadPoolExecutor(max_workers=3) as pool:return list(pool.map(one,TOPS))

def latency_table():
    rows=[]
    for q,n,stages_count in ((12289,8,3),(12289,16,4),(12289,64,6),(12289,256,8),
                             (12289,512,9),(12289,1024,10),(3329,256,7)):
        for bandwidth in (64,128):
            parallel_issues=n//8; pair_issues=n//4
            parallel_beats=(128+bandwidth-1)//bandwidth
            pair_beats=(64+bandwidth-1)//bandwidth
            # A read adapter assembles a transaction before the input register;
            # output serialization consumes its final beat before the barrier.
            # Compute pipeline is three sampled edges (two intervals).
            parallel_pass=(parallel_issues-1)*parallel_beats+2*parallel_beats+1
            short_parallel_pass=parallel_pass-1
            pair_pass=(pair_issues-1)*pair_beats+2*pair_beats+1
            par=stages_count*parallel_pass
            short_par=stages_count*short_parallel_pass
            paired=(stages_count//2)*pair_pass+(stages_count%2)*parallel_pass
            rows.append({'q':q,'n':n,'layers':stages_count,'data_bits_each_direction':bandwidth,
                         'parallel_cycles':par,'paired_cycles':paired,'ratio':round(par/paired,3),
                         'dedicated_short_cycles':short_par,'short_ratio':round(short_par/paired,3),
                         'parallel_data_bits_each_direction':stages_count*n*16,
                         'paired_data_bits_each_direction':((stages_count+1)//2)*n*16})
    return rows

def report(sim,rows):
    result={'simulation':sim,'synthesis':rows,'isolated_transform_model':latency_table(),
            'modes':{'0':{'ntt_butterflies':4,'layers':1,'data_bits_each_direction':128,'root_bits':64},
                     '1':{'ntt_butterflies':4,'layers':2,'data_bits_each_direction':64,'root_bits':48},
                     '2':{'ntt_butterflies':2,'layers':1,'data_bits_each_direction':64,'root_bits':32},
                     '3':{'exact_signed_32bit_products':1,'data_input_bits':64,'data_output_bits':64}},
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [*SOURCES,TB]},
            'limits':['Shared RTL: three sampled edges and II1; dedicated short baseline: two edges and II1. No backpressure or RAM.',
                      'Isolated transform table assumes a barrier after each pass, ideal read/write adapters and externally gathered groups.',
                      'Cycle model covers butterfly layers only; inverse normalization, BASEMUL and domain conversions are excluded.',
                      'Twiddle bandwidth, address gathering, target timing, memory area and energy are not measured.',
                      'GE uses generic mapping and 4.67 GE per FF; depth is not Fmax.']}
    (RESULT/'ntt_cluster.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# Four-leaf configurable NTT cluster','',
           f'- RTL simulation: {sim["transactions"]} vectors, {sim["configurations"]} configurations, zero mismatches.',
           f'- {len(sim["transforms"])} forward/inverse traces over both profiles.',
           f'- {sim["r8_driver_composed_complex_products"]} R8 complex products reconstructed in the driver from exact RTL32 products.',
           '', '| Top | Comb GE | FF bits | Total GE | Gate depth |','|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f'| {row["top"]} | {row["comb_ge"]} | {row["ff"]} | {row["total_ge"]} | {row["depth_cells"]} |')
    if rows:
        by_top={r['top']:r for r in rows}
        comparisons=[('Add stage pairing to FFT-capable cluster','cluster_flex_parallel','cluster_flex_pair'),
                     ('Add bypass to pair-only NTT','cluster_ntt_pair_only','cluster_ntt_pair_bypass'),
                     ('Add four-independent-BF mode to pair/bypass NTT','cluster_ntt_pair_bypass','cluster_ntt_configurable'),
                     ('Full shared cluster vs short dedicated NTT','cluster_ntt_parallel_short','cluster_flex_pair'),
                     ('Runtime q vs fixed12289, pair-only','cluster_ntt_pair_q12289','cluster_ntt_pair_only'),
                     ('Runtime q vs fixed3329, pair-only','cluster_ntt_pair_q3329','cluster_ntt_pair_only')]
        result['area_comparisons']=[{'label':label,'baseline':base,'candidate':candidate,
                                    'total_ge_ratio':by_top[candidate]['total_ge']/by_top[base]['total_ge']}
                                   for label,base,candidate in comparisons]
        lines+=['','## Area comparisons','', '| Comparison | Total GE change |','|---|---:|']
        for comp in result['area_comparisons']:
            lines.append(f'| {comp["label"]} | {(comp["total_ge_ratio"]-1)*100:+.2f}% |')
        lines+=['','Small generic mapping differences do not establish zero-cost FFT support or target timing.']
    lines+=['','## Isolated-transform cycle model','',
            'Data bandwidth is per direction. Root bandwidth is separate. Same-clock hypothesis; not measured speedup.',
            'One pass takes (issues-1)*beats+2*beats+1 cycles: initial input assembly, three-edge compute and final output serialization.',
            'beats=ceil(transaction_data_bits/bandwidth). A tail layer uses four independent butterflies. Normalization is excluded.',
            '', '| q | N | Layers | Data bits/cycle | Dedicated short cycles | Shared parallel cycles | Shared paired cycles | Short / paired |',
            '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in result['isolated_transform_model']:
        lines.append('| '+' | '.join(str(row[k]) for k in ('q','n','layers','data_bits_each_direction','dedicated_short_cycles','parallel_cycles','paired_cycles','short_ratio'))+' |')
    lines+=['','## Limits','']+['- '+s for s in [*result['limits'],*sim['limits']]]
    (RESULT/'ntt_cluster.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (RESULT/'ntt_cluster.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synth',action='store_true')
    parser.add_argument('--synth-only',action='store_true')
    parser.add_argument('--yosys')
    args=parser.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True);RESULT.mkdir(parents=True,exist_ok=True)
    if args.synth_only:
        data=json.loads((RESULT/'ntt_cluster.json').read_text(encoding='utf-8'))
        for name,digest in data['source_sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'RTL changed since simulation'
        sim=data['simulation']
    else:
        sim=simulate();report(sim,[])
    if args.synth or args.synth_only:report(sim,synthesize(args.yosys))

if __name__=='__main__':main()
