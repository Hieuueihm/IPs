# 11 — Kiểm thử cấp tile

> **Thay đổi 02/11/2026, lần 8:** tile còn ba chế độ, `req_mode` 2 bit ([10](10_hop_dong_tile.md) lần 11): 0 NTT, 1 FFT,
> 2 NTT hai hệ số 16 bit mỗi từ.
> - Bỏ `raw32.txt`, `fft32.txt` và các dòng phép nhân modulo đơn của `ntt.txt`; `ntt.txt` bỏ cột chế độ (6 228 ca, sinh lại).
> - Vector mới `ntt16.txt` (7 254 request) cho chế độ NTT hai hệ số. Testbench đọc `+KIND=0` NTT, `1` FFT 32 bit, `2` FFT
>   64 / 128 bit, `3` NTT hai hệ số.
> - Chuỗi đổi chế độ chạy NTT q12289 → FFT 32 bit → NTT q8380417 → NTT hai hệ số → NTT GS prime NTRUGen có chia đôi →
>   FFT 128 bit.
> - Regression chạy chế độ mới ở nhóm A, B, C như NTT, chỉ ở biến thể trên mảng; chạy cả với `-DTL_EN_REG=1`.
> - Kiểm chéo vector thêm mô hình một lá mỗi làn cho `ntt16.txt`.
>
> Bản trước: [trước khi rút gọn chế độ](../../../docs/plan_history/before_tile_mode6_2026-11-01/11_kiem_thu_tile.md).

> **Thay đổi 01/11/2026, lần 7:** chế độ 5 ở 64 / 128 bit ([10](10_hop_dong_tile.md) mục 4.8). Vector mới `fftwbf.txt`
> (1 920 butterfly, mỗi dòng 2L nhịp), testbench đọc bằng `+KIND=4`; regression thêm các lần chạy nhóm A, B như chế độ 5
> 32 bit, lỗi `FAULT_SWAP_XY` và lỗi mới `FAULT_NO_CARRY` (bỏ cờ nhớ giữa các phần). Đo thời gian ra của từng nhịp:
> [sim/tile_thu/tb_wide_timing.sv](../../../sim/tile_thu/tb_wide_timing.sv). Bản trước:
> [trước khi thêm 64 / 128 bit](../../../docs/plan_history/before_fft_wide_2026-11-01/11_kiem_thu_tile.md).

> **Thay đổi 01/11/2026, lần 6:** chế độ 5 (butterfly FFT 32 bit, [10](10_hop_dong_tile.md) mục 4.7). Vector mới
> `fft32bf.txt` (1 470 butterfly, mỗi dòng hai nhịp), testbench đọc bằng `+KIND=3` và luôn đưa nhịp 2 ngay sau nhịp 1;
> regression thêm chế độ 5 ở nhóm A, B (dừng, request thưa, ghi hằng số lúc bận, reset giữa chừng, lịch không phụ thuộc
> dữ liệu) và lỗi `FAULT_SWAP_XY`; cấu hình `-DTL_EN_REG=1` bỏ chế độ 5 (hợp đồng chỉ định nghĩa nó với `EN_REG` = 0).
> Bản trước: [trước khi thêm chế độ 5](../../../docs/plan_history/before_tile_mode5_2026-11-01/11_kiem_thu_tile.md).

> **Thay đổi 31/10/2026, lần 5:** theo hợp đồng một lane 32 bit ([10](10_hop_dong_tile.md), lần 6). Ba file
> `ntt16_pqc.txt`, `ntt16_q_khac.txt`, `ntt32.txt` gộp thành `ntt.txt` (mọi q, R = 2³², không còn cột lane32); testbench
> bỏ `cfg_lane32`; hai ô modulus và lỗi `FAULT_IGNORE_SLOT` nay kiểm cả q nhỏ; script mặc định chạy RTL nghiệm thu. Bản
> trước: [trước khi chuyển sang một lane 32 bit](../../../docs/plan_history/before_one_lane_2026-10-31/11_kiem_thu_tile.md).

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
| `fft32bf.txt` | 1 470 | Chế độ FFT 32 bit, xuôi; ngược không chia và chia với s = 1, 5, 9; mỗi giá trị biên (0, ±1, 2³¹ − 1, −2³¹, ±2¹⁶, …) lần lượt ở từng toán hạng, còn lại ngẫu nhiên. Kết quả tính bằng số nguyên thuần (spec 1.0 01.1) và kiểm chéo với model/fft_core_plan.py | Cả hai |
| `fftwbf.txt` | 1 920 | Chế độ FFT ở 64 bit (`fmt` 1) và 128 bit (`fmt` 2), mỗi độ rộng: xuôi; ngược không chia và chia với s = 1, 5, 9; mỗi giá trị biên (0, ±1, 2^(W−1) − 1, −2^(W−1), ±2^(W/2), 2³² − 1, ±2³², …) lần lượt ở từng toán hạng, còn lại ngẫu nhiên. Kết quả tính bằng số nguyên thuần (spec 1.0 01.1) và kiểm chéo với model/fft_wide_tile.py (tính theo từng phần) | Cả hai |
| `ntt.txt` | 6 228 | Chế độ NTT, R = 2³², q tăng dần: 3, 3329, 7681, 12289, 65521, 8380417; prime đầu, giữa và cuối của NTRUGen; 2³¹ − 1 | Cả hai |
| `ntt16.txt` | 7 254 | Chế độ NTT hai hệ số, R = 2¹⁶, hằng số theo làn ({q, q}, {q′, q′}), q = 3329, 7681, 10753, 12289, 18433; mỗi q: CT, GS, GS có chia đôi, mỗi loại với hai cách ghép cặp; mỗi giá trị biên (0, 1, 2, q − 1, q − 2, q/2, lũy thừa của 2) lần lượt ở từng toán hạng của hai làn; các ca b · w là bội của 2¹⁶; còn lại ngẫu nhiên | Chỉ trên mảng |

Với mỗi q, vector NTT phủ đủ ba tổ hợp: CT; GS; GS có chia đôi.

Mỗi giá trị đặc biệt (0, 1, 2, q − 1, q − 2, quanh q/2, các lũy thừa của 2) lần lượt nằm ở từng ô đang dùng (d0, d1,
r0), ô root đi kèm một giá trị đặc biệt khác. Mỗi request có đúng một phép nhân modulo. Các trường hợp góc:

| Trường hợp | q < 2¹⁶ | q > 2¹⁶ |
|---|---:|---:|
| Phép nhân modulo đã phủ | 2 502 | 3 726 |
| T là bội của R nhưng khác 0 (T_thấp = 0, bit `[T_thấp ≠ 0]` phải bằng 0) | 0 (không xảy ra: T < q² < R) | 217 |
| T = 0 | 249 | 308 |

Vì vậy lỗi "luôn cộng bit `[T_thấp ≠ 0]` = 1" chỉ bị bắt nhờ q lớn hoặc ca T = 0; với q nhỏ, mọi ca T ≠ 0 đều có
T_thấp ≠ 0.

**Cách đọc file.** Mỗi dòng một ca, các trường hex cách nhau bằng dấu cách, dòng bắt đầu bằng `#` là chú thích. File
chỉ có ký tự ASCII, đọc được bằng `$fscanf(fd, "%h ...")`. Cột của file NTT là:

```text
q qinv dir halve x y w z0 z1
```

qinv = −q⁻¹ mod 2³² với mọi q. Dòng được nhóm theo q rồi theo hướng. Khi q, chế độ, hướng hoặc cờ chia đôi đổi,
testbench phải chờ `idle = 1`, ghi thanh ghi hằng số (q, qinv, halve), rồi gửi tiếp. Nếu cột halve = 0 thì
`cfg_halve = 0`.

Bộ vector này **thay cho** 16 102 vector của cụm NTT cũ khi kiểm khối tile thử, vì cụm cũ chỉ có lane 16 bit và cách
đóng gói khác. Nó cũng thay bộ vector nhịp hai tầng của hợp đồng tile trước (bản sao ở thư mục lịch sử).

**Kiểm chéo đã chạy (02/11/2026):** [scripts/check_spec2_tile_vectors.py](../../../scripts/check_spec2_tile_vectors.py)
chạy lại 6 228 ca NTT và 7 254 ca NTT hai hệ số qua mô hình dạng phần cứng và cho khớp hết:
- tích cộng từ các tích con 16×16 (NTT) hoặc một lá 16×16 mỗi làn (NTT hai hệ số);
- Montgomery ba lượt với `[T_thấp ≠ 0]`;
- chia đôi bằng cộng có điều kiện rồi dịch.

2 076 ca CT (mọi q) khớp thêm mô hình đã đối chiếu với C của NTRUGen. Vector FFT kiểm chéo với
model/fft_core_plan.py và model/fft_wide_tile.py.

## 2. Các case kiểm thử

### Nhóm A — đúng số học

| Case | Cách làm | Đạt khi |
|---|---|---|
| **NTT, mọi q** | Chạy `ntt.txt` | z0, z1 đúng (với q nhỏ, các bit cao bằng 0 vì kết quả < q) |
| **FFT 32 / 64 / 128 bit** | Chạy `fft32bf.txt`, `fftwbf.txt` | Mọi nhịp kết quả đúng, xuôi và ngược, có chia hay không |
| **NTT hai hệ số mỗi từ** | Chạy `ntt16.txt` | Hai từ kết quả đúng ở cả hai cách ghép cặp |

### Nhóm B — luồng dữ liệu và thời gian

| Case | Cách làm | Đạt khi |
|---|---|---|
| **Đúng thứ tự và nhãn** | Gửi liên tiếp mọi vector của một file, `req_tag` tăng dần quay vòng | Kết quả ra đúng thứ tự gửi, đúng một kết quả mỗi request, `rsp_tag` đúng |
| **Dừng chung** | Như trên, hạ `en` ngẫu nhiên với xác suất 0,1 và 0,3; thêm các đợt hạ liên tục dài tới 64 chu kỳ | Chuỗi kết quả giống hệt khi không dừng; `rsp_valid = 0` mọi chu kỳ `en = 0`; đầu ra không đổi trong lúc `en = 0` |
| **Request thưa** | Hạ `req_valid` ngẫu nhiên (xác suất 0,5) | Kết quả đúng và đúng thứ tự |
| **Độ trễ cố định** | Với từng chế độ và q, gửi liên tục không dừng | Mọi request có cùng độ trễ, bằng con số đã công bố trong manifest |
| **Lịch không phụ thuộc dữ liệu** | Chạy cùng một chuỗi request hai lần: lần một dữ liệu và root đều bằng 0, lần hai ngẫu nhiên | Chuỗi `req_ready` và `rsp_valid` theo chu kỳ giống hệt nhau |
| **Tốc độ bền vững** | Với từng dòng của bảng tốc độ ở mục 6 của hợp đồng: ≥ 1 000 request, `req_valid = 1`, `en = 1` | Tốc độ ≥ 98% con số của biến thể đang kiểm |
| **Đổi chế độ và hằng số** | Chuỗi: NTT q = 12289 → FFT 32 bit → NTT q = 8380417 → NTT hai hệ số (ghép trong một từ) → NTT GS prime NTRUGen có chia đôi → FFT 128 bit. Mỗi lần đổi chờ `idle = 1` rồi ghi hằng số | Mọi kết quả đúng; không có kết quả lẫn giữa hai đoạn |
| **Ghi hằng số chỉ khi rảnh** | Giữ `cfg_we = 1` lúc `idle = 0` (chỉ để kiểm) | Hằng số không bị đổi giữa chừng; chỉ chốt khi `idle = 1`; kết quả của các request đang chạy vẫn đúng |
| **Hai ô modulus** | Ghi hai q khác nhau (cùng chế độ, chiều, cờ chia đôi) vào ô 0 và ô 1, rồi trộn ngẫu nhiên request của hai nhóm với `req_slot` tương ứng, có dừng và request thưa; có cặp q nhỏ với q nhỏ, q nhỏ với q lớn (65521 với 8380417) và q lớn với q lớn | Mọi kết quả đúng với q của ô mà request chọn |
| **Reset giữa chừng** | Bật `rst` khi còn request đang chạy, ở nhiều thời điểm khác nhau | Sau reset: không còn kết quả của request cũ, `idle = 1`, hằng số bằng 0; ghi lại hằng số rồi chạy tiếp thì kết quả đúng |

### Nhóm C — testbench phải bắt được lỗi

Testbench chỉ đáng tin nếu nó bắt được lỗi cố ý cài vào. Mỗi lỗi chạy một lần, và phải ra **không đạt**:

| Lỗi cài vào | Phải bắt được nhờ |
|---|---|
| Sửa một giá trị mong đợi trong bản sao của file vector | So sánh kết quả |
| Bỏ bit `[T_thấp ≠ 0]` trong RTL (một `define` chỉ dùng để kiểm) | Các ca T_thấp ≠ 0 |
| Luôn cộng bit `[T_thấp ≠ 0]` = 1 | Các ca T là bội của R |
| Bỏ bước trừ q cuối | Các ca có u ≥ q |
| Chia đôi cả khi `cfg_halve = 0` | Các ca GS không chia đôi |
| Đổi chỗ x và y của butterfly | Mọi ca NTT có d0 ≠ d1 (và FFT, NTT hai hệ số) |
| Mọi request dùng ô modulus 0 | Case hai ô modulus |
| Đổi chỗ hai kết quả liền nhau | Case đúng thứ tự và nhãn |

### Nhóm D — đo trên FPGA

Theo mục 8 của [hợp đồng cấp tile](10_hop_dong_tile.md#8-đo-trên-fpga). Chỉ đo sau khi nhóm A, B, C đạt ở cả hai biến
thể. Các bảng bên dưới là số đo khi tile còn hai lane (lane 16 bit trên ba bộ nhân); số đo một lane 32 bit ở mục 3, lần
chạy 6.

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

Lần chạy 11, 02/11/2026: tile ba chế độ (`req_mode` 2 bit, NTT hai hệ số hai làn), RTL `69c03f65acec27d9`, testbench
`c2ba81e12dc7f48b`, vector sinh lại (manifest mới). Năm cấu hình, hai biến thể: mặc định, `IN_REG`, `LEAF_PD = 4`, `PHASE = 2`
mỗi cấu hình 62 lần chạy đạt, 28/28 lỗi bị bắt; `EN_REG` 27 lần chạy, 22/22 (không có FFT). Kiểm chéo vector:
`check_spec2_tile_vectors.py` đạt. Lõi với tile này: 48 + 54 + 100 ca đạt, chu kỳ không đổi. Diện tích (chỉ tổng hợp, 5,0 ns):
1 759 LUT / 1 521 FF / 251 LUTRAM / 4 DSP, WNS +2,01 ns.

Lần chạy 10, 01/11/2026: RTL thêm chế độ 5 ở 64 / 128 bit (hash `1c7502f7fd64e8a8`). Năm cấu hình, hai biến thể: mặc định, `IN_REG`,
`LEAF_PD = 4`, `PHASE = 2` mỗi cấu hình 82 lần chạy đạt, 22/22 lỗi bị bắt; `EN_REG` 50 lần chạy, 16/16 (không có chế độ 5).
Tốc độ đo: 0,337 request mỗi chu kỳ ở 64 bit (mức 4/12), 0,181 ở 128 bit (mức 8/45). Độ trễ khi testbench gửi liên tục
(butterfly phải chờ trong 4 chỗ giữ): 23..49 (64 bit), 44..173 (128 bit); khi không chờ, đúng bảng của
[10](10_hop_dong_tile.md) mục 4.8 ở cả hai chiều, có chia hay không. Lịch không phụ thuộc dữ liệu (`+SCHED=1`).

Lần chạy 9, 01/11/2026: RTL thêm chế độ 5 (hash `29326f6d2523a117`). Năm cấu hình, hai biến thể: mặc định, `IN_REG`, `LEAF_PD = 4`,
`PHASE = 2` mỗi cấu hình 66 lần chạy đạt, 18/18 lỗi bị bắt; `EN_REG` 50 lần chạy, 16/16 (không có chế độ 5). Độ trễ chế
độ 5: 9 (`IN_REG`: 10; `LEAF_PD = 4`: 11); tốc độ 2/3 request mỗi chu kỳ. Lỗi đã gặp và sửa: với `EN_REG` = 1 hai nhịp có thể
vào đường dữ liệu cách nhau hai chu kỳ (chế độ 5 vì vậy chỉ định nghĩa với `EN_REG` = 0). Vivado (biến thể 1, vỏ đo): 1 299
LUT / 1 213 FF / 4 DSP, WNS −0,009 ns (trước chế độ 5: 781 LUT).

Lần chạy 8, 01/11/2026: RTL thêm tham số `PHASE` (hash `4f7b721872c531da`). Năm cấu hình (mặc định; `-DTL_IN_REG=1`; `-DTL_EN_REG=1`; `-DTL_LEAF_PD=4`; `-DTL_PHASE=2`), hai biến thể: mỗi cấu hình 50 lần chạy đạt, 16/16 lỗi bị bắt (log `sim/tile_thu/build/lech_<cấu hình>.log`). Với `PHASE = 2`, độ trễ và tốc độ không đổi. Tile lệch pha (`PHASE` = t / 6) và 4 bank gói root: mạng 5 216 LUT / 6 001 FF, WNS +0,487 ns (root 1 536 LUT, trước 2 560); 16 tile 12 495 LUT / 14 872 FF / 64 DSP, WNS +0,063 ns; phần tính + mạng 17 711 LUT, 64 DSP.

Lần chạy 7, 01/11/2026: RTL đổi mặc định sang `TREN_MANG = 1` (thiết kế v1 trên mảng; hash `eaf87bef1b1c0820`, logic như lần chạy 6). Cấu hình mặc định, hai biến thể: 50 lần chạy đạt, 16/16 lỗi bị bắt (log `sim/tile_thu/build/v1tm_base.log`). 16 tile v1 trên mảng sau một thanh ghi `en`: 12 494 LUT / 14 872 FF / 64 DSP / 0 BRAM, WNS +0,073 ns; phần tính + mạng 18 733 LUT, 64 DSP.

Lần chạy 6, 31/10/2026, **một lane 32 bit**: RTL hash `cc9b52093081f7c7`, testbench `a66fc98851ab995d`, manifest vector `c539036b6c34ae19`, Icarus Verilog 14.0, lệnh `sh sim/tile_thu/run.sh` (hai biến thể) với bốn cấu hình (mặc định; `-DTL_IN_REG=1`; `-DTL_EN_REG=1`; `-DTL_LEAF_PD=4`): mỗi cấu hình 50 lần chạy đạt, 16/16 lỗi bị bắt (8 loại × 2 biến thể), độ trễ cố định 6 / 15 / 19 (chế độ 0, 1 / NTT riêng / NTT trên mảng; `IN_REG`: +1; `LEAF_PD = 4`: 8 / 17 / 25). `+MIX` chạy đủ 10 cặp q liền nhau, gồm 65521 với 8380417 và 2³¹ − 1 với 3. Script chạy: `study/build/run_regress_mot_lan.sh`, log `sim/tile_thu/build/mot_lan_<cấu hình>.log`. Vivado 2018.1, 3,0 ns, sau route: biến thể 3 (v1) 777 LUT / 1 004 FF / 11 DSP, WNS +0,261 ns; biến thể 1 781 LUT / 937 FF / 4 DSP, WNS +0,371 ns; 16 tile v1 12 207 LUT / 15 888 FF / 176 DSP, WNS +0,112 ns; BRAM / URAM đều 0. So với lần 4 (hai lane), biến thể trên mảng nay đạt các ngưỡng số của giả thuyết 2 ở cấp tile (LUT +0,5%, DSP −7, NTT N256 chậm 1,8 / 1,9 lần với một / hai đa thức); với chữ bản đối chứng cho một lane đã duyệt và khóa lại (lần 5, 01/11/2026, sau khi đã có số đo), giả thuyết 2 **đạt ở cấp tile**. Bảng dưới đúng cho lần chạy này, với hai dòng NTT 16 bit / 32 bit gộp thành "NTT, mọi q".

Lần chạy 5, 31/10/2026: RTL sau tối ưu vi mô (hash `e1d97d2a6dd476b2`, testbench `e177c81a706cff5d`; lane 16 bit chỉ
dùng ô 0), bốn cấu hình, mỗi cấu hình 66 lần chạy đạt, 26/26 lỗi bị bắt. Vivado cấu hình mặc định: 913 LUT, 1 155 FF,
11 DSP, WNS +0,234 ns (biến thể 1: 1 046 LUT, 4 DSP). Bảng dưới cũng đúng cho lần chạy này (lỗi cài vào: 8 loại).

Lần chạy 4, 31/10/2026: RTL có hai ô modulus (hash `9c9082575083813e`, testbench `e177c81a706cff5d` có `+MIX`), bốn
cấu hình (mặc định; `-DTL_EN_REG=1`; `-DTL_IN_REG=1`; `-DTL_LEAF_PD=4`), mỗi cấu hình 68 lần chạy đạt, 28/28 lỗi bị bắt.
Vivado cấu hình mặc định: 1 052 LUT, 1 126 FF, 11 DSP, WNS +0,182 ns (biến thể 1: 1 155 LUT, 4 DSP). Bảng dưới là kết quả
lần chạy này.

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

| Case | Trên mảng | Rút gọn riêng (v1) |
|---|---|---|
| Tích thô 32×32 | đạt | đạt |
| Tích FFT 32 bit | đạt | đạt |
| NTT, mọi q | đạt | đạt |
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
| Hai ô modulus | đạt | đạt |
| Bắt được lỗi cài vào (8 lỗi) | đạt | đạt |
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
sh sim/tile_thu/run.sh                                   # RTL nghiệm thu, hai biến thể
VARIANTS="3" IVFLAGS="-DTL_EN_REG=1" sh sim/tile_thu/run.sh hdl/mul_ss.v <các file RTL của bạn>
```

Yêu cầu với RTL: module `tile_thu` có tham số `TREN_MANG` (1 = rút gọn trên mảng, thiết kế v1 từ 01/11/2026; 3 = rút
gọn riêng, bản đối chứng). Bản nháp `hdl/tile_thu/` còn hợp đồng hai lane (`cfg_lane32`) và chỉ chạy với testbench
cũ trong `docs/plan_history/before_one_lane_2026-10-31/sim/`. Nếu tên khác, sửa một dòng khởi tạo trong testbench và ghi
vào manifest triển khai.

| Case | Cách testbench làm |
|---|---|
| Nhóm A, thứ tự và nhãn, độ trễ cố định | Mặc định |
| Tốc độ bền vững | Tự kiểm: mọi nhóm chạy không dừng, không hạ `req_valid`, không reset, có ≥ 1 000 request phải đạt 98% tốc độ ở mục 6 của hợp đồng (NTT và NTT hai hệ số 1/3 khi `TREN_MANG` = 1, NTT 1 khi 3; FFT 2/3, 4/12, 8/45). Script chạy `+REP=2` cho FFT, `+REP=6` cho NTT, `+REP=5` cho NTT hai hệ số; nhóm q = 3 (126 hoặc 129 ca, dưới 1 000 sau khi lặp 6 lần) không được kiểm tốc độ |
| Dừng chung | `+STALL=10`, `+STALL=30 +BURST=1`. Luôn kiểm thêm: `rsp_valid = 0` khi `en = 0`; `rsp_data`, `rsp_tag`, `idle` không đổi qua một chu kỳ `en = 0` |
| Request thưa | `+SPARSE=50` |
| Đổi chế độ và hằng số | `+CHAIN=<thư mục vector>`: NTT q12289 → FFT 32 bit → NTT q8380417 → NTT hai hệ số → NTT GS prime NTRUGen có chia đôi → FFT 128 bit; mỗi lần đổi chờ rảnh rồi ghi hằng số. Chỉ ở biến thể trên mảng và `EN_REG` = 0 (chuỗi có FFT và NTT hai hệ số); nơi khác `+CORRUPT`, `+SWAPEXP` chạy trên `ntt.txt` |
| Ghi hằng số chỉ khi rảnh | `+CFGBUSY=1`: mọi chu kỳ có `idle = 0`, giữ `cfg_we = 1` với hằng số ngẫu nhiên; kết quả phải vẫn đúng |
| Reset giữa chừng | `+RESETAT=k`: sau k request của mỗi nhóm, bật `rst` một chu kỳ; 64 chu kỳ sau đó phải `rsp_valid = 0` và `idle = 1`; ghi lại hằng số và chạy lại nhóm, kết quả phải đúng. "Hằng số bằng 0 sau reset" không kiểm được từ cổng; RTL thật kiểm bằng assertion nội bộ nếu muốn |
| Lịch không phụ thuộc dữ liệu | `+SCHED=1`: mỗi nhóm chạy hai lần từ reset với cùng chuỗi `en`/`req_valid`, lần đầu dữ liệu và root bằng 0; chuỗi `req_ready`/`rsp_valid` theo chu kỳ phải giống hệt |
| Hai ô modulus | `+MIX=1` trên `ntt.txt` và `ntt16.txt` (cùng cách ghép cặp), kèm `+STALL=20 +BURST=1 +SPARSE=30`: mỗi nhóm NTT ghép với nhóm kế tiếp (vòng tròn) cùng chế độ, chiều, cờ chia đôi nhưng khác q; vì q tăng dần nên có cả cặp q nhỏ với q lớn |
| Nhóm C, sửa giá trị mong đợi | `+CORRUPT=1` (lật một bit của kết quả mong đợi đầu tiên) |
| Nhóm C, đổi chỗ hai kết quả | `+SWAPEXP=1` (đổi kết quả và nhãn mong đợi của hai request đầu; thay cho việc sửa RTL) |
| Nhóm C, lỗi trong RTL | RTL phải có các `define` sau, mỗi cái cài đúng một lỗi, không bao giờ bật khi build thường: `FAULT_NO_NZ` (bit `[T_thấp ≠ 0]` = 0), `FAULT_NZ_ONE` (= 1), `FAULT_NO_SUBQ` (bỏ trừ q cuối), `FAULT_HALVE_ALWAYS` (chia đôi cả khi `cfg_halve = 0`), `FAULT_SWAP_XY` (đổi chỗ x và y của butterfly), `FAULT_IGNORE_SLOT` (mọi request dùng ô 0; script chạy với `+MIX=1`). Script chạy mỗi lỗi trên `ntt.txt` (mọi q) và trên `ntt16.txt` (NTT hai hệ số); `FAULT_SWAP_XY` thêm trên hai file FFT; `FAULT_NO_CARRY` (bỏ cờ nhớ giữa các phần) trên `fftwbf.txt`. Mọi lần phải ra không đạt |

Mỗi dòng kết quả của script kết thúc bằng `PASS` hoặc `FAIL`; mọi dòng nhóm C phải ghi "bắt được". Kết quả trên bản
nháp ở [study/results/tile_thu_draft.md](../../../study/results/tile_thu_draft.md); bảng ở mục 3 chỉ điền khi chạy
trên RTL thật.
