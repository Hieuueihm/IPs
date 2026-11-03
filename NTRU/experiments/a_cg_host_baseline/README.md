# Accepted experimental baseline: registered host + packed16

The user adopted this baseline after the five-way synthesis study.
`rtl/` is an immutable, byte-identical copy of
`experiments/a_cg_timing/host/rtl/`; `manifest.json` pins its hashes and evidence.
Production `hdl/` is not changed.

Measured with clock 5 ns read before synthesis, full host/root/data included:
36,721 LUT, 25,334 FF, 64 DSP, 48 RAMB18. Estimated setup WNS:
+1.417 ns internally and including the assumed synchronous I/O boundary.
These are synthesis estimates, not measured routed Fmax. Temporary I/O hold
is not closed by this study; see the full previous report.

Runtime modes retained: FFT/IFFT32/64/128, native NTRUGen64, NTT/INTT32,
packed16 for q<32768, and homogeneous batches. Arithmetic and roots are exact
under the existing R8 contracts. Kernel examples remain 505 clocks for packed
q12289 N1024, 217 for packed q3329 N256 hmin1, and 6508 for FFT128 N1024.

Host requests are captured first, then served. Compared with the earlier
fall-through host, this adds one load and one read clock per 128-bit host line.
Validation: 1026 vector cases, 38 four-state cases, 74 live C transform calls,
4 verified signatures and 14 byte-identical application artifacts. Only the
transform kernels are replaced in the C application replay.

Evidence: `study/results/a_cg_timing.md` / `.json` and
`study/build/a_cg_timing/host/`. Further experiments live separately in
`experiments/a_cg_host_opt/`; they do not replace this baseline automatically.
