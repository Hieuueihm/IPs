# Accepted PS7/AXI/core 160 MHz baseline. Preserve existing accepted evidence.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
if {[file exists [file join $workspace study build a_cg_z020_system160 system_synth.dcp]]} {
    error "Accepted baseline checkpoint exists. Build in a separate workspace; see fpga/z020/README.md."
}
set argv [list synth]
source [file join $workspace experiments a_cg_z020_system160 create_project.tcl]
