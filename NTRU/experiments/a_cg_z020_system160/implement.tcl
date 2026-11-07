set root [file normalize [file join [file dirname [info script]] ../..]]
set exp [file join $root experiments a_cg_z020_system160]
set out [file join $root study build a_cg_z020_system160 route]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $root study build a_cg_z020_system160 system_synth.dcp]
source [file join $exp signoff.tcl]
# No OOC clock-location assumption or raw-core input/output-delay assumptions.
opt_design
place_design
write_checkpoint -force [file join $out placed.dcp]
phys_opt_design
route_design
write_checkpoint -force [file join $out routed.dcp]
report_route_status -file [file join $out route_status.rpt]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
report_timing -delay_type max -max_paths 30 -file [file join $out setup.rpt]
report_timing -delay_type min -max_paths 20 -file [file join $out hold.rpt]
report_drc -file [file join $out drc.rpt]
report_clocks -file [file join $out clocks.rpt]
report_clock_interaction -file [file join $out clock_interaction.rpt]
report_cdc -details -file [file join $out cdc.rpt]
report_exceptions -file [file join $out exceptions.rpt]
check_timing -verbose -file [file join $out check_timing.rpt]
set f [open [file join $out metrics.txt] w]
puts $f "FULL_WNS_NS=[get_property SLACK [get_timing_paths -setup -max_paths 1]]"
puts $f "FULL_WHS_NS=[get_property SLACK [get_timing_paths -hold -max_paths 1]]"
puts $f "SETUP_FAILING=[llength [get_timing_paths -setup -max_paths 100000 -nworst 1 -slack_lesser_than 0.0]]"
puts $f "HOLD_FAILING=[llength [get_timing_paths -hold -max_paths 100000 -nworst 1 -slack_lesser_than 0.0]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]"
puts $f "RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1}]]"
puts $f "PS7=[llength [get_cells -hier -filter {REF_NAME == PS7}]]"
puts $f "MMCM=[llength [get_cells -hier -filter {REF_NAME == MMCME2_ADV}]]"
puts $f "BLACKBOX=[llength [get_cells -quiet -hier -filter {IS_BLACKBOX == 1}]]"
close $f
puts "SYSTEM_IMPLEMENT_DONE"
exit
