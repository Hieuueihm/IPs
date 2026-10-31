`timescale 1ns/1ps
module tb_radix4_compare;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,in_valid=0,profile=0,inverse=0;
    reg [1:0] mode=0;
    reg [15:0] tag=0;
    reg [127:0] data=0;
    reg [63:0] paired_roots=0,factor_roots=0;
    wire [8:0] valid,qp,iv;
    wire [1:0] om[0:8];wire [15:0] ot[0:8];wire [127:0] result[0:8];
`define P(N,W) clk,rst,in_valid,mode,profile,inverse,tag,data,W,valid[N],om[N],qp[N],iv[N],ot[N],result[N]
    radix2_shared3 d0(`P(0,paired_roots));
    radix2_shared4 d1(`P(1,paired_roots));
    radix4_shared4 d2(`P(2,factor_roots));
    radix2_pair4 d3(`P(3,paired_roots));
    radix4_pair4 d4(`P(4,factor_roots));
    radix4_pair_q12289 d5(`P(5,factor_roots));
    radix4_pair_q3329 d6(`P(6,factor_roots));
    radix2_pair_q12289 d7(`P(7,paired_roots));
    radix2_pair_q3329 d8(`P(8,paired_roots));
`undef P
    reg [1:0] ms[0:24999];reg qs[0:24999],ivs[0:24999];
    reg [127:0] ds[0:24999],es[0:24999];reg [63:0] prs[0:24999],frs[0:24999];
    reg [2047:0] input_path,output_path;
    reg [2:0] history=0;
    reg [8:0] ev;
    reg eligible;
    integer fi,fo,rc,n=0,k,j,index;
    integer checked[0:8],coverage[0:8];
    initial begin
        for(j=0;j<9;j=j+1)begin checked[j]=0;coverage[j]=0;end
        if(!$value$plusargs("vectors=%s",input_path))$fatal(1,"vectors");
        if(!$value$plusargs("actual=%s",output_path))$fatal(1,"actual");
        fi=$fopen(input_path,"r");fo=$fopen(output_path,"w");if(!fi||!fo)$fatal(1,"file open");
        while(!$feof(fi))begin
            rc=$fscanf(fi,"%h %h %h %h %h %h %h\n",ms[n],qs[n],ivs[n],ds[n],prs[n],frs[n],es[n]);
            if(rc==7)n=n+1;else if(rc!=-1)$fatal(1,"format");
            if(n>=25000)$fatal(1,"capacity");
        end
        $fclose(fi);repeat(3)@(negedge clk);rst=0;
        for(k=0;k<n;k=k+1)begin
            if(k%13==0)begin @(negedge clk);in_valid=0;end
            @(negedge clk);in_valid=1;tag=k;mode=ms[k];profile=qs[k];inverse=ivs[k];
            data=ds[k];paired_roots=prs[k];factor_roots=frs[k];
        end
        @(negedge clk);in_valid=0;repeat(5)@(negedge clk);
        for(j=0;j<9;j=j+1)begin
            if(checked[j]!=n||coverage[j]==0)$fatal(1,"coverage/lost top=%0d",j);
            $display("coverage top=%0d checked=%0d",j,coverage[j]);
        end
        $fclose(fo);$display("PASS: %0d radix4 compare transactions; all 9 tops, CT/GS, modes, profiles, exact 3/4-edge latency",n);$finish;
    end
    always @(posedge clk)begin
        ev=rst?0:{{8{history[2]}},history[1]};history=rst?0:{history[1:0],in_valid};#1;
        if(valid!==ev)$fatal(1,"valid latency");
        for(j=0;j<9;j=j+1)if(ev[j])begin
            index=checked[j];
            if(index>=n)$fatal(1,"extra output");
            eligible=j<3 || (ms[index]==1 && (j<5 || ((j==5||j==7)&&!qs[index]) || ((j==6||j==8)&&qs[index])));
            if(eligible)begin
                if(ot[j]!==index[15:0] || om[j]!==ms[index] || qp[j]!==qs[index] ||
                   iv[j]!==ivs[index] || result[j]!==es[index])begin
                    $display("FAIL top=%0d index=%0d mode=%0d q=%0d inverse=%0d",j,index,ms[index],qs[index],ivs[index]);
                    $display("got=%h expected=%h",result[j],es[index]);$fatal(1,"radix4 mismatch");
                end
                coverage[j]=coverage[j]+1;
            end
            if(j==2)$fwrite(fo,"%0d %h\n",index,result[j]);
            checked[j]=checked[j]+1;
        end
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
