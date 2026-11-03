`timescale 1ns/1ps
module tb_mont_reducers;
    reg clk=0;
    always #5 clk=~clk;
    reg rst=1,in_valid=0,profile=0;
    reg [15:0] tag=0;
    reg [27:0] t=0;
    wire [8:0] ov,op;
    wire [15:0] ot[0:8],r[0:8];
`define P(N) clk,rst,in_valid,profile,tag,t,ov[N],op[N],ot[N],r[N]
    reduce_original_dynamic d0(`P(0));
    reduce_csa_dynamic d1(`P(1));
    reduce_compact_dynamic d2(`P(2));
    reduce_original_q12289 d3(`P(3));
    reduce_csa_q12289 d4(`P(4));
    reduce_compact_q12289 d5(`P(5));
    reduce_original_q3329 d6(`P(6));
    reduce_csa_q3329 d7(`P(7));
    reduce_compact_q3329 d8(`P(8));
`undef P
    reg qs[0:149999];
    reg [27:0] ts[0:149999];
    reg [15:0] expected[0:149999];
    reg [2047:0] input_path;
    integer fd,rc,n=0,k,j,checked=0;
    reg history=0,ev,eligible;
    initial begin
        if(!$value$plusargs("vectors=%s",input_path)) $fatal(1,"vectors missing");
        fd=$fopen(input_path,"r");if(!fd) $fatal(1,"file open");
        while(!$feof(fd)) begin
            rc=$fscanf(fd,"%h %h %h\n",qs[n],ts[n],expected[n]);
            if(rc==3) n=n+1;
            else if(rc!=-1) $fatal(1,"format");
            if(n>=150000) $fatal(1,"capacity");
        end
        $fclose(fd);
        repeat(3) @(negedge clk);rst=0;
        for(k=0;k<n;k=k+1) begin
            if(k%97==0) begin @(negedge clk);in_valid=0;end
            @(negedge clk);
            in_valid=1;profile=qs[k];tag=k;t=ts[k];
        end
        @(negedge clk);in_valid=0;
        repeat(3) @(negedge clk);
        if(checked!=n) $fatal(1,"lost transaction");
        $display("PASS: %0d reducer transactions; 9 configurations, exact latency/profile/tag and bubbles",n);
        $finish;
    end
    always @(posedge clk) begin
        ev=!rst && history;history=!rst && in_valid;
        #1;
        if(ov!=={9{ev}}) $fatal(1,"valid latency");
        if(ev) begin
            for(j=0;j<9;j=j+1) begin
                eligible=j<3 || (j<6 && !qs[checked]) || (j>=6 && qs[checked]);
                if(eligible && (ot[j]!==checked[15:0] || op[j]!==qs[checked] || r[j]!==expected[checked])) begin
                    $display("FAIL top=%0d index=%0d qprofile=%0d t=%h got=%h expected=%h",j,checked,qs[checked],ts[checked],r[j],expected[checked]);
                    $fatal(1,"reduction mismatch");
                end
            end
            checked=checked+1;
        end
    end
    initial begin #10000000;$fatal(1,"timeout");end
endmodule
