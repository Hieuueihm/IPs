# Four-leaf configurable NTT cluster

- RTL simulation: 16102 vectors, 9 configurations, zero mismatches.
- 56 forward/inverse traces over both profiles.
- 70 R8 complex products reconstructed in the driver from exact RTL32 products.

| Top | Comb GE | FF bits | Total GE | Gate depth |
|---|---:|---:|---:|---:|
| cluster_ntt_parallel | 21022.5 | 477 | 23250.1 | 118 |
| cluster_ntt_pair_only | 20861.2 | 295 | 22238.8 | 120 |
| cluster_ntt_configurable | 26259.3 | 643 | 29262.1 | 122 |
| cluster_flex_parallel | 25843.8 | 640 | 28832.6 | 119 |
| cluster_flex_pair | 26147.3 | 643 | 29150.1 | 125 |
| cluster_ntt_pair_q12289 | 17068.8 | 292 | 18432.4 | 105 |
| cluster_ntt_pair_q3329 | 14882.0 | 258 | 16086.9 | 107 |
| cluster_ntt_pair_bypass | 23313.6 | 610 | 26162.3 | 122 |
| cluster_ntt_parallel_short | 20637.7 | 318 | 22122.7 | 118 |

## Area comparisons

| Comparison | Total GE change |
|---|---:|
| Add stage pairing to FFT-capable cluster | +1.10% |
| Add bypass to pair-only NTT | +17.64% |
| Add four-independent-BF mode to pair/bypass NTT | +11.85% |
| Full shared cluster vs short dedicated NTT | +31.77% |
| Runtime q vs fixed12289, pair-only | +20.65% |
| Runtime q vs fixed3329, pair-only | +38.24% |

Small generic mapping differences do not establish zero-cost FFT support or target timing.

## Isolated-transform cycle model

Data bandwidth is per direction. Root bandwidth is separate. Same-clock hypothesis; not measured speedup.
One pass takes (issues-1)*beats+2*beats+1 cycles: initial input assembly, three-edge compute and final output serialization.
beats=ceil(transaction_data_bits/bandwidth). A tail layer uses four independent butterflies. Normalization is excluded.

| q | N | Layers | Data bits/cycle | Dedicated short cycles | Shared parallel cycles | Shared paired cycles | Short / paired |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12289 | 8 | 3 | 64 | 12 | 15 | 9 | 1.333 |
| 12289 | 8 | 3 | 128 | 6 | 9 | 7 | 0.857 |
| 12289 | 16 | 4 | 64 | 24 | 28 | 12 | 2.0 |
| 12289 | 16 | 4 | 128 | 12 | 16 | 12 | 1.0 |
| 12289 | 64 | 6 | 64 | 108 | 114 | 54 | 2.0 |
| 12289 | 64 | 6 | 128 | 54 | 60 | 54 | 1.0 |
| 12289 | 256 | 8 | 64 | 528 | 536 | 264 | 2.0 |
| 12289 | 256 | 8 | 128 | 264 | 272 | 264 | 1.0 |
| 12289 | 512 | 9 | 64 | 1170 | 1179 | 651 | 1.797 |
| 12289 | 512 | 9 | 128 | 585 | 594 | 586 | 0.998 |
| 12289 | 1024 | 10 | 64 | 2580 | 2590 | 1290 | 2.0 |
| 12289 | 1024 | 10 | 128 | 1290 | 1300 | 1290 | 1.0 |
| 3329 | 256 | 7 | 64 | 462 | 469 | 265 | 1.743 |
| 3329 | 256 | 7 | 128 | 231 | 238 | 232 | 0.996 |

## Limits

- Shared RTL: three sampled edges and II1; dedicated short baseline: two edges and II1. No backpressure or RAM.
- Isolated transform table assumes a barrier after each pass, ideal read/write adapters and externally gathered groups.
- Cycle model covers butterfly layers only; inverse normalization, BASEMUL and domain conversions are excluded.
- Twiddle bandwidth, address gathering, target timing, memory area and energy are not measured.
- GE uses generic mapping and 4.67 GE per FF; depth is not Fmax.
- W64/W128 assembly and sign fixups are in the driver, not synthesized RTL.
- Full transform traces are compared to integer arithmetic, not Falcon/Kyber C.
- q3329 N256 uses seven layers and normalization 128^-1; no BASEMUL implemented.
