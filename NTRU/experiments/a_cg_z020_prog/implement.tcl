# One place-and-route of the synthesized a_cg_z020_prog core on XC7Z020-CLG400-2, 5 ns (constraints of synth.tcl).
# OOC core with host adapter and root cache; no board pins, no PS/AXI integration, no bitstream.
set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_z020_prog route]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $base study build a_cg_z020_prog synth synthesized.dcp]
set sites [lsort -dictionary [get_sites -filter {SITE_TYPE == BUFGCTRL}]]
set clock_site [lindex $sites [expr {[llength $sites]/2}]]
set_property HD.CLK_SRC $clock_site [get_ports clk]
set f [open [file join $out run_config.txt] w]
puts $f "clock_ns=5.000 HD.CLK_SRC=$clock_site part=[get_property PART [current_design]]"
puts $f "opt_design Explore, place_design Explore, phys_opt_design Explore, route_design Explore"
close $f
opt_design -directive Explore
place_design -directive Explore
write_checkpoint -force [file join $out placed.dcp]
puts "PLACE_DONE"
phys_opt_design -directive Explore
route_design -directive Explore
write_checkpoint -force [file join $out routed.dcp]
report_route_status -file [file join $out route_status.rpt]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 20 -nworst 1 -unique_pins -file [file join $out internal_setup.rpt]
report_timing -from $registers -to $registers -delay_type min -max_paths 5 -file [file join $out internal_hold.rpt]
set setup [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set hold [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]"
puts $f "RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1}]]"
close $f
set ps [get_timing_paths -from $registers -to $registers -setup -max_paths 20000 -nworst 1 -unique_pins -slack_lesser_than 0.0]
set f [open [file join $out failing_endpoints.txt] w]
foreach p $ps { puts $f "[get_property SLACK $p] [get_property LOGIC_LEVELS $p] [get_property STARTPOINT_PIN $p] [get_property ENDPOINT_PIN $p]" }
close $f
puts "IMPLEMENT_DONE"
exit
