module axi4_lite (
    input  wire                  clk,
    input  wire                  rst_n,
 
    // Write Address Channel
    input  wire [31:0] s_axi_awaddr,
    input  wire                  s_axi_awvalid,
    output reg                   s_axi_awready,

    // Write Data Channel
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]            s_axi_wstrb,
    input  wire                  s_axi_wvalid,
    output reg                   s_axi_wready,

    // Write Response Channel
    output reg [1:0]             s_axi_bresp,
    output reg                   s_axi_bvalid,
    input  wire                  s_axi_bready,

    // Read Address Channel
    input  wire [31:0] s_axi_araddr,
    input  wire                  s_axi_arvalid,
    output reg                   s_axi_arready,

    // Read Data Channel
    output reg [31:0]  s_axi_rdata,
    output reg [1:0]             s_axi_rresp,
    output reg                   s_axi_rvalid,
    input  wire                  s_axi_rready,

    // Output register
    output wire [31:0] control_reg_o,
    output wire [31:0] config_reg_o
    // output wire gpio_o,
    // output wire gpio_1
);
    
    // Internal Register
    reg [31:0] reg_0;
    reg [31:0] reg_0_d;  // Register at offset 0x00
    reg [31:0] reg_1; // register at offset 0x04
    reg [31:0] reg_1_d;
    reg [7:0] w_offset_r;
    reg [7:0] r_offset_r;

    always @(posedge clk) begin 
        if(~rst_n) begin
            w_offset_r <= 0;
            r_offset_r <= 0;
        end else begin
            w_offset_r <=  s_axi_awaddr[7:0];
            r_offset_r <= s_axi_araddr[7:0];
        end
    end
   

    localparam  WR_IDLE = 2'b00,
                WR_READY = 2'b01,
                WR_DATA = 2'b10,
                WR_DONE = 2'b11;
    reg [1:0] wr_state, wr_state_next;



    
    // Write FSM
    always @(posedge clk) begin
        if (!rst_n)
            wr_state <= WR_IDLE;
        else
            wr_state <= wr_state_next;
    end
    always @(*) begin
        wr_state_next = wr_state;
        case(wr_state)
            WR_IDLE: wr_state_next = (s_axi_awvalid) ? WR_READY : WR_IDLE;
            WR_READY: wr_state_next = WR_DATA;
            WR_DATA: wr_state_next = (s_axi_bready) ? WR_DONE : WR_DATA;
            WR_DONE: wr_state_next = WR_IDLE ;

        endcase
    end
    always @(*) begin
        s_axi_wready  = 0;
        s_axi_bvalid  = 0;
        s_axi_bresp   = 2'b00; 
        reg_0 = reg_0_d;
        reg_1 = reg_1_d;
        s_axi_awready = 1'b0;
        case (wr_state)
            WR_IDLE: begin

            end
            WR_READY: begin
            	s_axi_awready = 1'b1;
            end
            WR_DATA: begin
                    s_axi_wready = 1;
                    if (w_offset_r[7:0] == 8'h00 & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) reg_0[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_0[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_0[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_0[31:24] = s_axi_wdata[31:24];
                    end
                    if (w_offset_r[7:0] == 8'h04 & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) reg_1[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_1[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_1[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_1[31:24] = s_axi_wdata[31:24];
                    end 

            end
            WR_DONE: begin
                s_axi_bvalid = 1;

            end
        endcase
    end

    // FSM for Read
    localparam RD_IDLE = 2'b00;
    localparam RD_READY = 2'b01;
    localparam RD_DONE = 2'b10;
    reg [1:0] rd_state, rd_state_next;

    // Read FSM
    always @(posedge clk) begin
        if (!rst_n)
            rd_state <= RD_IDLE;
        else
            rd_state <= rd_state_next;
    end
    always @(*) begin
        rd_state_next = rd_state;
        case(rd_state)
            RD_IDLE: rd_state_next = (s_axi_arvalid) ? RD_READY : RD_IDLE;
            RD_READY: rd_state_next = s_axi_rready ? RD_DONE : RD_READY;
            RD_DONE: rd_state_next = RD_IDLE ;
            default: rd_state_next = RD_IDLE;
        endcase


    end
 
    always @(*) begin
        s_axi_rvalid  = 0;
        s_axi_rresp   = 2'b00; // OKAY
        s_axi_rdata   = 32'b0;
        s_axi_arready = 1'b0;
        case (rd_state)
            RD_IDLE: begin
              
            end
            RD_READY: begin
            	s_axi_arready = 1'b1;
            end

            RD_DONE: begin
                    s_axi_rvalid  = 1;
                    if (r_offset_r[7:0]  == 8'h00 & s_axi_rready )begin
                          s_axi_rdata   = reg_0_d;
                    end
                    if (r_offset_r[7:0]  == 8'h04 & s_axi_rready )begin
                          s_axi_rdata   = reg_1_d;
                    end
            end
            default: begin
                    s_axi_rvalid  = 0;
                    s_axi_rresp   = 2'b00; // OKAY
                    s_axi_rdata   = 32'b0;
                    s_axi_arready = 1'b0;
            end
        endcase
           

    end

    assign start_pulse = reg_0_d[0];

    // Output assignment
    always @(posedge clk) begin
        if (!rst_n) begin
            reg_0_d <= 32'd0;
        end else if(start_pulse) begin
            reg_0_d[0] <= 1'b0;
        end else  begin
            reg_0_d <= reg_0;
        end
    end
    always @(posedge clk) begin 
        if(~rst_n) begin
            reg_1_d <= 0;
        end else begin
            reg_1_d <= reg_1;
        end
    end
    
   assign control_reg_o = reg_0_d;
   assign config_reg_o = reg_1_d;
   // assign gpio_o = reg_0[0];
   // assign gpio_1 = reg_1[0];

endmodule
