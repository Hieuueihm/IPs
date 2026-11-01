"""Cycle schedule of FFT 32 bit (format 0) in the minimal core, design (A): one tile per complex butterfly.

Same memory, tiles, network and root-pack banks as the NTT core (model/ntt_core_sched.py). Format 0: element e (32 bit)
in cells 2e, 2e + 1, superbank sb(e) = bank(2e) >> 1. N components = N/2 complex points: real parts a[0:hn], imaginary
a[hn:N]. Every layer pairs elements at distance h (forward h = hn/2 .. 1, inverse 1 .. hn/2); butterfly b reads
A = (a[j], a[j + hn]) and B = (a[j + h], a[j + h + hn]), j = b with a 0 inserted at bit log2 h, root index
N / (2h) + j / (2h) (forward GM, inverse conj(GM)); spec 1.0, 01.4.

Tile of a butterfly: bank-indexed tile of the real pair (sb(A.re), sb(B.re)), the NTT rule over the hn real parts, so
the real pair reuses the NTT port sources; the imaginary pair sits hn elements further (the network gains those
sources). The layer table is the NTT one for logn - 1. All tiles read data in the same cycles (one butterfly per tile
per 3 cycles; the k-th butterflies of all tiles form a conflict-free set, the imaginary pair a shifted copy), so data
reads and writes never collide. Roots: one root per word ({wi, wr} in the two pack "children"), root k at bank k mod 4;
every bank has two read ports, tiles 0..7 use port a and 8..15 port b; reads are staggered by tile group
(t >> 2) mod 3. Checked conflict-free: one word per bank port per cycle.

Per butterfly, e = data read cycle (e = 3k from the layer start), c = e - 3 its address stage:
  e - 2 + g  read the root word, g = tile group 0, 1, 2; it waits in the network's root register ({wi, wr})
  e          read A.re (port x), B.re (port y)
  e + 1      read A.im, B.im
  e + 2      tile beat 1 (mode 5, spec 10): d0 = A.re, d1 = B.re, root = wr
  e + 3      tile beat 2: d0 = A.im, d1 = B.im, root = wi
             the tile makes p0, p1, p2 on its multiplier, T, and A +- T (or A + B, (A - B) * w) on its add/sub
  e + 11     beat 1 result (tile latency 9): write select of the real pair; RAM write e + 12
  e + 12     beat 2 result: write select of the imaginary pair; RAM write e + 13
Read -> write latency 14 (e .. e + 13). Inverse: the last layer's beats carry the scale flag, so the tile divides every
output by 2^(logn - 1) (div2e). Roots quantized from the 1.0 Q64.64 table (spec 1.0 01.3); inverse wi = Q(-wi); root
indices reach N/2 + N/4 - 1 = 767 at N = 1024. Barrier per layer: the next layer starts 3 * count + 12 cycles after this
one (the last write is at 3 * count + 10; rounded up so every layer starts on the same issue phase, as the RTL does).

Run: python model/fft_core_sched.py   (checks every format-0 golden case, writes study/results/fft_core_sched.md)
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / "model" / file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


sn = _load("structured_net", "structured_net.py")
plan = _load("fft_core_plan", "fft_core_plan.py")
TILES, PB = 16, 4
PHASE = [t // 6 for t in range(TILES)]
W = 32
LAT_RW = 14
RGRP = [(t >> 2) % 3 for t in range(TILES)]


def sb(e):
    return sn.bank(2 * e) >> 1


def layers(logn, inverse):
    hn = (1 << logn) // 2
    hs = []
    h = hn // 2
    while h >= 1:
        hs.append(h)
        h //= 2
    return hs[::-1] if inverse else hs


def bfly(b, h, hn):
    lo = b % h
    j = ((b - lo) << 1) | lo
    return j, j + h, j + hn, j + h + hn          # A.re, B.re, A.im, B.im


def layer_config(logn, h):
    """Affine enumeration: {tile: p_t}, kernel basis, butterflies per tile."""
    hn = (1 << logn) // 2
    nbf = hn // 2
    nb = nbf.bit_length() - 1
    tile = []
    for b in range(nbf):
        ar, br, ai, bi = bfly(b, h, hn)
        tile.append(sn.tile_of(sb(ar), sb(br)))
    lin = [tile[1 << k] ^ tile[0] for k in range(nb)]
    for b in range(nbf):
        v = tile[0]
        for k in range(nb):
            if b >> k & 1:
                v ^= lin[k]
        assert v == tile[b], (logn, h, b)
    kernel, seen = [], {}
    for k in range(nb):
        v, vec = lin[k], 1 << k
        while v and (v & -v) in seen:
            pv, pvec = seen[v & -v]
            v ^= pv
            vec ^= pvec
        if v:
            seen[v & -v] = (v, vec)
        else:
            kernel.append(vec)
    first = {}
    for b, t in enumerate(tile):
        first.setdefault(t, b)
    count = 1 << len(kernel)
    assert all(tile.count(t) == count for t in first)
    return first, kernel, count


def enum(p, kernel, k):
    i = p
    for j, v in enumerate(kernel):
        if k >> j & 1:
            i ^= v
    return i


def wrap(x):
    return plan.wrap(x, W)


def run(logn, inverse, data, gm, igm):
    """One command: returns (result, cycles first read .. last write + 1, latency, conflict counts)."""
    n = 1 << logn
    hn = n // 2
    mem = list(data)
    if logn < 2:
        return mem, 0, 0, (0, 0, 0)
    tab = igm if inverse else gm
    reads, writes, rroot = {}, {}, {}
    S = 0
    hs = layers(logn, inverse)
    for li, h in enumerate(hs):
        last = li == len(hs) - 1
        firsts, kernel, count = layer_config(logn, h)
        new = {}
        last_w = S
        for t, p in firsts.items():
            e0 = S
            for k in range(count):
                e = e0 + 3 * k
                ar, br, ai, bi = bfly(enum(p, kernel, k), h, hn)
                for cyc, s in ((e, sb(ar)), (e, sb(br)), (e + 1, sb(ai)), (e + 1, sb(bi))):
                    reads.setdefault(cyc, []).append(s)
                r = n // (2 * h) + ar // (2 * h)
                rroot.setdefault(e - 2 + RGRP[t], {}).setdefault((r % PB, t >= 8), set()).add(r)
                wr, wi = tab[r]
                xr, xi, yr, yi = mem[ar], mem[ai], mem[br], mem[bi]
                if inverse:
                    o1, o2 = wrap(xr - yr), wrap(xi - yi)
                else:
                    o1, o2 = yr, yi
                p0, p1 = plan.mul(o1, wr, W), plan.mul(o2, wi, W)
                p2 = plan.mul(wrap(o1 + o2), wrap(wr + wi), W)
                tr, ti = wrap(p0 - p1), wrap(wrap(p2 - p0) - p1)
                if inverse:
                    z = [wrap(xr + yr), tr, wrap(xi + yi), ti]
                else:
                    z = [wrap(xr + tr), wrap(xr - tr), wrap(xi + ti), wrap(xi - ti)]
                if inverse and last and logn - 1 > 0:
                    s_ = logn - 1
                    z = [wrap(v + (1 << (s_ - 1))) >> s_ for v in z]
                new[ar], new[br], new[ai], new[bi] = z
                for cyc, s in ((e + 12, sb(ar)), (e + 12, sb(br)), (e + 13, sb(ai)), (e + 13, sb(bi))):
                    writes.setdefault(cyc, []).append(s)
                last_w = max(last_w, e + 13)
        for c, v in new.items():
            mem[c] = v
        S = S + 3 * count + 12
    rc = sum(1 for v in reads.values() if len(v) != len(set(v)))
    wc = sum(1 for v in writes.values() if len(v) != len(set(v)))
    pc = sum(max(len(x) for x in b.values()) - 1 for b in rroot.values())
    return mem, last_w + 1, LAT_RW, (rc, wc, pc)


def main():
    gm, igm = plan.roots(W), plan.roots_inv(W)
    lines = ["# Lịch chu kỳ FFT 32 bit trong lõi (cách A)\n",
             "Mô hình: [model/fft_core_sched.py](../../model/fft_core_sched.py). Rào chắn mỗi tầng. Chu kỳ = từ lần đọc đầu "
             "tới lần ghi cuối, cộng 1.\n",
             "| N | Chiều | Khớp ca vàng | Chu kỳ | Chu kỳ xung đột đọc / ghi | Chu kỳ thêm do bank root |",
             "|---:|---|---|---:|---:|---:|"]
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] not in (0, 1) or c["fmt"] != 0:
            continue
        a = [wrap(int(x, 16)) for x in d["a"][0]]
        e = [wrap(int(x, 16)) for x in d["expected"][0]]
        res, cyc, lat, (rc, wc, pc) = run(c["logn"], c["op"] == 1, a, gm, igm)
        ok = res == e
        assert ok, c
        lines.append(f"| {1 << c['logn']} | {'ngược' if c['op'] else 'xuôi'} | có | {cyc} | {rc} / {wc} | {pc} |")
    (ROOT / "study" / "results" / "fft_core_sched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
