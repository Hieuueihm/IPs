`timescale 1ns/1ps

module tb_cipher_block;
    reg clk;
    reg rst_n;
    reg key_load;
    reg start128, start192, start256;
    reg [127:0] key128;
    reg [191:0] key192;
    reg [255:0] key256;
    reg [127:0] plain128, plain192, plain256;
    wire [127:0] cipher128, cipher192, cipher256;
    wire ready128, ready192, ready256;
    wire busy128, busy192, busy256;
    wire done128, done192, done256;
    integer errors;

    localparam [127:0] PLAINTEXT = 128'h00112233445566778899aabbccddeeff;
    localparam [127:0] CT128 = 128'h69c4e0d86a7b0430d8cdb78070b4c55a;
    localparam [127:0] CT192 = 128'hdda97ca4864cdfe06eaf70a0ec0d7191;
    localparam [127:0] CT256 = 128'h8ea2b7ca516745bfeafc49904b496089;
    localparam [127:0] ZERO_CT128 = 128'h66e94bd4ef8a2c3b884cfa59ca342b2e;

    cipher_block #(.KEY_BITS(128)) dut128 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key128),
        .key_ready(ready128), .start(start128), .data_in(plain128),
        .data_out(cipher128), .busy(busy128), .done(done128)
    );

    cipher_block #(.KEY_BITS(192)) dut192 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key192),
        .key_ready(ready192), .start(start192), .data_in(plain192),
        .data_out(cipher192), .busy(busy192), .done(done192)
    );

    cipher_block #(.KEY_BITS(256)) dut256 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load), .key_in(key256),
        .key_ready(ready256), .start(start256), .data_in(plain256),
        .data_out(cipher256), .busy(busy256), .done(done256)
    );

    always #5 clk = ~clk;

    // Protect against a hung or incorrect state machine.
    initial begin
        #10000;
        $display("FAIL: simulation timeout");
        $finish;
    end

    initial begin
        clk      = 1'b0;
        rst_n    = 1'b0;
        key_load = 1'b0;
        start128 = 1'b0;
        start192 = 1'b0;
        start256 = 1'b0;
        key128 = 128'h000102030405060708090a0b0c0d0e0f;
        key192 = 192'h000102030405060708090a0b0c0d0e0f1011121314151617;
        key256 = 256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f;
        plain128 = PLAINTEXT;
        plain192 = PLAINTEXT;
        plain256 = PLAINTEXT;
        errors   = 0;

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;

        wait(ready128 && ready192 && ready256);
        @(negedge clk);
        if (busy128 || busy192 || busy256) begin
            $display("FAIL: key expansion should be idle");
            errors = errors + 1;
        end

        // AES-128 / AES-192 / AES-256 standard block-encryption vectors.
        start128 = 1'b1;
        start192 = 1'b1;
        start256 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        start192 = 1'b0;
        start256 = 1'b0;

        wait(done128);
        #1;
        if (cipher128 !== CT128) begin
            $display("FAIL AES-128: got %h, expected %h", cipher128, CT128);
            errors = errors + 1;
        end else $display("PASS AES-128");

        wait(done192);
        #1;
        if (cipher192 !== CT192) begin
            $display("FAIL AES-192: got %h, expected %h", cipher192, CT192);
            errors = errors + 1;
        end else $display("PASS AES-192");

        wait(done256);
        #1;
        if (cipher256 !== CT256) begin
            $display("FAIL AES-256: got %h, expected %h", cipher256, CT256);
            errors = errors + 1;
        end else $display("PASS AES-256");

        // Reusing the current round keys must work without another key_load.
        @(negedge clk);
        plain128 = PLAINTEXT;
        start128 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        wait(done128);
        #1;
        if (cipher128 !== CT128) begin
            $display("FAIL AES-128 reused key: got %h", cipher128);
            errors = errors + 1;
        end else $display("PASS AES-128 reused key");

        // Re-key AES-128 to all zeros and encrypt a zero block.
        // The other two instances also reload on key_load, so their key
        // inputs remain set; this is harmless for the AES-128 check.
        @(negedge clk);
        key128 = 128'b0;
        plain128 = 128'b0;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;
        if (ready128 || !busy128) begin
            $display("FAIL: key reload was not accepted");
            errors = errors + 1;
        end
        wait(ready128);
        @(negedge clk);
        start128 = 1'b1;
        @(negedge clk);
        start128 = 1'b0;
        wait(done128);
        #1;
        if (cipher128 !== ZERO_CT128) begin
            $display("FAIL AES-128 zero vector: got %h, expected %h", cipher128, ZERO_CT128);
            errors = errors + 1;
        end else $display("PASS AES-128 zero vector");

        if (errors == 0)
            $display("PASS: all aes_cipher_block tests");
        else
            $display("FAIL: %0d aes_cipher_block errors", errors);
        $finish;
    end
endmodule
