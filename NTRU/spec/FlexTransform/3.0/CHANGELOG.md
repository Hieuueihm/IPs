# 3.0 — contract của baseline được nhận, 2026-11-04

Implementation `a_cg_z020_system160`, STA toàn hệ thống 160 MHz trên XC7Z020-CLG400-2. [Baseline](../../../experiments/BASELINE.md).

Thêm [đặc tả triển khai RTL](05_trien_khai_rtl.md): cấu trúc cổng, mux/register/RAM, pipeline/latency, port và quan hệ giữa controller/tile/AXI. Bổ sung mô tả, không đổi RTL hoặc numerical contract. Latency NTT CT/GS được đối chiếu riêng trên source baseline, theo định nghĩa giá trị sau cạnh clock.

So với spec 2.0: format native 2 bit và native flag riêng; một context/slot 0 ở core; descriptor/root RAM theo tile; bộ nhớ 32 bank 32 bit/CG/ping-pong; packed16 và batch đồng cấu hình; host AXI-Lite hiện hành; IFFT scale ở đường đọc host. Không tương thích giao diện format 3 bit, nhiều khe prime, địa chỉ A/B/C và map memory của bản cũ.

Đây là version mới để không sửa ngầm contract 2.0. Các yêu cầu mở rộng của 2.0 không được coi là hoàn thành hoặc bị xóa khỏi lịch sử. Nguồn RTL không đổi trong lần nhận baseline; thay đổi ở danh mục nguồn, trạng thái, tài liệu và điểm vào build/kiểm baseline.

Thay đổi numerical semantics/packing/interface cần version contract mới, vector và kiểm chứng tương ứng. Đổi pipeline/timing trong contract phải có source/evidence revision mới. Đổi baseline phải được người dùng nhận; không tự sửa hash cho một source đã thay.
