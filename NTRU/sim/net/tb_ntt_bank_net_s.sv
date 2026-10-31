// Random self-check of the generated hdl/net/ntt_bank_net_s.sv: every select is a random index into the
// port's source list (sim/net/structured_lists.svh), and the outputs must equal the listed source.
`timescale 1ns/1ps
module tb_ntt_bank_net_s;
    `include "structured_lists.svh"
    localparam integer T = 16, B = 64, P = 4, N = 20000;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg              en;
    reg  [B*16-1:0]  bank_rd;
    reg  [P*96-1:0]  pack_rd;
    reg  [T*3-1:0]   sel_xlo, sel_ylo;
    reg  [T*3-1:0]   sel_xhi, sel_yhi;
    reg  [T-1:0]     hold_x;
    reg  [31:0]      root1;
    reg  [T*4-1:0]   sel_root;
    reg  [T*64-1:0]  tile_z;
    reg  [B*3-1:0]   wsel;
    reg  [B-1:0]     wen;
    wire [T*32-1:0]  op_x, op_y, op_w;
    wire [B*16-1:0]  bank_wd;
    wire [B-1:0]     bank_we;

    ntt_bank_net_s dut (.clk(clk), .en(en), .bank_rd(bank_rd), .pack_rd(pack_rd),
        .sel_xlo(sel_xlo), .sel_ylo(sel_ylo), .sel_xhi(sel_xhi), .sel_yhi(sel_yhi), .hold_x(hold_x),
        .root1(root1), .sel_root(sel_root), .op_x(op_x), .op_y(op_y), .op_w(op_w),
        .tile_z(tile_z), .wsel(wsel), .wen(wen), .bank_wd(bank_wd), .bank_we(bank_we));

    function integer pick(input integer base, input integer r);
        pick = r % LO_SRC[base];
    endfunction

    integer c, t, b, k, err, seed, port, ilo, ihi, n;
    reg [31:0] xprev [0:T-1];
    reg [31:0] ex [0:T-1], ey [0:T-1], ew [0:T-1], xn;
    reg [15:0] ewd [0:B-1];
    reg        ewe [0:B-1];
    reg [15:0] lo16, hi16;
    initial begin
        err = 0; seed = 11; en = 1'b1;
        for (c = 0; c < N; c = c + 1) begin
            @(negedge clk);
            if (c > 1) begin
                for (t = 0; t < T; t = t + 1)
                    if (op_x[32*t +: 32] !== ex[t] || op_y[32*t +: 32] !== ey[t] || op_w[32*t +: 32] !== ew[t]) begin
                        if (err < 5) $display("  MISMATCH cycle %0d tile %0d", c, t);
                        err = err + 1;
                    end
                for (b = 0; b < B; b = b + 1)
                    if (bank_wd[16*b +: 16] !== ewd[b] || bank_we[b] !== ewe[b]) begin
                        if (err < 5) $display("  MISMATCH cycle %0d bank %0d", c, b);
                        err = err + 1;
                    end
            end
            for (b = 0; b < B; b = b + 1) bank_rd[16*b +: 16] = $random(seed);
            for (b = 0; b < P * 3; b = b + 1) pack_rd[32*b +: 32] = $random(seed);
            root1 = $random(seed);
            for (t = 0; t < T; t = t + 1) begin
                tile_z[64*t +: 64] = {$random(seed), $random(seed)};
                hold_x[t] = $random(seed); sel_root[4*t +: 4] = $unsigned($random(seed)) % (2 * P + 1);
            end
            for (b = 0; b < B; b = b + 1) begin
                wsel[3*b +: 3] = $unsigned($random(seed)) % WR_SRC[17*b];
                wen[b] = $random(seed);
            end
            #1;
            for (t = 0; t < T; t = t + 1) begin
                for (k = 0; k < 2; k = k + 1) begin
                    port = 17 * (2 * t + k);
                    ilo = $unsigned($random(seed)) % LO_SRC[port];
                    ihi = (HI_SRC[port] == 0) ? 0 : $unsigned($random(seed)) % HI_SRC[port];
                    if (k == 0) begin sel_xlo[3*t +: 3] = ilo; sel_xhi[3*t +: 3] = ihi; end
                    else        begin sel_ylo[3*t +: 3] = ilo; sel_yhi[3*t +: 3] = ihi; end
                    lo16 = bank_rd[16*LO_SRC[port + 1 + ilo] +: 16];
                    hi16 = (HI_SRC[port] == 0) ? 16'd0 : bank_rd[16*HI_SRC[port + 1 + ihi] +: 16];
                    xn = {hi16, lo16};
                    if (k == 0) begin ex[t] = hold_x[t] ? xprev[t] : xn; xprev[t] = xn; end
                    else ey[t] = xn;
                end
                k = sel_root[4*t +: 4];
                ew[t] = (k == 2 * P) ? root1 : pack_rd[96*(k/2) + 32*(k%2 + 1) +: 32];
            end
            for (b = 0; b < B; b = b + 1) begin
                ewd[b] = tile_z[WR_SRC[17*b + 1 + wsel[3*b +: 3]] +: 16];
                ewe[b] = wen[b];
            end
        end
        $display("TOTAL cycles=%0d err=%0d %0s", N, err, err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
