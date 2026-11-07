# FlexTransform — FFT đa precision và NTT đa modulus

**Baseline được chấp nhận ngày 2026-11-04: `a_cg_z020_system160`.** Hệ thống PS7 → AXI → lõi FFT/NTT đã qua P&R và sign-off STA tại **160 MHz** trên `xc7z020clg400-2`. Nguồn chuẩn vẫn ở thư mục được chỉ rõ bên dưới; không lấy RTL cũ trong `hdl/` ghép vào baseline này.

| Kết quả toàn hệ thống | Giá trị |
|---|---:|
| LUT / FF | **31.242 / 31.186** |
| DSP48 / RAMB18 | **64 / 48** |
| Setup / hold | **+0,038 / +0,011 ns** |
| Pulse-width slack | **+1,995 ns** |
| Endpoint vi phạm timing | **0** |

Phạm vi gồm PS7/OCM-JTAG, AXI interconnect/converter, AXI-Lite, MMCM/reset, toàn lõi/data/root. DDR và ngoại vi carrier đang tắt; **chưa nạp hoặc đo trên board**. Mốc 160 MHz là điểm đã sign-off, không phải Fmax cực đại đã tìm được.

## Đọc từ đâu

1. [Baseline và nguồn được nhận](experiments/BASELINE.md), [manifest máy đọc](experiments/BASELINE.json).
2. [Kiến trúc hiện hành](docs/architecture_v1.md).
3. [Contract 3.0 của baseline](spec/FlexTransform/3.0/README.md): phạm vi, số học, giao tiếp và kiểm chứng.
   [Spec triển khai RTL và cổng logic](spec/FlexTransform/3.0/05_trien_khai_rtl.md) hướng dẫn nối module và pipeline để viết lại.
4. [Báo cáo sign-off](study/results/a_cg_z020_system160.md), [bản tích hợp và register map](experiments/a_cg_z020_system160/README.md).
5. [Kế hoạch tiếp theo](PLAN.md). [Spec 2.0](spec/FlexTransform/2.0/README.md) và [bản lưu tài liệu cũ](docs/plan_history/pre_baseline_160_2026_11_04/INDEX.md) phục vụ đối chiếu.

## Source và lệnh kiểm

- **RTL baseline:** [experiments/a_cg_z020_system160/rtl/](experiments/a_cg_z020_system160/rtl/), gồm `a_cg_axil.v`, `a_cg_fast.sv`, `tile_a.sv`, `mul_ss.v`.
- Top hệ thống: `system_wrapper`, sinh bởi [create_project.tcl](experiments/a_cg_z020_system160/create_project.tcl).
- [Điểm vào build XC7Z020](fpga/z020/README.md); checkpoint chốt là `study/build/a_cg_z020_system160/route/signoff.dcp`.
- Kiểm nguồn và bằng chứng đã nhận: `python -X utf8 scripts/check_baseline.py`.
- [Danh mục `hdl/`](hdl/README.md) ghi rõ source cũ. Giữ nguyên các file RTL ở đó để bảo toàn lịch sử và script cũ.

## Đã kiểm chứng

Giữ FFT32/64/128, native NTRUGen64, NTT đa modulus, packed16 và batch đồng cấu hình. 1.026 ca qua AXI khớp kết quả và chu kỳ kernel; kiểm AW/W độc lập, B/R stall, WSTRB, reset bridge và IP reset Xilinx. 74 lời gọi transform từ ứng dụng C cho 14 artifact giống reference, 4 chữ ký qua verifier độc lập. Phần ngoài transform vẫn chạy C; đây chưa phải toàn signer RTL.

IFFT scale khi đọc host: phải đọc hết kết quả trước cấu hình/start/load tiếp theo. Không suy tăng tốc toàn ứng dụng từ chu kỳ kernel hoặc coi toàn spec 2.0 đã đạt.

## Quy tắc cập nhật

Nguồn và bằng chứng baseline được pin bằng SHA-256. Thử nghiệm mới làm trên bản riêng; chỉ thay baseline khi người dùng chấp nhận. Tài liệu phải phân biệt kết quả mô hình, synth, OOC và STA toàn hệ thống, đồng thời ghi đúng source và cấu hình đã đo. Không tự giảm precision, đổi rounding hoặc nới constraint để tăng số đo.
