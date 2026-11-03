# Selected 37,917-LUT candidate: one fast implementation

`adopt.py` pins the exact `prepare_split` source, synthesis checkpoint and
correctness evidence. The immutable source copy is in
`experiments/a_cg_prepare_split_baseline/rtl/`. Production HDL is unchanged.

`implement.tcl` opens the existing checkpoint; it does not resynthesize.
It uses AltSpreadLogic_high placement, default physical optimization and
RuntimeOptimized routing. The existing 5 ns constraints remain in force.
This is an OOC core run including host and roots, with no board pins or bitstream.

After successful routing, `report.py` validates the frozen evidence and writes
`study/results/a_cg_prepare_route.{md,json}`. It separates internal register timing
from the assumed I/O boundary timing. Review `route_status.rpt` and `drc.rpt` as
well as slack. A completed run does not automatically mark the baseline approved.
