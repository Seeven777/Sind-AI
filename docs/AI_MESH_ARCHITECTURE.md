# AI Mesh Architecture

```text
                         JARVIS
                            |
                    +-------+-------+
                    |   ModelRouter  |
                    +-------+-------+
                            |
          +-----------------+------------------+
          |                 |                  |
       LOCAL            PREMIUM             ADVISORY
       Ollama           Nemotron             Hermes
          |                 |                  |
          +-----------------+------------------+
                            |
                    Mission / Operator
                            |
        +-------------------+-------------------+
        |                   |                   |
     Windows            WhatsApp            Creative
     Browser          Desktop / WA-AKG       Muapi
        |                   |                   |
        +-------------------+-------------------+
                            |
                       VERIFICATION
```

## Trust boundaries

Hermes is an advisory agent. It is launched by Jarvis with the `safe` toolset by default.
It does not inherit Jarvis Operator permissions.

Nemotron is a model provider, not an executor.

WA-AKG is a transport. It does not become the canonical WhatsApp transport until delivery can be independently verified.

Creative Studio is an external job system. A completed API job is persisted only after an actual result is returned.
