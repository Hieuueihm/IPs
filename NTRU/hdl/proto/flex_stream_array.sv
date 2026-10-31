// 16 four-leaf tiles: FFT32x16 / FFT64x4 / FFT128x1, or compact NTT lanes.
// FFT input A in data[511:0], B in data[1023:512]; each packs its active words.
// NTT data/root words are packed without holes by 8/4 data and 4/3/2 roots/tile.
// Width code 0/1/2 = 32/64/128 per real component, fraction = W/2.
// Four sampled edges at advance=1. One global stall freezes all arithmetic.
module flex_stream_array #(
    parameter integer STALL_ENABLE=1
) (
    input clk,rst,in_valid,input ntt,input [1:0] width,ntt_mode,
    input profile,inverse,input [31:0] tag,
    input [2047:0] data,input [1023:0] twiddle,
    output in_ready,input out_ready,output reg out_valid,
    output reg out_ntt,output reg [1:0] out_width,out_ntt_mode,
    output reg out_profile,out_inverse,output reg [31:0] out_tag,
    output reg [2047:0] result
);
    wire advance=STALL_ENABLE ? (rst || !out_valid || out_ready) : 1'b1;
    assign in_ready=advance;
    wire [127:0] y[0:15];
    wire [15:0] tile_valid;
    genvar t;
    generate for(t=0;t<16;t=t+1)begin:g_tile
        localparam integer I64=t%2,J64=(t/2)%2;
        localparam integer I128=(t&1)|((t>>1)&2),J128=((t>>1)&1)|((t>>2)&2);
        wire [31:0] a32=data[t*32+:32],b32=data[512+t*32+:32];
        wire [31:0] a64=data[(t/4)*64+I64*32+:32],b64=data[512+(t/4)*64+J64*32+:32];
        wire [31:0] a128=data[I128*32+:32],b128=data[512+J128*32+:32];
        wire [31:0] a=width==0?a32:width==1?a64:a128;
        wire [31:0] b=width==0?b32:width==1?b64:b128;
        wire [1:0] sg=width==0?2'b11:width==1?{(J64==1),(I64==1)}:{(J128==3),(I128==3)};
        wire [127:0] nd=ntt_mode==0?data[t*128+:128]:{64'b0,data[t*64+:64]};
        wire [63:0] nw=ntt_mode==0?twiddle[t*64+:64]:ntt_mode==1?{16'b0,twiddle[t*48+:48]}:
                                                                            {32'b0,twiddle[t*32+:32]};
        wire [127:0] td=ntt?nd:{64'b0,b,a};
        flex_stream_tile #(.REDUCE_IMPL(2)) u(.clk(clk),.rst(rst),.ce(advance),
          .in_valid(in_valid),.fft_sign(sg),.mode(ntt?ntt_mode:2'd3),.profile(profile),.inverse(inverse),
          .tag(tag[15:0]),.data(td),.twiddle(nw),.out_valid(tile_valid[t]),
          .out_mode(),.out_profile(),.out_inverse(),.out_tag(),.result(y[t]));
    end endgenerate
    reg [2:0] mv,nn,qq,ii;
    reg [1:0] ww[0:2],mm[0:2];
    reg [31:0] tt[0:2];
    integer k;
    always @(posedge clk)if(advance)begin
        mv<={mv[1:0],!rst&&in_valid};nn<={nn[1:0],ntt};qq<={qq[1:0],profile};ii<={ii[1:0],inverse};
        ww[0]<=width;mm[0]<=ntt_mode;tt[0]<=tag;
        for(k=1;k<3;k=k+1)begin ww[k]<=ww[k-1];mm[k]<=mm[k-1];tt[k]<=tt[k-1];end
        if(rst)mv<=0;
        out_valid<=!rst&&mv[2];out_ntt<=nn[2];out_width<=ww[2];out_ntt_mode<=mm[2];
        out_profile<=qq[2];out_inverse<=ii[2];out_tag<=tt[2];
    end
    wire [2047:0] packed_ntt,fft32,fft64;
    generate for(t=0;t<16;t=t+1)begin:g_pack
        assign packed_ntt[t*128+:128]=y[t];
        wire [47:0] r=y[t][47:0]+48'h8000;
        assign fft32[t*32+:32]=r[47:16];
    end endgenerate
    assign fft32[2047:512]=0;
    wire [1023:0] short_ntt;
    generate for(t=0;t<16;t=t+1)begin:g_short
        assign short_ntt[t*64+:64]=y[t][63:0];
    end endgenerate
    generate for(t=0;t<4;t=t+1)begin:g_f64
        wire [95:0] p0={{31{y[4*t][64]}},y[4*t][64:0]};
        wire [95:0] p1={{31{y[4*t+1][64]}},y[4*t+1][64:0]};
        wire [95:0] p2={{31{y[4*t+2][64]}},y[4*t+2][64:0]};
        wire [95:0] p3={{31{y[4*t+3][64]}},y[4*t+3][64:0]};
        wire [95:0] r=p0+(p1<<32)+(p2<<32)+(p3<<64)+96'h80000000;
        assign fft64[t*64+:64]=r[95:32];
    end endgenerate
    assign fft64[2047:256]=0;
    wire [191:0] tree128[0:4][0:15];
    generate for(t=0;t<16;t=t+1)begin:g_f128
        localparam integer I=(t&1)|((t>>1)&2),J=((t>>1)&1)|((t>>2)&2);
        wire [191:0] p={{127{y[t][64]}},y[t][64:0]};
        assign tree128[0][t]=p;
    end endgenerate
    genvar lv;
    generate for(lv=0;lv<4;lv=lv+1)begin:g_tree
        for(t=0;t<(16>>(lv+1));t=t+1)begin:g_node
            assign tree128[lv+1][t]=tree128[lv][2*t]+(tree128[lv][2*t+1]<<(32<<(lv/2)));
        end
    end endgenerate
    wire [191:0] r128=tree128[4][0]+192'h8000000000000000;
    always @(posedge clk)if(advance)begin
        result<=nn[2]?(mm[2]==0?packed_ntt:{1024'b0,short_ntt}):
                ww[2]==0?fft32:ww[2]==1?fft64:{1920'b0,r128[191:64]};
    end
endmodule

// Two-entry input queue decouples upstream ready from downstream stall.
// COUNT=0 wrapper bypasses the queue; no output FIFO is required because the
// global advance holds output data/metadata stable while out_valid&&!out_ready.
module flex_stream_buffered #(parameter integer FIFO_ENABLE=1,STALL_ENABLE=1)(
    input clk,rst,in_valid,input ntt,input [1:0] width,ntt_mode,
    input profile,inverse,input [31:0] tag,input [2047:0] data,input [1023:0] twiddle,
    output in_ready,input out_ready,output out_valid,output out_ntt,
    output [1:0] out_width,out_ntt_mode,output out_profile,out_inverse,
    output [31:0] out_tag,output [2047:0] result
);
    wire core_ready;
    wire [3110:0] payload={ntt,width,ntt_mode,profile,inverse,tag,data,twiddle};
    wire [3110:0] cp;
    wire cv;
    generate if(FIFO_ENABLE)begin:g_fifo
        reg [3110:0] queue[0:1];reg rd,wr;reg [1:0] count;
        wire push=in_valid&&in_ready,pop=cv&&core_ready;
        assign in_ready=count<2;assign cv=count!=0;assign cp=queue[rd];
        always @(posedge clk)begin
            if(rst)begin rd<=0;wr<=0;count<=0;end
            else begin
                if(push)begin queue[wr]<=payload;wr<=!wr;end
                if(pop)rd<=!rd;
                case({push,pop})2'b10:count<=count+1;2'b01:count<=count-1;endcase
            end
        end
    end else begin:g_direct
        assign in_ready=core_ready;assign cv=in_valid;assign cp=payload;
    end endgenerate
    // Payload is 1+2+2+1+1+32+2048+1024 = 3111 bits.
    flex_stream_array #(.STALL_ENABLE(STALL_ENABLE)) core(.clk(clk),.rst(rst),.in_valid(cv),
      .ntt(cp[3110]),.width(cp[3109:3108]),.ntt_mode(cp[3107:3106]),.profile(cp[3105]),.inverse(cp[3104]),
      .tag(cp[3103:3072]),.data(cp[3071:1024]),.twiddle(cp[1023:0]),.in_ready(core_ready),.out_ready(out_ready),
      .out_valid(out_valid),.out_ntt(out_ntt),.out_width(out_width),.out_ntt_mode(out_ntt_mode),
      .out_profile(out_profile),.out_inverse(out_inverse),.out_tag(out_tag),.result(result));
endmodule
