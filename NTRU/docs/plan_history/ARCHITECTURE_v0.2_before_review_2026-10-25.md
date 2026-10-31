# FlexTransform v0.2 — core butterfly trên mảng nhân ghép/tách

> Đề xuất kiến trúc cập nhật ngày 25/10/2026; chưa phải RTL core hay kết quả PPA.
> Bản này thay đề xuất core v0.1 ở các điểm liệt kê tại mục 1.
> [Bản v0.1 được lưu để đối chiếu](docs/plan_history/ARCHITECTURE_v0.1_2026-10-25.md).
> Tập trung số học, operand routing và giao diện; chưa thiết kế scheduler/RAM/DMA.
> Ràng buộc PQC: giữ precision, constants, scaling và rounding của reference đã chọn.

## 1. Quyết định và phần đang mở

| Nội dung | Hướng v0.2 | Trạng thái |
|---|---|---|
| FFT/NTT | Cùng mảng nhân nguyên, có signedness theo operand | Hướng kiến trúc |
| Fusion | Tạo từng tích thực/nguyên chính xác trước khi ghép Re/Im | Đề xuất thay cây Re/Im trực tiếp v0.1 |
| Độ rộng leaf | So F16: leaf 16×16 ghép lên, với R32: leaf 32×32 | Mở lại lựa chọn; chưa chốt bằng PPA |
| F16 | 4 leaf 16×16 độc lập hoặc ghép thành một 32×32; tiếp tục ghép 64/128 | Ứng viên phù hợp mục tiêu NTT hẹp |
| FFT complex multiply | 4M, giữ các ranh giới rounding theo reference | Baseline chức năng; 3M chưa được chấp nhận |
| Butterfly ALU | Ngân hàng A+T/A−T chia lane, có guard/carry | Ứng viên chia sẻ thứ hai |
| FFT postprocess | Complex recombination, scaling/rounding/overflow đúng contract | Riêng theo semantics |
| NTT reduction | Montgomery generic và Montgomery theo profile PQC | Hai backend cần so chi phí |
| CT/GS | CT là kernel đầu tiên; giữ GS trong yêu cầu khảo sát, chưa hứa cùng throughput | Chưa khóa hỗ trợ GS |
| Modulus | Chọn context hợp lệ lúc chạy, chỉ đổi sau khi drain | Không trộn nhiều context đang bay ở baseline |
| Băng thông | 512 bit mỗi hướng là điểm đối chiếu cũ; khảo sát thêm 1024/2048 | Không khóa băng thông để loại F16 trước |

Đây là đề xuất cần đánh giá. “Chia sẻ được” không đồng nghĩa chia sẻ sẽ giảm area
hoặc tăng throughput sau khi tính mux, register, reduction và hậu xử lý.

## 2. Bài toán và khác biệt cần chứng minh so với OpenNTT

FN-DSA/Falcon dùng q=12289 cho các phép toán modular và có các kernel FFT trong
đường xử lý khóa/ký. Bài toán của core là phục vụ các kernel này trên cùng tài nguyên,
đồng thời có thể tái dùng cho những profile PQC khác. Không yêu cầu FFT và NTT chạy
đồng thời; đây cũng chưa phải toàn bộ bộ ký hoặc keygen FN-DSA.

OpenNTT hỗ trợ đổi modulus trong cấu hình phù hợp, nhưng định cỡ integer multiplier
và Montgomery reducer theo modulus lớn nhất. LOGQ, PE và số tầng reducer là tham số
tạo phần cứng. Chọn q nhỏ hơn không tự tạo thêm lane butterfly.

Nguồn đã kiểm tra, ghim commit 86c07a5e77639f7f33292b31418f50c56c6aabd5:

- [Paper, mục III-D và IV](https://flokrieger.github.io/papers/tcad25_opennttext.pdf).
- [Generator: logq_max và LOGQ/PE](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/tool/openntt.py#L164).
- [Integer product rồi modular reduction](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/butterfly/btf_modmul.sv#L29).
- [PE generate và chọn FFT/NTT khi elaboration](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/ntt_control/ntt_core.sv#L254).

| Cơ chế | OpenNTT trong cấu hình đã kiểm tra | Mục tiêu FlexTransform |
|---|---|---|
| Đổi modulus | Có, với context/root phù hợp | Có |
| Độ rộng vật lý | Theo q lớn nhất, cố định sau khi tạo lõi | Leaf cố định, grouping và output taps thay đổi |
| FFT/NTT trên cùng mảng số học lúc chạy | Chọn loại transform khi tạo lõi | Có mode FFT/NTT dùng chung tài nguyên |
| q nhỏ có thêm lane | Không có cơ chế tách PE theo q | Khảo sát bằng F16, không suy ra từ đổi q |

Khác biệt dự kiến là cách phân bổ cùng mảng số học, không phải riêng tính năng
đổi q bằng Montgomery. Đây chưa phải kết luận novelty so với mọi prior work.

## 3. Tại sao mở lại leaf 16×16?

Nếu mục tiêu bao gồm NTT 12/14 bit có nhiều tích độc lập hơn NTT 23/32 bit, F16
là lựa chọn tự nhiên để thử. R32 không có cơ chế đó ở bên trong mỗi tile.

Với radix H=2^16, x=x0+H*x1, y=y0+H*y1:

~~~text
p00 = x0*y0
p01 = x0*y1
p10 = x1*y0
p11 = x1*y1

x*y = p00 + ((p01+p10) << 16) + (p11 << 32)
~~~

Limb thấp unsigned; limb cao signed nếu toán hạng gốc signed. Không được coi
mọi limb là signed 16 bit, hoặc mất carry của p01+p10.

Một cụm bốn leaf có hai cách dùng:

~~~text
TÁCH: 4 cặp operand riêng → 4 tích 16×16 độc lập
GHÉP: 1 cặp operand 32 bit → 4 tích chéo → 1 tích 32×32 chính xác
~~~

Hai PE chỉ chứa một bộ nhân 16×16 mỗi PE không đủ bốn tích để tạo một tích 32×32
trong cùng một lượt theo schoolbook. Có thể dùng hai lượt và accumulator; khi đó
phải tính lại throughput. Bản F16 này chọn bốn leaf/cụm để làm baseline không gian.

| Độ rộng một operand | Leaf/tích với R32 | Leaf/tích với F16 |
|---|---:|---:|
| 16 | 1 | 1 |
| 32 | 1 | 4 |
| 64 | 4 | 16 |
| 128 | 16 | 64 |

Đây là số tích schoolbook khi hai operand cùng width, chưa có reduction/rounding.
Không giảm precision FFT để làm bảng đẹp hơn.

Đối chiếu ban đầu: R32 gồm 32 leaf 32×32; F16 gồm 128 leaf 16×16, chia thành
32 cụm bốn leaf. Hai cấu hình có cùng tổng proxy diện tích nhân g², nhưng KHÔNG
cùng diện tích thực: F16 thêm mux, cây ghép, cổng kết quả và register cho lane độc lập.
Phải so thêm dưới ngân sách area sau synthesis, không chỉ cùng proxy.

## 4. Sơ đồ datapath đề xuất

~~~text
CONFIG: op, domain, width, profile_id, numeric_contract_id
                             |
A/B/w → operand registers / limb split / signedness
                             |
              operand selector theo nhóm cố định
                ↑                         |
      NTT feedback register               v
                ↑                shared multiplier array
                |                  F16 hoặc R32
                |                         |
                |              exact real/integer products
                |              taps 16/32/64/128 theo cấu hình
                |                         |
                |               +---------+----------+
                |               |                    |
                |        FFT numeric adapter    NTT reduction
                |        4M recombination       generic / profile
                |        reference rounding         |
                +----------- tích phụ ---------------+
                                |                    |
                                +---------+----------+
                                          |
       A delayed / pre-add operands → shared lane A±T ALU
                                          |
                      FFT scale/round hoặc NTT correction
                                          |
                          pairing / pack / valid / output
~~~

Sơ đồ là đường CT cơ sở. GS cần đường từ pre-add đến operand registers của bộ nhân,
và nhánh bypass cho tổng; phần mở rộng đó chưa được tính là có sẵn trong RTL.

Các tích phụ Montgomery đi vào selector qua register riêng; không dùng vòng hồi tiếp
tổ hợp. Chỉ nối các nguồn cần thiết theo nhóm, chưa giả định crossbar mọi-tới-mọi.
Fan-in của cả FFT và NTT phải được tính lại; số mux trong model FFT cũ chưa bao phủ NTT.

## 5. Mảng nhân và bộ ghép tích chính xác

### 5.1 Ranh giới giữa tile và butterfly

Leaf/tile nhân không phải một PE butterfly hoàn chỉnh. Một butterfly FFT có thể cần
nhiều leaf hợp tác; một butterfly NTT còn cần reduction và mod-add/sub.
Số leaf không trực tiếp bằng số butterfly/cycle.

F16 đề xuất ghép theo phân cấp 16 → 32 → 64 → 128. R32 dùng 32 → 64 → 128.
Mỗi mức có tap lấy từng product độc lập; nhóm không hoạt động phải có valid mask.
Không tạo riêng một core cho mỗi width rồi gọi bộ chọn output là fusion.

### 5.2 Kiểu product và độ rộng

Leaf 16/32 bit hỗ trợ signed/unsigned riêng từng operand. Kiểu kết quả thống nhất
có dấu cần 2g+1 bit để chứa cả unsigned×unsigned: 33 bit cho g=16, 65 bit cho g=32.
Tương tự, product W×W hoàn chỉnh có thể được đưa ra dạng signed 2W+1 bit thống nhất.
Các nút nội bộ phải có chứng minh bound/carry trước khi thu hẹp; chưa chốt bit-width
từng adder hoặc register của reconstructor mới chỉ từ model v0.1.

Full product là baseline đúng số học. Low-product có thể bỏ các hạng chắc chắn
không ảnh hưởng phần thấp; high-product phải giữ carry từ phần thấp. FFT rounded
extraction cần thông tin rounding/sticky theo contract, không dùng floor thay thế.

### 5.3 FFT mapping 4M trên mảng đối chiếu

Đặt B=br+j*bi, w=wr+j*wi. Tạo bốn real product chính xác:

~~~text
p0=br*wr; p1=bi*wi; p2=br*wi; p3=bi*wr
Re = p0-p1; Im = p2+p3
~~~

| Mode | Tổng leaf slots R32 / F16 mỗi complex product | Khả năng mảng đối chiếu |
|---|---:|---|
| FFT32 | 4 / 16 | 8 complex products mỗi lượt tính toán |
| FFT64 | 16 / 64 | 2 complex products mỗi lượt |
| FFT128 | 64 / 256 | 1 complex product cần 2 lượt |

“Lượt” là issue dữ liệu vào mảng, không phải latency end-to-end. Các con số giả định
mọi leaf có thể nhận một product mỗi cycle và phần ghép/hậu xử lý theo kịp.
FFT128 giữ operand; lượt 0 tạo p0,p1, lượt 1 tạo p2,p3. Mỗi real product được ghép
hoàn chỉnh trong một lượt ở cấu hình đối chiếu, cần buffer kết quả/định danh qua hai lượt.

Khác v0.1: dựng từng real product trước, không khóa cây gom trực tiếp Re/Im.
Điều này giữ được ranh giới làm tròn từng real multiplication nếu reference yêu cầu,
và làm product interface dễ tái dùng cho NTT/pointwise hơn. Chi phí tăng/giảm cần đo.
Cây Re/Im trực tiếp vẫn là ứng viên khi chứng minh cùng semantics và có lợi PPA.

## 6. FFT adapter: giữ chính xác hợp đồng đã chọn

Các width 32/64/128 tính cho mỗi thành phần thực/ảo; không phải toàn bộ số phức.
Chưa coi một width hoặc Q-format là mặc nhiên đủ cho mọi kernel FN-DSA.

Adapter phải được đặc tả theo một reference đã pin, gồm:

1. Format data/twiddle, giá trị constants và input bounds.
2. Rounding mode và vị trí rounding: từng real product hay sau complex recombination.
3. Scaling từng stage hoặc cuối transform; xử lý overflow và output format.
4. Layout/embedding/split/merge phù hợp kernel Falcon nếu adapter đó được dùng.

Nếu reference làm tròn từng p trước Re/Im, adapter làm đúng như vậy. Nếu reference
gom exact p rồi mới làm tròn Re/Im, adapter giữ đủ bit đến vị trí đó. Không mặc định
hai cách bit-identical. Giữ một contract khi so hai kiến trúc; không nhất thiết xây
một bộ adapter runtime hỗ trợ mọi cách rounding trong lần RTL đầu.

Complex recombination trên product chưa rounding có thể rộng tới 2W+1 bit.
Không coi ngân hàng butterfly ALU chứa payload W bit đã tự xử lý được bước này;
cần dimension riêng hoặc tái sử dụng accumulator qua nhiều lượt có tính chi phí.

Twiddle có bound gần đơn vị; pointwise complex product không mặc nhiên có bound đó.
Không áp dụng guard W+2 của butterfly unit-twiddle cho mọi pointwise operand.
3M, twiddle hẹp hoặc fused-rounding thay đổi output nằm ngoài baseline PQC hiện tại.

## 7. NTT backend và context

### 7.1 Profile

| Profile | Storage lane | Đường dùng dự kiến |
|---|---:|---|
| 3329 | 16 | ML-KEM, incomplete NTT và BASEMUL |
| 12289 | 16 | Ưu tiên Falcon/FN-DSA |
| 8380417 | 32 | ML-DSA |
| Prime 30–32 bit đã chuẩn bị | 32 | NTT/RNS, không bao gồm CRT ở core |

Context chứa q, word radix R, kiểu/polarity Montgomery, constants, root/seed set,
normalization và representation. Đổi q phải đồng bộ toàn context. Core không tự
sinh prime/root; N và loại transform phải hợp lệ với profile. Dùng modulus khác
không có nghĩa FN-DSA thay q theo security level.

### 7.2 Generic Montgomery

Đặt R=2^32, q lẻ <R, a,b canonical, qprime=−q^(-1) mod R:

~~~text
T = a*b
m = low32(low32(T)*qprime)
S = T+m*q                       // giữ carry 65 bit
u = S >> 32
out = u-q nếu u>=q, ngược lại u
~~~

Đây là a*b*R^(-1) mod q, chưa phải canonical multiplication thông thường nếu không
encode operand phù hợp. T<qR cho phép u<2q và một correction.

R32 dùng ba variable-product slots cho một modmul. F16 dùng 4 leaf cho T, 3 leaf
cho low32 product m, và 4 leaf cho m*q: 11 leaf slots theo schoolbook, không phải 1.
Các phép có phụ thuộc; đạt initiation interval mong muốn cần partition/pipeline đủ
cho từng loại product, delay T và context. Không suy throughput nguyên từ 32/3 hay 128/11.

### 7.3 Montgomery theo profile PQC

Với constants thưa, hai phép nhân với q và hệ số inverse có thể dùng shift-add:

| q | R | Biến thể | Constant cho m |
|---|---|---|---:|
| 3329 | 2^16 | (T+m*q)/R, sau đó trừ q nếu cần | −q^(-1) mod R = 3327 |
| 12289 | 2^16 | (T+m*q)/R, sau đó trừ q nếu cần | −q^(-1) mod R = 12287 |
| 8380417 | 2^32 | (T−m*q)/R, sau đó cộng q nếu âm | q^(-1) mod R = 58728449 |

Khi đó một modmul chỉ có một general product a*b; reducer vẫn tốn cộng/trừ,
register và routing. Chọn một trong vài profile cần mux/mạng hằng số tương ứng,
không đồng thời có hiệu suất hằng số này cho mọi q runtime tùy ý.

F16 có thể dùng một leaf cho tích chính q3329/q12289, bốn leaf cho q8380417.
R32 dùng một leaf cho cả ba. Lợi thế narrow-lane chỉ thành throughput nếu có đủ
reducer issue capacity, mod-add/sub và data/twiddle. So Barrett/Shoup là thí nghiệm,
không mặc định chúng hơn Montgomery sau khi tối ưu constant products.

### 7.4 Representation và kernel ngoài butterfly

Data canonical + root wR: Mont(B,wR) cho kết quả B*w canonical. Với pointwise,
hai operand canonical cần conversion phù hợp trước khi dùng Montgomery.
All-Montgomery là ứng viên khác, phải tính entry/exit và normalization toàn workload.

INTT dùng inverse roots và factor normalization đúng miền. Có thể khảo sát
half_q(x)=(x+(x&1)*q)>>1 cho x canonical, hoặc ghép factor vào phép nhân phù hợp.
Không dùng rounding FFT để thực hiện chia modular.

BASEMUL q3329 cần các phép nhân và cộng trên cặp hệ số, không phải scalar pointwise.
Phải có opcode/bypass để điều khiển các primitive đó; chưa tuyên bố hoàn tất BASEMUL
hoặc toàn bộ FN-DSA chỉ nhờ có butterfly.

## 8. Ngân hàng cộng/trừ chung và CT/GS

CT: T=B*w; U=A+T; V=A−T. FFT dùng số phức; NTT dùng arithmetic modulo q.

| Mode, tại ngân sách data 512 bit | Payload mỗi phía của A±T |
|---|---:|
| FFT32, 4 butterfly | 8 thành phần ×32 =256 bit |
| FFT64, 2 butterfly | 4 thành phần ×64 =256 bit |
| FFT128, 1 butterfly khi đủ kết quả | 2 thành phần ×128 =256 bit |
| NTT16, 16 butterfly | 16×16 =256 bit |
| NTT32, 8 butterfly | 8×32 =256 bit |

Đây là payload, không phải width vật lý một adder. Cần guard FFT, carry/borrow NTT,
isolation giữa lane và cả hai output tổng/hiệu. q gần 2^32 cần 33 bit cho tổng.
Hai nhánh modular correction có chi phí thực: thêm hardware hoặc nhiều lượt qua ALU.
Không vừa tính full throughput vừa coi correction là miễn phí.

GS: U=A+B; V=(A−B)*w. Muốn dùng cùng mảng, phải đưa pre-add đến multiplier,
giữ nhánh tổng và căn metadata. Với FFT, A−B có thể cần W+1 bit; không cắt về W.
Counts FFT ở mục 5 là CT, không tự áp dụng cho GS. Quyết định hỗ trợ GS phải gắn
với width, numeric contract và kết quả đo, chưa chỉ thêm một mode bit vào sơ đồ CT.

Không ép complex recombination, butterfly add/sub và Montgomery correction xảy ra
cùng lúc trên một ngân hàng có capacity chỉ đủ một trong các công việc đó.

## 9. Giới hạn song song và dữ liệu

So khả năng issue tích chính trước khi tính reducer/ALU/memory:

| Kernel | R32: 32 leaf | F16: 128 leaf |
|---|---:|---:|
| NTT16 theo profile, một general product | 32 | 128 |
| NTT32 theo profile, một general product | 32 | 32 |
| FFT32 4M complex product | 8 | 8 |
| FFT64 4M complex product | 2 | 2 |
| FFT128 4M complex product, trung bình qua hai lượt | 0,5 | 0,5 |

Các số là trần số học lý tưởng theo lượt issue, chưa phải butterfly throughput đo được.
Không gán NTT generic Montgomery vào dòng một-product.

Với I/O butterfly chứa A và B, cùng payload input/output mỗi hướng:

| Data bit/cycle mỗi hướng | Trần NTT16 butterfly/cycle | Trần NTT32 | Trần FFT32 |
|---|---:|---:|---:|
| 512 | 16 | 8 | 4 |
| 1024 | 32 | 16 | 8 |
| 2048 | 64 | 32 | 16 |

Twiddle có đường riêng và cũng phải cấp đủ. Ở 512, F16 không tăng throughput NTT16
so R32 trong model cũ; ở 2048, trần data cho phép thấy khác biệt 64 so 32 nếu đủ
reducer/ALU. Không suy ra 2048 là điều kiện phổ quát: phụ thuộc số leaf, reuse,
giao diện và mọi nút thắt của cấu hình. Năng lượng khi dùng ít leaf hơn phải đo riêng.

## 10. Interface và ranh giới hiện thực

Configuration: op, domain, fft_width, profile_id, numeric_contract_id và normalization.
Baseline pin một contract FFT cho mỗi kernel trước; không bắt buộc runtime-select mọi contract.

Ops dự kiến: BUTTERFLY_CT, CMUL, MULMOD, ADD_SUB và PRODUCT_RAW; các micro-ops
cho BASEMUL/split/merge được đặc tả sau. GS chưa thuộc ops đã dimension xong.
PRODUCT_RAW giữ bypass trước rounding/reduction, phục vụ conversion và kiểm chứng.

Input/output mang transaction ID, lane_valid và component/pass khi cần. Overflow FFT
được báo, không âm thầm saturation/wrap. Chuyển cấu hình sau khi drain toàn bộ
product/pairing/feedback buffers. Điều này là ràng buộc giao diện, chưa phải scheduler.

Chọn flow control cụ thể trước RTL core. Các tile hiện có chưa có valid/CE; không
được hứa stall pipeline bằng một dây ready khi các register vẫn chạy tự do.
Phải thêm CE đồng bộ hoặc thiết kế buffer/handshake với capacity được chứng minh.

## 11. Dữ liệu hiện có và những phép kiểm tra còn thiếu

- [RTL L32](hdl/tile_l32.v), [RTL bốn L16 ghép/tách](hdl/tile_l16x4.v) đã có ở cấp tile.
- [Study tile](docs/tile_analysis.md) báo 36 884 kiểm tra Icarus không lỗi; generic synthesis
  cho thấy lựa chọn ghép/tách tốt nhất đắt thêm khoảng 16–26% combinational GE so với
  L32 tốt nhất trong cùng flow và khoảng gấp đôi FF ở wrapper được xét. Đây là dữ liệu
  lịch sử cấp tile, không phải PPA core v0.2 hoặc kết quả FPGA/ASIC đích.
- [Model liên tile cũ](docs/intertile_model.md) dùng cây Re/Im trực tiếp; không xác nhận
  reconstructor từng real product, routing NTT hay pipeline v0.2.
- [Phân tích số học](docs/arithmetic_reassessment.md) có các identity/bound Montgomery,
  Barrett, Shoup và FFT; không thay differential check với reference FN-DSA đã pin.
- [Model width/fusion v0.2](model/core_fusion_v02.py) kiểm tra decomposition theo
  leaf 16/32, dấu và mapping 4M; báo cáo riêng tại [kết quả](study/results/core_fusion_v02.md).

Trình tự quyết định core:

1. Pin numeric contract; kiểm tra integer identity/bound và kernel bit-exact trước PPA.
2. So F16/R32 cùng chức năng, giữ cả same-count-proxy và area-budget sau synthesis.
3. Tổng hợp reconstructor, operand routing, FFT adapter và reducer theo profile.
4. Định cỡ ALU/correction/rounder/pairing đủ cho issue rate của từng mode.
5. So 512/1024/2048 và các workload FN-DSA/PQC; báo time/area/energy, không tối ưu
   chỉ theo phần trăm tile bận hoặc tỷ lệ chia sẻ.
6. Chốt F16 hoặc R32 và CT/GS bằng kết quả; sau đó mới khóa scheduler và memory layout.

Không gọi F16 tối ưu trước khi có các kết quả này. Lý do đưa F16 vào trung tâm so sánh
là nó hiện thực được việc tách lane hẹp mà R32 hiện tại không có.
