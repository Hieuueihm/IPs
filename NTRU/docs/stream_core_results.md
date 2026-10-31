# Ghép FFT rộng, cấp dữ liệu NTT và đo toàn mảng

> Cập nhật sau báo cáo này: [sizing cục bộ đã xử lý vi phạm slew](stream_slew_repair.md). Các số baseline bên dưới được giữ để so sánh.

Ngày 26/10/2026. Đây là prototype để đo hướng **radix-2 một/hai tầng + compact reducer**,
không chốt 16 cụm là kích thước cuối cùng của core.

## 1. Phần RTL đã có

Một mảng gồm 16 tile, mỗi tile có bốn leaf nhân 16×16, chia hai leaf ở mỗi tầng tính.
Tái dùng cùng 64 leaf vật lý để thực hiện:

| Chế độ | Công việc mỗi giao dịch của mảng |
|---|---|
| FFT32 | 16 tích thực Q16.16 |
| FFT64 | 4 tích thực Q32.32 |
| FFT128 | 1 tích thực Q64.64 |
| NTT mode0 | 64 butterfly độc lập, 128 hệ số |
| NTT mode1 | 16 nhóm × 4 hệ số, mỗi nhóm qua hai tầng, tổng 64 butterfly |
| NTT mode2 | 16 nhóm × 4 hệ số qua một tầng, tổng 32 butterfly |

Ở FFT, bảng trên là **tích thực**, không phải 16/4/1 butterfly phức hoàn chỉnh.
R8 3M cần ba tích thực với ba vị trí rounding riêng. Các phép cộng phức và controller
FFT hoàn chỉnh chưa nằm trong RTL này.

File mới, giữ các baseline cũ nguyên bản:

- [flex_stream_tile.sv](../hdl/proto/flex_stream_tile.sv): signed/unsigned limb, tích raw65,
  compact reducer và clock enable.
- [flex_stream_array.sv](../hdl/proto/flex_stream_array.sv): phát limb theo width, cây ghép,
  rounding, pack NTT, pipeline metadata và queue hai phần tử.
- [ntt_bank_permute64.sv](../hdl/proto/ntt_bank_permute64.sv): gather/scatter bank và wrapper
  `flex_stream_banked`, cùng đường FFT bypass.
- [flex_stream_tops.sv](../hdl/proto/flex_stream_tops.sv): ba đối chứng flow control.

Mảng có bốn cạnh lấy mẫu khi không bị chặn; wrapper queue thêm một cạnh.
Khoảng cách khởi phát II=1 khi cấp đủ dữ liệu và đầu ra nhận liên tục.
Global enable giữ mọi tầng khi đầu ra valid nhưng chưa được nhận. Queue hai phần tử
giảm phụ thuộc ready của nguồn vào downstream; queue đầy không nhận thêm ở cùng cạnh
pop, nên có thể mất một cơ hội nhận ngay sau stall. Chưa có FIFO kết quả riêng.

## 2. Số học FFT và kiểm chứng R8

Chỉ limb cao nhất của mỗi toán hạng có dấu. Các limb thấp unsigned; do đó raw product
32×32 được giữ **65 bit có dấu**, đủ biểu diễn cả unsigned32×unsigned32.
Cộng các tích riêng với dịch cố định; không rounding ở leaf hoặc tại biên tile.

FFT64 gom bốn raw65, giữ modulo 2^96, cộng 2^31 rồi lấy bit [95:32].
FFT128 gom 16 raw65 bằng cây cân bằng có shift 32,32,64,64; giữ modulo 2^192,
cộng 2^63 rồi lấy [191:64]. Carry thấp vẫn được giữ chính xác.
Không tự hạ precision, saturation hoặc thay tie rule của reference.

[Kết quả kiểm chứng](../study/results/flex_stream_validation.json):

- 22.724 giao dịch qua mảng có queue/stall, không sai khác; gồm 1.000 giao dịch đổi
  nhanh FFT/NTT, width, profile và CT/GS.
- 19.968 phép nhân Q64.64 lấy từ bốn kernel C R8: FFT/iFFT ở N512 và N1024.
  Kết quả nhân **thực sự đọc từ RTL** được đưa lại vào kernel model; toàn bộ 3.072
  word đầu ra khớp vector C, không chỉ kiểm tra từng phép nhân riêng.
- 56 trace NTT từ bộ vector trước được đóng gói lại cho mảng; oracle là số nguyên
  modulo, chưa phải differential trực tiếp với C Falcon/Kyber.
- Mảng buffered chịu 16.217 chu kỳ bị chặn đầu ra; dữ liệu và metadata giữ nguyên.
  Hai đối chứng direct-stall và không-stall cùng qua 1.900 giao dịch.

Reference R8: commit `ad1e5bf7714d53230ad457364db8a46a1b459c94`, scalar mode2,
Q64.64. Các kernel replay mới dùng vector synthetic xuất bởi C, không phải hardware
thay thế trọn luồng ký. FFT64/32 hiện có contract Q32.32/Q16.16 tự định nghĩa; **chưa
được xác nhận tương đương một mode precision thấp của R8**.

## 3. Bộ nhớ cấp được hai tầng NTT trong điều kiện nào?

### Dữ liệu

Dùng 64 bank × 16 bit, mỗi bank **1 read + 1 write mỗi chu kỳ**. Không giả định SRAM
một cổng có thể đọc và ghi đồng thời. Tại N1024, mỗi bank sâu16 word, tổng 16.384 bit.

~~~text
bank(i) = (i & 63) XOR ((i >> 2) & 0x30) XOR ((i >> 4) & 0x30)
row(i)  = i >> 6
~~~

Cặp bank,row là ánh xạ một-một. Hai tầng stride 2^p và 2^(p+1) dùng nhóm
`[a,a+2^p,a+2^(p+1),a+3*2^p]`. Gom 16 nhóm theo thứ tự các bit địa chỉ còn lại
cho một lượt 64 hệ số không trùng bank. CT/GS có thứ tự tính khác nhau nhưng giữ
nguyên nhóm bốn địa chỉ này.

Tầng lẻ dùng mode2, phải chọn năm bit địa chỉ tự do có các cột bank độc lập với
bit stride, rồi mới duyệt các bit còn lại. Không dùng thứ tự butterfly thông thường
một cách máy móc. CT pack `[A0,A1,B0,B1]`; GS pack `[A0,B0,A1,B1]`.

RTL gather/scatter dùng các hoán vị cố định theo loại stride, chọn cấu hình và XOR
hai bit bank cao. Đây không phải crossbar tùy ý 64×64, nhưng vẫn có mux và fanout.

### Twiddle

16 bank root, mỗi word48 bit, lưu bundle:

~~~text
bundle[g] = [GM[g], GM[2g], GM[2g+1]], đã Montgomery encode
root_bank = g & 15; root_row = g >> 4
~~~

Mỗi nhóm hai tầng lấy một bundle; cùng node thì broadcast. Với tập lượt đã kiểm,
mỗi chu kỳ cần tối đa16 bundle khác nhau và không đụng bank. Tầng lẻ chọn root con
từ bundle cha; GS tầng stride lớn nhất dùng root node1. Inverse dùng root inverse
được nạp sẵn, không tính nghịch đảo trên đường xử lý nóng.

Ở N1024 cần 16×32×48 =24.576 bit **mỗi chiều** nếu bố trí đủ cả bank. Gần 1,5 lần
bảng phẳng N×16, vì bundle lặp lại root. Nếu giữ riêng cả forward và inverse thì
dung lượng root tăng gấp đôi; nếu nạp lại thì phải tính thời gian đổi context.

### Kết quả và giới hạn

[Model cấp bank](../model/ntt_banked_supply.py), [kết quả](../study/results/ntt_banked_supply.json):
28 transform case, N8…1024 ở q12289; N8…256 ở q3329. N256/q3329 giữ incomplete
7 tầng. Cả CT/GS không xung đột data/root và khớp phép biến đổi số nguyên.

| Trường hợp | Lượt đọc với bank XOR + thứ tự thích hợp | Bank modulo đơn giản |
|---|---:|---:|
| q12289, N8, CT/GS | 2 | 2 |
| q12289, N256, CT/GS | 16 | 28 |
| q12289, N512, CT/GS | 40 | 72 |
| q12289, N1024, CT/GS | 80 | 176 |
| q3329, N256, CT | 16 | 28 |
| q3329, N256, GS | 16 | 24 |

Đây là **lượt truyền**, không phải latency hay speedup trọn transform: chưa cộng
đọc RAM, drain giữa các lượt, stall, normalization hoặc BASEMUL q3329. Ghi cần số
lượt tương ứng; mức 1R+1W cho phép chồng đọc/ghi các nhóm độc lập trong cùng pass.
Controller còn phải chờ dữ liệu pass trước ghi xong trước khi phát pass kế tiếp.

Với N8 chỉ hai trong16 tile có dữ liệu hữu ích. Hết xung đột không đồng nghĩa N nhỏ
có hiệu suất cao; vẫn cần so kích thước mảng, batch hoặc nhiều transform đồng thời.
Mode0 cần **128 hệ số/cycle**, gấp đôi cấu hình64 bank này. Wrapper cho mode0 bypass
gather/scatter và nhận dữ liệu prepacked; không tuyên bố nuôi mode0 đầy đủ từ64 bank.

[Kiểm chứng banked RTL](../study/results/banked_stream_validation.json):
1.328 giao dịch mixed/stall, gồm376 lượt NTT đọc-bank → gather → array → scatter,
còn lại952 giao dịch FFT32/64/128; không sai khác. Row address và request của RAM
vẫn được Python sinh. Chưa có SRAM macro, controller phát stage hoặc root RAM RTL.
Tag nội bộ32 bit chứa stride4, bank-XOR2, logN4 và user-tag22; metadata đi cùng queue
và stall, không lấy cấu hình đầu vào hiện tại để scatter một kết quả cũ.

## 4. Timing và diện tích của toàn arithmetic island

<!-- STA_TABLE -->

| Cấu hình | Cell area (mm²) | FF cell | Arrival R→R (ns) | Worst setup slack @10ns (ns) |
|---|---:|---:|---:|---:|
| Mảng, không stall/queue | 0.349785 | 11,450 | 5.4002 | 4.4644 |
| Mảng + global stall | 0.372343 | 11,450 | 5.4023 | 4.4544 |
| + queue hai phần tử | 0.419044 | 17,421 | 5.4514 | 4.4139 |
| + gather/scatter bank | 0.450294 | 17,421 | 5.1370 | 4.7197 |

Global stall tăng area 6.45%; queue tăng thêm 12.54%; gather/scatter tăng thêm 7.46% so với bản buffered. Toàn bản banked tăng 28.73% so với mảng không stall/queue.

Arrival R→R gồm clock-to-Q và logic đến D, chưa cộng setup. Slack có tính setup và uncertainty.
Các endpoint không được timing đều là cổng nối hằng, đã kiểm trong netlist; reset được loại có chủ đích.
Ba bản chưa có bank router không có vi phạm max-transition trong log. Bản banked còn 110 pin vi phạm slew; log làm tròn cho thấy transition0,21ns so với limit0,20ns (worst reported slack −0,01ns). Đây là số pin, không phải số net độc lập. **Chưa đóng timing về điện; cần sửa buffer/drive/fanout rồi đo lại.** Không xem setup slack dương hoặc arrival thấp hơn của bản banked là bằng chứng routing tăng Fmax.

[JSON ba đối chứng](../study/results/stream_sta.json), [JSON banked](../study/results/banked_stream_sta.json),
[audit và phần trăm overhead](../study/results/stream_core_summary.json).
Bản banked dùng cùng map/buffer/size flow, thêm cleanup node dangling trước ABC buffer;
re-export cho OpenSTA được kiểm không đổi số lượng từng loại cell vật lý.

<!-- END_STA_TABLE -->

Nangate45 typical, 1,1V,25°C; Yosys0.52 + ABC mapping và OpenSTA2.0.17.
Clock tham chiếu10ns, uncertainty0,1ns, input/output delay0,2ns,
driver BUF_X1, load5fF. Reset là đường false; mọi mode còn lại đều active trong STA,
không case-analysis để giấu đường cấu hình. ABC có bước buffer/upsize/dnsize.

Diện tích là tổng cell đã map, gồm các buffer do ABC chèn; không phải diện tích
core sau floorplan. Routing ở đây là **mạng logic mux/hoán vị đã tổng hợp**, không phải
wire RC sau place-and-route. Chưa có SRAM, clock tree, parasitic, power hoặc corner signoff.
Không đổi số delay trước layout thành Fmax đạt được trên chip/FPGA.

## 5. Quyết định kiến trúc từ thí nghiệm này

1. Giữ ghép signed/unsigned limb và rounding một lần cho mỗi tích thực. Đường 128bit
   đã có kiểm chứng RTL và replay R8, không cần đánh đổi độ chính xác.
2. Hai tầng NTT có thể cấp dữ liệu với64 bank nếu đi cùng bank mapping, thứ tự
   butterfly và bundle twiddle phù hợp. Đây là một thiết kế bộ nhớ cụ thể có điều kiện,
   không phải lời khẳng định mọi SRAM đều nuôi được mảng.
3. Giữ đường một tầng cho phần dư; giữ đường mode0 để đánh giá khi có băng thông cao hơn.
4. Dùng các số đo full-island để quyết định số tile và mức buffering. Chưa chốt64 leaf
   cho mọi workload, chưa suy novelty/PPA advantage chỉ từ tỷ lệ dùng chung multiplier.
5. Công việc còn lại khi làm full core là RAM/stage controller có hazard handling,
   butterfly phức và normalization FFT, C differential NTT, rồi FPGA hoặc physical
   implementation với target cụ thể. Các phép chia và full keygen vẫn ngoài prototype.

## 6. Chạy lại

~~~powershell
python -X utf8 scripts/validate_flex_stream.py
python -X utf8 model/ntt_banked_supply.py
python -X utf8 scripts/validate_banked_stream.py
python -X utf8 scripts/bootstrap_stream_sta.py
~~~

STA cần Yosys/ABC Linux và OpenSTA. Bộ local hiện tại ở `study/tools/` (gitignore).
Sau bootstrap, giải nén OpenSTA bằng `dpkg-deb -x study/tools/stream_sta/opensta.deb
study/tools/stream_sta/root`. Trong WSL đặt `LD_LIBRARY_PATH` tới lib của Yosys local,
`TCL_LIBRARY` tới `usr/share/tcltk/tcl8.6`, thêm bin Yosys vào PATH, rồi chạy:

~~~sh
python3 scripts/benchmark_stream_sta.py
python3 scripts/benchmark_banked_sta.py
~~~

Hai script kiểm hash RTL đã qua validation. `--sta-only` tái dùng netlist có sẵn,
kiểm timestamp RTL, re-export đúng subset Verilog của OpenSTA và kiểm số cell không đổi.
Nguồn dependency và SHA256 được lưu trong JSON kết quả; thư viện lấy từ revision
OpenROAD-flow-scripts đã pin trong manifest, không lấy bản master thay đổi cho từng lần chạy.
