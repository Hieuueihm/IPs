# 10 — Hợp đồng cấp tile

> **Thay đổi 01/11/2026, lần 7** (người dùng chọn): **thiết kế v1 là biến thể trên mảng** (mục 5.1, tham số 1). Với một lane
> 32 bit, giả thuyết 2 đạt ở cấp tile (khóa lại lần 5: trên mảng 781 LUT / 4 DSP so với riêng 777 LUT / 11 DSP), nên theo
> mục 8 lõi dùng rút gọn trên mảng: không DSP nào ngoài 4 bộ nhân của tile, NTT 1/3 request/chu kỳ mỗi tile. Bộ Montgomery
> riêng (mục 5.2, tham số 3) trở lại làm bản đối chứng. Giao diện, vector và kiểm thử không đổi. Bản trước:
> [trước khi chuyển v1 sang trên mảng](../../../docs/plan_history/before_on_array_v1_2026-11-01/10_hop_dong_tile.md).
>
> **Thay đổi 31/10/2026, lần 6** (người dùng duyệt): **một lane 32 bit cho mọi NTT.** Bỏ lane 16 bit: mọi modulus, kể cả
> 3329 và 12289, đi qua cùng bộ Montgomery 32 bit với R = 2³². Bỏ `cfg_lane32`; `req_slot` áp dụng cho mọi request NTT.
> Lý do: tile bớt bộ rút gọn lane 16 bit, và mạng bank → tile chỉ còn một cách xếp dữ liệu (dạng 4, [03](03_bo_nho.md)).
> Số đo: xem mục 8 và [ghi chú bản nháp](../../../study/results/tile_thu_draft.md) mục 21. Cái giá: NTT q nhỏ trễ 15 thay vì
> 13 chu kỳ; dữ liệu q nhỏ chiếm gấp đôi bộ nhớ và gấp đôi số dòng chép host; biến thể trên mảng nay chậm 3 lần cho mọi
> q, không chỉ cho q 32 bit. Bản trước:
> [trước khi chuyển sang một lane 32 bit](../../../docs/plan_history/before_one_lane_2026-10-31/10_hop_dong_tile.md).
>
> **Thay đổi 31/10/2026, lần 5** (người dùng chọn): **thanh ghi hằng số có hai ô** (q, q′), mỗi request chọn ô bằng
> `req_slot`. Lý do: mạng bank → tile có cấu trúc gán butterfly vào tile theo bank của toán hạng (spec 03 mục 1); ở lệnh
> nhiều prime N = 8..32, một tile khi đó nhận butterfly của tối đa hai prime. Mạng giảm từ 35 623 xuống 9 397 LUT (ghi chú
> bản nháp mục 16). Bản trước:
> [trước khi thêm ô hằng số thứ hai](../../../docs/plan_history/spec2_before_two_slots_2026-10-31/10_hop_dong_tile.md).
>
> **Thay đổi 31/10/2026, lần 4** (người dùng xác nhận): **lane 32 bit dùng bộ Montgomery riêng**. Giả thuyết 2 bị bác bỏ
> ở cấp tile trên RTL nghiệm thu ([11](11_kiem_thu_tile.md), nhóm D: LUT +12,8% để bớt 7 DSP), nên theo mục 8 lane 32 bit
> của lõi dùng bộ Montgomery riêng (mục 5.2, tham số 3). Lane 16 bit giữ rút gọn trên mảng. Biến thể lane 32 bit trên mảng
> (tham số 1) chỉ còn là số đo đã ghi. Bản trước:
> [trước khi chuyển lane 32 bit sang bộ riêng](../../../docs/plan_history/spec2_before_dedicated32_2026-10-31/10_hop_dong_tile.md).
>
> **Thay đổi 31/10/2026, lần 3** (người dùng chọn): **thiết kế v1 rút gọn mọi modulus trên mảng nhân**, kể cả lane 16
> bit (ba lượt Montgomery chạy trên ba bộ nhân khác nhau, 1 request/chu kỳ, mọi q lẻ < 2¹⁶). Lý do: với một làn NTT mỗi
> tile, cách này ít LUT hơn bộ rút gọn hằng 6,7% trên bản nháp (ghi chú bản nháp mục 9), cùng DSP và tốc độ. Bản đối
> chứng của giả thuyết 2 đổi theo: lane 16 bit giống thiết kế, chỉ lane 32 bit dùng bộ Montgomery riêng. Bộ rút gọn
> hằng 3329/12289 chỉ còn là điểm đo. Bản trước:
> [trước khi chuyển sang mọi modulus trên mảng](../../../docs/plan_history/spec2_before_all_on_array_2026-10-31/10_hop_dong_tile.md).
>
> **Thay đổi 31/10/2026, lần 2** (người dùng duyệt): **một làn NTT mỗi tile, bố cục ô cố định**. Lý do: tách LUT của bản
> nháp ([study/results/tile_thu_draft.md](../../../study/results/tile_thu_draft.md) mục 8) cho thấy 4 làn NTT 16 bit
> chiếm khoảng 1 700 / 4 000 LUT mỗi tile, trong khi NTT 16 bit chiếm dưới 0,1% số chu kỳ của FN-DSA; khoảng một phần
> ba LUT là hoán vị dữ liệu bên trong tile. Bản trước:
> [trước khi chuyển sang một làn](../../../docs/plan_history/spec2_before_single_lane_2026-10-31/10_hop_dong_tile.md).
>
> | Hạng mục | Trước | Sau |
> |---|---|---|
> | Làn NTT 16 bit mỗi tile | 4 làn, 4 bộ rút gọn hằng | 1 làn, 1 bộ rút gọn hằng |
> | Chế độ 3 (nhịp hai tầng) | Có, cả hai lane | **Bỏ**; mã 3 thành dự trữ |
> | Chế độ 4 | 4 hệ số, 2 butterfly, cách xếp ô đổi theo chiều | **1 butterfly**: x = d0, y = d1, w = r0; ra z0, z1; không đổi theo chiều |
> | Chế độ 2 | 4 phép nhân modulo | **1 phép nhân**: z0 = Mont(d0, r0) |
> | `req_data` / `req_root` / `rsp_data` | 128 / 128 / 128 bit | 64 / 32 / 65 bit |
> | Ghép cặp CT/GS, đặt kết quả, chia root | Trong tile | Ở tầng bộ nhớ (mạng bank → tile), [03](03_bo_nho.md) |
> | Tốc độ, lane 16 bit | 1 request/chu kỳ (4 hoặc 2 butterfly) | 1 request/chu kỳ (1 butterfly) |
> | Tốc độ, lane 32 bit (lai / rút gọn riêng) | 1/12, 1/12, 1/6 / 1/4, 1/4, 1/2 | 1/3 / 1 |
>
> Phần cấp lõi (gói root và xung đột bank ở 03, dự báo chu kỳ của kiến trúc) **chưa** cập nhật theo thay đổi này.

Tài liệu này định nghĩa **khối tile thử**: đơn vị nhỏ nhất của lõi có thể viết RTL, kiểm chức năng và đo tài nguyên
riêng. Nó là nền cho thí nghiệm quyết định giả thuyết 2 của [kiến trúc v1](../../../docs/architecture_v1.md): rút gọn
Montgomery 32 bit trên mảng nhân có rẻ hơn bộ Montgomery 32 bit riêng hay không. Thí nghiệm đã chạy và cho kết quả âm,
nên thiết kế v1 là biến thể rút gọn riêng (mục 5.2). Từ lần 6, tile chỉ có một lane NTT 32 bit, dùng cho mọi q; đo lại
trên một lane, giả thuyết 2 đạt, và từ lần 7 thiết kế v1 là biến thể trên mảng (mục 5.1).

## 1. Khối tile thử gồm gì

| Phần | Trong lõi đầy đủ | Trong khối tile thử |
|---|---|---|
| 4 bộ nhân 16×16 và cây cộng của tile | Có, 16 bản | 1 bản |
| Chọn toán hạng vào bộ nhân (dữ liệu, root, T_thấp, q′, m, q) | Có | Có |
| Thanh ghi giữ T, toán hạng chờ, metadata | Có | Có |
| Bộ cộng "phần cao + hạng bù + 1 bit" | Phần của ngân hàng dùng chung | Phần ứng với một butterfly |
| Cộng/trừ modulo, trừ q có điều kiện, chia đôi modulo | Phần của ngân hàng dùng chung | Phần ứng với một butterfly |
| Ghép cặp hệ số cho CT/GS, đặt kết quả về bộ nhớ | Mạng bank → tile và đường ghi | **Không**; testbench cấp toán hạng đã xếp |
| Ghép tích giữa các tile (FFT 64/128 bit), ghép số phức 3 tích | Có | **Không**; tile chỉ xuất tích thô 32×32 |
| Bộ nhớ, bảng root, bộ điều khiển lệnh | Có | **Không**; testbench cấp trực tiếp |

Mọi phép tính hoàn tất trong một tile thì khối tile thử phải tính đủ đến kết quả cuối:
- butterfly và phép nhân modulo của NTT, mọi q lẻ từ 3 đến dưới 2³¹;
- tích FFT 32 bit đã làm tròn.

Phép tính cần nhiều tile (FFT 64 và 128 bit) thì khối chỉ xuất tích thô 32×32 của phần mình.

## 2. Tín hiệu

Một miền clock, reset đồng bộ mức cao. Tên tín hiệu là gợi ý; được đổi tên nếu ghi rõ ánh xạ trong manifest triển
khai.

| Tín hiệu | Hướng | Bit | Ý nghĩa |
|---|---|---:|---|
| `clk`, `rst` | vào | 1 | Clock; reset đồng bộ |
| `en` | vào | 1 | **Cho phép chung.** `en = 0`: không nhận request, không phát kết quả, các cổng ra giữ nguyên (mục 6) |
| `idle` | ra | 1 | 1 khi không còn phép nào đang chạy trong khối |
| `cfg_we` | vào | 1 | Ghi thanh ghi hằng số (mục 3) |
| `cfg_slot` | vào | 1 | Ô hằng số được ghi: q, q′ vào ô 0 hoặc ô 1 (mục 3) |
| `cfg_q` | vào | 32 | Modulus q |
| `cfg_qinv` | vào | 32 | q′ = −q⁻¹ mod 2³² |
| `cfg_floor` | vào | 1 | Tích FFT 32 bit: 0 = làm tròn nửa-lên, 1 = cắt bớt |
| `cfg_halve` | vào | 1 | Butterfly GS: 1 = chia đôi modulo nhánh tổng |
| `req_valid`, `req_ready` | vào / ra | 1 | Bắt tay request; nhận khi `en & req_valid & req_ready` ở cạnh clock |
| `req_mode` | vào | 3 | Chế độ (mục 4) |
| `req_dir` | vào | 1 | NTT: 0 = CT (xuôi), 1 = GS (ngược) |
| `req_slot` | vào | 1 | Ô hằng số (q, q′) dùng cho request NTT này; được đổi giữa các request liên tiếp |
| `req_sign` | vào | 2 | Tích thô: bit 0 = a có dấu, bit 1 = b có dấu |
| `req_data` | vào | 64 | 2 ô 32 bit: d0 ở `[31:0]`, d1 ở `[63:32]` |
| `req_root` | vào | 32 | Ô r0 |
| `req_tag` | vào | 8 | Nhãn, trả lại nguyên vẹn cùng kết quả |
| `rsp_valid` | ra | 1 | Có kết quả; chỉ lên khi `en = 1` |
| `rsp_data` | ra | 65 | z0 ở `[31:0]`, z1 ở `[63:32]`; bit 64 chỉ dùng ở chế độ 0 |
| `rsp_tag` | ra | 8 | Nhãn của request tương ứng |

Không có `rsp_ready`. Khi phía sau chưa nhận được kết quả, bộ điều khiển hạ `en` cho cả khối; đây là cách dừng mà mô
hình chu kỳ đã kiểm (dừng chung, kết quả đúng thứ tự, chỉ mất đúng phần chu kỳ bị dừng).

Mỗi ô là một số 32 bit, kể cả khi q nhỏ (khi đó các bit cao bằng 0 vì giá trị < q). Ô không dùng ở đầu vào phải bằng 0;
ô không dùng ở kết quả phải bằng 0.

**Tín hiệu bắt tay chỉ quyết định bit hợp lệ.** Toán hạng phải được chọn theo chế độ và trạng thái khe đã chốt, không
theo `req_valid & req_ready`. Bản nháp vi phạm điều này mất 17% Fmax (ghi chú bản nháp mục 7).

## 3. Thanh ghi hằng số

- Các trường `cfg_*` được chốt vào thanh ghi khi `cfg_we = 1`, `en = 1` và `idle = 1`. `cfg_q`, `cfg_qinv` vào ô
  `cfg_slot`; `cfg_floor`, `cfg_halve` là chung cho cả hai ô.
- **Hai ô modulus.** Mỗi request NTT dùng q, q′ của ô `req_slot`, với mọi q. Ô không được ghi giữ giá trị cũ.
- Bộ điều khiển chỉ được ghi khi `idle = 1`. Ghi lúc đang chạy là lỗi của bộ điều khiển; khối không bắt buộc phát hiện.
- Sau reset thanh ghi bằng 0; phải ghi trước khi gửi request NTT.
- Hai biến thể rút gọn có cùng thanh ghi này. Hằng số **không** đi kèm từng request, để kích thước thanh ghi pipeline
  của hai biến thể không bị lệch vì hằng số.
- Trong lõi, mỗi tile có thanh ghi riêng. Các tile khác nhau được phép giữ q khác nhau cùng lúc, và mỗi tile giữ tối đa
  hai q; đó là cách lõi chạy nhiều prime trong một lệnh ([03 mục 6](03_bo_nho.md)).

## 4. Chế độ và phép tính

### 4.1 Ký hiệu

- `floor` làm tròn về −∞. `wrap_W(x)`: lấy x mod 2^W rồi hiểu theo bù hai W bit.
- R = 2³² với mọi q. (Trước lần 6, q < 2¹⁶ dùng R = 2¹⁶; phần mềm viết cho R = 2¹⁶ phải đổi hằng số, xem
  [01](01_so_hoc_kernel.md).)
- `Mont(a, b) = a · b · R⁻¹ mod q`, kết quả trong [0, q).
- `d0, d1` là các ô của `req_data`, `r0` là `req_root`, `z0, z1` là các ô của `rsp_data`.

### 4.2 Bảng chế độ

| `req_mode` | Chế độ | Dùng cho |
|---:|---|---|
| 0 | Tích thô 32×32 | Phần của tile trong FFT 64 / 128 bit |
| 1 | Tích FFT 32 bit đã làm tròn | FFT 32 bit |
| 2 | Một phép nhân modulo | Đưa vào miền Montgomery, nhân từng điểm, chuẩn hóa cuối NTT ngược |
| 4 | Một butterfly NTT | Mọi tầng của NTT xuôi và ngược |
| 3, 5–7 | Dự trữ | Không được gửi |

Chế độ của các request liên tiếp phải giống nhau. Chỉ đổi chế độ, hướng hoặc `req_sign` khi `idle = 1`; `req_slot`
được đổi ở mọi request. Bộ điều khiển
bảo đảm điều này; khối có thể giữ `req_ready = 0` cho đến khi rảnh nếu thấy chế độ đổi.

### 4.3 Chế độ 0 — tích thô 32×32

```text
a = d0 (có dấu nếu req_sign[0]), b = d1 (có dấu nếu req_sign[1])
z = a · b chính xác, bù hai 65 bit, đặt ở rsp_data[64:0]
```

65 bit vì tích hai số không dấu 32 bit có thể vượt 2⁶³. Không làm tròn, không cắt.

### 4.4 Chế độ 1 — tích FFT 32 bit

```text
a = d0, b = d1, cả hai có dấu 32 bit (Q16.16)
c = 2^15 nếu cfg_floor = 0 (nửa-lên, đúng quy tắc của bản chuẩn), c = 0 nếu cfg_floor = 1
z0 = wrap_32( floor((a·b + c) / 2^16) );  rsp_data[64:32] = 0
```

Viết theo dạng phần cứng: `z0 = P[47:16] + (cfg_floor ? 0 : P[15])` lấy 32 bit thấp, với P là tích đầy đủ. Đây là
cùng bộ cộng "phần cao + hạng bù + 1 bit" mà NTT dùng.

### 4.5 Phép nhân modulo và butterfly

**Miền giá trị hợp lệ:**
- q lẻ.
- 3 ≤ q < 2³¹. Cả hai biến thể đều hỗ trợ toàn miền này.
- Mọi hệ số và root nằm trong [0, q).

Ngoài miền này, khối không cam kết kết quả.

```text
Mont(a, b):  T = a·b;  m = (T mod R)·q′ mod R;  u = (T + m·q) / R;  kết quả = u − q nếu u ≥ q, ngược lại u
CT(x, y, w):  t = Mont(y, w);  trả (x + t mod q,  x − t mod q)
GS(x, y, w):  s = x + y mod q;  d = x − y mod q
              trả (cfg_halve ? s·2⁻¹ mod q : s,  Mont(d, w))
s·2⁻¹ mod q = (s + (s lẻ ? q : 0)) / 2        // q lẻ
```

- Với q < R, u < 2q, nên **một** lần trừ q là đủ. Thanh ghi u cần 32 bit (vì q < 2³¹).
- Khi q² < 2³² (mọi q < 2¹⁶), T < R, nên trường hợp T_thấp = 0 mà T ≠ 0 không xảy ra; trường hợp đó chỉ kiểm được với q
  lớn ([11](11_kiem_thu_tile.md)).
- Chia đôi modulo chỉ áp dụng cho **nhánh tổng** của GS. Hệ số 1/2 của nhánh hiệu nằm sẵn trong root (bảng igm của
  NTRUGen). Đây không phải phép chia đôi của FFT 64 bit NTRUGen: FFT chia đôi cả hai nhánh trước phép nhân, theo
  kiểu số có dấu, và việc đó nằm ở phần chuẩn bị toán hạng cấp lõi, không thuộc khối tile.

### 4.6 Chế độ 2 và 4 — NTT

| Chế độ | Phép tính |
|---|---|
| 2 | `z0 = Mont(d0, r0)`; `z1 = 0`. Không dùng `d1`, `req_dir`, `cfg_halve` |
| 4, CT | `(z0, z1) = CT(d0, d1, r0)` |
| 4, GS | `(z0, z1) = GS(d0, d1, r0)` |

Mỗi request là đúng một butterfly, nên vị trí toán hạng và kết quả không đổi theo chiều hay theo tầng. Việc chọn hai
hệ số của butterfly và root của nó, rồi ghi hai kết quả về đúng chỗ, thuộc phần cấp lõi. Không còn giá trị trung gian
nào giữ trong tile giữa hai tầng.

Phép tính trên từng butterfly giống hệt các nhịp cũ, nên NTT đầy đủ vẫn khớp `mp_NTT` / `mp_iNTT` của NTRUGen nếu bộ
điều khiển phát đúng các cặp. [model/ntrugen_mp31.py](../../../model/ntrugen_mp31.py) đã chạy lại với lịch một tầng
(`tile_request`, mỗi tầng phát butterfly theo thứ tự ngẫu nhiên) và khớp.

## 5. Hai biến thể rút gọn

Hai biến thể **phải** có cùng giao diện, cùng thanh ghi hằng số và cùng kết quả trên miền hợp lệ, ở **mọi** chế độ
0, 1, 2, 4. Chỉ khác cách tính phần rút gọn, độ trễ và tốc độ NTT. Chọn biến thể bằng một tham số RTL lúc tổng hợp. Mọi
phần còn lại phải là cùng một mã RTL.

(Mục 5.0 cũ, lane 16 bit rút gọn trên ba bộ nhân, bỏ ở lần 6 cùng với lane 16 bit.)

### 5.1 Biến thể trên mảng: rút gọn trên mảng nhân (thiết kế v1 từ lần 7; bác bỏ ở lần 4 khi còn hai lane)

Theo mục 5.3 của kiến trúc v1. Mỗi phép nhân modulo đi qua 4 bộ nhân của tile ba lượt:

| Lượt | Bộ nhân |
|---|---|
| T = a·b | 4 bộ nhân |
| m = T_thấp · q′ mod R (chỉ cần nửa thấp) | 3 bộ nhân |
| m·q (chỉ cần nửa cao) | 4 bộ nhân |

Phép rút gọn hoàn tất ở bộ cộng dùng chung: `u = T_cao + (m·q)_cao + [T_thấp ≠ 0]`, rồi trừ q nếu u ≥ q.
- `[T_thấp ≠ 0]` là bit nhớ của `T_thấp + (m·q)_thấp`. Hai số này cộng lại bằng 0 mod R, nên không cần cộng phần thấp,
  chỉ cần cổng OR trên T_thấp.
- **Không được** bỏ qua lượt nào theo giá trị dữ liệu (ví dụ khi T_thấp = 0): lịch chạy không được phụ thuộc giá trị.

Không có bộ nhân nào ngoài 4 bộ nhân của tile.

### 5.2 Rút gọn riêng (bản đối chứng; là thiết kế v1 từ lần 4 đến lần 7)

- **1 bộ Montgomery 32 bit tổng quát**, lấy q và q′ từ thanh ghi hằng số, dùng cho mọi q. Hai phép nhân
  m = T_thấp·q′ mod 2³² và m·q viết bằng phép nhân hành vi; Vivado tự chọn DSP hay LUT, và báo cáo phải ghi rõ;
- 4 bộ nhân của tile chỉ tính T (và tích FFT); không quay vòng toán hạng.

Bản đối chứng này thay cho "64 bộ rút gọn của lõi cũ" trong giả thuyết 2, vì lõi cũ không chạy được 8380417 hay prime
nạp lúc chạy.

### 5.3 Điểm đo thêm (không phải biến thể của v1)

Chỉ để so sánh, không thuộc nghiệm thu (đều có lane 16 bit, nên chỉ còn là số đo đã ghi trước lần 6):
- **Bộ rút gọn hằng ở lane 16 bit** (thiết kế lai trước đây): một bộ nhân hằng cộng/dịch cho 3329/12289 sau bộ nhân 0;
  chỉ nhận hai modulus đó; lane 32 bit như mục 5.1.
- **Rút gọn riêng cho cả hai lane**: lane 16 bit như điểm trên, lane 32 bit như mục 5.2.
- **Hai lane** (lần 3–5): lane 16 bit rút gọn trên ba bộ nhân (1 request/chu kỳ, R = 2¹⁶), lane 32 bit như mục 5.2.
  RTL lưu ở [plan_history](../../../docs/plan_history/before_one_lane_2026-10-31/hdl/tile_thu.sv).

## 6. Luồng dữ liệu và thời gian

- **Đúng thứ tự:** kết quả ra theo đúng thứ tự request được nhận, mỗi request đúng một kết quả, `rsp_tag` bằng
  `req_tag`.
- **Dừng chung** (quan sát từ cổng): khi `en = 0`, khối không nhận request, `rsp_valid = 0`, và `rsp_data`, `rsp_tag`,
  `idle` giữ nguyên. Một chuỗi request cho ra cùng chuỗi kết quả bất kể `en` bị hạ ở những chu kỳ nào.
- Trạng thái bên trong **được phép chạy thêm tối đa một chu kỳ** sau khi `en` xuống, nếu các điều kiện trên vẫn giữ (sửa
  31/10/2026; trước đó yêu cầu mọi thanh ghi đứng yên ngay). Cách này cho phép `en` tới đường dữ liệu qua một thanh ghi
  rồi tỏa ra tại chỗ, vì trong lõi `en` phải tới cả 16 tile. Khi đó mỗi đợt dừng mất thêm một chu kỳ, và `req_ready` có
  thể bằng 0 trong chu kỳ đầu sau khi `en` lên lại.
- **Trong lõi, `en` phải lấy trực tiếp từ một thanh ghi** (bộ điều khiển quyết định dừng sớm một chu kỳ). Đo 16 tile cho
  thấy khi đó Vivado tự đưa `en` lên bộ đệm toàn cục và vẫn đạt 3,0 ns, không cần thanh ghi `en` trong tile (ghi chú bản
  nháp mục 14).
- **Độ trễ cố định:** số chu kỳ có `en = 1`, tính từ lúc nhận request đến lúc phát kết quả, chỉ phụ thuộc chế độ và
  biến thể; không phụ thuộc giá trị dữ liệu hay q. Nếu trạng thái bên trong chạy thêm một chu kỳ sau khi `en` xuống (mục
  trên), mỗi đợt dừng xảy ra khi phép đang chạy cộng thêm tối đa một chu kỳ. Manifest triển khai phải công bố độ trễ cho
  từng chế độ khi khối chạy liên tục (không dừng, request liên tiếp).
- **Lịch phát:** người triển khai tự chọn. Lịch đã được mô hình kiểm là: ưu tiên lượt của phép cũ hơn, phép mới chỉ
  lấp bộ nhân còn trống ([model/mont_on_array_tile.py](../../../model/mont_on_array_tile.py)).
- **Tốc độ bền vững tối thiểu**, đo khi `req_valid` luôn bằng 1, `en` luôn bằng 1, ít nhất 1 000 request cùng chế độ.
  Tốc độ = số request nhận / số chu kỳ từ request đầu đến request cuối. Phải đạt ít nhất 98% con số dưới đây:

| Chế độ | Trên mảng, v1 (request/chu kỳ) | Rút gọn riêng (request/chu kỳ) |
|---|---:|---:|
| 0, 1 | 1 | 1 |
| 2, 4 (mọi q) | 1/3 | 1 |

Con số của biến thể trên mảng suy từ số lượt bộ nhân: một phép nhân modulo chiếm cả tile 3 chu kỳ, và mỗi request ở chế
độ 2 hay 4 có đúng một phép nhân modulo.

## 7. Reset

Sau `rst`, không còn phép nào đang chạy: `rsp_valid = 0`, `idle = 1`, thanh ghi hằng số bằng 0. Request đang chạy
lúc reset bị hủy, không phát kết quả.

## 8. Đo trên FPGA

Mục đích: số liệu cho giả thuyết 2 ở cấp một tile, trước khi làm cả lõi.

1. **Vỏ đo** `tile_thu_top`: thanh ghi ở mọi đầu vào và đầu ra, để đường I/O không quyết định timing. Tham số chọn
   biến thể. Hai biến thể dùng cùng vỏ.
2. **Vivado**, cùng phiên bản cho mọi lần đo. Linh kiện `xczu7ev-ffvc1156-2-e`. Tổng hợp `out_of_context`, rồi
   `opt_design`, `place_design`, `route_design` với cài đặt mặc định. Ràng buộc clock 3,0 ns cho cả hai biến thể.
   Tham khảo cách viết của [fpga/zcu106/synth.tcl](../../../fpga/zcu106/synth.tcl).
3. **Không** gọi primitive của Xilinx; DSP và RAM do Vivado tự suy ra.
4. **Báo cáo sau route**, riêng từng loại, không cộng gộp: LUT, FF, DSP, BRAM/URAM (mong đợi 0), WNS. Fmax =
   1000 / (3,0 − WNS) MHz. Khi WNS ≥ 0, ghi "≥ 333 MHz": đó chỉ là cận dưới. Ghi thêm LUT và FF của riêng khối tile
   (không tính thanh ghi của vỏ đo) từ báo cáo phân cấp; con số dùng cho giả thuyết 2 vẫn là số của cả vỏ đo.
5. **So sánh:**

| Đạt khi | Bác bỏ khi |
|---|---|
| DSP (trên mảng) ≤ DSP (rút gọn riêng) − 4; LUT (trên mảng) ≤ 1,05 × LUT (rút gọn riêng); Fmax giảm ≤ 10% | DSP giảm < 2, hoặc LUT tăng > 10% |

6. Ghi thêm: FF chênh lệch giữa hai biến thể, và độ trễ đã công bố của hai biến thể.

Kết quả âm vẫn là kết quả: báo cáo như vậy, và khi đó lõi dùng bộ Montgomery riêng. **Đã xảy ra** (31/10/2026, RTL
nghiệm thu, khi còn hai lane): xem đầu tài liệu. Số đo của một lane 32 bit (lần 6) ở
[hdl/tile/MANIFEST.md](../../../hdl/tile/MANIFEST.md).

## 9. Phần người triển khai tự chọn

Được đổi nếu giữ nguyên mục 2–7:
- số tầng pipeline, vị trí thanh ghi;
- đưa `en` tới đường dữ liệu qua một thanh ghi (mục 6);
- cách cộng trong cây của tile;
- cách mã hóa trạng thái;
- lịch phát lượt;
- tên tín hiệu.

Manifest triển khai phải ghi:
- biến thể;
- độ trễ từng chế độ;
- phiên bản Vivado;
- các thay đổi so với gợi ý.
