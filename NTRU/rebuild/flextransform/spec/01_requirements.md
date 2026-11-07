# 01 — Yêu cầu và ranh giới

Trạng thái: yêu cầu cho thiết kế mới, chưa triển khai. Các ID bên dưới dùng để truy từ spec tới test và gate trong PLAN.

## 1. Bài toán

Các kernel PQC cần phép biến đổi trên hai miền số học: FFT có dấu và fixed-point nhiều độ rộng; NTT tính đúng modulo q. Dựng hai datapath riêng làm tăng tài nguyên; dùng chung quá tập trung lại tạo mux, state và fanout lớn. Bài toán là tổ chức nhân/cộng và bộ nhớ dùng chung có kiểm soát, giữ đúng từng bit và có throughput hữu ích trong FPGA nhỏ.

FN-DSA là ứng dụng kiểm chứng chính: FFT128 theo R8 cho đường expand/sign_tree, native NTRUGen64 và NTT cho những kernel tương ứng. FFT32/64 thường phục vụ tính linh hoạt của IP; không dùng chúng để tự giảm precision của signer R8. Các q khác cho thấy khả năng dùng lại NTT, không đồng nghĩa đã hiện thực đầy đủ mọi scheme PQC.

## 2. Yêu cầu bắt buộc

| ID | Yêu cầu | Bằng chứng nghiệm thu |
|---|---|---|
| R01 | FFT/IFFT thường W=32/64/128, đúng wrap/round và 3M | Golden theo precision; R8 C cho W128 |
| R02 | Native NTRUGen FFT64/IFFT64 đúng contract riêng | Vector C native, gồm wrap/halving |
| R03 | NTT/INTT scalar: q lẻ, 3≤q<2³¹, R=2³² | Oracle modulo, q biên và NTRUGen primes |
| R04 | Packed16: q<2¹⁵, hai butterfly/gói, hai nhóm leaf | Oracle độc lập, rate và isolation giữa lane |
| R05 | N=2^logn; FFT logn=0..10, NTT logn=1..10; NTT 0≤hmin≤2, hmin<logn | Decode cấu hình và vector nhỏ/identity |
| R06 | Batch 2^jobs_log, jobs_log=0..4 khi mapping vừa | Không alias, kết quả từng job độc lập |
| R07 | 32 data bank 256×32, 16 root bank 512×32 | Mô hình cổng, infer RAM và báo cáo resource |
| R08 | AXI-Lite 32 bit, map 3.1, AW/W độc lập, B/R stall-safe | Protocol/reset/byte-enable tests |
| R09 | Một command/context thực thi; payload snapshot khi nhận | Thay live pins sau handshake không đổi phép cũ |
| R10 | Reset hủy việc cũ, không rò response; không reset toàn BRAM | Reset tại mọi stage/response pending |
| R11 | Kết thúc sau khi mọi write cuối đã commit | Scoreboard active-mask; host đọc sau done đúng |
| R12 | Mục tiêu 64 DSP, 48 RAMB18, ≤35k LUT toàn hệ thống | Synth + P&R, cùng scope/part/constraints |
| R13 | Mục tiêu 160 MHz, setup/hold/pulse-width đều pass | Full-system STA, không bỏ endpoint để đạt số |
| R14 | Tái lập được bằng source/asset/tool/constraint hash | Manifest cho mỗi run, output riêng |
| R15 | 1.026 ca kernel và 74 lời gọi C được tái kiểm trên RTL mới | Không kế thừa PASS từ RTL cũ |

Trong R05, điều kiện NTT chính xác là **0≤hmin≤2 và hmin<logn**. FFT N1/N2 là identity theo convention phần mềm. q/root hợp lệ là điều kiện phía producer; xem spec số học.

## 3. Những giới hạn phải ghi rõ

- FFT N1024 là 1.024 hệ số thực theo layout phần mềm, tương ứng **512 điểm phức**; không đem so trực tiếp với FFT 1.024 điểm phức.
- Packed16 thay cách lưu và thực thi số nguyên modulo, không phải approximate computing.
- Một batch dùng chung mode, direction, fmt, N, hmin, q và bảng root. Không trộn FFT/NTT hoặc nhiều q trong cùng batch.
- q cấu hình được không có nghĩa mọi q có root cần thiết cho mọi N. RTL không tự chứng minh prime/root order.
- Mỗi tile mới chỉ có một context q; hai slot của tile nghiên cứu cũ không phải yêu cầu của core.
- Không có backpressure tùy ý trên output tile. Controller phải đặt trước nơi ghi cho mọi response.
- IFFT thường normalize ở host-read. Phải đọc hết kết quả trước CFG/LOAD/START mới; dữ liệu RAM chưa normalize không được chain trực tiếp.

## 4. Ngoài bản dựng đầu

Không đưa vào critical path của project: IEEE floating point, q≥2³¹, q packed≥2¹⁵, CRT/big integer, RECIP, block exponent, CMUL/SPLIT/MERGE/BASEMUL như kernel riêng, full sampler/keygen/signer RTL, DMA/DDR, nhiều context đồng thời, inter-tile fusion theo precision hoặc pause giữa kernel.

Chúng là mở rộng có version và test riêng. Chưa đạt PPA không phải lý do để tự bỏ native64, giảm precision, đổi rounding hoặc đổi tập modulus.

## 5. Quy tắc thay đổi

Thay pipeline/mapping thì cập nhật latency manifest, planner, descriptor và test. Thay numerical semantics thì phải mở một arithmetic contract khác, không gọi là tương thích 3.1. Không ghi đè baseline cho đến khi có một kết quả mới được người dùng nhận.
