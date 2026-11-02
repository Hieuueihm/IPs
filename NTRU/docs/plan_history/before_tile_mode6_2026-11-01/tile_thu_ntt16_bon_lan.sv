// tile_thu: acceptance RTL of the tile test block (spec/FlexTransform/2.0/10_hop_dong_tile.md).
// Separate from the draft in hdl/tile_thu/; do not compile both together.
//
// One 32-bit NTT lane per tile, R = 2^32 for every odd q, 3 <= q < 2^31 (small q such as 3329 and
// 12289 included: there is no 16-bit lane). A request is one modmul (mode 2) or one butterfly
// (mode 4) with fixed operand slots x = d0, y = d1, w = r0; modes 0/1 are the raw and the FFT 32x32
// products.
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
// Mode 5 (FFT butterfly, spec 10, 4.7; one engine for 32 / 64 / 128 bit since 01/11/2026): cfg_q[5:4] = 0 / 1 / 2 gives
// L = 1 / 2 / 4 limbs of 32 bit per value. A butterfly is 2L beats: limb k of (A.re, B.re, wr) for k = 0..L-1, then limb
// k of (A.im, B.im, wi); its 2L results come back in the same order. The tile keeps the limbs of up to 4 butterflies in
// small memories and reuses its own operations: the fused multiplier makes each W-bit product as 1 / 4 / 15 limb
// products, column by column into one product accumulator (rounding added in at the start; at 32 bit the Q16.16
// product of mode 1); the add/sub with q = 0 makes A + B, A - B (inverse, at the input) and A + T, A - T (forward, at
// the output) with a carry between limbs; two sum adders make o.re + o.im and wr + wi, three T adders p0 - p1,
// p0 + p1, p2 - (p0 + p1), and two rounding adders with one funnel shifter each make div2e (req_sign[0] = 1, s =
// cfg_q[3:0]; the last layer of the inverse FFT), all with a carry between limbs. One butterfly every 3 * (1 / 4 / 15)
// cycles.
//
// Mode 6 (NTT with two 16-bit coefficients per 32-bit word, spec 10, 4.9; q < 2^15): a request is two words and two
// 16-bit roots; the four 16x16 leaves run as four independent 16-bit Montgomery lanes (R = 2^16, three passes on the
// same leaf, 4 cycles apart with LEAF_PD = 2), two lanes per request, two requests every 3 cycles: 4 coefficient butterflies per 3 cycles.
//
// Every register holds when en = 0. Latency per mode is fixed and does not depend on data
// or on the direction. The handshake drives valid bits only, never an operand select.

// Fault hooks for the testbench self-check (11_kiem_thu_tile.md, group C). Never defined in a
// normal build. FAULT_NO_NZ / FAULT_NZ_ONE: carry bit [T_lo != 0] forced to 0 / 1;
// FAULT_NO_SUBQ: final conditional subtract of q in the reduction removed; FAULT_HALVE_ALWAYS:
// GS sum halved even when cfg_halve = 0; FAULT_SWAP_XY: butterfly operands x and y swapped;
// FAULT_IGNORE_SLOT: every request uses modulus slot 0; FAULT_NO_CARRY: no carry between the limbs of mode 5 at
// 64 / 128 bit (add/sub, sums, T, rounding).
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
                ar <= a[16*k+:16]; br <= b[16*k+:16]; sar <= sa[k]; sbr <= sb[k];
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

// Modular add and subtract, a, b in [0, q): s = a + b mod q, d = a - b mod q. One carry chain for
// each sum and one for each correction; the sign of the corrected value picks the result. ci / bi carry into the
// sum / borrow into the difference, co / bo out (limb chains of mode 5, only with q = 0; else 0).
module tl_addsub #(parameter integer W = 32) (
    input  wire [W-1:0] a, b, q,
    input  wire         ci, bi,
    output wire [W-1:0] s, d,
    output wire         co, bo
);
    wire [W:0]   sum = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, ci};
    wire [W+1:0] sq  = {1'b0, sum} - {2'b0, q};
    wire [W:0]   df  = {1'b0, a} - {1'b0, b} - {{W{1'b0}}, bi};
    wire [W-1:0] dq  = df[W-1:0] + q;
    assign s = sq[W+1] ? sum[W-1:0] : sq[W-1:0];
    assign d = df[W] ? dq : df[W-1:0];
    assign co = sum[W];
    assign bo = df[W];
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

module tile_thu #(parameter integer TREN_MANG = 1,
                  parameter integer LEAF_PD   = `TL_LEAF_PD_DEFAULT,
                  parameter integer IN_REG    = `TL_IN_REG_DEFAULT,
                  parameter integer EN_REG    = `TL_EN_REG_DEFAULT,
                  parameter integer PHASE     = `TL_PHASE_DEFAULT) (
    input  wire         clk, rst, en,
    output wire         idle,
    input  wire         cfg_we, cfg_slot,
    input  wire [31:0]  cfg_q, cfg_qinv,
    input  wire         cfg_floor, cfg_halve,
    input  wire         req_valid,
    output wire         req_ready,
    input  wire [2:0]   req_mode,
    input  wire         req_dir,
    input  wire         req_slot,
    input  wire [1:0]   req_sign,
    input  wire [63:0]  req_data,
    input  wire [31:0]  req_root,
    input  wire [7:0]   req_tag,
    output wire         rsp_valid,
    output wire [64:0]  rsp_data,
    output wire [7:0]   rsp_tag
);
    localparam [0:0] ARR32  = (TREN_MANG == 1);            // reduction on the fused leaves
    localparam [0:0] INREG  = (IN_REG == 1);
    localparam [0:0] ENREG  = (EN_REG == 1);
    localparam [1:0] PH0    = PHASE;                     // reset value of the issue counter
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
    reg        floor_r, halve_r;
    reg [31:0] q0, q1, qi0, qi1;
    reg [6:0]  inflight;
    assign idle = (inflight == 7'd0);
    always @(posedge clk)
        if (rst) begin
            floor_r <= 1'b0; halve_r <= 1'b0;
            q0 <= 32'd0; q1 <= 32'd0; qi0 <= 32'd0; qi1 <= 32'd0;
        end else if (en && cfg_we && idle) begin
            floor_r <= cfg_floor; halve_r <= cfg_halve;
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
    reg  [2:0] md;
    reg        dir, m5;                       // m5: mode 5, kept as its own register (it steers the add/sub's q)
    always @(posedge clk)
        if (rst) begin md <= 3'd0; dir <= 1'b0; m5 <= 1'b0; end
        else if (en && idle) begin md <= req_mode; dir <= req_dir; m5 <= (req_mode == 3'd5); end
    wire same = (req_mode == md) && (req_dir == dir);
    wire ntt  = (md == 3'd2) || (md == 3'd4);
    wire m6   = (md == 3'd6);
    // mode 6: free-running period-3 counter (no PHASE offset); requests at phase 0 go to leaves 0, 1, at phase 1 to 2, 3
    reg [1:0] p6;
    always @(posedge clk)
        if (rst) p6 <= 2'd0;
        else if (ce) p6 <= (p6 == 2'd2) ? 2'd0 : p6 + 2'd1;
    // mode 5 width (constants slot 0, bits 5:4): 0 = 32 bit (L = 1 limb), 1 = 64 bit (L = 2), 2 = 128 bit (L = 4)
    wire       l1   = (q0[5:4] == 2'd0);
    wire       w4   = q0[5];
    wire [2:0] wL   = w4 ? 3'd4 : l1 ? 3'd1 : 3'd2;
    wire [2:0] wB   = w4 ? 3'd7 : l1 ? 3'd1 : 3'd3;     // last beat of a butterfly, 2L - 1
    // mode 5: a butterfly is accepted while one of the limb buffers is free (wnb: butterflies holding one). The limb
    // memories have 32 entries: 8 buffers of 2 beats at 32 bit (its latency needs more than 4 for one butterfly every 3
    // cycles), 4 of 4 or 8 beats at 64 / 128 bit.
    reg  [2:0] wbf;                                 // beat of the butterfly being accepted
    reg  [3:0] wnb;                                 // buffers in use
    wire       wrel;                                // the last result of a butterfly leaves: its buffer is free
    wire       wspace = (wbf != 3'd0) || (wnb != (l1 ? 4'd8 : 4'd4));
    // memory address of beat (or limb) k of buffer b: 2L entries per buffer
    function [4:0] wadr(input f4, input f1, input [2:0] b, input [2:0] k);
        wadr = f4 ? {b[1:0], k} : f1 ? {1'b0, b, k[0]} : {1'b0, b[1:0], k[1:0]};
    endfunction
    function [2:0] wnext(input f1, input [2:0] b);                  // next buffer (8 at 32 bit, else 4)
        wnext = f1 ? b + 3'd1 : {1'b0, b[1:0] + 2'd1};
    endfunction

    // Issue slot of the on-array engine (period 3); always open with the dedicated engine.
    reg [1:0] ph;
    always @(posedge clk)
        if (rst) ph <= ARR32 ? PH0 : 2'd0;
        else if (ce) ph <= (!ARR32 || ph == 2'd2) ? 2'd0 : ph + 2'd1;

    assign req_ready = same && (!ENREG || ce) && ((md <= 3'd1) || (ntt && ph == 2'd0) ||
                       (m5 && wspace) || (m6 && p6 != 2'd2));
    wire fire = en && req_valid && req_ready;
    always @(posedge clk)
        if (rst) begin wbf <= 3'd0; wnb <= 4'd0; end
        else begin
            if (fire && m5) wbf <= (wbf == wB) ? 3'd0 : wbf + 3'd1;
            wnb <= wnb + {3'd0, fire && m5 && wbf == 3'd0} - {3'd0, wrel};
        end
    wire f01  = fire && (md <= 3'd1);
    wire f5   = fire && m5;
    wire f6   = fire && m6;

    // Request as the datapath sees it: the ports, or one register stage after acceptance (IN_REG).
    wire        rq_ntt, rq_01, rq_slot, rq_5, rq_6, rq_g6;
    wire [63:0] rq_data;
    wire [31:0] rq_root;
    wire [7:0]  rq_tag;
    wire [1:0]  rq_sign;
    generate if (INREG) begin : g_in_reg
        reg        rn, r01, rslot, r5, r6, rg6;
        reg [63:0] rdat;
        reg [31:0] rroot;
        reg [7:0]  rtag;
        reg [1:0]  rsign;
        always @(posedge clk) begin
            if (rst) begin rn <= 1'b0; r01 <= 1'b0; r5 <= 1'b0; r6 <= 1'b0; end
            else if (ce) begin rn <= fire && ntt; r01 <= f01; r5 <= f5; r6 <= f6; end
            if (ce) rg6 <= (p6 == 2'd1);
            if (ce) begin
                rdat <= req_data; rroot <= req_root; rtag <= req_tag; rsign <= req_sign; rslot <= `TL_SLOT(req_slot);
            end
        end
        assign rq_ntt = rn;  assign rq_01 = r01;  assign rq_data = rdat;  assign rq_slot = rslot;
        assign rq_5 = r5;  assign rq_6 = r6;  assign rq_g6 = rg6;
        assign rq_root = rroot;  assign rq_tag = rtag;  assign rq_sign = rsign;
    end else begin : g_in_wire
        assign rq_ntt = fire && ntt;  assign rq_01 = f01;  assign rq_data = req_data;  assign rq_slot = `TL_SLOT(req_slot);
        assign rq_5 = f5;  assign rq_6 = f6;  assign rq_g6 = (p6 == 2'd1);
        assign rq_root = req_root;  assign rq_tag = req_tag;  assign rq_sign = req_sign;
    end endgenerate

    // ---------------- butterfly: operand stage ----------------
    wire [31:0] d0 = rq_data[31:0], d1 = rq_data[63:32];
`ifdef FAULT_SWAP_XY
    wire [31:0] xin = d1, yin = d0;
`else
    wire [31:0] xin = d0, yin = d1;
`endif
    wire [31:0] side_t, t;          // side data and engine result at the post stage
    wire        slot_t;             // modulus slot at the post stage
    wire [31:0] us, ud;
    wire        as_co, as_bo, as_ci, as_bi;
    // mode 5: q = 0, so the modular add/sub is the plain 32-bit wrap add/sub
    tl_addsub #(.W(32)) u_as (
        .a(dir ? xin : side_t), .b(dir ? yin : t),
        .q(m5 ? 32'd0 : ((dir ? rq_slot : slot_t) ? q1 : q0)), .ci(as_ci), .bi(as_bi), .s(us), .d(ud),
        .co(as_co), .bo(as_bo));

    // m5: beat and buffer of the request at the datapath input (after IN_REG), its limb; the inverse A + B, A - B
    // chains carry from limb to limb at the input, the forward A + T, A - T chains at the output (wte: output limb)
    reg  [2:0] wbi;
    reg  [2:0] wbn;
    reg        wic, wib, wfc, wfb;
    wire [1:0] wte;
    wire       wte0 = (wte != 2'd0);
    wire [2:0] wki  = (wbi >= wL) ? wbi - wL : wbi;
    always @(posedge clk) begin
        if (rst) begin wbi <= 3'd0; wbn <= 3'd0; end
        else if (ce && rq_5 && m5) begin
            wbi <= (wbi == wB) ? 3'd0 : wbi + 3'd1;
            if (wbi == wB) wbn <= wnext(l1, wbn);
        end
        if (ce && rq_5) begin wic <= as_co; wib <= as_bo; end
    end
    assign as_ci = `TL_CY(m5 && (dir ? (wki != 3'd0) && wic : wte0 && wfc));
    assign as_bi = `TL_CY(m5 && (dir ? (wki != 3'd0) && wib : wte0 && wfb));

    // Operand stage: engine operand a1 (times w1) and side data s1 (x for CT, x + y for GS).
    reg         v1, v5, sc1;
    reg  [31:0] a1, w1, s1;
    reg  [7:0]  g1;
    reg  [2:0]  wb1;
    reg  [2:0]  wn1;
    always @(posedge clk) begin
        if (ce) begin wb1 <= wbi; wn1 <= wbn; end
        if (rst) begin v1 <= 1'b0; v5 <= 1'b0; end
        else if (ce) begin v1 <= rq_ntt; v5 <= rq_5; end
        if (ce) begin
            a1 <= (md == 3'd2) ? d0 : dir ? ud : yin;
            s1 <= dir ? us : xin;
            w1 <= rq_root;
            g1 <= rq_tag;
            sc1 <= rq_sign[0];
        end
    end

    // Modulus slot of the operation, ks[n] = slot of the operation n cycles after the operand stage.
    reg [E32:0] ks;
    always @(posedge clk)
        if (ce) ks <= {ks[E32-1:0], rq_slot};

    // Side data and valid wait for the engine.
    reg [40:0]    sd [1:E32];
    reg [E32:1]   vd;
    integer i;
    always @(posedge clk) begin
        if (rst) vd <= {E32{1'b0}};
        else if (ce) vd <= {vd[E32-1:1], v1};
        if (ce) begin
            sd[1] <= {ks[0], g1, s1};
            for (i = 2; i <= E32; i = i + 1) sd[i] <= sd[i-1];
        end
    end
    // NTT results at +E32 (shift-register LUTs); mode 5 from its own engine below
    wire        wov;                    // mode 5: a result limb this cycle
    wire [7:0]  wtag;
    wire [40:0] wav;                    // mode 5: the A-side limb of the output limb (A or A + B, tag, scale)
    wire        tv  = m5 ? wov : vd[E32];
    wire [40:0] tap = sd[E32];
    assign side_t = m5 ? wav[31:0] : tap[31:0];
    wire [7:0]  tag_t = m5 ? wtag : tap[39:32];
    assign slot_t = tap[40];

    // ---------------- multiplier leaves and modmul engine ----------------
    reg  [63:0]  la, lb;
    reg  [3:0]   lsa, lsb;
    wire [131:0] lp;
    wire [64:0]  lf;
    tl_leaves #(.PD(LEAF_PD)) leaves (.clk(clk), .en(ce), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(lp), .f(lf));

    wire [31:0] A32e, B32e, r32;
    reg  [31:0] sa5, sw5;
    // m5: limb memories, 4 buffers of 2L beats / L limbs, address {buffer, beat or limb}; small LUT memories (a block
    // RAM's slow clock-to-out would sit on the output path)
    (* ram_style = "distributed" *) reg  [40:0] wma  [0:31];    // A (forward) or A + B (inverse), tag, scale flag; per beat
    (* ram_style = "distributed" *) reg  [31:0] wmx  [0:31];    // o: B (forward) or A - B (inverse); per beat
    (* ram_style = "distributed" *) reg  [31:0] wmw  [0:31];    // root; per beat
    (* ram_style = "distributed" *) reg  [31:0] wmsx [0:31];    // o.re + o.im; per limb
    (* ram_style = "distributed" *) reg  [31:0] wmsw [0:31];    // wr + wi; per limb
    wire       wim1 = (wb1 >= wL);                              // imaginary beat at the operand stage
    wire [2:0] wk1  = wim1 ? wb1 - wL : wb1;
    wire [4:0] wir  = wadr(w4, l1, wn1, wk1);                  // its real beat
    reg        wcs, wcw, wsv, wsl;
    reg  [4:0] wsa;
    // the two sum adders: a limb of o.re + o.im, wr + wi with the carry of the limb below
    wire        wcz = `TL_CY(wk1 != 3'd0);
    wire [32:0] sao = {1'b0, wmx[wir]} + {1'b0, a1} + {32'd0, wcz && wcs};
    wire [32:0] swo = {1'b0, wmw[wir]} + {1'b0, w1} + {32'd0, wcz && wcw};
    always @(posedge clk) begin
        if (ce && v5 && wim1) begin sa5 <= sao[31:0]; sw5 <= swo[31:0]; end
        if (ce && v5 && m5) begin
            wma[wadr(w4, l1, wn1, wb1)] <= {sc1, g1, s1}; wmx[wadr(w4, l1, wn1, wb1)] <= a1; wmw[wadr(w4, l1, wn1, wb1)] <= w1;
        end
        if (rst) wsv <= 1'b0;
        else if (ce) wsv <= v5 && m5 && wim1;
        if (ce && v5 && m5 && wim1) begin wcs <= sao[32]; wcw <= swo[32]; wsa <= {wn1, wk1[1:0]}; wsl <= (wk1 == wL - 3'd1); end
        if (ce && wsv) begin wmsx[wsa] <= sa5; wmsw[wsa] <= sw5; end
    end

    // mode 5: products. One butterfly at a time, in order: p0 = o.re * wr, p1 = o.im * wi, p2 = (o.re + o.im) * (wr + wi),
    // each as limb products column by column (product scanning; top limb signed). wtab: {i, j, last of its column,
    // column emitted, emitted limb}; a product's emitted columns are L/2 .. 3L/2 - 1, columns from 3L/2 are dropped
    // (L = 1: one product, its bits 47:16).
    function [7:0] wtab(input f4, input f1, input [3:0] st);
        if (f1)
            wtab = {2'd0, 2'd0, 1'b1, 1'b1, 2'd0};
        else if (!f4)
            case (st[1:0])
                2'd0: wtab = {2'd0, 2'd0, 1'b1, 1'b0, 2'd0};
                2'd1: wtab = {2'd0, 2'd1, 1'b0, 1'b0, 2'd0};
                2'd2: wtab = {2'd1, 2'd0, 1'b1, 1'b1, 2'd0};
                default: wtab = {2'd1, 2'd1, 1'b1, 1'b1, 2'd1};
            endcase
        else
            case (st)
                4'd0:  wtab = {2'd0, 2'd0, 1'b1, 1'b0, 2'd0};
                4'd1:  wtab = {2'd0, 2'd1, 1'b0, 1'b0, 2'd0};
                4'd2:  wtab = {2'd1, 2'd0, 1'b1, 1'b0, 2'd0};
                4'd3:  wtab = {2'd0, 2'd2, 1'b0, 1'b0, 2'd0};
                4'd4:  wtab = {2'd1, 2'd1, 1'b0, 1'b0, 2'd0};
                4'd5:  wtab = {2'd2, 2'd0, 1'b1, 1'b1, 2'd0};
                4'd6:  wtab = {2'd0, 2'd3, 1'b0, 1'b0, 2'd1};
                4'd7:  wtab = {2'd1, 2'd2, 1'b0, 1'b0, 2'd1};
                4'd8:  wtab = {2'd2, 2'd1, 1'b0, 1'b0, 2'd1};
                4'd9:  wtab = {2'd3, 2'd0, 1'b1, 1'b1, 2'd1};
                4'd10: wtab = {2'd1, 2'd3, 1'b0, 1'b0, 2'd2};
                4'd11: wtab = {2'd2, 2'd2, 1'b0, 1'b0, 2'd2};
                4'd12: wtab = {2'd3, 2'd1, 1'b1, 1'b1, 2'd2};
                4'd13: wtab = {2'd2, 2'd3, 1'b0, 1'b0, 2'd3};
                default: wtab = {2'd3, 2'd2, 1'b1, 1'b1, 2'd3};
            endcase
    endfunction
    reg  [3:0] wrdy;                    // butterflies with every input limb in, not yet multiplied
    reg        mbz;                     // the multiplier runs a m5 butterfly
    reg  [2:0] mbn;                     // its buffer
    reg  [1:0] mpr;                     // product
    reg  [3:0] mst;                     // step in the product
    wire [3:0] mlst = w4 ? 4'd14 : l1 ? 4'd0 : 4'd3;
    wire       mend = mbz && mpr == 2'd2 && mst == mlst;
    wire       mtake = (!mbz || mend) && (wrdy != 4'd0);
    always @(posedge clk)
        if (rst) begin wrdy <= 4'd0; mbz <= 1'b0; mbn <= 3'd0; mpr <= 2'd0; mst <= 4'd0; end
        else if (ce) begin
            wrdy <= wrdy + {3'd0, wsv && wsl} - {3'd0, mtake};
            if (mend) mbn <= wnext(l1, mbn);
            if (mtake) begin mbz <= 1'b1; mpr <= 2'd0; mst <= 4'd0; end
            else if (mend) mbz <= 1'b0;
            else if (mbz) begin
                if (mst == mlst) begin mst <= 4'd0; mpr <= mpr + 2'd1; end
                else mst <= mst + 4'd1;
            end
        end
    wire [7:0]  mt   = wtab(w4, l1, mst);
    wire [2:0]  moff = (mpr == 2'd1) ? wL : 3'd0;             // p1 reads the imaginary beats
    wire [31:0] mopa = (mpr == 2'd2) ? wmsx[{mbn, mt[7:6]}] : wmx[wadr(w4, l1, mbn, {1'b0, mt[7:6]} + moff)];
    wire [31:0] mopb = (mpr == 2'd2) ? wmsw[{mbn, mt[5:4]}] : wmw[wadr(w4, l1, mbn, {1'b0, mt[5:4]} + moff)];
    wire        msa  = mt[7:6] == (w4 ? 2'd3 : l1 ? 2'd0 : 2'd1);    // top limb: signed
    wire        msb  = mt[5:4] == (w4 ? 2'd3 : l1 ? 2'd0 : 2'd1);
    wire [31:0] A32 = mbz ? mopa : A32e;
    wire [31:0] B32 = mbz ? mopb : B32e;
    generate if (ARR32) begin : g_arr32
        // On the fused leaves: T at +0, m = T_lo*q' at +FUSE, m*q at +2*FUSE (three different
        // residues mod 3, so ops issued 3 cycles apart never collide); result at +3*FUSE+2 = E32.
        reg  [2*FUSE:1] vs;
        reg  [32:0] u32;
        wire [31:0] q32r = ((ks[E32-1]) ? q1 : q0);
        wire [33:0] u32q = {1'b0, u32} - {2'b0, q32r};     // sign bit 33: u < q
        reg  [31:0] r32r;
        wire [32:0] th32;
        always @(posedge clk) begin
            if (rst) vs <= {2*FUSE{1'b0}};
            else if (ce) vs <= {vs[2*FUSE-1:1], v1};
            if (ce) begin
                u32  <= {1'b0, th32[31:0]} + {1'b0, lf[63:32]} + `TL_NZ(th32[32]);
                r32r <= `TL_GE(!u32q[33]) ? u32q[31:0] : u32[31:0];
            end
        end
        tl_delay #(.W(33), .D(2 * FUSE)) d_th32 (.clk(clk), .en(ce), .d({|lf[31:0], lf[63:32]}), .q(th32));
        assign A32e = (vs[FUSE] | vs[2*FUSE]) ? lf[31:0] : a1;
        assign B32e = vs[2*FUSE] ? ((ks[2*FUSE]) ? q1 : q0) : vs[FUSE] ? ((ks[FUSE]) ? qi1 : qi0) : w1;
        assign r32 = r32r;
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
        assign A32e = a1;
        assign B32e = w1;
        assign r32 = r32r;
    end endgenerate
    // mode 5: product accumulator. A product's first step starts from the rounding 2^(W/2 - 1) (2^15 for L = 1, as mode 1
    // with cfg_floor; 2^31 in column 0 for L = 2, 2^63 = 2^31 in column 1 for L = 4); a column's last step emits the low
    // 32 bit (L = 1: bits 47:16), the next step shifts by 32.
    wire [9:0] dcw;
    reg  [FUSE:1] mvd;
    always @(posedge clk)
        if (rst) mvd <= {FUSE{1'b0}};
        else if (ce) mvd <= {mvd[FUSE-1:1], mbz};
    tl_delay #(.W(10), .D(FUSE)) d_mcw (.clk(clk), .en(ce), .d({mbn, mpr, mt[1:0], mt[2], mt[3], mst == 4'd0}), .q(dcw));
    reg  signed [67:0] wacc;
    reg         wcn;
    wire signed [67:0] winit = w4 ? 68'sh8000_0000_0000_0000 : l1 ? (floor_r ? 68'sd0 : 68'sh8000) : 68'sh8000_0000;
    wire signed [67:0] wain = dcw[0] ? winit : wcn ? (wacc >>> 32) : wacc;
    wire signed [67:0] wanx = wain + {{3{lf[64]}}, lf};
    reg         wpv;
    reg  [31:0] wpl;
    reg  [1:0]  wpp, wpe;
    reg  [2:0]  wpn;
    always @(posedge clk) begin
        if (ce && mvd[FUSE]) begin wacc <= wanx; wcn <= dcw[1]; end
        if (rst) wpv <= 1'b0;
        else if (ce) wpv <= mvd[FUSE] && dcw[1] && dcw[2];
        if (ce) begin wpl <= l1 ? wanx[47:16] : wanx[31:0]; wpp <= dcw[6:5]; wpe <= dcw[4:3]; wpn <= dcw[9:7]; end
    end
    // T: p0 limbs wait in wps; with p1: T.re = p0 - p1 and p0 + p1 (back into wps); with p2: T.im = p2 - (p0 + p1)
    (* ram_style = "distributed" *) reg  [31:0] wps [0:3];
    wire [31:0] wpr = wps[wpe];
    wire        wpc = `TL_CY(wpe != 2'd0);
    reg         wtb1, wtc1, wtb2, wtv;
    reg  [40:0] wavr;
    reg  [1:0]  wtp, wtl;
    wire [32:0] wtd = {1'b0, wpr} - {1'b0, wpl} - {32'd0, wpc && wtb1};
    wire [32:0] wts = {1'b0, wpr} + {1'b0, wpl} + {32'd0, wpc && wtc1};
    wire [32:0] wti = {1'b0, wpl} - {1'b0, wpr} - {32'd0, wpc && wtb2};
    always @(posedge clk) begin
        if (rst) wtv <= 1'b0;
        else if (ce) wtv <= wpv && wpp != 2'd0;
        if (ce && wpv) begin
            if (wpp == 2'd0) wps[wpe] <= wpl;
            if (wpp == 2'd1) begin wps[wpe] <= wts[31:0]; wtc1 <= wts[32]; wtb1 <= wtd[32]; end
            if (wpp == 2'd2) wtb2 <= wti[32];
            wtp <= wpp; wtl <= wpe;
            // the A-side limb of the output limb (row wpp: 1 real, 2 imaginary), read here and registered so the
            // output stage starts from a register, as with the other modes
            wavr <= wma[wadr(w4, l1, wpn, (wpp == 2'd2) ? {1'b0, wpe} + wL : {1'b0, wpe})];
        end
    end
    assign wte = wtl;
    assign wav = wavr;

    reg  [31:0] t5;                                // T limb at the output stage
    always @(posedge clk)
        if (ce && wpv && wpp != 2'd0) t5 <= (wpp == 2'd1) ? wtd[31:0] : wti[31:0];
    assign t = m5 ? t5 : r32;


    // ---------------- mode 6: four 16-bit Montgomery lanes on the four leaves ----------------
    // Lane A / B of a request: inter-word pairing (req_sign[0] = 0) (x.lo, y.lo), (x.hi, y.hi); intra-word pairing (1)
    // (x.lo, x.hi), (y.lo, y.hi). Lane butterfly as mode 4 on 16-bit values: CT (a + t, a - t), t = Mont16(b, w); GS
    // (half?(a + b), Mont16(a - b, w)). Group g (leaves 2g, 2g + 1) takes the requests of phase g. Per leaf, cycles after
    // the operand stage o (P6 = pass spacing, LEAF + 1 or LEAF + 2 so that 0, P6, 2 P6 fall on different phases; with
    // LEAF_PD = 2: P6 = 4, post stage 13): pass T = op * w at o; T at o + LEAF; pass m = T_lo * q' at o + P6; m at
    // o + P6 + LEAF; pass m * q at o + 2 P6; m q at o + 2 P6 + LEAF, with u = T_hi + (m q)_hi + [T_lo != 0]; u - q if
    // u >= q one cycle later; post stage (A + t, A - t for CT) at POST6 = 2 P6 + LEAF + 2.
    localparam integer P6    = ((LEAF + 1) % 3 != 0) ? LEAF + 1 : LEAF + 2;
    localparam integer POST6 = 2 * P6 + LEAF + 2;
    wire [15:0] q6  = (rq_slot ? q1[15:0] : q0[15:0]);
    wire [15:0] x6lo = xin[15:0], x6hi = xin[31:16], y6lo = yin[15:0], y6hi = yin[31:16];
    wire        pair6 = rq_sign[0];
    wire [15:0] a6A = x6lo, b6A = pair6 ? x6hi : y6lo;          // lane A operands at the request
    wire [15:0] a6B = pair6 ? y6lo : x6hi, b6B = y6hi;          // lane B
    wire [15:0] s6A, d6A, s6B, d6B, side6A, side6B, t6A, t6B;
    wire [15:0] q6o;                                            // modulus of the result at the post stage
    // two 16-bit modular add/subs: before the products for GS (dir = 1), after them for CT
    tl_addsub #(.W(16)) u_as6a (.a(dir ? a6A : side6A), .b(dir ? b6A : t6A), .q(dir ? q6 : q6o), .ci(1'b0), .bi(1'b0),
        .s(s6A), .d(d6A), .co(), .bo());
    tl_addsub #(.W(16)) u_as6b (.a(dir ? a6B : side6B), .b(dir ? b6B : t6B), .q(dir ? q6 : q6o), .ci(1'b0), .bi(1'b0),
        .s(s6B), .d(d6B), .co(), .bo());
    function [15:0] half16(input [15:0] v, input [15:0] qq);
        reg [16:0] h;
        begin
            h = {1'b0, v} + (v[0] ? {1'b0, qq} : 17'd0);
            half16 = h[16:1];
        end
    endfunction
`ifdef FAULT_HALVE_ALWAYS
    wire        hv6 = 1'b1;
`else
    wire        hv6 = halve_r;
`endif
    // operand stage: product operand and root of each leaf, the group's valid chain and slot chain
    reg  [15:0] op6 [0:3];
    reg  [15:0] w6  [0:3];
    reg  [POST6:0] vc6 [0:1];                                    // vc6[g][k]: group g's request entered o k cycles ago
    reg  [POST6:0] sl6;                                          // sl6[k]: slot of the request that entered o k cycles ago
    integer     g6;
    always @(posedge clk) begin
        for (g6 = 0; g6 < 2; g6 = g6 + 1) begin
            if (rst) vc6[g6] <= {(POST6 + 1){1'b0}};
            else if (ce) vc6[g6] <= {vc6[g6][POST6-1:0], rq_6 && (rq_g6 == g6[0])};
        end
        if (ce) sl6 <= {sl6[POST6-1:0], rq_slot};
        if (ce && rq_6) begin
            op6[{rq_g6, 1'b0}] <= dir ? d6A : b6A;  w6[{rq_g6, 1'b0}] <= rq_root[15:0];
            op6[{rq_g6, 1'b1}] <= dir ? d6B : b6B;  w6[{rq_g6, 1'b1}] <= rq_root[31:16];
        end
    end
    // side data (CT: a; GS: the halved sum), tag and pairing wait for the products
    wire [40:0] sd6;
    tl_delay #(.W(41), .D(POST6 + 1)) d_sd6 (.clk(clk), .en(ce),
        .d({pair6, rq_tag, dir ? (hv6 ? half16(s6B, q6) : s6B) : a6B, dir ? (hv6 ? half16(s6A, q6) : s6A) : a6A}), .q(sd6));
    // per leaf: the three passes and the reduction
    reg  [15:0] lf6a [0:3];
    reg  [15:0] lf6b [0:3];
    reg  [15:0] tlo6 [0:3];
    reg  [15:0] m6r  [0:3];
    reg  [16:0] u6   [0:3];
    reg  [15:0] r6   [0:3];
    wire [16:0] thd6 [0:3];
    genvar k6;
    generate for (k6 = 0; k6 < 4; k6 = k6 + 1) begin : g_lane6
        localparam integer G = k6 / 2;
        wire [31:0] pr6 = lp[33*k6 +: 32];                       // the leaf's product (unsigned 16 x 16)
        wire [15:0] qk  = sl6[2*P6] ? q1[15:0] : q0[15:0];             // pass m * q
        wire [15:0] qik = sl6[P6] ? qi1[15:0] : qi0[15:0];             // pass T_lo * q'
        wire [15:0] qu  = sl6[POST6-1] ? q1[15:0] : q0[15:0];          // u - q
        always @* begin
            lf6a[k6] = vc6[G][0] ? op6[k6] : vc6[G][P6] ? tlo6[k6] : vc6[G][2*P6] ? m6r[k6] : 16'd0;
            lf6b[k6] = vc6[G][0] ? w6[k6]  : vc6[G][P6] ? qik      : vc6[G][2*P6] ? qk       : 16'd0;
        end
        tl_delay #(.W(17), .D(2 * P6)) d_th6 (.clk(clk), .en(ce), .d({`TL_NZ(|pr6[15:0]), pr6[31:16]}), .q(thd6[k6]));
        wire [17:0] uq = {1'b0, u6[k6]} - {2'b0, qu};
        always @(posedge clk)
            if (ce) begin
                if (vc6[G][LEAF]) tlo6[k6] <= pr6[15:0];          // held until pass P6 (< LEAF + 3)
                if (vc6[G][P6+LEAF]) m6r[k6] <= pr6[15:0];
                u6[k6] <= {1'b0, thd6[k6][15:0]} + {1'b0, pr6[31:16]} + {16'd0, thd6[k6][16]};
                r6[k6] <= `TL_GE(!uq[17]) ? uq[15:0] : u6[k6][15:0];
            end
    end endgenerate
    // post stage: the group whose products are ready
    wire        pg6 = vc6[1][POST6];
    wire        pv6 = vc6[0][POST6] | vc6[1][POST6];
    assign t6A = pg6 ? r6[2] : r6[0];
    assign t6B = pg6 ? r6[3] : r6[1];
    assign side6A = sd6[15:0];
    assign side6B = sd6[31:16];
    assign q6o = sl6[POST6] ? q1[15:0] : q0[15:0];
    wire [15:0] o6A0 = dir ? side6A : s6A, o6A1 = dir ? t6A : d6A;      // lane results (first, second)
    wire [15:0] o6B0 = dir ? side6B : s6B, o6B1 = dir ? t6B : d6B;
    reg         tv6;
    reg  [63:0] z6;
    reg  [7:0]  tg6;
    always @(posedge clk) begin
        if (rst) tv6 <= 1'b0;
        else if (ce) tv6 <= pv6;
        if (ce && pv6) begin
            z6  <= sd6[40] ? {o6B1, o6B0, o6A1, o6A0} : {o6B1, o6A1, o6B0, o6A0};   // {new y word, new x word}
            tg6 <= sd6[39:32];
        end
    end

    // Leaf operands: mode 0/1 request or the modmul engine, both on the fused 32x32 multiplier.
    wire sa01 = (md == 3'd1) | rq_sign[0];
    wire sb01 = (md == 3'd1) | rq_sign[1];
    always @* begin
        if (m6) begin                                // mode 6: four independent unsigned 16 x 16 lanes
            la  = {lf6a[3], lf6a[2], lf6a[1], lf6a[0]};
            lb  = {lf6b[3], lf6b[2], lf6b[1], lf6b[0]};
            lsa = 4'd0;
            lsb = 4'd0;
        end else if (md <= 3'd1) begin
            la  = {d0[31:16], d0[15:0], d0[31:16], d0[15:0]};
            lb  = {d1[15:0], d1[31:16], d1[31:16], d1[15:0]};
            lsa = {sa01, 1'b0, sa01, 1'b0};
            lsb = {1'b0, sb01, sb01, 1'b0};
        end else begin
            la  = {A32[31:16], A32[15:0], A32[31:16], A32[15:0]};
            lb  = {B32[15:0], B32[31:16], B32[31:16], B32[15:0]};
            lsa = mbz ? {msa, 1'b0, msa, 1'b0} : 4'd0;    // mode 5: only the top limb is signed; NTT unsigned
            lsb = mbz ? {1'b0, msb, msb, 1'b0} : 4'd0;
        end
    end

    // ---------------- post stage and result ----------------
    function [31:0] half(input [31:0] s, input [31:0] qq);
        reg [32:0] h;
        begin
            h = {1'b0, s} + (s[0] ? {1'b0, qq} : 33'd0);
            half = h[32:1];
        end
    endfunction
    wire [31:0] q_t = slot_t ? q1 : q0;
`ifdef FAULT_HALVE_ALWAYS
    wire [31:0] gs0 = half(side_t, q_t);
`else
    wire [31:0] gs0 = halve_r ? half(side_t, q_t) : side_t;
`endif
    wire [31:0] zn0 = (md == 3'd2) ? t : dir ? gs0 : us;
    wire [31:0] zn1 = (md == 3'd2) ? 32'd0 : dir ? t : ud;
    // mode 5, scale (inverse FFT only): div2e(v, s) = (v + 2^(s-1)) >>> s after a wrap, s = q0[3:0]. The inverse
    // outputs are the side data (A + B) and T, both registers, so the division does not follow the add/sub. The rounding
    // adds into limb 0 and carries up; the shift takes s bits from the next limb, so a limb leaves one limb later (the
    // last one in the cycle after; L = 1: the cycle after its own), for every butterfly, scaled or not.
    wire [31:0] rnd = (!wte0 && wav[40] && dir) ? ((32'd1 << q0[3:0]) >> 1) : 32'd0;
    reg         wr0c, wr1c;
    wire [32:0] ry0 = {1'b0, side_t} + {1'b0, rnd} + {32'd0, `TL_CY(wte0 && wr0c)};
    wire [32:0] ry1 = {1'b0, t5} + {1'b0, rnd} + {32'd0, `TL_CY(wte0 && wr1c)};
    reg  [31:0] wy0l, wy0p, wy1l, wy1p;     // latest and previous limb of each output (after rounding)
    reg  [7:0]  wgl, wgp;                   // their tags
    reg         wo1, wx2, wo2, wsc, wim;
    wire        wlast;                  // the limb leaving now is the last one (its upper bits are its sign)
    always @(posedge clk) begin
        if (rst) begin wo1 <= 1'b0; wx2 <= 1'b0; wo2 <= 1'b0; end
        else if (ce) begin
            wo1 <= wtv && (wte0 || l1);                 // limb wte - 1 (L = 1: the limb itself) leaves in the next cycle
            wx2 <= wtv && !l1 && ({1'b0, wte} == wL - 3'd1);    // the last limb leaves one cycle after that
            wo2 <= wx2;
        end
        if (ce && wtv) begin
            wr0c <= ry0[32]; wr1c <= ry1[32]; wfc <= as_co; wfb <= as_bo;
            wy0p <= wy0l; wy1p <= wy1l; wgp <= wgl;
            wy0l <= dir ? ry0[31:0] : us;  wy1l <= dir ? ry1[31:0] : ud;  wgl <= wav[39:32];
            wsc <= wav[40] && dir;  wim <= (wtp == 2'd2);
        end
    end
    assign wlast = wo2 || (wo1 && l1);
    assign wov  = wo1 | wo2;
    assign wtag = wlast ? wgl : wgp;
    assign wrel = ce && wlast && wim;
    wire [31:0] fl0 = wlast ? wy0l : wy0p;
    wire [31:0] fh0 = wlast ? {32{wy0l[31]}} : wy0l;
    wire [31:0] fl1 = wlast ? wy1l : wy1p;
    wire [31:0] fh1 = wlast ? {32{wy1l[31]}} : wy1l;
    wire [3:0]  fsh = wsc ? q0[3:0] : 4'd0;
    wire [63:0] fz0 = {fh0, fl0} >> fsh;
    wire [63:0] fz1 = {fh1, fl1} >> fsh;
    wire [31:0] z0 = m5 ? fz0[31:0] : zn0;
    wire [31:0] z1 = m5 ? fz1[31:0] : zn1;

    // Mode 0/1: operands presented in cycle 0, fused product in cycle FUSE.
    reg  [FUSE:1] v01;
    wire [7:0] tag01;
    always @(posedge clk)
        if (rst) v01 <= {FUSE{1'b0}};
        else if (ce) v01 <= {v01[FUSE-1:1], rq_01};
    tl_delay #(.W(8), .D(FUSE)) d_tag01 (.clk(clk), .en(ce), .d(rq_tag), .q(tag01));
    wire [31:0] fft32 = lf[47:16] + {31'd0, ~floor_r & lf[15]};

    wire        emit  = v01[FUSE] | tv | tv6;
    wire [64:0] edata = v01[FUSE] ? ((md == 3'd0) ? lf : {33'd0, fft32}) : tv6 ? {1'b0, z6} : {1'b0, z1, z0};
    wire [7:0]  etag  = v01[FUSE] ? tag01 : tv6 ? tg6 : tag_t;

    // Port register rv/rd/rt changes only when en = 1. Skid kv/kd/kt (EN_REG): the result made in the
    // extra datapath cycle after en falls waits there and moves to the port register when en returns
    // (that cycle the datapath is still, so nothing else is emitted).
    reg         rv, kv;
    reg [64:0]  rd, kd;
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

    always @(posedge clk)
        if (rst) inflight <= 7'd0;
        else inflight <= inflight + {6'd0, fire} - {6'd0, rsp_valid};
endmodule

// Measurement wrapper: every input and output registered (spec 10, section 8).
module tile_thu_top #(parameter integer TREN_MANG = 1,
                      parameter integer IN_REG    = `TL_IN_REG_DEFAULT,
                      parameter integer EN_REG    = `TL_EN_REG_DEFAULT,
                      parameter integer PHASE     = `TL_PHASE_DEFAULT) (
    input  wire         clk, rst_i, en_i,
    output reg          idle_o,
    input  wire         cfg_we_i, cfg_slot_i,
    input  wire [31:0]  cfg_q_i, cfg_qinv_i,
    input  wire         cfg_floor_i, cfg_halve_i,
    input  wire         req_valid_i,
    output reg          req_ready_o,
    input  wire [2:0]   req_mode_i,
    input  wire         req_dir_i, req_slot_i,
    input  wire [1:0]   req_sign_i,
    input  wire [63:0]  req_data_i,
    input  wire [31:0]  req_root_i,
    input  wire [7:0]   req_tag_i,
    output reg          rsp_valid_o,
    output reg  [64:0]  rsp_data_o,
    output reg  [7:0]   rsp_tag_o
);
    reg         rst, en, cfg_we, cfg_slot, cfg_floor, cfg_halve, req_valid, req_dir, req_slot;
    reg [31:0]  cfg_q, cfg_qinv;
    reg [2:0]   req_mode;
    reg [1:0]   req_sign;
    reg [63:0]  req_data;
    reg [31:0]  req_root;
    reg [7:0]   req_tag;
    wire        idle, req_ready, rsp_valid;
    wire [64:0] rsp_data;
    wire [7:0]  rsp_tag;
    always @(posedge clk) begin
        rst <= rst_i; en <= en_i; cfg_we <= cfg_we_i; cfg_slot <= cfg_slot_i;
        req_slot <= req_slot_i;
        cfg_q <= cfg_q_i; cfg_qinv <= cfg_qinv_i; cfg_floor <= cfg_floor_i; cfg_halve <= cfg_halve_i;
        req_valid <= req_valid_i; req_mode <= req_mode_i; req_dir <= req_dir_i; req_sign <= req_sign_i;
        req_data <= req_data_i; req_root <= req_root_i; req_tag <= req_tag_i;
        idle_o <= idle; req_ready_o <= req_ready; rsp_valid_o <= rsp_valid;
        rsp_data_o <= rsp_data; rsp_tag_o <= rsp_tag;
    end
    tile_thu #(.TREN_MANG(TREN_MANG), .IN_REG(IN_REG), .EN_REG(EN_REG), .PHASE(PHASE)) u_tile (
        .clk(clk), .rst(rst), .en(en), .idle(idle),
        .cfg_we(cfg_we), .cfg_slot(cfg_slot), .cfg_q(cfg_q), .cfg_qinv(cfg_qinv),
        .cfg_floor(cfg_floor), .cfg_halve(cfg_halve),
        .req_valid(req_valid), .req_ready(req_ready), .req_mode(req_mode), .req_dir(req_dir), .req_slot(req_slot),
        .req_sign(req_sign), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));
endmodule
