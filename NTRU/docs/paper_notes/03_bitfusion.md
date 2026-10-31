# P3 — BitFusion: ghép được PE, nhưng ghép xong phục vụ butterfly thế nào?

Ngày phân tích: 21/10/2026. Đọc toàn văn arXiv v2, tập trung Section II–IV và V-A.
Các phép tính cho FlexTransform bên dưới là dẫn xuất riêng, không phải số liệu BitFusion.

## Bằng chứng từ bài

[Bit Fusion: Bit-Level Dynamically Composable Architecture for Accelerating Deep Neural Networks](https://arxiv.org/html/1712.01507v2),
ISCA 2018.

Section II–III: Fusion Unit có 16 BitBrick; toán hạng cơ sở 2 bit, signed/unsigned.
Ghép không gian hỗ trợ tới 8×8; 16×16 dùng bốn cycle. Shift-add tree gom tích riêng;
output phục vụ multiply-accumulate. Section IV: setup instruction chọn cấu hình
cho block. Section V-A: Verilog, synthesis 45 nm và cycle-accurate simulation.
[Nguồn: Section II–V](https://arxiv.org/html/1712.01507v2#S3).

## Điều rút ra cho câu hỏi “PE0 + PE1 tạo phép nhân rộng?”

**Có thể ghép, nhưng số tích riêng quyết định số lần cấp việc.**
Dưới đây dùng schoolbook để dễ kiểm tra, không giả định hệ số của Karatsuba.
Gọi B=2^32, phân tách số nguyên không dấu:

~~~text
x = x0 + B*x1
y = y0 + B*y1
x*y = x0*y0 + B*(x0*y1 + x1*y0) + B^2*(x1*y1)
~~~

64×64 cần bốn tích 32×32. Nếu chỉ có hai uPE:

| Issue slot | uPE0 | uPE1 |
|---|---|---|
| 0 | x0*y0 | x0*y1 |
| 1 | x1*y0 | x1*y1 |
| Sau khi tích sẵn sàng | Căn dịch, gom carry và cộng kết quả | Cùng một phép nhân 64×64 |

Mỗi slot không đồng nghĩa với lúc output đã có. Nếu multiplier có latency L,
các tích của slot 0 đến sau L cycle; reduction tree còn có latency riêng.
Chỉ khi các tài nguyên phụ trợ đủ throughput mới có thể lập lịch liên tiếp như bảng.

Với Q multiplication slots mỗi cycle và W chia hết cho 32:

~~~text
P(W) = (W/32)^2                 số tích cơ sở cho một real product
C_issue >= ceil(P(W)/Q)         số slot cấp tích cho một product biệt lập
R_product <= Q/P(W)             cận tốc độ dài hạn, chưa tính bottleneck khác
~~~

| Real product | P(W) | Q=2: issue slots | Q=4 | Q=8 |
|---|---:|---:|---:|---:|
| 64×64 | 4 | 2 | 1 | 1 |
| 128×128 | 16 | 8 | 4 | 2 |

Q=8 có thể cấp hai product 64×64 mỗi cycle nếu routing/gom tích cho phép;
bảng issue của một product không diễn tả hết mức song song nhiều product.

## Signedness: lỗi dễ mắc khi chia limb

Với số signed W bit, limb cao nhất mang dấu; các limb thấp vẫn unsigned.
Ví dụ x=-1 ở 64 bit:

~~~text
x_hi = -1
x_lo = 2^32 - 1
x = x_lo + 2^32*x_hi = -1
~~~

Nếu coi x_lo là signed -1 thì biểu thức thành -1-2^32 và sai.
Mảng nhân cần hỗ trợ đúng các tổ hợp signed/unsigned hoặc dùng phép hiệu chỉnh
tương đương. Chỉ đổi bit mode trên multiplier mà bỏ qua signedness của từng limb
chưa tạo được phép nhân rộng đúng.

Tổng các tích được căn dịch trước khi bỏ bit. Với FFT fixed-point, vị trí rounding
phải theo numeric contract; không round từng limb product như thể chúng là các
phép fixed-point độc lập. Với NTT, phép gom và reduction phải bảo toàn residue chính xác.

## Từ một product sang một FFT butterfly

Giả thiết khảo sát, cùng baseline trong PLAN:

- K=32 uPE, mỗi uPE cấp một phép 32×32 mỗi cycle.
- Nhân phức thông thường dùng bốn real product.
- Data và twiddle có cùng width W.
- Hai số phức vào, hai số phức ra mỗi butterfly.
- Data read/write mỗi hướng 512 bit/cycle; twiddle dùng đường riêng.

| Mode | Tích cơ sở/BF | Trần compute BF/cycle | Data read/BF | Trần read BF/cycle | Trần kết hợp |
|---|---:|---:|---:|---:|---:|
| FFT64 | 4×4 = 16 | 2 | 256 bit | 2 | 2 |
| FFT128 | 4×16 = 64 | 0.5 | 512 bit | 1 | 0.5 |

Đây là cận trên của mô hình, chưa chứng minh khả thi ở FPGA.
Nếu thực sự đạt các trần này, FFT64 cần tới 256 bit twiddle/cycle và FFT128 trung bình
128 bit/cycle khi không có reuse. Đường twiddle riêng vẫn có chi phí.

Ở FFT128 có thể cấp 32 tích riêng trong slot 0, 32 tích còn lại trong slot 1.
Metadata phải giữ các tích thuộc cùng butterfly cho đến khi gom đủ.
Không gọi cấu hình này là “một FFT128 butterfly mỗi cycle”.

## Khác biệt quan trọng khi chuyển fusion sang FFT/NTT

Các điểm sau là yêu cầu của bài toán mới do mình phân tích:

**Kết quả độc lập.** Hai butterfly NTT tạo bốn hệ số output độc lập.
Không được gom các lane vào cùng một tổng như một dot product.
Ngay cả khi dùng chung adder tree vật lý, cần chế độ phân đoạn và writeback riêng.

**Không trộn hai loại cộng.** Trong mode rộng, cộng các partial product tạo một
integer product. Trong mode hẹp, các product thuộc nhiều butterfly khác nhau.
Mode control phải xác định rõ ranh giới này.

**Reduction là một tài nguyên riêng.** NTT cần throughput của modular reduction,
không chỉ throughput integer multiply. Có thể chia sẻ phần nhân của reducer,
nhưng khi đó phải tính cả công việc phụ vào ngân sách.

**Local grouping ảnh hưởng routing.** Ghép nhóm lân cận là ứng viên dễ kiểm soát.
Chưa có bằng chứng cần hoặc có lợi với mạng cho mọi uPE ghép tùy ý.

## Thí nghiệm nào giúp đánh giá hướng này?

Giữ cùng K và cùng ngân sách memory, so ba phương án:

1. Nhóm rộng cố định, chạy operand hẹp bằng padding.
2. Ghép hoàn toàn trong không gian nếu đủ tài nguyên.
3. Ghép kết hợp không gian và nhiều lượt cấp tích.

Báo cáo cycles, Fmax sau place-and-route, LUT/FF/DSP và traffic.
Nếu phương án 3 ít cycle hơn nhưng giảm Fmax nhiều, phải so latency theo thời gian.
Giữ riêng phép so cùng K với phép so cùng tổng area: routing/reduction bổ sung
có thể khiến chúng không đồng thời thỏa mãn.

BitFusion cung cấp tiền lệ fusion. Phần cần chứng minh của mình là grouping phục vụ
butterfly độc lập, tính đúng theo từng miền số học và lợi ích toàn lõi.
