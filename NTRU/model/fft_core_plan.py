"""How complex FFT butterflies map onto the single-lane tiles (planning model, before RTL).

The architecture's section 3 / 4 describe the earlier 4-lane tile with a fusion tree; this model compares the two
families for the current core (16 tiles, each one fused 32x32 multiplier: mode 0 raw product, mode 1 rounded FFT32
product, one request per cycle, latency 6):

  (A) temporal: one tile does a whole complex butterfly. Its 3 real products (3-product complex multiply, spec 1.0
      01.1) run one after another; at 64 / 128 bit each product is the sum of its 32-bit limb products
      (4 / 15 raw products; a3*b3 has weight >= 192 and is dropped), accumulated in the tile's post-processing.
      Tile occupancy per butterfly: 3 / 12 / 45 cycles. Narrower W = more butterflies per cycle, from time.
  (B) spatial (architecture 3.1): one product spread over 1 / 4 / 16 tiles with a cross-tile sum; batches of
      16 / 4 / 1 butterflies. Numbers from model/flex_v1_projection.py as given in the architecture (section 4).

For (A) it computes, per width and N, the cycles of FFT and IFFT with a barrier per layer (IFFT scaling fused into
the last layer's writes, no extra pass), the read-to-write latency of one butterfly, and checks them against
hypothesis 3 (locked, lần 6). It also counts, for the network, the superbanks each tile port must reach when tile =
bank-indexed tile of the real pair (model/structured_net.py), with the real and the imaginary parts of an operand
on the same port, for formats 0, 1, 2; and checks the arithmetic of the 3-product butterfly against the 1.0 fixtures.

Run: python model/fft_core_plan.py   (writes study/results/fft_core_plan.md)
"""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("structured_net", ROOT / "model" / "structured_net.py")
sn = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sn)

TILES = 16
TILE_LAT = 6                      # mode 0/1 latency of the acceptance tile
RAW = {32: 1, 64: 4, 128: 15}     # tile requests per real product (FFT32 uses the rounded mode 1)
CELLS = {32: 2, 64: 4, 128: 8}    # 16-bit cells per element
H3 = {"fwd": {32: 700, 64: 2300, 128: 8500}, "inv": {32: 770, 64: 2530, 128: 9350}}
B_SPATIAL = {32: 552, 64: 1864, 128: 7496}    # architecture section 4, changes 1 + 2 + 3, N = 1024 forward


# ---------------- arithmetic (spec 1.0, 01.1 - 01.4) ----------------

def wrap(x, w):
    x &= (1 << w) - 1
    return x - (1 << w) if x >> (w - 1) else x


def mul(a, b, w):
    f = w // 2
    return wrap((a * b + (1 << (f - 1))) >> f, w)


def cmul(ar, ai, br, bi, w):
    p0, p1 = mul(ar, br, w), mul(ai, bi, w)
    p2 = mul(wrap(ar + ai, w), wrap(br + bi, w), w)
    return wrap(p0 - p1, w), wrap(wrap(p2 - p0, w) - p1, w)


def roots(w):
    rows = (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "fft_q64_64.mem").read_text().split()
    out = []
    for r in rows:
        v = int(r, 16)
        re, im = wrap(v >> 128, 128), wrap(v, 128)
        if w < 128:
            d = 64 - w // 2
            re, im = wrap((re + (1 << (d - 1))) >> d, w), wrap((im + (1 << (d - 1))) >> d, w)
        out.append((re, im))
    return out


def roots_inv(w):
    rows = (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "fft_q64_64.mem").read_text().split()
    out = []
    for r in rows:
        v = int(r, 16)
        re, im = wrap(v >> 128, 128), wrap(-wrap(v, 128), 128)
        if w < 128:
            d = 64 - w // 2
            re, im = wrap((re + (1 << (d - 1))) >> d, w), wrap((im + (1 << (d - 1))) >> d, w)
        out.append((re, im))
    return out


def fft(a, logn, w, gm):
    a = list(a)
    n = 1 << logn
    hn = n // 2
    span, groups = hn, 2
    while span >= 2:
        half = span // 2
        for g in range(groups // 2):
            wr, wi = gm[groups + g]
            for off in range(half):
                j = g * span + off
                tr, ti = cmul(a[j + half], a[j + half + hn], wr, wi, w)
                ar, ai = a[j], a[j + hn]
                a[j], a[j + hn] = wrap(ar + tr, w), wrap(ai + ti, w)
                a[j + half], a[j + half + hn] = wrap(ar - tr, w), wrap(ai - ti, w)
        span, groups = half, groups * 2
    return a


def ifft(a, logn, w, igm):
    a = list(a)
    n = 1 << logn
    hn = n // 2
    stride, groups = 1, n
    last = None
    while groups > 2:
        for g in range(groups // 4):
            wr, wi = igm[groups // 2 + g]
            for off in range(stride):
                j = 2 * g * stride + off
                ar, ai, br, bi = a[j], a[j + hn], a[j + stride], a[j + stride + hn]
                a[j], a[j + hn] = wrap(ar + br, w), wrap(ai + bi, w)
                a[j + stride], a[j + stride + hn] = cmul(wrap(ar - br, w), wrap(ai - bi, w), wr, wi, w)
        stride, groups = stride * 2, groups // 2
    s = logn - 1
    if s > 0:
        a = [wrap(x + (1 << (s - 1)), w) >> s for x in a]
    return a


def check_fixtures():
    n_ok = 0
    gm = {w: roots(w) for w in (32, 64, 128)}
    igm = {w: roots_inv(w) for w in (32, 64, 128)}
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] not in (0, 1) or c["fmt"] > 2:
            continue
        w = 32 << c["fmt"]
        a = [wrap(int(x, 16), w) for x in d["a"][0]]
        e = [wrap(int(x, 16), w) for x in d["expected"][0]]
        got = fft(a, c["logn"], w, gm[w]) if c["op"] == 0 else ifft(a, c["logn"], w, igm[w])
        assert got == e, (c, w)
        n_ok += 1
    return n_ok


# ---------------- design (A): cycles ----------------

def cycles_a(w, logn, inverse):
    """Barrier per layer. Per layer: butterflies spread over the tiles, each tile busy 3 * RAW[w] cycles per butterfly."""
    if logn < 2:
        return 0, 0
    n = 1 << logn
    layers = logn - 1
    bf = n // 4
    occ = 3 * RAW[w]
    per_tile = math.ceil(bf / TILES)
    # read 1 (RAM) + 1 (network register) + products of one butterfly + tile latency + accumulate / combine 2 + write 1
    lat = 2 + occ + TILE_LAT + 2 + 1
    # operands of one butterfly arrive over several cycles (4 * W / 64 network deliveries), overlapped with the previous
    total = layers * (per_tile * occ + lat - occ)
    return total, lat


# ---------------- design (A): network sources ----------------

def sb(cell):
    return sn.bank(cell) >> 1


def network_sources():
    """Superbanks each tile port must reach: port x = operand A (real and imaginary, all limbs), port y = operand B."""
    out = {}
    for w in (32, 64, 128):
        cpe = CELLS[w]
        ports = {(t, op): set() for t in range(TILES) for op in "xy"}
        for logn in range(2, 11):
            n = 1 << logn
            hn = n // 2
            span = hn
            while span >= 2:
                half = span // 2
                for g in range(hn // span):
                    for off in range(half):
                        j = g * span + off
                        t = sn.tile_of(sb(cpe * j), sb(cpe * (j + half)))
                        for op, e in (("x", j), ("y", j + half)):
                            for comp in (e, e + hn):
                                for limb in range(cpe // 2):
                                    ports[(t, op)].add(sb(cpe * comp + 2 * limb))
                span = half
        out[w] = ports
    union = {k: set().union(*(out[w][k] for w in out)) for k in out[32]}
    return out, union


def main():
    n_ok = check_fixtures()
    lines = ["# FFT trên tile một làn: hai cách đặt (mô hình trước RTL)\n",
             f"Mô hình: [model/fft_core_plan.py](../../model/fft_core_plan.py). Số học butterfly 3 tích kiểm lại với {n_ok} ca "
             "vàng FFT / FFT ngược của 1.0 (định dạng 0, 1, 2, logn 0..10): khớp hết.\n",
             "## Chu kỳ, N = 1024 (giả thuyết 3, khóa lần 6)\n",
             "| W | (A) xuôi | (A) ngược | (A) độ trễ đọc → ghi | (B) xuôi (kiến trúc mục 4) | Ngưỡng xuôi / ngược |",
             "|---:|---:|---:|---:|---:|---:|"]
    res = {}
    for w in (32, 64, 128):
        f, lat = cycles_a(w, 10, False)
        i, _ = cycles_a(w, 10, True)
        res[w] = (f, i, lat)
        lines.append(f"| {w} | {f} | {i} | {lat} | {B_SPATIAL[w]} | {H3['fwd'][w]} / {H3['inv'][w]} |")
    r128_32 = res[128][0] / res[32][0]
    r128_64 = res[128][0] / res[64][0]
    f512 = {w: cycles_a(w, 9, False)[0] for w in (32, 128)}
    lines.append(f"\n(A): tỉ lệ 128 / 32 bit = {r128_32:.1f} (ngưỡng ≥ 10; N512 {f512[128] / f512[32]:.1f}, ngưỡng ≥ 8), "
                 f"128 / 64 bit = {r128_64:.1f} (ngưỡng ≥ 3). Độ trễ đọc → ghi của một butterfly: "
                 f"{res[32][2]} / {res[64][2]} / {res[128][2]} chu kỳ (điều kiện của giả thuyết 3: ≤ 24).\n")
    per, union = network_sources()
    lines.append("## Mạng: số siêu bank mỗi cổng tile phải tới (A), tile = tile của cặp phần thực\n")
    lines.append("| Định dạng | Lớn nhất | Trung bình | NTT hiện tại (mỗi nửa) |")
    lines.append("|---|---:|---:|---:|")
    for w in (32, 64, 128):
        v = [len(s) for s in per[w].values()]
        lines.append(f"| W = {w} | {max(v)} | {sum(v) / len(v):.1f} | 6 / 4,5 |")
    v = [len(s) for s in union.values()]
    lines.append(f"| Hợp ba độ rộng | {max(v)} | {sum(v) / len(v):.1f} | |")
    (ROOT / "study" / "results" / "fft_core_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
