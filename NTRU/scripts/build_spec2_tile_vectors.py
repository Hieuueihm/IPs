"""Golden vectors for the tile contract of spec 2.0 (spec/FlexTransform/2.0/10_hop_dong_tile.md).

Expected values come only from plain integer and modular arithmetic:
  NTT:        Mont(a, b) = a*b*R^-1 mod q with R = 2^32 for every q (packed NTT: R = 2^16);  half(s) = s*2^-1 mod q
  FFT:        spec 1.0 01.1 (wrap, round-half-up products, 3-product complex multiply, div2e)
This script must not import the leaf-level hardware models in model/: those are what the vectors test.

Output (spec/FlexTransform/2.0/assets/tile/), one case per line, fields in hex separated by spaces, '#' comments:
  ntt.txt         q qinv dir halve x y w z0 z1          (NTT mode, one 32-bit lane: small and large q alike)
  fft32bf.txt     FFT mode at 32 bit (two beats per line)
  fftwbf.txt      FFT mode at 64 / 128 bit (2L beats per line)
  ntt16.txt       q qinv dir halve pair x y wa wb zx zy  (packed NTT mode: two 16-bit coefficients per word, R = 2^16)
  manifest.json   seed, counts, SHA-256
Since 02/11/2026 the tile has three modes (NTT, FFT, packed NTT); the raw 32x32 product, the FFT 32-bit product and
the single modmul vectors (raw32.txt, fft32.txt, mode-2 rows of ntt.txt) were dropped with those modes.

Run: python scripts/build_spec2_tile_vectors.py
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "spec" / "FlexTransform" / "2.0" / "assets" / "tile"
SEED = 20261030
RANDOM_PER_GROUP = 120
# Packed NTT mode (two 16-bit coefficients per 32-bit word, q < 2^15): ML-KEM 3329, 7681, 10753, FN-DSA 12289, 18433
Q_NTT16 = (3329, 7681, 10753, 12289, 18433)

# One 32-bit lane for every NTT (R = 2^32), small q included, in increasing order so that the
# testbench's +MIX partner of the last small q is the first large one:
# small odd q (3, ML-KEM 3329, 7681, FN-DSA 12289, 65521); 8380417 (ML-DSA); first, a middle and the
# last prime of NTRUGen's PRIMES[]; 2^31 - 1
Q_NTT = (3, 3329, 7681, 12289, 65521, 8380417, 2140348417, 2144120833, 2147473409, 2147483647)

HEADERS = {
    "ntt": "q qinv dir halve x y w z0 z1",
}


def is_prime(n):
    if n < 2:
        return False
    f = 2
    while f * f <= n:
        if n % f == 0:
            return False
        f += 1
    return True


# --- NTT ----------------------------------------------------------------------------------------

def ntt_ops(q, rbits):
    r = 1 << rbits
    rinv, inv2 = pow(r, -1, q), pow(2, -1, q)

    def mont(a, b):
        return a * b * rinv % q

    def ct(x, y, w):
        t = mont(y, w)
        return (x + t) % q, (x - t) % q

    def gs(x, y, w, halve):
        s, d = (x + y) % q, (x - y) % q
        return (s * inv2 % q if halve else s), mont(d, w)

    return mont, ct, gs


def ntt_expected(q, rbits, direction, halve, d0, d1, r0):
    """One request of the NTT mode: one butterfly."""
    mont, ct, gs = ntt_ops(q, rbits)
    if direction == 0:
        return list(ct(d0, d1, r0))
    return list(gs(d0, d1, r0, halve))


def special_values(q, rbits):
    """0, 1, q - 1, q/2 neighbours, and powers of two (for q > 2^16 their products reach multiples of R)."""
    vals = {0, 1, 2, q - 1, q - 2, q // 2, q // 2 + 1}
    for k in range(rbits + 1):
        if (1 << k) < q:
            vals.add(1 << k)
    return sorted(v for v in vals if 0 <= v < q)


def ntt_cases(q, rbits, rng):
    r = 1 << rbits
    qinv = (-pow(q, -1, r)) % r
    sv = special_values(q, rbits)
    out = []
    for direction, halve in ((0, 0), (1, 0), (1, 1)):
        used = (0, 1, 2)                              # slots x, y, w
        cases = []
        # every special value in every used slot, the other slots random; a data slot is paired with a
        # second special value in the root slot
        for i, v in enumerate(sv):
            for s in used:
                x = [rng.randrange(q) for _ in range(3)]
                x[s] = v
                if s != 2:
                    x[2] = sv[(i + s + 1) % len(sv)]
                cases.append(x)
        # products that are exact multiples of R: T_low = 0 with T != 0 (none when q^2 < R)
        for k in range(1, rbits):
            a, b = 1 << k, 1 << (rbits - k)
            if a < q and b < q:
                cases.append([a, a, b])
        cases += [[rng.randrange(q) for _ in range(3)] for _ in range(RANDOM_PER_GROUP)]
        for d0, d1, r0 in cases:
            z = ntt_expected(q, rbits, direction, halve, d0, d1, r0)
            assert all(0 <= x < q for x in z)
            out.append(" ".join(f"{x:x}" for x in (q, qinv, direction, halve, d0, d1, r0, *z)))
    return out


def ntt16_lanes(pair, x, y, wa, wb):
    """Lane A / B operands (a, b, w) of a packed NTT request; pair 0 inter-word, 1 intra-word (spec 10, 4.9)."""
    xl, xh, yl, yh = x & 0xFFFF, x >> 16, y & 0xFFFF, y >> 16
    if pair == 0:
        return (xl, yl, wa), (xh, yh, wb)
    return (xl, xh, wa), (yl, yh, wb)


def ntt16_words(pair, oa, ob):
    """Result words (x, y) from the lane results (first, second)."""
    if pair == 0:
        return oa[0] | ob[0] << 16, oa[1] | ob[1] << 16
    return oa[0] | oa[1] << 16, ob[0] | ob[1] << 16


def ntt16_cases(q, rng):
    rbits = 16
    qinv = (-pow(q, -1, 1 << rbits)) % (1 << rbits)
    mont, ct, gs = ntt_ops(q, rbits)
    sv = special_values(q, rbits)
    out = []
    for direction, halve in ((0, 0), (1, 0), (1, 1)):
        for pair in (0, 1):
            # lane slots: (a, b, w) of lane A, then of lane B, as values; mapped to words below
            cases = []
            for i, v in enumerate(sv):
                for sl in range(6):
                    x = [rng.randrange(q) for _ in range(6)]
                    x[sl] = v
                    cases.append(x)
            for k in range(1, rbits):                 # T = b * w a multiple of R (T_low = 0, T != 0)
                a, b = 1 << k, 1 << (rbits - k)
                if a < q and b < q:
                    cases.append([rng.randrange(q), a, b, rng.randrange(q), b, a])
            cases += [[rng.randrange(q) for _ in range(6)] for _ in range(RANDOM_PER_GROUP)]
            for aA, bA, wa, aB, bB, wb in cases:
                if pair == 0:
                    x, y = aA | aB << 16, bA | bB << 16
                else:
                    x, y = aA | bA << 16, aB | bB << 16
                la, lb = ntt16_lanes(pair, x, y, wa, wb)
                assert la == (aA, bA, wa) and lb == (aB, bB, wb)
                res = [ct(a, b, w) if direction == 0 else gs(a, b, w, halve) for a, b, w in (la, lb)]
                zx, zy = ntt16_words(pair, *res)
                out.append(" ".join(f"{v:x}" for v in (q, qinv, direction, halve, pair, x, y, wa, wb, zx, zy)))
    return out


def write(name, header, lines, comment):
    path = OUT / name
    text = f"# {comment}\n# {header}\n" + "\n".join(lines) + "\n"
    path.write_text(text, encoding="ascii", newline="\n")
    return {"file": name, "cases": len(lines), "sha256": hashlib.sha256(text.encode()).hexdigest()}


def wrap32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x >> 31 else x


def fmul(a, b):
    """spec 1.0 01.1, W = 32: wrap32(floor((a*b + 2^15) / 2^16))."""
    return wrap32((a * b + (1 << 15)) >> 16)


def fft_bf(direction, scale, s, ar, br, ai, bi, wr, wi):
    """Mode 5: one FFT 32-bit butterfly. Forward (A + T, A - T), T = B * w; inverse (A + B, (A - B) * w). 3-product
    complex multiply, every operation wraps to 32 bits; scale: div2e(v, s) = (wrap32(v + 2^(s-1))) >> s (arithmetic)."""
    if direction:
        o1, o2 = wrap32(ar - br), wrap32(ai - bi)
    else:
        o1, o2 = br, bi
    p0, p1 = fmul(o1, wr), fmul(o2, wi)
    p2 = fmul(wrap32(o1 + o2), wrap32(wr + wi))
    tr, ti = wrap32(p0 - p1), wrap32(wrap32(p2 - p0) - p1)
    if direction:
        z = [wrap32(ar + br), tr, wrap32(ai + bi), ti]
    else:
        z = [wrap32(ar + tr), wrap32(ar - tr), wrap32(ai + ti), wrap32(ai - ti)]
    if scale:
        z = [wrap32(v + (1 << (s - 1))) >> s for v in z]
    return z


def fft_bf_cases(rng):
    edges = [0, 1, -1, 0x7FFFFFFF, -0x80000000, 0x10000, -0x10000, 0x7FFF8000, 0x8000]
    out = []
    for direction in (0, 1):
        for scale, s in ((0, 0), (1, 1), (1, 5), (1, 9)):
            if direction == 0 and scale:
                continue                          # forward FFT never scales
            vals = []
            for e in edges:                       # every edge value in every operand, the rest random
                for pos in range(6):
                    v = [wrap32(rng.getrandbits(32)) for _ in range(6)]
                    v[pos] = e
                    vals.append(v)
            vals += [[wrap32(rng.getrandbits(32)) for _ in range(6)] for _ in range(2 * RANDOM_PER_GROUP)]
            for ar, br, ai, bi, wr, wi in vals:
                z = fft_bf(direction, scale, s, ar, br, ai, bi, wr, wi)
                out.append(" ".join(f"{x & 0xFFFFFFFF:08x}" if i > 2 else f"{x:x}"
                                    for i, x in enumerate([direction, scale, s, ar, br, ai, bi, wr, wi, *z])))
    return out


def wrapw(x, w):
    x &= (1 << w) - 1
    return x - (1 << w) if x >> (w - 1) else x


def fft_bf_w(w, direction, scale, s, ar, br, ai, bi, wr, wi):
    """Mode 5 at W = 64 / 128 bit (spec 1.0 01.1: mul(a, b) = wrap(floor((a*b + 2^(W/2-1)) / 2^(W/2))), the same
    butterfly as fft_bf, every operation wraps to W bits; scale: div2e(v, s) = (wrap(v + 2^(s-1))) >> s."""
    f = w // 2
    mul = lambda a, b: wrapw((a * b + (1 << (f - 1))) >> f, w)
    if direction:
        o1, o2 = wrapw(ar - br, w), wrapw(ai - bi, w)
    else:
        o1, o2 = br, bi
    p0, p1 = mul(o1, wr), mul(o2, wi)
    p2 = mul(wrapw(o1 + o2, w), wrapw(wr + wi, w))
    tr, ti = wrapw(p0 - p1, w), wrapw(wrapw(p2 - p0, w) - p1, w)
    if direction:
        z = [wrapw(ar + br, w), tr, wrapw(ai + bi, w), ti]
    else:
        z = [wrapw(ar + tr, w), wrapw(ar - tr, w), wrapw(ai + ti, w), wrapw(ai - ti, w)]
    if scale:
        z = [wrapw(v + (1 << (s - 1)), w) >> s for v in z]
    return z


def fft_bf_wide_cases(rng):
    """fmt 1 (64 bit) and 2 (128 bit); for each, the same groups and edge pattern as fft_bf_cases."""
    out = []
    for fmt, w in ((1, 64), (2, 128)):
        h = 1 << (w - 1)
        edges = [0, 1, -1, h - 1, -h, 1 << (w // 2), -(1 << (w // 2)), (1 << 32) - 1, 1 << 32, -(1 << 32),
                 h - (1 << (w // 2 - 1)), 1 << (w // 2 - 1)]
        for direction in (0, 1):
            for scale, s in ((0, 0), (1, 1), (1, 5), (1, 9)):
                if direction == 0 and scale:
                    continue
                vals = []
                for e in edges:
                    for pos in range(6):
                        v = [wrapw(rng.getrandbits(w), w) for _ in range(6)]
                        v[pos] = e
                        vals.append(v)
                vals += [[wrapw(rng.getrandbits(w), w) for _ in range(6)] for _ in range(RANDOM_PER_GROUP)]
                for ar, br, ai, bi, wr, wi in vals:
                    z = fft_bf_w(w, direction, scale, s, ar, br, ai, bi, wr, wi)
                    out.append(" ".join([f"{fmt:x}", f"{direction:x}", f"{scale:x}", f"{s:x}"] +
                                        [f"{x & ((1 << w) - 1):0{w // 4}x}" for x in (ar, br, ai, bi, wr, wi, *z)]))
    return out


def main():
    for q in Q_NTT:
        assert q % 2 == 1 and 3 <= q < 1 << 31
    for q in Q_NTT[5:9]:
        assert is_prime(q), q
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    files = [
        # vector files stay ASCII so any $fscanf reader handles them
        write("ntt.txt", HEADERS["ntt"], [l for q in Q_NTT for l in ntt_cases(q, 32, rng)],
              "NTT mode (req_mode 0), one 32-bit lane, R = 2^32 for every q (both reduction variants)"),
        # own random streams, so each file keeps its hash when another one changes
        write("fft32bf.txt", "dir scale s ar br ai bi wr wi zr0 zr1 zi0 zi1", fft_bf_cases(random.Random(SEED + 5)),
              "FFT mode (req_mode 1) at 32 bit, two beats (real pair, imaginary pair); dir 0 forward, 1 inverse"),
        write("fftwbf.txt", "fmt dir scale s ar br ai bi wr wi zr0 zr1 zi0 zi1", fft_bf_wide_cases(random.Random(SEED + 6)),
              "FFT mode at 64 / 128 bit (fmt 1 / 2): 2L beats of 32-bit limbs (real limbs low first, then imaginary)"),
        write("ntt16.txt", "q qinv dir halve pair x y wa wb zx zy",
              [l for q in Q_NTT16 for l in ntt16_cases(q, random.Random(SEED + 7 + q))],
              "packed NTT mode (req_mode 2): two 16-bit butterflies per request, R = 2^16; pair 0 = (x.lo, y.lo) "
              "(x.hi, y.hi), 1 = (x.lo, x.hi) (y.lo, y.hi); tile constants cfg_q = {q, q}, cfg_qinv = {qinv, qinv}"),
    ]
    manifest = {
        "spec": "FlexTransform 2.0, 10_hop_dong_tile.md",
        "generator": "scripts/build_spec2_tile_vectors.py",
        "seed": SEED,
        "q_ntt": list(Q_NTT),
        "q_ntt16": list(Q_NTT16),
        "montgomery_r": "2^32 (NTT hai hệ số mỗi từ: 2^16)",
        "modes": {"0": "NTT: một butterfly", "1": "FFT: một butterfly 32 / 64 / 128 bit (2L nhịp)",
                  "2": "NTT hai hệ số mỗi từ: hai butterfly 16 bit trên hai từ"},
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for f in files:
        print(f"{f['file']:18s} {f['cases']:6d} ca  {f['sha256'][:16]}")


if __name__ == "__main__":
    main()
