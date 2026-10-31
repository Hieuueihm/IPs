// Four shared 16x16 leaves, physically split over two registered compute stages.
// mode 0: four independent NTT butterflies, data = (A0,B0,...,A3,B3).
// mode 1: two adjacent NTT layers on four coefficients, data[63:0].
// mode 2: first layer only on four coefficients; second layer is bypassed.
// mode 3: exact signed 32x32 product, data = {unused64, b32, a32}.
// profile 0: q=12289; profile 1: q=3329. Canonical data and w*2^16 roots.
// inverse selects GS; otherwise CT. No normalization inside the cluster.
// Pair CT: (0,2),(1,3) then (0,1),(2,3).
// Pair GS: (0,1),(2,3) then (0,2),(1,3).
// Mode 1 uses three roots: [common, distinct0, distinct1] in low 48 bits.
// CT shares the first-layer root; GS shares the second-layer root.
// Three sampled edges, II=1, no ready/stall. Mode 2 has the same latency.
module flex_ntt_cluster #(
    parameter integer HAS_FFT=1, HAS_CASCADE=1,
    parameter integer FIXED_MODE=-1, FIXED_PROFILE=-1, SHORT_PARALLEL=0
) (
    input wire clk,rst,in_valid,
    input wire [1:0] mode,
    input wire profile,inverse,
    input wire [15:0] tag,
    input wire [127:0] data,
    input wire [63:0] twiddle,
    output reg out_valid,
    output reg [1:0] out_mode,
    output reg out_profile,out_inverse,
    output reg [15:0] out_tag,
    output reg [127:0] result
);
    wire [1:0] selected_mode=FIXED_MODE>=0 ? FIXED_MODE :
        (HAS_FFT && mode==3) ? 2'd3 :
        HAS_CASCADE ? (mode==3 ? 2'd0 : mode) : 2'd0;
    wire selected_profile=FIXED_PROFILE>=0 ? FIXED_PROFILE : profile;
    // Exact width specialization for canonical residues, never FFT truncation.
    wire [127:0] input_data;
    wire [63:0] input_twiddle;
    genvar limb;
    generate for(limb=0;limb<8;limb=limb+1) begin:g_input_width
        wire [15:0] narrow=selected_profile ? {4'b0,data[16*limb+:12]} :
                                                        {2'b0,data[16*limb+:14]};
        assign input_data[16*limb+:16]=selected_mode==3 ? data[16*limb+:16] : narrow;
        if(limb<4) begin:g_root
            assign input_twiddle[16*limb+:16]=selected_profile ? {4'b0,twiddle[16*limb+:12]} :
                                                               {2'b0,twiddle[16*limb+:14]};
        end
    end endgenerate
    reg v0,v1;
    reg [1:0] m0,m1;
    reg q0,q1,i0,i1;
    reg [15:0] tag0,tag1;
    reg [127:0] d0;
    reg [63:0] w0;
    always @(posedge clk) begin
        v0<=!rst && in_valid; m0<=selected_mode;
        q0<=selected_profile; i0<=inverse; tag0<=tag;
        d0<=input_data; w0<=input_twiddle;
    end

    function automatic [15:0] addq(input [15:0] a,b,input profile_bit);
        reg [16:0] s;
        reg [15:0] q,r;
        begin
            q=profile_bit ? 16'd3329 : 16'd12289;
            s={1'b0,a}+{1'b0,b};
            r=s>=q ? s-q : s[15:0];
            addq=profile_bit ? {4'b0,r[11:0]} : {2'b0,r[13:0]};
        end
    endfunction
    function automatic [15:0] subq(input [15:0] a,b,input profile_bit);
        reg [15:0] q,r;
        begin
            q=profile_bit ? 16'd3329 : 16'd12289;
            r=a>=b ? a-b : {1'b0,a}+q-{1'b0,b};
            subq=profile_bit ? {4'b0,r[11:0]} : {2'b0,r[13:0]};
        end
    endfunction
    function automatic [15:0] mont(input [31:0] t,input profile_bit);
        reg [15:0] m,q,r;
        reg [29:0] me,mq,s;
        reg [14:0] u;
        begin
            q=profile_bit ? 16'd3329 : 16'd12289;
            m=profile_bit ? (t[15:0]<<12)-(t[15:0]<<10)+(t[15:0]<<8)-t[15:0] :
                            (t[15:0]<<14)-(t[15:0]<<12)-t[15:0];
            me={14'b0,m};
            mq=profile_bit ? (me<<12)-(me<<10)+(me<<8)+me :
                             (me<<14)-(me<<12)+me;
            s={2'b0,t[27:0]}+mq;
            u={1'b0,s[29:16]};
            r=u>=q ? u-q : u;
            mont=profile_bit ? {4'b0,r[11:0]} : {2'b0,r[13:0]};
        end
    endfunction

    wire [15:0] a0[0:1],b0[0:1],la0[0:1],lb0[0:1];
    wire [32:0] p0[0:1];
    wire [15:0] u0[0:1],z0[0:1];
    genvar k;
    generate for(k=0;k<2;k=k+1) begin:g_first
        assign a0[k]=m0==0 || i0 ? d0[k*32+:16] : d0[k*16+:16];
        assign b0[k]=m0==0 || i0 ? d0[k*32+16+:16] : d0[(k+2)*16+:16];
        assign la0[k]=m0==3 ? d0[k*16+:16] :
                       i0 ? subq(a0[k],b0[k],q0) : b0[k];
        assign lb0[k]=m0==3 ? d0[32+k*16+:16] :
                      m0==1 ? (i0 ? w0[(k+1)*16+:16] : w0[15:0]) : w0[k*16+:16];
        mul_ss #(.W(16)) mul(la0[k],lb0[k],m0==3 && k==1,m0==3 && k==1,p0[k]);
        wire [15:0] t=mont(p0[k][31:0],q0);
        assign u0[k]=i0 ? addq(a0[k],b0[k],q0) : addq(a0[k],t,q0);
        assign z0[k]=i0 ? t : subq(a0[k],t,q0);
    end endgenerate

    reg [63:0] first,tail;
    reg [31:0] roots;
    reg [63:0] fft_args;
    reg [32:0] pp00,pp11;
    generate if(SHORT_PARALLEL) begin:g_short_parallel
      always @* begin
        v1=v0; m1=m0; q1=q0; i1=i0; tag1=tag0;
        first={z0[1],u0[1],z0[0],u0[0]};
        tail=d0[127:64]; roots=w0[63:32];
        fft_args=d0[63:0]; pp00=p0[0]; pp11=p0[1];
      end
    end else begin:g_registered_pair
      always @(posedge clk) begin
        v1<=!rst && v0; m1<=m0; q1<=q0; i1<=i0; tag1<=tag0;
        // Preserve natural coefficient ordering in a paired layer.
        first<=m0==0 || i0 ? {z0[1],u0[1],z0[0],u0[0]} :
                             {z0[1],z0[0],u0[1],u0[0]};
        tail<=d0[127:64];
        roots<=m0==1 ? (i0 ? {2{w0[15:0]}} : w0[47:16]) : w0[63:32];
        fft_args<=d0[63:0]; pp00<=p0[0]; pp11<=p0[1];
      end
    end endgenerate

    wire [15:0] a1[0:1],b1[0:1],la1[0:1],lb1[0:1];
    wire [32:0] p1[0:1];
    wire [15:0] u1[0:1],z1[0:1];
    generate for(k=0;k<2;k=k+1) begin:g_second
        assign a1[k]=m1==0 ? tail[k*32+:16] :
                      i1 ? first[k*16+:16] : first[k*32+:16];
        assign b1[k]=m1==0 ? tail[k*32+16+:16] :
                      i1 ? first[(k+2)*16+:16] : first[k*32+16+:16];
        assign la1[k]=m1==3 ? fft_args[k*16+:16] :
                       i1 ? subq(a1[k],b1[k],q1) : b1[k];
        assign lb1[k]=m1==3 ? fft_args[32+(1-k)*16+:16] : roots[k*16+:16];
        mul_ss #(.W(16)) mul(la1[k],lb1[k],m1==3 && k==1,m1==3 && k==0,p1[k]);
        wire [15:0] t=mont(p1[k][31:0],q1);
        assign u1[k]=i1 ? addq(a1[k],b1[k],q1) : addq(a1[k],t,q1);
        assign z1[k]=i1 ? t : subq(a1[k],t,q1);
    end endgenerate
    wire [63:0] second=i1 ? {z1[1],z1[0],u1[1],u1[0]} :
                            {z1[1],u1[1],z1[0],u1[0]};
    // Exact integer product: do not round either partial product stage.
    wire [63:0] f00={{31{pp00[32]}},pp00};
    wire [63:0] f11={pp11[31:0],32'b0};
    wire [63:0] f01={{15{p1[0][32]}},p1[0],16'b0};
    wire [63:0] f10={{15{p1[1][32]}},p1[1],16'b0};
    wire [63:0] fused=f00+f11+f01+f10;
    wire [63:0] parallel_second={z1[1],u1[1],z1[0],u1[0]};
    always @(posedge clk) begin
        out_valid<=!rst && v1; out_mode<=m1;
        out_profile<=q1; out_inverse<=i1; out_tag<=tag1;
        result<=m1==3 ? {64'b0,fused} : m1==0 ? {parallel_second,first} :
                m1==2 ? {64'b0,first} : {64'b0,second};
    end
endmodule

`define CLUSTER_PORTS \
    input clk,rst,in_valid,input [1:0] mode,input profile,inverse, \
    input [15:0] tag,input [127:0] data,input [63:0] twiddle, \
    output out_valid,output [1:0] out_mode,output out_profile,out_inverse, \
    output [15:0] out_tag,output [127:0] result
module cluster_ntt_parallel(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0),.HAS_CASCADE(0)) u(.*);
endmodule
module cluster_ntt_pair_only(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0),.FIXED_MODE(1)) u(.*);
endmodule
module cluster_ntt_configurable(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0)) u(.*);
endmodule
module cluster_flex_parallel(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_CASCADE(0)) u(.*);
endmodule
module cluster_flex_pair(`CLUSTER_PORTS);
    flex_ntt_cluster u(.*);
endmodule
module cluster_ntt_pair_q12289(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0),.FIXED_MODE(1),.FIXED_PROFILE(0)) u(.*);
endmodule
module cluster_ntt_pair_q3329(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0),.FIXED_MODE(1),.FIXED_PROFILE(1)) u(.*);
endmodule
module cluster_ntt_pair_bypass(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0)) u(.mode(mode==2 ? 2'd2 : 2'd1),.*);
endmodule
// Fair low-latency dedicated baseline: all four butterflies in one compute stage.
module cluster_ntt_parallel_short(`CLUSTER_PORTS);
    flex_ntt_cluster #(.HAS_FFT(0),.HAS_CASCADE(0),.FIXED_MODE(0),.SHORT_PARALLEL(1)) u(.*);
endmodule
`undef CLUSTER_PORTS
