"""Cycle schedule of the minimal NTT core (one polynomial, opcodes 0x5 / 0x6, profiles 0, 1, 2).

This is the schedule the RTL (hdl/core_ntt/) implements; the generator scripts/gen_ntt_core.py takes its tables
from here. Same structure as the measured blocks:
  - memory region A: 64 banks x 128 rows x 16 bit, bank(k) = (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30),
    format 4: coefficient c in cells 2c (low half) and 2c + 1 (high half), superbank s = bank(2c) >> 1, row c >> 5;
  - 16 on-array tiles (hdl/tile/tile_thu.sv, TREN_MANG = 1); tile t accepts in cycles A with (PHASE[t] + A) mod 3 == 0,
    PHASE[t] = t // 6 (counted from reset; every tile sees the same en);
  - bank-indexed tile of a butterfly (model/structured_net.py tile_of);
  - 4 root-pack banks, pack g at position g - 1, bank (g - 1) mod 4, row (g - 1) div 4; root 1 from a register.

Per layer (logn, h) the tile map i -> tile is affine over GF(2) (checked here for every layer). Tile t takes the
butterflies i = p_t xor K(k), k = 0, 1, ...: p_t is the smallest i of the tile, K(k) xors the kernel basis vectors
selected by the bits of k. All tiles at the same k then read a shifted copy of the k = 0 superbank set, which is
conflict-free, so reads never collide.

Pipeline (cycle numbers relative to the accept cycle A of the butterfly at its tile):
  A - 2  read x and y rows, read the root pack            (x at A - 3 when x and y share a superbank: distance 512)
  A - 1  network selects (x select at A - 2 and hold_x at A - 1 when they share a superbank), root select
  A      tile accepts (req_valid)
  A + 20 tile result (core tiles use IN_REG = 1 since 01/11/2026; 19 before); write select for x (and y)
  A + 20 RAM write of x (and y); when they share a superbank, y's write select at A + 20 and its write at A + 21
A layer starts reading at S; the next layer's first read is one cycle after the last write (barrier per layer).

INTT: every layer halves the sum branch (tile cfg_halve = 1) and the inverse roots are stored times 2^-1 mod q,
so the result already carries 2^-L (L = number of layers): no separate normalisation pass. Same results as 1.0,
which multiplies by R * 2^-L at the end.

Run: python model/ntt_core_sched.py   (checks every profile / logn / direction against the golden vectors, writes
study/results/ntt_core_sched.md)
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("structured_net", ROOT / "model" / "structured_net.py")
sn = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sn)

TILES, PB, TILE_LAT = 16, 4, 20
PHASE = [t // 6 for t in range(TILES)]
R32 = 1 << 32
PROFILES = {0: (12289, range(3, 11)), 1: (3329, range(3, 9)), 2: (8380417, range(8, 9))}


def bank(k):
    return sn.bank(k)


def superbank(c):
    return bank(2 * c) >> 1


def min_stride(q, logn):
    return 2 if (q == 3329 and logn == 8) else 1


def layers(q, logn, inverse):
    """Distances h of the layers in execution order."""
    n = 1 << logn
    hs = []
    h = n // 2
    while h >= min_stride(q, logn):
        hs.append(h)
        h //= 2
    return hs[::-1] if inverse else hs


def pair(i, h):
    lo = i % h
    c = ((i - lo) << 1) | lo
    return c, c + h


def layer_config(logn, h):
    """Affine enumeration of one layer: {tile: (p_t, count)}, kernel basis, same-superbank flag."""
    n = 1 << logn
    nb = logn - 1
    tile = []
    for i in range(n // 2):
        cx, cy = pair(i, h)
        tile.append(sn.tile_of(superbank(cx), superbank(cy)))
    lin = [tile[1 << b] ^ tile[0] for b in range(nb)]
    for i in range(n // 2):                                    # affine check
        v = tile[0]
        for b in range(nb):
            if i >> b & 1:
                v ^= lin[b]
        assert v == tile[i], (logn, h, i)
    kernel = []                                                # basis of {v : linear part = 0}, row-reduced
    seen = {}
    for b in range(nb):
        v, vec = lin[b], 1 << b
        while v and (v & -v) in seen:
            pv, pvec = seen[v & -v]
            v ^= pv
            vec ^= pvec
        if v:
            seen[v & -v] = (v, vec)
        else:
            kernel.append(vec)
    first = {}
    for i, t in enumerate(tile):
        first.setdefault(t, i)
    count = 1 << len(kernel)
    assert all(tile.count(t) == count for t in first)
    same = superbank(pair(0, h)[0]) == superbank(pair(0, h)[1])
    return {t: first[t] for t in first}, kernel, count, same


def enum(p, kernel, k):
    i = p
    for j, v in enumerate(kernel):
        if k >> j & 1:
            i ^= v
    return i


def root_index(n, h, c):
    return n // (2 * h) + c // (2 * h)


def mont32(a, b, q):
    return a * b * pow(R32, -1, q) % q


class Tables:
    """Root tables of profiles 0, 1, 2 as the core stores them (R = 2^32; inverse times 2^-1)."""

    def __init__(self):
        one = ROOT / "spec" / "FlexTransform" / "1.0" / "assets"
        two = ROOT / "spec" / "FlexTransform" / "2.0" / "assets"
        self.gm, self.igm = {}, {}
        for q, name, base in ((12289, "ntt_q12289", one), (3329, "ntt_q3329", one), (8380417, "ntt_q8380417", two)):
            f = [int(x, 16) for x in (base / f"{name}_forward.mem").read_text().split()]
            g = [int(x, 16) for x in (base / f"{name}_inverse.mem").read_text().split()]
            if q != 8380417:                                   # 1.0 tables carry R = 2^16
                f = [w * (1 << 16) % q for w in f]
                g = [w * (1 << 16) % q for w in g]
            inv2 = pow(2, -1, q)
            self.gm[q] = f
            self.igm[q] = [w * inv2 % q for w in g]


def run(q, logn, inverse, data, tabs, start=0):
    """Execute one command; returns (result, cycles from first read to last write + 1, stats)."""
    n = 1 << logn
    mem = list(data)
    roots = tabs.igm[q] if inverse else tabs.gm[q]
    reads, writes, packs = {}, {}, {}
    S = start
    issued = 0
    for h in layers(q, logn, inverse):
        firsts, kernel, count, same = layer_config(logn, h)
        new = {}
        last_w = S
        for t, p in firsts.items():
            a0 = S + (3 if same else 2)
            while (PHASE[t] + a0) % 3:
                a0 += 1
            for k in range(count):
                A = a0 + 3 * k
                i = enum(p, kernel, k)
                cx, cy = pair(i, h)
                sx, sy = superbank(cx), superbank(cy)
                rx = A - 3 if same else A - 2
                for cyc, s in ((rx, sx), (A - 2, sy)):
                    reads.setdefault(cyc, []).append(s)
                r = root_index(n, h, cx)
                if r >= 2:
                    pos = (r >> 1) - 1
                    packs.setdefault(A - 2, {}).setdefault(pos % PB, set()).add(pos)
                w = roots[r]
                x, y = mem[cx], mem[cy]
                if inverse:
                    s_, d = (x + y) % q, (x - y) % q
                    zx, zy = (s_ + (q if s_ & 1 else 0)) >> 1, mont32(d, w, q)
                else:
                    tt = mont32(y, w, q)
                    zx, zy = (x + tt) % q, (x - tt) % q
                new[cx], new[cy] = zx, zy
                wx = A + TILE_LAT + 1
                wy = wx + 1 if same else wx
                for cyc, s in ((wx, sx), (wy, sy)):
                    writes.setdefault(cyc, []).append(s)
                last_w = max(last_w, wy)
                issued += 1
        for c, v in new.items():
            mem[c] = v
        S = last_w + 1
    for cyc, v in list(reads.items()) + list(writes.items()):
        assert len(v) == len(set(v)), ("bank conflict", q, logn, inverse, cyc)
    pack_extra = sum(max(len(x) for x in b.values()) - 1 for b in packs.values())
    assert issued == len(layers(q, logn, inverse)) * n // 2
    return mem, S - start, pack_extra


def golden():
    """(profile, logn, op) -> list of (input, expected) from the 1.0 fixtures and the 2.0 kernel assets."""
    out = {}
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] in (5, 6) and c["jobs"] == 1 and c["profile"] in (0, 1):
            out.setdefault((c["profile"], c["logn"], c["op"]), []).append(
                ([int(x, 16) for x in d["a"][0]], [int(x, 16) for x in d["expected"][0]]))
    for line in (ROOT / "spec" / "FlexTransform" / "2.0" / "assets" / "kernel" / "ntt_q8380417.jsonl").read_text().splitlines():
        d = json.loads(line)
        if d["op"] in ("NTT", "INTT") and d["jobs"] == 1:
            out.setdefault((2, 8, 5 if d["op"] == "NTT" else 6), []).append(
                ([int(x, 16) for x in d["input"][0]], [int(x, 16) for x in d["expected"][0]]))
    return out


def main():
    tabs = Tables()
    gold = golden()
    lines = ["# Lịch chu kỳ của lõi NTT tối thiểu\n",
             "Mô hình: [model/ntt_core_sched.py](../../model/ntt_core_sched.py). Một đa thức, 16 tile trên mảng lệch pha "
             "(t / 6), mạng gán theo bank, 4 bank gói root, rào chắn mỗi tầng. Chu kỳ = từ lần đọc đầu tới lần ghi cuối, "
             "cộng 1. Mô hình giả thuyết 4 (khóa lần 6) = tổng các tầng của 3 × chu kỳ phát (single_lane_feed) + 19 + 2.\n",
             "| Profile | q | N | Chiều | Ca vàng | Khớp | Chu kỳ | Mô hình giả thuyết 4 | Chu kỳ thêm do bank gói |",
             "|---:|---:|---:|---|---:|---|---:|---:|---:|"]
    feed_spec = importlib.util.spec_from_file_location("feed", ROOT / "model" / "single_lane_feed.py")
    feed = importlib.util.module_from_spec(feed_spec)
    feed_spec.loader.exec_module(feed)
    total_ok = 0
    for prof, (q, lns) in PROFILES.items():
        for logn in lns:
            for op in (5, 6):
                cases = gold.get((prof, logn, op), [])
                ok = True
                cyc = extra = None
                for a, e in cases:
                    res, cyc, extra = run(q, logn, op == 6, a, tabs)
                    ok &= res == e
                assert cases and ok, (prof, logn, op)
                total_ok += len(cases)
                g = max(1, (1 << logn) // 2 - 1)
                model = 0
                for layer in range(len(layers(q, logn, op == 6))):
                    f = feed.schedule(logn, layer, op == 6, [0], 8)
                    model += 3 * f + 19 + 2
                lines.append(f"| {prof} | {q} | {1 << logn} | {'ngược' if op == 6 else 'xuôi'} | {len(cases)} | "
                             f"{'có' if ok else 'KHÔNG'} | {cyc} | {model} | {extra} |")
    lines.append(f"\nMọi {total_ok} ca vàng khớp; không có xung đột bank dữ liệu (đọc, ghi) ở chu kỳ nào.")
    (ROOT / "study" / "results" / "ntt_core_sched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
