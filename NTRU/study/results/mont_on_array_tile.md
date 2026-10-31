# Mô hình chu kỳ: rút gọn Montgomery trên mảng nhân của một tile

Một tile = 4 bộ nhân 16×16. Mỗi phép nhân modulo đi 3 lượt (T, m, m·q) trên các bộ nhân, rồi qua bộ cộng chung. Stall = dừng toàn tile (clock-enable). Mọi kết quả được so với a·b·R⁻¹ mod q.
Bit giữ thêm mỗi phép = toán hạng A + tag (24 bit) + phần T/m đang chờ (không tính thanh ghi bên trong bộ nhân, trên FPGA nằm trong DSP).

## 1. Không stall, không giới hạn số phép đang chạy

| Modulus | Độ trễ nhân | Phép/chu kỳ (trên mảng) | Phép/chu kỳ (rút gọn riêng) | Đang chạy tối đa | Bit giữ tối đa (trên mảng) | Bit giữ (rút gọn riêng, độ trễ rút gọn 2) | Độ trễ TB | Đúng thứ tự |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| q12289 (16 bit) | 3 | 1.333 | 4.000 | 16 | 588 | 480 | 10.0 | có |
| q12289 (16 bit) | 4 | 1.333 | 4.000 | 20 | 752 | 576 | 13.0 | có |
| q12289 (16 bit) | 5 | 1.333 | 4.000 | 24 | 916 | 672 | 16.0 | có |
| q3329 (16 bit) | 3 | 1.333 | 4.000 | 16 | 588 | 480 | 10.0 | có |
| q3329 (16 bit) | 4 | 1.333 | 4.000 | 20 | 752 | 576 | 13.0 | có |
| q3329 (16 bit) | 5 | 1.333 | 4.000 | 24 | 916 | 672 | 16.0 | có |
| q8380417 (32 bit) | 3 | 0.333 | 1.000 | 4 | 195 | 120 | 10.0 | có |
| q8380417 (32 bit) | 4 | 0.333 | 1.000 | 5 | 252 | 144 | 13.0 | có |
| q8380417 (32 bit) | 5 | 0.333 | 1.000 | 6 | 309 | 168 | 16.0 | có |

## 2. Giới hạn số phép đang chạy (đổi bit giữ lấy tốc độ), độ trễ nhân 4

| Modulus | Giới hạn | Phép/chu kỳ | Bit giữ tối đa |
|---|---:|---:|---:|
| q12289 (16 bit) | 16 | 1.230 | 656 |
| q12289 (16 bit) | 12 | 0.923 | 492 |
| q12289 (16 bit) | 8 | 0.615 | 328 |
| q12289 (16 bit) | 6 | 0.461 | 246 |
| q12289 (16 bit) | 4 | 0.308 | 164 |
| q3329 (16 bit) | 16 | 1.230 | 656 |
| q3329 (16 bit) | 12 | 0.923 | 492 |
| q3329 (16 bit) | 8 | 0.615 | 328 |
| q3329 (16 bit) | 6 | 0.461 | 246 |
| q3329 (16 bit) | 4 | 0.308 | 164 |
| q8380417 (32 bit) | 6 | 0.333 | 252 |
| q8380417 (32 bit) | 4 | 0.308 | 228 |
| q8380417 (32 bit) | 3 | 0.231 | 171 |
| q8380417 (32 bit) | 2 | 0.154 | 114 |
| q8380417 (32 bit) | 1 | 0.077 | 57 |

## 3. Stall và bubble ngẫu nhiên, độ trễ nhân 4, không giới hạn

| Modulus | Xác suất stall | Xác suất bubble | Phép/chu kỳ | Tỉ lệ so với không stall | Đúng thứ tự | Số phép đã kiểm |
|---|---:|---:|---:|---:|---|---:|
| q12289 (16 bit) | 0.1 | 0.0 | 1.200 | 0.900 | có | 48000 |
| q12289 (16 bit) | 0.3 | 0.0 | 0.933 | 0.700 | có | 37308 |
| q12289 (16 bit) | 0.0 | 0.2 | 1.151 | 0.864 | có | 46054 |
| q12289 (16 bit) | 0.2 | 0.2 | 0.918 | 0.688 | có | 36710 |
| q3329 (16 bit) | 0.1 | 0.0 | 1.197 | 0.898 | có | 47892 |
| q3329 (16 bit) | 0.3 | 0.0 | 0.934 | 0.701 | có | 37360 |
| q3329 (16 bit) | 0.0 | 0.2 | 1.149 | 0.862 | có | 45947 |
| q3329 (16 bit) | 0.2 | 0.2 | 0.913 | 0.685 | có | 36518 |
| q8380417 (32 bit) | 0.1 | 0.0 | 0.300 | 0.899 | có | 11988 |
| q8380417 (32 bit) | 0.3 | 0.0 | 0.234 | 0.701 | có | 9348 |
| q8380417 (32 bit) | 0.0 | 0.2 | 0.308 | 0.923 | có | 12302 |
| q8380417 (32 bit) | 0.2 | 0.2 | 0.247 | 0.742 | có | 9892 |

## 4. Nhịp NTT hai tầng (4 hệ số, tầng 2 chờ tầng 1), cộng/trừ butterfly 1 chu kỳ

| Modulus | Rút gọn | Độ trễ nhân | Nhịp/chu kỳ/tile | Độ trễ nhịp tối thiểu | Độ trễ nhịp TB | Nhịp đang chạy tối đa | Bit giữ tối đa | Đúng thứ tự |
|---|---|---:|---:|---:|---:|---:|---:|---|
| q12289 (16 bit) | riêng | 3 | 0.998 | 12 | 12.0 | 12 | 864 | có |
| q12289 (16 bit) | trên mảng | 3 | 0.326 | 22 | 23.8 | 9 | 912 | có |
| q12289 (16 bit) | riêng | 4 | 0.998 | 14 | 14.0 | 14 | 1008 | có |
| q12289 (16 bit) | trên mảng | 4 | 0.332 | 28 | 28.0 | 11 | 1124 | có |
| q8380417 (32 bit) | riêng | 3 | 0.249 | 14 | 16.0 | 4 | 544 | có |
| q8380417 (32 bit) | trên mảng | 3 | 0.083 | 24 | 32.5 | 3 | 637 | có |
| q8380417 (32 bit) | riêng | 4 | 0.249 | 16 | 16.0 | 4 | 544 | có |
| q8380417 (32 bit) | trên mảng | 4 | 0.083 | 30 | 36.0 | 4 | 871 | có |
| q12289, stall 0.1 | trên mảng | 4 | 0.299 | 28 | 31.1 | 11 | 1124 | có |
| q12289, stall 0.3 | trên mảng | 4 | 0.231 | 31 | 40.2 | 11 | 1124 | có |

Nhịp hai tầng đã kiểm so với NTT số nguyên: 23092, không sai khác.

Tổng số phép nhân modulo đã kiểm kết quả: 722787, không sai khác.

