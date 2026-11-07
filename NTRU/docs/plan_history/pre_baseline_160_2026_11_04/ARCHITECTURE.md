# FlexTransform v0.4 — core FFT/NTT trên mảng nhân ghép/tách

> Đã có RTL tự chạy nguyên kernel FFT/iFFT và NTT/iNTT, RAM/controller và AXI-Lite. 5.992 kernel khớp reference/oracle; bốn chữ ký N512/N1024 khớp byte C và qua verifier độc lập. [Phạm vi và bằng chứng mục 18](docs/autonomous_kernel_rtl.md).
> Cập nhật 26/10/2026. Đây là accelerator kernel; chưa triển khai toàn bộ FN-DSA lên RTL.
> Phạm vi hiện tại: chốt kiến trúc ở mức mô phỏng RTL. Triển khai ZCU106, bitstream, DMA và timing vật lý để giai đoạn sau; không phải điều kiện chốt hiện tại.
> Đã đo cycle/lane/stall ở mục 19: FFT hẹp chưa được cấp đủ lane; ưu tiên controller và cấp dữ liệu trước khi tăng số tile. [Báo cáo profiling](docs/kernel_parallelism_profile.md).
> Các bảng số học/budget được kiểm bằng [model/arch_checks.py](model/arch_checks.py)
> (kết quả: [study/results/arch_checks.md](study/results/arch_checks.md)); throughput vẫn là trần/giả định.
> Cập nhật kiểm chứng C: **3 842 lời gọi kernel, 171 464 word output mỗi model F16/R32, 0 sai khác**
> so với executable R8 đã pin. [Contract và cách chạy](docs/numeric_contract.md),
> [báo cáo C differential](study/results/r8_differential.md).
> Prototype RTL bank số học F16/R32: [mô tả](docs/arithmetic_prototype.md),
> [kết quả mô phỏng/tổng hợp generic](study/results/arith_proto.md). Kết quả này chỉ thuộc prototype số học trước mục 18.
> Cập nhật 26/10: [cụm nhỏ NTT một/hai tầng dùng chung multiplier FFT](docs/ntt_cluster.md),
> [kết quả](study/results/ntt_cluster.md). Đây là ứng viên mới ở mục 13; chưa khóa số cụm toàn core.
> Đã so RTL ba reducer và radix-4 CT/GS: [kết quả và lựa chọn ở mục 15](docs/reducer_radix4_results.md).
> Cập nhật sizing sau mapping: đã xử lý 110 pin vi phạm slew; tăng 0.00236% cell area. [Kết quả và phạm vi kiểm tra](docs/stream_slew_repair.md).
> Đã có RTL ghép FFT64/128, routing bank, FIFO/stall và đo cell-area/STA Nangate45:
> [báo cáo ở mục 16](docs/stream_core_results.md). PPA này chưa gồm RAM/controller của mục 18; chưa place-and-route toàn core.
> Lịch sử: [v0.1](docs/plan_history/ARCHITECTURE_v0.1_2026-10-25.md),
> [v0.2 trước review](docs/plan_history/ARCHITECTURE_v0.2_before_review_2026-10-25.md),
> [v0.2 trước khi làm gọn](docs/plan_history/ARCHITECTURE_v0.2_before_cleanup_2026-10-25.md),
> [v0.3 trước kiểm chứng C](docs/plan_history/ARCHITECTURE_v0.3_before_c_validation_2026-10-25.md).

## 1. Tóm tắt quyết định

| Nội dung | Hướng v0.3 | Trạng thái |
|---|---|---|
| Contract FFT | Theo R8 đã pin (mục 3): Q64.64, nhân 3M, làm tròn half-up từng tích, cộng/trừ wrap | FFT128 đã so kernel đầy đủ với C trên vector ghi; FFT32/64 chưa có reference |
| Nhân phức | **3M** (không phải 4M): 4M lệch phần ảo so với R8 | Chốt theo contract |
| iFFT | Cấu trúc **GS** của R8, chia cuối bằng `fpr_div2e` | Bắt buộc nếu cần khớp bit |
| NTT nghịch | CT-only (thêm một lượt pointwise) hoặc GS | So sánh bằng PPA |
| Leaf | So F16 (leaf 16×16) với R32 (leaf 32×32) | Chưa chốt |
| Ghép tích | Cây nhị phân dịch cố định, tap theo width, bỏ hạng không ảnh hưởng kết quả | Kiểm bit-exact ở model |
| Product bus | 16 khe × 32 bit; làm tròn FFT tại gốc cây | Đề xuất |
| Montgomery tổng quát | Tích phụ m, m·q đi đường nội bộ; bus chỉ mang T | Đề xuất |
| Reducer 3329/12289 | Compact high(mq), giữ CSA làm ứng viên ưu tiên timing | Đã kiểm RTL/tổng hợp generic, mục 15; chưa target STA |
| Twiddle NTT | Một RAM, nạp từ seed khi đổi context; quy tắc root nghịch theo bậc root | Đề xuất |
| Twiddle FFT | ROM từ executable R8: thuận có wr+wi, nghịch có wr−wi | Đã xuất .mem/JSON; chưa ánh xạ RAM vật lý |
| Context | Một modulus đang chạy; đổi sau khi drain | Baseline |
| Băng thông | Khảo sát 512/1024/2048 bit mỗi hướng | Chưa chốt |

“Chia sẻ được” không đồng nghĩa giảm area hay tăng throughput sau khi tính mux, register,
cây ghép, reducer và hậu xử lý.

## 2. Phạm vi và khác biệt cần chứng minh

FN-DSA dùng NTT mod 12289 và các kernel FFT trong đường khóa/ký. Core phục vụ các kernel này
trên cùng tài nguyên và có thể tái dùng cho profile PQC khác. FFT và NTT không chạy đồng thời.
Đây không phải toàn bộ bộ ký hay keygen.

So với OpenNTT (theo review trước, commit `86c07a5e77639f7f33292b31418f50c56c6aabd5`;
**chưa được kiểm lại độc lập trong bản v0.3**): OpenNTT đổi được modulus trong cấu hình phù hợp,
nhưng độ rộng bộ nhân và reducer theo modulus lớn nhất, chọn FFT/NTT khi tạo lõi, và q nhỏ
không tạo thêm lane. Khác biệt FlexTransform nhắm tới là cách phân bổ cùng mảng số học
lúc chạy (ghép/tách theo width, FFT/NTT). Đây chưa phải kết luận novelty.

- [Paper OpenNTT](https://flokrieger.github.io/papers/tcad25_opennttext.pdf)
- [Generator](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/tool/openntt.py#L164),
  [modmul](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/butterfly/btf_modmul.sv#L29),
  [core](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/ntt_control/ntt_core.sv#L254)

## 3. Contract số học FFT: reference R8

### 3.1 Bản được pin

- Mã: [fixed-point-fndsa/fixed-point-c](https://github.com/fixed-point-fndsa/fixed-point-c),
  commit `ad1e5bf7714d53230ad457364db8a46a1b459c94`.
- Cấu hình mặc định ở commit này (`config.h`): `FALCON_FPR_MODE = 2` (fixed-point, `FALCON_FXP`),
  `FALCON_AVX2 = 0`. Contract dưới đây chỉ áp dụng cho cấu hình đó (nhánh scalar).
- File đã đọc: `fpr.h` (nhánh `FALCON_FXP`), `fft.c` (`FPC_MUL`, `FFT`, `iFFT`).
- Đã build source nguyên bản bằng GCC Linux LP64 trong WSL và ghi input/output từ lời gọi C;
  compiler flags, hash source và hash vector nằm trong [manifest](study/vectors/r8/manifest.json).
  Không dùng GCC MinGW LLP64 để kết luận luồng ký: R8 dùng `__builtin_clzl` với toán hạng 64 bit.

### 3.2 Phép toán cơ bản

`fpr` là số 128 bit bù 2, định dạng Q64.64 (giá trị = v / 2^64). Ký hiệu wrap(x) = x mod 2^128
diễn giải có dấu.

| Hàm R8 | Ngữ nghĩa chính xác |
|---|---|
| `fpr_add`, `fpr_sub` | wrap(x ± y); không làm tròn, không báo tràn |
| `fpr_mul` | wrap(floor((x·y + 2^63) / 2^64)) — làm tròn gần nhất, **hòa làm tròn lên (+∞)** |
| `fpr_div2e(x, n)` | n = 0: x; n ≥ 1: floor(wrap(x + 2^(n−1)) / 2^n) — phép cộng wrap trước khi dịch |
| `fpr_half(x)` | `fpr_div2e(x, 1)` |

`fpr_mul` của R8 tách 64/64 bit, chỉ làm tròn tích xl·yl và giữ chính xác các tích chéo;
kết quả bằng đúng công thức trên (kiểm 100 081 cặp gồm giá trị biên). Đây không phải
ties-to-even.

### 3.3 Nhân phức `FPC_MUL` (3M)

Với a = ar + j·ai (dữ liệu), b = br + j·bi (twiddle hoặc toán hạng thứ hai):

~~~text
p0 = fpr_mul(ar, br)
p1 = fpr_mul(ai, bi)
k  = fpr_mul(wrap(ar + ai), wrap(br + bi))
d_re = wrap(p0 − p1)
d_im = wrap(k − wrap(p0 + p1))
~~~

Ba tích, mỗi tích làm tròn riêng; mọi phép cộng/trừ wrap 128 bit. So với 4M cùng quy tắc
làm tròn (d_im = rnd(ar·bi) + rnd(ai·br)): phần thực luôn bằng, **phần ảo khác ở 40,0%**
trường hợp ngẫu nhiên (50 000 mẫu, mỗi thành phần |a| < 2^6 và |b| < 1). Vì vậy baseline phải là 3M.

### 3.4 FFT và iFFT

- **Bố cục:** n hệ số thực → n/2 số phức; phần thực ở `f[k]`, phần ảo ở `f[k + n/2]`.
- **FFT** (CT, đầu ra bit-reversed): lặp `u = 1 … logn−1`; với twiddle s = GM[m + i1]
  (GM[k] = w^rev(k), w = exp(iπ/N), theo chú thích trong `fft.c`):
  y = `FPC_MUL`(f[j+ht], s); f[j] = x + y; f[j+ht] = x − y.
  Vòng đầu được bỏ vì là phép đồng nhất trong bố cục này.
- **iFFT** (GS): f[j] = x + y; f[j+t] = `FPC_MUL`(x − y, s) với s = iGM = liên hợp của GM.
  Vòng cuối được thay bằng chia cho N/2: mọi hệ số nhân `fpr_div2e(f[u], logn − 1)` khi logn > 0.
- **Hằng số:** bảng twiddle phải lấy đúng giá trị `fpr_gm_tab` của R8 (đã làm tròn sẵn ở
  dạng Q64.64), không tự tính lại.

### 3.5 Hệ quả cho phần cứng

1. Nhân phức là **3M**: 3 tích thực/nhân phức, mỗi tích làm tròn half-up tại gốc cây.
2. Toán hạng cộng trước (ar+ai, br+bi) **wrap về 128 bit**, nên không rộng thêm bit; ánh xạ limb
   giữ nguyên. Tổng br+bi của twiddle lưu sẵn trong ROM (wrap là tất định nên khớp bit);
   với twiddle liên hợp của iFFT cần wr−wi, không dùng lại tổng wr+wi của chiều thuận.
   tổng của dữ liệu cần một bộ cộng 128 bit trước bộ nhân.
3. iFFT cần đường **GS**: hiệu x − y (wrap) đi vào bộ nhân, sau đó lại cộng trước cho 3M
   (hai bộ cộng nối tiếp trước bộ nhân); tổng x + y đi thẳng ra.
4. Cộng/trừ butterfly và gộp Re/Im **wrap W bit**, không có guard bit. Muốn khớp bit thì phần cứng
   cũng phải wrap; cờ tràn chỉ có thể là tín hiệu debug không đổi dữ liệu.
5. Chia cuối iFFT là `fpr_div2e` với n = logn − 1 (cộng nửa đơn vị, wrap, dịch số học).

Đã xuất hai ROM Q64.64 gồm 1024 dòng 384 bit, mỗi dòng chứa real/imag/tổng đã wrap:
[thuận](study/vectors/r8/twiddle_forward_q64_64.mem),
[nghịch](study/vectors/r8/twiddle_inverse_q64_64.mem).
Constants được đọc từ `fpr_gm_tab` trong executable C, không tính lại bằng sin/cos.

### 3.6 FFT32 và FFT64

R8 chỉ có Q64.64 cho các kernel FFT. Mode FFT32 (Q16.16) và FFT64 (Q32.32) dùng **cùng quy tắc**
(3M, rnd(x·y) = wrap_W(floor((x·y + 2^(F−1)) / 2^F)), F = W/2, cộng wrap) để một datapath có một
ngữ nghĩa. Đây là contract tự định nghĩa, không khớp với reference nào; nếu dùng cho kernel
có reference riêng (ví dụ NTRUGen Q32.32) thì phải pin contract của reference đó.

## 4. Mảng nhân và cây ghép

### 4.1 F16 và R32

| Cấu hình | Leaf | Số leaf | Proxy diện tích nhân |
|---|---|---:|---:|
| R32 | 32×32, chọn dấu từng toán hạng | 32 | 32·32² = 32 768 |
| F16 | 16×16, chọn dấu; 4 leaf/cụm, tách hoặc ghép | 128 | 128·16² = 32 768 |

Cùng proxy g² nhưng không cùng diện tích thật: F16 thêm mux, cây ghép, cổng kết quả và register
cho lane độc lập. Phân tích tile trước đó (docs/tile_analysis.md) cho thấy tile 2×2 leaf 16 bit đắt hơn
16–26% diện tích tổ hợp so với L32 trong tổng hợp generic; đó là dữ liệu cấp tile, chưa phải PPA core.

### 4.2 Phân rã limb và hạng bỏ được

Toán hạng W bit chia thành k = W/g limb; limb thấp unsigned, limb cao nhất có dấu.
x·y = Σ x_i·y_j·2^(g(i+j)). Kết quả contract rnd(x·y) = wrap_W(floor((x·y + 2^(F−1))/2^F)) chỉ phụ
thuộc x·y mod 2^(3W/2), vì bit đầu ra là bit [F, F+W) của tích với F + W = 3W/2.
Do đó **bỏ được mọi tích limb có trọng số g(i+j) ≥ 3W/2**; tổng trong cây cũng được wrap ở 3W/2 bit.

| Leaf g | W | Tích limb đủ | Giữ lại | Dịch theo cấp cây | Bit cộng một cây (nút ≤ 3W/2 bit) |
|---:|---:|---:|---:|---|---:|
| 32 | 32 | 1 | 1 | — | 0 |
| 32 | 64 | 4 | 4 | 32, 32 | 192 |
| 32 | 128 | 16 | 15 | 32, 32, 64, 64 | 1 158 |
| 16 | 32 | 4 | 4 | 16, 16 | 96 |
| 16 | 64 | 16 | 15 | 16, 16, 32, 32 | 582 |
| 16 | 128 | 64 | 58 | 16, 16, 32, 32, 64, 64 | 2 734 |

Kiểm bit-exact: 30 081 phép nhân phức qua cây phần cứng (cả g = 32 và g = 16, có bỏ hạng, tổng
twiddle lấy sẵn) khớp `FPC_MUL` của R8 viết lại nguyên văn; FFT32/64 khớp contract của mục 3.6.

### 4.3 Cây dịch cố định

Xếp bit chỉ số limb theo trọng số (i0, j0, i1, j1, …): mỗi cấp cây có **một** lượng dịch, dùng chung
cho mọi width; mode chỉ chọn cấp tap. Không cần bộ dịch thay đổi theo mode hay cắt carry.
Một cây W = 128 có k² vị trí leaf; vị trí của hạng bị bỏ để trống (leaf không dùng).
Làm tròn half-up thực hiện ngay tại gốc cây (cộng 2^(F−1), lấy bit [F, F+W)).

### 4.4 Trần tính toán FFT (3M)

Một tích thực chiếm một cây k² vị trí; mỗi nhân phức cần 3 tích. Trần dữ liệu tính với
4W bit đọc/butterfly (A và B, mỗi số phức 2W bit).

| Mode | R32: tích/chu kỳ → BF/chu kỳ | F16: tích/chu kỳ → BF/chu kỳ | Trần dữ liệu 512 / 1024 / 2048 bit |
|---|---|---|---|
| FFT32 | 32 → 10,7 | 32 → 10,7 | 4 / 8 / 16 |
| FFT64 | 8 → 2,67 | 8 → 2,67 | 2 / 4 / 8 |
| FFT128 | 2 → 0,667 | 2 → 0,667 | 1 / 2 / 4 |

Đây là trần lý tưởng theo lượt issue, chưa tính pipeline, ALU, twiddle hay xung đột bộ nhớ.
Với FFT, F16 và R32 có cùng trần; khác biệt của F16 chỉ nằm ở NTT hẹp (mục 8).
FFT128 bị giới hạn bởi tính toán ở 512 bit: 3 tích × 16 vị trí = 48 vị trí/butterfly trên 32 leaf.

## 5. Datapath và product bus

### 5.1 Sơ đồ

~~~text
CONFIG: op, domain, width, profile_id, contract_id
                         |
A, B, twiddle → operand regs → [GS: x−y] → [3M: a_re+a_im] → limb split, chọn dấu
                         |
                operand selector (nhóm cố định)  ←── tích phụ Montgomery (register)
                         |
               mảng nhân F16 hoặc R32
                         |
           cây dịch cố định, tap theo width
             |                        |
   FFT: làm tròn half-up         NTT: T chính xác
             |                        |
             +----- product bus ------+          (đường nội bộ: m, m·q → reducer tổng quát)
             |                        |
   FFT: gộp Re/Im 3M (wrap)      NTT: reducer theo profile / tổng quát
             +-----------+------------+
                         |
              ALU A±T dùng chung (FFT wrap; NTT cộng/trừ mod q)
                         |
              FFT: div2e cuối iFFT | NTT: hiệu chỉnh, N^(−1)
                         |
                 pairing / pack / valid / output
~~~

Các tích phụ Montgomery đi qua register, không tạo vòng tổ hợp. Chỉ nối các nguồn cần thiết
theo nhóm; chưa giả định crossbar. Fan-in toán hạng phải tính lại cho cả FFT và NTT.
Ở GS, nhánh tổng A+B đi bypass đến output, nhánh hiệu A−B đi vào 3M; kết quả nhân không
chạy qua butterfly A±T lần nữa. Nếu tái dùng một ngân hàng ALU giữa pre-add GS và post-add CT,
phải có selector/delay và capacity tương ứng; sơ đồ trên chưa dimension đường điều khiển đó.

### 5.2 Product bus cố định

Bus nằm giữa cây ghép (đã làm tròn FFT) và khối xử lý sau. F16 và R32 chỉ khác nhau phía trước bus,
nên FFT adapter và reducer giữ nguyên khi đổi lựa chọn leaf. Đề xuất cho cấu hình 512 bit:
**16 khe × 32 bit** (512 bit tải), mỗi khe có `slot_valid`; tích rộng chiếm nhiều khe liền nhau.

| Mode, tại trần dữ liệu 512 bit | Tích/chu kỳ | Bit/tích | Khe dùng |
|---|---:|---:|---:|
| FFT32 (4 BF × 3 tích) | 12 | 32 | 12 |
| FFT64 (2 BF × 3 tích) | 6 | 64 | 12 |
| FFT128 (2 tích mỗi chu kỳ) | 2 | 128 | 8 |
| NTT 3329/12289: T = a·b | 16 | ≤ 28 | 16 |
| NTT 8380417: T | 8 | ≤ 46 | 16 |
| NTT prime RNS: T (m, m·q đi đường nội bộ) | 8 | 64 | 16 |

Metadata mỗi nhóm khe: job/transaction ID, loại tích (p0/p1/k của 3M, hoặc T), vị trí lượt.
Bus mang tích đã làm tròn nên không phục vụ được op lấy tích chính xác 2W+1 bit; nếu cần op đó
(ví dụ kiểm chứng), dùng nhiều lượt hoặc đường riêng.

Montgomery tổng quát: nếu cả T (64 bit), m (32 bit) và m·q (64 bit) đều qua bus thì mỗi modmul
cần 5 khe, trần chỉ còn 16/5 = 3,2 modmul/chu kỳ (với bus 16 khe × 65 bit, 1 khe/tích: 16/3 ≈ 5,33),
thấp hơn trần dữ liệu 8 của lane 32 bit. Vì vậy baseline dùng **đường nội bộ** cho m và m·q giữa
nhóm tile và reducer tổng quát; buffer chỉ hấp thụ burst, không bù thiếu băng thông liên tục.

## 6. NTT backend

### 6.1 Profile và context

| Profile | Lane lưu | Root | NTT cho x^N + 1 | Dùng cho |
|---|---:|---|---|---|
| 3329 | 16 | ζ = 17, bậc 256 | N = 256, **không đầy đủ** (7 tầng) + BASEMUL | ML-KEM |
| 12289 | 16 | root bậc 2N (q − 1 = 2^12·3 nên N ≤ 2048; Falcon dùng N ≤ 1024; ví dụ bậc 2048: 1945) | đầy đủ | FN-DSA |
| 8380417 | 32 | 1753, bậc 512 | N = 256, đầy đủ | ML-DSA |
| prime RNS 30–32 bit | 32 | root bậc 2N do host cung cấp | đầy đủ | nhân đa thức qua RNS; CRT ở host |

Context gồm q, R, biến thể Montgomery, hằng số, seed root, quy tắc root nghịch, normalization_factor và dạng biểu
diễn. Một context đang chạy tại một thời điểm; đổi context sau khi drain. Core không tự sinh prime/root.

### 6.2 Montgomery tổng quát (R = 2^32)

~~~text
q lẻ < 2^32, a, b ∈ [0, q), q' = −q^(−1) mod 2^32
T = a·b
m = (T mod 2^32)·q' mod 2^32
S = T + m·q                 // S < 2^65, S chia hết cho 2^32
u = S / 2^32                // u < 2q
out = u − q nếu u ≥ q, ngược lại u      // = a·b·2^(−32) mod q
~~~

Kiểm ngẫu nhiên trên q = 3329, 12289, 8380417, 2013265921, 4293918721. R32 dùng 3 tích/modmul;
F16 dùng 4 (T) + 3 (m, chỉ cần nửa thấp) + 4 (m·q) = 11 leaf. Ba tích phụ thuộc nhau; throughput
phụ thuộc cách pipeline, không suy thẳng từ 32/3 hay 128/11.

### 6.3 Montgomery theo profile

| q | R | Biến thể | Hằng số cho m | CSD hằng số | CSD q | T tối đa |
|---:|---|---|---:|---|---|---:|
| 3329 | 2^16 | (T + m·q)/R, trừ q nếu ≥ q | −q⁻¹ = 3327 | 2^12 − 2^10 + 2^8 − 2^0 | 2^12 − 2^10 + 2^8 + 2^0 | 24 bit |
| 12289 | 2^16 | (T + m·q)/R, trừ q nếu ≥ q | −q⁻¹ = 12287 | 2^14 − 2^12 − 2^0 | 2^14 − 2^12 + 2^0 | 28 bit |
| 8380417 | 2^32 | (T − m·q)/R, m có dấu, cộng q nếu âm | q⁻¹ = 58728449 | 2^26 − 2^23 + 2^13 + 2^0 | 2^23 − 2^13 + 2^0 | 46 bit |

Bound (input canonical): với 3329, S ≤ 229 241 599 < 2^28; với 12289, S ≤ 956 354 559 < 2^30;
cả hai cho u < 2q. Với 8380417, (T − m·q)/R ∈ (−q, q).
Khi đó mỗi modmul chỉ có một tích tổng quát a·b; hai phép nhân hằng là shift-add.

**Reducer chung 3329/12289.** Hai profile cùng R = 2^16 và cùng biến thể; trong mỗi profile, hằng số
cho m và q chỉ khác dấu số hạng 2^0. Một mạng shift-add trên tập số hạng {2^14, 2^12, 2^10, 2^8, 2^0}
với bit bật/dấu theo profile phục vụ cả hai; datapath định cỡ theo 12289. Lưu ý: đây là chia sẻ
**giữa hai profile**; bước tính m và bước tính m·q vẫn là hai phép nhân hằng (hai mạng, hoặc một
mạng dùng hai lượt). 8380417 dùng reducer riêng. So mạng chung với hai mạng riêng + mux ở bước PPA.

Bảng root lưu dạng w·R mod q nên phụ thuộc R của profile (2^16 hay 2^32); không dùng chung bảng
giữa các profile.

### 6.4 Biểu diễn, INTT, BASEMUL

- Dữ liệu canonical, root dạng w·R: Mont(B, w·R) = B·w mod q canonical. Pointwise hai toán hạng
  canonical cần chuyển đổi trước Montgomery.
- INTT dùng root nghịch và normalization_factor đúng profile/miền. NTT đầy đủ có log2(N) tầng
  dùng N^(−1); ML-KEM N=256 chỉ có 7 tầng nên dùng **128^(−1)**, không phải 256^(−1).
  Reference Kyber còn gộp chuyển miền: f=1441=R²/128 mod 3329, R=2^16; không chép nguyên
  factor đó nếu policy representation khác. Có thể dùng half_q(x) = (x + (x&1)·q) >> 1
  = x/2 mod q (kết quả < q) cho phép chia 2 từng stage. Không dùng làm tròn FFT cho phép chia modulo.
- BASEMUL (3329) là phép nhân trên cặp hệ số trong Z_q[x]/(x² − ζ), cần opcode/bypass riêng.

### 6.5 Nguồn twiddle NTT

- Một **twiddle RAM** chung, được nạp lại từ seed khi đổi context, thay cho ROM riêng mỗi profile/prime.
  Sinh trong miền Montgomery: Mont(w·R, s·R) = (w·s)·R mod q. Chi phí khoảng N phép nhân mỗi lần đổi
  context, khấu hao khi chạy nhiều transform cùng modulus.
- Không sinh twiddle cho từng butterfly lúc chạy: ở các stage cuối mỗi butterfly có twiddle riêng,
  nên gần như gấp đôi tải mảng nhân; thứ tự bit-reversed cũng không là cấp số nhân đơn giản.
- **Root nghịch phụ thuộc bậc root:**
  - Root bậc 2N (NTT đầy đủ: 12289, 8380417, prime RNS): ψ^(−k) = −ψ^(N−k) mod q.
  - Root bậc N (NTT không đầy đủ của ML-KEM, ζ = 17, N = 256): ζ^(−k) = ζ^(N−k), **không đổi dấu**.
    Ví dụ 17^(−1) = 1175 còn −17^255 = 2154 (mod 3329).
  - Ngoài ra phải ánh xạ đúng thứ tự bit-reversed của bảng; hoặc lưu bảng nghịch riêng.
- Băng thông đọc twiddle vẫn phải đủ cho trần dữ liệu (tới 64 root khác nhau/chu kỳ ở cấu hình
  2048 bit); một RAM chung không giải quyết số cổng đọc.

## 7. ALU cộng/trừ và CT/GS

CT: T = B·w; U = A + T; V = A − T. GS: U = A + B; V = (A − B)·w.

| Mode, dữ liệu 512 bit | Payload mỗi phía của A±T |
|---|---:|
| FFT32, 4 BF | 8 thành phần × 32 = 256 bit |
| FFT64, 2 BF | 4 × 64 = 256 bit |
| FFT128, 1 BF | 2 × 128 = 256 bit |
| NTT lane 16, 16 BF | 16 × 16 = 256 bit |
| NTT lane 32, 8 BF | 8 × 32 = 256 bit |

- FFT: cộng/trừ wrap W bit theo contract, không guard bit.
- NTT: cộng/trừ mod q kèm hiệu chỉnh; q gần 2^32 cần 33 bit cho tổng. Hai nhánh hiệu chỉnh tốn
  phần cứng hoặc thêm lượt; không tính full throughput mà coi hiệu chỉnh là miễn phí.
- Không ép gộp Re/Im, cộng/trừ butterfly và hiệu chỉnh Montgomery cùng chạy trên một ngân hàng
  chỉ đủ capacity cho một việc.

**FFT:** iFFT của R8 là GS, nên muốn khớp bit phải có đường GS (mục 3.5). CT-only cho iFFT đổi thứ tự
phép toán và vị trí làm tròn, không bit-identical; chỉ dùng được với contract cho phép sai số có chặn.

**NTT:** có thể bỏ GS bằng CT-only: địa chỉ đầu vào bit-reversed, đầu ra tự nhiên, root nghịch;
untwist ψ^(−i) gộp với N^(−1) thành một lượt pointwise N phép nhân (lượt N^(−1) vốn đã cần).
Số học chính xác nên kết quả mod q giống GS. So chi phí datapath GS với lượt pointwise và bộ sinh địa chỉ.
Mô tả untwist và N^(−1) này dành cho NTT negacyclic đầy đủ; không áp dụng nguyên xi cho
incomplete NTT của ML-KEM, vốn có BASEMUL và normalization riêng ở mục 6.4.

## 8. Giới hạn song song, latency và batching

Trần tích chính (một tích tổng quát/modmul cho profile Montgomery):

| Kernel | R32 (32 leaf) | F16 (128 leaf) |
|---|---:|---:|
| NTT lane 16 (3329, 12289) | 32 | 128 |
| NTT 8380417 | 32 | 32 |

Trần dữ liệu (A, B vào và ra cùng payload mỗi hướng):

| Bit/chu kỳ mỗi hướng | NTT lane 16 | NTT lane 32 | FFT32 | FFT64 | FFT128 |
|---:|---:|---:|---:|---:|---:|
| 512 | 16 | 8 | 4 | 2 | 1 |
| 1024 | 32 | 16 | 8 | 4 | 2 |
| 2048 | 64 | 32 | 16 | 8 | 4 |

- Ở 512 và 1024 bit, F16 không vượt R32 cho NTT lane 16 (trần dữ liệu ≤ 32). Ở 2048 bit, trần dữ liệu
  cho phép 64 so với 32 nếu reducer, ALU và twiddle theo kịp.
- Số reducer và lane cộng/trừ mod q định cỡ theo **trần dữ liệu**, không theo trần nhân.

**Mô hình latency có rào chắn giữa stage (giả định):** nếu stage sau chỉ bắt đầu khi stage trước
ghi xong, mỗi stage tốn (N/2)/P + L chu kỳ, và BF/chu kỳ ≈ (N/2)/((N/2)/P + L).
Ví dụ N = 256, L = 8 (giả định, chưa đo): R32 ở 1024 bit (P = 32) → 10,67; F16 ở 2048 bit (P = 64) → 12,80.
Mô hình này là cận dưới thô: lập lịch chồng lấp các stage (OpenNTT có nghiên cứu lịch truy cập
tránh stall) có thể giảm khoảng trống. Cần đánh giá cả ba trường hợp:

1. Một transform, có rào chắn giữa stage.
2. Một transform, có lập lịch chồng lấp stage.
3. Batch nhiều transform **cùng modulus** xen kẽ (k đa thức của ML-KEM, vector của ML-DSA,
   nhiều đa thức trên cùng một prime). Xen kẽ nhiều prime RNS cần nhiều context và nguồn twiddle,
   nằm ngoài baseline.

Ở cấu hình rộng, phương án bộ nhớ đáng xét là **song song theo đa thức**: nhiều vùng nhớ độc lập,
mỗi vùng một đa thức với bề rộng như cấu hình 512 bit, thay vì một bộ nhớ 2048 bit chia bank cho một
đa thức. Ở 2048 bit mỗi hướng, bộ nhớ (khoảng 128 lane 16 bit mỗi hướng) và twiddle có thể đắt hơn
mảng nhân; so diện tích **toàn core**.

## 9. Giao diện và ràng buộc hiện thực

- Cấu hình: op, domain, width FFT, profile_id, contract_id, normalization. Mỗi kernel pin một contract.
- Op dự kiến: BUTTERFLY_CT, BUTTERFLY_GS (FFT bắt buộc theo R8), CMUL, MULMOD, ADD_SUB;
  micro-op cho BASEMUL và split/merge đặc tả sau.
- Vào/ra mang transaction ID, lane_valid, component/lượt. FFT wrap theo contract; cờ tràn chỉ để debug.
- Đổi cấu hình sau khi drain mọi buffer tích, pairing và đường nội bộ.
- Chọn flow control trước RTL core: các tile hiện có chưa có valid/CE; phải thêm CE đồng bộ hoặc
  buffer/handshake có capacity được chứng minh.

## 10. Bộ kiểm tra so sánh với reference

### 10.1 Đã hoàn tất ở mức C và golden model Q64.64

- [Driver](scripts/validate_r8.py) build R8 đúng commit, giữ source nguyên bản; wrapper C bên
  ngoài ghi các lời gọi FFT/iFFT, `poly_mul_fft`, split và merge, kèm input/output hex128 và origin.
- 364 kernel calls synthetic: zero, impulse, alternating, biên/rounding ties, random nhỏ,
  random đủ 128 bit, ±LSB. FFT/iFFT N=1..1024; các kernel còn lại N=2..1024.
- Chạy keygen, mở rộng khóa, ký `sign_tree` và verify bằng chính R8 ở N=512 và N=1024.
  Ghi thêm 3 478 kernel calls từ mở rộng khóa/luồng ký. `sign_dyn` gọi đường reference khác
  ở commit này nên không dùng để gán workload cho contract fixed-point đã chốt.
- Keygen dùng NTRUGen Q32.32, chưa được ghi/kiểm ở bộ Q64.64 này; không gán các vector
  mở rộng khóa thành bằng chứng cho toàn bộ NTRUSolve/keygen FFT.
- [Golden model](model/r8_golden.py) dùng cây fixed-shift từng cấp, wrap 192 bit và bỏ đúng
  hạng không ảnh hưởng output. Cả leaf16 và leaf32 khớp **3 842 kernel calls / 171 464 word
  output mỗi model**, không sai khác. ROM cũng xuất từ executable C.
- Hai negative controls đều bị phát hiện: thay 3M bằng 4M; dùng root thuận cho iFFT.

Tái lập, schema vector, compiler flags, ROM và giới hạn:
[numeric_contract.md](docs/numeric_contract.md), [báo cáo](study/results/r8_differential.md),
[manifest/vector](study/vectors/r8/manifest.json).

### 10.2 Chưa hoàn tất

- RTL core transform đầy đủ và kiểm tra pipeline/stall/backpressure; sẽ dùng lại expected words đã ghi từ C.
  Prototype bank số học đã có kiểm tra RTL trong phạm vi mục 12.
- FFT32/64 so với reference phù hợp; Q64.64 của R8 không chứng minh hai mode đó.
- Differential NTT với `mq_NTT`/`mq_iNTT` Falcon, pq-crystals, và oracle số nguyên cho prime RNS.
- Thay kernel phần cứng vào signer. Chữ ký R8 đã verify ở 10.1 chưa phải chữ ký có kernel
  phần cứng; không mở rộng kết luận về phân phối chữ ký ngoài điều kiện của R8.

## 11. Bằng chứng hiện có và trình tự quyết định

- [model/arch_checks.py](model/arch_checks.py): mọi con số của tài liệu này (contract R8, 3M, cây,
  trần throughput/budget, bus, Montgomery, root), trừ kết quả C differential có báo cáo riêng.
- [C differential](study/results/r8_differential.md): executable R8 đối chiếu kernel đầy đủ
  với cây leaf16/32; không phải kết quả RTL/PPA.
- [RTL tile L32](hdl/tile_l32.v), [RTL bốn leaf 16 ghép/tách](hdl/tile_l16x4.v); [phân tích tile](docs/tile_analysis.md).
- [Model liên tile v0.1](docs/intertile_model.md) và [model cây từng tích](model/product_tree_v02.py):
  dùng 4M (không phải contract hiện tại); đã chuyển sang làm tròn half-up, giữ để đối chiếu.
- [Phân tích số học](docs/arithmetic_reassessment.md), [model fusion v0.2](model/core_fusion_v02.py).

Trình tự:

1. Bộ kiểm tra C R8 → golden model đã có (mục 10); giữ làm regression và dùng vector cho RTL.
2. So F16/R32 cùng chức năng, cả cùng proxy lẫn cùng ngân sách area sau tổng hợp.
3. Tổng hợp cây ghép, operand routing (gồm cộng trước cho 3M và GS), làm tròn, reducer.
4. Định cỡ ALU, hiệu chỉnh, pairing và đường nội bộ Montgomery theo trần dữ liệu từng mode.
5. So 512/1024/2048 bit với ba trường hợp latency/batching (mục 8) và CT-only so với GS cho NTT;
   báo time/area/energy toàn core.
6. Chốt F16 hoặc R32 bằng kết quả; sau đó mới khóa scheduler và bố trí bộ nhớ.

## 12. Prototype RTL nhanh để so F16/R32

Đã có [flex_arith_bank.sv](hdl/proto/flex_arith_bank.sv): một bank đủ tạo một real product
128 bit mỗi lượt, gồm operand mux, leaf array dùng chung, cây ghép, FFT half-up/wrap,
Montgomery12289, một ALU A±T chia lane và register input/output.

| Top | Leaf | Lane NTT12289 | Mục đích |
|---|---|---:|---|
| proto_r32 | 16 ×32×32 | 16 | Baseline |
| proto_f16_common | 64 ×16×16 | 16 | So overhead ở cùng năng lực NTT |
| proto_f16_mid | 64 ×16×16 | 32 | Điểm giữa: tăng lane với đường NTT vừa đủ |
| proto_f16_wide | 64 ×16×16 | 64 | So khả năng tăng lane hẹp |

Các top có cùng capacity nhân thực FFT32/64/128: 16/4/1 product mỗi cycle nếu cấp đủ
dữ liệu. Một bank là nửa mảng đối chiếu ở mục 4; không thay số lane của toàn mảng bằng bảng này.

Mô phỏng: 1 335 transaction ×4 top, gồm đổi mode liên tục và valid bubbles, không lỗi.
189 kết quả nhân phức từ ba tích RTL ghép lại khớp vector C R8. Pre-add, issue ba tích
và recombination 3M được thực hiện trong test driver, chưa là complex controller RTL.
Không gán kết quả đó thành bằng chứng FFT/iFFT transform RTL đầy đủ.

Tổng hợp đo cả register, mux, cây, reduction và ALU trong bank. Báo cáo GE/độ dài
đường gate là **generic**, không phải Fmax, diện tích FPGA/ASIC đích hoặc năng lượng.
Xem [báo cáo](study/results/arith_proto.md) và [cách tái lập](docs/arithmetic_prototype.md).
Mảng vẫn chưa có RAM/scheduler/handshake backpressure hoặc NTT multi-modulus RTL hoàn chỉnh.

Vòng tổng hợp bốn top: R32 ~246 933 total GE; F16 common ~264 393 (+7,1%);
F16 mid ~285 459 (+15,6%); F16 wide ~353 393 (+43,1%). Mid có 32 lane NTT,
gấp đôi R32, với cùng 3 078 FF bit; wide có 64 lane và 6 118 FF bit.
Capacity/GE của mid khoảng 1,73× R32 tại cùng clock giả định và băng thông đủ.

Ở 512 bit/cycle mỗi hướng, cả bốn bị chặn ở 16 butterfly NTT/cycle. Ở 1024 bit,
mid và wide cùng đạt trần 32 BF/cycle nhưng mid ít hơn khoảng 19,2% total GE.
Đây là điểm cân bằng trong họ bank cũ, chưa đủ để chọn core tối ưu cho NTT;
giữ R32 baseline, wide là ứng viên khi khai thác được trên 32 lane. Không chuyển
nguyên điểm bão hòa này sang mảng hai bank ở mục 8.

Mid giữ cây ghép FFT phân cấp hiện có, chỉ thay tham số số lane NTT khi tổng hợp;
chưa phải thử một mạng nối tile mới. Không chia sẻ reducer theo thời gian nên
không giảm issue rate do tái sử dụng reducer. FFT vẫn cùng capacity 16/4/1 tích thực.
Chưa chốt leaf toàn core hoặc tuyên bố speedup thực tế từ những số generic này.

## 13. Ứng viên mới: cụm nhỏ NTT một/hai tầng + FFT (26/10)

Thay vì chỉ giới hạn số reducer trên mảng nhân rộng, prototype mới dùng cụm bốn
leaf16. Cả bốn leaf được dùng cho bốn BF độc lập, hoặc hai BF mỗi tầng trong hai
tầng liên tiếp trên bốn hệ số. Mode FFT dùng cùng bốn leaf để tạo tích signed32×32
đầy đủ; chưa có cây W64/W128 mới. [Contract/RTL/kiểm tra](docs/ntt_cluster.md).

NTT q3329/q12289 giữ canonical và Montgomery R=2^16. Làm rõ các bit cao bằng zero
ở độ rộng 12/14 bit, không giảm precision FFT. Reduction chính xác ở từng tầng;
mode paired giữ hệ số trung gian trong cụm. CT chia sẻ root tầng đầu, GS chia sẻ
root tầng sau: ba root/nhóm. Bypass tầng hai có cùng latency với các mode shared.

Data mỗi transaction NTT: độc lập 128 bit mỗi hướng cho bốn BF; paired 64 bit
mỗi hướng cho cùng bốn BF tương đương qua hai tầng. Trần số học vẫn bốn BF/cycle.
Một cụm shared có ba cạnh lấy mẫu, II=1; thêm baseline NTT-only hai cạnh, II=1
để tránh đánh giá quá cao ghép tầng ở N nhỏ.

Mô phỏng 16 102 vector qua chín cấu hình theo mode hỗ trợ, 56 trace NTT/INTT
với oracle số nguyên, không sai khác. q3329 N256 là incomplete 7 tầng; chưa BASEMUL.
Tích FFT32 raw đã kiểm; 70 CMUL C R8 được ghép từ tích RTL trong driver,
không phải RTL butterfly/FFT128 mới. NTT chưa so trực tiếp C Falcon/Kyber.

Tổng hợp generic: shared parallel+FFT ~28 833 GE; thêm paired/bypass ~29 150 GE
(+1,10%). NTT-only pipeline ngắn ~22 123 GE: full shared vẫn đắt hơn khoảng 31,77%.
Mode paired-only hai profile ~22 239 GE, thêm bypass ~26 162 GE. Fixed q3329
paired ~16 087 GE; fixed q12289 ~18 432 GE. Không coi configurability là miễn phí.

Mô hình rào chắn giữa các lượt, có tính đọc/ghi serialize, cùng clock giả định:
q3329 N256 ở data64 bit mỗi hướng: dedicated short 462 cycle vs shared paired
265 cycle (~1,74×); ở data128 bit: 231 vs 232, không có lợi cycle. q12289 N8
ở data128 bit: short 6 vs paired 7; N nhỏ không tự làm paired tốt hơn.
Các cycle này là dự báo, chưa đo transform RTL với RAM, chưa gồm normalization.

**Lựa chọn hiện tại:** khảo sát cụm nhỏ configurable một/hai tầng thay cho việc
khóa F16–32 bank. Giữ các baseline, chưa chốt số cụm, ghép FFT rộng, interconnect
hay scheduler. Ưu tiên lợi ích về data reuse và hiệu quả toàn core theo workload;
không tối đa tỷ lệ multiplier bận nếu phải trả bằng nhiều area hoặc timing xấu.

## 14. Phân tích tiếp: radix-4 và cộng/reduction dùng chung

[Báo cáo phân tích](docs/radix4_shared_accum_analysis.md),
[model](model/radix4_shared_accum.py), [kết quả](study/results/radix4_shared_accum.json).
Đây là model số học, chưa thêm RTL hoặc có số đo GE mới cho hai ứng viên này.

Radix-4 factor thay bốn tích twiddle bằng ba tích twiddle + một tích với root
bậc4 cố định theo context; tích hằng vẫn cần mạng shift-add và reduction.
Forward cần ba tích trước recombination; inverse cần ba tích sau recombination.
Không khớp trực tiếp bố trí hai+hai hiện tại, không tự giảm số multiplier vật lý
vốn cần cho FFT. Giữ R8 FFT3M và mọi vị trí rounding như cũ.

Reducer profile có ứng viên cục bộ: q=k*2^a+1, (k,a)=(3,12)/(13,8).
Tính high(m*q) bằng tách m rồi giữ carry chính xác từ nửa thấp; u cuối cần14/12 bit,
nhưng còn mạng sinh m16 bit và carry18/20 bit. Không gọi toàn reducer là14/12 bit.
Đã kiểm hết65 536 word m và65 536 word Tlow mỗi q, cùng các nhóm CT/GS, nhân hằng
và CSA chia lane, không sai khác. Chưa differential NTT C hoặc RTL cho ứng viên mới.

Ưu tiên so reducer hiện tại/CSA/compact cùng pipeline và II trước; sau đó mới so
radix-4 có đủ chi phí nhân hằng và CT/GS. Fabric64 bit phục vụ một tổng64 bit của FFT32
hoặc hai NTT32-bit sums, không phải bốn. Chỉ chia sẻ phần CPA/compressor có đủ
capacity và đúng stage; các mạng profile nhỏ có thể giữ riêng nếu rẻ hơn.

## 15. Đã đo RTL reducer và radix-4 CT/GS

[Báo cáo](docs/reducer_radix4_results.md),
[reducer](study/results/reducer_compare.md), [radix-4](study/results/radix4_compare.md).
Nguồn mới nằm riêng trong `hdl/proto/`, giữ baseline cũ nguyên bản.

Ba reducer trong cùng shared cluster, cùng m generator, ba cạnh/II=1:
original29 300 GE/depth124; CSA29 489/depth109; compact28 198/depth118.
Chọn **compact** theo area thấp nhất với generic depth không vượt original.
Giữ CSA vì có tradeoff timing proxy tốt hơn; không suy Fmax từ gate-depth.
Đã khớp139 292 transaction reducer và16 102 transaction cluster, gồm cả các
mode FFT32 raw, CT/GS, đổi profile và bubbles. Các expected/vector FFT cũ được tái dùng.

Radix-4 đã có đủ nhân hằng, reduction, bốn mode và pipeline CT/GS. Mixed cho phép
đổi từng transaction; epoch dùng chung một constant-unit với profile/inverse
giữ ổn định đến khi drain. Cả hai có bốn cạnh/II=1; các đối chứng radix-2 có
ba cạnh hoặc thêm output FF thành bốn cạnh. Tất cả dùng reducer compact.

Shared radix-2 bốn cạnh28 987 GE/depth119; shared radix-4 mixed40 558/depth101;
shared radix-4 epoch39 083/depth100. Epoch vẫn tăng34,83% GE ở cùng bốn cạnh,
chưa có timing đích để chứng minh bù được area. Bốn multiplier vẫn giữ cho FFT
và bốn BF độc lập, nên ba tích twiddle trong paired mode chưa tiết kiệm leaf vật lý.

NTT-pair-only cho kết quả khác. Cùng bốn cạnh, fixed12289: radix-2 compact17 780 GE,
radix-4 epoch16 413 (−7,69%). Fixed3329:15 408→14 468 (−6,10%). Runtime hai q:
21 259→21 279, xem như ngang area trong flow này. Không dùng area pair-only để
thay cho full shared core: bản đó thiếu FFT, bốn BF độc lập và bypass tầng lẻ.

Đã kiểm17 510 vector ở chín cấu hình mixed/đối chứng và cùng17 510 vector qua
bốn cấu hình epoch có drain, không sai khác; các top kiểm theo mode/profile hỗ trợ.
Root mode factor thỏa đúng quan hệ hai tầng NTT, không chấp nhận arbitrary roots.
Giữ70 CMUL R8 ghép trong driver; NTT vẫn oracle số nguyên, chưa full C differential.

**Lựa chọn hiện tại: shared radix-2 một/hai tầng + compact reducer.** Giữ radix-4
epoch làm hướng NTT chuyên biệt/profile cố định hoặc giảm số mode, chưa dùng làm
default chung FFT/NTT. Chưa có fabric compressor chia sẻ FFT/reduction đầy đủ;
CSA đang đo là CSA nội bộ reducer. Chưa chốt leaf toàn mảng, FFT64/128 mới,
interconnect, scheduler, số cụm hoặc công suất.

## 16. Ghép FFT rộng, cấp bank NTT và đo toàn mảng

[Báo cáo chi tiết](docs/stream_core_results.md), [kiểm chứng](study/results/flex_stream_validation.json),
[banked RTL](study/results/banked_stream_validation.json), [số đo](study/results/stream_core_summary.json).

Đã triển khai prototype 16 tile × bốn leaf16. Cùng mảng cho 16 tích FFT32, bốn FFT64
hoặc một FFT128 mỗi giao dịch; đây là tích thực, chưa là butterfly FFT phức đầy đủ.
Chọn dấu ở limb cao, raw65, ghép modulo96/192 bit và rounding cuối từng tích.
FFT128 giữ Q64.64 R8; FFT32/64 hiện là contract tự định nghĩa, chưa so reference thấp precision.

22.724 giao dịch mảng không sai khác; 19.968 tích RTL đưa lại bốn kernel FFT/iFFT C R8
N512/N1024, khớp 3.072 word. Có 16.217 chu kỳ output stall và 1.000 giao dịch đổi cấu hình nhanh.
Không dùng kết quả này để nói đã thay full core phần cứng vào signer.

64 data-bank 16 bit 1R+1W, XOR bank map và thứ tự tầng lẻ theo bank cấp được 16 nhóm
hai tầng mỗi lượt. 16 root-bank 48 bit lưu bundle ba root; tốn gần 1,5× bảng phẳng mỗi chiều.
28 transform case không xung đột; gather/array/scatter RTL khớp 376 lượt NTT trong 1.328
giao dịch mixed. RAM row generator, root RAM và stage controller vẫn là model/host.
Mode0 cần 128 hệ số/cycle nên không được nuôi đủ bởi 64 bank; N8 chỉ dùng hai trong 16 tile.

Nangate45 typical, trước layout, cell area toàn banked 0.450294 mm²,
arrival R→R 5.1370ns và setup slack 4.7197ns ở clock10ns.
Gồm routing logic, compact reducer, fusion, queue và global stall; chưa SRAM/CTS/wire RC/power.
Toàn bản banked tăng area 28.73% so với mảng không stall/queue.
Banked còn 110 pin vi phạm slew (log làm tròn: worst −0,01ns), chưa đóng timing về điện.
Không dùng arrival thấp hơn sau mapping để kết luận thêm routing làm tăng Fmax.
Đây là chi phí cấu hình trong cùng thiết kế, chưa chứng minh thắng các core FFT/NTT chuyên dụng.

Giữ hướng radix-2 một/hai tầng và exact fusion. Chưa khóa 16 tile; bước full-core cần
RAM/controller có hazard handling, FFT complex butterfly/normalization và NTT C differential,
rồi đo FPGA hoặc physical implementation ở target cụ thể.

## 17. Kiểm chứng ứng dụng PQC qua adapter C/RTL

[Báo cáo](docs/pqc_application_cosim.md), [kết quả](study/results/pqc_application.json),
[audit RTL](study/results/pqc_application_audit.json).

Đã chạy hai thông điệp cho mỗi N512/N1024. C tiêu thụ kết quả kernel dựng từ RTL,
tạo bốn chữ ký khớp từng byte baseline và được verifier C gốc độc lập chấp nhận.
Thông điệp/chữ ký sửa bị từ chối. Có 5,472 lời gọi kernel,
315,753 giao dịch RTL duy nhất; không sai khác output kernel.

FFT128: phép nhân thực Q64.64 ở RTL; 3M/add/sub/scaling và điều phối ở host.
NTT/iNTT q12289: butterfly một/hai tầng và routing ở RTL; stage/row controller ở host.
Chuẩn hóa iNTT, TOMONT và MODMUL cũng dùng Montgomery RTL. Các frame chạy trên
cùng mảng banked có FIFO/stall; input trùng được tái dùng chính xác.

C replay kiểm mọi input sống, không gọi lại kernel đã thay và không fallback.
Trace cố định qua file là co-simulation chức năng, không phải bus accelerator thời gian thực.
Đã có C differential trên NTT q12289 và chứng cứ ứng dụng cho nhóm kernel này;
FFT32/64, ứng dụng q3329, full RTL controller và signoff/side-channel vẫn ngoài kết quả.

## 18. Lõi kernel tự điều khiển — chốt ở mức mô phỏng

[Thiết kế và kết quả](docs/autonomous_kernel_rtl.md),
[kernel](study/results/kernel_engine.json),
[C replay](study/results/kernel_application.json),
[AXI-Lite](study/results/kernel_axil.json).

Đã thêm RAM chia bank, ROM bundle, stage/row controller, FFT complex 3M,
add/sub và chuẩn hóa ngay trong RTL. C chỉ gửi nguyên kernel và dùng output;
không dựng frame số học hoặc tính các tầng transform như mục 17.
5.992 kernel/325.492 word khớp oracle/reference, gồm toàn bộ 5.472 lời gọi C.
Bốn chữ ký N512/N1024 khớp byte baseline và được verifier độc lập chấp nhận.

FFT128 giữ đúng contract R8; FFT32/64 chỉ được xác nhận contract riêng.
NTT q12289 và q3329 dùng profile cố định, chưa q tùy ý/BASEMUL.
FFT controller hiện serial butterfly; chưa tận dụng hết lane hẹp hoặc đạt II=1
cho cả kernel. Ba scratch store 64 bank ×16 bit ×128 row, tổng 48 KiB.

AXI-Lite qua 15 kernel và kiểm handshake/strobe/backpressure. Theo phạm vi hiện tại,
chỉ cần mô phỏng để chốt đường số học và chức năng kernel. Giữ mảng nhân dùng chung,
ghép FFT rộng, NTT một/hai tầng, ROM và map bank hiện tại làm baseline RTL đã kiểm chứng.
Không cần xử lý Vivado, hoàn thiện block design hoặc nạp ZCU106 trong giai đoạn này.

FFT128 đã đối chiếu C R8; không suy rộng chứng cứ đó sang độ chính xác PQC của FFT32/64.
16 tile, controller FFT tuần tự và 48 KiB scratch là cấu hình baseline đã mô phỏng,
chưa phải lựa chọn tối ưu về throughput hay tài nguyên. Nếu cần chốt mức song song,
đánh giá tiếp cycle/kernel, mức sử dụng lane và stall ngay trong mô phỏng.
PPA arithmetic island ở mục trước không đại diện cho lõi mới có RAM/controller.
Các file ZCU106 giữ lại để dùng ở giai đoạn sau; chưa có bitstream hay kết quả board.

## 19. Profiling cycle, lane và stall để chọn mức song song

[Báo cáo](docs/kernel_parallelism_profile.md),
[số đo RTL](study/results/kernel_profile.json),
[phân tích cấp dữ liệu FFT batch](study/results/fft_batch_supply.json).

Đã chạy lại 5.992 kernel với monitor chỉ đọc, hai lượt không pause/có pause;
650.984 word output khớp file RTL dùng trong kiểm chứng C. Giữ nguyên datapath,
RAM, FSM và precision. Không chạy FPGA.

FFT N1024 mất 52.992 cycle ở cả W32/64/128. Controller dùng 23 cycle/butterfly,
chỉ phát ba real-product frame; lane dùng/frame lần lượt 6,25% /25% /100%.
Mật độ slot lá nhân trên toàn kernel lần lượt 0,82% /3,26% /13,04%.
Đó là metric công việc được giao, không phải công suất hoặc số phép nhân bit tối thiểu.

NTT phát một frame/10 cycle. N8 dùng hai trong 16 tile; N16 dùng bốn, N32 dùng tám.
q12289 N1024 cần 800 cycle; q12289/q3329 N256 đều 160 cycle do cùng bốn lượt,
dù q3329 có một tầng tail. Tái sử dụng hai tầng đã giảm số lượt dữ liệu;
controller chưa chồng lấp các frame. Lượt không pause không có input-ready stall
hay output backpressure, FIFO chỉ đạt một entry.

Quyết định: **giữ 16 tile làm baseline, chưa coi là tối ưu**. Ưu tiên chồng lấp đọc/tính/ghi,
batch FFT hẹp và gom nhiều job NTT nhỏ. Phân tích địa chỉ cho thấy batch FFT32
16 butterfly có thể cần 16 root ở tầng cuối; ROM FFT hiện chỉ đọc một root/cycle.
FFT128 một butterfly cũng có thể cần 2–4 lượt đọc do map bank. Phải xử lý cấp dữ liệu
và twiddle đồng thời với packing, không suy ra speedup từ số lane lý thuyết.

Chưa sweep RTL mảng 4/8/16/32 tile: bảng capacity trong báo cáo là phân tích slot,
không phải cycle/area đo của các mảng khác. Giảm số tile cần temporal fusion FFT128
và kiểm lại số học; tăng tile cần controller và băng thông khai thác được phần thêm.

## 20. Bản vẽ ý tưởng RTL v2 — để triển khai tiếp

[Hình và đặc tả ý tưởng](docs/rtl_concept_v2.md). Chỉ sửa bản vẽ/mô tả; không
thay RTL đã kiểm chứng, không tuyên bố controller/batching mới đã chạy mô phỏng.

Đã thể hiện pre-add FFT 3M, giữ K và collector p0/p1/p2 theo context/lane;
NTT giữ A cho CT hoặc A+B cho GS; root và side-data đi cùng valid/ready.
Đã vẽ nhóm tile, sign theo limb cao nhất, độ rộng tích giữ và rounding từng product.

Đề xuất hai context ping-pong, coefficient bank service nhiều lượt khi trùng bank,
FFT root prefetch từ một cổng complex root/cycle vào buffer 16/4/1 lane,
NTT root bundle 16 bank ×48 bit. Chỉ phát batch khi đủ dữ liệu/root. Đổi cấu hình
sau khi drain; qua tầng mới sau khi các write đã commit. Map bank đa job và độ
sâu pipeline/buffer vẫn cần người triển khai quyết định, chưa suy ra speedup.

## 21. Implementation specification 1.0

[Bộ đặc tả triển khai REF16](spec/FlexTransform/1.0/README.md) khóa số học,
native interface, bank/byte layout, đa job NTT, context, pause/flush và verification
traceability. Đây là candidate baseline để người thiết kế viết RTL; không thêm
RTL hay tuyên bố các block mới đã signoff. Số bank/map/job packing của REF16
được cụ thể hóa trong spec; latency, RAM macro và queue depth cần công bố trong
implementation manifest. Ranh giới commit là memory pass, cho phép hai tầng
NTT fused trong cùng tile không ghi intermediate vào RAM.
