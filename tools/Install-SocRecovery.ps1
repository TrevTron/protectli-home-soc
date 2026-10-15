param([Parameter(Mandatory)][string]$ConfigPath)
$ErrorActionPreference='Stop'
$taskName='Protectli Home SOC recovery'
$taskUser=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskPowerShell=Join-Path $PSHOME 'pwsh.exe'
if(-not(Test-Path -LiteralPath $taskPowerShell -PathType Leaf)){throw 'Run this installer using PowerShell 7.'}
$taskConfigFile=[IO.Path]::GetFullPath($ConfigPath)
$taskConfig=Get-Content -LiteralPath $taskConfigFile -Raw | ConvertFrom-Json
$taskRestore=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'Restore-SocAfterLogin.ps1'))
if(Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue){throw 'A task with this name exists. Inspect before replacing it.'}
$taskAction=New-ScheduledTaskAction -Execute $taskPowerShell -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "'+$taskRestore+'" -ConfigPath "'+$taskConfigFile+'"') -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$taskLogon=New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$taskRepeat=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$taskPrincipal=New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$taskSettings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger @($taskLogon,$taskRepeat) -Principal $taskPrincipal -Settings $taskSettings -Description 'Owned local SOC recovery after user sign-in. No saved credentials, protected-model control, downloads, evidence truncation or policy changes. Honor recovery/paused.flag.' | Out-Null
$taskXml=Export-ScheduledTask -TaskName $taskName
$taskXml | Set-Content -LiteralPath (Join-Path $taskConfig.DataDirectory 'recovery\registered-task.xml') -Encoding utf8
Write-Output 'Registered limited user sign-in recovery and five-minute ownership checks. No Windows or Vault password was stored.'
