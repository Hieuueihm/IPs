# Complete command pipeline: physical review

**All internal registers at 200 MHz: FAIL.** User approval remains pending.

| Routed design, same 5 ns target | LUT | FF | Internal WNS | Internal WHS |
|---|---:|---:|---:|---:|
| a_cg_prepare_route | 37,356 | 25,367 | -0.456 ns | +0.010 ns |
| a_cg_control | 37,429 | 26,618 | -0.803 ns | +0.010 ns |
| a_cg_control_pipe | 37,437 | 26,622 | -2.918 ns | +0.010 ns |
| a_cg_control_gate | 37,493 | 26,622 | -2.940 ns | +0.010 ns |
| a_cg_cmd_pipe | 37,360 | 26,964 | -1.716 ns | +0.011 ns |

DSP/RAMB18: 64/48 (16 root + 32 data banks).
Full-boundary setup/hold: **-1.716/-2.447 ns**.
Execution-only setup/hold: +0.040/+0.011 ns (diagnostic only).

## Transaction boundary

One capture stage registers every payload field together with its accepted command token: config,
start, root/commit, descriptors, load and read. Payload registers clock unconditionally. Storage
enables consume accepted tokens rather than live context-pending qualification. Host direction
and payload commit also consume tokens. Reset is registered; accepted start drives local reset.
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
    "slack_ns": -1.716,
    "source": "p_cfg_valid_reg/C",
    "destination": "p_load_valid_reg/D",
    "delay": "6.494ns  (logic 0.263ns (4.050%)  route 6.231ns (95.950%))",
    "levels": "2  (LUT5=1 LUT6=1)"
  },
  {
    "slack_ns": 0.04,
    "source": "u_exec/engine[15].u_tile/mf_reg_rep__1/C",
    "destination": "u_exec/engine[15].u_tile/s1_reg[9]/D",
    "delay": "4.617ns  (logic 1.553ns (33.637%)  route 3.064ns (66.363%))",
    "levels": "14  (CARRY8=7 LUT4=3 LUT6=4)"
  },
  {
    "slack_ns": 0.049,
    "source": "u_exec/engine[12].u_tile/wbi_reg[1]/C",
    "destination": "u_exec/engine[12].u_tile/rd_reg[33]/D",
    "delay": "4.766ns  (logic 1.651ns (34.641%)  route 3.115ns (65.359%))",
    "levels": "16  (CARRY8=8 LUT4=3 LUT6=5)"
  },
  {
    "slack_ns": 0.05,
    "source": "u_exec/engine[15].u_tile/mf_reg_rep__1/C",
    "destination": "u_exec/engine[15].u_tile/s1_reg[2]/D",
    "delay": "4.607ns  (logic 1.511ns (32.798%)  route 3.096ns (67.202%))",
    "levels": "14  (CARRY8=7 LUT4=3 LUT6=4)"
  },
  {
    "slack_ns": 0.06,
    "source": "u_exec/engine[12].u_tile/wbi_reg[1]/C",
    "destination": "u_exec/engine[12].u_tile/rd_reg[24]/D",
    "delay": "4.754ns  (logic 1.663ns (34.981%)  route 3.091ns (65.019%))",
    "levels": "16  (CARRY8=8 LUT4=3 LUT6=5)"
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

Production HDL and retained baselines are unchanged. No bitstream/board deployment was performed.
Raw evidence: study/build/a_cg_cmd_pipe/route/. JSON companion records SHA256 hashes.
