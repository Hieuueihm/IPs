# Local reset and staged config: physical review

Internal register timing at 5 ns: **FAIL**. User approval pending.

| Metric | Retained baseline after route | Control prototype after route |
|---|---:|---:|
| LUT | 37,356 | 37,493 |
| FF | 25,367 | 26,622 |
| DSP | 64 | 64 |
| RAMB18 | 48 | 48 |
| RAMB36 | 0 | 0 |
| Internal setup WNS | -0.456 ns | -2.940 ns |
| Internal hold WHS | +0.010 ns | +0.010 ns |

Full-boundary setup/hold: **-2.940/-2.415 ns**.
Boundary paths are included in that number. OOC partition pin positions are undefined;
do not interpret internal closure as a complete interface or board signoff.

## Changes and correctness

Sixteen local reset registers and sixteen local configuration strobes retain the original compute phases.
The captured configuration is decoded in five setup clocks. No butterfly, precision, modular reduction,
rounding or kernel schedule changes. Per-tile sign-control registers are preserved against merging.

Configuration setup uses a private five-bit valid pipeline, so it adds no states to the compute/host FSM.
The prior combined-FSM prototype is retained separately in `experiments/a_cg_control/`.

The redundant pending gate on host acceptance has been removed. Configured stays zero during all five
setup clocks; simulation checks this invariant while conflicting commands are asserted.
Synthesis requires zero cfg_pipe registers in the combinational fan-in of every host_line clock enable.

All 1,026 frozen vectors match; 38 four-state cases pass; 12 reset-abort/restart mode groups pass.
Configuration pins are changed immediately after acceptance to check capture semantics.
All kernel cycle counts are identical; host setup adds exactly five clocks per configuration.
Live C replay: 74 transform calls, four independently verified signatures and 14 byte-identical artifacts.
Packed16, runtime moduli, FFT32/64/128 and native64 are retained. Production RTL is unchanged.

## Critical internal setup paths

```json
[
  {
    "slack_ns": -2.94,
    "source": "cfg_pipe_reg[0]/C",
    "destination": "engine[8].root_mem_reg/WEBWE[2]",
    "delay": "7.248ns  (logic 0.272ns (3.753%)  route 6.976ns (96.247%))",
    "levels": "3  (LUT2=1 LUT5=1 LUT6=1)"
  },
  {
    "slack_ns": -2.929,
    "source": "cfg_pipe_reg[0]/C",
    "destination": "engine[6].root_mem_reg/WEBWE[1]",
    "delay": "7.524ns  (logic 0.367ns (4.878%)  route 7.157ns (95.122%))",
    "levels": "3  (LUT2=1 LUT5=1 LUT6=1)"
  },
  {
    "slack_ns": -2.923,
    "source": "cfg_pipe_reg[0]/C",
    "destination": "engine[6].root_mem_reg/WEBWE[0]",
    "delay": "7.518ns  (logic 0.367ns (4.882%)  route 7.151ns (95.118%))",
    "levels": "3  (LUT2=1 LUT5=1 LUT6=1)"
  },
  {
    "slack_ns": -2.913,
    "source": "state_reg[1]/C",
    "destination": "host_direction_reg/D",
    "delay": "7.777ns  (logic 0.276ns (3.549%)  route 7.501ns (96.451%))",
    "levels": "3  (LUT2=1 LUT4=1 LUT6=1)"
  },
  {
    "slack_ns": -2.911,
    "source": "cfg_pipe_reg[0]/C",
    "destination": "desc_reg[2][39]/CE",
    "delay": "7.720ns  (logic 0.355ns (4.598%)  route 7.365ns (95.402%))",
    "levels": "3  (LUT4=1 LUT5=2)"
  }
]
```

## Reset distribution and configuration

```json
{
  "reset_feed_paths": [
    {
      "slack_ns": -0.637,
      "source": "state_reg[0]/C",
      "destination": "engine[6].reset_local_reg/D",
      "delay": "5.597ns  (logic 0.338ns (6.039%)  route 5.259ns (93.961%))",
      "levels": "2  (LUT4=1 LUT5=1)"
    },
    {
      "slack_ns": -0.492,
      "source": "state_reg[0]/C",
      "destination": "engine[14].reset_local_reg/D",
      "delay": "5.450ns  (logic 0.338ns (6.202%)  route 5.112ns (93.798%))",
      "levels": "2  (LUT4=1 LUT5=1)"
    }
  ],
  "reset_tree_paths": [
    {
      "slack_ns": 1.016,
      "source": "engine[7].reset_local_reg/C",
      "destination": "engine[7].u_tile/wbi_reg[0]/R",
      "delay": "3.485ns  (logic 0.200ns (5.739%)  route 3.285ns (94.261%))",
      "levels": "1  (LUT2=1)"
    },
    {
      "slack_ns": 1.016,
      "source": "engine[7].reset_local_reg/C",
      "destination": "engine[7].u_tile/wbi_reg[1]/R",
      "delay": "3.485ns  (logic 0.200ns (5.739%)  route 3.285ns (94.261%))",
      "levels": "1  (LUT2=1)"
    }
  ],
  "config_boundary_paths": [
    {
      "slack_ns": -1.066,
      "source": "cfg_valid",
      "destination": "host_direction_reg/D",
      "delay": "6.783ns  (logic 0.165ns (2.433%)  route 6.618ns (97.567%))",
      "levels": "2  (LUT4=1 LUT6=1)"
    },
    {
      "slack_ns": -0.62,
      "source": "cfg_valid",
      "destination": "host_word_reg[0]/R",
      "delay": "6.235ns  (logic 0.280ns (4.491%)  route 5.955ns (95.509%))",
      "levels": "3  (LUT2=1 LUT5=1 LUT6=1)"
    }
  ]
}
```

## Physical scope

The same placement and fast timing-driven routing directives are used as the retained baseline.
All routable nets are fully routed with zero routing errors. See raw route status for OOC gaps/ports.
DRC summary: [{"rule": "DPIP-2", "severity": "Warning", "description": "Input pipelining", "count": 64}, {"rule": "RTSTAT-10", "severity": "Warning", "description": "No routable loads", "count": 1}].

- OOC core includes host and roots, with no physical board/partition pin placement.
- Global boundary timing uses unchanged max/min I/O delay 1/0 ns; inspect both setup and hold.
- Positive internal timing alone is not a board or complete interface timing signoff.
- RTL correctness checked with frozen vectors and live C kernel replay; no post-route gate simulation.
- Configuration acceptance requires five additional setup clocks before cfg_ready returns.

Raw reports and checkpoints: `study/build/a_cg_control_gate/route/`. JSON companion includes evidence hashes.
