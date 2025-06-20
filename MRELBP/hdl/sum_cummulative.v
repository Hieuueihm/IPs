module sum_cumulative #(
    parameter WIDTH1 = 13,
    parameter WIDTH2 = 13
) (
    input clk,
    input rst_n,
    input en,
    input ld,
    input [WIDTH1-1:0] data_in1,
    input [WIDTH1-1:0] data_in2,
    output reg [WIDTH2-1:0] sum_out
);

  wire [WIDTH2-1:0] sum_next;
  (* use_carry_chain = "yes" *)wire [WIDTH2-1:0] mux_a_out;

  assign mux_a_out = en ? (sum_out + data_in1 + data_in2) : sum_out;

  assign sum_next  = ld ? data_in1 : mux_a_out;
  always @(posedge clk) begin
    if (~rst_n) sum_out <= 0;
    else sum_out <= sum_next;
  end

endmodule