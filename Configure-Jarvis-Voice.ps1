$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project '.venv\Scripts\python.exe'

Write-Host ''
Write-Host 'JARVIS v6 - VOZ' -ForegroundColor Cyan
Write-Host '1 - Edge Neural (recomendado, gratuito, sem API key)' -ForegroundColor Green
Write-Host '2 - Chatterbox local/OpenAI-compatible (opcional)' -ForegroundColor Gray
Write-Host '3 - ElevenLabs (opcional)' -ForegroundColor Gray
Write-Host '4 - Windows SAPI (fallback)' -ForegroundColor Gray
Write-Host ''
$choice = Read-Host 'Escolha [1]'
if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }

switch ($choice.Trim()) {
  '1' {
    if (-not (Test-Path $Python)) { throw '.venv não encontrado. Execute Setup-Jarvis-Base.cmd primeiro.' }
    Write-Host 'Instalando/atualizando Edge Neural TTS...' -ForegroundColor Cyan
    & $Python -m pip install --upgrade 'edge-tts>=7.2.8,<8'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar edge-tts.' }
    $voice = Read-Host 'Voz masculina pt-BR [pt-BR-AntonioNeural]'
    if ([string]::IsNullOrWhiteSpace($voice)) { $voice = 'pt-BR-AntonioNeural' }
    [Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER','edge-tts','User')
    [Environment]::SetEnvironmentVariable('JARVIS_EDGE_VOICE',$voice.Trim(),'User')
    [Environment]::SetEnvironmentVariable('JARVIS_EDGE_RATE','-6%','User')
    [Environment]::SetEnvironmentVariable('JARVIS_EDGE_PITCH','-14Hz','User')
    Write-Host "Voz configurada: $($voice.Trim())" -ForegroundColor Green
  }
  '2' {
    $url = Read-Host 'URL do servidor Chatterbox [http://127.0.0.1:4123]'
    if ([string]::IsNullOrWhiteSpace($url)) { $url = 'http://127.0.0.1:4123' }
    [Environment]::SetEnvironmentVariable('JARVIS_CHATTERBOX_URL',$url.TrimEnd('/'),'User')
    [Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER','chatterbox','User')
    Write-Host 'Chatterbox configurado. O servidor deve estar ativo.' -ForegroundColor Green
  }
  '3' {
    $key = Read-Host 'ElevenLabs API Key'
    $voice = Read-Host 'ElevenLabs Voice ID'
    if ([string]::IsNullOrWhiteSpace($key) -or [string]::IsNullOrWhiteSpace($voice)) { throw 'API Key e Voice ID são obrigatórios.' }
    [Environment]::SetEnvironmentVariable('JARVIS_ELEVENLABS_API_KEY',$key.Trim(),'User')
    [Environment]::SetEnvironmentVariable('JARVIS_ELEVENLABS_VOICE_ID',$voice.Trim(),'User')
    [Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER','elevenlabs','User')
    Write-Host 'ElevenLabs configurado.' -ForegroundColor Green
  }
  '4' {
    [Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER','windows-sapi','User')
    Write-Host 'Windows SAPI configurado como fallback principal.' -ForegroundColor Yellow
  }
  default { throw 'Opção inválida.' }
}
Write-Host 'Reinicie o Jarvis para aplicar.' -ForegroundColor Cyan
