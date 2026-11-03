
module sub_bytes (
    input  wire [127:0] state_in,
    output wire [127:0] state_out
);
    genvar b;
    generate
        for (b = 0; b < 16; b = b + 1) begin : gen_sbox
            sbox u_sbox (
                .in_byte (state_in [127 - b*8 -: 8]),
                .out_byte(state_out[127 - b*8 -: 8])
            );
        end
    endgenerate
endmodule
