// ntt_core: minimal core of FlexTransform v1. One polynomial; opcodes NTT (0x5) and NTT ngược (0x6) for profiles 0
// (q = 12289, logn 3..10), 1 (3329, logn 3..8, 7 layers at N = 256) and 2 (8380417, logn 8); FFT (0x0) and FFT ngược
// (0x1) in format 0 (32 bit, logn 0..10). Memory region A only, simple host line port. Schedules and tables:
// model/ntt_core_sched.py, model/ntt_core_overlap.py, model/fft_core_sched.py, scripts/gen_ntt_core.py (ntt_core_gen.sv).
//
// Blocks: region A (flex_banked_scratch, 64 banks x 128 rows x 16 bit; NTT format 4 and FFT format 0 both keep a 32-bit
// element e in cells 2e, 2e + 1), 4 root-pack ROM banks (NTT packs, FFT root pairs), the structured bank -> tile network
// (hdl/net/ntt_bank_net_s.sv) and 16 on-array tiles (hdl/tile/tile_thu.sv, TREN_MANG = 1, PHASE = t / 6). FFT runs on the
// tiles' own butterfly path (tile mode 5); the core only supplies operands, roots and write addresses.
//
// Per layer (distance h = 2^hlog) tile t runs butterflies i = p_t xor K(k), k = 0 .. 2^kdim - 1 (layer table, loaded
// into registers one layer ahead; the next layer starts delta cycles after this one).
// NTT (tile mode 4): tile t accepts in cycles A with (PHASE + A) mod 3 == 0. Pipeline, e = first read cycle:
//   e - 1  address stage: i, c, superbanks (one-hot), rows, root pack            -> s0
//   e      RAM read x (and y), pack ROM read; same superbank: x only            -> s1 (with network selects)
//   e + 1  network selects; same superbank: RAM read y, pack read, x captured    -> s2
//   e + 2  tile accepts (same superbank: network selects for y and root, hold x) -> s3
//   e + 3  same superbank: tile accepts
// Result at A + 19: write select of x and y (same superbank: y one cycle later); RAM write the next cycle. Layers
// overlap (model/ntt_core_overlap.py); each result takes its write address from a per-tile FIFO filled at issue.
// INTT: tiles halve the sum branch and the inverse roots carry 2^-1, so no normalisation pass (spec 2.0, 03).
// FFT (tile mode 5): every tile issues in the same cycles, one complex butterfly per 3 cycles; the tile is the bank-indexed
// tile of the real pair. Address stage c: root pair word read at c + 1 + g (g = t / 6), captured; data addresses are made
// again at c + 2 from the delayed butterfly index, so e = c + 3: read A.re (x), B.re (y); e + 1: read A.im, B.im;
// e + 2: tile beat 1 (A.re, B.re, wr); e + 3: beat 2 (A.im, B.im, wi); results e + 11, e + 12; RAM writes e + 12, e + 13
// (model/fft_core_sched.py). Barrier per layer.
//
// Host port: only while idle. Line l (128 bit) = cells 8l .. 8l + 7, low cell in the low bits. Cell 8l + j always sits
// in a bank whose low 3 bits are j, so lane j of a line only ever reaches the 8 banks {g, j}.
`ifndef NTT_ROM_DIR
`define NTT_ROM_DIR "hdl/core_ntt/"
`endif

// One root-pack ROM bank: 768 rows x 96 bit, two read ports (NTT packs of profile 0 / 1 / 2, then FFT 32 bit roots
// [95:64] = wi, [63:32] = wr; scripts/gen_ntt_core.py). Tiles 0..7 read port a, tiles 8..15 port b.
module ntt_core_pack_rom #(parameter FILE = "root_pack_b0.mem") (
    input  wire        clk,
    input  wire [9:0]  addr_a, addr_b,
    output reg  [95:0] qa, qb
);
    (* rom_style = "block" *) reg [95:0] rom [0:767];
    initial $readmemh(FILE, rom);
    always @(posedge clk) begin qa <= rom[addr_a]; qb <= rom[addr_b]; end
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
    input  wire         start_fft,          // 1: FFT format 0 (start_profile ignored)
    input  wire         start_inverse,
    input  wire [1:0]   start_profile,
    input  wire [3:0]   start_logn,
    output wire         busy,
    output reg          done,
    output reg          error,
    output reg  [31:0]  cycles
);
    localparam [1:0] IDLE = 2'd0, CFG = 2'd1, RUN = 2'd2, FIN = 2'd3;
    localparam integer XW = 4;               // network select width (hdl/net/ntt_bank_net_s.sv)
    reg  [1:0] state;
    reg        inverse, fft;
    reg  [1:0] profile;
    reg  [3:0] logn, hlog, hmin;
    assign busy = (state != IDLE);

    // ---------------- constants and layer table ----------------
    wire [31:0] cq, cqinv, croot1;
    wire [8:0]  pbase;
    ntt_core_consts u_consts (.profile(profile), .inverse(inverse), .q(cq), .qinv(cqinv), .root1(croot1), .pbase(pbase));
    // The table is read for the first layer in CFG and for the next layer during RUN, registered at the switch.
    wire          layer_sw;
    wire [3:0]    hnext = inverse ? hlog + 4'd1 : hlog - 4'd1;
    wire [15:0]   n_tv;
    wire [16*9-1:0] n_lp;
    wire [5*9-1:0]  n_kb;
    wire [2:0]    n_kdim;
    wire          n_same;
    wire [7:0]    n_delta;
    ntt_core_layer_rom u_layer (.fft(fft), .ms2(!fft && hmin == 4'd1), .inverse(!fft && inverse), .logn(logn),
        .hlog(state == RUN ? hnext : hlog), .tv(n_tv), .p(n_lp), .kb(n_kb), .kdim(n_kdim), .same(n_same), .delta(n_delta));
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
    reg  [13:0] cmd_total;                      // butterflies of the command
    reg  [13:0] wdone;                          // butterflies fully written (last write select issued)
    wire [3:0]  hn_log = logn - 4'd1;           // FFT: log2 of hn (imaginary parts start at element hn)

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
    function [4:0] sbank(input [9:0] c);                         // superbank of element c = bank(2c) >> 1
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
    reg  [15:0] s0m, s1m, s2m, s3m;             // NTT: same superbank, per butterfly
    reg  [16*5-1:0] s0sx, s0sy, s0sxi, s0syi, s1sxi, s1syi;  // superbanks (network selects); FFT imaginary pair
    reg  [16*32-1:0] s0xo, s0yo, s1yo;          // superbanks one-hot, gated by valid (for the RAM requests)
    reg  [16*32-1:0] s0xio, s0yio, s1xio, s1yio; // FFT imaginary pair, one-hot, gated
    reg  [16*7-1:0] s0rx, s0ry, s1ry, s0rxi, s0ryi, s1rxi, s1ryi;
    reg  [16*4-1:0] s0po, s1po, s2po;           // pack bank one-hot, gated (NTT root 1 reads no pack)
    reg  [16*10-1:0] s0pr, s1pr, s2pr;
    reg  [16*4-1:0] s0rs, s1rs, s2rs, s3rs;
    reg  [16*3-1:0] s1fr, s2fr, s3fr;           // FFT root: {pack bank, slot} for the capture
    wire [16*XW-1:0] nsel_xlo, nsel_xhi, nsel_ylo, nsel_yhi, isel_xlo, isel_xhi, isel_ylo, isel_yhi;
    reg  [16*XW-1:0] s1xlo, s1xhi, s1ylo, s1yhi, s2ylo, s2yhi, s2xlo_i, s2xhi_i, s2ylo_i, s2yhi_i;
    ntt_core_sel u_sel (.sx(s0sx), .sy(s0sy), .sel_xlo(nsel_xlo), .sel_xhi(nsel_xhi), .sel_ylo(nsel_ylo), .sel_yhi(nsel_yhi));
    ntt_core_sel u_seli (.sx(s1sxi), .sy(s1syi), .sel_xlo(isel_xlo), .sel_xhi(isel_xhi), .sel_ylo(isel_ylo), .sel_yhi(isel_yhi));

    wire [15:0] rsp_valid;
    wire [15:0] f_re, f_im;                     // FFT: real / imaginary pair write select this cycle
    reg  [15:0] fpar;                           // FFT: next result of the tile is the imaginary pair
    reg  [15:0] ypend;                          // NTT same superbank: y write select pending for the next cycle
    reg  [15:0] hm;                             // head of the address FIFO: same-superbank flag
    reg  [16*32-1:0] hxo, hyo, ysbo, hxio, hyio; // head superbanks one-hot, y pending, FFT imaginary pair
    reg  [16*7-1:0] hrx, hry, yrow, hrxi, hryi;
    reg  [16*5-1:0] kr;
    reg  [15:0] rdone;
    wire [15:0] fin_now;                        // butterflies whose last write select is this cycle

    wire [15:0] fgo;                            // FFT: root request issued this cycle (address stage)
    genvar t;
    generate for (t = 0; t < 16; t = t + 1) begin : g_issue
        localparam integer PH = t / 6;
        wire       phase_ok = fft ? (gph == 2'd1) : (((PH + gph + same) % 3) == 0);
        wire       go = layer_on && tv[t] && !rdone[t] && phase_ok;
        wire [8:0] i  = enumi(lp[9*t +: 9], kr[5*t +: 5], kb);
        // FFT: data addresses two cycles after the root address (roots are read first)
        reg  [8:0] id1, id2;
        reg        gd1, gd2;
        always @(posedge clk) begin
            gd1 <= !rst && go && fft;  gd2 <= !rst && gd1;
            id1 <= i;  id2 <= id1;
        end
        wire       dgo = fft ? gd2 : go;
        assign fgo[t] = fft && go;
        wire [8:0] di  = fft ? id2 : i;
        wire [9:0] cx = ins0(di, hlog);
        wire [9:0] cy = cx | (10'd1 << hlog);
        wire [9:0] cxi = cx | (10'd1 << hn_log);   // FFT imaginary parts
        wire [9:0] cyi = cy | (10'd1 << hn_log);
        wire [9:0] r  = (10'd1 << (logn - 4'd1 - hlog)) + ({1'b0, i} >> hlog);   // N/(2h) + c/(2h), c = i with a 0 at hlog
        wire [8:0] pos = r[9:1] - 9'd1;
        wire       r1 = !fft && (hlog == logn - 4'd1);
        wire [9:0] fword = r;                       // FFT root word (one root per word)
        // write addresses in issue order: 16 entries (at most 8 butterflies of a tile are in flight)
        reg [48:0] fifo [0:15];
        reg [3:0]  wp, rp;
        wire [48:0] fh = fifo[rp];
        always @(posedge clk) begin
            // address stage
            s0v[t] <= !rst && dgo;
            s0m[t] <= same;
            s0sx[5*t +: 5] <= sbank(cx);  s0rx[7*t +: 7] <= {2'b0, cx[9:5]};
            s0sy[5*t +: 5] <= sbank(cy);  s0ry[7*t +: 7] <= {2'b0, cy[9:5]};
            s0xo[32*t +: 32] <= (!rst && dgo) ? (32'd1 << sbank(cx)) : 32'd0;
            s0yo[32*t +: 32] <= (!rst && dgo) ? (32'd1 << sbank(cy)) : 32'd0;
            s0xio[32*t +: 32] <= (!rst && dgo && fft) ? (32'd1 << sbank(cxi)) : 32'd0;
            s0yio[32*t +: 32] <= (!rst && dgo && fft) ? (32'd1 << sbank(cyi)) : 32'd0;
            s0rxi[7*t +: 7] <= {2'b0, cxi[9:5]};  s0ryi[7*t +: 7] <= {2'b0, cyi[9:5]};
            s0sxi[5*t +: 5] <= sbank(cxi);  s0syi[5*t +: 5] <= sbank(cyi);
            if (fft) begin
                s0po[4*t +: 4] <= (!rst && go) ? (4'd1 << fword[1:0]) : 4'd0;     // root read stage, ahead of data
                s0pr[10*t +: 10] <= {2'b0, fword[9:2]} + (inverse ? 10'd576 : 10'd384);
                s0rs[4*t +: 4] <= {1'b0, fword[1:0], 1'b0};
            end else begin
                s0po[4*t +: 4] <= (!rst && go && !r1) ? (4'd1 << pos[1:0]) : 4'd0;
                s0pr[10*t +: 10] <= {3'b0, pos[8:2]} + {1'b0, pbase};
                s0rs[4*t +: 4] <= r1 ? 4'd8 : {1'b0, pos[1:0], r[0]};
            end
            if (rst || !layer_on || layer_sw) kr[5*t +: 5] <= 5'd0;
            else if (go) kr[5*t +: 5] <= kr[5*t +: 5] + 5'd1;
            if (rst || !layer_on || layer_sw) rdone[t] <= 1'b0;
            else if (go && ({1'b0, kr[5*t +: 5]} + 6'd1 == bf_per_tile)) rdone[t] <= 1'b1;
            // address FIFO: push at issue, pop at the last write select; the head is decoded one cycle later
            if (rst) begin wp <= 4'd0; rp <= 4'd0; fpar[t] <= 1'b0; end
            else begin
                if (dgo) begin
                    fifo[wp] <= {same, sbank(cx), 2'b0, cx[9:5], sbank(cy), 2'b0, cy[9:5],
                                 sbank(cxi), 2'b0, cxi[9:5], sbank(cyi), 2'b0, cyi[9:5]};
                    wp <= wp + 4'd1;
                end
                if (fft ? f_im[t] : rsp_valid[t]) rp <= rp + 4'd1;
                if (fft && rsp_valid[t]) fpar[t] <= !fpar[t];
            end
            hm[t] <= fh[48];
            hxo[32*t +: 32]  <= 32'd1 << fh[47:43];  hrx[7*t +: 7]  <= fh[42:36];
            hyo[32*t +: 32]  <= 32'd1 << fh[35:31];  hry[7*t +: 7]  <= fh[30:24];
            hxio[32*t +: 32] <= 32'd1 << fh[23:19];  hrxi[7*t +: 7] <= fh[18:12];
            hyio[32*t +: 32] <= 32'd1 << fh[11:7];   hryi[7*t +: 7] <= fh[6:0];
            ypend[t] <= !rst && !fft && rsp_valid[t] && hm[t];
            if (rsp_valid[t]) begin ysbo[32*t +: 32] <= hyo[32*t +: 32]; yrow[7*t +: 7] <= hry[7*t +: 7]; end
        end
        assign f_re[t] = fft && rsp_valid[t] && !fpar[t];      // FFT results alternate: real pair, imaginary pair
        assign f_im[t] = fft && rsp_valid[t] && fpar[t];
        assign fin_now[t] = fft ? f_im[t] : ((rsp_valid[t] && !hm[t]) || ypend[t]);
    end endgenerate

    // pipeline stages s1..s3 (all tiles at once)
    always @(posedge clk) begin
        s1v <= rst ? 16'd0 : s0v;
        s2v <= rst ? 16'd0 : s1v;
        s3v <= rst ? 16'd0 : s2v;
        s1m <= s0m;  s2m <= s1m;  s3m <= s2m;
        s1yo <= rst ? {16*32{1'b0}} : s0yo;
        s1xio <= rst ? {16*32{1'b0}} : s0xio;
        s1yio <= rst ? {16*32{1'b0}} : s0yio;
        s1po <= rst ? 64'd0 : s0po;
        s2po <= rst ? 64'd0 : s1po;
        s1ry <= s0ry;  s1pr <= s0pr;  s2pr <= s1pr;  s1rs <= s0rs;
        s1rxi <= s0rxi;  s1ryi <= s0ryi;
        s1sxi <= s0sxi;  s1syi <= s0syi;
        s1xlo <= nsel_xlo;  s1xhi <= nsel_xhi;  s1ylo <= nsel_ylo;  s1yhi <= nsel_yhi;
        s2ylo <= s1ylo;  s2yhi <= s1yhi;  s2rs <= s1rs;  s3rs <= s2rs;
        s2xlo_i <= isel_xlo;  s2xhi_i <= isel_xhi;  s2ylo_i <= isel_ylo;  s2yhi_i <= isel_yhi;
    end
    // FFT root request stage per tile group (g = t / 6 reads at e + g) and the capture one cycle later
    reg [15:0] rv1, rv2, rv3, rv4;              // FFT root stages: address stage + 1 .. + 4
    always @(posedge clk) begin
        rv1 <= rst ? 16'd0 : fgo;  rv2 <= rst ? 16'd0 : rv1;  rv3 <= rst ? 16'd0 : rv2;  rv4 <= rst ? 16'd0 : rv3;
    end
    reg [16*3-1:0] s0rs_fr;
    integer tf;
    always @* for (tf = 0; tf < 16; tf = tf + 1) s0rs_fr[3*tf +: 3] = s0rs[4*tf +: 3];
    always @(posedge clk) begin
        s1fr <= s0rs_fr;  s2fr <= s1fr;  s3fr <= s2fr;
    end

    // ---------------- memory requests ----------------
    // NTT, per tile: RAM read x from s0; y and the root pack from s0, or from s1 when x and y share a superbank.
    // FFT, per tile: real pair from s0, imaginary pair from s1; root pair word from s0 / s1 / s2 by tile group.
    reg  [16*32-1:0] rxo, ryo, wxo, wyo;
    reg  [16*7-1:0]  rxr, ryr, wxr, wyr;
    reg  [16*4-1:0]  ppo;
    reg  [16*10-1:0] ppr;
    reg  [16*XW-1:0] q_xlo, q_xhi, q_ylo, q_yhi;
    reg  [16*4-1:0]  q_rs;
    reg  [15:0]      q_hold, q_load, n_req, f_rootv;
    reg  [16*3-1:0]  f_rootsel;
    integer tw;
    always @* begin
        for (tw = 0; tw < 16; tw = tw + 1) begin
            if (fft) begin
                rxo[32*tw +: 32] = s0xo[32*tw +: 32] | s1xio[32*tw +: 32];
                ryo[32*tw +: 32] = s0yo[32*tw +: 32] | s1yio[32*tw +: 32];
                rxr[7*tw +: 7]   = s1v[tw] ? s1rxi[7*tw +: 7] : s0rx[7*tw +: 7];
                ryr[7*tw +: 7]   = s1v[tw] ? s1ryi[7*tw +: 7] : s0ry[7*tw +: 7];
                // root read group (t >> 2) mod 3 (model/fft_core_sched.py: no ROM port conflicts)
                case ((tw >> 2) % 3)
                    0: begin ppo[4*tw +: 4] = s0po[4*tw +: 4]; ppr[10*tw +: 10] = s0pr[10*tw +: 10]; end
                    1: begin ppo[4*tw +: 4] = s1po[4*tw +: 4]; ppr[10*tw +: 10] = s1pr[10*tw +: 10]; end
                    default: begin ppo[4*tw +: 4] = s2po[4*tw +: 4]; ppr[10*tw +: 10] = s2pr[10*tw +: 10]; end
                endcase
                case ((tw >> 2) % 3)
                    0: begin f_rootv[tw] = rv2[tw]; f_rootsel[3*tw +: 3] = s1fr[3*tw +: 3]; end
                    1: begin f_rootv[tw] = rv3[tw]; f_rootsel[3*tw +: 3] = s2fr[3*tw +: 3]; end
                    default: begin f_rootv[tw] = rv4[tw]; f_rootsel[3*tw +: 3] = s3fr[3*tw +: 3]; end
                endcase
                // network selects: real pair at e + 1 (s1), imaginary pair at e + 2 (s2)
                q_xlo[XW*tw +: XW] = s2v[tw] ? s2xlo_i[XW*tw +: XW] : s1xlo[XW*tw +: XW];
                q_xhi[XW*tw +: XW] = s2v[tw] ? s2xhi_i[XW*tw +: XW] : s1xhi[XW*tw +: XW];
                q_ylo[XW*tw +: XW] = s2v[tw] ? s2ylo_i[XW*tw +: XW] : s1ylo[XW*tw +: XW];
                q_yhi[XW*tw +: XW] = s2v[tw] ? s2yhi_i[XW*tw +: XW] : s1yhi[XW*tw +: XW];
                q_rs[4*tw +: 4]  = {1'b0, f_rootsel[3*tw+1 +: 2], 1'b0};    // the bank of the tile's root this cycle
                q_load[tw]       = f_rootv[tw];
                q_hold[tw]       = 1'b0;
                n_req[tw]        = 1'b0;
                // writes: real pair, then imaginary pair
                wxo[32*tw +: 32] = ({32{f_re[tw]}} & hxo[32*tw +: 32]) | ({32{f_im[tw]}} & hxio[32*tw +: 32]);
                wyo[32*tw +: 32] = ({32{f_re[tw]}} & hyo[32*tw +: 32]) | ({32{f_im[tw]}} & hyio[32*tw +: 32]);
                wxr[7*tw +: 7]   = f_im[tw] ? hrxi[7*tw +: 7] : hrx[7*tw +: 7];
                wyr[7*tw +: 7]   = f_im[tw] ? hryi[7*tw +: 7] : hry[7*tw +: 7];
            end else begin
                rxo[32*tw +: 32] = s0xo[32*tw +: 32];
                ryo[32*tw +: 32] = (s0yo[32*tw +: 32] & {32{!s0m[tw]}}) | (s1yo[32*tw +: 32] & {32{s1m[tw]}});
                rxr[7*tw +: 7]   = s0rx[7*tw +: 7];
                ryr[7*tw +: 7]   = (s1v[tw] && s1m[tw]) ? s1ry[7*tw +: 7] : s0ry[7*tw +: 7];
                ppo[4*tw +: 4]   = (s0po[4*tw +: 4] & {4{!s0m[tw]}}) | (s1po[4*tw +: 4] & {4{s1m[tw]}});
                ppr[10*tw +: 10] = (s1v[tw] && s1m[tw]) ? s1pr[10*tw +: 10] : s0pr[10*tw +: 10];
                f_rootv[tw] = 1'b0;  f_rootsel[3*tw +: 3] = 3'd0;
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
    reg [8*10-1:0] paddr;
    always @* begin
        paddr = 0;
        for (pb = 0; pb < 4; pb = pb + 1)
            for (tt = 0; tt < 16; tt = tt + 1)
                paddr[10*(pb + (tt < 8 ? 0 : 4)) +: 10] = paddr[10*(pb + (tt < 8 ? 0 : 4)) +: 10] |
                                                         ({10{ppo[4*tt + pb]}} & ppr[10*tt +: 10]);
    end
    genvar gb;
    generate for (gb = 0; gb < 4; gb = gb + 1) begin : g_pack
        localparam [7:0] DIG = 8'd48 + gb;          // "0" + bank
        ntt_core_pack_rom #(.FILE({`NTT_ROM_DIR, "root_pack_b", DIG, ".mem"})) u_rom (.clk(clk),
            .addr_a(paddr[10*gb +: 10]), .addr_b(paddr[10*(gb + 4) +: 10]),
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

    // ---------------- network, tiles and FFT lanes ----------------
    wire [16*32-1:0] op_x, op_y;
    wire [16*64-1:0] op_w;                      // {child 2, child 1} (NTT: the core picks one), FFT {wi, wr}
    wire [16*64-1:0] tile_z;
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
        // FFT: the root {wi, wr} waits in the network's op_w; wi is kept for the second beat
        reg  [31:0]  fwi;
        always @(posedge clk)
            if (s2v[t]) fwi <= op_w[64*t+32 +: 32];
        // NTT: child 1 or 2 of the pack, by the child bit of the stage that accepts
        wire         nchild = (s3v[t] && s3m[t]) ? s3rs[4*t] : s2rs[4*t];
        wire [31:0]  nroot = nchild ? op_w[64*t+32 +: 32] : op_w[64*t +: 32];
        // FFT beats: real pair at s2 (e + 2), imaginary pair at s3 (e + 3)
        assign req_valid[t] = fft ? (s2v[t] || s3v[t]) : n_req[t];
        tile_thu #(.TREN_MANG(1), .PHASE(t / 6)) u_tile (
            .clk(clk), .rst(rst), .en(1'b1), .idle(tile_idle[t]),
            .cfg_we(cfg_we), .cfg_slot(1'b0), .cfg_q(fft ? {28'd0, logn - 4'd1} : cq), .cfg_qinv(cqinv),
            .cfg_floor(1'b0), .cfg_halve(inverse),
            .req_valid(req_valid[t]), .req_ready(req_ready[t]), .req_mode(fft ? 3'd5 : 3'd4), .req_dir(inverse),
            .req_slot(1'b0), .req_sign({1'b0, scale}),
            .req_data({op_y[32*t +: 32], op_x[32*t +: 32]}),
            .req_root(fft ? (s2v[t] ? op_w[64*t +: 32] : fwi) : nroot),
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
    wire last_layer = fft ? (inverse ? (hlog == logn - 4'd2) : (hlog == 4'd0))
                          : (inverse ? (hlog == logn - 4'd1) : (hlog == hmin));
    assign layer_sw = (state == RUN) && layer_on && !last_layer && (lt == delta - 8'd1);
    wire cmd_last_write = (state == RUN) && (wdone + {9'd0, nfin} == cmd_total);
    wire bad = start_fft ? (start_logn > 4'd10)
                         : ((start_logn < 4'd3) || (start_profile == 2'd3) ||
                            (start_profile == 2'd0 && start_logn > 4'd10) || (start_profile == 2'd1 && start_logn > 4'd8) ||
                            (start_profile == 2'd2 && start_logn != 4'd8));
    wire [3:0] start_hmin = (!start_fft && start_profile == 2'd1 && start_logn == 4'd8) ? 4'd1 : 4'd0;
    // FFT: N/4 butterflies per layer, logn - 1 layers; NTT: N/2 per layer, logn - hmin layers
    wire [13:0] start_total = start_fft ? ({10'd0, start_logn - 4'd1} << (start_logn - 4'd2))
                                        : ({10'd0, start_logn - start_hmin} << (start_logn - 4'd1));

    always @(posedge clk) begin
        done <= 1'b0;
        cfg_we <= 1'b0;
        if (rst) begin
            state <= IDLE; layer_on <= 1'b0; error <= 1'b0; cycles <= 32'd0; wdone <= 14'd0; lt <= 8'd0; fft <= 1'b0;
            inverse <= 1'b0; profile <= 2'd0; logn <= 4'd3; hlog <= 4'd0; hmin <= 4'd0; cmd_total <= 14'd0;
        end else begin
            if (busy) cycles <= cycles + 32'd1;
            case (state)
                IDLE: if (start) begin
                    cycles <= 32'd0;
                    error <= bad;
                    if (bad || (start_fft && start_logn < 4'd2)) done <= 1'b1;    // FFT with N <= 2 is the identity
                    else begin
                        fft <= start_fft; inverse <= start_inverse; profile <= start_profile; logn <= start_logn;
                        hmin <= start_hmin;
                        hlog <= start_fft ? (start_inverse ? 4'd0 : start_logn - 4'd2)
                                          : (start_inverse ? start_hmin : start_logn - 4'd1);
                        cmd_total <= start_total;
                        state <= CFG;
                    end
                end
                // Constants (and the tile mode) are taken while every tile is idle. The first layer starts at issue
                // phase 2, the phase the layer tables were made for.
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
