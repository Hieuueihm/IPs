# vivado -mode batch -source fpga/zcu106/tile_thu_breakdown.tcl -tclargs <tag> <top> [GENERIC=value ...]
# Synthesis-only LUT/FF breakdown of the draft tile and of one butterfly lane.
# -flatten_hierarchy none keeps logic inside the instance that owns it in the RTL, so the
# per-instance counts are not the post-route counts of tile_thu.tcl (those move logic across
# boundaries). Reports go to study/build/tile_breakdown/<tag>.
set tag [lindex $argv 0]
set top [lindex $argv 1]
set gens [lrange $argv 2 end]
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/tile_breakdown/$tag]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv hdl/tile_thu/tile_thu.sv
set g {}
# cmd.exe splits NAME=VALUE at "=", so the arguments arrive as NAME VALUE pairs.
foreach {n v} $gens { lappend g -generic $n=$v }
synth_design -top $top -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy none {*}$g
report_utilization -hierarchical -file [file join $out util_hier.rpt]
report_utilization -file [file join $out util.rpt]
puts "BREAKDOWN_DONE $tag"
