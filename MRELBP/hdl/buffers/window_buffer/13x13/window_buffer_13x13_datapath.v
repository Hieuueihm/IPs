module window_buffer_13x13_datapath  (
    input clk,
    input rst_n,
    input count_en,
    input data_valid_i,
    input [7:0] S1_i,
    S2_i,
    S3_i,
    S4_i,
    S5_i,
    S6_i,
    S7_i,
    S8_i,
    S9_i,
    S10_i,
    S11_i,
    S12_i,
    S13_i,
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
    S50_o,
    S51_o,
    S52_o,
    S53_o,
    S54_o,
    S55_o,
    S56_o,
    S57_o,
    S58_o,
    S59_o,
    S60_o,
    S61_o,
    S62_o,
    S63_o,
    S64_o,
    S65_o,
    S66_o,
    S67_o,
    S68_o,
    S69_o,
    S70_o,
    S71_o,
    S72_o,
    S73_o,
    S74_o,
    S75_o,
    S76_o,
    S77_o,
    S78_o,
    S79_o,
    S80_o,
    S81_o,
    S82_o,
    S83_o,
    S84_o,
    S85_o,
    S86_o,
    S87_o,
    S88_o,
    S89_o,
    S90_o,
    S91_o,
    S92_o,
    S93_o,
    S94_o,
    S95_o,
    S96_o,
    S97_o,
    S98_o,
    S99_o,
    S100_o,
    S101_o,
    S102_o,
    S103_o,
    S104_o,
    S105_o,
    S106_o,
    S107_o,
    S108_o,
    S109_o,
    S110_o,
    S111_o,
    S112_o,
    S113_o,
    S114_o,
    S115_o,
    S116_o,
    S117_o,
    S118_o,
    S119_o,
    S120_o,
    S121_o,
    S122_o,
    S123_o,
    S124_o,
    S125_o,
    S126_o,
    S127_o,
    S128_o,
    S129_o,
    S130_o,
    S131_o,
    S132_o,
    S133_o,
    S134_o,
    S135_o,
    S136_o,
    S137_o,
    S138_o,
    S139_o,
    S140_o,
    S141_o,
    S142_o,
    S143_o,
    S144_o,
    S145_o,
    S146_o,
    S147_o,
    S148_o,
    S149_o,
    S150_o,
    S151_o,
    S152_o,
    S153_o,
    S154_o,
    S155_o,
    S156_o,
    S157_o,
    S158_o,
    S159_o,
    S160_o,
    S161_o,
    S162_o,
    S163_o,
    S164_o,
    S165_o,
    S166_o,
    S167_o,
    S168_o,
    S169_o,
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
  assign i_col_ge_threshold = (i_counter > 10);


  always @(posedge clk) begin
    if (~rst_n) begin
      i_row <= 0;
    end else if (reset_en) begin
      i_row <= 0;
    end else if (i_col_eq_max) begin
      i_row <= i_row + 1;
    end
  end
  assign i_row_eq_max = (i_row == IMG_SIZE_I - 12);




  reg [7:0] S1_delay;
  reg [7:0] S2_delay;
  reg [7:0] S3_delay;
  reg [7:0] S4_delay;
  reg [7:0] S5_delay;
  reg [7:0] S6_delay;
  reg [7:0] S7_delay;
  reg [7:0] S8_delay;
  reg [7:0] S9_delay;
  reg [7:0] S10_delay;
  reg [7:0] S11_delay;
  reg [7:0] S12_delay;
  reg [7:0] S13_delay;

  always @(posedge clk) begin
    if (~rst_n) begin
      S1_delay  <= 0;
      S2_delay  <= 0;
      S3_delay  <= 0;
      S4_delay  <= 0;
      S5_delay  <= 0;
      S6_delay  <= 0;
      S7_delay  <= 0;
      S8_delay  <= 0;
      S9_delay  <= 0;
      S10_delay <= 0;
      S11_delay <= 0;
      S12_delay <= 0;
      S13_delay <= 0;
    end else if(data_valid_i) begin
      S1_delay  <= S1_i;
      S2_delay  <= S2_i;
      S3_delay  <= S3_i;
      S4_delay  <= S4_i;
      S5_delay  <= S5_i;
      S6_delay  <= S6_i;
      S7_delay  <= S7_i;
      S8_delay  <= S8_i;
      S9_delay  <= S9_i;
      S10_delay <= S10_i;
      S11_delay <= S11_i;
      S12_delay <= S12_i;
      S13_delay <= S13_i;
    end
  end

  reg [7:0] S1_window[12:0];
  reg [7:0] S2_window[12:0];
  reg [7:0] S3_window[12:0];
  reg [7:0] S4_window[12:0];
  reg [7:0] S5_window[12:0];
  reg [7:0] S6_window[12:0];
  reg [7:0] S7_window[12:0];
  reg [7:0] S8_window[12:0];
  reg [7:0] S9_window[12:0];
  reg [7:0] S10_window[12:0];
  reg [7:0] S11_window[12:0];
  reg [7:0] S12_window[12:0];
  reg [7:0] S13_window[12:0];
  integer i;
  always @(posedge clk) begin
    if (~rst_n) begin
      for (i = 0; i < 13; i = i + 1) begin
        S1_window[i]  <= 0;
        S2_window[i]  <= 0;
        S3_window[i]  <= 0;
        S4_window[i]  <= 0;
        S5_window[i]  <= 0;
        S6_window[i]  <= 0;
        S7_window[i]  <= 0;
        S8_window[i]  <= 0;
        S9_window[i]  <= 0;
        S10_window[i] <= 0;
        S11_window[i] <= 0;
        S12_window[i] <= 0;
        S13_window[i] <= 0;
      end
    end else begin
      S1_window[0]  <= S1_delay;
      S2_window[0]  <= S2_delay;
      S3_window[0]  <= S3_delay;
      S4_window[0]  <= S4_delay;
      S5_window[0]  <= S5_delay;
      S6_window[0]  <= S6_delay;
      S7_window[0]  <= S7_delay;
      S8_window[0]  <= S8_delay;
      S9_window[0]  <= S9_delay;
      S10_window[0] <= S10_delay;
      S11_window[0] <= S11_delay;
      S12_window[0] <= S12_delay;
      S13_window[0] <= S13_delay;

      for (i = 1; i < 13; i = i + 1) begin
        S1_window[i]  <= S1_window[i-1];
        S2_window[i]  <= S2_window[i-1];
        S3_window[i]  <= S3_window[i-1];
        S4_window[i]  <= S4_window[i-1];
        S5_window[i]  <= S5_window[i-1];
        S6_window[i]  <= S6_window[i-1];
        S7_window[i]  <= S7_window[i-1];
        S8_window[i]  <= S8_window[i-1];
        S9_window[i]  <= S9_window[i-1];
        S10_window[i] <= S10_window[i-1];
        S11_window[i] <= S11_window[i-1];
        S12_window[i] <= S12_window[i-1];
        S13_window[i] <= S13_window[i-1];

      end
    end
  end

  assign S1_o   = S1_window[12];
  assign S2_o   = S1_window[11];
  assign S3_o   = S1_window[10];
  assign S4_o   = S1_window[9];
  assign S5_o   = S1_window[8];
  assign S6_o   = S1_window[7];
  assign S7_o   = S1_window[6];
  assign S8_o   = S1_window[5];
  assign S9_o   = S1_window[4];
  assign S10_o  = S1_window[3];
  assign S11_o  = S1_window[2];
  assign S12_o  = S1_window[1];
  assign S13_o  = S1_window[0];

  assign S14_o  = S2_window[12];
  assign S15_o  = S2_window[11];
  assign S16_o  = S2_window[10];
  assign S17_o  = S2_window[9];
  assign S18_o  = S2_window[8];
  assign S19_o  = S2_window[7];
  assign S20_o  = S2_window[6];
  assign S21_o  = S2_window[5];
  assign S22_o  = S2_window[4];
  assign S23_o  = S2_window[3];
  assign S24_o  = S2_window[2];
  assign S25_o  = S2_window[1];
  assign S26_o  = S2_window[0];

  assign S27_o  = S3_window[12];
  assign S28_o  = S3_window[11];
  assign S29_o  = S3_window[10];
  assign S30_o  = S3_window[9];
  assign S31_o  = S3_window[8];
  assign S32_o  = S3_window[7];
  assign S33_o  = S3_window[6];
  assign S34_o  = S3_window[5];
  assign S35_o  = S3_window[4];
  assign S36_o  = S3_window[3];
  assign S37_o  = S3_window[2];
  assign S38_o  = S3_window[1];
  assign S39_o  = S3_window[0];

  assign S40_o  = S4_window[12];
  assign S41_o  = S4_window[11];
  assign S42_o  = S4_window[10];
  assign S43_o  = S4_window[9];
  assign S44_o  = S4_window[8];
  assign S45_o  = S4_window[7];
  assign S46_o  = S4_window[6];
  assign S47_o  = S4_window[5];
  assign S48_o  = S4_window[4];
  assign S49_o  = S4_window[3];
  assign S50_o  = S4_window[2];
  assign S51_o  = S4_window[1];
  assign S52_o  = S4_window[0];

  assign S53_o  = S5_window[12];
  assign S54_o  = S5_window[11];
  assign S55_o  = S5_window[10];
  assign S56_o  = S5_window[9];
  assign S57_o  = S5_window[8];
  assign S58_o  = S5_window[7];
  assign S59_o  = S5_window[6];
  assign S60_o  = S5_window[5];
  assign S61_o  = S5_window[4];
  assign S62_o  = S5_window[3];
  assign S63_o  = S5_window[2];
  assign S64_o  = S5_window[1];
  assign S65_o  = S5_window[0];


  assign S66_o  = S6_window[12];
  assign S67_o  = S6_window[11];
  assign S68_o  = S6_window[10];
  assign S69_o  = S6_window[9];
  assign S70_o  = S6_window[8];
  assign S71_o  = S6_window[7];
  assign S72_o  = S6_window[6];
  assign S73_o  = S6_window[5];
  assign S74_o  = S6_window[4];
  assign S75_o  = S6_window[3];
  assign S76_o  = S6_window[2];
  assign S77_o  = S6_window[1];
  assign S78_o  = S6_window[0];


  assign S79_o  = S7_window[12];
  assign S80_o  = S7_window[11];
  assign S81_o  = S7_window[10];
  assign S82_o  = S7_window[9];
  assign S83_o  = S7_window[8];
  assign S84_o  = S7_window[7];
  assign S85_o  = S7_window[6];
  assign S86_o  = S7_window[5];
  assign S87_o  = S7_window[4];
  assign S88_o  = S7_window[3];
  assign S89_o  = S7_window[2];
  assign S90_o  = S7_window[1];
  assign S91_o  = S7_window[0];

  assign S92_o  = S8_window[12];
  assign S93_o  = S8_window[11];
  assign S94_o  = S8_window[10];
  assign S95_o  = S8_window[9];
  assign S96_o  = S8_window[8];
  assign S97_o  = S8_window[7];
  assign S98_o  = S8_window[6];
  assign S99_o  = S8_window[5];
  assign S100_o = S8_window[4];
  assign S101_o = S8_window[3];
  assign S102_o = S8_window[2];
  assign S103_o = S8_window[1];
  assign S104_o = S8_window[0];

  assign S105_o = S9_window[12];
  assign S106_o = S9_window[11];
  assign S107_o = S9_window[10];
  assign S108_o = S9_window[9];
  assign S109_o = S9_window[8];
  assign S110_o = S9_window[7];
  assign S111_o = S9_window[6];
  assign S112_o = S9_window[5];
  assign S113_o = S9_window[4];
  assign S114_o = S9_window[3];
  assign S115_o = S9_window[2];
  assign S116_o = S9_window[1];
  assign S117_o = S9_window[0];


  assign S118_o = S10_window[12];
  assign S119_o = S10_window[11];
  assign S120_o = S10_window[10];
  assign S121_o = S10_window[9];
  assign S122_o = S10_window[8];
  assign S123_o = S10_window[7];
  assign S124_o = S10_window[6];
  assign S125_o = S10_window[5];
  assign S126_o = S10_window[4];
  assign S127_o = S10_window[3];
  assign S128_o = S10_window[2];
  assign S129_o = S10_window[1];
  assign S130_o = S10_window[0];

  assign S131_o = S11_window[12];
  assign S132_o = S11_window[11];
  assign S133_o = S11_window[10];
  assign S134_o = S11_window[9];
  assign S135_o = S11_window[8];
  assign S136_o = S11_window[7];
  assign S137_o = S11_window[6];
  assign S138_o = S11_window[5];
  assign S139_o = S11_window[4];
  assign S140_o = S11_window[3];
  assign S141_o = S11_window[2];
  assign S142_o = S11_window[1];
  assign S143_o = S11_window[0];


  assign S144_o = S12_window[12];
  assign S145_o = S12_window[11];
  assign S146_o = S12_window[10];
  assign S147_o = S12_window[9];
  assign S148_o = S12_window[8];
  assign S149_o = S12_window[7];
  assign S150_o = S12_window[6];
  assign S151_o = S12_window[5];
  assign S152_o = S12_window[4];
  assign S153_o = S12_window[3];
  assign S154_o = S12_window[2];
  assign S155_o = S12_window[1];
  assign S156_o = S12_window[0];


  assign S157_o = S13_window[12];
  assign S158_o = S13_window[11];
  assign S159_o = S13_window[10];
  assign S160_o = S13_window[9];
  assign S161_o = S13_window[8];
  assign S162_o = S13_window[7];
  assign S163_o = S13_window[6];
  assign S164_o = S13_window[5];
  assign S165_o = S13_window[4];
  assign S166_o = S13_window[3];
  assign S167_o = S13_window[2];
  assign S168_o = S13_window[1];
  assign S169_o = S13_window[0];
endmodule
