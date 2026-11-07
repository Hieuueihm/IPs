# 08 — Port đã khóa, contract 0.2

Sinh từ `microarchitecture/ports.json` bằng tools/freeze_microarchitecture.py. Tất cả width là số bit chính xác; bit pattern unsigned ở port, sign-extension thực hiện theo numerical contract. Không có module implementation mới trong file này.

Reset active-high synchronous cho module có rst; ft_axil_top dùng aresetn. ft_cg_addr/ft_cg_route/ft_reduce_or_sum là combinational, không có clock/reset. Data RAM/SRL/data FF không reset nội dung.

## ft_core

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cmd_valid` | input | 1 |
| `cmd_op` | input | 4 |
| `cmd_payload` | input | 160 |
| `abort_req` | input | 1 |
| `cmd_ready` | output | 1 |
| `ack_valid` | output | 1 |
| `ack_error` | output | 1 |
| `abort_ack` | output | 1 |
| `line_rsp_valid` | output | 1 |
| `line_rsp_data` | output | 128 |
| `kernel_busy` | output | 1 |
| `kernel_done` | output | 1 |
| `kernel_error` | output | 1 |
| `kernel_cycles` | output | 32 |
| `cfg_available` | output | 1 |
| `load_available` | output | 1 |
| `read_available` | output | 1 |

## ft_cmd_frontend

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `mmio_valid` | input | 1 |
| `mmio_op` | input | 4 |
| `mmio_payload` | input | 160 |
| `soft_reset` | input | 1 |
| `core_cmd_ready` | input | 1 |
| `core_ack_valid` | input | 1 |
| `core_ack_error` | input | 1 |
| `core_abort_ack` | input | 1 |
| `core_line_valid` | input | 1 |
| `core_line_data` | input | 128 |
| `core_busy` | input | 1 |
| `core_done` | input | 1 |
| `core_error` | input | 1 |
| `core_cycles` | input | 32 |
| `core_cfg_available` | input | 1 |
| `core_load_available` | input | 1 |
| `core_read_available` | input | 1 |
| `clear_status` | input | 1 |
| `mmio_ready` | output | 1 |
| `cmd_valid` | output | 1 |
| `cmd_op` | output | 4 |
| `cmd_payload` | output | 160 |
| `abort_req` | output | 1 |
| `pending` | output | 1 |
| `done_sticky` | output | 1 |
| `error_sticky` | output | 1 |
| `read_complete` | output | 1 |
| `output_line` | output | 128 |
| `cycles` | output | 32 |
| `cfg_ready` | output | 1 |
| `load_ready` | output | 1 |
| `read_ready` | output | 1 |

## ft_cfg_decode

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cfg_valid` | input | 1 |
| `cfg_word` | input | 32 |
| `q` | input | 32 |
| `qi` | input | 32 |
| `cfg_ready` | output | 1 |
| `params_valid` | output | 1 |
| `cfg_ctx` | output | 128 |
| `cfg_done` | output | 1 |
| `cfg_error` | output | 1 |

## ft_stage_ctrl

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `kernel_begin` | input | 1 |
| `epoch_reset` | input | 1 |
| `activate_first` | input | 1 |
| `cfg_ctx` | input | 128 |
| `desc_we` | input | 1 |
| `desc_stage` | input | 4 |
| `desc_data` | input | 46 |
| `issue_stage_ready` | input | 1 |
| `issue_stage_done` | input | 1 |
| `done_stage` | input | 4 |
| `tail_commit` | input | 16 |
| `fault` | input | 1 |
| `stage_valid` | output | 1 |
| `stage_id` | output | 4 |
| `stage_desc` | output | 46 |
| `stage_due` | output | 20 |
| `epoch` | output | 20 |
| `write_context_credit` | output | 1 |
| `write_ctx_valid` | output | 1 |
| `write_ctx` | output | 36 |
| `all_reads_issued` | output | 1 |
| `contexts_empty` | output | 1 |
| `stage_fault` | output | 1 |

## ft_issue_ctrl

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `stage_valid` | input | 1 |
| `stage_id` | input | 4 |
| `stage_desc` | input | 46 |
| `stage_due` | input | 20 |
| `epoch` | input | 20 |
| `cfg_ctx` | input | 128 |
| `write_context_credit` | input | 1 |
| `epoch_run` | input | 1 |
| `stage_ready` | output | 1 |
| `rd_issue` | output | 1 |
| `active_mask` | output | 16 |
| `k` | output | 5 |
| `plane` | output | 3 |
| `beat` | output | 3 |
| `src_buf` | output | 1 |
| `internal` | output | 1 |
| `first` | output | 1 |
| `stage_issue_done` | output | 1 |
| `done_stage` | output | 4 |

## ft_fft_program

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cfg_ctx` | input | 128 |
| `accepted_first` | input | 1 |
| `accepted_mask` | input | 16 |
| `prog_valid` | output | 1 |
| `prog_product` | output | 2 |
| `prog_step` | output | 4 |
| `prog_mask` | output | 16 |

## ft_data_mem

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `ren` | input | 32 |
| `raddr` | input | 256 |
| `wen` | input | 32 |
| `waddr` | input | 256 |
| `wdata` | input | 1024 |
| `rdata` | output | 1024 |
| `rvalid` | output | 32 |

## ft_root_mem

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `compute_ren` | input | 16 |
| `compute_addr` | input | 9 |
| `host_we` | input | 1 |
| `dest` | input | 16 |
| `addr` | input | 9 |
| `data` | input | 32 |
| `root_data` | output | 512 |
| `root_valid` | output | 16 |

## ft_cg_addr

| Port | Direction | Bits |
|---|---|---:|
| `cfg_ctx` | input | 128 |
| `read_stage` | input | 4 |
| `read_k` | input | 5 |
| `read_plane` | input | 3 |
| `read_beat` | input | 3 |
| `read_buf` | input | 1 |
| `read_internal` | input | 1 |
| `write_ctx` | input | 36 |
| `out_tag` | input | 8 |
| `rd_row0` | output | 8 |
| `rd_row1` | output | 8 |
| `wr_row0` | output | 8 |
| `wr_row1` | output | 8 |
| `route_near` | output | 1 |
| `route_swap` | output | 1 |
| `route_far` | output | 1 |
| `route_dummy` | output | 1 |
| `root_addr` | output | 9 |

## ft_cg_route

| Port | Direction | Bits |
|---|---|---:|
| `bank_data` | input | 1024 |
| `read_meta` | input | 30 |
| `read_valid` | input | 1 |
| `tile_data` | input | 1024 |
| `write_ctx` | input | 36 |
| `out_tag` | input | 8 |
| `cfg_ctx` | input | 128 |
| `tile_x` | output | 512 |
| `tile_y` | output | 512 |
| `req_meta` | output | 30 |
| `req_valid` | output | 1 |
| `routed_wdata` | output | 1024 |

## ft_writeback

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cfg_ctx` | input | 128 |
| `write_ctx_valid` | input | 1 |
| `write_ctx` | input | 36 |
| `tile_valid` | input | 16 |
| `tile_data` | input | 1024 |
| `tile_tag` | input | 128 |
| `tile_bf_last` | input | 16 |
| `wr_row0` | input | 8 |
| `wr_row1` | input | 8 |
| `routed_wdata` | input | 1024 |
| `abort_req` | input | 1 |
| `wen` | output | 32 |
| `waddr` | output | 256 |
| `wdata` | output | 1024 |
| `tail_commit` | output | 16 |
| `fault` | output | 1 |
| `out_tag` | output | 8 |

## ft_host_map

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `req_valid` | input | 1 |
| `is_read` | input | 1 |
| `line` | input | 10 |
| `data` | input | 128 |
| `cfg_ctx` | input | 128 |
| `bank_rdata` | input | 1024 |
| `bank_rvalid` | input | 32 |
| `req_ready` | output | 1 |
| `ren` | output | 32 |
| `raddr` | output | 256 |
| `wen` | output | 32 |
| `waddr` | output | 256 |
| `wdata` | output | 1024 |
| `gather_valid` | output | 1 |
| `gather_data` | output | 128 |
| `request_done` | output | 1 |
| `fault` | output | 1 |

## ft_read_normalize

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `in_valid` | input | 1 |
| `line_data` | input | 128 |
| `fmt` | input | 2 |
| `shift` | input | 4 |
| `normalize` | input | 1 |
| `out_valid` | output | 1 |
| `data` | output | 128 |

## ft_tile

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cfg_valid` | input | 1 |
| `cfg_mode` | input | 2 |
| `cfg_inverse` | input | 1 |
| `cfg_native` | input | 1 |
| `cfg_fmt` | input | 2 |
| `cfg_q` | input | 32 |
| `cfg_qinv` | input | 32 |
| `req_valid` | input | 1 |
| `req_data` | input | 64 |
| `req_root` | input | 32 |
| `req_tag` | input | 8 |
| `req_pairing` | input | 1 |
| `req_first` | input | 1 |
| `prog_valid` | input | 1 |
| `prog_product` | input | 2 |
| `prog_step` | input | 4 |
| `req_ready` | output | 1 |
| `rsp_valid` | output | 1 |
| `rsp_data` | output | 64 |
| `rsp_tag` | output | 8 |
| `rsp_bf_last` | output | 1 |
| `busy` | output | 1 |
| `fault` | output | 1 |

## ft_leaf_array

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `a` | input | 64 |
| `b` | input | 64 |
| `a_signed` | input | 4 |
| `b_signed` | input | 4 |
| `raw_p` | output | 132 |
| `fused_p` | output | 65 |

## ft_addsub

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `in_valid` | input | 1 |
| `a` | input | 32 |
| `b` | input | 32 |
| `q` | input | 32 |
| `ci` | input | 1 |
| `bi` | input | 1 |
| `split16` | input | 1 |
| `plain` | input | 1 |
| `fa` | input | 32 |
| `fb` | input | 32 |
| `wa` | input | 32 |
| `wb` | input | 32 |
| `fci` | input | 1 |
| `wci` | input | 1 |
| `out_valid` | output | 1 |
| `s` | output | 32 |
| `d` | output | 32 |
| `co_now` | output | 1 |
| `bo_now` | output | 1 |
| `fs` | output | 33 |
| `ws` | output | 33 |

## ft_reduce_or_sum

| Port | Direction | Bits |
|---|---|---:|
| `fft_mode` | input | 1 |
| `split16` | input | 1 |
| `u_bus` | input | 34 |
| `q_word` | input | 32 |
| `fft_a` | input | 32 |
| `fft_b` | input | 32 |
| `fft_ci` | input | 1 |
| `result` | output | 32 |
| `fft_sum` | output | 33 |
| `underflow` | output | 2 |

## ft_mont_pipe

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `cfg_mode` | input | 2 |
| `q_word` | input | 32 |
| `qi_word` | input | 32 |
| `packet_valid` | input | 1 |
| `group` | input | 1 |
| `pairing` | input | 1 |
| `operand` | input | 32 |
| `root` | input | 32 |
| `side` | input | 32 |
| `tag` | input | 8 |
| `alloc_addr` | input | 4 |
| `head_addr` | input | 4 |
| `side_rd` | input | 42 |
| `fused_p` | input | 65 |
| `raw_p` | input | 132 |
| `corrected` | input | 32 |
| `leaf_a` | output | 64 |
| `leaf_b` | output | 64 |
| `leaf_valid` | output | 4 |
| `u_valid` | output | 1 |
| `u_bus` | output | 34 |
| `side_we` | output | 1 |
| `side_wa` | output | 4 |
| `side_wd` | output | 42 |
| `side_re` | output | 1 |
| `side_ra` | output | 4 |
| `corr_valid` | output | 1 |
| `corr_data` | output | 32 |
| `corr_side` | output | 32 |
| `corr_tag` | output | 8 |
| `corr_pairing` | output | 1 |
| `fault` | output | 1 |

## ft_tile_state

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `fmt` | input | 2 |
| `alloc` | input | 1 |
| `free_buf` | input | 1 |
| `free_buf_id` | input | 3 |
| `ntt_reserve` | input | 1 |
| `ntt_release` | input | 1 |
| `side_we` | input | 1 |
| `side_wa` | input | 4 |
| `side_wd` | input | 42 |
| `side_ra` | input | 4 |
| `operand_we` | input | 1 |
| `operand_wa` | input | 4 |
| `operand_wd` | input | 32 |
| `operand_ra` | input | 4 |
| `root_we` | input | 1 |
| `root_wa` | input | 4 |
| `root_wd` | input | 32 |
| `root_ra` | input | 4 |
| `operand_sum_we` | input | 1 |
| `operand_sum_wa` | input | 3 |
| `operand_sum_wd` | input | 32 |
| `operand_sum_ra` | input | 3 |
| `root_sum_we` | input | 1 |
| `root_sum_wa` | input | 3 |
| `root_sum_wd` | input | 32 |
| `root_sum_ra` | input | 3 |
| `partial_we` | input | 1 |
| `partial_wa` | input | 2 |
| `partial_wd` | input | 32 |
| `partial_ra` | input | 2 |
| `alloc_ready` | output | 1 |
| `alloc_buf` | output | 3 |
| `ntt_alloc_addr` | output | 4 |
| `ntt_head_addr` | output | 4 |
| `fft_count` | output | 4 |
| `side_count` | output | 5 |
| `side_rd` | output | 42 |
| `operand_rd` | output | 32 |
| `root_rd` | output | 32 |
| `operand_sum_rd` | output | 32 |
| `root_sum_rd` | output | 32 |
| `partial_rd` | output | 32 |
| `fault` | output | 1 |

## ft_fft_accum

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `launch_valid` | input | 1 |
| `launch_meta` | input | 10 |
| `fused_p` | input | 65 |
| `native` | input | 1 |
| `fmt` | input | 2 |
| `limb_valid` | output | 1 |
| `limb_data` | output | 32 |
| `limb_meta` | output | 7 |

## ft_fft_combine

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `limb_valid` | input | 1 |
| `limb_data` | input | 32 |
| `limb_meta` | input | 7 |
| `side_rd` | input | 42 |
| `partial_rd` | input | 32 |
| `c4_sum` | input | 33 |
| `fmt` | input | 2 |
| `c4_valid` | output | 1 |
| `c4_a` | output | 32 |
| `c4_b` | output | 32 |
| `c4_ci` | output | 1 |
| `side_ra` | output | 4 |
| `partial_ra` | output | 2 |
| `partial_we` | output | 1 |
| `partial_wa` | output | 2 |
| `partial_wd` | output | 32 |
| `t_valid` | output | 1 |
| `t_data` | output | 32 |
| `t_side` | output | 32 |
| `t_tag` | output | 8 |
| `t_last` | output | 1 |
| `release_buf` | output | 1 |
| `release_id` | output | 3 |

## ft_native_align

| Port | Direction | Bits |
|---|---|---:|
| `clk` | input | 1 |
| `rst` | input | 1 |
| `native` | input | 1 |
| `inverse` | input | 1 |
| `fmt` | input | 2 |
| `raw_valid` | input | 1 |
| `raw_xy` | input | 64 |
| `raw_root` | input | 32 |
| `raw_tag` | input | 8 |
| `raw_buf` | input | 3 |
| `raw_beat` | input | 3 |
| `raw_first` | input | 1 |
| `post_valid` | input | 1 |
| `post_sum` | input | 32 |
| `post_diff` | input | 32 |
| `post_root` | input | 32 |
| `post_tag` | input | 8 |
| `post_buf` | input | 3 |
| `post_beat` | input | 3 |
| `post_first` | input | 1 |
| `biased_xy` | output | 64 |
| `aligned_valid` | output | 1 |
| `aligned_side` | output | 32 |
| `aligned_operand` | output | 32 |
| `aligned_root` | output | 32 |
| `aligned_tag` | output | 8 |
| `aligned_buf` | output | 3 |
| `aligned_beat` | output | 3 |
| `aligned_first` | output | 1 |

## ft_axil_top

| Port | Direction | Bits |
|---|---|---:|
| `aclk` | input | 1 |
| `aresetn` | input | 1 |
| `s_axi_awaddr` | input | 12 |
| `s_axi_awprot` | input | 3 |
| `s_axi_awvalid` | input | 1 |
| `s_axi_wdata` | input | 32 |
| `s_axi_wstrb` | input | 4 |
| `s_axi_wvalid` | input | 1 |
| `s_axi_bready` | input | 1 |
| `s_axi_araddr` | input | 12 |
| `s_axi_arprot` | input | 3 |
| `s_axi_arvalid` | input | 1 |
| `s_axi_rready` | input | 1 |
| `s_axi_awready` | output | 1 |
| `s_axi_wready` | output | 1 |
| `s_axi_bresp` | output | 2 |
| `s_axi_bvalid` | output | 1 |
| `s_axi_arready` | output | 1 |
| `s_axi_rdata` | output | 32 |
| `s_axi_rresp` | output | 2 |
| `s_axi_rvalid` | output | 1 |

## Width nội bộ bắt buộc

- C0 sum33, C1 difference34, C2 correction35, C3 correction34.
- U bus34: packed `{U_hi17,U_lo17}`; scalar `{0,U33}`.
- C4 là một adder36 có mux operand; equations chính xác ở spec09.
- Leaf signed extension17, full product34 rồi raw33; fused65; MAC signed68.
- side pointer4/count5; FFT buffer index3/count4; context pointer4/count5; stage4; k5; plane3; request tag8.
- FFT limb result metadata7 = `{buffer3,product2,limb2}`; MAC launch metadata10 giữ như design.json.
- read_meta30 = `{active_mask16,tag8,near,swap,far,dummy,pairing,first}`; ft_cg_route không chứa FF, ft_core chốt output route ở C1.
- C4 và C2/C3 có đúng một physical owner, không instantiate một bản theo mỗi mode.
