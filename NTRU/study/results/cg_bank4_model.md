# CG: ứng viên mạng tối đa bốn nguồn mỗi cổng

Model chu kỳ RAM vật lý; chưa phải RTL, chưa có số LUT/BRAM/timing.

Tối đa nguồn đọc: **4**; nguồn ghi: **4**.
154 cấu hình cổng/phụ thuộc; kiểm số học: {'NTT_golden': 48, 'NTT_survey_configs': 11, 'FFT32_identity_N1': 2, 'FFT32_golden': 20, 'FFT64_identity_N1': 2, 'FFT64_golden': 20, 'FFT64_golden_interleaved': 20, 'FFT128_identity_N1': 2, 'FFT128_golden': 20, 'FFT128_golden_interleaved': 20, 'mutation_missing_bank_xor_detected': 1}.

## Chu kỳ tiêu biểu

| Mode | N | hmin | Chiều | Input xen kẽ | Kernel cycle | Hàng/buffer | Nạp/đọc: tối đa nhịp con mỗi line 128 bit |
|---|---:|---:|---|---|---:|---:|---|
| NTT | 256 | 0 | xuôi | không | 309 | 8 | 1 / 1 |
| NTT | 256 | 0 | ngược | không | 309 | 8 | 1 / 1 |
| NTT | 256 | 1 | xuôi | không | 272 | 8 | 2 / 2 |
| NTT | 256 | 1 | ngược | không | 272 | 8 | 2 / 2 |
| NTT | 256 | 2 | xuôi | không | 234 | 8 | 4 / 4 |
| NTT | 256 | 2 | ngược | không | 234 | 8 | 4 / 4 |
| NTT | 512 | 0 | xuôi | không | 467 | 16 | 1 / 1 |
| NTT | 512 | 0 | ngược | không | 467 | 16 | 1 / 1 |
| NTT | 512 | 1 | xuôi | không | 417 | 16 | 2 / 2 |
| NTT | 512 | 1 | ngược | không | 417 | 16 | 2 / 2 |
| NTT | 512 | 2 | xuôi | không | 368 | 16 | 4 / 4 |
| NTT | 512 | 2 | ngược | không | 368 | 16 | 4 / 4 |
| NTT | 1024 | 0 | xuôi | không | 983 | 32 | 1 / 1 |
| NTT | 1024 | 0 | ngược | không | 983 | 32 | 1 / 1 |
| NTT | 1024 | 1 | xuôi | không | 887 | 32 | 2 / 2 |
| NTT | 1024 | 1 | ngược | không | 887 | 32 | 2 / 2 |
| NTT | 1024 | 2 | xuôi | không | 791 | 32 | 4 / 4 |
| NTT | 1024 | 2 | ngược | không | 791 | 32 | 4 / 4 |
| FFT32 | 1024 | 0 | xuôi | không | 451 | 32 | 1 / 1 |
| FFT32 | 1024 | 0 | ngược | không | 451 | 32 | 1 / 1 |
| FFT64 | 1024 | 0 | xuôi | không | 1750 | 64 | 2 / 2 |
| FFT64 | 1024 | 0 | xuôi | có | 1750 | 64 | 2 / 2 |
| FFT64 | 1024 | 0 | ngược | không | 1750 | 64 | 2 / 2 |
| FFT64 | 1024 | 0 | ngược | có | 1750 | 64 | 2 / 2 |
| FFT128 | 1024 | 0 | xuôi | không | 6935 | 128 | 4 / 4 |
| FFT128 | 1024 | 0 | xuôi | có | 6935 | 128 | 4 / 4 |
| FFT128 | 1024 | 0 | ngược | không | 6935 | 128 | 4 / 4 |
| FFT128 | 1024 | 0 | ngược | có | 6935 | 128 | 4 / 4 |

## Giới hạn

- Assumes current tile scalar-NTT/FFT issue periods and output latencies. Interleaved inputs use the memory-retiming hypothesis; no new RTL or packed16.
- Root values correct in replay; root ROM port implementation and BRAM cost are not modeled.
- Host layout changes; line serialization counted, adapter RTL and buffering not designed.
- Kernel cycles exclude load/readback/configuration/root loading.
- No area/Fmax claim. Four is a found fan-in bound, not a proof of global optimality.

Nguồn: [model](../../model/cg_bank4_model.py), [JSON, topology đầy đủ và hash](cg_bank4_model.json).
