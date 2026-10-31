"""Replay the spec 2.0 tile vectors through a leaf-level model of the tile (on-array reduction).

Independent of the generator: products are summed from 16x16 leaf products with signed upper halves,
FFT 32 bit rounding is P[47:16] + P[15], Montgomery is the three-pass form of 10_hop_dong_tile.md 5.1
(u = T_high + (m*q)_high + [T_low != 0], one conditional subtract), halving is (s + (s odd ? q : 0)) >> 1.
R = 2^32 for every q (one 32-bit lane). Also checks the manifest hashes and that every modmul case agrees
with model/ntrugen_mp31.mont_hw.

Run: python scripts/check_spec2_tile_vectors.py
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TILE = ROOT / "spec" / "FlexTransform" / "2.0" / "assets" / "tile"

_spec = importlib.util.spec_from_file_location("mp31", ROOT / "model" / "ntrugen_mp31.py")
mp31 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mp31)


def halves(x, signed):
    lo, hi = x & 0xFFFF, x >> 16
    if signed and hi >> 15:
        hi -= 1 << 16
    return lo, hi


def leaf_product32(a, b, sa, sb):
    """4 leaves: lo*lo, lo*hi, hi*lo, hi*hi; only the upper halves carry the sign."""
    al, ah = halves(a, sa)
    bl, bh = halves(b, sb)
    return al * bl + ((al * bh + ah * bl) << 16) + ((ah * bh) << 32)


def mont_leaf(a, b, q, qinv):
    rb = 32
    mask = (1 << rb) - 1
    t = leaf_product32(a, b, 0, 0)                                   # 4 leaves
    tl, th = halves(t & mask, 0)
    ql, qh = halves(qinv, 0)
    m = (tl * ql + (((tl * qh + th * ql) & 0xFFFF) << 16)) & mask      # 3 leaves, low half only
    mq = leaf_product32(m, q, 0, 0)                                  # 4 leaves
    u = (t >> rb) + (mq >> rb) + ((t & mask) != 0)
    assert u < 2 * q
    return u - q if u >= q else u


def ntt_leaf(q, qinv, mode, direction, halve, d0, d1, r0):
    def mont(x, w):
        return mont_leaf(x, w, q, qinv)

    def add(x, y):
        s = x + y
        return s - q if s >= q else s

    def sub(x, y):
        s = x - y
        return s + q if s < 0 else s

    def ct(x, y, w):
        t = mont(y, w)
        return add(x, t), sub(x, t)

    def gs(x, y, w):
        s = add(x, y)
        if halve:
            s = (s + (q if s & 1 else 0)) >> 1
        return s, mont(sub(x, y), w)

    if mode == 2:
        return [mont(d0, r0), 0]
    return list(ct(d0, d1, r0) if direction == 0 else gs(d0, d1, r0))


def rows(name):
    for line in (TILE / name).read_text(encoding="ascii").splitlines():
        if line and not line.startswith("#"):
            yield [int(x, 16) for x in line.split()]


def main():
    manifest = json.loads((TILE / "manifest.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        assert hashlib.sha256((TILE / f["file"]).read_bytes()).hexdigest() == f["sha256"], f["file"]
        assert sum(1 for _ in rows(f["file"])) == f["cases"], f["file"]

    n = 0
    for sa, sb, a, b, p in rows("raw32.txt"):
        assert leaf_product32(a, b, sa, sb) & ((1 << 65) - 1) == p
        n += 1
    for fl, a, b, z in rows("fft32.txt"):
        pp = leaf_product32(a, b, 1, 1)
        assert (((pp >> 16) + (0 if fl else (pp >> 15) & 1)) & 0xFFFFFFFF) == z
        n += 1
    agree32 = 0
    for q, qinv, mode, direction, halve, d0, d1, r0, *z in rows("ntt.txt"):
        assert ntt_leaf(q, qinv, mode, direction, halve, d0, d1, r0) == z, (q, mode, direction)
        if mode == 2:
            assert mp31.mont_hw(d0, r0, q, qinv) == z[0]
            agree32 += 1
        n += 1
    print(f"PASS: {n} ca khớp mô hình dạng tích 16×16; hash manifest khớp; "
          f"{agree32} ca nhân modulo 32 bit khớp thêm model/ntrugen_mp31.mont_hw.")


if __name__ == "__main__":
    main()
