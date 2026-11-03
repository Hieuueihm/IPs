# Control-path timing prototype

Parent: immutable `a_cg_prepare_split_baseline` (the 37,917-LUT synthesis candidate).
This separate prototype leaves that source and production HDL unchanged.

## Changes

* Each engine has a preserved local synchronous reset register. The request is
  predicted from an idle start, so its high pulse remains in RESET_TILE. Kernel
  latency is unchanged. Global reset invalidates the core immediately; the local
  datapath reset is completed on the following edge before any configuration or
  new work can reach it. A single-edge reset can abort a running transform.
  The tile configuration strobe is likewise registered locally, predicted from
  RESET_TILE so it keeps exactly the original CONFIG_TILE phase. Neither pulse
  requires a new compute state or changes a butterfly clock.
* A configuration request is captured when `cfg_valid && cfg_ready`. Geometry and
  validity are derived from captured fields in five setup clocks. `cfg_ready`
  stays low until this completes; the host must wait for it before root/descriptor
  loading or another command. External configuration pins may change immediately
  after acceptance. Each transform pays five additional setup clocks; load/read
  line service and kernel schedules do not change.
* The existing per-engine input sign-control register is preserved to prevent
  merging between engines. It adds no pipeline latency. Other tile arithmetic,
  products, reducers, rounding and precision contracts are byte-identical to the
  parent, apart from this control-flop attribute.

Packed16, NTT32/modulus selection, FFT32/64/128 and native NTRUGen64 remain runtime
features. The root cache and host adapter are included in synthesis and routing.

## Checks and implementation

`run_sim.ps1` runs the frozen 1,026 numeric cases, a single-edge reset/restart in
12 mode groups, poisoned config pins after acceptance, 38 four-state cases and
the live C application replay. Simulation checks the staged geometry against
the frozen combinational decoder. `validate.py` requires all these checks and
unchanged kernel cycles before P&R.

`synth.tcl` retains the same 5 ns clock, 0.100/0.050 ns uncertainty and 1/0 ns
max/min I/O delays. The physical run uses the previous placement/routing strategy
for comparison. No false paths, multicycle constraints, static mode constraints,
board pin placement or bitstream are introduced. Register-to-register timing and
boundary timing must be distinguished: the OOC ports have no partition pin locations.
