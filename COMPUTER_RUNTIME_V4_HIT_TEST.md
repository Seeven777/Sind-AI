# Sind AI — Computer Runtime V4 Hit-Test

O V3 provou que:
- o campo raw de busca é encontrado;
- `Me (você)` é um resultado lógico único;
- a falha acontece na ativação/verificação.

O V4 elimina cliques cegos.

## Mudanças

1. Foreground é aplicado no HWND raiz do aplicativo (`GA_ROOT`), não apenas
   no renderer `Chrome_WidgetWin_1`.
2. Mouse usa `SendInput`, com verificação da posição real do cursor.
3. Antes de cada clique, `UIA ElementFromPoint`/`Desktop.from_point()` confirma
   qual elemento existe naquele pixel.
4. O clique só acontece se o elemento ou um ancestral for realmente o contato.
5. O cabeçalho da conversa aceita nomes de acessibilidade com pequeno sufixo
   de status no painel direito.
6. O benchmark grava `activation_trace`, contendo:
   - pontos candidatos;
   - elemento UIA atingido em cada ponto;
   - cadeia de ancestrais;
   - ponto escolhido;
   - evidência do painel direito imediatamente após o clique.
7. Nenhuma mensagem é enviada.

## Instalação

Feche o Jarvis e extraia por cima da raiz do projeto.

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v4.py
.\.venv\Scripts\python.exe .\run_computer_v4_tests.py
.\.venv\Scripts\python.exe .\computer_v4_benchmark.py --contact "Me (você)"
```

Não execute benchmark de rascunho até o benchmark de abertura retornar `ok: true`.
