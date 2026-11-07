# Sign-off STA PS7–AXI–FFT/NTT, XC7Z020-CLG400-2

Ngày đo/nhận baseline: 2026-11-04. **Baseline hiện hành: `a_cg_z020_system160`**, xem [nguồn và manifest](../../experiments/BASELINE.md). **Đạt STA cho thiết kế tích hợp tại 160 MHz**, trong phạm vi PS7/OCM-JTAG, AXI interconnect/converter, AXI-Lite bridge, MMCM/reset và toàn bộ lõi/data/root. DDR và ngoại vi carrier đang tắt. Chưa nạp/đo trên board. RTL chính không đổi, chưa commit.

| Chỉ tiêu | Đo sau P&R và audit clock |
|---|---:|
| Setup WNS | **+0,038 ns**, 0 endpoint lỗi |
| Hold WHS | **+0,011 ns**, 0 endpoint lỗi |
| Pulse-width slack | **+1,995 ns**, 0 endpoint lỗi |
| Endpoint setup/hold | **77.432** |
| LUT / FF | **31.242 / 31.186** |
| DSP / RAMB18 | **64 / 48** |
| Route | **59.641/59.641** net, 0 lỗi |

Jitter 0,300 ns tại PS FCLK100 và nhánh Wizard, clock input Wizard generated 1:1 từ PS, MMCM ra 160 MHz. Setup uncertainty 0,100 ns, hold uncertainty 0,050 ns. Không dùng virtual I/O delays hoặc OOC clock location. Các cổng lệnh/data thô đã nối với thanh ghi/bus AXI thực, nên lỗi hold I/O OOC trước đó không còn.

Không có clock/endpoint/port thiếu ràng buộc hoặc vòng tổ hợp. CDC báo mọi đường được timing an toàn. DRC 0 lỗi, còn 64 khuyến nghị input-pipeline DSP. Không thêm false-path/multicycle cho datapath; exception vendor duy nhất có endpoint không tồn tại, không ảnh hưởng đường nào.

Correctness: 1.026 ca qua AXI khớp từng bit và chu kỳ kernel; kiểm AW/W độc lập, B/R stall, WSTRB, reset giao dịch và reset IP Xilinx; 74 transform gọi từ ứng dụng C, 14 artifact giống reference, 4 chữ ký qua verifier độc lập. Giữ nguyên packed16, FFT32/64/128, NTT multi-modulus và native NTRUGen64. Phần ngoài transform vẫn ở C.

Worst setup: `q_root_addr_reg[7]` tới root BRAM engine 4; chủ yếu là dây phân phối địa chỉ root. Worst hold: `prev_real_reg[25]` tới `sa5_reg[31]` ở tile 11. Đây là số STA, không phải đo trên board và không bao gồm ngoại vi chưa ghép.

Chi tiết: [README bản tích hợp](../../experiments/a_cg_z020_system160/README.md), [nguồn board](../../experiments/a_cg_z020_system160/board_sources.md), [kết quả máy đọc](../build/a_cg_z020_system160/signoff_results.json), [timing toàn hệ thống](../build/a_cg_z020_system160/route/timing.rpt). Checkpoint chốt: `study/build/a_cg_z020_system160/route/signoff.dcp`. Dùng `python -X utf8 scripts/check_baseline.py` để kiểm mốc đã pin; `fpga/z020/audit.tcl` tính lại STA sang thư mục riêng, không ghi đè bằng chứng.
