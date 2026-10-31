"""Integer-only custom FFT32/64 contracts. No PQC accuracy claim for these widths."""
def evaluate(op, a, b, logn, width, rom):
    mask=(1<<width)-1;fraction=width//2
    def wrap(x):
        x&=mask
        return x-(1<<width) if x>>(width-1) else x
    def div(x,s):return wrap(x+((1<<s)>>1))>>s
    def root(k,inv=False):
        re,im=rom[2*k:2*k+2]
        if inv:im=-im
        shift=64-fraction
        return tuple(wrap((x+(1<<(shift-1)))>>shift) for x in (re,im))
    def mul(x,y):return wrap((x*y+(1<<(fraction-1)))>>fraction)
    def cmul(ar,ai,br,bi):
        p=mul(ar,br);q=mul(ai,bi);s=mul(wrap(ar+ai),wrap(br+bi))
        return wrap(p-q),wrap(s-p-q)
    a=[wrap(x) for x in a];b=[wrap(x) for x in b]
    n=1<<logn;hn=n//2;qn=hn//2
    if op=='FFT':
        span=hn;groups=2
        while span>=2:
            for g in range(groups//2):
                for j in range(g*span,g*span+span//2):
                    ar,ai=a[j],a[j+hn];tr,ti=cmul(a[j+span//2],a[j+span//2+hn],*root(groups+g))
                    a[j],a[j+hn]=wrap(ar+tr),wrap(ai+ti)
                    a[j+span//2],a[j+span//2+hn]=wrap(ar-tr),wrap(ai-ti)
            span//=2;groups*=2
        out=a
    elif op=='IFFT':
        stride=1;groups=n
        while groups>2:
            for g in range(groups//4):
                for j in range(g*2*stride,g*2*stride+stride):
                    ar,ai,br,bi=a[j],a[j+hn],a[j+stride],a[j+stride+hn]
                    a[j],a[j+hn]=wrap(ar+br),wrap(ai+bi)
                    a[j+stride],a[j+stride+hn]=cmul(wrap(ar-br),wrap(ai-bi),*root(groups//2+g,True))
            stride*=2;groups//=2
        out=[div(x,logn-1) for x in a] if logn else a
    elif op=='CMUL':
        out=[0]*n
        for j in range(hn):out[j],out[j+hn]=cmul(a[j],a[j+hn],b[j],b[j+hn])
    elif op=='SPLIT':
        if n==2:out=a[:]
        else:
            out=[0]*n
            for j in range(qn):
                ar,ai,br,bi=a[2*j],a[2*j+hn],a[2*j+1],a[2*j+1+hn]
                out[j],out[j+qn]=div(wrap(ar+br),1),div(wrap(ai+bi),1)
                tr,ti=cmul(wrap(ar-br),wrap(ai-bi),*root(j+hn,True))
                out[j+hn],out[j+hn+qn]=div(tr,1),div(ti,1)
    elif op=='MERGE':
        if n==2:out=[a[0],b[0]]
        else:
            out=[0]*n
            for j in range(qn):
                tr,ti=cmul(b[j],b[j+qn],*root(j+hn))
                out[2*j],out[2*j+hn]=wrap(a[j]+tr),wrap(a[j+qn]+ti)
                out[2*j+1],out[2*j+1+hn]=wrap(a[j]-tr),wrap(a[j+qn]-ti)
    else:raise ValueError(op)
    return [x% (1<<128) for x in out]
