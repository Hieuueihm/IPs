`timescale 1ns/1ps
module tb_flex_ntt_cluster;
    reg clk=0;
    always #5 clk=~clk;
    reg rst=1,in_valid=0;
    reg [1:0] mode=0;
    reg profile=0,inverse=0;
    reg [15:0] tag=0;
    reg [127:0] data=0;
    reg [63:0] twiddle=0;
    wire [8:0] valid,oq,oi;
    wire [1:0] om[0:8];
    wire [15:0] ot[0:8];
    wire [127:0] result[0:8];
`define DUT_ARGS(N) clk,rst,in_valid,mode,profile,inverse,tag,data,twiddle,valid[N],om[N],oq[N],oi[N],ot[N],result[N]
    cluster_ntt_parallel d0(`DUT_ARGS(0));
    cluster_ntt_pair_only d1(`DUT_ARGS(1));
    cluster_ntt_configurable d2(`DUT_ARGS(2));
    cluster_flex_parallel d3(`DUT_ARGS(3));
    cluster_flex_pair d4(`DUT_ARGS(4));
    cluster_ntt_pair_q12289 d5(`DUT_ARGS(5));
    cluster_ntt_pair_q3329 d6(`DUT_ARGS(6));
    cluster_ntt_pair_bypass d7(`DUT_ARGS(7));
    cluster_ntt_parallel_short d8(`DUT_ARGS(8));
`undef DUT_ARGS
    reg [1:0] modes[0:65534];
    reg qs[0:65534],ivs[0:65534];
    reg [127:0] ds[0:65534],expected[0:65534];
    reg [63:0] ws[0:65534];
    integer fd,fo,rc,n=0,issued,j,index;
    integer coverage[0:8],checked[0:8];
    reg eligible;
    reg [1:0] valid_history=0;
    reg [8:0] expected_valid;
    reg [2047:0] input_path,output_path;
    initial begin
        for(j=0;j<9;j=j+1) begin coverage[j]=0; checked[j]=0; end
        if(!$value$plusargs("vectors=%s",input_path)) $fatal(1,"missing vectors");
        if(!$value$plusargs("actual=%s",output_path)) $fatal(1,"missing actual");
        fd=$fopen(input_path,"r"); fo=$fopen(output_path,"w");
        if(!fd || !fo) $fatal(1,"file open");
        while(!$feof(fd)) begin
            rc=$fscanf(fd,"%h %h %h %h %h %h\n",modes[n],qs[n],ivs[n],ds[n],ws[n],expected[n]);
            if(rc==6) n=n+1;
            else if(rc!=-1) $fatal(1,"bad vector");
            if(n>=65535) $fatal(1,"too many vectors");
        end
        $fclose(fd);
        repeat(3) @(negedge clk);
        rst=0;
        for(issued=0;issued<n;issued=issued+1) begin
            if(issued%13==0) begin @(negedge clk); in_valid=0; end
            @(negedge clk);
            in_valid=1; tag=issued; mode=modes[issued]; profile=qs[issued]; inverse=ivs[issued];
            data=ds[issued]; twiddle=ws[issued];
        end
        @(negedge clk); in_valid=0;
        repeat(4) @(negedge clk);
        for(j=0;j<9;j=j+1) begin
            if(checked[j]!=n) $fatal(1,"lost transaction top=%0d",j);
            if(coverage[j]==0) $fatal(1,"uncovered top");
            $display("coverage top=%0d checked=%0d",j,coverage[j]);
        end
        $display("PASS: %0d vectors; 9 configurations; exact valid latency, bubbles, modes, profiles, CT/GS",n);
        $fclose(fo); $finish;
    end
    always @(posedge clk) begin
        expected_valid=rst ? 0 : {valid_history[0],{8{valid_history[1]}}};
        valid_history=rst ? 0 : {valid_history[0],in_valid};
        #1;
        if(valid!==expected_valid) $fatal(1,"pipeline valid/latency");
        for(j=0;j<9;j=j+1) begin
          if(expected_valid[j]) begin
                index=checked[j];
                if(index>=n) $fatal(1,"extra output");
                case(j)
                    0: eligible=modes[index]==0;
                    1: eligible=modes[index]==1;
                    2: eligible=modes[index]!=3;
                    3: eligible=modes[index]==0 || modes[index]==3;
                    4: eligible=1;
                    5: eligible=modes[index]==1 && !qs[index];
                    6: eligible=modes[index]==1 && qs[index];
                    7: eligible=modes[index]==1 || modes[index]==2;
                    8: eligible=modes[index]==0;
                endcase
                if(eligible) begin
                    if(ot[j]!==index[15:0] || om[j]!==modes[index] ||
                       oq[j]!==qs[index] || oi[j]!==ivs[index] || result[j]!==expected[index]) begin
                        $display("FAIL top=%0d vector=%0d mode=%0d qprofile=%0d inv=%0d",j,index,modes[index],qs[index],ivs[index]);
                        $display("actual=%h expected=%h",result[j],expected[index]);
                        $fatal(1,"cluster mismatch");
                    end
                    coverage[j]=coverage[j]+1;
                end
                if(j==4) $fwrite(fo,"%0d %h\n",index,result[4]);
                checked[j]=checked[j]+1;
          end
        end
    end
    initial begin #10000000; $fatal(1,"timeout"); end
endmodule
