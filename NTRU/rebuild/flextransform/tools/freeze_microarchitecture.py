"""Emit locked design contracts, never implementation RTL or baseline files."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
OUT=HERE/'microarchitecture'
def p(direction,name,width=1,signed=False):return dict(direction=direction,name=name,width=width,signed=signed)
def inputs(text):
    return [p('input',a.split(':')[0],int(a.split(':')[1]) if ':' in a else 1) for a in text.split()]
def outputs(text):
    return [dict(x,direction='output') for x in inputs(text)]
def mod(ins,outs,reset=True):return inputs('clk'+(' rst' if reset else '')+' '+ins)+outputs(outs)

def ports():
    normal_in='cmd_valid cmd_op:4 cmd_payload:160 abort_req'
    normal_out='cmd_ready ack_valid ack_error abort_ack line_rsp_valid line_rsp_data:128 kernel_busy kernel_done kernel_error kernel_cycles:32 cfg_available load_available read_available'
    m={
      'ft_core':mod(normal_in,normal_out),
      'ft_cmd_frontend':mod('mmio_valid mmio_op:4 mmio_payload:160 soft_reset core_cmd_ready core_ack_valid core_ack_error core_abort_ack core_line_valid core_line_data:128 core_busy core_done core_error core_cycles:32 core_cfg_available core_load_available core_read_available clear_status',
          'mmio_ready cmd_valid cmd_op:4 cmd_payload:160 abort_req pending done_sticky error_sticky read_complete output_line:128 cycles:32 cfg_ready load_ready read_ready'),
      'ft_cfg_decode':mod('cfg_valid cfg_word:32 q:32 qi:32','cfg_ready params_valid cfg_ctx:128 cfg_done cfg_error'),
      'ft_stage_ctrl':mod('kernel_begin epoch_reset activate_first cfg_ctx:128 desc_we desc_stage:4 desc_data:46 issue_stage_ready issue_stage_done done_stage:4 tail_commit:16 fault',
          'stage_valid stage_id:4 stage_desc:46 stage_due:20 epoch:20 write_context_credit write_ctx_valid write_ctx:36 all_reads_issued contexts_empty stage_fault'),
      'ft_issue_ctrl':mod('stage_valid stage_id:4 stage_desc:46 stage_due:20 epoch:20 cfg_ctx:128 write_context_credit epoch_run',
          'stage_ready rd_issue active_mask:16 k:5 plane:3 beat:3 src_buf internal first stage_issue_done done_stage:4'),
      'ft_fft_program':mod('cfg_ctx:128 accepted_first accepted_mask:16',
          'prog_valid prog_product:2 prog_step:4 prog_mask:16'),
      'ft_data_mem':mod('ren:32 raddr:256 wen:32 waddr:256 wdata:1024','rdata:1024 rvalid:32'),
      'ft_root_mem':mod('compute_ren:16 compute_addr:9 host_we dest:16 addr:9 data:32','root_data:512 root_valid:16'),
      'ft_cg_addr':mod('cfg_ctx:128 read_stage:4 read_k:5 read_plane:3 read_beat:3 read_buf read_internal write_ctx:36 out_tag:8',
          'rd_row0:8 rd_row1:8 wr_row0:8 wr_row1:8 route_near route_swap route_far route_dummy root_addr:9'),
      'ft_cg_route':mod('bank_data:1024 read_meta:30 read_valid tile_data:1024 write_ctx:36 out_tag:8 cfg_ctx:128',
          'tile_x:512 tile_y:512 req_meta:30 req_valid routed_wdata:1024',False),
      'ft_writeback':mod('cfg_ctx:128 write_ctx_valid write_ctx:36 tile_valid:16 tile_data:1024 tile_tag:128 tile_bf_last:16 wr_row0:8 wr_row1:8 routed_wdata:1024 abort_req',
          'wen:32 waddr:256 wdata:1024 tail_commit:16 fault out_tag:8'),
      'ft_host_map':mod('req_valid is_read line:10 data:128 cfg_ctx:128 bank_rdata:1024 bank_rvalid:32',
          'req_ready ren:32 raddr:256 wen:32 waddr:256 wdata:1024 gather_valid gather_data:128 request_done fault'),
      'ft_read_normalize':mod('in_valid line_data:128 fmt:2 shift:4 normalize','out_valid data:128'),
      'ft_tile':mod('cfg_valid cfg_mode:2 cfg_inverse cfg_native cfg_fmt:2 cfg_q:32 cfg_qinv:32 req_valid req_data:64 req_root:32 req_tag:8 req_pairing req_first prog_valid prog_product:2 prog_step:4',
          'req_ready rsp_valid rsp_data:64 rsp_tag:8 rsp_bf_last busy fault'),
      'ft_leaf_array':mod('a:64 b:64 a_signed:4 b_signed:4','raw_p:132 fused_p:65',False),
      'ft_addsub':mod('in_valid a:32 b:32 q:32 ci bi split16 plain fa:32 fb:32 wa:32 wb:32 fci wci',
          'out_valid s:32 d:32 co_now bo_now fs:33 ws:33'),
      'ft_reduce_or_sum':mod('fft_mode split16 u_bus:34 q_word:32 fft_a:32 fft_b:32 fft_ci',
          'result:32 fft_sum:33 underflow:2',False),
      'ft_mont_pipe':mod('cfg_mode:2 q_word:32 qi_word:32 packet_valid group pairing operand:32 root:32 side:32 tag:8 alloc_addr:4 head_addr:4 side_rd:42 fused_p:65 raw_p:132 corrected:32',
          'leaf_a:64 leaf_b:64 leaf_valid:4 u_valid u_bus:34 side_we side_wa:4 side_wd:42 side_re side_ra:4 corr_valid corr_data:32 corr_side:32 corr_tag:8 corr_pairing fault'),
      'ft_tile_state':mod('fmt:2 alloc free_buf free_buf_id:3 ntt_reserve ntt_release '+
          'side_we side_wa:4 side_wd:42 side_ra:4 operand_we operand_wa:4 operand_wd:32 operand_ra:4 root_we root_wa:4 root_wd:32 root_ra:4 operand_sum_we operand_sum_wa:3 operand_sum_wd:32 operand_sum_ra:3 root_sum_we root_sum_wa:3 root_sum_wd:32 root_sum_ra:3 partial_we partial_wa:2 partial_wd:32 partial_ra:2',
          'alloc_ready alloc_buf:3 ntt_alloc_addr:4 ntt_head_addr:4 fft_count:4 side_count:5 side_rd:42 operand_rd:32 root_rd:32 operand_sum_rd:32 root_sum_rd:32 partial_rd:32 fault'),
      'ft_fft_accum':mod('launch_valid launch_meta:10 fused_p:65 native fmt:2',
          'limb_valid limb_data:32 limb_meta:7'),
      'ft_fft_combine':mod('limb_valid limb_data:32 limb_meta:7 side_rd:42 partial_rd:32 c4_sum:33 fmt:2',
          'c4_valid c4_a:32 c4_b:32 c4_ci side_ra:4 partial_ra:2 partial_we partial_wa:2 partial_wd:32 t_valid t_data:32 t_side:32 t_tag:8 t_last release_buf release_id:3'),
      'ft_native_align':mod('native inverse fmt:2 raw_valid raw_xy:64 raw_root:32 raw_tag:8 raw_buf:3 raw_beat:3 raw_first post_valid post_sum:32 post_diff:32 post_root:32 post_tag:8 post_buf:3 post_beat:3 post_first',
          'biased_xy:64 aligned_valid aligned_side:32 aligned_operand:32 aligned_root:32 aligned_tag:8 aligned_buf:3 aligned_beat:3 aligned_first')
    }
    axi=inputs('aclk aresetn s_axi_awaddr:12 s_axi_awprot:3 s_axi_awvalid s_axi_wdata:32 s_axi_wstrb:4 s_axi_wvalid s_axi_bready s_axi_araddr:12 s_axi_arprot:3 s_axi_arvalid s_axi_rready')+outputs('s_axi_awready s_axi_wready s_axi_bresp:2 s_axi_bvalid s_axi_arready s_axi_rdata:32 s_axi_rresp:2 s_axi_rvalid')
    m['ft_axil_top']=axi
    for name in ('ft_cg_addr','ft_cg_route','ft_reduce_or_sum'):
        m[name]=[x for x in m[name] if x['name'] not in ('clk','rst')]
    # Arithmetic products are bit patterns; the MAC state itself is signed68.
    return dict(schema_version=1,contract='0.2',ports=m,
                rules=['Vector lane t occupies [t*W+:W].','Ports are bit patterns; sign-select forms signed17 leaf operands, signed extension65 and MAC68. Carry/residue paths unsigned.',
                       'No inout, no rsp_ready on tile, one physical owner per state.',
                       'ft_cg_route outputs are combinational; core owns the route/request register.',
                       'Memory reset clears rvalid only; data/arrays have no reset.'])

def timing():
    steps={1:[(0,0)],2:[(0,0),(0,1),(1,0),(1,1)],4:[(0,0),(0,1),(1,0),(0,2),(1,1),(2,0),(0,3),(1,2),(2,1),(3,0),(1,3),(2,2),(3,1),(2,3),(3,2)]}
    profiles={}
    for L in [1,2,4]:
        K=len(steps[L]);H={1:7,2:9,4:13}[L]
        for inv in (0,1):
            for native in ((0,1) if L==2 else (0,)):
                h=H+2*int(native and inv);events=[];outputs=[]
                for product in range(3):
                    for step,(i,j) in enumerate(steps[L]):
                        col=i+j;last=step==K-1 or sum(steps[L][step+1])!=col
                        emit=last and (L==1 or (L==2 and col>=1) or (L==4 and col>=2))
                        limb=0 if L==1 else col-(1 if L==2 else 2)
                        launch=h+product*K+step
                        e=dict(product=product,step=step,i=i,j=j,column_last=last,emit=emit,
                               limb=limb if emit else None,early=launch-1,launch=launch,raw=launch+3,fused=launch+5,mac=launch+6,combine=launch+7)
                        if emit and product>0:
                            e['rsp']=launch+8+(not inv);e['commit']=e['rsp']+1
                            outputs.append(dict(product=product,limb=limb,rsp=e['rsp'],commit=e['commit']))
                        events.append(e)
                name=f'fft{32*L}_{"gs" if inv else "ct"}'+('_native' if native else '')
                profiles[name]=dict(L=L,fmt={1:0,2:1,4:2}[L],inverse=inv,native=native,period=3*K,
                    buffer_depth={1:8,2:4,4:2}[L],input_edges=list(range(2*L)),
                    operand_write_edges=[2+b+2*int(native and inv) for b in range(2*L)],
                    sum_write_edges=[4+2*k+2*int(native and inv) for k in range(L)],
                    product_start=h,steps=events,outputs=outputs,
                    release_edge=max(e['combine'] for e in events if e['emit'] and e['product']==2))
    return dict(schema_version=1,contract='0.2',edge_convention='C0 is tile request fire at edge; after-edge outputs consumed at following edge',
        read_to_tile_accept=2,tile_rsp_to_bank_commit=1,extra_write_data_registers=0,
        phase_origin='First edge after tile CFG is phase0; phi_req=(edge-origin)%3; phi_launch=(edge-origin-2)%3.',
        ntt=dict(operand=2,launches=[2,7,12],raw_returns=[5,10,15],fused_returns=[7,12,17],side_write=2,
                 history_write=8,history_ready=17,side_read=19,u=18,correction=19,rsp_gs=20,rsp_ct=21,commit_gs=21,commit_ct=22,side_depth=16,
                 packed_accept_phases=[0,1],scalar_accept_phases=[0]),
        fft=profiles,
        host=dict(prepare_edges=1,max_service_phases=4,read_last_to_gather=1,gather_to_carry=1,gather_to_sum=2,gather_to_shift=3,gather_to_core_rsp=4,gather_to_frontend_capture=5),
        start=dict(start_relative_phase_origin=-3,context0_push=1,first_read_min=2,done_after_last_commit=1),
        cfg=dict(decode_edges=5,core_capture_edge=6))

def row(when,to,actions=()):return dict(when=when,to=to,actions=list(actions))
def fsm():
    machines={}
    machines['frontend']=dict(initial='FREE',global_rules=[row('bus_reset','FREE',['clear_bus_and_core_tokens']),row('soft_reset','ABORT_SEND',['discard_normal_tokens','preserve_AXI_responses'])],states={
      'FREE':[row('enqueue','P0',['snapshot160','reserve']),row('true','FREE')],
      'P0':[row('true','P1',['shift_token_payload'])],
      'P1':[row('core_ready','WAIT_ACK',['core_fire']),row('true','P1')],
      'WAIT_ACK':[row('core_ack','FREE',['capture_line_and_ack_atomic','release']),row('true','WAIT_ACK')],
      'ABORT_SEND':[row('true','ABORT_WAIT',['pulse_abort_req'])],
      'ABORT_WAIT':[row('abort_ack','FREE',['release','clear_context_status']),row('true','ABORT_WAIT')]
    })
    machines['executor']=dict(initial='RECOVER0',global_rules=[row('bus_reset','RECOVER0',['flush_context_valid']),row('abort_req','RECOVER0',['suppress_write','flush_context_valid','mark_abort_pending'])],states={
      'RECOVER0':[row('true','RECOVER1',['tile_reset','suppress_write'])],
      'RECOVER1':[row('true','IDLE',['abort_ack_if_pending'])],
      'IDLE':[row('bad_command','IDLE',['ack_error']),row('cmd_cfg','CFG_WAIT',['decode_fire','invalidate_context']),
          row('cmd_start & !start_ok','IDLE',['ack_error','done_error','cycles_zero']),
          row('cmd_start & identity','IDLE',['ack_ok','done_ok','cycles_zero']),
          row('cmd_start','TILE_RESET',['ack_ok','start_cycles','launch_tile_reset']),
          row('cmd_load','HOST_PREP',['snapshot_host_write']),row('cmd_read','HOST_PREP',['snapshot_host_read']),
          row('cmd_root','IDLE',['root_write','invalidate_root_commit','ack_ok']),row('cmd_desc','IDLE',['desc_write','ack_ok']),
          row('cmd_commit','IDLE',['root_commit','ack_ok']),row('true','IDLE')],
      'CFG_WAIT':[row('decode_done','IDLE',['capture_params_or_error','ack_decode']),row('true','CFG_WAIT')],
      'HOST_WAIT':[row('host_done & !host_is_read','IDLE',['ack_ok']),row('gather_valid','NORM_WAIT'),row('true','HOST_WAIT')],
      'NORM_WAIT':[row('norm_valid','IDLE',['capture_norm_line','line_rsp','ack_ok']),row('true','NORM_WAIT')],
      'TILE_RESET':[row('true','TILE_CONFIG',['tile_reset','launch_tile_config'])],
      'TILE_CONFIG':[row('true','SETTLE',['tile_config'])],
      'SETTLE':[row('true','STAGE_SETUP',['prefetch_desc0'])],
      'STAGE_SETUP':[row('true','RUN',['push_context0','activate_issue0'])],
      'RUN':[row('fault','ERROR_ABORT',['suppress_write','invalidate_context']),row('all_reads_issued','DRAIN',['issue_if_due','push_next_if_due','commit_if_valid']),row('true','RUN',['issue_if_due','push_next_if_due','commit_if_valid'])],
      'DRAIN':[row('fault','ERROR_ABORT',['suppress_write','invalidate_context']),row('drained','IDLE',['done_ok','stop_cycles']),row('true','DRAIN',['commit_if_valid'])],
      'ERROR_ABORT':[row('true','RECOVER0',['done_error_if_kernel_active','flush_context_valid','ack_error_if_pending','stop_kernel_active'])]
    })
    # Host faults also enter the same abort path before any phase write.
    for state in ('HOST_WAIT','NORM_WAIT'):
        machines['executor']['states'][state].insert(0,row('fault','ERROR_ABORT',['suppress_write','invalidate_context']))
    for r in machines['executor']['states']['IDLE']:
        if r['to']=='HOST_PREP':r['to']='HOST_WAIT';r['actions'].append('host_req_fire')
    machines['host_map']=dict(initial='IDLE',global_rules=[row('reset','IDLE',['clear_valid_selectors'])],states={
      'IDLE':[row('req_fire','PREP',['snapshot_line']),row('true','IDLE')],
      'PREP':[row('true','SERVICE',['map_and_latch_phases'])],
      'SERVICE':[row('last_phase & is_read','GATHER',['read_phase','capture_previous_read']),row('last_phase','IDLE',['write_phase','request_done']),row('true','SERVICE',['service_phase','capture_previous_read','advance_phase'])],
      'GATHER':[row('true','IDLE',['capture_last_read','gather_valid','request_done'])]
    })
    machines['stage_ctrl']=dict(initial='IDLE',global_rules=[row('reset','IDLE',['clear_queue_valid'])],states={
      'IDLE':[row('kernel_begin','ARMED',['clear_kernel_counters']),row('true','IDLE')],
      'ARMED':[row('activate_first & issue_ready','ACTIVE',['push_context0','fire_stage0']),row('activate_first','ARMED',['stage_fault']),row('true','ARMED')],
      'ACTIVE':[row('fault','ACTIVE',['suppress_push']),row('all_reads_issued','DRAINING',['pop_if_tail']),row('true','ACTIVE',['fire_next_at_due_minus1','pop_if_tail'])],
      'DRAINING':[row('contexts_empty','IDLE'),row('true','DRAINING',['pop_if_tail'])]
    })
    machines['cfg_decode']=dict(initial='IDLE',global_rules=[row('reset','IDLE',['clear_valid'])],states={
      'IDLE':[row('fire','D1',['snapshot_cfg']),row('true','IDLE')],
      'D1':[row('true','D2',['derive_logm_base_and_mode_ranges'])],
      'D2':[row('true','D3',['derive_stages_bank_jobs'])],
      'D3':[row('true','D4',['derive_row_jobs_plane_log'])],
      'D4':[row('true','D5',['derive_row_exponent_and_rows'])],
      'D5':[row('true','IDLE',['done_pulse','params_valid_if_legal'])]
    })
    machines['issue']=dict(initial='EMPTY',global_rules=[row('reset','EMPTY',['clear_tokens'])],states={
      'EMPTY':[row('stage_fire','WAIT_DUE',['load_stage_and_counters']),row('true','EMPTY')],
      'WAIT_DUE':[row('due & last_read & next_stage_fire','WAIT_DUE',['read_first_last','stage_done','load_next_stage']),row('due & last_read','EMPTY',['read_first_last','stage_done']),row('due','ISSUE',['read_first','advance']),row('true','WAIT_DUE')],
      'ISSUE':[row('last_read & next_stage_fire','WAIT_DUE',['read_last','stage_done','load_next_stage']),row('last_read','EMPTY',['read_last','stage_done']),row('true','ISSUE',['read_if_slot','advance'])]
    })
    machines['tile_lifecycle']=dict(initial='COLD',global_rules=[row('reset','COLD',['clear_inflight_valid_phase'])],states={
      'COLD':[row('cfg_good','READY',['latch_cfg','phase_zero']),row('cfg_bad','COLD',['fault']),row('true','COLD')],
      'READY':[row('cfg_good','READY',['latch_cfg','phase_zero']),row('cfg_bad','COLD',['fault_clear_configured']),row('packet_fire','BUSY',['reserve']),row('true','READY')],
      'BUSY':[row('cfg_any','BUSY',['fault_keep_old_context']),row('becomes_empty','READY',['apply_reserve_retire']),row('true','BUSY',['apply_reserve_retire'])]
    })
    return dict(schema_version=1,contract='0.2',priority='Global rules first, then first true state rule; actions at edge using old state. Default hold has no command side effect.',machines=machines,
        status_update_rules={
          'default_pulses':'ack_valid,line_rsp_valid,kernel_done,abort_ack default0 each edge; data hold or free-run under separate valid.',
          'reset':'bus_reset or accepted soft_reset clears done/read_complete/error; soft reset preserves AXI B/R already valid.',
          'done':'accepted CFG/START clears and dominates old core_done. Otherwise (old_done AND NOT clear_status) OR core_done; new completion wins over ACK.',
          'read_complete':'accepted CFG/START/LOAD/READ clears. Else (old_complete AND NOT clear_status) OR accepted_READ_line_response.',
          'error':'accepted CFG/START clears old error. Else old_error OR (core_done AND core_error) OR (accepted_core_ack AND ack_error). ACK does not clear error.',
          'pending':'frontend state!=FREE; abort replaces old reservation. New MMIO normal command only accepted when frontend FREE and availability guard holds.',
          'busy_cycles':'kernel_active is set by legal nonidentity START, cleared by DONE/error/abort. kernel_busy=kernel_active AND state in TILE_RESET/TILE_CONFIG/SETTLE/STAGE_SETUP/RUN/DRAIN/ERROR_ABORT. Increment cycles only while old kernel_active1, including DONE edge; hold on host/CFG error; identity0.'})

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,fn in [('ports',ports),('timing',timing),('fsm',fsm)]:
        (OUT/(name+'.json')).write_text(json.dumps(fn(),indent=2)+'\n',encoding='utf-8')
    md=['# 08 — Port đã khóa, contract 0.2','','Sinh từ `microarchitecture/ports.json` bằng tools/freeze_microarchitecture.py. Tất cả width là số bit chính xác; bit pattern unsigned ở port, sign-extension thực hiện theo numerical contract. Không có module implementation mới trong file này.','',
        'Reset active-high synchronous cho module có rst; ft_axil_top dùng aresetn. ft_cg_addr/ft_cg_route/ft_reduce_or_sum là combinational, không có clock/reset. Data RAM/SRL/data FF không reset nội dung.','']
    for name,ps in ports()['ports'].items():
        md += ['## '+name,'','| Port | Direction | Bits |','|---|---|---:|']
        md += [f'| `{a["name"]}` | {a["direction"]} | {a["width"]} |' for a in ps]
        md += ['']
    md += ['## Width nội bộ bắt buộc','','- C0 sum33, C1 difference34, C2 correction35, C3 correction34.','- U bus34: packed `{U_hi17,U_lo17}`; scalar `{0,U33}`.','- C4 là một adder36 có mux operand; equations chính xác ở spec09.','- Leaf signed extension17, full product34 rồi raw33; fused65; MAC signed68.','- side pointer4/count5; FFT buffer index3/count4; context pointer4/count5; stage4; k5; plane3; request tag8.','- FFT limb result metadata7 = `{buffer3,product2,limb2}`; MAC launch metadata10 giữ như design.json.','- read_meta30 = `{active_mask16,tag8,near,swap,far,dummy,pairing,first}`; ft_cg_route không chứa FF, ft_core chốt output route ở C1.','- C4 và C2/C3 có đúng một physical owner, không instantiate một bản theo mỗi mode.','']
    (HERE/'spec/08_locked_ports.md').write_text('\n'.join(md),encoding='utf-8')
    md=['# 10 — FSM đã khóa, contract 0.2','','Sinh từ `microarchitecture/fsm.json`. Mỗi hàng dùng giá trị trước cạnh; action/state mới có hiệu lực sau cạnh. Hàng trên ưu tiên hơn hàng dưới. `true` là default; không tự tạo ack hoặc memory write khi chờ.','',
        'Fault runtime ưu tiên issue/commit; abort_req ưu tiên fault và mọi command; bus reset ưu tiên tất cả. Soft reset giữ AXI B/R đã phát. Frontend ABORT_SEND phát abort_req đúng một clock, không giữ cao và làm executor reset mãi.','']
    for name,m in fsm()['machines'].items():
        md+=['## '+name,'','Initial state: `'+m['initial']+'`.','','| State | Guard theo ưu tiên | Next | Actions |','|---|---|---|---|']
        for a in m['global_rules']:md.append(f'| ALL | `{a["when"]}` | {a["to"]} | '+', '.join(a['actions'])+' |')
        for state,rs in m['states'].items():
            for a in rs:md.append(f'| {state} | `{a["when"]}` | {a["to"]} | '+(', '.join(a['actions']) or 'hold/no side effect')+' |')
        md+=['']
    md+=['## Default pulse và sticky status','','| Register/nhóm | Quy tắc ưu tiên |','|---|---|']
    md += [f'| {name} | {rule} |' for name,rule in fsm()['status_update_rules'].items()]
    md+=['']
    md+=['## Guard và quy tắc datapath','','- command flags là one-hot-or-zero từ cmd_fire/op; bad_command gồm reserved opcode, sai range hoặc LOAD/READ thiếu configured.','- start_ok = configured AND (identity OR (roots_committed AND đủ desc-valid)). Không kiểm primality/root value trong RTL.','- due dùng first-read timestamp của tầng so với epoch; các gap là khoảng cách giữa hai first-read timestamp, không phải khoảng chờ sau last read.','- drained = all reads issued AND context count0 AND tail_seen sạch AND mọi tile busy0 AND request/output pipeline rỗng; last write đã commit ở cạnh trước.','- stage_issue_done nghĩa last **read**; nếu có next_stage_fire cùng cạnh thì vẫn phát stage_done cho tầng cũ. Không coi nó là completion compute.','- Cấu hình native/precision/q không đổi trong RUN/DRAIN. cfg ở tile BUSY là fault, không ghi đè context cũ.','- Kernel error/abort làm invalidate context; ROOT/DESC/COMMIT trước CFG vẫn được lưu nhưng CFG tiếp theo invalidate chúng.','- ACK chỉ ở bridge: clear done/read_complete, không reset context, không vào normal queue. RESET đi abort_req.','- NORM_WAIT nhận norm_valid ở G+4, xuất core line_rsp+ack cùng cạnh; frontend tiêu thụ ở G+5 để output/read_complete/pending đổi nguyên tử.','- AXI channel FSM độc lập: AW_EMPTY→AW_FULL khi AW fire, W tương tự; commit khi cả hai full và B rỗng; B_HOLD/R_HOLD giữ đến ready. Soft abort không clear các state này; bus reset mới clear.','- Executor FSM và bộ đếm kernel cycles thuộc ft_core; stage_ctrl chỉ sở hữu descriptor, queue và stage sub-FSM. Host-map sở hữu phase/gather sub-FSM; normalizer là pipeline3 stage riêng.','- stage_valid phát đúng cạnh activation deadline; stage_ready phải1 (EMPTY hoặc last-read-lookahead). Nếu không, stage_fault và abort, không lùi lịch âm thầm.','- Epoch20 bắt đầu0 ở cạnh đầu sau TILE_CONFIG; max10 tầng × gap65535 cộng tail dưới2^20. Cycles32 ở ft_core là số đo kernel, không phải epoch counter.','']
    (HERE/'spec/10_locked_fsm.md').write_text('\n'.join(md),encoding='utf-8')
    print('MICROARCH_CONTRACTS_EMITTED',len(ports()['ports']),'modules')
if __name__=='__main__':main()
