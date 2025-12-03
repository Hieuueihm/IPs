
module parity (
    input  logic        parity_type_i,     // 0: even, 1: odd
    input  logic [7:0]  data_i,
    input  logic [1:0]  data_bit_num_i,    // 00: 5-bit, 01: 6-bit, 10: 7-bit, 11: 8-bit
    output logic        parity_bit_o
);

    logic parity_calculated;

    always_comb begin
        case (data_bit_num_i)
            2'b00: parity_calculated = ^data_i[4:0];   // 5-bit data
            2'b01: parity_calculated = ^data_i[5:0];   // 6-bit data
            2'b10: parity_calculated = ^data_i[6:0];   // 7-bit data
            2'b11: parity_calculated = ^data_i[7:0];   // 8-bit data
            default: parity_calculated = ^data_i;      // Fallback (should not happen)
        endcase

        // Apply parity type: 0 = even, 1 = odd
        parity_bit_o = (parity_type_i) ? parity_calculated : ~parity_calculated;
    end

endmodule : parity
