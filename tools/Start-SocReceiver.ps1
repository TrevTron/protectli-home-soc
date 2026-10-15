param(
    [Parameter(Mandatory=$true)][string]$LanAddress,
    [Parameter(Mandatory=$true)][string]$VaultAddress,
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [int]$SyslogPort = 5514,
    [int]$DashboardPort = 8765,
    [ValidateRange(1,1024)][int]$MaxMiB = 1024,
    [string]$OwnerPath = (Join-Path $PSScriptRoot '..\private\analyst\recovery\receiver-owner.json')
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOwnerPath = [IO.Path]::GetFullPath($OwnerPath)
$taskPrivateRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot 'private')) + [IO.Path]::DirectorySeparatorChar
if (-not $taskOwnerPath.StartsWith($taskPrivateRoot,[StringComparison]::OrdinalIgnoreCase)) {throw 'Receiver ownership receipt must stay within this project private directory.'}
$taskPrivate = Join-Path $taskRoot 'private\logs'
New-Item -ItemType Directory -Path $taskPrivate -Force | Out-Null
$taskExisting = Get-NetUDPEndpoint -LocalAddress $LanAddress -LocalPort $SyslogPort -ErrorAction SilentlyContinue
if ($taskExisting) { throw "Port $SyslogPort is already bound at $LanAddress. Inspect its owner before starting." }
$taskArgs = @('-u', ('"' + (Join-Path $PSScriptRoot 'soc_receiver.py') + '"'), '--bind', $LanAddress,
    '--allow-source', $VaultAddress, '--port', $SyslogPort, '--dashboard-port', $DashboardPort,
    '--output', ('"' + (Join-Path $taskPrivate 'syslog.jsonl') + '"'), '--max-mib', $MaxMiB)
$taskRunStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$taskStdout = Join-Path $taskPrivate "receiver-$taskRunStamp-stdout.log"
$taskStderr = Join-Path $taskPrivate "receiver-$taskRunStamp-stderr.log"
$taskProcess = Start-Process -FilePath $PythonPath -ArgumentList $taskArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskPrivate 'receiver.pid')
[pscustomobject]@{time=(Get-Date).ToString('o');pid=$taskProcess.Id;stdout=$taskStdout;stderr=$taskStderr;lan=$LanAddress;source=$VaultAddress;syslogPort=$SyslogPort;dashboardPort=$DashboardPort} | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $taskPrivate 'receiver-launches.jsonl')
$taskDeadline = (Get-Date).AddSeconds(5)
do {
    Start-Sleep -Milliseconds 100
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) { throw "Receiver exited. Inspect $taskStderr" }
    $taskSocket = Get-NetUDPEndpoint -LocalAddress $LanAddress -LocalPort $SyslogPort -ErrorAction SilentlyContinue
} while (-not $taskSocket -and (Get-Date) -lt $taskDeadline)
if (-not $taskSocket -or $taskSocket.OwningProcess -ne $taskProcess.Id) { throw 'Receiver socket ownership could not be verified.' }
$taskNativeProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskProcess.Id)"
if (-not $taskNativeProcess -or $taskNativeProcess.ExecutablePath -ne [IO.Path]::GetFullPath($PythonPath)) {throw 'Receiver executable identity could not be verified; ownership receipt not replaced.'}
$taskOwnerDirectory = Split-Path -Parent $taskOwnerPath
New-Item -ItemType Directory -Path $taskOwnerDirectory -Force | Out-Null
$taskOwnerPending = $taskOwnerPath + '.' + $taskProcess.Id + '.pending'
@{pid=$taskProcess.Id;started_utc=$taskNativeProcess.CreationDate.ToUniversalTime().ToString('o');executable=$taskNativeProcess.ExecutablePath} | ConvertTo-Json | Set-Content -LiteralPath $taskOwnerPending -Encoding utf8
[IO.File]::Move($taskOwnerPending,$taskOwnerPath,$true)
Write-Output "Receiver PID $($taskProcess.Id) owns UDP ${LanAddress}:$SyslogPort. Verify live Vault receipt before claiming forwarding works."
