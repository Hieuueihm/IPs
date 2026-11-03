param([switch]$Synthesize, [switch]$FourState)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
python -X utf8 experiments/a_cg_batch/build.py
if ($LASTEXITCODE -ne 0) { throw 'Fixture/source generation failed' }
& C:/iverilog/bin/iverilog.exe -g2012 -s a_cg_fast -o study/build/a_cg_batch/lint.vvp experiments/a_cg_batch/rtl/mul_ss.v experiments/a_cg_batch/rtl/tile_a.sv experiments/a_cg_batch/rtl/a_cg_fast.sv
if ($LASTEXITCODE -ne 0) { throw 'Icarus elaboration failed' }
& C:/msys64/usr/bin/bash.exe -lc 'export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_fast --Mdir study/build/a_cg_batch/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ experiments/a_cg_batch/rtl/mul_ss.v experiments/a_cg_batch/rtl/tile_a.sv experiments/a_cg_batch/rtl/a_cg_fast.sv D:/IPs/NTRU/experiments/a_cg_batch/main.cpp > study/build/a_cg_batch/verilator_build.log 2>&1'
if ($LASTEXITCODE -ne 0) { throw 'Verilator build failed; see verilator_build.log' }
& study/build/a_cg_batch/obj/Va_cg_fast.exe study/build/a_cg_batch/fixtures.bin > study/build/a_cg_batch/sim.log 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Numeric simulation failed; see sim.log' }
Get-Content study/build/a_cg_batch/sim.log -Tail 4
if ($FourState -or $Synthesize) {
    & C:/iverilog/bin/iverilog.exe -g2012 -s tb_four_state -o study/build/a_cg_batch/four_state.vvp experiments/a_cg_batch/rtl/mul_ss.v experiments/a_cg_batch/rtl/tile_a.sv experiments/a_cg_batch/rtl/a_cg_fast.sv experiments/a_cg_batch/tb_four_state.sv
    if ($LASTEXITCODE -ne 0) { throw 'Four-state testbench compilation failed' }
    & C:/iverilog/bin/vvp.exe study/build/a_cg_batch/four_state.vvp +FIXTURE=study/build/a_cg_batch/four_state.bin > study/build/a_cg_batch/four_state.log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Four-state simulation failed' }
    Get-Content study/build/a_cg_batch/four_state.log -Tail 3
}
if ($Synthesize) {
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/synth.tcl -log study/build/a_cg_batch/vivado.log -journal study/build/a_cg_batch/vivado.jou > study/build/a_cg_batch/vivado_console.log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Vivado synthesis failed; see vivado.log' }
    Get-Content study/build/a_cg_batch/synth/util.rpt -TotalCount 65
}
