set base [file normalize [file join [file dirname [info script]] ../..]]
set dir [file join $base experiments a_cg_z020_100mhz rtl]
set out [file join $base study build a_cg_z020_100mhz synth10]
file mkdir $out
set_param general.maxThreads 4
set device [get_parts -quiet xc7z020clg400-2]
if {[llength $device] != 1} {error "XC7Z020 CLG400 -2 device support not installed"}
puts "TARGET_PART=$device"
read_verilog [file join $dir mul_ss.v]
read_verilog -sv [file join $dir tile_a.sv]
read_verilog -sv [file join $dir a_cg_fast.sv]
read_xdc [file join $base experiments a_cg_z020_100mhz clock_10ns.xdc]
synth_design -top a_cg_fast -part xc7z020clg400-2 -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $out util_hier.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing.rpt]
set registers [all_registers]
report_timing -from $registers -to $registers -delay_type max -max_paths 10 -file [file join $out internal_setup.rpt]
report_timing -from $registers -to $registers -delay_type min -max_paths 5 -file [file join $out internal_hold.rpt]
set setup [get_timing_paths -from $registers -to $registers -delay_type max -max_paths 1]
set hold [get_timing_paths -from $registers -to $registers -delay_type min -max_paths 1]
set f [open [file join $out metrics.txt] w]
puts $f "REGISTER_TO_REGISTER_WNS_NS=[get_property SLACK $setup]"
puts $f "REGISTER_TO_REGISTER_WHS_NS=[get_property SLACK $hold]"
puts $f "ROOT_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1 && NAME =~ *root_mem*}]]"
puts $f "DATA_RAMB18=[llength [get_cells -hier -filter {REF_NAME == RAMB18E1 && NAME =~ *data_bank*}]]"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E1}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
puts $f "LOCAL_RESETS=[llength [get_cells -hier -filter {NAME =~ *reset_local_reg}]]"
puts $f "LOCAL_CONFIGS=[llength [get_cells -hier -filter {NAME =~ *config_local_reg && REF_NAME == FDRE}]]"
close $f
write_checkpoint -force [file join $out synthesized.dcp]
set ext [get_ports -filter {DIRECTION == IN && NAME != clk}]
set internal_registers [filter [all_registers] {NAME =~ u_exec/*}]
set direct [get_timing_paths -from $ext -to $internal_registers -max_paths 1]
set f [open [file join $out command_barrier.txt] w]
puts $f "CORE_REGISTERS=[llength $internal_registers]"
puts $f "DIRECT_INPUT_TO_CORE_PATHS=[llength $direct]"
close $f
if {[llength $internal_registers] == 0 || [llength $direct] != 0} {error "Command register barrier incomplete"}
set dest [get_pins -of_objects [get_cells p_load_valid_reg] -filter {REF_PIN_NAME == D}]
set sources [get_cells -quiet -of_objects [all_fanin -flat -startpoints_only -to $dest]]
set bad [filter $sources {NAME == p_cfg_valid_reg}]
set f [open [file join $out occupancy_barrier.txt] w]
puts $f "LOAD_FLAG_P_CFG_DEPENDENCIES=[llength $bad]"
puts $f "OCCUPANCY_REGISTERS=[llength [get_cells -filter {NAME == reserved_reg}]]"
close $f
if {[llength $bad] != 0 || [llength [get_cells -filter {NAME == reserved_reg}]] != 1} {error "Distributed opcode feedback remains"}
set dest [get_pins -of_objects [get_cells p_load_valid_reg] -filter {REF_PIN_NAME == D}]
set cone [all_fanin -flat -startpoints_only -to $dest]
set source_cells [get_cells -quiet -of_objects $cone]
set global_reset [filter $source_cells {NAME == p_rst_reg}]
set raw_reset [filter $cone {NAME == rst}]
set local_live [filter $source_cells {NAME == frontend_live_reg}]
set f [open [file join $out frontend_reset_barrier.txt] w]
puts $f "LOAD_GLOBAL_RESET_DEPENDENCIES=[llength $global_reset]"
puts $f "LOAD_RAW_RESET_D_DEPENDENCIES=[llength $raw_reset]"
puts $f "LOAD_LOCAL_PERMISSION_DEPENDENCIES=[llength $local_live]"
close $f
if {[llength $global_reset] != 0 || [llength $raw_reset] != 0 || [llength $local_live] != 1} {error "Ingress reset isolation failed"}
set permission_path [get_timing_paths -from [get_cells frontend_live_reg] -to [get_pins reserved_reg/D] -delay_type max -max_paths 1]
set levels [get_property LOGIC_LEVELS $permission_path]
report_timing -from [get_cells frontend_live_reg] -to [get_pins reserved_reg/D] -delay_type max -max_paths 1 -file [file join $out reservation_permission.rpt]
set f [open [file join $out reservation_permission.txt] w]
puts $f "PERMISSION_TO_RESERVATION_LOGIC_LEVELS=$levels"
close $f
if {[llength $permission_path] != 1 || $levels > 1} {error "Permission traverses more than final reservation gate"}
# one command stage (p_*) since a_cg_z020_100mhz
set first_regs [filter [all_registers] {NAME =~ p_* && NAME != p_rst_reg}]
set second_regs [filter [all_registers] {NAME =~ q_*}]
set response_bypass [get_timing_paths -from $internal_registers -to [get_ports {read_data[*] read_rsp_valid}] -max_paths 1]
set f [open [file join $out dispatch_barrier.txt] w]
puts $f "COMMAND_STAGE_REGISTERS=[llength $first_regs]"
puts $f "SECOND_STAGE_REGISTERS=[llength $second_regs]"
puts $f "CORE_TO_READ_RESPONSE_BYPASS=[llength $response_bypass]"
close $f
if {[llength $first_regs] == 0 || [llength $second_regs] != 0 || [llength $response_bypass] != 0} {error "Command stage or response barrier incomplete"}
puts "CONTROL_SYNTH_DONE"
exit
