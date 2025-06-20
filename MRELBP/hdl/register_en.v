module register_en #(
    parameter WIDTH = 8
)  //  
(
    input clk,
    input rst_n,
    input en,
    input [WIDTH - 1:0] D,
    output [WIDTH - 1:0] Q
);
  reg [WIDTH - 1:0] data_out;
  assign Q = data_out;
  always @(posedge clk) begin
    if (~rst_n) begin
      data_out <= 0;
    end else if (en) begin
      data_out <= D;
    end
  end


endmodule