# Tile đang dùng

Source: [tile_thu.sv](tile_thu.sv), dùng [mul_ss.v](../mul_ss.v).
Hợp đồng: [spec 2.0, cấp tile](../../spec/FlexTransform/2.0/10_hop_dong_tile.md).
Đây là một khối tính; core còn phải cấp dữ liệu, root và địa chỉ đúng lúc.

## Cấu trúc

- Bốn bộ nhân 16×16 ghép thành một bộ nhân 32×32.
- Bộ cộng/trừ dùng chung cho CT, GS và FFT.
- NTT dùng số học Montgomery 32 bit với hai ô lưu q/qprime.
- FFT rộng tính lần lượt từng phần 32 bit, giữ đúng carry và rounding.

## Các chế độ

| req_mode | Phép tính |
|---:|---|
| 0 | Tích nguyên 32×32, chọn dấu cho mỗi toán hạng |
| 1 | Nhân fixed-point 32 bit theo cấu hình làm tròn |
| 2 | Một phép nhân Montgomery |
| 4 | Một butterfly NTT, chọn CT hoặc GS |
| 5 | Một butterfly FFT 32/64/128 bit, nhận nhiều nhịp cho số rộng |

Mã 3 không thuộc danh sách chế độ đang dùng. Cách đóng gói và các ràng buộc
nhận dữ liệu xem hợp đồng; không suy từ bảng này rằng mọi chế độ có cùng tốc độ.

## Các lựa chọn khi biên dịch

| Tham số | Ý nghĩa |
|---|---|
| TREN_MANG=1 | Bản đang chọn: dùng lại multiplier cho cả ba lượt Montgomery |
| TREN_MANG=3 | Bản đối chiếu: có phần nhân riêng cho reduction |
| LEAF_PD | Số thanh ghi pipeline trong bộ nhân nhỏ; mặc định 2 |
| IN_REG | Thêm thanh ghi đầu vào; core dùng 1 |
| EN_REG | Đăng ký tín hiệu enable và giữ kết quả khi dừng; mode 5 hiện dùng 0 |
| PHASE | Dời lịch nhận NTT; core đặt tile t ở pha t/6 |

Với TREN_MANG=1, tile nhận một phép NTT mới mỗi ba chu kỳ. Với LEAF_PD=2,
độ trễ NTT là 19 chu kỳ khi IN_REG=0, thêm một chu kỳ khi IN_REG=1.
Thay LEAF_PD phải kiểm lại điều kiện hợp lệ và lịch cấp lõi.

## Giao diện

`en` cho cả đường tính tiến một bước. Request chỉ nhận khi có đủ
`en && req_valid && req_ready`. Output không có rsp_ready riêng; muốn dừng
phải giữ đúng toàn bộ đường dữ liệu bằng en. Không coi port này là AXI-stream.
Mode và direction chỉ đổi khi tile rảnh; cấu hình q không ghi khi còn việc.

## Bằng chứng gần nhất

Lượt review ngày 01/11: 11.520 case FFT rộng có stall và 16.110 case NTT có
trộn modulus/stall đều PASS. Đây là các lượt kiểm chọn lọc. Core FFT32 vẫn có
lỗi chuyển tầng, dù tile chạy đúng trong các lượt đó.
[Chi tiết](../../docs/implementation_review_2026_11_01.md).

Script chạy: [sim/tile_thu/run.sh](../../sim/tile_thu/run.sh).
Các lần kiểm, biến thể, số đo FPGA và lỗi cố ý trước đây được giữ trong
[bản lưu](../../docs/plan_history/cleanup_2026_11_01/tile_MANIFEST.md).
Không lấy số đo của bản cũ làm số đo source hiện tại.
