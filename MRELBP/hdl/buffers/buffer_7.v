module buffer_7  (
    input clk,
    input rst_n,

    input wire [7:0] s_axis_tdata,
    input wire s_axis_tvalid,
    input wire s_axis_tready,

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
    output data6_valid_o
);


  wire [7:0] line_buffer_data[5:0];
  wire line_buffer_data_valid[5:0];

  assign data0_o = s_axis_tdata;
  assign data1_o = line_buffer_data[0];
  assign data2_o = line_buffer_data[1];
  assign data3_o = line_buffer_data[2];
  assign data4_o = line_buffer_data[3];
  assign data5_o = line_buffer_data[4];
  assign data6_o = line_buffer_data[5];

  assign data0_valid_o = s_axis_tvalid;
  assign data1_valid_o =  line_buffer_data_valid[0];
  assign data2_valid_o = line_buffer_data_valid[1];
  assign data3_valid_o = line_buffer_data_valid[2];
  assign data4_valid_o = line_buffer_data_valid[3];
  assign data5_valid_o = line_buffer_data_valid[4];
  assign data6_valid_o = line_buffer_data_valid[5];

  generate
    for (genvar i = 0; i < 6; i = i + 1) begin : gen_line_buffers
      line_buffer
      inst_line_buffer_7 (
      .clk           (clk),
      .rst_n         (rst_n),
      .s_axis_tdata  ((i == 0) ? s_axis_tdata : line_buffer_data[i - 1]),
      .s_axis_tvalid ((i == 0) ? s_axis_tvalid : line_buffer_data_valid[ i - 1]),
      .s_axis_tready (s_axis_tready),
      .IMG_SIZE_I  (IMG_SIZE_I),
      .data_o        (line_buffer_data[i]),
      .data_valid_o  (line_buffer_data_valid[i])
    );

    end
  endgenerate




endmodule