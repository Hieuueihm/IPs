# Lõi kernel tự điều khiển — chốt ở mức mô phỏng

## Phạm vi chốt hiện tại

Theo yêu cầu hiện tại, dừng triển khai ZCU106 và dùng mô phỏng RTL để chốt
đường số học, bộ nhớ và chức năng kernel. Không cần bitstream, block design
hoàn chỉnh hoặc timing vật lý để hoàn thành bước này. Các file FPGA đã tạo
được giữ lại cho giai đoạn sau; lỗi tool không phải điều kiện chặn chốt mô phỏng.

Chốt baseline: mảng nhân dùng chung với cơ chế ghép FFT rộng, butterfly NTT
một/hai tầng, ROM twiddle và RAM chia bank hiện tại. Chứng cứ bên dưới xác nhận
baseline chạy đúng trên tập kiểm tra. Số tile, packing FFT hẹp, dung lượng RAM
và mức chồng lấp controller vẫn có thể điều chỉnh; chưa có kết luận chúng tối ưu.
Đánh giá các lựa chọn song song tiếp theo, nếu cần, dùng cycle/kernel, mức sử
dụng lane và stall trong mô phỏng. Đã có [profiling baseline](kernel_parallelism_profile.md)
với 5.992 kernel/lượt, không pause và có pause. Kết quả xác định ưu tiên cấp dữ liệu
và chồng lấp controller; chưa phải phép sweep RTL số tile.

## Thay đổi so với adapter C/RTL trước

`hdl/core/flex_kernel_engine.sv` nhận nguyên mảng dữ liệu và một lệnh. RTL tự
đọc RAM, lấy twiddle, điều khiển mảng nhân dùng chung, thực hiện 3M/add/sub,
ghi butterfly và chuẩn hóa. Host không tạo frame số học, không tính các tầng
FFT/NTT và không sửa output. Đây vẫn là accelerator kernel; SHAKE, sampler,
điều phối ký/sinh khóa và codec còn trong C.

| Kernel | Đường thực thi |
|---|---|
| FFT / iFFT | Butterfly phức, 3 phép nhân thực, wrap theo W, chuẩn hóa iFFT |
| CMUL | Nhân phức từng cặp hệ số |
| SPLIT / MERGE | Địa chỉ và output đúng bố trí R8; SPLIT xuất f0 rồi f1 |
| NTT / iNTT | CT / GS, ghép hai tầng khi còn đủ tầng, bypass một tầng cuối |
| TOMONT / MODMUL | Montgomery qua cùng mảng; iNTT dùng đường này để chuẩn hóa |

FFT128 Q64.64 giữ rounding half-up của từng phép nhân 3M, wrap128 khi cộng/trừ,
và **wrap trước khi dịch** khi chia lũy thừa hai. Twiddle lấy nguyên bit từ C R8
commit `ad1e5bf7714d53230ad457364db8a46a1b459c94`. Không cắt precision ở đường này.
FFT32 Q16.16 và FFT64 Q32.32 là contract riêng, đã kiểm với oracle số nguyên;
không được suy ra là đủ chính xác cho ký FN-DSA.

## Bộ nhớ và điều khiển

Ba scratch store A/B/C, mỗi store có 64 bank 16 bit × 128 row, tổng dung lượng
dữ liệu 48 KiB. B giữ toán hạng thứ hai; C giữ kết quả SPLIT/MERGE để tránh
ghi đè input. Không reset toàn RAM: phần mềm phải nạp mọi input cần dùng.

FFT32/64/128 dùng lần lượt 2/4/8 word 16 bit mỗi thành phần thực. NTT dùng một
word. Map địa chỉ vật lý: `bank=(i&63)^((i>>2)&48)^((i>>4)&48)`, `row=i>>6`.
NTT cấp tối đa 64 hệ số mỗi lượt đọc; ROM gồm 16 bank bundle 48 bit. Địa chỉ
row, lựa chọn bundle và chuyển tầng hiện đã ở RTL.

Mảng số học giữ nguyên 16 tile/64 lá nhân 16×16 đã kiểm chứng. Đây là FSM
ưu tiên chức năng: FFT chạy lần lượt từng butterfly và chỉ dùng lane đầu ở
W32/64; chưa khai thác hết các lane hẹp. NTT chạy tối đa 16 cụm hai tầng mỗi
frame, có lượt đọc, phát lệnh, chờ và ghi riêng; **không tuyên bố toàn kernel II=1**.

Profile 0: q=12289, N=8..1024. Profile 1: q=3329, N=8..128 đầy đủ và N=256
incomplete 7 tầng; chuẩn hóa inverse theo 128 ở N256. Các N nhỏ là contract
transform với twiddle xác định, không phải tuyên bố đầy đủ ứng dụng ML-KEM.
Chưa có BASEMUL q3329, modulus 23/32 bit hay q tùy ý.
NTT yêu cầu input canonical `[0,q)`; controller không kiểm range từng hệ số.

## Chứng cứ chức năng

- [Kết quả kernel](../study/results/kernel_engine.json): 5.992 kernel,
  325.492 word, không sai khác; gồm 364 synthetic kernel từ C R8, 100 kernel
  FFT32/64 contract riêng, 56 kernel modular-oracle và 5.472 lời gọi ứng dụng.
- 184.709 chu kỳ pause trong lượt chạy cố định; giữ DONE, lệnh không hợp lệ
  và reset hủy transform đang chạy đều được kiểm tra.
- [C replay](../study/results/kernel_application.json): toàn bộ 5.472 lời gọi
  thay bằng **output toàn kernel từ RTL**. Bốn chữ ký N512/N1024, khóa, expanded
  key và thông điệp khớp byte baseline; verifier C gốc độc lập chấp nhận bốn
  chữ ký và từ chối thông điệp sai. Các kiểm tra live input của bridge vẫn bật.
  Sửa một word output RTL làm bridge phát hiện sai khác live input ở bước kế tiếp
  và dừng (exit 7), không tiếp tục bằng kết quả reference.
- [AXI-Lite](../study/results/kernel_axil.json): 15 kernel, 1.183 write và 757
  read; AW/W lệch nhau, B/R backpressure, byte strobes và địa chỉ sai đều được kiểm.

Nguồn, ROM, request và output được ghi SHA256. `--no-build` từ chối nếu RTL/ROM
khác manifest của mô hình đã biên dịch. Đây là số lượng workload cố định, không
phải chứng minh hình thức mọi input, chứng nhận chuẩn hay đánh giá side-channel.

## ZCU106 — lưu lại cho giai đoạn sau

Đích là `xczu7ev-ffvc1156-2-e`, theo board files ZCU106 của Vivado 2018.1 cài
trên máy và [tài liệu AMD UG936](https://www.amd.com/content/dam/xilinx/support/documents/sw_manuals/xilinx2022_2/ug936-vivado-tutorial-programming-debugging.pdf).

- `hdl/core/flex_kernel_axil.sv`: slave AXI4-Lite 32 bit.
- `fpga/zcu106/flex_kernel_mmio.h`: giao diện C nạp/chạy/đọc/ack/reset.
- `fpga/zcu106/synth.tcl`: thử tổng hợp OOC ở mục tiêu clock 100 MHz.
- `fpga/zcu106/create_project.tcl`: scaffold PS→AXI-Lite, base dự kiến
  `0xA0000000`, PL clock dự kiến 100 MHz. Chưa được coi là project triển khai thành công.

**Tình trạng phần cứng:** chưa có timing/utilization hoàn chỉnh hay bitstream.
Lượt synth đầu gặp `$sformatf` không được Vivado 2018.1 hỗ trợ; đã đổi sang
tên file ROM literal và xác nhận lại mô phỏng. Lượt synth sau đi qua elaboration
và RTL optimization nhưng dùng nhiều RAM, gây paging; đã dừng trước khi có report.
Tạo block design dừng tại `create_bd_cell -type module -reference
flex_kernel_axil accelerator`, chưa có chẩn đoán đủ để kết luận nguyên nhân.
Không tuyên bố lỗi thuật toán, lỗi chip hay lỗi phiên bản tool từ các hiện tượng này.

Log trong `study/build/kernel_vivado_console.log` và
`study/build/zcu106_project_console.log`. Chưa nạp board hoặc chạy đo trên board.
Số PPA Nangate45 ở các mục trước chỉ thuộc arithmetic island, **không áp dụng cho
lõi có RAM/controller mới**. Mục tiêu 100 MHz chưa được xác nhận.

## Register map AXI-Lite

| Offset | Nội dung |
|---|---|
| 0x00 | CFG: op[3:0], logN[7:4], width[9:8], profile[10] |
| 0x04 | W1P START bit0, ACK bit1, RESET bit2; pause bit8 khi ghi byte1 |
| 0x08 | Status: start_ready bit0, load_ready bit1, DONE bit2, error bit3, read_complete bit4, pending bit5 |
| 0x0c | Chu kỳ kernel, kể cả pause, không gồm nạp/đọc host |
| 0x10 / 0x14 | Index hệ số / store input A=0 hoặc B=1 |
| 0x18 | Command: 1=LOAD, 2=READ; command không hợp lệ trả SLVERR |
| 0x20..0x2c | Input 128 bit, limb 32 bit thấp trước |
| 0x30..0x3c | Output 128 bit, limb 32 bit thấp trước |

Op 0..8: FFT, IFFT, CMUL, SPLIT, MERGE, NTT, INTT, TOMONT, MODMUL.
Width 0/1/2: 32/64/128; NTT dùng low16. Host cấu hình, nạp input, START, đợi
DONE, phát READ và đợi read_complete cho từng hệ số, rồi ACK. ACK khi đang pause
bị từ chối. MMIO phải được map device/uncached; header có barrier ARM.

## Tái chạy

Từ thư mục gốc repo, dùng Python native với MSYS2 Verilator/GCC và Icarus:

```text
python -X utf8 scripts/generate_kernel_rom.py
python -X utf8 scripts/validate_kernel_engine.py --full
python -X utf8 scripts/validate_kernel_axil.py
python -X utf8 scripts/replay_kernel_application.py
```

C replay dùng các executable LP64 và capture pristine từ phép thử ứng dụng trước,
không sửa nguồn `third_party/r8`. Chưa tối ưu tốc độ bus, interleave butterfly,
packing nhiều FFT hẹp, routing vật lý hoặc constant-time của toàn accelerator.
