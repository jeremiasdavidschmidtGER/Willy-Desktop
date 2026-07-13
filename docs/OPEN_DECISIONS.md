# Willy Desktop — OPEN_DECISIONS.md

Decisions made where the source docs were silent/ambiguous. Each has a
recommended default already baked into ARCHITECTURE/INTERFACES/BACKLOG.
Only D-1, D-4, D-5 are genuine forks where your input changes work; the rest
are recorded for the ADR trail.

## Genuine forks — want your call before A-02/A-05

**D-1: Settings storage — SQLite (default) vs JSON file.**
Default: everything in the single SQLite DB (crash-safe, one store, one
backup/erase path — helps the later "erase everything" control).
Alternative: settings in an atomically-written JSON file (human-editable,
debuggable without tooling; DB keeps only state). Cost of switching later:
low. Pick before A-02.

**D-4: Click-through mode.**
Gate A's required-feature list doesn't include it, but the Platform agent's
responsibility list does. Default: **defer past Gate A**; reserve the
settings key. If you want it in Gate A, it's Win32 `WS_EX_TRANSPARENT`
toggling (Qt's `WA_TransparentForMouseEvents` alone is insufficient for a
top-level transparent window) — roughly half a task added to A-03.

**D-5: Mirroring in Gate A — full (default) vs deferred.**
Gate A only strictly needs a walking Willy; you could ship right-facing-only
and defer mirroring to Gate B. Default: include it (task A-05) — it's cheap,
the spec's example brief already exists, and retrofitting anchors later is
worse. Defer only if art delivery is the bottleneck.

## Recorded defaults — object only if you disagree

**D-2: Threading.** Single Qt main thread, no asyncio; LLM later as
`QProcess` subprocess. Revisit only if soak tests show main-thread stalls.

**D-3: Position model.** Virtual-desktop coordinates + `QScreen.name()`;
clamp to primary when invalid. Simplest scheme meeting criterion 5. Per-
monitor-relative coords would survive rearrangement better but add ambiguity;
not worth it now.

**D-6: Animation timing.** Single 33 ms render tick + time-based frame
selection (not per-frame timers). Deterministic under fake clock,
hiccup-robust.

**D-7: Event bus semantics.** Synchronous, main-thread, exact-type
subscription, re-entrancy depth cap 3. Queued/async dispatch deferred to
Gate B if needed.

**D-8: Right-click.** Publishes an event but shows no context menu in
Gate A. MVP §6.3 lists the context menu under basic interactions, but the
Gate A acceptance criteria (§6.4) don't test it and tray covers all controls
— flagging as spec-ambition > Gate A need. Menu contents land with Gate B
(den access needs to exist first anyway). Same for the double-click status
panel.

**D-9: Annoyance state.** Session-only in Gate A (not persisted). Emotional
persistence belongs to the Gate B state model; persisting one ad-hoc value
now would prejudge that schema.

**D-10: Python/Qt versions.** Python 3.13, PySide6 pinned ≥ 6.7,
windows-latest CI. Pin moved 3.12 → 3.13 (2026-07-13, user decision): the
original 3.12 rationale was only "current stable"; 3.12 is now in
security-only maintenance, the dev machine runs 3.13, and PySide6 ≥ 6.8
supports it — this removes the recorded A-01 venv/CI version deviation.
Packaging tool (PyInstaller vs Nuitka) deliberately undecided — not needed
until Phase 15.

**D-11: Single-instance guard.** A second launch detects the running
instance (lock file in `%APPDATA%/WillyDesktop/`) and exits with a message.
Cheap, prevents two Willys fighting over the DB; folded into A-03.

**D-12: Asset placeholders.** Backlog tasks A-04…A-11 run on placeholder
PNGs so agent work never blocks on art; A-12 acceptance requires final art.
