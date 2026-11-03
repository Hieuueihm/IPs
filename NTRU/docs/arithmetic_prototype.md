# Prototype RTL nhanh: bank số học F16 và R32

Ngày: 25/10/2026. RTL nghiên cứu độc lập công nghệ; chưa phải cả bộ biến đổi.

## 1. Câu hỏi cần trả lời

Giữ cùng một năng lực nhân rộng, chi phí của việc tách leaf 16 bit thành các lane
NTT độc lập có được bù bởi throughput NTT hẹp không? Đo cả operand mux, cây ghép,
rounding, reducer, ALU và register, không chỉ đếm multiplier.

Prototype dùng **một bank** đủ tạo một real product 128×128 mỗi lượt:

| Top | Leaf vật lý | Lane NTT12289 | Vai trò |
|---|---|---:|---|
| proto_r32 | 16 × 32×32 | 16 | Baseline |
| proto_f16_common | 64 × 16×16 | 16 | So cùng capacity đầu ra NTT |
| proto_f16_mid | 64 × 16×16 | 32 | Điểm giữa: 2× lane so với R32 |
| proto_f16_wide | 64 × 16×16 | 64 | Khảo sát lợi ích narrow lanes |

Tổng proxy diện tích nhân đều là 16 384 (g²), không phải diện tích tổng hợp bằng nhau.
Mảng trong ARCHITECTURE có hai bank tương đương; không dùng số lane của prototype
này thay trực tiếp vào bảng của toàn mảng.

Bản mid dùng lại cây ghép phân cấp hiện có; mỗi nhóm bốn leaf 16×16 đã có tap
cho FFT32. Vòng này chỉ thay `NTT_LANES=32`: trang bị 32 reducer và đường hiệu chỉnh
mod q, giữ 64 leaf để phục vụ FFT. Không time-multiplex reducer và không đổi
rounding/truncation. Số lane NTT là tham số khi tổng hợp; FFT width/domain vẫn đổi
theo transaction. Bật ít lane trên phần cứng wide có sẵn không tự giảm area như
việc tổng hợp riêng bản mid. Chưa có mạng nối tile mới trong vòng thử này.

## 2. Phần RTL đã có

[flex_arith_bank.sv](../hdl/proto/flex_arith_bank.sv), dùng lại [mul_ss.v](../hdl/mul_ss.v).

- mode=0: nhiều phép Mont(B,wR), q=12289, R=2^16, input canonical.
- mode=1/2/3: nhân thực fixed-point W32/W64/W128, F=W/2, signed, half-up và wrap.
- Leaf được dùng lại giữa mọi mode; không tạo hai mảng nhân riêng cho FFT/NTT.
- Operand selector chọn limb, signedness và cách grouping.
- Cây interleaved-index có fixed shift và tap 32/64/128; chỉ bỏ hạng FFT không ảnh hưởng output.
  Leaf tại vị trí bị mask FFT vẫn có thể dùng như một lane NTT độc lập.
- Rounding đặt ở tap, giống contract R8 cho W128; W32/64 theo contract tự định nghĩa.
- Montgomery12289: m = low16(T*12287), S=T+m*12289, chia 2^16 và một correction.
  Hai tích hằng dùng shift-add; T của NTT không bị cắt theo quy tắc product FFT.
- **Một ALU dual-output dùng chung:** các đoạn 16 bit nối carry thành lane 16/32/64/128
  theo mode. FFT giữ wrap; NTT thêm correction mod q sau cùng raw add/sub đó.
  Biên carry bắt buộc được ngắt tĩnh; các đoạn chỉ phục vụ NTT hẹp không nối carry
  thành một đường 1024 bit. Kết quả trước khi ngắt rõ ràng được giữ tại
  [JSON đối chiếu](../study/results/arith_proto_before_alu_break.json).
- Có thanh ghi input và output, valid/mode đi kèm; nhận transaction mỗi cycle.
  Không có ready/stall. Đổi mode được kiểm ở mức bank vì mỗi transaction mang mode riêng.
  Điều này không đổi quy tắc drain context của toàn transform core.

Vào là x, y và z; ra product p, z+p và z−p theo arithmetic của mode.
Ba bus vào rộng tối đa 1024 bit để chứa cấu hình NTT64; bit không dùng được constant/prune.
Đây là bus nội bộ, không phải yêu cầu chân I/O vật lý của FPGA.

## 3. Trần issue và băng thông

| Mode | Cả bốn cấu hình, real products/cycle |
|---|---:|
| FFT32 | 16 |
| FFT64 | 4 |
| FFT128 | 1 |

Đây là real products. Nhân phức 3M cần ba real products, thêm pre-add/recombination
và buffer; chưa có complex issue controller trong RTL này.

Peak NTT16 là 16/16/32/64 lane mỗi cycle, nếu mọi khối và nguồn dữ liệu theo kịp.
Mỗi butterfly NTT đọc A và B (32 data bits), đọc root riêng (16 twiddle bits),
ghi hai output (32 data bits). Áp giới hạn data mỗi hướng cho **một bank prototype**:

| Data bit/cycle mỗi hướng | R32 | F16 common | F16 mid | F16 wide |
|---:|---:|---:|---:|---:|
| 512 | 16 | 16 | 16 | 16 |
| 1024 | 16 | 16 | 32 | 32 |
| 2048 | 16 | 16 | 32 | 64 |

Các số này chưa tính stall stage, RAM banking hoặc twiddle conflict.
Toàn mảng hai bank có điểm bão hòa khác; không suy rộng 4× của bank thành 4× FN-DSA.

## 4. Kiểm chứng

[Driver](../scripts/prototype_arith.py), [testbench](../sim/src/tb_flex_arith_bank.sv).

- 1 335 giao dịch, mỗi giao dịch kiểm cả bốn top, gồm boundary và random.
- Đổi liên tục mode giữa các giao dịch, chèn valid bubbles; kiểm valid/mode và đúng thứ tự output.
- So product output và cả hai nhánh ALU; FFT32/64 so contract số nguyên,
  NTT12289 so oracle Montgomery/canonical chính xác. Kiểm đủ 32 lane của bản mid,
  các bit output ngoài lane hoạt động phải bằng zero; các top còn lại kiểm tương tự.
- Lấy input/output CMUL từ vector C R8 đã ghi, cấp ba tích thực qua RTL W128,
  recombine 3M trong test driver và so với C: **189 complex products, 0 sai khác**.

Recombination 3M trong test không có nghĩa RTL đã có đầy đủ butterfly 3M.
FFT/iFFT đầy đủ mới được kiểm ở golden model trong [báo cáo R8](../study/results/r8_differential.md).
Testbench của bank không thay kiểm chứng toàn pipeline/transform sau này.

## 5. Tổng hợp và đọc kết quả

[Báo cáo](../study/results/arith_proto.md), [JSON](../study/results/arith_proto.json).

Kết quả vòng đo sau khi ngắt carry tĩnh:

| Top | Tổng GE xấp xỉ, gồm FF | So với R32 | Độ dài đường gate | Lane NTT |
|---|---:|---:|---:|---:|
| R32 | 246 933 | 1,000× | 179 | 16 |
| F16 common | 264 393 | 1,071× | 193 | 16 |
| F16 mid | 285 459 | 1,156× | 190 | 32 |
| F16 wide | 353 393 | 1,431× | 193 | 64 |

Ở cùng clock giả định và băng thông đủ, F16 wide có 4× capacity NTT với 1,431×
total GE, tức khoảng 2,80× capacity/GE. Đây chưa phải speedup đo trên phần cứng.
Với 512 bit/cycle data mỗi hướng, cả bốn đều chỉ cấp được 16 butterfly NTT/cycle;
ở điểm đó các phương án F16 không có lợi throughput trong model này.

**Điểm giữa đáng chọn để phát triển tiếp:** F16 mid tăng 15,6% total GE so với R32,
cho 2× lane NTT tại cùng clock giả định, tương đương 1,73× peak capacity/GE.
Ở 1024 data bit/cycle mỗi hướng, mid và wide cùng bị giới hạn ở 32 BF/cycle,
nhưng mid dùng ít hơn khoảng 19,2% total GE. Mid có 3 078 FF bit, bằng R32/common,
vì các bus FFT sẵn có đã đủ chứa 32 lane NTT; wide tăng lên 6 118 FF bit.
Depth 190 của mid là số gate, không chứng minh clock bằng R32 (179).

Giữ R32 làm baseline gọn cho băng thông hẹp/FFT; ưu tiên F16 mid cho điểm thiết kế
1024 bit/cycle của một bank; F16 wide còn hợp lý khi khai thác được trên 32 lane
và cấp đủ data/twiddle. F16 common chưa bù được overhead bằng throughput.
Cả bốn giữ cùng capacity FFT, nên không dùng kết quả này để tuyên bố FFT nhanh hơn.
Chưa chốt leaf cho toàn core từ một flow generic hoặc suy ra lợi ích energy.

Các top được tổng hợp lại cùng vòng thêm mid. Số GE baseline thay đổi dưới 0,2%
so với vòng trước; dùng bảng cùng vòng này để tính mọi tỷ lệ.

Flow generic: Yosys native 0.52, `synth -flatten -noabc`,
`abc -fast -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX`.
Chọn fast mapping cho vòng thử kiến trúc, không phải kết quả đã tối ưu PPA đầy đủ.
GE dùng trọng số xấp xỉ như study tile cũ; FF tách riêng rồi quy đổi 4,67 GE/bit
để tạo một chỉ số total GE. Không dùng số này làm diện tích silicon hay DSP/LUT FPGA.

`ltp -noff` cho độ dài đường logic theo cell, **không phải Fmax hoặc ns**.
Chưa có library, placement/routing, constraints clock hoặc đo công suất.
Không suy năng lượng từ số bit không hoạt động.

So R32 và F16 common để đánh giá overhead ở cùng 16 lane. F16 wide có năng lực
NTT đầu ra lớn hơn, nên đánh giá thêm throughput/area với điều kiện băng thông
thay vì chỉ kết luận từ area tuyệt đối. Cùng-clock peak throughput chưa phải
throughput thật nếu timing hai phương án khác nhau.

## 6. Chạy lại

~~~powershell
python -X utf8 scripts/prototype_arith.py
python -X utf8 scripts/prototype_arith.py --synth-only
~~~

Lệnh đầu dùng Icarus (`iverilog`, `vvp`). Lệnh sau chỉ reuse simulation nếu RTL/testbench
không thay đổi sau compile. Có thể dùng `--synth` để mô phỏng rồi tổng hợp trong một lần.
Native Yosys được ưu tiên. Vòng đo này dùng Yosys/ABC của Ubuntu giải nén local
vào `study/tools/yosys_native`, không cài system package. Bốn top được chạy qua pool
tối đa ba tiến trình tổng hợp đồng thời.
YoWASP local qua [yosys_local.py](../scripts/yosys_local.py) là phương án dự phòng,
nhưng chậm hơn; không trộn số đo giữa hai version/flow.

Lệnh native đã dùng, từ PowerShell:

~~~powershell
wsl --exec env LD_LIBRARY_PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/lib/x86_64-linux-gnu PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin:/usr/bin:/bin python3 -X utf8 /mnt/d/IPs/NTRU/scripts/prototype_arith.py --synth-only --yosys /mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin/yosys
~~~

Build/log/netlist ở `study/build/arith_proto`; kết quả chính ở `study/results`.
Không chạy lại keygen/sign hoặc build C R8 trong vòng thử RTL này.
