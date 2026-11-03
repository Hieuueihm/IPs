"""Live C application substitution using this prototype's transform outputs.

Only FFT/IFFT and NTT/INTT are replaced. Other kernels explicitly stay in C.
Supported transforms have no C fallback during replay. Windows orchestrates;
the pristine pinned C executable and independent verifier run under WSL LP64.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'study/build/a_cg_cmd_dispatch2'
APP=BUILD/'application'
OLD=ROOT/'study/build/pqc_application'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def linux():
    APP.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((OLD/'c/manifest.json').read_text())
    source=ROOT/'third_party/r8'
    assert all(digest(source/f)==h for f,h in manifest['source_sha256'].items()),'Pinned C source changed'
    original=(ROOT/'sim/ref/r8_pqc_cosim.c').read_text()
    text=original.replace('if(!replacement)return 0;',
                          'if(!replacement || (strcmp(op,"FFT") && strcmp(op,"IFFT")))return 0;',1)
    where=text.index('int pqc_ntt_replay(')
    text=text[:where]+text[where:].replace('if(!replacement)return 0;',
                            'if(!replacement || (strcmp(op,"NTT") && strcmp(op,"INTT")))return 0;',1)
    harness=APP/'transform_bridge.c';harness.write_text(text)
    commands=manifest['commands']
    compile_original=next(c for c in commands if '-c' in c and any(x.endswith('/sim/ref/r8_pqc_cosim.c') for x in c))
    obj=APP/'transform_bridge.o'
    cmd=[str(harness) if x.endswith('/sim/ref/r8_pqc_cosim.c') else str(obj) if x==compile_original[-1] else x for x in compile_original]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    link=next(c for c in commands if '-c' not in c and c[-1].endswith('/pqc_bridge'))
    exe=APP/'transform_bridge'
    cmd=[str(obj) if x==compile_original[-1] else str(exe) if x==link[-1] else x for x in link]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    results=[];comparisons={};negative=[]
    for n in (512,1024):
        out=APP/f'N{n}';out.mkdir(exist_ok=True)
        replacement=out/'replacement.txt'
        with (out/'trace.jsonl').open('w') as f:
            p=subprocess.run([str(exe),'replay',str(n.bit_length()-1),str(out),str(replacement)],stdout=f,stderr=subprocess.PIPE,text=True,timeout=120)
        (out/'stderr.log').write_text(p.stderr)
        assert p.returncode==0,p.stderr
        for name in ('sk.bin','pk.bin','expanded.bin','sig0.bin','sig1.bin','msg0.bin','msg1.bin'):
            assert (out/name).read_bytes()==(OLD/f'N{n}/capture'/name).read_bytes(),(n,name)
            comparisons[f'N{n}/{name}']=digest(out/name)
        for trial in range(2):
            p=subprocess.run([str(OLD/'c/independent_verify'),str(out/'pk.bin'),str(out/f'sig{trial}.bin'),str(out/f'msg{trial}.bin')],capture_output=True,text=True,check=True)
            results.append(dict(n=n,trial=trial,**json.loads(p.stdout)))
        # An altered supported live input must fail, rather than run C fallback.
        lines=replacement.read_text().splitlines();words=lines[1].split()
        words[0]=f'{int(words[0],16)^1:032x}' if len(words[0])==32 else str((int(words[0])+1)%12289)
        lines[1]=' '.join(words);bad=out/'bad_input.txt';bad.write_text('\n'.join(lines)+'\n')
        guard=out/'guard';guard.mkdir(exist_ok=True)
        p=subprocess.run([str(exe),'replay',str(n.bit_length()-1),str(guard),str(bad)],capture_output=True,text=True,timeout=120)
        assert p.returncode==7 and 'live ' in p.stderr,p.stderr
        negative.append(dict(n=n,code=p.returncode,stderr=p.stderr))
    report=dict(commit=manifest['commit'],replaced=['FFT','IFFT','NTT','INTT'],
                remains_C=['CMUL','SPLIT','MERGE','TOMONT','MODMUL','sampler','NTRUGen keygen','codec','SHAKE','others'],
                independent_verification=results,artifacts_sha256=comparisons,negative_live_input=negative,
                generated_harness_sha256=digest(harness),original_harness_sha256=digest(ROOT/'sim/ref/r8_pqc_cosim.c'))
    (APP/'application_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


def main():
    APP.mkdir(parents=True,exist_ok=True)
    import shutil
    def load(name,file):
        sp=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
    cg=load('appcg','model/cg_bank4_model.py');speed=load('appspeed','model/a_cg_speed_estimate.py')
    cg.FFT[4]=(45,cg.FFT[4][1]);speed.cg.FFT[4]=(45,speed.cg.FFT[4][1])
    count=0;summary=[]
    for n in (512,1024):
        records=[];cases=[];gm=igm=ngm=nigm=None
        capture=OLD/f'N{n}/capture/trace.jsonl'
        for line in capture.open():
            d=json.loads(line)
            if d['type']=='rom':
                w=[cg.fp.wrap(int(x,16),128) for x in d['words']];gm=list(zip(w[::2],w[1::2]));igm=[(a,cg.fp.wrap(-b,128)) for a,b in gm]
            elif d['type']=='ntt_rom':
                q=12289;ngm=[x*65536%q for x in d['forward']];nigm=[x*65536*pow(2,-1,q)%q for x in d['inverse']]
            elif d['type']=='kernel' and d['op'] in ('FFT','IFFT','NTT','INTT'):
                records.append(d);fft=d['op'] in ('FFT','IFFT');inv=d['op'] in ('IFFT','INTT');ln=d['logn']
                if fft:a=[cg.fp.wrap(int(x,16),128) for x in d['a']];z=[cg.fp.wrap(int(x,16),128) for x in d['out']]
                else:a=d['a'];z=d['out']
                cases.append((f'app{n}_{d["id"]}_{d["op"]}',int(fft),2 if fft else 0,ln,0,inv,0 if fft else 12289,a,z,gm if fft else ngm,igm if fft else nigm,0,0 if fft else 1,0))
        stem=f'app_N{n}';shutil.copy2(ROOT/'study/build/a_cg_batch'/(stem+'.bin'),BUILD/(stem+'.bin'))
        output=BUILD/(stem+'_output.bin')
        with (BUILD/(stem+'_sim.log')).open('w') as f:
            subprocess.run([str(BUILD/'obj/Va_cg_fast.exe'),str(BUILD/(stem+'.bin')),str(output)],check=True,stdout=f,stderr=subprocess.STDOUT)
        raw=output.read_bytes();w=struct.unpack('<'+'I'*(len(raw)//4),raw);assert w[:2]==(0x4f554732,len(records));pos=2
        out=APP/f'N{n}';out.mkdir(exist_ok=True)
        with (out/'replacement.txt').open('w') as f:
            for d in records:
                nw=w[pos];pos+=1;vals=w[pos:pos+nw];pos+=nw
                fft=d['op'] in ('FFT','IFFT');l=4 if fft else 1
                y=[sum(vals[i+j]<<(32*j) for j in range(l)) for i in range(0,nw,l)] if fft else [x for v in vals for x in (v&65535,v>>16)]
                assert y==[int(x,16) for x in d['out']] if fft else y==d['out']
                f.write(f'{d["op"]} {d["logn"]} {len(d["a"])} 0 {len(y)} 0\n')
                encode=lambda a:' '.join(f'{x:032x}' for x in a) if fft else ' '.join(map(str,a))
                a=[int(x,16) for x in d['a']] if fft else d['a']
                f.write(encode(a)+'\n'+encode(y)+'\n')
        assert pos==len(w)
        count+=len(records);summary.append(dict(n=n,calls=len(records),capture_sha256=digest(capture),rtl_output_sha256=digest(output)))
    (APP/'rtl_records.json').write_text(json.dumps(dict(calls=count,applications=summary),indent=2)+'\n')
    subprocess.run(['wsl','--exec','python3','/mnt/d/IPs/NTRU/experiments/a_cg_cmd_dispatch2/application.py','--linux'],check=True)


if __name__=='__main__':
    if '--linux' in sys.argv:linux()
    else:main()
