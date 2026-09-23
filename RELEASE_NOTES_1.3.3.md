# Jarvis Personal GPT 1.3.3 — Mobile Access Fix

Esta hotfix corrige o fluxo mostrado nos testes reais do Mobile Companion.

## Corrigido

- rota de PIN usa regex real de seis dígitos;
- `/791327` e outros PINs de 6 dígitos abrem a interface mobile;
- fallback SPA permanece disponível;
- diagnóstico identifica rede `Public`;
- botão **Tornar rede privada** foi adicionado;
- mudança de perfil exige elevação administrativa;
- regra do Firewall continua limitada a redes Private;
- o Jarvis não abre a porta mobile para a internet pública.

## Fluxo recomendado

1. Jarvis Mobile → Ativar acesso mobile.
2. Diagnosticar.
3. Se `Perfil da rede: Public`, clicar **Tornar rede privada**.
4. Diagnosticar novamente.
5. No celular, abrir o endereço `http://IP:PORT/`.
6. Informar o PIN, ou usar `http://IP:PORT/PIN`.

## Segurança

A correção não amplia a regra de firewall para redes públicas. Em vez disso, converte explicitamente a rede confiável atual para `Private`, com confirmação administrativa do Windows.
