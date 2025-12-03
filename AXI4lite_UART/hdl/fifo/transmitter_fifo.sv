module transmitter_fifo #(parameter DEPTH = 16)(
	input clk,
	input reset_n,
	input [7:0] fifo_tx_i,
	input fifo_tx_push_i,
	input fifo_tx_pop_i,
	input fifo_tx_reset_i,
	output logic  [7:0] fifo_tx_o,
	output  fifo_tx_empty_o,
	output  fifo_tx_full_o
	);
   localparam PTR_WIDTH = $clog2(DEPTH);
   logic [7:0] mem [0:DEPTH-1];
   logic [PTR_WIDTH-1:0] rd_ptr, wr_ptr;
   logic [PTR_WIDTH:0]   count;

    assign  fifo_tx_empty_o = (count == 0);
    assign fifo_tx_full_o  = (count == DEPTH);
    // logic [7:0] fifo_tx_o_reg;
    assign fifo_tx_o = mem[rd_ptr];
   
     always_ff @(posedge clk) begin
        if (~reset_n ) begin
            rd_ptr <= 0;
            wr_ptr <= 0;
            count  <= 0;
        end else if(fifo_tx_reset_i)  begin 
             rd_ptr <= 0;
            wr_ptr <= 0;
            count  <= 0;
        end else begin
            if (fifo_tx_push_i & !fifo_tx_full_o) begin
                mem[wr_ptr] <= fifo_tx_i;
                wr_ptr <= wr_ptr + 1;
                count <= count + 1;
            end
            if (fifo_tx_pop_i & !fifo_tx_empty_o) begin
                rd_ptr <= rd_ptr + 1;
                count <= count - 1;
            end
        end
    end


endmodule