# A + CG: native NTRUGen, burst host và chồng lấp tầng

Bản riêng; không thay `hdl/`, spec, PLAN hoặc nguyên mẫu `experiments/a_cg`.
Top là `rtl/a_cg_fast.sv`. `build.py` sinh `rtl/tile_a.sv` từ production đã kiểm
SHA256; top và multiplier được giữ trực tiếp trong thư mục này.

## Contract được hỗ trợ

- FFT32/64/128 generic: contract spec 1.0, wrap, round-nearest từng tích 3M,
  inverse scale ở tầng cuối. FFT32/64 không tự được chọn thay FFT128 trong signer.
- `cfg_ntrugen=1`, `cfg_fft=1`, `cfg_fmt=1`: FFT64 native NTRUGen, root GM_TAB
  riêng, nhân cắt bớt và inverse signed rounded-half **cả hai nhánh trước nhân**
  ở mọi tầng. Không scale cuối. Không hợp lệ với format khác.
- NTT/INTT scalar32: q lẻ 3..2^31-1, N2..1024, hmin0..2 với hmin<logn,
  root Montgomery R=2^32. Inverse half nhánh tổng, root inverse đã nhân inv2.
  Native domain/order của thư viện ứng dụng cần adapter đúng; modulus phải có
  root cần thiết. Phần mềm cung cấp qinv và root tương ứng.

NTRUGen half được viết lại theo đồng nhất thức chính xác:

```text
wrap64(wrap64(A+1) + B) = wrap64(A+B+1)
wrap64(wrap64(A+1) - B) = wrap64(A-B+1)
```

Mạch chỉ tăng A một lần theo limb, dùng lại cộng/trừ GS, rồi dịch phải có dấu
một bit. Thanh ghi operand hiện có giữ limb thấp; một delay register đưa nó tới
đúng lúc nhận limb cao. Không thay thứ tự rounding hay bỏ carry/overflow wrap.

Engine là đơn vị nội bộ được core lập lịch. Mode/q chỉ cấu hình sau reset tile;
không giữ bộ đếm idle và admission controller tổng quát ở từng engine. Các
assertion mô phỏng vẫn theo dõi số BF sống, giới hạn 8/4/2 buffer tương ứng.
Không dùng engine riêng này như production tile có request tùy ý/backpressure.

## Lịch và host

Descriptor 46 bit/tầng: mask16, root base9, root period mask5, gap16.
Generator kiểm cổng RAM, RAW/WAR/WAW và pha microprogram chung; chọn lịch rào nếu
overlap không có lợi. Gap là microcode tin cậy của host, không phải đầu vào tùy ý
được phần cứng tự chứng minh an toàn. Tầng đọc và tầng ghi có context riêng;
mask/request/scale và mask chương trình nhân được pipeline tới đúng nơi dùng.

Host load/read line128 ở thứ tự tự nhiên. Bốn word dùng 1/2/4 lượt bank ở
FFT32/64/128, có xử lý riêng transform rất nhỏ. Load phase0 ngay cạnh handshake;
read có thể nhận line kế khi trả line trước. `read_rsp_valid` không có ready:
caller phải nhận mọi response. Request giữ stable khi valid chưa được nhận.

Root write là một word32 tới `root_dest[15:0]` tại cùng row; chỉ multicast các
bit-pattern trùng nhau. Commit sau khi nạp đúng context. Cổng cfg/root/descriptor,
start và data dùng bởi một host theo từng nhóm thao tác, không phát đồng thời
những thao tác thay context. Root/descriptor chỉ ghi khi idle; start sau khi mọi
load hoàn tất. Đổi contract/q/chiều/precision/N phải nạp đúng context trước start.

Chưa có AXI/DMA, hỗ trợ NTT packed16 hoặc nhiều bảng root resident. Root cache,
host, 32 bank data, descriptor và 16 engine đều nằm trong top synth.

## Chạy lại

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File experiments/a_cg_fast/run.ps1 -FourState -Synthesize
python -X utf8 experiments/a_cg_fast/application.py
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_fast/audit.tcl
python -X utf8 experiments/a_cg_fast/report.py
```

Dùng Vivado2018.1, Icarus và Verilator đã cài trên máy; application gọi GCC Linux
LP64 trong WSL. Driver C++ xuất output thật từ simulator ra file, sau đó C R8
kiểm live input và tiêu thụ output ấy. Chỉ FFT/IFFT/NTT/INTT được thay; các kernel
khác và phần NTRUGen keygen còn ở C. Không fallback về C cho bốn transform đã thay.
Verifier độc lập và so sánh artifact xác nhận chức năng trên workload đã kiểm;
chưa phải toàn bộ PQC được làm bằng RTL hoặc chứng nhận tuân thủ chuẩn.

Fixture còn dùng dump C `study/build/ntrugen_mp31/dump.bin` từ
`scripts/build_spec2_kernel_assets.py`. Co-sim tái dùng capture/objects đã kiểm hash
ở `study/build/pqc_application`; nếu thiếu, tạo lại bằng helper C LP64
`scripts/pqc_c_bridge.py capture` trong WSL. Không cần chạy RTL cũ để tạo capture C.

Kết quả, vector, log và checkpoint ở `study/build/a_cg_fast`. Báo cáo cuối ở
`study/results/a_cg_fast.md`; các thử nghiệm tổng hợp cũ nằm ở `attempt1` để đối chiếu.
