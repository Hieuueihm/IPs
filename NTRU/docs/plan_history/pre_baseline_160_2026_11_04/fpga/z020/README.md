# Mục tiêu FPGA hiện tại: XC7Z020-CLG400-2

Theo lựa chọn của người dùng, chuyển lượt synth sang chip trên board Qiming.
Giữ cấu hình ZCU106 cũ để đối chiếu; chưa đổi RTL chính.

Source đo: `experiments/a_cg_z020_dispatch2/rtl/`, bản sao từng byte của prototype
dispatch2 đã qua các kiểm tra PQC. Clock synth 5 ns, đủ host adapter và root cache.
Giữ packed16, FFT32/64/128, NTT nhiều modulus và lịch kernel hiện tại.

Từ thư mục gốc, chạy Vivado với `-mode batch -source fpga/z020/synth.tcl`.
Sau khi synth xong, chạy `python -X utf8 experiments/a_cg_z020_dispatch2/report.py`.
Kết quả nằm ở `study/build/a_cg_z020_dispatch2/synth/` và
`study/results/a_cg_z020_dispatch2.md`.

Đây chưa phải project chạy board: chưa P&R, chưa thêm PS/AXI/DMA, chưa chọn chân
hoặc mô hình clock/I/O của board. Không dùng timing của ZCU106 để kết luận 200 MHz
trên Z020. Mục tiêu giảm về khoảng 30k LUT vẫn là công việc tối ưu tiếp theo.
