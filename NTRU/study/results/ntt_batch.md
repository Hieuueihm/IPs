# Nhiều đa thức trong một lệnh NTT: làn 32 bit so với hai hệ số mỗi từ (mô hình trước RTL)

Mô hình: [model/ntt_batch.py](../../model/ntt_batch.py). Mỗi tầng gồm butterfly của mọi đa thức; phát theo từng chu kỳ, tile chỉ phát khi bank đọc, bank ghi và bank root của nó còn trống (mô hình bộ phân xử tham lam, chưa phải bảng tĩnh của RTL). Rào chắn mỗi tầng theo lượt ghi. Độ trễ làn: 32 bit 20, 16 bit 16 (ước lượng). Mọi kết quả xuôi khớp định nghĩa (đánh giá đa thức) của từng đa thức.

## Cùng q, nhiều đa thức

| Ứng dụng | q | N | Số đa thức | Một làn: chu kỳ (mỗi đa thức) | Hai hệ số / từ: chu kỳ (mỗi đa thức) | Nhanh hơn | Chu kỳ chờ bank (một làn / hai hệ số) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ML-KEM | 3329 | 256 | 1 | 329 (329) | 168 (168) | 1.96× | 0 / 0 |
| ML-KEM | 3329 | 256 | 2 | 497 (248) | 210 (105) | 2.37× | 0 / 0 |
| ML-KEM | 3329 | 256 | 3 | 665 (222) | 252 (84) | 2.64× | 0 / 0 |
| ML-KEM | 3329 | 256 | 4 | 833 (208) | 294 (74) | 2.83× | 0 / 0 |
| FN-DSA kiểm | 12289 | 512 | 1 | 639 (639) | 282 (282) | 2.27× | 0 / 64 |
| FN-DSA kiểm | 12289 | 512 | 2 | 1071 (536) | 402 (201) | 2.66× | 0 / 128 |
| FN-DSA kiểm | 12289 | 1024 | 1 | 1190 (1190) | 444 (444) | 2.68× | 0 / 128 |
| FN-DSA kiểm | 12289 | 1024 | 2 | 2150 (1075) | 708 (354) | 3.04× | 0 / 256 |

## Nhiều prime 31 bit (NTRUSolve), làn 32 bit: chu kỳ mỗi đa thức theo số đa thức

Dưới N = 64 các đa thức nằm trên các tile khác nhau; từ 64 trở lên mỗi tile phục vụ mọi đa thức nên tối đa 2 prime (2 ô modulus mỗi tile).

| N | Số đa thức | Chu kỳ | Mỗi đa thức | So với một đa thức | Chu kỳ chờ bank |
|---:|---:|---:|---:|---:|---:|
| 8 | 1 | 72 | 72 | 1.00× | 0 |
| 8 | 2 | 76 | 38 | 1.89× | 0 |
| 8 | 8 | 87 | 11 | 6.62× | 0 |
| 16 | 1 | 102 | 102 | 1.00× | 0 |
| 16 | 2 | 104 | 52 | 1.96× | 0 |
| 16 | 4 | 116 | 29 | 3.52× | 0 |
| 32 | 1 | 130 | 130 | 1.00× | 0 |
| 32 | 2 | 145 | 72 | 1.79× | 0 |
| 64 | 1 | 174 | 174 | 1.00× | 0 |
| 64 | 2 | 210 | 105 | 1.66× | 0 |
| 128 | 1 | 245 | 245 | 1.00× | 0 |
| 128 | 2 | 329 | 164 | 1.49× | 0 |
| 256 | 1 | 376 | 376 | 1.00× | 0 |
| 256 | 2 | 568 | 284 | 1.32× | 0 |
| 512 | 1 | 639 | 639 | 1.00× | 0 |
| 512 | 2 | 1071 | 536 | 1.19× | 0 |
