module median_filter(
    input clk,
    input rst_n,
    input wire [7:0] s_axis_tdata,
    input wire s_axis_tvalid,
    input wire s_axis_tready,
    input [8:0] IMG_SIZE_I,
    output [7:0] data_root_o,
    output data_root_valid_o,
    output [7:0] m_3x3_o,
    output m_3x3_valid_o,
    output [7:0] m_5x5_o,
    output m_5x5_valid_o,
    output [7:0] m_7x7_o,
    output m_7x7_valid_o
);


  wire [7:0] b_data0, b_data1, b_data2, b_data3, b_data4, b_data5, b_data6;
  wire b_data0_valid, b_data1_valid, b_data2_valid, b_data3_valid, b_data4_valid, b_data5_valid, b_data6_valid;

    buffer_7 inst_buffer_7
        (
            .clk           (clk),
            .rst_n         (rst_n),
            .s_axis_tdata  (s_axis_tdata),
            .s_axis_tvalid (s_axis_tvalid),
            .s_axis_tready (s_axis_tready),
            .IMG_SIZE_I    (IMG_SIZE_I),
            .data0_o       (b_data0),
            .data0_valid_o (b_data0_valid),
            .data1_o       (b_data1),
            .data1_valid_o (b_data1_valid),
            .data2_o       (b_data2),
            .data2_valid_o (b_data2_valid),
            .data3_o       (b_data3),
            .data3_valid_o (b_data3_valid),
            .data4_o       (b_data4),
            .data4_valid_o (b_data4_valid),
            .data5_o       (b_data5),
            .data5_valid_o (b_data5_valid),
            .data6_o       (b_data6),
            .data6_valid_o (b_data6_valid)
        );

  assign data_root_o = b_data3;
  assign data_root_valid_o = b_data3_valid;
 



    median_filter_3x3 inst_median_filter_3x3
        (
            .clk          (clk),
            .rst_n        (rst_n),
            .d0_i         (b_data2),
            .d1_i         (b_data3),
            .d2_i         (b_data4),
            .d0_valid_i   (b_data2_valid),
            .d1_valid_i   (b_data3_valid),
            .d2_valid_i   (b_data4_valid),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .median_o     (m_3x3_o),
            .data_valid_o (m_3x3_valid_o)
        );
    median_filter_5x5  inst_median_filter_5x5 (
            .clk          (clk),
            .rst_n        (rst_n),
            .d0_i         (b_data1),
            .d1_i         (b_data2),
            .d2_i         (b_data3),
            .d3_i         (b_data4),
            .d4_i         (b_data5),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .d0_valid_i   (b_data1_valid),
            .d1_valid_i   (b_data2_valid),
            .d2_valid_i   (b_data3_valid),
            .d3_valid_i   (b_data4_valid),
            .d4_valid_i   (b_data5_valid),
            .median_o     (m_5x5_o),
            .data_valid_o (m_5x5_valid_o)
        );

    median_filter_7x7  inst_median_filter_7x7 (
            .clk          (clk),
            .rst_n        (rst_n),
            .d0_i         (b_data0),
            .d1_i         (b_data1),
            .d2_i         (b_data2),
            .d3_i         (b_data3),
            .d4_i         (b_data4),
            .d5_i         (b_data5),
            .d6_i         (b_data6),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .d0_valid_i   (b_data0_valid),
            .d1_valid_i   (b_data1_valid),
            .d2_valid_i   (b_data2_valid),
            .d3_valid_i   (b_data3_valid),
            .d4_valid_i   (b_data4_valid),
            .d5_valid_i   (b_data5_valid),
            .d6_valid_i   (b_data6_valid),
            .median_o     (m_7x7_o),
            .data_valid_o (m_7x7_valid_o)
        );


    



endmodule