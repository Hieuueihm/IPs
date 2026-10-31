// Generated from reducer_compare.json selection; REDUCE_IMPL=2.
module radix2_delay #(parameter integer FIXED_MODE=-1,FIXED_PROFILE=-1)(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output reg out_valid,output reg [1:0] out_mode,output reg out_profile,out_inverse,
output reg [15:0] out_tag,output reg [127:0] result);
wire v,q,iv;wire [1:0] m;wire [15:0] t;wire [127:0] y;
flex_reduce_cluster #(.REDUCE_IMPL(2),.FIXED_MODE(FIXED_MODE),.FIXED_PROFILE(FIXED_PROFILE)) u(
 .clk(clk),.rst(rst),.in_valid(in_valid),.mode(mode),.profile(profile),.inverse(inverse),
 .tag(tag),.data(data),.twiddle(twiddle),.out_valid(v),.out_mode(m),
 .out_profile(q),.out_inverse(iv),.out_tag(t),.result(y));
always @(posedge clk) begin
 out_valid<=!rst&&v;out_mode<=m;out_profile<=q;out_inverse<=iv;out_tag<=t;result<=y;
end
endmodule
module radix2_shared3(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_reduce_cluster #(.REDUCE_IMPL(2)) u(.*);
endmodule
module radix2_shared4(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
radix2_delay u(.*);
endmodule
module radix4_shared4(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2)) u(.*);
endmodule
module radix2_pair4(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
radix2_delay #(.FIXED_MODE(1)) u(.*);
endmodule
module radix4_pair4(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.FIXED_MODE(1)) u(.*);
endmodule
module radix4_pair_q12289(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.FIXED_MODE(1),.FIXED_PROFILE(0)) u(.*);
endmodule
module radix4_pair_q3329(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.FIXED_MODE(1),.FIXED_PROFILE(1)) u(.*);
endmodule
module radix2_pair_q12289(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
radix2_delay #(.FIXED_MODE(1),.FIXED_PROFILE(0)) u(.*);
endmodule
module radix2_pair_q3329(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
radix2_delay #(.FIXED_MODE(1),.FIXED_PROFILE(1)) u(.*);
endmodule
module radix4_shared_epoch(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.SHARE_CONSTANT(1)) u(.*);
endmodule
module radix4_pair_epoch(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.SHARE_CONSTANT(1),.FIXED_MODE(1)) u(.*);
endmodule
module radix4_pair_epoch_q12289(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.SHARE_CONSTANT(1),.FIXED_MODE(1),.FIXED_PROFILE(0)) u(.*);
endmodule
module radix4_pair_epoch_q3329(
input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result);
flex_radix4_factor #(.REDUCE_IMPL(2),.SHARE_CONSTANT(1),.FIXED_MODE(1),.FIXED_PROFILE(1)) u(.*);
endmodule
