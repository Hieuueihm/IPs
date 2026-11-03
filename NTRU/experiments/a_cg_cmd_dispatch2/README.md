# Two command stages and registered read response

Private child of a_cg_cmd_frontreserve; production and retained baselines unchanged.
All accepted command flags and payloads cross a second unconditional payload
register stage. Two-stage occupancy blocks conflicting main commands until delivery;
root and descriptor streams still accept one word per clock. Read response data
and valid share another stage, flushed on raw or delayed reset. Busy covers both
queued start stages. Arithmetic and kernel schedule are unchanged.

Relative to the parent: command delivery +1 clock, root/descriptor latency +1
clock (throughput unchanged), read response +1 clock. Main host commands have
three-clock spacing instead of two. This is a timing/latency tradeoff.

The external input-to-first-register OOC hold warning is NOT fixed by these stages.
The parent's worst path has zero modelled data delay because boundary routing and
partition-pin positions are absent. Actual host/clock integration is needed to
close that interface; no clock/IO constraints or false paths are changed here.
Full host/root included in synthesis and cold P&R, at the original 5 ns target.
