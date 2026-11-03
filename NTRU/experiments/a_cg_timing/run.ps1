param([switch]$Synthesize)
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
python -X utf8 experiments/a_cg_timing/build.py
if ($LASTEXITCODE -ne 0) { throw 'Generation/hash checks failed' }
python -X utf8 experiments/a_cg_timing/check_addsub.py
if ($LASTEXITCODE -ne 0) { throw 'Adder equivalence failed' }
foreach ($variant in @('host','local','raw','all')) {
    $argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File','experiments/a_cg_timing/run_sim.ps1','-Variant',$variant)
    if ($variant -in @('host','all')) { $argsList+='-FourState' }
    & powershell @argsList
    if ($LASTEXITCODE -ne 0) { throw "Validation failed: $variant" }
}
python -X utf8 experiments/a_cg_timing/application.py
if ($LASTEXITCODE -ne 0) { throw 'Combined application replay failed' }
python -X utf8 experiments/a_cg_timing/application_host.py
if ($LASTEXITCODE -ne 0) { throw 'Host application replay failed' }
if ($Synthesize) {
    foreach ($variant in @('base','host','local','raw','all')) {
        & C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_timing/synth.tcl -log "study/build/a_cg_timing/$variant/vivado.log" -journal "study/build/a_cg_timing/$variant/vivado.jou" -tclargs $variant
        if ($LASTEXITCODE -ne 0) { throw "Synthesis failed: $variant" }
    }
    python -X utf8 experiments/a_cg_timing/report.py
    if ($LASTEXITCODE -ne 0) { throw 'Report verification failed' }
}
