"""Independent job inputs and logical-transform oracles for the new modes."""
import importlib.util
import random
from pathlib import Path
from planner import config

ROOT=Path(__file__).resolve().parents[4]


def extend(cases,cg):
    rng=random.Random(20261103);extra=[]
    def evaluation(a,q,ln,hm):
        # Direct polynomial evaluation by Horner, independent of butterfly RTL.
        m=1<<(ln-hm);b=1<<hm;psi=cg.pc.psi_of(q,2*m);out=[]
        for k in range(m):
            z=pow(psi,2*cg.pc.rev(k,ln-hm)+1,q)
            for j in range(b):
                v=0
                for i in range(len(a)-b+j,j-1,-b):v=(v*z+a[i])%q
                out.append(v)
        return out
    for c in cases:
        if not c[1] and c[6]<32768:extra.append((*c,1,0))
    # Logical evaluation oracle for NTT (rather than cloning the CG loop).
    for q,ln,hm in [(12289,l,h) for l in (1,2,3,4,5,8,9,10) for h in range(min(2,l-1)+1)]+[(3329,8,1),(18433,8,0),(10753,8,0),(8380417,8,0)]:
        gm,igm=cg.pc.tables(q,ln,hm)
        for packed in (0,1) if q<32768 else (0,):
            for jl in (0,1,2,3,4):
                try:config(0,0,ln,hm,packed,jl)
                except AssertionError:continue
                if not packed and jl==0:continue
                a=[];z=[]
                for job in range(1<<jl):
                    v=[rng.randrange(q) for _ in range(1<<ln)]
                    if job==0:v=[(q-1 if j%2 else 0) for j in range(1<<ln)]
                    a.extend(v);z.extend(evaluation(v,q,ln,hm))
                prefix=f'new_NTT_q{q}_N{1<<ln}_h{hm}_p{packed}_J{1<<jl}'
                extra.extend([(prefix+'_f',0,0,ln,hm,False,q,a,z,gm,igm,0,packed,jl),
                              (prefix+'_i',0,0,ln,hm,True,q,z,a,gm,igm,0,packed,jl)])
    sp=importlib.util.spec_from_file_location('native_oracle',ROOT/'scripts/check_spec2_kernel_assets.py')
    native=importlib.util.module_from_spec(sp);sp.loader.exec_module(native)
    gm_native=[(int(v,16)>>64,int(v,16)&((1<<64)-1)) for v in (ROOT/'spec/FlexTransform/2.0/assets/fft_ntrugen_q32_32.mem').read_text().split()]
    for fmt in range(3):
        for ln in (0,1,2,3,4,5,6,8):
            w=32*(1<<fmt)
            for nr in ((0,1) if fmt==1 and ln else (0,)):
                gm=gm_native if nr else cg.fp.roots(w)
                igm=[(cg.fp.wrap(r,w),cg.fp.wrap(-i,w)) for r,i in gm] if nr else cg.fp.roots_inv(w)
                for jl in (1,2,3,4):
                    try:config(1,fmt,ln,0,0,jl)
                    except AssertionError:continue
                    for inv in (False,True):
                        a=[];z=[]
                        for job in range(1<<jl):
                            v=[cg.fp.wrap(rng.getrandbits(w),w) for _ in range(1<<ln)]
                            if nr:
                                ref=(native.ifft_ntrugen if inv else native.fft_ntrugen)(v,ln,gm)
                                out=[cg.fp.wrap(x,w) for x in ref]
                            else:out=v if ln==0 else (cg.fp.ifft(v,ln,w,igm) if inv else cg.fp.fft(v,ln,w,gm))
                            a.extend(v);z.extend(out)
                        extra.append((f'new_FFT{w}_n{ln}_r{nr}_J{1<<jl}_{int(inv)}',1,fmt,ln,0,inv,0,a,z,gm,igm,nr,0,jl))
    return cases+extra
