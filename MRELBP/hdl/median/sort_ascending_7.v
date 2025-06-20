module sort_ascending_7 (
    input clk,
    input rst_n,
    input [7:0] S1,
    S2,
    S3,
    S4,
    S5,
    S6,
    S7,
    output [7:0] min,
    out2,
    out3,
    mid,
    out5,
    out6,
    max
);
  // a b c d e f g
  // S1 S2 S3 S4 S5 S6 S7

  // sort 5 first values S1 S2 S3 S4 S5
  wire [7:0] sa1_min, sa1_out2, sa1_mid, sa1_max, sa1_out4;
  // 3
 
  sort_ascending_5 SA1 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(S1),
      .S2(S2),
      .S3(S3),
      .S4(S4),
      .S5(S5),
      .min(sa1_min),
      .out2(sa1_out2),
      .mid(sa1_mid),
      .out4(sa1_out4),
      .max(sa1_max)
  );


  reg [7:0] p1_S6, p1_S7;
  reg [7:0] p2_S6, p2_S7;
  reg [7:0] p3_S6, p3_S7;
  reg [7:0] p4_S6, p4_S7;


  reg [7:0] p1_sa1_min, p1_sa1_out2, p1_sa1_mid, p1_sa1_max, p1_sa1_out4;
  reg [7:0] p1_sa1_min_1, p1_sa1_out2_1;
  reg [7:0] p1_sa1_min_2, p1_sa1_out2_2;
  reg [7:0] p1_sa1_min_3, p1_sa1_out2_3;

//4
  always @(posedge clk) begin
    if (~rst_n) begin
      p1_S6 <= 0;
      p1_S7 <= 0;
      p1_sa1_min <= 0;
      p1_sa1_out2 <= 0;
      p1_sa1_mid <= 0;
      p1_sa1_max <= 0;
      p1_sa1_out4 <= 0;
    end else begin
      p1_S6 <= S6;
      p1_S7 <= S7;
      p1_sa1_min <= sa1_min;
      p1_sa1_out2 <= sa1_out2;
      p1_sa1_mid <= sa1_mid;
      p1_sa1_max <= sa1_max;
      p1_sa1_out4 <= sa1_out4;
    end
  end
  always @(posedge clk) begin
    if (~rst_n) begin
      p2_S6 <= 0;
      p2_S7 <= 0;
    end else begin
      p2_S6 <= p1_S6;
      p2_S7 <= p1_S7;
    end
  end
  always @(posedge clk) begin
    if (~rst_n) begin
      p3_S6 <= 0;
      p3_S7 <= 0;
    end else begin
      p3_S6 <= p2_S6;
      p3_S7 <= p2_S7;
    end
  end
  always @(posedge clk) begin
    if (~rst_n) begin
      p4_S6 <= 0;
      p4_S7 <= 0;
    end else begin
      p4_S6 <= p3_S6;
      p4_S7 <= p3_S7;
    end
  end

  always @(posedge clk) begin
    if (~rst_n) begin
      p1_sa1_min_1  <= 0;
      p1_sa1_out2_1 <= 0;

      p1_sa1_min_2  <= 0;
      p1_sa1_out2_2 <= 0;

      p1_sa1_min_3  <= 0;
      p1_sa1_out2_3 <= 0;


    end else begin
      p1_sa1_min_1  <= p1_sa1_min;
      p1_sa1_out2_1 <= p1_sa1_out2;

      p1_sa1_min_2  <= p1_sa1_min_1;
      p1_sa1_out2_2 <= p1_sa1_out2_1;

      p1_sa1_min_3  <= p1_sa1_min_2;
      p1_sa1_out2_3 <= p1_sa1_out2_2;


    end
  end
  wire [7:0] sa2_min, sa2_out2, sa2_mid, sa2_max, sa2_out4;
  // sort 5 last values S5 S6 sa1_max, sa1_out4, sa1_mid
  // 7
  sort_ascending_5 SA2 (
      .clk(clk),
      .rst_n(rst_n),
      .S1(p4_S6),
      .S2(p4_S7),
      .S3(p1_sa1_max),
      .S4(p1_sa1_out4),
      .S5(p1_sa1_mid),
      .min(sa2_min),
      .out2(sa2_out2),
      .mid(sa2_mid),
      .out4(sa2_out4),
      .max(sa2_max)
  );


  reg [7:0] p2_sa2_min, p2_sa2_out2, p2_sa2_mid, p2_sa2_out4, p2_sa2_max;
  reg [7:0] p2_sa1_min, p2_sa1_out2;
  // 8
  always @(posedge clk) begin
    if (~rst_n) begin
      p2_sa1_min  <= 0;
      p2_sa1_out2 <= 0;
      p2_sa2_min  <= 0;
      p2_sa2_out2 <= 0;
      p2_sa2_mid  <= 0;
      p2_sa2_max  <= 0;
      p2_sa2_out4 <= 0;
    end else begin
      p2_sa1_min  <= p1_sa1_min_3;
      p2_sa1_out2 <= p1_sa1_out2_3;
      p2_sa2_min  <= sa2_min;
      p2_sa2_out2 <= sa2_out2;
      p2_sa2_mid  <= sa2_mid;
      p2_sa2_max  <= sa2_max;
      p2_sa2_out4 <= sa2_out4;
    end
  end


  wire [7:0] sn1_max, sn1_med, sn1_min;
  sorting_network SN1 (
      .S1 (p2_sa1_min),
      .S2 (p2_sa1_out2),
      .S3 (p2_sa2_min),
      .max(sn1_max),
      .med(sn1_med),
      .min(sn1_min)
  );

  reg [7:0] p3_sn1_max, p3_sn1_med, p3_sn1_min;
  reg [7:0] p3_sa2_out2, p3_sa2_mid, p3_sa2_out4, p3_sa2_max;
// 9
  always @(posedge clk) begin
    if (~rst_n) begin
      p3_sn1_max  <= 0;
      p3_sn1_med  <= 0;
      p3_sn1_min  <= 0;
      p3_sa2_out2 <= 0;
      p3_sa2_mid  <= 0;
      p3_sa2_out4 <= 0;
      p3_sa2_max  <= 0;
    end else begin
      p3_sn1_max  <= sn1_max;
      p3_sn1_med  <= sn1_med;
      p3_sn1_min  <= sn1_min;
      p3_sa2_out2 <= p2_sa2_out2;
      p3_sa2_mid  <= p2_sa2_mid;
      p3_sa2_out4 <= p2_sa2_out4;
      p3_sa2_max  <= p2_sa2_max;
    end
  end


  wire [7:0] sn2_max, sn2_med, sn2_min;


  sorting_network SN2 (
      .S1 (p3_sn1_med),
      .S2 (p3_sn1_max),
      .S3 (p3_sa2_out2),
      .max(sn2_max),
      .med(sn2_med),
      .min(sn2_min)
  );

  // reg [7:0] p4_sn2_max, p4_sn2_med, p4_sn2_min;
  // reg p4_done_o;
  // reg [7:0] p4_sa2_mid, p4_sa2_out4, p4_sa2_max;
  // reg [7:0] p4_sn1_min;

  // always @(posedge clk) begin
  //   if (~rst_n) begin
  //     p4_sn2_max  <= 0;
  //     p4_sn2_med  <= 0;
  //     p4_sn2_min  <= 0;
  //     p4_done_o   <= 0;
  //     p4_sa2_mid  <= 0;
  //     p4_sa2_out4 <= 0;
  //     p4_sa2_max  <= 0;
  //     p4_sn1_min  <= 0;
  //   end else begin
  //     p4_sn2_max  <= sn2_max;
  //     p4_sn2_med  <= sn2_med;
  //     p4_sn2_min  <= sn2_min;

  //     p4_done_o   <= p3_done_o;
  //     p4_sa2_mid  <= p3_sa2_mid;
  //     p4_sa2_out4 <= p3_sa2_out4;
  //     p4_sa2_max  <= p3_sa2_max;
  //     p4_sn1_min  <= p3_sn1_min;

  //   end
  // end

  // sorting_network SN3 (
  //     .S1 (p4_sn1_min),
  //     .S2 (p4_sn2_med),
  //     .S3 (p4_sn2_min),
  //     .max(out3),
  //     .med(out2),
  //     .min(min)
  // );
  // assign mid = p4_sn2_max;
  // assign out5 = p4_sa2_mid;
  // assign out6 = p4_sa2_out4;
  // assign max = p4_sa2_max;
  // assign done_o = p4_done_o;

  // sn2_max -> mid
  // sa2_mid -> out5
  // sa2_out4 -> out6
  // sa2_max -> max


  assign min = p3_sn1_min;
  assign out2 = sn2_min;
  assign out3 = sn2_med;

  assign mid = sn2_max;
  assign out5 = p3_sa2_mid;
  assign out6 = p3_sa2_out4;
  assign max = p3_sa2_max;


endmodule