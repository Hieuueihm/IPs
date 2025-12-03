module testbench();

import uvm_pkg::*;
import uart_test_pkg::*;
import common_pkg::*;
`include "common_defines.sv"

logic clk;
logic preset_n;

apb_if APB(.clk(clk), .preset_n(preset_n));
serial_if RX_UART();
serial_if TX_UART();
interrupt_if IRQ();
wire rts_n;
wire tick_rx;
wire tick_tx;

apb_uart DUT (
  // .clk(clk),
  // .reset_n(preset_n),

  .pclk(clk),
  .preset_n(preset_n),
  .paddr(APB.paddr),
  .pwdata(APB.pwdata),
  .prdata(APB.prdata),
  .pwrite(APB.pwrite),
  .penable(APB.penable),
  .psel(APB.psel),
  .pready(APB.pready),
  .pslverr(APB.pslverr),
  .pstrb(APB.pstrb),
  .irq(IRQ.irq),
  
  .tx(TX_UART.sdata),
  .rx(RX_UART.sdata),
  .cts_n   (TX_UART.handshake),
  .rts_n (RX_UART.handshake),
  .baud_o(tick_tx),
  .tick_rx(tick_rx)
  );
  // apb_assertion apb_assertion_inst(
  //   .clk(clk),    
  //   .preset_n(preset_n),  
  //   .psel(APB.psel),
  //   .penable(APB.penable),
  //   .pwrite(APB.pwrite),
  //   .paddr(APB.paddr),
  //   .pstrb   (APB.pstrb),
  //   .pwdata(APB.pwdata),
  //   .prdata(APB.prdata),
  //   .pready(APB.pready),
  //   .pslverr(APB.pslverr)
  // );



// UVM virtual interface handling and run_test()
initial begin
  uvm_config_db #(virtual apb_if)::set(null, "uvm_test_top", "APB", APB);
  uvm_config_db #(virtual serial_if)::set(null, "uvm_test_top", "RX_UART", RX_UART);
  uvm_config_db #(virtual serial_if)::set(null, "uvm_test_top", "TX_UART", TX_UART);
  uvm_config_db #(virtual interrupt_if)::set(null, "uvm_test_top", "IRQ", IRQ);
  run_test("test_reg_access");
end


initial begin
  clk = 0;
  preset_n = 0;
  repeat(10) begin
    #1ns clk = ~clk;
  end
  preset_n = 1;
  forever begin
    #1ns clk = ~clk;
  end


end

assign IRQ.clk = clk;
assign IRQ.baud_o = tick_tx;
assign RX_UART.tick_tx = tick_tx;
assign RX_UART.tick_rx = tick_rx;
assign RX_UART.clk = clk;

assign TX_UART.tick_tx = tick_tx;
assign TX_UART.tick_rx = tick_rx;
assign TX_UART.clk = clk;

initial begin
          $dumpfile("dump_uvm.vcd");
          $dumpvars;
          #10s;
          $finish;
end 

endmodule