# Same numerical modes, chip, clock, host/data/root scope for every ablation.
set root [file normalize [file join [file dirname [info script]] ../..]]
set variant [lindex $argv 0]
set dir [file join $root experiments paper_ablation31 variants $variant rtl]
set out [file join $root study build paper_ablation31 $variant synth]
if {[file exists [file join $out synthesized.dcp]]} {error "Preserve completed ablation synthesis"}
file mkdir $out
set_param general.maxThreads 2
read_verilog [file join $dir mul_ss.v]
read_verilog -sv [file join $dir tile_a.sv]
read_verilog -sv [file join $dir a_cg_fast.sv]
read_verilog [file join $dir a_cg_axil.v]
read_xdc [file join $root experiments a_cg_packed4 clock.xdc]
synth_design -top a_cg_axil -part xc7z020clg400-2 -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 12 -file [file join $out hierarchy.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set regs [all_registers]
report_timing -from $regs -to $regs -delay_type max -max_paths 10 -file [file join $out setup.rpt]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK [get_timing_paths -from $regs -to $regs -delay_type min -max_paths 1]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]"
puts $f "RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
close $f
write_checkpoint -force [file join $out synthesized.dcp]
puts "ABLATION_SYNTH_DONE $variant"
exit
