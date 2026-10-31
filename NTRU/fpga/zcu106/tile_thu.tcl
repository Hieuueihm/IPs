# vivado -mode batch -source fpga/zcu106/tile_thu.tcl -tclargs <TREN_MANG 0|1|2> [place directive]
# With a place directive the reports go to study/build/tile_thu_<variant>_<directive>.
# Environment: TILE_RTL = RTL file (default the draft hdl/tile_thu/tile_thu.sv); TILE_TAG = prefix of the
# report folder (default tile_thu); TILE_GENERIC = extra generics, e.g. "IN_REG:1,EN_REG:1" (":" because cmd.exe splits "=").
# DRAFT measurement of the tile test block (spec 2.0, 10_hop_dong_tile.md section 8).
# OOC synthesis + default opt/place/route, 3.0 ns clock, no Xilinx primitives in RTL.
set variant [lindex $argv 0]
set pdir [lindex $argv 1]
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set rtl hdl/tile_thu/tile_thu.sv
if {[info exists ::env(TILE_RTL)]} { set rtl $::env(TILE_RTL) }
set tag tile_thu
if {[info exists ::env(TILE_TAG)]} { set tag $::env(TILE_TAG) }
set out [file join $root study/build/${tag}_$variant]
if {$pdir ne ""} { set out ${out}_$pdir }
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv $rtl
set extra {}
if {[info exists ::env(TILE_GENERIC)]} { foreach g [split $::env(TILE_GENERIC) " ,"] { if {$g ne ""} { lappend extra -generic [string map {: =} $g] } } }
synth_design -top tile_thu_top -part xczu7ev-ffvc1156-2-e -mode out_of_context -generic TREN_MANG=$variant {*}$extra
create_clock -name clk -period 3.000 [get_ports clk]
report_utilization -hierarchical -file [file join $out util_synth_hier.rpt]
opt_design
if {$pdir ne ""} { place_design -directive $pdir } else { place_design }
route_design
report_utilization -file [file join $out util_route.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $out util_route_hier.rpt]
report_timing_summary -file [file join $out timing_route.rpt]
report_timing -max_paths 10 -file [file join $out timing_paths.rpt]
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
puts "TILE_THU_DONE variant=$variant place=$pdir WNS=$wns"
