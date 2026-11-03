# 06 — Integration examples and implementation checklist

Ví dụ dưới đây giải thích contract, không khóa pipeline latency hay FSM encoding.
Các wait đều chờ handshake thật, không đoán thời điểm bằng một delay cố định.

## 06.1 Host sequence và raw memory packing

1. Giữ synchronous reset low ít nhất hai rising edge; deassert reset.
2. Chờ không pause/flush. Nạp input bằng aligned host-memory lines và byte enables.
   Mỗi request chờ response OK trước request kế tiếp. Nạp cả A/B khi op cần B.
3. Assert CMD valid với mọi field cố định đến khi cmd_ready handshake. Sau đó có
   thể hạ valid/đổi input, không thay đổi job đã latch.
4. Chờ cpl_valid. Nếu muốn đọc output trong DONE, giữ cpl_ready=0, đọc mọi line
   output và drain memory responses. Không ghi RAM trong DONE.
5. ACK completion. Sau khi response cũ drain và ready trở lại, có thể nạp job mới.
   Cũng có thể ACK trước rồi đọc output ở IDLE, nhưng không nạp đè trước khi đọc.

Ví dụ FFT Q16.16 N2: A0=1.0, A1=−2.0. Hai component là hex00010000 và
fffe0000. Host write storeA, addr0, wdata low64=`fffe000000010000`, upper64=0,
strb=0x00ff. CMD op0/fmt0/profile0/logn1/jobs_m1=0/reserved0; tag tùy chọn.
FFT N2 identity nên A0/A1 giữ nguyên. Các byte8..15 của line không bị ghi bởi
host request này hay bởi command; nếu chưa khởi tạo, không so expected ở đó.

Ví dụ NTT multi-job N8/jobs8: jobj nằm tại byte16*j..16*j+15 trong storeA.
Nạp tám line, CMD op5/fmt3/profile0/logn3/jobs_m1=7. Không phải một N64 NTT.
OK có cpl_job_mask=0xff; hai store B/C và byte128 trở đi của A không thay đổi.
Với profile1, cùng packing; chỉ root/reducer constants thay.

## 06.2 Pause và flush khi output đang chờ

Nếu cpl_valid đã high và cpl_ready=0, assert pause hoặc flush không được đổi
status/tag/mask/counters. Có thể ACK completion trong pause/flush. Nếu flush
được lấy mẫu trước completion publish, cancel thắng: không command write tại
edge đó và command trả ABORTED/mask0 sau clean/drain. Không có tình huống
vừa trả OK vừa ABORTED cho một command.

Khi ABORTED/INTERNAL_FAULT, bỏ mọi output batch, reload input cho in-place
kernel. Flush không khôi phục input cũ. Reset không bảo toàn completion; host
phải coi command/host transaction chưa nhận reply là canceled qua reset.

flush_i giữ high đến flush_done, rồi deassert và chờ flush_done low. cmd_ready
và mem_req_ready MUST low khi flush_i hoặc flush_done high. Completion chưa
ACK vẫn chặn nhận command tiếp theo dù flush handshake đã xong.

## 06.3 Trình tự triển khai đề nghị

| Mốc | Artifact cần chốt | Kiểm trước khi nối tiếp |
|---|---|---|
| Arithmetic | leaf sign, raw65, exact fusion/round, reducer, CT/GS | T_FP_PRIM, T_NTT_PRIM, T_ROOT |
| Array | Frame packing, latency, stall/CE, bypass alignment | T_ARRAY, masks và stable payload |
| Context | Hai buffer, triplet collect, side-data/address ownership | T_CONTEXT, canceled epoch |
| Memory | Bank map/service, byte enables, host response, commit ACK | T_BANK, T_MEMORY |
| Kernel | FFT/NTT loop/root/layout, paired pass, scalar normalize | T_FP_KERNEL, T_NTT_KERNEL, T_JOBS |
| Protocol | Validate, completion, reset/pause/flush/error paths | T_CFG, T_NATIVE, T_STABILITY, T_FLUSH, T_RESET |
| Release | Live R8 integration, stress, trace/perf, manifest | T_SIGNER, T_MUTATE, T_STRESS, T_PROFILE, T_PERF, T_RELEASE |

Chốt implementation manifest trước integration: pipeline latency và capacity
cho mỗi path; vị trí fusion/rounding; context/queue depth; macro RAM timing;
root prefetch/arbitration; reset/flush invalidation. Chỉ memory-pass sau mới
chờ RAM commit barrier; hai tầng NTT fused truyền intermediate trong tile.

Khi đọc hình cũ ở [concept v2](../../../docs/rtl_concept_v2.md), dùng các width,
enum và ownership đã khóa trong bộ spec này. Hình không ghi đè protocol; không
lấy baseline simulation làm evidence cho các block mới chưa được viết.
