# Thử ba hướng cải thiện timing, giữ packed16

**Đề xuất giữ bản host:** LUT thấp nhất và WNS ước tính toàn core bằng bản kết hợp. Bản kết hợp thêm 767 LUT nhưng chưa tăng margin timing synth. Đây chưa phải kết luận sau route.

Chỉ synth, cùng part xczu7ev-ffvc1156-2-e và cùng XDC clock 5 ns đọc trước synth. Không P&R, không sửa RTL chính. Các input mode vẫn runtime; không buộc mode để làm nhỏ mạch.

| Bản | LUT | Δ LUT | FF | WNS nội bộ | Δ WNS nội bộ | WNS gồm I/O |
|---|---:|---:|---:|---:|---:|---:|
| base | 36,862 | +0 | 25,322 | +0.826 ns | +0.000 ns | +0.192 ns |
| host | 36,721 | -141 | 25,334 | +1.417 ns | +0.591 ns | +1.417 ns |
| local | 37,322 | +460 | 25,380 | +0.826 ns | +0.000 ns | +0.192 ns |
| raw | 36,957 | +95 | 25,334 | +0.826 ns | +0.000 ns | +0.192 ns |
| all | 37,488 | +626 | 25,389 | +1.417 ns | +0.591 ns | +1.417 ns |

Mọi bản đều 64 DSP, 48 RAMB18 (32 data + 16 root), không blackbox. WNS càng lớn càng tốt dưới CÙNG ràng buộc. Không quy đổi WNS này thành Fmax sau route. Baseline so sánh là bản base mới, không phải lượt 36.231 LUT tạo clock sau synth.

## Ý nghĩa các bản

- host: chụp request/line/data, phục vụ bank từ chu kỳ sau; bỏ đường xuyên từ ready/accept đến RAM trong cùng chu kỳ.
- local: giữ các register cấu hình trong mỗi tile; không DONT_TOUCH mảng nhân, bộ nhớ hay toàn datapath.
- raw: FFT dùng tổng/hiệu thô, NTT dùng hiệu chỉnh q cũ; cùng carry/borrow, wrap, rounding và số bit.
- all: kết hợp cả ba.

## Kiểm chứng

- Mỗi bản sửa qua 1.026 ca dùng lại input/root/expected đã đóng băng. Tất cả chu kỳ kernel trùng baseline.
- Bộ cộng mới khớp bản cũ trong 100.256 phép thử, gồm signed-bit patterns, wrap, carry/borrow, NTT32 và packed16.
- Bản kết hợp qua 38 ca Icarus bốn trạng thái; 74 lần gọi transform từ C, 4 chữ ký verify và 14 artifact khớp từng byte; đầu vào live bị sửa bị từ chối.
- Bản host được đề xuất cũng qua riêng 38 ca bốn trạng thái, 74 lần gọi C, 4 chữ ký verify và 14 artifact khớp từng byte; đầu vào live bị sửa bị từ chối.
- Bản host/all thêm đúng 2 × ceil(số word/4) chu kỳ cho tổng nạp + đọc của mỗi ca. Chi phí nằm ở host, không ẩn vào số kernel.

## Fanout điều khiển sau synth

| Bản | dir max | mf max | fmt_r max | shift_r max | native_r max |
|---|---:|---:|---:|---:|---:|
| base | 1046 | 144 | 122 | 174 | 96 |
| host | 1046 | 160 | 122 | 174 | 111 |
| local | 377 | 221 | 84 | 156 | 6 |
| raw | 1046 | 99 | 122 | 174 | 96 |
| all | 377 | 312 | 84 | 156 | 6 |

## Chu kỳ kernel và giao dịch host ở bản đề xuất

| Trường hợp | Kernel trước/sau | Cold baseline | Cold host |
|---|---:|---:|---:|
| Packed16 NTT q=12289 N=1024 | 505 / 505 | 1544 | 1800 |
| Packed16 NTT q=3329 N=256 | 217 / 217 | 421 | 485 |
| FFT128 N1024 | 6508 / 6508 | 16967 | 19015 |

Cold gồm cấu hình, root, nạp, kernel và đọc theo cùng driver. Chi phí host tăng đã được tính, không suy ra tăng tốc toàn ứng dụng từ WNS synth.

## Đường tới hạn nội bộ

- base: `state_reg[3]/C` → `data_bank[24].mem_reg/WEBWE[3]`; 3.645ns  (logic 0.685ns (18.793%)  route 2.960ns (81.207%)); 13  (LUT3=2 LUT4=2 LUT5=2 LUT6=7).
- host: `state_reg[0]/C` → `data_bank[1].mem_reg/ADDRBWRADDR[7]`; 3.142ns  (logic 0.589ns (18.746%)  route 2.553ns (81.254%)); 11  (LUT2=1 LUT4=1 LUT5=1 LUT6=8).
- local: `state_reg[3]/C` → `data_bank[24].mem_reg/WEBWE[3]`; 3.645ns  (logic 0.685ns (18.793%)  route 2.960ns (81.207%)); 13  (LUT3=2 LUT4=2 LUT5=2 LUT6=7).
- raw: `state_reg[3]/C` → `data_bank[24].mem_reg/WEBWE[3]`; 3.645ns  (logic 0.685ns (18.793%)  route 2.960ns (81.207%)); 13  (LUT3=2 LUT4=2 LUT5=2 LUT6=7).
- all: `state_reg[0]/C` → `data_bank[1].mem_reg/ADDRBWRADDR[7]`; 3.142ns  (logic 0.589ns (18.746%)  route 2.553ns (81.254%)); 11  (LUT2=1 LUT4=1 LUT5=1 LUT6=8).

## Giới hạn

- Unplaced net delay estimates; not physical Fmax or timing closure.
- XDC identical for all variants; Vivado may classify uncertainty as implementation-only. Inspect actual timing reports.
- Local DONT_TOUCH applies only to configuration flops and does not guarantee physical placement locality.
- Host/all trade one load and one read cycle per host line for a registered request path.
- Application replay substitutes only FFT/IFFT/NTT/INTT; remaining application code runs in C.
- WNS setup dương không có nghĩa đã khép timing. Mô hình I/O tạm còn hold -0,110 ns sau synth; hold register→register được ghi riêng trong JSON. Chưa có timing sau layout.

README và lệnh tái lập: experiments/a_cg_timing/README.md. JSON lưu từng ca, hash nguồn/checkpoint và dữ liệu ứng dụng.
