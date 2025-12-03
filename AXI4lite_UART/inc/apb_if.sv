
interface apb_if(input clk,
                 input preset_n);
  logic psel; 
  logic penable;
  logic pwrite;
  logic pready;
  logic pslverr;
  logic[11:0] paddr;
  logic [3:0] pstrb;
  logic[31:0] prdata;
  logic[31:0] pwdata;


endinterface: apb_if