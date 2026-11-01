# vivado -mode batch -source fpga/zcu106/ntt_core.tcl
# Minimal NTT core (hdl/core_ntt/ntt_core.sv): OOC synthesis + default opt/place/route, 3.0 ns, no Xilinx primitives.
# Reports go to study/build/ntt_core.
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/ntt_core]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv hdl/tile/tile_thu.sv
read_verilog -sv hdl/net/ntt_bank_net_s.sv
read_verilog -sv hdl/core/flex_banked_scratch.sv
read_verilog -sv hdl/core_ntt/ntt_core_gen.sv
read_verilog -sv hdl/core_ntt/ntt_core.sv
synth_design -top ntt_core -part xczu7ev-ffvc1156-2-e -mode out_of_context
create_clock -name clk -period 3.000 [get_ports clk]
opt_design
place_design
route_design
report_utilization -file [file join $out util_route.rpt]
report_utilization -hierarchical -hierarchical_depth 2 -file [file join $out util_route_hier.rpt]
report_timing_summary -file [file join $out timing_route.rpt]
report_timing -max_paths 10 -file [file join $out timing_paths.rpt]
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
puts "NTT_CORE_DONE WNS=$wns"
