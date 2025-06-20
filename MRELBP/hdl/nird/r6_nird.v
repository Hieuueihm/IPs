module r6_nird  (
    input clk,
    input rst_n,
    input [7:0] m_5x5_i,
    input m_5x5_valid_i,
    input [7:0] m_7x7_i,
    input m_7x7_valid_i,
    input [8:0] IMG_SIZE_I,
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

  wire [7:0] data0_m5x5, data1_m5x5, data2_m5x5, data3_m5x5, data4_m5x5;
  wire [7:0] data5_m5x5, data6_m5x5, data7_m5x5, data8_m5x5;
  wire [7:0] data9_m5x5, data10_m5x5, data11_m5x5, data12_m5x5;
  wire data0_m5x5_data_valid, data1_m5x5_data_valid, data2_m5x5_data_valid, data3_m5x5_data_valid;
  wire data4_m5x5_data_valid, data5_m5x5_data_valid, data6_m5x5_data_valid, data7_m5x5_data_valid;
  wire data8_m5x5_data_valid, data9_m5x5_data_valid, data10_m5x5_data_valid;
  wire data11_m5x5_data_valid, data12_m5x5_data_valid;
  wire buffer13_m5x5_data_valid;
  wire buffer13_m5x5_data_start;
  wire m_5x5_valid_d;
  wire [7:0] m_5x5_d;
      shift_registers #(
        .WIDTH(1),
        .CYCLE(23)
    ) SHIFT_DATA_VALID_I (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(m_5x5_valid_i),
        .data_o(m_5x5_valid_d)
    );
      shift_registers #(
        .WIDTH(8),
        .CYCLE(23)
    ) SHIFT_DATA_I (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(m_5x5_i),
        .data_o(m_5x5_d)
    );

    buffer_13 inst_buffer_13_m5x5
    (
      .clk            (clk),
      .rst_n          (rst_n),
      .data_i         (m_5x5_d),
      .data_valid_i   (m_5x5_valid_d),
      .IMG_SIZE_I     (IMG_SIZE),
      .data0_o        (data0_m5x5),
      .data0_valid_o  (data0_m5x5_data_valid),
      .data1_o        (data1_m5x5),
      .data1_valid_o  (data1_m5x5_data_valid),
      .data2_o        (data2_m5x5),
      .data2_valid_o  (data2_m5x5_data_valid),
      .data3_o        (data3_m5x5),
      .data3_valid_o  (data3_m5x5_data_valid),
      .data4_o        (data4_m5x5),
      .data4_valid_o  (data4_m5x5_data_valid),
      .data5_o        (data5_m5x5),
      .data5_valid_o  (data5_m5x5_data_valid),
      .data6_o        (data6_m5x5),
      .data6_valid_o  (data6_m5x5_data_valid),
      .data7_o        (data7_m5x5),
      .data7_valid_o  (data7_m5x5_data_valid),
      .data8_o        (data8_m5x5),
      .data8_valid_o  (data8_m5x5_data_valid),
      .data9_o        (data9_m5x5),
      .data9_valid_o  (data9_m5x5_data_valid),
      .data10_o       (data10_m5x5),
      .data10_valid_o (data10_m5x5_data_valid),
      .data11_o       (data11_m5x5),
      .data11_valid_o (data11_m5x5_data_valid),
      .data12_o       (data12_m5x5),
      .data12_valid_o (data12_m5x5_data_valid),
      .r2_first_o     (),
      .r4_first_o     (),
      .r6_first_o     (buffer13_m5x5_data_start)
    );
  assign buffer13_m5x5_data_valid = data12_m5x5_data_valid;

  
  wire [7:0] data0_m7x7, data1_m7x7, data2_m7x7, data3_m7x7;
  wire [7:0] data4_m7x7;
  wire [7:0] data5_m7x7, data6_m7x7, data7_m7x7, data8_m7x7;
  wire [7:0] data9_m7x7, data10_m7x7, data11_m7x7, data12_m7x7;

  wire data0_m7x7_data_valid, data1_m7x7_data_valid, data2_m7x7_data_valid, data3_m7x7_data_valid;
  wire data4_m7x7_data_valid, data5_m7x7_data_valid, data6_m7x7_data_valid, data7_m7x7_data_valid;
  wire data8_m7x7_data_valid, data9_m7x7_data_valid, data10_m7x7_data_valid;
  wire data11_m7x7_data_valid, data12_m7x7_data_valid;
  wire buffer13_m7x7_data_valid;
  wire buffer13_m7x7_data_start;
  buffer_13 inst_buffer_13_m7x7
    (
      .clk            (clk),
      .rst_n          (rst_n),
      .data_i         (m_7x7_i),
      .data_valid_i   (m_7x7_valid_i),
      .IMG_SIZE_I     (IMG_SIZE),
      .data0_o        (data0_m7x7),
      .data0_valid_o  (data0_m7x7_data_valid),
      .data1_o        (data1_m7x7),
      .data1_valid_o  (data1_m7x7_data_valid),
      .data2_o        (data2_m7x7),
      .data2_valid_o  (data2_m7x7_data_valid),
      .data3_o        (data3_m7x7),
      .data3_valid_o  (data3_m7x7_data_valid),
      .data4_o        (data4_m7x7),
      .data4_valid_o  (data4_m7x7_data_valid),
      .data5_o        (data5_m7x7),
      .data5_valid_o  (data5_m7x7_data_valid),
      .data6_o        (data6_m7x7),
      .data6_valid_o  (data6_m7x7_data_valid),
      .data7_o        (data7_m7x7),
      .data7_valid_o  (data7_m7x7_data_valid),
      .data8_o        (data8_m7x7),
      .data8_valid_o  (data8_m7x7_data_valid),
      .data9_o        (data9_m7x7),
      .data9_valid_o  (data9_m7x7_data_valid),
      .data10_o       (data10_m7x7),
      .data10_valid_o (data10_m7x7_data_valid),
      .data11_o       (data11_m7x7),
      .data11_valid_o (data11_m7x7_data_valid),
      .data12_o       (data12_m7x7),
      .data12_valid_o (data12_m7x7_data_valid),
      .r2_first_o     (),
      .r4_first_o     (),
      .r6_first_o     (buffer13_m7x7_data_start)
    );
    assign buffer13_m7x7_data_valid = data12_m7x7_data_valid;


  wire [7:0] S1_7x7, S2_7x7, S3_7x7, S4_7x7, S5_7x7, S6_7x7, S7_7x7, S8_7x7;
  wire [7:0] S9_7x7, S10_7x7, S11_7x7, S12_7x7, S13_7x7, S14_7x7, S15_7x7, S16_7x7;
  wire [7:0] S17_7x7, S18_7x7, S19_7x7, S20_7x7, S21_7x7, S22_7x7, S23_7x7, S24_7x7;
  wire [7:0] S25_7x7, S26_7x7, S27_7x7, S28_7x7, S29_7x7, S30_7x7, S31_7x7, S32_7x7;
  wire [7:0] S33_7x7, S34_7x7, S35_7x7, S36_7x7, S37_7x7, S38_7x7, S39_7x7, S40_7x7;
  wire [7:0] S41_7x7, S42_7x7, S43_7x7, S44_7x7, S45_7x7, S46_7x7, S47_7x7, S48_7x7;
  wire [7:0] S49_7x7, S50_7x7, S51_7x7, S52_7x7, S53_7x7, S54_7x7, S55_7x7, S56_7x7;
  wire [7:0] S57_7x7, S58_7x7, S59_7x7, S60_7x7, S61_7x7, S62_7x7, S63_7x7, S64_7x7;
  wire [7:0] S65_7x7, S66_7x7, S67_7x7, S68_7x7, S69_7x7, S70_7x7, S71_7x7, S72_7x7;
  wire [7:0] S73_7x7, S74_7x7, S75_7x7, S76_7x7, S77_7x7, S78_7x7, S79_7x7, S80_7x7;
  wire [7:0] S81_7x7, S82_7x7, S83_7x7, S84_7x7, S85_7x7, S86_7x7, S87_7x7, S88_7x7;
  wire [7:0] S89_7x7, S90_7x7, S91_7x7, S92_7x7, S93_7x7, S94_7x7, S95_7x7, S96_7x7;
  wire [7:0] S97_7x7, S98_7x7, S99_7x7, S100_7x7, S101_7x7, S102_7x7, S103_7x7, S104_7x7;
  wire [7:0] S105_7x7, S106_7x7, S107_7x7, S108_7x7, S109_7x7, S110_7x7, S111_7x7, S112_7x7;
  wire [7:0] S113_7x7, S114_7x7, S115_7x7, S116_7x7, S117_7x7, S118_7x7, S119_7x7, S120_7x7;
  wire [7:0] S121_7x7;

  wire wdbf_11x11_data_valid;
  wire wdbf_11x11_finish;

    window_buffer_11x11 inst_window_buffer_11x11
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (buffer13_m5x5_data_valid),
      .start_i      (buffer13_m5x5_data_start),
      .S1_i         (data11_m5x5),
      .S2_i         (data10_m5x5),
      .S3_i         (data9_m5x5),
      .S4_i         (data8_m5x5),
      .S5_i         (data7_m5x5),
      .S6_i         (data6_m5x5),
      .S7_i         (data5_m5x5),
      .S8_i         (data4_m5x5),
      .S9_i         (data3_m5x5),
      .S10_i        (data2_m5x5),
      .S11_i        (data1_m5x5),
      .IMG_SIZE_I  (IMG_SIZE),
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
      .S50_o        (S50_7x7),
      .S51_o        (S51_7x7),
      .S52_o        (S52_7x7),
      .S53_o        (S53_7x7),
      .S54_o        (S54_7x7),
      .S55_o        (S55_7x7),
      .S56_o        (S56_7x7),
      .S57_o        (S57_7x7),
      .S58_o        (S58_7x7),
      .S59_o        (S59_7x7),
      .S60_o        (S60_7x7),
      .S61_o        (S61_7x7),
      .S62_o        (S62_7x7),
      .S63_o        (S63_7x7),
      .S64_o        (S64_7x7),
      .S65_o        (S65_7x7),
      .S66_o        (S66_7x7),
      .S67_o        (S67_7x7),
      .S68_o        (S68_7x7),
      .S69_o        (S69_7x7),
      .S70_o        (S70_7x7),
      .S71_o        (S71_7x7),
      .S72_o        (S72_7x7),
      .S73_o        (S73_7x7),
      .S74_o        (S74_7x7),
      .S75_o        (S75_7x7),
      .S76_o        (S76_7x7),
      .S77_o        (S77_7x7),
      .S78_o        (S78_7x7),
      .S79_o        (S79_7x7),
      .S80_o        (S80_7x7),
      .S81_o        (S81_7x7),
      .S82_o        (S82_7x7),
      .S83_o        (S83_7x7),
      .S84_o        (S84_7x7),
      .S85_o        (S85_7x7),
      .S86_o        (S86_7x7),
      .S87_o        (S87_7x7),
      .S88_o        (S88_7x7),
      .S89_o        (S89_7x7),
      .S90_o        (S90_7x7),
      .S91_o        (S91_7x7),
      .S92_o        (S92_7x7),
      .S93_o        (S93_7x7),
      .S94_o        (S94_7x7),
      .S95_o        (S95_7x7),
      .S96_o        (S96_7x7),
      .S97_o        (S97_7x7),
      .S98_o        (S98_7x7),
      .S99_o        (S99_7x7),
      .S100_o       (S100_7x7),
      .S101_o       (S101_7x7),
      .S102_o       (S102_7x7),
      .S103_o       (S103_7x7),
      .S104_o       (S104_7x7),
      .S105_o       (S105_7x7),
      .S106_o       (S106_7x7),
      .S107_o       (S107_7x7),
      .S108_o       (S108_7x7),
      .S109_o       (S109_7x7),
      .S110_o       (S110_7x7),
      .S111_o       (S111_7x7),
      .S112_o       (S112_7x7),
      .S113_o       (S113_7x7),
      .S114_o       (S114_7x7),
      .S115_o       (S115_7x7),
      .S116_o       (S116_7x7),
      .S117_o       (S117_7x7),
      .S118_o       (S118_7x7),
      .S119_o       (S119_7x7),
      .S120_o       (S120_7x7),
      .S121_o       (S121_7x7),
      .data_valid_o (wdbf_11x11_data_valid),
      .finish_o     (wdbf_11x11_finish)
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
  wire [7:0] S82_9x9, S83_9x9, S84_9x9, S85_9x9, S86_9x9, S87_9x9, S88_9x9, S89_9x9, S90_9x9;
  wire [7:0] S91_9x9, S92_9x9, S93_9x9, S94_9x9, S95_9x9, S96_9x9, S97_9x9, S98_9x9, S99_9x9;
  wire [7:0] S100_9x9, S101_9x9, S102_9x9, S103_9x9, S104_9x9, S105_9x9, S106_9x9, S107_9x9, S108_9x9;
  wire [7:0] S109_9x9, S110_9x9, S111_9x9, S112_9x9, S113_9x9, S114_9x9, S115_9x9, S116_9x9, S117_9x9;
  wire [7:0] S118_9x9, S119_9x9, S120_9x9, S121_9x9, S122_9x9, S123_9x9, S124_9x9, S125_9x9, S126_9x9;
  wire [7:0] S127_9x9, S128_9x9, S129_9x9, S130_9x9, S131_9x9, S132_9x9, S133_9x9, S134_9x9, S135_9x9;
  wire [7:0] S136_9x9, S137_9x9, S138_9x9, S139_9x9, S140_9x9, S141_9x9, S142_9x9, S143_9x9, S144_9x9;
  wire [7:0] S145_9x9, S146_9x9, S147_9x9, S148_9x9, S149_9x9, S150_9x9, S151_9x9, S152_9x9, S153_9x9;
  wire [7:0] S154_9x9, S155_9x9, S156_9x9, S157_9x9, S158_9x9, S159_9x9, S160_9x9, S161_9x9, S162_9x9;
  wire [7:0] S163_9x9, S164_9x9, S165_9x9, S166_9x9, S167_9x9, S168_9x9, S169_9x9;
  wire wdbf_13x13_data_valid;
  wire wdbf_13x13_finish;

  window_buffer_13x13 WINDOW_BUFFER_13x13 (
      .clk            (clk),
      .rst_n          (rst_n),
      .data_valid_i         (buffer13_m7x7_data_valid),
      .start_i     (buffer13_m7x7_data_start),
      .IMG_SIZE_I  (IMG_SIZE),
      .S1_i           (data12_m7x7),
      .S2_i           (data11_m7x7),
      .S3_i           (data10_m7x7),
      .S4_i           (data9_m7x7),
      .S5_i           (data8_m7x7),
      .S6_i           (data7_m7x7),
      .S7_i           (data6_m7x7),
      .S8_i           (data5_m7x7),
      .S9_i           (data4_m7x7),
      .S10_i          (data3_m7x7),
      .S11_i          (data2_m7x7),
      .S12_i          (data1_m7x7),
      .S13_i          (data0_m7x7),
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
      .S82_o          (S82_9x9),
      .S83_o          (S83_9x9),
      .S84_o          (S84_9x9),
      .S85_o          (S85_9x9),
      .S86_o          (S86_9x9),
      .S87_o          (S87_9x9),
      .S88_o          (S88_9x9),
      .S89_o          (S89_9x9),
      .S90_o          (S90_9x9),
      .S91_o          (S91_9x9),
      .S92_o          (S92_9x9),
      .S93_o          (S93_9x9),
      .S94_o          (S94_9x9),
      .S95_o          (S95_9x9),
      .S96_o          (S96_9x9),
      .S97_o          (S97_9x9),
      .S98_o          (S98_9x9),
      .S99_o          (S99_9x9),
      .S100_o         (S100_9x9),
      .S101_o         (S101_9x9),
      .S102_o         (S102_9x9),
      .S103_o         (S103_9x9),
      .S104_o         (S104_9x9),
      .S105_o         (S105_9x9),
      .S106_o         (S106_9x9),
      .S107_o         (S107_9x9),
      .S108_o         (S108_9x9),
      .S109_o         (S109_9x9),
      .S110_o         (S110_9x9),
      .S111_o         (S111_9x9),
      .S112_o         (S112_9x9),
      .S113_o         (S113_9x9),
      .S114_o         (S114_9x9),
      .S115_o         (S115_9x9),
      .S116_o         (S116_9x9),
      .S117_o         (S117_9x9),
      .S118_o         (S118_9x9),
      .S119_o         (S119_9x9),
      .S120_o         (S120_9x9),
      .S121_o         (S121_9x9),
      .S122_o         (S122_9x9),
      .S123_o         (S123_9x9),
      .S124_o         (S124_9x9),
      .S125_o         (S125_9x9),
      .S126_o         (S126_9x9),
      .S127_o         (S127_9x9),
      .S128_o         (S128_9x9),
      .S129_o         (S129_9x9),
      .S130_o         (S130_9x9),
      .S131_o         (S131_9x9),
      .S132_o         (S132_9x9),
      .S133_o         (S133_9x9),
      .S134_o         (S134_9x9),
      .S135_o         (S135_9x9),
      .S136_o         (S136_9x9),
      .S137_o         (S137_9x9),
      .S138_o         (S138_9x9),
      .S139_o         (S139_9x9),
      .S140_o         (S140_9x9),
      .S141_o         (S141_9x9),
      .S142_o         (S142_9x9),
      .S143_o         (S143_9x9),
      .S144_o         (S144_9x9),
      .S145_o         (S145_9x9),
      .S146_o         (S146_9x9),
      .S147_o         (S147_9x9),
      .S148_o         (S148_9x9),
      .S149_o         (S149_9x9),
      .S150_o         (S150_9x9),
      .S151_o         (S151_9x9),
      .S152_o         (S152_9x9),
      .S153_o         (S153_9x9),
      .S154_o         (S154_9x9),
      .S155_o         (S155_9x9),
      .S156_o         (S156_9x9),
      .S157_o         (S157_9x9),
      .S158_o         (S158_9x9),
      .S159_o         (S159_9x9),
      .S160_o         (S160_9x9),
      .S161_o         (S161_9x9),
      .S162_o         (S162_9x9),
      .S163_o         (S163_9x9),
      .S164_o         (S164_9x9),
      .S165_o         (S165_9x9),
      .S166_o         (S166_9x9),
      .S167_o         (S167_9x9),
      .S168_o         (S168_9x9),
      .S169_o         (S169_9x9),
      .data_valid_o         (wdbf_13x13_data_valid),
      .finish_o(wdbf_13x13_finish)
  );

  wire [23:0] S1_r5, S2_r5, S3_r5, S4_r5, S5_r5, S6_r5, S7_r5, S8_r5;
  wire r5_inter_finish;
  wire r5_inter_valid;

  // 1 2 3 4 5 6 7 8 9 10 11 
  // 12 13 14 15 16 17 18 19 20 21 22
  // 23 24 25 26 27 28 29 30 31 32 33
  // 34 35 36 37 38 39 40 41 42 43 44
  // 45 46 47 48 49 50 51 52 53 54 55
  // 56 57 58 59 60 61 62 63 64 65 66
  // 67 68 69 70 71 72 73 74 75 76 77
  // 78 79 80 81 82 83 84 85 86 87 88
  // 89 90 91 92 93 94 95 96 97 98 99
  // 100 101 102 103 104 105 106 107 108 109 110
  // 111 112 113 114 115 116 117 118 119 120 121
  interpolation_R_x #(
      .R(5)
  ) INTERPOLATION_R_5 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(wdbf_13x13_finish),
      .data_valid_i(wdbf_13x13_data_valid),
      .S_0_i(S66_7x7),
      .S_90_i(S6_7x7),
      .S_180_i(S56_7x7),
      .S_270_i(S116_7x7),
      .S_45_i_1(S20_7x7),
      .S_45_i_2(S21_7x7),
      .S_45_i_3(S31_7x7),
      .S_45_i_4(S32_7x7),
      .S_135_i_1(S13_7x7),
      .S_135_i_2(S14_7x7),
      .S_135_i_3(S24_7x7),
      .S_135_i_4(S25_7x7),
      .S_225_i_1(S90_7x7),
      .S_225_i_2(S91_7x7),
      .S_225_i_3(S101_7x7),
      .S_225_i_4(S102_7x7),
      .S_315_i_1(S97_7x7),
      .S_315_i_2(S98_7x7),
      .S_315_i_3(S108_7x7),
      .S_315_i_4(S109_7x7),
      .S1_o(S1_r5),
      .S2_o(S2_r5),
      .S3_o(S3_r5),
      .S4_o(S4_r5),
      .S5_o(S5_r5),
      .S6_o(S6_r5),
      .S7_o(S7_r5),
      .S8_o(S8_r5),
      .data_valid_o(r5_inter_valid),
      .finish_o(r5_inter_finish)
  );
  wire [23:0] S1_r6, S2_r6, S3_r6, S4_r6, S5_r6, S6_r6, S7_r6, S8_r6;
  wire r6_inter_valid;
  wire r6_inter_finish;

  // 1 2 3 4 5 6 7 8 9 10 11 12 13
  // 14 15 16 17 18 19 20 21 22 23 24 25 26
  // 27 28 29 30 31 32 33 34 35 36 37 38 39
  // 40 41 42 43 44 45 46 47 48 49 50 51 52
  // 53 54 55 56 57 58 59 60 61 62 63 64 65
  // 66 67 68 69 70 71 72 73 74 75 76 77 78
  // 79 80 81 82 83 84 85 86 87 88 89 90 91
  // 92 93 94 95 96 97 98 99 100 101 102 103 104
  // 105 106 107 108 109 110 111 112 113 114 115 116 117
  // 118 119 120 121 122 123 124 125 126 127 128 129 130
  // 131 132 133 134 135 136 137 138 139 140 141 142 143
  // 144 145 146 147 148 149 150 151 152 153 154 155 156
  // 157 158 159 160 161 162 163 164 165 166 167 168 169
  interpolation_R_x #(
      .R(6)
  ) INTERPOLATION_R_6 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(wdbf_13x13_finish),
      .data_valid_i(wdbf_13x13_data_valid),
      .S_0_i(S91_9x9),
      .S_90_i(S7_9x9),
      .S_180_i(S79_9x9),
      .S_270_i(S163_9x9),
      .S_45_i_1(S24_9x9),
      .S_45_i_2(S25_9x9),
      .S_45_i_3(S37_9x9),
      .S_45_i_4(S38_9x9),
      .S_135_i_1(S15_9x9),
      .S_135_i_2(S16_9x9),
      .S_135_i_3(S28_9x9),
      .S_135_i_4(S29_9x9),
      .S_225_i_1(S132_9x9),
      .S_225_i_2(S133_9x9),
      .S_225_i_3(S145_9x9),
      .S_225_i_4(S146_9x9),
      .S_315_i_1(S141_9x9),
      .S_315_i_2(S142_9x9),
      .S_315_i_3(S154_9x9),
      .S_315_i_4(S155_9x9),
      .S1_o(S1_r6),
      .S2_o(S2_r6),
      .S3_o(S3_r6),
      .S4_o(S4_r6),
      .S5_o(S5_r6),
      .S6_o(S6_r6),
      .S7_o(S7_r6),
      .S8_o(S8_r6),
      .data_valid_o(r6_inter_valid),
      .finish_o(r6_inter_finish)
  );




  wire [15:0] r6_patch_sum;
  wire patch_sum_data_valid;
  wire patch_sum_finish;

    r6_patch_sum inst_r6_patch_sum
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (buffer13_m7x7_data_valid),
      .start_i      (buffer13_m7x7_data_start),
      .IMG_SIZE_I   (IMG_SIZE),
      .S1           (data0_m7x7),
      .S2           (data1_m7x7),
      .S3           (data2_m7x7),
      .S4           (data3_m7x7),
      .S5           (data4_m7x7),
      .S6           (data5_m7x7),
      .S7           (data6_m7x7),
      .S8           (data7_m7x7),
      .S9           (data8_m7x7),
      .S10          (data9_m7x7),
      .S11          (data10_m7x7),
      .S12          (data11_m7x7),
      .S13          (data12_m7x7),
      .sum_o        (r6_patch_sum),
      .data_valid_o (patch_sum_data_valid),
      .finish_o     (patch_sum_finish)
    );


    wire rd_valid;
    wire rd_finish;

    wire bit1_rd, bit2_rd, bit3_rd, bit4_rd, bit5_rd, bit6_rd, bit7_rd, bit8_rd;
    rd rd_calc_r6 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r6_inter_valid),
      .finish_i(r6_inter_finish),
      .S1_r2(S1_r6),
      .S2_r2(S2_r6),
      .S3_r2(S3_r6),
      .S4_r2(S4_r6),
      .S5_r2(S5_r6),
      .S6_r2(S6_r6),
      .S7_r2(S7_r6),
      .S8_r2(S8_r6),
      .S1_r1(S1_r5),
      .S2_r1(S2_r5),
      .S3_r1(S3_r5),
      .S4_r1(S4_r5),
      .S5_r1(S5_r5),
      .S6_r1(S6_r5),
      .S7_r1(S7_r5),
      .S8_r1(S8_r5),
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


  wire ni_valid;
  wire ni_finish;
  wire bit1_ni, bit2_ni, bit3_ni,
    bit4_ni, bit5_ni, bit6_ni, bit7_ni, bit8_ni;
  ni #(
      .WIDTH(16),
      .GAIN (169)
  ) ni_CALC_r6 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r6_inter_valid),
      .finish_i(r6_inter_finish),
      .S1_r2(S1_r6),
      .S2_r2(S2_r6),
      .S3_r2(S3_r6),
      .S4_r2(S4_r6),
      .S5_r2(S5_r6),
      .S6_r2(S6_r6),
      .S7_r2(S7_r6),
      .S8_r2(S8_r6),
      .sum_i(r6_patch_sum),
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
      .finish_o    ()  
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
      .finish_i(ni_valid),
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