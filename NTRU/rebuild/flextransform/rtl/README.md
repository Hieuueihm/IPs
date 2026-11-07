# Nơi viết RTL mới

Thư mục này hiện chỉ có kế hoạch filelist, chưa có module synthesizable. Không dùng `filelist.planned` như một filelist đã build được.

Thứ tự phụ thuộc/ownership ở [spec05](../spec/05_rtl_blocks.md); cổng top/tile ở [spec04](../spec/04_interfaces.md). Viết bằng SystemVerilog, tên `ft_*`, build tách khỏi toàn bộ `hdl/` và RTL baseline.

Nếu phải đổi tên top để chạy harness cũ, tạo adapter trong verification hoặc copy harness và chỉ đổi model class/port/path cần thiết; không sửa accepted source. Adapter không tính vào PPA core trừ khi thật sự được tích hợp vào hệ thống đo.
