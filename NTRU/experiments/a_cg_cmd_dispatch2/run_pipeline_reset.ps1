$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir='study/build/a_cg_cmd_dispatch2'
$rtlDir='experiments/a_cg_cmd_dispatch2/rtl'
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_pipeline_reset -o "$buildDir/pipeline_reset.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" experiments/a_cg_cmd_dispatch2/tb_pipeline_reset.sv
if($LASTEXITCODE -ne 0){throw 'Pipeline reset elaboration failed'}
& C:/iverilog/bin/vvp.exe "$buildDir/pipeline_reset.vvp" > "$buildDir/pipeline_reset.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Pipeline reset check failed'}
Get-Content "$buildDir/pipeline_reset.log" -Tail 2
