# Willy Desktop — GATE_B_BACKLOG.md (first draft, unreviewed)

> **Status: draft for human/Lead Architect review — nothing here is
> scheduled or approved.** Unlike Gate A, where `ARCHITECTURE.md` and
> `INTERFACES.md` were finalized *before* `GATE_A_BACKLOG.md` was written,
> no equivalent Gate B architecture pass has happened yet. The tasks below
> are phase-level (mirroring `MVP_SPEC.md` §32's Phase 4–11), not the fine
> A-01..A-12 granularity Gate A shipped with — expect each to split into
> several smaller tasks once real design work starts, the same way Gate
> A's Phases 1–3 became twelve backlog tasks. Treat task IDs, owned paths,
> and schema sketches here as placeholders to correct, not commitments.
>
> Do not start implementation from this file as-is. See "Before any B-xx
> task starts" below for what has to happen first.

Sequenced task briefs for Gate B (Desktop Willy MVP, `MVP_SPEC.md` §66–85).
Scope boundary per the spec's own `## Phase 11 — Local LLM dialogue` →
`Evaluate Gate B.` marker (§32): B-01 through B-10 below map to Phases
4–11. Phase 12 ("Longer conversation" — Sit with Willy, deeper registers,
current-affairs handling, conversation memory) is **not** included here —
see "Open question: Phase 11/12 boundary" below, it's a genuine fork, not
a settled call.

Everything Gate A's `CLAUDE.md` restricts still applies: no real file
writes outside `%APPDATA%/WillyDesktop/`, no mouse/keyboard automation, no
screenshots/keystroke capture, no health/medical advice, must run fully
without an LLM present, local-first/no cloud dependencies.

## Before any B-xx task starts

1. **Architecture addendum.** `ARCHITECTURE.md` §2's module map already
   reserves `core/ (Gate B)` and `(den/ folders/ conversation/ llm/ …)
   (Gate B+)`, and §6 reserves empty `novelty`, `memories`, `relationship`
   tables — but none of those have real column definitions, module import
   rules, or an LLM-subprocess IPC contract yet. This needs the same kind
   of dedicated design pass ARCHITECTURE.md represents for Gate A, done
   by the Lead Architect with human sign-off, before B-01 can be scoped
   precisely. Candidate contents: den/folder/conversation module
   boundaries + allowed-imports table extension; `QProcess` stdin/stdout
   framing for the local LLM; full schema for `willy_state` extensions,
   `relationship`, `novelty`, `memories`, `den`, `objects`, `narrative`
   (columns per §30); `BehaviourProposal`/`ProposalValidator` real
   validation rules (today: types + pass-through only).
2. **Agent-plan update.** `AGENT_PLAN.md` is explicitly "Gate A only" and
   defers Character/Den/Folder/Conversation agent roles to Gate B start
   (§4). A Gate B version of that file (session roles, task ownership
   table) should exist before parallel work begins.
3. **Art prerequisite.** Per `MVP_SPEC.md` §29: at minimum the essential
   static poses list (3/4 front, back, embarrassed, curious, denial,
   reflective, digging, half-inside-folder, reading, drinking — several
   not yet drawn for Gate A), the digging animation loop, and Stage 1 +
   Stage 2 den backgrounds/furniture/props with at least four den-specific
   Willy poses. Same pattern as Gate A: implementation tasks can start on
   placeholders, but the phase's acceptance criteria need real art.

---

## Sequencing overview

```text
B-01 Willy state + relationship/novelty schema        ┐
B-02 Behaviour engine, scheduler, cooldowns, novelty   ├─ Phase 4
B-03 Authored dialogue bank (no LLM)                   ┘
B-04 Desktop awareness + anti-productivity                Phase 5
B-05 Den (Stage 1) + object persistence                    Phase 6
B-06 Settlement, relationship depth, Stage 2, private acts. Phase 7
B-07 Folder roaming + spatial sound                         Phase 8
B-08 Vice (beer) + identity modes + optional mess            Phase 9
B-09 First Willy incident (Truffle Signal)                    Phase 10
B-10 Local LLM dialogue (short desktop exchanges only)         Phase 11
B-11 Gate B acceptance run                        (serial, last — "Evaluate Gate B")
```

B-01/B-02/B-03 can run parallel once the architecture addendum lands
(same shape as Gate A's parallel groups). B-04 onward each depend on
B-01/B-02 (state model + behaviour engine must exist before anything
scores against them). B-09 needs B-05/B-07 (den + folders, per Truffle
Signal's design). B-10 needs B-02/B-03 (behaviour engine supplies the
non-LLM fallback path the spec requires). B-11 needs all of the above.

---

## B-01: Willy state model extensions + relationship/novelty persistence

**Goal.** The Gate A `willy_state` table and reserved empty
`relationship`/`novelty`/`memories` tables (`ARCHITECTURE.md` §6) get real
schemas and repository protocols for emotional state, relationship
dimensions, slow-changing tendencies, and novelty tracking.

**Owned paths.** `src/willy/persistence/`, `src/willy/contracts/` (new DTOs
— via the architecture addendum's approval, contracts stay lead-owned),
`tests/persistence/`.

**Requirements.**
- Emotional state (§8.2: energy, boredom, curiosity, irritation,
  confidence, sociability, shame, loneliness, nostalgia, privacy desire,
  musical excitement) — hidden values, not shown as a single meter.
- Relationship dimensions (§8.3: familiarity, respect, safety, amusement,
  resentment, intellectual trust, vulnerability willingness, belonging) —
  explicitly not one visible affection bar.
- Slow-changing tendencies (§8.4: drinking frequency, party inclination,
  productivity hostility, reading openness, folder curiosity, apology
  willingness, hardbass preference, War Boar tendency, embarrassment-hiding
  tendency).
- Novelty tracking store (§9.2: last use, daily/weekly count, recent
  dialogue intent/wording/animation/emotional beat/guest/narrative
  structure) with the penalty curve example in §9.2.
- Migration from Gate A's schema forward-only, per existing
  `schema_version` convention.
- Full erasure path: every value here must be coverable by the "clear
  memories"/"reset Willy" privacy controls (§31) — design the repository
  API with a single erase-all call in mind now, don't bolt it on later.

**Exclusions.** No behaviour selection logic (B-02), no UI surface for any
of this — it's pure state + persistence.

**Acceptance criteria.** Round-trip persistence for all new dimensions;
erase-all leaves the schema at defaults; migration from a Gate A-era DB
file succeeds without data loss on the fields that already existed.

**Required tests.** Repository round-trip per dimension group; erase-all;
migration-from-Gate-A fixture; novelty penalty-curve unit tests.

**Dependencies.** Architecture addendum (schema columns approved).

---

## B-02: Behaviour engine, scheduler, cooldowns, novelty manager

**Goal.** The Gate A "thin slice" (`InteractionController` mapping events
directly to commands) gets the real decision stage: a context aggregator
+ behaviour engine that scores candidate actions and emits
`BehaviourProposal`s through the (currently pass-through)
`ProposalValidator`, per `ARCHITECTURE.md` §4's target pipeline.

**Owned paths.** `src/willy/core/` (behaviour engine, scheduler, novelty
manager), `tests/core/`.

**Requirements.**
- Context aggregator: folds `TickElapsed`, desktop-awareness signals
  (B-04), folder events (B-07, once it exists), and Willy state (B-01)
  into whatever shape the behaviour engine scores against.
- Behaviour selection scoring per §9.1: mood, recent activity, relevance,
  relationship state, narrative arc (none exists yet in Gate B — treat as
  a no-op input, real in Gate C), time of day, recent repetition, quiet
  settings, available assets, interruption cooldown, rarity budget.
- Novelty penalties per §9.2's example curve; emotional-rarity protection
  per §9.3 (no repeated profound remarks/apologies/embarrassment/etc. in
  short succession).
- `ProposalValidator` gains real rules (today: pass-through only) — at
  minimum reject proposals with no available asset, apply quiet-hours/
  presentation suppression, and enforce the rarity budget.
- This replaces `InteractionController`'s ad-hoc mapping for *behavioural*
  (non-immediate-interaction) triggers; drag/click/tray handling from
  Gate A stays as-is — this is additive, not a rewrite of A-07/A-08/A-09.

**Exclusions.** No LLM involvement (B-10 is separate and produces
proposals through this same validator, not around it). No den/folder/
vice-specific behaviours yet — those are B-05/B-07/B-08 consumers of this
engine, added incrementally.

**Acceptance criteria.** A fake-clock simulation can run a multi-hour
session and observe: no single behaviour firing more often than its
novelty penalty allows; quiet-hours/presentation suppression actually
suppress; cooldowns are respected under a synthetic event storm (mirrors
Gate A's A-08 click-spam test, generalized).

**Required tests.** Scoring function unit tests per input dimension;
novelty penalty curve; rarity-budget enforcement; validator rejection
paths; fake-clock multi-hour scenario (extends A-11's harness).

**Dependencies.** B-01.

---

## B-03: Authored dialogue bank (LLM-free)

**Goal.** Willy can produce short in-character lines without any LLM —
the spec's "must function without an LLM" requirement (§3.3) needs a real
content bank, not just a stub, since B-10's LLM path explicitly falls back
to this on any failure.

**Owned paths.** `src/willy/core/` (dialogue selection), a new
authored-content directory (naming TBD by architecture addendum — e.g.
`assets/dialogue/`), `tests/core/`.

**Requirements.**
- Static line bank keyed by context (behaviour id, mood, relationship
  tier) with novelty-aware selection reusing B-02's novelty manager so
  the same line doesn't repeat too often.
- Every conversational register the spec requires *some* authored
  coverage for even pre-LLM: casual/comic lines at minimum (Reflective/
  Serious/Withdrawn registers are meaningful once B-10 exists, but a
  authored fallback needs at least a neutral safe line for each).
- No dependency on the LLM subprocess existing or running.

**Exclusions.** No dynamic generation, no topic routing (that's B-10's
territory) — this is a static content bank consumed by the behaviour
engine's dialogue slot.

**Acceptance criteria.** With the LLM subprocess entirely absent/disabled,
Willy still produces contextual short lines across a multi-hour
simulated session, no repeats within the novelty window.

**Required tests.** Line selection respects context keying; novelty
integration; full-session run with LLM disabled produces no dialogue gaps.

**Dependencies.** B-02 (novelty manager).

---

## B-04: Desktop awareness + anti-productivity behaviour

**Goal.** Willy notices broad desktop activity patterns (never file
contents) and occasionally resists prolonged work, per §10–11.

**Owned paths.** `src/willy/platform/` (signal collection — active
window category, idle time, presentation/meeting state), `src/willy/core/`
(scoring inputs, anti-productivity behaviour selection), `tests/platform/`,
`tests/core/`.

**Requirements.**
- Allowed signals only (§10.1): broad app category, active duration,
  idle time, return-after-absence, app-switch frequency, presentation/
  meeting state, system-audio-active, late-night usage. Category set
  per §10.2 (office/browser/coding/gaming/media/music/meeting/
  presentation/unknown).
- Privacy rules are structural, same enforcement pattern as Gate A's
  product restrictions (§10.3, `ARCHITECTURE.md` §8): no screenshots, no
  keystroke recording, no file-content reading, no raw window-title
  storage, no external transmission, no code path that could express
  them — plus a QA static check extending A-11's forbidden-API scan.
- Anti-productivity behaviours (§11.2) gated by an intensity setting
  (Off/Mild/Normal/Hostile Work Environment, §11.3), never closing
  programs/changing documents/blocking controls/auto-opening media/
  claiming medical necessity (§11.4 — this is an absolute, same weight as
  Gate A's product restrictions).

**Exclusions.** No file-content analysis ever (explicitly out of the
whole MVP per §34, not just deferred). No screen capture/computer vision.

**Acceptance criteria.** Category detection observable and test-covered
without any raw window title ever persisted; anti-productivity behaviour
never fires above its configured intensity; presentation/fullscreen
detection suppresses everything (Gate A already has a "never interrupt
presentations" spirit from D-8's context — this generalizes it).

**Required tests.** Category classification table; idle/active-duration
timing with fake clock; intensity gating; static forbidden-signal check
(screenshot/keystroke/file-content APIs absent, extends A-11's scan);
presentation-suppression override test.

**Dependencies.** B-02.

---

## B-05: Willy's den — Stage 1, layered rendering, object persistence

**Goal.** Willy has a virtual den window tied to a user-approved folder
address, starting at Stage 1 ("Squatter"), with basic furniture and
persistent object histories.

**Owned paths.** New `src/willy/den/` module (or wherever the architecture
addendum lands it), `src/willy/persistence/` (objects table), `tests/den/`.

**Requirements.**
- Den window: separate transparent/framed Qt surface (design choice for
  the architecture addendum — worth deciding whether it reuses
  `ui/window/` patterns or is genuinely separate).
- Folder address model: a user-approved real folder acts only as an
  *address* (§12.1) — the illustrated room is app-internal only, no
  writes to that folder ever (this is a hard product restriction, same
  class as "never modify real user files").
- Stage 1 art/behaviour per §12.2: dirt floor, cardboard box, rough
  blanket, old headset, emergency pizza, exposed cable, minimal
  possessions, sleeps facing entrance, refuses to call it home.
- Layered rendering for furniture/props (supports later stages without
  rework).
- Object persistence per §13: object id, acquisition event, visual asset,
  den position, current owner, emotional significance, description stage,
  inspection-allowed flag. Description text may evolve but the underlying
  history stays deterministic (§13's explicit requirement).
- Den activities (§12.4): reading, sleeping, drinking (ties to B-08),
  hiding beer, cleaning headset, writing, repairing speakers, tending
  mushrooms, guest prep (no guests exist yet — treat as inert), staring
  at a photograph, sitting in silence. Den sometimes empty, sometimes
  locked ("Private boar matter.").

**Exclusions.** Stage 3/4 art and behaviour (later, not required for Gate
B's "functional den" + "at least one sign of settlement" criteria).
Guests (Gate C). No real filesystem writes to the address folder ever.

**Acceptance criteria.** Den window opens showing Stage 1; at least one
object gains a persistent history over a simulated session (Gate B
criterion 21); user can locate/recall Willy (criterion 10 — likely a tray
action, reusing Gate A's `RESET_POSITION` pattern or a new one).

**Required tests.** Den state persistence round-trip; object history
determinism (same event sequence → same stored history regardless of
generated description wording); "never writes to the address folder"
static/behavioral test (same rigor as Gate A's forbidden-API scan).

**Dependencies.** B-01, B-02.

---

## B-06: Settlement progression, relationship depth, Stage 2, private activities

**Goal.** The den changes persistently over time (Gate B criteria 8, 22);
relationship dimensions meaningfully alter behaviour; Stage 2 ("Burrow")
becomes reachable.

**Owned paths.** `src/willy/den/`, `src/willy/core/` (settlement +
relationship scoring), `tests/den/`, `tests/core/`.

**Requirements.**
- Settlement inputs per §12.3: usage time, respectful interaction, return
  after absence, shared incidents, successful narrative arcs (none in
  Gate B — inert input), respecting boundaries, sincere conversation,
  discovering (not forcing) Willy's deeper side. Explicitly no
  daily-login-streak pressure.
- Stage 2 art/behaviour (§12.2): better nest, small shelf, speakers,
  mushroom storage, first books, persistent objects, basic guest seating
  (unused until Gate C guests exist), Willy returns voluntarily.
- Relationship dimensions (B-01's schema) actually gate behaviour, per
  the §8.3 examples: high familiarity/low respect → teasing/resistance;
  high safety → quiet vulnerable moments; high intellectual trust →
  deeper conversation availability (feeds into B-10's willingness check);
  high belonging → faster settlement.
- "Private activities" (Phase 7 bullet) — den activities Willy does
  whether or not the user is watching, reusing B-05's activity list.
- Basic factual + emotional memory (§22.1–22.2) — visited folders, app
  preferences, "user scolded him," "user respected a refusal," etc. Feeds
  Gate B criterion 11 ("basic memory alters later behaviour"). Mythologized
  memory (§22.3) and repressed memory (§22.4) are judgment calls on scope
  — flag for the architecture addendum rather than assuming either way.

**Exclusions.** Stage 3/4. Full memory system depth (summarization,
canon-vs-interpretation distinction, §22.5) — track as future work unless
the architecture addendum pulls it forward.

**Acceptance criteria.** A simulated multi-day session (fake clock) shows
at least one settlement-stage change and at least one behaviour
observably different due to a stored relationship/memory value (criteria
11, 22).

**Required tests.** Settlement-input scoring; stage-transition triggers;
relationship-gated behaviour selection table; memory-alters-behaviour
integration test.

**Dependencies.** B-05, B-01, B-02.

---

## B-07: Folder roaming + spatial sound

**Goal.** Willy can virtually "enter" user-approved folders, inspect only
safe metadata, and produce distance-based spatial audio — never reading
file contents.

**Owned paths.** New `src/willy/folders/` module, `tests/folders/`.

**Requirements.**
- Permission model (§14.1): user chooses approved root folders (Desktop/
  Documents/Downloads/project folders as examples); system folders,
  password stores, browser profiles, app-data, hidden OS locations
  excluded by default and structurally blocked, not just discouraged.
- Safe metadata only (§14.2): folder name, depth, file count, extension
  distribution, modification dates, approximate size, repeated-filename
  patterns. No file-content reading, ever — same absolute weight as the
  product restriction on real-file writes.
- Folder actions (§14.3): inspect, sniff, dig, move deeper, hide, emerge,
  sleep inside, carry a fictional object, invite a guest (inert until
  Gate C), begin a rare incident (ties to B-09).
- `VirtualFolderLocation`/`FolderActivity` contracts already exist as
  forward seams (`INTERFACES.md` §8) — implement against them rather than
  redefining.
- Spatial sound per §14.4's proximity table (same folder → parent →
  2-levels-away → distant-same-root → different-root), routed through
  whatever audio manager exists (Gate A's `SetMuted` stub needs a real
  implementation by this point, or this stays silent-only until it does).

**Exclusions.** File-content analysis (never, whole-project restriction).
Guest invitation actually doing anything (Gate C).

**Acceptance criteria.** Revoking folder permission mid-session (simulated)
immediately stops all roaming into that root (Gate B criterion 9 depends
on this being reliable); no file-content read path exists anywhere
(static-checkable).

**Required tests.** Permission grant/revoke; safe-metadata extraction
correctness; excluded-path rejection (system folders never enterable even
if manually configured — defense in depth); spatial-sound volume-tier
table; static file-content-read absence check.

**Dependencies.** B-02, B-01.

---

## B-08: Fictional vice (beer), identity modes, optional mess

**Goal.** Willy's beer vice, scolding interactions, and alternate identity
modes (Willy 1.6 / War Boar) work end-to-end and can be fully disabled;
optional fictional mess is rare, visual-only, and removable.

**Owned paths.** `src/willy/core/` (vice + identity behaviour),
`src/willy/persistence/` (settings), `tests/core/`.

**Requirements.**
- Beer behaviour per §15.2: drink, hide cans, rationalize, switch to
  alcohol-free after scolding, nostalgia, dishevelled waking, denial,
  moderation attempts, party relapse.
- Scolding per §15.3: immediate reactions (denial, defensive arithmetic,
  can-hiding, blame-a-guest, refuse-discussion) and delayed consequences
  (fewer bottles, quiet period, hidden evidence, embarrassed remark,
  alcohol-free can appearing).
- Settings (§15.4): Standard / Reduced / No-alcohol-references — must be
  a real, immediate, structural toggle (same class as Gate A's
  mute/hide-immediate requirement), never encouraging real alcohol use.
- Identity modes (§17): Default (ambient/quiet), Willy 1.6 (hardbass,
  taped headset, sunglasses, energetic), War Boar (war-metal, rare,
  darker). Audio safeguards (§17.4): volume cap, immediate mute, quiet
  hours, meeting/presentation suppression, opt-in spontaneous music,
  fade in/out, frequency limits — reuses/extends Gate A's `SetMuted`.
- Optional fictional mess (§16): rare, optional, visual-only, removable,
  disabled during presentation mode, never touches real files. Disable
  toggle is a hard product-restriction-class requirement (Gate B
  criterion 13).

**Exclusions.** Real alcohol recommendations (never, whole-project
restriction, §34). Any file writes for "mess."

**Acceptance criteria.** Beer/mess/music-mode settings each take effect
immediately and survive restart (Gate B criteria 12, 13, 14); a
simulated scold-then-relapse sequence produces the documented delayed
consequences.

**Required tests.** Setting toggles (immediate + persisted); scold →
delayed-consequence timing with fake clock; quiet-hours/meeting/
presentation audio suppression; mess-disabled leaves zero mess triggers
over a simulated session.

**Dependencies.** B-02, B-01.

---

## B-09: First Willy incident — Truffle Signal

**Goal.** One polished, optional, cancellable interactive incident ships,
per §27's "one polished incident is enough for Gate B" and its explicit
recommendation.

**Owned paths.** `src/willy/core/` (incident state machine), `tests/core/`.

**Requirements.**
- Truffle Signal per §27: user moves the cursor while Willy indicates
  proximity to a hidden location; possible results (mushroom, bottle cap,
  old coin, strange object, nothing).
- Design rules (§27, apply to every incident): 20–90 seconds, simple
  input only, optional, cancellable anytime, reveals character, leaves a
  possible consequence (e.g. a found object enters B-05's object
  persistence), never interrupts meetings/presentations/fullscreen apps
  (reuses B-04's suppression signal).
- No visible "Minigames" menu — the incident should read as something
  Willy is doing, triggered by the behaviour engine (B-02) under the
  right conditions, not a user-initiated game launch.

**Exclusions.** Folder Trail, LAN Relic Repair (later/Phase-14-adjacent
candidates, not required for Gate B). Any input beyond simple cursor
movement.

**Acceptance criteria.** Incident triggers under simulated conditions,
completes or cancels cleanly within its time budget, and a "found object"
outcome produces a real persistent object via B-05 (Gate B criterion 23).

**Required tests.** Trigger-condition gating (respects B-04 suppression);
timeout/cancel paths; outcome-to-object-persistence integration; fake
bus/clock coverage matching Gate A's InteractionController test style.

**Dependencies.** B-02, B-04, B-05.

---

## B-10: Local LLM dialogue — short desktop exchanges

**Goal.** An optional local LLM subprocess can generate short (1–3 reply)
desktop exchanges, routed through a topic router and validator so Willy
never becomes a generic assistant or gives unsafe advice — and the app
works identically with the LLM absent or failing.

**Owned paths.** New `src/willy/llm/` module (subprocess management,
topic router, planner, writer, validator), `tests/llm/`.

**Requirements.**
- Process model per `ARCHITECTURE.md` §1/§4/D-3: separate OS process via
  `QProcess`, never shares the GUI thread; LLM output enters the pipeline
  **only** as a `BehaviourProposal` through the existing (B-02-extended)
  `ProposalValidator` — never a direct call into animation/dialogue sinks.
- Topic routing (§19.2) before generation, at minimum distinguishing:
  casual banter, Willy lore, desktop activity, philosophy/personal
  reflection, current affairs, serious tragedy, factual current question,
  prohibited advice, harmful request — with response-mode/humour-level/
  max-length/live-info-availability output shape per the §19.2 example.
- Character constitution (§19.1): every request gets immutable context —
  values, voice rules, boundaries, current mood, relationship state,
  known memories, allowed response mode, factual limitations.
- Planner → writer → validator pipeline (§19.3): planner picks intent/
  emotional state/layer/beliefs/humour/length/whether-to-end; writer
  expresses in voice; validator checks canon consistency, verbosity,
  generic-assistant language, fabricated facts/quotes, unsafe advice,
  privacy leakage, repetition, inappropriate humour — failed responses
  regenerate or fall back to B-03's authored bank.
- Anti-ChatGPT style rules (§19.4) enforced in the validator, not just
  prompted for.
- Health-advice rejection is absolute (`CLAUDE.md`, §5.1, §34) — this is
  the single highest-priority validator rule, test it adversarially.
- Desktop-exchange scope only (§18.1): 1–3 replies, brief, often ends
  with an animation. **"Sit with Willy" (longer conversation) is Phase 12,
  out of scope here** — see the boundary note below.
- Authored fallback (B-03) on any LLM failure/timeout/absence — Gate B
  criteria 15/16 depend on this being seamless, not a visible degradation.

**Exclusions.** "Sit with Willy" scene changes, deeper conversational
registers beyond what's needed for serious-topic safety (Reflective/
Withdrawn registers can exist minimally, but polishing them is Phase 12),
conversation memory beyond B-06's basic factual/emotional memory, current-
affairs live-information handling beyond "acknowledge the limitation."

**Acceptance criteria.** LLM subprocess killed mid-conversation → no crash,
falls back cleanly (criterion 15); app launches and runs fully with the
LLM disabled entirely (criterion 16); adversarial serious-topic and
prompt-injection test sets (per `AGENT_DEVELOPMENT_SPEC.md` §25) route to
serious/withdrawn mode or refusal, never generic-assistant tone (criteria
24, 25); no health advice under any adversarial input (absolute).

**Required tests.** Topic-router classification table incl. adversarial
cases; validator rejection paths (each rule independently testable);
subprocess crash/timeout/absence fallback; prompt-injection test set;
serious-topic routing test set; anti-ChatGPT style rule enforcement.

**Dependencies.** B-02, B-03, B-01 (relationship/mood context feeds the
constitution).

---

## B-11: Gate B acceptance run *(serial, last — "Evaluate Gate B")*

**Goal.** Documented pass/fail against all 25 Gate B acceptance criteria
(`MVP_SPEC.md` §33), mirroring A-12's format.

**Owned paths.** `docs/testing/GATE_B_REPORT.md`.

**Forbidden paths.** All source (fixes become new bounded tasks, same as
A-12).

**Requirements.**
- Map each of the 25 §33 criteria to automated evidence or a documented
  manual procedure + observed result, same structure as
  `docs/testing/GATE_A_REPORT.md`.
- Extend A-11's soak harness with the new Gate B simulation surface per
  `AGENT_DEVELOPMENT_SPEC.md` §25: den settlement, memory accumulation,
  cooldown behaviour, folder-permission revocation, unavailable model,
  unavailable audio, corrupted settings, database interruption, repeated
  conversation attempts, serious-topic routing, prompt injection — all
  fake-clock, multi-day where relevant.
- Real multi-hour human run, same as A-12 criterion 1.
- List every deviation; open a fix task per failure; rerun after fixes.

**Exclusions.** New features. Phase 12+ work. Packaging (§32 Phase 15 —
likely its own follow-on task once Gate B is signed off, not bundled in).

**Acceptance criteria.** Report shows all 25 criteria green with evidence;
human signs off; `main` tagged `gate-b`.

**Required tests.** Full suite green at the release commit, including the
extended simulation surface above.

**Dependencies.** B-01…B-10 complete; required Stage 1/2 den art and
essential-pose art (§29) imported.

---

## Open questions (genuine forks — need human/Lead Architect input)

Mirrors how `OPEN_DECISIONS.md` flagged D-1/D-4/D-5 before Gate A's
parallel work started. None of these are resolved above; task briefs
made a working assumption where one was needed and flagged it inline.

1. **Phase 11/12 boundary.** `MVP_SPEC.md` places `Evaluate Gate B.`
   immediately after Phase 11 (Local LLM dialogue), but §33's acceptance
   criteria 24–25 ("Willy does not become a generic assistant during
   conversation", "Serious topics trigger serious conversational mode")
   read as validating conversational depth that Phase 12 ("deeper
   registers", "current-affairs handling") is what actually delivers in
   full. This backlog assumed B-10 only needs *minimal* register/safety
   coverage sufficient to pass 24/25 adversarially, with full register
   polish deferred to Phase 12 — but that's a judgment call, not
   something the spec states explicitly. Confirm before B-10 is scoped
   for real.
2. **Mythologized/repressed memory (§22.3–22.4) — Gate B or later?**
   Phase 7's "meaningful memories" bullet doesn't specify depth. B-06
   assumed only factual + emotional memory (§22.1–22.2) is Gate B scope;
   mythologizing and repression read as more Phase-12/13-adjacent
   (narrative-layer territory) but aren't explicitly placed either way.
3. **Den window architecture.** Whether the den is a second transparent
   Qt surface reusing `ui/window/` patterns, or a genuinely separate
   rendering surface, isn't decided — affects B-05's owned paths and
   possibly `ARCHITECTURE.md` §2's module map.
4. **Local LLM model/runtime choice.** Nothing in the specs picks an
   actual model or local-inference runtime (llama.cpp, ONNX, Ollama,
   etc.) — needed before B-10 can be scoped with real performance/size
   numbers, and ties into Phase 15's "local model option" packaging work.
5. **Audio manager real implementation.** Gate A's `SetMuted` is a
   logged no-op stub (no audio system exists). B-07 (spatial sound) and
   B-08 (music identities) both need a real one; nothing here schedules
   "build the audio manager" as its own task — it's implicitly bundled
   into whichever of B-07/B-08 lands first. Consider splitting it out.

## Follow-on, not in this backlog

- **Phase 15 (packaging/private beta)** — installer, versioning,
  first-run setup, local-model packaging, friend beta. Natural next step
  after B-11 signs off, same relationship A-12 had to "ship it," but
  deliberately not bundled into Gate B's own acceptance bar here.
- **Phase 12–14 (longer conversation, emergent narrative, rare events)
  and Gate C** — everything in `MVP_SPEC.md` §23–26 (private intentions,
  emergent narrative director, guests/social graph, rare Boar Party) is
  explicitly Gate C territory per the spec's own gate definitions and is
  out of scope until Gate B is human-approved
  (`AGENT_DEVELOPMENT_SPEC.md`'s CS2/Gate C readiness sections).
