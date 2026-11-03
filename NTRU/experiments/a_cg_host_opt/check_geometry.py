"""Exhaustively prove disjoint address fields for all accepted geometries."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/a_cg_batch'))
import planner

def host_selection(c,fft,fmt,ln,checks):
    n=c['n'];bl=c['base_log'];pack=fmt if fft else bl
    words=(1<<c['job_word_log'])*c['jobs']
    mask=1 if fft and n==0 and fmt==0 else 3 if fft and n==0 else 1 if fft and n==1 and fmt==0 else (1<<pack)-1
    for flip in (0,1):
        shift=5-c['bj'] if flip else 5-n-c['bj']
        for first in range(0,words,4):
            elem=first>>pack;p=elem&(c['m']-1);job=first>>c['job_word_log']
            jb=job&((1<<c['bj'])-1);jr=job>>c['bj']
            plane=(jr<<bl)|((((elem>>n)&1)<<fmt) if fft and ln else 0)
            base=((p&31)^(((p>>(n-1))&1)<<4)) if n>=6 else ((p if flip else p<<(5-n))^(jb<<shift))
            bank_basis=[];phase_basis=[]
            for hb in range(2):
                lane=hb<pack;bit=(hb-pack)&7;isjob=hb>=c['job_word_log']
                position=not isjob and not lane and bit<n
                component=not isjob and fft and not lane and bit==n
                pd=(1<<bit)&31
                tiny=(pd if flip else pd<<(5-n)) if n<6 else 0
                delta=(1<<(shift+hb-c['job_word_log'])) if isjob else (pd^(16 if bit==n-1 else 0)) if position and n>=6 else tiny if position else 0
                bank_basis.append(delta&31)
                phase_basis.append(((1<<hb) if lane else (1<<fmt) if component else 0)&3)
            selected={ph:[] for ph in range(mask+1)}
            for j in range(4):
                word=first+j
                if word>=words:continue
                actual=(base^(bank_basis[0] if j&1 else 0)^(bank_basis[1] if j&2 else 0))&31
                phase=((plane&3)^(phase_basis[0] if j&1 else 0)^(phase_basis[1] if j&2 else 0))&mask
                job=word>>c['job_word_log'];local=word&((1<<c['job_word_log'])-1)
                jb=job&((1<<c['bj'])-1);jr=job>>c['bj']
                element=local>>pack;pos=element&(c['m']-1)
                bp=(((element>>n)<<fmt) if fft and ln else 0)|(local&((1<<pack)-1))
                expect=planner.bank(pos,jb,n,n if flip else 0,c['bj'])
                assert actual==expect
                assert phase==(((jr<<bl)|bp)&mask)
                assert actual not in selected[phase],('host bank collision',c,flip,first,j,phase,actual)
                selected[phase].append(actual);checks+=1
    return checks

def main():
    geometries=[];composed=far=host_checks=0
    configs=[]
    for ln in range(11):
        for fmt in range(3):configs.append((1,fmt,ln,0,0))
    for ln in range(1,11):
        for hm in range(min(2,ln-1)+1):
            for packed in (0,1):configs.append((0,0,ln,hm,packed))
    for fft,fmt,ln,hm,packed in configs:
        for jl in range(5):
            try:c=planner.config(fft,fmt,ln,hm,packed,jl)
            except AssertionError:continue
            rows,planes=c['rows'],c['planes'];size=rows*planes
            assert size<=128
            for buf in (0,1):
                for pl in range(planes):
                    for k in range(rows):
                        a,b,d=buf*size,pl*rows,k
                        assert (a&b)==(a&d)==(b&d)==0
                        assert a+b+d==(a|b|d)<256
                        composed+=1
            off=rows//2 if c['n']>=6 else 0
            for k in range(rows):
                for half in (0,1):
                    a,b=k>>1,off if half else 0
                    assert a&b==0 and a+b==(a|b)<rows
                    far+=1
            host_checks=host_selection(c,fft,fmt,ln,host_checks)
            geometries.append(dict(fft=fft,fmt=fmt,logn=ln,hmin=hm,packed=packed,jobs_log=jl,rows=rows,planes=planes))
    out=ROOT/'study/build/a_cg_host_opt';out.mkdir(parents=True,exist_ok=True)
    result=dict(result='PASS',geometry_count=len(geometries),row_compositions=composed,far_compositions=far,host_word_mappings=host_checks,one_valid_word_per_bank_phase=True,geometries=geometries,
        scope='All accepted address dimensions; fields OR equals integer addition for active valid addresses. Does not prove arbitrary invalid configuration states.')
    (out/'geometry_proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='geometries'}))

if __name__=='__main__':main()
