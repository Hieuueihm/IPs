// Synchronous ROM: one FFT complex root or one bundle per NTT bank each cycle.
`ifndef FLEX_ROM_DIR
`define FLEX_ROM_DIR "hdl/core/rom/"
`endif
module flex_kernel_rom(
    input clk,fft_en,input [9:0] fft_addr,
    output reg [127:0] fft_re,fft_im,
    input [15:0] ntt_en,input [79:0] ntt_addr,
    input profile,inverse,output [767:0] ntt_data
);
    reg [127:0] fr[0:1023],fi[0:1023];
    initial begin
        $readmemh({`FLEX_ROM_DIR,"fft_0.mem"},fr);
        $readmemh({`FLEX_ROM_DIR,"fft_1.mem"},fi);
    end
    always @(posedge clk)if(fft_en)begin fft_re<=fr[fft_addr];fft_im<=fi[fft_addr];end
    genvar b;
    generate for(b=0;b<16;b=b+1)begin:bank
        reg [47:0] f0[0:31],i0[0:31],f1[0:31],i1[0:31];
        reg [47:0] data;
        initial begin
            `include "hdl/core/rom/ntt_init.vh"
        end
        always @(posedge clk)if(ntt_en[b])
            data<=profile?(inverse?i1[ntt_addr[b*5+:5]]:f1[ntt_addr[b*5+:5]]):
                           (inverse?i0[ntt_addr[b*5+:5]]:f0[ntt_addr[b*5+:5]]);
        assign ntt_data[b*48+:48]=data;
    end endgenerate
endmodule
