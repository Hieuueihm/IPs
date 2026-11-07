# Read accepted checkpoints; write all new evidence into this private study.
set root [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $root study build paper_ablation31 decomposition]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $root study build a_cg_packed4_system160 route signoff.dcp]
report_utilization -hierarchical -hierarchical_depth 12 -file [file join $out routed_hierarchy.rpt]
set f [open [file join $out primitive_samples.tsv] w]
puts $f "name\tref\ttype"
foreach c [get_cells -hier -filter {IS_PRIMITIVE == 1}] {
    puts $f "[get_property NAME $c]\t[get_property REF_NAME $c]\t[get_property PRIMITIVE_TYPE $c]"
}
close $f
puts "DECOMPOSITION_DONE"
exit
