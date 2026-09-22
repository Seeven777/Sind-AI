# Mobile Hotfix 1.3.1

Corrige dois sintomas reportados no Windows:

1. `favicon.ico 404`
   - agora existe favicon SVG;
   - `/favicon.ico` responde 204, portanto não gera erro no console.

2. janela de CMD/PowerShell piscando
   - a detecção de interfaces de rede usava PowerShell durante o refresh da UI;
   - agora os subprocessos Windows são executados com `CREATE_NO_WINDOW`;
   - endereços de rede são cacheados por 60 segundos.

Também foram adicionados:

- `web_root` ancorado em `mobile/companion.py`, evitando dependência do diretório atual;
- validação explícita de `mobile/web/index.html`;
- tentativa automática das portas 8770–8780 se 8770 estiver ocupada;
- endpoint `/health`;
- diagnóstico mostra se a interface mobile realmente existe;
- página HTML explicativa em vez de JSON cru caso os arquivos da UI estejam ausentes.
