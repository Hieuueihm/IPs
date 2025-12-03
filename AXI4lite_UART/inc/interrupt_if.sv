interface interrupt_if #(parameter SYSTEM_FREQUENCY = 100000000) ();

	logic irq;
	logic clk;
	logic baud_o;
	
endinterface : interrupt_if