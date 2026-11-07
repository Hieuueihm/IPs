// Tile of the A + constant-geometry core on XC7Z020 (module tile_a2), after the tile contract
// spec/FlexTransform/2.0/10_hop_dong_tile.md. Interleaved inputs; dense state; shared FFT product sequencer.
// Separate from the draft in hdl/tile_thu/; do not compile both together.
//
// One 32-bit NTT lane per tile, R = 2^32 for every odd q, 3 <= q < 2^31 (small q such as 3329 and
// 12289 included). Three modes, req_mode (2 bit, since 02/11/2026):
//   0 NTT: one butterfly, fixed operand slots x = d0, y = d1, w = r0;
//   1 FFT: one complex butterfly, 32 / 64 / 128 bit, 2L beats;
//   2 packed NTT: two 16-bit butterflies on two words of two coefficients, q < 2^15;
//   3 reserved, never accepted (req_ready = 0).
// The raw 32x32 product, the FFT 32-bit product and the single modmul of earlier versions were removed on 02/11/2026
// (the core never sends them); a single modmul is an NTT CT butterfly with x = 0 (z0 = Mont(y, w), z1 ignored).
// Internal names v5, r5, f5, rq_5, t5, sa5, sw5 belong to the FFT mode (its number before 02/11/2026).
//
// TREN_MANG = 1 (default): architecture v1 since 01/11/2026 (hypothesis 2 met at tile level with one
//   lane). Reduction on the array: the 4 leaves fused into one 32x32 multiplier, 3 passes (T, m, m*q)
//   issued FUSE cycles apart; a new modmul every 3 cycles, no DSP besides the 4 leaves.
// TREN_MANG = 3: dedicated reduction (hypothesis 2 baseline; v1 from 31/10 to 01/11/2026). The fused
//   leaves compute T, then one general 32-bit Montgomery (behavioral *), one modmul per cycle.
//
// LEAF_PD: pipeline registers of a leaf after its input register (default 2). Every engine latency
// below is derived from it, so changing the multiplier pipeline keeps the side data aligned.
// IN_REG = 1: one register stage on the accepted request before any datapath logic (latency + 1),
// for use inside the core where the request arrives through the bank -> tile network.
// EN_REG = 1: the datapath clock enable is a registered copy of en, so en reaches the datapath
// through one register and fans out locally. The datapath then moves one cycle after en falls and
// stays still one cycle after en rises; a one-entry skid holds a result made in that extra cycle,
// and a request is accepted only when en and its copy are both high. Ports behave as with
// EN_REG = 0 except that each stall costs one more cycle.
// PHASE (0..2, on-array only): reset value of the period-3 issue counter, so the tiles of a core can
// accept in different cycles (core: tile t uses t / 6, model/staggered_net.py). Ports are unchanged; the
// first accepting cycle after reset moves by PHASE.
//
// Butterfly: one modular add/sub unit, used before the engine for GS ((x + y, x - y) then
// Mont(x - y, w)) and after it for CT ((x + t, x - t) with t = Mont(y, w)). Mode and direction are
// fixed while the tile is busy (spec 10, 4.2), so the unit serves one place per stream.
//
// FFT mode (spec 10, 4.7; one engine for 32 / 64 / 128 bit since 01/11/2026): cfg_q[5:4] = 0 / 1 / 2 gives
// L = 1 / 2 / 4 limbs of 32 bit per value. A butterfly is 2L beats, limb by limb: (A.re, B.re, wr) of limb k, then
// (A.im, B.im, wi) of limb k (beat bit 0: imaginary). Its 2L results leave as the L limbs of the real part, then the L
// limbs of the imaginary part, each in the clock its T limb is made (inverse) or one clock later (forward). The tile keeps
// the limbs of up to 8 / 4 / 2 butterflies in small memories and reuses its own operations: the fused multiplier makes
// each W-bit product as 1 / 4 / 15 limb products, column by column into one product accumulator (rounding added in at
// the start; at 32 bit the rounded Q16.16 product); the add/sub with q = 0 makes A + B, A - B (inverse, at the input) and
// A + T, A - T (forward, at the output) with a carry between limbs; its two correction chains, idle in the FFT mode, make
// o.re + o.im and wr + wi; the Montgomery u - q chain makes p0 + p1, and one subtract chain p0 - p1 and p2 - (p0 + p1),
// all with a carry between limbs. One butterfly every 3 * (1 / 4 / 15) cycles. The tile does not scale: div2e of the
// last inverse FFT layer is applied by the core when the host reads the result, so cfg_shift is unused and req_sign is
// ignored in the FFT mode.
//
// Packed NTT mode (two 16-bit coefficients per 32-bit word, spec 10, 4.9; q < 2^15): one request is two coefficient
// butterflies, one per 16-bit lane, on the NTT engine: leaves 0 (lo x lo) and 1 (hi x hi) carry the two lanes,
// leaves 2 and 3 get 0, so the fused product is {lane B product, lane A product}; the add/sub, the reduction and the
// halving cut their carries at bit 16. Constants are per lane: cfg_q = {q, q}, cfg_qinv = {q', q'} with
// q' = -q^-1 mod 2^16. req_sign = 1 pairs the two coefficients inside each word (lanes (x.lo, x.hi), (y.lo, y.hi)),
// 0 the words (lanes (x.lo, y.lo), (x.hi, y.hi)). Same rate and latency as the NTT mode. Only with TREN_MANG = 1.
//
// Every register holds when en = 0. Latency is fixed for each mode and direction and does not depend on data
// (CT / FFT forward: one clock more than GS / FFT inverse). The handshake drives valid bits only, never an operand select.

// Fault hooks for the testbench self-check (11_kiem_thu_tile.md, group C). Never defined in a
// normal build. FAULT_NO_NZ / FAULT_NZ_ONE: carry bit [T_lo != 0] forced to 0 / 1;
// FAULT_NO_SUBQ: final conditional subtract of q in the reduction removed; FAULT_HALVE_ALWAYS:
// GS sum halved even when cfg_halve = 0; FAULT_SWAP_XY: butterfly operands x and y swapped;
// FAULT_IGNORE_SLOT: every request uses modulus slot 0; FAULT_NO_CARRY: no carry between the limbs of the FFT mode at
// 64 / 128 bit (add/sub, sums, T).
`ifdef FAULT_NO_NZ
`define TL_NZ(b) 1'b0
`elsif FAULT_NZ_ONE
`define TL_NZ(b) 1'b1
`else
`define TL_NZ(b) (b)
`endif
`ifdef FAULT_IGNORE_SLOT
`define TL_SLOT(s) 1'b0
`else
`define TL_SLOT(s) (s)
`endif
`ifdef FAULT_NO_CARRY
`define TL_CY(c) 1'b0
`else
`define TL_CY(c) (c)
`endif
`ifdef FAULT_NO_SUBQ
`define TL_GE(ge) 1'b0
`else
`define TL_GE(ge) (ge)            // ge: sign bit of u - q, so no separate comparator is built
`endif

// En-gated delay line, no reset (maps to SRL).
module tl_delay #(parameter integer W = 1, D = 1) (
    input  wire         clk, en,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [1:D];
    integer i;
    always @(posedge clk)
        if (en) begin
            r[1] <= d;
            for (i = 2; i <= D; i = i + 1) r[i] <= r[i-1];
        end
    assign q = r[D];
endmodule

// 2x2 array of 16x16 sign-select leaves: an input register and PD product registers per leaf, plus
// the two-stage fused 32x32 combine. Operands presented in cycle c: leaf k product in p[33k+:33] in
// cycle c + 1 + PD, exact 65-bit fused product of leaves 0..3 in f in cycle c + 3 + PD.
// Fused leaf map: 0 = lo*lo, 1 = hi*hi, 2 = lo(a)*hi(b), 3 = hi(a)*lo(b).
module tl_leaves #(parameter integer PD = 2) (
    input  wire         clk, en,
    input  wire         zh,                 // A operand of leaves 2 and 3 forced to 0 (packed NTT), on the leaf register
    input  wire [63:0]  a, b,
    input  wire [3:0]   sa, sb,
    output wire [131:0] p,
    output reg  [64:0]  f
);
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_leaf
        reg [15:0] ar, br;
        reg        sar, sbr;
        reg [32:0] pp [1:PD];
        wire [32:0] prod;
        integer s;
        mul_ss #(.W(16), .IMPL("EXT")) u_mul (.a(ar), .b(br), .a_signed(sar), .b_signed(sbr), .p(prod));
        always @(posedge clk)
            if (en) begin
                ar <= (k >= 2 && zh) ? 16'd0 : a[16*k+:16]; br <= b[16*k+:16]; sar <= sa[k]; sbr <= sb[k];
                pp[1] <= prod;
                for (s = 2; s <= PD; s = s + 1) pp[s] <= pp[s-1];
            end
        assign p[33*k+:33] = pp[PD];
    end endgenerate

    // The two cross products are added into the fused result in one three-input add.
    reg [32:0] p2r, p3r;
    reg [64:0] cat;
    always @(posedge clk)
        if (en) begin
            p2r <= p[2*33+:33];
            p3r <= p[3*33+:33];
            cat <= {p[1*33+:33], p[0+:32]};
            f   <= cat + {{16{p2r[32]}}, p2r, 16'b0} + {{16{p3r[32]}}, p3r, 16'b0};
        end
endmodule

// Modular add and subtract in two clocks, a, b in [0, q): s = a + b mod q, d = a - b mod q.
// First clock: a + b + ci and a - b - bi, registered (co / bo leave in this clock, for the limb chains of the FFT mode,
// only with q = 0). Second clock: the corrections a + b - q and a - b + q from the registers, one chain each, and the
// selection; s and d belong to the inputs of the previous clock.
// split = 1 (packed NTT mode): two independent W/2-bit lanes, q = {q_hi, q_lo}, values below 2^(W/2 - 1). Every chain is
// one continuous chain with a guard bit at W/2: it propagates when split = 0; when split = 1 it cuts the low lane, whose
// carry lands in the guard bit, and gives the high lane its own +1 where a subtraction needs it.
// The FFT mode (plain) needs no correction, so the two correction chains make the FFT sums instead: fs = fa + fb + fci and
// ws = wa + wb + wci (W + 1 bits, from the caller's registers). Each chain picks its operands by plain; the select fits in
// the chain's LUTs (two sources per operand).
module tl_addsub #(parameter integer W = 32) (
    input  wire         clk, ce,
    input  wire [W-1:0] a, b, q,
    input  wire         ci, bi, split, plain,
    output wire [W-1:0] s, d,
    output wire         co, bo,
    input  wire [W-1:0] fa, fb, wa, wb,
    input  wire         fci, wci,
    output wire [W:0]   fs, ws
);
    localparam integer H = W / 2;
    wire [W:0]   sum = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, ci};
    wire [W+1:0] dif = {1'b0, a[W-1:H], 1'b1, a[H-1:0]} + {1'b0, ~b[W-1:H], split, ~b[H-1:0]} + {{(W+1){1'b0}}, !bi};
    assign co = sum[W];
    assign bo = !dif[W+1];
    reg [W:0]   sum_r;
    reg [W+1:0] dif_r;
    reg [W-1:0] q_r;
    reg         split_r, plain_r;
    always @(posedge clk)
        if (ce) begin sum_r <= sum; dif_r <= dif; q_r <= q; split_r <= split; plain_r <= plain; end
    // a + b - q (sum + ~q + 1): non-negative when the carry out is set; FFT: fa + fb + fci (guard bit propagates)
    wire [W+2:0] sq = (plain_r ? {2'b0, fa[W-1:H], 1'b1, fa[H-1:0]} : {1'b0, sum_r[W:H], 1'b1, sum_r[H-1:0]}) +
                      (plain_r ? {2'b0, fb[W-1:H], 1'b0, fb[H-1:0]} : {1'b0, ~{1'b0, q_r[W-1:H]}, split_r, ~q_r[H-1:0]}) +
                      {{(W+2){1'b0}}, plain_r ? fci : 1'b1};
    // a - b + q; FFT: wa + wb + wci
    wire [W+1:0] dq = (plain_r ? {1'b0, wa[W-1:H], 1'b1, wa[H-1:0]} : {1'b0, dif_r[W:H+1], !split_r, dif_r[H-1:0]}) +
                      (plain_r ? {1'b0, wb[W-1:H], 1'b0, wb[H-1:0]} : {1'b0, q_r[W-1:H], 1'b0, q_r[H-1:0]}) +
                      {{(W+1){1'b0}}, plain_r && wci};
    assign fs = {sq[W+1], sq[W:H+1], sq[H-1:0]};
    assign ws = {dq[W+1], dq[W:H+1], dq[H-1:0]};
`ifndef SYNTHESIS
    // shadow: the separate chains before a_cg_z020_share
    wire [W+2:0] sq_ref = {1'b0, sum_r[W:H], 1'b1, sum_r[H-1:0]} + {1'b0, ~{1'b0, q_r[W-1:H]}, split_r, ~q_r[H-1:0]} +
                          {{(W+2){1'b0}}, 1'b1};
    wire [W+1:0] dq_ref = {1'b0, dif_r[W:H+1], !split_r, dif_r[H-1:0]} + {1'b0, q_r[W-1:H], 1'b0, q_r[H-1:0]};
    always @(posedge clk)
        if (ce && plain_r === 1'b0 && (^{sum_r, dif_r, q_r, split_r}) !== 1'bx && (sq !== sq_ref || dq !== dq_ref))
            $fatal(1, "fused correction chain differs");
`endif
    wire         sneg_h = !sq[W+2];
    wire         sneg_l = split_r ? !sq[H] : sneg_h;
    wire         dneg_h = !dif_r[W+1];
    wire         dneg_l = split_r ? !dif_r[H] : dneg_h;
    wire [W-1:0] modular_s = {sneg_h ? sum_r[W-1:H] : sq[W:H+1], sneg_l ? sum_r[H-1:0] : sq[H-1:0]};
    wire [W-1:0] modular_d = {dneg_h ? dq[W:H+1] : dif_r[W:H+1], dneg_l ? dq[H-1:0] : dif_r[H-1:0]};
    // FFT selects the exact raw sum/difference, before q correction.
    assign s = plain_r ? sum_r[W-1:0] : modular_s;
    assign d = plain_r ? {dif_r[W:H+1], dif_r[H-1:0]} : modular_d;
endmodule

`ifdef TL_LEAF_PD
`define TL_LEAF_PD_DEFAULT `TL_LEAF_PD
`else
`define TL_LEAF_PD_DEFAULT 2
`endif
`ifdef TL_IN_REG
`define TL_IN_REG_DEFAULT `TL_IN_REG
`else
`define TL_IN_REG_DEFAULT 0
`endif
`ifdef TL_EN_REG
`define TL_EN_REG_DEFAULT `TL_EN_REG
`else
`define TL_EN_REG_DEFAULT 0
`endif
`ifdef TL_PHASE
`define TL_PHASE_DEFAULT `TL_PHASE
`else
`define TL_PHASE_DEFAULT 0
`endif

module tile_a2 #(parameter integer TREN_MANG = 1,
                  parameter integer LEAF_PD   = `TL_LEAF_PD_DEFAULT,
                  parameter integer IN_REG    = `TL_IN_REG_DEFAULT,
                  parameter integer EN_REG    = `TL_EN_REG_DEFAULT,
                  parameter integer PHASE     = `TL_PHASE_DEFAULT) (
    input  wire         clk, rst, en,
    output wire         idle,
    input  wire         cfg_we, cfg_slot,
    input wire cfg_ntrugen,
    input wire [1:0] cfg_fmt,
    input wire [3:0] cfg_shift,
    input wire ext_fft_valid,            // product program, one clock ahead of use (registered here), decoded by the core:
    input wire [1:0] ext_fft_mpr,        //   product (p0, p1, p2)
    input wire [2:0] ext_fft_ka, ext_fft_kb,   // limb of the A / B limb memory (p1: imaginary beats, L further)
    input wire [1:0] ext_fft_sa, ext_fft_sb,   // limb of the A / B sum memory (p2)
    input wire [1:0] ext_fft_sgn,        //   top limb, signed: {B, A}
    input wire [3:0] ext_fft_col,        //   {last step of its column, column emitted, emitted limb}
    input wire ext_fft_first,            //   first step of a product
    input wire ext_fft_last,             //   last step of p2
    input  wire [31:0]  cfg_q, cfg_qinv,
    input  wire         cfg_floor, cfg_halve,
    input  wire         req_valid,
    output wire         req_ready,
    input  wire [1:0]   req_mode,
    input  wire         req_dir,
    input  wire         req_slot,
    input  wire         req_sign,
    input  wire [63:0]  req_data,
    input  wire [31:0]  req_root,
    input  wire [7:0]   req_tag,
    output wire         rsp_valid,
    output wire [63:0]  rsp_data,
    output wire [7:0]   rsp_tag
);
    localparam [0:0] ARR32  = (TREN_MANG == 1);            // reduction on the fused leaves
    localparam [0:0] INREG  = (IN_REG == 1);
    localparam [0:0] ENREG  = (EN_REG == 1);
    localparam [1:0] PH0    = PHASE;                     // reset value of the issue counter
    // req_mode (spec 10, 4.2): NTT butterfly, FFT butterfly (32 / 64 / 128 bit), NTT butterfly pair on 16-bit lanes
    localparam [1:0] MD_NTT = 2'd0, MD_FFT = 2'd1, MD_NTT16 = 2'd2;
    // Cycles from operands presented to the leaves to the product: one leaf, the fused 32x32.
    localparam integer LEAF = 1 + LEAF_PD;
    localparam integer FUSE = LEAF + 2;
    // Dedicated Montgomery: registers from the fused T to m*q (ma, mp1, mp2, mq1, mq2, mq3).
    localparam integer DED  = 6;
    // Cycles from the operand stage to the engine result: three fused passes (on the array) or T plus
    // the dedicated chain, then u and the result.
    localparam integer E32  = ARR32 ? 3 * FUSE + 2 : FUSE + DED + 2;

    generate if (TREN_MANG != 1 && TREN_MANG != 3) begin : g_bad_param
        tl_tren_mang_must_be_1_or_3 u_stop ();      // elaboration error on purpose
    end endgenerate
    // On the array, passes at 0, FUSE, 2*FUSE must fall on different phases of the 3-cycle slot.
    generate if (ARR32 && (FUSE % 3 == 0)) begin : g_bad_fuse
        tl_fuse_latency_must_not_be_a_multiple_of_3 u_stop ();
    end endgenerate
    generate if (LEAF_PD < 1 || (IN_REG != 0 && IN_REG != 1) || (EN_REG != 0 && EN_REG != 1) || PHASE < 0 || PHASE > 2) begin : g_bad_pipe
        tl_leaf_pd_or_in_reg_out_of_range u_stop ();
    end endgenerate

    // ---------------- constants register ----------------
    // Two modulus slots (q, q'); cfg_slot picks the slot written, req_slot the slot an NTT request uses.
    // The slot bit travels with the request, and every stage that needs q or q' selects by it.
    reg native_r;
    reg [1:0] fmt_r;
    reg        floor_r, halve_r;
    reg [31:0] q0, q1, qi0, qi1;
    assign idle = 1'b1;
    always @(posedge clk)
        if (rst) begin
            native_r <= 0; fmt_r <= 0; floor_r <= 1'b0; halve_r <= 1'b0;
            q0 <= 32'd0; q1 <= 32'd0; qi0 <= 32'd0; qi1 <= 32'd0;
        end else if (en && cfg_we && idle) begin
            native_r <= cfg_ntrugen; fmt_r <= cfg_fmt; floor_r <= cfg_floor; halve_r <= cfg_halve;
            if (cfg_slot) begin q1 <= cfg_q; qi1 <= cfg_qinv; end
            else          begin q0 <= cfg_q; qi0 <= cfg_qinv; end
        end
    // (selected inline, not through a function: a continuous assignment through a function that reads
    // q0/q1 directly would not be re-evaluated in simulation when only q0/q1 change)

    // Clock enable of the datapath: en, or its registered copy (EN_REG). The constants, the mode
    // latch, acceptance and the in-flight count stay on en.
    wire ce;
    generate if (ENREG) begin : g_en_reg
        reg en_r;
        always @(posedge clk) en_r <= !rst && en;
        assign ce = en_r;
    end else begin : g_en_wire
        assign ce = en;
    end endgenerate

    // ---------------- request side ----------------
    // Mode and direction follow the request while idle and freeze while busy. A request whose
    // mode or direction differs from the latched value waits (spec 10, 4.2).
    reg  [1:0] md;
    reg        dir, mf;                       // mf: FFT mode, kept as its own register (it steers the add/sub's q)
    always @(posedge clk)
        if (rst) begin md <= MD_NTT; dir <= 1'b0; mf <= 1'b0; end
        else if (en && cfg_we) begin md <= req_mode; dir <= req_dir; mf <= (req_mode == MD_FFT); end
    wire same = (req_mode == md) && (req_dir == dir);
    wire mp   = (md == MD_NTT16);                  // packed NTT mode: the NTT mode on two 16-bit lanes
    wire ntt  = (md == MD_NTT) || (mp && ARR32);   // packed mode only on the array (two lanes of its reduction)
    // FFT width (constants slot 0, bits 5:4): 0 = 32 bit (L = 1 limb), 1 = 64 bit (L = 2), 2 = 128 bit (L = 4)
    wire       l1   = (fmt_r == 2'd0);
    wire       w4   = fmt_r[1];
    wire [2:0] wL   = w4 ? 3'd4 : l1 ? 3'd1 : 3'd2;
    wire [2:0] wB   = w4 ? 3'd7 : l1 ? 3'd1 : 3'd3;     // last beat of a butterfly, 2L - 1
    // FFT: the core sends a butterfly only while one of the limb buffers is free (wnb: butterflies holding one; checked
    // in simulation). The limb memories have 16 entries: 8 buffers of 2 beats at 32 bit (its latency needs more than 4
    // for one butterfly every 3 cycles), 4 of 4 beats at 64 bit, 2 of 8 beats at 128 bit.
    reg  [2:0] wbf;                                 // beat of the butterfly being accepted
    reg  [3:0] wnb;                                 // buffers in use
    wire       wrel;                                // the last result of a butterfly leaves: its buffer is free
    // memory address of beat (or limb) k of buffer b: 2L entries per buffer
    function [3:0] wadr(input f4, input f1, input [2:0] b, input [2:0] k);
        wadr = f4 ? {b[0], k} : f1 ? {b, k[0]} : {b[1:0], k[1:0]};
    endfunction
    function [2:0] sadr(input f4, input f1, input [2:0] b, input [1:0] k);
        sadr = f4 ? {b[0], k} : f1 ? b : {b[1:0], k[0]};
    endfunction
    function [2:0] wnext(input f4, input f1, input [2:0] b);
        wnext = f4 ? {2'b0, ~b[0]} : f1 ? b + 3'd1 : {1'b0, b[1:0] + 2'd1};
    endfunction

    // Issue slot of the on-array engine (period 3); always open with the dedicated engine.
    reg [1:0] ph;
    always @(posedge clk)
        if (rst) ph <= ARR32 ? PH0 : 2'd0;
        else if (ce) ph <= (!ARR32 || ph == 2'd2) ? 2'd0 : ph + 2'd1;

    assign req_ready = same && (!ENREG || ce) && ((ntt && ph == 2'd0) || mf);
    wire fire = en && req_valid && req_ready;
    always @(posedge clk)
        if (rst) begin wbf <= 3'd0; wnb <= 4'd0; end
        else begin
            if (fire && mf) wbf <= (wbf == wB) ? 3'd0 : wbf + 3'd1;
            wnb <= wnb + {3'd0, fire && mf && wbf == 3'd0} - {3'd0, wrel};
        end
    wire f5   = fire && mf;
`ifndef SYNTHESIS
    always @(posedge clk) if(!rst && fire && mf && wbf==0)
        if(wnb>=(w4 ? 2 : l1 ? 8 : 4))$fatal(1,"scheduled FFT buffer overflow");
`endif

    // Request as the datapath sees it: the ports, or one register stage after acceptance (IN_REG).
    wire        rq_ntt, rq_slot, rq_5;
    wire [63:0] rq_data;
    wire [31:0] rq_root;
    wire [7:0]  rq_tag;
    wire        rq_sign;
    generate if (INREG) begin : g_in_reg
        reg        rn, rslot, r5;
        reg [63:0] rdat;
        reg [31:0] rroot;
        reg [7:0]  rtag;
        (* DONT_TOUCH="yes" *) reg rsign; // Preserve the local sign-control sink.
        // NTRUGen inverse: A + 1, carried limb to limb (one carry per real / imaginary row), made before this register so
        // the increment does not sit in front of the add/sub. wbf is the accepted beat.
        reg  [1:0]  native_acc_carry;
        wire        native_bias = native_r && mf && dir;
        wire [32:0] native_acc_inc = {1'b0, req_data[31:0]} + {32'd0, (wbf[2:1] == 2'd0) || native_acc_carry[wbf[0]]};
        always @(posedge clk) begin
            if (rst) begin rn <= 1'b0; r5 <= 1'b0; end
            else if (ce) begin rn <= fire && ntt; r5 <= f5; end
            if (ce) begin
                rdat <= {req_data[63:32], native_bias ? native_acc_inc[31:0] : req_data[31:0]};
                rroot <= req_root; rtag <= req_tag; rsign <= req_sign; rslot <= `TL_SLOT(req_slot);
            end
            if (f5 && native_bias) native_acc_carry[wbf[0]] <= native_acc_inc[32];
        end
        assign rq_ntt = rn;  assign rq_data = rdat;  assign rq_slot = rslot;
        assign rq_5 = r5;
        assign rq_root = rroot;  assign rq_tag = rtag;  assign rq_sign = rsign;
    end else begin : g_in_wire
        assign rq_ntt = fire && ntt;  assign rq_data = req_data;  assign rq_slot = `TL_SLOT(req_slot);
        assign rq_5 = f5;
        assign rq_root = req_root;  assign rq_tag = req_tag;  assign rq_sign = req_sign;
    end endgenerate

    // ---------------- butterfly: operand stage ----------------
    // packed NTT, pairing inside a word (req_sign = 1): lanes (x.lo, x.hi), (y.lo, y.hi) -> words {y.lo, x.lo}, {y.hi, x.hi}
    wire        sw6 = mp && rq_sign;
    wire [31:0] d0 = sw6 ? {rq_data[47:32], rq_data[15:0]} : rq_data[31:0];
    wire [31:0] d1 = sw6 ? {rq_data[63:48], rq_data[31:16]} : rq_data[63:32];
`ifdef FAULT_SWAP_XY
    wire [31:0] xin = d1, yin = d0;
`else
    wire [31:0] xin = d0, yin = d1;
`endif
    wire [31:0] side_t, t;          // side data and engine result at the post stage
    wire        slot_t;             // modulus slot at the post stage
    wire [31:0] us, ud;
    wire [31:0] biased_x;
    wire        as_co, as_bo, as_ci, as_bi;
    // the add/sub (u_as) is instantiated below the FFT sums, whose operands it also takes

    // mf: beat and buffer of the request at the datapath input (after IN_REG), its limb; the inverse A + B, A - B
    // chains carry from limb to limb at the input, the forward A + T, A - T chains at the output (wte: output limb)
    reg  [2:0] wbi;
    reg  [2:0] wbn;
    reg [1:0] wic, wib;
    reg wfc, wfb;
    wire [1:0] wte;
    wire       wte0 = (wte != 2'd0);
    wire [2:0] wki  = {1'b0, wbi[2:1]};
    // Increment A once: (A+1)+B and (A+1)-B give exactly the
    // rounded GS branches modulo 2^64, before their arithmetic right shift.
    generate if (INREG) begin : g_bias_reg
        assign biased_x = xin;                    // rdat already holds A + 1 (g_in_reg)
    end else begin : g_bias_wire
        reg [1:0] native_xcarry;
        wire [32:0] native_xinc={1'b0,xin}+{32'd0,(wki==0)||native_xcarry[wbi[0]]};
        assign biased_x=(native_r && mf && dir) ? native_xinc[31:0] : xin;
        always @(posedge clk)
            if(ce && rq_5 && native_r && dir)native_xcarry[wbi[0]]<=native_xinc[32];
    end endgenerate
    always @(posedge clk) begin
        if (rst) begin wbi <= 3'd0; wbn <= 3'd0; end
        else if (ce && rq_5 && mf) begin
            wbi <= (wbi == wB) ? 3'd0 : wbi + 3'd1;
            if (wbi == wB) wbn <= wnext(w4, l1, wbn);
        end
        if (ce && rq_5) begin wic[wbi[0]] <= as_co; wib[wbi[0]] <= as_bo; end
    end
    // One more request register: every request reaches the operand stage one clock later, in every mode and direction,
    // with the add/sub's second clock. The add/sub's first clock, the limb counters and the limb carries
    // still work on rq_* / wbi.
    reg        rqd_ntt, rqd_5, rqd_slot, rqd_sign;
    reg [31:0] rqd_root, rqd_x, rqd_y;
    reg [7:0]  rqd_tag;
    reg [2:0]  wbi_d, wbn_d;
    always @(posedge clk) begin
        if (rst) begin rqd_ntt <= 1'b0; rqd_5 <= 1'b0; end
        else if (ce) begin rqd_ntt <= rq_ntt; rqd_5 <= rq_5; end
        if (ce) begin
            rqd_slot <= rq_slot; rqd_sign <= rq_sign; rqd_root <= rq_root; rqd_tag <= rq_tag;
            rqd_x <= xin; rqd_y <= yin; wbi_d <= wbi; wbn_d <= wbn;
        end
    end
    assign as_ci = `TL_CY(mf && (dir ? (wki != 3'd0) && wic[wbi[0]] : wte0 && wfc));
    assign as_bi = `TL_CY(mf && (dir ? (wki != 3'd0) && wib[wbi[0]] : wte0 && wfb));

    // Native NTRUGen inverse: wrap64(v+1) >>> 1 on BOTH GS
    // branches before the multiply. Reuse u_as and its interleaved carries.
    wire nh = native_r && mf && dir;
    reg v1,v5,sc1;
    reg [31:0] a1,w1,s1;
    reg [7:0] g1;
    reg [2:0] wb1,wn1;
    // The operand registers already hold each low input for one clock.
    // One delay register reuses them, replacing four indexed tiny memories.
    reg [103:0] nlo_delay;
    wire [31:0] nslo=nlo_delay[103:72],ndlo=nlo_delay[71:40];
    wire [31:0] nshi=us,ndhi=ud;
    reg [1:0] nhv;
    reg [109:0] nhp0, nhp1;
    wire nlow = rqd_5 && wbi_d[1];
    // inputs of the operand registers w1, wb1, wn1, v5 (nhp1 = {wn1, wb1, g1, w1, s1, a1}); the root memory wmw is written
    // from them at the edge that loads the registers
    wire        nlo_sel = nh && nlow;
    wire        nhp_sel = nh && !nlow && nhv[1];
    wire [31:0] w1_n  = nlo_sel ? nlo_delay[39:8] : nhp_sel ? nhp1[95:64] : rqd_root;
    wire [2:0]  wb1_n = nlo_sel ? wbi_d - 3'd2 : nhp_sel ? nhp1[106:104] : wbi_d;
    wire [2:0]  wn1_n = nhp_sel ? nhp1[109:107] : wbn_d;
    wire        v5_n  = nh ? (nlow || nhv[1]) : rqd_5;
    always @(posedge clk) begin
        if (rst) nhv<=0;
        else if(ce) nhv<={nhv[0],nh && nlow};
        if(ce) begin
            nhp1<=nhp0;
            nlo_delay<={s1,a1,w1,g1};
            if(nh && nlow)
                nhp0<={wbn_d,wbi_d,rqd_tag,rqd_root,{nshi[31],nshi[31:1]},{ndhi[31],ndhi[31:1]}};
        end
    end
    always @(posedge clk) begin
        if(rst) begin v1<=0;v5<=0;end
        else if(ce) begin v1<=rqd_ntt;v5<=v5_n;end
        if(ce) begin
            wb1<=wb1_n;wn1<=wn1_n;w1<=w1_n;
            a1<=dir ? ud : rqd_y;s1<=dir ? us : rqd_x;
            g1<=rqd_tag;sc1<=rqd_sign;
            if(nh) begin
                sc1<=0;
                if(nlow) begin
                    a1<={ndhi[0],ndlo[31:1]};s1<={nshi[0],nslo[31:1]};
                    g1<=nlo_delay[7:0];
                end else if(nhv[1]) begin
                    g1<=nhp1[103:96]; s1<=nhp1[63:32]; a1<=nhp1[31:0];
                end
            end
        end
    end

    // Modulus slot of the operation, ks[n] = slot of the operation n cycles after the operand stage.
    reg [E32:0] ks;
    always @(posedge clk)
        if (ce) ks <= {ks[E32-1:0], rqd_slot};

    // Valid waits for the engine. The side data (x or x + y, tag, slot, packed pairing) waits in the FFT side
    // memory wma: written at the operand stage, read in order one cycle before the result (nwa / nra: ring addresses;
    // at most E32 operations in flight, below 16).
    reg [E32:1]   vd;
    reg  [3:0]    nwa, nra;
    always @(posedge clk) begin
        if (rst) begin vd <= {E32{1'b0}}; nwa <= 4'd0; nra <= 4'd0; end
        else if (ce) begin
            vd <= {vd[E32-1:1], v1};
            if (v1) nwa <= nwa + 4'd1;
            if (vd[E32-1]) nra <= nra + 4'd1;
        end
    end
    wire        wtv;                    // FFT: a T limb (and its A-side limb) this cycle
    wire [41:0] wav;                    // side memory read: {slot, scale flag or pairing, tag, A-side value}
    wire        tv  = mf ? wtv : vd[E32];
    assign side_t = wav[31:0];
    wire [7:0]  tag_t = wav[39:32];
    assign slot_t = wav[41];

    // ---------------- multiplier leaves and modmul engine ----------------
    reg  [63:0]  la, lb;
    reg  [3:0]   lsa, lsb;
    wire [64:0]  lf;
    tl_leaves #(.PD(LEAF_PD)) leaves (.clk(clk), .en(ce), .zh(mp), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(), .f(lf));

    wire [31:0] A32, B32, r32;
    reg  [31:0] sa5, sw5;
    // mf: limb memories, buffers of 2L beats / L limbs, address {buffer, beat or limb}; small LUT memories (a block
    // RAM's slow clock-to-out would sit on the output path)
    (* ram_style = "distributed" *) reg  [41:0] wma  [0:15];    // A (forward) or A + B (inverse), tag, scale flag; per beat
                                                                // (NTT: x or x + y, tag, pairing, slot; per operation)
    (* ram_style = "distributed" *) reg  [31:0] wmx  [0:15];    // o: B (forward) or A - B (inverse); per beat
    (* ram_style = "distributed" *) reg  [31:0] wmw  [0:15];    // root; per beat (NTT: the operation's root, entry 0)
    (* ram_style = "distributed" *) reg  [31:0] wmsx [0:7];    // o.re + o.im; per limb
    (* ram_style = "distributed" *) reg  [31:0] wmsw [0:7];    // wr + wi; per limb
    wire       wim1 = wb1[0];                              // imaginary beat at the operand stage
    wire [2:0] wk1  = {1'b0, wb1[2:1]};
    reg        wcs, wcw, wsv;
    reg [2:0] wsa;
    reg [31:0] prev_real, prev_wr;
    wire [2:0] wsem1 = wim1 ? wk1 + wL : wk1;
    wire [2:0] wsem1_n = wb1_n[0] ? {1'b0, wb1_n[2:1]} + wL : {1'b0, wb1_n[2:1]};
    always @(posedge clk) if (ce && v5 && mf && !wim1) begin prev_real <= a1; prev_wr <= w1; end
    // the two sums: a limb of o.re + o.im, wr + wi with the carry of the limb below, made by the add/sub's correction chains
    wire        wcz = `TL_CY(wk1 != 3'd0);
    wire [32:0] sao, swo;
    // FFT: q = 0, so the modular add/sub is the plain 32-bit wrap add/sub
    // two clocks: us / ud come one clock after these inputs (GS / FFT inverse: at the delayed request; NTT CT and FFT
    // forward: one clock after the result, see the output stage); as_co / as_bo in the same clock
    tl_addsub #(.W(32)) u_as (.clk(clk), .ce(ce),
        .a(dir ? biased_x : side_t), .b(dir ? yin : t),
        .q((dir ? rq_slot : slot_t) ? q1 : q0), .ci(as_ci), .bi(as_bi), .split(mp), .plain(mf), .s(us), .d(ud),
        .co(as_co), .bo(as_bo),
        .fa(prev_real), .fb(a1), .fci(wcz && wcs), .wa(prev_wr), .wb(w1), .wci(wcz && wcw), .fs(sao), .ws(swo));
`ifndef SYNTHESIS
    always @(posedge clk)
        if (!rst && ce && v5 && mf && wim1 && (sao !== {1'b0, prev_real} + {1'b0, a1} + {32'd0, wcz && wcs} ||
                                               swo !== {1'b0, prev_wr} + {1'b0, w1} + {32'd0, wcz && wcw}))
            $fatal(1, "FFT sums on the correction chains differ");
`endif
    always @(posedge clk) begin
        if (ce && v5 && wim1) begin sa5 <= sao[31:0]; sw5 <= swo[31:0]; end
        if (ce && (mf ? v5 : v1)) wma[mf ? wadr(w4, l1, wn1, wsem1) : nwa] <= {ks[0], sc1, g1, s1};
        if (ce && v5 && mf) wmx[wadr(w4, l1, wn1, wsem1)] <= a1;
        // root memory: written at the edge that loads w1 (FFT: the beat's root; NTT: the operation's root, entry 0)
        if (ce && (mf ? v5_n : rqd_ntt)) wmw[mf ? wadr(w4, l1, wn1_n, wsem1_n) : 4'd0] <= w1_n;
        if (rst) wsv <= 1'b0;
        else if (ce) wsv <= v5 && mf && wim1;
        if (ce && v5 && mf && wim1) begin wcs <= sao[32]; wcw <= swo[32]; wsa <= sadr(w4, l1, wn1, wk1[1:0]); end
        if (ce && wsv) begin wmsx[wsa] <= sa5; wmsw[wsa] <= sw5; end
    end

    // FFT products: p0 = o.re * wr, p1 = o.im * wi, p2 = (o.re + o.im) * (wr + wi), each as limb products column by
    // column (product scanning; top limb signed). The core decodes the program once for all tiles and sends it one clock
    // early (ext_fft_*); it is registered here, so the program reaches the leaves from a local register, and the limb
    // memory addresses of the next clock are made from the early program and this tile's buffer index.
    reg       mbz, mfirst, mlast;
    reg [1:0] mpr, msg;
    reg [3:0] mcol;
    always @(posedge clk)
        if (rst) begin mbz <= 1'b0; mpr <= 2'd0; msg <= 2'd0; mcol <= 4'd0; mfirst <= 1'b0; mlast <= 1'b0; end
        else if (ce) begin
            mbz <= ext_fft_valid; mpr <= ext_fft_mpr; msg <= ext_fft_sgn; mcol <= ext_fft_col;
            mfirst <= ext_fft_first; mlast <= ext_fft_last;
        end
    reg [2:0] mbn;
    wire mend = mbz && mlast;
    always @(posedge clk)
        if (rst) mbn <= 0;
        else if (ce && mend) mbn <= wnext(w4, l1, mbn);
    // next clock's limb memory addresses, from the early program and the buffer index the next clock will use
    wire [2:0]  mbn_n  = mend ? wnext(w4, l1, mbn) : mbn;
    reg  [3:0]  mxa, mwa;
    reg  [2:0]  msxa, mswa;
    reg         msum;
    always @(posedge clk)
        if (ce) begin
            mxa  <= wadr(w4, l1, mbn_n, ext_fft_ka);  msxa <= sadr(w4, l1, mbn_n, ext_fft_sa);
            mwa  <= mf ? wadr(w4, l1, mbn_n, ext_fft_kb) : 4'd0;  mswa <= sadr(w4, l1, mbn_n, ext_fft_sb);
            msum <= (ext_fft_mpr == 2'd2);
        end
    wire [31:0] mopa = msum ? wmsx[msxa] : wmx[mxa];
    wire [31:0] mopb = msum ? wmsw[mswa] : wmw[mwa];
    wire        msa  = msg[0];                     // top limb: signed
    wire        msb  = msg[1];
    // forward declarations for the fused chain below (assigned in the accumulator and T stages)
    reg         wpv;
    wire [31:0] wpr;
    wire        wpc;
    reg         wtc1;
    reg  [31:0] wpl;
    reg  [1:0]  wpp, wpe;
    wire [32:0] wts;                               // FFT p0 + p1 (T stage)
    generate if (ARR32) begin : g_arr32
        // On the fused leaves: T at +0, m = T_lo*q' at +FUSE, m*q at +2*FUSE (three different
        // residues mod 3, so ops issued 3 cycles apart never collide); result at +3*FUSE+2 = E32.
        reg  [2*FUSE:1] vs;
        // packed NTT: lf = {lane B product, lane A product}; low / high halves of each lane regrouped as {B, A}
        wire [31:0] lfl = mp ? {lf[47:32], lf[15:0]} : lf[31:0];     // T_lo (then m) of the next pass
        wire [31:0] lfh = mp ? {lf[63:48], lf[31:16]} : lf[63:32];   // T_hi, (m q)_hi
        wire [1:0]  lnz = mp ? {|lf[47:32], |lf[15:0]} : {1'b0, |lf[31:0]};
        reg  [32:0] u32;
        wire [31:0] q32r = ((ks[E32-1]) ? q1 : q0);
        // u - q as one chain with a guard bit at 16 (propagate; packed: cut the low lane, whose no-borrow lands in the guard
        // bit, and give the high lane its own +1). In the FFT mode the same chain makes p0 + p1 of the T stage (wts).
        wire [34:0] uq = (mf ? {2'b0, wpr[31:16], 1'b1, wpr[15:0]} : {1'b0, u32[32:16], 1'b1, u32[15:0]}) +
                         (mf ? {2'b0, wpl[31:16], 1'b0, wpl[15:0]} : {1'b0, ~{1'b0, q32r[31:16]}, mp, ~q32r[15:0]}) +
                         {34'd0, mf ? wpc && wtc1 : 1'b1};
        wire        uq_ge_h = uq[34];
        wire        uq_ge_l = mp ? uq[16] : uq[34];
        assign wts = {uq[33], uq[32:17], uq[15:0]};
        reg  [31:0] r32r;
        wire [33:0] th32;
        // u = T_hi + (m q)_hi + [T_lo != 0], per lane in the packed mode (each lane sum is below 2^16)
        wire [16:0] uln = {1'b0, th32[15:0]} + {1'b0, lfh[15:0]} + {16'd0, `TL_NZ(th32[32])};
        wire [16:0] uhn = {1'b0, th32[31:16]} + {1'b0, lfh[31:16]} + {16'd0, mp ? `TL_NZ(th32[33]) : uln[16]};
        always @(posedge clk) begin
            if (rst) vs <= {2*FUSE{1'b0}};
            else if (ce) vs <= {vs[2*FUSE-1:1], v1};
            if (ce) begin
                u32  <= {uhn, uln[15:0]};
                r32r <= {`TL_GE(uq_ge_h) ? uq[32:17] : u32[31:16], `TL_GE(uq_ge_l) ? uq[15:0] : u32[15:0]};
            end
        end
`ifndef SYNTHESIS
        // shadow: u - q in two halves and the separate p0 + p1 (before a_cg_z020_share)
        wire [16:0] uql = {1'b0, u32[15:0]} - {1'b0, q32r[15:0]};
        wire [17:0] uqh = {1'b0, u32[32:16]} - {2'b0, q32r[31:16]} - {17'd0, !mp && uql[16]};
        wire        gel = mp ? !uql[16] : !uqh[17];
        always @(posedge clk) begin
            if (!rst && ce && !mf && (^{u32, q32r}) !== 1'bx && (uq_ge_h !== !uqh[17] || uq_ge_l !== gel ||
                (uq_ge_h && uq[32:17] !== uqh[15:0]) || (uq_ge_l && uq[15:0] !== uql[15:0])))
                $fatal(1, "u - q chain differs");
            if (!rst && ce && mf && wpv && wpp == 2'd1 && wts !== {1'b0, wpr} + {1'b0, wpl} + {32'd0, wpc && wtc1})
                $fatal(1, "p0 + p1 on the Montgomery chain differs");
        end
`endif
        tl_delay #(.W(34), .D(2 * FUSE)) d_th32 (.clk(clk), .en(ce), .d({lnz, lfh}), .q(th32));
        // Operands of the fused multiplier, each picked by a 2-bit select registered one clock ahead (from the early FFT
        // program and the pass valids), so each operand bit is one 4-input select:
        //   A: FFT limb memory, FFT limb sum memory, T_lo / m of the next pass (lfl), a1 (T pass);
        //   B: FFT root memory (NTT T pass: the operation's root, entry 0), FFT root sum memory, q', q.
        reg  [1:0] asel, bsel;
        always @(posedge clk)
            if (rst) begin asel <= 2'd3; bsel <= 2'd0; end
            else if (ce) begin
                asel <= ext_fft_valid ? {1'b0, ext_fft_mpr == 2'd2} : (vs[FUSE-1] | vs[2*FUSE-1]) ? 2'd2 : 2'd3;
                bsel <= ext_fft_valid ? {1'b0, ext_fft_mpr == 2'd2} : vs[2*FUSE-1] ? 2'd3 : vs[FUSE-1] ? 2'd2 : 2'd0;
            end
        assign A32 = asel == 2'd0 ? wmx[mxa] : asel == 2'd1 ? wmsx[msxa] : asel == 2'd2 ? lfl : a1;
        assign B32 = bsel == 2'd0 ? wmw[mwa] : bsel == 2'd1 ? wmsw[mswa] :
                     bsel == 2'd2 ? ((ks[FUSE]) ? qi1 : qi0) : ((ks[2*FUSE]) ? q1 : q0);
        assign r32 = r32r;
`ifndef SYNTHESIS
        // shadow: the operand selects before a_cg_z020_share
        wire [31:0] A32_ref = mbz ? mopa : (vs[FUSE] | vs[2*FUSE]) ? lfl : a1;
        wire [31:0] B32_ref = mbz ? mopb : vs[2*FUSE] ? ((ks[2*FUSE]) ? q1 : q0) : vs[FUSE] ? ((ks[FUSE]) ? qi1 : qi0) : w1;
        always @(posedge clk)
            if (!rst && ce && (mbz || v1 || vs[FUSE] || vs[2*FUSE]) && (A32 !== A32_ref || B32 !== B32_ref))
                $fatal(1, "registered operand select differs: A %h/%h B %h/%h", A32, A32_ref, B32, B32_ref);
`endif
    end else begin : g_ded32
        // Dedicated: fused leaves compute T (+FUSE); m = T_lo*q' and m*q with behavioral *
        // through DED registers; result at +FUSE+DED+2 = E32.
        reg  [31:0] ma, mp1, mp2, r32r;
        reg  [63:0] mq1, mq2, mq3;
        reg  [32:0] u32;
        wire [31:0] q32r = ((ks[E32-1]) ? q1 : q0);
        wire [31:0] qim  = ks[FUSE+1] ? qi1 : qi0;     // q' and q of the operation at the two products
        wire [31:0] qm   = ks[FUSE+3] ? q1 : q0;
        wire [33:0] u32q = {1'b0, u32} - {2'b0, q32r};     // sign bit 33: u < q
        wire [32:0] th32;
        always @(posedge clk)
            if (ce) begin
                ma   <= lf[31:0];
                mp1  <= ma * qim;
                mp2  <= mp1;
                mq1  <= mp2 * qm;
                mq2  <= mq1;
                mq3  <= mq2;
                u32  <= {1'b0, th32[31:0]} + {1'b0, mq3[63:32]} + `TL_NZ(th32[32]);
                r32r <= `TL_GE(!u32q[33]) ? u32q[31:0] : u32[31:0];
            end
        tl_delay #(.W(33), .D(DED)) d_th32 (.clk(clk), .en(ce), .d({|lf[31:0], lf[63:32]}), .q(th32));
        assign A32 = mbz ? mopa : a1;
        assign B32 = mbz ? mopb : w1;
        assign wts = {1'b0, wpr} + {1'b0, wpl} + {32'd0, wpc && wtc1};
        assign r32 = r32r;
    end endgenerate
    // FFT: product accumulator. A product's first step starts from the rounding 2^(W/2 - 1) (2^15 for L = 1,
    // with cfg_floor; 2^31 in column 0 for L = 2, 2^63 = 2^31 in column 1 for L = 4); a column's last step emits the low
    // 32 bit (L = 1: bits 47:16), the next step shifts by 32.
    wire [9:0] dcw;
    reg  [FUSE:1] mvd;
    always @(posedge clk)
        if (rst) mvd <= {FUSE{1'b0}};
        else if (ce) mvd <= {mvd[FUSE-1:1], mbz};
    tl_delay #(.W(10), .D(FUSE)) d_mcw (.clk(clk), .en(ce), .d({mbn, mpr, mcol[1:0], mcol[2], mcol[3], mfirst}), .q(dcw));
    reg  signed [67:0] wacc;
    reg         wcn;
    wire signed [67:0] winit = native_r ? 68'sd0 : w4 ? 68'sh8000_0000_0000_0000 : l1 ? (floor_r ? 68'sd0 : 68'sh8000) : 68'sh8000_0000;
    wire signed [67:0] wain = dcw[0] ? winit : wcn ? (wacc >>> 32) : wacc;
    wire signed [67:0] wanx = wain + {{3{lf[64]}}, lf};
    reg  [2:0]  wpn;
    always @(posedge clk) begin
        if (ce && mvd[FUSE]) begin wacc <= wanx; wcn <= dcw[1]; end
        if (rst) wpv <= 1'b0;
        else if (ce) wpv <= mvd[FUSE] && dcw[1] && dcw[2];
        if (ce) begin wpl <= l1 ? wanx[47:16] : wanx[31:0]; wpp <= dcw[6:5]; wpe <= dcw[4:3]; wpn <= dcw[9:7]; end
    end
    // T: p0 limbs wait in wps; with p1: T.re = p0 - p1 and p0 + p1 (back into wps); with p2: T.im = p2 - (p0 + p1)
    (* ram_style = "distributed" *) reg  [31:0] wps [0:3];
    assign      wpr = wps[wpe];
    assign      wpc = `TL_CY(wpe != 2'd0);
    reg         wtb1, wtb2, wtv_r;
    reg  [41:0] wavr;
    reg  [1:0]  wtp, wtl;
    // one subtract chain: row 1 p0 - p1 (wps - product), row 2 p2 - (p0 + p1) (product - wps)
    wire        w2  = (wpp == 2'd2);
    wire [32:0] wtx = {1'b0, w2 ? wpl : wpr} - {1'b0, w2 ? wpr : wpl} - {32'd0, wpc && (w2 ? wtb2 : wtb1)};
    always @(posedge clk) begin
        if (rst) wtv_r <= 1'b0;
        else if (ce) wtv_r <= wpv && wpp != 2'd0;
        if (ce && wpv) begin
            if (wpp == 2'd0) wps[wpe] <= wpl;
            if (wpp == 2'd1) begin wps[wpe] <= wts[31:0]; wtc1 <= wts[32]; wtb1 <= wtx[32]; end
            if (wpp == 2'd2) wtb2 <= wtx[32];
            wtp <= wpp; wtl <= wpe;
        end
        // the A-side limb of the output limb (FFT, row wpp: 1 real, 2 imaginary), or the NTT side data, read here
        // and registered so the output stage starts from a register
        if (ce && (mf ? wpv : vd[E32-1]))
            wavr <= wma[mf ? wadr(w4, l1, wpn, (wpp == 2'd2) ? {1'b0, wpe} + wL : {1'b0, wpe}) : nra];
    end
    assign wte = wtl;
    assign wav = wavr;
    assign wtv = wtv_r;

    reg  [31:0] t5;                                // T limb at the output stage
    always @(posedge clk)
        if (ce && wpv && wpp != 2'd0) t5 <= wtx[31:0];
    assign t = mf ? t5 : r32;


    // Leaf operands: the engine's 32x32 operands on the fused multiplier (packed NTT: leaves 2, 3 get A = 0 through their
    // register's reset, zh).
    always @* begin
        la  = {A32[31:16], A32[15:0], A32[31:16], A32[15:0]};
        lb  = {B32[15:0], B32[31:16], B32[31:16], B32[15:0]};
        lsa = mbz ? {msa, 1'b0, msa, 1'b0} : 4'd0;    // FFT: only the top limb is signed; NTT unsigned
        lsb = mbz ? {1'b0, msb, msb, 1'b0} : 4'd0;
    end

    // ---------------- post stage and result ----------------
    function [31:0] half(input [31:0] s, input [31:0] qq, input ln);    // ln: two 16-bit lanes (packed NTT)
        reg [32:0] h;
        begin
            h = {1'b0, s} + {1'b0, ((ln ? s[16] : s[0]) ? qq[31:16] : 16'd0), (s[0] ? qq[15:0] : 16'd0)};
            half = {h[32:17], h[16] && !ln, h[15:1]};
        end
    endfunction
    wire [31:0] q_t = slot_t ? q1 : q0;
`ifdef FAULT_HALVE_ALWAYS
    wire [31:0] gs0 = half(side_t, q_t, mp);
`else
    wire [31:0] gs0 = (halve_r && !mf) ? half(side_t, q_t, mp) : side_t;     // FFT: no halving
`endif
    // CT (dir = 0: NTT CT and FFT forward): x + t, x - t leave the add/sub one clock after the result, so the output moves
    // one clock (valid, tag, pairing flag delayed with it). GS (dir = 1: NTT GS and FFT inverse): the side data (x + y, or
    // A + B) and the result (T) leave in the clock of the result. FFT limbs leave in order, each in the clock its T limb is
    // made (forward: one clock later); the carry between limbs of the forward A + T, A - T comes from the add/sub's first
    // clock. No scaling here: the core applies div2e of the last inverse layer when the host reads the result.
    wire        ct_out = !dir;
    reg         tv_d, sw6t_d;
    reg  [7:0]  tag_d;
    wire [31:0] zn0 = dir ? gs0 : us;
    wire [31:0] zn1 = dir ? t : ud;
    always @(posedge clk)
        if (ce && wtv) begin wfc <= as_co; wfb <= as_bo; end
    // a butterfly's buffers are free once its last T limb (imaginary row, top limb) is made
    assign wrel = ce && wtv && wtp == 2'd2 && ({1'b0, wte} == wL - 3'd1);
    // packed NTT, pairing inside a word: lane A's two results form z0, lane B's z1
    wire        sw6t_now = mp && wav[40];
    always @(posedge clk) begin
        if (rst) tv_d <= 1'b0;
        else if (ce) tv_d <= tv && ct_out;
        if (ce) begin sw6t_d <= sw6t_now; tag_d <= tag_t; end
    end
    wire        sw6t = ct_out ? sw6t_d : sw6t_now;
    wire [31:0] z0 = sw6t ? {zn1[15:0], zn0[15:0]} : zn0;
    wire [31:0] z1 = sw6t ? {zn1[31:16], zn0[31:16]} : zn1;

    wire        emit  = ct_out ? tv_d : tv;
    wire [63:0] edata = {z1, z0};
    wire [7:0]  etag  = ct_out ? tag_d : tag_t;

    // Port register rv/rd/rt changes only when en = 1. Skid kv/kd/kt (EN_REG): the result made in the
    // extra datapath cycle after en falls waits there and moves to the port register when en returns
    // (that cycle the datapath is still, so nothing else is emitted).
    reg         rv, kv;
    reg [63:0]  rd, kd;
    reg [7:0]   rt, kt;
    always @(posedge clk) begin
        if (rst) begin
            rv <= 1'b0; kv <= 1'b0;
        end else if (en) begin
            rv <= kv | (ce & emit);
            kv <= 1'b0;
        end else if (ce && emit) begin
            kv <= 1'b1;
        end
        if (en && kv) begin rd <= kd; rt <= kt; end
        else if (en && ce && emit) begin rd <= edata; rt <= etag; end
        if (!en && ce && emit) begin kd <= edata; kt <= etag; end
    end
    assign rsp_valid = rv & en;
    assign rsp_data  = rd;
    assign rsp_tag   = rt;

endmodule

