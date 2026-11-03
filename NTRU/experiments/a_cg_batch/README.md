# Isolated packed16 NTT + independent-job batching prototype

This fork extends `experiments/a_cg_tune`. Production HDL, spec, PLAN and previous
measured forks are untouched. It preserves all FFT arithmetic contracts and
the 16 engines / 64 DSP / 32 data RAMB18 + 16 root RAMB18 organization.

Measured results: `study/results/a_cg_batch.md` and `.json`. Do not infer LUT
from the architectural description: packed support adds logic even though
DSP/BRAM count is unchanged. Reports cover the complete transaction host,
root/descriptor storage, data banks, routing and engines, without AXI/DMA.

## Packed16 NTT

Set `cfg_packed=1` only for NTT/INTT and odd `3 <= q < 32768`. Input/output
memory words contain two **canonical** coefficients, low index in low 16 bits.
The existing 32-bit multiplier array runs two separate 16-bit modular products;
carry and borrow boundaries, reduction and inverse halving are split per lane.
This is exact arithmetic modulo q, not truncated scalar arithmetic.

The external config still supplies scalar q and `-q^-1 mod 2^32`. Engines
replicate q's low half and use qinv's low half for Montgomery R16. Root words
contain two R16 roots. `build.pack` converts mathematical R32 tables by
`w16 = w32 * (2^16)^-1 mod q`; truncating an R32 root is incorrect.

For hmin >= 1, pack two parity planes and halve the plane count. For full NTT
(hmin=0), run word-level CG layers and one within-word butterfly layer. Forward
places that layer last; inverse places it first. The within-word layer uses
two distinct roots per packet and near-to-near routing. N=2 reserves a dummy
bank for the unused second word and forces its input to zero.

## Independent jobs in one command

`cfg_jobs_log=0..4` selects 1,2,4,8,16 jobs. All jobs share transform type,
precision, N, hmin, q, direction, arithmetic contract and root tables. Inputs
and outputs are job-major. This does not provide concurrent mixed moduli or
mixed FFT/NTT contexts, nor does it make a dependent job available early.

Small transforms use idle bank bits for job identity. Jobs beyond those bank
bits use additional row planes in the existing ping-pong buffers. A single
shared schedule and root cache serve all jobs. No per-job controller is added.

Let m be the log2 word-CG length and b be the base plane log:

| Mode | m | b |
|---|---|---|
| FFT | max(logn-1,0) | fmt+1 |
| Scalar NTT | logn-hmin | hmin |
| Packed NTT, hmin=0 | logn-1 | 0 |
| Packed NTT, hmin>=1 | logn-hmin | hmin-1 |

Bank job log is `min(jobs_log,max(0,5-m))`; remaining job bits use row planes.
Require total plane log <=3 and `max(m-5,0)+plane_log <=7`. This admits at most
4096 host words per command with the current address widths. `planner.config`
and RTL reject capacity overflow; jobs_log=4 is not universally admissible.
Unsupported packed FFT and q>=32768 are also rejected.

## Scheduling and verification

`planner.py` reserves every physical bank read/write and models dependencies,
pipeline latency, root use and output order. It numerically replays the
chronological RAM events. FFT retains 3/12/45 product cycles per butterfly.
Packed NTT accepts two coefficient butterflies per packet every three clocks.
Batch jobs increase occupancy; they do not increase arithmetic capacity.

`extra_cases.py` adds independent jobs with different inputs. New NTT expected
values come from direct polynomial evaluation by Horner, separately from the
CG scheduling model. Forward and inverse results are checked against external
logical arrays, not merely an unchecked RTL roundtrip. The first 454 original
cases preserve input/root/expected payload. Four-state cases exercise packed
word layers, within-word layers, bank jobs, row jobs, FFT and native64.

`application.py` runs captured live C transform inputs through RTL and replays
actual RTL outputs into the C application. NTT/INTT use packed16; FFT/IFFT keep
FFT128. Other kernels remain C. It checks artifact identity, independent
signature verification and rejection of altered live input. Batch correctness
is checked by independent transform vectors, not this single-job application
replay. These checks are not a formal proof or a certification of PQC security.

## Reproduce

From the repository root, with the same installed tools as earlier forks:

```powershell
./experiments/a_cg_batch/run.ps1 -Synthesize
python -X utf8 experiments/a_cg_batch/application.py
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/audit.tcl -log study/build/a_cg_batch/audit.log -journal study/build/a_cg_batch/audit.jou
./experiments/a_cg_batch/run_batch_only.ps1 -Synthesize
python -X utf8 experiments/a_cg_batch/report.py
```

`build.py` regenerates the private tile from pinned production source and
checks production hashes. `rtl/a_cg_fast.sv` is the private core source.
Fixture header version is `0x43474233`; thirteen u32 fields are FFT, fmt,
logn, hmin, inverse, q, qinv, native, packed, jobs_log, stage_count,
root_words_per_lane, host_word_count. Each stage has mask/base/period/gap.
Root payload is lane-major; input and expected payloads follow.

Vivado OOC synthesis targets xczu7ev-ffvc1156-2-e. The 5 ns clock is applied
after synthesis to match the historical reporting convention. There is no
place/route in that synthesis study, measured Fmax or complete algorithm speedup claim. Cold host
cycles and kernel-only cycles are reported separately. Saved `attempt1`
build reports preserve the initial implementation for area comparison.

`synth_batch_only.tcl` synthesizes a static ablation generated as
`rtl/batch_only.sv`: the same core with packed mode tied off, retaining batch
and FFT32/64/128. That file replaces `a_cg_fast.sv` in the compile list;
both declare the same module and must not be compiled together. Its packed
configuration port is absent. It cannot deliver the packed16 speedups.
`study/build/a_cg_batch/attempt2` archives a losing scalar-q replication
experiment (36,499 LUT); it is not the retained implementation.

## Core place and route

The initial physical implementation runs were stopped at the user's request
to use synthesis estimates only. Neither run produced a completed post-route
result. Partial routing logs are diagnostic data, not final timing/resource
measurements. `study/build/a_cg_batch/implementation_status.json` records this
status. The completed results remain `study/results/a_cg_batch.md` / `.json`.

`route.tcl` implements the frozen full or batch-only synthesis checkpoint,
without regenerating RTL or modifying the historical synthesis results:

```powershell
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/route.tcl -log study/build/a_cg_batch/route_packed.log -journal study/build/a_cg_batch/route_packed.jou -tclargs packed 5.000
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/route_audit.tcl -log study/build/a_cg_batch/route_packed_audit.log -journal study/build/a_cg_batch/route_packed_audit.jou -tclargs packed
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/route.tcl -log study/build/a_cg_batch/route_batch_only.log -journal study/build/a_cg_batch/route_batch_only.jou -tclargs batch_only 5.000
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/route_audit.tcl -log study/build/a_cg_batch/route_batch_only_audit.log -journal study/build/a_cg_batch/route_batch_only_audit.jou -tclargs batch_only
python -X utf8 experiments/a_cg_batch/route_report.py
```

Logs/journal options must precede `-tclargs`. The collector reads those logs,
falling back to stdout logs named `route_packed_console.log` and
`route_batch_only_console.log` in the build directory.

Both implementations use a 5 ns clock, max/min synchronous I/O delays of
1/0 ns and setup/hold uncertainty 0.100/0.050 ns. No false paths hide config,
host or reset timing. `HD.CLK_SRC` names a repeatable real BUFGCE site on the
part (recorded in `run_config.txt`); it is a reference for OOC clock timing,
not a board pin or an inserted top-level clocking subsystem. This is core
implementation, without board I/O, a board project or a bitstream. Reports
are separate in `study/results/a_cg_batch_route.md` / `.json`. Vectorless
power estimation is not measured power.

Virtual OOC ports do not have assigned `HD.PARTPIN_LOCS`. Vivado warns that
their boundary routing and I/O timing are incomplete. The audit therefore
also reports register-to-register setup/hold, and the collector keeps both
that internal result and the full-design timing table. A positive internal
result does not establish board I/O timing closure.
