# Controlled reducer comparison

Simulation: `{"reducer_transactions": 139292, "reducer_configurations": 9, "exhaustive_tlow_per_q": 65536, "cluster_transactions": 16102, "cluster_configurations": 3, "transform_traces": 56, "r8_composed_complex_products": 70, "mismatches": 0}`

| Top | Comb GE | FF bits | Total GE | Gate depth |
|---|---:|---:|---:|---:|
| reduce_original_dynamic | 1744.8 | 78 | 2109.1 | 51 |
| reduce_csa_dynamic | 1784.9 | 78 | 2149.2 | 41 |
| reduce_compact_dynamic | 1464.6 | 78 | 1828.9 | 50 |
| reduce_original_q12289 | 843.2 | 76 | 1198.2 | 39 |
| reduce_csa_q12289 | 912.4 | 76 | 1267.4 | 36 |
| reduce_compact_q12289 | 650.6 | 76 | 1005.5 | 42 |
| reduce_original_q3329 | 1075.5 | 70 | 1402.4 | 41 |
| reduce_csa_q3329 | 1180.7 | 70 | 1507.6 | 38 |
| reduce_compact_q3329 | 861.9 | 70 | 1188.8 | 45 |
| reduce_cluster_original | 26297.2 | 643 | 29300.0 | 124 |
| reduce_cluster_csa | 26486.1 | 643 | 29488.9 | 109 |
| reduce_cluster_compact | 25194.7 | 643 | 28197.5 | 118 |

Selection: **compact**, rule: minimum cluster total GE among candidates with generic gate depth no worse than original.

Limits

- Canonical products only; R=2^16, q3329/q12289.
- Original/CSA/compact use the same m generator, pipeline and II.
- Generic GE/depth only, not target-library area/Fmax/energy.
