# Jarvis 3D Office Architecture

The 3D HQ is a renderer, not a second runtime.

```text
Jarvis Core
    |
    +-- /api/hq  --->  3D renderer
    |                  |
    |                  +-- rooms
    |                  +-- desks
    |                  +-- agents
    |                  +-- status lights
    |                  +-- missions/attention inspector
    |
    +-- Event Bus / Task Engine / Agent Runs remain source of truth
```

## Interaction

- orbit: drag
- pan: right drag / configured OrbitControls behavior
- zoom: wheel or controls
- click agent: show agent state
- click room: show department state
- reset: restore overview camera
- auto: toggle slow camera rotation

The visual agent state is sampled from `/api/hq`; the frontend never invents execution state.
