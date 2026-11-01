// ntt_core: minimal NTT core of FlexTransform v1. One polynomial, opcodes NTT (0x5) and NTT ngược (0x6), profiles 0
// (q = 12289, logn 3..10), 1 (3329, logn 3..8, 7 layers at N = 256) and 2 (8380417, logn 8), memory region A only,
// simple host line port. Schedule and tables: model/ntt_core_sched.py, scripts/gen_ntt_core.py (ntt_core_gen.sv).
//
// Blocks: region A (flex_banked_scratch, 64 banks x 128 rows x 16 bit, format 4: coefficient c in cells 2c, 2c + 1),
// 4 root-pack ROM banks, the structured bank -> tile network (hdl/net/ntt_bank_net_s.sv, 4 pack banks), 16 on-array
// tiles (hdl/tile/tile_thu.sv, TREN_MANG = 1, PHASE = t / 6).
//
// Per layer (distance h = 2^hlog) tile t runs butterflies i = p_t xor K(k), k = 0 .. 2^kdim - 1 (layer table, loaded
// into registers one layer ahead). Tile t accepts in cycles A with (PHASE + A) mod 3 == 0 (gph counts the same cycles
// as the tiles' issue counters). Pipeline per butterfly, e = first read cycle:
//   e - 1  address stage: i, c, superbanks (one-hot), rows, root pack            -> s0
//   e      RAM read x (and y), pack ROM read; same superbank: x only            -> s1 (with network selects)
//   e + 1  network selects; same superbank: RAM read y, pack read, x captured    -> s2
//   e + 2  tile accepts (same superbank: network selects for y and root, hold x) -> s3
//   e + 3  same superbank: tile accepts
// Result at A + 19: write select of x and y (same superbank: y one cycle later); RAM write the next cycle. Layers
// overlap: the next layer starts a table-given number of cycles after the current one (model/ntt_core_overlap.py), and
// each result takes its write address from a per-tile FIFO filled at issue.
// INTT: tiles halve the sum branch and the inverse roots carry 2^-1, so no normalisation pass (spec 2.0, 03).
//
// Host port: only while idle. Line l (128 bit) = cells 8l .. 8l + 7, low cell in the low bits. Cell 8l + j always sits
// in a bank whose low 3 bits are j, so lane j of a line only ever reaches the 8 banks {g, j}.
`ifndef NTT_ROM_DIR
`define NTT_ROM_DIR "hdl/core_ntt/"
`endif

// One root-pack ROM bank: 384 rows x 96 bit (profile 0 / 1 / 2, forward then inverse; scripts/gen_ntt_core.py).
module ntt_core_pack_rom #(parameter FILE = "root_pack_b0.mem") (
    input  wire        clk,
    input  wire [8:0]  addr,
    output reg  [95:0] q
);
    (* rom_style = "block" *) reg [95:0] rom [0:383];
    initial $readmemh(FILE, rom);
    always @(posedge clk) q <= rom[addr];
endmodule

module ntt_core (
    input  wire         clk, rst,
    input  wire         load_valid,
    input  wire [9:0]   load_line,
    input  wire [127:0] load_data,
    input  wire         read_valid,
    input  wire [9:0]   read_line,
    output reg          read_rsp_valid,
    output reg  [127:0] read_data,
    input  wire         start,
    input  wire         start_inverse,
    input  wire [1:0]   start_profile,
    input  wire [3:0]   start_logn,
    output wire         busy,
    output reg          done,
    output reg          error,
    output reg  [31:0]  cycles
);
    localparam [1:0] IDLE = 2'd0, CFG = 2'd1, RUN = 2'd2, FIN = 2'd3;
    reg  [1:0] state;
    reg        inverse;
    reg  [1:0] profile;
    reg  [3:0] logn, hlog, hmin;
    assign busy = (state != IDLE);

    // ---------------- constants and layer table ----------------
    wire [31:0] cq, cqinv, croot1;
    wire [8:0]  pbase;
    ntt_core_consts u_consts (.profile(profile), .inverse(inverse), .q(cq), .qinv(cqinv), .root1(croot1), .pbase(pbase));
    // The table is read for the first layer in CFG and for the next layer during RUN, registered at the switch. Layers
    // overlap: the next one starts delta cycles after the current one (model/ntt_core_overlap.py), without waiting for
    // the writes of the current one; results find their addresses in a per-tile FIFO.
    wire          layer_sw;
    wire [3:0]    hnext = inverse ? hlog + 4'd1 : hlog - 4'd1;
    wire [15:0]   n_tv;
    wire [16*9-1:0] n_lp;
    wire [5*9-1:0]  n_kb;
    wire [2:0]    n_kdim;
    wire          n_same;
    wire [7:0]    n_delta;
    ntt_core_layer_rom u_layer (.ms2(hmin == 4'd1), .inverse(inverse), .logn(logn), .hlog(state == RUN ? hnext : hlog),
        .tv(n_tv), .p(n_lp), .kb(n_kb), .kdim(n_kdim), .same(n_same), .delta(n_delta));
    reg  [15:0]   tv;
    reg  [16*9-1:0] lp;
    reg  [5*9-1:0]  kb;
    reg  [5:0]    bf_per_tile;
    reg           same;
    reg  [7:0]    delta, lt;                    // cycles to the next layer's start, cycles since this layer's start
    always @(posedge clk)
        if (state == CFG || layer_sw) begin
            tv <= n_tv; lp <= n_lp; kb <= n_kb; bf_per_tile <= 6'd1 << n_kdim; same <= n_same; delta <= n_delta;
        end
    reg  [13:0] cmd_total;                      // butterflies of the command = layers x N / 2
    reg  [13:0] wdone;                          // butterflies fully written (last write select issued)

    // issue phase, aligned with the tiles' counters (same reset, en always 1)
    reg [1:0] gph;
    always @(posedge clk)
        if (rst) gph <= 2'd0;
        else gph <= (gph == 2'd2) ? 2'd0 : gph + 2'd1;

    function [9:0] ins0(input [8:0] i, input [3:0] hl);          // c: a 0 inserted at bit hl of i
        reg [9:0] m, v;
        begin
            m = (10'd1 << hl) - 10'd1;
            v = {1'b0, i};
            ins0 = ((v & ~m) << 1) | (v & m);
        end
    endfunction
    function [4:0] sbank(input [9:0] c);                         // superbank of coefficient c = bank(2c) >> 1
        reg [10:0] k;
        reg [5:0]  b;
        begin
            k = {c, 1'b0};
            b = {k[5:4] ^ k[7:6] ^ k[9:8], k[3:0]};
            sbank = b[5:1];
        end
    endfunction
    function [8:0] enumi(input [8:0] p, input [4:0] k, input [5*9-1:0] basis);
        integer j;
        begin
            enumi = p;
            for (j = 0; j < 5; j = j + 1)
                if (k[j]) enumi = enumi ^ basis[9*j +: 9];
        end
    endfunction

    // ---------------- per-tile issue and write address FIFO ----------------
    reg         layer_on;
    reg  [15:0] s0v, s1v, s2v, s3v;
    reg  [15:0] s0m, s1m, s2m, s3m;             // same superbank, per butterfly
    reg  [16*5-1:0] s0sx, s0sy;                 // superbanks (for the network selects)
    reg  [16*32-1:0] s0xo, s0yo, s1yo;          // superbanks one-hot, gated by valid (for the RAM requests)
    reg  [16*7-1:0] s0rx, s0ry, s1ry;
    reg  [16*4-1:0] s0po, s1po;                 // pack bank one-hot, gated (root 1 reads no pack)
    reg  [16*9-1:0] s0pr, s1pr;
    reg  [16*4-1:0] s0rs, s1rs, s2rs;
    wire [16*3-1:0] nsel_xlo, nsel_xhi, nsel_ylo, nsel_yhi;
    reg  [16*3-1:0] s1xlo, s1xhi, s1ylo, s1yhi, s2ylo, s2yhi;
    ntt_core_sel u_sel (.sx(s0sx), .sy(s0sy), .sel_xlo(nsel_xlo), .sel_xhi(nsel_xhi), .sel_ylo(nsel_ylo), .sel_yhi(nsel_yhi));

    wire [15:0] rsp_valid;
    reg  [15:0] ypend;                          // same superbank: y write select pending for the next cycle
    reg  [15:0] hm;                             // head of the address FIFO: same-superbank flag
    reg  [16*32-1:0] hxo, hyo, ysbo;            // head superbanks one-hot, y pending
    reg  [16*7-1:0] hrx, hry, yrow;
    reg  [16*5-1:0] kr;
    reg  [15:0] rdone;
    wire [15:0] fin_now;                        // butterflies whose last write select is this cycle

    genvar t;
    generate for (t = 0; t < 16; t = t + 1) begin : g_issue
        localparam integer PH = t / 6;
        wire       go = layer_on && tv[t] && !rdone[t] && (((PH + gph + same) % 3) == 0);
        wire [8:0] i  = enumi(lp[9*t +: 9], kr[5*t +: 5], kb);
        wire [9:0] cx = ins0(i, hlog);
        wire [9:0] cy = cx | (10'd1 << hlog);
        wire [9:0] r  = (10'd1 << (logn - 4'd1 - hlog)) + (cx >> (hlog + 4'd1));
        wire [8:0] pos = r[9:1] - 9'd1;
        wire       r1 = (hlog == logn - 4'd1);
        // write addresses in issue order: 16 entries (at most 8 butterflies of a tile are in flight)
        reg [24:0] fifo [0:15];
        reg [3:0]  wp, rp;
        wire [24:0] fh = fifo[rp];
        always @(posedge clk) begin
            // address stage
            s0v[t] <= !rst && go;
            s0m[t] <= same;
            s0sx[5*t +: 5] <= sbank(cx);  s0rx[7*t +: 7] <= {2'b0, cx[9:5]};
            s0sy[5*t +: 5] <= sbank(cy);  s0ry[7*t +: 7] <= {2'b0, cy[9:5]};
            s0xo[32*t +: 32] <= (!rst && go) ? (32'd1 << sbank(cx)) : 32'd0;
            s0yo[32*t +: 32] <= (!rst && go) ? (32'd1 << sbank(cy)) : 32'd0;
            s0po[4*t +: 4] <= (!rst && go && !r1) ? (4'd1 << pos[1:0]) : 4'd0;
            s0pr[9*t +: 9] <= {2'b0, pos[8:2]} + pbase;
            s0rs[4*t +: 4] <= r1 ? 4'd8 : {1'b0, pos[1:0], r[0]};
            if (rst || !layer_on || layer_sw) kr[5*t +: 5] <= 5'd0;
            else if (go) kr[5*t +: 5] <= kr[5*t +: 5] + 5'd1;
            if (rst || !layer_on || layer_sw) rdone[t] <= 1'b0;
            else if (go && ({1'b0, kr[5*t +: 5]} + 6'd1 == bf_per_tile)) rdone[t] <= 1'b1;
            // address FIFO: push at issue, pop at the result; the head is decoded into registers one cycle later
            if (rst) begin wp <= 4'd0; rp <= 4'd0; end
            else begin
                if (go) begin fifo[wp] <= {same, sbank(cx), 2'b0, cx[9:5], sbank(cy), 2'b0, cy[9:5]}; wp <= wp + 4'd1; end
                if (rsp_valid[t]) rp <= rp + 4'd1;
            end
            hm[t] <= fh[24];
            hxo[32*t +: 32] <= 32'd1 << fh[23:19];  hrx[7*t +: 7] <= fh[18:12];
            hyo[32*t +: 32] <= 32'd1 << fh[11:7];   hry[7*t +: 7] <= fh[6:0];
            ypend[t] <= !rst && rsp_valid[t] && hm[t];
            if (rsp_valid[t]) begin ysbo[32*t +: 32] <= hyo[32*t +: 32]; yrow[7*t +: 7] <= hry[7*t +: 7]; end
        end
        assign fin_now[t] = (rsp_valid[t] && !hm[t]) || ypend[t];
    end endgenerate

    // pipeline stages s1..s3 (all tiles at once)
    always @(posedge clk) begin
        s1v <= rst ? 16'd0 : s0v;
        s2v <= rst ? 16'd0 : s1v;
        s3v <= rst ? 16'd0 : s2v;
        s1m <= s0m;  s2m <= s1m;  s3m <= s2m;
        s1yo <= rst ? {16*32{1'b0}} : s0yo;
        s1po <= rst ? 64'd0 : s0po;
        s1ry <= s0ry;  s1pr <= s0pr;  s1rs <= s0rs;
        s1xlo <= nsel_xlo;  s1xhi <= nsel_xhi;  s1ylo <= nsel_ylo;  s1yhi <= nsel_yhi;
        s2ylo <= s1ylo;  s2yhi <= s1yhi;  s2rs <= s1rs;
    end

    // ---------------- memory requests ----------------
    // Per tile: RAM read x from s0; y and the root pack from s0, or from s1 when x and y share a superbank. A tile issues
    // at most every 3 cycles, so its s0 and s1 never both hold a request.
    reg  [16*32-1:0] ryo, wxo, wyo;
    reg  [16*7-1:0]  ryr, wyr;
    reg  [16*4-1:0]  ppo;
    reg  [16*9-1:0]  ppr;
    reg  [16*3-1:0]  q_ylo, q_yhi;
    reg  [16*4-1:0]  q_rs;
    reg  [15:0]      q_hold, req_valid;
    integer tw;
    always @* begin
        for (tw = 0; tw < 16; tw = tw + 1) begin
            ryo[32*tw +: 32] = (s0yo[32*tw +: 32] & {32{!s0m[tw]}}) | (s1yo[32*tw +: 32] & {32{s1m[tw]}});
            ryr[7*tw +: 7]   = (s1v[tw] && s1m[tw]) ? s1ry[7*tw +: 7] : s0ry[7*tw +: 7];
            ppo[4*tw +: 4]   = (s0po[4*tw +: 4] & {4{!s0m[tw]}}) | (s1po[4*tw +: 4] & {4{s1m[tw]}});
            ppr[9*tw +: 9]   = (s1v[tw] && s1m[tw]) ? s1pr[9*tw +: 9] : s0pr[9*tw +: 9];
            // network selects: y and root at s1, or at s2 (with x held) when same superbank
            q_ylo[3*tw +: 3] = (s2v[tw] && s2m[tw]) ? s2ylo[3*tw +: 3] : s1ylo[3*tw +: 3];
            q_yhi[3*tw +: 3] = (s2v[tw] && s2m[tw]) ? s2yhi[3*tw +: 3] : s1yhi[3*tw +: 3];
            q_rs[4*tw +: 4]  = (s2v[tw] && s2m[tw]) ? s2rs[4*tw +: 4]  : s1rs[4*tw +: 4];
            q_hold[tw]       = s2v[tw] && s2m[tw];
            req_valid[tw]    = (s2v[tw] && !s2m[tw]) || (s3v[tw] && s3m[tw]);
            // writes: x and (unless same superbank) y at the result; y one cycle later when same
            wxo[32*tw +: 32] = {32{rsp_valid[tw]}} & hxo[32*tw +: 32];
            wyo[32*tw +: 32] = ({32{rsp_valid[tw] && !hm[tw]}} & hyo[32*tw +: 32]) | ({32{ypend[tw]}} & ysbo[32*tw +: 32]);
            wyr[7*tw +: 7]   = ypend[tw] ? yrow[7*tw +: 7] : hry[7*tw +: 7];
        end
    end

    wire [63:0]     c_re, c_wen;
    wire [64*7-1:0] c_ra, c_wa;
    wire [64*3-1:0] c_wsel;
    ntt_core_route u_route (.clk(clk), .rxo(s0xo), .ryo(ryo), .rxr(s0rx), .ryr(ryr), .re(c_re), .ra(c_ra),
        .wxo(wxo), .wyo(wyo), .wxr(hrx), .wyr(wyr), .wsel(c_wsel), .wen(c_wen), .wa(c_wa));

    // root-pack ROM, 4 banks; a bank is read by every tile that needs its pack this cycle (always the same pack)
    wire [4*96-1:0] pack_rd;
    integer tt, pb;
    reg [4*9-1:0] paddr;
    always @* begin
        paddr = 0;
        for (pb = 0; pb < 4; pb = pb + 1)
            for (tt = 0; tt < 16; tt = tt + 1)
                paddr[9*pb +: 9] = paddr[9*pb +: 9] | ({9{ppo[4*tt + pb]}} & ppr[9*tt +: 9]);
    end
    ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b0.mem"})) u_rom0 (.clk(clk), .addr(paddr[0 +: 9]),  .q(pack_rd[0 +: 96]));
    ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b1.mem"})) u_rom1 (.clk(clk), .addr(paddr[9 +: 9]),  .q(pack_rd[96 +: 96]));
    ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b2.mem"})) u_rom2 (.clk(clk), .addr(paddr[18 +: 9]), .q(pack_rd[192 +: 96]));
    ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b3.mem"})) u_rom3 (.clk(clk), .addr(paddr[27 +: 9]), .q(pack_rd[288 +: 96]));

    // ---------------- region A ----------------
    reg  [63:0]     m_re, m_we;
    reg  [64*7-1:0] m_ra, m_wa;
    reg  [1023:0]   m_wd;
    wire [1023:0]   m_rd;
    wire [1023:0]   net_wd;
    wire [63:0]     net_we;
    flex_banked_scratch #(.ROW_BITS(7)) u_mem (.clk(clk), .re(m_re), .we(m_we), .ra(m_ra), .wa(m_wa), .wd(m_wd), .rd(m_rd));

    // bank of cell 8l + j = {grp(l), j}
    function [2:0] grp(input [9:0] l);
        grp = {l[2:1] ^ l[4:3] ^ l[6:5], l[0]};
    endfunction
    wire host = (state == IDLE);
    integer bk;
    always @* begin
        for (bk = 0; bk < 64; bk = bk + 1) begin
            m_re[bk] = host ? (read_valid && grp(read_line) == bk[5:3]) : c_re[bk];
            m_ra[7*bk +: 7] = host ? read_line[9:3] : c_ra[7*bk +: 7];
            m_we[bk] = host ? (load_valid && grp(load_line) == bk[5:3]) : net_we[bk];
            m_wa[7*bk +: 7] = host ? load_line[9:3] : c_wa[7*bk +: 7];
            m_wd[16*bk +: 16] = host ? load_data[16*bk[2:0] +: 16] : net_wd[16*bk +: 16];
        end
    end
    reg       rd_pend;
    reg [2:0] rgrp;
    integer jj;
    always @(posedge clk) begin
        rd_pend <= !rst && host && read_valid;
        if (host && read_valid) rgrp <= grp(read_line);
        read_rsp_valid <= !rst && rd_pend;
        if (rd_pend)
            for (jj = 0; jj < 8; jj = jj + 1) read_data[16*jj +: 16] <= m_rd[16*{rgrp, jj[2:0]} +: 16];
    end

    // ---------------- network and tiles ----------------
    wire [16*32-1:0] op_x, op_y, op_w;
    wire [16*64-1:0] tile_z;
    ntt_bank_net_s u_net (.clk(clk), .en(1'b1), .bank_rd(m_rd), .pack_rd(pack_rd),
        .sel_xlo(s1xlo), .sel_xhi(s1xhi), .sel_ylo(q_ylo), .sel_yhi(q_yhi),
        .hold_x(q_hold), .root1(croot1), .sel_root(q_rs),
        .op_x(op_x), .op_y(op_y), .op_w(op_w), .tile_z(tile_z), .wsel(c_wsel), .wen(c_wen),
        .bank_wd(net_wd), .bank_we(net_we));

    reg cfg_we;
    wire [15:0] req_ready, tile_idle;
    generate for (t = 0; t < 16; t = t + 1) begin : g_tile
        wire [64:0] rd;
        wire [7:0]  rt;
        tile_thu #(.TREN_MANG(1), .PHASE(t / 6)) u_tile (
            .clk(clk), .rst(rst), .en(1'b1), .idle(tile_idle[t]),
            .cfg_we(cfg_we), .cfg_slot(1'b0), .cfg_q(cq), .cfg_qinv(cqinv), .cfg_floor(1'b0), .cfg_halve(inverse),
            .req_valid(req_valid[t]), .req_ready(req_ready[t]), .req_mode(3'd4), .req_dir(inverse), .req_slot(1'b0),
            .req_sign(2'd0), .req_data({op_y[32*t +: 32], op_x[32*t +: 32]}), .req_root(op_w[32*t +: 32]),
            .req_tag(8'd0), .rsp_valid(rsp_valid[t]), .rsp_data(rd), .rsp_tag(rt));
        assign tile_z[64*t +: 64] = rd[63:0];
    end endgenerate

    // ---------------- command control ----------------
    function [4:0] pop16(input [15:0] v);
        integer m;
        begin
            pop16 = 5'd0;
            for (m = 0; m < 16; m = m + 1) pop16 = pop16 + {4'd0, v[m]};
        end
    endfunction
    wire [4:0] nfin = pop16(fin_now);
    wire last_layer = inverse ? (hlog == logn - 4'd1) : (hlog == hmin);
    assign layer_sw = (state == RUN) && layer_on && !last_layer && (lt == delta - 8'd1);
    wire cmd_last_write = (state == RUN) && (wdone + {9'd0, nfin} == cmd_total);
    wire bad = (start_logn < 4'd3) || (start_profile == 2'd3) ||
               (start_profile == 2'd0 && start_logn > 4'd10) || (start_profile == 2'd1 && start_logn > 4'd8) ||
               (start_profile == 2'd2 && start_logn != 4'd8);
    wire [3:0] start_hmin = (start_profile == 2'd1 && start_logn == 4'd8) ? 4'd1 : 4'd0;

    always @(posedge clk) begin
        done <= 1'b0;
        cfg_we <= 1'b0;
        if (rst) begin
            state <= IDLE; layer_on <= 1'b0; error <= 1'b0; cycles <= 32'd0; wdone <= 14'd0; lt <= 8'd0;
            inverse <= 1'b0; profile <= 2'd0; logn <= 4'd3; hlog <= 4'd0; hmin <= 4'd0; cmd_total <= 14'd0;
        end else begin
            if (busy) cycles <= cycles + 32'd1;
            case (state)
                IDLE: if (start) begin
                    cycles <= 32'd0;
                    error <= bad;
                    if (bad) done <= 1'b1;
                    else begin
                        inverse <= start_inverse; profile <= start_profile; logn <= start_logn;
                        hmin <= start_hmin;
                        hlog <= start_inverse ? start_hmin : start_logn - 4'd1;
                        cmd_total <= {10'd0, start_logn - start_hmin} << (start_logn - 4'd1);
                        state <= CFG;
                    end
                end
                // Constants are written while every tile is idle. The first layer starts at issue phase 2 (the phase the
                // overlap plan was searched at), so the table's layer distances hold.
                CFG: if (&tile_idle && gph == 2'd1) begin
                    cfg_we <= 1'b1;
                    state <= RUN;
                    layer_on <= 1'b1;
                    lt <= 8'd0;
                    wdone <= 14'd0;
                end
                RUN: begin
                    wdone <= wdone + {9'd0, nfin};
                    lt <= layer_sw ? 8'd0 : lt + 8'd1;
                    if (layer_sw) hlog <= hnext;
                    if (cmd_last_write) begin layer_on <= 1'b0; state <= FIN; end
                end
                FIN: begin                        // the last RAM write happens in this cycle
                    done <= 1'b1;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
