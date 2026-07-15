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
  wiring do not. **Not the same idea as the dragging-animation expansion
  below (D-18)** — this one is a post-drop reaction; D-18's "annoyed
  dangle" is a mid-drag pose. They could eventually stack.

## 2026-07-15 — dragging-animation expansion, scoped but not scheduled

Follow-up to the `willy_dragged_by_cursor_rough.png` reference sheet flagged
in the asset factory's `HANDOFF.md`. Scoping conversation held with the user
2026-07-15 — full technical scope in `OPEN_DECISIONS.md` **D-18**. Summary:
swing-motion dangle + annoyed dangle (anger-spark icon) are in scope as two
new escalation tiers on the existing drag loop, triggered by combined
hold-duration + swing-intensity (whichever crosses its threshold first);
ground-resist/floor-drag is explicitly deferred pending its own scoping
conversation. Scheduled for **after A-12** — no code or art yet. Pull this
into a real backlog entry (Gate B backlog file doesn't exist yet) once it's
actually next up.
- ~~**Tier-1 click reaction is too strong.**~~ **Resolved:** swapped tier 1
  from `willy_surprised` to a new front-facing turn sequence
  (`willy_front_enter`/`idle`/`leave`). Turned out the concept sheet's
  "FRONT" pose had already been extracted and animated in the asset
  factory's raw pipeline output — it just never got bridged/exported to
  Gate A. No new art generation needed; see `OPEN_DECISIONS.md` D-17.
- **The front-facing ↔ side-view transformation could be smoother — still
  unsolved, one fix attempted and reverted.** `willy_front_leave` was
  extended from 4 to 8 frames (via `codex_requests/done/
  willy_front_leave_smoothing.md`) to end on a real side profile instead
  of a 3/4 angle. Live-tested: it made the transition read as *more*
  shapeshifting, not less, so it was reverted back to 4 frames — see
  `OPEN_DECISIONS.md` D-17 and the asset factory's `README.md` failure
  #25 for the full story. Whatever the eventual fix is, it isn't "just
  add more in-between frames." Still open, still a detail for later
  stages — the *enter* side (and any other front/side transition) is
  untouched too.
