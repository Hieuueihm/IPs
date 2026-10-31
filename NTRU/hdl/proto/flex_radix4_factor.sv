// Four-edge, II1 radix4-factor experiment with all four cluster modes.
// Mode1 roots are [uR,u^2 R,u^3 R], not the paired-core root encoding.
// Forward c: 1479 (q12289), 1729 (q3329); inverse uses -c.
// Both pre/post constant paths are present for per-transaction CT/GS switching.
module flex_radix4_factor #(
    parameter integer REDUCE_IMPL=0,FIXED_MODE=-1,FIXED_PROFILE=-1,SHARE_CONSTANT=0
) (
    input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
    input [15:0] tag,input [127:0] data,input [63:0] twiddle,
    output reg out_valid,output reg [1:0] out_mode,
    output reg out_profile,out_inverse,output reg [15:0] out_tag,
    output reg [127:0] result
);
    function automatic [15:0] narrow(input [15:0] x,input q);
        narrow=q ? {4'b0,x[11:0]} : {2'b0,x[13:0]};
    endfunction
    function automatic [15:0] addq(input [15:0] a,b,input p);
        reg [16:0] s;reg [15:0] q,r;
        begin q=p?3329:12289;s={1'b0,a}+{1'b0,b};r=s>=q?s-q:s;addq=narrow(r,p);end
    endfunction
    function automatic [15:0] subq(input [15:0] a,b,input p);
        reg [15:0] q,r;
        begin q=p?3329:12289;r=a>=b?a-b:{1'b0,a}+q-{1'b0,b};subq=narrow(r,p);end
    endfunction
    `include "mont_reduce16_functions.vh"
    function automatic [15:0] fixed_i(input [15:0] x,input p,inv);
        reg [31:0] a,t;
        begin
            a={16'b0,x};
            if(p) t=inv ? (a<<10)-(a<<8)-(a<<3)-(a<<1) :
                          (a<<11)+(a<<9)+(a<<4)-(a<<2)-a;
            else t=inv ? (a<<13)-(a<<8)-(a<<6)+(a<<4) :
                         (a<<12)+(a<<8)+(a<<6)-(a<<4)+a;
            fixed_i=mont(t,p);
        end
    endfunction
    wire [1:0] sm=FIXED_MODE>=0?FIXED_MODE:mode;
    wire sq=FIXED_PROFILE>=0?FIXED_PROFILE:profile;
    reg [1:0] m0,m1,m2;
    reg q0,q1,q2,i0,i1,i2,v0,v1,v2;
    reg [15:0] tag0,tag1,tag2;
    reg [127:0] d0;
    reg [63:0] w0;
    genvar g;
    generate for(g=0;g<8;g=g+1)begin:g_input
        always @(posedge clk) d0[g*16+:16]<=sm==3?data[g*16+:16]:narrow(data[g*16+:16],sq);
        if(g<4)always @(posedge clk) w0[g*16+:16]<=narrow(twiddle[g*16+:16],sq);
    end endgenerate
    always @(posedge clk)begin
        m0<=sm;q0<=sq;i0<=inverse;tag0<=tag;v0<=!rst&&in_valid;
    end

    wire [15:0] x[0:7];
    generate for(g=0;g<8;g=g+1)begin:g_x
        assign x[g]=d0[g*16+:16];
    end endgenerate
    wire [15:0] ia=addq(x[0],x[1],q0),ib=subq(x[0],x[1],q0);
    wire [15:0] shared_fixed;
    wire [15:0] ic=addq(x[2],x[3],q0);
    wire [15:0] id=SHARE_CONSTANT ? shared_fixed : fixed_i(subq(x[2],x[3],q0),q0,1'b1);
    reg [63:0] ax,bx,aux;
    reg [15:0] a,b;
    integer j;
    always @*begin
        ax=0;bx=0;aux=0;a=0;b=0;
        if(m0==3)begin
            ax={x[1],x[0],x[1],x[0]};
            bx={x[2],x[3],x[3],x[2]};
        end else if(m0==1)begin
            ax[15:0]=i0?addq(ib,id,q0):x[1];
            ax[31:16]=i0?subq(ia,ic,q0):x[2];
            ax[47:32]=i0?subq(ib,id,q0):x[3];
            bx[47:0]=w0[47:0];
            aux[15:0]=i0?addq(ia,ic,q0):x[0];
        end else begin
            for(j=0;j<4;j=j+1)begin
                if(m0==0 || j<2)begin
                    if(m0==0 || i0)begin a=x[2*j];b=x[2*j+1];end
                    else begin a=x[j];b=x[j+2];end
                    ax[j*16+:16]=i0?subq(a,b,q0):b;
                    bx[j*16+:16]=w0[j*16+:16];
                    aux[j*16+:16]=i0?addq(a,b,q0):a;
                end
            end
        end
    end
    reg [63:0] ar,br,aux1,aux2;
    always @(posedge clk)begin
        ar<=ax;br<=bx;aux1<=aux;
        m1<=m0;q1<=q0;i1<=i0;tag1<=tag0;v1<=!rst&&v0;
        m2<=m1;q2<=q1;i2<=i1;tag2<=tag1;v2<=!rst&&v1;aux2<=aux1;
    end
    wire [32:0] raw[0:3];
    reg [32:0] prod[0:3];
    generate for(g=0;g<4;g=g+1)begin:g_mul
        mul_ss #(.W(16)) mul(ar[g*16+:16],br[g*16+:16],
            m1==3&&(g==1||g==3),m1==3&&(g==1||g==2),raw[g]);
        always @(posedge clk)prod[g]<=m1==3?raw[g]:{17'b0,mont(raw[g][31:0],q1)};
    end endgenerate
    wire [15:0] fa=addq(aux2[15:0],prod[1][15:0],q2);
    wire [15:0] fb=subq(aux2[15:0],prod[1][15:0],q2);
    wire [15:0] fc=addq(prod[0][15:0],prod[2][15:0],q2);
    wire [15:0] fd=SHARE_CONSTANT ? shared_fixed : fixed_i(subq(prod[0][15:0],prod[2][15:0],q2),q2,1'b0);
    // Optional epoch contract: profile/inverse must remain stable until all
    // in-flight transactions drain. One physical fixed-multiply/reducer then
    // serves inverse preprocessing OR forward postprocessing, at II1.
    assign shared_fixed=fixed_i(i0?subq(x[2],x[3],q0):subq(prod[0][15:0],prod[2][15:0],q2),
                               i0?q0:q2,i0);
    wire [63:0] factored=i2?{prod[2][15:0],prod[1][15:0],prod[0][15:0],aux2[15:0]}:
        {subq(fb,fd,q2),addq(fb,fd,q2),subq(fa,fc,q2),addq(fa,fc,q2)};
    wire [63:0] p00={{31{prod[0][32]}},prod[0]};
    wire [63:0] p11={prod[1][31:0],32'b0};
    wire [63:0] p01={{15{prod[2][32]}},prod[2],16'b0};
    wire [63:0] p10={{15{prod[3][32]}},prod[3],16'b0};
    wire [63:0] fft=p00+p11+p01+p10;
    wire [15:0] u[0:3],z[0:3];
    generate for(g=0;g<4;g=g+1)begin:g_output_bf
        assign u[g]=i2?aux2[g*16+:16]:addq(aux2[g*16+:16],prod[g][15:0],q2);
        assign z[g]=i2?prod[g][15:0]:subq(aux2[g*16+:16],prod[g][15:0],q2);
    end endgenerate
    always @(posedge clk)begin
        out_valid<=!rst&&v2;out_mode<=m2;out_profile<=q2;out_inverse<=i2;out_tag<=tag2;
        case(m2)
            0:result<={z[3],u[3],z[2],u[2],z[1],u[1],z[0],u[0]};
            1:result<={64'b0,factored};
            2:result<=i2?{64'b0,z[1],u[1],z[0],u[0]}:{64'b0,z[1],z[0],u[1],u[0]};
            3:result<={64'b0,fft};
        endcase
    end
endmodule
