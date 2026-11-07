# Additional endpoint groups after inspecting mapped hierarchy names.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $workspace study build a_cg_z020_100mhz path_groups]
set_param general.maxThreads 4
open_checkpoint [file join $workspace study build a_cg_z020_100mhz route10 routed.dcp]
set_property HD.CLK_SRC BUFGCTRL_X0Y16 [get_ports clk]
update_timing -full
set regs [all_registers]
set p [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]
if {abs([get_property SLACK $p]-0.032)>0.002} {error "Original setup timing did not reproduce"}
set f [open [file join $out groups_supplement.tsv] w]
puts $f "group\tsources\tendpoints\tslack_ns\tlogic_levels\tstartpoint\tendpoint"
proc pick {patterns} {
    global regs
    set c {}
    foreach pattern $patterns {set c [concat $c [filter $regs "NAME =~ $pattern"]]}
    return [lsort -unique $c]
}
proc group {name sources endpoints} {
    global f out
    if {[llength $sources]==0 || [llength $endpoints]==0} {error "No registers in $name"}
    set paths [get_timing_paths -from $sources -to $endpoints -delay_type max -max_paths 1]
    if {[llength $paths]==0} {error "No path in $name"}
    set p [lindex $paths 0]
    puts $f "$name\t[llength $sources]\t[llength $endpoints]\t[get_property SLACK $p]\t[get_property LOGIC_LEVELS $p]\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
    flush $f
    report_timing -from $sources -to $endpoints -delay_type max -max_paths 3 -nworst 1 -unique_pins -file [file join $out ${name}.rpt]
    puts "GROUP_DONE $name WNS=[get_property SLACK $p]"
}
group montgomery $regs [pick {*u32_reg* *r32r_reg*}]
group bank_to_tile [pick {u_exec/data_bank*}] [pick {*req_x_reg* *req_y_reg*}]
group root_to_tile [pick {*root_mem*}] [pick {*u_tile/*}]
set root [lindex [pick {*root_mem*}] 0]
set info [open [file join $out root_output_registers.txt] w]
puts $info "CELL=$root"
puts $info "DOA_REG=[get_property DOA_REG $root]"
puts $info "DOB_REG=[get_property DOB_REG $root]"
close $info
group host_line_capture_all $regs [pick {u_exec/line_data_reg*}]
close $f
puts "TIMING_GROUP_SUPPLEMENT_DONE"
exit
