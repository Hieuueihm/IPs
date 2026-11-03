# Cấp dữ liệu và root cho tile một làn (16 butterfly/chu kỳ)

Mô hình: [model/single_lane_feed.py](../../model/single_lane_feed.py). Bộ nhớ dữ liệu như spec 03 mục 1; gói root ba phần tử như spec 03 mục 4, đọc root con từ gói của nút cha; P = số bank gói root. Xếp tham lam theo thứ tự tự nhiên, có đọc lệch một chu kỳ khi hai toán hạng cùng bank. Một lane 32 bit: mọi NTT, kể cả q nhỏ, lưu dạng 4; độ trễ mỗi lượt 17 (RTL nghiệm thu 15 + 2 chu kỳ RAM). Mạng bank → tile giả định nối đầy đủ; chi phí LUT của nó đo riêng (study/results/structured_net.md).

Tốc độ hiệu dụng = tổng butterfly / tổng chu kỳ phát; lý tưởng là 16 (N nhỏ bị giới hạn bởi số butterfly mỗi tầng, N/2).

## Một đa thức (mọi q)

| N | Chiều | P = 4: chu kỳ phát / tốc độ | P = 8: chu kỳ phát / tốc độ | P = 8: thời gian NTT |
|---:|---|---:|---:|---:|
| 2 | xuôi | 1 / 1.00 | 1 / 1.00 | 18 |
| 2 | ngược | 1 / 1.00 | 1 / 1.00 | 18 |
| 4 | xuôi | 2 / 2.00 | 2 / 2.00 | 36 |
| 4 | ngược | 2 / 2.00 | 2 / 2.00 | 36 |
| 8 | xuôi | 3 / 4.00 | 3 / 4.00 | 54 |
| 8 | ngược | 3 / 4.00 | 3 / 4.00 | 54 |
| 16 | xuôi | 4 / 8.00 | 4 / 8.00 | 72 |
| 16 | ngược | 4 / 8.00 | 4 / 8.00 | 72 |
| 32 | xuôi | 6 / 13.33 | 5 / 16.00 | 90 |
| 32 | ngược | 6 / 13.33 | 5 / 16.00 | 90 |
| 64 | xuôi | 14 / 13.71 | 12 / 16.00 | 114 |
| 64 | ngược | 14 / 13.71 | 12 / 16.00 | 114 |
| 128 | xuôi | 32 / 14.00 | 28 / 16.00 | 147 |
| 128 | ngược | 32 / 14.00 | 28 / 16.00 | 147 |
| 256 | xuôi | 72 / 14.22 | 64 / 16.00 | 200 |
| 256 | ngược | 72 / 14.22 | 64 / 16.00 | 200 |
| 512 | xuôi | 160 / 14.40 | 144 / 16.00 | 297 |
| 512 | ngược | 160 / 14.40 | 144 / 16.00 | 297 |
| 1024 | xuôi | 353 / 14.50 | 321 / 15.95 | 491 |
| 1024 | ngược | 353 / 14.50 | 321 / 15.95 | 491 |

Không đọc lệch, N = 1024 xuôi: 1312 chu kỳ phát, thời gian 1482. Ở tầng khoảng cách 512 cả hai toán hạng của mọi butterfly nằm cùng một siêu bank, vì hàm bank bỏ qua bit 10 của địa chỉ.

## Nhiều đa thức trong một lệnh

N < 64: min(8, 64/N) đa thức, mỗi đa thức một prime (khe riêng, vùng gói riêng, cách nhau G gói), 16/jobs tile mỗi đa thức. N ≥ 64: hai đa thức cùng prime, hai context.

| N | jobs | Chiều | P = 8: chu kỳ phát / tốc độ | Thời gian lệnh | Mỗi đa thức |
|---:|---:|---|---:|---:|---:|
| 2 | 8 | xuôi | 1 / 8.00 | 18 | 2.2 |
| 2 | 8 | ngược | 1 / 8.00 | 18 | 2.2 |
| 4 | 8 | xuôi | 2 / 16.00 | 36 | 4.5 |
| 4 | 8 | ngược | 2 / 16.00 | 36 | 4.5 |
| 8 | 8 | xuôi | 8 / 12.00 | 59 | 7.4 |
| 8 | 8 | ngược | 8 / 12.00 | 59 | 7.4 |
| 16 | 4 | xuôi | 10 / 12.80 | 78 | 19.5 |
| 16 | 4 | ngược | 10 / 12.80 | 78 | 19.5 |
| 32 | 2 | xuôi | 13 / 12.31 | 98 | 49.0 |
| 32 | 2 | ngược | 13 / 12.31 | 98 | 49.0 |
| 64 | 2 | xuôi | 24 / 16.00 | 114 | 57.0 |
| 64 | 2 | ngược | 24 / 16.00 | 114 | 57.0 |
| 128 | 2 | xuôi | 56 / 16.00 | 147 | 73.5 |
| 128 | 2 | ngược | 56 / 16.00 | 147 | 73.5 |
| 256 | 2 | xuôi | 128 / 16.00 | 200 | 100.0 |
| 256 | 2 | ngược | 128 / 16.00 | 200 | 100.0 |
| 512 | 2 | xuôi | 288 / 16.00 | 297 | 148.5 |
| 512 | 2 | ngược | 288 / 16.00 | 297 | 148.5 |
| 1024 | 2 | xuôi | 657 / 15.59 | 657 | 328.5 |
| 1024 | 2 | ngược | 657 / 15.59 | 657 | 328.5 |

