param([Parameter(Mandatory=$true)][string]$Variant,[ValidateSet('sim','synth','pnr')][string]$Stage='sim')
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir="study/build/paper_ablation31/$Variant"
$rtlDir="experiments/paper_ablation31/variants/$Variant/rtl"
New-Item -ItemType Directory -Force $buildDir | Out-Null
if($Stage -eq 'synth') {
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log "$buildDir/synth.log" -source "$PSScriptRoot/synth.tcl" -tclargs $Variant > "$buildDir/synth_console.log" 2>&1
    if($LASTEXITCODE -ne 0){throw 'Ablation synthesis failed'}
} elseif($Stage -eq 'pnr') {
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log "$buildDir/create.log" -source "$PSScriptRoot/variants/$Variant/create_project.tcl" -tclargs synth > "$buildDir/create_console.log" 2>&1
    if($LASTEXITCODE -ne 0){throw 'Ablation system synthesis failed'}
    & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log "$buildDir/implement.log" -source "$PSScriptRoot/variants/$Variant/implement.tcl" > "$buildDir/implement_console.log" 2>&1
    if($LASTEXITCODE -ne 0){throw 'Ablation P&R failed'}
} else {
    python -X utf8 "$PSScriptRoot/fixtures.py" $Variant > "$buildDir/fixtures_build.log" 2>&1
    if($LASTEXITCODE -ne 0){throw 'Ablation fixture/model replay failed'}
    $cmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_axil --Mdir '+$buildDir+'/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ '+$rtlDir+'/mul_ss.v '+$rtlDir+'/tile_a.sv '+$rtlDir+'/a_cg_fast.sv '+$rtlDir+'/a_cg_axil.v D:/IPs/NTRU/experiments/a_cg_packed4/main.cpp > '+$buildDir+'/verilator_build.log 2>&1'
    & C:/msys64/usr/bin/bash.exe -lc $cmd
    if($LASTEXITCODE -ne 0){throw 'Ablation Verilator build failed'}
    & "$buildDir/obj/Va_cg_axil.exe" "$buildDir/fixtures.bin" > "$buildDir/sim.log" 2>&1
    if($LASTEXITCODE -ne 0){throw 'Ablation numeric simulation failed'}
    Get-Content "$buildDir/sim.log" -Tail 2
}
Write-Output "ABLATION_DONE variant=$Variant stage=$Stage"
