// File: apb_uart_tb.sv
`timescale 1ns / 1ps

import common_pkg::*; // Đảm bảo bạn đã định nghĩa các địa chỉ thanh ghi ở file này

module apb_uart_tb;

  // Tín hiệu chung
  logic clk;
  logic preset_n;

  // Tín hiệu APB cho TX
  logic        psel1, penable_t, pwrite_t;
  logic [11:0] paddr_t;
  logic [3:0]  pstrb_t;
  logic [31:0] pwdata_t;
  wire         pready_t, pslverr_t;
  wire [31:0]  prdata_t;
  wire         irq_t;
  wire         baud_o_t;

  // Tín hiệu APB cho RX
  logic        psel_r, penable_r, pwrite_r;
  logic [11:0] paddr_r;
  logic [3:0]  pstrb_r;
  logic [31:0] pwdata_r;
  wire         pready_r, pslverr_r;
  wire [31:0]  prdata_r;
  wire         irq_r;
  wire         baud_o_r;

  // UART line
  wire tx, rx;
  wire cts_n, rts_n;

  // Kết quả đọc
  logic [31:0] read_data;

  // Instance UART truyền
  apb_uart dut_tx (
    .pclk      (clk),
    .preset_n (preset_n),
    .psel     (psel1),
    .penable  (penable_t),
    .pwrite   (pwrite_t),
    .paddr    (paddr_t),
    .pstrb    (pstrb_t),
    .pwdata   (pwdata_t),
    .pready   (pready_t),
    .pslverr  (pslverr_t),
    .prdata   (prdata_t),
    .irq      (irq_t),
    .baud_o   (baud_o_t),
    .cts_n    (rts_n),
    .rx       (rx),
    .tx       (tx),
    .rts_n    (cts_n)
  );

  // Instance UART nhận
  apb_uart dut_rx (
    .pclk      (clk),
    .preset_n (preset_n),
    .psel     (psel_r),
    .penable  (penable_r),
    .pwrite   (pwrite_r),
    .paddr    (paddr_r),
    .pstrb    (pstrb_r),
    .pwdata   (pwdata_r),
    .pready   (pready_r),
    .pslverr  (pslverr_r),
    .prdata   (prdata_r),
    .irq      (irq_r),
    .baud_o   (baud_o_r),
    .cts_n    (cts_n),
    .rx       (tx),
    .tx       (rx),
    .rts_n    (rts_n)
  );

  always #10 clk = ~clk;

  // Reset và khởi tạo
  initial begin
    clk      = 0;
    preset_n = 0;

    psel1    = 0; penable_t = 0; pwrite_t = 0; paddr_t = 0; pstrb_t = 0; pwdata_t = 0;
    psel_r   = 0; penable_r = 0; pwrite_r = 0; paddr_r = 0; pstrb_r = 0; pwdata_r = 0;

    repeat(3) @(posedge clk);
    preset_n = 1;  // Hủy reset
    @(posedge clk);
  end

  task apb_write(input logic [11:0] addr, input logic [31:0] data, input [3:0] strb,
                 input logic is_tx);
    begin
      if (is_tx) begin
        pwrite_t = 1; paddr_t = addr; pwdata_t = data; pstrb_t = strb;
        @(posedge clk); psel1 = 1; penable_t = 0;
        @(posedge clk); penable_t = 1;
        wait(pready_t == 1); @(posedge clk);
        psel1 = 0; penable_t = 0;
      end else begin
        pwrite_r = 1; paddr_r = addr; pwdata_r = data; pstrb_r = strb;
        @(posedge clk); psel_r = 1; penable_r = 0;
        @(posedge clk); penable_r = 1;
        wait(pready_r == 1); @(posedge clk);
        psel_r = 0; penable_r = 0;
      end
    end
  endtask

  task apb_read(input logic [11:0] addr, output logic [31:0] data);
    begin
      paddr_r = addr; pstrb_r = 4'hF; pwrite_r = 0;
      @(posedge clk); psel_r = 1; penable_r = 0;
      @(posedge clk); penable_r = 1;
      wait(pready_r == 1); @(posedge clk);
      data = prdata_r;
      psel_r = 0; penable_r = 0;
    end
  endtask

  // Test case chính
  initial begin
    #100;

    $display("Cấu hình UART...");

    apb_write(ADDR_LCR, 32'h00000003, 4'h3, 1); // 8-bit
    apb_write(ADDR_FCR, 32'h00000001, 4'h1, 1); // FIFO on
    apb_write(ADDR_HCR, 32'h00000001, 4'h1, 1);
    apb_write(ADDR_OCR, 32'h00000005, 4'h1, 1); // TX_EN + RX_EN

    // Bên nhận cũng cần cấu hình tương tự
    apb_write(ADDR_LCR, 32'h00000003, 4'h3, 0);
    apb_write(ADDR_FCR, 32'h00000001, 4'h1, 0);
    apb_write(ADDR_HCR, 32'h00000001, 4'h1, 0);
    apb_write(ADDR_OCR, 32'h00000005, 4'h1, 0); // RX_EN

    $display("Gửi dữ liệu qua UART...");
    // for (int i = 1; i <= 5; i++) begin
      apb_write(ADDR_TDR, 32'd10, 4'h1, 1); // Gửi từ TX
      apb_write(ADDR_OCR, 32'h00000007, 4'h1, 1); // start_tx
    $display("Gửi dữ liệu qua UART....1.");
      #1000000; // Chờ truyền xong
      apb_read(ADDR_RDR, read_data);  // Đọc ở RX
      $display("Đã nhận tại RX: %0h", read_data);
    // end

    #200;
    $finish;
  end

  // VCD cho waveform
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, apb_uart_tb);
  end

endmodule