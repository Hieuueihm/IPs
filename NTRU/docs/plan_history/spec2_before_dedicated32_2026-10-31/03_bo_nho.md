# 03 — Bộ nhớ, gom lô, bảng root và xen kẽ hai đa thức

> **Chưa cập nhật theo hợp đồng tile một làn (31/10/2026, lần 2).** Tile nay nhận một butterfly mỗi request, không còn
> nhịp hai tầng ([10](10_hop_dong_tile.md), đầu tài liệu). Các phần dựa trên nhịp hai tầng phải làm lại trước khi dùng:
> kiểm xung đột bank ở mục 1 (đã kiểm cho lượt hai tầng và một tầng cuối), gói root ba phần tử ở mục 4, và cách xếp N
> nhỏ vào tile ở mục 6. Ghép cặp hệ số cho CT/GS nay là việc của mạng bank → tile.

Ba vùng nhớ A/B/C, hàm đánh bank `bank(k) = (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30)`, `row(k) = k >> 6`,
quy tắc một đọc + một ghi mỗi bank mỗi chu kỳ, cách nối với dòng 128 bit của host, rào chắn giữa các lượt và context
**giữ nguyên như [03 của bản 1.0](../1.0/03_microarchitecture_memory.md)**. k luôn là địa chỉ ô 16 bit.

## 1. Cách đặt hệ số

Mọi địa chỉ dưới đây cộng thêm **địa chỉ đầu** của vùng tương ứng trong lệnh (`cmd_base_a_i`, `cmd_base_b_i`,
`cmd_base_c_i`, [02 mục 1](02_giao_dien.md)). Bản 1.0 tương ứng với mọi địa chỉ đầu bằng 0.

| Định dạng | Phần tử i của đa thức j (so với địa chỉ đầu) | Số byte vào / ra |
|---|---|---|
| 0, 1, 2 | Như 1.0 (W/16 ô 16 bit liên tiếp, ô thấp trước) | Như 1.0 |
| 5 | Như định dạng 1 | Như định dạng 1 |
| 3 | `k = j·N + i` (như 1.0, nay áp dụng cả cho N ≥ 64 với j = 0, 1) | jobs · N · 2 |
| 4 | `k = 2(j·N + i)` (nửa thấp), `2(j·N + i) + 1` (nửa cao) | jobs · N · 4 |
| Nạp prime | Đọc vùng C: 16 + 8N byte (02 mục 3) | Không vùng dữ liệu nào bị sửa |

**Kích thước vùng F** (ô 16 bit, trước khi làm tròn lên lũy thừa của 2) theo vùng nhớ mà phép dùng, như bảng vùng nhớ
của 1.0 mục 03.4:

| Phép | Vùng A | Vùng B | Vùng C |
|---|---|---|---|
| FFT, FFT ngược | N·W/16 | — | — |
| Nhân số phức | N·W/16 | N·W/16 | — |
| Tách | N·W/16 | — | N·W/16 |
| Ghép | N·W/32 | N·W/32 | N·W/16 |
| NTT, NTT ngược, phép 0x7 | jobs·N (định dạng 3) hoặc 2·jobs·N (định dạng 4) | — | — |
| Phép 0x8 | như trên | như vùng A | — |
| Nạp prime | — | — | 8 + 4N |

Với W là độ rộng phần tử (64 cho định dạng 5). Địa chỉ đầu căn theo F làm tròn lên lũy thừa của 2 (ít nhất 8), nên
các bit của địa chỉ đầu rời với các bit bên trong vùng. Hàm bank tuyến tính theo xor, nên mọi nhóm đọc trong lệnh chỉ bị
xor số bank với một hằng: số xung đột bank giống hệt địa chỉ 0. Đã kiểm 4 084 trường hợp NTT 16 và 32 bit với mọi địa
chỉ đầu hợp lệ ([model/res32_bank_map.py](../../../model/res32_bank_map.py)).

**Giữ dữ liệu trong lõi.** Nội dung RAM không bị xóa giữa các lệnh (như 1.0). Trình điều khiển host có thể để đầu ra
của một lệnh nằm lại làm đầu vào của lệnh sau, và giữ nhiều bộ đệm ở các địa chỉ khác nhau trong 48 KiB. Lõi không theo
dõi bộ đệm nào; việc chọn chỗ là của host.

Hai nửa của hệ số 32 bit luôn nằm ở hai bank cạnh nhau (bank(2c+1) = bank(2c) xor 1) cùng hàng, nên một "siêu bank 32
bit" đọc được cả hệ số trong một chu kỳ.

**Xung đột bank đã kiểm** ([model/res32_bank_map.py](../../../model/res32_bank_map.py)), cho các lượt hai tầng và lượt
một tầng cuối:
- Định dạng 4, N ≤ 512, và đa thức thứ hai ở N = 256: không xung đột.
- Định dạng 4, N = 1024: 20% chu kỳ phải đọc hai lượt. Được phép; phải phục vụ nhiều lượt theo quy tắc của 1.0. Không
  làm chậm, vì phần tính chỉ nhận 1,33 trong 4 nhịp mà bộ nhớ cấp được mỗi chu kỳ.
- Định dạng 3, đa thức thứ hai ở N = 64..1024: không xung đột.
- Định dạng 4, N < 64 với min(8, 64/N) đa thức (tới 64 hệ số, 128 ô): không xung đột khi đọc mỗi nhóm 4 nhịp theo thứ
  tự đa thức (đã kiểm N = 4..32, cả lượt hai tầng và một tầng). N = 2: 16 hệ số nằm trong hàng đầu, mỗi hệ số một siêu
  bank riêng.
- Với mọi N khác: địa chỉ của đa thức thứ hai chỉ cộng thêm một khoảng có các bit rời với bit trong đa thức. Hàm bank
  tuyến tính theo xor, nên số bank chỉ bị xor với một hằng. Vì vậy đa thức thứ hai có đúng tính chất xung đột của đa
  thức thứ nhất.

## 2. Gom lô FFT (bắt buộc)

Bản 1.0 chỉ khuyến nghị; bản 2.0 **bắt buộc**:
- Bộ điều khiển phải phát được các lô 16 / 4 / 1 butterfly độc lập cho W = 32 / 64 / 128 bit. Định dạng 5 là W = 64.
- Tầng nào không đủ butterfly thì phát lô thiếu, kèm mặt nạ lane.
- Đọc, tính và ghi chạy chồng nhau giữa các lô (thay đổi 1 của kiến trúc). Tầng sau chỉ bắt đầu đọc khi mọi kết quả
  của tầng trước đã ghi xong.

Mục tiêu thời gian của gom lô là giả thuyết 3 của kiến trúc, không phải điều kiện chức năng.

## 3. Bảng root FFT

- Hai bảng:
  - Q64.64 của 1.0, dùng cho định dạng 0–2, lượng tử hóa xuống W = 32/64 như 1.0;
  - Q32.32 của NTRUGen ([assets/fft_ntrugen_q32_32.mem](assets/fft_ntrugen_q32_32.mem)), dùng nguyên giá trị cho
    định dạng 5.
- **4 bank:** root số k ở bank k mod 4, hàng k >> 2. Mỗi bank đọc được một root mỗi chu kỳ.
- Một lô cần nhiều root khác nhau trong cùng bank thì đọc nhiều lượt. Lô chỉ được phát khi đã có đủ root.
- Root cùng chỉ số có thể phát chung cho nhiều butterfly.

## 4. Gói root NTT lane 32 bit

```text
gói(g) = [GM[g], GM[2g], GM[2g+1]],  96 bit, phần tử đầu ở bit thấp
bank = g mod 4, hàng = g >> 2,  g = 1 .. max(1, N/2 − 1)
phần tử có chỉ số ≥ N đặt bằng 0 và không bao giờ được dùng
```

- Có hai bộ, một cho chiều xuôi (GM) và một cho chiều ngược (IGM).
- Lượt một tầng cuối lấy hai root con từ gói của nút cha `max(1, g >> 1)`, như 1.0.
- Đã kiểm với mọi N từ 4 đến 1024: mỗi bank chỉ bị đọc nhiều nhất một gói mỗi chu kỳ.

| Profile | Nguồn | Dung lượng |
|---|---|---|
| 2 (8380417) | ROM từ [assets/ntt_q8380417_forward.mem](assets/ntt_q8380417_forward.mem) và `_inverse.mem` | 127 gói × 96 bit mỗi chiều |
| 3 (khe prime) | RAM, do phép nạp prime ghi từ gm/igm tuyến tính | 511 gói × 96 bit mỗi chiều (khoảng 12 KiB cả hai chiều), chia cho 16 khe |

**Profile 3, địa chỉ gói:** gói g của khe s nằm ở vị trí `b_s + g − 1` trong RAM, với b_s là vị trí gói đầu của khe
([02 mục 3](02_giao_dien.md)). Bank là `(b_s + g − 1) mod 4`, hàng là `(b_s + g − 1) >> 2`. Khi các đa thức của một lệnh
dùng khe khác nhau, hai gói cùng bank trong một chu kỳ phải đọc hai lượt. Được phép: phần tính 32 bit chỉ cần khoảng
1,33 gói mỗi chu kỳ, còn 4 bank cấp được 4.

Cách phép nạp prime đọc vùng C và ghi RAM gói do người triển khai chọn. Chỉ yêu cầu nội dung RAM đúng định nghĩa ở
trên khi phép nạp báo thành công.

## 5. Xen kẽ hai đa thức

- Lệnh NTT với jobs = 2 và N ≥ 64: đa thức 0 dùng context 0, đa thức 1 dùng context 1.
- Rào chắn giữa các lượt tính **riêng cho từng đa thức**. Lượt k của đa thức 1 được chạy trong lúc lượt k của đa thức 0
  đang chờ ghi xong, và ngược lại.
- Kết quả phải giống hệt khi chạy hai lệnh một đa thức riêng rẽ.
- Lệnh chỉ báo thành công khi cả hai đa thức đã ghi xong.

## 6. Giao tiếp nội bộ với mảng nhân

Gói dữ liệu giữa bộ điều khiển và mảng nhân là giao diện nội bộ, được đổi cách mã hóa. Nó phải mang đủ thông tin để
mỗi tile nhận đúng các trường của [hợp đồng tile](10_hop_dong_tile.md):
- chế độ, hướng;
- lane 16 hay 32 bit;
- dữ liệu 4 ô và root theo chế độ;
- nhãn đủ để ghi kết quả về đúng chỗ (context, epoch, đa thức, vị trí).

Hằng số q, q′, cờ chia đôi và hằng làm tròn được chốt vào thanh ghi của tile khi mảng rảnh, không đi kèm từng gói.

**Cách xếp N nhỏ vào tile** (định dạng 3 và 4):
- N ≥ 4: như 1.0, `tile = job · (N/4) + tile_trong_đa_thức`. Với định dạng 4, jobs ≤ min(8, 64/N) nên dùng tối đa 16
  tile.
- N = 2 (chỉ profile 3): mỗi đa thức một tile, `tile = job`, một tầng, chế độ 4.
- **Mỗi tile một modulus** (profile 3, N < 64, cờ cùng khe = 0): trước khi phát nhịp đầu tiên của lệnh, lúc mảng rảnh,
  bộ điều khiển ghi q, q′ của khe (khe đầu + j) mod 16 vào thanh ghi hằng số của mọi tile chứa đa thức j. Các tile không
  dùng giữ nguyên. Với N ≥ 64 hoặc cờ cùng khe = 1, mọi tile nhận cùng một hằng số.
  - NTT xuôi: hệ số 0 ở ô d0, hệ số 1 ở ô d2.
  - NTT ngược: hệ số 0 ở ô d0, hệ số 1 ở ô d1.
  - Ô không dùng và root r1 bằng 0. Chỉ ghi lại hai ô kết quả tương ứng.

Cách ghép tích giữa các tile cho FFT 64 / 128 bit giữ như 1.0 mục 03.8. Định dạng 5 dùng cùng cây ghép với định dạng 1,
chỉ khác hằng làm tròn (bằng 0).

## 7. Manifest triển khai

Thêm vào danh sách của 1.0:
- biến thể rút gọn;
- độ trễ từng chế độ của tile;
- số lượt đọc root FFT mỗi lô;
- cách xếp RAM gói root của profile 3, số chu kỳ của phép nạp prime theo N, và số chu kỳ ghi hằng số cho từng tile ở
  đầu lệnh nhiều khe;
- cách xen kẽ hai đa thức.
