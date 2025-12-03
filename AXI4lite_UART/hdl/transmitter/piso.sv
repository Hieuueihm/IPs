
module piso (
	input clk,    // Clock
	input reset_n,  // Asynchronous reset active low
	input shift_en_i,
	input load_en_i,
	input load_d0_i,
	input [7:0] data_i,
	output logic tx_o
);	
	logic [7:0] data;
	wire  f1, f2, f3, f4, f5, f6, f7;
	assign data[7] = load_en_i ? data_i[7] : 1;
	assign data[6] = load_en_i ? data_i[6] : f7;
	assign data[5] = load_en_i ? data_i[5] : f6;
	assign data[4] = load_en_i ? data_i[4] : f5;
	assign data[3] = load_en_i ? data_i[3] : f4;
	assign data[2] = load_en_i ? data_i[2] : f3;
	assign data[1] = load_en_i ? data_i[1] : f2;
	assign data[0] = (load_d0_i) ? 0 : (load_en_i ? data_i[0] : f1);

	ff ff_1_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[0]), .Q(tx_o));
	ff ff_2_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[1]), .Q(f1));
	ff ff_3_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[2]), .Q(f2));
	ff ff_4_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[3]), .Q(f3));
	ff ff_5_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[4]), .Q(f4));
	ff ff_6_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[5]), .Q(f5));
	ff ff_7_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[6]), .Q(f6));
	ff ff_8_inst (.clk(clk), .reset_n(reset_n), .en_i(shift_en_i), .D(data[7]), .Q(f7));






endmodule 