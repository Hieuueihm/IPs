# XC7Z020: tile latency + 1 (approved 03/11/2026)

Child of `a_cg_z020_timing` (all its changes, plus the bank-address changes: stage flags `read_near`, `internal_read`,
`write_far`, `more_stages` and the next descriptor are registers set with the stage index; `rd_plane` is a register
updated with the counters; read rows come from `row_tab[half][plane]`, plane base plus the stage's k offset, updated with
k). Production `hdl/`, PLAN and spec unchanged; nothing committed.

## Change

- Tile add/sub in two clocks (sums registered, corrections from the registers); the carry-save parallel version is gone.
- One more request register before the operand stage, in every mode; the add/sub's first clock, the limb counters and
  the limb carries still use the undelayed request.
- NTT CT output one more clock (it leaves the add/sub's second clock).
- Latency vs `a_cg_cmd_dispatch2`: NTT inverse (GS) +1, NTT forward (CT) +2, FFT +1 (both directions, native included).
- Core: FFT product program one clock later (`program_d` + 1). Schedule: `planner.py` here (write completion + 1, + 1 more
  for NTT forward); fixtures and application inputs rebuilt from it (`build_fixtures.py`, `application.py`).

## Results

Functional (`run_sim.ps1`, `compare.py`): 1,026 cases exact, RTL kernel cycles equal to the new planner in every case;
reset abort 12 modes; 38 four-state; pipeline reset; 74 live C calls, 14 identical artifacts, 4 signatures. Kernel cycles
vs `a_cg_cmd_dispatch2`: total +1.24 %, at most +26 cycles in a case. The add/sub shadow (previous combinational add/sub,
registered one clock) runs in every simulation.

Synthesis, XC7Z020-CLG400-2, 5 ns:

| | `a_cg_z020_dispatch2` | `a_cg_z020_timing` | this |
|---|---:|---:|---:|
| LUT | 37,841 | 39,816 | 40,790 |
| FF | 27,397 | 28,084 | 31,491 |
| LUTRAM | 3,236 | 3,281 | 3,281 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | −3.604 ns | −2.248 ns | **−1.018 ns** |
| Negative endpoints | 6,828 | 4,363 | 1,785 |
| 16 tiles / core logic (LUT) | 31,780 / 6,039 | 33,399 / 6,395 | 33,395 / 7,373 |

Every tile path now meets 5 ns (worst tile path +0.056 ns). Remaining, all in the core: plane table → bank write row
(−1.02), `logm` → bank write data select (−0.72, 1,517 endpoints), stage index / beat → `row_tab` update (−0.74 / −0.60),
`fmt` → host map row (−0.44), `state` → `cfg_ready` port (−0.48, interface, not touched).

LUT went the wrong way for the 30k goal: +2,949 over `a_cg_z020_dispatch2`. Attributed per RTL signal (netlist cell
names, tile 1 and core; see docs/ra_soat_rtl_z020.md section 6): each tile +91 (two-clock add/sub with guard bits, moved
NTRUGen increment), the core +1,507 (`row_tab` 646, the read-row mux repeated in all 32 banks +784, `desc_nx` and
`read_gap_m1` ~250). The `d_mcw` hierarchy growth seen in the per-module report is the FFT accumulator moved into that
module by Vivado, not new logic.
