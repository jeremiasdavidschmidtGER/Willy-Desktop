# Willy Desktop — AGENT_PLAN.md (Gate A only)

Smallest structure that works. The full seven-role hierarchy and the Hermes
orchestrator from AGENT_DEVELOPMENT_SPEC.md are **deferred** — see §4.

## 1. Structure for Gate A

```text
Human (you)
├── LEAD      — Claude Code session in main checkout   C:\Projects\willy-desktop
├── IMPL-A    — Claude Code worktree "platform"        C:\Projects\willy-platform
├── IMPL-B    — Claude Code worktree "animation"       C:\Projects\willy-animation
└── QA        — Claude Code worktree "qa"              C:\Projects\willy-qa
```

Four sessions total; at most two implementation sessions active at once
(matches the source spec's early-parallelism cap).

**LEAD** — owns `contracts/`, `app/`, `docs/`; writes/adjusts task briefs;
reviews every PR for interface compliance; the only session that merges to
`main` (after your approval). Does A-01 itself. Uses **subagents** for
bounded read-only investigation (e.g. "verify PySide6 6.7 focus-steal
behaviour of `WA_ShowWithoutActivating` on Windows 11", "survey Qt screen-
change signal reliability") — never for implementation.

**IMPL-A (platform track)** — window, tray, monitors, interaction plumbing,
persistence. Collapsing the spec's Platform + Character/Persistence roles
into one session is fine at Gate A: the character system is only the small
`InteractionController`, and serializing A-02→A-03→A-07→… avoids all shared-
file conflicts.

**IMPL-B (animation track)** — asset runtime, mirroring, animation
controller. Genuinely independent of the platform track until A-07
integration (which IMPL-A does, consuming IMPL-B's protocol).

**QA** — independent; owns `tools/test_harness/`, `tests/simulation/`, CI.
Never edits `src/willy/`. Verifies each completion report by rerunning
commands before LEAD merges.

## 2. Task ownership

| Task | Owner | Notes |
|---|---|---|
| A-01 scaffold + contracts | LEAD | serial, first |
| A-02 persistence | IMPL-A | parallel group 1 |
| A-03 window | IMPL-A | after A-02 within its track (or swap order) |
| A-04 asset runtime | IMPL-B | parallel group 1 |
| A-05 mirroring | IMPL-B | parallel group 2 |
| A-06 anim controller | IMPL-B | parallel group 2 |
| A-07 drag/drop + persistence | IMPL-A | integration point; IMPL-B idle or on A-05 polish |
| A-08 click reactions | IMPL-A | parallel group 3 |
| A-09 tray | IMPL-A | group 3 — serialize A-08/A-09 within IMPL-A, or hand A-09 to IMPL-B (it's isolated in `ui/tray/`) |
| A-10 monitors/DPI | IMPL-B → `platform/`? No: IMPL-A owns `platform/`. A-10 = IMPL-A; IMPL-B assists with scale-factor API only | keep path ownership clean |
| A-11 soak/perf | QA | fixtures start right after A-01 |
| A-12 acceptance run | QA prepares, human executes, LEAD signs report | serial, last |

Practical cadence: group 1 is the only period with three sessions coding at
once (A-02/A-03 serialized inside IMPL-A anyway, so effectively two). If
coordination overhead bites, drop to LEAD + one IMPL + QA — the backlog is
ordered so a single implementer can also just walk it top-to-bottom.

## 3. Workflow per task

1. LEAD copies the brief from GATE_A_BACKLOG.md into the worktree session.
2. Agent posts a short plan; LEAD approves before coding (spec §6.1).
3. Agent implements on `feature/gate-a-XX-name`, runs standard commands,
   returns the completion report format from CLAUDE.md.
4. QA reruns tests in its own worktree; adds findings.
5. LEAD reviews diff vs owned paths + interfaces; you spot-check user-visible
   behaviour (window feel, drag feel, art crispness — agents can't judge
   these).
6. LEAD merges to `main` with your approval.

## 4. Deferred, and when it becomes worth it

- **Character, Den/Folder, Conversation, Content agents:** at Gate B start —
  when the modules they own actually exist. Split Character/Persistence out
  of IMPL-A first (Phase 4–7 work), Den/Folder second (Phase 6/8),
  Conversation only after deterministic Willy passes review (spec §6.6 start
  condition).
- **Hermes orchestrator:** only after Gate B's backlog exists, standard
  commands are boringly stable, and you've run this manual 4-session loop
  through at least one full milestone (spec §22.1). At Gate A scale, Hermes
  is pure overhead — its dependency-selection job is already done by the
  backlog ordering.
