// Read-only simulation monitor. The DUT and its datapath are unchanged.
module flex_kernel_profile(
    input clk,rst,pause,
    input [3:0] cfg_op,cfg_logn,input [1:0] cfg_width,input cfg_profile,
    input start_valid,output start_ready,
    input load_valid,output load_ready,input load_bank,
    input [9:0] load_address,input [127:0] load_data,
    input read_valid,output read_ready,input [9:0] read_address,
    output read_response_valid,output [127:0] read_data,
    output done_valid,input done_ready,output error,
    output [31:0] cycles,output [3071:0] metrics
);
    flex_kernel_engine dut(.*);
    reg [31:0] count[0:95];
    genvar k;
    generate for(k=0;k<96;k=k+1)begin:counters
        assign metrics[k*32+:32]=count[k];
    end endgenerate
    function automatic integer pop(input [63:0] bits);
        integer b;begin pop=0;for(b=0;b<64;b=b+1)pop=pop+bits[b];end
    endfunction
    wire busy=dut.state!=0&&dut.state!=21;
    wire accepted=dut.array_valid&&dut.array_in_ready;
    wire [6:0] active_coeff=dut.n<64?dut.n:64;
    integer i,s;
    always @(posedge clk)begin
        if(rst||(start_valid&&start_ready))begin
            for(i=0;i<96;i=i+1)count[i]<=0;
        end else if(busy)begin
            count[0]<=count[0]+1;
            count[1]<=count[1]+pause;
            count[16+dut.state]<=count[16+dut.state]+1;
            if(!pause)count[38+dut.state]<=count[38+dut.state]+1;
            if(accepted)begin
                if(!dut.array_ntt)begin
                    count[2]<=count[2]+1;
                    // Logical assigned leaf-products: includes retained-limb padding,
                    // not transistor activity or a power measurement.
                    count[6]<=count[6]+(4<<(2*dut.width));
                    count[69]<=count[69]+1;
                    count[70]<=count[70]+(16>>(2*dut.width));
                end else begin
                    case(dut.mode)
                    0:count[5]<=count[5]+1;
                    1:count[3]<=count[3]+1;
                    2:count[4]<=count[4]+1;
                    endcase
                    count[6]<=count[6]+(dut.mode==2?active_coeff>>1:active_coeff);
                    count[71]<=count[71]+((active_coeff+3)>>2);
                    count[72]<=count[72]+16;
                end
            end
            count[7]<=count[7]+(dut.array_valid&&!dut.array_in_ready);
            count[8]<=count[8]+(!pause&&(dut.state==5||dut.state==12)&&!dut.array_out_valid);
            count[9]<=count[9]+(dut.array_out_valid&&!dut.array_ready);
            count[10]<=count[10]+(!dut.arithmetic.core.core.advance);
            count[11]<=count[11]+pop(dut.re[0])+pop(dut.re[1])+pop(dut.re[2]);
            count[12]<=count[12]+pop(dut.we[0])+pop(dut.we[1])+pop(dut.we[2]);
            count[13]<=count[13]+pop({48'b0,dut.root_en});
            count[14]<=count[14]+dut.fft_en;
            count[15]<=count[15]+(dut.array_out_valid&&dut.array_ready);
            if(dut.arithmetic.core.g_fifo.count>count[60])count[60]<=dut.arithmetic.core.g_fifo.count;
            count[61]<=count[61]+(dut.arithmetic.core.g_fifo.count!=0);
            for(s=0;s<3;s=s+1)begin
                count[62+s]<=count[62+s]+pop(dut.re[s]);
                count[65+s]<=count[65+s]+pop(dut.we[s]);
            end
        end
    end
endmodule
