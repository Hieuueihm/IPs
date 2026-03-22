module subbytes (
    input  wire [127:0] in,
    output wire [127:0] out
);
    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : sb
            sbox_lut u (
                .in  (in [127 - i*8 -: 8]),
                .out (out[127 - i*8 -: 8])
            );
        end
    endgenerate
endmodule