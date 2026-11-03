# vivado -mode batch -source fpga/zcu106/synth.tcl
# OOC synthesis of the complete AXI-Lite core. No board pins are assumed.
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/zcu106_ooc]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
set_property include_dirs [list [file join $root hdl/proto]] [current_fileset]
set sources [list hdl/mul_ss.v hdl/proto/flex_stream_tile.sv hdl/proto/flex_stream_array.sv \
    hdl/proto/ntt_bank_permute64.sv hdl/core/flex_banked_scratch.sv \
    hdl/core/flex_kernel_rom.sv hdl/core/flex_kernel_engine.sv hdl/core/flex_kernel_axil.sv]
foreach src $sources {read_verilog -sv $src}
synth_design -top flex_kernel_axil -part xczu7ev-ffvc1156-2-e -mode out_of_context
create_clock -name core_clk -period 10.000 [get_ports aclk]
set_clock_uncertainty 0.100 [get_clocks core_clk]
set_input_delay 0.200 -clock core_clk [get_ports -filter {DIRECTION == IN && NAME != aclk}]
set_output_delay 0.200 -clock core_clk [get_ports -filter {DIRECTION == OUT}]
report_utilization -hierarchical -file [file join $out utilization.rpt]
report_timing_summary -file [file join $out timing_synth.rpt]
report_drc -file [file join $out drc_synth.rpt]
write_checkpoint -force [file join $out kernel_synth.dcp]
puts "FLEX_SYNTH_COMPLETE $out"
