module rd_calc(input clk,
               input rst_n,
               input [23:0] S_r2,
               input [23:0] S_r1,
               output bit_o);
    
    
    
    assign bit = (S_r2 < S_r1) ? 1'b0 : 1'b1;
    register #(.WIDTH(1)) register_bit (
    .clk(clk),
    .rst_n(rst_n),
    .D(bit),
    .Q(bit_o)
    );
    
    
endmodule