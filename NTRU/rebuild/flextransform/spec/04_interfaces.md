# 04 — Giao tiếp và quản lý command

Contract0.2 đã khóa: giao tiếp ngoài giữ map3.1; port chính xác ở spec08, clock ở09, FSM ở10. Phần giải thích sau dùng cùng contract. Tất cả trong một clock. Các tín hiệu valid/data cùng transaction phải đi qua pipeline như một bundle.

## 1. ft_axil_top

| Nhóm port | Rộng | Hướng |
|---|---|---|
| aclk, aresetn | 1,1 | input; reset ngoài active-low |
| s_axi_awaddr, awprot, awvalid / awready | 12,3,1 /1 | input /output |
| s_axi_wdata, wstrb, wvalid /wready | 32,4,1 /1 | input /output |
| s_axi_bresp, bvalid /bready | 2,1 /1 | output /input |
| s_axi_araddr, arprot, arvalid /arready | 12,3,1 /1 | input /output |
| s_axi_rdata, rresp, rvalid /rready | 32,2,1 /1 | output /input |

Một transaction write và một transaction read outstanding. AW/W nhận độc lập; BVALID/BRESP và RVALID/RDATA/RRESP giữ nguyên khi stall. WSTRB merge theo byte. Command word cũng merge với old=0. Offset sai, alignment sai, lệnh nhiều bit hoặc command không nhận được trả SLVERR; không im lặng bỏ lệnh.

Reset hệ thống làm mất các transaction chưa hoàn tất; master phải reset/khởi tạo lại. Không để một AW cũ ghép với W mới sau reset. `awprot/arprot` không được mô tả thành cơ chế security khi chưa triển khai.

## 2. Register map tương thích

Base address trong system profile: 0x43C00000, range4KiB.

| Offset | Quyền / nội dung |
|---|---|
| 000 | RO ID 0x41434731 cho compatibility profile; tài liệu build phân biệt implementation |
| 004 | WO command một bit: CFG1, START2, ROOT_WRITE4, ROOT_COMMIT8, DESC_WRITE16, LOAD32, READ64, RESET128, ACK256 |
| 008 | RO status: cfg_ready0, load_ready1, read_ready2, busy3, done4, error5, read_complete6, pending7 |
| 00C | RO kernel cycles32 |
| 010 | RW cfg: fft0,inverse1,native2,packed3,jobs_log6:4,fmt8:7,hmin10:9,logn14:11 |
| 014 /018 | RW q /qinv32 |
| 020/024/028/02C/030 | RW descriptor stage/mask/root_base/root_mask/gap |
| 034/038/03C | RW root destination mask/address/data |
| 040 | RW line_index |
| 050/054/058/05C | RW input128, word thấp trước |
| 060/064/068/06C | RO output128, word thấp trước |

Không expose queue FIFO hay tile microcode qua các register mới trong profile đầu. Reserved config bits producer ghi0; không truncate field vượt range rồi nhận như hợp lệ.

## 3. Command nội bộ

`ft_cmd_frontend` nối `ft_axil_top` với `ft_core`:

| Signal | Rộng | Ý nghĩa |
|---|---:|---|
| cmd_valid /cmd_ready | 1/1 | fire tại cạnh khi cả hai1 |
| cmd_op | 4 | CFG1,START2,ROOT3,COMMIT4,DESC5,LOAD6,READ7,RESET8,ACK9 |
| cmd_payload | 160 | Snapshot payload bên dưới |
| ack_valid /ack_error | 1/1 | Token command đã áp dụng hoặc từ chối; không backpressure |
| line_rsp_valid /line_rsp_data | 1/128 | Output READ; consumer đã reserve một slot |
| kernel_busy/done/error/cycles | 1/1/1/32 | Trạng thái kernel, tách khỏi ack |
| abort_req /abort_ack | 1/1 | Soft reset ưu tiên, bypass normal queue; xem spec07 |

Một command đang pending. Producer giữ valid/op/payload đến fire. Không dùng pins MMIO sống sau fire. Command mới không được vượt command cũ; RESET hủy transaction pipeline đang có và có đường ưu tiên riêng, không chờ FIFO cũ drain mới reset.

Payload bit layout:

```text
CFG:  [31:0] cfg_word, [63:32] q, [95:64] qinv
ROOT: [15:0] dest, [24:16] addr, [56:25] data
DESC: [3:0] stage, [19:4] mask, [28:20] base,
      [33:29] root_mask, [49:34] gap
LOAD: [9:0] line, [137:10] data128
READ: [9:0] line
START/COMMIT/RESET/ACK: payload0
Các bit còn lại bằng0.
```

Các macro/typedef pack và unpack phải có một nguồn định nghĩa trong `ft_defs.svh`. Các module có port vector tường minh; không bắt buộc SystemVerilog interface để tool cũ dễ dùng.

## 4. Ack không phải kernel done

| Command | Khi ack | Điều kiện/hiệu ứng |
|---|---|---|
| CFG | Decode và range check xong | Latch context, invalidate desc/root, error nếu cấu hình sai |
| ROOT/DESC | Storage write commit | Chỉ idle; ROOT clear root_committed |
| COMMIT | Set root_committed | Không xác minh toàn bộ nội dung root |
| LOAD | Mọi phase line write xong | Không cần chờ cố định4clock ở bridge |
| READ | Line đã gather/normalize và latch output | Set read_complete; không trộn với AXI R handshake |
| START | Core nhận bắt đầu hoặc báo precondition error | Busy tiếp tục đến kernel done; ack không đợi kernel |
| ACK | Cờ done/read_complete đã clear | Không xóa output RAM, không reset context |
| RESET | Valid/context/command đã flush và core sẵn sàng hồi phục | Không phải xóa sạch BRAM |

AXI B response xác nhận MMIO write/enqueue, không xác nhận transform đã chạy xong. CFG lỗi đã enqueue hợp lệ có thể trả B OKAY rồi status error; lỗi địa chỉ/command/điều kiện nhận của bridge trả SLVERR ngay. Phân biệt hai loại này trong driver.

Pending bật cùng cạnh enqueue và giữ tới ack. Payload không được ghi khi pending/busy; status vẫn đọc được. Mọi ready tính từ state đã register và reservation, tránh chuỗi decoder→ready→accept dài.

## 5. ft_tile

| Port | Rộng | Hướng / contract |
|---|---:|---|
| clk,rst | 1,1 | input; rst sync active-high |
| cfg_valid | 1 | input, chỉ khi tile đã drain hoặc reset |
| cfg_mode,cfg_inverse,cfg_native,cfg_fmt | 2,1,1,2 | input, context cố định khi busy |
| cfg_q,cfg_qinv | 32,32 | input; packed scalar q16 được nhân bản nội bộ |
| req_valid /req_ready | 1/1 | input/output; scheduled request |
| req_data,req_root,req_tag | 64,32,8 | input; {Y,X}, root word, {k,plane} |
| req_pairing,req_first | 1,1 | input; pairing NTT / beat đầu FFT |
| prog_valid,prog_product,prog_step | 1,2,4 | input; early FFT product program |
| rsp_valid,rsp_data,rsp_tag,rsp_bf_last | 1,64,8,1 | output, không rsp_ready |
| busy | 1 | output thật, gồm in-flight và pipeline drain |

cfg_mode: scalar NTT0, FFT1, packed NTT2; 3 không hợp lệ. Không còn cfg_slot/req_slot, cfg_floor hoặc en ở core-profile tile mới. Điều này giữ tính năng kernel nhưng không tương thích standalone tile API nghiên cứu cũ.

FFT nhận 2L beat theo re0,im0,re1,im1...; output L real limb rồi L imaginary limb. req_first reserve một butterfly buffer. Sau đó toàn bộ beat/program phải theo lịch đã kiểm; req_ready không phải cơ chế tự cứu một scheduler sai. Khi một tile active không nhận được request đã lên lịch: lỗi contract, abort an toàn, không tiếp tục với data cũ.

Output consumer luôn sẵn sàng. `rsp_bf_last=1` cho mọi gói NTT, hoặc limb imaginary cuối của FFT. Packed một gói là hai butterfly; counter tính theo gói, không tự nhân2 khi quản lý FIFO.

## 6. Vòng đời context và output

Driver: CFG→chờ ready/error→DESC/ROOT→COMMIT→LOAD→START→poll DONE/error→READ từng line. Đọc đủ trước CFG/LOAD/START mới. READ lặp cùng line hợp lệ; READ không làm double-normalize.

Project đầu không thêm bitmap theo dõi phần mềm đã đọc mọi line. Vì vậy lifetime toàn output là **nghĩa vụ caller được ghi rõ**, giống numerical API3.1; phần cứng chỉ ngăn command khi một READ/command còn pending. ACK không phải RELEASE cho một buffer tự động chain kernel.

## 7. Reset và lỗi

Reset clears valid, phase, in-flight counts, FIFO pointers/valid, descriptor-valid/root-committed, sticky status, normalization context và mọi response pending. Không clears dữ liệu RAM. Local reset/config được register gần tile, có thứ tự reset→config→settle, không đồng thời.

Phân biệt reset core và bus: soft RESET flush core/READ nội bộ nhưng **giữ mọi B/R response AXI đã phát đến khi handshake**, kể cả B của chính lệnh RESET. Chỉ reset hệ thống/bus mới clear AW/W/B/R. Không hạ RVALID đang stall chỉ vì phần mềm reset phép tính.

Lỗi cấu hình/thiếu desc/root không phát compute. Khi fault đã định nghĩa (phase/credit/mask/tag/context) được phát hiện ở runtime phải khóa write không hợp lệ, báo done+error, invalidate context; phần mềm reset rồi nạp lại. Không claim hardware phát hiện mọi descriptor/root sai; bank/RAW correctness của lịch hợp lệ được generator/model và assertion kiểm. Không công bố response chứa X hoặc kết quả nửa chừng là thành công. Checker kiểm cả lần abort và công việc hợp lệ sau reset.
