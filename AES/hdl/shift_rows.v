
module shift_rows (
    input  logic [127:0] state_in,
    output logic [127:0] state_out
);

    // Row 0: No shift
    assign state_out[127:120] = state_in[127:120];
    assign state_out[95:88]   = state_in[95:88];
    assign state_out[63:56]   = state_in[63:56];
    assign state_out[31:24]   = state_in[31:24];

    // Row 1: Left shift 1 byte
    assign state_out[119:112] = state_in[87:80];
    assign state_out[87:80]   = state_in[55:48];
    assign state_out[55:48]   = state_in[23:16];
    assign state_out[23:16]   = state_in[119:112];

    // Row 2: Left shift 2 bytes
    assign state_out[111:104] = state_in[47:40];
    assign state_out[79:72]   = state_in[15:8];
    assign state_out[47:40]   = state_in[111:104];
    assign state_out[15:8]    = state_in[79:72];

    // Row 3: Left shift 3 bytes
    assign state_out[103:96] = state_in[7:0];
    assign state_out[71:64]  = state_in[103:96];
    assign state_out[39:32]  = state_in[71:64];
    assign state_out[7:0]    = state_in[39:32];

endmodule
