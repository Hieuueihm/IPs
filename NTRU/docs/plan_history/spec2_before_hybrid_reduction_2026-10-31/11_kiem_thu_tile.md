# 11 — Kiểm thử cấp tile

Các case dưới đây kiểm **khối tile thử** theo [hợp đồng cấp tile](10_hop_dong_tile.md). Mỗi case phải chạy trên **cả
hai biến thể** rút gọn, trừ chỗ ghi "chỉ trên mảng". Trạng thái của mỗi case là một trong: chưa chạy, đạt, không đạt,
không áp dụng. "Chưa chạy" không bao giờ được tính là đạt.

## 1. Vector chuẩn

Sinh bằng [scripts/build_spec2_tile_vectors.py](../../../scripts/build_spec2_tile_vectors.py) (seed cố định
20261030). Giá trị mong đợi chỉ tính bằng phép nhân số nguyên và phép toán modulo thuần túy, **không** dùng mô hình
tích 16×16, vì đó chính là thứ cần kiểm. Hash SHA-256 của từng file ở [assets/tile/manifest.json](assets/tile/manifest.json).

| File | Số ca | Nội dung | Biến thể |
|---|---:|---|---|
| `raw32.txt` | 2 320 | Chế độ 0, bốn tổ hợp dấu, giá trị biên (0, 1, −1, −2³¹, 2³¹ − 1, 2³² − 1, …) và ngẫu nhiên | Cả hai |
| `fft32.txt` | 1 842 | Chế độ 1, nửa-lên và cắt bớt, 264 ca đúng điểm giữa (16 bit thấp của tích = 0x8000) và lân cận ±1 | Cả hai |
| `ntt16_pqc.txt` | 2 814 | Chế độ 2–4, lane 16 bit, q = 3329 và 12289 | Cả hai |
| `ntt16_q_khac.txt` | 3 864 | Chế độ 2–4, lane 16 bit, q = 3, 7681, 65521 | Chỉ trên mảng |
| `ntt32.txt` | 11 263 | Chế độ 2–4, lane 32 bit, q = 8380417; prime đầu, giữa và cuối của NTRUGen; 2³¹ − 1; 12289 đặt trong lane 32 bit | Cả hai |

Với mỗi q, vector NTT phủ đủ bảy tổ hợp:
- chế độ 2;
- chế độ 3 CT, chế độ 3 GS, chế độ 3 GS có chia đôi;
- chế độ 4 CT, chế độ 4 GS, chế độ 4 GS có chia đôi.

Mỗi giá trị đặc biệt (0, 1, 2, q − 1, q − 2, quanh q/2, các lũy thừa của 2) lần lượt nằm ở từng ô dữ liệu và từng ô
root. Các trường hợp góc của phép rút gọn:

| Trường hợp | Lane 16 bit | Lane 32 bit |
|---|---:|---:|
| Phép nhân modulo đã phủ | 20 988 | 35 398 |
| T là bội của R nhưng khác 0 (T_thấp = 0, bit `[T_thấp ≠ 0]` phải bằng 0) | 531 | 1 534 |
| T = 0 | 2 330 | 1 794 |

**Cách đọc file.** Mỗi dòng một ca, các trường hex cách nhau bằng dấu cách, dòng bắt đầu bằng `#` là chú thích. File
chỉ có ký tự ASCII, đọc được bằng `$fscanf(fd, "%h ...")`. Cột của file NTT là:

```text
q qinv lane32 mode dir halve d0 d1 d2 d3 r0 r1 r2 r3 z0 z1 z2 z3
```

Dòng được nhóm theo q rồi theo chế độ. Khi q, lane, chế độ, hướng hoặc cờ chia đôi đổi, testbench phải chờ
`idle = 1`, ghi thanh ghi hằng số (q, qinv, lane32, halve), rồi gửi tiếp. Nếu cột halve = 0 thì `cfg_halve = 0`.

Bộ vector này **thay cho** 16 102 vector của cụm NTT cũ khi kiểm khối tile thử, vì cụm cũ chỉ có lane 16 bit và cách
đóng gói khác.

**Kiểm chéo đã chạy:** [scripts/check_spec2_tile_vectors.py](../../../scripts/check_spec2_tile_vectors.py) chạy lại
toàn bộ 22 103 ca qua mô hình dạng phần cứng và cho khớp hết:
- tích cộng từ các tích con 16×16, nửa cao mang dấu;
- `P[47:16] + P[15]` cho FFT 32 bit;
- Montgomery ba lượt với `[T_thấp ≠ 0]`;
- chia đôi bằng cộng có điều kiện rồi dịch.

1 609 ca nhân modulo 32 bit khớp thêm mô hình đã đối chiếu với C của NTRUGen.

## 2. Các case kiểm thử

### Nhóm A — đúng số học

| Case | Cách làm | Đạt khi |
|---|---|---|
| **Tích thô 32×32** | Chạy toàn bộ `raw32.txt` | Mọi `rsp_data[64:0]` bằng cột product65, `rsp_data[127:65] = 0` |
| **Tích FFT 32 bit** | Chạy toàn bộ `fft32.txt`, đổi `cfg_floor` theo cột floor | Mọi `rsp_data[31:0]` đúng, phần còn lại bằng 0 |
| **NTT 16 bit, q chuẩn** | Chạy `ntt16_pqc.txt` | Mọi z0..z3 đúng, 16 bit cao của mỗi ô bằng 0 |
| **NTT 16 bit, q khác** (chỉ trên mảng) | Chạy `ntt16_q_khac.txt` | Như trên. Biến thể rút gọn riêng ghi "không áp dụng" |
| **NTT 32 bit** | Chạy `ntt32.txt` | Mọi z0..z3 đúng |
| **Ô không dùng** | Trong mọi ca trên | Ô kết quả không thuộc chế độ luôn bằng 0 |

### Nhóm B — luồng dữ liệu và thời gian

| Case | Cách làm | Đạt khi |
|---|---|---|
| **Đúng thứ tự và nhãn** | Gửi liên tiếp mọi vector của một file, `req_tag` tăng dần quay vòng | Kết quả ra đúng thứ tự gửi, đúng một kết quả mỗi request, `rsp_tag` đúng |
| **Dừng chung** | Như trên, hạ `en` ngẫu nhiên với xác suất 0,1 và 0,3; thêm các đợt hạ liên tục dài tới 64 chu kỳ | Chuỗi kết quả giống hệt khi không dừng; `rsp_valid = 0` mọi chu kỳ `en = 0`; đầu ra không đổi trong lúc `en = 0` |
| **Request thưa** | Hạ `req_valid` ngẫu nhiên (xác suất 0,5) | Kết quả đúng và đúng thứ tự |
| **Độ trễ cố định** | Với từng chế độ và lane, gửi liên tục không dừng | Mọi request có cùng độ trễ, bằng con số đã công bố trong manifest |
| **Lịch không phụ thuộc dữ liệu** | Chạy cùng một chuỗi request hai lần: lần một dữ liệu và root đều bằng 0, lần hai ngẫu nhiên | Chuỗi `req_ready` và `rsp_valid` theo chu kỳ giống hệt nhau |
| **Tốc độ bền vững** | Với từng dòng của bảng tốc độ ở mục 6 của hợp đồng: ≥ 1 000 request, `req_valid = 1`, `en = 1` | Tốc độ ≥ 98% con số của biến thể đang kiểm |
| **Đổi chế độ và hằng số** | Chuỗi: NTT 16 bit q = 12289 → tích FFT 32 bit → NTT 32 bit q = 8380417 → tích thô → NTT 32 bit prime NTRUGen có chia đôi → NTT 16 bit q = 3329. Mỗi lần đổi chờ `idle = 1` rồi ghi hằng số | Mọi kết quả đúng; không có kết quả lẫn giữa hai đoạn |
| **Ghi hằng số chỉ khi rảnh** | Giữ `cfg_we = 1` lúc `idle = 0` (chỉ để kiểm) | Hằng số không bị đổi giữa chừng; chỉ chốt khi `idle = 1`; kết quả của các request đang chạy vẫn đúng |
| **Reset giữa chừng** | Bật `rst` khi còn request đang chạy, ở nhiều thời điểm khác nhau | Sau reset: không còn kết quả của request cũ, `idle = 1`, hằng số bằng 0; ghi lại hằng số rồi chạy tiếp thì kết quả đúng |

### Nhóm C — testbench phải bắt được lỗi

Testbench chỉ đáng tin nếu nó bắt được lỗi cố ý cài vào. Mỗi lỗi chạy một lần, và phải ra **không đạt**:

| Lỗi cài vào | Phải bắt được nhờ |
|---|---|
| Sửa một giá trị mong đợi trong bản sao của file vector | So sánh kết quả |
| Bỏ bit `[T_thấp ≠ 0]` trong RTL (một `define` chỉ dùng để kiểm) | Các ca T_thấp ≠ 0 |
| Luôn cộng bit `[T_thấp ≠ 0]` = 1 | Các ca T là bội của R |
| Bỏ bước trừ q cuối | Các ca có u ≥ q |
| Chia đôi cả khi `cfg_halve = 0` | Các ca GS không chia đôi |
| Đảo r1 và r2 ở chế độ 3 | Các ca nhịp hai tầng |
| Đổi chỗ hai kết quả liền nhau | Case đúng thứ tự và nhãn |

### Nhóm D — đo trên FPGA

Theo mục 8 của [hợp đồng cấp tile](10_hop_dong_tile.md#8-đo-trên-fpga). Chỉ đo sau khi nhóm A, B, C đạt ở cả hai biến
thể.

| Số liệu (sau route) | Trên mảng | Rút gọn riêng | Tỉ lệ |
|---|---:|---:|---:|
| LUT | | | |
| FF | | | |
| DSP | | | |
| BRAM / URAM | | | |
| WNS ở 3,0 ns; Fmax | | | |
| Độ trễ đã công bố (từng chế độ) | | | |

## 3. Bảng kết quả

Điền sau mỗi lần chạy. Ghi kèm phiên bản RTL, phiên bản trình mô phỏng và hash của manifest vector.

| Case | Trên mảng | Rút gọn riêng |
|---|---|---|
| Tích thô 32×32 | chưa chạy | chưa chạy |
| Tích FFT 32 bit | chưa chạy | chưa chạy |
| NTT 16 bit, q chuẩn | chưa chạy | chưa chạy |
| NTT 16 bit, q khác | chưa chạy | không áp dụng |
| NTT 32 bit | chưa chạy | chưa chạy |
| Ô không dùng | chưa chạy | chưa chạy |
| Đúng thứ tự và nhãn | chưa chạy | chưa chạy |
| Dừng chung | chưa chạy | chưa chạy |
| Request thưa | chưa chạy | chưa chạy |
| Độ trễ cố định | chưa chạy | chưa chạy |
| Lịch không phụ thuộc dữ liệu | chưa chạy | chưa chạy |
| Tốc độ bền vững | chưa chạy | chưa chạy |
| Đổi chế độ và hằng số | chưa chạy | chưa chạy |
| Ghi hằng số chỉ khi rảnh | chưa chạy | chưa chạy |
| Reset giữa chừng | chưa chạy | chưa chạy |
| Bắt được lỗi cài vào (7 lỗi) | chưa chạy | chưa chạy |
| Đo trên FPGA | chưa chạy | chưa chạy |

## 4. Tái lập

Từ thư mục dự án:

```text
python scripts/build_spec2_tile_vectors.py    # sinh lại vector; hash phải giống manifest đã phát hành
python scripts/check_spec2_tile_vectors.py    # kiểm chéo vector với mô hình dạng phần cứng
```
