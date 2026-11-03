# Complete command pipeline: physical review

**All internal registers at 200 MHz: FAIL.** User approval remains pending.

| Routed design, same 5 ns target | LUT | FF | Internal WNS | Internal WHS |
|---|---:|---:|---:|---:|
| a_cg_prepare_route | 37,356 | 25,367 | -0.456 ns | +0.010 ns |
| a_cg_control | 37,429 | 26,618 | -0.803 ns | +0.010 ns |
| a_cg_control_pipe | 37,437 | 26,622 | -2.918 ns | +0.010 ns |
| a_cg_control_gate | 37,493 | 26,622 | -2.940 ns | +0.010 ns |
| a_cg_cmd_pipe | 37,360 | 26,964 | -1.716 ns | +0.011 ns |
| a_cg_cmd_credit | 37,419 | 26,965 | -0.003 ns | +0.010 ns |

DSP/RAMB18: 64/48 (16 root + 32 data banks).
Full-boundary setup/hold: **-0.003/-1.578 ns**.
Execution-only setup/hold: +0.153/+0.010 ns (diagnostic only).

## Transaction boundary

One capture stage registers every payload field together with its accepted command token: config,
start, root/commit, descriptors, load and read. Payload registers clock unconditionally. Storage
enables consume accepted tokens rather than live context-pending qualification. Host direction
and payload commit also consume tokens. Reset is registered; accepted start drives local reset.
A separate occupancy register replaces feedback from opcode flags. Its equality to the token OR
is checked on every simulation clock. Consumer readiness does not recheck queued opcode flags.
A reservation blocks a second state-changing command until the first is consumed. Root/descriptor
packets stream one per clock. Root-write/commit and descriptor/start ordering is preserved.

## Correctness and latency

All 1,026 frozen vectors, 38 four-state cases and 12 reset-abort/restart mode groups pass.
Config, descriptor, root and load pins change after acceptance; read lines change under burst traffic.
Live C replay passes 74 transform calls, four independent signature verifications, 14 byte-identical
C artifacts and two rejected bad-input replays. Packed16 and all FFT/NTT modes remain supported.
Synthesis proves zero direct raw-input-to-execution-register paths across the command barrier.

Kernel cycles remain identical. Relative to a_cg_control_gate, each load/read line adds one clock;
configuration and start each add one clock. Configuration preparation versus the selected retained
baseline totals six clocks. Every vector is checked against the predicted total interface delta.
Root/descriptor latency is one clock and throughput remains one packet per clock.

## Critical internal setup paths

```json
[
  {
    "slack_ns": -0.003,
    "source": "p_rst_reg/C",
    "destination": "p_load_valid_reg/D",
    "delay": "4.894ns  (logic 0.270ns (5.517%)  route 4.624ns (94.483%))",
    "levels": "2  (LUT3=1 LUT5=1)"
  },
  {
    "slack_ns": 0.153,
    "source": "u_exec/logm_reg[1]/C",
    "destination": "u_exec/engine[8].u_tile/shift_r_reg[1]/D",
    "delay": "4.673ns  (logic 0.081ns (1.733%)  route 4.592ns (98.267%))",
    "levels": "0"
  },
  {
    "slack_ns": 0.214,
    "source": "u_exec/engine[0].u_tile/g_in_reg.rtag_reg[5]/C",
    "destination": "u_exec/engine[15].u_tile/g1_reg[5]/D",
    "delay": "4.603ns  (logic 0.130ns (2.824%)  route 4.473ns (97.176%))",
    "levels": "1  (LUT6=1)"
  },
  {
    "slack_ns": 0.241,
    "source": "u_exec/engine[0].u_tile/g_in_reg.rtag_reg[5]/C",
    "destination": "u_exec/engine[15].u_tile/nhp0_reg[101]/D",
    "delay": "4.576ns  (logic 0.079ns (1.726%)  route 4.497ns (98.274%))",
    "levels": "0"
  },
  {
    "slack_ns": 0.249,
    "source": "u_exec/engine[0].u_tile/g_in_reg.rtag_reg[7]/C",
    "destination": "u_exec/engine[1].u_tile/g1_reg[7]/D",
    "delay": "4.554ns  (logic 0.115ns (2.525%)  route 4.439ns (97.475%))",
    "levels": "1  (LUT6=1)"
  }
]
```

## Scope

- Complete frontend, host adapter and root storage are included; no board/partition pin placement.
- External paths retain max/min I/O delays 1/0 ns and have OOC pin-location limitations.
- The internal 200 MHz verdict includes BOTH frontend and execution registers; core-only timing is diagnostic.
- RTL/vector/live C checks do not establish correct silicon operation at a clock that fails setup or hold.
- No post-route gate simulation, precision reduction, false paths, multicycle exceptions or board deployment.

All routable nets are fully routed with zero routing errors. See raw status for OOC port/gap details.
DRC summary: [{"rule": "DPIP-2", "severity": "Warning", "description": "Input pipelining", "count": 64}, {"rule": "RTSTAT-10", "severity": "Warning", "description": "No routable loads", "count": 1}].

The attempted incremental import crashed in Vivado 2018.1 before placement. This measured result
uses a fresh cold implementation of the new synthesized netlist, with the same placement/routing
directives and timing constraints as the cold-run baseline. The failed import log is retained.
Production HDL and retained baselines are unchanged. No bitstream/board deployment was performed.
Raw evidence: study/build/a_cg_cmd_credit/route/. JSON companion records SHA256 hashes.
