#!/bin/sh
# Minimal core regression (from the project root): regenerate tables, then run every golden case (NTT, then FFT
# format 0). The layer table reads study/results/ntt_core_overlap.json (model/ntt_core_overlap.py).
set -e
python scripts/gen_ntt_core.py
B=sim/core_ntt/build
mkdir -p $B
iverilog -g2012 -o $B/tb.vvp hdl/mul_ss.v hdl/tile/tile_thu.sv hdl/net/ntt_bank_net_s.sv \
    hdl/core/flex_banked_scratch.sv hdl/core_ntt/ntt_core_gen.sv hdl/core_ntt/ntt_core.sv \
    sim/core_ntt/tb_ntt_core.sv
vvp -n $B/tb.vvp > $B/all.log
vvp -n $B/tb.vvp +FILE=sim/core_ntt/vectors_fft.txt > $B/fft.log
grep '^CASE' $B/all.log | awk '{print $3, $4, $5, $6, $7, $8, $10}'
grep '^TOTAL' $B/all.log
grep '^CASE' $B/fft.log | awk '{print $3, $4, $5, $6, $7, $8, $10}'
grep '^TOTAL' $B/fft.log
