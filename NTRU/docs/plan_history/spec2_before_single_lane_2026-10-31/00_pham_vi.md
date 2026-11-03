# 00 — Phạm vi, định dạng, modulus và cấu hình

Phần không nhắc tới ở đây **giữ nguyên như [00 của bản 1.0](../1.0/00_scope_profiles.md)**.

## 1. Các phép (opcode)

| Opcode | Phép | Định dạng được phép | Ghi chú |
|---:|---|---|---|
| 0x0 | FFT | 0, 1, 2, 5 | Định dạng 5 là FFT 64 bit theo NTRUGen |
| 0x1 | FFT ngược | 0, 1, 2, 5 | |
| 0x2 | Nhân số phức từng điểm | 0, 1, 2 | Như 1.0 |
| 0x3 | Tách (split) | 0, 1, 2 | Như 1.0 |
| 0x4 | Ghép (merge) | 0, 1, 2 | Như 1.0 |
| 0x5 | NTT | 3, 4 | |
| 0x6 | NTT ngược | 3, 4 | Cách chuẩn hóa theo modulus (mục 3) |
| 0x7 | Đưa vào miền Montgomery: x → x·R mod q | 3, 4 | |
| 0x8 | Nhân từng điểm Montgomery: a·b·R⁻¹ mod q | 3, 4 | |
| **0x9** | **Nạp prime** | 4 | Mới. Chỉ modulus 3. Đọc p, p0i, R² mod p và hai bảng root từ vùng nhớ C ([02](02_giao_dien.md)) |
| 0xA–0xF | Dự trữ | — | Lỗi sai opcode |

Vẫn **không** có: phép nhân cơ sở của ML-KEM, ghép CRT, chia, căn, dấu phẩy động, sinh khóa hay ký trọn vẹn.

## 2. Trường định dạng (3 bit)

| Định dạng | Ý nghĩa | Bit mỗi phần tử | Quy tắc số học |
|---:|---|---:|---|
| 0 | Q16.16 | 32, có dấu | Như 1.0 |
| 1 | Q32.32 | 64, có dấu | Như 1.0 (làm tròn nửa-lên, chia ở cuối FFT ngược) |
| 2 | Q64.64 | 128, có dấu | Như 1.0, khớp từng bit bản chuẩn ký FN-DSA |
| 3 | Hệ số 16 bit | 16, không dấu, trong [0, q) | Như 1.0 |
| **4** | **Hệ số 32 bit** | 32, không dấu, trong [0, q) | Mới, [01 mục 3–4](01_so_hoc_kernel.md) |
| **5** | **Q32.32 theo NTRUGen** | 64, có dấu | Mới: nhân cắt bớt, chia đôi mỗi tầng, bảng root riêng ([01 mục 2](01_so_hoc_kernel.md)) |
| 6–7 | Dự trữ | — | Lỗi sai định dạng |

Định dạng 1 và 5 cùng độ rộng nhưng **khác quy tắc số học**. Không được đổi định dạng của một lệnh để tăng tốc.

## 3. Modulus (trường profile, 2 bit)

| Profile | q | Định dạng | logn | NTT ngược chuẩn hóa thế nào |
|---:|---|---:|---|---|
| 0 | 12289 | 3 | 3..10 | Như 1.0: nhân 2^(−logn) ở cuối |
| 1 | 3329 | 3 | 3..8 | Như 1.0 (N = 256: 7 tầng) |
| **2** | **8380417** | 4 | **chỉ 8** | Nhân 256⁻¹ ở cuối |
| **3** | **Prime 31 bit đã nạp vào khe** | 4 | 1..10, không lớn hơn logn lúc nạp khe | **Chia đôi ở mỗi tầng**, không nhân ở cuối (theo NTRUGen) |

- Phép FFT phải có profile = 0.
- Profile 3 dùng các **khe prime** đã nạp. Lõi có **16 khe**; mỗi khe giữ một prime và bảng root của nó. Các đa thức
  trong một lệnh có thể dùng các khe khác nhau, tức chạy các modulus khác nhau cùng lúc trên các tile khác nhau
  (mục 4).
- Lõi không kiểm p có phải số nguyên tố hay bảng root có đúng không; đó là trách nhiệm của host, giống như việc giữ hệ
  số trong [0, q).

## 4. Số đa thức mỗi lệnh

| Định dạng | N nhỏ | N lớn |
|---|---|---|
| FFT (0, 1, 2, 5) | 1 | 1 |
| 3 | jobs · N ≤ 64 (như 1.0) | **N ≥ 64: 1 hoặc 2** |
| 4 | N < 64: tối đa min(8, 64/N) | **N ≥ 64: 1 hoặc 2** (profile 3: 2 đa thức phải cùng khe) |
| Nạp prime | 1 | 1 |

Hai đa thức ở N ≥ 64 chạy xen kẽ trên hai context để che độ trễ giữa các tầng (thay đổi 6 của kiến trúc). Các đa
thức trong một lệnh dùng chung phép, định dạng, profile và logn.

**Profile 3, khe của từng đa thức:**
- Lệnh có trường "khe đầu" s và cờ "cùng khe".
- Cờ "cùng khe" = 1: mọi đa thức dùng khe s.
- Cờ "cùng khe" = 0: đa thức j dùng khe (s + j) mod 16.
- Với N < 64, mỗi đa thức nằm trên các tile riêng, nên mỗi tile chạy với modulus của khe mình (thay đổi 9 của kiến
  trúc). Với N ≥ 64, mọi tile phục vụ cả lệnh, nên chỉ một khe được dùng.

## 5. Bộ tham số tham chiếu

Giữ cấu hình 16 tile của 1.0, đổi các dòng sau:

| Tham số | Bản 1.0 | Bản 2.0 |
|---|---|---|
| Rút gọn modulo | 64 bộ rút gọn riêng | **Lai**: 3329/12289 dùng 64 bộ rút gọn hằng; lane 32 bit rút gọn trên mảng nhân ([hợp đồng tile](10_hop_dong_tile.md)); bản đối chứng là tham số RTL |
| Số root FFT mỗi chu kỳ | 1 | **4 bank**, root số k ở bank k mod 4 |
| Bảng root FFT | Q64.64 (1 024 số phức) | Thêm bảng Q32.32 của NTRUGen (1 024 số phức, 16 KiB) |
| Gói root NTT lane 32 bit | — | 3 root × 32 bit = 96 bit, 4 bank, bank = số gói mod 4 |
| Bảng root cho profile 3 | — | RAM, mỗi chiều 511 gói × 96 bit, chia cho các khe theo vị trí host chọn |
| Khe prime | — | **16**, mỗi khe: p, p0i, R² mod p, logn, mặt nạ bảng, vị trí gói đầu, cờ hợp lệ |
| Trường định dạng / khe đầu / cùng khe / dự trữ | 2 / — / — / 8 bit | **3 / 4 / 1 / 2 bit** |
| Context | 2 | 2 (dùng cho xen kẽ hai đa thức) |
| Giao dịch bộ nhớ host đang chờ | 1 | **8**, 1 dòng 128 bit mỗi chu kỳ ([02 mục 6](02_giao_dien.md)) |
| Địa chỉ dữ liệu trong lệnh | Luôn 0 | **Địa chỉ đầu 13 bit cho mỗi vùng A, B, C** ([02 mục 1](02_giao_dien.md)) |

## 6. Trạng thái giữ qua các lệnh

Ngoài nội dung RAM như 1.0, lõi giữ **trạng thái của 16 khe prime**. Mỗi khe có p, p0i, R² mod p, logn của bảng, mặt
nạ bảng có mặt (gm, igm), vị trí gói đầu trong RAM gói root, và một cờ hợp lệ.
- Phép nạp prime thành công đặt cờ hợp lệ của khe được nạp.
- Phép nạp cũng xóa cờ của mọi khe khác có vùng gói chồng lên vùng vừa ghi.
- Reset xóa cờ của mọi khe. Một phép nạp bị hủy hay lỗi giữa chừng xóa cờ của khe đang nạp.
- Lệnh profile 3 bị từ chối khi một khe cần dùng chưa hợp lệ, khi logn lớn hơn logn của khe, hoặc khi khe thiếu bảng
  cần dùng ([02](02_giao_dien.md)). Logn nhỏ hơn được phép, vì bảng của N lớn chứa bảng của mọi N nhỏ hơn.

Lịch chạy vẫn phải **không phụ thuộc giá trị hệ số** như 1.0. Giá trị của p không được làm đổi lịch.
