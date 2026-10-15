param(
    [string]$InputText = '',
    [Parameter(Mandatory)][string]$ReceiptPath,
    [ValidateRange(1,50)][int]$Seconds = 5,
    [ValidateRange(100,20000)][int]$DisplayTail = 3000
)
$ErrorActionPreference = 'Stop'
$taskSerial = [IO.Ports.SerialPort]::new('COM3',115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
$taskSerial.Handshake = [IO.Ports.Handshake]::None
try {
    $taskSerial.Open()
    if ($InputText) { $taskSerial.Write($InputText) }
    $taskUntil = [DateTime]::UtcNow.AddSeconds($Seconds)
    $taskText = ''
    while ([DateTime]::UtcNow -lt $taskUntil) {
        $taskText += $taskSerial.ReadExisting()
        Start-Sleep -Milliseconds 100
    }
    if ($taskText) {
        Add-Content -LiteralPath $ReceiptPath -Value $taskText -Encoding utf8
        Write-Output $taskText.Substring([Math]::Max(0,$taskText.Length-$DisplayTail))
    } else { Write-Output 'No new serial output. No probe sent.' }
} finally {
    if ($taskSerial.IsOpen) { $taskSerial.Close() }
    $taskSerial.Dispose()
}
