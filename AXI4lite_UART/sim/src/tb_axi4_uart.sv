`timescale 1ns/1ps

module tb_axi4_uart;

  reg clk = 0;
  always #5 clk = ~clk;  // 100MHz clock

  reg rst_n;

  // AXI-Lite signals
    // AXI-Lite signals
  reg [31:0]  s_axi_awaddr;
  reg        s_axi_awvalid;
  wire       s_axi_awready;
  reg [31:0] s_axi_wdata;
  reg [3:0]  s_axi_wstrb;
  reg        s_axi_wvalid;
  wire       s_axi_wready;
  wire [1:0] s_axi_bresp;
  wire       s_axi_bvalid;
  reg        s_axi_bready;
  reg [31:0]  s_axi_araddr;
  reg        s_axi_arvalid;
  wire       s_axi_arready;
  wire [31:0] s_axi_rdata;
  wire [1:0]  s_axi_rresp;
  wire        s_axi_rvalid;
  reg         s_axi_rready;


  wire irq;
  wire sline;
  logic cts_n = 1'b0;
  wire rts_n;


  axi4_uart inst_axi4_uart (
      .clk           (clk),
      .rst_n         (rst_n),
      .s_axi_awaddr  (s_axi_awaddr),
      .s_axi_awvalid (s_axi_awvalid),
      .s_axi_awready (s_axi_awready),
      .s_axi_wdata   (s_axi_wdata),
      .s_axi_wstrb   (s_axi_wstrb),
      .s_axi_wvalid  (s_axi_wvalid),
      .s_axi_wready  (s_axi_wready),
      .s_axi_bresp   (s_axi_bresp),
      .s_axi_bvalid  (s_axi_bvalid),
      .s_axi_bready  (s_axi_bready),
      .s_axi_araddr   (s_axi_araddr),
      .s_axi_arvalid (s_axi_arvalid),
      .s_axi_arready (s_axi_arready),
      .s_axi_rdata   (s_axi_rdata),
      .s_axi_rresp   (s_axi_rresp),
      .s_axi_rvalid  (s_axi_rvalid),
      .s_axi_rready  (s_axi_rready),
      .irq           (irq),
      .cts_n         (cts_n),
      .rx            (sline),
      .tx            (sline),
      .rts_n         (rts_n)
    );






   task axi_read(input logic [31:0] addr);
          begin
              s_axi_araddr  = addr;
              s_axi_arvalid = 1;
              @(posedge clk);
              while (!s_axi_arready) @(posedge clk);
              s_axi_arvalid = 0;

              s_axi_rready = 1;
              @(posedge clk);
              while (!s_axi_rvalid) @(posedge clk);
              $display("[READ ] Addr = 0x%08X, Data = 0x%08X", addr, s_axi_rdata);
              s_axi_rready = 0;
          end
      endtask
    task axi_write(input logic [31:0] addr, input logic [31:0] data);
        begin
            // Write address
            s_axi_awaddr  = addr;
            s_axi_awvalid = 1;
            // Write data
            s_axi_wdata   = data;
            s_axi_wstrb   = 4'hF;
            s_axi_awvalid = 1'b1;
            @(posedge clk);
            @(posedge clk);
            s_axi_awvalid = 0;
            while(!s_axi_wready) @(posedge clk);
            s_axi_wvalid  = 1;
            s_axi_bready = 1;
            @(posedge clk);
            s_axi_wvalid  = 0;

            // Wait for bvalid
            @(posedge clk);
            while (!s_axi_bvalid) @(posedge clk);
            s_axi_bready = 0;
            $display("[WRITE] Addr = 0x%08X, Data = 0x%08X", addr, data);
        end
    endtask

 
  initial begin
    $dumpfile("axi4_uart.vcd");
    $dumpvars(0, tb_axi4_uart);


    // Reset
    rst_n = 0;
    s_axi_awaddr = 0; s_axi_awvalid = 0;
    s_axi_wdata  = 0; s_axi_wstrb = 0; s_axi_wvalid = 0;
    s_axi_bready = 0;
    s_axi_araddr = 0; s_axi_arvalid = 0; s_axi_rready = 0;


    #20 rst_n = 1;
    #20;


    $display("Cấu hình UART...");

    axi_write({20'd0, ADDR_LCR}, 32'h00000003); 
    axi_write({20'd0, ADDR_FCR}, 32'h00000001); 
    axi_write({20'd0, ADDR_HCR}, 32'h00000000);
    axi_write({20'd0, ADDR_OCR}, 32'h00000005); 

  

    $display("Gửi dữ liệu qua UART...");
    // for (int i = 1; i <= 5; i++) begin
      axi_write({20'd0, ADDR_TDR}, 32'd10); // Gửi từ TX
      axi_write({20'd0, ADDR_OCR}, 32'h00000007); // start_tx
      axi_write({20'd0, ADDR_TDR}, 32'd11); // Gửi từ TX

    $display("Gửi dữ liệu qua UART....1.");
      #1000000; // Chờ truyền xong
    axi_read({20'd0, ADDR_RDR});    // end
    axi_read({20'd0, ADDR_RDR});    // end

    #200;
    $finish;

   
  end

endmodule


