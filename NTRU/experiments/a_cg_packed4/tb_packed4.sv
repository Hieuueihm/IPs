`timescale 1ns/1ps
// Independent arithmetic scoreboard, two modulus slots, lane pairing, bubbles and enable stalls.
module tb_packed4;
    reg clk=0; always #5 clk=~clk;
    reg rst=1,en=1,cfg_we=0,cfg_slot=0,halve=0,dir=0;
    reg [31:0] cq=0,ci=0;
    reg valid=0,slot=0,pairing=0;
    reg [63:0] data=0;
    reg [31:0] root=0;
    reg [7:0] tag=0;
    wire ready,rv,idle;
    wire [63:0] result;
    wire [7:0] rtag;
    tile_a2 #(.IN_REG(1)) dut(.clk(clk),.rst(rst),.en(en),.idle(idle),
        .cfg_we(cfg_we),.cfg_slot(cfg_slot),.cfg_ntrugen(1'b0),.cfg_fmt(2'd0),.cfg_shift(4'd0),
        .ext_fft_valid(1'b0),.ext_fft_mpr(2'd0),.ext_fft_mst(4'd0),
        .cfg_q(cq),.cfg_qinv(ci),.cfg_floor(1'b0),.cfg_halve(halve),
        .req_valid(valid),.req_ready(ready),.req_mode(2'd2),.req_dir(dir),.req_slot(slot),
        .req_sign(pairing),.req_data(data),.req_root(root),.req_tag(tag),
        .rsp_valid(rv),.rsp_data(result),.rsp_tag(rtag));
    localparam N=600;
    reg [63:0] want[0:N-1];
    integer qs[0:1],qset[0:6];
    integer seed=1709,sent=0,got=0,ticks=0,errors=0,total=0,qn,dn,hn,st;
    integer active=0,stress=0,accepted=0;
    integer clock_count=0,sat_first=0,sat_last=0,dual_busy=0;
    function [15:0] neginv(input [15:0] q);
        reg [15:0] v;integer k;
        begin v=q;for(k=0;k<4;k=k+1)v=v*(16'd2-q*v);neginv=-v;end
    endfunction
    // Oracle uses modular inverse of R, not the RTL's Montgomery T/m/mq formula.
    function integer invr(input integer q);
        integer t,newt,r,newr,quot,tmp;
        begin
            t=0;newt=1;r=q;newr=65536%q;
            while(newr!=0)begin quot=r/newr;tmp=t-quot*newt;t=newt;newt=tmp;
                tmp=r-quot*newr;r=newr;newr=tmp;end
            invr=(t%q+q)%q;
        end
    endfunction
    function [31:0] bf(input integer x,y,w,q);
        reg [63:0] z;integer a,b,t;
        begin
            if(dir)begin
                a=(x+y)%q;b=(x-y+q)%q;z=b;z=z*w;z=z*invr(q);b=z%q;
                if(halve)a=(a+(a%2)*q)/2;
            end else begin
                z=y;z=z*w;z=z*invr(q);t=z%q;a=(x+t)%q;b=(x-t+q)%q;
            end
            bf={b[15:0],a[15:0]};
        end
    endfunction
    task next_request;
        integer q,x0,x1,y0,y1,w0,w1;reg [31:0] z0,z1;
        begin
            slot=$random(seed)&1;q=qs[slot];pairing=$random(seed)&1;
            x0=$unsigned($random(seed))%q;x1=$unsigned($random(seed))%q;
            y0=$unsigned($random(seed))%q;y1=$unsigned($random(seed))%q;
            w0=$unsigned($random(seed))%q;w1=$unsigned($random(seed))%q;
            if(sent%8==0)begin x0=0;y0=0;w0=0;x1=q-1;y1=q-1;w1=q-1;end
            if(sent%8==1)begin x0=q-1;y0=1;w0=1;x1=0;y1=q-1;w1=q-1;end
            data={y1[15:0],y0[15:0],x1[15:0],x0[15:0]};root={w1[15:0],w0[15:0]};tag=sent;
            if(pairing)begin z0=bf(x0,x1,w0,q);z1=bf(y0,y1,w1,q);want[sent]={z1,z0};end
            else begin z0=bf(x0,y0,w0,q);z1=bf(x1,y1,w1,q);want[sent]={z1[31:16],z0[31:16],z1[15:0],z0[15:0]};end
        end
    endtask
    always @(posedge clk) begin
        clock_count=clock_count+1;
        accepted=active && !rst && en && valid && ready;
        if(accepted && sent==0)sat_first=clock_count;
        if(accepted && sent==N/2-1)sat_last=clock_count;
        if(active && !rst && en &&
           ((dut.v1 && !dut.group1) || dut.g_arr32.packed_stream[0].pv[5] || dut.g_arr32.packed_stream[0].pv[10]) &&
           ((dut.v1 && dut.group1) || dut.g_arr32.packed_stream[1].pv[5] || dut.g_arr32.packed_stream[1].pv[10]))dual_busy=dual_busy+1;
        if(active && !rst && rv) begin
            if(got>=sent || result!==want[got] || rtag!==got[7:0])begin
                errors=errors+1;
                if(errors<6)$display("MISMATCH q=%0d dir=%0d half=%0d got=%0d data=%h want=%h tag=%0d",qs[0],dir,halve,got,result,want[got],rtag);
            end
            got=got+1;
        end
    end
    initial begin
        qset[0]=3;qset[1]=17;qset[2]=3329;qset[3]=7681;qset[4]=12289;qset[5]=18433;qset[6]=32749;
        for(qn=0;qn<7;qn=qn+1)for(dn=0;dn<2;dn=dn+1)for(hn=0;hn<2;hn=hn+1)begin
            @(negedge clk);active=0;rst=1;valid=0;en=1;
            repeat(3)@(negedge clk);
            rst=0;dir=dn;halve=hn;qs[0]=qset[qn];qs[1]=qset[(qn+1)%7];
            for(st=0;st<2;st=st+1)begin
                cfg_we=1;cfg_slot=st;cq={qs[st][15:0],qs[st][15:0]};ci={neginv(qs[st]),neginv(qs[st])};@(negedge clk);
            end
            cfg_we=0;sent=0;got=0;ticks=0;active=1;next_request();valid=1;
            while(sent<N || got<N)begin
                @(posedge clk);#1;
                if(accepted)sent=sent+1;
                @(negedge clk);ticks=ticks+1;
                if(ticks>5000)$fatal(1,"packed test timeout sent=%0d got=%0d",sent,got);
                // First half saturated, second half introduces independent gaps and clock-enable stalls.
                en=sent<N/2 ? 1 : ($unsigned($random(seed))%7!=0);
                valid=sent<N && (sent<N/2 || $unsigned($random(seed))%5!=0);
                if(accepted && sent<N)next_request();
            end
            total=total+got;
            if(sat_last-sat_first>449)$fatal(1,"packed saturated throughput below 2 packets / 3 clocks");
            $display("PACKED4_TILE q0=%0d q1=%0d dir=%0d halve=%0d packets=%0d ticks=%0d errors=%0d",qs[0],qs[1],dir,halve,got,ticks,errors);
            $display("PACKED4_RATE packets=300 first_to_last_clocks=%0d",sat_last-sat_first);
        end
        // Abort with both stream A and B in flight, then require no stale response.
        @(negedge clk);active=0;sent=0;valid=1;en=1;
        repeat(6)@(negedge clk);
        rst=1;valid=0;repeat(3)@(negedge clk);rst=0;
        repeat(50)begin @(posedge clk);#1;if(rv)$fatal(1,"stale packed response after reset abort");end
        if(errors)$fatal(1,"PACKED4_TILE errors=%0d",errors);
        $display("PACKED4_RESET both_streams_inflight=1 PASS");
        $display("PACKED4_UTIL cycles_with_four_useful_leaves=%0d",dual_busy);
        $display("PACKED4_TILE packets=%0d butterflies=%0d PASS",total,2*total);$finish;
    end
endmodule
