// Same arithmetic and external interface; isolate flow-control overhead.
`define STREAM_PORTS \
 input clk,rst,in_valid,ntt, input [1:0] width,ntt_mode, \
 input profile,inverse,input [31:0] tag,input [2047:0] data,input [1023:0] twiddle, \
 output in_ready,input out_ready,output out_valid,out_ntt,output [1:0] out_width,out_ntt_mode, \
 output out_profile,out_inverse,output [31:0] out_tag,output [2047:0] result
module stream_plain(`STREAM_PORTS);
 flex_stream_buffered #(.FIFO_ENABLE(0),.STALL_ENABLE(0)) u(.*);
endmodule
module stream_stall(`STREAM_PORTS);
 flex_stream_buffered #(.FIFO_ENABLE(0),.STALL_ENABLE(1)) u(.*);
endmodule
module stream_buffered(`STREAM_PORTS);
 flex_stream_buffered #(.FIFO_ENABLE(1),.STALL_ENABLE(1)) u(.*);
endmodule
`undef STREAM_PORTS
