"""LP64 C build/capture/replay helper for the PQC RTL application experiment."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from validate_r8 import ROOT,SOURCE,COMMIT,KERNELS,reference,digest

BUILD=ROOT/'study/build/pqc_application'
C_BUILD=BUILD/'c'
NAMES=('mq_NTT','mq_iNTT','mq_poly_tomonty','mq_poly_montymul_ntt')


def command(args,**kw):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,**kw)
    if p.returncode:raise RuntimeError(f'{args}:\n{p.stdout}\n{p.stderr}')
    return p


def build():
    sources_before=reference();C_BUILD.mkdir(parents=True,exist_ok=True)
    cc=shutil.which('gcc');assert cc
    macros=command([cc,'-dM','-E','-'],input='').stdout
    assert '#define __SIZEOF_LONG__ 8' in macros,'Run under WSL LP64'
    text=(SOURCE/'vrfy.c').read_text()
    declarations='\n#include <stdio.h>\n#include <string.h>\n#include "r8_pqc_bridge.h"\n'
    declarations+='static void mq_NTT(uint16_t *,unsigned);\nstatic void mq_iNTT(uint16_t *,unsigned);\n'
    declarations+='static void mq_poly_tomonty(uint16_t *,unsigned);\nstatic void mq_poly_montymul_ntt(uint16_t *,const uint16_t *,unsigned);\n'
    assert text.count('#include "inner.h"')==1
    text=text.replace('#include "inner.h"','#include "inner.h"'+declarations)
    for name in NAMES:
        text,count=re.subn(r'(?m)^'+name+r'\(',f'pqc_original_{name}(',text)
        assert count==1,(name,count)
    text+='\n#include "r8_pqc_ntt.inc"\n'
    adapted=C_BUILD/'vrfy_instrumented.c';adapted.write_text(text)
    flags=['-O2','-std=gnu11','-fno-strict-aliasing','-ffunction-sections','-fdata-sections',
           '-DFALCON_FPR_MODE=2','-DFALCON_AVX2=0','-DFALCON_RAND_WIN32=0',
           '-I',SOURCE,'-I',ROOT/'sim/ref']
    files=[SOURCE/name for name in ('codec.c','common.c','falcon.c','fft.c','fpr.c','rng.c','shake.c','sign.c','sign_ref.c')]
    files += [SOURCE/'ntrugen/src'/name for name in ('ng_falcon.c','ng_fxp.c','ng_gauss.c','ng_mp31.c','ng_ntru.c','ng_poly.c','ng_zint31.c','sha3.c')]
    files += [adapted,ROOT/'sim/ref/r8_pqc_cosim.c']
    objects=[];commands=[]
    for i,path in enumerate(files):
        obj=C_BUILD/f'{i:02d}_{path.stem}.o';cmd=[cc,*flags]
        if path==SOURCE/'fft.c':cmd += [f'-Dfalcon_inner_{k}=r8_original_{k}' for k in KERNELS]
        cmd+=['-c',path,'-o',obj];objects.append(obj);commands.append(cmd)
    def one(cmd):return command(cmd).stderr
    with ThreadPoolExecutor(max_workers=4) as pool:logs=list(pool.map(one,commands))
    exe=C_BUILD/'pqc_bridge'
    link=[cc,*objects,'-Wl,--gc-sections','-lm','-o',exe];logs.append(command(link).stderr)
    # Separate original verifier TU, without any hooks or generated source.
    original_obj=C_BUILD/'original_vrfy.o';verify_main=C_BUILD/'verify_main.o'
    extra=[[cc,*flags,'-c',SOURCE/'vrfy.c','-o',original_obj],
           [cc,*flags,'-c',ROOT/'sim/ref/r8_verify_file.c','-o',verify_main]]
    for cmd in extra:logs.append(command(cmd).stderr)
    verify_link=[cc,*objects[:-2],original_obj,verify_main,'-Wl,--gc-sections','-lm','-o',C_BUILD/'independent_verify']
    logs.append(command(verify_link).stderr)
    (C_BUILD/'compiler.log').write_text('\n'.join(logs))
    assert reference()==sources_before,'reference source changed'
    manifest={'commit':COMMIT,'source_pristine':True,'source_sha256':sources_before,
              'compiler':command([cc,'--version']).stdout.splitlines()[0],
              'commands':[[str(x) for x in cmd] for cmd in [*commands,link,*extra,verify_link]],
              'generated_vrfy_sha256':digest(adapted),'instrumentation':{'definition_names_renamed':list(NAMES),'original_calls_preserved':True},
              'configuration':{'FALCON_FPR_MODE':2,'FALCON_AVX2':0,'FALCON_RAND_WIN32':0},
              'harness_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'sim/ref'/name for name in
                                 ('r8_pqc_bridge.h','r8_pqc_ntt.inc','r8_pqc_cosim.c','r8_verify_file.c')]}}
    (C_BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built pristine R8 + external kernel bridge and independent original verifier',flush=True)


def run_application(mode,logn,replacement=None,folder=None):
    folder=folder or mode
    out=BUILD/f'N{1<<logn}'/folder;out.mkdir(parents=True,exist_ok=True)
    args=[C_BUILD/'pqc_bridge',mode,str(logn),out,replacement or '-']
    with (out/'trace.jsonl').open('w') as f:
        p=subprocess.run([str(x) for x in args],stdout=f,stderr=subprocess.PIPE,text=True,timeout=120)
    (out/'stderr.log').write_text(p.stderr)
    if p.returncode:raise RuntimeError(f'{mode} N{1<<logn} returned {p.returncode}: {p.stderr}')
    print(mode,'N'+str(1<<logn),'completed',flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=('capture','replay','verify','guard'))
    ap.add_argument('--logn',type=int,choices=(9,10));args=ap.parse_args()
    if args.mode=='capture':
        build()
        for logn in (9,10):run_application('capture',logn)
    elif args.mode=='replay':
        for logn in (9,10):run_application('replay',logn,BUILD/f'N{1<<logn}'/'replacement.txt')
    elif args.mode=='verify':
        results=[]
        for logn in (9,10):
            out=BUILD/f'N{1<<logn}'/'replay'
            for trial in range(2):
                p=command([C_BUILD/'independent_verify',out/'pk.bin',out/f'sig{trial}.bin',out/f'msg{trial}.bin'])
                results.append({'n':1<<logn,'trial':trial,**json.loads(p.stdout)})
        (BUILD/'independent_verify.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results),flush=True)
    else:
        logn=args.logn or 9;work=BUILD/f'N{1<<logn}';original=work/'replacement.txt'
        # Corrupt the first live input word, not a checksum or an unused byte.
        lines=original.read_text().splitlines();words=lines[1].split()
        words[0]=str((int(words[0])+1)%12289) if len(words[0])!=32 else f'{int(words[0],16)^1:032x}'
        lines[1]=' '.join(words);bad=work/'bad_input.txt';bad.write_text('\n'.join(lines)+'\n')
        out=work/'guard';out.mkdir(exist_ok=True)
        p=subprocess.run([str(C_BUILD/'pqc_bridge'),'replay',str(logn),str(out),str(bad)],capture_output=True,text=True,timeout=120)
        assert p.returncode==7 and 'live ' in p.stderr,p.stderr
        (work/'guard_result.json').write_text(json.dumps({'returncode':p.returncode,'stderr':p.stderr},indent=2)+'\n')
        print('PASS: corrupted live-input record rejected',flush=True)


if __name__=='__main__':main()
