module apb_slave (
	input clk,    
	input preset_n,  
	
	input psel,
	input penable,
	input pwrite,
	input[11:0] paddr,
	input[3:0] pstrb,
	input[31:0] pwdata,
	output pready,
	output pslverr,
	output[31:0] prdata,
	output [31:0] tdr,
	input  [31:0] rdr,
	output logic [31:0] lcr,
	output logic [31:0] ocr,
	input [31:0] lsr,
	output logic [31:0] fcr,
	output logic [31:0] ier,
	input [31:0] iir,
	output logic [31:0] hcr
);

	logic addr_err;
	
	logic register_access_en;
	apb_controller apb_controller_inst
		(
			.clk        (clk),
			.reset_n    (preset_n),
			.psel_i     (psel),
			.penable_i  (penable),
			.addr_err_i (addr_err),
			.pready_o   (pready),
			.act_en_o   (register_access_en),
			.pslverr_o  (pslverr)
		);
	register_file register_file_inst
		(
			.clk           (clk),
			.reset_n       (preset_n),
			.addr_i        (paddr),
			.wr_rd_i       (pwrite),
			.en_i          (register_access_en),
			.pwdata_i      (pwdata),
			.byte_strobe_i (pstrb),
			.prdata_o      (prdata),
			.tdr_o         (tdr),
			.rdr_i         (rdr),
			.lcr_o         (lcr),
			.ocr_o         (ocr),
			.lsr_i         (lsr),
			.fcr_o         (fcr),
			.ier_o         (ier),
			.iir_i         (iir),
	.hcr_o        (hcr),
			.addr_err_o    (addr_err)
		);


`ifdef SVA
	property SIGNAL_VALID(signal);
		@(posedge clk) !$isunknown(signal);
	endproperty;

	// check psel, penalbe, pwrite and preset_n valid
	RESET_VALID: assert property(SIGNAL_VALID(preset_n));
	PSEL_VALID : assert property(SIGNAL_VALID(psel));

	// control signal valid

	property CONTROL_SIGNAL_VALID(signal);
		@(posedge clk) psel |-> !$isunknown(signal);

	endproperty
	PADDR_VALID: assert property(CONTROL_SIGNAL_VALID(paddr));
	PWRITE_VALID: assert property(CONTROL_SIGNAL_VALID(pwrite));
	PENABLE_VALID: assert property(CONTROL_SIGNAL_VALID(penable));

	// write data valid
	property PWDATA_SIGNAL_VALID;
	  @(posedge clk)
	  (psel && pwrite) |-> !$isunknown(pwdata);
	endproperty

	PWDATA_VALID: assert property(PWDATA_SIGNAL_VALID);

	property PENABLE_SIGNAL_VALID(signal);
	  @(posedge clk)
	  $rose(penable) |-> !$isunknown(signal)[*1:$] ##1 $fell(penable);
	endproperty
	PREADY_VALID: assert property(PENABLE_SIGNAL_VALID(pready));
	PSLVERR_VALID: assert property(PENABLE_SIGNAL_VALID(pslverr));

	property PRDATA_SIGNAL_VALID;
	  @(posedge clk)
	  ($rose(penable && !pwrite && pready)) |-> !$isunknown(prdata)[*1:$] ##1 $fell(penable);
	endproperty

	property PENABLE_DEASSERTED;
	  @(posedge clk)
	  $rose(penable && pready) |=> !penable;
	endproperty

	property PSEL_TO_PENABLE_ACTIVE;
	  @(posedge clk)
	  ($rose(psel)) |=> penable;
	endproperty

	property PSEL_ASSERT_SIGNAL_STABLE(signal);
	  @(posedge clk)
	  ($rose(psel)) |=> $stable(signal)[*1:$] ##1 $fell(penable);
	endproperty
	PWRITE_STABLE: assert property(PSEL_ASSERT_SIGNAL_STABLE(pwrite));
	PADDR_STABLE: assert property(PSEL_ASSERT_SIGNAL_STABLE(paddr));
	PWDATA_STABLE: assert property(PSEL_ASSERT_SIGNAL_STABLE(pwdata & pwrite));
`endif

endmodule 