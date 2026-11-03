# FFT 64 / 128 bit trên tile một làn, theo từng phần 32 bit (mô hình trước RTL)

Mô hình: [model/fft_wide_tile.py](../../model/fft_wide_tile.py). Số học theo phần 32 bit (nhân cộng dồn theo cột, cộng/trừ có nhớ, div2e) khớp từng bit với spec 1.0: 40000 phép nhân / nhân phức / div2e ngẫu nhiên và biên, 36 ca vàng FFT / FFT ngược định dạng 1, 2 (logn 2..10).

## Việc của một butterfly (số chu kỳ của từng bộ phận trong tile)

| W | Chiều | Tích 32×32 (bộ nhân) | Phép cộng/trừ 32 bit | Chiếm tile (chu kỳ) |
|---:|---|---:|---:|---:|
| 64 | xuôi | 12 | 12 | 12 |
| 64 | ngược | 12 | 12 | 12 |
| 64 | ngược, tầng cuối (div2e) | 12 | 28 | 28 |
| 128 | xuôi | 45 | 24 | 45 |
| 128 | ngược | 45 | 24 | 45 |
| 128 | ngược, tầng cuối (div2e) | 45 | 56 | 56 |

Phép cộng/trừ (mỗi giá trị L phần): A + B, A - B (re, im) = 2·L; o.re + o.im = 1·L; wr + wi = 1·L; p0 - p1, p0 + p1 = 1·L; p2 - (p0 + p1) = 1·L; div2e (rounding pass + shift, 4 values) = 8·L; FFT xuôi thay A ± B bằng A ± T = 2·L.

## Chu kỳ N = 1024 (rào chắn mỗi tầng; độ trễ đọc → ghi như model/fft_core_plan.py)

| W | Xuôi | Ngược | Ngưỡng giả thuyết 3 (xuôi / ngược) | Xuôi, wr + wi lấy từ ROM | Ngược, wr + wi lấy từ ROM |
|---:|---:|---:|---:|---:|---:|
| 32 | 531 | 531 | 700 / 770 | 531 | 531 |
| 64 | 1827 | 2067 | 2300 / 2530 | 1827 | 2037 |
| 128 | 6579 | 6744 | 8500 / 9350 | 6579 | 6684 |

Tỉ lệ 128 / 32 bit = 12.4 (ngưỡng ≥ 10; N512 10.6, ≥ 8); 128 / 64 bit = 3.6 (≥ 3). Hàng 32 bit là lõi đã đo (chế độ 5, 539 chu kỳ).

## Root

- Bảng một chiều, 768 root (re, im): 32 bit 48 kbit, 64 bit 96 kbit, 128 bit 192 kbit (một BRAM36 = 36 kbit).
- Root 64 bit = làm tròn root 128 bit: xuôi khớp, ngược khớp. Root ngược = (re, −im) của root xuôi: 128 bit đúng theo định nghĩa, 64 bit đúng, 32 bit đúng.
