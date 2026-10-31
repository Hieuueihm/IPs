# FlexTransform v1 — kiến trúc và giả thuyết đã chốt

| Thuộc tính | Giá trị |
|---|---|
| Ngày | 30/10/2026 |
| Trạng thái | **Chốt để triển khai.** Thay đổi sau ngày này đi qua change request (CR) |
| Nền | [spec 1.0 / REF16](../spec/FlexTransform/1.0/README.md); mọi điều không nêu ở đây giữ nguyên spec 1.0 |
| Thay thế | [Đề xuất v1](architecture_v1_proposal.md) (giữ để tham khảo phân tích) |
| Bằng chứng số | [model/flex_v1_projection.py](../model/flex_v1_projection.py), [model/res32_bank_map.py](../model/res32_bank_map.py), [model/arch_checks.py](../model/arch_checks.py) |
| Cổng hồi quy bắt buộc | 5 992 kernel khớp như hiện tại; bốn chữ ký N512/N1024 khớp từng byte và qua verifier |

Nhãn: **[đo]** kết quả RTL đã có; **[model]** đếm chính xác; **[dự báo]** model + giả định ghi rõ.

## 1. Luận điểm của đề tài

> Một fabric gồm 64 leaf 16×16 có chọn dấu thực hiện FFT fixed-point ở ba độ rộng 32/64/128 bit,
> mỗi độ rộng khớp bit một contract reference (ký FN-DSA: Q64.64 của R8; keygen FN-DSA: Q32.32 của
> NTRUGen), và NTT ở hai độ rộng residue 16/32 bit. Một controller batch co giãn theo độ rộng biến toán hạng
> hẹp hơn thành nhiều butterfly hơn mỗi chu kỳ, trong giới hạn cấp dữ liệu bank và twiddle đã đo.

Không tuyên bố "đầu tiên". Phần tách lane NTT theo độ rộng residue đã có tiền lệ (P1, R10) và chỉ là để
đủ chức năng. Đóng góp nằm ở trục FFT, cơ chế batch và hai tầng NTT gộp.

## 2. Giả thuyết và tiêu chí chấp nhận

Đo trên RTL v1, cùng harness profiling của [kernel_parallelism_profile](kernel_parallelism_profile.md).
Cycle tính từ sau START đến DONE, không pause.

| ID | Giả thuyết | Tiêu chí chấp nhận | Bị bác bỏ khi | Dự báo |
|---|---|---|---|---|
| **H1** | Batch theo độ rộng (CR-A2) tạo trục precision cho FFT và IFFT | N1024: FFT T32 ≤ 700, T64 ≤ 2 300, T128 ≤ 8 500; IFFT ≤ 770 / 2 530 / 9 350 (gồm lượt chia cuối). T128/T32 ≥ 10 và T128/T64 ≥ 3 cho cả FFT và IFFT; N512: T128/T32 ≥ 8. Ablation chỉ A1: T128/T32 ≤ 2. Ngưỡng đúng với L đo ≤ 16 | T128/T32 < 4 khi có A2 | FFT = IFFT trước bước chia: 552 / 1 864 / 7 496 (N1024), 264 / 832 / 3 264 (N512); chỉ A1: 4 680 / 5 192 / 7 496 |
| **H1n** | Controller pipeline đưa NTT tới gần trần | Với L đo = latency một frame (từ đọc đầu đến commit ghi cuối): T ≤ 1,25 × M(L), M = Σ lượt (frame + L); hai job xen kẽ M = Σ lượt max(2·frame, frame + L) / 2. Tại L = 9: q12289 N1024 ≤ 156, N256 ≤ 65, hai job N256 ≤ 33/job, RES32 N256 ≤ 125 | T > 2 × M(L) hoặc N1024 > 400 | M(9) = 125 / 52 / 26 / 100 |
| **H2a** | Linh hoạt rẻ so với core cố định W128 (WFIX) | Diện tích flex ≤ 1,35 × WFIX; throughput/diện tích ở W32 ≥ 7 × WFIX; ở W128 ≥ 0,75 × WFIX. "Throughput W32 của WFIX" = cùng transform N chạy ở Q64.64 (không cùng output) | Không đạt cả hai ngưỡng W32 | — |
| **H2b** | Phạt so với NTT RES16 chuyên dụng có giới hạn | Diện tích flex ≤ 1,5 × NTT chuyên dụng (cùng 64 leaf và bộ nhớ); cycle NTT ≤ 1,1 × | Diện tích > 2 × | Cụm đã đo +31,77% [đo] |
| **H3** | Ghép tích theo contract khớp bit reference | 0 sai khác trên mọi vector; chữ ký khớp byte | Một sai khác | **Đã đạt** [đo] |
| **H4** | Hai tầng NTT gộp giảm một nửa traffic với chi phí nhỏ | Số lượt dữ liệu N1024 = 5 (thay vì 10); thêm ≤ 3% GE so với cụm chỉ một tầng | Thêm > 10% GE | 5 lượt, +1,10% GE [đo] |
| **H5** | Cùng fabric chạy W128 của ký và W64 của keygen trong một reference FN-DSA | NG64 khớp bit `vect_FFT`/`vect_iFFT`; keygen thay kernel FFT bằng RTL cho khóa khớp từng byte (≥ 2 seed mỗi N512/N1024) | Một sai khác | — |
| **H6** | Lớp RES32 chạy đúng, không xung đột bank | Khớp NTT/INTT Dilithium (sau đổi biểu diễn); bộ đếm xung đột bank = 0 | Một sai khác hoặc xung đột | Không xung đột [model] |

**Baseline cho H2** (tổng hợp cùng flow Yosys + OpenSTA Nangate45):
- **WFIX:** cùng bộ nhớ, controller và 64 leaf, chỉ FFT W128; không có lane hẹp và NTT.
- **NTT chuyên dụng:** cùng bộ nhớ và 64 leaf, chỉ RES16.
- **SSEP:** tổng các core chuyên dụng; chỉ báo cáo phụ.
- **Cách tính diện tích:** cell area không gồm RAM và ROM ở mọi thiết kế; RAM/ROM báo riêng theo số bit
  (WFIX: ROM R8; flex: ROM R8 + ROM NG 16 KiB + bundle NTT). Không tổng hợp ROM thành logic ở một thiết kế
  này mà loại trừ ở thiết kế khác.

**Hình trung tâm:** throughput theo độ rộng toán hạng (FFT 32/64/128, NTT 16/32) trên cùng fabric, cạnh WFIX
và NTT chuyên dụng.

## 3. Cấu hình REF16-v1 (delta so với REF16)

| Tham số | REF16 | REF16-v1 |
|---|---|---|
| Tile / leaf | 16 × 4 leaf 16×16 | không đổi |
| Store | 3 × 64 bank × 16 bit × 128 row | không đổi; map vật lý spec 03.3 không đổi |
| Context | 2 | không đổi; dùng thêm cho xen kẽ job (CR-D) |
| FFT root read | 1 root phức/chu kỳ | **4 bank root, mỗi bank 1 root phức/chu kỳ**, bank = chỉ số root mod 4 (CR-B) |
| FFT root ROM | R8 Q64.64, 1 024 row | R8 Q64.64 + **ROM NTRUGen Q32.32, 1 024 row × 128 bit** (CR-E), cùng tổ chức 4 bank |
| NTT root bundle | 16 bank × 48 bit (RES16) | RES16 không đổi; **RES32: 4 bank × 96 bit**, bank = g mod 4, row = g >> 2 (CR-C) |
| Reducer | RES16 compact | RES16 compact chung 3329/12289 (4/tile) + **RES32 8380417 (1/tile)** |
| `cmd_fmt_i` | 2 bit | **3 bit**, lấy 1 bit từ `cmd_reserved_i` (còn 7 bit) |

## 4. Format, profile và opcode

| fmt | Tên | Bit/phần tử | Opcode | Contract |
|---:|---|---:|---|---|
| 0 | Q16.16 | 32 | FFT family | spec 01, không có reference |
| 1 | Q32.32 | 64 | FFT family | spec 01, không có reference |
| 2 | Q64.64 | 128 | FFT family | spec 01 = R8 |
| 3 | RES16 | 16 | NTT family | spec 01 |
| **4** | **RES32** | 32 | NTT, INTT, TOMONT, MODMUL | mục 5.2 |
| **5** | **NG64** (Q32.32 NTRUGen) | 64 | FFT, IFFT; logn 1..10 | mục 5.1 |
| 6–7 | dự trữ | — | — | BAD_FMT |

| Profile | q | fmt | logn | Ghi chú |
|---:|---:|---|---|---|
| 0 | 12289 | RES16 | 3..10 | không đổi |
| 1 | 3329 | RES16 | 3..8 | không đổi |
| **2** | **8380417** | RES32 | **8** | ML-DSA; 8 tầng, đều paired |
| 3 | — | — | — | dự trữ |

Số job (CR-D, thay spec 00.4): N ≤ 32 giữ như spec; **N ≥ 64: jobs ∈ {1, 2}**. Hai job dùng hai context,
xen kẽ theo lượt (pass); không trộn hai job trong một frame. Job j đặt từ word k = j·N (RES16) hoặc k = j·2N (RES32).

## 5. Contract số học mới

### 5.1 NG64 — FFT Q32.32 theo NTRUGen (CR-E)

Nguồn: thư mục `ntrugen/` đi kèm R8 commit `ad1e5bf7714d53230ad457364db8a46a1b459c94`
(`falcon_keygen_make` gọi `falcon_ntrugen_keygen`). Biên dịch **`NTRUGEN_AVX2 = 0`**; build AVX2 là
reference khác cho tới khi differential chứng minh bằng nhau. wrap64 diễn giải có dấu.

```text
mul(x, y)  = wrap64(floor(x·y / 2^32))                  // fxr_mul: nhân có dấu, cắt bớt
add, sub   = wrap64(x ± y);  conj(s) = (s_re, wrap64(−s_im))
half(v)    = floor(wrap64(v + 1) / 2)                   // fxr_div2e(v, 1): cộng rồi dịch số học
cmul(s, y): z0 = mul(s_re, y_re); z1 = mul(s_im, y_im)
            z2 = mul(wrap64(s_re + s_im), wrap64(y_re + y_im))
            re = wrap64(z0 − z1); im = wrap64(z2 − wrap64(z0 + z1))

FFT  (lm = 1 .. logn−1, cùng lịch chỉ số và bố cục với FFT của spec):
     s = GM_NG[m + i];  y ← cmul(s, y);  (x, y) ← (x + y, x − y)
IFFT (lm = logn−1 .. 1):
     s = conj(GM_NG[m + i]);  z1 = half(x + y);  z2 = cmul(s, half(x − y))
     KHÔNG có bước chia cuối
```

- `GM_NG` chép nguyên bit từ `GM_TAB[1024]` trong `ng_fxp.c` ở commit trên; ghi SHA vào manifest.
- Trên phần cứng: làm tròn tại tap dùng **bias = 0** (floor). Vẫn bỏ được các hạng tích ngoài 3W/2 = 96 bit,
  vì floor(P/2^32) mod 2^64 chỉ phụ thuộc P mod 2^96.
- iFFT cần hai bộ `half` (nhánh tổng và nhánh hiệu, trước bộ nhân) mỗi butterfly.
- Batch như W64: 4 butterfly, 4 tích/chu kỳ.
- **Đã kiểm bằng code** ([arch_checks](../study/results/arch_checks.md), mục A2): hai đường `fxr_mul` (int128 và
  limb 32 bit) bằng công thức trên và bằng cây phần cứng bias 0 (leaf 16 và 32) trên 100 081 cặp;
  `fxr_div2e(v, 1)` bằng `half`; `vect_FFT`/`vect_iFFT` viết lại khớp lịch chỉ số R8 với các primitive trên,
  logn 2..10. Chưa chạy trên bảng `GM_TAB` thật và chưa so với binary C: việc đó thuộc H5.

### 5.2 RES32 — q = 8380417 (CR-C)

```text
Dữ liệu canonical [0, q) trong lane 32 bit; root lưu w·2^32 mod q
t = a·b                                         // tile ở chế độ 32×32
m = signed32(low32(t) · 58728449)               // q^(−1) mod 2^32
u = (t − m·q) / 2^32                            // ∈ (−q, q)
out = u + q nếu u < 0, ngược lại u               // = a·b·2^(−32) mod q
```

- Hằng số shift-add (đã kiểm trong arch_checks): q = 2^23 − 2^13 + 2^0; q^(−1) = 2^26 − 2^23 + 2^13 + 2^0 (mod 2^32).
- NTT: CT, 8 tầng negacyclic đầy đủ, root ζ = 1753 (bậc 512):
  `GM32[k] = 2^32 · 1753^bitreverse8(k) mod q`, theo cùng lịch chỉ số của spec 01.7.
- INTT: GS với `IGM32[k] = 2^32 · (1753^bitreverse8(k))^(−1) mod q`, cuối cùng nhân 256^(−1) mod q = 8 347 681 ở dạng canonical.
- **Bố cục:** hệ số c chiếm word16 k = 2c (nửa thấp) và 2c + 1 (nửa cao), như FFT với LIMBS = 2.
  Với map vật lý của spec, hai nửa luôn ở cặp bank (2s, 2s + 1) cùng row.
- **Lịch phát:** 4 frame paired/chu kỳ theo thứ tự nhóm của `ntt_banked_supply.groups`.
  [model] **không xung đột** cho cả 4 lượt N256, thuận và nghịch, cả dữ liệu lẫn root bundle
  (`model/res32_bank_map.py`, 128 chu kỳ).
- Chỉ hỗ trợ N = 256: ở lịch một tầng hoặc N1024, map hiện có xung đột 2 lượt [model].
- Differential (H6): so với NTT/INTT của pq-crystals Dilithium sau khi đổi biểu diễn (Montgomery,
  miền [−q, q]) và thứ tự; harness phải ghi rõ phép đổi.

### 5.3 Quan hệ với spec 1.0

Spec yêu cầu mọi mâu thuẫn phải thành change request. Các CR dưới đây thay thế đúng phần ghi ở cột 2;
phần còn lại của spec giữ nguyên.

| CR | Phần spec bị thay | Nội dung mới |
|---|---|---|
| C, E | 00.2 bảng fmt; FT-SCP-001..004 | fmt 3 bit: thêm 4 = RES32, 5 = NG64; 6–7 dự trữ |
| C | 00.3 bảng profile ("Profile 2/3 reserved") | Profile 2 = q8380417, chỉ fmt RES32, logn = 8 |
| D | 00.4 job (FT-SCP-005..008) | N ≥ 64: jobs ∈ {1, 2}; job j đặt từ word j·N (RES16) hoặc j·2N (RES32) |
| B | 00.5 `FFT_ROOT_READ_PORTS = 1`; 03.5 FT-ARC-005 ("một complex root/cycle") | 4 bank root, mỗi bank 1 root/chu kỳ, bank = chỉ số mod 4; thêm ROM NG |
| A2 | 03.5 FT-ARC-004 (SHOULD gom butterfly) | MUST: microbatch 16 / 4 / 1 theo W (NG64 = 4) |
| C | 03.4 FT-MEM-010..011 (mapping logic) | RES32: hệ số c ở word 2c, 2c + 1 (LIMBS = 2); map vật lý 03.3 không đổi |
| C | 03.6 root bundle | RES32 bundle 4 bank × 96 bit, bank = g mod 4, row = g >> 2 |
| C, E | 01 (contract số học) | Thêm mục 5.1 (NG64) và 5.2 (RES32) của tài liệu này |
| C, E | 02 `cmd_fmt_i` (2 bit), `cmd_reserved_i` (8 bit); `interface.json` `fmt_bits` | `cmd_fmt_i` 3 bit, `cmd_reserved_i` 7 bit, phải bằng 0 |

**Lỗi lệnh mới** (giữ thứ tự kiểm BAD_RESERVED → BAD_OP → BAD_FMT → BAD_PROFILE → BAD_LOGN → BAD_JOBS):

| Lỗi | Điều kiện mới |
|---|---|
| BAD_FMT | fmt 6–7; fmt 4 với opcode họ FFT; fmt 5 với opcode khác FFT/IFFT |
| BAD_PROFILE | profile 2 với fmt khác 4; fmt 4 với profile khác 2; profile 3 |
| BAD_LOGN | fmt 4 với logn khác 8; fmt 5 với logn = 0 |
| BAD_JOBS | N ≥ 64 với jobs > 2 |

## 6. Vi kiến trúc bắt buộc

| CR | Quy tắc |
|---|---|
| **A1** controller pipeline | Tách đọc / tính / ghi; scoreboard theo tag; đọc microbatch kế tiếp trong khi tính microbatch hiện tại. Butterfly trong một tầng độc lập nên không có hazard nội tầng. Tầng kế tiếp chỉ đọc sau khi mọi write của tầng hiện tại đã commit (spec 03, không đổi) |
| **A2** batch theo độ rộng | Spec 03.5 (FT-ARC-004/005) nâng từ SHOULD lên **MUST**: microbatch 16 / 4 / 1 butterfly cho W32 / W64 và NG64 / W128, butterfly liên tiếp theo lịch tầng. Ba nhịp tích (p0, p1, k) mỗi microbatch, II = 1 khi đủ dữ liệu, root và context. Đuôi tầng dùng `lane_mask`. Gather nhiều lượt khi trùng bank là hợp lệ; không bắt buộc đổi map FFT (map lý tưởng chỉ lợi thêm 3–7% [dự báo]) |
| **B** root store 4 bank | Bank = chỉ số root mod 4; dedupe root trùng trong microbatch; cache theo spec 03.5. Lượng tử hóa W32/W64 và tổng re+im giữ đúng spec 01.3 |
| **C** RES32 | Mục 5.2; 16 reducer RES32 (1/tile); bundle 4 bank × 96 bit |
| **D** xen kẽ job | Hai job N ≥ 64 cùng cấu hình chạy xen kẽ theo lượt trên hai context; rào chắn tính riêng từng job. [model] offset job 1 giữ frame paired không xung đột (RES16 N64..1024, RES32 N256; `model/res32_bank_map.py`) |
| **E** NG64 | Mục 5.1; bias tap chọn theo fmt; hai bộ half ở operand stage và collector cho IFFT |
| Không đổi | Cây ghép dịch cố định, bỏ hạng ngoài 3W/2, làm tròn một lần tại tap; hai tầng NTT RES16; reducer compact; ALU A±T wrap |

## 7. Kiểm chứng và báo cáo

| Bước | Kiểm chứng | Báo cáo bắt buộc |
|---|---|---|
| Mỗi CR | Cổng hồi quy (5 992 kernel, chữ ký) | Cycle, lane, stall; bộ đếm xung đột bank và chờ root |
| A1 | Ablation: chỉ A1 | Cycle FFT ba W, NTT; so dự báo mục 2 |
| A2 + B | R_tw ∈ {1, 2, 4} | H1 |
| D | 1 và 2 job | H1n |
| C | Dilithium differential; ngẫu nhiên + biên 0, 1, q−1 | H6 |
| E | NTRUGen differential trên trace keygen; keygen thay kernel → khóa khớp byte | H5 |
| Diện tích/timing | Flex, WFIX, NTT chuyên dụng, SSEP; cùng flow | H2a, H2b; overhead từng CR |
| Sai số | W32/W64 so với số học chính xác (SQNR, sai số tuyệt đối) | Đường cong precision–throughput (W32 chỉ cho xử lý tín hiệu) |

Nếu cycle đo lệch dự báo quá 30%, cập nhật `model/flex_v1_projection.py` theo latency thật trước khi đánh giá giả thuyết.

## 8. Thứ tự triển khai đề xuất

1. A1 → hồi quy, ablation.
2. A2 + B → H1.
3. D → H1n.
4. C → H6.
5. E → H5.
6. Tổng hợp WFIX / NTT chuyên dụng / SSEP → H2, hình trung tâm.

## 9. Ngoài phạm vi v1 và rủi ro còn lại

- **Ngoài v1:** RNS Montgomery tổng quát, BASEMUL của ML-KEM, RES32 khác N256, q tùy ý, NG64 cho CMUL/SPLIT/MERGE.
- **R10 (ICTA 2026)** mới đọc abstract: đọc toàn văn trước khi viết phần so sánh trong bài.
- **Thứ tự ra của NTT RES32 so với Dilithium** chưa đối chiếu: harness H6 phải xác định phép hoán vị nếu có.
- **Latency L thực tế** quyết định NTT N256 (48 / 64 / 80 cycle với L = 8 / 12 / 16); vì vậy ngưỡng H1n viết
  theo L đo, không theo một hằng số.
- **IFFT có thêm lượt chia cuối** (W32/64/128 theo spec): khoảng N·W / 1024 chu kỳ ở băng thông 64 × 16 bit,
  đã cộng vào ngưỡng IFFT của H1. NG64 không có lượt này.
- **Diện tích** chưa có số cho các CR; ngưỡng H2 có thể sai hướng. Nếu sai, báo cáo như kết quả âm, không sửa ngưỡng sau khi đo.
