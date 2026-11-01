// ntt_core: minimal core of FlexTransform v1. One polynomial; opcodes NTT (0x5) and NTT ngược (0x6) for profiles 0
// (q = 12289, logn 3..10), 1 (3329, logn 3..8, 7 layers at N = 256), 2 (8380417, logn 8) and 3 (a loaded prime: any odd
// q < 2^31 with its root packs in one of 16 slots, logn 1..10, 0..2 skipped last layers; model/ntt_prime_core.py); FFT (0x0) and FFT ngược
// (0x1) in formats 0, 1, 2 (32 / 64 / 128 bit, logn 0..10). Memory region A only, simple host line port. Schedules and
// tables: model/ntt_core_sched.py, model/ntt_core_overlap.py, model/fft_core_sched.py, model/fft_wide_sched.py,
// scripts/gen_ntt_core.py (ntt_core_gen.sv).
//
// Blocks: region A (flex_banked_scratch, 64 banks x 128 rows x 16 bit; NTT format 4 and FFT format 0 keep a 32-bit
// element e in cells 2e, 2e + 1; FFT formats 1 / 2 keep limb k of element e in cells 2(L e + k), 2(L e + k) + 1, L = 2 / 4),
// 4 root-pack ROM banks (NTT packs, FFT roots), the structured bank -> tile network (hdl/net/ntt_bank_net_s.sv) and 16
// on-array tiles (hdl/tile/tile_thu.sv, TREN_MANG = 1, PHASE = t / 6). FFT runs on the tiles' own butterfly path (tile
// mode 5, at 64 / 128 bit limb by limb); the core only supplies operands, roots and write addresses.
//
// Per layer (distance h = 2^hlog) tile t runs butterflies i = p_t xor K(k), k = 0 .. 2^kdim - 1 (layer table, loaded
// into registers one layer ahead; the next layer starts delta cycles after this one).
// NTT (tile mode 4): tile t accepts in cycles A with (PHASE + A) mod 3 == 0. Pipeline, e = first read cycle:
//   e - 1  address stage: i, c, superbanks (one-hot), rows, root pack            -> s0
//   e      RAM read x (and y), pack ROM read; same superbank: x only            -> s1 (with network selects)
//   e + 1  network selects; same superbank: RAM read y, pack read, x captured    -> s2
//   e + 2  tile accepts (same superbank: network selects for y and root, hold x) -> s3
//   e + 3  same superbank: tile accepts
// Result at A + 20 (tile IN_REG = 1): write select of x and y (same superbank: y one cycle later); RAM write the next cycle. Layers
// overlap (model/ntt_core_overlap.py); each result takes its write address from a per-tile FIFO filled at issue.
// INTT: tiles halve the sum branch and the inverse roots carry 2^-1, so no normalisation pass (spec 2.0, 03).
//
// FFT: a tile issues a butterfly at g (its index registered there); everything after is a fixed offset from g, made by
// a shift register of the issue, and every address is made from the registered index. Barrier per layer on commits:
// the next layer starts the cycle after the last write select of this one.
// Format 0 (model/fft_core_sched.py): every tile issues in the same cycles, one complex butterfly per 3 cycles, the tile
// is the bank-indexed tile of the real pair. Root word read at g + 2 + (t >> 2) mod 3 into the network's root register;
// data e = g + 4: read A.re (x), B.re (y); e + 1: A.im, B.im; e + 2: tile beat 1 (A.re, B.re, wr); e + 3: beat 2 (A.im,
// B.im, wi); results e + 12, e + 13 (tile IN_REG = 1), each written (x and y) two cycles later through the tile's
// forwarding register.
// Formats 1, 2 (model/fft_wide_sched.py): limb k of an element is the format-0 element L e + k, so the format-0 rule puts
// the limb-k pair of butterfly b on tile T(b) | k: the L tiles T(b) .. T(b) + L - 1 are a block that shares the
// butterfly. Every block issues its m-th butterfly at g = m Q (Q = 6 / 12; all blocks in step) on block tile m mod L (its
// "owner"); block tile k reads limb k: x of the real parts at e + k (e = g + D), y at e + k + 1 (the network holds x one
// cycle), the imaginary parts from e + L, and its root limb {wi_k, wr_k} at a per-block lead into its root register; the
// owner takes beat j at e + 3 + j from block tile j mod L (data and root). Result beat j (limb j mod L) goes back to the
// forwarding register of block tile j mod L (one register stage, then the write address from its FIFO), which writes x
// two cycles after the result and y three cycles after. No bank, write or
// root-ROM conflicts in any layer (checked by the model), and no network source beyond the format-0 ones.
//
// Host port: only while idle. Line l (128 bit) = cells 8l .. 8l + 7, low cell in the low bits. Cell 8l + j always sits
// in a bank whose low 3 bits are j, so lane j of a line only ever reaches the 8 banks {g, j}.
// Profile 3: the host writes a slot (q, q' = -q^-1 mod 2^32, root 1 of each direction, position of the slot's first root
// pack, a multiple of 4, and logn of its tables) and the slot's root packs [GM[g], GM[2g], GM[2g + 1]] (g = 1 .. N'/2 - 1,
// position base + g - 1, one direction at a time) into rows 3072 .. 3327 of the root-pack banks. (Spec 2.0 02 lets the
// prime load read linear gm / igm tables; this minimal core takes the packs from the host, as it takes data lines.)
`ifndef NTT_ROM_DIR
`define NTT_ROM_DIR "hdl/core_ntt/"
`endif

// One root-pack bank: 3328 rows x 96 bit, two ports (NTT packs of profile 0 / 1 / 2, then FFT roots: 32 bit [95:64] = wi,
// [63:32] = wr; 64 / 128 bit one limb pair {wi_k, wr_k} per row; scripts/gen_ntt_core.py; rows 3072 .. 3327: the packs of
// profile 3, written by the host while the core is idle, through port a). Tiles 0..7 read port a, tiles 8..15 port b.
module ntt_core_pack_rom #(parameter FILE = "root_pack_b0.mem") (
    input  wire        clk,
    input  wire        we,
    input  wire [11:0] wa,
    input  wire [95:0] wd,
    input  wire [11:0] addr_a, addr_b,
    output reg  [95:0] qa, qb
);
    (* ram_style = "block" *) reg [95:0] rom [0:3327];
    initial $readmemh(FILE, rom);
    wire [11:0] aa = we ? wa : addr_a;
    always @(posedge clk) begin
        if (we) rom[aa] <= wd;
        qa <= rom[aa];
    end
    always @(posedge clk) qb <= rom[addr_b];
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
    input  wire         start_fft,          // 1: FFT (start_profile ignored)
    input  wire [1:0]   start_fmt,          // FFT format: 0 / 1 / 2 = 32 / 64 / 128 bit
    input  wire         start_inverse,
    input  wire [1:0]   start_profile,
    input  wire [3:0]   start_logn,
    input  wire [3:0]   start_slot,         // profile 3: the slot
    input  wire [1:0]   start_hmin,         // profile 3: skipped last layers (incomplete NTT, 0..2)
    // profile 3 slots and root packs, only while idle
    input  wire         slot_we,
    input  wire [3:0]   slot_idx,
    input  wire [31:0]  slot_q, slot_qinv, slot_root1f, slot_root1i,
    input  wire [8:0]   slot_base,          // position of the slot's pack 1 (multiple of 4)
    input  wire [3:0]   slot_logn,
    input  wire         pack_we,
    input  wire         pack_inv,
    input  wire [8:0]   pack_pos,
    input  wire [95:0]  pack_data,
    output wire         busy,
    output reg          done,
    output reg          error,
    output reg  [31:0]  cycles
);
    localparam [1:0] IDLE = 2'd0, CFG = 2'd1, RUN = 2'd2, FIN = 2'd3;
    localparam integer XW = 4;               // network select width (hdl/net/ntt_bank_net_s.sv)
    reg  [1:0] state;
    reg        inverse, fft;
    reg  [1:0] profile, fmt;
    reg  [3:0] logn, hlog, hmin;
    assign busy = (state != IDLE);
    wire       wide = fft && (fmt != 2'd0);
    wire       w4   = fmt[1];                // 128 bit: L = 4 limbs; 64 bit: L = 2
    wire [3:0] fq   = w4 ? 4'd12 : 4'd6;     // wide: cycles between a block's butterflies

    // ---------------- constants and layer table ----------------
    wire [31:0] fq_, fqinv, froot1;
    wire [8:0]  fpbase;
    ntt_core_consts u_consts (.profile(profile), .inverse(inverse), .q(fq_), .qinv(fqinv), .root1(froot1), .pbase(fpbase));
    // profile 3: 16 slots (written by the host), the command's slot latched at start
    reg  [31:0] sl_q [0:15];
    reg  [31:0] sl_qi [0:15];
    reg  [31:0] sl_r1f [0:15];
    reg  [31:0] sl_r1i [0:15];
    reg  [8:0]  sl_base [0:15];
    reg  [3:0]  sl_logn [0:15];
    reg  [15:0] sl_ok;
    reg  [31:0] p3q, p3qi, p3r1f, p3r1i;
    reg  [6:0]  p3base;
    wire        p3 = !fft && profile == 2'd3;
    wire [31:0] cq     = p3 ? p3q : fq_;
    wire [31:0] cqinv  = p3 ? p3qi : fqinv;
    wire [31:0] croot1 = p3 ? (inverse ? p3r1i : p3r1f) : froot1;
    wire [11:0] pbase  = p3 ? 12'd3072 + {4'd0, inverse, p3base} : {3'd0, fpbase};
    // The table is read for the first layer in CFG and for the next layer during RUN, registered at the switch.
    wire          layer_sw;
    wire [3:0]    hnext = inverse ? hlog + 4'd1 : hlog - 4'd1;
    wire [15:0]   n_tv;
    wire [16*9-1:0] n_lp;
    wire [6*9-1:0]  n_kb;
    wire [2:0]    n_kdim;
    wire          n_same;
    wire [9:0]    n_delta;
    ntt_core_layer_rom u_layer (.fft(fft), .fmt(fft ? fmt : 2'd0), .hmin(fft ? 2'd0 : hmin[1:0]), .inverse(!fft && inverse),
        .logn(logn), .hlog(state == RUN ? hnext : hlog), .tv(n_tv), .p(n_lp), .kb(n_kb), .kdim(n_kdim), .same(n_same),
        .delta(n_delta));
    reg  [15:0]   tv;
    reg  [16*9-1:0] lp;
    reg  [6*9-1:0]  kb;
    reg  [6:0]    bf_per_tile;
    reg           same;
    reg  [9:0]    delta, lt;                    // cycles to the next layer's start, cycles since this layer's start
    reg  [3:0]    qc;                           // wide: issue slot counter, mod fq from the layer's start
    always @(posedge clk)
        if (state == CFG || layer_sw) begin
            tv <= n_tv; lp <= n_lp; kb <= n_kb; bf_per_tile <= 7'd1 << n_kdim; same <= n_same; delta <= n_delta;
        end
    reg  [13:0] cmd_total;                      // butterflies of the command (FFT: per block tile)
    reg  [13:0] wdone;                          // butterflies fully written (last write select issued)
    reg  [13:0] lwdone, ltot;                   // FFT: written in this layer; per layer (N/4 butterflies x L block tiles)
    wire [3:0]  hn_log = logn - 4'd1;           // FFT: log2 of hn (imaginary parts start at element hn)
    // FFT timing (generated from model/fft_core_sched.py, model/fft_wide_sched.py): data read offset D of the format,
    // root address stage of each tile
    wire [3:0]       fD;
    wire [16*4-1:0]  froot_d;
    ntt_core_fft_timing u_ftim (.fmt(fmt), .d(fD), .droot(froot_d));

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
    function [4:0] sbank(input [11:0] c);                        // superbank of (virtual) element c = bank(2c) >> 1
        reg [12:0] k;
        reg [5:0]  b;
        begin
            k = {c, 1'b0};
            b = {k[5:4] ^ k[7:6] ^ k[9:8], k[3:0]};
            sbank = b[5:1];
        end
    endfunction
    function [8:0] enumi(input [8:0] p, input [5:0] k, input [6*9-1:0] basis);
        integer j;
        begin
            enumi = p;
            for (j = 0; j < 6; j = j + 1)
                if (k[j]) enumi = enumi ^ basis[9*j +: 9];
        end
    endfunction
    // FFT: (virtual) element of port x (A) or y (B), real or imaginary part, limb k: L e + k
    function [11:0] felem(input [8:0] i, input [3:0] hl, input [3:0] hnl, input y, input im, input [1:0] f, input [1:0] k);
        reg [9:0] e;
        begin
            e = ins0(i, hl) | (y ? (10'd1 << hl) : 10'd0) | (im ? (10'd1 << hnl) : 10'd0);
            felem = (f == 2'd0) ? {2'b0, e} : (f == 2'd1) ? {1'b0, e, k[0]} : {e, k};
        end
    endfunction

    // ---------------- per-tile issue and write address FIFO ----------------
    reg         layer_on;
    reg  [15:0] s0v, s1v, s2v, s3v;
    reg  [15:0] s0m, s1m, s2m, s3m;             // NTT: same superbank, per butterfly
    reg  [16*5-1:0] s0sx, s0sy;                 // superbanks (network selects)
    reg  [16*32-1:0] s0xo, s0yo, s1yo;          // superbanks one-hot, gated by valid (for the RAM requests)
    reg  [16*7-1:0] s0rx, s0ry, s1ry;
    reg  [16*4-1:0] s0po, s1po, s2po;           // NTT: pack bank one-hot, gated (root 1 reads no pack)
    reg  [16*12-1:0] s0pr, s1pr, s2pr;
    reg  [16*4-1:0] s0rs, s1rs, s2rs, s3rs;
    wire [16*XW-1:0] nsel_xlo, nsel_xhi, nsel_ylo, nsel_yhi;
    reg  [16*XW-1:0] s1xlo, s1xhi, s1ylo, s1yhi, s2ylo, s2yhi;
    ntt_core_sel u_sel (.sx(s0sx), .sy(s0sy), .sel_xlo(nsel_xlo), .sel_xhi(nsel_xhi), .sel_ylo(nsel_ylo), .sel_yhi(nsel_yhi));

    wire [15:0] rsp_valid;
    wire [16*8-1:0] rsp_tag;
    wire [16*65-1:0] rsp_dat;
    reg  [15:0] ypend;                          // NTT same superbank: y write select pending for the next cycle
    reg  [15:0] hm;                             // head of the address FIFO: same-superbank flag
    reg  [16*32-1:0] hxo, hyo, ysbo;            // NTT: head superbanks one-hot, y pending
    reg  [16*7-1:0] hrx, hry, yrow;
    reg  [16*6-1:0] kr;
    reg  [15:0] rdone;
    wire [15:0] fin_now;                        // butterflies whose last write select is this cycle
    // FFT
    reg  [16*12-1:0] f_rpr;                     // root ROM row of the tile's root read (address stage, registered)
    reg  [16*4-1:0]  f_rpo;                     // its bank one-hot, gated
    reg  [16*2-1:0]  f_rbk;                     // bank, kept for the root register load two cycles later
    wire [15:0]      f_rld;                     // root register load this cycle
    reg  [16*32-1:0] f_wxo, f_wyo;              // write superbank one-hot (event registers), gated below by the strobes
    reg  [16*7-1:0]  f_wxr, f_wyr;
    reg  [15:0]      f_wxs, f_wys, f_wyd;       // x / y write select this cycle; wide: y one cycle after x
    reg  [15:0]      f_yim, f_ydim;             // the y write is of an imaginary row (the butterfly's last)
    reg  [16*64-1:0] f_z;                       // forwarding register: the result being written
    wire [15:0]      f_req;                     // owner: a beat this cycle
    wire [16*3-1:0]  f_bj;                      // its beat

    genvar t;
    generate for (t = 0; t < 16; t = t + 1) begin : g_issue
        localparam integer PH = t / 6;
        localparam [3:0] TT = t;
        wire [1:0] kt = w4 ? TT[1:0] : (fmt == 2'd1) ? {1'b0, TT[0]} : 2'd0;   // limb (block tile) of this tile
        wire       go_n = layer_on && tv[t] && !rdone[t] && (((PH + gph + same) % 3) == 0);
        wire       go_f = layer_on && tv[t] && !rdone[t] && (wide ? (qc == 4'd0) : (gph == 2'd0));
        wire       go = fft ? go_f : go_n;
        wire [8:0] i  = enumi(lp[9*t +: 9], kr[6*t +: 6], kb);

        // ---- NTT address stage (unchanged) ----
        wire [9:0] cx = ins0(i, hlog);
        wire [9:0] cy = cx | (10'd1 << hlog);
        wire [9:0] r  = (10'd1 << (logn - 4'd1 - hlog)) + ({1'b0, i} >> hlog);   // N/(2h) + c/(2h), c = i with a 0 at hlog
        wire [8:0] pos = r[9:1] - 9'd1;
        wire       r1 = (hlog == logn - 4'd1);

        // ---- FFT: issue shift register, registered index, owner ----
        reg  [15:0] gs, gso;
        wire        own = !wide || (kr[6*t +: 2] & (w4 ? 2'd3 : 2'd1)) == kt;   // wide: this tile runs butterfly m
        wire [16:0] gd = {gs, fft && go};       // gd[d]: issued d cycles ago (d = 0: this cycle)
        wire [16:0] god = {gso, fft && go && own};     // the same, for butterflies this tile runs
        reg  [8:0]  ib, ib2;
        always @(posedge clk) begin
            gs  <= rst ? 16'd0 : gd[15:0];
            gso <= rst ? 16'd0 : god[15:0];
            if (go) ib <= i;
            ib2 <= ib;
        end
        // events (address stage of the read the next cycle). Format 0: x and y of the real parts at d = 3, imaginary at
        // d = 4 (index from ib2, the next issue has loaded ib). Wide: x real at D - 1 + k, y real at D + k, imaginary L later.
        wire [4:0] dxr = fD - 4'd1 + {2'd0, kt};
        wire [4:0] dlw = w4 ? 5'd4 : 5'd2;
        // (gd[d] = gs[d - 1] for d >= 1: only registered bits, never the issue decision of this cycle)
        wire       xre = wide ? gs[dxr - 5'd1] : gs[2];
        wire       xim = wide ? gs[dxr + dlw - 5'd1] : gs[3];
        wire       yre = wide ? gs[dxr] : gs[2];
        wire       yim = wide ? gs[dxr + dlw] : gs[3];
        wire [8:0] ixe = (!wide && xim) ? ib2 : ib;
        wire [8:0] iye = (!wide && yim) ? ib2 : ib;
        wire [11:0] vx = felem(ixe, hlog, hn_log, 1'b0, xim, fmt, kt);
        wire [11:0] vy = felem(iye, hlog, hn_log, 1'b1, yim, fmt, kt);
        // root: address stage at froot_d (format 0: 1 + (t >> 2) mod 3; wide: per block lead), register load two later
        wire [3:0] drt = froot_d[4*t +: 4];
        wire       rev = gs[drt - 4'd1];
        wire [9:0] fr  = (10'd1 << (logn - 4'd1 - hlog)) + ({1'b0, ib} >> hlog);     // root index N/(2h) + j/(2h)
        wire [11:0] fbase = !wide ? (inverse ? 12'd576 : 12'd384) : !w4 ? (inverse ? 12'd1152 : 12'd768)
                                                                        : (inverse ? 12'd2304 : 12'd1536);
        wire [11:0] frow = !wide ? fbase + {4'd0, fr[9:2]} : !w4 ? fbase + {3'd0, fr[9:2], kt[0]} : fbase + {2'd0, fr[9:2], kt};

        // write address FIFO (NTT: superbanks and rows; FFT: the butterfly index and its layer, since the last results of
        // a layer are written after the next layer has started), 16 entries. FFT: one read pointer per row, since at
        // 128 bit the real results of the next butterfly come before the imaginary results of this one.
        reg [24:0] fifo [0:15];
        reg [12:0] ffifo [0:15];
        reg [3:0]  wp, rp, fpr, fpi;
        wire [24:0] fh = fifo[rp];
        // FFT result capture: the block tile whose result limb is this tile's (format 0: the tile itself)
        reg        cap;
        reg [2:0]  cj;
        reg [63:0] cz;
        integer    ob;
        always @* begin
            cap = 1'b0; cj = 3'd0; cz = 64'd0;
            for (ob = 0; ob < 4; ob = ob + 1)
                if (((t & ~3) | ob) == t || (wide && (w4 || ob[1] == TT[1])))
                    if (rsp_valid[(t & ~3) | ob] &&
                        ((rsp_tag[8*((t & ~3) | ob) +: 3] & (w4 ? 3'd3 : (fmt == 2'd1) ? 3'd1 : 3'd0)) == {1'b0, kt})) begin
                        cap = 1'b1; cj = rsp_tag[8*((t & ~3) | ob) +: 3];
                        cz = rsp_dat[65*((t & ~3) | ob) +: 64];
                    end
        end
        // registered first (capa, cja, cza); the write addresses are made from the FIFO one cycle later
        reg        capa;
        reg [2:0]  cja;
        reg [63:0] cza;
        always @(posedge clk) begin
            capa <= !rst && fft && cap;
            if (cap) begin cja <= cj; cza <= cz; end
        end
        wire       crow = w4 ? cja[2] : (fmt == 2'd1) ? cja[1] : cja[0];        // result of the imaginary row
        wire [12:0] fhe = ffifo[crow ? fpi : fpr];
        wire [8:0]  fhi = fhe[8:0];
        wire [3:0]  fhl = fhe[12:9];
        wire [11:0] wvx = felem(fhi, fhl, hn_log, 1'b0, crow, fmt, kt);
        wire [11:0] wvy = felem(fhi, fhl, hn_log, 1'b1, crow, fmt, kt);

        always @(posedge clk) begin
            // address stage
            s0v[t] <= !rst && go && !fft;
            s0m[t] <= same;
            if (fft) begin
                s0sx[5*t +: 5] <= sbank(vx);  s0rx[7*t +: 7] <= vx[11:5];
                s0sy[5*t +: 5] <= sbank(vy);  s0ry[7*t +: 7] <= vy[11:5];
                s0xo[32*t +: 32] <= (!rst && (xre || xim)) ? (32'd1 << sbank(vx)) : 32'd0;
                s0yo[32*t +: 32] <= (!rst && (yre || yim)) ? (32'd1 << sbank(vy)) : 32'd0;
                s0po[4*t +: 4] <= 4'd0;
            end else begin
                s0sx[5*t +: 5] <= sbank({2'b0, cx});  s0rx[7*t +: 7] <= {2'b0, cx[9:5]};
                s0sy[5*t +: 5] <= sbank({2'b0, cy});  s0ry[7*t +: 7] <= {2'b0, cy[9:5]};
                s0xo[32*t +: 32] <= (!rst && go) ? (32'd1 << sbank({2'b0, cx})) : 32'd0;
                s0yo[32*t +: 32] <= (!rst && go) ? (32'd1 << sbank({2'b0, cy})) : 32'd0;
                s0po[4*t +: 4] <= (!rst && go && !r1) ? (4'd1 << pos[1:0]) : 4'd0;
            end
            s0pr[12*t +: 12] <= {5'b0, pos[8:2]} + pbase;
            s0rs[4*t +: 4] <= r1 ? 4'd8 : {1'b0, pos[1:0], r[0]};
            // FFT root read
            f_rpo[4*t +: 4] <= (!rst && fft && rev) ? (4'd1 << fr[1:0]) : 4'd0;
            f_rpr[12*t +: 12] <= frow;
            if (rev) f_rbk[2*t +: 2] <= fr[1:0];
            if (rst || !layer_on || layer_sw) kr[6*t +: 6] <= 6'd0;
            else if (go) kr[6*t +: 6] <= kr[6*t +: 6] + 6'd1;
            if (rst || !layer_on || layer_sw) rdone[t] <= 1'b0;
            else if (go && ({1'b0, kr[6*t +: 6]} + 7'd1 == bf_per_tile)) rdone[t] <= 1'b1;
            // address FIFO: push at issue, pop at the last write select; the head is decoded one cycle later
            if (rst) begin wp <= 4'd0; rp <= 4'd0; fpr <= 4'd0; fpi <= 4'd0; end
            else begin
                if (fft ? gd[1] : go) wp <= wp + 4'd1;
                if (!fft && rsp_valid[t]) rp <= rp + 4'd1;
                if (capa && !crow) fpr <= fpr + 4'd1;
                if (capa && crow)  fpi <= fpi + 4'd1;
            end
            if (fft && gd[1]) ffifo[wp] <= {hlog, ib};
            if (!fft && go) fifo[wp] <= {same, sbank({2'b0, cx}), 2'b0, cx[9:5], sbank({2'b0, cy}), 2'b0, cy[9:5]};
            hm[t] <= fh[24];
            hxo[32*t +: 32]  <= 32'd1 << fh[23:19];  hrx[7*t +: 7]  <= fh[18:12];
            hyo[32*t +: 32]  <= 32'd1 << fh[11:7];   hry[7*t +: 7]  <= fh[6:0];
            ypend[t] <= !rst && !fft && rsp_valid[t] && hm[t];
            if (rsp_valid[t]) begin ysbo[32*t +: 32] <= hyo[32*t +: 32]; yrow[7*t +: 7] <= hry[7*t +: 7]; end
            // FFT result: forwarding register and write events (x the next cycle; y with it (format 0) or one later)
            if (capa) begin
                f_z[64*t +: 64] <= cza;
                f_wxo[32*t +: 32] <= 32'd1 << sbank(wvx);  f_wxr[7*t +: 7] <= wvx[11:5];
                f_wyo[32*t +: 32] <= 32'd1 << sbank(wvy);  f_wyr[7*t +: 7] <= wvy[11:5];
            end
            f_wxs[t] <= !rst && capa;
            f_wyd[t] <= !rst && wide && capa;
            f_wys[t] <= !rst && fft && (wide ? f_wyd[t] : capa);
            f_ydim[t] <= capa && crow;
            f_yim[t] <= wide ? f_ydim[t] : (capa && crow);
        end
        assign fin_now[t] = fft ? (f_wys[t] && f_yim[t]) : ((rsp_valid[t] && !hm[t]) || ypend[t]);
        // owner beats: format 0 at g + 6, g + 7; wide at e + 3 + j = g + D + 3 + j, j = 0 .. 2L - 1. Decided one cycle
        // ahead from registered bits (god[d] one cycle later = gso[d - 2] now) and registered.
        reg        bv, bvr;
        reg [2:0]  bj, bjr;
        integer    jb;
        always @* begin
            bv = 1'b0; bj = 3'd0;
            if (!wide) begin
                if (gso[4]) begin bv = 1'b1; bj = 3'd0; end
                if (gso[5]) begin bv = 1'b1; bj = 3'd1; end
            end else
                for (jb = 0; jb < 8; jb = jb + 1)
                    if ((jb < 4 || w4) && gso[fD + 4'd1 + jb]) begin bv = 1'b1; bj = jb; end
        end
        always @(posedge clk) begin bvr <= !rst && bv; bjr <= bj; end
        assign f_req[t] = bvr;
        assign f_bj[3*t +: 3] = bjr;
        // root register load (address stage + 2)
        reg [1:0] rl;
        always @(posedge clk) rl <= rst ? 2'd0 : {rl[0], fft && rev};
        assign f_rld[t] = rl[1];
    end endgenerate

    // pipeline stages s1..s3 (all tiles at once)
    always @(posedge clk) begin
        s1v <= rst ? 16'd0 : s0v;
        s2v <= rst ? 16'd0 : s1v;
        s3v <= rst ? 16'd0 : s2v;
        s1m <= s0m;  s2m <= s1m;  s3m <= s2m;
        s1yo <= rst ? {16*32{1'b0}} : s0yo;
        s1po <= rst ? 64'd0 : s0po;
        s2po <= rst ? 64'd0 : s1po;
        s1ry <= s0ry;  s1pr <= s0pr;  s2pr <= s1pr;  s1rs <= s0rs;
        s1xlo <= nsel_xlo;  s1xhi <= nsel_xhi;  s1ylo <= nsel_ylo;  s1yhi <= nsel_yhi;
        s2ylo <= s1ylo;  s2yhi <= s1yhi;  s2rs <= s1rs;  s3rs <= s2rs;
    end

    // ---------------- memory requests ----------------
    // NTT, per tile: RAM read x from s0; y and the root pack from s0, or from s1 when x and y share a superbank.
    // FFT, per tile: x and y read events from s0; root word from the tile's own root read stage.
    reg  [16*32-1:0] rxo, ryo, wxo, wyo;
    reg  [16*7-1:0]  rxr, ryr, wxr, wyr;
    reg  [16*4-1:0]  ppo;
    reg  [16*12-1:0] ppr;
    reg  [16*XW-1:0] q_xlo, q_xhi, q_ylo, q_yhi;
    reg  [16*4-1:0]  q_rs;
    reg  [15:0]      q_hold, q_load, n_req;
    integer tw;
    always @* begin
        for (tw = 0; tw < 16; tw = tw + 1) begin
            if (fft) begin
                rxo[32*tw +: 32] = s0xo[32*tw +: 32];
                ryo[32*tw +: 32] = s0yo[32*tw +: 32];
                rxr[7*tw +: 7]   = s0rx[7*tw +: 7];
                ryr[7*tw +: 7]   = s0ry[7*tw +: 7];
                ppo[4*tw +: 4]   = f_rpo[4*tw +: 4];
                ppr[12*tw +: 12] = f_rpr[12*tw +: 12];
                // network selects one cycle after each read; wide: the network holds x one cycle (y is read one later)
                q_xlo[XW*tw +: XW] = s1xlo[XW*tw +: XW];
                q_xhi[XW*tw +: XW] = s1xhi[XW*tw +: XW];
                q_ylo[XW*tw +: XW] = s1ylo[XW*tw +: XW];
                q_yhi[XW*tw +: XW] = s1yhi[XW*tw +: XW];
                q_rs[4*tw +: 4]  = {1'b0, f_rbk[2*tw +: 2], 1'b0};       // the bank of the tile's root this cycle
                q_load[tw]       = f_rld[tw];
                q_hold[tw]       = wide;
                n_req[tw]        = 1'b0;
                // writes: x / y events of the forwarding register
                wxo[32*tw +: 32] = {32{f_wxs[tw]}} & f_wxo[32*tw +: 32];
                wyo[32*tw +: 32] = {32{f_wys[tw]}} & f_wyo[32*tw +: 32];
                wxr[7*tw +: 7]   = f_wxr[7*tw +: 7];
                wyr[7*tw +: 7]   = f_wyr[7*tw +: 7];
            end else begin
                rxo[32*tw +: 32] = s0xo[32*tw +: 32];
                ryo[32*tw +: 32] = (s0yo[32*tw +: 32] & {32{!s0m[tw]}}) | (s1yo[32*tw +: 32] & {32{s1m[tw]}});
                rxr[7*tw +: 7]   = s0rx[7*tw +: 7];
                ryr[7*tw +: 7]   = (s1v[tw] && s1m[tw]) ? s1ry[7*tw +: 7] : s0ry[7*tw +: 7];
                ppo[4*tw +: 4]   = (s0po[4*tw +: 4] & {4{!s0m[tw]}}) | (s1po[4*tw +: 4] & {4{s1m[tw]}});
                ppr[12*tw +: 12] = (s1v[tw] && s1m[tw]) ? s1pr[12*tw +: 12] : s0pr[12*tw +: 12];
                // network selects: y and root at s1, or at s2 (with x held) when same superbank
                q_xlo[XW*tw +: XW] = s1xlo[XW*tw +: XW];
                q_xhi[XW*tw +: XW] = s1xhi[XW*tw +: XW];
                q_ylo[XW*tw +: XW] = (s2v[tw] && s2m[tw]) ? s2ylo[XW*tw +: XW] : s1ylo[XW*tw +: XW];
                q_yhi[XW*tw +: XW] = (s2v[tw] && s2m[tw]) ? s2yhi[XW*tw +: XW] : s1yhi[XW*tw +: XW];
                q_rs[4*tw +: 4]  = (s2v[tw] && s2m[tw]) ? s2rs[4*tw +: 4]  : s1rs[4*tw +: 4];
                q_load[tw]       = 1'b1;
                q_hold[tw]       = s2v[tw] && s2m[tw];
                n_req[tw]        = (s2v[tw] && !s2m[tw]) || (s3v[tw] && s3m[tw]);
                // writes: x and (unless same superbank) y at the result; y one cycle later when same
                wxo[32*tw +: 32] = {32{rsp_valid[tw]}} & hxo[32*tw +: 32];
                wyo[32*tw +: 32] = ({32{rsp_valid[tw] && !hm[tw]}} & hyo[32*tw +: 32]) | ({32{ypend[tw]}} & ysbo[32*tw +: 32]);
                wxr[7*tw +: 7]   = hrx[7*tw +: 7];
                wyr[7*tw +: 7]   = ypend[tw] ? yrow[7*tw +: 7] : hry[7*tw +: 7];
            end
        end
    end

    wire [63:0]      c_re, c_wen;
    wire [64*7-1:0]  c_ra, c_wa;
    wire [64*XW-1:0] c_wsel;
    ntt_core_route u_route (.clk(clk), .rxo(rxo), .ryo(ryo), .rxr(rxr), .ryr(ryr), .re(c_re), .ra(c_ra),
        .wxo(wxo), .wyo(wyo), .wxr(wxr), .wyr(wyr), .wsel(c_wsel), .wen(c_wen), .wa(c_wa));

    // root-pack ROM, 4 banks x 2 ports (tiles 0..7: port a, 8..15: port b); a bank port is read by every tile that needs
    // its word this cycle (always the same word)
    wire [8*96-1:0]  pack_q;                    // port a banks 0..3, then port b banks 0..3
    wire [8*64-1:0]  pack_rd;                   // {child 2, child 1} of each
    integer tt, pb;
    reg [8*12-1:0] paddr;
    always @* begin
        paddr = 0;
        for (pb = 0; pb < 4; pb = pb + 1)
            for (tt = 0; tt < 16; tt = tt + 1)
                paddr[12*(pb + (tt < 8 ? 0 : 4)) +: 12] = paddr[12*(pb + (tt < 8 ? 0 : 4)) +: 12] |
                                                         ({12{ppo[4*tt + pb]}} & ppr[12*tt +: 12]);
    end
    genvar gb;
    generate for (gb = 0; gb < 4; gb = gb + 1) begin : g_pack
        localparam [7:0] DIG = 8'd48 + gb;          // "0" + bank
        ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b", DIG, ".mem"})) u_rom (.clk(clk),
            .we(state == IDLE && pack_we && pack_pos[1:0] == gb), .wa(12'd3072 + {4'd0, pack_inv, pack_pos[8:2]}), .wd(pack_data),
            .addr_a(paddr[12*gb +: 12]), .addr_b(paddr[12*(gb + 4) +: 12]),
            .qa(pack_q[96*gb +: 96]), .qb(pack_q[96*(gb + 4) +: 96]));
        assign pack_rd[64*gb +: 64]       = pack_q[96*gb + 32 +: 64];
        assign pack_rd[64*(gb + 4) +: 64] = pack_q[96*(gb + 4) + 32 +: 64];
    end endgenerate

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
    wire [16*32-1:0] op_x, op_y;
    wire [16*64-1:0] op_w;                      // {child 2, child 1} (NTT: the core picks one), FFT {wi, wr}
    reg  [16*64-1:0] tile_z;
    ntt_bank_net_s u_net (.clk(clk), .en(1'b1), .bank_rd(m_rd), .pack_rd(pack_rd),
        .sel_xlo(q_xlo), .sel_xhi(q_xhi), .sel_ylo(q_ylo), .sel_yhi(q_yhi),
        .hold_x(q_hold), .root1(croot1), .sel_root(q_rs), .load_w(q_load),
        .op_x(op_x), .op_y(op_y), .op_w(op_w), .tile_z(tile_z), .wsel(c_wsel), .wen(c_wen),
        .bank_wd(net_wd), .bank_we(net_we));

    reg cfg_we;
    wire [15:0] req_ready, tile_idle, req_valid;
    wire scale = fft && inverse && (hlog == logn - 4'd2);     // last layer of the inverse FFT: div2e in the tile
    generate for (t = 0; t < 16; t = t + 1) begin : g_tile
        wire [64:0] rd;
        wire [7:0]  rt;
        // FFT beat source: block tile j mod L (format 0: this tile); data from its port, root from its root register
        localparam [3:0] TT = t;
        wire [2:0] bj = f_bj[3*t +: 3];
        wire [1:0] sk = w4 ? bj[1:0] : (fmt == 2'd1) ? {TT[1], bj[0]} : TT[1:0];
        wire [3:0] st = {TT[3:2], sk};
        wire       bim = w4 ? bj[2] : (fmt == 2'd1) ? bj[1] : bj[0];
        // format 0: wi is kept for the second beat (the root register may load the next root before it)
        reg  [31:0] fwi;
        always @(posedge clk)
            if (f_req[t] && !wide && !bim) fwi <= op_w[64*t+32 +: 32];
        wire [31:0] froot = wide ? (bim ? op_w[64*st+32 +: 32] : op_w[64*st +: 32]) : (bim ? fwi : op_w[64*t +: 32]);
        // NTT: child 1 or 2 of the pack, by the child bit of the stage that accepts
        wire         nchild = (s3v[t] && s3m[t]) ? s3rs[4*t] : s2rs[4*t];
        wire [31:0]  nroot = nchild ? op_w[64*t+32 +: 32] : op_w[64*t +: 32];
        assign req_valid[t] = fft ? f_req[t] : n_req[t];
        // IN_REG = 1: the request (and the FFT beat source choice in front of it) is registered at the tile's input
        tile_thu #(.TREN_MANG(1), .IN_REG(1), .PHASE(t / 6)) u_tile (
            .clk(clk), .rst(rst), .en(1'b1), .idle(tile_idle[t]),
            .cfg_we(cfg_we), .cfg_slot(1'b0), .cfg_q(fft ? {26'd0, fmt, logn - 4'd1} : cq), .cfg_qinv(cqinv),
            .cfg_floor(1'b0), .cfg_halve(inverse),
            .req_valid(req_valid[t]), .req_ready(req_ready[t]), .req_mode(fft ? 3'd5 : 3'd4), .req_dir(inverse),
            .req_slot(1'b0), .req_sign({1'b0, scale}),
            .req_data(fft ? {op_y[32*st +: 32], op_x[32*st +: 32]} : {op_y[32*t +: 32], op_x[32*t +: 32]}),
            .req_root(fft ? froot : nroot),
            .req_tag({5'd0, bj}), .rsp_valid(rsp_valid[t]), .rsp_data(rd), .rsp_tag(rt));
        assign rsp_tag[8*t +: 8] = rt;
        assign rsp_dat[65*t +: 65] = rd;
        always @* tile_z[64*t +: 64] = fft ? f_z[64*t +: 64] : rd[63:0];
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
    wire last_layer = fft ? (inverse ? (hlog == logn - 4'd2) : (hlog == 4'd0))
                          : (inverse ? (hlog == logn - 4'd1) : (hlog == hmin));
    // NTT: the layer table's overlap plan. FFT: barrier on commits: the next layer starts two cycles after the last write
    // select of this layer (the count of written butterflies is registered first), whatever the tile latency.
    wire lay_done = fft ? (lwdone == ltot) : (lt == delta - 10'd1);
    assign layer_sw = (state == RUN) && layer_on && !last_layer && lay_done;
    wire cmd_last_write = (state == RUN) && (wdone + {9'd0, nfin} == cmd_total);
    // profile 3: the slot must be loaded with tables for at least this logn; 0..2 skipped layers, at least one layer kept
    wire p3bad = !sl_ok[start_slot] || (start_logn == 4'd0) || (start_logn > 4'd10) || (start_logn > sl_logn[start_slot]) ||
                 (start_hmin == 2'd3) || ({2'd0, start_hmin} >= start_logn);
    wire bad = start_fft ? ((start_logn > 4'd10) || (start_fmt == 2'd3))
                         : (start_profile == 2'd3) ? p3bad
                         : ((start_logn < 4'd3) ||
                            (start_profile == 2'd0 && start_logn > 4'd10) || (start_profile == 2'd1 && start_logn > 4'd8) ||
                            (start_profile == 2'd2 && start_logn != 4'd8));
    wire [3:0] start_hm = start_fft ? 4'd0 : (start_profile == 2'd3) ? {2'd0, start_hmin}
                        : (start_profile == 2'd1 && start_logn == 4'd8) ? 4'd1 : 4'd0;
    // FFT: N/4 butterflies per layer, logn - 1 layers, each written by L block tiles; NTT: N/2 per layer, logn - hmin layers
    wire [13:0] start_total = start_fft ? (({10'd0, start_logn - 4'd1} << (start_logn - 4'd2)) << start_fmt)
                                        : ({10'd0, start_logn - start_hm} << (start_logn - 4'd1));

    always @(posedge clk) begin
        if (rst) sl_ok <= 16'd0;
        else if (host && slot_we) sl_ok[slot_idx] <= 1'b1;
        if (host && slot_we) begin
            sl_q[slot_idx] <= slot_q; sl_qi[slot_idx] <= slot_qinv; sl_r1f[slot_idx] <= slot_root1f;
            sl_r1i[slot_idx] <= slot_root1i; sl_base[slot_idx] <= slot_base; sl_logn[slot_idx] <= slot_logn;
        end
    end

    always @(posedge clk) begin
        done <= 1'b0;
        cfg_we <= 1'b0;
        if (rst) begin
            state <= IDLE; layer_on <= 1'b0; error <= 1'b0; cycles <= 32'd0; wdone <= 14'd0; lt <= 10'd0; fft <= 1'b0;
            inverse <= 1'b0; profile <= 2'd0; fmt <= 2'd0; logn <= 4'd3; hlog <= 4'd0; hmin <= 4'd0; cmd_total <= 14'd0;
            qc <= 4'd0; lwdone <= 14'd0; ltot <= 14'd0;
        end else begin
            if (busy) cycles <= cycles + 32'd1;
            case (state)
                IDLE: if (start) begin
                    cycles <= 32'd0;
                    error <= bad;
                    if (bad || (start_fft && start_logn < 4'd2)) done <= 1'b1;    // FFT with N <= 2 is the identity
                    else begin
                        fft <= start_fft; fmt <= start_fft ? start_fmt : 2'd0; inverse <= start_inverse;
                        profile <= start_profile; logn <= start_logn;
                        hmin <= start_hm;
                        p3q <= sl_q[start_slot]; p3qi <= sl_qi[start_slot]; p3base <= sl_base[start_slot][8:2];
                        p3r1f <= sl_r1f[start_slot]; p3r1i <= sl_r1i[start_slot];
                        hlog <= start_fft ? (start_inverse ? 4'd0 : start_logn - 4'd2)
                                          : (start_inverse ? start_hm : start_logn - 4'd1);
                        cmd_total <= start_total;
                        ltot <= (14'd1 << (start_logn - 4'd2)) << start_fmt;
                        state <= CFG;
                    end
                end
                // Constants (and the tile mode) are taken while every tile is idle. The first layer starts at issue
                // phase 2, the phase the layer tables were made for.
                CFG: if (&tile_idle && gph == 2'd1) begin
                    cfg_we <= 1'b1;
                    state <= RUN;
                    layer_on <= 1'b1;
                    lt <= 10'd0;
                    qc <= 4'd0;
                    wdone <= 14'd0;
                    lwdone <= 14'd0;
                end
                RUN: begin
                    wdone <= wdone + {9'd0, nfin};
                    lwdone <= layer_sw ? 14'd0 : lwdone + {9'd0, nfin};
                    lt <= layer_sw ? 10'd0 : lt + 10'd1;
                    qc <= (layer_sw || qc == fq - 4'd1) ? 4'd0 : qc + 4'd1;
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
