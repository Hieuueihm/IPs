`timescale 1ns/1ps
module tb_inv_cipher_block;
    reg clk, rst_n, key_load;
    reg start128, start192, start256;
    reg [127:0] key128;
    reg [191:0] key192;
    reg [255:0] key256;
    reg [127:0] cipher128, cipher192, cipher256;
    wire [127:0] plain128, plain192, plain256;
    wire ready128, ready192, ready256;
    wire busy128, busy192, busy256;
    wire done128, done192, done256;
    integer errors;

    localparam [127:0] PT    = 128'h00112233445566778899aabbccddeeff;
    localparam [127:0] CT128 = 128'h69c4e0d86a7b0430d8cdb78070b4c55a;
    localparam [127:0] CT192 = 128'hdda97ca4864cdfe06eaf70a0ec0d7191;
    localparam [127:0] CT256 = 128'h8ea2b7ca516745bfeafc49904b496089;
    localparam [127:0] ZERO_CT128 = 128'h66e94bd4ef8a2c3b884cfa59ca342b2e;

    inv_cipher_block #(.KEY_BITS(128)) dut128 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key128),
        .key_ready(ready128), .start(start128), .data_in(cipher128),
        .data_out(plain128), .busy(busy128), .done(done128)
    );
    inv_cipher_block #(.KEY_BITS(192)) dut192 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key192),
        .key_ready(ready192), .start(start192), .data_in(cipher192),
        .data_out(plain192), .busy(busy192), .done(done192)
    );
    inv_cipher_block #(.KEY_BITS(256)) dut256 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key256),
        .key_ready(ready256), .start(start256), .data_in(cipher256),
        .data_out(plain256), .busy(busy256), .done(done256)
    );

    always #5 clk = ~clk;

    initial begin
        #10000;
        $display("FAIL: aes_inv_cipher_block timeout");
        $finish;
    end

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        key_load = 1'b0;
        start128 = 1'b0;
        start192 = 1'b0;
        start256 = 1'b0;
        key128 = 128'h000102030405060708090a0b0c0d0e0f;
        key192 = 192'h000102030405060708090a0b0c0d0e0f1011121314151617;
        key256 = 256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f;
        cipher128 = CT128;
        cipher192 = CT192;
        cipher256 = CT256;
        errors = 0;

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;

        wait(ready128 && ready192 && ready256);
        @(negedge clk);
        if (busy128 || busy192 || busy256) begin
            $display("FAIL: key schedule remains busy");
            errors = errors + 1;
        end

        start128 = 1'b1;
        start192 = 1'b1;
        start256 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        start192 = 1'b0;
        start256 = 1'b0;

        wait(done128);
        #1;
        if (plain128 !== PT) begin
            $display("FAIL AES-128: got %h, expected %h", plain128, PT);
            errors = errors + 1;
        end else $display("PASS AES-128 decryption");

        wait(done192);
        #1;
        if (plain192 !== PT) begin
            $display("FAIL AES-192: got %h, expected %h", plain192, PT);
            errors = errors + 1;
        end else $display("PASS AES-192 decryption");

        wait(done256);
        #1;
        if (plain256 !== PT) begin
            $display("FAIL AES-256: got %h, expected %h", plain256, PT);
            errors = errors + 1;
        end else $display("PASS AES-256 decryption");

        // Reuse the existing key without another key_load.
        @(negedge clk);
        cipher128 = CT128;
        start128 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        wait(done128);
        #1;
        if (plain128 !== PT) begin
            $display("FAIL AES-128 reused key: got %h", plain128);
            errors = errors + 1;
        end else $display("PASS AES-128 reused key");

        // Key re-load: all-zero AES-128 key decrypts the known zero ciphertext.
        @(negedge clk);
        key128 = 128'b0;
        cipher128 = ZERO_CT128;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;
        if (ready128 || !busy128) begin
            $display("FAIL: AES-128 key reload not accepted");
            errors = errors + 1;
        end
        wait(ready128);
        @(negedge clk);
        start128 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        wait(done128);
        #1;
        if (plain128 !== 128'b0) begin
            $display("FAIL AES-128 all zero: got %h", plain128);
            errors = errors + 1;
        end else $display("PASS AES-128 all-zero vector");

        if (errors == 0) $display("PASS: all aes_inv_cipher_block tests");
        else $display("FAIL: %0d aes_inv_cipher_block test errors", errors);
        $finish;
    end
endmodule
