# R8 C vectors for FlexTransform

Provenance, exact hashes and build commands: `manifest.json`.
Pinned R8: `ad1e5bf7714d53230ad457364db8a46a1b459c94`, scalar fixed-point Q64.64.

- `synthetic.jsonl.gz`: 364 C kernel calls, N=1..1024 (FFT/iFFT) and N=2..1024
  (CMUL/SPLIT/MERGE), including boundaries and deterministic random inputs.
- `workload_512.jsonl.gz`, `workload_1024.jsonl.gz`: calls observed while expanding
  a generated key and signing a deterministic test message with R8 `sign_tree`.
  The final workload record contains keygen/expand/sign/verify return codes.
- `twiddle_forward_q64_64.mem`, `twiddle_inverse_q64_64.mem`: 1024 rows of 384 bits,
  concatenated real, selected imag, wrapped(real+selected imag). Big-endian hex
  text within each word; no endianness-dependent binary reinterpretation.
- `twiddle_q64_64.json`: the same words in readable root-indexed form.

Each JSONL file starts with a `rom` record: `words` is the exact 2048-word
`fpr_gm_tab` emitted by the C binary. Kernel records contain `id`, `case`, `origin`,
`op`, `logn`, `a`, optionally `b`, `out`, and optionally `out1` for SPLIT.
Every array element is a 32-digit two's-complement hex128 bit pattern.

For CMUL, both `a` and `b` have N words. For MERGE each has N/2 words.
SPLIT has N input words and N/2 words in each output. These are R8 kernel array
layouts, not a DMA stream or a cycle-level RTL stimulus specification.

Test keys/PRNG seeds are deterministic and created only for this regression.
The capture does not include NTRUGen's Q32.32 keygen arithmetic and does not
replace any C kernel with hardware. See `docs/numeric_contract.md` in the project
root and `study/results/r8_differential.md` for reproduction and coverage.
