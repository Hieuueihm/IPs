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
    output reg read_rsp_valid,
    output reg [127:0] read_data,
    input wire start,
    output wire busy,
    output reg done, error,
    output reg [31:0] cycles
);
    localparam IDLE=0, HLOAD=1, HREAD=2, HCATCH=3, RESET_TILE=4,
               CONFIG_TILE=5, SETTLE=6, STAGE=7, RUN=8, HPREP=9, CFG0=10, CFG1=11, CFG2=12, CFG3=13, CFG4=14;
    reg [3:0] state;
    reg [2:0] cfg_jobs_q;
    reg [3:0] cfg_plane_q;
    reg [4:0] cfg_row_q;
    reg cfg_bad_q;
    // Reset prediction is valid only for an accepted idle start. Its local
    // registered replicas are asserted in RESET_TILE, with no extra kernel clock.
    wire reset_launch=state==IDLE && start && !cfg_valid;

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
    reg read_started;
    reg [8:0] root_base;
    reg [4:0] root_mask;
    reg [4:0] k;
    reg [5:0] beat;
    reg [2:0] part;
    reg sent_all;
    wire internal_read=packed16 && hmin==0 && (inverse ? stage_idx==0 : stage_idx==stages-1);
    wire internal_write=packed16 && hmin==0 && (inverse ? write_stage==0 : write_stage==stages-1);
    wire read_near=inverse || internal_read;
    wire write_far=inverse && !internal_write;
    wire [3:0] base_planes=4'd1<<base_log;
    wire [3:0] row_jobs=4'd1<<row_jobs_log;
    wire [2:0] limbs = 3'd1 << fmt;
    wire [5:0] period = !fft ? 6'd3 : fmt==0 ? 6'd3 : fmt==1 ? 6'd12 : 6'd45;
    wire [4:0] last_k = logm>5 ? ((6'd1 << (logm-5))-1) : 0;
    wire [3:0] fstage = inverse ? logm-1-stage_idx : stage_idx;
    wire tile_rst = rst || state==RESET_TILE;
    reg [1:0] ph;
    always @(posedge clk)
        if (tile_rst) ph<=0;
        else ph <= ph==2 ? 0 : ph+1'b1;
    wire rd_issue = state==RUN && !sent_all &&
                    (fft ? beat<base_planes : (beat==0 && ph==1));
    wire [2:0] rd_plane = fft ? ((part<<base_log) | ((beat[0] ? limbs : 0)+(beat>>1))) : part;
    wire near_swap = logm>=6 ? ((k >> (logm-6)) & 1'b1) : 1'b0;
    wire [7:0] rd_plane_base = (({5'b0,rd_plane} << rowlog) + (stage_idx[0] ? rows_per_buf : 0));
    wire [7:0] far_y_offset = logm>=6 ? (8'd1 << (logm-6)) : 0;
    wire [8:0] rt_addr = root_base + (fft ? ((k & root_mask) << (fmt+1)) + (rd_plane&(base_planes-1)) : (k & root_mask));

    assign busy = state>=RESET_TILE && state<=RUN;
    assign cfg_ready = state==IDLE;
    assign load_ready = state==IDLE && configured && !cfg_valid;
    assign read_ready = (state==IDLE || state==HCATCH) && configured && !cfg_valid && !load_valid;

    // Registered host adapter: capture request first, serve phase 0 next. A natural
    // line uses 1/2/4 bank-service clocks at FFT32/64/128, without changing
    // the compute bank map. Read responses pipeline across line boundaries.
    reg [127:0] host_data;
    reg [9:0] host_line;
    reg [1:0] host_word;
    reg host_direction;
    wire load_accept=load_valid && load_ready;
    wire read_accept=read_valid && read_ready;
    always @(posedge clk)
        if(rst) host_direction<=0;
        else if(load_accept) host_direction<=0;
        else if(read_accept) host_direction<=1;
    wire host_write=state==HLOAD;
    wire host_read=state==HREAD;
    wire [1:0] host_submask=fft && logm==0 ? (fmt==0 ? 2'd1 : 2'd3) :
                            fft && logm==1 && fmt==0 ? 2'd1 : (3'd1 << (fft ? fmt : hmin_eff))-1'b1;
    wire [1:0] host_sub=host_word;
    wire [9:0] host_line_sel=host_line;
    wire [127:0] host_data_sel=host_data;
`ifndef SYNTHESIS
    always @(posedge clk) if(!rst)begin
        if(host_read && !host_direction)$fatal(1,"read map direction not captured");
        if(host_write && host_direction)$fatal(1,"write map direction not captured");
    end
`endif
    wire [12:0] total_words=(13'd1<<job_word_log)<<(bank_jobs_log+row_jobs_log);
    wire [9:0] pmask=(11'd1 << logm)-1;
    wire [4:0] host_bank[0:3];
    wire [7:0] host_row[0:3];
    wire [3:0] host_select,host_oob;
    reg [3:0] cap_select,cap_oob;
    reg [4:0] cap_bank[0:3];
    // A natural line starts at a multiple of four words. The low two
    // word-index bits therefore map linearly into bank/row bits. Map word0
    // once, then XOR two shared basis vectors instead of four wide mappers.
    wire [1:0] host_pack=fft ? fmt : hmin_eff;
    wire [11:0] host_base_j={host_line_sel,2'b0};
    wire [11:0] host_base_element=host_base_j>>host_pack;
    wire [9:0] host_base_p=host_base_element[9:0]&pmask;
    wire [3:0] host_base_job=host_base_j>>job_word_log;
    wire [3:0] host_bank_job=host_base_job&((5'd1<<bank_jobs_log)-1);
    wire [3:0] host_row_job=host_base_job>>bank_jobs_log;
    wire [3:0] job_bank_shift=(inverse ^ host_direction) ? 5-bank_jobs_log : 5-logm-bank_jobs_log;
    wire [2:0] host_base_plane=((host_row_job<<base_log) | ((fft && logn!=0) ? (((host_base_element>>logm)&1)<<fmt) : 0));
    wire [4:0] host_base_tiny=(inverse ^ host_direction) ? host_base_p[4:0] : (host_base_p[4:0]<<(5-logm));
    wire [4:0] host_base_bank=logm>=6 ? (host_base_p[4:0]^(((host_base_p>>(logm-1))&1)<<4)) : (host_base_tiny^(host_bank_job<<job_bank_shift));
    wire [7:0] host_base_row=(host_direction && stages[0] ? rows_per_buf : 0)+({5'd0,host_base_plane}<<rowlog)+(host_base_p>>5);
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
        wire [4:0] tiny=(inverse ^ host_direction) ? p_delta : (p_delta<<(5-logm));
        assign host_bank_basis[hb]=job_bit ? (5'd1<<(job_bank_shift+hb-job_word_log)) : position_bit ? (logm>=6 ? p_delta^((pbit==logm-1) ? 5'd16 : 5'd0) : tiny) : 0;
        assign host_row_basis[hb]=lane_bit ? (8'd1<<(rowlog+hb)) : component_bit ? (8'd1<<(rowlog+fmt)) : 0;
        assign host_phase_basis[hb]=lane_bit ? (2'd1<<hb) : component_bit ? (2'd1<<fmt) : 0;
    end endgenerate
    genvar hw;
    generate for(hw=0;hw<4;hw=hw+1) begin:host_map
        localparam [1:0] J=hw;
        wire [11:0] j={host_line_sel,J};
        wire [1:0] phase=host_base_plane[1:0]^(J[0] ? host_phase_basis[0] : 2'd0)^(J[1] ? host_phase_basis[1] : 2'd0);
        wire [4:0] mapped_bank=host_base_bank^(J[0] ? host_bank_basis[0] : 5'd0)^(J[1] ? host_bank_basis[1] : 5'd0);
        wire [7:0] mapped_row=host_base_row^(J[0] ? host_row_basis[0] : 8'd0)^(J[1] ? host_row_basis[1] : 8'd0);
        wire mapped_oob=j>=total_words;
        reg [4:0] bank_q;
        reg [7:0] row_q;
        reg [1:0] phase_q;
        reg oob_q;
        always @(posedge clk) if(state==HPREP)begin
            bank_q<=mapped_bank;row_q<=mapped_row;phase_q<=phase;oob_q<=mapped_oob;
        end
        assign host_bank[hw]=bank_q;
        assign host_row[hw]=row_q;
        assign host_select[hw]=((phase_q & host_submask)==host_sub);
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

    // Each bank has exactly one synchronous read and one write port. All rows
    // hold live runtime data; no initial contents or tied-off mode inputs.
    wire [31:0] bank_rdata [0:31];
    wire [31:0] roots [0:15];
    wire [15:0] rsp_valid, req_ready;
    wire [63:0] rsp_data [0:15];
    wire [7:0] rsp_tag [0:15];
    wire prog_valid;
    wire [15:0] prog_mask;
    wire [1:0] prog_product;
    wire [3:0] prog_step;
    wire [4:0] out_k = rsp_tag[0][7:3];
    wire [2:0] out_plane = rsp_tag[0][2:0];
    wire out_near_swap = logm>=6 ? ((out_k>>(logm-6))&1'b1) : 1'b0;
    wire [7:0] wr_plane_base = (({5'b0,out_plane}<<rowlog) + (!write_stage[0] ? rows_per_buf : 0));
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
        wire [7:0] wr_row = wr_plane_base + (write_far ? ((out_k>>1) + ((out_k[0]!=(b>>4)) ? far_y_offset : 0)) : out_k);
        wire [7:0] rd_row = rd_plane_base + (read_near ? k : ((k>>1) + ((k[0]!=(b>>4)) ? far_y_offset : 0)));
        wire compute_read_en = read_near ? (near_swap ? active[TF^8] : active[TF]) : active[TI];
        reg hr,hw;
        reg [7:0] hra,hwa;
        reg [31:0] hwd;
        integer hj;
        always @* begin
            hr=0;hw=0;hra=0;hwa=0;hwd=0;
            for(hj=0;hj<4;hj=hj+1) begin
                if(host_read && host_select[hj] && !host_oob[hj] && host_bank[hj]==b) begin hr=1;hra=host_row[hj];end
                if(host_write && host_select[hj] && !host_oob[hj] && host_bank[hj]==b) begin
                    hw=1;hwa=host_row[hj];hwd=host_data_sel[32*hj+:32];
                end
            end
        end
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
        if (rd_issue) begin r_far<=k[0]; r_near<=near_swap; rgeom<=read_near;rdummy<=internal_read && logm==0;rtag<={k,rd_plane};rmask<=active;rscale<=fft && inverse && !native64 && stage_idx==stages-1; rfirst<=fft && beat==0; if(!fft)rscale<=internal_read; end
        if (rvalid) begin req_tag<=rtag;qmask<=rmask;qscale<=rscale;qfirst<=rfirst;end
    end
    genvar t;
    generate for (t=0;t<16;t=t+1) begin : engine
        (* ram_style="block" *) reg [31:0] root_mem [0:511];
        reg [31:0] root_q;
        always @(posedge clk) begin
            if (rd_issue) root_q<=root_mem[rt_addr];
            if (root_we && state==IDLE && root_dest[t]) root_mem[root_addr]<=root_data;
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
        always @(posedge clk) reset_local <= rst || reset_launch;
`ifndef SYNTHESIS
        always @(posedge clk) if(!rst)begin
            if(state==RESET_TILE && reset_local!==1'b1)$fatal(1,"local reset not asserted");
            if(state==CONFIG_TILE && reset_local!==1'b0)$fatal(1,"local reset overlaps tile config");
        end
`endif
        wire unused_idle;
        tile_a2 #(.TREN_MANG(1),.IN_REG(1),.EN_REG(0),.PHASE(0)) u_tile (
            .clk(clk),.rst(reset_local),.en(1'b1),.idle(unused_idle),
            .cfg_we(state==CONFIG_TILE),.cfg_slot(1'b0),.cfg_q(packed16 ? {q[15:0],q[15:0]} : q),.cfg_qinv(packed16 ? {qi[15:0],qi[15:0]} : qi),
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
    // Accepted first beat -> first limb product = 2L+4 clocks, IN_REG=1.
    reg [11:0] program_delay;
    reg [15:0] mask_delay[0:11];
    reg [15:0] program_mask;
    wire [3:0] program_d=fmt==0 ? 5 : fmt==1 ? (native64 && inverse ? 9 : 7) : 11;
    integer mi;
    wire first_fft = req_valid && fft && qfirst;
    wire program_start = fmt==0 ? program_delay[5] : fmt==1 ? (native64 && inverse ? program_delay[9] : program_delay[7]) : program_delay[11];
    assign prog_mask=program_start ? mask_delay[program_d] : program_mask;
    reg program_busy;
    reg [1:0] product;
    reg [3:0] step;
    wire [3:0] last_step = fmt==0 ? 0 : fmt==1 ? 3 : 14;
    assign prog_valid = program_start || program_busy;
    assign prog_product = program_start ? 0 : product;
    assign prog_step = program_start ? 0 : step;
    always @(posedge clk) begin
        if (tile_rst) begin program_delay<=0; program_busy<=0; product<=0; step<=0; end
        else begin
            program_delay <= {program_delay[10:0],first_fft};
            mask_delay[0]<=qmask;
            for(mi=1;mi<12;mi=mi+1)mask_delay[mi]<=mask_delay[mi-1];
            if(program_start)program_mask<=mask_delay[program_d];
            if (prog_valid) begin
                if (prog_step==last_step) begin
                    step<=0;
                    if (prog_product==2) begin program_busy<=0; product<=0; end
                    else begin program_busy<=1; product<=prog_product+1'b1; end
                end else begin program_busy<=1; step<=prog_step+1'b1; product<=prog_product; end
            end
        end
    end

    wire [9:0] wanted_desc = (11'd1 << stages)-1;
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
    always @(posedge clk) if(!rst && state==CFG4)begin
        if(cfg_bad_q!==ref_bad || logm!==ref_logm || base_log!==ref_base_log[2:0] ||
           bank_jobs_log!==ref_bank_jobs[2:0] || row_jobs_log!==ref_row_jobs[2:0] ||
           cfg_plane_q!==ref_plane_log || cfg_row_q!==ref_row_log ||
           planes!==(4'd1<<ref_plane_log))$fatal(1,"pipelined config differs from frozen decode");
    end
`endif
    integer v;
    always @(posedge clk) begin
        done<=0; read_rsp_valid<=0;
        if (rst) begin
            cfg_jobs_q<=0;cfg_plane_q<=0;cfg_row_q<=0;cfg_bad_q<=0;
            state<=IDLE; configured<=0; roots_valid<=0; desc_valid<=0;
            cycles<=0; error<=0; fft<=0; inverse<=0; native64<=0;packed16<=0;stages<=0;bank_jobs_log<=0;row_jobs_log<=0;base_log<=0;job_word_log<=0;hmin_eff<=0;fmt<=0; hmin<=0;
            logn<=0; logm<=0; rowlog<=0; stage_idx<=0; q<=0; qi<=0; planes<=1;
            rows_per_buf<=1; active<=0;write_active<=0;write_stage<=0;read_gap<=0;stage_elapsed<=0;read_started<=0;root_base<=0;root_mask<=0;
            host_word<=0; read_data<=0;
            k<=0; beat<=0; part<=0; sent_all<=0;
        end else begin
            if (busy) cycles<=cycles+1;
            if (state==IDLE) begin
                if (cfg_valid) begin
                    fft<=cfg_fft; inverse<=cfg_inverse; native64<=cfg_ntrugen;packed16<=cfg_packed;fmt<=cfg_fmt; hmin<=cfg_hmin;
                    logn<=cfg_logn;cfg_jobs_q<=cfg_jobs_log;
                    q<=cfg_q;qi<=cfg_qinv;configured<=0;
                    roots_valid<=0;desc_valid<=0;error<=0;state<=CFG0;
                end else if (start) begin
                    error<=!configured || (stages!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc));
                    cycles<=0;
                    if (!configured || (stages!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc))) done<=1;
                    else if (stages==0) done<=1;
                    else begin state<=RESET_TILE; stage_idx<=0;write_stage<=0;write_active<=desc[0][45:30]; end
                end else if (load_valid && load_ready) begin
                    host_data<=load_data; host_line<=load_line; host_word<=0; state<=HPREP;
                end else if (read_valid && read_ready) begin
                    host_line<=read_line; host_word<=0; state<=HPREP;
                end
                if (root_we) roots_valid<=0;
                if (root_commit) roots_valid<=1;
                if (desc_we && desc_stage<10) begin
                    desc[desc_stage]<={desc_mask,desc_root_base,desc_root_mask,desc_gap};
                    desc_valid[desc_stage]<=1;
                end
            end
            if(state==CFG0)begin
                logm<=fft ? (logn==0 ? 0 : logn-1) : logn-((packed16 && hmin==0) ? 1 : hmin);
                base_log<=fft ? fmt+1 : ((packed16 && hmin!=0) ? hmin-1 : hmin);
                hmin_eff<=packed16 && hmin!=0 ? hmin-1 : hmin;
                job_word_log<=fft ? logn+fmt : logn-packed16;
                cfg_bad_q<=logn>10 || fmt==3 || cfg_jobs_q>4 ||
                    (native64 && (!fft || fmt!=1)) || (packed16 && (fft || q>=32768)) ||
                    (!fft && (hmin>2 || hmin>=logn || !q[0] || q<3 || q[31]));
                state<=CFG1;
            end
            if(state==CFG1)begin
                rowlog<=logm>5 ? logm-5 : 0;
                stages<=logm+(!fft && packed16 && hmin==0);
                bank_jobs_log<=cfg_jobs_q<bank_capacity ? cfg_jobs_q : bank_capacity;
                state<=CFG2;
            end
            if(state==CFG2)begin
                row_jobs_log<=cfg_jobs_q-bank_jobs_log;
                cfg_plane_q<={1'b0,base_log}+({1'b0,cfg_jobs_q}-{1'b0,bank_jobs_log});
                state<=CFG3;
            end
            if(state==CFG3)begin
                cfg_row_q<=row_exponent;
                planes<=4'd1<<cfg_plane_q;
                cfg_bad_q<=cfg_bad_q || cfg_plane_q>3 || row_exponent>7;
                state<=CFG4;
            end
            if(state==CFG4)begin
                rows_per_buf<=8'd1<<cfg_row_q;
                configured<=!cfg_bad_q;error<=cfg_bad_q;state<=IDLE;
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
                if(cap_select[v]) read_data[32*v+:32]<=cap_oob[v] ? 32'd0 : bank_rdata[cap_bank[v]];
            if(state==HCATCH) begin
                state<=IDLE;read_rsp_valid<=1;
                if(read_accept) begin host_line<=read_line;host_word<=0;state<=HPREP;end
            end
            if (state==RESET_TILE) state<=CONFIG_TILE;
            if (state==CONFIG_TILE) state<=SETTLE;
            if (state==SETTLE) state<=STAGE;
            if (state==STAGE) begin
                {active,root_base,root_mask,read_gap}<=desc[stage_idx];stage_elapsed<=0;read_started<=0;
                k<=0; beat<=0; part<=0; sent_all<=0; state<=RUN;
            end
            if (state==RUN) begin
                if (!sent_all) begin
                    if (fft) begin
                        if (beat==period-1) begin
                            beat<=0;
                            if(part==row_jobs-1)begin part<=0;if(k==last_k)sent_all<=1;else k<=k+1'b1;end else part<=part+1'b1;
                        end else beat<=beat+1'b1;
                    end else if (rd_issue) begin
                        if (part==planes-1) begin
                            part<=0;
                            if (k==last_k) sent_all<=1; else k<=k+1'b1;
                        end else part<=part+1'b1;
                    end
                end
                if(read_started)stage_elapsed<=stage_elapsed+1'b1;
                else if(rd_issue)begin read_started<=1;stage_elapsed<=1;end
                if(read_started && stage_idx<stages-1 && stage_elapsed==read_gap-1'b1)begin
                    stage_idx<=stage_idx+1'b1;
                    {active,root_base,root_mask,read_gap}<=desc[stage_idx+1'b1];
                    k<=0;part<=0;beat<=0;sent_all<=0;read_started<=0;stage_elapsed<=0;
                end
                if(rsp_valid[0] && out_k==last_k && out_plane==planes-1)begin
                    if(write_stage==stages-1)begin state<=IDLE;done<=1;end
                    else begin write_stage<=write_stage+1'b1;write_active<=desc[write_stage+1'b1][45:30];end
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
