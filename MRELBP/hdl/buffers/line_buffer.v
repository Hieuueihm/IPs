module line_buffer #(parameter DEPTH = 1024)(
    input wire clk,
    input wire rst_n,

    input wire [7:0] s_axis_tdata,
    input wire s_axis_tvalid,
    input wire s_axis_tready,

    input [8:0] IMG_SIZE_I,

    output [7:0] data_o,
    output data_valid_o,
    output wire tfirst_o
);  

    reg [8:0] IMG_SIZE;
    always @(posedge clk) begin
        if(~rst_n) begin
            IMG_SIZE <= 0;
        end else begin
            IMG_SIZE <= IMG_SIZE_I;
        end
    end

    reg reset_en;

    reg [9:0] wr_pointer;
    reg [9:0] rd_pointer;
    reg [31:0] count_num_inp;
    reg [31:0] count_num_oup;

    assign wr_en = s_axis_tvalid & s_axis_tready;
    reg rd_en;
    always @(posedge clk) begin 
        if(~rst_n) begin
            count_num_inp <= 0;
        end else if(reset_en) begin
            count_num_inp <= 0;
        end else if(wr_en) begin
            count_num_inp <= count_num_inp + 1;
        end
    end

    always @(posedge clk) begin 
        if (~rst_n)
            wr_pointer <= 0;
        else if (reset_en)
            wr_pointer <= 0;
        else if (wr_en) begin
            if (wr_pointer == IMG_SIZE - 1)
                wr_pointer <= 0;
            else
                wr_pointer <= wr_pointer + 1;
        end
    end


    always @(posedge clk) begin 
        if (~rst_n) begin
          count_num_oup <= 0;
        end else if (reset_en) begin
          count_num_oup <= 0;
        end else if (rd_en) begin
          count_num_oup <= count_num_oup + 1;
        end
      end


    always @(posedge clk) begin 
        if (~rst_n)
            rd_pointer <= 0;
        else if (reset_en)
            rd_pointer <= 0;
        else if (rd_en) begin
            if (rd_pointer == IMG_SIZE - 1)
                rd_pointer <= 0;
            else
                rd_pointer <= rd_pointer + 1;
        end
    end


    assign first_full = (count_num_inp == IMG_SIZE - 3);
    assign last_full = (count_num_oup == count_num_inp - 2);


    reg first_full_r;
    reg last_full_r;
    always @(posedge clk) begin 
        if(~rst_n) begin
            first_full_r <= 0;
        end else if(wr_en) begin
            first_full_r <= first_full;
        end
    end
    always @(posedge clk) begin 
        if(~rst_n) begin
            last_full_r <= 0;
        end else if(rd_en) begin
            last_full_r <= last_full;
        end
    end




    // read pointer and read num



    // FSM CONTROLLER
    localparam BUFF_IDLE = 2'b00,
            BUFF_READ_EN = 2'b01,
            BUFF_DONE = 2'b10;


    reg [1:0] current_state, next_state;
    always @(posedge clk) begin 
        if(~rst_n) begin
            current_state <= BUFF_IDLE;
        end else begin
            current_state <= next_state;
        end
    end


    always @(*) begin
        next_state = current_state;
        case (current_state)
            BUFF_IDLE: next_state = (first_full_r) ? BUFF_READ_EN : BUFF_IDLE;
            BUFF_READ_EN: next_state = (last_full_r) ? BUFF_DONE : BUFF_READ_EN;
            BUFF_DONE: next_state = BUFF_IDLE;
            default: next_state = BUFF_IDLE; 
        endcase
    end
    reg tfirst_d, tfirst_d1;
    always @(posedge clk) begin
        if(~rst_n) begin
            tfirst_d <= 0;
            tfirst_d1 <= 0;
        end else begin
            tfirst_d <= first_full_r;
            tfirst_d1 <= tfirst_d;
        end
    end
    assign tfirst_o = tfirst_d1;


    always @(*) begin
        reset_en = 1'b0;
        rd_en = 1'b0;
        case (current_state)
            BUFF_IDLE: begin
            
            end
            BUFF_READ_EN: rd_en = 1'b1;
            BUFF_DONE: reset_en = 1'b1;
            default : begin
                reset_en = 1'b0;
                rd_en = 1'b0;

            end
        endcase
    end





    // MEMORY INSTANCE
    memory #(
      .DEPTH(DEPTH),
      .DATA_SIZE(8)
    ) inst_memory (
      .clk(clk),
      .rst_n(rst_n),
      .r_addr(rd_pointer),
      .w_addr(wr_pointer),
      .ren(rd_en),
      .wren(wr_en),
      .w_data(s_axis_tdata),
      .r_data(data_o),
      .data_valid_o(data_valid_o)
  );

endmodule
