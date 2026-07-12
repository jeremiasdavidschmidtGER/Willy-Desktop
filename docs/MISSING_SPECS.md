# Missing source documents (escalation note, A-01)

`docs/MVP_SPEC.md` and `docs/AGENT_DEVELOPMENT_SPEC.md` are referenced as
the top of the source-of-truth chain (ARCHITECTURE.md header, CLAUDE.md)
but were not present in the DevelopmentSpecs folder this repo was seeded
from. Consequences until they arrive:

- Canonical animation asset ids (MVP §29) are unknown — the asset factory
  exports provisional ids (`willy_idle`, `willy_walk`, …).
- Gate A acceptance criteria list (MVP §6.4) is known only indirectly via
  backlog references.

Action: obtain both files and drop them into `docs/`.
