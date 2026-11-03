`timescale 1ns / 1ps

module tb_sub_bytes;
  logic [127:0] state_in;
  logic [127:0] state_out;

  sub_bytes dut (
      .state_in (state_in),
      .state_out(state_out)
  );

  initial begin
    $dumpfile("tb_sub_bytes.vcd");
    $dumpvars(0, tb_sub_bytes);
  end

  initial begin
    // Known AES SubBytes vector (FIPS 197 round example).
    state_in = 128'h00102030405060708090a0b0c0d0e0f0;
    #1;
    if (state_out !== 128'h63cab7040953d051cd60e0e7ba70e18c)
      $fatal(1, "Test 1 failed: got %h", state_out);

    // SBOX[0x00] = 0x63 for every byte.
    state_in = 128'h00000000000000000000000000000000;
    #1;
    if (state_out !== 128'h63636363636363636363636363636363)
      $fatal(1, "Test 2 failed: got %h", state_out);

    // SBOX[0x53] = 0xED for every byte.
    state_in = 128'h53535353535353535353535353535353;
    #1;
    if (state_out !== 128'hedededededededededededededededed)
      $fatal(1, "Test 3 failed: got %h", state_out);

    $display("PASS: aes_sub_bytes");
    $finish;
  end
endmodule
