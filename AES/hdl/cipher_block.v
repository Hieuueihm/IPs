module cipher_block #(
    parameter KEY_BITS = 128
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                key_load,
    input  wire [KEY_BITS-1:0] key_in,
    output wire                key_ready,
    input  wire                start,
    input  wire [127:0]        data_in,
    output reg  [127:0]        data_out,
    output wire                busy,
    output reg                 done
);
    localparam NR = (KEY_BITS == 128) ? 10 :
                    (KEY_BITS == 192) ? 12 : 14;

    localparam ST_IDLE  = 2'd0;
    localparam ST_INIT  = 2'd1;
    localparam ST_MAIN  = 2'd2;
    localparam ST_FINAL = 2'd3;

    reg  [1:0]   phase;
    reg  [127:0] state_reg;
    reg  [3:0]   round_index;
    reg          block_busy;
    wire         key_busy;
    wire         accepted_key_load;
    wire [127:0] round_key;

   
    assign busy = key_busy | block_busy;
    assign accepted_key_load = key_load && !busy && !start;

    key_expansion #(.KEY_BITS(KEY_BITS)) u_key_expansion (
        .clk(clk),
        .rst_n(rst_n),
        .key_load(accepted_key_load),
        .key_in(key_in),
        .round_index(round_index),
        .round_key(round_key),
        .busy(key_busy),
        .key_ready(key_ready)
    );

   
    wire [127:0] sub_out;
    wire [127:0] shift_out;
    wire [127:0] mix_out;
    wire [127:0] xor_in;
    wire [127:0] xor_out;

    sub_bytes u_sub_bytes (
        .state_in(state_reg),
        .state_out(sub_out)
    );

    shift_rows u_shift_rows (
        .state_in(sub_out),
        .state_out(shift_out)
    );

    mix_columns u_mix_columns (
        .state_in(shift_out),
        .state_out(mix_out)
    );

    assign xor_in = (phase == ST_INIT)  ? state_reg :
                    (phase == ST_FINAL) ? shift_out :
                                          mix_out;

    add_round_key u_add_round_key (
        .state_in(xor_in),
        .round_key(round_key),
        .state_out(xor_out)
    );


    always @(posedge clk) begin
        if (!rst_n) begin
            phase       <= ST_IDLE;
            block_busy  <= 1'b0;
            state_reg   <= 128'b0;
            round_index <= 4'd0;
            data_out    <= 128'b0;
            done        <= 1'b0;
        end else begin
            done <= 1'b0;

            case (phase)
                ST_IDLE: begin
                    if (start && key_ready && !key_busy && !key_load) begin
                        state_reg   <= data_in;
                        round_index <= 4'd0;
                        block_busy  <= 1'b1;
                        phase       <= ST_INIT;
                    end
                end

                ST_INIT: begin
                    state_reg   <= xor_out;
                    round_index <= 4'd1;
                    phase       <= ST_MAIN;
                end

                ST_MAIN: begin
                    state_reg <= xor_out;
                    if (round_index == NR - 1) begin
                        round_index <= NR;
                        phase <= ST_FINAL;
                    end else begin
                        round_index <= round_index + 4'd1;
                    end
                end

                ST_FINAL: begin
                    data_out   <= xor_out;
                    block_busy <= 1'b0;
                    done       <= 1'b1;
                    phase      <= ST_IDLE;
                end

                default: begin
                    phase      <= ST_IDLE;
                    block_busy <= 1'b0;
                end
            endcase
        end
    end
endmodule
