# Jarvis Next 1.0 RC3 — UI/Productivity Expansion

## Objetivo
RC3 melhora a experiência de uso diário sem alterar os princípios do core.

## Companion
- histórico persistente de conversas
- busca por título e conteúdo
- nova conversa
- renomear, fixar, arquivar e excluir
- regenerar resposta
- copiar resposta
- editar mensagem para reenviar
- renderização básica de Markdown segura
- atalhos Ctrl+K e Ctrl+Shift+N
- briefing e estado do sistema no painel lateral

## HQ
- escritório 3D interativo baseado em Three.js
- câmera orbital, zoom, rotação e reset
- departamentos como salas reais
- mesas, monitores, cadeiras, plantas, janelas e iluminação
- agentes como personagens 3D
- seleção de agente/departamento
- status visual sincronizado com backend
- painel de missão e atenção
- fallback para HQ clássico quando WebGL não estiver disponível

## Core
- SQLite permanece thread-affine
- novas operações de conversa são enfileiradas no thread proprietário
- nenhuma nova permissão de execução é concedida ao Hermes ou aos especialistas
- histórico de conversa passa a ser contexto real do modelo para chat e modos diretos

## Dependência visual
O renderer usa Three.js 0.186.1 via import map CDN. O backend continua Python-only; se a dependência visual não estiver disponível, o HQ clássico permanece acessível em `/hq-classic`.
