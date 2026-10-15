param([Parameter(Mandatory)][string]$ConfigPath,[switch]$InspectOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskConfig=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$taskRawMaxMiB=if($null -ne $taskConfig.RawMaxMiB){[int]$taskConfig.RawMaxMiB}else{200}
if($taskRawMaxMiB -lt 1 -or $taskRawMaxMiB -gt 1024){throw 'Configured raw retention is outside the admitted 1-1024 MiB bound.'}
if($taskConfig.ModelName -notin @('qwen3:4b-instruct','qwen3.5:4b') -or $taskConfig.ModelProfile -notin @('native','common')){throw 'Recovery requires an admitted analyst model and explicit generation profile.'}
$taskData=[IO.Path]::GetFullPath($taskConfig.DataDirectory)
$taskAcceleration=if($taskConfig.Acceleration){[string]$taskConfig.Acceleration}else{'cpu'}
if($taskAcceleration -notin @('cpu','vulkan')){throw 'Unknown recovery acceleration.'}
$taskModelPort=if($taskAcceleration -eq 'vulkan'){11436}else{11435}
$taskModelDirectory=if($taskAcceleration -eq 'vulkan'){
    if($taskConfig.GpuRuntimeDirectory){[IO.Path]::GetFullPath($taskConfig.GpuRuntimeDirectory)}else{Join-Path $taskData 'gpu-runtime'}
}else{Join-Path $taskData 'model-runtime'}
if(-not $taskModelDirectory.StartsWith(($taskRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)){throw 'Model receipts must stay within the project.'}
$taskRecovery=Join-Path $taskData 'recovery'
New-Item -ItemType Directory -Path $taskRecovery -Force | Out-Null
$taskLock=$null
try{$taskLock=[IO.File]::Open((Join-Path $taskRecovery 'recovery.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{Write-Output 'Another recovery check owns the lock.';exit 0}
$taskState=[ordered]@{checked_utc=[DateTime]::UtcNow.ToString('o');pid=$PID;status='checking';autostart='Windows user sign-in';receiver='unknown';model='unknown';viewer='unknown';native_login='Authenticated console required; credentials are never stored';inspect_only=[bool]$InspectOnly}
function Find-Owner([string]$Exe,[string]$Script,[object]$Owner,[int]$Port,[switch]$Udp){
    $taskSockets=if($Udp){@(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue)}else{@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)}
    if(-not $taskSockets.Count){return $null}
    $taskIds=@($taskSockets.OwningProcess | Sort-Object -Unique)
    if($taskIds.Count -ne 1 -or -not $Owner -or [int]$Owner.pid -ne $taskIds[0]){throw "Port $Port owner is unrecognized. No conflicting process is stopped."}
    $taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$($taskIds[0])"
    if(-not $taskProcess -or $taskProcess.ExecutablePath -ne $Exe){throw "Port $Port executable differs from the recorded owner."}
    if($Script -and $taskProcess.CommandLine -notlike ('*"'+[IO.Path]::GetFullPath($Script)+'"*')){throw "Port $Port script differs from the recorded owner."}
    if(-not $Script -and $taskProcess.CommandLine -notmatch '\bserve\s*$'){throw "Port $Port is not the recorded model server."}
    $taskExpected=([DateTimeOffset]$Owner.started_utc).UtcDateTime
    if([Math]::Abs(($taskProcess.CreationDate.ToUniversalTime()-$taskExpected).TotalSeconds) -gt 15){throw "Port $Port process creation time differs."}
    return $taskProcess
}
function Read-Owner([string]$Path){if(Test-Path -LiteralPath $Path){Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json}else{$null}}
try{
    if(Test-Path -LiteralPath (Join-Path $taskRecovery 'paused.flag')){$taskState.status='paused';return}
    if(Test-Path -LiteralPath (Join-Path $taskRecovery 'pending-windows-reboot.flag')){
        $taskObservedBoot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
        if($taskObservedBoot -le ([DateTimeOffset]$taskConfig.PreWindowsBootUtc).UtcDateTime){$taskState.status='awaiting authorized Windows reboot';return}
    }
    foreach($taskPath in @($taskConfig.PythonPath,$taskConfig.OllamaPath,$taskConfig.HealthBackup)){if(-not(Test-Path -LiteralPath $taskPath -PathType Leaf)){throw 'Configured executable or backup is missing.'}}
    if(-not(Test-Path -LiteralPath $taskConfig.LogPath -PathType Leaf) -and -not(Test-Path -LiteralPath ($taskConfig.LogPath+'.segments.json') -PathType Leaf)){throw 'Configured original evidence and segmented manifest are missing.'}
    if(-not @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $taskConfig.ClientAddress -ErrorAction SilentlyContinue).Count){throw 'Recorded Vault-facing client address is not present. No address is guessed.'}
    if((Get-FileHash -LiteralPath $taskConfig.HealthBackup).Hash.ToLowerInvariant() -ne $taskConfig.BackupSha256){throw 'Recovery backup differs from configured reference.'}
    $taskReceiverOwner=Read-Owner (Join-Path $taskRecovery 'receiver-owner.json')
    $taskReceiver=Find-Owner -Exe $taskConfig.PythonPath -Script (Join-Path $PSScriptRoot 'soc_receiver.py') -Owner $taskReceiverOwner -Port 5514 -Udp
    $taskHttpOwners=@(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
    if($taskHttpOwners.Count -and (-not $taskReceiver -or @($taskHttpOwners | Where-Object {$_.OwningProcess -ne $taskReceiver.ProcessId -or $_.LocalAddress -ne '127.0.0.1'}).Count)){throw 'Receiver dashboard listener has unexpected ownership/address.'}
    if(-not $taskReceiver){
        if($InspectOnly){$taskState.receiver='would start'}else{
            & (Join-Path $PSScriptRoot 'Start-SocReceiver.ps1') -LanAddress $taskConfig.ClientAddress -VaultAddress $taskConfig.VaultAddress -PythonPath $taskConfig.PythonPath -MaxMiB $taskRawMaxMiB -OwnerPath (Join-Path $taskRecovery 'receiver-owner.json') | Out-Null
            $taskState.receiver='started'
        }
    }else{$taskState.receiver='reused recorded owner'}
    if(-not $InspectOnly){
        $taskReceiverApi=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/events' -TimeoutSec 5
        if($taskReceiverApi.max_bytes -ne ($taskRawMaxMiB * 1MB)){throw 'Active receiver retention differs from recovery configuration. Inspect its recorded owner before maintenance.'}
        $taskRolling=$taskReceiverApi.rolling_retention.mode -eq 'rolling-v2'
        if($taskReceiverApi.retention_full -or $taskReceiverApi.storage_error -or (-not $taskRolling -and $taskReceiverApi.stored_bytes -ge $taskReceiverApi.max_bytes)){throw 'Receiver cannot retain new records. Inspect its storage error and retention status.'}
    }
    $taskModelOwner=Read-Owner (Join-Path $taskModelDirectory 'owner.json')
    if($taskModelOwner -and $taskModelOwner.models -ne (Join-Path $taskData 'model-runtime\models')){throw 'Recorded analyst model store differs.'}
    if($taskAcceleration -eq 'vulkan' -and $taskModelOwner -and $taskModelOwner.endpoint -ne 'http://127.0.0.1:11436'){throw 'GPU runtime endpoint differs.'}
    $taskModel=Find-Owner -Exe $taskConfig.OllamaPath -Script '' -Owner $taskModelOwner -Port $taskModelPort
    if(-not $taskModel){
        if($InspectOnly){$taskState.model='would start isolated runtime'}else{
            if($taskAcceleration -eq 'vulkan'){
                & (Join-Path $PSScriptRoot 'Start-SocGpuProbe.ps1') -OllamaPath $taskConfig.OllamaPath -ModelsDirectory (Join-Path $taskData 'model-runtime\models') -DataDirectory $taskModelDirectory | Out-Null
            }else{
                & (Join-Path $PSScriptRoot 'Start-SocAnalystModel.ps1') -OllamaPath $taskConfig.OllamaPath -DataDirectory $taskModelDirectory | Out-Null
            }
            $taskState.model='started isolated runtime'
        }
    }else{$taskState.model='reused recorded owner'}
    if(-not $InspectOnly){
        $taskModelReady=$false
        for($taskTry=0;$taskTry -lt 6;$taskTry++){
            try{$taskTags=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$taskModelPort+'/api/tags') -TimeoutSec 3;$taskModelReady=$true;break}catch{Start-Sleep -Seconds 1}
        }
        if(-not $taskModelReady){throw 'Isolated analyst runtime did not become ready.'}
        if(-not @($taskTags.models | Where-Object {$_.name -eq $taskConfig.ModelName -and $_.digest -eq $taskConfig.ModelDigest}).Count){throw 'Recorded model/digest is missing. Nothing is downloaded or substituted.'}
    }
    $taskViewerOwner=Read-Owner (Join-Path $taskData 'viewer-owner.json')
    $taskViewer=Find-Owner -Exe $taskConfig.PythonPath -Script (Join-Path $PSScriptRoot 'soc_analyst_server.py') -Owner $taskViewerOwner -Port 8766
    if($taskViewer){
        if($taskViewerOwner.model -ne $taskConfig.ModelName -or $taskViewerOwner.generation_profile -ne $taskConfig.ModelProfile){throw 'Active viewer model/profile differs from recovery configuration. Inspect the recorded owner before restarting.'}
        $taskViewerAcceleration=if($taskViewerOwner.acceleration){$taskViewerOwner.acceleration}else{'cpu'}
        if($taskViewerAcceleration -ne $taskAcceleration){throw 'Viewer acceleration differs from recovery configuration. Inspect the recorded owner before restarting.'}
        $taskWorker=Read-Owner (Join-Path $taskData 'worker-state.json')
        $taskHealth=Read-Owner (Join-Path $taskData 'native-health-state.json')
        if($taskWorker.pid -ne $taskViewer.ProcessId){throw 'Viewer worker ownership is unknown.'}
        if($taskWorker.status -eq 'bounded_monitor_complete' -and $taskHealth.status -ne 'collecting'){
            if($InspectOnly){$taskState.viewer='would renew completed finite batch'}else{& (Join-Path $PSScriptRoot 'Stop-SocAnalyst.ps1') -DataDirectory $taskData | Out-Null;$taskViewer=$null}
        }else{$taskState.viewer='reused active recorded worker'}
    }
    if(-not $taskViewer){
        if($InspectOnly){$taskState.viewer='would start'}else{
            & (Join-Path $PSScriptRoot 'Start-SocAnalyst.ps1') -PythonPath $taskConfig.PythonPath -LogPath $taskConfig.LogPath -ClientAddress $taskConfig.ClientAddress -DataDirectory $taskData -MaxRuns 288 -IntervalSeconds 300 -ModelName $taskConfig.ModelName -ModelProfile $taskConfig.ModelProfile -Acceleration $taskAcceleration -NativeHealth -VaultAddress $taskConfig.VaultAddress -HealthBackup $taskConfig.HealthBackup -SerialPort $taskConfig.SerialPort | Out-Null
            $taskState.viewer='started finite 288-start batch; recovery renews after completion'
        }
    }
    if(-not $InspectOnly){
        $taskViewerReady=$false
        for($taskTry=0;$taskTry -lt 6;$taskTry++){try{[void](Invoke-WebRequest -Uri 'http://127.0.0.1:8766/health' -TimeoutSec 3);$taskViewerReady=$true;break}catch{Start-Sleep -Seconds 1}}
        if(-not $taskViewerReady){throw 'Started viewer did not become ready.'}
    }
    $taskState.status=if($InspectOnly){'inspection_only'}else{'ready'}
    if(-not $InspectOnly -and (Test-Path -LiteralPath (Join-Path $taskRecovery 'pending-windows-reboot.flag'))){
        $taskCurrentBoot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
        if($taskCurrentBoot -gt ([DateTimeOffset]$taskConfig.PreWindowsBootUtc).UtcDateTime){
            & (Join-Path $PSScriptRoot 'Test-SocWindowsRecovery.ps1') -ConfigPath $ConfigPath | Out-Null
            Move-Item -LiteralPath (Join-Path $taskRecovery 'pending-windows-reboot.flag') -Destination (Join-Path $taskRecovery ('windows-reboot-receipt-collected-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.flag'))
        }
    }
}catch{$taskState.status='error';$taskState.reason=$_.Exception.Message}
finally{
    if(-not $InspectOnly -and $taskState.status -notin @('paused','awaiting authorized Windows reboot')){
        try{
            & $taskConfig.PythonPath (Join-Path $PSScriptRoot 'soc_operational_checkpoint.py') --data $taskData --log $taskConfig.LogPath --archives (Join-Path $taskData 'scheduled-archives') | Out-Null
            if($LASTEXITCODE -ne 0){throw 'Operational observation/archive checkpoint failed. Inspect retained state.'}
            $taskState.operational_receipts='bounded 48-hour observation; six-hour private archives within that window'
        }catch{$taskState.operational_error=$_.Exception.Message;$taskState.status='error'}
    }
    $taskState.finished_utc=[DateTime]::UtcNow.ToString('o')
    if(-not $InspectOnly){
        $taskJson=$taskState | ConvertTo-Json -Depth 6
        $taskPending=Join-Path $taskRecovery ('state-'+$PID+'.pending')
        $taskJson | Set-Content -LiteralPath $taskPending -Encoding utf8
        [IO.File]::Move($taskPending,(Join-Path $taskData 'startup-state.json'),$true)
        $taskReceiptDir=Join-Path $taskRecovery 'receipts'
        New-Item -ItemType Directory -Path $taskReceiptDir -Force | Out-Null
        if(@(Get-ChildItem -LiteralPath $taskReceiptDir -File).Count -lt 4096){$taskJson | Set-Content -LiteralPath (Join-Path $taskReceiptDir ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')) -Encoding utf8}
    }
    if($taskLock){$taskLock.Dispose()}
    $taskState | ConvertTo-Json -Depth 6 | Write-Output
}
if($taskState.status -eq 'error'){exit 1}
