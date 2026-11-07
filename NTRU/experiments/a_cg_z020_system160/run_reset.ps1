$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/../..").Path
$out=Join-Path $root 'study/build/a_cg_z020_system160/reset_sim'
New-Item -ItemType Directory -Force $out | Out-Null
Push-Location $out
try {
    & C:/Xilinx/Vivado/2018.1/bin/xvhdl.bat -work lib_cdc_v1_0_2 C:/Xilinx/Vivado/2018.1/data/ip/xilinx/lib_cdc_v1_0/hdl/lib_cdc_v1_0_rfs.vhd > compile_cdc.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Vendor CDC library compile failed'}
    & C:/Xilinx/Vivado/2018.1/bin/xvhdl.bat -work proc_sys_reset_v5_0_12 C:/Xilinx/Vivado/2018.1/data/ip/xilinx/proc_sys_reset_v5_0/hdl/proc_sys_reset_v5_0_vh_rfs.vhd > compile_reset.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Vendor reset library compile failed'}
    $wrapper=Join-Path $root 'study/build/a_cg_z020_system160/project/acg_qiming.srcs/sources_1/bd/system/ip/system_resets_0/sim/system_resets_0.vhd'
    & C:/Xilinx/Vivado/2018.1/bin/xvhdl.bat -work xil_defaultlib $wrapper > compile_vhdl.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Generated reset VHDL compile failed'}
    & C:/Xilinx/Vivado/2018.1/bin/xvlog.bat --sv -work xil_defaultlib "$PSScriptRoot/tb_generated_reset.sv" > compile_sv.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Reset testbench compile failed'}
    & C:/Xilinx/Vivado/2018.1/bin/xvlog.bat -work xil_defaultlib C:/Xilinx/Vivado/2018.1/data/verilog/src/glbl.v > compile_glbl.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Global startup model compile failed'}
    & C:/Xilinx/Vivado/2018.1/bin/xelab.bat xil_defaultlib.tb_generated_reset xil_defaultlib.glbl -L proc_sys_reset_v5_0_12 -L lib_cdc_v1_0_2 -L unisims_ver -debug typical -s reset_tb > elaborate.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Generated reset elaboration failed'}
    & C:/Xilinx/Vivado/2018.1/bin/xsim.bat reset_tb -runall > run.log 2>&1
    if ($LASTEXITCODE -ne 0) {throw 'Reset simulation failed'}
    if (!(Select-String -Quiet -Path run.log -Pattern 'GENERATED_RESET .* PASS')) {throw 'Reset simulation did not pass'}
    Get-Content run.log -Tail 5
} finally {Pop-Location}
