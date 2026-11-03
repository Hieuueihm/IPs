# FlexTransform — kiến trúc core tái cấu hình

> Bản v0.1 để review — 25/10/2026.
> Phạm vi: datapath số học, ghép tile, cây gom, xử lý FFT/NTT và giao diện dữ liệu.
> Chưa đặc tả scheduler, địa chỉ RAM, DMA hoặc lịch các stage của transform.
> Không phải thông báo core hoàn chỉnh đã được hiện thực hoặc đạt các throughput nêu dưới.

> Trạng thái nghiên cứu: đang phân tích lại phép toán trước khi khóa ARC tiếp theo.
> Xem [phân tích FFT/NTT và ứng viên chia sẻ](docs/arithmetic_reassessment.md).
> Các lựa chọn dưới đây được giữ làm baseline v0.1 để đối chiếu.
> Ràng buộc PQC: mọi tối ưu phải giữ precision và khớp numeric contract/reference
> đã chọn. Các đề xuất format/rounding trong bản v0.1 chưa thay cho kiểm chứng đó;
> không tự bật 3M, twiddle hẹp hoặc fused rounding nếu làm thay đổi kết quả.

## 1. Những quyết định chính để kiểm tra trước

| ID | Quyết định | Trạng thái |
|---|---|---|
| A1 | Một mảng tile nhân dùng chung cho FFT và NTT | Hướng đã thống nhất |
| A2 | K=32 tile L32; mỗi tile nhân 32×32, chọn signed/unsigned từng operand | Theo PLAN và phân tích tile hiện tại |
| A3 | Ghép giữa tile; tile L32 không tách xuống leaf 16 bit | Đã chọn cho cấu hình cơ sở |
| A4 | Cây gom nhị phân 5 cấp, dịch cố định, lấy kết quả theo precision | Đã có model số học; chưa có RTL cây |
| A5 | FFT32/64/128 là fixed-point, width tính cho mỗi thành phần thực/ảo | Phạm vi hiện tại |
| A6 | Đường FFT và modular reduction NTT là các khối hoàn tất riêng | Hướng đã thống nhất |
| A7 | NTT có context q/constants/root; FN-DSA ưu tiên q=12289 | Hướng đã thống nhất |
| A8 | Dùng butterfly CT làm kernel cơ sở trong sơ đồ v0.1, cả thuận và nghịch | Đề xuất để review; khác ứng viên CT-thuận/GS-nghịch trong PLAN |
| A9 | Twiddle cùng width data nhưng Q2.(W−2), theo model liên tile hiện tại | Đề xuất để review; cần đồng bộ lại giả định format trong PLAN |
| A10 | Data 512 bit đọc + 512 bit ghi mỗi cycle; twiddle có đường riêng | Ngân sách để định cỡ, chưa chứng minh layout/cổng RAM |

**Đối tượng tái cấu hình là cách mảng tile hợp tác và đường lấy kết quả.**
Đổi mode không tạo thêm multiplier vật lý hoặc thay đổi RTL đã tổng hợp.

## 2. Sơ đồ core

~~~text
         CONFIG: domain, fft_width, modulus_profile, normalization
                                    |
 DATA: A, B ----------------+       |       +---------- TWIDDLE: w
                            v       v       v
                    +-------------------------+
                    | Operand registers       |
                    | Unpack / limb selection |
                    +------------+------------+
                                 |
                    +------------v------------+
                    | Operand distribution    |
                    | Mux theo mode + sign    |
                    +------------+------------+
                                 |
                    +------------v------------+
                    | 32 x tile L32           |
                    | exact 32x32 -> 65 bits  |
                    +------+------------+-----+
                           |            |
                         FFT           NTT
                           |            |
       +-------------------v---+    +---v-------------------------+
       | Inter-tile tree       |    | Modular product backend     |
       | fixed shifts + taps   |    | PQC fast reducer: candidate  |
       | complex Re/Im         |    | Montgomery: reuse tiles      |
       +-----------+-----------+    +---------------+-------------+
                   |                               |
       +-----------v-----------+    +--------------v--------------+
       | Round complex product |    | Canonical residue t          |
       | Keep guard bits       |    | Correct Montgomery domain    |
       +-----------+-----------+    +--------------+--------------+
                   |                               |
 A delayed --------+-------------------------------+
                   |                               |
       +-----------v-----------+    +--------------v--------------+
       | Complex CT add/sub    |    | Modular CT add/sub           |
       | Stage scale / RNE     |    | Optional inverse normalize   |
       +-----------+-----------+    +--------------+--------------+
                   |                               |
                   +---------------+---------------+
                                   |
                    +--------------v--------------+
                    | Output pairing / pack       |
                    | Valid mask / overflow flag  |
                    +--------------+--------------+
                                   |
                              DATA: U, V
~~~

Đường A đi vòng qua phép nhân phải được giữ đúng cùng butterfly với kết quả b*w.
Ở Montgomery, các tích phụ quay lại mảng tile qua một đường operand chuyên dụng;
mũi tên đó được lược trong hình để giữ sơ đồ dễ đọc.

Core xử lý nhiều butterfly của cùng cấu hình trong pipeline. Bản cơ sở chưa trộn
FFT và NTT hoặc nhiều modulus đồng thời.

## 3. Ranh giới giữa các khối

| Khối | Trách nhiệm | Không đảm nhiệm |
|---|---|---|
| Operand registers/distribution | Giữ input, tách limb, chọn nguồn và signedness | Chọn địa chỉ RAM cho transform |
| Tile array | Tạo tích số nguyên chính xác | Rounding hoặc modulo |
| Inter-tile tree | Căn trọng số, cộng/trừ và ghép Re/Im | Scale theo stage hoặc saturation |
| FFT postprocess | Rounding, cộng/trừ phức và normalization đã chọn | Tự suy đoán precision đủ cho signing |
| Modular backend | Modular product, correction, representation | Tự sinh prime/root hợp lệ |
| Output pack | Ghép thành phần, giữ định danh và valid | Đổi thứ tự toàn bộ transform |

Input/output order và ánh xạ FFT Falcon thuộc transform wrapper/adapter.
Không mặc định FFT phức thông thường có layout giống reference Falcon.

## 4. Tile L32 và signedness

### 4.1 Giao diện số học

~~~text
a[31:0], b[31:0]
a_signed, b_signed
        |
      L32
        |
p[64:0] : signed two's complement, exact product
~~~

65 bit giúp biểu diễn thống nhất cả unsigned×unsigned và các tổ hợp có dấu.
Không ép mọi product thành signed 64 bit: tích hai unsigned 32 bit có thể vượt
miền signed 64 bit.

RTL đã có:

- [mul_ss.v](hdl/mul_ss.v): combinational sign-select multiplier.
- [tile_l32.v](hdl/tile_l32.v): thanh ghi input/output, latency khai báo 2 cycle.

Độ sâu pipeline của tile khi ghép core còn là tham số hiện thực.
Tag và valid của core phải đi qua đúng cùng số tầng với product; RTL tile hiện tại
chưa có các tín hiệu này.

### 4.2 Cách chia số rộng

Với radix B=2^32:

~~~text
x = sum(x_i * B^i)
y = sum(y_j * B^j)
x*y = sum((x_i*y_j) * B^(i+j))
~~~

Limb thấp là unsigned. Limb cao nhất của một giá trị signed mang dấu.
Mỗi product được sign-extend đúng trước khi cộng ở cây.

Ví dụ signed 64 bit x=-1:

~~~text
x0 = 0xFFFFFFFF, interpreted unsigned
x1 = 0xFFFFFFFF, interpreted signed = -1
x  = x0 + 2^32*x1 = -1
~~~

Baseline dùng schoolbook. Karatsuba và nhân phức ba real product là nhánh so sánh
sau, vì chúng làm thay đổi độ rộng tổng đầu vào và cấu trúc gom.

## 5. Cây gom liên tile

### 5.1 Gom trực tiếp thành phần nhân phức

Gọi B=br+j*bi, w=wr+j*wi:

~~~text
P_Re = br*wr - bi*wi
P_Im = br*wi + bi*wr
~~~

Cấp đầu ghép hai product có cùng trọng số bằng cộng hoặc trừ.
Các cấp sau ghép theo chỉ số limb.

Với x là vector 32 product:

~~~text
L1[k] = x[2k] +/- x[2k+1]                 k=0..15
L2[k] = L1[2k] + (L1[2k+1] << 32)        k=0..7
L3[k] = L2[2k] + (L2[2k+1] << 32)        k=0..3
L4[k] = L3[2k] + (L3[2k+1] << 64)        k=0..1
L5[0] = L4[0] + (L4[1] << 64)
~~~

L1 dùng trừ cho đóng góp Re, cộng cho Im. Trong FFT64, các nhóm Re và Im có thể
cùng tồn tại trong một cycle nên dấu điều khiển riêng theo nhóm.
Những đầu vào không hợp lệ phải bị mask; không để giá trị cũ đi vào nhóm đang hoạt động.

### 5.2 Điểm lấy kết quả theo mode

| Mode | Tile/thành phần Re hoặc Im | Tap | Cách dùng mảng K=32 |
|---|---:|---|---|
| FFT32 | 2 | L1 | Tối đa 16 thành phần = 8 complex product mỗi lượt |
| FFT64 | 8 | L3 | 4 thành phần = 2 complex product mỗi lượt |
| FFT128 | 32 | L5 | 1 thành phần mỗi lượt; Re/Im cần hai lượt |

Đây là khả năng phần nhân/cây gom, chưa gồm giới hạn các khối phía sau.
FFT32 bị giới hạn còn 4 butterfly/cycle theo ngân sách data 512 bit.

Ví dụ mapping FFT64:

~~~text
tile  0.. 7 -> Re của butterfly 0
tile  8..15 -> Im của butterfly 0
tile 16..23 -> Re của butterfly 1
tile 24..31 -> Im của butterfly 1
~~~

FFT128 dùng cả 32 tile cho Re hoặc Im. Mỗi lượt tạo một thành phần hoàn chỉnh,
do đó cấu hình K=32 này không cần accumulator cộng dồn partial product giữa hai lượt.
Cần buffer ghép Re/Im đúng định danh; đây là chức năng khác accumulator.

### 5.3 Độ rộng phần cứng theo model hiện có

| Cấp | Số nút | Width output/nút | Shift của nhánh trên |
|---|---:|---:|---:|
| Tile product | 32 | 65 | — |
| L1 | 16 | 66 | 0, cộng/trừ |
| L2 | 8 | 98 | 32 |
| L3 | 4 | 130 | 32 |
| L4 | 2 | 193 | 64 |
| L5 | 1 | 257 | 64 |

Width là chặn trên từ model interval; không có nghĩa mọi bit đều cần đi qua
một bộ cộng đầy đủ. Những bit thấp không chồng trọng số có thể đi thẳng.
Model hiện tại báo 31 nút cộng, tổng 2427 bit cộng hữu hiệu.

Nguồn kiểm tra:
[intertile model](docs/intertile_model.md),
[Python model](model/intertile_model.py),
[mapping K=32](study/results/intertile_map_k32.csv).

Pipeline register và chi phí mux/tap chưa được tổng hợp ở cấp cây.
Lượng dịch cố định được hiện thực bằng wiring/sign extension, không cần barrel shifter.

## 6. Đường FFT fixed-point

### 6.1 Biểu diễn đề xuất để review

Quy ước QI.F: I gồm bit dấu; W=I+F.

| Mode | Data mỗi real/imag | Twiddle mỗi real/imag |
|---|---|---|
| FFT32 | Q16.16 | Q2.30 |
| FFT64 | Q32.32 | Q2.62 |
| FFT128 | Q64.64 | Q2.126 |

Width data và twiddle bằng nhau; số bit phần lẻ khác nhau.
Đây là format trong model liên tile hiện tại, biểu diễn được cả +1 và -1 của twiddle.
PLAN mục 4.3 còn giả định cùng số bit lẻ cho reference; cần chọn một hợp đồng thống nhất
trước khi tạo ROM/golden model chính thức. Bản này chưa sửa PLAN.

Twiddle hợp lệ có từng thành phần nằm trong [-1,1].
FFT32 dùng đánh giá co giãn; chưa gán mode này cho một kernel signing FN-DSA.

### 6.2 Hợp đồng CT đề xuất

~~~text
P_Re = exact(br*wr - bi*wi)
P_Im = exact(br*wi + bi*wr)

t_Re = RNE(P_Re / 2^F_twiddle)
t_Im = RNE(P_Im / 2^F_twiddle)

u = RNE((a + t) / 2^stage_shift)
v = RNE((a - t) / 2^stage_shift)
~~~

RNE là round-to-nearest, ties-to-even; thực hiện riêng cho real/imag.
Không làm tròn từng limb product.

Đề xuất giữ W+2 bit có dấu cho t và kết quả cộng/trừ trước stage scaling:
với |wr|,|wi|<=1, mỗi thành phần t có trị tuyệt đối không quá 2^W;
cộng thêm thành phần a vẫn nằm trong miền signed W+2 bit.
Sau rounding/scaling, kiểm tra fit W bit trước khi pack; overflow phải được báo.

stage_shift là tham số công khai của phép toán, chưa chốt giá trị theo từng stage.
Core không tự thay đổi precision dựa trên giá trị hệ số.

Hợp đồng trên làm tròn nhân phức trước cộng/trừ butterfly.
Đổi sang fused butterfly chỉ làm tròn ở cuối sẽ là một semantics khác cần đánh giá riêng.
Cùng Q-format chưa bảo đảm bit-match với NTRUGen hoặc prototype fixed-point signing.

### 6.3 IFFT và quyết định CT/GS

V0.1 dùng cùng kernel CT cho FFT và IFFT. Hướng nghịch chọn bộ twiddle nghịch;
normalization 1/N phải được thực hiện đúng một lần, hoặc phân bố bằng một hợp đồng
stage scaling tương đương đã kiểm chứng.

Input/output ordering do transform wrapper xác định. Dùng CT cho IFFT không hàm ý
wrapper được dùng nguyên mọi thứ của FFT thuận.

Nếu chuyển sang GS, cần xử lý (a+b) và (a-b) trước nhân. Trong fixed-point, các tổng
này có thể cần W+1 bit; không được cắt về W rồi giữ nguyên model tile count mà
không có bound/headroom hoặc scaling hợp lệ.

Vì vậy, CT/GS là điểm cần review trước RTL core; GS không được coi là một bit mux miễn phí.

## 7. Đường NTT nhiều modulus

### 7.1 Modulus profile

Mỗi profile chứa:

~~~text
q, storage_width, reduction_kind
Montgomery q_prime = -q^(-1) mod 2^32, R^2 mod q nếu dùng
root/twiddle set, inverse-normalization constants
supported N, ordering và representation
~~~

Core dùng profile đã chuẩn bị hợp lệ; không kiểm tra primality hoặc sinh root trong datapath.

| Profile | Storage lane | Mục đích |
|---|---:|---|
| q=12289 | 16 bit | Falcon/FN-DSA |
| q=3329 | 16 bit | ML-KEM, NTT không đầy đủ |
| q=8380417 | 32 bit | ML-DSA |
| Bảng prime 30–32 bit | 32 bit | RNS; host xử lý CRT |

Các operand đều vừa tile L32. Đổi q không làm tile tự tách thành lane nhỏ.

### 7.2 Hai ứng viên modular backend

**Backend tổng quát Montgomery** có công thức rõ ràng để làm baseline chức năng.
Đặt R=2^32, q lẻ, 0<q<R, 0<=a,b<q:

~~~text
T = a*b                         : full 64 bits
m = (low32(T)*q_prime) mod R     : low 32 bits
S = T + m*q                     : giữ carry, 65 bits
u = S >> 32                     : tối đa cần 33 bits
out = u-q nếu u>=q, ngược lại u
~~~

out tương ứng a*b*R^(-1) mod q. Khi dùng operand Montgomery, kết quả giữ đúng miền;
conversion và twiddle encoding phải được định nghĩa trong profile.

T<qR nên u<2q, đủ một correction. Không làm mất carry của S.
Ba phép nhân (a*b, low32(T)*q_prime, m*q) đều dùng tile; chúng có phụ thuộc dữ liệu.
Không coi một modular multiply chỉ tốn một product slot.

Ví dụ định cỡ 8 Montgomery lane: ba nhóm 8 tile cho ba tầng product, tổng 24 tile,
để các butterfly khác nhau đi qua pipeline. Cần delay T và metadata tương ứng.
Đây là phương án kết nối để khảo sát; latency từng tầng và throughput thực chưa đo.

**Backend nhanh PQC** là ứng viên cho 3329/12289/8380417: reducer chuyên biệt
hoặc Barrett với constants cố định theo profile. Công thức, bound, tích phụ và chi phí
phải được dẫn xuất trước khi chốt. Chưa có cơ sở tuyên bố các lane đó miễn phí.

Hai phương án cần so: Montgomery cho mọi q; hoặc backend nhanh PQC kết hợp Montgomery RNS.

### 7.3 Butterfly, inverse và BASEMUL

CT modulo:

~~~text
t = modmul(b,w)
u = canonical(a+t mod q)
v = canonical(a-t mod q)
~~~

INTT dùng inverse roots và normalization đúng miền. Normalization tiêu thụ modular
multiply nếu không được ghép vào một phép khác đã chứng minh tương đương.
Số lane normalization phải được tính vào resource/throughput.

Ở q=3329, N=256 dùng NTT 7 stage, dừng ở các khối bậc 2.
BASEMUL của một cặp có dạng:

~~~text
c0 = a0*b0 + zeta*a1*b1 mod q
c1 = a0*b1 + a1*b0      mod q
~~~

Đường này cần tổ hợp nhiều modmul và cộng modulo; không đồng nhất nó với một
pointwise multiply vô hướng. Cách tái sử dụng datapath cho BASEMUL còn cần đặc tả riêng.

## 8. Cấp dữ liệu và giao diện core

### 8.1 Ngân sách dữ liệu dùng để định cỡ

| Mode | Data input cho một butterfly | Butterfly/cycle theo data 512 bit | Twiddle tại mức đó |
|---|---:|---:|---:|
| FFT32 | 128 bit | 4 | 256 bit/cycle |
| FFT64 | 256 bit | 2 | 256 bit/cycle |
| FFT128 | 512 bit | 1 | 256 bit/cycle |
| NTT lane16 | 32 bit | 16 | 256 bit/cycle |
| NTT lane32 | 64 bit | 8 | 256 bit/cycle |

Data output có cùng payload với input. Đề xuất giao diện payload data 512 bit mỗi
hướng và twiddle 256 bit/cycle, với valid mask.
Đây là khả năng giao diện mong muốn; chưa quyết định số bank hoặc cổng RAM vật lý.

FFT128 bị compute giới hạn 0,5 butterfly/cycle: có thể giữ operand và twiddle
trong register cho hai lượt. 256 bit twiddle/cycle là trần giao diện, không phải
traffic trung bình bắt buộc ở mode này.

### 8.2 Giao diện logic đề xuất, chưa phải pin-level RTL

| Nhóm | Nội dung |
|---|---|
| Configuration | domain, fft_width/profile_id, normalization policy |
| Input | A/B/w, butterfly_id, component/pass khi cần, lane_valid |
| Output | U/V, butterfly_id, lane_valid, overflow/error |
| Flow control | valid/ready hoặc stall/clock-enable đồng bộ toàn pipeline |

Phải giữ cấu hình của mọi phép đang bay cho đến khi phép đó hoàn tất.
Chuyển mode ở ranh giới đã drain hoặc mang context đi cùng dữ liệu; V1 ưu tiên drain.
Đây là ràng buộc interface, chưa phải thiết kế scheduler.

Với FFT128, buffer ghép Re/Im có định danh và hai cờ hoàn tất.
Dung lượng buffer phụ thuộc pipeline latency; chưa chốt trước khi pipeline được định cỡ.
Output chỉ hợp lệ khi đủ thành phần của đúng butterfly.

## 9. Module dự kiến và ranh giới phần đã có

| Module chức năng | Trạng thái |
|---|---|
| L32 multiplier và register wrapper | Có hdl/mul_ss.v, hdl/tile_l32.v |
| Operand distribution theo mode | Có mapping model; chưa có RTL core |
| Cây gom 5 cấp + taps | Có model/mapping/bound; chưa có RTL |
| FFT rounding + CT add/sub | Semantics đề xuất ở mục 6; cần golden model đầy đủ |
| Re/Im pairing và valid/tag | Chưa có RTL |
| Modular backend và normalization | Chưa chọn kết quả hiện thực cuối |
| PQC BASEMUL | Yêu cầu chức năng; chưa chốt datapath tái sử dụng |
| Output pack và flow control | Chưa có RTL |

RTL lõi giữ độc lập công nghệ; vendor DSP/RAM wrapper hoặc backend chuyên biệt
đặt riêng. Bản này không tạo module HDL mới.

## 10. Những điểm cần duyệt

1. **Giữ L32 và K=32** làm core cơ sở; L16 là thí nghiệm với ngân sách memory khác?
2. **Chọn cây gom trực tiếp Re/Im với taps L1/L3/L5**, thay vì dựng từng real product riêng?
3. **Dùng Q2.(W−2) cho twiddle** như model hiện tại và đồng bộ numeric contract/PLAN?
4. **V1 dùng CT cho cả hai hướng**, hay cần GS ngay và mở rộng phân tích headroom trước nhân?
5. **Giữ rounding nhân phức trước butterfly add/sub** như mục 6, hay khảo sát fused rounding?
6. **Montgomery tổng quát trước, backend nhanh PQC sau**, hay đưa cả hai vào lần RTL đầu?
7. **Định cỡ theo 512-bit data và 256-bit twiddle**, rồi mới chứng minh memory có cấp được?

Các điểm trên là nội dung review, chưa tự động thay các lựa chọn trong PLAN.
Hiện chưa chốt Fmax, FPGA cụ thể, vị trí pipeline register hay số cycle end-to-end.

## 11. Cơ sở từ bốn bài đã chọn

| Paper | Điều dùng để định hướng | Phần do đề tài tự thiết kế/đánh giá |
|---|---|---|
| Unified FFT/NTT, ICASSP 2025 | Chia sẻ arithmetic giữa fixed-point FFT và NTT | FFT32/64/128 trên cùng mảng tile |
| BitFusion, ISCA 2018 | Ghép/tách cần product decomposition và shift-add | Output butterfly độc lập, signed limbs, numeric semantics |
| Maestro, arXiv 2025, Section V | Precision gắn với butterfly parallelism và data movement | Fixed-point, width lớn và tree/taps của mình |
| OpenNTT, TCAD | Modulus profile, runtime/design-time và datapath theo q lớn nhất | Cùng mảng nhân cho FFT đa precision và NTT |

Nguồn:
[Unified FFT/NTT](https://arxiv.org/html/2504.11124v1),
[BitFusion](https://arxiv.org/html/1712.01507v2),
[Maestro](https://arxiv.org/html/2503.04581v1),
[OpenNTT](https://flokrieger.github.io/papers/tcad25_opennttext.pdf).

Bốn bài định hướng kiến trúc, chưa chứng minh tính mới của tổ hợp.
Xem thêm [IDEA](IDEA.md), [PLAN](PLAN.md) và [related work](docs/related_work.md).

## 12. Kiểm tra bản v0.1

Kiểm tra số học khi soạn ngày 25/10/2026, không ghi đè các kết quả study:

- 1870 đầu ra thành phần nhân phức qua mapping/tree K=32, gồm biên và ngẫu nhiên.
- Độ rộng vật lý các cấp khớp model: 66/98/130/193/257 bit.
- 3456 tổ hợp biên xác nhận miền W+2 cho postprocess FFT với từng thành phần twiddle trong [-1,1].
- 545 trường hợp xác nhận công thức Montgomery, carry 65 bit và bound u<2q.
- Kiểm tra encoding, code fence và các link nội bộ của tài liệu.

Các phép kiểm tra trên không xác nhận pipeline, backpressure, transform hoàn chỉnh,
numeric security của FN-DSA hoặc PPA. Chúng cũng không thay các lựa chọn cần review ở mục 10.
