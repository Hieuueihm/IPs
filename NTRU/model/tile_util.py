"""Tile utilization model for FlexTransform (PLAN section 16, step 3).

Question: does one multiplier tile switch efficiently between many narrow
products and one wide product?

Analytic and technology-independent. It counts leaf multiplications, useful
bit-products and compute/memory ceilings. Multiplier area proxy = P*P for a
P x P leaf. Reduction-tree, mux and reducer costs appear only as proxies;
synthesis is needed for real numbers. No FPGA/ASIC result is implied.

Run: python model/tile_util.py [--tiles 32] [--mem-bits 512]
Writes study/results/tile_util.csv and study/results/tile_util.md.
"""
import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Leaf:
    name: str
    p: int              # physical leaf multiplier is p x p
    signed_only: bool   # True: two's-complement p-bit operands only, limbs are p-1 bits
    per_tile: int       # leaves per tile (tile ~ one 32x32 equivalent)
    requested: bool     # leaf asked for in this study; others are sensitivity rows

    @property
    def limb(self):
        return self.p - 1 if self.signed_only else self.p

    @property
    def area(self):
        return self.p * self.p


LEAVES = [
    Leaf("L32 (32x32, sign-select)", 32, False, 1, True),
    Leaf("L17 (17x17, signed-only)", 17, True, 4, True),
    Leaf("L16 (16x16, sign-select)", 16, False, 4, False),
    Leaf("L33 (33x33, signed-only)", 33, True, 1, False),
]


@dataclass(frozen=True)
class Product:
    wa: int
    wb: int
    signed: bool                 # operands are two's complement (FFT) or unsigned (NTT)
    low_bits: int | None = None  # only result bits below this are needed


@dataclass(frozen=True)
class Op:
    name: str
    products: tuple              # integer products per butterfly
    read_bits: int               # data bits read per butterfly (write is the same)
    optional: bool = False


def fft(w, tw=None, optional=False):
    tw = tw or w
    name = f"FFT{w}" + (f" tw{tw}" if tw != w else "")
    return Op(name, (Product(w, tw, True),) * 4, 4 * w, optional)


def ntt(name, qbits, lane):
    return Op(name, (Product(qbits, qbits, False),), 2 * lane)


OPS = [
    ntt("NTT q=3329 (12b)", 12, 16),
    ntt("NTT q=12289 (14b)", 14, 16),
    ntt("NTT q=8380417 (23b)", 23, 32),
    # Montgomery: T = a*b, m = (T mod R)*q' mod R, U = (T + m*q)/R, R = 2^32.
    Op("NTT RNS 32b (Montgomery)",
       (Product(32, 32, False), Product(32, 32, False, low_bits=32),
        Product(32, 32, False)), 64),
    fft(32), fft(64), fft(128),
    fft(64, 32, optional=True), fft(128, 64, optional=True),
]


# ---------------------------------------------------------------- counting

def n_limbs(width, leaf):
    return ceil(width / leaf.limb)


def leaf_pairs(prod, leaf):
    la, lb = n_limbs(prod.wa, leaf), n_limbs(prod.wb, leaf)
    pairs = [(i, j) for i in range(la) for j in range(lb)]
    if prod.low_bits is not None:
        pairs = [(i, j) for i, j in pairs if (i + j) * leaf.limb < prod.low_bits]
    return pairs


def useful_bit_products(prod):
    if prod.low_bits is None:
        return prod.wa * prod.wb
    return sum(1 for x in range(prod.wa) for y in range(prod.wb)
               if x + y < prod.low_bits)


# ------------------------------------------------- functional self-check

def limbs_of(value, width, leaf, signed):
    """Split value into leaf.limb-bit limbs; only the top limb carries sign."""
    k = n_limbs(width, leaf)
    mask = (1 << leaf.limb) - 1
    enc = value % (1 << (k * leaf.limb))
    limbs = [(enc >> (leaf.limb * i)) & mask for i in range(k)]
    if signed and limbs[-1] >> (leaf.limb - 1):
        limbs[-1] -= 1 << leaf.limb
    return limbs


def fits_leaf(x, leaf):
    if leaf.signed_only:
        return -(1 << (leaf.p - 1)) <= x < (1 << (leaf.p - 1))
    return -(1 << (leaf.p - 1)) <= x < (1 << leaf.p)  # signed or unsigned p bits


def check_decomposition(seed=20261021, trials=200):
    rng = Random(seed)
    count = 0
    for leaf in LEAVES:
        for op in OPS:
            for prod in op.products:
                def rand(w):
                    if prod.signed:
                        lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
                    else:
                        lo, hi = 0, (1 << w) - 1
                    return [lo, hi, 0, 1, -1 if prod.signed else 2] + \
                        [rng.randint(lo, hi) for _ in range(trials // 10)]
                for a in rand(prod.wa):
                    for b in rand(prod.wb)[:8]:
                        la = limbs_of(a, prod.wa, leaf, prod.signed)
                        lb = limbs_of(b, prod.wb, leaf, prod.signed)
                        assert all(fits_leaf(x, leaf) for x in la + lb), (leaf, prod)
                        acc = sum((la[i] * lb[j]) << (leaf.limb * (i + j))
                                  for i, j in leaf_pairs(prod, leaf))
                        if prod.low_bits is None:
                            assert acc == a * b, (leaf, prod, a, b)
                        else:
                            m = (1 << prod.low_bits) - 1
                            assert acc & m == (a * b) & m, (leaf, prod, a, b)
                        count += 1
    return count


# ------------------------------------------------------------------ model

def evaluate(tiles, mem_bits, extra_mem=(1024, 2048)):
    rows = []
    for leaf in LEAVES:
        total_leaves = tiles * leaf.per_tile
        total_area = total_leaves * leaf.area
        for op in OPS:
            pairs = [leaf_pairs(p, leaf) for p in op.products]
            leaves_bf = sum(len(x) for x in pairs)
            useful = sum(useful_bit_products(p) for p in op.products)
            util = Fraction(useful, leaves_bf * leaf.area)
            compute_bf = Fraction(total_leaves, leaves_bf)
            mem_bf = Fraction(mem_bits, op.read_bits)
            eff = min(compute_bf, mem_bf)
            pp_max = max(len(x) for x in pairs)
            row = {
                "leaf": leaf.name,
                "requested": leaf.requested,
                "op": op.name,
                "optional": op.optional,
                "leaves_per_bf": leaves_bf,
                "pp_per_product": pp_max,
                "tree_in_bits_proxy": pp_max * 2 * leaf.p,
                "bit_util": float(util),
                "compute_bf": float(compute_bf),
                "mem_bf": float(mem_bf),
                "eff_bf": float(eff),
                "bound": "compute" if compute_bf < mem_bf else
                         ("memory" if mem_bf < compute_bf else "both"),
                "leaves_busy": float(eff * leaves_bf / total_leaves),
                "eff_bf_per_32k_area": float(eff * 32768 / total_area),
                "mult_area_proxy": total_area,
            }
            for mb in extra_mem:
                row[f"eff_bf_mem{mb}"] = float(
                    min(compute_bf, Fraction(mb, op.read_bits)))
            rows.append(row)
    return rows


def group_sizes(rows, leaf_name):
    return sorted({r["pp_per_product"] for r in rows
                   if r["leaf"] == leaf_name and not r["optional"]})


# ----------------------------------------------------------------- output

def pct(x):
    return f"{100 * x:.1f}%"


def num(x):
    return f"{x:.3g}"


def markdown(rows, tiles, mem_bits):
    out = []
    out.append(f"Cấu hình: {tiles} tile, bộ nhớ {mem_bits} bit đọc/chu kỳ "
               f"(ghi bằng đọc). Diện tích bộ nhân proxy = P² mỗi leaf.\n")
    out.append("### Bảng chính: leaf được yêu cầu\n")
    head = ("| Leaf | Phép | Leaf/butterfly | Tích riêng/tích | Hiệu suất bit | "
            "Trần tính toán | Trần bộ nhớ | Đạt được | Giới hạn | Leaf bận | "
            "BF/chu kỳ trên 32k diện tích |")
    out.append(head)
    out.append("|" + "---|" * 11)
    for r in rows:
        if not r["requested"] or r["optional"]:
            continue
        out.append(f"| {r['leaf']} | {r['op']} | {r['leaves_per_bf']} | "
                   f"{r['pp_per_product']} | {pct(r['bit_util'])} | "
                   f"{num(r['compute_bf'])} | {num(r['mem_bf'])} | {num(r['eff_bf'])} | "
                   f"{r['bound']} | {pct(r['leaves_busy'])} | "
                   f"{num(r['eff_bf_per_32k_area'])} |")
    out.append("\n### Độ nhạy: băng thông bộ nhớ (butterfly/chu kỳ đạt được)\n")
    out.append(f"| Leaf | Phép | {mem_bits} bit | 1024 bit | 2048 bit |")
    out.append("|---|---|---|---|---|")
    for r in rows:
        if r["optional"]:
            continue
        out.append(f"| {r['leaf']} | {r['op']} | {num(r['eff_bf'])} | "
                   f"{num(r['eff_bf_mem1024'])} | {num(r['eff_bf_mem2048'])} |")
    out.append("\n### Độ nhạy: cách xử lý dấu ở leaf và twiddle hẹp\n")
    out.append("| Leaf | Phép | Leaf/butterfly | Hiệu suất bit | Đạt được | "
               "BF/chu kỳ trên 32k diện tích | Diện tích bộ nhân |")
    out.append("|---|---|---|---|---|---|---|")
    for r in rows:
        if r["requested"] and not r["optional"]:
            continue
        out.append(f"| {r['leaf']} | {r['op']} | {r['leaves_per_bf']} | "
                   f"{pct(r['bit_util'])} | {num(r['eff_bf'])} | "
                   f"{num(r['eff_bf_per_32k_area'])} | {r['mult_area_proxy']} |")
    out.append("\n### Proxy chi phí ghép\n")
    out.append("| Leaf | Các kích thước nhóm (tích riêng/tích) | "
               "Bit vào cây gom, tích rộng nhất (proxy) |")
    out.append("|---|---|---|")
    for leaf in LEAVES:
        widest = max((r for r in rows if r["leaf"] == leaf.name and not r["optional"]),
                     key=lambda r: r["pp_per_product"])
        out.append(f"| {leaf.name} | {group_sizes(rows, leaf.name)} | "
                   f"{widest['tree_in_bits_proxy']} ({widest['op']}) |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tiles", type=int, default=32)
    ap.add_argument("--mem-bits", type=int, default=512)
    ap.add_argument("--out", type=Path, default=ROOT / "study" / "results")
    args = ap.parse_args()

    n = check_decomposition()
    print(f"Self-check: {n} limb decompositions reproduce the exact product.")

    rows = evaluate(args.tiles, args.mem_bits)
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "tile_util.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = markdown(rows, args.tiles, args.mem_bits)
    (args.out / "tile_util.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
