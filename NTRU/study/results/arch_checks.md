# Kiểm tra số cho ARCHITECTURE.md

## A. Contract FFT (R8) và phép phân rã phần cứng

- PASS fpr_mul(R8) = floor((x·y + 2^63)/2^64) mod 2^128: 100081 cặp.
- PASS fpr_div2e(x, n) = floor(wrap128(x + 2^(n−1)) / 2^n), n = 0 là đồng nhất (n = 0..10). Phép cộng wrap trước khi dịch: khác floor((x + 2^(n−1))/2^n) chỉ khi x ≥ 2^127 − 2^(n−1).
- PASS FPC_MUL(R8, 3M) = cây phần cứng (leaf 32 và 16, bỏ hạng thừa, tổng twiddle từ ROM): 30081 phép nhân phức.
- 3M (R8) so với 4M cùng quy tắc làm tròn: phần thực luôn bằng, phần ảo khác ở 20006/50000 (40.0%) trường hợp (|a| < 2^6, |b| ≤ 1 dạng Q64.64).
- PASS contract cùng quy tắc cho W = 32/64 (Q16.16, Q32.32): cây phần cứng khớp định nghĩa (leaf 16 và 32). Lưu ý: W = 32/64 không có reference R8.

## A2. Contract NG64 (NTRUGen Q32.32, keygen FFT)

- PASS fxr_mul (đường int128 và đường limb 32 bit) = wrap64(floor(x·y/2^32)) = cây phần cứng bias 0 (leaf 32 và 16, bỏ hạng ≥ 96 bit): 100081 cặp.
- PASS fxr_div2e(v, 1) = floor(wrap64(v + 1)/2).
- PASS fxc_mul 3M khớp giữa hai đường nhân và giao hoán theo thứ tự toán hạng (s, y) ↔ (y, s).
- PASS vect_FFT/vect_iFFT (NTRUGen, viết lại) = lịch chỉ số R8 với primitive NG64 (GM[m+i], iFFT chia đôi hai nhánh mỗi tầng, không chia cuối): 18 transform, logn 2..10; FFT logn ≤ 6 còn khớp với cmul dựng từ cây phần cứng bias 0.

## B. Hạng giữ lại, cây dịch cố định, độ rộng

| Leaf | W | Tích limb đủ | Giữ lại | Dịch theo cấp | Bit cộng một cây (nút ≤ 3W/2 bit) |
|---:|---:|---:|---:|---|---:|
| 32 | 32 | 1 | 1 | [] | 0 |
| 32 | 64 | 4 | 4 | [32, 32] | 192 |
| 32 | 128 | 16 | 15 | [32, 32, 64, 64] | 1158 |
| 16 | 32 | 4 | 4 | [16, 16] | 96 |
| 16 | 64 | 16 | 15 | [16, 16, 32, 32] | 582 |
| 16 | 128 | 64 | 58 | [16, 16, 32, 32, 64, 64] | 2734 |

## C. Trần throughput FFT (3M) và dữ liệu

Tích thực theo cây (một cây = k² vị trí leaf, kể cả vị trí bỏ trống); 3 tích/nhân phức.

| Mode | R32 (32 leaf): tích/chu kỳ → BF | F16 (128 leaf): tích/chu kỳ → BF | Trần dữ liệu 512 / 1024 / 2048 |
|---|---|---|---|
| FFT32 | 32 → 10.7 | 32 → 10.7 | 4 / 8 / 16 |
| FFT64 | 8 → 2.67 | 8 → 2.67 | 2 / 4 / 8 |
| FFT128 | 2 → 0.667 | 2 → 0.667 | 1 / 2 / 4 |

Bus sản phẩm tại trần dữ liệu 512 bit, làm tròn ngay tại gốc cây (khe 32 bit):

| Mode | Tích/chu kỳ | Bit/tích | Khe 32 bit |
|---|---:|---:|---:|
| FFT32 | 12 | 32 | 12 |
| FFT64 | 6 | 64 | 12 |
| FFT128 (trung bình 2 tích/chu kỳ) | 2 | 128 | 8 |
| NTT 3329/12289: T | 16 | 28 | 16 |
| NTT 8380417: T | 8 | 46 | 16 |
| NTT prime RNS: T (m, m·q đi đường nội bộ) | 8 | 64 | 16 |
- Nếu cả T (64 bit), m (32 bit) và m·q (64 bit) của Montgomery tổng quát đều qua bus khe 32 bit: 5 khe/modmul → trần 3.20 modmul/chu kỳ; với bus cũ 16 khe × 65 bit (1 khe/tích): 5.33. Cả hai thấp hơn trần dữ liệu 8 của lane 32 bit.

## D. NTT: Montgomery, hằng số, root

- PASS Montgomery tổng quát R = 2^32: S < 2^65, u < 2q, kết quả = a·b·R^(−1) mod q (q = 3329, 12289, 8380417, 2013265921, 4293918721).

| q | R | Hằng số | CSD hằng số | CSD q | T tối đa (bit) |
|---:|---|---:|---|---|---:|
| 3329 | 2^16 | 3327 (−q⁻¹) | +2^12 −2^10 +2^8 −2^0 | +2^12 −2^10 +2^8 +2^0 | 24 |
| 12289 | 2^16 | 12287 (−q⁻¹) | +2^14 −2^12 −2^0 | +2^14 −2^12 +2^0 | 28 |
| 8380417 | 2^32 | 58728449 (q⁻¹) | +2^26 −2^23 +2^13 +2^0 | +2^23 −2^13 +2^0 | 46 |
- PASS reducer (T + m·q)/2^16, q = 3329: S ≤ 229241599 < 2^28, u < 2q.
- PASS reducer (T + m·q)/2^16, q = 12289: S ≤ 956354559 < 2^30, u < 2q.
- PASS reducer (T − m·q)/2^32 với m có dấu, q = 8380417: kết quả trong (−q, q), +q nếu âm.
- Bậc root: 17 mod 3329 = 256 (ML-KEM, N = 256 → NTT không đầy đủ); 1753 mod 8380417 = 512 (ML-DSA, 2N); 12289 có root bậc 2048 (ví dụ 1945).
- PASS root nghịch: bậc 2N → ψ^(−k) = −ψ^(N−k); bậc N (ML-KEM) → ζ^(−k) = ζ^(N−k) (không đổi dấu; 17^(−1) = 1175 ≠ −17^255 = 2154).
- PASS Mont(w·R, s·R) = (w·s)·R mod q (sinh twiddle trong miền Montgomery).
- PASS half_q(x) = (x + (x&1)·q) >> 1 = x/2 mod q, kết quả < q.
- F16 Montgomery tổng quát: T 4 leaf + m (nửa thấp) 3 leaf + m·q 4 leaf = 11 leaf.

- PASS ML-KEM N=256, 7 tầng: inverse chưa chuẩn hóa cho 128*x; factor là 128^(-1), không phải 256^(-1). Reference gộp Montgomery: R²/128 mod 3329 = 1441 (22 vector số nguyên; chưa phải differential C/RTL).

## D2. Montgomery chạy trên mảng nhân dùng chung (biến thể cộng, q' = −q⁻¹ mod R)

Mỗi tích là tổng các tích leaf 16×16 có chọn dấu; bước cuối là bộ cộng chung u = T_cao + (m·q)_cao + [T_thấp ≠ 0], rồi trừ q nếu u ≥ q.

| q | R | Leaf/phép nhân modulo (T + m + m·q) | Phép nhân modulo/chu kỳ (64 leaf) |
|---:|---|---:|---:|
| 3329 | 2^16 | 3 | 21.3 |
| 12289 | 2^16 | 3 | 21.3 |
| 8380417 | 2^32 | 11 | 5.82 |
| 2013265921 | 2^32 | 11 | 5.82 |
| 4293918721 | 2^32 | 11 | 5.82 |

- PASS: T, m (chỉ nửa thấp) và m·q dựng từ tích leaf; bộ cộng chung cho kết quả đúng a·b·R⁻¹ mod q, u < 2q (20 004 mẫu mỗi q, gồm 0, 1, q−1).

## E. Mô hình latency có rào chắn giữa stage (giả định)

- R32, 1024 bit: P = 32, N = 256, L = 8 → 10.67 BF/chu kỳ.
- F16, 2048 bit: P = 64, N = 256, L = 8 → 12.80 BF/chu kỳ.

## F. Tile một làn NTT 32 bit (thiết kế v1 từ 31/10/2026)

| Rút gọn (mọi q) | Lượt bộ nhân mỗi phép | Phép nhân modulo mỗi tile mỗi chu kỳ | Cả lõi (16 tile) |
|---|---:|---:|---:|
| Bộ Montgomery riêng (v1) | 4 | 1 | 16 |
| Trên mảng (biến thể 1) | 11 | 0.333 | 5.33 |

- PASS: trên mảng, ba lượt ở độ lệch 0, 5, 10 rơi vào ba pha khác nhau của chu kỳ 3.

