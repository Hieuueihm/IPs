# XC7Z020 — baseline hệ thống 160 MHz

Mặc định từ 2026-11-04: **a_cg_packed4_system160**, [baseline được nhận](../../experiments/BASELINE.md), [contract 3.1](../../spec/FlexTransform/3.1/README.md). Không còn dùng dispatch2/synth 5 ns làm mặc định.

**Nguồn:** `experiments/a_cg_packed4_system160/rtl/`. **Top:** `system_wrapper` sinh từ BD, PS7 → AXI interconnect/converter → `a_cg_axil` → `a_cg_fast`. **Target:** `xc7z020clg400-2`, clock 160 MHz. PS FCLK100, input Wizard generated 1:1, MMCM160; jitter 0,300 ns, setup/hold uncertainty 0,100/0,050 ns.

Đã sign-off toàn hệ thống: **34.277 LUT, 33.397 FF, 64 DSP, 48 RAMB18; setup +0,178 ns, hold +0,032 ns**, 0 lỗi timing/routing/DRC Error. DDR/ngoại vi tắt, chưa chạy board. [Nguồn cấu hình Qiming](../../experiments/a_cg_packed4_system160/board_sources.md).

## Kiểm baseline đã nhận

Chạy từ root repo:

```powershell
python -X utf8 scripts/check_baseline.py
python -X utf8 experiments/a_cg_packed4_system160/validate.py
```

Checker baseline so nguồn/bằng chứng với [manifest](../../experiments/BASELINE.json). Raw evidence nằm trong `study/build/` và bị git-ignore: giữ/copy asset khi chuyển máy. Thiếu asset phải báo thiếu, không tạo lại hash rồi coi là cùng lần đo.

## Audit STA mà không ghi đè mốc

```powershell
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source fpga/z020/audit.tcl
```

Đọc `study/build/a_cg_packed4_system160/route/signoff.dcp`, tính lại đầy đủ max/min/clock/CDC, xuất báo cáo riêng ở `study/build/z020_packed4_baseline_audit/`. Không chạy place/route và không ghi lại DCP/report đã pin. Đây là kiểm lại STA, không phải nạp board.

## Full build trên workspace sạch/bản sao

```powershell
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source fpga/z020/synth.tcl
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source fpga/z020/implement.tcl
```

Các điểm vào này dùng generator/implementation của baseline, không lấy file ở `hdl/`. Chúng dừng nếu checkpoint baseline đã tồn tại để tránh ghi đè bằng chứng được nhận; dùng bản sao workspace hoặc output thử nghiệm riêng khi build lại. Không xóa raw evidence chỉ để vượt guard. Lượt build mới chưa tự trở thành baseline dù RTL giống nhau; giữ riêng kết quả và đối chiếu manifest/constraint.

ZCU106 và các nhánh Z020 cũ được giữ để đối chiếu. Thêm DDR, DMA, ngoại vi hoặc clock mới phải sign-off lại phạm vi mới.
