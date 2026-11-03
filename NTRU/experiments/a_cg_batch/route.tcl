# Core-only implementation of a frozen synthesis checkpoint. No board I/O,
# bitstream or production RTL edits. Usage: -tclargs packed|batch_only [period_ns]
set base [file normalize [file join [file dirname [info script]] ../..]]
set variant packed
if {[llength $argv]>0} {set variant [lindex $argv 0]}
if {$variant ni {packed batch_only}} {error "Expected packed or batch_only"}
set period 5.000
if {[llength $argv]>1} {set period [lindex $argv 1]}
set source_dir synth
if {$variant eq "batch_only"} {set source_dir batch_only_synth}
set checkpoint [file join $base study build a_cg_batch $source_dir synthesized.dcp]
set out [file join $base study build a_cg_batch route_${variant}_${period}]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint $checkpoint

# The virtual core boundary is synchronous to clk. Use the same constraints
# for both variants. Do not hide host/config/reset paths with false paths.
create_clock -period $period -name clk [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold 0.050 [get_clocks clk]
set inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -max 1.000 $inputs
set_input_delay -clock clk -min 0.000 $inputs
set_output_delay -clock clk -max 1.000 [all_outputs]
set_output_delay -clock clk -min 0.000 [all_outputs]

# An OOC clock has no board pin/IBUF/BUFG instance. Give timing a real,
# repeatable reference BUFGCE site instead of leaving HD.CLK_SRC unset.
set sites [lsort -dictionary [get_sites -filter {SITE_TYPE == BUFGCE}]]
if {[llength $sites]==0} {error "No BUFGCE site on target part"}
set clock_site [lindex $sites [expr {[llength $sites]/2}]]
set_property HD.CLK_SRC $clock_site [get_ports clk]
set f [open [file join $out run_config.txt] w]
puts $f "variant=$variant"
puts $f "checkpoint=$checkpoint"
puts $f "period_ns=$period"
puts $f "input_max_ns=1.000 input_min_ns=0.000"
puts $f "output_max_ns=1.000 output_min_ns=0.000"
puts $f "setup_uncertainty_ns=0.100 hold_uncertainty_ns=0.050"
puts $f "HD.CLK_SRC=$clock_site"
puts $f "part=[get_property PART [current_design]]"
puts $f "flow=opt_design;place_design;phys_opt_design;route_design"
puts $f "board_io=false bitstream=false"
close $f
write_xdc -force [file join $out constraints.xdc]
puts "A_CG_IMPLEMENT_START variant=$variant period=$period clock_site=$clock_site"

opt_design
place_design
report_utilization -file [file join $out placed_util.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out placed_timing.rpt]
phys_opt_design
route_design
report_route_status -file [file join $out route_status.rpt]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file [file join $out timing.rpt]
report_timing -delay_type max -max_paths 20 -sort_by group -file [file join $out setup_paths.rpt]
report_timing -delay_type min -max_paths 20 -sort_by group -file [file join $out hold_paths.rpt]
report_drc -file [file join $out drc.rpt]
report_power -file [file join $out power.rpt]
write_checkpoint -force [file join $out routed.dcp]
puts "A_CG_IMPLEMENT_DONE variant=$variant period=$period"
exit
