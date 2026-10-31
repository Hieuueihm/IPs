# 10 — Hợp đồng cấp tile

Tài liệu này định nghĩa **khối tile thử**: đơn vị nhỏ nhất của lõi có thể viết RTL, kiểm chức năng và đo tài nguyên
riêng. Nó là nền cho thí nghiệm quyết định giả thuyết 2 của [kiến trúc v1](../../../docs/architecture_v1.md): rút gọn
Montgomery trên mảng nhân có tốn ít tài nguyên hơn bộ rút gọn riêng hay không.

## 1. Khối tile thử gồm gì

| Phần | Trong lõi đầy đủ | Trong khối tile thử |
|---|---|---|
| 4 bộ nhân 16×16 và cây cộng của tile | Có, 16 bản | 1 bản |
| Chọn toán hạng vào bộ nhân (dữ liệu, root, T_thấp, q′, m, q) | Có | Có |
| Thanh ghi giữ T, toán hạng chờ, metadata | Có | Có |
| Bộ cộng "phần cao + hạng bù + 1 bit" | Phần của ngân hàng dùng chung | Phần ứng với 4 hệ số của tile |
| Cộng/trừ modulo, trừ q có điều kiện, chia đôi modulo | Phần của ngân hàng dùng chung | Phần ứng với 4 hệ số của tile |
| Ghép tích giữa các tile (FFT 64/128 bit), ghép số phức 3 tích | Có | **Không**; tile chỉ xuất tích thô 32×32 |
| Bộ nhớ, bảng root, bộ điều khiển lệnh | Có | **Không**; testbench cấp trực tiếp |

Mọi phép tính hoàn tất trong một tile thì khối tile thử phải tính đủ đến kết quả cuối:
- NTT 16 bit và 32 bit;
- tích FFT 32 bit đã làm tròn.

Phép tính cần nhiều tile (FFT 64 và 128 bit) thì khối chỉ xuất tích thô 32×32 của phần mình.

## 2. Tín hiệu

Một miền clock, reset đồng bộ mức cao. Tên tín hiệu là gợi ý; được đổi tên nếu ghi rõ ánh xạ trong manifest triển
khai.

| Tín hiệu | Hướng | Bit | Ý nghĩa |
|---|---|---:|---|
| `clk`, `rst` | vào | 1 | Clock; reset đồng bộ |
| `en` | vào | 1 | **Cho phép chung.** `en = 0`: toàn khối đứng yên, mọi thanh ghi giữ nguyên, không nhận request, không phát kết quả |
| `idle` | ra | 1 | 1 khi không còn phép nào đang chạy trong khối |
| `cfg_we` | vào | 1 | Ghi thanh ghi hằng số (mục 3) |
| `cfg_lane32` | vào | 1 | 0 = lane 16 bit (R = 2¹⁶); 1 = lane 32 bit (R = 2³²) |
| `cfg_q` | vào | 32 | Modulus q |
| `cfg_qinv` | vào | 32 | q′ = −q⁻¹ mod R (lane 16 bit chỉ dùng 16 bit thấp) |
| `cfg_floor` | vào | 1 | Tích FFT 32 bit: 0 = làm tròn nửa-lên, 1 = cắt bớt |
| `cfg_halve` | vào | 1 | Butterfly GS: 1 = chia đôi modulo nhánh tổng |
| `req_valid`, `req_ready` | vào / ra | 1 | Bắt tay request; nhận khi `en & req_valid & req_ready` ở cạnh clock |
| `req_mode` | vào | 3 | Chế độ (mục 4) |
| `req_dir` | vào | 1 | NTT: 0 = CT (xuôi), 1 = GS (ngược) |
| `req_sign` | vào | 2 | Tích thô: bit 0 = a có dấu, bit 1 = b có dấu |
| `req_data` | vào | 128 | 4 ô 32 bit: ô i ở `[32i+31 : 32i]` |
| `req_root` | vào | 128 | 4 ô 32 bit: root theo chế độ |
| `req_tag` | vào | 8 | Nhãn, trả lại nguyên vẹn cùng kết quả |
| `rsp_valid` | ra | 1 | Có kết quả; chỉ lên khi `en = 1` |
| `rsp_data` | ra | 128 | Kết quả, cùng cách xếp ô |
| `rsp_tag` | ra | 8 | Nhãn của request tương ứng |

Không có `rsp_ready`. Khi phía sau chưa nhận được kết quả, bộ điều khiển hạ `en` cho cả khối; đây là cách dừng mà mô
hình chu kỳ đã kiểm (dừng chung, kết quả đúng thứ tự, chỉ mất đúng phần chu kỳ bị dừng).

Ở lane 16 bit, mỗi ô dùng 16 bit thấp. 16 bit cao của ô đầu vào phải bằng 0; 16 bit cao của ô kết quả phải bằng 0.
Ô không dùng ở đầu vào phải bằng 0; ô không dùng ở kết quả phải bằng 0.

## 3. Thanh ghi hằng số

- Các trường `cfg_*` được chốt vào thanh ghi khi `cfg_we = 1`, `en = 1` và `idle = 1`.
- Bộ điều khiển chỉ được ghi khi `idle = 1`. Ghi lúc đang chạy là lỗi của bộ điều khiển; khối không bắt buộc phát hiện.
- Sau reset thanh ghi bằng 0; phải ghi trước khi gửi request NTT.
- Hai biến thể rút gọn có cùng thanh ghi này. Hằng số **không** đi kèm từng request, để kích thước thanh ghi pipeline
  của hai biến thể không bị lệch vì hằng số.
- Trong lõi, mỗi tile có thanh ghi riêng. Các tile khác nhau được phép giữ q khác nhau cùng lúc; đó là cách lõi chạy
  nhiều prime trong một lệnh ([03 mục 6](03_bo_nho.md)).

## 4. Chế độ và phép tính

### 4.1 Ký hiệu

- `floor` làm tròn về −∞. `wrap_W(x)`: lấy x mod 2^W rồi hiểu theo bù hai W bit.
- R = 2¹⁶ khi `cfg_lane32 = 0`, R = 2³² khi `cfg_lane32 = 1`.
- `Mont(a, b) = a · b · R⁻¹ mod q`, kết quả trong [0, q).
- `d0..d3` là các ô của `req_data`, `r0..r3` là các ô của `req_root`, `z0..z3` là các ô của `rsp_data`.

### 4.2 Bảng chế độ

| `req_mode` | Chế độ | Dùng cho |
|---:|---|---|
| 0 | Tích thô 32×32 | Phần của tile trong FFT 64 / 128 bit |
| 1 | Tích FFT 32 bit đã làm tròn | FFT 32 bit |
| 2 | Bốn phép nhân modulo độc lập | Đưa vào miền Montgomery, nhân từng điểm, chuẩn hóa cuối NTT ngược |
| 3 | Nhịp NTT hai tầng | Lượt hai tầng của NTT |
| 4 | Nhịp NTT một tầng | Lượt một tầng cuối khi số tầng lẻ |
| 5–7 | Dự trữ | Không được gửi |

Chế độ của các request liên tiếp phải giống nhau. Chỉ đổi chế độ, hướng hoặc `req_sign` khi `idle = 1`. Bộ điều khiển
bảo đảm điều này; khối có thể giữ `req_ready = 0` cho đến khi rảnh nếu thấy chế độ đổi.

### 4.3 Chế độ 0 — tích thô 32×32

```text
a = d0 (có dấu nếu req_sign[0]), b = d1 (có dấu nếu req_sign[1])
z = a · b chính xác, bù hai 65 bit, đặt ở rsp_data[64:0]; rsp_data[127:65] = 0
```

65 bit vì tích hai số không dấu 32 bit có thể vượt 2⁶³. Không làm tròn, không cắt.

### 4.4 Chế độ 1 — tích FFT 32 bit

```text
a = d0, b = d1, cả hai có dấu 32 bit (Q16.16)
c = 2^15 nếu cfg_floor = 0 (nửa-lên, đúng quy tắc của bản chuẩn), c = 0 nếu cfg_floor = 1
z0 = wrap_32( floor((a·b + c) / 2^16) )
```

Viết theo dạng phần cứng: `z0 = P[47:16] + (cfg_floor ? 0 : P[15])` lấy 32 bit thấp, với P là tích đầy đủ. Đây là
cùng bộ cộng "phần cao + hạng bù + 1 bit" mà NTT dùng.

### 4.5 Phép nhân modulo và butterfly

**Miền giá trị hợp lệ:**
- q lẻ.
- Lane 16 bit: 3 ≤ q < 2¹⁶. Biến thể rút gọn riêng chỉ hỗ trợ q = 3329 và q = 12289.
- Lane 32 bit: 3 ≤ q < 2³¹. Cả hai biến thể đều hỗ trợ toàn miền này.
- Mọi hệ số và root nằm trong [0, q).

Ngoài miền này, khối không cam kết kết quả.

```text
Mont(a, b):  T = a·b;  m = (T mod R)·q′ mod R;  u = (T + m·q) / R;  kết quả = u − q nếu u ≥ q, ngược lại u
CT(x, y, w):  t = Mont(y, w);  trả (x + t mod q,  x − t mod q)
GS(x, y, w):  s = x + y mod q;  d = x − y mod q
              trả (cfg_halve ? s·2⁻¹ mod q : s,  Mont(d, w))
s·2⁻¹ mod q = (s + (s lẻ ? q : 0)) / 2        // q lẻ
```

- Với q < R, u < 2q, nên **một** lần trừ q là đủ. Thanh ghi u cần 17 bit ở lane 16 bit và 32 bit ở lane 32 bit (vì
  q < 2³¹).
- Chia đôi modulo chỉ áp dụng cho **nhánh tổng** của GS. Hệ số 1/2 của nhánh hiệu nằm sẵn trong root (bảng igm của
  NTRUGen). Đây không phải phép chia đôi của FFT 64 bit NTRUGen: FFT chia đôi cả hai nhánh trước phép nhân, theo
  kiểu số có dấu, và việc đó nằm ở phần chuẩn bị toán hạng cấp lõi, không thuộc khối tile.

### 4.6 Chế độ 2, 3, 4 — NTT

| Chế độ | Root dùng | Phép tính |
|---|---|---|
| 2 | r0..r3 | `z_i = Mont(d_i, r_i)`, i = 0..3. Không dùng `req_dir`, `cfg_halve` |
| 3, CT | r0 = chung, r1 = w0, r2 = w1 | `(y0, y2) = CT(d0, d2, r0)`; `(y1, y3) = CT(d1, d3, r0)`; rồi `(z0, z1) = CT(y0, y1, r1)`; `(z2, z3) = CT(y2, y3, r2)` |
| 3, GS | r0 = chung, r1 = w0, r2 = w1 | `(y0, y1) = GS(d0, d1, r1)`; `(y2, y3) = GS(d2, d3, r2)`; rồi `(z0, z2) = GS(y0, y2, r0)`; `(z1, z3) = GS(y1, y3, r0)` |
| 4, CT | r0 = w0, r1 = w1 | `(z0, z2) = CT(d0, d2, r0)`; `(z1, z3) = CT(d1, d3, r1)` |
| 4, GS | r0 = w0, r1 = w1 | `(z0, z1) = GS(d0, d1, r0)`; `(z2, z3) = GS(d2, d3, r1)` |

Cách xếp hệ số và root này giống mục 01.8 của bản 1.0 (gói root `[chung, w0, w1]`). Cách lấy 4 hệ số từ bộ nhớ thuộc
phần cấp lõi. Đã kiểm khớp từng bit với NTRUGen: [model/ntrugen_mp31.py](../../../model/ntrugen_mp31.py) chạy đúng các
nhịp này và cho kết quả bằng `mp_NTT` / `mp_iNTT` trên cả 323 prime.

Giá trị trung gian y không được ghi ra ngoài; hai tầng trao đổi trực tiếp trong khối.

## 5. Hai biến thể rút gọn

Hai biến thể **phải** có cùng giao diện, cùng thanh ghi hằng số và cùng kết quả trên miền hợp lệ chung, ở **mọi** chế
độ 0–4. Chỉ khác cách tính phần rút gọn, độ trễ và tốc độ. Chọn biến thể bằng một tham số RTL lúc tổng hợp.

### 5.1 Rút gọn trên mảng nhân

Theo mục 5.3 của kiến trúc v1. Mỗi phép nhân modulo đi qua 4 bộ nhân của tile ba lượt:

| Lượt | Lane 16 bit | Lane 32 bit |
|---|---|---|
| T = a·b | 1 bộ nhân | 4 bộ nhân |
| m = T_thấp · q′ mod R (chỉ cần nửa thấp) | 1 bộ nhân | 3 bộ nhân |
| m·q (chỉ cần nửa cao) | 1 bộ nhân | 4 bộ nhân |

Phép rút gọn hoàn tất ở bộ cộng dùng chung: `u = T_cao + (m·q)_cao + [T_thấp ≠ 0]`, rồi trừ q nếu u ≥ q.
- `[T_thấp ≠ 0]` là bit nhớ của `T_thấp + (m·q)_thấp`. Hai số này cộng lại bằng 0 mod R, nên không cần cộng phần thấp,
  chỉ cần cổng OR trên T_thấp.
- **Không được** bỏ qua lượt nào theo giá trị dữ liệu (ví dụ khi T_thấp = 0): lịch chạy không được phụ thuộc giá trị.

Không có bộ nhân nào ngoài 4 bộ nhân của tile.

### 5.2 Rút gọn riêng (bản đối chứng)

Bản đối chứng làm đủ cùng tập modulus của lõi với ít tài nguyên nhất:
- **4 bộ rút gọn 16 bit hằng số**, mỗi bộ chọn giữa q = 3329 và q = 12289 (nhân hằng q′ và q bằng cộng/dịch, như lõi
  hiện tại). Lane 16 bit với q khác hai giá trị này không được hỗ trợ.
- **1 bộ Montgomery 32 bit tổng quát**, lấy q và q′ từ thanh ghi hằng số. Hai phép nhân m = T_thấp·q′ mod 2³² và m·q
  viết bằng phép nhân hành vi; Vivado tự chọn DSP hay LUT, và báo cáo phải ghi rõ.
- 4 bộ nhân của tile chỉ tính T (và tích FFT); không quay vòng toán hạng.

Bản đối chứng này thay cho "64 bộ rút gọn của lõi cũ" trong giả thuyết 2, vì lõi cũ không chạy được 8380417 hay prime
nạp lúc chạy.

## 6. Luồng dữ liệu và thời gian

- **Đúng thứ tự:** kết quả ra theo đúng thứ tự request được nhận, mỗi request đúng một kết quả, `rsp_tag` bằng
  `req_tag`.
- **Dừng chung:** khi `en = 0`, không thanh ghi nào đổi giá trị. Một chuỗi request cho ra cùng chuỗi kết quả bất kể
  `en` bị hạ ở những chu kỳ nào.
- **Độ trễ cố định:** số chu kỳ có `en = 1`, tính từ lúc nhận request đến lúc phát kết quả, chỉ phụ thuộc chế độ, lane
  và biến thể; không phụ thuộc giá trị dữ liệu. Manifest triển khai phải công bố độ trễ này cho từng chế độ khi khối
  chạy liên tục (không dừng, request liên tiếp).
- **Lịch phát:** người triển khai tự chọn. Lịch đã được mô hình kiểm là: ưu tiên lượt của phép cũ hơn, phép mới chỉ
  lấp bộ nhân còn trống ([model/mont_on_array_tile.py](../../../model/mont_on_array_tile.py)).
- **Tốc độ bền vững tối thiểu**, đo khi `req_valid` luôn bằng 1, `en` luôn bằng 1, ít nhất 1 000 request cùng chế độ.
  Tốc độ = số request nhận / số chu kỳ từ request đầu đến request cuối. Phải đạt ít nhất 98% con số dưới đây:

| Chế độ | Lane | Trên mảng (request/chu kỳ) | Rút gọn riêng (request/chu kỳ) |
|---|---|---:|---:|
| 0, 1 | — | 1 | 1 |
| 2 | 16 bit | 1/3 | 1 |
| 3 | 16 bit | 1/3 | 1 |
| 4 | 16 bit | 2/3 | 1 |
| 2 | 32 bit | 1/12 | 1/4 |
| 3 | 32 bit | 1/12 | 1/4 |
| 4 | 32 bit | 1/6 | 1/2 |

Các con số trên mảng suy từ số lượt bộ nhân: một phép nhân modulo cần 3 lượt bộ nhân ở lane 16 bit và 3 chu kỳ của cả
tile ở lane 32 bit; mỗi request ở chế độ 2 và 3 có 4 phép nhân modulo, ở chế độ 4 có 2. Chúng trùng với mô hình chu kỳ
(0,333 và 0,083 nhịp/chu kỳ).

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
   1000 / (3,0 − WNS) MHz.
5. **So sánh:**

| Đạt khi | Bác bỏ khi |
|---|---|
| LUT (trên mảng) ≤ 0,90 × LUT (rút gọn riêng); DSP (trên mảng) ≤ DSP (rút gọn riêng); Fmax giảm ≤ 10% | LUT giảm < 5% |

6. Ghi thêm: FF chênh lệch so với dự báo của mô hình (khoảng 180 bit/tile ở lane 16 bit), và độ trễ đã công bố của hai
   biến thể.

Kết quả âm vẫn là kết quả: báo cáo như vậy, và khi đó lõi giữ bộ rút gọn riêng.

## 9. Phần người triển khai tự chọn

Được đổi nếu giữ nguyên mục 2–7:
- số tầng pipeline, vị trí thanh ghi;
- cách cộng trong cây của tile;
- cách mã hóa trạng thái;
- lịch phát lượt;
- tên tín hiệu.

Manifest triển khai phải ghi:
- biến thể;
- độ trễ từng chế độ;
- phiên bản Vivado;
- các thay đổi so với gợi ý.
