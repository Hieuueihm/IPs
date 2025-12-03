package apb_sequence_pkg;
	import uvm_pkg::*;
`include "uvm_macros.svh"
`include "common_defines.sv"

	import common_pkg::*;

import apb_agent_pkg::*;
import uart_reg_pkg::*;
import uart_env_pkg::*;


	class common_sequence extends uvm_sequence #(apb_transaction);
		`uvm_object_utils(common_sequence);
		uart_env_cfg cfg;
		uart_reg_block rm;


		uvm_status_e status;
		rand uvm_reg_data_t data;

        function new(string name = "common_sequence");
        super.new(name);
        endfunction

	task body;
        if(!uvm_config_db #(uart_env_cfg)::get(m_sequencer, "", `UART_ENV_CFG, cfg)) begin
            `uvm_error("body", "Unable to find uart_env_cfg in uvm_config_db")
        end
        rm = cfg.rm;
	 endtask

	endclass


	// to test
	class quick_reg_access_seq extends common_sequence;

	`uvm_object_utils(quick_reg_access_seq)

	function new(string name = "quick_reg_access_seq");
	  super.new(name);
	  `uvm_info("build phase", "create quick_reg_access_seq", UVM_LOW);
	endfunction

	task body;
	  super.body();
	 	`uvm_info("run phase", "quick_reg_access_seq running", UVM_LOW);

	  rm.TDR.read(status, data, .parent(this));

	  rm.RDR.read(status, data, .parent(this));
	  rm.LCR.read(status, data, .parent(this));
	  rm.OCR.read(status, data, .parent(this));
	  rm.LSR.read(status, data, .parent(this));
	  rm.FCR.read(status, data, .parent(this));
	  rm.IIR.read(status, data, .parent(this));
	  rm.IER.read(status, data, .parent(this));
	  rm.HCR.read(status, data, .parent(this));

	  // // write to all the registers
	  data = 32'haa;
	  rm.TDR.write(status, data, .parent(this));
	    `uvm_info("WRITE", $sformatf("TDR write: status=%0d, data=0x%0h", status, data), UVM_LOW);

	  rm.RDR.write(status, data, .parent(this));
	  rm.LCR.write(status, data, .parent(this));
	  rm.LSR.write(status, data, .parent(this));
	  rm.FCR.write(status, data, .parent(this));
	  rm.IER.write(status, data, .parent(this));
	  rm.OCR.write(status, data, .parent(this));
	  rm.HCR.write(status, data, .parent(this));
	  rm.IIR.write(status, data, .parent(this));

	  // read back again
	  rm.TDR.read(status, data, .parent(this));
	  rm.RDR.read(status, data, .parent(this));
	  rm.LCR.read(status, data, .parent(this));
	  rm.LSR.read(status, data, .parent(this));
	  rm.FCR.read(status, data, .parent(this));
	  rm.IER.read(status, data, .parent(this));
	  rm.OCR.read(status, data, .parent(this));
	  rm.HCR.read(status, data, .parent(this));
	  rm.IIR.read(status, data, .parent(this));

	endtask

	endclass

	class uart_config_seq extends common_sequence;

		`uvm_object_utils(uart_config_seq)

		rand bit[7:0] LCR;
		rand bit[4:0] FCR;
		rand bit[2:0] OCR;
		rand bit[2:0] IER;
		rand bit[1:0] HCR;

		function new(string name = "uart_config_seq");
		  super.new(name);
		endfunction

		task body;
		  super.body();
		  rm.LCR.write(status, {'0, LCR}, .parent(this));
		//   rm.LCR.read(status, data, .parent(this));
		  rm.FCR.write(status, {'0, FCR}, .parent(this));
		  			rm.HCR.write(status, {'0, HCR}, .parent(this));

			rm.IER.write(status, {'0, IER}, .parent(this));
		  
		  rm.OCR.write(status, {'0, OCR}, .parent(this));
		

		endtask

	endclass

	class uart_host_tx_seq extends common_sequence;

		`uvm_object_utils(uart_host_tx_seq)

		rand int no_tx_chars;
		int has_data_in = 0;
		bit [31:0] data_in;

		constraint char_limit_c { no_tx_chars inside {[1:20]};}
		uart_config_seq s_cfg;

		function new(string name = "uart_host_tx_seq");
		  super.new(name);
		endfunction

		task body;
			bit[7:0] data;
		  super.body();
		//   `LOG("TEST", "RUN TEST")
		// 	`LOG("TEST", $sformatf("%h", cfg.LCR[7:5]))

		    rm.LSR.read(status, data, .parent(this));

		    while(!data[4]) begin
	    		rm.LSR.read(status, data, .parent(this));
					
				end
		    for(int j = 0; j < no_tx_chars; j++) begin
		      rm.TDR.write(status,	has_data_in ? data_in : $urandom(), .parent(this));
			end
			// `uvm_info("TEST", $sformatf("cfg.OCR[2] = %0b", cfg.OCR[2]), UVM_MEDIUM);
			// `uvm_info("TEST", $sformatf("cfg.OCR = %03b", cfg.OCR), UVM_MEDIUM);

		      rm.OCR.write(status, {29'b0, s_cfg.OCR[2], 1'b1, s_cfg.OCR[0]}, .parent(this));
				while(!data[0]) begin
					rm.LSR.read(status, data, .parent(this));
				end
	endtask

	endclass


	class uart_host_tx_seq_wfifo extends common_sequence;

		`uvm_object_utils(uart_host_tx_seq_wfifo)

		rand int no_tx_chars;
		int has_data_in = 0;
		bit [31:0] data_in;

		constraint char_limit_c { no_tx_chars inside {[1:20]};}
		uart_config_seq s_cfg;

		function new(string name = "uart_host_tx_seq_wfifo");
		  super.new(name);
		endfunction

		task body;
			bit[7:0] data;
		  super.body();
		//   `LOG("TEST", "RUN TEST")
		// 	`LOG("TEST", $sformatf("%h", cfg.LCR[7:5]))

		    rm.LSR.read(status, data, .parent(this));

		    while(!data[4]) begin
	    		rm.LSR.read(status, data, .parent(this));	
			end
		     for(int j = 0; j < no_tx_chars; j++) begin
		      rm.TDR.write(status,	has_data_in ? data_in : $urandom(), .parent(this));
			 end
			// `uvm_info("TEST", $sformatf("cfg.OCR[2] = %0b", cfg.OCR[2]), UVM_MEDIUM);
			// `uvm_info("TEST", $sformatf("cfg.OCR = %03b", cfg.OCR), UVM_MEDIUM);

		      rm.OCR.write(status, {29'b0, s_cfg.OCR[2], 1'b1, s_cfg.OCR[0]}, .parent(this));
				// while(!data[0]) begin
				// 	rm.LSR.read(status, data, .parent(this));
				// end
			
	endtask

	endclass


	class uart_host_rx_seq extends common_sequence;

	`uvm_object_utils(uart_host_rx_seq)

	rand int no_rx_chars;
	event rx_data_event;

	constraint char_limit_c { no_rx_chars inside {[1:20]};}

	function new(string name = "uart_host_rx_seq");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  for(int i = 0; i < no_rx_chars; i++) begin
	    rm.LSR.read(status, data, .parent(this));
	    while(!data[1]) begin
	      rm.LSR.read(status, data, .parent(this));
	      cfg.wait_for_clock(10);
	    end

	    rm.RDR.read(status, data, .parent(this));
	  end
	endtask

	endclass

		class uart_host_rx_seq_wfifo extends common_sequence;

	`uvm_object_utils(uart_host_rx_seq_wfifo)

	rand int no_rx_chars;
	event rx_data_event;

	constraint char_limit_c { no_rx_chars inside {[1:20]};}

	function new(string name = "uart_host_rx_seq_wfifo");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  for(int i = 0; i < no_rx_chars; i++) begin
	    rm.LSR.read(status, data, .parent(this));
	    while(!data[1]) begin
	      rm.LSR.read(status, data, .parent(this));
	      cfg.wait_for_clock(10);
	    end
	   	 rm.RDR.read(status, data, .parent(this));
	  end
	endtask

	endclass

	
	class uart_host_rx_seq_parity extends common_sequence;

	`uvm_object_utils(uart_host_rx_seq_parity)

	rand int no_rx_chars;
	event rx_data_event;

	constraint char_limit_c { no_rx_chars inside {[1:20]};}

	function new(string name = "uart_host_rx_seq_parity");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  for(int i = 0; i < no_rx_chars; i++) begin
	    rm.LSR.read(status, data, .parent(this));
	    while(!data[2]) begin
	      rm.LSR.read(status, data, .parent(this));
		  cfg.wait_for_clock(10);
		//   `LOG("HOST_RX_SEQ_PARITY", $sformatf("LSR: %b", data))

	    end

		`LOG("HOST_RX_SEQ_PARITY", "PARITY ERROR DETECTED")
	   	 rm.RDR.read(status, data, .parent(this));

	    rm.LSR.read(status, data, .parent(this));
		if(!data[2]) begin
			`LOG("HOST_RX_SEQ_PARITY", "PARITY ERROR CLEARED AFTER READING LSR")
		end

	  end
	endtask

	endclass


		class uart_host_rx_seq_frame extends common_sequence;

	`uvm_object_utils(uart_host_rx_seq_frame)

	rand int no_rx_chars;
	event rx_data_event;

	constraint char_limit_c { no_rx_chars inside {[1:20]};}

	function new(string name = "uart_host_rx_seq_frame");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  for(int i = 0; i < no_rx_chars; i++) begin
	    rm.LSR.read(status, data, .parent(this));
	    while(!data[3]) begin
	      rm.LSR.read(status, data, .parent(this));
		  cfg.wait_for_clock(10);
		//   `LOG("HOST_RX_SEQ_PARITY", $sformatf("LSR: %b", data))

	    end

		`LOG("HOST_RX_SEQ_FRAME", "FRAME ERROR DETECTED")
	   	 rm.RDR.read(status, data, .parent(this));

	    rm.LSR.read(status, data, .parent(this));
		if(!data[3]) begin
			`LOG("HOST_RX_SEQ_FRAME", "FRAME ERROR CLEARED AFTER READING LSR")
		end

	  end
	endtask

	endclass




		class uart_host_rx_seq_overrun extends common_sequence;

	`uvm_object_utils(uart_host_rx_seq_overrun)

	rand int no_rx_chars;
	event rx_data_event;

	constraint char_limit_c { no_rx_chars inside {[1:20]};}

	function new(string name = "uart_host_rx_seq_overrun");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  for(int i = 0; i < no_rx_chars; i++) begin
	    rm.LSR.read(status, data, .parent(this));
	    while(!data[6]) begin
	      rm.LSR.read(status, data, .parent(this));
		  cfg.wait_for_clock(10);
		//   `LOG("HOST_RX_SEQ_PARITY", $sformatf("LSR: %b", data))
	    end

		`LOG("HOST_RX_SEQ_OVERRUN", "OVERRUN DETECTED")
	   	 rm.RDR.read(status, data, .parent(this));
		 rm.LSR.read(status, data, .parent(this));
		if(!data[6]) begin
			`LOG("HOST_RX_SEQ_FRAME", "OVERRUN ERROR CLEARED AFTER READING LSR")
		end
			
		rm.RDR.read(status, data, .parent(this));


	    

	  end
	endtask

	endclass

		class uart_host_intr_seq extends common_sequence;

	`uvm_object_utils(uart_host_intr_seq)

	event rx_data_event;
	bit [2:0] ier;
			uart_config_seq s_cfg;



	function new(string name = "uart_host_intr_seq");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	  case(ier) 
		3'b001: begin
			wait(cfg.IRQ.irq == 1);
			`LOG("HOST_INTR_SEQ", "INTERRUPT DETECTED")
			rm.IIR.read(status, data, .parent(this));
			`LOG("HOST_INTR_SEQ", $sformatf("IIR id: %b", data[2:1]))
			rm.RDR.read(status, data, .parent(this));
			

		end

		3'b010: begin
			rm.OCR.write(status, {29'b0, s_cfg.OCR[2], 1'b1, s_cfg.OCR[0]}, .parent(this));
			wait(cfg.IRQ.irq == 1);
			`LOG("HOST_INTR_SEQ", "INTERRUPT DETECTED")
						rm.IIR.read(status, data, .parent(this));

						`LOG("HOST_INTR_SEQ", $sformatf("IIR id: %b", data[2:1]))

			rm.RDR.read(status, data, .parent(this));

		end

		3'b100: begin
						wait(cfg.IRQ.irq == 1);
						`LOG("HOST_INTR_SEQ", "INTERRUPT DETECTED")
						rm.IIR.read(status, data, .parent(this));

						`LOG("HOST_INTR_SEQ", $sformatf("IIR id: %b", data[2:1]))

			rm.RDR.read(status, data, .parent(this));



		end

	  endcase
	
	endtask

	endclass



	class uart_host_hf_seq extends common_sequence;

	`uvm_object_utils(uart_host_hf_seq)

	event rx_data_event;
	bit [2:0] ier;
	uart_config_seq s_cfg;



	function new(string name = "uart_host_hf_seq");
	  super.new(name);
	endfunction

	task body;
	  super.body();
	   rm.LSR.read(status, data, .parent(this));
	    while(!data[1]) begin
	      rm.LSR.read(status, data, .parent(this));
	      cfg.wait_for_clock(10);
	    end
	   	 rm.RDR.read(status, data, .parent(this));

		  rm.LSR.read(status, data, .parent(this));
	    while(!data[1]) begin
	      rm.LSR.read(status, data, .parent(this));
	      cfg.wait_for_clock(10);
	    end
	   	 rm.RDR.read(status, data, .parent(this));


		 
		  rm.LSR.read(status, data, .parent(this));
	    while(!data[1]) begin
	      rm.LSR.read(status, data, .parent(this));
	      cfg.wait_for_clock(10);
	    end
	   	 rm.RDR.read(status, data, .parent(this));


	endtask

	endclass

endpackage 