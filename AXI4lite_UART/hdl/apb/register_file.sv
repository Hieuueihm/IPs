import common_pkg::*;

module register_file (
	input        clk,           // Clock
	input        reset_n,
	input [11:0] addr_i,
	input        wr_rd_i,
	input        en_i,
	input [31:0] pwdata_i,
	input [3:0]  byte_strobe_i,
	output logic [31:0] prdata_o,
	output logic [31:0] tdr_o,
	input [31:0] rdr_i,
	output logic [31:0] lcr_o,
	output logic [31:0] ocr_o,
	input [31:0] lsr_i,
	output logic [31:0] fcr_o,
	output logic [31:0] ier_o,
	input [31:0] iir_i,
  output logic [31:0] hcr_o,
	output logic        addr_err_o
);




  wire start_tx_pulse;
  assign start_tx_pulse = ocr_o[1];

  always_ff @(posedge clk) begin
    if (~reset_n) begin
      tdr_o       <= 32'b0;
      lcr_o       <= 32'b0;
      ocr_o       <= 32'b0;
      fcr_o       <= 32'b0;
      ier_o       <= 32'b0;
      hcr_o <=    32'b0;
      prdata_o    <= 32'b0;
      addr_err_o  <= 1'b0;
    end else begin
      addr_err_o <= 1'b0;
      if (start_tx_pulse) begin
        ocr_o[1] <= 1'b0; 
      end
      if (en_i & wr_rd_i) begin  // Write
        unique case (addr_i)
          ADDR_TDR: begin
            if (byte_strobe_i[0]) tdr_o[7:0]    <= pwdata_i[7:0];
            if (byte_strobe_i[1]) tdr_o[15:8]   <= pwdata_i[15:8];
            if (byte_strobe_i[2]) tdr_o[23:16]  <= pwdata_i[23:16];
            if (byte_strobe_i[3]) tdr_o[31:24]  <= pwdata_i[31:24];
          end

 

        ADDR_LCR: begin
          if (byte_strobe_i[0]) lcr_o[7:0]    <= pwdata_i[7:0];
          if (byte_strobe_i[1]) lcr_o[15:8]   <= pwdata_i[15:8];
          if (byte_strobe_i[2]) lcr_o[23:16]  <= pwdata_i[23:16];
          if (byte_strobe_i[3]) lcr_o[31:24]  <= pwdata_i[31:24];
        end

        ADDR_OCR: begin
          if (byte_strobe_i[0]) ocr_o[7:0]    <= pwdata_i[7:0];
          if (byte_strobe_i[1]) ocr_o[15:8]   <= pwdata_i[15:8];
          if (byte_strobe_i[2]) ocr_o[23:16]  <= pwdata_i[23:16];
          if (byte_strobe_i[3]) ocr_o[31:24]  <= pwdata_i[31:24];
        end


        ADDR_FCR: begin
          if (byte_strobe_i[0]) fcr_o[7:0]    <= pwdata_i[7:0];
          if (byte_strobe_i[1]) fcr_o[15:8]   <= pwdata_i[15:8];
          if (byte_strobe_i[2]) fcr_o[23:16]  <= pwdata_i[23:16];
          if (byte_strobe_i[3]) fcr_o[31:24]  <= pwdata_i[31:24];
        end


        ADDR_IER: begin
          if (byte_strobe_i[0]) ier_o[7:0]    <= pwdata_i[7:0];
          if (byte_strobe_i[1]) ier_o[15:8]   <= pwdata_i[15:8];
          if (byte_strobe_i[2]) ier_o[23:16]  <= pwdata_i[23:16];
          if (byte_strobe_i[3]) ier_o[31:24]  <= pwdata_i[31:24];
        end

      ADDR_HCR: begin
        if (byte_strobe_i[0]) hcr_o[7:0]    <= pwdata_i[7:0];
        if (byte_strobe_i[1]) hcr_o[15:8]   <= pwdata_i[15:8];
        if (byte_strobe_i[2]) hcr_o[23:16]  <= pwdata_i[23:16];
        if (byte_strobe_i[3]) hcr_o[31:24]  <= pwdata_i[31:24];
      end
      default: addr_err_o <= 1'b1;

    endcase
    end else if (en_i & !wr_rd_i) begin  // Read
        unique case (addr_i)
          ADDR_TDR: prdata_o <= tdr_o;
          ADDR_RDR: prdata_o <= rdr_i;
          ADDR_LCR: prdata_o <= lcr_o;
          ADDR_OCR: prdata_o <= ocr_o;
          ADDR_LSR: prdata_o <= lsr_i;
          ADDR_FCR: prdata_o <= fcr_o;
          ADDR_IER: prdata_o <= ier_o;
          ADDR_IIR: prdata_o <= iir_i;
          ADDR_HCR: prdata_o <= hcr_o;
          default: begin
            prdata_o   <= 32'b0;
            addr_err_o <= 1'b1;
          end
        endcase
      end
    end
  end

endmodule
