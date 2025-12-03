
package uart_env_pkg;




import uvm_pkg::*;
`include "uvm_macros.svh"
`include "common_defines.sv"
import common_pkg::*;

import apb_agent_pkg::*;
import uart_agent_pkg::*;
import uart_reg_pkg::*;


class uart_env_cfg extends uvm_object;
    `uvm_object_utils(uart_env_cfg)
    apb_agent_cfg m_apb_agent_cfg;
    uart_agent_cfg m_tx_uart_agent_cfg;
    uart_agent_cfg m_rx_uart_agent_cfg;

    uart_reg_block rm;
    virtual interrupt_if IRQ;

    function new(string name = "UART_ENV_CFG");
        super.new(name);
    endfunction

    task wait_for_interrupt();
        @(posedge IRQ.irq);
    endtask


    task wait_for_clock(int n = 1);
        repeat (n) begin
            @(posedge IRQ.clk);
        end
    endtask

    function bit is_interrupt();
        return IRQ.irq;
    endfunction

    task wait_for_baud_rate();
        @(posedge IRQ.baud_o);
    endtask


endclass
class uart_tx_scoreboard extends uvm_component;
// behavioral -> apb send -> monitor capture -> send to scoreboard -> check
    `uvm_component_utils(uart_tx_scoreboard)

    uvm_tlm_analysis_fifo #(apb_transaction) apb_fifo;
    uvm_tlm_analysis_fifo #(uart_transaction) uart_fifo;

    uart_reg_block rm;


    int no_chars_written;
    int no_chars_tx;
    int no_data_errors;
    int no_errors;

    bit [7:0] data_q[$];

    
  function new(string name = "uart_tx_scoreboard", uvm_component parent = null);
    super.new(name, parent);
  endfunction


    function void build_phase(uvm_phase phase);
    apb_fifo = new("apb_fifo", this);
    uart_fifo = new("uart_fifo", this);
  endfunction


  task run_phase(uvm_phase phase);
        no_chars_written = 0;
        no_chars_tx = 0;
        no_data_errors = 0;
        no_errors = 0;

        fork
            monitor_apb;
            monitor_uart;
        join
        `LOG(`UART_TX_SCOREBOARD, "run_phase done");
  endtask


    task monitor_apb();
        // check whether the tx transaction is triggered by the apb transaction
        apb_transaction host_req;
             uvm_reg_data_t  lcr_reg;

        forever begin
            // 
            apb_fifo.get(host_req); 
            if((host_req.paddr == ADDR_TDR) & (host_req.pwrite == 1)) begin
                lcr_reg = rm.LCR.get();
                `LOG(`UART_TX_SCOREBOARD,  $sformatf("SENT DATA %h with LCR %h", host_req.pdata, lcr_reg[7:0]));
                no_chars_written++;
                data_q.push_back(host_req.pdata);
            end
        end
        
    endtask

    task monitor_uart();
        uart_transaction item;
        bit [7:0] data;
        uvm_reg_data_t  lcr_reg;
        forever begin
            uart_fifo.get(item);
            `LOG(`UART_TX_SCOREBOARD, $sformatf("UART TX SCOREBOARD received %h", item.data))
            // item.print();
            lcr_reg = rm.LCR.get();
            if(item.pe || item.fe) begin
                `uvm_error("monitor_uart", $sformatf("TX Data error detected: PE:%0b FE:%0b LCR:%0h", item.pe, item.fe, lcr_reg[7:0]))
                no_errors++;
            end
            if(data_q.size() > 0) begin
                data = data_q.pop_front();
            end
            case(lcr_reg[1:0]) 
                     2'b00: begin
                        if(data[4:0] != item.data[4:0]) begin
                            no_data_errors++;
                            `uvm_error("monitor_uart", $sformatf("Error in observed UART TX data expected:%0h actual:%0h LCR:%0h", data[4:0], item.data[4:0], lcr_reg[7:0]))
                        end
                        end
                2'b01: begin
                        if(data[5:0] != item.data[5:0]) begin
                            no_data_errors++;
                            `uvm_error("monitor_uart", $sformatf("Error in observed UART TX data expected:%0h actual:%0h LCR:%0h", data[5:0], item.data[5:0], lcr_reg[7:0]))
                        end
                        end
                2'b10: begin
                        if(data[6:0] != item.data[6:0]) begin
                            no_data_errors++;
                            `uvm_error("monitor_uart", $sformatf("Error in observed UART TX data expected:%0h actual:%0h LCR:%0h", data[6:0], item.data[6:0], lcr_reg[7:0]))
                        end
                        end
                2'b11: begin
                        if(data[7:0] != item.data[7:0]) begin
                            no_data_errors++;
                            `uvm_error("monitor_uart", $sformatf("Error in observed UART TX data expected:%0h actual:%0h LCR:%0h", data[7:0], item.data[7:0], lcr_reg[7:0]))
                        end
                        end

            endcase
            no_chars_tx++;

            // `LOG(`UART_TX_SCOREBOARD, $sformatf("UART TX SCOREBOARD report_item %h", report_item.lcr))
        end

    endtask

      function void report_phase(uvm_phase phase);

        if((no_errors == 0) && (no_data_errors == 0)) begin
        `uvm_info("report_phase", $sformatf("%0d characters transmitted from the UART with no errors", no_chars_written), UVM_LOW)
        end
        if(no_errors != 0) begin
        `uvm_error("report_phase", $sformatf("%0d characters transmitted with errors from %0d transmitted overall", no_errors, no_chars_written))
        end
        if(no_data_errors != 0) begin
        `uvm_error("report_phase", $sformatf("%0d characters transmitted with data_errors from %0d transmitted overall", no_data_errors, no_chars_written))
        end

    endfunction


endclass


class uart_rx_scoreboard extends uvm_component;

      `uvm_component_utils(uart_rx_scoreboard)
      
    uvm_tlm_analysis_fifo #(apb_transaction) apb_fifo;
    uvm_tlm_analysis_fifo #(uart_transaction) uart_fifo;

    uart_reg_block rm;

    int no_chars_rx;
    int no_data_errors;
    int no_errors;

    bit pe;
    bit fe;



    bit[9:0] data_q[$]; // include pe and fe

    function new(string name = "uart_rx_scoreboard", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        apb_fifo = new("apb_fifo", this);
        uart_fifo = new("uart_fifo", this);
    endfunction

    task run_phase(uvm_phase phase);
        no_chars_rx = 0;
        no_data_errors = 0;
        no_errors = 0;

        fork
            monitor_uart;
            monitor_apb;
        join

  endtask


    task monitor_uart();
        uart_transaction item;
        bit[7:0] data;
        forever begin
            uart_fifo.get(item);
            `LOG(`UART_RX_SCOREBOARD, $sformatf("UART RX SCOREBOARD received exp %h", item.data))
            data_q.push_back({item.pe, item.fe, item.data[7:0]});

        end 
    endtask

  task monitor_apb();
    apb_transaction host_req;
    bit [9:0] data;
    bit [7:0] msg;
    uvm_reg_data_t lcr_reg;

    forever begin

        apb_fifo.get(host_req);
        // read RDR register
            // `LOG(`UART_RX_SCOREBOARD, $sformatf("rce data"));
        if((host_req.paddr == ADDR_RDR) & (host_req.pwrite == 0)) begin
            // host_req.print();
            `LOG(`UART_RX_SCOREBOARD, $sformatf("READ DATA FROM REG %h", host_req.pdata))

            lcr_reg = rm.LCR.get();
            // `LOG(`UART_RX_SCOREBOARD, $sformatf("DATA QUEUE SIZE %d", data_q.size()))

            if(data_q.size() > 0) begin
                data = data_q.pop_front();
                pe = data[9];
                fe = data[8];
                msg = data[7:0];
                // `LOG(`UART_RX_SCOREBOARD, $sformatf("DATA COMPARE %h", msg))

            end 
        // has pe or fe
        if(data[9:8] != 0) begin
            `LOG(`UART_RX_SCOREBOARD, $sformatf("RX data error detected: PE:%0b FE:%0b LCR:%0h", data[9], data[8], lcr_reg[7:0]))
            no_errors++;
        end

        case(lcr_reg[1:0])
          2'b00: begin
                   if(msg[4:0] != host_req.pdata[4:0]) begin
                     no_data_errors++;
                     `uvm_error("monitor_uart", $sformatf("Error in observed UART RX data expected:%0h actual:%0h LCR:%b case %b", msg[4:0], host_req.pdata[4:0], lcr_reg[7:0], lcr_reg[1:0]))
                   end
                 end
          2'b01: begin
                   if(msg[5:0] != host_req.pdata[5:0]) begin
                     no_data_errors++;
                     `uvm_error("monitor_uart", $sformatf("Error in observed UART RX data expected:%0h actual:%0h LCR:%b  case %b", msg[5:0], host_req.pdata[5:0], lcr_reg[7:0], lcr_reg[1:0]))
                   end
                 end
          2'b10: begin
                   if(msg[6:0] != host_req.pdata[6:0]) begin
                     no_data_errors++;
                     `uvm_error("monitor_uart", $sformatf("Error in observed UART RX data expected:%0h actual:%0h LCR:%b  case %b", msg[6:0], host_req.pdata[6:0], lcr_reg[7:0], lcr_reg[1:0]))
                   end
                 end
          2'b11: begin
                   if(msg[7:0] != host_req.pdata[7:0]) begin
                     no_data_errors++;
                     `uvm_error("monitor_uart", $sformatf("Error in observed UART RX data expected:%0h actual:%0h LCR:%b case %b", msg[7:0], host_req.pdata[7:0], lcr_reg[7:0], lcr_reg[1:0]))
                   end
                 end
        endcase
                no_chars_rx++;

        
        end
    end




  endtask

  function void report_phase(uvm_phase phase);

    if( (no_data_errors == 0)) begin
      `uvm_info("report_phase", $sformatf("%0d characters received by the UART with %0d inserted errors", no_chars_rx, no_errors), UVM_LOW)
    end

    if(no_data_errors != 0) begin
      `uvm_error("report_phase", $sformatf("%0d characters received with data_errors from %0d received overall", no_data_errors, no_chars_rx))
    end

  endfunction

endclass



class uart_env extends uvm_component;

`uvm_component_utils(uart_env)

  uart_env_cfg m_cfg;

  apb_agent m_apb_agent;
  uart_agent m_tx_uart_agent;
  uart_agent m_rx_uart_agent;

  uart_tx_scoreboard tx_sb;
  uart_rx_scoreboard rx_sb;
  reg2apb_adapter reg_adapter;

  uvm_reg_predictor #(apb_transaction) reg_predictor;
  


  function new(string name = "UART_ENV", uvm_component parent = null);
    super.new(name, parent);
  endfunction


  function void build_phase(uvm_phase phase);
    if(!uvm_config_db #(uart_env_cfg)::get(this, "", `UART_ENV_CFG, m_cfg)) begin
      `uvm_error("build_phase", "Unable to get uart_env_cfg from uvm_config_db")
    end
    m_apb_agent = apb_agent::type_id::create("m_apb_agent", this);
    uvm_config_db #(apb_agent_cfg)::set(this, "m_apb_agent*", `APB_AGENT_CFG, m_cfg.m_apb_agent_cfg);
    m_tx_uart_agent = uart_agent::type_id::create("m_tx_uart_agent", this);
    uvm_config_db #(uart_agent_cfg)::set(this, "m_tx_uart_agent*", `UART_AGENT_CFG, m_cfg.m_tx_uart_agent_cfg);
    m_rx_uart_agent = uart_agent::type_id::create("m_rx_uart_agent", this);
    uvm_config_db #(uart_agent_cfg)::set(this, "m_rx_uart_agent*", `UART_AGENT_CFG, m_cfg.m_rx_uart_agent_cfg);

    reg_predictor = uvm_reg_predictor #(apb_transaction)::type_id::create("reg_predictor", this);
    reg_adapter = reg2apb_adapter::type_id::create("reg_adapter");

      tx_sb = uart_tx_scoreboard::type_id::create("tx_sb", this);
  rx_sb = uart_rx_scoreboard::type_id::create("rx_sb", this);

  endfunction

  function void connect_phase(uvm_phase phase);
    `LOG(`UART_ENV, "CONNECT PHASE")

    m_cfg.rm.map.set_sequencer(m_apb_agent.sequencer, reg_adapter);
    reg_predictor.map = m_cfg.rm.map;
    reg_predictor.adapter = reg_adapter;
    m_apb_agent.ap.connect(reg_predictor.bus_in);
    // tx scoreboard
      m_apb_agent.ap.connect(tx_sb.apb_fifo.analysis_export);
  m_tx_uart_agent.ap.connect(tx_sb.uart_fifo.analysis_export);
  tx_sb.rm = m_cfg.rm;
    // rx scoreboard
   m_apb_agent.ap.connect(rx_sb.apb_fifo.analysis_export);
  m_rx_uart_agent.ap.connect(rx_sb.uart_fifo.analysis_export);
  rx_sb.rm = m_cfg.rm;

  endfunction

endclass


endpackage