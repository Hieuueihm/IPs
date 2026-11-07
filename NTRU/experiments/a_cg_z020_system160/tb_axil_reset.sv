`timescale 1ns/1ps
module tb_acg_axil_reset;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    reg [11:0] awaddr=0,araddr=0;
    reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
    reg [31:0] wdata=0;reg [3:0] wstrb=15;
    wire awready,wready,bvalid,arready,rvalid;wire [1:0] bresp,rresp;wire [31:0] rdata;
    a_cg_axil dut(.aclk(clk),.aresetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(3'b0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready));
    integer writes=0,reads=0;
    task automatic write_reg(input [11:0] addr,input [31:0] value,input [3:0] strb,input [1:0] expected_resp);
        integer gap;reg [1:0] held;
        begin
            gap=writes%3;writes=writes+1;
            fork
                begin
                    repeat(gap)@(negedge clk);
                    @(negedge clk);awaddr=addr;awvalid=1;
                    @(posedge clk);while(!awready)@(posedge clk);
                    @(negedge clk);awvalid=0;
                end
                begin
                    repeat(2-gap)@(negedge clk);
                    @(negedge clk);wdata=value;wstrb=strb;wvalid=1;
                    @(posedge clk);while(!wready)@(posedge clk);
                    @(negedge clk);wvalid=0;
                end
            join
            while(!bvalid)@(negedge clk);
            held=bresp;
            repeat(2)begin @(negedge clk);if(!bvalid||bresp!==held)$fatal(1,"B changed under stall");end
            if(held!==expected_resp)$fatal(1,"write response addr=%h got=%h expected=%h",addr,held,expected_resp);
            bready=1;@(negedge clk);bready=0;
        end
    endtask
    task automatic read_reg(input [11:0] addr,output [31:0] value,input [1:0] expected_resp);
        reg [31:0] held;reg [1:0] response;
        begin
            reads=reads+1;
            @(negedge clk);araddr=addr;arvalid=1;
            @(posedge clk);while(!arready)@(posedge clk);
            @(negedge clk);arvalid=0;
            while(!rvalid)@(negedge clk);
            held=rdata;response=rresp;
            repeat(2)begin @(negedge clk);if(!rvalid||rdata!==held||rresp!==response)$fatal(1,"R changed under stall");end
            if(response!==expected_resp)$fatal(1,"read response");
            value=held;rready=1;@(negedge clk);rready=0;
        end
    endtask

    reg [31:0] value;
    task release_reset;
        begin resetn=0;awvalid=0;wvalid=0;arvalid=0;bready=0;rready=0;
        repeat(3)@(negedge clk);resetn=1;repeat(10)@(negedge clk);
        if(bvalid||rvalid)$fatal(1,"stale response survived reset");end
    endtask
    initial begin
        release_reset();
        // An AW accepted before reset cannot pair with a W after reset.
        awaddr=12'h014;awvalid=1;@(negedge clk);awvalid=0;
        release_reset();
        wdata=32'hdeadbeef;wstrb=15;wvalid=1;@(negedge clk);wvalid=0;
        repeat(5)@(negedge clk);if(bvalid)$fatal(1,"AW survived reset");
        release_reset();
        // Symmetric case: W before reset cannot pair with AW after reset.
        wdata=32'hdeadbeef;wstrb=15;wvalid=1;@(negedge clk);wvalid=0;
        release_reset();awaddr=12'h014;awvalid=1;@(negedge clk);awvalid=0;
        repeat(5)@(negedge clk);if(bvalid)$fatal(1,"W survived reset");
        release_reset();
        // B response held under backpressure is flushed.
        awaddr=12'h014;awvalid=1;wdata=123;wvalid=1;
        @(negedge clk);awvalid=0;wvalid=0;
        repeat(5)@(negedge clk);if(!bvalid)$fatal(1,"missing held B");
        release_reset();read_reg(12'h014,value,0);if(value!=0)$fatal(1,"payload not reset");
        // R response held under backpressure is flushed.
        araddr=0;arvalid=1;@(negedge clk);arvalid=0;
        repeat(3)@(negedge clk);if(!rvalid)$fatal(1,"missing held R");
        release_reset();read_reg(0,value,0);if(value!=32'h41434731)$fatal(1,"ID after reset");
        $display("AXI_RESET aw_split=1 w_split=1 b_pending=1 r_pending=1 PASS");$finish;
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
