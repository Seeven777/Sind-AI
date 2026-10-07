Sind-AI v4.1 - Validate hotfix

Corrige somente o teste legado de voz em tests/product/test_companion_presence_v2.py.
Presence v4 adicionou Windows SAPI como backend TTS zero-config. Em Windows, o estado correto passou a ser healthy/windows-sapi, mas o teste antigo ainda exigia unconfigured.

Aplicacao:
1. Extraia sobre C:\Users\AMD\Desktop\Sind-AI
2. Confirme substituicao.
3. Rode Validate-Jarvis-Complete.cmd novamente.

Validacao neste pacote:
- pytest: 102 passed
- scripts/release_self_test.py: PASS
