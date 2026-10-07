$ErrorActionPreference = 'Stop'
$taskName = 'JarvisNext'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host 'Inicialização automática do Jarvis removida.'
} else {
    Write-Host 'Nenhuma tarefa JarvisNext estava instalada.'
}
