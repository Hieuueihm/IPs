// 64 independent synchronous 1R/1W banks. No reset of RAM contents.
// Word address: bank=(i&63)^((i>>2)&48)^((i>>4)&48), row=i>>6.
module flex_banked_scratch #(parameter ROW_BITS=7)(
    input clk,
    input [63:0] re,we,
    input [64*ROW_BITS-1:0] ra,wa,
    input [1023:0] wd,
    output [1023:0] rd
);
    genvar b;
    generate for(b=0;b<64;b=b+1)begin:bank
        (* ram_style="block" *) reg [15:0] mem[0:(1<<ROW_BITS)-1];
        reg [15:0] q;
        always @(posedge clk)begin
            if(we[b])mem[wa[b*ROW_BITS+:ROW_BITS]]<=wd[b*16+:16];
            if(re[b])q<=mem[ra[b*ROW_BITS+:ROW_BITS]];
        end
        assign rd[b*16+:16]=q;
    end endgenerate
endmodule
