# Actual MMCM output clock in the integrated PS7 design; no virtual I/O delays.
set ps7 [get_cells -hier -filter {REF_NAME == PS7}]
if {[llength $ps7] != 1} {error "Real PS7 primitive missing"}
set fclk0_pin [get_pins -of_objects $ps7 -filter {REF_PIN_NAME == "FCLKCLK[0]"}]
if {[llength $fclk0_pin] != 1} {error "PS7 FCLK0 clock pin missing"}
# Also establishes the real root clock when reading a mapped checkpoint whose
# generated 2018.1 PS clock XDC was scoped one wrapper level too high.
if {[llength [get_clocks -quiet clk_fpga_0]] == 0} {
    create_clock -name clk_fpga_0 -period 10.000 $fclk0_pin
    set_input_jitter [get_clocks clk_fpga_0] 0.300
}
if {abs([get_property PERIOD [get_clocks clk_fpga_0]]-10.0)>0.001} {error "FCLK0 is not 100 MHz"}
# The wizard's stand-alone input clock would cut the PS clock tree and use
# 0.1 ns jitter. Propagate the actual PS FCLK (vendor jitter 0.3 ns) instead.
set wizard_root [get_clocks -quiet system_i/clock160/inst/clk_in1]
set wizard_pin [get_pins system_i/clock160/inst/clk_in1]
if {[llength $wizard_pin] != 1} {error "Clock Wizard input pin missing"}
if {[llength $wizard_root] != 0} {set_input_jitter $wizard_root 0.300}
# Vivado 2018.1 replaces a same-name clock without -add. A 1:1 generated
# clock preserves propagation from the physical FCLK source and its jitter.
create_generated_clock -name system_i/clock160/inst/clk_in1 -source $fclk0_pin -divide_by 1 $wizard_pin
set clk160_pin [get_pins -hier -filter {REF_PIN_NAME == CLKOUT0}]
if {[llength $clk160_pin] != 1} {error "Expected exactly one MMCM CLKOUT0"}
set clk160 [get_clocks -of_objects $clk160_pin]
if {[llength $clk160] != 1} {error "160 MHz generated clock missing"}
if {abs([get_property PERIOD $clk160] - 6.25) > 0.001} {error "Integrated clock is not 160 MHz"}
set_clock_uncertainty -setup 0.100 $clk160
set_clock_uncertainty -hold 0.050 $clk160
