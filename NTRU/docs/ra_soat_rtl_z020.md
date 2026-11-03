# Rà soát RTL trên XC7Z020: phần thừa có thể cắt, và phần phải sửa để đạt 200 MHz

> Ngày 03/11/2026. Phân tích, chưa sửa RTL. Đối tượng: bản `experiments/a_cg_z020_dispatch2/rtl/` (`tile_a.sv`,
> `a_cg_fast.sv`, `mul_ss.v`), cùng RTL đã kiểm PQC của `a_cg_cmd_dispatch2`. Số đo: Vivado 2018.1 tổng hợp cho
> `xc7z020clg400-2`, clock 5 ns, báo cáo trong `study/build/a_cg_z020_dispatch2/synth/`. Mục tiêu: **≤ 30 000 LUT** và
> **200 MHz**, giữ NTT hai hệ số mỗi từ (packed16) và mọi hợp đồng số học. Số ghi "ước tính" chưa đo.

## 1. Hiện trạng

| | LUT | FF | LUTRAM | DSP | RAMB18 | WNS nội bộ ở 5 ns |
|---|---:|---:|---:|---:|---:|---:|
| Tổng hợp trên XC7Z020 -2 | 37 841 | 27 397 | 3 236 | 64 | 48 | **−3,604 ns** |
| Cùng thiết kế trên XCZU7EV, tổng hợp | 37 917 | 25 365 | | 64 | 48 | +1,603 ns |
| Cùng thiết kế trên XCZU7EV, sau đặt dây | 37 356 | 25 367 | | 64 | 48 | −0,456 ns |

Chuyển từ UltraScale+ sang 7-series làm chậm khoảng 1,6–2 lần trên mỗi chuỗi nhớ và mỗi tầng LUT. Quy tắc thực tế cho
200 MHz trên XC7Z020 -2: **mỗi tầng thanh ghi chứa tối đa một chuỗi cộng 32 bit cộng 2–3 tầng LUT**. Đường hiện tại có
11 khối CARRY4 nối tiếp và 19 tầng logic.

### Tài nguyên theo khối (tổng hợp XC7Z020)

| Khối | LUT | FF | LUTRAM | Ghi chú |
|---|---:|---:|---:|---|
| 16 tile | 31 780 | 24 197 | 2 496 | ~1 986 mỗi tile |
| — logic cấp tile (máy FFT, đường NTT, đầu ra) | 16 745 | 19 666 | 2 496 | ~1 047 mỗi tile |
| — bộ cộng/trừ modulo `u_as` | 7 903 | 0 | 0 | **494 mỗi tile** (đã gộp bộ chọn toán hạng và bộ +1) |
| — 4 lá nhân và bộ ghép 32×32 | 5 011 | 3 936 | 0 | 313 mỗi tile |
| — bộ cộng/trừ FFT CT tách riêng `u_fft_ct` | 1 040 | 0 | 0 | 65 mỗi tile |
| — đường trễ | 1 081 | 595 | 0 | |
| Logic cấp lõi `a_cg_exec` | 6 039 | 2 385 | 0 | địa chỉ bank, dữ liệu ghi, host, chương trình FFT |
| Vỏ lệnh hai tầng thanh ghi | ~20 | ~815 | 0 | |

## 2. Timing: năm nhóm đường vi phạm

Lấy từ checkpoint, mỗi chân đích một đường xấu nhất, gom theo họ thanh ghi (6 828 chân đích âm):

| Nhóm | Slack xấu nhất | Số đích | Nguyên nhân trong RTL |
|---|---:|---:|---|
| T1. Tầng vào của tile: `rdat` → `u_as` → `s1`, `a1`, `rd`, `nhp0`, cờ nhớ | −3,60 | ~3 100 | Trong một chu kỳ: bộ +1 32 bit (`native_xinc`, làm tròn NTRUGen) → bộ chọn toán hạng theo chiều → x ± y → trừ q ở 16 bit thấp rồi 16 bit cao (nhớ qua bit 16 vì packed16) → chọn → bộ chọn đích |
| T2. Chương trình FFT dùng chung → lá nhân: `program_delay` → DSP cổng A/B | −2,54 | ~1 800 | `program_start` là mux theo `fmt`/`native64` → `prog_step` → bảng `wtab` → đọc LUTRAM `wmx`/`wmw`/`wmsx`/`wmsw` → mux `A32`/`B32` → DSP, phát tới 16 tile không có thanh ghi cục bộ |
| T3. Địa chỉ và dữ liệu bank: `beat`, `fmt`, `rowlog`, `stage_idx` → BRAM | −2,42 | ~1 900 | `rd_row` = dịch theo `rowlog` + cộng + mux mỗi chu kỳ; `rt_addr` = cộng + dịch theo `fmt`; `fmt` (tĩnh) quạt ra 1 344 đích |
| T4. Bản đồ host: `hmin_eff` → `host_map.row_q` | −2,45 | 32 | Trạng thái HPREP tính dịch, mask, cơ sở bank/hàng từ cấu hình trong một chu kỳ |
| T5. Điều khiển: `read_gap` → `k`/`beat`, `state` → `cfg_ready` | −0,47 | ~30 | So `stage_elapsed == read_gap − 1` (trừ 16 bit rồi so), giải mã trạng thái ra cổng |

Kiểm thêm: đường CT ở đầu ra (kết quả nhân → `u_as` → `rd`) cũng −3,46 ns. Nguyên nhân là bộ +1 nằm trong nón đầu vào
`a` của `u_as` ở mọi chiều (`native_xcarry` → `native_xinc` → mux → `u_as`), nên sửa T1 cũng sửa luôn đường này.

### Cách sửa từ RTL

**T1 — tầng vào của tile (quan trọng nhất).**
1. **Đưa bộ +1 ra trước thanh ghi vào.** Tính `x + 1` (và cờ nhớ giữa các phần `native_xcarry`) ở phía `req_data` → `rdat`,
   dùng bộ đếm nhịp lúc nhận (`wbf`) thay cho `wbi`. `rdat` khi đó đã giữ x đã cộng. Bỏ được một chuỗi 32 bit (~1,3 ns),
   không tốn LUT, không đổi độ trễ.
2. **Tính tổng và tổng đã hiệu chỉnh song song, không nối tiếp.** Hiện `sql`/`sqh` lấy `sum` làm đầu vào. Viết
   `s − q = a + b + ~q + 1` thành phép cộng ba toán hạng (Vivado 7-series ánh xạ cộng ba toán hạng thành một chuỗi
   LUT6 + CARRY4), tương tự `d + q = a − b + q`. Dấu của chuỗi hiệu chỉnh chọn kết quả. Bỏ một chuỗi 32 bit (~1,5 ns),
   LUT gần như không đổi.
3. **Bỏ phụ thuộc nhớ thấp → cao ở bit 16.** Packed16 cắt nhớ ở bit 16 bằng mux trên cờ nhớ, nên Vivado tách thành hai chuỗi
   nối tiếp có LUT ở giữa. Dùng một bit chặn ở vị trí 16 (toán hạng mở rộng 33 bit: bit chặn = 0/0 để cắt khi packed16,
   1/0 để chuyền nhớ khi không), cho một chuỗi liền. Hoặc chọn nhớ (tính nửa cao cho cả nhớ vào 0 và 1). Giữ nguyên số
   học packed16.
4. Ước tính sau 1–3: còn một chuỗi 32 bit + 3–4 tầng LUT, khoảng 4,0–4,5 ns, slack tổng hợp −0,1 .. +0,6 ns. Nếu sau
   đặt dây vẫn thiếu: thêm một thanh ghi sau `u_as`, trước bộ chọn đích `s1`/`a1`/`rd`/`nhp0`. Đường CT và GS phải
   cùng thêm để độ trễ không phụ thuộc chiều; độ trễ tile tăng 1 và lịch lõi phải cập nhật.

**T2 — chương trình FFT.**
1. Lấy `program_start` từ nhánh `program_delay` sớm hơn một nhịp, rồi đăng ký `prog_valid`, `prog_product`, `prog_step`,
   `prog_mask`. Độ trễ không đổi, đường dài bị cắt đôi.
2. Đặt một bản sao thanh ghi của các tín hiệu này trong mỗi tile (như `reset_local`), để không còn quạt ra 16 tile qua
   logic.
3. Trong tile, tính trước địa chỉ LUTRAM (`wadr`/`sadr` của bước kế) vào thanh ghi; đọc LUTRAM ở địa chỉ đã đăng ký rồi
   qua một mux vào DSP. Thêm ~130 FF toàn lõi, LUT không đổi.

**T3 — địa chỉ bank.**
1. Tính `rd_row`, `wr_row`, `rt_addr` của lần phát kế tiếp ngay trong khối cập nhật `k`/`beat`/`part`, lưu thanh ghi,
   đưa thẳng vào BRAM.
2. Các phần cố định mỗi tầng (`rd_plane_base` theo plane, `far_y_offset`, `<< rowlog`, chọn bộ đệm) tính một lần ở
   trạng thái STAGE.
3. Thay `fmt`, `fft`, `read_near`, `write_far` ở đường dữ liệu bằng các cờ đã giải mã sẵn lúc cấu hình, nhân bản theo
   nhóm bank để giảm quạt ra. LUT có thể giảm vì bỏ các bộ dịch theo `rowlog` khỏi đường mỗi chu kỳ.

**T4 — bản đồ host.** Tính các giá trị chỉ phụ thuộc cấu hình (`host_pack`, `pmask`, `job_bank_shift`, các vectơ cơ sở
bank/hàng/pha) ở các nhịp CFG, lưu thanh ghi. HPREP chỉ còn dịch dòng và XOR.

**T5 — điều khiển.** Lưu `read_gap − 1` khi nạp mô tả tầng, chỉ so bằng. Đăng ký `cfg_ready`/`read_ready`/`load_ready`
(hoặc giải mã từ thanh ghi one-hot của trạng thái).

## 3. Phần thừa có thể cắt để giảm LUT

| # | Phần | Chi phí hiện tại | Đề xuất | Tiết kiệm (ước tính) | Cái giá | Độ tin |
|---|---|---:|---|---:|---|---|
| R1 | Chia làm tròn `div2e` trong mỗi tile: 2 bộ cộng làm tròn `ry0`/`ry1`, 2 bộ dịch 64→32 theo `shift_r`, thanh ghi phần trước/sau `wy*p`, chọn `fh`/`fl`, logic `wo2`/`wx2` | ước tính 200–350 LUT mỗi tile | **Làm `div2e` ở đường đọc host.** Dữ liệu cuối giữ chưa chia trong RAM (W bit đủ chỗ); 4 làn ở cổng đọc 128 bit (mỗi làn cộng làm tròn có nhớ giữa các phần trong dòng và dịch). Kết quả bit-exact giống hệt vì `div2e` là phép cuối cùng. | **3 000 .. 5 000** | Đổi hợp đồng tile (`req_sign` FFT) và lõi; cần chắc host luôn đọc kết quả ra (không có lệnh lõi dùng tiếp dữ liệu đã chia); đường xuất tile ngắn hơn, có lợi cho timing | trung bình |
| R2 | Cổng host: mux đọc 32→1 cho mỗi từ (4 × 32 bit), mux ghi 4→1 và so 4 chỉ số bank ở mỗi bank | ước tính 2 000 .. 2 500 | Đi qua mạng sẵn có, hoặc giới hạn mỗi từ host chỉ tới một nhóm 8 bank theo cấu trúc bản đồ; hoặc host 32 bit mỗi chu kỳ | 1 000 .. 2 000 | Băng thông nạp/đọc host giảm nếu thu hẹp | trung bình |
| R3 | Bộ cộng/trừ FFT CT tách riêng `u_fft_ct` | 1 040 | Dùng lại đường "plain" của `u_as` (đã có `side_t` và `t5` ở đầu vào khi `mf`) | 800 .. 1 000 | Bản này được chọn có chủ ý ("exact separated FFT post-adder"); phải tìm lại lý do (timing trên ZU7EV hay lỗi nhớ) trước khi gộp | trung bình |
| R4 | Bộ ghép 32×32 của 4 lá: cộng ba toán hạng 65 bit bằng LUT (`cat + p2r<<16 + p3r<<16`) | ước tính 100–130 LUT mỗi tile | Viết theo mẫu `a*b + c` có thanh ghi để Vivado dùng bộ cộng sau nhân của DSP48E1 (chuỗi PCIN) | 0 .. 2 000 | Lá tách 16 bit (không phải 17) và packed16 cần hai tích độc lập: chưa chắc suy ra được bằng RTL chung | thấp |
| R5 | Dữ liệu ghi mỗi bank: mux tiến/lùi/host 32 bit × 32 bank; tính `wr_row`/`rd_row` riêng từng bank dù chỉ phụ thuộc `b >> 4` | ước tính 2 000 .. 2 500 | Tính hàng hai lần (nửa dưới, nửa trên) dùng chung; host đi qua cùng mux của mạng | 0 .. 600 | Vivado có thể đã gộp biểu thức trùng | thấp |
| — | Hai khe modulus (`q1`, `qi1`, đường khe), `TREN_MANG = 3`, `EN_REG`, móc lỗi | ~0 | Dọn mã; lõi buộc khe = 0 nên Vivado đã bỏ | 0 | — | — |
| — | Vỏ lệnh hai tầng `p_*`/`q_*` có DONT_TOUCH | ~815 FF, ~0 LUT | Giữ (chỉ FF) | 0 | — | — |

Không cắt: NTT hai hệ số mỗi từ (giữ theo yêu cầu); đường làm tròn NTRUGen (`native64`, cần để khớp bit NTRUGen); bộ
nhớ trạng thái FFT (đã đóng gói 16/8 theo phân tích liveness).

**Cộng lại:** R1 + R2 + R3 ≈ 4 800 .. 8 000 LUT; thêm R4/R5 nếu đo ra có lợi. Mục tiêu 30k cần giảm 7 841. Chỉ R1 đến R3 ở
đầu cao mới đủ, nên R1 là khoản quyết định.

## 4. Thứ tự đề xuất và cách đo

Gom thành hai đợt tổng hợp, mỗi đợt mô phỏng đủ trước (theo cách làm đã thống nhất: mô phỏng, gom, đo một lần):

1. **Đợt timing** (không đổi hợp đồng, không đổi độ trễ): T1.1–T1.3, T2, T3, T4, T5. Chạy lại bộ kiểm số học (1 026 ca,
   PQC C) rồi tổng hợp một lần trên XC7Z020. Kỳ vọng: WNS tổng hợp ≥ 0; LUT thay đổi trong ±500.
2. **Đợt tài nguyên**: R3 (nhỏ, cần lý do lịch sử trước), R1 (đổi hợp đồng: cần anh duyệt), R2. Tổng hợp một lần.
   Kỳ vọng: 30 000 .. 33 000 LUT.
3. Chỉ khi cả hai đợt đạt mới chạy đặt dây một lần trên XC7Z020.

## 5. Câu hỏi cần anh quyết

1. R1 đổi hợp đồng: tile không còn chia `div2e`, việc chia chuyển sang đường đọc host. Có chấp nhận không?
2. Nếu T1 sau đặt dây vẫn thiếu: có chấp nhận thêm một chu kỳ độ trễ tile (lịch lõi cập nhật, số chu kỳ mỗi lệnh tăng rất
   ít) không?

## 6. Rà soát lần 2 (03/11/2026, sau đợt timing và +1 độ trễ)

Bản đo: `experiments/a_cg_z020_lat1` trên XC7Z020, 40 790 LUT, WNS −1,018 ns. Cách đo: mỗi ô logic trong netlist sau tổng
hợp được quy về tín hiệu RTL mà nó điều khiển (tên ô của Vivado), cho tile 1 và cho phần logic cấp lõi; so cùng cách với
bản gốc `a_cg_z020_dispatch2`. Số dưới đây là số ô LUT logic; LUTRAM tính riêng. Vivado có thể đặt logic của lõi vào trong
tile (ví dụ dữ liệu ghi bank), bảng ghi rõ chỗ đó.

### 6.1 Một tile: 2 012 LUT logic, ~200 LUTRAM

| Khối | LUT | Tỉ lệ | Dùng khi |
|---|---:|---:|---|
| FFT: tích từng phần, cộng dồn, T, tổng 3M, làm tròn, trạng thái phần (kèm 387 ô LUTRAM) | 590 | 29 % | chỉ FFT |
| Tầng ra: chọn 64 bit giữa các chế độ, dịch `div2e`, đổi cặp packed16 | 371 | 18 % | mọi chế độ; dịch `div2e` chỉ ở tầng cuối FFT ngược |
| Bộ cộng/trừ hai nhịp | 231 | 11 % | mọi chế độ |
| Bốn lá nhân và bộ cộng ghép 32×32 | 218 | 11 % | mọi chế độ |
| Dữ liệu ghi bank (logic của lõi, Vivado đặt vào tile) | 195 | 10 % | mọi chế độ |
| Bộ chọn tầng toán hạng (`a1`, `s1`, `w1`, `g1`) | 182 | 9 % | mọi chế độ |
| Đường FFT ngược NTRUGen (+1, dịch, giữ phần thấp) | 104 | 5 % | chỉ FFT 64 bit ngược NTRUGen |
| Rút gọn Montgomery (u, u − q, kết quả) | ~100 | 5 % | chỉ NTT |

### 6.2 Logic cấp lõi: 8 257 LUT

| Khối | LUT |
|---|---:|
| Bộ chọn dữ liệu, hàng, enable của 32 bank (cộng 195 × 16 nằm trong tile) | 3 182 |
| Mạng đọc: `req_x`/`req_y` 4 nguồn × 64 bit × 16 tile | 1 985 |
| Đọc host: chọn 32→1 cho 4 từ (thêm 512 MUXF7) | 1 156 |
| `row_tab` (thêm ở đợt này) | 646 |
| Điều khiển, bản đồ host, mô tả tầng, chương trình FFT | ~1 300 |

### 6.3 Vấn đề chính, theo mức tài nguyên

1. **Bộ máy FFT nhân 16 và phần lớn thời gian ngồi không.** 590 LUT + ~200 LUTRAM mỗi tile, ~12 000 tổng, là 55 % tile
   nếu tính cả phần dịch ở tầng ra và đường NTRUGen; phần riêng của NTT chỉ ~100 LUT.
   - Ở NTT, toàn bộ khối này không làm gì.
   - Ở FFT 64/128 bit, các bộ cộng chỉ chạy 1/3 và 1/6 số chu kỳ, vì bộ nhân là giới hạn (12 và 45 tích mỗi butterfly).
   Đây là cái giá của "máy nào cũng làm mọi độ rộng"; chia thời gian bộ cộng thì đã đo là không lợi trên FPGA.
2. **Mạng dữ liệu hai chiều và cổng host: ~9 400 LUT (23 %).** Gồm dữ liệu ghi bank 3 182 + 16 × 195, mạng đọc 1 985, đọc
   host 1 156. Đây là khoản lớn thứ hai, lớn hơn mọi khối số học riêng lẻ.
3. **Tầng ra của tile: 371 LUT mỗi tile (~5 900).** Một bộ chọn 64 bit gom 5 nguồn (FFT kèm dịch `div2e`, GS chia đôi, CT
   cộng/trừ, đổi cặp packed16). Hai bộ dịch 64→32 cho `div2e` chỉ dùng ở tầng cuối FFT ngược.
4. **DSP48E1 chỉ dùng bộ nhân.** Bộ cộng sau nhân (48 bit) và chuỗi nối tầng giữa các DSP không dùng. Bộ cộng ghép 32×32
   (65 bit, ba toán hạng) và bộ cộng dồn FFT 68 bit nằm trong LUT, ~150 LUT mỗi tile (~2 400). Hai trong bốn lá không đưa
   được thanh ghi vào trong DSP (AREG/BREG = 0).
5. **Phép tính địa chỉ dùng bộ cộng ở chỗ các trường không bao giờ chồng nhau.** Hàng bank = bộ đệm | plane | phần theo k:
   - plane < số plane, phần theo k < số hàng một plane;
   - phần lệch xa `k/2 + far` cũng là ghép bit, vì `k/2 < far`;
   - mọi kích thước đều là lũy thừa 2.

   Vì vậy phép cộng có thể thay bằng phép OR (ghép bit): không có chuỗi nhớ, và chỉ cần tính một lần cho mỗi nửa bank. Đợt
   vừa rồi làm ngược lại:
   - `row_tab` 646 LUT;
   - bộ chọn 8→1 lặp lại ở cả 32 bank, +784 LUT;
   - `desc_nx` và `read_gap_m1` ~250 LUT.

   Tổng ~1 700 LUT, và cũng chính là các đường còn trượt timing (bảng plane → hàng bank, cập nhật `row_tab`).
6. **Đường chọn dữ liệu ghi theo `logm`** (1 517 đích, −0,72 ns): bit đổi chỗ `(out_k >> (logm − 6)) & 1` dịch theo cấu
   hình ở mỗi chu kỳ. Một mặt nạ một-bit đăng ký sẵn theo lệnh là đủ.

### 6.4 Đợt tiếp theo đề xuất

Không đổi hợp đồng, không đổi số chu kỳ:
1. Hàng bank đọc/ghi và hàng host bằng ghép bit (OR), tính một lần cho mỗi nửa bank. Bỏ `row_tab`; kiểm tra bóng giữ như cũ.
2. Bit đổi chỗ khi ghi bằng mặt nạ đăng ký.

Kỳ vọng (ước tính): lõi −1 500 .. −2 000 LUT, các đường lõi còn trượt về dương ở tổng hợp.

Cần anh duyệt (đổi hợp đồng hoặc giao diện):
3. `div2e` ra khỏi tile, làm ở đường đọc host (mục 3; ước tính −3 000 .. −5 000).
4. Đọc host một từ mỗi chu kỳ thay vì bốn (−~1 000 LUT, băng thông đọc giảm 4 lần).
5. Dùng chuỗi DSP cho bộ ghép 32×32 và bộ cộng dồn FFT (mục 4). Cần thử xem RTL chung có suy ra được không; lá 16 bit
   không khớp phép dịch 17 bit của chuỗi DSP48E1.
