# Selected baseline pending physical review

The user selected the exact `prepare_split` candidate: synthesis 37,917 LUT,
25,365 FF, 64 DSP, 48 RAMB18, internal estimated WNS +1.603 ns at 5 ns.
This directory is an immutable copy of the measured source; its manifest
pins the source, synthesis checkpoint and validation evidence.

Packed16, NTT32/multi-modulus, all FFT precisions and native64 remain runtime
features. Numerical contracts, 3M products, rounding and kernel cycles are
unchanged. The prepared host adds one load and one read cycle per 128-bit line
relative to the previous registered-host baseline.

Validation: 1,026 whole-core vectors, 38 four-state cases, 100,256 adder
carry/borrow comparisons, 74 live C transform calls, four verified signatures
and 14 byte-identical C artifacts. Only transform kernels are substituted in C.

Physical review uses `experiments/a_cg_prepare_route/implement.tcl`, opening
the frozen synthesis checkpoint without resynthesis. It is a single fast
timing-driven OOC run, without board pins or a bitstream. Positive synthesis
slack is not physical timing closure. Source and production HDL stay unchanged.
