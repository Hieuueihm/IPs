"""NTT with two 16-bit coefficients per 32-bit word and four 16-bit lanes per tile (planning model, before RTL).

Question: for q < 2^15 (3329, 7681, 10753, 12289, 18433) the core now runs one 32-bit Montgomery lane per tile: three
passes over the fused 32x32 multiplier, one butterfly per tile every 3 cycles. The tile's four 16x16 leaves could instead
run four independent 16-bit lanes (Montgomery R = 2^16: T = a b, m = T_lo q' mod 2^16, m q; three passes per leaf, a new
modular product on each leaf every 3 cycles), i.e. 4 modular products per tile every 3 cycles. This model checks whether
the memory, the bank -> tile network and the root ROM of the current core can feed that, without a second data layout.

Layout ("narrowing" by the same mapping as the wide FFT): coefficient c in 16-bit cell c, so word w (cells 2w, 2w + 1)
holds coefficients 2w and 2w + 1, and is the format-4 element w of the existing core (superbank bank(2w) >> 1).
  - a layer of distance h >= 2 over N coefficients pairs words (w, w + h/2): exactly the format-4 layer of distance h/2
    over N/2 elements (same tile tables, same network sources); one word pair = two coefficient butterflies (low lanes,
    high lanes) with the SAME root N/(2h) + floor(w / h);
  - the last layer (h = 1, only for a complete transform) pairs the two coefficients inside each word; a tile takes two
    neighbouring words (2j, 2j + 1) (the format-4 layer of distance 1 over N/2 elements), roots N/2 + 2j and N/2 + 2j + 1:
    the two children of one root pack, which the network already delivers together.
So every layer is N/4 "beats" (a word pair, two coefficient butterflies), half the beats of the one-lane core, each
needing one root pack (or root 1, or both children of one pack). A tile takes 2 beats every 3 cycles (lanes 0-1, 2-3).

Checked here, per layer and cycle, with the existing tables (model/ntt_core_sched.py) and the core's pipeline offsets:
values against the 1.0 golden NTT cases (q 12289, q 3329 with 7 layers at N = 256) and against the evaluation definition
for the other small moduli of study/results/pqc_moduli.md; read / write bank conflicts; root-pack bank conflicts per ROM
port (counted as extra cycles, as the one-lane model does); cycles against the one-lane core. The issue phase of the
tiles is a parameter (all in step, or staggered as the one-lane core).

Run: python model/ntt_packed16.py   (writes study/results/ntt_packed16.md)
"""
import importlib.util
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / "model" / file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


sc = _load("ntt_core_sched", "ntt_core_sched.py")
pc = _load("ntt_prime_core", "ntt_prime_core.py")
TILES, PB = 16, 4
LAT16 = 16          # accept -> result of a 16-bit lane (estimate: passes 4 cycles apart on a leaf of latency 3, IN_REG)


def layers(logn, inverse, hmin):
    hs, h = [], (1 << logn) // 2
    while h >= (1 << hmin):
        hs.append(h)
        h //= 2
    return hs[::-1] if inverse else hs


def beats_of_layer(logn, h):
    """Per tile: list of beats; a beat = (word x, word y, [(cx, cy, root), (cx, cy, root)], packs)."""
    n = 1 << logn
    lw = logn - 1                                     # words: N / 2 = 2^lw
    out = {}
    if lw == 0:                                       # N = 2: one word, one intra-word butterfly
        out[0] = [(0, None, [(0, 1, 1)], set())]
        return out
    hp = max(h // 2, 1)
    firsts, kernel, count, same = sc.layer_config(lw, hp)
    assert not same                                   # words never share a superbank at N <= 1024
    for t, p in firsts.items():
        lst = []
        for k in range(count):
            wx, wy = sc.pair(sc.enum(p, kernel, k), hp)
            if h >= 2:
                r = sc.root_index(n, h, 2 * wx)
                bfs = [(2 * wx, 2 * wy, r), (2 * wx + 1, 2 * wy + 1, r)]
                packs = set() if r < 2 else {(r >> 1) - 1}
            else:                                     # intra-word butterflies of words wx, wy = wx + 1
                bfs = [(2 * wx, 2 * wx + 1, n // 2 + wx), (2 * wy, 2 * wy + 1, n // 2 + wy)]
                packs = {((n // 2 + wx) >> 1) - 1}
                assert (n // 2 + wx) >> 1 == (n // 2 + wy) >> 1        # both children of one pack
            lst.append((wx, wy, bfs, packs))
        out[t] = lst
    return out


def run(q, logn, inverse, data, gm, igm, hmin, phase, lat=LAT16):
    """Barrier per layer. Tile t accepts beats in cycles A with (A + phase[t]) mod 3 in {0, 1}; reads (x, y words and
    the root pack) at A - 2, writes at A + lat + 1. Returns (result, cycles, read conflicts, write conflicts, root extra)."""
    mem = list(data)
    roots = igm if inverse else gm
    reads, writes, packs = {}, {}, {}
    S = 0
    first_read = None
    for h in layers(logn, inverse, hmin):
        per = beats_of_layer(logn, h)
        new = {}
        last_w = S
        for t, lst in per.items():
            a = S + 2
            while (a + phase[t]) % 3:
                a += 1
            for k, (wx, wy, bfs, pk) in enumerate(lst):
                A = a + 3 * (k // 2) + (k % 2)
                for w in (wx, wy):
                    if w is not None:
                        reads.setdefault(A - 2, []).append(sc.superbank(w))
                        writes.setdefault(A + lat + 1, []).append(sc.superbank(w))
                first_read = A - 2 if first_read is None else min(first_read, A - 2)
                for pos in pk:
                    packs.setdefault((A - 2, t >= 8), {}).setdefault(pos % PB, set()).add(pos)
                for cx, cy, r in bfs:
                    x, y, w_ = mem[cx], mem[cy], roots[r]
                    if inverse:
                        s_, d = (x + y) % q, (x - y) % q
                        new[cx], new[cy] = (s_ + (q if s_ & 1 else 0)) >> 1, sc.mont32(d, w_, q)
                    else:
                        tt = sc.mont32(y, w_, q)
                        new[cx], new[cy] = (x + tt) % q, (x - tt) % q
                last_w = max(last_w, A + lat + 1)
        for c, v in new.items():
            mem[c] = v
        S = last_w + 1
    rc = sum(len(v) - len(set(v)) for v in reads.values())
    wc = sum(len(v) - len(set(v)) for v in writes.values())
    extra = sum(max(len(x) for x in b.values()) - 1 for b in packs.values())
    return mem, S - first_read + extra, rc, wc, extra


PHASES = {"cùng pha": [0] * TILES, "lệch t mod 3": [t % 3 for t in range(TILES)],
          "lệch t / 6 (như lõi một làn)": [t // 6 for t in range(TILES)]}


def main():
    tabs = sc.Tables()
    gold = sc.golden()
    lines = ["# NTT hai hệ số mỗi từ, bốn làn 16 bit mỗi tile (mô hình trước RTL)\n",
             "Mô hình: [model/ntt_packed16.py](../../model/ntt_packed16.py). Hệ số c ở ô 16 bit c; từ w (hai hệ số) là phần "
             "tử định dạng 4 thứ w, nên mỗi tầng dùng lại bảng tầng định dạng 4 của N/2 phần tử và nguồn mạng hiện có. "
             "Mỗi nhịp là một cặp từ = hai butterfly; tile nhận 2 nhịp mỗi 3 chu kỳ (4 làn, Montgomery 16 bit 3 lượt). "
             f"Rào chắn mỗi tầng; độ trễ làn ước lượng {LAT16}.\n"]
    # 1. golden cases, every phase option
    lines.append("## Khớp số học và chi phí theo cách lệch pha (ca vàng 1.0)\n")
    lines.append("| Lệch pha | q | N | Chiều | Ca | Khớp | Xung đột đọc / ghi | Chu kỳ thêm do bank root | Chu kỳ |")
    lines.append("|---|---:|---:|---|---:|---|---:|---:|---:|")
    best = {}
    for pname, ph in PHASES.items():
        for prof, (q, lns) in ((0, (12289, (8, 9, 10))), (1, (3329, (8,)))):
            for logn in lns:
                hmin = 1 if (q == 3329 and logn == 8) else 0
                for op in (5, 6):
                    cases = gold[(prof, logn, op)]
                    ok, res = True, None
                    for a, e in cases:
                        res = run(q, logn, op == 6, a, tabs.gm[q], tabs.igm[q], hmin, ph)
                        ok &= res[0] == e
                    assert ok, (pname, q, logn, op)
                    _, cyc, rc, wc, extra = res
                    best.setdefault((q, logn, op), {})[pname] = (cyc, rc, wc, extra)
                    lines.append(f"| {pname} | {q} | {1 << logn} | {'ngược' if op == 6 else 'xuôi'} | {len(cases)} | có | "
                                 f"{rc} / {wc} | {extra} | {cyc} |")
    # 2. other small moduli against the definition, all N, in-step phase
    lines.append("\n## Các modulus nhỏ khác, so với định nghĩa (đánh giá đa thức), N = 2..1024\n")
    rng = random.Random(20261101)
    small = [("HAWK ký", 18433, 0), ("Kyber vòng 1", 7681, 0), ("Saber RNS", 10753, 0), ("FN-DSA", 12289, 0),
             ("ML-KEM", 3329, 1)]
    n_ok = 0
    for app, q, hmin_all in small:
        for logn in range(1, 11):
            hmin = hmin_all if logn >= 2 else 0
            v2 = ((q - 1) & -(q - 1)).bit_length() - 1
            if logn - hmin > v2 - 1:                   # q has no root of order 2^(logn - hmin + 1)
                continue
            gm, igm = pc.tables(q, logn, hmin)
            a = [rng.randrange(q) for _ in range(1 << logn)]
            f = run(q, logn, False, a, gm, igm, hmin, PHASES["cùng pha"])
            assert f[0] == pc.ref_forward(a, q, logn, hmin) and f[2] == 0 and f[3] == 0, (app, q, logn)
            b = run(q, logn, True, f[0], gm, igm, hmin, PHASES["cùng pha"])
            assert b[0] == a, (app, q, logn, "inverse")
            n_ok += 2
    lines.append(f"{n_ok} phép biến đổi (5 modulus, mọi N có root, xuôi khớp định nghĩa, ngược trả lại đầu vào), không "
                 "xung đột bank đọc/ghi.\n")
    # 3. against the one-lane core
    lines.append("## So với lõi một làn 32 bit hiện tại (cùng rào chắn mỗi tầng)\n")
    lines.append("| q | N | Chiều | Một làn, rào chắn | Một làn, chồng tầng (RTL) | Hai hệ số / từ, cách lệch tốt nhất | Nhanh hơn (rào chắn) |")
    lines.append("|---:|---:|---|---:|---:|---:|---:|")
    overlap = {(12289, 10, 5): 984, (12289, 10, 6): 985, (3329, 8, 5): 231, (3329, 8, 6): 225}
    for (q, logn, op), d in sorted(best.items()):
        hmin = 1 if (q == 3329 and logn == 8) else 0
        a, _ = gold[(0 if q == 12289 else 1, logn, op)][0]
        _, one, _ = sc.run(q, logn, op == 6, a, tabs)
        pname, (cyc, _, _, _) = min(d.items(), key=lambda kv: kv[1][0])
        ov = overlap.get((q, logn, op), "")
        lines.append(f"| {q} | {1 << logn} | {'ngược' if op == 6 else 'xuôi'} | {one} | {ov} | {cyc} ({pname}) | "
                     f"{one / cyc:.2f}× |")
    # 4. sensitivity to the lane latency
    lines.append("\n## Độ nhạy theo độ trễ làn 16 bit (q 12289, N 1024, xuôi, cùng pha)\n")
    lines.append("| Độ trễ làn | Chu kỳ |")
    lines.append("|---:|---:|")
    a, _ = gold[(0, 10, 5)][0]
    for lat in (13, 16, 20):
        lines.append(f"| {lat} | {run(12289, 10, False, a, tabs.gm[12289], tabs.igm[12289], 0, PHASES['cùng pha'], lat)[1]} |")
    # 5. throughput regime: issue cycles only (what interleaving independent polynomials approaches)
    lines.append("\n## Khi đủ việc: chu kỳ phát mỗi đa thức (nhiều đa thức xen nhau che độ trễ)\n")
    lines.append("Một làn: mỗi tầng N/2 butterfly, mỗi tile một butterfly mỗi 3 chu kỳ. Hai hệ số mỗi từ: mỗi tầng N/4 nhịp, "
                 "mỗi tile 2 nhịp mỗi 3 chu kỳ. Chưa tính xung đột bank root (khoảng 7% ở N1024 khi cùng pha).\n")
    lines.append("| Ứng dụng | q | N | Tầng | Một làn: chu kỳ phát | Hai hệ số / từ: chu kỳ phát | Tỉ lệ | "
                 "Phần độ trễ trong một đa thức (hai hệ số, rào chắn) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for app, q, logn, hmin, op in (("ML-KEM", 3329, 8, 1, 5), ("FN-DSA kiểm", 12289, 9, 0, 5),
                                   ("FN-DSA kiểm", 12289, 10, 0, 5)):
        nl = logn - hmin
        one = nl * ((1 << logn) // 2 // TILES) * 3
        two = nl * ((1 << logn) // 4 // TILES) * 3 // 2
        a, _ = gold[(0 if q == 12289 else 1, logn, op)][0]
        cyc = run(q, logn, False, a, tabs.gm[q], tabs.igm[q], hmin, PHASES["cùng pha"])[1]
        lines.append(f"| {app} | {q} | {1 << logn} | {nl} | {one} | {two} | {one / two:.1f}× | "
                     f"{100 * (cyc - two) / cyc:.0f}% |")
    lines += [
        "\n## Ước lượng tài nguyên (chưa đo, ước lượng tay theo RTL tile hiện tại)\n",
        "| Thêm vào mỗi tile | LUT ước lượng |",
        "|---|---:|",
        "| Toán hạng riêng cho từng lá ở chế độ làn (3 lượt: (y, w), (T thấp, q′), (m, q) mỗi làn 16 bit) | 60–100 |",
        "| Rút gọn mỗi làn: u = T cao + (m q) cao + [T thấp ≠ 0] và trừ q có điều kiện, 4 làn × 17 bit | 130–140 |",
        "| Chẻ bộ cộng/trừ modulo và phép chia đôi thành hai nửa 16 bit | 30–50 |",
        "| Điều khiển nhận 2 nhịp mỗi 3 chu kỳ | khoảng 20 |",
        "| **Cộng** | **khoảng 250–350 mỗi tile, 4–5,6k cho 16 tile (khoảng 8–10% lõi)** |",
        "",
        "Ngoài tile: mạng, bộ nhớ và bảng tầng giữ nguyên (bảng định dạng 4 của logn − 1). Lõi cần cờ \"hai hệ số mỗi từ\" "
        "chọn bảng logn − 1, cách lấy cả hai root con cho tầng cuối, và bảng root dạng R = 2¹⁶ (bảng gốc của 1.0 cho 12289 / "
        "3329). Điều kiện số học: q < 2¹⁵ để u < 2q vừa 16 bit (3329, 7681, 10753, 12289, 18433; không gồm 64513).",
        "",
        "## Kết luận\n",
        "- Hai hệ số mỗi từ dùng lại được mạng, bộ nhớ và bảng tầng hiện có: không xung đột đọc/ghi ở mọi N, xung đột bank "
        "root nhỏ nhất khi các tile cùng pha (khoảng 7% ở N1024).",
        "- Một đa thức: nhanh hơn 2,0× (N256) đến 2,6× (N1024) với rào chắn mỗi tầng, vì độ trễ mỗi tầng chiếm 47–75% thời gian.",
        "- Khi đủ việc (nhiều đa thức hoặc nhiều prime xen nhau, như ma trận–vectơ của ML-KEM hay NTRUSolve), trần phát là 4×. "
        "Vậy làn hẹp chỉ phát huy hết khi đi cùng chạy nhiều đa thức trong một lệnh.",
    ]
    (ROOT / "study" / "results" / "ntt_packed16.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
