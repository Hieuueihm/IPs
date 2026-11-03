#!/bin/sh
# Minimal core regression (from the project root): regenerate tables, then run every golden case: NTT of the fixed
# profiles (vectors.txt), FFT formats 0/1/2 (vectors_fft.txt), NTT profile 3 with loaded primes (vectors_p3.txt). The
# layer table reads study/results/ntt_core_overlap.json and ntt_prime_overlap.json (model/ntt_core_overlap.py,
# model/ntt_prime_core.py).
# Fails (exit 1) unless every file runs all of its cases (one CASE line per vector line) with no error.
set -e
python scripts/gen_ntt_core.py
B=sim/core_ntt/build
mkdir -p $B
iverilog -g2012 -o $B/tb.vvp -f sim/core_ntt/sources.f
status=0
for f in vectors vectors_fft vectors_p3; do
    vvp -n $B/tb.vvp +FILE=sim/core_ntt/$f.txt > $B/$f.log
    want=$(grep -c . sim/core_ntt/$f.txt)
    ran=$(grep -c '^CASE' $B/$f.log || true)
    bad=$(grep '^CASE' $B/$f.log | grep -vc ' err=0 ' || true)
    grep '^CASE' $B/$f.log | awk '{print $3, $4, $5, $6, $7, $8, $10}'
    grep '^TOTAL' $B/$f.log
    if [ "$ran" != "$want" ] || [ "$bad" != "0" ] || ! grep -q '^TOTAL.*PASS' $B/$f.log; then
        echo "FAIL $f: $ran of $want cases ran, $bad with errors"
        status=1
    else
        echo "OK $f: $ran of $want cases"
    fi
done
exit $status
