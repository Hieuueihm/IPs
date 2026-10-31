"""Root-pack banks needed when the tiles of the on-array v1 design issue at staggered phases.

On-array tile (spec 2.0, 10 section 5.1): a tile accepts one butterfly every 3 cycles. If every tile starts at the
same phase, 16 butterflies arrive together every third cycle and the bank -> tile network and the root-pack banks must
serve the full burst. Staggered: tile t accepts in cycles c with (c + PHASE[t]) mod 3 == 0, so each cycle only one
group of 5-6 tiles is fed. The tile of a butterfly stays the bank-indexed one of model/structured_net.py, and tile t
takes its k-th butterfly of a layer in its k-th accepting cycle; the tiles of one group in one cycle take a subset of
what the 16-at-once schedule took together, so data banks never conflict.

Root packs (spec 03 section 4): butterfly with root r reads pack r >> 1 (r >= 2) or the shared root-1 register
(r = 1); pack bank = (slot base + pack - 1) mod P. Two different packs in one bank in one cycle cost one extra cycle
for the whole core (as model/structured_net.py counts it). For each P and phase map the script counts every
supported case (same cases as model/structured_net.py, forward and inverse) and reports
  - cycles = 3 * (butterflies of the busiest tile) + extra cycles, against the ideal ceil(butterflies / (16/3));
  - root mux sources per tile: 2P + 1.

Run: python model/staggered_net.py   (writes study/results/staggered_net.md)
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("structured_net", ROOT / "model" / "structured_net.py")
sn = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sn)

TILES = 16
PHASES = {
    "t mod 3": [t % 3 for t in range(TILES)],
    "t // 6": [min(t // 6, 2) for t in range(TILES)],
    "(t >> 2) mod 3": [(t >> 2) % 3 for t in range(TILES)],
    "all 0 (not staggered)": [0] * TILES,
}


def run(pbanks, phase):
    bf_total = cyc_total = extra_total = 0
    worst = 1.0
    for logn, jobs in sn.cases():
        n = 1 << logn
        g_tables = max(1, n // 2 - 1)
        for inverse in (False, True):
            for layer in range(logn):
                per_tile = {}
                for j in range(jobs):
                    base = 8 * ((j * g_tables + 7) // 8)          # slot pack base, multiple of 8 (spec 03 section 6)
                    for (cx, cy, r) in sn.pairs(logn, layer, inverse):
                        t = sn.tile_of(sn.unit(j * n + cx), sn.unit(j * n + cy))
                        per_tile.setdefault(t, []).append(None if r == 1 else base + sn.pack_of(r) - 1)
                k_max = max(len(v) for v in per_tile.values())
                extra = 0
                for k in range(k_max):
                    for p in range(3):
                        banks = {}
                        for t, v in per_tile.items():
                            if phase[t] == p and k < len(v) and v[k] is not None:
                                banks.setdefault(v[k] % pbanks, set()).add(v[k])
                        if banks:
                            extra += max(len(x) for x in banks.values()) - 1
                bf = jobs * n // 2
                cyc = 3 * k_max + extra
                ideal = -(-bf * 3 // TILES)
                bf_total += bf
                cyc_total += cyc
                extra_total += extra
                worst = min(worst, ideal / cyc)
    return bf_total, cyc_total, extra_total, worst


def main():
    out = []
    say = lambda s="": (print(s), out.append(s))
    say("# Tile lệch pha và số bank gói root (v1 trên mảng)\n")
    say("Mô hình: [model/staggered_net.py](../../model/staggered_net.py). Tile t nhận butterfly ở chu kỳ có "
        "(c + pha[t]) mod 3 = 0; gán tile theo bank như [structured_net](structured_net.md). Tốc độ lý tưởng 16/3 "
        "butterfly/chu kỳ. Nguồn của mux root mỗi tile = 2P + 1.\n")
    say("| Pha | P (bank gói) | Nguồn mux root | Butterfly | Chu kỳ | Tốc độ | So với 16/3 | Chu kỳ thêm do bank gói | Tầng tệ nhất |")
    say("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, phase in PHASES.items():
        for pbanks in (8, 4, 3, 2):
            bf, cyc, extra, worst = run(pbanks, phase)
            say(f"| {name} | {pbanks} | {2 * pbanks + 1} | {bf} | {cyc} | {bf / cyc:.3f} | "
                f"{100 * bf / cyc / (16 / 3):.1f}% | {extra} | {100 * worst:.0f}% |")
    (ROOT / "study" / "results" / "staggered_net.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
