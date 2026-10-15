param(
    [Parameter(Mandatory)][string]$PythonPath,
    [Parameter(Mandatory)][string]$LogPath,
    [Parameter(Mandatory)][string]$ClientAddress,
    [string]$DataDirectory = (Join-Path $PSScriptRoot '..\private\analyst'),
    [ValidateRange(1,288)][int]$MaxRuns=12,
    [ValidateRange(30,86400)][int]$IntervalSeconds=300,
    [switch]$ViewOnly,
    [ValidateSet('qwen3:4b-instruct','qwen3.5:4b')][string]$ModelName='qwen3.5:4b',
    [ValidateSet('native','common')][string]$ModelProfile='common',
    [ValidateSet('cpu','vulkan')][string]$Acceleration='cpu',
    [switch]$NativeHealth,
    [string]$VaultAddress,
    [string]$HealthBackup,
    [ValidatePattern('^COM[1-9][0-9]?$')][string]$SerialPort='COM3'
)
$ErrorActionPreference='Stop'
if (Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8766 is occupied. Check its owner before restarting the analyst.' }
[void][Net.IPAddress]::Parse($ClientAddress)
$taskData=[IO.Path]::GetFullPath($DataDirectory)
$taskLog=[IO.Path]::GetFullPath($LogPath)
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {throw 'Python executable missing.'}
if (-not (Test-Path -LiteralPath $taskLog -PathType Leaf) -and -not (Test-Path -LiteralPath ($taskLog+'.segments.json') -PathType Leaf)) {throw 'Original evidence and segmented manifest missing.'}
New-Item -ItemType Directory -Path $taskData -Force | Out-Null
$taskArgs=@(('"'+(Join-Path $PSScriptRoot 'soc_analyst_server.py')+'"'),'--log',('"'+$taskLog+'"'),'--client',$ClientAddress,'--data',('"'+$taskData+'"'),'--max-runs',$MaxRuns,'--interval',$IntervalSeconds)
if($ViewOnly){$taskArgs+='--view-only'}
$taskArgs+=@('--model',$ModelName,'--generation-profile',$ModelProfile)
$taskArgs+=@('--acceleration',$Acceleration)
if($Acceleration -eq 'vulkan'){$taskArgs+=@('--endpoint','http://127.0.0.1:11436')}
if($NativeHealth){
    [void][Net.IPAddress]::Parse($VaultAddress)
    $taskPowerShell=Join-Path $PSHOME 'pwsh.exe'
    if(-not (Test-Path -LiteralPath $taskPowerShell -PathType Leaf)){throw 'Native health requires PowerShell 7 on Windows.'}
    $taskArgs+=@('--native-health','--vault-address',$VaultAddress,'--serial-port',$SerialPort,'--powershell',('"'+$taskPowerShell+'"'))
    if($HealthBackup){$taskArgs+=@('--health-backup',('"'+[IO.Path]::GetFullPath($HealthBackup)+'"'))}
}
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$taskStdout=Join-Path $taskData ("viewer-$taskStamp.stdout.log")
$taskStderr=Join-Path $taskData ("viewer-$taskStamp.stderr.log")
$taskProcess=Start-Process -FilePath $PythonPath -ArgumentList $taskArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr
try{$taskProcess.PriorityClass='BelowNormal'}catch{}
$taskOwner=[pscustomobject]@{pid=$taskProcess.Id;started_utc=[DateTime]::UtcNow.ToString('o');url='http://127.0.0.1:8766/';view_only=[bool]$ViewOnly;native_health=[bool]$NativeHealth;max_runs=$MaxRuns;interval_seconds=$IntervalSeconds;executable=$PythonPath;script=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'soc_analyst_server.py'));stdout=$taskStdout;stderr=$taskStderr}
$taskOwner | Add-Member -NotePropertyName model -NotePropertyValue $ModelName
$taskOwner | Add-Member -NotePropertyName generation_profile -NotePropertyValue $ModelProfile
$taskOwner | Add-Member -NotePropertyName acceleration -NotePropertyValue $Acceleration
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData "viewer-owner-$taskStamp.json") -Encoding utf8
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData 'viewer-owner.json') -Encoding utf8
Write-Output "Analyst viewer started as PID $($taskProcess.Id) at http://127.0.0.1:8766/. View-only: $ViewOnly. This is an explicit launcher, not autostart."
