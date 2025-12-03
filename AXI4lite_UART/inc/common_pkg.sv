package common_pkg;
  
  typedef enum logic [11:0] {
    ADDR_TDR = 12'h000,
    ADDR_RDR = 12'h004,
    ADDR_LCR = 12'h008,
    ADDR_OCR = 12'h00C,
    ADDR_LSR = 12'h010,
    ADDR_FCR = 12'h014,
    ADDR_IER = 12'h018,
    ADDR_IIR = 12'h01C,
    ADDR_HCR = 12'h020
  } apb_addr_e;




    typedef enum {ZERO, SHORT, MEDIUM, LARGE, MAX} delay_e;


    function int get_baud_rate(bit [2:0] sel);
      case (sel)
        3'b000: return 4800;
        3'b001: return 9600;
        3'b010: return 14400;
        3'b011: return 19200;
        3'b100: return 38400;
        3'b101: return 57600;
        3'b110: return 115200;
        3'b111: return 230400;
        default: return 0;
      endcase
    endfunction
  
endpackage