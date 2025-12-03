
module uart_rx_top (
    input        clk,
    input        reset_n,
    input        rx_en_i,
    input        tick_i,
    input        parity_type_i,
    input        parity_en_i,
    input        tx_i,
    input fifo_rx_reset_i,
    input        stop_bit_num_i,
    input [1:0]  data_bit_num_i,
    input        fifo_en_i,    
    input  force_rts_i,                
    input        fifo_rx_pop_i,
    input [1:0]  fifo_rx_trig_level_i,
    input        hf_en_i,
    input rdr_empty_i,
    output logic [7:0]  data_o,
    output logic        data_o_valid,
    output logic        parity_err_o,
    output logic        stop_bit_err_o,
    output logic        fifo_rx_empty_o,
    output fifo_rx_overrun,
    output logic rts_no
);

    // UART Receiver 
    logic [7:0] receiver_data;
    logic       receiver_data_valid;
    wire fifo_rx_full_o;
    wire trigger_fifo_lt_14;
    assign trigger_fifo_lt_14 = ~(fifo_rx_trig_level_i[0] & fifo_rx_trig_level_i[1]);

    uart_receiver uart_rx_inst (
        .clk(clk),
        .reset_n(reset_n),
        .rx_en_i(rx_en_i),
        .tick_i(tick_i),
        .parity_type_i(parity_type_i),
        .parity_en_i(parity_en_i),
        .tx_i(tx_i),
        .rts_ni        (rts_no),
        .stop_bit_num_i(stop_bit_num_i),
        .data_bit_num_i(data_bit_num_i),
        .data_o(receiver_data),
        .data_o_valid(receiver_data_valid),
        .parity_err_o(parity_err_o),
        .stop_bit_err_o(stop_bit_err_o)
    );
    wire fifo_rx_triggered;
    logic [7:0] fifo_out;
    logic       fifo_push;


    
    always_ff @(posedge clk) begin
        if(~reset_n) begin
            rts_no <= 0;
        end else if(hf_en_i) begin
           if(force_rts_i) begin
            rts_no <= 0;
            end else if( (~fifo_en_i & ~rdr_empty_i) | (fifo_en_i &(trigger_fifo_lt_14 & fifo_rx_triggered) | (~trigger_fifo_lt_14 & fifo_rx_triggered))) begin 
                rts_no <= 1;
            end else if(  (~fifo_en_i & rdr_empty_i) | (fifo_en_i & (trigger_fifo_lt_14 & rts_no & fifo_rx_empty_o) | (~trigger_fifo_lt_14 & ~fifo_rx_triggered))) begin
                rts_no <= 0;
            end
         end
        
    end

    assign fifo_push = fifo_en_i && receiver_data_valid;
    //  FIFO 

    receiver_fifo fifo_rx_inst (
        .clk(clk),
        .reset_n(reset_n),
        .fifo_rx_i(receiver_data),
        .fifo_rx_push_i(fifo_push),
        .fifo_rx_pop_i(fifo_rx_pop_i),
        .fifo_rx_reset_i(fifo_rx_reset_i),  
        .fifo_rx_o(fifo_out),
        .fifo_rx_empty_o(fifo_rx_empty_o),
        .fifo_rx_trig_level_i(fifo_rx_trig_level_i),
        .fifo_rx_full_o(fifo_rx_full_o),
        .fifo_rx_triggered_o (fifo_rx_triggered)
           );
    logic fifo_rx_pop_d;
    always_ff @(posedge clk) begin 
        if(~reset_n) begin
            fifo_rx_pop_d <= 0;
        end else begin
            fifo_rx_pop_d <= fifo_rx_pop_i;
        end
    end
    wire negedge_rx_pop= ~fifo_rx_pop_i & fifo_rx_pop_d;
    assign fifo_rx_overrun = fifo_en_i & fifo_rx_full_o & receiver_data_valid;
    
    logic [7:0] msg;
    logic data_valid;

    always_comb begin
        if (fifo_en_i) begin
            msg       = fifo_out;
            data_valid = (fifo_rx_empty_o & receiver_data_valid) | (~fifo_rx_empty_o & negedge_rx_pop );
        end else begin
            msg       = receiver_data;
            data_valid = receiver_data_valid;
        end
    end
    logic data_valid_d;
    always_ff @(posedge clk) begin : proc_
        if(~reset_n) begin
            data_o_valid <= 0;
            data_valid_d <= 0;      
        end else  begin
            data_valid_d <= data_valid;
             data_o_valid <= data_valid_d;
        end
    end
    always_ff @(posedge clk) begin
        if(~reset_n) begin
            data_o <= 0;
        end else if(data_valid_d) begin
            data_o <= msg;
        end
    end

endmodule
