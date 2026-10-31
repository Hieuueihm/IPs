# FlexTransform: Unifying Multi-Precision FFT and NTT Acceleration

> Kế hoạch nghiên cứu và triển khai — cập nhật ngày 21/10/2026.
> Mục tiêu: bài kiến trúc phần cứng 4–6 trang, có **RTL độc lập công nghệ**, kiểm chứng,
> kết quả hiện thực trên FPGA và tổng hợp generic để chứng minh tính khả chuyển.
> Ước lượng: 18 tuần cho một người toàn thời gian, thêm khoảng 2 tuần dự phòng.
> Trạng thái: đã thống nhất hướng nhiều PE có thể ghép/tách runtime; các con số tài nguyên,
> latency, băng thông và hiệu năng dưới đây là mô hình hoặc ứng viên khảo sát, chưa phải kết quả đo.

## 1. Mục tiêu và câu hỏi nghiên cứu

Xây dựng một lõi FFT/IFFT và NTT/INTT dùng chung tài nguyên số học và bộ nhớ.
Ở mode hẹp, các nhóm PE xử lý nhiều butterfly độc lập. Ở mode rộng, nhiều PE hợp tác
tính các tích riêng của cùng một butterfly, có thể qua nhiều lượt cấp việc.

Hai chiều linh hoạt của lõi:

1. **Precision FFT:** chọn fixed-point 64 hoặc 128 bit cho mỗi thành phần thực/ảo.
2. **Miền số học:** chọn số phức fixed-point hoặc số học chính xác modulo 12289.

Câu hỏi nghiên cứu chính:

> Một mảng PE có thể ghép/tách theo độ rộng có phục vụ cả FFT đa precision lẫn NTT
> hiệu quả hơn các phương án tài nguyên cố định, sau khi tính đủ chi phí gom tích riêng,
> kết nối và bộ nhớ hay không?

Falcon là case study và nguồn workload; tính mới của đề tài nằm ở kiến trúc lõi.
Chưa đặt điều kiện phải tăng tốc trọn bộ keygen hoặc signing mới được coi là hoàn thành.

### 1.1 Động lực ứng dụng

| Workload | Nhu cầu số học | Vai trò trong đánh giá |
|---|---|---|
| FFT phân tích tín hiệu | Precision theo yêu cầu sai số và dải động | Thể hiện khả năng dùng FFT ở nhiều cấu hình |
| Phần FFT của NTRUGen | Reference đã có fixed-point 64 bit, 32 bit lẻ [R7] | Nguồn workload thực tế cho mode FFT64 |
| Phần FFT của bản ký Falcon fixed-point | Có implementation dùng Q64.64 [R8] | Nguồn workload precision rộng; không mặc định 128 bit là tối thiểu |
| Nhân đa thức/verify Falcon | NTT modulo 12289 [R9] | Đánh giá đường số học chính xác |

Ví dụ nền tảng: một thiết bị vừa xử lý tín hiệu cảm biến, vừa ký báo cáo và kiểm tra chữ ký.
Đây là kịch bản động lực, không phải yêu cầu triển khai cả ứng dụng cảm biến hoặc giao thức.

### 1.2 Đã thống nhất và còn phải khảo sát

| Hạng mục | Trạng thái |
|---|---|
| Lõi dùng chung FFT/IFFT và NTT/INTT | Đã thống nhất |
| Nhiều PE; PE có thể hợp tác tạo phép tính rộng | Đã thống nhất |
| FFT64, FFT128 và NTT mod 12289 | Tập mode xuất phát |
| Một lệnh chọn một mode chung cho cả mảng | Phạm vi cơ sở; không trộn nhiều mode đồng thời |
| Memory-based với nhiều PE, xử lý theo stage | Điểm xuất phát theo phương án B đã thảo luận |
| Radix-2, CT thuận và GS nghịch | Phương án cơ sở để lập model; khóa sau khi xác định thứ tự dữ liệu |
| K = 32 bộ nhân cơ sở 32×32 | Ứng viên ban đầu, không phải cấu hình FPGA đã chốt |
| In-place; bộ nhớ chia bank; băng thông mục tiêu 512 bit | Ứng viên, phải chứng minh lịch truy cập |
| Word 512 bit, ánh xạ XOR cụ thể, số bank vật lý | Chưa chốt |
| RTL độc lập công nghệ; không instantiate primitive của nhà sản xuất trong lõi (mục 5.7) | Đã thống nhất |
| Board FPGA để đánh giá | Chưa chốt; chỉ cần trước P6, không ràng buộc kiến trúc RTL |
| Ghép nhóm cố định lân cận | Ưu tiên khảo sát trước mạng ghép tùy ý |
| Mọi mode có cùng latency | Không bắt buộc; điều khiển bằng metadata và valid/ready |

## 2. Phạm vi bài đầu

### 2.1 Bắt buộc

- FFT/IFFT phức thông thường cho N = 2^logN, ban đầu logN = 1…10.
- Hai mode FFT64 và FFT128 trên cùng RTL và cùng bitstream.
- NTT/INTT modulo 12289, N = 2…1024; chốt biểu diễn hệ số và quy ước transform.
- Ghép/tách PE thực sự thay đổi cách cấp việc và gom kết quả.
- Bộ nhớ, đường twiddle và điều khiển phục vụ cả ba mode.
- Phép nhân từng điểm cho số phức và modulo để kiểm tra luồng nhân đa thức.
- Mô hình số học bit-accurate, mô hình lịch thực thi và testbench tự kiểm tra.
- Tổng hợp/place-and-route trên một FPGA cụ thể; đo chu kỳ và tài nguyên.
- Cùng RTL tổng hợp thêm bằng một luồng generic (Yosys; tùy chọn OpenROAD với PDK mở)
  để chứng minh lõi không phụ thuộc nhà sản xuất.
- Đánh giá chi phí của tính linh hoạt và ảnh hưởng của tổ chức bộ nhớ.

### 2.2 Case study Falcon, sau khi lõi cơ sở hoạt động

- Adapter biểu diễn FFT riêng của Falcon; không đồng nhất FFT Falcon với DFT thông thường.
- Vector hoặc trace FFT/IFFT và NTT/INTT của reference.
- Nhân đa thức modulo q và kiểm tra tích hợp verifier nếu có sẵn reference chạy được.
- Thay một tập kernel FFT trong reference bằng model/core, đo lợi ích của đúng phần đã thay.
- Báo cáo riêng kết quả kernel và kết quả ứng dụng; không suy ra tăng tốc toàn bộ Falcon từ kernel.
- Nếu thử signing fixed-point: giữ các điều kiện về khóa, scaling và sai số của implementation tham chiếu.

### 2.3 Mở rộng có điều kiện

- PW_ADD, PW_SUB, MUL_ADJ, SPLIT, MERGE phục vụ trace Falcon.
- Twiddle hẹp hơn toán hạng; nhân cắt bớt tích riêng với quy tắc carry/làm tròn đã chứng minh.
- Cây gom tích riêng gộp phép nhân phức.
- Backend chuyên biệt FPGA cho cây gom (V2, DSP cascade), đối chiếu V1 generic;
  nằm ngoài lõi, không đổi giao diện (mục 5.7).
- Hàng đợi lệnh để giảm chi phí điều khiển các transform nhỏ.

### 2.4 Ngoài phạm vi cơ sở

- RECIP, division, sqrt, block exponent tự động.
- NTRUSolve số nguyên lớn, RNS nhiều prime, keygen đầy đủ.
- SamplerZ và ffSampling hoàn toàn trong FPGA.
- Modulus tùy ý, ML-KEM/ML-DSA hoặc NTT31 nếu chưa được triển khai và kiểm chứng.
- Floating-point IEEE-754, precision tùy ý, hoặc đổi mode giữa chừng một transform.
- Trộn nhiều job/precision khác nhau đồng thời trên các PE.
- Masking, TVLA và tuyên bố an toàn side-channel đầy đủ.

Các mục mở rộng không được âm thầm trở thành điều kiện hoàn thành của lõi cơ sở.

## 3. Giả thuyết đóng góp và đối chiếu công trình trước

### 3.1 Những gì không tuyên bố là mới

- FFT/NTT dùng chung phần cứng: đã có [R2, R3, R4, R5].
- FFT đa precision hoặc phép ghép/tách đơn vị tính toán: đã có tiền lệ [R1, R11].
- FFT Q32.32 trong keygen NTRU/Falcon: đã có trong NTRUGen [R7].
- Chỉ tăng độ rộng lên 128 bit, thêm mux mode, AXI hoặc thêm số PE.
- Chỉ ghép các IP FFT và NTT riêng vào cùng wrapper.

### 3.2 Đóng góp cần kiểm chứng

1. **Một cơ chế ghép/tách nhóm PE thống nhất** cho FFT ở hai độ rộng và NTT.
2. **Gom tích riêng và xử lý fixed-point đúng quy tắc**, có thể phân đoạn theo nhóm độc lập.
3. **Lịch cấp việc và layout bộ nhớ theo mode** giúp phần song song tính toán có ích trong toàn lõi.
4. **Đánh giá định lượng**: lợi ích, overhead và các giới hạn khi so cùng precision, N, FPGA và tài nguyên.

Không dùng từ “đầu tiên” khi chưa hoàn thành rà soát tài liệu. Danh sách trên là giả thuyết
đóng góp, không phải novelty đã được chứng minh. Một tổ hợp tính năng chưa thấy trùng hoàn toàn
vẫn có thể bị đánh giá là incremental nếu không có cơ chế hoặc kết quả đủ thuyết phục.

### 3.3 Ma trận related work

| Nguồn | Điểm đã xác nhận | Điều cần đối chiếu thêm |
|---|---|---|
| BitFusion, ISCA 2018 [R1] | Ghép/tách đơn vị tính theo bitwidth cho DNN | Tiền lệ composability; không phải FFT/NTT |
| Unified FFT/NTT, ICASSP 2025 [R2] | FFT fixed-point 32 bit và NTT ML-KEM/ML-DSA trên tài nguyên chung | Khác biệt của nhiều precision cho chính FFT |
| Aloha-HE, DATE 2024 [R3] | Chia sẻ số học floating-point/modulo, RTL FPGA công khai | Mức chia sẻ, bộ nhớ, lịch thực thi |
| ABC-FHE [R4] | Fourier engine streaming, FFT FP55 và modulo 44 bit | Đổi miền số học so với đổi precision FFT runtime |
| Unified NTRU/Falcon, ISCAS 2025 [R5] | FFT/NTT; NTT 64 bit radix-4 và 128 bit radix-2 | Đã đọc abstract; cần toàn văn trước kết luận về dataflow/precision |
| OpenNTT [R6] | Kiến trúc iterative nhiều PE, bank memory, sinh twiddle | FFT/NTT chọn khi sinh lõi; không coi là đổi miền runtime |
| Fused FP64/modular, ICTA 2026 [R10] | Abstract có ghép bộ nhân 14 bit cho FP64 và tách lane NTT | Đối thủ gần; cần đọc toàn văn, không suy diễn phần chưa công bố |
| ZK-Flex [R12] | Multi-precision và chia sẻ tài nguyên cho ZKP | Tiền lệ bổ sung về mảng tính toán; kiểm tra kiến trúc đầy đủ |

Đầu ra Phase 0: docs/related_work.md, gồm phần đã đọc toàn văn, phần chỉ có abstract,
feature matrix, nguồn số liệu và khoảng trống nghiên cứu còn có thể bảo vệ.

## 4. Định nghĩa số học trước khi thiết kế PE

### 4.1 Format và độ rộng

| Mode | Thành phần thực/ảo hoặc hệ số | Biểu diễn cơ sở |
|---|---|---|
| FFT64 | W = 64 bit mỗi thành phần | Signed Q32.32 |
| FFT128 | W = 128 bit mỗi thành phần | Signed Q64.64 |
| NTT12289 | Hệ số lưu trong 16 bit | Canonical 0…12288 |

Quy ước QI.F: I gồm cả bit dấu, tổng W = I + F. Một số phức chiếm 2W bit.
128 bit là độ rộng mỗi thành phần, không phải tổng của cả số phức.

Độ rộng hệ số lưu trữ khác với độ rộng trung gian. Sản phẩm, tổng butterfly và carry
phải có guard bits; không cắt sớm theo độ rộng lưu trữ.

### 4.2 Phép nhân và làm tròn FFT

- Model tham chiếu số nguyên arbitrary-precision tính đầy đủ tích và tổng.
- Quy tắc cơ sở: round-to-nearest, ties-to-even khi đưa sản phẩm về format đầu ra.
- Nhân phức cơ sở: tính chính xác Re = ac − bd và Im = ad + bc, rồi làm tròn mỗi thành phần.
- Giữ tối thiểu 2W+1 bit có dấu cho tổng/hiệu của hai sản phẩm đầy đủ; kiểm tra lại bound
  tại mọi nút của cây gom, nhất là khi biểu diễn tích riêng unsigned/signed.
- Phép cộng/trừ butterfly dùng W+1 bit trước khi scale/ghi kết quả.
- Stage scaling có cấu hình nhưng là lịch công khai, xác định trước; chốt thứ tự
  cộng, scale và làm tròn trong docs/numeric_contract.md.
- Overflow phải được phát hiện và báo lỗi trong chế độ kiểm chứng.
  Không dùng saturation để che tràn rồi vẫn báo một phép FFT mật mã hợp lệ.
- Nếu thêm saturation cho workload DSP, đó là một semantics riêng, có mode và phép thử riêng.

Rounding một lần cho nhân phức có thể khác reference làm tròn từng phép nhân thực.
Do đó, model bit-accurate phải mô tả chính xác lõi; adapter phải đánh giá sai số hoặc dùng
semantics tương thích reference. Không hứa bit-match với phần mềm chỉ vì cùng Q-format.

### 4.3 Twiddle

**Cơ sở để tính chi phí:** twiddle và dữ liệu cùng độ rộng W và cùng số bit lẻ F.
Cách này cho một reference rõ ràng, chưa phải lựa chọn ROM tối ưu.

Ứng viên tối ưu kế thừa từ PLAN cũ:

- FFT64: dữ liệu Q32.32, twiddle Q2.30, phép nhân 64×32.
- FFT128: dữ liệu Q64.64, twiddle Q2.62, phép nhân 128×64.

Chỉ bật ứng viên này sau khi đo và phân tích riêng sai số lượng tử hóa twiddle.
Dữ liệu có 64 bit lẻ không có nghĩa twiddle 62 bit lẻ tự động đáp ứng mọi yêu cầu.

Sinh twiddle bằng tính toán precision cao; lượng tử hóa theo hợp đồng số học;
lưu kèm hash, tham số, thứ tự root và quy tắc làm tròn để tái lập vector.
ROM đầy đủ là phương án đầu; compression và sinh twiddle on-the-fly là nhánh mở rộng.

### 4.4 NTT/INTT

- q = 12289; root, normalization và ordering phải có bảng cho từng N.
- Dùng reduction chính xác; baseline chọn một thuật toán có miền đầu vào và bound hiệu chỉnh rõ ràng.
- Montgomery hoặc Barrett là ứng viên; nếu dùng Montgomery, mô tả rõ chuyển vào/ra miền.
- Không suy ra “reduction chỉ cộng/dịch và một lần hiệu chỉnh” chỉ từ dạng q = 3·2^12 + 1.
- Nếu dùng reduction chuyên biệt q, phải dẫn xuất công thức, số bước và bound trung gian.
- Cơ sở lưu hệ số canonical; lazy reduction chỉ thêm sau khi chứng minh bound và lợi ích.
- INTT phải có nhân N^(-1) mod q đúng vị trí, đúng miền số học.

### 4.5 Quy ước transform và adapter

- LOGN là log2 của số điểm thực sự đưa vào engine, không luôn là log2 bậc đa thức Falcon.
- FFT thông thường: đặc tả dấu mũ, input/output order và hệ số chuẩn hóa IFFT.
- NTT negacyclic: đặc tả twist hoặc root schedule tương ứng với phép nhân modulo x^N+1.
- Falcon lưu một nửa số embedding phức; n = 512/1024 không đồng nghĩa FFT phức thông thường
  có cùng số điểm. Adapter phải theo đúng reference, root order và layout thực/ảo.
- Identity/bypass cho transform 1 điểm được đặc tả riêng nếu adapter cần; không đưa vào
  công thức logN stage như một phép butterfly.

## 5. Kiến trúc mảng PE có thể ghép/tách

### 5.1 Ba cấp để tránh nhập nhằng tên PE

1. **uPE:** đơn vị cơ sở có một bộ nhân 32×32, thanh ghi và metadata tích riêng.
2. **Cụm PE:** một nhóm uPE có operand routing và bộ gom cục bộ.
3. **Logical butterfly PE:** tài nguyên được scheduler gán cho một butterfly hoàn chỉnh;
   số uPE và số lượt cấp việc phụ thuộc mode.

Trong mode hẹp, nhiều logical butterfly PE độc lập. Trong mode rộng, nhiều cụm PE
cùng tham gia một logical butterfly PE. Đây là ghép tài nguyên số học giữa các PE,
không phải chỉ gửi cùng lệnh cho nhiều PE có bộ nhân rộng riêng biệt.

### 5.2 Sơ đồ chức năng

~~~
                  Lệnh / cấu hình đã chốt
                           |
       +-------------------+-------------------+
       | Stage scheduler / group mapper        |
       | địa chỉ, group_id, phase, valid mask   |
       +------------+--------------------------+
                    |
       Banked data RAM <--> Read router / unpack
                                  |
                    Operand buffers + twiddle ROM
                                  |
                       Limb distribution network
                                  |
             +--------------------+--------------------+
             | Cụm PE0            | Cụm PE1            |
             | nhiều uPE 32x32    | nhiều uPE 32x32    | ...
             +--------------------+--------------------+
                                  |
                Local reduction / inter-cluster combine
                                  |
               FFT rounding + add/sub / NTT reduction
                                  |
                       Write router / pack
                                  |
                         Banked data RAM
~~~

NTT có thể bypass phần ghép số rộng, nhưng vẫn cần đủ reduction/add-sub lanes cho
mức song song thực tế. Không coi những khối phụ trợ đó là tài nguyên miễn phí.

### 5.3 Ghép phép nhân rộng

Với cơ số B = 2^32:

A = Σ a_i·B^i, B_op = Σ b_j·B^j,
A·B_op = Σ (a_i·b_j)·B^(i+j).

- Limb thấp là unsigned; limb cao nhất mang dấu khi biểu diễn số signed.
- Mỗi tích riêng phải được zero-extend hoặc sign-extend đúng trước khi gom.
- Mỗi uPE nhận operand limbs, signedness, vị trí dịch, dấu đóng góp và group_id.
- Việc hai PE hợp tác không có nghĩa số chu kỳ giữ nguyên khi độ rộng tăng gấp đôi.

Baseline dùng schoolbook và bốn phép nhân thực cho một phép nhân phức.
Karatsuba/nhân phức ba phép nhân chỉ khảo sát sau; phải tính cả tăng độ rộng của tổng đầu vào.

### 5.4 Số tích riêng: mô hình chi phí, không phải throughput đo

Gọi Ld = ceil(W_data/32), Lt = ceil(W_twiddle/32).
Chi phí nhân cho một complex multiply thông thường là Cmul = 4·Ld·Lt tích riêng.

| Cấu hình | Nhân thực | Tích riêng / nhân phức | K = 32: trần tính toán |
|---|---|---:|---|
| FFT64 cơ sở | 64×64 | 16 | 2 butterfly / chu kỳ cấp việc |
| FFT128 cơ sở | 128×128 | 64 | 1 butterfly / 2 chu kỳ cấp việc |
| FFT64 twiddle hẹp, tùy chọn | 64×32 | 8 | 4 butterfly / chu kỳ cấp việc |
| FFT128 twiddle hẹp, tùy chọn | 128×64 | 32 | 1 butterfly / chu kỳ cấp việc |
| NTT12289 | 14×14, lưu lane 16 bit | 1 / modular multiply | Tối đa 32 butterfly / chu kỳ cấp việc |

Các trần trên giả sử mỗi uPE nhận một tích riêng mỗi chu kỳ và không có bottleneck khác.
Chưa gồm pipeline, cây gom, reducer, bộ nhớ, twiddle, scale và drain giữa stage.
PW_MUL phức có hai toán hạng đầy đủ; không dùng dòng twiddle hẹp để ước tính PW_MUL.

### 5.5 Lịch minh họa cho K = 32

Cơ sở: hai cụm PE, mỗi cụm 16 uPE.

- **FFT64:** mỗi cụm nhận một butterfly độc lập; mỗi cụm tính bốn tích thực 64×64.
- **FFT128:** ghép cả hai cụm cho một butterfly:
  - lượt 0: 16 tích riêng của ac và 16 tích riêng của bd;
  - lượt 1: 16 tích riêng của ad và 16 tích riêng của bc;
  - gom Re/Im, làm tròn và hoàn tất butterfly.
- **NTT:** uPE nhận các modular multiply độc lập; số lane bật phụ thuộc bộ nhớ và reducer.

Ở FFT128, các lượt của cùng butterfly có cùng tag; không cho kết quả của hai job lẫn nhau.
Lịch này minh họa khả năng ghép cả hai cụm, chưa giả định mọi lượt đã có kết quả sau một cycle.
K = 16, 32, 64 được khảo sát bằng model trước khi quyết định cấu hình đưa lên FPGA.

### 5.6 Mạng ghép và cây gom

Ưu tiên nhóm lân cận, kích thước lũy thừa hai; chỉ đặt đường nối cần cho các mode đã hỗ trợ.

- V1 cơ sở: dựng đầy đủ từng sản phẩm thực, sau đó cộng/trừ nhân phức theo numeric contract.
- V1 tối ưu: gom trực tiếp các tích riêng có trọng số và dấu vào cây Re/Im.
- Cây có ranh giới nhóm, accumulator và valid mask độc lập.
- Nếu dùng adder segmented: chặn carry qua ranh giới nhóm; nếu dùng cây con riêng,
  không giả định mọi phép ghép đều thực hiện được bằng một tín hiệu chặn carry.
- Định tuyến group_id và phase đi cùng dữ liệu; nhóm chưa đủ tích riêng không được commit.
- So sánh cây trực tiếp, pipeline theo tầng và local-reduce rồi global-reduce.
- Không chốt số ngõ mux hoặc số DSP trước khi có mapping và synthesis.

**V2 DSP cascade (backend FPGA, tùy chọn):** nhánh thử nghiệm sau V1, đặt trong `hdl/tech/fpga/`
và thay thế V1 qua cùng giao diện; lõi chính luôn dùng V1 generic. DSP48E1/E2 phụ thuộc board và có độ rộng,
đường cascade, placement cùng chế độ điều khiển cụ thể. Không coi chuỗi cascade là một
bộ cộng 128/256 bit có thể tùy ý cắt/nối runtime. Phải đọc tài liệu đúng thiết bị,
làm microbenchmark và chứng minh bit-accurate trước khi đưa vào lõi.

### 5.7 Nguyên tắc RTL độc lập công nghệ

Kiến trúc được thiết kế theo nhu cầu số học và dữ liệu, không theo hình dạng DSP/BRAM của một board.

- **Bộ nhân:** `upe_mul32.v` viết bằng phép nhân hành vi có tham số độ rộng (hoặc ghép phân cấp
  từ các leaf hành vi); công cụ tự ánh xạ sang DSP trên FPGA hoặc bộ nhân Booth/Wallace trên ASIC.
- **Bộ nhớ:** RAM qua wrapper hành vi (`ram_1r1w.v`, `ram_2p.v`) để công cụ suy ra BRAM
  hoặc thay bằng SRAM macro; không instantiate primitive trực tiếp trong lõi.
- **Tham số hóa:** K, W, độ rộng limb/leaf, số bank, độ sâu pipeline; không mã hóa cứng 27×18, 17 bit, v.v.
- **Lớp công nghệ tách riêng:** `hdl/tech/<target>/` chỉ chứa wrapper tùy chọn (DSP cascade,
  RAM macro); thay thế qua cùng giao diện, lõi tổng hợp được khi không có thư mục này.
- **Kiểm tra khả chuyển:** từ P4, mỗi khối số học tổng hợp trên ít nhất hai target
  (công cụ FPGA + Yosys generic); lint quy tắc “không primitive vendor trong `hdl/`”.
- **Kích thước leaf của uPE:** mặc định 32×32; P2 so sánh với leaf 16×16 ghép phân cấp
  bằng tổng hợp generic, không bằng số DSP của một thiết bị.

Số liệu FPGA trong bài là một hiện thực của kiến trúc, không phải định nghĩa của kiến trúc.

## 6. Bộ nhớ và băng thông theo mode

### 6.1 Mô hình cơ sở

Lõi có data RAM nhiều bank và đường twiddle riêng.
Cấu hình xuất phát để đánh giá là 512 bit đọc và 512 bit ghi mỗi chu kỳ ở cấp lõi;
đây không phải cam kết AXI hoặc DRAM đạt cùng băng thông.

Một ứng viên là 32 bank logic × 16 bit; ứng viên khác là 16 bank × 32 bit có packing
hệ số NTT. Bank viết qua wrapper RAM hành vi (mục 5.7); cần đo BRAM fragmentation, cổng
và write-enable khi ánh xạ lên FPGA thật, và kiểm tra wrapper vẫn suy ra được SRAM ở luồng generic.

### 6.2 Băng thông dữ liệu của một lô butterfly

| Mode | Dữ liệu đọc / butterfly | K = 32, 512 bit đọc/ghi: trần dữ liệu |
|---|---:|---|
| FFT64 | 2 số phức × 128 bit = 256 bit | 2 butterfly / chu kỳ |
| FFT128 | 2 số phức × 256 bit = 512 bit | 1 butterfly / chu kỳ; tính toán cơ sở chỉ đạt 0,5 |
| NTT16 | 2 hệ số × 16 bit = 32 bit | 16 butterfly / chu kỳ |

Đường ghi có cùng lượng dữ liệu cho butterfly hai đầu ra.
Đường twiddle phải xét riêng: mỗi butterfly FFT cần một số phức, NTT cần một hệ số root;
có thể broadcast khi các butterfly thực sự dùng cùng root, không mặc định mọi lane đều dùng chung.

Ví dụ K = 32: cấu hình twiddle hẹp FFT64 có trần tính toán 4 nhưng trần dữ liệu 2.
NTT có trần nhân 32 nhưng trần dữ liệu 16. Đây là lý do phải khảo sát PE và bộ nhớ cùng nhau.

### 6.3 Layout và lịch truy cập

Cần có bảng (mode, stage, batch) -> (bank, row, lane) cho mọi operand và output.

- Chọn các butterfly trong một batch dựa trên cả độc lập dữ liệu và số cổng bank.
- Bao quát cặp cùng word, khác word, stride nhỏ và stride lớn.
- Phân biệt thời điểm đọc và thời điểm writeback sau pipeline.
- Kiểm tra read-after-write, write-after-write và read-during-write của BRAM.
- Nếu cần hoán vị giữa stage, tính cả chu kỳ, băng thông và chi phí mạng hoán vị.
- Không khẳng định ánh xạ XOR là conflict-free trước khi kiểm tra đầy đủ.
- Stage nhỏ có thể không đủ butterfly để lấp đầy mọi PE; scheduler phải hỗ trợ tail mask.
- Bắt đầu với in-place. Nếu khó bảo đảm lịch, đánh giá ping-pong như một baseline:
  đổi thêm dung lượng RAM lấy đơn giản hóa hazard; báo cáo rõ chi phí.

### 6.4 Thay precision và định dạng dữ liệu

Mode chỉ thay giữa các lệnh; mỗi buffer có metadata về format, số điểm và trạng thái hợp lệ.

- Không diễn giải lại buffer FFT64 như FFT128 bằng cách chỉ đổi MODE.
- Nếu cần chuyển giá trị Q32.32 sang Q64.64, phải sign-extend và đổi scale chính xác.
- Chiều hẹp lại cần làm tròn và kiểm tra overflow.
- Bản đầu có thể chuyển format ở host; nếu thêm hardware CONVERT, đo riêng chi phí.
- Giao diện host dùng little-endian limbs 32 bit; real/imag interleaved.
  Layout nội bộ được phép khác nhưng phải có pack/unpack xác định và kiểm chứng.

## 7. Điều phối toàn lõi

### 7.1 Chính sách cơ sở

- Một job đang hoạt động, một mode chung cho toàn mảng.
- Ghép/tách nhóm cố định trong suốt lệnh; không ghép tùy ý giữa chừng butterfly.
- Cùng clock cho các PE; không cần nhiều miền clock để thay precision.
- Latency và initiation interval được đặc tả riêng theo mode và OP.
- Không chèn delay để ép mọi mode có cùng latency nếu điều đó không đem lại lợi ích đo được.

### 7.2 Chu trình lệnh

1. Kiểm tra MODE, OP, LOGN, buffer, alignment và các tổ hợp được hỗ trợ.
2. Snapshot cấu hình; thiết lập group map, twiddle set và lịch scale.
3. Sinh địa chỉ của stage và chọn batch không xung đột.
4. Fetch dữ liệu/twiddle; giữ trong operand buffers nếu cần nhiều lượt.
5. Issue tích riêng theo group_id và phase; cập nhật scoreboard.
6. Reduce, round/modred, cộng/trừ butterfly và scale theo hợp đồng.
7. Writeback đúng tag; đánh dấu kết quả đã commit.
8. Kết thúc stage khi mọi dependency cho stage sau đã an toàn.
9. Chuẩn hóa cuối transform theo semantics; kết thúc lệnh.
10. Drain mọi đường cũ trước khi commit mode của lệnh kế tiếp.

INTT và IFFT có chuẩn hóa khác nhau. Các công thức thuận/nghịch, root, ordering,
scale N^(-1) hoặc 1/N phải được mô tả và test riêng.

### 7.3 Metadata và invariants

Metadata tối thiểu: job_id, mode, stage_id, butterfly_id, group_id, product_id,
phase_id, valid mask và địa chỉ đích.

Invariants kiểm tra bằng assertion/model:

- Một uPE không nhận hai phép khác nhau trong cùng chu kỳ.
- Mỗi tích riêng được issue và gom đúng một lần.
- Không có carry hoặc accumulator state rò sang nhóm độc lập.
- Không writeback trước khi đủ tích riêng hoặc khi tag không còn hợp lệ.
- Stall giữ nguyên toàn bộ dữ liệu và metadata liên quan.
- Lệnh lỗi không được âm thầm tạo DONE thành công.
- Reset hủy tags/inflight state; dữ liệu ghi dở không được coi là kết quả hợp lệ.

Latency cố định theo lệnh và mode là mục tiêu của controller, không đủ để tuyên bố
toàn hệ thống constant-time hoặc không có side-channel. Nếu dùng lịch thích nghi
theo giá trị dữ liệu phải xem là thay đổi phạm vi và phân tích riêng.

## 8. Golden model, mô hình chu kỳ và cấu trúc mã

Ba model tách biệt:

1. **Math reference:** DFT/FFT precision cao, NTT số nguyên chính xác.
2. **Bit-accurate model:** đúng signedness, rounding, overflow, twiddle và scaling của RTL.
3. **Cycle/schedule model:** PE grouping, bank access, pipeline, stall, tail và switch mode.

Bit-accurate khớp RTL chưa chứng minh numeric contract đủ tốt; phải so cả với math reference.

~~~
NTRU/
├── PLAN.md
├── ref/                         # Reference bên ngoài, giữ nguyên và pin revision
├── algorithm/
│   ├── fixed.hpp                # Arithmetic fixed-point và flags
│   ├── fft_fx.cpp               # FFT/IFFT bit-accurate
│   ├── ntt.cpp                  # NTT/INTT, normalization, pointwise
│   ├── complex_ops.cpp
│   ├── falcon_adapter.cpp       # Case study, sau lõi cơ sở
│   └── vecgen.cpp
├── model/
│   ├── math_reference.py        # Arbitrary/high precision
│   ├── pe_mapping.py
│   ├── bank_schedule.py
│   └── cycle_model.py
├── study/
│   ├── configs/                 # K, bank geometry, formats, pipeline
│   ├── vectors/
│   └── results/                 # CSV có seed/config hash
├── hdl/
│   ├── upe_mul32.v
│   ├── pe_cluster.v
│   ├── operand_route.v
│   ├── pp_reduce.v
│   ├── complex_round.v
│   ├── fft_addsub.v
│   ├── modred_12289.v
│   ├── ntt_addsub.v
│   ├── group_mapper.v
│   ├── stage_scheduler.v
│   ├── addr_gen.v
│   ├── mem_banks.v
│   ├── read_write_router.v
│   ├── twiddle_rom.v
│   ├── ram_1r1w.v / ram_2p.v    # Wrapper RAM hành vi, suy ra BRAM/SRAM
│   ├── fftntt_core.v            # Giao diện lõi generic (valid/ready + thanh ghi)
│   ├── fftntt_axil_slave.v      # Adapter host AXI4-Lite, tách khỏi lõi
│   └── tech/                    # Tùy chọn: wrapper chuyên biệt (fpga/, asic/)
├── sim/src/                     # Unit/integration testbenches và assertions
├── sim/work/                    # Output sinh ra, không coi là nguồn
├── scripts/                     # Build, sim, sweep, synthesis, parse reports
├── sw/                          # Driver và host benchmark
└── docs/
    ├── related_work.md
    ├── numeric_contract.md
    ├── pe_mapping.md
    ├── memory_schedule.md
    ├── arch.md
    ├── verification.md
    ├── results.md
    └── plan_history/
~~~

Dùng API phần mềm độc lập backend để có thể thay kernel mà không sửa reference gốc.
Lưu compiler/tool versions, reference revision, seeds và lệnh tái lập.

## 9. Giao tiếp host và bộ đếm đo

Bản đầu dùng AXI4-Lite cho control; dữ liệu qua BRAM controller hoặc DMA tùy board.
Không dùng tốc độ AXI4-Lite để đại diện hiệu năng mảng PE.

Register map đề xuất, 32 bit mỗi thanh ghi:

| Offset | Tên | Chức năng |
|---|---|---|
| 0x00 | CTRL | START, SOFT_RESET/ABORT, CLEAR_STATUS |
| 0x04 | MODE | FFT64 / FFT128 / NTT12289 |
| 0x08 | OP | FFT / IFFT / NTT / INTT / PW_CMUL / PW_MULMOD |
| 0x0C | LOGN | log2 số điểm engine |
| 0x10 | SRC_A | Buffer ID |
| 0x14 | SRC_B | Buffer ID, chỉ dùng cho OP hai nguồn |
| 0x18 | DST | Buffer ID |
| 0x1C | STATUS | BUSY, DONE, ERROR |
| 0x20 | SCALE_CFG | Lịch scale đã hỗ trợ; không phải số mũ block tự động |
| 0x24 | TWIDDLE_SET | Root/layout profile đã nạp |
| 0x28 | ERROR_CODE | Opcode/mode/length/buffer/overflow/protocol |
| 0x2C | CYCLE_COUNT | Chu kỳ thực thi lệnh, quy định rõ điểm bắt đầu/kết thúc |
| 0x30 | CAPABILITY | Version, K, mode và độ dài hỗ trợ |
| 0x34 | STALL_COUNT | Chu kỳ chờ dữ liệu hoặc tài nguyên |

Địa chỉ dữ liệu nằm trong một vùng riêng đã xác định dung lượng. Chỉ công bố cửa sổ
0x1000+ nếu implementation thật sự ánh xạ được vùng đó.

Đặc tả thêm: ghi config khi BUSY, hành vi START khi BUSY, sticky status, clear flags,
buffer aliasing/in-place, reset giữa lệnh và dữ liệu ghi dở.
Hàng đợi lệnh là mở rộng: dùng descriptor đầy đủ, không nhét cả lệnh vào một word 32 bit
khi số trường không đủ chỗ.

## 10. Thực nghiệm và baseline

### 10.1 Các cấu hình phải so sánh

| Mã | Cấu hình | Câu hỏi trả lời |
|---|---|---|
| S64 | FFT64 chuyên dụng | Overhead so với lõi hẹp |
| S128 | FFT128 chuyên dụng | Overhead so với lõi rộng |
| SN | NTT12289 chuyên dụng | Giá phải trả cho chia sẻ với FFT |
| SSEP | S64 + S128 + SN | Tổng tài nguyên nếu giữ ba chức năng riêng |
| WFIX | Đường FFT luôn dùng tài nguyên rộng, cùng semantics đầu ra khi so sánh | Lợi ích của ghép/tách theo precision |
| FUSE | Lõi đề xuất, K và memory configuration đã chốt | Hiệu quả toàn kiến trúc |
| FUSE-M | Cùng mảng số học, thay memory layout/scheduler | Đóng góp riêng của bộ nhớ |
| FUSE-R | Gom sản phẩm thực riêng so với gom trực tiếp nhân phức | Đóng góp riêng của cây gom |

Không bắt buộc triển khai mọi baseline ở mọi K nếu không cần để trả lời câu hỏi nghiên cứu.
Chốt ma trận thí nghiệm trước khi làm RTL để tránh viết nhiều lõi nhưng thiếu đối chiếu hữu ích.

Hai kiểu công bằng phải báo cáo tách biệt:

- **Cùng functionality:** tài nguyên tổng của các lõi riêng so với lõi hợp nhất.
- **Cùng ngân sách/throughput:** cùng K, BRAM/băng thông hoặc cùng tốc độ yêu cầu.
  Không vừa cho lõi đề xuất nhiều bộ nhân hơn, vừa kết luận tốt hơn do tính linh hoạt.

### 10.2 Workload và thông số

- N = 16, 64, 256, 512, 1024 cho bảng chính; mô phỏng thêm các N nhỏ và mọi stage.
- FFT64/FFT128: impulse, constant, single tone, random complex, gần triệt tiêu,
  dải động lớn, gần ngưỡng overflow và các điểm tie của rounding.
- NTT: zero, one, q−1, delta, random và nhân đa thức negacyclic.
- Cùng giá trị đầu vào hợp lệ ở cả hai precision để quan sát sai số và chi phí.
- Case study Falcon: vector/trace reference được pin, đánh giá đúng kernel đã hỗ trợ.
- Chuỗi nhiều job: FFT64 -> FFT128 -> NTT -> IFFT -> INTT; kiểm tra chi phí mode switch.

### 10.3 Số liệu bắt buộc

- LUT, FF, DSP, BRAM; clock constraints, achieved timing và WNS sau implementation.
- Chu kỳ/OP/mode/N; latency và initiation interval tách riêng.
- Tốc độ butterfly hoặc hệ số/giây; định nghĩa số điểm và layout rõ.
- Utilization của uPE, cụm PE, reducer và cổng RAM.
- Chu kỳ compute, memory stall, reduction, stage transition, fill/drain và mode switch.
- Sai số max absolute, relative khi reference khác 0, và relative L2/SQNR phù hợp.
- Overflow count và miền đầu vào đã khảo sát.
- Kernel-only, transfer và host orchestration time báo riêng.

Nếu báo power/energy: ghi rõ đo board hay estimate từ activity;
nêu stimulus, nguồn VCD/SAIF, clock và phương pháp. Không gọi power estimate là đo thực tế.
Không cộng LUT/DSP/BRAM thành một “area” tùy ý mà không giải thích trọng số.
Không so trực tiếp mm² ASIC với LUT FPGA như cùng một chỉ số.
Kết quả tổng hợp generic (cell area, timing với thư viện/PDK ghi rõ) báo cáo tách riêng,
dùng để so tương đối giữa các cấu hình và chứng minh tính khả chuyển.

### 10.4 Tiêu chí thành công

- Một RTL/bitstream chạy được cả ba mode và chiều thuận/nghịch.
- Mọi kiểm thử bit-accurate và truy cập bộ nhớ đã định nghĩa đều qua.
- Quan sát được PE ghép/tách đúng lịch; mode hẹp tạo thêm mức song song có ích
  trong ít nhất một cấu hình và workload đã chỉ rõ.
- Báo cáo đầy đủ overhead của fusion, cả trường hợp bị giới hạn bởi bộ nhớ.
- Có ít nhất một điểm đánh đổi tài nguyên/throughput/precision tốt hơn baseline phù hợp.
- Nếu chưa có lợi ích: xác định bottleneck và giới hạn kiến trúc; không tự đổi tiêu chí
  thành “chỉ cần chạy được ba mode là đủ novelty”.

## 11. Lộ trình và cổng quyết định

| Phase | Tuần | Công việc và đầu ra | Điều kiện hoàn thành |
|---|---|---|---|
| P0 — Scope và tài liệu | 1 | Related-work matrix; pin reference; chọn tool, target đánh giá (FPGA + generic) và ngân sách | Khoảng trống rõ, số liệu có nguồn, luồng tổng hợp chạy được |
| P1 — Số học và golden model | 2–3 | Numeric contract; FFT/IFFT, NTT/INTT, pointwise; twiddle/vector generator | NTT exact; FFT khớp high-precision theo hợp đồng và không tràn trong miền đã chọn |
| P2 — PE fusion model | 4–5 | **Phân tích uPE trước tiên** (mục 16); mapping K = 16/32/64; scheduler tích riêng; khảo sát cây gom | Mọi tích riêng có nơi đến, đủ guard bits; có bảng chi phí và cycle model |
| P3 — Memory và architecture spec | 6–7 | Bank/layout sweep, hazard simulation, quyết định group/memory | Có lịch hợp lệ mọi mode/stage; dự đoán throughput có tính stall |
| P4 — RTL số học | 8–10 | uPE, local/global reduction, rounding, modular path; synthesis microbench trên FPGA và Yosys generic | Bit-match model, groups độc lập, ghép mode rộng đúng; timing khả thi; không primitive vendor |
| P5 — Core FFT/NTT | 11–12 | Scheduler, RAM, twiddle, forward/inverse và pointwise | RTL khớp golden model cho mọi mode và N hỗ trợ |
| P6 — Giao tiếp và board | 13–14 | AXI wrapper, driver, transfer và reset/error handling | Cùng bitstream chạy chuỗi job đổi mode trên board |
| P7 — Đánh giá | 15–16 | Baselines, PPA, bottleneck, precision, Falcon kernel case study | Có kết quả tái lập và đủ đối chiếu cho từng đóng góp |
| P8 — Bài báo và artifact | 17–18 | Bản thảo, hình/bảng, scripts và hướng dẫn chạy | Claim khớp bằng chứng; artifact build/verify tái lập |

Viết numeric/architecture notes ngay trong từng phase; bản thảo có thể bắt đầu trước P8.
Dự phòng khoảng 2 tuần cho lỗi timing, mapping BRAM hoặc tích hợp board.

### Gate G0 — Sau P0: tính mới có thể bảo vệ

- Đọc toàn văn các đối thủ gần nếu truy cập được; ghi rõ nguồn chưa có toàn văn.
- Không tiếp tục chỉ với câu “chưa thấy ai kết hợp hai tính năng”.
- Nếu có bài trùng cơ chế, xác định khác biệt thực chất trước khi đầu tư RTL lớn.

### Gate G1 — Sau P1/P2: số học và ghép PE khả thi

- FFT128 chạy đúng với tích đầy đủ; không phụ thuộc twiddle hẹp mới đủ tài nguyên.
- K = 32 được phép dùng hai lượt cho butterfly rộng.
- Nếu cần K = 64 mới đạt mục tiêu throughput, kiểm tra board và chi phí trước khi chọn.
- Twiddle hẹp không đạt sai số -> giữ baseline đầy đủ, không bỏ mode FFT64.

### Gate G2 — Sau P3: PE và bộ nhớ cân bằng

- So sánh tốc độ có thể đạt với giới hạn compute/data/twiddle/writeback.
- Nếu bị memory-bound: chọn trong giảm K, tăng bank/băng thông hoặc sửa layout.
- Chỉ thay một yếu tố mỗi lần và ghi kết quả để tránh nhầm lợi ích fusion với tăng tài nguyên.
- Không khóa layout chỉ vì “word 512 bit chứa được đủ hệ số”.

### Gate G3 — Sau P4: timing và chi phí

- Có synthesis/implementation microbench cho multiplier, reducer và inter-cluster combine.
- Nếu đường global-reduce quá chậm: thêm pipeline hoặc chuyển sang local-then-global.
- V2 DSP cascade không khả thi -> bỏ nhánh V2, giữ V1; không để V2 chặn lõi chính.

### Gate G4 — Sau P7: claim của bài

- Có lợi ích và overhead rõ -> viết bài quanh cơ chế đã chứng minh.
- Chỉ có tính đúng, chưa có lợi ích -> xem lại mục tiêu hoặc cơ chế, chưa khẳng định đủ novelty.
- Falcon adapter chưa xong -> ghi giới hạn case study; không gọi lõi kernel là Falcon accelerator hoàn chỉnh.

## 12. Kế hoạch kiểm chứng

| Cấp | Kiểm tra cần có |
|---|---|
| Arithmetic | Zero, min/max signed, unsigned limbs, đổi dấu, carry, tie-to-even, overflow |
| Wide multiply | So toàn bộ kết quả với arbitrary-precision; random seed cố định và các pattern cực trị |
| Fusion | Tách nhóm/gom nhóm, K khác nhau, hai phase cùng tag, dữ liệu giữa nhóm không lẫn |
| Complex path | ac−bd/ad+bc, gần triệt tiêu, round đúng vị trí, scale từng stage |
| Modulo | Miền đầu vào, bound reducer, correction; exhaustive operand pair nếu chi phí cho phép |
| Scheduler | Không trùng uPE, không thiếu/lặp tích riêng, tail mask, stall/backpressure |
| Memory | Mọi mode/stage/N; kiểm tra số cổng, RAW/WAW và read-during-write |
| FFT/IFFT | RTL bit-match golden; so DFT/high-precision; roundtrip có bound, không đòi identity tuyệt đối |
| NTT/INTT | Roundtrip exact; convolution khớp schoolbook modulo x^N+1 |
| System | Lệnh không hợp lệ, reset/abort, buffer aliasing, đổi mode sau drain và status |
| FPGA | Vector khớp simulation; counter khớp schedule; lặp nhiều job không mất dữ liệu |

Nếu dùng simulator cụ thể, tránh tính năng testbench không hỗ trợ.
Chỉ công bố KAT đầy đủ khi đã chạy đúng harness/phiên bản reference;
NTT khớp bit không tự động đồng nghĩa cả verifier đã qua KAT.

Signing verify thành công hoặc một phép KS test không chứng minh phân phối lấy mẫu an toàn.
Nếu có kết quả signing, giới hạn kết luận theo điều kiện và bằng chứng của [R8].

## 13. Rủi ro và hướng xử lý

| Rủi ro | Hướng xử lý |
|---|---|
| Fusion FFT đa precision + NTT đã có bài sát | Rà soát R2/R4/R5/R10 và arithmetic composability trước RTL |
| Định nghĩa PE thay đổi giữa tài liệu | Dùng cố định uPE / cụm PE / logical butterfly PE trong code và hình |
| Nghĩ ghép hai PE sẽ giữ throughput khi tăng gấp đôi width | Dùng số tích riêng và initiation interval; tính đủ số lượt |
| Twiddle hẹp làm sai số lớn | Giữ full-width reference; đo sai số twiddle riêng và toàn transform |
| Gom nhân phức thay semantics reference | Giữ model định nghĩa rõ; có baseline gom sản phẩm thực riêng |
| Bộ nhớ không cấp đủ | Sweep bank/layout/batch; báo compute ceiling và achieved throughput riêng |
| BRAM fragmentation hoặc DSP vượt board | Synthesis sớm, chọn lại K/bank geometry trước RTL toàn lõi |
| Kiến trúc bị “uốn” theo DSP/BRAM của một board, mất tính tổng quát | Quy tắc mục 5.7; tổng hợp trên ≥ 2 target từ P4; tối ưu vendor chỉ trong `hdl/tech/` |
| Global routing hoặc cây gom làm giảm Fmax | Nhóm lân cận, local reduction, pipeline; đo sau place-and-route |
| NTT lane nhiều nhưng reducer ít | Model reducer throughput và cấp lane mask đúng tài nguyên thật |
| Mode switch làm lẫn kết quả | Drain + tag/scoreboard; test chuỗi mode và reset giữa job |
| Falcon chiếm hết thời gian | Core là deliverable chính; case study theo kernel, mở rộng có giới hạn |
| Timeline tăng do RECIP/cascade/on-the-fly twiddle | Chỉ mở nhánh sau khi cổng cơ sở qua; giữ kết quả nhánh như thí nghiệm riêng |

## 14. Bố cục bài báo dự kiến

1. Motivation: nhu cầu FFT đa precision và NTT trên cùng nền tảng.
2. Background/related work: phân biệt đổi miền số học, đổi precision và ghép PE.
3. Architecture: cấu trúc PE, group map, cây gom, số học và memory/scheduler.
4. Evaluation: tính đúng, sai số, chi phí fusion, throughput, bottleneck và case study.
5. Limitations và kết luận đúng theo các mode/workload đã thực hiện.

Hình/bảng tối thiểu: sơ đồ mảng, hai mapping hẹp/rộng, lịch issue/writeback,
bank layout minh họa, bảng PPA/baseline và biểu đồ precision–throughput.
Chi tiết numeric contract, test vectors và full sweep để trong artifact/tài liệu bổ sung.

## 15. Tài liệu tham khảo và trạng thái sử dụng

Các mô tả dưới đây phục vụ định vị; số liệu so sánh phải được trích từ cấu hình cụ thể
trong toàn văn, không sao chép speedup của toàn ứng dụng thành speedup của core.

- **[R1] Bit Fusion: Bit-Level Dynamically Composable Architecture for Accelerating Deep Neural Networks.**
  [Paper](https://arxiv.org/abs/1712.01507), ISCA 2018. Tiền lệ ghép/tách bitwidth cho DNN.
- **[R2] A Unified Hardware Accelerator for Fast Fourier Transform and Number Theoretic Transform.**
  [Toàn văn](https://arxiv.org/html/2504.11124v1), ICASSP 2025. Baseline hợp nhất FFT/NTT.
- **[R3] Aloha-HE: A Low-Area Hardware Accelerator for Client-Side Operations in Homomorphic Encryption.**
  [Paper](https://flokrieger.github.io/papers/date24_aloha.pdf),
  [RTL](https://github.com/flokrieger/Aloha-HE), DATE 2024.
- **[R4] ABC-FHE: A Resource-Efficient Accelerator Enabling Bootstrappable Parameters for Client-Side Fully Homomorphic Encryption.**
  [Toàn văn](https://arxiv.org/html/2506.08461v1). Đối chiếu streaming và Fourier engine.
- **[R5] A Unified FFT/NTT Design for Efficient NTRU Equation Solving in FALCON Cryptography.**
  [Trang nhóm tác giả](https://researchoutput.ncku.edu.tw/en/publications/a-unified-fftntt-design-for-efficient-ntru-equation-solving-in-fa/),
  ISCAS 2025. Đã xác nhận abstract; cần toàn văn để kết luận chi tiết.
- **[R6] A Flexible Hardware Design Tool for Fast Fourier and Number-Theoretic Transformation Architectures.**
  [Paper](https://flokrieger.github.io/papers/tcad25_opennttext.pdf),
  [OpenNTT](https://github.com/flokrieger/OpenNTT).
  Online publication 2025; bản journal hiện có mang thông tin số tháng 5/2026.
- **[R7] NTRUGen.**
  [Mã nguồn format số học](https://github.com/pornin/ntrugen/blob/main/src/ng_inner.h).
  Pin revision khi sử dụng; không coi keygen Q32.32 là đóng góp mới.
- **[R8] Toward a Secure Fixed-Point Implementation of the Falcon Signature Scheme.**
  [ePrint 2026/1531](https://eprint.iacr.org/2026/1531),
  [Giải thích của tác giả](https://pqshield.com/falcon-without-floating-point/),
  [Implementation](https://github.com/fixed-point-fndsa/fixed-point-c).
- **[R9] Falcon specification/reference.**
  [Đặc tả](https://falcon-sign.info/falcon.pdf). Pin phiên bản dùng cho adapter và KAT.
- **[R10] A Lightweight Fused Floating-Point & Modular Arithmetic Unit for FALCON FFT/NTT.**
  [Abstract ICTA 2026](https://epapers2.org/icta2026/ESR/paper_details.php?paper_id=7294).
  Đã xác nhận abstract/acceptance; chưa dùng làm bằng chứng về phần không mô tả.
- **[R11] A Flexible CO-OFDM Using Reconfigurable Multi-Precision FFT.**
  [Thông tin và abstract từ trường](https://digital.library.adelaide.edu.au/items/27137897-cc26-47c7-af99-72859a4559c2),
  IEEE Communications Letters 2017. Tiền lệ FFT runtime precision; cần toàn văn cho chi tiết kiến trúc.
- **[R12] ZK-Flex: A Flexible and Scalable Framework for Accelerating Zero-Knowledge Proofs.**
  [Paper](https://arxiv.org/abs/2606.03046), DAC 2026. Nguồn bổ sung về multi-precision cho ZKP.

Ghi chú nguồn từ PLAN trước: ePrint 2026/2431 chưa xác minh được nội dung trong đợt cập nhật này,
nên không dùng làm căn cứ cho precision hoặc tính an toàn. Chỉ đưa lại sau khi xác nhận
đúng title, tác giả, phiên bản và nội dung.

## 16. Việc bắt đầu sau khi chốt PLAN

1. Tạo related-work matrix và numeric contract, pin reference.
2. Xác nhận tool, target đánh giá, resource budget và số mode/độ dài đưa vào bài đầu
   (board FPGA cụ thể chỉ cần trước P6).
3. **Phân tích một uPE trước tiên**, độc lập công nghệ:
   - hiệu suất dùng bộ nhân ở từng mode (bit-product có ích / khả dụng), gồm NTT 14×14 trên leaf 32×32;
   - chi phí chuyển giữa nhiều phép hẹp và một phép rộng: mux phát toán hạng, cắt carry, metadata;
   - giới hạn cấp dữ liệu: số phép hẹp có ích không vượt được trần băng thông của mục 6.2;
   - so leaf 32×32 với leaf 16×16 ghép phân cấp bằng tổng hợp generic (area/timing tương đối).
4. Viết model phép nhân rộng, nhân phức và group mapping cho K = 16/32/64.
5. Viết model bank/schedule trước khi khóa RTL RAM và mạng hoán vị.
6. Qua G0–G2 rồi mới triển khai mảng RTL và tích hợp hệ thống.

Các bản PLAN trước được lưu tại:
- [docs/plan_history/PLAN_2026-10-21_before_flextransform.md](docs/plan_history/PLAN_2026-10-21_before_flextransform.md)
- [docs/plan_history/PLAN_2026-10-21_before_generic_rtl.md](docs/plan_history/PLAN_2026-10-21_before_generic_rtl.md)
