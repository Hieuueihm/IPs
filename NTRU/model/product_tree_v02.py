"""Per-real-product reduction tree check for ARCHITECTURE.md v0.2 (review 2026-10-25).

v0.2 reconstructs each real product exactly before Re/Im recombination. This
checks that the fixed-shift binary tree of the v0.1 inter-tile model still
works per real product: limb-index bits ordered by weight give one shift per
level, shared by every width, for leaf g = 16 and g = 32:

    g = 32: levels shift [32, 32, 64, 64]          (tap: W=64 at 2, W=128 at 4)
    g = 16: levels shift [16, 16, 32, 32, 64, 64]  (tap: W=32 at 2, 64 at 4, 128 at 6)

It also reports node widths (analytic bounds), adder bits, and the width of
Re/Im recombination after rounding each real product to Q(W-F).F when the
twiddle is a unit-bounded Q(W-F).F value (4M, round-half-up as in R8).
Superseded for the pinned contract (3M, wrap 2^W, dropped high terms) by
model/arch_checks.py; kept for the 4M width comparison.

Run: python model/product_tree_v02.py
"""
from random import Random

WIDTHS = (32, 64, 128)


def shifts(g, levels):
    return [g << (k // 2) for k in range(levels)]


def limbs(v, w, g):
    k = w // g
    enc = v % (1 << w)
    out = [(enc >> (g * i)) & ((1 << g) - 1) for i in range(k)]
    if out[-1] >> (g - 1):
        out[-1] -= 1 << g
    return out


def tree_order(w, g):
    """Leaf order: bit 2m of the leaf index = i_m, bit 2m+1 = j_m (weights g*2^m)."""
    k = w // g
    nb = k.bit_length() - 1
    order = []
    for t in range(k * k):
        i = sum(((t >> (2 * m)) & 1) << m for m in range(nb))
        j = sum(((t >> (2 * m + 1)) & 1) << m for m in range(nb))
        order.append((i, j))
    return order, 2 * nb


def reduce(vals, sh):
    levels = [vals]
    for s in sh:
        vals = [vals[k] + (vals[k + 1] << s) for k in range(0, len(vals), 2)]
        levels.append(vals)
    return levels


def signed_bits(lo, hi):
    n = 1
    while not (-(1 << (n - 1)) <= lo and hi < (1 << (n - 1))):
        n += 1
    return n


def bounds(w, g):
    order, nlev = tree_order(w, g)
    k = w // g
    rng = lambda idx: (-(1 << (g - 1)), (1 << (g - 1)) - 1) if idx == k - 1 else (0, (1 << g) - 1)
    cur = []
    for i, j in order:
        c = [x * y for x in rng(i) for y in rng(j)]
        cur.append((min(c), max(c)))
    widths = [signed_bits(min(a for a, _ in cur), max(b for _, b in cur))]
    for s in shifts(g, nlev):
        cur = [(cur[q][0] + (cur[q + 1][0] << s), cur[q][1] + (cur[q + 1][1] << s))
               for q in range(0, len(cur), 2)]
        widths.append(signed_bits(min(a for a, _ in cur), max(b for _, b in cur)))
    return widths, shifts(g, nlev)


def rne(v, s):
    """Round-half-up (R8 rule): floor((v + 2^(s-1)) / 2^s). Name kept for history."""
    return (v + (1 << (s - 1))) >> s


def main():
    rnd = Random(20261025)
    total = 0
    print("| Leaf | W | Leaf/tích | Tap (cấp) | Dịch theo cấp | Độ rộng nút theo cấp | Bit cộng |")
    print("|---:|---:|---:|---:|---|---|---:|")
    for g in (32, 16):
        for w in WIDTHS:
            if w < g:
                continue
            order, nlev = tree_order(w, g)
            sh = shifts(g, nlev)
            lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
            corners = [lo, lo + 1, -1, 0, 1, hi]
            pairs = [(a, b) for a in corners for b in corners]
            pairs += [(rnd.randint(lo, hi), rnd.randint(lo, hi)) for _ in range(3000)]
            for a, b in pairs:
                la, lb = limbs(a, w, g), limbs(b, w, g)
                vals = [la[i] * lb[j] for i, j in order]
                assert reduce(vals, sh)[-1][0] == a * b, (g, w, a, b)
                total += 1
            widths, _ = bounds(w, g)
            n_nodes = [len(order) >> (lv + 1) for lv in range(nlev)]
            adder = sum(n * (widths[lv + 1] - sh[lv]) for lv, n in enumerate(n_nodes))
            print(f"| {g} | {w} | {len(order)} | {nlev} | {sh} | {widths} | {adder} |")

    # Recombination after per-product rounding, unit-bounded twiddle in the same Q format.
    print("\n| W | F | Re/Im sau làm tròn: bit cần (chặn trên, kiểm tra biên) |")
    print("|---:|---:|---:|")
    for w in WIDTHS:
        f = w // 2
        lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
        one = 1 << f
        worst = 0
        for br in (lo, hi):
            for bi in (lo, hi):
                for wr in (-one, one):
                    for wi in (-one, one, 0):
                        p = [rne(br * wr, f), rne(bi * wi, f), rne(br * wi, f), rne(bi * wr, f)]
                        for v in (p[0] - p[1], p[2] + p[3]):
                            worst = max(worst, signed_bits(min(v, 0), max(v, 0)))
        print(f"| {w} | {f} | {worst} |")
    print(f"\nBit-exact: {total} real products reproduced by the fixed-shift tree.")


if __name__ == "__main__":
    main()
