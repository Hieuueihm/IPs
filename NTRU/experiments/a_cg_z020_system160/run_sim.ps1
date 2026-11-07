$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir='study/build/a_cg_z020_system160'
$rtlDir="$buildDir/rtl_run"
if (Test-Path -LiteralPath $rtlDir) { throw 'Preserve existing snapshot; use a fresh build directory' }
Copy-Item -Recurse "$PSScriptRoot/rtl" $rtlDir
$cmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_axil --Mdir '+$buildDir+'/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ '+$rtlDir+'/mul_ss.v '+$rtlDir+'/tile_a.sv '+$rtlDir+'/a_cg_fast.sv '+$rtlDir+'/a_cg_axil.v D:/IPs/NTRU/experiments/a_cg_z020_system160/main.cpp > '+$buildDir+'/verilator_build.log 2>&1'
& C:/msys64/usr/bin/bash.exe -lc $cmd
if ($LASTEXITCODE -ne 0) {throw 'AXI simulation build failed'}
& "$buildDir/obj/Va_cg_axil.exe" study/build/a_cg_z020_perf160/fixtures.bin > "$buildDir/sim.log" 2>&1
if ($LASTEXITCODE -ne 0) {throw 'AXI numeric simulation failed'}
Get-Content "$buildDir/sim.log" -Tail 3
python -X utf8 experiments/a_cg_z020_system160/application.py > "$buildDir/application_console.log" 2>&1
if ($LASTEXITCODE -ne 0) {throw 'AXI C application replay failed'}
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_acg_axil_reset -o "$buildDir/axil_reset.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" "$rtlDir/a_cg_axil.v" "$PSScriptRoot/tb_axil_reset.sv"
if ($LASTEXITCODE -ne 0) {throw 'AXI reset bench compile failed'}
& C:/iverilog/bin/vvp.exe "$buildDir/axil_reset.vvp" > "$buildDir/axil_reset.log" 2>&1
if ($LASTEXITCODE -ne 0) {throw 'AXI reset bench failed'}
& "$PSScriptRoot/run_reset.ps1" > "$buildDir/reset_console.log" 2>&1
python -X utf8 experiments/a_cg_z020_system160/validate.py
if ($LASTEXITCODE -ne 0) {throw 'Integrated functional gate failed'}
Write-Output 'AXI_FUNCTIONAL_DONE'
