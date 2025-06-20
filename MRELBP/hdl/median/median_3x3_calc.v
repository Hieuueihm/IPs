module median_3x3_calc (
    input clk,
    input rst_n,
    input data_valid_i,
    input [7:0] S1,
    input [7:0] S2,
    input [7:0] S3,
    input [7:0] S4,
    input [7:0] S5,
    input [7:0] S6,
    input [7:0] S7,
    input [7:0] S8,
    input [7:0] S9,
    output [7:0] median_o,
    output data_valid_o
);

  reg [7:0] p1_S1, p1_S2, p1_S3;
  reg [7:0] p1_S4, p1_S5, p1_S6;
  reg [7:0] p1_S7, p1_S8, p1_S9;
  reg p1_done_i;

  always @(posedge clk) begin
    if (~rst_n) begin
      p1_S1     <= 0;
      p1_S2     <= 0;
      p1_S3     <= 0;
      p1_S4     <= 0;
      p1_S5     <= 0;
      p1_S6     <= 0;
      p1_S7     <= 0;
      p1_S8     <= 0;
      p1_S9     <= 0;
      p1_done_i <= 0;
    end else begin
      p1_S1     <= S1;
      p1_S2     <= S2;
      p1_S3     <= S3;
      p1_S4     <= S4;
      p1_S5     <= S5;
      p1_S6     <= S6;
      p1_S7     <= S7;
      p1_S8     <= S8;
      p1_S9     <= S9;
      p1_done_i <= data_valid_i;
    end
  end

  wire [7:0] max1, med1, min1;
  wire [7:0] max2, med2, min2;
  wire [7:0] max3, med3, min3;

  reg [7:0] p2_max1, p2_med1, p2_min1;
  reg [7:0] p2_max2, p2_med2, p2_min2;
  reg [7:0] p2_max3, p2_med3, p2_min3;
  reg p2_done_i;

  wire [7:0] min4, min5, med5, max4, max5;

  reg [7:0] p3_min5, p3_med5, p3_max5;
  wire [7:0] p3_median;
  reg        p3_done_i;

  sorting_network SN1 (
      .S1 (p1_S1),
      .S2 (p1_S2),
      .S3 (p1_S3),
      .max(max1),
      .med(med1),
      .min(min1)
  );

  sorting_network SN2 (
      .S1 (p1_S4),
      .S2 (p1_S5),
      .S3 (p1_S6),
      .max(max2),
      .med(med2),
      .min(min2)
  );

  sorting_network SN3 (
      .S1 (p1_S7),
      .S2 (p1_S8),
      .S3 (p1_S9),
      .max(max3),
      .med(med3),
      .min(min3)
  );

  always @(posedge clk) begin
    if (~rst_n) begin
      p2_max1   <= 0;
      p2_med1   <= 0;
      p2_min1   <= 0;
      p2_max2   <= 0;
      p2_med2   <= 0;
      p2_min2   <= 0;
      p2_max3   <= 0;
      p2_med3   <= 0;
      p2_min3   <= 0;
      p2_done_i <= 0;
    end else begin
      p2_max1   <= max1;
      p2_med1   <= med1;
      p2_min1   <= min1;
      p2_max2   <= max2;
      p2_med2   <= med2;
      p2_min2   <= min2;
      p2_max3   <= max3;
      p2_med3   <= med3;
      p2_min3   <= min3;
      p2_done_i <= p1_done_i;
    end
  end

  node N1 (
      .A(p2_min1),
      .B(p2_min2),
      .min_o(),
      .max_o(max4)
  );
  node N2 (
      .A(max4),
      .B(p2_min3),
      .min_o(),
      .max_o(max5)
  );

  sorting_network SN4 (
      .S1 (p2_med1),
      .S2 (p2_med2),
      .S3 (p2_med3),
      .max(),
      .med(med5),
      .min()
  );
  node N3 (
      .A(p2_max1),
      .B(p2_max2),
      .min_o(min4),
      .max_o()
  );
  node N4 (
      .A(min4),
      .B(p2_max3),
      .min_o(min5),
      .max_o()
  );

  // Stage 3 pipeline
  always @(posedge clk) begin
    if (~rst_n) begin
      p3_min5   <= 0;
      p3_med5   <= 0;
      p3_max5   <= 0;
      p3_done_i <= 0;
    end else begin
      p3_min5   <= min5;
      p3_med5   <= med5;
      p3_max5   <= max5;
      p3_done_i <= p2_done_i;
    end
  end


  sorting_network SN5 (
      .S1 (p3_min5),
      .S2 (p3_med5),
      .S3 (p3_max5),
      .max(),
      .med(p3_median),
      .min()
  );

  reg [7:0] p4_median;
  reg       p4_done_i;
  always @(posedge clk) begin
    if (~rst_n) begin
      p4_median <= 0;
      p4_done_i <= 0;
    end else begin
      p4_median <= p3_median;
      p4_done_i <= p3_done_i;
    end
  end



  assign data_valid_o   = p4_done_i;
  assign median_o = p4_median;

endmodule