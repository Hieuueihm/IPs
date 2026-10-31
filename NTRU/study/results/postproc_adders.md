# Định cỡ ngân hàng cộng/trừ dùng chung

Bit cộng cần mỗi chu kỳ ở từng tầng, tại tốc độ đỉnh của mỗi chế độ trên 64 bộ nhân 16×16.

| Chế độ | Butterfly/chu kỳ | Tầng pre | Tầng A | Tầng B | Tầng C | Tầng D | Tổng |
|---|---:|---:|---:|---:|---:|---:|---:|
| FFT 32 bit | 5.33 | 341 | 528 | 512 | 683 | 0 | 2064 |
| FFT 64 bit | 1.33 | 171 | 260 | 256 | 341 | 0 | 1028 |
| FFT 128 bit | 0.333 | 85 | 129 | 128 | 171 | 0 | 513 |
| NTT 16 bit, bộ rút gọn hằng | 64 | 0 | 0 | 0 | 2176 | 2176 | 4352 |
| NTT 32 bit, rút gọn trên mảng | 5.33 | 0 | 176 | 176 | 352 | 352 | 1056 |

| Cách bố trí | Tầng pre | Tầng A | Tầng B | Tầng C | Tầng D | Tổng bit cộng |
|---|---:|---:|---:|---:|---:|---:|
| Riêng FFT (lớn nhất các chế độ FFT) | 341 | 528 | 512 | 683 | 0 | 2064 |
| Riêng NTT | 0 | 176 | 176 | 2176 | 2176 | 4704 |
| Hai ngân hàng riêng | 341 | 704 | 688 | 2859 | 2176 | 6768 |
| Một ngân hàng dùng chung | 341 | 528 | 512 | 2176 | 2176 | 5733 |

Dùng chung tiết kiệm 15% bit cộng so với hai ngân hàng riêng (chưa tính mux chọn làn và cắt chuỗi nhớ).

NTT 16 bit với bộ rút gọn hằng: tầng A, B và hai phép nhân hằng nằm trong 64 bộ rút gọn, không tính ở đây.
