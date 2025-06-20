module riu2_mapping (
    input clk,
    input rst_n,
    input data_valid_i,
    input finish_i,
    input bit1_i,
    input bit2_i,
    input bit3_i,
    bit4_i,
    bit5_i,
    bit6_i,
    bit7_i,
    bit8_i,
    output [3:0] data_o,
    output data_valid_o,
    output finish_o
);

  wire b1xor2 = bit1_i ^ bit2_i;
  wire b2xor3 = bit2_i ^ bit3_i;
  wire b3xor4 = bit3_i ^ bit4_i;
  wire b4xor5 = bit4_i ^ bit5_i;
  wire b5xor6 = bit5_i ^ bit6_i;
  wire b6xor7 = bit6_i ^ bit7_i;
  wire b7xor8 = bit7_i ^ bit8_i;
  wire b8xor1 = bit8_i ^ bit1_i;


  wire [1:0] sum_1, sum_2, sum_3, sum_4;
  sum #(
      .WIDTH(1)
  ) SUM1 (
      .clk(clk),
      .rst_n(rst_n),
      .a(b1xor2),
      .b(b2xor3),
      .en(data_valid_i),
      .result(sum_1)
  );
  sum #(
      .WIDTH(1)
  ) SUM2 (
      .clk(clk),
      .rst_n(rst_n),
      .a(b3xor4),
      .b(b4xor5),
      .en(data_valid_i),
      .result(sum_2)
  );
  sum #(
      .WIDTH(1)
  ) SUM3 (
      .clk(clk),
      .rst_n(rst_n),
      .a(b5xor6),
      .b(b6xor7),
      .en(data_valid_i),
      .result(sum_3)
  );
  sum #(
      .WIDTH(1)
  ) SUM4 (
      .clk(clk),
      .rst_n(rst_n),
      .a(b7xor8),
      .b(b8xor1),
      .en(data_valid_i),
      .result(sum_4)
  );

  wire st1_done;
  register #(
      .WIDTH(1)
  ) DONE_register1 (
      .clk(clk),
      .rst_n(rst_n),
      .D(data_valid_i),
      .Q(st1_done)
  );
  wire [2:0] sum_12, sum_34;
  sum #(
      .WIDTH(2)
  ) SUM12 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum_1),
      .b(sum_2),
      .en(st1_done),
      .result(sum_12)
  );
  sum #(
      .WIDTH(2)
  ) SUM34 (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum_3),
      .b(sum_4),
      .en(st1_done),
      .result(sum_34)
  );
  wire st2_done;
  register #(
      .WIDTH(1)
  ) register_DONE2 (
      .clk(clk),
      .rst_n(rst_n),
      .D(st1_done),
      .Q(st2_done)
  );
  wire [3:0] sum_all;
  sum #(
      .WIDTH(3)
  ) SUMALL (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum_12),
      .b(sum_34),
      .en(st2_done),
      .result(sum_all)
  );

  wire [1:0] sum_1_, sum_2_, sum_3_, sum_4_;
  sum #(
      .WIDTH(1)
  ) SUM1_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(bit1_i),
      .b(bit2_i),
      .en(data_valid_i),
      .result(sum_1_)
  );
  sum #(
      .WIDTH(1)
  ) SUM2_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(bit3_i),
      .b(bit4_i),
      .en(data_valid_i),
      .result(sum_2_)
  );
  sum #(
      .WIDTH(1)
  ) SUM3_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(bit5_i),
      .b(bit6_i),
      .en(data_valid_i),
      .result(sum_3_)
  );
  sum #(
      .WIDTH(1)
  ) SUM4_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(bit7_i),
      .b(bit8_i),
      .en(data_valid_i),
      .result(sum_4_)
  );

  wire [2:0] sum12_, sum34_;
  sum #(
      .WIDTH(2)
  ) SUM12_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum_1_),
      .b(sum_2_),
      .en(st1_done),
      .result(sum12_)
  );
  sum #(
      .WIDTH(2)
  ) SUM34_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum_3_),
      .b(sum_4_),
      .en(st1_done),
      .result(sum34_)
  );
  wire [3:0] sumall_;

  sum #(
      .WIDTH(3)
  ) SUMALL_ (
      .clk(clk),
      .rst_n(rst_n),
      .a(sum12_),
      .b(sum34_),
      .en(st2_done),
      .result(sumall_)
  );

  reg [7:0] data;
  always @(posedge clk) begin
    if(~rst_n) begin
      data <= 0;
    end else begin
      data <= (sum_all) > 2 ? 4'd9 : sumall_;
    end
  end
  assign data_o = data;
  wire data_valid;
  
  register #(
      .WIDTH(1)
  ) register_data_valid_3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(st2_done),
      .Q(data_valid)
  );

  register #(
      .WIDTH(1)
  ) register_data_valid_4 (
      .clk(clk),
      .rst_n(rst_n),
      .D(data_valid),
      .Q(data_valid_o)
  );

  shift_registers #(
      .WIDTH(1),
      .CYCLE(4)
  ) SHIFT_PROGRESS (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(finish_i),
      .data_o(finish_o)
  );
endmodule