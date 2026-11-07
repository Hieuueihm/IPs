> **Contract lịch sử.** Baseline hiện hành là packed16 bốn leaf `a_cg_packed4_system160`, xem [spec 3.1](../3.1/README.md). Nội dung 3.0 bên dưới giữ mô tả lịch một gói packed16 mỗi ba chu kỳ của mốc trước.

# FlexTransform 3.0 — contract baseline 160 MHz

Ngày nhận: **2026-11-04**. Implementation: **`a_cg_z020_system160`**, [nguồn/manifest baseline](../../../experiments/BASELINE.md). Đây là contract của bản đã triển khai và kiểm chứng, không phải lời xác nhận mọi yêu cầu công nghiệp của spec 2.0 đều hoàn thành.

| Tài liệu | Nội dung |
|---|---|
| [00_pham_vi.md](00_pham_vi.md) | Mode, giới hạn cấu hình và phần ngoài phạm vi |
| [01_so_hoc.md](01_so_hoc.md) | Precision, Montgomery, 3M và scale IFFT |
| [02_giao_dien.md](02_giao_dien.md) | Native core, AXI map, sequencing và reset |
| [03_bo_nho.md](03_bo_nho.md) | 32 bank, root, CG và batch |
| [04_kiem_chung.md](04_kiem_chung.md) | Những gì đã kiểm, STA và cách tái kiểm |
| [05_trien_khai_rtl.md](05_trien_khai_rtl.md) | Cấu trúc cổng/mux/thanh ghi, port từng module, pipeline và cách viết RTL |
| [CHANGELOG.md](CHANGELOG.md) | Khác biệt so với spec 2.0 và điều khiển thay đổi |

Số đo chuẩn là **toàn hệ thống PS7–AXI–lõi**, target XC7Z020-CLG400-2: 160 MHz, 31.242 LUT, 31.186 FF, 64 DSP, 48 RAMB18, setup +0,038 ns, hold +0,011 ns. [Báo cáo](../../../study/results/a_cg_z020_system160.md). DDR/ngoại vi tắt, chưa chạy board.

RTL nằm tại [baseline/rtl](../../../experiments/a_cg_z020_system160/rtl/); top hệ thống `system_wrapper` sinh từ BD. Thư mục `hdl/`, spec 1.0/2.0 và các báo cáo cũ giữ làm lịch sử, không phải file list/giao diện cho baseline 3.0.

Khi có khác biệt giữa mô tả và RTL/vector đã pin, ghi issue và đối chiếu source/evidence; không tự đổi rounding, bit layout hoặc nới constraint. Việc bổ sung một tính năng còn thiếu của 2.0 phải có yêu cầu, kiểm chứng và phiên bản contract tương ứng. Tài liệu mô tả không tự biến yêu cầu chưa có thành tính năng đã đạt.
