# Real PS7 + AXI + MMCM + reset integration; private project, no production RTL changes.
set root [file normalize [file join [file dirname [info script]] ../../../..]]
set exp [file join $root experiments paper_ablation31 variants split_domains]
set out [file join $root study build paper_ablation31 split_domains]
file mkdir $out
set_param general.maxThreads 4
if {[file exists [file join $out project]]} {error "Preserve existing private project"}
create_project acg_ablate_split_domains [file join $out project] -part xc7z020clg400-2 -force
foreach f {mul_ss.v tile_a.sv a_cg_fast.sv a_cg_axil.v} {add_files -norecurse [file join $exp rtl $f]}
set_property target_language Verilog [current_project]
update_compile_order -fileset sources_1
create_bd_design system
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps
set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_USE_M_AXI_GP1 {0} \
    CONFIG.PCW_EN_DDR {0} CONFIG.PCW_CRYSTAL_PERIPHERAL_FREQMHZ {33.333333} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} CONFIG.PCW_EN_CLK0_PORT {1} \
    CONFIG.PCW_EN_RST0_PORT {1} CONFIG.PCW_PRESET_BANK0_VOLTAGE {LVCMOS 3.3V} \
    CONFIG.PCW_PRESET_BANK1_VOLTAGE {LVCMOS 1.8V}] [get_bd_cells ps]
make_bd_intf_pins_external [get_bd_intf_pins ps/FIXED_IO]
create_bd_cell -type ip -vlnv xilinx.com:ip:clk_wiz:6.0 clock160
set_property -dict [list CONFIG.PRIM_IN_FREQ {100.000} CONFIG.CLKOUT1_REQUESTED_OUT_FREQ {160.000} \
    CONFIG.USE_RESET {false} CONFIG.USE_LOCKED {true}] [get_bd_cells clock160]
connect_bd_net [get_bd_pins ps/FCLK_CLK0] [get_bd_pins clock160/clk_in1]
create_bd_cell -type module -reference a_cg_axil accelerator
if {[llength [get_bd_intf_pins -quiet accelerator/s_axi]] != 1} {error "AXI inference failed"}
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] [get_bd_cells axi]
connect_bd_intf_net [get_bd_intf_pins ps/M_AXI_GP0] [get_bd_intf_pins axi/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi/M00_AXI] [get_bd_intf_pins accelerator/s_axi]
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 resets
connect_bd_net [get_bd_pins clock160/clk_out1] [get_bd_pins accelerator/aclk] \
    [get_bd_pins ps/M_AXI_GP0_ACLK] [get_bd_pins axi/ACLK] [get_bd_pins axi/S00_ACLK] \
    [get_bd_pins axi/M00_ACLK] [get_bd_pins resets/slowest_sync_clk]
connect_bd_net [get_bd_pins clock160/locked] [get_bd_pins resets/dcm_locked]
connect_bd_net [get_bd_pins ps/FCLK_RESET0_N] [get_bd_pins resets/ext_reset_in]
connect_bd_net [get_bd_pins resets/interconnect_aresetn] [get_bd_pins axi/ARESETN]
connect_bd_net [get_bd_pins resets/peripheral_aresetn] [get_bd_pins axi/S00_ARESETN] \
    [get_bd_pins axi/M00_ARESETN] [get_bd_pins accelerator/aresetn]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const0
set_property CONFIG.CONST_VAL {0} [get_bd_cells const0]
connect_bd_net [get_bd_pins const0/dout] [get_bd_pins resets/mb_debug_sys_rst]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const1
set_property CONFIG.CONST_VAL {1} [get_bd_cells const1]
connect_bd_net [get_bd_pins const1/dout] [get_bd_pins resets/aux_reset_in]
assign_bd_address
set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces ps/Data] -filter {NAME =~ *accelerator*}]
if {[llength $seg] != 1} {error "Cannot resolve accelerator address segment"}
set_property range 4K $seg
set_property offset 0x43C00000 $seg
validate_bd_design
if {[get_property CONFIG.C_EXT_RESET_HIGH [get_bd_cells resets]] != 0 ||
    [get_property CONFIG.C_AUX_RESET_HIGH [get_bd_cells resets]] != 0} {error "Reset polarity differs from inactive ties"}
save_bd_design
set bd [get_files system.bd]
set_property synth_checkpoint_mode None $bd
generate_target all $bd
# Vivado 2018.1 emits DDR pad constraints even with PCW_EN_DDR=0.
# Preserve its actual clock/PS pad constraints, omit only disabled DDR pads.
set original_xdc [file join [file dirname $bd] ip system_ps_0 system_ps_0.xdc]
set original_obj [get_files -all $original_xdc]
if {[llength $original_obj] != 1} {error "PS7 source constraints missing"}
set_property USED_IN_SYNTHESIS false $original_obj
set_property USED_IN_IMPLEMENTATION false $original_obj
set fh [open $original_xdc r]; set original_text [read $fh]; close $fh
set clean_xdc [file join $out ps7_no_ddr.xdc]
set fh [open $clean_xdc w]
puts $fh "# Derived from generated PS7 XDC; only disabled DDR pad constraints omitted."
foreach line [split $original_text "\n"] {
    if {[regexp {\[get_ports "DDR_} $line]} {continue}
    set line [string map {PS7_i/FCLKCLK inst/PS7_i/FCLKCLK} $line]
    puts $fh $line
}
close $fh
add_files -fileset constrs_1 -norecurse $clean_xdc
set_property SCOPED_TO_REF system_ps_0 [get_files $clean_xdc]
set_property PROCESSING_ORDER EARLY [get_files $clean_xdc]
set wrapper [make_wrapper -files $bd -top]
add_files -norecurse $wrapper
set_property top system_wrapper [current_fileset]
update_compile_order -fileset sources_1
set cfg [open [file join $out system_config.txt] w]
puts $cfg "PART=[get_property PART [current_project]]"
puts $cfg "PS_CRYSTAL_MHZ=[get_property CONFIG.PCW_CRYSTAL_PERIPHERAL_FREQMHZ [get_bd_cells ps]]"
puts $cfg "PS_ACT_FCLK0_MHZ=[get_property CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ [get_bd_cells ps]]"
puts $cfg "MMCM_OUT_MHZ=[get_property CONFIG.CLKOUT1_REQUESTED_OUT_FREQ [get_bd_cells clock160]]"
puts $cfg "DDR_ENABLED=[get_property CONFIG.PCW_EN_DDR [get_bd_cells ps]]"
puts $cfg "AXI_BASE=0x43C00000 AXI_RANGE=4K"
close $cfg
puts "SYSTEM_PROJECT_READY"
if {[lsearch -exact $argv synth] >= 0} {
    launch_runs synth_1 -jobs 4
    wait_on_run synth_1
    if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {error "System synthesis failed"}
    open_run synth_1
    report_utilization -file [file join $out synth_util.rpt]
    report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out synth_timing.rpt]
    write_checkpoint -force [file join $out system_synth.dcp]
    puts "SYSTEM_SYNTH_DONE"
}
exit
