# Modulus của các bài toán PQC hiện nay (khảo sát 01/11/2026)

Mục đích: xác định NTT nhiều modulus của lõi cần phủ những q nào. Người dùng duyệt phạm vi ngày 01/11/2026: **mọi q lẻ
< 2³¹, N = 2..1024 lũy thừa 2, có thể thiếu tầng, bảng root nạp vào RAM** (thay đổi 8, 9 và giả thuyết 10 của kiến trúc),
giữ 3 profile ROM cho các chuẩn đã ban hành.

| Ứng dụng | q | Bit | N | NTT trên X^N + 1 | Ghi chú |
|---|---:|---:|---:|---|---|
| ML-KEM (FIPS 203) | 3 329 | 12 | 256 | thiếu 1 tầng (7 tầng) | v₂(q − 1) = 8 |
| ML-DSA (FIPS 204) | 8 380 417 | 23 | 256 | đủ | |
| FN-DSA / Falcon (FIPS 206, chưa ban hành chính thức) | 12 289 | 14 | 512, 1024 | đủ | |
| FN-DSA sinh khóa (NTRUGen, RNS) | 323 prime 2 140 348 417 … 2 147 473 409 | 31 | 2 … 1024 | đủ | 2048 \| p − 1 với mọi prime (đọc từ dump C) |
| HAWK kiểm chữ ký và sinh khóa (vòng 3 chữ ký bổ sung, NIST IR 8610) | 2 147 473 409; 2 147 389 441 | 31 | 512, 1024 | đủ | chính là 2 prime đầu của bảng NTRUGen |
| HAWK ký (bản tham chiếu) | 18 433 (hoặc 12 289) | 15 | 512, 1024 | đủ | spec HAWK mục 4.1.3 |
| HAETAE (KpqC) | 64 513 | 16 | 256 | đủ | chưa xác minh từ nguồn |
| Saber chạy bằng NTT (Chung et al. 2021) | 25 166 081 / 20 972 417 | 25 | 256 | thiếu 1 / 2 tầng | prime phụ, đủ lớn cho tích hệ số |
| Saber RNS (AVX2), Kyber vòng 1 | 7 681, 10 753 | 13–14 | 256 | đủ | |
| NTRU, NTRU Prime, NTRU+, NTTRU | 2048–8192 (lũy thừa 2), 4 591, 3 457, 7 681 | | 509 … 1152 | N không phải lũy thừa 2 | cần tầng cơ số 3 hoặc NTT vòng: ngoài phạm vi |
| NTRU qua NTT (Fritzmann) | 549 755 809 793 | 39 | 2048 | | quá 31 bit: ngoài phạm vi |
| HQC, Classic McEliece | GF(2) | | | không dùng NTT mod q | |

Tính toán (khi khảo sát):
- Tile: Montgomery R = 2³² cho mọi q lẻ < 2³¹ (u < 2q < 2³², thanh ghi 32 bit đủ).
- Số tầng NTT = min(logn, v₂(q − 1) − 1); 3329 và 25 166 081 ở N = 256: 7 tầng, 20 972 417: 6 tầng.
- Bảng root mỗi prime ở N = 1024: gm + igm = 2 048 word (8 KiB); bảng N = 1024 là tiền tố cho mọi N nhỏ hơn. Không thể
  lưu sẵn 323 prime (khoảng 2,6 MB), nên nạp lúc chạy: host nạp khoảng 512 chu kỳ (4 word mỗi dòng 128 bit), tự sinh
  trên tile khoảng 570 chu kỳ (10 mức nhân đôi), nên chọn host nạp.

Kiểm trên mô hình lõi: [study/results/ntt_prime_core.md](ntt_prime_core.md).

Nguồn:
- [NIST IR 8610](https://csrc.nist.gov/pubs/ir/8610/final) (ứng viên vòng 3 chữ ký bổ sung)
- [Spec HAWK](https://www.hawk-sign.info/hawk-spec.pdf) (mục 3.4, 4.1)
- [Khảo sát NTT cho mật mã lưới, arXiv 2211.13546](https://arxiv.org/pdf/2211.13546) (bảng 3, mục 8.4–8.6)
- [Chung et al., NTT Multiplication for NTT-unfriendly Rings](https://eprint.iacr.org/2020/1397)
- [NTTRU, TCHES 2019](https://tches.iacr.org/index.php/TCHES/article/download/8293/7643); [NTRU+ IETF draft](https://datatracker.ietf.org/doc/draft-jhpark-cfrg-ntruplus-security-considerations/)
- [libntruprime](https://libntruprime.cr.yp.to/libntruprime-20260717/doc/internals.md)
- [KpqC](https://pub.dev/documentation/kpqc/0.1.1/); [HQC](https://arxiv.org/pdf/2601.07634)
