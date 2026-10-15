param([string]$DataDirectory=(Join-Path $PSScriptRoot '..\private\analyst'))
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath($DataDirectory)
$taskOwner=Get-Content -LiteralPath (Join-Path $taskRoot 'viewer-owner.json') -Raw | ConvertFrom-Json
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$taskOwner.pid)"
if (-not $taskProcess) {Write-Output 'Recorded analyst viewer is no longer running.';return}
$taskScript=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'soc_analyst_server.py'))
if ($taskProcess.ExecutablePath -ne $taskOwner.executable -or $taskProcess.CommandLine -notlike ('*"'+$taskScript+'"*')) {throw 'Recorded PID does not match the owned analyst script; nothing stopped.'}
$taskExpected=([DateTimeOffset]$taskOwner.started_utc).UtcDateTime
if ([Math]::Abs(($taskProcess.CreationDate.ToUniversalTime()-$taskExpected).TotalSeconds) -gt 15) {throw 'Recorded process creation time differs; nothing stopped.'}
if (Test-Path -LiteralPath (Join-Path $taskRoot 'worker-state.json')) {
    $taskWorker=Get-Content -LiteralPath (Join-Path $taskRoot 'worker-state.json') -Raw | ConvertFrom-Json
    if ($taskWorker.pid -eq $taskOwner.pid -and $taskWorker.status -eq 'analyzing') {throw 'An analyst request is active. Wait for its bounded request to finish before stopping the viewer.'}
}
if (Test-Path -LiteralPath (Join-Path $taskRoot 'native-health-state.json')) {
    $taskHealthWorker=Get-Content -LiteralPath (Join-Path $taskRoot 'native-health-state.json') -Raw | ConvertFrom-Json
    if ($taskHealthWorker.pid -eq $taskOwner.pid -and $taskHealthWorker.status -eq 'collecting') {throw 'A bounded native health collection is active. Wait for it to finish before stopping the viewer.'}
}
Stop-Process -Id $taskOwner.pid
[pscustomobject]@{pid=$taskOwner.pid;stopped_utc=[DateTime]::UtcNow.ToString('o');verified_owned_script=$taskScript} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot ('viewer-stopped-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')) -Encoding utf8
Write-Output 'Stopped only the verified local analyst viewer. Sensor logging and model runtimes remain separate.'
