create_clock -name clk -period 6.250 [get_ports aclk]
set_input_jitter [get_clocks clk] 0.300
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold 0.050 [get_clocks clk]
