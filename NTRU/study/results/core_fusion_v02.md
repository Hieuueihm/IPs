# Core fusion v0.2 — kiểm tra số học và mapping

Seed: 20261025. Không đo throughput RTL, Fmax, area hoặc năng lượng.

- signedness_product_cases: 4896
- fft_mapping_batches: 768
- fft_butterflies: 2816
- ntt_main_product_cases: 1370

| Leaf | FFT width/component | Butterfly/batch | Lượt issue/batch |
|---|---|---|---|
| 16 | 32 | 8 | 1 |
| 16 | 64 | 2 | 1 |
| 16 | 128 | 1 | 2 |
| 32 | 32 | 8 | 1 |
| 32 | 64 | 2 | 1 |
| 32 | 128 | 1 | 2 |

Lượt issue không phải latency. Hai contract rounding chỉ kiểm tra rằng product
reconstruction giữ được giá trị đầu vào cho mỗi contract; không chứng minh hai
contract tương đương nhau hoặc bit-match với FN-DSA. NTT chỉ kiểm tra tích chính,
không kiểm tra reducer/context conversion. Không mô hình hóa stall, feedback,
adder width nội bộ, twiddle/memory hay pipeline của core.
