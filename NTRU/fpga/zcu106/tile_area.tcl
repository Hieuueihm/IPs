# Synthesis-only area of one tile (tile_thu_top, TREN_MANG = 1, IN_REG = 1 as in the core); reports in study/build/tile_area/<tag>.
# Args: <tag> <tile rtl file>
# [period ns, default 5.0 since 02/11/2026; the clock is set after synth_design, so it changes only the WNS line].
set tag [lindex $argv 0]
set rtl [lindex $argv 1]
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/tile_area/$tag]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv $rtl
synth_design -top tile_thu_top -part xczu7ev-ffvc1156-2-e -mode out_of_context -generic TREN_MANG=1 -generic IN_REG=1
set period [expr {[llength $argv] > 2 ? [lindex $argv 2] : 5.000}]
create_clock -name clk -period $period [get_ports clk]
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 2 -file [file join $out util_hier.rpt]
report_timing -max_paths 5 -file [file join $out timing.rpt]
puts "TILE_AREA_DONE $tag"
