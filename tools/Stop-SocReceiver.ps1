param([Parameter(Mandatory)][string]$ConfigPath)
$ErrorActionPreference='Stop'
$taskConfig=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$taskOwner=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'recovery\receiver-owner.json') -Raw | ConvertFrom-Json
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$taskOwner.pid)"
if(-not $taskProcess){Write-Output 'Recorded receiver is no longer running.';return}
$taskScript=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'soc_receiver.py'))
if($taskProcess.ExecutablePath -ne $taskOwner.executable -or $taskProcess.ExecutablePath -ne $taskConfig.PythonPath -or $taskProcess.CommandLine -notlike ('*"'+$taskScript+'"*')){throw 'Receiver executable/script ownership differs; nothing stopped.'}
$taskExpected=([DateTimeOffset]$taskOwner.started_utc).UtcDateTime
if([Math]::Abs(($taskProcess.CreationDate.ToUniversalTime()-$taskExpected).TotalSeconds) -gt 15){throw 'Receiver creation time differs; nothing stopped.'}
$taskUdp=@(Get-NetUDPEndpoint -LocalAddress $taskConfig.ClientAddress -LocalPort 5514 -ErrorAction SilentlyContinue)
$taskHttp=@(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
if($taskUdp.Count -ne 1 -or $taskUdp[0].OwningProcess -ne $taskOwner.pid -or $taskHttp.Count -ne 1 -or $taskHttp[0].OwningProcess -ne $taskOwner.pid -or $taskHttp[0].LocalAddress -ne '127.0.0.1'){throw 'Receiver socket ownership differs; nothing stopped.'}
if(-not(Test-Path -LiteralPath (Join-Path $taskConfig.DataDirectory 'recovery\paused.flag'))){throw 'Pause the owned recovery checker before receiver maintenance.'}
Stop-Process -Id $taskOwner.pid
@{pid=$taskOwner.pid;stopped_utc=[DateTime]::UtcNow.ToString('o');verified_owned_script=$taskScript;originals_deleted=$false;receipt_gap_possible=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskConfig.DataDirectory ('receiver-stopped-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')) -Encoding utf8
Write-Output 'Stopped only the verified receiver. UDP receipts during this maintenance interval may be lost; original files remain in place.'
