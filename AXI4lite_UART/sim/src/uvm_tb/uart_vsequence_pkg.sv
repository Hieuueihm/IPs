package uart_vsequence_pkg;

import uvm_pkg::*;
`include "uvm_macros.svh"
`include "common_defines.sv"

import common_pkg::*;

import apb_agent_pkg::*;
import uart_agent_pkg::*;
import uart_reg_pkg::*;
import uart_env_pkg::*;

import apb_sequence_pkg::*;


class uart_vseq_base extends uvm_sequence #(uart_transaction);

`uvm_object_utils(uart_vseq_base)
apb_sequencer apb;
uart_sequencer uart;
uart_env_cfg cfg;

uart_agent_cfg tx_uart_config;
uart_agent_cfg rx_uart_config;
uart_env m_env;

uart_reg_block rm;

function new(string name = "uart_vseq_base");
  super.new(name);
endfunction

endclass

class basic_reg_vseq extends uart_vseq_base;

    `uvm_object_utils(basic_reg_vseq)

    function new(string name = "basic_reg_vseq");
    super.new(name);
    endfunction

    task body;

    quick_reg_access_seq t_seq = quick_reg_access_seq::type_id::create("t_seq");
    `uvm_info("run", "basic_reg_vseq running", UVM_LOW);
    t_seq.start(apb);

    endtask

endclass




  class uart_rx_seq extends uvm_sequence #(uart_transaction);

    `uvm_object_utils(uart_rx_seq)

    rand int no_rx_chars;

    rand bit[7:0] lcr_r;
    rand bit no_errors;
    bit fe_fixed;
    bit pe_fixed;

    function new(string name = "uart_rx_seq");
        super.new(name);
    endfunction

    task body;
        uart_transaction rx_char = uart_transaction::type_id::create("rx_char");
        // `uvm_info("RUNNING SEQUENCE", "RX SEQUENCE RUN", UVM_LOW);

        repeat(no_rx_chars) begin
            start_item(rx_char);
          assert(rx_char.randomize() with {
            data[4:0] != 0;
            pe dist {1 := 1, 0 := 9};
            fe dist {1 := 1, 0 := 9};
          });
            rx_char.lcr = lcr_r;
            // rx_char.data[7:0] = 8'h8d;
                    `uvm_info("RUNNING SEQUENCE", $sformatf("%h %h", rx_char.data, rx_char.lcr), UVM_LOW);

            if(no_errors) begin
                rx_char.fe = 0;
                rx_char.pe = 0;
            end
            if (fe_fixed) begin
              rx_char.fe = 1;
            end
            if(pe_fixed) begin
              rx_char.pe = 1;
            end
          finish_item(rx_char);
          // #10;
        end
    endtask

endclass



class tx_polling_vseq extends uart_vseq_base;

`uvm_object_utils(tx_polling_vseq)

function new(string name = "tx_polling_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_tx_seq host_tx = uart_host_tx_seq::type_id::create("host_tx");
  bit[4:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  bit [2:0] baud;

  int tx_cnt_before;


  tx_cnt_before = 0;
  baud = 0;
  lcr = 0;
  fcr = 0;
  ocr = 5; 

  host_tx.no_tx_chars =1;

  repeat(8) begin
      fcr = 0;
      lcr[4:0] = 0;
      repeat(32) begin
        assert(setup.randomize() with {setup.LCR[4:0] == lcr[4:0];
                                      setup.LCR[7:5] == baud[2:0];
                                      setup.FCR == fcr;
                                      setup.OCR == ocr;
                                      });
        setup.start(apb);
        tx_uart_config.lcr[4:0] = lcr[4:0];
        tx_uart_config.lcr[7:5] = baud[2:0];
        host_tx.s_cfg = setup;
        // host_tx.has_data_in = 1;
        // host_tx.data_in = 32'h13ec2483;


        fork
          host_tx.start(apb);
          wait(m_env.tx_sb.no_chars_tx == tx_cnt_before + 1);
        join
        tx_cnt_before = m_env.tx_sb.no_chars_tx;
        lcr++;
      end
      baud++;
    `LOG("TEST TX POOLING", "CHNAGE BAUD RATE")
  baud++;
  end
endtask

endclass



class tx_fifo_vseq extends uart_vseq_base;

`uvm_object_utils(tx_fifo_vseq)

function new(string name = "tx_fifo_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_tx_seq_wfifo host_tx = uart_host_tx_seq_wfifo::type_id::create("host_tx");
  bit[4:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  bit [2:0] baud;

  int tx_cnt_before;


  tx_cnt_before = 0;
  baud = 0;
  lcr = 0;
  fcr = 0;
  ocr = 5; 

  host_tx.no_tx_chars = 16;

  repeat(1) begin
      fcr = 1;
      lcr[4:0] = 0;
      repeat(1) begin
        assert(setup.randomize() with {setup.LCR[4:0] == lcr[4:0];
                                      setup.LCR[7:5] == baud[2:0];
                                      setup.FCR == fcr;
                                      setup.OCR == ocr;
                                      });
        setup.start(apb);
        tx_uart_config.lcr[4:0] = lcr[4:0];
        tx_uart_config.lcr[7:5] = baud[2:0];
        host_tx.s_cfg = setup;
        // host_tx.has_data_in = 1;
        // host_tx.data_in = 32'h13ec2483;


        fork
          host_tx.start(apb);
          wait(m_env.tx_sb.no_chars_tx == tx_cnt_before + 16);
        join
        tx_cnt_before = m_env.tx_sb.no_chars_tx;
        lcr++;
      end
    // `LOG("TEST TX POOLING", "CHNAGE BAUD RATE")
  baud++;
  end
endtask

endclass




class rx_polling_vseq extends uart_vseq_base;

`uvm_object_utils(rx_polling_vseq)

function new(string name = "rx_polling_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_rx_seq host_rx = uart_host_rx_seq::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  int rx_cnt_before;


  rx_cnt_before = 0;

  lcr = 0;
  fcr = 0;
  ocr = 5; 

  host_rx.no_rx_chars =1;
  rx_serial.no_rx_chars = 1;
  rx_serial.no_errors = 1;


  repeat(32) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    });
      setup.start(apb);
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;

      fork
        host_rx.start(apb);
        rx_serial.start(uart);
        wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      join
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      lcr++;
  end

endtask

endclass

class rx_fifo_vseq extends uart_vseq_base;

`uvm_object_utils(rx_fifo_vseq)

function new(string name = "rx_fifo_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_rx_seq_wfifo host_rx = uart_host_rx_seq_wfifo::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  int rx_cnt_before;


  rx_cnt_before = 0;

  lcr = 0;
  fcr = 1;
  ocr = 5; 

  host_rx.no_rx_chars =16;
  rx_serial.no_rx_chars = 16;
  rx_serial.no_errors = 1;


  repeat(1) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    });
      setup.start(apb);
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;

      fork
        rx_serial.start(uart);
        // host_rx.start(apb);

        // wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 16);
        
      join
      `LOG("RX FIFO VSEQ", $sformatf("RX COUNT BEFORE: %0d", rx_cnt_before))
      
      fork
        host_rx.start(apb);
        wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 16);

        
      join
    
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      lcr++;
  end

endtask

endclass




class rx_parity_vseq extends uart_vseq_base;

`uvm_object_utils(rx_parity_vseq)

function new(string name = "rx_parity_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_rx_seq_parity host_rx = uart_host_rx_seq_parity::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  int rx_cnt_before;


  rx_cnt_before = 0;

  lcr = 8'd8;
  fcr = 0;
  ocr = 5; 

  host_rx.no_rx_chars =1;
  rx_serial.no_rx_chars = 1;
  rx_serial.pe_fixed = 1;


  repeat(1) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    });
      setup.start(apb);
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;

      fork
        host_rx.start(apb);
        rx_serial.start(uart);
        wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      join
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      lcr++;
  end

endtask

endclass






class rx_frame_vseq extends uart_vseq_base;

`uvm_object_utils(rx_frame_vseq)

function new(string name = "rx_frame_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_rx_seq_frame host_rx = uart_host_rx_seq_frame::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  int rx_cnt_before;


  rx_cnt_before = 0;

  lcr = 8'd8;
  fcr = 0;
  ocr = 5; 

  host_rx.no_rx_chars =1;
  rx_serial.no_rx_chars = 1;
  rx_serial.fe_fixed = 1;


  repeat(1) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    });
      setup.start(apb);
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;

      fork
        host_rx.start(apb);
        rx_serial.start(uart);
        wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      join
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      lcr++;
  end

endtask

endclass

class rx_overrun_vseq extends uart_vseq_base;

`uvm_object_utils(rx_overrun_vseq)

function new(string name = "rx_overrun_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_rx_seq_overrun host_rx = uart_host_rx_seq_overrun::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  int rx_cnt_before;


  rx_cnt_before = 0;

  lcr = 0;
  fcr = 0;
  ocr = 5; 

  host_rx.no_rx_chars =1;
  rx_serial.no_rx_chars = 2;
  rx_serial.no_errors = 1;

  repeat(1) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    });
      setup.start(apb);
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;

      fork
        rx_serial.start(uart);
      join
      `LOG("RX OVERRUN VSEQ", $sformatf("RX COUNT BEFORE: %0d", rx_cnt_before))

      fork
        host_rx.start(apb);
        wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 2);
      join
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      lcr++;
  end

endtask

endclass



class interrupt_vseq extends uart_vseq_base;

`uvm_object_utils(interrupt_vseq)

function new(string name = "interrupt_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_intr_seq host = uart_host_intr_seq::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  bit [2:0] ier;
  int rx_cnt_before;


  rx_cnt_before = 0;
  ier = 3'b001;
  lcr = 0;
  fcr = 0;
  ocr = 5; 

  rx_serial.no_rx_chars = 1;
  rx_serial.no_errors = 1;


  repeat(3) begin
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    setup.IER == ier;
                                    });
      setup.start(apb);
      host.ier = ier;
      host.s_cfg = setup;
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;
      if(ier == 3'b100) begin
        rx_serial.fe_fixed = 1;
      end


      fork
        case(ier) 
          3'b001: begin
            rx_serial.start(uart);
              host.start(apb);

          end

          3'b010: begin
            host.start(apb);
          end

          3'b100: begin
            rx_serial.start(uart);
            host.start(apb);
          end

        endcase

        // wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      join
      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      // lcr++;
    ier = ier << 1; // test 

  end

endtask

endclass


class hf_vseq extends uart_vseq_base;

`uvm_object_utils(hf_vseq)

function new(string name = "hf_vseq");
  super.new(name);
endfunction

task body;
  uart_config_seq setup = uart_config_seq::type_id::create("setup");
  uart_host_hf_seq host = uart_host_hf_seq::type_id::create("host_rx");
  uart_rx_seq rx_serial = uart_rx_seq::type_id::create("rx_serial");

  bit[7:0] lcr;
  bit[4:0] fcr;
  bit[2:0] ocr;
  bit [2:0] ier;
  bit [1:0] hcr;
  int rx_cnt_before;


  rx_cnt_before = 0;
  // ier = 3'b001;
  hcr = 2'b1;
  lcr = 0;
  fcr = 0;
  ocr = 5; 

  rx_serial.no_rx_chars = 15;
  rx_serial.no_errors = 1;


  repeat(1) begin
      fcr= 5'b11001;
      assert(setup.randomize() with {setup.LCR == lcr;
                                    setup.FCR == fcr;
                                    setup.OCR == ocr;
                                    setup.IER == ier;
                                    setup.HCR == hcr;
                                    });
      setup.start(apb);
      host.ier = ier;
      host.s_cfg = setup;
      rx_uart_config.lcr = lcr;
      rx_serial.lcr_r = lcr;



      fork
        rx_serial.start(uart);
        // wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      
      join
        if(rx_uart_config.sline.handshake == 1) begin
          `LOG("HF VSEQ", "HANDSHAKE IS 1")
        end
      fork
        host.start(apb);
        // wait(m_env.rx_sb.no_chars_rx == rx_cnt_before + 1);
      
      join
        if(rx_uart_config.sline.handshake == 0) begin
          `LOG("HF VSEQ", "HANDSHAKE IS 0")
        end

      rx_cnt_before = m_env.rx_sb.no_chars_rx;

      // lcr++;
    // ier = ier << 1; // test 

  end

endtask

endclass


endpackage
