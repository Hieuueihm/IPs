`timescale 1ns/1ps

module tb_buffer_7;

  reg clk;
  reg rst_n;

  reg [7:0] s_axis_tdata;
  reg s_axis_tvalid;
  reg s_axis_tready;

  reg [8:0] image_size_i;

  wire [7:0] data0_o, data1_o, data2_o, data3_o, data4_o, data5_o, data6_o;
  wire data0_valid_o, data1_valid_o, data2_valid_o, data3_valid_o, data4_valid_o;
  wire data_5_valid_o, data_6_valid_o;

  // Instantiate the DUT
  buffer_7 uut (
    .clk(clk),
    .rst_n(rst_n),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .IMG_SIZE_I(image_size_i),
    .data0_o(data0_o),
    .data0_valid_o(data0_valid_o),
    .data1_o(data1_o),
    .data1_valid_o(data1_valid_o),
    .data2_o(data2_o),
    .data2_valid_o(data2_valid_o),
    .data3_o(data3_o),
    .data3_valid_o(data3_valid_o),
    .data4_o(data4_o),
    .data4_valid_o(data4_valid_o),
    .data5_o(data5_o),
    .data5_valid_o(data_5_valid_o),
    .data6_o(data6_o),
    .data6_valid_o(data_6_valid_o)
  );

  // Clock generation
  always #5 clk = ~clk;

  initial begin
    $display("[TB] Starting testbench for buffer_7");

    clk = 0;
    rst_n = 0;
    s_axis_tvalid = 0;
    s_axis_tdata = 0;
    image_size_i = 9'd5 ;// 128x128 assumed
    s_axis_tready = 1'b1;

    #20 rst_n = 1;

    // Send some data into the chain
    repeat (300) begin
      @(posedge clk);
      s_axis_tvalid <= 1;
      s_axis_tdata <= $random % 256;
    end

    // Stop valid signal
    @(posedge clk);
    s_axis_tvalid <= 0;

    // Wait for a while to let pipeline flush
    repeat (100) @(posedge clk);
    $display("[TB] Done simulation");
    $finish;
  end

  // Optional: Monitor outputs
  always @(posedge clk) begin
    if (data0_valid_o || data1_valid_o || data2_valid_o || data3_valid_o ||
        data4_valid_o || data_5_valid_o || data_6_valid_o) begin
      $display("%0t: D0=%02x D1=%02x D2=%02x D3=%02x D4=%02x D5=%02x D6=%02x", $time,
               data0_o, data1_o, data2_o, data3_o, data4_o, data5_o, data6_o);
    end
  end

endmodule