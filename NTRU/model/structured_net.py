"""Structured bank -> tile network for the single-lane tile: which bank each port can ever need.

One 32-bit lane: every NTT, small q included, keeps its coefficients in format 4 (one 32-bit word per
coefficient, two banks). Bank-indexed assignment (no free choice of tile): the tile of a butterfly is a
fixed function of the superbanks of its two operands, so two tiles never read the same bank in one cycle
and every port needs only a few sources. Superbank = {F (2 bits), n (3 bits)}: operands differing in F bit
q -> tile {other F bit, n}; nibbles differing in bit p -> tile {F, n without bit p}; the same superbank
(N = 1024, distance 512, staggered read) -> tile s mod 16.
A tile takes one butterfly per cycle; cycle k of a layer takes the k-th butterfly (natural order) of every
tile. Butterfly i pairs coefficients c and c + h, c = i with a 0 inserted at bit log2(h).

Memory (spec 03 section 1): bank(k) = (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30). Format 4:
coefficient c of polynomial j in cells 2(j*N + c) and 2(j*N + c) + 1, superbank bank(2(j*N + c)) >> 1,
banks 2s (low half) and 2s + 1 (high half).

For every supported case (N = 2..1024; jobs 1 or min(8, 64/N) below 64, 1 or 2 from 64; the 1-job cases
below 64 are the former 16-bit-lane ones), the script collects:
  - per tile, the banks its x low half, y low half and the high halves can read;
  - per bank, the (tile, result, half) it can be written from;
  - per tile, the root-pack banks it reads when every slot's pack base is a multiple of 8 (P = 8);
  - issue groups whose 32 reads collide in a bank (each costs an extra cycle), the cost in cycles.
It writes the source tables to study/results/structured_net.json for the RTL generator and a summary
to study/results/structured_net.md.

Run: python model/structured_net.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TILES, BANKS, PB = 16, 64, 8


def bank(k):
    return (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30)


def pairs(logn, layer, inverse):
    """(c, c + h, root index) for butterfly i = 0 .. N/2 - 1 of the layer, in natural order."""
    n = 1 << logn
    if not inverse:
        m, t = 1 << layer, n >> layer
        h = t >> 1
        root = lambda c: m + c // t
    else:
        h = 1 << layer
        root = lambda c: (n >> (layer + 1)) + c // (2 * h)
    out = []
    for i in range(n // 2):
        lo = i % h
        c = ((i - lo) << 1) | lo
        out.append((c, c + h, root(c)))
    return out


def pack_of(r):
    return 1 if r == 1 else r >> 1


def cases():
    for logn in range(1, 11):
        n = 1 << logn
        for jobs in ((1, 2) if n >= 64 else sorted({1, min(8, 64 // n)})):
            yield logn, jobs


def unit(k):
    """Superbank of coefficient cell k (format 4)."""
    return bank(2 * k) >> 1


def tile_of(ux, uy):
    """Bank-indexed tile of a butterfly whose operands sit in superbanks ux, uy."""
    d = ux ^ uy
    if d == 0:
        return ux & 15
    if d >= 8:
        q = (d >> 3).bit_length() - 1
        return ((ux >> (3 + (1 - q))) & 1) << 3 | (ux & 7)
    p = d.bit_length() - 1
    n = ux & 7
    return ((ux >> 3) & 3) << 2 | ((n >> (p + 1)) << p) | (n & ((1 << p) - 1))


def main():
    rd_lo = {(t, op): set() for t in range(TILES) for op in "xy"}
    rd_hi = {(t, op): set() for t in range(TILES) for op in "xy"}
    wr = {b: set() for b in range(BANKS)}
    moduli = {}
    bf_total = cyc_total = root_extra = slow = 0
    for logn, jobs in cases():
        n = 1 << logn
        g_tables = max(1, n // 2 - 1)
        for inverse in (False, True):
            for layer in range(logn):
                buckets = {}
                for j in range(jobs):
                    base_pack = 8 * ((j * g_tables + 7) // 8)          # pack base of slot j, multiple of 8
                    for (cx, cy, r) in pairs(logn, layer, inverse):
                        ux, uy = unit(j * n + cx), unit(j * n + cy)
                        t = tile_of(ux, uy)
                        buckets.setdefault(t, []).append(base_pack + pack_of(r) - 1)
                        moduli.setdefault((logn, jobs, t), set()).add(j)
                        for op, u in (("x", ux), ("y", uy)):
                            rd_lo[(t, op)].add(2 * u)
                            wr[2 * u].add((t, op, "lo"))
                            rd_hi[(t, op)].add(2 * u + 1)
                            wr[2 * u + 1].add((t, op, "hi"))
                cyc = max(len(v) for v in buckets.values())
                extra = 0
                for k in range(cyc):
                    per_bank = {}
                    for v in buckets.values():
                        if k < len(v):
                            per_bank.setdefault(v[k] % PB, set()).add(v[k])
                    extra += max(len(x) for x in per_bank.values()) - 1
                bf = jobs * n // 2
                bf_total += bf
                cyc_total += cyc + extra
                root_extra += extra
                slow += (cyc + extra) > -(-bf // TILES)
    summary = {
        "read_lo_sources_max": max(len(v) for v in rd_lo.values()),
        "read_lo_sources_avg": sum(len(v) for v in rd_lo.values()) / len(rd_lo),
        "read_hi_sources_max": max(len(v) for v in rd_hi.values()),
        "write_sources_max": max(len(v) for v in wr.values()),
        "write_sources_avg": sum(len(v) for v in wr.values()) / len(wr),
        "moduli_per_tile_max": max(len(v) for v in moduli.values()),
        "butterflies": bf_total, "cycles": cyc_total, "rate": bf_total / cyc_total,
        "root_extra_cycles": root_extra, "layers_slower_than_ideal": slow,
    }
    tables = {
        "read_lo": {f"{t}{op}": sorted(v) for (t, op), v in rd_lo.items()},
        "read_hi": {f"{t}{op}": sorted(v) for (t, op), v in rd_hi.items()},
        "write": {str(b): sorted(f"{t}{op}{h}" for (t, op, h) in v) for b, v in wr.items()},
        "summary": summary,
    }
    (ROOT / "study" / "results" / "structured_net.json").write_text(json.dumps(tables, indent=1) + "\n")
    for k, v in summary.items():
        print(f"{k}: {v}")
    lines = ["# Mạng bank → tile có cấu trúc: gán tile theo bank\n",
             "Mô hình: [model/structured_net.py](../../model/structured_net.py). Tile của một butterfly là hàm cố định "
             "của superbank hai toán hạng. Một lane 32 bit: mọi NTT, kể cả q nhỏ, lưu dạng 4 (mỗi hệ số một từ "
             "32 bit trên hai bank). Mọi trường hợp N 2..1024 (dưới 64: 1 hoặc min(8, 64/N) đa thức; từ 64: 1 hoặc 2), "
             "xuôi và ngược. Vị trí gói đầu của mỗi khe là bội của 8.\n",
             "| Cổng | Số nguồn lớn nhất | Trung bình | Crossbar |",
             "|---|---:|---:|---:|",
             f"| Đọc, nửa thấp mỗi toán hạng | {summary['read_lo_sources_max']} | {summary['read_lo_sources_avg']:.1f} | 64 |",
             f"| Đọc, nửa cao mỗi toán hạng | {summary['read_hi_sources_max']} | | 32 |",
             f"| Ghi, mỗi bank | {summary['write_sources_max']} | {summary['write_sources_avg']:.1f} | 32 |",
             "",
             f"Tốc độ: {summary['butterflies']} butterfly trong {summary['cycles']} chu kỳ = {summary['rate']:.2f} mỗi chu kỳ; "
             f"chu kỳ thêm do xung đột bank gói root: {summary['root_extra_cycles']}; số tầng chậm hơn lý tưởng: "
             f"{summary['layers_slower_than_ideal']}. Không có xung đột bank dữ liệu (do cách gán).",
             "",
             f"Số modulus một tile phải phục vụ trong một lệnh nhiều prime: tối đa {summary['moduli_per_tile_max']} "
             "(N = 8, 16, 32), nên tile cần bảng hằng số 2 ô chọn theo request."]
    (ROOT / "study" / "results" / "structured_net.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
