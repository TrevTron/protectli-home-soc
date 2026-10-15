param([string]$Port = 'COM3')
$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = 'Protectli Vault USB login: existing root password'
$taskStatusPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'private\console-login-status.json'
function Save-LoginStatus([string]$Status, [string]$Reason = '') {
    [pscustomobject]@{time=(Get-Date).ToString('o');port=$Port;status=$Status;reason=$Reason} | ConvertTo-Json | Set-Content -LiteralPath $taskStatusPath -Encoding utf8
}
$taskSerial = [System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$taskSerial.Handshake = [System.IO.Ports.Handshake]::None
$taskSerial.DtrEnable = $false
$taskSerial.RtsEnable = $false
$taskSerial.Encoding = [Text.UTF8Encoding]::new($false)
$taskFailureReason = 'transport_or_input_error'
function Read-ConsoleText([int]$Seconds, [string]$StopPattern = '') {
    $taskUntil = [DateTime]::UtcNow.AddSeconds($Seconds)
    $taskText = ''
    while ([DateTime]::UtcNow -lt $taskUntil) {
        $taskText += $taskSerial.ReadExisting()
        if ($StopPattern -and $taskText -match $StopPattern) { break }
        Start-Sleep -Milliseconds 100
    }
    return $taskText
}
try {
    $taskSerial.Open()
    $taskSerial.Write("`n")
    $taskGreeting = Read-ConsoleText 2
    Write-Host $taskGreeting
    if ($taskGreeting -notmatch 'login:\s*$') {
        Save-LoginStatus 'failed_or_inconclusive' 'clean_login_prompt_missing'
        Write-Host 'No clean login prompt. No password will be sent. Leave this window and report the visible state.'
        Read-Host 'Press Enter to close'
        exit 1
    }
    $taskSerial.Write("root`n")
    $taskPasswordPrompt = Read-ConsoleText 2
    Write-Host $taskPasswordPrompt
    if ($taskPasswordPrompt -notmatch 'Password:\s*$') {
        $taskFailureReason = 'expected_password_prompt_missing'
        throw 'Expected a password prompt. No password sent.'
    }
    Save-LoginStatus 'waiting_for_password'
    $taskSecret = Read-Host 'Vault root password (hidden, never saved)' -AsSecureString
    $taskSecretPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecret)
    try {
        $taskSerial.Write([Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskSecretPtr))
        $taskSerial.Write("`n")
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskSecretPtr)
        $taskSecret.Dispose()
    }
    $taskLoginResult = Read-ConsoleText 10 '(?:Login incorrect|login:\s*$|Enter an option|root@protectli-soc[^\r\n]*#)'
    Write-Host $taskLoginResult
    if ($taskLoginResult -match 'Login incorrect|(?m)^\s*login:\s*$') {
        $taskFailureReason = 'credential_rejected'
        throw 'The Vault rejected this USB login. No automatic retry.'
    }
    if ($taskLoginResult -notmatch 'Enter an option|root@protectli-soc[^\r\n]*#') {
        $taskFailureReason = 'response_inconclusive'
        throw 'Login response was inconclusive. No commands sent.'
    }
    if ($taskLoginResult -notmatch 'root@protectli-soc[^\r\n]*#') {
        $taskSerial.Write("8`n")
        $taskShellResult = Read-ConsoleText 5 'root@protectli-soc[^\r\n]*#'
        if ($taskShellResult -notmatch 'root@protectli-soc[^\r\n]*#') {
            $taskFailureReason = 'authenticated_menu_shell_not_confirmed'
            throw 'Login reached the menu, but the diagnostic shell was not confirmed. No native health command sent.'
        }
    }
    Save-LoginStatus 'authenticated'
    Write-Host 'Authenticated. COM3 is now released automatically for diagnostics. You can close this window.'
} catch {
    Save-LoginStatus 'failed_or_inconclusive' $taskFailureReason
    Write-Host $_.Exception.Message
    Read-Host 'Press Enter to close'
} finally {
    if ($taskSerial.IsOpen) { $taskSerial.Close() }
    $taskSerial.Dispose()
}
