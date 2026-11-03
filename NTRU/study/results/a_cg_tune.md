# Tuning sau bản 34.062 LUT

**Đo mới: 33,669 LUT, giảm 393 LUT, còn 1,331 LUT dưới ngân sách 35k.**
Ngày 02/11/2026. Chỉ thêm bản riêng `experiments/a_cg_tune`; không thay production, spec, PLAN hoặc bản 34.062 LUT.

## Hai thay đổi

1. FFT128 cấp BF mỗi 45 thay vì 48 chu kỳ. Ba tích thật ×15 tích con =45 lượt trên bộ nhân32×32; bỏ ba nhịp trống. Giữ nguyên 3M, thứ tự tích, bit giữ lại, carry, rounding và precision.
2. Host map word0 một lần, tạo word1/2/3 bằng XOR hai vector cơ sở. Giữ nguyên layout, giao thức, cổng RAM, bank grouping và xử lý N nhỏ.

Số LUT là của bản kết hợp hai thay đổi; chưa đo ablation riêng để gán toàn bộ mức giảm cho host mapping.

## Tài nguyên toàn core

| Tài nguyên | Bản trước | Bản thử mới |
|---|---:|---:|
| LUT | 34,062 | 33,669 |
| FF | 24,950 | 24,932 |
| DSP | 64 | 64 |
| RAMB18 | 48 | 48 |
| RAMB36 | 0 | 0 |

Vivado2018.1, xczu7ev-ffvc1156-2-e, OOC synthesis, cùng setting baseline. WNS sau synth +1.046 ns tại clock báo cáo 5 ns; clock vẫn được đặt sau synth, chưa place/route hoặc xác nhận Fmax. Root/host/data/16 engine đều được tính.
Checkpoint: 16 root RAMB18 +32 data RAMB18, 64 DSP, 0 black box.

## Chu kỳ RTL N1024

| Kernel | Bản trước | Bản thử mới |
|---|---:|---:|
| NTT q12289 | 985 | 985 |
| FFT32 | 453 | 453 |
| FFT64 generic | 1,752 | 1,752 |
| FFT64 NTRUGen | 1,752 | 1,752 |
| IFFT64 NTRUGen | 1,754 | 1,754 |
| FFT128 R8 | 6,937 | 6,508 |
| IFFT128 R8 | 6,937 | 6,508 |

FFT128 giảm 429 chu kỳ (6.18%), speedup 1.066× ở cùng clock.
Toàn giao dịch FFT128, gồm cold root/input/readback: 17,396 → 16,967 chu kỳ. Không phải tăng tốc toàn thuật toán ký.
FFT N1024 ở đây là 1.024 thành phần scalar =512 điểm phức. Các chế độ ngoài FFT128 giữ chu kỳ như baseline.

## Correctness và kiểm chứng

- 454/454 ca Verilator, 16/16 ca Icarus khớp; có assertion số BF sống, request/phase, host bank conflict và same-edge RAW.
- Root, input và expected payload của cả 454 ca giống nguyên bit với bản 34.062 LUT; chỉ descriptor timing được đổi. C/vector reference không sửa.
- Ánh xạ affine bank/row/phase khớp ánh xạ full-index cũ trên 240 cấu hình, 81.836 word hợp lệ.
- 74 output transform từ RTL mới được C R8 tiêu thụ qua live-input checking; bốn chữ ký N512/N1024 được verifier độc lập chấp nhận; 14 artifact khớp byte với C gốc. Sửa live input bị BRIDGE_FAIL ở cả hai kích thước.
- Chỉ FFT/IFFT/NTT/INTT được thay trong co-sim; các kernel khác, sampler và NTRUGen keygen còn C. Chưa phải full-PQC hardware, formal proof hoặc chuẩn hóa bảo mật.

## Dư địa còn lại

Với 16 engine, lịch hiện tại cần 103.680 tích con cho FFT128 N1024, cận dưới tính toán 6.480 chu kỳ. Kết quả 6.508 chỉ còn cao hơn 28 chu kỳ. NTT32 N1024 có cận ba lượt nhân/BF là 960, hiện 985. Các cận này có điều kiện giữ số engine và cách tính hiện tại.
Tăng tốc lớn hơn cần thay năng lực tính hoặc cách phục vụ workload: ví dụ packed16 NTT cho q nhỏ, batch các transform nhỏ độc lập, hoặc thay cấu trúc số học có chứng minh tương đương. Chưa đo các hướng đó, chưa hứa mức LUT/speedup.
Giảm LUT tiếp nên nhắm mapper/operand mux, metadata và buffer còn lặp; không thể lấy các số sau flatten/rebuild của riêng một tile làm chi phí thật độc lập của tile ấy.

## Tệp

- [Source và chạy lại](../../experiments/a_cg_tune/README.md).
- [Utilization](../build/a_cg_tune/synth/util.rpt), [timing](../build/a_cg_tune/synth/timing.rpt), [audit](../build/a_cg_tune/synth/audit.txt).
- [JSON số đo, mọi ca kiểm và SHA256](a_cg_tune.json).
