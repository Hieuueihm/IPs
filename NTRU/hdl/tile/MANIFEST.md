# Tile của nhánh hdl/ — lịch sử

> **Baseline hiện hành từ 2026-11-04:** [a_cg_packed4_system160](../../experiments/BASELINE.md), source tại `experiments/a_cg_packed4_system160/rtl/`, contract [3.1](../../spec/FlexTransform/3.1/README.md). Các file trong `hdl/` và mô tả bên dưới thuộc nhánh trước; giữ nguyên RTL làm lịch sử, không ghép chúng vào build baseline.

Source: [tile_thu.sv](tile_thu.sv), dùng [mul_ss.v](../mul_ss.v).
Hợp đồng: [spec 2.0, cấp tile](../../spec/FlexTransform/2.0/10_hop_dong_tile.md).
Đây là một khối tính; core còn phải cấp dữ liệu, root và địa chỉ đúng lúc.

## Cấu trúc

- Bốn bộ nhân 16×16 ghép thành một bộ nhân 32×32.
- Bộ cộng/trừ dùng chung cho CT, GS và FFT; ở chế độ NTT hai hệ số nó cắt nhớ ở bit 16 thành hai làn.
- NTT dùng số học Montgomery 32 bit với hai ô lưu q/qprime.
- NTT hai hệ số mỗi từ chạy trên chính máy NTT: lá 0 và lá 1 mang hai làn 16 bit, lá 2 và 3 nhận 0.
- FFT rộng tính lần lượt từng phần 32 bit, giữ đúng carry và rounding.
- Dữ liệu đi kèm của NTT chờ trong bộ nhớ LUT của FFT; hai bộ trừ T của FFT dùng chung một chuỗi.

## Các chế độ

`req_mode` 2 bit từ 02/11/2026:

| req_mode | Phép tính |
|---:|---|
| 0 | Một butterfly NTT, chọn CT hoặc GS (chế độ 4 cũ) |
| 1 | Một butterfly FFT 32/64/128 bit, nhận nhiều nhịp cho số rộng (chế độ 5 cũ) |
| 2 | Hai butterfly NTT 16 bit trên hai từ, mỗi từ hai hệ số, q < 2¹⁵ (mới; chỉ TREN_MANG=1) |

Mã 3 dự trữ, tile không bao giờ nhận. Tích thô 32×32, tích FFT 32 bit và phép nhân
modulo đơn đã bỏ (lõi không dùng); phép nhân modulo đơn là NTT CT với x = 0.
`req_sign` còn 1 bit, `rsp_data` còn 64 bit. Cách đóng gói và các ràng buộc nhận
dữ liệu xem hợp đồng; không suy từ bảng này rằng mọi chế độ có cùng tốc độ.

## Các lựa chọn khi biên dịch

| Tham số | Ý nghĩa |
|---|---|
| TREN_MANG=1 | Bản đang chọn: dùng lại multiplier cho cả ba lượt Montgomery |
| TREN_MANG=3 | Bản đối chiếu: có phần nhân riêng cho reduction |
| LEAF_PD | Số thanh ghi pipeline trong bộ nhân nhỏ; mặc định 2 |
| IN_REG | Thêm thanh ghi đầu vào; core dùng 1 |
| EN_REG | Đăng ký tín hiệu enable và giữ kết quả khi dừng; chế độ FFT hiện dùng 0 |
| PHASE | Dời lịch nhận NTT; core đặt tile t ở pha t/6 |

Với TREN_MANG=1, tile nhận một phép NTT (hoặc một cặp NTT 16 bit) mới mỗi ba
chu kỳ. Với LEAF_PD=2, độ trễ NTT và NTT hai hệ số là 19 chu kỳ khi IN_REG=0,
thêm một chu kỳ khi IN_REG=1.
Thay LEAF_PD phải kiểm lại điều kiện hợp lệ và lịch cấp lõi.

## Giao diện

`en` cho cả đường tính tiến một bước. Request chỉ nhận khi có đủ
`en && req_valid && req_ready`. Output không có rsp_ready riêng; muốn dừng
phải giữ đúng toàn bộ đường dữ liệu bằng en. Không coi port này là AXI-stream.
Mode và direction chỉ đổi khi tile rảnh; cấu hình q không ghi khi còn việc.

## Bằng chứng gần nhất

02/11/2026, source sau khi rút gọn chế độ (`sh study/build/run_tile_regress_wide.sh`, năm cấu hình, hai biến thể):
mặc định, `IN_REG`, `LEAF_PD = 4`, `PHASE = 2` mỗi cấu hình 62 lần chạy đạt, 28/28 lỗi cài vào bị bắt; `EN_REG` 27 lần
chạy, 22/22 (không có FFT). RTL `69c03f65acec27d9`, testbench `c2ba81e12dc7f48b`. Độ trễ khi gửi liên tục: NTT 19 (biến
thể rút gọn riêng 15), NTT hai hệ số 19, FFT 15..23 / 23..49 / 44..173; `IN_REG` cộng 1, `LEAF_PD = 4` như bảng hợp đồng.
Tốc độ: NTT và NTT hai hệ số 0,334 request mỗi chu kỳ, FFT 0,67 / 0,335 / 0,179.

Lõi với tile này (`sh sim/core_ntt/run.sh`): NTT 48/48, FFT 54/54, prime nạp 100/100; chu kỳ N1024 không đổi (NTT 984 / 985,
FFT 644 / 2 031 / 7 510).

## Diện tích

Chỉ tổng hợp, Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, vỏ đo `tile_thu_top`, TREN_MANG=1, IN_REG=1, clock 5,0 ns
(`sh fpga/zcu106/tile_area.sh <tên> <file RTL>`; clock đặt sau tổng hợp nên chỉ đổi WNS):

| Source | LUT | FF | LUTRAM | DSP | WNS |
|---|---:|---:|---:|---:|---:|
| Chỉ NTT và tích thô (commit 342b06a) | 797 | 1 036 | 88 | 4 | |
| + FFT 32 bit (commit 267dae9) | 1 335 | 1 317 | 131 | 4 | +2,44 ns |
| + FFT 64/128 bit, máy chung (commit 256e425) | 2 045 | 1 547 | 299 | 4 | +2,32 ns |
| + NTT hai hệ số, bốn làn (không chọn) | 2 964 | 2 183 | 410 | 4 | +2,20 ns |
| + NTT hai hệ số, hai làn | 2 099 | 1 564 | 301 | 4 | +1,93 ns |
| Bỏ chế độ 0, 1, 2 | 1 897 | 1 550 | 292 | 4 | +2,01 ns |
| **Hiện tại:** dữ liệu NTT chung bộ nhớ FFT, hai bộ trừ T chung một chuỗi, `req_mode` 2 bit | **1 759** | 1 521 | 251 | 4 | +2,01 ns |

Đã thử và bỏ: dùng một cặp chuỗi cộng cho bộ cộng/trừ modulo qua hai chu kỳ (290 LUT + 130 FF so với 196 LUT của bốn
chuỗi, đo riêng, [study/results/addsub_variants/](../../study/results/addsub_variants/addsub_variants.sv)): bộ chọn đầu vào không gộp được
vào LUT của bộ cộng.

Script chạy: [sim/tile_thu/run.sh](../../sim/tile_thu/run.sh).
Các lần kiểm, biến thể, số đo FPGA và lỗi cố ý trước đây được giữ trong
[bản lưu](../../docs/plan_history/cleanup_2026_11_01/tile_MANIFEST.md).
Không lấy số đo của bản cũ làm số đo source hiện tại.
