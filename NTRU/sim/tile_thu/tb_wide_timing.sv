// Output timing of the tile FFT mode (req_mode 1) at 32 / 64 / 128 bit (+W=1 / 2 / 4): butterflies of 2L consecutive beats, one every P cycles; prints the cycle
// of every result relative to the first beat of its butterfly (for the core schedule, model/fft_wide_sched.py).
// +DIR=1 inverse, +SC=1 scaled. Run: iverilog -g2012 -o b.vvp hdl/mul_ss.v hdl/tile/tile_thu.sv sim/tile_thu/tb_wide_timing.sv; vvp b.vvp +W=4 +P=48
`timescale 1ns/1ps
module tb_wide_timing;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg         rst = 1'b1, cfg_we = 1'b0, req_valid = 1'b0;
    reg  [31:0] cfg_q = 0;
    wire        idle, req_ready, rsp_valid;
    wire [63:0] rsp_data;
    wire [7:0]  rsp_tag;
    reg  [7:0]  tag = 0;
    integer dir = 0, sc = 0;
    tile_thu #(.TREN_MANG(1)) dut (.clk(clk), .rst(rst), .en(1'b1), .idle(idle), .cfg_we(cfg_we), .cfg_slot(1'b0),
        .cfg_q(cfg_q), .cfg_qinv(32'd0), .cfg_floor(1'b0), .cfg_halve(1'b0), .req_valid(req_valid), .req_ready(req_ready),
        .req_mode(2'd1), .req_dir(dir[0]), .req_slot(1'b0), .req_sign(sc[0]), .req_data({$random, $random}),
        .req_root($random), .req_tag(tag), .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));
    integer L, P, cyc = 0, b, k, nb = 12, start [0:255], nrdy = 0;
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk)
        if (rsp_valid) $display("OUT bf %0d beat %0d at +%0d", rsp_tag / (2 * L), rsp_tag % (2 * L), cyc - start[rsp_tag / (2 * L)]);
    initial begin
        if (!$value$plusargs("W=%d", L)) L = 4;
        if (!$value$plusargs("P=%d", P)) P = 48;
        if (!$value$plusargs("DIR=%d", dir)) dir = 0;
        if (!$value$plusargs("SC=%d", sc)) sc = 0;
        repeat (3) @(negedge clk);
        rst = 1'b0;
        @(negedge clk); cfg_we = 1'b1; cfg_q = (L == 1) ? 32'h05 : (L == 2) ? 32'h15 : 32'h25;     // s = 5
        @(negedge clk); cfg_we = 1'b0;
        for (b = 0; b < nb; b = b + 1) begin
            start[b] = cyc;
            for (k = 0; k < 2 * L; k = k + 1) begin
                req_valid = 1'b1; tag = 2 * L * b + k;
                #1; if (!req_ready) nrdy = nrdy + 1;
                @(negedge clk);
            end
            req_valid = 1'b0;
            repeat (P - 2 * L) @(negedge clk);
        end
        repeat (200) @(negedge clk);
        $display("not ready %0d", nrdy);
        $finish;
    end
endmodule
