# P1 — Unified FFT/NTT: chia sẻ số học đã giải quyết được gì?

Ngày phân tích: 21/10/2026. Phạm vi: toàn văn arXiv v1, Section III–IV.
Chưa chạy RTL hoặc tái lập kết quả FPGA của tác giả.

## Bằng chứng từ bài

[A Unified Hardware Accelerator for Fast Fourier Transform and Number Theoretic Transform](https://arxiv.org/html/2504.11124v1),
ICASSP 2025; [DOI](https://doi.org/10.1109/ICASSP49660.2025.10889132).

| Hạng mục | Mô tả trong Section III, Fig. 2–4 |
|---|---|
| FFT | N=512; real/imag 32 bit; data Q16.15, twiddle Q1.30, thêm sign |
| NTT | ML-DSA: N=256, q=8380417; ML-KEM: N=256, q=3329 |
| Arithmetic | 4 Karatsuba multiplier 32 bit, từ multiplier 16 bit; Barrett reduction |
| Memory | Data: 8×(256×16), true dual port; twiddle: 1024×32, dual port |
| Pipeline | 9 stage; mode FFT/ML-DSA/ML-KEM: 1/2/4 butterfly mỗi cycle |

Table I: unified core trên ZCU104, 400 MHz: 3716 LUT, 2400 FF, 12 DSP, 5 BRAM.
Cycles: FFT 2430; ML-DSA 624; ML-KEM 322.
FFT-only: 2300 LUT, 1898 FF, cùng DSP/BRAM và FFT cycles.
[Nguồn: Section III–IV, Table I](https://arxiv.org/html/2504.11124v1#S3).

## Phân tích của mình: vì sao đây là baseline gần?

Điểm cần đối chiếu là **thay đổi số butterfly độc lập trên tài nguyên chung**.
Nếu đề tài chỉ nói “FFT dùng phép nhân rộng, NTT tận dụng phép nhân hẹp”, reviewer
có thể yêu cầu giải thích khác biệt ngay với bài này.

Sơ đồ khái niệm dưới đây do mình tổng hợp để đặt câu hỏi thiết kế, không phải sơ đồ
netlist hay bản vẽ lại Fig. 4:

~~~text
                    lệnh / mode
                         |
RAM -> unpack / route -> shared arithmetic -> postprocess -> pack -> RAM
                           |                      |
                      partial products      FFT: fixed-point
                                            NTT: reduction
twiddle storage ----------^
~~~

Muốn mở rộng sơ đồ này sang nhiều precision FFT, phải trả lời thêm:

1. Khi chuyển FFT64 sang FFT128, những multiplier nào hợp tác tính cùng một tích?
2. Các tích riêng thuộc butterfly nào, dịch bao nhiêu và cộng ở đâu?
3. Khi số butterfly đang hoạt động giảm, địa chỉ RAM và thứ tự twiddle đổi thế nào?
4. Output rộng cần nhiều beat hơn hay giảm số kết quả mỗi beat?

Đó là các câu hỏi của FlexTransform; không gán chúng thành tính năng của P1.

## Bài tập lịch tính: throughput peak không phải latency transform

Đây là phép tính của người đọc. Với radix-2:

~~~text
Số butterfly = (N/2) × số stage
Ideal issue cycles >= tổng butterfly / peak butterfly-per-cycle
~~~

Quy ước đếm mỗi phép butterfly trên hai hệ số vô hướng là một butterfly NTT;
ML-KEM có 7 stage, không dùng 8 stage của NTT đầy đủ.

| Mode | Butterfly theo quy ước trên | Ideal issue cycles | Cycles Table I | Chênh lệch |
|---|---:|---:|---:|---:|
| FFT | 256×9 = 2304 | 2304 | 2430 | 126 |
| ML-DSA | 128×8 = 1024 | 512 | 624 | 112 |
| ML-KEM | 128×7 = 896 | 224 | 322 | 98 |

Các giá trị ideal chỉ là cận dưới theo phép đếm. Chênh lệch có thể gồm khởi động,
kết thúc, chuyển stage và điều khiển; bảng này không xác định phần nào chiếm bao nhiêu.
Không được lấy pipeline 9 stage rồi coi toàn bộ transform chỉ tốn thêm 9 cycle.

Hai tỉ lệ tự tính từ resource table:

~~~text
LUT overhead = (3716 - 2300) / 2300 = 61.57%
FF overhead  = (2400 - 1898) / 1898 = 26.45%
~~~

So sánh này đo chi phí thêm functionality vào FFT baseline. Nó chưa trả lời liệu
một lõi fusion có tốt hơn lõi cố định khi giữ cùng tổng area hay không.

## Tự tính nhu cầu dữ liệu tối thiểu

Giả sử không reuse các input giữa butterfly và mỗi hệ số được đọc/ghi đúng một lần
trong một stage; bỏ qua twiddle ở bảng này:

| Mode | Payload read cho một butterfly | Payload write | Payload read/cycle ở peak |
|---|---:|---:|---:|
| FFT | 2 số phức × 2 thành phần × 32 = 128 bit | 128 bit | 128 bit |
| ML-DSA | 2×23 = 46 bit | 46 bit | 92 bit |
| ML-KEM | 2×12 = 24 bit | 24 bit | 96 bit |

Đây là payload hữu ích, không phải tổng số bit vật lý qua RAM sau padding hoặc mux.
Số cổng và ánh xạ bank vẫn phải xét riêng: đủ bit tổng cộng chưa chứng minh được
hai toán hạng của mọi butterfly luôn nằm ở các vị trí truy cập đồng thời.

## Cấu hình và phần còn chưa xác minh

Mode select có bằng chứng ở Section III. Bài không mô tả nhiều precision FFT runtime.
Mình cũng chưa thấy mô tả đường nghịch hoặc modulus tùy chọn tổng quát trong phạm vi
toàn văn này; không tự suy ra IFFT/INTT từ sự tương đồng của butterfly.

Chưa xác minh repository RTL công khai. Kết quả trên là tác giả báo cáo,
không phải kết quả chạy trong workspace.

## Bài học cho hướng của mình

**Giữ:** đánh giá phần chia sẻ ở cấp multiplier, cộng/trừ, memory và control;
ghi nhận mức song song riêng cho từng mode.

**Cần chứng minh thêm:** một FFT có nhiều precision trên cùng bitstream,
grouping có lịch tính rõ ràng, và lợi ích sau khi tính chi phí bộ nhớ/gom tích riêng.
Nếu khảo sát NTT đa modulus, cần so với baseline đã đổi q và baseline có nhiều lane
modular arithmetic, không chỉ với FFT-only.

P1 làm giảm độ mạnh của claim “unified FFT/NTT”. Nó chưa đủ để khẳng định phần còn lại
là mới; phải đọc các bài FFT đa precision và modular multiplier có thể cấu hình.
