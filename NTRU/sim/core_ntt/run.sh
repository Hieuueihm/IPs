#!/bin/sh
# Minimal NTT core regression (from the project root): regenerate tables, then run every golden case.
set -e
python scripts/gen_ntt_core.py
B=sim/core_ntt/build
mkdir -p $B
iverilog -g2012 -o $B/tb.vvp hdl/mul_ss.v hdl/tile/tile_thu.sv hdl/net/ntt_bank_net_s.sv \
    hdl/core/flex_banked_scratch.sv hdl/core_ntt/ntt_core_gen.sv hdl/core_ntt/ntt_core.sv sim/core_ntt/tb_ntt_core.sv
vvp -n $B/tb.vvp > $B/all.log
grep '^CASE' $B/all.log | awk '{print $3, $4, $5, $6, $7, $8, $10}'
grep '^TOTAL' $B/all.log
