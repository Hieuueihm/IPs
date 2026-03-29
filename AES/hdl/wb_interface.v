// ============================================================
//  wb_interface.v
//  Wishbone B4 Slave — handshake, address decode, read mux
//
//  Spec: 32-bit data, byte-addressed, word-aligned
//  Timing:
//    Write: STB=1, WE=1 → ACK=1 next cycle (1 cycle latency)
//    Read:  STB=1, WE=0 → data from register combinational, ACK=1 next cycle
//    STALL: busy=1 & write to DIN → STALL=1 until not busy, then ACK=1 next cycle
//
//  Address range valid: 0x00..0x5C
//  Out of range → ERR_O=1
// ============================================================
module wb_interface (
    input  wire        CLK_I,
    input  wire        RST_I,
    input [7:0] ADR_I,      
    input [31:0] DAT_I, 
    output reg  [31:0] DAT_O,
    input  wire        WE_I,
    
    input  wire [3:0]  SEL_I,       
    input  wire        STB_I,

    output reg         ACK_O,
    input  wire        CYC_I,

    output wire        STALL_O,
    output reg         ERR_O,

    output wire [7:0]  wr_addr,
    output wire [31:0] wr_data,
    output wire        wr_en,
    output wire [7:0]  rd_addr,
    input  wire [31:0] rd_data,

    input  wire        busy
);

    wire [7:0] byte_addr  = ADR_I;
    wire       addr_valid = (byte_addr <= 8'h5C);

    wire       trans      = CYC_I & STB_I;

    // DIN = 0x40..0x4C
    wire wr_din = WE_I & (byte_addr >= 8'h40) & (byte_addr <= 8'h4C);

    assign STALL_O = trans & wr_din & busy;

    assign wr_addr = byte_addr;
    assign wr_data = DAT_I;
    assign wr_en   = trans & WE_I & addr_valid & ~STALL_O;

    assign rd_addr = byte_addr;

    always @(posedge CLK_I) begin
        if (RST_I) begin
            ACK_O <= 1'b0;
            ERR_O <= 1'b0;
            DAT_O <= 32'h0;
        end
        else begin
            ACK_O <= 1'b0;
            ERR_O <= 1'b0;

            if (trans & ~STALL_O) begin
                if (~addr_valid) begin
                    ERR_O <= 1'b1;
                end
                else begin
                    ACK_O <= 1'b1;
                    if (~WE_I)
                        DAT_O <= rd_data;
                end
            end
        end
    end

endmodule