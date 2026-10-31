"""Feed whole-kernel autonomous RTL outputs into the existing live-input C bridge."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'study/build/kernel_engine'
CROOT=ROOT/'study/build/pqc_application'
FP={'FFT','IFFT','CMUL','SPLIT','MERGE'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wsl(p):return '/mnt/'+str(p)[0].lower()+str(p)[2:].replace('\\','/')


def main():
    result=json.loads((ROOT/'study/results/kernel_engine.json').read_text());assert result['full']
    for name,digest in result['sha256'].items():assert sha(ROOT/name)==digest,('stale RTL evidence',name)
    manifest=json.loads((CROOT/'c/manifest.json').read_text())
    for name,digest in manifest['source_sha256'].items():assert sha(ROOT/'third_party/r8'/name)==digest,('reference modified',name)
    for name,digest in manifest['harness_sha256'].items():assert sha(ROOT/name)==digest,('bridge modified',name)
    cases=json.loads((BUILD/'cases.json').read_text());mapping=json.loads((BUILD/'mapping.json').read_text())
    actual=[]
    with (BUILD/'actual.txt').open() as f:
        while line:=f.readline():
            idx,n=map(int,line.split());assert idx==len(actual)
            values=[int(f.readline(),16) for _ in range(n)];actual.append(values)
    assert len(actual)==len(cases)==result['kernels']
    apps=[];artifacts=[];guards=[]
    for degree,ids in mapping.items():
        degree=int(degree);out=BUILD/f'N{degree}';out.mkdir(exist_ok=True);repl=out/'replacement.txt'
        with repl.open('w') as f:
            for idx in ids:
                c=cases[idx];a=c['a'];b=c.get('b',[]);ny=len(c['out']);nz=len(c.get('out1',[]));values=actual[idx]
                expected=[int(x,16) if isinstance(x,str) else x for x in c['out']+c.get('out1',[])]
                assert values==expected
                f.write(f'{c["op"]} {c["logn"]} {len(a)} {len(b)} {ny} {nz}\n')
                def words(v):
                    if c['op'] in FP:return ' '.join(f'{(int(x,16) if isinstance(x,str) else x):032x}' for x in v)+'\n'
                    return ' '.join(map(str,v))+'\n'
                for v in (a,b,values[:ny],values[ny:]):
                    if v:f.write(words(v))
        replay=out/'replay';replay.mkdir(exist_ok=True)
        with (replay/'trace.jsonl').open('w') as stdout:
            p=subprocess.run(['wsl','--exec',wsl(CROOT/'c/pqc_bridge'),'replay',str(degree.bit_length()-1),wsl(replay),wsl(repl)],stdout=stdout,stderr=subprocess.PIPE,text=True,timeout=120)
        (replay/'stderr.log').write_text(p.stderr);assert p.returncode==0,p.stderr
        capture=CROOT/f'N{degree}/capture'
        for baseline in sorted(capture.glob('*.bin')):
            got=replay/baseline.name;assert got.read_bytes()==baseline.read_bytes(),baseline.name
            artifacts.append({'n':degree,'file':baseline.name,'sha256':sha(got),'baseline_equal':True})
        for trial in range(2):
            p=subprocess.run(['wsl','--exec',wsl(CROOT/'c/independent_verify'),wsl(replay/'pk.bin'),wsl(replay/f'sig{trial}.bin'),wsl(replay/f'msg{trial}.bin')],capture_output=True,text=True,timeout=60)
            assert p.returncode==0,p.stderr
            apps.append({'n':degree,'trial':trial,**json.loads(p.stdout)})
        if degree==512:
            # Change an RTL OUTPUT, retaining every live input in the bridge.
            lines=repl.read_text().splitlines();header=lines[0].split()
            output_line=1+int(int(header[2])>0)+int(int(header[3])>0)
            words=lines[output_line].split();is_fp=header[0] in FP
            value=int(words[0],16) if is_fp else int(words[0])
            words[0]=f'{value^1:032x}' if is_fp else str((value+1)%12289)
            lines[output_line]=' '.join(words)
            bad=out/'mutated_rtl_output.txt';bad.write_text('\n'.join(lines)+'\n')
            guard=out/'guard_output';guard.mkdir(exist_ok=True)
            with (guard/'trace.jsonl').open('w') as stdout:
                p=subprocess.run(['wsl','--exec',wsl(CROOT/'c/pqc_bridge'),'replay',str(degree.bit_length()-1),wsl(guard),wsl(bad)],stdout=stdout,stderr=subprocess.PIPE,text=True,timeout=120)
            assert p.returncode==7 and 'live ' in p.stderr,p.stderr
            (guard/'stderr.log').write_text(p.stderr)
            guards.append({'n':degree,'changed':'first actual RTL kernel output word','returncode':p.returncode,'stderr':p.stderr})
        print(f'N{degree}: live C replay and independent verifier passed',flush=True)
    report={'autonomous_kernel_rtl':True,'kernel_calls':sum(map(len,mapping.values())),
        'applications':apps,'artifacts':artifacts,'output_mutation_guards':guards,'kernel_result_sha256':sha(ROOT/'study/results/kernel_engine.json'),
        'script_sha256':sha(Path(__file__)),
        'c_build_manifest_sha256':sha(CROOT/'c/manifest.json'),
        'c_bridge_sha256':sha(CROOT/'c/pqc_bridge'),
        'independent_verifier_sha256':sha(CROOT/'c/independent_verify'),
        'reference_sources_pristine':True,
        'remaining_in_C':'keygen, sampler, signing orchestration, encoding and SHAKE',
        'scope':'Fixed deterministic workload; four signatures. Functional co-simulation, no side-channel or standard certification.'}
    (ROOT/'study/results/kernel_application.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
