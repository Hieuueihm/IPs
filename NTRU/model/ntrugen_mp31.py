"""NTT modulo the 31-bit primes of NTRUGen on the FlexTransform datapath (docs/architecture_v1.md).

Reference: third_party/r8/ntrugen/src/ng_mp31.c (pinned with the FN-DSA reference), built with
NTRUGEN_AVX2 = 0 by model/ntrugen_mp31_harness.c, which dumps for all 323 primes of PRIMES[]:
mp_montymul on edge and random pairs, and for logn = 1..10 the root tables of mp_mkgmigm,
mp_NTT on random input and mp_iNTT on random input.

Checks, in the form the hardware computes:
  1. Montgomery from 16x16 leaf products and the shared adder (R = 2^32, q' = p0i):
       T = a*b; m = (T_low * q') mod 2^32; u = T_high + (m*q)_high + [T_low != 0]; u - q if u >= q.
  2. Root tables as the host must load them:
       gm[rev(u)]  = g_n^u * R mod p,  igm[rev(u)] = (1/2) * g_n^(-u) * R mod p,
       g_n = primitive 2n-th root (the table g squared 10 - logn times), rev over logn bits.
  3. Two-layer frames (4 coefficients, 3 roots) plus a single-layer last pass when logn is odd:
       forward CT  (x, y) -> (x + w*y, x - w*y)
       inverse GS  (x, y) -> (half(x + y), w*(x - y)), half(v) = (v + (p if v odd)) >> 1,
       halving at every layer and no final 1/n (the 1/2 of the difference branch is inside igm).
  4. Single-layer passes of the tile contract with one butterfly per request (spec 2.0, 10 since
     31/10/2026): every layer is one pass, each butterfly is one tile request (mode 4: x = d0, y = d1,
     w = r0), and the butterflies of a layer are issued in a random order (seeded), to check that the
     result does not depend on the issue order.

Run: python model/ntrugen_mp31.py   (builds the harness with gcc if needed;
     writes study/results/ntrugen_mp31.md)
"""
import os
import random
import shutil
import subprocess
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "third_party" / "r8" / "ntrugen" / "src"
BUILD = ROOT / "study" / "build" / "ntrugen_mp31"
NUM_PRIMES, MONT_PAIRS = 323, 67
R = 1 << 32


def leaf_mul(x, y, xl, yl):
    """x*y from 16x16 leaf products (xl, yl = number of 16-bit limbs), as the tree sums them."""
    acc = 0
    for i in range(xl):
        for j in range(yl):
            acc += ((x >> 16 * i) & 0xFFFF) * ((y >> 16 * j) & 0xFFFF) << 16 * (i + j)
    return acc


def mont_hw(a, b, p, qp):
    t = leaf_mul(a, b, 2, 2)                          # pass 1: 4 leaves
    t_lo, t_hi = t & (R - 1), t >> 32
    m = leaf_mul(t_lo, qp, 2, 2) & (R - 1)            # pass 2: only the low half is kept
    mq_hi = leaf_mul(m, p, 2, 2) >> 32                # pass 3: 4 leaves
    u = t_hi + mq_hi + (t_lo != 0)                    # shared "high part + correction + carry" adder
    assert u < 2 * p
    return u - p if u >= p else u


def add_hw(x, y, p):
    s = x + y
    return s - p if s >= p else s


def sub_hw(x, y, p):
    d = x - y
    return d + p if d < 0 else d


def half_hw(v, p):
    return (v + (p if v & 1 else 0)) >> 1


def rev(u, bits):
    return int(format(u, f"0{bits}b")[::-1], 2) if bits else 0


def root_tables(logn, p, g_mont, ig_mont):
    n = 1 << logn
    rinv = pow(R, -1, p)
    gn = pow(g_mont * rinv % p, 1 << (10 - logn), p)
    ign = pow(ig_mont * rinv % p, 1 << (10 - logn), p)
    half = pow(2, -1, p)
    gm, igm = [0] * n, [0] * n
    for u in range(n):
        gm[rev(u, logn)] = pow(gn, u, p) * R % p
        igm[rev(u, logn)] = half * pow(ign, u, p) * R % p
    return gm, igm


def ntt_frames(a, gm, logn, p, qp):
    """Forward: two-layer frames over layers (lm, lm + 1), then a single-layer tail if logn is odd."""
    a, n = list(a), 1 << logn
    frames = 0

    def bf(x, y, w):
        t = mont_hw(y, w, p, qp)
        return add_hw(x, t, p), sub_hw(x, t, p)

    lm = 0
    while lm + 1 < logn:
        m, t = 1 << lm, n >> lm
        ht, q4 = t >> 1, t >> 2
        for u in range(m):
            w0, w1, w2 = gm[m + u], gm[2 * m + 2 * u], gm[2 * m + 2 * u + 1]   # one root bundle
            for v in range(q4):
                j = u * t + v
                x0, x1, x2, x3 = a[j], a[j + q4], a[j + ht], a[j + ht + q4]
                x0, x2 = bf(x0, x2, w0)
                x1, x3 = bf(x1, x3, w0)
                x0, x1 = bf(x0, x1, w1)
                x2, x3 = bf(x2, x3, w2)
                a[j], a[j + q4], a[j + ht], a[j + ht + q4] = x0, x1, x2, x3
                frames += 1
        lm += 2
    if lm < logn:
        m, t = 1 << lm, n >> lm
        ht = t >> 1
        for u in range(m):
            for v in range(ht):
                j = u * t + v
                a[j], a[j + ht] = bf(a[j], a[j + ht], gm[m + u])
    return a, frames


def intt_frames(a, igm, logn, p, qp):
    """Inverse: GS with halving at every layer, two-layer frames, single-layer tail if logn is odd."""
    a, n = list(a), 1 << logn

    def bf(x, y, w):
        return half_hw(add_hw(x, y, p), p), mont_hw(sub_hw(x, y, p), w, p, qp)

    lm, t = 0, 1
    while lm + 1 < logn:
        hm = n >> (lm + 1)
        hm2 = hm >> 1
        for u2 in range(hm2):
            w0, w1, w2 = igm[hm + 2 * u2], igm[hm + 2 * u2 + 1], igm[hm2 + u2]
            for v in range(t):
                j = u2 * 4 * t + v
                x0, x1, x2, x3 = a[j], a[j + t], a[j + 2 * t], a[j + 3 * t]
                x0, x1 = bf(x0, x1, w0)
                x2, x3 = bf(x2, x3, w1)
                x0, x2 = bf(x0, x2, w2)
                x1, x3 = bf(x1, x3, w2)
                a[j], a[j + t], a[j + 2 * t], a[j + 3 * t] = x0, x1, x2, x3
        lm, t = lm + 2, t * 4
    if lm < logn:
        hm = n >> (lm + 1)
        for u in range(hm):
            for v in range(t):
                j = u * 2 * t + v
                a[j], a[j + t] = bf(a[j], a[j + t], igm[hm + u])
    return a


def tile_request(direction, x, y, w, p, qp):
    """One mode-4 request of the single-lane tile (halving on for GS, as NTRUGen needs)."""
    if direction == 0:
        t = mont_hw(y, w, p, qp)
        return add_hw(x, t, p), sub_hw(x, t, p)
    return half_hw(add_hw(x, y, p), p), mont_hw(sub_hw(x, y, p), w, p, qp)


def ntt_single(a, gm, logn, p, qp, rng):
    """Forward CT, one pass per layer, butterflies issued in a random order."""
    a, n = list(a), 1 << logn
    for lm in range(logn):
        m, t = 1 << lm, n >> lm
        ht = t >> 1
        jobs = [(u * t + v, m + u) for u in range(m) for v in range(ht)]
        rng.shuffle(jobs)
        for j, r in jobs:
            a[j], a[j + ht] = tile_request(0, a[j], a[j + ht], gm[r], p, qp)
    return a


def intt_single(a, igm, logn, p, qp, rng):
    """Inverse GS with halving, one pass per layer, butterflies issued in a random order."""
    a, n = list(a), 1 << logn
    t = 1
    for lm in range(logn):
        hm = n >> (lm + 1)
        jobs = [(u * 2 * t + v, hm + u) for u in range(hm) for v in range(t)]
        rng.shuffle(jobs)
        for j, r in jobs:
            a[j], a[j + t] = tile_request(1, a[j], a[j + t], igm[r], p, qp)
        t *= 2
    return a


def build_dump():
    exe, dump = BUILD / "harness.exe", BUILD / "dump.bin"
    if dump.exists():
        return dump
    BUILD.mkdir(parents=True, exist_ok=True)
    gcc = shutil.which("gcc") or r"C:\msys64\mingw64\bin\gcc.exe"
    env = dict(os.environ, PATH=str(Path(gcc).parent) + os.pathsep + os.environ.get("PATH", ""))
    subprocess.run([gcc, "-O2", "-DNTRUGEN_AVX2=0", f"-I{SRC}", str(ROOT / "model" / "ntrugen_mp31_harness.c"),
                    str(SRC / "ng_mp31.c"), "-o", str(exe)], check=True, env=env)
    subprocess.run([str(exe), str(dump)], check=True, env=env)
    return dump


def main():
    words = array("I")
    words.frombytes(build_dump().read_bytes())
    assert sys.byteorder == "little"
    pos = 0

    def take(k):
        nonlocal pos
        pos += k
        return words[pos - k:pos].tolist()

    mont_ok = tab_ok = fwd_ok = inv_ok = fwd1_ok = inv1_ok = 0
    rng = random.Random(20261031)
    max_p = 0
    for _ in range(NUM_PRIMES):
        p, p0i, g, ig = take(4)
        assert p < 1 << 31 and p0i == (-pow(p, -1, R)) % R
        for _ in range(MONT_PAIRS):
            x, y, ref = take(3)
            assert mont_hw(x, y, p, p0i) == ref, (p, x, y)
            mont_ok += 1
        for logn in range(1, 11):
            n = 1 << logn
            gm, igm, a, ntt_ref, b, intt_ref = (take(n) for _ in range(6))
            assert (gm, igm) == root_tables(logn, p, g, ig), (p, logn)
            tab_ok += 1
            out, _ = ntt_frames(a, gm, logn, p, p0i)
            assert out == ntt_ref, (p, logn, "NTT")
            fwd_ok += 1
            assert intt_frames(b, igm, logn, p, p0i) == intt_ref, (p, logn, "iNTT")
            inv_ok += 1
            assert ntt_single(a, gm, logn, p, p0i, rng) == ntt_ref, (p, logn, "NTT one layer")
            fwd1_ok += 1
            assert intt_single(b, igm, logn, p, p0i, rng) == intt_ref, (p, logn, "iNTT one layer")
            inv1_ok += 1
            max_p = max(max_p, p)
    assert pos == len(words)

    lines = [
        "# NTT modulo các prime 31 bit của NTRUGen trên đường dữ liệu FlexTransform\n",
        "Bản chuẩn: `ng_mp31.c` của NTRUGen đi kèm bản FN-DSA đã ghim, build `NTRUGEN_AVX2=0` "
        "(`model/ntrugen_mp31_harness.c`). Cả 323 prime của bảng `PRIMES`, logn = 1..10.\n",
        "| Kiểm | Số trường hợp | Kết quả |",
        "|---|---:|---|",
        f"| Montgomery dựng từ tích 16×16 + bộ cộng chung = `mp_montymul` (gồm 0, 1, p − 1) | {mont_ok} | khớp |",
        f"| Bảng root tính theo công thức = `mp_mkgmigm` | {tab_ok} | khớp |",
        f"| NTT xuôi bằng nhịp hai tầng (+ một tầng cuối khi logn lẻ) = `mp_NTT` | {fwd_ok} | khớp |",
        f"| NTT ngược GS, chia đôi mỗi tầng, nhịp hai tầng = `mp_iNTT` | {inv_ok} | khớp |",
        f"| NTT xuôi, mỗi tầng một lượt, mỗi butterfly một request tile, thứ tự phát ngẫu nhiên = `mp_NTT` | {fwd1_ok} | khớp |",
        f"| NTT ngược GS chia đôi, mỗi tầng một lượt, thứ tự phát ngẫu nhiên = `mp_iNTT` | {inv1_ok} | khớp |",
        "",
        f"Prime lớn nhất {max_p} < 2^31, nên u < 2p < 2^32: thanh ghi 32 bit đủ.",
    ]
    text = "\n".join(lines) + "\n"
    print(text)
    (ROOT / "study" / "results" / "ntrugen_mp31.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
