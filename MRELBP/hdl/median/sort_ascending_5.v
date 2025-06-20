module sort_ascending_5 (
    input clk,
    input rst_n,
    input [7:0] S1,
    S2,
    S3,
    S4,
    S5,
    output [7:0] min,
    out2,
    mid,
    out4,
    max
);
  wire [7:0] sn1_max, sn1_med, sn1_min;
  sorting_network SN1 (
      .S1 (S1),
      .S2 (S2),
      .S3 (S3),
      .max(sn1_max),
      .med(sn1_med),
      .min(sn1_min)
  );
  reg [7:0] p1_S4, p1_S5, p1_max, p1_med, p1_min;
  always @(posedge clk) begin
    if (~rst_n) begin
      p1_S4 <= 0;
      p1_S5 <= 0;
      p1_max <= 0;
      p1_min <= 0;
      p1_med <= 0;
    end else begin
      p1_S4 <= S4;
      p1_S5 <= S5;
      p1_max <= sn1_max;
      p1_min <= sn1_min;
      p1_med <= sn1_med;
    end
  end
  wire [7:0] sn2_max, sn2_med, sn2_min;
  sorting_network SN2 (
      .S1 (p1_max),
      .S2 (p1_S4),
      .S3 (p1_S5),
      .max(sn2_max),
      .med(sn2_med),
      .min(sn2_min)
  );
  reg [7:0] p2_max, p2_med, p2_min;
  reg [7:0] p2_med1, p2_min1;
  always @(posedge clk) begin
    if (~rst_n) begin
      p2_max <= 0;
      p2_min <= 0;
      p2_med <= 0;
      p2_med1 <= 0;
      p2_min1 <= 0;
    end else begin
      p2_med1 <= p1_med;
      p2_min1 <= p1_min;
      p2_max <= sn2_max;
      p2_min <= sn2_min;
      p2_med <= sn2_med;
    end
  end
  wire [7:0] sn3_max, sn3_med, sn3_min;
  sorting_network SN3 (
      .S1 (p2_med1),
      .S2 (p2_med),
      .S3 (p2_min),
      .max(sn3_max),
      .med(sn3_med),
      .min(sn3_min)
  );
  reg [7:0] p3_max, p3_min, p3_med;
  reg [7:0] p3_min1, p3_max_o;
  always @(posedge clk) begin
    if (~rst_n) begin
      p3_max <= 0;
      p3_min <= 0;
      p3_med <= 0;
      p3_min1 <= 0;
      p3_max_o <= 0;
    end else begin
      p3_max_o <= p2_max;
      p3_min1 <= p2_min1;
      p3_max <= sn3_max;
      p3_min <= sn3_min;
      p3_med <= sn3_med;
    end
  end
  wire [7:0] sn4_max, sn4_med, sn4_min;

  sorting_network SN4 (
      .S1 (p3_min1),
      .S2 (p3_med),
      .S3 (p3_min),
      .max(sn4_max),
      .med(sn4_med),
      .min(sn4_min)
  );



  assign min = sn4_min;
  assign out2 = sn4_med;
  assign mid = sn4_max;
  assign out4 = p3_max;
  assign max = p3_max_o;




endmodule