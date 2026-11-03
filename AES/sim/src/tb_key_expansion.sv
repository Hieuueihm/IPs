`timescale 1ns/1ps

module tb_key_expansion;
    reg clk;
    reg rst_n;
    reg key_load;
    reg [3:0] round_index;
    reg [127:0] key128;
    reg [191:0] key192;
    reg [255:0] key256;

    wire [127:0] rk128, rk192, rk256;
    wire busy128, busy192, busy256;
    wire ready128, ready192, ready256;
    integer errors;
    integer r;

    key_expansion #(.KEY_BITS(128)) dut128 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load),
        .key_in(key128), .round_index(round_index),
        .round_key(rk128), .busy(busy128), .key_ready(ready128)
    );
    key_expansion #(.KEY_BITS(192)) dut192 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load),
        .key_in(key192), .round_index(round_index),
        .round_key(rk192), .busy(busy192), .key_ready(ready192)
    );
    key_expansion #(.KEY_BITS(256)) dut256 (
        .clk(clk), .rst_n(rst_n), .key_load(key_load),
        .key_in(key256), .round_index(round_index),
        .round_key(rk256), .busy(busy256), .key_ready(ready256)
    );

    always #5 clk = ~clk;

    function [127:0] expected128;
        input integer idx;
        begin
            case (idx)
                0: expected128 = 128'h000102030405060708090a0b0c0d0e0f;
                1: expected128 = 128'hd6aa74fdd2af72fadaa678f1d6ab76fe;
                2: expected128 = 128'hb692cf0b643dbdf1be9bc5006830b3fe;
                3: expected128 = 128'hb6ff744ed2c2c9bf6c590cbf0469bf41;
                4: expected128 = 128'h47f7f7bc95353e03f96c32bcfd058dfd;
                5: expected128 = 128'h3caaa3e8a99f9deb50f3af57adf622aa;
                6: expected128 = 128'h5e390f7df7a69296a7553dc10aa31f6b;
                7: expected128 = 128'h14f9701ae35fe28c440adf4d4ea9c026;
                8: expected128 = 128'h47438735a41c65b9e016baf4aebf7ad2;
                9: expected128 = 128'h549932d1f08557681093ed9cbe2c974e;
                10: expected128 = 128'h13111d7fe3944a17f307a78b4d2b30c5;
                default: expected128 = 128'h0;
            endcase
        end
    endfunction

    function [127:0] expected192;
        input integer idx;
        begin
            case (idx)
                0: expected192 = 128'h000102030405060708090a0b0c0d0e0f;
                1: expected192 = 128'h10111213141516175846f2f95c43f4fe;
                2: expected192 = 128'h544afef55847f0fa4856e2e95c43f4fe;
                3: expected192 = 128'h40f949b31cbabd4d48f043b810b7b342;
                4: expected192 = 128'h58e151ab04a2a5557effb5416245080c;
                5: expected192 = 128'h2ab54bb43a02f8f662e3a95d66410c08;
                6: expected192 = 128'hf501857297448d7ebdf1c6ca87f33e3c;
                7: expected192 = 128'he510976183519b6934157c9ea351f1e0;
                8: expected192 = 128'h1ea0372a995309167c439e77ff12051e;
                9: expected192 = 128'hdd7e0e887e2fff68608fc842f9dcc154;
                10: expected192 = 128'h859f5f237a8d5a3dc0c02952beefd63a;
                11: expected192 = 128'hde601e7827bcdf2ca223800fd8aeda32;
                12: expected192 = 128'ha4970a331a78dc09c418c271e3a41d5d;
                default: expected192 = 128'h0;
            endcase
        end
    endfunction

    function [127:0] expected256;
        input integer idx;
        begin
            case (idx)
                0: expected256 = 128'h000102030405060708090a0b0c0d0e0f;
                1: expected256 = 128'h101112131415161718191a1b1c1d1e1f;
                2: expected256 = 128'ha573c29fa176c498a97fce93a572c09c;
                3: expected256 = 128'h1651a8cd0244beda1a5da4c10640bade;
                4: expected256 = 128'hae87dff00ff11b68a68ed5fb03fc1567;
                5: expected256 = 128'h6de1f1486fa54f9275f8eb5373b8518d;
                6: expected256 = 128'hc656827fc9a799176f294cec6cd5598b;
                7: expected256 = 128'h3de23a75524775e727bf9eb45407cf39;
                8: expected256 = 128'h0bdc905fc27b0948ad5245a4c1871c2f;
                9: expected256 = 128'h45f5a66017b2d387300d4d33640a820a;
                10: expected256 = 128'h7ccff71cbeb4fe5413e6bbf0d261a7df;
                11: expected256 = 128'hf01afafee7a82979d7a5644ab3afe640;
                12: expected256 = 128'h2541fe719bf500258813bbd55a721c0a;
                13: expected256 = 128'h4e5a6699a9f24fe07e572baacdf8cdea;
                14: expected256 = 128'h24fc79ccbf0979e9371ac23c6d68de36;
                default: expected256 = 128'h0;
            endcase
        end
    endfunction

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        key_load = 1'b0;
        round_index = 4'd0;
        key128 = 128'h000102030405060708090a0b0c0d0e0f;
        key192 = 192'h000102030405060708090a0b0c0d0e0f1011121314151617;
        key256 = 256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f;
        errors = 0;

        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;
        // AES-256 takes 52 clocks; wait 55 clocks to finish all variants.
        repeat (55) @(negedge clk);
        if (!ready128 || !ready192 || !ready256 || busy128 || busy192 || busy256) begin
            $display("FAIL: ready/busy after expansion");
            errors = errors + 1;
        end

        for (r = 0; r < 15; r = r + 1) begin
            round_index = r;
            #1;
            if ((r <= 10) && (rk128 !== expected128(r))) begin
                $display("FAIL AES-128 round=%0d expected=%h actual=%h", r, expected128(r), rk128);
                errors = errors + 1;
            end
            if ((r > 10) && (rk128 !== 128'b0)) begin
                $display("FAIL AES-128 invalid round=%0d", r);
                errors = errors + 1;
            end
            if ((r <= 12) && (rk192 !== expected192(r))) begin
                $display("FAIL AES-192 round=%0d expected=%h actual=%h", r, expected192(r), rk192);
                errors = errors + 1;
            end
            if ((r > 12) && (rk192 !== 128'b0)) begin
                $display("FAIL AES-192 invalid round=%0d", r);
                errors = errors + 1;
            end
            if (rk256 !== expected256(r)) begin
                $display("FAIL AES-256 round=%0d expected=%h actual=%h", r, expected256(r), rk256);
                errors = errors + 1;
            end
        end

        // Reload new keys and verify that the previous valid state is cleared.
        @(negedge clk);
        key128 = 128'b0;
        key192 = 192'b0;
        key256 = 256'b0;
        key_load = 1'b1;
        @(negedge clk);
        key_load = 1'b0;
        #1;
        if (ready128 || ready192 || ready256 || !busy128 || !busy192 || !busy256) begin
            $display("FAIL: reloading did not invalidate previous round keys");
            errors = errors + 1;
        end
        if (rk128 !== 128'b0 || rk192 !== 128'b0 || rk256 !== 128'b0) begin
            $display("FAIL: output must be zero until key_ready");
            errors = errors + 1;
        end
        repeat (55) @(negedge clk);
        round_index = 4'd0;
        #1;
        if (!ready128 || !ready192 || !ready256 ||
            rk128 !== 128'b0 || rk192 !== 128'b0 || rk256 !== 128'b0) begin
            $display("FAIL: reload all-zero key round 0");
            errors = errors + 1;
        end
        if (errors == 0)
            $display("PASS: AES-128/192/256 full key schedule and key reload");
        else
            $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
