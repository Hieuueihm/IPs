# Whole prototype, including runtime configuration, host adapter, data RAM,
# direction-specific root RAM, stage descriptors and all sixteen engines.
set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_batch batch_only_synth]
file mkdir $out
set_param general.maxThreads 4
read_verilog [file join $base experiments a_cg_batch rtl mul_ss.v]
read_verilog -sv [file join $base experiments a_cg_batch rtl tile_a.sv]
read_verilog -sv [file join $base experiments a_cg_batch rtl batch_only.sv]
synth_design -top a_cg_fast -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy rebuilt
# Same synthesis-only reporting convention as study/build/core_area.
create_clock -period 5.000 [get_ports clk]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 5 -file [file join $out util_hier.rpt]
report_timing_summary -file [file join $out timing.rpt]
write_checkpoint -force [file join $out synthesized.dcp]
puts "A_CG_SYNTH_DONE"
exit
