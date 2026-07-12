# Willy Desktop — GATE_A_BACKLOG.md

Sequenced task briefs for Gate A (Desktop Creature Foundation). Work
top-to-bottom unless marked PARALLEL. Each task ≈ one focused Claude Code
session. Global rules in CLAUDE.md apply to every task and are not repeated.

Sequencing overview:

```text
A-01 (serial, first)
  ├── A-02 persistence      ┐
  ├── A-03 window           ├─ PARALLEL group 1
  └── A-04 asset runtime    ┘
        ├── A-05 mirroring  ┐
        └── A-06 anim ctrl  ├─ PARALLEL group 2 (both need A-04 only)
A-07 drag/drop        (needs A-02, A-03, A-06)
A-08 click reactions  (needs A-07)          ┐
A-09 tray controls    (needs A-03, A-06)    ├─ PARALLEL group 3
A-10 monitors + DPI   (needs A-07)          ┘
A-11 soak + perf harness (fixtures after A-01; final run after A-10)
A-12 Gate A acceptance run (last, serial)
```

Asset prerequisite (human, not an agent task): exported PNGs for standing
idle, idle-blink frames, walk frames, sitting, lying, sleeping, waking,
annoyed, smug, surprised, dragged, drop-landing — right-facing, per MVP §29.
A-04 starts with placeholder rectangles if art is late; A-12 requires real
art.

---

## A-01: Repository scaffold and contracts package

**Goal.** `python -m willy` launches and exits cleanly (blank stub);
`pytest` and Ruff run green; contracts package exists exactly as
INTERFACES.md defines.

**Owned paths.** Whole repo (one-time scaffold): `pyproject.toml`,
`src/willy/` skeleton, `src/willy/contracts/`, `tests/`, `.github/workflows/`,
`AGENTS.md`, `CLAUDE.md`, `docs/`.

**Forbidden paths.** None (first task), but create no feature logic.

**Requirements.**
- Layout per ARCHITECTURE.md §2; empty `__init__.py` stubs for Gate A modules.
- `contracts/` implemented verbatim from INTERFACES.md (enums, events,
  commands, DTOs, protocols) + the 30-line synchronous `EventBus`
  implementation with re-entrancy guard.
- `pyproject.toml`: Python 3.12, PySide6 pinned ≥6.7, pytest, pytest-qt,
  Ruff config (line length 100).
- CI workflow: pytest + ruff on windows-latest.
- Copy MVP_SPEC.md and AGENT_DEVELOPMENT_SPEC.md into `docs/`; add
  ARCHITECTURE.md, INTERFACES.md.

**Exclusions.** No window, no rendering, no persistence, no assets.

**Acceptance criteria.**
- `python -m willy --version` prints version and exits 0.
- All standard commands run green locally and in CI.
- `contracts` imports nothing beyond stdlib (test-enforced).

**Required tests.** Bus subscribe/publish order; bus re-entrancy guard;
DTO frozen-ness; contracts stdlib-only import check.

**Dependencies.** None.

---

## A-02: SQLite persistence and settings  *(PARALLEL group 1)*

**Goal.** Settings and Willy position survive process kill (crash-safe);
first run creates defaults; corrupt DB never blocks launch.

**Owned paths.** `src/willy/persistence/`, `tests/persistence/`.

**Forbidden paths.** `src/willy/contracts/`, `src/willy/platform/`,
`src/willy/ui/`, `src/willy/animation/`.

**Requirements.**
- DB at `%APPDATA%/WillyDesktop/willy.db` (path injectable for tests); WAL,
  `synchronous=NORMAL`.
- Schema v1 per ARCHITECTURE.md §6 incl. empty reserved tables; forward-only
  numbered migrations keyed on `schema_version`.
- Implement `WillyStateRepository` and `SettingsRepository` protocols.
- Corrupt/missing DB → back up bad file, recreate defaults, log warning.
- Debounced writer utility (flush interval injectable; forced `flush()`).

**Exclusions.** No Qt imports; no memory/relationship/novelty logic.

**Acceptance criteria.**
- Kill -9 between debounced writes loses at most the last interval, never
  corrupts.
- First run yields defaults without error; corrupted file path proven by test.

**Required tests.** Round-trip both repos; migration from empty; corrupt-file
recovery; debounce timing with fake clock; concurrent-open (second instance
read) does not deadlock.

**Dependencies.** A-01.

---

## A-03: Transparent frameless window with static Willy  *(PARALLEL group 1)*

**Goal.** A static Willy PNG floats on the desktop with per-pixel
transparency, ignores keyboard focus, and can be shown/hidden
programmatically.

**Owned paths.** `src/willy/platform/`, `src/willy/ui/window/`,
`src/willy/app/` (composition wiring only), `tests/platform/`.

**Forbidden paths.** `src/willy/contracts/`, `src/willy/animation/`,
`src/willy/persistence/`, `src/willy/core/`.

**Requirements.**
- Flags per ARCHITECTURE.md §7; `WA_TranslucentBackground`;
  `WA_ShowWithoutActivating`; always-on-top toggleable via
  `SetVisibility`/settings key (wiring in `app`).
- Window sized to sprite; hit area = sprite bounding box (pixel-perfect mask
  is an A-08 nicety, not required here).
- Executes `SetWindowPosition` and `SetVisibility` commands.
- Publishes `AppStarted`, `ShutdownRequested` on the bus.
- Any Win32 call isolated in `platform/win32.py`.

**Exclusions.** No dragging, no animation, no tray, no persistence hookup,
no click-through.

**Acceptance criteria.**
- Willy visible over other windows with clean alpha edges.
- Typing in another app is never interrupted when Willy appears (manual
  check: focus stays put).
- No taskbar entry.

**Required tests.** pytest-qt: window flags set; show/hide commands take
effect; offscreen smoke launch/quit. Manual checklist entries recorded in the
completion report for focus behaviour.

**Dependencies.** A-01.

---

## A-04: Asset manifests and pixmap runtime  *(PARALLEL group 1)*

**Goal.** Animation clips defined by JSON manifests load, validate, and cache
as pixmap sequences; bad manifests fail loudly with precise errors.

**Owned paths.** `src/willy/animation/` (loading/validation half),
`src/willy/assets_runtime/`, `assets/manifests/`, `tests/animation/`.

**Forbidden paths.** `src/willy/platform/`, `src/willy/ui/`,
`src/willy/core/`, `src/willy/persistence/`.

**Requirements.**
- Parse `AnimationManifest` from JSON; validate: ≥1 frame, durations > 0,
  files exist, anchors in-bounds, `source_direction == RIGHT` for canon
  assets.
- Pixmap cache keyed (asset_id, facing); nearest-neighbour only.
- Missing-asset fallback: registered static idle pose; loader never raises in
  release mode (returns fallback + logged error), strict mode raises for
  tests/dev.
- Write manifests for the Gate A pose/animation list (placeholder PNGs
  acceptable).

**Exclusions.** No playback timing, no mirroring (A-05), no rendering widget.

**Acceptance criteria.**
- All Gate A manifests validate; a deliberately broken manifest produces an
  error naming file + field.
- Loading each asset twice hits the cache (test-observable).

**Required tests.** Valid/invalid manifest matrix; fallback path; cache
reuse; anchor bounds validation.

**Dependencies.** A-01.

---

## A-05: Runtime sprite mirroring and anchor transforms  *(PARALLEL group 2)*

**Goal.** One right-facing canonical sprite displays facing left with
pixel-exact mirroring and correctly transformed anchors.

**Owned paths.** `src/willy/animation/`, `assets/manifests/`,
`tests/animation/`.

**Forbidden paths.** `src/willy/core/`, `src/willy/persistence/`,
`src/willy/platform/`, `src/willy/ui/`.

**Requirements.**
- Exact horizontal mirror preserving alpha; `x' = width - 1 - x` for all
  anchors; `y` unchanged.
- Mirror computed once per load; both facings cached.
- `mirror_allowed=False` assets served unmirrored for either facing.
- No smoothing anywhere in the pipeline.

**Exclusions.** Behaviour selection, artwork creation, UI, new animations.

**Acceptance criteria.**
- Mirrored image equals numpy/pixel-loop reference mirror exactly.
- Ground anchor y unchanged; mouth/rear_effect x transformed per formula.
- Second facing request performs zero image operations (cache hit).

**Required tests.** Pixel-exact mirror equality; anchor transform table;
neutral-asset passthrough; cache reuse; invalid `source_direction` rejection.

**Dependencies.** A-04.

---

## A-06: Animation controller and rendering  *(PARALLEL group 2)*

**Goal.** Willy visibly animates: idle blink and breathing loop by default;
clips can be interrupted by priority and return to idle when finished.

**Owned paths.** `src/willy/animation/` (controller/render half),
`src/willy/ui/window/` (paint integration), `tests/animation/`.

**Forbidden paths.** `src/willy/core/`, `src/willy/persistence/`,
`src/willy/platform/` (except the agreed paint hook in the window widget).

**Requirements.**
- 33 ms render tick; time-based frame selection from clip start (fake-clock
  testable; timing logic Qt-free).
- Implements `AnimationController` protocol; consumes `PlayAnimation`,
  `SetPaused`; publishes `AnimationFinished`.
- Priority interruption per `AnimationPriority`; equal priority replaces;
  lower is ignored.
- Non-loop clip end → auto return-to-idle.
- Pause freezes current frame; resume continues without jump.

**Acceptance criteria.**
- Idle blink loops indefinitely without drift (soak-testable).
- REACTION clip interrupts walk; on finish, idle resumes.
- Pause/resume leaves no visual glitch; frame index deterministic under fake
  clock.

**Required tests.** Frame selection vs fake clock (incl. hiccup: 500 ms gap
→ correct frame, no crash); priority matrix; return-to-idle;
`AnimationFinished` emission; pause semantics.

**Dependencies.** A-04 (A-05 merges in whenever ready; controller is written
against the cache API, facing-agnostic).

---

## A-07: Drag, drop, and position persistence

**Goal.** User drags Willy (dedicated dragged pose), drops him (landing
reaction), and his position — including facing — survives app restart.

**Owned paths.** `src/willy/platform/`, `src/willy/ui/window/`,
`src/willy/core/` (new `InteractionController`), `src/willy/app/`,
`tests/platform/`, `tests/core/`.

**Forbidden paths.** `src/willy/contracts/`, `src/willy/animation/`
(consume via protocol only), `src/willy/persistence/` internals (repos only).

**Requirements.**
- Window layer: left-press+move → drag; publishes `DragStarted`,
  `DragEnded`; window follows cursor with grab-point offset.
- `InteractionController` (Qt-free): `DragStarted` → `PlayAnimation(dragged,
  REACTION)`; `DragEnded` → landing clip, then idle; marks state dirty.
- Position + facing saved via `WillyStateRepository` (debounced + flush on
  quit); restored on launch; facing flips toward drag direction.
- Rapid drag-drop-drag sequences never wedge the animation state machine.

**Exclusions.** Multi-monitor edge handling (A-10), click reactions (A-08).

**Acceptance criteria.**
- Drag shows dragged pose within one render tick; drop plays landing then
  idle.
- Restart restores position within 1 px and facing exactly (Gate A
  criterion 4).
- 20 rapid drag/drop cycles end in idle, correct position.

**Required tests.** InteractionController event→command mapping (pure, fake
bus/clock); persistence round-trip through real repo with temp DB; pytest-qt
drag simulation smoke; rapid-cycle state machine test.

**Dependencies.** A-02, A-03, A-06.

---

## A-08: Click reactions and annoyance escalation  *(PARALLEL group 3)*

**Goal.** Left click → small contextual reaction; repeated clicking →
visibly increasing annoyance; annoyance decays with time.

**Owned paths.** `src/willy/core/`, `src/willy/ui/window/` (click publishing
only), `tests/core/`.

**Forbidden paths.** `src/willy/contracts/`, `src/willy/animation/`,
`src/willy/persistence/`, `src/willy/platform/`.

**Requirements.**
- Window publishes `WillyClicked` with rolling 10 s click count.
- `InteractionController`: thresholds map count → reaction tier
  (e.g. 1–2: surprised/curious; 3–5: annoyed; 6+: smug refusal/turn away) —
  exact clips per available art; tiers data-driven, not hard-coded.
- Decay via `TickElapsed`; no persistence of annoyance (session-only in
  Gate A).
- Reactions use INTERACTION priority (dragging still wins).
- Right click reserved: publishes event, no menu yet (context menu is not a
  Gate A criterion; note as Gate B).

**Exclusions.** Dialogue text, audio, context menu contents, double-click
panel.

**Acceptance criteria.**
- Distinct reaction tiers observable; annoyance resets after quiet period.
- Click spam (10/s for 30 s) causes no crash, no queue buildup, no stuck
  animation.

**Required tests.** Tier mapping table (pure); decay with fake clock; spam
simulation via fake bus; priority interaction with drag.

**Dependencies.** A-07.

---

## A-09: System tray controls  *(PARALLEL group 3)*

**Goal.** Tray icon with Mute, Pause, Hide/Show, Reset position, Exit — each
acts immediately and persists where applicable.

**Owned paths.** `src/willy/ui/tray/`, `src/willy/app/`, `tests/platform/`.

**Forbidden paths.** `src/willy/core/`, `src/willy/animation/` internals,
`src/willy/contracts/`.

**Requirements.**
- Tray menu publishes `TrayCommandIssued`; `app` routes: mute → `SetMuted`
  (stub sink logs; no audio exists yet) + settings; pause → `SetPaused`;
  hide → `SetVisibility` + settings; reset → `SetWindowPosition(primary
  screen center)`; exit → clean shutdown with persistence flush.
- Checkable menu items reflect persisted state on relaunch.
- Exit path: flush, close window, stop timers, exit 0.

**Exclusions.** Settings dialog, quiet hours, any audio playback.

**Acceptance criteria.**
- Hide/mute take effect immediately (Gate A criterion 7); state survives
  restart.
- Exit leaves no orphan process; reset recovers an off-screen Willy.

**Required tests.** Command routing (pure); settings persistence of toggles;
pytest-qt tray action trigger smoke; shutdown flush ordering.

**Dependencies.** A-03, A-06 (pause), A-02 (persist toggles).

---

## A-10: Multi-monitor support, recovery, and high-DPI  *(PARALLEL group 3)*

**Goal.** Willy survives monitor unplug/replug and mixed-DPI setups: never
lost off-screen, sprites stay crisp at every scale factor.

**Owned paths.** `src/willy/platform/`, `tests/platform/`.

**Forbidden paths.** `src/willy/core/`, `src/willy/animation/` (may call
scale API only), `src/willy/contracts/`.

**Requirements.**
- Subscribe to `QGuiApplication` screen add/remove; publish
  `ScreenLayoutChanged`.
- Restore/relocate rule per ARCHITECTURE.md §7: saved screen missing or
  point off all screens → clamp to primary available geometry, save new
  position.
- Integer sprite scale per screen scale factor (1x at ≤1.25, 2x at ≥1.5 —
  tune by eye); nearest-neighbour.
- Drag between monitors keeps grab offset; position saved with new screen
  name.

**Exclusions.** Per-monitor behaviour differences, window snapping.

**Acceptance criteria.**
- Simulated layout change with saved position on removed screen → Willy on
  primary, fully visible (automated with fake geometry provider).
- Manual: unplug real monitor while Willy is on it → he reappears on primary
  (Gate A criterion 5); crisp pixels at 100 % and 150 % scaling.

**Required tests.** Clamp logic matrix (pure, fake geometries); restore with
missing screen; scale-factor selection; drag-across-boundary position save.

**Dependencies.** A-07.

---

## A-11: Soak harness and performance checks  *(QA-owned)*

**Goal.** Automated evidence for Gate A criteria 1, 2, 8, 9: multi-hour
stability, responsive animation, sane CPU/memory.

**Owned paths.** `tools/test_harness/`, `tests/simulation/`,
`.github/workflows/`, `docs/testing/`.

**Forbidden paths.** All `src/willy/` (testability tweaks go through owning
agent as micro-tasks).

**Requirements.**
- Fake-clock simulation: 8 h of synthetic events (ticks, clicks, drags,
  layout changes) against real core + animation timing logic, headless.
- Real-time mini-soak: 30 min offscreen run in CI; assert RSS growth
  < 20 MB and no unhandled exceptions.
- Local profiling script reporting idle CPU % and RSS; thresholds: idle CPU
  < 2 % on dev machine, RSS < 150 MB.
- Static forbidden-API check (pyautogui/keyboard/SendInput/file writes
  outside app dir) wired into CI.
- Regression-report template in `docs/testing/`.

**Exclusions.** Installer/packaging (post-Gate-A), OS-level UI automation.

**Acceptance criteria.**
- 8 h simulated session: zero exceptions, animation state machine never
  wedged, bounded memory.
- CI runs simulation + mini-soak on every PR to main.

**Required tests.** The harness *is* the test; plus unit tests for the fake
event generator.

**Dependencies.** Fixtures can start after A-01; final thresholds run after
A-10.

---

## A-12: Gate A acceptance run  *(serial, last)*

**Goal.** Documented pass/fail against all 10 Gate A criteria (MVP §6.4),
with evidence, using final art.

**Owned paths.** `docs/testing/GATE_A_REPORT.md`.

**Forbidden paths.** All source (fixes become new bounded tasks).

**Requirements.**
- Execute checklist mapping each of the 10 criteria to: automated evidence
  (test/soak output) or manual procedure + observed result.
- 4 h real-run on the human's machine (criterion 1) — human performs, agent
  prepares instructions and collects logs.
- List every deviation; open a fix task per failure; rerun after fixes.

**Exclusions.** New features, packaging.

**Acceptance criteria.** Report shows all 10 criteria green with evidence;
human signs off; `main` tagged `gate-a`.

**Required tests.** Full suite green at the release commit.

**Dependencies.** A-01…A-11 complete; final art imported.
