param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [Parameter(Mandatory)][string]$ReceiptDirectory
)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$taskConfig=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$taskData=[IO.Path]::GetFullPath($taskConfig.DataDirectory)
$taskLog=[IO.Path]::GetFullPath($taskConfig.LogPath)
$taskReceipt=[IO.Path]::GetFullPath($ReceiptDirectory)
foreach($taskTarget in @($taskData,$taskLog,$taskReceipt)){
    if(-not $taskTarget.StartsWith(($taskRoot+'\private\'),[StringComparison]::OrdinalIgnoreCase)){throw 'Migration paths must stay in this project private tree.'}
}
if(Test-Path -LiteralPath $taskReceipt){throw 'Use a new receipt directory. Earlier evidence is preserved.'}
if(-not(Test-Path -LiteralPath (Join-Path $taskData 'recovery\paused.flag'))){throw 'Pause recovery before migration.'}
$taskOwner=Get-Content -LiteralPath (Join-Path $taskData 'recovery\receiver-owner.json') -Raw | ConvertFrom-Json
if(Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$taskOwner.pid)"){throw 'Recorded receiver is still running. Use its ownership-checked stop helper first.'}
if(@(Get-NetUDPEndpoint -LocalPort 5514 -ErrorAction SilentlyContinue).Count -or @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue).Count){throw 'Collector sockets remain occupied. No conflicting process is changed.'}
New-Item -ItemType Directory -Path $taskReceipt | Out-Null
Copy-Item -LiteralPath (Join-Path $taskData 'recovery\receiver-owner.json') -Destination (Join-Path $taskReceipt 'stopped-receiver-owner.json')
Copy-Item -LiteralPath ($taskLog+'.segments.json') -Destination (Join-Path $taskReceipt 'original-segments.json')
@{started_utc=[DateTime]::UtcNow.ToString('o');receiver_pid=$taskOwner.pid;receiver_absent=$true;collector_sockets_absent=$true;recovery_paused=$true;log=$taskLog;receipt=$taskReceipt} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskReceipt 'maintenance-preflight.json') -Encoding utf8
& $taskConfig.PythonPath (Join-Path $PSScriptRoot 'soc_retention_activate.py') --log $taskLog --receipt $taskReceipt
if($LASTEXITCODE -ne 0){throw 'Migration failed. Retain receipts and inspect before recovery; no originals are overwritten by this helper.'}
Write-Output 'Rolling manifest activated after a verified, immutable one-time baseline. Restart the recorded receiver and verify fresh Vault receipts.'
