# Instalação Jarvis Next Base v0.2

1. Extraia o conteúdo deste ZIP diretamente em `C:\Users\AMD\Desktop\Sind-AI`.
2. Preserve a pasta `.git`.
3. Quando o Windows perguntar, substitua os arquivos existentes.
4. Execute `Setup-Jarvis-Base.cmd`.
5. O instalador reutiliza a Foundation, instala Ollama se necessário, baixa `qwen3.5:4b`, executa os testes e delega uma missão real ao Research Agent.
6. Depois execute `Start-Jarvis.cmd`.

O modelo é configurável em `%LOCALAPPDATA%\JarvisNext\config\config.toml`.

O sistema já contém a base arquitetural dos demais domínios, mas eles permanecem desabilitados até suas implementações serem verificadas.
