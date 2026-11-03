# Next timing study from the accepted registered-host baseline

Accepted baseline: `experiments/a_cg_host_baseline/rtl/`, pinned by its manifest
and `experiments/BASELINE.md`. This study changes neither that baseline nor
production HDL, PLAN or numerical specs. Packed16, runtime modulus, every FFT
precision and native NTRUGen64 are retained. No place/route is run.

| Variant | Change | Extra clocks vs accepted baseline |
|---|---|---|
| direction | Latch read/write direction on host acceptance; use it inside mapping instead of decoding live FSM state | None |
| fields | Replace additions of provably disjoint row/buffer/plane fields by OR | None |
| prepare | Includes direction latch; cache four lane bank/row/phase/OOB values in HPREP before RAM service | One per load line, one per read line |
| prepare_local | Same prepared host, plus the previously tested local configuration-flop attributes | Same as prepare |
| select | Includes direction latch; one shared bank hit decoder for reads/writes and parallel masked-OR word selection | None |
| prepare_split | Prepared host + separate exact FFT forward post-adder; GS/NTT keep shared unit with FFT raw bypass | Same as prepare |
| select_split | Parallel host word decode/selection + the same separated FFT post-adder, without HPREP | None |

All variants preserve kernel cycles. HPREP is explicitly excluded from the
compute `busy` range; host wait clocks are reported separately. Lane metadata
is captured only in HPREP and checked against the original mapping during
every service cycle in simulation. Direction is checked against read/write
state whenever the host services RAM.

For field OR, valid configuration constrains rows and planes to powers of two.
The within-plane row, plane index and ping-pong buffer occupy disjoint bits;
the far half offset is disjoint from k>>1. `check_geometry.py` enumerates every
accepted geometry, all fields and row offsets. Simulation also compares the
legacy addition addresses at each active RAM port. Arithmetic data, products,
rounding, carry state and roots are untouched.

The select experiment relies on the checked invariant that no two valid words
in one 128-bit host line target the same bank in one service phase. It does
not store wide one-hot bank tags: only a combinational four-word selection is
changed. The existing collision assertion stays active in simulation.

The split experiment adds a small 32-bit sum/difference unit, not a multiplier
or a precision-specific FFT engine. FFT forward uses it at the output; inverse
keeps its existing round/scale branch. Forward carry/borrow feedback comes from
the same new raw outputs. The input GS/NTT unit retains its role and FFT raw
bypass. Keeping the new unit's hierarchy prevents its operator from being
merged back across the intended stage boundary. No additional pipeline stage
or changed rounding/product order is introduced. Numerical outputs, rather
than unused FFT scratch-register contents during NTT mode, are the contract.

The cached lane registers need no reset contents: RAM host service only starts
after HPREP captures them. Valid/capture conditions remain reset and checked
in four-state simulation. No I/O request accesses RAM before it is captured.

## Reproduce

```powershell
python -X utf8 experiments/a_cg_host_opt/build.py
python -X utf8 experiments/a_cg_host_opt/check_geometry.py
./experiments/a_cg_host_opt/run_sim.ps1 -Variant direction -FourState
./experiments/a_cg_host_opt/run_sim.ps1 -Variant fields -FourState
./experiments/a_cg_host_opt/run_sim.ps1 -Variant prepare -FourState
./experiments/a_cg_host_opt/run_sim.ps1 -Variant prepare_local
```

For each variant, run its generated application bridge, for example:

```powershell
python -X utf8 experiments/a_cg_host_opt/application_prepare.py
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_host_opt/synth.tcl -log study/build/a_cg_host_opt/prepare/vivado.log -journal study/build/a_cg_host_opt/prepare/vivado.jou -tclargs prepare
```

The full numerical fixture remains the frozen 1026 cases from
`study/build/a_cg_batch/fixtures.bin`. Four-state uses the frozen 38-case
subset. All four application bridges use the same live C inputs; the new RTL
provides replacement outputs. Only FFT/IFFT/NTT/INTT are substituted in C.
The two prepared cores are byte-identical; their tile differences are only
configuration preservation attributes/declaration splitting, not behavior.

The XDC and synthesis settings are identical to the accepted baseline:
xczu7ev-ffvc1156-2-e, Vivado 2018.1, clock 5 ns read before synthesis,
synchronous boundary delays max/min 1/0 ns and setup/hold uncertainty
0.100/0.050 ns. No false paths, multicycle exceptions, fixed mode constraints,
placement or routing. Synthesis wire delay is an estimate; do not infer
measured Fmax or physical timing closure from slack.
