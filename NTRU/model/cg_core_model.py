"""Constant-geometry schedule for the whole core (NTT every q, FFT 32 / 64 / 128 bit): no per-tile address generation.

Question (02/11/2026): the current core (hdl/core_ntt/ntt_core.sv) works in place. Every layer pairs elements at a
different distance, so for each tile and each butterfly the core computes element pair, superbanks, rows and root
address, and a structured network with per-bank row multiplexers routes 16 tiles to 64 banks. Can a schedule whose data
movement is the same in every layer replace that with shared counters and fixed wiring?

Constant geometry (Pease): layer s reads positions i and i + M/2 of one buffer and writes the two results to positions
2i and 2i + 1 of the other buffer (ping-pong in the same BRAMs, which use 128 of 1024 rows today). The inverse is the
transpose (read 2i, 2i + 1, write i, i + M/2). With hmin skipped NTT layers the 2^hmin low bits stay in place. M is the
number of points: N for NTT, N/2 complex points for FFT (real parts at elements 0 .. N/2 - 1, imaginary after, as now).

Assignment (same for NTT and FFT): T = min(16, M/2) tiles; tiles 0 .. T/2 - 1 take i = (T/2) k + t (first quarter),
tiles T/2 .. T - 1 take i = M/4 + (T/2) k + (t - T/2). So in every step half the tiles write the lower half of the
buffer and half the upper half (needed for FFT, where all 16 tiles issue together: with i = 16k + t all 64 result words
of a step would land in 16 superbanks).
Placement: position p of a buffer is in superbank 16 [p >= M/2] + ((p mod 16) xor 8 [bit b of p]), b = log2(M/4) when
b >= 4 (else no xor), row (p mod M/2) div 16; FFT parts (real / imaginary) and limbs only change the row.

Tile timing (accept cycle A of a request; first beat for FFT):
  NTT: tile t accepts when (PHASE[t] + A) mod 3 == 0, PHASE[t] = t div 6; x and y read at A - 2; results written at
       A + 21 (spec 10: latency 20 with IN_REG = 1, write one cycle after).
  FFT: all tiles issue together, one butterfly every P = 3 / 12 / 48 cycles per tile (32 / 64 / 128 bit, the tile's own
       rate, as the current core); beat j (real limbs, then imaginary limbs) reads x and y at A - 2 + j; result beat j
       written at A + OUT[j] + 2 (spec 10 4.7 / 4.8 with IN_REG = 1; capture and forwarding register as now).

Checks, every layer of every case:
  1. each butterfly of the schedule is a butterfly of the in-place transform (pair at the right distance, every pair
     once); NTT values against the golden vectors and the profile-3 reference; final layout is the natural order;
  2. no superbank gets two reads or two writes in one cycle (both buffers share the ports);
  3. every read after the write that produced the word, every write after the last read of the old word;
  4. cycles, first read to last write + 1, each layer started as early as 2-3 allow, against the current core;
  5. sources per tile read port and per superbank write port; each tile's root index as a function of the step.

Run: python model/cg_core_model.py   (writes study/results/cg_core_model.md)
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


sc = _load("sched", "ntt_core_sched.py")
pc = _load("prime", "ntt_prime_core.py")

TILES, PHASE = sc.TILES, sc.PHASE
NTT_WRITE = sc.TILE_LAT + 1
FFT = {1: (3, [16, 17]), 2: (12, [24, 25, 28, 29]), 4: (48, [45, 48, 50, 51, 60, 63, 65, 66])}   # L: (P, OUT)


def place(p, m):
    """Superbank of position p in a buffer of m points."""
    h = m // 2
    b = (m // 4).bit_length() - 1
    s = p % 16
    if b >= 4 and p >> b & 1:
        s ^= 8
    return 16 * (p >= h) + s


def positions(i, m, hmin, inverse):
    """Read positions (x, y) and write positions (x', y') of butterfly i."""
    b, ih = i & ((1 << hmin) - 1), i >> hmin
    lo = ((ih << 1) << hmin) | b
    near = (lo, lo | (1 << hmin))
    far = (i, i + m // 2)
    return (near, far) if inverse else (far, near)


def assignment(m):
    """{tile: [butterfly of step 0, 1, ...]}."""
    nb = m // 2
    t_ = min(TILES, nb)
    out = {}
    if t_ == 1:
        return {0: [0]}
    half = t_ // 2
    for t in range(t_):
        base = t if t < half else m // 4 + (t - half)
        out[t] = [base + half * k for k in range(nb // t_)]
    assert sorted(i for v in out.values() for i in v) == list(range(nb))
    return out


def layer_hs(m, hmin, inverse):
    hs, h = [], m // 2
    while h >= (1 << hmin):
        hs.append(h)
        h //= 2
    return hs[::-1] if inverse else hs


def layer_events(m, hmin, inverse, s, start, fft_l):
    """Butterflies of layer s started at `start`. Words are (buffer, position, part, limb)."""
    src, dst = s & 1, 1 - (s & 1)
    ev = []
    for t, idx in assignment(m).items():
        if fft_l:
            per, out = FFT[fft_l]
            a = start + 2
        else:
            per, out = 3, None
            a = start + 2
            while (PHASE[t] + a) % 3:
                a += 1
        for k, i in enumerate(idx):
            A = a + per * k
            (px, py), (wx, wy) = positions(i, m, hmin, inverse)
            reads, writes = [], []
            if fft_l:
                for j in range(2 * fft_l):
                    part, limb = j // fft_l, j % fft_l
                    for p in (px, py):
                        reads.append(((src, p, part, limb), place(p, m), A - 2 + j))
                    for p in (wx, wy):
                        writes.append(((dst, p, part, limb), place(p, m), A + out[j] + 2))
            else:
                for p in (px, py):
                    reads.append(((src, p, 0, 0), place(p, m), A - 2))
                for p in (wx, wy):
                    writes.append(((dst, p, 0, 0), place(p, m), A + NTT_WRITE))
            ev.append({"t": t, "k": k, "i": i, "A": A, "per": per, "rp": (px, py), "wp": (wx, wy), "reads": reads,
                       "writes": writes})
    return ev


class Book:
    def __init__(self):
        self.rd, self.wr, self.wt, self.rt, self.last = {}, {}, {}, {}, {}

    def fits(self, ev):
        rd, wr = {}, {}
        for e in ev:
            for w, sb, cyc in e["reads"]:
                if sb in self.rd.get(cyc, ()) or sb in rd.setdefault(cyc, set()):
                    return False
                rd[cyc].add(sb)
                if self.wt.get(w, -10**9) >= cyc:
                    return False
            for w, sb, cyc in e["writes"]:
                if sb in self.wr.get(cyc, ()) or sb in wr.setdefault(cyc, set()):
                    return False
                wr[cyc].add(sb)
                if self.rt.get(w, -10**9) >= cyc:
                    return False
            if self.last.get(e["t"], -10**9) >= e["A"]:
                return False
        return True

    def take(self, ev):
        for e in ev:
            for w, sb, cyc in e["reads"]:
                self.rd.setdefault(cyc, set()).add(sb)
                self.rt[w] = max(self.rt.get(w, -10**9), cyc)
            for w, sb, cyc in e["writes"]:
                self.wr.setdefault(cyc, set()).add(sb)
                self.wt[w] = cyc
            self.last[e["t"]] = max(self.last.get(e["t"], -10**9), e["A"] + e["per"] - 1)   # tile busy until then


def run(m, hmin, inverse, fft_l=0, q=None, data=None, gm=None, igm=None):
    """One command. Returns (values in logical order or None, cycles, layer starts, final layout natural, stats)."""
    hs = layer_hs(m, hmin, inverse)
    lay = [list(range(m)), [None] * m]
    val = [list(data), [None] * m] if data is not None else None
    roots = (igm if inverse else gm) if data is not None else None
    book = Book()
    start, starts, stats = 0, [], []
    for s, h in enumerate(hs):
        while True:
            ev = layer_events(m, hmin, inverse, s, start, fft_l)
            if book.fits(ev):
                break
            start += 1
        book.take(ev)
        starts.append(start)
        src, dst = s & 1, 1 - (s & 1)
        seen = set()
        st = {"rsrc": {}, "wsrc": {}, "root": {}}
        for e in ev:
            (px, py), (wx, wy) = e["rp"], e["wp"]
            cx, cy = lay[src][px], lay[src][py]
            assert cy == cx + h and (cx // h) % 2 == 0, ("pair", m, hmin, inverse, fft_l, s, e["i"])
            assert cx not in seen
            seen.add(cx)
            r = sc.root_index(m, h, cx)
            if val is not None:
                w = roots[r]
                x, y = val[src][px], val[src][py]
                if inverse:
                    a_, d = (x + y) % q, (x - y) % q
                    zx, zy = (a_ + (q if a_ & 1 else 0)) >> 1, sc.mont32(d, w, q)
                else:
                    tt = sc.mont32(y, w, q)
                    zx, zy = (x + tt) % q, (x - tt) % q
                val[dst][wx], val[dst][wy] = zx, zy
            lay[dst][wx], lay[dst][wy] = cx, cy
            t = e["t"]
            st["rsrc"].setdefault(("x", t), set()).add(place(px, m))
            st["rsrc"].setdefault(("y", t), set()).add(place(py, m))
            st["wsrc"].setdefault(place(wx, m), set()).add((t, 0))
            st["wsrc"].setdefault(place(wy, m), set()).add((t, 1))
            st["root"].setdefault(t, {})[e["k"]] = r
        assert len(seen) == m // 2
        stats.append(st)
        lay[src] = [None] * m
        if val is not None:
            val[src] = [None] * m
    fin = len(hs) & 1
    out = None
    if val is not None:
        out = [None] * m
        for p in range(m):
            out[lay[fin][p]] = val[fin][p]
    cyc = max(book.wr) - min(book.rd) + 1
    return out, cyc, starts, lay[fin] == list(range(m)), stats


def root_kind(st):
    """How the tiles' root indices depend on the step: shared address into a per-tile table, period p."""
    r = st["root"]
    ks = sorted(next(iter(r.values())))
    if all(len({r[t][k] for t in r}) == 1 for k in ks):
        return "chung", 1
    p = max(len(set(v.values())) for v in r.values())
    assert all(v[k] == v[k % p] for v in r.values() for k in ks)
    return ("cố định", 1) if p == 1 else ("bảng", p)


def current_ntt():
    cur = {}
    for line in (ROOT / "study" / "results" / "ntt_core_overlap.md").read_text(encoding="utf-8").splitlines():
        f = [x.strip() for x in line.strip("|").split("|")]
        if len(f) > 6 and f[0].isdigit() and f[1].isdigit():
            cur[(int(f[0]), int(f[1]), f[2])] = int(f[6])
    return cur


def current_fft():
    """(L, N, direction) -> cycles of the current core (barrier per layer)."""
    cur = {}
    for name, lw in (("fft_core_sched.md", None), ("fft_wide_sched.md", "W")):
        for line in (ROOT / "study" / "results" / name).read_text(encoding="utf-8").splitlines():
            f = [x.strip() for x in line.strip("|").split("|")]
            if lw is None and len(f) >= 4 and f[0].isdigit() and f[3].isdigit():
                cur[(1, int(f[0]), f[1])] = int(f[3])
            elif lw and len(f) >= 5 and f[0] in ("64", "128") and f[1].isdigit() and f[4].isdigit():
                cur[(int(f[0]) // 32, int(f[1]), f[2])] = int(f[4])
    return cur


def main():
    tabs = sc.Tables()
    gold = sc.golden()
    cn = current_ntt()
    cf = current_fft()
    ports_r, ports_w, roots_kind, root_words = {}, {}, {}, {}

    def collect(tag, stats, key, big):
        words = 0
        for st in stats:
            for scope in (("all",) + (("big",) if big else ())):
                for (p, t), v in st["rsrc"].items():
                    ports_r.setdefault((scope, tag, p, t), set()).update(v)
                for sb, v in st["wsrc"].items():
                    ports_w.setdefault((scope, tag, sb), set()).update(v)
            k, p = root_kind(st)
            roots_kind[(tag, k)] = roots_kind.get((tag, k), 0) + 1
            words += p
        root_words[key] = words

    lines = ["# Lịch hình học cố định cho cả lõi (mô hình trước RTL)\n",
             "Mô hình: [model/cg_core_model.py](../../model/cg_core_model.py). Mỗi tầng đọc vị trí i, i + M/2 của một bộ "
             "đệm, ghi 2i, 2i + 1 vào bộ đệm kia (ngược: chuyển vị); M = N với NTT, N/2 điểm phức với FFT. Nửa số tile làm "
             "phần tư đầu của các butterfly, nửa kia phần tư thứ hai, để mỗi bước một nửa tile ghi nửa dưới, nửa kia ghi nửa "
             "trên bộ đệm. Tầng sau bắt đầu sớm nhất có thể (không trùng cổng, đọc sau ghi, ghi sau đọc). Cột \"lõi hiện tại\": "
             "NTT theo kế hoạch chồng tầng, FFT có rào chắn mỗi tầng (cả hai trùng RTL).\n",
             "## NTT\n",
             "| Profile | N | hmin | Chiều | Ca vàng | Khớp | Thứ tự cuối tự nhiên | Chu kỳ | Lõi hiện tại | Chênh |",
             "|---:|---:|---:|---|---:|---|---|---:|---:|---:|"]
    for prof, (q, lns) in sc.PROFILES.items():
        for logn in lns:
            hm = sc.min_stride(q, logn).bit_length() - 1
            for op in (5, 6):
                inv = op == 6
                cases = gold[(prof, logn, op)]
                ok = True
                for a, e in cases:
                    res, cyc, starts, nat, stats = run(1 << logn, hm, inv, 0, q, a, tabs.gm[q], tabs.igm[q])
                    ok &= res == e
                assert ok, (prof, logn, op)
                collect("NTT", stats, ("NTT", logn, hm, inv), logn >= 6)
                c0 = cn[(prof, 1 << logn, "ngược" if inv else "xuôi")]
                lines.append(f"| {prof} | {1 << logn} | {hm} | {'ngược' if inv else 'xuôi'} | {len(cases)} | có | "
                             f"{'có' if nat else 'không'} | {cyc} | {c0} | {100 * (cyc - c0) / c0:+.0f}% |")
    rng = random.Random(7)
    lines += ["\nProfile 3, các modulo khảo sát, dữ liệu ngẫu nhiên, so với định nghĩa đánh giá và lượt ngược về lại:\n",
              "| Ứng dụng | q | N | hmin | Xuôi khớp | Ngược về lại | Chu kỳ |",
              "|---|---:|---:|---:|---|---|---:|"]
    for app, q, logn, hm in pc.SURVEY:
        gm, igm = pc.tables(q, logn, hm)
        a = [rng.randrange(q) for _ in range(1 << logn)]
        f, c1, _, n1, s1 = run(1 << logn, hm, False, 0, q, a, gm, igm)
        g, c2, _, n2, s2 = run(1 << logn, hm, True, 0, q, f, gm, igm)
        assert f == pc.ref_forward(a, q, logn, hm) and g == a and n1 and n2, app
        collect("NTT", s1, ("NTT", logn, hm, False), logn >= 6)
        collect("NTT", s2, ("NTT", logn, hm, True), logn >= 6)
        lines.append(f"| {app} | {q} | {1 << logn} | {hm} | có | có | {c1} |")
    # every NTT size and hmin for the port and root statistics
    for logn in range(3, 11):
        for hm in range(3):
            if hm < logn - 1:
                for inv in (False, True):
                    collect("NTT", run(1 << logn, hm, inv)[4], ("NTT", logn, hm, inv), logn >= 6)
    lines += ["\n## FFT (cấu trúc: cặp, cổng, phụ thuộc, chu kỳ; số học như lõi hiện tại)\n",
              "| Độ rộng | N | Chiều | Mọi cặp đúng tầng | Thứ tự cuối tự nhiên | Chu kỳ | Lõi hiện tại | Chênh |",
              "|---:|---:|---|---|---|---:|---:|---:|"]
    for fl in (1, 2, 4):
        for logn in range(3, 11):
            for inv in (False, True):
                _, cyc, starts, nat, stats = run(1 << (logn - 1), 0, inv, fl)
                collect(f"FFT{32 * fl}", stats, (f"FFT{32 * fl}", logn, 0, inv), logn >= 7)
                c0 = cf.get((fl, 1 << logn, "ngược" if inv else "xuôi"))
                ch = f"{100 * (cyc - c0) / c0:+.0f}%" if c0 else ""
                if logn >= 6 or fl == 1:
                    lines.append(f"| {32 * fl} | {1 << logn} | {'ngược' if inv else 'xuôi'} | có | "
                                 f"{'có' if nat else 'không'} | {cyc} | {c0 or ''} | {ch} |")
    lines += ["\n## Mạng và root\n",
              "| Chế độ | Cổng đọc x / y mỗi tile, mọi N | Cổng ghi mỗi superbank, mọi N | Cổng đọc, N ≥ 64 | Cổng ghi, N ≥ 64 |",
              "|---|---:|---:|---:|---:|"]
    tags = ["NTT", "FFT32", "FFT64", "FFT128"]

    def mx(sc_, tgs, port=None):
        if port is None:
            return max(len(set().union(*(ports_w.get((sc_, tg, b), set()) for tg in tgs))) for b in range(32))
        return max(len(set().union(*(ports_r.get((sc_, tg, port, t), set()) for tg in tgs))) for t in range(TILES))
    for tg in tags + ["mọi chế độ"]:
        tgs = tags if tg == "mọi chế độ" else [tg]
        lines.append(f"| {tg} | {mx('all', tgs, 'x')} / {mx('all', tgs, 'y')} | {mx('all', tgs)} | "
                     f"{mx('big', tgs, 'x')} / {mx('big', tgs, 'y')} | {mx('big', tgs)} |")
    lines.append("\nLõi hiện tại: mỗi nửa 16 bit của cổng toán hạng chọn tới 6 superbank (mạng có cấu trúc), mỗi bank có bộ "
                 "chọn hàng giữa các tile, và địa chỉ được tính riêng cho từng tile.\n")
    kinds = {}
    for (tag, k), v in roots_kind.items():
        kinds.setdefault(tag, {})[k] = v
    lines.append("Root theo tầng (số tầng): " + "; ".join(
        f"{tag}: " + ", ".join(f"{ {'chung': 'một root chung', 'cố định': 'mỗi tile một root cả tầng', 'bảng': 'bảng riêng mỗi tile, địa chỉ chung'}[k]} {v}"
                               for k, v in sorted(kinds[tag].items())) for tag in tags) +
                 ". Không tầng nào cần địa chỉ root riêng cho từng tile.\n")
    lines.append("Số từ root mỗi tile cho một lệnh (một chiều): " + ", ".join(
        f"{tag} N{1 << ln}" + (f" hmin {hm}" if hm else "") + f": {w}"
        for (tag, ln, hm, inv), w in sorted(root_words.items()) if not inv and (ln == 10 or (tag == "NTT" and ln == 8))) +
                 " (FFT: số root phức, mỗi root L từ thực + L từ ảo).")
    out = ROOT / "study" / "results" / "cg_core_model.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
