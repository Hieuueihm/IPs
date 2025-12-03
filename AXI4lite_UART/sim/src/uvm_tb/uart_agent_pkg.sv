package uart_agent_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  `include "common_defines.sv"

  function bit calParity(bit[7:0] lcr, bit[7:0] data);
    int num_bits;
    bit parity;
    parity = 0;
    case (lcr[1:0])
        2'b00: num_bits = 5;
        2'b01: num_bits = 6;
        2'b10: num_bits = 7;
        2'b11: num_bits = 8;
    endcase

    for (int i = 0; i < num_bits; i++)
        parity ^= data[i];

    if (lcr[4]) 
        return parity;
    else
        return ~parity;
endfunction


  class uart_agent_cfg extends uvm_object;

    `uvm_object_utils(uart_agent_cfg)
    virtual serial_if sline;
    rand logic [7:0] lcr;
    rand logic [2:0] ocr;
    rand logic [4:0] fcr;
    rand logic [2:0] ier;

    function new(string name = "UART_AGENT_CFG");
      super.new(name);
    endfunction
  endclass

  class uart_transaction extends uvm_sequence_item;


    rand logic [7:0] data;
    rand logic [7:0] lcr;

    rand logic fe;
    rand logic pe;

   	function new(string name = "uart_transaction");
	  super.new(name);
	endfunction

      `uvm_object_utils_begin(uart_transaction)
          `uvm_field_int(data, UVM_ALL_ON)
        `uvm_field_int(lcr, UVM_ALL_ON)
        `uvm_field_int(fe, UVM_ALL_ON)
        `uvm_field_int(pe, UVM_ALL_ON)

    `uvm_object_utils_end


  endclass



  class uart_sequencer extends uvm_sequencer #(uart_transaction);

    `uvm_component_utils(uart_sequencer)
    function new(string name, uvm_component parent);

      super.new(name, parent);

    endfunction


  endclass





  class uart_driver extends uvm_driver #(uart_transaction);

    `uvm_component_utils(uart_driver)

    // Declare variables first
    virtual serial_if sline;
    uart_transaction pkt;

    // Constructor
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        pkt = new("UART_PKT");
        `LOG(`UART_DRIVER, "UART DRIVER BUILD PHASE")
        
        
    endfunction
        integer bitPtr = 0;

    task run_phase(uvm_phase phase);
      if (sline == null)
            `uvm_fatal("NULL_IF", "serial_if interface (cfg.sline) is NULL. Make sure it was set properly using uvm_config_db::set.")
        else
            `uvm_info("IF_CHECK", "serial_if interface connected successfully.", UVM_LOW)
       begin
        sline.sdata = 1;
        sline.handshake = 0;
        forever
          begin
            sline.sdata = 1;
            seq_item_port.get_next_item(pkt);
            `uvm_info("UART DRIVER", "SEND SCHAR", UVM_LOW);
            // Start bit
            sline.sdata = 0;
            bitPtr = 0;
            bitPeriod;
            // Data bits 0 to 4
            while(bitPtr < 5)
              begin
                sline.sdata = pkt.data[bitPtr];
                bitPeriod;
                bitPtr++;
              end
            // Data bits 5 to 7
            if (pkt.lcr[1:0] > 2'b00)
              begin
                sline.sdata = pkt.data[5];

                bitPeriod;
              end
            if (pkt.lcr[1:0] > 2'b01)
              begin
                sline.sdata = pkt.data[6];  
                
                bitPeriod;
              end
            if (pkt.lcr[1:0] > 2'b10)
              begin
                sline.sdata = pkt.data[7];
                bitPeriod;
              end
            // Parity
            if (pkt.lcr[3])
              begin
                sline.sdata = logic'(calParity(pkt.lcr, pkt.data));
                if (pkt.pe) begin
                  sline.sdata = ~sline.sdata;
                  `LOG(`UART_DRIVER, $sformatf("send msg with parity error: %b", sline.sdata))

                end
                bitPeriod;

              end
            // Stop bit
            if (!pkt.fe)
              sline.sdata = 1;
            else begin
              `LOG(`UART_DRIVER, $sformatf("send msg with stopbit error: %b", pkt.fe))
              sline.sdata = 0;
            end
            bitPeriod; 
            if(pkt.lcr[2]) begin
              sline.sdata = 1;
              bitPeriod;
            end 

             seq_item_port.item_done();
          end
      end
    endtask

    task bitPeriod;
  begin
    repeat(16)
      @(posedge sline.tick_rx);
  end
endtask

endclass



  class uart_monitor extends uvm_monitor;
  
    `uvm_component_utils(uart_monitor)

    virtual serial_if sline;

    uvm_analysis_port #(uart_transaction) ap;

    function new(string name, uvm_component parent = null);

      super.new(name, parent);

    endfunction
    uart_agent_cfg cfg;
    uart_transaction s_char;




  	function void build_phase(uvm_phase phase);
        super.build_phase(phase);
	  if (!uvm_config_db #(uart_agent_cfg)::get(this, "", `UART_AGENT_CFG, cfg) )
	     `uvm_fatal("CONFIG_LOAD", "Cannot get() configuration uart_agent_config from uvm_config_db. Have you set() it?")
	    s_char = new("Serial_character");
      	  ap = new("ap", this);

      `LOG(`UART_MONITOR, "UART MONITOR BUILD PHASE")
      

	endfunction


    bit pe;
    bit fe;
    logic [7:0] data;
    logic parity;
    logic stop_bit;


    task receive_pkt();
        fe = 0;
        pe = 0;
        data = 0;
      while (sline.sdata !== 1'b1) begin
        @(posedge sline.clk);
      end
        while(sline.sdata == 1 || sline.sdata == 1'bx || sline.sdata == 1'bz) begin
          @(posedge sline.tick_rx);
        end
        // start bit detected


        repeat(23) @(posedge sline.tick_rx);
       data[0] = sline.sdata;
      bitPeriod;
      data[1] = sline.sdata;
      bitPeriod;
      data[2] = sline.sdata;
      bitPeriod;
      data[3] = sline.sdata;
      bitPeriod;
      data[4] = sline.sdata;
        if (cfg.lcr[1:0] > 2'b00) begin
          bitPeriod();
          data[5] = sline.sdata; 
      end
      if (cfg.lcr[1:0] > 2'b01) begin
        bitPeriod();
          data[6] = sline.sdata;
      end
      if (cfg.lcr[1:0] > 2'b10) begin
        bitPeriod();
          data[7] = sline.sdata;
      end

        if (cfg.lcr[3])
          begin
            bitPeriod;
            parity = sline.sdata;
            pe = logic'(calParity (cfg.lcr, data));
            // `LOG("UART MONITOR", $sformatf("parity %b", pe))
            if (pe != parity) begin
                `LOG(`UART_MONITOR, "UART MONITOR: parity error detected")
                `LOG(`UART_MONITOR, $sformatf("parity: %b expected %d datasend %h", parity, pe, data))
              pe = 1;
            end
            else
              pe = 0;
          end
          bitPeriod;
          if (sline.sdata == 1'b0) begin
            `LOG(`UART_MONITOR, "UART MONITOR: stop bit error detected")
            `LOG(`UART_MONITOR, $sformatf("stop bit: %b", sline.sdata))
            fe = 1;
          end
        // bitPeriod;
        repeat(8) @(posedge sline.tick_rx);
        if(cfg.lcr[2]) begin
            bitPeriod;
            if (sline.sdata == 1'b0) begin
              `LOG(`UART_MONITOR, "UART MONITOR: stop bit error detected")
              `LOG(`UART_MONITOR, $sformatf("stop bit: %b", sline.sdata))
              fe = 1;
            end
        end
    endtask

    
task bitPeriod;
  begin
    repeat(16)
      @(posedge sline.tick_rx);
  end
endtask


    task run_phase(uvm_phase phase);
        `LOG(`UART_MONITOR, "UART MONITOR RUN PHASE")
    
      forever begin
    
            receive_pkt();
            // 3 f -> 
            s_char = new("Serial_character");

            s_char.data = data;
            s_char.fe = fe;
            s_char.pe = pe;
              // `LOG(`UART_MONITOR, "UART MONITOR captured")

            ap.write(s_char);
    
        end

    endtask



  endclass

    class uart_agent extends uvm_agent;
    
        `uvm_component_utils(uart_agent)
    
        uart_driver    driver;
        uart_sequencer sequencer;
        uart_monitor   monitor;
        uart_agent_cfg    cfg;

        uvm_analysis_port #(uart_transaction) ap;
    
        function new(string name, uvm_component parent);
    
        super.new(name, parent);
    
        endfunction
    
        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            ap = new("ap", this);
            `LOG(`UART_AGENT, "UART AGENT BUILD PHASE")
            if (!uvm_config_db #(uart_agent_cfg)::get(this, "", `UART_AGENT_CFG, cfg) )
            `uvm_fatal("CONFIG_LOAD", "Cannot get() configuration uart_agent_config from uvm_config_db. Have you set() it?")
                
        if (cfg.sline == null)
            `uvm_fatal("NULL_IF", "serial_if interface (cfg.sline) is NULL. Make sure it was set properly using uvm_config_db::set.")
        else
            `uvm_info("IF_CHECK", "serial_if interface connected successfully.", UVM_LOW)
            driver = uart_driver::type_id::create("driver", this);
            sequencer = uart_sequencer::type_id::create("sequencer", this);
            monitor = uart_monitor::type_id::create("monitor", this);
         
        endfunction

        function void connect_phase(uvm_phase phase);
            super.connect_phase(phase);
            `LOG(`UART_AGENT, "UART AGENT CONNECT PHASE")
            monitor.sline = cfg.sline;
            driver.sline = cfg.sline;
            driver.seq_item_port.connect(sequencer.seq_item_export);

  
            monitor.ap.connect(ap);
        endfunction



    endclass    





endpackage































