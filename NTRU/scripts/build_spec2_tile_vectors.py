"""Golden vectors for the tile contract of spec 2.0 (spec/FlexTransform/2.0/10_hop_dong_tile.md).

Expected values come only from plain integer and modular arithmetic:
  raw 32x32:  exact a*b as 65-bit two's complement
  FFT 32 bit: wrap32(floor((a*b + c) / 2^16)), c = 2^15 or 0
  NTT:        Mont(a, b) = a*b*R^-1 mod q with R = 2^32 for every q;  half(s) = s*2^-1 mod q
This script must not import the leaf-level hardware models in model/: those are what the vectors test.

Output (spec/FlexTransform/2.0/assets/tile/), one case per line, fields in hex separated by spaces, '#' comments:
  raw32.txt       sign_a sign_b a b product65
  fft32.txt       floor a b result
  ntt.txt         q qinv mode dir halve d0 d1 r0 z0 z1   (one 32-bit lane: small and large q alike)
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

# One 32-bit lane for every NTT (R = 2^32), small q included, in increasing order so that the
# testbench's +MIX partner of the last small q is the first large one:
# small odd q (3, ML-KEM 3329, 7681, FN-DSA 12289, 65521); 8380417 (ML-DSA); first, a middle and the
# last prime of NTRUGen's PRIMES[]; 2^31 - 1
Q_NTT = (3, 3329, 7681, 12289, 65521, 8380417, 2140348417, 2144120833, 2147473409, 2147483647)

HEADERS = {
    "raw32.txt": "sign_a sign_b a b product65",
    "fft32.txt": "floor a b result",
    "ntt": "q qinv mode dir halve d0 d1 r0 z0 z1",
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


def ntt_expected(q, rbits, mode, direction, halve, d0, d1, r0):
    """One request of the single-lane tile: mode 2 is one modular product, mode 4 one butterfly."""
    mont, ct, gs = ntt_ops(q, rbits)
    if mode == 2:
        return [mont(d0, r0), 0]
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
    for mode, direction, halve in ((2, 0, 0), (4, 0, 0), (4, 1, 0), (4, 1, 1)):
        used = (0, 2) if mode == 2 else (0, 1, 2)     # slots d0, d1, r0; mode 2 leaves d1 = 0
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
            if mode == 2:
                d1 = 0
            z = ntt_expected(q, rbits, mode, direction, halve, d0, d1, r0)
            assert all(0 <= x < q for x in z)
            out.append(" ".join(f"{x:x}" for x in (q, qinv, mode, direction, halve, d0, d1, r0, *z)))
    return out


def write(name, header, lines, comment):
    path = OUT / name
    text = f"# {comment}\n# {header}\n" + "\n".join(lines) + "\n"
    path.write_text(text, encoding="ascii", newline="\n")
    return {"file": name, "cases": len(lines), "sha256": hashlib.sha256(text.encode()).hexdigest()}


def main():
    for q in Q_NTT:
        assert q % 2 == 1 and 3 <= q < 1 << 31
    for q in Q_NTT[5:9]:
        assert is_prime(q), q
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    files = [
        # vector files stay ASCII so any $fscanf reader handles them
        write("raw32.txt", HEADERS["raw32.txt"], raw_cases(rng), "mode 0: raw 32x32 product, 65-bit two's complement"),
        write("fft32.txt", HEADERS["fft32.txt"], fft32_cases(rng),
              "mode 1: FFT 32-bit product; floor = 0 round half up, 1 truncate"),
        write("ntt.txt", HEADERS["ntt"], [l for q in Q_NTT for l in ntt_cases(q, 32, rng)],
              "modes 2 and 4, one 32-bit lane, R = 2^32 for every q (both reduction variants)"),
    ]
    manifest = {
        "spec": "FlexTransform 2.0, 10_hop_dong_tile.md",
        "generator": "scripts/build_spec2_tile_vectors.py",
        "seed": SEED,
        "q_ntt": list(Q_NTT),
        "montgomery_r": "2^32",
        "modes": {"2": "một phép nhân modulo", "4": "một butterfly"},
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for f in files:
        print(f"{f['file']:18s} {f['cases']:6d} ca  {f['sha256'][:16]}")


if __name__ == "__main__":
    main()
