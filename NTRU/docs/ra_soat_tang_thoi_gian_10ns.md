# Rà soát các tầng chỉ thêm vào cho 5 ns, khi mục tiêu là 100 MHz

Ngày 03/11/2026. Bản rà soát: `experiments/a_cg_z020_share`, đo ở 10 ns: 30 349 LUT, 29 897 FF, 2 969 LUTRAM, 64 DSP,
48 RAMB18 sau place and route; WNS +0,576 ns, WHS +0,050 ns. Mục tiêu LUT là 30k, còn thiếu khoảng 350 LUT.

Tài liệu chỉ phân tích, chưa sửa RTL. Số FF đếm theo tên thanh ghi trong netlist tổng hợp ở 10 ns (`study/build/
a_cg_z020_share/ff10.txt`; tile 5 đại diện, nhân 16). Số chu kỳ tính bằng planner của bản share trên 1 026 case. Số LUT
là ước tính.

## 1. Kết luận ngắn

- Bỏ các tầng chỉ dùng cho 5 ns:
  - giảm khoảng **5 700 FF** (19 % FF);
  - giảm **1,2–1,5 % số chu kỳ kernel** (NTT 2,6–3,4 %, FFT 32 tới 5,3 %);
  - giảm 1–2 nhịp độ trễ lệnh và độ trễ đọc host.
- **LUT chỉ giảm khoảng 100–200.** Thanh ghi pipeline gần như không tốn LUT: bỏ thanh ghi thì phần logic giữa các tầng
  vẫn còn nguyên. Riêng việc này nhiều khả năng **không đủ** đưa lõi xuống dưới 30k.
- Hai việc lớn nhất đổi độ trễ tile (hợp đồng tile) nên cần duyệt:
  - bỏ tầng +1 của bản lat1;
  - bỏ thanh ghi vào của tile (`IN_REG`).

## 2. Danh sách

### 2.1 Trong tile

| Tầng | Thêm ở | Việc nó làm | FF (mỗi tile / toàn lõi) | Bỏ đi thì | Hợp đồng |
|---|---|---|---:|---|---|
| **Tầng +1 và bộ cộng/trừ hai nhịp** | `a_cg_z020_lat1` | Mọi yêu cầu qua thêm một thanh ghi (`rqd_x`, `rqd_y`, `rqd_root`, nhãn, beat); bộ cộng/trừ tách thành nhịp cộng và nhịp hiệu chỉnh (`sum_r`, `dif_r`, `q_r`) | ~210 / **~3 400** | GS −1, CT −2, FFT −1 nhịp. Chu kỳ kernel **−1,23 %** (NTT 32 −2,6 %, packed −3,1 %, FFT 32 −1,3 %). Hiệu chỉnh modulo lại nối tiếp sau phép cộng; hai chuỗi gộp với tổng FFT vẫn giữ được. LUT gần như không đổi | Có: độ trễ tile; planner `TILE_EXTRA`, `NTT_CT_EXTRA` về 0 |
| **Thanh ghi vào của tile** (`IN_REG = 1`) | trước z020 | Một thanh ghi sau khi nhận yêu cầu (`rdat`, `rroot`, nhãn, cờ), vì yêu cầu đi từ bank qua mạng tới tile | ~107 / **~1 700** | Mọi mode −1 nhịp. Cộng với dòng trên: chu kỳ kernel **−1,50 %** (FFT 32 −5,3 %, NTT packed −3,4 %). Tile đã có sẵn nhánh `IN_REG = 0`; khi đó +1 của NTRUGen nằm trước bộ cộng/trừ, ở 10 ns không sao | Có: độ trễ tile (tham số có sẵn) |
| Chương trình tích FFT chạy sớm một nhịp, tile đăng ký lại; địa chỉ limb đăng ký sẵn | `a_cg_z020_timing` | Chương trình tới bộ nhân từ thanh ghi cạnh tile | ~20 / ~300 | Nên **giữ**: mã chọn toán hạng 2 bit (`asel`, `bsel`) của bản share dựa vào chương trình sớm này, và chính nó giúp giảm LUT | Có |
| Nhánh trễ NTRUGen (`nhp0`, `nhp1`, `nlo_delay`) | trước z020 | Sắp lại thứ tự limb cho phép dịch của FFT 64 bit ngược | 318 / 5 088 | Không phải tầng timing, là chức năng | — |

### 2.2 Ở lõi

| Tầng | Việc nó làm | FF | Bỏ đi thì | Hợp đồng |
|---|---|---:|---|---|
| Thanh ghi yêu cầu `req_x`, `req_y` | Chọn 1 trong 4 bank cho mỗi đầu vào tile rồi đăng ký | 1 024 | Thay cho việc bỏ `IN_REG` của tile; **chỉ bỏ một trong hai**. Bỏ `IN_REG` lợi hơn (1 700 FF) và đã có sẵn tham số | — |
| Hai tầng lệnh ở cổng vào (`p_*`, `q_*`, `DONT_TOUCH`) | Chụp mọi trường của lệnh hai lần trước khi vào lõi | ~660 | Bỏ một tầng: −~330 FF, lệnh −1 nhịp. Phải sửa các kiểm tra rào chắn trong `synth.tcl` (yêu cầu đủ hai tầng) và testbench pipeline reset (`command_stages=2`) | Có: độ trễ lệnh (không đổi chức năng) |
| Tầng A của bộ chia div2e khi host đọc (`sa_line`, `sa_add`, `sa_c`) | Tính trước nhớ giữa các từ bằng cây AND, để phép cộng không chạy xuyên 4 từ | 176 | Đọc host −1 nhịp; ở 10 ns cộng thẳng bằng chuỗi nhớ cắt theo định dạng, bỏ cây AND: **−~40 LUT** | Đọc host −1 nhịp |
| Thanh ghi đáp ứng đọc ở cổng ra (`rsp_data_q`) | Đăng ký dữ liệu đọc trước khi ra cổng | 128 | Có thể gộp với tầng trên; nhưng nó cũng là rào chắn được kiểm tra trong `synth.tcl` | Đọc host −1 nhịp |
| Chọn từ host one-hot cho từng bank, đăng ký từ giá trị nhịp sau (`hsel`) | Cổng bank không phải so sánh | 128 | LUT gần như không đổi (cùng 128 phép so sánh) | — |
| Tầng chuẩn bị bản đồ host (`HPREP`, `bank_q`, `row_q`, `phase_q`, `oob_q`) | Mọi giá trị bản đồ là thanh ghi trước khi phục vụ dòng | ~100 | Mỗi dòng host −1 nhịp; LUT không đổi | Thời gian tải/đọc dòng |
| Hằng số theo lệnh đăng ký sẵn (`period_m2`, `planes_m1`, `stages_m1`, `last_k_r`, `wanted_desc`, `host_submask`, `total_words`, `pmask`, `host_rdoff`, `swap_mask`, ...) và cơ sở bản đồ host cho cả hai chiều (`bank_basis_r`) | So sánh với thanh ghi thay vì biểu thức | ~150 | Cơ sở bản đồ host chỉ cần tính cho chiều hiện tại: **−~45 LUT**. Phần còn lại LUT ±0, nên giữ | — |
| `cfg_ready`, `load_ready`, `read_ready`, `busy` từ thanh ghi nhịp sau | Tách cổng giao tiếp khỏi trạng thái | 4 | Tính thẳng từ trạng thái: **−~20 LUT** | — |
| Bản sao reset/cấu hình mỗi tile (`reset_local`, `config_local`) | Giảm fanout reset | 32 | Giữ: rẻ, và có kiểm tra trong `synth.tcl` | — |

## 3. Tổng nếu bỏ hết phần nên bỏ

Gồm: tầng +1 và bộ cộng/trừ hai nhịp, `IN_REG`, một tầng lệnh, tầng A của div2e, tính thẳng `ready`, cơ sở bản đồ host
một chiều, `hsel` tổ hợp.

| | Bản share ở 10 ns | Ước tính |
|---|---:|---:|
| FF | 29 897 | ~24 200 (−~5 700) |
| LUT | 30 349 | ~30 150 .. 30 250 (−100 .. −200) |
| Chu kỳ kernel, tổng 1 026 case | 559 565 | 551 184 (−1,50 %) |
| Độ trễ lệnh / đọc host | | −1 / −2 nhịp |

LUT vẫn có thể còn cao hơn 30k. Phần thiếu (khoảng 150–250 LUT) phải lấy từ một khối logic thật, không phải từ thanh ghi
pipeline. Các khối logic lớn nhất hiện nay:
- đường ghi 32 bank: khoảng 5 300 LUT;
- mạng đọc: khoảng 2 000;
- chọn từ khi host đọc: khoảng 1 200 (anh đã quyết định giữ nguyên);
- bộ dịch có điền dấu của div2e: khoảng 580.

## 4. Đề xuất thứ tự

1. Một đợt "bỏ tầng 5 ns", gồm các mục ở mục 3. Không đổi số học. Cần duyệt:
   - độ trễ tile: GS −2, CT −3, FFT −2 nhịp;
   - bỏ một tầng lệnh ở cổng vào.
2. Đo một lần ở 10 ns. Nếu LUT còn trên 30k, xét tiếp phần dịch của div2e hoặc đường ghi bank.

## 5. Kết quả đợt bỏ tầng (04/11/2026)

Bản `experiments/a_cg_z020_100mhz`, gồm mọi mục ở mục 3. Chi tiết trong README của bản đó.

Chức năng:
- 1 026 case khớp chính xác; số chu kỳ RTL bằng planner ở mọi case;
- 38 case bốn trạng thái; pipeline reset với một tầng lệnh;
- 74 lần gọi C, 14 tệp kết quả giống hệt, 4 chữ ký;
- bài kiểm tra mới ở mức tile cho cả hai slot modulus (lõi chỉ dùng slot 0).

Độ trễ tile so với bản share: NTT GS −2, NTT CT −3, FFT ngược −2, **FFT xuôi −3**. Ở mục 2 ước tính FFT −2, nhưng
trong bản share kết quả FFT xuôi đã đi qua bộ cộng/trừ hai nhịp, nên nó cũng được bớt nhịp đó.

Đo ở 10 ns, sau place and route:

| | Bản share | Sau đợt bỏ tầng | **Thêm bộ dịch div2e mới** |
|---|---:|---:|---:|
| LUT | 30 349 | 30 075 (−274) | **29 837** (−512) |
| FF | 29 897 | 24 139 | **24 115** (−5 782, −19,3 %) |
| LUTRAM / DSP / RAMB18 | 2 969 / 64 / 48 | 2 968 / 64 / 48 | 2 968 / 64 / 48 |
| WNS / WHS thanh ghi tới thanh ghi | +0,576 / +0,050 ns | +0,236 / +0,040 ns | **+0,032 / +0,051 ns** (đạt) |
| Chu kỳ kernel, tổng 1 026 case | 559 565 | 550 644 (−1,59 %) | 550 644 |
| Thời gian host toàn bộ trong testbench | 2 361 794 | 2 111 547 (−10,6 %) | 2 111 547 |

Chu kỳ theo mode: NTT −2,7 .. −3,5 %, FFT 32 −8,0 / −8,9 %, FFT 64 −1,5 .. −2,6 %, FFT 128 −0,3 / −0,4 %.

Một phát hiện về LUT. Lần đo đầu, LUT tăng +640: mỗi tile +48. Tổng hợp riêng một tile cho thấy:
- bỏ thanh ghi vào của tile không tốn LUT;
- bộ cộng/trừ một nhịp chỉ tốn thêm LUT vì q được chọn theo slot, và slot của kết quả CT được đọc từ bộ nhớ phụ.

Ở bản hai nhịp, thanh ghi `q_r` giữ sẵn q đã chọn. Bỏ thanh ghi đó thì phép chọn đi vào từng LUT của hai chuỗi hiệu chỉnh.
Khi lấy slot từ thanh ghi dịch `ks` (giá trị không đổi, hợp đồng giữ nguyên), mỗi tile còn 1 213 LUT, thấp hơn bản
share (1 222).

Sau đợt bỏ tầng, LUT còn cao hơn 30k khoảng 75. Bộ dịch div2e được viết lại:
- trước: dịch logic cả dòng 128 bit, rồi so sánh từng bit để thay bit tràn bằng dấu;
- sau: dịch số học từng giá trị qua hai tầng chọn 4:1 (theo s[1:0], rồi theo s[3:2]); bit nào có nguồn nằm trên đỉnh
  giá trị của nó thì lấy bit dấu.

Tổng hợp riêng, khối này giảm từ 378 xuống 291 LUT. Trong lõi, logic mức lõi giảm từ 7 414 xuống 7 161 LUT. Sau place
and route, toàn lõi còn **29 837 LUT, dưới mốc 30k**.

Đường găng mới là phép cộng làm tròn của div2e khi host đọc: chuỗi nhớ chạy qua bốn từ của giá trị 128 bit (35
CARRY4). Đường này đạt 10 ns nhưng chỉ dư 32 ps. Nó có từ khi bỏ tầng A của div2e trong đợt này. Nếu sau này không còn
đạt, có thể tạo nhớ vào mỗi từ bằng phép dò toàn bit 1 của các từ bên dưới ngay trong cùng nhịp (cây AND của bản
share, nhưng không có thanh ghi), tốn khoảng 50 LUT.
