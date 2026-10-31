# 02 — Native interface, protocol, reset, pause and flush

## 02.1 Timing conventions và reset

Tất cả signal đồng bộ `clk_i`, transfer tại rising edge khi `valid && ready`
được lấy mẫu là 1. Sender MUST giữ valid và toàn payload ổn định khi valid=1,
ready=0; receiver MAY giữ ready=0 tùy ý. Không có transfer chỉ dựa trên valid.
Ready MAY phụ thuộc occupancy; không tạo vòng tổ hợp qua valid/ready giữa các
module. Registered ready hoặc skid buffer SHOULD dùng ở đường dài.
(FT-IF-001..003)

`rst_ni`: synchronous active-low, ưu tiên cao nhất; giữ low ít nhất hai rising
edge khi khởi tạo. Reset clear toàn bộ valid/occupancy/context/error/counter,
không clear data RAM/ROM. Không sinh completion cho command bị reset. Không
phát write RAM khi reset low; output-valid và command/memory-ready phải low
trong reset. Sau deassert, có thể nhận request từ rising edge kế tiếp nếu
không pause/flush và không còn response cũ. Không dựa vào `initial` để reset
control; ROM initialization là trường hợp riêng. (FT-RST-001..002)

## 02.2 External port groups

Danh mục machine-readable: [interface.json](interface.json). Tất cả payload là
unsigned bit vector, trừ dữ liệu số học được diễn giải theo format ở tài liệu 01.

| Group | Input | Output |
|---|---|---|
| Clock/control | clk_i, rst_ni, pause_i, flush_i | flush_done_o |
| Command | cmd_valid_i, payload dưới đây | cmd_ready_o |
| Completion | cpl_ready_i | cpl_valid_o, payload dưới đây |
| Host-memory request | mem_req_valid_i, write/store/addr/data/strb | mem_req_ready_o |
| Host-memory response | mem_rsp_ready_i | mem_rsp_valid_o, data/status |

### Command payload

| Signal | Bits | Ý nghĩa |
|---|---:|---|
| cmd_op_i | 4 | Opcode 0..8 |
| cmd_fmt_i | 2 | 0/1/2 FFT format, 3 RES16 |
| cmd_profile_i | 2 | FFT=0, NTT=0/1 |
| cmd_logn_i | 4 | log2 N |
| cmd_jobs_m1_i | 3 | jobs−1 |
| cmd_tag_i | 32 | Opaque batch identifier, trả nguyên trong completion |
| cmd_reserved_i | 8 | MUST zero |

Mọi field latch đúng tại command handshake. Source MAY đổi command payload
sau handshake; thay đổi đó không ảnh hưởng job đang chạy. Không có đầu vào q
thô, twiddle thay thế hoặc per-job format. (FT-IF-004)

Chỉ một command chưa hoàn thành/ACK. Hai **context nội bộ** không có nghĩa nhận
hai external command đồng thời. `cmd_ready_o` chỉ high ở IDLE, không pause,
không flush, không completion/host-memory response đang chờ. Nếu command và
memory request cùng valid ở IDLE, host-memory request có ưu tiên; cmd_ready
MUST low để không nhận cả hai tại một edge. (FT-IF-005)

### Completion payload

| Signal | Bits | Ý nghĩa |
|---|---:|---|
| cpl_tag_o | 32 | Tag của command đã nhận |
| cpl_status_o | 8 | Bảng status dưới đây |
| cpl_job_mask_o | 8 | OK: bit j=1 cho mọi job 0..jobs−1; error/abort: zero |
| cpl_cycles_o | 64 | Clock edges core bận, gồm pause, không gồm host load/read/DONE hold |
| cpl_active_cycles_o | 64 | Busy edges có pause_i=0; gồm điều khiển/retire |

Command nhận tại E0. Counter bắt đầu từ zero; tăng trên từng rising edge tiếp
theo mà command chưa publish completion, gồm edge hoàn tất công việc. Payload
counter latch khi publish cpl_valid, sau đó không tăng trong DONE. Identity và
invalid command MAY publish ngay sau E0 với counter=0; completion handshake
vẫn chỉ xảy ra từ edge tiếp theo. Counter không quy đổi sang ns hoặc MHz.

Mỗi accepted command MUST có đúng một completion, trừ khi reset hủy command.
Không có unsolicited completion cho flush ở IDLE. `OK` chỉ publish sau khi
toàn bộ job đã tính xong, tất cả write đã commit, context/pipeline không còn
side-effect của command. cpl_valid và payload phải giữ đến ACK, kể cả pause
hoặc flush đến sau khi completion đã publish. (FT-IF-006..008)

### Command status và validation priority

| Code | Tên | Điều kiện |
|---:|---|---|
| 0x00 | OK | Toàn bộ kết quả hợp lệ, đã commit |
| 0x01 | BAD_RESERVED | reserved khác zero |
| 0x02 | BAD_OP | Opcode không hỗ trợ |
| 0x03 | BAD_FMT | Format không thuộc family opcode |
| 0x04 | BAD_PROFILE | Profile không hợp lệ cho family |
| 0x05 | BAD_LOGN | N không thuộc bảng support |
| 0x06 | BAD_JOBS | jobs vượt miền cho op/N |
| 0x10 | ABORTED | Flush hủy command chưa publish completion |
| 0x11 | INTERNAL_FAULT | Detected context/tag/retire invariant failure |

Nếu nhiều field sai, chọn lỗi đầu tiên theo thứ tự BAD_RESERVED → BAD_OP →
BAD_FMT → BAD_PROFILE → BAD_LOGN → BAD_JOBS. Tránh kiểm predicate phụ thuộc
op/profile chưa hợp lệ. Invalid command MUST không issue arithmetic, không
đọc coefficient/ROM để chạy kernel, không sửa RAM; trả tag và mask=0.
Checker INTERNAL_FAULT không phải fault-injection/functional-safety certification.
(FT-ERR-001..003)

Khi phát hiện invariant failure trong RUN, core MUST dừng issue/command write,
discard pending writes, drain/invalidate packet rồi publish INTERNAL_FAULT,
mask=0. Không rollback dữ liệu đã commit; caller phải reload input như ABORTED.
Reset có ưu tiên cao nhất; flush lấy mẫu trước khi error completion publish
chọn ABORTED. Nếu INTERNAL_FAULT đã publish, flush giữ nguyên completion đó.
Không thay đổi payload một response đã publish để báo lỗi mới.

## 02.3 Host-memory request/response

| Signal | Bits | Ý nghĩa |
|---|---:|---|
| mem_req_write_i | 1 | 1=write, 0=read |
| mem_req_store_i | 2 | 0=A,1=B,2=C,3 reserved |
| mem_req_addr_i | 16 | Byte address trong store, 16-byte aligned |
| mem_req_wdata_i | 128 | Byte thấp nhất ở [7:0] |
| mem_req_strb_i | 16 | Byte enables cho write; bit b điều khiển wdata[8b+:8] |
| mem_rsp_rdata_o | 128 | Raw line read; write/error response trả zero |
| mem_rsp_status_o | 3 | 0 OK,1 BAD_STORE,2 BAD_ALIGN,3 RANGE,4 STATE |

Mỗi store 0x0000..0x3fff byte. Request đọc/ghi đúng một line 16 byte, không
burst. `addr[3:0]` MUST zero; `addr<=0x3ff0`. Store, alignment, range được
kiểm trước state với priority theo thứ tự trên. Reads ignore strb; writes all
strb=0 là successful no-op, vẫn trả response. Partial byte writes chỉ thay
byte được enable. Không có read-modify-write ngầm làm mất byte còn lại.

Chỉ một outstanding memory transaction; mỗi request đã nhận có đúng một
response. Memory ready low cho đến khi response cũ handshake. Response ổn
định khi blocked. Host write response OK chỉ sau khi mọi enabled byte commit.
Read response xuất hiện không sớm hơn edge sau request; latency không cố định
nếu phải service nhiều bank round. Không reorder response. (FT-MEM-001..004)

IDLE cho phép đọc/ghi; RUN/FLUSH không nhận host-memory request. DONE chỉ đọc;
write được nhận rồi trả STATE, không thay RAM. Completion và read có thể cùng
valid. Nếu completion handshake ở một edge, mem_req_ready MUST low ở edge đó;
response của request đã nhận trước đó vẫn được bảo toàn. Sau ACK, state
RETURN chờ memory response cũ drain rồi mới trở về IDLE/nhận command mới.
Không nhận command chỉ vì cpl_valid đã được ACK nếu memory response còn pending.
(FT-MEM-005..006)

Host raw line interface độc lập cmd_fmt. Little-endian:
`line.byte[b] = store.byte[addr+b]`; word16 thấp lưu limb thấp. Đọc phần chưa
khởi tạo có giá trị không quy định. Không có cache coherence/AXI/CDC/DMA trong
interface này. System adapter chịu trách nhiệm nối bus/ordering bên ngoài.

## 02.4 Pause

`pause_i=1` ngăn nhận command/memory request mới và giữ toàn bộ datapath,
issue, gather/prefetch, context và internal write-retire. Không có arithmetic
accept hoặc RAM write của command trong pause. Data/valid của pipeline đang
stall giữ nguyên; không chỉ dừng FSM trong khi metadata vẫn chạy tiếp.

Completion/memory response đã publish vẫn giữ valid, có thể được ACK trong
pause; channel quản lý được phép drain các response đó. Wall counter vẫn tăng
khi command RUN bị pause, active counter không tăng. Reset và flush có ưu
tiên cao hơn pause; flush phải hoàn thành được dù pause giữ high.
(FT-CTL-001..002)

Host-memory request đã accept trước pause vẫn được hoàn tất và trả response;
đây không phải command write-retire. Pause không được làm mất request đó.
Flush phải cho giao dịch host đã nhận hoàn tất rồi drain response trước ACK.

## 02.5 Flush — four-phase level handshake

1. Host assert `flush_i=1` và giữ đến khi `flush_done_o=1`.
2. Core không nhận command/host-memory request mới. Với command RUN chưa
   publish completion: cancel issue, discard kết quả/queued write chưa commit,
   drain hoặc invalidate packet in-flight bằng epoch, tạo một completion ABORTED.
3. Khi internal state đã sạch, accepted host-memory response đã drain và
   completion ABORTED (nếu có) đã latch ổn định, core assert flush_done.
   Không chờ cpl_ready để assert flush_done.
4. flush_done giữ high khi flush_i vẫn high. Host deassert flush_i; core
   deassert flush_done tại edge kế tiếp. Chỉ sau đó mới có thể nhận request mới,
   và vẫn phải tôn trọng completion chưa ACK.

cmd_ready và mem_req_ready MUST low khi flush_i hoặc flush_done high.

Ở edge đầu core lấy mẫu flush_i high, không được commit thêm command write.
Write đã commit ở edge trước vẫn ở RAM; không rollback. Mọi output của batch
bị ABORTED là invalid, kể cả job có vẻ đã chạy xong; job_mask=0. Caller phải
nạp lại input trước khi chạy lại in-place kernel. (FT-FLS-001..003)

Nếu cpl_valid đã high trước edge nhận flush, completion payload đó bất biến:
không đổi OK thành ABORTED, không tạo completion thứ hai. Flush ở IDLE chỉ
clean/drain rồi ACK, không sinh completion. Flush ở DONE có thể cùng lúc ACK
completion. Reset trong flush hủy protocol state và flush_done=0.
(FT-FLS-004..005)

Request chưa handshake không thuộc core và không bị flush hủy. Sender vẫn giữ
valid/payload nếu muốn request đó được nhận sau flush; hệ thống không được giả
định một request đang blocked đã chạy hoặc đã bị cancel. Host MUST cho phép
memory response cũ drain khi yêu cầu flush; nếu giữ mem_rsp_ready=0 mãi thì
flush_done không có bảo đảm thời gian hữu hạn.

Flush MUST không deadlock và hoàn tất trong 256 clock sau khi accepted
host-memory responses đã drain, với clk chạy liên tục; pause không kéo dài
bound này. Completion backpressure không được kéo dài bound. Pipeline sâu hơn
không đáp ứng bound cần version/profile đổi, không tự tăng bound trong RTL.
(FT-FLS-006)

## 02.6 State/priority và interface invariants

Priority: reset → flush/cancel → published response handshake → pause-hold →
normal issue/retire. Published payload không bị reset/flush semantics làm
thay đổi, ngoại trừ reset hủy valid theo 02.1.

| State | Command ready | Memory request | Completion |
|---|---|---|---|
| RESET | 0 | 0 | invalid |
| IDLE | theo arbitration | read/write | invalid |
| VALIDATE/RUN | 0 | 0 | invalid đến khi publish |
| DONE | 0 | read; write trả STATE | valid, held đến ACK |
| RETURN | 0 | 0 | đã ACK, chờ memory response cũ |
| FLUSH | 0 | 0 | preserve published hoặc publish ABORTED |

Control state MAY encode khác bảng nhưng hành vi MUST tương đương. Không có
combinational dependence từ một payload secret vào ready/cpl latency.
Trong functional verification, sender/receiver có thể backpressure tùy dài;
core phải giữ đúng dữ liệu, không duplicate/drop hoặc reuse context sớm.
