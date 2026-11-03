// tile_l16x4: 2x2 array of 16x16 sign-select leaves (tile L16 in docs/tile_analysis.md).
//
// fuse = 0: four independent 16x16 products (lanes). Lane k uses
//           a_bus[16k+:16], b_bus[16k+:16], a_signed[k], b_signed[k];
//           result k in p[33k+:33].
// fuse = 1: one 32x32 product of a_bus[31:0] x b_bus[31:0]; the top limbs use
//           a_signed[0] / b_signed[0], the low limbs are unsigned;
//           result in p[64:0], upper bits zero.
//
// Lane-to-leaf mapping is chosen so that lanes 0 and 1 already carry the
// operands of leaves (0,0) and (1,1) in fused mode; only leaves (0,1) and
// (1,0) need operand muxes.
//   lane 0 -> leaf (a0,b0)   lane 1 -> leaf (a1,b1)
//   lane 2 -> leaf (a0,b1)   lane 3 -> leaf (a1,b0)
//
// FUSE_EN = 0 removes the fused path (split-only baseline).
// Registered inputs and output; latency 2 clock cycles.
module tile_l16x4 #(
    parameter         IMPL    = "CORR",
    parameter integer FUSE_EN = 1
) (
    input  wire         clk,
    input  wire         fuse,
    input  wire [63:0]  a_bus,
    input  wire [63:0]  b_bus,
    input  wire [3:0]   a_signed,
    input  wire [3:0]   b_signed,
    output reg  [131:0] p
);

    reg  [63:0] a_r, b_r;
    reg  [3:0]  sa_r, sb_r;
    reg         fuse_r;

    always @(posedge clk) begin
        a_r    <= a_bus;
        b_r    <= b_bus;
        sa_r   <= a_signed;
        sb_r   <= b_signed;
        fuse_r <= (FUSE_EN != 0) & fuse;
    end

    // Operands and sign modes per leaf.
    wire [15:0] la [0:3];
    wire [15:0] lb [0:3];
    wire [3:0]  lsa, lsb;

    assign la[0] = a_r[15:0];
    assign lb[0] = b_r[15:0];
    assign la[1] = a_r[31:16];
    assign lb[1] = b_r[31:16];
    assign la[2] = fuse_r ? a_r[15:0]  : a_r[47:32];
    assign lb[2] = fuse_r ? b_r[31:16] : b_r[47:32];
    assign la[3] = fuse_r ? a_r[31:16] : a_r[63:48];
    assign lb[3] = fuse_r ? b_r[15:0]  : b_r[63:48];

    assign lsa = fuse_r ? {sa_r[0], 1'b0, sa_r[0], 1'b0} : sa_r;
    assign lsb = fuse_r ? {1'b0, sb_r[0], sb_r[0], 1'b0} : sb_r;

    wire [32:0] lp [0:3];

    genvar k;
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_leaf
            mul_ss #(.W(16), .IMPL(IMPL)) u_leaf (
                .a(la[k]), .b(lb[k]), .a_signed(lsa[k]), .b_signed(lsb[k]), .p(lp[k])
            );
        end
    endgenerate

    // Fused result: p00 + (p01 + p10) * 2^16 + p11 * 2^32.
    wire [64:0] s00 = {{32{lp[0][32]}}, lp[0]};
    wire [64:0] s11 = {lp[1], 32'b0};
    wire [64:0] s01 = {{16{lp[2][32]}}, lp[2], 16'b0};
    wire [64:0] s10 = {{16{lp[3][32]}}, lp[3], 16'b0};
    wire [64:0] fused = s00 + s01 + s10 + s11;

    wire [131:0] split = {lp[3], lp[2], lp[1], lp[0]};

    always @(posedge clk) begin
        p <= fuse_r ? {67'b0, fused} : split;
    end

endmodule
