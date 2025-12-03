
module ff #(parameter BIT_RESET = 1) (
	input clk,    // Clock
	input reset_n,  // Asynchronous reset active low
	input D,
	input en_i,
	output logic Q
);
	always_ff @(posedge clk) begin : proc_
		if(~reset_n) begin
			Q <= BIT_RESET;
		end else if(en_i) begin
			Q <= D;
		end else Q <= Q;
	end

endmodule : ff