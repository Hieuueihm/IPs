package uart_reg_pkg;

  import uvm_pkg::*;
  `include "uvm_macros.svh"
  `include "common_defines.sv"

  import common_pkg::*;

  // data.configure(

  // this,      // Parent register (this object)

  // 8,         // Number of bits in this field (width)

  // 0,         // LSB position (bit offset)

  // "WO",      // Access type: Write-Only ("RW", "RO", "WO", etc.)

  // 0,         // Volatility (0 = not volatile)

  // 8'h0,      // Reset value

  // 0,         // Has reset value? (0 = no, 1 = yes)

  // 1,         // Is it accessible? (1 = yes)

  // 0          // Is it individually resettable? (rarely used)

  // ) ;

  class tdr_reg extends uvm_reg;
    `uvm_object_utils(tdr_reg)

    rand uvm_reg_field data;
    rand uvm_reg_field rfu;

    function new(string name = "tdr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      data = uvm_reg_field::type_id::create("data");
      data.configure(this, 8, 0, "RW", 0, 8'h0, 0, 1, 0);
      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 24, 8, "WO", 0, 0, 1, 0, 0);

    endfunction
  endclass

  class rdr_reg extends uvm_reg;
    `uvm_object_utils(rdr_reg)

    uvm_reg_field data;
    uvm_reg_field rfu;

    function new(string name = "rdr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      data = uvm_reg_field::type_id::create("data");
      data.configure(this, 8, 0, "RO", 1, 8'h0, 0, 0, 0);
      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 24, 8, "RO", 0, 0, 1, 0, 0);
    endfunction
  endclass

  class lcr_reg extends uvm_reg;
    `uvm_object_utils(lcr_reg)

    rand uvm_reg_field DBN;
    rand uvm_reg_field SBN;
    rand uvm_reg_field PE;
    rand uvm_reg_field PT;
    rand uvm_reg_field BDR;
    rand uvm_reg_field rfu;

    function new(string name = "lcr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      DBN = uvm_reg_field::type_id::create("DBN");
      DBN.configure(this, 2, 0, "RW", 0, 2'b00, 1, 1, 0);
      SBN = uvm_reg_field::type_id::create("SBN");
      SBN.configure(this, 1, 2, "RW", 0, 1'b0, 1, 1, 0);
      PE = uvm_reg_field::type_id::create("PE");
      PE.configure(this, 1, 3, "RW", 0, 1'b0, 1, 1, 0);
      PT = uvm_reg_field::type_id::create("PT");
      PT.configure(this, 1, 4, "RW", 0, 1'b0, 1, 1, 0);
      BDR = uvm_reg_field::type_id::create("BDR");
      BDR.configure(this, 3, 5, "RW", 0, 3'b000, 1, 1, 0);
      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 24, 8, "WO", 0, 0, 1, 0, 0);
    endfunction

  endclass


  class ocr_reg extends uvm_reg;
    `uvm_object_utils(ocr_reg)

    rand uvm_reg_field RE;
    rand uvm_reg_field ST;
    rand uvm_reg_field TE;
    rand uvm_reg_field rfu;


    function new(string name = "ocr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      RE = uvm_reg_field::type_id::create("DBN");
      RE.configure(this, 1, 0, "RW", 0, 1'b0, 1, 1, 0);
      ST = uvm_reg_field::type_id::create("ST");
      ST.configure(this, 1, 1, "RW", 0, 1'b0, 1, 1, 0);
      TE = uvm_reg_field::type_id::create("TE");
      TE.configure(this, 1, 2, "RW", 0, 1'b0, 1, 1, 0);
      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 29, 3, "WO", 0, 0, 1, 0, 0);
    endfunction

  endclass

  class lsr_reg extends uvm_reg;
    `uvm_object_utils(lsr_reg)

    uvm_reg_field TD;
    uvm_reg_field RDRDY;
    uvm_reg_field FR;
    uvm_reg_field PERR;
    uvm_reg_field TDRE;
    uvm_reg_field FDE;
    uvm_reg_field OVE;
    uvm_reg_field rfu;


    function new(string name = "lsr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      TD = uvm_reg_field::type_id::create("TD");
      TD.configure(this, 1, 0, "RO", 1, 1'b0, 1, 0, 0);

      RDRDY = uvm_reg_field::type_id::create("RDRDY");
      RDRDY.configure(this, 1, 1, "RO", 1, 1'b0, 1, 0, 0);

      PERR = uvm_reg_field::type_id::create("PERR");
      PERR.configure(this, 1, 2, "RO", 1, 1'b0, 1, 0, 0);

      FR = uvm_reg_field::type_id::create("FR");
      FR.configure(this, 1, 3, "RO", 1, 1'b0, 1, 0, 0);

      TDRE = uvm_reg_field::type_id::create("TDRE");
      TDRE.configure(this, 1, 4, "RO", 1, 1'b0, 1, 0, 0);

      FDE = uvm_reg_field::type_id::create("FDE");
      FDE.configure(this, 1, 5, "RO", 1, 1'b0, 1, 0, 0);

      OVE = uvm_reg_field::type_id::create("OVE");
      OVE.configure(this, 1, 6, "RO", 1, 1'b0, 1, 0, 0);

      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 25, 7, "RO", 1, 0, 1, 0, 0);
    endfunction

  endclass


  class fcr_reg extends uvm_reg;
    `uvm_object_utils(fcr_reg)

    rand uvm_reg_field FIFOEN;
    rand uvm_reg_field RXR;
    rand uvm_reg_field TXR;
    rand uvm_reg_field FTL;
    rand uvm_reg_field rfu;


    function new(string name = "fcr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      FIFOEN = uvm_reg_field::type_id::create("FIFOEN");
      FIFOEN.configure(this, 1, 0, "RO", 0, 1'b0, 1, 1, 0);
      RXR = uvm_reg_field::type_id::create("RXR");
      RXR.configure(this, 1, 1, "RO", 0, 1'b0, 1, 1, 0);
      TXR = uvm_reg_field::type_id::create("TXR");
      TXR.configure(this, 1, 2, "RO", 0, 1'b0, 1, 1, 0);
      FTL = uvm_reg_field::type_id::create("FTL");
      FTL.configure(this, 2, 3, "RO", 0, 2'b00, 1, 1, 0);
      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 27, 5, "WO", 0, 0, 1, 0, 0);
    endfunction

  endclass
  class ier_reg extends uvm_reg;
    `uvm_object_utils(ier_reg)

    rand uvm_reg_field DRI;
    rand uvm_reg_field TEI;
    rand uvm_reg_field RLSI;

    rand uvm_reg_field rfu;

    function new(string name = "ier_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      DRI = uvm_reg_field::type_id::create("RDI");
      DRI.configure(this, 1, 0, "RW", 0, 0, 1, 1, 0);

      TEI = uvm_reg_field::type_id::create("TEI");
      TEI.configure(this, 1, 1, "RW", 0, 0, 1, 1, 0);

      RLSI = uvm_reg_field::type_id::create("RLSI");
      RLSI.configure(this, 1, 2, "RW", 0, 0, 1, 1, 0);


      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 29, 3, "WO", 0, 0, 1, 0, 0);
    endfunction

  endclass



  class iir_reg extends uvm_reg;
    `uvm_object_utils(iir_reg)

    uvm_reg_field INTRPEN;
    uvm_reg_field INTRID;

    uvm_reg_field rfu;

    function new(string name = "iir_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      INTRPEN = uvm_reg_field::type_id::create("INTRPEN");
      INTRPEN.configure(this, 1, 0, "RO", 1, 0, 1, 0, 0);
      INTRID = uvm_reg_field::type_id::create("INTRID");
      INTRID.configure(this, 2, 1, "RO", 1, 2'b00, 1, 0, 0);

      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 29, 3, "RO", 0, 0, 1, 0, 0);
    endfunction

  endclass



  class hcr_reg extends uvm_reg;
    `uvm_object_utils(hcr_reg)

    uvm_reg_field HEN;
    uvm_reg_field FRTS;

    uvm_reg_field rfu;

    function new(string name = "hcr_reg");
      super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    function void build();
      HEN = uvm_reg_field::type_id::create("HEN");
      HEN.configure(this, 1, 0, "RW", 0, 0, 1, 1, 0);
      FRTS = uvm_reg_field::type_id::create("FRTS");
      FRTS.configure(this, 1, 1, "RW", 0, 0, 1, 1, 0);

      rfu = uvm_reg_field::type_id::create("rfu");
      rfu.configure(this, 29, 2, "RO", 0, 0, 1, 0, 0);
    endfunction

  endclass



  class uart_reg_block extends uvm_reg_block;
    `uvm_object_utils(uart_reg_block)

    rand tdr_reg TDR;
    rand rdr_reg RDR;
    rand lcr_reg LCR;
    rand ocr_reg OCR;
    lsr_reg LSR;
    rand fcr_reg FCR;
    rand ier_reg IER;
    iir_reg IIR;
    rand hcr_reg HCR;

    uvm_reg_map map;

    function new(string name = "uart_reg_block");
      super.new(name, UVM_NO_COVERAGE);
    endfunction

    function void build();
      `uvm_info("build_phase", "UART register phase", UVM_LOW);

      TDR = tdr_reg::type_id::create("TDR");
      TDR.build();
      TDR.configure(this);

      RDR = rdr_reg::type_id::create("RDR");
      RDR.build();
      RDR.configure(this);

      LCR = lcr_reg::type_id::create("RDR");
      LCR.build();
      LCR.configure(this);

      OCR = ocr_reg::type_id::create("OCR");
      OCR.build();
      OCR.configure(this);

      LSR = lsr_reg::type_id::create("LSR");
      LSR.build();
      LSR.configure(this);

      FCR = fcr_reg::type_id::create("FCR");
      FCR.build();
      FCR.configure(this);

      IER = ier_reg::type_id::create("IER");
      IER.build();
      IER.configure(this);

      IIR = iir_reg::type_id::create("IIR");
      IIR.build();
      IIR.configure(this);

      HCR = hcr_reg::type_id::create("HCR");
      HCR.build();
      HCR.configure(this);


      map = create_map("map", 'h0, 4, UVM_LITTLE_ENDIAN);



      map.add_reg(TDR, ADDR_TDR, "RW");
      map.add_reg(RDR, ADDR_RDR, "RO");
      map.add_reg(LCR, ADDR_LCR, "RW");
      map.add_reg(OCR, ADDR_OCR, "RW");
      map.add_reg(LSR, ADDR_LSR, "RW");
      map.add_reg(FCR, ADDR_FCR, "RW");
      map.add_reg(IER, ADDR_IER, "RW");
      map.add_reg(IIR, ADDR_IIR, "RO");
      map.add_reg(HCR, ADDR_HCR, "RW");

      lock_model();
    endfunction

  endclass

endpackage
