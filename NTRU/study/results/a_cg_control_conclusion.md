# Control-path optimization: measured conclusion

**No tested control prototype closes internal timing at 200 MHz. Do not promote these experiments.**
The retained baseline is also not closed at 200 MHz; it remains the best measured internal setup point.
Production RTL and the selected immutable source are unchanged.

| Routed design, same 5 ns target | LUT | FF | Internal setup WNS | Internal hold WHS |
|---|---:|---:|---:|---:|
| Retained baseline | 37,356 | 25,367 | -0.456 ns | +0.010 ns |
| Local reset + combined config FSM | 37,429 | 26,618 | -0.803 ns | +0.010 ns |
| Private config pipeline | 37,437 | 26,622 | -2.918 ns | +0.010 ns |
| Private pipeline + redundant host gate removed | 37,493 | 26,622 | -2.940 ns | +0.010 ns |

All include the host and roots, packed16, all FFT precision modes, 64 DSP and 48 RAMB18.

## What was established

- Local tile reset distribution has positive leaf setup slack in the last prototype (+1.016 ns).
  Its upstream state-to-reset-register feed still fails (-0.637 ns), so the complete reset path is not closed.
- The redundant cfg_pipe-to-host_line clock-enable dependency is absent from all ten host_line registers
  in the synthesized netlist. This fixes that dependency, not the entire command frontend.
- The new worst internal path is cfg_pipe_reg[0] to engine[8].root_mem_reg/WEBWE[2]:
  -2.940 ns slack, 7.248 ns data delay, of which 6.976 ns (96.247%) is routing.
- Other near-worst paths remain: state to host_direction (-2.913 ns) and cfg_pipe to descriptor CE (-2.911 ns).
  Fixing only root WE would therefore not establish 200 MHz.

These are register-to-register failures. Missing OOC partition-pin locations do not remove those failures.
Full-boundary setup/hold is -2.940/-2.415 ns; external-interface timing also remains incomplete.

## Correctness and contracts

The last source passes 1,026 frozen numeric vectors, 38 four-state cases, 12 reset-abort/restart mode groups,
74 live C transform replacements, four independent signature verifications and 14 byte-identical C artifacts.
Conflicting commands are driven during configuration preparation and the no-exposure invariant is checked.
Tile arithmetic is unchanged apart from a preservation attribute on a control register. No precision or
modular arithmetic has been approximated. Kernel cycle counts match the retained source in every vector.
Configuration preparation adds five clocks per accepted configuration. These are RTL correctness checks,
not evidence of correct silicon operation at a clock that fails timing.

## Design implication

The next architectural candidate should register complete accepted command transactions (valid/type,
destination, address and data together) before fan-out to root/descriptor storage and host state.
Distributed registered write strobes and a bounded reset broadcast tree are needed; adding a shared
pending condition to distant memory/host enables creates long timing paths.
Root commit/drain ordering and any new interface latency must be specified and checked before another
implementation attempt. This frontend revision has not been implemented or measured here.

Evidence: study/results/a_cg_control_gate.{md,json} and study/build/a_cg_control_gate/route/.
The final routed checkpoint is retained for inspection; no bitstream or board deployment was performed.
