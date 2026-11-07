# Read-only STA recheck: do not replace accepted reports, manifests or DCP.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
set checkpoint [file join $workspace study build a_cg_z020_system160 route signoff.dcp]
if {![file exists $checkpoint]} {error "Accepted signoff.dcp missing; restore the pinned baseline assets."}
set out [file join $workspace study build z020_baseline_audit]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint $checkpoint
update_timing -full
report_utilization -file [file join $out util.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
report_timing -delay_type max -max_paths 20 -file [file join $out setup.rpt]
report_timing -delay_type min -max_paths 20 -file [file join $out hold.rpt]
report_clocks -file [file join $out clocks.rpt]
check_timing -verbose -file [file join $out check_timing.rpt]
report_cdc -details -file [file join $out cdc.rpt]
report_exceptions -file [file join $out exceptions.rpt]
puts "BASELINE_AUDIT_DONE reports=$out"
exit
