module key_expansion #(
    parameter KEY_BITS = 128
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                key_load,
    input  wire [KEY_BITS-1:0] key_in,
    input  wire [3:0]          round_index,
    output reg  [127:0]        round_key,
    output reg                 busy,
    output reg                 key_ready
);

    localparam NK = KEY_BITS / 32;
    localparam NR = (KEY_BITS == 128) ? 10 :
                    (KEY_BITS == 192) ? 12 : 14;
    localparam TOTAL_WORDS = 4 * (NR + 1);

    reg  [31:0] w [0:TOTAL_WORDS-1];
    reg  [6:0]  word_index;
    reg  [31:0] temp;
    integer j;

    wire [31:0] prev_word;
    wire [31:0] sbox_word_in;
    wire [31:0] sub_word;

    assign prev_word = busy ? w[word_index - 7'd1] : 32'b0;

    assign sbox_word_in = (word_index % NK == 0) ?
                          {prev_word[23:0], prev_word[31:24]} :
                           prev_word;

    genvar b;
    generate
        for (b = 0; b < 4; b = b + 1) begin : gen_subword
            sbox u_sbox (
                .in_byte (sbox_word_in[31 - b*8 -: 8]),
                .out_byte(sub_word    [31 - b*8 -: 8])
            );
        end
    endgenerate

    function [7:0] rcon;
        input integer index;
        begin
            case (index)
                1:  rcon = 8'h01;
                2:  rcon = 8'h02;
                3:  rcon = 8'h04;
                4:  rcon = 8'h08;
                5:  rcon = 8'h10;
                6:  rcon = 8'h20;
                7:  rcon = 8'h40;
                8:  rcon = 8'h80;
                9:  rcon = 8'h1b;
                10: rcon = 8'h36;
                default: rcon = 8'h00;
            endcase
        end
    endfunction

    always @(*) begin
        temp = prev_word;
        if (busy) begin
            if ((word_index % NK) == 0)
                temp = sub_word ^ {rcon(word_index / NK), 24'b0};
            else if ((NK == 8) && ((word_index % NK) == 4))
                temp = sub_word;
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            busy       <= 1'b0;
            key_ready  <= 1'b0;
            word_index <= 7'd0;
            for (j = 0; j < TOTAL_WORDS; j = j + 1)
                w[j] <= 32'b0;
        end
        else if (!busy && key_load) begin
            for (j = 0; j < NK; j = j + 1)
                w[j] <= key_in[KEY_BITS - 1 - 32*j -: 32];
            word_index <= NK;
            busy       <= 1'b1;
            key_ready  <= 1'b0;
        end
        else if (busy) begin
            w[word_index] <= w[word_index - NK] ^ temp;
            if (word_index == TOTAL_WORDS - 1) begin
                busy      <= 1'b0;
                key_ready <= 1'b1;
            end
            else begin
                word_index <= word_index + 1'b1;
            end
        end
    end

    always @(*) begin
        round_key = 128'b0;
        if (key_ready && (round_index <= NR)) begin
            round_key = {
                w[round_index * 4],
                w[round_index * 4 + 1],
                w[round_index * 4 + 2],
                w[round_index * 4 + 3]
            };
        end
    end
endmodule
