module regs (
    input  wire        clk,
    input  wire        rst_n,
 
    // Wishbone write interface
    input  wire [7:0]  wr_addr,     
    input  wire [31:0] wr_data,     
    input  wire        wr_en,       
    // Wishbone read interface
    input  wire [7:0]  rd_addr,
    output reg  [31:0] rd_data,

    // Controller và KEM 
    output reg         start,    
    output wire [1:0]  mode,       
    output wire        op,         
    output wire        key_len,    
    output reg         key_valid,   
    output reg         iv_valid,    
    output wire        auto_start, 
    output wire        auto_iv_upd,
    output wire        irq_en,     
    input wire key_expanded,
    //  Key, IV, Data registers
    output reg  [255:0] key_out,
    output reg  [127:0] iv_out,    
    output reg  [127:0] din_out,   

    //  Data output 
    input  wire [127:0] dout_in,   
    input  wire         dout_wr,  

     // Status inputs
    input  wire         busy,
    input  wire         iv_upd_trig,     

    input  wire [127:0] iv_next,       
 
    output reg          irq
);


    localparam ADDR_CTRL   = 8'h00;
    localparam ADDR_STATUS = 8'h04;
    localparam ADDR_CONFIG = 8'h08;
 
    localparam ADDR_KEY_0  = 8'h10;
    localparam ADDR_KEY_1  = 8'h14;
    localparam ADDR_KEY_2  = 8'h18;
    localparam ADDR_KEY_3  = 8'h1C;
    localparam ADDR_KEY_4  = 8'h20;
    localparam ADDR_KEY_5  = 8'h24;
    localparam ADDR_KEY_6  = 8'h28;
    localparam ADDR_KEY_7  = 8'h2C;
 
    localparam ADDR_IV_0   = 8'h30;
    localparam ADDR_IV_1   = 8'h34;
    localparam ADDR_IV_2   = 8'h38;
    localparam ADDR_IV_3   = 8'h3C;
 
    localparam ADDR_DIN_0  = 8'h40;
    localparam ADDR_DIN_1  = 8'h44;
    localparam ADDR_DIN_2  = 8'h48;
    localparam ADDR_DIN_3  = 8'h4C;
 
    localparam ADDR_DOUT_0 = 8'h50;
    localparam ADDR_DOUT_1 = 8'h54;
    localparam ADDR_DOUT_2 = 8'h58;
    localparam ADDR_DOUT_3 = 8'h5C;



    reg [31:0]  ctrl_reg;
    reg [31:0]  config_reg;

    reg [127:0] dout_reg;
    reg output_valid;

     assign mode        = ctrl_reg[2:1];
    assign op          = ctrl_reg[3];
    assign key_len     = ctrl_reg[4];

    assign auto_start  = config_reg[0];
    assign auto_iv_upd = config_reg[1];
    assign irq_en      = config_reg[2];

    reg start_pending;

     always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_reg     <= 32'h0;
            config_reg   <= 32'h0;
            key_out      <= 256'h0;
            iv_out       <= 128'h0;
            din_out      <= 128'h0;
            start_pending <= 1'b0; 
            dout_reg     <= 128'h0;
            key_valid    <= 1'b0;
            iv_valid     <= 1'b0;
            output_valid <= 1'b0;
            start        <= 1'b0;
            irq          <= 1'b0;
        end
        else begin
            start        <= 1'b0; 
            irq          <= 1'b0;
 
            if (dout_wr) begin
                dout_reg     <= dout_in;
                output_valid <= 1'b1;
                if (config_reg[2]) irq <= 1'b1;
            end
 
            if (iv_upd_trig && auto_iv_upd) begin
                iv_out <= iv_next;
            end

            if (start_pending && key_expanded) begin
                start         <= 1'b1;   
                start_pending <= 1'b0;
            end
 
 
            if (wr_en) begin
                case (wr_addr)
                    ADDR_CTRL: begin
                        if(wr_data[4] != ctrl_reg[4]) begin
                            key_valid <= 1'b0;
                        end
                        ctrl_reg <= wr_data[6:0];
                        if (wr_data[0]) start <= 1'b1;
                        key_valid <= wr_data[5];
                        iv_valid  <= wr_data[6];
                    end
 
                    ADDR_CONFIG: config_reg <= wr_data[2:0];


                    ADDR_KEY_0: begin 
                        key_out[255:224]  <= wr_data;
                        key_valid <= 1'b0;
                    end
                    ADDR_KEY_1: key_out[223:192]   <= wr_data;
                    ADDR_KEY_2: key_out[191:160]   <= wr_data;
                    ADDR_KEY_3: begin
                        key_out[159:128] <= wr_data;
                        if (!ctrl_reg[4]) begin
                            key_valid    <= 1'b1;
                            ctrl_reg[5]  <= 1'b1;
                        end
                    end
 
                    ADDR_KEY_4: begin
                            key_out[127:96] <= wr_data;
                            key_valid <= 1'b0;

                    end 
                    ADDR_KEY_5: key_out[95:64] <= wr_data;
                    ADDR_KEY_6: key_out[63:32] <= wr_data;
                    ADDR_KEY_7: begin
                        key_out[31:0] <= wr_data;
                        if (ctrl_reg[4]) begin
                            key_valid    <= 1'b1;
                            ctrl_reg[5]  <= 1'b1;
                        end
                    end
                    
 
                    ADDR_IV_0: begin
                         iv_out[127:96] <= wr_data;
                         iv_valid <= 1'b0;
                    end
                    ADDR_IV_1: iv_out[95:64]  <= wr_data;
                    ADDR_IV_2: iv_out[63:32]  <= wr_data;
                    ADDR_IV_3: begin
                        iv_out[31:0] <= wr_data;
                        iv_valid    <= 1'b1;
                        ctrl_reg[6] <= 1'b1;
                    end
 
                    ADDR_DIN_0: din_out[127:96] <= wr_data;
                    ADDR_DIN_1: din_out[95:64]  <= wr_data;
                    ADDR_DIN_2: din_out[63:32]  <= wr_data;
                    ADDR_DIN_3: begin
                        din_out[31:0] <= wr_data;
                        if (auto_start && key_valid &&
                            (mode == 2'b00 || iv_valid)) begin
                            if (key_expanded)
                                start <= 1'b1;       
                            else
                                start_pending <= 1'b1; 
                        end
                    end

                    default: ; 
 
                endcase
            end 
 
        
            if (rd_addr == ADDR_DOUT_3 && output_valid) begin
                output_valid <= 1'b0;
                ctrl_reg[5]  <= ctrl_reg[5]; 
            end
 
            ctrl_reg[5] <= key_valid;
            ctrl_reg[6] <= iv_valid;
 
        end
    end

    always @(*) begin
        rd_data = 32'h0; // default
 
        case (rd_addr)
            ADDR_CTRL:   rd_data = {25'h0, ctrl_reg};
 
            
            ADDR_STATUS: rd_data = {28'h0,
                                     key_expanded,           // [3] KEY_EXANPADED
                                     !busy & !output_valid,  // [2] INPUT_READY
                                     output_valid,           // [1]
                                     busy};                  // [0]
 
            // CONFIG
            ADDR_CONFIG: rd_data = {29'h0, config_reg};
 
            // KEY — WO, đọc trả về 0 (bảo mật: không để lộ key)
            ADDR_KEY_0,
            ADDR_KEY_1,
            ADDR_KEY_2,
            ADDR_KEY_3,
            ADDR_KEY_4,
            ADDR_KEY_5,
            ADDR_KEY_6,
            ADDR_KEY_7:  rd_data = 32'h0;
 
            // IV
            ADDR_IV_0:   rd_data = iv_out[127:96];
            ADDR_IV_1:   rd_data = iv_out[95:64];
            ADDR_IV_2:   rd_data = iv_out[63:32];
            ADDR_IV_3:   rd_data = iv_out[31:0];
 
            // DIN — WO, trả về 0
            ADDR_DIN_0,
            ADDR_DIN_1,
            ADDR_DIN_2,
            ADDR_DIN_3:  rd_data = 32'h0;
 
            // DOUT — đọc kết quả từ cipher
            ADDR_DOUT_0: rd_data = dout_reg[127:96];
            ADDR_DOUT_1: rd_data = dout_reg[95:64];
            ADDR_DOUT_2: rd_data = dout_reg[63:32];
            ADDR_DOUT_3: rd_data = dout_reg[31:0];
 
            default:     rd_data = 32'hDEADBEEF; // invalid address
        endcase
    end
endmodule