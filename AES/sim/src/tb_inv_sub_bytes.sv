`timescale 1ns/1ps

module tb_inv_sub_bytes;
    logic [127:0] state_in;
    logic [127:0] state_out;
    logic [127:0] forward_out;
    int i;

    inv_sub_bytes dut (
        .state_in  (state_in),
        .state_out (state_out)
    );

    sub_bytes u_forward (
        .state_in  (state_out),
        .state_out (forward_out)
    );

    // Dump VCD for waveform viewing.
    initial begin
        $dumpfile("tb_inv_sub_bytes.vcd");
        $dumpvars(0, tb_inv_sub_bytes);
    end

    initial begin
        // FIPS 197 example: reverse the SubBytes output.
        state_in = 128'h63cab7040953d051cd60e0e7ba70e18c;
        #1;
        if (state_out !== 128'h00102030405060708090a0b0c0d0e0f0)
            $fatal(1, "Known vector failed: got %h", state_out);

        // INV_SBOX[0x63] = 0x00.
        state_in = 128'h63636363636363636363636363636363;
        #1;
        if (state_out !== 128'h00000000000000000000000000000000)
            $fatal(1, "0x63 test failed: got %h", state_out);

        // INV_SBOX[0x00] = 0x52.
        state_in = 128'h00000000000000000000000000000000;
        #1;
        if (state_out !== 128'h52525252525252525252525252525252)
            $fatal(1, "0x00 test failed: got %h", state_out);

        // Test every possible byte: SubBytes(InvSubBytes(x)) == x.
        for (i = 0; i < 256; i++) begin
            state_in = {16{8'(i)}};
            #1;
            if (forward_out !== state_in)
                $fatal(1, "Round-trip failed for byte %02h: got %h", i[7:0], forward_out);
        end

        $display("PASS: aes_inv_sub_bytes (3 vectors + 256 round-trips)");
        $finish;
    end
endmodule
