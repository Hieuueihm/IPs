// Private AXI4-Lite integration of the frozen 160 MHz core. One read and write outstanding.
module a_cg_axil(
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 aclk CLK", X_INTERFACE_PARAMETER="XIL_INTERFACENAME aclk, ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET aresetn" *) input wire aclk,
    (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 aresetn RST", X_INTERFACE_PARAMETER="XIL_INTERFACENAME aresetn, POLARITY ACTIVE_LOW" *) input wire aresetn,
    input wire [11:0] s_axi_awaddr, input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid, output wire s_axi_awready,
    input wire [31:0] s_axi_wdata, input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid, output wire s_axi_wready,
    output reg [1:0] s_axi_bresp, output reg s_axi_bvalid, input wire s_axi_bready,
    input wire [11:0] s_axi_araddr, input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid, output wire s_axi_arready,
    output reg [31:0] s_axi_rdata, output reg [1:0] s_axi_rresp,
    output reg s_axi_rvalid, input wire s_axi_rready
);
    reg aw_full, w_full;
    reg [11:0] awaddr;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    reg [31:0] cfg, modulus, qinv, dstage, dmask, dbase, drmask, dgap;
    reg [31:0] rdest, raddr, rdata, line_index;
    reg [127:0] input_line, output_line;
    reg cmd_cfg, cmd_start, cmd_root, cmd_commit, cmd_desc, cmd_load, cmd_read;
    reg [3:0] soft_reset, settle;
    reg read_wait, read_complete, done_sticky;
    wire core_cfg_ready, core_load_ready, core_read_ready, core_busy, core_done, core_error, core_rvalid;
    wire [31:0] core_cycles;
    wire [127:0] core_result;
    wire core_rst = !aresetn || (|soft_reset);
    wire ready_command = settle == 0 && !read_wait && !(|soft_reset);
    wire payload_open = ready_command && !core_busy;
    assign s_axi_awready = aresetn && !aw_full && !s_axi_bvalid;
    assign s_axi_wready = aresetn && !w_full && !s_axi_bvalid;
    assign s_axi_arready = aresetn && !s_axi_rvalid;
    function automatic [31:0] merge(input [31:0] old_value, new_value, input [3:0] strb);
        integer j; begin merge=old_value; for(j=0;j<4;j=j+1) if(strb[j]) merge[8*j+:8]=new_value[8*j+:8]; end
    endfunction
    wire [31:0] command = merge(0,wdata,wstrb);
    wire [31:0] status = {24'd0, !ready_command, read_complete, core_error, done_sticky, core_busy,
                          payload_open && core_read_ready, payload_open && core_load_ready,
                          payload_open && core_cfg_ready};
    a_cg_fast core(
        .clk(aclk),.rst(core_rst),.cfg_valid(cmd_cfg),.cfg_ready(core_cfg_ready),
        .cfg_fft(cfg[0]),.cfg_inverse(cfg[1]),.cfg_ntrugen(cfg[2]),.cfg_packed(cfg[3]),
        .cfg_jobs_log(cfg[6:4]),.cfg_fmt(cfg[8:7]),.cfg_hmin(cfg[10:9]),.cfg_logn(cfg[14:11]),
        .cfg_q(modulus),.cfg_qinv(qinv),.root_we(cmd_root),.root_commit(cmd_commit),
        .root_dest(rdest[15:0]),.root_addr(raddr[8:0]),.root_data(rdata),
        .desc_we(cmd_desc),.desc_stage(dstage[3:0]),.desc_mask(dmask[15:0]),
        .desc_root_base(dbase[8:0]),.desc_root_mask(drmask[4:0]),.desc_gap(dgap[15:0]),
        .load_valid(cmd_load),.load_ready(core_load_ready),.load_line(line_index[9:0]),.load_data(input_line),
        .read_valid(cmd_read),.read_ready(core_read_ready),.read_line(line_index[9:0]),
        .read_rsp_valid(core_rvalid),.read_data(core_result),.start(cmd_start),
        .busy(core_busy),.done(core_done),.error(core_error),.cycles(core_cycles)
    );
    always @(posedge aclk) begin
        if(!aresetn) begin
            aw_full<=0;w_full<=0;awaddr<=0;wdata<=0;wstrb<=0;
            s_axi_bresp<=0;s_axi_bvalid<=0;s_axi_rresp<=0;s_axi_rvalid<=0;s_axi_rdata<=0;
            cfg<=0;modulus<=0;qinv<=0;dstage<=0;dmask<=0;dbase<=0;drmask<=0;dgap<=0;
            rdest<=0;raddr<=0;rdata<=0;line_index<=0;input_line<=0;output_line<=0;
            cmd_cfg<=0;cmd_start<=0;cmd_root<=0;cmd_commit<=0;cmd_desc<=0;cmd_load<=0;cmd_read<=0;
            soft_reset<=0;settle<=6;read_wait<=0;read_complete<=0;done_sticky<=0;
        end else begin
            cmd_cfg<=0;cmd_start<=0;cmd_root<=0;cmd_commit<=0;cmd_desc<=0;cmd_load<=0;cmd_read<=0;
            soft_reset<={1'b0,soft_reset[3:1]};
            if(settle!=0) settle<=settle-1'b1;
            if(core_done) done_sticky<=1;
            if(core_rvalid && read_wait) begin output_line<=core_result;read_wait<=0;read_complete<=1;end
            if(s_axi_bvalid && s_axi_bready) s_axi_bvalid<=0;
            if(s_axi_rvalid && s_axi_rready) s_axi_rvalid<=0;
            if(s_axi_awvalid && s_axi_awready) begin aw_full<=1;awaddr<=s_axi_awaddr;end
            if(s_axi_wvalid && s_axi_wready) begin w_full<=1;wdata<=s_axi_wdata;wstrb<=s_axi_wstrb;end
            if(aw_full && w_full && !s_axi_bvalid) begin
                aw_full<=0;w_full<=0;s_axi_bvalid<=1;s_axi_bresp<=0;
                if(awaddr==12'h004) begin
                    if(command==128) begin
                        soft_reset<=15;settle<=8;read_wait<=0;read_complete<=0;done_sticky<=0;
                    end else if(command==256) begin done_sticky<=0;read_complete<=0;end
                    else if(!payload_open || command==0 || (command & (command-1))!=0 || command>64) s_axi_bresp<=2;
                    else case(command)
                        1: if(core_cfg_ready) begin cmd_cfg<=1;settle<=4;done_sticky<=0;read_complete<=0;end else s_axi_bresp<=2;
                        2: begin cmd_start<=1;settle<=4;done_sticky<=0;read_complete<=0;end
                        4: if(core_cfg_ready && raddr<512 && rdest<65536) begin cmd_root<=1;settle<=4;end else s_axi_bresp<=2;
                        8: if(core_cfg_ready) begin cmd_commit<=1;settle<=4;end else s_axi_bresp<=2;
                        16: if(core_cfg_ready && dstage<16 && dmask<65536 && dbase<512 && drmask<32 && dgap<65536) begin cmd_desc<=1;settle<=4;end else s_axi_bresp<=2;
                        32: if(core_load_ready && line_index<1024) begin cmd_load<=1;settle<=4;read_complete<=0;end else s_axi_bresp<=2;
                        64: if(core_read_ready && line_index<1024) begin cmd_read<=1;settle<=4;read_wait<=1;read_complete<=0;end else s_axi_bresp<=2;
                        default:s_axi_bresp<=2;
                    endcase
                end else if(!payload_open) s_axi_bresp<=2;
                else case(awaddr)
                    12'h010:cfg<=merge(cfg,wdata,wstrb);
                    12'h014:modulus<=merge(modulus,wdata,wstrb);
                    12'h018:qinv<=merge(qinv,wdata,wstrb);
                    12'h020:dstage<=merge(dstage,wdata,wstrb);
                    12'h024:dmask<=merge(dmask,wdata,wstrb);
                    12'h028:dbase<=merge(dbase,wdata,wstrb);
                    12'h02c:drmask<=merge(drmask,wdata,wstrb);
                    12'h030:dgap<=merge(dgap,wdata,wstrb);
                    12'h034:rdest<=merge(rdest,wdata,wstrb);
                    12'h038:raddr<=merge(raddr,wdata,wstrb);
                    12'h03c:rdata<=merge(rdata,wdata,wstrb);
                    12'h040:line_index<=merge(line_index,wdata,wstrb);
                    12'h050:input_line[31:0]<=merge(input_line[31:0],wdata,wstrb);
                    12'h054:input_line[63:32]<=merge(input_line[63:32],wdata,wstrb);
                    12'h058:input_line[95:64]<=merge(input_line[95:64],wdata,wstrb);
                    12'h05c:input_line[127:96]<=merge(input_line[127:96],wdata,wstrb);
                    default:s_axi_bresp<=2;
                endcase
            end
            if(s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid<=1;s_axi_rresp<=0;
                case(s_axi_araddr)
                    12'h000:s_axi_rdata<=32'h41434731;
                    12'h008:s_axi_rdata<=status;
                    12'h00c:s_axi_rdata<=core_cycles;
                    12'h010:s_axi_rdata<=cfg;
                    12'h014:s_axi_rdata<=modulus;
                    12'h018:s_axi_rdata<=qinv;
                    12'h020:s_axi_rdata<=dstage;
                    12'h024:s_axi_rdata<=dmask;
                    12'h028:s_axi_rdata<=dbase;
                    12'h02c:s_axi_rdata<=drmask;
                    12'h030:s_axi_rdata<=dgap;
                    12'h034:s_axi_rdata<=rdest;
                    12'h038:s_axi_rdata<=raddr;
                    12'h03c:s_axi_rdata<=rdata;
                    12'h040:s_axi_rdata<=line_index;
                    12'h050:s_axi_rdata<=input_line[31:0];
                    12'h054:s_axi_rdata<=input_line[63:32];
                    12'h058:s_axi_rdata<=input_line[95:64];
                    12'h05c:s_axi_rdata<=input_line[127:96];
                    12'h060:s_axi_rdata<=output_line[31:0];
                    12'h064:s_axi_rdata<=output_line[63:32];
                    12'h068:s_axi_rdata<=output_line[95:64];
                    12'h06c:s_axi_rdata<=output_line[127:96];
                    default:begin s_axi_rdata<=0;s_axi_rresp<=2;end
                endcase
            end
        end
    end
endmodule
