# Nhu cầu tài nguyên butterfly — phân tích ngày 02/11/2026

Cận giải tích, chưa phải chu kỳ hay PPA của kiến trúc đề xuất.

## Cận theo số tích 32×32 và số từ kết quả

| Mode | Butterfly | Tích phần/BF | Chu kỳ baseline | Ít nhất engine ở tốc độ đó | Cận chu kỳ 8 / 12 / 16 engine | Ít nhất làn xuất 2 word32/ck (trung bình) |
|---|---:|---:|---:|---:|---|---:|
| NTT32_N1024 | 5120 | 3 | 984 | 16 | 1920 / 1280 / 960 | 6 |
| FFT32_N1024 | 2304 | 3 | 644 | 11 | 864 / 576 / 432 | 8 |
| FFT64_N1024 | 2304 | 12 | 2031 | 14 | 3456 / 2304 / 1728 | 5 |
| FFT128_N1024 | 2304 | 45 | 7510 | 14 | 12960 / 8640 / 6480 | 3 |

## Số context sống với lịch core hiện tại

| FFT W | Cách BF (ck) | Lần dùng cuối (ck) | Context sống | Slot làm tròn lũy thừa 2 | Từ 32 bit mỗi mảng operand | Từ mỗi mảng tổng |
|---|---:|---:|---:|---:|---:|---:|
| 32 | 3 | 17 | 6 | 8 | 16 | 8 |
| 64 | 12 | 29 | 3 | 4 | 16 | 8 |
| 128 | 48 | 66 | 2 | 2 | 16 | 8 |

## Giới hạn

- Fixed 32x32 engines accepting one integer product each cycle; FFT 3M and current product truncation.
- NTT uses three Montgomery passes on these engines; bounds do not cover alternative reductions.
- FFT N1024 means 1024 scalar components, 512 complex points, 9 stages, 2304 butterflies.
- Cycle bounds exclude pipeline fill, dependencies, memory conflicts, roots, and stage transitions.
- One output-pair lane serves two 32-bit words/cycle; this does not include all arithmetic work.
- Live-context counts describe current core issue intervals, default LEAF_PD=2 and IN_REG=1.
- Smaller buffers change burst acceptance; no compatibility claim for the old four-context tile contract.
- No LUT saving is inferred from buffer bit count or adder operation count.

Kiểm phép cộng các tích phần theo thứ tự bất kỳ, giữ nguyên wrap/rounding và 3M:

- W=32: 3049 tích vô hướng, 1000 ca 3M PASS.
- W=64: 3049 tích vô hướng, 1000 ca 3M PASS.
- W=128: 3049 tích vô hướng, 1000 ca 3M PASS.

Đổi thứ tự cộng dùng số nguyên đủ rộng trong kiểm này; chưa chứng minh độ rộng accumulator hữu hạn hoặc pipeline mới.

Số đo và hash báo cáo nguồn: [JSON](butterfly_resource_demand.json).
