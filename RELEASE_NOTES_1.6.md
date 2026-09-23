# Jarvis Personal GPT 1.6 — Capability Acquisition

## Mudança central

A versão 1.6 introduz um **Capability Acquisition Engine** para o Jarvis não depender apenas do catálogo pré-programado.

## Novidades

- Capability Resolver;
- registro persistente de lacunas;
- Capability Factory;
- composição de Skills a partir de Actions/Workflows/Capabilities/Skills existentes;
- validação de IDs e parâmetros antes da instalação;
- parâmetros ausentes viram inputs reutilizáveis;
- proveniência das Skills adquiridas;
- descoberta de OpenAPI pública;
- importação continua restrita a GET público/anônimo HTTPS;
- descoberta de interfaces públicas de sites;
- integração com fontes públicas existentes;
- documentação pública como candidato de investigação;
- falhas do Agent Runtime alimentam o mapa de lacunas;
- Self Awareness passa a explicar descoberta autônoma;
- Centro de Controle mostra competências adquiridas e gaps;
- `Aprenda sozinho a fazer ...` pode instalar automaticamente uma receita local segura;
- `Descubra como fazer ...` apenas investiga/propoõe;
- instalação explícita funciona também pelo Mobile Companion.

## Arquitetura

```text
pedido
 ↓
resolver
 ↓
competência existente? ─ sim → executar normalmente
 ↓ não
Gap Registry
 ↓
Factory / API Discovery / Teaching
 ↓
Candidate
 ↓
Validator
 ↓
Skill / Capability persistente
```

## Continuidade preservada

A 1.6 mantém:

- Swarm Intelligence;
- Apprenticeship;
- ensino por demonstração;
- Long-Running Runtime;
- UX Stability;
- Mobile Companion;
- Auto Updater;
- Vercel launcher/PWA;
- memória/projetos em `JarvisData`.
