module rd (
    input clk,
    input rst_n,
    input data_valid_i,
    input finish_i,
    input [23:0] S1_r2,
    S2_r2,
    S3_r2,
    S4_r2,
    S5_r2,
    S6_r2,
    S7_r2,
    S8_r2,
    input [23:0] S1_r1,
    S2_r1,
    S3_r1,
    S4_r1,
    S5_r1,
    S6_r1,
    S7_r1,
    S8_r1,
    output reg data_valid_o,
    output reg finish_o,
    output bit1_o,
    bit2_o,
    bit3_o,
    bit4_o,
    bit5_o,
    bit6_o,
    bit7_o,
    bit8_o
);

  always @(posedge clk) begin
    if (~rst_n) begin
      finish_o <= 1'b0;
      data_valid_o <= 1'b0;
    end else begin
      finish_o <= finish_i;
      data_valid_o <= data_valid_i;
    end
  end
  rd_calc rd1 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S1_r2),
      .S_r1(S1_r1),
      .bit_o(bit1_o)
  );
  rd_calc rd2 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S2_r2),
      .S_r1(S2_r1),
      .bit_o(bit2_o)
  );
  rd_calc rd3 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S3_r2),
      .S_r1(S3_r1),
      .bit_o(bit3_o)
  );
  rd_calc rd4 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S4_r2),
      .S_r1(S4_r1),
      .bit_o(bit4_o)
  );
  rd_calc rd5 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S5_r2),
      .S_r1(S5_r1),
      .bit_o(bit5_o)
  );
  rd_calc rd6 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S6_r2),
      .S_r1(S6_r1),
      .bit_o(bit6_o)
  );
  rd_calc rd7 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S7_r2),
      .S_r1(S7_r1),
      .bit_o(bit7_o)
  );
  rd_calc rd8 (
      .clk(clk),
      .rst_n(rst_n),
      .S_r2(S8_r2),
      .S_r1(S8_r1),
      .bit_o(bit8_o)
  );

endmodule