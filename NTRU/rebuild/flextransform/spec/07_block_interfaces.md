# 07 — Hợp đồng nối các khối RTL

Contract0.2 đã khóa. File này giữ bundle layout và quy tắc nối; danh sách port đầy đủ, chính xác cho23 module nằm ở [08](08_locked_ports.md), lịch ở [09](09_locked_cycles.md), FSM ở [10](10_locked_fsm.md). Nếu mô tả draft trước đây khác, các file08..11 và JSON0.2 là normative.

Mọi module có clk; rst chỉ ở control có state cần reset. Không truyền một struct C hoặc pointer host vào RTL.

## 1. Các bundle chuẩn

### cfg_ctx128

| Bits | Field |
|---|---|
| 1:0 | mode: NTT32=0, FFT=1, packed=2 |
| 2 /3 /5:4 | inverse /native /fmt |
| 9:6 /11:10 /14:12 | logn /hmin /jobs_log |
| 18:15 /21:19 | logm /base_log |
| 24:22 /27:25 /30:28 | bank_jobs_log /row_jobs_log /plane_log |
| 34:31 /38:35 /42:39 | rowlog /stages /job_word_log |
| 50:43 | rows_per_buffer, 1..128 |
| 82:51 /114:83 | q /qinv32 |
| 127:115 | reserved0 |

Không phát toàn128 bit tới mọi FF tile. ft_core tách phần q/mode cần cho tile, phần geometry cho address/host, rồi register cục bộ. params_valid chỉ bật sau decode/range check xong.

### write_ctx36

| Bits | Field |
|---|---|
| 3:0 | stage_id |
| 19:4 | active_mask |
| 20 /21 /22 /23 | destination_buffer /write_far /internal_layer /last_stage |
| 31:24 | expected_last_tag |
| 35:32 | response_owner: tile đầu tiên trong active_mask |

Owner được chọn một lần khi push context, không dùng tile0 cứng. Owner phục vụ chọn tag chung của cohort; completion vẫn chờ mọi bit active_mask. Active mask0 cho tầng có việc là invalid descriptor. Context FIFO depth16, head payload đã register trước khi response đầu tới.

Queue phải có lookahead/prefetch head kế tiếp: nếu hai tầng trả output ở hai clock liền nhau, head mới phải sẵn ngay sau tail-pop. Không cộng một bubble ở queue rồi yêu cầu tile dừng output. Test push/pop cùng cạnh và bypass khi queue rỗng; đưa latency writeback vào planner nếu chọn thêm write FF.

## 2. Ownership điều khiển đã khóa

- ft_core sở hữu executor FSM13 state, configured, roots_committed, desc_valid10, error/status và cycles32.
- ft_stage_ctrl sở hữu descriptor RAM10x46, context queue16x36, tail_seen16, epoch20 và stage sub-FSM. Không sở hữu host/CFG executor FSM hay cycles32 thứ hai.
- ft_host_map sở hữu snapshot line, phase mapping, host-map FSM4 state, read-selector pipeline và gather128.
- ft_read_normalize là pipeline3 stage; core NORM_WAIT đợi out_valid. Không nhân đôi carry/sum/shift FSM ở core.
- ft_tile_state sở hữu RAM và reserve/free pointers. Mont chỉ nhận alloc_addr/head_addr; không tạo pointer riêng. Native align đi cùng buffer3/tag8/root32/beat3/first, không lấy buffer hiện tại cho dữ liệu cũ.
- partial_sum RAM thuộc ft_tile_state; ft_fft_combine phát địa chỉ/control và C5. C4 do ft_tile instantiate đúng một bản, share correction/tổng FFT.

## 3. Scheduled handshake và backpressure

Command valid/op/payload giữ tới fire, ack sau việc apply. Core không nhận command mới khi executor bận. RESET đi abort_req1-clock, ACK clear status tại bridge; không xếp hai opcode này sau normal command đang pending.

Stage valid là scheduled activation đúng deadline: context0 push epoch1; tầng sau first_read-1. Consumer stage_ready phải1 (EMPTY hoặc last-read-lookahead); không thì stage_fault/abort, không tự lùi gap. FIFO head/next đã prefetch trước response.

Tile req_ready bằng0 trong reset, chưa cfg hoặc cfg_valid đang1. CFG và request không fire cùng cạnh. Khi NTT: phase/side credit hợp lệ. FFT: req_first có buffer credit; beat sau đi đúng frame đã reserve. cfg ở BUSY báo fault và giữ context cũ đến reset.

Không có rsp_ready. Mọi response có write context và nơi commit đã reserve trước khi issue. Chỉ thay lịch thông qua một version contract mới có model PASS.

## 4. Storage token và valid

side42={reserved0,pairing,tag8,data32}. U34 packed={Uhi17,Ulo17}, scalar={0,U33}. MAC meta10={buffer3,product2,limb2,emit,column_last,first}; limb meta7={buffer3,product2,limb2}. read_meta30={mask16,tag8,near,swap,far,dummy,pairing,first}.

C4 width36, C0/C1/C2/C3 lần lượt33/34/35/34. C4 underflow[1:0]={high,low} khi packed, replicate borrow khi scalar,00 khi FFT; result ở FFT là low32 của fft_sum33. fft_sum chỉ có ý nghĩa cho caller FFT. s/d của addsub là outputs sau stage1 register; co_now/bo_now thuộc input hiện tại; fs/ws là tổng live từ FF của caller. Xem spec09 cho mốc chốt, không tự thêm FF để làm tất cả port có cùng latency.

Với tầng packed dummy, bank/word dummy bị mask; completion chỉ đòi các word thực của response. Tail_commit là điều kiện bank write **sẽ commit ở cạnh hiện tại**, cùng wen/address/data và cùng abort/fault gating. Context pop tại cạnh đó. DONE ở cạnh sau khi queue/valid/busy đã rỗng; không dùng product-done hoặc tile0 làm DONE.

## 5. Lỗi và compatibility

Địa chỉ/register map3.1 giữ nguyên cho traffic hợp lệ; thời gian ready/ack theo contract0.2. Frontend kiểm full32-bit payload trước khi pack field hẹp. DESC stage>=10 hoặc mask0 bị từ chối; root-order, root span, gap/collision phải được generator kiểm, RTL không tự chứng minh root có bậc đúng.

Soft abort không clear AXI B/R đã phát; chúng giữ đến handshake. Error của READ được báo qua ack_error/status error; driver phải poll complete OR error, không chờ complete mãi khi context đã abort. ACK không xóa error; enqueue CFG/START hoặc RESET clear lỗi cũ, rồi ack_error/core_done+error của giao dịch mới có thể set lại. Quy tắc ưu tiên chính xác ở spec10.
