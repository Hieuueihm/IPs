# FlexTransform: lõi FFT đa precision và NTT đa modulus, hướng tới FN-DSA

> Ngày cập nhật: 25/10/2026.
> Mục đích: giải thích bài toán, động lực và ý tưởng kiến trúc phần core.
> Tài liệu này tập trung vào datapath tái cấu hình; chưa đặc tả scheduler.
> Cơ sở hiện tại: tile L32, ghép ở cấp liên tile; xem các phân tích đã có trong dự án.
> Ràng buộc PQC: tối ưu cách hiện thực nhưng giữ precision và kết quả reference
> theo numeric contract đã chọn; không tự hạ độ chính xác để tăng hiệu năng.

## 1. Ý tưởng trong một đoạn

Thiết kế một lõi số học dùng chung mảng nhân số nguyên cho **FFT/IFFT nhiều precision**
và **NTT/INTT nhiều modulus**. Mảng gồm các tile nhân 32×32 có thể làm việc độc lập
hoặc hợp tác tạo phép tính rộng hơn. Một cây gom tích riêng có nhiều điểm lấy kết quả
cho phép thay đổi kích thước nhóm theo precision. Sau phần nhân dùng chung, đường FFT
xử lý số phức và fixed-point; đường NTT thực hiện modular reduction chính xác.

**FN-DSA/Falcon là ứng dụng mục tiêu để đặt bài toán:** các kernel Fourier trong
sinh khóa/ký và phép nhân đa thức modulo trong xác minh có nhu cầu số học khác nhau.
Đề tài khảo sát liệu cùng một mảng tài nguyên có phục vụ các nhu cầu đó hiệu quả hơn
cách định cỡ cố định hoặc tách thành các datapath riêng hay không.

## 2. Bài toán đang có trong FN-DSA là gì?

### 2.1 Một ứng dụng, hai miền số học

NIST đang phát triển FN-DSA dựa trên Falcon trong FIPS 206. Tại thời điểm kiểm tra,
trang NIST vẫn ghi FIPS 206 đang được phát triển; tài liệu này dùng đặc tả Falcon
và các implementation được nêu rõ làm nguồn workload, chưa tuyên bố tuân thủ một
bản FIPS 206 cuối cùng. [S1, S2]

Falcon dùng ring:

~~~text
R_q = Z_q[x] / (x^n + 1)
q = 12289
n = 512 hoặc 1024 cho các parameter set thực tế.
~~~

FFT và NTT xuất hiện với vai trò khác nhau. FFT phục vụ các phép tính gần đúng
trên số phức; NTT thực hiện số học chính xác modulo q. [S3]

| Phần ứng dụng | Kernel cần quan tâm | Yêu cầu lên core |
|---|---|---|
| Sinh khóa | Fourier arithmetic trong implementation NTRU; các phép toán modulo/RNS tùy implementation | Có đường nhân phức và số học nguyên; full NTRUSolve còn nhiều khối khác |
| Ký | FFT/IFFT và arithmetic ở miền Fourier của đường ký | Precision, scaling và rounding phải phù hợp reference |
| Xác minh | Nhân đa thức modulo 12289 | NTT/INTT và pointwise multiplication chính xác |

Ví dụ ở xác minh, cần tính lại quan hệ:

~~~text
s1 = c - s2*h  mod (x^n + 1, q).
~~~

Reference hiện thực phép nhân bằng NTT, nhân từng điểm và inverse NTT;
kiểm tra norm và các bước còn lại nằm ngoài phép biến đổi. [S4]

**Hệ quả kiến trúc do đề tài đặt ra:** một thiết bị có cả ký và xác minh có thể
cần hai miền số học trên cùng nền tảng. Đây là kịch bản sử dụng để nghiên cứu;
thiết bị chỉ xác minh có thể phù hợp hơn với một lõi NTT chuyên dụng.

### 2.2 Precision của một implementation không đại diện cho mọi kernel

Hai nguồn workload cụ thể:

- NTRUGen dùng fixed-point 64 bit, gồm 32 bit phần lẻ, cho FFT và các phép gần đúng. [S5]
- Prototype fixed-point Falcon có kiểu Q32.32 và Q64.64; kiểu rộng dùng container
  128 bit. Đây là bằng chứng về nhiều biểu diễn trong implementation, không phải
  quy định mọi FFT của FN-DSA đều cần 128 bit. [S6]

Như vậy, có cơ sở khảo sát **FFT64 và FFT128 trên cùng core**, thay vì mặc định
một width duy nhất cho toàn bộ workload.

FFT32 được giữ trong phạm vi kiến trúc hiện tại để đánh giá khả năng dùng lại và
độ co giãn theo precision. Chưa có cơ sở gán FFT32 cho một bước ký FN-DSA an toàn.

Trong tài liệu này, FFT64/FFT128 chỉ độ rộng **mỗi thành phần thực hoặc ảo**,
không phải tổng số bit của một số phức. Fixed-point 64 bit cũng không đồng nghĩa FP64.

Việc thay floating-point bằng fixed-point cần phân tích riêng về bound và sai số.
Công trình fixed-point Falcon được tham khảo có kết quả an toàn đặt dưới điều kiện
về bound sai số, với một phần precision analysis còn dựa trên thực nghiệm. [S7]
Vì vậy, chọn width trong phần cứng phải theo numeric contract của workload;
không tự động hạ precision chỉ vì dữ liệu trước mắt có vẻ nhỏ.

### 2.3 Mâu thuẫn cần giải quyết ở phần cứng

Đây là bài toán kiến trúc của đề tài:

> Cùng một ngân sách phần cứng phải xử lý được các phép nhân phức rộng cho FFT,
> nhưng vẫn khai thác được nhiều phép toán độc lập khi workload dùng biểu diễn hẹp
> hoặc số học modulo.

Các lựa chọn tạo ra những đánh đổi:

| Lựa chọn | Điểm cần đánh giá |
|---|---|
| Định cỡ toàn datapath theo precision lớn nhất | Cấu hình hẹp có tận dụng được tài nguyên còn lại không? |
| Tách lõi cho từng precision và cho NTT | Diện tích, bộ nhớ và kết nối bị nhân lên bao nhiêu? |
| Dùng một multiplier nhỏ qua nhiều lượt | Tiết kiệm phần cứng nhưng thời gian hoàn tất phép rộng tăng ra sao? |
| Ghép/tách một mảng tile chung | Lợi ích song song có bù được cây gom, mux, register và reducer không? |

Đề tài chọn khảo sát lựa chọn cuối. Chưa coi đó là phương án thắng trước khi đo.

## 3. Tại sao hướng này được đưa ra?

### 3.1 FFT và NTT có phần nhân số nguyên có thể dùng chung

Với một tích phức:

~~~text
(a + j*b)*(c + j*d) = (a*c - b*d) + j*(a*d + b*c).
~~~

Khi dùng fixed-point, các tích a*c, b*d, a*d, b*c bắt đầu bằng nhân số nguyên,
sau đó xử lý vị trí dấu phẩy và rounding.

Ở NTT:

~~~text
t = b*w mod q
u = a + t mod q
v = a - t mod q.
~~~

Phép b*w cũng bắt đầu bằng nhân số nguyên, rồi reduction.
**Điểm chung để xây core là phần tạo tích số nguyên; phần xử lý sau tích xác định
semantics fixed-point hay modulo.**

Các công trình unified FFT/NTT đã có tiền lệ chia sẻ tài nguyên. Do đó, đây là
cơ sở kỹ thuật để phát triển, không được xem riêng nó là novelty. [S8]

### 3.2 Phép nhân rộng có thể tách thành các tích nhỏ

Với B = 2^32:

~~~text
x = x0 + B*x1
y = y0 + B*y1

x*y = x0*y0
    + B*(x0*y1 + x1*y0)
    + B^2*x1*y1.
~~~

Một phép 64×64 cần bốn tích 32×32 theo schoolbook. Bốn tile có thể hợp tác
tính tích rộng hoặc nhận bốn cặp operand độc lập để tạo bốn tích hẹp.
Sự thay đổi này cần cả đường cấp operand và đường gom kết quả.

Đó là nguyên lý **ghép/tách tài nguyên theo độ rộng**. BitFusion là một tiền lệ
trong DNN; chuyển sang butterfly FFT/NTT cần xử lý các kết quả độc lập, signedness,
rounding và reduction đúng với từng miền. [S9]

### 3.3 Câu hỏi thực sự là hiệu quả trên cùng phần cứng

Giả thuyết nghiên cứu:

> Phân bổ lại cùng mảng tile theo precision có thể tăng mức song song hữu ích,
> trong khi giữ khả năng xử lý phép rộng và dùng lại phần nhân cho NTT.

Lợi ích cần được kiểm chứng sau khi tính đủ chi phí. Đặc biệt:

- Ít bit có nghĩa hơn không tự làm số lane tăng.
- Nhiều lane nhân hơn không bảo đảm throughput cao hơn nếu reducer hoặc memory giới hạn.
- Giảm số cycle có thể không giảm latency nếu đường ghép làm Fmax giảm.

## 4. Kiến trúc phần core được đề xuất

### 4.1 Ba khối chính

~~~text
Operand data + twiddle + mode
             |
     Phân phối operand/limb
             |
   Mảng K tile L32 sign-select
        (mỗi tile 32×32)
             |
       +-----+----------------------------------+
       |                                        |
Cây gom liên tile                         Product độc lập
dịch cố định, nhiều tap                          |
       |                                 Mảng reducer NTT
Gom Re/Im, scale, rounding                 + cộng/trừ modulo
và cộng/trừ butterfly                            |
       |                                        |
       +----------- Kết quả FFT/NTT ------------+
~~~

Đường NTT-RNS có thể dùng lại tile cho các tích phụ của Montgomery.
Do đó, ngân sách phép nhân phải tính cả các tích đó, không chỉ tích operand ban đầu.

### 4.2 Tile cơ sở: L32

Tile L32 thực hiện một phép nhân 32×32, cho phép chọn signed/unsigned trên từng
toán hạng. Limb thấp của một số rộng là unsigned; limb cao nhất mang dấu khi cần.

**Tái cấu hình cơ sở nằm ở cách các tile hợp tác với nhau.** Một tile L32 không
tự tách thành nhiều multiplier nhỏ trong cấu hình đã chọn.

Lựa chọn này cập nhật đề xuất ban đầu dùng leaf 16 bit. Theo phân tích hiện có
trong repository, với băng thông data 512 bit đọc và 512 bit ghi mỗi cycle,
tile gồm bốn leaf 16 bit chưa tăng throughput toàn lõi; tổng hợp generic ghi nhận
chi phí tổ hợp cao hơn khoảng 16–26% và số FF xấp xỉ gấp đôi so với cấu hình L32
đối chiếu tốt nhất trong từng flow. Đây là kết quả cấp tile, chưa phải FPGA PPA.
Xem [phân tích tile](docs/tile_analysis.md) và [bảng synthesis](study/results/tile_synth.md).

Vì vậy, core cơ sở giữ L32; tile leaf nhỏ là điểm khảo sát khi thay ngân sách memory.

### 4.3 Ghép ở cấp liên tile

Theo schoolbook:

| Một real product | Tích riêng 32×32 cần tính |
|---|---:|
| 32×32 | 1 |
| 64×64 | 4 |
| 128×128 | 16 |

Nhân phức thông thường dùng bốn real product. Các tile hợp tác bằng cách tạo
tích riêng, căn trọng số và gom tại cây liên tile.

Model hiện tại ánh xạ phần nhân phức lên một cây nhị phân có lượng dịch cố định
theo cấp: **0, 32, 32, 64, 64 bit** cho K=32. Precision chọn điểm lấy kết quả
ở cấp thích hợp; phép cộng/trừ tại cấp đầu tạo đóng góp Re hoặc Im.
Xem [model liên tile](docs/intertile_model.md).

Cấu trúc này cho phép lấy nhiều kết quả độc lập ở cấp thấp hoặc ít kết quả rộng
ở cấp cao. Đây là biểu hiện cụ thể của khả năng tái cấu hình trong phần core.
Chi tiết pipeline và chi phí hiện thực cây vẫn cần đo.

### 4.4 Xử lý sau phép nhân

**Đường FFT:** gom đúng phần thực/ảo, giữ bit trung gian cần thiết, xử lý scale,
rounding và cộng/trừ butterfly theo numeric contract. Mode FFT32/64/128 có định
dạng riêng; việc hỗ trợ nhiều width không tự chứng minh chúng thay thế được nhau.

**Đường NTT:** reduction và cộng/trừ modulo chính xác. Với q=12289, hệ số canonical
cần 14 bit có nghĩa và có thể lưu trong lane 16 bit. Reducer là tài nguyên có chi phí
và throughput riêng; không mặc định một multiplier lane đồng nghĩa một modular lane.

**Phần dùng chung chủ yếu:** tile nhân và các đường cấp/thu kết quả phù hợp.
Không yêu cầu mọi mạch của FFT và NTT phải hợp nhất bằng mọi giá.

## 5. Multi-modulus NTT liên quan gì đến mục tiêu FN-DSA?

**Modulus 12289 là nhu cầu trực tiếp của đường xác minh Falcon.**
Khả năng đổi sang modulus khác là mục tiêu dùng lại core, không phải vì
FN-DSA đổi q giữa các mức bảo mật. [S3, S4]

Phạm vi rộng hơn trong [PLAN](PLAN.md) có các modulus PQC 3329, 12289, 8380417
và prime RNS khoảng 30–32 bit. Các prime RNS còn tạo hướng khảo sát arithmetic
cho NTRUSolve, nhưng tích hợp đầy đủ keygen nằm ngoài core biến đổi.

Ba loại linh hoạt cần phân biệt:

| Khả năng | Thứ thay đổi |
|---|---|
| FFT multi-precision | Width fixed-point, cách ghép tile và điểm lấy kết quả |
| NTT multi-modulus | q, constants của reducer và bộ twiddle hợp lệ |
| NTT width-dependent parallelism | Số lane độc lập và tài nguyên reduction/cấp dữ liệu tương ứng |

Trong core L32 hiện tại, modulus 14 bit và 23 bit đều vừa một multiplier tile.
Đổi giữa hai giá trị đó không tự tăng số multiplier lane.

OpenNTT đã có runtime modulus trên datapath định cỡ theo q lớn nhất. Vì vậy,
chỉ thêm thanh ghi q không đủ tạo khác biệt kiến trúc. [S10]

## 6. Ví dụ định lượng để hiểu ý tưởng

Ví dụ này là **cận capacity của mô hình**, không phải kết quả RTL hoàn chỉnh:
K=32 tile L32, schoolbook, data/twiddle cùng width trong mode FFT, băng thông data
mỗi hướng 512 bit/cycle.

| Mode | Tích cơ sở cho phần nhân/BF | Trần compute | Trần data | Trần hai yếu tố |
|---|---:|---:|---:|---:|
| FFT32 | 4 | 8 BF/cycle | 4 | 4 |
| FFT64 | 16 | 2 | 2 | 2 |
| FFT128 | 64 | 0,5 | 1 | 0,5 |
| NTT12289 | 1, chưa tính reduction | 32 | 16 | ≤16 |

Tại FFT64, cùng mảng có thể phục vụ hai butterfly độc lập theo phép đếm.
Tại FFT128, toàn mảng cần hai lượt cấp tích cho một butterfly.
Model liên tile hiện tại tính một thành phần Re hoặc Im hoàn chỉnh mỗi lượt.

Bảng thể hiện quan hệ giữa precision và mức song song có thể khai thác.
Nó chưa bao gồm toàn bộ chi phí cây gom, rounding, reducer, twiddle, pipeline và memory hazard.

## 7. Đóng góp nào đang được nhắm tới?

Đối tượng nghiên cứu là **một datapath biến đổi có thể tái cấu hình**, với:

1. Mảng tile L32 dùng chung cho FFT fixed-point và NTT.
2. Ghép liên tile để hỗ trợ nhiều precision FFT trên cùng phần cứng.
3. Cây gom có điểm lấy kết quả theo mode và xử lý signedness/rounding rõ ràng.
4. Đường NTT nhiều modulus với chi phí reduction được tính đầy đủ.
5. Đánh giá hiệu quả và giới hạn khi so với các phương án cố định tương đương.

Đây là mục tiêu đóng góp, chưa phải kết luận novelty.
Unified FFT/NTT, multi-precision và fusion đều đã có tiền lệ. Phần cần chứng minh
là cơ chế cụ thể, tính đúng và lợi ích toàn core sau overhead.

Các baseline cần so: core định cỡ rộng cố định; các datapath chuyên dụng tách riêng;
runtime-modulus NTT với số lane cố định. So sánh cần cùng workload và numeric
semantics, đồng thời báo cáo cả resource, Fmax và latency.

## 8. Phạm vi và bằng chứng còn thiếu

- FN-DSA là mục tiêu ứng dụng; chưa triển khai toàn bộ signer, verifier hoặc keygen.
- Sampler, SHAKE, division, sqrt và NTRUSolve đầy đủ không thuộc ý tưởng core cơ sở.
- Core FFT thông thường cần adapter để khớp biểu diễn, twiddle và các phép split/merge
  của workload Falcon; không mặc định giao diện hai bên giống nhau.
- Model và generic synthesis hiện có là bằng chứng từng phần, chưa thay cho PPA của
  core hoàn chỉnh trên FPGA.
- Chưa kết luận cấu hình precision nào đủ cho mọi bước FN-DSA. Cần pin reference,
  khớp quy tắc số học và đánh giá sai số của đúng kernel được thay.
- Mức tăng tốc FN-DSA phụ thuộc tỷ trọng kernel và chi phí tích hợp. Không suy từ
  speedup butterfly thành speedup toàn bộ đường ký.

Câu hỏi cần trả lời bằng thực nghiệm:

> Với workload xuất phát từ FN-DSA, lợi ích của việc dùng chung và ghép tile theo
> precision có vượt chi phí kết nối, gom kết quả, reduction và cấp dữ liệu hay không?

## 9. Tài liệu tham khảo

Nguồn ngoài được kiểm tra ngày 25/10/2026. Các link main là nguồn giải thích;
phải pin revision cụ thể khi lấy code/vector để kiểm chứng.

- **[S1]** [NIST PQC Standardization — trạng thái FIPS 206](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/Post_Quantum_Cryptography-Standardization).
- **[S2]** [NIST, FIPS 206: FN-DSA (Falcon), trình bày tại PQC Conference 2025](https://csrc.nist.gov/Presentations/2025/fips-206-fn-dsa-falcon).
- **[S3]** [Falcon specification v1.2](https://falcon-sign.info/falcon.pdf), Sections 3.5, 3.8–3.10, 3.13.
- **[S4]** [Falcon reference: vrfy.c](https://falcon-sign.info/impl/vrfy.c.html), constants q, to_ntt_monty và verify_raw.
- **[S5]** [NTRUGen: ng_inner.h](https://github.com/pornin/ntrugen/blob/main/src/ng_inner.h), mục Fixed-point numbers.
- **[S6]** [Fixed-point Falcon prototype: fpr.h](https://github.com/fixed-point-fndsa/fixed-point-c/blob/main/fpr.h), nhánh FALCON_FXP, fpr64 và fpr.
- **[S7]** [Toward a Secure Fixed-Point Implementation of the Falcon Signature Scheme](https://eprint.iacr.org/2026/1531).
- **[S8]** [A Unified Hardware Accelerator for Fast Fourier Transform and Number Theoretic Transform](https://arxiv.org/html/2504.11124v1).
- **[S9]** [Bit Fusion: Bit-Level Dynamically Composable Architecture for Accelerating Deep Neural Networks](https://arxiv.org/html/1712.01507v2).
- **[S10]** [OpenNTT: A Flexible Hardware Design Tool for Fast Fourier and Number-Theoretic Transformation Architectures](https://flokrieger.github.io/papers/tcad25_opennttext.pdf), Section III-D, IV.

Tài liệu nội bộ bổ sung:
[PLAN](PLAN.md), [tile analysis](docs/tile_analysis.md),
[intertile model](docs/intertile_model.md), [related work](docs/related_work.md).
