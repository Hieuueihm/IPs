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
| a_cg_cmd_frontreset | 37,402 | 26,966 | -1.054 ns | +0.010 ns |

DSP/RAMB18: 64/48 (16 root + 32 data banks).
Full-boundary setup/hold: **-1.054/-2.236 ns**.
Execution-only setup/hold: +0.004/+0.010 ns (diagnostic only).

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
    "slack_ns": -1.054,
    "source": "frontend_live_reg/C",
    "destination": "reserved_reg/D",
    "delay": "5.875ns  (logic 0.444ns (7.557%)  route 5.431ns (92.443%))",
    "levels": "3  (LUT4=3)"
  },
  {
    "slack_ns": 0.004,
    "source": "u_exec/engine[14].u_tile/wic_reg[1]/C",
    "destination": "u_exec/engine[14].u_tile/s1_reg[14]/D",
    "delay": "4.687ns  (logic 1.493ns (31.854%)  route 3.194ns (68.146%))",
    "levels": "15  (CARRY8=7 LUT4=3 LUT5=1 LUT6=4)"
  },
  {
    "slack_ns": 0.063,
    "source": "u_exec/engine[14].u_tile/wic_reg[1]/C",
    "destination": "u_exec/engine[14].u_tile/s1_reg[10]/D",
    "delay": "4.615ns  (logic 1.617ns (35.038%)  route 2.998ns (64.962%))",
    "levels": "15  (CARRY8=7 LUT4=3 LUT5=1 LUT6=4)"
  },
  {
    "slack_ns": 0.089,
    "source": "u_exec/engine[14].u_tile/wic_reg[1]/C",
    "destination": "u_exec/engine[14].u_tile/rd_reg[9]/D",
    "delay": "4.601ns  (logic 1.635ns (35.536%)  route 2.966ns (64.464%))",
    "levels": "15  (CARRY8=7 LUT3=1 LUT4=2 LUT5=1 LUT6=4)"
  },
  {
    "slack_ns": 0.103,
    "source": "u_exec/engine[14].u_tile/wic_reg[1]/C",
    "destination": "u_exec/engine[14].u_tile/rd_reg[16]/D",
    "delay": "4.576ns  (logic 1.595ns (34.856%)  route 2.981ns (65.144%))",
    "levels": "15  (CARRY8=7 LUT4=3 LUT5=1 LUT6=4)"
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
One permission register is added; packet latency, priority and kernel cycles remain unchanged.
A fresh cold implementation uses the same placement/routing directives and constraints as its parent.
Production HDL and retained baselines are unchanged. No bitstream/board deployment was performed.
Raw evidence: study/build/a_cg_cmd_frontreset/route/. JSON companion records SHA256 hashes.
