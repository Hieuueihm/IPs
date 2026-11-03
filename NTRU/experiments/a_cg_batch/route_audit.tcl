# Inspect routed checkpoints without changing placement, nets or constraints.
set base [file normalize [file join [file dirname [info script]] ../..]]
set variant [lindex $argv 0]
if {$variant ni {packed batch_only}} {error "Expected packed or batch_only"}
set out [file join $base study build a_cg_batch route_${variant}_5.000]
set_param general.maxThreads 4
open_checkpoint [file join $out routed.dcp]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 10 -file [file join $out internal_setup_paths.rpt]
report_timing -from $registers -to $registers -delay_type min -max_paths 10 -file [file join $out internal_hold_paths.rpt]
set setup [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set hold [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out audit.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
set nr 0
set nd 0
foreach c [get_cells -hier -filter {REF_NAME == RAMB18E2}] {
    if {[string match *root_mem* $c]} {incr nr}
    if {[string match *data_bank* $c]} {incr nd}
}
puts $f "ROOT_RAMB18=$nr"
puts $f "DATA_RAMB18=$nd"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E2}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
close $f
if {$nr!=16 || $nd!=32} {error "Routed root/data memory count mismatch"}
puts "A_CG_ROUTE_AUDIT_DONE variant=$variant"
exit
