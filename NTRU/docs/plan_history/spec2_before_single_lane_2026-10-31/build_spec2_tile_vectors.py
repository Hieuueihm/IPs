"""Golden vectors for the tile contract of spec 2.0 (spec/FlexTransform/2.0/10_hop_dong_tile.md).

Expected values come only from plain integer and modular arithmetic:
  raw 32x32:  exact a*b as 65-bit two's complement
  FFT 32 bit: wrap32(floor((a*b + c) / 2^16)), c = 2^15 or 0
  NTT:        Mont(a, b) = a*b*R^-1 mod q;  half(s) = s*2^-1 mod q
This script must not import the leaf-level hardware models in model/: those are what the vectors test.

Output (spec/FlexTransform/2.0/assets/tile/), one case per line, fields in hex separated by spaces, '#' comments:
  raw32.txt       sign_a sign_b a b product65
  fft32.txt       floor a b result
  ntt16_pqc.txt   q qinv lane32 mode dir halve d0 d1 d2 d3 r0 r1 r2 r3 z0 z1 z2 z3   (both reduction variants)
  ntt16_q_khac.txt  same, other odd q < 2^16 (reduction on the array only)
  ntt32.txt       same, lane 32 bit, q < 2^31 (both variants)
  manifest.json   seed, counts, SHA-256

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

Q16_PQC = (3329, 12289)
Q16_OTHER = (3, 7681, 65521)
# 8380417 (ML-DSA); first, a middle and the last prime of NTRUGen's PRIMES[]; 2^31 - 1; a 16-bit q in a 32-bit lane
Q32 = (8380417, 2147473409, 2144120833, 2140348417, 2147483647, 12289)

HEADERS = {
    "raw32.txt": "sign_a sign_b a b product65",
    "fft32.txt": "floor a b result",
    "ntt": "q qinv lane32 mode dir halve d0 d1 d2 d3 r0 r1 r2 r3 z0 z1 z2 z3",
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


# --- raw and FFT 32 bit -------------------------------------------------------------------------

def as_value(x, signed):
    return x - (1 << 32) if signed and x >> 31 else x


def raw_cases(rng):
    edges = [0, 1, 2, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFF, 0xFFFF0000, 0x0000FFFF, 0x00010000]
    out = []
    for sa in (0, 1):
        for sb in (0, 1):
            pairs = [(a, b) for a in edges for b in edges]
            pairs += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(4 * RANDOM_PER_GROUP)]
            for a, b in pairs:
                p = as_value(a, sa) * as_value(b, sb)
                assert -(1 << 64) <= p < (1 << 64)
                out.append(f"{sa:x} {sb:x} {a:08x} {b:08x} {p & ((1 << 65) - 1):017x}")
    return out


def fft32(a, b, floor_mode):
    p = as_value(a, True) * as_value(b, True)
    c = 0 if floor_mode else 1 << 15
    r = (p + c) >> 16                       # Python >> is floor division by 2^16
    return r & 0xFFFFFFFF


def fft32_cases(rng):
    edges = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, 0x00010000, 0xFFFF0000, 0x00008000, 0xFFFF8000]
    out = []
    for floor_mode in (0, 1):
        pairs = [(a, b) for a in edges for b in edges]
        # exact ties: low 16 bits of a*b equal 0x8000 (positive and negative products), and +-1 around them
        for _ in range(RANDOM_PER_GROUP):
            b = rng.getrandbits(32) | 1
            lo = (0x8000 * pow(b & 0xFFFF, -1, 1 << 16)) & 0xFFFF
            for delta in (0, 1, 0xFFFF):
                a = ((rng.getrandbits(16) << 16) | ((lo + delta) & 0xFFFF))
                pairs.append((a, b))
        pairs += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(4 * RANDOM_PER_GROUP)]
        for a, b in pairs:
            out.append(f"{floor_mode:x} {a:08x} {b:08x} {fft32(a, b, floor_mode):08x}")
    return out


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


def ntt_expected(q, rbits, mode, direction, halve, d, r):
    mont, ct, gs = ntt_ops(q, rbits)
    if mode == 2:
        return [mont(d[i], r[i]) for i in range(4)]
    if mode == 3 and direction == 0:
        y0, y2 = ct(d[0], d[2], r[0])
        y1, y3 = ct(d[1], d[3], r[0])
        z0, z1 = ct(y0, y1, r[1])
        z2, z3 = ct(y2, y3, r[2])
        return [z0, z1, z2, z3]
    if mode == 3:
        y0, y1 = gs(d[0], d[1], r[1], halve)
        y2, y3 = gs(d[2], d[3], r[2], halve)
        z0, z2 = gs(y0, y2, r[0], halve)
        z1, z3 = gs(y1, y3, r[0], halve)
        return [z0, z1, z2, z3]
    if direction == 0:
        z0, z2 = ct(d[0], d[2], r[0])
        z1, z3 = ct(d[1], d[3], r[1])
        return [z0, z1, z2, z3]
    z0, z1 = gs(d[0], d[1], r[0], halve)
    z2, z3 = gs(d[2], d[3], r[1], halve)
    return [z0, z1, z2, z3]


def special_values(q, rbits):
    """0, 1, q - 1, q/2 neighbours, and powers of two whose products are multiples of R (T_low = 0, T != 0)."""
    vals = {0, 1, 2, q - 1, q - 2, q // 2, q // 2 + 1}
    for k in range(rbits + 1):
        if (1 << k) < q:
            vals.add(1 << k)
    return sorted(v for v in vals if 0 <= v < q)


def ntt_cases(q, rbits, rng):
    lane32 = 1 if rbits == 32 else 0
    r = 1 << rbits
    qinv = (-pow(q, -1, r)) % r
    sv = special_values(q, rbits)
    roots_used = {2: 4, 3: 3, 4: 2}
    out = []
    for mode, direction, halve in ((2, 0, 0), (3, 0, 0), (3, 1, 0), (3, 1, 1), (4, 0, 0), (4, 1, 0), (4, 1, 1)):
        nroot = roots_used[mode]
        cases = []
        # every special value in every data slot and every used root slot, others random
        for v in sv:
            for slot in range(4):
                d = [rng.randrange(q) for _ in range(4)]
                d[slot] = v
                rt = [rng.randrange(q) for _ in range(nroot)]
                rt[slot % nroot] = sv[(sv.index(v) + slot) % len(sv)]
                cases.append((d, rt))
        # products that are exact multiples of R: T_low = 0 with T != 0
        for k in range(1, rbits):
            a, b = 1 << k, 1 << (rbits - k)
            if a < q and b < q:
                cases.append(([a, a, a, a], [b] * nroot))
        cases += [([rng.randrange(q) for _ in range(4)], [rng.randrange(q) for _ in range(nroot)])
                  for _ in range(RANDOM_PER_GROUP)]
        for d, rt in cases:
            rr = rt + [0] * (4 - nroot)
            z = ntt_expected(q, rbits, mode, direction, halve, d, rr)
            assert all(0 <= x < q for x in z)
            out.append(" ".join(f"{x:x}" for x in (q, qinv, lane32, mode, direction, halve, *d, *rr, *z)))
    return out


def write(name, header, lines, comment):
    path = OUT / name
    text = f"# {comment}\n# {header}\n" + "\n".join(lines) + "\n"
    path.write_text(text, encoding="ascii", newline="\n")
    return {"file": name, "cases": len(lines), "sha256": hashlib.sha256(text.encode()).hexdigest()}


def main():
    for q in Q16_PQC + Q16_OTHER:
        assert q % 2 == 1 and 3 <= q < 1 << 16
    for q in Q32:
        assert q % 2 == 1 and 3 <= q < 1 << 31
    for q in Q32[:5]:
        assert is_prime(q), q
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    files = [
        # vector files stay ASCII so any $fscanf reader handles them
        write("raw32.txt", HEADERS["raw32.txt"], raw_cases(rng), "mode 0: raw 32x32 product, 65-bit two's complement"),
        write("fft32.txt", HEADERS["fft32.txt"], fft32_cases(rng),
              "mode 1: FFT 32-bit product; floor = 0 round half up, 1 truncate"),
        write("ntt16_pqc.txt", HEADERS["ntt"], [l for q in Q16_PQC for l in ntt_cases(q, 16, rng)],
              "modes 2-4, 16-bit lane, q = 3329 and 12289 (both reduction variants)"),
        write("ntt16_q_khac.txt", HEADERS["ntt"], [l for q in Q16_OTHER for l in ntt_cases(q, 16, rng)],
              "modes 2-4, 16-bit lane, other odd q (reduction on the array only)"),
        write("ntt32.txt", HEADERS["ntt"], [l for q in Q32 for l in ntt_cases(q, 32, rng)],
              "modes 2-4, 32-bit lane (both reduction variants)"),
    ]
    manifest = {
        "spec": "FlexTransform 2.0, 10_hop_dong_tile.md",
        "generator": "scripts/build_spec2_tile_vectors.py",
        "seed": SEED,
        "q_lane16_both_variants": list(Q16_PQC),
        "q_lane16_on_array_only": list(Q16_OTHER),
        "q_lane32": list(Q32),
        "modes": {"2": "bốn phép nhân modulo độc lập", "3": "nhịp hai tầng", "4": "nhịp một tầng"},
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for f in files:
        print(f"{f['file']:18s} {f['cases']:6d} ca  {f['sha256'][:16]}")


if __name__ == "__main__":
    main()
