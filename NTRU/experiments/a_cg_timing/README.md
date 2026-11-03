# Synthesis-only timing experiments, packed16 retained

Frozen input: `experiments/a_cg_batch/rtl/`. This fork never modifies production
HDL, PLAN, the spec or that prior experiment. Every variant retains runtime
NTT32, packed16 NTT (q <32768), FFT32/64/128 and native NTRUGen64, all 16 engines,
host, root/descriptor storage and the same numerical contracts.

| Variant | Change |
|---|---|
| base | Byte-identical frozen RTL, synthesized again under the common constraints |
| host | Capture host request/data first; bank phase 0 starts next cycle |
| local | DONT_TOUCH only per-tile configuration flops: mode, direction, format, shift, native and halving |
| raw | FFT takes the existing raw sum/difference before NTT q correction |
| all | The three changes together |

The host change adds one cycle per accepted load line and one cycle per read
line. RAM geometry, kernel issue schedule, carry state, root tables and kernel
pipeline latency are unchanged. Validate that explicitly against all frozen
cases; do not hide the cold-transaction cost behind kernel-only numbers.

The local change preserves configuration flops per tile. It neither locks
placement nor marks arithmetic, RAM or DSP cells DONT_TOUCH. It is a synthesis
experiment on load distribution; it does not prove shorter physical wires.

For the raw change, `plain=mf` is true only for FFT and split=0. The same sum
chain and borrow chain supply the raw outputs and unchanged co/bo. With q=0,
the previous modular correction is algebraically an identity modulo 2^32;
the new FFT output bypasses that correction. NTT retains the old equations.
The q input no longer needs an FFT zero mask. No product, rounding, wrap,
coefficient precision or Montgomery convention is changed.

## Reproduce

One complete validation + synthesis-only run:

```powershell
./experiments/a_cg_timing/run.ps1 -Synthesize
```

Or run the individual steps:

```powershell
python -X utf8 experiments/a_cg_timing/build.py
python -X utf8 experiments/a_cg_timing/check_addsub.py
./experiments/a_cg_timing/run_sim.ps1 -Variant host -FourState
./experiments/a_cg_timing/run_sim.ps1 -Variant local
./experiments/a_cg_timing/run_sim.ps1 -Variant raw
./experiments/a_cg_timing/run_sim.ps1 -Variant all -FourState
python -X utf8 experiments/a_cg_timing/application.py
python -X utf8 experiments/a_cg_timing/application_host.py
```

For each of `base host local raw all`, run (replace `base` consistently):

```powershell
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_timing/synth.tcl -log study/build/a_cg_timing/base/vivado.log -journal study/build/a_cg_timing/base/vivado.jou -tclargs base
python -X utf8 experiments/a_cg_timing/report.py
```

Run the collector after all five syntheses and validation complete. Build
sources are generated from pinned hashes. The input fixtures are reused
without regenerating golden values; the combined application replay reuses
the same live C inputs, while actual new RTL outputs supply the replacements.

## Timing scope

There is **no place_design, route_design or board project in this flow**.
All variants read the same XDC before synth_design: 5 ns clock, synchronous
I/O max/min 1/0 ns, setup/hold uncertainty requested as 0.100/0.050 ns.
Vivado 2018.1 may classify uncertainty as implementation-only; the actual
post-synthesis timing report is authoritative for what the estimator used.
Clock constraints themselves must appear before timing-driven synthesis.

The comparison baseline is the new `base` synthesis, not the old 36,231-LUT
flow that added its clock after synthesis. Primary STA has no case analysis,
false paths or multicycle exceptions. Report both full-boundary and internal
register-to-register timing, path levels and estimated net delays. A better
synthesis slack is an estimate, not a measured Fmax or proof of routed timing.

Packed16 root conversion R32→R16, hmin contracts and batch capacity rules are
unchanged from the previous fork. Application replay replaces only four
transform kernels; other application code remains C. No physical hardware
correctness at an unclosed clock is inferred from passing RTL vectors.
