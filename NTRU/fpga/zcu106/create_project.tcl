# Create a ZCU106 PS->AXI-Lite project; optional final argument "build" runs implementation.
# vivado -mode batch -source fpga/zcu106/create_project.tcl [-tclargs build]
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/zcu106_project]
create_project flex_zcu106 $out -part xczu7ev-ffvc1156-2-e -force
set boards [get_board_parts -quiet xilinx.com:zcu106:part0:*]
if {[llength $boards]==0} {error "Install the ZCU106 board files for this Vivado release"}
set_property board_part [lindex [lsort -dictionary $boards] end] [current_project]
set_property include_dirs [list $root [file join $root hdl/proto]] [current_fileset]
set_property verilog_define [list "FLEX_ROM_DIR=\"[file join $root hdl/core/rom]/\""] [current_fileset]
set sources [list hdl/mul_ss.v hdl/proto/flex_stream_tile.sv hdl/proto/flex_stream_array.sv \
    hdl/proto/ntt_bank_permute64.sv hdl/core/flex_banked_scratch.sv \
    hdl/core/flex_kernel_rom.sv hdl/core/flex_kernel_engine.sv hdl/core/flex_kernel_axil.sv]
foreach src $sources {add_files -norecurse [file join $root $src]}
add_files -norecurse [glob [file join $root hdl/core/rom/*.mem]]
update_compile_order -fileset sources_1
create_bd_design system
create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:* ps
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} [get_bd_cells ps]
set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 {1} CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] [get_bd_cells ps]
create_bd_cell -type module -reference flex_kernel_axil accelerator
set accel_if [get_bd_intf_pins -quiet accelerator/s_axi]
if {[llength $accel_if]!=1} {error "AXI-Lite inference failed for accelerator/s_axi"}
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config \
    {Master "/ps/M_AXI_HPM0_FPD" Clk_master "/ps/pl_clk0" Clk_slave "/ps/pl_clk0" Clk_xbar "/ps/pl_clk0" intc_ip "New AXI Interconnect"} $accel_if
assign_bd_address
set seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces ps/Data] -filter {NAME =~ *accelerator*}]
if {[llength $seg]!=1} {error "Cannot resolve accelerator address segment"}
set_property offset 0xA0000000 $seg
set_property range 4K $seg
validate_bd_design
save_bd_design
set bd [get_files system.bd]
generate_target all $bd
set wrapper [make_wrapper -files $bd -top]
add_files -norecurse $wrapper
set_property top system_wrapper [current_fileset]
update_compile_order -fileset sources_1
puts "FLEX_PROJECT_VALIDATED $out AXI_BASE=0xA0000000"
if {[lsearch -exact $argv build]>=0} {
    launch_runs impl_1 -to_step write_bitstream -jobs 4
    wait_on_run impl_1
    if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {error "Implementation did not finish"}
    open_run impl_1
    report_timing_summary -file [file join $out timing_impl.rpt]
    report_utilization -file [file join $out utilization_impl.rpt]
    write_hwdef -force -file [file join $out flex_zcu106.hdf]
}
