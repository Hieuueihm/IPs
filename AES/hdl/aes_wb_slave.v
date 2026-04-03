
module aes_wb_slave (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        wb_cyc,
    input  wire        wb_stb,
    input  wire        wb_we,
    input  wire [7:0]  wb_adr,
    input  wire [31:0] wb_dat_i,
    input  wire [3:0]  wb_sel,
    output wire        wb_ack,
    output wire        wb_stall,
    output wire [31:0] wb_dat_o,
    output wire        wb_err,

    output wire        irq
);


    wire [7:0]  wr_addr;
    wire [31:0] wr_data;
    wire        wr_en;
    wire [7:0]  rd_addr;
    wire [31:0] rd_data;


    wire        start;
    wire [1:0]  mode;
    wire        op;
    wire        key_len;
    wire        key_valid;
    wire        iv_valid;
    wire        auto_start;
    wire        auto_iv_upd;
    wire        irq_en;
    wire [255:0] key_out;
    wire [127:0] iv_out;
    wire [127:0] din_out;


    wire        kem_load;
    wire        kem_next_rk;
    wire        cipher_en;
    wire        load_state;
    wire        is_first;
    wire        is_last;
    wire        busy;
    wire        done_pulse;
    wire kem_load_dec;
    wire kem_save_dec;
    wire key_expanded;
    wire [3:0]  round_dbg;

    wire [127:0] rk_out;
    wire         rk_valid;

    wire [3:0]  round_cnt = round_dbg;

    wire [127:0] round_key =
        (!op && !key_len && round_cnt==0) ? key_out[255:128]   :
        (!op &&  key_len && round_cnt==0) ? key_out[255:128] :
        (!op &&  key_len && round_cnt==1) ? key_out[127:0]   :
                                            rk_out;
    wire [127:0] cipher_in_data; 
    wire [127:0] dout_data;       
    wire [127:0] iv_next;
    wire         iv_upd;


    reg  [127:0] state_reg;
    wire [127:0] state_out; 

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state_reg <= 128'h0;
        else if (load_state)
            state_reg <= cipher_in_data;
        else if (cipher_en)
            state_reg <= state_out;
    end

   
    wire        iv_upd_trig;      

 
    assign iv_upd_trig = done_pulse && iv_upd && auto_iv_upd;

  
    wb_interface u_wb (
        .CLK_I      (clk),
        .RST_I      (rst_n),
        .ADR_I      (wb_adr),
        .DAT_I      (wb_dat_i),
        .DAT_O      (wb_dat_o),
        .WE_I       (wb_we),
        .SEL_I      (wb_sel),
        .STB_I      (wb_stb),
        .ACK_O      (wb_ack),
        .CYC_I      (wb_cyc),
        .STALL_O    (wb_stall),
        .ERR_O      (wb_err),
        .wr_addr    (wr_addr),
        .wr_data    (wr_data),
        .wr_en      (wr_en),
        .rd_addr    (rd_addr),
        .rd_data    (rd_data),
        .busy       (busy)
    );






    regs u_reg (
        .clk            (clk),
        .rst_n          (rst_n),
        .wr_addr        (wr_addr),
        .wr_data        (wr_data),
        .wr_en          (wr_en),
        .rd_addr        (rd_addr),
        .rd_data        (rd_data),
        .start          (start),
        .mode           (mode),
        .op             (op),
        .key_len        (key_len),
        .key_valid      (key_valid),
        .iv_valid       (iv_valid),
        .auto_start     (auto_start),
        .auto_iv_upd    (auto_iv_upd),
        .irq_en         (irq_en),
        .key_expanded   (key_expanded),

        .key_out        (key_out),
        .iv_out         (iv_out),
        .din_out        (din_out),

        .dout_in        (dout_data),
        .dout_wr        (done_pulse),
        .busy           (busy),
        .iv_upd_trig    (iv_upd_trig),
        .iv_next        (iv_next),
        .irq            (irq)
    );

    controller_fsm u_ctrl (
        .clk          (clk),
        .rst_n        (rst_n),
        .start        (start),
        .key_valid    (key_valid),
        .iv_valid     (iv_valid),
        .mode         (mode),
        .key_len      (key_len),
        .op           (op),
        .kem_load_dec (kem_load_dec),
        .kem_save_dec (kem_save_dec),
        .key_expanded (key_expanded),
        .kem_load     (kem_load),
        .kem_next_rk  (kem_next_rk),
        .cipher_en    (cipher_en),
        .load_state   (load_state),
        .is_first     (is_first),
        .is_last      (is_last),
        .busy         (busy),
        .done_pulse   (done_pulse),
        .round_dbg    (round_dbg)
    );

    kem_core u_kem (
        .clk      (clk),
        .rst_n    (rst_n),
        .key_in   (key_out),
        .key_len  (key_len),
        .op       (op),
        .load_dec (kem_load_dec),
        .save_dec (kem_save_dec),
        .load     (kem_load),
        .next_rk  (kem_next_rk),
        .rk_out   (rk_out),
        .rk_valid (rk_valid)
    );

    mode_logic u_mode (
        .din        (din_out),
        .iv         (iv_out),
        .cipher_out (state_out),  
        .mode       (mode),
        .op         (op),
        .cipher_in  (cipher_in_data),
        .dout       (dout_data),
        .iv_next    (iv_next),
        .iv_upd     (iv_upd)
    );

    cipher_round u_cipher (
        .state_in  (state_reg),
        .round_key (round_key),
        .is_first  (is_first),
        .is_last   (is_last),
        .decrypt   (op),
        .state_out (state_out)
    );

endmodule