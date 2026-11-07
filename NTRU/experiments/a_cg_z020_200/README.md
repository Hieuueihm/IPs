# XC7Z020: block RAM output register, one more read stage, 200 MHz after place and route

Child of `a_cg_z020_hostdiv` (div2e at the host read, registered interface). Production `hdl/`, PLAN and spec unchanged;
nothing committed. Each change keeps a simulation-only shadow of the previous logic, or a check that the new copy equals
the signal it copies, which stops the simulation on a difference.

## Changes

| Change | Behavior |
|---|---|
| Data banks: the read data passes the block RAM output register; the write port (enable, row, data) is registered | Read data one clock later; every compute and host write lands one clock later. The same-clock read-after-write check uses the registered write |
| Compute read pipeline one stage longer: issue → RAM → RAM output register → request register → tile. The request stage's valid and selects (`far`, `near`, `geom`, `dummy`) are copied per tile; the root RAM gets its own output register | NTT reads are issued one clock earlier (phase 0 instead of 1), so the tile accepts at the same clock as before. FFT reads stay at the same clock and the tile accepts one clock later |
| Host line capture one clock later (select, out-of-data flag and bank copied once more); the scaler starts one clock later | Host read response +1 clock |
| Tile: Montgomery `u − q` as one 35-bit chain with a guard bit at 16 (packed mode cuts the low lane there and gives the high lane its own +1) | Same values; replaces the two separate subtractions and their select |
| Planner: `RD_EXTRA = 1` (FFT accept one clock later; NTT read one clock earlier), `WR_EXTRA = 1` (every write one clock later); the model counts cycles from the first stage start, as the RTL does | Kernel cycles equal to the RTL for every case |

## Results

Functional (`run_sim.ps1`, `compare.py`): 1,026 cases exact, kernel cycles equal to the planner; 38 four-state; pipeline
reset; 74 live C calls, 14 identical artifacts, 4 signatures.

Kernel cycles, sum over the 1,026 cases, against `a_cg_z020_hostdiv` (the later write delays a stage that reads what the
previous stage wrote; the start moves by whole beats):

| Mode | hostdiv | this batch | Change |
|---|---:|---:|---:|
| FFT 32 | 6,170 | 6,604 | +7.0 % (+0 to +22 per case) |
| FFT 64 | 30,696 | 30,990 | +1.0 % (+0 to +11) |
| FFT 128 | 306,274 | 306,980 | +0.23 % (+0 to +11) |
| NTT 32-bit forward / inverse | 64,947 / 64,788 | 66,399 / 64,788 | +2.2 % / 0 |
| NTT packed 16-bit forward / inverse | 43,938 / 43,812 | 45,111 / 43,812 | +2.7 % / 0 |
| All | 560,625 | 564,684 | +0.72 % (+1.97 % against dispatch2) |

XC7Z020-CLG400-2, 5 ns:

| | Synthesis | **After place and route** (Explore directives) |
|---|---:|---:|
| LUT | 35,602 | 35,259 |
| FF | 33,693 | 33,706 |
| LUTRAM | 3,282 | 2,970 |
| DSP / RAMB18 | 64 / 48 | 64 / 48 |
| Register-to-register WNS | +0.056 ns | about −0.43 ns (router log; not reported) |
| Register-to-register WHS | +0.126 ns | not reported |

Fully routed, no routing errors. The run was stopped while the timing reports were being written, so there is no
`timing.rpt`, `metrics.txt` or failing endpoint list. The router's last summary was WNS −0.432 ns, TNS −4.98 ns (≈ 184 MHz).
Its WHS of −1.268 ns is design-wide, including the OOC interface ports (like the −1.272 ns of `a_cg_z020_hostdiv`).
Register-to-register hold was not measured.

## Decision

The batch is stopped. 200 MHz is not required on XC7Z020; the stop point is a routed design that passes hold. The
retained version is `a_cg_z020_hostdiv`: 35,777 LUT, 31,946 FF, setup WNS −0.567 ns (≈ 180 MHz), register-to-register
WHS +0.050 ns. Compared with it, this batch gains about 0.14 ns of setup for +1,760 FF and +0.72 % kernel cycles.
