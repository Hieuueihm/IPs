//  States:
//    IDLE   — wait for key_valid
//    READY  — wait for start and iv_valid (if needed),
//    RUN    — cipher and kem  running in parallel, count rounds
//    DONE   — output ready, wait for next start or key change
//
//  Timing RUN (AES-128, Nr=10):
//
//    Cycle:   0      1      2    ...   9     10
//    KEM:    rk1    rk2    rk3  ...  rk10   idle
//    Cipher: rk0    rk1    rk2  ...   rk9   rk10
//    Flag:  first                           last
//
//  AES-256 (rk0,rk1 từ key_in trực tiếp):
//    Cycle:   0      1      2      3   ...  13    14
//    KEM:    rk2    rk3    rk4    rk5  ...  rk15  idle
//    Cipher: rk0    rk1    rk2    rk3  ...  rk13  rk14
// ============================================================
module controller_fsm (
    input  wire clk,
    input  wire rst_n,

    input  wire       start,       
    input  wire       key_valid,   
    input  wire       iv_valid,   
    input  wire [1:0] mode,      
    input  wire       key_len,     // 0=AES-128 1=AES-256

    output reg        kem_load,    
    output reg        kem_next_rk, 

    output reg        cipher_en,   // 1 when cipher should run (RUN state), 0 otherwise
    output reg        load_state,  // plaintext/IV is loaded into state at first cycle of RUN
    output reg        is_first,    // round 0: skip SubBytes/ShiftRows/MixColumns, only AddRoundKey
    output reg        is_last,     //  Nr: skip MixColumns

    output reg        busy,        // 1 when in RUN, 0 otherwise (ready for new start or key change)
    output reg        key_expanded,// 1 when KEM has loaded key and is ready to provide round keys, 0 otherwise
    output reg        done_pulse,  // 1 for 1 cycle when DONE, indicating output is ready and KEM is reloaded for next block,

    output reg [3:0] round_dbg     // debug: current round number (0..Nr)
);
    localparam [1:0]
        IDLE  = 2'b00,
        READY = 2'b01,
        RUN   = 2'b11,
        DONE  = 2'b10;

    reg [1:0] state;

 
    wire [3:0] Nr     = key_len ? 4'd14 : 4'd10;
    wire       iv_needed = (mode != 2'b00);  

   
    reg [3:0] round_cnt;
    assign round_dbg = (current_state == RUN) ? round_cnt : 4'b0;

    reg [1:0] current_state, next_state;
    wire is_start = start & (!iv_needed | iv_valid)


    always @(posedge clk or negedge rst_n) begin
        if(~rst_n) begin
            round_cnt <= 4'd0;
        end else if (current_state == RUN) begin
            round_cnt <= round_cnt + 4'd1;
        end else begin
            round_cnt <= 4'd0; 
        end
    end


    always @(posedge clk or negedge rst_n) begin
        if(~rst_n) begin
            current_state <= IDLE;
        end else begin
            current_state <= next_state;
        end
    end


    always @(*) begin
        case (current_state)
            IDLE: next_state = (key_valid) ? READY : IDLE;
            READY: next_state = (~key_valid) ? IDLE : is_start ? RUN : READY;
            RUN: next_state = (round_cnt == Nr) ? DONE : RUN;
            DONE: next_state = READY;
            default: next_state = IDLE;
        endcase
    end
   
   
    always @(*) begin
        kem_load    = 1'b0;
        kem_next_rk = 1'b0;
        cipher_en   = 1'b0;
        load_state  = 1'b0;
        is_first    = 1'b0;
        is_last     = 1'b0;
        busy        = 1'b0;
        key_expanded= 1'b0;
        done_pulse  = 1'b0;

        case (state)

            IDLE: begin
                if (key_valid)
                    kem_load = 1'b1;
            end

            READY: begin
                key_expanded = 1'b1; 
                if (is_start)
                    load_state = 1'b1;
            end

            RUN: begin
                busy         = 1'b1;
                key_expanded = 1'b1;
                cipher_en    = 1'b1;  
                is_first = (round_cnt == 4'd0);
                is_last  = (round_cnt == Nr);
                kem_next_rk = (round_cnt < Nr);
            end

            DONE: begin
                key_expanded = 1'b1;
                done_pulse   = 1'b1;  
                kem_load     = 1'b1;
            end

            default: ;

        endcase
    end

endmodule