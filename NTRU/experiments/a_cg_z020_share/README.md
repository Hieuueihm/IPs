# XC7Z020: FFT and NTT share more of the tile (output path, adders, operand selects)

Child of `a_cg_z020_hostdiv` (commit 1f3faab). Production `hdl/`, PLAN and spec unchanged; nothing committed. The three
changes come from `docs/dung_chung_fft_ntt.md` section 11 (directions 1, 2, 3, approved 03/11/2026). Changes that keep the
timing have a simulation-only shadow of the previous logic; a fault injected in each shadowed change was caught.

## Changes

| Change | Behavior |
|---|---|
| **FFT results leave through the NTT output path.** Forward: A + T, A − T come from the shared add/sub one clock after the T limb, like NTT CT. Inverse: A + B and T leave in the clock of the T limb, like NTT GS. The forward FFT's own wrap add/sub (`fft_ct_addsub`), the four limb registers and two tag registers that held each limb one limb longer (needed only by the in-tile div2e), and the output mode select are removed. GS halving is off in the FFT mode inside the tile | **Tile contract: FFT latency shorter.** Per result, by the gap to the next T limb of the same row (last limb: 1), plus 1 for the inverse; FFT 32 forward unchanged. Planner `FFT_OUT_EARLY`. Results bit-exact |
| **Three pairs of adders fused** (one NTT-only, one FFT-only; a mode uses one of them; the operand select fits in the chain's LUTs): u − q with p0 + p1 (T stage); a + b − q with o.re + o.im; a − b + q with wr + wi (the add/sub's second-clock correction chains, new ports `fa/fb/fci/fs`, `wa/wb/wci/ws`) | Same values, same timing |
| **Multiplier operands picked by registered 2-bit selects** (A: limb memory, limb sum memory, T_lo / m, a1; B: root memory, root sum memory, q′, q). The NTT T-pass root is written into the root memory (entry 0) at the edge that loads `w1`; the FFT root memory is written at that edge too (one clock earlier than before). Packed NTT zeroes the A operand of leaves 2 and 3 through the leaf register (`zh`) instead of a select | Same values, same timing |

## Results

Functional (`run_sim.ps1`, `compare.py`): 1,026 cases exact, kernel cycles equal to the planner; 38 four-state; pipeline
reset; 74 live C calls, 14 identical artifacts, 4 signatures. Fault injection (four-state run): a fault in each of the
fused correction chain, the fused u − q chain, the operand select and the FFT sums stopped the run at its shadow.

Kernel cycles, sum over the 1,026 cases: 560,625 → 559,565 (−0.19 %). NTT unchanged; FFT 32 forward unchanged; FFT 32
inverse −0.9 %, FFT 64 −0.8 % / −1.6 %, FFT 128 −0.14 % / −0.32 % (forward / inverse).

XC7Z020-CLG400-2, 5 ns:

| | `a_cg_z020_hostdiv` after place and route | Synthesis | **After place and route** |
|---|---:|---:|---:|
| LUT | 35,777 | 31,476 | **31,122** (−4,655, −13.0 %) |
| FF | 31,946 | 29,897 | 29,964 |
| LUTRAM | 2,968 | 3,281 | 2,969 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | −0.567 ns (≈ 180 MHz) | −0.881 ns | **−0.686 ns** (≈ 176 MHz) |
| Register-to-register WHS | +0.050 ns | +0.126 ns | **+0.051 ns** (hold met) |
| Failing endpoints (TNS) | 973 (−105.8 ns) | | 1,661 (−214.3 ns) |

Fully routed, no routing errors. The design-wide hold of −1.237 ns is on the OOC interface ports, as before.

One tile after synthesis: 1,568 → 1,266 logic LUT (−19 %), 1,745 → 1,606 FF. Core-level logic unchanged (7,595 LUT).

Post-route failing groups (worst first):
- **wpe → wps** (FFT T stage, through the fused u − q / p0 + p1 chain): −0.686 ns, 199 endpoints with the replicas. In
  `a_cg_z020_hostdiv` this path was −0.29 ns. The fused chain's select LUT no longer sits with the carry chain, and its
  sources come from two parts of the tile.
- **Block RAM → host line capture** (32 → 1 select): −0.674 ns, 128 endpoints. Not changed by this batch (−0.567 ns in
  `a_cg_z020_hostdiv`, placement varies).
- wpe → r32r through the same fused chain (−0.46 ns). This is an FFT-to-NTT path that never carries data, because the mode
  is fixed during a command, but static timing counts it.
- wb1 → rd (−0.42 ns), plain_r → nhp0 (−0.31 ns): FFT sum operands into the NTT correction outputs through the fused
  correction chains, the same kind of cross-mode path.
- md → u32 / wic / wfc / dif_r (−0.29 .. −0.35 ns): mode decode into the lane cut and limb carries.

## Same RTL at 10 ns (100 MHz, the target since 03/11/2026)

`synth10.tcl`, `implement10.tcl`, `clock_10ns.xdc` (only the clock period differs from the 5 ns constraints). Results in
`study/build/a_cg_z020_share/synth10` and `route10`.

| | 5 ns, after place and route | **10 ns, after place and route** |
|---|---:|---:|
| LUT | 31,122 | **30,349** (−773) |
| FF | 29,964 | 29,897 |
| LUTRAM | 2,969 | 2,969 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | −0.686 ns | **+0.576 ns** (met, 0 failing endpoints) |
| Register-to-register WHS | +0.051 ns | **+0.050 ns** (met) |

After synthesis: 30,690 LUT (one tile 1,222 logic LUT instead of 1,266; core-level logic 7,514 instead of 7,595); FF
unchanged. With 10 ns, Vivado no longer replicates registers or picks faster, larger structures for timing.

The worst path at 10 ns is the FFT program product index broadcast from the core to a tile's limb address register, with
one LUT and 8.8 ns of route. The router stops shortening routes once the 10 ns constraint is met, so this path's slack
does not show how fast the design can run.
