"""FFT 64 / 128 bit on the single-lane tile, limb by limb (planning model, before RTL).

Design (A) (model/fft_core_plan.py) keeps one complex butterfly in one tile. At W = 64 / 128 bit each value is
L = W / 32 limbs of 32 bit (little end first, top limb signed). The tile reuses its own operations:

  - the fused 32x32 multiplier, raw product (mode 0), with a signed / unsigned flag per operand;
  - one product accumulator, column by column (product scanning): column k sums the limb products a_i * b_j with
    i + j = k, adds the rounding 2^31 in column L/2 - 1, emits 32 bit and shifts right by 32. The product
    mul(a, b) = (a * b + 2^(W/2 - 1)) >> W/2 is the emitted columns L/2 .. L/2 + L - 1; products with
    i + j >= 3L/2 do not reach them (W = 128: a3 * b3 dropped, 15 products; W = 64: 4);
  - the modular add/sub with q = 0 and a carry between limbs (sum and difference of the same two limbs together);
  - div2e by limbs: rounding carry from the low limb, then a right shift that takes s bits from the next limb.

It checks the limb arithmetic bit for bit against spec 1.0 (01.1 - 01.4) and the 1.0 golden FFT / IFFT cases
(formats 1, 2), counts the work of one butterfly per resource (multiplier, accumulator, add/sub), gives the tile
occupancy, the N = 1024 cycles against hypothesis 3 (locked, lần 7), the root ROM size per width, and whether the
roots of a narrower width can be derived from the 128-bit table inside the tile.

Run: python model/fft_wide_tile.py   (writes study/results/fft_wide_tile.md)
"""
import importlib.util
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("fft_core_plan", ROOT / "model" / "fft_core_plan.py")
fp = importlib.util.module_from_spec(_s)
_s.loader.exec_module(fp)

M32 = (1 << 32) - 1
TILES = 16
H3 = fp.H3


# ---------------- limb arithmetic ----------------

def to_limbs(x, L):
    x &= (1 << (32 * L)) - 1
    return [(x >> (32 * k)) & M32 for k in range(L)]


def from_limbs(v):
    L = len(v)
    x = sum(l << (32 * k) for k, l in enumerate(v))
    return fp.wrap(x, 32 * L)


def limb_val(v, k):
    """Limb k as the multiplier sees it: top limb signed, the others unsigned."""
    x = v[k]
    return x - (1 << 32) if (k == len(v) - 1 and x >> 31) else x


def mul_limbs(a, b):
    """Product scanning. Returns the result limbs and the number of 32x32 products used."""
    L = len(a)
    lo = L // 2                        # first emitted column
    acc, out, nprod = 0, [], 0
    for k in range(lo + L):            # columns k >= 3L/2 cannot reach the result
        for i in range(L):
            j = k - i
            if 0 <= j < L:
                acc += limb_val(a, i) * limb_val(b, j)
                nprod += 1
        if k == lo - 1:
            acc += 1 << 31             # rounding 2^(W/2 - 1)
        if k >= lo:
            out.append(acc & M32)
        acc >>= 32                     # arithmetic shift (Python ints)
    return out, nprod


def add_limbs(a, b, sub=False):
    """One 32-bit add/sub per limb with a carry (borrow) between limbs; wraps at W."""
    out, c = [], 1 if sub else 0
    for x, y in zip(a, b):
        s = x + ((~y & M32) if sub else y) + c
        out.append(s & M32)
        c = s >> 32
    return out


def div2e_limbs(a, s):
    """(a + 2^(s-1)) >> s, arithmetic, wrap at W: a rounding carry pass, then a shift taking s bits from the next limb."""
    if s == 0:
        return list(a)
    r = add_limbs(a, to_limbs(1 << (s - 1), len(a)))
    sign = M32 if r[-1] >> 31 else 0
    nxt = r[1:] + [sign]
    return [((x >> s) | (y << (32 - s))) & M32 for x, y in zip(r, nxt)]


def cmul_limbs(ar, ai, br, bi):
    p0, n0 = mul_limbs(ar, br)
    p1, n1 = mul_limbs(ai, bi)
    p2, n2 = mul_limbs(add_limbs(ar, ai), add_limbs(br, bi))
    s01 = add_limbs(p0, p1)
    return add_limbs(p0, p1, sub=True), add_limbs(p2, s01, sub=True), n0 + n1 + n2


def check_random(trials=20000):
    rng = random.Random(7)
    edge = lambda w: [0, 1, -1, (1 << (w - 1)) - 1, -(1 << (w - 1)), 1 << (w // 2), -(1 << (w // 2)), 1 << (w // 2 - 1)]
    n = 0
    for w in (64, 128):
        L = w // 32
        vals = edge(w)
        for t in range(trials):
            a, b, c, d = (rng.choice(vals) if rng.random() < 0.2 else fp.wrap(rng.getrandbits(w), w) for _ in range(4))
            got, _ = mul_limbs(to_limbs(a, L), to_limbs(b, L))
            assert from_limbs(got) == fp.mul(a, b, w), (w, a, b)
            tr, ti, _ = cmul_limbs(*(to_limbs(x, L) for x in (a, b, c, d)))
            er, ei = fp.cmul(a, b, c, d, w)
            assert (from_limbs(tr), from_limbs(ti)) == (er, ei)
            s = rng.randrange(0, 10)
            assert from_limbs(div2e_limbs(to_limbs(a, L), s)) == ((fp.wrap(a + (1 << (s - 1)), w) >> s) if s else a)
            n += 1
    return n


# ---------------- whole transforms by limbs vs the 1.0 golden cases ----------------

def fft_limbs(a, logn, L, gm):
    a = [to_limbs(x, L) for x in a]
    n, hn = 1 << logn, (1 << logn) // 2
    span, groups = hn, 2
    while span >= 2:
        half = span // 2
        for g in range(groups // 2):
            wr, wi = (to_limbs(x, L) for x in gm[groups + g])
            for off in range(half):
                j = g * span + off
                tr, ti, _ = cmul_limbs(a[j + half], a[j + half + hn], wr, wi)
                ar, ai = a[j], a[j + hn]
                a[j], a[j + half] = add_limbs(ar, tr), add_limbs(ar, tr, sub=True)
                a[j + hn], a[j + half + hn] = add_limbs(ai, ti), add_limbs(ai, ti, sub=True)
        span, groups = half, groups * 2
    return [from_limbs(x) for x in a]


def ifft_limbs(a, logn, L, igm):
    a = [to_limbs(x, L) for x in a]
    n, hn = 1 << logn, (1 << logn) // 2
    stride, groups = 1, n
    s = logn - 1
    while groups > 2:
        last = groups == 4
        for g in range(groups // 4):
            wr, wi = (to_limbs(x, L) for x in igm[groups // 2 + g])
            for off in range(stride):
                j = 2 * g * stride + off
                ar, ai, br, bi = a[j], a[j + hn], a[j + stride], a[j + stride + hn]
                sr, si = add_limbs(ar, br), add_limbs(ai, bi)
                tr, ti, _ = cmul_limbs(add_limbs(ar, br, sub=True), add_limbs(ai, bi, sub=True), wr, wi)
                if last:               # the division folded into the last layer, as in the 32-bit core
                    sr, si, tr, ti = (div2e_limbs(x, s) for x in (sr, si, tr, ti))
                a[j], a[j + hn], a[j + stride], a[j + stride + hn] = sr, si, tr, ti
        stride, groups = stride * 2, groups // 2
    return [from_limbs(x) for x in a]


def check_fixtures():
    gm = {w: fp.roots(w) for w in (64, 128)}
    igm = {w: fp.roots_inv(w) for w in (64, 128)}
    n = 0
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] not in (0, 1) or c["fmt"] not in (1, 2) or c["logn"] < 2:
            continue
        w = 32 << c["fmt"]
        a = [fp.wrap(int(x, 16), w) for x in d["a"][0]]
        e = [fp.wrap(int(x, 16), w) for x in d["expected"][0]]
        got = fft_limbs(a, c["logn"], w // 32, gm[w]) if c["op"] == 0 else ifft_limbs(a, c["logn"], w // 32, igm[w])
        assert got == e, (c, w)
        n += 1
    return n


# ---------------- work of one butterfly, tile occupancy, cycles ----------------

def work(L, inverse, last=False, w_sum_in_rom=False):
    """Cycles of each tile resource for one butterfly at L limbs.
    Multiplier: one 32x32 product per cycle. Accumulator: in step with the multiplier (its own adder).
    Add/sub: one limb per cycle, sum and difference of the same two limbs together."""
    nprod = 3 * mul_limbs([0] * L, [0] * L)[1]
    ops = {
        "A + B, A - B (re, im)": 2 * L if inverse else 0,
        "o.re + o.im": L,
        "wr + wi": 0 if w_sum_in_rom else L,
        "p0 - p1, p0 + p1": L,
        "p2 - (p0 + p1)": L,
        "A + T, A - T (re, im)": 0 if inverse else 2 * L,
        "div2e (rounding pass + shift, 4 values)": 2 * 4 * L if (inverse and last) else 0,
    }
    return nprod, ops


def occupancy(L, inverse, last=False, w_sum_in_rom=False):
    nprod, ops = work(L, inverse, last, w_sum_in_rom)
    return max(nprod, sum(ops.values())), nprod, sum(ops.values())


def cycles(w, logn, inverse, w_sum_in_rom=False, lat=None):
    """Barrier per layer, as fp.cycles_a, with the occupancy from the resource count (last IFFT layer may be longer)."""
    L = w // 32
    n = 1 << logn
    bf = n // 4
    per_tile = math.ceil(bf / TILES)
    layers = logn - 1
    if lat is None:
        lat = fp.cycles_a(w, logn, inverse)[1]
    total = 0
    for k in range(layers):
        occ = occupancy(L, inverse, inverse and k == layers - 1, w_sum_in_rom)[0] if L > 1 else 3
        total += per_tile * occ + lat - occ
    return total


# ---------------- roots: table sizes, narrower widths from the 128-bit table ----------------

def roots_derivable():
    """Can the 64-bit roots (forward / inverse) be taken from the 128-bit table by one rounding pass in the tile?
    Rounding to 64 bit: (x + 2^31) >> 32 on the 128-bit value; the inverse 128-bit root im is -im (exact)."""
    r128, r64 = fp.roots(128), fp.roots(64)
    i128, i64 = fp.roots_inv(128), fp.roots_inv(64)
    rnd = lambda x: fp.wrap((x + (1 << 31)) >> 32, 64)
    fwd_ok = all((rnd(a), rnd(b)) == c for (a, b), c in zip(r128, r64))
    inv_ok = all((rnd(a), rnd(b)) == c for (a, b), c in zip(i128, i64))
    neg_ok = all(c[1] == fp.wrap(-a[1], 64) for a, c in zip(r64, i64))
    neg32 = all(c[1] == fp.wrap(-a[1], 32) for a, c in zip(fp.roots(32), fp.roots_inv(32)))
    return fwd_ok, inv_ok, neg_ok, neg32


def rom_kbit(nroots=768):
    out = {}
    for w in (32, 64, 128):
        out[w] = nroots * 2 * w / 1024        # (re, im), one direction
    return out


def main():
    nr = check_random()
    nf = check_fixtures()
    fwd_ok, inv_ok, neg_ok, neg32 = roots_derivable()
    lines = ["# FFT 64 / 128 bit trên tile một làn, theo từng phần 32 bit (mô hình trước RTL)\n",
             "Mô hình: [model/fft_wide_tile.py](../../model/fft_wide_tile.py). Số học theo phần 32 bit (nhân cộng dồn theo cột, "
             "cộng/trừ có nhớ, div2e) khớp từng bit với spec 1.0: "
             f"{nr} phép nhân / nhân phức / div2e ngẫu nhiên và biên, {nf} ca vàng FFT / FFT ngược định dạng 1, 2 (logn 2..10).\n",
             "## Việc của một butterfly (số chu kỳ của từng bộ phận trong tile)\n",
             "| W | Chiều | Tích 32×32 (bộ nhân) | Phép cộng/trừ 32 bit | Chiếm tile (chu kỳ) |",
             "|---:|---|---:|---:|---:|"]
    for w in (64, 128):
        L = w // 32
        for inv, name in ((False, "xuôi"), (True, "ngược"), (True, "ngược, tầng cuối (div2e)")):
            last = name.endswith("(div2e)")
            occ, npr, nops = occupancy(L, inv, last)
            lines.append(f"| {w} | {name} | {npr} | {nops} | {occ} |")
    _, ops = work(4, True, True)
    lines.append("\nPhép cộng/trừ (mỗi giá trị L phần): " + "; ".join(f"{k} = {v // 4}·L" for k, v in ops.items() if v) +
                 "; FFT xuôi thay A ± B bằng A ± T = 2·L.\n")
    lines.append("## Chu kỳ N = 1024 (rào chắn mỗi tầng; độ trễ đọc → ghi như model/fft_core_plan.py)\n")
    lines.append("| W | Xuôi | Ngược | Ngưỡng giả thuyết 3 (xuôi / ngược) | Xuôi, wr + wi lấy từ ROM | Ngược, wr + wi lấy từ ROM |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    res = {}
    for w in (32, 64, 128):
        f, i = cycles(w, 10, False), cycles(w, 10, True)
        fr, ir = cycles(w, 10, False, True), cycles(w, 10, True, True)
        res[w] = (f, i)
        lines.append(f"| {w} | {f} | {i} | {H3['fwd'][w]} / {H3['inv'][w]} | {fr} | {ir} |")
    f512 = {w: cycles(w, 9, False) for w in (32, 128)}
    lines.append(f"\nTỉ lệ 128 / 32 bit = {res[128][0] / res[32][0]:.1f} (ngưỡng ≥ 10; N512 {f512[128] / f512[32]:.1f}, ≥ 8); "
                 f"128 / 64 bit = {res[128][0] / res[64][0]:.1f} (≥ 3). Hàng 32 bit là lõi đã đo (chế độ 5, 539 chu kỳ).\n")
    kb = rom_kbit()
    lines.append("## Root\n")
    lines.append(f"- Bảng một chiều, 768 root (re, im): 32 bit {kb[32]:.0f} kbit, 64 bit {kb[64]:.0f} kbit, 128 bit {kb[128]:.0f} kbit "
                 f"(một BRAM36 = 36 kbit).")
    lines.append(f"- Root 64 bit = làm tròn root 128 bit: xuôi {'khớp' if fwd_ok else 'không khớp'}, ngược "
                 f"{'khớp' if inv_ok else 'không khớp'}. Root ngược = (re, −im) của root xuôi: 128 bit đúng theo định nghĩa, "
                 f"64 bit {'đúng' if neg_ok else 'không đúng'}, 32 bit {'đúng' if neg32 else 'không đúng'}.")
    (ROOT / "study" / "results" / "fft_wide_tile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
