# 3.0 — bằng chứng và nghiệm thu baseline

Baseline được nhận ngày 2026-11-04, không phải bộ kiểm tự chứng minh mọi đầu vào khả dĩ. [Manifest nguồn/evidence](../../../experiments/BASELINE.json), [báo cáo STA](../../../study/results/a_cg_z020_system160.md).

| Kiểm tra | Phạm vi đã đạt |
|---|---|
| 1.026 ca qua AXI-Lite | Khớp từng bit và chu kỳ kernel so với reference/planner; 252 ca packed, 78 ca native trong suite |
| AXI protocol | AW/W độc lập, B/R stall, WSTRB, địa chỉ và command không hợp lệ |
| AXI reset | AW-only/W-only trước reset không ghép với nửa transaction sau reset; B/R pending được flush |
| IP reset Xilinx | Startup, giữ reset khi chưa lock, PS reset, mất lock, aux active-low |
| 74 lời gọi transform từ C | 14 artifact giống reference, 4 chữ ký qua verifier độc lập; phần ngoài transform vẫn ở C |
| Core gốc cùng byte RTL | 38 ca bốn trạng thái, reset-abort 12 mode; hai modulus slot kiểm ở tile độc lập, core dùng slot 0 |

## STA toàn hệ thống

XC7Z020-CLG400-2, Vivado 2018.1. 160 MHz/6,250 ns; jitter PS/input Wizard 0,300 ns; setup/hold uncertainty 0,100/0,050 ns. Clock input Wizard generated 1:1 từ PS FCLK100, MMCM ra 160. Checkpoint chốt **`study/build/a_cg_z020_system160/route/signoff.dcp`**.

Kết quả: **31.242 LUT, 31.186 FF, 64 DSP, 48 RAMB18**; setup **+0,038 ns**, hold **+0,011 ns**, pulse-width **+1,995 ns**; 0 endpoint vi phạm, 77.432 endpoint setup/hold. 59.641/59.641 net route, 0 lỗi routing, 0 DRC Error. Còn 64 cảnh báo khuyến nghị DPIP-1, không gọi là 0 warning.

Không có pin thiếu clock/endpoint thiếu ràng buộc, I/O thiếu hoặc thiếu một phần delay, clock mất nguồn, nhiều clock hoặc vòng tổ hợp. CDC báo mọi đường được timing an toàn. Một exception vendor có endpoint không tồn tại, không loại đường nào; không thêm false-path/multicycle/case-analysis để vượt timing datapath.

STA này áp dụng cho PS7/OCM-JTAG + AXI + clock/reset + toàn core/data/root. DDR/ngoại vi tắt, chưa chạy board. Không dùng số OOC/core-only hoặc kết quả synth thay cho mốc này. Không suy tăng tốc toàn signer hay novelty từ số đo.

## Cách dùng

- Kiểm nguồn/evidence đã pin: `python -X utf8 scripts/check_baseline.py`.
- Kiểm log số học/protocol/reset/ứng dụng: `python -X utf8 experiments/a_cg_z020_system160/validate.py`.
- Tính lại STA trên route: Vivado chạy `fpga/z020/audit.tcl`, rồi checker baseline. Nếu report/hash khác mốc, giữ bằng chứng mới ở bản riêng và đối chiếu, không tự đổi manifest để PASS.
- Full rerun/build có thể mất nhiều phút và có thể khác placement do tool/config; theo [fpga/z020](../../../fpga/z020/README.md). Đổi RTL, latency, memory, clock hoặc constraint phải chạy lại phần kiểm bị ảnh hưởng và phát hành mốc mới khi được nhận.

Archive/build local ở `study/build/` bị git-ignore; manifest không thay thế raw report/DCP/vector/C reference. Cần giữ/copy các asset đã pin khi chuyển máy. Có manifest nhưng thiếu file phải báo thiếu, không coi là đã tái kiểm thành công.
