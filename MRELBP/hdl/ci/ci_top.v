module ci_top  (
    input clk,
    input rst_n,
    input [8:0] IMG_SIZE_I,
    input [7:0] m_3x3_i,
    input m_3x3_valid_i,

    output ci_r2_o,
    output ci_r2_valid_o,
    output ci_r2_finish_o,

    output ci_r4_o,
    output ci_r4_valid_o,
    output ci_r4_finish_o,

    output ci_r6_o,
    output ci_r6_valid_o,
    output ci_r6_finish_o
);
    wire [7:0] data0, data1, data2, data3, data4, data5, data6, data7;
    wire [7:0] data8, data9, data10, data11, data12;

    wire data0_valid, data1_valid, data2_valid, data3_valid, data4_valid, data5_valid;
    wire data6_valid, data7_valid, data8_valid, data9_valid, data10_valid, data11_valid, data12_valid; 
    wire r2_first, r4_first, r6_first;
    buffer_13 inst_buffer_13
        (
            .clk            (clk),
            .rst_n          (rst_n),
            .data_i         (m_3x3_i),
            .data_valid_i   (m_3x3_valid_i),
            .IMG_SIZE_I     (IMG_SIZE_I),
            .data0_o        (data0),
            .data0_valid_o  (data0_valid),
            .data1_o        (data1),
            .data1_valid_o  (data1_valid),
            .data2_o        (data2),
            .data2_valid_o  (data2_valid),
            .data3_o        (data3),
            .data3_valid_o  (data3_valid),
            .data4_o        (data4),
            .data4_valid_o  (data4_valid),
            .data5_o        (data5),
            .data5_valid_o  (data5_valid),
            .data6_o        (data6),
            .data6_valid_o  (data6_valid),
            .data7_o        (data7),
            .data7_valid_o  (data7_valid),
            .data8_o        (data8),
            .data8_valid_o  (data8_valid),
            .data9_o        (data9),
            .data9_valid_o  (data9_valid),
            .data10_o       (data10),
            .data10_valid_o (data10_valid),
            .data11_o       (data11),
            .data11_valid_o (data11_valid),
            .data12_o       (data12),
            .data12_valid_o (data12_valid),
            .r2_first_o    (r2_first),
            .r4_first_o    (r4_first),
            .r6_first_o    (r6_first)
        );


     ci_r2 inst_ci_r2
        (
            .clk          (clk),
            .rst_n        (rst_n),
            .start_i        (r2_first),
            .data_valid_i (data4_valid),
            .S1           (data0),
            .S2           (data1),
            .S3           (data2),
            .S4           (data3),
            .S5           (data4),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .ci_o         (ci_r2_o),
            .ci_valid_o   (ci_r2_valid_o),
            .finish_o     (ci_r2_finish_o)
        );
        ci_r4 inst_ci_r4
        (
            .clk          (clk),
            .rst_n        (rst_n),
            .data_valid_i (data8_valid),
            .IMG_SIZE_I  (IMG_SIZE_I),
            .start_i      (r4_first),
            .S1           (data0),
            .S2           (data1),
            .S3           (data2),
            .S4           (data3),
            .S5           (data4),
            .S6           (data5),
            .S7           (data6),
            .S8           (data7),
            .S9           (data8),
            .ci_o         (ci_r4_o),
            .ci_valid_o   (ci_r4_valid_o),
            .finish_o     (ci_r4_finish_o)
        );

    ci_r6 inst_ci_r6
        (
            .clk          (clk),
            .rst_n        (rst_n),
            .start_i      (r6_first),
            .data_valid_i (data12_valid),
            .IMG_SIZE_I   (IMG_SIZE_I),
            .S1           (data0),
            .S2           (data1),
            .S3           (data2),
            .S4           (data3),
            .S5           (data4),
            .S6           (data5),
            .S7           (data6),
            .S8           (data7),
            .S9           (data8),
            .S10          (data9),
            .S11          (data10),
            .S12          (data11),
            .S13          (data12),
            .ci_o         (ci_r6_o),
            .ci_valid_o   (ci_r6_valid_o),
            .finish_o     (ci_r6_finish_o)
        );





endmodule 
