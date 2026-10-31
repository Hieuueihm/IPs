# Sửa slew của bản banked bằng tăng drive cục bộ

Ngày 26/10/2026. Đối chứng giữ nguyên RTL và netlist gốc; đây là bước sizing sau mapping trong Nangate45.

## Kết quả

| Chỉ tiêu | Banked gốc | Sau sửa |
|---|---:|---:|
| Pin vi phạm max-transition | 110 | 0 |
| Worst transition slack (ns) | -0.0079 | Không vi phạm |
| Arrival register-to-register (ns) | 5.1370 | 5.1370 |
| Worst setup slack ở clock 10ns (ns) | 4.7197 | 4.7197 |
| Tổng cell area (mm²) | 0.450293844 | 0.450304484 |
| FF cell | 17,421 | 17,421 |

Tăng **10.640 µm²**, tương đương **0.00236%** diện tích banked gốc.

## Đã sửa gì và kiểm thế nào?

110 pin gốc thuộc 10 net do NOR4_X1 điều khiển; báo cáo tính cả pin driver và các sink.
Có 10 lần đổi cell, qua 1 vòng sizing/STA:

- 10 cổng `NOR4_X1` → `NOR4_X2`.

Không thêm tầng, không đổi phép toán, precision, bit rounding, FIFO hoặc giao thức stall.
Mỗi cặp cell được đối chiếu đầy đủ tên/hướng pin và hàm Boolean trong Liberty. Tất cả kết nối pin giữ nguyên.
Đảo lại đúng các token tên loại cell phải khôi phục toàn bộ netlist gốc từng byte. Đây là chứng cứ tương đương
logic zero-delay của phép sizing; không cần diễn giải kết quả số học khác đi để vượt kiểm tra.

Diện tích được kiểm tra độc lập bằng đếm mọi instance trong netlist đã sửa rồi cộng area từng cell từ Liberty.
Số cell và FF khớp baseline sau các thay thế đã ghi. Không thay giới hạn slew hoặc nới clock/IO constraint.

## Phạm vi kết luận

Các kiểm tra setup và max-transition đạt trong mô hình **trước layout**, Nangate45 typical 1,1V/25°C,
clock10ns, uncertainty0,1ns, IO delay0,2ns, output load5fF; giống bản gốc. Chưa xác nhận hold closure,
placement, CTS, RC dây, corner signoff, SRAM hoặc FPGA. Kết quả này xử lý vấn đề sizing đã thấy trong
flow tham chiếu; không phải một đóng góp kiến trúc mới hoặc chứng minh Fmax của chip.

RTL vẫn độc lập công nghệ. Với thư viện khác, cần thực hiện sizing/buffering tương ứng sau mapping.
Các phần còn thiếu của full core trong [báo cáo trước](stream_core_results.md) vẫn giữ nguyên phạm vi.

## Dữ liệu và chạy lại

- [JSON sizing, equivalence và từng vòng STA](../study/results/stream_slew_repair.json).
- [Audit toàn bộ số cell và diện tích](../study/results/stream_slew_repair_audit.json).
- [Script sửa slew](../scripts/repair_stream_slew.py), [script audit/báo cáo](../scripts/report_slew_repair.py).

Trong WSL, đặt LD_LIBRARY_PATH và TCL_LIBRARY như [flow tham chiếu](stream_core_results.md#6-chạy-lại), rồi chạy:

~~~sh
python3 scripts/repair_stream_slew.py
python3 scripts/report_slew_repair.py
~~~

Script giữ nguyên các artifact baseline, xuất netlist và log riêng vào `study/build/stream_slew_repair/`.
