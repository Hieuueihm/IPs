# Current accepted core baseline

**a_cg_prepare_split_baseline** — selected by the user for physical review:
prepared host, exact separated FFT post-adder, packed16 and all FFT/NTT modes.

The exact selected synthesis point is 37,917 LUT, 25,365 FF, 64 DSP,
48 RAMB18 and internal estimated WNS +1.603 ns at 5 ns. Its immutable RTL
copy and evidence hashes are in `experiments/a_cg_prepare_split_baseline/`.
Physical approval remains pending the single implementation run in
`experiments/a_cg_prepare_route/`. Production HDL is not overwritten.

That implementation has completed: 37,356 LUT, 25,367 FF, 64 DSP and
48 RAMB18. At 5 ns, internal setup WNS is -0.456 ns and hold WHS is
+0.010 ns. It does **not** close internal timing at 200 MHz. The full-boundary
timing is -3.831/-1.466 ns setup/hold, with OOC interface limitations.
Review `study/results/a_cg_prepare_route.md` and its JSON companion;
this is a retained candidate pending user review, not approved timing closure.

## Previous accepted baseline

**a_cg_host_baseline** — registered host, packed16 and all FFT/NTT modes.

The immutable RTL copy is `experiments/a_cg_host_baseline/rtl/`. Its manifest
pins the accepted source and the measured evidence from the `host` variant
of `study/results/a_cg_timing.json`.

Synthesis estimate: 36,721 LUT, 25,334 FF, 64 DSP, 48 RAMB18;
setup WNS +1.417 ns with the common 5 ns constraints. This is not post-route
timing closure. Numerical contracts remain unchanged. Production `hdl/`,
PLAN and the spec have not been overwritten.

New timing studies branch from this baseline in `experiments/a_cg_host_opt/`.
A better experimental result is a candidate for review, not an automatic
replacement of this accepted baseline.
