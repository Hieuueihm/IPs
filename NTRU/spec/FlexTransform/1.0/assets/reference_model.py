"""FT-SPEC-1.0 executable integer oracle. No RTL, float or cycle modeling.

Words returned by kernels are unsigned bit patterns of precisely the format.
The normative math is in 01_numeric_kernels.md; this model must agree with it.
"""
from pathlib import Path

OPS = {name: i for i, name in enumerate(
    ('FFT', 'IFFT', 'CMUL', 'SPLIT', 'MERGE', 'NTT', 'INTT', 'TOMONT', 'MODMUL'))}
WIDTHS = (32, 64, 128, 16)


def signed(x, width):
    x &= (1 << width) - 1
    return x - (1 << width) if x & (1 << (width - 1)) else x


def mul(a, b, width):
    return signed((signed(a, width) * signed(b, width)
                   + (1 << (width // 2 - 1))) >> (width // 2), width)


def div2e(a, shift, width):
    return signed(a, width) if shift == 0 else signed(a + (1 << (shift - 1)), width) >> shift


def mont(a, b, q):
    if not (0 <= a < q and 0 <= b < q):
        raise ValueError('noncanonical NTT input')
    t = a * b
    m = (t * (-pow(q, -1, 65536))) & 65535
    u = (t + m * q) >> 16
    return u - q if u >= q else u


def validate(cmd):
    """Command error priority. Inputs are already decoded unsigned port values."""
    op = cmd['op']
    if cmd.get('reserved', 0):
        return 1
    if op not in range(9):
        return 2
    if cmd['fmt'] not in ((0, 1, 2) if op < 5 else (3,)):
        return 3
    profile = cmd['profile']
    if profile not in ((0,) if op < 5 else (0, 1)):
        return 4
    logn = cmd['logn']
    low, high = ((0 if op < 2 else 1), 10) if op < 5 else (3, 10 if profile == 0 else 8)
    if not low <= logn <= high:
        return 5
    limit = 1 if op < 5 or logn >= 6 else (1 << (6 - logn))
    if not 1 <= cmd['jobs'] <= limit:
        return 6
    return 0


def read_roots(asset_dir=None):
    p = Path(asset_dir) if asset_dir else Path(__file__).parent
    fft = []
    for line in (p / 'fft_q64_64.mem').read_text().splitlines():
        value = int(line, 16)
        fft.append((signed(value >> 128, 128), signed(value, 128)))
    ntt = {}
    for q in (12289, 3329):
        for inv in (False, True):
            suffix = 'inverse' if inv else 'forward'
            ntt[q, inv] = [int(x, 16) for x in (p / f'ntt_q{q}_{suffix}.mem').read_text().splitlines()]
    return fft, ntt


def fft_kernel(op, a, b, logn, width, roots):
    w = lambda x: signed(x, width)
    add = lambda x, y: w(x + y)
    sub = lambda x, y: w(x - y)

    def root(k, inverse=False):
        re, im = roots[k]
        im = signed(-im, 128) if inverse else im
        shift = 64 - width // 2
        return (re, im) if not shift else tuple(w((x + (1 << (shift - 1))) >> shift) for x in (re, im))

    def cmul(ar, ai, br, bi):
        p0 = mul(ar, br, width)
        p1 = mul(ai, bi, width)
        p2 = mul(add(ar, ai), add(br, bi), width)
        return sub(p0, p1), sub(sub(p2, p0), p1)

    a, b = [w(x) for x in a], [w(x) for x in b]
    n = 1 << logn
    hn, qn = n // 2, n // 4
    if op == 'FFT':
        span, groups = hn, 2
        while span >= 2:
            half = span // 2
            for g in range(groups // 2):
                for off in range(half):
                    j = g * span + off
                    ar, ai = a[j], a[j + hn]
                    tr, ti = cmul(a[j + half], a[j + half + hn], *root(groups + g))
                    a[j], a[j + hn] = add(ar, tr), add(ai, ti)
                    a[j + half], a[j + half + hn] = sub(ar, tr), sub(ai, ti)
            span, groups = half, groups * 2
        out = a
    elif op == 'IFFT':
        stride, groups = 1, n
        while groups > 2:
            for g in range(groups // 4):
                for off in range(stride):
                    j = 2 * g * stride + off
                    ar, ai, br, bi = a[j], a[j + hn], a[j + stride], a[j + stride + hn]
                    a[j], a[j + hn] = add(ar, br), add(ai, bi)
                    a[j + stride], a[j + stride + hn] = cmul(sub(ar, br), sub(ai, bi), *root(groups // 2 + g, True))
            stride, groups = stride * 2, groups // 2
        out = [div2e(x, logn - 1, width) for x in a] if logn else a
    elif op == 'CMUL':
        out = [0] * n
        for j in range(hn):
            out[j], out[j + hn] = cmul(a[j], a[j + hn], b[j], b[j + hn])
    elif op == 'SPLIT':
        out = a[:] if n == 2 else [0] * n
        for j in range(qn):
            ar, ai, br, bi = a[2*j], a[2*j+hn], a[2*j+1], a[2*j+1+hn]
            out[j] = div2e(add(ar, br), 1, width)
            out[j + qn] = div2e(add(ai, bi), 1, width)
            tr, ti = cmul(sub(ar, br), sub(ai, bi), *root(j + hn, True))
            out[j + hn], out[j + hn + qn] = div2e(tr, 1, width), div2e(ti, 1, width)
    elif op == 'MERGE':
        out = [a[0], b[0]] if n == 2 else [0] * n
        for j in range(qn):
            tr, ti = cmul(b[j], b[j+qn], *root(j + hn))
            out[2*j], out[2*j+hn] = add(a[j], tr), add(a[j+qn], ti)
            out[2*j+1], out[2*j+1+hn] = sub(a[j], tr), sub(a[j+qn], ti)
    else:
        raise ValueError(op)
    return [x & ((1 << width) - 1) for x in out]


def ntt_kernel(op, a, b, logn, q, roots):
    a = a[:]
    n = 1 << logn
    if len(a) != n or any(not 0 <= x < q for x in a + b):
        raise ValueError('NTT length/domain')
    if op == 'TOMONT':
        return [mont(x, pow(65536, 2, q), q) for x in a]
    if op == 'MODMUL':
        if len(b) != n:
            raise ValueError('MODMUL B length')
        return [mont(x, y, q) for x, y in zip(a, b)]
    minimum = 2 if q == 3329 and n == 256 else 1
    if op == 'NTT':
        stride, groups = n // 2, 1
        while stride >= minimum:
            for g in range(groups):
                for off in range(stride):
                    i = 2 * g * stride + off
                    j = i + stride
                    t = mont(a[j], roots[q, False][groups + g], q)
                    a[i], a[j] = (a[i] + t) % q, (a[i] - t) % q
            stride, groups = stride // 2, groups * 2
    elif op == 'INTT':
        stride = minimum
        while stride <= n // 2:
            groups = n // (2 * stride)
            for g in range(groups):
                for off in range(stride):
                    i = 2 * g * stride + off
                    j = i + stride
                    a[i], a[j] = (a[i] + a[j]) % q, mont((a[i] - a[j]) % q, roots[q, True][groups + g], q)
            stride *= 2
        stages = logn - (minimum == 2)
        factor = (65536 * pow(1 << stages, -1, q)) % q
        a = [mont(x, factor, q) for x in a]
    else:
        raise ValueError(op)
    return a


def evaluate(command, a, b, roots):
    """a,b = list of jobs, each job = list of unsigned component words."""
    error = validate(command)
    if error:
        raise ValueError(f'command status {error:#x}')
    name = next(k for k, v in OPS.items() if v == command['op'])
    if len(a) != command['jobs']:
        raise ValueError('job count')
    fft, ntt = roots
    result = []
    for j, aj in enumerate(a):
        bj = b[j] if b else []
        if command['fmt'] == 3:
            result.append(ntt_kernel(name, aj, bj, command['logn'], (12289, 3329)[command['profile']], ntt))
        else:
            n = 1 << command['logn']
            want_a = n // 2 if name == 'MERGE' else n
            want_b = n if name == 'CMUL' else n // 2 if name == 'MERGE' else 0
            if len(aj) != want_a or len(bj) != want_b:
                raise ValueError('FFT input footprint')
            result.append(fft_kernel(name, aj, bj, command['logn'], WIDTHS[command['fmt']], fft))
    return result
