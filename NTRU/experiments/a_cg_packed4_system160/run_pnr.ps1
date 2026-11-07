$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir='study/build/a_cg_packed4_system160'
python -X utf8 scripts/check_baseline.py
if($LASTEXITCODE -ne 0){throw 'Accepted baseline verification failed'}
if(!(Test-Path -LiteralPath "$PSScriptRoot/rtl")) {
    python -X utf8 "$PSScriptRoot/prepare.py"
    if($LASTEXITCODE -ne 0){throw 'Candidate snapshot preparation failed'}
}
& C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log "$buildDir/create.log" -source "$PSScriptRoot/create_project.tcl" -tclargs synth > "$buildDir/create_console.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Private system project/synthesis failed'}
if(!(Test-Path -LiteralPath "$buildDir/system_synth.dcp")){throw 'System synthesis checkpoint missing'}
& C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -nojournal -log "$buildDir/implement.log" -source "$PSScriptRoot/implement.tcl" > "$buildDir/implement_console.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Private full-system implementation failed'}
python -X utf8 "$PSScriptRoot/report.py"
if($LASTEXITCODE -ne 0){throw 'Private P&R evidence audit failed'}
python -X utf8 scripts/check_baseline.py
if($LASTEXITCODE -ne 0){throw 'Accepted baseline evidence changed'}
Write-Output 'PACKED4_SYSTEM_PNR_COMPLETE'
