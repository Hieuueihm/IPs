module mrelbp (
    input  wire         clk,
    input  wire         rst_n,
    input [1:0] control_reg_i,
    input [0:0] config_reg_i,
    //slave 
    input [7:0] s_axis_tdata,
    input s_axis_tvalid,
    output wire  s_axis_tready,
    // master
    output wire [31:0]  m_axis_tdata,
    output wire         m_axis_tvalid,
    input  wire         m_axis_tready,

    output irq_o
    
);
    wire [31:0] cinird_r6;
    wire cinird_r6_data_valid;
    wire cinird_r6_joint_finish;
    wire cinird_r6_read_finish;
    wire read_r6_en;
    wire [31:0] cinird_r2;
    wire cinird_r2_data_valid;
    wire cinird_r2_joint_finish;
    wire cinird_r2_read_finish;
    wire read_r2_en;
    wire [31:0] cinird_r4;
    wire cinird_r4_data_valid;
    wire cinird_r4_joint_finish;
    wire cinird_r4_read_finish;
    wire read_r4_en;
    localparam IP_IDLE = 2'b00,
            IP_ACTIVE = 2'b01,
            IP_FINISH = 2'b10;
    reg [1:0] current_state, next_state;

    wire start = control_reg_i[0];
   

    always @(posedge clk) begin
        if(~rst_n) begin
            current_state <= IP_IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    always @(*) begin
        next_state = current_state;
        case (current_state)
            IP_IDLE: next_state = start ? IP_ACTIVE : IP_IDLE;
            IP_ACTIVE: next_state = cinird_r6_read_finish ? IP_FINISH: IP_ACTIVE;
            IP_FINISH: next_state = IP_IDLE;
            default : next_state = IP_FINISH;
        endcase


    end
    reg s_axis_ready;
    reg irq_r;
    always @(*) begin
        s_axis_ready = 0;
        irq_r = 0;
        case (current_state)
                IP_IDLE: begin 
                end
                IP_ACTIVE: s_axis_ready = 1'b1;
                IP_FINISH: irq_r = 1'b1;
            default : begin
                    s_axis_ready = 0;
                    irq_r = 0;
            end
        endcase
    end
    reg s_axis_tready_d;
    reg irq_d;
    always @(posedge clk) begin 
        if(~rst_n) begin
            s_axis_tready_d <= 0;
            irq_d <= 0;
        end else begin
            s_axis_tready_d <= s_axis_ready;
            irq_d <= irq_r;
        end
    end

    assign s_axis_tready = s_axis_tready_d;
    assign irq_o = irq_d;



    reg [8:0] IMG_SIZE_R;
    wire [8:0] IMG_SIZE;
    always @(posedge clk) begin 
        if(~rst_n) begin
            IMG_SIZE_R <= 0;
        end else begin
            IMG_SIZE_R <= IMG_SIZE;

        end
    end

    assign IMG_SIZE = (config_reg_i[0]) ? 9'd256 : 9'd128;


    wire [7:0] data_root, m_3x3, m_5x5, m_7x7;
    wire data_root_valid, m_3x3_valid, m_5x5_valid, m_7x7_valid;
    median_filter inst_median_filter
        (
            .clk               (clk),
            .rst_n             (rst_n),
            .s_axis_tdata      (s_axis_tdata),
            .s_axis_tvalid     (s_axis_tvalid),
            .s_axis_tready     (s_axis_tready),
            .IMG_SIZE_I        (IMG_SIZE_R),
            .data_root_o       (data_root),
            .data_root_valid_o (data_root_valid),
            .m_3x3_o           (m_3x3),
            .m_3x3_valid_o     (m_3x3_valid),
            .m_5x5_o           (m_5x5),
            .m_5x5_valid_o     (m_5x5_valid),
            .m_7x7_o           (m_7x7),
            .m_7x7_valid_o     (m_7x7_valid)
        );
    wire ci_r2;
    wire ci_r2_valid;
    wire ci_r2_finish;
    wire ci_r4;
    wire ci_r4_valid;
    wire ci_r4_finish;
    wire ci_r6;
    wire ci_r6_valid;
    wire ci_r6_finish;
    ci_top inst_ci_top
        (
            .clk            (clk),
            .rst_n          (rst_n),
            .IMG_SIZE_I     (IMG_SIZE_R),
            .m_3x3_i        (m_3x3),
            .m_3x3_valid_i  (m_3x3_valid),
            .ci_r2_o        (ci_r2),
            .ci_r2_valid_o  (ci_r2_valid),
            .ci_r2_finish_o (ci_r2_finish),
            .ci_r4_o        (ci_r4),
            .ci_r4_valid_o  (ci_r4_valid),
            .ci_r4_finish_o (ci_r4_finish),
            .ci_r6_o       (ci_r6),
            .ci_r6_valid_o (ci_r6_valid),
            .ci_r6_finish_o  (ci_r6_finish)

        );
        wire [3:0] r2_ni;
        wire [3:0] r2_rd;
        wire r2_data_valid;
        wire r2_finish;
    r2_nird inst_r2_nird
        (
            .clk               (clk),
            .rst_n             (rst_n),
            .m_3x3_i           (m_3x3),
            .m_3x3_valid_i     (m_3x3_valid),
            .IMG_SIZE_I        (IMG_SIZE_R),
            .data_root_i       (data_root),
            .data_root_valid_i (data_root_valid),
            .ni_o              (r2_ni),
            .rd_o              (r2_rd),
            .data_valid_o      (r2_data_valid),
            .finish_o          (r2_finish)
        );
        wire [3:0] r4_ni;
        wire [3:0] r4_rd;
        wire r4_data_valid;
        wire r4_finish;

        r4_nird inst_r4_nird
        (
            .clk           (clk),
            .rst_n         (rst_n),
            .IMG_SIZE_I    (IMG_SIZE_R),
            .m_3x3_i       (m_3x3),
            .m_3x3_valid_i (m_3x3_valid),
            .m_5x5_i       (m_5x5),
            .m_5x5_valid_i (m_5x5_valid),
            .ni_o          (r4_ni),
            .rd_o          (r4_rd),
            .data_valid_o  (r4_data_valid),
            .finish_o      (r4_finish)
        );
        wire [3:0] r6_ni;
        wire [3:0] r6_rd;
        wire r6_data_valid;
        wire r6_finish;

        r6_nird inst_r6_nird
        (
            .clk           (clk),
            .rst_n         (rst_n),
            .m_5x5_i       (m_5x5),
            .m_5x5_valid_i (m_5x5_valid),
            .m_7x7_i       (m_7x7),
            .m_7x7_valid_i (m_7x7_valid),
            .IMG_SIZE_I    (IMG_SIZE_R),
            .ni_o          (r6_ni),
            .rd_o          (r6_rd),
            .data_valid_o  (r6_data_valid),
            .finish_o      (r6_finish)
        );

    `define CYCLE_SHIFT_CI_r2 7
    wire ci_r2_d, ci_r4_d, ci_r6_d;
    wire ci_r2_valid_d, ci_r4_valid_d, ci_r6_valid_d;
    shift_registers #(
        .WIDTH(1),
        .CYCLE(8)
    ) inst_shift_cir2 (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(ci_r2),
        .data_o(ci_r2_d)
    );
    shift_registers #(
        .WIDTH(1),
        .CYCLE(8)
    ) inst_shift_cir2v (
        .clk(clk),
        .rst_n(rst_n),
        .data_i(ci_r2_valid),
        .data_o(ci_r2_valid_d)
    );
    shift_registers #(
      .WIDTH(1),
      .CYCLE(18)
      ) inst_shift_cir4 (
          .clk(clk),
          .rst_n(rst_n),
          .data_i(ci_r4),
          .data_o(ci_r4_d)
      );
    shift_registers #(
      .WIDTH(1),
      .CYCLE(18)
      ) inst_shift_cir4v (
          .clk(clk),
          .rst_n(rst_n),
          .data_i(ci_r4_valid),
          .data_o(ci_r4_valid_d)
      );
    shift_registers #(
      .WIDTH(1),
      .CYCLE(40)
    ) inst_shift_cir6 (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(ci_r6),
      .data_o(ci_r6_d)
    );
    shift_registers #(
      .WIDTH(1),
      .CYCLE(40)
    ) inst_shift_cir6v (
      .clk(clk),
      .rst_n(rst_n),
      .data_i(ci_r6_valid),
      .data_o(ci_r6_valid_d)
    );

    localparam READ_IDLE = 2'b00,   
                READ_R2 = 2'b01,
                READ_R4 = 2'b10,
                READ_R6 = 2'b11;


    reg [1:0] jh_current_state, jh_next_state;

    always @(posedge clk) begin 
        if(~rst_n) begin
            jh_current_state <= 0;
        end else begin
            jh_current_state <= jh_next_state;
        end
    end

    always @(*) begin 
        jh_next_state = jh_current_state;
        case(jh_current_state) 
            READ_IDLE: jh_next_state = (cinird_r2_joint_finish) ? READ_R2: READ_IDLE;
            READ_R2 : jh_next_state = (cinird_r2_read_finish) ? READ_R4 : READ_R2;
            READ_R4: jh_next_state= (cinird_r4_read_finish) ? READ_R6 : READ_R4;
            READ_R6: jh_next_state = (cinird_r6_read_finish) ? READ_IDLE: READ_R6;

            default: jh_next_state = READ_IDLE;

        endcase
            
    end
    reg read_r2_r, read_r4_r, read_r6_r;
    always @(*) begin 
        read_r2_r = 1'b0;
        read_r4_r = 1'b0;
        read_r6_r = 1'b0;
        case(jh_current_state) 
            READ_R2: begin
                read_r2_r = 1'b1;
            end
            READ_R4: begin
                read_r4_r = 1'b1;
            end
            READ_R6: begin
                read_r6_r = 1'b1;
            end
            default: begin

                read_r2_r = 1'b0;
                read_r4_r = 1'b0;
                read_r6_r = 1'b0;
            end
        endcase
            
    end



 
    assign read_r2_en = read_r2_r & m_axis_tready;

    joint_histogram inst_joint_histogram_r2
        (
            .clk            (clk),
            .rst_n          (rst_n),
            .ci_i           (ci_r2_d),
            .ni_i           (r2_ni),
            .rd_i           (r2_rd),
            .data_valid_i   (r2_data_valid),
            .finish_i       (r2_finish),
            .read_data_en_i (read_r2_en),
            .data_o         (cinird_r2),
            .data_valid_o   (cinird_r2_data_valid),
            .finish_joint_o      (cinird_r2_joint_finish),
            .finish_read_o (cinird_r2_read_finish)
        );

  
    assign read_r4_en = read_r4_r & m_axis_tready ;
    joint_histogram inst_joint_histogram_r4
        (
            .clk            (clk),
            .rst_n          (rst_n),
            .ci_i           (ci_r4_d),
            .ni_i           (r4_ni),
            .rd_i           (r4_rd),
            .data_valid_i   (r4_data_valid),
            .finish_i       (r4_finish),
            .read_data_en_i (read_r4_en),
            .data_o         (cinird_r4),
            .data_valid_o   (cinird_r4_data_valid),
            .finish_joint_o      (cinird_r4_joint_finish),
            .finish_read_o (cinird_r4_read_finish)
        );

 
    assign read_r6_en = read_r6_r & m_axis_tready;
    joint_histogram inst_joint_histogram_r6
        (
            .clk            (clk),
            .rst_n          (rst_n),
            .ci_i           (ci_r6_d),
            .ni_i           (r6_ni),
            .rd_i           (r6_rd),
            .data_valid_i   (r6_data_valid),
            .finish_i       (r6_finish),
            .read_data_en_i (read_r6_en),
            .data_o         (cinird_r6),
            .data_valid_o   (cinird_r6_data_valid),
            .finish_joint_o      (cinird_r6_joint_finish),
            .finish_read_o (cinird_r6_read_finish)
        );

    wire [31:0] tdata;
    reg [31:0] tdata_d;
    assign tdata = (read_r2_r) ? cinird_r2 : (read_r4_r) ? cinird_r4 : (read_r6_r) ? cinird_r6 : 32'd0;
    always @(posedge clk) begin 
        if(~rst_n) begin
            tdata_d <= 0;
        end else begin
            tdata_d <= tdata;
        end
    end
    assign m_axis_tdata = tdata_d;


    wire tvalid;
    reg tvalid_d;
    assign tvalid = (read_r2_r) ? cinird_r2_data_valid : (read_r4_r) ? cinird_r4_data_valid : (read_r6_r) ? cinird_r6_data_valid : 1'd0;

    always @(posedge clk) begin 
        if(~rst_n) begin
            tvalid_d <= 0;
        end else begin
            tvalid_d <= tvalid;
        end
    end
    assign m_axis_tvalid = tvalid_d;


endmodule