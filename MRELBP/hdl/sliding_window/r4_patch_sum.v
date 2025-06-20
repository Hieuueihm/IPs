module r4_patch_sum (
    input clk,
    input rst_n,
    input data_valid_i,
    input start_i,
    input [7:0] S1,
    input [7:0] S2,
    input [7:0] S3,
    input [7:0] S4,
    input [7:0] S5,
    S6,
    S7,
    S8,
    S9,
    input [8:0] IMG_SIZE_I,
    output [14:0] sum_o,
    output data_valid_o,
    output finish_o
);

  wire cum_en, sum_en, count_en;
  wire [9:0] i_counter;
  wire i_start_gt_2;
  wire ld_en;
  wire start_en;
  wire [7:0] central_value;
  wire i_row_eq_max;
  wire reset_en;
    r4_controller inst_r4_controller (
            .clk          (clk),
            .rst_n        (rst_n),
            .start_i      (start_i),
            .i_start_gt_2 (i_start_gt_2),
            .i_counter    (i_counter),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .i_row_eq_max (i_row_eq_max),
            .cum_en       (cum_en),
            .data_valid_o (data_valid_o),
            .sum_en       (sum_en),
            .count_en     (count_en),
            .start_en     (start_en),
            .ld_en        (ld_en),
            .finish_o     (finish_o),
            .reset_en     (reset_en)
        );


    r4_sum #(
            .USE_CENTRAL_VALUE(0)
        ) inst_r4_sum (
            .clk           (clk),
            .rst_n         (rst_n),
            .cum_en        (cum_en),
            .sum_en        (sum_en),
            .count_en      (count_en),
            .start_en      (start_en),
            .ld_en         (ld_en),
            .S1            (S1),
            .S2            (S2),
            .S3            (S3),
            .S4            (S4),
            .S5            (S5),
            .S6            (S6),
            .S7            (S7),
            .S8            (S8),
            .S9            (S9),
            .data_valid_i  (data_valid_i),
            .IMG_SIZE_I    (IMG_SIZE_I),
            .sum_o         (sum_o),
            .i_counter     (i_counter),
            .central_value (central_value),
            .i_row_eq_max  (i_row_eq_max),
            .i_start_gt_2  (i_start_gt_2),
            .reset_en      (reset_en)
        );




endmodule