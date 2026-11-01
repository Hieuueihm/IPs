> Bản lưu trước khi dọn tài liệu ngày 01/11/2026. Các con số và quyết định thuộc những phiên bản được ghi bên dưới.

# Manifest triển khai — lõi NTT tối thiểu

RTL: [ntt_core.sv](../../../hdl/core_ntt/ntt_core.sv) và bảng sinh tự động [ntt_core_gen.sv](../../../hdl/core_ntt/ntt_core_gen.sv)
([scripts/gen_ntt_core.py](../../../scripts/gen_ntt_core.py)), ROM gói root `root_pack_b0..3.mem`. Lịch chu kỳ:
[model/ntt_core_sched.py](../../../model/ntt_core_sched.py). Viết ngày 01/11/2026 bởi trợ lý, cùng tác giả với testbench.

## Phạm vi

| Có | Chưa làm (kiểm thử ghi "chưa chạy") |
|---|---|
| NTT (0x5) và NTT ngược (0x6), một đa thức; FFT (0x0) và FFT ngược (0x1) định dạng 0 (32 bit), logn 0..10 | Nhiều đa thức trong một lệnh, xen kẽ hai đa thức (dự báo "xen kẽ ≤ 240" của giả thuyết 4) |
| Profile 0 (12289, logn 3..10), 1 (3329, logn 3..8, 7 tầng ở N = 256), 2 (8380417, logn 8) | Profile 3, nạp prime 0x9, khe prime |
| Vùng nhớ A, dạng 4 | Phép 0x7, 0x8; vùng B, C; địa chỉ trong lệnh |
| Cổng host đơn giản: một dòng 128 bit mỗi lần, chỉ khi rảnh | Giải mã lệnh và mã lỗi của spec 2.0 (chỉ có cờ lỗi cho tổ hợp không hỗ trợ); cổng host có pipeline |
| 16 tile trên mảng lệch pha, mạng 4 bank gói root | FFT 64 / 128 bit (định dạng 1, 2), FFT NTRUGen (định dạng 5), CMUL, SPLIT, MERGE |

## Cách làm

- **Lịch:** mỗi tầng (khoảng cách h), tile t chạy các butterfly i = p_t xor K(k), k = 0 .. 2^kdim − 1, với p_t và cơ sở
  K lấy từ bảng tầng. Ánh xạ butterfly → tile là affine trên GF(2) ở cả 110 tầng (mô hình kiểm), nên mọi tile ở cùng k
  đọc một bản dịch của tập siêu bank ở k = 0, không xung đột. Tile t nhận ở chu kỳ có (t / 6 + chu kỳ) mod 3 = 0.
- **Pipeline:** tầng địa chỉ → đọc RAM và ROM gói → chọn ở mạng → tile nhận; kết quả sau 19 chu kỳ → chọn ghi → ghi RAM.
  Tầng khoảng cách 512 (N = 1024; x, y cùng siêu bank): đọc x sớm một chu kỳ và giữ ở mạng (`hold_x`), ghi y trễ một
  chu kỳ (kết quả của tile đứng yên 3 chu kỳ).
- **Chồng tầng** (từ lần 3, [model/ntt_core_overlap.py](../../../model/ntt_core_overlap.py)): tầng sau bắt đầu sau tầng trước một
  số chu kỳ lấy từ bảng tầng (kèm thứ tự cơ sở nhân của từng tầng), thay vì chờ lần ghi cuối. Mô hình chọn khoảng nhỏ nhất
  sao cho: mọi hệ số đọc sau lần ghi tạo ra nó; không xung đột bank đọc, ghi, bank gói giữa các tầng đang chạy; mỗi tile nhận
  đúng thứ tự; và mọi butterfly của tầng cũ đã phát trước khi đổi bảng (đổi cho cả lõi cùng lúc). Địa chỉ ghi của mỗi
  butterfly đi qua một FIFO 16 ô của tile (đẩy lúc phát, lấy lúc có kết quả); cờ cùng siêu bank đi theo từng butterfly.
  Tầng đầu bắt đầu ở pha 2 của bộ đếm khe (pha mô hình đã dùng). Lỗi đã gặp và sửa: bản đầu của mô hình chưa có điều kiện
  cuối, nên ở N1024 ngược tầng cuối bắt đầu sớm hơn một chu kỳ và 4 butterfly của tầng trước không bao giờ được phát.
- **NTT ngược:** tile chia đôi nhánh tổng ở mọi tầng, root ngược trong ROM đã nhân 2⁻¹ mod q, nên không có lượt chuẩn
  hóa; kết quả bằng 1.0 (nhân R·2⁻ᴸ ở cuối).
- **Root:** ROM gói 4 bank × 384 dòng × 96 bit (profile 0 / 1 / 2, xuôi rồi ngược). Root 12289 / 3329 là bảng 1.0 nhân
  2¹⁶ mod q (R = 2³²). Root 1 lấy từ hằng số, không đọc ROM.

## FFT 32 bit (01/11/2026)

Cách (A) đã chọn ([study/results/fft_core_plan.md](../../../study/results/fft_core_plan.md)): mỗi tile làm trọn một butterfly
phức bằng **chế độ 5 của chính tile** (hợp đồng tile mục 4.7); lõi chỉ cấp toán hạng, root và địa chỉ ghi. Lịch:
[model/fft_core_sched.py](../../../model/fft_core_sched.py).
- Tile của butterfly = tile gán theo bank của cặp phần thực (bảng tầng NTT cho logn − 1); cặp ảo nằm xa hn phần tử, mạng
  thêm nguồn cho nó (đọc trung bình 4,5 → 8,75 nguồn mỗi cổng, lớn nhất 16; ghi 4,5 → 8,75, lớn nhất 14).
- Dữ liệu đọc cùng nhịp ở mọi tile (không xung đột); root đọc trước dữ liệu 2 chu kỳ, lệch theo nhóm (t >> 2) mod 3, mỗi
  từ ROM một root ({wi, wr} ở hai "ô con" của gói NTT), ROM gói hai cổng (tile 0..7 cổng a, 8..15 cổng b); root chờ trong
  thanh ghi `op_w` 64 bit của mạng (tín hiệu `load_w`). Không xung đột cổng ROM.
- Tầng cuối FFT ngược: cờ chia ở nhịp, tile làm div2e. Rào chắn mỗi tầng.
- Đã thử rồi bỏ: (1) một khối `fft_lane` riêng ở mỗi tile: 51 049 LUT, WNS −0,766 ns; (2) cùng khối đó với bộ cộng dùng chung
  theo thời gian; (3) chế độ 5 với mux bắt root 64 bit ở lõi: 38 407 LUT. Bản sao trong `study/build/`.

## Kiểm thử

[sim/core_ntt/run.sh](../../../sim/core_ntt/run.sh): 48 ca vàng (1.0 `kernel_fixtures.jsonl` cho profile 0, 1, mỗi logn
một ca mỗi chiều; tài sản kernel 2.0 cho 8380417, 10 ca mỗi chiều). Kiểm thêm: mọi request gặp tile sẵn sàng.

Lần chạy 1, 01/11/2026 (RTL `ecd9bc98a924b212`, bảng `59fb3b393559f742`, testbench `6732389499a3c7b6`, Icarus
Verilog 14.0): **48/48 khớp**, không request nào gặp tile chưa sẵn sàng. Lần chạy 2 (RTL `34fe7264b39a7c05`, bảng
`ab7b54e93516cc4d`, sau khi sửa timing ở dưới): 48/48 khớp, chu kỳ không đổi. Lần chạy 3 (chồng tầng, RTL `275aa612b8066a4c`,
bảng `6b1636f7504f77f6`): 48/48 khớp; chu kỳ (a) trùng từng chu kỳ với [mô hình chồng tầng](../../../study/results/ntt_core_overlap.md).

Lần chạy 4 (FFT 32 bit, RTL `677796d0c00d7eae`, tile `29326f6d2523a117`): 48/48 NTT và 18/18 FFT định dạng 0 (1.0 `kernel_fixtures.jsonl`,
logn 2..10, xuôi và ngược; logn 0, 1 là đồng nhất, lõi báo xong ngay). FFT: (a) = 14 / 29 / 44 / 59 / 74 / 107 / 167 / 287 /
539 chu kỳ cho N = 4 .. 1024, như nhau hai chiều, trùng mô hình từng chu kỳ; độ trễ đọc → ghi một butterfly 14.

## Số đo (Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, 3,0 ns, sau route; `fpga/zcu106/ntt_core.tcl`)

| Bản | LUT | FF | DSP | BRAM tile (RAMB18) | URAM | WNS |
|---|---:|---:|---:|---:|---:|---:|
| Lần 1 (`ecd9bc98`) | 25 944 | 12 710 | 64 | 32 (64) | 0 | **−1,244 ns** |
| Lần 2 (`34fe7264`) | **17 493** | 13 191 | 64 | 38 (76) | 0 | **+0,200 ns** |
| Lần 3, chồng tầng (`275aa612`) | **17 748** | 13 408 | 64 | 38 (76) | 0 | **+0,098 ns** |
| Lần 4, thêm FFT 32 bit qua chế độ 5 (`677796d0`) | **33 423** | 22 076 | 64 | 44 (88) | 0 | **−0,061 ns** |

Đường găng lần 4: `dir` → mux toán hạng → bộ cộng/trừ modulo (cộng rồi trừ q, nối tiếp) → đường dữ liệu phụ chế độ 5
(`d_sd5`, shift-register LUT). Hai cách sửa đã thử và bỏ (RTL giữ như lần 4):
- viết phần hiệu chỉnh thành tổng ba đầu vào a + b − q để chạy song song với a + b: Vivado vẫn dựng hai chuỗi carry nối
  tiếp; 34 981 LUT, WNS −0,034 ns;
- cho `d_sd5` lấy tổng thô a + b (chế độ 5 có q = 0) qua một thanh ghi riêng: 35 058 LUT, WNS −0,250 ns (đường găng chuyển
  sang chỗ khác, xếp đặt xấu hơn).

Lần 1 không đạt: đường dài nhất đi từ `hlog` qua bảng tầng (tổ hợp), cờ `same`, mux chọn tầng, tới địa chỉ ROM gói
(12 mức logic); ROM gói thành LUT-ROM; cổng host chọn 1 trong 8 làn cho mỗi bank. Lần 2: bảng tầng nạp vào thanh ghi
trước một tầng; siêu bank và bank gói giải mã one-hot ở tầng địa chỉ; cổng host theo làn cố định (ô 8l + j luôn ở bank
có 3 bit thấp bằng j); ROM gói khai báo `rom_style = "block"` (cùng cách file RAM cũ dùng `ram_style`).

Phân bổ lần 2 (báo cáo phân cấp; Vivado dời logic qua ranh giới module nên chỉ là ước lượng): 16 tile 10 092 LUT / 7 696
FF / 64 DSP (chỉ còn đường NTT vì chế độ cố định là 4; tile đo riêng có cả FFT nên lớn hơn); phần còn lại (bộ nhớ, ROM gói,
mạng, định tuyến, điều khiển, cổng host) 7 401 LUT. RAM vùng A: 64 RAMB18; ROM gói: 12 RAMB18.

## Chu kỳ (giả thuyết 4, cách đo đã ghi trước ở kiến trúc mục 6)

(a) = từ lần đọc RAM đầu tới lần ghi RAM cuối, cộng 1; (b) = từ lúc nhận lệnh tới lúc báo xong.

| Lệnh | (a) rào chắn (lần 1, 2) | (a) chồng tầng (lần 3) | (b) lần 3 | Mô hình khóa (lần 6) | Ngưỡng ≤ 1,25 × mô hình | Kết quả |
|---|---:|---:|---:|---:|---:|---|
| q12289 N1024, xuôi / ngược | 1 182 / 1 182 | 983 / 984 | 987 / 986 | 1 173 | 1 466 | đạt (0,84 ×) |
| q12289 N512, xuôi / ngược | 630 / 630 | 460 / 457 | 464 / 460 | 621 | — | |
| q12289 N256, xuôi / ngược | 368 / 368 | 249 / 245 | 252 / 249 | 360 | 450 | đạt (0,69 ×) |
| q8380417 N256, xuôi / ngược | 368 / 368 | 249 / 245 | 251 / 247 | 360 | 450 | đạt |
| q3329 N256 (7 tầng), xuôi / ngược | 322 / 322 | 225 / 221 | 228 / 225 | 315 | — | |
| Hai đa thức xen kẽ | — | — | 192 mỗi đa thức | 240 | **chưa chạy** |

Lần 3: (a) trùng từng chu kỳ với mô hình chồng tầng ở mọi ca; (b) dài hơn (a) 2–5 chu kỳ (chờ pha ở đầu lệnh). N ≤ 32 gần
như không lợi (0–2%): mỗi tầng phải chờ kết quả của tầng trước. Mô hình khóa của giả thuyết 4 tính theo rào chắn mỗi tầng,
nên lõi chồng tầng nhanh hơn chính mô hình.
