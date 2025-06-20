module buffer_9  (
    input clk,
    input rst_n,

    input wire [7:0] data_i,
    input wire data_valid_i,
    input [8:0] IMG_SIZE_I,


    output [7:0] data0_o,
    output data0_valid_o,
    output [7:0] data1_o,
    output data1_valid_o,
    output [7:0] data2_o,
    output data2_valid_o,
    output [7:0] data3_o,
    output data3_valid_o,
    output [7:0] data4_o,
    output data4_valid_o,
    output [7:0] data5_o,
    output data5_valid_o,
    output [7:0] data6_o,
    output data6_valid_o,
    output [7:0] data7_o,
    output data7_valid_o,
    output [7:0] data8_o,
    output data8_valid_o,
    output tfirst_o


);


  wire [7:0] line_buffer_data[7:0];
  wire line_buffer_data_valid[7:0];
  wire tfirst [7:0];

  assign data0_o = data_i;
  assign data1_o = line_buffer_data[0];
  assign data2_o = line_buffer_data[1];
  assign data3_o = line_buffer_data[2];
  assign data4_o = line_buffer_data[3];
  assign data5_o = line_buffer_data[4];
  assign data6_o = line_buffer_data[5];
  assign data7_o = line_buffer_data[6];
  assign data8_o = line_buffer_data[7];
  assign tfirst_o = tfirst[7];

  assign data0_valid_o = data_valid_i;
  assign data1_valid_o =  line_buffer_data_valid[0];
  assign data2_valid_o = line_buffer_data_valid[1];
  assign data3_valid_o = line_buffer_data_valid[2];
  assign data4_valid_o = line_buffer_data_valid[3];
  assign data5_valid_o = line_buffer_data_valid[4];
  assign data6_valid_o = line_buffer_data_valid[5];
  assign data7_valid_o = line_buffer_data_valid[6];
  assign data8_valid_o = line_buffer_data_valid[7];

  generate
    for (genvar i = 0; i < 8; i = i + 1) begin : gen_line_buffers
      line_buffer
      inst_line_buffer_9 (
      .clk           (clk),
      .rst_n         (rst_n),
      .s_axis_tdata  ((i == 0) ? data_i : line_buffer_data[i - 1]),
      .s_axis_tvalid ((i == 0) ? data_valid_i : line_buffer_data_valid[ i - 1]),
      .s_axis_tready (1'b1),
      .IMG_SIZE_I  (IMG_SIZE_I),
      .data_o        (line_buffer_data[i]),
      .data_valid_o  (line_buffer_data_valid[i]),
      .tfirst_o    (tfirst[i])
    );

    end
  endgenerate




endmodule