// Random self-check of hdl/net/ntt_bank_net.sv against a direct reference, both lanes, with
// staggered reads. Prints PASS / FAIL.
`timescale 1ns/1ps
module tb_ntt_bank_net;
    localparam integer T = 16, B = 64, P = 8, N = 20000;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg              en, lane32;
    reg  [B*16-1:0]  bank_rd;
    reg  [P*96-1:0]  pack_rd;
    reg  [T*6-1:0]   sel_x, sel_y;
    reg  [T-1:0]     hold_x;
    reg  [T*3-1:0]   sel_pb;
    reg  [T*2-1:0]   sel_child;
    reg  [T*64-1:0]  tile_z;
    reg  [B*5-1:0]   wsel;
    reg  [B-1:0]     wen;
    wire [T*32-1:0]  op_x, op_y, op_w;
    wire [B*16-1:0]  bank_wd;
    wire [B-1:0]     bank_we;

    ntt_bank_net dut (.clk(clk), .en(en), .lane32(lane32), .bank_rd(bank_rd), .pack_rd(pack_rd),
        .sel_x(sel_x), .sel_y(sel_y), .hold_x(hold_x), .sel_pb(sel_pb), .sel_child(sel_child),
        .op_x(op_x), .op_y(op_y), .op_w(op_w), .tile_z(tile_z), .wsel(wsel), .wen(wen),
        .bank_wd(bank_wd), .bank_we(bank_we));

    function [31:0] ref_op(input [B*16-1:0] rd, input integer s, input l32);
        integer e;
        begin
            e = s - (s % 2);
            ref_op = l32 ? {rd[16*(e+1) +: 16], rd[16*e +: 16]} : {16'd0, rd[16*s +: 16]};
        end
    endfunction

    integer c, t, b, s, err, seed;
    reg [31:0] xprev [0:T-1];
    reg [31:0] ex [0:T-1], ey [0:T-1], ew [0:T-1];
    reg [15:0] ewd [0:B-1];
    reg        ewe [0:B-1];
    initial begin
        err = 0; seed = 7; en = 1'b1;
        for (t = 0; t < T; t = t + 1) xprev[t] = 32'd0;
        for (c = 0; c < N; c = c + 1) begin
            @(negedge clk);
            if (c > 1) begin   // cycle 1: the held x of the DUT starts unknown
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
            lane32 = (c / 1000) % 2;
            for (b = 0; b < B; b = b + 1) bank_rd[16*b +: 16] = $random(seed);
            for (b = 0; b < P * 3; b = b + 1) pack_rd[32*b +: 32] = $random(seed);
            for (t = 0; t < T; t = t + 1) begin
                sel_x[6*t +: 6] = $random(seed); sel_y[6*t +: 6] = $random(seed);
                hold_x[t] = $random(seed); sel_pb[3*t +: 3] = $random(seed);
                sel_child[2*t +: 2] = $unsigned($random(seed)) % 3;
                tile_z[64*t +: 64] = {$random(seed), $random(seed)};
            end
            for (b = 0; b < B; b = b + 1) begin wsel[5*b +: 5] = $random(seed); wen[b] = $random(seed); end
            #1;
            for (t = 0; t < T; t = t + 1) begin
                ex[t] = hold_x[t] ? xprev[t] : ref_op(bank_rd, sel_x[6*t +: 6], lane32);
                xprev[t] = ref_op(bank_rd, sel_x[6*t +: 6], lane32);
                ey[t] = ref_op(bank_rd, sel_y[6*t +: 6], lane32);
                ew[t] = pack_rd[96*sel_pb[3*t +: 3] + 32*sel_child[2*t +: 2] +: 32];
            end
            for (b = 0; b < B; b = b + 1) begin
                s = wsel[5*b +: 5];
                ewd[b] = (lane32 && b % 2 == 1) ? tile_z[32*s + 16 +: 16] : tile_z[32*s +: 16];
                ewe[b] = wen[b];
            end
        end
        $display("TOTAL cycles=%0d err=%0d %0s", N, err, err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
