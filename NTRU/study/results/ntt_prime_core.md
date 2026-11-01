# NTT modulo prime nạp được (profile 3) trên lõi tối thiểu (mô hình trước RTL)

Mô hình: [model/ntt_prime_core.py](../../model/ntt_prime_core.py). Lịch NTT của lõi (chồng tầng) chạy với q, q′ và bảng root của một khe; bảng theo quy ước `mp_mkgmigm` của NTRUGen, ngược chia đôi mỗi tầng.

- 323 prime của NTRUGen, logn 1..10, hai chiều: 6460 NTT khớp `mp_NTT` / `mp_iNTT` theo lịch rào chắn; 140 khớp theo lịch chồng tầng (lịch RTL chạy) trên 7 prime trải đều.

| N | Chu kỳ xuôi / ngược (chồng tầng) |
|---:|---:|
| 2 | 24 / 24 |
| 4 | 48 / 48 |
| 8 | 72 / 72 |
| 16 | 100 / 100 |
| 32 | 127 / 127 |
| 64 | 157 / 157 |
| 128 | 196 / 195 |
| 256 | 255 / 249 |
| 512 | 464 / 458 |
| 1024 | 984 / 985 |

## Modulus của khảo sát, so với định nghĩa (đánh giá đa thức), và chiều ngược trả lại đầu vào

| Ứng dụng | q | N | Tầng bỏ | Xuôi khớp | Ngược trả lại | Chu kỳ xuôi / ngược |
|---|---:|---:|---:|---|---|---:|
| ML-KEM | 3329 | 256 | 1 | có | có | 231 / 225 |
| ML-DSA | 8380417 | 256 | 0 | có | có | 255 / 249 |
| FN-DSA | 12289 | 512 | 0 | có | có | 464 / 458 |
| FN-DSA | 12289 | 1024 | 0 | có | có | 984 / 985 |
| HAWK ký | 18433 | 512 | 0 | có | có | 464 / 458 |
| HAWK ký | 18433 | 1024 | 0 | có | có | 984 / 985 |
| HAETAE | 64513 | 256 | 0 | có | có | 255 / 249 |
| Kyber vòng 1 | 7681 | 256 | 0 | có | có | 255 / 249 |
| Saber RNS | 10753 | 256 | 0 | có | có | 255 / 249 |
| Saber qua NTT | 25166081 | 256 | 1 | có | có | 231 / 225 |
| LightSaber qua NTT | 20972417 | 256 | 2 | có | có | 206 / 198 |

Kế hoạch chồng tầng cho mọi (logn, số tầng bỏ, chiều) của profile 3: 54 ([study/results/ntt_prime_overlap.json](ntt_prime_overlap.json)).
