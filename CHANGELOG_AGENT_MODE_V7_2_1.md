# Agent Mode v7.2.1 — Anywhere parser hotfix

- Corrige erro de parser do Windows PowerShell em `"$mode: ..."` usando `"${mode}: ..."`.
- Salva scripts públicos em UTF-8 com BOM para evitar textos `pÃºblico`/`nÃ£o` no Windows PowerShell 5.1.
- Adiciona teste de regressão para impedir o retorno da interpolação ambígua.
- Não altera token, autenticação, túnel ou runtime do Jarvis.
