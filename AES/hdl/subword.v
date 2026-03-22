module subword (
    input  wire [31:0] in,
    output wire [31:0] out
);
    sbox_lut u0 (.in(in[31:24]), .out(out[31:24]));
    sbox_lut u1 (.in(in[23:16]), .out(out[23:16]));
    sbox_lut u2 (.in(in[15:8]),  .out(out[15:8]));
    sbox_lut u3 (.in(in[7:0]),   .out(out[7:0]));
endmodule