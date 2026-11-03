# Complete command pipeline: physical review

**All internal registers at 200 MHz: PASS.** User approval remains pending.

| Routed design, same 5 ns target | LUT | FF | Internal WNS | Internal WHS |
|---|---:|---:|---:|---:|
| a_cg_prepare_route | 37,356 | 25,367 | -0.456 ns | +0.010 ns |
| a_cg_control | 37,429 | 26,618 | -0.803 ns | +0.010 ns |
| a_cg_control_pipe | 37,437 | 26,622 | -2.918 ns | +0.010 ns |
| a_cg_control_gate | 37,493 | 26,622 | -2.940 ns | +0.010 ns |
| a_cg_cmd_pipe | 37,360 | 26,964 | -1.716 ns | +0.011 ns |
| a_cg_cmd_credit | 37,419 | 26,965 | -0.003 ns | +0.010 ns |
| a_cg_cmd_frontreset | 37,402 | 26,966 | -1.054 ns | +0.010 ns |
| a_cg_cmd_frontreserve | 37,414 | 26,966 | +0.162 ns | +0.010 ns |

DSP/RAMB18: 64/48 (16 root + 32 data banks).
Full-boundary setup/hold: **+0.162/-1.590 ns**.
Execution-only setup/hold: +0.162/+0.010 ns (diagnostic only).

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
    "slack_ns": 0.162,
    "source": "u_exec/engine[4].u_tile/wbi_reg[0]/C",
    "destination": "u_exec/engine[4].u_tile/rd_reg[7]/D",
    "delay": "4.651ns  (logic 1.748ns (37.583%)  route 2.903ns (62.417%))",
    "levels": "16  (CARRY8=8 LUT3=1 LUT4=2 LUT6=5)"
  },
  {
    "slack_ns": 0.164,
    "source": "u_exec/engine[4].u_tile/wbi_reg[0]/C",
    "destination": "u_exec/engine[4].u_tile/s1_reg[9]/D",
    "delay": "4.632ns  (logic 1.815ns (39.184%)  route 2.817ns (60.816%))",
    "levels": "16  (CARRY8=8 LUT4=3 LUT6=5)"
  },
  {
    "slack_ns": 0.176,
    "source": "u_exec/engine[8].u_tile/mf_reg_rep__1/C",
    "destination": "u_exec/engine[8].u_tile/rd_reg[31]/D",
    "delay": "4.584ns  (logic 1.665ns (36.322%)  route 2.919ns (63.678%))",
    "levels": "13  (CARRY8=6 LUT3=1 LUT4=3 LUT6=3)"
  },
  {
    "slack_ns": 0.2,
    "source": "u_exec/engine[4].u_tile/wbi_reg[0]/C",
    "destination": "u_exec/engine[4].u_tile/rd_reg[8]/D",
    "delay": "4.606ns  (logic 1.775ns (38.537%)  route 2.831ns (61.463%))",
    "levels": "16  (CARRY8=8 LUT3=1 LUT4=2 LUT6=5)"
  },
  {
    "slack_ns": 0.207,
    "source": "u_exec/engine[4].u_tile/native_xcarry_reg[0]/C",
    "destination": "u_exec/engine[4].u_tile/rd_reg[10]/D",
    "delay": "4.580ns  (logic 1.841ns (40.196%)  route 2.739ns (59.803%))",
    "levels": "16  (CARRY8=8 LUT3=1 LUT4=2 LUT6=5)"
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

This RTL fork separates the frontend permission flip-flop from execution reset and decodes
accepted flags without raw reset in their D cones. Public readies retain immediate reset masking.
Synthesis proves the load-token D cone uses the local permission and neither global nor raw reset.
Reservation now qualifies an independent priority decode with permission/occupancy at its final LUT.
Synthesis proves exactly one LUT from local permission to reservation. Protocol equality is asserted.
Packet latency, priority and kernel cycles remain unchanged.
A fresh cold implementation uses the same placement/routing directives and constraints as its parent.
Production HDL and retained baselines are unchanged. No bitstream/board deployment was performed.
Raw evidence: study/build/a_cg_cmd_frontreserve/route/. JSON companion records SHA256 hashes.
