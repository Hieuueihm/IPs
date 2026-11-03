`timescale 1ns/1ps

module tb_aes_inv_shift_rows;
    logic [127:0] state_in;
    logic [127:0] state_out;
    logic [127:0] shifted_back;

    inv_shift_rows dut (
        .state_in  (state_in),
        .state_out (state_out)
    );

    // Round-trip check using the previously implemented ShiftRows module.
    shift_rows u_shift (
        .state_in  (state_out),
        .state_out (shifted_back)
    );

    task automatic check(
        input logic [127:0] in_value,
        input logic [127:0] expected_value,
        input string test_name
    );
        state_in = in_value;
        #1;
        if (state_out !== expected_value) begin
            $display("[FAIL] %s", test_name);
            $display("  Input    : %032h", state_in);
            $display("  Expected : %032h", expected_value);
            $display("  Actual   : %032h", state_out);
            $fatal(1, "InvShiftRows mismatch");
        end
        if (shifted_back !== state_in) begin
            $display("[FAIL] Round trip: %s", test_name);
            $display("  Original : %032h", state_in);
            $display("  Actual   : %032h", shifted_back);
            $fatal(1, "ShiftRows(InvShiftRows(x)) mismatch");
        end
        $display("[PASS] %s : %032h", test_name, state_out);
    endtask

    initial begin
        // AES-128 FIPS 197 example: after ShiftRows -> after SubBytes.
        check(128'h6353e08c0960e104cd70b751bacad0e7,
              128'h63cab7040953d051cd60e0e7ba70e18c,
              "FIPS-197 vector");

        // Distinct bytes expose any byte-index wiring mistakes.
        check(128'h000102030405060708090a0b0c0d0e0f,
              128'h000d0a0704010e0b0805020f0c090603,
              "Sequential bytes");

        check(128'h00000000000000000000000000000000,
              128'h00000000000000000000000000000000,
              "All zeros");

        $display("All InvShiftRows tests passed.");
        $finish;
    end
endmodule
