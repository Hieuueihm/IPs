// ============================================================
//  tb_aes_wb_slave.v
//  Direct testbench — AES Wishbone Slave
//
//  Test cases (NIST SP800-38A + FIPS-197):
//    1. AES-128 ECB encrypt  — FIPS-197 Appendix B
//    2. AES-128 ECB decrypt
//    3. AES-128 CBC encrypt  — SP800-38A F.2.1
//    4. AES-128 CBC decrypt  — SP800-38A F.2.2
//    5. AES-128 CTR encrypt  — SP800-38A F.5.1
//    6. AES-256 ECB encrypt  — FIPS-197 Appendix B
//    7. AES-256 CBC encrypt  — SP800-38A F.2.5
//
//  Wishbone write helper: wb_write(addr, data)
//  Wishbone read  helper: wb_read(addr) → rd_data
//
//  Register map:
//    0x00 CTRL    [4]=KEY_LEN [3]=OP [2:1]=MODE [0]=START
//    0x04 STATUS  [3]=KEY_EXP [2]=INPUT_READY [1]=OUTPUT_VALID [0]=BUSY
//    0x08 CONFIG  [0]=AUTO_START
//    0x10-0x2C KEY_0..7
//    0x30-0x3C IV_0..3
//    0x40-0x4C DIN_0..3
//    0x50-0x5C DOUT_0..3
// ============================================================
`timescale 1ns/1ps

module tb_aes_wb_slave;

    // ── Clock & Reset ─────────────────────────────────────────
    reg clk, rst_n;
    always #5 clk = ~clk;  // 100 MHz

    // ── DUT ports ─────────────────────────────────────────────
    reg        wb_cyc, wb_stb, wb_we;
    reg  [7:0] wb_adr;
    reg [31:0] wb_dat_i;
    reg  [3:0] wb_sel;
    wire       wb_ack, wb_stall, wb_err;
    wire[31:0] wb_dat_o;
    wire       irq;

    aes_wb_slave dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .wb_cyc   (wb_cyc),
        .wb_stb   (wb_stb),
        .wb_we    (wb_we),
        .wb_adr   (wb_adr),
        .wb_dat_i (wb_dat_i),
        .wb_sel   (wb_sel),
        .wb_ack   (wb_ack),
        .wb_stall (wb_stall),
        .wb_dat_o (wb_dat_o),
        .wb_err   (wb_err),
        .irq      (irq)
    );

    // ── Global state ──────────────────────────────────────────
    integer fail_count;
    reg [31:0] rd_data;

    // ============================================================
    //  Task: wb_write — single Wishbone write, wait for ACK
    // ============================================================
    task wb_write;
        input [7:0]  addr;
        input [31:0] data;
        begin
            $display(" start write");

            @(posedge clk); #1;
            wb_cyc  = 1; wb_stb = 1; wb_we = 1;
            wb_adr  = addr;
            wb_dat_i = data;
            wb_sel  = 4'hF;
            // Wait for ACK (registered — 1 cycle after STB)
            $display(" data write %h ", data);
            @(posedge clk); #1;
            while (!wb_ack) @(posedge clk); #1;
            wb_cyc  = 0; wb_stb = 0; wb_we = 0;
        end
    endtask

    // ============================================================
    //  Task: wb_read — single Wishbone read, wait for ACK
    // ============================================================
    task wb_read;
        input [7:0] addr;
        begin
            @(posedge clk); #1;
            wb_cyc  = 1; wb_stb = 1; wb_we = 0;
            wb_adr  = addr;
            wb_sel  = 4'hF;
            @(posedge clk); #1;
            while (!wb_ack) @(posedge clk); #1;
            rd_data = wb_dat_o;
            wb_cyc  = 0; wb_stb = 0;
        end
    endtask

    // ============================================================
    //  Task: wait_output_valid — poll STATUS[1]
    // ============================================================
    task wait_output_valid;
        integer timeout;
        begin
            timeout = 0;
            rd_data = 0;
            while (!(rd_data & 32'h2) && timeout < 200) begin
                wb_read(8'h04);
                timeout = timeout + 1;
            end
            if (timeout >= 200)
                $display("ERROR: timeout waiting for OUTPUT_VALID");
        end
    endtask

    // ============================================================
    //  Task: load_key_128 — write 4 KEY registers
    // ============================================================
    task load_key_128;
        input [127:0] key;
        begin
            wb_write(8'h10, key[127:96]);
            wb_write(8'h14, key[95:64]);
            wb_write(8'h18, key[63:32]);
            wb_write(8'h1C, key[31:0]);   // → KEY_VALID auto-set
        end
    endtask

    // ============================================================
    //  Task: load_key_256
    // ============================================================
    task load_key_256;
        input [255:0] key;
        begin
            wb_write(8'h10, key[255:224]);
            wb_write(8'h14, key[223:192]);
            wb_write(8'h18, key[191:160]);
            wb_write(8'h1C, key[159:128]);
            wb_write(8'h20, key[127:96]);
            wb_write(8'h24, key[95:64]);
            wb_write(8'h28, key[63:32]);
            wb_write(8'h2C, key[31:0]);   // → KEY_VALID auto-set
        end
    endtask

    // ============================================================
    //  Task: load_iv
    // ============================================================
    task load_iv;
        input [127:0] iv;
        begin
            wb_write(8'h30, iv[127:96]);
            wb_write(8'h34, iv[95:64]);
            wb_write(8'h38, iv[63:32]);
            wb_write(8'h3C, iv[31:0]);    // → IV_VALID auto-set
        end
    endtask

    // ============================================================
    //  Task: encrypt_block — write DIN, wait, read DOUT
    //  AUTO_START must be enabled before calling this
    // ============================================================
    task encrypt_block;
        input  [127:0] din;
        output [127:0] dout;
        begin
            wb_write(8'h40, din[127:96]);
            wb_write(8'h44, din[95:64]);
            wb_write(8'h48, din[63:32]);
            wb_write(8'h4C, din[31:0]);   // → AUTO_START fires

            wait_output_valid;

            wb_read(8'h50); dout[127:96] = rd_data;
            wb_read(8'h54); dout[95:64]  = rd_data;
            wb_read(8'h58); dout[63:32]  = rd_data;
            wb_read(8'h5C); dout[31:0]   = rd_data; // → OUTPUT_VALID clear
        end
    endtask

    // ============================================================
    //  Task: check_result
    // ============================================================
    task check_result;
        input [127:0] got;
        input [127:0] expected;
        input [127:0] test_name; // packed string
        begin
            if (got === expected) begin
                $display("PASS %s", test_name);
                $display("     %h", got);
            end else begin
                $display("FAIL %s", test_name);
                $display("     got      %h", got);
                $display("     expected %h", expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    // ============================================================
    //  Task: full_reset — reset DUT và bus
    // ============================================================
    task full_reset;
        begin
            rst_n = 0;
            wb_cyc = 0; wb_stb = 0; wb_we = 0;
            wb_adr = 0; wb_dat_i = 0; wb_sel = 4'hF;
            repeat(4) @(posedge clk);
            #1; rst_n = 1;
            repeat(2) @(posedge clk);
            $display("reset done! ");
        end
    endtask

    // ============================================================
    //  NIST Test Vectors
    // ============================================================

    // FIPS-197 Appendix B — AES-128
    localparam KEY128   = 128'h2b7e151628aed2a6abf7158809cf4f3c;
    localparam PLAIN128 = 128'h3243F6A8885A308D313198A2E0370734;
    localparam CIPH128  = 128'h3925841d02dc09fbdc118597196a0b32;

    // FIPS-197 Appendix B — AES-256
    localparam KEY256   = 256'h603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4;
    localparam PLAIN256 = 128'h6bc1bee22e409f96e93d7e117393172a;
    localparam CIPH256  = 128'hf3eed1bdb5d2a03c064b5a7e3db181f8;

    // SP800-38A F.2.1 — AES-128 CBC
    localparam CBC_IV   = 128'h000102030405060708090a0b0c0d0e0f;
    localparam CBC_P1   = 128'h6bc1bee22e409f96e93d7e117393172a;
    localparam CBC_P2   = 128'hae2d8a571e03ac9c9eb76fac45af8e51;
    localparam CBC_P3   = 128'h30c81c46a35ce411e5fbc1191a0a52ef;
    localparam CBC_P4   = 128'hf69f2445df4f9b17ad2b417be66c3710;
    localparam CBC_C1   = 128'h7649abac8119b246cee98e9b12e9197d;
    localparam CBC_C2   = 128'h5086cb9b507219ee95db113a917678b2;
    localparam CBC_C3   = 128'h73bed6b8e3c1743b7116e69e22229516;
    localparam CBC_C4   = 128'h3ff1caa1681fac09120eca307586e1a7;

    // SP800-38A F.5.1 — AES-128 CTR
    localparam CTR_IV   = 128'hf0f1f2f3f4f5f6f7f8f9fafbfcfdfeff;
    localparam CTR_P1   = 128'h6bc1bee22e409f96e93d7e117393172a;
    localparam CTR_P2   = 128'hae2d8a571e03ac9c9eb76fac45af8e51;
    localparam CTR_C1   = 128'h874d6191b620e3261bef6864990db6ce;
    localparam CTR_C2   = 128'h9806f66b7970fdff8617187bb9fffdff;

    // ============================================================
    //  Main test
    // ============================================================
    reg [127:0] dout;
    integer i;

    initial begin
        $dumpfile("tb_aes_wb_slave.vcd");
        $dumpvars(0, tb_aes_wb_slave);

        clk = 0; fail_count = 0;
        full_reset;

        // ════════════════════════════════════════════════════════
        //  TEST 1: AES-128 ECB Encrypt — FIPS-197 Appendix B
        // ════════════════════════════════════════════════════════
        $display("\n=== TEST 1: AES-128 ECB Encrypt ===");
        full_reset;

        // CTRL: ECB=00, enc=0, AES-128=0
        wb_write(8'h00, 32'h00);
        // CONFIG: AUTO_START=1
        wb_write(8'h08, 32'h01);
        // Load key
        load_key_128(KEY128);
        // Encrypt
        encrypt_block(PLAIN128, dout);
        check_result(dout, CIPH128, "AES-128 ECB enc");

        // ════════════════════════════════════════════════════════
        //  TEST 2: AES-128 ECB Decrypt
        // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 2: AES-128 ECB Decrypt ===");
        // full_reset;

        // // CTRL: ECB, decrypt=1, AES-128
        // wb_write(8'h00, 32'h08);  // OP=1
        // wb_write(8'h08, 32'h01);
        // load_key_128(KEY128);
        // encrypt_block(CIPH128, dout);
        // check_result(dout, PLAIN128, "AES-128 ECB dec");

        // // ════════════════════════════════════════════════════════
        // //  TEST 3: AES-128 CBC Encrypt — SP800-38A F.2.1
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 3: AES-128 CBC Encrypt (4 blocks) ===");
        // full_reset;

        // // CTRL: CBC=01, enc=0, AES-128=0
        // wb_write(8'h00, 32'h02);  // MODE=01
        // wb_write(8'h08, 32'h03);  // AUTO_START=1, AUTO_IV_UPDATE=1
        // load_key_128(KEY128);
        // load_iv(CBC_IV);

        // encrypt_block(CBC_P1, dout); check_result(dout, CBC_C1, "CBC enc block 1");
        // encrypt_block(CBC_P2, dout); check_result(dout, CBC_C2, "CBC enc block 2");
        // encrypt_block(CBC_P3, dout); check_result(dout, CBC_C3, "CBC enc block 3");
        // encrypt_block(CBC_P4, dout); check_result(dout, CBC_C4, "CBC enc block 4");

        // // ════════════════════════════════════════════════════════
        // //  TEST 4: AES-128 CBC Decrypt — SP800-38A F.2.2
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 4: AES-128 CBC Decrypt (4 blocks) ===");
        // full_reset;

        // // CTRL: CBC, decrypt=1, AES-128
        // wb_write(8'h00, 32'h0A);  // MODE=01, OP=1
        // wb_write(8'h08, 32'h03);
        // load_key_128(KEY128);
        // load_iv(CBC_IV);

        // encrypt_block(CBC_C1, dout); check_result(dout, CBC_P1, "CBC dec block 1");
        // encrypt_block(CBC_C2, dout); check_result(dout, CBC_P2, "CBC dec block 2");
        // encrypt_block(CBC_C3, dout); check_result(dout, CBC_P3, "CBC dec block 3");
        // encrypt_block(CBC_C4, dout); check_result(dout, CBC_P4, "CBC dec block 4");

        // // ════════════════════════════════════════════════════════
        // //  TEST 5: AES-128 CTR — SP800-38A F.5.1
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 5: AES-128 CTR Encrypt ===");
        // full_reset;

        // // CTRL: CTR=10, enc=0, AES-128
        // wb_write(8'h00, 32'h04);  // MODE=10
        // wb_write(8'h08, 32'h03);  // AUTO_START + AUTO_IV_UPDATE
        // load_key_128(KEY128);
        // load_iv(CTR_IV);

        // encrypt_block(CTR_P1, dout); check_result(dout, CTR_C1, "CTR enc block 1");
        // encrypt_block(CTR_P2, dout); check_result(dout, CTR_C2, "CTR enc block 2");

        // // ════════════════════════════════════════════════════════
        // //  TEST 6: AES-256 ECB Encrypt — FIPS-197 Appendix B
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 6: AES-256 ECB Encrypt ===");
        // full_reset;

        // // CTRL: ECB, enc, AES-256
        // wb_write(8'h00, 32'h10);  // KEY_LEN=1
        // wb_write(8'h08, 32'h01);
        // load_key_256(KEY256);
        // encrypt_block(PLAIN256, dout);
        // check_result(dout, CIPH256, "AES-256 ECB enc");

        // // ════════════════════════════════════════════════════════
        // //  TEST 7: STATUS register check
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 7: STATUS register ===");
        // full_reset;

        // wb_write(8'h00, 32'h00);
        // wb_write(8'h08, 32'h00);  // AUTO_START=0

        // // Trước khi load key: STATUS[3] (KEY_EXPANDED) = 0
        // wb_read(8'h04);
        // if (rd_data[3] == 0)
        //     $display("PASS STATUS: KEY_EXPANDED=0 before key load");
        // else begin
        //     $display("FAIL STATUS: KEY_EXPANDED should be 0");
        //     fail_count = fail_count + 1;
        // end

        // // Load key
        // load_key_128(KEY128);
        // repeat(5) @(posedge clk);

        // // Sau khi load: STATUS[3] = 1, STATUS[2] = INPUT_READY = 1
        // wb_read(8'h04);
        // if (rd_data[3] == 1 && rd_data[2] == 1)
        //     $display("PASS STATUS: KEY_EXPANDED=1, INPUT_READY=1");
        // else begin
        //     $display("FAIL STATUS: got %h", rd_data);
        //     fail_count = fail_count + 1;
        // end

        // // ════════════════════════════════════════════════════════
        // //  TEST 8: WB error on invalid address
        // // ════════════════════════════════════════════════════════
        // $display("\n=== TEST 8: Invalid address ===");
        // @(posedge clk); #1;
        // wb_cyc = 1; wb_stb = 1; wb_we = 1;
        // wb_adr = 8'h60; wb_dat_i = 32'hDEAD; wb_sel = 4'hF;
        // @(posedge clk); #1;
        // if (wb_err == 1)
        //     $display("PASS wb_err=1 for invalid addr 0x60");
        // else begin
        //     $display("FAIL wb_err should be 1 for invalid addr");
        //     fail_count = fail_count + 1;
        // end
        // wb_cyc = 0; wb_stb = 0;

        // ════════════════════════════════════════════════════════
        //  Summary
        // ════════════════════════════════════════════════════════
        $display("\n========================================");
        if (fail_count == 0)
            $display("  ALL TESTS PASSED");
        else
            $display("  %0d TEST(S) FAILED", fail_count);
        $display("========================================");

        $finish;
    end

    // Timeout watchdog
    initial begin
        #100000;
        $display("ERROR: Simulation timeout");
        $finish;
    end

endmodule