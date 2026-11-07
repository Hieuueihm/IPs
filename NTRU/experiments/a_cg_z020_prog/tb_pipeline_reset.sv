`timescale 1ns/1ps
// Focused protocol test: reset commands in each added stage, and a response
// arriving at reset recovery. Full arithmetic remains covered by frozen vectors.
module tb_pipeline_reset;
    reg clk=0; always #5 clk=~clk;
    reg rst=1,start=0;
    wire cfg_ready,load_ready,read_ready,read_rsp_valid,busy,done,error;
    wire [127:0] read_data;
    wire [31:0] cycles;
    a_cg_fast dut(
        .clk(clk),.rst(rst),.start(start),.cfg_valid(1'b0),.cfg_ready(cfg_ready),
        .cfg_fft(1'b0),.cfg_inverse(1'b0),.cfg_ntrugen(1'b0),.cfg_packed(1'b0),
        .cfg_jobs_log(3'd0),.cfg_fmt(2'd0),.cfg_hmin(2'd0),.cfg_logn(4'd8),
        .cfg_q(32'd12289),.cfg_qinv(32'd0),
        .root_we(1'b0),.root_commit(1'b0),.root_dest(16'd0),.root_addr(9'd0),.root_data(32'd0),
        .desc_we(1'b0),.desc_stage(4'd0),.desc_mask(16'd0),.desc_root_base(9'd0),.desc_root_mask(5'd0),.desc_gap(16'd0),
        .load_valid(1'b0),.load_ready(load_ready),.load_line(10'd0),.load_data(128'd0),
        .read_valid(1'b0),.read_ready(read_ready),.read_line(10'd0),
        .read_rsp_valid(read_rsp_valid),.read_data(read_data),.busy(busy),.done(done),.error(error),.cycles(cycles)
    );
    task tick; begin @(posedge clk); #1; end endtask
    integer phase,k;
    initial begin
        repeat(3)tick(); rst=0; repeat(2)tick();
        for(phase=0;phase<2;phase=phase+1)begin
            if(cfg_ready!==1)$fatal(1,"not ready after reset");
            start=1;tick();start=0;
            if(phase==1)tick();
            if(busy!==1)$fatal(1,"queued start not covered by busy at stage %0d",phase);
            rst=1;#1;
            if(busy!==0 || read_rsp_valid!==0)$fatal(1,"reset does not immediately mask interface");
            tick();rst=0;
            for(k=0;k<7;k=k+1)begin
                tick();
                if(done!==0 || busy!==0 || read_rsp_valid!==0 || load_ready!==0)
                    $fatal(1,"queued command leaked across reset at stage %0d",phase);
            end
        end
        // Producer-side injection isolates the new response pipeline's reset
        // behavior. It does not substitute for numerical or application tests.
        force dut.c_rsp_valid=1'b1;
        force dut.c_read_data=128'h0123456789abcdef_fedcba9876543210;
        tick();
        if(read_rsp_valid!==1 || read_data!==128'h0123456789abcdef_fedcba9876543210)
            $fatal(1,"response data/token are misaligned");
        rst=1;#1;
        if(read_rsp_valid!==0)$fatal(1,"pending response survives immediate reset masking");
        tick();rst=0;
        // Producer may retain its previous response until it sees delayed reset.
        tick();release dut.c_rsp_valid;release dut.c_read_data;
        if(read_rsp_valid!==0)$fatal(1,"stale response leaked at reset release");
        repeat(4)begin tick();if(read_rsp_valid!==0)$fatal(1,"stale response after reset");end
        $display("PIPELINE_RESET command_stages=2 response_flush=1 PASS");
        $finish;
    end
    initial begin #10000;$fatal(1,"pipeline reset timeout");end
endmodule
