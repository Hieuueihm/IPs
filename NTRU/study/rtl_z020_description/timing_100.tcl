# Read-only timing analysis of the existing synthesized netlist. No resynthesis,
# optimization, placement, routing, case analysis or path exceptions.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $workspace study build rtl_z020_description]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $workspace study build a_cg_z020_dispatch2 synth synthesized.dcp]
set regs [all_registers]
set old [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]
set old_wns [get_property SLACK $old]
if {abs($old_wns+3.604)>0.002} {error "Existing 5 ns timing did not reproduce: $old_wns"}
create_clock -name clk -period 10.000 [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold 0.050 [get_clocks clk]
set_input_delay -clock clk -max 1.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -min 0.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_output_delay -clock clk -max 1.000 [all_outputs]
set_output_delay -clock clk -min 0.000 [all_outputs]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing_100.rpt]
report_timing -from $regs -to $regs -delay_type max -max_paths 5 -file [file join $out internal_setup_100.rpt]
report_timing -from $regs -to $regs -delay_type min -max_paths 5 -file [file join $out internal_hold_100.rpt]
set setup [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]
set hold [get_timing_paths -from $regs -to $regs -delay_type min -max_paths 1]
set f [open [file join $out metrics_100.txt] w]
puts $f "PART=[get_property PART [current_design]]"
puts $f "PERIOD_NS=[get_property PERIOD [get_clocks clk]]"
puts $f "ORIGINAL_5NS_WNS=$old_wns"
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "REGISTER_COUNT=[llength $regs]"
puts $f "RESYNTHESIZED=false PLACED=false ROUTED=false RTL_MODIFIED=false"
close $f
write_xdc -force [file join $out constraints_100.xdc]
puts "Z020_100MHZ_ANALYSIS_DONE"
exit
