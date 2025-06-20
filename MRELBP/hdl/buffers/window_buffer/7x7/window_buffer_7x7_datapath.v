module window_buffer_7x7_datapath  (
    input clk,
    input rst_n,
    input count_en,
    input [7:0] S1_i,
    S2_i,
    S3_i,
    S4_i,
    S5_i,
    S6_i,
    S7_i,
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
    S10_o,
    S11_o,
    S12_o,
    S13_o,
    S14_o,
    S15_o,
    S16_o,
    S17_o,
    S18_o,
    S19_o,
    S20_o,
    S21_o,
    S22_o,
    S23_o,
    S24_o,
    S25_o,
    S26_o,
    S27_o,
    S28_o,
    S29_o,
    S30_o,
    S31_o,
    S32_o,
    S33_o,
    S34_o,
    S35_o,
    S36_o,
    S37_o,
    S38_o,
    S39_o,
    S40_o,
    S41_o,
    S42_o,
    S43_o,
    S44_o,
    S45_o,
    S46_o,
    S47_o,
    S48_o,
    S49_o,
    output i_col_eq_max,
    output i_col_ge_threshold,
    input reset_en
);

  reg [9:0] i_counter;
  reg [9:0] i_row;

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
  assign i_col_ge_threshold = (i_counter > 4);


  always @(posedge clk) begin
    if (~rst_n) begin
      i_row <= 0;
    end else if (reset_en) begin
      i_row <= 0;
    end else if (i_col_eq_max) begin
      i_row <= i_row + 1;
    end
  end
  assign i_row_eq_max = (i_row == IMG_SIZE_I - 6);

  reg [7:0] S1_delay;
  reg [7:0] S2_delay;
  reg [7:0] S3_delay;
  reg [7:0] S4_delay;
  reg [7:0] S5_delay;
  reg [7:0] S6_delay;
  reg [7:0] S7_delay;

  always @(posedge clk) begin
    if (~rst_n) begin
      S1_delay <= 0;
      S2_delay <= 0;
      S3_delay <= 0;
      S4_delay <= 0;
      S5_delay <= 0;
      S6_delay <= 0;
      S7_delay <= 0;
    end else if(data_valid_i) begin
      S1_delay <= S1_i;
      S2_delay <= S2_i;
      S3_delay <= S3_i;
      S4_delay <= S4_i;
      S5_delay <= S5_i;
      S6_delay <= S6_i;
      S7_delay <= S7_i;
    end
  end

  reg [7:0] S1_window[6:0];
  reg [7:0] S2_window[6:0];
  reg [7:0] S3_window[6:0];
  reg [7:0] S4_window[6:0];
  reg [7:0] S5_window[6:0];
  reg [7:0] S6_window[6:0];
  reg [7:0] S7_window[6:0];
  integer i;
  always @(posedge clk) begin
    if (~rst_n) begin
      for (i = 0; i < 7; i = i + 1) begin
        S1_window[i] <= 0;
        S2_window[i] <= 0;
        S3_window[i] <= 0;
        S4_window[i] <= 0;
        S5_window[i] <= 0;
        S6_window[i] <= 0;
        S7_window[i] <= 0;
      end
    end else begin
      S1_window[0] <= S1_delay;
      S2_window[0] <= S2_delay;
      S3_window[0] <= S3_delay;
      S4_window[0] <= S4_delay;
      S5_window[0] <= S5_delay;
      S6_window[0] <= S6_delay;
      S7_window[0] <= S7_delay;

      for (i = 1; i < 7; i = i + 1) begin
        S1_window[i] <= S1_window[i-1];
        S2_window[i] <= S2_window[i-1];
        S3_window[i] <= S3_window[i-1];
        S4_window[i] <= S4_window[i-1];
        S5_window[i] <= S5_window[i-1];
        S6_window[i] <= S6_window[i-1];
        S7_window[i] <= S7_window[i-1];
      end
    end
  end

  assign S1_o  = S1_window[6];
  assign S2_o  = S1_window[5];
  assign S3_o  = S1_window[4];
  assign S4_o  = S1_window[3];
  assign S5_o  = S1_window[2];
  assign S6_o  = S1_window[1];
  assign S7_o  = S1_window[0];

  assign S8_o  = S2_window[6];
  assign S9_o  = S2_window[5];
  assign S10_o = S2_window[4];
  assign S11_o = S2_window[3];
  assign S12_o = S2_window[2];
  assign S13_o = S2_window[1];
  assign S14_o = S2_window[0];

  assign S15_o = S3_window[6];
  assign S16_o = S3_window[5];
  assign S17_o = S3_window[4];
  assign S18_o = S3_window[3];
  assign S19_o = S3_window[2];
  assign S20_o = S3_window[1];
  assign S21_o = S3_window[0];

  assign S22_o = S4_window[6];
  assign S23_o = S4_window[5];
  assign S24_o = S4_window[4];
  assign S25_o = S4_window[3];
  assign S26_o = S4_window[2];
  assign S27_o = S4_window[1];
  assign S28_o = S4_window[0];


  assign S29_o = S5_window[6];
  assign S30_o = S5_window[5];
  assign S31_o = S5_window[4];
  assign S32_o = S5_window[3];
  assign S33_o = S5_window[2];
  assign S34_o = S5_window[1];
  assign S35_o = S5_window[0];


  assign S36_o = S6_window[6];
  assign S37_o = S6_window[5];
  assign S38_o = S6_window[4];
  assign S39_o = S6_window[3];
  assign S40_o = S6_window[2];
  assign S41_o = S6_window[1];
  assign S42_o = S6_window[0];


  assign S43_o = S7_window[6];
  assign S44_o = S7_window[5];
  assign S45_o = S7_window[4];
  assign S46_o = S7_window[3];
  assign S47_o = S7_window[2];
  assign S48_o = S7_window[1];
  assign S49_o = S7_window[0];


endmodule
