Cấu hình: 32 tile, bộ nhớ 512 bit đọc/chu kỳ (ghi bằng đọc). Diện tích bộ nhân proxy = P² mỗi leaf.

### Bảng chính: leaf được yêu cầu

| Leaf | Phép | Leaf/butterfly | Tích riêng/tích | Hiệu suất bit | Trần tính toán | Trần bộ nhớ | Đạt được | Giới hạn | Leaf bận | BF/chu kỳ trên 32k diện tích |
|---|---|---|---|---|---|---|---|---|---|---|
| L32 (32x32, sign-select) | NTT q=3329 (12b) | 1 | 1 | 14.1% | 32 | 16 | 16 | memory | 50.0% | 16 |
| L32 (32x32, sign-select) | NTT q=12289 (14b) | 1 | 1 | 19.1% | 32 | 16 | 16 | memory | 50.0% | 16 |
| L32 (32x32, sign-select) | NTT q=8380417 (23b) | 1 | 1 | 51.7% | 32 | 8 | 8 | memory | 25.0% | 8 |
| L32 (32x32, sign-select) | NTT RNS 32b (Montgomery) | 3 | 1 | 83.9% | 10.7 | 8 | 8 | memory | 75.0% | 8 |
| L32 (32x32, sign-select) | FFT32 | 4 | 1 | 100.0% | 8 | 4 | 4 | memory | 50.0% | 4 |
| L32 (32x32, sign-select) | FFT64 | 16 | 4 | 100.0% | 2 | 2 | 2 | both | 100.0% | 2 |
| L32 (32x32, sign-select) | FFT128 | 64 | 16 | 100.0% | 0.5 | 1 | 0.5 | compute | 100.0% | 0.5 |
| L17 (17x17, signed-only) | NTT q=3329 (12b) | 1 | 1 | 49.8% | 128 | 16 | 16 | memory | 12.5% | 14.2 |
| L17 (17x17, signed-only) | NTT q=12289 (14b) | 1 | 1 | 67.8% | 128 | 16 | 16 | memory | 12.5% | 14.2 |
| L17 (17x17, signed-only) | NTT q=8380417 (23b) | 4 | 4 | 45.8% | 32 | 8 | 8 | memory | 25.0% | 7.09 |
| L17 (17x17, signed-only) | NTT RNS 32b (Montgomery) | 11 | 4 | 81.0% | 11.6 | 8 | 8 | memory | 68.8% | 7.09 |
| L17 (17x17, signed-only) | FFT32 | 16 | 4 | 88.6% | 8 | 4 | 4 | memory | 50.0% | 3.54 |
| L17 (17x17, signed-only) | FFT64 | 64 | 16 | 88.6% | 2 | 2 | 2 | both | 100.0% | 1.77 |
| L17 (17x17, signed-only) | FFT128 | 256 | 64 | 88.6% | 0.5 | 1 | 0.5 | compute | 100.0% | 0.443 |

### Độ nhạy: băng thông bộ nhớ (butterfly/chu kỳ đạt được)

| Leaf | Phép | 512 bit | 1024 bit | 2048 bit |
|---|---|---|---|---|
| L32 (32x32, sign-select) | NTT q=3329 (12b) | 16 | 32 | 32 |
| L32 (32x32, sign-select) | NTT q=12289 (14b) | 16 | 32 | 32 |
| L32 (32x32, sign-select) | NTT q=8380417 (23b) | 8 | 16 | 32 |
| L32 (32x32, sign-select) | NTT RNS 32b (Montgomery) | 8 | 10.7 | 10.7 |
| L32 (32x32, sign-select) | FFT32 | 4 | 8 | 8 |
| L32 (32x32, sign-select) | FFT64 | 2 | 2 | 2 |
| L32 (32x32, sign-select) | FFT128 | 0.5 | 0.5 | 0.5 |
| L17 (17x17, signed-only) | NTT q=3329 (12b) | 16 | 32 | 64 |
| L17 (17x17, signed-only) | NTT q=12289 (14b) | 16 | 32 | 64 |
| L17 (17x17, signed-only) | NTT q=8380417 (23b) | 8 | 16 | 32 |
| L17 (17x17, signed-only) | NTT RNS 32b (Montgomery) | 8 | 11.6 | 11.6 |
| L17 (17x17, signed-only) | FFT32 | 4 | 8 | 8 |
| L17 (17x17, signed-only) | FFT64 | 2 | 2 | 2 |
| L17 (17x17, signed-only) | FFT128 | 0.5 | 0.5 | 0.5 |
| L16 (16x16, sign-select) | NTT q=3329 (12b) | 16 | 32 | 64 |
| L16 (16x16, sign-select) | NTT q=12289 (14b) | 16 | 32 | 64 |
| L16 (16x16, sign-select) | NTT q=8380417 (23b) | 8 | 16 | 32 |
| L16 (16x16, sign-select) | NTT RNS 32b (Montgomery) | 8 | 11.6 | 11.6 |
| L16 (16x16, sign-select) | FFT32 | 4 | 8 | 8 |
| L16 (16x16, sign-select) | FFT64 | 2 | 2 | 2 |
| L16 (16x16, sign-select) | FFT128 | 0.5 | 0.5 | 0.5 |
| L33 (33x33, signed-only) | NTT q=3329 (12b) | 16 | 32 | 32 |
| L33 (33x33, signed-only) | NTT q=12289 (14b) | 16 | 32 | 32 |
| L33 (33x33, signed-only) | NTT q=8380417 (23b) | 8 | 16 | 32 |
| L33 (33x33, signed-only) | NTT RNS 32b (Montgomery) | 8 | 10.7 | 10.7 |
| L33 (33x33, signed-only) | FFT32 | 4 | 8 | 8 |
| L33 (33x33, signed-only) | FFT64 | 2 | 2 | 2 |
| L33 (33x33, signed-only) | FFT128 | 0.5 | 0.5 | 0.5 |

### Độ nhạy: cách xử lý dấu ở leaf và twiddle hẹp

| Leaf | Phép | Leaf/butterfly | Hiệu suất bit | Đạt được | BF/chu kỳ trên 32k diện tích | Diện tích bộ nhân |
|---|---|---|---|---|---|---|
| L32 (32x32, sign-select) | FFT64 tw32 | 8 | 100.0% | 2 | 2 | 32768 |
| L32 (32x32, sign-select) | FFT128 tw64 | 32 | 100.0% | 1 | 1 | 32768 |
| L17 (17x17, signed-only) | FFT64 tw32 | 32 | 88.6% | 2 | 1.77 | 36992 |
| L17 (17x17, signed-only) | FFT128 tw64 | 128 | 88.6% | 1 | 0.886 | 36992 |
| L16 (16x16, sign-select) | NTT q=3329 (12b) | 1 | 56.2% | 16 | 16 | 32768 |
| L16 (16x16, sign-select) | NTT q=12289 (14b) | 1 | 76.6% | 16 | 16 | 32768 |
| L16 (16x16, sign-select) | NTT q=8380417 (23b) | 4 | 51.7% | 8 | 8 | 32768 |
| L16 (16x16, sign-select) | NTT RNS 32b (Montgomery) | 11 | 91.5% | 8 | 8 | 32768 |
| L16 (16x16, sign-select) | FFT32 | 16 | 100.0% | 4 | 4 | 32768 |
| L16 (16x16, sign-select) | FFT64 | 64 | 100.0% | 2 | 2 | 32768 |
| L16 (16x16, sign-select) | FFT128 | 256 | 100.0% | 0.5 | 0.5 | 32768 |
| L16 (16x16, sign-select) | FFT64 tw32 | 32 | 100.0% | 2 | 2 | 32768 |
| L16 (16x16, sign-select) | FFT128 tw64 | 128 | 100.0% | 1 | 1 | 32768 |
| L33 (33x33, signed-only) | NTT q=3329 (12b) | 1 | 13.2% | 16 | 15 | 34848 |
| L33 (33x33, signed-only) | NTT q=12289 (14b) | 1 | 18.0% | 16 | 15 | 34848 |
| L33 (33x33, signed-only) | NTT q=8380417 (23b) | 1 | 48.6% | 8 | 7.52 | 34848 |
| L33 (33x33, signed-only) | NTT RNS 32b (Montgomery) | 3 | 78.8% | 8 | 7.52 | 34848 |
| L33 (33x33, signed-only) | FFT32 | 4 | 94.0% | 4 | 3.76 | 34848 |
| L33 (33x33, signed-only) | FFT64 | 16 | 94.0% | 2 | 1.88 | 34848 |
| L33 (33x33, signed-only) | FFT128 | 64 | 94.0% | 0.5 | 0.47 | 34848 |
| L33 (33x33, signed-only) | FFT64 tw32 | 8 | 94.0% | 2 | 1.88 | 34848 |
| L33 (33x33, signed-only) | FFT128 tw64 | 32 | 94.0% | 1 | 0.94 | 34848 |

### Proxy chi phí ghép

| Leaf | Các kích thước nhóm (tích riêng/tích) | Bit vào cây gom, tích rộng nhất (proxy) |
|---|---|---|
| L32 (32x32, sign-select) | [1, 4, 16] | 1024 (FFT128) |
| L17 (17x17, signed-only) | [1, 4, 16, 64] | 2176 (FFT128) |
| L16 (16x16, sign-select) | [1, 4, 16, 64] | 2048 (FFT128) |
| L33 (33x33, signed-only) | [1, 4, 16] | 1056 (FFT128) |
