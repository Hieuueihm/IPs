module z7x7  (
    input            clk,
    input            rst_n,
    input      [7:0] d0_i,
    input      [7:0] d1_i,
    input      [7:0] d2_i,
    input      [7:0] d3_i,
    input      [7:0] d4_i,
    input      [7:0] d5_i,
    input      [7:0] d6_i,
    input       d0_valid_i,
    input d1_valid_i,
    input d2_valid_i,
    input d3_valid_i,
    input d4_valid_i,
    input d5_valid_i,
    input d6_valid_i,
    input [8:0] IMG_SIZE_I,
    output reg [7:0] d0_o,
    output reg [7:0] d1_o,
    output reg [7:0] d2_o,
    output reg [7:0] d3_o,
    output reg [7:0] d4_o,
    output reg [7:0] d5_o,
    output reg [7:0] d6_o,
    output reg [7:0] d7_o,
    output reg [7:0] d8_o,
    output reg [7:0] d9_o,
    output reg [7:0] d10_o,
    output reg [7:0] d11_o,
    output reg [7:0] d12_o,
    output reg [7:0] d13_o,
    output reg [7:0] d14_o,
    output reg [7:0] d15_o,
    output reg [7:0] d16_o,
    output reg [7:0] d17_o,
    output reg [7:0] d18_o,
    output reg [7:0] d19_o,
    output reg [7:0] d20_o,
    output reg [7:0] d21_o,
    output reg [7:0] d22_o,
    output reg [7:0] d23_o,
    output reg [7:0] d24_o,
    output reg [7:0] d25_o,
    output reg [7:0] d26_o,
    output reg [7:0] d27_o,
    output reg [7:0] d28_o,
    output reg [7:0] d29_o,
    output reg [7:0] d30_o,
    output reg [7:0] d31_o,
    output reg [7:0] d32_o,
    output reg [7:0] d33_o,
    output reg [7:0] d34_o,
    output reg [7:0] d35_o,
    output reg [7:0] d36_o,
    output reg [7:0] d37_o,
    output reg [7:0] d38_o,
    output reg [7:0] d39_o,
    output reg [7:0] d40_o,
    output reg [7:0] d41_o,
    output reg [7:0] d42_o,
    output reg [7:0] d43_o,
    output reg [7:0] d44_o,
    output reg [7:0] d45_o,
    output reg [7:0] d46_o,
    output reg [7:0] d47_o,
    output reg [7:0] d48_o,
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
  reg count_en;
  reg reset_en;
  reg output_en;
  assign in_valid = d3_valid_i;
  reg [9:0] i_row, i_col;

  wire i_col_eq_max = (i_col == IMG_SIZE - 1) ? 1 : 0;
  wire i_row_eq_max = (i_row == IMG_SIZE - 1) ? 1 : 0;


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
    end else if (i_row == IMG_SIZE) begin
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
  assign padding_fi = (i_counter == 2) ? 1 : 0;
  assign finish_en  = (i_col_eq_max & i_row_eq_max);

  reg [7:0]
      data0,
      data1,
      data2,
      data3,
      data4,
      data5,
      data6,
      data7,
      data8,
      data9,
      data10,
      data11,
      data12,
      data13,
      data14,
      data15,
      data16,
      data17,
      data18,
      data19,
      data20,
      data21,
      data22,
      data23,
      data24,
      data25,
      data26,
      data27,
      data28,
      data29,
      data30,
      data31,
      data32,
      data33,
      data34,
      data35,
      data36,
      data37,
      data38,
      data39,
      data40,
      data41,
      data42,
      data43,
      data44,
      data45,
      data46,
      data47,
      data48;
  wire i_row_lt_3 = (i_row < 3) ? 1 : 0;
  wire i_row_lt_2 = (i_row < 2) ? 1 : 0;
  wire i_row_lt_1 = (i_row < 1) ? 1 : 0;

  wire i_col_lt_3 = (i_col < 3) ? 1 : 0;
  wire i_col_lt_2 = (i_col < 2) ? 1 : 0;
  wire i_col_lt_1 = (i_col < 1) ? 1 : 0;

  wire i_col_gt_col_2 = (i_col > IMG_SIZE - 2) ? 1 : 0;
  wire i_col_gt_col_3 = (i_col > IMG_SIZE - 3) ? 1 : 0;
  wire i_col_gt_col_4 = (i_col > IMG_SIZE - 4) ? 1 : 0;

  wire i_row_gt_row_2 = (i_row > IMG_SIZE - 2) ? 1 : 0;
  wire i_row_gt_row_3 = (i_row > IMG_SIZE - 3) ? 1 : 0;
  wire i_row_gt_row_4 = (i_row > IMG_SIZE - 4) ? 1 : 0;


  always @(posedge clk) begin
    if (~rst_n) begin
      d0_o  <= 0;
      d1_o  <= 0;
      d2_o  <= 0;
      d3_o  <= 0;
      d4_o  <= 0;
      d5_o  <= 0;
      d6_o  <= 0;
      d7_o  <= 0;
      d8_o  <= 0;
      d9_o  <= 0;
      d10_o <= 0;
      d11_o <= 0;
      d12_o <= 0;
      d13_o <= 0;
      d14_o <= 0;
      d15_o <= 0;
      d16_o <= 0;
      d17_o <= 0;
      d18_o <= 0;
      d19_o <= 0;
      d20_o <= 0;
      d21_o <= 0;
      d22_o <= 0;
      d23_o <= 0;
      d24_o <= 0;
      d25_o <= 0;
      d26_o <= 0;
      d27_o <= 0;
      d28_o <= 0;
      d29_o <= 0;
      d30_o <= 0;
      d31_o <= 0;
      d32_o <= 0;
      d33_o <= 0;
      d34_o <= 0;
      d35_o <= 0;
      d36_o <= 0;
      d37_o <= 0;
      d38_o <= 0;
      d39_o <= 0;
      d40_o <= 0;
      d41_o <= 0;
      d42_o <= 0;
      d43_o <= 0;
      d44_o <= 0;
      d45_o <= 0;
      d46_o <= 0;
      d47_o <= 0;
      d48_o <= 0;

    end else begin
      // zero padding
      if (output_en) begin

        d0_o  <= (i_row_lt_3 | i_col_lt_3) ? 0 : data0;
        d1_o  <= (i_row_lt_3 | i_col_lt_2) ? 0 : data1;
        d2_o  <= (i_row_lt_3 | i_col_lt_1) ? 0 : data2;
        d3_o  <= (i_row_lt_3) ? 0 : data3;
        d4_o  <= (i_row_lt_3 | i_col_gt_col_2) ? 0 : data4;
        d5_o  <= (i_row_lt_3 | i_col_gt_col_3) ? 0 : data5;
        d6_o  <= (i_row_lt_3 | i_col_gt_col_4) ? 0 : data6;

        d7_o  <= (i_row_lt_2 | i_col_lt_3) ? 0 : data7;
        d8_o  <= (i_row_lt_2 | i_col_lt_2) ? 0 : data8;
        d9_o  <= (i_row_lt_2 | i_col_lt_1) ? 0 : data9;
        d10_o <= (i_row_lt_2) ? 0 : data10;
        d11_o <= (i_row_lt_2 | i_col_gt_col_2) ? 0 : data11;
        d12_o <= (i_row_lt_2 | i_col_gt_col_3) ? 0 : data12;
        d13_o <= (i_row_lt_2 | i_col_gt_col_4) ? 0 : data13;

        d14_o <= (i_row_lt_1 | i_col_lt_3) ? 0 : data14;
        d15_o <= (i_row_lt_1 | i_col_lt_2) ? 0 : data15;
        d16_o <= (i_row_lt_1 | i_col_lt_1) ? 0 : data16;
        d17_o <= (i_row_lt_1) ? 0 : data17;
        d18_o <= (i_row_lt_1 | i_col_gt_col_2) ? 0 : data18;
        d19_o <= (i_row_lt_1 | i_col_gt_col_3) ? 0 : data19;
        d20_o <= (i_row_lt_1 | i_col_gt_col_4) ? 0 : data20;

        d21_o <= (i_col_lt_3) ? 0 : data21;
        d22_o <= (i_col_lt_2) ? 0 : data22;
        d23_o <= (i_col_lt_1) ? 0 : data23;
        d24_o <= data24;
        d25_o <= (i_col_gt_col_2) ? 0 : data25;
        d26_o <= (i_col_gt_col_3) ? 0 : data26;
        d27_o <= (i_col_gt_col_4) ? 0 : data27;


        d28_o <= (i_row_gt_row_2 | i_col_lt_3) ? 0 : data28;
        d29_o <= (i_row_gt_row_2 | i_col_lt_2) ? 0 : data29;
        d30_o <= (i_row_gt_row_2 | i_col_lt_1) ? 0 : data30;
        d31_o <= (i_row_gt_row_2) ? 0 : data31;
        d32_o <= (i_row_gt_row_2 | i_col_gt_col_2) ? 0 : data32;
        d33_o <= (i_row_gt_row_2 | i_col_gt_col_3) ? 0 : data33;
        d34_o <= (i_row_gt_row_2 | i_col_gt_col_4) ? 0 : data34;

        d35_o <= (i_row_gt_row_3 | i_col_lt_3) ? 0 : data35;
        d36_o <= (i_row_gt_row_3 | i_col_lt_2) ? 0 : data36;
        d37_o <= (i_row_gt_row_3 | i_col_lt_1) ? 0 : data37;
        d38_o <= (i_row_gt_row_3) ? 0 : data38;
        d39_o <= (i_row_gt_row_3 | i_col_gt_col_2) ? 0 : data39;
        d40_o <= (i_row_gt_row_3 | i_col_gt_col_3) ? 0 : data40;
        d41_o <= (i_row_gt_row_3 | i_col_gt_col_4) ? 0 : data41;

        d42_o <= (i_row_gt_row_4 | i_col_lt_3) ? 0 : data42;
        d43_o <= (i_row_gt_row_4 | i_col_lt_2) ? 0 : data43;
        d44_o <= (i_row_gt_row_4 | i_col_lt_1) ? 0 : data44;
        d45_o <= (i_row_gt_row_4) ? 0 : data45;
        d46_o <= (i_row_gt_row_4 | i_col_gt_col_2) ? 0 : data46;
        d47_o <= (i_row_gt_row_4 | i_col_gt_col_3) ? 0 : data47;
        d48_o <= (i_row_gt_row_4 | i_col_gt_col_4) ? 0 : data48;


      end
    end

  end




  always @(posedge clk) begin
    if (~rst_n) begin
      data0  <= 0;
      data1  <= 0;
      data2  <= 0;
      data3  <= 0;
      data4  <= 0;
      data5  <= 0;
      data6  <= 0;
      data7  <= 0;
      data8  <= 0;
      data9  <= 0;
      data10 <= 0;
      data11 <= 0;
      data12 <= 0;
      data13 <= 0;
      data14 <= 0;
      data15 <= 0;
      data16 <= 0;
      data17 <= 0;
      data18 <= 0;
      data19 <= 0;
      data20 <= 0;
      data21 <= 0;
      data22 <= 0;
      data23 <= 0;
      data24 <= 0;
      data25 <= 0;
      data26 <= 0;
      data27 <= 0;
      data28 <= 0;
      data29 <= 0;
      data30 <= 0;
      data31 <= 0;
      data32 <= 0;
      data33 <= 0;
      data34 <= 0;
      data35 <= 0;
      data36 <= 0;
      data37 <= 0;
      data38 <= 0;
      data39 <= 0;
      data40 <= 0;
      data41 <= 0;
      data42 <= 0;
      data43 <= 0;
      data44 <= 0;
      data45 <= 0;
      data46 <= 0;
      data47 <= 0;
      data48 <= 0;

    end else begin
      // d7 d6 d5 d4 d3 d2 d1
      data0  <= data1;
      data1  <= data2;
      data2  <= data3;
      data3  <= data4;
      data4  <= data5;
      data5  <= data6;
      data6  <= d6_i;


      data7  <= data8;
      data8  <= data9;
      data9  <= data10;
      data10 <= data11;
      data11 <= data12;
      data12 <= data13;
      data13 <= d5_i;

      data14 <= data15;
      data15 <= data16;
      data16 <= data17;
      data17 <= data18;
      data18 <= data19;
      data19 <= data20;
      data20 <= d4_i;

      data21 <= data22;
      data22 <= data23;
      data23 <= data24;
      data24 <= data25;
      data25 <= data26;
      data26 <= data27;
      data27 <= d3_i;


      data28 <= data29;
      data29 <= data30;
      data30 <= data31;
      data31 <= data32;
      data32 <= data33;
      data33 <= data34;
      data34 <= d2_i;


      data35 <= data36;
      data36 <= data37;
      data37 <= data38;
      data38 <= data39;
      data39 <= data40;
      data40 <= data41;
      data41 <= d1_i;

      data42 <= data43;
      data43 <= data44;
      data44 <= data45;
      data45 <= data46;
      data46 <= data47;
      data47 <= data48;
      data48 <= d0_i;

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