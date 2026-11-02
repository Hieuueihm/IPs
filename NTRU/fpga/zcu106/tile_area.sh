#!/bin/sh
# Synthesis-only area of one tile: sh fpga/zcu106/tile_area.sh <tag> <tile rtl file> [period ns, default 5.0]
# Prints LUT / FF / LUTRAM / DSP and the post-synthesis WNS; reports in study/build/tile_area/<tag>/.
cd "$(dirname "$0")/../.."
mkdir -p study/build/tile_area
/c/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log study/build/tile_area/$1.log -source fpga/zcu106/tile_area.tcl -tclargs $1 $2 ${3:-5.000} > /dev/null 2>&1
d=study/build/tile_area/$1
echo "$1: LUT $(grep -m1 'CLB LUTs' $d/util.rpt | awk -F'|' '{print $3}') FF $(grep -m1 'CLB Registers' $d/util.rpt | awk -F'|' '{print $3}') LUTRAM $(grep -m1 'LUT as Memory' $d/util.rpt | awk -F'|' '{print $3}') DSP $(grep -m1 'DSPs' $d/util.rpt | awk -F'|' '{print $3}') WNS $(grep -m1 'Slack' $d/timing.rpt | awk '{print $4}')"
