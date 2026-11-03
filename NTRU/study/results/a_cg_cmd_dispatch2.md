# Kết quả thêm pipeline lệnh và trả dữ liệu đọc

**Timing thanh ghi nội bộ tại 200 MHz: ĐẠT.**

| Bản P&R | LUT | FF | Setup WNS | Hold |
|---|---:|---:|---:|---:|
| Baseline frontreserve | 37,414 | 26,966 | +0.162 ns | +0.010 ns |
| Dispatch2 | 37,389 | 27,437 | +0.304 ns | +0.010 ns |

DSP/RAMB18: 64/48, gồm 16 root và 32 bank dữ liệu.
Timing toàn biên OOC: setup +0.304 ns, hold -1.591 ns.

## Thay đổi RTL

Thêm một tầng chuyển lệnh: dữ liệu, địa chỉ và token của mọi loại lệnh cùng đi qua thanh ghi thứ hai.
Giữ chỗ cho lệnh đang nằm trong cả hai tầng, ngăn cấu hình hoặc start vượt qua lệnh trước.
Thêm một tầng cho cặp read_data/read_rsp_valid, xóa token khi reset hoặc reset trễ đang hoạt động.
Busy bao phủ cả hai tầng start. RTL số học trong tile và bộ nhân giữ nguyên từng byte.

## Độ trễ và kiểm tra

Số chu kỳ kernel giữ nguyên. So với baseline frontreserve: mỗi lệnh chính giao chậm thêm một clock,
mỗi kết quả đọc chậm thêm một clock; khoảng cách tối thiểu giữa lệnh chính từ 2 lên 3 clock.
Root/descriptor thêm một clock trễ nhưng vẫn nhận một từ mỗi clock.
Tổng chi phí trên mỗi transform tăng 2*ceil(words/4)+3 clock, kiểm tra trên toàn bộ 1.026 ca.
Qua 1.026 vector, 38 ca bốn trạng thái, 12 nhóm reset, 74 lần gọi transform từ C và 4 xác minh chữ ký.
14 artifact ứng dụng giống bản C tham chiếu; 2 đầu vào sai bị từ chối. Packed16 được giữ.
Netlist xác nhận không có đường bỏ qua tầng chuyển lệnh hoặc tầng trả dữ liệu đọc.

## Giới hạn I/O

Không được hiểu thêm pipeline là đã sửa lỗi hold ngay tại chân OOC. Đường desc_stage[2] tới
thanh ghi đầu tiên của baseline có trễ dữ liệu được mô hình là 0 ns vì cổng chưa được route.
Tầng pipeline mới nằm sau thanh ghi đó. Cần tích hợp nguồn phát dữ liệu và clock thực tế để
kiểm tra lại giao tiếp; không nới ràng buộc và không thêm ngoại lệ timing trong thử nghiệm này.
RTL chính và baseline đã chọn chưa đổi; chưa chạy board hoặc tạo bitstream.

## Đường setup nội bộ chậm nhất

```json
[
  {
    "slack_ns": 0.304,
    "source": "u_exec/engine[8].u_tile/wbi_reg[2]/C",
    "destination": "u_exec/engine[8].u_tile/rd_reg[8]/D",
    "delay": "4.490ns  (logic 1.666ns (37.105%)  route 2.824ns (62.895%))",
    "levels": "16  (CARRY8=8 LUT3=1 LUT4=2 LUT6=5)"
  },
  {
    "slack_ns": 0.332,
    "source": "u_exec/engine[15].u_tile/wbi_reg[0]/C",
    "destination": "u_exec/engine[15].u_tile/s1_reg[1]/D",
    "delay": "4.481ns  (logic 1.684ns (37.581%)  route 2.797ns (62.419%))",
    "levels": "15  (CARRY8=7 LUT4=3 LUT5=1 LUT6=4)"
  },
  {
    "slack_ns": 0.336,
    "source": "u_exec/engine[15].u_tile/wbi_reg[0]/C",
    "destination": "u_exec/engine[15].u_tile/rd_reg[27]/D",
    "delay": "4.485ns  (logic 1.680ns (37.458%)  route 2.805ns (62.542%))",
    "levels": "15  (CARRY8=7 LUT4=3 LUT5=1 LUT6=4)"
  }
]
```
