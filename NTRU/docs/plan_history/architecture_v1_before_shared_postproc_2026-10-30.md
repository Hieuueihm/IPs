# FlexTransform v1 — ý tưởng, kiến trúc và giả thuyết

> Ngày 30/10/2026. **Bản chốt để triển khai RTL.** Thay đổi sau ngày này cần ghi lý do và cập nhật lại tài liệu.
> Bản trước khi làm gọn: [docs/plan_history/architecture_v1_before_cleanup_2026-10-30.md](plan_history/architecture_v1_before_cleanup_2026-10-30.md).

## 1. Ý tưởng

Lõi FlexTransform dùng **một mảng 64 bộ nhân 16×16** cho cả hai loại phép biến đổi mà FN-DSA (Falcon) cần:

- **FFT số phức fixed-point** ở ba độ rộng: 32, 64 và 128 bit mỗi phần thực/ảo.
- **NTT modulo** ở hai độ rộng hệ số: 16 bit (q = 12289 của FN-DSA, q = 3329 của ML-KEM) và
  32 bit (q = 8380417 của ML-DSA).

Một phép nhân w bit cần (w/16)² bộ nhân 16×16. Vì vậy mảng 64 bộ nhân làm được **64 / (w/16)² phép nhân
mỗi chu kỳ**: toán hạng càng hẹp thì càng nhiều phép nhân song song. Quy luật này giống nhau cho FFT và NTT.

Ý tưởng chính của v1: **bộ điều khiển gom nhiều butterfly vào một lượt theo độ rộng đang chạy**, để
"hẹp hơn" thật sự trở thành "nhanh hơn" trong giới hạn bộ nhớ và bảng twiddle cấp được.

Ba độ rộng FFT không phải tùy chọn tự đặt. Chúng ứng với workload thật:

| Độ rộng FFT | Dùng cho | Phép tính phải khớp từng bit với |
|---|---|---|
| 128 bit (Q64.64) | Ký FN-DSA | Bản FN-DSA fixed-point đã chọn làm chuẩn (mục 5) |
| 64 bit (Q32.32) | Sinh khóa FN-DSA | Thư viện NTRUGen đi kèm chính bản chuẩn đó |
| 32 bit (Q16.16) | Xử lý tín hiệu | Quy tắc số học tự định nghĩa; không dùng cho ký |

## 2. Vấn đề hiện tại

Lõi đã chạy đúng hoàn toàn: 5 992 lời gọi kernel khớp, và bốn chữ ký (N = 512 và 1024) khớp từng byte với
phần mềm. Nhưng hai chiều linh hoạt mới có về chức năng, chưa có về tốc độ:

- **FFT 32, 64 và 128 bit đều mất 52 992 chu kỳ** (N = 1024). Bộ điều khiển xử lý tuần tự,
  23 chu kỳ cho mỗi butterfly, nên dùng toán hạng hẹp không nhanh hơn.
- **NTT mất 10 chu kỳ cho mỗi lượt dữ liệu**; với N nhỏ, phần lớn mảng nhân để trống.
- **NTT chỉ có hai modulus, cùng độ rộng 16 bit**, nên đổi modulus không thay đổi số phép nhân song song.

Muốn bảo vệ được luận điểm "hai chiều linh hoạt", v1 phải biến độ rộng thành tốc độ ở cả hai chiều.

## 3. Kiến trúc

~~~text
              Lệnh + nạp/đọc dữ liệu (giao diện của spec 1.0)
                                |
   +------------- Khối lệnh: gom lô, 2 context, xen kẽ đa thức -------------+
                  |                                       |
     Bộ nhớ: 3 vùng × 64 bank × 16 bit         Bảng twiddle
     (hệ số 32 bit = 2 bank liền kề)            FFT: 4 bank, mỗi bank 1 root/chu kỳ
                  |                             NTT: gói 3 root cho hai tầng liên tiếp
                  |                                       |
     Chuẩn bị toán hạng: cộng trước cho phép nhân phức 3 tích; trừ (và chia đôi nếu
     là FFT 64 bit theo NTRUGen) cho butterfly ngược; giữ toán hạng chờ kết quả
                                |
     Mảng 16 tile × 4 bộ nhân 16×16, nhóm theo độ rộng đang chạy
                                |
     Cây cộng ghép tích, lượng dịch cố định; lấy kết quả ở mức 1, 4, 16 hoặc 64 bộ nhân
             |                                            |
   FFT: làm tròn từng tích,                    NTT: rút gọn modulo
        ghép số phức 3 tích,                        16 bit: 4 bộ/tile, dùng chung cho 3329 và 12289
        cộng/trừ butterfly                          32 bit: 1 bộ/tile cho 8380417
             +---------------------+----------------------+
                                   |
     Bộ điều khiển: đọc, tính, ghi chạy song song; chỉ sang tầng mới
     khi mọi kết quả của tầng cũ đã ghi xong
~~~

### 3.1 Cách nhóm bộ nhân theo chế độ

| Chế độ | Bộ nhân cho một phép nhân | Phép nhân/chu kỳ | Butterfly/lô |
|---|---:|---:|---:|
| FFT 32 bit | 4 | 16 | 16 |
| FFT 64 bit (cả bản NTRUGen) | 16 | 4 | 4 |
| FFT 128 bit | 64 (58 cần dùng) | 1 | 1 |
| NTT 16 bit, hai tầng gộp | 1 | 64 | 64 hệ số, hai tầng |
| NTT 32 bit, hai tầng gộp | 4 | 16 | 16 hệ số, hai tầng |

Mỗi phép nhân phức FFT dùng **ba tích thực** (gọi là "nhân phức 3 tích"), đúng như phần mềm chuẩn.
Ở 128 bit, 6 trong 64 tích con không ảnh hưởng tới kết quả nên được bỏ, và điều này vẫn chính xác từng bit.

### 3.2 Sáu thay đổi so với lõi hiện tại

| # | Thay đổi | Mục đích |
|---|---|---|
| 1 | **Bộ điều khiển pipeline**: đọc, tính và ghi chạy chồng lên nhau | Bỏ 23 chu kỳ tuần tự mỗi butterfly |
| 2 | **Gom lô theo độ rộng**: 16 / 4 / 1 butterfly cho FFT 32 / 64 / 128 bit | Đây là cơ chế biến độ rộng hẹp thành tốc độ |
| 3 | **Bảng twiddle FFT chia 4 bank** (root số k nằm ở bank k mod 4) | FFT 32 bit cần nhiều root khác nhau mỗi chu kỳ |
| 4 | **NTT 32 bit cho q = 8380417** (ML-DSA, N = 256) | Thêm chiều độ rộng cho NTT |
| 5 | **Chạy xen kẽ hai đa thức NTT** trên hai context sẵn có | Che thời gian chờ giữa các tầng |
| 6 | **FFT 64 bit theo đúng NTRUGen** | Sinh khóa FN-DSA dùng được lõi, khớp từng bit |

Không đổi: cây cộng ghép tích, cách làm tròn FFT 128 bit, NTT hai tầng gộp, bộ rút gọn modulo 16 bit hiện có.

## 4. Dự báo tốc độ

Tính bằng [model/flex_v1_projection.py](../model/flex_v1_projection.py). Đây là **dự báo**, chưa phải số đo:
giả định mỗi lượt phát được một chu kỳ một lần, đọc và ghi song song, chờ 8 chu kỳ giữa hai tầng.
Số lượt đọc bộ nhớ và số root lấy từ phân tích địa chỉ thật của lõi hiện tại.

**FFT, N = 1024** (hiện tại 52 992 chu kỳ cho cả ba độ rộng):

| Áp dụng | 32 bit | 64 bit | 128 bit |
|---|---:|---:|---:|
| Chỉ thay đổi 1 (pipeline) | 4 680 | 5 192 | 7 496 |
| Thay đổi 1 + 2 + 3 | 552 | 1 864 | 7 496 |
| Giới hạn tính toán (không thể nhanh hơn) | 432 | 1 728 | 6 912 |

- Chỉ pipeline thì ba độ rộng gần như chạy ngang nhau: chưa có chiều precision.
- Thêm gom lô thì tỉ lệ thời gian 32 : 64 : 128 bit là 1 : 3,4 : 13,6, gần mức lý tưởng 1 : 4 : 16.
- FFT ngược cho cùng số chu kỳ, cộng thêm một lượt chia cuối (khoảng 32 / 64 / 128 chu kỳ).
  Với N = 512: 264 / 832 / 3 264 chu kỳ.

**NTT** (hiện tại: 800 chu kỳ cho q12289 N1024; 160 cho N256):

| Trường hợp | Dự báo, chờ 8 chu kỳ/tầng | Nếu chờ 12 | Nếu chờ 16 |
|---|---:|---:|---:|
| q12289, N1024, một đa thức | 120 | 140 | 160 |
| q12289, N256, một đa thức | 48 | 64 | 80 |
| q12289, N256, hai đa thức xen kẽ (mỗi đa thức) | 24 | — | — |
| q8380417, N256 (NTT 32 bit) | 96 | 112 | 128 |

Với N nhỏ, thời gian chờ giữa các tầng chiếm phần lớn, nên chạy xen kẽ hai đa thức quan trọng không kém pipeline.

## 5. Quy tắc số học

### 5.1 Bản chuẩn

Bản chuẩn là mã FN-DSA fixed-point
[fixed-point-fndsa/fixed-point-c](https://github.com/fixed-point-fndsa/fixed-point-c), commit
`ad1e5bf7714d53230ad457364db8a46a1b459c94`, cấu hình mặc định (fixed-point, không AVX2).
Trong bản này:
- phần **ký** dùng FFT 128 bit (Q64.64), đã được lõi khớp từng bit;
- phần **sinh khóa** gọi thư viện **NTRUGen** đi kèm, dùng FFT 64 bit (Q32.32).

Các quy tắc FFT 32/64/128 bit hiện có giữ nguyên như [spec 1.0](../spec/FlexTransform/1.0/01_numeric_kernels.md).

### 5.2 FFT 64 bit theo NTRUGen (thay đổi 6)

Đã đọc trong mã nguồn và kiểm bằng [model/arch_checks.py](../model/arch_checks.py). Mọi phép cộng/trừ quay vòng ở 64 bit (có dấu).

```text
nhân(x, y)  = floor(x·y / 2^32)            // cắt bớt, KHÔNG làm tròn
nửa(v)      = floor((v + 1) / 2)           // cộng 1 rồi dịch phải
nhân phức 3 tích(s, y):
    z0 = nhân(s_re, y_re);  z1 = nhân(s_im, y_im)
    z2 = nhân(s_re + s_im, y_re + y_im)
    phần thực = z0 − z1;  phần ảo = z2 − (z0 + z1)

FFT xuôi:  y ← s·y;  (x, y) ← (x + y, x − y)                 // cùng lịch chỉ số với FFT 128 bit
FFT ngược: (x, y) ← (nửa(x + y), liên_hợp(s) · nửa(x − y))   // chia đôi ở MỌI tầng, không chia cuối
```

Khác với FFT 64 bit hiện có của spec ở ba điểm, nên cần thêm phần cứng nhỏ:
1. Nhân cắt bớt: bỏ hằng số làm tròn ở gốc cây cộng.
2. Chia đôi ở cả hai nhánh của butterfly ngược, mỗi tầng.
3. Bảng twiddle riêng: 1 024 số phức, chép nguyên bit từ `GM_TAB` của NTRUGen (16 KiB).

Phải build NTRUGen **không AVX2** làm chuẩn so sánh.

### 5.3 NTT 32 bit cho q = 8380417 (thay đổi 4)

```text
Hệ số nằm trong [0, q); root lưu dạng w·2^32 mod q
t = a·b
m = phần 32 bit thấp của (t · 58728449), hiểu là số có dấu   // 58728449 = q^(−1) mod 2^32
u = (t − m·q) / 2^32                                            // nằm trong (−q, q)
kết quả = u + q nếu u < 0, ngược lại u                           // = a·b·2^(−32) mod q
```

- Hai phép nhân hằng làm bằng cộng/dịch: q = 2^23 − 2^13 + 1; q^(−1) mod 2^32 = 2^26 − 2^23 + 2^13 + 1.
- NTT xuôi 8 tầng, root ζ = 1753 (bậc 512); NTT ngược nhân thêm 256^(−1) mod q = 8 347 681 ở cuối.
- **Cách đặt trong bộ nhớ**: hệ số thứ c chiếm hai ô 16 bit liền nhau (địa chỉ 2c và 2c + 1), giống cách
  FFT đặt số nhiều phần. Với cách đánh bank sẵn có của lõi, hai nửa luôn nằm ở hai bank cạnh nhau cùng hàng.
- **Không xung đột bank**: đã kiểm toàn bộ 4 lượt xuôi và ngược của N = 256, cả dữ liệu lẫn bảng root
  ([model/res32_bank_map.py](../model/res32_bank_map.py)). Chỉ hỗ trợ N = 256; với kích thước khác sẽ xung đột.

## 6. Giả thuyết cần chứng minh

Đo trên RTL v1 bằng công cụ profiling hiện có, tính chu kỳ từ lúc bắt đầu đến lúc xong lệnh.
Ngưỡng được đặt **trước khi đo**; không sửa sau khi có kết quả.

| # | Giả thuyết | Đạt khi | Bác bỏ khi |
|---|---|---|---|
| 1 | **Gom lô tạo ra chiều precision cho FFT** | N1024: FFT xuôi ≤ 700 / 2 300 / 8 500 chu kỳ cho 32 / 64 / 128 bit; FFT ngược ≤ 770 / 2 530 / 9 350. Tỉ lệ 128 bit so với 32 bit ≥ 10, so với 64 bit ≥ 3 (N512: ≥ 8). Khi chỉ có pipeline, tỉ lệ 128/32 bit ≤ 2 | Có gom lô mà tỉ lệ 128/32 bit < 4 |
| 2 | **Pipeline đưa NTT tới gần giới hạn** | Thời gian ≤ 1,25 × mô hình, với mô hình = tổng các lượt × (số nhịp + L), L là độ trễ đo được của một nhịp. Với L = 9: q12289 N1024 ≤ 156, N256 ≤ 65, hai đa thức xen kẽ ≤ 33 mỗi đa thức, NTT 32 bit N256 ≤ 125 | Vượt 2 × mô hình, hoặc N1024 > 400 |
| 3 | **Linh hoạt không đắt so với lõi chỉ làm FFT 128 bit** | Diện tích ≤ 1,35 lần lõi chỉ-128-bit; tốc độ trên diện tích ở 32 bit ≥ 7 lần, ở 128 bit ≥ 0,75 lần | Không đạt cả hai ngưỡng 32 bit |
| 4 | **Linh hoạt có giá giới hạn so với lõi chỉ làm NTT 16 bit** | Diện tích ≤ 1,5 lần; chu kỳ NTT ≤ 1,1 lần | Diện tích > 2 lần |
| 5 | **Mọi kết quả khớp từng bit với phần mềm chuẩn** | 0 sai khác; chữ ký khớp từng byte | Một sai khác (**đã đạt** với lõi hiện tại) |
| 6 | **NTT hai tầng gộp giảm một nửa lượng dữ liệu, tốn ít diện tích** | N1024 cần 5 lượt thay vì 10; thêm ≤ 3% diện tích | Thêm > 10% (**đã đo**: 5 lượt, +1,10%) |
| 7 | **Một lõi phục vụ cả ký (128 bit) và sinh khóa (64 bit)** | FFT 64 bit khớp NTRUGen; sinh khóa dùng lõi cho khóa khớp từng byte (≥ 2 seed mỗi N512/N1024) | Một sai khác |
| 8 | **NTT 32 bit chạy đúng, không xung đột bank** | Khớp NTT của bản chuẩn ML-DSA (Dilithium, pq-crystals) sau khi đổi cách biểu diễn; bộ đếm xung đột = 0 | Một sai khác hoặc có xung đột |

**Cách đo diện tích** (giả thuyết 3, 4): cùng công cụ Yosys + OpenSTA, thư viện Nangate45. Không tính RAM/ROM vào
diện tích logic ở mọi thiết kế; báo riêng số bit RAM/ROM. "Tốc độ 32 bit" của lõi chỉ-128-bit nghĩa là chạy
cùng phép biến đổi ở 128 bit (kết quả không giống hệt, chỉ để so thời gian).
Tổng diện tích các lõi chuyên dụng riêng lẻ chỉ báo cáo phụ, vì luôn lớn hơn.

**Hình chính của bài báo:** tốc độ theo độ rộng toán hạng (FFT 32/64/128, NTT 16/32) trên cùng lõi, đặt cạnh
lõi chỉ-128-bit và lõi NTT chuyên dụng.

## 7. Thay đổi so với spec 1.0

| Thay đổi | Mục spec bị thay | Nội dung mới |
|---|---|---|
| 4, 6 | 00.2 bảng định dạng | Trường định dạng 3 bit: thêm **4 = NTT 32 bit**, **5 = FFT 64 bit NTRUGen** (chỉ FFT/FFT ngược, logn 1..10); 6–7 dự trữ |
| 4 | 00.3 bảng modulus | Thêm modulus số 2 = 8380417, chỉ định dạng 4, chỉ N = 256 |
| 5 | 00.4 số đa thức mỗi lệnh | N ≥ 64: cho phép 1 hoặc 2 đa thức; đa thức thứ hai bắt đầu ở ô N (16 bit) hoặc 2N (32 bit) |
| 3 | 00.5 và 03.5 "một root mỗi chu kỳ" | 4 bank root; thêm bảng NTRUGen |
| 2 | 03.5 "nên gom butterfly" | Thành **bắt buộc**: 16 / 4 / 1 butterfly theo độ rộng |
| 4 | 03.4 cách đặt hệ số; 03.6 gói root | NTT 32 bit: hệ số c ở ô 2c, 2c + 1; gói 3 root 96 bit ở 4 bank, bank = số gói mod 4 |
| 4, 6 | 02 giao diện lệnh | `cmd_fmt_i` thành 3 bit, `cmd_reserved_i` còn 7 bit (vẫn phải bằng 0) |

Lỗi lệnh mới (giữ thứ tự kiểm như spec):

| Lỗi | Khi nào |
|---|---|
| Sai định dạng | Định dạng 6–7; NTT 32 bit cho lệnh FFT; FFT NTRUGen cho lệnh khác FFT/FFT ngược |
| Sai modulus | Modulus 2 với định dạng khác 4; định dạng 4 với modulus khác 2; modulus 3 |
| Sai kích thước | NTT 32 bit với N khác 256; FFT NTRUGen với N = 1 |
| Sai số đa thức | N ≥ 64 với hơn 2 đa thức |

## 8. Kiểm chứng và thứ tự triển khai

Mọi bước phải giữ: 5 992 kernel khớp như hiện tại, chữ ký khớp từng byte và được verifier chấp nhận.

| Bước | Làm | Kiểm và báo cáo |
|---|---|---|
| 1 | Bộ điều khiển pipeline | Chu kỳ FFT ba độ rộng và NTT khi **chỉ** có bước này; độ trễ L thật |
| 2 | Gom lô + twiddle 4 bank | Giả thuyết 1; thử 1, 2, 4 bank twiddle |
| 3 | Xen kẽ hai đa thức | Giả thuyết 2 |
| 4 | NTT 32 bit | Giả thuyết 8; so với Dilithium, giá trị biên 0, 1, q − 1 |
| 5 | FFT 64 bit NTRUGen | Giả thuyết 7 |
| 6 | Tổng hợp lõi linh hoạt, lõi chỉ-128-bit, lõi NTT chuyên dụng | Giả thuyết 3, 4; diện tích thêm của từng bước |

Báo cáo thêm: sai số FFT 32/64 bit theo độ rộng (cho xử lý tín hiệu). Nếu chu kỳ đo lệch dự báo quá 30%,
cập nhật mô hình theo độ trễ thật trước khi kết luận.

## 9. So với các công trình gần nhất

| Công trình | Đã làm | Điểm FlexTransform khác |
|---|---|---|
| *A Unified Hardware Accelerator for FFT and NTT* (ICASSP 2025) | Bộ nhân 32 bit ghép từ 16 bit; FFT 32 bit; NTT ML-KEM/ML-DSA với 4/2 butterfly mỗi chu kỳ | FFT ba độ rộng tới 128 bit, khớp bit phần mềm thật; gom lô theo độ rộng; NTT hai tầng gộp |
| *OpenNTT* | Chọn FFT/NTT và modulus khi tạo lõi | Đổi lúc chạy trên cùng lõi |
| *BitFusion* (ISCA 2018) | Ghép/tách bộ nhân theo độ rộng cho mạng nơ-ron | Có làm tròn và rút gọn modulo đúng chuẩn |
| *A Lightweight Fused Floating-Point & Modular Arithmetic Unit for FALCON FFT/NTT* (ICTA 2026) | Ghép bộ nhân 14 bit thành nhân dấu phẩy động 64 bit; tách thành 8 làn NTT | Fixed-point ba độ rộng khớp phần mềm; mới đọc tóm tắt, **cần đọc toàn văn** |

Phần "NTT hẹp hơn thì nhiều làn hơn" **không phải điểm mới**: bài ICASSP 2025 đã làm. Điểm mới nằm ở chiều
FFT, cơ chế gom lô và NTT hai tầng gộp.

## 10. Ngoài phạm vi v1 và rủi ro

- **Chưa làm trong v1:** NTT nhiều modulus kiểu RNS, phép nhân cơ sở của ML-KEM, NTT 32 bit với N khác 256,
  modulus tùy ý, FFT NTRUGen cho các phép khác ngoài FFT/FFT ngược.
- **Thứ tự kết quả NTT 32 bit so với Dilithium** chưa đối chiếu; bước kiểm phải ghi rõ phép đổi thứ tự nếu có.
- **FFT 64 bit NTRUGen** mới kiểm bằng mô hình, chưa chạy với bảng twiddle thật và chương trình C.
- **Độ trễ thật giữa các tầng** quyết định NTT N nhỏ; ngưỡng giả thuyết 2 đã viết theo độ trễ đo được.
- **Diện tích các thay đổi** chưa đo; nếu không đạt ngưỡng, báo cáo như kết quả âm.

## Phụ lục: kiểm tra có thể chạy lại

| Script | Kiểm gì |
|---|---|
| [model/arch_checks.py](../model/arch_checks.py) | Số học FFT 128 bit và 64 bit NTRUGen, cây cộng, rút gọn modulo, root |
| [model/flex_v1_projection.py](../model/flex_v1_projection.py) | Mọi dự báo chu kỳ ở mục 4 |
| [model/res32_bank_map.py](../model/res32_bank_map.py) | NTT 32 bit và xen kẽ hai đa thức không xung đột bank |
