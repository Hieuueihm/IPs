module median_filter_3x3  (
    input clk,
    input rst_n,
    input [7:0] d0_i,
    input [7:0] d1_i,
    input [7:0] d2_i,
    input d0_valid_i,
    input d1_valid_i,
    input d2_valid_i,
    input [8:0] IMG_SIZE_I,
    output [7:0] median_o,
    output data_valid_o
);
  wire [7:0] data0, data1, data2, data3, data4, data5, data6, data7, data8;
  wire z_o_valid;
    z3x3  inst_z3x3 (
      .clk          (clk),
      .rst_n        (rst_n),
      .d0_i         (d0_i),
      .d1_i         (d1_i),
      .d2_i         (d2_i),
      .d0_valid_i   (d0_valid_i),
      .d1_valid_i   (d1_valid_i),
      .d2_valid_i   (d2_valid_i),
      .IMG_SIZE_I   (IMG_SIZE_I),
      .d0_o         (data0),
      .d1_o         (data1),
      .d2_o         (data2),
      .d3_o         (data3),
      .d4_o         (data4),
      .d5_o         (data5),
      .d6_o         (data6),
      .d7_o         (data7),
      .d8_o         (data8),
      .data_valid_o (z_o_valid)
    );


  median_3x3_calc median_3X3_CALC (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(z_o_valid),
      .S1(data0),
      .S2(data1),
      .S3(data2),
      .S4(data3),
      .S5(data4),
      .S6(data5),
      .S7(data6),
      .S8(data7),
      .S9(data8),
      .median_o(median_o),
      .data_valid_o(data_valid_o)
  );



endmodule