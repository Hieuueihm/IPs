# 11 — Kiểm thử cấp tile

> **Thay đổi 31/10/2026, lần 4:** kết quả nhóm D bác bỏ giả thuyết 2 ở cấp tile; thiết kế v1 nay là biến thể **rút gọn
> riêng lane 32 bit** (tham số 3). Các bảng kết quả bên dưới giữ nguyên số đo; chỉ đổi tên cột.

> **Thay đổi 31/10/2026, lần 2:** theo hợp đồng tile một làn ([10](10_hop_dong_tile.md), đầu tài liệu). Vector NTT,
> cột file, chuỗi đổi chế độ, lỗi cài vào và kiểm tốc độ được làm lại. Bản trước:
> [trước khi chuyển sang một làn](../../../docs/plan_history/spec2_before_single_lane_2026-10-31/11_kiem_thu_tile.md).
>
> **Thay đổi 31/10/2026, lần 3:** thiết kế v1 rút gọn mọi modulus trên mảng (10, đầu tài liệu). Hai biến thể kiểm là
> **trên mảng** (v1) và **rút gọn riêng lane 32 bit** (đối chứng); `ntt16_q_khac.txt` nay áp dụng cho cả hai. Bản trước:
> [trước khi chuyển sang mọi modulus trên mảng](../../../docs/plan_history/spec2_before_all_on_array_2026-10-31/11_kiem_thu_tile.md).

Các case dưới đây kiểm **khối tile thử** theo [hợp đồng cấp tile](10_hop_dong_tile.md). Mỗi case phải chạy trên **cả
hai biến thể** rút gọn, trừ chỗ ghi "không áp dụng". Trạng thái của mỗi case là một trong: chưa chạy, đạt, không đạt,
không áp dụng. "Chưa chạy" không bao giờ được tính là đạt.

## 1. Vector chuẩn

Sinh bằng [scripts/build_spec2_tile_vectors.py](../../../scripts/build_spec2_tile_vectors.py) (seed cố định
20261030). Giá trị mong đợi chỉ tính bằng phép nhân số nguyên và phép toán modulo thuần túy, **không** dùng mô hình
tích 16×16, vì đó chính là thứ cần kiểm. Hash SHA-256 của từng file ở [assets/tile/manifest.json](assets/tile/manifest.json).

| File | Số ca | Nội dung | Biến thể |
|---|---:|---|---|
| `raw32.txt` | 2 320 | Chế độ 0, bốn tổ hợp dấu, giá trị biên (0, 1, −1, −2³¹, 2³¹ − 1, 2³² − 1, …) và ngẫu nhiên | Cả hai |
| `fft32.txt` | 1 842 | Chế độ 1, nửa-lên và cắt bớt, 264 ca đúng điểm giữa (16 bit thấp của tích = 0x8000) và lân cận ±1 | Cả hai |
| `ntt16_pqc.txt` | 1 428 | Chế độ 2 và 4, lane 16 bit, q = 3329 và 12289 | Cả hai |
| `ntt16_q_khac.txt` | 1 998 | Chế độ 2 và 4, lane 16 bit, q = 3, 7681, 65521 | Cả hai (không áp dụng cho điểm đo có bộ rút gọn hằng) |
| `ntt32.txt` | 5 486 | Chế độ 2 và 4, lane 32 bit, q = 8380417; prime đầu, giữa và cuối của NTRUGen; 2³¹ − 1; 12289 đặt trong lane 32 bit | Cả hai |

Với mỗi q, vector NTT phủ đủ bốn tổ hợp: chế độ 2; chế độ 4 CT; chế độ 4 GS; chế độ 4 GS có chia đôi.

Mỗi giá trị đặc biệt (0, 1, 2, q − 1, q − 2, quanh q/2, các lũy thừa của 2) lần lượt nằm ở từng ô đang dùng (d0, d1,
r0), ô root đi kèm một giá trị đặc biệt khác. Mỗi request có đúng một phép nhân modulo. Các trường hợp góc:

| Trường hợp | Lane 16 bit | Lane 32 bit |
|---|---:|---:|
| Phép nhân modulo đã phủ | 1 428 | 5 486 |
| T là bội của R nhưng khác 0 (T_thấp = 0, bit `[T_thấp ≠ 0]` phải bằng 0) | 58 | 409 |
| T = 0 | 63 | 336 |

**Cách đọc file.** Mỗi dòng một ca, các trường hex cách nhau bằng dấu cách, dòng bắt đầu bằng `#` là chú thích. File
chỉ có ký tự ASCII, đọc được bằng `$fscanf(fd, "%h ...")`. Cột của file NTT là:

```text
q qinv lane32 mode dir halve d0 d1 r0 z0 z1
```

Dòng được nhóm theo q rồi theo chế độ. Khi q, lane, chế độ, hướng hoặc cờ chia đôi đổi, testbench phải chờ
`idle = 1`, ghi thanh ghi hằng số (q, qinv, lane32, halve), rồi gửi tiếp. Nếu cột halve = 0 thì `cfg_halve = 0`.

Bộ vector này **thay cho** 16 102 vector của cụm NTT cũ khi kiểm khối tile thử, vì cụm cũ chỉ có lane 16 bit và cách
đóng gói khác. Nó cũng thay bộ vector nhịp hai tầng của hợp đồng tile trước (bản sao ở thư mục lịch sử).

**Kiểm chéo đã chạy:** [scripts/check_spec2_tile_vectors.py](../../../scripts/check_spec2_tile_vectors.py) chạy lại
toàn bộ 13 074 ca qua mô hình dạng phần cứng và cho khớp hết:
- tích cộng từ các tích con 16×16, nửa cao mang dấu;
- `P[47:16] + P[15]` cho FFT 32 bit;
- Montgomery ba lượt với `[T_thấp ≠ 0]`;
- chia đôi bằng cộng có điều kiện rồi dịch.

1 229 ca nhân modulo 32 bit khớp thêm mô hình đã đối chiếu với C của NTRUGen.

## 2. Các case kiểm thử

### Nhóm A — đúng số học

| Case | Cách làm | Đạt khi |
|---|---|---|
| **Tích thô 32×32** | Chạy toàn bộ `raw32.txt` | Mọi `rsp_data[64:0]` bằng cột product65 |
| **Tích FFT 32 bit** | Chạy toàn bộ `fft32.txt`, đổi `cfg_floor` theo cột floor | Mọi `rsp_data[31:0]` đúng, phần còn lại bằng 0 |
| **NTT 16 bit, q chuẩn** | Chạy `ntt16_pqc.txt` | z0, z1 đúng, 16 bit cao của mỗi ô bằng 0, bit 64 bằng 0 |
| **NTT 16 bit, q khác** | Chạy `ntt16_q_khac.txt` | z0, z1 đúng, 16 bit cao của mỗi ô bằng 0, bit 64 bằng 0 |
| **NTT 32 bit** | Chạy `ntt32.txt` | z0, z1 đúng, bit 64 bằng 0 |
| **Ô không dùng** | Trong mọi ca trên | Ô kết quả không thuộc chế độ luôn bằng 0 |

### Nhóm B — luồng dữ liệu và thời gian

| Case | Cách làm | Đạt khi |
|---|---|---|
| **Đúng thứ tự và nhãn** | Gửi liên tiếp mọi vector của một file, `req_tag` tăng dần quay vòng | Kết quả ra đúng thứ tự gửi, đúng một kết quả mỗi request, `rsp_tag` đúng |
| **Dừng chung** | Như trên, hạ `en` ngẫu nhiên với xác suất 0,1 và 0,3; thêm các đợt hạ liên tục dài tới 64 chu kỳ | Chuỗi kết quả giống hệt khi không dừng; `rsp_valid = 0` mọi chu kỳ `en = 0`; đầu ra không đổi trong lúc `en = 0` |
| **Request thưa** | Hạ `req_valid` ngẫu nhiên (xác suất 0,5) | Kết quả đúng và đúng thứ tự |
| **Độ trễ cố định** | Với từng chế độ và lane, gửi liên tục không dừng | Mọi request có cùng độ trễ, bằng con số đã công bố trong manifest |
| **Lịch không phụ thuộc dữ liệu** | Chạy cùng một chuỗi request hai lần: lần một dữ liệu và root đều bằng 0, lần hai ngẫu nhiên | Chuỗi `req_ready` và `rsp_valid` theo chu kỳ giống hệt nhau |
| **Tốc độ bền vững** | Với từng dòng của bảng tốc độ ở mục 6 của hợp đồng: ≥ 1 000 request, `req_valid = 1`, `en = 1` | Tốc độ ≥ 98% con số của biến thể đang kiểm |
| **Đổi chế độ và hằng số** | Chuỗi: butterfly 16 bit q = 12289 → tích FFT 32 bit → butterfly 32 bit q = 8380417 → tích thô → butterfly GS 32 bit prime NTRUGen có chia đôi → nhân modulo 16 bit q = 3329. Mỗi lần đổi chờ `idle = 1` rồi ghi hằng số | Mọi kết quả đúng; không có kết quả lẫn giữa hai đoạn |
| **Ghi hằng số chỉ khi rảnh** | Giữ `cfg_we = 1` lúc `idle = 0` (chỉ để kiểm) | Hằng số không bị đổi giữa chừng; chỉ chốt khi `idle = 1`; kết quả của các request đang chạy vẫn đúng |
| **Reset giữa chừng** | Bật `rst` khi còn request đang chạy, ở nhiều thời điểm khác nhau | Sau reset: không còn kết quả của request cũ, `idle = 1`, hằng số bằng 0; ghi lại hằng số rồi chạy tiếp thì kết quả đúng |

### Nhóm C — testbench phải bắt được lỗi

Testbench chỉ đáng tin nếu nó bắt được lỗi cố ý cài vào. Mỗi lỗi chạy một lần, và phải ra **không đạt**:

| Lỗi cài vào | Phải bắt được nhờ |
|---|---|
| Sửa một giá trị mong đợi trong bản sao của file vector | So sánh kết quả |
| Bỏ bit `[T_thấp ≠ 0]` trong RTL (một `define` chỉ dùng để kiểm), ở bộ rút gọn hằng và ở lane 32 bit | Các ca T_thấp ≠ 0 |
| Luôn cộng bit `[T_thấp ≠ 0]` = 1 | Các ca T là bội của R |
| Bỏ bước trừ q cuối | Các ca có u ≥ q |
| Chia đôi cả khi `cfg_halve = 0` | Các ca GS không chia đôi |
| Đổi chỗ x và y của butterfly | Mọi ca chế độ 4 có d0 ≠ d1 |
| Đổi chỗ hai kết quả liền nhau | Case đúng thứ tự và nhãn |

### Nhóm D — đo trên FPGA

Theo mục 8 của [hợp đồng cấp tile](10_hop_dong_tile.md#8-đo-trên-fpga). Chỉ đo sau khi nhóm A, B, C đạt ở cả hai biến
thể.

| Số liệu (sau route) | Trên mảng | Rút gọn riêng lane 32 bit (v1) | Tỉ lệ |
|---|---:|---:|---:|
| LUT | 1 022 | 906 | 1,128 (+12,8%) |
| FF | 959 | 1 033 | 0,928 |
| DSP | 4 | 11 | −7 |
| BRAM / URAM | 0 / 0 | 0 / 0 | |
| WNS ở 3,0 ns; Fmax | +0,168 ns; ≥ 333 MHz | +0,287 ns; ≥ 333 MHz | cả hai đạt 3,0 ns, Fmax chỉ là cận dưới |
| Độ trễ đã công bố (từng chế độ) | 0, 1: 6; 2, 4 lane 16 bit: 13; 2, 4 lane 32 bit: 19 | 6; 13; 15 | |

Lần đo 31/10/2026, Vivado 2018.1, RTL [hdl/tile/tile_thu.sv](../../../hdl/tile/tile_thu.sv), script
`fpga/zcu106/tile_thu.tcl` với `TILE_RTL=hdl/tile/tile_thu.sv TILE_TAG=tile_acc`; báo cáo ở `study/build/tile_acc_<biến thể>/`.

**Giả thuyết 2** (ngưỡng khóa lần 3): DSP ít hơn 7 (đạt); LUT tăng 12,8% (**chạm điều kiện bác bỏ**, LUT tăng > 10%);
Fmax không thấy giảm (cận dưới); tốc độ tile lane 32 bit chậm 3 lần, cả NTT 32 bit N256 chưa đo, ước lượng theo lượt một
tầng khoảng 1,8 lần (đạt, ngưỡng ≤ 3,5). Kết quả: **bác bỏ ở cấp tile**, ở điều kiện LUT. Cấp lõi chưa đo.

**Lần đo 2** (31/10/2026, RTL sửa: mặc định `TREN_MANG = 3`, độ trễ suy từ tham số `LEAF_PD`, tham số `IN_REG`, sửa
cảnh báo độ rộng; hash `8d2a02a8890211e1`; báo cáo `study/build/tile_acc2_<biến thể>/`):

| Số liệu (sau route) | Trên mảng | Rút gọn riêng lane 32 bit (v1) | Tỉ lệ | v1 với `IN_REG = 1` |
|---|---:|---:|---:|---:|
| LUT | 1 022 | 925 | 1,105 (+10,5%) | 905 |
| FF | 959 | 1 033 | 0,928 | 1 132 |
| DSP | 4 | 11 | −7 | 11 |
| BRAM / URAM | 0 / 0 | 0 / 0 | | 0 / 0 |
| WNS ở 3,0 ns; Fmax | +0,118 ns; ≥ 333 MHz | +0,265 ns; ≥ 333 MHz | cận dưới | +0,258 ns; ≥ 333 MHz |
| Độ trễ (0, 1 / lane 16 / lane 32) | 6 / 13 / 19 | 6 / 13 / 15 | | 7 / 14 / 16 |

Logic của hai biến thể không đổi so với lần 1; LUT của biến thể v1 lệch 19 do đặt cell. Giả thuyết 2 vẫn **bác bỏ** (LUT
+10,5% > 10%), sát ngưỡng hơn lần 1. Đường dài nhất của v1 nay là tín hiệu cho phép chung `en` (fanout 784, 2,56 ns dây)
tới chân cho phép của thanh ghi đầu vào bộ nhân.

## 3. Bảng kết quả

Điền sau mỗi lần chạy. Ghi kèm phiên bản RTL, phiên bản trình mô phỏng và hash của manifest vector.

Lần chạy 3, 31/10/2026: RTL thêm tùy chọn `EN_REG` (hash `539b0697ef9cdb4f`), bốn cấu hình với testbench `ff750e01c3cf3066`; sau đó testbench sửa thành `68480ad04e87b005` (bước chờ `idle` có giới hạn, để RTL làm mất kết quả thì ra FAIL thay vì treo) và chạy lại cấu hình mặc định và `-DTL_EN_REG=1`, đều đạt. Bốn cấu hình (mặc
định; `-DTL_EN_REG=1`; thêm `-DTL_IN_REG=1`; thêm `-DTL_LEAF_PD=4`), mỗi cấu hình 64 lần chạy đạt, 24/24 lỗi bị bắt.
Đo Vivado cấu hình mặc định: 932 LUT, 1 036 FF, 11 DSP, WNS +0,238 ns (ghi chú bản nháp mục 14). Bảng dưới vẫn đúng.

Lần chạy 2, 31/10/2026: RTL sửa (hash `8d2a02a8890211e1`, testbench `ff750e01c3cf3066`), cùng lệnh, chạy ba cấu hình
(mặc định; `IVFLAGS="-DTL_IN_REG=1"`; `IVFLAGS="-DTL_LEAF_PD=4"`), mỗi cấu hình 64 lần chạy đạt, 24/24 lỗi bị bắt, độ
trễ cố định (log `sim/tile_thu/build/acceptance_<cấu hình>.log`). Bảng dưới vẫn đúng cho lần chạy này.

Lần chạy 1, 31/10/2026: RTL [hdl/tile/tile_thu.sv](../../../hdl/tile/tile_thu.sv) (SHA-256 16 ký tự đầu `0a28e919ccc11633`, bản sao ở
`study/build/tile_acc_v1_0a28e919.sv`),
Icarus Verilog 14.0, testbench `709d56e377a8517b`, manifest vector `f06dd7af39b63c64`, lệnh
`VARIANTS="1 3" sh sim/tile_thu/run.sh hdl/mul_ss.v hdl/tile/tile_thu.sv`: 64 lần chạy đạt, 24/24 lỗi cài vào bị bắt
(log `sim/tile_thu/build/acceptance.log`). **RTL này do trợ lý viết, cùng tác giả với testbench**, nên phần hiểu hợp đồng
giao tiếp chưa được kiểm độc lập.

| Case | Trên mảng | Rút gọn riêng lane 32 bit (v1) |
|---|---|---|
| Tích thô 32×32 | đạt | đạt |
| Tích FFT 32 bit | đạt | đạt |
| NTT 16 bit, q chuẩn | đạt | đạt |
| NTT 16 bit, q khác | đạt | đạt |
| NTT 32 bit | đạt | đạt |
| Ô không dùng | đạt | đạt |
| Đúng thứ tự và nhãn | đạt | đạt |
| Dừng chung | đạt | đạt |
| Request thưa | đạt | đạt |
| Độ trễ cố định | đạt | đạt |
| Lịch không phụ thuộc dữ liệu | đạt | đạt |
| Tốc độ bền vững | đạt | đạt |
| Đổi chế độ và hằng số | đạt | đạt |
| Ghi hằng số chỉ khi rảnh | đạt | đạt |
| Reset giữa chừng | đạt | đạt |
| Bắt được lỗi cài vào (7 lỗi) | đạt | đạt |
| Đo trên FPGA | đã đo (nhóm D) | đã đo (nhóm D) |

## 4. Tái lập

Từ thư mục dự án:

```text
python scripts/build_spec2_tile_vectors.py    # sinh lại vector; hash phải giống manifest đã phát hành
python scripts/check_spec2_tile_vectors.py    # kiểm chéo vector với mô hình dạng phần cứng
```

## 5. Testbench và script chạy sẵn

Testbench [sim/tile_thu/tb_tile_thu.sv](../../../sim/tile_thu/tb_tile_thu.sv) chỉ dùng các cổng ở mục 2 của
[hợp đồng tile](10_hop_dong_tile.md), nên chạy được với RTL bất kỳ có cùng giao diện. Script
[sim/tile_thu/run.sh](../../../sim/tile_thu/run.sh) chạy toàn bộ nhóm A, B, C cho các biến thể:

```text
sh sim/tile_thu/run.sh                                   # RTL bản nháp
VARIANTS="1 3" sh sim/tile_thu/run.sh hdl/mul_ss.v <các file RTL của bạn>   # RTL thật
```

Yêu cầu với RTL: module `tile_thu` có tham số `TREN_MANG` (3 = rút gọn riêng lane 32 bit, thiết kế v1; 1 = lane 32 bit
trên mảng, biến thể đã bác bỏ, giữ để so). Bản nháp có thêm hai điểm đo: 2 = bộ rút gọn hằng ở lane 16 bit, 0 = rút gọn riêng cả hai lane. Nếu tên khác, sửa một dòng khởi tạo trong testbench và ghi vào manifest triển khai.

| Case | Cách testbench làm |
|---|---|
| Nhóm A, thứ tự và nhãn, độ trễ cố định | Mặc định |
| Tốc độ bền vững | Tự kiểm: mọi nhóm chạy không dừng, không hạ `req_valid`, không reset, có ≥ 1 000 request phải đạt 98% tốc độ ở mục 6 của hợp đồng (lane 32 bit trên mảng khi `TREN_MANG` = 1 hoặc 2, riêng khi 3 hoặc 0). Script chạy `+REP=2` cho tích thô và FFT, `+REP=6` cho NTT |
| Dừng chung | `+STALL=10`, `+STALL=30 +BURST=1`. Luôn kiểm thêm: `rsp_valid = 0` khi `en = 0`; `rsp_data`, `rsp_tag`, `idle` không đổi qua một chu kỳ `en = 0` |
| Request thưa | `+SPARSE=50` |
| Đổi chế độ và hằng số | `+CHAIN=<thư mục vector>`: butterfly q12289 → tích FFT 32 bit → butterfly q8380417 → tích thô → butterfly GS prime NTRUGen có chia đôi → nhân modulo q3329; mỗi lần đổi chờ rảnh rồi ghi hằng số |
| Ghi hằng số chỉ khi rảnh | `+CFGBUSY=1`: mọi chu kỳ có `idle = 0`, giữ `cfg_we = 1` với hằng số ngẫu nhiên; kết quả phải vẫn đúng |
| Reset giữa chừng | `+RESETAT=k`: sau k request của mỗi nhóm, bật `rst` một chu kỳ; 64 chu kỳ sau đó phải `rsp_valid = 0` và `idle = 1`; ghi lại hằng số và chạy lại nhóm, kết quả phải đúng. "Hằng số bằng 0 sau reset" không kiểm được từ cổng; RTL thật kiểm bằng assertion nội bộ nếu muốn |
| Lịch không phụ thuộc dữ liệu | `+SCHED=1`: mỗi nhóm chạy hai lần từ reset với cùng chuỗi `en`/`req_valid`, lần đầu dữ liệu và root bằng 0; chuỗi `req_ready`/`rsp_valid` theo chu kỳ phải giống hệt |
| Nhóm C, sửa giá trị mong đợi | `+CORRUPT=1` (lật một bit của kết quả mong đợi đầu tiên) |
| Nhóm C, đổi chỗ hai kết quả | `+SWAPEXP=1` (đổi kết quả và nhãn mong đợi của hai request đầu; thay cho việc sửa RTL) |
| Nhóm C, lỗi trong RTL | RTL phải có các `define` sau, mỗi cái cài đúng một lỗi, không bao giờ bật khi build thường: `FAULT_NO_NZ` (bit `[T_thấp ≠ 0]` = 0), `FAULT_NZ_ONE` (= 1), `FAULT_NO_SUBQ` (bỏ trừ q cuối), `FAULT_HALVE_ALWAYS` (chia đôi cả khi `cfg_halve = 0`), `FAULT_SWAP_XY` (đổi chỗ x và y của butterfly). Ba lỗi đầu phải áp dụng cho cả rút gọn lane 16 bit lẫn lane 32 bit; script chạy mỗi lỗi trên cả `ntt16_pqc` và `ntt32`, cả hai phải ra không đạt |

Mỗi dòng kết quả của script kết thúc bằng `PASS` hoặc `FAIL`; mọi dòng nhóm C phải ghi "bắt được". Kết quả trên bản
nháp ở [study/results/tile_thu_draft.md](../../../study/results/tile_thu_draft.md); bảng ở mục 3 chỉ điền khi chạy
trên RTL thật.
