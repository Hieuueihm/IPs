"""Inter-tile composition model for FlexTransform (PLAN section 16, step 4).

Tiles are L32: one 32x32 sign-select multiplier each (docs/tile_analysis.md).
Wide FFT products are composed *between* tiles by a binary reduction tree over
the tile index with fixed shifts per level; each mode only chooses the level
where results are tapped (and the add/sub at level 0).

    level:   0     1     2     3     4
    shift:   0    32    32    64    64   (bits; weight of the higher child)

Tile index t (bits t0..t4): t0 selects the pair member of a complex-multiply
output (Re = br*wr - bi*wi, Im = br*wi + bi*wr), the next bits select limb
indices (i of data, j of twiddle) ordered by weight, the remaining high bits
select the output slot (butterfly, Re/Im). The model checks that this mapping
exists for every mode, reproduces the exact complex product and Q-format
rounding (round-half-up, the R8 rule), and reports node widths, tap
points, rounders, operand fan-in and throughput.

Run: python model/intertile_model.py
Writes study/results/intertile_*.csv and study/results/intertile.md.
"""
import csv
from dataclasses import dataclass
from fractions import Fraction
from math import log2
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent
LIMB = 32
SHIFT = [0, 32, 32, 64, 64, 128]   # level 5 only exists for K = 64; unused by any mode
MEM_BITS = 512                      # data read per cycle (PLAN 6.2)


@dataclass(frozen=True)
class Mode:
    name: str
    wd: int          # data width per real component, Q(wd-fd).fd
    fd: int
    wt: int          # twiddle width per real component, Q(wt-ft).ft
    ft: int
    optional: bool = False

    @property
    def ld(self):
        return self.wd // LIMB

    @property
    def lt(self):
        return self.wt // LIMB

    @property
    def tiles_per_output(self):
        return 2 * self.ld * self.lt


MODES = [
    Mode("FFT32", 32, 16, 32, 30),
    Mode("FFT64", 64, 32, 64, 62),
    Mode("FFT128", 128, 64, 128, 126),
    Mode("FFT64 tw32", 64, 32, 32, 30, optional=True),
    Mode("FFT128 tw64", 128, 64, 64, 62, optional=True),
]


# ------------------------------------------------------------------ mapping

def index_bits(mode):
    """Limb-index bits ordered by weight: (name, weight)."""
    bits = []
    for k in range(int(log2(mode.ld))):
        bits.append((f"i{k}", LIMB << k))
    for k in range(int(log2(mode.lt))):
        bits.append((f"j{k}", LIMB << k))
    return sorted(bits, key=lambda b: (b[1], b[0]))


def build_mapping(mode, k_tiles):
    """Return (tap, phases_per_output, rows) where rows describe every tile/phase."""
    tpo = mode.tiles_per_output
    tap = int(log2(tpo))                      # number of tree levels used per output
    bits = index_bits(mode)
    assert len(bits) == tap - 1
    for level, (_, weight) in enumerate(bits, start=1):
        if SHIFT[level] != weight:
            raise ValueError(f"{mode.name}: level {level} needs shift {weight}, "
                             f"tree has {SHIFT[level]}")
    span = min(tpo, k_tiles)
    pass_per_output = tpo // span             # >1 means accumulation over passes
    outputs_per_pass = k_tiles // span
    slots_total = 2                           # Re and Im of one butterfly per "pair"
    rows = []
    # Butterflies per issue group: enough to fill the array in one or more passes.
    n_out = max(outputs_per_pass, 2)          # at least Re and Im of one butterfly
    for out in range(n_out):
        bf, comp = divmod(out, slots_total)   # comp 0 = Re, 1 = Im
        for local in range(tpo):
            member = local & 1
            idx = {"i0": 0, "i1": 0, "j0": 0, "j1": 0}
            for level, (name, _) in enumerate(bits, start=1):
                idx[name] = (local >> level) & 1
            i = idx["i0"] + 2 * idx["i1"]
            j = idx["j0"] + 2 * idx["j1"]
            # Pair members: Re: (br*wr, -bi*wi); Im: (br*wi, +bi*wr)
            if comp == 0:
                d, t, sign = ("br", "wr", +1) if member == 0 else ("bi", "wi", -1)
            else:
                d, t, sign = ("br", "wi", +1) if member == 0 else ("bi", "wr", +1)
            flat = out * tpo + local
            phase, tile = divmod(flat, k_tiles)
            rows.append({
                "mode": mode.name, "K": k_tiles, "phase": phase, "tile": tile,
                "bf": bf, "out": "Re" if comp == 0 else "Im",
                "data": d, "i": i, "a_signed": int(i == mode.ld - 1),
                "tw": t, "j": j, "b_signed": int(j == mode.lt - 1),
                "sign": sign, "weight": LIMB * (i + j),
            })
    return tap, pass_per_output, rows


# ------------------------------------------------------------- arithmetic

def limb(value, width, idx, top_signed):
    enc = value % (1 << width)
    x = (enc >> (LIMB * idx)) & ((1 << LIMB) - 1)
    if top_signed and x >> (LIMB - 1):
        x -= 1 << LIMB
    return x


def round_half_up(value, shift):
    """Round-to-nearest, ties toward +inf: floor((v + 2^(s-1)) / 2^s), as R8 fpr_mul."""
    if shift == 0:
        return value
    return (value + (1 << (shift - 1))) >> shift


def reduce_tree(values, tap, l0_sign):
    """values: per-tile products of one output (len 2^tap), returns node values per level."""
    levels = [list(values)]
    cur = list(values)
    for level in range(tap):
        nxt = []
        for k in range(0, len(cur), 2):
            lo, hi = cur[k], cur[k + 1]
            if level == 0:
                nxt.append(lo + l0_sign * hi)          # add/sub at level 0
            else:
                nxt.append(lo + (hi << SHIFT[level]))
        cur = nxt
        levels.append(cur)
    return levels


def check_mode(mode, k_tiles, rng, trials=400):
    tap, passes, rows = build_mapping(mode, k_tiles)
    tpo = mode.tiles_per_output
    lo_d, hi_d = -(1 << (mode.wd - 1)), (1 << (mode.wd - 1)) - 1
    lo_t, hi_t = -(1 << (mode.wt - 1)), (1 << (mode.wt - 1)) - 1
    corners_d = [lo_d, lo_d + 1, -1, 0, 1, hi_d, 1 << (mode.wd - 2)]
    corners_t = [lo_t, -(1 << mode.ft), 0, 1 << mode.ft, hi_t]   # -1.0, 0, +1.0 included
    n_out = len(rows) // tpo
    n_bf = (n_out + 1) // 2
    node_min = [[0] * 1 for _ in range(tap + 1)]
    ext = [[None, None] for _ in range(tap + 1)]
    checks = 0

    def one(ops):
        nonlocal checks
        for out in range(n_out):
            sel = rows[out * tpo:(out + 1) * tpo]
            bf = sel[0]["bf"]
            o = ops[bf]
            prods = []
            for r in sel:
                a = limb(o[r["data"]], mode.wd, r["i"], r["a_signed"])
                b = limb(o[r["tw"]], mode.wt, r["j"], r["b_signed"])
                prods.append(a * b)
            l0_sign = -1 if sel[0]["out"] == "Re" else +1
            levels = reduce_tree(prods, tap, l0_sign)
            for lv, vals in enumerate(levels):
                for v in vals:
                    e = ext[lv]
                    e[0] = v if e[0] is None else min(e[0], v)
                    e[1] = v if e[1] is None else max(e[1], v)
            got = levels[-1][0]
            if sel[0]["out"] == "Re":
                exact = o["br"] * o["wr"] - o["bi"] * o["wi"]
            else:
                exact = o["br"] * o["wi"] + o["bi"] * o["wr"]
            assert got == exact, (mode.name, out, got, exact)
            # Q-format rounding: product has fd+ft fraction bits, result fd (half-up, R8 rule).
            ref = round_half_up(exact, mode.ft)
            assert round_half_up(got, mode.ft) == ref
            frac = Fraction(exact, 1 << mode.ft)
            assert ref - Fraction(1, 2) <= frac < ref + Fraction(1, 2)
            checks += 1

    for br in corners_d:
        for wr in corners_t:
            ops = [{"br": br, "bi": corners_d[(k + 3) % len(corners_d)],
                    "wr": wr, "wi": corners_t[(k + 1) % len(corners_t)]}
                   for k in range(n_bf)]
            one(ops)
    for _ in range(trials):
        ops = [{"br": rng.randint(lo_d, hi_d), "bi": rng.randint(lo_d, hi_d),
                "wr": rng.randint(lo_t, hi_t), "wi": rng.randint(lo_t, hi_t)}
               for _ in range(n_bf)]
        one(ops)
    return tap, passes, rows, checks


# ------------------------------------------------------------ width bounds

def signed_bits(lo, hi):
    n = 1
    while not (-(1 << (n - 1)) <= lo and hi <= (1 << (n - 1)) - 1):
        n += 1
    return n


def node_bounds(mode, tap):
    """Interval bound of every tree level for one output (worst case over Re/Im)."""
    def limb_range(idx, top, width):
        if idx == top:
            return -(1 << (LIMB - 1)), (1 << (LIMB - 1)) - 1
        return 0, (1 << LIMB) - 1

    out = []
    for comp in ("Re", "Im"):
        _, _, rows = build_mapping(mode, 1 << 10)
        sel = [r for r in rows if r["out"] == comp][:mode.tiles_per_output]
        cur = []
        for r in sel:
            a = limb_range(r["i"], mode.ld - 1, mode.wd)
            b = limb_range(r["j"], mode.lt - 1, mode.wt)
            cands = [x * y for x in a for y in b]
            cur.append((min(cands), max(cands)))
        levels = [cur]
        for level in range(tap):
            nxt = []
            for k in range(0, len(cur), 2):
                (l0, h0), (l1, h1) = cur[k], cur[k + 1]
                if level == 0:
                    s = -1 if comp == "Re" else 1
                    c = [l0 + s * l1, l0 + s * h1, h0 + s * l1, h0 + s * h1]
                    nxt.append((min(c), max(c)))
                else:
                    sh = SHIFT[level]
                    nxt.append((l0 + (l1 << sh), h0 + (h1 << sh)))
            cur = nxt
            levels.append(cur)
        out.append(levels)
    widths = []
    for lv in range(tap + 1):
        lo = min(x[0] for comp in out for x in comp[lv])
        hi = max(x[1] for comp in out for x in comp[lv])
        widths.append(signed_bits(lo, hi))
    return widths


# ------------------------------------------------------------------ fan-in

def operand_lanes(row, mode):
    """32-bit lane of the flat operand vectors (data: br|bi per bf, twiddle: wr|wi)."""
    d = (row["bf"] * 2 * mode.wd + (0 if row["data"] == "br" else mode.wd)
         + LIMB * row["i"]) // LIMB
    t = (row["bf"] * 2 * mode.wt + (0 if row["tw"] == "wr" else mode.wt)
         + LIMB * row["j"]) // LIMB
    return d, t


# ------------------------------------------------------------------- main

def main():
    rng = Random(20261021)
    out_dir = ROOT / "study" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary, all_rows, widths_tbl = [], [], []
    fanin = {}
    for k_tiles in (16, 32, 64):
        for mode in MODES:
            tap, passes, rows, checks = check_mode(mode, k_tiles, rng)
            tpo = mode.tiles_per_output
            outputs_per_cycle = Fraction(k_tiles, tpo)
            compute_bf = outputs_per_cycle / 2
            mem_bf = Fraction(MEM_BITS, 4 * mode.wd)
            eff = min(compute_bf, mem_bf)
            phases = max(r["phase"] for r in rows) + 1
            summary.append({
                "K": k_tiles, "mode": mode.name, "optional": mode.optional,
                "tiles_per_output": tpo, "tap_level": tap,
                "passes_per_output": passes, "accumulator": passes > 1,
                "phases_per_issue": phases,
                "compute_bf": float(compute_bf), "mem_bf": float(mem_bf),
                "eff_bf": float(eff),
                "busy": float(eff * 2 * tpo / k_tiles),
                "checks": checks,
            })
            if k_tiles == 32:
                all_rows += rows
                w = node_bounds(mode, tap)
                widths_tbl.append({"mode": mode.name, "tap": tap, "widths": w})
                for r in rows:
                    d, t = operand_lanes(r, mode)
                    s = fanin.setdefault(r["tile"], {"a": set(), "b": set()})
                    s["a"].add((mode.name, d))
                    s["b"].add((mode.name, t))

    with open(out_dir / "intertile_map_k32.csv", "w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        wcsv.writeheader()
        wcsv.writerows(all_rows)
    with open(out_dir / "intertile_summary.csv", "w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(summary[0]))
        wcsv.writeheader()
        wcsv.writerows(summary)

    # Hardware width per level = max over modes that use the level.
    n_levels = 5
    hw = []
    for lv in range(1, n_levels + 1):
        need = [t["widths"][lv] for t in widths_tbl if t["tap"] >= lv]
        node_w = max(need)
        add_w = node_w - SHIFT[lv - 1] if lv > 1 else node_w
        hw.append((lv, 32 >> lv, node_w, add_w))
    adder_bits = sum(n * a for _, n, _, a in hw)

    taps = {}
    for t in widths_tbl:
        taps.setdefault(t["tap"], []).append(t["mode"])
    rounders = [(lv, 32 >> lv, max(t["widths"][lv] for t in widths_tbl if t["tap"] == lv),
                 taps[lv]) for lv in sorted(taps)]

    fan_a = [len({x for x in v["a"]}) for v in fanin.values()]
    fan_b = [len({x for x in v["b"]}) for v in fanin.values()]
    distinct_a = [len({lane for _, lane in v["a"]}) for v in fanin.values()]
    distinct_b = [len({lane for _, lane in v["b"]}) for v in fanin.values()]

    md = []
    md.append("Model ghép liên tile, tile L32; cây nhị phân dịch cố định "
              f"{SHIFT[:5]} bit; bộ nhớ {MEM_BITS} bit đọc/chu kỳ.\n")
    md.append("### Throughput và điểm lấy kết quả\n")
    md.append("| K | Mode | Tile/đầu ra | Tap (cấp) | Lượt/đầu ra | Accumulator | Lượt/nhóm phát | "
              "BF/chu kỳ tính toán | BF/chu kỳ bộ nhớ | Đạt được | Tile bận | Kiểm tra |")
    md.append("|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for s in summary:
        md.append(f"| {s['K']} | {s['mode']}{' (tùy chọn)' if s['optional'] else ''} | "
                  f"{s['tiles_per_output']} | {s['tap_level']} | {s['passes_per_output']} | "
                  f"{'có' if s['accumulator'] else 'không'} | {s['phases_per_issue']} | "
                  f"{s['compute_bf']:.3g} | {s['mem_bf']:.3g} | {s['eff_bf']:.3g} | "
                  f"{100 * s['busy']:.0f}% | {s['checks']} |")
    md.append("\n### Độ rộng nút cây (K = 32, bit có dấu, chặn trên giải tích)\n")
    md.append("| Mode | " + " | ".join(f"Cấp {lv}" for lv in range(6)) + " |")
    md.append("|---|" + "---:|" * 6)
    for t in widths_tbl:
        cells = [str(t["widths"][lv]) if lv < len(t["widths"]) else "—" for lv in range(6)]
        md.append(f"| {t['mode']} | " + " | ".join(cells) + " |")
    md.append("\n### Phần cứng cây gom (K = 32)\n")
    md.append("| Cấp | Số nút | Độ rộng nút | Độ rộng bộ cộng (bỏ bit thấp đi thẳng) | Phép |")
    md.append("|---:|---:|---:|---:|---|")
    for lv, n, node_w, add_w in hw:
        md.append(f"| {lv} | {n} | {node_w} | {add_w} | "
                  f"{'cộng/trừ' if lv == 1 else f'cộng, dịch {SHIFT[lv - 1]}'} |")
    md.append(f"\nTổng bit bộ cộng: {adder_bits}.\n")
    md.append("### Bộ làm tròn theo điểm tap (K = 32)\n")
    md.append("| Cấp tap | Số đầu ra/chu kỳ | Độ rộng vào | Mode dùng |")
    md.append("|---:|---:|---:|---|")
    for lv, n, w, ms in rounders:
        md.append(f"| {lv} | {n} | {w} | {', '.join(ms)} |")
    md.append(f"\nNếu mỗi điểm tap có bộ làm tròn riêng: {sum(n for _, n, _, _ in rounders)} bộ, "
              f"tổng {sum(n * w for _, n, w, _ in rounders)} bit vào.\n")
    md.append("### Fan-in toán hạng mỗi tile (K = 32, mọi mode FFT)\n")
    md.append(f"- Ngõ dữ liệu: tối đa {max(distinct_a)} lane 32 bit khác nhau, "
              f"trung bình {sum(distinct_a) / len(distinct_a):.2f}.")
    md.append(f"- Ngõ twiddle: tối đa {max(distinct_b)} lane, "
              f"trung bình {sum(distinct_b) / len(distinct_b):.2f}.")
    md.append("- Lane = vị trí 32 bit trong vector toán hạng đóng gói (br|bi mỗi butterfly, wr|wi). "
              "Chưa tối ưu thứ tự đóng gói; NTT chưa tính.")
    text = "\n".join(md) + "\n"
    (out_dir / "intertile.md").write_text(text, encoding="utf-8")
    total = sum(s["checks"] for s in summary)
    print(f"Bit-exact: {total} complex-multiply outputs reproduced exactly "
          f"(and rounded half-up) across K = 16/32/64.\n")
    print(text)


if __name__ == "__main__":
    main()
