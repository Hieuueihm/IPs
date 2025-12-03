#!/bin/bash

RTL_DIR="../../hdl"
INC_DIR="../../inc"
TB_DIR="../src/uvm_tb"

vlib work

inc_sverilog_files=$(find "$INC_DIR" -type f -name "*.sv")
sverilog_files=$(find "$RTL_DIR" -type f -name "*.sv")

echo "Compiling RTL and include files:"
echo "$inc_sverilog_files"
echo "$sverilog_files"
echo
vlog -sv +define+SVA $inc_sverilog_files
vlog -sv +define+SVA $sverilog_files



echo "-> Compiling supporting testbench files"
vlog -sv +define+SVA +incdir+"$TB_DIR" \
  "$TB_DIR/common_defines.sv" \
  "$TB_DIR/uart_reg_pkg.sv" \
  "$TB_DIR/apb_agent_pkg.sv" \
  "$TB_DIR/uart_agent_pkg.sv" \
  "$TB_DIR/uart_env_pkg.sv" \
  "$TB_DIR/apb_sequence_pkg.sv" \
  "$TB_DIR/uart_vsequence_pkg.sv" \
  "$TB_DIR/uart_test_pkg.sv" \
  "$TB_DIR/testbench.sv" \

  # "$TB_DIR/apb_assertion.sv" \
  # "$TB_DIR/apb_uart_tb.sv"



# echo
UVM_V="UVM_LOW"
UVM_T="tx_fifo_test"

echo "Running simulation:"
vsim -voptargs=+acc -c -sv_seed random work.testbench \
  -uvmcontrol=all \
  +UVM_TESTNAME=$UVM_T\
  +UVM_VERBOSITY=$UVM_V \
  -do "run -all; quit"