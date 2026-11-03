# FlexTransform v0.2 — core butterfly trên mảng nhân ghép/tách

> Đề xuất kiến trúc cập nhật ngày 25/10/2026; chưa phải RTL core hay kết quả PPA.
> Bản này thay đề xuất core v0.1 ở các điểm liệt kê tại mục 1.
> [Bản v0.1 được lưu để đối chiếu](docs/plan_history/ARCHITECTURE_v0.1_2026-10-25.md).
> Tập trung số học, operand routing và giao diện; chưa thiết kế scheduler/RAM/DMA.
> Ràng buộc PQC: giữ precision, constants, scaling và rounding của reference đã chọn.
> Cập nhật sau review 25/10/2026: batching/latency cho F16 (mục 9.1), phương án CT-only cho
> phép biến đổi nghịch (mục 8.1), cây dịch cố định cho từng tích thực (mục 5.4), sửa câu về floor;
> product bus cố định (5.5), bộ kiểm tra so sánh với R8 (6.1), reducer chung 3329/12289 (7.3),
> nguồn twiddle (7.5).
> [Bản trước review](docs/plan_history/ARCHITECTURE_v0.2_before_review_2026-10-25.md).

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
| CT/GS | CT là kernel đầu tiên; so GS với phương án CT-only cho phép biến đổi nghịch (mục 8.1) | Chưa khóa hỗ trợ GS |
| Product reconstructor | Cây nhị phân dịch cố định theo trọng số limb, tap theo width (mục 5.4) | Đã kiểm bit-exact ở model; chưa có RTL |
| Batching | So F16/R32 cả khi có và không có nhiều transform độc lập xen kẽ (mục 9.1) | Tiêu chí so sánh bắt buộc |
| Product bus | 16 khe × 65 bit cố định giữa mảng nhân và khối xử lý sau (mục 5.5) | Đề xuất; kiểm bằng PPA |
| Twiddle | NTT: một twiddle RAM nạp từ seed khi đổi context; FFT: ROM (mục 7.5) | Đề xuất |
| Reducer 3329/12289 | Một mạng shift-add chung, bit bật/dấu theo profile (mục 7.3) | Đề xuất; so với hai mạng riêng |
| Contract FFT | Pin bằng bộ kiểm tra so sánh với reference fixed-point R8 (mục 6.1) | Làm trước RTL core |
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
không ảnh hưởng phần thấp; high-product phải giữ carry từ phần thấp. Bước trích kết quả
FFT làm đúng phép làm tròn của contract: nếu contract là round-to-nearest thì cần bit
rounding/sticky; nếu reference dịch phải số học (floor) thì phần cứng phải dùng đúng floor
để khớp bit. Không tự đổi phép làm tròn so với reference đã pin.

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

### 5.4 Cây dịch cố định cho từng tích thực

Kết quả của [model liên tile v0.1](docs/intertile_model.md) vẫn áp dụng cho v0.2: dựng từng
tích thực tương đương cây cũ bỏ bit “thành viên cặp” ở cấp 1. Xếp các bit chỉ số limb theo
trọng số (i0, j0 rồi i1, j1, …) thì mỗi cấp có một lượng dịch duy nhất, dùng chung cho mọi
width; mode chỉ chọn cấp tap. Không cần bộ dịch thay đổi theo mode hay cắt carry.

Kiểm tra bằng [model/product_tree_v02.py](model/product_tree_v02.py): 18 216 tích thực
(biên và ngẫu nhiên, operand signed) tái tạo chính xác.

| Leaf | Dịch theo cấp (bit) | Tap: W=32 / 64 / 128 | Độ rộng nút lớn nhất | Bit cộng một cây W=128 |
|---:|---|---|---:|---:|
| 32 | [32, 32, 64, 64] | 0 / 2 / 4 | 256 | 1 356 |
| 16 | [16, 16, 32, 32, 64, 64] | 2 / 4 / 6 | 256 | 3 196 |

Với R32, K = 32: hai cây 16 tile chạy song song ở FFT128 (2 tích/lượt), tổng khoảng 2 700 bit
cộng, cùng cỡ cây Re/Im trực tiếp của v0.1 (2 427 bit). Hệ quả so với v0.1:

- Gộp Re/Im **sau** khi làm tròn từng tích chỉ cần W+2 bit (34/66/130 với twiddle đơn vị cùng
  Q-format, kiểm tra ở giá trị biên), thay vì 2W+1 bit khi gộp trước làm tròn.
- Số bộ làm tròn tăng gấp đôi: một bộ cho mỗi tích thực thay vì mỗi thành phần Re/Im.
  Định cỡ theo trần dữ liệu (ví dụ FFT32 ở 512 bit: 4 butterfly × 4 tích = 16 bộ 65 bit).
- Cấp cây và độ rộng nút là chặn trên giải tích; chưa có thanh ghi pipeline hay RTL.

### 5.5 Product bus cố định giữa mảng nhân và khối xử lý sau

Đặt một giao diện cố định giữa mảng nhân (cùng reconstructor) và khối xử lý sau
(FFT adapter, NTT reducer). F16 và R32 chỉ khác nhau **trước** bus; FFT adapter và reducer
giữ nguyên. Nhờ vậy so sánh F16/R32 công bằng và đổi lựa chọn không phải viết lại phần sau.

Đề xuất cho cấu hình 512 bit/chu kỳ: **16 khe × 65 bit**, mỗi khe kèm `slot_valid`.
Tích rộng chiếm nhiều khe liền nhau:

| Mode, tại trần dữ liệu 512 bit | Tích/chu kỳ | Độ rộng một tích | Khe dùng |
|---|---:|---:|---:|
| FFT32 (4 butterfly × 4 tích) | 16 | 65 | 16 |
| FFT64 (2 butterfly × 4 tích) | 8 | 129 | 16 |
| FFT128 (2 tích mỗi lượt) | 2 | 257 | 8 |
| NTT16 profile (16 butterfly) | 16 | ≤ 29 | 16 |
| NTT32 profile (8 butterfly) | 8 | 65 | 8 |

Metadata đi cùng mỗi nhóm khe: job/batch ID, transaction ID, loại tích (p0–p3 của FFT,
T hoặc tích phụ m/m·q của Montgomery), vị trí lượt (FFT128). Bus rộng khoảng 2× bus dữ liệu
(1 040 bit tải), cần tính vào area và routing. Ở cấu hình 1024/2048 bit, số khe nhân tương ứng.
NTT16 chỉ dùng ≤ 29/65 bit mỗi khe; nếu routing đắt, xét khe hẹp riêng cho NTT ở bước PPA.

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

### 6.1 Bộ kiểm tra so sánh với reference fixed-point FN-DSA

Contract làm tròn (từng tích hay sau khi gộp, round hay floor, scaling từng stage) quyết định
cả cây gom lẫn bộ làm tròn, nên dựng bộ kiểm tra này **trước RTL core**:

1. Pin implementation fixed-point của [R8 trong PLAN](PLAN.md)
   ([mã nguồn](https://github.com/fixed-point-fndsa/fixed-point-c)) theo commit; giữ nguyên mã gốc.
2. Gắn hook vào các lời gọi kernel FFT/iFFT và nhân đa thức trong keygen/sign để ghi
   vector: tham số, input, output và vị trí gọi. Không đổi kết quả của reference.
3. Đọc mã để chốt contract (format, rounding, scaling, overflow) vào docs/numeric_contract.md.
4. Golden model của core phải khớp bit các vector này; testbench RTL dùng lại đúng các vector đó.
5. NTT: so với `mq_NTT`/`mq_iNTT` của Falcon reference cho 12289, và reference pq-crystals
   cho 3329 (ML-KEM) và 8380417 (ML-DSA); prime RNS so với NTT số nguyên chính xác.
6. Nếu thay kernel vào luồng ký: chữ ký phải verify được bằng verifier gốc; mọi kết luận về
   phân phối chữ ký giới hạn theo điều kiện của R8.

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

Đã kiểm lại các constant trên. Viết dạng chữ số có dấu (CSD), q và hằng số dùng cho m
chỉ có 3–5 số hạng, nên phép nhân hằng là shift-add vài tầng.

Vì R khác nhau giữa các profile (2^16 cho 3329/12289, 2^32 cho 8380417 và prime RNS),
bảng root lưu dạng w·R mod q phải tạo theo đúng R của profile; context phải mang R
và bảng tương ứng, không dùng chung bảng giữa các profile.

Khi đó một modmul chỉ có một general product a*b; reducer vẫn tốn cộng/trừ,
register và routing. Chọn một trong vài profile cần mux/mạng hằng số tương ứng,
không đồng thời có hiệu suất hằng số này cho mọi q runtime tùy ý.

**Reducer chung cho 3329 và 12289.** Hai profile cùng R = 2^16, cùng biến thể (T+m·q)/R,
và hằng số ở dạng CSD gần như trùng nhau:

| Hằng số | CSD |
|---:|---|
| 3327 (−q⁻¹, q = 3329) | 2^12 − 2^10 + 2^8 − 2^0 |
| 3329 | 2^12 − 2^10 + 2^8 + 2^0 |
| 12287 (−q⁻¹, q = 12289) | 2^14 − 2^12 − 2^0 |
| 12289 | 2^14 − 2^12 + 2^0 |

Trong mỗi profile, hằng số cho m và q chỉ khác dấu của số hạng 2^0. Một mạng shift-add
dùng chung các số hạng {2^14, 2^12, 2^10, 2^8, 2^0} với bit bật/dấu theo profile phục vụ cả hai.
Datapath định cỡ theo 12289: T < 2^28, S < 2^30, u < 2q. 8380417 (R = 2^32, biến thể trừ)
dùng reducer riêng. So sánh ở bước PPA: mạng chung so với hai mạng riêng + mux đầu ra.

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

### 7.5 Nguồn twiddle: NTT sinh từ seed, FFT dùng ROM

- **NTT:** số học chính xác, nên twiddle sinh bằng nhân lũy tiến không có sai số:
  Mont(w·R, s·R) = (w·s)·R mod q, nên bảng giữ nguyên dạng Montgomery. Đề xuất **một twiddle RAM chung,
  được nạp lại bởi bộ sinh khi đổi context**, thay vì ROM riêng cho từng profile và từng prime RNS.
  Context chỉ cần mang seed (root và bước theo stage); điều này phù hợp với “core không tự sinh
  prime/root” ở mục 7.1 vì seed vẫn do host cung cấp.
- Chi phí nạp: khoảng N phép Montgomery mỗi lần đổi context, dùng lại lane nhân/reducer;
  khấu hao khi batch nhiều transform cùng profile. RAM định cỡ theo N lớn nhất (1024 × 32 bit
  cho twiddle thuận; twiddle nghịch lấy từ cùng bảng vì ψ^(−k) = −ψ^(N−k) mod q, hoặc thêm một bảng).
- Không khuyến nghị sinh twiddle **cho từng butterfly** lúc chạy: ở các stage cuối, mỗi butterfly
  có twiddle riêng, nên bộ sinh tốn thêm một phép nhân cho mỗi butterfly, gần như gấp đôi tải
  mảng nhân. Thứ tự twiddle theo bit-reversed của CT cũng không phải dãy cấp số nhân đơn giản.
- Băng thông đọc twiddle vẫn phải đủ cho trần dữ liệu (tới 64 root khác nhau mỗi chu kỳ ở
  cấu hình 2048 bit); RAM chung không giải quyết vấn đề số cổng đọc.
- **FFT:** giữ ROM. Nhân lũy tiến ở fixed-point tích lũy sai số và phá contract của mục 6.
- Tiền lệ sinh twiddle on-the-fly: OpenNTT [mục 2]; cần đối chiếu cách họ xử lý thứ tự twiddle.

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

### 8.1 Phương án CT-only cho phép biến đổi nghịch

Có thể làm phép biến đổi nghịch bằng chính butterfly CT, không cần đường pre-add vào bộ nhân:

- Dùng thứ tự địa chỉ cho đầu vào bit-reversed, đầu ra thứ tự tự nhiên, với root nghịch đảo.
- NTT negacyclic: phép untwist ψ^(−i) không gộp được vào CT nghịch như ở GS, nhưng gộp được
  với nhân N^(−1) thành **một lượt pointwise** N phép modmul — lượt N^(−1) vốn đã cần.
- Chi phí đổi lại: bộ sinh địa chỉ và thứ tự twiddle thêm một chế độ; một lượt pointwise
  (có thể đã tồn tại) so với datapath GS (pre-add vào bộ nhân, nhánh bypass, metadata).

Giới hạn quan trọng:

- **NTT:** số học chính xác, nên CT-only cho kết quả mod q giống hệt GS; khớp được reference.
- **FFT:** thứ tự phép toán và vị trí làm tròn khác reference (Falcon iFFT có cấu trúc kiểu GS),
  nên **không bit-identical**. Nếu cần khớp bit IFFT với reference đã pin, phải theo đúng cấu trúc
  của reference; CT-only cho IFFT chỉ dùng được khi contract cho phép sai số có chặn.

Quyết định GS so với CT-only cần đo cả hai: area/timing của datapath GS so với chu kỳ lượt
pointwise và chi phí bộ sinh địa chỉ, tách riêng cho NTT và FFT.

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

Số reducer và lane mod-add/sub định cỡ theo **trần dữ liệu** (16 lane ở 512 bit, 64 lane ở
2048 bit cho NTT16), không theo trần nhân 128 của F16; phần leaf vượt trần dữ liệu là rảnh.

### 9.1 Latency giữa các stage và batching

Một transform có phụ thuộc giữa các stage: stage sau đọc kết quả stage trước, nên mỗi stage
tốn khoảng (N/2)/P + L chu kỳ, với P butterfly/chu kỳ và L latency pipeline (nhân, ghép,
reducer, cộng/trừ, ghi). Throughput thực của **một** transform:

    BF/chu kỳ ≈ (N/2) / ((N/2)/P + L)

Ví dụ minh họa NTT N = 256 với L = 8 (giả định, chưa đo):

| Cấu hình | P | Chu kỳ/stage | BF/chu kỳ thực |
|---|---:|---:|---:|
| R32, 1024 bit | 32 | 4 + 8 | ≈ 10,7 |
| F16, 2048 bit | 64 | 2 + 8 | ≈ 12,8 |

Chênh lệch nhỏ hơn nhiều so với tỷ lệ trần 64 : 32. F16 chỉ khai thác được trần khi **xen kẽ
nhiều transform độc lập** để lấp latency: k đa thức của ML-KEM, các vector của ML-DSA, nhiều
prime RNS. Vì vậy:

- So F16/R32 cả trường hợp một transform và trường hợp batch; báo cáo riêng.
- Phương án bộ nhớ đáng xét cho cấu hình rộng: **song song theo đa thức** — nhiều vùng nhớ
  độc lập, mỗi vùng giữ một đa thức với bề rộng như cấu hình 512 bit, thay vì một bộ nhớ
  2048 bit chia bank cho một đa thức. Cách này tránh xung đột bank và mạng hoán vị rất rộng,
  và khớp tự nhiên với batching.
- Ở 2048 bit mỗi chiều, hệ thống bộ nhớ (khoảng 128 lane 16 bit mỗi hướng) và twiddle (tới 64
  root khác nhau mỗi chu kỳ ở các stage cuối) có thể đắt hơn mảng nhân. So diện tích **toàn
  core**, không chỉ mảng nhân.

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
- [Model liên tile cũ](docs/intertile_model.md) dùng cây Re/Im trực tiếp. Tính chất dịch cố định
  áp dụng được cho reconstructor từng tích thực của v0.2 ([model/product_tree_v02.py](model/product_tree_v02.py),
  mục 5.4); chưa xác nhận routing NTT hay pipeline v0.2.
- Review 25/10: các constant Montgomery mục 7.3, đẳng thức và bound mục 7.2 (kiểm ngẫu nhiên
  trên 5 modulus) và half_q đã kiểm lại. Các link OpenNTT ở mục 2 chưa được kiểm tra lại độc lập.
- [Phân tích số học](docs/arithmetic_reassessment.md) có các identity/bound Montgomery,
  Barrett, Shoup và FFT; không thay differential check với reference FN-DSA đã pin.
- [Model width/fusion v0.2](model/core_fusion_v02.py) kiểm tra decomposition theo
  leaf 16/32, dấu và mapping 4M; báo cáo riêng tại [kết quả](study/results/core_fusion_v02.md).

Trình tự quyết định core:

1. Dựng bộ kiểm tra so sánh với reference R8 (mục 6.1) và pin numeric contract; kiểm tra
   integer identity/bound và kernel bit-exact trước PPA.
2. So F16/R32 cùng chức năng, giữ cả same-count-proxy và area-budget sau synthesis.
3. Tổng hợp reconstructor, operand routing, FFT adapter và reducer theo profile.
4. Định cỡ ALU/correction/rounder/pairing đủ cho issue rate của từng mode.
5. So 512/1024/2048 và các workload FN-DSA/PQC, **có và không có batching** (mục 9.1),
   và **CT-only so với GS** cho phép biến đổi nghịch (mục 8.1); báo time/area/energy của
   toàn core, không tối ưu chỉ theo phần trăm tile bận hoặc tỷ lệ chia sẻ.
6. Chốt F16 hoặc R32 và CT/GS bằng kết quả; sau đó mới khóa scheduler và memory layout.

Không gọi F16 tối ưu trước khi có các kết quả này. Lý do đưa F16 vào trung tâm so sánh
là nó hiện thực được việc tách lane hẹp mà R32 hiện tại không có.
