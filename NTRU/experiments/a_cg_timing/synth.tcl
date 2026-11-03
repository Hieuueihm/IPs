# Synthesis only. Every variant includes host, roots and runtime packed16.
set base [file normalize [file join [file dirname [info script]] ../..]]
set variant [lindex $argv 0]
if {$variant ni {base host local raw all}} {error "Unknown variant"}
set dir [file join $base experiments a_cg_timing $variant rtl]
set out [file join $base study build a_cg_timing $variant synth]
file mkdir $out
set_param general.maxThreads 4
read_verilog [file join $dir mul_ss.v]
read_verilog -sv [file join $dir tile_a.sv]
read_verilog -sv [file join $dir a_cg_fast.sv]
read_xdc [file join $base experiments a_cg_timing clock.xdc]
synth_design -top a_cg_fast -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set registers [all_registers]
set pmax [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set pmin [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $pmax]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $pmin]"
puts $f "ROOT_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *root_mem*}]]"
puts $f "DATA_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E2 && NAME =~ *data_bank*}]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E2}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
close $f
report_timing -from $registers -to $registers -delay_type max -max_paths 10 -file [file join $out internal_paths.rpt]
# Check intended replication and remaining loads on configuration controls.
set f [open [file join $out control_fanout.txt] w]
foreach c [get_cells -hier -filter {REF_NAME == FDRE || REF_NAME == FDSE}] {
    set original [get_property -quiet ORIG_CELL_NAME $c]
    if {$original eq ""} {set original [get_property NAME $c]}
    set leaf [lindex [split $original /] end]
    if {[regexp {^(dir|mf|native_r|fmt_r|shift_r|halve_r|md)_reg} $leaf]} {
        set q [get_pins -of_objects $c -filter {REF_PIN_NAME == Q}]
        set net [get_nets -of_objects $q]
        set loads [get_pins -leaf -of_objects $net -filter {DIRECTION == IN}]
        puts $f "$c fanout=[llength $loads] dont_touch=[get_property DONT_TOUCH $c]"
    }
}
close $f
write_checkpoint -force [file join $out synthesized.dcp]
puts "TIMING_SYNTH_DONE variant=$variant"
exit
