# Manifest triển khai — khối tile thử, RTL nghiệm thu

Theo mục 9 của [hợp đồng cấp tile](../../spec/FlexTransform/2.0/10_hop_dong_tile.md). RTL:
[tile_thu.sv](tile_thu.sv), dùng [hdl/mul_ss.v](../mul_ss.v) cho bộ nhân 16×16. Viết ngày 31/10/2026 bởi trợ lý, cùng tác
giả với testbench (xem [11 mục 3](../../spec/FlexTransform/2.0/11_kiem_thu_tile.md)).

**Một lane 32 bit** (31/10/2026, lần 6 của hợp đồng): mọi q lẻ 3 ≤ q < 2³¹, kể cả 3329 và 12289, dùng cùng bộ
Montgomery R = 2³². Không còn `cfg_lane32`; `req_slot` chọn ô modulus cho mọi request NTT. Bản hai lane trước đó:
[docs/plan_history/before_one_lane_2026-10-31/hdl/tile_thu.sv](../../docs/plan_history/before_one_lane_2026-10-31/hdl/tile_thu.sv)
(và `study/build/tile_acc_v6_e1d97d2a.sv`).

## Biến thể

**Thiết kế v1 dùng `TREN_MANG = 3`**, cũng là giá trị mặc định (người dùng xác nhận 31/10/2026, sau khi giả thuyết 2 bị
bác bỏ ở cấp tile).

Tham số khác:
- `LEAF_PD` (mặc định 2): số thanh ghi tích của mỗi bộ nhân sau thanh ghi đầu vào. Mọi độ trễ engine suy từ tham số này;
  đã chạy đủ kiểm thử với `LEAF_PD = 4`. Biến thể 1 cần (LEAF_PD + 3) không chia hết cho 3, nếu không sẽ báo lỗi lúc
  elaboration.
- `IN_REG` (mặc định 0): 1 thêm một tầng thanh ghi cho request đã nhận, trước mọi logic đường dữ liệu; độ trễ mọi chế độ
  tăng 1. Dùng trong lõi, khi request đến qua mạng bank → tile. Tốn thêm khoảng 100 FF.
- `EN_REG` (mặc định 0): 1 cho đường dữ liệu dùng bản sao `en` qua một thanh ghi, kèm một ô đệm ở cổng ra; mỗi đợt dừng
  mất thêm một chu kỳ. Tốn khoảng 45 LUT và 75 FF mỗi tile. Đo 16 tile cho thấy không cần khi `en` của lõi lấy từ một
  thanh ghi (ghi chú bản nháp mục 14).
- Khi mô phỏng có thể đặt mặc định bằng `define`: `TL_LEAF_PD`, `TL_IN_REG`, `TL_EN_REG`.

| `TREN_MANG` | Biến thể | Rút gọn (mọi q) |
|---:|---|---|
| 1 | Trên mảng (bác bỏ ở lần 4 khi còn hai lane; đo lại ở bảng dưới) | Bốn bộ nhân ghép thành 32×32, ba lượt cách nhau 5 chu kỳ, một phép nhân modulo mỗi 3 chu kỳ |
| 3 | **Thiết kế v1** (trước đó là đối chứng của giả thuyết 2) | Bộ nhân ghép tính T; m và m·q bằng phép nhân hành vi (Vivado suy ra 7 DSP) |

Giá trị khác của `TREN_MANG` gây lỗi lúc elaboration.

## Độ trễ (chu kỳ có `en = 1`, từ lúc nhận request đến lúc `rsp_valid`)

| Chế độ | Biến thể 1 | Biến thể 3 | Biến thể 3, `IN_REG = 1` |
|---|---:|---:|---:|
| 0, 1 | 6 | 6 | 7 |
| 2, 4 (mọi q) | 19 | 15 | 16 |

Với `LEAF_PD` khác 2: chế độ 0, 1 là LEAF_PD + 4; NTT riêng LEAF_PD + 13, trên mảng 3·LEAF_PD + 13 (cộng thêm 1 nếu
`IN_REG = 1`). (Khi còn lane 16 bit, NTT q < 2¹⁶ trễ 13.)

Độ trễ không phụ thuộc chiều CT/GS hay q. Tốc độ NTT: 1/3 request/chu kỳ (biến thể 1), 1 (biến thể 3).

## Công cụ

- Mô phỏng: Icarus Verilog 14.0.
- FPGA: Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, `fpga/zcu106/tile_thu.tcl` với `TILE_RTL=hdl/tile/tile_thu.sv`.

## Khác với gợi ý của hợp đồng

- **Một bộ cộng/trừ modulo dùng chung cho CT và GS.** Chiều cố định trong một chuỗi request (hợp đồng 4.2), nên bộ này
  đứng trước bộ rút gọn khi GS và sau khi CT. Độ trễ hai chiều bằng nhau.
- Kết quả bộ nhân của lượt trước đi thẳng vào thanh ghi đầu vào của lượt sau, không qua thanh ghi chờ.
- Hai tham số không có trong hợp đồng: `LEAF_PD`, `IN_REG` (xem trên). Mặc định cho đúng độ trễ đã công bố ở bảng trên.
- Kết quả cuối ghi thẳng vào thanh ghi đầu ra, không có tầng thanh ghi butterfly riêng.
- Tên tín hiệu giữ như mục 2 của hợp đồng. Tên module con có tiền tố `tl_`, để không trùng với bản nháp trong
  `hdl/tile_thu/`; không biên dịch hai file cùng lúc.
- Các `define` cài lỗi của nhóm C: `FAULT_NO_NZ`, `FAULT_NZ_ONE`, `FAULT_NO_SUBQ`, `FAULT_HALVE_ALWAYS`, `FAULT_SWAP_XY`,
  `FAULT_IGNORE_SLOT`.
- Hai ô modulus (hợp đồng mục 3): bit `req_slot` đi theo request qua pipeline; mỗi tầng cần q hoặc q′ chọn theo bit của
  phép đang ở tầng đó, với mọi q.

## Số đo (Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, 3,0 ns, sau route)

| | LUT | FF | DSP | BRAM / URAM | WNS |
|---|---:|---:|---:|---:|---:|
| Biến thể 3 (v1), một lane | 777 | 1 004 | 11 | 0 / 0 | +0,261 ns |
| Biến thể 1, một lane | 781 | 937 | 4 | 0 / 0 | +0,371 ns |
| Biến thể 3, hai lane (trước) | 913 | 1 155 | 11 | 0 / 0 | +0,234 ns |
| Biến thể 1, hai lane (trước) | 1 046 | 1 063 | 4 | 0 / 0 | +0,187 ns |

Báo cáo ở `study/build/tile_mot_lan_<biến thể>/`. RTL hash `cc9b52093081f7c7`: 4 cấu hình × 50 lần chạy đạt, 16/16 lỗi bị bắt ([11](../../spec/FlexTransform/2.0/11_kiem_thu_tile.md) mục 3, lần chạy 6). 16 tile v1 sau một thanh ghi `en`: 12 207 LUT / 15 888 FF / 176 DSP, WNS +0,112 ns. Verilator `-Wall`: ngoài các bit cố ý không dùng, còn `lp` (tích từng bộ nhân) không dùng ngoài khối bộ nhân từ khi bỏ lane 16 bit. Các tối ưu vi mô và số đo từng bước: ghi chú bản nháp mục 20, 21.
