# XC7Z020-CLG400-2 synthesis check

Exact RTL copy of the PQC-verified a_cg_cmd_dispatch2 prototype. Re-infers
7-series DSP48E1, RAMB18E1 and carry primitives, at the same 5 ns constraint.
Reports full core including host adapter and root cache. No P&R, board pin
constraints, PS/AXI integration, bitstream or hardware run is implied.
Existing PQC evidence applies to the identical RTL; this is not post-map testing.
The selected baseline, production RTL, precision, modulus and packed16 modes
remain unchanged. This experiment does not implement the separate 30k LUT goal.
