# 3.0 — phạm vi được nhận

Nguồn: `experiments/a_cg_z020_system160/rtl/`, schema và register map ở [02](02_giao_dien.md).

| Mode | Contract |
|---|---|
| FFT/IFFT thường | Fixed-point 32/64/128 bit mỗi thành phần, `cfg_fmt=0/1/2` |
| Native FFT/IFFT NTRUGen64 | `cfg_fft=1`, `cfg_ntrugen=1`, `cfg_fmt=1`; contract C riêng |
| NTT/INTT thường | R=2³², q lẻ, 3 ≤ q < 2³¹; CT/GS theo chiều |
| Packed16 NTT/INTT | q < 2¹⁵, hai hệ số 16 bit/từ 32 bit, R=2¹⁶ mỗi lane |
| Batch | `jobs=2^jobs_log`, đồng nhất mode/precision/modulus/chiều/kích thước |

Giới hạn do RTL kiểm: `logn≤10`, `fmt≠3`, `jobs_log≤4`; NTT còn `0≤hmin≤2`, `hmin<logn`; native chỉ ở FFT64, packed không dùng trong FFT. Cấu hình còn phải thỏa số plane ≤8 và row exponent ≤7 theo [planner baseline](../../../experiments/a_cg_z020_system160/planner.py). Không hứa mọi tổ hợp đều hỗ trợ 16 job.

`N=2^logn` trong giao diện là số hệ số theo biểu diễn phần mềm. FFT dùng N/2 điểm phức khi logn>0; N1024 của bảng FFT tương ứng 512 điểm phức. Các trường hợp nhỏ/identity tuân theo vector và planner, không đổi cách hiểu N để so cycle với paper khác.

q lẻ là điều kiện engine Montgomery; một NTT có ý nghĩa còn cần root và quy ước transform tương thích q/N/hmin. Host chọn modulus, tính qinv, nạp root và descriptor đúng chiều từ nguồn đã kiểm; RTL không tự chứng minh primality/cấp root hoặc tự sinh mọi bảng.

Một context hoạt động trong core, một cấu hình chung cho cả batch. Hai slot modulus ở tile độc lập không có nghĩa core có 16 prime slot hoặc trộn nhiều modulus cùng lúc; core hiện dùng slot 0.

Ngoài mốc được nhận: kernel riêng CMUL/SPLIT/MERGE/BASEMUL/RECIP; full CRT/keygen/sampler/signer RTL; DMA/DDR/ngoại vi; pause/flush đầy đủ của spec cũ; địa chỉ đầu A/B/C tự do; ghép PE liên tile; nhiều mode đồng thời; prime >31 bit; IEEE floating point; chứng nhận side-channel. Cấu hình/inverse reset không thay thế API pause/flush chưa có. Host/C vẫn làm phần ứng dụng ngoài transform.
