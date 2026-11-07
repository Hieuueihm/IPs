# Full integrated baseline, never overwrite the accepted sign-off checkpoint.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
if {[file exists [file join $workspace study build a_cg_packed4_system160 route signoff.dcp]]} {
    error "Accepted baseline evidence exists. Implement in a separate workspace; see fpga/z020/README.md."
}
source [file join $workspace experiments a_cg_packed4_system160 implement.tcl]
