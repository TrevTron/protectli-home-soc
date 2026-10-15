param([Parameter(Mandatory)][string]$ReceiptPath)
# Run in Administrator PowerShell. Retains existing time-provider configuration.
$ErrorActionPreference = 'Stop'
$taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$taskPrincipal = [Security.Principal.WindowsPrincipal]::new($taskIdentity)
if (-not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Windows requires an elevated process to start its time service.'
}
Start-Transcript -LiteralPath $ReceiptPath -Append | Out-Null
try {
    Get-Service -Name W32Time | Select-Object Name,Status,StartType
    Start-Service -Name W32Time
    w32tm /query /configuration
    w32tm /resync /rediscover
    if ($LASTEXITCODE -ne 0) { throw 'Windows time resync failed. Receipt retained; no provider change made.' }
    w32tm /query /status
    Get-Service -Name W32Time | Select-Object Name,Status,StartType
} finally {
    Stop-Transcript | Out-Null
}
