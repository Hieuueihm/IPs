module ci_r2  (
    input clk,
    input rst_n,
    input data_valid_i,
    input start_i,
    input [7:0] S1,
    input [7:0] S2,
    input [7:0] S3,
    input [7:0] S4,
    input [7:0] S5,
    input [8:0] IMG_SIZE_I,
    output ci_o,
    output ci_valid_o,
    output reg finish_o
);
 reg [8:0] IMG_SIZE;
    always @(posedge clk) begin
        if(~rst_n) begin
            IMG_SIZE <= 0;
        end else begin
            IMG_SIZE <= IMG_SIZE_I;
        end
    end

  wire cum_en, sum_en, count_en;
  wire [9:0] i_counter;
  wire i_start_gt_1;
  wire ld_en;
  wire start_en;
  wire sum_valid;
  wire [12:0] sum_o;
  wire [7:0] central_value;
  wire i_row_eq_max;
  wire reset_en;
  wire r2_finish;
  r2_controller inst_r2_controller(
      .clk(clk),
      .rst_n(rst_n),
      .start_i(start_i),
      .i_counter(i_counter),
      .i_start_gt_1(i_start_gt_1),
      .ld_en(ld_en),
      .IMG_SIZE_I  (IMG_SIZE),
      .cum_en(cum_en),
      .data_valid_o(sum_valid),
      .sum_en(sum_en),
      .count_en(count_en),
      .i_row_eq_max(i_row_eq_max),
      .start_en(start_en),
      .finish_o(r2_finish),
      .reset_en(reset_en)

  );

  r2_sum inst_r2_sum (
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
      .data_valid_i (data_valid_i),
      .IMG_SIZE_I   (IMG_SIZE),
      .sum_o(sum_o),
      .i_counter(i_counter),
      .i_row_eq_max(i_row_eq_max),
      .i_start_gt_1(i_start_gt_1),
      .central_value(central_value),
      .start_en(start_en),
      .reset_en(reset_en)


  );


  reg [25:0] scale_value;
  reg scale_valid;
  always @(posedge clk) begin
    if (~rst_n) begin
      scale_valid <= 0;
      scale_value <= 0;
      finish_o <= 0;
    end else begin
      scale_valid <= sum_valid;
      scale_value <= ~(central_value * 25 < sum_o);
      finish_o <= r2_finish;
    end
  end

  assign ci_o   = scale_value;
  assign ci_valid_o = scale_valid;





endmodule