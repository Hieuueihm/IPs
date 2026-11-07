// Isolated A + constant-geometry prototype, 16 identical engines, 64 DSP.
// One runtime context; host loads direction-specific roots and stage descriptors.
// Input/output natural order. Full host adapter and root cache are synthesized.
module a_cg_fast (
    input wire clk, rst,
    input wire cfg_valid,
    output wire cfg_ready,
    input wire cfg_fft, cfg_inverse, cfg_ntrugen, cfg_packed,
    input wire [2:0] cfg_jobs_log,
    input wire [1:0] cfg_fmt, cfg_hmin,
    input wire [3:0] cfg_logn,
    input wire [31:0] cfg_q, cfg_qinv,
    input wire root_we, root_commit,
    input wire [15:0] root_dest,
    input wire [8:0] root_addr,
    input wire [31:0] root_data,
    input wire desc_we,
    input wire [3:0] desc_stage,
    input wire [15:0] desc_mask,
    input wire [8:0] desc_root_base,
    input wire [4:0] desc_root_mask,
    input wire [15:0] desc_gap,
    input wire load_valid,
    output wire load_ready,
    input wire [9:0] load_line,
    input wire [127:0] load_data,
    input wire read_valid,
    output wire read_ready,
    input wire [9:0] read_line,
    output wire read_rsp_valid,
    output wire [127:0] read_data,
    input wire start,
    output wire busy,
    output wire done, error,
    output wire [31:0] cycles
);
    (* DONT_TOUCH="yes" *) reg p_cfg_fft;
    (* DONT_TOUCH="yes" *) reg p_cfg_inverse;
    (* DONT_TOUCH="yes" *) reg p_cfg_ntrugen;
    (* DONT_TOUCH="yes" *) reg p_cfg_packed;
    (* DONT_TOUCH="yes" *) reg [2:0] p_cfg_jobs_log;
    (* DONT_TOUCH="yes" *) reg [1:0] p_cfg_fmt;
    (* DONT_TOUCH="yes" *) reg [1:0] p_cfg_hmin;
    (* DONT_TOUCH="yes" *) reg [3:0] p_cfg_logn;
    (* DONT_TOUCH="yes" *) reg [31:0] p_cfg_q;
    (* DONT_TOUCH="yes" *) reg [31:0] p_cfg_qinv;
    (* DONT_TOUCH="yes" *) reg [15:0] p_root_dest;
    (* DONT_TOUCH="yes" *) reg [8:0] p_root_addr;
    (* DONT_TOUCH="yes" *) reg [31:0] p_root_data;
    (* DONT_TOUCH="yes" *) reg [3:0] p_desc_stage;
    (* DONT_TOUCH="yes" *) reg [15:0] p_desc_mask;
    (* DONT_TOUCH="yes" *) reg [8:0] p_desc_root_base;
    (* DONT_TOUCH="yes" *) reg [4:0] p_desc_root_mask;
    (* DONT_TOUCH="yes" *) reg [15:0] p_desc_gap;
    (* DONT_TOUCH="yes" *) reg [9:0] p_load_line;
    (* DONT_TOUCH="yes" *) reg [127:0] p_load_data;
    (* DONT_TOUCH="yes" *) reg [9:0] p_read_line;
    (* DONT_TOUCH="yes" *) reg p_cfg_valid;
    (* DONT_TOUCH="yes" *) reg p_root_we;
    (* DONT_TOUCH="yes" *) reg p_root_commit;
    (* DONT_TOUCH="yes" *) reg p_desc_we;
    (* DONT_TOUCH="yes" *) reg p_load_valid;
    (* DONT_TOUCH="yes" *) reg p_read_valid;
    (* DONT_TOUCH="yes" *) reg p_start;
    (* DONT_TOUCH="yes" *) reg p_rst;
    (* DONT_TOUCH="yes" *) reg q_cfg_fft;
    (* DONT_TOUCH="yes" *) reg q_cfg_inverse;
    (* DONT_TOUCH="yes" *) reg q_cfg_ntrugen;
    (* DONT_TOUCH="yes" *) reg q_cfg_packed;
    (* DONT_TOUCH="yes" *) reg [2:0] q_cfg_jobs_log;
    (* DONT_TOUCH="yes" *) reg [1:0] q_cfg_fmt;
    (* DONT_TOUCH="yes" *) reg [1:0] q_cfg_hmin;
    (* DONT_TOUCH="yes" *) reg [3:0] q_cfg_logn;
    (* DONT_TOUCH="yes" *) reg [31:0] q_cfg_q;
    (* DONT_TOUCH="yes" *) reg [31:0] q_cfg_qinv;
    (* DONT_TOUCH="yes" *) reg [15:0] q_root_dest;
    (* DONT_TOUCH="yes" *) reg [8:0] q_root_addr;
    (* DONT_TOUCH="yes" *) reg [31:0] q_root_data;
    (* DONT_TOUCH="yes" *) reg [3:0] q_desc_stage;
    (* DONT_TOUCH="yes" *) reg [15:0] q_desc_mask;
    (* DONT_TOUCH="yes" *) reg [8:0] q_desc_root_base;
    (* DONT_TOUCH="yes" *) reg [4:0] q_desc_root_mask;
    (* DONT_TOUCH="yes" *) reg [15:0] q_desc_gap;
    (* DONT_TOUCH="yes" *) reg [9:0] q_load_line;
    (* DONT_TOUCH="yes" *) reg [127:0] q_load_data;
    (* DONT_TOUCH="yes" *) reg [9:0] q_read_line;
    (* DONT_TOUCH="yes" *) reg q_cfg_valid;
    (* DONT_TOUCH="yes" *) reg q_root_we;
    (* DONT_TOUCH="yes" *) reg q_root_commit;
    (* DONT_TOUCH="yes" *) reg q_desc_we;
    (* DONT_TOUCH="yes" *) reg q_load_valid;
    (* DONT_TOUCH="yes" *) reg q_read_valid;
    (* DONT_TOUCH="yes" *) reg q_start;
    (* DONT_TOUCH="yes" *) reg accepted_main_d;
    (* DONT_TOUCH="yes" *) reg rsp_valid_q;
    (* DONT_TOUCH="yes" *) reg [127:0] rsp_data_q;
    wire c_cfg_ready,c_load_ready,c_read_ready,c_busy,c_done,c_error,c_rsp_valid;
    wire [31:0] c_cycles;
    wire [127:0] c_read_data;
    (* DONT_TOUCH="yes" *) reg reserved;
    // Distinct low-fanout permission FF; execution reset does not feed token D.
    (* DONT_TOUCH="yes" *) reg frontend_live;
    wire main_request_i;
    // Decode request priority without permission/occupancy; apply those local
    // FFs only at the final occupancy gate, not through the read-token chain.
    (* KEEP_HIERARCHY="yes" *) a_cg_main_request u_main_request (
        .cfg_available(c_cfg_ready),.load_available(c_load_ready),.read_available(c_read_ready),
        .cfg_valid(cfg_valid),.start(start),.load_valid(load_valid),.read_valid(read_valid),
        .request(main_request_i)
    );
    wire cfg_open_i,load_open_i,read_open_i;
    wire cfg_fire_i,start_fire_i,load_fire_i,read_fire_i;
    wire root_fire_i,commit_fire_i,desc_fire_i;
    (* KEEP_HIERARCHY="yes" *) a_cg_command_decode u_command_decode (
        .live(frontend_live),.reserved(reserved),
        .cfg_available(c_cfg_ready),.load_available(c_load_ready),.read_available(c_read_ready),
        .cfg_valid(cfg_valid),.start(start),.load_valid(load_valid),.read_valid(read_valid),
        .root_we(root_we),.root_commit(root_commit),.desc_we(desc_we),.desc_stage(desc_stage),
        .cfg_open(cfg_open_i),.load_open(load_open_i),.read_open(read_open_i),
        .cfg_fire(cfg_fire_i),.start_fire(start_fire_i),.load_fire(load_fire_i),.read_fire(read_fire_i),
        .root_fire(root_fire_i),.commit_fire(commit_fire_i),.desc_fire(desc_fire_i)
    );
    // Asserting reset masks the public interface immediately. The synchronous
    // reset on flag FFs dominates capture, so token decode need not include rst.
    assign cfg_ready=!rst && cfg_open_i;
    assign load_ready=!rst && load_open_i;
    assign read_ready=!rst && read_open_i;
    assign busy=!rst && !p_rst && (c_busy || p_start || q_start);
    assign done=!rst && !p_rst && c_done;
    assign error=c_error;
    assign cycles=c_cycles;
    assign read_rsp_valid=!rst && !p_rst && rsp_valid_q;
    assign read_data=rsp_data_q;
    // Read payload and its token advance together. Delayed reset also flushes
    // a response that the execution stage generated on the raw reset edge.
    always @(posedge clk)begin
        rsp_data_q<=c_read_data;
        if(rst || p_rst)rsp_valid_q<=0;
        else rsp_valid_q<=c_rsp_valid;
    end
    // Snapshot every payload field. Accepted strobes are the only data enables
    // in the consumer; changing the external pins after handshake is safe.
    always @(posedge clk)begin
        p_rst<=rst;
        frontend_live<=!rst;
        p_cfg_fft<=cfg_fft;
        p_cfg_inverse<=cfg_inverse;
        p_cfg_ntrugen<=cfg_ntrugen;
        p_cfg_packed<=cfg_packed;
        p_cfg_jobs_log<=cfg_jobs_log;
        p_cfg_fmt<=cfg_fmt;
        p_cfg_hmin<=cfg_hmin;
        p_cfg_logn<=cfg_logn;
        p_cfg_q<=cfg_q;
        p_cfg_qinv<=cfg_qinv;
        p_root_dest<=root_dest;
        p_root_addr<=root_addr;
        p_root_data<=root_data;
        p_desc_stage<=desc_stage;
        p_desc_mask<=desc_mask;
        p_desc_root_base<=desc_root_base;
        p_desc_root_mask<=desc_root_mask;
        p_desc_gap<=desc_gap;
        p_load_line<=load_line;
        p_load_data<=load_data;
        p_read_line<=read_line;
        q_cfg_fft<=p_cfg_fft;
        q_cfg_inverse<=p_cfg_inverse;
        q_cfg_ntrugen<=p_cfg_ntrugen;
        q_cfg_packed<=p_cfg_packed;
        q_cfg_jobs_log<=p_cfg_jobs_log;
        q_cfg_fmt<=p_cfg_fmt;
        q_cfg_hmin<=p_cfg_hmin;
        q_cfg_logn<=p_cfg_logn;
        q_cfg_q<=p_cfg_q;
        q_cfg_qinv<=p_cfg_qinv;
        q_root_dest<=p_root_dest;
        q_root_addr<=p_root_addr;
        q_root_data<=p_root_data;
        q_desc_stage<=p_desc_stage;
        q_desc_mask<=p_desc_mask;
        q_desc_root_base<=p_desc_root_base;
        q_desc_root_mask<=p_desc_root_mask;
        q_desc_gap<=p_desc_gap;
        q_load_line<=p_load_line;
        q_load_data<=p_load_data;
        q_read_line<=p_read_line;
        if(rst)begin
            reserved<=0;
            accepted_main_d<=0;
            q_cfg_valid<=0;
            q_root_we<=0;
            q_root_commit<=0;
            q_desc_we<=0;
            q_load_valid<=0;
            q_read_valid<=0;
            q_start<=0;
            p_cfg_valid<=0;p_start<=0;p_load_valid<=0;p_read_valid<=0;
            p_root_we<=0;p_root_commit<=0;p_desc_we<=0;
        end else begin
            reserved <= accepted_main_d || (frontend_live && !reserved && main_request_i);
            accepted_main_d <= frontend_live && !reserved && main_request_i;
            q_cfg_valid<=p_cfg_valid;
            q_root_we<=p_root_we;
            q_root_commit<=p_root_commit;
            q_desc_we<=p_desc_we;
            q_load_valid<=p_load_valid;
            q_read_valid<=p_read_valid;
            q_start<=p_start;
            p_cfg_valid<=cfg_fire_i;
            p_start<=start_fire_i;
            p_load_valid<=load_fire_i;
            p_read_valid<=read_fire_i;
            p_root_we<=root_fire_i;
            p_root_commit<=commit_fire_i;
            p_desc_we<=desc_fire_i;
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk)if(!rst)begin
        if(frontend_live !== !p_rst)
            $fatal(1,"frontend permission differs from delayed reset complement");
        if(accepted_main_d !== (p_cfg_valid || p_start || p_load_valid || p_read_valid))
            $fatal(1,"first-stage occupancy differs from accepted token");
        if(reserved !== (p_cfg_valid || p_start || p_load_valid || p_read_valid ||
                         q_cfg_valid || q_start || q_load_valid || q_read_valid))
            $fatal(1,"command occupancy differs from accepted main token");
    end
`endif
    (* KEEP_HIERARCHY="yes" *) a_cg_exec u_exec (
        .clk(clk),
        .rst(p_rst),
        .cfg_fft(q_cfg_fft),
        .cfg_inverse(q_cfg_inverse),
        .cfg_ntrugen(q_cfg_ntrugen),
        .cfg_packed(q_cfg_packed),
        .cfg_jobs_log(q_cfg_jobs_log),
        .cfg_fmt(q_cfg_fmt),
        .cfg_hmin(q_cfg_hmin),
        .cfg_logn(q_cfg_logn),
        .cfg_q(q_cfg_q),
        .cfg_qinv(q_cfg_qinv),
        .root_dest(q_root_dest),
        .root_addr(q_root_addr),
        .root_data(q_root_data),
        .desc_stage(q_desc_stage),
        .desc_mask(q_desc_mask),
        .desc_root_base(q_desc_root_base),
        .desc_root_mask(q_desc_root_mask),
        .desc_gap(q_desc_gap),
        .load_line(q_load_line),
        .load_data(q_load_data),
        .read_line(q_read_line),
        .cfg_valid(q_cfg_valid),
        .root_we(q_root_we),
        .root_commit(q_root_commit),
        .desc_we(q_desc_we),
        .load_valid(q_load_valid),
        .read_valid(q_read_valid),
        .start(q_start),
        .cfg_ready(c_cfg_ready),
        .load_ready(c_load_ready),
        .read_ready(c_read_ready),
        .busy(c_busy),
        .done(c_done),
        .error(c_error),
        .cycles(c_cycles),
        .read_rsp_valid(c_rsp_valid),
        .read_data(c_read_data)
    );
endmodule

// Execution stage behind the command frontend: configuration decode, host line map and host-read scaling, stage
// schedule, 32 data banks (block RAM), 16 tiles with their root memories, and the shared FFT product program.
module a_cg_exec (
    input wire clk, rst,
    input wire cfg_valid,
    output wire cfg_ready,
    input wire cfg_fft, cfg_inverse, cfg_ntrugen, cfg_packed,
    input wire [2:0] cfg_jobs_log,
    input wire [1:0] cfg_fmt, cfg_hmin,
    input wire [3:0] cfg_logn,
    input wire [31:0] cfg_q, cfg_qinv,
    input wire root_we, root_commit,
    input wire [15:0] root_dest,
    input wire [8:0] root_addr,
    input wire [31:0] root_data,
    input wire desc_we,
    input wire [3:0] desc_stage,
    input wire [15:0] desc_mask,
    input wire [8:0] desc_root_base,
    input wire [4:0] desc_root_mask,
    input wire [15:0] desc_gap,
    input wire load_valid,
    output wire load_ready,
    input wire [9:0] load_line,
    input wire [127:0] load_data,
    input wire read_valid,
    output wire read_ready,
    input wire [9:0] read_line,
    output reg read_rsp_valid,
    output wire [127:0] read_data,
    input wire start,
    output wire busy,
    output reg done, error,
    output reg [31:0] cycles
);
    localparam IDLE=0, HLOAD=1, HREAD=2, HCATCH=3, RESET_TILE=4,
               CONFIG_TILE=5, SETTLE=6, STAGE=7, RUN=8, HPREP=9;
    reg [3:0] state;
    // Config has a private fixed-latency valid pipeline. It does not add states
    // or feedback decoders to the butterfly/host FSM.
    reg [4:0] cfg_pipe;
    wire cfg_pending=|cfg_pipe;
    wire cfg_accept=cfg_valid; // Accepted command token from the frontend.
    always @(posedge clk)
        if(rst)cfg_pipe<=0;
        else cfg_pipe<={cfg_pipe[3:0],cfg_accept};
    reg [2:0] cfg_jobs_q;
    reg [3:0] cfg_plane_q;
    reg [4:0] cfg_row_q;
    reg cfg_bad_q;
    // Reset prediction is valid only for an accepted idle start. Its local
    // registered replicas are asserted in RESET_TILE, with no extra kernel clock.
    wire reset_launch=start; // Already accepted in the idle command window.

    reg fft, inverse, native64, packed16, configured, roots_valid;
    reg [3:0] stages;
    reg [2:0] bank_jobs_log,row_jobs_log,base_log;
    reg [3:0] job_word_log;
    reg [1:0] hmin_eff;
    reg [1:0] fmt, hmin;
    reg [3:0] logn, logm, rowlog, stage_idx;
    reg [31:0] q, qi;
    reg [3:0] planes;
    reg [7:0] rows_per_buf;
    reg [9:0] desc_valid;
    (* ram_style="distributed" *) reg [45:0] desc [0:9];
    reg [15:0] active,write_active;
    reg [3:0] write_stage;
    reg [15:0] read_gap,stage_elapsed;
    // stage_elapsed counts from 1 (it is the previous count + 1), so the switch compares it with read_gap directly
    reg read_started;
    reg [8:0] root_base;
    reg [4:0] root_mask;
    reg [4:0] k;
    reg [5:0] beat;
    reg [2:0] part;
    reg sent_all;
    // Stage flags are registers, set whenever the stage index changes. irf is used only in procedural code: a continuous
    // assignment through a function that reads module signals is re-evaluated in simulation only when its arguments change.
    function irf(input [3:0] idx);                 // packed16 within-word layer
        irf = packed16 && hmin==0 && (inverse ? idx==0 : idx==stages-1);
    endfunction
    reg  internal_read, read_near, write_far;
    reg  more_stages;                             // stage_idx < stages - 1
    reg  [45:0] desc_nx;                          // desc[stage_idx + 1], prefetched
    wire [3:0] base_planes=4'd1<<base_log;
    wire [3:0] row_jobs=4'd1<<row_jobs_log;
    wire [2:0] limbs = 3'd1 << fmt;
    wire [5:0] period = !fft ? 6'd3 : fmt==0 ? 6'd3 : fmt==1 ? 6'd12 : 6'd45;
    wire [4:0] last_k = logm>5 ? ((6'd1 << (logm-5))-1) : 0;
    wire tile_rst = rst || state==RESET_TILE;
    reg [1:0] ph;
    always @(posedge clk)
        if (tile_rst) ph<=0;
        else ph <= ph==2 ? 0 : ph+1'b1;
    reg  beat_rd;                                 // beat < base_planes, kept with beat (FFT)
    reg  [5:0] bp_m1;                             // base_planes - 1
    always @(posedge clk) bp_m1 <= {2'b0, base_planes} - 1'b1;
    wire rd_issue = state==RUN && !sent_all &&
                    (fft ? beat_rd : (beat==0 && (ph==1)));
    function [2:0] rpf(input [5:0] bt, input [2:0] pa);
        rpf = fft ? ((pa<<base_log) | ((bt[0] ? limbs : 0)+(bt>>1))) : pa;
    endfunction
    reg  [2:0] rd_plane;                          // rpf(beat, part), registered with the counters
    wire [7:0] far_y_offset = logm>=6 ? (8'd1 << (logm-6)) : 0;
    // Bank and root addresses: the parts that depend on k are registers updated with k.
    function [7:0] koff_f(input [4:0] kk, input h);            // far geometry: k/2, plus the far offset for the other half
        koff_f = (kk>>1) + ((kk[0]!=h) ? far_y_offset : 0);
    endfunction
    function nswap_f(input [4:0] kk);
        nswap_f = logm>=6 ? ((kk >> (logm-6)) & 1'b1) : 1'b0;
    endfunction
    function [8:0] kroot_f(input [4:0] kk, input [4:0] rm);
        kroot_f = fft ? ((kk & rm) << (fmt+1)) : (kk & rm);
    endfunction
    // Rows are bit fields: buffer (rows_per_buf), plane (<< rowlog) and the row inside the plane (< 2^rowlog) never
    // overlap, and the far offset is one bit above k/2, so every row is an OR, not a sum.
    // Read row = rd_hi | koff[half]: rd_hi is registered with rd_plane, koff with k; both bank halves share them.
    function [7:0] hi_f(input par, input [2:0] pl);
        hi_f = (par ? rows_per_buf : 8'd0) | ({5'b0,pl} << rowlog);
    endfunction
    reg [7:0] rd_hi;                                           // hi_f(stage parity, rd_plane)
    reg [7:0] koff [0:1];                                      // per bank half: read_near ? k : koff_f(k, half)
    reg [4:0] swap_mask;                                       // bit logm - 6 (logm >= 6), for the write-side swap
    always @(posedge clk) swap_mask <= logm>=6 ? (5'd1 << (logm-6)) : 5'd0;
    wire [7:0] rd_row_h [0:1];
    assign rd_row_h[0] = rd_hi | koff[0];
    assign rd_row_h[1] = rd_hi | koff[1];
    reg       near_swap;                                       // nswap_f(k)
    reg [8:0] rbk;                                             // root_base + kroot_f(k, root_mask)
    wire [4:0] k_inc = k + 1'b1;
    // Values fixed per command, registered (compares become equalities with registers; configuration ends several clocks
    // before a command starts).
    reg [5:0] period_m2;
    reg       beat_last;                         // beat == period - 1, kept with beat
    reg [3:0] row_jobs_m1, planes_m1, stages_m1;
    reg [4:0] last_k_r;
    always @(posedge clk) begin
        period_m2<=period-2'd2; row_jobs_m1<=row_jobs-1'b1; planes_m1<=planes-1'b1; stages_m1<=stages-1'b1; last_k_r<=last_k;
    end
    // next issue counters inside a stage (the stage switch overrides them)
    reg [4:0] k_nx; reg [5:0] beat_nx; reg [2:0] part_nx; reg sa_nx, kstep;
    always @* begin
        k_nx=k; beat_nx=beat; part_nx=part; sa_nx=sent_all; kstep=1'b0;
        if (!sent_all) begin
            if (fft) begin
                if (beat_last) begin
                    beat_nx=0;
                    if({1'b0,part}==row_jobs_m1)begin part_nx=0; if(k==last_k_r) sa_nx=1'b1; else begin k_nx=k_inc; kstep=1'b1; end end
                    else part_nx=part+1'b1;
                end else beat_nx=beat+1'b1;
            end else if (rd_issue) begin
                if ({1'b0,part}==planes_m1) begin part_nx=0; if (k==last_k_r) sa_nx=1'b1; else begin k_nx=k_inc; kstep=1'b1; end end
                else part_nx=part+1'b1;
            end
        end
    end
    wire [2:0] rd_plane_in = rd_plane & (base_planes[2:0] - 3'd1);    // plane within the root pack (FFT)
    wire [8:0] rt_addr = rbk + (fft ? {6'd0, rd_plane_in} : 9'd0);

    // configured remains zero throughout config preparation; it is sufficient
    // to protect host acceptance without routing cfg_pending into host CEs.
`ifndef SYNTHESIS
    always @(posedge clk) if(!rst && cfg_pending)begin
        if(configured || load_ready || read_ready || busy || roots_valid || desc_valid!=0)
            $fatal(1,"host/context exposed during configuration preparation");
    end
`endif

    // Registered host adapter: capture request first, serve phase 0 next. A natural
    // line uses 1/2/4 bank-service clocks at FFT32/64/128, without changing
    // the compute bank map. Read responses pipeline across line boundaries.
    reg [127:0] host_data;
    reg [1:0] host_word;
    reg host_direction;
    wire load_accept=load_valid;
    wire read_accept=read_valid;
    always @(posedge clk)
        if(rst) host_direction<=0;
        else if(load_accept) host_direction<=0;
        else if(read_accept) host_direction<=1;
    // Payload and command token are committed together. No live frontend
    // ready/config gating is distributed to these register enables.
    always @(posedge clk)
        if(load_valid)host_data<=load_data;
    wire host_write=state==HLOAD;
    wire host_read=state==HREAD;
    wire [1:0] host_submask_c=fft && logm==0 ? (fmt==0 ? 2'd1 : 2'd3) :
                            fft && logm==1 && fmt==0 ? 2'd1 : (3'd1 << (fft ? fmt : hmin_eff))-1'b1;
    reg  [1:0] host_submask;                     // host_submask_c, registered (fixed per configuration)
    always @(posedge clk) host_submask<=host_submask_c;
`ifndef SYNTHESIS
    always @(posedge clk) if(!rst)begin
        if(host_read && !host_direction)$fatal(1,"read map direction not captured");
        if(host_write && host_direction)$fatal(1,"write map direction not captured");
    end
`endif
    // Host map. Values that depend only on the configuration are registered every clock (host commands arrive at least
    // two clocks after configuration ends, through the command stages); values that depend on the line are made when the
    // line is captured. HPREP then only combines registers.
    wire [12:0] total_words_c=(13'd1<<job_word_log)<<(bank_jobs_log+row_jobs_log);
    wire [9:0] pmask_c=(11'd1 << logm)-1;
    wire [1:0] host_pack_c=fft ? fmt : hmin_eff;
    reg  [12:0] total_words;
    reg  [9:0]  pmask;
    reg  [1:0]  host_pack;
    reg  [3:0]  job_bank_shift_d [0:1];          // by host direction
    reg  [7:0]  host_rdoff;                       // read direction: rows of the second buffer when stages is odd
    reg         fft_lognz;                        // fft && logn != 0
    always @(posedge clk) begin
        total_words<=total_words_c; pmask<=pmask_c; host_pack<=host_pack_c;
        job_bank_shift_d[0]<=inverse ? 5-bank_jobs_log : 5-logm-bank_jobs_log;
        job_bank_shift_d[1]<=inverse ? 5-logm-bank_jobs_log : 5-bank_jobs_log;
        host_rdoff<=stages[0] ? rows_per_buf : 8'd0;
        fft_lognz<=fft && logn!=0;
    end
    // line-derived, at capture (the line comes from the command stage register)
    wire [9:0]  cap_line=load_valid ? load_line : read_line;
    wire [11:0] cap_j={cap_line,2'b0};
    wire [11:0] cap_element=cap_j>>host_pack;
    wire [3:0]  cap_job=cap_j>>job_word_log;      // 4 bits first, as the single-clock map
    reg  [9:0]  host_base_p;                      // position of the line's first element
    reg  [3:0]  host_oob_line;                    // per word of the line: beyond the data
    reg  [4:0]  host_base_bank_r;                 // bank of the line's first word, made at capture
    reg  [2:0]  host_base_plane_r;                // plane of the line's first word, made at capture
    wire        cap_dir=!load_valid;              // 0 load, 1 read (as host_direction after the capture)
    wire [9:0]  cap_p=cap_element[9:0]&pmask;
    wire [3:0]  cap_bank_job=cap_job&((5'd1<<bank_jobs_log)-1);
    wire [4:0]  capl_tiny=(inverse ^ cap_dir) ? cap_p[4:0] : (cap_p[4:0]<<(5-logm));
    wire [4:0]  capl_bank=logm>=6 ? (cap_p[4:0]^(((cap_p>>(logm-1))&1)<<4)) : (capl_tiny^(cap_bank_job<<job_bank_shift_d[cap_dir]));
    integer cw;
    always @(posedge clk)
        if(load_valid || read_valid) begin
            host_base_bank_r<=capl_bank;
            host_base_plane_r<=(((cap_job>>bank_jobs_log)<<base_log) | (fft_lognz ? ({2'b0,cap_element[logm]}<<fmt) : 3'd0));
            host_base_p<=cap_element[9:0]&pmask;
            for(cw=0;cw<4;cw=cw+1) host_oob_line[cw]<=({cap_line,cw[1:0]})>=total_words;
        end
    wire [7:0] host_base_row=(host_direction ? host_rdoff : 8'd0) | ({5'd0,host_base_plane_r}<<rowlog) | (host_base_p>>5);
    wire [4:0] host_bank_basis[0:1];
    wire [7:0] host_row_basis[0:1];
    wire [1:0] host_phase_basis[0:1];
    genvar hb;
    generate for(hb=0;hb<2;hb=hb+1) begin:host_basis
        wire lane_bit=hb<host_pack;
        wire [2:0] pbit=hb-host_pack;
        wire job_bit=hb>=job_word_log;
        wire position_bit=!job_bit && !lane_bit && pbit<logm;
        wire component_bit=!job_bit && fft && !lane_bit && pbit==logm;
        wire [4:0] p_delta=5'd1<<pbit;
        wire [7:0] row_basis_c=lane_bit ? (8'd1<<(rowlog+hb)) : component_bit ? (8'd1<<(rowlog+fmt)) : 0;
        wire [1:0] phase_basis_c=lane_bit ? (2'd1<<hb) : component_bit ? (2'd1<<fmt) : 0;
        // registered (fixed per configuration), the bank basis for both directions
        reg  [4:0] bank_basis_r [0:1];
        reg  [7:0] row_basis_r;
        reg  [1:0] phase_basis_r;
        integer bd;
        always @(posedge clk) begin
            for (bd=0;bd<2;bd=bd+1)
                bank_basis_r[bd] <= job_bit ? (5'd1<<(job_bank_shift_d[bd]+hb-job_word_log)) :
                                    position_bit ? (logm>=6 ? p_delta^((pbit==logm-1) ? 5'd16 : 5'd0) :
                                                   ((inverse ^ bd[0]) ? p_delta : (p_delta<<(5-logm)))) : 5'd0;
            row_basis_r <= row_basis_c; phase_basis_r <= phase_basis_c;
        end
        assign host_bank_basis[hb]=bank_basis_r[host_direction];
        assign host_row_basis[hb]=row_basis_r;
        assign host_phase_basis[hb]=phase_basis_r;
    end endgenerate
    wire [4:0] host_bank[0:3];
    wire [7:0] host_row[0:3];
    wire [3:0] host_select,host_oob;
    reg [3:0] cap_select,cap_oob;
    reg [4:0] cap_bank[0:3];
    wire [4:0] mapped_bank_w[0:3];
    wire [1:0] mapped_phase_w[0:3];
    genvar hw;
    generate for(hw=0;hw<4;hw=hw+1) begin:host_map
        localparam [1:0] J=hw;
        wire [1:0] phase=host_base_plane_r[1:0]^(J[0] ? host_phase_basis[0] : 2'd0)^(J[1] ? host_phase_basis[1] : 2'd0);
        wire [4:0] mapped_bank=host_base_bank_r^(J[0] ? host_bank_basis[0] : 5'd0)^(J[1] ? host_bank_basis[1] : 5'd0);
        wire [7:0] mapped_row=host_base_row^(J[0] ? host_row_basis[0] : 8'd0)^(J[1] ? host_row_basis[1] : 8'd0);
        wire mapped_oob=host_oob_line[hw];
        assign mapped_bank_w[hw]=mapped_bank; assign mapped_phase_w[hw]=phase;
        reg [4:0] bank_q;
        reg [7:0] row_q;
        reg [1:0] phase_q;
        reg oob_q;
        always @(posedge clk) if(state==HPREP)begin
            bank_q<=mapped_bank;row_q<=mapped_row;phase_q<=phase;oob_q<=mapped_oob;
        end
        assign host_bank[hw]=bank_q;
        assign host_row[hw]=row_q;
        assign host_select[hw]=((phase_q & host_submask)==host_word);
        assign host_oob[hw]=oob_q;
`ifndef SYNTHESIS
        always @(posedge clk) if(!rst && (host_read||host_write))begin
            if(bank_q!==mapped_bank || row_q!==mapped_row || phase_q!==phase || oob_q!==mapped_oob)
                $fatal(1,"prepared host map changed during service");
        end
`endif
        always @(posedge clk) begin
            if(rst) begin cap_select[hw]<=0;cap_oob[hw]<=0; end
            else begin
                cap_select[hw]<=host_read && host_select[hw];
                cap_oob[hw]<=host_oob[hw];
                cap_bank[hw]<=host_bank[hw];
            end
        end
    end endgenerate

    // ---- inverse FFT scaling at the host read ----
    // The tiles do not apply div2e to the last inverse FFT layer: the result stays in the banks unscaled (W bits hold it)
    // and every line read after such a command is scaled here: wrap_W(v + 2^(s-1)) >>> s for each W-bit value of the
    // line (W = 32 << fmt; a line holds 4 >> fmt values, low limb first; s = logm). Bit-exact with div2e in the last
    // layer, since it is the last operation of the transform. The scale is pending from the end of a non-NTRUGen
    // inverse FFT until the next configuration, start or load. Two clocks: the rounding increment (word 0 of each value
    // by 2^(s-1), carries passed word to word inside a value), then the shift (made combinationally into the frontend's
    // response register).
    reg         scale_pend;
    reg  [3:0]  scale_s;
    reg  [31:0] scale_r, scale_lowm;              // 2^(s-1) and 2^(s-1) - 1 (0 when s = 0), set with scale_s
    reg         scale_nz;
    reg  [1:0]  scale_fmt;
    reg  [127:0] line_data;
    reg         line_valid;
    reg  [127:0] rs_sum;
    reg  [3:0]  rs_s;
    reg  [1:0]  rs_fmt;
    wire [3:0]  sc_s = scale_pend ? scale_s : 4'd0;
    wire [31:0] sc_r = scale_pend ? scale_r : 32'd0;
    wire [3:0]  sc_first = scale_fmt==2'd0 ? 4'b1111 : scale_fmt==2'd1 ? 4'b0101 : 4'b0001;   // low limb of a value
    // Carries between the words of a value without carry chains: adding 2^(s-1) to a low limb carries out when its
    // bits s-1 .. 31 are all ones; a higher limb passes its carry-in on when it is all ones. Each word is then one
    // 32-bit add with its own carry-in (timing: no chain through the four words).
    wire [3:0]  sc_cf = {4{scale_pend && scale_nz}} & {&(line_data[127:96] | scale_lowm), &(line_data[95:64] | scale_lowm),
                                                        &(line_data[63:32] | scale_lowm), &(line_data[31:0] | scale_lowm)};
    wire [3:0]  sc_ones = {&line_data[127:96], &line_data[95:64], &line_data[63:32], &line_data[31:0]};
    wire        sc_c1 = !sc_first[1] && sc_cf[0];
    wire        sc_o1 = sc_first[1] ? sc_cf[1] : (sc_c1 && sc_ones[1]);
    wire        sc_c2 = !sc_first[2] && sc_o1;
    wire        sc_o2 = sc_first[2] ? sc_cf[2] : (sc_c2 && sc_ones[2]);
    wire        sc_c3 = !sc_first[3] && sc_o2;
    // first clock: carries and the addends registered; second clock: one add per word
    reg  [127:0] sa_line, sa_add;
    reg  [3:0]   sa_c;
    reg  [3:0]   sa_s;
    reg  [1:0]   sa_fmt;
    reg          sa_valid;
    always @(posedge clk) begin
        sa_valid <= !rst && line_valid;
        sa_line <= line_data;
        sa_add <= {sc_first[3] ? sc_r : 32'd0, sc_first[2] ? sc_r : 32'd0, sc_first[1] ? sc_r : 32'd0, sc_r};
        sa_c <= {sc_c3, sc_c2, sc_c1, 1'b0};
        sa_s <= sc_s; sa_fmt <= scale_fmt;
    end
    wire [31:0] sc_w0 = sa_line[31:0] + sa_add[31:0];
    wire [31:0] sc_w1 = sa_line[63:32] + sa_add[63:32] + {31'd0, sa_c[1]};
    wire [31:0] sc_w2 = sa_line[95:64] + sa_add[95:64] + {31'd0, sa_c[2]};
    wire [31:0] sc_w3 = sa_line[127:96] + sa_add[127:96] + {31'd0, sa_c[3]};
    always @(posedge clk) begin
        if (rst) read_rsp_valid <= 1'b0;
        else read_rsp_valid <= sa_valid;
        rs_sum <= {sc_w3, sc_w2, sc_w1, sc_w0};
        rs_s <= sa_s; rs_fmt <= sa_fmt;
    end
    // shift: logical right shift of the whole line, then the bits that came from the value above (or beyond the line)
    // replaced by the sign of their own value
    // Boundary-aware arithmetic shifter, exact per-value sign extension.
    wire rs_c02 = rs_fmt != 2'd0;
    wire rs_c1  = rs_fmt == 2'd2;
    // bit j of x shifted right by e inside its value (j and e are constants at each use)
    function rs_pick(input [127:0] x, input integer j, input integer e, input c02, input c1);
        integer i, w;
        begin
            i = j + e; w = j / 32;
            if (i / 32 == w) rs_pick = x[i];
            else if (w == 3) rs_pick = x[127];
            else rs_pick = ((w == 1) ? c1 : c02) ? x[i] : x[32*w + 31];
        end
    endfunction
    wire [127:0] rs_lo, rs_out;                     // after the s[1:0] level, after the s[3:2] level
    genvar rj;
    generate for (rj=0; rj<128; rj=rj+1) begin : g_ash
        assign rs_lo[rj] = rs_s[1] ? (rs_s[0] ? rs_pick(rs_sum, rj, 3, rs_c02, rs_c1) : rs_pick(rs_sum, rj, 2, rs_c02, rs_c1))
                                   : (rs_s[0] ? rs_pick(rs_sum, rj, 1, rs_c02, rs_c1) : rs_sum[rj]);
        assign rs_out[rj] = rs_s[3] ? (rs_s[2] ? rs_pick(rs_lo, rj, 12, rs_c02, rs_c1) : rs_pick(rs_lo, rj, 8, rs_c02, rs_c1))
                                    : (rs_s[2] ? rs_pick(rs_lo, rj, 4, rs_c02, rs_c1) : rs_lo[rj]);
    end endgenerate
    assign read_data = rs_out;
`ifndef SYNTHESIS
    integer ob;
    // reference: div2e per value, in plain integer arithmetic
    reg [127:0] rs_line_sim, rs_ref;
    reg [3:0]   rs_s_sim; reg [1:0] rs_fmt_sim;
    reg         rs_valid_sim;                   // a real line response (a testbench may force the port net)
    integer rv, rw;
    reg signed [127:0] vv;
    always @(posedge clk) begin
        rs_line_sim <= sa_line; rs_s_sim <= sa_s; rs_fmt_sim <= sa_fmt; rs_valid_sim <= !rst && sa_valid;
        if (!rst && rs_valid_sim) begin
            rw = 32 << rs_fmt_sim;
            for (rv=0; rv<128/rw; rv=rv+1) begin
                vv = rs_line_sim >> (rv*rw);
                vv = (rw==32) ? {{96{vv[31]}}, vv[31:0]} : (rw==64) ? {{64{vv[63]}}, vv[63:0]} : vv;
                if (rs_s_sim != 0) vv = vv + (128'sd1 <<< (rs_s_sim-1));
                vv = (rw==32) ? {{96{vv[31]}}, vv[31:0]} : (rw==64) ? {{64{vv[63]}}, vv[63:0]} : vv;   // wrap to W bits
                vv = vv >>> rs_s_sim;
                for (ob=0; ob<rw; ob=ob+1) rs_ref[rv*rw+ob] = vv[ob];
            end
            if (rs_ref !== read_data) $fatal(1,"host-side div2e differs: %h vs %h (s %0d fmt %0d)", read_data, rs_ref, rs_s_sim, rs_fmt_sim);
        end
    end
`endif

    // Host selects of the next clock: word index, phases and banks as they will be, so each bank registers its own
    // one-hot word select (hsel) and the bank ports see no compare.
    wire [1:0] hword_nx = (state==HPREP) ? 2'd0 : (state==HLOAD || state==HREAD) ? host_word+1'b1 : host_word;
    wire [3:0] hsel_word_nx;
    genvar hx;
    generate for (hx=0;hx<4;hx=hx+1) begin : g_hsel_word
        // words beyond the data are masked where hsel is used (host_oob is registered and fixed during the service)
        assign hsel_word_nx[hx] = (((state==HPREP ? mapped_phase_w[hx] : host_map[hx].phase_q) & host_submask) == hword_nx);
    end endgenerate

    // Each bank has exactly one synchronous read and one write port. All rows
    // hold live runtime data; no initial contents or tied-off mode inputs.
    wire [31:0] bank_rdata [0:31];
    wire [15:0] rsp_valid, req_ready;
    wire [63:0] rsp_data [0:15];
    wire [7:0] rsp_tag [0:15];
    wire prog_valid;
    wire [15:0] prog_mask;
    wire [1:0] prog_product;
    wire [3:0] prog_step;
    wire [4:0] out_k = rsp_tag[0][7:3];
    wire [2:0] out_plane = rsp_tag[0][2:0];
    wire out_near_swap = |(out_k & swap_mask);
    wire [7:0] wr_hi = (!write_stage[0] ? rows_per_buf : 8'd0) | ({5'b0,out_plane} << rowlog);
    wire [7:0] wr_row_h [0:1];
    assign wr_row_h[0] = wr_hi | (write_far ? ((out_k>>1) | (out_k[0] ? far_y_offset : 8'd0)) : {3'b0,out_k});
    assign wr_row_h[1] = wr_hi | (write_far ? ((out_k>>1) | (!out_k[0] ? far_y_offset : 8'd0)) : {3'b0,out_k});
    genvar b;
    generate for (b=0;b<32;b=b+1) begin : data_bank
        (* ram_style="block" *) reg [31:0] mem [0:255];
        reg [31:0] dout;
        localparam integer TF=b>>1, TI=b&15;
        wire [31:0] forward_data = out_near_swap ? rsp_data[TF^8][32*(b&1)+:32]
                                                                : rsp_data[TF][32*(b&1)+:32];
        wire [31:0] inverse_data = (out_k[0]==(b>>4)) ? rsp_data[TI][0+:32] : rsp_data[TI][32+:32];
        wire forward_valid = out_near_swap ? (write_active[TF^8] && rsp_valid[TF^8]) : (write_active[TF] && rsp_valid[TF]);
        wire inverse_valid = write_active[TI] && rsp_valid[TI];
        wire compute_write = state==RUN && (write_far ? inverse_valid : forward_valid);
        wire [7:0] wr_row = wr_row_h[b>>4];
        wire [7:0] rd_row = rd_row_h[b>>4];
        wire compute_read_en = read_near ? (near_swap ? active[TF^8] : active[TF]) : active[TI];
        reg [3:0] hsel;                            // word hj of the line goes to / comes from this bank in this clock
        integer hk;
        always @(posedge clk)
            for (hk=0;hk<4;hk=hk+1)
                hsel[hk] <= hsel_word_nx[hk] && ((state==HPREP ? mapped_bank_w[hk] : host_bank[hk])==b);
        wire [3:0]  hsv = hsel & ~host_oob;
        wire        hr = host_read && |hsv;
        wire        hw = host_write && |hsv;
        wire [7:0]  hra = ({8{hsv[0]}} & host_row[0]) | ({8{hsv[1]}} & host_row[1]) | ({8{hsv[2]}} & host_row[2]) |
                          ({8{hsv[3]}} & host_row[3]);
        wire [7:0]  hwa = hra;
        wire [31:0] hwd = ({32{hsv[0]}} & host_data[31:0]) | ({32{hsv[1]}} & host_data[63:32]) |
                          ({32{hsv[2]}} & host_data[95:64]) | ({32{hsv[3]}} & host_data[127:96]);
        wire ren=(rd_issue && compute_read_en)||hr;
        wire [7:0] ra=host_read ? hra : rd_row;
        wire wen=compute_write||hw;
        wire [7:0] wa=host_write ? hwa : wr_row;
        wire [31:0] wd=host_write ? hwd : write_far ? inverse_data : forward_data;
        always @(posedge clk) begin
            if (ren) dout <= mem[ra];
            if (wen) mem[wa] <= wd;
        end
        assign bank_rdata[b]=dout;
`ifndef SYNTHESIS
        integer hcount,hidx;
        always @(posedge clk) if(!rst)begin
            if(state==RUN && ren && wen && ra==wa)$fatal(1,"same-edge bank RAW");
            hcount=0;
            for(hidx=0;hidx<4;hidx=hidx+1)
                if((host_read||host_write)&&host_select[hidx]&&!host_oob[hidx]&&host_bank[hidx]==b)hcount=hcount+1;
            if(hcount>1)$fatal(1,"host bank collision");
        end
`endif
    end endgenerate

    reg rvalid, req_valid;
    reg r_far, r_near,rscale,qscale,rfirst,qfirst,rgeom,rdummy;
    reg [15:0] rmask,qmask;
    reg [7:0] rtag, req_tag;
    reg [31:0] req_x[0:15], req_y[0:15], req_root[0:15];
    always @(posedge clk) begin
        if (rst || state!=RUN) begin rvalid<=0; req_valid<=0; end
        else begin rvalid<=rd_issue; req_valid<=rvalid; end
        if (rd_issue) begin r_far<=k[0]; r_near<=near_swap; rgeom<=read_near;rdummy<=internal_read && logm==0;rtag<={k,rd_plane};rmask<=active;rscale<=fft && inverse && !native64 && !more_stages; rfirst<=fft && beat==0; if(!fft)rscale<=internal_read; end
        if (rvalid) begin req_tag<=rtag;qmask<=rmask;qscale<=rscale;qfirst<=rfirst;end
    end
    genvar t;
    generate for (t=0;t<16;t=t+1) begin : engine
        (* ram_style="block" *) reg [31:0] root_mem [0:511];
        reg [31:0] root_q;
        always @(posedge clk) begin
            if (rd_issue) root_q<=root_mem[rt_addr];
            if (root_we && root_dest[t]) root_mem[root_addr]<=root_data;
            if (rvalid) begin
                // Four candidates per input: two far and two near banks.
                req_x[t] <= rgeom ? (r_near ? bank_rdata[(2*t)^16] : bank_rdata[2*t])
                                    : (r_far ? bank_rdata[t+16] : bank_rdata[t]);
                req_y[t] <= rdummy ? 32'd0 : rgeom ? (r_near ? bank_rdata[(2*t+1)^16] : bank_rdata[2*t+1])
                                    : (r_far ? bank_rdata[t] : bank_rdata[t+16]);
                req_root[t]<=root_q;
            end
        end
        (* DONT_TOUCH="yes" *) reg reset_local;
        (* DONT_TOUCH="yes" *) reg config_local;
        always @(posedge clk)begin
            reset_local <= rst || reset_launch;
            config_local <= !rst && state==RESET_TILE;
        end
`ifndef SYNTHESIS
        always @(posedge clk) if(!rst)begin
            if(state==RESET_TILE && reset_local!==1'b1)$fatal(1,"local reset not asserted");
            if(state==CONFIG_TILE && reset_local!==1'b0)$fatal(1,"local reset overlaps tile config");
            if(config_local!==(state==CONFIG_TILE))$fatal(1,"local config pulse changed phase");
        end
`endif
        wire unused_idle;
        tile_a2 #(.TREN_MANG(1),.IN_REG(1),.EN_REG(0),.PHASE(0)) u_tile (
            .clk(clk),.rst(reset_local),.en(1'b1),.idle(unused_idle),
            .cfg_we(config_local),.cfg_slot(1'b0),.cfg_q(packed16 ? {q[15:0],q[15:0]} : q),.cfg_qinv(packed16 ? {qi[15:0],qi[15:0]} : qi),
            .cfg_ntrugen(native64),.cfg_fmt(fmt),.cfg_shift(logm),.cfg_floor(1'b0),.cfg_halve(inverse),
            .ext_fft_valid(prog_valid && prog_mask[t]),.ext_fft_mpr(prog_product),.ext_fft_mst(prog_step),
            .req_valid(req_valid && qmask[t]),.req_ready(req_ready[t]),
            .req_mode(fft ? 2'd1 : packed16 ? 2'd2 : 2'd0),.req_dir(inverse),.req_slot(1'b0),
            .req_sign(qscale),
            .req_data({req_y[t],req_x[t]}),.req_root(req_root[t]),.req_tag(req_tag),
            .rsp_valid(rsp_valid[t]),.rsp_data(rsp_data[t]),.rsp_tag(rsp_tag[t])
        );
    end endgenerate

    // One product program for all engines; state/multiplier operands stay local.
    // Accepted first beat -> first limb product = 2L+5 clocks, with the tile's input register and its extra request
    // register. The program runs one clock early from registers (taps program_d - 2 of the delay lines), and every tile
    // registers it once, so each tile sees the same program on time from a local register.
    // The taps used are 4 .. 10. The delay lines keep 13 entries: with a variable tap, synthesis keeps entries 11 and 12
    // (never selected), and the measured netlist has them.
    reg [12:0] program_delay;
    reg [15:0] mask_delay[0:12];
    wire [3:0] program_d=fmt==0 ? 6 : fmt==1 ? (native64 && inverse ? 10 : 8) : 12;
    integer mi;
    wire first_fft = req_valid && fft && qfirst;
    wire start_early = fmt==0 ? program_delay[4] : fmt==1 ? (native64 && inverse ? program_delay[8] : program_delay[6]) : program_delay[10];
    wire [3:0] last_step = fmt==0 ? 0 : fmt==1 ? 3 : 14;
    reg        e_valid;
    reg [1:0]  e_product;
    reg [3:0]  e_step;
    reg [15:0] e_mask;
    assign prog_valid = e_valid;
    assign prog_mask = e_mask;
    assign prog_product = e_product;
    assign prog_step = e_step;
    always @(posedge clk) begin
        if (tile_rst) begin program_delay<=0; e_valid<=0; e_product<=0; e_step<=0; end
        else begin
            program_delay <= {program_delay[11:0],first_fft};
            mask_delay[0]<=qmask;
            for(mi=1;mi<13;mi=mi+1)mask_delay[mi]<=mask_delay[mi-1];
            if (start_early) begin e_valid<=1; e_product<=0; e_step<=0; e_mask<=mask_delay[program_d-2]; end
            else if (e_valid) begin
                if (e_step==last_step) begin
                    e_step<=0;
                    if (e_product==2) begin e_valid<=0; e_product<=0; end
                    else e_product<=e_product+1'b1;
                end else e_step<=e_step+1'b1;
            end
        end
    end
    wire [9:0] wanted_desc_c = (11'd1 << stages)-1;
    reg  [9:0] wanted_desc;                      // registered (fixed per configuration; a start comes clocks later)
    always @(posedge clk) wanted_desc <= wanted_desc_c;
    // Availability and busy outputs come from registers, loaded from the next state with the value they will have in the
    // next clock: cfg_ready = IDLE and no configuration pending, load_ready = IDLE and configured, read_ready = IDLE or
    // HCATCH and configured, busy = RESET_TILE .. RUN.
    wire busy_c = state>=RESET_TILE && state<=RUN;     // busy in this clock (cycle counter)
    wire start_go = configured && stages!=0 && roots_valid && (desc_valid&wanted_desc)==wanted_desc;
    wire run_last = rsp_valid[0] && out_k==last_k_r && {1'b0,out_plane}==planes_m1 && write_stage==stages_m1;
    reg [3:0] state_nx;
    always @* begin
        state_nx = state;
        if (state==IDLE) begin
            if (cfg_valid) state_nx = IDLE;
            else if (start) state_nx = start_go ? RESET_TILE : IDLE;
            else if (load_valid || read_valid) state_nx = HPREP;
        end
        if (state==HPREP) state_nx = host_direction ? HREAD : HLOAD;
        if (state==HLOAD && host_word==host_submask) state_nx = IDLE;
        if (state==HREAD && host_word==host_submask) state_nx = HCATCH;
        if (state==HCATCH) state_nx = read_accept ? HPREP : IDLE;
        if (state==RESET_TILE) state_nx = CONFIG_TILE;
        if (state==CONFIG_TILE) state_nx = SETTLE;
        if (state==SETTLE) state_nx = STAGE;
        if (state==STAGE) state_nx = RUN;
        if (state==RUN && run_last) state_nx = IDLE;
        if (rst) state_nx = IDLE;
    end
    wire cfg_pending_nx = !rst && (|{cfg_pipe[3:0], cfg_accept});
    wire configured_nx = rst ? 1'b0 : cfg_pipe[4] ? !cfg_bad_q : (state==IDLE && cfg_valid) ? 1'b0 : configured;
    reg  cfg_ready_r, load_ready_r, read_ready_r, busy_r;
    always @(posedge clk) begin
        cfg_ready_r <= state_nx==IDLE && !cfg_pending_nx;
        load_ready_r <= state_nx==IDLE && configured_nx;
        read_ready_r <= (state_nx==IDLE || state_nx==HCATCH) && configured_nx;
        busy_r <= state_nx>=RESET_TILE && state_nx<=RUN;
    end
    assign busy = busy_r;
    assign cfg_ready = cfg_ready_r;
    assign load_ready = load_ready_r;
    assign read_ready = read_ready_r;
    // Five configuration setup clocks. Each dependent decode starts from
    // registers; host requests resume only after CFG4 returns to IDLE.
    wire [3:0] bank_capacity=logm<5 ? 5-logm : 0;
    wire [4:0] row_exponent={1'b0,rowlog}+{1'b0,cfg_plane_q};
`ifndef SYNTHESIS
    wire [3:0] ref_logm=fft ? (logn==0 ? 0 : logn-1) : logn-((packed16 && hmin==0) ? 1 : hmin);
    wire [3:0] ref_base_log=fft ? fmt+1 : ((packed16 && hmin!=0) ? hmin-1 : hmin);
    wire [3:0] ref_bank_cap=ref_logm<5 ? 5-ref_logm : 0;
    wire [3:0] ref_bank_jobs=cfg_jobs_q<ref_bank_cap ? cfg_jobs_q : ref_bank_cap;
    wire [3:0] ref_row_jobs=cfg_jobs_q-ref_bank_jobs;
    wire [3:0] ref_plane_log=ref_base_log+ref_row_jobs;
    wire [4:0] ref_row_log=(ref_logm>5 ? ref_logm-5 : 0)+ref_plane_log;
    wire ref_bad=logn>10 || fmt==3 || cfg_jobs_q>4 || ref_plane_log>3 || ref_row_log>7 ||
        (native64 && (!fft || fmt!=1)) || (packed16 && (fft || q>=32768)) ||
        (!fft && (hmin>2 || hmin>=logn || !q[0] || q<3 || q[31]));
    always @(posedge clk) if(!rst && cfg_pipe[4])begin
        if(cfg_bad_q!==ref_bad || logm!==ref_logm || base_log!==ref_base_log[2:0] ||
           bank_jobs_log!==ref_bank_jobs[2:0] || row_jobs_log!==ref_row_jobs[2:0] ||
           cfg_plane_q!==ref_plane_log || cfg_row_q!==ref_row_log ||
           planes!==(4'd1<<ref_plane_log))$fatal(1,"pipelined config differs from frozen decode");
    end
`endif
    // The producer qualifies commands once, before registering the entire
    // transaction. Storage only consumes the committed token and payload.
    always @(posedge clk)if(desc_we)
        desc[desc_stage]<={desc_mask,desc_root_base,desc_root_mask,desc_gap};
`ifndef SYNTHESIS
    always @(posedge clk)if(!rst)begin
        if((cfg_valid || start || root_we || root_commit || desc_we) &&
           (state!=IDLE || cfg_pending))$fatal(1,"command committed outside idle window");
        if(load_valid && (state!=IDLE || !configured || cfg_pending))$fatal(1,"load token not executable");
        if(read_valid && ((state!=IDLE && state!=HCATCH) || !configured || cfg_pending))$fatal(1,"read token not executable");
        if(desc_we && desc_stage>=10)$fatal(1,"invalid descriptor token");
        if((cfg_valid && (start||load_valid||read_valid)) || (start && (load_valid||read_valid)) ||
           (load_valid && read_valid))$fatal(1,"multiple main command tokens");
    end
`endif
    integer v;
    always @(posedge clk) begin
        done<=0; line_valid<=0;
        if (rst) begin
            cfg_jobs_q<=0;cfg_plane_q<=0;cfg_row_q<=0;cfg_bad_q<=0;
            state<=IDLE; configured<=0; roots_valid<=0; desc_valid<=0; scale_pend<=0;
            cycles<=0; error<=0; fft<=0; inverse<=0; native64<=0;packed16<=0;stages<=0;bank_jobs_log<=0;row_jobs_log<=0;base_log<=0;job_word_log<=0;hmin_eff<=0;fmt<=0; hmin<=0;
            logn<=0; logm<=0; rowlog<=0; stage_idx<=0; q<=0; qi<=0; planes<=1;
            rows_per_buf<=1; active<=0;write_active<=0;write_stage<=0;read_gap<=0;stage_elapsed<=1;read_started<=0;root_base<=0;root_mask<=0;
            host_word<=0; line_data<=0;
            k<=0; beat<=0; part<=0; sent_all<=0;
            near_swap<=0; rbk<=0; rd_plane<=0; beat_last<=0; beat_rd<=1; rd_hi<=0; koff[0]<=0; koff[1]<=0; internal_read<=0; read_near<=0; write_far<=0; more_stages<=0;
        end else begin
            if (busy_c) cycles<=cycles+1;
            if (state==IDLE) begin
                if (cfg_valid) begin
                    scale_pend<=0;
                    fft<=cfg_fft; inverse<=cfg_inverse; native64<=cfg_ntrugen;packed16<=cfg_packed;fmt<=cfg_fmt; hmin<=cfg_hmin;
                    logn<=cfg_logn;cfg_jobs_q<=cfg_jobs_log;
                    q<=cfg_q;qi<=cfg_qinv;configured<=0;
                    roots_valid<=0;desc_valid<=0;error<=0;
                end else if (start) begin
                    scale_pend<=0;
                    error<=!configured || (stages!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc));
                    cycles<=0;
                    if (!configured || (stages!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc))) done<=1;
                    else if (stages==0) done<=1;
                    else begin state<=RESET_TILE; stage_idx<=0;write_stage<=0;write_active<=desc[0][45:30];
                        internal_read<=irf(4'd0); read_near<=inverse || irf(4'd0); write_far<=inverse && !irf(4'd0);
                        more_stages<=4'd0<stages-1; desc_nx<=desc[1]; end
                end else if (load_valid) begin
                    scale_pend<=0;
                    host_word<=0; state<=HPREP;
                end else if (read_valid) begin
                    host_word<=0; state<=HPREP;
                end
            end
            if(root_we)roots_valid<=0;
            if(root_commit)roots_valid<=1;
            if(desc_we)desc_valid[desc_stage]<=1;
            if(cfg_pipe[0])begin
                logm<=fft ? (logn==0 ? 0 : logn-1) : logn-((packed16 && hmin==0) ? 1 : hmin);
                base_log<=fft ? fmt+1 : ((packed16 && hmin!=0) ? hmin-1 : hmin);
                hmin_eff<=packed16 && hmin!=0 ? hmin-1 : hmin;
                job_word_log<=fft ? logn+fmt : logn-packed16;
                cfg_bad_q<=logn>10 || fmt==3 || cfg_jobs_q>4 ||
                    (native64 && (!fft || fmt!=1)) || (packed16 && (fft || q>=32768)) ||
                    (!fft && (hmin>2 || hmin>=logn || !q[0] || q<3 || q[31]));
            end
            if(cfg_pipe[1])begin
                rowlog<=logm>5 ? logm-5 : 0;
                stages<=logm+(!fft && packed16 && hmin==0);
                bank_jobs_log<=cfg_jobs_q<bank_capacity ? cfg_jobs_q : bank_capacity;
            end
            if(cfg_pipe[2])begin
                row_jobs_log<=cfg_jobs_q-bank_jobs_log;
                cfg_plane_q<={1'b0,base_log}+({1'b0,cfg_jobs_q}-{1'b0,bank_jobs_log});
            end
            if(cfg_pipe[3])begin
                cfg_row_q<=row_exponent;
                planes<=4'd1<<cfg_plane_q;
                cfg_bad_q<=cfg_bad_q || cfg_plane_q>3 || row_exponent>7;
            end
            if(cfg_pipe[4])begin
                rows_per_buf<=8'd1<<cfg_row_q;
                configured<=!cfg_bad_q;error<=cfg_bad_q;
            end
            if(state==HPREP)begin
                host_word<=0;state<=host_direction?HREAD:HLOAD;
            end
            if(state==HLOAD) begin
                host_word<=host_word+1'b1;
                if(host_word==host_submask) state<=IDLE;
            end
            if(state==HREAD) begin
                host_word<=host_word+1'b1;
                if(host_word==host_submask) state<=HCATCH;
            end
            for(v=0;v<4;v=v+1)
                if(cap_select[v]) line_data[32*v+:32]<=cap_oob[v] ? 32'd0 : bank_rdata[cap_bank[v]];
            if(state==HCATCH) begin
                state<=IDLE;line_valid<=1;
                if(read_accept) begin host_word<=0;state<=HPREP;end
            end
            if (state==RESET_TILE) state<=CONFIG_TILE;
            if (state==CONFIG_TILE) state<=SETTLE;
            if (state==SETTLE) state<=STAGE;
            if (state==STAGE) begin
                {active,root_base,root_mask,read_gap}<=desc[stage_idx];stage_elapsed<=1;read_started<=0;
                k<=0; beat<=0; part<=0; sent_all<=0; state<=RUN; beat_last<=0; beat_rd<=1;
                rd_plane<=rpf(6'd0,3'd0); near_swap<=1'b0; rbk<=desc[stage_idx][29:21];
                rd_hi<=hi_f(stage_idx[0],rpf(6'd0,3'd0));
                koff[0]<=read_near ? 8'd0 : koff_f(5'd0,1'b0); koff[1]<=read_near ? 8'd0 : koff_f(5'd0,1'b1);
            end
            if (state==RUN) begin
                k<=k_nx; beat<=beat_nx; part<=part_nx; sent_all<=sa_nx;
                if (!sent_all && fft) begin
                    beat_last <= beat_last ? 1'b0 : (beat==period_m2);
                    beat_rd <= beat_last ? 1'b1 : (beat<bp_m1);
                end
                rd_plane<=rpf(beat_nx,part_nx);
                rd_hi<=hi_f(stage_idx[0],rpf(beat_nx,part_nx));
                if (kstep) begin
                    near_swap<=nswap_f(k_inc); rbk<=root_base+kroot_f(k_inc,root_mask);
                    koff[0]<=read_near ? {3'b0,k_inc} : koff_f(k_inc,1'b0); koff[1]<=read_near ? {3'b0,k_inc} : koff_f(k_inc,1'b1);
                end
                if(read_started)stage_elapsed<=stage_elapsed+1'b1;
                else if(rd_issue)begin read_started<=1;stage_elapsed<=2;end
                if(read_started && more_stages && stage_elapsed==read_gap)begin
                    stage_idx<=stage_idx+1'b1;
                    {active,root_base,root_mask,read_gap}<=desc_nx;
                    k<=0;part<=0;beat<=0;sent_all<=0;read_started<=0;stage_elapsed<=1;beat_last<=0;beat_rd<=1;
                    rd_plane<=rpf(6'd0,3'd0); near_swap<=1'b0; rbk<=desc_nx[29:21];
                    internal_read<=irf(stage_idx+1'b1); read_near<=inverse || irf(stage_idx+1'b1);
                    more_stages<=stage_idx+1'b1<stages-1; desc_nx<=desc[stage_idx+2'd2];
                    rd_hi<=hi_f(!stage_idx[0],rpf(6'd0,3'd0));
                    koff[0]<=(inverse || irf(stage_idx+1'b1)) ? 8'd0 : koff_f(5'd0,1'b0);
                    koff[1]<=(inverse || irf(stage_idx+1'b1)) ? 8'd0 : koff_f(5'd0,1'b1);
                end
                if(rsp_valid[0] && out_k==last_k_r && {1'b0,out_plane}==planes_m1)begin
                    if(write_stage==stages_m1)begin state<=IDLE;done<=1;
                        scale_pend<=fft && inverse && !native64; scale_s<=logm; scale_fmt<=fmt;
                        scale_nz<=logm!=0;
                        scale_r<=(logm==0) ? 32'd0 : (32'd1 << (logm-1'b1));
                        scale_lowm<=(logm==0) ? 32'd0 : ((32'd1 << (logm-1'b1)) - 1'b1); end
                    else begin write_stage<=write_stage+1'b1;write_active<=desc[write_stage+1'b1][45:30];
                        write_far<=inverse && !irf(write_stage+1'b1); end
                end
            end
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (!tile_rst && state==RUN) begin
        if (req_valid && ((req_ready&qmask)!=qmask)) $fatal(1,"A/CG dropped tile request");
        if ((rsp_valid&write_active)!=0 && (rsp_valid&write_active)!=write_active) $fatal(1,"A/CG response phase mismatch");
        if (rd_issue && rt_addr>511) $fatal(1,"root address overflow");
    end
`endif
endmodule

// No raw reset or global execution-reset input crosses this boundary. All
// accepted flags share this priority contract; payload capture is unchanged.
module a_cg_command_decode (
    input wire live,reserved,cfg_available,load_available,read_available,
    input wire cfg_valid,start,load_valid,read_valid,root_we,root_commit,desc_we,
    input wire [3:0] desc_stage,
    output wire cfg_open,load_open,read_open,
    output wire cfg_fire,start_fire,load_fire,read_fire,root_fire,commit_fire,desc_fire
);
    wire open=live && !reserved;
    assign cfg_open=open && cfg_available;
    assign load_open=open && load_available && !cfg_valid && !start;
    assign read_open=open && read_available && !cfg_valid && !start && !load_valid;
    assign cfg_fire=cfg_open && cfg_valid;
    assign start_fire=cfg_open && !cfg_valid && start;
    assign load_fire=load_open && load_valid;
    assign read_fire=read_open && read_valid;
    assign root_fire=cfg_open && !cfg_valid && !start && root_we;
    assign commit_fire=cfg_open && !cfg_valid && !start && root_commit;
    assign desc_fire=cfg_open && !cfg_valid && !start && desc_we && desc_stage<10;
endmodule

// Same priority as accepted tokens: config/start preempt load, which preempts
// read even when its corresponding availability is low. Side writes do not
// reserve the main-command slot. No reset/live/occupancy input enters here.
module a_cg_main_request (
    input wire cfg_available,load_available,read_available,
    input wire cfg_valid,start,load_valid,read_valid,
    output wire request
);
    assign request=(cfg_valid || start) ? cfg_available :
                   load_valid ? load_available : (read_valid && read_available);
endmodule
