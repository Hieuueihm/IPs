# vivado -mode batch -source fpga/zcu106/tile_thu_glue.tcl -tclargs <TREN_MANG>
# Groups the LUTs that sit directly in tile_thu (outside bf0..bf3, leaves, delays) by the
# register or net they are named after. Synthesis only, hierarchy kept; the grouping is an
# approximation because Vivado names a LUT after one of the nets it drives.
set variant [lindex $argv 0]
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set out [file join $root study/build/tile_breakdown/glue_$variant.txt]
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog hdl/mul_ss.v
read_verilog -sv hdl/tile_thu/tile_thu.sv
synth_design -top tile_thu_top -part xczu7ev-ffvc1156-2-e -mode out_of_context -flatten_hierarchy none -generic TREN_MANG=$variant
set cnt [dict create]
foreach c [get_cells -hier -filter {REF_NAME =~ LUT*}] {
    set n [get_property NAME $c]
    if {![regexp {^u_tile/([^/]+)$} $n -> n]} continue
    regsub {\[.*$} $n {} n
    regsub {_i_[0-9]+.*$} $n {} n
    regsub {_reg.*$} $n {} n
    dict incr cnt $n
}
set fh [open $out w]
dict for {k v} $cnt { puts $fh "$v $k" }
close $fh
puts "GLUE_DONE $variant"
