# Registered command transactions: isolated prototype

Parent source: `experiments/a_cg_control_gate/rtl/`. Production HDL and all retained
baselines stay unchanged. Numerical tile RTL and multiplier RTL are byte-identical
to that parent. Packed16, NTT32/modulus selection, FFT32/64/128 and native64 remain
runtime features. The entire host frontend and root cache are included in PPA.

## Interface and ordering

Every payload field is sampled into an unconditional register on the acceptance
edge. Qualified valid/type strobes cross the same edge. On the following clock,
the execution core consumes that registered transaction, not live external pins.
This covers config, start, root/commit, descriptors, load and read. Root writes
carry the captured destination mask/address/data; descriptor writes carry the
captured stage/mask/root metadata/gap. The reset input is also registered.

Only one state-changing command may be in the capture stage. Its reservation
suppresses ready until the core consumes it. Root and descriptor commands can
stream at one packet per clock while the context window remains open. Config has
priority over start; start has priority over load; load has priority over read.
Config/start suppress new root/descriptor requests on the same edge. Root and
descriptor channels may otherwise overlap each other or a host line command.
Descriptor stages outside 0..9 are ignored at acceptance.

Consumer-side root/descriptor storage enables use the qualified tokens. They do
not re-evaluate a global pending condition. Simulation checks that every token
arrives in an executable core state. Host direction, line and load data are
committed from accepted tokens without live interface qualification on their CEs.

Public handshake adds one capture clock per load/read command. Configuration
setup is six clocks after acceptance, compared with five in the control parent;
start completion is shifted by one clock. Root/descriptor command latency is one
clock and throughput is still one per clock. Root commit follows the same stream,
so a commit cannot overtake a preceding root write. Descriptor writes precede
start with the same ordering. Kernel cycle counts and butterfly schedules stay
unchanged. Full cold latency, including these interface clocks, is checked and
reported rather than hidden in kernel cycles.

Synchronous reset flushes the capture strobes and blocks public ready/response
valids immediately; the core receives reset on the following edge. An accepted
root/descriptor write preceding reset can finish at that edge. The context is
invalidated before any new command can execute. A one-edge reset can abort a job;
tests reconfigure and restart all twelve mode/direction groups.

## Validation and physical run

`run_sim.ps1` uses the frozen 1,026 numeric vectors and 38 four-state cases. It
changes configuration, descriptor, root and load pins after acceptance; read
lines change under burst/backpressure. Live C replay substitutes only the four
transform kernels and requires 74 calls, four independently verified signatures,
14 byte-identical C artifacts and two rejected wrong-input replays.

`validate.py` requires unchanged kernel cycles and the predicted interface cost:
relative to the control parent, two extra clocks per 128-bit line (one load plus
one read), plus one config and one start clock per case. Synthesis must show zero
direct paths from raw input ports to execution-core registers. No primary config,
root, descriptor or host signal may bypass the packet register boundary.

The same xczu7ev-ffvc1156-2-e, 5 ns clock, 0.100/0.050 ns setup/hold uncertainty,
and max/min I/O delays 1/0 ns are retained. No false paths, multicycle exceptions,
precision reduction, case analysis or board deployment are introduced. P&R uses
AltSpreadLogic_high placement and RuntimeOptimized timing-driven routing. Report
both internal register timing and full OOC boundary timing. External partition
pin locations remain undefined, so internal timing alone is not board signoff.
