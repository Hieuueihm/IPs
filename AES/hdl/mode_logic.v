// ============================================================
//  mode_logic.v
//  Inputs:
//    din        [127:0] — plaintext (encrypt) or ciphertext (decrypt)
//    iv         [127:0] — IV current (CBC) or Counter current (CTR)
//    cipher_out [127:0] — output from AES cipher core 
//    mode       [1:0]   — 00=ECB, 01=CBC, 10=CTR
//    op                 — 0=encrypt, 1=decrypt
//
//  Outputs:
//    cipher_in  [127:0] — input to AES cipher core
//    dout       [127:0] — output to CPU / DOUT registers
//    iv_next    [127:0] — IV for next block (CBC) or next Counter (CTR)
//    iv_upd             — 1 pulse: CSR needs to update IV with iv_next
//
// ============================================================
module mode_logic (
    input  wire [127:0] din,       
    input  wire [127:0] iv,        
    input  wire [127:0] cipher_out, 
    input  wire [1:0]   mode,       
    input  wire         op,         

    output wire [127:0] cipher_in,   
    output wire [127:0] dout,        
    output wire [127:0] iv_next,   
    output wire         iv_upd       
);


    localparam ECB = 2'b00;
    localparam CBC = 2'b01;
    localparam CTR = 2'b10;


    assign cipher_in = (mode == CTR) ? iv            
                     : (mode == CBC && !op) ? din ^ iv 
                     :                        din;     

  
    assign dout = (mode == CTR)              ? cipher_out ^ din  // CTR: XOR keystream
                : (mode == CBC && op)        ? cipher_out ^ iv   // CBC dec: XOR with IV
                :                              cipher_out;       // ECB or CBC enc

    wire [127:0] ctr_next = {iv[127:32], iv[31:0] + 32'd1};

    assign iv_next = (mode == CTR)       ? ctr_next   
                   : (mode == CBC && !op) ? cipher_out 
                   : (mode == CBC &&  op) ? din        
                   :                       iv;         

   
    assign iv_upd = (mode != ECB);

endmodule