# FlexTransform — kế hoạch từ baseline 160 MHz

Cập nhật 2026-11-04. **Baseline được người dùng nhận: `a_cg_packed4_system160`.** [Nguồn/manifest](experiments/BASELINE.md), [kiến trúc](docs/architecture_v1.md), [contract 3.1](spec/FlexTransform/3.1/README.md). Kế hoạch nhiều PE ghép/tách, K=32 L32 và các mốc 21 tuần trước đây được lưu ở [PLAN lịch sử](docs/plan_history/pre_baseline_160_2026_11_04/PLAN.md), không còn là yêu cầu bắt buộc của baseline này.

## 1. Bài toán và câu hỏi nghiên cứu

Cần hỗ trợ FFT/IFFT nhiều precision và NTT/INTT nhiều modulus cho các kernel PQC, đặc biệt Falcon/FN-DSA, với ít tài nguyên. Yêu cầu giữ đa precision, đa modulus và kết quả tham chiếu; số tile, cách ghép/tách, số lượt tính và tổ chức bộ nhớ là biến thiết kế.

Câu hỏi hiện tại: dùng chung mảng nhân/cộng và trạng thái trung gian, kết hợp lịch bộ nhớ constant-geometry, có giảm chi phí hỗ trợ nhiều mode trong ngân sách khoảng 35k LUT mà vẫn giữ đúng số học và có throughput hữu ích hay không?

Baseline tăng độ rộng FFT bằng các lượt limb trong mỗi tile, không ghép nhiều tile cho cùng một phép nhân rộng. Không lấy hợp tác liên tile làm điều kiện nghiệm thu hiện tại, cũng không gọi nó là tính năng đã triển khai. Tính mới và lợi ích so với prior art vẫn phải phân tích, không được suy từ việc core chạy đúng.

## 2. Mốc đã đạt

| Hạng mục | Bằng chứng hiện tại |
|---|---|
| FFT32/64/128, native NTRUGen64, NTT nhiều modulus | Có cùng core, cùng cấu hình hệ thống |
| Packed16 dùng cả bốn leaf, batch đồng cấu hình | Hai nhóm leaf, hai gói/3 chu kỳ; 252 ca packed qua AXI |
| Correctness | 1.026 ca đúng bit, packed nhanh hơn hoặc bằng mốc trước; 74 transform C, 14 artifact, 4 chữ ký độc lập |
| Host thật | PS7 GP0 → AXI interconnect → AXI-Lite; MMIO nạp root/descriptor/dữ liệu |
| STA toàn hệ thống | XC7Z020-CLG400-2, **160 MHz**, setup **+0,178 ns**, hold **+0,032 ns**, 0 vi phạm |
| Tài nguyên sau route | **34.277 LUT, 33.397 FF, 64 DSP, 48 RAMB18**, tính đủ host/root/AXI/reset/clock |

Đây là cấu hình PS7/OCM-JTAG tối thiểu, DDR và ngoại vi tắt; chưa đo board, chưa full signer RTL, chưa chứng minh Fmax cực đại hoặc số tile tối ưu.

## 3. Quy tắc bảo toàn

1. Giữ nguyên precision, wrap, rounding, Montgomery và contract native C; không tự giảm độ chính xác để đổi PPA.
2. Giữ source/evidence baseline được pin; mọi tối ưu tiếp theo trên bản riêng. Chỉ thay mốc khi người dùng nhận kết quả mới.
3. So đúng phạm vi: toàn hệ thống với toàn hệ thống, core với core; synth estimate, OOC và P&R/audit là ba loại số khác nhau.
4. IFFT scale tại host-read: không chạy cfg/start/load mới trước khi đọc hết kết quả. Không mặc định có chaining normalize trong RAM.
5. Kiểm correctness và các điều kiện timing bị ảnh hưởng sau thay đổi; không nới constraint hoặc thêm false-path để đạt số.

## 4. Công việc nghiên cứu còn lại

- Phân rã chi phí arithmetic, state, memory, mux và điều khiển trên chính baseline được nhận.
- Đánh giá overhead của FFT multi-precision và NTT multi-modulus/packed16 bằng ablation có cùng numerical contract, FPGA, clock và phạm vi host/memory.
- Đối chiếu core dùng chung với các lựa chọn riêng hoặc fixed-width ở điểm throughput/latency tương ứng; không cộng LUT từ paper khác công nghệ để suy kết luận chắc chắn.
- Báo cả cycle/kernel, thời gian tính từ clock đã đạt STA, chi phí nạp/đọc AXI và phạm vi phần ứng dụng thay bằng RTL. Không suy tốc độ toàn signer từ FFT128.
- Nếu cần chạy board: dùng đúng PS init/clock và mô hình board đã chọn, kiểm chức năng thực. Nếu thêm DDR/DMA/ngoại vi hoặc clock mới, sign-off lại phạm vi mới.

## 5. Ngoài mốc đã nhận

CMUL/SPLIT/MERGE/RECIP riêng, phép basemul ML-KEM ở mức kernel, full keygen/CRT/sampler/signer, DMA, nhiều mode đồng thời, ghép PE liên tile theo precision, modulus >31 bit, IEEE floating point, side-channel/security certification chưa được thêm vào baseline. Host/reference còn làm phần ngoài transform. Các yêu cầu mở rộng của spec 2.0 giữ để xét tiếp, không mặc nhiên trở thành tính năng hoàn thành.

## 6. Kiểm lại và tài liệu

`python -X utf8 scripts/check_baseline.py` kiểm source/evidence được nhận. [fpga/z020](fpga/z020/README.md) là điểm vào build/audit; [spec 3.1](spec/FlexTransform/3.1/README.md) là contract của baseline. Tài liệu lịch sử và bảng số cũ phải có nhãn phiên bản khi được trích dẫn.
