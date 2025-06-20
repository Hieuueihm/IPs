module z3x3(
 	input            clk,
    input            rst_n,
    input      [7:0] d0_i,        // 99
    input      [7:0] d1_i,        // 8
    input      [7:0] d2_i,        // 7
    input            d0_valid_i,
    input 			 d1_valid_i,
    input 			 d2_valid_i,
    input 		[8:0] IMG_SIZE_I,
    output reg [7:0] d0_o,
    output reg [7:0] d1_o,
    output reg [7:0] d2_o,
    output reg [7:0] d3_o,
    output reg [7:0] d4_o,
    output reg [7:0] d5_o,
    output reg [7:0] d6_o,
    output reg [7:0] d7_o,
    output reg [7:0] d8_o,
    output reg data_valid_o

	);

    reg [8:0] IMG_SIZE;
    always @(posedge clk) begin
        if(~rst_n) begin
            IMG_SIZE <= 0;
        end else begin
            IMG_SIZE <= IMG_SIZE_I;
        end
    end

  reg [7:0] data0, data1, data2, data3, data4, data5, data6, data7, data8;

    reg [9:0] i_row, i_col;
    assign in_valid = d1_valid_i;
    reg reset_en;
    reg count_en;
    wire i_row_lt_1 = (i_row < 1);
    wire i_col_lt_1 = (i_col < 1);
    wire i_col_eq_max = (i_col == IMG_SIZE - 1);
    wire i_row_eq_max = (i_row == IMG_SIZE - 1);
     reg output_en;

    always @(posedge clk) begin
        if (~rst_n) begin
          i_col <= 0;
        end else if (reset_en) begin
          i_col <= 0;
        end else if (i_col_eq_max) begin
          i_col <= 0;
        end else if (output_en) begin
          i_col <= i_col + 1;
        end

    end

    always @(posedge clk) begin
        if (~rst_n) begin
          i_row <= 0;
        end else if (reset_en) begin
          i_row <= 0;
        end else if (i_row == IMG_SIZE_I) begin
          i_row <= 0;
        end else if (output_en & i_col_eq_max) begin
          i_row <= i_row + 1;
        end
    end

     reg [2:0] i_counter;
      always @(posedge clk) begin
        if (~rst_n) begin
          i_counter <= 0;
        end else if (count_en) begin
          i_counter <= i_counter + 1;
        end else begin
          i_counter <= 0;
        end
    end

    assign padding_fi = ~|i_counter;
    assign finish_en  = i_col_eq_max & i_row_eq_max;
    always @(posedge clk) begin
    if (~rst_n) begin
      d0_o <= 0;
      d1_o <= 0;
      d2_o <= 0;
      d3_o <= 0;
      d4_o <= 0;
      d5_o <= 0;
      d6_o <= 0;
      d7_o <= 0;
      d8_o <= 0;

    end else begin
      if (output_en) begin
        d0_o <= (i_row_lt_1 | i_col_lt_1) ? 0 : data0;
        d1_o <= (i_row_lt_1) ? 0 : data1;
        d2_o <= (i_row_lt_1 | i_col_eq_max) ? 0 : data2;
        d3_o <= (i_col_lt_1) ? 0 : data3;
        d4_o <= data4;
        d5_o <= (i_col_eq_max) ? 0 : data5;
        d6_o <= (i_row_eq_max | i_col_lt_1) ? 0 : data6;
        d7_o <= (i_row_eq_max) ? 0 : data7;
        d8_o <= (i_row_eq_max | i_col_eq_max) ? 0 : data8;
      end
    end

  end


  always @(posedge clk) begin
    if (~rst_n) begin
      data0 <= 0;
      data1 <= 0;
      data2 <= 0;
      data3 <= 0;
      data4 <= 0;
      data5 <= 0;
      data6 <= 0;
      data7 <= 0;
      data8 <= 0;

    end else begin
      data0 <= data1;
      data1 <= data2;
      data2 <= d2_i;


      data3 <= data4;
      data4 <= data5;
      data5 <= d1_i;


      data6 <= data7;
      data7 <= data8;
      data8 <= d0_i;

    end

  end

  reg [1:0] current_state;
  reg [1:0] next_state;

  parameter IDLE = 2'b00;
  parameter START = 2'b01;
  parameter DATA = 2'b10;
  parameter DONE = 2'b11;

  always @(posedge clk) begin
    if (~rst_n) begin
      current_state <= IDLE;
    end else begin
      current_state <= next_state;
    end
  end

  always @(*) begin
    next_state = current_state;
    case (current_state)
      IDLE: next_state = (in_valid) ? START : IDLE;
      START: next_state = (padding_fi) ? DATA : START;
      DATA: next_state = (finish_en) ? DONE : DATA;
      DONE: next_state = IDLE;
      default: next_state = IDLE;

    endcase
  end
  
  always @(posedge clk) begin
    if(~rst_n) begin
        data_valid_o <= 0;
    
    end else begin
        data_valid_o <= output_en;
    
    end
  
  end
 
  always @(*) begin
    output_en = 0;
    count_en  = 0;
    reset_en  = 0;
    case (current_state)
      IDLE: begin
      end
      START: begin
        count_en = 1'b1;
        reset_en = 1'b1;
      end
      DATA: begin
        output_en = 1'b1;
      end
      DONE: begin

      end
      default: begin
        output_en = 1'b0;
        count_en  = 1'b0;
        reset_en  = 1'b0;
      end

    endcase
  end









endmodule