import common_pkg::*;

module axi4_lite (
    input  wire                  clk,
    input  wire                  rst_n,
 
    // Write Address Channel
    input  wire [31:0]           s_axi_awaddr,
    input  wire                  s_axi_awvalid,
    output logic                   s_axi_awready,

    // Write Data Channel
    input  wire [31:0]           s_axi_wdata,
    input  wire [3:0]            s_axi_wstrb,
    input  wire                  s_axi_wvalid,
    output logic                   s_axi_wready,

    // Write Response Channel
    output logic [1:0]             s_axi_bresp,
    output logic                   s_axi_bvalid,
    input  wire                  s_axi_bready,

    // Read Address Channel
    input  logic [31:0] s_axi_araddr,
    input  logic                  s_axi_arvalid,
    output reg                   s_axi_arready,

    // Read Data Channel
    output logic [31:0]  s_axi_rdata,
    output logic [1:0]             s_axi_rresp,
    output logic                   s_axi_rvalid,
    input  wire                  s_axi_rready,

    output  [31:0] tdr_o,
    input [31:0] rdr_i,
    output  [31:0] lcr_o,
    output  [31:0] ocr_o,
    input [31:0] lsr_i,
    output  [31:0] fcr_o,
    output  [31:0] ier_o,
    input [31:0] iir_i,
    output  [31:0] hcr_o


);
    
    // Internal Register
    logic [31:0] tdr, tdr_d;
    logic [31:0] rdr;;
    logic [31:0] lcr, lcr_d;
    logic [31:0] ocr, ocr_d;
    logic [31:0] lsr;
    logic [31:0] fcr, fcr_d;
    logic [31:0] ier, ier_d;
    logic [31:0] iir;
    logic [31:0] hcr, hcr_d;

    always_ff @(posedge clk) begin 
        if(~rst_n) begin
            rdr <= 0;
            lsr <= 0;
            iir <= 0;
        end else begin
            rdr <= rdr_i;
            lsr <= lsr_i;
            iir <= iir_i;
        end
    end
   
    logic [11:0] w_offset_r;
    logic [11:0] r_offset_r;

    always @(posedge clk) begin 
        if(~rst_n) begin
            w_offset_r <= 0;
            r_offset_r <= 0;
        end else begin
            w_offset_r <=  s_axi_awaddr[11:0];
            r_offset_r <= s_axi_araddr[11:0];
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
        s_axi_awready = 1'b0;
        tdr = tdr_d;
        lcr = lcr_d;
        ocr = ocr_d;
        fcr = fcr_d;
        ier = ier_d;
        hcr = hcr_d;
        case (wr_state)
            WR_IDLE: begin

            end
            WR_READY: begin
            	s_axi_awready = 1'b1;
            end
            WR_DATA: begin
                    s_axi_wready = 1;
                    if (w_offset_r[11:0] == ADDR_TDR & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) tdr[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) tdr[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) tdr[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) tdr[31:24] = s_axi_wdata[31:24];
                    end
                    if (w_offset_r[11:0] ==  ADDR_LCR & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) lcr[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) lcr[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) lcr[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) lcr[31:24] = s_axi_wdata[31:24];
                    end

                    if (w_offset_r[11:0] ==  ADDR_OCR & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) ocr[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) ocr[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) ocr[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) ocr[31:24] = s_axi_wdata[31:24];
                    end 

                    if (w_offset_r[11:0] == ADDR_FCR & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) fcr[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) fcr[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) fcr[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) fcr[31:24] = s_axi_wdata[31:24];
                    end               

                    if (w_offset_r[11:0] == ADDR_IER & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) ier[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) ier[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) ier[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) ier[31:24] = s_axi_wdata[31:24];
                    end                    

                    if (w_offset_r[11:0] == ADDR_HCR & s_axi_bready & s_axi_wvalid) begin
                        if (s_axi_wstrb[0]) hcr[7:0]   = s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) hcr[15:8]  = s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) hcr[23:16] = s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) hcr[31:24] = s_axi_wdata[31:24];
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
                    if(s_axi_rready) begin
                        case(r_offset_r) 
                            ADDR_TDR: s_axi_rdata = tdr_d;
                            ADDR_RDR: s_axi_rdata = rdr;
                            ADDR_LCR: s_axi_rdata = lcr_d;
                            ADDR_LSR: s_axi_rdata = lsr;
                            ADDR_OCR: s_axi_rdata = ocr_d;
                            ADDR_IER: s_axi_rdata = ier_d;
                            ADDR_FCR: s_axi_rdata = fcr_d;
                            ADDR_IIR: s_axi_rdata = iir;
                            ADDR_HCR: s_axi_rdata = hcr_d;

                            default: s_axi_rdata = 0;
                        endcase

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

    assign start_pulse = ocr_d[1];

    // Output assignment
    always @(posedge clk) begin
        if (!rst_n) begin
            ocr_d <= 32'd0;
        end else if(start_pulse) begin
            ocr_d[1] <= 1'b0;
        end else  begin
            ocr_d <= ocr;
        end
    end
    always @(posedge clk) begin 
        if(~rst_n) begin
            tdr_d <= 0;
            fcr_d <= 0;
            ier_d <= 0;
            hcr_d <= 0;
            lcr_d <= 0;
        end else begin
            tdr_d <= tdr;
            fcr_d <= fcr;
            ier_d <= ier;
            hcr_d <= hcr;
            lcr_d <= lcr;

        end
    end
    
    assign tdr_o = tdr_d;
    assign ocr_o = ocr_d;
    assign fcr_o = fcr_d;
    assign lcr_o = lcr_d;
    assign ier_o = ier_d;
    assign hcr_o = hcr_d;
endmodule
