# Nguyên mẫu A + CG bốn nguồn

Source độc lập, không thay `hdl/`, `PLAN.md` hoặc spec. Kết quả tổng hợp và
phạm vi so sánh ở [báo cáo](../../study/results/a_cg_prototype.md).

Top `rtl/a_cg_core.sv` gồm đủ adapter host, dữ liệu, descriptor, root cache và
16 engine. Host giao tiếp trực tiếp, chưa có AXI/DMA. Giữ một context root cho
một chiều; không giữ sẵn toàn bộ ROM/slot của core cũ. Có rào giữa các tầng.

`rtl/tile_a.sv` được `build.py` sinh từ source production đã kiểm SHA256.
Các comment upstream được giữ để đối chiếu; hợp đồng nguyên mẫu khác upstream:

- FFT input: `re0, im0, re1, im1, ...`, output: tất cả real limb rồi imaginary.
- Precision và shift là hai cổng cấu hình riêng; không mã hóa chúng trong q.
- 8/4/2 slot BF cho 32/64/128 bit, X/W/side 16 entry, tổng 3M 8 entry.
- `ext_fft_valid/mpr/mst` từ sequencer chung; không còn hàng chờ multiplier riêng.
- Giữ 64 FF real/root gần nhất để bỏ lượt đọc PRE; carry GS real/imag riêng.
- Top chỉ phát mode NTT scalar và FFT; không có lệnh packed16.

Chạy từ repo root trên máy này:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File experiments/a_cg/run.ps1 -Synthesize
```

Lệnh tạo snapshot nguồn, fixture, build Verilator, kiểm số học, kiểm Icarus
bốn trạng thái rồi synth Vivado 2018.1. Công cụ dùng đường dẫn đã cài trên máy.
Mô phỏng không synth: bỏ `-Synthesize`; thêm `-FourState` để chạy cả Icarus.

Sau synth có thể kiểm checkpoint và tổng hợp báo cáo:

```powershell
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg/audit.tcl
python -X utf8 experiments/a_cg/report.py
```

Build/report ở `study/build/a_cg_prototype/`; report kết luận ở
`study/results/a_cg_prototype.{md,json}`. Không commit tự động.
