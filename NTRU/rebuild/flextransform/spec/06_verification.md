# 06 — Kế hoạch kiểm chứng và nghiệm thu

Mọi PASS thuộc RTL/source/constraint hash cụ thể. Source mới không thừa hưởng 160 MHz, 1.026 ca hay 74 lời gọi C của source cũ.

## 1. Ba lớp kiểm tra độc lập

1. **Oracle số học:** công thức integer/executable C, không viết expected bằng cách chạy lại RTL model.
2. **Model mapping/lịch:** bank/row/root, resource reservation, phiên bản dữ liệu, liveness.
3. **RTL:** actual handshake, latency, reset, X propagation và netlist/resource/timing.

Arithmetic có thể đúng trong khi tầng đọc sai dữ liệu; model schedule có thể đúng trong khi RTL trễ một clock. Phải qua đủ ba lớp.

## 2. Unit và các corner case

| Unit | Kiểm tra tối thiểu |
|---|---|
| Leaf/fuse | signed×signed, mixed sign, unsigned max; raw/fused đúng cùng transaction |
| Add/sub | carry/borrow0/1, unsigned q biên, ±q, tách lane; real/imag carry độc lập |
| Montgomery | q3, q gần2¹⁵/2³¹, T_lo0/khác0, U≥q; CT/GS và inverse half |
| Packed | Hai nhóm có giá trị/tag/root khác nhau; pairing0/1; bubbles tại pha hợp lệ; reset cả hai nhóm đang có việc |
| FFT multiply | W32/64/128, signed min/max, all-ones, ties, carry từ cột thấp; 15-product128 so full-product oracle |
| FFT butterfly | 3M, CT/GS, mọi limb/buffer, nhiều butterfly chồng lấp |
| Native | mul không rounding seed; wrap(v+1) trước half; sum/diff có dấu âm và overflow |
| Tile state | Pointer wrap, allocate/release cùng clock, full/empty, giữ tag/pairing/side |
| Host normalize | Mọi fmt, s0..9, negative minimum, bias overflow; không lẫn hai số64/bốn số32 trong line |

Probe latency sau cạnh nhận và trước cạnh consumer tách riêng. Assert đúng valid/tag/data ở từng boundary. Tile mới không có input en/pause; không gọi test CE-stall của tile cũ là coverage cho API mới. Test bus stall vẫn bắt buộc.

## 3. Kiểm model bộ nhớ

Quét mọi tổ hợp mode/fmt/logn/hmin/jobs hợp lệ theo decode. Với mỗi cấu hình/chiều:

- Mỗi logical word có duy nhất một bank/row, đúng buffer/plane/job.
- Dummy/OOB không ghi đè word thực.
- Mỗi bank tối đa1R/1W mỗi clock; root đủ1R/tile/clock.
- Không RAW cùng cạnh, read đúng version tầng trước, không overwrite quá sớm.
- Root span≤512, active mask và expected tail tag đúng thực tế từng tile.
- Không tranh multiplier, U/correction, side RAM hoặc FFT buffer.
- Queue context không vượt16, side không vượt16, FFT occupancy≤8/4/2.
- Output host đúng natural order của API phần mềm, không tự đồng nhất với thứ tự đánh giá NTT trên giấy.

Xuất trace event máy đọc và latency manifest; generator descriptor chỉ chạy từ manifest đang đo. Mỗi thay đổi latency phải làm stale hash của descriptor cũ.

## 4. Differential kernel

Tái dùng input/expected/root của 1.026 ca baseline, gồm252 packed và774 nonpacked. Chỉ regenerate descriptor/schedule và protocol adapter cần thiết. Hash riêng arithmetic payload để chứng minh không thay golden khi timing thay đổi.

Chạy đủ FFT32/64/128 thường/native, scalar/packed NTT nhiều q, cả chiều, hmin và batch bank/row. Kiểm output từng word; FFT round-trip gần đúng hoặc chỉ pass checksum không thay được việc này.

Four-state bằng Icarus hoặc simulator tương đương trên **source mới**: các đường vừa đổi, mọi precision/direction và boundary nhỏ. Có negative tests chứng minh assertions bắt sai schedule/uninitialized read. Không chốt chỉ bằng Verilator hai-state.

## 5. Command/AXI/reset

AW trước W, W trước AW, B/R stall dài, byte strobes, unaligned/unmapped, lệnh nhiều bit, payload thay ngay sau accepted command. Một command không được execute hai lần do token bị giữ valid.

Reset tại cfg setup, root/desc pending, host LOAD/READ từng phase, packed feedback, FFT column, writeback và response đang giữ. Kiểm không có response cũ sau core reset; công việc kế tiếp phải đúng. Soft reset không được phá response AXI đã phát mà chưa handshake; chỉ bus/system reset mới hủy transaction AXI theo reset domain.

START thiếu context/desc/root phải trả lỗi và không ghi compute. Trước DONE, cố đọc khi busy không được nhận. Sau DONE, mọi write đã commit. Mask thiếu tile0 trong một **lịch được generator xác nhận hợp lệ** không được gây treo chỉ vì logic completion cứng tile0.

Descriptor cố ý sai root-order không nhất thiết hardware phát hiện; test generator phải từ chối. Không viết test kỳ vọng một tính năng validation phần cứng chưa có.

## 6. Ứng dụng C

R8 C source/commit/compile flags khóa theo reference_lock và manifest gốc. Dùng LP64; không sửa C arithmetic để làm khớp RTL.

Tại N512/N1024, lấy74 lời gọi FFT/IFFT/NTT/INTT sống, đưa qua RTL mới bằng interface adapter riêng. Output RTL phải thay thế trong C mà không fallback cho kernel được hỗ trợ. So14 artifact byte-exact và kiểm4 chữ ký bằng verifier riêng. Cố tình đổi live input phải bị từ chối.

CMUL/SPLIT/MERGE/sampler/keygen ngoài transform vẫn ở C. Báo phạm vi này; không gắn nhãn full signer RTL hoặc chứng nhận toàn bộ ML-KEM/ML-DSA.

## 7. Resource và timing

Đo unit→tile→core OOC→toàn hệ thống, không trộn các cột. Hàng matched ablation phải cùng part/tool/clock, numerical workload và scope host/root. Netlist phải có đủ64 DSP/48 RAMB18 cho profile chính, zero latch/blackbox, không constant-tie mất mode.

P&R toàn system: xc7z020clg400-2;160MHz; jitter0.300ns; uncertainty setup0.100/hold0.050ns. Dùng generated clocks đúng cây PS/MMCM, constrain mọi endpoint. Setup, hold, pulse-width, CDC, DRC và routing đều audit. Không lấy WNS synth để tính Fmax thật.

Số đo nguồn chuẩn để khôi phục performance được ghi trong design.json. Budget checkpoint đầu cho các kernel đại diện là chu kỳ baseline+16 core clock; đây là **mục tiêu đề xuất** của rewrite, không phải chứng nhận đã đạt. Các overhead phải xuất hiện trong trace, không đổi định nghĩa bộ đếm để che regression.

## 8. Traceability

| Requirement | Kiểm ở đâu | Gate |
|---|---|---|
| R01/R02 | Oracle C, unit/tile/kernel | M1,M2,M3,M5 |
| R03/R04 | Modulo oracle, packed rate/reset, full core | M2,M3,M4,M6 |
| R05/R06/R07 | Decode exhaustive, mapping/event replay, RAM infer | M1,M4,M6 |
| R08/R09/R10 | Command/AXI/reset/four-state | M3,M6,M7 |
| R11 | Write commit/tail mask/context queue | M4,M5,M6 |
| R12/R13 | Same-scope synth và full P&R | M2,M3,M7 |
| R14 | Build/asset/source/constraint manifests | M0..M8 |
| R15 | Full differential và live application replay | M6,M7 |

## 9. Một run phải lưu gì?

Source/filelist/git state, tool version, seed/strategy, constraints, arithmetic asset hash, latency manifest hash, descriptors, command line, test log, cycle/counter CSV, resource reports, timing/DRC/CDC reports và DCP khi có. Record expected/got của ca fail trước khi sửa. Output dưới `study/build/flextransform_rebuild/<run_id>/`.

Chỉ khi source/codegen/constraints thay đổi hoặc có failure mới cần chạy lại coverage bị ảnh hưởng. Không dùng việc chạy lại cùng test nhiều lần làm thay thế cho thiếu kiểm ở một boundary khác.
