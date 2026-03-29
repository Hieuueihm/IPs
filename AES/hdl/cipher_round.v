module cipher_round (
    input  wire [127:0] state_in,
    input  wire [127:0] round_key,
    input  wire         is_first,
    input  wire         is_last,
    input  wire         decrypt,
    output wire [127:0] state_out
);

  
    wire [127:0] after_sub, after_inv_sub;
    subbytes     u_sub     (.in(state_in),  .out(after_sub));
    inv_subbytes u_inv_sub (.in(state_in),  .out(after_inv_sub));

    wire [127:0] sub_result = is_first ? state_in
                            : decrypt  ? after_inv_sub
                            :            after_sub;

    // ----------------------------------------------------------
    //  ShiftRows / InvShiftRows — wire reorder, 0 gate
    //
    //  Tên byte: s_row_col
    //    s00 = sub_result[127:120]  s01 = sub_result[95:88]
    //    s02 = sub_result[63:56]    s03 = sub_result[31:24]
    //    s10 = sub_result[119:112]  s11 = sub_result[87:80]
    //    s12 = sub_result[55:48]    s13 = sub_result[23:16]
    //    s20 = sub_result[111:104]  s21 = sub_result[79:72]
    //    s22 = sub_result[47:40]    s23 = sub_result[15:8]
    //    s30 = sub_result[103:96]   s31 = sub_result[71:64]
    //    s32 = sub_result[39:32]    s33 = sub_result[7:0]
    //
    //  ShiftRows (encrypt): output[row][col] = input[row][(col+row)%4]
    //    col0 output: {s00, s11, s22, s33}
    //    col1 output: {s01, s12, s23, s30}
    //    col2 output: {s02, s13, s20, s31}
    //    col3 output: {s03, s10, s21, s32}
    //
    //  InvShiftRows (decrypt): output[row][col] = input[row][(col-row+4)%4]
    //    col0 output: {s00, s13, s22, s31}
    //    col1 output: {s01, s10, s23, s32}
    //    col2 output: {s02, s11, s20, s33}
    //    col3 output: {s03, s12, s21, s30}
    // ----------------------------------------------------------
    wire [7:0] s00=sub_result[127:120], s01=sub_result[95:88];
    wire [7:0] s02=sub_result[63:56],   s03=sub_result[31:24];
    wire [7:0] s10=sub_result[119:112], s11=sub_result[87:80];
    wire [7:0] s12=sub_result[55:48],   s13=sub_result[23:16];
    wire [7:0] s20=sub_result[111:104], s21=sub_result[79:72];
    wire [7:0] s22=sub_result[47:40],   s23=sub_result[15:8];
    wire [7:0] s30=sub_result[103:96],  s31=sub_result[71:64];
    wire [7:0] s32=sub_result[39:32],   s33=sub_result[7:0];

    wire [127:0] sr_enc = {
        s00, s11, s22, s33,   // col0
        s01, s12, s23, s30,   // col1
        s02, s13, s20, s31,   // col2
        s03, s10, s21, s32    // col3
    };

    wire [127:0] sr_dec = {
        s00, s13, s22, s31,   // col0
        s01, s10, s23, s32,   // col1
        s02, s11, s20, s33,   // col2
        s03, s12, s21, s30    // col3
    };

    wire [127:0] shift_result = is_first ? state_in
                              : decrypt  ? sr_dec
                              :            sr_enc;

   
    wire [127:0] mixed, inv_mixed;
    mixcolumns     u_mix     (.in(shift_result), .out(mixed));
    inv_mixcolumns u_inv_mix (.in(shift_result), .out(inv_mixed));

    wire [127:0] mix_result = (is_first || is_last) ? shift_result
                            : decrypt               ? inv_mixed
                            :                         mixed;

    
    assign state_out = mix_result ^ round_key;

endmodule
