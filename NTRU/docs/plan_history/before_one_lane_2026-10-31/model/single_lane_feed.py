"""Memory and root supply for the single-lane tile (spec 2.0, 10 since 31/10/2026).

Each of the 16 tiles takes one butterfly per cycle at both lane widths (v1 design: lane 16 on the
multiplier array, lane 32 dedicated Montgomery). Every layer of an NTT is one pass; a pass may start
only after the previous pass of the same polynomial has written back (barrier per polynomial).

Data memory (spec 03 section 1, unchanged): 64 banks of 16-bit cells, one read and one write per bank
per cycle, bank(k) = (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30).
  lane 16, format 3: coefficient i of polynomial j at cell k = j*N + i.
  lane 32, format 4: cells 2(j*N + i), 2(j*N + i) + 1, one "superbank" bank(2c) >> 1 (32 superbanks).
A butterfly reads 2 coefficients and later writes the same 2. The results of one issue cycle are
written together E cycles later, so a group that reads conflict-free also writes conflict-free.

Root memory: the three-root packs of spec 03 section 4 are kept, [GM[g], GM[2g], GM[2g+1]] at position
b + g - 1 of the slot. A single-layer butterfly with root index r reads pack r >> 1 (r >= 2; one pack
gives both children) or pack 1 (r = 1). Pack bank = position mod P; one pack per bank per cycle.
The same layout is assumed for the inverse tables and for the 16-bit root ROMs.

Network assumed: any data superbank (or bank) to any tile operand port, and any root bank to any tile.
Its LUT cost is not modeled here.

Scheduling: list scheduling in natural butterfly order; a cycle takes up to 16 butterflies whose data
banks are all distinct, whose packs fit the root banks, and (multi-polynomial commands) at most
16 / jobs butterflies of each polynomial, because each tile holds one modulus. When both operands of a
butterfly sit in one bank (format 4, N = 1024, distance 512: the bank function ignores address bit 10),
x is read one cycle early and held at the tile ("stagger"); without it that butterfly takes two cycles
alone.

Run: python model/single_lane_feed.py   (writes study/results/single_lane_feed.md)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TILES = 16
LAT = {16: 13 + 2, 32: 15 + 2}       # acceptance RTL latency of the v1 design + RAM read and write


def bank(k):
    return (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30)


def data_unit(lane, n, j, i):
    """Bank (lane 16) or superbank (lane 32) that holds coefficient i of polynomial j."""
    c = j * n + i
    return bank(c) if lane == 16 else bank(2 * c) >> 1


def layer_jobs(logn, layer, inverse):
    """Butterflies of one layer: (index of x, index of y, root index)."""
    n = 1 << logn
    out = []
    if not inverse:
        m, t = 1 << layer, n >> layer
        ht = t >> 1
        for u in range(m):
            for v in range(ht):
                j = u * t + v
                out.append((j, j + ht, m + u))
    else:
        hm, t = n >> (layer + 1), 1 << layer
        for u in range(hm):
            for v in range(t):
                j = u * 2 * t + v
                out.append((j, j + t, hm + u))
    return out


def pack_of(r):
    return 1 if r == 1 else r >> 1


def schedule(lane, logn, layer, inverse, bases, pbanks, stagger=True):
    """Issue cycles of one layer for len(bases) polynomials (one base per polynomial's root packs).

    List scheduling in natural butterfly order: each butterfly goes to the earliest cycle with a free
    tile (and a free tile of its polynomial), free data banks and a free root bank (or the same pack).
    stagger = True: when both operands sit in one bank, x is read one cycle before y and held at the
    tile; otherwise such a butterfly reads in two cycles with nothing else issued.
    """
    n, jobs = 1 << logn, len(bases)
    cap = TILES // jobs
    used, tiles, per_poly, packs = {}, {}, {}, {}
    last, low = -1, 0
    for p in range(jobs):
        for (x, y, r) in layer_jobs(logn, layer, inverse):
            ux, uy = data_unit(lane, n, p, x), data_unit(lane, n, p, y)
            pos = bases[p] + pack_of(r) - 1
            pb = pos % pbanks
            c = low
            while True:
                if tiles.get(c, 0) < TILES and per_poly.get((c, p), 0) < cap                         and packs.get((c, pb), pos) == pos:
                    if ux != uy:
                        if ux not in used.get(c, ()) and uy not in used.get(c, ()):
                            used.setdefault(c, set()).update((ux, uy))
                            break
                    elif stagger and c >= 1:
                        if ux not in used.get(c, ()) and ux not in used.get(c - 1, ()):
                            used.setdefault(c, set()).add(ux)
                            used.setdefault(c - 1, set()).add(ux)
                            break
                    elif not stagger and tiles.get(c, 0) == 0 and tiles.get(c + 1, 0) == 0                             and not used.get(c) and not used.get(c + 1):
                        used.setdefault(c, set()).add(ux)
                        used.setdefault(c + 1, set()).add(ux)
                        tiles[c + 1] = TILES
                        break
                c += 1
            tiles[c] = tiles.get(c, 0) + 1
            per_poly[(c, p)] = per_poly.get((c, p), 0) + 1
            packs[(c, pb)] = pos
            last = max(last, c + (1 if (ux == uy and not stagger) else 0))
            while tiles.get(low, 0) >= TILES:
                low += 1
    return last + 1


def ntt_cycles(lane, logn, inverse, jobs, pbanks, bases=None, stagger=True):
    """(issue cycles of all layers, time with a barrier per layer and polynomial)."""
    if bases is None:
        g = max(1, (1 << logn) // 2 - 1)
        bases = [p * g for p in range(jobs)]
    issue, time = 0, 0
    for layer in range(logn):
        f = schedule(lane, logn, layer, inverse, bases, pbanks, stagger)
        issue += f
        if jobs == 2 and logn >= 6:
            # two contexts: one polynomial's pass overlaps the other's latency (architecture section 4)
            f1 = schedule(lane, logn, layer, inverse, bases[:1], pbanks, stagger)
            time += max(f, f1 + LAT[lane])          # f: both polynomials scheduled together
        else:
            time += f + LAT[lane]
    return issue, time


def main():
    out = []
    say = lambda s="": (print(s), out.append(s))
    say("# Cấp dữ liệu và root cho tile một làn (16 butterfly/chu kỳ)\n")
    say("Mô hình: [model/single_lane_feed.py](../../model/single_lane_feed.py). Bộ nhớ dữ liệu như spec 03 mục 1; gói root "
        "ba phần tử như spec 03 mục 4, đọc root con từ gói của nút cha; P = số bank gói root. Xếp tham lam theo thứ tự "
        "tự nhiên, có đọc lệch một chu kỳ khi hai toán hạng cùng bank. Độ trễ mỗi lượt: lane 16 bit 15, lane 32 bit 17 "
        "(RTL nghiệm thu + 2 chu kỳ RAM). Mạng bank → tile giả định nối đầy đủ; chi phí LUT của nó chưa mô hình.\n")
    say("Tốc độ hiệu dụng = tổng butterfly / tổng chu kỳ phát; lý tưởng là 16 (N nhỏ bị giới hạn bởi số butterfly mỗi "
        "tầng, N/2).\n")
    for lane in (16, 32):
        say(f"## Lane {lane} bit, một đa thức\n")
        say("| N | Chiều | P = 4: chu kỳ phát / tốc độ | P = 8: chu kỳ phát / tốc độ | P = 8: thời gian NTT |")
        say("|---:|---|---:|---:|---:|")
        for logn in range(1, 11):
            n = 1 << logn
            for inverse in (False, True):
                bf = logn * n // 2
                i4, _ = ntt_cycles(lane, logn, inverse, 1, 4)
                i8, t8 = ntt_cycles(lane, logn, inverse, 1, 8)
                say(f"| {n} | {'ngược' if inverse else 'xuôi'} | {i4} / {bf / i4:.2f} | {i8} / {bf / i8:.2f} | {t8} |")
        say("")
    i0, t0 = ntt_cycles(32, 10, False, 1, 8, stagger=False)
    say(f"Không đọc lệch, lane 32 bit N = 1024 xuôi: {i0} chu kỳ phát, thời gian {t0}. Ở tầng khoảng cách 512 cả hai "
        "toán hạng của mọi butterfly nằm cùng một siêu bank, vì hàm bank bỏ qua bit 10 của địa chỉ.\n")
    say("## Lane 32 bit, nhiều đa thức trong một lệnh\n")
    say("N < 64: min(8, 64/N) đa thức, mỗi đa thức một prime (khe riêng, vùng gói riêng, cách nhau G gói), "
        "16/jobs tile mỗi đa thức. N ≥ 64: hai đa thức cùng prime, hai context.\n")
    say("| N | jobs | Chiều | P = 8: chu kỳ phát / tốc độ | Thời gian lệnh | Mỗi đa thức |")
    say("|---:|---:|---|---:|---:|---:|")
    for logn in range(1, 11):
        n = 1 << logn
        jobs = min(8, 64 // n) if n < 64 else 2
        for inverse in (False, True):
            bf = jobs * logn * n // 2
            if n >= 64:
                g = max(1, n // 2 - 1)
                i8, t8 = ntt_cycles(32, logn, inverse, 2, 8, bases=[0, 0])
            else:
                i8, t8 = ntt_cycles(32, logn, inverse, jobs, 8)
            say(f"| {n} | {jobs} | {'ngược' if inverse else 'xuôi'} | {i8} / {bf / i8:.2f} | {t8} | {t8 / jobs:.1f} |")
    say("")
    (ROOT / "study" / "results" / "single_lane_feed.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
