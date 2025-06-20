module sum #(
    parameter WIDTH = 8
) (
    input clk,
    input rst_n,
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input en,
    output [WIDTH:0] result
);


  (* use_carry_chain = "yes" *) wire [WIDTH:0] sum;
  assign sum = a + b;
  register_en #(
      .WIDTH(WIDTH + 1)
  ) SUM_R (
      .clk(clk),
      .rst_n(rst_n),
      .en(en),
      .D(sum),
      .Q(result)
  );


endmodule