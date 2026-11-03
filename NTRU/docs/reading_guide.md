# Hướng dẫn đọc paper cho FlexTransform

> Cập nhật: 21/10/2026.
> Mục đích: xây khả năng phân tích kiến trúc trước khi triển khai RTL.
> Hướng đang khảo sát: FFT đa precision, NTT đổi modulus và phân bổ tài nguyên theo độ rộng.
> Đây là danh sách chọn lọc và câu hỏi đọc, không phải kết luận đã chứng minh novelty.

Đã hoàn thành vòng phân tích P1–P3:
[bảng đối chiếu và nhận định](related_work.md),
[P1](paper_notes/01_unified_fft_ntt.md),
[P2](paper_notes/02_openntt.md),
[P3](paper_notes/03_bitfusion.md).
Ghi chú phân biệt bằng chứng nguồn, suy luận và phần chưa tái lập.

## 1. Thứ tự và mục tiêu đọc

Đọc sáu bài nền theo thứ tự P1 -> P2 -> P3 -> P4 -> P5 -> P6.
Song song tìm toàn văn nhóm N1–N3 để tránh đánh giá khoảng trống chỉ dựa vào OpenNTT.
Không cần đọc hết bối cảnh ứng dụng của mọi bài trước khi xem phần kiến trúc.

| Thứ tự | Bài | Năng lực cần rút ra |
|---|---|---|
| P1 | Unified FFT/NTT, ICASSP 2025 | Nhìn ra phần số học có thể chia sẻ giữa hai miền |
| P2 | OpenNTT, TCAD, online 2025 / số journal 2026 | Phân biệt configurability, dataflow, banking và twiddle generation |
| P3 | BitFusion, ISCA 2018 | Phân tích ghép/tách đơn vị số học và mức song song theo bitwidth |
| P4 | Maestro, bản arXiv 2025, tập trung Section V | Phân tích FFT multi-precision và hiệu quả ở cấp butterfly/data movement |
| P5 | CoHA-NTT, ePrint 2021 / journal 2022 | Hiểu đường modular multiply và tính linh hoạt theo tham số |
| P6 | Aloha-HE, DATE 2024 | Đánh giá chia sẻ tài nguyên và chi phí điều phối ở cấp hệ thống |

Trạng thái truy cập ở đây không có nghĩa mọi con số của bài đã được tái lập.
Các câu “cần phân tích” là câu hỏi nghiên cứu đề xuất, không phải mô tả tính năng đã xác nhận.

## 2. Sáu bài đọc nền

### P1 — A Unified Hardware Accelerator for Fast Fourier Transform and Number Theoretic Transform

- Venue: ICASSP 2025.
- [Toàn văn HTML](https://arxiv.org/html/2504.11124v1).
- [PDF](https://arxiv.org/pdf/2504.11124).
- Trạng thái: đã kiểm tra phần kiến trúc và bảng implementation.

**Vì sao đọc đầu tiên:** bài ngắn, trực tiếp với mục tiêu hợp nhất.
Bài hỗ trợ FFT fixed-point 32 bit, NTT ML-KEM/ML-DSA; dùng các bộ nhân nhỏ,
cấu hình butterfly và bộ nhớ chung. Đây chưa phải bằng chứng FFT đổi nhiều precision runtime.

**Đọc kỹ:** Section III, Fig. 2–4 và Table I.
**Tự làm sau khi đọc:**

1. Vẽ lại datapath FFT và hai mode NTT bằng ba màu: dùng chung, FFT riêng, NTT riêng.
2. Giải thích vì sao cùng lõi có các mức song song 1/2/4 butterfly theo mode.
3. Tách “số bit hệ số”, “độ rộng bộ nhân” và “độ rộng sản phẩm”.
4. Theo dõi một butterfly từ RAM -> tính toán -> RAM; chỉ ra nơi cần thêm logic.
5. Ghi overhead khi thêm NTT vào FFT; không nhầm so sánh này với lõi cùng ngân sách tính toán.

**Đầu ra mong muốn:** một sơ đồ chia sẻ tài nguyên và bảng chi phí theo mode.

### P2 — A Flexible Hardware Design Tool for Fast Fourier and Number-Theoretic Transformation Architectures

- DOI: 10.1109/TCAD.2025.3595834.
- Online publication 2025; bản PDF hiện có ghi số journal tháng 5/2026.
- [Paper](https://flokrieger.github.io/papers/tcad25_opennttext.pdf).
- [OpenNTT RTL/tool](https://github.com/flokrieger/OpenNTT).
- Trạng thái: đã kiểm tra phần III–IV và các module code liên quan.

**Vì sao cần đọc sâu:** baseline cho kiến trúc nhiều PE dùng bộ nhớ theo stage.
Paper kết hợp lịch truy cập với sinh twiddle, đưa ra MemOpt/RoutOpt và hỗ trợ chọn modulus
runtime. FFT hay NTT, N và số PE là các cấu hình tạo lõi; không đồng nhất với runtime fusion.

**Đọc kỹ:** Section III-D, IV-A/B, Fig. 2–4; sau đó đọc lại III-A/B/C để hiểu lịch.

**Đọc code theo thứ tự:**

1. [openntt.py](https://github.com/flokrieger/OpenNTT/blob/main/tool/openntt.py):
   q_list -> logq_max -> LOGQ; io_band -> PE.
2. [ntt_core.sv](https://github.com/flokrieger/OpenNTT/blob/main/hardware/ntt_control/ntt_core.sv):
   vòng generate butterfly, q đầu vào, timing và twiddle.
3. [btf_modmul.sv](https://github.com/flokrieger/OpenNTT/blob/main/hardware/butterfly/btf_modmul.sv):
   integer multiply rồi modular reduction.
4. [wlmont.sv](https://github.com/flokrieger/OpenNTT/blob/main/hardware/modred/modred_wl_mont/wlmont.sv):
   tham số LOGQ/W/L và các tầng reduction.
5. [polyRam.sv](https://github.com/flokrieger/OpenNTT/blob/main/hardware/memory/polyRam.sv):
   cặp bank cấp toán hạng cho butterfly.

**Câu hỏi cần trả lời:**

- Những tham số nào cần tổng hợp lại, tham số nào đổi giữa các lệnh?
- Thay q nhỏ hơn có thay số lane, multiplier width hoặc số tầng reduction không?
- MemOpt tiết kiệm ROM bằng cách nào, RoutOpt trả thêm ROM để được gì?
- Có ràng buộc nào giữa pipeline latency, N và số PE?
- Tốc độ bị giới hạn ở data RAM, twiddle hay arithmetic với mỗi cấu hình?

**Đầu ra mong muốn:** sơ đồ PE/RAM/TwGen và bảng synthesis-time/runtime.
Ví dụ q nhỏ dùng datapath rộng phải ghi là phân tích cấu trúc; không gọi là benchmark
khi chưa thực hiện mô phỏng/đo.

### P3 — Bit Fusion: Bit-Level Dynamically Composable Architecture for Accelerating Deep Neural Networks

- Venue: ISCA 2018.
- [Paper và các phiên bản](https://arxiv.org/abs/1712.01507).
- [PDF](https://arxiv.org/pdf/1712.01507).
- Trạng thái: đã đọc vi kiến trúc Section II–IV, phương pháp đánh giá V-A;
  đã dẫn xuất ví dụ signed schoolbook và lịch cấp tích cho FFT trong note P3.

**Vai trò:** tiền lệ quan trọng của ghép/tách đơn vị tính toán theo bitwidth.
Bối cảnh là DNN, không phải butterfly phức hay modular arithmetic.

**Cần phân tích:**

1. Đơn vị cơ sở tính gì; phạm vi nào có thể ghép với nhau?
2. Có bao nhiêu tích riêng, dịch bao nhiêu bit và gom ở đâu?
3. Signedness, carry và accumulator được xử lý thế nào?
4. Đổi width thay mức song song, latency, initiation interval hay cả ba?
5. Lợi ích về truyền dữ liệu đến từ packing nào?
6. Phần nào chuyển được sang integer multiply trong FFT/NTT; phần nào phụ thuộc DNN?
7. So sánh có cùng area, frequency, precision và workload không?

**Đầu ra mong muốn:** tự dẫn xuất một phép nhân rộng từ các phép nhân hẹp,
kèm lịch cấp việc. Không sao chép cấu hình bit cực nhỏ của DNN sang FPGA mà chưa đo.

### P4 — Maestro: A 302 GFLOPS/W and 19.8GFLOPS RISC-V Vector-Tensor Architecture for Wearable Ultrasound Edge Computing

- Nguồn: bản arXiv 2025.
- [Toàn văn HTML](https://arxiv.org/html/2503.04581v1).
- [PDF](https://arxiv.org/pdf/2503.04581).
- Trạng thái: đã kiểm tra Section V, Fig. 4–5.

**Vai trò:** ví dụ FFT đa precision có data movement và butterfly cụ thể.
MP-FFT hỗ trợ FP16/FP32; paper mô tả một C64 hoặc hai C32 butterfly mỗi chu kỳ.
C32/C64 ở đây là tổng số bit của một số phức, không phải độ rộng mỗi thành phần.
Đây là floating-point, khác Q32.32/Q64.64 dự kiến của FlexTransform.

**Đọc trước:** Section V-A/B/C, Fig. 4–5; sau đó phần đo FFT ở Section VI.

**Câu hỏi cần trả lời:**

- Precision thấp dùng lại engine rộng như thế nào; phần nào là tài nguyên bổ sung?
- Gather/scatter và các cổng memory hỗ trợ hai mức song song ra sao?
- Butterfly fused thay đổi vị trí rounding và yêu cầu trung gian như thế nào?
- Khi so với fixed-point, phần exponent/normalization nào không áp dụng?
- Số liệu nào là FFT, số liệu nào là toàn SoC hoặc tensor engine?

**Đầu ra mong muốn:** bảng một butterfly rộng vs hai butterfly hẹp và sơ đồ đường dữ liệu.
Không dùng chỉ số 302 GFLOPS/W của tensor trong title để đại diện hiệu năng FFT.

### P5 — CoHA-NTT: A Configurable Hardware Accelerator for NTT-based Polynomial Multiplication

- Kemal Derya, Ahmet Can Mert, Erdinç Öztürk, Erkay Savaş.
- [ePrint 2021/1527 và PDF](https://eprint.iacr.org/2021/1527).
- [Journal 2022, DOI 10.1016/j.micpro.2022.104451](https://doi.org/10.1016/j.micpro.2022.104451).
- Trạng thái: xác nhận abstract/metadata; cần đọc toàn văn phần multiplier và controller.

**Vai trò:** nền tảng để hiểu “configurable NTT” ngoài trường hợp riêng OpenNTT.
Bài phân biệt tính linh hoạt runtime của tham số với cấu hình phần cứng khi tạo lõi.

**Cần phân tích:**

1. Cho phép những N, q và loại root nào; có yêu cầu về dạng prime không?
2. Modular multiplier gồm integer multiply và reduction như thế nào?
3. Có đổi số bước hoặc latency khi thay modulus không?
4. Cùng butterfly hỗ trợ forward/inverse/pointwise bằng đường dữ liệu nào?
5. Họ xử lý correction, overflow, miền Montgomery và inverse normalization ở đâu?
6. Khi đổi q, thứ gì host cần chuẩn bị ngoài chính giá trị q?

**Đầu ra mong muốn:** một phép modular multiply hoàn chỉnh trên giấy,
từ input representation đến canonical output và bound trung gian.

### P6 — Aloha-HE: A Low-Area Hardware Accelerator for Client-Side Operations in Homomorphic Encryption

- Venue: DATE 2024.
- [Paper](https://flokrieger.github.io/papers/date24_aloha.pdf).
- [RTL](https://github.com/flokrieger/Aloha-HE).
- [Bản mở rộng AMD OpenHW](https://github.com/flokrieger/Aloha-HE_AMD-OpenHW).
- Trạng thái: đã kiểm tra phần III và sơ đồ hệ thống.

**Vai trò:** cách chia sẻ phần số học nguyên giữa floating-point và modular ring,
cùng việc điều phối nhiều loại phép toán. Bản AMD OpenHW có phần mở rộng runtime N;
không gán tính năng đó cho mọi cấu hình của paper gốc.

**Đọc kỹ:** III-A/B, sơ đồ shared multiplier và architecture tổng thể.
**Câu hỏi cần trả lời:**

- Tài nguyên nào thật sự được dùng chung và tài nguyên nào vẫn tồn tại riêng?
- Pre/post-processing của floating-point và Montgomery reduction đặt ở đâu?
- Nhân phức dùng các integer multiplier thế nào?
- Throughput FFT và NTT có cùng đơn vị đo không?
- Chi phí bộ nhớ, DMA và instruction có được tính trong latency không?

**Đầu ra mong muốn:** bảng chức năng -> multiplier/adders/reducer/memory/controller.
So trực tiếp với P1 để hiểu hai cách dùng chung FFT/NTT khác nhau ra sao.

## 3. Nhóm phải kiểm tra trước khi khóa claim novelty

### N1 — R-BMM: A Reconfigurable Barrett Modular Multiplier Architecture for High-Performance Cryptographic Systems

- Venue: ISQED 2026.
- DOI: 10.1109/ISQED69900.2026.11534683.
- [Trang IEEE](https://ieeexplore.ieee.org/document/11534683/).
- Trạng thái: xác nhận abstract từ IEEE; chưa có toàn văn đã phân tích.

Abstract mô tả cấu hình một phép modulo 256 bit, ba phép 128 bit hoặc chín phép 64 bit
song song trên một Karatsuba core dùng lại.

**Vì sao ưu tiên:** sát ý tưởng nhiều phép hẹp đổi thành ít phép rộng trong miền modulo.

**Khi có toàn văn, kiểm tra:**

- Reduction có đổi cấu trúc theo mode cùng multiplier không?
- Modulus là runtime hay synthesis-time; có bao nhiêu q độc lập đồng thời?
- Quan hệ giữa “parallel” với initiation interval và latency?
- Cơ chế ghép là trong một multiplier hay giữa nhiều butterfly PE?
- Bitwidth, routing và chi phí tái cấu hình có áp dụng được cho NTT workload không?

Không dùng tỉ lệ 1/3/9 như một quy luật chung cho schoolbook multiplication.

### N2 — A High-Performance and Configurable NTT Accelerator Based on Scalable 2-D Architecture

- Jianbo Guo, Jiaoyang Zhu, Hao Xiao.
- DOI: 10.1109/TVLSI.2025.3606636.
- [Trang DOI](https://doi.org/10.1109/TVLSI.2025.3606636).
- Trạng thái: đã xác nhận title/DOI qua metadata; chưa truy cập được toàn văn publisher.

**Vai trò trong danh sách:** đối chiếu kiến trúc NTT nhiều đơn vị tính,
configurability và tổ chức dữ liệu. Chưa dùng thông tin từ bản tóm tắt thứ cấp
để khẳng định chính xác cơ chế runtime hoặc khả năng ghép/tách của bài.

**Cần kiểm tra toàn văn:** datapath modulo, số kênh thay đổi thế nào theo width,
điều phối 2-D, memory traffic và các cấu hình so sánh. Bổ sung dẫn chứng số trang/hình
sau khi đọc, trước khi dùng làm cơ sở cho nhận định novelty.

### N3 — A Lightweight Fused Floating-Point & Modular Arithmetic Unit for FALCON FFT/NTT

- Nguồn: ICTA 2026.
- [Abstract hội nghị](https://epapers2.org/icta2026/ESR/paper_details.php?paper_id=7294).
- Trạng thái: mới xác nhận abstract/acceptance, chưa phân tích toàn văn.

Abstract mô tả bộ nhân con 14 bit ghép cho mantissa FP64 và cấu hình thành tám lane NTT.
**Cần kiểm tra:** FFT có nhiều precision không; mức fusion ở đâu; reduction và
memory có thay theo mode không. Đây là đối chiếu trực tiếp cho FFT/NTT chia sẻ tài nguyên.

## 4. Đọc bổ sung theo vấn đề còn thiếu

| Nhu cầu | Bài | Cách sử dụng |
|---|---|---|
| So sánh với streaming thay vì memory-based | [ABC-FHE](https://arxiv.org/html/2506.08461v1) | Đọc Section III–IV về Fourier engine/MDC, twiddle và buffer |
| Precision FFT gắn yêu cầu ứng dụng | [A Flexible CO-OFDM Using Reconfigurable Multi-Precision FFT](https://digital.library.adelaide.edu.au/items/27137897-cc26-47c7-af99-72859a4559c2) | Có abstract trường; cần toàn văn để đánh giá phương pháp chọn precision |
| NTT bitwidth và reduction | [A Bitwidth-Flexible Modular Multiplier with Shift-Free Accumulation for Efficient NTT Acceleration in FHE](https://epapers2.org/iscas2026/ESR/paper_details.php?paper_id=1750) | Abstract ISCAS 2026; tìm toàn văn trước khi kết luận về mức song song |
| Multi-precision ngoài DNN | [ZK-Flex](https://arxiv.org/abs/2606.03046) | Đối chiếu multiplier/composability cho ZKP, không đồng nhất với FFT |
| Kiến trúc NTRU gần Falcon | [Unified FFT/NTT, ISCAS 2025](https://researchoutput.ncku.edu.tw/en/publications/a-unified-fftntt-design-for-efficient-ntru-equation-solving-in-fa/) | Đọc toàn văn để tách số học keygen, radix và độ rộng NTT |
| Sai số fixed-point khi chọn Falcon case study | [Toward a Secure Fixed-Point Implementation of the Falcon Signature Scheme](https://eprint.iacr.org/2026/1531) | Phục vụ numeric contract; không thay thế tài liệu kiến trúc PE |

## 5. Mẫu phân tích bắt buộc cho mỗi bài

Không chỉ ghi “nhanh hơn x lần”. Mỗi bài tạo một note khoảng 1–2 trang với các mục:

1. **Bài toán:** kernel nào, workload nào, vì sao cần flex?
2. **Semantics:** số thực/phức/modulo, số bit input/product/output, rounding hoặc reduction.
3. **Cấu hình:** bảng synthesis-time vs runtime; danh sách giá trị hợp lệ.
4. **Sơ đồ tự vẽ:** memory -> operand routing -> arithmetic -> writeback.
5. **Mapping:** một ví dụ hẹp và một ví dụ rộng, nếu có; nhóm nào hợp tác?
6. **Lịch:** latency, initiation interval, stage transition và chi phí đổi mode.
7. **Băng thông:** hệ số và twiddle đọc/ghi mỗi cycle; số bank/cổng cần thiết.
8. **Đánh giá:** FPGA/process, tool, clock, resource, stimulus và phạm vi latency.
9. **Điểm chưa chứng minh:** từ abstract, từ toàn văn, hay suy luận của người đọc?
10. **Đối chiếu FlexTransform:** giống ở đâu, khác ở đâu, giả thuyết cần đo là gì?

Mọi claim quan trọng phải có số trang, mục, hình hoặc file RTL cụ thể.
Tách chữ “runtime” thành: chọn giá trị tham số, chọn độ rộng, đổi mức song song,
hoặc đổi miền FFT/NTT. Bốn điều này không đồng nghĩa nhau.

## 6. Feature matrix để tự điền sau khi đọc

| Paper | FFT/NTT cùng bitstream? | FFT runtime precision? | q runtime? | NTT width đổi runtime? | Lane tăng khi width giảm? | Memory có packing theo width? | Code? |
|---|---|---|---|---|---|---|---|
| P1 | Có | Không mô tả | Chọn hai mode PQC | Theo mode | Có theo mode | Có theo mode | Chưa xác minh |
| P2 | Tool chọn FFT hoặc NTT | Không mô tả | Có trong cấu hình hỗ trợ | Datapath theo q lớn nhất | Không trong datapath đã đọc | Chưa thấy runtime width packing | Có repo |
| P3 | Không phải transform accelerator | — | — | — | Có cho arithmetic DNN | Có | Chưa xác minh |
| P4 | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Xác minh |
| P5 | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Xác minh |
| P6 | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Điền dẫn chứng | Có repo |
| N1–N3 | Chỉ điền sau khi có đủ bằng chứng | | | | | | |

Dùng “không mô tả” hoặc “chưa xác minh” thay cho “không có” nếu chưa đủ dữ liệu.
Số PE vật lý có thể cố định dù số lane/butterfly logic thay đổi theo mode.

## 7. Bài tập tổng hợp trước khi chốt kiến trúc

### Vòng 1 — Hiểu ba chiều linh hoạt

Sau P1/P2/P5, tự giải thích bằng một ví dụ:

- đổi q nhưng giữ width;
- đổi width nhưng giữ số PE/lane;
- đổi width đồng thời đổi grouping và số lane.

Chỉ ra twiddle, reducer và memory cần thay đổi gì trong mỗi trường hợp.

### Vòng 2 — Tự tính chi phí

Sau P3/P4:

- Tách phép nhân 64×64 thành tích riêng 32×32.
- Tách phép nhân 128×128 tương tự.
- Từ đó lập lịch với 2/4/8 đơn vị nhân, không giả định ghép hai đơn vị là đủ giữ throughput.
- Mở rộng sang nhân phức, rồi thêm modular reduction.
- Tính riêng giới hạn arithmetic, twiddle, read và write; lấy bottleneck toàn lõi.
- Phân biệt “bit ít hơn nên dùng ít tài nguyên khi tổng hợp” và “cùng bitstream nhưng chạy nhiều lane hơn”.

### Vòng 3 — Định vị đóng góp

Sau nhóm N:

- Mỗi khác biệt đề xuất có đối thủ gần nhất nào?
- Lợi ích có đến từ cơ chế mới hay chỉ tăng K/băng thông?
- Có workload thực sự cần các width/modulus được chọn không?
- Có baseline cùng functionality và cùng ngân sách phù hợp không?
- Chi phí reduction/memory có làm mất lợi ích ghép/tách không?

Đầu ra trước RTL: related-work matrix có dẫn chứng, numeric contract ban đầu,
một sơ đồ grouping, một lịch butterfly và mô hình băng thông. Chỉ sau đó mới khóa
cấu hình triển khai và sửa PLAN theo các kết luận có bằng chứng.
