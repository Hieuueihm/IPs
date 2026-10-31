`timescale 1ns/1ps
module tb_kernel_axil;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    reg [11:0] awaddr=0,araddr=0;
    reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
    reg [31:0] wdata=0;reg [3:0] wstrb=15;
    wire awready,wready,bvalid,arready,rvalid;wire [1:0] bresp,rresp;wire [31:0] rdata;
    flex_kernel_axil dut(.aclk(clk),.aresetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(3'b0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready));
    integer writes=0,reads=0;
    task automatic write_reg(input [11:0] addr,input [31:0] value,input [3:0] strb,input [1:0] expected_resp);
        integer gap;reg [1:0] held;
        begin
            gap=writes%3;writes=writes+1;
            fork
                begin
                    repeat(gap)@(negedge clk);
                    @(negedge clk);awaddr=addr;awvalid=1;
                    @(posedge clk);while(!awready)@(posedge clk);
                    @(negedge clk);awvalid=0;
                end
                begin
                    repeat(2-gap)@(negedge clk);
                    @(negedge clk);wdata=value;wstrb=strb;wvalid=1;
                    @(posedge clk);while(!wready)@(posedge clk);
                    @(negedge clk);wvalid=0;
                end
            join
            while(!bvalid)@(negedge clk);
            held=bresp;
            repeat(2)begin @(negedge clk);if(!bvalid||bresp!==held)$fatal(1,"B changed under stall");end
            if(held!==expected_resp)$fatal(1,"write response addr=%h got=%h expected=%h",addr,held,expected_resp);
            bready=1;@(negedge clk);bready=0;
        end
    endtask
    task automatic read_reg(input [11:0] addr,output [31:0] value,input [1:0] expected_resp);
        reg [31:0] held;reg [1:0] response;
        begin
            reads=reads+1;
            @(negedge clk);araddr=addr;arvalid=1;
            @(posedge clk);while(!arready)@(posedge clk);
            @(negedge clk);arvalid=0;
            while(!rvalid)@(negedge clk);
            held=rdata;response=rresp;
            repeat(2)begin @(negedge clk);if(!rvalid||rdata!==held||rresp!==response)$fatal(1,"R changed under stall");end
            if(response!==expected_resp)$fatal(1,"read response");
            value=held;rready=1;@(negedge clk);rready=0;
        end
    endtask
    reg [127:0] a[0:1023],b[0:1023],expected[0:1023],actual;
    integer fd,rc,cases=0,op,width,logn,profile,na,nb,ny,i,j,k,tries;
    reg [31:0] status,value;reg [1023:0] vector_path;
    initial begin
        #200000000;$fatal(1,"AXI timeout");
    end
    initial begin
        repeat(4)@(negedge clk);resetn=1;
        write_reg(12'h010,32'h12345678,15,0);
        write_reg(12'h010,32'haabbccdd,5,0);
        read_reg(12'h010,value,0);if(value!==32'h12bb56dd)$fatal(1,"WSTRB merge");
        write_reg(12'hfff,0,15,2);read_reg(12'hfff,value,2);
        write_reg(12'h004,3,15,2);
        if(!$value$plusargs("vectors=%s",vector_path))$fatal(1,"missing vectors");
        fd=$fopen(vector_path,"r");if(!fd)$fatal(1,"open vectors");
        rc=$fscanf(fd,"%d %d %d %d %d %d %d",op,width,logn,profile,na,nb,ny);
        while(rc==7)begin
            for(i=0;i<na;i=i+1)rc=$fscanf(fd,"%h",a[i]);
            for(i=0;i<nb;i=i+1)rc=$fscanf(fd,"%h",b[i]);
            for(i=0;i<ny;i=i+1)rc=$fscanf(fd,"%h",expected[i]);
            write_reg(0,op|(logn<<4)|(width<<8)|(profile<<10),15,0);
            for(k=0;k<2;k=k+1)begin
                write_reg(12'h014,k,15,0);
                for(i=0;i<(k?nb:na);i=i+1)begin
                    write_reg(12'h010,i,15,0);
                    for(j=0;j<4;j=j+1)write_reg(12'h020+4*j,k?b[i][32*j+:32]:a[i][32*j+:32],15,0);
                    write_reg(12'h018,1,15,0);
                end
            end
            write_reg(12'h004,1,15,0);
            tries=0;status=0;
            while(!status[2]&&tries<20000)begin read_reg(12'h008,status,0);tries=tries+1;end
            if(!status[2]||status[3])$fatal(1,"kernel command failed");
            for(i=0;i<ny;i=i+1)begin
                write_reg(12'h010,i,15,0);write_reg(12'h018,2,15,0);
                status=0;while(!status[4])read_reg(12'h008,status,0);
                for(j=0;j<4;j=j+1)begin read_reg(12'h030+j*4,value,0);actual[j*32+:32]=value;end
                if(actual!==expected[i])$fatal(1,"AXI result case=%d word=%d got=%h expected=%h",cases,i,actual,expected[i]);
            end
            write_reg(12'h004,2,15,0);cases=cases+1;
            rc=$fscanf(fd,"%d %d %d %d %d %d %d",op,width,logn,profile,na,nb,ny);
        end
        $fclose(fd);$display("PASS AXI kernels=%0d writes=%0d reads=%0d",cases,writes,reads);$finish;
    end
endmodule
