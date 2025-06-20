module window_buffer_controller (
    input clk,
    input rst_n,
    input start_i,
    input i_row_eq_max,
    input i_col_eq_max,
    input i_col_ge_threshold,
    output reg count_en,
    output reg finish_o,
    output reg data_valid_o,
    output reg reset_en
);

  reg [2:0] current_state, next_state;
  parameter IDLE = 3'b000;
  parameter START = 3'b001;
  parameter START_COL = 3'b010;
  parameter COL_OUT = 3'b011;
  parameter END_COL = 3'b100;
  parameter FINISH_ALL = 3'b110;
  always @(posedge clk) begin
    if (~rst_n) begin
      current_state <= IDLE;
    end else begin
      current_state <= next_state;
    end
  end

  always @(*) begin
    case (current_state)
      IDLE: next_state = (start_i) ? START : IDLE;
      START: next_state = START_COL;
      START_COL: next_state = (i_col_ge_threshold) ? COL_OUT : START_COL;
      COL_OUT: next_state = (i_col_eq_max) ? END_COL : COL_OUT;
      END_COL: next_state = i_row_eq_max ? FINISH_ALL : START_COL;
      FINISH_ALL: next_state = IDLE;
      default: next_state = IDLE;
    endcase
  end
  always @(*) begin
    count_en      = 1'b0;
    data_valid_o        = 1'b0;
    finish_o = 1'b0;
    reset_en      = 1'b0;
    case (current_state)
      IDLE: begin

      end
      START_COL: begin
        count_en = 1'b1;
      end
      COL_OUT: begin
        count_en = 1'b1;
        data_valid_o   = 1'b1;
      end
      END_COL: begin
        data_valid_o = 1'b1;
      end

      FINISH_ALL: begin
        finish_o = 1'b1;
        reset_en = 1'b1;

      end
      default: begin
        count_en      = 1'b0;
        data_valid_o        = 1'b0;
        finish_o = 1'b0;
        reset_en      = 1'b0;
      end
    endcase

  end


endmodule
