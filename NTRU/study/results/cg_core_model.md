# Lịch hình học cố định cho cả lõi (mô hình trước RTL)

Mô hình: [model/cg_core_model.py](../../model/cg_core_model.py). Mỗi tầng đọc vị trí i, i + M/2 của một bộ đệm, ghi 2i, 2i + 1 vào bộ đệm kia (ngược: chuyển vị); M = N với NTT, N/2 điểm phức với FFT. Nửa số tile làm phần tư đầu của các butterfly, nửa kia phần tư thứ hai, để mỗi bước một nửa tile ghi nửa dưới, nửa kia ghi nửa trên bộ đệm. Tầng sau bắt đầu sớm nhất có thể (không trùng cổng, đọc sau ghi, ghi sau đọc). Cột "lõi hiện tại": NTT theo kế hoạch chồng tầng, FFT có rào chắn mỗi tầng (cả hai trùng RTL).

## NTT

| Profile | N | hmin | Chiều | Ca vàng | Khớp | Thứ tự cuối tự nhiên | Chu kỳ | Lõi hiện tại | Chênh |
|---:|---:|---:|---|---:|---|---|---:|---:|---:|
| 0 | 8 | 0 | xuôi | 1 | có | có | 72 | 72 | +0% |
| 0 | 8 | 0 | ngược | 1 | có | có | 72 | 72 | +0% |
| 0 | 16 | 0 | xuôi | 1 | có | có | 102 | 100 | +2% |
| 0 | 16 | 0 | ngược | 1 | có | có | 102 | 100 | +2% |
| 0 | 32 | 0 | xuôi | 1 | có | có | 128 | 127 | +1% |
| 0 | 32 | 0 | ngược | 1 | có | có | 128 | 127 | +1% |
| 0 | 64 | 0 | xuôi | 1 | có | có | 171 | 157 | +9% |
| 0 | 64 | 0 | ngược | 1 | có | có | 171 | 157 | +9% |
| 0 | 128 | 0 | xuôi | 1 | có | có | 224 | 196 | +14% |
| 0 | 128 | 0 | ngược | 1 | có | có | 224 | 195 | +15% |
| 0 | 256 | 0 | xuôi | 1 | có | có | 309 | 255 | +21% |
| 0 | 256 | 0 | ngược | 1 | có | có | 309 | 249 | +24% |
| 0 | 512 | 0 | xuôi | 1 | có | có | 467 | 464 | +1% |
| 0 | 512 | 0 | ngược | 1 | có | có | 467 | 458 | +2% |
| 0 | 1024 | 0 | xuôi | 1 | có | có | 983 | 984 | -0% |
| 0 | 1024 | 0 | ngược | 1 | có | có | 983 | 985 | -0% |
| 1 | 8 | 0 | xuôi | 1 | có | có | 72 | 72 | +0% |
| 1 | 8 | 0 | ngược | 1 | có | có | 72 | 72 | +0% |
| 1 | 16 | 0 | xuôi | 1 | có | có | 102 | 100 | +2% |
| 1 | 16 | 0 | ngược | 1 | có | có | 102 | 100 | +2% |
| 1 | 32 | 0 | xuôi | 1 | có | có | 128 | 127 | +1% |
| 1 | 32 | 0 | ngược | 1 | có | có | 128 | 127 | +1% |
| 1 | 64 | 0 | xuôi | 1 | có | có | 171 | 157 | +9% |
| 1 | 64 | 0 | ngược | 1 | có | có | 171 | 157 | +9% |
| 1 | 128 | 0 | xuôi | 1 | có | có | 224 | 196 | +14% |
| 1 | 128 | 0 | ngược | 1 | có | có | 224 | 195 | +15% |
| 1 | 256 | 1 | xuôi | 1 | có | có | 272 | 231 | +18% |
| 1 | 256 | 1 | ngược | 1 | có | có | 272 | 225 | +21% |
| 2 | 256 | 0 | xuôi | 10 | có | có | 309 | 255 | +21% |
| 2 | 256 | 0 | ngược | 10 | có | có | 309 | 249 | +24% |

Profile 3, các modulo khảo sát, dữ liệu ngẫu nhiên, so với định nghĩa đánh giá và lượt ngược về lại:

| Ứng dụng | q | N | hmin | Xuôi khớp | Ngược về lại | Chu kỳ |
|---|---:|---:|---:|---|---|---:|
| ML-KEM | 3329 | 256 | 1 | có | có | 272 |
| ML-DSA | 8380417 | 256 | 0 | có | có | 309 |
| FN-DSA | 12289 | 512 | 0 | có | có | 467 |
| FN-DSA | 12289 | 1024 | 0 | có | có | 983 |
| HAWK ký | 18433 | 512 | 0 | có | có | 467 |
| HAWK ký | 18433 | 1024 | 0 | có | có | 983 |
| HAETAE | 64513 | 256 | 0 | có | có | 309 |
| Kyber vòng 1 | 7681 | 256 | 0 | có | có | 309 |
| Saber RNS | 10753 | 256 | 0 | có | có | 309 |
| Saber qua NTT | 25166081 | 256 | 1 | có | có | 272 |
| LightSaber qua NTT | 20972417 | 256 | 2 | có | có | 234 |

## FFT (cấu trúc: cặp, cổng, phụ thuộc, chu kỳ; số học như lõi hiện tại)

| Độ rộng | N | Chiều | Mọi cặp đúng tầng | Thứ tự cuối tự nhiên | Chu kỳ | Lõi hiện tại | Chênh |
|---:|---:|---|---|---|---:|---:|---:|
| 32 | 8 | xuôi | có | có | 43 | 50 | -14% |
| 32 | 8 | ngược | có | có | 43 | 50 | -14% |
| 32 | 16 | xuôi | có | có | 64 | 77 | -17% |
| 32 | 16 | ngược | có | có | 64 | 77 | -17% |
| 32 | 32 | xuôi | có | có | 85 | 104 | -18% |
| 32 | 32 | ngược | có | có | 85 | 104 | -18% |
| 32 | 64 | xuôi | có | có | 106 | 131 | -19% |
| 32 | 64 | ngược | có | có | 106 | 131 | -19% |
| 32 | 128 | xuôi | có | có | 145 | 176 | -18% |
| 32 | 128 | ngược | có | có | 145 | 176 | -18% |
| 32 | 256 | xuôi | có | có | 193 | 248 | -22% |
| 32 | 256 | ngược | có | có | 193 | 248 | -22% |
| 32 | 512 | xuôi | có | có | 274 | 380 | -28% |
| 32 | 512 | ngược | có | có | 274 | 380 | -28% |
| 32 | 1024 | xuôi | có | có | 451 | 644 | -30% |
| 32 | 1024 | ngược | có | có | 451 | 644 | -30% |
| 64 | 64 | xuôi | có | có | 158 | 227 | -30% |
| 64 | 64 | ngược | có | có | 158 | 227 | -30% |
| 64 | 128 | xuôi | có | có | 261 | 345 | -24% |
| 64 | 128 | ngược | có | có | 261 | 345 | -24% |
| 64 | 256 | xuôi | có | có | 400 | 571 | -30% |
| 64 | 256 | ngược | có | có | 400 | 571 | -30% |
| 64 | 512 | xuôi | có | có | 790 | 1037 | -24% |
| 64 | 512 | ngược | có | có | 790 | 1037 | -24% |
| 64 | 1024 | xuôi | có | có | 1750 | 2031 | -14% |
| 64 | 1024 | ngược | có | có | 1750 | 2031 | -14% |
| 128 | 64 | xuôi | có | có | 327 | 570 | -43% |
| 128 | 64 | ngược | có | có | 327 | 570 | -43% |
| 128 | 128 | xuôi | có | có | 679 | 973 | -30% |
| 128 | 128 | ngược | có | có | 679 | 973 | -30% |
| 128 | 256 | xuôi | có | có | 1367 | 1808 | -24% |
| 128 | 256 | ngược | có | có | 1367 | 1808 | -24% |
| 128 | 512 | xuôi | có | có | 3095 | 3603 | -14% |
| 128 | 512 | ngược | có | có | 3095 | 3603 | -14% |
| 128 | 1024 | xuôi | có | có | 6935 | 7510 | -8% |
| 128 | 1024 | ngược | có | có | 6935 | 7510 | -8% |

## Mạng và root

| Chế độ | Cổng đọc x / y mỗi tile, mọi N | Cổng ghi mỗi superbank, mọi N | Cổng đọc, N ≥ 64 | Cổng ghi, N ≥ 64 |
|---|---:|---:|---:|---:|
| NTT | 11 / 10 | 11 | 8 / 8 | 8 |
| FFT32 | 5 / 6 | 6 | 4 / 4 | 4 |
| FFT64 | 5 / 6 | 6 | 4 / 4 | 4 |
| FFT128 | 5 / 6 | 6 | 4 / 4 | 4 |
| mọi chế độ | 11 / 10 | 11 | 8 / 8 | 8 |

Lõi hiện tại: mỗi nửa 16 bit của cổng toán hạng chọn tới 6 superbank (mạng có cấu trúc), mỗi bank có bộ chọn hàng giữa các tile, và địa chỉ được tính riêng cho từng tile.

Root theo tầng (số tầng): NTT: bảng riêng mỗi tile, địa chỉ chung 286, một root chung 98, mỗi tile một root cả tầng 242; FFT32: bảng riêng mỗi tile, địa chỉ chung 28, một root chung 16, mỗi tile một root cả tầng 44; FFT64: bảng riêng mỗi tile, địa chỉ chung 28, một root chung 16, mỗi tile một root cả tầng 44; FFT128: bảng riêng mỗi tile, địa chỉ chung 28, một root chung 16, mỗi tile một root cả tầng 44. Không tầng nào cần địa chỉ root riêng cho từng tile.

Số từ root mỗi tile cho một lệnh (một chiều): FFT128 N1024: 50, FFT32 N1024: 50, FFT64 N1024: 50, NTT N256: 26, NTT N256 hmin 1: 25, NTT N256 hmin 2: 24, NTT N1024: 98, NTT N1024 hmin 1: 97, NTT N1024 hmin 2: 96 (FFT: số root phức, mỗi root L từ thực + L từ ảo).
