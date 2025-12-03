module receiver_fifo #(
    parameter DEPTH = 16,
    parameter int TRIG_LEVELS[0:3] = '{1, 4, 8, 14}  // Can redefine for deeper FIFOs

)(
    input            clk,
    input             reset_n,

    input   [7:0] fifo_rx_i,
    input               fifo_rx_push_i,
    input               fifo_rx_pop_i,
    input               fifo_rx_reset_i,

    input   [1:0]       fifo_rx_trig_level_i,

    output logic [7:0] fifo_rx_o,
    output              fifo_rx_empty_o,
    output              fifo_rx_full_o,
    output fifo_rx_triggered_o
    );

    localparam PTR_WIDTH = $clog2(DEPTH);
    logic [7:0] mem [0:DEPTH-1];
    logic [PTR_WIDTH-1:0] rd_ptr, wr_ptr;
    logic [PTR_WIDTH:0]   count;
    assign fifo_rx_triggered_o = (count >= TRIG_LEVELS[fifo_rx_trig_level_i]);

    assign fifo_rx_empty_o = (count == 0);
    assign fifo_rx_full_o  = (count == DEPTH);
    assign fifo_rx_o = mem[rd_ptr];

    always_ff @(posedge clk) begin
        if (fifo_rx_reset_i | ~reset_n) begin
            rd_ptr <= 0;
            wr_ptr <= 0;
            count  <= 0;
        end else begin
            if (fifo_rx_push_i & !fifo_rx_full_o) begin
                mem[wr_ptr] <= fifo_rx_i;
                wr_ptr <= wr_ptr + 1;
                count <= count + 1;
            end
            if (fifo_rx_pop_i & !fifo_rx_empty_o) begin
                rd_ptr <= rd_ptr + 1;
                count <= count - 1;
            end
        end
    end
endmodule
