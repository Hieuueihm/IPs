module r4_nird  (
    input clk,
    input rst_n,
    input [8:0] IMG_SIZE_I,
    input [7:0] m_3x3_i,
    input m_3x3_valid_i,
    input [7:0] m_5x5_i,
    input m_5x5_valid_i,
    output [3:0] ni_o,
    output [3:0] rd_o,
    output data_valid_o,
    output finish_o
);

  reg [8:0] IMG_SIZE;
  always @(posedge clk) begin
        if(~rst_n) begin
            IMG_SIZE <= 0;
        end else begin
            IMG_SIZE <= IMG_SIZE_I;
        end
    end
  wire [7:0] data0_m3x3, data1_m3x3, data2_m3x3, data3_m3x3, data4_m3x3;
  wire [7:0] data5_m3x3, data6_m3x3, data7_m3x3, data8_m3x3;
  wire data0_m3x3_data_valid, data1_m3x3_data_valid, data2_m3x3_data_valid, data3_m3x3_data_valid;
  wire data4_m3x3_data_valid, data5_m3x3_data_valid, data6_m3x3_data_valid, data7_m3x3_data_valid, 
  data8_m3x3_data_valid;
  wire buffer9_m3x3_data_valid;
  wire buffer9_m3x3_data_start;
    `define CYCLE_DELAY 12
    wire m_3x3_valid_d;
    wire [7:0] m_3x3_d;
      shift_registers #(
        .WIDTH(1),
        .CYCLE(`CYCLE_DELAY)
    ) SHIFT_DATA_VALID_I (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(m_3x3_valid_i),
        .data_o(m_3x3_valid_d)
    );
      shift_registers #(
        .WIDTH(8),
        .CYCLE(`CYCLE_DELAY)
    ) SHIFT_DATA_I (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(m_3x3_i),
        .data_o(m_3x3_d)
    );
  buffer_9 inst_buffer_9_m3x3
    (
      .clk           (clk),
      .rst_n         (rst_n),
      .data_i        (m_3x3_d),
      .data_valid_i  (m_3x3_valid_d),
      .IMG_SIZE_I    (IMG_SIZE),
      .data0_o       (data0_m3x3),
      .data0_valid_o (data0_m3x3_data_valid),
      .data1_o       (data1_m3x3),
      .data1_valid_o (data1_m3x3_data_valid),
      .data2_o       (data2_m3x3),
      .data2_valid_o (data2_m3x3_data_valid),
      .data3_o       (data3_m3x3),
      .data3_valid_o (data3_m3x3_data_valid),
      .data4_o       (data4_m3x3),
      .data4_valid_o (data4_m3x3_data_valid),
      .data5_o       (data5_m3x3),
      .data5_valid_o (data5_m3x3_data_valid),
      .data6_o       (data6_m3x3),
      .data6_valid_o (data6_m3x3_data_valid),
      .data7_o       (data7_m3x3),
      .data7_valid_o (data7_m3x3_data_valid),
      .data8_o       (data8_m3x3),
      .data8_valid_o (data8_m3x3_data_valid),
      .tfirst_o      (buffer9_m3x3_data_start)
    );
    assign buffer9_m3x3_data_valid = data8_m3x3_data_valid;


  wire [7:0] data0_m5x5, data1_m5x5, data2_m5x5, data3_m5x5, data4_m5x5;
  wire [7:0] data5_m5x5, data6_m5x5, data7_m5x5, data8_m5x5;
  wire data0_m5x5_data_valid, data1_m5x5_data_valid, data2_m5x5_data_valid, data3_m5x5_data_valid;
  wire data4_m5x5_data_valid, data5_m5x5_data_valid, data6_m5x5_data_valid, data7_m5x5_data_valid, 
  data8_m5x5_data_valid;
  wire buffer9_m5x5_data_valid;
  wire buffer9_m5x5_data_start;

  buffer_9 inst_buffer_9_m5x5
    (
      .clk           (clk),
      .rst_n         (rst_n),
      .data_i        (m_5x5_i),
      .data_valid_i  (m_5x5_valid_i),
      .IMG_SIZE_I    (IMG_SIZE),
      .data0_o       (data0_m5x5),
      .data0_valid_o (data0_m5x5_data_valid),
      .data1_o       (data1_m5x5),
      .data1_valid_o (data1_m5x5_data_valid),
      .data2_o       (data2_m5x5),
      .data2_valid_o (data2_m5x5_data_valid),
      .data3_o       (data3_m5x5),
      .data3_valid_o (data3_m5x5_data_valid),
      .data4_o       (data4_m5x5),
      .data4_valid_o (data4_m5x5_data_valid),
      .data5_o       (data5_m5x5),
      .data5_valid_o (data5_m5x5_data_valid),
      .data6_o       (data6_m5x5),
      .data6_valid_o (data6_m5x5_data_valid),
      .data7_o       (data7_m5x5),
      .data7_valid_o (data7_m5x5_data_valid),
      .data8_o       (data8_m5x5),
      .data8_valid_o (data8_m5x5_data_valid),
      .tfirst_o      (buffer9_m5x5_data_start)
    );
    assign buffer9_m5x5_data_valid = data8_m5x5_data_valid;

 


  wire [7:0] S1_7x7, S2_7x7, S3_7x7, S4_7x7, S5_7x7, S6_7x7, S7_7x7, S8_7x7;
  wire [7:0] S9_7x7, S10_7x7, S11_7x7, S12_7x7, S13_7x7, S14_7x7, S15_7x7, S16_7x7;
  wire [7:0] S17_7x7, S18_7x7, S19_7x7, S20_7x7, S21_7x7, S22_7x7, S23_7x7, S24_7x7;
  wire [7:0] S25_7x7, S26_7x7, S27_7x7, S28_7x7, S29_7x7, S30_7x7, S31_7x7, S32_7x7;
  wire [7:0] S33_7x7, S34_7x7, S35_7x7, S36_7x7, S37_7x7, S38_7x7, S39_7x7, S40_7x7;
  wire [7:0] S41_7x7, S42_7x7, S43_7x7, S44_7x7, S45_7x7, S46_7x7, S47_7x7, S48_7x7;
  wire [7:0] S49_7x7;

  wire  _data_valid;
  wire wdbf_7x7_finish;

    window_buffer_7x7 inst_window_buffer_7x7
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (buffer9_m3x3_data_valid),
      .start_i      (buffer9_m3x3_data_start),
      .S1_i         (data7_m3x3),
      .S2_i         (data6_m3x3),
      .S3_i         (data5_m3x3),
      .S4_i         (data4_m3x3),
      .S5_i         (data3_m3x3),
      .S6_i         (data2_m3x3),
      .S7_i         (data1_m3x3),
      .IMG_SIZE_I   (IMG_SIZE),
      .S1_o         (S1_7x7),
      .S2_o         (S2_7x7),
      .S3_o         (S3_7x7),
      .S4_o         (S4_7x7),
      .S5_o         (S5_7x7),
      .S6_o         (S6_7x7),
      .S7_o         (S7_7x7),
      .S8_o         (S8_7x7),
      .S9_o         (S9_7x7),
      .S10_o        (S10_7x7),
      .S11_o        (S11_7x7),
      .S12_o        (S12_7x7),
      .S13_o        (S13_7x7),
      .S14_o        (S14_7x7),
      .S15_o        (S15_7x7),
      .S16_o        (S16_7x7),
      .S17_o        (S17_7x7),
      .S18_o        (S18_7x7),
      .S19_o        (S19_7x7),
      .S20_o        (S20_7x7),
      .S21_o        (S21_7x7),
      .S22_o        (S22_7x7),
      .S23_o        (S23_7x7),
      .S24_o        (S24_7x7),
      .S25_o        (S25_7x7),
      .S26_o        (S26_7x7),
      .S27_o        (S27_7x7),
      .S28_o        (S28_7x7),
      .S29_o        (S29_7x7),
      .S30_o        (S30_7x7),
      .S31_o        (S31_7x7),
      .S32_o        (S32_7x7),
      .S33_o        (S33_7x7),
      .S34_o        (S34_7x7),
      .S35_o        (S35_7x7),
      .S36_o        (S36_7x7),
      .S37_o        (S37_7x7),
      .S38_o        (S38_7x7),
      .S39_o        (S39_7x7),
      .S40_o        (S40_7x7),
      .S41_o        (S41_7x7),
      .S42_o        (S42_7x7),
      .S43_o        (S43_7x7),
      .S44_o        (S44_7x7),
      .S45_o        (S45_7x7),
      .S46_o        (S46_7x7),
      .S47_o        (S47_7x7),
      .S48_o        (S48_7x7),
      .S49_o        (S49_7x7),
      .data_valid_o (wdbf_7x7_data_valid),
      .finish_o     (wdbf_7x7_finish)
    );




  wire [7:0] S1_9x9, S2_9x9, S3_9x9, S4_9x9, S5_9x9, S6_9x9, S7_9x9, S8_9x9, S9_9x9;
  wire [7:0] S10_9x9, S11_9x9, S12_9x9, S13_9x9, S14_9x9, S15_9x9, S16_9x9, S17_9x9, S18_9x9;
  wire [7:0] S19_9x9, S20_9x9, S21_9x9, S22_9x9, S23_9x9, S24_9x9, S25_9x9, S26_9x9, S27_9x9;
  wire [7:0] S28_9x9, S29_9x9, S30_9x9, S31_9x9, S32_9x9, S33_9x9, S34_9x9, S35_9x9, S36_9x9;
  wire [7:0] S37_9x9, S38_9x9, S39_9x9, S40_9x9, S41_9x9, S42_9x9, S43_9x9, S44_9x9, S45_9x9;
  wire [7:0] S46_9x9, S47_9x9, S48_9x9, S49_9x9, S50_9x9, S51_9x9, S52_9x9, S53_9x9, S54_9x9;
  wire [7:0] S55_9x9, S56_9x9, S57_9x9, S58_9x9, S59_9x9, S60_9x9, S61_9x9, S62_9x9, S63_9x9;
  wire [7:0] S64_9x9, S65_9x9, S66_9x9, S67_9x9, S68_9x9, S69_9x9, S70_9x9, S71_9x9, S72_9x9;
  wire [7:0] S73_9x9, S74_9x9, S75_9x9, S76_9x9, S77_9x9, S78_9x9, S79_9x9, S80_9x9, S81_9x9;
  wire wdbf_9x9_data_valid;
  wire wdbf_9x9_finish;


    window_buffer_9x9 inst_window_buffer_9x9
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (buffer9_m5x5_data_valid),
      .start_i      (buffer9_m5x5_data_start),
      .S1_i         (data8_m5x5),
      .S2_i         (data7_m5x5),
      .S3_i         (data6_m5x5),
      .S4_i         (data5_m5x5),
      .S5_i         (data4_m5x5),
      .S6_i         (data3_m5x5),
      .S7_i         (data2_m5x5),
      .S8_i         (data1_m5x5),
      .S9_i         (data0_m5x5),
      .IMG_SIZE_I   (IMG_SIZE),
      .S1_o           (S1_9x9),
      .S2_o           (S2_9x9),
      .S3_o           (S3_9x9),
      .S4_o           (S4_9x9),
      .S5_o           (S5_9x9),
      .S6_o           (S6_9x9),
      .S7_o           (S7_9x9),
      .S8_o           (S8_9x9),
      .S9_o           (S9_9x9),
      .S10_o          (S10_9x9),
      .S11_o          (S11_9x9),
      .S12_o          (S12_9x9),
      .S13_o          (S13_9x9),
      .S14_o          (S14_9x9),
      .S15_o          (S15_9x9),
      .S16_o          (S16_9x9),
      .S17_o          (S17_9x9),
      .S18_o          (S18_9x9),
      .S19_o          (S19_9x9),
      .S20_o          (S20_9x9),
      .S21_o          (S21_9x9),
      .S22_o          (S22_9x9),
      .S23_o          (S23_9x9),
      .S24_o          (S24_9x9),
      .S25_o          (S25_9x9),
      .S26_o          (S26_9x9),
      .S27_o          (S27_9x9),
      .S28_o          (S28_9x9),
      .S29_o          (S29_9x9),
      .S30_o          (S30_9x9),
      .S31_o          (S31_9x9),
      .S32_o          (S32_9x9),
      .S33_o          (S33_9x9),
      .S34_o          (S34_9x9),
      .S35_o          (S35_9x9),
      .S36_o          (S36_9x9),
      .S37_o          (S37_9x9),
      .S38_o          (S38_9x9),
      .S39_o          (S39_9x9),
      .S40_o          (S40_9x9),
      .S41_o          (S41_9x9),
      .S42_o          (S42_9x9),
      .S43_o          (S43_9x9),
      .S44_o          (S44_9x9),
      .S45_o          (S45_9x9),
      .S46_o          (S46_9x9),
      .S47_o          (S47_9x9),
      .S48_o          (S48_9x9),
      .S49_o          (S49_9x9),
      .S50_o          (S50_9x9),
      .S51_o          (S51_9x9),
      .S52_o          (S52_9x9),
      .S53_o          (S53_9x9),
      .S54_o          (S54_9x9),
      .S55_o          (S55_9x9),
      .S56_o          (S56_9x9),
      .S57_o          (S57_9x9),
      .S58_o          (S58_9x9),
      .S59_o          (S59_9x9),
      .S60_o          (S60_9x9),
      .S61_o          (S61_9x9),
      .S62_o          (S62_9x9),
      .S63_o          (S63_9x9),
      .S64_o          (S64_9x9),
      .S65_o          (S65_9x9),
      .S66_o          (S66_9x9),
      .S67_o          (S67_9x9),
      .S68_o          (S68_9x9),
      .S69_o          (S69_9x9),
      .S70_o          (S70_9x9),
      .S71_o          (S71_9x9),
      .S72_o          (S72_9x9),
      .S73_o          (S73_9x9),
      .S74_o          (S74_9x9),
      .S75_o          (S75_9x9),
      .S76_o          (S76_9x9),
      .S77_o          (S77_9x9),
      .S78_o          (S78_9x9),
      .S79_o          (S79_9x9),
      .S80_o          (S80_9x9),
      .S81_o          (S81_9x9),
      .data_valid_o (wdbf_9x9_data_valid),
      .finish_o     (wdbf_9x9_finish)
    );


  wire [23:0] S1_r3, S2_r3, S3_r3, S4_r3, S5_r3, S6_r3, S7_r3, S8_r3;
  wire r3_inter_valid;
  wire r3_inter_finish;
  // 1 2 3 4 5 6 7
  // 8 9 10 11 12 13 14
  // 15 16 17 18 19 20 21
  // 22 23 24 25 26 27 28
  // 29 30 31 32 33 34 35
  // 36 37 38 39 40 41 42
  // 43 44 45 46 47 48 49
  interpolation_R_x #(
      .R(3)
  ) INTERPOLATION_R_3 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(wdbf_9x9_finish),
      .data_valid_i(wdbf_9x9_data_valid),
      .S_0_i(S28_7x7),
      .S_90_i(S4_7x7),
      .S_180_i(S22_7x7),
      .S_270_i(S46_7x7),
      .S_45_i_1(S6_7x7),
      .S_45_i_2(S7_7x7),
      .S_45_i_3(S13_7x7),
      .S_45_i_4(S14_7x7),
      .S_135_i_1(S1_7x7),
      .S_135_i_2(S2_7x7),
      .S_135_i_3(S8_7x7),
      .S_135_i_4(S9_7x7),
      .S_225_i_1(S36_7x7),
      .S_225_i_2(S37_7x7),
      .S_225_i_3(S43_7x7),
      .S_225_i_4(S44_7x7),
      .S_315_i_1(S41_7x7),
      .S_315_i_2(S42_7x7),
      .S_315_i_3(S48_7x7),
      .S_315_i_4(S49_7x7),
      .S1_o(S1_r3),
      .S2_o(S2_r3),
      .S3_o(S3_r3),
      .S4_o(S4_r3),
      .S5_o(S5_r3),
      .S6_o(S6_r3),
      .S7_o(S7_r3),
      .S8_o(S8_r3),
      .data_valid_o(r3_inter_valid),
      .finish_o(r3_inter_finish)
  );
  wire [23:0] S1_r4, S2_r4, S3_r4, S4_r4, S5_r4, S6_r4, S7_r4, S8_r4;
  wire r4_inter_valid;
  wire r4_inter_finish;

  // 1 2 3 4 5 6 7 8 9
  // 10 11 12 13 14 15 16 17 18
  // 19 20 21 22 23 24 25 26 27
  // 28 29 30 31 32 33 34 35 36 
  // 37 38 39 40 41 42 43 44 45 
  // 46 47 48 49 50 51 52 53 54
  // 55 56 57 58 59 60 61 62 63
  // 64 65 66 67 68 69 70 71 72
  // 73 74 75 76 77 78 79 80 81
  interpolation_R_x #(
      .R(4)
  ) INTERPOLATION_R_4 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(wdbf_9x9_finish),
      .data_valid_i(wdbf_9x9_data_valid),
      .S_0_i(S45_9x9),
      .S_90_i(S5_9x9),
      .S_180_i(S37_9x9),
      .S_270_i(S77_9x9),
      .S_45_i_1(S16_9x9),
      .S_45_i_2(S17_9x9),
      .S_45_i_3(S25_9x9),
      .S_45_i_4(S26_9x9),
      .S_135_i_1(S11_9x9),
      .S_135_i_2(S12_9x9),
      .S_135_i_3(S20_9x9),
      .S_135_i_4(S21_9x9),
      .S_225_i_1(S56_9x9),
      .S_225_i_2(S57_9x9),
      .S_225_i_3(S65_9x9),
      .S_225_i_4(S66_9x9),
      .S_315_i_1(S61_9x9),
      .S_315_i_2(S62_9x9),
      .S_315_i_3(S70_9x9),
      .S_315_i_4(S71_9x9),
      .S1_o(S1_r4),
      .S2_o(S2_r4),
      .S3_o(S3_r4),
      .S4_o(S4_r4),
      .S5_o(S5_r4),
      .S6_o(S6_r4),
      .S7_o(S7_r4),
      .S8_o(S8_r4),
      .data_valid_o(r4_inter_valid),
      .finish_o(r4_inter_finish)
  );





  wire [14:0] r4_patch_sum;
  wire r4_ps_valid;
  wire r4_ps_finish;

   r4_patch_sum inst_r4_patch_sum
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (buffer9_m5x5_data_valid),
      .start_i      (buffer9_m5x5_data_start),
      .IMG_SIZE_I  (IMG_SIZE),
      .S1           (data0_m5x5),
      .S2           (data1_m5x5),
      .S3           (data2_m5x5),
      .S4           (data3_m5x5),
      .S5           (data4_m5x5),
      .S6           (data5_m5x5),
      .S7           (data6_m5x5),
      .S8           (data7_m5x5),
      .S9           (data8_m5x5),
      .sum_o        (r4_patch_sum),
      .data_valid_o (r4_ps_valid),
      .finish_o     (r4_ps_finish)
    );

  

   wire rd_valid;
   wire rd_finish;
  wire  bit1_rd, bit2_rd, bit3_rd, bit4_rd, bit5_rd, bit6_rd, bit7_rd, bit8_rd;
  rd rd_calc_r4 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r4_inter_valid),
      .finish_i(r4_inter_finish),
      .S1_r2(S1_r4),
      .S2_r2(S2_r4),
      .S3_r2(S3_r4),
      .S4_r2(S4_r4),
      .S5_r2(S5_r4),
      .S6_r2(S6_r4),
      .S7_r2(S7_r4),
      .S8_r2(S8_r4),
      .S1_r1(S1_r3),
      .S2_r1(S2_r3),
      .S3_r1(S3_r3),
      .S4_r1(S4_r3),
      .S5_r1(S5_r3),
      .S6_r1(S6_r3),
      .S7_r1(S7_r3),
      .S8_r1(S8_r3),
      .data_valid_o(rd_valid),
      .finish_o(rd_finish),
      .bit1_o(bit1_rd),
      .bit2_o(bit2_rd),
      .bit3_o(bit3_rd),
      .bit4_o(bit4_rd),
      .bit5_o(bit5_rd),
      .bit6_o(bit6_rd),
      .bit7_o(bit7_rd),
      .bit8_o(bit8_rd)
  );







  wire ni_valid, ni_finish;
  wire bit1_ni, bit2_ni, bit3_ni,
    bit4_ni, bit5_ni, bit6_ni, bit7_ni, bit8_ni;
  ni #(
      .WIDTH(15),
      .GAIN (81)
  ) ni_calc_r4 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r4_inter_valid),
      .finish_i(r4_inter_finish),
      .S1_r2(S1_r4),
      .S2_r2(S2_r4),
      .S3_r2(S3_r4),
      .S4_r2(S4_r4),
      .S5_r2(S5_r4),
      .S6_r2(S6_r4),
      .S7_r2(S7_r4),
      .S8_r2(S8_r4),
      .sum_i(r4_patch_sum),
      .data_valid_o(ni_valid),
      .finish_o(ni_finish),
      .bit1_o(bit1_ni),
      .bit2_o(bit2_ni),
      .bit3_o(bit3_ni),
      .bit4_o(bit4_ni),
      .bit5_o(bit5_ni),
      .bit6_o(bit6_ni),
      .bit7_o(bit7_ni),
      .bit8_o(bit8_ni)
  );

  wire [3:0] rd;
  riu2_mapping riu2_rd (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(rd_valid),
      .finish_i(rd_finish),
      .bit1_i(bit1_rd),
      .bit2_i(bit2_rd),
      .bit3_i(bit3_rd),
      .bit4_i(bit4_rd),
      .bit5_i(bit5_rd),
      .bit6_i(bit6_rd),
      .bit7_i(bit7_rd),
      .bit8_i(bit8_rd),
      .data_o(rd),
      .data_valid_o(),
      .finish_o()
  );

  shift_registers #(
      .WIDTH(4),
      .CYCLE(3)
  ) shift_rd_output (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(rd),
      .data_o(rd_o)
  );
  riu2_mapping riu2_ni (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(ni_valid),
      .finish_i(ni_finish),
      .bit1_i(bit1_ni),
      .bit2_i(bit2_ni),
      .bit3_i(bit3_ni),
      .bit4_i(bit4_ni),
      .bit5_i(bit5_ni),
      .bit6_i(bit6_ni),
      .bit7_i(bit7_ni),
      .bit8_i(bit8_ni),
      .data_o(ni_o),
      .data_valid_o(data_valid_o),
      .finish_o(finish_o)
  );






endmodule