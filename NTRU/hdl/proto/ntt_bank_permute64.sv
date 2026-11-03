// 64-bank gather/scatter for the XOR bank map in model/ntt_banked_supply.py.
// A paired warp has lane bits [p,p+1,lowest four remaining address bits].
// A tail warp has stride p plus five independent bank columns; CT swaps the
// first two lane bits. The upper-bank XOR accounts for the warp's fixed bits.
// No SRAM, row address generator, root RAM, or stage controller is included.
module ntt_bank_permute64(
    input [1023:0] bank_read,logical_write,
    input [63:0] logical_mask,
    input [3:0] low_stride,
    input [1:0] bank_xor,
    input tail,inverse,
    output [1023:0] logical_read,bank_write,
    output [63:0] bank_mask
);
    function automatic integer permutation(input integer lane,kind);
        integer i,p,col;
        begin
            p=kind%6;
            if(kind<6)begin
                case(p)
                0:permutation=lane;
                1:permutation={lane[5],lane[4],lane[3],lane[1],lane[0],lane[2]};
                2:permutation={lane[5],lane[4],lane[1],lane[0],lane[3],lane[2]};
                3:permutation={lane[5],lane[1],lane[0],lane[4],lane[3],lane[2]};
                4:permutation={lane[1],lane[0],lane[5],lane[4],lane[3],lane[2]};
                5:permutation={lane[0],lane[1],lane[5],lane[4],lane[3],lane[2]};
                endcase
            end else begin
                permutation=(lane&1)<<p;
                for(i=1;i<6;i=i+1)begin
                    col=i>p?i:i-1;
                    permutation=permutation|(((lane>>i)&1)<<col);
                end
            end
        end
    endfunction
    function automatic integer reverse_permutation(input integer bank,kind);
        integer i,p,col;
        begin
            p=kind%6;
            if(kind<6)begin
                case(p)
                0:reverse_permutation=bank;
                1:reverse_permutation={bank[5],bank[4],bank[3],bank[0],bank[2],bank[1]};
                2:reverse_permutation={bank[5],bank[4],bank[1],bank[0],bank[3],bank[2]};
                3:reverse_permutation={bank[5],bank[2],bank[1],bank[0],bank[4],bank[3]};
                4:reverse_permutation={bank[3],bank[2],bank[1],bank[0],bank[5],bank[4]};
                5:reverse_permutation={bank[3],bank[2],bank[1],bank[0],bank[4],bank[5]};
                endcase
            end else begin
                reverse_permutation=(bank>>p)&1;
                for(i=1;i<6;i=i+1)begin
                    col=i>p?i:i-1;
                    reverse_permutation=reverse_permutation|(((bank>>col)&1)<<i);
                end
            end
        end
    endfunction
    wire [2:0] pclass=low_stride<4?low_stride[2:0]:(low_stride[0]?3'd5:3'd4);
    wire [3:0] kind=(tail?4'd6:4'd0)+pclass;
    wire swap=tail&&!inverse;
    wire [15:0] read_x0[0:63],read_x1[0:63],gather[0:63],write_basic[0:63],scatter[0:63],write_x0[0:63];
    wire mask_basic[0:63],mask_scatter[0:63],mask_x0[0:63];
    genvar l,c;
    generate for(l=0;l<64;l=l+1)begin:g_lane
        localparam integer SW=(l&60)|((l&1)<<1)|((l&2)>>1);
        assign read_x0[l]=bank_xor[0]?bank_read[(l^16)*16+:16]:bank_read[l*16+:16];
        assign read_x1[l]=bank_xor[1]?read_x0[l^32]:read_x0[l];
        wire [15:0] read_choices[0:11],write_choices[0:11];
        wire mask_choices[0:11];
        for(c=0;c<12;c=c+1)begin:g_choice
            assign read_choices[c]=read_x1[permutation(l,c)];
            assign write_choices[c]=write_basic[reverse_permutation(l,c)];
            assign mask_choices[c]=mask_basic[reverse_permutation(l,c)];
        end
        assign gather[l]=read_choices[kind];
        assign logical_read[l*16+:16]=swap?gather[SW]:gather[l];
        assign write_basic[l]=swap?logical_write[SW*16+:16]:logical_write[l*16+:16];
        assign mask_basic[l]=swap?logical_mask[SW]:logical_mask[l];
        assign scatter[l]=write_choices[kind];assign mask_scatter[l]=mask_choices[kind];
        assign write_x0[l]=bank_xor[0]?scatter[l^16]:scatter[l];
        assign mask_x0[l]=bank_xor[0]?mask_scatter[l^16]:mask_scatter[l];
        assign bank_write[l*16+:16]=bank_xor[1]?write_x0[l^32]:write_x0[l];
        assign bank_mask[l]=bank_xor[1]?mask_x0[l^32]:mask_x0[l];
    end endgenerate
endmodule

// Banked arithmetic island. The 32-bit transaction tag carries ten internal
// address-control bits and a 22-bit user tag. Modes 1/2 use 64 bank words;
// mode0 bypasses this router and still requires 128 prepacked coefficients.
module flex_stream_banked(
    input clk,rst,in_valid,ntt,input [1:0] width,ntt_mode,
    input profile,inverse,input [31:0] tag,
    input [2047:0] data,input [1023:0] twiddle,
    output in_ready,input out_ready,output out_valid,out_ntt,
    output [1:0] out_width,out_ntt_mode,output out_profile,out_inverse,
    output [31:0] out_tag,output [2047:0] result,output [63:0] bank_write_mask
);
    // tag[31:28]=stride bit, [27:26]=bank XOR, [25:22]=logN, [21:0]=user.
    wire [1023:0] gathered;
    wire [2047:0] core_data=ntt&&ntt_mode!=0?{1024'b0,gathered}:data;
    wire [2047:0] core_result;
    ntt_bank_permute64 read_route(.bank_read(data[1023:0]),.logical_write(1024'b0),.logical_mask(64'b0),
      .low_stride(tag[31:28]),.bank_xor(tag[27:26]),.tail(ntt_mode==2),.inverse(inverse),
      .logical_read(gathered),.bank_write(),.bank_mask());
    flex_stream_buffered core(.clk(clk),.rst(rst),.in_valid(in_valid),.ntt(ntt),.width(width),.ntt_mode(ntt_mode),
      .profile(profile),.inverse(inverse),.tag(tag),.data(core_data),.twiddle(twiddle),
      .in_ready(in_ready),.out_ready(out_ready),.out_valid(out_valid),.out_ntt(out_ntt),
      .out_width(out_width),.out_ntt_mode(out_ntt_mode),.out_profile(out_profile),.out_inverse(out_inverse),
      .out_tag(out_tag),.result(core_result));
    wire [3:0] logn=out_tag[25:22];
    wire [63:0] active=logn==3?64'hff:logn==4?64'hffff:logn==5?64'hffffffff:64'hffffffffffffffff;
    wire [1023:0] scattered;
    wire [63:0] wm;
    ntt_bank_permute64 write_route(.bank_read(1024'b0),.logical_write(core_result[1023:0]),.logical_mask(active),
      .low_stride(out_tag[31:28]),.bank_xor(out_tag[27:26]),.tail(out_ntt_mode==2),.inverse(out_inverse),
      .logical_read(),.bank_write(scattered),.bank_mask(wm));
    assign result=out_ntt&&out_ntt_mode!=0?{1024'b0,scattered}:core_result;
    assign bank_write_mask=out_valid&&out_ntt&&out_ntt_mode!=0?wm:64'b0;
endmodule
