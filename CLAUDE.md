# Willy Desktop — Development Rules (Claude Code)

> **Orientation for any agent landing here. Read this map first.** The map
> below is duplicated verbatim in the asset factory's CLAUDE.md
> (`...\Willy App\Python-Test\CLAUDE.md`) — if you change one, change both.

## Willy project map — TWO git repos, one parent folder

Everything Willy lives under `...\Desktop\Dateien für KI-Projekte\`:

| Path | What it is | Nature |
|---|---|---|
| `Willy App\willy-desktop\` ← **you are here** | **Product app**: PySide6 desktop pet that *consumes* exported clips | Strict, gate-driven: no network, local-first, contracts read-only. |
| `Willy App\Python-Test\` | **Asset factory**: concept art → animations → Gate A clip export | Art lab. Uses OpenAI API + screenshots. Experimental. |
| `Willy App\DevelopmentSpecs\` | Product vision & specs (also copied into this repo's `docs/`) | Reference only, not a git repo. |
| `Willy_Archive\` | Retired attempts + the **Codex reference app** | **Never work here** — but `codex-product-app\` there has A-01..A-10 implemented (unreviewed); read its `persistence/`, `ui/window/`, `platform/win32.py` as *reference* before A-02/A-03. |

**Cross-repo continuity source: `...\Willy App\Python-Test\HANDOFF.md`** holds
the project-wide *now*/*next*. Consume finished art from
`...\Willy App\Python-Test\assets\gate_a\` (PNGs + AnimationManifest JSON) —
that deliverable is the only thing that crosses from the factory to here.

---

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

- Stack is fixed: Python 3.12, PySide6, SQLite, pytest, Ruff.
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
