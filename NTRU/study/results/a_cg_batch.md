# Packed16 NTT và batch transform: số đo RTL

Bản riêng: **36,231 LUT, 25,331 FF, 64 DSP, 48 RAMB18**; chênh ngân sách 35k: -1,231 LUT.
Toàn core gồm host, root, descriptor, bộ nhớ và 16 engine. Không thay production, PLAN, spec hay các bản thử trước. Chưa commit.

## Hiệu năng

Chu kỳ đo từ start đến done. Tỷ lệ throughput so với chạy tuần tự cùng số job bằng scalar NTT hoặc FFT một job, cùng clock; không phải tăng tốc toàn ứng dụng.

| Cấu hình | Job/lệnh | Baseline/job | Chu kỳ cả lô | Chu kỳ/job | Throughput | Cold cả lô |
|---|---:|---:|---:|---:|---:|---:|
| NTT_p0_N1024_5 | 1 | 985 | 505 | 505.00 | 1.95× | 1544 |
| NTT_p1_N256_5 | 1 | 265 | 217 | 217.00 | 1.22× | 421 |
| new_NTT_q12289_N8_h0_p0_J16_f | 16 | 76 | 85 | 5.31 | 14.31× | 165 |
| new_NTT_q12289_N8_h0_p1_J16_f | 16 | 76 | 79 | 4.94 | 15.39× | 125 |
| new_NTT_q12289_N1024_h0_p1_J2_f | 2 | 985 | 985 | 492.50 | 2.00× | 2280 |
| new_NTT_q8380417_N256_h0_p0_J2_f | 2 | 301 | 409 | 204.50 | 1.47× | 934 |
| new_FFT128_n3_r0_J8_0 | 8 | 143 | 143 | 17.88 | 8.00× | 685 |
| FFT128_N1024_0 | 1 | 6508 | 6508 | 6508.00 | 1.00× | 16967 |

Cold bao gồm cấu hình, root/descriptor, nạp dữ liệu và đọc kết quả theo driver hiện tại. Batch N=8 là trường hợp nhỏ minh họa mức lấp đầy; không suy ra throughput tương tự cho N lớn.

## Tính đúng

- 1026 ca Verilator: khớp model chu kỳ và mọi word kết quả; 454 ca cũ giữ nguyên input/root/expected.
- 38 ca Icarus bốn trạng thái, gồm packed tầng thường/tầng trong word, bank jobs và row jobs.
- NTT mới dùng oracle đánh giá đa thức Horner độc lập. FFT giữ nguyên contract 32/64/128 và native NTRUGen64.
- 74 lần gọi transform trong C thực tế, dùng packed cho NTT/INTT, FFT128 như trước; 4 chữ ký verify và 14 artifact khớp từng byte. Đầu vào bị sửa bị từ chối.
- Không phải chứng minh hình thức mọi đầu vào hay chứng nhận an toàn toàn bộ ứng dụng PQC.

## Diện tích và giới hạn

Baseline 33,669 LUT; bản này tăng 2,562 LUT. DSP và BRAM không tăng.
WNS sau synth ở clock 5 ns: +0.705 ns. Clock đặt sau synth như baseline; chưa place/route.
- Kernel cycles exclude host/root loading; cold transaction cycles are also reported.
- Batch jobs share N, q, direction, precision, tables and arithmetic contract; no mixed-context execution.
- Packed16 requires canonical inputs and odd q < 32768, with roots in Montgomery R16 domain.
- No additional DSP/BRAM; combined packed and batch increase LUT versus the 33,669-LUT baseline.
- Application replay substitutes only FFT/IFFT/NTT/INTT; other PQC kernels remain C.
- Application replay uses single jobs; batch correctness uses independent transform vectors.
- Synth-only timing is not measured post-route Fmax; no full-algorithm speedup claim.

Chi tiết cơ chế, cấu hình và lệnh tái lập: `experiments/a_cg_batch/README.md`. JSON kèm hash nguồn, báo cáo và từng ca đo.

## Đo tách chức năng packed

Bản compile-time tắt packed, giữ batch và FFT32/64/128: **33,802 LUT, 24,971 FF, 64 DSP, 48 RAMB18**.
Chênh ngân sách 35k: +1,198 LUT. Chênh so với baseline 33.669 LUT: +133 LUT.
Đây là cấu hình chuyên biệt tĩnh của cùng source, với packed=0; **774 ca mô phỏng riêng đều qua**, chu kỳ kernel và cold trùng core đầy đủ ở cùng chế độ. Chưa mô phỏng netlist sau synth.
Không được gán số chu kỳ packed16 cho bản này. Tính năng batch không tự tạo ra các job độc lập trong ứng dụng.
Thử đưa phép nhân bản q vào engine thay vì cổng cấu hình làm tăng từ 36.231 lên 36.499 LUT, nên đã bỏ. Báo cáo lần thử được giữ trong attempt2.
