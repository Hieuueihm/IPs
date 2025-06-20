module ni_calc #(
    parameter WIDTH = 10,
    parameter GAIN  = 25
) (
    input clk,
    input rst_n,
    input [23:0] S,
    input [WIDTH - 1:0] sum_i,
    output bit_o
);

  reg [23:0] S_reg;
  reg [16+WIDTH - 1:0] scaled_S_r2;
  reg [16+WIDTH - 1:0] scaled_S_r2_reg;





  // Pipeline Stage 1: Register Input
  always @(posedge clk) begin
    if (~rst_n) begin
      S_reg <= 0;
    end else begin
      S_reg <= S;
    end
  end

  // Pipeline Stage 2: Perform Multiplication
  always @(posedge clk) begin
    if (~rst_n) begin
      scaled_S_r2 <= 0;
    end else begin
      scaled_S_r2 <= S_reg * GAIN;
    end
  end

  // Pipeline Stage 3: Register Output
  always @(posedge clk) begin
    if (~rst_n) begin
      scaled_S_r2_reg <= 0;
    end else begin
      scaled_S_r2_reg <= scaled_S_r2;
    end
  end



  wire [WIDTH - 1 : 0] sum_delay;
  shift_registers #(
      .WIDTH(WIDTH),
      .CYCLE(3)
  ) shift_registers_sum_i (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(sum_i),
      .data_o(sum_delay)
  );
  wire compare_result;
  assign compare_result = (scaled_S_r2_reg[16+WIDTH-1 : 16] < sum_delay) ? 1'b0 : 1'b1;
  reg registered_bit_o;
  always @(posedge clk) begin
    if (~rst_n) begin
      registered_bit_o <= 0;
    end else begin
      registered_bit_o <= compare_result;
    end

  end
  assign bit_o = registered_bit_o;

endmodule