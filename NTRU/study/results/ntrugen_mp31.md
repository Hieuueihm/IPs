# NTT modulo các prime 31 bit của NTRUGen trên đường dữ liệu FlexTransform

Bản chuẩn: `ng_mp31.c` của NTRUGen đi kèm bản FN-DSA đã ghim, build `NTRUGEN_AVX2=0` (`model/ntrugen_mp31_harness.c`). Cả 323 prime của bảng `PRIMES`, logn = 1..10.

| Kiểm | Số trường hợp | Kết quả |
|---|---:|---|
| Montgomery dựng từ tích 16×16 + bộ cộng chung = `mp_montymul` (gồm 0, 1, p − 1) | 21641 | khớp |
| Bảng root tính theo công thức = `mp_mkgmigm` | 3230 | khớp |
| NTT xuôi bằng nhịp hai tầng (+ một tầng cuối khi logn lẻ) = `mp_NTT` | 3230 | khớp |
| NTT ngược GS, chia đôi mỗi tầng, nhịp hai tầng = `mp_iNTT` | 3230 | khớp |
| NTT xuôi, mỗi tầng một lượt, mỗi butterfly một request tile, thứ tự phát ngẫu nhiên = `mp_NTT` | 3230 | khớp |
| NTT ngược GS chia đôi, mỗi tầng một lượt, thứ tự phát ngẫu nhiên = `mp_iNTT` | 3230 | khớp |

Prime lớn nhất 2147473409 < 2^31, nên u < 2p < 2^32: thanh ghi 32 bit đủ.
