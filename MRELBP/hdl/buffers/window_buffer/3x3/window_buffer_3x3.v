module window_buffer_3x3 (
    input clk,
    input rst_n,
    input data_valid_i,
    input start_i,
    input [7:0] S1_i,
    S2_i,
    S3_i,
    input [8:0] IMG_SIZE_I,
    output [7:0] S1_o,
    S2_o,
    S3_o,
    S4_o,
    S5_o,
    S6_o,
    S7_o,
    S8_o,
    S9_o,
    output data_valid_o,
    output finish_o
);
  wire i_row_eq_max, i_col_eq_max, i_col_ge_threshold;
  wire count_en;
  wire reset_en;
  window_buffer_controller inst_window_buffer_controller_3x3 (
      .clk                (clk),
      .rst_n              (rst_n),
      .start_i           (start_i),      
      .i_row_eq_max       (i_row_eq_max),
      .i_col_eq_max       (i_col_eq_max),
      .i_col_ge_threshold (i_col_ge_threshold),
      .count_en           (count_en),
      .finish_o           (finish_o),
      .data_valid_o       (data_valid_o),
      .reset_en           (reset_en)
    );


  window_buffer_3x3_datapath inst_window_buffer_3x3_datapath
    (
      .clk                (clk),
      .rst_n              (rst_n),
      .count_en           (count_en),
      .S1_i               (S1_i),
      .S2_i               (S2_i),
      .S3_i               (S3_i),
      .data_valid_i      (data_valid_i),
      .IMG_SIZE_I         (IMG_SIZE_I),
      .i_row_eq_max       (i_row_eq_max),
      .S1_o               (S1_o),
      .S2_o               (S2_o),
      .S3_o               (S3_o),
      .S4_o               (S4_o),
      .S5_o               (S5_o),
      .S6_o               (S6_o),
      .S7_o               (S7_o),
      .S8_o               (S8_o),
      .S9_o               (S9_o),
      .i_col_eq_max       (i_col_eq_max),
      .i_col_ge_threshold (i_col_ge_threshold),
      .reset_en           (reset_en)
    );


endmodule
