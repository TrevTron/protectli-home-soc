param([Parameter(Mandatory)][string]$ConfigPath)
$ErrorActionPreference='Stop'
$taskConfig=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$taskBoot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
if($taskBoot -le ([DateTimeOffset]$taskConfig.PreWindowsBootUtc).UtcDateTime){Write-Output 'Windows has not rebooted since preparation. No post-reboot success is recorded.';return}
$taskBaseline=Get-Content -LiteralPath $taskConfig.RestartBaselinePath -Raw | ConvertFrom-Json
$taskDir=Split-Path -Parent $taskConfig.RestartBaselinePath
$taskReceipt=Join-Path $taskDir ('windows-after-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'.json')
$taskSuffix=[IO.Path]::GetFileNameWithoutExtension($taskReceipt)
$taskState=[ordered]@{checked_utc=[DateTime]::UtcNow.ToString('o');windows_boot_utc=$taskBoot.ToString('o');new_windows_boot=$true;raw_prefix_matches=$false;review_journal_matches=$false;backup_matches=$false;https='unknown';uid_control='unknown';dns='unknown';native_observation='unknown';protected_runtime='not controlled by recovery';status='checking'}
try{
    $taskRaw=[IO.File]::Open($taskConfig.LogPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    $taskSha=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
    try{
        $taskRemaining=[long]$taskBaseline.raw_prefix_bytes
        $taskBuffer=[byte[]]::new(65536)
        while($taskRemaining -gt 0){$taskRead=$taskRaw.Read($taskBuffer,0,[int][Math]::Min($taskRemaining,$taskBuffer.Length));if($taskRead -eq 0){throw 'Original log shortened.'};$taskSha.AppendData($taskBuffer,0,$taskRead);$taskRemaining-=$taskRead}
        $taskState.raw_prefix_matches=([Convert]::ToHexString($taskSha.GetHashAndReset()).ToLowerInvariant() -eq $taskBaseline.raw_prefix_sha256)
    }finally{$taskRaw.Dispose();$taskSha.Dispose()}
    $taskState.review_journal_matches=((Get-FileHash -LiteralPath (Join-Path $taskConfig.DataDirectory 'operator-review.jsonl')).Hash.ToLowerInvariant() -eq $taskBaseline.journal_sha256)
    $taskState.backup_matches=((Get-FileHash -LiteralPath $taskConfig.HealthBackup).Hash.ToLowerInvariant() -eq $taskBaseline.backup_sha256)
    if(-not $taskState.raw_prefix_matches -or -not $taskState.review_journal_matches -or -not $taskState.backup_matches){throw 'Original evidence/review/backup integrity needs investigation.'}
    $taskCurl=Join-Path $env:SystemRoot 'System32\curl.exe'
    $taskHttps=& $taskCurl --max-time 15 -sS -o (Join-Path $taskDir ($taskSuffix+'-https.html')) -w '%{http_code} %{ssl_verify_result}' 'https://example.com/' 2>(Join-Path $taskDir ($taskSuffix+'-https.stderr.txt'))
    $taskState.https=@{curl_exit=$LASTEXITCODE;http_tls_result=$taskHttps}
    $taskUid=& $taskCurl --max-time 15 -sS -o (Join-Path $taskDir ($taskSuffix+'-uid.txt')) -w '%{http_code} %{local_ip} %{local_port} %{remote_ip} %{remote_port} %{size_download}' 'http://testmyids.com/' 2>(Join-Path $taskDir ($taskSuffix+'-uid.stderr.txt'))
    $taskState.uid_control=@{curl_exit=$LASTEXITCODE;tuple_and_result=$taskUid}
    try{$taskState.dns=@(Resolve-DnsName -Name example.com -Server $taskConfig.VaultAddress -Type A -DnsOnly -QuickTimeout -ErrorAction Stop | Where-Object Type -eq A | Select-Object -ExpandProperty IPAddress)}catch{$taskState.dns='DNS check failed'}
    $taskState.receiver=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/events' -TimeoutSec 5 | Select-Object accepted_this_run,retention_full,stored_bytes,max_bytes,uptime_seconds
    $taskState.viewer=Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/status' -TimeoutSec 5
    $taskState.native_observation=Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'health-snapshot.json') -Raw | ConvertFrom-Json
    $taskReceiverPid=[int](Get-Content -LiteralPath (Join-Path (Split-Path -Parent $taskConfig.LogPath) 'receiver.pid'))
    $taskModelPid=(Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'model-runtime\owner.json') -Raw | ConvertFrom-Json).pid
    $taskViewerPid=(Get-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'viewer-owner.json') -Raw | ConvertFrom-Json).pid
    $taskState.owned_processes=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in $taskReceiverPid,$taskModelPid,$taskViewerPid} | Select-Object ProcessId,CreationDate,ExecutablePath)
    $taskState.status='receipt collected; verify new report, native freshness and EVE tuple separately'
}catch{$taskState.status='needs investigation';$taskState.reason=$_.Exception.Message}
finally{$taskState.finished_utc=[DateTime]::UtcNow.ToString('o');$taskState | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $taskReceipt -Encoding utf8}
Write-Output "Post-Windows-boot receipt saved: $taskReceipt. This is collected evidence, not a blanket success assertion."
