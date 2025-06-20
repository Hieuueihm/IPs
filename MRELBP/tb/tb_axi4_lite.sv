`timescale 1ns/1ps

module tb_axi4_lite;

    // Parameters
    localparam ADDR_WIDTH = 8;
    localparam DATA_WIDTH = 32;

    // DUT signals
    logic clk;
    logic rst_n;

    logic [ADDR_WIDTH-1:0] s_axi_awaddr;
    logic                  s_axi_awvalid;
    logic                  s_axi_awready;

    logic [DATA_WIDTH-1:0] s_axi_wdata;
    logic [3:0]            s_axi_wstrb;
    logic                  s_axi_wvalid;
    logic                  s_axi_wready;

    logic [1:0]            s_axi_bresp;
    logic                  s_axi_bvalid;
    logic                  s_axi_bready;

    logic [ADDR_WIDTH-1:0] s_axi_araddr;
    logic                  s_axi_arvalid;
    logic                  s_axi_arready;

    logic [DATA_WIDTH-1:0] s_axi_rdata;
    logic [1:0]            s_axi_rresp;
    logic                  s_axi_rvalid;
    logic                  s_axi_rready;

    logic  status_reg_o;

    // Clock generation
    always #5 clk = ~clk;

    // DUT instantiation
    axi4_lite dut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .gpio_o(status_reg_o)
    );

    // Task: AXI Write
    task axi_write(input logic [31:0] addr, input logic [31:0] data);
        begin
            // Write address
            s_axi_awaddr  = addr;
            s_axi_awvalid = 1;
            // Write data
            s_axi_wdata   = data;
            s_axi_wstrb   = 4'hF;
            s_axi_bready =  1'b1;
            s_axi_wvalid  = 1;
            bready_wait: while (!s_axi_awready || !s_axi_wready) @(posedge clk);
            s_axi_awvalid = 0;
            s_axi_wvalid  = 0;

            // Wait for bvalid
            s_axi_bready = 1;
            @(posedge clk);
            while (!s_axi_bvalid) @(posedge clk);
            s_axi_bready = 0;
            $display("[WRITE] Addr = 0x%08X, Data = 0x%08X", addr, data);
        end
    endtask

    // Task: AXI Read
    task axi_read(input logic [31:0] addr);
        begin
            s_axi_araddr  = addr;
            s_axi_arvalid = 1;
            @(posedge clk);
            while (!s_axi_arready) @(posedge clk);
            s_axi_arvalid = 0;

            s_axi_rready = 1;
            @(posedge clk);
            while (!s_axi_rvalid) @(posedge clk);
            $display("[READ ] Addr = 0x%08X, Data = 0x%08X", addr, s_axi_rdata);
            s_axi_rready = 0;
        end
    endtask

    // Initial block
    initial begin
        // Initialize
        clk = 0;
        rst_n = 0;
        s_axi_awvalid = 0;
        s_axi_wvalid = 0;
        s_axi_bready = 0;
        s_axi_arvalid = 0;
        s_axi_rready = 0;

        #20 rst_n = 1;

        // Wait after reset
        #10;
        @(posedge clk);
        // Write value to 0x00
        axi_write(8'h00, 32'hDEADBEEF);

        // Read value from 0x00
        axi_read(8'h00);

        // Check status_reg_o
        #5;
        $display("[STATUS] status_reg_o = 0x%08X", status_reg_o);

        #20 $finish;
    end

endmodule
