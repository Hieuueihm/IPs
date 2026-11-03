`timescale 1ns/1ps
module tb_flex_arith_bank;
    reg clk=0;
    always #5 clk=~clk;
    reg rst=1,in_valid=0;
    reg [1:0] mode=0;
    reg [1023:0] x=0,y=0,z=0;
    wire [3:0] valid;
    wire [1:0] om[0:3];
    wire [1023:0] p[0:3],u[0:3],v[0:3];
    proto_r32 d0(clk,rst,in_valid,mode,x,y,z,valid[0],om[0],p[0],u[0],v[0]);
    proto_f16_common d1(clk,rst,in_valid,mode,x,y,z,valid[1],om[1],p[1],u[1],v[1]);
    proto_f16_wide d2(clk,rst,in_valid,mode,x,y,z,valid[2],om[2],p[2],u[2],v[2]);
    proto_f16_mid d3(clk,rst,in_valid,mode,x,y,z,valid[3],om[3],p[3],u[3],v[3]);
    reg [1:0] modes[0:8191];
    reg [1023:0] xs[0:8191],ys[0:8191],zs[0:8191];
    reg [1023:0] ps[0:8191],us[0:8191],vs[0:8191];
    integer fd,fo,rc,n=0,issued=0,checked=0,d;
    reg [1023:0] ep,eu,ev;
    reg [2047:0] input_path,output_path;
    initial begin
        if(!$value$plusargs("vectors=%s",input_path)) $fatal(1,"missing vectors");
        if(!$value$plusargs("actual=%s",output_path)) $fatal(1,"missing actual");
        fd=$fopen(input_path,"r"); if(!fd) $fatal(1,"cannot open vectors");
        fo=$fopen(output_path,"w"); if(!fo) $fatal(1,"cannot open result");
        while(!$feof(fd)) begin
            rc=$fscanf(fd,"%h %h %h %h %h %h %h\n",modes[n],xs[n],ys[n],zs[n],ps[n],us[n],vs[n]);
            if(rc==7) n=n+1;
            else if(rc!=-1) $fatal(1,"bad vector format");
            if(n>=8192) $fatal(1,"vector capacity");
        end
        $fclose(fd);
        repeat(3) @(negedge clk);
        rst=0;
        for(issued=0;issued<n;issued=issued+1) begin
            if(issued%11==0) begin
                @(negedge clk); in_valid=0;
            end
            @(negedge clk);
            in_valid=1; mode=modes[issued]; x=xs[issued]; y=ys[issued]; z=zs[issued];
        end
        @(negedge clk); in_valid=0;
        repeat(3) @(negedge clk);
        if(checked!=n) $fatal(1,"lost transactions %0d/%0d",checked,n);
        $fclose(fo);
        $display("PASS: %0d transactions x 4 configurations; continuous issues, bubbles and mode switches",n);
        $finish;
    end
    always @(posedge clk) begin
        #1;
        if(valid!==4'b0000 && valid!==4'b1111) $fatal(1,"valid disagreement");
        if(valid==4'b1111) begin
            if(checked>=n) $fatal(1,"extra output");
            for(d=0;d<4;d=d+1) begin
                ep=ps[checked]; eu=us[checked]; ev=vs[checked];
                if(modes[checked]==0 && (d==0 || d==1)) begin
                    ep[1023:256]=0; eu[1023:256]=0; ev[1023:256]=0;
                end
                if(modes[checked]==0 && d==3) begin
                    ep[1023:512]=0; eu[1023:512]=0; ev[1023:512]=0;
                end
                if(om[d]!==modes[checked] || p[d]!==ep || u[d]!==eu || v[d]!==ev) begin
                    $display("FAIL vector=%0d dut=%0d mode=%0d",checked,d,modes[checked]);
                    $display("product=%h expected=%h",p[d],ep);
                    $fatal(1,"arithmetic mismatch");
                end
            end
            $fwrite(fo,"%0d %h\n",checked,p[0]);
            checked=checked+1;
        end
    end
    initial begin #1000000; $fatal(1,"timeout"); end
endmodule
