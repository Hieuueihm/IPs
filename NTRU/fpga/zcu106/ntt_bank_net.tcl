# vivado -mode batch -source fpga/zcu106/ntt_bank_net.tcl
# DRAFT measurement of the bank -> tile network (hdl/net/ntt_bank_net.sv): OOC, default opt/place/route,
# 3.0 ns. Splits the LUTs by the register they feed: read operands (op_x, op_y, xh), roots (op_w),
# write data (bank_wd). Reports go to study/build/ntt_bank_net.
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/ntt_bank_net]
file mkdir $out
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog -sv hdl/net/ntt_bank_net.sv
read_verilog -sv hdl/net/ntt_bank_net_top.sv
synth_design -top ntt_bank_net_top -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name clk -period 3.000 [get_ports clk]
# LUTs by the register they feed (fan-in cones of each group's registers)
set fh [open [file join $out lut_split.txt] w]
foreach {name pat} {read "*op_x_reg* *op_y_reg* *xh_reg*" root "*op_w_reg*" write "*bank_wd_reg*"} {
    set regs [get_cells -hier -filter "IS_SEQUENTIAL" $pat]
    set luts [get_cells -quiet [all_fanin -flat -only_cells [get_pins -of $regs -filter {DIRECTION == IN}]] -filter {REF_NAME =~ LUT*}]
    set mux [get_cells -quiet [all_fanin -flat -only_cells [get_pins -of $regs -filter {DIRECTION == IN}]] -filter {REF_NAME =~ MUXF*}]
    puts $fh "$name regs [llength $regs] luts [llength $luts] muxf [llength $mux]"
}
close $fh
opt_design
place_design
route_design
report_utilization -file [file join $out util_route.rpt]
report_timing_summary -file [file join $out timing_route.rpt]
report_timing -max_paths 10 -file [file join $out timing_paths.rpt]
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
puts "BANK_NET_DONE WNS=$wns"
