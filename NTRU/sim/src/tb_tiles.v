// tb_tiles: self-checking testbench for mul_ss, tile_l32 and tile_l16x4.
// Compares every configuration (CORR/EXT, split/fuse) with the exact product.
//
// Run (from NTRU/):
//   iverilog -g2012 -o sim/work/tb_tiles.vvp sim/src/tb_tiles.v hdl/mul_ss.v hdl/tile_l32.v hdl/tile_l16x4.v
//   vvp sim/work/tb_tiles.vvp
`timescale 1ns / 1ps

module tb_tiles;

    localparam integer N_RANDOM = 5000;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    // ---------------------------------------------------------------- DUTs
    reg  [31:0]  a32, b32;
    reg          sa32, sb32;
    wire [64:0]  p32c, p32e;

    tile_l32 #(.IMPL("CORR")) dut32c (.clk(clk), .a(a32), .b(b32),
        .a_signed(sa32), .b_signed(sb32), .p(p32c));
    tile_l32 #(.IMPL("EXT"))  dut32e (.clk(clk), .a(a32), .b(b32),
        .a_signed(sa32), .b_signed(sb32), .p(p32e));

    reg          fuse;
    reg  [63:0]  abus, bbus;
    reg  [3:0]   sa16, sb16;
    wire [131:0] p16c, p16e, p16s;

    tile_l16x4 #(.IMPL("CORR"), .FUSE_EN(1)) dut16c (.clk(clk), .fuse(fuse),
        .a_bus(abus), .b_bus(bbus), .a_signed(sa16), .b_signed(sb16), .p(p16c));
    tile_l16x4 #(.IMPL("EXT"),  .FUSE_EN(1)) dut16e (.clk(clk), .fuse(fuse),
        .a_bus(abus), .b_bus(bbus), .a_signed(sa16), .b_signed(sb16), .p(p16e));
    tile_l16x4 #(.IMPL("CORR"), .FUSE_EN(0)) dut16s (.clk(clk), .fuse(1'b0),
        .a_bus(abus), .b_bus(bbus), .a_signed(sa16), .b_signed(sb16), .p(p16s));

    // ----------------------------------------------------------- references
    function [64:0] ref32(input [31:0] a, input [31:0] b, input sa, input sb);
        reg signed [33:0] ax, bx;
        reg signed [67:0] full;
        begin
            ax    = sa ? {{2{a[31]}}, a} : {2'b00, a};
            bx    = sb ? {{2{b[31]}}, b} : {2'b00, b};
            full  = ax * bx;
            ref32 = full[64:0];
        end
    endfunction

    function [32:0] ref16(input [15:0] a, input [15:0] b, input sa, input sb);
        reg signed [17:0] ax, bx;
        reg signed [35:0] full;
        begin
            ax    = sa ? {{2{a[15]}}, a} : {2'b00, a};
            bx    = sb ? {{2{b[15]}}, b} : {2'b00, b};
            full  = ax * bx;
            ref16 = full[32:0];
        end
    endfunction

    // --------------------------------------------------------------- checks
    integer errors = 0;
    integer checks = 0;
    integer seed   = 20261021;

    task check(input [255:0] tag, input [131:0] got, input [131:0] exp);
        begin
            checks = checks + 1;
            if (got !== exp) begin
                errors = errors + 1;
                if (errors <= 10)
                    $display("FAIL %0s: got %h exp %h (a=%h b=%h sa=%b sb=%b)",
                             tag, got, exp, a32, b32, sa32, sb32);
            end
        end
    endtask

    // One 32-bit vector through tile_l32 (both IMPL) and fused tile_l16x4 (both IMPL).
    task run32(input [31:0] a, input [31:0] b, input sa, input sb);
        reg [64:0] e;
        begin
            a32 = a; b32 = b; sa32 = sa; sb32 = sb;
            fuse = 1'b1;
            abus = {$random(seed), a};            // upper half must be ignored
            bbus = {$random(seed), b};
            sa16 = {$random(seed), sa};           // only bit 0 is used in fuse mode
            sb16 = {$random(seed), sb};
            sa16[0] = sa; sb16[0] = sb;
            @(posedge clk); @(posedge clk); #1;
            e = ref32(a, b, sa, sb);
            check("l32 CORR", {67'b0, p32c}, {67'b0, e});
            check("l32 EXT ", {67'b0, p32e}, {67'b0, e});
            check("l16 CORR fuse", p16c, {67'b0, e});
            check("l16 EXT  fuse", p16e, {67'b0, e});
        end
    endtask

    // One split vector: four independent 16x16 lanes.
    task run16(input [63:0] a, input [63:0] b, input [3:0] sa, input [3:0] sb);
        reg [131:0] e;
        integer k;
        begin
            fuse = 1'b0; abus = a; bbus = b; sa16 = sa; sb16 = sb;
            @(posedge clk); @(posedge clk); #1;
            for (k = 0; k < 4; k = k + 1)
                e[33*k +: 33] = ref16(a[16*k +: 16], b[16*k +: 16], sa[k], sb[k]);
            check("l16 CORR split", p16c, e);
            check("l16 EXT  split", p16e, e);
            check("l16 split-only", p16s, e);
        end
    endtask

    reg [31:0] corner32 [0:8];
    reg [15:0] corner16 [0:6];
    integer i, j, m;
    reg [63:0] ra, rb;

    initial begin
        corner32[0] = 32'h0000_0000; corner32[1] = 32'h0000_0001;
        corner32[2] = 32'h7FFF_FFFF; corner32[3] = 32'h8000_0000;
        corner32[4] = 32'hFFFF_FFFF; corner32[5] = 32'h8000_0001;
        corner32[6] = 32'h0001_0000; corner32[7] = 32'h0000_FFFF;
        corner32[8] = 32'hFFFF_0000;
        corner16[0] = 16'h0000; corner16[1] = 16'h0001; corner16[2] = 16'h7FFF;
        corner16[3] = 16'h8000; corner16[4] = 16'hFFFF; corner16[5] = 16'h8001;
        corner16[6] = 16'h00FF;

        // 32-bit corners x all sign modes.
        for (i = 0; i < 9; i = i + 1)
            for (j = 0; j < 9; j = j + 1)
                for (m = 0; m < 4; m = m + 1)
                    run32(corner32[i], corner32[j], m[1], m[0]);

        // 16-bit corners in every lane position, all sign modes.
        for (i = 0; i < 7; i = i + 1)
            for (j = 0; j < 7; j = j + 1)
                for (m = 0; m < 4; m = m + 1)
                    run16({4{corner16[i]}}, {corner16[j], corner16[(j+1)%7],
                          corner16[(j+2)%7], corner16[(j+3)%7]},
                          {4{m[1]}}, {m[0], ~m[0], m[0], ~m[0]});

        // Random.
        for (i = 0; i < N_RANDOM; i = i + 1) begin
            run32($random(seed), $random(seed), $random(seed), $random(seed));
            ra = {$random(seed), $random(seed)};
            rb = {$random(seed), $random(seed)};
            run16(ra, rb, $random(seed), $random(seed));
        end

        if (errors == 0)
            $display("PASS: %0d checks, 0 errors", checks);
        else
            $display("FAIL: %0d checks, %0d errors", checks, errors);
        $finish;
    end

endmodule
