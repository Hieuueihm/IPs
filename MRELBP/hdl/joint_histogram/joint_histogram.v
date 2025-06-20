module joint_histogram(
	input clk,
	input rst_n,
	input ci_i,
	input [3:0] ni_i,
	input [3:0] rd_i,
	input data_valid_i,
	input finish_i,
	input read_data_en_i, 
	output [31:0] data_o,
	output data_valid_o,
	output finish_read_o,
	output finish_joint_o
	);
	
	wire reset_en;
	wire [7:0] ci_scale;
	assign ci_scale = (ci_i << 6) + (ci_i << 5) + (ci_i << 2);
	wire [7:0] ni_scale;
	assign ni_scale = (ni_i << 3) + (ni_i << 1);

	reg [7:0] ci_d, ni_d, rd_d;
	always @(posedge clk) begin 
	 	if(~rst_n) begin
	 		ci_d <= 0;
	 		ni_d <= 0;
	 		rd_d <= 0;
	 	end else if(data_valid_i) begin
	 		ci_d <= ci_scale;
	 		ni_d <= ni_scale;
	 		rd_d <= {4'b0, rd_i};
	 	end
	 end
	reg data_valid_d; 
	reg data_valid_d1;
	always @(posedge clk) begin 
		if(~rst_n) begin
			data_valid_d <= 0;
			data_valid_d1 <= 0;
		end else begin
			data_valid_d <= data_valid_i;
			data_valid_d1 <= data_valid_d;
		end
	end
	wire  [7:0] addr = (ci_d + ni_d + rd_d);
	reg [7:0] addr_d;
	always @(posedge clk) begin 
		if(~rst_n) begin
			addr_d <= 0;
		end else if(data_valid_d) begin
			addr_d <= addr;
		end
	end


	reg [31:0] mem [0:199];

reg [7:0] reset_counter;
reg resetting;

assign reset_counter_lt_200 = reset_counter < 8'd200;

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
        reset_counter <= 8'd0;
        resetting <= 1'b1;
    end else if (reset_en) begin
        reset_counter <= 8'd0;
        resetting <= 1'b1;
    end else if(~reset_counter_lt_200) begin
    	resetting <= 1'b0;
    end else if (resetting) begin
            reset_counter <= reset_counter + 1'b1;
        end
    end

reg [31:0] data_read;
reg [7:0] addr_for_write;
reg write_request;

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
        addr_for_write <= 8'd0;
    end else if (data_valid_d1) begin
        addr_for_write <= addr_d;
    end
end

assign wr_en = data_valid_d1 && addr_d < 200 && !reset_counter_lt_200;

always @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin
        write_request <= 1'b0;
    end else if (wr_en) begin
        write_request <= 1'b1;
    end else begin
        write_request <= 1'b0;
    end
end

	always @(posedge clk) begin
		if(~rst_n) begin
			data_read <= 0;
		end
	    if (wr_en) begin
	        if (write_request && (addr_for_write == addr_d))
	            data_read <= data_read + 1;
	        else
	            data_read <= mem[addr_d];
	    end

	    if (resetting) begin
	        mem[reset_counter] <= 32'd0;
	    end else if (write_request) begin
	        mem[addr_for_write] <= data_read + 1;
	    end
	end

	shift_registers #(
      .WIDTH(1),
      .CYCLE(4)
  ) shift_rd_output (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(finish_i),
      .data_o(finish_joint_o)
  );
  // assign reset_en = finish_o;

  // read en
  reg [7:0] read_index;
  assign read_index_lt_200 = read_index < 200;
  always @(posedge clk) begin 
  	if(~rst_n) begin
  		read_index <= 0;
  	end else if(reset_en) begin
  		read_index <= 0;
  	end else if(read_data_en_i & read_index_lt_200) begin
  		read_index <= read_index + 1;
  	end
  end
  reg [31:0] data;
  reg data_valid;
  always @(posedge clk) begin 
  	if(~rst_n) begin
  		data <= 0;
  	end else if(read_data_en_i & read_index_lt_200) begin
  		data <= mem[read_index];

  	end
  end
  always @(posedge clk) begin 
  	if(~rst_n) begin
  		data_valid <= 0;
  	end else if(read_data_en_i & read_index_lt_200) begin
  		data_valid <= 1'b1;
  	end else begin
  		data_valid <= 1'b0;
  	end
  end
  assign data_o = data;
  assign data_valid_o = data_valid; 
  assign finish_read_o = ~read_index_lt_200;
  assign reset_en = finish_read_o;




endmodule 