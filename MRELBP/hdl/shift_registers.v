module shift_registers #(
    parameter WIDTH = 8,
    parameter CYCLE = 5
) (
    input clk,
    input rst_n,
    input [WIDTH - 1 : 0] data_i,
    output reg [WIDTH - 1:0] data_o
);

  reg [WIDTH-1:0] shift_reg[CYCLE - 2:0];

  integer i;
  always @(posedge clk) begin
    if (~rst_n) begin
      for (i = 0; i < CYCLE - 1; i = i + 1) begin
        shift_reg[i] <= 0;
      end
      data_o <= 0;
    end else begin
      shift_reg[0] <= data_i;
      for (i = 1; i < CYCLE - 1; i = i + 1) begin
        shift_reg[i] <= shift_reg[i-1];
      end
      data_o <= shift_reg[CYCLE-2];

    end
  end
  // assign data_o = shift_reg[CYCLE - 1];
endmodule