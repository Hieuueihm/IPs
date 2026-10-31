"""Validate shared-array signed limb fusion, NTT packing, stall, and R8 product replay."""
from collections import Counter, defaultdict
import gzip
import importlib.util
import json
from random import Random
import re
import sys
from arith_experiment_common import ROOT, run, hashes

sys.path.insert(0, str(ROOT))
from model.r8_golden import Core, wrap

BUILD=ROOT/'study/build/flex_stream'
RESULT=ROOT/'study/results/flex_stream_validation.json'
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_stream_tile.sv','hdl/proto/flex_stream_array.sv']
DEPENDENCIES=[*SOURCES,'hdl/proto/mont_reduce16_functions.vh','sim/src/tb_flex_stream.sv',
              'scripts/validate_flex_stream.py','model/r8_golden.py']


def signed(x, w):
    x &= (1<<w)-1
    return x-(1<<w) if x>>(w-1) else x


def pack(words, w):
    return sum((x% (1<<w))<<(w*i) for i,x in enumerate(words))


def generate():
    rng=Random(20261026)
    vectors=[]; counts=Counter(); kernels=[]
    def add(ntt,width,mode,profile,inverse,data,roots,expected,origin):
        vectors.append((ntt,width,mode,profile,inverse,data,roots,expected))
        counts[origin]+=1
        return len(vectors)-1
    def real_product(x,y):
        v=wrap((x*y+(1<<63))>>64)
        idx=add(0,2,0,0,0,(x% (1<<128))|((y% (1<<128))<<512),0,v% (1<<128),'R8_real_product')
        return idx,v
    # Every active lane; endpoints, limb carries, unsigned low limbs, random signs.
    for code,w in enumerate((32,64,128)):
        count={32:16,64:4,128:1}[w]
        edges=[0,1,-1,-(1<<(w-1)),(1<<(w-1))-1,(1<<(w//2))-1,1<<(w//2),-(1<<(w//2))]
        if w>=64:edges += [0xffffffff,0x80000000,0xffffffff00000001,-0x100000001]
        edges=[signed(x,w) for x in edges]
        pairs=[(a,b) for a in edges for b in edges]
        pairs += [(signed(rng.getrandbits(w),w),signed(rng.getrandbits(w),w)) for _ in range(256*count)]
        for start in range(0,len(pairs),count):
            chunk=pairs[start:start+count]+[(0,0)]*max(0,count-len(pairs[start:start+count]))
            aa,bb=zip(*chunk)
            out=[((a*b+(1<<(w//2-1)))>>(w//2))% (1<<w) for a,b in chunk]
            add(0,code,rng.randrange(3),rng.randrange(2),rng.randrange(2),pack(aa,w)|(pack(bb,w)<<512),rng.getrandbits(1024),pack(out,w),f'FFT{w}_unit')
    # Pack the previously validated complete NTT stage traces into 16 tiles.
    spec=importlib.util.spec_from_file_location('tile_reference',ROOT/'scripts/prototype_ntt_cluster.py')
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    ref.BUILD=BUILD
    tile_vectors,cases,_,_=ref.generate()
    buckets=defaultdict(list)
    for mode,profile,inverse,data,roots,expected in tile_vectors:
        if mode!=3:buckets[mode,profile,inverse].append((data,roots,expected))
    for (mode,profile,inverse),items in buckets.items():
        dw=128 if mode==0 else 64;rw=(4,3,2)[mode]*16
        for start in range(0,len(items),16):
            chunk=items[start:start+16]
            mask=(1<<dw)-1;rm=(1<<rw)-1
            add(1,0,mode,profile,inverse,pack([d&mask for d,r,e in chunk],dw),
                pack([r&rm for d,r,e in chunk],rw),pack([e for d,r,e in chunk],dw),'NTT_packed')
    tables=json.loads((ROOT/'study/vectors/r8/twiddle_q64_64.json').read_text())
    rom=[signed(int(word,16),128) for row in tables['roots'] for word in row['forward'][:2]]
    chosen={}
    with gzip.open(ROOT/'study/vectors/r8/synthetic.jsonl.gz','rt') as f:
        for line in f:
            rec=json.loads(line)
            if rec.get('op') in ('FFT','IFFT') and rec['logn'] in (9,10):
                # Last case is deliberately preferred to the initial all-zero vectors.
                chosen[rec['op'],rec['logn']]=rec
    for key,rec in sorted(chosen.items()):
        calls=[]
        class Trace(Core):
            def mul(self,x,y):
                idx,v=real_product(x,y);calls.append((idx,x,y));return v
        got,_=Trace(rom,32).evaluate(rec)
        assert got==[signed(int(x,16),128) for x in rec['out']],key
        kernels.append((rec,calls))
    # Rapid width/FFT/NTT/profile/direction changes through the same stalled pipeline.
    pool=vectors[:sum(counts[k] for k in ('FFT32_unit','FFT64_unit','FFT128_unit','NTT_packed'))]
    for _ in range(1000):
        vectors.append(rng.choice(pool));counts['mixed_reconfiguration']+=1
    return vectors,dict(counts),kernels,rom,len(cases)


def simulate(vectors,name,fifo,stall,banked=0):
    path=BUILD/(name+'.txt');actual=BUILD/(name+'_actual.txt');exe=BUILD/(name+'.vvp')
    path.write_text(''.join(' '.join(f'{x:x}' for x in (v if len(v)==10 else (*v,0,0)))+'\n' for v in vectors))
    run(['iverilog','-g2012','-I',ROOT/'hdl/proto','-s','tb_flex_stream',
         f'-Ptb_flex_stream.FIFO_ENABLE={fifo}',f'-Ptb_flex_stream.STALL_ENABLE={stall}',f'-Ptb_flex_stream.BANKED={banked}',
         '-o',exe,*[ROOT/s for s in SOURCES],*([ROOT/'hdl/proto/ntt_bank_permute64.sv'] if banked else []),ROOT/'sim/src/tb_flex_stream.sv'])
    import subprocess
    p=subprocess.run(['vvp',str(exe),f'+vectors={path.as_posix()}',f'+actual={actual.as_posix()}'],capture_output=True,text=True)
    (BUILD/(name+'.log')).write_text(p.stdout+p.stderr)
    print(p.stdout,flush=True)
    p.check_returncode()
    found=re.search(r'PASS transactions=(\d+) cycles=(\d+) blocked_in=(\d+) blocked_out=(\d+)',p.stdout)
    assert found,p.stdout
    outputs={int(k):int(v,16) for k,v in (line.split() for line in actual.read_text().splitlines())}
    assert len(outputs)==len(vectors)
    return outputs,dict(zip(('transactions','cycles','blocked_in','blocked_out'),map(int,found.groups())))


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    vectors,counts,kernels,rom,traces=generate()
    print('Generated',len(vectors),counts,flush=True)
    outputs,stats=simulate(vectors,'buffered',1,1)
    # A mixed subset includes all three FFT widths and every NTT mode/profile/direction.
    subset=[v for v in vectors if v[0] or v[1]!=2][:1800]+[v for v in vectors if not v[0] and v[1]==2][:100]
    _,direct=simulate(subset,'direct_stall',0,1)
    _,plain=simulate(subset,'plain',0,0)
    replay=[]
    for rec,calls in kernels:
        position=0
        class Replay(Core):
            def mul(self,x,y):
                nonlocal position
                idx,xx,yy=calls[position];position+=1
                assert (x,y)==(xx,yy)
                return signed(outputs[idx],128)
        got,_=Replay(rom,32).evaluate(rec)
        assert position==len(calls)
        assert got==[signed(int(x,16),128) for x in rec['out']]
        replay.append({'op':rec['op'],'n':1<<rec['logn'],'real_products':len(calls),'output_words':len(got)})
    result={'counts':counts,'buffered':stats,'direct_stall':direct,'plain':plain,
            'r8_kernel_replay':replay,'ntt_transform_traces':traces,'mismatches':0,
            'source_sha256':hashes(DEPENDENCIES),
            'scope':['FFT128 Q64.64 RTL real products substituted into C-captured full FFT/IFFT vectors.',
                     'FFT32/64 use explicit Q16.16/Q32.32 contracts; no lower-width R8 certification.',
                     'No full FFT butterfly/controller RTL, SRAM macros, or complete FN-DSA integration.']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
