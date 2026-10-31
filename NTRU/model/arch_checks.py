"""Numeric checks behind every number in ARCHITECTURE.md (v0.3).

Each section prints PASS lines or tables; any failed assertion stops the run.
R8 = fixed-point FN-DSA C implementation, commit ad1e5bf7714d53230ad457364db8a46a1b459c94,
FALCON_FPR_MODE = 2 (FXP), FALCON_AVX2 = 0. Functions below re-implement the R8 code
literally (fpr_mul, fpr_div2e, FPC_MUL) to compare against the hardware decomposition.

Run: python model/arch_checks.py   (writes study/results/arch_checks.md)
"""
from math import ceil
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent
RNG = Random(20261025)
OUT = []


def say(line=""):
    print(line)
    OUT.append(line)


def sgn(v, w):
    v %= 1 << w
    return v - (1 << w) if v >> (w - 1) else v


# ---------------------------------------------------------------- R8 literal (W = 128)

def r8_fpr_mul(x, y):
    """R8 fpr_mul: split 64/64, round only xl*yl, exact cross terms, wrap 2^128."""
    xl, yl = x % (1 << 64), y % (1 << 64)
    xh, yh = sgn(x, 128) >> 64, sgn(y, 128) >> 64
    z0 = (xl * yl + (1 << 63)) >> 64
    z1, z2, z3 = xl * yh, yl * xh, (xh * yh) << 64
    return sgn(z0 + z1 + z2 + z3, 128)


def r8_div2e(x, n):
    """R8 fpr_div2e: add ((1<<n)>>1), arithmetic shift right n."""
    return sgn(sgn(x + ((1 << n) >> 1), 128) >> n, 128)


def r8_fpc_mul(ar, ai, br, bi):
    """R8 FPC_MUL (3M): d_re = p0 - p1; d_im = mul(ar+ai, br+bi) - (p0 + p1)."""
    p0, p1 = r8_fpr_mul(ar, br), r8_fpr_mul(ai, bi)
    k = r8_fpr_mul(sgn(ar + ai, 128), sgn(br + bi, 128))
    return sgn(p0 - p1, 128), sgn(k - sgn(p0 + p1, 128), 128)


# ------------------------------------------------- contract (any W, F = W/2), hardware view

def rnd(x, y, w):
    """Contract product: floor((x*y + 2^(F-1)) / 2^F) mod 2^W, F = W/2 (R8 rule for W=128)."""
    f = w // 2
    return sgn((sgn(x, w) * sgn(y, w) + (1 << (f - 1))) >> f, w)


def limbs(v, w, g):
    k = w // g
    enc = v % (1 << w)
    out = [(enc >> (g * i)) & ((1 << g) - 1) for i in range(k)]
    if out[-1] >> (g - 1):
        out[-1] -= 1 << g
    return out


def kept_terms(w, g):
    """Limb pairs that can affect result bits [F, F+W): drop weight >= 3W/2."""
    k = w // g
    return [(i, j) for i in range(k) for j in range(k) if g * (i + j) < w + w // 2]


def tree_product(x, y, w, g):
    """Hardware: kept limb products, fixed-shift sum mod 2^(3W/2), round, wrap to W."""
    f, top = w // 2, w + w // 2
    lx, ly = limbs(x, w, g), limbs(y, w, g)
    acc = sum((lx[i] * ly[j]) << (g * (i + j)) for i, j in kept_terms(w, g))
    acc %= 1 << top
    return sgn((acc + (1 << (f - 1))) >> f, w)


def hw_cmul(ar, ai, br, bi, w, g, tw_sum=None):
    """3M with twiddle sum from ROM (tw_sum = br+bi wrapped), data pre-add wrapped."""
    p0, p1 = tree_product(ar, br, w, g), tree_product(ai, bi, w, g)
    ts = sgn(br + bi, w) if tw_sum is None else tw_sum
    k = tree_product(sgn(ar + ai, w), ts, w, g)
    return sgn(p0 - p1, w), sgn(k - p0 - p1, w)


def cmul_4m(ar, ai, br, bi, w):
    return (sgn(rnd(ar, br, w) - rnd(ai, bi, w), w),
            sgn(rnd(ar, bi, w) + rnd(ai, br, w), w))


def corners(w):
    lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
    one = 1 << (w // 2)
    return [lo, lo + 1, -one, -1, 0, 1, one, hi - 1, hi]


def section_fft():
    say("## A. Contract FFT (R8) và phép phân rã phần cứng\n")
    n = 0
    for _ in range(100000):
        x, y = sgn(RNG.getrandbits(128), 128), sgn(RNG.getrandbits(128), 128)
        assert r8_fpr_mul(x, y) == rnd(x, y, 128)
        n += 1
    for x in corners(128):
        for y in corners(128):
            assert r8_fpr_mul(x, y) == rnd(x, y, 128)
            n += 1
    say(f"- PASS fpr_mul(R8) = floor((x·y + 2^63)/2^64) mod 2^128: {n} cặp.")

    for nn in range(0, 11):
        for x in corners(128) + [sgn(RNG.getrandbits(128), 128) for _ in range(2000)]:
            ref = x if nn == 0 else sgn(x + (1 << (nn - 1)), 128) >> nn
            assert r8_div2e(x, nn) == ref
    say("- PASS fpr_div2e(x, n) = floor(wrap128(x + 2^(n−1)) / 2^n), n = 0 là đồng nhất "
        "(n = 0..10). Phép cộng wrap trước khi dịch: khác floor((x + 2^(n−1))/2^n) chỉ khi "
        "x ≥ 2^127 − 2^(n−1).")

    n = 0
    for _ in range(30000):
        a = [sgn(RNG.getrandbits(128), 128) for _ in range(4)]
        assert r8_fpc_mul(*a) == hw_cmul(*a, 128, 32) == hw_cmul(*a, 128, 16)
        n += 1
    for ar in corners(128):
        for bi in corners(128):
            a = (ar, corners(128)[3], corners(128)[6], bi)
            assert r8_fpc_mul(*a) == hw_cmul(*a, 128, 32) == hw_cmul(*a, 128, 16)
            n += 1
    say(f"- PASS FPC_MUL(R8, 3M) = cây phần cứng (leaf 32 và 16, bỏ hạng thừa, "
        f"tổng twiddle từ ROM): {n} phép nhân phức.")

    diff, total = 0, 50000
    for _ in range(total):
        ar, ai = (RNG.randrange(-(1 << 70), 1 << 70) for _ in range(2))
        br, bi = (RNG.randrange(-(1 << 64), 1 << 64) for _ in range(2))
        m3, m4 = r8_fpc_mul(ar, ai, br, bi), cmul_4m(ar, ai, br, bi, 128)
        assert m3[0] == m4[0]
        diff += m3[1] != m4[1]
    say(f"- 3M (R8) so với 4M cùng quy tắc làm tròn: phần thực luôn bằng, phần ảo khác ở "
        f"{diff}/{total} ({100 * diff / total:.1f}%) trường hợp (|a| < 2^6, |b| ≤ 1 dạng Q64.64).")

    for w in (32, 64):
        for g in (16, 32):
            if g > w:
                continue
            for _ in range(20000):
                a = [sgn(RNG.getrandbits(w), w) for _ in range(4)]
                ref = (sgn(rnd(a[0], a[2], w) - rnd(a[1], a[3], w), w),
                       sgn(rnd(sgn(a[0] + a[1], w), sgn(a[2] + a[3], w), w)
                           - rnd(a[0], a[2], w) - rnd(a[1], a[3], w), w))
                assert hw_cmul(*a, w, g) == ref
    say("- PASS contract cùng quy tắc cho W = 32/64 (Q16.16, Q32.32): cây phần cứng khớp "
        "định nghĩa (leaf 16 và 32). Lưu ý: W = 32/64 không có reference R8.\n")


# ------------------------------------------------ NG64: NTRUGen Q32.32 (keygen FFT)

def ng_mul_int128(x, y):
    """ntrugen fxr_mul, __int128 path: z = (int64)x * (int64)y; v = (uint64)(z >> 32)."""
    return sgn((sgn(x, 64) * sgn(y, 64)) >> 32, 64)


def ng_mul_limbs(x, y):
    """ntrugen fxr_mul fallback: 32-bit limbs, z0 = (xl*yl) >> 32, cross terms exact, wrap 2^64."""
    xl, yl = x % (1 << 32), y % (1 << 32)
    xh, yh = sgn(x, 64) >> 32, sgn(y, 64) >> 32
    z0 = (xl * yl) >> 32
    return sgn(z0 + xl * yh + yl * xh + ((xh * yh) << 32), 64)


def ng_half(v):
    """ntrugen fxr_div2e(v, 1): v += 1; arithmetic shift right 1 (wrap first)."""
    return sgn(v + 1, 64) >> 1


def ng_cmul(sr, si, yr, yi, mul=ng_mul_int128):
    """ntrugen fxc_mul(s, y), 3M with truncating multiply."""
    z0, z1 = mul(sr, yr), mul(si, yi)
    z2 = mul(sgn(sr + si, 64), sgn(yr + yi, 64))
    return sgn(z0 - z1, 64), sgn(z2 - sgn(z0 + z1, 64), 64)


def contract_floor(x, y):
    """Doc contract NG64: wrap64(floor(x*y / 2^32))."""
    return sgn((sgn(x, 64) * sgn(y, 64)) // (1 << 32), 64)


def tree_product_bias(x, y, w, g, bias):
    """tree_product with selectable rounding bias (1 = half-up as R8, 0 = floor as NG64)."""
    f, top = w // 2, w + w // 2
    lx, ly = limbs(x, w, g), limbs(y, w, g)
    acc = sum((lx[i] * ly[j]) << (g * (i + j)) for i, j in kept_terms(w, g)) % (1 << top)
    return sgn((acc + (bias << (f - 1))) >> f, w)


def ng_vect_fft(f, logn, gm, cmul):
    """Transliteration of ntrugen vect_FFT (generic path)."""
    f = list(f)
    hn = 1 << (logn - 1)
    t = hn
    for lm in range(1, logn):
        m, ht, j0, hm = 1 << lm, t >> 1, 0, (1 << lm) >> 1
        for i in range(hm):
            sr, si = gm[m + i]
            for j in range(j0, j0 + ht):
                xr, xi, yr, yi = f[j], f[j + hn], f[j + ht], f[j + ht + hn]
                yr, yi = cmul(sr, si, yr, yi)
                f[j], f[j + hn] = sgn(xr + yr, 64), sgn(xi + yi, 64)
                f[j + ht], f[j + ht + hn] = sgn(xr - yr, 64), sgn(xi - yi, 64)
            j0 += t
        t = ht
    return f


def ng_vect_ifft(f, logn, gm, cmul):
    """Transliteration of ntrugen vect_iFFT (generic path): per-stage halving, no final scale."""
    f = list(f)
    hn, ht = 1 << (logn - 1), 1
    for lm in range(logn - 1, 0, -1):
        m, t, j0, hm = 1 << lm, ht << 1, 0, (1 << lm) >> 1
        for i in range(hm):
            sr, si = gm[m + i][0], sgn(-gm[m + i][1], 64)
            for j in range(j0, j0 + ht):
                xr, xi, yr, yi = f[j], f[j + hn], f[j + ht], f[j + ht + hn]
                f[j], f[j + hn] = ng_half(sgn(xr + yr, 64)), ng_half(sgn(xi + yi, 64))
                dr, di = ng_half(sgn(xr - yr, 64)), ng_half(sgn(xi - yi, 64))
                f[j + ht], f[j + ht + hn] = cmul(sr, si, dr, di)
            j0 += t
        ht = t
    return f


def doc_fft_r8_schedule(f, logn, gm, cmul):
    """Doc NG64 FFT = R8 Zf(FFT) loop structure with NG primitives."""
    f = list(f)
    n = 1 << logn
    hn, t, m = n >> 1, n >> 1, 2
    for _ in range(1, logn):
        ht, hm = t >> 1, m >> 1
        j1 = 0
        for i1 in range(hm):
            sr, si = gm[m + i1]
            for j in range(j1, j1 + ht):
                xr, xi, yr, yi = f[j], f[j + hn], f[j + ht], f[j + ht + hn]
                yr, yi = cmul(sr, si, yr, yi)
                f[j], f[j + hn] = sgn(xr + yr, 64), sgn(xi + yi, 64)
                f[j + ht], f[j + ht + hn] = sgn(xr - yr, 64), sgn(xi - yi, 64)
            j1 += t
        t, m = ht, m << 1
    return f


def doc_ifft_r8_schedule(f, logn, gm, cmul):
    """Doc NG64 IFFT = R8 Zf(iFFT) loop structure, halving both outputs, no final scaling."""
    f = list(f)
    n = 1 << logn
    hn, t, m = n >> 1, 1, n
    for _ in range(logn, 1, -1):
        hm, dt = m >> 1, t << 1
        i1, j1 = 0, 0
        while j1 < hn:
            sr, si = gm[hm + i1][0], sgn(-gm[hm + i1][1], 64)
            for j in range(j1, j1 + t):
                xr, xi, yr, yi = f[j], f[j + hn], f[j + t], f[j + t + hn]
                f[j], f[j + hn] = ng_half(sgn(xr + yr, 64)), ng_half(sgn(xi + yi, 64))
                dr, di = ng_half(sgn(xr - yr, 64)), ng_half(sgn(xi - yi, 64))
                f[j + t], f[j + t + hn] = cmul(dr, di, sr, si)   # R8 operand order (data, twiddle)
            i1, j1 = i1 + 1, j1 + dt
        t, m = dt, hm
    return f


def section_ng64():
    say("## A2. Contract NG64 (NTRUGen Q32.32, keygen FFT)\n")
    lo, hi = -(1 << 63), (1 << 63) - 1
    corner = [lo, lo + 1, -(1 << 32), -1, 0, 1, 1 << 32, hi - 1, hi]
    pairs = [(a, b) for a in corner for b in corner]
    pairs += [(sgn(RNG.getrandbits(64), 64), sgn(RNG.getrandbits(64), 64)) for _ in range(100000)]
    for x, y in pairs:
        r = contract_floor(x, y)
        assert ng_mul_int128(x, y) == r == ng_mul_limbs(x, y)
        assert tree_product_bias(x, y, 64, 32, 0) == r == tree_product_bias(x, y, 64, 16, 0)
    say(f"- PASS fxr_mul (đường int128 và đường limb 32 bit) = wrap64(floor(x·y/2^32)) = cây phần cứng "
        f"bias 0 (leaf 32 và 16, bỏ hạng ≥ 96 bit): {len(pairs)} cặp.")
    for v in corner + [sgn(RNG.getrandbits(64), 64) for _ in range(20000)]:
        assert ng_half(v) == sgn(v + 1, 64) >> 1
    say("- PASS fxr_div2e(v, 1) = floor(wrap64(v + 1)/2).")
    for _ in range(20000):
        s = [sgn(RNG.getrandbits(64), 64) for _ in range(4)]
        assert ng_cmul(*s) == ng_cmul(*s, mul=ng_mul_limbs) == ng_cmul(s[2], s[3], s[0], s[1])
    say("- PASS fxc_mul 3M khớp giữa hai đường nhân và giao hoán theo thứ tự toán hạng (s, y) ↔ (y, s).")
    hw_cmul_ng = lambda a, b, c, d: (                       # hardware: floor tree, leaf 16
        sgn(tree_product_bias(a, c, 64, 16, 0) - tree_product_bias(b, d, 64, 16, 0), 64),
        sgn(tree_product_bias(sgn(a + b, 64), sgn(c + d, 64), 64, 16, 0)
            - sgn(tree_product_bias(a, c, 64, 16, 0) + tree_product_bias(b, d, 64, 16, 0), 64), 64))
    count = 0
    for logn in range(2, 11):
        n = 1 << logn
        gm = [(sgn(RNG.getrandbits(64), 64) >> 31, sgn(RNG.getrandbits(64), 64) >> 31)
              for _ in range(1024)]                      # |root| ≲ 1 in Q32.32
        f = [sgn(RNG.getrandbits(64), 64) >> 20 for _ in range(n)]
        a = ng_vect_fft(f, logn, gm, ng_cmul)
        assert a == doc_fft_r8_schedule(f, logn, gm, ng_cmul)
        if logn <= 6:
            assert a == ng_vect_fft(f, logn, gm, hw_cmul_ng)
        b = ng_vect_ifft(f, logn, gm, ng_cmul)
        assert b == doc_ifft_r8_schedule(f, logn, gm, ng_cmul)
        count += 2
    say(f"- PASS vect_FFT/vect_iFFT (NTRUGen, viết lại) = lịch chỉ số R8 với primitive NG64 "
        f"(GM[m+i], iFFT chia đôi hai nhánh mỗi tầng, không chia cuối): {count} transform, logn 2..10; "
        "FFT logn ≤ 6 còn khớp với cmul dựng từ cây phần cứng bias 0.\n")


def section_tree():
    say("## B. Hạng giữ lại, cây dịch cố định, độ rộng\n")
    say("| Leaf | W | Tích limb đủ | Giữ lại | Dịch theo cấp | Bit cộng một cây (nút ≤ 3W/2 bit) |")
    say("|---:|---:|---:|---:|---|---:|")
    rows = {}
    for g in (32, 16):
        for w in (32, 64, 128):
            if g > w:
                continue
            k = w // g
            kept = kept_terms(w, g)
            nb = k.bit_length() - 1
            shifts = [g << (lv // 2) for lv in range(2 * nb)]
            # interval bounds per node (limb ranges), capped at 3W/2 bits (wrap is allowed)
            top = w + w // 2
            rng_l = lambda idx: ((-(1 << (g - 1)), (1 << (g - 1)) - 1) if idx == k - 1
                                 else (0, (1 << g) - 1))
            order = []
            for t in range(k * k):
                i = sum(((t >> (2 * m)) & 1) << m for m in range(nb))
                j = sum(((t >> (2 * m + 1)) & 1) << m for m in range(nb))
                order.append((i, j))
            cur = []
            for i, j in order:
                if (i, j) in kept:
                    c = [x * y for x in rng_l(i) for y in rng_l(j)]
                    cur.append((min(c), max(c)))
                else:
                    cur.append((0, 0))
            adder = 0
            for s in shifts:
                nxt = []
                for q in range(0, len(cur), 2):
                    (l0, h0), (l1, h1) = cur[q], cur[q + 1]
                    lo, hi = l0 + (l1 << s), h0 + (h1 << s)
                    bits = 1
                    while not (-(1 << (bits - 1)) <= lo and hi < (1 << (bits - 1))):
                        bits += 1
                    if (l1, h1) != (0, 0) and s < top:
                        adder += min(bits, top) - s
                    nxt.append((lo, hi))
                cur = nxt
            rows[(g, w)] = (k * k, len(kept), adder)
            say(f"| {g} | {w} | {k * k} | {len(kept)} | {shifts} | {adder} |")
    say("")
    return rows


def section_throughput(rows):
    say("## C. Trần throughput FFT (3M) và dữ liệu\n")
    say("Tích thực theo cây (một cây = k² vị trí leaf, kể cả vị trí bỏ trống); 3 tích/nhân phức.\n")
    say("| Mode | R32 (32 leaf): tích/chu kỳ → BF | F16 (128 leaf): tích/chu kỳ → BF | "
        "Trần dữ liệu 512 / 1024 / 2048 |")
    say("|---|---|---|---|")
    res = {}
    for w in (32, 64, 128):
        out = []
        for g, leaves in ((32, 32), (16, 128)):
            pos = (w // g) ** 2
            prods = leaves // pos
            out.append((prods, prods / 3))
        data = [b // (4 * w) for b in (512, 1024, 2048)]
        res[w] = (out, data)
        say(f"| FFT{w} | {out[0][0]} → {out[0][1]:.3g} | {out[1][0]} → {out[1][1]:.3g} | "
            f"{data[0]} / {data[1]} / {data[2]} |")
    say("")
    say("Bus sản phẩm tại trần dữ liệu 512 bit, làm tròn ngay tại gốc cây (khe 32 bit):\n")
    say("| Mode | Tích/chu kỳ | Bit/tích | Khe 32 bit |")
    say("|---|---:|---:|---:|")
    bus = [("FFT32", 4 * 3, 32), ("FFT64", 2 * 3, 64), ("FFT128 (trung bình 2 tích/chu kỳ)", 2, 128),
           ("NTT 3329/12289: T", 16, 28), ("NTT 8380417: T", 8, 46),
           ("NTT prime RNS: T (m, m·q đi đường nội bộ)", 8, 64)]
    for name, n, b in bus:
        slots = n * ceil(b / 32)
        assert slots <= 16
        say(f"| {name} | {n} | {b} | {slots} |")
    say("- Nếu cả T (64 bit), m (32 bit) và m·q (64 bit) của Montgomery tổng quát đều qua bus "
        f"khe 32 bit: 5 khe/modmul → trần {16 / 5:.2f} modmul/chu kỳ; với bus cũ 16 khe × 65 bit "
        f"(1 khe/tích): {16 / 3:.2f}. Cả hai thấp hơn trần dữ liệu 8 của lane 32 bit.\n")


def section_ntt():
    say("## D. NTT: Montgomery, hằng số, root\n")
    for q in (3329, 12289, 8380417, 2013265921, 4293918721):
        R = 1 << 32
        qp = (-pow(q, -1, R)) % R
        for _ in range(20000):
            a, b = RNG.randrange(q), RNG.randrange(q)
            t = a * b
            m = ((t % R) * qp) % R
            s = t + m * q
            assert s % R == 0 and s < (1 << 65) and (s >> 32) < 2 * q
            u = s >> 32
            assert (u - q if u >= q else u) == (a * b * pow(R, -1, q)) % q
    say("- PASS Montgomery tổng quát R = 2^32: S < 2^65, u < 2q, kết quả = a·b·R^(−1) mod q "
        "(q = 3329, 12289, 8380417, 2013265921, 4293918721).")

    def csd(n):
        d, i = [], 0
        while n:
            if n & 1:
                t = 2 - (n & 3)
                d.append((t, i))
                n -= t
            n >>= 1
            i += 1
        return " ".join(("+" if t > 0 else "−") + f"2^{i}" for t, i in reversed(d))

    say("\n| q | R | Hằng số | CSD hằng số | CSD q | T tối đa (bit) |")
    say("|---:|---|---:|---|---|---:|")
    for q, r, c in ((3329, 16, "neg"), (12289, 16, "neg"), (8380417, 32, "pos")):
        R = 1 << r
        const = (-pow(q, -1, R)) % R if c == "neg" else pow(q, -1, R)
        say(f"| {q} | 2^{r} | {const} ({'−q⁻¹' if c == 'neg' else 'q⁻¹'}) | {csd(const)} | "
            f"{csd(q)} | {((q - 1) ** 2).bit_length()} |")
    assert (-pow(3329, -1, 1 << 16)) % (1 << 16) == 3327
    assert (-pow(12289, -1, 1 << 16)) % (1 << 16) == 12287
    assert pow(8380417, -1, 1 << 32) == 58728449

    for q in (3329, 12289):
        R, c = 1 << 16, (-pow(q, -1, 1 << 16)) % (1 << 16)
        smax = (q - 1) ** 2 + (R - 1) * q
        assert smax < 2 * q * R
        vals = [0, 1, q - 1] + [RNG.randrange(q) for _ in range(3000)]
        for a in vals:
            for b in vals[:40]:
                t = a * b
                m = ((t % R) * c) % R
                u = (t + m * q) >> 16
                assert (t + m * q) % R == 0 and u < 2 * q
                assert (u - q if u >= q else u) == a * b * pow(R, -1, q) % q
        say(f"- PASS reducer (T + m·q)/2^16, q = {q}: S ≤ {smax} < 2^{smax.bit_length()}, u < 2q.")
    q, R = 8380417, 1 << 32
    qi = pow(q, -1, R)
    for _ in range(20000):
        a, b = RNG.randrange(q), RNG.randrange(q)
        t = a * b
        m = sgn((t % R) * qi, 32)
        v = (t - m * q) >> 32
        assert (t - m * q) % R == 0 and -q < v < q
        assert (v + q if v < 0 else v) == a * b * pow(R, -1, q) % q
    say("- PASS reducer (T − m·q)/2^32 với m có dấu, q = 8380417: kết quả trong (−q, q), +q nếu âm.")

    def order(z, q):
        k, x = 1, z % q
        while x != 1:
            x = x * z % q
            k += 1
        return k

    assert order(17, 3329) == 256 and order(1753, 8380417) == 512
    psi = next(pow(g, (12289 - 1) // 2048, 12289) for g in range(2, 100)
               if order(pow(g, (12289 - 1) // 2048, 12289), 12289) == 2048)
    say(f"- Bậc root: 17 mod 3329 = 256 (ML-KEM, N = 256 → NTT không đầy đủ); "
        f"1753 mod 8380417 = 512 (ML-DSA, 2N); 12289 có root bậc 2048 (ví dụ {psi}).")
    for z, q, n, signed in ((17, 3329, 256, False), (1753, 8380417, 256, True), (psi, 12289, 1024, True)):
        for k in range(1, n):
            inv = pow(z, -k, q)
            if signed:
                assert inv == (-pow(z, n - k, q)) % q
            else:
                assert inv == pow(z, n - k, q)
    assert pow(17, -1, 3329) == 1175 and (-pow(17, 255, 3329)) % 3329 == 2154
    say("- PASS root nghịch: bậc 2N → ψ^(−k) = −ψ^(N−k); bậc N (ML-KEM) → ζ^(−k) = ζ^(N−k) "
        "(không đổi dấu; 17^(−1) = 1175 ≠ −17^255 = 2154).")
    for q, r in ((3329, 16), (12289, 16), (8380417, 32)):
        R = 1 << r
        for _ in range(2000):
            w, s = RNG.randrange(q), RNG.randrange(q)
            assert (w * R % q) * (s * R % q) * pow(R, -1, q) % q == w * s * R % q
    say("- PASS Mont(w·R, s·R) = (w·s)·R mod q (sinh twiddle trong miền Montgomery).")
    for q in (3329, 12289, 8380417):
        for x in range(0, q, max(1, q // 5000)):
            h = (x + (x & 1) * q) >> 1
            assert h < q and (2 * h) % q == x
    say("- PASS half_q(x) = (x + (x&1)·q) >> 1 = x/2 mod q, kết quả < q.")
    low = [(i, j) for i in range(2) for j in range(2) if 16 * (i + j) < 32]
    assert len(low) == 3
    say("- F16 Montgomery tổng quát: T 4 leaf + m (nửa thấp) 3 leaf + m·q 4 leaf = 11 leaf.\n")

    # ML-KEM has seven stages over 256 scalar coefficients (quadratic factors).
    # A canonical integer transform oracle checks the normalisation independently
    # of Montgomery encoding; it is not a C/RTL differential test.
    q, n = 3329, 256
    roots = [pow(17, int(f"{k:07b}"[::-1], 2), q) for k in range(128)]
    local_rng = Random(20261025)
    inputs = [[1] + [0] * 255, [0] * 256]
    inputs += [[local_rng.randrange(q) for _ in range(n)] for _ in range(20)]
    for data in inputs:
        a, idx, length = data[:], 1, 128
        while length >= 2:
            for start in range(0, n, 2 * length):
                root = roots[idx]
                idx += 1
                for j in range(start, start + length):
                    t = root * a[j + length] % q
                    a[j + length], a[j] = (a[j] - t) % q, (a[j] + t) % q
            length //= 2
        idx, length = 127, 2
        while length <= 128:
            for start in range(0, n, 2 * length):
                root = roots[idx]
                idx -= 1
                for j in range(start, start + length):
                    t = a[j]
                    a[j], a[j + length] = (t + a[j + length]) % q, root * (a[j + length] - t) % q
            length *= 2
        assert a == [128 * x % q for x in data]
        assert [x * pow(128, -1, q) % q for x in a] == data
    assert (1 << 32) * pow(128, -1, q) % q == 1441
    assert 128 * pow(256, -1, q) % q == 1665  # wrong normalisation gives x/2
    say("- PASS ML-KEM N=256, 7 tầng: inverse chưa chuẩn hóa cho 128*x; factor là 128^(-1), "
        "không phải 256^(-1). Reference gộp Montgomery: R²/128 mod 3329 = 1441 "
        "(22 vector số nguyên; chưa phải differential C/RTL).\n")


def section_mont_on_array():
    say("## D2. Montgomery chạy trên mảng nhân dùng chung (biến thể cộng, q' = −q⁻¹ mod R)\n")
    say("Mỗi tích là tổng các tích leaf 16×16 có chọn dấu; bước cuối là bộ cộng chung "
        "u = T_cao + (m·q)_cao + [T_thấp ≠ 0], rồi trừ q nếu u ≥ q.\n")

    def leaf_sum(x, y, wx, wy, pairs=None, g=16):
        """Unsigned x (wx bits) × y (wy bits) as a sum of g×g leaf products; optional subset."""
        kx, ky = ceil(wx / g), ceil(wy / g)
        lx = [(x >> (g * i)) & ((1 << g) - 1) for i in range(kx)]
        ly = [(y >> (g * j)) & ((1 << g) - 1) for j in range(ky)]
        sel = pairs if pairs is not None else [(i, j) for i in range(kx) for j in range(ky)]
        return sum((lx[i] * ly[j]) << (g * (i + j)) for i, j in sel), len(sel)

    rows = []
    for q, rbits in ((3329, 16), (12289, 16), (8380417, 32), (2013265921, 32), (4293918721, 32)):
        R = 1 << rbits
        qp = (-pow(q, -1, R)) % R
        wq = q.bit_length()
        k = rbits // 16
        low_pairs = [(i, j) for i in range(k) for j in range(k) if 16 * (i + j) < rbits]
        leaves = None
        vals = [0, 1, q - 1, q // 2] + [RNG.randrange(q) for _ in range(20000)]
        for a in vals:
            b = RNG.randrange(q)
            t, n1 = leaf_sum(a, b, rbits, rbits)
            assert t == a * b
            t_lo, t_hi = t & (R - 1), t >> rbits
            mfull, n2 = leaf_sum(t_lo, qp, rbits, rbits, low_pairs)
            m = mfull & (R - 1)
            assert m == (t_lo * qp) % R
            mq, n3 = leaf_sum(m, q, rbits, wq)
            u = t_hi + (mq >> rbits) + (t_lo != 0)
            assert u == (t + m * q) >> rbits and u < 2 * q
            out = u - q if u >= q else u
            assert out == a * b * pow(R, -1, q) % q
            leaves = n1 + n2 + n3
        rows.append((q, rbits, leaves))
    say("| q | R | Leaf/phép nhân modulo (T + m + m·q) | Phép nhân modulo/chu kỳ (64 leaf) |")
    say("|---:|---|---:|---:|")
    for q, rbits, leaves in rows:
        say(f"| {q} | 2^{rbits} | {leaves} | {64 / leaves:.3g} |")
    say("\n- PASS: T, m (chỉ nửa thấp) và m·q dựng từ tích leaf; bộ cộng chung cho kết quả đúng "
        "a·b·R⁻¹ mod q, u < 2q (20 004 mẫu mỗi q, gồm 0, 1, q−1).\n")


def section_latency():
    say("## E. Mô hình latency có rào chắn giữa stage (giả định)\n")
    for name, p in (("R32, 1024 bit", 32), ("F16, 2048 bit", 64)):
        n, lat = 256, 8
        eff = (n / 2) / ((n / 2) / p + lat)
        say(f"- {name}: P = {p}, N = 256, L = 8 → {eff:.2f} BF/chu kỳ.")
    say("")


def section_single_lane():
    """Single-lane tile (spec 2.0, 10 since 31/10/2026): leaf use per cycle and core rates of the v1 design."""
    say("## F. Tile một làn NTT 32 bit (thiết kế v1 từ 31/10/2026)\n")
    # One 32-bit lane for every q (R = 2^32). On the array: passes at 0, 5, 10 on all 4 leaves, period 3.
    # (The former 16-bit lane, passes on leaves 0, 1, 2, was removed on 31/10/2026.)
    assert len({0 % 3, 5 % 3, 10 % 3}) == 3
    rows = [("Bộ Montgomery riêng (v1)", 4, 1.0),
            ("Trên mảng (biến thể 1)", 11, 1 / 3)]
    say("| Rút gọn (mọi q) | Lượt bộ nhân mỗi phép | Phép nhân modulo mỗi tile mỗi chu kỳ | Cả lõi (16 tile) |")
    say("|---|---:|---:|---:|")
    for name, leaves, r in rows:
        say(f"| {name} | {leaves} | {r:.3g} | {16 * r:.3g} |")
    say("\n- PASS: trên mảng, ba lượt ở độ lệch 0, 5, 10 rơi vào ba pha khác nhau của chu kỳ 3.\n")


def main():
    section_fft()
    section_ng64()
    rows = section_tree()
    section_throughput(rows)
    section_ntt()
    section_mont_on_array()
    section_latency()
    section_single_lane()
    out = ROOT / "study" / "results" / "arch_checks.md"
    out.write_text("# Kiểm tra số cho ARCHITECTURE.md\n\n" + "\n".join(OUT) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
