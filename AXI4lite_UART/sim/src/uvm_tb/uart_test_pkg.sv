package uart_test_pkg;

import uvm_pkg::*;
`include "uvm_macros.svh"
`include "common_defines.sv"

import common_pkg::*;

import uart_reg_pkg::*;
import uart_agent_pkg::*;
import apb_agent_pkg::*;

import uart_env_pkg::*;
import uart_vsequence_pkg::*;
import apb_sequence_pkg::*;


class uart_test_base extends uvm_test;

`uvm_component_utils(uart_test_base)

uart_env m_env;
uart_env_cfg m_env_cfg;
uart_reg_block rm;

uart_agent_cfg m_tx_uart_cfg;
uart_agent_cfg m_rx_uart_cfg;
apb_agent_cfg m_apb_cfg;



  function new(string name = "uart_test_base", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  function void build_phase(uvm_phase phase);
    `uvm_info("build phase", "uart_test_base build", UVM_LOW);
    m_env_cfg = uart_env_cfg::type_id::create("m_env_cfg");

    rm = uart_reg_block::type_id::create("rm");
    rm.build();
    m_env_cfg.rm = rm;

    m_apb_cfg = apb_agent_cfg::type_id::create("m_apb_cfg");
    if(!uvm_config_db #(virtual apb_if)::get(this, "", "APB", m_apb_cfg.APB)) begin
      `uvm_error("build_phase", "Unable to find APB interface in the uvm_config_db")
    end
    m_env_cfg.m_apb_agent_cfg = m_apb_cfg;
    m_tx_uart_cfg = uart_agent_cfg::type_id::create("m_tx_uart_cfg");
    if(!uvm_config_db #(virtual serial_if)::get(this, "", "TX_UART", m_tx_uart_cfg.sline)) begin
      `uvm_error("build_phase", "Unable to find UART interface in the uvm_config_db")
    end
    m_env_cfg.m_tx_uart_agent_cfg = m_tx_uart_cfg;
    m_rx_uart_cfg = uart_agent_cfg::type_id::create("m_rx_uart_cfg");
    if(!uvm_config_db #(virtual serial_if)::get(this, "", "RX_UART", m_rx_uart_cfg.sline)) begin
      `uvm_error("build_phase", "Unable to find UART interface in the uvm_config_db")
    end
    m_env_cfg.m_rx_uart_agent_cfg = m_rx_uart_cfg;
    if(!uvm_config_db #(virtual interrupt_if)::get(this, "", "IRQ", m_env_cfg.IRQ)) begin
      `uvm_error("build_phase", "Unable to find IRQ interface in the uvm_config_db")
    end
    m_env = uart_env::type_id::create("m_env", this);
    uvm_config_db #(uart_env_cfg)::set(this, "m_env*", `UART_ENV_CFG, m_env_cfg);
  endfunction

  function void init_vseq(uart_vseq_base vseq);
    `uvm_info("init", "init_vseq", UVM_LOW);
    vseq.apb = m_env.m_apb_agent.sequencer;
    vseq.uart = m_env.m_rx_uart_agent.sequencer;
    vseq.rm = rm;
    vseq.tx_uart_config = m_tx_uart_cfg;
    vseq.rx_uart_config = m_rx_uart_cfg;
    vseq.cfg = m_env_cfg;
    vseq.m_env = m_env; 
  endfunction
endclass



// test read and write regs
class test_reg_access extends uart_test_base;

`uvm_component_utils(test_reg_access)

  function new(string name = "test_reg_access", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);

    basic_reg_vseq vseq = basic_reg_vseq::type_id::create("vseq");
            `uvm_info("run_phase", "run_phase OF UART TEST", UVM_LOW);

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);

  endtask

  function void report_phase(uvm_phase phase);
    `uvm_info("*** UVM TEST PASSED ***", "Register RW paths checked", UVM_LOW)
  endfunction
endclass





class tx_polling_test extends uart_test_base;

`uvm_component_utils(tx_polling_test)

  function new(string name = "tx_polling_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    tx_polling_vseq vseq = tx_polling_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if((m_env.tx_sb.no_errors == 0) && (m_env.tx_sb.no_data_errors == 0)) begin
      `uvm_info("*** UVM TEST PASSED ***", "No TX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "TX data errors detected - see scoreboard reports for more detail")
    end
  endfunction
endclass



  class tx_fifo_test extends uart_test_base;

  `uvm_component_utils(tx_fifo_test)

    function new(string name = "tx_fifo_test", uvm_component parent = null);
      super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
      tx_fifo_vseq vseq = tx_fifo_vseq::type_id::create("vseq");

      phase.raise_objection(this);
      init_vseq(vseq);
      vseq.start(null);
      phase.drop_objection(this);
    endtask


    function void report_phase(uvm_phase phase);
      if((m_env.tx_sb.no_errors == 0) && (m_env.tx_sb.no_data_errors == 0)) begin
        `uvm_info("*** UVM TEST PASSED ***", "No TX data errors detected", UVM_LOW)
      end
      else begin
        `uvm_error("*** UVM TEST FAILED ***", "TX data errors detected - see scoreboard reports for more detail")
      end
    endfunction
  endclass



class rx_polling_test extends uart_test_base;

`uvm_component_utils(rx_polling_test)

  function new(string name = "rx_polling_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    rx_polling_vseq vseq = rx_polling_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass



class rx_fifo_test extends uart_test_base;

`uvm_component_utils(rx_fifo_test)

  function new(string name = "rx_fifo_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    rx_fifo_vseq vseq = rx_fifo_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass



class parity_error_test extends uart_test_base;

`uvm_component_utils(parity_error_test)

  function new(string name = "parity_error_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    rx_parity_vseq vseq = rx_parity_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass


class frame_error_test extends uart_test_base;

`uvm_component_utils(frame_error_test)

  function new(string name = "frame_error_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    rx_frame_vseq vseq = rx_frame_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass


  class overrun_error_test extends uart_test_base;

`uvm_component_utils(overrun_error_test)

  function new(string name = "overrun_error_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    rx_overrun_vseq vseq = rx_overrun_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass



  class interrupt_test extends uart_test_base;

`uvm_component_utils(interrupt_test)

  function new(string name = "interrupt_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    interrupt_vseq vseq = interrupt_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction
  endclass


  

  class hf_test extends uart_test_base;

`uvm_component_utils(hf_test)

  function new(string name = "hf_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    hf_vseq vseq = hf_vseq::type_id::create("vseq");

    phase.raise_objection(this);
    init_vseq(vseq);
    vseq.start(null);
    phase.drop_objection(this);
  endtask


  function void report_phase(uvm_phase phase);
    if(m_env.rx_sb.no_data_errors == 0) begin
      `uvm_info("*** UVM TEST PASSED ***", "No RX data errors detected", UVM_LOW)
    end
    else begin
      `uvm_error("*** UVM TEST FAILED ***", "RX data errors detected - see scoreboard reports for more detail")
    end
  endfunction


  endclass















endpackage
