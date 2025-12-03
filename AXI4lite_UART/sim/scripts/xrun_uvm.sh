#!/bin/bash

RTL_DIR="../../hdl"
INC_DIR="../../inc"
TB_DIR="../src/uvm_tb"


rm -rf xcelium.d INCA* *.log *.key *.simvis* waves* *.shm


inc_sverilog_files=$(find "$INC_DIR" -type f -name "*.sv")
sverilog_files=$(find "$RTL_DIR" -type f -name "*.sv")


UVM_V="UVM_LOW"
UVM_T="tx_fifo_test"

echo "Running simulation with Xcelium:"
xrun -sv -64bit -debug_opts verisium_pp -log xrun.log \
  -access +rwc \
  +define+SVA \
  +incdir+"$TB_DIR" \
  $inc_sverilog_files \
  $sverilog_files \
  "$TB_DIR/common_defines.sv" \
  "$TB_DIR/uart_reg_pkg.sv" \
  "$TB_DIR/apb_agent_pkg.sv" \
  "$TB_DIR/uart_agent_pkg.sv" \
  "$TB_DIR/uart_env_pkg.sv" \
  "$TB_DIR/apb_sequence_pkg.sv" \
  "$TB_DIR/uart_vsequence_pkg.sv" \
  "$TB_DIR/uart_test_pkg.sv" \
  "$TB_DIR/testbench.sv" \
  +UVM_TESTNAME="$UVM_T" \
  +UVM_VERBOSITY="$UVM_V" \
  +tcl+run_batch.tcl