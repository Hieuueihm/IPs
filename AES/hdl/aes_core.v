module aes_core #(
    parameter KEY_BITS = 128
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                key_load,
    input  wire [KEY_BITS-1:0] key_in,
    output wire                key_ready,
    input  wire                iv_load,
    input  wire [127:0]        iv_in,
    output wire [127:0]        iv_out,
    input  wire [1:0]          mode,       // 00=ECB, 01=CBC, 10=CTR
    input  wire                decrypt,    // ignored in CTR (forward cipher)
    input  wire                start,
    input  wire [127:0]        data_in,
    output reg  [127:0]        data_out,
    output wire                busy,
    output reg                 done
);
    localparam MODE_ECB = 2'b00;
    localparam MODE_CBC = 2'b01;
    localparam MODE_CTR = 2'b10;

    reg  [127:0] current_iv;
    reg  [127:0] saved_input;
    reg  [1:0]   saved_mode;
    reg          saved_decrypt;
    reg          active;

    wire [127:0] enc_data_in;
    wire [127:0] dec_data_in;
    wire [127:0] enc_data_out;
    wire [127:0] dec_data_out;
    wire enc_busy, dec_busy;
    wire enc_done, dec_done;
    wire enc_key_ready, dec_key_ready;
    wire enc_start, dec_start;
    wire accept_start;
    wire use_dec;

    assign iv_out = current_iv;
    assign key_ready = enc_key_ready & dec_key_ready;
    assign busy = active | enc_busy | dec_busy;

    assign accept_start = start & !busy & key_ready & !key_load & !iv_load &
                          (mode != 2'b11);
    assign use_dec = decrypt & (mode != MODE_CTR);
    assign enc_start = accept_start & !use_dec;
    assign dec_start = accept_start & use_dec;

    assign enc_data_in = (mode == MODE_CBC) ? (data_in ^ current_iv) :
                         (mode == MODE_CTR) ? current_iv : data_in;
    assign dec_data_in = data_in;

    cipher_block #(.KEY_BITS(KEY_BITS)) u_encrypt (
        .clk(clk), .rst_n(rst_n),
        .key_load(key_load & !busy & !start), .key_in(key_in),
        .key_ready(enc_key_ready),
        .start(enc_start), .data_in(enc_data_in),
        .data_out(enc_data_out), .busy(enc_busy), .done(enc_done)
    );

    inv_cipher_block #(.KEY_BITS(KEY_BITS)) u_decrypt (
        .clk(clk), .rst_n(rst_n),
        .key_load(key_load & !busy & !start), .key_in(key_in),
        .key_ready(dec_key_ready),
        .start(dec_start), .data_in(dec_data_in),
        .data_out(dec_data_out), .busy(dec_busy), .done(dec_done)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            current_iv    <= 128'b0;
            saved_input   <= 128'b0;
            saved_mode    <= MODE_ECB;
            saved_decrypt <= 1'b0;
            active        <= 1'b0;
            data_out      <= 128'b0;
            done          <= 1'b0;
        end else begin
            done <= 1'b0;

            if (iv_load && !busy && !start && !key_load)
                current_iv <= iv_in;

            if (accept_start) begin
                saved_input   <= data_in;
                saved_mode    <= mode;
                saved_decrypt <= use_dec;
                active        <= 1'b1;
            end

            if (active && ((saved_decrypt && dec_done) ||
                           (!saved_decrypt && enc_done))) begin
                active <= 1'b0;
                done   <= 1'b1;
                case (saved_mode)
                    MODE_ECB: begin
                        data_out <= saved_decrypt ? dec_data_out : enc_data_out;
                    end
                    MODE_CBC: begin
                        if (saved_decrypt) begin
                            data_out   <= dec_data_out ^ current_iv;
                            current_iv <= saved_input; 
                        end else begin
                            data_out   <= enc_data_out;
                            current_iv <= enc_data_out;
                        end
                    end
                    MODE_CTR: begin
                        data_out   <= saved_input ^ enc_data_out;
                        current_iv <= current_iv + 128'd1;
                    end
                    default: data_out <= 128'b0;
                endcase
            end
        end
    end
endmodule
