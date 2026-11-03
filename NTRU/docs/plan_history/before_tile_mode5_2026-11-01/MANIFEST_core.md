# Manifest triển khai — lõi NTT tối thiểu

RTL: [ntt_core.sv](ntt_core.sv) và bảng sinh tự động [ntt_core_gen.sv](ntt_core_gen.sv)
([scripts/gen_ntt_core.py](../../scripts/gen_ntt_core.py)), ROM gói root `root_pack_b0..3.mem`. Lịch chu kỳ:
[model/ntt_core_sched.py](../../model/ntt_core_sched.py). Viết ngày 01/11/2026 bởi trợ lý, cùng tác giả với testbench.

## Phạm vi

| Có | Chưa làm (kiểm thử ghi "chưa chạy") |
|---|---|
| NTT (0x5) và NTT ngược (0x6), một đa thức | Nhiều đa thức trong một lệnh, xen kẽ hai đa thức (dự báo "xen kẽ ≤ 240" của giả thuyết 4) |
| Profile 0 (12289, logn 3..10), 1 (3329, logn 3..8, 7 tầng ở N = 256), 2 (8380417, logn 8) | Profile 3, nạp prime 0x9, khe prime |
| Vùng nhớ A, dạng 4 | Phép 0x7, 0x8; vùng B, C; địa chỉ trong lệnh |
| Cổng host đơn giản: một dòng 128 bit mỗi lần, chỉ khi rảnh | Giải mã lệnh và mã lỗi của spec 2.0 (chỉ có cờ lỗi cho tổ hợp không hỗ trợ); cổng host có pipeline |
| 16 tile trên mảng lệch pha, mạng 4 bank gói root | FFT (mọi độ rộng) |

## Cách làm

- **Lịch:** mỗi tầng (khoảng cách h), tile t chạy các butterfly i = p_t xor K(k), k = 0 .. 2^kdim − 1, với p_t và cơ sở
  K lấy từ bảng tầng. Ánh xạ butterfly → tile là affine trên GF(2) ở cả 110 tầng (mô hình kiểm), nên mọi tile ở cùng k
  đọc một bản dịch của tập siêu bank ở k = 0, không xung đột. Tile t nhận ở chu kỳ có (t / 6 + chu kỳ) mod 3 = 0.
- **Pipeline:** tầng địa chỉ → đọc RAM và ROM gói → chọn ở mạng → tile nhận; kết quả sau 19 chu kỳ → chọn ghi → ghi RAM.
  Tầng khoảng cách 512 (N = 1024; x, y cùng siêu bank): đọc x sớm một chu kỳ và giữ ở mạng (`hold_x`), ghi y trễ một
  chu kỳ (kết quả của tile đứng yên 3 chu kỳ).
- **Chồng tầng** (từ lần 3, [model/ntt_core_overlap.py](../../model/ntt_core_overlap.py)): tầng sau bắt đầu sau tầng trước một
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

## Kiểm thử

[sim/core_ntt/run.sh](../../sim/core_ntt/run.sh): 48 ca vàng (1.0 `kernel_fixtures.jsonl` cho profile 0, 1, mỗi logn
một ca mỗi chiều; tài sản kernel 2.0 cho 8380417, 10 ca mỗi chiều). Kiểm thêm: mọi request gặp tile sẵn sàng.

Lần chạy 1, 01/11/2026 (RTL `ecd9bc98a924b212`, bảng `59fb3b393559f742`, testbench `6732389499a3c7b6`, Icarus
Verilog 14.0): **48/48 khớp**, không request nào gặp tile chưa sẵn sàng. Lần chạy 2 (RTL `34fe7264b39a7c05`, bảng
`ab7b54e93516cc4d`, sau khi sửa timing ở dưới): 48/48 khớp, chu kỳ không đổi. Lần chạy 3 (chồng tầng, RTL `275aa612b8066a4c`,
bảng `6b1636f7504f77f6`): 48/48 khớp; chu kỳ (a) trùng từng chu kỳ với [mô hình chồng tầng](../../study/results/ntt_core_overlap.md).

## Số đo (Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, 3,0 ns, sau route; `fpga/zcu106/ntt_core.tcl`)

| Bản | LUT | FF | DSP | BRAM tile (RAMB18) | URAM | WNS |
|---|---:|---:|---:|---:|---:|---:|
| Lần 1 (`ecd9bc98`) | 25 944 | 12 710 | 64 | 32 (64) | 0 | **−1,244 ns** |
| Lần 2 (`34fe7264`) | **17 493** | 13 191 | 64 | 38 (76) | 0 | **+0,200 ns** |
| Lần 3, chồng tầng (`275aa612`) | **17 748** | 13 408 | 64 | 38 (76) | 0 | **+0,098 ns** |

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
