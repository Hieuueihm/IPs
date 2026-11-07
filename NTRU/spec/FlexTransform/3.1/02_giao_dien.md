# 3.1 — giao tiếp baseline

Hệ thống: `system_wrapper` sinh bởi `create_project.tcl`; AXI slave `a_cg_axil`; native core `a_cg_fast`. Xem [RTL bridge](../../../experiments/a_cg_packed4_system160/rtl/a_cg_axil.v) và [native ports](../../../experiments/a_cg_packed4_system160/rtl/a_cg_fast.sv). Các file RTL đang được pin, không sao chép cổng từ spec 2.0.

AXI4-Lite 32-bit data, 12-bit offset, base **0x43C00000**, range **4 KiB**. AW/W được nhận độc lập; B/R giữ nguyên khi bị backpressure; một response đọc/ghi outstanding. WSTRB merge theo byte. Địa chỉ/lệnh không hợp lệ trả SLVERR. Mode/descriptor/root là các thanh ghi payload và command riêng, không phát qua giao diện opcode/format 3 bit/A-B-C của bản cũ.

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


## Sequencing bắt buộc

1. Chờ cfg-ready, ghi config/q/qinv, phát CFG và chờ command hoàn tất/ready trở lại; kiểm core-error.
2. Nạp descriptor từng tầng, root theo tile/địa chỉ; phát ROOT_COMMIT theo trình tự driver baseline. Chỉ dùng bảng/planner đúng cấu hình và chiều. Lõi không tự chứng minh mọi descriptor tùy ý không gây xung đột.
3. Chờ load-ready, ghi line_index/input, phát LOAD cho từng dòng.
4. Chờ được nhận lệnh, phát START; poll done-sticky, kiểm error, đọc cycles.
5. Chờ read-ready, ghi line_index, phát READ; chờ read-complete rồi đọc các word output. Đọc đủ trước cấu hình/start/load mới, đặc biệt IFFT.

`cfg_fmt` native là **2 bit**, 0/1/2 tương ứng 32/64/128; 3 không hợp lệ. `cfg_hmin` 2 bit, `cfg_jobs_log` 3 bit, `cfg_logn` 4 bit. Payload được snapshot qua pipeline. Không phát command mới hoặc đổi payload khi command đang pending/core busy; đọc status vẫn được phép. START/CFG/LOAD/READ và lệnh root/descriptor phải tuân guard bridge/ready; không dùng việc có AXI response để suy kernel đã xong.

## Reset và clock

Miền AXI/lõi cùng 160 MHz. PS FCLK100 đi qua MMCM; GP0 ACLK nối cùng 160 MHz với PL. PS reset và LOCKED của MMCM vào `proc_sys_reset`; reset phụ active-low nối 1, debug reset active-high nối 0. IP reset được kiểm startup, chưa lock, PS reset, mất lock và aux reset.

Bridge có RESET command giữ core reset nhiều chu kỳ và chặn command khi đang phục hồi. Reset hệ thống xóa giao dịch AW/W chưa đủ và response B/R đang chờ; phần mềm phải khởi tạo context/bảng/dữ liệu sau reset, không tiếp tục transaction cũ. Đây không phải secure-erasure claim cho toàn bộ BRAM.

## Lịch tile thay đổi từ 3.0

AXI register map, config fields và số bit port giữ nguyên. Tile packed16 req_ready mở ở pha0/1 trong period3, thay vì chỉ pha0; mỗi gói vẫn req64/root32/tag8 và rsp64/tag8, không có rsp_ready. NTT32 vẫn chỉ pha0. Core có lịch lockstep và luôn nhận output; cần regen descriptor/gap theo planner bốn leaf, không tự tăng mật độ yêu cầu mà giữ nguyên lịch cũ.
