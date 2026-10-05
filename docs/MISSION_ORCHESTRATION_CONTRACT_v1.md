# Jarvis — Mission Orchestration Contract v1

## Complex mission pipeline

When a request is explicitly identified as a complex/orchestrated mission, Jarvis uses:

```text
Memory Curator
      ↓
Research
      ↓
Analyst
      ↓
Creator  ← policy gate
      ↓
Developer
      ↓
Operator
      ↓
Reviewer ← final independent gate
```

### Stage responsibilities

**Memory Curator** is the first stage. It retrieves mission-relevant persistent memory and reports the current memory state. It does not delete or rewrite memories automatically.

**Research** is limited to context and sources explicitly supplied by the system for this complex flow. External web access is disabled by the mission policy so that a complex run does not silently reach unapproved networks.

**Analyst** converts evidence into findings, risks, priorities, decisions and gaps.

**Creator** produces the actionable plan and must emit `CREATOR_GATE: APPROVED` before the Developer stage. `CREATOR_GATE: BLOCKED` or a missing gate stops the mission before implementation.

**Developer** produces the implementation, tests and, whenever physical/external execution is required, a machine-readable `EXECUTION_PLAN`.

**Operator** is the only stage allowed to execute physical/external actions through the registered Jarvis tools. It never inherits additional permissions from Hermes, Agency Agents or other planning components. It requires verifiable tool evidence and can pause for the existing approval policy.

**Reviewer** remains an independent final gate. A mission is considered verified only when the final artifact contains `VERDICT: PASS`.

## Non-negotiable invariants

- No component may claim an action happened without evidence.
- Hermes is advisory and isolated from Operator permissions.
- Agency specialists are knowledge specialists and do not inherit Operator tools.
- WA-AKG remains an optional gateway; WhatsApp Desktop remains the verified fallback path until a gateway delivery verification flow is proven.
- Nemotron is remote/premium and is never assumed to be a local model.
- Standard missions keep the existing lightweight planner; the full contract is activated only for explicit complex/orchestration signals.
