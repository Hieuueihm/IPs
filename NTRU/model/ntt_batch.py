"""Several polynomials in one NTT command (planning model, before RTL): one-lane 32-bit tiles vs two coefficients per word.

The packed model (model/ntt_packed16.py) shows that one polynomial is latency-bound (47-75% of the time is the layer
latency), so four 16-bit lanes give only 2-2.6x. Workloads often hold several independent polynomials: ML-KEM's
matrix-vector product (k = 2..4 NTTs of N = 256, one q), FN-DSA key generation (NTRUSolve: many NTTs, each modulo a
different 31-bit prime, N from 2 to 1024). Here every layer of the command holds the butterflies of all its polynomials,
so one polynomial's work fills the latency of another's.

Placement: polynomial j sits at coefficient offset j N (one-lane: format 4; packed: word offset j N / 2); the tile of a
butterfly is the bank-indexed rule on the superbanks of its two words (model/structured_net.py tile_of), as the core
does for jobs > 1. Issue, cycle by cycle (a greedy model of an arbiter, not yet the RTL's static tables): every tile
works through its butterflies of the layer in order (polynomial, then index); it issues in its slots (one-lane: one
butterfly every 3 cycles at phase t / 6; packed: 2 beats every 3 cycles, all tiles in step) when its two read
superbanks, its two write superbanks (lat + 1 cycles later) and its root-pack bank on its ROM port are free (the same
pack may be shared). Barrier per layer on commits. Distinct primes need their constants in the tile: one-lane tiles hold
2 moduli, so at N >= 64 (every tile serves every polynomial) a command takes at most 2 primes; below 64 the polynomials
sit on different tiles.

Run: python model/ntt_batch.py   (writes study/results/ntt_batch.md)
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
sn = sc.sn
pc = _load("ntt_prime_core", "ntt_prime_core.py")
TILES, PB = 16, 4
LAT1 = sc.TILE_LAT          # one-lane tile (IN_REG = 1)
LAT16 = 16                  # 16-bit lane estimate (model/ntt_packed16.py)


def sbw(w):
    return sc.superbank(w)


def items_of_layer(polys, logn, h, packed):
    """Work items of one layer for every polynomial: (tile, words (wx, wy), pack, [(poly, cx, cy, root)])."""
    n = 1 << logn
    out = []
    for j, P in enumerate(polys):
        if not packed:
            for i in range(n // 2):
                cx, cy = sc.pair(i, h)
                r = sc.root_index(n, h, cx)
                wx, wy = j * n + cx, j * n + cy
                out.append((sn.tile_of(sbw(wx), sbw(wy)), (wx, wy), None if r < 2 else (r >> 1) - 1,
                            [(j, cx, cy, r)]))
        else:
            nw = n // 2
            if nw == 1:
                out.append((j % TILES, (j * nw, None), None, [(j, 0, 1, 1)]))
                continue
            hp = max(h // 2, 1)
            for i in range(nw // 2):
                ux, uy = sc.pair(i, hp)
                wx, wy = j * nw + ux, j * nw + uy
                if h >= 2:
                    r = sc.root_index(n, h, 2 * ux)
                    bfs = [(j, 2 * ux, 2 * uy, r), (j, 2 * ux + 1, 2 * uy + 1, r)]
                    pk = None if r < 2 else (r >> 1) - 1
                else:
                    bfs = [(j, 2 * ux, 2 * ux + 1, n // 2 + ux), (j, 2 * uy, 2 * uy + 1, n // 2 + uy)]
                    pk = ((n // 2 + ux) >> 1) - 1
                out.append((sn.tile_of(sbw(wx), sbw(wy)), (wx, wy), pk, bfs))
    return out


def run(polys, logn, inverse, hmin, packed):
    """polys: list of dicts {q, gm, igm, data}. Returns (results, cycles first read .. last write + 1, stall cycles)."""
    n = 1 << logn
    mems = [list(P["data"]) for P in polys]
    lat = LAT16 if packed else LAT1
    hs, h = [], n // 2
    while h >= (1 << hmin):
        hs.append(h)
        h //= 2
    if inverse:
        hs = hs[::-1]
    S, first, last_w, stalls = 0, None, 0, 0
    rd, wr, pk_use = {}, {}, {}
    for h in hs:
        items = items_of_layer(polys, logn, h, packed)
        queues = {}
        for it in items:
            queues.setdefault(it[0], []).append(it)
        new = [dict() for _ in polys]
        c = S + 2
        pending = sum(len(v) for v in queues.values())
        layer_last = S
        slot_used = {}
        while pending:
            for t in sorted(queues):
                q = queues[t]
                if not q:
                    continue
                ph = (c + (0 if packed else t // 6)) % 3
                if (packed and ph == 2) or (not packed and ph != 0):
                    continue
                _, (wx, wy), pack, bfs = q[0]
                ws = [sbw(w) for w in (wx, wy) if w is not None]
                rs = rd.setdefault(c - 2, set())
                wsx = wr.setdefault(c + lat + 1, set())
                pkey = (c - 2, t >= 8, None if pack is None else pack % PB)
                if any(s in rs for s in ws) or any(s in wsx for s in ws) or \
                        (pack is not None and pk_use.get(pkey, pack) != pack):
                    stalls += 1
                    continue
                rs.update(ws)
                wsx.update(ws)
                if pack is not None:
                    pk_use[pkey] = pack
                q.pop(0)
                pending -= 1
                first = c - 2 if first is None else min(first, c - 2)
                layer_last = max(layer_last, c + lat + 1)
                for j, cx, cy, r in bfs:
                    P, mem = polys[j], mems[j]
                    qq = P["q"]
                    roots = P["igm"] if inverse else P["gm"]
                    x, y, w_ = mem[cx], mem[cy], roots[r]
                    if inverse:
                        s_, d = (x + y) % qq, (x - y) % qq
                        new[j][cx], new[j][cy] = (s_ + (qq if s_ & 1 else 0)) >> 1, sc.mont32(d, w_, qq)
                    else:
                        tt = sc.mont32(y, w_, qq)
                        new[j][cx], new[j][cy] = (x + tt) % qq, (x - tt) % qq
            c += 1
        for j in range(len(polys)):
            for cc, v in new[j].items():
                mems[j][cc] = v
        last_w = max(last_w, layer_last)
        S = layer_last + 1
    return mems, last_w + 1 - first, stalls


def make_polys(qs, logn, hmin, rng):
    out = []
    for q in qs:
        gm, igm = pc.tables(q, logn, hmin)
        out.append({"q": q, "gm": gm, "igm": igm, "data": [rng.randrange(q) for _ in range(1 << logn)]})
    return out


def check(polys, res, logn, hmin, inverse_input=None):
    for P, r in zip(polys, res):
        assert r == pc.ref_forward(P["data"], P["q"], logn, hmin)


def main():
    rng = random.Random(20261102)
    lines = ["# Nhiều đa thức trong một lệnh NTT: làn 32 bit so với hai hệ số mỗi từ (mô hình trước RTL)\n",
             "Mô hình: [model/ntt_batch.py](../../model/ntt_batch.py). Mỗi tầng gồm butterfly của mọi đa thức; phát theo từng "
             "chu kỳ, tile chỉ phát khi bank đọc, bank ghi và bank root của nó còn trống (mô hình bộ phân xử tham lam, chưa "
             f"phải bảng tĩnh của RTL). Rào chắn mỗi tầng theo lượt ghi. Độ trễ làn: 32 bit {LAT1}, 16 bit {LAT16} (ước lượng). "
             "Mọi kết quả xuôi khớp định nghĩa (đánh giá đa thức) của từng đa thức.\n"]
    # 1. same q, several polynomials: ML-KEM and FN-DSA verify
    lines.append("## Cùng q, nhiều đa thức\n")
    lines.append("| Ứng dụng | q | N | Số đa thức | Một làn: chu kỳ (mỗi đa thức) | Hai hệ số / từ: chu kỳ (mỗi đa thức) | "
                 "Nhanh hơn | Chu kỳ chờ bank (một làn / hai hệ số) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for app, q, logn, hmin, ks in (("ML-KEM", 3329, 8, 1, (1, 2, 3, 4)), ("FN-DSA kiểm", 12289, 9, 0, (1, 2)),
                                   ("FN-DSA kiểm", 12289, 10, 0, (1, 2))):
        for k in ks:
            polys = make_polys([q] * k, logn, hmin, rng)
            r1, c1, s1 = run(polys, logn, False, hmin, False)
            check(polys, r1, logn, hmin)
            r2, c2, s2 = run(polys, logn, False, hmin, True)
            check(polys, r2, logn, hmin)
            lines.append(f"| {app} | {q} | {1 << logn} | {k} | {c1} ({c1 / k:.0f}) | {c2} ({c2 / k:.0f}) | "
                         f"{c1 / c2:.2f}× | {s1} / {s2} |")
    # 2. distinct 31-bit primes (NTRUSolve), one lane
    lines.append("\n## Nhiều prime 31 bit (NTRUSolve), làn 32 bit: chu kỳ mỗi đa thức theo số đa thức\n")
    lines.append("Dưới N = 64 các đa thức nằm trên các tile khác nhau; từ 64 trở lên mỗi tile phục vụ mọi đa thức nên tối đa 2 "
                 "prime (2 ô modulus mỗi tile).\n")
    lines.append("| N | Số đa thức | Chu kỳ | Mỗi đa thức | So với một đa thức | Chu kỳ chờ bank |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    primes = [2147473409, 2147389441, 2147387393, 2147377153, 2147358721, 2147352577, 2147346433, 2147338241]
    for logn in (3, 4, 5, 6, 7, 8, 9):
        n = 1 << logn
        kmax = min(8, 64 // n) if n < 64 else 2
        base = None
        for k in sorted({1, 2, kmax}):
            if k > kmax:
                continue
            polys = make_polys(primes[:k], logn, 0, rng)
            res, cyc, st = run(polys, logn, False, 0, False)
            check(polys, res, logn, 0)
            base = cyc if k == 1 else base
            lines.append(f"| {n} | {k} | {cyc} | {cyc / k:.0f} | {base / (cyc / k):.2f}× | {st} |")
    (ROOT / "study" / "results" / "ntt_batch.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
