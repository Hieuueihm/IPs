module key_expansion(
	input clk,
	input rst_n,

	input [31:0] w0_i,
	input [31:0] w1_i,
	input [31:0] w2_i,
	input [31:0] w3_i,
	input i_valid_i,
	input [3:0] round_i,
	input start_i,


	output [31:0] w4_o,
	output [31:0] w5_o,
	output [31:0] w6_o,
	output [31:0] w7_o,
	output busy_o,
	output data_valid_o

	);


	function [31:0] RotWord(input [31:0] w);
	begin
		RotWord = { w[23:0], w[31:24] };
	end
	endfunction

	reg [1:0] counter;
	reg store_en;
	reg counter_active;
	reg count_en;

	reg [31:0] reg_w3, reg_w2, reg_w1, reg_w0;
	reg [31:0] reg_w4_o, reg_w5_o, reg_w6_o, reg_w7_o;
	reg [31:0] reg_temp, reg_temp1;

	wire load_en;

	reg [31:0] reg_rot_word;

	always @(posedge clk) begin
		if(~rst_n) begin
			counter <= 0;
		end else if(~counter_active)  begin
			counter <= 0;
		end else if(counter_active & count_en) begin
			counter <= counter + 1;
		end
		
	end

	// demux load data
	reg [31:0] reg_xor_data;
	always @(*) begin
		reg_xor_data = 0;
		case(counter)
			2'b00: begin
				reg_xor_data <= reg_w0;
			end

			2'b01: begin
				reg_xor_data <= reg_w1;
			end
			2'b10: begin
				reg_xor_data <= reg_w2;
			end
			2'b11: begin
				reg_xor_data <= reg_w3;
			end
			
		endcase
	end

	// reg temp
	always @(posedge clk ) begin
		if(~rst_n) begin
			reg_temp <= 0;
		end else if(load_en) begin
			reg_temp <= reg_data_load;
		end
	end
	always @(posedge clk) begin
		if(~rst_n) begin
			reg_rot_word <= 0;
		end else if(handle) begin
			reg_rot_word <= RotWord(reg_temp);
		end
		
	end

	


	// copy data
	always @(posedge clk) begin
		if(~rst_n) begin
			reg_w3 <= 0;
			reg_w2 <= 0;
			reg_w1 <= 0;
			reg_w0 <= 0;
		end else if(i_valid_i) begin
			reg_w3 <= w3_i;
			reg_w2 <= w2_i;
			reg_w1 <= w1_i;
			reg_w0 <= w0_i;
		end	else if(store_en & ~|counter) begin
			reg_w0 <= reg_temp1;
		end else if(store_en & counter == 1) begin
			reg_w1 <= reg_temp1;
		end else if(store_en & counter == 2) begin
			reg_w2 <= reg_temp1;
		end else if(store_en & counter == 3) begin
			reg_w3 <= reg_temp1;
		end
	end

endmodule