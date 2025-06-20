module sorting_network (
    input  [7:0] S1,
    input  [7:0] S2,
    input  [7:0] S3,
    output [7:0] max,
    output [7:0] med,
    output [7:0] min
);

  wire [7:0] max1, min1;
  wire [7:0] min2;


  // nodes
  node N1 (
      .A(S1),
      .B(S2),
      .min_o(min1),
      .max_o(max1)
  );
  node N2 (
      .A(max1),
      .B(S3),
      .min_o(min2),
      .max_o(max)
  );

  node N3 (
      .A(min1),
      .B(min2),
      .min_o(min),
      .max_o(med)
  );




endmodule