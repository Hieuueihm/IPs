# FFT 64 / 128 bit trong lõi: gán khối tile và lịch đọc (mô hình trước RTL)

Mô hình: [model/fft_wide_sched.py](../../model/fft_wide_sched.py). Mỗi phần 32 bit của một phần tử là một phần tử định dạng 0 "ảo"; cặp phần thứ k của butterfly b rơi vào tile T(b) | k theo luật định dạng 0, nên L tile T(b) .. T(b) + L − 1 là một khối: tile T(b) | k đọc phần k bằng nguồn mạng định dạng 0 của nó rồi chuyển cho tile của khối làm butterfly.

| Định dạng | Tầng đã xét | Chu kỳ đọc xung đột | Nguồn đọc thêm mỗi cổng (lớn nhất / trung bình) | Nguồn đọc mỗi cổng sau khi thêm (lớn nhất / trung bình) | Nguồn ghi thêm mỗi siêu bank (lớn nhất) |
|---|---:|---:|---:|---:|---:|
| 1 (64 bit) | 45 | 64 | 0 / 0.00 | 16 / 8.75 | 0 |
| 2 (128 bit) | 45 | 320 | 0 / 0.00 | 16 / 8.75 | 0 |

Hợp cả ba định dạng và NTT: đọc 16 / 8.75 nguồn mỗi cổng (trước: 16 / 8.75); ghi 14 / 8.75 nguồn mỗi bank (trước: 14 / 8.75).

## Lịch đầy đủ: ca vàng 1.0, xung đột, chu kỳ (rào chắn mỗi tầng)

Đọc x phần k ở e + k, y ở e + k + 1 (x giữ một chu kỳ trong mạng); phần ảo từ e + L; kết quả ghi x một chu kỳ sau khi tile trả, y hai chu kỳ sau; root phần k đọc ở e + k − (độ sớm của khối).

| W | N | Chiều | Khớp ca vàng | Chu kỳ | Xung đột đọc / ghi / ROM root | Ngưỡng giả thuyết 3 |
|---:|---:|---|---|---:|---:|---:|
| 64 | 4 | xuôi | có | 37 | 0 / 0 / 0 |  |
| 64 | 8 | xuôi | có | 77 | 0 / 0 / 0 |  |
| 64 | 16 | xuôi | có | 117 | 0 / 0 / 0 |  |
| 64 | 32 | xuôi | có | 157 | 0 / 0 / 0 |  |
| 64 | 64 | xuôi | có | 227 | 0 / 0 / 0 |  |
| 64 | 128 | xuôi | có | 345 | 0 / 0 / 0 |  |
| 64 | 256 | xuôi | có | 571 | 0 / 0 / 0 |  |
| 64 | 512 | xuôi | có | 1037 | 0 / 0 / 0 |  |
| 64 | 1024 | xuôi | có | 2031 | 0 / 0 / 0 | 2300 |
| 128 | 4 | xuôi | có | 74 | 0 / 0 / 0 |  |
| 128 | 8 | xuôi | có | 153 | 0 / 0 / 0 |  |
| 128 | 16 | xuôi | có | 232 | 0 / 0 / 0 |  |
| 128 | 32 | xuôi | có | 359 | 0 / 0 / 0 |  |
| 128 | 64 | xuôi | có | 570 | 0 / 0 / 0 |  |
| 128 | 128 | xuôi | có | 973 | 0 / 0 / 0 |  |
| 128 | 256 | xuôi | có | 1808 | 0 / 0 / 0 |  |
| 128 | 512 | xuôi | có | 3603 | 0 / 0 / 0 |  |
| 128 | 1024 | xuôi | có | 7510 | 0 / 0 / 0 | 8500 |
| 64 | 4 | ngược | có | 37 | 0 / 0 / 0 |  |
| 64 | 8 | ngược | có | 77 | 0 / 0 / 0 |  |
| 64 | 16 | ngược | có | 117 | 0 / 0 / 0 |  |
| 64 | 32 | ngược | có | 157 | 0 / 0 / 0 |  |
| 64 | 64 | ngược | có | 227 | 0 / 0 / 0 |  |
| 64 | 128 | ngược | có | 345 | 0 / 0 / 0 |  |
| 64 | 256 | ngược | có | 571 | 0 / 0 / 0 |  |
| 64 | 512 | ngược | có | 1037 | 0 / 0 / 0 |  |
| 64 | 1024 | ngược | có | 2031 | 0 / 0 / 0 | 2530 |
| 128 | 4 | ngược | có | 74 | 0 / 0 / 0 |  |
| 128 | 8 | ngược | có | 153 | 0 / 0 / 0 |  |
| 128 | 16 | ngược | có | 232 | 0 / 0 / 0 |  |
| 128 | 32 | ngược | có | 359 | 0 / 0 / 0 |  |
| 128 | 64 | ngược | có | 570 | 0 / 0 / 0 |  |
| 128 | 128 | ngược | có | 973 | 0 / 0 / 0 |  |
| 128 | 256 | ngược | có | 1808 | 0 / 0 / 0 |  |
| 128 | 512 | ngược | có | 3603 | 0 / 0 / 0 |  |
| 128 | 1024 | ngược | có | 7510 | 0 / 0 / 0 | 9350 |
