# Packed16 dùng cả bốn leaf — kết quả nguyên mẫu

**Cập nhật P&R sau phép đo synth này:** bản hệ thống riêng đã đạt 160 MHz,
34.277 LUT, setup +0,178 ns và hold +0,032 ns. Xem
[báo cáo toàn hệ thống](a_cg_packed4_system160.md). Các dòng “chưa P&R”
bên dưới mô tả phạm vi của riêng phép đo OOC ở thời điểm sinh báo cáo này.

Nguồn riêng: `experiments/a_cg_packed4/rtl/`. Baseline 160 MHz không đổi. Chưa commit.

## Tài nguyên: cùng top AXI host + core + data/root, chỉ synth

| Bản | LUT | FF | DSP | RAMB18 | Setup nội bộ (ns) | Hold nội bộ (ns) |
|---|---:|---:|---:|---:|---:|---:|
| Baseline, synth lại cùng flow | 31,137 | 30,644 | 64 | 48 | -0.531 | +0.126 |
| Hai luồng, T-high riêng | 35,393 | 33,911 | 64 | 48 | -0.531 | +0.126 |
| Hai luồng, T-high dùng chung (RTL hiện tại) | 34,185 | 32,855 | 64 | 48 | -0.531 | +0.126 |

Part `xc7z020clg400-2`, Vivado 2018.1, chu kỳ 6,25 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns, input jitter 0,300 ns.
Các con số OOC này không bao gồm PS7/interconnect/MMCM/reset của top board. Không thay số P&R toàn hệ thống 31.242 LUT của baseline.
Setup synth âm là chưa đạt ràng buộc trong mô hình ước tính này. Chưa P&R hoặc sign-off 160 MHz cho ứng viên; không thừa kế sign-off baseline.

## Chu kỳ kernel đo qua AXI

| q | N | hmin | Jobs | Hướng | Baseline packed16 | Bốn leaf | Tăng tốc |
|---:|---:|---:|---:|---|---:|---:|---:|
| 3329 | 256 | 1 | 1 | NTT | 237 | 214 | 1.107× |
| 3329 | 256 | 1 | 1 | INTT | 236 | 213 | 1.108× |
| 3329 | 256 | 1 | 4 | NTT | 381 | 286 | 1.332× |
| 3329 | 256 | 1 | 4 | INTT | 380 | 285 | 1.333× |
| 12289 | 512 | 0 | 1 | NTT | 351 | 298 | 1.178× |
| 12289 | 512 | 0 | 1 | INTT | 350 | 297 | 1.178× |
| 12289 | 1024 | 0 | 1 | NTT | 531 | 391 | 1.358× |
| 12289 | 1024 | 0 | 1 | INTT | 530 | 390 | 1.359× |
| 12289 | 1024 | 0 | 2 | NTT | 987 | 535 | 1.845× |
| 12289 | 1024 | 0 | 2 | INTT | 986 | 534 | 1.846× |

252 ca packed16 qua kiểm; mọi ca không tăng chu kỳ. 774 ca nonpacked giữ nguyên chu kỳ và kết quả.
Đây là chu kỳ kernel; không quy đổi thành tốc độ toàn bộ signer hay thông lượng AXI end-to-end.

## Correctness và mức sử dụng leaf

- 1.026 ca FFT32/64/128, scalar/packed NTT, nhiều modulus và batch qua AXI: không sai số.
- Oracle tile độc lập: 16.800 gói / 33.600 butterfly, hai slot, CT/GS, halving, pairing, bubbles, enable stall, dữ liệu biên.
- 300 gói bão hòa trong 448–449 khoảng chu kỳ. Có chu kỳ cả bốn leaf chứa phép toán hợp lệ; thông lượng ổn định 4 butterfly/3 chu kỳ/tile.
- Reset khi cả hai luồng đang xử lý: không có response cũ sau reset.
- 10 ca four-state tập trung packed16 ở cấp lõi: PASS, có N=2/N1024, incomplete NTT và batch.
- C replay: 74 transform; 14 artifact trùng từng byte; 4 chữ ký xác minh độc lập; altered-live-input bị từ chối.
- AXI split AW/W, B/R stalls, WSTRB, lỗi địa chỉ/lệnh và reset giao dịch: PASS.

## Phần thay đổi

Chia leaf0/1 và leaf2/3 thành hai luồng lệch một chu kỳ. Tích thô được căn độ trễ năm chu kỳ và phản hồi riêng từng nhóm. Hai luồng dùng chung T-high/NZ history, reducer cuối, add/sub và side/tag RAM. Không thêm DSP hoặc cổng BRAM.
Core đọc ở hai pha mỗi ba chu kỳ; planner đổi thời điểm phát và gap giữa tầng, kiểm bank/RAW và phiên bản dữ liệu. Transform ngắn vẫn chịu fill/drain; batch giúp tăng lượng công việc độc lập.

Nguồn và constraints đã đóng băng trong `study/build/a_cg_packed4/rtl_final/` và `final_source_manifest.json`. Kết quả máy đọc: `study/build/a_cg_packed4/results.json`.
Bản đầu T-high riêng giữ ở `variants/separate_history/tile_a.sv`, `synth_candidate`, `sim_v0.log`, `application_v0`. Four-state v0 dừng khi đổi bản, không tính là PASS.
Kiểm lại bằng `python -X utf8 experiments/a_cg_packed4/report.py` và `python -X utf8 scripts/check_baseline.py`.
