module ci_r4 (
    input clk,
    input rst_n,
    input data_valid_i,
    input start_i,
    input [7:0] S1,
    input [7:0] S2,
    input [7:0] S3,
    input [7:0] S4,
    input [7:0] S5,
    input [7:0] S6,
    S7,
    S8,
    S9,
    input [8:0] IMG_SIZE_I,
    output ci_o,
    output ci_valid_o,
    output reg finish_o
);

  wire cum_en, sum_en, count_en;
  wire [9:0] i_counter;
  wire i_start_gt_2;
  wire ld_en;
  wire start_en;
  wire [14:0] sum_o;
  wire [7:0] central_value;
  wire i_row_eq_max;
  wire reset_en;

  wire pd;
  r4_controller inst_r4_controller (
      .clk(clk),
      .rst_n(rst_n),
      .start_i(start_i),
      .IMG_SIZE_I  (IMG_SIZE_I),
      .i_counter(i_counter),
      .i_start_gt_2(i_start_gt_2),
      .ld_en(ld_en),
      .cum_en(cum_en),
      .sum_en(sum_en),
      .count_en(count_en),
      .i_row_eq_max(i_row_eq_max),
      .start_en(start_en),
      .data_valid_o(sum_valid),
      .finish_o(pd),
      .reset_en(reset_en)
  );

  r4_sum inst_r4_sum (
      .clk(clk),
      .rst_n(rst_n),
      .cum_en(cum_en),
      .count_en(count_en),
      .sum_en(sum_en),
      .ld_en(ld_en),
      .S1(S1),
      .S2(S2),
      .S3(S3),
      .S4(S4),
      .S5(S5),
      .S6(S6),
      .S7(S7),
      .S8(S8),
      .S9(S9),
      .data_valid_i (data_valid_i),
      .IMG_SIZE_I   (IMG_SIZE_I),
      .sum_o(sum_o),
      .i_counter(i_counter),
      .i_row_eq_max(i_row_eq_max),
      .i_start_gt_2(i_start_gt_2),
      .central_value(central_value),
      .start_en(start_en),
      .reset_en(reset_en)


  );

  reg [29:0] scale_value;
  reg done_scale;
  always @(posedge clk) begin
    if (~rst_n) begin
      done_scale <= 0;
      scale_value <= 0;
      finish_o <= 0;
    end else begin
      done_scale <= sum_valid;
      scale_value <= ~(central_value * 81 < sum_o);
      finish_o <= pd;
    end
  end

  assign ci_o   = scale_value;
  assign ci_valid_o = done_scale;

endmodule