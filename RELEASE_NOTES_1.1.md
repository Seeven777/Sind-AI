# Jarvis Personal GPT 1.1 — Local Portal

## Distribuição
- compatibilidade Vercel como portal estático;
- `app.py` renomeado para `jarvis_desktop.py`;
- build Node estático em `vercel_dist`;
- instalador PowerShell para equipe;
- protocolo `jarvis://open`;
- instalação local adaptativa por RAM.

## Self/Capability Awareness
- perguntas sobre capacidades são respondidas pelo estado real do runtime;
- lista de ferramentas do SindPetshop-SP vem de `institutional_services.json`;
- o Qwen não decide sozinho se “pode” ou “não pode” acessar uma ferramenta.

## Institutional Service Runtime
- pedidos como “veja nosso dashboard” usam Browser Agent diretamente;
- síntese usa o modelo FAST, não o 4B de raciocínio;
- fallback determinístico impede timeout bruto;
- Dashboard de Insights usa a URL de trabalho fornecida pelo usuário;
- nenhum login é armazenado pelo mapa de serviços.
