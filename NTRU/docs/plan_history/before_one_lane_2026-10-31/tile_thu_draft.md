# Khối tile thử — bản nháp, số đo đầu tiên (31/10/2026)

**Đây là bản nháp**, viết để có sớm số liệu cho câu hỏi còn mở của giai đoạn 0: rút gọn trên mảng nhân hay bộ rút
gọn riêng. Đây **không** phải RTL nghiệm thu. Bảng kết quả ở
[11_kiem_thu_tile.md](../../spec/FlexTransform/2.0/11_kiem_thu_tile.md) vẫn để "chưa chạy".

> **Cập nhật cùng ngày:** người dùng chọn **rút gọn lai** (biến thể C, mục 6 bên dưới). Giả thuyết 2 được viết lại
> **trước** khi đo biến thể C (bảng "Sửa sau khi khóa" ở mục 6 của kiến trúc). Mục 1–5 là lần đo đầu, so biến thể
> "trên mảng cho mọi modulus" (A) với "rút gọn riêng" (B); ngưỡng nói ở mục 3–4 là ngưỡng cũ.

## 1. Đã làm gì

| Phần | File |
|---|---|
| RTL hai biến thể, chọn bằng tham số `TREN_MANG` (1 = rút gọn trên mảng, 0 = rút gọn riêng), vỏ đo `tile_thu_top` có thanh ghi ở mọi cổng | [hdl/tile_thu/tile_thu.sv](../../hdl/tile_thu/tile_thu.sv) |
| Testbench đọc file vector, chờ rảnh rồi ghi hằng số trước mỗi nhóm, kiểm thứ tự, nhãn, độ trễ, tốc độ | [sim/tile_thu/tb_tile_thu.sv](../../sim/tile_thu/tb_tile_thu.sv) |
| Chạy toàn bộ kiểm thử bản nháp | [sim/tile_thu/run.sh](../../sim/tile_thu/run.sh) |
| Tổng hợp, đặt, đi dây trên Vivado | [fpga/zcu106/tile_thu.tcl](../../fpga/zcu106/tile_thu.tcl) |

Cách làm chính:
- Cả hai biến thể dùng chung 4 bộ nhân 16×16 (`mul_ss`), cùng phần butterfly (cộng/trừ modulo, chia đôi), cùng
  vỏ đo. Chỉ khác phần rút gọn.
- **Trên mảng:** mỗi phép nhân modulo đi qua bộ nhân ba lượt: T = a·w, m = T_thấp·q′, rồi m·q. Ở lane 16 bit, mỗi bộ
  nhân là một "máy" riêng. Ở lane 32 bit, 4 bộ nhân ghép thành một bộ 32×32. Ngoài 4 bộ nhân này không có phép nhân
  nào khác.
- **Rút gọn riêng:** bộ nhân chỉ tính T. Có thêm 4 bộ rút gọn hằng cho 3329/12289 (cộng và dịch, cùng công thức với
  lõi cũ), và 1 bộ Montgomery 32 bit tổng quát viết bằng phép nhân hành vi.
- **Lịch phát tĩnh:** mỗi máy nhận một phép mới sau mỗi P chu kỳ (P = 3 trên mảng, 1 rút gọn riêng). Lượt T, m, m·q
  được chọn bằng bit hợp lệ đã trễ, nên không bao giờ tranh bộ nhân. Mọi thanh ghi đứng yên khi `en = 0`.
- Một sửa sau lần đo đầu: chế độ và hướng được chốt vào thanh ghi lúc rảnh. Request khác chế độ đang chốt thì phải
  chờ, đúng như mục 4.2 của hợp đồng cho phép. Lý do: ở lần đo đầu, đường tới hạn của cả hai biến thể đi từ bộ đếm
  request đang chạy, không liên quan tới phần rút gọn.

## 2. Kết quả chức năng (Icarus Verilog 14)

| Kiểm thử | Trên mảng | Rút gọn riêng |
|---|---|---|
| `raw32` (2 320), `fft32` (1 842), `ntt16_pqc` (2 814), `ntt32` (11 263) | 0 sai | 0 sai |
| `ntt16_q_khac` (3 864; q = 3, 7681, 65521) | 0 sai | không áp dụng |
| Dừng chung: `en = 0` ngẫu nhiên 10%; 30% kèm các đợt dừng dài tới 64 chu kỳ | 0 sai | 0 sai |
| Request thưa (`req_valid = 0` với xác suất 50%) | 0 sai | 0 sai |
| Thứ tự và nhãn (nhãn tăng dần quay vòng) | đúng | đúng |
| Độ trễ cố định: mọi request cùng chế độ có cùng độ trễ | đúng | đúng |
| Tốc độ bền vững: mỗi nhóm lặp 6 lần, tức 1 170–1 758 request mỗi nhóm | ≥ 99,9% bảng | ≥ 99,9% bảng |

Tổng: 38 lần chạy đều đạt. Vector có hash manifest `0009f5da6e2c83ca…`.

**Độ trễ** (số chu kỳ có `en = 1`, từ lúc nhận request tới lúc phát kết quả):

| Chế độ | Lane | Trên mảng | Rút gọn riêng |
|---|---|---:|---:|
| 0, 1 | — | 6 | 6 |
| 2 | 16 | 16 | 10 |
| 3 | 16 | 31 | 19 |
| 4 | 16 | 16 | 10 |
| 2 | 32 | 33 | 19 |
| 3 | 32 | 57 | 35 |
| 4 | 32 | 27 | 17 |

**Tốc độ đo được** (request/chu kỳ):
- Trên mảng: 0,3335 (chế độ 2 và 3, lane 16); 0,6667 (chế độ 4, lane 16); 0,0834 (chế độ 2 và 3, lane 32);
  0,1667 (chế độ 4, lane 32).
- Rút gọn riêng: 1; 0,2501; 0,5001.

Tất cả khớp bảng ở mục 6 của hợp đồng.

**Bổ sung sau (cùng ngày), chạy trên biến thể C và B** (`sh sim/tile_thu/run.sh`, cách làm ở mục 5 của
[11_kiem_thu_tile.md](../../spec/FlexTransform/2.0/11_kiem_thu_tile.md)):

| Case | C (lai) | B (rút gọn riêng) |
|---|---|---|
| Đầu ra đứng yên khi `en = 0` (kiểm trong mọi lần chạy) | đạt | đạt |
| Chuỗi đổi chế độ và hằng số (6 đoạn), kể cả khi dừng và request thưa | đạt | đạt |
| Ghi hằng số lúc đang chạy (`cfg_we = 1` mọi chu kỳ bận, hằng số ngẫu nhiên) | đạt | đạt |
| Reset giữa chừng, rồi chạy lại nhóm | đạt | đạt |
| Lịch không phụ thuộc dữ liệu (dữ liệu 0 so với dữ liệu thật, từ reset) | đạt | đạt |
| 7 lỗi cài vào (5 lỗi RTL × 2 file vector, sửa giá trị mong đợi, đổi chỗ kết quả) | bắt được cả 12 | bắt được cả 12 |

Tổng: 76 lần chạy đạt, 24 lần chạy lỗi đều bị bắt (`sim/tile_thu/build/regression.log`). Hai lỗi đầu của phép kiểm
lịch là lỗi testbench, đã sửa: hai lượt phải bắt đầu từ reset và cùng giá trị `req_mode`, vì bộ đếm khe chạy tự do.
Chưa kiểm được "hằng số bằng 0 sau reset" từ cổng.

## 3. Số đo Vivado (sau route)

Vivado **2018.1** (bản duy nhất có trên máy), `xczu7ev-ffvc1156-2-e`, `out_of_context`, cài đặt mặc định, clock 3,0
ns. Số dưới đây gồm cả vỏ đo.

| Số liệu | Trên mảng | Rút gọn riêng | Tỉ lệ |
|---|---:|---:|---:|
| LUT | 3 654 | 3 907 | **0,935** (−6,5%) |
| trong đó LUT làm SRL | 222 | 181 | |
| FF | 2 851 | 2 916 | 0,978 |
| DSP | 4 | 11 | **0,36** |
| BRAM / URAM | 0 / 0 | 0 / 0 | |
| WNS ở 3,0 ns | −0,151 ns | −0,266 ns | |
| Fmax | 317 MHz | 306 MHz | 1,04 |

**Cách đọc theo ngưỡng đã khóa của giả thuyết 2:**
- LUT giảm 6,5%. Con số này nằm giữa ngưỡng "đạt" (≥ 10%) và ngưỡng "bác bỏ" (< 5%), nên **chưa kết luận được**.
- DSP giảm từ 11 xuống 4: đạt điều kiện "DSP không tăng", và giảm mạnh. Vivado đặt bộ Montgomery 32 bit của bản rút
  gọn riêng lên 7 DSP.
- Fmax không giảm, thậm chí cao hơn 4%: đạt. Đường tới hạn của cả hai bản nằm ở phần chọn toán hạng butterfly 32 bit
  dùng chung, không ở phần rút gọn. Vì vậy Fmax ở đây chưa nói gì về phép rút gọn.

**Phần chênh nằm ở đâu** (báo cáo theo khối, cùng lần route):

| Phần | Trên mảng | Rút gọn riêng | Chênh |
|---|---:|---:|---:|
| Ngoài 4 làn butterfly: bộ nhân, máy rút gọn, chọn toán hạng bộ nhân, hàng trễ T, cùng phần dùng chung như thanh ghi giữ request lane 32, bộ gom kết quả, bộ đếm, thanh ghi hằng số | 764 | 1 187 | −423 |
| 4 làn butterfly (gồm logic chọn request mà Vivado gộp vào làn 0) | 2 882 | 2 713 | +169 |

- Phần rút gọn trên mảng rẻ hơn khoảng 420 LUT và 7 DSP. Chỉ phần chênh là chắc chắn; hai con số 764 và 1 187 còn
  gồm logic dùng chung, nên không chia thành phần trăm.
- Đổi lại, làn butterfly phải giữ dữ liệu phụ lâu hơn vì độ trễ dài hơn, tốn thêm khoảng 170 LUT.
- Phần dùng chung chiếm khoảng 75% LUT của tile. Riêng làn butterfly 32 bit là 2 200 LUT; tổng hợp riêng nó chỉ khoảng
  800 LUT. Phần còn lại là logic chọn request và xếp lịch lane 32 bit của bản nháp, chưa tối ưu. Phần dùng chung càng
  lớn thì tỉ lệ cả tile càng gần 1.

FF trên mảng không nhiều hơn bản rút gọn riêng. Mô hình dự báo khoảng 180 bit/tile phải giữ thêm, nhưng bản rút gọn
riêng cũng tốn FF cho pipeline của chính bộ rút gọn. Hai khoản này gần bù nhau.

## 4. Kết luận tạm

1. Rút gọn trên mảng **chạy đúng** ở mọi chế độ, đúng tốc độ thiết kế, và không làm chậm clock.
2. Về tài nguyên:
   - phần rút gọn nhỏ hơn rõ rệt: −423 LUT, −7 DSP;
   - cả tile chỉ nhỏ hơn 6,5% LUT, chưa qua ngưỡng 10%. Lý do là phần dùng chung của bản nháp lớn.
3. Kết quả cuối phụ thuộc vào kích thước phần dùng chung trong RTL thật, tức bản bạn viết. Ước lượng thô, không phải
   số đo: dù phần dùng chung gọn hơn, tỉ lệ vẫn chỉ quanh **0,90**, tức đúng sát ngưỡng 10%, chưa vượt qua.
   - Nếu bỏ khoảng 1 400 LUT logic chọn request khỏi cả hai bản: (3 654 − 1 400) / (3 907 − 1 400) ≈ 0,90.
   - Nếu phần dùng chung còn 1 500 LUT và vẫn tính 169 LUT làn butterfly mà bản trên mảng tốn thêm:
     (764 + 169 + 1 500) / (1 187 + 1 500) ≈ 0,91.
4. Giả thuyết 2 đã có sẵn hai điều kiện ngoài LUT: "DSP không tăng" và "Fmax giảm ≤ 10%". Bản nháp đạt cả hai.
   Mức tiết kiệm DSP (7 mỗi tile, khoảng 112 với 16 tile) chỉ là nhận xét. Đổi nó thành tiêu chí đạt là quyết định của
   bạn. Nếu đổi, đó là sửa ngưỡng **sau khi đã có số đo**, và phải ghi rõ theo quy tắc ở mục 6 của kiến trúc.

## 5. Tái lập

```text
sh sim/tile_thu/run.sh                     # 38 lần chạy, kết quả ở sim/tile_thu/build/regression.log
vivado -mode batch -source fpga/zcu106/tile_thu.tcl -tclargs 1   # trên mảng
vivado -mode batch -source fpga/zcu106/tile_thu.tcl -tclargs 0   # rút gọn riêng
```

Báo cáo ở `study/build/tile_thu_<biến thể>/`. Lần đo đầu, trước khi chốt chế độ vào thanh ghi, nằm ở
`study/build/tile_thu_<biến thể>_v1/`: LUT 3 645 / 3 917, Fmax 266 / 294 MHz. Ở lần đó, đường tới hạn đi qua bộ đếm
request.

Hash SHA-256 (16 ký tự đầu): RTL `13bd10ebd865333c`, testbench `84bf6e639b1eb02d`.

## 6. Biến thể C: rút gọn lai (thiết kế của v1)

`TREN_MANG = 2`: lane 16 bit dùng bộ rút gọn hằng như B, lane 32 bit rút gọn trên mảng như A. Cùng RTL, cùng testbench,
cùng script. B được tổng hợp lại từ đúng bản RTL này để hai bên so cùng nguồn (hash RTL 16 ký tự đầu
`dc02fb4dd4dfb274`).

**Chức năng:** toàn bộ vector, dừng chung, request thưa và tốc độ đều đạt (xem `sim/tile_thu/build/regression.log`).
Tốc độ lane 16 bit là 1 request/chu kỳ ở mọi chế độ; lane 32 bit là 1/12 và 1/6 như A. Độ trễ: lane 16 bit như B
(10 / 19 / 10), lane 32 bit như A (33 / 57 / 27).

**Vivado 2018.1, sau route, 3,0 ns:**

| Số liệu | C (lai) | B (rút gọn riêng) | C so với B |
|---|---:|---:|---:|
| LUT | 4 002 | 3 923 | +2,0% |
| FF | 2 964 | 2 917 | +1,6% |
| DSP | 4 | 11 | −7 |
| BRAM / URAM | 0 / 0 | 0 / 0 | |
| WNS | −0,909 ns | −0,223 ns | |
| Fmax | 256 MHz | 310 MHz | −17,6% |

**Đối chiếu ngưỡng giả thuyết 2 mới** (đặt trước lần đo này):

| Điều kiện | Ngưỡng đạt | Bản nháp | |
|---|---|---|---|
| DSP | ít hơn ≥ 4 mỗi tile | ít hơn 7 | đạt |
| LUT | tăng ≤ 5% | tăng 2,0% | đạt |
| Fmax | giảm ≤ 10% | giảm 17,6% | **không đạt** |

Không chạm điều kiện bác bỏ nào (DSP giảm < 2, LUT tăng > 10%, chậm > 4 lần). Kết quả: **chưa kết luận**, vì Fmax.

**Vì sao Fmax chưa nói lên điều gì về phép rút gọn:**
- Cả 10 đường xấu nhất của **cả hai** biến thể đều kết thúc ở cùng một chỗ: đầu vào hàng trễ dữ liệu phụ của làn
  butterfly 32 bit. Đường bắt đầu từ thanh ghi chế độ của request, đi qua logic chọn request và phép cộng/trừ trước
  butterfly. Đây là phần dùng chung, giống hệt nhau ở hai biến thể.
- Ở C, đường này có 10 tầng logic và 77% thời gian là dây nối (B: 65%). **Chưa giải thích được** vì sao C chậm hơn:
  A có cùng các mux đưa toán hạng vào bộ nhân của lane 32 bit (và thêm mux của lane 16 bit), mà vẫn đạt 317 MHz trên
  cùng loại đường.
- Chạy lại C lần hai với cùng mã và cùng cài đặt cho kết quả giống hệt (LUT 4 002, WNS −0,909 ns): Vivado tất định
  với cùng đầu vào, nên khoảng chênh không phải nhiễu giữa các lần chạy. Chênh 0,4% LUT / 1% Fmax của B giữa lần 2 và
  lần 3 đến từ việc mã RTL đã được sắp lại (cùng logic).
- Vì vậy con số −17,6% là số đo thật của bản nháp, nhưng bản nháp **không quyết định được** điều kiện Fmax. RTL thật
  cần thêm thanh ghi ở đường request → butterfly; thêm thì phải thêm cho **cả hai** biến thể, rồi đo lại.

**Cái giá ở cấp lõi mà tile không thấy:** với C, NTT 16 bit chạy 64 butterfly mỗi chu kỳ thay vì 21,3, nên ngân hàng cộng
dùng chung của lõi cần khoảng 5 730 bit cộng thay vì khoảng 2 830 (kiến trúc mục 3.1b). Bản nháp tile cho mọi biến thể
đủ phần butterfly cho tốc độ tối đa, nên không thấy khoản này. So A với C ở cấp lõi phải đo khi có lõi.

**Ba biến thể cạnh nhau** (cùng script; A từ lần đo 2, B và C từ lần đo 3 trên cùng RTL; B ở lần 2 là 3 907 LUT,
306 MHz, tức chênh giữa hai lần chạy cỡ 0,4% LUT và 1% Fmax):

| | A: trên mảng mọi modulus | C: lai | B: rút gọn riêng |
|---|---:|---:|---:|
| LUT | 3 654 | 4 002 | 3 923 |
| DSP | 4 | 4 | 11 |
| Fmax | 317 MHz | 256 MHz | 310 MHz |
| NTT 16 bit (request/chu kỳ, chế độ 3) | 1/3 | 1 | 1 |
| NTT 32 bit (request/chu kỳ, chế độ 3) | 1/12 | 1/12 | 1/4 |

> **Cập nhật:** khoảng chênh Fmax ở trên đã tìm ra nguyên nhân và đã sửa, xem mục 7.

## 7. Sửa đường bắt tay, đo lại C và B

**Nguyên nhân.** Bản nháp dùng tín hiệu nhận request (`fire = en && req_valid && req_ready`) làm điều kiện chọn toán hạng
đưa vào butterfly. Vì vậy, trong cùng một chu kỳ có: quyết định nhận request (so `req_mode` với chế độ đã chốt, xét bộ đếm
khe), mux chọn toán hạng (net fanout 90), rồi phép cộng/trừ mod q 32 bit trước butterfly. Ở B cả hai engine có chu kỳ 1,
nên bộ đếm khe `ph` luôn bằng 0 và Vivado rút gọn hết. Ở C, lane 32 bit có chu kỳ 3, nên `ph` và `lane32` là logic thật
trong `req_ready`, nằm nối tiếp trên đường dài nhất. Đây là cơ chế đọc từ RTL và báo cáo timing; bằng chứng là một lần sửa
chung đưa C từ 256 lên 327 MHz. Chưa đo riêng phần đóng góp của `ph`.

**Cách sửa** (giống nhau cho mọi biến thể, không thêm chu kỳ trễ): toán hạng chỉ được chọn theo chế độ và khe đã chốt;
`fire` và các bit hợp lệ của lane 32 bit (`Rv`, `pv`, `av`) chỉ quyết định bit hợp lệ. Lần sửa thứ nhất chỉ bỏ `fire`;
khi đó C lên 327 MHz nhưng B tụt xuống 278 MHz vì đường dài nhất của B chuyển sang `av` → mux toán hạng → trừ mod q.
Lần sửa thứ hai bỏ nốt các bit hợp lệ khỏi mux. Dừng sửa ở đây: sửa tiếp theo đường xấu nhất của từng biến thể là chỉnh
về đáp án.

**Quy tắc cho RTL thật:** tín hiệu bắt tay chỉ điều khiển bit hợp lệ, không tham gia chọn dữ liệu. Quan trọng hơn ở C vì
có bộ đếm khe chu kỳ 3.

Hash RTL 16 ký tự đầu `63acc723c4374682`, testbench `cc85aa9417c0ff92`. Regression đầy đủ sau sửa: 76 lần chạy đạt,
24/24 lỗi cài vào bị bắt.

**Vivado 2018.1, sau route, 3,0 ns, cài đặt mặc định** (đúng thủ tục của hợp đồng tile mục 8):

| Số liệu | C (lai) | B (rút gọn riêng) | C so với B |
|---|---:|---:|---:|
| LUT | 4 014 | 3 948 | +1,7% |
| FF | 2 975 | 2 926 | +1,7% |
| DSP | 4 | 11 | −7 |
| BRAM / URAM | 0 / 0 | 0 / 0 | |
| WNS | −0,163 ns | −0,172 ns | |
| Fmax | 316 MHz | 315 MHz | +0,3% |

| Điều kiện giả thuyết 2 | Ngưỡng đạt | Bản nháp sau sửa | |
|---|---|---|---|
| DSP | ít hơn ≥ 4 mỗi tile | ít hơn 7 | đạt |
| LUT | tăng ≤ 5% | tăng 1,7% | đạt |
| Fmax | giảm ≤ 10% | không giảm | đạt |
| NTT 32 bit | chậm ≤ 3,5 lần | chậm 3 lần | đạt |

Đây vẫn là chỉ dấu từ bản nháp; bảng nghiệm thu của spec 11 chờ RTL thật.

**Độ dao động theo chiến lược đặt cell** (chỉ để biết khoảng nhiễu, không dùng làm số của giả thuyết 2):

| Chiến lược `place_design` | C: LUT | C: Fmax | B: LUT | B: Fmax |
|---|---:|---:|---:|---:|
| Mặc định | 4 014 | 316 MHz | 3 948 | 315 MHz |
| `Explore` | 4 019 | 325 MHz | 3 947 | 310 MHz |
| `ExtraNetDelay_high` | 4 027 | ≥ 333 MHz (đạt 3,0 ns, WNS +0,064) | 3 955 | 313 MHz |
| `AltSpreadLogic_high` | 4 019 | 318 MHz | 3 944 | 322 MHz |

FF không đổi giữa các chiến lược (C 2 975, B 2 926); DSP 4 và 11. Khoảng dao động: C 316 đến ≥ 333 MHz, B 310 đến
322 MHz.

Khoảng dao động giữa các chiến lược lớn hơn khoảng chênh C/B ở cài đặt mặc định. Khi WNS dương, Vivado dừng tối ưu, nên
Fmax chỉ là cận dưới.

Báo cáo ở `study/build/tile_thu_4lan/tile_thu_<biến thể>[_<chiến lược>]/` (chuyển vào đó khi đổi sang tile một làn, mục
9); báo cáo trước khi sửa ở `study/build/tile_thu_2_r2`, `tile_thu_0_r3`, sau lần sửa thứ nhất ở `tile_thu_2_f1`,
`tile_thu_0_f1`; bản RTL trước khi sửa ở `study/build/tile_thu_before_fire_fix.sv`, bản RTL và testbench của mục 7–8 ở
`study/build/tile_thu_4lan.sv`, `study/build/tb_tile_thu_4lan.sv`.

## 8. Vì sao một tile tốn khoảng 4 000 LUT

**Cách đo.** Tổng hợp riêng (không place/route), giữ nguyên phân cấp (`-flatten_hierarchy none`) để logic nằm ở khối sở
hữu nó trong RTL. Script `fpga/zcu106/tile_thu_breakdown.tcl` và `fpga/zcu106/tile_thu_glue.tcl`; báo cáo ở
`study/build/tile_thu_4lan/tile_breakdown/`. Phần logic nằm trực tiếp
trong `tile_thu` được chia theo tên tín hiệu mà LUT điều khiển; đây là ước lượng, vì Vivado đặt tên LUT theo một trong các
net nó lái. Tổng sau tổng hợp (4 195 LUT ở C) lệch vài phần trăm so với sau route (4 014).

| Phần của tile C | LUT (ước lượng) | Tỉ lệ | Ghi chú |
|---|---:|---:|---|
| 4 làn butterfly (cộng/trừ/chia đôi mod q, hàng trễ dữ liệu phụ) | 1 549 | 37% | làn 32 bit 797 (218 là SRL hàng trễ), mỗi làn 16 bit ~250 |
| Mux chọn toán hạng vào 4 làn | ~800 | ~19% | hoán vị theo chế độ, chiều, khe; giữ request lane 32 bit |
| 4 bộ rút gọn hằng 3329/12289 | ~770 | ~18% | ~190 mỗi bộ; mỗi bộ có cả hai công thức shift-add rồi chọn |
| Gom kết quả và sắp lại lane 32 bit (`rd`, `zacc`, `yacc`, `pY`) | ~590 | ~14% | mux 128 bit nhiều nguồn |
| Mux toán hạng vào bộ nhân, bộ nhân và phần ghép | ~260 | ~6% | chính 4 bộ nhân gần như không tốn LUT |
| Đuôi rút gọn 32 bit trên mảng (kể cả hàng trễ 33 bit) | ~150 | ~4% | |
| Điều khiển | < 50 | ~1% | |

Các con số "~" trong tile đã quy đổi theo tỉ lệ 2 515 / 2 879 (số LUT sau đóng gói trên số ô LUT đếm theo tên).

**Đọc bảng:** bộ nhân chỉ chiếm vài phần trăm. Khoảng một phần ba LUT là **di chuyển dữ liệu bên trong tile** (mux vào và
mux ra), là hệ quả trực tiếp của hợp đồng tile: request 128 bit chứa 4 hệ số và root đi kèm, tile phải tự hoán vị theo
5 chế độ, 2 chiều, 2 làn và tự ghép lớp 2 của frame hai lớp. Thêm gần một phần năm cho 4 bộ rút gọn chọn được hai modulus.

**So với P1** (lõi FFT/NTT hợp nhất, ICASSP 2025; số tác giả báo cáo, chưa tái lập; cùng chip xczu7ev-2):

| | P1 (cả lõi) | Tile C (chỉ phần tính) |
|---|---|---|
| LUT / FF / DSP / BRAM | 3 716 / 2 400 / 12 / 5 | 4 014 / 2 975 / 4 / 0 |
| Fmax | 400 MHz | 316 MHz |
| ML-KEM, butterfly/chu kỳ | 4 | 4 |
| ML-DSA, butterfly/chu kỳ | 2 | 1/3 |
| LUT trên mỗi DSP | ~310 | ~1 000 |
| Dữ liệu đến butterfly | bộ nhớ chia bank và bộ sinh địa chỉ đưa đúng chỗ | tile tự hoán vị từ frame 128 bit |
| Modulus | hai q cố định, Barrett | 3329/12289 chọn lúc chạy; lane 32 bit q bất kỳ |
| Chiều nghịch | chưa thấy mô tả | có, kèm chia đôi |

P1 tốn 1 416 LUT để thêm NTT vào lõi FFT (2 300 → 3 716). Riêng 4 bộ rút gọn và phần mux trong tile của mình đã vượt con
số đó. Khác biệt chính không nằm ở số học mà ở chỗ **ai lo sắp dữ liệu**: P1 để bộ nhớ và bộ sinh địa chỉ lo, một lần cho
cả lõi; tile của mình tự lo, lặp lại ở cả 16 tile.

**Hướng giảm (đề xuất, chưa làm, cần duyệt vì đổi hợp đồng tile):**
1. Chuyển phần hoán vị (ghép cặp CT/GS, đặt kết quả, lớp 2 của frame hai lớp) ra tầng bộ nhớ/sinh địa chỉ dùng chung;
   tile chỉ nhận toán hạng đã xếp đúng làn. Ảnh hưởng lớn nhất, nhưng phải xem tầng bộ nhớ có trả thêm chi phí không.
2. Bộ rút gọn 16 bit: thay hai công thức song song bằng một bộ dùng chung bộ cộng, hoặc một kiểu rút gọn rẻ hơn cho
   3329/12289; cần đo.
3. Bỏ frame hai lớp ở lane 32 bit nếu lịch NTT không cần (bỏ `pY`/`aY`/`yacc`/`pA`/`aA`, khoảng 530 FF).
4. Thanh ghi I/O 480 FF của `tile_thu_top` là của testbench, không tính vào thiết kế thật.

## 9. Tile một làn NTT (hợp đồng tile 31/10/2026, lần 2)

Người dùng duyệt: giữ 16 tile nhưng mỗi tile chỉ còn một làn NTT; mỗi request là một butterfly hoặc một phép nhân
modulo, toán hạng ở ô cố định (x = d0, y = d1, w = r0), không còn hoán vị trong tile; bỏ nhịp hai tầng; tách số của vỏ
đo. Hợp đồng: [spec 2.0, 10](../../spec/FlexTransform/2.0/10_hop_dong_tile.md). Bản nháp viết lại theo hợp đồng này, có
ba biến thể: 2 = lai (v1), 0 = rút gọn riêng (đối chứng), 1 = mọi modulus trên mảng (điểm đo, 10 mục 5.3: lane 16 bit
chia ba lượt Montgomery cho ba bộ nhân khác nhau nên vẫn 1 request/chu kỳ, nhận mọi q lẻ < 2¹⁶).

Hash 16 ký tự đầu: RTL `c05c85e5745b2553`, testbench `f38283e8b62b6d93`; vector NTT mới (manifest): `ntt16_pqc`
`e2ecca81852abab0`, `ntt16_q_khac` `48ad79626fc3cfbc`, `ntt32` `62a73ea8d5a80643` (tích thô và FFT không đổi).

**Chức năng:** regression đầy đủ ở cả ba biến thể (nhóm A, B gồm chuỗi đổi chế độ, ghi hằng số lúc bận, reset giữa
chừng, lịch không phụ thuộc dữ liệu; testbench nay tự kiểm tốc độ): **92 lần chạy đạt; 36/36 lỗi cài vào bị bắt** (7 lỗi
× 3 biến thể, năm lỗi RTL chạy trên cả vector 16 và 32 bit). `ntt16_q_khac` đạt trên biến thể 1.

| Độ trễ (chu kỳ có `en = 1`) | Lai (2) | Rút gọn riêng (0) | Mọi modulus trên mảng (1) |
|---|---:|---:|---:|
| Chế độ 0, 1 | 6 | 6 | 6 |
| Chế độ 2, 4, lane 16 bit | 10 | 10 | 16 |
| Chế độ 2, 4, lane 32 bit | 24 | 16 | 24 |
| Tốc độ lane 16 / 32 bit (request/chu kỳ) | 1 / 1/3 | 1 / 1 | 1 / 1/3 |

**Vivado 2018.1, sau route, 3,0 ns, cài đặt mặc định:**

| Số liệu | Lai (2) | Rút gọn riêng (0) | Trên mảng (1) | Lai 4 làn (mục 7) |
|---|---:|---:|---:|---:|
| LUT (cả vỏ đo) | 1 279 | 1 233 | 1 193 | 4 014 |
| FF (cả vỏ đo) | 1 099 | 1 049 | 1 102 | 2 975 |
| LUT / FF riêng khối tile | 1 279 / 842 | 1 233 / 762 | 1 193 / 845 | 4 006 / 2 495 |
| DSP | 4 | 11 | 4 | 4 |
| BRAM / URAM | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| WNS | +0,255 ns | +0,320 ns | +0,331 ns | −0,163 ns |
| Fmax | ≥ 333 MHz | ≥ 333 MHz | ≥ 333 MHz | 316 MHz |

Cả ba biến thể đạt 3,0 ns, nên Fmax chỉ là cận dưới và không so được chênh lệch Fmax giữa chúng. Siết clock để so là
đổi thủ tục đo, cần người dùng duyệt.

Phân bổ LUT của biến thể lai (báo cáo phân cấp sau route): butterfly 32 bit dùng chung cho cả hai lane 782 (61%),
bộ nhân và mux toán hạng vào bộ nhân 225, phần còn lại (bộ rút gọn hằng, đuôi rút gọn 32 bit, điều khiển, gom kết quả)
244. Đường dài nhất của C: thanh ghi kết quả rút gọn 32 bit → cộng/trừ mod q của tầng sau butterfly.

**So với tile 4 làn (mục 7):** LUT giảm 68%, FF giảm 63%, cùng DSP; Fmax từ 316 lên ≥ 333 MHz. **Một phần khoản giảm là
chuyển chỗ chứ không mất đi:** ghép cặp CT/GS, đặt kết quả và cấp root riêng cho từng butterfly nay thuộc mạng bank →
tile. Chưa kiểm phần đó có gộp được vào mạng chọn sẵn có của lõi mà không tốn thêm hay không.

**Giả thuyết 2 trên bản nháp** (thủ tục: số của cả vỏ đo): DSP ít hơn 7 (đạt); LUT tăng 3,7% (đạt, ngưỡng ≤ 5%); Fmax
cả hai ≥ 333 MHz (không thấy giảm, nhưng chỉ là cận dưới); NTT 32 bit chậm 3 lần (đạt). Khoảng cách tới ngưỡng LUT
hẹp hơn trước (2,0% → 3,7%) vì phần dùng chung nhỏ đi. Vẫn chỉ là chỉ dấu của bản nháp.

**Điểm mới cần người dùng quyết định:** biến thể 1 (mọi modulus trên mảng) nay **ít LUT hơn lai 6,7%** (1 193 so với
1 279), cùng 4 DSP, cùng FF, cùng tốc độ, và nhận mọi q lẻ < 2¹⁶ ở lane 16 bit thay vì chỉ 3329/12289. Cái giá: độ trễ
lane 16 bit 16 thay vì 10 chu kỳ (mỗi lượt NTT 16 bit dài thêm 6 chu kỳ). Lý do chọn lai trước đây (NTT 16 bit nhanh gấp
3) không còn, vì với một làn, ba lượt Montgomery chạy trên ba bộ nhân khác nhau. Chưa đổi lựa chọn v1.

**Ước lượng cấp lõi (chưa đo):** 16 tile × ~1 280 LUT ≈ 20 500 LUT cho phần tile, so với ≈ 64 000 trước, **chưa tính
phần ghép cặp và cấp root đã chuyển ra mạng bank → tile**. Cùng 12 DSP như P1 (3 tile): khoảng 3 800 LUT phần tile so
với 3 716 LUT cả lõi P1 (gồm bộ nhớ và điều khiển); vì phần chuyển ra ngoài chưa tính, so sánh này còn lợi cho mình.
Theo DSP: ML-KEM 3 butterfly/chu kỳ trên 12 DSP so với 4 của P1.

**Ước lượng NTT theo lượt một tầng** (độ trễ bản nháp + 2 chu kỳ RAM, 16 tile, không ghép đa thức):
- NTT 16 bit N1024: khoảng 440 chu kỳ (trước: 185 với 4 làn và nhịp hai tầng); N256: 160 (trước 100). Giả định bộ nhớ
  cấp đủ 16 butterfly độc lập mỗi chu kỳ, mỗi cái một root; cấp root của spec 03 tính cho gói ba root của nhịp hai tầng
  (4 bank, một gói mỗi bank mỗi chu kỳ), nên các tầng cuối nhiều root khác nhau có thể bị giới hạn bởi cấp root. Chưa
  kiểm.
- NTT prime 31 bit của sinh khóa N1024 (theo số lời gọi ở `fn_dsa_workload_lai.md`): lai khoảng 1,04 triệu chu kỳ so
  với 1,14 triệu theo lịch nhịp hai tầng với độ trễ bản nháp cũ (−9%); rút gọn riêng 0,66 so với 0,67 triệu. Bỏ nhịp hai
  tầng không làm chậm lane 32 bit, vì độ trễ nhịp hai tầng của bản nháp cũ (57 chu kỳ) hơn hai lần độ trễ một butterfly
  (24).

**Chưa cập nhật theo thay đổi này:** gói root và kiểm xung đột bank ở spec 03 (làm cho nhịp hai tầng), cách xếp N nhỏ vào
tile, dự báo chu kỳ của kiến trúc mục 4, mô hình workload, mô hình ngân hàng cộng (`model/postproc_adders.py`, sẽ nhỏ
đi), `model/arch_checks.py`, `docs/diem_manh_kien_truc.md`, giả thuyết 7 (so nhịp hai tầng với một tầng, nay không còn
nhịp hai tầng), bằng chứng khớp NTRUGen (cho lịch hai tầng). Ngưỡng giả thuyết 4 cũ hỏng do thay đổi này; đề xuất mới ở
bảng "Sửa sau khi khóa" của kiến trúc, chưa duyệt.

**Báo cáo:** `study/build/tile_thu_<biến thể>/`. Lưu ý: lần đo này **ghi đè** `study/build/tile_thu_1/` và log của nó,
tức báo cáo của biến thể A cũ (4 làn, lần đo 2: 3 654 LUT, 317 MHz, mục 3 và 6). Số liệu đó chỉ còn trong ghi chú này.

## 10. Thiết kế v1 chuyển sang mọi modulus trên mảng; bản đối chứng công bằng cho giả thuyết 2

Người dùng chọn biến thể 1 (mọi modulus trên mảng) làm thiết kế v1. Hợp đồng tile mục 5 đòi bản đối chứng chỉ khác thiết
kế ở lane 32 bit, nên bản nháp có thêm biến thể 3: lane 16 bit trên mảng như thiết kế, lane 32 bit dùng bộ Montgomery
32 bit riêng. Mã tham số: 1 = thiết kế v1, 3 = đối chứng; 2 (lai cũ) và 0 (rút gọn riêng cả hai lane) chỉ là điểm đo.
RTL chỉ đổi cách ánh xạ tham số; hash 16 ký tự đầu: RTL `f170a821f4dd7298`, testbench `709d56e377a8517b`.

**Chức năng:** regression bốn biến thể: **124 lần chạy đạt, 48/48 lỗi cài vào bị bắt**; `ntt16_q_khac` đạt trên 1 và 3.
Biến thể 3: lane 32 bit độ trễ 16, tốc độ 1 request/chu kỳ.

**Vivado 2018.1, sau route, 3,0 ns, cài đặt mặc định** (số của 1, 2, 0 trùng lần đo ở mục 9):

| Số liệu | 1: v1, trên mảng | 3: đối chứng | 1 so với 3 | 2: lai cũ | 0: riêng cả hai lane |
|---|---:|---:|---:|---:|---:|
| LUT (cả vỏ đo) | 1 193 | 1 027 | **+16,2%** | 1 279 | 1 233 |
| FF (cả vỏ đo) | 1 102 | 1 017 | +8,4% | 1 099 | 1 049 |
| LUT / FF riêng khối tile | 1 193 / 845 | 1 027 / 730 | | 1 279 / 842 | 1 233 / 762 |
| DSP | 4 | 11 | −7 | 4 | 11 |
| BRAM / URAM | 0 / 0 | 0 / 0 | | 0 / 0 | 0 / 0 |
| WNS | +0,331 ns | +0,461 ns | | +0,255 ns | +0,320 ns |
| Fmax | ≥ 333 MHz | ≥ 333 MHz | cận dưới | ≥ 333 MHz | ≥ 333 MHz |
| Lane 32 bit: tốc độ / độ trễ | 1/3 / 24 | 1 / 16 | chậm 3 lần | 1/3 / 24 | 1 / 16 |

**Giả thuyết 2 với bản đối chứng công bằng** (thủ tục: số của cả vỏ đo; ngưỡng giữ nguyên, chỉ đổi định nghĩa bản đối
chứng, đề xuất chưa duyệt): DSP ít hơn 7 (đạt); **LUT tăng 16,2%, chạm điều kiện bác bỏ "LUT tăng > 10%"**; Fmax cả hai
≥ 333 MHz (chỉ cận dưới); NTT 32 bit chậm 3 lần (đạt). Trên bản nháp, **giả thuyết 2 bị bác bỏ** ở điều kiện LUT.

Đọc kết quả:
- Phần LUT chênh tuyệt đối là 166 LUT mỗi tile để bớt 7 DSP. Ở tile 4 làn (mục 7), cùng lane 32 bit trên mảng chỉ tốn
  thêm 66 LUT so với đối chứng của nó, nhưng khi đó phần dùng chung lớn nên tỉ lệ chỉ +1,7%. Ngưỡng 5% / 10% được đặt
  khi tile còn khoảng 4 000 LUT.
- Biến thể 3 rẻ hơn biến thể 0 tới 206 LUT (lane 16 bit trên mảng so với bộ hằng), nhưng biến thể 1 chỉ rẻ hơn 2 là 86
  LUT. Khi cả hai lane cùng dùng bộ nhân cho các lượt rút gọn, mux đầu vào bộ nhân có nhiều nguồn hơn; đây là chỗ khả
  dĩ nhất của khoản chênh, chưa tách riêng để kiểm.
- Theo hợp đồng tile mục 8, kết quả âm thì lane 32 bit của lõi dùng bộ Montgomery riêng. Đây mới là số bản nháp, nghiệm
  thu là trên RTL thật; nhưng bản nháp đã dùng cùng một mã cho phần chung của hai biến thể.
- Không chỉnh ngưỡng hay sửa RTL để đổi kết quả này.
- **Người dùng quyết định (31/10/2026): giữ lane 32 bit trên mảng, chờ số đo trên RTL thật** (biến thể 1 và 3) rồi mới
  chọn giữa trên mảng và bộ Montgomery riêng.

Cả lõi (ước lượng, 16 tile, chưa tính phần đã chuyển ra mạng bank → tile): thiết kế 1 khoảng 19 100 LUT và 64 DSP; đối
chứng 3 khoảng 16 400 LUT và 176 DSP, NTT 32 bit nhanh gấp 3 (sinh khóa: khoảng 0,66 so với 1,04 triệu chu kỳ NTT theo
ước lượng ở mục 9).

## 11. RTL nghiệm thu (người dùng giao cho trợ lý viết, 31/10/2026)

RTL riêng, không phải bản nháp: [hdl/tile/tile_thu.sv](../../hdl/tile/tile_thu.sv), manifest triển khai
[hdl/tile/MANIFEST.md](../../hdl/tile/MANIFEST.md). Chỉ có biến thể 1 (thiết kế) và 3 (đối chứng), dùng chung toàn bộ
mã trừ khối rút gọn lane 32 bit. Các tối ưu áp dụng như nhau cho cả hai: một bộ cộng/trừ modulo dùng chung cho CT và GS,
bỏ thanh ghi chờ giữa các lượt nhân, ghi kết quả thẳng vào thanh ghi đầu ra. **Cùng tác giả với testbench.**

**Kiểm thử:** `VARIANTS="1 3" sh sim/tile_thu/run.sh hdl/mul_ss.v hdl/tile/tile_thu.sv`: 64 lần chạy đạt, 24/24 lỗi cài
vào bị bắt; mỗi nhóm có một độ trễ cố định (6 / 13 / 19 ở biến thể 1, 6 / 13 / 15 ở biến thể 3). Bảng kết quả của spec
11 đã điền.

**Vivado 2018.1, sau route, 3,0 ns, cài đặt mặc định:**

| Số liệu | 1: trên mảng | 3: đối chứng | 1 so với 3 | Bản nháp 1 / 3 (mục 10) |
|---|---:|---:|---:|---:|
| LUT | 1 022 | 906 | +12,8% | 1 193 / 1 027 |
| FF | 959 | 1 033 | −7,2% | 1 102 / 1 017 |
| DSP | 4 | 11 | −7 | 4 / 11 |
| BRAM / URAM | 0 / 0 | 0 / 0 | | |
| WNS; Fmax | +0,168 ns; ≥ 333 MHz | +0,287 ns; ≥ 333 MHz | cận dưới | |

Phân bổ LUT (báo cáo phân cấp): bộ nhân và mux đầu vào bộ nhân 358 so với 262, tức mux đưa ba lượt lane 32 bit vào bộ
nhân tốn thêm khoảng 96 LUT; bộ cộng/trừ dùng chung 321 so với 305; phần còn lại 301 so với 297 (biến thể 3 dùng 7 DSP
cho m và m·q).

**Giả thuyết 2** (ngưỡng khóa lần 3): DSP ít hơn 7 (đạt); **LUT tăng 12,8%, chạm điều kiện bác bỏ (> 10%)**; Fmax không
thấy giảm (cận dưới); tốc độ tile lane 32 bit chậm 3 lần, cả NTT 32 bit N256 ước lượng khoảng 1,8 lần (8 lượt × (24 + 21)
so với 8 × (8 + 17) chu kỳ; đạt, ngưỡng ≤ 3,5). **Bác bỏ ở cấp tile.** Cấp lõi chưa đo: với biến thể 3, mạng bank → tile và
cấp root phải nuôi 16 butterfly 32 bit mỗi chu kỳ thay vì 16/3, mỗi cái một root riêng. Khoảng chênh tuyệt đối giảm từ 166 LUT (bản nháp) xuống
116 LUT, nhưng phần dùng chung cũng nhỏ đi nên tỉ lệ vẫn trên 10%.

Theo hợp đồng tile mục 8, kết quả âm thì lane 32 bit của lõi dùng bộ Montgomery riêng (biến thể 3). Việc áp dụng chờ
người dùng xác nhận.

Ước lượng cả lõi, 16 tile, chưa tính phần ghép cặp và cấp root đã chuyển ra mạng bank → tile: biến thể 1 khoảng 16 400
LUT và 64 DSP; biến thể 3 khoảng 14 500 LUT và 176 DSP, NTT 32 bit nhanh gấp 3.

## 12. Phần cấp lõi sau khi đổi sang tile một làn (31/10/2026)

- **Khớp NTRUGen theo lịch một tầng:** [model/ntrugen_mp31.py](../../model/ntrugen_mp31.py) thêm NTT xuôi và ngược mỗi
  tầng một lượt, mỗi butterfly là một request tile, phát theo thứ tự ngẫu nhiên trong tầng: khớp `mp_NTT` / `mp_iNTT` trên
  3 230 trường hợp mỗi chiều (323 prime × logn 1..10). Kết quả ở [ntrugen_mp31.md](ntrugen_mp31.md). Vector kernel của spec
  2.0 không phụ thuộc lịch nhịp và vẫn kiểm đạt.
- **Cấp dữ liệu và root:** [model/single_lane_feed.py](../../model/single_lane_feed.py),
  kết quả [single_lane_feed.md](single_lane_feed.md). Với 8 bank gói root (trước là 4) và đọc lệch một chu kỳ khi hai
  toán hạng cùng bank, cả hai lane đạt 16 butterfly/chu kỳ ở N từ 32 đến 1024 (lane 32 bit N1024: 15,95). Không đọc lệch,
  lane 32 bit N1024 tụt còn 3,9 vì hàm bank bỏ qua bit 10 của địa chỉ. Định dạng gói và dung lượng RAM root không đổi.
  Mạng bank → tile giả định nối đầy đủ, **chi phí LUT chưa đo**. Spec 03 mục 1, 4, 6 đã viết lại theo mô hình.
- **Workload** ([fn_dsa_workload_mot_lan.md](fn_dsa_workload_mot_lan.md), cùng số lời gọi với `fn_dsa_workload_lai`):
  N1024 sinh khóa khoảng 1,25 triệu chu kỳ với thiết kế v1 (lane 32 bit riêng), 1,50 triệu nếu lane 32 bit trên mảng; ký
  130 nghìn (không đổi); kiểm 1 727 (trước 656). Độ trễ dùng số của RTL nghiệm thu, còn bản `_lai` dùng mô hình chu kỳ cũ,
  nên hai bản không so trực tiếp từng chu kỳ.
- **Ngân hàng cộng** ([postproc_adders_mot_lan.md](postproc_adders_mot_lan.md)): dùng chung 3 493 bit so với 4 720 riêng
  (−26%); trước là 5 733 so với 6 768 (−15%).
- **`arch_checks`:** thêm mục F (tốc độ tile một làn, không bộ nhân nào nhận hai lượt cùng chu kỳ); đạt.
- **Giả thuyết 4:** đề xuất viết lại công thức theo lượt một tầng và mô hình cấp dữ liệu, dự báo không đổi (≤ 590 / 230 /
  115, NTT 32 bit ≤ 250). Người dùng duyệt; đã khóa lại lần 4 (SHA `4ce1e243…`).

## 13. Sửa RTL nghiệm thu, đo lại (31/10/2026)

Ba sửa đổi trên [hdl/tile/tile_thu.sv](../../hdl/tile/tile_thu.sv) (hash `8d2a02a8890211e1`; bản đo lần 1 lưu ở
`study/build/tile_acc_v1_0a28e919.sv`):
1. `TREN_MANG` mặc định 3 (thiết kế v1).
2. Mọi độ trễ engine suy từ tham số `LEAF_PD` của bộ nhân; biến thể 1 tự báo lỗi nếu ba lượt rơi cùng pha.
3. Tham số `IN_REG`: một tầng thanh ghi cho request đã nhận, dùng trong lõi.

Thêm: sửa hết cảnh báo độ rộng của Verilator `-Wall` (còn lại chỉ là bit không dùng, có chủ ý); `run.sh` nhận `IVFLAGS`
và `BUILD`; `tile_thu.tcl` nhận `TILE_GENERIC`.

**Kiểm thử:** ba cấu hình (mặc định, `IN_REG = 1`, `LEAF_PD = 4`) × hai biến thể, mỗi cấu hình 64 lần chạy đạt và 24/24
lỗi bị bắt; độ trễ cố định và đúng công thức trong manifest (mặc định 6 / 13 / 15; `IN_REG` +1; `LEAF_PD = 4`: 8 / 19 /
17). Biến thể 1 với `LEAF_PD = 3` bị chặn lúc elaboration như thiết kế.

**Vivado** (cài đặt mặc định, 3,0 ns):

| | v1 (3) | v1, `IN_REG = 1` | Biến thể 1 |
|---|---:|---:|---:|
| LUT / FF / DSP | 925 / 1 033 / 11 | 905 / 1 132 / 11 | 1 022 / 959 / 4 |
| WNS | +0,265 ns | +0,258 ns | +0,118 ns |

- Giả thuyết 2 vẫn bác bỏ: LUT +10,5% (lần 1: +12,8%); logic không đổi, chênh do đặt cell.
- `IN_REG = 1` tốn khoảng 100 FF. Trong vỏ đo nó không cải thiện timing, vì vỏ đo đã có thanh ghi ở cổng; lợi ích chỉ thấy
  khi request đến qua mạng bank → tile.
- **Phát hiện mới, rủi ro cấp lõi:** đường dài nhất của v1 nay là tín hiệu cho phép chung `en`: fanout 784 trong một tile,
  2,56 ns dây, tới chân cho phép của thanh ghi đầu vào bộ nhân. Hợp đồng tile yêu cầu `en = 0` giữ mọi thanh ghi ngay
  trong chu kỳ đó. Trong lõi, `en` phải tới 16 tile (khoảng 12 500 thanh ghi). Nhận định lúc đó rằng một chu kỳ "gần
  như chắc chắn không đủ" là **sai**: đo 16 tile ở mục 14 cho thấy vẫn đạt 3,0 ns.

## 14. Tín hiệu dừng chung `en` (31/10/2026)

**Tùy chọn `EN_REG`** trong [hdl/tile/tile_thu.sv](../../hdl/tile/tile_thu.sv): đường dữ liệu dùng bản sao `en` qua một
thanh ghi; thanh ghi cổng ra chỉ đổi khi `en = 1`; một ô đệm giữ kết quả sinh ra trong chu kỳ chạy thêm; chỉ nhận request
khi cả `en` lẫn bản sao bằng 1. Hợp đồng tile mục 2 và 6 sửa theo những gì thấy ở cổng (spec 2.0 CHANGELOG lần 5).
Testbench không đổi.

**Kiểm thử:** bốn cấu hình (mặc định; `EN_REG = 1`; `EN_REG = 1` với `IN_REG = 1`; `EN_REG = 1` với `LEAF_PD = 4`) × hai
biến thể: mỗi cấu hình 64 lần chạy đạt, 24/24 lỗi bị bắt, gồm dừng ngẫu nhiên, đợt dừng dài, kiểm cổng ra đứng yên khi
`en = 0`, ghi hằng số lúc bận, reset giữa chừng, lịch không phụ thuộc dữ liệu. Verilator `-Wall` sạch ở mọi cấu hình.

**Một tile (biến thể 3, Vivado 2018.1, 3,0 ns):** `EN_REG = 0`: 932 LUT, 1 036 FF, WNS +0,238 ns; `EN_REG = 1`: 977 LUT,
1 110 FF, WNS +0,078 ns (đường dài nhất qua mux cổng ra mới); thêm `IN_REG = 1`: 970 LUT, 1 209 FF, +0,167 ns.

**16 tile sau một thanh ghi `en` chung** ([hdl/tile/tile_array16_top.sv](../../hdl/tile/tile_array16_top.sv),
[fpga/zcu106/tile_array16.tcl](../../fpga/zcu106/tile_array16.tcl); mỗi tile có thanh ghi vào/ra riêng):

| | LUT | FF | DSP | WNS | Đường dài nhất |
|---|---:|---:|---:|---:|---|
| `EN_REG = 0` | 14 863 | 16 381 | 176 | +0,037 ns | tầng sau butterfly → thanh ghi cổng ra |
| `EN_REG = 1` | 15 398 | 17 550 | 176 | +0,061 ns | như trên |

- Với `EN_REG = 0`, placer của Vivado tự chèn một BUFG cho `en` (log: "inserted BUFG to drive 10502 loads"), nên `en`
  không còn là đường dài nhất. Cả hai cách đều đạt 3,0 ns.
- `EN_REG = 1` tốn thêm 535 LUT (+3,6%) và 1 169 FF (+7%) cho 16 tile mà không cải thiện timing có ý nghĩa.
- **Kết luận:** giữ `EN_REG = 0` (mặc định). Điều kiện ở cấp lõi: `en` phải lấy trực tiếp từ một thanh ghi, tức bộ điều
  khiển quyết định dừng sớm một chu kỳ. `EN_REG = 1` để dành cho trường hợp lõi không làm được điều đó, hoặc khi không
  có bộ đệm toàn cục (ASIC: cần cây buffer, chưa đánh giá).
- **Testbench bắt được lỗi của cơ chế mới:** phá ô đệm (không bao giờ giữ kết quả) hoặc bỏ điều kiện nhận request khi
  bản sao `en` bằng 0 đều cho FAIL khi có dừng ngẫu nhiên (1 301 và 1 347 lỗi trên `fft32`). Phép thử này lộ ra testbench
  treo khi tile làm mất kết quả (chờ `idle` mãi trước khi ghi hằng số); đã sửa: chờ quá 10 000 chu kỳ thì báo lỗi và
  reset. Testbench mới `68480ad04e87b005`, chạy lại đủ cấu hình mặc định và `EN_REG = 1`: 64 đạt, 24/24.
- Đây là ước lượng cấp lõi một phần: chưa có bộ nhớ, mạng bank → tile và bộ điều khiển, nên WNS +0,037 ns của 16 tile chỉ
  cho biết phần tile không phải là chỗ nghẽn.

## 15. Mạng bank → tile (bản nháp crossbar) và so với các bài khác (31/10/2026)

**Bản nháp:** [hdl/net/ntt_bank_net.sv](../../hdl/net/ntt_bank_net.sv), crossbar đầy đủ: mỗi tile hai toán hạng chọn
từ 64 bank (lane 32 bit dùng cặp bank), thanh ghi giữ cho đọc lệch, root chọn từ 8 bank gói rồi một trong ba root của
gói, mỗi bank ghi chọn một trong 32 kết quả (16 tile × 2). Không gồm RAM, sinh địa chỉ và bộ điều khiển. Kiểm ngẫu nhiên
20 000 chu kỳ khớp mô hình tham chiếu ([sim/net/tb_ntt_bank_net.sv](../../sim/net/tb_ntt_bank_net.sv)).

**Vivado 2018.1, sau route, 3,0 ns** ([fpga/zcu106/ntt_bank_net.tcl](../../fpga/zcu106/ntt_bank_net.tcl), mọi đầu vào có
thanh ghi): **35 623 LUT, 6 626 FF**, 15 904 MUXF7, 3 664 MUXF8, 0 DSP, 0 BRAM, WNS +0,195 ns. Theo phần logic nuôi từng
nhóm thanh ghi (sau tổng hợp, có thể chồng nhau một ít): đọc khoảng 19 100 LUT, root 3 600, ghi 13 300.

**So với các bài khác** (số tác giả báo cáo, cả bộ tăng tốc gồm bộ nhớ, mạng và điều khiển; chưa tái lập):

| Thiết kế | Thiết bị | Bài toán | Song song | LUT / FF / BRAM / DSP | Chu kỳ NTT |
|---|---|---|---|---|---:|
| HF-NTT, 16 PE | Virtex-7 | N 4096, q 32 bit | 16 PE | 12 671 / 9 564 / 192 / 112 | 1 555 |
| HF-NTT, 32 PE | Virtex-7 | N 4096, q 32 bit | 32 PE | 25 040 / 19 203 / 192 / 224 | 787 |
| HF-NTT, 16 PE | Virtex-7 | N 1024, q 14 bit | 16 PE | 6 560 / 3 859 / 17,3 / 48 | 335 |
| Bài [11] trong PIP-NTT (2021) | Artix-7 | Kyber N 256 | — | 9 508 / 2 684 / 35 / 16 | 69 |
| Bài [16] trong PIP-NTT (2024) | Artix-7 | Kyber N 256 | — | 18 296 / 12 134 / 0 / 64 | 85 |
| P1 (FFT/NTT hợp nhất) | ZCU104 | ML-KEM, ML-DSA, FFT 32 bit | 4 butterfly | 3 716 / 2 400 / 5 / 12 | 322 (ML-KEM) |
| **Mình: 16 tile** | ZCU106 | NTT 16/32 bit + FFT 32/64/128 | 16 butterfly | 14 863 / 16 381 / 0 / 176 | — |
| **Mình: mạng crossbar** | ZCU106 | | | 35 623 / 6 626 / 0 / 0 | — |

Đọc bảng:
- Cùng 16 butterfly/chu kỳ và modulus 32 bit, HF-NTT dùng khoảng **12 700 LUT cho cả bộ tăng tốc**. Riêng mạng crossbar
  của mình đã gấp gần 3 lần con số đó; tile cộng mạng khoảng 50 500 LUT, gấp khoảng 4 lần. **Crossbar đầy đủ là quá
  nhiều so với các bài cùng loại.**
- Phần tile (14 900 LUT) cũng hơn cả bộ HF-NTT. Một phần là tính năng mình có mà HF-NTT không có (FFT 32/64/128 bit, hai
  lane, q 16 bit đổi lúc chạy), nhưng mạng thì không có lý do để đắt như vậy.
- Mục tiêu hợp lý cho mạng có cấu trúc: vài nghìn LUT, để cả phần tính + mạng ở mức khoảng 1,5–2 lần HF-NTT, đổi lấy FFT
  nhiều độ chính xác.
- Thiết bị khác nhau (Virtex-7, Artix-7 so với UltraScale+); cả hai đều dùng LUT 6 đầu vào nên số LUT so được ở mức thô.

**Một quan sát về giả thuyết 2** (không mở lại quyết định, chỉ ghi lại): các bài so sánh thường quy DSP và BRAM về một
thước đo chung. PIP-NTT dùng SEC = 200 × BRAM + 100 × DSP + slice, với slice ≈ 0,25 × LUT + 0,125 × FF (lấy từ các bài
trước). Theo thước đo này, tile lane 32 bit trên mảng (1 022 LUT, 959 FF, 4 DSP) khoảng 775, tile dùng bộ Montgomery
riêng (925 LUT, 1 033 FF, 11 DSP) khoảng 1 460, tức trên mảng rẻ hơn khoảng 47%. Giả thuyết 2 đã khóa chỉ xét LUT tăng
≤ 10% nên bác bỏ. Đổi thước đo sau khi đã biết kết quả là chỉnh về đáp án; nếu muốn dùng thước đo này phải ghi rõ như vậy.

Nguồn: HF-NTT, [arXiv 2410.04805](https://arxiv.org/abs/2410.04805), Table II; PIP-NTT,
[arXiv 2607.18533](https://arxiv.org/abs/2607.18533), Table III; P1, [arXiv 2504.11124](https://arxiv.org/abs/2504.11124).

## 16. Mạng bank → tile có cấu trúc (31/10/2026)

**Ý tưởng:** tile của một butterfly là hàm cố định của bank hai toán hạng, không phải thứ tự butterfly. Hàm bank có dạng
{2 bit XOR, 4 bit thấp của địa chỉ}, nên tile lấy theo 4 bit thấp (có hiệu chỉnh theo tầng). Hai tile khác nhau không bao
giờ đọc cùng bank trong một chu kỳ, và mỗi cổng chỉ cần vài nguồn. Mô hình [model/structured_net.py](../../model/structured_net.py),
kết quả [structured_net.md](structured_net.md); RTL sinh từ bảng nguồn bằng
[scripts/gen_structured_net.py](../../scripts/gen_structured_net.py) thành
[hdl/net/ntt_bank_net_s.sv](../../hdl/net/ntt_bank_net_s.sv); kiểm ngẫu nhiên 20 000 chu kỳ đạt
([sim/net/tb_ntt_bank_net_s.sv](../../sim/net/tb_ntt_bank_net_s.sv)).

| Số nguồn mỗi cổng | Crossbar | Theo bank (lớn nhất / trung bình) |
|---|---:|---:|
| Đọc, nửa thấp | 64 | 16 / 11,7 |
| Đọc, nửa cao (lane 32 bit) | 32 | 6 |
| Ghi, mỗi bank | 32 | 12 / 8,1 |

Tốc độ trên mọi trường hợp (lane 16 và 32 bit, N 2..1024, 1–8 đa thức, xuôi và ngược): 15,87 butterfly/chu kỳ; không xung
đột bank dữ liệu; 40 chu kỳ thêm do xung đột bank gói root (vị trí gói đầu của mỗi khe phải là bội của 8).

**Vivado 2018.1, sau route, 3,0 ns** (cùng cách đặt thanh ghi đầu vào như crossbar):

| Phần | Crossbar | Theo bank |
|---|---:|---:|
| Đọc | ~19 100 LUT | ~3 400 LUT |
| Ghi | ~13 300 LUT | ~2 600 LUT |
| Root | ~3 600 LUT | ~3 600 LUT (chưa tối ưu) |
| Tổng LUT / FF | 35 623 / 6 626 | **9 397 / 6 594** |
| WNS | +0,195 ns | +0,441 ns |

Phần tính + mạng: 16 tile (14 863 LUT, đo ở mục 14) + mạng 9 397 ≈ **24 300 LUT, 176 DSP**, chưa gồm RAM, sinh địa chỉ và
bộ điều khiển. So với HF-NTT 16 PE, modulus 32 bit (12 671 LUT cho cả bộ tăng tốc, mục 15): khoảng 1,9 lần LUT, đổi lấy
FFT 32/64/128 bit, hai lane và q 16 bit đổi lúc chạy. Nằm trong khoảng mục tiêu 1,5–2 lần.

**Điều kiện mới, chưa quyết:** với cách gán theo bank, ở lệnh nhiều prime (lane 32 bit, N = 8, 16, 32) một tile nhận
butterfly của tối đa **2 đa thức khác prime**. Hai cách:
1. Tile có bảng hằng số 2 ô (q, q′), chọn theo một bit trong request. Đổi hợp đồng tile; ước khoảng 130 LUT và 64 FF mỗi
   tile (chưa đo).
2. Giữ hợp đồng: ở các lệnh đó, mỗi đa thức dùng tile cố định của nó. Mạng khi đó cần tới 25 nguồn đọc và 18 nguồn ghi
   (thay vì 16 và 12), ước to hơn khoảng 1,5 lần ở phần đọc/ghi (chưa đo).

**Còn lại:** mạng root (3 600 LUT) nay là phần lớn nhất; chưa thử thu hẹp. Thanh ghi giữ cho đọc lệch ở N = 1024 lane 32
bit có thể cần 2 ô thay vì 1 (mô hình chỉ đếm chu kỳ, chưa mô phỏng tới mức cổng).

## 17. Hai ô modulus mỗi tile (31/10/2026)

Người dùng chọn cho tile giữ hai prime (lệnh nhiều prime N = 8..32 với mạng có cấu trúc). Hợp đồng tile mục 3: thanh ghi
hằng số hai ô, cổng `cfg_slot` (ô được ghi) và `req_slot` (ô của request). RTL [hdl/tile/tile_thu.sv](../../hdl/tile/tile_thu.sv)
(hash `9c9082575083813e`): bit ô đi theo request qua pipeline, mỗi tầng chọn q, q′ theo bit của phép đang ở tầng đó.

**Một lỗi viết RTL tìm ra khi kiểm:** lúc đầu tôi chọn q bằng một hàm đọc thẳng q0/q1 của module. Với phép gán liên tục,
trình mô phỏng chỉ tính lại khi đối số đổi, nên khi bit ô luôn bằng 0 thì q bị kẹt ở giá trị lúc khởi động: kiểm thử thường
sai hết, kiểm thử trộn lại đạt. Phần cứng tổng hợp ra vẫn đúng, nhưng đây là chỗ mô phỏng và tổng hợp khác nhau, nên đã
viết lại thành mux trực tiếp.

**Kiểm thử:** testbench thêm `+MIX=1` (ghi hai prime vào hai ô, trộn ngẫu nhiên request, có dừng và request thưa) và lỗi cài
vào `FAULT_IGNORE_SLOT`. Bốn cấu hình × hai biến thể: mỗi cấu hình 68 lần chạy đạt, 28/28 lỗi bị bắt. Verilator sạch.

**Vivado (3,0 ns):** biến thể 3 (v1): 1 052 LUT, 1 126 FF, 11 DSP, WNS +0,182 ns (trước 932 / 1 036: thêm 120 LUT, 90 FF);
biến thể 1: 1 155 LUT, 1 035 FF, 4 DSP, +0,230 ns.

**Cả phần tính + mạng (ước lượng, chưa gồm RAM và bộ điều khiển):** 16 × 1 052 + 9 397 ≈ **26 200 LUT, 176 DSP**, khoảng 2,1
lần HF-NTT 16 PE (12 671 LUT cả bộ tăng tốc). So với crossbar trước đó (≈ 50 500), giảm khoảng 48%.

## 18. Tối ưu thêm mạng bank → tile (31/10/2026)

**Mạng root.** Mỗi tile chọn 1 trong 24 root (8 bank gói × 3 phần tử). Phần tử đầu GM[g] của gói chỉ được dùng cho root 1
(các GM[g] khác đã có sẵn làm phần tử con của gói cha), mà root 1 là root chung của mọi butterfly ở tầng đầu NTT xuôi và
tầng cuối NTT ngược. Bộ sinh RTL nay đưa root 1 vào một thanh ghi chung do bộ điều khiển nạp ở đầu tầng, nên mỗi tile chọn
1 trong 17 nguồn và không phụ thuộc vị trí gói đầu của khe. Kiểm ngẫu nhiên 20 000 chu kỳ đạt. Vivado: mạng root khoảng
3 584 → **2 560 LUT**; cả mạng **9 397 → 8 371 LUT**, 6 370 FF, WNS +0,680 ns. Báo cáo cũ giữ ở `study/build/ntt_bank_net_s_v1/`.

Hệ quả phụ, chưa làm: RAM gói root có thể bỏ phần tử đầu (chỉ giữ root 1 riêng), tiết kiệm 1/3 dung lượng RAM root.

Hai cách khác đã thử và **không** dùng:
- Lưu root tuyến tính, mỗi root một ô, 16 hoặc 32 bank: mỗi tile vẫn cần mọi bank, vì root phụ thuộc chỉ số khối (các bit
  cao của địa chỉ) còn tile phụ thuộc các bit thấp.
- Đặt root vào bank của tile dùng nó, root dùng chung phát qua đường chung: ở các tầng giữa một chu kỳ có tới 8 root dùng
  chung; với 4 đường chung vẫn chậm 11%, còn muốn không chậm phải nhân bản bảng root nhiều lần (tốn BRAM nhiều hơn số LUT
  tiết kiệm).

**Hàm gán tile.** Tìm trong họ 512 hàm (chọn bit F thay vào nibble, thứ tự bit ở lane 32 bit) và 1 500 hàm ngẫu nhiên có
XOR thêm bit F vào chỉ số tile (581 hàm không xung đột, không chậm): **không hàm nào rẻ hơn** cách gán hiện tại theo ước
lượng số LUT của cây mux. Số nguồn hiện nay (16 mỗi cổng đọc, 12 mỗi cổng ghi) có vẻ là bản chất: mỗi cổng phải gom nguồn
của cả lane 16 lẫn lane 32 qua mọi tầng.

**Tổng phần tính + mạng:** 16 × 1 052 + 8 371 ≈ **25 200 LUT**, 176 DSP (chưa gồm RAM, sinh địa chỉ, bộ điều khiển); khoảng
2,0 lần HF-NTT 16 PE.

## 19. Thử hai hướng còn lại (31/10/2026)

### 19.1 Rút gọn lười

**Phân tích lại.** Ước lượng trước (bớt một bước trừ trong bộ cộng/trừ) sai: prime lane 32 bit dài tới 31 bit nên 4q vượt
32 bit, và giá trị phải giữ trong [0, 2q). Khi đó mỗi đầu ra của bộ cộng/trừ vẫn cần đúng một bước trừ có điều kiện (trừ
2q thay vì q), nên bộ cộng/trừ không rẻ hơn. Phần bỏ được là **bước trừ q cuối của Montgomery**: với a < 2q, root < q và
2q < R, kết quả u = (T + m·q)/R < 2q, nằm sẵn trong miền [0, 2q).

**Cận trên đo được** (bản sao RTL bỏ hẳn bước trừ cuối ở cả hai lane, chỉ để đo diện tích, không đúng chức năng;
Vivado 2018.1, 3,0 ns):

| | Hiện tại | Bỏ bước trừ cuối | Chênh |
|---|---:|---:|---:|
| Biến thể 3 (v1): LUT / FF | 1 052 / 1 126 | 894 / 1 172 | −158 LUT (−15%) |
| Biến thể 1: LUT / FF | 1 155 / 1 035 | 1 039 / 1 031 | −116 LUT |

Khoản bớt lớn hơn dự kiến vì bỏ luôn được mux chọn q theo ô đi kèm bước trừ đó.

**Nếu làm thật** (chưa làm, cần đổi hợp đồng số học):
- Hệ số giữa các tầng nằm trong [0, 2q); tile nhận đầu vào trong [0, 2q).
- Bộ cộng/trừ chọn mốc 2q ở các tầng giữa và q ở tầng cuối (và ở đầu ra chế độ 2, đi qua bộ cộng/trừ đang rảnh), nên đầu ra
  cuối vẫn rút gọn hết, **không cần lượt chuẩn hóa thêm**. Thêm một mux mốc q/2q, nên khoản bớt thực tế ước khoảng 120 LUT
  mỗi tile (khoảng 1 900 cho lõi).
- Lane 16 bit chỉ dùng được khi 2q < 2¹⁶ (3329, 12289 được; q lớn hơn 2¹⁵ thì không), vì ô nhớ 16 bit.
- Phải sinh vector có đầu vào trong [0, 2q) và kiểm cả hai mốc.

### 19.2 Thước đo DSP so với LUT cho lane 32 bit

Số đo của tile hai ô (mục 17) và mạng (mục 18). SEC theo cách tính của các bài so sánh (PIP-NTT): slice ≈ 0,25 × LUT +
0,125 × FF; SEC = slice + 100 × DSP + 200 × BRAM. Thời gian sinh khóa N1024 lấy từ `fn_dsa_workload_mot_lan.md`.

| Lane 32 bit | LUT / FF / DSP mỗi tile | SEC mỗi tile | Lõi (16 tile + mạng): LUT | DSP | SEC | Sinh khóa (chu kỳ) | SEC × thời gian sinh khóa | SEC × thời gian ký |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Trên mảng (biến thể 1) | 1 155 / 1 035 / 4 | 818 | 26 851 | 64 | 15 979 | 1 499 233 | 23 956 | 2 077 |
| Bộ riêng (biến thể 3, v1) | 1 052 / 1 126 / 11 | 1 504 | 25 203 | 176 | 26 949 | 1 253 463 | 33 780 | 3 502 |

- Theo LUT (thước đo đã khóa của giả thuyết 2): bộ riêng rẻ hơn 6,5% ở cấp lõi.
- Theo SEC: trên mảng chỉ bằng **0,59 lần** bộ riêng. Theo SEC × thời gian sinh khóa: **0,71 lần**, dù sinh khóa chậm hơn
  20%; với ký (chỉ FFT) là 0,59 lần.
- Đổi thước đo của giả thuyết 2 sau khi đã biết kết quả là chỉnh về đáp án; nếu đổi phải ghi rõ trong bảng lịch sử và
  trong bài. Đây là quyết định của người dùng.

### 19.3 Rút gọn lười: thử cách làm đúng, kết luận không dùng

Đầu ra NTT phải khớp từng bit với NTRUGen / FN-DSA, tức nằm trong [0, q). Bỏ bước trừ cuối của Montgomery (mục 19.1)
khiến tầng cuối ra giá trị trong [0, 2q), nên phải rút gọn lần cuối. Đã thử cả hai cách:

| Cách rút gọn lần cuối | LUT tile (v1) | Timing 3,0 ns | Thời gian |
|---|---:|---|---|
| Hiện tại (Montgomery trừ q cuối) | 1 052 | đạt, +0,182 ns | — |
| (a) Bỏ trừ cuối của Montgomery, thêm bước chỉnh z0, z1 ở đầu ra tile, bật ở tầng cuối | 1 047 | **trượt, −0,466 ns** | không đổi nếu thêm một tầng thanh ghi (thêm FF, độ trễ +1) |
| (b) Bỏ trừ cuối, thêm một lượt chuẩn hóa sau mỗi NTT | khoảng 930 (ước lượng) | đạt (ước lượng) | phần NTT của sinh khóa +29%, cả sinh khóa N1024 +15% |

(a) đo bằng bản sao RTL chỉ để đo diện tích (không kiểm chức năng, không lưu trong dự án); (b) ước lượng theo mô hình cấp dữ liệu,
mỗi lượt chuẩn hóa là N phép nhân modulo trên 16 tile cộng độ trễ.

**Kết luận:** (a) không tiết kiệm và làm trượt timing; (b) bớt khoảng 7% LUT phần tính + mạng nhưng sinh khóa chậm 15%, tích
diện tích × thời gian xấu hơn. **Không đổi hợp đồng số học.** Ước lượng ban đầu (bớt 1 100–1 600 LUT) là sai: bỏ qua việc
đầu ra phải rút gọn hết.

## 20. Tối ưu vi mô trong tile (31/10/2026)

Mỗi tối ưu thử trên bản sao RTL, đo riêng bằng Vivado 2018.1 (3,0 ns, biến thể 3 = v1), chỉ giữ cái có lợi. Gốc: tile hai ô
modulus, 1 052 LUT.

| Thử | LUT | Ghi chú |
|---|---:|---|
| A: tích thô / FFT 32 bit đi qua tầng thanh ghi toán hạng | 1 056 | mux chuyển chỗ, không bớt; **bỏ** |
| C: lane 16 bit chỉ dùng ô modulus 0 | 1 008 | bỏ ba mux chọn q; đổi nhỏ hợp đồng (lệnh nhiều prime chỉ ở lane 32 bit) |
| E: cộng hai tích chéo vào tích ghép 32×32 bằng một phép cộng ba toán hạng | 1 009 | +32 FF |
| C + E | 980 | **giữ** |
| F (trên C + E): bước trừ q cuối của Montgomery lấy điều kiện từ bit dấu của u − q | **913** | bỏ bộ so sánh riêng ở cả hai lane; **giữ** |
| G (trên F): bit làm tròn FFT 32 bit đưa vào chân nhớ của phép cộng ghép tích | 908 | trong nhiễu đặt cell, biến thể 1 còn tăng, timing kém hơn; **bỏ** |

**RTL sau tối ưu** ([hdl/tile/tile_thu.sv](../../hdl/tile/tile_thu.sv), hash `e1d97d2a6dd476b2`, testbench `e177c81a706cff5d`):
- biến thể 3 (v1): **913 LUT**, 1 155 FF, 11 DSP, WNS +0,234 ns (−13% LUT so với 1 052);
- biến thể 1: 1 046 LUT, 1 063 FF, 4 DSP, WNS +0,187 ns;
- regression bốn cấu hình (mặc định, `EN_REG`, `IN_REG`, `LEAF_PD = 4`): mỗi cấu hình 66 lần chạy đạt, 26/26 lỗi bị bắt (phép
  trộn hai prime và lỗi bỏ qua ô nay chỉ chạy trên vector lane 32 bit); Verilator sạch.

**Tổng phần tính + mạng:** 16 × 913 + 8 371 ≈ **23 000 LUT**, 176 DSP (chưa gồm RAM, sinh địa chỉ, bộ điều khiển); khoảng
1,8 lần HF-NTT 16 PE. Theo SEC: v1 khoảng 26 450, biến thể 1 khoảng 15 600 (0,59 lần).

## 21. Hướng "một lane 32 bit" (31/10/2026, thử nghiệm diện tích, chưa áp dụng)

Ý tưởng: bỏ phân biệt lane 16 / 32 bit trong đường tính. Mọi NTT, kể cả q = 3329 / 12289, đi qua bộ Montgomery 32 bit riêng
(R = 2³²), và hệ số 16 bit lưu trong bộ nhớ như hệ số 32 bit (định dạng 4, mỗi hệ số một siêu bank). "16 bit" chỉ còn nghĩa là q
nhỏ.

**Đo trên bản sao RTL / mạng sinh lại** (Vivado 2018.1, 3,0 ns; bản sao không lưu trong dự án):

| | Hiện tại | Một lane 32 bit | Chênh |
|---|---:|---:|---:|
| Tile (v1): LUT / FF / DSP | 913 / 1 155 / 11 | **777** / 1 004 / 11 | −136 LUT (−15%) |
| Mạng: LUT (đọc / ghi / root) | 8 371 (3 432 / 2 585 / 2 560) | **6 193** (2 257 / 1 568 / 2 560) | −2 178 (−26%) |
| Số nguồn mỗi cổng đọc nửa thấp / ghi (lớn nhất) | 16 / 11 | 6 / 7 | |
| Phần tính + mạng | ≈ 23 000 LUT | **≈ 18 600 LUT** | −19%; khoảng 1,5 lần HF-NTT 16 PE |
| WNS | +0,234 / +0,680 ns | +0,261 / +0,690 ns | đều đạt |

Tile một lane kiểm nhanh trên `ntt32.txt` (gồm q = 12289 đặt ở lane 32 bit): 5 486 ca đạt.

**Cái giá (cần người dùng quyết):**
- Số học: q nhỏ dùng R = 2³², q′ = −q⁻¹ mod 2³². Kết quả NTT không đổi (twiddle lưu ở dạng Montgomery với R mới), nhưng phép nhân
  từng điểm kiểu Montgomery R = 2¹⁶ của FN-DSA (`mq_poly_montymul_ntt`, `mq_poly_tomonty`) cần thêm một lượt nhân hằng 2⁴⁸ mod q
  để giữ đúng kết quả.
- Bộ nhớ và giao diện: dữ liệu 16 bit chiếm gấp đôi ô nhớ và dòng host cho các kernel đó (định dạng 3 → 4); thay đổi giao diện
  host.
- Độ trễ NTT q nhỏ mỗi lượt 13 → 15 chu kỳ (thêm khoảng 2 chu kỳ mỗi tầng).
- Câu chuyện: thiết kế v1 không còn rút gọn trên mảng nhân ở bất kỳ lane nào; bù lại một lane nhận mọi q lẻ < 2³¹.
