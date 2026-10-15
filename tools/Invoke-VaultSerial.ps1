param(
    [Parameter(Mandatory)][string]$Command,
    [Parameter(Mandatory)][string]$ReceiptPath,
    [ValidatePattern('^COM[1-9][0-9]*$')][string]$Port = 'COM3',
    [ValidateRange(1,60)][int]$TimeoutSeconds = 15,
    [switch]$PrivateOutput
)
$ErrorActionPreference = 'Stop'
if ($Command -match "[`r`n]" -or $Command.Length -gt 900) { throw 'Use one bounded shell command line.' }
$taskSerial = [System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$taskSerial.Handshake = [System.IO.Ports.Handshake]::None
$taskSerialMutex = [Threading.Mutex]::new($false,('Local\ProtectliVaultSerial_' + $Port))
$taskSerialLockHeld = $false
try {
    try { $taskSerialLockHeld = $taskSerialMutex.WaitOne(10000) }
    catch [Threading.AbandonedMutexException] { $taskSerialLockHeld = $true }
    if (-not $taskSerialLockHeld) { throw 'Serial command refused: another owned collector holds the port lock. No command sent.' }
    $taskSerial.Open()
    # Discard queued historical output before requesting a fresh prompt.
    # Kernel diagnostics can follow a valid prompt in the same serial read.
    $taskSerial.DiscardInBuffer()
    $taskPromptPattern = '(?m)^root@protectli-soc[^\r\n#]*#[ \t]*(?:\r?$|(?=\S))'
    $taskSerial.Write("`n")
    $taskCheck = ''
    $taskUntil = [DateTime]::UtcNow.AddSeconds(2)
    while ([DateTime]::UtcNow -lt $taskUntil) {
        $taskCheck += $taskSerial.ReadExisting()
        if ($taskCheck -match $taskPromptPattern) { break }
        Start-Sleep -Milliseconds 100
    }
    if ($taskCheck -notmatch $taskPromptPattern) { throw 'Expected the already-authenticated Protectli shell. No command sent.' }
    $taskSerial.Write($Command + "`n")
    $taskOutput = ''
    $taskUntil = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $taskComplete = $false
    while ([DateTime]::UtcNow -lt $taskUntil) {
        $taskOutput += $taskSerial.ReadExisting()
        if ($taskOutput -match $taskPromptPattern) { $taskComplete = $true; break }
        Start-Sleep -Milliseconds 100
    }
    $taskOutput | Set-Content -LiteralPath $ReceiptPath -Encoding utf8
    if ($PrivateOutput) { Write-Output "Private console receipt saved ($($taskOutput.Length) characters). Command completed: $taskComplete" }
    else { Write-Output $taskOutput }
    if (-not $taskComplete) { throw 'Timeout. Receipt retained; inspect the console before sending another command.' }
} finally {
    if ($taskSerial.IsOpen) { $taskSerial.Close() }
    $taskSerial.Dispose()
    if ($taskSerialLockHeld) { $taskSerialMutex.ReleaseMutex() }
    $taskSerialMutex.Dispose()
}
