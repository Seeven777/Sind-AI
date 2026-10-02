$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonW = Join-Path $Project ".venv\Scripts\pythonw.exe"
$Python = Join-Path $Project ".venv\Scripts\python.exe"
$BaseUrl = "http://127.0.0.1:4760"

if (-not (Test-Path $PythonW)) { $PythonW = $Python }
if (-not (Test-Path $PythonW)) { throw ".venv não encontrado." }

function Test-Jarvis {
    try {
        $x = Invoke-RestMethod -Uri "$BaseUrl/api/ping" -TimeoutSec 1
        return ($x.ok -eq $true)
    } catch { return $false }
}

if (-not (Test-Jarvis)) {
    Start-Process -FilePath $PythonW -ArgumentList @("-m","jarvis","ui","--no-open") -WorkingDirectory $Project -WindowStyle Hidden
    for ($i=0; $i -lt 80; $i++) {
        Start-Sleep -Milliseconds 250
        if (Test-Jarvis) { break }
    }
}

if (-not (Test-Jarvis)) { throw "Jarvis não iniciou." }

# Briefing notification. Failure here never kills Jarvis.
try {
    $brief = Invoke-RestMethod -Uri "$BaseUrl/api/briefing" -TimeoutSec 4
    $s = $brief.summary
    $text = "$($s.inbox_unread) inbox | $($s.upcoming_events) eventos | $($s.active_tasks) tarefas | $($s.pending_approvals) aprovações"

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.Visible = $true
    $notify.BalloonTipTitle = "Jarvis"
    $notify.BalloonTipText = $text
    $notify.ShowBalloonTip(8000)
    Start-Sleep -Seconds 9
    $notify.Dispose()
} catch {}
