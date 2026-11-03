"""Use the known-working cold flow after Vivado 2018.1 incremental import crashed."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
s=(ROOT/'experiments/a_cg_cmd_pipe/implement.tcl').read_text()
s=s.replace('a_cg_cmd_pipe','a_cg_cmd_credit')
s=s.replace('variant=local_reset_staged_config','variant=complete_commands_local_occupancy_cold')
(HERE/'implement_cold.tcl').write_text(s)
print('Cold implementation script prepared; new synthesized netlist and unchanged constraints.')
