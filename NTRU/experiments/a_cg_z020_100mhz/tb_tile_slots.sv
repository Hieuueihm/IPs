`timescale 1ns/1ps
// Tile alone, NTT mode, both modulus slots in use (the core always uses slot 0): requests alternate slots at random,
// CT then GS (halving on), every result checked against plain Montgomery arithmetic (R = 2^32), in order.
module tb_tile_slots;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cfg_we = 0, cfg_slot = 0, cfg_halve = 0;
    reg [31:0] cfg_q = 0, cfg_qinv = 0;
    reg req_valid = 0, req_dir = 0, req_slot = 0;
    reg [63:0] req_data = 0;
    reg [31:0] req_root = 0;
    reg [7:0]  req_tag = 0;
    wire req_ready, rsp_valid, idle;
    wire [63:0] rsp_data;
    wire [7:0]  rsp_tag;
    tile_a2 #(.TREN_MANG(1), .IN_REG(0), .EN_REG(0), .PHASE(0)) dut (
        .clk(clk), .rst(rst), .en(1'b1), .idle(idle), .cfg_we(cfg_we), .cfg_slot(cfg_slot),
        .cfg_ntrugen(1'b0), .cfg_fmt(2'd0), .cfg_shift(4'd0),
        .ext_fft_valid(1'b0), .ext_fft_mpr(2'd0), .ext_fft_mst(4'd0),
        .cfg_q(cfg_q), .cfg_qinv(cfg_qinv), .cfg_floor(1'b0), .cfg_halve(cfg_halve),
        .req_valid(req_valid), .req_ready(req_ready), .req_mode(2'd0), .req_dir(req_dir), .req_slot(req_slot),
        .req_sign(1'b0), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));

    localparam integer N = 300;
    reg [31:0] qs [0:1];
    reg [63:0] want [0:N-1];
    integer sent, got, errors, dirn, seed;

    function [31:0] neg_inv(input [31:0] q);           // -q^-1 mod 2^32 (Newton)
        reg [31:0] v; integer i;
        begin v = q; for (i = 0; i < 5; i = i + 1) v = v * (32'd2 - q * v); neg_inv = -v; end
    endfunction
    function [31:0] mont(input [31:0] a, b, q);          // a * b * 2^-32 mod q
        reg [63:0] t; reg [31:0] m; reg [64:0] u;
        begin
            t = a * b; m = t[31:0] * neg_inv(q);
            u = ({1'b0, t} + {1'b0, m * {32'd0, q}}) >> 32;
            mont = (u >= q) ? u - q : u;
        end
    endfunction
    function [31:0] half(input [31:0] s, q);
        half = s[0] ? (s + q) >> 1 : s >> 1;
    endfunction
    function [63:0] model(input dir, input [31:0] x, y, w, q);
        reg [31:0] t, s, d;
        begin
            if (!dir) begin
                t = mont(y, w, q);
                model = {(x >= t) ? x - t : x + q - t, (x + t >= q) ? x + t - q : x + t};
            end else begin
                s = (x + y >= q) ? x + y - q : x + y;
                d = (x >= y) ? x - y : x + q - y;
                model = {mont(d, w, q), half(s, q)};
            end
        end
    endfunction

    task configure(input dir);
        begin
            rst = 1; repeat (3) @(posedge clk); #1 rst = 0; req_dir = dir; cfg_halve = dir;
            cfg_we = 1; cfg_slot = 0; cfg_q = qs[0]; cfg_qinv = neg_inv(qs[0]); @(posedge clk); #1;
            cfg_slot = 1; cfg_q = qs[1]; cfg_qinv = neg_inv(qs[1]); @(posedge clk); #1;
            cfg_we = 0; cfg_slot = 0;
        end
    endtask
    task next_request;
        reg [31:0] x, y, w, q;
        begin
            req_slot = $random(seed); q = qs[req_slot];
            x = $unsigned($random(seed)) % q; y = $unsigned($random(seed)) % q; w = $unsigned($random(seed)) % q;
            req_data = {y, x}; req_root = w; req_tag = sent[7:0];
            want[sent] = model(req_dir, x, y, w, q);
        end
    endtask

    always @(posedge clk) if (!rst && rsp_valid) begin
        if (rsp_data !== want[got] || rsp_tag !== got[7:0]) begin
            errors = errors + 1;
            if (errors < 5) $display("MISMATCH dir=%0d n=%0d got %h tag %0d want %h", req_dir, got, rsp_data, rsp_tag, want[got]);
        end
        got = got + 1;
    end

    initial begin
        seed = 7; errors = 0; qs[0] = 32'd12289; qs[1] = 32'd3329;
        for (dirn = 0; dirn < 2; dirn = dirn + 1) begin
            configure(dirn[0]);
            sent = 0; got = 0;
            next_request(); req_valid = 1;
            while (sent < N) begin
                @(negedge clk);                          // ready is stable here; the request fires at the next edge
                if (req_ready) begin
                    @(posedge clk); #1 sent = sent + 1;
                    if (sent < N) next_request(); else req_valid = 0;
                end
            end
            req_valid = 0;
            repeat (60) @(posedge clk);
            if (got != N) begin $display("dir=%0d results %0d of %0d", dirn, got, N); errors = errors + 1; end
        end
        if (errors == 0) $display("TILE_SLOTS cases=%0d dirs=2 slots=2 PASS", N);
        else $display("TILE_SLOTS FAIL errors=%0d", errors);
        $finish;
    end
endmodule
