# FlexTransform v0.3 — core butterfly trên mảng nhân ghép/tách

> Đề xuất kiến trúc, cập nhật 25/10/2026. Chưa phải RTL core hay kết quả PPA.
> Phạm vi: số học, ghép tích, operand routing, giao diện. Chưa thiết kế scheduler/RAM/DMA.
> **Mọi con số trong tài liệu được kiểm bằng [model/arch_checks.py](model/arch_checks.py)**
> (kết quả: [study/results/arch_checks.md](study/results/arch_checks.md)), trừ khi ghi rõ là giả định.
> Lịch sử: [v0.1](docs/plan_history/ARCHITECTURE_v0.1_2026-10-25.md),
> [v0.2 trước review](docs/plan_history/ARCHITECTURE_v0.2_before_review_2026-10-25.md),
> [v0.2 trước khi làm gọn](docs/plan_history/ARCHITECTURE_v0.2_before_cleanup_2026-10-25.md).

## 1. Tóm tắt quyết định

| Nội dung | Hướng v0.3 | Trạng thái |
|---|---|---|
| Contract FFT | Theo R8 đã pin (mục 3): Q64.64, nhân 3M, làm tròn half-up từng tích, cộng/trừ wrap | Chốt cho FFT128; FFT32/64 dùng cùng quy tắc nhưng không có reference |
| Nhân phức | **3M** (không phải 4M): 4M lệch phần ảo so với R8 | Chốt theo contract |
| iFFT | Cấu trúc **GS** của R8, chia cuối bằng `fpr_div2e` | Bắt buộc nếu cần khớp bit |
| NTT nghịch | CT-only (thêm một lượt pointwise) hoặc GS | So sánh bằng PPA |
| Leaf | So F16 (leaf 16×16) với R32 (leaf 32×32) | Chưa chốt |
| Ghép tích | Cây nhị phân dịch cố định, tap theo width, bỏ hạng không ảnh hưởng kết quả | Kiểm bit-exact ở model |
| Product bus | 16 khe × 32 bit; làm tròn FFT tại gốc cây | Đề xuất |
| Montgomery tổng quát | Tích phụ m, m·q đi đường nội bộ; bus chỉ mang T | Đề xuất |
| Reducer 3329/12289 | Một mạng shift-add chung, bật/dấu theo profile | Đề xuất; so với hai mạng riêng |
| Twiddle NTT | Một RAM, nạp từ seed khi đổi context; quy tắc root nghịch theo bậc root | Đề xuất |
| Twiddle FFT | ROM chứa đúng hằng số của R8 (kèm tổng re+im) | Chốt theo contract |
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
   tổng của dữ liệu cần một bộ cộng 128 bit trước bộ nhân.
3. iFFT cần đường **GS**: hiệu x − y (wrap) đi vào bộ nhân, sau đó lại cộng trước cho 3M
   (hai bộ cộng nối tiếp trước bộ nhân); tổng x + y đi thẳng ra.
4. Cộng/trừ butterfly và gộp Re/Im **wrap W bit**, không có guard bit. Muốn khớp bit thì phần cứng
   cũng phải wrap; cờ tràn chỉ có thể là tín hiệu debug không đổi dữ liệu.
5. Chia cuối iFFT là `fpr_div2e` với n = logn − 1 (cộng nửa đơn vị, wrap, dịch số học).

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

Context gồm q, R, biến thể Montgomery, hằng số, seed root, quy tắc root nghịch, N^(−1) và dạng biểu
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
- INTT dùng root nghịch và nhân N^(−1) đúng miền. Có thể dùng half_q(x) = (x + (x&1)·q) >> 1
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

Làm **trước RTL core**:

1. Dùng R8 đã pin (mục 3.1), giữ nguyên mã gốc.
2. Gắn hook vào các lời gọi FFT/iFFT, `poly_mul_fft`, split/merge trong keygen/sign để ghi vector
   (tham số, input, output, vị trí gọi), không đổi kết quả.
3. Golden model của core phải khớp bit các vector; testbench RTL dùng lại đúng các vector đó.
4. NTT: so với `mq_NTT`/`mq_iNTT` của Falcon cho 12289, reference pq-crystals cho 3329 và 8380417;
   prime RNS so với NTT số nguyên chính xác.
5. Nếu thay kernel vào luồng ký: chữ ký phải verify được bằng verifier gốc; kết luận về phân phối
   chữ ký giới hạn theo điều kiện của R8.

## 11. Bằng chứng hiện có và trình tự quyết định

- [model/arch_checks.py](model/arch_checks.py): mọi con số của tài liệu này (contract R8, 3M, cây,
  throughput, bus, Montgomery, root).
- [RTL tile L32](hdl/tile_l32.v), [RTL bốn leaf 16 ghép/tách](hdl/tile_l16x4.v); [phân tích tile](docs/tile_analysis.md).
- [Model liên tile v0.1](docs/intertile_model.md) và [model cây từng tích](model/product_tree_v02.py):
  dùng 4M (không phải contract hiện tại); đã chuyển sang làm tròn half-up, giữ để đối chiếu.
- [Phân tích số học](docs/arithmetic_reassessment.md), [model fusion v0.2](model/core_fusion_v02.py).

Trình tự:

1. Dựng bộ kiểm tra so sánh với R8 (mục 10); xác nhận contract mục 3 trên vector thật.
2. So F16/R32 cùng chức năng, cả cùng proxy lẫn cùng ngân sách area sau tổng hợp.
3. Tổng hợp cây ghép, operand routing (gồm cộng trước cho 3M và GS), làm tròn, reducer.
4. Định cỡ ALU, hiệu chỉnh, pairing và đường nội bộ Montgomery theo trần dữ liệu từng mode.
5. So 512/1024/2048 bit với ba trường hợp latency/batching (mục 8) và CT-only so với GS cho NTT;
   báo time/area/energy toàn core.
6. Chốt F16 hoặc R32 bằng kết quả; sau đó mới khóa scheduler và bố trí bộ nhớ.
