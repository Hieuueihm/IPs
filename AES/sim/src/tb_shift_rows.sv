`timescale 1ns/1ps

module tb_shift_rows;
    logic [127:0] state_in;
    logic [127:0] state_out;
    logic [127:0] expected;

    shift_rows dut (
        .state_in  (state_in),
        .state_out (state_out)
    );

    task automatic check(
        input logic [127:0] in_value,
        input logic [127:0] expected_value,
        input string test_name
    );
        state_in = in_value;
        expected = expected_value;
        #1;
        if (state_out !== expected) begin
            $display("[FAIL] %s", test_name);
            $display("  Input    : %032h", state_in);
            $display("  Expected : %032h", expected);
            $display("  Actual   : %032h", state_out);
            $fatal(1, "ShiftRows mismatch");
        end
        $display("[PASS] %s : %032h", test_name, state_out);
    endtask

    initial begin
        // FIPS 197 AES-128 example: state after SubBytes -> after ShiftRows.
        check(128'h63cab7040953d051cd60e0e7ba70e18c,
              128'h6353e08c0960e104cd70b751bacad0e7,
              "FIPS-197 vector");

        // Unique bytes to make the 16 positions easy to inspect.
        check(128'h000102030405060708090a0b0c0d0e0f,
              128'h00050a0f04090e03080d02070c01060b,
              "Sequential bytes");

        check(128'h00000000000000000000000000000000,
              128'h00000000000000000000000000000000,
              "All zeros");

        $display("All ShiftRows tests passed.");
        $finish;
    end
endmodule
