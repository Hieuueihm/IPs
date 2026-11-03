
module mix_columns (
    input  logic [127:0] state_in,
    output logic [127:0] state_out
);

    function automatic logic [7:0] xtime(
        input logic [7:0] x
    );
        xtime = {x[6:0], 1'b0} ^
                (x[7] ? 8'h1b : 8'h00);
    endfunction

    for (genvar c = 0; c < 4; c++) begin : gen_mix_columns
        wire [31:0] col = state_in[127 - 32*c -: 32];

        wire [7:0] a  = col[31:24];
        wire [7:0] b  = col[23:16];
        wire [7:0] cc = col[15:8];
        wire [7:0] d  = col[7:0];

        assign state_out[127 - 32*c -: 32] = {
            xtime(a) ^ (xtime(b) ^ b) ^ cc ^ d,
            a ^ xtime(b) ^ (xtime(cc) ^ cc) ^ d,
            a ^ b ^ xtime(cc) ^ (xtime(d) ^ d),
            (xtime(a) ^ a) ^ b ^ cc ^ xtime(d)
        };
    end

endmodule
