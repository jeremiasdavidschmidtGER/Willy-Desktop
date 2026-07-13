# Willy Desktop — ARCHITECTURE.md

Status: Draft 1 for Gate A start. Owned by Lead Architect. Changes require ADR.
Scope: depth needed to build Gate A without painting Gate B into a corner.
Source of truth above this file: MVP_SPEC.md, AGENT_DEVELOPMENT_SPEC.md.

---

## 1. Runtime model

**Single process, single UI thread (Qt event loop).** No asyncio, no worker
threads in Gate A.

- All UI, animation, interaction, and behaviour logic run on the Qt main
  thread, driven by `QTimer`s.
- SQLite writes are synchronous on the main thread but **debounced** (see §6).
  Write volume in Gate A is trivial (position, settings); WAL mode keeps
  writes sub-millisecond.
- The future local LLM is a **separate OS process** managed via `QProcess`
  (Gate B/C). It never shares the GUI thread. This is the only planned
  concurrency seam.

*Rationale:* one thread eliminates the entire class of Qt cross-thread bugs;
Gate A workload cannot saturate it. Threads are added only when a measured
need appears (soak test, §9).

**Timers:**

| Timer | Period | Purpose |
|---|---|---|
| render tick | 33 ms (~30 fps) | time-based frame selection + repaint |
| behaviour tick | 1000 ms | emits `TickElapsed`; idle/annoyance decay |
| persist debounce | 1000 ms, restartable | flush dirty state to SQLite |

Time-based frame selection (clip start time + elapsed → frame index) rather
than one timer per frame: robust to event-loop hiccups, no timer churn.

---

## 2. Module map and dependency direction

```text
src/willy/
├── app/            application controller, wiring, main()        (Lead)
├── contracts/      events, commands, DTOs, enums, protocols      (Lead)
├── platform/       Windows/Qt shell: window, tray, monitors      (Platform)
├── ui/window/      transparent Willy window widget               (Platform)
├── ui/tray/        tray icon + menu                              (Platform)
├── animation/      manifests, loading, mirroring, controller     (Animation)
├── assets_runtime/ pixmap cache, asset validation                (Animation)
├── core/           interaction state, behaviour engine (Gate B)  (Character)
├── persistence/    SQLite, repositories, migrations              (Character)
└── (den/ folders/ conversation/ llm/ …)                          (Gate B+)
```

**Allowed imports (strict):**

```text
app            → everything (composition root)
platform, ui   → contracts only
animation      → contracts, assets_runtime
assets_runtime → contracts only
core           → contracts, persistence
persistence    → contracts only
contracts      → stdlib only
```

No module imports a sibling's internals. Cross-module effects travel as
events/commands through the bus (§3). `app/` is the only place where concrete
implementations are constructed and connected.

---

## 3. Event bus

**Synchronous, in-process, typed pub/sub on the main thread.**

- Events are frozen dataclasses (see INTERFACES.md). Subscription is by exact
  event type: `bus.subscribe(DragEnded, handler)`.
- `publish()` dispatches immediately, in subscription order. Handlers must be
  fast (<1 ms guideline) and must not publish re-entrantly more than one level
  deep (bus raises on depth > 3 to catch loops).
- No queues, no threads, no priorities in Gate A. The bus interface
  (`EventBus` protocol) is what's stable; the implementation can gain a
  deferred-dispatch queue in Gate B without touching callers.

*Rationale:* the MVP spec's event-flow diagram needs a bus eventually; a
30-line synchronous one gives Gate A the seam at near-zero cost.

---

## 4. Deterministic flow (target shape, Gate A slice)

Full Gate B pipeline (per MVP spec §7.1):

```text
sensors/user/timers → EventBus → ContextAggregator → WillyState
        → BehaviourEngine → ProposalValidator → ActionScheduler
        → sinks: Animation | Dialogue | Audio | Persistence
```

**Gate A implements only the thin slice:** platform publishes interaction
events; a small `InteractionController` (in `core/`) maps them to
`PlayAnimation` / position-save commands. No scoring, no novelty, no
dialogue. But everything already flows *event → decision → command → sink*,
so the Gate B behaviour engine slots in as a replacement decision stage, not
a rewrite.

**Separation guarantees (enforced by import rules + review):**

- `platform`/`ui` never mutate character state; they only publish events and
  execute the animation/window commands handed to them (`PlayAnimation`,
  `SetWindowPosition`, `SetVisibility`).
- `animation` never decides *why*; it only plays what it's told and reports
  `AnimationFinished`.
- Decision code (`core`) never touches Qt types. It consumes events, emits
  commands. This is what keeps the deterministic system testable with a fake
  clock and what keeps the future LLM output as *proposals only*.
- LLM seam (Gate B): generated output enters the pipeline **only** as a
  `BehaviourProposal` into the validator — never as direct calls.

---

## 5. Animation subsystem

- One canonical direction (right-facing) on disk; horizontal mirror generated
  at load, anchors x-transformed, both directions cached (per MVP §28.5–28.6).
- `AnimationManifest` (JSON) per clip: frames, per-frame duration ms, loop,
  `mirror_allowed`, anchors, transition hints. Validated at load; invalid
  manifest → hard error in dev, fallback-to-idle in release.
- `AnimationController` is a small state machine: current clip, priority-based
  interruption (`REACTION > INTERACTION > AMBIENT > IDLE`), default
  return-to-idle on clip end, missing-asset fallback = static idle pose.
- Rendering: `QPixmap` on a transparent `QWidget`, `Qt.FastTransformation`
  (nearest-neighbour) everywhere; integer scale factors only.

---

## 6. Persistence

**One SQLite file** at `%APPDATA%/WillyDesktop/willy.db`, WAL mode,
`synchronous=NORMAL`. Everything (settings included) lives here — one atomic,
crash-safe store beats a JSON/DB split (see OPEN_DECISIONS D-1).

Access only via repository protocols (INTERFACES.md). No SQL outside
`persistence/`.

**Gate A schema (v1):**

```sql
CREATE TABLE schema_version (version INTEGER NOT NULL);

CREATE TABLE settings (          -- typed access via SettingsRepository
    key   TEXT PRIMARY KEY,      -- e.g. 'audio.muted', 'window.always_on_top'
    value TEXT NOT NULL          -- JSON-encoded scalar/object
);

CREATE TABLE willy_state (       -- singleton row, id always 1
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    pos_x       INTEGER NOT NULL,        -- virtual-desktop coords
    pos_y       INTEGER NOT NULL,
    screen_name TEXT    NOT NULL,        -- QScreen.name() at save time
    facing      TEXT    NOT NULL,        -- 'left' | 'right'
    updated_at  TEXT    NOT NULL         -- ISO-8601 UTC
);
```

Reserved for Gate B (created empty in v1 so migrations stay linear):
`novelty`, `memories`, `relationship`. Columns defined when their gate starts.

**Write policy:** state marked dirty → debounce timer → single UPDATE.
Forced flush on `aboutToQuit`. Corrupt/missing DB at startup → recreate with
defaults, log warning, never crash (Gate A criterion 10: app always launches).

Migrations: numbered scripts applied by `schema_version`; forward-only.

---

## 7. Platform layer (Windows specifics, isolated)

- Window: `Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint`
  (last one toggleable), `WA_TranslucentBackground`,
  `WA_ShowWithoutActivating` — never steals keyboard focus.
- Click-through mode: **deferred past Gate A** (OPEN_DECISIONS D-4); the
  settings key is reserved.
- Monitors: position stored in virtual-desktop coordinates + screen name.
  On restore or `QGuiApplication.screenAdded/Removed`: if saved screen absent
  or point off all screens → clamp onto primary screen's available geometry.
- DPI: Qt 6 per-monitor DPI awareness is default; sprites use integer scaling
  only, chosen per screen scale factor.
- Any raw Win32 call lives in `platform/win32.py` behind a plain-Python
  interface; nothing else imports `ctypes`.

---

## 8. Settings, tray, and product-restriction enforcement

- Tray menu: Mute, Pause animations, Hide/Show, Reset position, Exit. Each
  publishes a `TrayCommandIssued` event; `app` routes it. Mute/hide effect is immediate
  (Gate A criterion 7).
- Product restrictions (no file modification, no input automation, no
  screenshots/keystrokes, no health advice) are structural: no module has
  code paths for them, `contracts` contains no command that could express
  them, and QA adds static checks (grep-level) for forbidden APIs
  (`pyautogui`, `keyboard`, `SendInput`, file writes outside
  `%APPDATA%/WillyDesktop`).

---

## 9. Testing architecture (summary; details in TESTING.md later)

- `contracts` and `core`: pure unit tests, fake clock, fake bus recorder.
- `animation`: golden-image mirror tests, manifest validation, transition
  table tests — all headless (`QPixmap` works with `QGuiApplication`
  offscreen platform).
- `platform`: thin; covered by `pytest-qt` smoke tests + manual checklist
  (monitor unplug cannot be automated reliably — human step in Gate A
  acceptance).
- Soak harness (`tools/test_harness/`): drives synthetic events for a
  simulated multi-hour session at accelerated fake-clock time; asserts no
  unbounded memory growth, no animation-state deadlock.
- CI: `pytest`, `ruff check`, `ruff format --check` on every PR (GitHub
  Actions, windows-latest).

---

## 10. Decision log (Gate A)

| # | Decision | Rationale |
|---|---|---|
| 1 | Single Qt thread, no asyncio | Gate A load is trivial; removes concurrency bug class |
| 2 | Synchronous typed event bus | Needed seam per spec §7.1; 30 lines now, upgradable later |
| 3 | LLM as future subprocess via QProcess | Crash/timeout isolation; keeps "must work without LLM" trivially true |
| 4 | One SQLite file incl. settings | Single crash-safe store; repos hide it (fork noted, D-1) |
| 5 | Time-based frame selection, 30 fps render tick | Hiccup-robust, no per-frame timers |
| 6 | Right-facing canon + load-time mirror in Gate A | Walk animation needs facing; cost is low, spec mandates it eventually |
| 7 | Virtual-desktop coords + screen name for position | Simplest scheme that survives monitor changes with clamp fallback |
| 8 | Restrictions enforced structurally + QA static checks | Cheaper and stronger than runtime guards |
| 9 | Python 3.13, PySide6 ≥ 6.7 pinned | Current stable (pin moved from 3.12, 2026-07-13; see D-10); per-monitor DPI mature in Qt 6 |
| 10 | Recreate-on-corrupt DB, never block launch | Gate A criterion 10 |

Forward-compatibility seams deliberately left (and nothing more):
`BehaviourProposal` DTO defined now; empty Gate B tables; bus interface;
`contracts` as the only shared surface.
