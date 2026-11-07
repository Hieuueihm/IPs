# Re-analyse the completed route with the real PS-rooted generated clock.
set root [file normalize [file join [file dirname [info script]] ../..]]
set exp [file join $root experiments a_cg_z020_system160]
set out [file join $root study build a_cg_z020_system160 route]
set_param general.maxThreads 4
open_checkpoint [file join $out routed.dcp]
source [file join $exp signoff.tcl]
update_timing -full
report_clocks -file [file join $out clocks.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
report_timing -delay_type max -max_paths 30 -file [file join $out setup.rpt]
report_timing -delay_type min -max_paths 20 -file [file join $out hold.rpt]
check_timing -verbose -file [file join $out check_timing.rpt]
report_clock_interaction -file [file join $out clock_interaction.rpt]
report_cdc -details -file [file join $out cdc.rpt]
report_exceptions -file [file join $out exceptions.rpt]
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
write_checkpoint -force [file join $out signoff.dcp]
puts "SYSTEM_AUDIT_DONE"
exit
