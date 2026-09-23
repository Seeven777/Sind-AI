# Capability Acquisition Engine — Jarvis 1.6

## Objetivo

A 1.6 adiciona uma camada entre **"não sei fazer"** e **"peça ao usuário para fazer manualmente"**.

O fluxo passa a ser:

```text
objetivo
  ↓
Capability Resolver
  ↓
Já existe Skill / Action / Workflow / Capability / serviço?
  ├─ sim → reutilizar
  └─ não
       ↓
registrar lacuna
       ↓
Capability Factory
       ├─ compor Skill com primitivas confiáveis
       ├─ procurar API pública/OpenAPI
       ├─ localizar fonte/documentação
       └─ se ainda faltar executor → pedir ensino/demonstração
```

## Princípio de segurança

O modelo **não ganha execução arbitrária de código**.

Uma competência adquirida automaticamente é, preferencialmente:

1. uma **Skill declarativa** composta por ferramentas já existentes;
2. uma capacidade **GET pública/anônima** importada de OpenAPI HTTPS;
3. uma referência de fonte/documentação que ainda precisa de integração;
4. um procedimento aprendido por explicação/demonstração.

Ações high/critical continuam passando pela governança normal quando a Skill for executada.

## Comandos naturais

### Verificar se já existe caminho

`O que falta para você fazer conciliação de dados?`

### Descobrir sem instalar

`Descubra como fazer conciliação de dados.`

O Jarvis registra uma lacuna e retorna candidatos numerados.

### Aprender sozinho

`Aprenda sozinho a fazer conciliação de dados.`

Se for possível montar uma receita segura com primitivas existentes, ela é validada e salva como Skill automaticamente.

### Validar um candidato

`Teste o candidato #3`

### Instalar um candidato

`Instale a capacidade #3`

### Listar lacunas

`Liste lacunas de capacidade.`

### Listar candidatos

`Liste capacidades candidatas.`

## Skill Factory

O modelo recebe somente IDs reais de primitivas do runtime e deve produzir JSON declarativo.

Exemplo conceitual:

```json
{
  "name": "Criar rascunho de matéria",
  "inputs": {
    "title": {"required": true},
    "content": {"required": true}
  },
  "steps": [
    {
      "kind": "action",
      "id": "wordpress.post.create",
      "params": {
        "title": "{{title}}",
        "content": "{{content}}",
        "status": "draft"
      }
    }
  ]
}
```

Antes de salvar, o validator confirma que todos os IDs existem. Parâmetros obrigatórios ausentes viram entradas da Skill.

## Persistência

Fica em:

`~/JarvisData/cognitive/capability_acquisition.db`

A base guarda:

- lacunas;
- tentativas;
- candidatos;
- testes;
- instalações;
- resolução da lacuna.

Skills adquiridas continuam na biblioteca persistente de Skills e recebem metadata de proveniência.

## Integração com falhas

Quando uma tarefa termina em falha ou atinge o limite estrutural de autonomia, a 1.6 tenta registrar uma lacuna se não houver executor relacionado com confiança suficiente.

Isso cria um histórico útil de **o que o Jarvis ainda precisa aprender**.

## Limites reais

Capability Acquisition não contorna:

- login/permissões;
- autenticação exigida por serviços externos;
- falta de dados;
- ausência de acesso autorizado;
- limites físicos do computador;
- ações proibidas pela governança.

O objetivo é transformar limites desconhecidos em lacunas identificáveis e ensináveis, não fingir que todo acesso já existe.
