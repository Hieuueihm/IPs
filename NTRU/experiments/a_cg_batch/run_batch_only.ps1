param([switch]$Synthesize)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
# Run the full build first to generate fixtures and the static RTL source.
python -X utf8 experiments/a_cg_batch/batch_only.py
if ($LASTEXITCODE -ne 0) { throw 'Batch-only preparation failed' }
& C:/msys64/usr/bin/bash.exe -lc 'export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_fast --Mdir study/build/a_cg_batch/obj_batch_only -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ experiments/a_cg_batch/rtl/mul_ss.v experiments/a_cg_batch/rtl/tile_a.sv experiments/a_cg_batch/rtl/batch_only.sv D:/IPs/NTRU/study/build/a_cg_batch/batch_only_main.cpp > study/build/a_cg_batch/batch_only_build.log 2>&1'
if ($LASTEXITCODE -ne 0) { throw 'Batch-only compile failed' }
& study/build/a_cg_batch/obj_batch_only/Va_cg_fast.exe study/build/a_cg_batch/batch_only.bin > study/build/a_cg_batch/batch_only_sim.log 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Batch-only numeric simulation failed' }
Get-Content study/build/a_cg_batch/batch_only_sim.log -Tail 2
if ($Synthesize) {
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/synth_batch_only.tcl -log study/build/a_cg_batch/batch_only_vivado.log -journal study/build/a_cg_batch/batch_only_vivado.jou > study/build/a_cg_batch/batch_only_console.log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Batch-only synthesis failed' }
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_batch/audit_batch_only.tcl -log study/build/a_cg_batch/batch_only_audit.log -journal study/build/a_cg_batch/batch_only_audit.jou > study/build/a_cg_batch/batch_only_audit_console.log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Batch-only audit failed' }
}
