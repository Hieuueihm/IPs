// Testbench for the tile test block (spec 2.0, 11_kiem_thu_tile.md). Black-box: uses only the
// ports of 10_hop_dong_tile.md section 2, so it runs on any RTL with that interface.
//
// Vector source (one of):
//   +FILE=<vector file> +KIND=0 raw32 | 1 fft32 | 2 ntt
//   +CHAIN=<asset dir>  mode-change chain over raw32, fft32, ntt (group B case
//                       "Đổi chế độ và hằng số"): q12289 butterfly -> FFT32 -> q8380417 ->
//                       raw product -> NTRUGen prime GS with halving -> q3329 modmul
// Stimulus:
//   +STALL=<percent en = 0>  +BURST=1 adds en = 0 bursts up to 64 cycles
//   +SPARSE=<percent req_valid = 0>  +REP=<repeat each group>  +SEED=<n>
// Extra checks (each adds errors to the total):
//   always     rsp_valid = 0 while en = 0; rsp_data, rsp_tag, idle unchanged across an en = 0 cycle
//   +CFGBUSY=1 drive cfg_we = 1 with random constants on every cycle with idle = 0
//   +RESETAT=k in every group, pulse rst after k accepted requests; then require no result
//              and idle = 1 for 64 cycles, rewrite the constants and rerun the group
//   +MIX=1     NTT file: pairs of groups with different q in modulus slots 0 and 1, requests interleaved
//              at random with req_slot (lệnh nhiều prime, mỗi tile hai modulus); groups are in
//              increasing q, so one pair puts the largest small q next to the smallest large q
//   +SCHED=1   run every group twice from reset with the same en/valid pattern, first with data and
//              roots all zero, and require identical per-cycle req_ready/rsp_valid traces
// Testbench self-checks (the run must FAIL):
//   +CORRUPT=1 flip one bit of the first expected result
//   +SWAPEXP=1 swap the expected results (and tags) of the first two requests
// Rate: a group run with no stall, no idle request slot and at least 1000 requests must reach 98% of
// the rate of 10_hop_dong_tile.md section 6 (NTT every 3 cycles for TREN_MANG = 1, else every cycle).
// Prints one line per group (cases, errors, latency min..max in en = 1 cycles, rate) and a TOTAL.
`timescale 1ns/1ps
module tb_tile_thu;
    parameter integer TREN_MANG = 3;
    localparam integer MAXN = 20000;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg          rst, en, cfg_we, cfg_floor, cfg_halve;
    reg          cfg_slot = 1'b0, req_slot = 1'b0;
    reg  [31:0]  cfg_q, cfg_qinv;
    reg          req_valid, req_dir;
    reg  [2:0]   req_mode;
    reg  [1:0]   req_sign;
    reg  [63:0]  req_data;
    reg  [31:0]  req_root;
    reg  [7:0]   req_tag;
    wire         idle, req_ready, rsp_valid;
    wire [64:0]  rsp_data;
    wire [7:0]   rsp_tag;

    tile_thu #(.TREN_MANG(TREN_MANG)) dut (
        .clk(clk), .rst(rst), .en(en), .idle(idle),
        .cfg_we(cfg_we), .cfg_slot(cfg_slot), .cfg_q(cfg_q), .cfg_qinv(cfg_qinv),
        .cfg_floor(cfg_floor), .cfg_halve(cfg_halve),
        .req_valid(req_valid), .req_ready(req_ready), .req_mode(req_mode), .req_dir(req_dir), .req_slot(req_slot),
        .req_sign(req_sign), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));

    // vector store
    reg [2:0]   v_mode  [0:MAXN-1];
    reg [31:0]  v_q     [0:MAXN-1];
    reg [31:0]  v_qi    [0:MAXN-1];
    reg         v_dir   [0:MAXN-1];
    reg         v_halve [0:MAXN-1];
    reg         v_floor [0:MAXN-1];
    reg [1:0]   v_sign  [0:MAXN-1];
    reg [63:0]  v_d     [0:MAXN-1];
    reg [31:0]  v_r     [0:MAXN-1];
    reg [64:0]  v_z     [0:MAXN-1];
    integer n;

    reg [8*256-1:0] fname, cdir;
    integer kind, stall, burst, sparse, rep, seed, cfgbusy, resetat, sched, corrupt, swapexp;
    integer rs;             // random state, reloaded per pass so SCHED passes see the same pattern

    function integer rnd(input integer m);
        integer r;
        begin
            r = $random(rs);
            rnd = (r & 32'h7fffffff) % m;
        end
    endfunction

    task load(input [8*256-1:0] path, input integer k);
        integer fd, c, rc;
        reg [31:0] a, b, sa, sb, fl, q, qi, md, dr, hv;
        reg [31:0] d0, d1, r0, z0, z1;
        reg [64:0] p65;
        reg [8*512-1:0] line;
        begin
            fd = $fopen(path, "r");
            if (fd == 0) begin $display("ERROR cannot open %0s", path); $finish; end
            while (!$feof(fd)) begin
                c = $fgetc(fd);
                if (c == "#") rc = $fgets(line, fd);
                else if (c == " " || c == "\n" || c == "\r" || c == "\t" || c == -1) ;
                else begin
                    rc = $ungetc(c, fd);
                    v_d[n] = 0; v_r[n] = 0; v_z[n] = 0; v_dir[n] = 0; v_halve[n] = 0;
                    v_floor[n] = 0; v_sign[n] = 0; v_q[n] = 0; v_qi[n] = 0;
                    if (k == 0) begin
                        rc = $fscanf(fd, "%h %h %h %h %h", sa, sb, a, b, p65);
                        v_mode[n] = 0; v_sign[n] = {sb[0], sa[0]};
                        v_d[n] = {b, a}; v_z[n] = p65;
                    end else if (k == 1) begin
                        rc = $fscanf(fd, "%h %h %h %h", fl, a, b, z0);
                        v_mode[n] = 1; v_floor[n] = fl[0];
                        v_d[n] = {b, a}; v_z[n] = {33'd0, z0};
                    end else begin
                        rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h",
                                     q, qi, md, dr, hv, d0, d1, r0, z0, z1);
                        v_mode[n] = md[2:0]; v_q[n] = q; v_qi[n] = qi;
                        v_dir[n] = dr[0]; v_halve[n] = hv[0];
                        v_d[n] = {d1, d0}; v_r[n] = r0; v_z[n] = {1'b0, z1, z0};
                    end
                    n = n + 1;
                end
            end
            $fclose(fd);
        end
    endtask

    function same_group(input integer i, input integer j);
        same_group = v_mode[i] == v_mode[j] && v_q[i] == v_q[j] &&
                     v_qi[i] == v_qi[j] && v_dir[i] == v_dir[j] && v_halve[i] == v_halve[j] &&
                     v_floor[i] == v_floor[j] && v_sign[i] == v_sign[j];
    endfunction

    integer ecyc;           // cycles with en = 1
    integer acc_cyc [0:255];
    integer total_cases, total_err, lat_min, lat_max, first_acc, last_acc, timeout;
    integer burst_left, trace_h, trace_n;

    task cycle_inputs(input integer want_req);
        begin
            if (burst != 0 && burst_left == 0 && rnd(1000) < 3) burst_left = 1 + rnd(64);
            if (burst_left > 0) begin en = 1'b0; burst_left = burst_left - 1; end
            else en = (stall == 0) ? 1'b1 : (rnd(100) >= stall);
            req_valid = want_req && (sparse == 0 || rnd(100) >= sparse);
        end
    endtask

    // Wait for idle with en = 1, then write the constants of group g0. A block that never returns to
    // idle (a lost result) counts as an error and is reset, so the run ends with FAIL instead of hanging.
    task write_cfg(input integer g0);
        integer w;
        begin
            @(negedge clk); rst = 1'b0; en = 1'b1; req_valid = 1'b0; cfg_we = 1'b0; #1;
            w = 0;
            while (!idle) begin
                @(negedge clk); en = 1'b1; req_valid = 1'b0; #1;
                w = w + 1;
                if (w == 10000) begin
                    $display("  ERROR idle = 0 for 10000 cycles before a constant write; resetting");
                    total_err = total_err + 1;
                    rst = 1'b1; @(negedge clk); rst = 1'b0; #1;
                end
            end
            cfg_we = 1'b1; cfg_q = v_q[g0]; cfg_qinv = v_qi[g0];
            cfg_floor = v_floor[g0]; cfg_halve = v_halve[g0];
            req_mode = v_mode[g0]; req_dir = v_dir[g0]; req_sign = v_sign[g0];
            @(negedge clk); cfg_we = 1'b0;
        end
    endtask

    // One pass over a group. zero = 1: data and roots forced to 0, results not checked.
    // Returns the error count; the per-cycle req_ready/rsp_valid trace goes to trace_h.
    task run_pass(input integer g0, input integer cnt, input integer zero, output integer e);
        integer i, j, tot, lat, idx, first, did_reset, k, prev_ok;
        reg [64:0]  prev_data;
        reg [7:0]   prev_tag;
        reg         prev_idle, prev_en;
        begin
            // SCHED: both passes start from the same state (free-running slot counters included)
            if (sched != 0) begin
                @(negedge clk); rst = 1'b1; en = 1'b1; req_valid = 1'b0; cfg_we = 1'b0;
                req_mode = v_mode[g0]; req_dir = v_dir[g0]; req_sign = v_sign[g0];
                @(negedge clk); rst = 1'b0;
            end
            write_cfg(g0);
            tot = cnt * rep; i = 0; j = 0; e = 0; did_reset = 0;
            lat_min = 1 << 30; lat_max = 0; first_acc = -1; last_acc = 0; timeout = 0; first = 1;
            trace_h = 17; trace_n = 0; prev_ok = 0; prev_en = 1'b1;
            while (j < tot) begin
                if (!first) @(negedge clk);
                first = 0;
                cycle_inputs(i < tot);
                idx = g0 + (i % cnt);
                req_data = zero ? 64'd0 : v_d[idx];
                req_root = zero ? 32'd0 : v_r[idx];
                req_tag = i[7:0];
                cfg_we = 1'b0;
                cfg_q = v_q[g0]; cfg_qinv = v_qi[g0];
                cfg_floor = v_floor[g0]; cfg_halve = v_halve[g0];
                #1;
                // writes while busy must be ignored
                if (cfgbusy != 0 && !idle) begin
                    cfg_we = 1'b1; cfg_q = $random(rs); cfg_qinv = $random(rs);
                    cfg_floor = rnd(2); cfg_halve = rnd(2);
                end
                // en = 0 holds everything
                if (!en && rsp_valid) begin
                    if (e < 5) $display("  ERROR rsp_valid = 1 while en = 0");
                    e = e + 1;
                end
                if (prev_ok && !prev_en && (rsp_data !== prev_data || rsp_tag !== prev_tag || idle !== prev_idle)) begin
                    if (e < 5) $display("  ERROR output changed across an en = 0 cycle");
                    e = e + 1;
                end
                prev_data = rsp_data; prev_tag = rsp_tag; prev_idle = idle; prev_en = en; prev_ok = 1;
                trace_h = trace_h * 31 + {req_ready, rsp_valid};
                trace_n = trace_n + 1;
                if (en && req_valid && req_ready) begin
                    acc_cyc[i % 256] = ecyc;
                    if (first_acc < 0) first_acc = ecyc;
                    last_acc = ecyc;
                    i = i + 1;
                end
                if (rsp_valid) begin
                    idx = g0 + (j % cnt);
                    if (swapexp != 0 && j < 2 && cnt > 1) idx = g0 + 1 - j;
                    if (!zero && (rsp_data !== v_z[idx] ||
                                  rsp_tag !== ((swapexp != 0 && j < 2 && cnt > 1) ? 1 - j : j[7:0]))) begin
                        if (e < 5) $display("  MISMATCH case %0d (line %0d): got %h tag %h, want %h",
                                            j, idx, rsp_data, rsp_tag, v_z[idx]);
                        e = e + 1;
                    end
                    lat = ecyc - acc_cyc[j % 256];
                    if (lat < lat_min) lat_min = lat;
                    if (lat > lat_max) lat_max = lat;
                    j = j + 1;
                end
                if (en) ecyc = ecyc + 1;
                // reset in the middle of the group, then start the group again
                if (resetat >= 0 && !did_reset && i == resetat && i > j) begin
                    did_reset = 1;
                    @(negedge clk); rst = 1'b1; en = 1'b1; req_valid = 1'b0; cfg_we = 1'b0;
                    @(negedge clk); rst = 1'b0; en = 1'b1;
                    for (k = 0; k < 64; k = k + 1) begin
                        #1;
                        if (rsp_valid || !idle) begin
                            if (e < 5) $display("  ERROR after reset: rsp_valid=%b idle=%b", rsp_valid, idle);
                            e = e + 1;
                        end
                        @(negedge clk);
                    end
                    write_cfg(g0);
                    i = 0; j = 0; first = 1; prev_ok = 0;
                end
                timeout = timeout + 1;
                if (timeout > 200 * tot + 10000) begin
                    $display("  TIMEOUT sent %0d received %0d of %0d", i, j, tot);
                    e = e + 1; j = tot;
                end
            end
            cfg_we = 1'b0;
        end
    endtask

    task run_group(input integer g0, input integer cnt);
        integer e, ez, hz, nz;
        real rate, want;
        begin
            ez = 0;
            if (sched != 0) begin
                rs = seed; burst_left = 0;
                run_pass(g0, cnt, 1, ez);
                hz = trace_h; nz = trace_n;
            end
            rs = seed; burst_left = 0;
            run_pass(g0, cnt, 0, e);
            e = e + ez;
            if (sched != 0 && (hz !== trace_h || nz !== trace_n)) begin
                $display("  ERROR schedule depends on data: %0d / %0d cycles, trace %h / %h", nz, trace_n, hz, trace_h);
                e = e + 1;
            end
            rate = (last_acc > first_acc) ? (1.0 * cnt * rep) / (last_acc - first_acc + 1) : 1.0;
            want = (v_mode[g0] >= 2 && TREN_MANG == 1) ? 1.0 / 3.0 : 1.0;
            if (stall == 0 && burst == 0 && sparse == 0 && resetat < 0 && cnt * rep >= 1000 && rate < 0.98 * want) begin
                $display("  ERROR rate %0.4f below 98%% of %0.4f", rate, want);
                e = e + 1;
            end
            $display("GROUP mode=%0d q=%0d dir=%0d halve=%0d floor=%0d sign=%0d cases=%0d err=%0d lat=%0d..%0d rate=%0.4f",
                     v_mode[g0], v_q[g0], v_dir[g0], v_halve[g0], v_floor[g0], v_sign[g0],
                     cnt * rep, e, lat_min, lat_max, rate);
            total_cases = total_cases + cnt * rep;
            total_err = total_err + e;
        end
    endtask

    // First group (start, length) matching a chain step.
    task find_group(input integer step, output integer gs, output integer gl);
        integer g, h, ok;
        begin
            gs = -1; gl = 0; g = 0;
            while (g < n && gs < 0) begin
                h = g;
                while (h < n && same_group(g, h)) h = h + 1;
                case (step)
                    0: ok = v_mode[g] == 4 && v_q[g] == 12289;
                    1: ok = v_mode[g] == 1 && !v_floor[g];
                    2: ok = v_mode[g] == 4 && v_q[g] == 8380417;
                    3: ok = v_mode[g] == 0;
                    4: ok = v_mode[g] == 4 && v_q[g] == 2147473409 && v_dir[g] && v_halve[g];
                    default: ok = v_mode[g] == 2 && v_q[g] == 3329;
                endcase
                if (ok) begin gs = g; gl = h - g; end
                g = h;
            end
            if (gs < 0) begin $display("ERROR chain step %0d has no group", step); $finish; end
        end
    endtask

    // +MIX=1: two groups of the same mode, direction and halving but different q go into modulus
    // slots 0 and 1; their requests are interleaved at random (req_slot per request) and every result
    // must match its own group. Stall, burst and sparse stimulus apply; en = 0 hold checks apply.
    reg [64:0] mx_z [0:MAXN-1];
    reg [7:0]  mx_t [0:MAXN-1];
    task run_mix(input integer ga, input integer na, input integer gb, input integer nb);
        integer ia, ib, i, j, e, tot, pick, idx, timeout2;
        reg [64:0] prev_data;
        reg [7:0]  prev_tag;
        reg        prev_idle, prev_en, prev_ok;
        begin
            cfg_slot = 1'b0; write_cfg(ga);
            cfg_slot = 1'b1; write_cfg(gb);
            cfg_slot = 1'b0;
            ia = 0; ib = 0; i = 0; j = 0; e = 0; tot = na + nb; timeout2 = 0; prev_ok = 0;
            pick = rnd(2);
            while (j < tot) begin
                @(negedge clk);
                cycle_inputs(i < tot);
                if (ia >= na) pick = 1; else if (ib >= nb) pick = 0;
                idx = pick ? gb + ib : ga + ia;
                req_slot = pick;
                req_data = v_d[idx]; req_root = v_r[idx]; req_tag = i[7:0];
                cfg_we = 1'b0;
                #1;
                if (!en && rsp_valid) begin
                    if (e < 5) $display("  ERROR rsp_valid = 1 while en = 0");
                    e = e + 1;
                end
                if (prev_ok && !prev_en && (rsp_data !== prev_data || rsp_tag !== prev_tag || idle !== prev_idle)) begin
                    if (e < 5) $display("  ERROR output changed across an en = 0 cycle");
                    e = e + 1;
                end
                prev_data = rsp_data; prev_tag = rsp_tag; prev_idle = idle; prev_en = en; prev_ok = 1;
                if (en && req_valid && req_ready) begin
                    mx_z[i % MAXN] = v_z[idx]; mx_t[i % MAXN] = i[7:0];
                    if (pick) ib = ib + 1; else ia = ia + 1;
                    i = i + 1;
                    pick = rnd(2);
                end
                if (rsp_valid) begin
                    if (rsp_data !== mx_z[j % MAXN] || rsp_tag !== mx_t[j % MAXN]) begin
                        if (e < 5) $display("  MISMATCH mixed result %0d: got %h tag %h, want %h tag %h",
                                            j, rsp_data, rsp_tag, mx_z[j % MAXN], mx_t[j % MAXN]);
                        e = e + 1;
                    end
                    j = j + 1;
                end
                if (en) ecyc = ecyc + 1;
                timeout2 = timeout2 + 1;
                if (timeout2 > 200 * tot + 10000) begin
                    $display("  TIMEOUT sent %0d received %0d of %0d", i, j, tot);
                    e = e + 1; j = tot;
                end
            end
            req_slot = 1'b0;
            $display("MIX mode=%0d q=%0d,%0d dir=%0d halve=%0d cases=%0d err=%0d",
                     v_mode[ga], v_q[ga], v_q[gb], v_dir[ga], v_halve[ga], tot, e);
            total_cases = total_cases + tot;
            total_err = total_err + e;
        end
    endtask

    integer g, h, s, gs, gl, mix, ng, gi, gj;
    integer gstart [0:255];
    integer glen   [0:255];
    initial begin
        n = 0;
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        if (!$value$plusargs("BURST=%d", burst)) burst = 0;
        if (!$value$plusargs("SPARSE=%d", sparse)) sparse = 0;
        if (!$value$plusargs("REP=%d", rep)) rep = 1;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("CFGBUSY=%d", cfgbusy)) cfgbusy = 0;
        if (!$value$plusargs("RESETAT=%d", resetat)) resetat = -1;
        if (!$value$plusargs("SCHED=%d", sched)) sched = 0;
        if (!$value$plusargs("CORRUPT=%d", corrupt)) corrupt = 0;
        if (!$value$plusargs("SWAPEXP=%d", swapexp)) swapexp = 0;
        if (!$value$plusargs("MIX=%d", mix)) mix = 0;
        if ($value$plusargs("CHAIN=%s", cdir)) begin
            load({cdir, "/raw32.txt"}, 0);
            load({cdir, "/fft32.txt"}, 1);
            load({cdir, "/ntt.txt"}, 2);
            fname = "chain";
        end else begin
            if (!$value$plusargs("FILE=%s", fname)) begin $display("need +FILE or +CHAIN"); $finish; end
            if (!$value$plusargs("KIND=%d", kind)) kind = 2;
            load(fname, kind);
        end
        if (corrupt != 0) v_z[0][0] = ~v_z[0][0];
        $display("TREN_MANG=%0d source=%0s vectors=%0d stall=%0d burst=%0d sparse=%0d rep=%0d cfgbusy=%0d resetat=%0d sched=%0d",
                 TREN_MANG, fname, n, stall, burst, sparse, rep, cfgbusy, resetat, sched);

        rst = 1'b1; en = 1'b1; cfg_we = 1'b0; cfg_floor = 0; cfg_halve = 0;
        cfg_q = 0; cfg_qinv = 0; req_valid = 0; req_dir = 0; req_mode = 0; req_sign = 0;
        req_data = 0; req_root = 0; req_tag = 0;
        ecyc = 0; total_cases = 0; total_err = 0; burst_left = 0; rs = seed;
        repeat (3) @(negedge clk);
        rst = 1'b0;

        if (fname == "chain") begin
            for (s = 0; s < 6; s = s + 1) begin
                find_group(s, gs, gl);
                run_group(gs, gl);
            end
        end else if (mix != 0) begin
            ng = 0; g = 0;
            while (g < n) begin
                h = g;
                while (h < n && same_group(g, h)) h = h + 1;
                gstart[ng] = g; glen[ng] = h - g; ng = ng + 1;
                g = h;
            end
            for (gi = 0; gi < ng; gi = gi + 1) begin
                // partner: the next group (cyclically) with the same mode, direction, halving, other q
                gj = (gi + 1) % ng;
                while (gj != gi && !(v_mode[gstart[gj]] == v_mode[gstart[gi]] &&
                                     v_dir[gstart[gj]] == v_dir[gstart[gi]] && v_halve[gstart[gj]] == v_halve[gstart[gi]] &&
                                     v_q[gstart[gj]] != v_q[gstart[gi]]))
                    gj = (gj + 1) % ng;
                if (gj != gi && v_mode[gstart[gi]] >= 2) run_mix(gstart[gi], glen[gi], gstart[gj], glen[gj]);
            end
        end else begin
            g = 0;
            while (g < n) begin
                h = g;
                while (h < n && same_group(g, h)) h = h + 1;
                run_group(g, h - g);
                g = h;
            end
        end
        $display("TOTAL cases=%0d err=%0d %0s", total_cases, total_err, total_err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
