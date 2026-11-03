# Diagnostic STA on the existing full synthesis checkpoint. No resynthesis,
# placement, routing, area pruning or production RTL edits.
# Static mode cases model an already configured kernel, not config transitions
# or a proof of whole-core/system timing closure.
set base [file normalize [file join [file dirname [info script]] ../..]]
set out [file join $base study build a_cg_batch profile_timing]
file mkdir $out
set_param general.maxThreads 4
open_checkpoint [file join $base study build a_cg_batch synth synthesized.dcp]
set allregs [all_registers]
set tile_regs [filter $allregs {NAME =~ "*u_tile/*"}]
if {[llength $tile_regs]<100} {error "Too few recognized tile registers"}
set cells [get_cells -hier -filter {REF_NAME == FDRE || REF_NAME == FDSE}]
set f [open [file join $out controls.txt] w]
set controls {}
foreach c $cells {
    set n [get_property NAME $c]
    set leaf [lindex [split $n /] end]
    # Synthesis already creates mode-register replicas. Use their recorded
    # original name so all copies receive the same case value. Fixing only
    # the unsuffixed register would leave replica-launched paths active.
    set original [get_property -quiet ORIG_CELL_NAME $c]
    if {$original ne ""} {set leaf [lindex [split $original /] end]}
    if {[regexp {^(dir|mf|native_r|native64|fft|inverse|packed16|fmt_r|fmt|md)_reg(\[([01])\])?$} $leaf -> kind suffix bit]} {
        set pin [get_pins -of_objects $c -filter {REF_PIN_NAME == Q}]
        if {[llength $pin]!=1} {error "Ambiguous config output: $c"}
        lappend controls [list $pin $kind $bit]
        puts $f "$pin $kind $bit"
    }
}
close $f
if {[llength $controls]<4} {error "Too few recognized mode control registers"}
set f [open [file join $out metrics.txt] w]
set paths [get_timing_paths -from $allregs -to $allregs -delay_type max -max_paths 1]
set tile_paths [get_timing_paths -from $tile_regs -to $tile_regs -delay_type max -max_paths 1]
puts $f "unconstrained_modes WNS_NS=[get_property SLACK $paths] TILE_WNS_NS=[get_property SLACK $tile_paths]"
report_timing -from $allregs -to $allregs -delay_type max -max_paths 10 -file [file join $out unconstrained_modes.rpt]
report_timing -from $tile_regs -to $tile_regs -delay_type max -max_paths 3 -file [file join $out unconstrained_modes_tile.rpt]
foreach profile {{ntt32_forward 0 0 0 0 0} {ntt16_forward 0 0 0 1 0} {fft128_forward 1 2 0 0 0} {fft128_inverse 1 2 1 0 0} {native64_inverse 1 1 1 0 1}} {
    lassign $profile label isfft fmt inverse packed native
    # Every recognized control pin is reassigned in every profile. Setting
    # its new case value replaces the previous one; no reset_case_analysis
    # command is available in the installed Vivado 2018.1.
    foreach control $controls {
        lassign $control pin kind bit
        switch $kind {
            dir - inverse {set value $inverse}
            mf - fft {set value $isfft}
            native_r - native64 {set value $native}
            packed16 {set value $packed}
            fmt_r - fmt {set value [expr {($fmt >> $bit)&1}]}
            md {set value [expr {(($isfft ? 1 : ($packed ? 2 : 0)) >> $bit)&1}]}
            default {error "Unexpected kind: $kind"}
        }
        set_case_analysis $value $pin
    }
    set paths [get_timing_paths -from $allregs -to $allregs -delay_type max -max_paths 1]
    set tile_paths [get_timing_paths -from $tile_regs -to $tile_regs -delay_type max -max_paths 1]
    puts $f "$label WNS_NS=[get_property SLACK $paths] TILE_WNS_NS=[get_property SLACK $tile_paths]"
    flush $f
    report_timing -from $allregs -to $allregs -delay_type max -max_paths 10 -file [file join $out ${label}.rpt]
    report_timing -from $tile_regs -to $tile_regs -delay_type max -max_paths 3 -file [file join $out ${label}_tile.rpt]
    puts "PROFILE_TIMING_DONE $label"
}
close $f
puts "PROFILE_TIMING_ALL_DONE"
exit
