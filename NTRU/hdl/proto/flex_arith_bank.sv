// Arithmetic-bank experiment, not a complete complex butterfly/transform.
// Same array switches between NTT12289 and real fixed-point W=32/64/128.
// One input register and one output register, II=1, no stalls.
// mode: 0=NTT16, 1=FFT32, 2=FFT64, 3=FFT128.
module flex_arith_bank #(
    parameter integer G = 32,
    parameter integer NTT_LANES = 16
) (
    input wire clk, rst, in_valid,
    input wire [1:0] mode,
    input wire [1023:0] x, y, z,
    output reg out_valid,
    output reg [1:0] out_mode,
    output reg [1023:0] product, sum_out, diff_out
);
    localparam integer K=128/G;
    localparam integer N=K*K;
    localparam integer LEVELS=$clog2(N);
    reg valid_r;
    reg [1:0] mode_r;
    reg [1023:0] x_r,y_r,z_r;
    always @(posedge clk) begin
        valid_r <= !rst && in_valid;
        mode_r <= mode;
        x_r <= x; y_r <= y; z_r <= z;
    end

    function integer limb_i(input integer index, input integer logk);
        integer bitn;
        begin
            limb_i=0;
            for(bitn=0;bitn<logk;bitn=bitn+1)
                limb_i=limb_i|(((index>>(2*bitn))&1)<<bitn);
        end
    endfunction
    function integer limb_j(input integer index, input integer logk);
        integer bitn;
        begin
            limb_j=0;
            for(bitn=0;bitn<logk;bitn=bitn+1)
                limb_j=limb_j|(((index>>(2*bitn+1))&1)<<bitn);
        end
    endfunction
    function integer node_width(input integer level);
        integer lv,ww;
        begin
            ww=2*G+1;
            for(lv=0;lv<level;lv=lv+1) begin
                ww=ww+(G<<(lv/2))+1;
                if(ww>192) ww=192;
            end
            node_width=ww;
        end
    endfunction

    wire [191:0] tree[0:LEVELS][0:N-1];
    genvar t,lv,j;
    generate for(t=0;t<N;t=t+1) begin:g_leaf
        localparam integer K32=32/G, K64=64/G;
        localparam integer I32=limb_i(t%(K32*K32),$clog2(K32));
        localparam integer J32=limb_j(t%(K32*K32),$clog2(K32));
        localparam integer I64=limb_i(t%(K64*K64),$clog2(K64));
        localparam integer J64=limb_j(t%(K64*K64),$clog2(K64));
        localparam integer I128=limb_i(t,$clog2(K));
        localparam integer J128=limb_j(t,$clog2(K));
        wire [G-1:0] ax32=x_r[(t/(K32*K32))*32+I32*G+:G];
        wire [G-1:0] by32=y_r[(t/(K32*K32))*32+J32*G+:G];
        wire [G-1:0] ax64=x_r[(t/(K64*K64))*64+I64*G+:G];
        wire [G-1:0] by64=y_r[(t/(K64*K64))*64+J64*G+:G];
        wire [G-1:0] ax128=x_r[I128*G+:G];
        wire [G-1:0] by128=y_r[J128*G+:G];
        wire [G-1:0] an, bn;
        if(t<NTT_LANES) begin:g_ntt_operand
            assign an={{(G-16){1'b0}},x_r[t*16+:16]};
            assign bn={{(G-16){1'b0}},y_r[t*16+:16]};
        end else begin:g_unused_ntt
            assign an=0; assign bn=0;
        end
        wire [G-1:0] ax=mode_r==0?an:mode_r==1?ax32:mode_r==2?ax64:ax128;
        wire [G-1:0] by=mode_r==0?bn:mode_r==1?by32:mode_r==2?by64:by128;
        wire sa=mode_r==0?1'b0:mode_r==1?(I32==K32-1):mode_r==2?(I64==K64-1):(I128==K-1);
        wire sb=mode_r==0?1'b0:mode_r==1?(J32==K32-1):mode_r==2?(J64==K64-1):(J128==K-1);
        wire [2*G:0] p;
        // All leaf sites remain available in NTT mode. Mask high FFT terms at
        // the tree input only: no leaf is physically removed from narrow mode.
        wire keep=mode_r==0 || (mode_r==1?G*(I32+J32)<48:
                                   mode_r==2?G*(I64+J64)<96:G*(I128+J128)<192);
        mul_ss #(.W(G),.IMPL("CORR")) u_mul(ax,by,sa,sb,p);
        assign tree[0][t]=keep?{{(192-(2*G+1)){p[2*G]}},p}:192'b0;
    end endgenerate

    generate for(lv=0;lv<LEVELS;lv=lv+1) begin:g_level
        localparam integer CW=node_width(lv), NW=node_width(lv+1);
        localparam integer SHIFT=G<<(lv/2);
        for(j=0;j<(N>>(lv+1));j=j+1) begin:g_node
            wire [NW-1:0] a={{(NW-CW){tree[lv][2*j][CW-1]}},tree[lv][2*j][CW-1:0]};
            wire [NW-1:0] b={{(NW-CW){tree[lv][2*j+1][CW-1]}},tree[lv][2*j+1][CW-1:0]};
            wire [NW-1:0] s=a+(b<<SHIFT);
            assign tree[lv+1][j]={{(192-NW){s[NW-1]}},s};
        end
    end endgenerate

    wire [1023:0] np;
    generate for(j=0;j<64;j=j+1) begin:g_ntt
        if(j<NTT_LANES) begin:g_active
            wire [31:0] t=tree[0][j][31:0];
            // q=12289, -q^-1 mod 2^16=12287.
            wire [15:0] m=(t[15:0]<<14)-(t[15:0]<<12)-t[15:0];
            wire [29:0] me={14'b0,m};
            wire [29:0] mq=(me<<14)-(me<<12)+me;
            wire [29:0] s={2'b0,t[27:0]}+mq;
            wire [14:0] u={1'b0,s[29:16]};
            wire [15:0] residue=u>=15'd12289 ? u-15'd12289 : u;
            assign np[j*16+:16]=residue;
        end else begin:g_idle
            assign np[j*16+:16]=0;
        end
    end endgenerate

    wire [1023:0] fp32,fp64;
    localparam integer TAP32=2*$clog2(32/G), TAP64=2*$clog2(64/G);
    generate for(j=0;j<16;j=j+1) begin:g_f32
        wire [47:0] s=tree[TAP32][j][47:0]+48'h000000008000;
        wire [31:0] p=s[47:16];
        assign fp32[j*32+:32]=p;
    end endgenerate
    assign fp32[1023:512]=0;
    generate for(j=0;j<4;j=j+1) begin:g_f64
        wire [95:0] s=tree[TAP64][j][95:0]+96'h000000000000000080000000;
        wire [63:0] p=s[95:32];
        assign fp64[j*64+:64]=p;
    end endgenerate
    assign fp64[1023:256]=0;
    wire [191:0] s128=tree[LEVELS][0]+192'h000000000000000000000000000000008000000000000000;
    wire [127:0] p128=s128[191:64];
    wire [1023:0] selected_p=mode_r==0 ? np : mode_r==1 ? fp32 : mode_r==2 ? fp64 : {896'b0,p128};
    // One dual-output lane ALU: carry chains span 16/32/64/128 bits by mode.
    // Mod-q correction follows this same raw add/sub; it is not a second BF ALU.
    wire [64:0] carry_add,carry_sub;
    wire [1023:0] selected_u,selected_v;
    assign carry_add[0]=0; assign carry_sub[0]=1;
    generate for(j=0;j<64;j=j+1) begin:g_alu
        wire start;
        // Make physical carry cuts explicit. Higher chunks never participate
        // in the wider FFT modes, so they need no carry from inactive lanes.
        if(j>=32 || j%8==0 || (j>=16 && j%2==0) || (j>=8 && j%4==0)) begin:g_static_cut
            assign start=1'b1;
        end else if(j%4==0) begin:g_cut64
            assign start=(mode_r!=3);
        end else if(j%2==0) begin:g_cut32
            assign start=!mode_r[1];
        end else begin:g_cut16
            assign start=(mode_r==0);
        end
        wire ca=start ? 1'b0 : carry_add[j];
        wire cs=start ? 1'b1 : carry_sub[j];
        wire [16:0] a={1'b0,z_r[j*16+:16]}+{1'b0,selected_p[j*16+:16]}+ca;
        wire [16:0] b={1'b0,z_r[j*16+:16]}+{1'b0,~selected_p[j*16+:16]}+cs;
        assign carry_add[j+1]=a[16]; assign carry_sub[j+1]=b[16];
        wire active=mode_r==0 ? j<NTT_LANES : mode_r==1 ? j<32 : mode_r==2 ? j<16 : j<8;
        wire [15:0] corrected_add,corrected_sub;
        if(j<NTT_LANES) begin:g_correct
            assign corrected_add=a>=17'd12289 ? a-17'd12289 : a[15:0];
            assign corrected_sub=b[16] ? b[15:0] : b[15:0]+16'd12289;
        end else begin:g_no_correct
            assign corrected_add=0; assign corrected_sub=0;
        end
        assign selected_u[j*16+:16]=active ? (mode_r==0 ? corrected_add : a[15:0]) : 16'b0;
        assign selected_v[j*16+:16]=active ? (mode_r==0 ? corrected_sub : b[15:0]) : 16'b0;
    end endgenerate
    always @(posedge clk) begin
        out_valid <= !rst && valid_r;
        out_mode <= mode_r;
        product<=selected_p; sum_out<=selected_u; diff_out<=selected_v;
    end
endmodule

module proto_r32(input clk,rst,in_valid,input [1:0] mode,input [1023:0] x,y,z,
    output out_valid,output [1:0] out_mode,output [1023:0] product,sum_out,diff_out);
    flex_arith_bank #(.G(32),.NTT_LANES(16)) u(.*);
endmodule
module proto_f16_common(input clk,rst,in_valid,input [1:0] mode,input [1023:0] x,y,z,
    output out_valid,output [1:0] out_mode,output [1023:0] product,sum_out,diff_out);
    flex_arith_bank #(.G(16),.NTT_LANES(16)) u(.*);
endmodule
module proto_f16_wide(input clk,rst,in_valid,input [1:0] mode,input [1023:0] x,y,z,
    output out_valid,output [1:0] out_mode,output [1023:0] product,sum_out,diff_out);
    flex_arith_bank #(.G(16),.NTT_LANES(64)) u(.*);
endmodule
module proto_f16_mid(input clk,rst,in_valid,input [1:0] mode,input [1023:0] x,y,z,
    output out_valid,output [1:0] out_mode,output [1023:0] product,sum_out,diff_out);
    flex_arith_bank #(.G(16),.NTT_LANES(32)) u(.*);
endmodule
