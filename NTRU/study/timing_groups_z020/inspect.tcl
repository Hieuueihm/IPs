# Read-only inspection of the routed 100 MHz design. Restore OOC clock origin
# because Vivado 2018.1 does not preserve HD.CLK_SRC on checkpoint reopening.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $workspace study build a_cg_z020_100mhz path_groups]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $workspace study build a_cg_z020_100mhz route10 routed.dcp]
set_property HD.CLK_SRC BUFGCTRL_X0Y16 [get_ports clk]
update_timing -full
if {[get_property PERIOD [get_clocks clk]] != 10.0} {error "Unexpected clock period"}
set regs [all_registers]
set summary [open [file join $out groups.tsv] w]
puts $summary "group\tsources\tendpoints\tslack_ns\tlogic_levels\tstartpoint\tendpoint"
proc select_regs {patterns} {
    global regs
    set result {}
    foreach pattern $patterns {
        set result [concat $result [filter $regs "NAME =~ $pattern"]]
    }
    return [lsort -unique $result]
}
proc inspect_group {name sources endpoints} {
    global out summary
    if {[llength $sources] == 0 || [llength $endpoints] == 0} {
        puts $summary "$name\t[llength $sources]\t[llength $endpoints]\tNONE\t0\t-\t-"
        puts "GROUP_EMPTY $name"
        flush $summary
        return
    }
    set paths [get_timing_paths -from $sources -to $endpoints -delay_type max -max_paths 1 -nworst 1]
    if {[llength $paths] == 0} {
        puts $summary "$name\t[llength $sources]\t[llength $endpoints]\tNO_PATH\t0\t-\t-"
        puts "GROUP_NO_PATH $name"
        flush $summary
        return
    }
    set p [lindex $paths 0]
    puts $summary "$name\t[llength $sources]\t[llength $endpoints]\t[get_property SLACK $p]\t[get_property LOGIC_LEVELS $p]\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
    flush $summary
    report_timing -from $sources -to $endpoints -delay_type max -max_paths 3 -nworst 1 -unique_pins -file [file join $out ${name}.rpt]
    puts "GROUP_DONE $name WNS=[get_property SLACK $p]"
}
set baseline [get_timing_paths -from $regs -to $regs -delay_type max -max_paths 1]
set hold [get_timing_paths -from $regs -to $regs -delay_type min -max_paths 1]
if {abs([get_property SLACK $baseline]-0.032)>0.002 || abs([get_property SLACK $hold]-0.051)>0.002} {
    error "Routed timing did not reproduce at the original clock source"
}
puts "ORIGINAL_TIMING_REPRODUCED setup=[get_property SLACK $baseline] hold=[get_property SLACK $hold]"
inspect_group all_internal $regs $regs
set non_rounding [filter $regs {NAME !~ u_exec/rs_sum_reg*}]
inspect_group except_rounding $regs $non_rounding
set tiles [select_regs {*u_tile/*}]
inspect_group tile_all $regs $tiles
inspect_group tile_to_tile $tiles $tiles
inspect_group fft_accumulator $regs [select_regs {*u_tile/wacc_reg* *u_tile/wpl_reg*}]
inspect_group fft_T $regs [select_regs {*u_tile/wps_reg* *u_tile/t5_reg*}]
inspect_group operand_stage $regs [select_regs {*u_tile/a1_reg* *u_tile/s1_reg* *u_tile/nhp0_reg*}]
inspect_group fft_limb_sums $regs [select_regs {*u_tile/sa5_reg* *u_tile/sw5_reg* *u_tile/wmsx_reg* *u_tile/wmsw_reg*}]
inspect_group montgomery $regs [select_regs {*u_tile/g_arr32/u32_reg* *u_tile/g_arr32/r32r_reg*}]
inspect_group multiplier $regs [select_regs {*u_tile/leaves/*}]
inspect_group tile_response $regs [select_regs {*u_tile/rd_reg* *u_tile/rt_reg* *u_tile/rv_reg*}]
inspect_group bank_to_tile [select_regs {u_exec/data_bank*}] [select_regs {u_exec/req_x_reg* u_exec/req_y_reg*}]
inspect_group host_read_select [select_regs {u_exec/data_bank*}] [select_regs {u_exec/line_data_reg*}]
inspect_group host_shift $regs [select_regs {rsp_data_q_reg*}]
inspect_group data_bank_write $regs [select_regs {u_exec/data_bank*}]
inspect_group root_load $regs [select_regs {*root_mem*}]
inspect_group root_to_tile [select_regs {*root_mem*}] [select_regs {u_exec/req_root_reg*}]
inspect_group program_broadcast [select_regs {u_exec/e_step_reg* u_exec/e_product_reg*}] $tiles
inspect_group context_config $regs [select_regs {*u_tile/q0_reg* *u_tile/qi0_reg* *u_tile/fmt_r_reg* *u_tile/md_reg* *u_tile/dir_reg*}]
inspect_group reset_from_frontend [select_regs {p_rst_reg}] $regs
close $summary
puts "TIMING_GROUP_INSPECTION_DONE"
exit
