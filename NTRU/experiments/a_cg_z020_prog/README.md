# XC7Z020: FFT product program decoded once in the core (direction 4) — no gain, not kept

Child of `a_cg_z020_share`. Direction 4 of `docs/dung_chung_fft_ntt.md` section 11, approved 03/11/2026. Production
`hdl/`, PLAN and spec unchanged; nothing committed.

## Change

The core decodes each product step once (`wtab`) and sends the decoded program to the 16 tiles. The tile FFT program
ports change from `ext_fft_mst` (step, 4 bit) to these:
- limb indices of the A / B limb memories (with the p1 offset) and of the sum memories;
- top-limb signs and column flags;
- first and last step.

The core's program counters run one clock earlier and a decode register follows them, so the tiles see the program at
the same clock as before. Each tile drops its two step decoders, the p1 offset add and the sign and last-step compares.

## Results

Functional: 1,026 cases exact, kernel cycles equal to the planner and to `a_cg_z020_share` (559,565); 38 four-state;
pipeline reset; live C replay identical.

XC7Z020-CLG400-2, 5 ns:

| | `a_cg_z020_share` | this batch |
|---|---:|---:|
| LUT, synthesis | 31,476 | 31,535 (+59) |
| One tile, synthesis | 1,266 | 1,274 .. 1,276 |
| Core-level logic, synthesis | 7,595 | 7,471 (the delay lines are 10 entries instead of 13) |
| LUT after place and route | 31,122 | 31,201 (+79) |
| FF after place and route | 29,964 | 30,201 |
| WNS after place and route | −0.686 ns | −0.814 ns |

The tile does not get smaller. Before this change, synthesis had already folded each step decoder (4-bit step and
format) into the LUTs that form the limb memory addresses, so it cost almost nothing. The pre-decoded program adds input
bits (21 instead of 7) to those LUTs. **Direction 4 is dropped; `a_cg_z020_share` stays the reference.**
