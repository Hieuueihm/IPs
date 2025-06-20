// tb_median_filter_all.v
`timescale 1ns/1ps

module tb_median_filter;

  reg clk = 0;
  always #5 clk = ~clk; // 100MHz

  reg rst_n;
  reg [7:0] s_axis_tdata;
  reg s_axis_tvalid;
  wire s_axis_tready = 1;
  reg [8:0] IMG_SIZE_I;

  wire [7:0] m_3x3_o, m_5x5_o, m_7x7_o;
  wire m_3x3_valid_o, m_5x5_valid_o, m_7x7_valid_o;

  // DUT
  median_filter dut (
    .clk(clk),
    .rst_n(rst_n),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .IMG_SIZE_I(IMG_SIZE_I),
    .data_root_o(), // optional
    .data_root_valid_o(), // optional
    .m_3x3_o(m_3x3_o),
    .m_3x3_valid_o(m_3x3_valid_o),
    .m_5x5_o(m_5x5_o),
    .m_5x5_valid_o(m_5x5_valid_o),
    .m_7x7_o(m_7x7_o),
    .m_7x7_valid_o(m_7x7_valid_o)
  );

  // Matrix 9x9
  reg [7:0] matrix [0:20000];
  integer i;
  initial begin
    $readmemh("/home/hieu/Workspace/IP/MRELBP/src/matrix_input_hex.txt", matrix);  
  end
  initial begin
    $dumpfile("waveform.vcd");
    $dumpvars(0, tb_median_filter);

    // Reset
    rst_n = 0; s_axis_tvalid = 0; s_axis_tdata = 0;
    IMG_SIZE_I = 9;
    #100 rst_n = 1;

    // Init matrix
    for (i = 0; i < IMG_SIZE_I * IMG_SIZE_I; i = i + 1) begin
      @(posedge clk);
      s_axis_tvalid <= 1;
      s_axis_tdata <= matrix[i];
    end

 
    @(posedge clk);
    s_axis_tvalid <= 0;

    #100000;
    $finish;
  end

    // File handles for separate median outputs
    integer fout_3x3, fout_5x5, fout_7x7;

    // Mở 3 file output riêng biệt
    initial begin
      fout_3x3 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_3x3.txt", "w");
      fout_5x5 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_5x5.txt", "w");
      fout_7x7 = $fopen("/home/hieu/Workspace/IP/MRELBP/src/check_median/median_7x7.txt", "w");
    end

    // Ghi kết quả vào 3 file riêng biệt
    always @(posedge clk) begin
      if (m_3x3_valid_o)
        $fwrite(fout_3x3, "%0d\n", m_3x3_o);
      if (m_5x5_valid_o)
        $fwrite(fout_5x5, "%0d\n", m_5x5_o);
      if (m_7x7_valid_o)
        $fwrite(fout_7x7, "%0d\n", m_7x7_o);
    end

    // Đóng file khi kết thúc mô phỏng (optional but good practice)
    final begin
      $fclose(fout_3x3);
      $fclose(fout_5x5);
      $fclose(fout_7x7);
    end


endmodule
