`timescale 1ns/1ps
module tb_four_state;
    reg clk=0; always #5 clk=~clk;
    reg rst=1, cfg_valid=0, cfg_fft=0, cfg_inverse=0;
    reg [1:0] cfg_fmt=0,cfg_hmin=0;
    reg [3:0] cfg_logn=0;
    reg [31:0] cfg_q=0,cfg_qinv=0;
    wire cfg_ready;
    reg root_we=0,root_commit=0;
    reg [3:0] root_bank=0;
    reg [8:0] root_addr=0;
    reg [31:0] root_data=0;
    reg desc_we=0;
    reg [3:0] desc_stage=0;
    reg [15:0] desc_mask=0;
    reg [8:0] desc_root_base=0;
    reg [4:0] desc_root_mask=0;
    reg load_valid=0,read_valid=0,start=0;
    wire load_ready,read_ready,read_rsp_valid,busy,done,error;
    reg [9:0] load_line=0,read_line=0;
    reg [127:0] load_data=0;
    wire [127:0] read_data;
    wire [31:0] cycles;
    a_cg_core dut(.*);
    integer fd,ncase,nstage,nroot,nword,c,b,a,s,l,j,nwait;
    reg [31:0] input_words[0:4095],expected[0:4095];
    reg [1023:0] filename;
    function automatic [31:0] word;
        integer k,byte_value;
        begin
            for(k=0;k<4;k=k+1)begin
                byte_value=$fgetc(fd);
                if(byte_value<0)$fatal(1,"truncated fixture");
                word[8*k+:8]=byte_value;
            end
        end
    endfunction
    task tick; begin @(posedge clk); #1; end endtask
    initial begin
        $display("FOUR_STATE starting");$fflush();
        if(!$value$plusargs("FIXTURE=%s",filename))$fatal(1,"FIXTURE missing");
        fd=$fopen(filename,"rb");if(fd==0)$fatal(1,"fixture open failed");
        if(word()!=32'h43474131)$fatal(1,"fixture magic");
        ncase=word();
        repeat(4)tick();rst=0;tick();
        for(c=0;c<ncase;c=c+1)begin
            cfg_fft=word();cfg_fmt=word();cfg_logn=word();cfg_hmin=word();
            cfg_inverse=word();cfg_q=word();cfg_qinv=word();
            nstage=word();nroot=word();nword=word();
            $display("BEGIN case=%0d fft=%0d fmt=%0d logn=%0d root_words_per_lane=%0d t=%0t",c,cfg_fft,cfg_fmt,cfg_logn,nroot,$time);
            $fflush();
            cfg_valid=1;tick();cfg_valid=0;
            if(error!==0)$fatal(1,"configuration failed");
            for(s=0;s<nstage;s=s+1)begin
                desc_mask=word();desc_root_base=word();desc_root_mask=word();
                desc_stage=s;desc_we=1;tick();
            end
            desc_we=0;
            for(b=0;b<16;b=b+1)for(a=0;a<nroot;a=a+1)begin
                root_bank=b;root_addr=a;root_data=word();root_we=1;tick();
            end
            root_we=0;root_commit=1;tick();root_commit=0;
            $display("ROOTS loaded case=%0d t=%0t",c,$time);
            $fflush();
            for(a=0;a<nword;a=a+1)input_words[a]=word();
            for(a=0;a<nword;a=a+1)expected[a]=word();
            for(l=0;l<(nword+3)/4;l=l+1)begin
                while(load_ready!==1)tick();
                load_line=l;
                for(j=0;j<4;j=j+1)load_data[32*j+:32]=(4*l+j<nword)?input_words[4*l+j]:0;
                load_valid=1;tick();load_valid=0;
            end
            while(load_ready!==1)tick();
            start=1;tick();start=0;nwait=0;
            while(done!==1 && nwait<200000)begin tick();nwait=nwait+1;end
            if(done!==1 || error!==0)$fatal(1,"kernel timeout/error");
            $display("FOUR_STATE case=%0d fft=%0d fmt=%0d logn=%0d inverse=%0d kernel_cycles=%0d",c,cfg_fft,cfg_fmt,cfg_logn,cfg_inverse,cycles);
            $fflush();
            tick();
            for(l=0;l<(nword+3)/4;l=l+1)begin
                while(read_ready!==1)tick();
                read_valid=1;read_line=l;tick();read_valid=0;nwait=0;
                while(read_rsp_valid!==1 && nwait<50)begin tick();nwait=nwait+1;end
                if(read_rsp_valid!==1)$fatal(1,"read response timeout");
                for(j=0;j<4 && 4*l+j<nword;j=j+1)
                    if(read_data[32*j+:32]!==expected[4*l+j])
                        $fatal(1,"four-state mismatch case=%0d word=%0d got=%h expected=%h",c,4*l+j,read_data[32*j+:32],expected[4*l+j]);
                tick();
            end
        end
        $display("FOUR_STATE TOTAL cases=%0d PASS",ncase);$finish;
    end
    initial begin #100000000; $fatal(1,"global timeout");end
endmodule
