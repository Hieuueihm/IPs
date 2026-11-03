# FN-DSA trên FlexTransform: NTT chiếm bao nhiêu, rút gọn trên mảng tốn bao nhiêu

Bản chuẩn R8 + NTRUGen đi kèm, build WSL gcc LP64, `FALCON_FPR_MODE=2`, AVX2 tắt. 4 khóa × 8 chữ ký mỗi N. Mọi lời gọi kernel được đếm và đo thời gian phần mềm (`sim/ref/workload_profile.c`). Chu kỳ phần cứng = số lời gọi × dự báo của kiến trúc v1 mục 4 (độ trễ bộ nhân 4), cộng 16 chu kỳ mỗi lệnh. Số liệu tính cho **một** lần sinh khóa / mở rộng khóa / ký / kiểm.

**Tile một làn** (spec 2.0, 10 từ 31/10/2026): butterfly/chu kỳ của lõi 16 bit 16; 32 bit trên mảng 5.33, riêng (thiết kế v1) 16. Độ trễ mỗi lượt (gồm đọc/ghi RAM): 16 bit 15, 32 bit 21 / 17. Thời gian NTT lấy từ model/single_lane_feed.py (xung đột bank và gói root). Số lời gọi lấy lại từ fn_dsa_workload_lai.json; cột "riêng" là thiết kế v1.

## N = 512

### Số lời gọi và thời gian phần mềm (mỗi thao tác)

| Pha | Thời gian phần mềm (ms) | Lời gọi FFT | Lời gọi NTT | Lời gọi tạo bảng root | Phần mềm trong FFT | trong NTT | trong tạo bảng |
|---|---:|---:|---:|---:|---:|---:|---:|
| keygen | 13.211 | 866 | 3038 | 1380 | 12.0% | 47.3% | 2.6% |
| expand | 2.688 | 515 | 6 | 0 | 83.4% | 2.3% | 0.0% |
| sign | 4.134 | 648 | 0 | 0 | 89.1% | 0.0% | 0.0% |
| verify | 0.094 | 0 | 5 | 0 | 0.0% | 62.2% | 0.0% |

### Chu kỳ phần cứng dự báo (mỗi thao tác)

| Pha | FFT | NTT trên mảng | NTT riêng | Nạp root (lõi) | Host ghi vùng C (dòng) | Tổng trên mảng | Tổng riêng | Tăng | NTT/tổng (trên mảng) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| keygen | 59546 | 336295 | 256501 | 31052 | 18442 | 426893 | 347099 | +23.0% | 78.8% |
| expand | 28968 | 1353 | 1353 | 0 | 0 | 30321 | 30321 | +0.0% | 4.5% |
| sign | 59368 | 0 | 0 | 0 | 0 | 59368 | 59368 | +0.0% | 0.0% |
| verify | 0 | 1058 | 1058 | 0 | 0 | 1058 | 1058 | +0.0% | 100.0% |

Không tính chi phí cố định mỗi lệnh: tăng keygen +30.4%, expand +0.0%, sign +0.0%, verify +0.0%.

## N = 1024

### Số lời gọi và thời gian phần mềm (mỗi thao tác)

| Pha | Thời gian phần mềm (ms) | Lời gọi FFT | Lời gọi NTT | Lời gọi tạo bảng root | Phần mềm trong FFT | trong NTT | trong tạo bảng |
|---|---:|---:|---:|---:|---:|---:|---:|
| keygen | 58.859 | 2186 | 9588 | 4402 | 13.9% | 36.5% | 1.8% |
| expand | 6.923 | 1027 | 6 | 0 | 84.7% | 2.3% | 0.0% |
| sign | 9.014 | 1288 | 0 | 0 | 90.3% | 0.0% | 0.0% |
| verify | 0.173 | 0 | 5 | 0 | 0.0% | 63.7% | 0.0% |

### Chu kỳ phần cứng dự báo (mỗi thao tác)

| Pha | FFT | NTT trên mảng | NTT riêng | Nạp root (lõi) | Host ghi vùng C (dòng) | Tổng trên mảng | Tổng riêng | Tăng | NTT/tổng (trên mảng) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| keygen | 371203 | 1028979 | 783209 | 99051 | 58582 | 1499233 | 1253463 | +19.6% | 68.6% |
| expand | 62536 | 2213 | 2213 | 0 | 0 | 64749 | 64749 | +0.0% | 3.4% |
| sign | 129952 | 0 | 0 | 0 | 0 | 129952 | 129952 | +0.0% | 0.0% |
| verify | 0 | 1727 | 1727 | 0 | 0 | 1727 | 1727 | +0.0% | 100.0% |

Không tính chi phí cố định mỗi lệnh: tăng keygen +24.7%, expand +0.0%, sign +0.0%, verify +0.0%.

## NTT của sinh khóa theo kích thước (lời gọi mỗi lần sinh khóa, N = 1024)

| logn | NTT prime 31 bit | NTT ngược | Tạo bảng (gm, igm, cả hai) | Chu kỳ một NTT, trên mảng / riêng |
|---:|---:|---:|---:|---:|
| 0 | 539 | 0 | 0 / 0 / 0 | đồng nhất, host bỏ qua |
| 1 | 989 | 1267 | 180 / 182 / 539 | 22 / 18 |
| 2 | 454 | 642 | 89 / 93 / 271 | 44 / 36 |
| 3 | 195 | 260 | 46 / 47 / 98 | 66 / 54 |
| 4 | 1818 | 1827 | 38 / 24 / 1750 | 92 / 72 |
| 5 | 621 | 632 | 20 / 14 / 588 | 120 / 90 |
| 6 | 212 | 213 | 12 / 7 / 191 | 162 / 114 |
| 7 | 98 | 106 | 6 / 5 / 90 | 231 / 147 |
| 8 | 50 | 57 | 6 / 6 / 42 | 360 / 200 |
| 9 | 78 | 36 | 21 / 21 / 2 | 621 / 297 |
| 10 | 16 | 14 | 9 / 7 / 0 | 1170 / 491 |

## Ghép nhiều đa thức cùng prime vào một lệnh (sinh khóa)

Một lời gọi NTT prime 31 bit được ghép vào lô đang mở khi: ngay sau lời gọi cuối của lô (không có kernel nào khác xen giữa), cùng chiều, cùng logn, cùng prime, cùng bảng root, mảng không chồng lên nhau, và lô chưa vượt giới hạn của spec 2.0 (N < 64: jobs · N ≤ 32, tối đa 8; N ≥ 64: tối đa 2). Chỗ gọi của các lời gọi được ghép liệt kê ở cuối để kiểm tính độc lập trong mã nguồn.

| N | Chu kỳ sinh khóa, một đa thức mỗi lệnh: trên mảng / riêng | Tăng | Có ghép: trên mảng / riêng | Tăng | Có ghép, trên mảng so với không ghép, riêng |
|---:|---:|---:|---:|---:|---:|
| 512 | 426893 / 347099 | +23.0% | 395673 / 324149 | +22.1% | +14.0% |
| 1024 | 1499233 / 1253463 | +19.6% | 1432926 / 1198829 | +19.5% | +14.3% |

### Cận trên khi ghép **khác prime** (mỗi tile một modulus)

Trong một đoạn chỉ có công việc NTT prime 31 bit (không có kernel loại khác xen giữa), các lời gọi cùng chiều và cùng logn với N < 64 được gom thành lệnh tới min(8, 64/N) đa thức, dù khác prime (mỗi đa thức nằm trên các tile riêng, mỗi tile một modulus). N ≥ 64 giữ một prime mỗi lệnh. Giả định vòng lặp theo prime tách được (các làn RNS độc lập); đây là cận trên. Nạp bảng root giữ nguyên số lần.

| N | Ghép khác prime: trên mảng / riêng | Tăng | Trên mảng so với không ghép, riêng | NTT sinh khóa, trên mảng: không ghép → ghép khác prime |
|---:|---:|---:|---:|---:|
| 512 | 280727 / 222890 | +25.9% | -19.1% | 335363 → 189197 |
| 1024 | 993878 / 824656 | +20.5% | -20.7% | 1027442 → 522088 |

## Chép dữ liệu giữa host và lõi

Dòng 128 bit host phải ghi vào / đọc ra lõi cho dữ liệu của kernel (`sim/ref/workload_profile.c`), chưa gồm bảng root (cột riêng). Ba cách tính:
- **không giữ lại**: mọi đầu vào ghi vào, mọi đầu ra đọc ra;
- **giữ đầu vào**: không ghi lại đầu vào nếu lõi còn giữ đúng nội dung đó từ kernel trước (tới 48 KiB, bỏ bộ đệm dùng lâu nhất); đầu ra vẫn đọc ra hết;
- **giữ cả hai** (cận dưới): đầu ra chỉ đọc khi host sửa bộ đệm đó, khi bị đẩy ra, hoặc cuối pha. Không thấy được lúc host chỉ đọc mà không sửa.

Hai cách giữ lại cần lệnh chỉ ra được địa chỉ bộ đệm trong vùng nhớ; lệnh của 1.0 luôn dùng địa chỉ 0.

### N = 512 (mỗi thao tác)

| Pha | Chu kỳ tính | Dòng: không giữ | giữ đầu vào | giữ cả hai | Dòng bảng root | Tổng, Giao diện 1.0: một giao dịch, không burst, không giữ | Tổng, Burst / pipeline 128 bit, không giữ | Tổng, Burst / pipeline 256 bit, không giữ | Tổng, burst 128, giữ cả hai |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| keygen | 280727 | 74140 | 68682 | 55246 | 18442 | 465891 (40% chép) | 373309 (25% chép) | 327018 (14% chép) | 354415 (21% chép) |
| expand | 30321 | 14144 | 12160 | 8448 | 0 | 58609 (48% chép) | 44465 (32% chép) | 37393 (19% chép) | 38769 (22% chép) |
| sign | 59368 | 55808 | 44192 | 30864 | 0 | 170984 (65% chép) | 115176 (48% chép) | 87272 (32% chép) | 90232 (34% chép) |
| verify | 1058 | 704 | 448 | 256 | 0 | 2466 (57% chép) | 1762 (40% chép) | 1410 (25% chép) | 1314 (19% chép) |

### N = 1024 (mỗi thao tác)

| Pha | Chu kỳ tính | Dòng: không giữ | giữ đầu vào | giữ cả hai | Dòng bảng root | Tổng, Giao diện 1.0: một giao dịch, không burst, không giữ | Tổng, Burst / pipeline 128 bit, không giữ | Tổng, Burst / pipeline 256 bit, không giữ | Tổng, burst 128, giữ cả hai |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| keygen | 993878 | 329251 | 315090 | 279300 | 58582 | 1769544 (44% chép) | 1381711 (28% chép) | 1187795 (16% chép) | 1331760 (25% chép) |
| expand | 64749 | 30336 | 25856 | 17408 | 0 | 125421 (48% chép) | 95085 (32% chép) | 79917 (19% chép) | 82157 (21% chép) |
| sign | 129952 | 122880 | 100352 | 73696 | 0 | 375712 (65% chép) | 252832 (49% chép) | 191392 (32% chép) | 203648 (36% chép) |
| verify | 1727 | 1408 | 896 | 512 | 0 | 4543 (62% chép) | 3135 (45% chép) | 2431 (29% chép) | 2239 (23% chép) |

Chu kỳ tính của sinh khóa đã gồm ghép khác prime (thay đổi 9). Chép và tính được cộng nối tiếp (chưa chồng nhau), đúng với giao diện 1.0 vì host không được truy cập bộ nhớ khi lõi đang chạy.


Phân bố lô cùng prime (sinh khóa N = 1024, mỗi lần sinh khóa):

| Chiều | logn | Số đa thức mỗi lô | Số lô |
|---|---:|---:|---:|
| xuôi | 1 | 1 | 988.8 |
| xuôi | 2 | 1 | 454.5 |
| xuôi | 3 | 1 | 194.8 |
| xuôi | 4 | 1 | 1817.5 |
| xuôi | 5 | 1 | 621.0 |
| xuôi | 6 | 1 | 212.0 |
| xuôi | 7 | 1 | 97.5 |
| xuôi | 8 | 1 | 50.5 |
| xuôi | 9 | 1 | 9.5 |
| xuôi | 9 | 2 | 34.0 |
| xuôi | 10 | 1 | 3.0 |
| xuôi | 10 | 2 | 6.8 |
| ngược | 1 | 1 | 539.0 |
| ngược | 1 | 2 | 364.0 |
| ngược | 2 | 1 | 271.2 |
| ngược | 2 | 2 | 185.5 |
| ngược | 3 | 1 | 97.5 |
| ngược | 3 | 2 | 81.0 |
| ngược | 4 | 1 | 1750.0 |
| ngược | 4 | 2 | 38.5 |
| ngược | 5 | 1 | 632.0 |
| ngược | 6 | 1 | 191.0 |
| ngược | 6 | 2 | 11.0 |
| ngược | 7 | 1 | 90.0 |
| ngược | 7 | 2 | 8.2 |
| ngược | 8 | 1 | 42.0 |
| ngược | 8 | 2 | 7.5 |
| ngược | 9 | 1 | 11.0 |
| ngược | 9 | 2 | 12.8 |
| ngược | 10 | 2 | 6.8 |

Các cặp chỗ gọi được ghép (lời gọi đầu lô → lời gọi được ghép), N = 1024:

| Lời gọi đầu lô | Lời gọi được ghép | Số lần |
|---|---|---:|
| ng_ntru.c:85 | ng_ntru.c:86 | 1491 |
| ng_ntru.c:495 | ng_ntru.c:496 | 1330 |
| ng_poly.c:903 | ng_poly.c:909 | 68 |
| ng_poly.c:927 | ng_poly.c:928 | 68 |
| ng_poly.c:959 | ng_poly.c:967 | 32 |
| ng_ntru.c:23 | ng_ntru.c:194 | 12 |
| ng_ntru.c:23 | ng_ntru.c:215 | 7 |
| ng_ntru.c:868 | ng_ntru.c:924 | 4 |
| ng_ntru.c:1101 | ng_ntru.c:1102 | 4 |
| ng_ntru.c:1189 | ng_ntru.c:1190 | 4 |
| ng_ntru.c:1269 | ng_ntru.c:1270 | 4 |

