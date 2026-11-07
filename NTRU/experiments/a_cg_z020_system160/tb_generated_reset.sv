`timescale 1ns/1ps
module tb_generated_reset;
    reg clk=0; always #3.125 clk=~clk;
    reg ext_n, aux_n, locked;
    wire [0:0] resetn;
    system_resets_0 dut(.slowest_sync_clk(clk),.ext_reset_in(ext_n),
        .aux_reset_in(aux_n),.mb_debug_sys_rst(1'b0),.dcm_locked(locked),
        .mb_reset(),.bus_struct_reset(),.peripheral_reset(),.interconnect_aresetn(),.peripheral_aresetn(resetn));
    task cycles(input integer n);begin repeat(n)@(negedge clk);end endtask
    initial begin
        // Drive a real post-elaboration transition across the SV/VHDL boundary.
        #1;ext_n=0;aux_n=1;locked=0;
        cycles(64);if(resetn!==0)$fatal(1,"reset not asserted at startup: %b",resetn);
        ext_n=1;cycles(64);if(resetn!==0)$fatal(1,"released while MMCM unlocked");
        locked=1;cycles(64);if(resetn!==1)$fatal(1,"reset never releases (check aux polarity/tie)");
        ext_n=0;cycles(16);if(resetn!==0)$fatal(1,"PS reset not propagated");
        ext_n=1;cycles(64);if(resetn!==1)$fatal(1,"PS reset recovery failed");
        locked=0;cycles(16);if(resetn!==0)$fatal(1,"loss of lock not propagated");
        locked=1;cycles(64);if(resetn!==1)$fatal(1,"lock recovery failed");
        aux_n=0;cycles(16);if(resetn!==0)$fatal(1,"active-low auxiliary reset ignored");
        aux_n=1;cycles(64);if(resetn!==1)$fatal(1,"aux reset recovery failed");
        $display("GENERATED_RESET startup=1 lock_gate=1 ps_reset=1 lock_loss=1 aux_polarity=1 PASS");$finish;
    end
    initial begin #100000;$fatal(1,"reset test timeout");end
endmodule
