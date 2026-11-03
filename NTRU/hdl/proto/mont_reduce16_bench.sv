module mont_reduce16_bench #(
    parameter integer REDUCE_IMPL=0,FIXED_PROFILE=-1
) (
    input clk,rst,in_valid,input profile,input [15:0] tag,input [27:0] t,
    output reg out_valid,output reg out_profile,output reg [15:0] out_tag,
    output reg [15:0] residue
);
    wire qp=FIXED_PROFILE<0 ? profile : FIXED_PROFILE;
    reg v,qr;
    reg [15:0] tr;
    reg [27:0] value;
    always @(posedge clk) begin
        v<=!rst && in_valid; qr<=qp; tr<=tag;
        value<=qp ? {4'b0,t[23:0]} : t;
    end
    `include "mont_reduce16_functions.vh"
    always @(posedge clk) begin
        out_valid<=!rst && v; out_profile<=qr; out_tag<=tr;
        residue<=mont({4'b0,value},qr);
    end
endmodule
`define REDUCE_PORTS input clk,rst,in_valid,input profile,input [15:0] tag,input [27:0] t, \
    output out_valid,out_profile,output [15:0] out_tag,residue
module reduce_original_dynamic(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(0)) u(.*);
endmodule
module reduce_csa_dynamic(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(1)) u(.*);
endmodule
module reduce_compact_dynamic(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(2)) u(.*);
endmodule
module reduce_original_q12289(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(0),.FIXED_PROFILE(0)) u(.*);
endmodule
module reduce_csa_q12289(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(1),.FIXED_PROFILE(0)) u(.*);
endmodule
module reduce_compact_q12289(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(2),.FIXED_PROFILE(0)) u(.*);
endmodule
module reduce_original_q3329(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(0),.FIXED_PROFILE(1)) u(.*);
endmodule
module reduce_csa_q3329(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(1),.FIXED_PROFILE(1)) u(.*);
endmodule
module reduce_compact_q3329(`REDUCE_PORTS);
    mont_reduce16_bench #(.REDUCE_IMPL(2),.FIXED_PROFILE(1)) u(.*);
endmodule
`undef REDUCE_PORTS
