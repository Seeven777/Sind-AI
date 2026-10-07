$ErrorActionPreference = 'Stop'
$taskName = 'JarvisNext'
$runner = (Resolve-Path (Join-Path $PSScriptRoot 'start_jarvis_background.ps1')).Path
$user = "$env:USERDOMAIN\$env:USERNAME"
$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Inicia o Jarvis Personal Agent OS no logon do Windows.' -Force | Out-Null
Write-Host "Jarvis configurado para iniciar com o Windows: $taskName"
Write-Host "Para iniciar agora: Start-ScheduledTask -TaskName '$taskName'"
