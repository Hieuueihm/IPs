# 03 — Bộ nhớ, gom lô, bảng root và xen kẽ hai đa thức

> **Thay đổi 31/10/2026, lần 7** (người dùng duyệt): **một lane 32 bit cho mọi NTT** ([10](10_hop_dong_tile.md), lần 6). Mọi NTT lưu dạng 4, nên mạng bank → tile chỉ còn một cách
> gán và đo được 6 239 LUT (trước 8 371). Bảng root 16 bit đổi giá trị (nhân thêm 2¹⁶ mod q). Bản trước:
> [trước khi chuyển sang một lane 32 bit](../../../docs/plan_history/before_one_lane_2026-10-31/03_bo_nho.md).
>
> **Cập nhật 31/10/2026 theo tile một làn** ([10](10_hop_dong_tile.md), đầu tài liệu): mỗi tile nhận một butterfly mỗi
> chu kỳ ở cả hai lane, mỗi tầng NTT là một lượt. Mục 1 (xung đột bank), 4 (gói root) và 6 (xếp N nhỏ vào tile) viết lại
> theo mô hình [model/single_lane_feed.py](../../../model/single_lane_feed.py), kết quả ở
> [study/results/single_lane_feed.md](../../../study/results/single_lane_feed.md). Bản trước:
> [trước khi chuyển lane 32 bit sang bộ riêng](../../../docs/plan_history/spec2_before_dedicated32_2026-10-31/03_bo_nho.md).

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
| 3 | Không còn phép nào nhận (00 mục 2) | — |
| 4 | `k = 2(j·N + i)` (nửa thấp), `2(j·N + i) + 1` (nửa cao); mọi profile NTT | jobs · N · 4 |
| Nạp prime | Đọc vùng C: 16 + 8N byte (02 mục 3) | Không vùng dữ liệu nào bị sửa |

**Kích thước vùng F** (ô 16 bit, trước khi làm tròn lên lũy thừa của 2) theo vùng nhớ mà phép dùng, như bảng vùng nhớ
của 1.0 mục 03.4:

| Phép | Vùng A | Vùng B | Vùng C |
|---|---|---|---|
| FFT, FFT ngược | N·W/16 | — | — |
| Nhân số phức | N·W/16 | N·W/16 | — |
| Tách | N·W/16 | — | N·W/16 |
| Ghép | N·W/32 | N·W/32 | N·W/16 |
| NTT, NTT ngược, phép 0x7 | 2·jobs·N | — | — |
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

**Cấp dữ liệu cho NTT** (đã kiểm bằng mô hình, [model/single_lane_feed.py](../../../model/single_lane_feed.py)):
- Mỗi chu kỳ bộ điều khiển phát tối đa 16 butterfly của cùng một tầng, mỗi tile một butterfly. Mỗi butterfly đọc hai hệ
  số và ghi lại hai hệ số đó sau một độ trễ cố định; các butterfly phát cùng chu kỳ ghi cùng chu kỳ, nên nhóm đọc không
  xung đột thì nhóm ghi cũng không.
- 16 butterfly đọc 32 hệ số, tức đủ cả 32 siêu bank, và ghi 32 hệ số mỗi chu kỳ, với mọi q.
- **Đọc lệch một chu kỳ (bắt buộc):** khi hai toán hạng của một butterfly nằm cùng một bank (định dạng 4, N = 1024, tầng
  khoảng cách 512: hàm bank bỏ qua bit 10 của địa chỉ), toán hạng x được đọc sớm một chu kỳ và giữ ở đầu vào tile. Không
  có cơ chế này, N = 1024 tụt còn 3,9 butterfly/chu kỳ.
- Kết quả của mô hình (xếp tham lam theo thứ tự tự nhiên, có đọc lệch, 8 bank gói root như mục 4): 16 butterfly/chu kỳ ở
  mọi N từ 32 đến 512, xuôi và ngược; N = 1024 đạt 15,95 (trước lần 7, q 16 bit dạng 3 đạt 16,0); N < 32 bị giới hạn bởi
  N/2 butterfly mỗi tầng. Hai đa thức cùng prime ở N = 1024: 15,6 butterfly/chu kỳ.
- Mô hình giả định mạng bank → tile nối đầy đủ (mọi bank tới mọi cổng toán hạng). Crossbar đầy đủ đo được 35 623 LUT, quá
  đắt.
- **Gán butterfly vào tile theo bank của hai toán hạng** (chốt 31/10/2026)
  ([model/structured_net.py](../../../model/structured_net.py)). Khi đó không có xung đột bank dữ liệu, tốc độ 15,75
  butterfly/chu kỳ trên mọi trường hợp, và mạng chỉ cần tối đa 6 nguồn mỗi cổng đọc (nửa thấp và nửa cao), 7 mỗi cổng
  ghi: đo được 6 239 LUT, WNS +0,571 ns ([hdl/net/ntt_bank_net_s.sv](../../../hdl/net/ntt_bank_net_s.sv), ghi chú bản
  nháp mục 21; khi còn dạng 3 cho q 16 bit: 16 và 12 nguồn, 8 371 LUT, 15,9 butterfly/chu kỳ). Ở lệnh nhiều prime
  N = 8..32 một tile nhận butterfly của tối đa 2 prime; người dùng chọn cho tile hai ô modulus ([10](10_hop_dong_tile.md)
  mục 3). Cách gán: siêu bank = {F (2 bit), n (3 bit)}: khác bit q của F → tile {bit F còn lại, n}; khác bit p của n →
  tile {F, n bỏ bit p}; cùng siêu bank (N = 1024, đọc lệch) → tile = siêu bank mod 16.

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

## 4. Gói root NTT

```text
gói(g) = [GM[g], GM[2g], GM[2g+1]],  96 bit, phần tử đầu ở bit thấp
bank = g mod 8, hàng = g >> 3,  g = 1 .. max(1, N/2 − 1)
phần tử có chỉ số ≥ N đặt bằng 0 và không bao giờ được dùng
```

- Có hai bộ, một cho chiều xuôi (GM) và một cho chiều ngược (IGM). Định dạng gói và dung lượng **không đổi** so với lịch
  nhịp hai tầng, nên phép nạp prime ([02 mục 3](02_giao_dien.md)) và vector kernel không đổi.
- **Đọc theo lượt một tầng:** butterfly dùng root chỉ số r ≥ 2 đọc phần tử con (1 hoặc 2) của gói r >> 1. Root 1 là root
  chung của mọi butterfly ở tầng đầu NTT xuôi và tầng cuối NTT ngược; bộ điều khiển nạp nó vào một thanh ghi chung ở đầu
  tầng, nên mạng root của mỗi tile chỉ chọn 1 trong 17 nguồn (8 bank × 2 phần tử con, cộng root 1). Phần tử đầu của gói
  vì thế chỉ cần cho gói 1; RAM gói có thể bỏ nó ở các gói khác (chưa áp dụng).
- **8 bank gói** (trước là 4): mỗi bank đọc một gói mỗi chu kỳ. Ở các tầng cuối, 16 butterfly của một chu kỳ cần 16 root
  liên tiếp, tức 8 gói liên tiếp, nằm ở 8 bank khác nhau. Với 4 bank, mô hình chỉ đạt khoảng 14–14,5 butterfly/chu kỳ ở
  N ≥ 64.
- Bảng root của 12289 và 3329 (ROM) dùng cùng cách xếp gói và 8 bank, với giá trị `GM16[k]·2¹⁶ mod q` để dùng với
  Montgomery R = 2³² ([01 mục 3.0](01_so_hoc_kernel.md)); mỗi giá trị vẫn < 2¹⁶. Tile nhận mọi q lẻ < 2³¹, nhưng lõi chỉ
  có bảng ROM cho hai modulus này và 8380417; q nhỏ khác cần nạp bảng, **ngoài phạm vi v1**.

| Profile | Nguồn | Dung lượng |
|---|---|---|
| 2 (8380417) | ROM từ [assets/ntt_q8380417_forward.mem](assets/ntt_q8380417_forward.mem) và `_inverse.mem` | 127 gói × 96 bit mỗi chiều |
| 3 (khe prime) | RAM, do phép nạp prime ghi từ gm/igm tuyến tính | 511 gói × 96 bit mỗi chiều (khoảng 12 KiB cả hai chiều), chia cho 16 khe |

**Profile 3, địa chỉ gói:** gói g của khe s nằm ở vị trí `b_s + g − 1` trong RAM, với b_s là vị trí gói đầu của khe
([02 mục 3](02_giao_dien.md)). Bank là `(b_s + g − 1) mod 8`, hàng là `(b_s + g − 1) >> 3`. Khi các đa thức của một lệnh
dùng khe khác nhau, hai gói cùng bank trong một chu kỳ phải đọc hai lượt; mô hình đã tính khoản này (mục 6).

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
- dữ liệu 4 ô và root theo chế độ;
- nhãn đủ để ghi kết quả về đúng chỗ (context, epoch, đa thức, vị trí).

Hằng số q, q′, cờ chia đôi và hằng làm tròn được chốt vào thanh ghi của tile khi mảng rảnh, không đi kèm từng gói.

**Cách xếp đa thức vào tile** (định dạng 4):
- Một tile nhận một butterfly mỗi chu kỳ; hai toán hạng luôn ở ô d0 (x) và d1 (y), root ở r0, cho cả CT và GS.
- Tile của một butterfly do bank hai toán hạng quyết định (mục 1), không do thứ tự butterfly. Mỗi chu kỳ của một tầng,
  mỗi tile lấy butterfly kế tiếp (theo thứ tự tự nhiên) trong số các butterfly thuộc về nó.
- N ≥ 64: jobs ≤ 2; mọi tile dùng chung một prime (hoặc hai prime của hai đa thức, mỗi đa thức một ô).
- N < 64: jobs ≤ min(8, 64/N). **Nhiều prime** (profile 3, cờ cùng khe = 0): trước khi phát butterfly đầu tiên, lúc mảng
  rảnh, bộ điều khiển ghi vào mỗi tile q, q′ của những đa thức có butterfly thuộc tile đó: tối đa hai, vào ô 0 và ô 1
  (mô hình kiểm: N = 8, 16, 32 cần đúng 2; N = 2, 4 cần 1). Mỗi request mang `req_slot` của đa thức nó thuộc về. Với
  N ≥ 64 hoặc cờ cùng khe = 1, mọi tile nhận cùng một hằng số ở ô 0.
- Host **nên** đặt vị trí gói root đầu của mỗi khe ở bội của 8 (02 mục 3 vẫn cho phép mọi vị trí). Khi đó các tile ít
  tranh bank gói: mô hình đếm 40 chu kỳ thêm trên mọi trường hợp. Vị trí khác vẫn đúng kết quả, chỉ có thể chậm hơn.

Cách ghép tích giữa các tile cho FFT 64 / 128 bit giữ như 1.0 mục 03.8. Định dạng 5 dùng cùng cây ghép với định dạng 1,
chỉ khác hằng làm tròn (bằng 0).

## 7. Manifest triển khai

Thêm vào danh sách của 1.0:
- biến thể rút gọn;
- độ trễ từng chế độ của tile;
- cách mạng bank → tile đọc lệch một chu kỳ, và số thanh ghi giữ toán hạng;
- số lượt đọc root FFT mỗi lô;
- cách xếp RAM gói root của profile 3, số chu kỳ của phép nạp prime theo N, và số chu kỳ ghi hằng số cho từng tile ở
  đầu lệnh nhiều khe;
- cách xen kẽ hai đa thức.
