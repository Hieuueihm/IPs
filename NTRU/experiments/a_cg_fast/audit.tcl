set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_fast synth]
open_checkpoint [file join $out synthesized.dcp]
set f [open [file join $out audit.txt] w]
set nr 0
set nd 0
foreach c [get_cells -hier -filter {REF_NAME == RAMB18E2}] {
    puts $f "RAMB18 $c"
    if {[string match *root_mem* $c]} { incr nr }
    if {[string match *data_bank* $c]} { incr nd }
}
puts $f "ROOT_RAMB18=$nr"
puts $f "DATA_RAMB18=$nd"
puts $f "DSP48=[llength [get_cells -hier -filter {REF_NAME == DSP48E2}]]"
puts $f "BLACKBOX=[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]]"
foreach name {load_valid load_ready read_valid read_ready read_rsp_valid root_we root_commit cfg_valid desc_we} {
    set port [get_ports $name]
    set nets [get_nets -of_objects $port]
    set pins [get_pins -leaf -of_objects $nets]
    puts $f "PORT $name connected_leaf_pins=[llength $pins]"
}
close $f
if {$nr!=16 || $nd!=32} {error "Expected 16 root RAM and 32 data RAM in synthesized checkpoint"}
puts "A_CG_AUDIT_DONE"
exit
