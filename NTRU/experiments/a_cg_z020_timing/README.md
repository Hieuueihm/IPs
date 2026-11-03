# XC7Z020 timing batch (no latency or contract change)

Child of `a_cg_z020_dispatch2` (same RTL as the PQC-verified `a_cg_cmd_dispatch2`). Analysis:
[docs/ra_soat_rtl_z020.md](../../docs/ra_soat_rtl_z020.md). Production `hdl/`, PLAN and spec unchanged; nothing committed.

## Changes (each with a simulation-only shadow of the previous logic that stops the simulation on any difference)

| Group | Change |
|---|---|
| Tile input stage | NTRUGen `A + 1` made before the input register (`g_in_reg`); add/sub computes `a + b - q` and `a - b + q` in parallel with `a + b`, `a - b` (carry-save stage + one chain), packed lanes cut by a guard bit at 16 |
| FFT product program | core runs the program one clock early from registers; each tile registers it; limb-memory addresses registered one clock ahead |
| Bank / root addresses | plane row bases from two registered tables; `k`-dependent offsets (`kfar0/1`, `near_swap`, root base + k term) are registers updated with `k` |
| Host map | configuration-derived values registered; line-derived values made at capture |
| Control | `read_gap - 1` kept in a register |

## Results

Functional (`run_sim.ps1`, then `compare.py`): 1,026 cases, kernel and host cycles identical to `a_cg_cmd_dispatch2`
case by case; reset abort 12 modes; 38 four-state; pipeline reset; 74 live C calls, 14 identical artifacts, 4 signatures.
Shadow checks verified live: four injected faults (far offset, root base, limb-memory offset, host bank shift) each stopped
the four-state run.

Synthesis, XC7Z020-CLG400-2, 5 ns (`synth.tcl`):

| | Before (`a_cg_z020_dispatch2`) | After |
|---|---:|---:|
| LUT | 37,841 | 39,816 (+1,975) |
| FF | 27,397 | 28,084 |
| LUTRAM | 3,236 | 3,281 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | −3.604 ns | −2.248 ns |
| Negative endpoints (one path each) | 6,828 | 4,363 |

Remaining groups: bank read address from `stage_idx` (−2.25, `stage_idx == stages - 1` compare in front of the row add),
plane table → bank address (−1.30), `fmt` → `rd_plane` → bank address (−1.84), tile add/sub (−1.12, one 35-bit chain plus
3 LUT levels before and 3 after), host map from `logn` (−0.69), stage switch (−0.58), `state` → `cfg_ready` port (−0.46,
not touched: it is an interface change). The FFT program group is closed.
