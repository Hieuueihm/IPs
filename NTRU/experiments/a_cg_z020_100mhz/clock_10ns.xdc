# 100 MHz measurement (target since 03/11/2026); otherwise identical to experiments/a_cg_host_opt/clock.xdc.
# Synchronous core-boundary assumptions; not a board timing model.
create_clock -name clk -period 10.000 [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold 0.050 [get_clocks clk]
set_input_delay -clock clk -max 1.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -min 0.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_output_delay -clock clk -max 1.000 [all_outputs]
set_output_delay -clock clk -min 0.000 [all_outputs]
