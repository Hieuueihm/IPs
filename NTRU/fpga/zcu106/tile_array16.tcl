# vivado -mode batch -source fpga/zcu106/tile_array16.tcl -tclargs <EN_REG 0|1> [TREN_MANG, default 1]
# Measurement of the global stall: 16 acceptance tiles (hdl/tile/tile_thu.sv) behind one shared en
# register, OOC, default opt/place/route, 3.0 ns. Reports go to study/build/tile_array16_en<EN_REG>_v<TREN_MANG>.
set enreg [lindex $argv 0]
set variant [lindex $argv 1]
if {$variant eq ""} { set variant 1 }
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/tile_array16_en${enreg}_v$variant]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv hdl/tile/tile_thu.sv
read_verilog -sv hdl/tile/tile_array16_top.sv
synth_design -top tile_array16_top -part xczu7ev-ffvc1156-2-e -mode out_of_context \
    -generic TREN_MANG=$variant -generic EN_REG=$enreg
create_clock -name clk -period 3.000 [get_ports clk]
opt_design
place_design
route_design
report_utilization -file [file join $out util_route.rpt]
report_utilization -hierarchical -hierarchical_depth 2 -file [file join $out util_route_hier.rpt]
report_timing_summary -file [file join $out timing_route.rpt]
report_timing -max_paths 10 -file [file join $out timing_paths.rpt]
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set en_fo [get_property FLAT_PIN_COUNT [get_nets -of [get_pins en_reg/Q]]]
puts "ARRAY16_DONE en_reg=$enreg WNS=$wns en_net_pins=$en_fo"
