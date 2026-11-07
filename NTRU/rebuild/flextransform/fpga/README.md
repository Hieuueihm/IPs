# Profile FPGA cho bản dựng lại

Mục tiêu: **xc7z020clg400-2**,160MHz, same-scope PS7/OCM-JTAG +AXI +MMCM/reset +host/core/data/root; chưa thêm DDR/DMA. Build output mới ở `study/build/flextransform_rebuild/<run_id>/`.

Ở gateM7 tạo project/scripts riêng theo hierarchy mới. Có thể đọc cấu hình IP/clock đã khóa của baseline làm reference, không chạy script cũ vào output đã pin. Nếu đổi hierarchy, mọi `get_cells/get_clocks` của constraint phải match đúng đối tượng; empty collection phải fail, không im lặng bỏ constraint.

Giữ period6.250ns, jitter0.300ns, uncertainty setup0.100ns/hold0.050ns khi so với baseline. Audit generated clocks thực tế, setup/hold/pulse-width, unconstrained endpoints, routing, DRC và CDC. Board deployment không thuộc bộ hồ sơ này; kết quả STA mới không tự trở thành bằng chứng đã chạy board.
