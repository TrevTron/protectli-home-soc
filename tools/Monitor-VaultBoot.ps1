param([int]$Minutes = 20)
$ErrorActionPreference = 'Stop'
if ($Minutes -lt 1 -or $Minutes -gt 30) { throw 'Monitoring must be bounded to 1-30 minutes.' }
$taskPrivate = Join-Path (Split-Path -Parent $PSScriptRoot) 'private'
$taskReceipt = Join-Path $taskPrivate 'major-upgrade-console-20261005.txt'
$taskStatus = Join-Path $taskPrivate 'console-monitor-status.json'
$taskSerial = [IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$taskSerial.Handshake = [IO.Ports.Handshake]::None
$taskSerial.DtrEnable = $false
$taskSerial.RtsEnable = $false
$taskState = 'monitoring'
try {
    $taskSerial.Open()
    @{status=$taskState;pid=$PID;started=(Get-Date).ToString('o');receipt=$taskReceipt} | ConvertTo-Json | Set-Content -LiteralPath $taskStatus
    $taskDeadline = [DateTime]::UtcNow.AddMinutes($Minutes)
    $taskTail = ''
    while ([DateTime]::UtcNow -lt $taskDeadline) {
        $taskChunk = $taskSerial.ReadExisting()
        if ($taskChunk) {
            Add-Content -LiteralPath $taskReceipt -Value $taskChunk -NoNewline -Encoding utf8
            $taskTail += $taskChunk
            $taskTail = $taskTail.Substring([Math]::Max(0,$taskTail.Length-1000))
            if ($taskTail -match 'login:\s*$') { $taskState='login_prompt_port_released'; break }
        }
        Start-Sleep -Milliseconds 100
    }
    if ($taskState -eq 'monitoring') { $taskState='timeout_port_released' }
} catch { $taskState='error_port_released'; Add-Content -LiteralPath $taskReceipt -Value ('Monitor error: '+$_.Exception.Message) }
finally {
    if ($taskSerial.IsOpen) { $taskSerial.Close() }
    $taskSerial.Dispose()
    @{status=$taskState;pid=$PID;finished=(Get-Date).ToString('o');receipt=$taskReceipt} | ConvertTo-Json | Set-Content -LiteralPath $taskStatus
}
