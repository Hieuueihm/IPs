`timescale 1ns/1ps
module tb_radix4_epoch;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,in_valid=0,profile=0,inverse=0;
    reg [1:0] mode=0;
    reg [15:0] tag=0;
    reg [127:0] data=0;
    reg [63:0] paired_roots=0,factor_roots=0;
    wire [3:0] valid,qp,iv;
    wire [1:0] om[0:3];wire [15:0] ot[0:3];wire [127:0] result[0:3];
`define P(N,W) clk,rst,in_valid,mode,profile,inverse,tag,data,W,valid[N],om[N],qp[N],iv[N],ot[N],result[N]
    radix4_shared_epoch d0(`P(0,factor_roots));
    radix4_pair_epoch d1(`P(1,factor_roots));
    radix4_pair_epoch_q12289 d2(`P(2,factor_roots));
    radix4_pair_epoch_q3329 d3(`P(3,factor_roots));
`undef P
    reg [1:0] ms[0:24999];reg qs[0:24999],ivs[0:24999];
    reg [127:0] ds[0:24999],es[0:24999];reg [63:0] prs[0:24999],frs[0:24999];
    reg [2047:0] input_path,output_path;
    reg [2:0] history=0;
    reg [3:0] ev;
    reg eligible;
    integer fi,fo,rc,n=0,k,j,index;
    integer checked[0:3],coverage[0:3];
    initial begin
        for(j=0;j<4;j=j+1)begin checked[j]=0;coverage[j]=0;end
        if(!$value$plusargs("vectors=%s",input_path))$fatal(1,"vectors");
        fi=$fopen(input_path,"r");if(!fi)$fatal(1,"file open");
        while(!$feof(fi))begin
            rc=$fscanf(fi,"%h %h %h %h %h %h %h\n",ms[n],qs[n],ivs[n],ds[n],prs[n],frs[n],es[n]);
            if(rc==7)n=n+1;else if(rc!=-1)$fatal(1,"format");
            if(n>=25000)$fatal(1,"capacity");
        end
        $fclose(fi);repeat(3)@(negedge clk);rst=0;
        for(k=0;k<n;k=k+1)begin
            if(k>0 && (qs[k]!=qs[k-1] || ivs[k]!=ivs[k-1]))begin
                @(negedge clk);in_valid=0;
                repeat(5)@(negedge clk);
                if(valid!==0)$fatal(1,"not drained before epoch change");
            end
            if(k%13==0)begin @(negedge clk);in_valid=0;end
            @(negedge clk);in_valid=1;tag=k;mode=ms[k];profile=qs[k];inverse=ivs[k];
            data=ds[k];paired_roots=prs[k];factor_roots=frs[k];
        end
        @(negedge clk);in_valid=0;repeat(5)@(negedge clk);
        for(j=0;j<4;j=j+1)begin
            if(checked[j]!=n||coverage[j]==0)$fatal(1,"coverage/lost top=%0d",j);
            $display("coverage top=%0d checked=%0d",j,coverage[j]);
        end
        $display("PASS: %0d epoch transactions; 4 tops, all modes, CT/GS; drain before profile/direction changes",n);$finish;
    end
    always @(posedge clk)begin
        ev=rst?0:{4{history[2]}};history=rst?0:{history[1:0],in_valid};#1;
        if(valid!==ev)$fatal(1,"valid latency");
        for(j=0;j<4;j=j+1)if(ev[j])begin
            index=checked[j];
            if(index>=n)$fatal(1,"extra output");
            eligible=j==0 || (ms[index]==1 && (j==1 || (j==2&&!qs[index]) || (j==3&&qs[index])));
            if(eligible)begin
                if(ot[j]!==index[15:0] || om[j]!==ms[index] || qp[j]!==qs[index] ||
                   iv[j]!==ivs[index] || result[j]!==es[index])begin
                    $display("FAIL top=%0d index=%0d mode=%0d q=%0d inverse=%0d",j,index,ms[index],qs[index],ivs[index]);
                    $display("got=%h expected=%h",result[j],es[index]);$fatal(1,"radix4 mismatch");
                end
                coverage[j]=coverage[j]+1;
            end
            checked[j]=checked[j]+1;
        end
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
