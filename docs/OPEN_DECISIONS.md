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

**D-13: "smug" pose.** MVP §6.2 lists smug among Gate A core visible states,
but §29's essential-pose list omits it — an internal MVP inconsistency.
Treated as required (the explicit Gate A list wins); `willy_smug` is already
exported by the asset factory, so nothing to do. Recorded 2026-07-13 to
prevent future "is smug canon?" churn.

**D-14: Base sprite scale 2×.** (2026-07-14, user decision after live demo.)
Native art (~90 px) is too quiet for a character meant to demand attention.
Runtime renders at a base integer scale of 2 (nearest-neighbour, via the
pixmap cache); A-10 multiplies this by the per-monitor DPI factor. Anchors
stay in native pixel coordinates. Crude in-betweens being more visible at 2×
is an art-iteration item for the factory, not a runtime concern.

**D-15: Floor gravity on drop.** (2026-07-14, user decision after live demo;
parameters salvaged from the retired lab, `docs/reference/
willy_behaviors_lab.json`.) Willy lives on a ground line (bottom of the
current screen's available geometry): releasing a drag starts a gravity fall
(900 px/s²) stepped by the render tick; `DragEnded` is published at *impact*,
so the landing clip plays when he hits the floor — no contract change needed.
Launch snaps him to the floor (x restored exactly; y is derived). Deliberate
trade-off: mid-screen parking is gone — a hovering boar was conceptually
wrong, and Gate B floor-walking needs the ground line anyway. Gate A
criterion 4 ("position survives restart") is interpreted as: x within 1 px,
y = floor. Implementation note found while building this: since clips can
have different frame heights, a grounded (not falling, not dragging) Willy
is re-snapped to the floor line whenever his sprite changes size — otherwise
switching poses at rest would make him drift off the ground.

**D-16: Startle reaction at fall start.** (2026-07-14, user decision — the
"extra distressed frame" remembered from an earlier build.) The retired lab
had three separate drag poses (`dangle`/`fall`/`land`); Gate A only shipped
two (`willy_dragged`, `willy_drop_landing`). `willy_surprised` — already
exported, checklist-required by MVP §6.2, previously unused anywhere — fills
the missing middle: releasing a drag plays it once (REACTION), and if the
fall is still going when it finishes, `willy_dragged` resumes for the rest
of the drop (via the same "finished-handler play() wins over idle" seam
A-06 already has — no controller change needed). A very short release near
the floor lands instantly and skips the startle entirely, since there is
nothing to interrupt.
