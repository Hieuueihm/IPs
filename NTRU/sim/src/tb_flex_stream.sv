`timescale 1ns/1ps
module tb_flex_stream;
    parameter integer FIFO_ENABLE=1, STALL_ENABLE=1, BANKED=0;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,in_valid=0,ntt=0,profile=0,inverse=0,out_ready=0;
    reg [1:0] width=0,ntt_mode=0;
    reg [31:0] tag=0;
    reg [2047:0] data=0;
    reg [1023:0] twiddle=0;
    wire in_ready,out_valid,out_ntt,out_profile,out_inverse;
    wire [1:0] out_width,out_ntt_mode;
    wire [31:0] out_tag;
    wire [2047:0] result;
    wire [63:0] bank_write_mask;
    generate if(BANKED)begin:g_banked
        flex_stream_banked dut(.*);
    end else begin:g_normal
        flex_stream_buffered #(.FIFO_ENABLE(FIFO_ENABLE),.STALL_ENABLE(STALL_ENABLE)) dut(.*);
        assign bank_write_mask=0;
    end endgenerate
    reg ns[0:65535],qs[0:65535],ivs[0:65535];
    reg [1:0] ws[0:65535],ms[0:65535];
    reg [2047:0] ds[0:65535],es[0:65535];
    reg [1023:0] ts[0:65535];
    reg [31:0] cs[0:65535];
    reg [63:0] masks[0:65535];
    reg [4095:0] path,actual;
    integer fi,fo,rc,n=0,sent=0,checked=0,cycles=0,blocked_in=0,blocked_out=0;
    reg accepted=0,was_blocked=0;
    reg [2151:0] held;
    reg [31:0] random_state=32'h13579bdf;
    initial begin
        if(!$value$plusargs("vectors=%s",path) || !$value$plusargs("actual=%s",actual))$fatal(1,"paths");
        fi=$fopen(path,"r");fo=$fopen(actual,"w");
        if(!fi || !fo)$fatal(1,"file open");
        while(!$feof(fi))begin
            rc=$fscanf(fi,"%h %h %h %h %h %h %h %h %h %h\n",ns[n],ws[n],ms[n],qs[n],ivs[n],ds[n],ts[n],es[n],cs[n],masks[n]);
            if(rc==10)n=n+1;else if(rc!=-1)$fatal(1,"format");
            if(n>=65536)$fatal(1,"capacity");
        end
        $fclose(fi);
        repeat(3)@(negedge clk);rst=0;
        while(checked<n)begin
            @(negedge clk);
            random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
            // Long stalls exercise queue saturation and freeze all pipeline stages.
            out_ready=!STALL_ENABLE || ((cycles%127)<99 && random_state[1:0]!=0);
            if(!in_valid || accepted)begin
                in_valid=sent<n && random_state[3:2]!=0;
                if(in_valid)begin
                    ntt=ns[sent];width=ws[sent];ntt_mode=ms[sent];profile=qs[sent];inverse=ivs[sent];
                    data=ds[sent];twiddle=ts[sent];tag=sent|cs[sent];
                end
            end
        end
        @(negedge clk);in_valid=0;out_ready=1;
        repeat(8)@(negedge clk);
        if(sent!=n || checked!=n)$fatal(1,"lost/duplicate transaction");
        $fclose(fo);
        $display("PASS transactions=%0d cycles=%0d blocked_in=%0d blocked_out=%0d FIFO=%0d STALL=%0d",n,cycles,blocked_in,blocked_out,FIFO_ENABLE,STALL_ENABLE);
        $finish;
    end
    always @(posedge clk)begin
        if(!rst)begin
            cycles=cycles+1;
            if(was_blocked && {out_valid,out_ntt,out_width,out_ntt_mode,out_profile,out_inverse,out_tag,result,bank_write_mask}!==held)
                $fatal(1,"output changed while blocked");
            was_blocked=out_valid&&!out_ready;
            held={out_valid,out_ntt,out_width,out_ntt_mode,out_profile,out_inverse,out_tag,result,bank_write_mask};
            accepted=in_valid&&in_ready;
            if(accepted)sent=sent+1;
            if(in_valid&&!in_ready)blocked_in=blocked_in+1;
            if(out_valid&&!out_ready)blocked_out=blocked_out+1;
            if(out_valid&&out_ready)begin
                if(out_tag!==(checked|cs[checked]) || out_ntt!==ns[checked] || out_width!==ws[checked] ||
                   out_ntt_mode!==ms[checked] || out_profile!==qs[checked] || out_inverse!==ivs[checked] ||
                   result!==es[checked] || bank_write_mask!==masks[checked])begin
                    $display("FAIL index=%0d tag=%0d ntt=%0d width=%0d got=%h expected=%h",checked,out_tag,out_ntt,out_width,result,es[checked]);
                    $fatal(1,"stream mismatch");
                end
                $fwrite(fo,"%0d %h\n",checked,result);checked=checked+1;
                if(checked>n)$fatal(1,"duplicate");
            end
            if(cycles>400000)$fatal(1,"timeout");
        end else begin accepted=0;was_blocked=0;end
    end
endmodule
