param([string]$ReceiptPath = (Join-Path $PSScriptRoot '..\private\major-upgrade-console-20261005.txt'))
$Host.UI.RawUI.WindowTitle = 'Protectli Vault maintenance log (read-only)'
Write-Host 'Live copy of the saved USB-console output. This window does not own COM3.'
Write-Host 'The maintenance reader appends output after each bounded read. Ctrl+C closes this view.'
Get-Content -LiteralPath $ReceiptPath -Tail 30 -Wait
