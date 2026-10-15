param(
    [Parameter(Mandatory=$true)][string]$LanAddress,
    [Parameter(Mandatory=$true)][string]$VaultAddress,
    [Parameter(Mandatory=$true)][string]$InterfaceAlias,
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [int]$Port = 5514
)
# Run once in Administrator PowerShell. This never disables the firewall.
$ErrorActionPreference = 'Stop'
if ($LanAddress -eq '0.0.0.0' -or $VaultAddress -in @('Any','0.0.0.0','0.0.0.0/0')) {
    throw 'Use the exact owned LAN address and Vault address.'
}
$taskName = 'Protectli Home SOC syslog receiver'
$taskExistingRule = Get-NetFirewallRule -DisplayName $taskName -ErrorAction SilentlyContinue
if ($taskExistingRule) {
    throw 'A rule with this name exists. Inspect its address, port, interface and program filters before changing it.'
}
New-NetFirewallRule -DisplayName $taskName -Description 'Owned Vault LAN syslog only. Dashboard stays localhost-only.' -Direction Inbound -Action Allow -Protocol UDP -LocalAddress $LanAddress -LocalPort $Port -RemoteAddress $VaultAddress -InterfaceAlias $InterfaceAlias -Program $PythonPath -Profile Any | Select-Object DisplayName,Enabled,Direction,Action
