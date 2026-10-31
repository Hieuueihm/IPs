// tile_thu: acceptance RTL of the tile test block (spec/FlexTransform/2.0/10_hop_dong_tile.md).
// Separate from the draft in hdl/tile_thu/; do not compile both together.
//
// One 32-bit NTT lane per tile, R = 2^32 for every odd q, 3 <= q < 2^31 (small q such as 3329 and
// 12289 included: there is no 16-bit lane). A request is one modmul (mode 2) or one butterfly
// (mode 4) with fixed operand slots x = d0, y = d1, w = r0; modes 0/1 are the raw and the FFT 32x32
// products.
//
// TREN_MANG = 3 (default): architecture v1. The fused leaves compute T, then one general 32-bit
//   Montgomery (behavioral *), one modmul per cycle.
// TREN_MANG = 1: reduction on the array too (rejected by hypothesis 2 at tile level, kept to compare):
//   the 4 leaves fused into one 32x32 multiplier, 3 passes (T, m, m*q) issued FUSE cycles apart; a
//   new modmul every 3 cycles.
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
//
// Butterfly: one modular add/sub unit, used before the engine for GS ((x + y, x - y) then
// Mont(x - y, w)) and after it for CT ((x + t, x - t) with t = Mont(y, w)). Mode and direction are
// fixed while the tile is busy (spec 10, 4.2), so the unit serves one place per stream.
//
// Every register holds when en = 0. Latency per mode is fixed and does not depend on data
// or on the direction. The handshake drives valid bits only, never an operand select.

// Fault hooks for the testbench self-check (11_kiem_thu_tile.md, group C). Never defined in a
// normal build. FAULT_NO_NZ / FAULT_NZ_ONE: carry bit [T_lo != 0] forced to 0 / 1;
// FAULT_NO_SUBQ: final conditional subtract of q in the reduction removed; FAULT_HALVE_ALWAYS:
// GS sum halved even when cfg_halve = 0; FAULT_SWAP_XY: butterfly operands x and y swapped;
// FAULT_IGNORE_SLOT: every request uses modulus slot 0.
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
// each sum and one for each correction; the sign of the corrected value picks the result.
module tl_addsub #(parameter integer W = 32) (
    input  wire [W-1:0] a, b, q,
    output wire [W-1:0] s, d
);
    wire [W:0]   sum = {1'b0, a} + {1'b0, b};
    wire [W+1:0] sq  = {1'b0, sum} - {2'b0, q};
    wire [W:0]   df  = {1'b0, a} - {1'b0, b};
    wire [W-1:0] dq  = df[W-1:0] + q;
    assign s = sq[W+1] ? sum[W-1:0] : sq[W-1:0];
    assign d = df[W] ? dq : df[W-1:0];
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

module tile_thu #(parameter integer TREN_MANG = 3,
                  parameter integer LEAF_PD   = `TL_LEAF_PD_DEFAULT,
                  parameter integer IN_REG    = `TL_IN_REG_DEFAULT,
                  parameter integer EN_REG    = `TL_EN_REG_DEFAULT) (
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
    generate if (LEAF_PD < 1 || (IN_REG != 0 && IN_REG != 1) || (EN_REG != 0 && EN_REG != 1)) begin : g_bad_pipe
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
    reg        dir;
    always @(posedge clk)
        if (rst) begin md <= 3'd0; dir <= 1'b0; end
        else if (en && idle) begin md <= req_mode; dir <= req_dir; end
    wire same = (req_mode == md) && (req_dir == dir);
    wire ntt  = (md == 3'd2) || (md == 3'd4);

    // Issue slot of the on-array engine (period 3); always open with the dedicated engine.
    reg [1:0] ph;
    always @(posedge clk)
        if (rst) ph <= 2'd0;
        else if (ce) ph <= (!ARR32 || ph == 2'd2) ? 2'd0 : ph + 2'd1;

    assign req_ready = same && (!ENREG || ce) && ((md <= 3'd1) || (ntt && ph == 2'd0));
    wire fire = en && req_valid && req_ready;
    wire f01  = fire && (md <= 3'd1);

    // Request as the datapath sees it: the ports, or one register stage after acceptance (IN_REG).
    wire        rq_ntt, rq_01, rq_slot;
    wire [63:0] rq_data;
    wire [31:0] rq_root;
    wire [7:0]  rq_tag;
    wire [1:0]  rq_sign;
    generate if (INREG) begin : g_in_reg
        reg        rn, r01, rslot;
        reg [63:0] rdat;
        reg [31:0] rroot;
        reg [7:0]  rtag;
        reg [1:0]  rsign;
        always @(posedge clk) begin
            if (rst) begin rn <= 1'b0; r01 <= 1'b0; end
            else if (ce) begin rn <= fire && ntt; r01 <= f01; end
            if (ce) begin
                rdat <= req_data; rroot <= req_root; rtag <= req_tag; rsign <= req_sign; rslot <= `TL_SLOT(req_slot);
            end
        end
        assign rq_ntt = rn;  assign rq_01 = r01;  assign rq_data = rdat;  assign rq_slot = rslot;
        assign rq_root = rroot;  assign rq_tag = rtag;  assign rq_sign = rsign;
    end else begin : g_in_wire
        assign rq_ntt = fire && ntt;  assign rq_01 = f01;  assign rq_data = req_data;  assign rq_slot = `TL_SLOT(req_slot);
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
    tl_addsub #(.W(32)) u_as (
        .a(dir ? xin : side_t), .b(dir ? yin : t), .q(((dir ? rq_slot : slot_t) ? q1 : q0)), .s(us), .d(ud));

    // Operand stage: engine operand a1 (times w1) and side data s1 (x for CT, x + y for GS).
    reg         v1;
    reg  [31:0] a1, w1, s1;
    reg  [7:0]  g1;
    always @(posedge clk) begin
        if (rst) v1 <= 1'b0;
        else if (ce) v1 <= rq_ntt;
        if (ce) begin
            a1 <= (md == 3'd2) ? d0 : dir ? ud : yin;
            s1 <= dir ? us : xin;
            w1 <= rq_root;
            g1 <= rq_tag;
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
    wire        tv  = vd[E32];
    wire [40:0] tap = sd[E32];
    assign side_t = tap[31:0];
    wire [7:0]  tag_t = tap[39:32];
    assign slot_t = tap[40];

    // ---------------- multiplier leaves and modmul engine ----------------
    reg  [63:0]  la, lb;
    reg  [3:0]   lsa, lsb;
    wire [131:0] lp;
    wire [64:0]  lf;
    tl_leaves #(.PD(LEAF_PD)) leaves (.clk(clk), .en(ce), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(lp), .f(lf));

    wire [31:0] A32, B32, r32;
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
        assign A32 = (vs[FUSE] | vs[2*FUSE]) ? lf[31:0] : a1;
        assign B32 = vs[2*FUSE] ? ((ks[2*FUSE]) ? q1 : q0) : vs[FUSE] ? ((ks[FUSE]) ? qi1 : qi0) : w1;
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
        assign A32 = a1;
        assign B32 = w1;
        assign r32 = r32r;
    end endgenerate
    assign t = r32;

    // Leaf operands: mode 0/1 request or the modmul engine, both on the fused 32x32 multiplier.
    wire sa01 = (md == 3'd1) | rq_sign[0];
    wire sb01 = (md == 3'd1) | rq_sign[1];
    always @* begin
        if (md <= 3'd1) begin
            la  = {d0[31:16], d0[15:0], d0[31:16], d0[15:0]};
            lb  = {d1[15:0], d1[31:16], d1[31:16], d1[15:0]};
            lsa = {sa01, 1'b0, sa01, 1'b0};
            lsb = {1'b0, sb01, sb01, 1'b0};
        end else begin
            la  = {A32[31:16], A32[15:0], A32[31:16], A32[15:0]};
            lb  = {B32[15:0], B32[31:16], B32[31:16], B32[15:0]};
            lsa = 4'd0;
            lsb = 4'd0;
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
    wire [31:0] z0 = (md == 3'd2) ? t : dir ? gs0 : us;
    wire [31:0] z1 = (md == 3'd2) ? 32'd0 : dir ? t : ud;

    // Mode 0/1: operands presented in cycle 0, fused product in cycle FUSE.
    reg  [FUSE:1] v01;
    wire [7:0] tag01;
    always @(posedge clk)
        if (rst) v01 <= {FUSE{1'b0}};
        else if (ce) v01 <= {v01[FUSE-1:1], rq_01};
    tl_delay #(.W(8), .D(FUSE)) d_tag01 (.clk(clk), .en(ce), .d(rq_tag), .q(tag01));
    wire [31:0] fft32 = lf[47:16] + {31'd0, ~floor_r & lf[15]};

    wire        emit  = v01[FUSE] | tv;
    wire [64:0] edata = v01[FUSE] ? ((md == 3'd0) ? lf : {33'd0, fft32}) : {1'b0, z1, z0};
    wire [7:0]  etag  = v01[FUSE] ? tag01 : tag_t;

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
module tile_thu_top #(parameter integer TREN_MANG = 3,
                      parameter integer IN_REG    = `TL_IN_REG_DEFAULT,
                      parameter integer EN_REG    = `TL_EN_REG_DEFAULT) (
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
    tile_thu #(.TREN_MANG(TREN_MANG), .IN_REG(IN_REG), .EN_REG(EN_REG)) u_tile (
        .clk(clk), .rst(rst), .en(en), .idle(idle),
        .cfg_we(cfg_we), .cfg_slot(cfg_slot), .cfg_q(cfg_q), .cfg_qinv(cfg_qinv),
        .cfg_floor(cfg_floor), .cfg_halve(cfg_halve),
        .req_valid(req_valid), .req_ready(req_ready), .req_mode(req_mode), .req_dir(req_dir), .req_slot(req_slot),
        .req_sign(req_sign), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));
endmodule
