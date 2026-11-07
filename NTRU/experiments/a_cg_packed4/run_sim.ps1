$ErrorActionPreference='Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
$buildDir='study/build/a_cg_packed4'
New-Item -ItemType Directory -Force $buildDir | Out-Null
python -X utf8 "$PSScriptRoot/build_fixtures.py" > "$buildDir/fixtures_build.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Candidate physical-schedule fixtures failed'}
$rtlDir='experiments/a_cg_packed4/rtl'
$cmd='export PATH=/ucrt64/bin:/usr/bin:$PATH; cd /d/IPs/NTRU; verilator --cc --exe --build -j 2 -O1 -Wno-fatal --top-module a_cg_axil --Mdir '+$buildDir+'/obj -CFLAGS -D_GLIBCXX_USE_CXX11_ABI=0 -LDFLAGS -static-libgcc -LDFLAGS -static-libstdc++ '+$rtlDir+'/mul_ss.v '+$rtlDir+'/tile_a.sv '+$rtlDir+'/a_cg_fast.sv '+$rtlDir+'/a_cg_axil.v D:/IPs/NTRU/experiments/a_cg_packed4/main.cpp > '+$buildDir+'/verilator_build.log 2>&1'
& C:/msys64/usr/bin/bash.exe -lc $cmd
if($LASTEXITCODE -ne 0){throw 'Candidate Verilator build failed'}
& "$buildDir/obj/Va_cg_axil.exe" "$buildDir/fixtures.bin" > "$buildDir/sim.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Candidate AXI numerical simulation failed'}
Get-Content "$buildDir/sim.log" -Tail 3
python -X utf8 "$PSScriptRoot/application.py" > "$buildDir/application_console.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Candidate live C replay failed'}
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_packed4 -o "$buildDir/tile_shared.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$PSScriptRoot/tb_packed4.sv"
if($LASTEXITCODE -ne 0){throw 'Packed tile compile failed'}
& C:/iverilog/bin/vvp.exe "$buildDir/tile_shared.vvp" > "$buildDir/tile_shared.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Packed tile test failed'}
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_four_state -o "$buildDir/four_state_shared.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" experiments/a_cg_z020_perf160/tb_four_state.sv
if($LASTEXITCODE -ne 0){throw 'Four-state compile failed'}
& C:/iverilog/bin/vvp.exe "$buildDir/four_state_shared.vvp" "+FIXTURE=$buildDir/four_state_packed.bin" > "$buildDir/four_state.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'Four-state test failed'}
& C:/iverilog/bin/iverilog.exe -g2012 -s tb_acg_axil_reset -o "$buildDir/axil_reset.vvp" "$rtlDir/mul_ss.v" "$rtlDir/tile_a.sv" "$rtlDir/a_cg_fast.sv" "$rtlDir/a_cg_axil.v" experiments/a_cg_z020_system160/tb_axil_reset.sv
if($LASTEXITCODE -ne 0){throw 'AXI reset compile failed'}
& C:/iverilog/bin/vvp.exe "$buildDir/axil_reset.vvp" > "$buildDir/axil_reset.log" 2>&1
if($LASTEXITCODE -ne 0){throw 'AXI reset test failed'}
python -X utf8 scripts/check_baseline.py
if($LASTEXITCODE -ne 0){throw 'Accepted baseline changed'}
