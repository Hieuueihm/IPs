# NTT hai hệ số mỗi từ, bốn làn 16 bit mỗi tile (mô hình trước RTL)

Mô hình: [model/ntt_packed16.py](../../model/ntt_packed16.py). Hệ số c ở ô 16 bit c; từ w (hai hệ số) là phần tử định dạng 4 thứ w, nên mỗi tầng dùng lại bảng tầng định dạng 4 của N/2 phần tử và nguồn mạng hiện có. Mỗi nhịp là một cặp từ = hai butterfly; tile nhận 2 nhịp mỗi 3 chu kỳ (4 làn, Montgomery 16 bit 3 lượt). Rào chắn mỗi tầng; độ trễ làn ước lượng 16.

## Khớp số học và chi phí theo cách lệch pha (ca vàng 1.0)

| Lệch pha | q | N | Chiều | Ca | Khớp | Xung đột đọc / ghi | Chu kỳ thêm do bank root | Chu kỳ |
|---|---:|---:|---|---:|---|---:|---:|---:|
| cùng pha | 12289 | 256 | xuôi | 1 | có | 0 / 0 | 8 | 200 |
| cùng pha | 12289 | 256 | ngược | 1 | có | 0 / 0 | 8 | 200 |
| cùng pha | 12289 | 512 | xuôi | 1 | có | 0 / 0 | 16 | 286 |
| cùng pha | 12289 | 512 | ngược | 1 | có | 0 / 0 | 16 | 286 |
| cùng pha | 12289 | 1024 | xuôi | 1 | có | 0 / 0 | 32 | 452 |
| cùng pha | 12289 | 1024 | ngược | 1 | có | 0 / 0 | 32 | 452 |
| cùng pha | 3329 | 256 | xuôi | 1 | có | 0 / 0 | 0 | 168 |
| cùng pha | 3329 | 256 | ngược | 1 | có | 0 / 0 | 0 | 168 |
| lệch t mod 3 | 12289 | 256 | xuôi | 1 | có | 0 / 0 | 28 | 236 |
| lệch t mod 3 | 12289 | 256 | ngược | 1 | có | 0 / 0 | 28 | 236 |
| lệch t mod 3 | 12289 | 512 | xuôi | 1 | có | 0 / 0 | 60 | 348 |
| lệch t mod 3 | 12289 | 512 | ngược | 1 | có | 0 / 0 | 60 | 348 |
| lệch t mod 3 | 12289 | 1024 | xuôi | 1 | có | 0 / 0 | 126 | 566 |
| lệch t mod 3 | 12289 | 1024 | ngược | 1 | có | 0 / 0 | 126 | 566 |
| lệch t mod 3 | 3329 | 256 | xuôi | 1 | có | 0 / 0 | 18 | 200 |
| lệch t mod 3 | 3329 | 256 | ngược | 1 | có | 0 / 0 | 18 | 200 |
| lệch t / 6 (như lõi một làn) | 12289 | 256 | xuôi | 1 | có | 0 / 0 | 11 | 219 |
| lệch t / 6 (như lõi một làn) | 12289 | 256 | ngược | 1 | có | 0 / 0 | 11 | 219 |
| lệch t / 6 (như lõi một làn) | 12289 | 512 | xuôi | 1 | có | 0 / 0 | 24 | 312 |
| lệch t / 6 (như lõi một làn) | 12289 | 512 | ngược | 1 | có | 0 / 0 | 23 | 311 |
| lệch t / 6 (như lõi một làn) | 12289 | 1024 | xuôi | 1 | có | 0 / 0 | 51 | 491 |
| lệch t / 6 (như lõi một làn) | 12289 | 1024 | ngược | 1 | có | 0 / 0 | 48 | 488 |
| lệch t / 6 (như lõi một làn) | 3329 | 256 | xuôi | 1 | có | 0 / 0 | 5 | 187 |
| lệch t / 6 (như lõi một làn) | 3329 | 256 | ngược | 1 | có | 0 / 0 | 7 | 189 |

## Các modulus nhỏ khác, so với định nghĩa (đánh giá đa thức), N = 2..1024

88 phép biến đổi (5 modulus, mọi N có root, xuôi khớp định nghĩa, ngược trả lại đầu vào), không xung đột bank đọc/ghi.

## So với lõi một làn 32 bit hiện tại (cùng rào chắn mỗi tầng)

| q | N | Chiều | Một làn, rào chắn | Một làn, chồng tầng (RTL) | Hai hệ số / từ, cách lệch tốt nhất | Nhanh hơn (rào chắn) |
|---:|---:|---|---:|---:|---:|---:|
| 3329 | 256 | xuôi | 329 | 231 | 168 (cùng pha) | 1.96× |
| 3329 | 256 | ngược | 329 | 225 | 168 (cùng pha) | 1.96× |
| 12289 | 256 | xuôi | 376 |  | 200 (cùng pha) | 1.88× |
| 12289 | 256 | ngược | 376 |  | 200 (cùng pha) | 1.88× |
| 12289 | 512 | xuôi | 639 |  | 286 (cùng pha) | 2.23× |
| 12289 | 512 | ngược | 639 |  | 286 (cùng pha) | 2.23× |
| 12289 | 1024 | xuôi | 1192 | 984 | 452 (cùng pha) | 2.64× |
| 12289 | 1024 | ngược | 1192 | 985 | 452 (cùng pha) | 2.64× |

## Độ nhạy theo độ trễ làn 16 bit (q 12289, N 1024, xuôi, cùng pha)

| Độ trễ làn | Chu kỳ |
|---:|---:|
| 13 | 422 |
| 16 | 452 |
| 20 | 510 |

## Khi đủ việc: chu kỳ phát mỗi đa thức (nhiều đa thức xen nhau che độ trễ)

Một làn: mỗi tầng N/2 butterfly, mỗi tile một butterfly mỗi 3 chu kỳ. Hai hệ số mỗi từ: mỗi tầng N/4 nhịp, mỗi tile 2 nhịp mỗi 3 chu kỳ. Chưa tính xung đột bank root (khoảng 7% ở N1024 khi cùng pha).

| Ứng dụng | q | N | Tầng | Một làn: chu kỳ phát | Hai hệ số / từ: chu kỳ phát | Tỉ lệ | Phần độ trễ trong một đa thức (hai hệ số, rào chắn) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ML-KEM | 3329 | 256 | 7 | 168 | 42 | 4.0× | 75% |
| FN-DSA kiểm | 12289 | 512 | 9 | 432 | 108 | 4.0× | 62% |
| FN-DSA kiểm | 12289 | 1024 | 10 | 960 | 240 | 4.0× | 47% |

## Ước lượng tài nguyên (chưa đo, ước lượng tay theo RTL tile hiện tại)

| Thêm vào mỗi tile | LUT ước lượng |
|---|---:|
| Toán hạng riêng cho từng lá ở chế độ làn (3 lượt: (y, w), (T thấp, q′), (m, q) mỗi làn 16 bit) | 60–100 |
| Rút gọn mỗi làn: u = T cao + (m q) cao + [T thấp ≠ 0] và trừ q có điều kiện, 4 làn × 17 bit | 130–140 |
| Chẻ bộ cộng/trừ modulo và phép chia đôi thành hai nửa 16 bit | 30–50 |
| Điều khiển nhận 2 nhịp mỗi 3 chu kỳ | khoảng 20 |
| **Cộng** | **khoảng 250–350 mỗi tile, 4–5,6k cho 16 tile (khoảng 8–10% lõi)** |

Ngoài tile: mạng, bộ nhớ và bảng tầng giữ nguyên (bảng định dạng 4 của logn − 1). Lõi cần cờ "hai hệ số mỗi từ" chọn bảng logn − 1, cách lấy cả hai root con cho tầng cuối, và bảng root dạng R = 2¹⁶ (bảng gốc của 1.0 cho 12289 / 3329). Điều kiện số học: q < 2¹⁵ để u < 2q vừa 16 bit (3329, 7681, 10753, 12289, 18433; không gồm 64513).

## Kết luận

- Hai hệ số mỗi từ dùng lại được mạng, bộ nhớ và bảng tầng hiện có: không xung đột đọc/ghi ở mọi N, xung đột bank root nhỏ nhất khi các tile cùng pha (khoảng 7% ở N1024).
- Một đa thức: nhanh hơn 2,0× (N256) đến 2,6× (N1024) với rào chắn mỗi tầng, vì độ trễ mỗi tầng chiếm 47–75% thời gian.
- Khi đủ việc (nhiều đa thức hoặc nhiều prime xen nhau, như ma trận–vectơ của ML-KEM hay NTRUSolve), trần phát là 4×. Vậy làn hẹp chỉ phát huy hết khi đi cùng chạy nhiều đa thức trong một lệnh.
