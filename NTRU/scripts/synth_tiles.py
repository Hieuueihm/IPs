"""Generic Yosys synthesis of the tile benchmarks (docs/tile_analysis.md section 7).

Maps each benchmark top to Yosys internal gates (no vendor library) and reports
cell counts, an approximate NAND2-equivalent area and the longest combinational
path in cells. Numbers are relative comparisons between configurations, not
silicon area or timing.

Run (from NTRU/):  python scripts/synth_tiles.py [--yosys PATH] [--no-booth]
Yosys is looked up as --yosys, $YOSYS, `yosys`, then `yowasp-yosys`.
Writes study/results/tile_synth.csv and study/results/tile_synth.md.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["hdl/mul_ss.v", "hdl/tile_l32.v", "hdl/tile_l16x4.v", "hdl/bench/tile_bench.v"]

# (top, label, number of 32x32-equivalent tiles it represents)
CONFIGS = [
    ("bench_u32",       "Baseline: unsigned 32x32",            1),
    ("bench_l32_corr",  "L32 sign-select (CORR)",              1),
    ("bench_l32_ext",   "L32 via extension (= 33x33 signed)",  1),
    ("bench_l16_split", "2x2 L16 sign-select, split only",     1),
    ("bench_l16_corr",  "2x2 L16 sign-select, split + fuse",   1),
    ("bench_l16_ext",   "2x2 L17 signed-only, split + fuse",   1),
]

# Approximate NAND2-equivalent weights for Yosys internal gates.
GE = {
    "$_BUF_": 0.67, "$_NOT_": 0.67,
    "$_NAND_": 1.0, "$_NOR_": 1.0,
    "$_AND_": 1.33, "$_OR_": 1.33, "$_ANDNOT_": 1.33, "$_ORNOT_": 1.33,
    "$_XOR_": 2.33, "$_XNOR_": 2.33, "$_MUX_": 2.33,
}
FF_GE = 4.67
GATES = "AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX"


def find_yosys(arg):
    for cand in (arg, os.environ.get("YOSYS"), "yosys", "yowasp-yosys"):
        if cand and shutil.which(cand):
            return shutil.which(cand)
    raise SystemExit("Yosys not found: install it or pass --yosys PATH.")


def run_one(yosys, top, booth, workdir):
    stat_json = workdir / f"{top}_stat.json"
    ltp_txt = workdir / f"{top}_ltp.txt"
    srcs = " ".join(str(ROOT / s).replace("\\", "/") for s in SOURCES)
    script = "\n".join([
        f"read_verilog -sv {srcs}",
        f"hierarchy -check -top {top}",
        f"synth -flatten {'-booth ' if booth else ''}-top {top}",
        f"abc -g {GATES}",
        "opt_clean -purge",
        f"tee -q -o {stat_json.as_posix()} stat -json",
        f"tee -q -o {ltp_txt.as_posix()} ltp -noff",
    ])
    ys = workdir / f"{top}.ys"
    ys.write_text(script, encoding="utf-8")
    res = subprocess.run([yosys, "-q", "-s", str(ys)], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"Yosys failed on {top}:\n{res.stdout}\n{res.stderr}")

    data = json.loads(stat_json.read_text(encoding="utf-8"))
    mod = data["modules"].get(top) or data["modules"].get("\\" + top) \
        or next(iter(data["modules"].values()))
    cells = mod["num_cells_by_type"]
    ff = sum(n for t, n in cells.items() if "DFF" in t)
    unknown = sorted(t for t in cells if t not in GE and "DFF" not in t)
    comb_ge = sum(GE.get(t, 0) * n for t, n in cells.items())
    m = re.search(r"length=(\d+)", ltp_txt.read_text(encoding="utf-8"))
    return {
        "cells": mod["num_cells"],
        "ff": ff,
        "comb_ge": round(comb_ge, 1),
        "total_ge": round(comb_ge + FF_GE * ff, 1),
        "depth": int(m.group(1)) if m else None,
        "unknown_types": ";".join(unknown),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yosys")
    ap.add_argument("--no-booth", action="store_true", help="skip the synth -booth run")
    ap.add_argument("--out", type=Path, default=ROOT / "study" / "results")
    args = ap.parse_args()

    yosys = find_yosys(args.yosys)
    out = subprocess.run([yosys, "-V"], capture_output=True, text=True).stdout
    ver = [ln for ln in out.splitlines() if ln.startswith("Yosys")][-1].strip()
    print(f"Using {ver}")

    flows = [("array", False)] + ([] if args.no_booth else [("booth", True)])
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for flow, booth in flows:
            base = None
            for top, label, tiles in CONFIGS:
                r = run_one(yosys, top, booth, Path(tmp))
                if top == "bench_u32":
                    base = r
                r.update({
                    "flow": flow, "top": top, "config": label,
                    "comb_ge_vs_u32": round(r["comb_ge"] / base["comb_ge"], 3),
                    "depth_vs_u32": round(r["depth"] / base["depth"], 3)
                    if r["depth"] and base["depth"] else None,
                })
                rows.append(r)
                print(f"[{flow}] {label}: comb {r['comb_ge']} GE, FF {r['ff']}, "
                      f"depth {r['depth']}")

    args.out.mkdir(parents=True, exist_ok=True)
    cols = ["flow", "top", "config", "cells", "ff", "comb_ge", "total_ge", "depth",
            "comb_ge_vs_u32", "depth_vs_u32", "unknown_types"]
    with open(args.out / "tile_synth.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    md = [f"Yosys: `{ver}`. Gate mapping `abc -g {GATES}`; "
          f"GE weights are approximate (FF = {FF_GE} GE).\n",
          "| Flow | Config | Comb GE | × u32 | FF | Total GE | Depth (cells) | × u32 |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md.append(f"| {r['flow']} | {r['config']} | {r['comb_ge']} | {r['comb_ge_vs_u32']} | "
                  f"{r['ff']} | {r['total_ge']} | {r['depth']} | {r['depth_vs_u32']} |")
    if any(r["unknown_types"] for r in rows):
        md.append("\nUnweighted cell types: " +
                  ", ".join(sorted({r['unknown_types'] for r in rows if r['unknown_types']})))
    (args.out / "tile_synth.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
