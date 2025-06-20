module window_buffer_3x3_datapath (
    input clk,
    input rst_n,
    input count_en,
    input [7:0] S1_i,
    S2_i,
    S3_i,
    input data_valid_i,
    input [8:0] IMG_SIZE_I,
    output i_row_eq_max,
    output [7:0] S1_o,
    S2_o,
    S3_o,
    S4_o,
    S5_o,
    S6_o,
    S7_o,
    S8_o,
    S9_o,
    output i_col_eq_max,
    output i_col_ge_threshold,
    input reset_en
);


  reg [9:0] i_counter;
  always @(posedge clk) begin
    if (~rst_n) begin
      i_counter <= 0;
    end else if (reset_en) begin
      i_counter <= 0;
    end else if (i_col_eq_max) begin
      i_counter <= 0;
    end else if (count_en) begin
      i_counter <= i_counter + 1;
    end
  end
  assign i_col_eq_max = (i_counter == IMG_SIZE_I - 2);


  reg [9:0] i_row;
  always @(posedge clk) begin
    if (~rst_n) begin
      i_row <= 0;
    end else if (reset_en) begin
      i_row <= 0;
    end else if (i_col_eq_max) begin
      i_row <= i_row + 1;
    end
  end
  assign i_col_ge_threshold = (i_counter > 0);
  assign i_row_eq_max       = (i_row == IMG_SIZE_I - 3);


  reg [7:0] S1_delay;
  reg [7:0] S2_delay;
  reg [7:0] S3_delay;

  always @(posedge clk) begin
    if (~rst_n) begin
      S1_delay <= 0;
      S2_delay <= 0;
      S3_delay <= 0;
    end else if(data_valid_i) begin
      S1_delay <= S1_i;
      S2_delay <= S2_i;
      S3_delay <= S3_i;
    end
  end

  reg [7:0] S1_window[2:0];
  reg [7:0] S2_window[2:0];
  reg [7:0] S3_window[2:0];
  integer i;
  always @(posedge clk) begin
    if (~rst_n) begin
      for (i = 0; i < 3; i = i + 1) begin
        S1_window[i] <= 0;
        S2_window[i] <= 0;
        S3_window[i] <= 0;
      end
    end else begin
      S1_window[0] <= S1_delay;
      S2_window[0] <= S2_delay;
      S3_window[0] <= S3_delay;

      for (i = 1; i < 3; i = i + 1) begin
        S1_window[i] <= S1_window[i-1];
        S2_window[i] <= S2_window[i-1];
        S3_window[i] <= S3_window[i-1];
      end
    end
  end

  assign S1_o = S1_window[2];
  assign S2_o = S1_window[1];
  assign S3_o = S1_window[0];

  assign S4_o = S2_window[2];
  assign S5_o = S2_window[1];
  assign S6_o = S2_window[0];

  assign S7_o = S3_window[2];
  assign S8_o = S3_window[1];
  assign S9_o = S3_window[0];
endmodule
