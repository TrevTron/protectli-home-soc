param([ValidateSet('transfer-ling-long-02')][string]$RunName='transfer-ling-long-02')
$ErrorActionPreference='Stop'
$taskRoot='C:\REDACTED_PROJECT'
$taskWork=Join-Path $taskRoot 'private\ai-followup-20261007\model-skills-v5'
$taskOutput=Join-Path $taskWork $RunName
$taskConfigPath=Join-Path $taskRoot 'private\analyst\recovery\config.json'
$taskConfig=Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json
$taskPause=Join-Path $taskConfig.DataDirectory 'recovery\paused.flag'
if(Test-Path -LiteralPath $taskPause){throw 'Another maintenance boundary is active.'}
$taskCpu=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'model-runtime\owner.json') -Raw | ConvertFrom-Json
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$taskCpu.pid)"
$taskSocket=@(Get-NetTCPConnection -LocalPort 11435 -State Listen -ErrorAction SilentlyContinue)
if(-not $taskProcess -or $taskProcess.ExecutablePath -ne $taskCpu.executable -or $taskSocket.Count -ne 1 -or $taskSocket[0].OwningProcess -ne $taskCpu.pid -or $taskSocket[0].LocalAddress -ne '127.0.0.1'){throw 'CPU ownership or loopback listener changed.'}
$taskExpected=([DateTimeOffset]$taskCpu.started_utc).UtcDateTime
if([Math]::Abs(($taskProcess.CreationDate.ToUniversalTime()-$taskExpected).TotalSeconds) -gt 15){throw 'CPU creation time differs.'}
if(-not $taskCpu.cloud_disabled -or $taskCpu.endpoint -ne 'http://127.0.0.1:11435'){throw 'Expected isolated runtime required.'}
$taskVersion=Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/version' -TimeoutSec 5
$taskCpuState=Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/ps' -TimeoutSec 5
$taskGpuState=Invoke-RestMethod -Uri 'http://127.0.0.1:11436/api/ps' -TimeoutSec 5
if($taskCpuState.models.Count){throw 'Existing CPU work takes priority.'}
$taskDeadline=[DateTime]::UtcNow.AddSeconds(60)
do{
    $taskWorker=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'worker-state.json') -Raw | ConvertFrom-Json
    $taskSampler=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'native-health-state.json') -Raw | ConvertFrom-Json
    if($taskWorker.status -ne 'analyzing' -and $taskSampler.status -ne 'collecting'){break}
    Start-Sleep -Seconds 1
}while([DateTime]::UtcNow -lt $taskDeadline)
if($taskWorker.status -eq 'analyzing' -or $taskSampler.status -eq 'collecting'){throw 'Bounded work still active.'}
$taskRecoveryLock=[IO.File]::Open((Join-Path $taskConfig.DataDirectory 'recovery\recovery.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
@{utc=[DateTime]::UtcNow.ToString('o');cpu_pid=$taskCpu.pid;ownership_verified=$true;version=$taskVersion;worker=$taskWorker;native=$taskSampler;user_authorization='2026-10-07: do not ask permission, launch step by step with each';protected_11434_invoked=$false;collector_stopped=$false} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $taskOutput 'launch-preflight.json') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $taskConfig.DataDirectory 'viewer-owner.json') -Destination (Join-Path $taskOutput 'viewer-owner-before.json')
$taskReceiverPath=Join-Path $taskRoot 'private\logs\receiver-owner.json'
if(Test-Path -LiteralPath $taskReceiverPath){Copy-Item -LiteralPath $taskReceiverPath -Destination (Join-Path $taskOutput 'receiver-owner-before.json')}
[IO.File]::WriteAllText($taskPause,'Authorized model-skills-v2 development.')
$taskChanged=$false
$taskExit=1
try{
    & (Join-Path $taskRoot 'tools\Stop-SocAnalyst.ps1') -DataDirectory $taskConfig.DataDirectory
    $taskChanged=$true
    & (Join-Path $taskRoot 'tools\Start-SocAnalyst.ps1') -PythonPath $taskConfig.PythonPath -LogPath $taskConfig.LogPath -ClientAddress $taskConfig.ClientAddress -DataDirectory $taskConfig.DataDirectory -ViewOnly -MaxRuns 288 -IntervalSeconds 300 -ModelName $taskConfig.ModelName -ModelProfile $taskConfig.ModelProfile -Acceleration vulkan -NativeHealth -VaultAddress $taskConfig.VaultAddress -HealthBackup $taskConfig.HealthBackup -SerialPort $taskConfig.SerialPort
    $taskOwnSnapshot=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'viewer-owner.json') -Raw | ConvertFrom-Json
    Copy-Item -LiteralPath (Join-Path $taskConfig.DataDirectory 'viewer-owner.json') -Destination (Join-Path $taskOutput 'owned-snapshot-viewer.json')
    & $taskConfig.PythonPath -B -u (Join-Path $taskWork 'run_ling_continuation.py') $RunName 2>&1 | Tee-Object -FilePath (Join-Path $taskOutput 'console.log')
    $taskExit=$LASTEXITCODE
}finally{
    if($taskChanged){
        $taskDeadline=[DateTime]::UtcNow.AddSeconds(60)
        do{
            $taskSampler=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'native-health-state.json') -Raw | ConvertFrom-Json
            if($taskSampler.status -ne 'collecting'){break}
            Start-Sleep -Seconds 1
        }while([DateTime]::UtcNow -lt $taskDeadline)
        $taskEndingOwner=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'viewer-owner.json') -Raw | ConvertFrom-Json
        if($taskEndingOwner.pid -ne $taskOwnSnapshot.pid){throw 'Recorded snapshot owner changed; stop no conflicting process.'}
        & (Join-Path $taskRoot 'tools\Stop-SocAnalyst.ps1') -DataDirectory $taskConfig.DataDirectory
    }
    Move-Item -LiteralPath $taskPause -Destination (Join-Path $taskOutput ('completed-maintenance-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.flag'))
    $taskRecoveryLock.Dispose()
    & (Join-Path $taskRoot 'tools\Restore-SocAfterLogin.ps1') -ConfigPath $taskConfigPath
    Copy-Item -LiteralPath (Join-Path $taskConfig.DataDirectory 'startup-state.json') -Destination (Join-Path $taskOutput 'recovery-after.json')
    @{utc=[DateTime]::UtcNow.ToString('o');exit_code=$taskExit;receiver_stopped=$false;protected_11434_invoked=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'execution-exit.json') -Encoding utf8
}
if($taskExit -ne 0){throw 'Development stopped with receipts retained; recovery restoration attempted.'}
