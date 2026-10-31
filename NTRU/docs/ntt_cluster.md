# Cụm nhỏ dùng chung FFT/NTT: tách lane và ghép tầng

Ngày: 26/10/2026. Prototype RTL số học; chưa phải core transform có bộ nhớ.

## 1. Bài toán cần giải quyết

F16–32 trước đây giảm số reducer so với F16–64 nhưng để 32/64 multiplier không
hoạt động trong mode NTT. Nó chọn điểm diện tích/băng thông, chưa khai thác dữ liệu
giữa các tầng NTT. Các số đo đó cũng chưa so với NTT chuyên dụng có pipeline ngắn.

Prototype mới dùng **bốn multiplier 16×16**, phân bổ hai multiplier cho mỗi tầng
compute. Chuyển cách nối cục bộ theo mode, không dựng thêm mảng nhân riêng cho FFT.
Mục tiêu là giữ các multiplier hoạt động bằng cách làm hai tầng NTT trên cùng
bốn hệ số, thay vì tăng số hệ số phải đọc/ghi ngoài core.

## 2. Contract và các mode

RTL: [flex_ntt_cluster.sv](../hdl/proto/flex_ntt_cluster.sv).

| Mode | Công việc | Hệ số vào/ra | Root word 16 bit |
|---|---|---:|---:|
| 0 | 4 butterfly NTT độc lập | 8 | 4 |
| 1 | 2 tầng NTT liên tiếp, mỗi tầng 2 butterfly | 4 | 3 |
| 2 | 2 butterfly của tầng đầu, bypass tầng sau | 4 | 2 |
| 3 | Tích signed32×signed32 đầy đủ, cho đường FFT | 2 toán hạng 32 bit | 0 |

Mỗi transaction được nhận ở một cạnh clock; mode/profile/inverse/tag đi cùng
dữ liệu. Các mode của bản dùng chung cùng latency **ba cạnh lấy mẫu**, II=1,
không backpressure. Bypass tầng sau không rút ngắn latency. Bản NTT chuyên dụng
`cluster_ntt_parallel_short` bỏ thanh ghi giữa và có latency **hai cạnh**, II=1.
Không gọi ba cạnh lấy mẫu là ba khoảng clock từ cạnh nhận đến cạnh ra: khoảng
đó là hai chu kỳ ở bản shared, một chu kỳ ở bản short.

Profile 0: q=12289. Profile 1: q=3329. Data canonical trong [0,q), root lưu
wR mod q, R=2^16; Mont(B,wR)=B·w mod q. CT cho forward, GS cho inverse trong
các trace; inverse normalization không nằm trong cụm. Profile/inverse đổi được
theo transaction ở prototype; toàn core vẫn cần quy tắc context/drain riêng.
Không hỗ trợ lazy input ngoài [0,q) trong vòng thử này.

### 2.1 Kết nối trong cụm

CT mode 1:

~~~text
Input: x0,x1,x2,x3
Tầng 1: BF(x0,x2,w_common), BF(x1,x3,w_common)
Giữ kết quả theo thứ tự hệ số trong thanh ghi giữa.
Tầng 2: BF(y0,y1,w0), BF(y2,y3,w1)
Output: z0,z1,z2,z3
~~~

GS mode 1:

~~~text
Tầng 1: BF(x0,x1,w0), BF(x2,x3,w1)
Tầng 2: BF(y0,y2,w_common), BF(y1,y3,w_common)
~~~

Bus root mode 1 chứa `[common, distinct0, distinct1]` theo thứ tự word từ thấp
lên cao; word thứ tư không dùng. Đây là contract cho **hai tầng NTT kế tiếp**,
không phải bốn butterfly với bốn root tùy ý. Lưu common root một lần giảm root
payload từ 64 xuống 48 bit mỗi transaction. Broadcast giữa nhiều cụm chưa làm.

Mode 0 ghép các cặp (x0,x1),(x2,x3),(x4,x5),(x6,x7). Hai cặp đầu chạy ở compute
stage đầu; hai cặp sau được giữ operand/root và chạy ở stage sau. Kết quả ra cùng
lúc, đúng tag. Mode 2 dùng kết nối tầng đầu của mode 1 rồi bypass.

### 2.2 Tối ưu chính xác cho q nhỏ

- Canonical q=3329 cần 12 bit; q=12289 cần 14 bit. RTL làm rõ các bit cao bằng
  zero ở đầu vào, root và kết quả modular để công cụ tổng hợp bỏ phần không dùng.
- Đây không phải giảm precision FFT: mode 3 giữ toàn bộ limb16, tích signed32
  có đủ 64 bit, không rounding/cắt partial product ở giữa hai stage.
- Tổng modular dùng 17 bit trước correction; hiệu được cộng q nếu âm.
- Montgomery: m=low16(T*qprime); S=T+m*q; u=S>>16; trừ q nếu cần.
  qprime lần lượt 12287 và 3327. Các tích hằng dùng shift-add.
- Với input canonical và q<=12289: T<2^28, S<2^30 và u<2q. Vì vậy các giới hạn
  độ rộng trong reducer cùng một correction là đủ; kết quả canonical có đúng
  các bit cao bằng zero vừa nêu. Không bỏ carry cần thiết.

Hai tầng vẫn có reducer riêng để duy trì II=1. Mảng nhân dùng chung giữa FFT/NTT;
reduction và cây ghép tích FFT hiện còn riêng. Chưa tuyên bố đã chia sẻ tối đa
adder/compressor giữa hai domain hoặc đã đạt reduction nhỏ nhất.

## 3. Đối chứng để đánh giá chi phí

Tất cả dùng cùng nguồn RTL và flow generic, xem bảng đo trong
[ntt_cluster.md](../study/results/ntt_cluster.md).

| Top | Chức năng |
|---|---|
| cluster_ntt_parallel_short | NTT chuyên dụng, 4 BF độc lập, 2 cạnh |
| cluster_ntt_parallel | NTT chuyên dụng, 4 BF độc lập, 3 cạnh |
| cluster_ntt_pair_only | Chỉ mode 1, đổi hai profile |
| cluster_ntt_pair_bypass | Mode 1/2: đo thêm chi phí bypass |
| cluster_ntt_configurable | Mode 0/1/2: thêm kết nối độc lập và paired |
| cluster_flex_parallel | Mode 0/3: NTT độc lập + FFT32 raw |
| cluster_flex_pair | Cả bốn mode, hai profile |
| cluster_ntt_pair_q12289 | Mode 1, cố định q=12289 |
| cluster_ntt_pair_q3329 | Mode 1, cố định q=3329 |

So pair-only với pair-bypass để đo chi phí hỗ trợ bypass gồm control/root packing
và output mux; không quy toàn bộ chênh lệch area thành một mux. So configurable
với pair-bypass để đánh giá thêm đường bốn BF độc lập. So flex-pair với
flex-parallel để đánh giá thêm ghép tầng trong core đã có FFT. So pair-only với
hai bản fixed-q để đánh giá chi phí đổi modulus trong cùng chức năng.

GE là trọng số cell generic, FF quy đổi 4,67 GE/bit, giống flow bank trước.
Không dùng chênh lệch rất nhỏ trong mapping heuristic để kết luận thêm tính năng
là miễn phí. Độ dài đường gate không phải Fmax; các tỷ lệ cycle giả định cùng clock.

## 4. Kiểm chứng

[Driver](../scripts/prototype_ntt_cluster.py),
[testbench](../sim/src/tb_flex_ntt_cluster.sv).

- 16 102 vector; chín top được kiểm trên các mode/profile mà từng top hỗ trợ.
  Không phải mỗi top đều hỗ trợ cả 16 102 phép toán. Testbench báo coverage riêng.
- Biên 0,1,q−1,q/2; root biên; random canonical; CT/GS; đổi mode/profile ở các
  transaction liên tiếp; valid bubbles; kiểm chính xác latency, tag và thứ tự.
- Tích FFT32 signed đầy đủ gồm 0, ±1, min/max signed32 và random.
- 56 trace forward/inverse: hai pattern ở mỗi N/profile. q12289: N=8..1024;
  q3329: N=8..128 là NTT negacyclic đầy đủ, N=256 là incomplete NTT 7 tầng.
  Đây là trace oracle, không phải phép đo thời gian transform trên RAM thực.
- Mỗi nhóm RTL so với áp dụng từng tầng bằng số nguyên modulo, không dùng
  Montgomery để tính expected. N<=32 còn so forward với đánh giá đa thức trực
  tiếp ở các root; inverse được normalization bên ngoài rồi kiểm roundtrip.
- NTT q3329 N256 dùng root17 bậc256, normalization 128^-1, không dùng 256^-1.
  Chưa có BASEMUL. Các N nhỏ khác là bài kiểm số học, không phải parameter ML-KEM mới.
- 70 CMUL từ C R8: tách thành các tích signed32 qua RTL rồi hiệu chỉnh dấu,
  ghép W128, rounding và 3M trong driver; khớp C. Đây chỉ kiểm việc dùng lại
  multiplier/đường FFT32 raw; chưa có cây ghép W64/W128 hay butterfly FFT RTL mới.

Các trace NTT chưa đối chiếu trực tiếp C Falcon/Kyber. Chưa thay kernel vào signer,
chưa kiểm backpressure, timing đích, hoặc công suất.

## 5. N nhỏ và giới hạn băng thông

Mỗi cụm có trần bốn butterfly radix-2 tương đương/cycle ở cả mode 0 lẫn mode 1.
Mode 1 không tăng trần số học; nó giảm data mỗi transaction từ 128 xuống 64 bit.
Một transform dùng ceil(số_tầng/2) lượt đọc/ghi thay vì số_tầng lượt; tầng lẻ cuối
dùng mode 0 để tận dụng cả bốn multiplier, nếu có đủ nhóm.

Bảng cycle trong báo cáo có ba trường hợp: NTT chuyên dụng hai cạnh, shared
parallel ba cạnh và shared paired ba cạnh. Giả định mỗi lượt phải ghi xong mới
bắt đầu lượt tiếp theo, adapter đọc/ghi lý tưởng, có sẵn kết nối gather, root đủ
băng thông và clock bằng nhau. Mỗi transaction cần b=ceil(payload/B) beat dữ liệu:

~~~text
cycles/pass = (transactions−1)*b + 2*b + pipeline_edges−2
~~~

Công thức tính cả đọc nhóm đầu, pipeline và serialize nhóm cuối; đọc/ghi hai
hướng có thể chạy đồng thời. Mode parallel có payload 128 bit, paired 64 bit.
Không tính normalization INTT, chuyển miền, BASEMUL, root setup, RAM latency hay
xung đột bank. Đây là mô hình rào chắn giữa các lượt, không phải scheduler đã triển khai.

Ở 64 bit/cycle mỗi hướng, paired có cơ sở giảm số chu kỳ nhờ giữ dữ liệu trung
gian. Ở 128 bit/cycle, lợi ích có thể biến mất khi so với NTT chuyên dụng pipeline
ngắn. Với N quá nhỏ, có thể không đủ nhóm để lấp nhiều cụm; vòng này chỉ đo một
cụm, chưa chốt số cụm toàn core.

## 6. Kết quả và lựa chọn hiện tại

| Cấu hình | Total GE | FF bit | Độ dài gate |
|---|---:|---:|---:|
| NTT chuyên dụng 4 BF, pipeline ngắn | 22 122,7 | 318 | 118 |
| NTT chỉ paired, hai profile | 22 238,8 | 295 | 120 |
| NTT paired + bypass | 26 162,3 | 610 | 122 |
| NTT mode 0/1/2 | 29 262,1 | 643 | 122 |
| FFT + NTT độc lập | 28 832,6 | 640 | 119 |
| **FFT + NTT độc lập/paired/bypass** | **29 150,1** | **643** | **125** |
| NTT chỉ paired q12289 cố định | 18 432,4 | 292 | 105 |
| NTT chỉ paired q3329 cố định | 16 086,9 | 258 | 107 |

Thêm ghép tầng vào cụm đã có FFT tăng khoảng **1,10% total GE**, ba FF bit.
Đây là so sánh cùng cụm bốn multiplier; không so trực tiếp absolute area với bank
64 multiplier ở tài liệu trước. Bản chỉ paired nhẹ hơn vì không giữ operand cho
mode bốn butterfly độc lập và không cần output bus 128 bit hoạt động trong NTT.
Thêm bypass vào pair-only tăng khoảng 17,64%, gồm cả quy tắc root/mode và register;
không thể coi bypass là miễn phí. Toàn shared-cluster đắt hơn baseline NTT chuyên
dụng ngắn khoảng **31,77%**. Tính linh hoạt vẫn có chi phí.

Ví dụ mô hình cycle, so với NTT chuyên dụng ngắn, cùng clock giả định:

| q / N | Data mỗi hướng | NTT chuyên dụng | Shared paired | Tỷ lệ chu kỳ |
|---|---:|---:|---:|---:|
| 12289 / 8 | 64 bit/cycle | 12 | 9 | 1,33× |
| 12289 / 16 | 64 bit/cycle | 24 | 12 | 2,00× |
| 12289 / 64 | 64 bit/cycle | 108 | 54 | 2,00× |
| 3329 / 256, 7 tầng | 64 bit/cycle | 462 | 265 | 1,74× |
| 12289 / 16 | 128 bit/cycle | 12 | 12 | 1,00× |
| 12289 / 8 | 128 bit/cycle | 6 | 7 | 0,86× |

**Giữ cụm nhỏ và chế độ paired làm ứng viên**, đặc biệt khi data hạn chế so với
năng lực nhân. Chưa khóa số cụm và chưa thay thế baseline R32/F16 bank. Với N rất
nhỏ, data đủ rộng hoặc workload NTT chiếm ưu thế, đường NTT ngắn vẫn có thể tốt
hơn. Không chọn paired chỉ vì mọi multiplier đều hoạt động: throughput/area/timing
và tổng data phải có lợi. Giữ một/two-layer trong thiết kế để khảo sát theo workload.

Các con số cycle là dự báo của mô hình adapter, không phải cycle transform đã đo
trên RTL RAM; không phải bằng chứng speedup FN-DSA. Ghép W64/W128, kết nối giữa
các cụm và timing đích vẫn là các quyết định chưa được đo.

Phân tích tiếp theo, chưa đổi RTL cụm: [radix-4 factor và tích lũy/reduction
dùng chung](radix4_shared_accum_analysis.md). Ưu tiên so reducer compact theo
profile với reducer hiện tại trước khi đổi bố trí pipeline cho radix-4.
Đã thực hiện bước đó: [kết quả RTL](reducer_radix4_results.md). Chọn compact cho
shared cluster; radix-4 factor được giữ riêng làm ứng viên, chưa thay default.

## 7. Tái lập

~~~powershell
python -X utf8 scripts/prototype_ntt_cluster.py
wsl --exec env LD_LIBRARY_PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/lib/x86_64-linux-gnu PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin:/usr/bin:/bin python3 -X utf8 /mnt/d/IPs/NTRU/scripts/prototype_ntt_cluster.py --synth-only --yosys /mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin/yosys
~~~

Vector/log/build ở `study/build/ntt_cluster/`, báo cáo JSON/Markdown ở
`study/results/ntt_cluster.*`. JSON lưu hash RTL/testbench; `--synth-only` từ chối
reuse simulation nếu hash không còn khớp. Nguồn C R8 và các vector đã có được giữ nguyên.
