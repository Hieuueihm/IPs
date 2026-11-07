# Đối chiếu prior work với baseline 3.1

Ngày 2026-11-04. Baseline: `a_cg_packed4_system160`, [registry](../../experiments/BASELINE.md), [spec 3.1](../../spec/FlexTransform/3.1/README.md).

Đã đọc lại các mục kiến trúc, sơ đồ và bảng tương ứng trong bốn PDF đã tải cho người dùng. Đây là phân tích cấu trúc, không phải tái lập RTL/PPA của tác giả. ICTA 2026 vẫn chỉ có abstract truy cập được; không tìm được toàn văn trong nguồn công khai hoặc các PDF cục bộ đã kiểm. Không dùng việc thiếu toàn văn để kết luận tính mới.

## 1. Kết luận cho hướng paper

Khác biệt rõ nhất trong tập bốn bài này là tổ chức một tile hỗ trợ trong cùng bitstream: FFT fixed-point 32/64/128 theo contract riêng, NTT đa modulus, và packed16 hai nhóm leaf có phản hồi Montgomery riêng nhưng dùng chung phần lưu/cộng/hiệu chỉnh cuối. Các mode được chọn giữa các lệnh, không tính FFT và NTT đồng thời.

Đây là ứng viên cho đóng góp vi kiến trúc có số đo thực nghiệm. Các ý riêng lẻ như unified FFT/NTT, multiprecision, đổi q, packing, ghép/tách multiplier hoặc Montgomery đều đã có tiền lệ. Chưa có cơ sở gọi toàn thiết kế là kiến trúc đầu tiên trong toàn bộ literature.

## 2. Bốn bài và điểm đối chiếu

| Bài | Vị trí đọc chính | Điều đã có trong bài | Điểm cần phân biệt ở baseline 3.1 |
|---|---|---|---|
| Unified FFT/NTT, ICASSP 2025 | Section III–IV; Fig.2–4; Table I; PDF p.2–4 | Cùng số học/memory cho FFT32 và NTT ML-KEM/ML-DSA; tách multiplier con để tăng butterfly NTT; reducer Barrett theo mode | FFT nhiều precision/chiều; modulus nạp runtime; nhân cho T/m/mq chạy lại trên cùng leaf; hai nhóm packed dùng chung tầng cuối |
| OpenNTT, TCAD 2026, online 2025 | Section III-D, IV-A/B; Fig.2–4; PDF p.6–8 | Runtime direction/q; multiplier/reducer theo q lớn nhất; TwGen và MemOpt/RoutOpt | FFT/NTT cùng bitstream, precision runtime và q nhỏ làm đổi số gói; stored roots/CG là một đánh đổi khác với TFG |
| Maestro, arXiv 2025 | Section V-A/B/C; Fig.4–5; PDF p.8–9 | FFT FP16/FP32, tái sử dụng engine rộng cho mức hẹp, gather/scatter | Fixed-point theo contract tham chiếu, thêm modulo chính xác và các phần arithmetic dùng chung giữa hai miền |
| BitFusion, ISCA 2018 | Section III-C; Fig.8–10; PDF p.5 | Kết hợp fusion trong không gian và nhiều lượt theo thời gian cho MAC DNN | Butterfly có nhiều output độc lập, phản hồi reduction và root/bank/tag; không chỉ là shift-add tạo tích rộng |

Nguồn chính:

- [Unified FFT/NTT — toàn văn](https://arxiv.org/html/2504.11124v1).
- [OpenNTT — toàn văn tác giả](https://flokrieger.github.io/papers/tcad25_opennttext.pdf).
- [Maestro — toàn văn](https://arxiv.org/html/2503.04581v1).
- [BitFusion — toàn văn](https://arxiv.org/html/1712.01507v2).

### 2.1 Unified FFT/NTT là đối chiếu gần nhất về chia sẻ số học

Fig.4 có các khối reduction theo mode sau đường nhân. Do đó ý tưởng dùng multiplier FFT cho nhiều NTT hẹp không còn mới. Điểm khác có thể kiểm trực tiếp là baseline 3.1 sử dụng lại chính các leaf cho các phép nhân phụ thuộc trong reduction; không thêm một bộ nhân reduction bên cạnh cho từng lane.

Suy luận thiết kế: thay reduction riêng theo hai mode bằng đường q/qinv tổng quát đổi lại phải trả ba lượt nhân mỗi phép Montgomery. Đây là đánh đổi tính linh hoạt, DSP, latency và điều khiển; chưa phải chứng minh phương án mình tốt hơn. Số học FFT và FPGA của hai bên khác nhau nên không so raw LUT/cycle trực tiếp.

### 2.2 OpenNTT là đối chiếu gần nhất về modulus và dataflow

Section III-D/IV-A phân biệt rõ FFT hay NTT được chọn khi tạo thiết kế; q/chiều là runtime trong cấu hình hỗ trợ. Không diễn giải unified forward/inverse thành FFT/NTT chung datapath runtime. Đổi q vì thế không phải đóng góp riêng của mình.

Suy luận thiết kế: baseline của mình đổi mức sử dụng leaf khi vào packed16, đồng thời tăng mật độ đọc bank/root; hướng này khác việc chỉ đổi q trên datapath định cỡ lớn nhất. OpenNTT có lợi ích riêng về sinh twiddle và chuyển prime; mình dùng root RAM nạp từ host, không được tự nhận tiết kiệm BRAM hoặc chuyển prime tốt hơn.

### 2.3 Maestro làm rõ giới hạn của claim multiprecision

C32/C64 trong Maestro là độ rộng tổng của số phức, tương ứng FP16/FP32 mỗi thành phần. Không đặt chúng ngang FFT32/64 của mình, vốn là độ rộng mỗi thành phần fixed-point. Họ còn có ghép tính toán precision thấp trên engine rộng; không mô tả họ như hai core hoàn toàn độc lập không dùng chung.

Mình tăng độ rộng FFT bằng số lượt limb trong cùng tile. Việc chạy nhiều precision là khác biệt chức năng so với một FFT fixed-width, nhưng tự nó không phải cơ chế fusion mới. Các ranh giới wrap/round/3M của reference phải giữ; không lấy fused-rounding của floating point thay vào rồi gọi tương đương.

### 2.4 BitFusion là tiền lệ, không phải đối thủ FFT/NTT cùng workload

BitFusion đã có cả fusion không gian và nhiều lượt theo thời gian. Vì thế schoolbook từ multiplier nhỏ và tính nhiều lượt không đủ làm novelty. Thêm FFT/NTT vào một ứng dụng khác cũng chưa tự tạo ra đóng góp phương pháp.

Phần cần chứng minh ở mình là tổ chức reduction có phụ thuộc, nhiều kết quả butterfly độc lập và bộ nhớ theo kịp. Không gọi FFT128 tính limb trong một tile là ghép nhiều tile. Baseline chỉ đổi grouping của bốn leaf giữa fused32 và packed16, chưa đổi thành nhóm liên tile theo precision FFT.

## 3. Cơ chế cụ thể nên đặt làm trung tâm

Mỗi phép Montgomery trên một lane cần:

```text
T = a * w
m = low(T) * qinv mod R
P = m * q
u = high(T) + high(P) + [low(T) != 0]
r = conditional_subtract(u, q)
```

NTT32 dùng bốn leaf tạo phép nhân 32×32 cho từng lượt. Packed16 dùng leaf0/1 cho luồng A, leaf2/3 cho luồng B; mỗi luồng mang hai butterfly và khởi động lệch một clock. Với FUSE=5, các lượt của một gói ở 0/5/10, không phải ba phép phụ thuộc hoàn tất trong ba clock liên tiếp.

| Pha ổn định | Leaf0/1 | Leaf2/3 |
|---|---|---|
| 0 | T | m |
| 1 | mq | T |
| 2 | m | mq |

Các ô thuộc nhiều gói đang xử lý. Tích thô bypass mạng cộng ghép; alignment giữ phản hồi 5 clock. T-high/NZ được chọn ở thời điểm T về rồi lưu trong một history dùng chung. Khi mq về, chọn đúng nhóm tại thời điểm khác và dùng chung tầng cộng U, correction, butterfly add/sub và side/tag RAM.

Đây là phần kết hợp tài nguyên có thể phân tích ở mức cổng/lịch, không chỉ bảng tính năng. Cận tính toán packed theo cách hiện thực hiện tại là 4 leaf-products/clock chia 3 leaf-products/Montgomery = 4/3 butterfly/clock/tile. Test đã đạt nhịp bão hòa bốn butterfly/3 clock. Lịch RAM thực tế vẫn phải chịu fill/drain và phụ thuộc tầng.

Nguồn: [tile RTL được nhận](../../experiments/a_cg_packed4_system160/rtl/tile_a.sv), nhánh `g_arr32/packed_stream`; [spec cổng và lịch](../../spec/FlexTransform/3.1/05_trien_khai_rtl.md), mục 7, 10, 13–14; [planner](../../experiments/a_cg_packed4/planner.py).

Core đọc packed ở pha1/2, tile nhận pha0/1. Giữ request/response64, root32, mạng bốn nguồn mỗi ngõ đọc và số cổng BRAM; mỗi gói đến ở clock riêng. Tăng lane tính mà không giữ các giới hạn này có thể trả chi phí mux/memory lớn hơn lợi ích nhân.

## 4. Mức độ mạnh của từng claim

| Claim dự kiến | Đánh giá |
|---|---|
| Đầu tiên hợp nhất FFT/NTT | Không dùng; ICASSP đã có |
| Đầu tiên có runtime modulus | Không dùng; OpenNTT đã có |
| Đầu tiên multiprecision hoặc ghép multiplier nhỏ | Không dùng; Maestro/BitFusion đã có tiền lệ |
| FFT128 là nhiều tile ghép thành một PE rộng | Không đúng với baseline |
| Thiết kế thực hiện bit-exact nhiều contract và NTT đa modulus trên cùng mảng | Claim chức năng đã có bằng chứng; chưa tự chứng minh novelty |
| Lịch hai nhóm Montgomery dùng chung history/tầng cuối trên mảng FFT | Ứng viên đóng góp vi kiến trúc đáng kiểm với prior art rộng hơn |
| Lịch trên tăng hiệu năng dưới giới hạn cổng/bus/DSP/BRAM | Có ablation nội bộ; không đồng nghĩa thắng mọi paper |
| Nhanh/nhỏ/tiết kiệm điện nhất | Chưa có căn cứ |

Không mô tả trong bốn bài không có nghĩa chưa ai làm. ICTA còn thiếu toàn văn; trong abstract của họ đã có fusion FFT/NTT nên vẫn phải ghi nhận khi viết related work.

## 5. Bằng chứng nội bộ hiện có

Hai bản đều P&R toàn hệ thống ở 160 MHz trên cùng part/clock contract:

| Chỉ tiêu | Packed hai leaf trước | Packed bốn leaf hiện hành |
|---|---:|---:|
| LUT | 31.242 | 34.277 |
| FF | 31.186 | 33.397 |
| DSP48 / RAMB18 | 64 / 48 | 64 / 48 |
| NTT q12289 N1024, một job | 531 cycle | 391 cycle |
| NTT q12289 N1024, hai job | 987 cycle | 535 cycle |
| NTT q3329 N256 hmin1, một job | 237 cycle | 214 cycle |

LUT thêm 9,71%; N1024 tăng tốc 1,36×, batch hai job 1,84×. Transform nhỏ không mặc định hưởng 2×. Đây là so với mốc trước của chính thiết kế, chưa phải speedup so với bốn bài.

Ablation cùng OOC synth: bốn leaf với T-high riêng 35.393 LUT; dùng chung T-high còn 34.185 LUT, tiết kiệm 1.208 LUT. Không tráo các số synth này với 34.277 LUT toàn hệ thống sau P&R.

Nguồn: [báo cáo synth/cycle](../../study/results/a_cg_packed4.md), [báo cáo P&R](../../study/results/a_cg_packed4_system160.md), [manifest số đo](../../experiments/BASELINE.json). Correctness là vector/C replay và STA; chưa đo điện năng, chưa chạy board hoặc full signer RTL.

## 6. Cách diễn đạt đóng góp và phần còn thiếu

Luận điểm nên thử bảo vệ: **tổ chức cùng mảng nhân cho tích FFT đa precision và các lượt nhân của Montgomery, cùng lịch packed hai nhóm chia sẻ trạng thái/tầng cuối, để tăng công việc hữu ích trong giới hạn bộ nhớ và độ chính xác PQC.**

Ba phần đóng góp có thể trình bày: (1) datapath dùng chung và cách hiện thực đúng các contract; (2) lịch hai nhóm và chứng minh không tranh chấp tài nguyên/history/metadata; (3) kiểm hiệu năng, diện tích và correctness toàn kernel/hệ thống. Cần coi đây là một tổ chức thống nhất, không gắn nhãn ba phát minh độc lập cho ba kỹ thuật đã quen thuộc.

Phần cần hoàn thiện để claim mạnh: phân rã chi phí LUT/FF theo multiplier/reduction/state/control/memory; ablation cùng numerical contract/FPGA/phạm vi host; đo lợi ích theo FFT precision, q/N và single/batch. Đối chiếu paper chỉ chuẩn hóa khi cùng phép biến đổi, precision, số điểm phức và scope tài nguyên. Có thể công bố một đánh đổi tốt có ứng dụng cụ thể, không cần tuyên bố thắng toàn bộ cấu hình.
