# Phân tích tile: leaf 32×32 và 17×17

> Tóm tắt: ở bộ nhớ 512 bit/chu kỳ, tile 2×2 leaf 16 bit đạt cùng throughput với tile 32×32
> nhưng tốn thêm 16–26% diện tích tổ hợp (tổng hợp generic) và gấp đôi FF. Chỉ có lợi cho NTT hẹp
> khi bộ nhớ ≥ 2 048 bit/chu kỳ. Chi tiết: mục 3 (model) và mục 7–8 (RTL + Yosys).

> PLAN mục 16, bước 3. Model: `model/tile_util.py` (chạy: `python model/tile_util.py`).
> Bảng đầy đủ: `study/results/tile_util.md`, dữ liệu: `study/results/tile_util.csv`.
> Đây là **mô hình giải tích độc lập công nghệ**, chưa phải kết quả tổng hợp.

## 1. Câu hỏi

Một tile có thực sự chuyển hiệu quả giữa nhiều phép nhân hẹp và một phép nhân rộng không,
khi phục vụ NTT 12/14/23/32 bit và FFT32/64/128?

## 2. Giả định

| Hạng mục | Giá trị |
|---|---|
| Mảng | 32 tile; tile ≈ một bộ nhân 32×32 tương đương |
| L32 | 1 leaf 32×32 **sign-select** (mỗi toán hạng chọn signed/unsigned), limb 32 bit |
| L17 | 2×2 leaf 17×17 **signed-only**, limb 16 bit (bit thêm để chứa limb unsigned) |
| Độ nhạy | L16 = 2×2 leaf 16×16 sign-select; L33 = 1 leaf 33×33 signed-only |
| FFT | 1 butterfly = 4 phép nhân thực W×W (twiddle cùng độ rộng); twiddle hẹp là dòng tùy chọn |
| NTT PQC | 1 butterfly = 1 tích q×q; reducer chuyên biệt không dùng tile |
| NTT RNS | Montgomery R = 2^32: 2 tích đầy đủ + 1 tích chỉ cần nửa thấp, đều chạy trên tile |
| Bộ nhớ | 512 bit đọc + 512 bit ghi mỗi chu kỳ; lane NTT 16 bit (12/14 bit) hoặc 32 bit |
| Diện tích | Proxy P² mỗi leaf; chưa tính cây gom, mux, logic chọn dấu, reducer |

Model tự kiểm tra: 20 800 phép tách limb (biên và ngẫu nhiên) tái tạo đúng tích chính xác,
kể cả tích nửa thấp của Montgomery, và mọi limb nằm trong miền toán hạng của leaf.

## 3. Kết quả chính (512 bit/chu kỳ)

| Phép | L32: leaf/BF | L32: hiệu suất bit | L17: leaf/BF | L17: hiệu suất bit | BF/chu kỳ (cả hai) | Giới hạn |
|---|---:|---:|---:|---:|---:|---|
| NTT 3329 (12b) | 1 | 14,1% | 1 | 49,8% | 16 | bộ nhớ |
| NTT 12289 (14b) | 1 | 19,1% | 1 | 67,8% | 16 | bộ nhớ |
| NTT 8380417 (23b) | 1 | 51,7% | 4 | 45,8% | 8 | bộ nhớ |
| NTT RNS 32b (Montgomery) | 3 | 83,9% | 11 | 81,0% | 8 | bộ nhớ |
| FFT32 | 4 | 100% | 16 | 88,6% | 4 | bộ nhớ |
| FFT64 | 16 | 100% | 64 | 88,6% | 2 | cả hai |
| FFT128 | 64 | 100% | 256 | 88,6% | 0,5 | tính toán |

Diện tích bộ nhân proxy: L32 = 32 768, L17 = 36 992 (**+12,9%**).
Throughput trên cùng diện tích của L17 thấp hơn L32 khoảng 11% ở mọi mode FFT.

## 4. Nhận xét

1. **Với bộ nhớ 512 bit, leaf nhỏ không đem lại throughput.** L32 và L17 đạt cùng số butterfly
   mỗi chu kỳ ở mọi phép. Mọi NTT và FFT32 bị giới hạn bởi bộ nhớ; FFT64 cân bằng; chỉ FFT128
   bị giới hạn bởi tính toán.
2. **Hiệu suất bit thấp không đồng nghĩa với mất throughput.** NTT 12/14 bit chỉ dùng 14–19% mỗi
   leaf 32×32, nhưng một nửa số tile vốn đã rảnh vì bộ nhớ chỉ cấp đủ 16 butterfly.
   Câu hỏi “tile chuyển mode có hiệu quả không” phải trả lời ở cấp hệ thống, không chỉ ở cấp leaf.
3. **Leaf signed-only tốn diện tích.** Bit thêm của 17×17 làm tăng 12,9% diện tích và kéo hiệu suất
   FFT xuống 88,6%. Leaf L16 sign-select cùng diện tích với L32, giữ 100% cho FFT và đạt 76,6%
   cho NTT 14 bit. Nếu dùng leaf nhỏ, nên chọn **sign-select** thay vì thêm bit (chi phí logic chọn
   dấu cần đo bằng tổng hợp).
4. **Leaf nhỏ làm cây gom lớn hơn.** Ở FFT128, mỗi tích thực cần 64 tích riêng với leaf 16/17 bit
   so với 16 với leaf 32 bit (proxy bit vào cây: 2 176 so với 1 024), và thêm một cấp nhóm (64).
5. **Leaf nhỏ chỉ có lợi khi bộ nhớ rộng hơn nhiều.** Với NTT 12/14 bit, L32 đạt trần 32 butterfly
   từ 1 024 bit/chu kỳ; L16/L17 chỉ vượt (64 butterfly) khi có 2 048 bit/chu kỳ. NTT 23 bit và FFT
   không khác nhau ở các mức đã xét. Montgomery: 11,6 so với 10,7 nhờ tích nửa thấp tiết kiệm hơn.
6. **Đòn bẩy lớn nhất cho FFT128 là twiddle hẹp**, không phải kích thước leaf: twiddle 64 bit đưa
   FFT128 từ 0,5 lên 1 butterfly/chu kỳ (chạm trần bộ nhớ), với điều kiện qua phân tích sai số.

## 5. Kết luận tạm thời

- Ở cấu hình cơ sở (512 bit), **tile 32×32 sign-select là đủ**; tách xuống 16 bit không tăng
  throughput mà tăng cây gom (và diện tích nếu dùng leaf signed-only).
- Kích thước leaf và băng thông bộ nhớ cho NTT là **một quyết định gắn với nhau**: chỉ nên chọn leaf
  16 bit nếu kiến trúc cấp được ≥ 2 048 bit/chu kỳ cho NTT hẹp.
- Đề xuất: giữ `L` là tham số RTL; L32 sign-select làm cơ sở, L16 sign-select làm điểm khảo sát
  “bộ nhớ rộng” trong bài.

## 6. Giới hạn của model giải tích

- Chưa tính: cây gom liên tile, reducer, twiddle traffic, xung đột bank, pipeline và drain giữa stage.
  Bộ nhớ giả định lịch truy cập hoàn hảo.
- Proxy diện tích P² bỏ qua khác biệt Booth/array và chi phí mux/ghép. Mục 7 thay proxy này
  bằng tổng hợp generic ở cấp tile.

## 7. Tổng hợp generic (Yosys)

### 7.1 RTL và kiểm chứng

| File | Nội dung |
|---|---|
| `hdl/mul_ss.v` | Leaf W×W sign-select. `IMPL="CORR"`: lõi unsigned + hạng hiệu chỉnh dấu; `IMPL="EXT"`: mở rộng toán hạng lên W+1 bit, nhân signed (= leaf signed-only) |
| `hdl/tile_l32.v` | Tile L32: một leaf 32×32, thanh ghi vào/ra |
| `hdl/tile_l16x4.v` | Tile 2×2 leaf 16×16: `fuse=0` bốn tích 16×16 độc lập, `fuse=1` một tích 32×32; chỉ 2 leaf cần mux toán hạng; `FUSE_EN=0` bỏ đường ghép |
| `hdl/bench/tile_bench.v` | Các top dùng cho tổng hợp, gồm baseline unsigned 32×32 |
| `sim/src/tb_tiles.v` | Testbench tự kiểm tra mọi cấu hình so với tích chính xác |
| `scripts/synth_tiles.py` | Chạy Yosys, xuất `study/results/tile_synth.{csv,md}` |

Mô phỏng (Icarus Verilog 14): **36 884 phép kiểm tra, 0 lỗi** (góc 32/16 bit × 4 chế độ dấu,
5 000 vector ngẫu nhiên mỗi loại). Phép thử đột biến (xóa hạng sa·sb·2^2W) cho 3 034 lỗi,
xác nhận testbench phát hiện được sai.

### 7.2 Kết quả

Yosys 0.70 (YoWASP), `synth -flatten` (± `-booth`), ánh xạ `abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX`.
GE là ước lượng NAND2-equivalent với trọng số xấp xỉ; độ sâu tính bằng số cell trên đường dài nhất
(Yosys ánh xạ bộ cộng kiểu ripple, nên chỉ dùng để so tương đối).

| Cấu hình | Array: GE tổ hợp | × u32 | Booth: GE tổ hợp | × u32 | FF | Độ sâu (array / booth) |
|---|---:|---:|---:|---:|---:|---|
| Baseline unsigned 32×32 | 9 374 | 1,00 | 7 684 | 1,00 | 128 | 126 / 129 |
| L32 sign-select (CORR) | 10 209 | 1,09 | 8 280 | 1,08 | 131 | 127 / 132 |
| L32 mở rộng (= 33×33 signed-only) | 11 106 | 1,18 | 7 992 | 1,04 | 131 | 109 / 128 |
| 2×2 L16 sign-select, chỉ tách | 10 738 | 1,15 | 9 377 | 1,22 | 268 | 64 / 68 |
| 2×2 L16 sign-select, tách + ghép | 11 825 | 1,26 | 10 531 | 1,37 | 269 | 127 / 135 |
| 2×2 L17 signed-only, tách + ghép | 12 962 | 1,38 | 10 063 | 1,31 | 269 | 127 / 136 |

### 7.3 Nhận xét từ tổng hợp

1. **Tile linh hoạt đắt hơn tile cố định 16–26% diện tích tổ hợp.** So sánh cấu hình tốt nhất
   của mỗi bên trong cùng flow: array 1,16× (L16 CORR so với L32 CORR), Booth 1,26×
   (L17 EXT so với L32 EXT). Số FF gấp đôi vì mỗi lane cần thanh ghi toán hạng và kết quả riêng.
2. **Riêng phần ghép (cây cộng + mux) tốn thêm 10–12%** so với tile chỉ tách.
3. **Cách xử lý dấu tốt nhất phụ thuộc kiểu bộ nhân.** Với array, sign-select (CORR) rẻ hơn mở rộng
   (L32: 1,09 so với 1,18); với Booth thì ngược lại (1,08 so với 1,04, và tile L17 rẻ hơn tile L16 CORR).
   Proxy P² ở mục 3 (L17 đắt hơn 12,9%) chỉ đúng hướng với bộ nhân array.
   → Giữ `IMPL` là tham số; chọn theo luồng hiện thực, không cố định trong kiến trúc.
4. **Không có lợi về tần số ở chế độ ghép.** Đường ghép sâu bằng L32 (127 so với 127); chỉ chế độ
   tách thuần có đường ngắn bằng một nửa (64), nhưng một thiết kế một xung nhịp không tận dụng được.

### 7.4 Kết hợp với model giải tích

| Bộ nhớ | NTT 12/14 bit: throughput L16 / L32 | FFT: throughput L16 / L32 | Diện tích tile L16 / L32 (Booth) | Hiệu quả trên diện tích (NTT hẹp / FFT) |
|---|---:|---:|---:|---|
| 512 bit/chu kỳ | 1,0 | 1,0 | 1,26 | 0,79 / 0,79 |
| 2 048 bit/chu kỳ | 2,0 | 1,0 | 1,26 | 1,59 / 0,79 |

(Diện tích: tile 2×2 tốt nhất so với L32 tốt nhất trong flow Booth; chưa tính FF.)

## 8. Kết luận (cập nhật sau tổng hợp)

- **Câu trả lời cho câu hỏi tile:** tile 2×2 L16 chuyển đúng giữa 4 tích hẹp và 1 tích rộng
  (kiểm chứng bit-exact), nhưng **không chuyển “hiệu quả” ở cấu hình cơ sở**: tốn thêm 16–26%
  diện tích tổ hợp và gấp đôi FF, trong khi bộ nhớ 512 bit không cấp đủ dữ liệu cho phần song song thêm.
- Tile linh hoạt chỉ có lợi khi NTT hẹp được cấp ≥ 2 048 bit/chu kỳ, và khi đó FFT trả giá ~21%
  hiệu quả trên diện tích. Đây là một **điểm đánh đổi cần báo cáo**, không phải lợi ích mặc định.
- Đề xuất cho kiến trúc:
  - Cơ sở: **tile L32**, `IMPL` chọn theo luồng (CORR cho array, EXT cho Booth).
  - Ghép phân cấp đặt ở **cấp liên tile** (32 → 64 → 128 bit), nơi FFT64/128 thực sự cần.
  - Tile 2×2 L16 giữ như **điểm khảo sát “bộ nhớ rộng”**, gắn với thiết kế bộ nhớ cấp ≥ 2 048 bit cho NTT.
- Giới hạn: tổng hợp generic, trọng số GE xấp xỉ, bộ cộng ripple; chưa có thư viện cell thật
  hay FPGA. Bước sau: lặp lại với thư viện mở (ví dụ Nangate45/OpenROAD) và trên FPGA đích.
