"""Generate post-route pin/routing refinement; keep the cold result unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'implement_cold.tcl').read_text()
reports=source[source.index('report_route_status -file'):]
prefix='''set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_cmd_credit route_pinopt]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $base study build a_cg_cmd_credit route routed.dcp]
# HD.CLK_SRC is not retained by this Vivado version when reopening the routed
# OOC checkpoint. Restore the EXACT cold-run source before timing/optimization.
set_property HD.CLK_SRC BUFGCE_X1Y48 [get_ports clk]
update_timing -full
set before_regs [all_registers]
set before_setup [get_timing_paths -from $before_regs -to $before_regs -delay_type max -max_paths 1]
set before_hold [get_timing_paths -from $before_regs -to $before_regs -delay_type min -max_paths 1]
set before_wns [get_property SLACK $before_setup]
set before_whs [get_property SLACK $before_hold]
if {abs($before_wns - (-0.003)) > 0.001 || abs($before_whs-0.010) > 0.001} {
    error "Reopened checkpoint does not reproduce cold timing: WNS=$before_wns WHS=$before_whs"
}
report_timing -from $before_regs -to $before_regs -delay_type max -max_paths 1 -file [file join $out baseline_internal.rpt]
puts "COLD_TIMING_REPRODUCED WNS=$before_wns WHS=$before_whs"
set f [open [file join $out run_config.txt] w]
puts $f "source=route/routed.dcp clock_ns=5.000 unchanged_constraints=true"
puts $f "optimization=critical_pin_opt then routing_opt/rewire/critical_cell_opt"
puts $f "retiming=false RTL_change=false"
puts $f "HD.CLK_SRC=BUFGCE_X1Y48 baseline_WNS=$before_wns baseline_WHS=$before_whs"
close $f
puts "PINOPT_START"
phys_opt_design -critical_pin_opt
phys_opt_design -routing_opt -rewire -critical_cell_opt
route_design -preserve -directive RuntimeOptimized
write_checkpoint -force [file join $out routed.dcp]
write_xdc -force [file join $out constraints.xdc]
puts "PINOPT_ROUTING_DONE"
'''
(HERE/'pinopt.tcl').write_text(prefix+reports)
print('Physical pin/routing refinement prepared; no timing constraint or RTL change.')
