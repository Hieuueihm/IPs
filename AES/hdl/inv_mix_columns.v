
module inv_mix_columns (
    input  logic [127:0] state_in,
    output logic [127:0] state_out
);

    function automatic logic [7:0] xtime(
        input logic [7:0] x
    );
        xtime = {x[6:0], 1'b0} ^
                (x[7] ? 8'h1b : 8'h00);
    endfunction

    for (genvar c = 0; c < 4; c++) begin : gen_inv_mix_columns
        wire [31:0] col = state_in[127 - 32*c -: 32];

        wire [7:0] a  = col[31:24];
        wire [7:0] b  = col[23:16];
        wire [7:0] cc = col[15:8];
        wire [7:0] d  = col[7:0];

        wire [7:0] a2 = xtime(a);
        wire [7:0] a4 = xtime(a2);
        wire [7:0] a8 = xtime(a4);

        wire [7:0] b2 = xtime(b);
        wire [7:0] b4 = xtime(b2);
        wire [7:0] b8 = xtime(b4);

        wire [7:0] c2 = xtime(cc);
        wire [7:0] c4 = xtime(c2);
        wire [7:0] c8 = xtime(c4);

        wire [7:0] d2 = xtime(d);
        wire [7:0] d4 = xtime(d2);
        wire [7:0] d8 = xtime(d4);

        assign state_out[127 - 32*c -: 32] = {
            (a8 ^ a4 ^ a2) ^ (b8 ^ b2 ^ b)  ^
            (c8 ^ c4 ^ cc) ^ (d8 ^ d),

            (a8 ^ a) ^ (b8 ^ b4 ^ b2) ^
            (c8 ^ c2 ^ cc) ^ (d8 ^ d4 ^ d),

            (a8 ^ a4 ^ a) ^ (b8 ^ b) ^
            (c8 ^ c4 ^ c2) ^ (d8 ^ d2 ^ d),

            (a8 ^ a2 ^ a) ^ (b8 ^ b4 ^ b) ^
            (c8 ^ cc) ^ (d8 ^ d4 ^ d2)
        };
    end

endmodule
