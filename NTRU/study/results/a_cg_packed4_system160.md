# Packed16 bốn leaf — P&R toàn hệ thống 160 MHz

**ĐẠT timing 160 MHz theo báo cáo routed toàn hệ thống.**
Baseline được người dùng nhận ngày 2026-11-04, contract 3.1. Mốc trước `a_cg_z020_system160` giữ làm lịch sử. Chưa commit/chạy board.

| Chỉ tiêu | Baseline cũ | Packed16 bốn leaf |
|---|---:|---:|
| Setup WNS (ns) | +0.038 | +0.178 |
| Hold WHS (ns) | +0.011 | +0.032 |
| Pulse-width slack (ns) | +1.995 | +1.995 |
| LUT | 31,242 | 34,277 |
| FF | 31,186 | 33,397 |
| DSP48 | 64 | 64 |
| RAMB18 | 48 | 48 |

Setup vi phạm 0/79442 endpoint; hold vi phạm 0/79442; pulse width vi phạm 0.
Routing: 64234/64234 net; 0 lỗi. DRC: 0 Error, 64 Warning.
CDC an toàn: True. Endpoint chưa ràng buộc: 0. Ngân sách ≤35k LUT: True.

## Phạm vi và ràng buộc

Part xc7z020clg400-2; Vivado 2018.1. PS7 reference 33,333333 MHz, FCLK100 → MMCM160; AXI và lõi chung miền 160 MHz. DDR/ngoại vi tắt, dùng cấu hình OCM/JTAG như baseline.
Ràng buộc `signoff.tcl` giống baseline từng byte: PS clock jitter 0,300 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns; clock Wizard dẫn từ FCLK thật. Không dùng I/O OOC hoặc giả định chân clock ảo.
P&R mặc định: opt_design → place_design → phys_opt_design → route_design. Không thay RTL, precision, modulus hay thêm timing exception để làm đẹp kết quả.

## Đường setup xấu nhất

Nguồn: `system_i/accelerator/inst/core/u_exec/e_product_reg[0]/C`.
Đích: `system_i/accelerator/inst/core/u_exec/engine[8].u_tile/g_arr32.bsel_reg[0]/D`.

## Correctness và bằng chứng

Bốn file RTL giống từng byte với ứng viên `a_cg_packed4` đã kiểm: 1.026 ca AXI, 33.600 butterfly tại tile, 10 ca four-state, 74 transform C, 14 artifact giống từng byte và 4 chữ ký xác minh độc lập. Đây là kiểm chứng chức năng RTL; chưa chạy gate-level SDF hoặc board.
Checkpoint cuối: `study/build/a_cg_packed4_system160/route/signoff.dcp`. Các báo cáo setup/hold, timing summary, clocks, CDC, exceptions, check_timing, route_status và DRC ở cùng thư mục.
Kết quả máy đọc: `study/build/a_cg_packed4_system160/signoff_results.json`. Hash RTL/workflow trong `input_manifest.json`; hash bằng chứng trong `evidence_sha256.json`.
Kiểm lại: `python -X utf8 experiments/a_cg_packed4_system160/report.py`. Trạng thái baseline xem `experiments/BASELINE.json`; không tự nâng baseline khi chạy report.
