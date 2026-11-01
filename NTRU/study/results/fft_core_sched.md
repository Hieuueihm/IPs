# Lịch chu kỳ FFT 32 bit trong lõi (cách A)

Mô hình: [model/fft_core_sched.py](../../model/fft_core_sched.py). Rào chắn mỗi tầng. Chu kỳ = từ lần đọc đầu tới lần ghi cuối, cộng 1.

| N | Chiều | Khớp ca vàng | Chu kỳ | Chu kỳ xung đột đọc / ghi | Chu kỳ thêm do bank root |
|---:|---|---|---:|---:|---:|
| 1 | xuôi | có | 0 | 0 / 0 | 0 |
| 2 | xuôi | có | 0 | 0 / 0 | 0 |
| 4 | xuôi | có | 14 | 0 / 0 | 0 |
| 8 | xuôi | có | 29 | 0 / 0 | 0 |
| 16 | xuôi | có | 44 | 0 / 0 | 0 |
| 32 | xuôi | có | 59 | 0 / 0 | 0 |
| 64 | xuôi | có | 74 | 0 / 0 | 0 |
| 128 | xuôi | có | 107 | 0 / 0 | 0 |
| 256 | xuôi | có | 167 | 0 / 0 | 0 |
| 512 | xuôi | có | 287 | 0 / 0 | 0 |
| 1024 | xuôi | có | 539 | 0 / 0 | 0 |
| 1 | ngược | có | 0 | 0 / 0 | 0 |
| 2 | ngược | có | 0 | 0 / 0 | 0 |
| 4 | ngược | có | 14 | 0 / 0 | 0 |
| 8 | ngược | có | 29 | 0 / 0 | 0 |
| 16 | ngược | có | 44 | 0 / 0 | 0 |
| 32 | ngược | có | 59 | 0 / 0 | 0 |
| 64 | ngược | có | 74 | 0 / 0 | 0 |
| 128 | ngược | có | 107 | 0 / 0 | 0 |
| 256 | ngược | có | 167 | 0 / 0 | 0 |
| 512 | ngược | có | 287 | 0 / 0 | 0 |
| 1024 | ngược | có | 539 | 0 / 0 | 0 |
