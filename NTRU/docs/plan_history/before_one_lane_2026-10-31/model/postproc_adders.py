"""Sizing of the shared post-multiplication adder bank (docs/architecture_v1.md, change 4).

Counts adder bits needed per cycle, per pipeline stage, for each mode at its peak
throughput on 64 multipliers 16x16, and compares a shared bank (per stage: the max
over modes) with separate FFT and NTT banks (per stage: FFT max + NTT max).

Stages after the multiplier (forward transforms: FFT CT, NTT CT):
  A  shared "high part + correction + carry" adder
       FFT: rounding of each real product (3 per butterfly, W+1 bits)
       NTT: u = T_high + (m*q)_high + [T_low != 0]   (1 per butterfly, R+1 bits)
  B  FFT: 3-product complex recombination (3 per butterfly, W bits)
     NTT: subtract q if u >= q                       (1 per butterfly, R+1 bits)
  C  butterfly A +/- T: FFT 4 per butterfly (W bits); NTT 2 (R+1 bits)
  D  NTT only: corrections after A+T, A-T             (2 per butterfly, R+1 bits)
Input side (before the multiplier), FFT only: data sum and twiddle sum for 3 products (2, W bits).

Hybrid reduction (architecture v1 since 31/10/2026): NTT 16 bit (q = 3329, 12289) uses the
fixed reducers, so its stages A/B sit inside each reducer and only C/D (64 butterflies per
cycle) use the shared bank. NTT 32 bit keeps the reduction on the array. `--tren-mang`
prints the earlier all-on-array sizing for comparison.

`--mot-lan`: single-lane tile (spec 2.0, 10 since 31/10/2026), the v1 design: 16 butterflies per cycle at
both widths. NTT 16 bit reduces on the array (stages A, B in the shared bank); NTT 32 bit uses one
dedicated Montgomery per tile (stages A, B inside it). Writes postproc_adders_mot_lan.md.

Run: python model/postproc_adders.py   (writes study/results/postproc_adders.md)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGES = ("pre", "A", "B", "C", "D")

# (name, domain, butterflies per cycle, word width W or residue width R)
MODES = [
    ("FFT 32 bit", "FFT", 64 / 4 / 3, 32),
    ("FFT 64 bit", "FFT", 64 / 16 / 3, 64),
    ("FFT 128 bit", "FFT", 64 / 64 / 3, 128),
    ("NTT 16 bit, bộ rút gọn hằng", "NTTD", 64, 16),
    ("NTT 32 bit, rút gọn trên mảng", "NTT", 64 / 12, 32),
]
MOT_LAN = "--mot-lan" in sys.argv
if "--tren-mang" in sys.argv:
    MODES[3] = ("NTT 16 bit, rút gọn trên mảng", "NTT", 64 / 3, 16)
if MOT_LAN:
    MODES[3] = ("NTT 16 bit, trên mảng, một làn mỗi tile", "NTT", 16, 16)
    MODES[4] = ("NTT 32 bit, bộ Montgomery riêng, một làn mỗi tile", "NTTD", 16, 32)


def per_butterfly(domain, w):
    """{stage: (count, width)}"""
    if domain == "FFT":
        return {"pre": (2, w), "A": (3, w + 1), "B": (3, w), "C": (4, w), "D": (0, 0)}
    if domain == "NTTD":                      # A, B inside the fixed reducers
        return {"pre": (0, 0), "A": (0, 0), "B": (0, 0), "C": (2, w + 1), "D": (2, w + 1)}
    return {"pre": (0, 0), "A": (1, w + 1), "B": (1, w + 1), "C": (2, w + 1), "D": (2, w + 1)}


def main():
    out = []
    say = lambda s="": (print(s), out.append(s))
    say("# Định cỡ ngân hàng cộng/trừ dùng chung\n")
    say("Bit cộng cần mỗi chu kỳ ở từng tầng, tại tốc độ đỉnh của mỗi chế độ trên 64 bộ nhân 16×16.\n")
    say("| Chế độ | Butterfly/chu kỳ | " + " | ".join(f"Tầng {s}" for s in STAGES) + " | Tổng |")
    say("|---|---:|" + "---:|" * (len(STAGES) + 1))
    need = {}
    for name, dom, bf, w in MODES:
        pb = per_butterfly(dom, w)
        row = {s: bf * c * wd for s, (c, wd) in pb.items()}
        need[name] = (dom, row)
        say(f"| {name} | {bf:.3g} | " + " | ".join(f"{row[s]:.0f}" for s in STAGES)
            + f" | {sum(row.values()):.0f} |")
    shared = {s: max(r[s] for _, r in need.values()) for s in STAGES}
    fft = {s: max(r[s] for d, r in need.values() if d == "FFT") for s in STAGES}
    ntt = {s: max(r[s] for d, r in need.values() if d != "FFT") for s in STAGES}
    sep = {s: fft[s] + ntt[s] for s in STAGES}
    say("\n| Cách bố trí | " + " | ".join(f"Tầng {s}" for s in STAGES) + " | Tổng bit cộng |")
    say("|---|" + "---:|" * (len(STAGES) + 1))
    for label, d in (("Riêng FFT (lớn nhất các chế độ FFT)", fft), ("Riêng NTT", ntt),
                     ("Hai ngân hàng riêng", sep), ("Một ngân hàng dùng chung", shared)):
        say(f"| {label} | " + " | ".join(f"{d[s]:.0f}" for s in STAGES) + f" | {sum(d.values()):.0f} |")
    saving = 1 - sum(shared.values()) / sum(sep.values())
    say(f"\nDùng chung tiết kiệm {100 * saving:.0f}% bit cộng so với hai ngân hàng riêng "
        "(chưa tính mux chọn làn và cắt chuỗi nhớ).")
    if MOT_LAN:
        say("\nNTT 32 bit với bộ Montgomery riêng: tầng A, B nằm trong 16 bộ Montgomery (cùng 7 DSP mỗi tile), không "
            "tính ở đây. Tile của RTL nghiệm thu dùng một bộ cộng/trừ cho cả CT và GS, nên tầng C, D ở đây là cận trên.")
    elif "--tren-mang" not in sys.argv:
        say("\nNTT 16 bit với bộ rút gọn hằng: tầng A, B và hai phép nhân hằng nằm trong 64 bộ rút gọn, không tính ở đây.")
    name = ("postproc_adders_mot_lan.md" if MOT_LAN else
            "postproc_adders_tren_mang.md" if "--tren-mang" in sys.argv else "postproc_adders.md")
    (ROOT / "study" / "results" / name).write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
