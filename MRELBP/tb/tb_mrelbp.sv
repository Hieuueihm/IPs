`timescale 1ns/1ps

module tb_mrelbp;

  reg clk = 0;
  always #5 clk = ~clk;  // 100MHz clock

  reg rst_n;
  reg [1:0] status_reg_i;
  reg [1:0] config_reg_i;
  reg [7:0] s_axis_tdata;
  reg s_axis_tvalid;
  wire s_axis_tready;

  // DUT
  mrelbp dut (
    .clk(clk),
    .rst_n(rst_n),
    .status_reg_i(status_reg_i),
    .config_reg_i(config_reg_i),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready)
  );

  // Matrix inpu
  reg [7:0] matrix [0:20000];  // large enough
  integer i, img_size;
 initial begin
    $readmemh("/home/hieu/Workspace/IP/MRELBP/src/matrix_input_hex.txt", matrix);  
  end
  // Output file handles
  integer fout_3x3, fout_5x5, fout_7x7;
  integer fout_ci_r2, fout_ci_r4, fout_ci_r6;
  initial begin
      fout_3x3 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_3x3.txt", "w");
      fout_5x5 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_5x5.txt", "w");
      fout_7x7 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_7x7.txt", "w");
      fout_ci_r2 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r2.txt", "w");
      fout_ci_r4 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r4.txt", "w");
      fout_ci_r6 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_ci/ci_r6.txt", "w");

    end

  // Monitor and log median results
  always @(posedge clk) begin
    if (dut.m_3x3_valid)
      $fwrite(fout_3x3, "%0d\n", dut.m_3x3);
    if (dut.m_5x5_valid)
      $fwrite(fout_5x5, "%0d\n", dut.m_5x5);
    if (dut.m_7x7_valid)
      $fwrite(fout_7x7, "%0d\n", dut.m_7x7);
    if(dut.ci_r2_valid_o)     $fwrite(fout_ci_r2, "%0d\n", dut.ci_r2_o);
    if(dut.ci_r4_valid_o)     $fwrite(fout_ci_r4, "%0d\n", dut.ci_r4_o);
    if(dut.ci_r6_valid_o)     $fwrite(fout_ci_r6, "%0d\n", dut.ci_r6_o);

  end

  // Simulation control
  initial begin
    $dumpfile("wave.vcd");
    $dumpvars(0, tb_mrelbp);

    // Default signals
    rst_n = 0;
    s_axis_tdata = 0;
    s_axis_tvalid = 0;
    status_reg_i = 2'b00;
    config_reg_i = 2'b00;  // 9x9

    img_size = 20;
    #20 rst_n = 1;

    // Wait a bit
    #20;

    // Start signal
    status_reg_i = 2'b01;  // start bit = 1
    #10;
    status_reg_i = 2'b00;  // falling edge triggers start_pulse

    // Feed input data
    for (i = 0; i < img_size * img_size; i = i) begin
      @(posedge clk);
      if (s_axis_tready) begin
        s_axis_tdata <= matrix[i];
        s_axis_tvalid <= 1;
        i = i + 1;
      end
    end

    @(posedge clk);
    s_axis_tvalid <= 0;

    // Wait for outputs to finish
    #100000;
    $fclose(fout_3x3);
    $fclose(fout_5x5);
    $fclose(fout_7x7);
    $fclose(fout_ci_r2);
    $fclose(fout_ci_r4);
    $fclose(fout_ci_r6);

    $finish;
  end

endmodule
