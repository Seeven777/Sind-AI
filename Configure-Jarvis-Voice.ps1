$ErrorActionPreference = 'Stop'
Write-Host ''
Write-Host 'JARVIS - Configuracao de voz ElevenLabs' -ForegroundColor Cyan
Write-Host 'As credenciais serao salvas apenas nas variaveis de ambiente do seu usuario Windows.' -ForegroundColor DarkGray
Write-Host ''
$key = Read-Host 'ElevenLabs API Key'
$voice = Read-Host 'ElevenLabs Voice ID'
if ([string]::IsNullOrWhiteSpace($key) -or [string]::IsNullOrWhiteSpace($voice)) {
  Write-Host 'API Key e Voice ID sao obrigatorios. Nada foi alterado.' -ForegroundColor Yellow
  exit 1
}
[Environment]::SetEnvironmentVariable('JARVIS_ELEVENLABS_API_KEY', $key.Trim(), 'User')
[Environment]::SetEnvironmentVariable('JARVIS_ELEVENLABS_VOICE_ID', $voice.Trim(), 'User')
[Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER', 'elevenlabs', 'User')
Write-Host ''
Write-Host 'Voz configurada. Reinicie o Jarvis para aplicar.' -ForegroundColor Green
