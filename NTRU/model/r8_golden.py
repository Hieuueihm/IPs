"""Q64.64 core model driven by exact constants exported by pinned R8 C.

The multiplier uses the proposed interleaved-index fixed-shift tree, wraps at
192 bits and drops only terms with weight >=192. No binary floating point.
No cycle scheduling, handshakes or RTL are modeled.
"""
WIDTH = 128
FRACTION = 64
MASK = (1 << WIDTH) - 1


def wrap(x):
    x &= MASK
    return x - (1 << WIDTH) if x >> 127 else x


def parse_word(x):
    return wrap(int(x, 16))


class Core:
    def __init__(self, rom, leaf):
        assert leaf in (16, 32) and len(rom) == 2048
        self.rom = rom
        self.leaf = leaf
        k = WIDTH // leaf
        nb = k.bit_length() - 1
        self.shifts = [leaf << (level // 2) for level in range(2 * nb)]
        self.order = [(sum(((t >> (2*m)) & 1) << m for m in range(nb)),
                       sum(((t >> (2*m+1)) & 1) << m for m in range(nb)))
                      for t in range(k*k)]
        self.mul_calls = 0

    def mul(self, x, y):
        g = self.leaf
        k = WIDTH // g
        lm = (1 << g) - 1
        a = [((x & MASK) >> (i*g)) & lm for i in range(k)]
        b = [((y & MASK) >> (i*g)) & lm for i in range(k)]
        if a[-1] >> (g-1):
            a[-1] -= 1 << g
        if b[-1] >> (g-1):
            b[-1] -= 1 << g
        nodes = [a[i]*b[j] if g*(i+j) < 192 else 0 for i, j in self.order]
        mask = (1 << 192)-1
        for shift in self.shifts:
            nodes = [(nodes[i]+(nodes[i+1] << shift)) & mask
                     for i in range(0, len(nodes), 2)]
        self.mul_calls += 1
        return wrap((nodes[0]+(1 << 63)) >> 64)

    @staticmethod
    def div2e(x, shift):
        return wrap(x + ((1 << shift) >> 1)) >> shift

    def cmul(self, ar, ai, br, bi):
        p0 = self.mul(ar, br)
        p1 = self.mul(ai, bi)
        # This is also the required ROM value for a currently selected twiddle.
        precomputed_sum = wrap(br+bi)
        p2 = self.mul(wrap(ar+ai), precomputed_sum)
        return wrap(p0-p1), wrap(p2-p0-p1)

    def root(self, index, inverse=False):
        re, im = self.rom[2*index:2*index+2]
        return re, wrap(-im) if inverse else im

    def fft(self, data, logn):
        a = data[:]
        n = 1 << logn
        hn = n//2
        stride = hn
        groups = 2
        for _ in range(1, logn):
            half_stride = stride//2
            for i in range(groups//2):
                sr, si = self.root(groups+i)
                start = i*stride
                for j in range(start, start+half_stride):
                    ar, ai = a[j], a[j+hn]
                    br, bi = self.cmul(a[j+half_stride], a[j+half_stride+hn], sr, si)
                    a[j], a[j+hn] = wrap(ar+br), wrap(ai+bi)
                    a[j+half_stride], a[j+half_stride+hn] = wrap(ar-br), wrap(ai-bi)
            stride = half_stride
            groups *= 2
        return a

    def ifft(self, data, logn):
        a = data[:]
        n = 1 << logn
        hn = n//2
        stride = 1
        groups = n
        for _ in range(logn, 1, -1):
            half_groups = groups//2
            for i, start in enumerate(range(0, hn, 2*stride)):
                sr, si = self.root(half_groups+i, inverse=True)
                for j in range(start, start+stride):
                    ar, ai, br, bi = a[j], a[j+hn], a[j+stride], a[j+stride+hn]
                    a[j], a[j+hn] = wrap(ar+br), wrap(ai+bi)
                    a[j+stride], a[j+stride+hn] = self.cmul(wrap(ar-br), wrap(ai-bi), sr, si)
            stride *= 2
            groups = half_groups
        return [self.div2e(x, logn-1) for x in a] if logn else a

    def poly_mul(self, a, b):
        hn = len(a)//2
        out = [0]*len(a)
        for i in range(hn):
            out[i], out[i+hn] = self.cmul(a[i], a[i+hn], b[i], b[i+hn])
        return out

    def split(self, a):
        hn = len(a)//2
        qn = hn//2
        f0, f1 = [0]*hn, [0]*hn
        f0[0], f1[0] = a[0], a[hn]
        for i in range(qn):
            ar, ai = a[2*i], a[2*i+hn]
            br, bi = a[2*i+1], a[2*i+1+hn]
            f0[i], f0[i+qn] = self.div2e(wrap(ar+br), 1), self.div2e(wrap(ai+bi), 1)
            tr, ti = self.cmul(wrap(ar-br), wrap(ai-bi), *self.root(i+hn, inverse=True))
            f1[i], f1[i+qn] = self.div2e(tr, 1), self.div2e(ti, 1)
        return f0, f1

    def merge(self, f0, f1):
        hn = len(f0)
        qn = hn//2
        out = [0]*(2*hn)
        out[0], out[hn] = f0[0], f1[0]
        for i in range(qn):
            br, bi = self.cmul(f1[i], f1[i+qn], *self.root(i+hn))
            ar, ai = f0[i], f0[i+qn]
            out[2*i], out[2*i+hn] = wrap(ar+br), wrap(ai+bi)
            out[2*i+1], out[2*i+1+hn] = wrap(ar-br), wrap(ai-bi)
        return out

    def evaluate(self, record):
        a = [parse_word(x) for x in record['a']]
        op = record['op']
        if op == 'FFT':
            return self.fft(a, record['logn']), None
        if op == 'IFFT':
            return self.ifft(a, record['logn']), None
        if op == 'CMUL':
            return self.poly_mul(a, [parse_word(x) for x in record['b']]), None
        if op == 'SPLIT':
            return self.split(a)
        if op == 'MERGE':
            return self.merge(a, [parse_word(x) for x in record['b']]), None
        raise ValueError(op)
