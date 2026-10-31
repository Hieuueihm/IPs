// tile_thu: DRAFT of the tile test block (spec/FlexTransform/2.0/10_hop_dong_tile.md, single NTT lane).
// Written to get early numbers for the reduction decision; not the acceptance RTL.
//
// One NTT butterfly lane per tile. A request is one modmul (mode 2) or one butterfly (mode 4)
// with fixed operand slots: x = d0, y = d1, w = r0. Pairing coefficients for CT/GS and placing
// results is done by the core, not here.
//
// Lane 16 (any odd q < 2^16 on the array, or only 3329/12289 with a fixed reducer) and lane 32
// (on the array, or a general dedicated Montgomery) are chosen independently:
//   TREN_MANG = 1: architecture v1. Both lanes on the multipliers. Lane 16: the 3 Montgomery passes
//     run on 3 different leaves (T on leaf 0, m = T_lo*q' on leaf 1, m*q on leaf 2), one modmul per
//     cycle. Lane 32: the 4 leaves fused, 3 passes (T, m, m*q), one modmul every 3 cycles.
//   TREN_MANG = 3: baseline of hypothesis 2. Lane 16 as variant 1; lane 32: 1 general 32-bit
//     Montgomery (behavioral *), one modmul per cycle.
//   TREN_MANG = 2: measurement point (former hybrid). Lane 16: one fixed 3329/12289 shift-add
//     reducer after leaf 0; lane 32 as variant 1.
//   TREN_MANG = 0: measurement point, all dedicated. Lane 16 as variant 2, lane 32 as variant 3.
//
// Static schedule: the lane-32 on-array engine accepts a new op every 3 cycles; its leaf pass
// is picked by delayed valid bits. Every register is held when en = 0; latency per mode is
// fixed and does not depend on data.

// Fault hooks for the testbench self-check (11_kiem_thu_tile.md, group C). Never defined in a
// normal build. FAULT_NO_NZ / FAULT_NZ_ONE: carry bit [T_lo != 0] forced to 0 / 1;
// FAULT_NO_SUBQ: final conditional subtract of q removed; FAULT_HALVE_ALWAYS: GS sum halved
// even when cfg_halve = 0; FAULT_SWAP_XY: butterfly operands x and y swapped.
`ifdef FAULT_NO_NZ
`define TT_NZ(b) 1'b0
`elsif FAULT_NZ_ONE
`define TT_NZ(b) 1'b1
`else
`define TT_NZ(b) (b)
`endif
`ifdef FAULT_NO_SUBQ
`define TT_GE(u, q) 1'b0
`else
`define TT_GE(u, q) ((u) >= (q))
`endif

// En-gated delay line, no reset (maps to SRL).
module tt_delay #(parameter integer W = 1, D = 1) (
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

// 2x2 array of 16x16 sign-select leaves, 3 registers per leaf (in, M, P), plus the
// two-stage fused 32x32 combine. p: leaf k product in p[33k+:33] (cycle +3).
// f: exact 65-bit fused product of leaves 0..3 (cycle +5).
// Fused leaf map: 0 = lo*lo, 1 = hi*hi, 2 = lo(a)*hi(b), 3 = hi(a)*lo(b).
module tt_leaves (
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
        reg [32:0] mr, pr;
        wire [32:0] prod;
        mul_ss #(.W(16), .IMPL("EXT")) u_mul (.a(ar), .b(br), .a_signed(sar), .b_signed(sbr), .p(prod));
        always @(posedge clk)
            if (en) begin
                ar <= a[16*k+:16]; br <= b[16*k+:16]; sar <= sa[k]; sbr <= sb[k];
                mr <= prod; pr <= mr;
            end
        assign p[33*k+:33] = pr;
    end endgenerate

    reg [33:0] xsum;
    reg [64:0] cat;
    always @(posedge clk)
        if (en) begin
            xsum <= {p[2*33+32], p[2*33+:33]} + {p[3*33+32], p[3*33+:33]};
            cat   <= {p[1*33+:33], p[0+:32]};
            f     <= cat + {{15{xsum[33]}}, xsum, 16'b0};
        end
endmodule

// Butterfly lane: pre stage -> engine (outside, latency L16 or L32) -> post stage.
// kind 0: plain modmul, o0 = Mont(y, w).
// kind 1: CT, (o0, o1) = (x + t, x - t), t = Mont(y, w).
// kind 2: GS, (o0, o1) = (halve ? (x + y)/2 : x + y, Mont(x - y, w)).
module tt_bf #(parameter integer WD = 32, WA = 64, WS = 10, L16 = 13, L32 = 21) (
    input  wire          clk, rst, en, lane32, halve,
    input  wire [WD-1:0] q,
    input  wire          iv,
    input  wire [1:0]    ik,
    input  wire [WD-1:0] ix, iy, iw,
    input  wire [WA-1:0] iaux,
    input  wire [WS-1:0] isb,
    output reg           ev,
    output reg  [WD-1:0] ea, ew,
    input  wire [WD-1:0] et,
    output reg           ov,
    output reg  [WD-1:0] o0, o1,
    output reg  [WA-1:0] oaux,
    output reg  [WS-1:0] osb
);
    function [WD-1:0] addq(input [WD-1:0] a, input [WD-1:0] b);
        reg [WD:0] s;
        begin
            s = {1'b0, a} + {1'b0, b};
            addq = (s >= {1'b0, q}) ? s - {1'b0, q} : s[WD-1:0];
        end
    endfunction
    function [WD-1:0] subq(input [WD-1:0] a, input [WD-1:0] b);
        begin
            subq = (a >= b) ? a - b : a - b + q;
        end
    endfunction
    function [WD-1:0] half(input [WD-1:0] s);
        reg [WD:0] t;
        begin
            t = {1'b0, s} + (s[0] ? {1'b0, q} : {(WD+1){1'b0}});
            half = t[WD:1];
        end
    endfunction

    localparam integer WT = WD + 2 + WA + WS;
    reg [WD-1:0] eo;
    reg [1:0]    ek;
    reg [WA-1:0] eaux;
    reg [WS-1:0] esb;
    always @(posedge clk) begin
        if (rst) ev <= 1'b0;
        else if (en) ev <= iv;
        if (en) begin
            ea   <= (ik == 2'd2) ? subq(ix, iy) : iy;
            ew   <= iw;
            eo   <= (ik == 2'd2) ? addq(ix, iy) : ix;
            ek   <= ik;
            eaux <= iaux;
            esb  <= isb;
        end
    end

    // Side data waits for the engine; tap by lane width.
    reg [WT-1:0] dl [1:L32];
    reg [L32:1]  vl;
    integer i;
    always @(posedge clk) begin
        if (rst) vl <= {L32{1'b0}};
        else if (en) vl <= {vl[L32-1:1], ev};
        if (en) begin
            dl[1] <= {eo, ek, eaux, esb};
            for (i = 2; i <= L32; i = i + 1) dl[i] <= dl[i-1];
        end
    end
    wire          dv  = lane32 ? vl[L32] : vl[L16];
    wire [WT-1:0] tap = lane32 ? dl[L32] : dl[L16];
    wire [WD-1:0] dox;
    wire [1:0]    dk;
    wire [WA-1:0] daux;
    wire [WS-1:0] dsb;
    assign {dox, dk, daux, dsb} = tap;

    always @(posedge clk) begin
        if (rst) ov <= 1'b0;
        else if (en) ov <= dv;
        if (en) begin
            case (dk)
                2'd1:    begin o0 <= addq(dox, et); o1 <= subq(dox, et); end
`ifdef FAULT_HALVE_ALWAYS
                2'd2:    begin o0 <= half(dox); o1 <= et; end
`else
                2'd2:    begin o0 <= halve ? half(dox) : dox; o1 <= et; end
`endif
                default: begin o0 <= et; o1 <= {WD{1'b0}}; end
            endcase
            oaux <= daux;
            osb  <= dsb;
        end
    end
endmodule

module tile_thu #(parameter integer TREN_MANG = 1) (
    input  wire         clk, rst, en,
    output wire         idle,
    input  wire         cfg_we, cfg_lane32,
    input  wire [31:0]  cfg_q, cfg_qinv,
    input  wire         cfg_floor, cfg_halve,
    input  wire         req_valid,
    output wire         req_ready,
    input  wire [2:0]   req_mode,
    input  wire         req_dir,
    input  wire [1:0]   req_sign,
    input  wire [63:0]  req_data,
    input  wire [31:0]  req_root,
    input  wire [7:0]   req_tag,
    output wire         rsp_valid,
    output wire [64:0]  rsp_data,
    output wire [7:0]   rsp_tag
);
    localparam integer ARR16 = (TREN_MANG == 1) || (TREN_MANG == 3);   // lane-16 reduction on leaves 0..2
    localparam integer ARR32 = (TREN_MANG == 1) || (TREN_MANG == 2);   // lane-32 reduction on the fused leaves
    localparam integer P32  = ARR32 ? 3 : 1;
    localparam integer LM16 = ARR16 ? 13 : 7;
    localparam integer LM32 = ARR32 ? 21 : 13;

    // ---------------- constants register ----------------
    reg        lane32, floor_r, halve_r, p3329;
    reg [31:0] q, qinv;
    reg [6:0]  inflight;
    assign idle = (inflight == 7'd0);
    always @(posedge clk)
        if (rst) begin
            lane32 <= 1'b0; floor_r <= 1'b0; halve_r <= 1'b0; p3329 <= 1'b0;
            q <= 32'd0; qinv <= 32'd0;
        end else if (en && cfg_we && idle) begin
            lane32 <= cfg_lane32; floor_r <= cfg_floor; halve_r <= cfg_halve;
            p3329 <= (cfg_q == 32'd3329);
            q <= cfg_q; qinv <= cfg_qinv;
        end

    // ---------------- request side ----------------
    // Mode and direction follow the request while idle and freeze while busy. A request
    // whose mode or direction differs from the latched value waits (spec 10, 4.2), so
    // the idle flag stays off the request path.
    reg  [2:0] md_r;
    reg        dir_r;
    always @(posedge clk)
        if (rst) begin md_r <= 3'd0; dir_r <= 1'b0; end
        else if (en && idle) begin md_r <= req_mode; dir_r <= req_dir; end
    wire [2:0] md   = md_r;
    wire       dir  = dir_r;
    wire       same = (req_mode == md_r) && (req_dir == dir_r);
    wire       ntt  = (md == 3'd2) || (md == 3'd4);

    // Issue slot of the lane-32 on-array engine (period 3); always open otherwise.
    reg [1:0] ph;
    wire      slot = (ph == 2'd0);
    always @(posedge clk)
        if (rst) ph <= 2'd0;
        else if (en) ph <= (!lane32 || ph >= P32 - 1) ? 2'd0 : ph + 2'd1;

    assign req_ready = !same ? 1'b0 : (md <= 3'd1) ? 1'b1 : ntt && slot;
    wire fire = en && req_valid && req_ready;
    wire f01  = fire && (md <= 3'd1);

    // ---------------- butterfly lane ----------------
    // Operands come from fixed slots and the latched mode only; the handshake sets the valid
    // bit alone, so it stays off the operand path and the pre-stage adder.
    wire [31:0] d0 = req_data[31:0], d1 = req_data[63:32];
`ifdef FAULT_SWAP_XY
    wire [31:0] x0 = (md == 3'd2) ? d0 : d1;
    wire [31:0] y0 = d0;
`else
    wire [31:0] x0 = d0;
    wire [31:0] y0 = (md == 3'd2) ? d0 : d1;
`endif
    wire [1:0]  k0 = (md == 3'd2) ? 2'd0 : dir ? 2'd2 : 2'd1;

    wire        ev0, ov0;
    wire [31:0] ea0, ew0, et0, o00, o01;
    wire [0:0]  oaux0;
    wire [7:0]  osb0;
    tt_bf #(.WD(32), .WA(1), .WS(8), .L16(LM16), .L32(LM32)) bf0 (
        .clk(clk), .rst(rst), .en(en), .lane32(lane32), .halve(halve_r), .q(q),
        .iv(fire && ntt), .ik(k0), .ix(x0), .iy(y0), .iw(req_root), .iaux(1'b0), .isb(req_tag),
        .ev(ev0), .ea(ea0), .ew(ew0), .et(et0),
        .ov(ov0), .o0(o00), .o1(o01), .oaux(oaux0), .osb(osb0));

    // ---------------- multiplier leaves and modmul engines ----------------
    reg  [63:0]  la, lb;
    reg  [3:0]   lsa, lsb;
    wire [131:0] lp;
    wire [64:0]  lf;
    tt_leaves leaves (.clk(clk), .en(en), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(lp), .f(lf));

    wire [31:0] A32, B32;     // fused operands for lane 32
    wire [63:0] A16, B16;     // leaf operands for lane 16, leaf k at [16k+:16]
    wire [15:0] r16;
    wire [31:0] r32;
    assign et0 = lane32 ? r32 : {16'd0, r16};

    generate if (ARR16) begin : g_arr16
        // Lane 16: T on leaf 0 at c, m = T_lo*q' on leaf 1 at c+4, m*q on leaf 2 at c+8.
        reg  [15:0] pd0, pd1;
        reg  [16:0] u;
        reg  [15:0] r;
        wire [16:0] th;
        always @(posedge clk)
            if (en) begin
                pd0 <= lp[15:0];
                pd1 <= lp[33+:16];
                u   <= {1'b0, th[15:0]} + {1'b0, lp[66+16+:16]} + `TT_NZ(th[16]);
                r   <= `TT_GE(u, {1'b0, q[15:0]}) ? u - {1'b0, q[15:0]} : u[15:0];
            end
        tt_delay #(.W(17), .D(8)) d_th (.clk(clk), .en(en), .d({|lp[15:0], lp[31:16]}), .q(th));
        assign A16 = {16'd0, pd1, pd0, ea0[15:0]};
        assign B16 = {16'd0, q[15:0], qinv[15:0], ew0[15:0]};
        assign r16 = r;
    end else begin : g_ded16
        // Lane 16: leaf 0 computes T; one fixed 3329/12289 reducer, 4 stages.
        reg  [15:0] m1, th1, th2;
        reg         nz1, nz2;
        reg  [29:0] mq2;
        reg  [16:0] u3;
        reg  [15:0] r4;
        wire [31:0] t  = lp[31:0];
        wire [15:0] qc = p3329 ? 16'd3329 : 16'd12289;
        always @(posedge clk)
            if (en) begin
                m1  <= p3329 ? (t[15:0] << 12) - (t[15:0] << 10) + (t[15:0] << 8) - t[15:0]
                             : (t[15:0] << 14) - (t[15:0] << 12) - t[15:0];
                th1 <= t[31:16]; nz1 <= |t[15:0];
                mq2 <= p3329 ? ({14'd0, m1} << 12) - ({14'd0, m1} << 10) + ({14'd0, m1} << 8) + {14'd0, m1}
                             : ({14'd0, m1} << 14) - ({14'd0, m1} << 12) + {14'd0, m1};
                th2 <= th1; nz2 <= nz1;
                u3  <= {1'b0, th2} + {3'd0, mq2[29:16]} + `TT_NZ(nz2);
                r4  <= `TT_GE(u3, {1'b0, qc}) ? u3 - {1'b0, qc} : u3[15:0];
            end
        assign A16 = {48'd0, ea0[15:0]};
        assign B16 = {48'd0, ew0[15:0]};
        assign r16 = r4;
    end endgenerate

    generate if (ARR32) begin : g_arr32
        // Lane 32, fused leaves: T at c, m at c+7, m*q at c+14 (period 3).
        reg  [14:1] vs32;
        reg  [31:0] fd1, fd2, r32r;
        reg  [32:0] u32;
        wire [32:0] th32;
        always @(posedge clk) begin
            if (rst) vs32 <= 14'd0;
            else if (en) vs32 <= {vs32[13:1], ev0};
            if (en) begin
                fd1 <= lf[31:0]; fd2 <= fd1;
                u32  <= {1'b0, th32[31:0]} + {1'b0, lf[63:32]} + `TT_NZ(th32[32]);
                r32r <= `TT_GE(u32, {1'b0, q}) ? u32 - {1'b0, q} : u32[31:0];
            end
        end
        tt_delay #(.W(33), .D(14)) d_th32 (.clk(clk), .en(en), .d({|lf[31:0], lf[63:32]}), .q(th32));
        assign A32 = (vs32[7] | vs32[14]) ? fd2 : ea0;
        assign B32 = vs32[14] ? q : vs32[7] ? qinv : ew0;
        assign r32 = r32r;
    end else begin : g_ded32
        // Lane 32: fused leaves compute T; general Montgomery with behavioral *.
        reg  [31:0] ma, mp1, mp2, r32r;
        reg  [63:0] mq1, mq2, mq3;
        reg  [32:0] u32;
        wire [32:0] th32;
        always @(posedge clk)
            if (en) begin
                ma   <= lf[31:0];
                mp1  <= ma * qinv;
                mp2  <= mp1;
                mq1  <= mp2 * q;
                mq2  <= mq1;
                mq3  <= mq2;
                u32  <= {1'b0, th32[31:0]} + {1'b0, mq3[63:32]} + `TT_NZ(th32[32]);
                r32r <= `TT_GE(u32, {1'b0, q}) ? u32 - {1'b0, q} : u32[31:0];
            end
        tt_delay #(.W(33), .D(6)) d_th32 (.clk(clk), .en(en), .d({|lf[31:0], lf[63:32]}), .q(th32));
        assign A32 = ea0;
        assign B32 = ew0;
        assign r32 = r32r;
    end endgenerate

    // Leaf operand select: mode 0/1 request, fused lane-32 engine, or lane-16 engine.
    wire sa01 = (md == 3'd1) | req_sign[0];
    wire sb01 = (md == 3'd1) | req_sign[1];
    always @* begin
        if (md <= 3'd1) begin
            la  = {req_data[31:16], req_data[15:0], req_data[31:16], req_data[15:0]};
            lb  = {req_data[47:32], req_data[63:48], req_data[63:48], req_data[47:32]};
            lsa = {sa01, 1'b0, sa01, 1'b0};
            lsb = {1'b0, sb01, sb01, 1'b0};
        end else if (lane32) begin
            la  = {A32[31:16], A32[15:0], A32[31:16], A32[15:0]};
            lb  = {B32[15:0], B32[31:16], B32[31:16], B32[15:0]};
            lsa = 4'd0;
            lsb = 4'd0;
        end else begin
            la  = A16;
            lb  = B16;
            lsa = 4'd0;
            lsb = 4'd0;
        end
    end

    // ---------------- mode 0/1 path ----------------
    reg  [5:1] v01;
    wire [7:0] tag01;
    always @(posedge clk)
        if (rst) v01 <= 5'd0;
        else if (en) v01 <= {v01[4:1], f01};
    tt_delay #(.W(8), .D(5)) d_tag01 (.clk(clk), .en(en), .d(req_tag), .q(tag01));

    // ---------------- result ----------------
    wire [31:0] fft32 = lf[47:16] + {31'd0, ~floor_r & lf[15]};
    wire        emit  = v01[5] | ov0;
    wire [64:0] ez    = v01[5] ? ((md_r == 3'd0) ? lf : {33'd0, fft32}) : {1'b0, o01, o00};
    wire [7:0]  etag  = v01[5] ? tag01 : osb0;

    reg         rv;
    reg [64:0]  rd;
    reg [7:0]   rt;
    always @(posedge clk) begin
        if (rst) rv <= 1'b0;
        else if (en) rv <= emit;
        if (en && emit) begin rd <= ez; rt <= etag; end
    end
    assign rsp_valid = rv & en;
    assign rsp_data  = rd;
    assign rsp_tag   = rt;

    always @(posedge clk)
        if (rst) inflight <= 7'd0;
        else inflight <= inflight + {6'd0, fire} - {6'd0, rsp_valid};
endmodule

// Measurement wrapper: every input and output registered (spec 10, section 8).
module tile_thu_top #(parameter integer TREN_MANG = 1) (
    input  wire         clk, rst_i, en_i,
    output reg          idle_o,
    input  wire         cfg_we_i, cfg_lane32_i,
    input  wire [31:0]  cfg_q_i, cfg_qinv_i,
    input  wire         cfg_floor_i, cfg_halve_i,
    input  wire         req_valid_i,
    output reg          req_ready_o,
    input  wire [2:0]   req_mode_i,
    input  wire         req_dir_i,
    input  wire [1:0]   req_sign_i,
    input  wire [63:0]  req_data_i,
    input  wire [31:0]  req_root_i,
    input  wire [7:0]   req_tag_i,
    output reg          rsp_valid_o,
    output reg  [64:0]  rsp_data_o,
    output reg  [7:0]   rsp_tag_o
);
    reg         rst, en, cfg_we, cfg_lane32, cfg_floor, cfg_halve, req_valid, req_dir;
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
        rst <= rst_i; en <= en_i; cfg_we <= cfg_we_i; cfg_lane32 <= cfg_lane32_i;
        cfg_q <= cfg_q_i; cfg_qinv <= cfg_qinv_i; cfg_floor <= cfg_floor_i; cfg_halve <= cfg_halve_i;
        req_valid <= req_valid_i; req_mode <= req_mode_i; req_dir <= req_dir_i; req_sign <= req_sign_i;
        req_data <= req_data_i; req_root <= req_root_i; req_tag <= req_tag_i;
        idle_o <= idle; req_ready_o <= req_ready; rsp_valid_o <= rsp_valid;
        rsp_data_o <= rsp_data; rsp_tag_o <= rsp_tag;
    end
    tile_thu #(.TREN_MANG(TREN_MANG)) u_tile (
        .clk(clk), .rst(rst), .en(en), .idle(idle),
        .cfg_we(cfg_we), .cfg_lane32(cfg_lane32), .cfg_q(cfg_q), .cfg_qinv(cfg_qinv),
        .cfg_floor(cfg_floor), .cfg_halve(cfg_halve),
        .req_valid(req_valid), .req_ready(req_ready), .req_mode(req_mode), .req_dir(req_dir),
        .req_sign(req_sign), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));
endmodule
