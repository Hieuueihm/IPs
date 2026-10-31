# Trần và dự báo cho đề xuất kiến trúc v1

## 1. Luật lane theo độ rộng toán hạng [model]

| Miền | Toán hạng | Leaf/tích | Tích/chu kỳ (64 leaf) | Đơn vị công việc/chu kỳ |
|---|---|---:|---:|---|
| FFT | W32 (Q16.16) | 4 | 16 | 5.33 butterfly (3M) |
| FFT | W64 (Q32.32) | 16 | 4 | 1.33 butterfly (3M) |
| FFT | W128 (Q64.64) | 64 | 1 | 0.333 butterfly (3M) |
| NTT | RES16: 3329, 12289 | 1 | 64 | 64 butterfly-tầng (1 modmul/BF) |
| NTT | RES32: 8380417 (đề xuất) | 4 | 16 | 16 butterfly-tầng (1 modmul/BF) |
| NTT | RES32 RNS tổng quát (tùy chọn) | 4 ×3 tích | 16 | 5.33 modmul (T, m, m·q trên tile) |

Cùng một luật cho hai miền: tích/chu kỳ = 64 / (w/16)². Hạng FFT bị bỏ theo contract (W128: 58/64 leaf) không làm tăng số tích/chu kỳ trong bố trí cây hiện tại.

## 2. FFT N1024: dự báo cycle/kernel [projection]

Giả định: controller tách đọc/tính/ghi, II = 1 theo batch, đọc và ghi song song (1R+1W), rào chắn giữa tầng tốn L chu kỳ. Batch và map bank giống `model/fft_batch_supply.py` (kiểm khớp bên dưới); root store xen kẽ theo idx mod R_tw, đếm chính xác số lần đọc mỗi bank root; không cache root giữa batch. Đo hiện tại [measured] = 52 992 cycle cho cả ba W.

- PASS batch/map khớp `study/results/fft_batch_supply.json` (W32/64/128, N1024).

| W | Batch | Map bank | R_tw | L | Cycle/kernel | So với đo | Tầng chặn bởi tính/dữ liệu/twiddle |
|---:|---|---|---:|---:|---:|---:|---|
| 32 | 1 BF (chỉ pipeline) | hiện tại | 1 | 8 | 4680 | 11.3× | 0/9/0 |
| 64 | 1 BF (chỉ pipeline) | hiện tại | 1 | 8 | 5192 | 10.2× | 0/9/0 |
| 128 | 1 BF (chỉ pipeline) | hiện tại | 1 | 8 | 7496 | 7.1× | 7/2/0 |
| 32 | 16 BF | hiện tại | 1 | 8 | 840 | 63.1× | 4/2/3 |
| 32 | 16 BF | hiện tại | 4 | 8 | 552 | 96.0× | 6/2/1 |
| 32 | 16 BF | hiện tại | 16 | 8 | 536 | 98.9× | 7/2/0 |
| 32 | 16 BF | lý tưởng | 1 | 8 | 808 | 65.6× | 6/0/3 |
| 32 | 16 BF | lý tưởng | 4 | 8 | 520 | 101.9× | 8/0/1 |
| 32 | 16 BF | lý tưởng | 16 | 0 | 432 | 122.7× | 9/0/0 |
| 32 | 16 BF | lý tưởng | 16 | 8 | 504 | 105.1× | 9/0/0 |
| 64 | 4 BF | hiện tại | 1 | 8 | 1928 | 27.5× | 7/1/1 |
| 64 | 4 BF | hiện tại | 4 | 8 | 1864 | 28.4× | 8/1/0 |
| 64 | 4 BF | hiện tại | 16 | 8 | 1864 | 28.4× | 8/1/0 |
| 64 | 4 BF | lý tưởng | 1 | 8 | 1864 | 28.4× | 8/0/1 |
| 64 | 4 BF | lý tưởng | 4 | 8 | 1800 | 29.4× | 9/0/0 |
| 64 | 4 BF | lý tưởng | 16 | 0 | 1728 | 30.7× | 9/0/0 |
| 64 | 4 BF | lý tưởng | 16 | 8 | 1800 | 29.4× | 9/0/0 |
| 128 | 1 BF | hiện tại | 1 | 8 | 7496 | 7.1× | 7/2/0 |
| 128 | 1 BF | hiện tại | 4 | 8 | 7496 | 7.1× | 7/2/0 |
| 128 | 1 BF | hiện tại | 16 | 8 | 7496 | 7.1× | 7/2/0 |
| 128 | 1 BF | lý tưởng | 1 | 8 | 6984 | 7.6× | 9/0/0 |
| 128 | 1 BF | lý tưởng | 4 | 8 | 6984 | 7.6× | 9/0/0 |
| 128 | 1 BF | lý tưởng | 16 | 0 | 6912 | 7.7× | 9/0/0 |
| 128 | 1 BF | lý tưởng | 16 | 8 | 6984 | 7.6× | 9/0/0 |

- PASS batch/map khớp JSON cho mọi case FFT và IFFT, N4..N1024.

FFT và IFFT, N512/N1024, map hiện tại, L = 8 (A1 + A2, có/không B):

| Op | N | W | R_tw = 1 | R_tw = 4 | T128/T_W (R_tw = 4) |
|---|---:|---:|---:|---:|---:|
| FFT | 512 | 32 | 408 | 264 | 12.36 |
| FFT | 512 | 64 | 864 | 832 | 3.92 |
| FFT | 512 | 128 | 3264 | 3264 | 1.00 |
| FFT | 1024 | 32 | 840 | 552 | 13.58 |
| FFT | 1024 | 64 | 1928 | 1864 | 4.02 |
| FFT | 1024 | 128 | 7496 | 7496 | 1.00 |
| IFFT | 512 | 32 | 408 | 264 | 12.36 |
| IFFT | 512 | 64 | 864 | 832 | 3.92 |
| IFFT | 512 | 128 | 3264 | 3264 | 1.00 |
| IFFT | 1024 | 32 | 840 | 552 | 13.58 |
| IFFT | 1024 | 64 | 1928 | 1864 | 4.02 |
| IFFT | 1024 | 128 | 7496 | 7496 | 1.00 |

Độ nhạy theo L (map hiện tại, R_tw = 4, batch theo W):

| W | L = 8 | L = 12 | L = 16 |
|---:|---:|---:|---:|
| 32 | 552 | 588 | 624 |
| 64 | 1864 | 1900 | 1936 |
| 128 | 7496 | 7532 | 7568 |

## 3. NTT: dự báo cycle/batch [projection]

Giả định: frame II = 1, đọc/ghi song song, map bank không xung đột cho hai tầng (đã kiểm 28 case ở docs/stream_core_results.md cho RES16), rào chắn L chu kỳ/lượt.

| Profile | N | Job/batch | Tầng | Đo hiện tại (1 job) | L=0 | L=8 | Cycle/job ở L=8 | So với đo/job |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| q12289 RES16 | 1024 | 1 | 10 | 800 | 80 | 120 | 120.0 | 6.7× |
| q12289 RES16 | 256 | 1 | 8 | 160 | 16 | 48 | 48.0 | 3.3× |
| q3329 RES16 | 256 | 1 | 7 | 160 | 16 | 48 | 48.0 | 3.3× |
| q12289 RES16 | 8 | 8 | 3 | 20 | 2 | 18 | 2.2 | 8.9× |
| q12289 RES16 | 16 | 4 | 4 | 20 | 2 | 18 | 4.5 | 4.4× |
| q12289 RES16 | 32 | 2 | 5 | 30 | 3 | 27 | 13.5 | 2.2× |
| q8380417 RES32 (đề xuất) | 256 | 1 | 8 | — | 64 | 96 | 96.0 | — |

RES32 dùng 2 bank/hệ số (32 hệ số/chu kỳ), 1 tile/modmul (16 modmul/chu kỳ); chưa có RTL nên không có số đo. Không xung đột bank (mục 3b). Nếu xung đột 2 lượt, dự báo sẽ là 160 cycle — giữ để đối chiếu.

Độ nhạy theo L (L đo được của frame NTT hiện tại ≈ 9: READ, LATCH, ISSUE, 5 chờ mảng, WRITE):

| Profile | N | L = 8 | L = 12 | L = 16 |
|---|---:|---:|---:|---:|
| q12289 RES16 | 1024 | 120 | 140 | 160 |
| q12289 RES16 | 256 | 48 | 64 | 80 |
| q8380417 RES32 | 256 | 96 | 112 | 128 |

Xen kẽ hai context (REF16 có 2 context) cho hai đa thức độc lập cùng cấu hình, mỗi lượt tốn max(2·frame, frame + L) chu kỳ cho cả hai [projection, L = 8]:

| Profile | N | Tầng | 1 job, L=8 | 2 job xen kẽ | Cycle/job | So với đo/job |
|---|---:|---:|---:|---:|---:|---:|
| q12289 RES16 | 1024 | 10 | 120 | 160 | 80.0 | 10.0× |
| q12289 RES16 | 256 | 8 | 48 | 48 | 24.0 | 6.7× |
| q8380417 RES32 (đề xuất) | 256 | 8 | 96 | 128 | 64.0 | — |

## 3c. NTT khi rút gọn Montgomery chạy trên mảng nhân [projection, đã thay bằng mục 3d]

Mục này dùng cùng L cho cả hai cách rút gọn nên đánh giá quá lạc quan; tài liệu dùng mục 3d.

16 bit: 3 leaf/phép nhân modulo → 21,3 phép/chu kỳ; 32 bit: 3 lượt × 4 leaf trong một tile → 5,33 phép/chu kỳ (model/mont_on_array_tile.py). Cùng giả định với mục 3.

| Trường hợp | Rút gọn riêng, L=8 | Trên mảng, L=8 | Trên mảng, L=12 | Trên mảng, L=16 | Trên mảng, 2 đa thức xen kẽ (mỗi đa thức), L=8 | Đo hiện tại |
|---|---:|---:|---:|---:|---:|---:|
| q12289 N1024 | 120 | 280 | 300 | 320 | 240 | 800 |
| q12289 N256 | 48 | 80 | 96 | 112 | 48 | 160 |
| q3329 N256 | 48 | 74 | 90 | 106 | 43 | 160 |
| q8380417 N256 (32 bit) | 96 | 224 | 240 | 256 | 192 | — |

Mô hình ở L đo được (ngưỡng giả thuyết = 1,25 × mô hình), L = 9: q12289 N1024 = 285, q12289 N256 = 84, q8380417 N256 = 228, 2 đa thức q12289 N256 = 48/đa thức.

## 3d. NTT có tính độ trễ nhịp hai tầng [projection]

Tốc độ nhịp và độ trễ nhịp lấy từ mô hình tile (`model/mont_on_array_tile.py`, nhịp hai tầng, tầng 2 chờ tầng 1); thêm 2 chu kỳ đọc/ghi RAM. Mỗi lượt = số nhịp/(16 × tốc độ) + độ trễ. Xen kẽ 2 đa thức: mỗi lượt max(2·F, F + độ trễ).

| Trường hợp | Độ trễ bộ nhân | Rút gọn | Nhịp/chu kỳ/tile | Độ trễ nhịp | Một đa thức | Hai đa thức xen kẽ (mỗi đa thức) | Đo hiện tại |
|---|---:|---|---:|---:|---:|---:|---:|
| q12289 N1024 | 3 | riêng | 1 | 14 | 150 | 80 | 800 |
| q12289 N1024 | 3 | trên mảng | 0.333 | 24 | 360 | 240 | 800 |
| q12289 N1024 | 4 | riêng | 1 | 16 | 160 | 80 | 800 |
| q12289 N1024 | 4 | trên mảng | 0.333 | 30 | 390 | 240 | 800 |
| q12289 N256 | 3 | riêng | 1 | 14 | 72 | 36 | 160 |
| q12289 N256 | 3 | trên mảng | 0.333 | 24 | 144 | 72 | 160 |
| q12289 N256 | 4 | riêng | 1 | 16 | 80 | 40 | 160 |
| q12289 N256 | 4 | trên mảng | 0.333 | 30 | 168 | 84 | 160 |
| q8380417 N256 (32 bit) | 3 | riêng | 0.25 | 16 | 128 | 64 | — |
| q8380417 N256 (32 bit) | 3 | trên mảng | 0.0833 | 26 | 296 | 192 | — |
| q8380417 N256 (32 bit) | 4 | riêng | 0.25 | 18 | 136 | 68 | — |
| q8380417 N256 (32 bit) | 4 | trên mảng | 0.0833 | 32 | 320 | 192 | — |

Tỉ lệ chậm của rút gọn trên mảng so với rút gọn riêng (độ trễ bộ nhân 4):
- q12289 N1024: một đa thức 2.44×, hai đa thức xen kẽ 3.00×
- q12289 N256: một đa thức 2.10×, hai đa thức xen kẽ 2.10×
- q8380417 N256 (32 bit): một đa thức 2.35×, hai đa thức xen kẽ 2.82×

## 3e. NTT modulo prime 31 bit của NTRUGen (lane 32 bit, rút gọn trên mảng) [projection]

Độ trễ bộ nhân 4; 1.33 nhịp/chu kỳ cho 16 tile, độ trễ nhịp 32 (mô hình tile, cấu hình 32 bit). Lượt một tầng cuối khi logn lẻ: n/2 butterfly ở 16/3 phép nhân modulo/chu kỳ, lấy độ trễ bằng một nhịp (cận trên). Xung đột bank ở N1024 (20% chu kỳ đọc hai lượt) không làm chậm: phần tính chỉ dùng 1,33 trong 4 nhịp/chu kỳ mà bộ nhớ cấp được. Nạp prime theo spec 2.0 (02 mục 3): host ghi vùng C (1 dòng đầu + N/4 dòng 128 bit mỗi bảng), rồi phép nạp xếp ~N/2 gói mỗi bảng qua 4 bank (ước lượng thấp nhất N/8 chu kỳ mỗi bảng). Một lần nạp ở N lớn nhất dùng được cho mọi N nhỏ hơn.

| N | Lượt hai tầng | Lượt một tầng | NTT (chu kỳ) | Host ghi vùng C, một bảng / hai bảng (dòng) | Phép nạp, một bảng / hai bảng (chu kỳ, thấp nhất) |
|---:|---:|---:|---:|---:|---:|
| 2 | 0 | 1 | 33 | 2 / 2 | 1 / 2 |
| 4 | 1 | 0 | 33 | 2 / 3 | 1 / 2 |
| 8 | 1 | 1 | 67 | 3 / 5 | 1 / 2 |
| 16 | 2 | 0 | 70 | 5 / 9 | 2 / 4 |
| 32 | 2 | 1 | 111 | 9 / 17 | 4 / 8 |
| 64 | 3 | 0 | 132 | 17 / 33 | 8 / 16 |
| 128 | 3 | 1 | 212 | 33 / 65 | 16 / 32 |
| 256 | 4 | 0 | 320 | 65 / 129 | 32 / 64 |
| 512 | 4 | 1 | 592 | 129 / 257 | 64 / 128 |
| 1024 | 5 | 0 | 1120 | 257 / 513 | 128 / 256 |

## 3b. RES32: cặp bank có cấp đủ hai tầng không? [model]

Hệ số 32 bit chiếm hai bank 16 bit cùng row → 32 'siêu bank'. Mỗi chu kỳ phát 4 frame paired (16 hệ số, 16 modmul) hoặc 16 BF một tầng (32 hệ số). Nhóm hệ số theo thứ tự của `model/ntt_banked_supply.py` (groups). Đếm số lượt đọc tối đa mỗi siêu bank.

| Map siêu bank | N | Kiểu | Lượt đọc tối đa/chu kỳ |
|---|---:|---|---:|
| `bank(2c) >> 1 — layout spec 03.4 (LIMBS = 2), chốt` | 256 | paired | 1 |
| `bank(2c) >> 1 — layout spec 03.4 (LIMBS = 2), chốt` | 256 | một tầng | 2 |
| `bank(2c) >> 1 — layout spec 03.4 (LIMBS = 2), chốt` | 1024 | paired | 2 |
| `bank(2c) >> 1 — layout spec 03.4 (LIMBS = 2), chốt` | 1024 | một tầng | 2 |
| `bank(c) >> 1 — sai: map áp lên chỉ số hệ số` | 256 | paired | 2 |
| `bank(c) >> 1 — sai: map áp lên chỉ số hệ số` | 256 | một tầng | 2 |
| `bank(c) >> 1 — sai: map áp lên chỉ số hệ số` | 1024 | paired | 2 |
| `bank(c) >> 1 — sai: map áp lên chỉ số hệ số` | 1024 | một tầng | 2 |
| `c & 31 — sai: bỏ qua map spec` | 256 | paired | 4 |
| `c & 31 — sai: bỏ qua map spec` | 256 | một tầng | 2 |
| `c & 31 — sai: bỏ qua map spec` | 1024 | paired | 4 |
| `c & 31 — sai: bỏ qua map spec` | 1024 | một tầng | 2 |

1 = không xung đột (II = 1). Với layout của spec (hệ số c ở word 2c, 2c + 1), thứ tự nhóm hiện có không xung đột; kiểm chi tiết (cả root bundle) ở `model/res32_bank_map.py`.

## 4. Kiểm tra trần chỉ-tính-toán [model]

- FFT32 N1024: 2 304 butterfly / 5.33 BF/chu kỳ ≥ 432 cycle → tăng tối đa 122.7× so với đo.
- FFT64 N1024: 2 304 butterfly / 1.33 BF/chu kỳ ≥ 1728 cycle → tăng tối đa 30.7× so với đo.
- FFT128 N1024: 2 304 butterfly / 0.333 BF/chu kỳ ≥ 6912 cycle → tăng tối đa 7.7× so với đo.
- NTT q12289 N1024: 5 120 butterfly / 64 ≥ 80 cycle → tối đa 10.0× so với đo 800.

