# 10 — FSM đã khóa, contract 0.2

Sinh từ `microarchitecture/fsm.json`. Mỗi hàng dùng giá trị trước cạnh; action/state mới có hiệu lực sau cạnh. Hàng trên ưu tiên hơn hàng dưới. `true` là default; không tự tạo ack hoặc memory write khi chờ.

Fault runtime ưu tiên issue/commit; abort_req ưu tiên fault và mọi command; bus reset ưu tiên tất cả. Soft reset giữ AXI B/R đã phát. Frontend ABORT_SEND phát abort_req đúng một clock, không giữ cao và làm executor reset mãi.

## frontend

Initial state: `FREE`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `bus_reset` | FREE | clear_bus_and_core_tokens |
| ALL | `soft_reset` | ABORT_SEND | discard_normal_tokens, preserve_AXI_responses |
| FREE | `enqueue` | P0 | snapshot160, reserve |
| FREE | `true` | FREE | hold/no side effect |
| P0 | `true` | P1 | shift_token_payload |
| P1 | `core_ready` | WAIT_ACK | core_fire |
| P1 | `true` | P1 | hold/no side effect |
| WAIT_ACK | `core_ack` | FREE | capture_line_and_ack_atomic, release |
| WAIT_ACK | `true` | WAIT_ACK | hold/no side effect |
| ABORT_SEND | `true` | ABORT_WAIT | pulse_abort_req |
| ABORT_WAIT | `abort_ack` | FREE | release, clear_context_status |
| ABORT_WAIT | `true` | ABORT_WAIT | hold/no side effect |

## executor

Initial state: `RECOVER0`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `bus_reset` | RECOVER0 | flush_context_valid |
| ALL | `abort_req` | RECOVER0 | suppress_write, flush_context_valid, mark_abort_pending |
| RECOVER0 | `true` | RECOVER1 | tile_reset, suppress_write |
| RECOVER1 | `true` | IDLE | abort_ack_if_pending |
| IDLE | `bad_command` | IDLE | ack_error |
| IDLE | `cmd_cfg` | CFG_WAIT | decode_fire, invalidate_context |
| IDLE | `cmd_start & !start_ok` | IDLE | ack_error, done_error, cycles_zero |
| IDLE | `cmd_start & identity` | IDLE | ack_ok, done_ok, cycles_zero |
| IDLE | `cmd_start` | TILE_RESET | ack_ok, start_cycles, launch_tile_reset |
| IDLE | `cmd_load` | HOST_WAIT | snapshot_host_write, host_req_fire |
| IDLE | `cmd_read` | HOST_WAIT | snapshot_host_read, host_req_fire |
| IDLE | `cmd_root` | IDLE | root_write, invalidate_root_commit, ack_ok |
| IDLE | `cmd_desc` | IDLE | desc_write, ack_ok |
| IDLE | `cmd_commit` | IDLE | root_commit, ack_ok |
| IDLE | `true` | IDLE | hold/no side effect |
| CFG_WAIT | `decode_done` | IDLE | capture_params_or_error, ack_decode |
| CFG_WAIT | `true` | CFG_WAIT | hold/no side effect |
| HOST_WAIT | `fault` | ERROR_ABORT | suppress_write, invalidate_context |
| HOST_WAIT | `host_done & !host_is_read` | IDLE | ack_ok |
| HOST_WAIT | `gather_valid` | NORM_WAIT | hold/no side effect |
| HOST_WAIT | `true` | HOST_WAIT | hold/no side effect |
| NORM_WAIT | `fault` | ERROR_ABORT | suppress_write, invalidate_context |
| NORM_WAIT | `norm_valid` | IDLE | capture_norm_line, line_rsp, ack_ok |
| NORM_WAIT | `true` | NORM_WAIT | hold/no side effect |
| TILE_RESET | `true` | TILE_CONFIG | tile_reset, launch_tile_config |
| TILE_CONFIG | `true` | SETTLE | tile_config |
| SETTLE | `true` | STAGE_SETUP | prefetch_desc0 |
| STAGE_SETUP | `true` | RUN | push_context0, activate_issue0 |
| RUN | `fault` | ERROR_ABORT | suppress_write, invalidate_context |
| RUN | `all_reads_issued` | DRAIN | issue_if_due, push_next_if_due, commit_if_valid |
| RUN | `true` | RUN | issue_if_due, push_next_if_due, commit_if_valid |
| DRAIN | `fault` | ERROR_ABORT | suppress_write, invalidate_context |
| DRAIN | `drained` | IDLE | done_ok, stop_cycles |
| DRAIN | `true` | DRAIN | commit_if_valid |
| ERROR_ABORT | `true` | RECOVER0 | done_error_if_kernel_active, flush_context_valid, ack_error_if_pending, stop_kernel_active |

## host_map

Initial state: `IDLE`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `reset` | IDLE | clear_valid_selectors |
| IDLE | `req_fire` | PREP | snapshot_line |
| IDLE | `true` | IDLE | hold/no side effect |
| PREP | `true` | SERVICE | map_and_latch_phases |
| SERVICE | `last_phase & is_read` | GATHER | read_phase, capture_previous_read |
| SERVICE | `last_phase` | IDLE | write_phase, request_done |
| SERVICE | `true` | SERVICE | service_phase, capture_previous_read, advance_phase |
| GATHER | `true` | IDLE | capture_last_read, gather_valid, request_done |

## stage_ctrl

Initial state: `IDLE`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `reset` | IDLE | clear_queue_valid |
| IDLE | `kernel_begin` | ARMED | clear_kernel_counters |
| IDLE | `true` | IDLE | hold/no side effect |
| ARMED | `activate_first & issue_ready` | ACTIVE | push_context0, fire_stage0 |
| ARMED | `activate_first` | ARMED | stage_fault |
| ARMED | `true` | ARMED | hold/no side effect |
| ACTIVE | `fault` | ACTIVE | suppress_push |
| ACTIVE | `all_reads_issued` | DRAINING | pop_if_tail |
| ACTIVE | `true` | ACTIVE | fire_next_at_due_minus1, pop_if_tail |
| DRAINING | `contexts_empty` | IDLE | hold/no side effect |
| DRAINING | `true` | DRAINING | pop_if_tail |

## cfg_decode

Initial state: `IDLE`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `reset` | IDLE | clear_valid |
| IDLE | `fire` | D1 | snapshot_cfg |
| IDLE | `true` | IDLE | hold/no side effect |
| D1 | `true` | D2 | derive_logm_base_and_mode_ranges |
| D2 | `true` | D3 | derive_stages_bank_jobs |
| D3 | `true` | D4 | derive_row_jobs_plane_log |
| D4 | `true` | D5 | derive_row_exponent_and_rows |
| D5 | `true` | IDLE | done_pulse, params_valid_if_legal |

## issue

Initial state: `EMPTY`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `reset` | EMPTY | clear_tokens |
| EMPTY | `stage_fire` | WAIT_DUE | load_stage_and_counters |
| EMPTY | `true` | EMPTY | hold/no side effect |
| WAIT_DUE | `due & last_read & next_stage_fire` | WAIT_DUE | read_first_last, stage_done, load_next_stage |
| WAIT_DUE | `due & last_read` | EMPTY | read_first_last, stage_done |
| WAIT_DUE | `due` | ISSUE | read_first, advance |
| WAIT_DUE | `true` | WAIT_DUE | hold/no side effect |
| ISSUE | `last_read & next_stage_fire` | WAIT_DUE | read_last, stage_done, load_next_stage |
| ISSUE | `last_read` | EMPTY | read_last, stage_done |
| ISSUE | `true` | ISSUE | read_if_slot, advance |

## tile_lifecycle

Initial state: `COLD`.

| State | Guard theo ưu tiên | Next | Actions |
|---|---|---|---|
| ALL | `reset` | COLD | clear_inflight_valid_phase |
| COLD | `cfg_good` | READY | latch_cfg, phase_zero |
| COLD | `cfg_bad` | COLD | fault |
| COLD | `true` | COLD | hold/no side effect |
| READY | `cfg_good` | READY | latch_cfg, phase_zero |
| READY | `cfg_bad` | COLD | fault_clear_configured |
| READY | `packet_fire` | BUSY | reserve |
| READY | `true` | READY | hold/no side effect |
| BUSY | `cfg_any` | BUSY | fault_keep_old_context |
| BUSY | `becomes_empty` | READY | apply_reserve_retire |
| BUSY | `true` | BUSY | apply_reserve_retire |

## Default pulse và sticky status

| Register/nhóm | Quy tắc ưu tiên |
|---|---|
| default_pulses | ack_valid,line_rsp_valid,kernel_done,abort_ack default0 each edge; data hold or free-run under separate valid. |
| reset | bus_reset or accepted soft_reset clears done/read_complete/error; soft reset preserves AXI B/R already valid. |
| done | accepted CFG/START clears and dominates old core_done. Otherwise (old_done AND NOT clear_status) OR core_done; new completion wins over ACK. |
| read_complete | accepted CFG/START/LOAD/READ clears. Else (old_complete AND NOT clear_status) OR accepted_READ_line_response. |
| error | accepted CFG/START clears old error. Else old_error OR (core_done AND core_error) OR (accepted_core_ack AND ack_error). ACK does not clear error. |
| pending | frontend state!=FREE; abort replaces old reservation. New MMIO normal command only accepted when frontend FREE and availability guard holds. |
| busy_cycles | kernel_active is set by legal nonidentity START, cleared by DONE/error/abort. kernel_busy=kernel_active AND state in TILE_RESET/TILE_CONFIG/SETTLE/STAGE_SETUP/RUN/DRAIN/ERROR_ABORT. Increment cycles only while old kernel_active1, including DONE edge; hold on host/CFG error; identity0. |

## Guard và quy tắc datapath

- command flags là one-hot-or-zero từ cmd_fire/op; bad_command gồm reserved opcode, sai range hoặc LOAD/READ thiếu configured.
- start_ok = configured AND (identity OR (roots_committed AND đủ desc-valid)). Không kiểm primality/root value trong RTL.
- due dùng first-read timestamp của tầng so với epoch; các gap là khoảng cách giữa hai first-read timestamp, không phải khoảng chờ sau last read.
- drained = all reads issued AND context count0 AND tail_seen sạch AND mọi tile busy0 AND request/output pipeline rỗng; last write đã commit ở cạnh trước.
- stage_issue_done nghĩa last **read**; nếu có next_stage_fire cùng cạnh thì vẫn phát stage_done cho tầng cũ. Không coi nó là completion compute.
- Cấu hình native/precision/q không đổi trong RUN/DRAIN. cfg ở tile BUSY là fault, không ghi đè context cũ.
- Kernel error/abort làm invalidate context; ROOT/DESC/COMMIT trước CFG vẫn được lưu nhưng CFG tiếp theo invalidate chúng.
- ACK chỉ ở bridge: clear done/read_complete, không reset context, không vào normal queue. RESET đi abort_req.
- NORM_WAIT nhận norm_valid ở G+4, xuất core line_rsp+ack cùng cạnh; frontend tiêu thụ ở G+5 để output/read_complete/pending đổi nguyên tử.
- AXI channel FSM độc lập: AW_EMPTY→AW_FULL khi AW fire, W tương tự; commit khi cả hai full và B rỗng; B_HOLD/R_HOLD giữ đến ready. Soft abort không clear các state này; bus reset mới clear.
- Executor FSM và bộ đếm kernel cycles thuộc ft_core; stage_ctrl chỉ sở hữu descriptor, queue và stage sub-FSM. Host-map sở hữu phase/gather sub-FSM; normalizer là pipeline3 stage riêng.
- stage_valid phát đúng cạnh activation deadline; stage_ready phải1 (EMPTY hoặc last-read-lookahead). Nếu không, stage_fault và abort, không lùi lịch âm thầm.
- Epoch20 bắt đầu0 ở cạnh đầu sau TILE_CONFIG; max10 tầng × gap65535 cộng tail dưới2^20. Cycles32 ở ft_core là số đo kernel, không phải epoch counter.
