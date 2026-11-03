# Local reset and staged config: physical review

Internal register timing at 5 ns: **FAIL**. User approval pending.

| Metric | Retained baseline after route | Control prototype after route |
|---|---:|---:|
| LUT | 37,356 | 37,437 |
| FF | 25,367 | 26,622 |
| DSP | 64 | 64 |
| RAMB18 | 48 | 48 |
| RAMB36 | 0 | 0 |
| Internal setup WNS | -0.456 ns | -2.918 ns |
| Internal hold WHS | +0.010 ns | +0.010 ns |

Full-boundary setup/hold: **-2.918/-2.167 ns**.
Boundary paths are included in that number. OOC partition pin positions are undefined;
do not interpret internal closure as a complete interface or board signoff.

## Changes and correctness

Sixteen local reset registers and sixteen local configuration strobes retain the original compute phases.
The captured configuration is decoded in five setup clocks. No butterfly, precision, modular reduction,
rounding or kernel schedule changes. Per-tile sign-control registers are preserved against merging.

Configuration setup uses a private five-bit valid pipeline, so it adds no states to the compute/host FSM.
The prior combined-FSM prototype is retained separately in `experiments/a_cg_control/`.

All 1,026 frozen vectors match; 38 four-state cases pass; 12 reset-abort/restart mode groups pass.
Configuration pins are changed immediately after acceptance to check capture semantics.
All kernel cycle counts are identical; host setup adds exactly five clocks per configuration.
Live C replay: 74 transform calls, four independently verified signatures and 14 byte-identical artifacts.
Packed16, runtime moduli, FFT32/64/128 and native64 are retained. Production RTL is unchanged.

## Critical internal setup paths

```json
[
  {
    "slack_ns": -2.918,
    "source": "cfg_pipe_reg[4]/C",
    "destination": "host_line_reg[1]/CE",
    "delay": "7.623ns  (logic 0.283ns (3.712%)  route 7.340ns (96.288%))",
    "levels": "5  (LUT2=1 LUT5=2 LUT6=2)"
  },
  {
    "slack_ns": -2.918,
    "source": "cfg_pipe_reg[4]/C",
    "destination": "host_line_reg[3]/CE",
    "delay": "7.623ns  (logic 0.283ns (3.712%)  route 7.340ns (96.288%))",
    "levels": "5  (LUT2=1 LUT5=2 LUT6=2)"
  },
  {
    "slack_ns": -2.918,
    "source": "cfg_pipe_reg[4]/C",
    "destination": "host_line_reg[4]/CE",
    "delay": "7.623ns  (logic 0.283ns (3.712%)  route 7.340ns (96.288%))",
    "levels": "5  (LUT2=1 LUT5=2 LUT6=2)"
  },
  {
    "slack_ns": -2.918,
    "source": "cfg_pipe_reg[4]/C",
    "destination": "host_line_reg[5]/CE",
    "delay": "7.624ns  (logic 0.283ns (3.712%)  route 7.341ns (96.288%))",
    "levels": "5  (LUT2=1 LUT5=2 LUT6=2)"
  },
  {
    "slack_ns": -2.918,
    "source": "cfg_pipe_reg[4]/C",
    "destination": "host_line_reg[6]/CE",
    "delay": "7.624ns  (logic 0.283ns (3.712%)  route 7.341ns (96.288%))",
    "levels": "5  (LUT2=1 LUT5=2 LUT6=2)"
  }
]
```

## Reset distribution and configuration

```json
{
  "reset_feed_paths": [
    {
      "slack_ns": 0.182,
      "source": "cfg_pipe_reg[4]/C",
      "destination": "engine[8].reset_local_reg/D",
      "delay": "4.560ns  (logic 0.336ns (7.368%)  route 4.224ns (92.632%))",
      "levels": "3  (LUT4=1 LUT5=2)"
    },
    {
      "slack_ns": 0.182,
      "source": "cfg_pipe_reg[4]/C",
      "destination": "engine[0].reset_local_reg/D",
      "delay": "4.528ns  (logic 0.336ns (7.420%)  route 4.192ns (92.579%))",
      "levels": "3  (LUT4=1 LUT5=2)"
    }
  ],
  "reset_tree_paths": [
    {
      "slack_ns": 1.325,
      "source": "engine[11].reset_local_reg/C",
      "destination": "engine[11].u_tile/wpv_reg/R",
      "delay": "3.445ns  (logic 0.079ns (2.293%)  route 3.366ns (97.707%))",
      "levels": "0"
    },
    {
      "slack_ns": 1.48,
      "source": "engine[11].reset_local_reg/C",
      "destination": "engine[11].u_tile/q0_reg[15]/R",
      "delay": "3.279ns  (logic 0.079ns (2.409%)  route 3.200ns (97.591%))",
      "levels": "0"
    }
  ],
  "config_boundary_paths": [
    {
      "slack_ns": -1.636,
      "source": "cfg_valid",
      "destination": "host_line_reg[1]/CE",
      "delay": "7.112ns  (logic 0.209ns (2.939%)  route 6.903ns (97.061%))",
      "levels": "4  (LUT2=1 LUT5=1 LUT6=2)"
    },
    {
      "slack_ns": -1.636,
      "source": "cfg_valid",
      "destination": "host_line_reg[3]/CE",
      "delay": "7.112ns  (logic 0.209ns (2.939%)  route 6.903ns (97.061%))",
      "levels": "4  (LUT2=1 LUT5=1 LUT6=2)"
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

Raw reports and checkpoints: `study/build/a_cg_control_pipe/route/`. JSON companion includes evidence hashes.
