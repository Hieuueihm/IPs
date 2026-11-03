"""Exhaustive equivalence to the previous full-index host mapping."""
import importlib.util
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
sp=importlib.util.spec_from_file_location('mapcg',ROOT/'model/cg_bank4_model.py')
cg=importlib.util.module_from_spec(sp);sp.loader.exec_module(cg)
checks=configs=0
for fft in (0,1):
    for ln in range(0 if fft else 1,11):
        for fmt in (range(3) if fft else (0,)):
            for hm in ((0,) if fft else range(min(2,ln-1)+1)):
                n=max(0,ln-1) if fft else ln-hm
                m=1<<n;pack=fmt if fft else hm
                planes=(2<<fmt) if fft else 1<<hm
                rows=max(1,m//32);rowlog=max(0,n-5);bufrows=planes*rows
                total=(1<<ln) << (fmt if fft else 0)
                for inv in (0,1):
                    for out in (0,1):
                        st=(0 if inv else n) if out else (n if inv else 0)
                        def original(j):
                            el=j>>pack;p=el&(m-1)
                            plane=((((el>>n)&1)<<fmt)+(j&((1<<fmt)-1))) if fft else j&(planes-1)
                            return cg.bank(p,m,st),(n%2*bufrows if out else 0)+plane*rows+(p>>5)
                        db=[];dr=[];dp=[]
                        for b in range(2):
                            lane=b<pack;pbit=b-pack
                            pos=not lane and pbit<n
                            component=fft and not lane and pbit==n
                            db.append(cg.bank(1<<pbit,m,st) if pos else 0)
                            dr.append((1<<(rowlog+b)) if lane else (1<<(rowlog+fmt)) if component else 0)
                            dp.append((1<<b) if lane else (1<<fmt) if component else 0)
                        for first in range(0,total,4):
                            bank,row=original(first)
                            for j in range(min(4,total-first)):
                                new=(bank^(db[0] if j&1 else 0)^(db[1] if j&2 else 0),
                                     row^(dr[0] if j&1 else 0)^(dr[1] if j&2 else 0))
                                assert new==original(first+j),(fft,ln,fmt,hm,inv,out,first,j,new,original(first+j))
                                def plane(word):
                                    return ((((word>>fmt>>n)&1)<<fmt)+(word&((1<<fmt)-1))) if fft else word&(planes-1)
                                phase=(plane(first)^(dp[0] if j&1 else 0)^(dp[1] if j&2 else 0))&3
                                assert phase==(plane(first+j)&3)
                                checks+=1
                        configs+=1
out=ROOT/'study/build/a_cg_tune/host_map_equivalence.json'
out.write_text(json.dumps(dict(configurations=configs,word_mappings=checks,result='PASS'),indent=2)+'\n')
print(configs,'configurations,',checks,'word mappings PASS')
