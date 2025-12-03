
module uart_tx_top (
    input        clk,
    input        reset_n,
    input        fifo_en_i,              
    input        tx_en_i,
    input        parity_type_i,
    input        parity_en_i,
    input        tick_i,
    input fifo_tx_reset_i,
    input        stop_bit_num_i,
    input [1:0]  data_bit_num_i,
    input [7:0]  data_i,  
    input hf_en_i,
    input cts_ni,              
    input        write_data_i,  
    input start_tx_i,        

    output         tx_o,
    output         fifo_tx_empty_o,
    output         fifo_tx_full_o,
    output         trans_fi_o
);
    logic tx_busy;
    assign fifo_tx_pop = fifo_en_i & trans_fi_o & ~fifo_tx_empty_o;

    // FIFO output
    logic [7:0] fifo_data_out;
    logic       fifo_push;
    logic write_data_d1, write_data_d2;

    always_ff @(posedge clk) begin 
        if (~reset_n) begin
            write_data_d1 <= 0;
            write_data_d2 <= 0;
        end else begin
            write_data_d1 <= write_data_i;
            write_data_d2 <= write_data_d1;
        end
    end
    synchronizer inst_synchronizer (.clk(clk), .reset_n(reset_n), .async(cts_ni), .sync(cts_sync));

    logic tx_busy_pulse;

    assign negedge_write_data_en = ~write_data_d1 & write_data_d2;
    assign fifo_push = fifo_en_i & negedge_write_data_en;
    assign cts_n = hf_en_i ? cts_sync : 0;
    // FIFO instance
    transmitter_fifo fifo_tx_inst (
        .clk(clk),
        .reset_n(reset_n),
        .fifo_tx_i(data_i),
        .fifo_tx_push_i(fifo_push),
        .fifo_tx_pop_i(fifo_tx_pop),
        .fifo_tx_reset_i(fifo_tx_reset_i), 
        .fifo_tx_o(fifo_data_out),
        .fifo_tx_empty_o(fifo_tx_empty_o),
        .fifo_tx_full_o(fifo_tx_full_o)
    );

    // Transmitter input selection
    logic [7:0] tx_data_mux;
    logic       start_tx;

    always_comb begin
        if (fifo_en_i) begin
            tx_data_mux = fifo_data_out;
            start_tx = start_tx_i |  (~fifo_tx_empty_o & tx_busy_pulse);
        end else begin
            tx_data_mux = data_i;
            start_tx    = start_tx_i; 
        end
    end
    logic tx_busy_d;
    always_ff @(posedge clk) begin 
        if(~reset_n) begin
            tx_busy_d <= 0;
        end else begin
            tx_busy_d <= tx_busy;
        end
    end
    assign negedge_tx_busy = ~tx_busy & tx_busy_d;
        always_ff @(posedge clk) begin 
        if(~reset_n) begin
            tx_busy_pulse <= 0;
        end else if (negedge_tx_busy) begin
            tx_busy_pulse <= 1;
        end else begin
            tx_busy_pulse <= 0;
        end
    end
     always_ff @(posedge clk) begin
        if (~reset_n) begin
            tx_busy <= 1'b0;
        end else if (trans_fi_o) begin
            tx_busy <= 1'b0;
        end else if (start_tx & tx_en_i) begin
            tx_busy <= 1'b1;  
        end
    end

    // UART transmitter instance
    uart_transmitter uart_tx_inst (
        .clk(clk),
        .reset_n(reset_n),
        .cts_ni(cts_n),
        .start_tx_i(start_tx),
        .tx_en_i(tx_en_i),
        .parity_type_i(parity_type_i),
        .parity_en_i(parity_en_i),
        .data_i(tx_data_mux),
        .tick_i(tick_i),
        .stop_bit_num_i(stop_bit_num_i),
        .data_bit_num_i(data_bit_num_i),
        .tx_o(tx_o),
        .trans_fi_o(trans_fi_o)
    );

endmodule
