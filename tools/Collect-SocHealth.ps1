param(
    [string]$DataDirectory = (Join-Path $PSScriptRoot '..\private\analyst'),
    [Parameter(Mandatory)][string]$VaultAddress,
    [string]$BackupPath,
    [string]$Port = 'COM3'
)
$ErrorActionPreference = 'Stop'
[void][Net.IPAddress]::Parse($VaultAddress)
$taskData = [IO.Path]::GetFullPath($DataDirectory)
New-Item -ItemType Directory -Path $taskData -Force | Out-Null
$taskStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$taskReceipt = Join-Path $taskData "health-console-$taskStamp.txt"
$taskVault = @{status='unavailable';core_temperatures_c=@();pools='unknown';suricata_pid='unknown';configuration_matches_backup='unknown'}
try {
    & (Join-Path $PSScriptRoot 'Invoke-VaultSerial.ps1') -Port $Port -ReceiptPath $taskReceipt -PrivateOutput -Command 'sysctl dev.cpu.0.temperature dev.cpu.1.temperature dev.cpu.2.temperature dev.cpu.3.temperature; pgrep -x suricata; sha256 /conf/config.xml; zpool status -x' | Out-Null
    $taskRaw = Get-Content -LiteralPath $taskReceipt -Raw
    $taskTemps = @([regex]::Matches($taskRaw,'dev\.cpu\.\d\.temperature:\s*([0-9.]+)C') | ForEach-Object {[double]::Parse($_.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)})
    $taskPidMatch = [regex]::Match($taskRaw,'(?m)^\s*(\d+)\s*$')
    $taskHashMatch = [regex]::Match($taskRaw,'SHA256 \(/conf/config.xml\) = ([a-f0-9]{64})')
    if ($taskTemps.Count -eq 4 -and $taskHashMatch.Success) {
        $taskVault.status='observed'
        $taskVault.core_temperatures_c=$taskTemps
        if ($taskPidMatch.Success) {$taskVault.suricata_pid=[int]$taskPidMatch.Groups[1].Value}
        if ($taskRaw -match 'all pools are healthy') {$taskVault.pools='healthy'}
        else {$taskVault.pools='Native output needs review; see private receipt'}
        $taskVault.configuration_sha256=$taskHashMatch.Groups[1].Value
        if ($BackupPath -and (Test-Path -LiteralPath $BackupPath -PathType Leaf)) {
            $taskVault.configuration_matches_backup=($taskVault.configuration_sha256 -eq (Get-FileHash -LiteralPath $BackupPath -Algorithm SHA256).Hash.ToLowerInvariant())
        }
    }
} catch {
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $taskData "health-console-$taskStamp.error.txt") -Encoding utf8
}
$taskHost = @{vault_route_status='unknown';vault_dns_status='unknown';wifi_state='unknown';tailscale_status='unknown';available_memory_gib='unknown'}
try {
    $taskRoutes = @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop | Where-Object {$_.NextHop -eq $VaultAddress})
    $taskHost.vault_route_status = if ($taskRoutes.Count) {'Vault gateway route present; per-connection VPN routing may differ'} else {'No Vault default gateway route observed'}
    $taskDns = @($taskRoutes | ForEach-Object {Get-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop})
    $taskHost.vault_dns_status = if (@($taskDns.ServerAddresses) -contains $VaultAddress) {'Vault DNS configured on the Vault-facing adapter'} else {'Vault DNS not observed on that adapter'}
    $taskWifi = @(Get-NetAdapter -ErrorAction Stop | Where-Object {$_.Name -match 'Wi-?Fi|Wireless'})
    $taskHost.wifi_state = if ($taskWifi.Count) {($taskWifi.Status -join ', ')} else {'No Wi-Fi adapter identified by name'}
    $taskOs = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $taskHost.available_memory_gib = [Math]::Round($taskOs.FreePhysicalMemory/1048576,2)
} catch { $taskHost.observation_error='Host collection incomplete; missing fields remain unknown' }
try {
    $taskTailExe=(Get-Command tailscale.exe -ErrorAction Stop).Source
    $taskTailRaw=(& $taskTailExe status --json 2>$null) -join "`n"
    if ($LASTEXITCODE -ne 0 -or $taskTailRaw.Length -gt 1048576) {throw 'Tailscale status unavailable'}
    $taskTail=$taskTailRaw | ConvertFrom-Json
    $taskHost.tailscale_status="$($taskTail.BackendState); this device online: $($taskTail.Self.Online)"
} catch {}
$taskHealth=@{collected_utc=[DateTime]::UtcNow.ToString('o');vault=$taskVault;host=$taskHost;native_receipt=[IO.Path]::GetFileName($taskReceipt);collector='read-only explicit observation; no autostart'}
$taskJson=$taskHealth | ConvertTo-Json -Depth 8
$taskJson | Set-Content -LiteralPath (Join-Path $taskData "health-snapshot-$taskStamp.json") -Encoding utf8
$taskPending=Join-Path $taskData "health-snapshot-$taskStamp.pending"
$taskJson | Set-Content -LiteralPath $taskPending -Encoding utf8
[IO.File]::Move($taskPending,(Join-Path $taskData 'health-snapshot.json'),$true)
Write-Output 'Health observation saved. Missing or stale observations remain explicit. Read-only collection changed no device settings.'
if ($taskVault.status -ne 'observed') { throw 'Native Vault reading unavailable. Private health snapshot and error receipt retained.' }
