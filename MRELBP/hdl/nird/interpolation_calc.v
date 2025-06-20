module interpolation_calc #(
    parameter R = 2,
    ANGLE = 45
) (
    input clk,
    input rst_n,
    input [7:0] A,
    B,
    C,
    D,
    output [23:0] data_o
);
  reg [23:0] r1, r2, r3, r4;
  // r1 = (1-dx) * (1-dy)
  // r2 = dx * (1-dy)
  // r3 = (1-dx) * dy
  // r4 = dx * dy
  always @(posedge clk) begin
    if (~rst_n) begin
      case ({
        ANGLE, R
      })
        {
          45, 2
        } : begin
          r1 <= 24'h0003E1D;
          r2 <= 24'h00057D8;
          r3 <= 24'h0002BEC;
          r4 <= 24'h0003E1D;
        end
        {
          135, 2
        } : begin
          r1 <= 24'h0002BEC;
          r2 <= 24'h0003E1D;
          r3 <= 24'h0003E1D;
          r4 <= 24'h00057D8;
        end


        {
          225, 2
        } : begin
          r1 <= 24'h0003E1D;
          r2 <= 24'h0002BEC;
          r3 <= 24'h00057D8;
          r4 <= 24'h0003E1D;
        end

        {
          315, 2
        } : begin
          r1 <= 24'h00057D8;
          r2 <= 24'h0003E1D;
          r3 <= 24'h0003E1D;
          r4 <= 24'h0002BEC;
        end
        {
          45, 3
        } : begin
          r1 <= 24'h0001B4A;
          r2 <= 24'h000C5A6;
          r3 <= 24'h00003C4;
          r4 <= 24'h0001B4A;
        end
        {
          135, 3
        } : begin
          r1 <= 24'h00003C4;
          r2 <= 24'h0001B4A;
          r3 <= 24'h0001B4A;
          r4 <= 24'h000C5A6;
        end


        {
          225, 3
        } : begin
          r1 <= 24'h0001B4A;
          r2 <= 24'h00003C4;
          r3 <= 24'h000C5A6;
          r4 <= 24'h0001B4A;
        end

        {
          315, 3
        } : begin
          r1 <= 24'h000C5A6;
          r2 <= 24'h0001B4A;
          r3 <= 24'h0001B4A;
          r4 <= 24'h00003C4;
        end
        {
          45, 4
        } : begin
          r1 <= 24'h002463;
          r2 <= 24'h000789;
          r3 <= 24'h00afb0;
          r4 <= 24'h002463;
        end
        {
          135, 4
        } : begin
          r1 <= 24'h00afb0;
          r2 <= 24'h002463;
          r3 <= 24'h002463;
          r4 <= 24'h000789;
        end


        {
          225, 4
        } : begin
          r1 <= 24'h002463;
          r2 <= 24'h00AFB0;
          r3 <= 24'h000789;
          r4 <= 24'h002463;
        end

        {
          315, 4
        } : begin
          r1 <= 24'h000789;
          r2 <= 24'h002463;
          r3 <= 24'h002463;
          r4 <= 24'h00AFB0;
        end

        {
          45, 5
        } : begin
          r1 <= 24'h0003FAD;
          r2 <= 24'h0003739;
          r3 <= 24'h000496B;
          r4 <= 24'h0003FAD;
        end
        {
          135, 5
        } : begin
          r1 <= 24'h000496B;
          r2 <= 24'h0003FAD;
          r3 <= 24'h0003FAD;
          r4 <= 24'h0003739;

        end


        {
          225, 5
        } : begin
          r1 <= 24'h0003FAD;
          r2 <= 24'h000496B;
          r3 <= 24'h0003739;
          r4 <= 24'h0003FAD;
        end

        {
          315, 5
        } : begin
          r1 <= 24'h0003739;
          r2 <= 24'h0003FAD;
          r3 <= 24'h0003FAD;
          r4 <= 24'h000496B;
        end
        {
          45, 6
        } : begin
          r1 <= 24'h0002F0B;
          r2 <= 24'h00092D6;
          r3 <= 24'h0000F12;
          r4 <= 24'h0002F0B;
        end
        {
          135, 6
        } : begin
          r1 <= 24'h0000F12;
          r2 <= 24'h0002F0B;
          r3 <= 24'h0002F0B;
          r4 <= 24'h00092D6;
        end


        {
          225, 6
        } : begin
          r1 <= 24'h0002F0B;
          r2 <= 24'h0000F12;
          r3 <= 24'h00092D6;
          r4 <= 24'h0002F0B;
        end

        {
          315, 6
        } : begin
          r1 <= 24'h00092D6;
          r2 <= 24'h0002F0B;
          r3 <= 24'h0002F0B;
          r4 <= 24'h0000F12;
        end
        {
          45, 7
        } : begin
          r1 <= 24'h0000C37;
          r2 <= 24'h00000A5;
          r3 <= 24'h000E6EA;
          r4 <= 24'h0000C37;
        end
        {
          135, 7
        } : begin
          r1 <= 24'h000E6EA;
          r2 <= 24'h0000C37;
          r3 <= 24'h0000C37;
          r4 <= 24'h00000A5;
        end


        {
          225, 7
        } : begin
          r1 <= 24'h0000C37;
          r2 <= 24'h000E6EA;
          r3 <= 24'h00000A5;
          r4 <= 24'h0000C37;
        end

        {
          315, 7
        } : begin
          r1 <= 24'h00000A5;
          r2 <= 24'h0000C37;
          r3 <= 24'h0000C37;
          r4 <= 24'h000E6EA;
        end
        {
          45, 8
        } : begin
          r1 <= 24'h00039B3;
          r2 <= 24'h0001E24;
          r3 <= 24'h0006E73;
          r4 <= 24'h00039B3;
        end
        {
          135, 8
        } : begin
          r1 <= 24'h0006E73;
          r2 <= 24'h00039B3;
          r3 <= 24'h00039B3;
          r4 <= 24'h0001E24;
        end


        {
          225, 8
        } : begin
          r1 <= 24'h00039B3;
          r2 <= 24'h0006E73;
          r3 <= 24'h0001E24;
          r4 <= 24'h00039B3;
        end

        {
          315, 8
        } : begin
          r1 <= 24'h0001E24;
          r2 <= 24'h00039B3;
          r3 <= 24'h00039B3;
          r4 <= 24'h0006E73;
        end
      endcase
    end
  end

  reg [23:0] mult_result1, mult_result2, mult_result3, mult_result4;
  reg [23:0] add_result1, add_result2;
  reg [23:0] r1_mul_a, r2_mul_b, r3_mul_c, r4_mul_d;
  reg [23:0] add_12, add_34;
  reg [23:0] add_result;

  reg [23:0] A_q, B_q, C_q, D_q;
  always @(posedge clk) begin
    if (~rst_n) begin
      A_q <= 24'h0;
      B_q <= 24'h0;
      C_q <= 24'h0;
      D_q <= 24'h0;
    end else begin
      A_q <= A;
      B_q <= B;
      C_q <= C;
      D_q <= D;
    end
  end
  always @(posedge clk) begin
    if (~rst_n) begin
      r1_mul_a <= 24'h0;
      r2_mul_b <= 24'h0;
      r3_mul_c <= 24'h0;
      r4_mul_d <= 24'h0;
    end else begin
      r1_mul_a <= r1 * A_q;
      r2_mul_b <= r2 * B_q;
      r3_mul_c <= r3 * C_q;
      r4_mul_d <= r4 * D_q;
    end
  end


  always @(posedge clk) begin
    if (~rst_n) begin
      add_12 <= 24'h0;
      add_34 <= 24'h0;
    end else begin
      add_12 <= r1_mul_a + r2_mul_b;
      add_34 <= r3_mul_c + r4_mul_d;
    end
  end

  // Final addition pipeline stage
  always @(posedge clk) begin
    if (~rst_n) begin
      add_result <= 24'h0;
    end else begin
      add_result <= add_12 + add_34;
    end
  end
  assign data_o = add_result;
endmodule