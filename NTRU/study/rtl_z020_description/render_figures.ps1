$ErrorActionPreference='Stop'
$workspaceRoot=(Resolve-Path "$PSScriptRoot/../..").Path
$figRoot=Join-Path $workspaceRoot 'docs/figures/rtl_z020'
$scratchRoot=Join-Path $workspaceRoot 'study/build/rtl_z020_description'
$edgePath='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
$inventory=Get-Content -Raw (Join-Path $figRoot 'inventory.json') | ConvertFrom-Json
foreach($item in $inventory){
    $svgPath=Join-Path $figRoot ($item.name+'.svg')
    $pngPath=Join-Path $figRoot ($item.name+'.png')
    $profilePath=Join-Path $scratchRoot ('render_'+$item.name)
    $localUrl=([uri]$svgPath).AbsoluteUri
    $arguments=@('--headless','--disable-gpu','--hide-scrollbars','--no-first-run','--disable-background-networking',
        '--force-device-scale-factor=1',"--user-data-dir=$profilePath","--screenshot=$pngPath",
        "--window-size=$($item.width),$($item.height)",$localUrl)
    $renderProcess=Start-Process -FilePath $edgePath -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(-not $renderProcess.WaitForExit(20000)){
        Stop-Process -Id $renderProcess.Id -Force
        throw "Headless renderer timeout for $($item.name)"
    }
    if(-not (Test-Path -LiteralPath $pngPath)){throw "Missing rendered image: $pngPath"}
    Write-Output "RENDERED $($item.name)"
}
