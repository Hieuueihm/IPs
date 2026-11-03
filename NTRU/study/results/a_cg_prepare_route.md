# Selected prepare_split: physical review

The exact 37,917-LUT synthesis candidate was frozen and implemented once.

| Metric | After routing |
|---|---:|
| LUT | 37,356 |
| FF | 25,367 |
| DSP | 64 |
| RAMB18 | 48 |
| RAMB36 | 0 |
| Internal setup WNS at 5 ns | -0.456 ns |
| Internal hold WHS | +0.010 ns |
| Full-boundary setup WNS | -3.831 ns |
| Full-boundary hold WHS | -1.466 ns |

Internal 200 MHz setup and hold: **FAIL**. User approval remains pending.

Routing: 59,304/59,304 routable nets fully routed, zero nets with routing errors.
OOC status also reports one explicit gap and 476 implicitly routed ports; no board interface is implemented.
DRC: zero errors; 64 DSP input-pipeline warnings and one no-routable-loads warning for boundary outputs.

Includes host, 16 root RAMB18, 32 data RAMB18 and packed16. RTL and numerical contracts are unchanged.
Prior checks: 1,026 numeric cases; 38 four-state cases; 74 live C transform calls; 4 verified signatures.

Placement: AltSpreadLogic_high. Routing: RuntimeOptimized. Constraints: 5 ns clock,
0.100/0.050 ns setup/hold uncertainty, 1/0 ns max/min I/O delay.

## Critical internal setup path

```json
{
  "source": "state_reg[2]/C",
  "destination": "engine[12].u_tile/wbi_reg[0]/R",
  "data_path": "5.257ns  (logic 0.227ns (4.318%)  route 5.030ns (95.682%))",
  "levels": "1  (LUT6=1)"
}
```

The internal worst path is the core state decoder to a tile synchronous reset:
`state_reg[2] -> engine[12].u_tile/wbi_reg[0]/R`.
Its 5.257 ns data delay contains 5.030 ns routing (95.682%) and 0.227 ns logic.
There are also failing paths beyond reset: an engine[0] to engine[6] path at -0.207 ns
and a tile arithmetic-input path at -0.173 ns. Fixing reset alone does not establish closure.

The full-design worst setup path is `cfg_logn[0] -> planes_reg[1]/D` (-3.831 ns).
It is an actual configuration path as well as an OOC-boundary path; it cannot simply be ignored.
The configuration interface needs a defined physical/register boundary before system signoff.

## Scope

- OOC core including host and root; no board/partition pin placement or bitstream.
- Boundary timing uses 1/0 ns max/min I/O delays, not a board interface model.
- Register-to-register setup/hold is reported separately from boundary paths.
- Route status reports one explicit gap and 476 implicitly routed ports in this OOC design.
- One fast routing attempt; not an exhaustive physical optimization.
- Correctness evidence belongs to the unchanged RTL; no post-route gate-level simulation.

See `study/build/a_cg_prepare_route/fast/` for the routed checkpoint, routing status, DRC,
utilization and separate internal/boundary timing reports. See the JSON companion for hashes.
