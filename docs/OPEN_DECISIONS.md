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

**D-17: Tier-1 click reaction is a front-facing turn, not `willy_surprised`.**
(2026-07-14, user decision after live demo.) A real startle read as
disproportionate for a single friendly click; live feedback wanted Willy to
just turn and look at the user, "expecting interaction." The concept sheet's
FRONT pose turned out to already be extracted and animated in the asset
factory's raw pipeline output (`front/enter`, `idle`, `leave`) — it had just
never been bridged/exported to Gate A. No new art generation was needed;
`pixelpet/gate_export.py`'s `CLIPS` gained `willy_front_enter` (one-shot
turn-to-camera), `willy_front_idle` (looping hold), and `willy_front_leave`
(one-shot turn-back). `InteractionController` runs these as a small state
machine (`_front_state`: none/entering/holding/leaving): tier 1 plays
`enter`, then holds on `idle` for `FRONT_HOLD_SECONDS` (3.0s, first-pass
tuning) driven by `TickElapsed`, then plays `leave` and returns to normal
side-view idle. If annoyance escalates to tier 2/3 while still in the
front-facing sequence, `leave` plays first and the side-view reaction
(`willy_annoyed`/`willy_smug`) is queued to fire once `leave` finishes —
avoiding a jump-cut straight from facing the camera to a side-view pose
(second round of live feedback). `on_drag_started`/`on_fall_started` reset
the front-sequence state, since a real drag (REACTION priority) always
preempts it visually regardless. Known rough edge, tried and reverted:
the `leave` clip's last frame stops at a 3/4 angle, while `willy_annoyed`/
`willy_smug` start at a full side profile — live-confirmed as "a bit
rough." A Codex request (`Python-Test/codex_requests/done/
willy_front_leave_smoothing.md`) extended `leave` 4→8 frames to land on a
genuine side profile; live-tested again, it made the transition read as
*more* shapeshifting, not less, so it was reverted back to the original
4 frames. Recorded as failure/lesson #25 in the asset factory's
`README.md`: a geometrically-correct bridge between two poses isn't the
same as a *good* transition. Broader front/side transition polish stays
logged as a lower-priority, unsolved idea in `docs/IDEAS_BACKLOG.md`.

**D-18: Dragging-animation expansion — scope (not implementation).**
(2026-07-15, user decision, scoping conversation only — no code or art
generated yet.) `Reference Images/willy_dragged_by_cursor_rough.png` (asset
factory) sketches 4 drag-pose variants: calm dangle (shipped, `willy_dragged`),
swing-motion dangle with dust, annoyed dangle with an anger-spark icon, and a
ground-resist/floor-drag pose. Scoped this round:
- **In scope:** swing-motion dangle and annoyed dangle, as two new
  escalation tiers layered onto the existing single-pose `willy_dragged`
  loop (`src/willy/core/interaction.py`), mirroring A-08's
  `REACTION_TIERS` pattern (tuple of ascending thresholds → asset id).
- **Trigger:** combined signal — hold-duration (accumulated drag time,
  tick-driven, same shape as A-08's per-tick decay) and swing-intensity
  (cursor velocity while dragging) — whichever threshold is crossed first
  escalates the tier. Swing-intensity is new contract surface: today
  `WillyWindow` only publishes `DragStarted`/`DragEnded` as facts, not
  per-move velocity, so this needs a new `Event` in
  `src/willy/contracts/events.py` — contracts are read-only for
  implementation agents, so this is a flagged escalation item for whoever
  picks up the actual implementation task. Both signals reset on drag end
  (session-only, no persistence, same spirit as D-9).
- **Distinct from the existing unresolved `willy_fuming` idea** logged in
  `IDEAS_BACKLOG.md` (2026-07-14): that idea reuses the standing
  `willy_fuming` reaction pose as a *post-drop* escalation after repeated
  drag/drop cycles. "Annoyed dangle" here is a different, new dangle-pose
  asset (Willy keeps hanging, but with an anger-spark icon) triggered
  *mid-drag*. The two could eventually stack (mid-drag escalation via
  annoyed dangle, then a `willy_fuming` reaction on drop if still highly
  agitated) but that combination is undecided.
- **Explicitly out of scope this round:** the ground-resist/floor-drag
  pose. Not just a new dangle frame — a different interaction paradigm
  (dragged-along-the-floor vs. hanging-in-air), likely needing new
  event/command shapes comparable in size to a full A-08-style feature.
  Needs its own scoping conversation before any art brief.
- **Timing:** scheduled for **after A-12** (Gate A acceptance run) — not
  Gate A backlog work. No Gate B backlog file exists yet, so this stays
  parked in `IDEAS_BACKLOG.md` until one does.

**D-19: D-18 implementation — the swing tier is horizontal-motion-only,
not symmetric with the annoyed tier.** (2026-07-16, user decision after
live-testing the art + code together, PR #19.) `DragMoved` landed in
`src/willy/contracts/events.py` per D-18's escalation (approved before
editing); `InteractionController` derives a swing-velocity signal from
consecutive `DragMoved` points and a hold-duration signal from
`TickElapsed` while dragging. Two live-test findings changed the
original "combined signal, whichever crosses first" design from D-18:
- **The swing pose's motion curve.** Codex's first cut doubled
  `willy_dragged`'s rotate+dy amplitude ("energetic pendulum arc") —
  live-tested as "wobbles too much." `willy_dragged_swing`'s art (a
  stretched, gliding-looking pose) reads better swung left-right during
  an actual drag than spinning/bobbing in place. Fixed in the asset
  factory (`concept2pet/animate.py`): now a `dx`-driven horizontal
  swing (±14px) with a small phase-locked `rotate` lean, `dy` back near
  the base dangle's level.
- **The trigger must match**, per the same live-test: "this pose must
  be reserved for dragging from left to right only, ... can't be an
  idle hold pose." A motionless hold reaching the old duration
  threshold was escalating to `willy_dragged_swing` even with zero
  cursor movement — visually nonsensical once the art specifically
  depicts real horizontal motion. Fixed asymmetrically rather than
  dropping hold-duration entirely: `willy_dragged_annoyed`'s art has no
  implied motion (an angry static-ish dangle), so a long motionless
  hold reading as "still stuck up here, getting annoyed" is fine — it
  still escalates, but jumps straight to `ANNOYED_DRAG_ASSET_ID`,
  skipping `SWING_ASSET_ID` entirely. `SWING_ASSET_ID` is now reachable
  **only** via horizontal cursor velocity (`abs(dx)/dt`, not total
  displacement — a fast *vertical* shake must not trigger it either).
  `DRAG_HOLD_TIER_SECONDS` (a 2-tuple) became `DRAG_HOLD_ANNOYED_SECONDS`
  (a single scalar); `DRAG_VELOCITY_TIER_PX_S` became
  `DRAG_HORIZONTAL_VELOCITY_TIER_PX_S`.
- Also worth knowing for future single-clip art iterations: a full
  `pixelpet.gate_export` run rebuilds *every* tracked clip from its own
  source frames, which can surface unrelated upstream drift (caught
  `willy_dragged`'s canvas having silently grown 92→102px from some
  earlier, unrelated change while fixing the swing clip — reverted,
  not this task's concern). `pixelpet/gate_export.py` gained a
  `--only <asset_id>` flag (mirroring `bridge.py`'s `--full-one`) so a
  single-clip tuning pass doesn't force-touch everything else.
- **`willy_dragged_annoyed` needed facial movement, not just a static
  angry pose** (live-test 2026-07-16, same PR). Two eye-blinks (frames
  2-3 and 9-10 of the 16-frame loop) are baked in via a new
  `close_largest_light_blob` helper in the factory's
  `pixelpet/gate_export.py` — broader than the existing
  `detect_eye_rect` (which only exact-matches a single palette color
  and missed this pose's two-tone eye rendering, catching the tusk
  instead once widened naively). Leg movement was also requested but
  never produced a convincing result — tried locally (pixel-region
  offset leaves visible seams at a load-bearing joint, unlike an eye's
  small self-contained blob) and handed to Codex (two more approaches,
  neither survived review) — recorded as failure #26 in the asset
  factory's `README.md`. Shipping without leg movement; the pose still
  reads as annoyed via face + blinks.
- **The velocity signal itself was too noisy** (live-test 2026-07-20,
  after the art landed in PR #19): raw per-`DragMoved` instantaneous
  velocity, tracked as a running max, let a single sample spike the
  tier straight to `ANNOYED_DRAG_ASSET_ID` — two events firing a few ms
  apart with an ordinary small cursor jump computes to an unrealistic
  px/s reading from the tiny `dt` alone. `SWING_ASSET_ID` read as
  "hard to trigger" because it was almost always skipped entirely.
  Fixed by replacing the raw max with an EMA (`DRAG_VELOCITY_EMA_ALPHA`,
  `InteractionController`), then tracking the peak of the *smoothed*
  signal — still sticky, still never steps back down mid-drag, but now
  needs sustained fast swinging rather than one noisy sample to
  escalate.
- **Same session, two more findings from watching real dragging.**
  (1) `SWING_ASSET_ID` stayed stuck facing one direction regardless of
  which way the drag actually went — `self._facing` was only ever set
  in `on_drag_ended`, never live during the drag, so a directional pose
  had nothing to follow. Fixed by updating facing from `DragMoved` too,
  with a hysteresis band (`FACING_DRAG_FLIP_THRESHOLD_PX = 20`, much
  wider than the drop-time `FACING_FLIP_THRESHOLD_PX = 2`) so a real
  swing's own oscillation doesn't flicker it every sample; re-dispatches
  the active tier's clip on a flip so the pose actually shows the right
  direction. (2) The EMA fix above wasn't enough on its own — sustained
  fast velocity (not a single noisy sample) still reached
  `ANNOYED_DRAG_ASSET_ID` almost immediately during a real swing, since
  the EMA converges in a handful of samples. Rather than re-tuning
  thresholds a third time, removed the velocity→annoyed path entirely:
  velocity now only ever reaches `SWING_ASSET_ID`, hold-duration is the
  only path to `ANNOYED_DRAG_ASSET_ID` (already confirmed working well
  on its own). Each tier now has exactly one way in — no more shared
  thresholds to keep in balance against each other.
- **Same session, round three: the facing fix above had its own bug,
  plus a new pickup-time false trigger.** (1) The hysteresis reference
  point was anchored at the *last flip* and never moved while travel
  continued in the same direction — reversing after a long swing needed
  pulling back almost the entire swing distance before facing would
  flip, which read as major lag. Fixed by tracking a *trailing
  extremum* (the furthest x reached in the current facing direction)
  instead of a fixed point, so a flip only needs pulling back
  `FACING_DRAG_FLIP_THRESHOLD_PX` from wherever the swing actually
  turned around. (2) `SWING_ASSET_ID` was firing the instant Willy was
  picked up, before any real swinging — the very first `DragMoved` can
  land a fraction of a ms after `DragStarted`'s own timestamp, and
  dividing a real pixel jump by that near-zero `dt` spiked even the
  EMA's first, most-diluted sample past the threshold. Added
  `DRAG_VELOCITY_MIN_DT_S`: samples closer together than this are
  ignored, and the reference point only advances once a sample is
  actually used for a computation (not on every call) — otherwise a
  burst of too-close-together events would keep resetting it and never
  accumulate enough real time to produce a valid reading.
- **`willy_fall` added alongside `willy_surprised` at fall start**
  (2026-07-20, user request after live-testing the fixes above). The
  asset factory's `make_drag.py` had built a `drag/fall` clip (panicked
  wobble, from `Reference Images/generated/willy_falling_0.png`) since
  the drag set was first authored, but it was never bridged to Gate A —
  same situation D-17 found with the front-facing pose. No new
  generation needed; added a `CLIPS` entry and exported. Rather than
  replacing `willy_surprised`, `InteractionController.on_fall_started`
  now picks randomly between the two (`FALL_START_REACTIONS`) via an
  injected `random_choice` callable (`random.choice` by default,
  deterministic in tests) — the same "each tier/reaction has exactly
  one clear trigger" spirit as the earlier fixes, just applied to
  variety instead of escalation.
