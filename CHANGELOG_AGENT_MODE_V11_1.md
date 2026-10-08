# Jarvis Agent Mode v11.1 — Live Surface Reliability

- Corrige roteamento de linguagem natural para clima/notícias em tempo real.
- Comandos como "Qual a previsão do clima para hoje?" e "Abra o gadget da previsão do clima" agora acionam Research automaticamente.
- Adiciona `weather.forecast`, ferramenta read-only estruturada via Open-Meteo, sem API key.
- Usa a preferência `autonomy.location` como local padrão quando o usuário não informa outro local.
- O gadget de clima recebe temperatura, chance de chuva, umidade e vento diretamente de dados estruturados, sem depender de extração frágil do texto do LLM.
- Pedidos explícitos para abrir/mostrar gadget iniciam a superfície expandida.
- Mantém web.search/web.fetch como rota para notícias e pesquisa pública atual.
- Nenhuma mudança em Jarvis Anywhere/ngrok ou Evolution Lab.
