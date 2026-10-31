# Prototype arithmetic bank: F16 / R32

- Simulation: 1335 transactions ×3 configurations; 0 mismatches.
- 189 complex 3M results recomposed from RTL products match actual C R8.
- Input/output registers: II=1, two sampled clock edges; bubbles and mode changes checked.

| Top | Comb GE | FF | Total GE | Longest gate path | NTT16 lanes |
|---|---:|---:|---:|---:|---:|
| proto_r32 | 232643.9 | 3078 | 247018.1 | 434 | 16 |
| proto_f16_common | 250528.7 | 3078 | 264903.0 | 445 | 16 |
| proto_f16_wide | 324694.8 | 6118 | 353265.8 | 807 | 64 |

F16 common/R32 total GE: 1.072×; F16 wide/R32: 1.430×.
Peak narrow-NTT throughput ratio is 1× (common) or 4× (wide), at equal clock only.

Limits:
- Arithmetic bank only; no complex 3M controller, transform memory or scheduler.
- Generic gate depth is not frequency, nanoseconds or target-library STA.
- GE is approximate NAND2 equivalent; no measured power/energy.
- NTT64 lane throughput requires 2048 data bits per direction plus twiddle bandwidth.
