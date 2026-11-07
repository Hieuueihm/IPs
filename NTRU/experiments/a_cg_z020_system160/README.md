> **Baseline trước, đã được thay thế.** Người dùng đã nhận packed16 bốn leaf `a_cg_packed4_system160` (spec 3.1); xem [registry hiện hành](../BASELINE.md). Các kết quả và hướng dẫn bên dưới mô tả mốc cũ, giữ để đối chiếu.

# Hệ thống PS7–AXI–FFT/NTT cho Qiming

**Baseline hiện hành được người dùng chấp nhận ngày 2026-11-04: `a_cg_z020_system160`.** Nguồn chuẩn giữ tại thư mục này; không sao chép đè RTL cũ trong `hdl/`. [Danh mục/manifest baseline](../BASELINE.md), [contract 3.0](../../spec/FlexTransform/3.0/README.md). Phạm vi gồm host, bộ nhớ/root, AXI, clock và reset. Đã đạt sign-off STA sau P&R và audit clock thực. Xem kết quả đo bên dưới; chưa nạp hoặc đo trên board.

## Kết quả chốt (2026-11-04)

| Chỉ tiêu toàn hệ thống | Kết quả |
|---|---:|
| Clock AXI/lõi | **160 MHz**, chu kỳ 6,250 ns |
| Setup WNS / endpoint lỗi | **+0,038 ns / 0** |
| Hold WHS / endpoint lỗi | **+0,011 ns / 0** |
| Pulse-width slack / endpoint lỗi | **+1,995 ns / 0** |
| Endpoint được kiểm setup và hold | **77.432** |
| LUT, gồm LUTRAM | **31.242** |
| FF / DSP48 / RAMB18 | **31.186 / 64 / 48** |
| Routed / routable nets | **59.641 / 59.641**, 0 lỗi |
| DRC error / blackbox | **0 / 0** |
| Clock/reset | **1 PS7, 1 MMCM**, reset IP đã mô phỏng |

Ngân sách còn 3.758 LUT so với 35k. Phạm vi timing là toàn bộ thiết kế tích hợp PS7–AXI–lõi, không lọc register-to-register riêng lõi. Báo cáo có `All user specified timing constraints are met.` Không còn lỗi hold I/O −1,237 ns của mô hình OOC trước đó.

`check_timing`: 0 pin không clock, 0 endpoint thiếu ràng buộc, 0 port thiếu/thiếu một phần input/output delay, 0 pin nhiều clock, 0 generated clock mất nguồn, 0 vòng tổ hợp. CDC: `All paths are Safely Timed.`

DRC còn 64 cảnh báo DPIP-1 khuyến nghị dùng input pipeline nội bộ DSP; không có DRC Error/Critical Warning. Exceptions report có một false-path của vendor với endpoint không tồn tại, nên không loại đường timing nào; không thêm exception để che datapath. Sau audit clock PS, checkpoint chốt là **`route/signoff.dcp`**, không lấy `route/routed.dcp` trước audit làm số cuối.

## Thiết kế cụ thể

```text
PS reference 33.333333 MHz
    PS7 FCLK0 100 MHz -> MMCM 160 MHz -> AXI interconnect + AXI-Lite + core
    PS7 M_AXI_GP0 -> AXI interconnect/converter -> a_cg_axil -> a_cg_fast
    PS7 FCLK_RESET0_N + MMCM LOCKED -> proc_sys_reset -> AXI/core reset
```

Target `xc7z020clg400-2`. PS dùng OCM/JTAG, DDR và các ngoại vi carrier tắt; không thêm GPIO/PL data pins. `M_AXI_GP0_ACLK`, AXI interconnect và lõi đều dùng cùng clock 160 MHz từ MMCM. CPU có thể nạp mọi root, descriptor, modulus, dữ liệu và đọc mọi kết quả; đây là kết nối PS thực, không phải nguồn dữ liệu giả buộc hằng để xóa logic.

AXI base `0x43C00000`, range 4 KiB. Interconnect Xilinx xử lý giao tiếp AXI3 của GP0 và chuyển sang AXI-Lite. Bridge giữ AW/W độc lập, một write response và một read response outstanding, giữ response khi backpressure, hỗ trợ WSTRB. Reset từ PS/MMCM qua IP Xilinx; aux reset active-low được nối mức 1, debug reset active-high nối mức 0.

Số học trong 3 file lõi được sao chép nguyên byte từ bản 160 MHz đã kiểm. Giữ packed16, FFT32/64/128, multi-modulus NTT và native NTRUGen64. Từng kernel phải giữ nguyên số chu kỳ; tổng thời gian qua AXI có thêm chi phí giao dịch bus.

## Cấu hình board và phạm vi

Xem [nguồn board](board_sources.md): dùng core ATK-7020 của ALIENTEK Qiming Star, PS reference 33.333333 MHz, không dùng preset QMTECH/ZedBoard. Chưa quan sát revision bo vật lý. Các ngoại vi đang tắt không nằm trong phạm vi sign-off. Chưa chạy phần mềm hoặc đo trên board; sign-off STA cho FPGA không thay thế kiểm tra hoạt động vật lý.

Giữ contract IFFT của lõi: dữ liệu trong RAM chưa scale, scale khi đọc host; phải đọc hết kết quả trước một cấu hình/start/load mới. Bridge không thêm chaining trực tiếp giữa kernel trên dữ liệu IFFT đã chuẩn hóa.

## Kiểm chứng

- `validate.py`: 1.026 ca đi qua AXI thật, kết quả và chu kỳ kernel khớp bản lõi đã kiểm, gồm packed16/batch và các độ rộng/modulus.
- AW/W đến lệch nhau, B/R backpressure, WSTRB, địa chỉ/lệnh không hợp lệ.
- `tb_axil_reset.sv`: reset giữa AW/W và khi response B/R đang chờ.
- `tb_generated_reset.sv`: mô phỏng chính IP reset Xilinx sinh từ BD, kiểm startup, chờ LOCKED, PS reset, mất lock và reset phụ.
- 74 lời gọi transform từ C qua AXI, 14 artifact giống reference, 4 chữ ký được verifier độc lập chấp nhận. Phần ngoài transform vẫn ở C; không phải toàn signer chạy RTL.

Core đã có 38 ca kiểm bốn trạng thái và reset-abort 12 chế độ trong bản baseline; ba file core giữ nguyên, còn bridge/reset được kiểm riêng ở bản này.

## Register map

| Offset | Nội dung |
|---|---|
| `0x000` | ID, đọc `0x41434731` |
| `0x004` | Command, write-only, đúng một bit: CFG=1, START=2, ROOT_WRITE=4, ROOT_COMMIT=8, DESC_WRITE=16, LOAD=32, READ=64, RESET=128, ACK=256 |
| `0x008` | Status: bit0 cfg-ready, 1 load-ready, 2 read-ready, 3 core-busy, 4 done-sticky, 5 core-error, 6 read-complete, 7 command-pending |
| `0x00c` | Chu kỳ kernel |
| `0x010` | Config: fft[0], inverse[1], native[2], packed[3], jobs_log[6:4], fmt[8:7], hmin[10:9], logn[14:11] |
| `0x014`, `0x018` | q, qinv |
| `0x020`..`0x030` | Descriptor stage, mask, root_base, root_mask, gap; mỗi field một word |
| `0x034`..`0x03c` | Root destination mask, address, data |
| `0x040` | Chỉ số dòng load/read |
| `0x050`..`0x05c` | 128-bit input, limb thấp trước |
| `0x060`..`0x06c` | 128-bit output, limb thấp trước |

Chờ ready tương ứng trước khi phát command; khi command pending hoặc core busy, ghi payload bị trả SLVERR. RESET luôn được chấp nhận; ACK xóa cờ done/read-complete. Đọc trạng thái và đọc kết quả không tạo command mới. Bridge là giao tiếp điều khiển đơn giản; không dùng DMA hoặc coi bandwidth AXI-Lite bằng bandwidth kernel.

## Luồng build và STA

Từ gốc repo, chạy `create_project.tcl -tclargs synth`, `run_sim.ps1`, `run_reset.ps1`, `validate.py`, rồi `implement.tcl` bằng Vivado 2018.1. Mô phỏng dùng snapshot `study/build/a_cg_z020_system160/rtl_run`. Reset AXI được chạy bằng Icarus; IP reset VHDL bằng XSim cùng thư viện Xilinx.

`implement.tcl` đọc full-system mapped checkpoint, source `signoff.tcl`, rồi opt/place/phys-opt/route mặc định. `signoff.tcl` xác định chân FCLK0 thật của PS7, tạo/kiểm root 100 MHz, kiểm generated clock MMCM 160 MHz, đặt setup uncertainty 0.100 ns và hold uncertainty 0.050 ns. Không dùng OOC `HD.CLK_SRC`, input/output delay giả, hoặc tự thêm false-path/multicycle/case-analysis để xóa lỗi.

Vivado 2018.1 vẫn sinh ràng buộc pad DDR dù DDR tắt. Generator giữ clock và pad PS đang dùng, chỉ bỏ các dòng gán chân DDR không áp dụng. Clock constraint phải scoped đúng tầng `inst/PS7_i` của wrapper PS7. Implementation thiết lập lại root clock bằng chân primitive và kiểm period trực tiếp; không dựa vào một clock constraint bị thiếu ở synthesis. Clock đầu vào stand-alone của Wizard được thay bằng generated clock 1:1 từ FCLK0, rồi MMCM sinh 160 MHz. Jitter ở PS root và nhánh đầu vào Wizard đều đặt 0,300 ns; generated clock nối đúng nguồn PS. Setup/hold uncertainty ở 160 MHz lần lượt 0,100/0,050 ns.

`audit.tcl` mở lại route, áp đầy đủ clock/jitter cuối cùng, update timing và xuất toàn bộ báo cáo. Lượt P&R ban đầu có +0,043/+0,007 ns; số chốt sau audit là +0,038/+0,011 ns. Các số trong bảng đầu trang và `signoff_results.json` dùng bản audit, không dùng số sơ bộ.

Để kiểm baseline đã nhận: `python -X utf8 scripts/check_baseline.py`; kiểm chức năng bằng `python -X utf8 experiments/a_cg_z020_system160/validate.py`. Để Vivado tính lại mà giữ nguyên bằng chứng: chạy `fpga/z020/audit.tcl`; báo cáo mới ghi ở `study/build/z020_baseline_audit/`. Các script audit/report của thí nghiệm được giữ làm lịch sử, không dùng để ghi đè mốc đã pin. Checkpoint `signoff.dcp` đã chứa clock cuối; checkpoint `routed.dcp` cần audit lại trước khi đọc slack.

Bằng chứng ở `study/build/a_cg_z020_system160/`: cấu hình `system_config.txt`, `functional_verified.json`, các log mô phỏng, `reset_sim/run.log`, project PS7/init, `system_synth.dcp` và `route/`. Lượt P&R trước khi sửa reset hoặc trước khi sửa cách nạp constraint đã dừng, không dùng làm kết quả chốt.
