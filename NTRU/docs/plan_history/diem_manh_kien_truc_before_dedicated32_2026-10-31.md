# FlexTransform v1 — điểm mạnh và những gì có thể khẳng định trong bài báo

> Ngày 30/10/2026. Tài liệu làm việc, đi kèm [kiến trúc v1](architecture_v1.md). Mục đích:
> - xác định bài báo có thể khẳng định điều gì;
> - mỗi khẳng định cần bằng chứng gì;
> - cần làm thêm gì để khẳng định mạnh hơn.
>
> Chưa chọn hội nghị. Mọi con số tốc độ ở đây là **dự báo của mô hình**, chưa phải số đo.
>
> **31/10/2026:** cập nhật theo rút gọn lai (thay đổi 4 mới của kiến trúc): mục 2.2, 2.5, 3, 5. Bản trước:
> [plan_history/diem_manh_kien_truc_before_hybrid_reduction_2026-10-31.md](plan_history/diem_manh_kien_truc_before_hybrid_reduction_2026-10-31.md).

## 1. Câu chuyện của bài trong một câu

Lõi gồm một mảng 64 bộ nhân 16×16 và **một phép hậu xử lý duy nhất**. Lõi đổi được lúc chạy cả **độ chính xác FFT**
(32 / 64 / 128 bit) lẫn **modulus NTT**, và khớp từng bit với phần mềm FN-DSA thật. Giá của sự linh hoạt được trả bằng
**thời gian NTT 32 bit**, không phải bằng DSP. (Từ khi chuyển sang rút gọn lai, "một phép hậu xử lý duy nhất" chỉ đúng
cho làm tròn FFT và rút gọn lane 32 bit; 3329/12289 có 64 bộ rút gọn hằng riêng.)

## 2. Các điểm mạnh có thể khẳng định

### 2.1 Độ chính xác FFT thật sự đổi được thành tốc độ

**Khẳng định.** Trên cùng một lõi, hạ độ rộng FFT từ 128 bit xuống 64 bit thì nhanh khoảng 4 lần, xuống 32 bit thì
nhanh khoảng 13 lần. Dự báo ở N = 1024 là 7 496 / 1 864 / 552 chu kỳ. Chi phí LUT không quá 1,35 lần một lõi chỉ làm
FFT 128 bit.

**Vì sao mạnh.**
- Các lõi FFT/NTT hợp nhất đã đọc chỉ có **một** độ chính xác FFT:
  - bài ICASSP 2025: FFT fixed-point 32 bit;
  - bài ICTA 2026: dấu phẩy động 64 bit.
- Lõi hiện tại của mình có ba độ rộng nhưng cả ba cùng mất 52 992 chu kỳ. Nghĩa là "nhiều precision" mới có về chức
  năng, chưa có về tốc độ. Gom lô theo độ rộng là cơ chế tạo ra chiều này.

**Bằng chứng cần.**
- Giả thuyết 3: chu kỳ và tỉ lệ giữa các độ rộng. Báo cả tỉ lệ đạt được so với lý tưởng: 128 bit so với 32 bit dự báo
  13,6 lần, trong khi luật độ rộng cho 16 lần.
- Giả thuyết 5: LUT, DSP so với lõi chỉ-128-bit.
- Đối chứng ở đầu hẹp, để trả lời câu hỏi chắc chắn sẽ gặp: "tốc độ tăng theo (w/16)² chỉ là nhân schoolbook; linh
  hoạt tốn bao nhiêu ở độ rộng hẹp?". Cần thêm **lõi chỉ-32-bit** và **lõi chỉ-64-bit** (cho sinh khóa). Cả hai là tham
  số của cùng RTL: bỏ các điểm lấy kết quả rộng và cửa sổ bit rộng.

Đây là hình chính của bài.

**Rủi ro.**
- Chưa đọc Maestro (FFT nhiều precision) và toàn văn bài ISCAS 2025 về lõi FFT/NTT hợp nhất cho NTRU/Falcon.
- FFT 32 bit bị bộ nhớ và bảng twiddle chặn: trần chỉ-tính-toán là 432 chu kỳ.

### 2.2 Một phép hậu xử lý cho cả làm tròn fixed-point lẫn rút gọn modulo

**Khẳng định.** Làm tròn FFT (nửa-lên hoặc cắt) và rút gọn Montgomery có cùng dạng:
**phần cao của tích + một hạng bù + 1 bit**.
- Vì vậy một bộ cộng và một ngân hàng cộng/trừ chia làn phục vụ cả FFT lẫn NTT.
- **Từ 31/10/2026 (rút gọn lai):** chỉ lane 32 bit (8380417, mọi prime 31 bit) chạy các phép nhân phụ của Montgomery
  trên mảng nhân. Hai modulus 16 bit 3329 và 12289 dùng 64 bộ rút gọn hằng (không DSP) để NTT 16 bit chạy hết tốc độ.
  Câu "lõi không có bộ rút gọn riêng nào" **không còn đúng**; câu đúng là "lõi không có bộ rút gọn 32 bit riêng nào,
  và không phép rút gọn nào tốn DSP ngoài 64 bộ nhân chính".
- Ngân hàng cộng dùng chung cần 5 733 bit cộng, hai ngân hàng riêng cần 6 768, tức nhỏ hơn 15%
  ([model/postproc_adders.py](../model/postproc_adders.py)). Trước rút gọn lai là 2 832 so với 4 240 (33%): NTT 16 bit
  nay chạy gấp 3 butterfly mỗi chu kỳ nên cần gấp 3 bộ cộng butterfly.

**Vì sao mạnh, và phần nào không phải mới.**
- Montgomery dùng lại bộ nhân chính là cách quen thuộc ở bộ đồng xử lý RSA/ECC. Phần đó **không khẳng định**.
- Điểm mới là **dùng chung với làm tròn FFT**. Các lõi hợp nhất đã đọc đều giữ đường làm tròn và đường rút gọn riêng;
  bài ICTA 2026 rút gọn bằng bảng tra.

**Bằng chứng cần.**
- Giả thuyết 2 (viết lại 31/10/2026): so với cùng tile dùng bộ Montgomery 32 bit riêng, ít hơn ít nhất 4 DSP mỗi
  tile, LUT tăng không quá 5%. Bản đối chứng định nghĩa trong
  [hợp đồng cấp tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md), mục 5.2.
- Bản nháp khối tile thử ([study/results/tile_thu_draft.md](../study/results/tile_thu_draft.md)) là số đo đầu tiên,
  chưa phải bằng chứng nghiệm thu.
- Hai đẳng thức đã kiểm bằng code ([model/arch_checks.py](../model/arch_checks.py)).
- Bảng định cỡ ngân hàng cộng.

**Giá phải trả (nói thẳng trong bài).** NTT 32 bit chậm 2,4–2,8 lần so với khi có bộ Montgomery 32 bit riêng. NTT
16 bit không chậm.

**Rủi ro.**
- LUT của mux đưa toán hạng vào DSP có thể ăn hết phần tiết kiệm. Vì vậy phải đo **một tile** trên Vivado trước khi
  làm cả lõi.
- **Công trình có thể đã làm điều này:** Aloha-HE (DATE 2024) dùng chung số học dấu phẩy động và modulo; ABC-FHE có
  engine Fourier đổi giữa dấu phẩy động và modulo. Câu "các lõi hợp nhất đều giữ hai đường riêng" mới dựa trên bài
  ICASSP 2025 và phần tóm tắt bài ICTA 2026. **Phải đọc toàn văn Aloha-HE và ABC-FHE** trước khi trình bày 2.2 là
  điểm mạnh.
- Khi tính tốc độ trên LUT, NTT 32 bit thua (xem 2.5). Khẳng định 2.2 phải đứng trên tổng tài nguyên (chủ yếu là DSP),
  không phải trên hiệu suất của NTT 32 bit.

### 2.3 Quy tắc số học là dữ liệu, không phải phần cứng riêng

**Khẳng định.** Cùng một đường dữ liệu chạy đúng từng bit nhiều hợp đồng số học khác nhau. Mỗi hợp đồng chỉ khác nhau ở
vài hằng số: vị trí cửa sổ bit, hằng làm tròn, có chia đôi ở mỗi tầng hay không, q, q′.

| Hợp đồng | Quy tắc |
|---|---|
| FFT khi ký FN-DSA | Q64.64, làm tròn nửa-lên, nhân phức 3 tích, chia ở cuối |
| FFT khi sinh khóa (NTRUGen) | Q32.32, cắt bớt, chia đôi mỗi tầng, bảng root riêng |
| FFT 32 bit | Quy tắc tự định nghĩa cho xử lý tín hiệu |
| NTT | q = 3329, 12289, 8380417 và mọi prime 31 bit của NTRUGen (mục 4.1) |
| NTT ngược của NTRUGen | Chia đôi modulo p ở **mỗi tầng** (`mp_half`), không chia 1/n ở cuối: cùng chính sách "chia đôi mỗi tầng" với FFT NTRUGen |

Như vậy "chia đôi mỗi tầng" là một **chính sách** chung của hồ sơ, nhưng được thực hiện bằng hai phép khác nhau:
- FFT chia đôi cả hai nhánh trước phép nhân, theo kiểu số có dấu (v + 1) >> 1, ở phần chuẩn bị toán hạng.
- NTT chỉ chia đôi nhánh tổng, theo kiểu modulo (v + p nếu v lẻ) >> 1, trong ngân hàng cộng. Hệ số 1/2 của nhánh hiệu
  nằm sẵn trong bảng igm.

Không nói đây là "cùng một mạch".

**Vì sao mạnh.** Mục tiêu là khớp phần mềm thật ở mức sản phẩm cuối giống từng byte, không chỉ ở mức "sai số nhỏ". Trong
các bài phần cứng đã đọc, FFT cho Falcon thường dùng dấu phẩy động hoặc chỉ so sai số.

**Bằng chứng cần.** Giả thuyết 6, 8, 9.
- **Đã đạt** trên lõi cũ: bốn chữ ký (FFT 128 bit) khớp từng byte.
- **Chưa đạt, là mục tiêu:** khóa sinh bằng FFT 64 bit NTRUGen chạy trên lõi khớp từng byte (giả thuyết 8).

### 2.4 Một lõi phủ các phép biến đổi của FN-DSA và hai chuẩn PQC khác

| Việc | Phép biến đổi trên lõi |
|---|---|
| Ký FN-DSA | FFT 128 bit |
| Sinh khóa FN-DSA | FFT 64 bit; NTT modulo prime 31 bit (phần NTRUSolve) |
| Kiểm chữ ký FN-DSA | NTT q = 12289 |
| ML-KEM | NTT q = 3329, 7 tầng |
| ML-DSA | NTT q = 8380417 |

Khẳng định ở mức **từng kernel**, không khẳng định tăng tốc cả thuật toán.

**Bằng chứng cần.** Giả thuyết 6, 8, 9 và bảng thời gian của từng kernel.

### 2.5 Chi phí của tính linh hoạt được đo minh bạch

Điểm này không phải ý mới mà là thế mạnh khi trình bày. Các bản đối chứng là **tham số của cùng một RTL**, không phải các
lõi viết riêng:
- rút gọn riêng / trên mảng;
- hai ngân hàng cộng / một ngân hàng;
- chỉ-FFT, chỉ-NTT, chỉ-128-bit.

Danh sách bản đối chứng:
- rút gọn riêng / trên mảng;
- hai ngân hàng cộng / một ngân hàng;
- chỉ-FFT, chỉ-NTT;
- chỉ-128-bit, chỉ-64-bit, chỉ-32-bit.

**Chọn thước đo cho đúng.** Tính **tốc độ trên LUT của từng chế độ**, NTT 32 bit rút gọn trên mảng **thua**: nó chậm
2,4–2,8 lần mà không tiết kiệm LUT, chỉ tiết kiệm DSP. Phải nói thẳng điều này trong bài. Thước đo bảo vệ được là:

1. **Tổng tài nguyên** để có đủ tập chức năng (FFT ba độ rộng + NTT nhiều modulus), so với các lõi riêng.
2. **Thời gian toàn bộ workload** với tốc độ đó, để chứng tỏ NTT chậm không làm hỏng ứng dụng.

**Đã đo: NTT chiếm bao nhiêu, rút gọn trên mảng tốn bao nhiêu**
([scripts/profile_fn_dsa_workload.py](../scripts/profile_fn_dsa_workload.py)). Cột "trên mảng" dưới đây là **cấu
hình lai của v1** (`--lai`, kết quả [study/results/fn_dsa_workload_lai.md](../study/results/fn_dsa_workload_lai.md));
số của bản "trên mảng cho mọi modulus" trước đó ở [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md).

Cách đo:
- Build bản chuẩn FN-DSA cùng NTRUGen đi kèm, 4 khóa × 8 chữ ký mỗi N.
- Đếm mọi lời gọi FFT, NTT và tạo bảng root theo từng pha, rồi nhân với dự báo chu kỳ của mục 4 kiến trúc.
- Cộng 16 chu kỳ cho mỗi lệnh. Các lời gọi đồng nhất do host bỏ qua.

| Một lần … | N = 512: lai / riêng (chu kỳ) | Tăng | N = 1024: lai / riêng | Tăng | NTT trong tổng chu kỳ (lai) |
|---|---:|---:|---:|---:|---:|
| Ký | 59 368 / 59 368 | **0%** | 129 952 / 129 952 | **0%** | 0% |
| Mở rộng khóa | 29 600 / 29 600 | 0% | 63 368 / 63 368 | 0% | 1–2% |
| Kiểm chữ ký | 500 / 500 | **0%** | 656 / 656 | **0%** | 100% |
| Sinh khóa | 390 318 / 268 617 | **+45%** | 1 394 271 / 1 019 593 | **+37%** | 66–77% |

Câu chuyện của 2.2 phải viết theo đúng số này:
- **Ký**, thao tác dùng nhiều nhất, không gọi NTT lần nào. Rút gọn trên mảng **không tốn thời gian** khi ký.
- **Kiểm chữ ký và mở rộng khóa** chỉ dùng NTT 16 bit (q = 12289), nay chạy bằng bộ rút gọn hằng: **không chậm**. Với
  bản "trên mảng cho mọi modulus" trước đó, kiểm chữ ký chậm 103–126%.
- **Sinh khóa** chịu thiệt như trước: thời gian kernel tăng 37–45% (49–66% nếu không tính chi phí mỗi lệnh). Nguyên nhân là
  NTRUSolve gọi hàng nghìn NTT nhỏ với prime mới mỗi lần, chủ yếu N = 16 (khoảng 3 600 lần NTT và NTT ngược mỗi lần
  sinh khóa N = 1024). Ở cỡ này độ trễ nhịp quyết định: trên mảng 70 chu kỳ, rút gọn riêng 38 chu kỳ.
- Trong phần mềm, các kernel chỉ chiếm khoảng 22–26% thời gian sinh khóa (FFT 3–6%, NTT 13–17%, tạo bảng 3–7%). Phần
  lớn còn lại là số học số lớn và các phép khác ở host. Vì vậy khoản thiệt của NTT chỉ tác động lên phần nhỏ đó của sinh
  khóa.
- Nạp bảng root trong sinh khóa N = 1024 tốn khoảng 99 000 chu kỳ lõi và 58 600 dòng host ghi. Đây không phải chi phí
  nhỏ, vì gần như mỗi cặp NTT lại dùng một prime mới.

**Chép dữ liệu giữa host và lõi chiếm phần lớn thời gian** (cùng script, mục "Chép dữ liệu" của file kết quả). Đếm
số dòng 128 bit host phải ghi vào và đọc ra cho mỗi lời gọi kernel; tính và chép cộng nối tiếp, vì giao diện 1.0 không
cho host truy cập bộ nhớ khi lõi chạy.

| N = 1024, một lần … | Chu kỳ tính | Tổng, giao diện 1.0 (2 chu kỳ/dòng) | Tổng, burst 128 bit | Tổng, burst 128 bit + giữ dữ liệu trong lõi (cận dưới) |
|---|---:|---:|---:|---:|
| Ký | 129 952 | 375 712 (65% là chép) | 252 832 (49%) | 203 648 (36%) |
| Sinh khóa | 943 632 | 1 719 297 (45%) | 1 331 464 (29%) | 1 281 513 (26%) |
| Kiểm chữ ký | 1 484 | 4 300 (65%) | 2 892 (49%) | 1 996 (26%) |

- Các kernel của FN-DSA nhỏ, và giữa chúng host còn làm việc khác (bộ lấy mẫu khi ký, phép nhân từng điểm khi sinh
  khóa). Vì vậy dữ liệu phải qua lại liên tục.
- Giữ dữ liệu lại trong lõi giữa các kernel chỉ giảm số dòng của phép ký khoảng 40% (122 880 → 73 696), vì phần lớn đầu
  ra thật sự được host dùng ngay.
- **Hệ quả cho bài báo:** các khẳng định ở mức kernel vẫn đứng. Mọi câu về lợi ích ứng dụng phải tính cả phần chép,
  và phần này phụ thuộc giao diện host nhiều hơn phụ thuộc mảng nhân.
- **Đã đưa vào v1** (31/10/2026; thay đổi 10, 11; giả thuyết 12): cổng host có pipeline, và địa chỉ đầu của vùng
  A/B/C trong mỗi lệnh để giữ dữ liệu trong lõi. Chép trong lúc lõi chạy để sau v1.

**Ghép nhiều đa thức vào một lệnh** (cùng script, cùng file kết quả):

| Sinh khóa | N = 512: lai / riêng | N = 1024: lai / riêng |
|---|---:|---:|
| Mỗi lệnh 1 đa thức | 390 318 / 268 617 (+45%) | 1 394 271 / 1 019 593 (+37%) |
| Ghép đa thức **cùng prime**, theo đúng spec 2.0 | 362 944 / 251 697 (+44%) | 1 332 097 / 979 270 (+36%) |
| Ghép **khác prime**, mỗi tile một modulus (N < 64, tới min(8, 64/N) đa thức; cận trên theo cách gom) | 259 466 / 181 031 (+43%) | 942 896 / 717 718 (+31%) |

- **Ghép cùng prime gần như vô ích.** Ở N = 16, mỗi prime chỉ làm một chuỗi phụ thuộc ngắn: tạo bảng → NTT → nhân từng
  điểm ở host → NTT ngược. Không có hai đa thức cùng prime để ghép. Các cặp ghép được (f và g liền nhau) đã được kiểm
  trong mã là hai biến đổi độc lập.
- **Ghép khác prime giảm thời gian NTT của sinh khóa 1,8–2,0 lần** (N = 1024, trên mảng: 923 457 → 472 082 chu kỳ).
  Đây là lợi ích của chính lõi, so với một đa thức mỗi lệnh. **So cùng điều kiện** (cả hai biến thể đều ghép khác prime),
  bản trên mảng vẫn chậm hơn 31–44% thời gian kernel khi sinh khóa. Không nói "bản trên mảng nhanh hơn bản rút gọn
  riêng": so với bản rút gọn riêng không ghép, kết quả đổi từ chậm hơn 4–12% tới nhanh hơn 19–22%, tùy chi phí mỗi lệnh
  (0 đến 64 chu kỳ; dự báo dùng 16, cho nhanh hơn 3–7%).
- **Đã đưa vào v1** (thay đổi 9, giả thuyết 11, 31/10/2026). Ghép khác prime cần **mỗi tile một modulus**:
  - Mỗi tile đã có thanh ghi hằng số riêng ([hợp đồng tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md) mục 3),
    nên phần số học không tốn thêm gì.
  - Thêm 16 khe prime (p, p0i, R², vị trí bảng) và chia RAM gói root theo khe; bảng N = 16 chỉ có 7 gói.
  - Lệnh chọn khe cho từng đa thức bằng "khe đầu" và cờ "cùng khe" (spec 2.0, 02 mục 1).
  - Chỉ áp dụng cho N < 64. Ở N ≥ 64 hai đa thức xen kẽ dùng chung mọi tile, nên phải cùng prime.
- **Đây là cận trên.** Nó giả định có thể tách các vòng lặp theo prime trong NTRUSolve. Các vòng nóng (`ng_ntru.c` quanh
  dòng 470–562, `make_fg_step`) xử lý từng prime trên vùng mảng riêng. Một vòng trong `ng_poly.c` (quanh dòng 880–970)
  dùng chung mảng `k` giữa các prime, nên phải chép riêng cho từng prime.
- **Lợi cho khẳng định:** "các tile chạy modulus khác nhau cùng lúc" biến chiều modulus thành song song RNS thật trên
  cùng mảng, không chỉ là đổi modulus giữa các lệnh.

**Bằng chứng cần.** Giả thuyết 1, 2, 5 và bảng thời gian workload.

## 3. Những gì không khẳng định

| Không khẳng định | Lý do |
|---|---|
| NTT 32 bit nhanh | Chậm hơn 2,4–2,8 lần bản có bộ Montgomery 32 bit riêng. (NTT 16 bit chạy hết tốc độ: N = 256 một đa thức 80 chu kỳ, nhanh gấp 2 lõi cũ) |
| NTT hẹp hơn thì nhiều làn hơn | Bài ICASSP 2025 đã làm |
| NTT hai tầng gộp; đọc/tính/ghi chạy chồng | Kỹ thuật quen thuộc |
| Montgomery tính trên bộ nhân chung, xét riêng phía NTT | Quen thuộc ở bộ đồng xử lý RSA/ECC |
| "Đầu tiên" | Chưa rà đủ tài liệu |
| An toàn kênh kề | Ngoài phạm vi |

## 4. Đề xuất làm khẳng định mạnh hơn

Xếp theo lợi ích trên chi phí.

### 4.1 NTT modulo các prime 31 bit của NTRUGen (đề xuất mạnh nhất — **đã đưa vào v1**, 30/10/2026)

Đã thành thay đổi 8 và giả thuyết 10 của [kiến trúc v1](architecture_v1.md), mục 5.4. **Đã kiểm khớp từng bit với
C** ([model/ntrugen_mp31.py](../model/ntrugen_mp31.py)) trên cả 323 prime của bảng `PRIMES`, logn = 1..10. Phép kiểm
dùng Montgomery dựng từ tích 16×16, nhịp hai tầng như phần cứng, và chia đôi trong ngân hàng cộng:

| Kiểm | Số trường hợp khớp |
|---|---:|
| `mp_montymul` | 21 641 |
| Bảng root `mp_mkgmigm` | 3 230 |
| NTT xuôi `mp_NTT` | 3 230 |
| NTT ngược `mp_iNTT` | 3 230 |

Dự báo cho N1024: NTT mất 1 120 chu kỳ. Nạp một bảng root tốn thêm 257 dòng 128 bit do host ghi, cộng ít nhất 128
chu kỳ của phép nạp. Bảng nạp ở N lớn dùng được cho mọi N nhỏ hơn, nên mỗi prime chỉ nạp một lần. Các rủi ro "thứ tự root, bảng igm, cách chia đôi" ghi
bên dưới **đã được giải quyết** bằng phép kiểm này: igm gộp sẵn 1/2, và NTT ngược chia đôi mỗi tầng, không nhân 1/n ở cuối.

**Đã kiểm trong mã nguồn** (`third_party/r8/ntrugen/src/ng_inner.h`, đi kèm bản chuẩn):
- Phần NTRUSolve của sinh khóa dùng biểu diễn RNS, với bảng `PRIMES` gồm các prime nhỏ hơn 2³¹.
- Phép nhân là Montgomery với R = 2³² và p0i = −1/p mod 2³² (hàm `mp_montymul`). Đây đúng là dạng rút gọn 32 bit lõi
  đã có cho q = 8380417.
- NTT tính trên X^n + 1, với n từ 2 đến 1024 (hàm `mp_NTT`, `mp_iNTT`).

**Lợi ích.**
- Chiều modulus đổi từ "3 hằng số chọn sẵn" thành "mọi prime 31 bit trong một workload thật, đổi lúc chạy, không thêm
  phép tính nào".
- Sinh khóa FN-DSA dùng được lõi cho cả FFT lẫn NTT.
- Khẳng định 2.2 thêm ý nghĩa: đổi modulus không tốn diện tích số học.

**Chi phí.**
- **Bảng root là chi phí thật, không miễn phí:**
  - Bảng root NTT 32 bit phải là RAM nạp được thay cho ROM. Theo spec 2.0, RAM gói root của hai chiều khoảng 12 KiB
    (511 gói × 96 bit mỗi chiều), tức thêm BRAM.
  - NTRUSolve dùng nhiều prime, mỗi prime một bảng root. Thời gian nạp hoặc sinh bảng **phải tính vào thời gian
    kernel**. Spec 1.0 loại thời gian nạp từ host khỏi số chu kỳ kernel; với RNS làm vậy là không công bằng.
  - NTRUGen sinh bảng bằng một chuỗi phép nhân nối tiếp (`mp_mkgm`), nên sinh trên mảng sẽ chậm nếu không đổi cách sinh.
- q và q′ thành thanh ghi nạp theo lệnh.
- **Chia đôi modulo p** (x chẵn → x/2, x lẻ → (x + p)/2) trong ngân hàng cộng cho NTT ngược: một phép cộng có điều
  kiện rồi dịch.
- Bố cục 32 bit cho N từ 2 đến 1024, gồm cả lượt một tầng cuối khi log N lẻ (đã kiểm,
  [model/res32_bank_map.py](../model/res32_bank_map.py)):
  - N ≤ 512: không xung đột bank, kể cả bảng root.
  - N = 1024: 20% chu kỳ phải đọc hai lượt, chậm thêm tối đa khoảng 20%. Spec đã cho phép đọc nhiều lượt khi trùng bank.
- Vector chuẩn lấy từ `mp_NTT` / `mp_iNTT` của NTRUGen. Mã C đã có trong `third_party/r8`.
- Thêm kiểm thử chéo: nhân qua nhiều prime, ghép CRT, so với nhân số nguyên chính xác.

**Rủi ro.**
- Muốn khớp từng bit, phải đọc kỹ ba thứ trước khi chốt:
  - thứ tự root của `mp_NTT`;
  - cách `mp_mkgm` xếp bảng gm/igm, và bảng igm đã gộp sẵn hệ số 1/2 hay chưa;
  - cách chia đôi của `mp_iNTT`.

  Mỗi điểm khác lõi hiện tại sẽ thành thêm một trường của hồ sơ số học.
- NTT chỉ là một phần thời gian của NTRUSolve, nên chỉ khẳng định ở mức kernel.

### 4.2 Đường cong sai số – thời gian của FFT

Đo sai số FFT 32 / 64 / 128 bit so với DFT chính xác ở các N, rồi vẽ cạnh số chu kỳ. Hình này cho thấy người dùng chọn
precision theo yêu cầu sai số, và làm khẳng định 2.1 có ý nghĩa với cả xử lý tín hiệu. Chỉ cần mô hình Python, không đổi
phần cứng.

### 4.3 Bảng hồ sơ số học nạp được

Đưa các hằng ở mục 2.3 vào một bảng thanh ghi thay vì giải mã cứng theo trường định dạng. Khi đó có thể khẳng định thêm:
"hợp đồng số học mới không cần sửa RTL", trong giới hạn của cửa sổ bit. Chi phí khoảng vài chục FF và mux hằng. Nên đi
cùng 4.1.

### 4.4 Đọc đủ công trình liên quan trước khi khóa khẳng định

Cần toàn văn của:
- bài ICTA 2026 về khối số học hợp nhất dấu phẩy động / modulo;
- bài ISCAS 2025 về lõi FFT/NTT hợp nhất cho NTRU/Falcon;
- Maestro, CoHA-NTT, Aloha-HE;
- một bài bộ đồng xử lý Montgomery dùng chung bộ nhân, để trích dẫn phần không khẳng định.

## 5. Khẳng định và bằng chứng

| Khẳng định | Giả thuyết | Đo gì | Trạng thái |
|---|---|---|---|
| 2.1 Precision FFT thành tốc độ | 3, 5 | Chu kỳ FFT ba độ rộng; tỉ lệ đạt được so với lý tưởng; LUT/DSP so với lõi chỉ-128, chỉ-64, chỉ-32 bit | Dự báo bằng mô hình |
| 2.2 Một phép hậu xử lý | 2 | LUT/FF/DSP/Fmax một tile, rồi cả lõi, hai bản rút gọn (lai / riêng) | Công thức đã kiểm; bản nháp tile: DSP 4 so với 11, LUT +2%, Fmax chưa đạt; chưa đọc Aloha-HE, ABC-FHE |
| 2.3 Quy tắc số học là dữ liệu | 6, 8, 9 | Số sai khác so với bản chuẩn; chữ ký và khóa từng byte | Chữ ký đã đạt trên lõi cũ; khóa chưa |
| 2.4 Phủ các biến đổi PQC | 6, 8, 9 | Thời gian từng kernel | Chưa có RTL mới |
| 2.5 Chi phí linh hoạt | 1, 2, 5 | Tổng tài nguyên cho cả tập chức năng; tốc độ/LUT, tốc độ/DSP theo chế độ | Chưa đo |
| 2.5 NTT chậm không hỏng ứng dụng | Cần thêm giả thuyết mới | Thời gian kernel của luồng ký/kiểm/sinh khóa, tách FFT và NTT, hai bản rút gọn | Đã đếm trên bản chuẩn × dự báo, cấu hình lai: ký 0%, kiểm 0%, sinh khóa +37–45%; cần đo lại trên RTL |
| 4.1 Prime 31 bit | 10 | Khớp `mp_NTT`/`mp_iNTT` trên RTL; LUT/BRAM thêm; thời gian gồm cả nạp root; tỉ lệ thời gian NTT trong NTRUSolve | Mô hình khớp từng bit với C (323 prime × logn 1..10); chưa có RTL |
