"""Pinned R8 application consumes supported-kernel results reconstructed from RTL.

Windows orchestrator: C runs under LP64 WSL; native Icarus runs the existing
banked array including FIFO/stalls. The rest of the reference remains in C.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from arith_experiment_common import ROOT,hashes,check_hashes
import validate_flex_stream as rtl

sys.path.insert(0,str(ROOT))
from model.pqc_kernel_adapter import Frames,evaluate,MASK
from model.r8_golden import parse_word

BUILD=ROOT/'study/build/pqc_application'
RESULT=ROOT/'study/results/pqc_application.json'
FP_OPS={'FFT','IFFT','CMUL','SPLIT','MERGE'}
DEPENDENCIES=[*rtl.SOURCES,'hdl/proto/ntt_bank_permute64.sv','hdl/proto/mont_reduce16_functions.vh',
              'sim/src/tb_flex_stream.sv','scripts/validate_flex_stream.py','scripts/validate_pqc_application.py',
              'scripts/pqc_c_bridge.py','model/pqc_kernel_adapter.py','model/r8_golden.py',
              'model/ntt_banked_supply.py','scripts/prototype_ntt_cluster.py',
              *['sim/ref/'+name for name in ('r8_pqc_bridge.h','r8_pqc_ntt.inc','r8_pqc_cosim.c','r8_verify_file.c')]]


def c_phase(mode):
    path='/mnt/d/IPs/NTRU/scripts/pqc_c_bridge.py'
    subprocess.run(['wsl','--exec','python3','-X','utf8',path,mode],check=True)


def capture_records():
    rows={};rom=None;ntt_rom=None;apps=[]
    for n in (512,1024):
        records=[]
        with (BUILD/f'N{n}/capture/trace.jsonl').open() as f:
            for line in f:
                rec=json.loads(line)
                if rec['type']=='rom':
                    local=[parse_word(x) for x in rec['words']]
                    if rom is None:rom=local
                    assert rom==local
                elif rec['type']=='ntt_rom':
                    local={k:rec[k] for k in ('forward','inverse')}
                    if ntt_rom is None:ntt_rom=local
                    assert ntt_rom==local
                elif rec['type']=='kernel':
                    assert rec['id']==len(records);records.append(rec)
                elif rec['type']=='application':apps.append(rec)
                elif rec['type']=='complete':assert not rec['replayed'] and rec['kernels']==len(records)
        rows[n]=records
    assert rom is not None and ntt_rom is not None and len(apps)==4
    return rows,rom,ntt_rom,apps


def expected(rec):
    if rec['op'] in FP_OPS:
        return [int(x,16) for x in rec['out']],None if 'out1' not in rec else [int(x,16) for x in rec['out1']]
    return rec['out'],None


def encode(rec,y,z):
    a,b=rec['a'],rec.get('b',[]);z=z or []
    header=f'{rec["op"]} {rec["logn"]} {len(a)} {len(b)} {len(y)} {len(z)}\n'
    if rec['op'] in FP_OPS:
        aa=[int(x,16) for x in a];bb=[int(x,16) for x in b]
        words=lambda v:' '.join(f'{x:032x}' for x in v)+'\n'
    else:
        aa,bb=a,b
        words=lambda v:' '.join(map(str,v))+'\n'
    return header+''.join(words(v) for v in (aa,bb,y,z) if v)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-capture',action='store_true',help='Reuse capture only after checking pinned C/harness hashes')
    parser.add_argument('--jobs',type=int,default=3)
    args=parser.parse_args();assert 1<=args.jobs<=3
    BUILD.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    if args.reuse_capture:
        manifest=json.loads((BUILD/'c/manifest.json').read_text())
        check_hashes(manifest['harness_sha256'])
        for name,sha in manifest['source_sha256'].items():
            assert hashlib.sha256((ROOT/'third_party/r8'/name).read_bytes()).hexdigest()==sha
    else:c_phase('capture')
    records,rom,ntt_rom,apps=capture_records();frames=Frames();counts=Counter();words=0
    for n,kernels in records.items():
        for rec in kernels:
            y,z=evaluate(rec,rom,ntt_rom,frames)
            assert (y,z)==expected(rec),('integer plan vs original C',n,rec['id'],rec['op'])
            counts[f'{rec["origin"]}/{rec["op"]}/N{1<<rec["logn"]}']+=1;words+=len(y)+(len(z) if z else 0)
        print('Planned N'+str(n),len(kernels),'C kernel calls; unique frames so far',len(frames.vectors),flush=True)
    planning_calls=dict(frames.calls);cache_hits=dict(frames.hits)
    print('Simulating',len(frames.vectors),'unique array transactions for',sum(planning_calls.values()),'frame uses',flush=True)
    # Deduplication is exact. Shuffle unique frames so both arithmetic domains
    # and all encountered widths/modes mix through the same stalled array.
    schedule=list(range(len(frames.vectors)));random.Random(20261026).shuffle(schedule)
    actual={};stats=[];rtl.BUILD=BUILD/'rtl';rtl.BUILD.mkdir(exist_ok=True)
    sim_sources=[*rtl.SOURCES,'hdl/proto/ntt_bank_permute64.sv','hdl/proto/mont_reduce16_functions.vh',
                 'sim/src/tb_flex_stream.sv','scripts/validate_flex_stream.py']
    def simulate_batch(start_idx):
        chunk=schedule[start_idx:start_idx+60000];name=f'batch_{start_idx//60000:03d}'
        vectors=[frames.vectors[k] for k in chunk]
        payload=''.join(' '.join(f'{x:x}' for x in v)+'\n' for v in vectors)
        # Path.write_text uses native text newlines; compare the exact bytes
        # that the existing native-Icarus helper writes on this host.
        vector_hash=hashlib.sha256(payload.replace('\n',os.linesep).encode()).hexdigest()
        marker=rtl.BUILD/(name+'_result.json')
        schedule_hash=hashlib.sha256(json.dumps(chunk).encode()).hexdigest()
        if marker.exists():
            cached=json.loads(marker.read_text());check_hashes(cached['source_sha256'])
            if (cached['schedule_sha256']==schedule_hash and cached.get('vectors_sha256')==vector_hash
                    and hashlib.sha256((rtl.BUILD/(name+'.txt')).read_bytes()).hexdigest()==vector_hash
                    and hashlib.sha256((rtl.BUILD/(name+'_actual.txt')).read_bytes()).hexdigest()==cached['actual_sha256']):
                output={int(i):int(y,16) for i,y in (line.split() for line in (rtl.BUILD/(name+'_actual.txt')).read_text().splitlines())}
                assert len(output)==len(chunk)
                for i,k in enumerate(chunk):assert output[i]==frames.vectors[k][7]
                return chunk,output,cached['stats']
        output,stat=rtl.simulate(vectors,name,1,1,banked=1)
        marker.write_text(json.dumps({'schedule_sha256':schedule_hash,'source_sha256':hashes(sim_sources),'stats':stat,
                                      'vectors_sha256':vector_hash,
                                      'actual_sha256':hashlib.sha256((rtl.BUILD/(name+'_actual.txt')).read_bytes()).hexdigest()},indent=2)+'\n')
        return chunk,output,stat
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for chunk,output,stat in pool.map(simulate_batch,range(0,len(schedule),60000)):
            actual.update({global_idx:output[i] for i,global_idx in enumerate(chunk)})
            stats.append(stat);print('RTL finished',len(actual),'/',len(frames.vectors),flush=True)
    frames.actual=actual;frames.calls.clear()
    for n,kernels in records.items():
        path=BUILD/f'N{n}/replacement.txt'
        with path.open('w') as f:
            for rec in kernels:
                y,z=evaluate(rec,rom,ntt_rom,frames)
                assert (y,z)==expected(rec),('actual RTL vs C kernel',n,rec['id'],rec['op'])
                f.write(encode(rec,y,z))
        print('Actual RTL-backed replacements ready N'+str(n),flush=True)
    c_phase('replay');c_phase('verify');c_phase('guard')
    comparisons=[];replayed_apps=[]
    for n in (512,1024):
        capture=BUILD/f'N{n}/capture';replay=BUILD/f'N{n}/replay'
        files=[]
        for name in ('sk.bin','pk.bin','expanded.bin','sig0.bin','sig1.bin','msg0.bin','msg1.bin'):
            assert (capture/name).read_bytes()==(replay/name).read_bytes(),(n,name)
            files.append({'file':name,'sha256':hashlib.sha256((replay/name).read_bytes()).hexdigest()})
        comparisons.append({'n':n,'identical_to_original_C':files})
        rows=[json.loads(line) for line in (replay/'trace.jsonl').read_text().splitlines()]
        complete=rows[-1];assert complete['replayed'] and complete['kernels']==len(records[n])
        for rec in rows[:-1]:
            assert rec['type']=='application' and all(rec[k]==0 for k in ('keygen','expand','sign','verify'))
            assert rec['wrong_message']!=0 and rec['wrong_signature']!=0
            replayed_apps.append(rec)
    assert len(replayed_apps)==4
    # Mutation control: changing an actual RTL product must be detected at the
    # reconstructed C-kernel output boundary (not silently replaced by oracle).
    first=next(r for r in records[512] if r['op']=='FFT')
    victim=next(i for i,v in enumerate(frames.vectors) if v[0]==0 and v[5]!=0 and v[7]!=0)
    original=actual[victim];actual[victim]^=1
    detected=False
    for rec in records[512]:
        if rec['op'] in FP_OPS:
            try:got=evaluate(rec,rom,ntt_rom,frames)
            except AssertionError:detected=True;break
            if got!=expected(rec):detected=True;break
    actual[victim]=original
    assert detected,'RTL product mutation escaped kernel oracle'
    manifest=json.loads((BUILD/'c/manifest.json').read_text())
    # Verify pinned original source/harness again after all three C runs.
    for name,sha in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/'third_party/r8'/name).read_bytes()).hexdigest()==sha
    evidence=['study/build/pqc_application/c/manifest.json','study/build/pqc_application/independent_verify.json',
              'study/build/pqc_application/c/pqc_bridge','study/build/pqc_application/c/independent_verify',
              'study/build/pqc_application/c/vrfy_instrumented.c']
    evidence += [f'study/build/pqc_application/N{n}/{mode}/trace.jsonl' for n in (512,1024) for mode in ('capture','replay')]
    evidence += [f'study/build/pqc_application/N{n}/replacement.txt' for n in (512,1024)]
    result={'commit':manifest['commit'],'configuration':manifest['configuration'],'source_pristine':True,
            'c_kernel_calls':sum(map(len,records.values())),'c_output_words':words,'kernel_counts':dict(counts),
            'array_frame_uses':planning_calls,'exact_cache_hits':cache_hits,'unique_rtl_transactions':len(frames.vectors),
            'simulation':stats,'mismatches':0,'applications':replayed_apps,'artifact_comparisons':comparisons,
            'independent_original_C_verifier':json.loads((BUILD/'independent_verify.json').read_text()),
            'negative_controls':{'wrong_message_rejected':True,'wrong_signature_rejected':True,
                                 'corrupted_live_input_rejected':True,'mutated_RTL_product_detected':detected},
            'source_sha256':hashes(DEPENDENCIES),'evidence_sha256':hashes(evidence),'seconds':round(time.monotonic()-start,1),
            'limits':['Functional deterministic co-simulation, not an RTL implementation of the complete signature scheme.',
                      'Actual shared banked-array RTL handles FFT real products, NTT butterflies, modular products and iNTT normalization.',
                      'FFT add/sub, 3M sequencing, scaling and all RAM/stage orchestration run in the host adapter.',
                      'Other signing operations, sampling, divisions, NTRUGen keygen and protocol run in C.',
                      'Only pinned R8 scalar Q64.64 and q12289, N512/N1024, two messages per generated key.',
                      'No claim of full FN-DSA standard conformance, constant-time hardware or side-channel validation.']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('c_kernel_calls','unique_rtl_transactions','mismatches','applications','seconds')},indent=2))


if __name__=='__main__':main()
