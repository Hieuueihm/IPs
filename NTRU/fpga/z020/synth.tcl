# Selected target: Qiming board, XC7Z020-CLG400-2. Synthesis only.
# Uses the private verified prototype snapshot; does not replace production RTL.
set workspace [file normalize [file join [file dirname [info script]] ../..]]
source [file join $workspace experiments a_cg_z020_dispatch2 synth.tcl]
