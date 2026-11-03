# Metadata repair only: the previous query counted FDRE but not other legal
# synchronous FF mappings. Open the existing checkpoint; never resynthesize.
set base [file normalize [file join [file dirname [info script]] ../..]]
set dir [file join $base study build a_cg_cmd_pipe synth]
open_checkpoint [file join $dir synthesized.dcp]
set cells [get_cells -hier -filter {NAME =~ *reset_local_reg}]
if {[llength $cells] != 16} {error "Expected sixteen preserved local reset registers"}
set f [open [file join $dir reset_register_types.txt] w]
foreach c $cells {
    set ref [get_property REF_NAME $c]
    if {![string match FD* $ref]} {error "Reset object is not a flip-flop: $c $ref"}
    puts $f "$c $ref"
}
close $f
file copy -force [file join $dir metrics.txt] [file join $dir metrics_fdre_query.txt]
set f [open [file join $dir metrics.txt] r]
set metrics [read $f]
close $f
if {![regsub {LOCAL_RESETS=[0-9]+} $metrics "LOCAL_RESETS=[llength $cells]" metrics]} {error "Missing metric"}
set f [open [file join $dir metrics.txt] w]
puts -nonewline $f $metrics
close $f
puts "RESET_REGISTER_QUERY_VERIFIED"
exit
