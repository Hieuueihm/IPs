"""Tile assignment and read schedule of FFT 64 / 128 bit (formats 1, 2) in the minimal core (planning model, before RTL).

Format f = 1 / 2: element e is L = 2 / 4 limbs of 32 bit; limb k sits in cells 2(L e + k), 2(L e + k) + 1, i.e. it is the
format-0 element L e + k ("virtual element"). Its superbank is sb(L e) | k: the limbs of an element fill L neighbouring
superbanks, sb(L e) has its low log2 L bits 0 ("base superbank").

The limb-k pairs of a wide layer (distance h over N elements) are exactly the format-0 pairs of a layer with distance L h
over L N virtual elements, and the format-0 rule tile_of(sb(x), sb(y)) sends the limb-k pair of butterfly b to tile
T(b) | k, T(b) = tile_of(sb(L A.re), sb(L B.re)) with low log2 L bits 0. So the L tiles T(b) .. T(b) + L - 1 form a block:
tile T(b) | k reads limb k of the butterfly through its own format-0 network sources and passes it to the block's tile
that runs the butterfly (a 4-input choice in front of each tile, the same for the results on the way back).

Schedule: every block takes its m-th butterfly (affine enumeration, as the layer tables) at cycle m Q; the butterfly runs
on block tile m mod L. Limb k of the real parts is read at m Q + k by block tile k, of the imaginary parts at m Q + L + k.
All blocks are in step, so at any cycle all reads are limb k of the m-th butterflies (one k, real or imaginary): they
never collide when the m-th butterflies of the blocks use different base superbanks, which this model checks for every
layer. Q = 6 (64 bit: 2 tiles per block, a tile every 12 cycles = its own rate) or 12 (128 bit: 4 tiles, a tile every
48 cycles, its own rate is 45).

It also counts the network sources this adds to the format-0 / NTT lists (study/results/structured_net.json) and the
cycles of N = 1024 against hypothesis 3 (locked, lần 7).

Run: python model/fft_wide_sched.py   (writes study/results/fft_wide_sched.md)
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
fs = _load("fft_core_sched", "fft_core_sched.py")
TILES = 16
Q = {2: 6, 4: 12}
H3 = {"fwd": {64: 2300, 128: 8500}, "inv": {64: 2530, 128: 9350}}


def sb(v):
    """Superbank of format-0 (virtual) element v."""
    return sn.bank(2 * v) >> 1


def layer_blocks(logn, h, L):
    """Affine enumeration over blocks: {block: first butterfly}, kernel basis, butterflies per block."""
    hn = (1 << logn) // 2
    nbf = hn // 2
    nb = nbf.bit_length() - 1
    lb = L.bit_length() - 1
    blk = []
    for b in range(nbf):
        ar, br, ai, bi = fs.bfly(b, h, hn)
        t = sn.tile_of(sb(L * ar), sb(L * br))
        assert t & (L - 1) == 0
        blk.append(t >> lb)
    lin = [blk[1 << k] ^ blk[0] for k in range(nb)]
    for b in range(nbf):
        v = blk[0]
        for k in range(nb):
            if b >> k & 1:
                v ^= lin[k]
        assert v == blk[b], (logn, h, L, b)
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
    for b, t in enumerate(blk):
        first.setdefault(t, b)
    count = 1 << len(kernel)
    assert all(blk.count(t) == count for t in first)
    return first, kernel, count


def check(L):
    """Conflicts and port sources over every logn and layer of format log2 L."""
    lb = L.bit_length() - 1
    ports = {(t, op): set() for t in range(TILES) for op in "xy"}
    wbank = {s: set() for s in range(32)}
    conflicts = 0
    layers_seen = 0
    for logn in range(2, 11):
        hn = (1 << logn) // 2
        for h in fs.layers(logn, False):
            first, kernel, count = layer_blocks(logn, h, L)
            layers_seen += 1
            for m in range(count):
                re, im = [], []
                for blk, p in first.items():
                    ar, br, ai, bi = fs.bfly(fs.enum(p, kernel, m), h, hn)
                    re += [sb(L * ar), sb(L * br)]
                    im += [sb(L * ai), sb(L * bi)]
                    for k in range(L):
                        t = (blk << lb) | k
                        for op, es in (("x", (ar, ai)), ("y", (br, bi))):
                            for e in es:
                                ports[(t, op)].add(sb(L * e) | k)
                                wbank[sb(L * e) | k].add((t, op))
                conflicts += (len(re) != len(set(re))) + (len(im) != len(set(im)))
    return ports, wbank, conflicts, layers_seen


# tile mode 5 at 64 / 128 bit (hdl/tile/tile_thu.sv with IN_REG = 1 as in the core, measured with
# sim/tile_thu/tb_wide_timing.sv -DTL_IN_REG=1, the same both directions, scaled or not): cycle of result beat j after the
# butterfly's first beat (beats 0 .. L-1 real limbs, L .. 2L-1 imaginary limbs), for a tile that gets a butterfly every
# L * Q cycles (no queueing in its 4 buffers). Spec 10, 4.8 table (IN_REG = 0) plus 1.
OUT = {2: [24, 25, 28, 29], 4: [45, 48, 50, 51, 60, 63, 65, 66]}
# RTL timing, in cycles after the block's issue cycle g (hdl/core_ntt/ntt_core.sv): the butterfly index is registered at g,
# so every address stage lies in g + 1 .. g + Q. D: data read cycle e = g + D of limb 0 of the real parts.
D = {2: 6 // 2, 4: 5}
# root read lead of each block (cycles before its data read of the same limb): the two blocks of a 4-tile group read
# the same limb together (roots of one group differ mod 4 or are equal, format-0 property); groups, and at 128 bit the
# two blocks of a ROM port, read in different cycles
RS = {2: [1, 1, -1, -1, 1, 1, -1, -1], 4: [-1, 3, -1, 3]}
BEAT = 3            # beat j at e + 3 + j: y read at e + k + 1, network register, x held one cycle
WR = 2              # x write select two cycles after the result (capture register, forwarding register), y one more


def wrapw(x, w):
    x &= (1 << w) - 1
    return x - (1 << w) if x >> (w - 1) else x


def mulw(a, b, w):
    f = w // 2
    return wrapw((a * b + (1 << (f - 1))) >> f, w)


def run(L, logn, inverse, data, tab):
    """One command, cycle by cycle as the RTL. Block b issues its m-th butterfly at g = S + m Q, e = g + D: x limb k of
    the real parts read at e + k, y at e + k + 1 (x held one cycle in the network), the imaginary parts from e + L; beat j
    reaches the tile at e + 3 + j; result beat j at e + 3 + OUT[j]; written x one cycle later (forwarding register), y
    two cycles later. Root limb k of block b: ROM read at e + k - RS[b] (bank r mod 4, row (r >> 2) L + k; port a for
    tiles 0..7, b for 8..15), in the reading tile's root register from two cycles later until its imaginary beat.
    Returns (result, cycles first read .. last RAM write + 1 (as the RTL testbench's cycles_a), conflicts read / write /
    root)."""
    w = 32 * L
    n = 1 << logn
    hn = n // 2
    mem = list(data)
    if logn < 2:
        return mem, 0, (0, 0, 0)
    lb = L.bit_length() - 1
    Qc = Q[L]
    reads, writes, roots, emit = {}, {}, {}, {}
    S = 0
    last_w = 0
    hs = fs.layers(logn, inverse)
    for li, h in enumerate(hs):
        last = li == len(hs) - 1
        first, kernel, count = layer_blocks(logn, h, L)
        new = {}
        last_sel = S
        for blk, p in first.items():
            s_ = RS[L][blk]
            for m in range(count):
                g = S + m * Qc
                e = g + D[L]
                ar, br, ai, bi = fs.bfly(fs.enum(p, kernel, m), h, hn)
                r = n // (2 * h) + ar // (2 * h)
                for k in range(L):
                    t = (blk << lb) | k
                    for row, (xa, ya) in enumerate(((ar, br), (ai, bi))):
                        cx, cy = e + row * L + k, e + row * L + k + 1
                        # every address stage (cycle before the read) inside g + 1 .. g + Q
                        assert g + 1 <= cx - 1 and cy - 1 <= g + Qc, (L, k, row)
                        reads.setdefault(cx, []).append(sb(L * xa) | k)
                        reads.setdefault(cy, []).append(sb(L * ya) | k)
                        j = row * L + k
                        out = e + BEAT + OUT[L][j]
                        emit.setdefault((blk, k), []).append(out)
                        assert len({v for v in emit[(blk, k)] if v == out}) == 1
                        writes.setdefault(out + WR, []).append(sb(L * xa) | k)
                        writes.setdefault(out + WR + 1, []).append(sb(L * ya) | k)
                        last_w = max(last_w, out + WR + 2)
                        last_sel = max(last_sel, out + WR + 1)      # y write select (RAM write one cycle later)
                    rr = e + k - s_                      # ROM read; its address stage rr - 1 inside g + 1 .. g + Q
                    assert g + 1 <= rr - 1 <= g + Qc
                    # root register: loaded at the end of rr + 1, used at the beats e + 3 + k and e + 3 + L + k; the next
                    # butterfly's load (end of rr + Q + 1) comes after the imaginary beat
                    assert rr + 2 <= e + BEAT + k and rr + Qc + 1 >= e + BEAT + L + k
                    roots.setdefault((rr, t >= 8, r % 4), set()).add((r >> 2) * L + k)
                wr, wi = tab[r]
                xr, xi, yr, yi = mem[ar], mem[ai], mem[br], mem[bi]
                o1, o2 = (wrapw(xr - yr, w), wrapw(xi - yi, w)) if inverse else (yr, yi)
                p0, p1 = mulw(o1, wr, w), mulw(o2, wi, w)
                p2 = mulw(wrapw(o1 + o2, w), wrapw(wr + wi, w), w)
                tr, ti = wrapw(p0 - p1, w), wrapw(wrapw(p2 - p0, w) - p1, w)
                if inverse:
                    z = [wrapw(xr + yr, w), tr, wrapw(xi + yi, w), ti]
                else:
                    z = [wrapw(xr + tr, w), wrapw(xr - tr, w), wrapw(xi + ti, w), wrapw(xi - ti, w)]
                if inverse and last:
                    s2 = logn - 1
                    z = [wrapw(v + (1 << (s2 - 1)), w) >> s2 for v in z]
                new[ar], new[br], new[ai], new[bi] = z
        for c, v in new.items():
            mem[c] = v
        S = last_sel + 2                # barrier on commits (as the RTL): registered written count, then the switch
    # a block's results for one limb index: one at a time, at least 2 cycles apart (forwarding register: captured at the
    # end of the result cycle, read by the x write the next cycle and the y write the cycle after)
    for v in emit.values():
        v = sorted(v)
        assert all(b - a >= 2 for a, b in zip(v, v[1:])), v[:10]
    rc = sum(1 for v in reads.values() if len(v) != len(set(v)))
    wc = sum(1 for v in writes.values() if len(v) != len(set(v)))
    pc = sum(1 for v in roots.values() if len(v) > 1)
    return mem, last_w + 1 - D[L], (rc, wc, pc)


def delta(L, count):
    """Cycles from a layer's first issue to the next layer's: the last RAM write (y) of the layer is at
    (count - 1) Q + D + BEAT + OUT[-1] + WR + 2; the next layer's first read D cycles after its issue comes one later."""
    return (count - 1) * Q[L] + BEAT + OUT[L][-1] + WR + 3


def cycles(L, logn, lat=None):
    total = 0
    hs = fs.layers(logn, False)
    for i, h in enumerate(hs):
        _, _, count = layer_blocks(logn, h, L)
        total += delta(L, count) if i < len(hs) - 1 else (count - 1) * Q[L] + BEAT + OUT[L][-1] + WR + 2
    return total


def main():
    net = json.loads((ROOT / "study" / "results" / "structured_net.json").read_text())
    have = {(int(k[:-1]), k[-1]): {b >> 1 for b in v} for k, v in net["read_lo"].items()}
    have_w = {int(b): {(int(s[:-3]), s[-3]) for s in v} for b, v in net["write"].items()}
    lines = ["# FFT 64 / 128 bit trong lõi: gán khối tile và lịch đọc (mô hình trước RTL)\n",
             "Mô hình: [model/fft_wide_sched.py](../../model/fft_wide_sched.py). Mỗi phần 32 bit của một phần tử là một phần "
             "tử định dạng 0 \"ảo\"; cặp phần thứ k của butterfly b rơi vào tile T(b) | k theo luật định dạng 0, nên L tile "
             "T(b) .. T(b) + L − 1 là một khối: tile T(b) | k đọc phần k bằng nguồn mạng định dạng 0 của nó rồi chuyển cho "
             "tile của khối làm butterfly.\n",
             "| Định dạng | Tầng đã xét | Chu kỳ đọc xung đột | Nguồn đọc thêm mỗi cổng (lớn nhất / trung bình) | "
             "Nguồn đọc mỗi cổng sau khi thêm (lớn nhất / trung bình) | Nguồn ghi thêm mỗi siêu bank (lớn nhất) |",
             "|---|---:|---:|---:|---:|---:|"]
    union = {k: set(v) for k, v in have.items()}
    union_w = {k: set(v) for k, v in have_w.items()}
    for L, name in ((2, "1 (64 bit)"), (4, "2 (128 bit)")):
        ports, wbank, conf, nl = check(L)
        add = {k: ports[k] - have[k] for k in ports}
        for k in ports:
            union[k] |= ports[k]
        addw = []
        for s, v in wbank.items():
            for b in (2 * s, 2 * s + 1):
                new = v - union_w[b]
                union_w[b] |= v
                addw.append(len(new))
        tot = [len(have[k] | ports[k]) for k in ports]
        a = [len(v) for v in add.values()]
        lines.append(f"| {name} | {nl} | {conf} | {max(a)} / {sum(a) / len(a):.2f} | {max(tot)} / {sum(tot) / len(tot):.2f} | "
                     f"{max(addw)} |")
    tot = [len(v) for v in union.values()]
    old = [len(v) for v in have.values()]
    lines.append(f"\nHợp cả ba định dạng và NTT: đọc {max(tot)} / {sum(tot) / len(tot):.2f} nguồn mỗi cổng (trước: "
                 f"{max(old)} / {sum(old) / len(old):.2f}); ghi {max(len(v) for v in union_w.values())} / "
                 f"{sum(len(v) for v in union_w.values()) / 64:.2f} nguồn mỗi bank (trước: "
                 f"{max(len(v) for v in have_w.values())} / {sum(len(v) for v in have_w.values()) / 64:.2f}).\n")
    lines.append("## Lịch đầy đủ: ca vàng 1.0, xung đột, chu kỳ (rào chắn mỗi tầng)\n")
    lines.append("Đọc x phần k ở e + k, y ở e + k + 1 (x giữ một chu kỳ trong mạng); phần ảo từ e + L; kết quả ghi x một chu "
                 "kỳ sau khi tile trả, y hai chu kỳ sau; root phần k đọc ở e + k − (độ sớm của khối).\n")
    lines.append("| W | N | Chiều | Khớp ca vàng | Chu kỳ | Xung đột đọc / ghi / ROM root | Ngưỡng giả thuyết 3 |")
    lines.append("|---:|---:|---|---|---:|---:|---:|")
    tabs = {(L, inv): (plan.roots_inv(32 * L) if inv else plan.roots(32 * L)) for L in (2, 4) for inv in (False, True)}
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] not in (0, 1) or c["fmt"] not in (1, 2) or c["logn"] < 2:
            continue
        L, inv = 2 << (c["fmt"] - 1), c["op"] == 1
        w = 32 * L
        a = [wrapw(int(x, 16), w) for x in d["a"][0]]
        e = [wrapw(int(x, 16), w) for x in d["expected"][0]]
        res, cyc, (rc, wc, pc) = run(L, c["logn"], inv, a, tabs[(L, inv)])
        assert res == e, c
        th = f"{H3['inv' if inv else 'fwd'][w]}" if c["logn"] == 10 else ""
        lines.append(f"| {w} | {1 << c['logn']} | {'ngược' if inv else 'xuôi'} | có | {cyc} | {rc} / {wc} / {pc} | {th} |")
    (ROOT / "study" / "results" / "fft_wide_sched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
