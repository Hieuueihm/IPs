module r2_controller  (
    input clk,
    input rst_n,
    input start_i,
    input i_start_gt_1,
    input [9:0] i_counter,
    input i_row_eq_max,
    input [8:0] IMG_SIZE_I,
    output reg cum_en,
    output reg data_valid_o,
    output reg sum_en,
    output reg count_en,
    output reg start_en,
    output reg ld_en,
    output reg finish_o,
    output reg reset_en
 
);
 
  reg [2:0] current_state;
  reg [2:0] next_state, prev_state;
  parameter IDLE = 3'b000;
  parameter START = 3'b001;
  parameter START_ROW = 3'b010;
  parameter SUM_EN = 3'b011; // 3
  parameter CUM_EN = 3'b100; // 4
  parameter FINISH_ALL = 3'b101; //5
  always @(posedge clk) begin
    if (~rst_n) begin
      current_state <= IDLE;
      prev_state <= IDLE;
    end else begin
      prev_state = current_state;
      current_state <= next_state;
    end
  end

  always @(*) begin
    // next_state = current_state;
    case (current_state)
      IDLE: next_state = (start_i) ? START : IDLE;
      START: next_state = (i_start_gt_1 == 1'b1) ? START_ROW : START;
      START_ROW: next_state = SUM_EN;
      SUM_EN: next_state = i_row_eq_max ? FINISH_ALL : (i_counter > 3) ? CUM_EN : SUM_EN;
      CUM_EN: next_state = (i_counter > IMG_SIZE_I - 2) ? START_ROW : CUM_EN;
      FINISH_ALL: next_state = IDLE;
      default: next_state = IDLE;
    endcase
  end

  always @(*) begin
    // Giá trị mặc định cho tất cả tín hiệu
    count_en      = 1'b0;
    data_valid_o        = 1'b0;
    cum_en        = 1'b0;
    ld_en         = 1'b0;
    sum_en        = 1'b0;
    start_en      = 1'b0;
    finish_o = 1'b0;
    reset_en      = 1'b0;

    case (current_state)
      IDLE: begin
        // Giữ nguyên giá trị mặc định
      end
      START: begin
        start_en = 1'b1;
      end
      START_ROW: begin
        count_en = 1'b1;
        ld_en    = 1'b1;
        if (prev_state == CUM_EN) begin
          data_valid_o = 1'b1;
        end
      end
      SUM_EN: begin
        count_en = 1'b1;
        sum_en   = 1'b1;
      end
      CUM_EN: begin
        count_en = 1'b1;
        sum_en   = 1'b1;
        cum_en   = 1'b1;
        data_valid_o   = 1'b1;
      end
      FINISH_ALL: begin
        finish_o = 1'b1;
        reset_en = 1'b1;
        data_valid_o = 1'b0;
      end
      default: begin
        // Giữ nguyên giá trị mặc định
        count_en      = 1'b0;
        data_valid_o        = 1'b0;
        cum_en        = 1'b0;
        ld_en         = 1'b0;
        sum_en        = 1'b0;
        start_en      = 1'b0;
        finish_o = 1'b0;
        reset_en      = 1'b0;
      end
    endcase
  end

endmodule