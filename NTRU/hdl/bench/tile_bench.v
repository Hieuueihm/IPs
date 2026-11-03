// Synthesis benchmark tops for the tile study (not part of the core).
// Each top is one configuration in docs/tile_analysis.md section 7.

// Baseline: plain unsigned 32x32, registered in/out.
module bench_u32 (
    input  wire        clk,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [63:0] p
);
    reg [31:0] a_r, b_r;
    always @(posedge clk) begin
        a_r <= a;
        b_r <= b;
        p   <= a_r * b_r;
    end
endmodule

// L32 sign-select, correction-term implementation.
module bench_l32_corr (
    input wire clk, input wire [31:0] a, input wire [31:0] b,
    input wire a_signed, input wire b_signed, output wire [64:0] p
);
    tile_l32 #(.IMPL("CORR")) u (.clk(clk), .a(a), .b(b),
        .a_signed(a_signed), .b_signed(b_signed), .p(p));
endmodule

// L32 via operand extension (= 33x33 signed-only leaf).
module bench_l32_ext (
    input wire clk, input wire [31:0] a, input wire [31:0] b,
    input wire a_signed, input wire b_signed, output wire [64:0] p
);
    tile_l32 #(.IMPL("EXT")) u (.clk(clk), .a(a), .b(b),
        .a_signed(a_signed), .b_signed(b_signed), .p(p));
endmodule

// 2x2 L16 sign-select, split + fuse.
module bench_l16_corr (
    input wire clk, input wire fuse, input wire [63:0] a_bus, input wire [63:0] b_bus,
    input wire [3:0] a_signed, input wire [3:0] b_signed, output wire [131:0] p
);
    tile_l16x4 #(.IMPL("CORR"), .FUSE_EN(1)) u (.clk(clk), .fuse(fuse),
        .a_bus(a_bus), .b_bus(b_bus), .a_signed(a_signed), .b_signed(b_signed), .p(p));
endmodule

// 2x2 leaves via operand extension (= 17x17 signed-only, tile L17), split + fuse.
module bench_l16_ext (
    input wire clk, input wire fuse, input wire [63:0] a_bus, input wire [63:0] b_bus,
    input wire [3:0] a_signed, input wire [3:0] b_signed, output wire [131:0] p
);
    tile_l16x4 #(.IMPL("EXT"), .FUSE_EN(1)) u (.clk(clk), .fuse(fuse),
        .a_bus(a_bus), .b_bus(b_bus), .a_signed(a_signed), .b_signed(b_signed), .p(p));
endmodule

// 2x2 L16 sign-select, split only (no fusion hardware): isolates fusion cost.
module bench_l16_split (
    input wire clk, input wire fuse, input wire [63:0] a_bus, input wire [63:0] b_bus,
    input wire [3:0] a_signed, input wire [3:0] b_signed, output wire [131:0] p
);
    tile_l16x4 #(.IMPL("CORR"), .FUSE_EN(0)) u (.clk(clk), .fuse(fuse),
        .a_bus(a_bus), .b_bus(b_bus), .a_signed(a_signed), .b_signed(b_signed), .p(p));
endmodule
