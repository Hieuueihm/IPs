# 02 — Giao diện lệnh, nạp prime và lỗi

Giao thức valid/ready, reset, pause và flush **giữ nguyên như [02 của bản 1.0](../1.0/02_interfaces_protocol.md)**.
Giao diện bộ nhớ host giữ tín hiệu của 1.0 nhưng có pipeline (mục 6). Tài liệu này chỉ nêu phần thay đổi.

## 1. Trường lệnh

| Tín hiệu | Bit | Bản 2.0 |
|---|---:|---|
| `cmd_op_i` | 4 | 0x0–0x9 ([00 mục 1](00_pham_vi.md)) |
| `cmd_fmt_i` | **3** | 0–5 ([00 mục 2](00_pham_vi.md)) |
| `cmd_profile_i` | 2 | 0–3, cả bốn giá trị đều dùng ([00 mục 3](00_pham_vi.md)) |
| `cmd_logn_i` | 4 | Như 1.0 |
| `cmd_jobs_m1_i` | 3 | Như 1.0 |
| `cmd_tag_i` | 32 | Như 1.0 |
| **`cmd_slot_i`** | **4** | Khe đầu (profile 3 và phép nạp prime); lệnh khác phải bằng 0 |
| **`cmd_same_slot_i`** | **1** | 1 = mọi đa thức dùng khe đầu; 0 = đa thức j dùng khe (khe đầu + j) mod 16. Chỉ profile 3, lệnh 0x5–0x8; lệnh khác phải bằng 0 |
| `cmd_reserved_i` | **2** | Phải bằng 0 |
| **`cmd_base_a_i`** | **13** | Địa chỉ đầu (ô 16 bit) của dữ liệu trong vùng A |
| **`cmd_base_b_i`** | **13** | Địa chỉ đầu trong vùng B |
| **`cmd_base_c_i`** | **13** | Địa chỉ đầu trong vùng C |

Định dạng, khe đầu và cờ cùng khe lấy 6 bit từ trường dự trữ của 1.0. Ba trường địa chỉ là phần thêm mới: payload lệnh
từ 55 bit thành 94 bit.

**Địa chỉ đầu** (thay đổi 11 của kiến trúc):
- Mỗi phép đọc/ghi dữ liệu ở vùng của nó (bảng ở [03 mục 1](03_bo_nho.md)) bắt đầu từ địa chỉ đầu của vùng đó, thay cho
  địa chỉ 0 của 1.0.
- Vùng mà lệnh không dùng phải có địa chỉ đầu bằng 0.
- Địa chỉ đầu phải là bội của F, với F là kích thước vùng dữ liệu của lệnh ở vùng đó (tính bằng ô 16 bit), làm tròn lên
  lũy thừa của 2, nhỏ nhất 8. Đồng thời địa chỉ đầu + F ≤ 8 192.
- Với điều kiện này, xung đột bank giống hệt khi đặt ở địa chỉ 0 ([03 mục 1](03_bo_nho.md)).
- Lõi không có trạng thái địa chỉ nào giữ qua các lệnh.

## 2. Mã kết quả và thứ tự kiểm

| Mã | Tên | Khi nào |
|---:|---|---|
| 0x00 | Thành công | Như 1.0 |
| 0x01 | Sai dự trữ | `cmd_reserved_i` khác 0; hoặc `cmd_slot_i`, `cmd_same_slot_i` khác 0 ở lệnh không dùng chúng |
| 0x02 | Sai opcode | Opcode 0xA–0xF |
| 0x03 | Sai định dạng | Định dạng 6–7, hoặc định dạng không được phép cho opcode (bảng ở 00 mục 1) |
| 0x04 | Sai profile | Phép FFT với profile ≠ 0; định dạng 3 với profile 2 hoặc 3; định dạng 4 với profile 0 hoặc 1; nạp prime với profile ≠ 3 |
| 0x05 | Sai kích thước | logn ngoài bảng ở 00 mục 3; định dạng 5 với logn = 0; profile 2 với logn ≠ 8; profile 3 hoặc nạp prime với logn = 0 hoặc > 10 |
| 0x06 | Sai số đa thức | Vượt bảng ở 00 mục 4; hoặc profile 3, N ≥ 64, 2 đa thức với cờ cùng khe = 0 |
| **0x07** | **Chưa nạp prime** | Lệnh 0x5–0x8 với profile 3 khi một khe cần dùng: chưa hợp lệ; hoặc logn của lệnh **lớn hơn** logn của khe; hoặc NTT cần gm mà khe không có gm; hoặc NTT ngược cần igm mà khe không có igm. Phép 0x7, 0x8 không cần bảng |
| **0x08** | **Dữ liệu prime sai** | Phép nạp prime đọc thấy phần đầu không hợp lệ (mục 3) |
| **0x09** | **Sai địa chỉ** | Địa chỉ đầu của một vùng được dùng không là bội của F, hoặc địa chỉ đầu + F > 8 192; hoặc vùng không dùng có địa chỉ đầu khác 0 |
| 0x10 | Bị hủy | Như 1.0 |
| 0x11 | Lỗi nội bộ | Như 1.0 |

Khi nhiều trường cùng sai, báo lỗi đầu tiên theo thứ tự 0x01 → 0x02 → 0x03 → 0x04 → 0x05 → 0x06 → 0x09 → 0x07. Các lỗi này
được phát hiện trước khi chạy: không đọc dữ liệu, không ghi RAM, trả `job_mask = 0`, giống 1.0. Lỗi 0x08 chỉ phát hiện
được sau khi đọc phần đầu của dữ liệu prime (mục 3).

## 3. Phép nạp prime (opcode 0x9)

Lệnh: `op = 0x9`, `fmt = 4`, `profile = 3`, `logn` = logn của bảng, `jobs = 1`, `cmd_slot_i` = khe được nạp,
`cmd_same_slot_i = 0`.

Trước lệnh, host ghi vào **vùng nhớ C**, bắt đầu từ địa chỉ đầu `cmd_base_c_i` (theo byte, little-endian, byte 0 ở
địa chỉ đầu). F của phép nạp là (16 + 8N) / 2 ô, làm tròn lên lũy thừa của 2.

| Byte | Nội dung |
|---|---|
| 0–3 | p |
| 4–7 | p0i = −p⁻¹ mod 2³² |
| 8–11 | R² mod p, với R = 2³² |
| 12 | logn của bảng |
| 13 | Bảng có mặt: bit 0 = gm, bit 1 = igm; giá trị 1, 2 hoặc 3 |
| 14–15 | Vị trí gói đầu b (số 16 bit, 0 ≤ b ≤ 510) trong RAM gói root |
| 16 … 16 + 4N − 1 | gm[0 … N−1], mỗi phần tử 32 bit (chỉ đọc nếu bit 0 = 1) |
| 16 + 4N … 16 + 8N − 1 | igm[0 … N−1] (chỉ đọc nếu bit 1 = 1) |

N = 2^logn. Lớn nhất 16 + 8 · 1 024 = 8 208 byte, vừa trong 16 KiB của vùng C. Các bảng là bảng tuyến tính đúng như
NTRUGen tạo ra; lõi tự xếp thành gói root ([03](03_bo_nho.md)). NTRUGen thường chỉ tạo một trong hai bảng
(`mp_mkgm` hoặc `mp_mkigm`), nên được nạp riêng từng bảng để giảm thời gian.

Vùng gói của khe là các vị trí b … b + G − 1, với G = max(1, N/2 − 1) là số gói của bảng. Cùng vùng này dùng cho cả
RAM chiều xuôi và RAM chiều ngược.

**Trình tự của lõi:**
1. Xóa cờ hợp lệ của khe `cmd_slot_i`.
2. Đọc phần đầu và kiểm tra:
   - p lẻ, 3 ≤ p < 2³¹;
   - byte 12 bằng `cmd_logn_i`;
   - byte 13 là 1, 2 hoặc 3;
   - b + G ≤ 511.

   Sai thì kết thúc với mã 0x08 và không ghi bảng root.
3. Xóa cờ hợp lệ của mọi khe khác có vùng gói chồng lên b … b + G − 1.
4. Đọc các bảng có mặt, xếp vào RAM gói root của chiều tương ứng từ vị trí b.
5. Chốt p, p0i, R² mod p, logn, mặt nạ bảng và b vào khe; đặt cờ hợp lệ; báo thành công.

Lõi **không** kiểm p0i có đúng là −p⁻¹ không, không kiểm p là số nguyên tố, không kiểm bảng root. Nội dung vùng C
không bị sửa. Chu kỳ của phép này được tính vào bộ đếm của lệnh như mọi lệnh khác. Khi báo kết quả cho sinh khóa, thời
gian host ghi vùng C và chu kỳ của phép nạp đều phải được cộng vào.

Flush hoặc reset trong lúc nạp: cờ của khe đang nạp giữ ở 0 (đã xóa ở bước 1); lệnh bị flush kết thúc với mã 0x10.
Reset xóa cờ của mọi khe.

## 4. Dùng các khe đã nạp

Lệnh 0x5–0x8 với profile 3 dùng các khe theo [00 mục 4](00_pham_vi.md). Mỗi khe giữ nguyên qua các lệnh cho đến khi
nó bị nạp lại, bị một lần nạp khác ghi đè vùng gói, bị reset, hoặc một lần nạp vào chính nó bị lỗi hay bị hủy.

Với N < 64 và cờ cùng khe = 0, các đa thức chạy **các modulus khác nhau cùng lúc**. Bộ điều khiển ghi q, q′ của khe
tương ứng vào thanh ghi hằng số của các tile chứa đa thức đó, lúc mảng rảnh ([03 mục 6](03_bo_nho.md)).

**Một bảng dùng cho mọi N nhỏ hơn.** Với bảng của NTRUGen, N′ phần tử đầu của bảng nạp cho N chính là bảng cho N′ < N.
Điều này đã kiểm trên cả 323 prime, mọi cặp logn liền nhau, cả gm lẫn igm. NTRUSolve cũng gọi `mp_NTT(logn − 1, …)`
với bảng của logn. Vì vậy lệnh profile 3 được chạy với mọi logn ≤ logn của khe; host chỉ cần nạp một lần cho mỗi
prime, ở N lớn nhất cần dùng. Gói root vẫn đúng: gói g < N′/2 chỉ dùng root có chỉ số < N′.

**Cách host dùng cho sinh khóa.** NTRUSolve xử lý từng prime theo một chuỗi: tạo bảng, NTT, nhân từng điểm, NTT ngược.
Để có lợi từ nhiều khe, host tách vòng lặp theo prime: nạp tới 16 prime vào các khe, chạy NTT của chúng trong một lệnh,
làm phép nhân từng điểm, rồi chạy NTT ngược trong một lệnh. Đây là thay đổi ở phần mềm host, không đổi kết quả số học,
vì các làn RNS độc lập.

## 5. Bộ đếm

Như 1.0. Manifest triển khai phải ghi thêm, cho từng (phép, định dạng, profile, logn, số đa thức), số chu kỳ đo được
với cùng điều kiện như mục 4 của [kiến trúc v1](../../../docs/architecture_v1.md).

## 6. Giao diện bộ nhớ host có pipeline (thay đổi 10)

Tín hiệu, cách đánh địa chỉ, byte-enable, mã trả lời và quy tắc theo trạng thái (IDLE đọc/ghi, RUN không nhận, DONE chỉ
đọc) giữ như 1.0 mục 02.3. Thay đổi:
- **Tới 8 giao dịch đang chờ.** `mem_req_ready_o` có thể bằng 1 khi còn giao dịch chưa trả lời. Lõi phải nhận được một
  yêu cầu mỗi chu kỳ khi còn chỗ.
- **Trả lời đúng thứ tự nhận**, mỗi yêu cầu đúng một trả lời. Không đổi thứ tự giữa đọc và ghi.
- **Tốc độ:** khi host gửi liên tục và giữ `mem_rsp_ready_i = 1`, lõi phải đạt ít nhất 0,9 dòng mỗi chu kỳ cho chuỗi đọc
  liên tiếp, chuỗi ghi liên tiếp và chuỗi xen kẽ. Dòng 128 bit có 8 ô 16 bit liên tiếp, nằm ở 8 bank khác nhau, nên một
  dòng mỗi chu kỳ không vượt số cổng bank.
- **Ghi rồi đọc cùng địa chỉ:** lần đọc phải thấy dữ liệu vừa ghi (đọc sau ghi đúng thứ tự).
- Trả lời ghi "thành công" vẫn chỉ phát sau khi mọi byte đã ghi xong.
- Trước khi nhận lệnh mới, mọi giao dịch đang chờ phải trả lời xong, như quy tắc RETURN của 1.0.
- Flush chờ các giao dịch đã nhận trả lời xong; giới hạn 256 chu kỳ của 1.0 tính từ lúc đó.

Nối với cổng AXI HP 128 bit của Zynq UltraScale+ bằng một bộ chuyển đổi **bên ngoài lõi**; giao diện này không phải AXI.
