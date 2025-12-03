
module shift_register(
		input clk,
		input reset_n,
		input shift_en_i,
		input data_i,
		output [7:0] data_o
	);
	logic [7:0] shift_regs;
	always_ff @(posedge clk) begin
		if(~reset_n) begin
			shift_regs <= 0;
		end else if(shift_en_i) begin
			 shift_regs <= {data_i, shift_regs[7:1]} ;
		end
	end

	assign data_o = shift_regs;


endmodule