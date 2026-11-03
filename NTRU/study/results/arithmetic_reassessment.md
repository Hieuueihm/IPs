# Operation-level FFT/NTT reassessment

Analytical counts and exact checks. No area, Fmax or end-to-end throughput measured.

## Checks

- complex_3M_vs_4M_pairs: 6715
- modular_operand_pairs_all_backends: 25125
- modular_half_inputs: 40743
- lazy_montgomery_pairs_valid_bound: 3000
- full_low_product_pairs: 3000
- small_ntt_dft_and_inverse_cases: 100
- negacyclic_convolution_cases: 100
- basemul_karatsuba_pairs: 5000
- rational_split_merge_cases: 100

## FFT full-product slots, 32-bit limbs

| W | 4M | 3M generic W+1 | 3M twiddle W+1 | 3M carry correction | GS W+1 / 4M |
|---:|---:|---:|---:|---:|---:|
| 32 | 4 | 6 | 4 | 3 | 8 |
| 64 | 16 | 17 | 14 | 12 | 24 |
| 128 | 64 | 57 | 52 | 48 | 80 |

3M counts exclude extra adders, correction, coefficient storage and routing.

## Reduction profiles

| q | word | Montgomery polarity | coefficient | q NAF terms | coefficient NAF terms | Barrett mu |
|---:|---:|---|---:|---|---|---:|
| 3329 | 16 | plus | 3327 | [(1, 0), (1, 8), (-1, 10), (1, 12)] | [(-1, 0), (1, 8), (-1, 10), (1, 12)] | 5039 |
| 12289 | 16 | plus | 12287 | [(1, 0), (-1, 12), (1, 14)] | [(-1, 0), (-1, 12), (1, 14)] | 21843 |
| 8380417 | 32 | minus | 58728449 | [(1, 0), (-1, 13), (1, 23)] | [(1, 0), (1, 13), (-1, 23), (1, 26)] | 8396807 |
| 2013265921 | 32 | minus | 2281701377 | [(1, 0), (-1, 27), (1, 31)] | [(1, 0), (1, 27), (1, 31)] | 2290649223 |
| 4293918721 | 32 | minus | 1048577 | [(1, 0), (-1, 20), (1, 32)] | [(1, 0), (1, 20)] | 4296016127 |

NAF terms are (sign, shift). They are not measured gate/adder costs.

## Counterexamples

~~~json
{
  "high_product_dropped_carry": {
    "exact": 18446744073709551614,
    "wrong": 18446744073709551613
  },
  "shoup_q_near_radix": {
    "q": 251,
    "R": 256,
    "x": 9,
    "w": 140,
    "remainder": 256,
    "correct": 5
  },
  "rounding_location": {
    "round_product_then_add": 1,
    "round_after_add": 2
  },
  "pointwise_not_unit_twiddle": {
    "rounded_imag": 140737488224256,
    "signed_W_plus_2_max": 8589934591
  }
}
~~~
