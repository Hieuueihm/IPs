"""Replay the spec 2.0 tile vectors through a leaf-level model of the tile (on-array reduction).

Independent of the generator: products are summed from 16x16 leaf products, Montgomery is the three-pass form of
10_hop_dong_tile.md 5.1 (u = T_high + (m*q)_high + [T_low != 0], one conditional subtract), halving is
(s + (s odd ? q : 0)) >> 1. NTT mode: R = 2^32 for every q (one 32-bit lane); packed NTT mode: each 16-bit lane on one
leaf, R = 2^16. Also checks the manifest hashes and that every CT product agrees with model/ntrugen_mp31.mont_hw.
(The raw and FFT 32-bit product files went with their tile modes on 02/11/2026; the FFT butterfly files are checked
against model/fft_core_plan.py and model/fft_wide_tile.py by their own scripts.)

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


def mont16_leaf(a, b, q, qinv):
    """One 16x16 leaf, three passes: T = a b, m = T_lo q' mod 2^16, m q; u = T_hi + (m q)_hi + [T_lo != 0]."""
    t = a * b
    m = ((t & 0xFFFF) * (qinv & 0xFFFF)) & 0xFFFF
    mq = m * q
    u = (t >> 16) + (mq >> 16) + ((t & 0xFFFF) != 0)
    assert u < 2 * q
    return u - q if u >= q else u


def ntt_leaf(q, qinv, direction, halve, d0, d1, r0, mont_fn=mont_leaf):
    def mont(x, w):
        return mont_fn(x, w, q, qinv)

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
    agree32 = 0
    for q, qinv, direction, halve, d0, d1, r0, *z in rows("ntt.txt"):
        assert ntt_leaf(q, qinv, direction, halve, d0, d1, r0) == z, (q, direction)
        if direction == 0:
            assert (z[0] - d0) % q == mp31.mont_hw(d1, r0, q, qinv)
            agree32 += 1
        n += 1
    n16 = 0
    for q, qinv, direction, halve, pair, x, y, wa, wb, zx, zy in rows("ntt16.txt"):
        xl, xh, yl, yh = x & 0xFFFF, x >> 16, y & 0xFFFF, y >> 16
        la, lb = ((xl, yl), (xh, yh)) if pair == 0 else ((xl, xh), (yl, yh))
        oa = ntt_leaf(q, qinv, direction, halve, *la, wa, mont16_leaf)
        ob = ntt_leaf(q, qinv, direction, halve, *lb, wb, mont16_leaf)
        if pair == 0:
            want = [oa[0] | ob[0] << 16, oa[1] | ob[1] << 16]
        else:
            want = [oa[0] | oa[1] << 16, ob[0] | ob[1] << 16]
        assert want == [zx, zy], (q, direction, pair)
        n16 += 1
    print(f"PASS: {n} ca NTT khớp mô hình dạng tích 16×16, {n16} ca NTT hai hệ số mỗi từ khớp mô hình một lá mỗi làn; "
          f"hash manifest khớp; {agree32} ca CT khớp thêm model/ntrugen_mp31.mont_hw.")


if __name__ == "__main__":
    main()
