# Local frontend reset and token decode

Isolated child of a_cg_cmd_credit. Adds one preserved frontend permission FF,
equivalent to the complement of the delayed execution reset. Token D functions
are decoded in a kept hierarchy with no raw reset or execution reset input.
Public ready outputs still mask raw reset, and accepted flag registers retain
synchronous reset. Same command latency, priority, arithmetic and kernel schedule.

Synthesis must prove execution/global reset and raw reset absent from load-token
D fan-in. Functional gate includes frozen vectors, four-state simulation, reset
abort and live C application replay. Full host/root included in OOC synth/P&R.
Production RTL and selected baselines are unchanged. Constraints remain 5 ns.
