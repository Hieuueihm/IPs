set base [file normalize [file join [file dirname [info script]] ../..]]
set dir [file join $base experiments a_cg_control_gate rtl]
set out [file join $base study build a_cg_control_gate synth]
file mkdir $out
set_param general.maxThreads 4
read_verilog [file join $dir mul_ss.v]
read_verilog -sv [file join $dir tile_a.sv]
read_verilog -sv [file join $dir a_cg_fast.sv]
read_xdc [file join $base experiments a_cg_host_opt clock.xdc]
synth_design -top a_cg_fast -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 10 -file [file join $out internal_setup.rpt]
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
puts $f "LOCAL_RESETS=[llength [get_cells -hier -filter {NAME =~ *reset_local_reg && REF_NAME == FDRE}]]"
puts $f "LOCAL_CONFIGS=[llength [get_cells -hier -filter {NAME =~ *config_local_reg && REF_NAME == FDRE}]]"
close $f
write_checkpoint -force [file join $out synthesized.dcp]
set checked 0
set dependencies 0
set f [open [file join $out host_ce_fanin.txt] w]
foreach cell [get_cells -hier -filter {NAME =~ host_line_reg*}] {
    set ce [get_pins -of_objects $cell -filter {REF_PIN_NAME == CE}]
    if {[llength $ce] == 0} {continue}
    incr checked
    set starts [all_fanin -flat -startpoints_only -to $ce]
    set source_cells [get_cells -quiet -of_objects $starts]
    set found [filter $source_cells {NAME =~ *cfg_pipe_reg*}]
    incr dependencies [llength $found]
    puts $f "$cell config_pipeline_sources=[llength $found]"
}
puts $f "CHECKED_REGISTERS=$checked"
puts $f "CFG_PIPE_DEPENDENCIES=$dependencies"
close $f
if {$checked == 0 || $dependencies != 0} {error "Redundant host CE dependency remains"}
puts "CONTROL_SYNTH_DONE"
exit
