// File: node.v
module node (
    input  [7:0] A,
    input  [7:0] B,
    output [7:0] min_o,
    output [7:0] max_o
);
  wire a_lt_b = (A < B) ? 1 : 0;
  assign min_o = (a_lt_b) ? A : B;

  assign max_o = (a_lt_b) ? B : A;

endmodule