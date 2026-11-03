# Phân tích phép tính và đề xuất lõi đa precision, đa modulus

Ngày 02/11/2026. Đây là phân tích và kiến trúc ứng viên; không đổi PLAN, spec hay RTL.
Ngân sách người dùng: khoảng 35.000 LUT. Giữ đúng số học là điều kiện bắt buộc;
tốc độ hiện tại là mốc so sánh, chưa tự đặt thành một yêu cầu mới.

**Bổ sung sau phản biện và mô hình:** quota 22k/10k ở dưới chưa chứng minh khả thi;
A một mình không đủ cơ sở để hứa đạt 35k. Đã kiểm liveness/cổng của A và tìm một
ánh xạ CG bốn nguồn. Đọc [kết quả A + CG](ket_qua_mo_hinh_A_CG.md) để phân biệt
phần đã kiểm với chi phí host/root/RTL còn mở. Tài liệu này giữ phần suy luận ban đầu.

Script tái tạo số đếm: [butterfly_resource_demand.py](../model/butterfly_resource_demand.py).
Kết quả: [bảng](../study/results/butterfly_resource_demand.md),
[JSON và hash](../study/results/butterfly_resource_demand.json).

## 1. Kết luận để chọn hướng

Ưu tiên khảo sát **đường số học cơ sở 32 bit, điều khiển theo nhóm cùng tiến độ,
bộ nhớ trạng thái có chia bank và đóng gói theo precision**. Các đường tính đều
thực hiện được mọi precision; không giữ phương án 12 tile ngừng tính khi FFT rộng.

Precision quyết định số phần 32 bit và chương trình bước tính. Modulus quyết định
q, qprime và root, không tạo thêm một bộ nhân/reducer cho mỗi q. Hợp tác giữa nhiều
engine là phương án đối chiếu, chưa phải điều kiện của kiến trúc cơ sở.

Động lực không phải chỉ số bit của bộ nhân. RTL đã dùng bộ nhân 32×32 cho cả FFT
và NTT. Cần giảm máy điều khiển, cổng đọc phụ, trạng thái và lựa chọn nguồn bị lặp
mà vẫn đủ công suất cộng, tích lũy và xuất kết quả.

Chưa có số đo chứng minh phương án này dưới 35k LUT. Không dùng số bit bộ nhớ,
số phép cộng hoặc số controller xóa ở source để suy thẳng LUT tiết kiệm.

## 2. Các mốc đo và cách diễn giải

| Cấu hình | LUT | DSP | BRAM36 tương đương | Phạm vi |
|---|---:|---:|---:|---|
| Lõi hiện tại đầy đủ | 51.573 | 64 | 76 | Synthesis |
| Wrapper buộc FFT tắt | 24.672 | 64 | 76 | Synthesis, phép thử loại bỏ FFT |
| Wrapper buộc format FFT32 | 44.873 | 64 | 76 | Synthesis, không phải thiết kế FFT32 tối giản |

Các báo cáo ở `study/build/core_area/` và `study/build/core_split/`. Script lưu hash
các báo cáo đã đọc. Hash source hiện tại không thay cho bản chụp source lúc đo.

Chi phí bổ sung FFT trong cách tổ chức hiện tại là 26.901 LUT. Để xuống 35k phải
giảm ít nhất 16.573 LUT từ bản đầy đủ. Do đó không dựa vào vài thay đổi nhỏ trong
bộ cộng để hứa đạt ngân sách.

Wrapper format0 vẫn có 4.448 LUT làm bộ nhớ, bằng bản đầy đủ. `q0` hiện vừa giữ
modulus vừa mã hóa độ rộng FFT, nên buộc format ở cổng core không đủ để tự kết luận
mọi nhánh rộng bên trong tile đã bị loại. Cần parameter/tách trường cấu hình và
đối chiếu netlist nếu muốn đo một thiết kế chỉ FFT32 thực sự.

Mốc FFT32 gọn ở commit 267dae9 được ghi trong
[tài liệu so sánh](so_sanh_kien_truc_loi.md): 34.219 LUT cả core, 21.912 LUT trong
tile. Đây là bằng chứng về một cách tổ chức khác; nó còn khác profile, giao diện
và chức năng. Không lấy chênh lệch giữa hai commit làm số tiết kiệm của riêng FFT rộng.

## 3. Công việc số học của một butterfly

FFT dùng đúng 3M và rounding của spec. Đặt L = W/32. Một tích fixed-point dùng
1 / 4 / 15 tích phần 32×32 cho W = 32 / 64 / 128. Ở W128, chỉ bỏ tích có trọng số
nằm hoàn toàn trên phần kết quả sau wrap; các tích thấp tạo carry vẫn phải tính.

| Mode | Lượt nhân 32×32/BF | Cộng/trừ theo từ 32 bit ngoài tích lũy | Dữ liệu vào gồm root | Dữ liệu ra |
|---|---:|---|---:|---:|
| FFT32 | 3 | 9; tầng cuối IFFT thêm 4 phép cộng rounding | 6 word32 | 4 word32 |
| FFT64 | 12 | 18; tầng cuối IFFT thêm 8 | 12 word32 | 8 word32 |
| FFT128 | 45 | 36; tầng cuối IFFT thêm 16 | 24 word32 | 16 word32 |
| NTT32 | 3 lượt Montgomery | 4 phép cho tổng/hiệu và hiệu chỉnh; 1 cho u, 1 cho u−q; GS chia đôi thêm 1 | 3 word32 | 2 word32 |
| NTT16 packed | 3 lượt cho một request hai BF | Như NTT, hai làn độc lập 16 bit | 3 word32/request | 2 word32/request |

9L của FFT gồm 2L phép tạo hai tổng đầu vào 3M, 3L phép ghép p0/p1/p2 và 4L phép
cộng/trừ butterfly. Đây là số phép toán, không phải số adder vật lý. Chưa tính
phép tích lũy các tích phần, tạo địa chỉ và logic bit/sign/carry. IFFT vẫn phải
giữ wrap trước khi dịch; không dời rounding sang tầng khác hoặc thay 3M bằng 4M.

NTT nhiều modulus dùng cùng Montgomery R=2^32 cho đường 32 bit; packed dùng
R=2^16 với hằng số và root tương ứng. NTT hợp lệ còn đòi hỏi root phù hợp với N
và hmin; không suy từ hỗ trợ modmul q lẻ rằng mọi NTT cho q đó đều tồn tại.

## 4. Dữ liệu nào cần giữ, giữ đến khi nào?

| Dữ liệu | Lúc tạo | Lần dùng cuối / điều kiện giải phóng |
|---|---|---|
| FFT: A ở CT, A+B ở GS | Đọc đầu vào / cộng đầu vào | Khi tạo xong hai nhánh kết quả tương ứng |
| FFT: o.re, o.im, wr, wi | Đọc / chuẩn bị đầu vào | Khi các lượt nhân sử dụng chúng đã được phát |
| FFT: o.re+o.im, wr+wi | Sau khi đủ hai thành phần, wrap ở W | Khi phát hết tích p2 |
| FFT: p0 | Sau tích thứ nhất được rounding | Khi p1 tới, đã tạo T.re và p0+p1 |
| FFT: p0+p1 | Khi p1 tới | Khi p2 tới để tạo T.im |
| FFT: carry cộng dồn | Khi bắt đầu cột tích | Sau cột cuối cần cho kết quả |
| FFT: carry/borrow cộng phần | Sau mỗi phần thấp | Sau phần cao cuối của đúng phép đó |
| IFFT: phần hiện tại và phần kế | Sau cộng rounding có wrap | Khi đã xuất phần kết quả dịch tương ứng |
| NTT CT: x | Trước nhân | Khi Mont(y,w) tới và đã tính x±t |
| NTT GS: tổng đã chuẩn hóa | Trước nhân | Chia đôi ở post stage nếu bật halve, rồi phát cùng Mont(x−y,w) |
| NTT: T_low | Sau AB | Sau khi tính m; sau đó chỉ cần cờ T_low khác 0 |
| NTT: T_high | Sau AB | Khi (m q)_high tới để tạo u |
| NTT: m | Sau lượt T_low qprime | Khi phát m q |
| q, qprime, fmt, direction | Cấu hình lệnh | Hết lệnh và hết dữ liệu đang chạy |

RTL đã rút T_low còn cờ NZ cho phần chờ và đã dùng chung bộ nhớ side NTT/FFT.
Đây không phải các khoản tiết kiệm mới. Bảng dùng để tránh thiết kế lại dư trạng thái.

Với cấu hình tile mặc định và nhịp phát của core hiện tại:

| FFT W | Khoảng BF cùng engine | Dùng cuối sau nhịp đầu | Context đồng thời | Slot lũy thừa 2 đủ dùng | Số entry operand/side | Entry mỗi mảng tổng |
|---|---:|---:|---:|---:|---:|---:|
| 32 | 3 | 17 | 6 | 8 | 16 | 8 |
| 64 | 12 | 29 | 3 | 4 | 16 | 8 |
| 128 | 48 | 66 | 2 | 2 | 16 | 8 |

Đây là liveness của lịch đang xét, không phải giới hạn cho một tile nhận burst tùy ý.
Một cách đóng gói chung là 16 entry cho từng mảng operand/side, 8 entry cho từng
mảng tổng, với số context 8/4/2 theo precision. Cần tính thêm metadata và cấu hình
pipeline khác. Không còn cam kết nhận bốn BF128 ngay khi burst tới; phải backpressure.

Giảm depth không chắc giảm LUTRAM vì phụ thuộc primitive và số cổng. Giá trị quan
trọng hơn là dùng địa chỉ đặc, ít mux, ít cổng đọc và bộ đếm dùng chung.

## 5. Đồng thời ở steady state khác với thứ tự của một butterfly

Một BF có thứ tự chuẩn bị → nhân → ghép → xuất. Khi chạy liên tục, chuẩn bị BF k+1,
nhân BF k và ghép/xuất BF k−1 có thể cùng diễn ra. Không gộp chúng vào một ALU chỉ
vì nhìn trên một BF thì chúng ở các bước khác nhau.

- Tổng và hiệu cần cùng lúc: giữ cặp cộng/trừ hoặc chấp nhận lịch dài hơn.
- Hai phép trừ T.re và T.im ở hai lượt khác nhau: dùng chung được; RTL đã làm.
- Nhân FFT và Montgomery khác mode toàn lệnh: dùng chung cùng bộ nhân.
- NTT32 và hai làn NTT16: dùng cộng/reduction phân đoạn; không thêm reducer theo từng q.
- Cộng u của NTT với MAC FFT: ứng viên đo riêng. Cộng 33 bit và 68 bit có toán hạng,
  feedback khác nhau; mux có thể đắt hơn phần cộng bỏ được.
- Rounding/scaling IFFT và cộng đầu vào GS có thể trùng nhau giữa các BF: không gộp
  vào một cặp cộng nếu chưa có lịch đáp ứng cả hai.

Đã có phép thử ở [addsub_variants](../study/results/addsub_variants/addsub_variants.sv):
bản bốn chuỗi 196 LUT; bản chia hai chu kỳ 290 LUT +130 FF. Không lặp lại giả định
"ít adder ở source thì ít LUT".

## 6. Cận tốc độ để định cỡ phần dùng chung

Với sơ đồ tích hiện tại, NTT N1024 có 5.120 BF; FFT N1024 của reference có 512 điểm
phức, 9 tầng, 2.304 BF. Không nhầm N1024 scalar components với 1024 điểm phức.

| Mode | Chu kỳ hiện tại | Cận chỉ nhân, 8 engine | 12 engine | 16 engine | Ít nhất làn xuất 2 word32/ck theo trung bình |
|---|---:|---:|---:|---:|---:|
| NTT32 N1024 | 984 | 1.920 | 1.280 | 960 | 6 |
| FFT32 N1024 | 644 | 864 | 576 | 432 | 8 |
| FFT64 N1024 | 2.031 | 3.456 | 2.304 | 1.728 | 5 |
| FFT128 N1024 | 7.510 | 12.960 | 8.640 | 6.480 | 3 |

Các cận chưa có fill/drain, bank, root, dependency hoặc chờ tầng. Với thuật toán và
đơn vị 32×32 này, giữ NTT N1024 gần 984 chu kỳ cần năng lực tương đương 16 engine.
Giảm còn 12 khiến NTT ít nhất 1.280 chu kỳ (+30%) trước overhead, FFT64 ít nhất
2.304 (+13%), FFT128 ít nhất 8.640 (+15%). Đổi thuật toán reduction hoặc primitive
nhân có thể đổi các cận; đây không phải định lý cho mọi kiến trúc.

**Bốn hậu xử lý một cặp word/ck sẽ nghẽn.** Chỉ riêng xuất kết quả, bốn bộ cho
8 word32/ck cần ít nhất 1.152 chu kỳ ở FFT32 và 2.304 ở FFT64, đã vượt 644/2.031.

Nếu muốn không nghẽn ở cận nhân 16 engine, cần ít nhất 11/6/3 làn xuất cặp ở
FFT32/64/128. Đây chỉ là công suất xuất, chưa gồm toàn bộ cộng 3M và IFFT scaling.
Một cụm 4 engine cần tương ứng 3/2/1 làn xuất cặp theo cận trung bình số học.
Không được hiểu "4 cụm" là chỉ cần "4 hậu xử lý đơn làn".

## 7. Kiến trúc ứng viên A — ưu tiên trước

**Đường số học 32 bit, state chia bank tại chỗ, điều khiển dùng chung theo nhóm
cùng tiến độ. Mỗi engine vẫn thực hiện được mọi precision.**

1. Giữ độ rộng cơ sở 32 bit: multiplier có dấu/không dấu; cộng/trừ 32 bit với carry,
   correction modulo và tùy chọn split16. Không đặt bộ nhân 128×128 riêng.
2. Một descriptor công việc công khai gồm mode, fmt, direction, scaling và q/root
   context; fmt có trường riêng, không mã hóa trong q. Không truyền lại mọi trường
   qua từng thanh ghi nếu chúng ổn định đến khi hết lệnh.
3. Chương trình bước cố định theo mode điều khiển các nhóm cùng tiến độ. FFT32/
   FFT64/FFT128 khác số lượt 1/4/15 mỗi tích; NTT khác các lượt AB/Tlow·qprime/mq.
   Bộ đếm pha và giải mã dùng chung, có thanh ghi phát gần nơi dùng. Nhóm không đồng
   tiến vẫn giữ valid và context riêng; không xóa carry hay accumulator riêng.
4. Dữ liệu ở các bank cục bộ 1R/1W, địa chỉ context đóng gói theo precision như mục 4.
   Không tạo một RAM trung tâm 16 cổng hoặc register file đọc tùy ý.
5. Dùng thứ tự re_k, im_k để tạo tổng 3M từ thanh ghi của nhịp trước, khảo sát bỏ
   cổng đọc lại real ở wmx/wmw. Carry thực/ảo có trạng thái riêng. Đây là đổi thứ tự
   truyền, phải kiểm lại bank và hợp đồng tile; số học W-bit vẫn giữ nguyên.
6. Cộng/trừ butterfly và đường xuất có đủ làn cho FFT32/NTT. Phần nhân có thể chạy
   BF tiếp theo khi một BF đang ghép/xuất; các context hữu hạn và valid theo lịch.
7. NTT dùng Montgomery tổng quát một đường với q/qprime thay lúc chạy. Đường q nhỏ
   packed16 dùng cùng ALU/reduction; nếu chưa chứng minh lợi ích cả bộ nhớ thì giữ
   làm tùy chọn, không thêm nhiều reducer đặc biệt theo từng prime.
8. Root lưu có chia bank theo lịch; nạp context khi cần và cache cục bộ. Không mặc
   định chép toàn bộ mọi profile/slot thành 16 bảng riêng hoặc thêm bus wr+wi toàn mảng.

Lợi ích cần chứng minh: giảm bộ đếm, selector, cổng đọc và trạng thái dư. Không
trông đợi giảm lớn ở bốn chuỗi cộng modulo đã đo. Dữ liệu mỗi phép vẫn cục bộ,
không cần gom tích liên engine cho kiến trúc A.

Chọn số engine từ tốc độ: 16 nếu giữ mốc NTT hiện tại; 12 là điểm đối chiếu diện
tích nếu chấp nhận các cận chậm hơn ở mục 6. Mọi engine được dùng trong mọi precision.

## 8. Kiến trúc B — đối chiếu với hợp tác tính tích phần

Giữ các engine 32 bit, nhưng một nhóm cùng tính các tích phần của một BF rộng;
phần cộng cột, 3M, carry và scaling thuộc cụm. FFT32/NTT vẫn chạy nhiều BF độc lập.

Ưu điểm: có thể giảm số context BF rộng và máy điều khiển riêng. Chi phí bắt buộc:
đủ cổng nhận tích, adder/compressor, đọc operand và giữ context. Bốn tích/cycle
không thể đi vào một accumulator chỉ cộng được một tích/cycle mà không mất tốc độ.

Tổng 16 sản phẩm/cycle chỉ là cận năng lực, chưa là lịch khả thi. Cần xử lý hàng
đợi cột và carry giữa cột; độ trễ cooperative mới không được lấy nguyên 66 chu kỳ
của máy serial để suy sáu buffer mỗi cụm. Phải tính lại lifetime trên lịch mới.

Model intertile cũ dùng phép nhân phức 4M và rounding ties-to-even; không dùng
nguyên làm reference cho contract 3M, half-up hiện tại.

B là phương án cần so với A, không tự động tốt hơn vì có ghép PE.

## 9. Bộ nhớ và ngân sách

Hình học cố định và tại chỗ là hai biến thể độc lập của A/B. CG đã có kiểm tra
cấu trúc lịch; FFT của model CG chưa tính số học để so golden. Tốc độ chồng tầng
không phải lợi ích độc quyền của CG.

CG FFT128 lớn nhất cần hai vùng 128 hàng thay vì một. Có cơ sở về dung lượng vật
lý BRAM FPGA, nhưng phải mở địa chỉ RTL, kiểm ánh xạ và tổng hợp lại. Generic RAM
thật sự tăng số bit lưu. Root có thể là khoản tăng BRAM lớn hơn dữ liệu.

Nếu vẫn dùng ngân sách 80 BRAM36 tương đương: 44 RAMB36 +64 RAMB18 hiện tại =76;
80 RAMB36 +64 RAMB18 =112, không đạt. Với 64 RAMB18 dữ liệu, phần RAMB36 phải ≤48.

Phân bổ mục tiêu để thử, không phải dự báo:

| Khoản | Trần thiết kế để kiểm |
|---|---:|
| Số học, bank trạng thái cục bộ và hậu xử lý mọi mode | 22k LUT |
| Địa chỉ, mạng, root, giao tiếp và điều khiển | 10k LUT |
| Phần dự phòng cho tích hợp/đặt dây | 3k LUT |

Không suy LUT sau route bằng cách cộng một tỷ lệ cố định vào synthesis. Nếu chưa
đạt 32k ở synthesis thì không gọi là đã bảo đảm trần 35k sau tích hợp/route.

## 10. Thí nghiệm ngắn để chọn, theo đúng phụ thuộc

1. Chuẩn hóa primitive và dữ liệu ở mục 3–4; chọn A làm ứng viên đầu, B làm đối chiếu.
2. Model lifetime và cổng với lịch mới của A: state 16/8 entry, re/im xen kẽ, cùng
   số học 3M. Kiểm BF và toàn transform bằng reference, không chỉ đúng cặp.
3. Tổng hợp một engine và một nhóm điều khiển của A, tính cả mux, metadata và RAM.
   Giữ cùng workload/clock với bản đối chiếu; ghi hash và bản chụp nguồn.
4. Chỉ thử gộp u-NTT với MAC-FFT hoặc đổi ghép tích khi đo riêng có lợi. Không
   cộng các ước lượng tiết kiệm có thể trùng nhau.
5. Nếu A vượt quota, đo một cụm B với đủ cổng và lịch mới, không ngoại suy từ cây
   cộng lý tưởng. Đồng thời so 12 engine hoạt động ở mọi mode nếu tốc độ cho phép.
6. Chọn lịch bộ nhớ bằng tổng LUT/BRAM/cycle sau khi tính root và host; cuối cùng
   tổng hợp cả core và route. Không khóa CG vì tên gọi hoặc vì có bộ đếm chung.

## Nguồn ngoài về ánh xạ FPGA

- [AMD UG573 — cấu hình địa chỉ/độ sâu BRAM](https://docs.amd.com/r/en-US/ug573-ultrascale-memory-resources/Address-Bus-ADDRARDADDR-and-ADDRBWRADDR).
- [AMD UG579 — DSP48E2](https://docs.amd.com/api/khub/documents/pTysoma4TYgNH95BrY1Sbw/content).
  SIMD TWO24/FOUR12 không được dùng đồng thời multiplier của DSP; không coi đó là
  cách có thêm ALU miễn phí trong khi bốn lá vẫn đang nhân.

## Bằng chứng của lượt phân tích này

Script kiểm 9.147 tích fixed-point và 3.000 phép nhân phức 3M, gồm biên/ngẫu nhiên,
khớp phép tính số nguyên của reference ở W32/64/128. Nó chứng minh các tích phần
được giữ đủ cho wrap/rounding và phép cộng đổi thứ tự trên số nguyên đủ rộng.
Chưa chứng minh độ rộng accumulator hữu hạn, lịch mới, RTL mới hay mức LUT mới.
