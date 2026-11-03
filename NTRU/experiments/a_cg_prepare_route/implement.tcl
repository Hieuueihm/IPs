# Single fast timing-driven OOC implementation of the selected checkpoint.
set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_prepare_route fast]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $base study build a_cg_host_opt prepare_split synth synthesized.dcp]
# Preserve the 5 ns clock, uncertainty and I/O constraints in this checkpoint.
set sites [lsort -dictionary [get_sites -filter {SITE_TYPE == BUFGCE}]]
set clock_site [lindex $sites [expr {[llength $sites]/2}]]
set_property HD.CLK_SRC $clock_site [get_ports clk]
set f [open [file join $out run_config.txt] w]
puts $f "variant=prepare_split"
puts $f "clock_ns=5.000"
puts $f "HD.CLK_SRC=$clock_site"
puts $f "part=[get_property PART [current_design]]"
puts $f "place_directive=AltSpreadLogic_high"
puts $f "route_directive=RuntimeOptimized"
puts $f "scope=OOC core; boundary ports lack board/partition pin locations"
puts $f "RTL_changes=false resynthesis=false bitstream=false"
close $f
write_xdc -force [file join $out constraints.xdc]
puts "SELECTED_IMPLEMENT_START"
opt_design
place_design -directive AltSpreadLogic_high
write_checkpoint -force [file join $out placed.dcp]
puts "SELECTED_PLACEMENT_DONE"
phys_opt_design
route_design -directive RuntimeOptimized
puts "SELECTED_ROUTING_DONE"
# Write the result before diagnostic/reporting commands; never lose a finished
# route if a nonessential report encounters a version-specific issue.
write_checkpoint -force [file join $out routed.dcp]
report_route_status -file [file join $out route_status.rpt]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
report_drc -file [file join $out drc.rpt]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 5 -file [file join $out internal_setup.rpt]
report_timing -from $registers -to $registers -delay_type min -max_paths 5 -file [file join $out internal_hold.rpt]
set setup [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set hold [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "ROOT_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *root_mem*}]]"
puts $f "DATA_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *data_bank*}]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E2}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
close $f
puts "SELECTED_IMPLEMENT_DONE"
exit
