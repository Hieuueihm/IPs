# FFT và NTT trong PQC — phân tích từ ứng dụng đến kiến trúc

Ngày: 26/10/2026. Phạm vi: Falcon làm ứng dụng chính cho hướng FN-DSA;
ML-KEM và ML-DSA làm đối chiếu NTT. Các khẳng định Falcon dưới đây dựa trên
Falcon v1.2/reference và fixed-point artifact đã pin trong repo; không suy ra
chúng tự động là yêu cầu của mọi phiên bản FN-DSA.

Đây là phân tích ứng dụng, không sửa contract [FT-SPEC-1.0](../spec/FlexTransform/1.0/README.md).
Phân biệt dữ kiện từ nguồn, suy ra bằng toán học và quyết định thiết kế của repo.

## 1. Điểm xuất phát: số học đa thức, không phải phổ tín hiệu

Với các hệ lattice đang xét, đối tượng là đa thức trong
`Z[X]/(X^N+1)` hoặc `Z_q[X]/(X^N+1)`. Quan hệ `X^N=-1` tạo phép nhân
negacyclic: hạng có bậc vượt N−1 quay về với dấu trừ. Transform giúp đưa phép
nhân đa thức thành những phép nhỏ độc lập trong miền biến đổi.

NTT làm việc trên trường hữu hạn, còn FFT đánh giá đa thức ở nghiệm phức.
Hai miền có cấu trúc butterfly tương tự nhưng semantics số học khác nhau.
Các vành ứng dụng được định nghĩa trong [Falcon §3.5](https://falcon-sign.info/falcon.pdf),
[ML-KEM §2.4/4.3](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf) và
[ML-DSA §7.5](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf).

Ví dụ tự tính, N4/q17: `a=1+2X`, `b=3+X^3`.
Tích modulo `X^4+1` là `1+6X+X^3`, vì `2X^4=-2`.
Nghiệm của `X^4+1` trong Z17 là [2,8,15,9]. Đánh giá a cho [5,0,14,2],
b cho [11,5,12,1]. Nhân từng điểm modulo17 cho [4,0,15,2]; inverse transform
trả [1,6,0,1]. Không có rounding trong chuỗi modular này. Đây là ví dụ nhỏ
để giải thích cơ chế, không là tham số của một scheme PQC.

Không phải mọi PQC đều cần FFT/NTT. Phân tích này nhắm nhóm lattice có các
kernel trên; không suy rộng một accelerator transform thành accelerator mọi PQC.

## 2. Vì sao riêng Falcon có cả hai miền?

### 2.1 FFT: hỗ trợ hình học và lấy mẫu

Falcon dùng fast Fourier sampling. FFT representation hỗ trợ các phép toán
trên basis/Gram matrix và mục tiêu lấy mẫu. Đa thức thực có đối xứng liên hợp,
nên N hệ số thực có thể lưu bằng N/2 giá trị phức. N512 vì thế lưu 256 complex,
N1024 lưu 512 complex. N trong tên đa thức không phải số complex được lưu.
[Falcon §3.4–3.6, §4.2](https://falcon-sign.info/falcon.pdf).

Đi vào code, sampler thực hiện chuỗi split → đệ quy → merge → cập nhật bằng
nhân/cộng rồi xử lý nhánh còn lại. SPLIT/MERGE là biến đổi đại số trên đa thức
đã ở miền FFT, không đơn thuần chia đôi/ghép hai đoạn RAM. Một nhánh dùng kết
quả nhánh kia, nên không thể mặc định mọi nút cùng độ sâu chạy độc lập.
[Reference sign.c](https://falcon-sign.info/impl/sign.c.html).

Các kernel liên quan gồm FFT/IFFT, complex multiplication, cộng/trừ, conjugate,
split/merge; dựng tree còn có LDL và phép chia liên quan. Có butterfly FFT
không có nghĩa đã tăng tốc toàn bộ sampler.
[Reference fft.c](https://falcon-sign.info/impl/fft.c.html).

### 2.2 NTT: xử lý quan hệ modulo chính xác

Verification có tích `s2*h mod(X^N+1,q)` để kiểm quan hệ chữ ký. Với Falcon,
q=12289, N512/1024. Reference chuyển s2 sang NTT, nhân với public key đã
được chuẩn bị ở miền NTT/Montgomery, inverse rồi trừ challenge và kiểm norm.
Public-key generation cũng dùng NTT cùng phép chia theo từng tọa độ để tính
h=g/f. Có NTT/INTT/MODMUL chưa có nghĩa đã có phép nghịch đảo modular.
[Reference vrfy.c](https://falcon-sign.info/impl/vrfy.c.html).

FFT và NTT vì thế bổ sung nhau trong Falcon. NTT q12289 không cung cấp trực
tiếp thứ tự/độ lớn trên số thực và các đại lượng lấy mẫu mà FFT path đang dùng.
Thay FFT bằng NTT cần thiết kế lại biểu diễn/tính toán và phân tích tính đúng,
không phải đổi twiddle trong cùng phép toán.

### 2.3 NTT cho NTRU keygen là workload khác NTT q12289

Reference NTRU solver còn dùng các prime gần 2^31, số nguyên nhiều limb,
NTT/RNS và CRT để xử lý các hệ số lớn; Babai reduction có phần tính gần đúng.
Không thể suy từ q ứng dụng=12289 rằng mọi NTT trong keygen đều là 14 bit.
[Reference keygen.c](https://falcon-sign.info/impl/keygen.c.html).

Hệ quả kiến trúc: hỗ trợ q12289 và q3329 trên lane16 chưa bao phủ các NTT
31 bit/CRT của NTRU solver. Nếu xét NTT nhỏ ở các độ sâu keygen, phải ghi
cả N, prime width, số prime và representation; chỉ histogram theo N là thiếu.

## 3. NTT thay đổi theo scheme ở những gì?

| Workload | N | q / coefficient bits tối thiểu | Kiểu transform/điểm kết thúc |
|---|---:|---|---|
| Falcon modular arithmetic | 512/1024 | 12289 / 14 | Full NTT; nhân từng tọa độ scalar |
| ML-KEM | 256 | 3329 / 12 | Incomplete 7 tầng; 128 tọa độ là đa thức bậc1 |
| ML-DSA | 256 | 8380417 / 23 | Full 8 tầng; nhân từng tọa độ scalar |
| Falcon reference NTRU solver | Thay theo recursion | Nhiều prime gần2^31 | NTT theo prime và tái dựng CRT |

Thông số ML-KEM: [FIPS203 §4.3](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf).
Thông số ML-DSA: [FIPS204 §6.1/7.5](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf).
Workload keygen: [keygen.c](https://falcon-sign.info/impl/keygen.c.html).

Suy ra từ đại số: với q prime, full negacyclic NTT trong trường cơ sở cần
nghiệm nguyên thủy bậc2N; điều kiện tồn tại là `2N | q−1`.
q3329 có 256 chia hết q−1 nhưng 512 không chia hết q−1. Tại N256, polynomial
không tách hoàn toàn thành nhân tử bậc1 trong trường đó; đầu ra vẫn có cặp hệ số.

MultiplyNTTs của ML-KEM nhân hai cặp `(a0,a1)`, `(b0,b1)` modulo `X²−gamma`:

```text
c0 = a0*b0 + gamma*a1*b1  mod q
c1 = a0*b1 + a1*b0        mod q
```

Do đó 256 phép scalar MODMUL không thay được BASEMUL. INTT chuẩn hóa bằng
128^-1, theo bảy tầng, thay vì dùng 256^-1 máy móc.
[FIPS203 Algorithms9–12](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf).

Montgomery/Barrett/Shoup là lựa chọn hiện thực modular arithmetic, không phải
những định nghĩa NTT khác nhau. Nếu dùng Montgomery, phải theo dõi x hay xR,
root thường hay root×R, hệ số inverse và domain output. Canonical chỉ mô tả
khoảng [0,q); một word canonical vẫn có thể encode xR thay vì x.

## 4. Ba chiều linh hoạt phải phân biệt

| Thay đổi | Làm thay đổi gì? | Không tự động mang lại gì? |
|---|---|---|
| FFT W/F | Range, độ phân giải, rounding, số limb cần ghép | Quyền giảm precision khi ký |
| NTT q | Root, reducer/constants, coefficient/product width, domain | Số lane tăng nếu hai q vẫn dùng lane16 |
| Transform N | Số tầng, stride/root schedule, lượng việc và khả năng lấp lane | Độ rộng operand nhỏ hơn hoặc precision thấp hơn |

Ví dụ suy ra từ bounds: canonical q3329 cần12 bit, q12289 cần14 bit; tích
biến×biến cần tối đa24/28 bit. Cả hai vẫn vừa một leaf16×16, nên đổi14→12 bit
có thể giúp reducer/logic nhưng không tự nhân đôi số leaf. q8380417 cần23 bit
và tích46 bit: vượt một leaf16, phải ghép tài nguyên hoặc chọn datapath khác.
Carry/correction còn cần headroom theo representation nội bộ.

Multi-profile q nghĩa là chọn một cấu hình giữa các command. RNS multi-modulus
lại là biểu diễn một số lớn bằng nhiều residue, còn cần nhiều prime và CRT.
Hai khả năng này không đồng nhất.

FFT multiprecision là lựa chọn của accelerator. Artifact fixed-point hiện tại
đã thay đổi signing/FFT so với reference cũ; repo pin đúng phiên bản/config
để kiểm bit. Không mặc định mọi Falcon implementation đều cần Q64.64, và
cũng không suy từ FFT N nhỏ rằng Q16.16 đủ an toàn cho signer.
[Fixed-point artifact](https://github.com/fixed-point-fndsa/fixed-point-c),
[contract cục bộ](numeric_contract.md).

## 5. Bóc butterfly xuống primitive: phần chung nằm ở đâu?

Với CT, ở cả hai miền đều có hình thức `T=B*w; out=(A+T,A−T)`.
Với GS, hình thức là `S=A+B; D=A−B; out=(S,D*w)`; inverse còn phụ thuộc
root inverse và normalization. CT/GS quyết định vị trí phép nhân so với cộng,
không tự định nghĩa forward/inverse hay thứ tự dữ liệu cho mọi implementation.

FFT xử lý A/B/w phức. Trong contract R8 đã chọn, mỗi complex multiply dùng:

```text
p0=mul(ar,br); p1=mul(ai,bi)
p2=mul(wrap(ar+ai),wrap(br+bi))
re=wrap(p0-p1); im=wrap(p2-p0-p1)
```

Mỗi real product có rounding riêng. Ghép leaf/CSA/pipeline có thể đổi nếu giữ
bit-exact; đổi thành 4M hay dời rounding là thay contract, dù tương đương trên
số thực. Đây là ràng buộc reference của repo, không tuyên bố mọi FFT phải dùng3M.
[Numeric spec01](../spec/FlexTransform/1.0/01_numeric_kernels.md).

NTT CT cần một modular multiplication cho mỗi butterfly. Montgomery tính
full T=a*b rồi reduction/correction; logic có thể khai thác constants của q,
nhưng không được bỏ product bits theo quy tắc rounding của FFT.

| Khối | Có thể dùng chung | Ràng buộc/logic riêng phải giữ |
|---|---|---|
| Leaf integer multiply | Mạnh: FFT limb products / NTT residue products | Sign theo limb, width và vị trí product bits |
| Cây cộng/carry | Có thể chia sẻ các đoạn thích hợp | Ghép FFT rộng; cô lập carry giữa NTT lane |
| Add/sub | Có thể chia sẻ phần nền | FFT wrap/round; NTT carry/borrow và correction |
| Routing/register/valid | Có thể dùng cùng hạ tầng | Operand giữ, context/tag và latency mỗi path |
| Working RAM/gather | Có thể dùng chung bank infrastructure | FFT split-real/imag, NTT coefficient/job map khác nhau |
| Root storage/buffers | Dùng chung control được | Format/băng thông/root schedule khác nhau |
| FFT hậu xử lý | Nên chuyên biệt khi cần | Fusion, rounding, 3M collector, conjugate, scale |
| NTT hậu xử lý | Nên chuyên biệt khi cần | Reducer, correction, domain/scalar normalize/BASEMUL |

Suy luận thiết kế: phần hợp nhất có ý nghĩa nhất là integer products cùng
hạ tầng giữ/chuyển dữ liệu. Rounding của FFT và reduction của NTT cần đường
xử lý tương ứng; ép hai semantics vào một output equation sẽ làm contract sai.
Mức chia sẻ adder/mux cụ thể vẫn cần implementation/PPA, chưa là kết quả đo.

### 5.1 Liên hệ sâu hơn: complex multiply và ML-KEM BASEMUL

Tự biến đổi đại số từ hai công thức nhân cặp:

```text
u=a0*b0; v=a1*b1; t=(a0+a1)*(b0+b1)
cross=t-u-v
complex: c0=u-v,         c1=cross
BASEMUL: c0=u+gamma*v,   c1=cross     (mod q)
```

FFT complex có quan hệ i²=−1; tọa độ ML-KEM có X²=gamma. Cả hai đều có
cấu trúc nhân hai thành phần. Với BASEMUL, biến đổi này cần ba variable-product
và thêm gamma*v, tức bốn modular products nếu gamma*v dùng một modmul riêng;
không được gọi toàn bộ là ba phép nhân. Khi gamma thay theo tọa độ, cũng không
mặc định nhân gamma là shift/add cố định rẻ.

Đây là ứng viên chia sẻ pre-add/issue-triplet/collector giữa FFT và BASEMUL.
Tuy nhiên FFT dùng wrapped pre-add và rounded fixed products theo contract;
NTT dùng modular pre-add/products và gamma correction. Nếu dùng Montgomery,
mọi intermediate/gamma phải encode nhất quán. Vì vậy đây là suy luận về cấu
trúc có thể tái sử dụng, chưa là một block BASEMUL đã có trong spec1.0 hoặc
một kết quả tiết kiệm tài nguyên đã đo.

## 6. Lượng việc và dữ liệu: vì sao không so chỉ bằng số butterfly?

Tự đếm từ radix2 loops, chỉ xét một forward transform:

| Transform | Số tầng tính trên layout đang xét | Butterfly | Phép nhân ở cấp kernel |
|---|---:|---:|---|
| Falcon packed FFT N1024 | 9 | 2304 complex | 6912 real mul theo3M |
| Falcon NTT N1024 | 10 | 5120 modular | 5120 modmul; reduction có chi phí riêng |
| ML-KEM NTT N256 | 7 | 896 modular | 896 modmul; chưa gồm BASEMUL |
| ML-DSA NTT N256 | 8 | 1024 modular | 1024 modmul; width lớn hơn |

Với packed FFT N≥2: BF=(N/4)*(log2(N)−1). Full NTT:
BF=(N/2)*log2(N). Incomplete N256 ở ML-KEM bỏ tầng cuối. Các con số trên
không gồm inverse scaling, pointwise, split/merge, sampler hay data transfer.
Một real mul128 và một modmul14 không có cùng chi phí; không suy throughput
từ cách cộng số phép nhân này.

Nếu mỗi memory pass đọc rồi ghi mỗi component một lần, không giữ toàn transform
trong register, dữ liệu hệ số R+W là `2*N*(W/8)*passes` byte. Vì vậy:

- FFT128 N1024, 9pass: 288KiB.
- NTT16 N1024, 10pass radix2: 40KiB.
- NTT16 N1024, 5pass mỗi pass fuse hai tầng: 20KiB.

Đây là lượng dữ liệu logic theo giả định, không phải DRAM traffic hay kết quả
mô phỏng. Chưa gồm root/control/gather overhead và normalization pass. Hai tầng
NTT fused giảm intermediate RAM traffic, nhưng vẫn cần đủ root, register,
correction và đường nối giữa hai tầng. NTT ít phép nhân hơn không bảo đảm ít
cycle hơn nếu reducer hoặc cấp dữ liệu không theo kịp.

## 7. NTT nhỏ: cần phân biệt workload thật và benchmark

**q nhỏ khác N nhỏ.** q nhỏ tác động số học; N nhỏ làm ít butterfly hơn nên
cụm lớn dễ thiếu việc. Batch nhiều đa thức có thể lấp tile nếu các job đã sẵn
sàng và độc lập. Ví dụ tự đếm N8 có12BF; gom8job có96BF. Trong REF16,
một paired pass trên64coeff có thể lấp16tile; đây là capacity mapping, không
phải đo speedup hoặc chứng minh tám job độc lập xuất hiện trong ứng dụng.

ML-KEM/ML-DSA dùng đa thức N256 dù tên parameter set có 512/768/1024 hoặc
44/65/87. Các số trong tên scheme không thay N thành những giá trị đó; nhiều
đa thức trong vector/matrix tạo workload batch với dependency riêng.
[FIPS203](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf),
[FIPS204](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf).

Sampler Falcon có nhiều bài toán FFT-domain nhỏ qua split/merge; điều này
không tự tạo ra các job NTT q12289 N8/16/32. NTT nhỏ trong NTRU solver phải
xem cùng prime width/CRT và dependency của solver. Để khẳng định lợi ích PQC
cho small-NTT batching, cần call trace `(op,N,q,width,representation,dependency)`.
Trước khi có trace đó, N8/16/32 là benchmark chức năng/khả năng sử dụng tài
nguyên, chưa là bằng chứng tăng tốc một luồng Falcon thực.

## 8. Hệ quả cho core hiện tại và điều kiện chính xác

| Phạm vi | Core/spec hiện tại hỗ trợ đến đâu? | Phần còn ở ngoài |
|---|---|---|
| R8 fixed-point signing kernels | FFT128, CMUL, SPLIT, MERGE, IFFT theo contract đã pin | Full sampler/control/remaining arithmetic và chứng minh distribution toàn hệ |
| Falcon verify arithmetic | q12289 NTT/INTT/TOMONT/MODMUL | Hash, decoding, conversion/norm và integration verifier |
| ML-KEM transform | q3329 N256 incomplete và inverse normalization | BASEMUL và full scheme; MODMUL scalar chưa thay được |
| ML-DSA | Chưa có profile/datapath23bit | q8380417, reducer/root/representation và tích hợp kernel |
| Full Falcon NTRU solver | Chưa bao phủ bằng hai profile16bit | NTT31bit/multi-prime, big integers, CRT và solver/control |
| FFT32/64 trong signer | Có integer kernel contract | Chưa chứng minh được phép thay FFT128 trong signing path |

Các nhận định phạm vi trên dựa vào [spec00](../spec/FlexTransform/1.0/00_scope_profiles.md),
[numeric contract](numeric_contract.md) và code/nguồn đã dẫn. Chúng không thay
đổi spec1.0, mà chỉ ra các ranh giới khi mô tả ứng dụng trong paper.

Ba mức tính đúng cần giữ riêng:

1. **NTT exact algebra:** đúng residue/domain/order/scaling; round-trip chưa
   đủ nếu forward/inverse cùng sai một permutation so với application.
2. **FFT exact implementation contract:** bit-exact với reference cụ thể,
   không phải tính chính xác vô hạn trên số thực. Tối ưu giữ contract được;
   hạ precision là thay semantics, cần phân tích lại overflow/error/sampling.
3. **PQC application/security:** live integration và chữ ký hợp lệ là bằng
   chứng chức năng; vài vector/chữ ký không thay phân tích distribution, bound
   hoặc leakage. Lịch kernel độc lập dữ liệu chưa chứng minh toàn signer chống
   side-channel.

Hướng nghiên cứu hợp lý từ phân tích này: giữ mảng nhân ghép/tách theo width,
tối ưu riêng reduction NTT và rounding/fusion FFT, rồi đánh giá ba workload
tách biệt: R8 FFT-domain kernels, Falcon q12289 modular arithmetic, và q3329
transform kernels. Mỗi workload phải công bố N/q/W/domain/kernel coverage;
benefit của FFT precision thấp và NTT nhỏ chỉ gắn với PQC khi có căn cứ ứng dụng
tương ứng. Việc thêm ML-KEM BASEMUL, ML-DSA hoặc full keygen là scope extension
cần được quyết định riêng.
