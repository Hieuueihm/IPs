# Matched OOC synthesis, full AXI host + data/root RAMs + all sixteen tiles.
# This is NOT routed/system sign-off. Pass baseline or candidate as tclarg.
set base [file normalize [file join [file dirname [info script]] ../..]]
set variant [lindex $argv 0]
if {$variant ni {baseline candidate candidate_shared_t}} {error "Expected baseline or candidate"}
set source a_cg_packed4
if {$variant eq "baseline"} {set source a_cg_z020_system160}
set dir [file join $base experiments $source rtl]
set tile_file [file join $dir tile_a.sv]
if {$variant eq "candidate"} {
    set tile_file [file join $base experiments a_cg_packed4 variants separate_history tile_a.sv]
}
set out [file join $base study build a_cg_packed4 synth_$variant]
file mkdir $out
set_param general.maxThreads 4
read_verilog [file join $dir mul_ss.v]
read_verilog -sv $tile_file
read_verilog -sv [file join $dir a_cg_fast.sv]
read_verilog [file join $dir a_cg_axil.v]
read_xdc [file join $base experiments a_cg_packed4 clock.xdc]
synth_design -top a_cg_axil -part xc7z020clg400-2 -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set regs [all_registers]
report_timing -from $regs -to $regs -delay_type max -max_paths 10 -file [file join $out internal_setup.rpt]
set setup [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]
set hold [get_timing_paths -from $regs -to $regs -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]"
puts $f "RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
close $f
write_checkpoint -force [file join $out synthesized.dcp]
puts "PACKED4_SYNTH_DONE $variant"
exit
