module r6_sum #(parameter USE_CENTRAL_VALUE = 1) (
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
    S6,
    S7,
    S8,
    S9,
    S10,
    S11,
    S12,
    S13,
    input [8:0] IMG_SIZE_I,
    input data_valid_i,
    output [15:0] sum_o,
    output reg [9:0] i_counter,
    output [7:0] central_value,
    output i_row_eq_max,
    output i_start_gt_2,
    input reset_en
);




  reg [2:0] i_start;

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


  assign i_start_gt_2 = (i_start > 2);
  assign i_row_eq_max = (i_row == IMG_SIZE_I - 12);




  reg [7:0]
      st1_S1,
      st1_S2,
      st1_S3,
      st1_S4,
      st1_S5,
      st1_S6,
      st1_S7,
      st1_S8,
      st1_S9,
      st1_S10,
      st1_S11,
      st1_S12,
      st1_S13;
  always @(posedge clk) begin
    if (~rst_n) begin
      st1_S1  <= 0;
      st1_S2  <= 0;
      st1_S3  <= 0;
      st1_S4  <= 0;
      st1_S5  <= 0;
      st1_S6  <= 0;
      st1_S7  <= 0;
      st1_S8  <= 0;
      st1_S9  <= 0;
      st1_S10 <= 0;
      st1_S11 <= 0;
      st1_S12 <= 0;
      st1_S13 <= 0;
    end else begin
      st1_S1  <= S1;
      st1_S2  <= S2;
      st1_S3  <= S3;
      st1_S4  <= S4;
      st1_S5  <= S5;
      st1_S6  <= S6;
      st1_S7  <= S7;
      st1_S8  <= S8;
      st1_S9  <= S9;
      st1_S10 <= S10;
      st1_S11 <= S11;
      st1_S12 <= S12;
      st1_S13 <= S13;
    end
  end

  wire [8:0] sum12, sum34, sum56, sum78, sum910, sum1112;

  sum #(
      .WIDTH(8)
  ) SUM12 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S1),
      .b(st1_S2),
      .en(data_valid_i),
      .result(sum12)
  );

  sum #(
      .WIDTH(8)
  ) SUM34 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S3),
      .b(st1_S4),
      .en(data_valid_i),
      .result(sum34)
  );
  sum #(
      .WIDTH(8)
  ) SUM56 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S5),
      .b(st1_S6),
      .en(data_valid_i),
      .result(sum56)
  );
  sum #(
      .WIDTH(8)
  ) SUM78 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S7),
      .b(st1_S8),
      .en(data_valid_i),
      .result(sum78)
  );

  sum #(
      .WIDTH(8)
  ) SUM910 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S9),
      .b(st1_S10),
      .en(data_valid_i),
      .result(sum910)
  );
  sum #(
      .WIDTH(8)
  ) SUM1112 (
      .clk(clk),
      .rst_n(rst_n),
      .a(st1_S11),
      .b(st1_S12),
      .en(data_valid_i),
      .result(sum1112)
  );

  wire [9:0] sum1234, sum5678, sum9_to_12;

  sum #(
      .WIDTH(9)
  ) SUM1234 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum12),
      .b(sum34),
      .en(data_valid_i),
      .result(sum1234)
  );
  sum #(
      .WIDTH(9)
  ) SUM5678 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum56),
      .b(sum78),
      .en(data_valid_i),
      .result(sum5678)
  );
  sum #(
      .WIDTH(9)
  ) SUM9_TO_12 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum910),
      .b(sum1112),
      .en(data_valid_i),
      .result(sum9_to_12)
  );
  reg [7:0] st2_S13, st3_S13;
  always @(posedge clk) begin
    if (~rst_n) begin
      st2_S13 <= 0;
      st3_S13 <= 0;
    end else begin
      st2_S13 <= st1_S13;
      st3_S13 <= st2_S13;

    end
  end

  wire [10:0] sum1_to_8, sum9_to_13;
  sum #(
      .WIDTH(10)
  ) SUM1_TO_8 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum1234),
      .b(sum5678),
      .en(data_valid_i),
      .result(sum1_to_8)
  );
  sum #(
      .WIDTH(10)
  ) SUM9_TO_13 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum9_to_12),
      .b({2'b00, st3_S13}),
      .en(data_valid_i),
      .result(sum9_to_13)
  );

  wire [11:0] sum1;
  sum #(
      .WIDTH(11)
  ) SUM1 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum1_to_8),
      .b(sum9_to_13),
      .en(data_valid_i),
      .result(sum1)
  );

  reg [11:0] sum2;
  reg [11:0] st_sum2[0:11];
  integer i;

  always @(posedge clk) begin
    if (~rst_n) begin
      sum2 <= 0;
      for (i = 0; i < 12; i = i + 1) begin
        st_sum2[i] <= 0;
      end
    end else begin
      st_sum2[0] <= sum1;
      for (i = 0; i < 11; i = i + 1) begin
        st_sum2[i+1] <= st_sum2[i];
      end
      sum2 <= st_sum2[11];
    end
  end



  wire [15:0] sum2_extended;
  assign sum2_extended = ({4'b0000, sum2});
  wire [15:0] mux_1;
  assign mux_1 = (cum_en == 0) ? 16'b0 : ((~sum2_extended) + 1);

  sum_cumulative #(
      .WIDTH1(16),
      .WIDTH2(16)
  ) SUMO (
      .clk(clk),
      .rst_n(rst_n),
      .en(sum_en),
      .ld(ld_en),
      .data_in1({4'b0000, sum1}),
      .data_in2(mux_1),
      .sum_out(sum_o)
  );

  generate
    if (USE_CENTRAL_VALUE) begin
      reg [7:0] central[0:10];
      always @(posedge clk) begin
        if (~rst_n) begin
          for (i = 0; i < 11; i = i + 1) begin
            central[i] <= 0;
          end

        end else begin
          central[0] <= st1_S7;
          for (i = 0; i < 10; i = i + 1) begin
            central[i+1] <= central[i];
          end
        end
      end
      assign central_value = central[10];
    end else begin
      assign central_value = 8'b0;
    end

  endgenerate



endmodule