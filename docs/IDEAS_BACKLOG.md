# Willy Desktop — IDEAS_BACKLOG.md

Ideas and observations that come up while live-testing on the real
desktop, captured as they happen instead of getting lost in chat. This is
**not** a decision log (see `OPEN_DECISIONS.md` for those) and not a
committed backlog item (see `GATE_A_BACKLOG.md` for the current gate) —
just a parking lot. Pull an idea into a real backlog entry once it's
actually scheduled; leave it here until then.

Current gate (Gate A) explicitly excludes den/folders/LLM/narrative — see
`CLAUDE.md`. Ideas that need those are logged here for whichever later
gate picks them up, not for Gate A.

---

## 2026-07-14 — from live-testing A-08 (click reactions)

- **A "fuming"/enraged tier beyond smug.** Current tiers top out at 6+
  clicks → `willy_smug`. Idea: a further tier for sustained/extreme
  provocation with a visibly angrier pose. **Art now exists:**
  `willy_fuming` (generated via `codex_requests/willy_fuming.md`,
  12 frames, one-shot `REACTION`) is copied into `assets/manifests/` but
  **not wired into any behaviour yet** — scheduling the actual tier
  (threshold, decay interaction with the existing 1/3/6 tiers) is still
  open.
- **Extreme annoyance sends Willy off-screen to his den/folder.** Instead
  of (or in addition to) a fuming pose, sustained high annoyance could
  make Willy walk off the edge of the screen and "go home" for a while.
  Depends on the den/folder system, which doesn't exist yet — this is a
  Gate B+ idea (folders are explicitly out of scope for Gate A), and
  would also need a walk-off animation/exit behaviour and a way for him
  to later reappear.
- **Willy becomes "fuming" after being dragged and dropped too often.**
  A drag-specific escalation, distinct from the click-annoyance tiers —
  repeated drag/drop cycles in a short span would need their own tracked
  count (drag currently has no annoyance/frequency tracking at all). Art
  (`willy_fuming`, see above) now exists; the drag-frequency tracking and
  wiring do not.
- ~~**Tier-1 click reaction is too strong.**~~ **Resolved:** swapped tier 1
  from `willy_surprised` to a new front-facing turn sequence
  (`willy_front_enter`/`idle`/`leave`). Turned out the concept sheet's
  "FRONT" pose had already been extracted and animated in the asset
  factory's raw pipeline output — it just never got bridged/exported to
  Gate A. No new art generation needed; see `OPEN_DECISIONS.md` D-17.
- ~~**The front-facing ↔ side-view transformation could be smoother.**~~
  **Resolved for the leave→reaction handoff:** `willy_front_leave`
  extended from 4 to 8 frames (via `codex_requests/
  willy_front_leave_smoothing.md`) so it now ends on a real side profile
  instead of a 3/4 angle. The broader idea (the *enter* side, and any
  other front/side transition) is still just a polish note, not
  scheduled.
