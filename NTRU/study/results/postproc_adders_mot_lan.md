# Định cỡ ngân hàng cộng/trừ dùng chung

Bit cộng cần mỗi chu kỳ ở từng tầng, tại tốc độ đỉnh của mỗi chế độ trên 64 bộ nhân 16×16.

| Chế độ | Butterfly/chu kỳ | Tầng pre | Tầng A | Tầng B | Tầng C | Tầng D | Tổng |
|---|---:|---:|---:|---:|---:|---:|---:|
| FFT 32 bit | 5.33 | 341 | 528 | 512 | 683 | 0 | 2064 |
| FFT 64 bit | 1.33 | 171 | 260 | 256 | 341 | 0 | 1028 |
| FFT 128 bit | 0.333 | 85 | 129 | 128 | 171 | 0 | 513 |
| NTT mọi q, một lane 32 bit, bộ Montgomery riêng | 16 | 0 | 0 | 0 | 1056 | 1056 | 2112 |

| Cách bố trí | Tầng pre | Tầng A | Tầng B | Tầng C | Tầng D | Tổng bit cộng |
|---|---:|---:|---:|---:|---:|---:|
| Riêng FFT (lớn nhất các chế độ FFT) | 341 | 528 | 512 | 683 | 0 | 2064 |
| Riêng NTT | 0 | 0 | 0 | 1056 | 1056 | 2112 |
| Hai ngân hàng riêng | 341 | 528 | 512 | 1739 | 1056 | 4176 |
| Một ngân hàng dùng chung | 341 | 528 | 512 | 1056 | 1056 | 3493 |

Dùng chung tiết kiệm 16% bit cộng so với hai ngân hàng riêng (chưa tính mux chọn làn và cắt chuỗi nhớ).

NTT (mọi q) với bộ Montgomery riêng: tầng A, B nằm trong 16 bộ Montgomery (cùng 7 DSP mỗi tile), không tính ở đây. Tile của RTL nghiệm thu dùng một bộ cộng/trừ cho cả CT và GS, nên tầng C, D ở đây là cận trên.
