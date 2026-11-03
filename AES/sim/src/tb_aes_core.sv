`timescale 1ns/1ps
// Additional direct aes_core tests for AES-128/192/256 encryption + decryption.
// The AXI bus protocol and ECB/CBC/CTR chaining are tested in tb_aes_axi4lite.v.
module aes_core_key_case #(
    parameter KEY_BITS = 128,
    parameter [127:0] EXPECTED = 128'h69c4e0d86a7b0430d8cdb78070b4c55a
)(
    input wire clk,
    input wire rst_n,
    output reg passed,
    output reg failed
);
    localparam [255:0] KEY256 =
        256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f;
    localparam [127:0] PLAIN = 128'h00112233445566778899aabbccddeeff;
    reg key_load, iv_load, start, decrypt;
    reg [127:0] data_in;
    wire key_ready, busy, done;
    wire [127:0] data_out, iv_out;

    aes_core #(.KEY_BITS(KEY_BITS)) dut (
        .clk(clk), .rst_n(rst_n),
        .key_load(key_load), .key_in(KEY256[255 -: KEY_BITS]),
        .key_ready(key_ready), .iv_load(iv_load), .iv_in(128'b0), .iv_out(iv_out),
        .mode(2'b00), .decrypt(decrypt),
        .start(start), .data_in(data_in),
        .data_out(data_out), .busy(busy), .done(done)
    );

    initial begin
        passed = 0; failed = 0;
        key_load=0; iv_load=0; start=0; decrypt=0; data_in=PLAIN;
        wait(rst_n == 1);
        @(negedge clk); key_load=1;
        @(negedge clk); key_load=0;
        wait(key_ready == 1);
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        wait(done == 1);
        if (data_out !== EXPECTED) begin
            $display("FAIL AES-%0d ENC expected %032h got %032h",
                     KEY_BITS, EXPECTED, data_out);
            failed=1;
        end else begin
            $display("PASS AES-%0d ENC", KEY_BITS);
        end

        @(negedge clk);
        data_in=EXPECTED;
        decrypt=1;
        start=1;
        @(negedge clk); start=0;
        wait(done == 1);
        if (data_out !== PLAIN) begin
            $display("FAIL AES-%0d DEC expected %032h got %032h",
                     KEY_BITS, PLAIN, data_out);
            failed=1;
        end else begin
            $display("PASS AES-%0d DEC", KEY_BITS);
        end
        passed = !failed;
    end
endmodule

module tb_aes_core_all_keys;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    wire p128,f128,p192,f192,p256,f256;

    aes_core_key_case #(
        .KEY_BITS(128),
        .EXPECTED(128'h69c4e0d86a7b0430d8cdb78070b4c55a)
    ) case128(clk,rst_n,p128,f128);
    aes_core_key_case #(
        .KEY_BITS(192),
        .EXPECTED(128'hdda97ca4864cdfe06eaf70a0ec0d7191)
    ) case192(clk,rst_n,p192,f192);
    aes_core_key_case #(
        .KEY_BITS(256),
        .EXPECTED(128'h8ea2b7ca516745bfeafc49904b496089)
    ) case256(clk,rst_n,p256,f256);

    initial begin
        repeat(4) @(negedge clk);
        rst_n=1;
        wait((p128||f128)&&(p192||f192)&&(p256||f256));
        if (p128 && p192 && p256)
            $display("ALL AES KEY-SIZE TESTS PASSED");
        else
            $display("AES KEY-SIZE TEST FAILED");
        $finish;
    end
    initial begin
        #100000;
        $display("FATAL: key-size test timeout");
        $finish;
    end
endmodule
