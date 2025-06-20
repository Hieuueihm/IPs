`timescale 1ns/1ps

module tb_top;

  reg clk = 0;
  always #5 clk = ~clk;  // 100MHz clock

  reg rst_n;

  // AXI-Lite signals
    // AXI-Lite signals
  reg [31:0]  s_axi_awaddr;
  reg        s_axi_awvalid;
  wire       s_axi_awready;
  reg [31:0] s_axi_wdata;
  reg [3:0]  s_axi_wstrb;
  reg        s_axi_wvalid;
  wire       s_axi_wready;
  wire [1:0] s_axi_bresp;
  wire       s_axi_bvalid;
  reg        s_axi_bready;
  reg [31:0]  s_axi_araddr;
  reg        s_axi_arvalid;
  wire       s_axi_arready;
  wire [31:0] s_axi_rdata;
  wire [1:0]  s_axi_rresp;
  wire        s_axi_rvalid;
  reg         s_axi_rready;

  // AXI-Stream input
  reg [7:0] s_axis_tdata;
  reg       s_axis_tvalid;
  wire      s_axis_tready;

  // AXI-Stream output
  wire [31:0] m_axis_tdata;
  wire        m_axis_tvalid;
  reg         m_axis_tready = 1;


  wire irq;

  // Instantiate DUT
    top dut (
    .clk(clk),
    .rst_n(rst_n),
    // AXI-Lite
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

    // AXI-Stream input
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),

    // AXI-Stream output
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),

    .irq(irq)
  );


  reg [7:0] matrix [0:20000];  // enough space
  integer i, img_size;



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
    task axi_write(input logic [31:0] addr, input logic [31:0] data);
        begin
            // Write address
            s_axi_awaddr  = addr;
            s_axi_awvalid = 1;
            // Write data
            s_axi_wdata   = data;
            s_axi_wstrb   = 4'hF;
            s_axi_awvalid = 1'b1;
            @(posedge clk);
            @(posedge clk);
            s_axi_awvalid = 0;
            while(!s_axi_wready) @(posedge clk);
            s_axi_wvalid  = 1;
            s_axi_bready = 1;
            @(posedge clk);
            s_axi_wvalid  = 0;

            // Wait for bvalid
            @(posedge clk);
            while (!s_axi_bvalid) @(posedge clk);
            s_axi_bready = 0;
            $display("[WRITE] Addr = 0x%08X, Data = 0x%08X", addr, data);
        end
    endtask
initial begin
    $readmemh("/home/hieu/Workspace/IP/MRELBP/src/matrix_input_hex.txt", matrix);  
  end
  // Output file handles
  integer fout_3x3, fout_5x5, fout_7x7;
  integer fout_ci_r2, fout_ci_r4, fout_ci_r6;
  integer fout_r2_ni, fout_r2_rd;
  integer fout_r4_ni, fout_r4_rd;
  integer fout_r6_ni, fout_r6_rd;
  integer fout_jh;
  initial begin
      fout_3x3 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_3x3.txt", "w");
      fout_5x5 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_5x5.txt", "w");
      fout_7x7 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_7x7.txt", "w");
      fout_ci_r2 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r2.txt", "w");
      fout_ci_r4 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r4.txt", "w");
      fout_ci_r6 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r6.txt", "w");
      fout_r2_ni = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/ni_r2.txt", "w");
      fout_r2_rd = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/rd_r2.txt", "w");
      fout_r4_ni = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/ni_r4.txt", "w");
      fout_r4_rd = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/rd_r4.txt", "w");
      fout_r6_ni = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/ni_r6.txt", "w");
      fout_r6_rd = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_nird/rd_r6.txt", "w");
      fout_jh = $fopen("/home/hieu/Workspace/IP/MRELBP/src/histogram_verilog.txt", "w");

    end

  // Monitor and log median results
  always @(posedge clk) begin
    if (dut.inst_mrelbp.m_3x3_valid)
      $fwrite(fout_3x3, "%0d\n", dut.inst_mrelbp.m_3x3);
    if (dut.inst_mrelbp.m_5x5_valid)
      $fwrite(fout_5x5, "%0d\n", dut.inst_mrelbp.m_5x5);
    if (dut.inst_mrelbp.m_7x7_valid)
      $fwrite(fout_7x7, "%0d\n", dut.inst_mrelbp.m_7x7);
    if(dut.inst_mrelbp.ci_r2_valid)     $fwrite(fout_ci_r2, "%0d\n", dut.inst_mrelbp.ci_r2);
    if(dut.inst_mrelbp.ci_r4_valid)     $fwrite(fout_ci_r4, "%0d\n", dut.inst_mrelbp.ci_r4);
    if(dut.inst_mrelbp.ci_r6_valid)     $fwrite(fout_ci_r6, "%0d\n", dut.inst_mrelbp.ci_r6);
    if(dut.inst_mrelbp.r2_data_valid)     $fwrite(fout_r2_ni, "%0d\n", dut.inst_mrelbp.r2_ni);
    if(dut.inst_mrelbp.r2_data_valid)     $fwrite(fout_r2_rd, "%0d\n", dut.inst_mrelbp.r2_rd);
    if(dut.inst_mrelbp.r4_data_valid)     $fwrite(fout_r4_ni, "%0d\n", dut.inst_mrelbp.r4_ni);
    if(dut.inst_mrelbp.r4_data_valid)     $fwrite(fout_r4_rd, "%0d\n", dut.inst_mrelbp.r4_rd);
    if(dut.inst_mrelbp.r6_data_valid)     $fwrite(fout_r6_ni, "%0d\n", dut.inst_mrelbp.r6_ni);
    if(dut.inst_mrelbp.r6_data_valid)     $fwrite(fout_r6_rd, "%0d\n", dut.inst_mrelbp.r6_rd);
    if(m_axis_tvalid) $fwrite(fout_jh, "%0d\n", m_axis_tdata);
  end

  initial begin
    $dumpfile("wave.vcd");
    $dumpvars(0, tb_top);

    img_size = 128;

    // Reset
    rst_n = 0;
    s_axi_awaddr = 0; s_axi_awvalid = 0;
    s_axi_wdata  = 0; s_axi_wstrb = 0; s_axi_wvalid = 0;
    s_axi_bready = 0;
    s_axi_araddr = 0; s_axi_arvalid = 0; s_axi_rready = 0;

    s_axis_tdata = 0;
    s_axis_tvalid = 0;

    #20 rst_n = 1;
    #20;

    // Write control register (e.g., config=3'b010)
    axi_write(4'h4, 32'h00000000);  // config d20
    #20;
    axi_write(4'h0, 32'h00000001);  // start bit = 1 (bit 0), config=2

    // Feed image matrix
    for (i = 0; i < img_size * img_size; i = i) begin
      @(posedge clk);
      if (s_axis_tready) begin
        s_axis_tdata  <= matrix[i];
        s_axis_tvalid <= 1;
        i = i + 1;
      end
    end

    @(posedge clk);
    s_axis_tvalid <= 0;

    wait(irq);
    #10000;
     $fclose(fout_3x3);
    $fclose(fout_5x5);
    $fclose(fout_7x7);
    $fclose(fout_ci_r2);
    $fclose(fout_ci_r4);
    $fclose(fout_ci_r6);
    $fclose(fout_r2_ni);
    $fclose(fout_r2_rd);
    $fclose(fout_r4_ni);
    $fclose(fout_r4_rd);
    $fclose(fout_r6_ni);
    $fclose(fout_r6_rd);
    $fclose(fout_jh);



    $finish;
  end

endmodule


