// 32-bit AXI4-Lite register bridge, one outstanding read/write response.
// AW and W are captured independently; B/R payloads hold under backpressure.
module flex_kernel_axil(
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 aclk CLK",
       X_INTERFACE_PARAMETER="XIL_INTERFACENAME aclk, ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET aresetn" *) input aclk,
    (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 aresetn RST",
       X_INTERFACE_PARAMETER="XIL_INTERFACENAME aresetn, POLARITY ACTIVE_LOW" *) input aresetn,
    input [11:0] s_axi_awaddr,input [2:0] s_axi_awprot,input s_axi_awvalid,output s_axi_awready,
    input [31:0] s_axi_wdata,input [3:0] s_axi_wstrb,input s_axi_wvalid,output s_axi_wready,
    output reg [1:0] s_axi_bresp,output reg s_axi_bvalid,input s_axi_bready,
    input [11:0] s_axi_araddr,input [2:0] s_axi_arprot,input s_axi_arvalid,output s_axi_arready,
    output reg [31:0] s_axi_rdata,output reg [1:0] s_axi_rresp,output reg s_axi_rvalid,input s_axi_rready
);
    reg aw_full,w_full;reg [11:0] awaddr;reg [31:0] wdata;reg [3:0] wstrb;
    reg [31:0] config_word,address_word,bank_word;
    reg [127:0] input_word,output_word,load_payload;
    reg [9:0] load_index,read_index;reg load_store;
    reg start_pending,load_pending,read_pending,read_busy,read_complete,ack,soft_reset,paused;
    wire sr,lr,rr,rv,dv,err;wire [127:0] result_word;wire [31:0] cycles;
    wire core_reset=!aresetn||soft_reset;
    assign s_axi_awready=!aw_full&&!s_axi_bvalid;
    assign s_axi_wready=!w_full&&!s_axi_bvalid;
    assign s_axi_arready=!s_axi_rvalid;
    flex_kernel_engine engine(.clk(aclk),.rst(core_reset),.pause(paused),
        .cfg_op(config_word[3:0]),.cfg_logn(config_word[7:4]),.cfg_width(config_word[9:8]),.cfg_profile(config_word[10]),
        .start_valid(start_pending),.start_ready(sr),
        .load_valid(load_pending),.load_ready(lr),.load_bank(load_store),.load_address(load_index),.load_data(load_payload),
        .read_valid(read_pending),.read_ready(rr),.read_address(read_index),.read_response_valid(rv),.read_data(result_word),
        .done_valid(dv),.done_ready(ack),.error(err),.cycles(cycles));
    function automatic [31:0] merge(input [31:0] old_word,new_word,input [3:0] strb);
        integer i;begin merge=old_word;for(i=0;i<4;i=i+1)if(strb[i])merge[i*8+:8]=new_word[i*8+:8];end
    endfunction
    wire [31:0] command=merge(0,wdata,wstrb);
    wire pending=start_pending||load_pending||read_busy;
    always @(posedge aclk)begin
        if(!aresetn)begin
            aw_full<=0;w_full<=0;s_axi_bvalid<=0;s_axi_rvalid<=0;s_axi_bresp<=0;s_axi_rresp<=0;s_axi_rdata<=0;
            config_word<=32'h200;address_word<=0;bank_word<=0;input_word<=0;output_word<=0;
            start_pending<=0;load_pending<=0;read_pending<=0;read_busy<=0;read_complete<=0;
            ack<=0;soft_reset<=0;paused<=0;
        end else begin
            ack<=0;soft_reset<=0;
            if(start_pending&&sr)start_pending<=0;
            if(load_pending&&lr)load_pending<=0;
            if(read_pending&&rr)read_pending<=0;
            if(rv)begin output_word<=result_word;read_busy<=0;read_complete<=1;end
            if(s_axi_bvalid&&s_axi_bready)s_axi_bvalid<=0;
            if(s_axi_rvalid&&s_axi_rready)s_axi_rvalid<=0;
            if(s_axi_awvalid&&s_axi_awready)begin awaddr<=s_axi_awaddr;aw_full<=1;end
            if(s_axi_wvalid&&s_axi_wready)begin wdata<=s_axi_wdata;wstrb<=s_axi_wstrb;w_full<=1;end
            if(aw_full&&w_full&&!s_axi_bvalid)begin
                aw_full<=0;w_full<=0;s_axi_bvalid<=1;s_axi_bresp<=0;
                case(awaddr)
                12'h000:config_word<=merge(config_word,wdata,wstrb);
                12'h004:begin
                    // Atomic controls: START / ACK / RESET; bit8 changes pause.
                    if((command[0]+{1'b0,command[1]}+{1'b0,command[2]})>1)s_axi_bresp<=2;
                    else if(command[2])begin
                        soft_reset<=1;start_pending<=0;load_pending<=0;read_pending<=0;
                        read_busy<=0;read_complete<=0;paused<=0;
                    end else if(command[0])begin
                        if(sr&&!pending)begin start_pending<=1;read_complete<=0;end else s_axi_bresp<=2;
                    end else if(command[1])begin
                        if(dv&&!pending&&!paused)ack<=1;else s_axi_bresp<=2;
                    end
                    if(wstrb[1]&&!command[2])paused<=wdata[8];
                end
                12'h010:address_word<=merge(address_word,wdata,wstrb);
                12'h014:bank_word<=merge(bank_word,wdata,wstrb);
                12'h018:begin
                    if(command[1:0]==1&&lr&&!pending&&address_word<1024&&bank_word<2)begin
                        load_pending<=1;load_payload<=input_word;load_index<=address_word[9:0];load_store<=bank_word[0];
                    end else if(command[1:0]==2&&rr&&!pending&&address_word<1024)begin
                        read_pending<=1;read_busy<=1;read_complete<=0;read_index<=address_word[9:0];
                    end else if(command[1:0]!=0)s_axi_bresp<=2;
                end
                12'h020:input_word[31:0]<=merge(input_word[31:0],wdata,wstrb);
                12'h024:input_word[63:32]<=merge(input_word[63:32],wdata,wstrb);
                12'h028:input_word[95:64]<=merge(input_word[95:64],wdata,wstrb);
                12'h02c:input_word[127:96]<=merge(input_word[127:96],wdata,wstrb);
                default:s_axi_bresp<=2;
                endcase
            end
            if(s_axi_arvalid&&s_axi_arready)begin
                s_axi_rvalid<=1;s_axi_rresp<=0;
                case(s_axi_araddr)
                12'h000:s_axi_rdata<=config_word;
                12'h004:s_axi_rdata<={23'b0,paused,8'b0};
                12'h008:s_axi_rdata<={26'b0,pending,read_complete,err,dv,lr,sr};
                12'h00c:s_axi_rdata<=cycles;
                12'h010:s_axi_rdata<=address_word;
                12'h014:s_axi_rdata<=bank_word;
                12'h020:s_axi_rdata<=input_word[31:0];
                12'h024:s_axi_rdata<=input_word[63:32];
                12'h028:s_axi_rdata<=input_word[95:64];
                12'h02c:s_axi_rdata<=input_word[127:96];
                12'h030:s_axi_rdata<=output_word[31:0];
                12'h034:s_axi_rdata<=output_word[63:32];
                12'h038:s_axi_rdata<=output_word[95:64];
                12'h03c:s_axi_rdata<=output_word[127:96];
                default:begin s_axi_rdata<=0;s_axi_rresp<=2;end
                endcase
            end
        end
    end
endmodule
