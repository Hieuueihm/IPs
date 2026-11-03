`timescale 1ns/1ps

module tb_mix_columns;
    logic [127:0] state_in;
    logic [127:0] state_out;
    integer test_count = 0;

    mix_columns dut (
        .state_in  (state_in),
        .state_out (state_out)
    );

    task automatic check(
        input logic [127:0] input_state,
        input logic [127:0] expected,
        input string name
    );
        state_in = input_state;
        #1;
        if (state_out !== expected) begin
            $display("[FAIL] %s", name);
            $display("  input    = %032h", input_state);
            $display("  expected = %032h", expected);
            $display("  actual   = %032h", state_out);
            $fatal(1, "MixColumns mismatch");
        end
        test_count++;
        $display("[PASS] %s", name);
    endtask

    initial begin
        // AES standard round example: ShiftRows output -> MixColumns output.
        check(128'h6353e08c0960e104cd70b751bacad0e7,
              128'h5f72641557f5bc92f7be3b291db9f91a,
              "AES round vector");

        // Standalone MixColumns example: {db,13,53,45} -> {8e,4d,a1,bc}.
        check(128'hdb135345000000000000000000000000,
              128'h8e4da1bc000000000000000000000000,
              "Single column vector");

        // Another example: {d4,bf,5d,30} -> {04,66,81,e5}.
        check(128'hd4bf5d30000000000000000000000000,
              128'h046681e5000000000000000000000000,
              "Second column vector");

        check(128'h00000000000000000000000000000000,
              128'h00000000000000000000000000000000,
              "Zero state");

        $display("All %0d MixColumns tests passed.", test_count);
        $finish;
    end
endmodule
