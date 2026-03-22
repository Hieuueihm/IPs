module kem_core (
    input  wire         clk,
    input  wire         rst_n,

    input  wire [255:0] key_in,
    input  wire         key_len,   

    input  wire         load,   // load     
    input  wire         next_rk,   // tạo round key tiếp theo

    output wire [127:0] rk_out,    
    output reg          rk_valid
);

    reg [255:0] buf;
    reg [3:0]   r_idx;
    reg         step_sel;

    wire [31:0] w0 = buf[31:0];
    wire [31:0] w1 = buf[63:32];
    wire [31:0] w2 = buf[95:64];
    wire [31:0] w3 = buf[127:96];
    wire [31:0] w4 = buf[159:128];
    wire [31:0] w5 = buf[191:160];
    wire [31:0] w6 = buf[223:192];
    wire [31:0] w7 = buf[255:224];

    wire [31:0] rot_w3 = {w3[23:0], w3[31:24]};  

    wire [31:0] rot_w7 = {w7[23:0], w7[31:24]};

    wire [31:0] sub_rot_w3;
    wire [31:0] sub_rot_w7;
    wire [31:0] sub_w3;

    subword u_sub_rot_w3 (.in(rot_w3), .out(sub_rot_w3));
    subword u_sub_rot_w7 (.in(rot_w7), .out(sub_rot_w7));
    subword u_sub_w3     (.in(w3),     .out(sub_w3));

    wire [7:0] rc;
    rcon_lut u_rcon (.idx(r_idx), .rcon(rc));
    wire [31:0] rcon_word = {rc, 24'h000000};

    wire [31:0] g_w3 = sub_rot_w3 ^ rcon_word;
    wire [31:0] g_w7 = sub_rot_w7 ^ rcon_word;

    wire [31:0] temp = (!key_len)  ? g_w3      :  
                       (!step_sel) ? g_w7      :   
                                     sub_w3;      

    wire [31:0] nw0 = w0 ^ temp;
    wire [31:0] nw1 = w1 ^ nw0;
    wire [31:0] nw2 = w2 ^ nw1;
    wire [31:0] nw3 = w3 ^ nw2;

 
    wire [31:0] nw4 = w4 ^ temp;
    wire [31:0] nw5 = w5 ^ nw4;
    wire [31:0] nw6 = w6 ^ nw5;
    wire [31:0] nw7 = w7 ^ nw6;


    wire [127:0] rk_lower = {nw3, nw2, nw1, nw0};
    wire [127:0] rk_upper = {nw7, nw6, nw5, nw4};

    wire [127:0] rk_comb = (key_len & step_sel) ? rk_upper : rk_lower;


      always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            buf      <= 256'h0;
            r_idx    <= 4'd1;
            step_sel <= 1'b0;
            rk_out   <= 128'h0;
            rk_valid <= 1'b0;
        end

        else if (load) begin

            buf      <= key_len ? key_in : {128'h0, key_in[127:0]};
            r_idx    <= 4'd1;
            step_sel <= 1'b0;
            rk_out   <= 128'h0;
            rk_valid <= 1'b0;
        end
        else if (next_rk) begin
            rk_out   <= rk_comb;
            rk_valid <= 1'b1;
 
            if (!key_len) begin
                buf[127:0] <= rk_lower;
                r_idx      <= r_idx + 4'd1;
            end
            else begin
                if (!step_sel) begin
                    buf[127:0]   <= rk_lower;
                    r_idx        <= r_idx + 4'd1;
                    step_sel     <= 1'b1;
                end
                else begin
                
                    buf[255:128] <= rk_upper;
                    step_sel     <= 1'b0;
                end
            end
        end
        else begin
            rk_valid <= 1'b0;
        end

      end


endmodule