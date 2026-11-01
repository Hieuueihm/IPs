> Bản lưu trước khi dọn tài liệu ngày 01/11/2026.

# Manifest triển khai — khối tile thử, RTL nghiệm thu

Theo mục 9 của [hợp đồng cấp tile](../../../spec/FlexTransform/2.0/10_hop_dong_tile.md). RTL:
[tile_thu.sv](../../../hdl/tile/tile_thu.sv), dùng [hdl/mul_ss.v](../../../hdl/mul_ss.v) cho bộ nhân 16×16. Viết ngày 31/10/2026 bởi trợ lý, cùng tác
giả với testbench (xem [11 mục 3](../../../spec/FlexTransform/2.0/11_kiem_thu_tile.md)).

**Một lane 32 bit** (31/10/2026, lần 6 của hợp đồng): mọi q lẻ 3 ≤ q < 2³¹, kể cả 3329 và 12289, dùng cùng bộ
Montgomery R = 2³². Không còn `cfg_lane32`; `req_slot` chọn ô modulus cho mọi request NTT. Bản hai lane trước đó:
[docs/plan_history/before_one_lane_2026-10-31/hdl/tile_thu.sv](../before_one_lane_2026-10-31/hdl/tile_thu.sv)
(và `study/build/tile_acc_v6_e1d97d2a.sv`).

## Biến thể

**Thiết kế v1 dùng `TREN_MANG = 1`** (rút gọn trên mảng), cũng là giá trị mặc định: người dùng chọn 01/11/2026, sau khi
giả thuyết 2 đạt ở cấp tile trên RTL một lane. Từ 31/10 đến 01/11/2026 v1 là `TREN_MANG = 3` (bản trước:
[docs/plan_history/before_on_array_v1_2026-11-01/](../before_on_array_v1_2026-11-01)).

Tham số khác:
- `LEAF_PD` (mặc định 2): số thanh ghi tích của mỗi bộ nhân sau thanh ghi đầu vào. Mọi độ trễ engine suy từ tham số này;
  đã chạy đủ kiểm thử với `LEAF_PD = 4`. Biến thể 1 cần (LEAF_PD + 3) không chia hết cho 3, nếu không sẽ báo lỗi lúc
  elaboration.
- `IN_REG` (mặc định 0): 1 thêm một tầng thanh ghi cho request đã nhận, trước mọi logic đường dữ liệu; độ trễ mọi chế độ
  tăng 1. Dùng trong lõi, khi request đến qua mạng bank → tile. Tốn thêm khoảng 100 FF.
- `EN_REG` (mặc định 0): 1 cho đường dữ liệu dùng bản sao `en` qua một thanh ghi, kèm một ô đệm ở cổng ra; mỗi đợt dừng
  mất thêm một chu kỳ. Tốn khoảng 45 LUT và 75 FF mỗi tile. Đo 16 tile cho thấy không cần khi `en` của lõi lấy từ một
  thanh ghi (ghi chú bản nháp mục 14).
- `PHASE` (0..2, mặc định 0; chỉ có tác dụng với `TREN_MANG = 1`): giá trị reset của bộ đếm khe chu kỳ 3. Trong lõi tile t
  dùng t / 6, nên mỗi chu kỳ chỉ một nhóm 6, 6 hoặc 4 tile nhận butterfly và lõi chỉ cần 4 bank gói root
  ([model/staggered_net.py](../../../model/staggered_net.py)). Cổng không đổi; chỉ chu kỳ nhận đầu tiên sau reset dời đi.
  Đây là lịch phát, phần người triển khai tự chọn (hợp đồng mục 9).
- Khi mô phỏng có thể đặt mặc định bằng `define`: `TL_LEAF_PD`, `TL_IN_REG`, `TL_EN_REG`, `TL_PHASE`.

| `TREN_MANG` | Biến thể | Rút gọn (mọi q) |
|---:|---|---|
| 1 | **Thiết kế v1** (từ 01/11/2026; bác bỏ ở lần 4 khi còn hai lane, đạt khi một lane) | Bốn bộ nhân ghép thành 32×32, ba lượt cách nhau 5 chu kỳ, một phép nhân modulo mỗi 3 chu kỳ |
| 3 | Bản đối chứng của giả thuyết 2 (là v1 từ 31/10 đến 01/11/2026) | Bộ nhân ghép tính T; m và m·q bằng phép nhân hành vi (Vivado suy ra 7 DSP) |

Giá trị khác của `TREN_MANG` gây lỗi lúc elaboration.

## Chế độ 5: butterfly FFT 32 bit (01/11/2026)

Hai nhịp request mỗi butterfly (hợp đồng mục 4.7). Trong tile: bộ cộng/trừ modulo với q = 0 (cờ `m5` là thanh ghi riêng để
không nằm trên đường găng), tích p0, p1 ở tầng toán hạng của mỗi nhịp và p2 một chu kỳ sau nhịp 2 (thanh ghi tổng `sa5`,
`sw5`), làm tròn bằng bộ của chế độ 1, `t5` = p0 − p1 rồi p2 − (p0 + p1), dữ liệu phụ trên một đường trễ ngắn riêng
(`d_sd5`, độ sâu FUSE + 2) để cả hai đường trễ vẫn là shift-register LUT, div2e trên hai đầu ra của nhánh ngược. Bộ đếm
pha `fph` và cờ `got_r` chỉ tiến ở chu kỳ có cả `en` và `ce`. Chỉ dùng với `EN_REG` = 0.

## Chế độ 5 ở 64 / 128 bit (01/11/2026)

Hợp đồng mục 4.8. `q0[5:4]` chọn độ rộng. Trong tile:
- **Bộ nhớ phần** (LUTRAM, 4 butterfly × 2L nhịp): `wma` (A hoặc A + B, tag, cờ chia), `wmx` (o), `wmw` (root), `wmsx`,
  `wmsw` (o.re + o.im, wr + wi theo phần). Viết ở tầng toán hạng của mỗi nhịp; hai tổng dùng chính hai bộ cộng của chế độ 5
  32 bit, thêm cờ nhớ.
- **Bộ tuần tự tích** (`mbz`, `mpr`, `mst`, bảng `wtab`): mỗi butterfly p0, p1, p2 liền nhau, mỗi tích theo cột; phần trên
  cùng có dấu (cờ dấu của lá).
- **Bộ cộng dồn tích** `wacc` 68 bit: bắt đầu bằng số làm tròn 2³¹ (64 bit) hoặc 2⁶³ (128 bit), cột mới dịch 32 bit;
  cột phát ra cho phần thấp 32 bit vào `wpl`.
- **T theo phần** (`wps`, ba bộ cộng có nhớ: p0 − p1, p0 + p1, p2 − (p0 + p1)) ghi vào `t5` của chế độ 5.
- **Đầu ra:** A ± T (xuôi) qua bộ cộng/trừ modulo với cờ nhớ `ci`, `bi`; A + B và T (ngược) qua hai bộ cộng làm tròn có
  nhớ; phần trễ một phần (`wy0l`, `wy0p`, …) để bộ dịch (`fz0`, `fz1`, dịch 64 → 32 bit) lấy bit của phần kế. Bộ dịch này
  thay bộ dịch số học của div2e 32 bit (chế độ 5 32 bit dùng nó với phần kế là dấu).
- Độ trễ của một butterfly không phải chờ: xem hợp đồng mục 4.8; đo bằng `sim/tile_thu/tb_wide_timing.sv`.

## Độ trễ (chu kỳ có `en = 1`, từ lúc nhận request đến lúc `rsp_valid`)

| Chế độ | Biến thể 1 | Biến thể 3 | Biến thể 3, `IN_REG = 1` |
|---|---:|---:|---:|
| 0, 1 | 6 | 6 | 7 |
| 2, 4 (mọi q) | 19 | 15 | 16 |
| 5 (mỗi nhịp) | 9 | 9 | 10 |
| 5, 64 / 128 bit, nhịp j | hợp đồng mục 4.8 | như biến thể 1 | + 1 |

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
| Biến thể 1 (v1), có chế độ 5 | 1 299 | 1 213 | 4 | 0 / 0 | −0,009 ns |
| Biến thể 1 (v1), một lane | 781 | 937 | 4 | 0 / 0 | +0,371 ns |
| Biến thể 3, một lane | 777 | 1 004 | 11 | 0 / 0 | +0,261 ns |
| Biến thể 3, hai lane (trước) | 913 | 1 155 | 11 | 0 / 0 | +0,234 ns |
| Biến thể 1, hai lane (trước) | 1 046 | 1 063 | 4 | 0 / 0 | +0,187 ns |

Báo cáo ở `study/build/tile_mot_lan_<biến thể>/`. Thêm `PHASE` (hash `4f7b721872c531da`): 5 cấu hình (mặc định, `IN_REG`, `EN_REG`,
`LEAF_PD = 4`, `PHASE = 2`) × 50 lần chạy đạt, 16/16 lỗi bị bắt; tile lệch pha (`PHASE` = t / 6) và 4 bank gói root: mạng 5 216 LUT / 6 001 FF, WNS +0,487 ns (root 1 536 LUT, trước 2 560); 16 tile 12 495 LUT / 14 872 FF / 64 DSP, WNS +0,063 ns; phần tính + mạng 17 711 LUT, 64 DSP (báo cáo `study/build/ntt_bank_net_s/`,
`study/build/tile_array16_en0_v1/`; 16 tile cùng pha trước đó ở `tile_array16_en0_v1_cung_pha/`). Sau khi đổi mặc định sang `TREN_MANG = 1` (hash `eaf87bef1b1c0820`, chỉ đổi giá trị mặc định và chú thích): cấu hình mặc định chạy lại 50 lần đạt, 16/16 lỗi bị bắt. 16 tile v1 trên mảng sau một thanh ghi `en`: 12 494 LUT / 14 872 FF / 64 DSP / 0 BRAM, WNS +0,073 ns; phần tính + mạng 18 733 LUT, 64 DSP (báo cáo `study/build/tile_array16_en0_v1/`). RTL hash `cc9b52093081f7c7`: 4 cấu hình × 50 lần chạy đạt, 16/16 lỗi bị bắt ([11](../../../spec/FlexTransform/2.0/11_kiem_thu_tile.md) mục 3, lần chạy 6). 16 tile v1 sau một thanh ghi `en`: 12 207 LUT / 15 888 FF / 176 DSP, WNS +0,112 ns. Verilator `-Wall`: ngoài các bit cố ý không dùng, còn `lp` (tích từng bộ nhân) không dùng ngoài khối bộ nhân từ khi bỏ lane 16 bit. Các tối ưu vi mô và số đo từng bước: ghi chú bản nháp mục 20, 21.
