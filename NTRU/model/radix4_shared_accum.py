"""Exact arithmetic analysis of radix-4 factoring and shared accumulation.

No RTL PPA or transform speedup is estimated. Run from any working directory:
    python -X utf8 model/radix4_shared_accum.py
"""
import importlib.util
import hashlib
import json
from pathlib import Path
from random import Random

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('cluster_reference',ROOT/'scripts/prototype_ntt_cluster.py')
ref=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
PROFILES={12289:{'a':12,'k':3,'c':1479},3329:{'a':8,'k':13,'c':1729}}
R=1<<16

def naf(x):
    terms=[]; shift=0
    while x:
        if x&1:
            digit=2-(x&3)
            terms.append((shift,digit)); x-=digit
        x//=2;shift+=1
    return terms

def encode_terms(terms,width):
    """terms=(unsigned value, shift, sign), normalized modulo 2^width.

    Complement negative words and inject their +1 bias into known zero bits of
    a shifted positive operand when possible. No hidden discarded carry.
    """
    mask=(1<<width)-1
    words=[((x<<shift)&mask) if sign==1 else (~(x<<shift)&mask) for x,shift,sign in terms]
    bias=sum(sign<0 for _,_,sign in terms)
    if bias:
        for i,(_,shift,sign) in enumerate(terms):
            if sign==1 and shift>=bias.bit_length():
                assert words[i]&bias==0
                words[i]|=bias;break
        else:
            words.append(bias)
    return words

def reduce_csa(words,width,lane_width=None):
    lane_width=lane_width or width
    assert width%lane_width==0
    mask=(1<<width)-1
    cuts=sum(1<<bit for bit in range(lane_width,width,lane_width))
    words=words[:];count=0
    while len(words)>2:
        x,y,z=words[:3]
        s=x^y^z
        carry=(((x&y)|(x&z)|(y&z))<<1)&mask&~cuts
        words=[s,carry,*words[3:]];count+=1
    if len(words)==1:return words[0],count
    result=0
    for bit in range(0,width,lane_width):
        lm=(1<<lane_width)-1
        result|=((((words[0]>>bit)&lm)+((words[1]>>bit)&lm))&lm)<<bit
    return result,count

def sum_terms(terms,width):
    return reduce_csa(encode_terms(terms,width),width)[0]

def mont(t,q):
    m=(t*(-pow(q,-1,R)))%R
    u=(t+m*q)//R
    return u-q if u>=q else u

def compact_parts(t,q):
    p=PROFILES[q];a=p['a'];k=p['k'];s=16-a
    lo=t&65535
    m=((k*(lo&((1<<s)-1))<<a)-lo)&65535
    h=m>>s;l=m&((1<<s)-1)
    high=k*h+(((k*l<<a)+m)>>16)
    u=(t>>16)+high+int(lo!=0)
    return m,high,u,u-q if u>=q else u

def forward(x,u,c,q,use_mont=False):
    def product(a,b):return mont(a*(b*R%q),q) if use_mont else a*b%q
    p1=product(x[1],u);p2=product(x[2],u*u%q);p3=product(x[3],pow(u,3,q))
    a=(x[0]+p2)%q;b=(x[0]-p2)%q
    s=(p1+p3)%q;d=product((p1-p3)%q,c)
    return [(a+s)%q,(a-s)%q,(b+d)%q,(b-d)%q]

def backward(x,u,ci,q,use_mont=False):
    def product(a,b):return mont(a*(b*R%q),q) if use_mont else a*b%q
    a=(x[0]+x[1])%q;b=(x[0]-x[1])%q
    s=(x[2]+x[3])%q;d=product((x[2]-x[3])%q,ci)
    return [(a+s)%q,product((b+d)%q,u),product((a-s)%q,u*u%q),product((b-d)%q,pow(u,3,q))]

def paired(x,roots,q,inverse):
    y=x[:]
    first=((0,1),(2,3)) if inverse else ((0,2),(1,3))
    second=((0,2),(1,3)) if inverse else ((0,1),(2,3))
    for j,(a,b) in enumerate(first):y[a],y[b]=ref.bf(x[a],x[b],roots[j],q,inverse)
    z=y[:]
    for j,(a,b) in enumerate(second):z[a],z[b]=ref.bf(y[a],y[b],roots[j+2],q,inverse)
    return z

def check_actual_stage_pairs(rng):
    count=0; contexts=[]
    for q,p in PROFILES.items():
        sizes=(8,16,32,64,128,256,512,1024) if q==12289 else (8,16,32,64,128,256)
        for n in sizes:
            fs,bs,_=ref.stages(q,n,q==3329 and n==256)
            constants={False:set(),True:set()}
            for inverse,layers in ((False,fs),(True,bs)):
                for layer_index in range(0,len(layers)-1,2):
                    f={a:(b,w) for a,b,w in layers[layer_index]}
                    s={a:(b,w) for a,b,w in layers[layer_index+1]}
                    used=set()
                    for a in sorted(f):
                        if a in used:continue
                        if inverse:
                            b,w0=f[a];c,w2=s[a];d,w1=f[c];d2,w3=s[b]
                            assert w2==w3==w0*w0%q
                            u=w0;imag=w1*pow(u,-1,q)%q
                        else:
                            c,w0=f[a];b,w2=s[a];d,w1=f[b];d2,w3=s[c]
                            assert w0==w1==w2*w2%q
                            u=w2;imag=w3*pow(u,-1,q)%q
                        assert d==d2 and imag*imag%q==q-1
                        used.update((a,b,c,d));constants[inverse].add(imag)
                        x=[rng.randrange(q) for _ in range(4)]
                        expected=paired(x,[w0,w1,w2,w3],q,inverse)
                        factor=backward if inverse else forward
                        assert factor(x,u,imag,q)==expected
                        assert factor(x,u,imag,q,True)==expected
                        count+=1
            assert constants[False]=={p['c']}
            assert constants[True]=={q-p['c']}
            contexts.append({'q':q,'n':n,'forward_c':p['c'],'inverse_c':q-p['c'],
                             'paired_layers':len(fs)//2,'radix2_tail':len(fs)%2})
    return count,contexts

def main():
    rng=Random(20261026)
    root_checks,contexts=check_actual_stage_pairs(rng)
    rows=[]
    for q,p in PROFILES.items():
        a=p['a'];k=p['k'];s=16-a;c=p['c'];constant_checks=0
        # Exhaust all possible Montgomery m words and input low words.
        for value in range(R):
            h=value>>s;l=value&((1<<s)-1)
            assert k*h+(((k*l<<a)+value)>>16)==value*q>>16
            m=((k*(value&((1<<s)-1))<<a)-value)&65535
            assert m==value*(-pow(q,-1,R))%R
        constants=[]
        for imag in (c,q-c):
            constant=imag*R%q;terms=naf(constant)
            assert sum(sign*(1<<shift) for shift,sign in terms)==constant
            for x in range(q):
                t=sum_terms([(x,shift,sign) for shift,sign in terms],32)
                assert t==x*constant
                assert mont(t,q)==x*imag%q
                constant_checks+=1
            constants.append({'c':imag,'montgomery_constant':constant,
                              'csd_terms':terms,'shift_add_terms':len(terms),
                              'max_t_bits':((q-1)*constant).bit_length()})
        cases=[(x,y) for x in (0,1,q//2,q-1) for y in (0,1,q//2,q-1)]
        cases.extend((rng.randrange(q),rng.randrange(q)) for _ in range(5000))
        for x,y in cases:
            t=x*y;m,high,u,out=compact_parts(t,q)
            assert high==m*q>>16
            assert u==(t+m*q)>>16
            assert out==mont(t,q)==t*pow(R,-1,q)%q
            full_terms=[(t,0,1)]+[(m,shift,sign) for shift,sign in naf(q)]
            assert sum_terms(full_terms,32)==t+m*q
            # Two 32-bit lanes share a 64-bit compressor with carry cuts.
            t2=rng.randrange(q)*rng.randrange(q)
            m2=t2*(-pow(q,-1,R))%R
            words0=encode_terms(full_terms,32)
            words1=encode_terms([(t2,0,1)]+[(m2,sh,sg) for sh,sg in naf(q)],32)
            assert len(words0)==len(words1)
            merged=[lo|(hi<<32) for lo,hi in zip(words0,words1)]
            result,_=reduce_csa(merged,64,32)
            assert result==(t+m*q)|((t2+m2*q)<<32)
            # Three modulo products + one fixed product, both CT and GS.
            data=[rng.randrange(q) for _ in range(4)];u0=rng.randrange(1,q)
            y0=paired(data,[u0*u0%q,u0*u0%q,u0,c*u0%q],q,False)
            assert forward(data,u0,c,q,True)==y0
            ui=pow(u0,-1,q);ci=q-c
            expected=paired(y0,[ui,ci*ui%q,ui*ui%q,ui*ui%q],q,True)
            assert backward(y0,ui,ci,q,True)==expected
            assert [v*pow(4,-1,q)%q for v in expected]==data
        lmax=(1<<s)-1
        rows.append({'q':q,'a':a,'k':k,'constants':constants,
                     'all_m_words_checked':R,'all_t_low_words_checked':R,
                     'exhaustive_constant_inputs':constant_checks,'random_boundary_product_cases':len(cases),
                     'full_s_max_bound':(q-1)**2+(R-1)*q,
                     'full_s_bits':((q-1)**2+(R-1)*q).bit_length(),
                     'compact_low_carry_bits':((k*lmax<<a)+R-1).bit_length(),
                     'compact_mq_high_bits':(q-1).bit_length(),
                     'compact_u_max_bound':(((q-1)**2)>>16)+q,
                     'compact_u_bits':((((q-1)**2)>>16)+q).bit_length()})
    # Existing FFT32 limb products retain all bits; CSA works modulo 2^64.
    for _ in range(5016):
        x=ref.signed(rng.getrandbits(32),32);y=ref.signed(rng.getrandbits(32),32)
        xl=x&65535;xh=x>>16;yl=y&65535;yh=y>>16
        terms=[(xl*yl,0,1),(xh*yl,16,1),(xl*yh,16,1),(xh*yh,32,1)]
        # Signed partial values can be supplied as sign-extended words.
        words=[(v<<shift)% (1<<64) for v,shift,_ in terms]
        assert reduce_csa(words,64)[0]==x*y% (1<<64)
    # Negative controls: detect discarded Montgomery carry, root encoding and
    # carry leakage across packed lanes, rather than silently accepting them.
    controls=[]
    for q,p in PROFILES.items():
        _,_,u,expected=compact_parts(1,q)
        assert (u-1)%q!=expected
        assert mont(p['c'],q)!=p['c']
        controls.extend([f'q{q}: omitted low-half carry detected',
                         f'q{q}: unencoded c used in Montgomery detected'])
    for words in ([0x80000000,0x80000000,0],[0xffffffff,1,0]):
        assert reduce_csa(words,64,32)[0]==0
        assert reduce_csa(words,64,64)[0]==1<<32
    controls.append('compressor and final-CPA cross-lane carry leakage detected')
    result={'profiles':rows,'actual_stage_pair_cases':root_checks,'contexts':contexts,
            'fft32_csa_cases':5016,'mismatches':0,
            'negative_controls':controls,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                             for name in ('model/radix4_shared_accum.py','scripts/prototype_ntt_cluster.py')},
            'limits':['Integer arithmetic model only; no RTL or area/timing measurements for these two new candidates.',
                      'Radix4 variable-product count does not include the fixed-c multiplication and its reduction.',
                      'Shared compressor capacity is 1x64 FFT or 2x32 NTT; not four full NTT reductions/cycle.',
                      'Compact Montgomery is profile-specific, not arbitrary-modulus or lazy-input support.']}
    out=ROOT/'study/results/radix4_shared_accum.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {root_checks} actual stage-pair cases; 5016 FFT32 CSA cases; zero mismatches.')
    for row in rows:
        print(f'q={row["q"]}: all 65536 m words + 65536 T-low words; '
              f'{row["exhaustive_constant_inputs"]} fixed-root inputs; '
              f'{row["random_boundary_product_cases"]} boundary/random cases.')
    print(out)

if __name__=='__main__':main()
