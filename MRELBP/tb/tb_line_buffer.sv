`timescale 1ns/1ps

module tb_line_buffer();

  // Parameters
  localparam CLK_PERIOD = 10;

  // DUT signals
  logic clk;
  logic rst_n;
  logic [7:0] s_axis_tdata;
  logic s_axis_tvalid;
  logic s_axis_tready;
  logic [8:0] image_size_i;
  logic [7:0] data_o;
  logic [7:0] data_valid_o;

  // Instantiate DUT
  line_buffer dut (
    .clk(clk),
    .rst_n(rst_n),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .IMG_SIZE_I(image_size_i),
    .data_o(data_o),
    .data_valid_o(data_valid_o)
  );

  // Clock generator
  initial clk = 0;
  always #(CLK_PERIOD/2) clk = ~clk;

  // Stimulus task
  task send_pixel(input [7:0] val);
    begin
      @(posedge clk);
      s_axis_tdata  <= val;
      s_axis_tvalid <= 1;
      s_axis_tready <= 1; // simulate always ready
    end
  endtask

  // Reset task
  task reset_dut();
    begin
      rst_n <= 0;
      s_axis_tdata <= 0;
      s_axis_tvalid <= 0;
      s_axis_tready <= 0;
      image_size_i <= 9'd5; // Default to 128x128
      #(5*CLK_PERIOD);
      rst_n <= 1;
    end
  endtask

  // Monitor outputs
  always @(posedge clk) begin
    if (dut.rd_en)
      $display("[%t] READ_EN=1, DATA_OUT=0x%0h, VALID=%0b", $time, data_o, data_valid_o);
  end

  // Test sequence
  initial begin
    reset_dut();

    // Set image size to 128x128
    @(posedge clk);
    image_size_i <= 9'd5;

    // Feed 200 pixels (simulate part of 128x128 image)
    for(int i = 1; i <= 25; i++) begin
          send_pixel(i);
    end 
    @(posedge clk);
    s_axis_tvalid = 0;


   

    // Wait for read to start
    repeat (30000) @(posedge clk);

    $finish;
  end

endmodule
