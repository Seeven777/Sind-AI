# Hermes Windows PATH fix

O bridge do Hermes agora procura primeiro uma entrada exata no PATH antes de
usar `shutil.which()`. Isso evita que o Windows ignore scripts executáveis sem
extensão em testes/dev shims e selecione outro `hermes.exe` instalado no PATH.

O comportamento normal para `hermes.exe`, `hermes.cmd` etc. permanece preservado.
