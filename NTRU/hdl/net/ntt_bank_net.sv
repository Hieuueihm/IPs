// ntt_bank_net: DRAFT of the bank -> tile network for the single-lane tile (spec 2.0, 03 sections 1, 4, 6).
// Written to measure what the network costs; not acceptance RTL. Address generation, the scheduler and
// the RAMs themselves are outside this block: it receives the registered read data of the 64 data banks
// and the 8 root-pack banks, plus the per-tile and per-bank selects computed by the controller.
//
// Read side, per tile and operand (x, y), one register stage:
//   lane 16: operand = bank[sel] (64:1 of 16 bits);
//   lane 32: operand = {bank[sel | 1], bank[sel & ~1]} (superbank sel >> 1).
//   Staggered read (spec 03 section 1): when hold_x is set, x is the value read for this tile one cycle
//   earlier and held here, so x and y can come from the same bank in two cycles.
// Root side, per tile: pack bank pb (8:1 of 96 bits), then one of its three roots (child 0, 1, 2).
// Write side, per bank: the result z_k of tile t (32:1 of 32 bits), low half for even banks and for
// lane 16, high half for odd banks in lane 32; one register stage.
module ntt_bank_net #(parameter integer TILES = 16, BANKS = 64, PBANKS = 8) (
    input  wire                     clk, en,
    input  wire                     lane32,
    // read data of the data banks and the root-pack banks
    input  wire [BANKS*16-1:0]      bank_rd,
    input  wire [PBANKS*96-1:0]     pack_rd,
    // per-tile read selects
    input  wire [TILES*6-1:0]       sel_x, sel_y,
    input  wire [TILES-1:0]         hold_x,
    input  wire [TILES*3-1:0]       sel_pb,
    input  wire [TILES*2-1:0]       sel_child,
    // operands to the tiles
    output reg  [TILES*32-1:0]      op_x, op_y, op_w,
    // results of the tiles and per-bank write selects
    input  wire [TILES*64-1:0]      tile_z,          // {z1, z0} of every tile
    input  wire [BANKS*5-1:0]       wsel,            // {tile, which result} per bank
    input  wire [BANKS-1:0]         wen,
    output reg  [BANKS*16-1:0]      bank_wd,
    output reg  [BANKS-1:0]         bank_we
);
    function [31:0] operand(input [BANKS*16-1:0] rd, input [5:0] s, input l32);
        reg [15:0] lo, hi;
        begin
            lo = rd[16*s +: 16];
            hi = rd[16*(s | 6'd1) +: 16];
            operand = l32 ? {hi, rd[16*(s & 6'h3e) +: 16]} : {16'd0, lo};
        end
    endfunction

    genvar t, b;
    generate for (t = 0; t < TILES; t = t + 1) begin : g_tile
        reg  [31:0] xh;                  // x read one cycle early (staggered read)
        wire [31:0] xn = operand(bank_rd, sel_x[6*t +: 6], lane32);
        wire [31:0] yn = operand(bank_rd, sel_y[6*t +: 6], lane32);
        wire [95:0] pk = pack_rd[96*sel_pb[3*t +: 3] +: 96];
        wire [31:0] wn = pk[32*sel_child[2*t +: 2] +: 32];
        always @(posedge clk)
            if (en) begin
                xh <= xn;
                op_x[32*t +: 32] <= hold_x[t] ? xh : xn;
                op_y[32*t +: 32] <= yn;
                op_w[32*t +: 32] <= wn;
            end
    end endgenerate

    generate for (b = 0; b < BANKS; b = b + 1) begin : g_bank
        wire [4:0]  s  = wsel[5*b +: 5];
        wire [31:0] z  = tile_z[32*s +: 32];
        wire [15:0] wd = (lane32 && (b % 2 == 1)) ? z[31:16] : z[15:0];
        always @(posedge clk)
            if (en) begin
                bank_wd[16*b +: 16] <= wd;
                bank_we[b] <= wen[b];
            end
    end endgenerate
endmodule
