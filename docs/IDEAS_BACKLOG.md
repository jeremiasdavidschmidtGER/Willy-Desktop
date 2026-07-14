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
  provocation with a visibly angrier pose. Needs a new art asset (no
  "furious" clip exists yet in `assets/manifests/` or the asset
  factory's exports) before this can be scheduled.
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
  count (drag currently has no annoyance/frequency tracking at all) and
  the same not-yet-existing "furious" pose noted above.
- ~~**Tier-1 click reaction is too strong.**~~ **Resolved same day:**
  swapped tier 1 from `willy_surprised` to a new `willy_front` clip.
  Turned out the concept sheet's "FRONT" pose had already been extracted
  and animated (`front/enter`, a turn-to-face-camera) in the asset
  factory's raw pipeline output — it just never got bridged/exported to
  Gate A. No new art generation needed; see `OPEN_DECISIONS.md` for the
  decision record.
- **The front-facing ↔ side-view transformation could be smoother overall.**
  A detail for later stages, not urgent. The concrete instance already
  has a queued art request (`Python-Test/codex_requests/
  willy_front_leave_smoothing.md` — the leave→annoyed/smug handoff angle
  mismatch), but the broader idea is that any front/side transition
  (entering the front pose too, not just leaving it) could stand a
  visual polish pass once there's real art to do it with.
