# Area of the add/sub forms in study/results/addsub_variants/addsub_variants.sv (synthesis only, out of context). Arg: top module.
set top [lindex $argv 0]
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog -sv [file join [file dirname [info script]] addsub_variants.sv]
synth_design -top $top -part xczu7ev-ffvc1156-2-e -mode out_of_context
puts "AREA $top [llength [get_cells -hier -filter {REF_NAME =~ LUT*}]] LUT [llength [get_cells -hier -filter {REF_NAME =~ CARRY*}]] CARRY8 [llength [get_cells -hier -filter {REF_NAME =~ FD*}]] FF"
