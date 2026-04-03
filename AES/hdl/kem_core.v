module kem_core (
    input  wire         clk,
    input  wire         rst_n,

    input  wire [255:0] key_in,
    input  wire         key_len,   

    input  wire         load,   // load     
    input  wire         next_rk,   // tạo round key tiếp theo
    
    input wire op,
    input wire load_dec,
    input wire save_dec,

    output reg [127:0] rk_out,    
    output reg          rk_valid
);

    reg [255:0] buff;
    reg [3:0]   r_idx;
    reg         step_sel;
    reg [127:0] key_dec;

    wire [31:0] w0 = buff[31:0];
    wire [31:0] w1 = buff[63:32];
    wire [31:0] w2 = buff[95:64];
    wire [31:0] w3 = buff[127:96];
    wire [31:0] w4 = buff[159:128];
    wire [31:0] w5 = buff[191:160];
    wire [31:0] w6 = buff[223:192];
    wire [31:0] w7 = buff[255:224];

  
    wire [31:0] rot_w0 = {w0[23:0], w0[31:24]};  

    wire [31:0] rot_w4 = {w4[23:0], w4[31:24]};

    wire [31:0] sub_rot_w0;
    wire [31:0] sub_rot_w4;
    wire [31:0] sub_w4;

    subword u_sub_rot_w0 (.in(rot_w0), .out(sub_rot_w0));
    subword u_sub_rot_w4 (.in(rot_w4), .out(sub_rot_w4));
    subword u_sub_w0     (.in(w4),     .out(sub_w4));

    wire [7:0] rc;
    rcon_lut u_rcon (.idx(r_idx), .rcon(rc));
    wire [31:0] rcon_word = {rc, 24'h000000};

    wire [31:0] g_w0 = sub_rot_w0 ^ rcon_word;
    wire [31:0] g_w4 = sub_rot_w4 ^ rcon_word;

    wire [31:0] temp = (!key_len)  ? g_w4      :  
                       (!step_sel) ? g_w0      :   
                                     sub_w4;      

    wire [31:0] nw7 = w7 ^ temp;
    wire [31:0] nw6 = w6 ^ nw7;
    wire [31:0] nw5 = w5 ^ nw6;
    wire [31:0] nw4 = w4 ^ nw5;      

    wire [31:0] nw3 = w3 ^ temp;
    wire [31:0] nw2 = w2 ^ nw3;
    wire [31:0] nw1 = w1 ^ nw2;
    wire [31:0] nw0 = w0 ^ nw1;



    wire [127:0] rk_upper = {nw7, nw6, nw5, nw4};
    wire [127:0] rk_lower = {nw3, nw2, nw1, nw0};



    wire [127:0] rk_comb = (key_len & step_sel) ? rk_lower : rk_upper;

    wire [127:0] rk_imixed;
    inv_mixcolumns u_imc (.in(rk_comb), .out(rk_imixed));

    wire [3:0] Nr = key_len ? 4'd14 : 4'd10;
    wire is_boundary = (r_idx == 4'd1) || (r_idx == Nr);

    wire [127:0] rk_final = (op && !is_boundary) ? rk_imixed : rk_comb;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            buff     <= 256'h0;
            r_idx    <= 4'd1;
            step_sel <= 1'b0;
            rk_out   <= 128'h0;
            rk_valid <= 1'b0;
        end else if (load) begin
            r_idx    <= 4'd1;
            step_sel <= 1'b0;
            rk_out   <= 128'h0;
            rk_valid <= 1'b0;
            buff     <= key_len ? key_in : {key_in[255:128], 128'h0};;

        end else if(load_dec) begin
            buff     <= {key_dec, 128'h0};
            r_idx    <= 4'd1;
            step_sel <= 1'b0;
            rk_valid <= 1'b0;
        end else if(save_dec) begin
            key_dec <= buff[255:128];
        end else if (next_rk) begin
            rk_out   <= rk_final;
            rk_valid <= 1'b1;
 
            if (!key_len) begin
                buff[255:128] <= rk_final;
                r_idx      <= r_idx + 4'd1;
            end
            else begin
                step_sel <= ~step_sel;
                if (!step_sel) begin
                    buff[255:128]   <= rk_upper;
                    r_idx        <= r_idx + 4'd1;

                end else begin
                    buff[127:0] <= rk_lower;

                end
            end
        end else begin
            rk_valid <= 1'b0;
        end

      end


endmodule