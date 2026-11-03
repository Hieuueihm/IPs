set base [file normalize [file join [file dirname [info script]] ../..]]
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
report_route_status -file [file join $out route_status.rpt]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
report_drc -file [file join $out drc.rpt]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 10 -file [file join $out internal_setup.rpt]
report_timing -from $registers -to $registers -delay_type min -max_paths 5 -file [file join $out internal_hold.rpt]
set core_registers [filter $registers {NAME =~ u_exec/*}]
report_timing -from $core_registers -to $core_registers -delay_type max -max_paths 5 -file [file join $out execution_setup.rpt]
report_timing -from $core_registers -to $core_registers -delay_type min -max_paths 5 -file [file join $out execution_hold.rpt]
set core_setup [get_timing_paths -from $core_registers -to $core_registers -delay_type max -max_paths 1]
set core_hold [get_timing_paths -from $core_registers -to $core_registers -delay_type min -max_paths 1]
set reset_registers [get_cells -hier -filter {NAME =~ *reset_local_reg}]
report_timing -from $registers -to $reset_registers -delay_type max -max_paths 5 -file [file join $out reset_feed.rpt]
report_timing -from $reset_registers -to $registers -delay_type max -max_paths 5 -file [file join $out reset_tree.rpt]
set config_inputs [get_ports -filter {DIRECTION == IN && NAME =~ cfg_*}]
report_timing -from $config_inputs -delay_type max -max_paths 5 -file [file join $out config_boundary.rpt]
set setup [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set hold [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "EXECUTION_CORE_WNS_NS=[get_property SLACK $core_setup]"
puts $f "EXECUTION_CORE_WHS_NS=[get_property SLACK $core_hold]"
puts $f "ROOT_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *root_mem*}]]"
puts $f "DATA_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *data_bank*}]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E2}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
puts $f "LOCAL_RESETS=[llength [get_cells -hier -filter {NAME =~ *reset_local_reg}]]"
puts $f "LOCAL_CONFIGS=[llength [get_cells -hier -filter {NAME =~ *config_local_reg && REF_NAME == FDRE}]]"
close $f
set f [open [file join $out reset_distribution.txt] w]
foreach cell [get_cells -hier -filter {NAME =~ *reset_local_reg}] {
    set net [get_nets -of_objects [get_pins -of_objects $cell -filter {REF_PIN_NAME == Q}]]
    puts $f "$cell loads=[llength [get_pins -leaf -of_objects $net -filter {DIRECTION == IN}]]"
}
close $f
puts "CONTROL_IMPLEMENT_DONE"
exit
