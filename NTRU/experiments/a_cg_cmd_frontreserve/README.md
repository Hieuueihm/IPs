# Late-qualified command reservation

Isolated child of a_cg_cmd_frontreset. Routed parent failed frontend permission
to reservation through three LUTs and 5.431 ns routing. Independent request
priority decode has no live/reset/occupancy input. Reservation D applies local
permission and occupancy at the final gate, avoiding the accepted-read OR chain.
All accepted flags, payload, protocol latency and arithmetic remain identical.
Existing occupancy-equals-token-OR assertion checks protocol equivalence.
Synthesis requires exactly one logic level from permission to reservation D.
Full vectors, four-state, reset abort and live C replay gate cold OOC P&R.
Host/root included; 5 ns unchanged; no edits to production or retained baselines.
