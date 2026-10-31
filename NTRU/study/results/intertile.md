Model ghép liên tile, tile L32; cây nhị phân dịch cố định [0, 32, 32, 64, 64] bit; bộ nhớ 512 bit đọc/chu kỳ.

### Throughput và điểm lấy kết quả

| K | Mode | Tile/đầu ra | Tap (cấp) | Lượt/đầu ra | Accumulator | Lượt/nhóm phát | BF/chu kỳ tính toán | BF/chu kỳ bộ nhớ | Đạt được | Tile bận | Kiểm tra |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 16 | FFT32 | 2 | 1 | 1 | không | 1 | 4 | 4 | 4 | 100% | 3480 |
| 16 | FFT64 | 8 | 3 | 1 | không | 1 | 1 | 2 | 1 | 100% | 870 |
| 16 | FFT128 | 32 | 5 | 2 | có | 4 | 0.25 | 1 | 0.25 | 100% | 870 |
| 16 | FFT64 tw32 (tùy chọn) | 4 | 2 | 1 | không | 1 | 2 | 2 | 2 | 100% | 1740 |
| 16 | FFT128 tw64 (tùy chọn) | 16 | 4 | 1 | không | 2 | 0.5 | 1 | 0.5 | 100% | 870 |
| 32 | FFT32 | 2 | 1 | 1 | không | 1 | 8 | 4 | 4 | 50% | 6960 |
| 32 | FFT64 | 8 | 3 | 1 | không | 1 | 2 | 2 | 2 | 100% | 1740 |
| 32 | FFT128 | 32 | 5 | 1 | không | 2 | 0.5 | 1 | 0.5 | 100% | 870 |
| 32 | FFT64 tw32 (tùy chọn) | 4 | 2 | 1 | không | 1 | 4 | 2 | 2 | 50% | 3480 |
| 32 | FFT128 tw64 (tùy chọn) | 16 | 4 | 1 | không | 1 | 1 | 1 | 1 | 100% | 870 |
| 64 | FFT32 | 2 | 1 | 1 | không | 1 | 16 | 4 | 4 | 25% | 13920 |
| 64 | FFT64 | 8 | 3 | 1 | không | 1 | 4 | 2 | 2 | 50% | 3480 |
| 64 | FFT128 | 32 | 5 | 1 | không | 1 | 1 | 1 | 1 | 100% | 870 |
| 64 | FFT64 tw32 (tùy chọn) | 4 | 2 | 1 | không | 1 | 8 | 2 | 2 | 25% | 6960 |
| 64 | FFT128 tw64 (tùy chọn) | 16 | 4 | 1 | không | 1 | 2 | 1 | 1 | 50% | 1740 |

### Độ rộng nút cây (K = 32, bit có dấu, chặn trên giải tích)

| Mode | Cấp 0 | Cấp 1 | Cấp 2 | Cấp 3 | Cấp 4 | Cấp 5 |
|---|---:|---:|---:|---:|---:|---:|
| FFT32 | 64 | 65 | — | — | — | — |
| FFT64 | 65 | 66 | 97 | 129 | — | — |
| FFT128 | 65 | 66 | 98 | 130 | 193 | 257 |
| FFT64 tw32 | 64 | 65 | 97 | — | — | — |
| FFT128 tw64 | 65 | 66 | 98 | 129 | 193 | — |

### Phần cứng cây gom (K = 32)

| Cấp | Số nút | Độ rộng nút | Độ rộng bộ cộng (bỏ bit thấp đi thẳng) | Phép |
|---:|---:|---:|---:|---|
| 1 | 16 | 66 | 66 | cộng/trừ |
| 2 | 8 | 98 | 66 | cộng, dịch 32 |
| 3 | 4 | 130 | 98 | cộng, dịch 32 |
| 4 | 2 | 193 | 129 | cộng, dịch 64 |
| 5 | 1 | 257 | 193 | cộng, dịch 64 |

Tổng bit bộ cộng: 2427.

### Bộ làm tròn theo điểm tap (K = 32)

| Cấp tap | Số đầu ra/chu kỳ | Độ rộng vào | Mode dùng |
|---:|---:|---:|---|
| 1 | 16 | 65 | FFT32 |
| 2 | 8 | 97 | FFT64 tw32 |
| 3 | 4 | 129 | FFT64 |
| 4 | 2 | 193 | FFT128 tw64 |
| 5 | 1 | 257 | FFT128 |

Nếu mỗi điểm tap có bộ làm tròn riêng: 31 bộ, tổng 2975 bit vào.

### Fan-in toán hạng mỗi tile (K = 32, mọi mode FFT)

- Ngõ dữ liệu: tối đa 4 lane 32 bit khác nhau, trung bình 3.12.
- Ngõ twiddle: tối đa 6 lane, trung bình 4.19.
- Lane = vị trí 32 bit trong vector toán hạng đóng gói (br|bi mỗi butterfly, wr|wi). Chưa tối ưu thứ tự đóng gói; NTT chưa tính.
