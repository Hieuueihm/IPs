iverilog -o sim/work/output.vvp sim/src/tb_aes_wb_slave.v hdl/*.v
vvp sim/work/output.vvp
gtkwave -o tb_aes_wb_slave.vcd
