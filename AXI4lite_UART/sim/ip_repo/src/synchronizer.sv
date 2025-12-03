
module synchronizer(
	input clk,
	input reset_n,
	input async,
	output logic sync
);
	logic d1;

	always_ff @(posedge clk) begin 
		if(~reset_n) begin
			 d1 <= 0;
			 sync <= 0;
		end else begin
			 d1 <= async;
			 sync <= d1;
		end
	end



endmodule