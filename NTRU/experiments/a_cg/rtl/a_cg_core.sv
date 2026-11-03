// Isolated A + constant-geometry prototype, 16 identical engines, 64 DSP.
// One runtime context; host loads direction-specific roots and stage descriptors.
// Input/output natural order. Full host adapter and root cache are synthesized.
module a_cg_core (
    input wire clk, rst,
    input wire cfg_valid,
    output wire cfg_ready,
    input wire cfg_fft, cfg_inverse,
    input wire [1:0] cfg_fmt, cfg_hmin,
    input wire [3:0] cfg_logn,
    input wire [31:0] cfg_q, cfg_qinv,
    input wire root_we, root_commit,
    input wire [3:0] root_bank,
    input wire [8:0] root_addr,
    input wire [31:0] root_data,
    input wire desc_we,
    input wire [3:0] desc_stage,
    input wire [15:0] desc_mask,
    input wire [8:0] desc_root_base,
    input wire [4:0] desc_root_mask,
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
               CONFIG_TILE=5, SETTLE=6, STAGE=7, RUN=8;
    reg [3:0] state;
    reg fft, inverse, configured, roots_valid;
    reg [1:0] fmt, hmin;
    reg [3:0] logn, logm, rowlog, stage_idx;
    reg [31:0] q, qi;
    reg [3:0] planes;
    reg [7:0] rows_per_buf;
    reg [9:0] desc_valid;
    (* ram_style="distributed" *) reg [29:0] desc [0:9];
    reg [15:0] active;
    reg [8:0] root_base;
    reg [4:0] root_mask;
    reg [4:0] k;
    reg [5:0] beat;
    reg [1:0] part;
    reg sent_all;
    wire [2:0] limbs = 3'd1 << fmt;
    wire [5:0] period = !fft ? 6'd3 : fmt==0 ? 6'd3 : fmt==1 ? 6'd12 : 6'd48;
    wire [4:0] last_k = logm>5 ? ((6'd1 << (logm-5))-1) : 0;
    wire [3:0] fstage = inverse ? logm-1-stage_idx : stage_idx;
    wire tile_rst = rst || state==RESET_TILE;
    reg [1:0] ph;
    always @(posedge clk)
        if (tile_rst) ph<=0;
        else ph <= ph==2 ? 0 : ph+1'b1;
    wire rd_issue = state==RUN && !sent_all &&
                    (fft ? beat<planes : (beat==0 && ph==1));
    wire [2:0] rd_plane = fft ? ((beat[0] ? limbs : 0) + (beat>>1)) : {1'b0,part};
    wire near_swap = logm>=6 ? ((k >> (logm-6)) & 1'b1) : 1'b0;
    wire [7:0] rd_plane_base = (({5'b0,rd_plane} << rowlog) + (stage_idx[0] ? rows_per_buf : 0));
    wire [7:0] far_y_offset = logm>=6 ? (8'd1 << (logm-6)) : 0;
    wire [8:0] rt_addr = root_base + (fft ? ((k & root_mask) << (fmt+1)) + rd_plane : (k & root_mask));

    assign busy = state>=RESET_TILE;
    assign cfg_ready = state==IDLE;
    assign load_ready = state==IDLE && configured && !cfg_valid;
    assign read_ready = state==IDLE && configured && !cfg_valid && !load_valid;

    // Serialized 128-bit host line adapter. It is part of this top, not a stub.
    reg [127:0] host_data;
    reg [9:0] host_line;
    reg [1:0] host_word;
    reg [1:0] capture_word;
    reg capture_valid, capture_oob;
    reg [4:0] capture_bank;
    wire [11:0] host_j = {host_line,host_word};
    wire [12:0] total_words = (13'd1 << logn) << (fft ? fmt : 0);
    wire host_oob = host_j>=total_words;
    wire [11:0] host_element = host_j >> (fft ? fmt : hmin);
    wire [9:0] pmask = (11'd1 << logm)-1;
    wire [9:0] host_p = host_element[9:0] & pmask;
    wire [2:0] host_plane = fft ? (((host_element >> logm)&1) << fmt) + (host_j & (limbs-1))
                                : host_j & (planes-1);
    wire host_out = state==HREAD || state==HCATCH;
    wire [3:0] host_layout = host_out ? (inverse ? 0 : logm) : (inverse ? logm : 0);
    // Only the first/final layouts reach the host: E_0(p)=p<<(5-n),
    // E_n(p)=p. Intermediate tiny layouts are encoded by stage active masks.
    wire [4:0] host_tiny_bank = (inverse ^ host_out) ? host_p[4:0] : (host_p[4:0] << (5-logm));
    wire [4:0] host_bank = logm>=6 ? (host_p[4:0] ^ (((host_p>>(logm-1))&1)<<4))
                                                   : host_tiny_bank;
    wire [7:0] host_row = (host_out && logm[0] ? rows_per_buf : 0)
                                       + ({5'd0,host_plane}<<rowlog) + (host_p>>5);
    wire host_write = state==HLOAD && !host_oob;
    wire host_read = state==HREAD && !host_oob;

    // Each bank has exactly one synchronous read and one write port. All rows
    // hold live runtime data; no initial contents or tied-off mode inputs.
    wire [31:0] bank_rdata [0:31];
    wire [31:0] roots [0:15];
    wire [15:0] rsp_valid, req_ready;
    wire [63:0] rsp_data [0:15];
    wire [7:0] rsp_tag [0:15];
    wire prog_valid;
    wire [1:0] prog_product;
    wire [3:0] prog_step;
    wire [4:0] out_k = rsp_tag[0][7:3];
    wire [2:0] out_plane = rsp_tag[0][2:0];
    wire out_near_swap = logm>=6 ? ((out_k>>(logm-6))&1'b1) : 1'b0;
    wire [7:0] wr_plane_base = (({5'b0,out_plane}<<rowlog) + (!stage_idx[0] ? rows_per_buf : 0));
    genvar b;
    generate for (b=0;b<32;b=b+1) begin : data_bank
        (* ram_style="block" *) reg [31:0] mem [0:255];
        reg [31:0] dout;
        localparam integer TF=b>>1, TI=b&15;
        wire [31:0] forward_data = out_near_swap ? rsp_data[TF^8][32*(b&1)+:32]
                                                                : rsp_data[TF][32*(b&1)+:32];
        wire [31:0] inverse_data = (out_k[0]==(b>>4)) ? rsp_data[TI][0+:32] : rsp_data[TI][32+:32];
        wire forward_valid = out_near_swap ? (active[TF^8] && rsp_valid[TF^8]) : (active[TF] && rsp_valid[TF]);
        wire inverse_valid = active[TI] && rsp_valid[TI];
        wire compute_write = state==RUN && (inverse ? inverse_valid : forward_valid);
        wire [7:0] wr_row = wr_plane_base + (inverse ? ((out_k>>1) + ((out_k[0]!=(b>>4)) ? far_y_offset : 0)) : out_k);
        wire [7:0] rd_row = rd_plane_base + (inverse ? k : ((k>>1) + ((k[0]!=(b>>4)) ? far_y_offset : 0)));
        wire compute_read_en = inverse ? (near_swap ? active[TF^8] : active[TF]) : active[TI];
        wire ren = (rd_issue && compute_read_en) || (host_read && host_bank==b);
        wire [7:0] ra = state==HREAD ? host_row : rd_row;
        wire wen = compute_write || (host_write && host_bank==b);
        wire [7:0] wa = state==HLOAD ? host_row : wr_row;
        wire [31:0] wd = state==HLOAD ? host_data[32*host_word+:32] : inverse ? inverse_data : forward_data;
        always @(posedge clk) begin
            if (ren) dout <= mem[ra];
            if (wen) mem[wa] <= wd;
        end
        assign bank_rdata[b]=dout;
    end endgenerate

    reg rvalid, req_valid;
    reg r_far, r_near;
    reg [7:0] rtag, req_tag;
    reg [31:0] req_x[0:15], req_y[0:15], req_root[0:15];
    always @(posedge clk) begin
        if (rst || state!=RUN) begin rvalid<=0; req_valid<=0; end
        else begin rvalid<=rd_issue; req_valid<=rvalid; end
        if (rd_issue) begin r_far<=k[0]; r_near<=near_swap; rtag<={k,rd_plane}; end
        if (rvalid) req_tag<=rtag;
    end
    genvar t;
    generate for (t=0;t<16;t=t+1) begin : engine
        (* ram_style="block" *) reg [31:0] root_mem [0:511];
        reg [31:0] root_q;
        always @(posedge clk) begin
            if (rd_issue) root_q<=root_mem[rt_addr];
            if (root_we && state==IDLE && root_bank==t) root_mem[root_addr]<=root_data;
            if (rvalid) begin
                // Four candidates per input: two far and two near banks.
                req_x[t] <= inverse ? (r_near ? bank_rdata[(2*t)^16] : bank_rdata[2*t])
                                    : (r_far ? bank_rdata[t+16] : bank_rdata[t]);
                req_y[t] <= inverse ? (r_near ? bank_rdata[(2*t+1)^16] : bank_rdata[2*t+1])
                                    : (r_far ? bank_rdata[t] : bank_rdata[t+16]);
                req_root[t]<=root_q;
            end
        end
        wire unused_idle;
        tile_a #(.TREN_MANG(1),.IN_REG(1),.EN_REG(0),.PHASE(0)) u_tile (
            .clk(clk),.rst(tile_rst),.en(1'b1),.idle(unused_idle),
            .cfg_we(state==CONFIG_TILE),.cfg_slot(1'b0),.cfg_q(q),.cfg_qinv(qi),
            .cfg_fmt(fmt),.cfg_shift(logm),.cfg_floor(1'b0),.cfg_halve(inverse),
            .ext_fft_valid(prog_valid && active[t]),.ext_fft_mpr(prog_product),.ext_fft_mst(prog_step),
            .req_valid(req_valid && active[t]),.req_ready(req_ready[t]),
            .req_mode(fft ? 2'd1 : 2'd0),.req_dir(inverse),.req_slot(1'b0),
            .req_sign(fft && inverse && stage_idx==logm-1),
            .req_data({req_y[t],req_x[t]}),.req_root(req_root[t]),.req_tag(req_tag),
            .rsp_valid(rsp_valid[t]),.rsp_data(rsp_data[t]),.rsp_tag(rsp_tag[t])
        );
    end endgenerate

    // One product program for all engines; state/multiplier operands stay local.
    // Accepted first beat -> first limb product = 2L+4 clocks, IN_REG=1.
    reg [11:0] program_delay;
    wire first_fft = req_valid && fft && req_tag[2:0]==0;
    wire program_start = fmt==0 ? program_delay[5] : fmt==1 ? program_delay[7] : program_delay[11];
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
            if (prog_valid) begin
                if (prog_step==last_step) begin
                    step<=0;
                    if (prog_product==2) begin program_busy<=0; product<=0; end
                    else begin program_busy<=1; product<=prog_product+1'b1; end
                end else begin program_busy<=1; step<=prog_step+1'b1; product<=prog_product; end
            end
        end
    end

    wire [9:0] wanted_desc = (11'd1 << logm)-1;
    wire cfg_bad = cfg_logn>10 || cfg_fmt==3 || (!cfg_fft &&
                         (cfg_hmin>2 || cfg_hmin>=cfg_logn || !cfg_q[0] || cfg_q<3 || cfg_q[31]));
    wire [3:0] cfg_logm = cfg_fft ? (cfg_logn==0 ? 0 : cfg_logn-1) : cfg_logn-cfg_hmin;
    integer v;
    always @(posedge clk) begin
        done<=0; read_rsp_valid<=0;
        if (rst) begin
            state<=IDLE; configured<=0; roots_valid<=0; desc_valid<=0;
            cycles<=0; error<=0; fft<=0; inverse<=0; fmt<=0; hmin<=0;
            logn<=0; logm<=0; rowlog<=0; stage_idx<=0; q<=0; qi<=0; planes<=1;
            rows_per_buf<=1; active<=0; root_base<=0; root_mask<=0;
            host_word<=0; capture_valid<=0; read_data<=0;
            k<=0; beat<=0; part<=0; sent_all<=0;
        end else begin
            if (busy) cycles<=cycles+1;
            if (state==IDLE) begin
                capture_valid<=0;
                if (cfg_valid) begin
                    fft<=cfg_fft; inverse<=cfg_inverse; fmt<=cfg_fmt; hmin<=cfg_hmin;
                    logn<=cfg_logn; logm<=cfg_logm; rowlog<=cfg_logm>5 ? cfg_logm-5 : 0;
                    planes<=cfg_fft ? (4'd2<<cfg_fmt) : (4'd1<<cfg_hmin);
                    rows_per_buf<=(cfg_logm>5 ? (8'd1<<(cfg_logm-5)) : 8'd1)
                                   << (cfg_fft ? cfg_fmt+1 : cfg_hmin);
                    q<=cfg_q; qi<=cfg_qinv; configured<=!cfg_bad;
                    roots_valid<=0; desc_valid<=0; error<=cfg_bad;
                end else if (start) begin
                    error<=!configured || (logm!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc));
                    cycles<=0;
                    if (!configured || (logm!=0 && (!roots_valid || (desc_valid&wanted_desc)!=wanted_desc))) done<=1;
                    else if (logm==0) done<=1;
                    else begin state<=RESET_TILE; stage_idx<=0; end
                end else if (load_valid && load_ready) begin
                    host_data<=load_data; host_line<=load_line; host_word<=0; state<=HLOAD;
                end else if (read_valid && read_ready) begin
                    host_line<=read_line; host_word<=0; read_data<=0; state<=HREAD;
                end
                if (root_we) roots_valid<=0;
                if (root_commit) roots_valid<=1;
                if (desc_we && desc_stage<10) begin
                    desc[desc_stage]<={desc_mask,desc_root_base,desc_root_mask};
                    desc_valid[desc_stage]<=1;
                end
            end
            if (state==HLOAD) begin
                host_word<=host_word+1'b1;
                if (host_word==3) state<=IDLE;
            end
            if (state==HREAD) begin
                capture_valid<=1; capture_word<=host_word; capture_bank<=host_bank; capture_oob<=host_oob;
                host_word<=host_word+1'b1;
                if (host_word==3) state<=HCATCH;
            end
            if ((state==HREAD || state==HCATCH) && capture_valid)
                read_data[32*capture_word+:32]<=capture_oob ? 32'd0 : bank_rdata[capture_bank];
            if (state==HCATCH) begin state<=IDLE; read_rsp_valid<=1; capture_valid<=0; end
            if (state==RESET_TILE) state<=CONFIG_TILE;
            if (state==CONFIG_TILE) state<=SETTLE;
            if (state==SETTLE) state<=STAGE;
            if (state==STAGE) begin
                {active,root_base,root_mask}<=desc[stage_idx];
                k<=0; beat<=0; part<=0; sent_all<=0; state<=RUN;
            end
            if (state==RUN) begin
                if (!sent_all) begin
                    if (fft) begin
                        if (beat==period-1) begin
                            beat<=0;
                            if (k==last_k) sent_all<=1; else k<=k+1'b1;
                        end else beat<=beat+1'b1;
                    end else if (rd_issue) begin
                        if (part==planes-1) begin
                            part<=0;
                            if (k==last_k) sent_all<=1; else k<=k+1'b1;
                        end else part<=part+1'b1;
                    end
                end
                if (rsp_valid[0] && out_k==last_k && out_plane==planes-1) begin
                    if (stage_idx==logm-1) begin state<=IDLE; done<=1; end
                    else begin stage_idx<=stage_idx+1'b1; state<=STAGE; end
                end
            end
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (!tile_rst && state==RUN) begin
        if (req_valid && ((req_ready&active)!=active)) $fatal(1,"A/CG dropped tile request");
        if ((rsp_valid&active)!=0 && (rsp_valid&active)!=active) $fatal(1,"A/CG response phase mismatch");
        if (rd_issue && rt_addr>511) $fatal(1,"root address overflow");
    end
`endif
endmodule
