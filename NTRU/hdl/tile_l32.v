// tile_l32: one 32x32 sign-select leaf (tile L32 in docs/tile_analysis.md).
//
// Registered inputs and output so that synthesis reports a reg-to-reg path.
// Latency: 2 clock cycles.
module tile_l32 #(
    parameter IMPL = "CORR"
) (
    input  wire        clk,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire        a_signed,
    input  wire        b_signed,
    output reg  [64:0] p
);

    reg  [31:0] a_r, b_r;
    reg         sa_r, sb_r;
    wire [64:0] p_w;

    always @(posedge clk) begin
        a_r  <= a;
        b_r  <= b;
        sa_r <= a_signed;
        sb_r <= b_signed;
        p    <= p_w;
    end

    mul_ss #(.W(32), .IMPL(IMPL)) u_leaf (
        .a(a_r), .b(b_r), .a_signed(sa_r), .b_signed(sb_r), .p(p_w)
    );

endmodule
