# 11 — Kiểm thử cấp tile

> **Thay đổi 31/10/2026, lần 2:** theo hợp đồng tile một làn ([10](10_hop_dong_tile.md), đầu tài liệu). Vector NTT,
> cột file, chuỗi đổi chế độ, lỗi cài vào và kiểm tốc độ được làm lại. Bản trước:
> [trước khi chuyển sang một làn](../../../docs/plan_history/spec2_before_single_lane_2026-10-31/11_kiem_thu_tile.md).

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
| `ntt16_q_khac.txt` | 1 998 | Chế độ 2 và 4, lane 16 bit, q = 3, 7681, 65521 | Không áp dụng cho v1 (chỉ dùng cho điểm đo "mọi modulus trên mảng", 10 mục 5.3) |
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
| **NTT 16 bit, q khác** | Không áp dụng cho v1: lane 16 bit chỉ nhận 3329 và 12289 | — |
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

| Số liệu (sau route) | Lai | Rút gọn riêng | Tỉ lệ |
|---|---:|---:|---:|
| LUT | | | |
| FF | | | |
| DSP | | | |
| BRAM / URAM | | | |
| WNS ở 3,0 ns; Fmax | | | |
| Độ trễ đã công bố (từng chế độ) | | | |

## 3. Bảng kết quả

Điền sau mỗi lần chạy. Ghi kèm phiên bản RTL, phiên bản trình mô phỏng và hash của manifest vector.

| Case | Lai | Rút gọn riêng |
|---|---|---|
| Tích thô 32×32 | chưa chạy | chưa chạy |
| Tích FFT 32 bit | chưa chạy | chưa chạy |
| NTT 16 bit, q chuẩn | chưa chạy | chưa chạy |
| NTT 16 bit, q khác | không áp dụng | không áp dụng |
| NTT 32 bit | chưa chạy | chưa chạy |
| Ô không dùng | chưa chạy | chưa chạy |
| Đúng thứ tự và nhãn | chưa chạy | chưa chạy |
| Dừng chung | chưa chạy | chưa chạy |
| Request thưa | chưa chạy | chưa chạy |
| Độ trễ cố định | chưa chạy | chưa chạy |
| Lịch không phụ thuộc dữ liệu | chưa chạy | chưa chạy |
| Tốc độ bền vững | chưa chạy | chưa chạy |
| Đổi chế độ và hằng số | chưa chạy | chưa chạy |
| Ghi hằng số chỉ khi rảnh | chưa chạy | chưa chạy |
| Reset giữa chừng | chưa chạy | chưa chạy |
| Bắt được lỗi cài vào (7 lỗi) | chưa chạy | chưa chạy |
| Đo trên FPGA | chưa chạy | chưa chạy |

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
sh sim/tile_thu/run.sh hdl/mul_ss.v <các file RTL của bạn>   # RTL thật
```

Yêu cầu với RTL: module `tile_thu` có tham số `TREN_MANG` (2 = lai, 0 = rút gọn riêng; bản nháp có thêm 1 = mọi modulus
trên mảng). Nếu tên khác, sửa một dòng khởi tạo trong testbench và ghi vào manifest triển khai.

| Case | Cách testbench làm |
|---|---|
| Nhóm A, thứ tự và nhãn, độ trễ cố định | Mặc định |
| Tốc độ bền vững | Tự kiểm: mọi nhóm chạy không dừng, không hạ `req_valid`, không reset, có ≥ 1 000 request phải đạt 98% tốc độ ở mục 6 của hợp đồng (`TREN_MANG = 0`: rút gọn riêng, khác 0: lane 32 bit trên mảng). Script chạy `+REP=2` cho tích thô và FFT, `+REP=6` cho NTT |
| Dừng chung | `+STALL=10`, `+STALL=30 +BURST=1`. Luôn kiểm thêm: `rsp_valid = 0` khi `en = 0`; `rsp_data`, `rsp_tag`, `idle` không đổi qua một chu kỳ `en = 0` |
| Request thưa | `+SPARSE=50` |
| Đổi chế độ và hằng số | `+CHAIN=<thư mục vector>`: butterfly q12289 → tích FFT 32 bit → butterfly q8380417 → tích thô → butterfly GS prime NTRUGen có chia đôi → nhân modulo q3329; mỗi lần đổi chờ rảnh rồi ghi hằng số |
| Ghi hằng số chỉ khi rảnh | `+CFGBUSY=1`: mọi chu kỳ có `idle = 0`, giữ `cfg_we = 1` với hằng số ngẫu nhiên; kết quả phải vẫn đúng |
| Reset giữa chừng | `+RESETAT=k`: sau k request của mỗi nhóm, bật `rst` một chu kỳ; 64 chu kỳ sau đó phải `rsp_valid = 0` và `idle = 1`; ghi lại hằng số và chạy lại nhóm, kết quả phải đúng. "Hằng số bằng 0 sau reset" không kiểm được từ cổng; RTL thật kiểm bằng assertion nội bộ nếu muốn |
| Lịch không phụ thuộc dữ liệu | `+SCHED=1`: mỗi nhóm chạy hai lần từ reset với cùng chuỗi `en`/`req_valid`, lần đầu dữ liệu và root bằng 0; chuỗi `req_ready`/`rsp_valid` theo chu kỳ phải giống hệt |
| Nhóm C, sửa giá trị mong đợi | `+CORRUPT=1` (lật một bit của kết quả mong đợi đầu tiên) |
| Nhóm C, đổi chỗ hai kết quả | `+SWAPEXP=1` (đổi kết quả và nhãn mong đợi của hai request đầu; thay cho việc sửa RTL) |
| Nhóm C, lỗi trong RTL | RTL phải có các `define` sau, mỗi cái cài đúng một lỗi, không bao giờ bật khi build thường: `FAULT_NO_NZ` (bit `[T_thấp ≠ 0]` = 0), `FAULT_NZ_ONE` (= 1), `FAULT_NO_SUBQ` (bỏ trừ q cuối), `FAULT_HALVE_ALWAYS` (chia đôi cả khi `cfg_halve = 0`), `FAULT_SWAP_XY` (đổi chỗ x và y của butterfly). Ba lỗi đầu phải áp dụng cho cả bộ rút gọn hằng lane 16 bit lẫn rút gọn lane 32 bit; script chạy mỗi lỗi trên cả `ntt16_pqc` và `ntt32`, cả hai phải ra không đạt |

Mỗi dòng kết quả của script kết thúc bằng `PASS` hoặc `FAIL`; mọi dòng nhóm C phải ghi "bắt được". Kết quả trên bản
nháp ở [study/results/tile_thu_draft.md](../../../study/results/tile_thu_draft.md); bảng ở mục 3 chỉ điền khi chạy
trên RTL thật.
