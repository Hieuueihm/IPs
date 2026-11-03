// Testbench of the minimal core (hdl/core_ntt/ntt_core.sv). Golden cases from sim/core_ntt/vectors.txt (NTT: 1.0
// kernel fixtures for profiles 0, 1; spec 2.0 kernel assets for profile 2), vectors_fft.txt (FFT formats 0, 1, 2,
// written as profile 3, 4, 5: op 0 = FFT, 1 = FFT ngược; 1.0 kernel fixtures, each value as L = 1 / 2 / 4 words of
// 32 bit, low first) and vectors_p3.txt (NTT profile 3, written as 6: a loaded prime with its root tables, skipped last
// layers hmin), all written by scripts/gen_ntt_core.py.
// Per case: (profile 3: write a slot and its root packs, both directions, at a position that changes per case) load the
// words (word w in cells 2w, 2w + 1), run, read back, compare.
// Measures (architecture section 6, hypothesis 4): (a) first RAM read of the command to last RAM write, plus 1;
// (b) the core's cycle counter (start to done). Also checks that every request finds its tile ready, and once that a
// profile-3 command on a slot never written ends with error.
// +FILE=<vectors>  +ONLY=<n> runs only case n
`timescale 1ns/1ps
module tb_ntt_core;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg          rst, load_valid, read_valid, start, start_inverse, start_fft;
    reg  [1:0]   start_fmt, start_hmin;
    reg  [3:0]   start_slot;
    reg  [9:0]   load_line, read_line;
    reg  [127:0] load_data;
    reg  [1:0]   start_profile;
    reg  [3:0]   start_logn;
    reg          slot_we, pack_we, pack_inv;
    reg  [3:0]   slot_idx, slot_logn;
    reg  [31:0]  slot_q, slot_qinv, slot_root1f, slot_root1i;
    reg  [8:0]   slot_base, pack_pos;
    reg  [95:0]  pack_data;
    wire         read_rsp_valid, busy, done, error;
    wire [127:0] read_data;
    wire [31:0]  cycles;
    ntt_core dut (.clk(clk), .rst(rst), .load_valid(load_valid), .load_line(load_line), .load_data(load_data),
        .read_valid(read_valid), .read_line(read_line), .read_rsp_valid(read_rsp_valid), .read_data(read_data),
        .start(start), .start_fft(start_fft), .start_fmt(start_fmt), .start_inverse(start_inverse),
        .start_profile(start_profile), .start_logn(start_logn), .start_slot(start_slot), .start_hmin(start_hmin),
        .slot_we(slot_we), .slot_idx(slot_idx), .slot_q(slot_q), .slot_qinv(slot_qinv), .slot_root1f(slot_root1f),
        .slot_root1i(slot_root1i), .slot_base(slot_base), .slot_logn(slot_logn),
        .pack_we(pack_we), .pack_inv(pack_inv), .pack_pos(pack_pos), .pack_data(pack_data),
        .busy(busy), .done(done), .error(error), .cycles(cycles));

    // measurement and ready check
    integer cyc = 0, first_rd, last_wr, not_ready;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (busy && |dut.m_re && first_rd < 0) first_rd <= cyc;
        if (busy && |dut.m_we) last_wr <= cyc;
        if (|(dut.req_valid & ~dut.req_ready)) not_ready <= not_ready + 1;
    end

    reg [31:0] a [0:4095];
    reg [31:0] e [0:4095];
    reg [31:0] got [0:4095];
    reg [31:0] tg [0:1023];
    reg [31:0] ti [0:1023];
    integer fd, rc, prof, logn, op, hm, n, i, k, err, total_err, ncase, only, w, ng, gp, base, slot, nl;
    reg [31:0] q, qi;
    reg [8*256-1:0] fname;

    task write_packs(input integer inv, input integer b);
        integer g;
        begin
            for (g = 1; g < ng / 2; g = g + 1) begin
                @(negedge clk);
                pack_we = 1'b1; pack_inv = inv; pack_pos = b + g - 1;
                pack_data = inv ? {ti[2*g+1], ti[2*g], ti[g]} : {tg[2*g+1], tg[2*g], tg[g]};
            end
            @(negedge clk); pack_we = 1'b0;
        end
    endtask

    initial begin
        if (!$value$plusargs("FILE=%s", fname)) fname = "sim/core_ntt/vectors.txt";
        if (!$value$plusargs("ONLY=%d", only)) only = -1;
        rst = 1'b1; load_valid = 0; read_valid = 0; start = 0; start_inverse = 0; start_fft = 0; start_profile = 0; start_logn = 0;
        start_fmt = 0; start_slot = 0; start_hmin = 0; slot_we = 0; pack_we = 0; pack_inv = 0; pack_pos = 0; pack_data = 0;
        slot_idx = 0; slot_logn = 0; slot_q = 0; slot_qinv = 0; slot_root1f = 0; slot_root1i = 0; slot_base = 0;
        load_line = 0; read_line = 0; load_data = 0;
        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);
        total_err = 0; ncase = 0;
        // a profile-3 command on a slot that was never written must end at once with error
        start = 1'b1; start_profile = 2'd3; start_slot = 4'd15; start_logn = 4'd4; start_hmin = 2'd0;
        @(negedge clk); start = 1'b0;
        w = 0;
        while (!done && w < 10) begin @(negedge clk); w = w + 1; end
        if (!error || w >= 10) begin $display("  ERROR profile 3 on an empty slot did not end with error"); total_err = total_err + 1; end
        fd = $fopen(fname, "r");
        if (fd == 0) begin $display("ERROR cannot open %0s", fname); $finish; end
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%d %d %d", prof, logn, op);
            if (rc != 3) begin rc = $fgetc(fd); end
            else begin
                hm = 0;
                if (prof == 6) begin
                    rc = $fscanf(fd, "%d %h %h %h", hm, q, qi, ng);
                    for (i = 0; i < ng; i = i + 1) rc = $fscanf(fd, "%h", tg[i]);
                    for (i = 0; i < ng; i = i + 1) rc = $fscanf(fd, "%h", ti[i]);
                end
                n = (1 << logn) << ((prof >= 3 && prof <= 5) ? prof - 3 : 0);     // 32-bit words
                for (i = 0; i < n; i = i + 1) rc = $fscanf(fd, "%h", a[i]);
                for (i = 0; i < n; i = i + 1) rc = $fscanf(fd, "%h", e[i]);
                if (only < 0 || only == ncase) begin
                    if (prof == 6) begin
                        // slot and packs: a different slot and pack position per case (positions are multiples of 4)
                        slot = ncase % 16;
                        gp = (ng / 2 > 1) ? ng / 2 - 1 : 0;
                        base = ((ncase * 28) % (512 - gp)) & ~3;
                        @(negedge clk);
                        slot_we = 1'b1; slot_idx = slot; slot_q = q; slot_qinv = qi; slot_root1f = tg[1]; slot_root1i = ti[1];
                        slot_base = base; slot_logn = logn;
                        @(negedge clk); slot_we = 1'b0;
                        write_packs(0, base);
                        write_packs(1, base);
                    end
                    // load: line l = words 4l .. 4l + 3 (a last partial line is padded with zeros)
                    nl = (n + 3) / 4;
                    for (k = 0; k < nl; k = k + 1) begin
                        @(negedge clk);
                        load_valid = 1'b1; load_line = k;
                        load_data = {(4*k+3 < n) ? a[4*k+3] : 32'd0, (4*k+2 < n) ? a[4*k+2] : 32'd0,
                                     (4*k+1 < n) ? a[4*k+1] : 32'd0, a[4*k]};
                    end
                    @(negedge clk); load_valid = 1'b0;
                    first_rd = -1; last_wr = -1; not_ready = 0;
                    start = 1'b1; start_fft = (prof >= 3 && prof <= 5);
                    start_inverse = (prof >= 3 && prof <= 5) ? (op == 1) : (op == 6);
                    start_fmt = (prof >= 3 && prof <= 5) ? prof - 3 : 0;
                    start_profile = (prof == 6) ? 2'd3 : prof; start_logn = logn;
                    start_slot = (prof == 6) ? slot : 0; start_hmin = hm;
                    @(negedge clk); start = 1'b0;
                    w = 0;
                    while (!done && w < 200000) begin @(negedge clk); w = w + 1; end
                    // read back
                    for (k = 0; k < nl; k = k + 1) begin
                        read_valid = 1'b1; read_line = k;
                        @(negedge clk); read_valid = 1'b0;
                        while (!read_rsp_valid) @(negedge clk);
                        {got[4*k+3], got[4*k+2], got[4*k+1], got[4*k]} = read_data;
                    end
                    err = (w >= 200000) || error || (not_ready != 0);
                    for (i = 0; i < n; i = i + 1)
                        if (got[i] !== e[i]) begin
                            if (err < 40) $display("  MISMATCH profile %0d logn %0d op %0d coeff %0d: got %h want %h",
                                                  prof, logn, op, i, got[i], e[i]);
                            err = err + 1;
                        end
                    $display("CASE %0d profile=%0d logn=%0d op=%0d err=%0d cycles_a=%0d cycles_b=%0d not_ready=%0d hmin=%0d q=%0d",
                             ncase, prof, logn, op, err, last_wr - first_rd + 1, cycles, not_ready, hm, q);
                    total_err = total_err + err;
                end
                ncase = ncase + 1;
            end
        end
        $display("TOTAL cases=%0d err=%0d %0s", ncase, total_err, total_err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
