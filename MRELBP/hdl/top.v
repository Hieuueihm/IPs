module top (
    input  wire         clk,
    input  wire         rst_n,

    // AXI-Lite interface
    input  wire [31:0]   s_axi_awaddr,
    input  wire         s_axi_awvalid,
    output wire         s_axi_awready,

    input  wire [31:0]  s_axi_wdata,
    input  wire [3:0]   s_axi_wstrb,
    input  wire         s_axi_wvalid,
    output wire         s_axi_wready,

    output wire [1:0]   s_axi_bresp,
    output wire         s_axi_bvalid,
    input  wire         s_axi_bready,

    input  wire [31:0]   s_axi_araddr,
    input  wire         s_axi_arvalid,
    output wire         s_axi_arready,

    output wire [31:0]  s_axi_rdata,
    output wire [1:0]   s_axi_rresp,
    output wire         s_axi_rvalid,
    input  wire         s_axi_rready,

    // AXI-Stream input
    input  wire [7:0]   s_axis_tdata,
    input  wire         s_axis_tvalid,
    output wire         s_axis_tready,

    // AXI-Stream output
    output wire [31:0]  m_axis_tdata,
    output wire         m_axis_tvalid,
    input  wire         m_axis_tready,


    output irq
);

    wire [31:0] control_reg;
    wire [31:0] config_reg;
    axi4_lite inst_axi4_lite
        (
            .clk           (clk),
            .rst_n         (rst_n),
            .s_axi_awaddr  (s_axi_awaddr),
            .s_axi_awvalid (s_axi_awvalid),
            .s_axi_awready (s_axi_awready),
            .s_axi_wdata   (s_axi_wdata),
            .s_axi_wstrb   (s_axi_wstrb),
            .s_axi_wvalid  (s_axi_wvalid),
            .s_axi_wready  (s_axi_wready),
            .s_axi_bresp   (s_axi_bresp),
            .s_axi_bvalid  (s_axi_bvalid),
            .s_axi_bready  (s_axi_bready),
            .s_axi_araddr  (s_axi_araddr),
            .s_axi_arvalid (s_axi_arvalid),
            .s_axi_arready (s_axi_arready),
            .s_axi_rdata   (s_axi_rdata),
            .s_axi_rresp   (s_axi_rresp),
            .s_axi_rvalid  (s_axi_rvalid),
            .s_axi_rready  (s_axi_rready),
            .control_reg_o (control_reg),
            .config_reg_o  (config_reg)
        );


        mrelbp inst_mrelbp
        (
            .clk           (clk),
            .rst_n         (rst_n),
            .control_reg_i (control_reg[1:0]),
            .config_reg_i  (config_reg[0]),
            .s_axis_tdata  (s_axis_tdata),
            .s_axis_tvalid (s_axis_tvalid),
            .s_axis_tready (s_axis_tready),
            .m_axis_tdata (m_axis_tdata),
            .m_axis_tvalid(m_axis_tvalid),
            .m_axis_tready(m_axis_tready),
            .irq_o        (irq)

        );




    

endmodule