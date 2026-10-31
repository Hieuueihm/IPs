"""Exact leaf decomposition and issue mapping for the v0.2 core proposal.

Run: python model/core_fusion_v02.py
Writes study/results/core_fusion_v02.{json,md}; no old study is overwritten.
This is an arithmetic/mapping model, not an RTL, timing or FN-DSA reference test.
"""
from itertools import product
from pathlib import Path
from random import Random
import json

ROOT = Path(__file__).resolve().parent.parent
RNG = Random(20261025)


def decode(bits, width, signed):
    if signed and bits >= 1 << (width - 1):
        return bits - (1 << width)
    return bits


def terms(x, y, width, leaf, sx, sy, shift=0):
    """Return exact sign-selected leaf operands and their product weights."""
    if width <= leaf:
        mask = (1 << leaf) - 1
        a, b = decode(x & mask, leaf, sx), decode(y & mask, leaf, sy)
        assert a == x and b == y  # includes sign extension into a larger leaf
        return [(a, b, shift)]
    half = width // 2
    mask = (1 << half) - 1
    xparts = [(x & mask, False), (x >> half, sx)]
    yparts = [(y & mask, False), (y >> half, sy)]
    out = []
    for i, (a, sa) in enumerate(xparts):
        for j, (b, sb) in enumerate(yparts):
            out.extend(terms(a, b, half, leaf, sa, sb, shift+(i+j)*half))
    return out


def assemble(parts):
    return sum((a*b) << shift for a, b, shift in parts)


def values(width, signed):
    if signed:
        return [-(1 << (width-1)), -1, 0, 1, (1 << (width-1))-1]
    return [0, 1, 1 << (width-1), (1 << width)-2, (1 << width)-1]


def sample(width, signed):
    return decode(RNG.getrandbits(width), width, signed)


def rne(x, shift):
    quotient, remainder = divmod(x, 1 << shift)
    half = 1 << (shift-1)
    return quotient + int(remainder > half or
                          (remainder == half and quotient & 1))


def check_mapping(leaf, width, butterflies):
    """Pack complete real products into issues with no physical leaf collision."""
    capacity = 32 if leaf == 32 else 128
    jobs = []
    direct = []
    for bf in range(butterflies):
        a, b, c, d = [sample(width, True) for _ in range(4)]
        direct.append((a*c, b*d, a*d, b*c))
        for component, (x, y) in enumerate([(a, c), (b, d), (a, d), (b, c)]):
            jobs.append(((bf, component), terms(x, y, width, leaf, True, True)))
    issued, received, seen_slots = 0, {}, set()
    offset = 0
    for tag, parts in jobs:
        assert len(parts) <= capacity
        if offset + len(parts) > capacity:
            issued += 1
            offset = 0
        for lane in range(offset, offset+len(parts)):
            key = (issued, lane)
            assert key not in seen_slots
            seen_slots.add(key)
        assert tag not in received
        received[tag] = assemble(parts)
        offset += len(parts)
    for bf, expected in enumerate(direct):
        p0, p1, p2, p3 = [received[(bf, k)] for k in range(4)]
        assert (p0, p1, p2, p3) == expected
        assert (p0-p1, p2+p3) == (expected[0]-expected[1], expected[2]+expected[3])
        # Exercise both possible rounding boundaries; this pins no FN-DSA contract.
        shift = width // 2
        assert (rne(p0, shift)-rne(p1, shift), rne(p2, shift)+rne(p3, shift)) == (
            rne(expected[0], shift)-rne(expected[1], shift),
            rne(expected[2], shift)+rne(expected[3], shift))
        assert (rne(p0-p1, shift), rne(p2+p3, shift)) == (
            rne(expected[0]-expected[1], shift), rne(expected[2]+expected[3], shift))
    return issued+1


def main():
    counts = {"signedness_product_cases": 0, "fft_mapping_batches": 0,
              "fft_butterflies": 0, "ntt_main_product_cases": 0}
    for leaf, width, sx, sy in product((16, 32), (16, 32, 64, 128), (False, True), (False, True)):
        pairs = list(product(values(width, sx), values(width, sy)))
        pairs += [(sample(width, sx), sample(width, sy)) for _ in range(128)]
        for x, y in pairs:
            parts = terms(x, y, width, leaf, sx, sy)
            assert len(parts) == max(1, (width//leaf)**2)
            assert assemble(parts) == x*y
            assert -(1 << (2*width)) <= assemble(parts) < (1 << (2*width))
            counts["signedness_product_cases"] += 1
    rows = []
    for leaf, width in product((16, 32), (32, 64, 128)):
        butterflies = {32: 8, 64: 2, 128: 1}[width]
        expected_issues = 2 if width == 128 else 1
        for _ in range(128):
            assert check_mapping(leaf, width, butterflies) == expected_issues
            counts["fft_mapping_batches"] += 1
            counts["fft_butterflies"] += butterflies
        rows.append({"leaf": leaf, "fft_width": width,
                     "butterflies_per_batch": butterflies, "issue_count": expected_issues})
    for leaf, (q, width) in product((16, 32), ((3329, 16), (12289, 16), (8380417, 32),
                                             (2013265921, 32), (4293918721, 32))):
        pairs = list(product((0, 1, q-1), repeat=2))
        pairs += [(RNG.randrange(q), RNG.randrange(q)) for _ in range(128)]
        for a, b in pairs:
            assert assemble(terms(a, b, width, leaf, False, False)) == a*b
            counts["ntt_main_product_cases"] += 1
    result = {"seed": 20261025, "counts": counts, "mapping": rows,
              "limits": "Exact integer products and collision-free issue mapping only; no reduction, timing, RTL/PPA or pinned FN-DSA equivalence."}
    out = ROOT / "study" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "core_fusion_v02.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    lines = ["# Core fusion v0.2 — kiểm tra số học và mapping", "",
             "Seed: 20261025. Không đo throughput RTL, Fmax, area hoặc năng lượng.", ""]
    lines += [f"- {name}: {count}" for name, count in counts.items()]
    lines += ["", "| Leaf | FFT width/component | Butterfly/batch | Lượt issue/batch |",
              "|---|---|---|---|"]
    lines += [f"| {r['leaf']} | {r['fft_width']} | {r['butterflies_per_batch']} | {r['issue_count']} |" for r in rows]
    lines += ["", "Lượt issue không phải latency. Hai contract rounding chỉ kiểm tra rằng product",
              "reconstruction giữ được giá trị đầu vào cho mỗi contract; không chứng minh hai",
              "contract tương đương nhau hoặc bit-match với FN-DSA. NTT chỉ kiểm tra tích chính,",
              "không kiểm tra reducer/context conversion. Không mô hình hóa stall, feedback,",
              "adder width nội bộ, twiddle/memory hay pipeline của core.", ""]
    (out / "core_fusion_v02.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
