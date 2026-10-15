param(
    [Parameter(Mandatory)][string]$SourceAddress,
    [Parameter(Mandatory)][string]$Condition,
    [Parameter(Mandatory)][string]$ReceiptPath,
    [string]$RemoteAddress = ''
)
# Bounded downloads to Cloudflare's documented measurement endpoint.
# Measures the complete routed Internet path, not the Vault's maximum capacity.
$ErrorActionPreference = 'Stop'
$taskSizes = @(1000000,25000000,25000000,25000000)
for ($taskTrial=0; $taskTrial -lt $taskSizes.Count; $taskTrial++) {
    $taskBytes = $taskSizes[$taskTrial]
    $taskStart = [DateTime]::UtcNow.ToString('o')
    $taskCurlArgs = @('--noproxy','*','--interface',$SourceAddress,'--connect-timeout','5','--max-time','30','--silent','--show-error','--output','NUL','--write-out','%{json}')
    if ($RemoteAddress) { $taskCurlArgs += @('--resolve',"speed.cloudflare.com:443:$RemoteAddress") }
    $taskCurlArgs += "https://speed.cloudflare.com/__down?bytes=$taskBytes"
    $taskRaw = & curl.exe @taskCurlArgs
    $taskExit = $LASTEXITCODE
    $taskResponse = ConvertFrom-Json -InputObject $taskRaw
    $taskComplete = $taskExit -eq 0 -and $taskResponse.http_code -eq 200 -and $taskResponse.size_download -eq $taskBytes -and $taskResponse.ssl_verify_result -eq 0 -and $taskResponse.local_ip -eq $SourceAddress
    if ($RemoteAddress -and $taskResponse.remote_ip -ne $RemoteAddress) { $taskComplete = $false }
    $taskRate = $null
    if ($taskComplete -and $taskResponse.time_total -gt 0) {
        $taskRate = $taskResponse.size_download * 8 / $taskResponse.time_total / 1000000
    }
    $taskRecord = [pscustomobject]@{
        utc=$taskStart;condition=$Condition;trial=$taskTrial;warmup=($taskTrial -eq 0);fixed_remote=$RemoteAddress
        scope='Routed Internet endpoint download; includes connection/TLS; not Vault capacity'
        expected_bytes=$taskBytes;bytes=$taskResponse.size_download;complete=$taskComplete
        http_status=$taskResponse.http_code;curl_exit=$taskExit;ssl_verify_result=$taskResponse.ssl_verify_result
        local_ip=$taskResponse.local_ip;local_port=$taskResponse.local_port
        remote_ip=$taskResponse.remote_ip;remote_port=$taskResponse.remote_port;http_version=$taskResponse.http_version
        dns_s=$taskResponse.time_namelookup;connect_s=$taskResponse.time_connect
        tls_s=$taskResponse.time_appconnect;first_byte_s=$taskResponse.time_starttransfer
        total_s=$taskResponse.time_total;payload_over_total_mbps=$taskRate
    }
    $taskRecord | ConvertTo-Json -Compress | Add-Content -LiteralPath $ReceiptPath -Encoding utf8
    $taskRecord | Select-Object trial,warmup,complete,bytes,total_s,payload_over_total_mbps | ConvertTo-Json -Compress
    if (-not $taskComplete) { throw 'Incomplete or invalid bounded download. Receipt retained; stopped further trials.' }
}
