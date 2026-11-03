# Local reset and staged config: physical review

Internal register timing at 5 ns: **FAIL**. User approval pending.

| Metric | Retained baseline after route | Control prototype after route |
|---|---:|---:|
| LUT | 37,356 | 37,429 |
| FF | 25,367 | 26,618 |
| DSP | 64 | 64 |
| RAMB18 | 48 | 48 |
| RAMB36 | 0 | 0 |
| Internal setup WNS | -0.456 ns | -0.803 ns |
| Internal hold WHS | +0.010 ns | +0.010 ns |

Full-boundary setup/hold: **-0.803/-1.606 ns**.
Boundary paths are included in that number. OOC partition pin positions are undefined;
do not interpret internal closure as a complete interface or board signoff.

## Changes and correctness

Sixteen local reset registers and sixteen local configuration strobes retain the original compute phases.
The captured configuration is decoded in five setup clocks. No butterfly, precision, modular reduction,
rounding or kernel schedule changes. Per-tile sign-control registers are preserved against merging.

All 1,026 frozen vectors match; 38 four-state cases pass; 12 reset-abort/restart mode groups pass.
Configuration pins are changed immediately after acceptance to check capture semantics.
All kernel cycle counts are identical; host setup adds exactly five clocks per configuration.
Live C replay: 74 transform calls, four independently verified signatures and 14 byte-identical artifacts.
Packed16, runtime moduli, FFT32/64/128 and native64 are retained. Production RTL is unchanged.

## Critical internal setup paths

```json
[
  {
    "slack_ns": -0.803,
    "source": "state_reg[1]/C",
    "destination": "state_reg[0]/CE",
    "delay": "5.497ns  (logic 0.392ns (7.131%)  route 5.105ns (92.869%))",
    "levels": "4  (LUT2=1 LUT6=3)"
  },
  {
    "slack_ns": -0.692,
    "source": "state_reg[1]/C",
    "destination": "state_reg[3]/CE",
    "delay": "5.435ns  (logic 0.392ns (7.213%)  route 5.043ns (92.787%))",
    "levels": "4  (LUT2=1 LUT6=3)"
  },
  {
    "slack_ns": -0.686,
    "source": "state_reg[1]/C",
    "destination": "state_reg[1]/CE",
    "delay": "5.481ns  (logic 0.392ns (7.152%)  route 5.089ns (92.848%))",
    "levels": "4  (LUT2=1 LUT6=3)"
  },
  {
    "slack_ns": -0.658,
    "source": "stage_idx_reg[3]/C",
    "destination": "part_reg[2]/R",
    "delay": "5.251ns  (logic 0.932ns (17.749%)  route 4.319ns (82.251%))",
    "levels": "10  (CARRY8=2 LUT5=1 LUT6=7)"
  },
  {
    "slack_ns": -0.655,
    "source": "stage_idx_reg[3]/C",
    "destination": "part_reg[1]/R",
    "delay": "5.250ns  (logic 0.932ns (17.752%)  route 4.318ns (82.248%))",
    "levels": "10  (CARRY8=2 LUT5=1 LUT6=7)"
  }
]
```

## Reset distribution and configuration

```json
{
  "reset_feed_paths": [
    {
      "slack_ns": 1.001,
      "source": "state_reg[2]/C",
      "destination": "engine[2].reset_local_reg/D",
      "delay": "3.877ns  (logic 0.164ns (4.230%)  route 3.713ns (95.770%))",
      "levels": "2  (LUT4=2)"
    },
    {
      "slack_ns": 1.209,
      "source": "state_reg[2]/C",
      "destination": "engine[5].reset_local_reg/D",
      "delay": "3.566ns  (logic 0.164ns (4.599%)  route 3.402ns (95.401%))",
      "levels": "2  (LUT4=2)"
    }
  ],
  "reset_tree_paths": [
    {
      "slack_ns": 1.935,
      "source": "engine[2].reset_local_reg/C",
      "destination": "engine[2].u_tile/q0_reg[29]/R",
      "delay": "2.731ns  (logic 0.076ns (2.783%)  route 2.655ns (97.217%))",
      "levels": "0"
    },
    {
      "slack_ns": 2.015,
      "source": "engine[10].reset_local_reg/C",
      "destination": "engine[10].u_tile/fmt_r_reg[0]/R",
      "delay": "2.565ns  (logic 0.079ns (3.080%)  route 2.486ns (96.920%))",
      "levels": "0"
    }
  ],
  "config_boundary_paths": [
    {
      "slack_ns": 0.98,
      "source": "cfg_valid",
      "destination": "state_reg[0]/CE",
      "delay": "3.936ns  (logic 0.177ns (4.497%)  route 3.759ns (95.503%))",
      "levels": "3  (LUT6=3)"
    },
    {
      "slack_ns": 1.002,
      "source": "cfg_valid",
      "destination": "state_reg[1]/CE",
      "delay": "3.920ns  (logic 0.177ns (4.515%)  route 3.743ns (95.485%))",
      "levels": "3  (LUT6=3)"
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

Raw reports and checkpoints: `study/build/a_cg_control/route/`. JSON companion includes evidence hashes.
