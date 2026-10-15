$ErrorActionPreference='Stop'
$taskRoot='C:\REDACTED_PROJECT'
$taskData=Join-Path $taskRoot 'private\analyst'
$taskOutput=Join-Path $taskRoot 'private\ai-followup-20261007\model-skills-v2\development-01'
$taskPause=Join-Path $taskData 'recovery\paused.flag'
if((Get-Content -LiteralPath $taskPause -Raw) -ne 'Owned viewer reconciliation after development-01.'){throw 'Unexpected maintenance owner'}
$taskLock=[IO.File]::Open((Join-Path $taskData 'recovery\recovery.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try{
    $taskOwn=Get-Content -LiteralPath (Join-Path $taskData 'viewer-owner-20261007T2059414239619Z.json') -Raw | ConvertFrom-Json
    $taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$taskOwn.pid)"
    $taskSocket=@(Get-NetTCPConnection -LocalPort 8766 -State Listen)
    if(-not $taskOwn.view_only -or $taskOwn.pid -ne 54296 -or -not $taskProcess -or $taskProcess.ExecutablePath -ne $taskOwn.executable -or $taskProcess.CommandLine -notlike ('*"'+$taskOwn.script+'"*') -or $taskProcess.CommandLine -notlike '*--view-only*' -or [Math]::Abs(($taskProcess.CreationDate.ToUniversalTime()-([DateTimeOffset]$taskOwn.started_utc).UtcDateTime).TotalSeconds) -gt 15 -or $taskSocket.Count -ne 1 -or $taskSocket[0].OwningProcess -ne 54296){throw 'Owned snapshot verification failed'}
    if(@(Get-CimInstance Win32_Process -Filter 'ParentProcessId=54296' | Where-Object {$_.Name -ne 'conhost.exe'}).Count){throw 'Bounded work still active'}
    Copy-Item -LiteralPath (Join-Path $taskData 'viewer-owner.json') -Destination (Join-Path $taskOutput 'reconciliation-recorded-owner-before.json')
    @{utc=[DateTime]::UtcNow.ToString('o');verified_own_snapshot_pid=54296;owner=$taskOwn;socket_pid=54296;non_console_children=0;recovery_lock_held=$true} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskOutput 'reconciliation-preflight.json') -Encoding utf8
    Stop-Process -Id 54296
    Move-Item -LiteralPath $taskPause -Destination (Join-Path $taskOutput 'completed-reconciliation.flag')
}finally{$taskLock.Dispose()}
& (Join-Path $taskRoot 'tools\Restore-SocAfterLogin.ps1') -ConfigPath (Join-Path $taskData 'recovery\config.json')
Copy-Item -LiteralPath (Join-Path $taskData 'startup-state.json') -Destination (Join-Path $taskOutput 'recovery-reconciled.json')
Get-NetTCPConnection -LocalPort 8766 -State Listen | Select-Object LocalAddress,OwningProcess
