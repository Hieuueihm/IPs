$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir='study/build/a_cg_z020_perf160'
# compile a snapshot, so the RTL can be edited while a run is in progress
$rtlDir='study/build/a_cg_z020_perf160/rtl_run'
if (Test-Path -LiteralPath $rtlDir) {
    foreach ($file in Get-ChildItem "$PSScriptRoot/rtl" -File) {
        $snapshot = Join-Path $rtlDir $file.Name
        if (!(Test-Path -LiteralPath $snapshot) -or (Get-FileHash -LiteralPath $snapshot).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) { throw 'RTL snapshot differs; use a fresh build directory' }
    }
} else { Copy-Item -Recurse "$PSScriptRoot/rtl" $rtlDir }
New-Item -ItemType Directory -Force $buildDir | Out-Null

& C:/iverilog/bin/iverilog.exe -g2012 -s a_cg_fast -o "$buildDir/lint.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv"
if ($LASTEXITCODE -ne 0) { throw 'Control fork elaboration failed' }
$buildCmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_fast --Mdir '+$buildDir+'/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ '+$rtlDir+'/mul_ss.v '+$rtlDir+'/tile_a.sv '+$rtlDir+'/a_cg_fast.sv D:/IPs/NTRU/experiments/a_cg_z020_perf160/main.cpp > '+$buildDir+'/verilator_build.log 2>&1'
& C:/msys64/usr/bin/bash.exe -lc $buildCmd
if ($LASTEXITCODE -ne 0) { throw 'Control fork build failed' }
python -X utf8 experiments/a_cg_z020_perf160/build_fixtures.py
if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed' }
& "$buildDir/obj/Va_cg_fast.exe" study/build/a_cg_z020_perf160/fixtures.bin > "$buildDir/sim.log" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Control fork numeric simulation failed' }
Get-Content "$buildDir/sim.log" -Tail 3
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_four_state -o "$buildDir/four_state.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" experiments/a_cg_z020_perf160/tb_four_state.sv
if ($LASTEXITCODE -ne 0) { throw 'Control fork four-state compilation failed' }
& C:/iverilog/bin/vvp.exe "$buildDir/four_state.vvp" +FIXTURE=study/build/a_cg_z020_perf160/four_state.bin > "$buildDir/four_state.log" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Control fork four-state validation failed' }
Get-Content "$buildDir/four_state.log" -Tail 2
python -X utf8 experiments/a_cg_z020_perf160/application.py > "$buildDir/application_console.log" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Control fork live C replay failed' }
& ./experiments/a_cg_z020_perf160/run_pipeline_reset.ps1
# tile alone with both modulus slots (the core uses slot 0 only)
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_tile_slots -o "$buildDir/tile_slots.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" experiments/a_cg_z020_perf160/tb_tile_slots.sv
if ($LASTEXITCODE -ne 0) { throw 'Tile slot test compilation failed' }
& C:/iverilog/bin/vvp.exe "$buildDir/tile_slots.vvp" > "$buildDir/tile_slots.log" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'Tile slot test failed' }
Get-Content "$buildDir/tile_slots.log" -Tail 2
Write-Output 'CONTROL_FUNCTIONAL_DONE'
