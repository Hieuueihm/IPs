# XC7Z020: div2e at the host read, registered interface, then one place and route

Child of `a_cg_z020_addr` (tile latency +1, bank rows as bit fields). Production `hdl/`, PLAN and spec unchanged.

This is the retained version on XC7Z020: routed, register-to-register hold met, about 180 MHz (200 MHz is not required on
this part; `a_cg_z020_200` was stopped).

## Code cleanup

The RTL was cleaned without changing the hardware:
- The simulation-only shadows that compared each timing change with the logic it replaced were removed, together with
  the code only they used (the previous add/sub module, the previous FFT program, the single-clock host map, the
  previous row, root and select expressions).
- Unused signals were removed (registers that synthesis already dropped, aliases, an unused wire).
- Comments describe what the code does, without dates or experiment names.
- The protocol and invariant checks, the frozen configuration decode check and the host-side div2e reference stay.
- Tile ports and parameters are unchanged; `cfg_shift` is now unused (the core scales at the host read).

The checks were rerun: the functional regression and `compare.py` pass, and synthesis gives the same `util.rpt` and
`util_hier.rpt` line for line, with WNS +0.038 ns and WHS +0.126 ns. The place-and-route numbers below therefore still
apply.

The FFT program delay lines keep 13 entries. Shortening them to the 11 the taps use was tried and changes the netlist:
−63 LUT and −72 FF (the two entries that are never selected, a different split into shift registers, and different
register replication), with synthesis WNS −0.122 ns. That needs a new place and route, so it is not part of the cleanup.

## Changes

| Change | Behavior |
|---|---|
| div2e of the last inverse FFT layer removed from the 16 tiles; applied to every line read after a non-NTRUGen inverse FFT (rounding increment, then per-value arithmetic shift; scale pending until the next configuration, start or load) | Results bit-exact. Host read response +2 clocks. Contract: read an inverse FFT's results before loading new data or starting another command on them |
| `cfg_ready`, `load_ready`, `read_ready`, `busy` from registers loaded with the next-clock value (next state) | Same as before, clock for clock |
| Per-command constants registered (`period - 1`, `planes - 1`, `row_jobs - 1`, `stages - 1`, `last_k`, wanted descriptors, host submask); `beat_last`, `beat_rd` kept with `beat` | Same |
| Host: one-hot word select per bank registered from the next clock's values; line base bank and plane made at capture; host basis registered for both directions; out-of-data words masked at use | Same |

## Results

Functional (`run_sim.ps1`, `compare.py`): 1,026 cases exact, kernel cycles equal to the planner; 38 four-state; pipeline
reset; 74 live C calls, 14 identical artifacts, 4 signatures.

XC7Z020-CLG400-2, 5 ns:

| | Synthesis | **After place and route** (Explore directives) |
|---|---:|---:|
| LUT | 36,110 | **35,777** |
| FF | 31,883 | 31,946 |
| LUTRAM | 3,281 | 2,968 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | +0.038 ns | **−0.567 ns** (≈ 180 MHz) |
| Failing endpoints | 0 | 973 (TNS −105.8 ns) |
| Register-to-register WHS | +0.126 ns | +0.050 ns |

Fully routed, no routing errors. The −1.272 ns hold in the summary is on the OOC interface ports (1 / 0 ns I/O delays), not
register to register.

Post-route failing groups:
- **Block RAM read data without an output register** (clock-to-out ≈ 2.1 ns on 7-series plus long routes):
  - bank → host line capture through the 32 → 1 select: −0.57 ns, 128 endpoints;
  - bank → `req_x` / `req_y`: −0.38 / −0.33 ns;
  - `rvalid` → `req_x` / `req_y` clock enable, fanout 1,024: −0.25 ns.
- Tile: Montgomery `u - q` and select (−0.33, 13 levels); second clock of the add/sub through the output select to
  `rd` (−0.27); FFT T stage (−0.29); tile result tag → bank write row and enable (−0.32).
