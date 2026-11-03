// mul_ss: W x W sign-select multiplier leaf (technology independent).
//
// Each operand is interpreted as signed or unsigned by a_signed / b_signed.
// The result is the exact (2W+1)-bit two's-complement product.
//
// IMPL = "CORR": unsigned W x W core plus sign-correction terms
//                a_s*b_s = a_u*b_u - sa*2^W*b_u - sb*2^W*a_u + sa*sb*2^2W
//                (no multiplier wider than W x W).
// IMPL = "EXT" : extend both operands to W+1 bits and use a signed
//                (W+1) x (W+1) multiplier, i.e. a signed-only leaf.
module mul_ss #(
    parameter integer W    = 32,
    parameter         IMPL = "CORR"
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         a_signed,
    input  wire         b_signed,
    output wire [2*W:0] p
);

    generate
        if (IMPL == "EXT") begin : g_ext
            wire signed [W:0]     ax   = {a_signed & a[W-1], a};
            wire signed [W:0]     bx   = {b_signed & b[W-1], b};
            wire signed [2*W+1:0] full = ax * bx;
            assign p = full[2*W:0];
        end else begin : g_corr
            wire           sa   = a_signed & a[W-1];
            wire           sb   = b_signed & b[W-1];
            wire [2*W-1:0] uu   = a * b;
            wire [W+1:0]   csum = {2'b00, (sa ? b : {W{1'b0}})}
                                + {2'b00, (sb ? a : {W{1'b0}})};
            wire [2*W+1:0] corr = {csum, {W{1'b0}}};
            wire [2*W+1:0] top  = {1'b0, sa & sb, {(2*W){1'b0}}};
            wire [2*W+1:0] full = {2'b00, uu} - corr + top;
            assign p = full[2*W:0];
        end
    endgenerate

endmodule
