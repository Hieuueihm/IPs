# 04 — Kiểm thử cấp lõi, thí nghiệm giả thuyết và điều kiện nhận RTL

Quy tắc chung **giữ nguyên như [04 của bản 1.0](../1.0/04_verification_acceptance.md)**:
- so từng bit, không dùng dung sai;
- không lấy chính RTL đang kiểm làm nguồn kết quả mong đợi;
- "chưa chạy" không bao giờ là đạt;
- lịch chạy không phụ thuộc giá trị hệ số;
- giới hạn 1 048 576 chu kỳ để phát hiện treo.

Kiểm thử cấp lõi chỉ bắt đầu sau khi [kiểm thử cấp tile](11_kiem_thu_tile.md) đạt.

## 1. Vector chuẩn cấp kernel

| Nguồn | Nội dung | Kết quả mong đợi lấy từ |
|---|---|---|
| Vector của 1.0 ([assets](../1.0/assets/README.md)) | Định dạng 0–3, profile 0–1, mọi phép của 1.0 | Như 1.0 |
| [assets/kernel/fft_ntrugen.jsonl](assets/kernel/fft_ntrugen.jsonl) | 40 ca: FFT và FFT ngược định dạng 5, logn 1..10; giá trị cỡ của sinh khóa (\|x\| < 2⁴⁰) và giá trị 64 bit bất kỳ | C của NTRUGen (`vect_FFT`, `vect_iFFT`) |
| [assets/kernel/ntt_q8380417.jsonl](assets/kernel/ntt_q8380417.jsonl) | 60 ca: NTT, NTT ngược, phép 0x7, 0x8; 1 và 2 đa thức; mẫu toàn 0, toàn q − 1, xung đơn vị, ngẫu nhiên | Phép toán modulo thuần túy; mỗi kết quả NTT được kiểm lại bằng đánh giá đa thức trực tiếp |
| [assets/kernel/ntt_prime31.jsonl](assets/kernel/ntt_prime31.jsonl) | 235 ca. 225 ca trên 5 prime của NTRUGen (thứ tự 0, 1, 161, 321, 322) × logn 1..10: dữ liệu cho phép nạp prime, NTT, NTT ngược, phép 0x7, 0x8, và 2 đa thức khi N ≥ 64. Thêm 10 lệnh nhiều khe: N = 2..32, min(8, 64/N) đa thức, mỗi đa thức một prime khác nhau (8 prime: thứ tự 0, 1, 2, 80, 161, 240, 321, 322), có trường hợp khe quay vòng 15 → 0 | C của NTRUGen (`mp_NTT`, `mp_iNTT`, `mp_mkgmigm`), từng đa thức với prime của nó; phép 0x7, 0x8 và đa thức thứ hai cùng prime bằng phép toán modulo |

Mỗi dòng JSONL là một bản ghi:
- `op`, `fmt`, `profile`, `logn`, `jobs`;
- `input`: một mảng số hex cho mỗi đa thức;
- `input_b`: chỉ có với phép 0x8;
- `expected`;
- `source`: nguồn của kết quả mong đợi.

File `ntt_prime31.jsonl` có thêm bản ghi `nap_prime`:
- p, p0i, R², logn;
- `tables` = mặt nạ bảng có mặt;
- `slot`, `base` = khe và vị trí gói đầu;
- gm, igm.

Testbench ghi bản ghi này vào vùng C theo bố cục của [02 mục 3](02_giao_dien.md), chạy phép nạp prime vào khe `slot`,
rồi chạy các bản ghi trỏ tới nó. Bản ghi lệnh một khe có trường `prime`. Bản ghi lệnh nhiều khe có `primes` (một prime
cho mỗi đa thức), `khe_dau` và `cung_khe`. Để kiểm việc dùng bảng lớn cho N nhỏ, testbench nạp bản ghi `nap_prime` của logn = 10 rồi chạy các
bản ghi phép của logn nhỏ hơn cùng prime.

Sinh lại và kiểm:

```text
python scripts/build_spec2_kernel_assets.py
python scripts/check_spec2_kernel_assets.py
```

Bộ kiểm chạy mã giả của [01](01_so_hoc_kernel.md) bằng Python và cho kết quả trùng mọi vector. Nghĩa là văn bản spec
và C của bản chuẩn nói cùng một điều.

## 2. Các bộ kiểm thử cấp lõi

Các bộ kế thừa từ 1.0 giữ nguyên nội dung, chỉ đổi tên cho dễ đọc. Mỗi bộ phải chạy cho mọi định dạng và profile áp
dụng được.

| Bộ kiểm | Tương ứng 1.0 | Nội dung |
|---|---|---|
| Cấu hình lệnh và lỗi | T_CFG | Mọi bộ (phép, định dạng, profile, logn, số đa thức) hợp lệ; mọi lỗi 0x01–0x07 và 0x09; nhiều trường sai cùng lúc theo đúng thứ tự kiểm; lệnh lỗi không đọc, không tính, không ghi |
| Bắt tay lệnh và kết quả | T_NATIVE | Như 1.0 |
| Giữ ổn định khi bị chặn | T_STABILITY | Như 1.0 |
| Reset | T_RESET | Như 1.0, thêm: reset xóa cờ hợp lệ của mọi khe prime |
| Flush | T_FLUSH | Như 1.0, thêm: flush trong lúc nạp prime cho mã 0x10, cờ của khe đang nạp bằng 0, các khe khác giữ nguyên |
| Bộ nhớ host | T_MEMORY | Như 1.0, thêm cho cổng có pipeline: 8 giao dịch đang chờ; trả lời đúng thứ tự khi đọc và ghi xen kẽ; ghi rồi đọc ngay cùng địa chỉ thấy dữ liệu mới; host giữ `mem_rsp_ready_i = 0` lâu rồi thả ra không mất trả lời; tốc độ ≥ 0,9 dòng/chu kỳ cho đọc liên tiếp, ghi liên tiếp, xen kẽ; lệnh mới chỉ được nhận sau khi mọi giao dịch đã trả lời; flush khi còn giao dịch đang chờ |
| **Địa chỉ trong lệnh** | mới | Mọi phép chạy ở nhiều địa chỉ đầu hợp lệ ngẫu nhiên: kết quả bằng vector, byte ngoài vùng ra không đổi (canary). Địa chỉ không căn, vượt 8 192, hoặc khác 0 ở vùng không dùng → mã 0x09, không đọc, không ghi. Chuỗi lệnh dùng đầu ra của lệnh trước làm đầu vào mà host không chép lại: kết quả đúng. Bộ đếm lượt đọc thêm vì xung đột bank giống hệt khi đặt ở địa chỉ 0 |
| Phép cơ sở FFT | T_FP_PRIM | Như 1.0, thêm: nhân cắt bớt và `nửa` của định dạng 5 ở giá trị biên (−2⁶³, −1, 2⁶³ − 1) |
| Kernel FFT | T_FP_KERNEL | Như 1.0, thêm toàn bộ `fft_ntrugen.jsonl` |
| Phép cơ sở NTT | T_NTT_PRIM | Thay bằng [kiểm thử cấp tile](11_kiem_thu_tile.md) chạy trên tile thật trong lõi (đọc vector qua đường gỡ lỗi hoặc mô phỏng tile riêng) |
| Kernel NTT | T_NTT_KERNEL | Như 1.0, thêm toàn bộ `ntt_q8380417.jsonl` và `ntt_prime31.jsonl` |
| **Nạp prime** | mới | Phần đầu sai từng điều kiện (p chẵn, p < 3, p ≥ 2³¹, byte 12 khác logn, byte 13 không phải 1–3, vị trí gói b + G > 511) → mã 0x08, cờ của khe bằng 0, RAM gói không đổi. Nạp đúng → NTT profile 3 đúng. Nạp ở logn L rồi chạy mọi logn < L → kết quả bằng vector của logn đó; chạy logn > L → mã 0x07. Chỉ nạp gm rồi chạy NTT ngược → mã 0x07; chỉ nạp igm rồi chạy NTT → mã 0x07. Nạp prime thứ hai thay prime thứ nhất. Vùng C không bị sửa |
| **Nhiều khe prime** | mới | Nạp 8 prime khác nhau vào 8 khe, chạy NTT và NTT ngược với N = 2..32 và số đa thức tối đa: mỗi đa thức khớp vector của prime đó. Khe đầu khác 0 và quay vòng qua khe 15 → 0. Cờ cùng khe = 1 ở N < 64 (cùng một prime cho mọi đa thức). Nạp một khe có vùng gói chồng lên khe khác → khe kia bị từ chối với mã 0x07. Một khe chưa hợp lệ trong lệnh nhiều khe → mã 0x07, không ghi gì. N ≥ 64, 2 đa thức, cờ cùng khe = 0 → mã 0x06. Lịch theo chu kỳ không phụ thuộc prime nào nằm trong khe |
| **Gói root** | T_ROOT | Đọc lại nội dung RAM gói (qua đường gỡ lỗi nếu có) hoặc suy từ kết quả NTT với mẫu xung đơn vị ở mọi vị trí |
| Mảng nhân | T_ARRAY | Như 1.0 cho FFT; NTT theo hợp đồng tile |
| Context | T_CONTEXT | Như 1.0 |
| **Xen kẽ hai đa thức** | T_JOBS mở rộng | Mọi N ≥ 64, định dạng 3 và 4, hai đa thức khác nhau: kết quả bằng chạy riêng từng đa thức; bộ đếm cho thấy hai đa thức chồng thời gian; mặt nạ và vùng canary ngoài phạm vi không bị sửa |
| Bank | T_BANK | Như 1.0, thêm: với lịch tham chiếu của 1.0 mục 03.6, định dạng 4 ở N = 1024 có bộ đếm lượt đọc thêm khớp 20% chu kỳ, các N khác bằng 0. Lịch khác thì báo số đo được |
| **Gom lô FFT** | mới | Mọi tầng, ba độ rộng và định dạng 5: số butterfly mỗi lô đúng 16 / 4 / 1 khi tầng đủ; lô thiếu có mặt nạ đúng; số lượt đọc root mỗi lô bằng số root khác nhau trong cùng bank |
| Ngẫu nhiên dài | T_STRESS | Như 1.0, thêm lệnh của mọi định dạng và profile mới, xen phép nạp prime |
| Lịch không phụ thuộc dữ liệu | T_PROFILE | Như 1.0, thêm profile 3 với hai prime khác nhau cùng N: lịch phải giống nhau |
| Ứng dụng ký FN-DSA | T_SIGNER | Như 1.0: bốn chữ ký khớp từng byte |
| **Ứng dụng sinh khóa FN-DSA** | mới | Sinh khóa NTRUGen với FFT định dạng 5 và NTT profile 3 chạy trên RTL, ít nhất 2 seed mỗi N = 512, 1024: khóa khớp từng byte với C; ghi tách thời gian FFT, NTT, nạp prime |
| Bắt lỗi cố ý | T_MUTATE | Như 1.0, thêm: đổi hằng làm tròn của định dạng 5 thành 2³¹; bỏ chia đôi ở một tầng của FFT ngược định dạng 5; bỏ chia đôi modulo ở NTT ngược profile 3; đảo hai root trong một gói |
| Đo hiệu năng | T_PERF | Như 1.0, thêm: số chu kỳ từng (phép, định dạng, profile, logn, số đa thức) để so với dự báo ở mục 4 của kiến trúc |
| Phát hành | T_RELEASE | Như 1.0 |

## 3. Thí nghiệm giả thuyết

Ngưỡng nằm trong [kiến trúc v1, mục 6](../../../docs/architecture_v1.md#6-giả-thuyết-cần-chứng-minh) và **không được
sửa sau khi đo**. Bảng dưới chỉ nói cần đo gì và trên cấu hình nào.

| Giả thuyết | Đo | Cấu hình so sánh |
|---:|---|---|
| 1 | LUT, FF, DSP, BRAM/URAM, Fmax | Lõi chung; lõi chỉ-FFT; lõi chỉ-NTT (cùng tốc độ ở chế độ của nó) |
| 2 | Như trên, trước hết ở cấp tile ([10 mục 8](10_hop_dong_tile.md)), sau đó cả lõi; thêm chu kỳ NTT | Biến thể rút gọn trên mảng / rút gọn riêng |
| 3 | Chu kỳ FFT và FFT ngược N = 512, 1024, ba độ rộng; độ trễ đường FFT | Lõi đủ thay đổi; lõi chỉ có pipeline (tắt gom lô) |
| 4 | Chu kỳ NTT; độ trễ nhịp đo được | So với mô hình: tổng các lượt × (số nhịp / (16 × tốc độ) + độ trễ) |
| 5 | LUT, DSP; tốc độ trên LUT | Lõi chung; lõi chỉ-128-bit; lõi chỉ-64-bit; lõi chỉ-32-bit |
| 6 | Số sai khác | Toàn bộ vector và hai luồng ứng dụng |
| 7 | Số lượt; LUT | NTT hai tầng gộp / chỉ một tầng |
| 8 | Khóa từng byte | Bộ "Ứng dụng sinh khóa FN-DSA" |
| 9 | Số sai khác so với Dilithium sau khi đưa về [0, q); bộ đếm xung đột | NTT q = 8380417 |
| 10 | Số sai khác; LUT, BRAM thêm; chu kỳ (có và không có nạp prime) | Lõi có và không có profile 3 |
| 11 | Số sai khác của lệnh nhiều khe; LUT, FF thêm; thời gian NTT của sinh khóa với chu kỳ đo trên RTL | Lõi có 16 khe / chỉ 1 khe; workload đếm bằng [scripts/profile_fn_dsa_workload.py](../../../scripts/profile_fn_dsa_workload.py) |
| 12 | Tốc độ cổng host (dòng/chu kỳ); số dòng chép của luồng ký N = 1024 khi trình điều khiển giữ dữ liệu; LUT thêm | Cổng 1.0 / cổng có pipeline; trình điều khiển không giữ / có giữ dữ liệu |

**Mọi cấu hình so sánh là tham số của cùng một RTL** (tắt gom lô, chọn biến thể rút gọn, bỏ đường FFT hoặc NTT, giới
hạn độ rộng, tắt profile 3, số khe prime, số giao dịch host đang chờ), không phải lõi viết riêng. Cùng phiên bản Vivado, cùng linh kiện `xczu7ev-ffvc1156-2-e`,
cùng ràng buộc clock, tổng hợp và place-and-route out-of-context. Báo riêng từng loại tài nguyên, không cộng gộp.

## 4. Điều kiện nhận RTL

- **Chức năng:**
  - không sai khác trên đầu vào hợp lệ;
  - không assertion nào thất bại;
  - mọi bộ ở mục 2 đạt, hoặc được miễn có ghi lý do;
  - kiểm thử cấp tile đạt ở biến thể dùng trong lõi.
- **Ứng dụng:** "Ứng dụng ký FN-DSA" đạt. "Ứng dụng sinh khóa FN-DSA" đạt thì mới được nói lõi dùng được cho sinh khóa.
- **Thí nghiệm:**
  - mỗi giả thuyết có kết quả đạt, bác bỏ hoặc chưa chạy;
  - kết quả bác bỏ được báo như kết quả âm, không bỏ đi.
- **Manifest triển khai:** như 1.0, cộng các mục ở [03 mục 7](03_bo_nho.md), cộng hash của các manifest vector của
  bản 2.0.

Đạt các điều kiện trên **không** có nghĩa là đã kiểm timing vật lý, kênh kề hay chứng nhận FN-DSA.
