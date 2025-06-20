module r2_sum #(parameter USE_CENTRAL_VALUE = 1) (
    input clk,
    input rst_n,
    input cum_en,
    input sum_en,
    input count_en,
    input start_en,
    input ld_en,
    input [7:0] S1,
    S2,
    S3,
    S4,
    S5,
    input data_valid_i,
    input [8:0] IMG_SIZE_I,
    output [12:0] sum_o,
    output i_row_eq_max,
    output reg [9:0] i_counter,
    output [7:0] central_value,
    output i_start_gt_1,
    input reset_en
);

   

  reg [1:0] i_start;

  always @(posedge clk) begin
    if (~rst_n) begin
      i_start <= 0;
    end else if (reset_en) begin
      i_start <= 0;
    end else if (start_en) begin
      i_start <= i_start + 1;
    end
  end

  // );
  assign i_start_gt_1 = (i_start > 1);


  wire i_counter_eq_max;
  assign i_counter_eq_max = (i_counter == IMG_SIZE_I - 1);

  always @(posedge clk) begin
    if (~rst_n) begin
      i_counter <= 0;
    end else if (reset_en) begin
      i_counter <= 0;
    end else if (i_counter_eq_max) begin
      i_counter <= 0;
    end else if (count_en) begin
      i_counter <= i_counter + 1;
    end
  end

  reg [9:0] i_row;
  always @(posedge clk) begin
    if (~rst_n) begin
      i_row <= 0;
    end else if (reset_en) begin
      i_row <= 0;
    end else if (i_counter_eq_max) begin
      i_row <= i_row + 1;
    end
  end



  assign i_row_eq_max = (i_row == IMG_SIZE_I - 4);


  reg [7:0] st1_S1, st1_S2, st1_S3, st1_S4, st1_S5;
  always @(posedge clk) begin
    if (~rst_n) begin
      st1_S1 <= 0;
      st1_S2 <= 0;
      st1_S3 <= 0;
      st1_S4 <= 0;
      st1_S5 <= 0;
    end else if(data_valid_i) begin
      st1_S1 <= S1;
      st1_S2 <= S2;
      st1_S3 <= S3;
      st1_S4 <= S4;
      st1_S5 <= S5;
    end
  end

  wire [8:0] sum12, sum34;
  reg [7:0] st2_S5;
  always @(posedge clk) begin
    if (~rst_n) begin
      st2_S5 <= 0;
    end else begin
      st2_S5 <= st1_S5;

    end
  end

  sum #(
      .WIDTH(8)
  ) SUM12 (
      .clk(clk),
      .rst_n(rst_n),
      .en(data_valid_i),
      .a(st1_S1),
      .b(st1_S2),
      .result(sum12)
  );

  sum #(
      .WIDTH(8)
  ) SUM34 (
      .clk(clk),
      .rst_n(rst_n),
      .en(data_valid_i),
      .a(st1_S3),
      .b(st1_S4),
      .result(sum34)
  );

  wire [9:0] sum1234;

  sum #(
      .WIDTH(9)
  ) SUM1234 (
      .clk(clk),
      .rst_n(rst_n),
      .en(data_valid_i),
      .a(sum12),
      .b(sum34),
      .result(sum1234)
  );
  reg [7:0] st3_S5;
  always @(posedge clk) begin
    if (~rst_n) begin
      st3_S5 <= 0;
    end else begin
      st3_S5 <= st2_S5;

    end
  end

  wire [10:0] sum1;
  sum #(
      .WIDTH(10)
  ) SUM12345 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum1234),
      .en(data_valid_i),
      .b({2'b00, st3_S5}),
      .result(sum1)
  );

  reg [10:0] sum2, st1_sum2, st2_sum2, st3_sum2, st4_sum2;

  always @(posedge clk) begin
    if (~rst_n) begin
      sum2     <= 0;
      st1_sum2 <= 0;
      st2_sum2 <= 0;
      st3_sum2 <= 0;
      st4_sum2 <= 0;
    end else begin
      st1_sum2 <= sum1;
      st2_sum2 <= st1_sum2;
      st3_sum2 <= st2_sum2;
      st4_sum2 <= st3_sum2;
      sum2     <= st4_sum2;
    end
  end






  wire [12:0] sum2_extended;
  assign sum2_extended = {2'b00, sum2};
  wire [12:0] mux_1;
  assign mux_1 = (cum_en == 0) ? 13'b0 : ((~sum2_extended) + 1);
  sum_cumulative #(
      .WIDTH1(13),
      .WIDTH2(13)
  ) SUMO (
      .clk(clk),
      .rst_n(rst_n),
      .en(sum_en),
      .ld(ld_en),
      .data_in1({2'b00, sum1}),
      .data_in2(mux_1),
      .sum_out(sum_o)
  );

  generate
    if (USE_CENTRAL_VALUE) begin
      reg [7:0] central_1, central_2, central_3, central_4, central_5, central_6;
      always @(posedge clk) begin
        if (~rst_n) begin
          central_1 <= 0;
          central_2 <= 0;
          central_3 <= 0;
          central_4 <= 0;
          central_5 <= 0;
          central_6 <= 0;
        end else begin
          central_1 <= st1_S3;
          central_2 <= central_1;
          central_3 <= central_2;
          central_4 <= central_3;
          central_5 <= central_4;
          central_6 <= central_5;
        end
      end
      assign central_value = central_6;
    end else begin
      assign central_value = 8'b0;
    end
  endgenerate



endmodule