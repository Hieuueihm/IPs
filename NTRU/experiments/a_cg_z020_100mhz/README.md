# XC7Z020 at 100 MHz: stages added only for 5 ns removed

> **Mốc đối chiếu, không phải baseline hiện hành.** Từ 2026-11-04 baseline được nhận là [a_cg_z020_system160](../BASELINE.md). Số đo dưới đây chỉ thuộc cấu hình/source của thư mục này; không thay cho STA toàn hệ thống 160 MHz.


Child of `a_cg_z020_share`. Production `hdl/`, PLAN and spec unchanged; nothing committed. The batch is section 3 of
`docs/ra_soat_tang_thoi_gian_10ns.md` (approved 04/11/2026, with the tile latency change and one command stage less).
The target clock is 100 MHz (10 ns) since 03/11/2026, so every measurement here is at 10 ns (`synth10.tcl`,
`implement10.tcl`, `clock_10ns.xdc`; the 5 ns scripts were dropped).

## Changes

| Change | Behavior |
|---|---|
| **Tile add/sub in one clock.** The corrections a + b − q and a − b + q follow the first chains in the same clock (the two-clock version of `a_cg_z020_lat1` kept the first chains' results in registers). The fused chains with the FFT sums stay | Same values. New simulation shadow: plain modular add/sub per lane, for inputs below q |
| **Tile request register of `a_cg_z020_lat1` removed** (`rqd_*`): the operand stage takes the request in the clock of the add/sub (GS) | **Tile contract: −1 clock**, every mode |
| **CT output not delayed** (`tv_d`, `tag_d`, `sw6t_d` removed): NTT CT and FFT forward results leave the add/sub in the clock of the result | **NTT CT and FFT forward −1 more** |
| **Tile input register off** (`IN_REG = 0` in the core; the core's `req_x` / `req_y` already feed the tile). The NTRUGen A + 1 is made in front of the add/sub (`g_bias_wire`, already in the tile) | **Tile contract: −1 clock**, every mode. FFT product program 2 clocks earlier (`program_d` 4 / 6 / 8 / 10); its delay lines are 9 entries, the tap picked by a fixed select |
| **One command stage** (`q_*` removed): the core takes the commands from `p_*`. `reserved` is the occupancy of that stage; `accepted_main_d` removed. `synth10.tcl` checks one stage and the response barrier; `tb_pipeline_reset.sv` checks a reset with the command in that stage | Every command reaches the core one clock earlier |
| **div2e at the host read in one clock**: one add per word, the carry passed word to word and cut where a value starts (the AND trees of precomputed carries, the `sa_*` stage, `scale_lowm`, `scale_nz` removed) | Host read −1 clock. The div2e reference shadow is unchanged |
| **div2e shift as an arithmetic shift of each value** (added after the first two measurements, 04/11/2026): two levels of 4-to-1 selects (by s[1:0], then s[3:2]); a bit whose source lies above its value's top takes the value's sign. It replaces the logical shift of the whole line followed by a fill compare per bit | Same values (the div2e reference shadow checks every line read). Alone, synthesized: 378 → 291 LUT. Random check of all s 0 .. 15 and fmt 0 .. 2 against a plain arithmetic shift: 6,000 vectors exact; a boundary fault gave 1,746 differences |
| **`cfg_ready`, `load_ready`, `read_ready`, `busy` from the state** (no next-state registers; `state_nx` removed) | Same values in every clock |
| **Host bank basis for one direction**: registered for the direction of the next clock (`host_direction_nx`), instead of both directions and a select | Same values |
| **Modulus slot at the result from `ks[E32]`** (the slot shift register) instead of bit 41 of the side memory `wma` (now 41 bits). The add/sub and the GS halving select q by this slot. With the core's constant slot 0 the select disappears; read from the memory, synthesis kept it, and in the one-clock add/sub it went into every LUT of the two correction chains (see the first measurement below) | Same values. Simulation shadow: the slot carried through a ring beside `wma`, as before. New tile test `tb_tile_slots.sv` (both slots, CT and GS) in `run_sim.ps1`; the core never uses slot 1 |
| **Host bank selects (`hsel`) combinational** from the prepared map (`host_select`, `host_bank`), not registered from next-clock values | Same values |

Tile latency against `a_cg_z020_share`: NTT GS −2, NTT CT −3, FFT inverse −2, FFT forward −3 (the review estimated
FFT −2: in `a_cg_z020_share` the forward FFT results already went through the two-clock add/sub, so they gain its clock
too). Planner: `TILE_EXTRA = -1`, `NTT_CT_EXTRA = 0`, `FFT_OUT_SAME = 1`.

## Results

Functional (`run_sim.ps1`, `compare.py`): 1,026 cases exact, kernel cycles equal to the planner in every case; reset
abort 12 modes; 38 four-state; pipeline reset (one command stage); 74 live C calls, 14 identical artifacts, 4
signatures. Against `a_cg_cmd_dispatch2` (before the 5 ns stages): kernel cycles −0.57 % in total, every case equal or
shorter (−23 .. 0).

Fault injection (four-state run): with the q correction of the add/sub removed (`sneg_h` forced), the new add/sub shadow
stopped the run at the first NTT case (packed, q = 12289).

Kernel cycles, sum over the 1,026 cases: 559,565 → **550,644 (−1.59 %)**. The driver's whole host time per case
(configuration, descriptors, roots, loads, kernel, reads): 2,361,794 → 2,111,547 clocks (−10.6 %).

Fault injection (tile test): every request on slot 0 (`FAULT_IGNORE_SLOT`) gave wrong results; the result slot taken
one clock early stopped the run at the slot shadow.

### First measurement, without the slot change (`study/build/a_cg_z020_100mhz/synth10_try1`, `route10_try1`)

| | `a_cg_z020_share`, 10 ns | first measurement |
|---|---:|---:|
| LUT after place and route | 30,349 | 30,989 (+640) |
| FF | 29,897 | 24,155 (−5,742) |
| Synthesis: 16 tiles, logic LUT (a typical tile) | 19,874 (1,222) | 20,621 (1,270) |
| Synthesis: core-level logic LUT | 7,514 | 7,414 |
| WNS / WHS after place and route | +0.576 / +0.050 ns | +0.274 / +0.050 ns |

The tile grew by 48 LUT. One tile synthesized alone with the core's constant ties (`study/tools/lean_attrib`,
`study/build/lean_tile`), logic LUT:

| Tile | Logic LUT | FF |
|---|---:|---:|
| `a_cg_z020_share`, input register on (as in its core) | 1,138 | 1,648 |
| `a_cg_z020_share`, input register off | 1,137 | 1,538 |
| this batch, slot read from the side memory | 1,182 | 1,319 |
| same, with `keep` on the add/sub's first chains | 1,188 | 1,320 |
| same, add/sub q taken from slot 0 only (measurement only) | 1,121 | 1,319 |
| **this batch, slot from `ks[E32]`** | **1,123** | 1,320 |

The input register costs no LUT. The one-clock add/sub cost LUT only because q was picked by a slot read from the side
memory: in the two-clock version the register `q_r` held the picked q; without it, the pick went into each LUT of the two
correction chains (LUT5 became LUT6, fewer LUT pairs). Taking the slot from `ks[E32]` removes the pick in the core.

### Second measurement, with the slot change (`synth10_slot`, `route10_slot`)

XC7Z020-CLG400-2, 10 ns:

| | `a_cg_z020_share`, after place and route | Synthesis | **After place and route** |
|---|---:|---:|---:|
| LUT | 30,349 | 30,422 | **30,075** (−274) |
| LUT as logic / as memory | 27,380 / 2,969 | 27,142 / 3,280 | 27,107 / 2,968 |
| FF | 29,897 | 24,139 | **24,139** (−5,758, −19.3 %) |
| DSP / RAMB18 | 64 / 48 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | +0.576 ns | +1.604 ns | **+0.236 ns** (met, 0 failing endpoints) |
| Register-to-register WHS | +0.050 ns | +0.126 ns | **+0.040 ns** (met) |

Fully routed, no routing errors. The design-wide hold of −1.237 ns is on the OOC interface ports, as before.

After synthesis: 16 tiles 19,708 logic LUT (a typical tile 1,213; `a_cg_z020_share` 19,874 and 1,222), core-level logic
7,414 (7,514). Every barrier check of `synth10.tcl` passes: no input reaches the core directly, one command stage (341
registers), no second stage, no core-to-response bypass, the reservation is one logic level from its permission.

The worst setup path is again the FFT program broadcast from the core (`e_step`) to a tile's program register, no logic
and 8.9 ns of route: the router stops shortening routes once 10 ns is met. The worst hold path is the host read
(`line_data` → `rs_sum`).

LUT was 75 above the 30k goal, so the div2e shift was rewritten (the change list above).

### Final measurement, with the div2e shift (`synth10`, `route10`)

XC7Z020-CLG400-2, 10 ns:

| | `a_cg_z020_share`, after place and route | second measurement | Synthesis | **After place and route** |
|---|---:|---:|---:|---:|
| LUT | 30,349 | 30,075 | 30,174 | **29,837** (−512 vs `a_cg_z020_share`) |
| LUT as logic / as memory | 27,380 / 2,969 | 27,107 / 2,968 | 26,894 / 3,280 | 26,869 / 2,968 |
| FF | 29,897 | 24,139 | 24,115 | **24,115** (−5,782, −19.3 %) |
| DSP / RAMB18 | 64 / 48 | 64 / 48 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | +0.576 ns | +0.236 ns | +1.604 ns | **+0.032 ns** (met, 0 failing endpoints) |
| Register-to-register WHS | +0.050 ns | +0.040 ns | +0.126 ns | **+0.051 ns** (met) |

Fully routed, no routing errors; every barrier check of `synth10.tcl` passes. After synthesis: 16 tiles 19,713 logic
LUT (a typical tile 1,213), core-level logic 7,161 (7,414 in the second measurement, 7,514 in `a_cg_z020_share`).

The worst setup path is now the host-read rounding add of div2e (`scale_r` → `rs_sum[125]`): one carry chain through the
four words of a 128-bit value, 35 CARRY4, 9.66 ns. It comes from the one-clock rounding add of this batch (the two-clock
version precomputed the carries between words). It meets 10 ns with 32 ps; if it ever fails, the carry into each word
can be made from an all-ones detect of the words below in the same clock (the AND trees of `a_cg_z020_share`, without
their register), for about 50 LUT. The worst hold path is `sa5` → the limb sum memory `wmsx` in a tile.
