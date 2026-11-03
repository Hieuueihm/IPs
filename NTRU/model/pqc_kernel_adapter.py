"""Host kernel sequencing around actual flex_stream_banked RTL transactions.

FFT add/sub, 3M sequencing and scaling remain the pinned host contract. NTT
butterflies, modular products and normalization are delegated to array frames.
The frame backend can plan integer-oracle vectors or return actual RTL results.
"""
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from model.r8_golden import Core,wrap,parse_word
from model.ntt_banked_supply import bank,groups

MASK=(1<<128)-1
Q=12289
RINV=pow(65536,-1,Q)


def pack(values,width=16):
    return sum((v% (1<<width))<<(i*width) for i,v in enumerate(values))


def unpack(value,n,width=16):
    return [(value>>(i*width))&((1<<width)-1) for i in range(n)]


class Frames:
    def __init__(self):
        self.vectors=[];self.index={};self.actual=None;self.calls=Counter();self.hits=Counter()

    def exchange(self,vector,kind):
        self.calls[kind]+=1
        key=vector[:7]+vector[8:]
        idx=self.index.get(key)
        if self.actual is None:
            if idx is None:
                idx=len(self.vectors);self.index[key]=idx;self.vectors.append(vector)
            else:
                assert self.vectors[idx][7]==vector[7]
                self.hits[kind]+=1
            return vector[7]
        assert idx is not None,('RTL result missing for live reconstructed frame',kind)
        return self.actual[idx]

    def real_mul(self,x,y):
        # Signed multiplication and its rounding are commutative. Exact reuse
        # avoids simulating identical inputs repeatedly; no approximate cache.
        a,b=sorted((x&MASK,y&MASK))
        expected=wrap((x*y+(1<<63))>>64)&MASK
        result=self.exchange((0,2,0,0,0,a|(b<<512),0,expected,0,0),'FFT128_real_product')
        return wrap(result)

    def montgomery(self,a,b):
        assert len(a)==len(b)
        out=[]
        for start in range(0,len(a),64):
            aa=a[start:start+64];bb=b[start:start+64]
            products=[x*y*RINV%Q for x,y in zip(aa,bb)]
            data=pack([v for x in aa for v in (0,x)])
            expected=pack([v for p in products for v in (p,(-p)%Q)])
            got=self.exchange((1,0,0,0,0,data,pack(bb),expected,0,0),'NTT_scalar_montgomery')
            out += unpack(got,2*len(aa))[::2]
        return out

    def ntt(self,values,logn,inverse,table):
        n=1<<logn;current=values[:]
        assert len(current)==n and all(0<=x<Q for x in current)
        order=list(range(logn-1,-1,-1))
        if inverse:order.reverse()
        for stage in range(0,logn,2):
            paired=stage+1<logn;p=min(order[stage:stage+2]) if paired else order[stage]
            scheduled=groups(logn,p,paired,True,inverse);after=current[:]
            for start in range(0,len(scheduled),16):
                chunk=scheduled[start:start+16];indices=sum(chunk,[])
                rd=[0]*64;wr=[0]*64;roots=[];mask=0
                for positions in chunk:
                    data=[current[i] for i in positions]
                    if paired:
                        g=(n>>(p+2))+(positions[0]>>(p+2))
                        root=[table[g],table[2*g],table[2*g+1]]
                        applied=[root[1],root[2],root[0],root[0]] if inverse else [root[0],root[0],root[1],root[2]]
                    else:
                        pairs=((0,1),(2,3)) if inverse else ((0,2),(1,3))
                        root=[table[(n>>(p+1))+(positions[i]>>(p+1))] for i,j in pairs]
                        applied=root
                    first=((0,1),(2,3)) if inverse else ((0,2),(1,3))
                    second=((0,2),(1,3)) if inverse else ((0,1),(2,3))
                    for z,(i,j) in enumerate((*first,*second) if paired else first):
                        a,b=data[i],data[j];w=applied[z]
                        if inverse:data[i],data[j]=(a+b)%Q,(a-b)*w*RINV%Q
                        else:
                            t=b*w*RINV%Q;data[i],data[j]=(a+t)%Q,(a-t)%Q
                    roots.append(pack(root))
                    for k,i in enumerate(positions):
                        rd[bank(i)]=current[i];wr[bank(i)]=data[k];mask|=1<<bank(i)
                offset=bank(indices[0]);assert offset&15==0
                control=(p<<28)|((offset>>4)<<26)|(logn<<22)
                got=self.exchange((1,0,1 if paired else 2,0,int(inverse),pack(rd),pack(roots,48 if paired else 32),pack(wr),control,mask),'NTT_banked_pass')
                words=unpack(got,64)
                for i in indices:after[i]=words[bank(i)]
            current=after
        if inverse:
            ni=65536*pow(n,-1,Q)%Q
            current=self.montgomery(current,[ni]*n)
        return current


def evaluate(record,rom,ntt_rom,frames):
    if record['op'] in ('FFT','IFFT','CMUL','SPLIT','MERGE'):
        class HardwareProducts(Core):
            def mul(self,x,y):return frames.real_mul(x,y)
        y,z=HardwareProducts(rom,32).evaluate(record)
        return [x&MASK for x in y],None if z is None else [x&MASK for x in z]
    op=record['op'];a=record['a'];n=len(a)
    if op in ('NTT','INTT'):
        inverse=op=='INTT'
        return frames.ntt(a,record['logn'],inverse,ntt_rom['inverse' if inverse else 'forward']),None
    if op=='MODMUL':return frames.montgomery(a,record['b']),None
    if op=='TOMONT':return frames.montgomery(a,[10952]*n),None
    raise AssertionError(op)
