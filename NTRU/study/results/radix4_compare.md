# Radix4 factor vs paired radix2

Selected reducer: **compact**.

Simulation: `{"transactions": 17510, "configurations": 9, "epoch_transactions": 17510, "epoch_configurations": 4, "mismatches": 0, "transform_traces": 56, "excluded_non_ntt_root_unit_vectors": 640, "added_factor_root_vectors": 2048, "r8_composed_complex_products": 70, "scope": "All four shared modes; mode1 is restricted to actual adjacent-NTT-layer twiddle relations. No INTT normalization inside core."}`

| Top | Comb GE | FF bits | Total GE | Gate depth |
|---|---:|---:|---:|---:|
| radix2_shared3 | 25268.7 | 643 | 28271.5 | 118 |
| radix2_shared4 | 25325.4 | 784 | 28986.7 | 119 |
| radix4_shared4 | 36924.5 | 778 | 40557.8 | 101 |
| radix2_pair4 | 19531.2 | 370 | 21259.1 | 119 |
| radix4_pair4 | 21010.7 | 384 | 22803.9 | 97 |
| radix4_pair_q12289 | 15126.1 | 380 | 16900.7 | 87 |
| radix4_pair_q3329 | 13564.5 | 336 | 15133.6 | 87 |
| radix2_pair_q12289 | 16070.5 | 366 | 17779.7 | 109 |
| radix2_pair_q3329 | 13894.5 | 324 | 15407.6 | 113 |
| radix4_shared_epoch | 35449.5 | 778 | 39082.8 | 100 |
| radix4_pair_epoch | 19485.9 | 384 | 21279.2 | 104 |
| radix4_pair_epoch_q12289 | 14638.1 | 380 | 16412.7 | 90 |
| radix4_pair_epoch_q3329 | 12898.8 | 336 | 14467.9 | 89 |

radix4_shared4 / radix2_shared3: 1.4346× total GE (+43.46%).

radix4_shared4 / radix2_shared4: 1.3992× total GE (+39.92%).

radix4_pair4 / radix2_pair4: 1.0727× total GE (+7.27%).

radix4_pair_q12289 / radix2_pair_q12289: 0.9506× total GE (-4.94%).

radix4_pair_q3329 / radix2_pair_q3329: 0.9822× total GE (-1.78%).

radix4_shared_epoch / radix2_shared4: 1.3483× total GE (+34.83%).

radix4_pair_epoch / radix2_pair4: 1.0009× total GE (+0.09%).

radix4_pair_epoch_q12289 / radix2_pair_q12289: 0.9231× total GE (-7.69%).

radix4_pair_epoch_q3329 / radix2_pair_q3329: 0.9390× total GE (-6.10%).

Limits

- Same function and II1; paired baseline has 3 or 4 edges, factor has 4 edges.
- NTT-pair-only factor prunes the fourth multiplier; full shared factor retains four for FFT/independent NTT.
- Mixed CT/GS tops include both fixed-root paths. Epoch tops share one and require drain on profile/direction change.
- Generic GE/depth, not target timing, power, energy or whole-transform speedup.
- No shared compressor FFT/reduction fabric is implemented by this comparison.
