module aes(
	input clk,
	input rst_n,

	input [127:0] plaintext,
	input [127:0] key,
	input in_valid,

	// output 
	output [127:0] ciphertext,
	output out_valid
	);


	reg [127:0] plaintext_d;
	reg key_d;
	// captured inp
	reg start_r;
	always @(posedge clk or negedge rst_n) begin 
		if(~rst_n) begin
		plaintext_d <= 0;
			key_d <= 0;
			start_r <= 0;
		end else (in_valid) begin
			plaintext_d <= plaintext;
			key_d <= key;
			start_r <= 1;
		end else begin
			start_r <= 0;
		end
	end
	// key expansion
 	reg [127:0] ciphertext_r;
	always @(posedge clk or negedge rst_n) begin 
		if(~rst_n) begin
			ciphertext_r<= 0;
		end else if(start_r) begin
			ciphertext_r <= plaintext_d ^ key;
		end
	end





	// add round Key (xor plaintext with roundKey[0])


endmodule 