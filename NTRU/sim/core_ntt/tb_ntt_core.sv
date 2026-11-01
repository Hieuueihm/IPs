// Testbench of the minimal NTT core (hdl/core_ntt/ntt_core.sv). Golden cases from sim/core_ntt/vectors.txt (1.0
// kernel fixtures for profiles 0, 1; spec 2.0 kernel assets for profile 2), written by scripts/gen_ntt_core.py.
// Per case: load the polynomial in format 4 (coefficient c in cells 2c, 2c + 1), run, read back, compare.
// Measures (architecture section 6, hypothesis 4): (a) first RAM read of the command to last RAM write, plus 1;
// (b) the core's cycle counter (start to done). Also checks that every request finds its tile ready.
// +FILE=<vectors>  +ONLY=<n> runs only case n
`timescale 1ns/1ps
module tb_ntt_core;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg          rst, load_valid, read_valid, start, start_inverse;
    reg  [9:0]   load_line, read_line;
    reg  [127:0] load_data;
    reg  [1:0]   start_profile;
    reg  [3:0]   start_logn;
    wire         read_rsp_valid, busy, done, error;
    wire [127:0] read_data;
    wire [31:0]  cycles;
    ntt_core dut (.clk(clk), .rst(rst), .load_valid(load_valid), .load_line(load_line), .load_data(load_data),
        .read_valid(read_valid), .read_line(read_line), .read_rsp_valid(read_rsp_valid), .read_data(read_data),
        .start(start), .start_inverse(start_inverse), .start_profile(start_profile), .start_logn(start_logn),
        .busy(busy), .done(done), .error(error), .cycles(cycles));

    // measurement and ready check
    integer cyc = 0, first_rd, last_wr, not_ready;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (busy && |dut.m_re && first_rd < 0) first_rd <= cyc;
        if (busy && |dut.m_we) last_wr <= cyc;
        if (|(dut.req_valid & ~dut.req_ready)) not_ready <= not_ready + 1;
    end

    reg [31:0] a [0:1023];
    reg [31:0] e [0:1023];
    reg [31:0] got [0:1023];
    integer fd, rc, prof, logn, op, n, i, k, err, total_err, ncase, only, w;
    reg [8*256-1:0] fname;
    initial begin
        if (!$value$plusargs("FILE=%s", fname)) fname = "sim/core_ntt/vectors.txt";
        if (!$value$plusargs("ONLY=%d", only)) only = -1;
        rst = 1'b1; load_valid = 0; read_valid = 0; start = 0; start_inverse = 0; start_profile = 0; start_logn = 0;
        load_line = 0; read_line = 0; load_data = 0;
        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);
        fd = $fopen(fname, "r");
        if (fd == 0) begin $display("ERROR cannot open %0s", fname); $finish; end
        total_err = 0; ncase = 0;
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%d %d %d", prof, logn, op);
            if (rc != 3) begin rc = $fgetc(fd); end
            else begin
                n = 1 << logn;
                for (i = 0; i < n; i = i + 1) rc = $fscanf(fd, "%h", a[i]);
                for (i = 0; i < n; i = i + 1) rc = $fscanf(fd, "%h", e[i]);
                if (only < 0 || only == ncase) begin
                    // load: line l = coefficients 4l .. 4l + 3
                    for (k = 0; k < n / 4; k = k + 1) begin
                        @(negedge clk);
                        load_valid = 1'b1; load_line = k;
                        load_data = {a[4*k+3], a[4*k+2], a[4*k+1], a[4*k]};
                    end
                    @(negedge clk); load_valid = 1'b0;
                    first_rd = -1; last_wr = -1; not_ready = 0;
                    start = 1'b1; start_inverse = (op == 6); start_profile = prof; start_logn = logn;
                    @(negedge clk); start = 1'b0;
                    w = 0;
                    while (!done && w < 100000) begin @(negedge clk); w = w + 1; end
                    // read back
                    for (k = 0; k < n / 4; k = k + 1) begin
                        read_valid = 1'b1; read_line = k;
                        @(negedge clk); read_valid = 1'b0;
                        while (!read_rsp_valid) @(negedge clk);
                        {got[4*k+3], got[4*k+2], got[4*k+1], got[4*k]} = read_data;
                    end
                    err = (w >= 100000) || error || (not_ready != 0);
                    for (i = 0; i < n; i = i + 1)
                        if (got[i] !== e[i]) begin
                            if (err < 4) $display("  MISMATCH profile %0d logn %0d op %0d coeff %0d: got %h want %h",
                                                  prof, logn, op, i, got[i], e[i]);
                            err = err + 1;
                        end
                    $display("CASE %0d profile=%0d logn=%0d op=%0d err=%0d cycles_a=%0d cycles_b=%0d not_ready=%0d",
                             ncase, prof, logn, op, err, last_wr - first_rd + 1, cycles, not_ready);
                    total_err = total_err + err;
                end
                ncase = ncase + 1;
            end
        end
        $display("TOTAL cases=%0d err=%0d %0s", ncase, total_err, total_err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
