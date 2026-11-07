# 11 — Liveness, quyền sở hữu state và điều kiện khóa 0.2

Ngày khóa thiết kế: 2026-11-05. Port normative ở [08](08_locked_ports.md), clock ledger ở [09](09_locked_cycles.md), FSM ở [10](10_locked_fsm.md). Đây là khóa **microarchitecture của thiết kế**, không phải nghiệm thu RTL/PPA.

## 1. Mô hình chạy được

Source: `verification/model/liveness.py`. Chạy từ repository root:

```powershell
python -X utf8 rebuild/flextransform/tools/freeze_microarchitecture.py
python -X utf8 rebuild/flextransform/tools/render_timing_contract.py
python -X utf8 rebuild/flextransform/verification/model/liveness.py
python -X utf8 rebuild/flextransform/tools/check_design.py
```

Hai lệnh đầu chỉ sinh contract JSON/Markdown/CSV, không sinh datapath RTL. Model ghi `study/build/flextransform_rebuild/microarch_0_2/liveness_results.json`. `--quick` chạy subset và **không đủ để duy trì trạng thái locked**; phải có full report khớp hash source hiện tại.

Geometry dùng config/bank/addr primitives của planner đã pin; **lịch thời gian, resource reservations, data-version replay và các scoreboard dưới đây được dựng lại cho clock contract0.2**. ID/version trong model là shadow state để kiểm, không phải bus rộng hoặc tag bổ sung cần đưa vào phần cứng. Đây không phải một oracle số học FFT độc lập mới. Không thay expected output/reference C.

## 2. Mỗi cấu hình được kiểm gì?

Model quét 328 layout hợp lệ ×2 chiều, cộng native64 =730 trường hợp. Bao gồm identity, N nhỏ, dummy, full/incomplete packed, batch bank/row, FFT ba precision và native. q không đổi control latency nên không lặp mọi giá trị q cho cùng một shape; domain q vẫn phải theo arithmetic contract.

Với mỗi trường hợp:

1. Dựng từng butterfly và địa chỉ read/write/root theo tầng, k và plane.
2. Tính first-read, accept, từng product launch/return, MAC, side read, response và bank commit từ timing.json.
3. Reserve từng leaf, MAC68, C0/C1, C2/C3, C4, C5, output port và root-read port theo tile/clock.
4. Kiểm địa chỉ thực đi được qua **đúng mạng bốn nguồn**, mỗi nửa bank chỉ cần row đã quy định và toàn mảng dùng chung root address.
5. Kiểm 1R/1W, không RAW cùng cạnh; mỗi read thấy version `(tầng,job,p,plane)` đúng. Host cuối phải thấy version cuối, không chỉ đúng số transaction.
6. Theo dõi buffer, slot, partial sum và tag đến khi drain; không overwrite/free hai lần hoặc đọc state của butterfly khác.

Tầng có output phải push context trước nó. gap giữa hai tầng là first-read-to-first-read, 1..65535; gap của descriptor cuối bằng0 và bị bỏ qua. Epoch20 đủ cho10 tầng; mỗi timestamp model kiểm dưới2^20.

## 3. Bound và peak đã kiểm

| State/resource | Depth thiết kế | Peak model |
|---|---:|---:|
| Side slot đã reserve, chưa read/release | 16 | 13 |
| Side word đã write, chưa read | 16 | 12 |
| Packet NTT còn outstanding đến rsp | Counter5 bit | 14 |
| FFT32 butterfly buffer | 8 | 6 |
| FFT64 thường/native buffer | 4 | 3 |
| FFT128 buffer | 2 | 2 |
| Write context queue | 16 | 2 |

Peak model là peak của traffic/lịch được liệt kê, không phải upper bound cho traffic tùy ý. Bound queue16 còn có chứng minh cấu trúc: một kernel, tối đa10 tầng, mỗi tầng push một lần. Không giảm depth về2 chỉ vì peak hiện tại2 mà chưa thay contract và model.

## 4. Reserve, write, release và retire khác nhau

NTT: reserve địa chỉ tại tile fire C0; pipeline địa chỉ4 bit cùng data đến side write C2. Side read/register C19 rồi release slot. Rsp GS C20/CT C21 mới retire outstanding. Count5 bit không được wrap thành0 khi16; pointer4 bit được phép wrap.

FFT: reserve một buffer ở req_first. Mỗi beat ghi semantic index `(beat&1)*L+(beat>>1)` vào buffer. Free ở T-combine imaginary cuối C16/C27/C64 (native inverse64 C29); output vẫn có thể pending thêm1/2 clock. Busy là outstanding **hoặc** valid pipeline, không phải chỉ buffer_count.

Same-edge ordering cho state counter:

```text
count_next = count + reserve_now - release_now
can_reserve = count<depth OR release_now
```

Release chỉ từ giao dịch đã sống. Data cũ cần được read/capture tại cạnh đó trước khi slot được reuse cho **future writes**; alloc không đồng nghĩa ghi dữ liệu vào slot ngay. Model đọc old state, free/retire, rồi alloc/write theo hợp đồng; write/read BRAM cùng hàng vẫn bị cấm riêng.

`ntt_alloc_addr` và `ntt_head_addr` thuộc ft_tile_state. ft_mont_pipe chỉ pipeline alloc address tới C2 và dùng head address khi side_re C19; không có bộ pointer thứ hai. Partial_sum RAM cũng thuộc ft_tile_state, combine chỉ tạo địa chỉ/control.

## 5. History/group đúng giao dịch

Return identity theo từng nhóm được model lưu tại launch+5. T mux dùng group signal trễ5 tính từ operand C2; mq mux dùng trễ15. History write C8 lấy T đúng nhóm; U C18 lấy mq đúng nhóm và old history stage9 cùng ID. Invalid bubble vẫn shift qua history.

Không lấy group hiện tại hoặc group cuối thay group_at_T. Hai lane trong một packet và hai group có vai trò khác nhau; metadata group không được suy lại từ phase tại lúc kết quả về.

## 6. Context FIFO có head/next lookahead

RAM16×36 giữ backing storage; head và next là FF. Model LookaheadFIFO được so với deque oracle độc lập trong20.000 clock random, có full/empty và4.881 push/pop đồng thời ở seed đã pin.

| Trước cạnh | pop/push | Head sau cạnh |
|---|---|---|
| count0 | push | Incoming data bypass |
| count0 | push+pop | Forward incoming, queue vẫn rỗng; không dùng cho response kernel thiếu context |
| count1 | pop+push | Incoming data bypass thay head cũ |
| count≥2 | pop | Old next FF thành head |
| count2 | pop+push | Head=old next; next=incoming, bypass write/read RAM cùng địa chỉ |
| count16 | pop+push | Cho phép; pop dùng old head FF, không đọc nhầm word mới vừa overwrite |

Model kernel vẫn yêu cầu context đã push trước accept; empty bypass không được dùng để che lỗi đó. Tail_seen cập nhật từ write commit; khi tất cả active bit đã thấy terminal tag mới pop. Response_owner là lowest active tile, không phải tile0 cứng. Quét65.535 mask không rỗng, gồm những mask không có tile0.

## 7. FSM và reset

Guard evaluator dùng JSON cùng source với bảng spec10. Model duyệt mọi Boolean assignment của các guard liên quan trong mỗi state để kiểm default, target hợp lệ, reachable state/rule và ưu tiên reset/abort. Có7 FSM; số guard assignments chính xác nằm trong full report. Đây là kiểm finite-control, không là equivalence proof giữa RTL và spec.

Reset test có pipeline data **không reset** và valid reset từng stage, cùng pending-ID scoreboard. Với686 vị trí cắt/traffic scalar và packed, old request bị hủy, dữ liệu cũ vẫn có thể chảy nhưng không được retire; request mới sau recovery phải drain đúng. Mutant chỉ clear output-valid bị bắt. Model không thay việc test reset thật ở RTL hoặc IP Xilinx.

Host read model phát từng phase rồi gather kết quả phase trước từ synchronous bank output, so lại natural-order line. Mutant chỉ gather phase cuối bị bắt, đặc biệt bốn limb FFT128 cùng bank.

## 8. Negative controls phải thất bại

Full run phải bắt đủ11 lỗi cố ý:

- Ghép hai group packed về group0.
- History trễ9 thay vì10.
- T mux dùng group-delay15; mq mux dùng group-delay5.
- Side chỉ có2 slot; FFT128 chỉ có1 buffer.
- Context đến sau response; memory version không đúng tầng.
- Reset chỉ xóa valid cuối pipeline.
- C4 bỏ split guard.
- Host gather chỉ giữ phase cuối.

Nếu một lỗi trong danh sách không còn bị phát hiện sau sửa model, không nhận report PASS để khóa.

## 9. Arithmetic helper và phạm vi số học

Model C4 kiểm19.025 vector với q biên, hai q lane khác nhau và carry FFT; C0–C3 bit-slice model kiểm13.500 vector so mathematical modulo/sum/difference. Width36/35/34/33 được kiểm rõ, không suy từ output32 rồi cắt U.

Đây là sampled helper verification và lập luận bit-width, chưa phải kiểm FFT/NTT numeric toàn RTL mới. 1.026 vector kernel và74 C calls vẫn là gate bắt buộc khi có implementation.

## 10. Thay đổi sau khóa

Không còn lựa chọn tùy ý tại port/latency/guard/FSM của version0.2. Muốn đổi pipeline, FIFO, clock-enable hoặc handshake: tăng contract version, cập nhật JSON, sinh lại CSV/Markdown, chạy full model/negative controls và kiểm source lock. RTL không khớp timing.json là mismatch cần sửa hoặc review phiên bản mới; không sửa expected theo RTL chỉ để PASS.

PPA, DSP inference, routing và setup/hold vẫn phải đo. Một model drain được không bảo đảm FPGA đạt160MHz/35k LUT.
