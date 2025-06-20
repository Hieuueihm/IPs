module median_7x7_calc (
    input clk,
    input rst_n,
    input data_valid_i,
    input [7:0] S1,
    S2,
    S3,
    S4,
    S5,
    input [7:0] S6,
    S7,
    S8,
    S9,
    S10,
    input [7:0] S11,
    S12,
    S13,
    S14,
    S15,
    input [7:0] S16,
    S17,
    S18,
    S19,
    S20,
    input [7:0] S21,
    S22,
    S23,
    S24,
    S25,
    S26,
    input [7:0] S27,
    S28,
    S29,
    S30,
    S31,
    input [7:0] S32,
    S33,
    S34,
    S35,
    S36,
    input [7:0] S37,
    S38,
    S39,
    S40,
    S41,
    input [7:0] S42,
    S43,
    S44,
    S45,
    S46,
    input [7:0] S47,
    S48,
    S49,
    output [7:0] median_o,
    output data_valid_o
);

  reg [7:0]
      p1_S1,
      p1_S2,
      p1_S3,
      p1_S4,
      p1_S5,
      p1_S6,
      p1_S7,
      p1_S8,
      p1_S9,
      p1_S10,
      p1_S11,
      p1_S12,
      p1_S13,
      p1_S14,
      p1_S15,
      p1_S16,
      p1_S17,
      p1_S18,
      p1_S19,
      p1_S20,
      p1_S21,
      p1_S22,
      p1_S23,
      p1_S24,
      p1_S25,
      p1_S26,
      p1_S27,
      p1_S28,
      p1_S29,
      p1_S30,
      p1_S31,
      p1_S32,
      p1_S33,
      p1_S34,
      p1_S35,
      p1_S36,
      p1_S37,
      p1_S38,
      p1_S39,
      p1_S40,
      p1_S41,
      p1_S42,
      p1_S43,
      p1_S44,
      p1_S45,
      p1_S46,
      p1_S47,
      p1_S48,
      p1_S49;
  reg p1_done_i;

  always @(posedge clk) begin
    if (~rst_n) begin
      p1_S1     <= 0;
      p1_S2     <= 0;
      p1_S3     <= 0;
      p1_S4     <= 0;
      p1_S5     <= 0;
      p1_S6     <= 0;
      p1_S7     <= 0;
      p1_S8     <= 0;
      p1_S9     <= 0;
      p1_S10    <= 0;
      p1_S11    <= 0;
      p1_S12    <= 0;
      p1_S13    <= 0;
      p1_S14    <= 0;
      p1_S15    <= 0;
      p1_S16    <= 0;
      p1_S17    <= 0;
      p1_S18    <= 0;
      p1_S19    <= 0;
      p1_S20    <= 0;
      p1_S21    <= 0;
      p1_S22    <= 0;
      p1_S23    <= 0;
      p1_S24    <= 0;
      p1_S25    <= 0;
      p1_S26    <= 0;
      p1_S27    <= 0;
      p1_S28    <= 0;
      p1_S29    <= 0;
      p1_S30    <= 0;
      p1_S31    <= 0;
      p1_S32    <= 0;
      p1_S33    <= 0;
      p1_S34    <= 0;
      p1_S35    <= 0;
      p1_S36    <= 0;
      p1_S37    <= 0;
      p1_S38    <= 0;
      p1_S39    <= 0;
      p1_S40    <= 0;
      p1_S41    <= 0;
      p1_S42    <= 0;
      p1_S43    <= 0;
      p1_S44    <= 0;
      p1_S45    <= 0;
      p1_S46    <= 0;
      p1_S47    <= 0;
      p1_S48    <= 0;
      p1_S49    <= 0;
      p1_done_i <= 0;
    end else begin
      p1_S1     <= S1;
      p1_S2     <= S2;
      p1_S3     <= S3;
      p1_S4     <= S4;
      p1_S5     <= S5;
      p1_S6     <= S6;
      p1_S7     <= S7;
      p1_S8     <= S8;
      p1_S9     <= S9;
      p1_S10    <= S10;
      p1_S11    <= S11;
      p1_S12    <= S12;
      p1_S13    <= S13;
      p1_S14    <= S14;
      p1_S15    <= S15;
      p1_S16    <= S16;
      p1_S17    <= S17;
      p1_S18    <= S18;
      p1_S19    <= S19;
      p1_S20    <= S20;
      p1_S21    <= S21;
      p1_S22    <= S22;
      p1_S23    <= S23;
      p1_S24    <= S24;
      p1_S25    <= S25;
      p1_S26    <= S26;
      p1_S27    <= S27;
      p1_S28    <= S28;
      p1_S29    <= S29;
      p1_S30    <= S30;
      p1_S31    <= S31;
      p1_S32    <= S32;
      p1_S33    <= S33;
      p1_S34    <= S34;
      p1_S35    <= S35;
      p1_S36    <= S36;
      p1_S37    <= S37;
      p1_S38    <= S38;
      p1_S39    <= S39;
      p1_S40    <= S40;
      p1_S41    <= S41;
      p1_S42    <= S42;
      p1_S43    <= S43;
      p1_S44    <= S44;
      p1_S45    <= S45;
      p1_S46    <= S46;
      p1_S47    <= S47;
      p1_S48    <= S48;
      p1_S49    <= S49;
      p1_done_i <= data_valid_i;
    end
  end

  // stage 1 - sort row
  wire [7:0] sa1_max, sa1_out6, sa1_out5, sa1_mid, sa1_out3, sa1_out2, sa1_min;
  wire [7:0] sa2_max, sa2_out6, sa2_out5, sa2_mid, sa2_out3, sa2_out2, sa2_min;
  wire [7:0] sa3_max, sa3_out6, sa3_out5, sa3_mid, sa3_out3, sa3_out2, sa3_min;
  wire [7:0] sa4_max, sa4_out6, sa4_out5, sa4_mid, sa4_out3, sa4_out2, sa4_min;
  wire [7:0] sa5_max, sa5_out6, sa5_out5, sa5_mid, sa5_out3, sa5_out2, sa5_min;
  wire [7:0] sa6_max, sa6_out6, sa6_out5, sa6_mid, sa6_out3, sa6_out2, sa6_min;
  wire [7:0] sa7_max, sa7_out6, sa7_out5, sa7_mid, sa7_out3, sa7_out2, sa7_min;

  wire p2_done_i;
  shift_registers #(
      .WIDTH(1),
      .CYCLE(9)
  ) shift_registers_st_1 (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(p1_done_i),
      .data_o(p2_done_i)
  );
  sort_ascending_7 SA1 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S1),
      .S2(p1_S2),
      .S3(p1_S3),
      .S4(p1_S4),
      .S5(p1_S5),
      .S6(p1_S6),
      .S7(p1_S7),
      .min(sa1_min),
      .out2(sa1_out2),
      .out3(sa1_out3),
      .mid(sa1_mid),
      .out5(sa1_out5),
      .out6(sa1_out6),
      .max(sa1_max)
  );
  sort_ascending_7 SA2 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S8),
      .S2(p1_S9),
      .S3(p1_S10),
      .S4(p1_S11),
      .S5(p1_S12),
      .S6(p1_S13),
      .S7(p1_S14),
      .min(sa2_min),
      .out2(sa2_out2),
      .out3(sa2_out3),
      .mid(sa2_mid),
      .out5(sa2_out5),
      .out6(sa2_out6),
      .max(sa2_max)
  );
  sort_ascending_7 SA3 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S15),
      .S2(p1_S16),
      .S3(p1_S17),
      .S4(p1_S18),
      .S5(p1_S19),
      .S6(p1_S20),
      .S7(p1_S21),
      .min(sa3_min),
      .out2(sa3_out2),
      .out3(sa3_out3),
      .mid(sa3_mid),
      .out5(sa3_out5),
      .out6(sa3_out6),
      .max(sa3_max)
  );
  sort_ascending_7 SA4 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S22),
      .S2(p1_S23),
      .S3(p1_S24),
      .S4(p1_S25),
      .S5(p1_S26),
      .S6(p1_S27),
      .S7(p1_S28),
      .out2(sa4_out2),
      .out3(sa4_out3),
      .mid(sa4_mid),
      .out5(sa4_out5),
      .out6(sa4_out6),
      .min(sa4_min),
      .max(sa4_max)
  );
  sort_ascending_7 SA5 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S29),
      .S2(p1_S30),
      .S3(p1_S31),
      .S4(p1_S32),
      .S5(p1_S33),
      .S6(p1_S34),
      .S7(p1_S35),
      .min(sa5_min),
      .out2(sa5_out2),
      .out3(sa5_out3),
      .mid(sa5_mid),
      .out5(sa5_out5),
      .out6(sa5_out6),
      .max(sa5_max)
  );
  sort_ascending_7 SA6 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S36),
      .S2(p1_S37),
      .S3(p1_S38),
      .S4(p1_S39),
      .S5(p1_S40),
      .S6(p1_S41),
      .S7(p1_S42),
      .out2(sa6_out2),
      .out3(sa6_out3),
      .mid(sa6_mid),
      .out5(sa6_out5),
      .min(sa6_min),
      .out6(sa6_out6),
      .max(sa6_max)
  );
  sort_ascending_7 SA7 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p1_S43),
      .S2(p1_S44),
      .S3(p1_S45),
      .S4(p1_S46),
      .S5(p1_S47),
      .S6(p1_S48),
      .S7(p1_S49),
      .min(sa7_min),
      .out2(sa7_out2),
      .out3(sa7_out3),
      .mid(sa7_mid),
      .out5(sa7_out5),
      .out6(sa7_out6),
      .max(sa7_max)
  );


  reg p2_done_i_delay;
  reg [7:0] p2_sa8_S1, p2_sa8_S2, p2_sa8_S3, p2_sa8_S4, p2_sa8_S5, p2_sa8_S6, p2_sa8_S7;
  reg [7:0] p2_sa9_S1, p2_sa9_S2, p2_sa9_S3, p2_sa9_S4, p2_sa9_S5, p2_sa9_S6, p2_sa9_S7;
  reg [7:0] p2_sa10_S1, p2_sa10_S2, p2_sa10_S3, p2_sa10_S4, p2_sa10_S5, p2_sa10_S6, p2_sa10_S7;
  reg [7:0] p2_sa11_S1, p2_sa11_S2, p2_sa11_S3, p2_sa11_S4, p2_sa11_S5, p2_sa11_S6, p2_sa11_S7;
  reg [7:0] p2_sa12_S1, p2_sa12_S2, p2_sa12_S3, p2_sa12_S4, p2_sa12_S5, p2_sa12_S6, p2_sa12_S7;
  reg [7:0] p2_sa13_S1, p2_sa13_S2, p2_sa13_S3, p2_sa13_S4, p2_sa13_S5, p2_sa13_S6, p2_sa13_S7;
  reg [7:0] p2_sa14_S1, p2_sa14_S2, p2_sa14_S3, p2_sa14_S4, p2_sa14_S5, p2_sa14_S6, p2_sa14_S7;
  always @(posedge clk) begin
    if (~rst_n) begin
      p2_done_i_delay <= 1'b0;

      p2_sa8_S1 <= 8'd0;
      p2_sa8_S2 <= 8'd0;
      p2_sa8_S3 <= 8'd0;
      p2_sa8_S4 <= 8'd0;
      p2_sa8_S5 <= 8'd0;
      p2_sa8_S6 <= 8'd0;
      p2_sa8_S7 <= 8'd0;

      p2_sa9_S1 <= 8'd0;
      p2_sa9_S2 <= 8'd0;
      p2_sa9_S3 <= 8'd0;
      p2_sa9_S4 <= 8'd0;
      p2_sa9_S5 <= 8'd0;
      p2_sa9_S6 <= 8'd0;
      p2_sa9_S7 <= 8'd0;

      p2_sa10_S1 <= 8'd0;
      p2_sa10_S2 <= 8'd0;
      p2_sa10_S3 <= 8'd0;
      p2_sa10_S4 <= 8'd0;
      p2_sa10_S5 <= 8'd0;
      p2_sa10_S6 <= 8'd0;
      p2_sa10_S7 <= 8'd0;

      p2_sa11_S1 <= 8'd0;
      p2_sa11_S2 <= 8'd0;
      p2_sa11_S3 <= 8'd0;
      p2_sa11_S4 <= 8'd0;
      p2_sa11_S5 <= 8'd0;
      p2_sa11_S6 <= 8'd0;
      p2_sa11_S7 <= 8'd0;

      p2_sa12_S1 <= 8'd0;
      p2_sa12_S2 <= 8'd0;
      p2_sa12_S3 <= 8'd0;
      p2_sa12_S4 <= 8'd0;
      p2_sa12_S5 <= 8'd0;
      p2_sa12_S6 <= 8'd0;
      p2_sa12_S7 <= 8'd0;

      p2_sa13_S1 <= 8'd0;
      p2_sa13_S2 <= 8'd0;
      p2_sa13_S3 <= 8'd0;
      p2_sa13_S4 <= 8'd0;
      p2_sa13_S5 <= 8'd0;
      p2_sa13_S6 <= 8'd0;
      p2_sa13_S7 <= 8'd0;

      p2_sa14_S1 <= 8'd0;
      p2_sa14_S2 <= 8'd0;
      p2_sa14_S3 <= 8'd0;
      p2_sa14_S4 <= 8'd0;
      p2_sa14_S5 <= 8'd0;
      p2_sa14_S6 <= 8'd0;
      p2_sa14_S7 <= 8'd0;



    end else begin

      p2_done_i_delay <= p2_done_i;

      p2_sa8_S1 <= sa1_min;
      p2_sa8_S2 <= sa2_min;
      p2_sa8_S3 <= sa3_min;
      p2_sa8_S4 <= sa4_min;
      p2_sa8_S5 <= sa5_min;
      p2_sa8_S6 <= sa6_min;
      p2_sa8_S7 <= sa7_min;

      p2_sa9_S1 <= sa1_out2;
      p2_sa9_S2 <= sa2_out2;
      p2_sa9_S3 <= sa3_out2;
      p2_sa9_S4 <= sa4_out2;
      p2_sa9_S5 <= sa5_out2;
      p2_sa9_S6 <= sa6_out2;
      p2_sa9_S7 <= sa7_out2;

      p2_sa10_S1 <= sa1_out3;
      p2_sa10_S2 <= sa2_out3;
      p2_sa10_S3 <= sa3_out3;
      p2_sa10_S4 <= sa4_out3;
      p2_sa10_S5 <= sa5_out3;
      p2_sa10_S6 <= sa6_out3;
      p2_sa10_S7 <= sa7_out3;

      p2_sa11_S1 <= sa1_mid;
      p2_sa11_S2 <= sa2_mid;
      p2_sa11_S3 <= sa3_mid;
      p2_sa11_S4 <= sa4_mid;
      p2_sa11_S5 <= sa5_mid;
      p2_sa11_S6 <= sa6_mid;
      p2_sa11_S7 <= sa7_mid;

      p2_sa12_S1 <= sa1_out5;
      p2_sa12_S2 <= sa2_out5;
      p2_sa12_S3 <= sa3_out5;
      p2_sa12_S4 <= sa4_out5;
      p2_sa12_S5 <= sa5_out5;
      p2_sa12_S6 <= sa6_out5;
      p2_sa12_S7 <= sa7_out5;

      p2_sa13_S1 <= sa1_out6;
      p2_sa13_S2 <= sa2_out6;
      p2_sa13_S3 <= sa3_out6;
      p2_sa13_S4 <= sa4_out6;
      p2_sa13_S5 <= sa5_out6;
      p2_sa13_S6 <= sa6_out6;
      p2_sa13_S7 <= sa7_out6;

      p2_sa14_S1 <= sa1_max;
      p2_sa14_S2 <= sa2_max;
      p2_sa14_S3 <= sa3_max;
      p2_sa14_S4 <= sa4_max;
      p2_sa14_S5 <= sa5_max;
      p2_sa14_S6 <= sa6_max;
      p2_sa14_S7 <= sa7_max;


    end
  end


  // stage 2 - sort cols
  wire [7:0] sa8_max, sa8_out6, sa8_out5, sa8_mid, sa8_out3, sa8_out2, sa8_min;
  wire [7:0] sa9_max, sa9_out6, sa9_out5, sa9_mid, sa9_out3, sa9_out2, sa9_min;
  wire [7:0] sa10_max, sa10_out6, sa10_out5, sa10_mid, sa10_out3, sa10_out2, sa10_min;
  wire [7:0] sa11_max, sa11_out6, sa11_out5, sa11_mid, sa11_out3, sa11_out2, sa11_min;
  wire [7:0] sa12_max, sa12_out6, sa12_out5, sa12_mid, sa12_out3, sa12_out2, sa12_min;
  wire [7:0] sa13_max, sa13_out6, sa13_out5, sa13_mid, sa13_out3, sa13_out2, sa13_min;
  wire [7:0] sa14_max, sa14_out6, sa14_out5, sa14_mid, sa14_out3, sa14_out2, sa14_min;
  wire p3_done_i;

  shift_registers #(
      .WIDTH(1),
      .CYCLE(9)
  ) shift_registers_st_2 (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(p2_done_i_delay),
      .data_o(p3_done_i)
  );

  sort_ascending_7 SA8 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa8_S1),
      .S2(p2_sa8_S2),
      .S3(p2_sa8_S3),
      .S4(p2_sa8_S4),
      .S5(p2_sa8_S5),
      .S6(p2_sa8_S6),
      .S7(p2_sa8_S7),
      .min(sa8_min),
      .out2(sa8_out2),
      .out3(sa8_out3),
      .mid(sa8_mid),
      .out5(sa8_out5),
      .out6(sa8_out6),
      .max(sa8_max)
  );
  sort_ascending_7 SA9 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa9_S1),
      .S2(p2_sa9_S2),
      .S3(p2_sa9_S3),
      .S4(p2_sa9_S4),
      .S5(p2_sa9_S5),
      .S6(p2_sa9_S6),
      .S7(p2_sa9_S7),
      .min(sa9_min),
      .out2(sa9_out2),
      .out3(sa9_out3),
      .mid(sa9_mid),
      .out5(sa9_out5),
      .out6(sa9_out6),
      .max(sa9_max)
  );
  sort_ascending_7 SA10 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa10_S1),
      .S2(p2_sa10_S2),
      .S3(p2_sa10_S3),
      .S4(p2_sa10_S4),
      .S5(p2_sa10_S5),
      .S6(p2_sa10_S6),
      .S7(p2_sa10_S7),
      .min(sa10_min),
      .out2(sa10_out2),
      .out3(sa10_out3),
      .mid(sa10_mid),
      .out5(sa10_out5),
      .out6(sa10_out6),
      .max(sa10_max)
  );
  sort_ascending_7 SA11 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa11_S1),
      .S2(p2_sa11_S2),
      .S3(p2_sa11_S3),
      .S4(p2_sa11_S4),
      .S5(p2_sa11_S5),
      .S6(p2_sa11_S6),
      .S7(p2_sa11_S7),
      .out2(sa11_out2),
      .out3(sa11_out3),
      .mid(sa11_mid),
      .out5(sa11_out5),
      .out6(sa11_out6),
      .min(sa11_min),
      .max(sa11_max)
  );
  sort_ascending_7 SA12 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa12_S1),
      .S2(p2_sa12_S2),
      .S3(p2_sa12_S3),
      .S4(p2_sa12_S4),
      .S5(p2_sa12_S5),
      .S6(p2_sa12_S6),
      .S7(p2_sa12_S7),
      .min(sa12_min),
      .out2(sa12_out2),
      .out3(sa12_out3),
      .mid(sa12_mid),
      .out5(sa12_out5),
      .out6(sa12_out6),
      .max(sa12_max)
  );
  sort_ascending_7 SA13 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa13_S1),
      .S2(p2_sa13_S2),
      .S3(p2_sa13_S3),
      .S4(p2_sa13_S4),
      .S5(p2_sa13_S5),
      .S6(p2_sa13_S6),
      .S7(p2_sa13_S7),
      .out2(sa13_out2),
      .out3(sa13_out3),
      .mid(sa13_mid),
      .out5(sa13_out5),
      .min(sa13_min),
      .out6(sa13_out6),
      .max(sa13_max)
  );
  sort_ascending_7 SA14 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p2_sa14_S1),
      .S2(p2_sa14_S2),
      .S3(p2_sa14_S3),
      .S4(p2_sa14_S4),
      .S5(p2_sa14_S5),
      .S6(p2_sa14_S6),
      .S7(p2_sa14_S7),
      .min(sa14_min),
      .out2(sa14_out2),
      .out3(sa14_out3),
      .mid(sa14_mid),
      .out5(sa14_out5),
      .out6(sa14_out6),
      .max(sa14_max)
  );


  reg p3_done_i_delay;
  reg [7:0] p3_sa8_S5, p3_sa8_S6, p3_sa8_S7;
  reg [7:0] p3_sa9_S4, p3_sa9_S5, p3_sa9_S6, p3_sa9_S7;
  reg [7:0]  p3_sa10_S3, p3_sa10_S4, p3_sa10_S5, p3_sa10_S6, p3_sa10_S7;
  reg [7:0]  p3_sa11_S2, p3_sa11_S3, p3_sa11_S4, p3_sa11_S5, p3_sa11_S6;
  reg [7:0] p3_sa12_S1, p3_sa12_S2, p3_sa12_S3, p3_sa12_S4, p3_sa12_S5;
  reg [7:0] p3_sa13_S1, p3_sa13_S2, p3_sa13_S3, p3_sa13_S4;
  reg [7:0] p3_sa14_S1, p3_sa14_S2, p3_sa14_S3;
  always @(posedge clk) begin
    if (~rst_n) begin
      p3_done_i_delay <= 1'b0;

      p3_sa8_S5 <= 8'd0;
      p3_sa8_S6 <= 8'd0;
      p3_sa8_S7 <= 8'd0;

      p3_sa9_S4 <= 8'd0;
      p3_sa9_S5 <= 8'd0;
      p3_sa9_S6 <= 8'd0;
      p3_sa9_S7 <= 8'd0;

      p3_sa10_S3 <= 8'd0;
      p3_sa10_S4 <= 8'd0;
      p3_sa10_S5 <= 8'd0;
      p3_sa10_S6 <= 8'd0;
      p3_sa10_S7 <= 8'd0;

      p3_sa11_S2 <= 8'd0;
      p3_sa11_S3 <= 8'd0;
      p3_sa11_S4 <= 8'd0;
      p3_sa11_S5 <= 8'd0;
      p3_sa11_S6 <= 8'd0;

      p3_sa12_S1 <= 8'd0;
      p3_sa12_S2 <= 8'd0;
      p3_sa12_S3 <= 8'd0;
      p3_sa12_S4 <= 8'd0;
      p3_sa12_S5 <= 8'd0;

      p3_sa13_S1 <= 8'd0;
      p3_sa13_S2 <= 8'd0;
      p3_sa13_S3 <= 8'd0;
      p3_sa13_S4 <= 8'd0;

      p3_sa14_S1 <= 8'd0;
      p3_sa14_S2 <= 8'd0;
      p3_sa14_S3 <= 8'd0;



    end else begin

      p3_done_i_delay <= p3_done_i;

      p3_sa8_S5 <= sa8_out5;
      p3_sa8_S6 <= sa8_out6;
      p3_sa8_S7 <= sa8_max;

      p3_sa9_S4 <= sa9_mid;
      p3_sa9_S5 <= sa9_out5;
      p3_sa9_S6 <= sa9_out6;
      p3_sa9_S7 <= sa9_max;

      p3_sa10_S3 <= sa10_out3;
      p3_sa10_S4 <= sa10_mid;
      p3_sa10_S5 <= sa10_out5;
      p3_sa10_S6 <= sa10_out6;
      p3_sa10_S7 <= sa10_max;

      p3_sa11_S2 <= sa11_out2;
      p3_sa11_S3 <= sa11_out3;
      p3_sa11_S4 <= sa11_mid;
      p3_sa11_S5 <= sa11_out5;
      p3_sa11_S6 <= sa11_out6;


      p3_sa12_S1 <= sa12_min;
      p3_sa12_S2 <= sa12_out2;
      p3_sa12_S3 <= sa12_out3;
      p3_sa12_S4 <= sa12_mid;
      p3_sa12_S5 <= sa12_out5;

      p3_sa13_S1 <= sa13_min;
      p3_sa13_S2 <= sa13_out2;
      p3_sa13_S3 <= sa13_out3;
      p3_sa13_S4 <= sa13_mid;


      p3_sa14_S1 <= sa14_min;
      p3_sa14_S2 <= sa14_out2;
      p3_sa14_S3 <= sa14_out3;


    end
  end

  // sort 3 upper left corner element and lower right corner element
  wire [7:0] upper_left_max, lower_right_min;
  sorting_network SN1 (
      .S1 (p3_sa10_S3),
      .S2 (p3_sa11_S2),
      .S3 (p3_sa12_S1),
      .max(upper_left_max),
      .med(),
      .min()
  );

  sorting_network SN2 (
      .S1 (p3_sa10_S7),
      .S2 (p3_sa11_S6),
      .S3 (p3_sa12_S5),
      .max(),
      .med(),
      .min(lower_right_min)
  );
  // reg [7:0]
  //     p3_S1,
  //     p3_S2,
  //     p3_S3,
  //     p3_S4,
  //     p3_S5,
  //     p3_S6,
  //     p3_S7,
  //     p3_S8,
  //     p3_S9,
  //     p3_S10,
  //     p3_S11,
  //     p3_S12,
  //     p3_S13,
  //     p3_S14,
  //     p3_S15,
  //     p3_S16,
  //     p3_S17,
  //     p3_S18,
  //     p3_S19,
  //     p3_S20,
  //     p3_S21,
  //     p3_S22,
  //     p3_S23,
  //     p3_S24,
  //     p3_S25;

  // reg p4_done_o;
  // always @(posedge clk) begin
  //   if (~rst_n) begin
  //     p3_S1 <= 0;
  //     p3_S2 <= 0;
  //     p3_S3 <= 0;
  //     p3_S4 <= 0;
  //     p3_S5 <= 0;
  //     p3_S6 <= 0;
  //     p3_S7 <= 0;
  //     p3_S8 <= 0;
  //     p3_S9 <= 0;
  //     p3_S10 <= 0;
  //     p3_S11 <= 0;
  //     p3_S12 <= 0;
  //     p3_S13 <= 0;
  //     p3_S14 <= 0;
  //     p3_S15 <= 0;
  //     p3_S16 <= 0;
  //     p3_S17 <= 0;
  //     p3_S18 <= 0;
  //     p3_S19 <= 0;
  //     p3_S20 <= 0;
  //     p3_S21 <= 0;
  //     p3_S22 <= 0;
  //     p3_S23 <= 0;
  //     p3_S24 <= 0;
  //     p3_S25 <= 0;

  //     p4_done_o <= 0;
  //   end else begin

  //     p3_S1 <= p3_sa13_S1;
  //     p3_S2 <= p3_sa14_S1;
  //     p3_S3 <= p3_sa12_S2;
  //     p3_S4 <= p3_sa13_S2;
  //     p3_S5 <= p3_sa14_S2;

  //     p3_S6 <= upper_left_max;
  //     p3_S7 <= p3_sa11_S3;
  //     p3_S8 <= p3_sa12_S3;
  //     p3_S9 <= p3_sa13_S3;
  //     p3_S10 <= p3_sa14_S3;

  //     p3_S11 <= p3_sa9_S4;
  //     p3_S12 <= p3_sa10_S4;
  //     p3_S13 <= p3_sa11_S4;
  //     p3_S14 <= p3_sa12_S4;
  //     p3_S15 <= p3_sa13_S4;


  //     p3_S16 <= p3_sa8_S5;
  //     p3_S17 <= p3_sa9_S5;
  //     p3_S18 <= p3_sa10_S5;
  //     p3_S19 <= p3_sa11_S5;
  //     p3_S20 <= lower_right_min;

  //     p3_S21 <= p3_sa8_S6;
  //     p3_S22 <= p3_sa9_S6;
  //     p3_S23 <= p3_sa10_S6;
  //     p3_S24 <= p3_sa8_S7;
  //     p3_S25 <= p3_sa9_S7;


  //     p4_done_o <= p3_done_i_delay;
  //   end
  // end








  median_5x5_calc CALC75 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(p3_done_i_delay),
      .S1(p3_sa13_S1),
      .S2(p3_sa14_S1),
      .S3(p3_sa12_S2),
      .S4(p3_sa13_S2),
      .S5(p3_sa14_S2),
      .S6(upper_left_max),
      .S7(p3_sa11_S3),
      .S8(p3_sa12_S3),
      .S9(p3_sa13_S3),
      .S10(p3_sa14_S3),
      .S11(p3_sa9_S4),
      .S12(p3_sa10_S4),
      .S13(p3_sa11_S4),
      .S14(p3_sa12_S4),
      .S15(p3_sa13_S4),
      .S16(p3_sa8_S5),
      .S17(p3_sa9_S5),
      .S18(p3_sa10_S5),
      .S19(p3_sa11_S5),
      .S20(lower_right_min),
      .S21(p3_sa8_S6),
      .S22(p3_sa9_S6),
      .S23(p3_sa10_S6),
      .S24(p3_sa8_S7),
      .S25(p3_sa9_S7),
      .median_o(median_o),
      .data_valid_o(data_valid_o)
  );




endmodule