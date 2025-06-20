module r2_nird (
    input clk,
    input rst_n,
    input [7:0] m_3x3_i,
    input m_3x3_valid_i,
    input [8:0] IMG_SIZE_I,
    input [7:0] data_root_i,
    input data_root_valid_i,
    output [3:0] ni_o,
    output [3:0] rd_o,
    output data_valid_o,
    output finish_o
);
  reg [8:0] IMG_SIZE;
  always @(posedge clk) begin
        if(~rst_n) begin
            IMG_SIZE <= 0;
        end else begin
            IMG_SIZE <= IMG_SIZE_I;
        end
    end
  wire [7:0] m3x3_data0, m3x3_data1, m3x3_data2, m3x3_data3, m3x3_data4;
  wire m3x3_data0_valid, m3x3_data1_valid, m3x3_data2_valid, m3x3_data3_valid, m3x3_data4_valid;
  wire m3x3_first;
  buffer_5 inst_buffer_5_m3x3
		(
			.clk           (clk),
			.rst_n         (rst_n),
			.data_valid_i  (m_3x3_valid_i),
			.data_i        (m_3x3_i),
			.IMG_SIZE_I    (IMG_SIZE),
			.data0_o       (m3x3_data0),
			.data1_o       (m3x3_data1),
			.data2_o       (m3x3_data2),
			.data3_o       (m3x3_data3),
			.data4_o       (m3x3_data4),
			.data0_valid_o (m3x3_data0_valid),
			.data1_valid_o (m3x3_data1_valid),
			.data2_valid_o (m3x3_data2_valid),
			.data3_valid_o (m3x3_data3_valid),
			.data4_valid_o (m3x3_data4_valid),
      .tfirst_o(m3x3_first)
	);
	assign m3x3_buffer_data_valid = m3x3_data4_valid;

	wire [7:0] data0_root, data1_root, data2_root, data3_root, data4_root;
	wire data0_root_valid, data1_root_valid, data2_root_valid, data3_root_valid,data4_root_valid;
	// delay data_root_i 7 cycle (after)
  wire data_root_start;
  wire data_root_valid_d;
  wire [7:0] data_root_d;
  `define DONE_ORIGINAL_DELAY 7
  shift_registers #(
        .WIDTH(1),
        .CYCLE(`DONE_ORIGINAL_DELAY)
    ) SHIFT_7_DATA_VALID_I (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(data_root_valid_i),
        .data_o(data_root_valid_d)
    );
      shift_registers #(
        .WIDTH(8),
        .CYCLE(`DONE_ORIGINAL_DELAY)
    ) SHIFT_5_DATA0 (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(data_root_i),
        .data_o(data_root_d)
    );
 	buffer_5 inst_buffer_5_root
		(
			.clk           (clk),
			.rst_n         (rst_n),
			.data_valid_i  (data_root_valid_d),
			.data_i        (data_root_d),
			.IMG_SIZE_I    (IMG_SIZE),
			.data0_o       (data0_root),
			.data1_o       (data1_root),
			.data2_o       (data2_root),
			.data3_o       (data3_root),
			.data4_o       (data4_root),
			.data0_valid_o (data0_root_valid),
			.data1_valid_o (data1_root_valid),
			.data2_valid_o (data2_root_valid),
			.data3_valid_o (data3_root_valid),
			.data4_valid_o (data4_root_valid),
      .tfirst_o(data_root_start)
	);
  assign root_buffer_data_valid = data4_root_valid;




  wire [7:0] S1_5x5, S2_5x5, S3_5x5, S4_5x5, S5_5x5, S6_5x5, S7_5x5, S8_5x5;
  wire [7:0] S9_5x5, S10_5x5, S11_5x5, S12_5x5, S13_5x5;
  wire [7:0] S14_5x5, S15_5x5, S16_5x5, S17_5x5, S18_5x5,S19_5x5;
  wire [7:0] S20_5x5, S21_5x5, S22_5x5, S23_5x5, S24_5x5, S25_5x5;
  wire window_buffer_5x5_data_valid;
  wire window_buffer_5x5_finish;



  window_buffer_5x5 inst_window_buffer_5x5 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(m3x3_buffer_data_valid),
      .start_i     (m3x3_first),
      .S1_i(m3x3_data4),
      .S2_i(m3x3_data3),
      .S3_i(m3x3_data2),
      .S4_i(m3x3_data1),
      .S5_i(m3x3_data0),
      .IMG_SIZE_I  (IMG_SIZE),
      .S1_o(S1_5x5),
      .S2_o(S2_5x5),
      .S3_o(S3_5x5),
      .S4_o(S4_5x5),
      .S5_o(S5_5x5),
      .S6_o(S6_5x5),
      .S7_o(S7_5x5),
      .S8_o(S8_5x5),
      .S9_o(S9_5x5),
      .S10_o(S10_5x5),
      .S11_o(S11_5x5),
      .S12_o(S12_5x5),
      .S13_o(S13_5x5),
      .S14_o(S14_5x5),
      .S15_o(S15_5x5),
      .S16_o(S16_5x5),
      .S17_o(S17_5x5),
      .S18_o(S18_5x5),
      .S19_o(S19_5x5),
      .S20_o(S20_5x5),
      .S21_o(S21_5x5),
      .S22_o(S22_5x5),
      .S23_o(S23_5x5),
      .S24_o(S24_5x5),
      .S25_o(S25_5x5),
      .data_valid_o(window_buffer_5x5_data_valid),
      .finish_o(window_buffer_5x5_finish)
  );


  wire [7:0] S1_3x3, S2_3x3, S3_3x3, S4_3x3, S5_3x3, S6_3x3, S7_3x3, S8_3x3, S9_3x3;
  wire window_3x3_data_valid;
  wire window_3x3_finish;
  window_buffer_3x3  inst_window_buffer_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(root_buffer_data_valid),
      .S1_i        (data3_root),
      .S2_i        (data2_root),
      .S3_i        (data1_root),
      .start_i     (data_root_start),
      .IMG_SIZE_I  (IMG_SIZE),
      .S1_o(S1_3x3),
      .S2_o(S2_3x3),
      .S3_o(S3_3x3),
      .S4_o(S4_3x3),
      .S5_o(S5_3x3),
      .S6_o(S6_3x3),
      .S7_o(S7_3x3),
      .S8_o(S8_3x3),
      .S9_o(S9_3x3),
      .data_valid_o(window_3x3_data_valid),
      .finish_o(window_3x3_finish)
  );


  wire [23:0] S1_r1, S2_r1, S3_r1, S4_r1, S5_r1, S6_r1, S7_r1, S8_r1;
  wire r1_interpolation_valid;
  wire r1_interpolation_finish;
  wire [7:0] S6_3x3_q, S2_3x3_q, S4_3x3_q, S8_3x3_q, S3_3x3_q, S1_3x3_q, S7_3x3_q, S9_3x3_q;
  wire wdbf_5x5_finish_d;
  wire wdbf_5x5_data_valid_d;

  register #(
      .WIDTH(8)
  ) register_S6_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S6_3x3),
      .Q(S6_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S2_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S2_3x3),
      .Q(S2_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S4_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S4_3x3),
      .Q(S4_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S8_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S8_3x3),
      .Q(S8_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S3_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S3_3x3),
      .Q(S3_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S1_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S1_3x3),
      .Q(S1_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S7_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S7_3x3),
      .Q(S7_3x3_q)
  );
  register #(
      .WIDTH(8)
  ) register_S9_3x3 (
      .clk(clk),
      .rst_n(rst_n),
      .D(S9_3x3),
      .Q(S9_3x3_q)
  );

  register #(
      .WIDTH(1)
  ) register_WDBF_5x5_PD (
      .clk(clk),
      .rst_n(rst_n),
      .D(window_buffer_5x5_finish),
      .Q(wdbf_5x5_finish_d)
  );
  register #(
      .WIDTH(1)
  ) register_WDBF_5x5_DONE (
      .clk(clk),
      .rst_n(rst_n),
      .D(window_buffer_5x5_data_valid),
      .Q(wdbf_5x5_data_valid_d)
  );


  interpolation_R_x #(
      .R(1)
  ) INTERPOLATION_R_1 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(wdbf_5x5_finish_d),
      .data_valid_i(wdbf_5x5_data_valid_d),
      .S_0_i(S6_3x3_q),
      .S_90_i(S2_3x3_q),
      .S_180_i(S4_3x3_q),
      .S_270_i(S8_3x3_q),
      .S_45_i_1(S3_3x3_q),
      .S_45_i_2(),
      .S_45_i_3(),
      .S_45_i_4(),
      .S_135_i_1(S1_3x3_q),
      .S_135_i_2(),
      .S_135_i_3(),
      .S_135_i_4(),
      .S_225_i_1(S7_3x3_q),
      .S_225_i_2(),
      .S_225_i_3(),
      .S_225_i_4(),
      .S_315_i_1(S9_3x3_q),
      .S_315_i_2(),
      .S_315_i_3(),
      .S_315_i_4(),
      .S1_o(S1_r1),
      .S2_o(S2_r1),
      .S3_o(S3_r1),
      .S4_o(S4_r1),
      .S5_o(S5_r1),
      .S6_o(S6_r1),
      .S7_o(S7_r1),
      .S8_o(S8_r1),
      .data_valid_o(r1_interpolation_valid),
      .finish_o(r1_interpolation_finish)
  );

  wire [23:0] S1_r2, S2_r2, S3_r2, S4_r2, S5_r2, S6_r2, S7_r2, S8_r2;
  wire r2_inter_valid;
  wire r2_inter_finish;

  interpolation_R_x #(
      .R(2)
  ) INTERPOLATION_R_2 (
      .clk(clk),
      .rst_n(rst_n),
      .finish_i(window_buffer_5x5_finish),
      .data_valid_i(window_buffer_5x5_data_valid),
      .S_0_i(S15_5x5),
      .S_90_i(S3_5x5),
      .S_180_i(S11_5x5),
      .S_270_i(S23_5x5),
      .S_45_i_1(S4_5x5),
      .S_45_i_2(S5_5x5),
      .S_45_i_3(S9_5x5),
      .S_45_i_4(S10_5x5),
      .S_135_i_1(S1_5x5),
      .S_135_i_2(S2_5x5),
      .S_135_i_3(S6_5x5),
      .S_135_i_4(S7_5x5),
      .S_225_i_1(S16_5x5),
      .S_225_i_2(S17_5x5),
      .S_225_i_3(S21_5x5),
      .S_225_i_4(S22_5x5),
      .S_315_i_1(S19_5x5),
      .S_315_i_2(S20_5x5),
      .S_315_i_3(S24_5x5),
      .S_315_i_4(S25_5x5),
      .S1_o(S1_r2),
      .S2_o(S2_r2),
      .S3_o(S3_r2),
      .S4_o(S4_r2),
      .S5_o(S5_r2),
      .S6_o(S6_r2),
      .S7_o(S7_r2),
      .S8_o(S8_r2),
      .data_valid_o(r2_inter_valid),
      .finish_o(r2_inter_finish)
  );


  wire [12:0] patch_sum;
  wire r2_patch_sum_data_valid;
  wire r2_patch_sum_finish;

    r2_patch_sum inst_r2_patch_sum
    (
      .clk          (clk),
      .rst_n        (rst_n),
      .data_valid_i (m3x3_buffer_data_valid),
      .start_i     (m3x3_first),
      .S1           (m3x3_data0),
      .S2           (m3x3_data1),
      .S3           (m3x3_data2),
      .S4           (m3x3_data3),
      .S5           (m3x3_data4),
      .IMG_SIZE_I   (IMG_SIZE),
      .sum_o        (patch_sum),
      .data_valid_o (r2_patch_sum_data_valid),
      .finish_o     (r2_patch_sum_finish)
    );

  
  wire [12:0] patch_sum_delay;
  register #(
      .WIDTH(13)
  ) register_SUM_O_PATCH_SUM (
      .clk(clk),
      .rst_n(rst_n),
      .D(patch_sum),
      .Q(patch_sum_delay)
  );

  wire ni_r2_data_valid, ni_r2_finish;
  wire bit1_ni, bit2_ni, bit3_ni, bit4_ni, bit5_ni, bit6_ni, bit7_ni, bit8_ni;
  ni #(
      .WIDTH(13),
      .GAIN (25)
  ) ni_CALC_r2 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r2_inter_valid),
      .finish_i(r2_inter_finish),
      .S1_r2(S1_r2),
      .S2_r2(S2_r2),
      .S3_r2(S3_r2),
      .S4_r2(S4_r2),
      .S5_r2(S5_r2),
      .S6_r2(S6_r2),
      .S7_r2(S7_r2),
      .S8_r2(S8_r2),
      .sum_i(patch_sum_delay),
      .data_valid_o(ni_r2_data_valid),
      .finish_o(ni_r2_finish),
      .bit1_o(bit1_ni),
      .bit2_o(bit2_ni),
      .bit3_o(bit3_ni),
      .bit4_o(bit4_ni),
      .bit5_o(bit5_ni),
      .bit6_o(bit6_ni),
      .bit7_o(bit7_ni),
      .bit8_o(bit8_ni)
  );

  wire rd_r2_data_valid, rd_r2_finish;
  wire bit1_rd, bit2_rd, bit3_rd, bit4_rd, bit5_rd, bit6_rd, bit7_rd, bit8_rd;
  rd rd_CALC_r2 (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(r2_inter_valid),
      .finish_i(r2_inter_finish),
      .S1_r2(S1_r2),
      .S2_r2(S2_r2),
      .S3_r2(S3_r2),
      .S4_r2(S4_r2),
      .S5_r2(S5_r2),
      .S6_r2(S6_r2),
      .S7_r2(S7_r2),
      .S8_r2(S8_r2),
      .S1_r1(S1_r1),
      .S2_r1(S2_r1),
      .S3_r1(S3_r1),
      .S4_r1(S4_r1),
      .S5_r1(S5_r1),
      .S6_r1(S6_r1),
      .S7_r1(S7_r1),
      .S8_r1(S8_r1),
      .data_valid_o(rd_r2_data_valid),
      .finish_o(rd_r2_finish),
      .bit1_o(bit1_rd),
      .bit2_o(bit2_rd),
      .bit3_o(bit3_rd),
      .bit4_o(bit4_rd),
      .bit5_o(bit5_rd),
      .bit6_o(bit6_rd),
      .bit7_o(bit7_rd),
      .bit8_o(bit8_rd)
  );


  wire [3:0] rd;

  riu2_mapping RIU2_rd (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(rd_r2_data_valid),
      .finish_i(rd_r2_finish),
      .bit1_i(bit1_rd),
      .bit2_i(bit2_rd),
      .bit3_i(bit3_rd),
      .bit4_i(bit4_rd),
      .bit5_i(bit5_rd),
      .bit6_i(bit6_rd),
      .bit7_i(bit7_rd),
      .bit8_i(bit8_rd),
      .data_o(rd),
      .data_valid_o(),
      .finish_o()
  );
  shift_registers #(
      .WIDTH(4),
      .CYCLE(3)
  ) shift_rd_output (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(rd),
      .data_o(rd_o)
  );
  riu2_mapping RIU2_ni (
      .clk(clk),
      .rst_n(rst_n),
      .data_valid_i(ni_r2_data_valid),
      .finish_i(ni_r2_finish),
      .bit1_i(bit1_ni),
      .bit2_i(bit2_ni),
      .bit3_i(bit3_ni),
      .bit4_i(bit4_ni),
      .bit5_i(bit5_ni),
      .bit6_i(bit6_ni),
      .bit7_i(bit7_ni),
      .bit8_i(bit8_ni),
      .data_o(ni_o),
      .data_valid_o(data_valid_o),
      .finish_o(finish_o)
  );


endmodule