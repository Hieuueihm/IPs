# Prototype arithmetic bank: F16 / R32

- Simulation: 1335 transactions ×4 configurations; 0 mismatches.
- 189 complex 3M results recomposed from RTL products match actual C R8.
- Input/output registers: II=1, two sampled clock edges; bubbles and mode changes checked.

| Top | Comb GE | FF | Total GE | Longest gate path | NTT16 lanes |
|---|---:|---:|---:|---:|---:|
| proto_r32 | 232558.5 | 3078 | 246932.8 | 179 | 16 |
| proto_f16_common | 250018.7 | 3078 | 264392.9 | 193 | 16 |
| proto_f16_mid | 271084.8 | 3078 | 285459.0 | 190 | 32 |
| proto_f16_wide | 324822.4 | 6118 | 353393.4 | 193 | 64 |

| Top | Total GE / R32 | Peak NTT capacity / R32 | Peak NTT per GE / R32 |
|---|---:|---:|---:|
| proto_r32 | 1.000× | 1.0× | 1.000× |
| proto_f16_common | 1.071× | 1.0× | 0.934× |
| proto_f16_mid | 1.156× | 2.0× | 1.730× |
| proto_f16_wide | 1.431× | 4.0× | 2.795× |

Peak capacity assumes equal clock and full bandwidth; it is not measured speedup.

Tool: `Yosys 0.52 (git sha1 fee39a3284c90249e1d9684cf6944ffbbcbb8f90)`. Flow: `synth -flatten -noabc`, `abc -fast -g` generic gates.
GE: approximate weights from the tile study; registers counted at 4.67 GE/bit.

One-bank bandwidth ceilings (data read/write each direction, twiddle separate):

| Data bit/cycle | R32 NTT BF/cycle | F16 common | F16 mid | F16 wide |
|---:|---:|---:|---:|---:|
| 512 | 16 | 16 | 16 | 16 |
| 1024 | 16 | 16 | 32 | 32 |
| 2048 | 16 | 16 | 32 | 64 |

Limits:

- Arithmetic bank only; no complex 3M controller, transform memory or scheduler.
- Generic gate depth is not frequency, nanoseconds or target-library STA.
- GE is approximate NAND2 equivalent; no measured power/energy.
- NTT32/64 lane throughput requires 1024/2048 data bits per direction plus twiddle bandwidth.
