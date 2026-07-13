# Willy Desktop — Development Rules (Claude Code)

Read before changing anything: `docs/MVP_SPEC.md`,
`docs/AGENT_DEVELOPMENT_SPEC.md`, `docs/ARCHITECTURE.md`,
`docs/INTERFACES.md`, then your task brief in `docs/GATE_A_BACKLOG.md`.

## Current gate

**Gate A — Desktop Creature Foundation.** No den, folders, LLM, guests,
narrative, audio content, or CS2 code. If your task seems to need them, stop
and escalate.

## Product restrictions (absolute)

- Never modify, create, rename, or delete real user files. App writes only
  under `%APPDATA%/WillyDesktop/`.
- Never automate mouse/keyboard input; never import or suggest
  `pyautogui`/`keyboard`/`SendInput`.
- Never capture screenshots or keystrokes.
- No health/medical advice anywhere, including test fixtures and comments.
- Willy must fully function with no LLM present. Local-first; no cloud
  dependencies or network calls.

## Engineering rules

- Stack is fixed: Python 3.13, PySide6, SQLite, pytest, Ruff.
- Stay inside your task's **Owned paths**; never touch **Forbidden paths**.
- `src/willy/contracts/` is read-only for implementation agents. Interface
  changes go through escalation, not edits.
- Communicate across modules only via events/commands from INTERFACES.md.
  Platform code never mutates character state; decision code never imports Qt.
- Non-Qt code takes an injected `Clock`; no `datetime.now()` in core logic.
- Pixel art: nearest-neighbour scaling only, integer factors.
- Keep GUI non-blocking: no sleeps, no long loops on the main thread.
- Add tests for every behaviour change. Before reporting done, run:
  `python -m pytest`, `python -m ruff check .`,
  `python -m ruff format --check .`
- Small commits, one task per branch (`feature/gate-a-XX-name`). Never commit
  to `main`. No secrets, no generated junk files.
- Do not claim success without pasted test output.

## Escalate (stop, report, don't improvise) when

- the brief conflicts with a spec or with INTERFACES.md;
- you need to edit forbidden paths or shared contracts;
- a Windows behaviour can't be tested in this environment (say so; list the
  manual check instead);
- a new dependency is needed.

## Completion report (required, every task)

1. Summary. 2. Changed files. 3. Exact commands run. 4. Test output
(pass/fail/skip counts). 5. Manual checks actually performed. 6. Remaining
risks / untested assumptions. 7. Deliberately not implemented. 8. Branch +
commit id.
