
module mixcolumns (
    input  wire [127:0] in,
    output wire [127:0] out
);
    function [7:0] xt;
        input [7:0] x;
        xt = {x[6:0],1'b0} ^ (x[7] ? 8'h1b : 8'h00);
    endfunction

    genvar c;
    generate
        for (c = 0; c < 4; c = c + 1) begin : col
            wire [7:0] b0 = in[(3-c)*32+31 -: 8];
            wire [7:0] b1 = in[(3-c)*32+23 -: 8];
            wire [7:0] b2 = in[(3-c)*32+15 -: 8];
            wire [7:0] b3 = in[(3-c)*32+7  -: 8];

            wire [7:0] x0=xt(b0), x1=xt(b1), x2=xt(b2), x3=xt(b3);

            assign out[(3-c)*32+31 -: 8] = x0^(x1^b1)^b2^b3;
            assign out[(3-c)*32+23 -: 8] = b0^x1^(x2^b2)^b3;
            assign out[(3-c)*32+15 -: 8] = b0^b1^x2^(x3^b3);
            assign out[(3-c)*32+7  -: 8] = (x0^b0)^b1^b2^x3;
        end
    endgenerate
endmodule

module inv_mixcolumns (
    input  wire [127:0] in,
    output wire [127:0] out
);
    function [7:0] gmul;
        input [7:0] a, b;
        reg [7:0] p, aa; reg hi; integer k;
        begin
            p=0; aa=a;
            for(k=0;k<8;k=k+1) begin
                if(b[k]) p=p^aa;
                hi=aa[7]; aa=aa<<1; if(hi) aa=aa^8'h1b;
            end
            gmul=p;
        end
    endfunction

    genvar c;
    generate
        for (c = 0; c < 4; c = c + 1) begin : col
            wire [7:0] b0=in[(3-c)*32+31-:8], b1=in[(3-c)*32+23-:8];
            wire [7:0] b2=in[(3-c)*32+15-:8], b3=in[(3-c)*32+7 -:8];

            assign out[(3-c)*32+31-:8]=gmul(8'h0e,b0)^gmul(8'h0b,b1)^gmul(8'h0d,b2)^gmul(8'h09,b3);
            assign out[(3-c)*32+23-:8]=gmul(8'h09,b0)^gmul(8'h0e,b1)^gmul(8'h0b,b2)^gmul(8'h0d,b3);
            assign out[(3-c)*32+15-:8]=gmul(8'h0d,b0)^gmul(8'h09,b1)^gmul(8'h0e,b2)^gmul(8'h0b,b3);
            assign out[(3-c)*32+7 -:8]=gmul(8'h0b,b0)^gmul(8'h0d,b1)^gmul(8'h09,b2)^gmul(8'h0e,b3);
        end
    endgenerate
endmodule




