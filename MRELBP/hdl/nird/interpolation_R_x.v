
module interpolation_R_x #(
    parameter R = 2
) (
    input clk,
    input rst_n,
    input data_valid_i,
    input finish_i,
    input [7:0] S_0_i,
    S_90_i,
    S_180_i,
    S_270_i,
    S_45_i_1,
    S_45_i_2,
    S_45_i_3,
    S_45_i_4,
    S_135_i_1,
    S_135_i_2,
    S_135_i_3,
    S_135_i_4,
    S_225_i_1,
    S_225_i_2,
    S_225_i_3,
    S_225_i_4,
    S_315_i_1,
    S_315_i_2,
    S_315_i_3,
    S_315_i_4,
    output [23:0] S1_o,
    S2_o,
    S3_o,
    S4_o,
    S5_o,
    S6_o,
    S7_o,
    S8_o,
    output data_valid_o,
    output finish_o
);


  // 0 -> 1
  // 45 -> 2
  // 90 -> 3
  // 135 -> 4
  // 180 -> 5
  // 225 -> 6
  // 270 -> 7
  // 315 -> 8


  generate
    if (R == 1) begin : R1_LOGIC
      reg [7:0] S2_shift_1, S2_shift_2, S2_shift_3, S2_shift_4;
      reg [7:0] S4_shift_1, S4_shift_2, S4_shift_3, S4_shift_4;
      reg [7:0] S6_shift_1, S6_shift_2, S6_shift_3, S6_shift_4;
      reg [7:0] S8_shift_1, S8_shift_2, S8_shift_3, S8_shift_4;


      // S1 = S_0_i
      // S2 = S_45_i_1
      // S3 = S_90_i
      // S4 = S_135_i_1
      // S5 = S_180_i
      // S6 = S_225_i_1
      // S7 = S_270_i
      // S8 = S_315_i_1

      // Shift logic for S2
      always @(posedge clk) begin
        if (~rst_n) begin
          S2_shift_1 <= 0;
          S2_shift_2 <= 0;
          S2_shift_3 <= 0;
        end else begin
          S2_shift_1 <= S_45_i_1;
          S2_shift_2 <= S2_shift_1;
          S2_shift_3 <= S2_shift_2;
          S2_shift_4 <= S2_shift_3;
        end
      end
      assign S2_o = {S2_shift_4, 16'b0};

      // Shift logic for S4
      always @(posedge clk) begin
        if (~rst_n) begin
          S4_shift_1 <= 0;
          S4_shift_2 <= 0;
          S4_shift_3 <= 0;
        end else begin
          S4_shift_1 <= S_135_i_1;
          S4_shift_2 <= S4_shift_1;
          S4_shift_3 <= S4_shift_2;
          S4_shift_4 <= S4_shift_3;
        end
      end
      assign S4_o = {S4_shift_4, 16'b0};

      // Shift logic for S6
      always @(posedge clk) begin
        if (~rst_n) begin
          S6_shift_1 <= 0;
          S6_shift_2 <= 0;
          S6_shift_3 <= 0;
        end else begin
          S6_shift_1 <= S_225_i_1;
          S6_shift_2 <= S6_shift_1;
          S6_shift_3 <= S6_shift_2;
          S6_shift_4 <= S6_shift_3;

        end
      end
      assign S6_o = {S6_shift_4, 16'b0};


      // Shift logic for S8
      always @(posedge clk) begin
        if (~rst_n) begin
          S8_shift_1 <= 0;
          S8_shift_2 <= 0;
          S8_shift_3 <= 0;
        end else begin
          S8_shift_1 <= S_315_i_1;
          S8_shift_2 <= S8_shift_1;
          S8_shift_3 <= S8_shift_2;
          S8_shift_4 <= S8_shift_3;
        end
      end
      assign S8_o = {S8_shift_4, 16'b0};


    end else if (R > 1) begin
      // same time

      interpolation_calc #(
          .R(R),
          .ANGLE(45)
      ) INTER_r2_45 (
          .clk(clk),
          .rst_n(rst_n),
          .A(S_45_i_1),
          .B(S_45_i_2),
          .C(S_45_i_3),
          .D(S_45_i_4),
          .data_o(S2_o)
      );

      interpolation_calc #(
          .R(R),
          .ANGLE(135)
      ) INTER_r2_135 (
          .clk(clk),
          .rst_n(rst_n),
          .A(S_135_i_1),
          .B(S_135_i_2),
          .C(S_135_i_3),
          .D(S_135_i_4),
          .data_o(S4_o)
      );



      interpolation_calc #(
          .R(R),
          .ANGLE(225)
      ) INTER_r2_225 (
          .clk(clk),
          .rst_n(rst_n),
          .A(S_225_i_1),
          .B(S_225_i_2),
          .C(S_225_i_3),
          .D(S_225_i_4),
          .data_o(S6_o)
      );


      interpolation_calc #(
          .R(R),
          .ANGLE(315)
      ) INTER_r2_315 (
          .clk(clk),
          .rst_n(rst_n),
          .A(S_315_i_1),
          .B(S_315_i_2),
          .C(S_315_i_3),
          .D(S_315_i_4),
          .data_o(S8_o)
      );


    end
  endgenerate

  reg [3:0] done_shift;
  always @(posedge clk) begin
    if (~rst_n) begin
      done_shift <= 0;
    end else begin
      done_shift <= {done_shift[2:0], data_valid_i};

    end
  end

  assign data_valid_o = done_shift[3];

  reg [3:0] progress_shift;
  always @(posedge clk) begin
    if (~rst_n) begin
      progress_shift <= 0;
    end else begin
      progress_shift <= {progress_shift[2:0], finish_i};

    end
  end

  assign finish_o = progress_shift[3];

  reg [7:0] S1_shift_1, S1_shift_2, S1_shift_3, S1_shift_4;
  reg [7:0] S3_shift_1, S3_shift_2, S3_shift_3, S3_shift_4;
  reg [7:0] S5_shift_1, S5_shift_2, S5_shift_3, S5_shift_4;
  reg [7:0] S7_shift_1, S7_shift_2, S7_shift_3, S7_shift_4;
  always @(posedge clk) begin
    if (~rst_n) begin
      S1_shift_1 <= 0;
      S1_shift_2 <= 0;
      S1_shift_3 <= 0;
    end else begin
      S1_shift_1 <= S_0_i;
      S1_shift_2 <= S1_shift_1;
      S1_shift_3 <= S1_shift_2;
      S1_shift_4 <= S1_shift_3;
    end
  end
  assign S1_o = {S1_shift_4, 16'b0};
  always @(posedge clk) begin
    if (~rst_n) begin
      S3_shift_1 <= 0;
      S3_shift_2 <= 0;
      S3_shift_3 <= 0;
    end else begin
      S3_shift_1 <= S_90_i;
      S3_shift_2 <= S3_shift_1;
      S3_shift_3 <= S3_shift_2;
      S3_shift_4 <= S3_shift_3;
    end
  end
  assign S3_o = {S3_shift_4, 16'b0};

  always @(posedge clk) begin
    if (~rst_n) begin
      S5_shift_1 <= 0;
      S5_shift_2 <= 0;
      S5_shift_3 <= 0;
    end else begin
      S5_shift_1 <= S_180_i;
      S5_shift_2 <= S5_shift_1;
      S5_shift_3 <= S5_shift_2;
      S5_shift_4 <= S5_shift_3;
    end
  end
  assign S5_o = {S5_shift_4, 16'b0};

  always @(posedge clk) begin
    if (~rst_n) begin
      S7_shift_1 <= 0;
      S7_shift_2 <= 0;
      S7_shift_3 <= 0;
    end else begin
      S7_shift_1 <= S_270_i;
      S7_shift_2 <= S7_shift_1;
      S7_shift_3 <= S7_shift_2;
      S7_shift_4 <= S7_shift_3;
    end
  end
  assign S7_o = {S7_shift_4, 16'b0};
endmodule