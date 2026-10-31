# FlexTransform v1 — đề xuất kiến trúc hoàn chỉnh

> **Đã được thay bằng [kiến trúc chốt](architecture_v1.md).** Giữ lại để tham khảo phân tích. Hai điểm đã
> đổi khi chốt: RES32 dùng bố cục spec (word 2c, 2c + 1) và **không xung đột bank** ở N256
> (`model/res32_bank_map.py`), nên dòng "map hiện có 2 lượt" bên dưới không còn đúng; CR-E dựa trên
> mã NTRUGen đã đọc đủ (iFFT chia đôi cả hai nhánh mỗi tầng, không chia cuối).

> Ngày 30/10/2026. **Đề xuất**, chưa có RTL cho các thay đổi bên dưới. Không sửa ARCHITECTURE.md hay spec.
> Nền: [ARCHITECTURE.md v0.4](../ARCHITECTURE.md) và [spec 1.0 / REF16](../spec/FlexTransform/1.0/README.md).
> Đây là **delta** trên REF16 (16 tile × 4 leaf16); không mở lại F16 so với R32. Thay đổi contract/profile
> được ghi là change request (CR) theo quy tắc của spec.
> Nhãn số liệu: **[đo]** từ RTL đã chạy; **[model]** đếm chính xác từ tham số/dữ liệu repo;
> **[dự báo]** model + giả định ghi rõ. Tính bằng [model/flex_v1_projection.py](../model/flex_v1_projection.py),
> kết quả [study/results/flex_v1_projection.md](../study/results/flex_v1_projection.md).
> Cổng hồi quy cho mọi CR: 5 992 kernel khớp như hiện tại và bốn chữ ký N512/N1024 khớp từng byte.

## 1. Chẩn đoán: hai trục linh hoạt về chức năng, chưa linh hoạt về hiệu năng

| Hiện trạng | Bằng chứng |
|---|---|
| FFT32/64/128 N1024 cùng 52 992 cycle; controller 23 cycle/butterfly; lane dùng 6,25% / 25% / 100% khi phát | [đo] [profiling](kernel_parallelism_profile.md) |
| NTT 1 frame / 10 cycle; N8 dùng 2/16 tile | [đo] cùng nguồn |
| Trục modulus chỉ có q3329/q12289, cùng lane 16 bit | [model] spec 00.3 |
| FFT128 khớp bit R8; 5 992 kernel khớp; chữ ký khớp byte | [đo] [autonomous_kernel_rtl](autonomous_kernel_rtl.md) |
| Island Nangate45 0,450294 mm² (chưa SRAM/CTS); stall/queue/routing +28,73% | [đo] [stream_core_results](stream_core_results.md) |
| Cụm dùng chung đắt hơn NTT chuyên dụng 31,77% GE; compact reducer −3,76% GE | [đo] [reducer_radix4_results](reducer_radix4_results.md) |

Nếu precision thấp hơn và residue hẹp hơn không biến thành nhiều việc hơn mỗi chu kỳ, "hai chiều linh hoạt"
không có giá trị hiệu năng và không bảo vệ được novelty. v1 nhắm đúng việc đó, không thêm tile,
không đổi số học đã kiểm chứng.

## 2. Ý tưởng trung tâm và giới hạn của nó

### 2.1 Luật lane theo độ rộng toán hạng [model]

Một tích w bit chiếm (w/16)² leaf, nên mảng 64 leaf cho **64 / (w/16)² tích mỗi chu kỳ**,
bất kể là tích thực FFT hay tích modulo NTT.

| Miền | Lớp | Leaf/tích | Tích/chu kỳ | Việc/chu kỳ |
|---|---|---:|---:|---|
| FFT | W32 (Q16.16) | 4 | 16 | 5,33 butterfly (3M) |
| FFT | W64 (Q32.32) | 16 | 4 | 1,33 butterfly |
| FFT | W128 (Q64.64, R8) | 64 | 1 | 0,333 butterfly |
| NTT | RES16: 3329, 12289 | 1 | 64 | 64 butterfly-tầng |
| NTT | RES32: 8380417 (đề xuất) | 4 | 16 | 16 butterfly-tầng |

RES32 dùng đúng cấu hình tile 32×32 mà FFT32 đang dùng, nên không cần bộ nhân mới.

### 2.2 Phần nào không mới

Unified FFT/NTT của ICASSP 2025 (P1, [ghi chú](paper_notes/01_unified_fft_ntt.md)) đã dùng 4 bộ nhân
Karatsuba 32 bit dựng từ bộ nhân 16 bit, và chạy **1 / 2 / 4 butterfly mỗi chu kỳ** cho FFT 32 bit / ML-DSA /
ML-KEM. Nghĩa là **"residue hẹp hơn → nhiều lane hơn" ở miền NTT đã có tiền lệ**. R10 (ICTA 2026) cũng tách
bộ nhân con 14 bit thành 8 lane NTT. Lớp RES32 vì vậy là để đủ chức năng (ML-DSA), không phải novelty.

Khác biệt có thể bảo vệ nằm ở **miền FFT** và ở **cơ chế khai thác**:
1. FFT ba độ rộng (32/64/128) trên cùng fabric với contract số học chính xác; W128 khớp bit R8 và W64 có
   workload FN-DSA thật (mục 3.3).
2. Batching co giãn theo độ rộng, biến precision thấp thành throughput dưới giới hạn bank và twiddle đã đo.
3. Hai tầng NTT gộp bên trong fabric dùng chung.

## 3. Kiến trúc v1

~~~text
             native valid/ready command + host line (spec 02)
                               |
   +---------------- Command / batch / context unit ----------------+
   | gom batch cùng cấu hình; 2 context ping-pong; job packing      |
   +---------------+----------------------------+-------------------+
                   |                            |
    Bank service + gather/scatter        Twiddle subsystem
    3 store × 64 bank × 16 bit           FFT: root store xen kẽ R_tw = 4 (+ ROM NTRUGen nếu CR-E)
    RES32 = cặp bank                     NTT: bundle RAM theo profile
                   |                            |
          Operand stage: pre-add 3M; GS pre-sub (+ halving nếu CR-E); giữ K; NTT giữ A / A+B
                               |
          Fabric 16 tile × 4 leaf16, bảng mode → nhóm leaf theo lớp độ rộng
                               |
          Cây ghép dịch cố định, tap: leaf | tile | 4 tile | 16 tile
               |                                   |
   FFT: làm tròn tại tap (half-up R8;      NTT reducer pool
        floor nếu CR-E), collector 3M,     RES16 compact chung 3329/12289 (4/tile)
        ALU A±T wrap, div2e cuối iFFT      RES32 8380417, R=2^32 biến thể trừ (1/tile)
               +-----------------+-----------------+
                                 |
     Controller: đọc | tính | ghi tách rời, scoreboard + tag (CR-A1);
     batch theo độ rộng 16/4/1 BF (CR-A2); mở tầng kế tiếp khi mọi write đã commit
~~~

### 3.1 Bảng ánh xạ mode

| Mode | Nhóm leaf | Lane/chu kỳ | Hậu xử lý | Dữ liệu/batch | Root/batch |
|---|---|---:|---|---|---|
| FFT W32 | 1 tile/tích | 16 tích | làm tròn, 3M, A±T | 16 BF | ≤ 16 root phức |
| FFT W64 | 4 tile/tích | 4 tích | như trên | 4 BF | ≤ 4 |
| FFT W128 | 16 tile/tích (58/64 leaf dùng) | 1 tích | như trên | 1 BF | 1 |
| NTT RES16 paired | 2 leaf/tầng/tile, 2 tầng | 64 modmul | R16 compact | 64 hệ số | 16 bundle × 3 root |
| NTT RES32 | 1 tile/modmul | 16 modmul | R32 8380417 | 16 hệ số paired / 32 một tầng | ≤ 16 root |

### 3.2 Danh sách CR

| CR | Nội dung | Loại thay đổi | Cần người dùng quyết |
|---|---|---|---|
| **A1** | Controller pipeline: tách đọc/tính/ghi, scoreboard theo tag, II = 1 theo batch | Vi kiến trúc; không đổi contract | — |
| **A2** | Batch co giãn theo độ rộng: 16 / 4 / 1 butterfly cho W32 / W64 / W128 | Vi kiến trúc | — |
| **B** | Root store FFT xen kẽ R_tw = 4 theo bit thấp chỉ số root, dedupe root trùng trong batch | Tham số REF16 (FFT_ROOT_READ_PORTS = 1) → profile mới | Có |
| **C** | Lớp RES32 + profile 2 = q8380417; cặp bank; reducer R32 | Contract mới; trường `fmt` 2 bit đã dùng hết → phải mở rộng mã hóa | Có |
| **D** | Xen kẽ hai job NTT N ≥ 64 bằng 2 context sẵn có | Spec 00.4 hiện chỉ cho 1 job khi N ≥ 64 | Có |
| **E** | Contract W64 theo NTRUGen cho keygen (mục 3.3) | Contract mới + ROM mới | Có |
| — | RNS Montgomery tổng quát, BASEMUL | Ngoài v1 | — |

Root của CR-B vẫn lấy nguyên từ asset R8 và lượng tử hóa theo spec 01.3; tổng re + im tạo **sau** lượng tử hóa.
Reducer RES32 dùng (T − m·q)/2^32 với m có dấu; hằng số shift-add đã kiểm trong [arch_checks](../study/results/arch_checks.md).

### 3.3 W64 có workload FN-DSA ngay trong reference đã pin (cơ sở cho CR-E)

Đọc mã ở commit R8 `ad1e5bf` (đã kiểm từng điểm dưới đây trong nguồn):

- `falcon_keygen_make` gọi `falcon_ntrugen_keygen` (thư mục `ntrugen/` đi kèm), trừ khi build với `TEST_REFERENCE`.
- NTRUGen gọi `vect_FFT` / `vect_iFFT` trong `ng_falcon.c` và `ng_ntru.c`.
- Kiểu `fxr`: Q32.32 trong `uint64_t`.
  - `fxr_mul` nhân có dấu 64×64, rồi lấy `z >> 32`: **wrap64(floor(x·y / 2^32))**, tức cắt bớt, không cộng nửa đơn vị.
  - Cộng/trừ wrap 64 bit.
- `fxc_mul` dùng 3M, cùng công thức với R8: re = z0 − z1, im = z2 − (z0 + z1).
- `vect_iFFT` là GS và chia đôi **ở mỗi tầng**: z1 = half(x + y), z2 = conj(GM_TAB) · half(x − y).
  - `half` = `fxr_div2e(x, 1)`: cộng 1, dịch phải số học (half-up), wrap.
  - Phần mã sau vòng lặp tầng chưa đọc hết; phải đọc đủ khi pin.
- Hằng số twiddle là bảng `GM_TAB[1024]` riêng ở dạng Q32.32, **không** lượng tử hóa từ R8.
- AVX2 tự bật nếu biên dịch với `-mavx2` (`NTRUGEN_AVX2`), nên phải pin cấu hình không AVX2 để có một đường tham chiếu.

Hệ quả:
- Trong cùng reference FN-DSA đã pin: **ký dùng W128, keygen dùng W64**. Đây là lý do ứng dụng cho trục precision.
  W32 vẫn chỉ dành cho xử lý tín hiệu, không tuyên bố dùng cho ký.
- Contract W64 của spec 1.0 (half-up, lượng tử từ R8, chia một lần cuối iFFT) **khác** NTRUGen ở ba điểm,
  nên CR-E cần:
  1. Một bit tắt bias làm tròn.
  2. Halving half-up ở cả hai đầu ra GS mỗi tầng.
  3. ROM riêng 1 024 × 128 bit (16 KiB).
- Phải chạy C differential với NTRUGen (A7) trước khi khẳng định khớp.

## 4. Phân tích định lượng

### 4.1 FFT N1024 [dự báo]

Giả định: II = 1 theo batch, đọc/ghi song song (1R + 1W/bank), rào chắn L = 8 chu kỳ/tầng. Batch và map bank
tái tạo đúng [fft_batch_supply.json](../study/results/fft_batch_supply.json) (script tự kiểm khớp).
Root store xen kẽ theo idx mod R_tw, đếm chính xác số lần đọc mỗi bank root.

| CR áp dụng | W | Batch | R_tw | Cycle/kernel | So với 52 992 [đo] | Tầng chặn bởi tính / dữ liệu / twiddle |
|---|---:|---|---:|---:|---:|---|
| A1 (chỉ pipeline) | 32 | 1 BF | 1 | 4 680 | 11,3× | 0 / 9 / 0 |
| A1 | 64 | 1 BF | 1 | 5 192 | 10,2× | 0 / 9 / 0 |
| A1 | 128 | 1 BF | 1 | 7 496 | 7,1× | 7 / 2 / 0 |
| A1 + A2 | 32 | 16 BF | 1 | 840 | 63,1× | 4 / 2 / 3 |
| A1 + A2 + B | 32 | 16 BF | 4 | 552 | 96,0× | 6 / 2 / 1 |
| A1 + A2 | 64 | 4 BF | 1 | 1 928 | 27,5× | 7 / 1 / 1 |
| A1 + A2 + B | 64 | 4 BF | 4 | 1 864 | 28,4× | 8 / 1 / 0 |
| A1 + A2 (+ B) | 128 | 1 BF | 1 / 4 | 7 496 | 7,1× | 7 / 2 / 0 |

Trần chỉ-tính-toán [model]: W32 ≥ 432, W64 ≥ 1 728, W128 ≥ 6 912 cycle (tối đa 122,7× / 30,7× / 7,7×).
Map bank lý tưởng cải thiện thêm 3–7%. Độ nhạy L ∈ {8, 12, 16} với A1 + A2 + B: W32 552 / 588 / 624,
W64 1 864 / 1 900 / 1 936, W128 7 496 / 7 532 / 7 568.

Đọc bảng:
- **Chỉ pipeline (A1) không tạo trục precision:** W32 : W64 : W128 = 4 680 : 5 192 : 7 496, gần như phẳng,
  vì batch một butterfly bị chặn bởi bank ở W32/W64.
- **Batch co giãn (A2) mới tạo trục precision:** với A1 + A2 + B, tỷ lệ là 1 : 3,4 : 13,6, gần lý tưởng 1 : 4 : 16.
  Đây là cơ chế cần đưa vào claim; A1 là kỹ thuật chuẩn.
- **W32 cần CR-B:** với 1 root/chu kỳ, 3 tầng cuối bị chặn bởi twiddle.
- **W128 bị chặn bởi tính toán** và một phần bởi map bank (2 tầng); không có lợi từ CR-B.

### 4.2 NTT [dự báo]

L của frame NTT hiện tại suy ra từ FSM đã đo là khoảng 9 (READ, LATCH, ISSUE, 5 chu kỳ chờ mảng, WRITE).

| Profile | N | Job | Đo/job | Dự báo/job, L = 8 | L = 12 | L = 16 | Trần L = 0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| q12289 | 1024 | 1 | 800 | 120 (6,7×) | 140 | 160 | 80 |
| q12289 | 1024 | 2 xen kẽ (CR-D) | 800 | 80 (10,0×) | — | — | — |
| q12289 | 256 | 1 | 160 | 48 (3,3×) | 64 | 80 | 16 |
| q12289 | 256 | 2 xen kẽ (CR-D) | 160 | 24 (6,7×) | — | — | — |
| q3329 | 256 | 1 | 160 | 48 (3,3×) | — | — | 16 |
| q12289 | 8 | 8 gom | 20 | 2,2 (8,9×) | — | — | — |
| q8380417 RES32, map không xung đột | 256 | 1 | — | 96 | 112 | 128 | 64 |
| q8380417 RES32, map hiện có | 256 | 1 | — | 160 | — | — | — |

- Với N = 256, rào chắn chiếm phần lớn thời gian (4 frame/lượt so với L ≈ 9): CR-D quan trọng ngang A1.
- **RES32 với cặp bank theo thứ tự nhóm hiện có cần 2 lượt đọc mỗi chu kỳ** (mục 3b của script; thử ba map,
  N = 256/1024, paired và một tầng). Cần thiết kế map siêu bank riêng; nếu không, RES32 chạy khoảng nửa tốc độ.
- Hai tầng gộp [đo]: N1024 dùng 5 lượt dữ liệu thay vì 10.

### 4.3 Diện tích: chưa có số mới

Chưa có RTL cho các CR, nên không có số diện tích. Điểm tựa đã đo: island 0,450 mm², chi phí cấu hình +28,73%,
cụm dùng chung +31,77% so với NTT chuyên dụng. Phần dự kiến thêm: scoreboard và buffer batch (A1/A2),
root store xen kẽ (B), 16 reducer R32 và mux cặp bank (C), bias/halving và ROM 16 KiB (E). Mỗi phần đo riêng ở A3/A4.

## 5. Novelty: giả thuyết có thể bác bỏ

Không dùng chữ "đầu tiên". Mỗi đóng góp là một giả thuyết, đi kèm thí nghiệm và baseline.

| ID | Giả thuyết | Thí nghiệm | Baseline | Trạng thái |
|---|---|---|---|---|
| H1 | Với A2, throughput FFT tỷ lệ theo 64/(w/16)² trên ba độ rộng, trong X% so với trần ở N ≥ 256; không có A2 thì không | Profiling RTL A1 rồi A1 + A2 trên 5 992 kernel | Controller hiện tại; trần model | Dự báo có |
| H2a | Cùng diện tích với một core cố định W128 (WFIX), core linh hoạt cho throughput W64/W32 cao hơn ~3,4× / ~13,6× với chi phí cấu hình đo được | Tổng hợp WFIX và core linh hoạt cùng flow | WFIX (PLAN 10.1) | Chưa đo |
| H2b | So với NTT RES16 chuyên dụng, phạt diện tích của core linh hoạt nằm trong mức báo cáo | Như trên | NTT chuyên dụng (cụm đã đo +31,77%) | Một phần |
| H2c | Tổng các core chuyên dụng cùng throughput đỉnh (SSEP) lớn hơn core linh hoạt | Như trên | SSEP | Gần như hiển nhiên; chỉ báo cáo phụ |
| H3 | Ghép tích theo contract (bỏ hạng ngoài 3W/2, làm tròn một lần tại tap) khớp bit reference | Hồi quy R8, chữ ký | C R8 | **Đã có bằng chứng** |
| H4 | Hai tầng NTT gộp trong fabric dùng chung giảm một nửa traffic với chi phí nhỏ | Đếm word, cycle, GE | NTT một tầng | Traffic [đo] 5 thay vì 10 lượt; +1,10% GE [đo] |
| H5 | Một fabric phục vụ cả W128 của ký và W64 của keygen trong cùng reference FN-DSA | CR-E + differential NTRUGen | C R8 + NTRUGen | Chưa làm |

**Hình trung tâm của bài:** throughput theo độ rộng toán hạng cho FFT và NTT trên cùng fabric,
cạnh WFIX và core NTT chuyên dụng, cùng flow Nangate45. SSEP chỉ đặt làm tham chiếu phụ.

**Đối chiếu công trình gần:**

| Công trình | Đã làm | Khác biệt còn lại |
|---|---|---|
| Unified FFT/NTT, ICASSP 2025 (P1) | 4 Karatsuba 32 bit từ bộ nhân 16 bit; FFT 32 bit (Q16.15); 1/2/4 butterfly/chu kỳ cho FFT/ML-DSA/ML-KEM | FFT nhiều độ rộng tới 128 bit với contract chính xác; batching co giãn dưới giới hạn bank/twiddle; hai tầng NTT gộp |
| OpenNTT (P2) | Chọn FFT/NTT và q khi tạo lõi | Đổi lúc chạy trên cùng fabric |
| BitFusion (P3) | Ghép/tách bitwidth cho DNN | Làm tròn theo contract, reduction modulo |
| Fused FP64/modular, ICTA 2026 (R10, mới đọc abstract) | Bộ nhân con 14 bit ghép thành mantissa FP64 (Karatsuba hai tầng); tách thành 8 lane NTT; Artix-7 162 MHz, 3 081 LUT, 9 DSP | Một precision FP64 so với fixed-point ba độ rộng khớp reference; **phải đọc toàn văn trước khi khóa claim** |

## 6. Kế hoạch phân tích

| ID | Phân tích | Mục đích | Công cụ |
|---|---|---|---|
| A1 | Trần tính/dữ liệu/twiddle/bank theo mode | Bảng mục 4 (đã có) | model/flex_v1_projection.py |
| A2 | Cycle, lane, stall sau A1, rồi A1 + A2, rồi + B, + D | H1; so với dự báo mục 4 | harness profiling hiện có |
| A3 | Diện tích/timing core linh hoạt, WFIX, NTT chuyên dụng, SSEP | H2a/b/c | Yosys + OpenSTA Nangate45 hiện có |
| A4 | Ablation: A1 so với A1 + A2, R_tw ∈ {1, 2, 4, 8}, số context ∈ {1, 2}, tap ghép, paired, compact/CSA | Đóng góp riêng của từng cơ chế | cùng flow |
| A5 | Hồi quy W128 khớp bit, chữ ký | Không đổi | C R8, verifier |
| A6 | Sai số W32/W64 theo độ rộng (SQNR, sai số tuyệt đối) cho FFT xử lý tín hiệu | Đường cong precision–throughput | golden model |
| A7 | C differential: pq-crystals Dilithium (RES32); NTRUGen không AVX2 (CR-E) | Khớp bit | harness C |
| A8 | Thời gian kernel trong keygen và ký FN-DSA; NTT ML-KEM/ML-DSA | Chỉ báo kernel | replay C hiện có |

## 7. Rủi ro và giới hạn

| Rủi ro | Hậu quả | Giảm thiểu |
|---|---|---|
| L thực tế của FFT lớn hơn 8 | W32 chậm thêm ~13% ở L = 16 | Đo L sau A1; độ nhạy đã tính |
| Root store xen kẽ không đủ ở map thật | W32 bị chặn bởi twiddle | Ablation R_tw; cache root giữa batch |
| Không tìm được map siêu bank RES32 không xung đột | RES32 nửa tốc độ | Thiết kế map trước RTL CR-C; chấp nhận nửa tốc độ nếu cần |
| NTRUGen khác contract ở nhiều điểm hơn đã thấy | CR-E tốn công | Đọc đủ mã, differential trước RTL |
| R10 trùng cơ chế nhiều hơn abstract | Novelty yếu đi | Đọc toàn văn trước A3 |
| Dự báo khác đo | Kết luận sai | Claim chỉ dùng số [đo]; dự báo chỉ để chọn thứ tự |

## 8. Trình tự triển khai

1. **A1** → A2, A5. Nếu cycle đo lệch xa dự báo, sửa model trước khi đi tiếp.
2. **A2 + B** → A2 cho W32/W64, A4 phần batching và R_tw.
3. **D** → A2 cho N = 256/1024.
4. **Thiết kế map siêu bank RES32**, rồi **C** → A7 (Dilithium), H2b.
5. **E** nếu differential NTRUGen qua → H5.
6. **A3 + A4 đầy đủ** → hình trung tâm. RNS/BASEMUL để v2.
