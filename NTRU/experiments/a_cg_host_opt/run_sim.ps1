param([ValidateSet('direction','fields','prepare','prepare_local','select','prepare_split','select_split')][string]$Variant='prepare', [switch]$FourState)
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir="study/build/a_cg_host_opt/$Variant"
$rtlDir="experiments/a_cg_host_opt/$Variant/rtl"
& C:/iverilog/bin/iverilog.exe -g2012 -s a_cg_fast -o "$buildDir/lint.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv"
if ($LASTEXITCODE -ne 0) { throw "Elaboration failed: $Variant" }
$buildCmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_fast --Mdir '+$buildDir+'/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ '+$rtlDir+'/mul_ss.v '+$rtlDir+'/tile_a.sv '+$rtlDir+'/a_cg_fast.sv D:/IPs/NTRU/experiments/a_cg_host_opt/main.cpp > '+$buildDir+'/verilator_build.log 2>&1'
& C:/msys64/usr/bin/bash.exe -lc $buildCmd
if ($LASTEXITCODE -ne 0) { throw "Build failed: $Variant" }
& "$buildDir/obj/Va_cg_fast.exe" study/build/a_cg_batch/fixtures.bin > "$buildDir/sim.log" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Numeric simulation failed: $Variant" }
Get-Content "$buildDir/sim.log" -Tail 2
if ($FourState) {
    & C:/iverilog/bin/iverilog.exe -g2012 -s tb_four_state -o "$buildDir/four_state.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" experiments/a_cg_host_opt/tb_four_state.sv
    if ($LASTEXITCODE -ne 0) { throw 'Four-state compilation failed' }
    & C:/iverilog/bin/vvp.exe "$buildDir/four_state.vvp" +FIXTURE=study/build/a_cg_batch/four_state.bin > "$buildDir/four_state.log" 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Four-state validation failed' }
    Get-Content "$buildDir/four_state.log" -Tail 2
}
