# Phân tích lại phép toán FFT/NTT để đồng tối ưu phần chung và phần riêng

> Ngày: 25/10/2026.
> Phạm vi: FFT/IFFT, NTT/INTT radix-2, pointwise multiplication và các kernel
> liên quan trực tiếp đến arithmetic Falcon/FN-DSA.
> Mục tiêu: quyết định nên chia sẻ phần cứng nào sau khi tối ưu từng miền.
> Đây là phân tích phép toán, không phải kiến trúc đã chốt, scheduler hay kết quả PPA.

> Ràng buộc PQC: tối ưu cơ sở phải giữ precision và khớp kết quả reference đã chọn.
> Không tự giảm width/twiddle precision, bỏ carry hoặc thay rounding để đổi lấy PPA.

### Điều kiện chấp nhận trước khi so hiệu năng

1. Pin reference và numeric contract cho từng kernel; chưa chọn reference thì chưa
   kết luận một phương án đủ điều kiện đưa vào đường FN-DSA.
2. Chứng minh biến đổi đại số chính xác và miền trung gian đủ rộng, không mất bit.
3. Với FFT, giữ nguyên format, constants, scaling và quy tắc/vị trí rounding của
   hợp đồng đã chọn; kiểm tra bit-exact tại giao diện kernel tương ứng.
4. Với NTT, giữ residue chính xác và representation đúng tại giao diện;
   đổi representation nội bộ chỉ hợp lệ khi chuyển miền được chứng minh.
5. Kiểm chứng với reference trước khi dùng kết quả PPA để lựa chọn. Test random
   không thay proof về bound; ký/verify thành công không đủ chứng minh tương đương.

Các tối ưu làm thay đổi numeric semantics nằm ngoài baseline hiện tại.
Chỉ biến đổi cách hiện thực phần cứng, không tự đổi yêu cầu chính xác của bài toán.

## 1. Kết luận quan trọng từ vòng phân tích này

1. **Nhân số nguyên là phần chung rõ nhất**, nhưng phải phân biệt full product,
   low product, high product và nhân hằng số. Chúng không có cùng chi phí.
2. **Ngân hàng cộng/trừ butterfly là ứng viên chia sẻ mạnh thứ hai.**
   Cần giữ guard bits, ranh giới lane, carry/borrow và tính cả correction modulo.
3. **NTT với các modulus PQC có thể giảm còn một phép nhân biến×biến cho mỗi modmul**,
   khi hai tích với hằng số của Montgomery được hiện thực bằng shift-add.
   Vì vậy, dùng thêm tile để làm reduction chưa chắc là lựa chọn hiệu quả nhất.
4. **FFT ba phép nhân có tiềm năng**, nhưng phép cộng đầu vào tăng width.
   Có thể giữ width multiplier bằng một hạng hiệu chỉnh overflow chính xác;
   phải tính chi phí cộng, tái sử dụng product và lưu hệ số.
5. **Cây gom trực tiếp Re/Im hiện tại là ứng viên cho phương án 4M.**
   Nó chưa tự bao phủ 3M, reduction và nhiều kernel khác. Không nên dùng cây đó
   làm giả định khóa toàn bộ nghiên cứu trước khi đối chiếu các phương án.

Chưa có cơ sở gọi một phương án là tối ưu cao nhất về area, Fmax hoặc năng lượng.
Kết quả hiện tại cho biết nơi có thể giảm phép toán chính xác và thí nghiệm cần làm.

## 2. Bài toán phải được phân rã ở ba cấp

| Cấp | FFT | NTT |
|---|---|---|
| Transform | FFT/IFFT, ordering, normalization | NTT/INTT, root/twist, normalization |
| Kernel số học | Complex multiply, CT/GS, pointwise, split/merge | Modular multiply, CT/GS, pointwise, BASEMUL |
| Primitive phần cứng | Nhân số nguyên, cộng/trừ, shift, lấy bit, rounding | Nhân số nguyên, cộng/trừ, shift, lấy bit, correction |

Tối ưu chung nên bắt đầu ở primitive và kiểm tra lại kernel.
Hai biểu thức cùng có dấu “nhân” không đủ chứng minh dùng chung có lợi:
width, signedness, bit cần giữ và số kết quả độc lập mới quyết định hardware.

Không mặc định giữ K=32, leaf 32 bit hoặc băng thông 512 bit khi tìm phương án tốt nhất.
Chúng được giữ làm **điểm đối chiếu có sẵn**, không phải kết luận của vòng phân tích mới.
Không yêu cầu FFT và NTT chạy đồng thời để có resource sharing.

### Phân biệt semantics trước khi so sánh

- FFT ở đây dùng fixed-point: biểu diễn số gần đúng, có scale và rounding.
- NTT dùng số nguyên modulo q: kết quả phải chính xác theo representation đã chọn.
- Canonical nghĩa là residue trong [0,q); Montgomery là cách encode giá trị.
  Một giá trị Montgomery vẫn có thể được lưu canonical về mặt khoảng số.
- Twiddle FFT có magnitude gần 1; toán hạng pointwise bất kỳ không có bound đó.
- “Hằng số” phải phân biệt: cố định lúc synthesis; chọn từ profile; hoặc thay đổi
  theo root ở mỗi phép tính. Chi phí constant multiplication khác nhau giữa ba trường hợp.

## 3. Phân rã FFT/IFFT

### 3.1 Nhân phức 4M

Với x=a+j*b, w=c+j*d:

~~~text
p0 = a*c
p1 = b*d
p2 = a*d
p3 = b*c
Re = p0-p1
Im = p2+p3
~~~

Chi phí đại số: 4 real multiply + 2 real add/sub.
Với fixed-point data có Fd bit lẻ, hệ số có Ft bit lẻ, product có Fd+Ft bit lẻ.
Cần gom đúng trước khi đưa về format output.

Các lựa chọn khác nhau cần được đối chiếu:

| Phương án | Cấu trúc | Đánh đổi |
|---|---|---|
| Tạo từng real product | Bốn product rồi cộng/trừ | Dễ tái dùng cho modmul/pointwise |
| Gom trực tiếp Re/Im | Tích limb đi thẳng vào cây có dấu | Có thể giảm trung gian, nhưng gắn với mapping nhân phức |
| Carry-save rồi final carry-propagate | Gom nhiều hạng chưa truyền carry đầy đủ | Có thể rút critical path, thêm register/routing và logic tại tap |

Rounding sau từng real product và rounding sau khi gom Re/Im là hai hợp đồng khác nhau.
Khi so phần cứng, phải giữ cùng hợp đồng hoặc định lượng khác biệt sai số.
Trong phạm vi PQC cơ sở đang yêu cầu, phương án khác hợp đồng bị loại khỏi lựa chọn
triển khai; đo sai số chỉ là phân tích riêng, không phải quyền thay thế reference.

### 3.2 Nhân phức 3M: cơ hội có thật, width cũng có thật

Một công thức tổng quát:

~~~text
p0 = a*c
p1 = b*d
p2 = (a+b)*(c+d)
Re = p0-p1
Im = p2-p0-p1
~~~

Hai tổng đầu vào có thể cần thêm một bit. Nếu cứ tăng width rồi phân limb 32 bit,
số tile có thể không giảm như kỳ vọng.

Với twiddle cố định cho từng phép tính, có công thức thuận lợi hơn:

~~~text
P = (a+b)*c
Q = b*(c+d)
R = a*(d-c)
Re = P-Q
Im = P+R
~~~

c+d và d-c có thể chuẩn bị trước từ **c,d đã lượng tử hóa**, không lượng tử hóa
một lần độc lập làm đổi identity. Kiểm tra trực tiếp ROM để bảo đảm chúng fit width.
Twiddle gần unit circle có đủ headroom trong Q2.F, nhưng đây vẫn là điều kiện phải kiểm tra.

Hệ quả: lưu ba hệ số thay vì hai, hoặc thêm hai bộ cộng/trừ chuẩn bị hệ số tại core.
Product P phải cấp được cho cả Re lẫn Im.

### 3.3 Hiệu chỉnh overflow để 3M không tăng width multiplier

Đặt:

~~~text
s = a+b
s0 = wrap_signed_W(s)
e = (s-s0)/2^W, với e thuộc {-1,0,1}

P = s0*c + e*(c << W)
~~~

Hạng e*c chỉ là chọn 0, +c hoặc -c, không cần general multiplier.
Đẳng thức là chính xác trên số nguyên, không phải bỏ bit.

| W data = W twiddle | 4M | 3M tổng quát, tăng cả hai width | 3M twiddle, chỉ tăng data sum | 3M hiệu chỉnh overflow |
|---|---:|---:|---:|---:|
| 32 | 4 | 6 | 4 | 3 |
| 64 | 16 | 17 | 14 | 12 |
| 128 | 64 | 57 | 52 | 48 |

Đơn vị: số product slot 32×32 theo schoolbook, chưa tính bộ cộng/ROM/routing.
Đây là lý do không thể chỉ nói “3M tiết kiệm 25%” rồi giữ nguyên cấu trúc còn lại.

**64 xuống 48 không có nghĩa giảm precision 128 bit.** Ba real product vẫn xử lý
các operand ở đầy đủ width; hạng hiệu chỉnh giữ phần tràn của pre-add chính xác.
Identity này bảo toàn kết quả nguyên chưa rounding. Nó chỉ cho bit-exact với 4M
khi các bước rounding/scaling sau đó cũng theo cùng hợp đồng.

Nếu reference làm tròn từng real product trước cộng/trừ, identity chưa rounding
không đủ chứng minh 3M khớp reference. Model hiện tại so 3M và 4M với cùng rounding
sau khi gom thành phần phức, chưa chứng minh thay thế được mọi reference FN-DSA.
3M giữ trạng thái ứng viên; khi không đạt tương đương, dùng đường khớp reference.

Ứng viên hiệu chỉnh có thể giảm số product, nhưng thêm:

- Pre-add a+b và logic lấy e.
- Hạng cộng hiệu chỉnh có trọng số cao.
- Fan-out/buffer cho P được dùng hai lần.
- Đường hệ số c, c+d, d-c.

Nếu xuất ba hệ số mỗi butterfly, nhu cầu twiddle hữu ích tăng 50% so với hai hệ số.
Có thể đánh đổi ROM/băng thông đó bằng arithmetic tiền xử lý.

### 3.4 CT và GS: cùng các họ primitive, thứ tự khác nhau

~~~text
CT:
  t = complex_mul(B,w)
  U = A+t
  V = A-t

GS:
  U = A+B
  D = A-B
  V = complex_mul(D,w)
~~~

Với 4M, mỗi butterfly cần 4 real multiply và 6 real add/sub về mặt đại số.
Trong GS, D có thể rộng W+1 bit trước nhân.

| W | Product slots CT/4M | GS/4M nếu mở rộng D lên W+1 trực tiếp |
|---|---:|---:|
| 32 | 4 | 8 |
| 64 | 16 | 24 |
| 128 | 64 | 80 |

Các cách xử lý cần so: giữ headroom đã chứng minh; scale trước nhân; hiệu chỉnh
carry/overflow; hoặc chấp nhận multiplier rộng. Scale trước nhân có thể đổi sai số.

Điều này mở lại lựa chọn CT/GS từ nhu cầu số học, thay vì giữ CT chỉ vì sơ đồ v0.1 thuận tiện.
Thay đổi vị trí một ngân hàng cộng/trừ có thể cần mux, feedback hoặc thêm buffer;
hai kernel không phải cùng một datapath chỉ đổi tên lệnh.

### 3.5 Pointwise, liên hợp, bình phương và split/merge

| Kernel | Đại số cơ sở | Lưu ý khi tái dùng |
|---|---|---|
| Pointwise complex | Nhân phức với cả hai operand là data | Ft có thể bằng Fd; bound twiddle không áp dụng |
| Multiply adjoint | x*conj(y) | Đổi dấu đóng góp; giữ phép nhân |
| Squared magnitude | a^2+b^2 | Hai square; không cần tính phần ảo bằng zero-product |
| Negate/conjugate | Đổi dấu real/imag thích hợp | Signed minimum cần guard hoặc bound |
| MERGE | A ± w*B | Gần kernel CT |
| SPLIT | (A+B)/2, (A-B)*conj(w)/2 khi w là unit root | Gần GS, có half và khác vị trí rounding |

Falcon reference có các họ kernel conjugate, squared magnitude, split và merge;
layout Fourier riêng phải theo adapter. [S1]
Bảng trên phân tích nhu cầu arithmetic, chưa thêm mọi kernel vào RTL cơ sở.

FFT/IFFT normalization là chia cho lũy thừa hai ở mức số thực.
Trong fixed-point, phân bố phép chia theo stage và chia ở cuối có thể khác bit vì rounding.
Không được đồng nhất việc chúng tương đương đại số với tương đương implementation.

### 3.6 Những tối ưu riêng FFT đáng so sánh

1. 4M đối chiếu 3M có hiệu chỉnh, cùng numeric contract và kết quả bit-exact.
2. Cây carry-propagate đối chiếu carry-save và vị trí final carry-propagate.
3. Giữ precision và constants twiddle của reference trong baseline. Twiddle hẹp
   làm thay đổi constants là nhánh ngoài baseline, không tự bật theo kết quả PPA.
4. Fused hardware chỉ được đưa vào baseline khi bảo toàn các kết quả rounding
   quy định. Fused rounding cho kết quả khác thuộc nhánh ngoài baseline.
5. Root 1/-1/+j/-j bằng bypass/sign/swap, chỉ tại vị trí root thực sự tương ứng.
6. Square chuyên biệt khi workload có nhiều norm/self-adjoint arithmetic.

Số lượng root đặc biệt và tỷ lệ kernel phải lấy từ trace, không tự gán phần trăm tiết kiệm.

## 4. Phân rã NTT/INTT

Mọi tối ưu trong mục này phải exact modulo q. Không dùng approximate multiplier
hoặc quotient gần đúng nếu chưa có bound correction bảo đảm residue cuối chính xác
cho toàn bộ miền đầu vào. Giảm bit trung gian chỉ hợp lệ sau chứng minh các bit bị
bỏ không ảnh hưởng output; không dựa riêng vào tỷ lệ test qua.

### 4.1 Butterfly và modular add/sub

~~~text
CT:
  t = modmul(B,w)
  U = (A+t) mod q
  V = (A-t) mod q

GS:
  U = (A+B) mod q
  D = (A-B) mod q
  V = modmul(D,w)
~~~

Với canonical operands, trước correction:

~~~text
0 <= A+t < 2q
-q < A-t < q
~~~

Vì vậy, mỗi nhánh chỉ cần một correction thích hợp.
Ở q gần 2^32, tổng cần 33 bit dù storage lane là 32 bit.
Các modulus PQC nhỏ có headroom trong lane 16/32 nhưng phải nêu bound riêng.

Modular add/sub cần tổng/hiệu, thông tin carry/borrow hoặc so sánh, cùng correction.
Correction có thể là một phép cộng/trừ thật, không phải mux miễn phí.

Nếu tái dùng một ngân hàng cộng/trừ qua hai lượt cho cả butterfly và correction,
arithmetic issue demand tăng. Muốn giữ throughput cần thêm correction lane hoặc
fused modular add/sub. Đây là bài toán định cỡ core, chưa cần scheduler transform.

### 4.2 Montgomery tổng quát

Đặt R=2^r, q lẻ, q<R, T=A*B<qR.

~~~text
Phiên bản cộng:
  c = -q^(-1) mod R
  m = low_r(T*c)
  u = (T+m*q)/R
  out = u-q nếu u>=q, ngược lại u
  bound: 0 <= u < 2q

Phiên bản trừ:
  c = q^(-1) mod R
  m = low_r(T*c)
  u = (T-m*q)/R
  out = u+q nếu u<0, ngược lại u
  bound: -q < u < q
~~~

Chia cho R ở đây là lấy phần cao của một số chia hết cho R, không có rounding.
Kết quả bằng A*B*R^(-1) mod q.

Với q và c tùy chọn tổng quát, có ba tích:
A*B, low_r(low_r(T)*c), m*q.
Một tích chỉ cần phần thấp; tích T±m*q cần giữ carry/sign trước khi dịch.

Montgomery không bắt buộc luôn dùng R=2^32:
q=3329/12289 có thể dùng r=16; q=8380417 và prime 30–32 bit có thể dùng r=32.
Reference Falcon là một nguồn đối chiếu cho arithmetic q=12289 và Montgomery word 16 bit. [S2]

### 4.3 Montgomery chuyên biệt PQC: một general product có thể là đủ

| q | r | Chọn phiên bản | Hằng số c |
|---|---:|---|---|
| 3329 | 16 | Cộng | 3327 = 2^12−2^10+2^8−1 |
| 12289 | 16 | Cộng | 12287 = 2^14−2^12−1 |
| 8380417 | 32 | Trừ | 58728449 = 2^26−2^23+2^13+1 |

Các modulus cũng có dạng thưa:

~~~text
3329    = 2^12 - 2^10 + 2^8 + 1
12289   = 2^14 - 2^12 + 1
8380417 = 2^23 - 2^13 + 1
~~~

Do đó, T*c và m*q có thể dùng shift-add/sub thay vì general multiplier.
Khi tính m chỉ cần giữ modulo R, các bit cao không ảnh hưởng phần thấp.

**Điều giảm được là số general multiplication, không phải toàn bộ chi phí reduction.**
Vẫn cần mạng cộng/dịch, register, correction và representation đúng.

So ba ứng viên cho mỗi q:

| Ứng viên | General product dùng cho một modmul | Phần riêng |
|---|---:|---|
| Montgomery tổng quát trên mảng | 3 product slot nếu word <=32 | Cộng/dịch/correction |
| Montgomery với constant networks | 1 | Hai mạng nhân hằng số và cộng/dịch/correction |
| Chỉ chuyên biệt một trong hai hằng số | 2 | Một mạng nhân hằng số, phần còn lại dùng tile |

Cách thứ hai có thể tiết kiệm tài nguyên mạnh, kể cả khi để một số tile rảnh.
Chưa kết luận PPA trước synthesis, vì network hằng số có nhiều đường carry và replication.

Một prime RNS đã chọn cũng có thể thưa, ví dụ 4293918721=2^32−2^20+1,
với q^(-1) mod 2^32 = 1+2^20. Tuy nhiên, đây là tối ưu theo profile cụ thể;
không chuyển kết quả đó thành lời hứa cho mọi prime runtime.

### 4.4 Barrett: canonical, nhưng chi phí thay đổi theo q

Cho T<2^k, mu=floor(2^k/q):

~~~text
qhat = floor(T*mu/2^k)
r = T-qhat*q
out = r-q nếu r>=q, ngược lại r
~~~

Vì 0 <= T/q-T*mu/2^k < 1, qhat bằng floor(T/q) hoặc nhỏ hơn một.
Do đó 0<=r<2q, đủ một correction.
Với canonical A,B, chọn k=2*bit_length(q) đủ bao phủ T=A*B.

| q | T bits tối đa | mu | mu bits | T*mu: product slot L32 theo phân rã đầy đủ |
|---|---:|---:|---:|---:|
| 3329 | 24 | 5039 | 13 | 1 |
| 12289 | 28 | 21843 | 15 | 1 |
| 8380417 | 46 | 8396807 | 24 | 2 |
| 2013265921 | 62 | 2290649223 | 32 | 2 |
| 4293918721 | 64 | 4296016127 | 33 | 4 |

Chưa tính A*B và qhat*q. qhat*q có thể dùng mạng hằng số nếu q cố định/thưa.
T*mu có thể được tối ưu theo các bit cần lấy, nhưng không được bỏ carry tùy ý.

Ứng viên hai tile cho NTT12289 đã nêu ở vòng trước là:
một product A*B, một product T*mu, cộng/dịch hằng số q.
Nó phải được so với Montgomery constant-networks chỉ cần một general product,
không được mặc định thắng vì sử dụng đủ 32 tile.

### 4.5 Shoup: tối ưu khi một operand là twiddle đã chuẩn bị

Đặt R=2^r>q, 0<=x,w<q, w_pre=floor(w*R/q):

~~~text
qhat = floor(x*w_pre/R)
r = x*w-qhat*q
out = r-q nếu r>=q, ngược lại r
~~~

Có 0<=r<2q. Công thức này giữ r đầy đủ; nếu q gần R, r có thể cần r+1 bit.
Các biến thể chỉ giữ r bit cần thêm điều kiện hoặc cách phục hồi carry.

Shoup cần product x*w và high product x*w_pre; qhat*q vẫn phải xử lý.
Đổi lại tránh representation Montgomery trong công thức trên.
Twiddle phải mang thêm w_pre, làm tăng ROM và băng thông nếu không có reuse.

Không áp dụng miễn phí cho pointwise có hai operand thay đổi: cần tính/lưu
precompute của một operand và tính chi phí đó.

### 4.6 Representation và chuyển miền là một phần của phép toán

| Chính sách | Butterfly | Pointwise và normalization |
|---|---|---|
| Data canonical, root lưu w*R | Mont(B,w*R)=B*w canonical | Hai operand canonical không trực tiếp dùng Mont(A,B) |
| Data và root đều Montgomery | Mont(BR,wR)=B*w*R | Pointwise giữ miền; cần vào/ra miền |
| Barrett hoặc Shoup canonical | Giữ canonical theo công thức | Không có hệ số R, nhưng vẫn có precompute/correction |

Ví dụ nếu hai operand canonical:

~~~text
B_R = Mont(B, R^2 mod q)
A*B mod q = Mont(A, B_R)
~~~

Nếu toàn bộ data đang ở miền Montgomery, pointwise chỉ cần một Mont.
Phải cộng conversion vào chi phí workload, không chỉ báo chi phí butterfly.
INTT normalization có thể kết hợp conversion cuối khi constants và representation khớp.

### 4.7 Normalization, lazy reduction và BASEMUL

Với q lẻ và x canonical:

~~~text
half_q(x) = (x + (x&1)*q) >> 1
~~~

Đây là chia hai chính xác trong trường modulo, không phải fixed-point rounding.
Áp dụng mỗi stage inverse cho các output thích hợp có thể thay normalization cuối.
Ví dụ GS có thể dùng half_q cho nhánh tổng và đưa inv2 vào twiddle nhánh nhân.
Các hằng số mới và mọi bound phải theo đúng representation.

Lazy reduction là ứng viên tối ưu:
nếu A<alpha*q, B<beta*q, cần chứng minh T<qR trước khi dùng bound Montgomery trên.
Điều kiện đủ là alpha*beta*q<R.
Đổi profile có thể làm điều kiện mất hiệu lực; không dùng một bound chung tùy tiện.

Với BASEMUL q=3329:

~~~text
p0 = a0*b0
p1 = a1*b1
p2 = (a0+a1)*(b0+b1)
c0 = p0 + zeta*p1
c1 = p2-p0-p1                         (tất cả modulo q)
~~~

So với bốn tích chéo cộng một tích zeta, phương án này dùng ba tích chính và một
tích zeta: 4 modular product thay vì 5, chưa tính conversion.
Có thể canonicalize tổng trước nhân; nếu giữ lazy phải kiểm tra bound mới.
Không dùng lazy input T>=2^k với Barrett rồi vẫn suy ra một correction từ chứng minh ở mục 4.4.

## 5. Full, low và high product phải được tối ưu riêng

Với L limb:

| Nhu cầu | Các tích limb cần theo phương án cơ sở |
|---|---|
| Full product | L^2 |
| Low W bit | Chỉ i+j<L, có L*(L+1)/2 tích |
| High W bit | Không thể chỉ lấy các tích có trọng số cao, vì carry từ vùng thấp |
| Rounded high part FFT | Cần cả retained bits và thông tin guard/round/sticky hoặc thông tin tương đương |
| Nhân hằng số thưa | Có thể dùng cộng/trừ các bản dịch; cost phụ thuộc width và vị trí bit |

Với B=2^32, a=a0+B*a1, b=b0+B*b1:

~~~text
high64(a*b) =
  a1*b1 + floor((a0*b1 + a1*b0 + floor(a0*b0/B))/B)
~~~

Bỏ floor(a0*b0/B) có thể sai một đơn vị ở phần cao.
High product gần đúng chỉ được dùng khi đã đưa sai số đó vào bound và số correction.

Square có đối xứng: các tích i<j xuất hiện hai lần, đường tính có thể dùng ít
multiplier hơn generic product. Cần workload có đủ square để bù thêm mode và routing.

## 6. Ma trận chia sẻ thật sự

Chỉ xét sharing trên những kernel đã qua điều kiện chính xác. Không ép FFT dùng
floor của NTT, hoặc ép NTT dùng rounding của FFT, để làm hai datapath giống nhau.
Lựa chọn giữa full/low/high product phải giữ toàn bộ thông tin cần cho đúng kernel.

| Primitive | FFT cần gì? | NTT cần gì? | Đánh giá chia sẻ |
|---|---|---|---|
| General integer multiply | Signed/mixed-sign, nhiều limb | Unsigned, product và tích phụ | Rất mạnh, nếu phù hợp width |
| Low product | Ít hơn ở kernel cơ sở | Montgomery m | Có ích; không bắt mọi mode tính full nếu phần cứng tách được |
| High product | Fixed-point extraction | Barrett/Shoup quotient | Có tiềm năng; floor khác rounding |
| Dual-output add/sub | Butterfly và complex recombination | Butterfly, một số reduction | Rất đáng khảo sát; khác guard và correction |
| Carry-save/weighted accumulation | Nhiều partial products | T±m*q hoặc constant networks | Có điều kiện; FFT fixed-shift tree không tự dùng được cho mọi reduction |
| Constant shift | Limb alignment, scale | Nhân q/c, chia R, lấy bit | Có thể chia sẻ wiring/mux; barrel shifter chưa chắc cần |
| Conditional add/sub | RNE increment, negate | Correction ±q, half_q | Có phần chung, nhưng tăng variable-adder cost có thể không lợi |
| Register/buffer | Operand rộng, nhiều component | Nhiều residue, giữ T/m/q | Có tiềm năng qua packing; lifetime dữ liệu khác nhau |
| Round/overflow logic | Bắt buộc theo numeric contract | Không được dùng để xấp xỉ residue | Riêng về semantics |
| q/profile constants | Không có vai trò tương ứng | Bắt buộc | Riêng |

Sự giống nhau ở primitive không tự bảo đảm resource sharing hiệu quả.
Phải tính mux đầu vào, fan-out, retiming, register giữ dữ liệu và throughput của từng mode.

### 6.1 Ngân hàng cộng/trừ chung: khớp payload, chưa khớp mọi bit

Với ngân sách data 512 bit/chu kỳ đang dùng:

| Mode | Payload A cho các butterfly hoạt động | Payload T tương ứng |
|---|---:|---:|
| FFT32, 4 butterfly | 8 thành phần * 32 = 256 bit | 256 bit |
| FFT64, 2 butterfly | 4 * 64 = 256 bit | 256 bit |
| FFT128, 1 butterfly khi đủ component | 2 * 128 = 256 bit | 256 bit |
| NTT lane16, 16 butterfly | 16 * 16 = 256 bit | 256 bit |
| NTT lane32, 8 butterfly | 8 * 32 = 256 bit | 256 bit |

Điều này gợi ý một ngân hàng tạo A+T và A-T theo lane 16/32/64/128.
Tuy nhiên, đây là payload storage. FFT product sau rounding có thể cần guard W+2;
NTT q gần 2^32 cần carry 33 bit. Phải thiết kế phần mở rộng và biên lane riêng.
Không thể lấy một adder 256 bit rồi chỉ thêm bit chặn carry là xong.

### 6.2 Cây gom và correction: mức chia sẻ phải được chứng minh

Ở CT, ALU butterfly ở sau multiplication; GS cần ALU trước multiplication.
Muốn dùng chung một ALU phải định nghĩa đường đi và buffer tương ứng.

Một node cộng FFT có thể tính T±m*q nếu cấp được đúng hai operand.
Nhưng các shift cố định của cây hiện tại và nhu cầu cộng nhiều lane NTT không khớp
tự động. So chi phí reuse có mux với một correction/add network nhỏ đặt riêng.

Một khối được chia sẻ qua hai lượt không có cùng throughput với hai khối song song.
Số ALU/corrector/rounder phải đếm theo primitive issue demand của mỗi kernel.

## 7. Các giới hạn làm đảo chiều lựa chọn tối ưu

1. **Bandwidth:** 3M có thể giảm product nhưng tăng hệ số twiddle; Shoup cũng tăng dữ liệu root.
2. **Numeric contract:** GS pre-scaling, fused rounding và twiddle hẹp có thể đổi kết quả FFT.
3. **Modulus:** một reducer hằng số có lợi với PQC nhỏ chưa chắc tốt cho prime runtime.
4. **Workload:** core chỉ verify khác core có signing/keygen; tỷ lệ FFT/NTT quyết định mức lợi ích.
5. **Timing:** reuse một adder có mux dài có thể giảm Fmax của cả hai mode.
6. **Limb granularity:** hiệu chỉnh bit tăng thêm có thể tốt hơn tăng số limb; leaf nhỏ cũng tăng routing/gom.
7. **Transform convention:** negacyclic cần đúng twist/root; NTT q=3329, N=256 không đầy đủ.

Root FFT ±j là phép swap/sign trên hai thành phần. NTT scalar không có phép
swap real/imag tương ứng; không chuyển tối ưu đó sang NTT chỉ vì root có bậc 4.

Với data pointwise, bound W+2 từ twiddle unit không đủ nói chung.
Model có ví dụ FFT32 với hai operand lớn: phần ảo sau product scaling vượt signed 34 bit.
Phải giữ product guard thích hợp hoặc đặt bound/scaling riêng.

## 8. Thí nghiệm cần làm trước khi chọn kiến trúc tiếp theo

Mỗi thí nghiệm có hai bước: kiểm chứng tương đương trước; chỉ so PPA các phương án
đã đạt. Một phương án có ít product slot hơn nhưng khác output reference không
được xếp là phương án tối ưu hợp lệ cho baseline PQC.

| Thí nghiệm | Những phương án phải so cùng điều kiện |
|---|---|
| E1 — Nhân phức | 4M; 3M tăng width; 3M hiệu chỉnh overflow |
| E2 — FFT accumulation | Tạo real product; cây Re/Im trực tiếp; carry-save |
| E3 — Reducer từng q | Montgomery tổng quát; constant networks; Barrett; Shoup cho twiddle |
| E4 — Cộng/trừ | ALU FFT/NTT riêng; ALU chung theo lane; correction riêng hoặc dùng lại ALU |
| E5 — Granularity | L32; leaf16 có grouping; hiệu chỉnh extra bit thay tăng limb |
| E6 — Tập kernel | CT, GS, pointwise, normalization; thêm BASEMUL và split/merge theo workload |
| E7 — Rounding/twiddle | Giữ constants, format và kết quả reference; các semantics làm đổi output nằm ngoài baseline |

Các mức tích hợp:

~~~text
B0: FFT và NTT tối ưu riêng, cùng tập chức năng
B1: chia sẻ multiplier
B2: B1 + chia sẻ butterfly add/sub
B3: B2 + chia sẻ một phần accumulate/reduction
~~~

Mỗi mức phải báo: arithmetic coverage, resource sau mapping, Fmax, register/buffer,
latency và throughput từng kernel, data/twiddle traffic, numeric error hoặc exactness.
So cùng primitive budget và so cùng tổng area là hai phép so khác nhau.

Đích tối ưu là frontier area–time–energy dưới yêu cầu workload.
Tỷ lệ tile bận hoặc tỷ lệ mạch chia sẻ chỉ là chỉ số giải thích, không phải mục tiêu độc lập.
Không gọi B3 tốt hơn B2 chỉ vì dùng chung thêm một khối.

## 9. Tác động lên ARC v0.1

| Lựa chọn cũ | Đánh giá lại |
|---|---|
| L32, K=32 | Giữ làm baseline; chưa dùng nó để loại các decomposition khác |
| Cây trực tiếp Re/Im với taps | Hợp lệ cho 4M hiện có; phải so với 3M và product fabric tổng quát |
| NTT chia 3 nhóm multiplier | Đúng cho Montgomery tổng quát; PQC constant networks có thể dùng ít general product hơn |
| Hai đường butterfly add/sub riêng | Mở thí nghiệm ngân hàng ALU chung có guard/correction đầy đủ |
| Chỉ CT cho cả hai hướng | Mở lại CT/GS dựa trên width, headroom và tập kernel Falcon |
| Product RNE trước butterfly | Giữ một numeric baseline; so fused variant riêng |
| Chưa có operation/bypass | Bổ sung requirement cho raw product, pointwise, normalize và BASEMUL |

Kết luận vòng này là **các ứng viên để so**, không phải một ARC v0.2 đã chốt.
Ưu tiên E1/E3/E4: chúng quyết định phần nhân, phần cộng và phần riêng của hai miền.

## 10. Model và bằng chứng kiểm tra

[Model mới](../model/arithmetic_reassessment.py) chỉ dùng Python standard library.
Chạy:

~~~powershell
python model/arithmetic_reassessment.py
~~~

Kết quả:
[bảng kiểm tra](../study/results/arithmetic_reassessment.md),
[JSON](../study/results/arithmetic_reassessment.json).

| Kiểm tra | Số trường hợp |
|---|---:|
| Nhân phức 3M hiệu chỉnh so với 4M, gồm boundary/random | 6715 |
| Cặp operand kiểm tra Montgomery/Barrett/Shoup/modular add/sub | 25125 |
| Modular half, gồm toàn bộ residue của hai q nhỏ | 40743 |
| Montgomery với lazy inputs thỏa bound | 3000 |
| Full/low product với limb16/32 | 3000 |
| NTT nhỏ so DFT và inverse CT/GS | 100 |
| Negacyclic convolution qua twist/NTT so schoolbook | 100 |
| BASEMUL 3 tích chính so công thức trực tiếp | 5000 |
| Split/merge exact rational | 100 |

Các transform nhỏ dùng N=8/16; không phải KAT FN-DSA hoặc phép thử đầy đủ ML-KEM N=256.
NTT butterfly trong phép thử dùng canonical data và Montgomery roots; pointwise trong
convolution dùng phép modulo chính xác làm oracle, chưa đo conversion/hardware cost.
Split/merge rational chỉ kiểm identity, chưa kiểm sai số fixed-point.

Bốn phản ví dụ được lưu trong JSON:

- High product sai khi bỏ carry từ low product.
- Shoup q=251, R=256, x=9, w=140 cho remainder=256: mất bit cao trả kết quả sai.
- Round product rồi cộng khác fused rounding ở trường hợp tie.
- Guard theo unit-twiddle không dùng nguyên cho pointwise operand rộng.

Proof về correction bound và identity mới là cơ sở cho miền tổng quát;
các test boundary/random hỗ trợ bắt lỗi hiện thực model. Chưa có synthesis/PPA
cho các ứng viên mới, chưa có error bound cho toàn bộ signing.

## 11. Nguồn và phân biệt đóng góp

- **[S1]** [Falcon reference fft.c](https://falcon-sign.info/impl/fft.c.html):
  đối chiếu các họ kernel FFT/iFFT, conjugate, self-adjoint, split/merge.
- **[S2]** [Falcon reference vrfy.c](https://falcon-sign.info/impl/vrfy.c.html):
  arithmetic modulo 12289, Montgomery và đường NTT/iNTT.
- **[S3]** [Unified FFT/NTT, ICASSP 2025](https://arxiv.org/html/2504.11124v1):
  tiền lệ chia sẻ arithmetic và reducer đặc thù.
- **[S4]** [Maestro, Section V](https://arxiv.org/html/2503.04581v1):
  đối chiếu butterfly nhiều precision và fused arithmetic, ở miền floating-point.
- **[S5]** [Aloha-HE, Section III](https://flokrieger.github.io/papers/date24_aloha.pdf):
  đối chiếu chia sẻ integer multiplication giữa modular ring và floating-point.
- **[S6]** [OpenNTT](https://flokrieger.github.io/papers/tcad25_opennttext.pdf):
  parameter flexibility, twiddle và ràng buộc thiết kế.
- **[S7]** [BitFusion](https://arxiv.org/html/1712.01507v2):
  tiền lệ decomposition và fusion.

Nguồn giúp xác định kernel và prior art. Công thức và bảng ứng viên trong tài liệu
là phân tích lại cho bài toán dự án, không phải chép kết quả PPA của các paper.
Các identity 3M, Montgomery, Barrett và Shoup đều có tiền lệ; chưa tuyên bố chúng
là phát minh mới. Novelty phải đánh giá ở cơ chế hiện thực và lợi ích đã đo.
