# Identical estimate constraints for baseline and every experimental variant.
# Synchronous core-boundary assumptions; not a board timing model.
create_clock -name clk -period 5.000 [get_ports clk]
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold 0.050 [get_clocks clk]
set_input_delay -clock clk -max 1.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -min 0.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_output_delay -clock clk -max 1.000 [all_outputs]
set_output_delay -clock clk -min 0.000 [all_outputs]
