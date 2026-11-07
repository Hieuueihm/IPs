# FFT và NTT dùng chung những gì: đo trên netlist bản XC7Z020

Ngày 03/11/2026. Bản đo: `experiments/a_cg_z020_hostdiv` (commit 1f3faab), netlist sau tổng hợp trên XC7Z020-CLG400-2.
Đây là bản được giữ: 35 777 LUT, khoảng 180 MHz sau place and route. Tài liệu chỉ phân tích, không đổi RTL.

## 1. Câu hỏi

Lõi chạy FFT 32 / 64 / 128 bit và NTT nhiều modulus trên cùng phần cứng. Câu hỏi là:
- phần cứng nào thật sự chạy ở cả hai mode;
- phần nào chỉ một mode dùng;
- việc dùng chung phải trả thêm bao nhiêu.

## 2. Cách đo

Netlist sau tổng hợp được xuất ra từng ô (LUT, CARRY4, MUXF7, FF, LUTRAM, SRL, DSP, block RAM) kèm dây nối giữa các ô.
- **Theo đầu ra.** Mỗi ô tổ hợp được lần theo hướng đi tới, đến các thanh ghi, bộ nhớ hoặc DSP mà nó cấp dữ liệu. Ô đó
  được chia đều cho các đích này. Đích là thanh ghi chỉ một mode dùng thì ô thuộc mode đó.
- **Theo đầu vào, khi đích là thanh ghi dùng chung.** Ô được lần ngược về các thanh ghi dữ liệu nuôi nó; các thanh ghi
  điều khiển (mode, chiều, định dạng, valid) bị bỏ qua.
  - chỉ có nguồn dùng chung: **dùng chung**;
  - có nguồn chỉ FFT dùng: **riêng FFT**;
  - có nguồn chỉ NTT dùng (ví dụ modulus q): **riêng NTT**;
  - có cả nguồn FFT lẫn nguồn NTT: **chọn mode**, tức bộ chọn đặt trước thanh ghi chung để nhận dữ liệu của mode đang chạy.
- **Đối tượng đo.** Đo một tile đại diện (tile 5) rồi nhân 16. Tile 0 lớn hơn vì Vivado đặt thêm logic cấp lõi vào đó;
  phần này đã được tính ở cấp lõi. Logic cấp lõi mà Vivado đặt trong tile (đường ghi bank) cũng tính ở cấp lõi.

Giới hạn:
- **Số LUT là số ô LUT.** Vivado báo ít hơn khoảng 9 % vì hai LUT nhỏ có thể gộp vào một LUT6: tile 5 có 1 695 ô LUT,
  báo cáo ghi 1 568; toàn lõi có 35 764 ô, báo cáo ghi 32 829 LUT logic. Vì vậy nên đọc tỉ lệ phần trăm.
- **Chia đều theo đích là xấp xỉ.** Một ô nuôi nhiều thanh ghi được chia đều cho các thanh ghi đó.
- **Không phải số đo của lõi đơn mode.** Mục 8 ước tính một lõi chỉ có FFT hoặc chỉ có NTT; muốn có số đo thật phải
  tổng hợp riêng từng lõi (ablation).

Script nằm ở `study/tools/mode_attrib/` (ba file Tcl xuất ô và dây, `attrib2.py` phân loại). Kết quả thô nằm ở
`study/build/a_cg_z020_hostdiv/attrib_modes.tsv`.

## 3. Một tile

| Nhóm | Khối | LUT | CARRY4 | FF | LUTRAM | SRL | DSP |
|---|---|---:|---:|---:|---:|---:|---:|
| **Dùng chung** | Mảng nhân 32×32: 4 lá, thanh ghi lá, cộng ghép ba toán hạng | 86 | 13 | 246 | | | 4 |
| | Bộ cộng/trừ: nhịp 1 và thanh ghi | 44 | | 69 | | | |
| | Thanh ghi vào, tầng toán hạng, tầng ra, bộ nhớ phụ, hằng | 41 | | 425 | 28 | 1 | |
| | *Cộng* | *171* | *13* | *740* | *28* | *1* | *4* |
| **Chọn mode** | Toán hạng vào bộ nhân (limb FFT hay lượt rút gọn NTT) | 64 | | | | | |
| | Đầu vào bộ cộng/trừ (T của FFT hay kết quả Montgomery) | 62 | 16 | | | | |
| | Tầng toán hạng | 64 | | | | | |
| | Tầng ra | 65 | | | | | |
| | *Cộng* | *255* | *16* | | | | |
| **Riêng NTT** | Rút gọn Montgomery: u, u − q, chọn, trễ T_hi | 130 | 20 | 103 | | 36 | |
| | Hiệu chỉnh modulo của cộng/trừ (a + b − q, a − b + q), chia đôi GS, đổi cặp packed 16 bit | 233 | 22 | 35 | | | |
| | Đưa T_lo, q′, q vào bộ nhân cho ba lượt rút gọn | 64 | | | | | |
| | Thanh ghi q, q′ | | | 64 | | | |
| | *Cộng* | *427* | *42* | *202* | | *36* | |
| **Riêng FFT** | Bộ nhớ limb và hai bộ cộng tổng o.re + o.im, wr + wi | 75 | 18 | 134 | 96 | | |
| | Chương trình tích: địa chỉ limb, bước | 50 | | 42 | | 11 | |
| | Bộ cộng dồn 68 bit | 106 | 17 | 109 | | | |
| | Tầng T của nhân phức 3M: p0 − p1, p0 + p1, p2 − (p0 + p1) | 138 | 18 | 38 | 32 | | |
| | Limb ra và bộ cộng/trừ wrap riêng của FFT thuận | 136 | 19 | 133 | | | |
| | Đếm beat, buffer, nhớ giữa limb | 20 | 1 | 19 | | | |
| | Phần FFT ở thanh ghi vào, tầng toán hạng, tầng ra, bộ nhớ phụ (gồm +1 và chọn của NTRUGen) | 118 | 8 | 6 | | | |
| | *Cộng* | *643* | *81* | *481* | *128* | *11* | |
| **Riêng NTRUGen** | FFT 64 bit ngược NTRUGen: giữ nửa thấp, các thanh ghi trễ 104–108 bit | 66 | 6 | 322 | | | |
| **Tổng tile** | | **1 562** | 158 | 1 745 | 156 | 48 | 4 |

Tỉ lệ trong một tile:

| | LUT | FF |
|---|---:|---:|
| Dùng chung | 11 % | 42 % |
| Chọn mode | 16 % | 0 |
| Riêng NTT | 27 % | 12 % |
| Riêng FFT | 41 % | 28 % |
| Riêng NTRUGen | 4 % | 18 % |

## 4. Cấp lõi

| Nhóm | Khối | LUT | MUXF7 | FF | Block RAM |
|---|---|---:|---:|---:|---:|
| **Dùng chung** | Đường ghi 32 bank: dữ liệu, hàng, enable; gồm phần Vivado đặt trong tile | 5 268 | 1 024 | | 32 |
| | Mạng đọc `req_x` / `req_y` / `req_root` | 1 991 | | 1 119 | |
| | Đọc host: chọn 32 → 1 cho 4 từ | 1 167 | 512 | 165 | |
| | Lịch tầng và địa chỉ | 770 | | 699 | |
| | Bản đồ host | 558 | 22 | 460 | |
| | Cấu hình, bộ nhớ root, frontend, điều khiển | 166 | | 975 | 16 |
| | *Cộng* | *9 920* | *1 558* | *3 418* | *48* |
| **Riêng FFT** | Chia div2e khi host đọc kết quả FFT ngược | 745 | | 494 | |
| | Chương trình tích FFT phát cho 16 tile | 82 | | 211 | |
| | Đếm beat FFT | 25 | | 15 | |
| | *Cộng* | *852* | | *720* | |
| **Riêng NTT** | Không có khối riêng đáng kể (packed 16 bit và NTT không đầy đủ nằm trong lịch tầng) | | | | |

## 5. Toàn lõi (tile × 16 + cấp lõi)

| | LUT (ô) | | FF | | LUTRAM | SRL | DSP | Block RAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dùng chung | 12 656 | 35 % | 15 258 | 48 % | 448 | 16 | **64** | **48** |
| Chọn mode | 4 080 | 11 % | 0 | | | | | |
| Riêng NTT | 6 832 | 19 % | 3 232 | 10 % | | 576 | | |
| Riêng FFT | 11 140 | 31 % | 8 416 | 26 % | 2 048 | 193 | | |
| Riêng NTRUGen | 1 056 | 3 % | 5 152 | 16 % | | | | |
| **Tổng** | 35 764 | | 32 058 | | 2 496 | 785 | 64 | 48 |

Báo cáo của Vivado: 32 829 LUT logic, 31 883 FF, 2 496 LUTRAM, 785 SRL, 64 DSP, 48 RAMB18.

## 6. Mỗi khối làm việc bao nhiêu phần thời gian

Tỉ lệ số nhịp đồng hồ khối đó làm việc có ích, trong một tile, khi lõi chạy liên tục:

| Khối | NTT 32 bit | NTT packed 16 bit | FFT 32 | FFT 64 | FFT 128 |
|---|---:|---:|---:|---:|---:|
| Mảng nhân (4 DSP) | 100 % (3 lượt / 3 nhịp) | 50 % (2 lá) | 100 % (3 tích / 3 nhịp) | 100 % (12 / 12) | 100 % (45 / 45) |
| Bộ cộng/trừ dùng chung | 33 % | 33 % | 67 % ngược, 0 thuận | 33 % ngược, 0 thuận | 18 % ngược, 0 thuận |
| Rút gọn Montgomery | 33 % | 33 % | 0 | 0 | 0 |
| Bộ cộng dồn FFT | 0 | 0 | 100 % | 100 % | 100 % |
| Tầng T, tổng, limb ra của FFT | 0 | 0 | 67 % | 33 % | 18 % |
| Mạng đọc và ghi bank | 33 % | 33 % | 67 % | 33 % | 18 % |

FFT thuận dùng bộ cộng/trừ wrap riêng (nằm trong "limb ra", mục 3), nên bộ cộng/trừ dùng chung nghỉ ở chiều này.

## 7. Vì sao phần LUT quanh bộ nhân không dùng chung được nhiều hơn

**Phần đắt nhất đã dùng chung hoàn toàn.** Gồm:
- 64 DSP: bận 100 % ở mọi mode, trừ NTT packed 16 bit;
- 48 block RAM;
- mạng đọc và ghi bank, cổng host, lịch tầng: khoảng 9 900 LUT.

Một lõi chỉ FFT và một lõi chỉ NTT đặt cạnh nhau sẽ cần gấp đôi tất cả những phần này.

**Phần LUT quanh bộ nhân khác nhau vì hai phép toán khác nhau về bản chất.**
- NTT: một tích 32 × 32, rồi rút gọn Montgomery (m = T_lo · q′, u = T_hi + (m q)_hi, u − q). Ba lượt chạy trên chính bộ
  nhân chung. Sau đó cộng/trừ có hiệu chỉnh modulo, và chia đôi ở GS.
- FFT: số 64 / 128 bit được xử lý tuần tự từng limb 32 bit.
  - Phải lưu limb để dùng lại cho 4 hoặc 15 tích limb.
  - Phải cộng dồn tích theo cột trong bộ cộng 68 bit.
  - Nhân phức kiểu 3M cần thêm hai tổng (o.re + o.im, wr + wi) và ba phép T.
  - Không có modulo; cộng/trừ wrap có nhớ giữa các limb.
- Hai bên chỉ trùng nhau ở bộ nhân và ở bộ cộng/trừ khi bỏ phần hiệu chỉnh. Những chỗ trùng này đã được dùng chung.

**Gộp thêm bộ cộng có lợi hay không tùy số nguồn.** Một bộ chọn 2 : 1 rộng 32 bit đứng riêng tốn khoảng 32 LUT, ngang
một bộ cộng (32 LUT + 8 CARRY4). Nhưng bộ chọn 2 : 1 đặt ở hai toán hạng của một bộ cộng hai toán hạng thì nằm gọn trong
LUT6 của chính bộ cộng, vì mỗi bit chỉ cần 5 đầu vào: 4 bit dữ liệu và 1 tín hiệu chọn. Netlist cho thấy điều này:
- `a` của bộ cộng/trừ dùng chung (chọn giữa đầu vào và dữ liệu phụ) nằm trong LUT3 của chuỗi cộng;
- u − q, o.re + o.im, wr + wi, p0 + p1 mỗi bit chỉ dùng LUT2, còn trống 4 đầu vào.

Điều đó đúng về số LUT, không đúng về timing. Khi đã làm (mục 11.4), LUT chứa bộ chọn không còn đặt sát CARRY4, và chuỗi
gộp tạo ra đường timing giữa hai mode (từ thanh ghi FFT tới thanh ghi NTT). Các đường này không bao giờ mang dữ liệu, vì
mode cố định trong một lệnh, nhưng timing tĩnh vẫn tính. Gộp chỉ không có lợi khi mỗi toán hạng có từ 3 nguồn trở lên, ví dụ `b` của bộ cộng/trừ dùng chung (y, T của FFT, kết quả
Montgomery) cần thêm một LUT mỗi bit. Thử chia thời gian các bộ cộng của FFT trước đây rơi vào trường hợp này. Cột "chọn
mode" (4 080 LUT, 11 %) là cái giá của phần đã dùng chung. Mục 11 tận dụng trường hợp có lợi.

## 8. Ước tính: lõi dùng chung so với hai lõi riêng

Giả sử mỗi lõi riêng giữ nguyên phần dùng chung và bỏ hết phần chọn mode:

| | LUT (ô) | FF | LUTRAM | DSP | Block RAM |
|---|---:|---:|---:|---:|---:|
| Lõi chỉ NTT: dùng chung + riêng NTT | 19 488 | 18 490 | 448 | 64 | 48 |
| Lõi chỉ FFT: dùng chung + riêng FFT + NTRUGen | 24 852 | 28 826 | 2 496 | 64 | 48 |
| Hai lõi riêng | 44 340 | 47 316 | 2 944 | 128 | 96 |
| **Lõi dùng chung (bản này)** | **35 764** | **32 058** | **2 496** | **64** | **48** |
| Chênh lệch | −8 576 (−19 %) | −15 258 (−32 %) | −448 | −64 (−50 %) | −48 (−50 %) |

Phần LUT tiết kiệm được bằng phần dùng chung (12 656) trừ đi phần chọn mode (4 080).

Đây là ước tính, không phải số đo. Trong lõi đơn mode, một phần của khối "dùng chung" có thể nhỏ đi: lõi chỉ NTT không
cần xử lý limb trong bản đồ host và lịch tầng; lõi chỉ FFT không cần NTT không đầy đủ. Vì vậy mức tiết kiệm thật có thể
thấp hơn. Muốn claim con số này trong bài báo thì phải tổng hợp riêng lõi chỉ NTT và lõi chỉ FFT từ cùng RTL.

## 9. Những chỗ dùng chung chưa hết (chỉ ghi nhận, chưa làm)

| Chỗ | Quy mô | Ghi chú |
|---|---|---|
| FFT thuận có bộ cộng/trừ wrap riêng, đặt cạnh bộ cộng/trừ dùng chung | khoảng 65 LUT + 16 CARRY4 mỗi tile, khoảng 1 000 LUT toàn lõi | Bộ dùng chung có hai nhịp và có phần hiệu chỉnh modulo. Muốn gộp thì phải xét lại độ trễ đường ra FFT thuận (hợp đồng tile) |
| Đường NTRUGen chỉ dùng cho FFT 64 bit ngược | 322 FF và 66 LUT mỗi tile; 5 152 FF (16 % FF toàn lõi) | Phần lớn là ba thanh ghi trễ rộng 104–108 bit. FF chưa phải giới hạn trên XC7Z020 (31 883 / 106 400) |
| NTT packed 16 bit chỉ dùng 2 trong 4 lá nhân | 50 % DSP nghỉ trong mode này | Bù lại, mỗi lượt xử lý hai butterfly |
| Hiệu chỉnh modulo và chia đôi là riêng NTT, nằm trong đường cộng/trừ | 233 LUT mỗi tile, khoảng 3 700 toàn lõi | Phần lớn nhất của "riêng NTT" |
| Chia div2e khi host đọc là riêng FFT | 745 LUT, 494 FF | Chủ yếu là phép dịch 128 bit có điền dấu |
| Bộ chọn mode | 255 LUT mỗi tile, 4 080 toàn lõi | Giảm được nếu dữ liệu FFT và NTT đi vào cùng vị trí thanh ghi sớm hơn |

## 10. Nên viết gì trong bài báo

- **Claim được:** FFT và NTT dùng chung toàn bộ 64 DSP, 48 block RAM, mạng dữ liệu, cổng host và điều khiển. Mảng nhân
  bận 100 % ở mọi mode trừ NTT packed 16 bit. Phần LUT: 35 % dùng chung, 11 % chọn mode, 19 % riêng NTT, 31 % riêng
  FFT, 3 % riêng NTRUGen (đếm theo ô, mục 5).
- **Chưa claim được:** con số tiết kiệm so với hai lõi riêng (mục 8). Cần tổng hợp lõi chỉ NTT và lõi chỉ FFT.
- **Không nên claim:** "đường dữ liệu dùng chung hoàn toàn". Trong tile, logic LUT quanh bộ nhân chủ yếu là riêng từng
  mode, và đó là do hai phép toán khác nhau.

## 11. Có tối ưu được phần riêng từng mode không

Các con số dưới đây là ước tính từ bảng mục 3, tính bằng ô LUT; số LUT Vivado báo thấp hơn khoảng 8 %. Hướng 1, 2, 3 đã làm
chung một đợt, kết quả đo ở mục 11.4.

### 11.1 Đáng làm

| # | Hướng | Mỗi tile | Toàn lõi | Đổi hợp đồng tile |
|---|---|---|---|---|
| 1 | FFT ra cùng đường với NTT | −100 .. −170 LUT, −140 FF | −1 600 .. −2 700 LUT, −2 200 FF | Có: độ trễ FFT ngắn lại |
| 2 | Gộp ba cặp bộ cộng "chỉ FFT" với "chỉ NTT" | −~100 LUT, −26 CARRY4 | −~1 600 LUT | Không |
| 3 | Chọn toán hạng bộ nhân bằng địa chỉ LUTRAM | −60 .. −100 LUT | −1 000 .. −1 600 LUT | Không |
| 4 | Giải mã chương trình tích FFT một lần ở lõi | −30 .. −40 LUT | −500 .. −600 LUT | Có: cổng chương trình FFT |

Cộng 1 đến 4: khoảng −4 700 .. −6 500 ô LUT, tương đương −4 300 .. −6 000 LUT theo báo cáo Vivado. Từ 35 777 LUT xuống
khoảng 29 800 .. 31 500, nghĩa là vào vùng mục tiêu 30k. Cột "chọn mode" giảm từ 16 % xuống khoảng 8 % LUT của tile.

**1. FFT ra cùng đường với NTT.**
- Hiện trạng:
  - Ở FFT thuận, bộ cộng/trừ dùng chung đã nhận đúng A và T (vì chiều thuận nối `side_t`, `t` vào nó), tính A + T, A − T,
    rồi kết quả bị bỏ.
  - Một bộ cộng/trừ wrap riêng (`fft_ct_addsub`) tính lại đúng hai giá trị đó.
  - Sau đó mỗi limb còn được giữ thêm một limb (`wy0p`, `wy1p`, `wgp`) trước khi ra.
- Việc giữ thêm một limb chỉ cần cho div2e: phép dịch lấy bit từ limb kế tiếp. div2e đã ra khỏi tile ở bản này, nên
  phần giữ lại không còn tác dụng; hiện nó chỉ giữ độ trễ cũ.
- Cách làm:
  - FFT thuận lấy kết quả của bộ cộng/trừ dùng chung theo đúng nhịp của NTT CT, tức một nhịp sau kết quả.
  - FFT ngược ra A + B và T theo nhịp của NTT GS, chia đôi chỉ bật ở NTT.
  - Nhãn lấy từ bộ nhớ phụ như NTT; nhớ giữa limb lấy từ bộ cộng/trừ dùng chung.
- Bỏ được: bộ cộng/trừ FFT riêng, bốn thanh ghi limb 32 bit, hai thanh ghi nhãn, bộ chọn limb, và gần hết bộ chọn mode
  ở tầng ra.
- Cái giá:
  - Độ trễ FFT của tile ngắn đi, nên planner và thời điểm ghi bank của FFT phải sửa.
  - Cần duyệt vì đổi hợp đồng tile.
  - Số chu kỳ FFT giảm nhẹ.

**2. Gộp ba cặp bộ cộng.** Mỗi cặp gồm một bộ cộng chỉ NTT dùng và một bộ chỉ FFT dùng, cùng độ rộng, cùng hai toán hạng.
Hai bộ không bao giờ chạy cùng lúc vì mode cố định trong một lệnh. Theo mục 7, bộ chọn đặt ở toán hạng không tốn thêm LUT.
- u − q (Montgomery) với p0 + p1 (tầng T);
- a + b − q (hiệu chỉnh tổng) với o.re + o.im;
- a − b + q (hiệu chỉnh hiệu) với wr + wi.

Chuỗi gộp phải giữ cả bit chặn ở bit 16 của NTT packed và nhớ giữa limb của FFT; cả hai đều đã có trong bộ cộng/trừ dùng
chung. Không đổi độ trễ. Rủi ro nằm ở timing: u − q là một đường còn trượt sau place and route, và chuỗi gộp nhận nguồn từ
hai vùng của tile.

**3. Chọn toán hạng bộ nhân bằng địa chỉ.**
- Hiện trạng:
  - Phía B chọn dữ liệu 32 bit giữa limb FFT (`wmw`), root NTT (`w1`), q′ và q.
  - Phía A chọn giữa limb FFT (`wmx`), `a1` và T_lo / m (`lfl`).
- Cách làm:
  - Ở FFT, `wmx` / `wmw` đã được ghi từ chính `a1` / `w1`. NTT ghi `a1`, `w1` vào một ô cố định của hai bộ nhớ này.
  - q, q′ được ghi vào hai ô cố định khi cấu hình tile.
  - Khi đó phía B chỉ còn chọn địa chỉ 4 bit; bộ nhớ LUTRAM vốn là một bộ chọn.
  - Phía A vẫn giữ một bộ chọn cho `lfl`, vì T_lo / m sinh ra và dùng ngay ở lượt sau.
- Không đổi độ trễ. Cần hai nhịp ghi lúc cấu hình (CONFIG_TILE và SETTLE), vì bộ nhớ chỉ có một cổng ghi.

**4. Giải mã chương trình tích một lần.** Địa chỉ limb (`mxa`, `mwa`, `msxa`, `mswa`, `msum`) giống nhau ở mọi tile đang
chạy. Hiện mỗi tile tự giải mã bảng tích. Lõi có thể giải mã một lần rồi phát địa chỉ đã giải mã, mỗi tile vẫn đăng ký
lại một lần như bây giờ. Việc này đổi cổng chương trình FFT của tile.

### 11.2 Có lợi nhưng rủi ro cao, để sau

**5. Bỏ bộ cộng ghép 32×32 riêng.**
- Có hai cách:
  - gộp nó vào bộ cộng dồn FFT: một bộ cộng 4 toán hạng 68 bit, ở NTT thì giá trị khởi đầu là 0;
  - dùng chuỗi nối tầng của DSP48E1.
- Ước tính −80 LUT và −65 FF mỗi tile, khoảng −1 300 LUT toàn lõi.
- Cái giá:
  - Đổi độ trễ bộ nhân (FUSE), kéo theo mọi lịch NTT và FFT.
  - Bộ cộng 4 toán hạng 68 bit trong một nhịp khó đạt khoảng 180 MHz.
  - Chuỗi DSP cần tách 17 / 15 bit, làm lệch vị trí hai làn của NTT packed.

### 11.3 Không nên làm

| Hướng | Lý do |
|---|---|
| Rút gọn lười (giữ giá trị trong [0, 2q)) để bỏ một phần hiệu chỉnh | Chỉ đúng khi q < 2^30; mất các prime 31 bit đang hỗ trợ |
| Bỏ chia đôi ở mỗi tầng GS | Phải thêm một lượt nhân n⁻¹ hoặc đổi định nghĩa đầu ra; mất bit-exact theo hợp đồng |
| Cho tầng T của FFT dùng bộ cộng/trừ chung | FFT 32 cần 4 phép trong 3 nhịp, vượt 1 phép mỗi nhịp; mỗi toán hạng có 3 nguồn nên bộ chọn không còn nằm gọn trong LUT6 |
| Chuyển các thanh ghi trễ NTRUGen (5 152 FF) sang LUTRAM hay SRL | Chuyển chi phí từ FF (còn dư: 31 883 / 106 400) sang LUT (đang thiếu) |
| Dùng cả 4 lá nhân cho NTT packed | Mỗi yêu cầu phải mang 8 hệ số, mạng dữ liệu phải rộng gấp đôi |

### 11.4 Đã làm: hướng 1, 2, 3 (`experiments/a_cg_z020_share`)

Ba hướng làm chung một đợt, nên chỉ có số đo tổng; phần đóng góp của từng hướng vẫn là ước tính ở mục 11.1.

| | `a_cg_z020_hostdiv` | `a_cg_z020_share` |
|---|---:|---:|
| LUT sau place and route | 35 777 | **31 122** (−4 655, −13,0 %) |
| FF | 31 946 | 29 964 |
| LUTRAM / DSP / RAMB18 | 2 968 / 64 / 48 | 2 969 / 64 / 48 |
| WNS thanh ghi → thanh ghi | −0,567 ns (≈ 180 MHz) | −0,686 ns (≈ 176 MHz) |
| WHS thanh ghi → thanh ghi | +0,050 ns | +0,051 ns |
| LUT logic một tile (tổng hợp) | 1 568 | 1 266 (−19 %) |
| Chu kỳ, tổng 1 026 case | 560 625 | 559 565 (NTT giữ nguyên, FFT bằng hoặc ít hơn) |

Đúng bit với golden; số chu kỳ RTL bằng planner.

Hai đường trượt nặng nhất gần bằng nhau:
- chuỗi gộp u − q / p0 + p1 ở tầng T của FFT: −0,686 ns;
- đọc block RAM vào thanh ghi dòng của host, khối không đổi trong đợt này: −0,674 ns.

Vì vậy tách lại riêng cặp u − q / p0 + p1 chỉ được khoảng 0,01 ns mà mất lại khoảng 500 LUT.
