`timescale 1ns/1ps
module tb_reduce_cluster;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,in_valid=0,profile=0,inverse=0;
    reg [1:0] mode=0;
    reg [15:0] tag=0;
    reg [127:0] data=0;
    reg [63:0] twiddle=0;
    wire [2:0] valid,qp,iv;
    wire [1:0] om[0:2];
    wire [15:0] ot[0:2];
    wire [127:0] result[0:2];
`define P(N) clk,rst,in_valid,mode,profile,inverse,tag,data,twiddle,valid[N],om[N],qp[N],iv[N],ot[N],result[N]
    reduce_cluster_original d0(`P(0));
    reduce_cluster_csa d1(`P(1));
    reduce_cluster_compact d2(`P(2));
`undef P
    reg [1:0] ms[0:19999];
    reg qs[0:19999],ivs[0:19999];
    reg [127:0] ds[0:19999],es[0:19999];
    reg [63:0] ws[0:19999];
    reg [2047:0] input_path,output_path;
    reg [1:0] history=0;
    reg ev;
    integer fi,fo,rc,n=0,k,j,checked=0;
    initial begin
        if(!$value$plusargs("vectors=%s",input_path)) $fatal(1,"vectors missing");
        if(!$value$plusargs("actual=%s",output_path)) $fatal(1,"actual missing");
        fi=$fopen(input_path,"r");fo=$fopen(output_path,"w");
        if(!fi || !fo) $fatal(1,"file open");
        while(!$feof(fi)) begin
            rc=$fscanf(fi,"%h %h %h %h %h %h\n",ms[n],qs[n],ivs[n],ds[n],ws[n],es[n]);
            if(rc==6)n=n+1;else if(rc!=-1)$fatal(1,"format");
            if(n>=20000)$fatal(1,"capacity");
        end
        $fclose(fi);
        repeat(3)@(negedge clk);rst=0;
        for(k=0;k<n;k=k+1)begin
            if(k%13==0)begin @(negedge clk);in_valid=0;end
            @(negedge clk);in_valid=1;tag=k;mode=ms[k];profile=qs[k];inverse=ivs[k];data=ds[k];twiddle=ws[k];
        end
        @(negedge clk);in_valid=0;
        repeat(4)@(negedge clk);
        if(checked!=n)$fatal(1,"lost transaction");
        $fclose(fo);$display("PASS: %0d cluster transactions; three reducers; all modes, profiles, CT/GS",n);$finish;
    end
    always @(posedge clk)begin
        ev=!rst && history[1];history=rst?0:{history[0],in_valid};#1;
        if(valid!=={3{ev}})$fatal(1,"valid latency");
        if(ev)begin
            for(j=0;j<3;j=j+1)begin
                if(ot[j]!==checked[15:0] || om[j]!==ms[checked] || qp[j]!==qs[checked] ||
                   iv[j]!==ivs[checked] || result[j]!==es[checked])begin
                    $display("FAIL index=%0d top=%0d got=%h expected=%h",checked,j,result[j],es[checked]);
                    $fatal(1,"cluster mismatch");
                end
            end
            $fwrite(fo,"%0d %h\n",checked,result[0]);checked=checked+1;
        end
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
