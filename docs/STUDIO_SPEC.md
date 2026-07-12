# Willy Desktop — STUDIO_SPEC.md

Status: Draft 1. Owned by Product/Lead. Changes require ADR.
Scope: the Studio — Willy's creation system and its coupling to conversation.
Position: **the organizing spine of Gate C.** Extends MVP_SPEC.md; conflicts
resolve in favour of MVP_SPEC product restrictions (§11.4, CLAUDE.md), which
remain absolute.
Prerequisites from Gate B: den, object system, memory, conversation router,
relationship model, LLM subprocess seam (`BehaviourProposal` → validator).

---

## 1. Product thesis

The Studio converts attention into objects. Conversation is how Willy learns
the user; artifacts are how he proves he was listening. Over months, the den
becomes a museum of the shared history: the piece from the month the user was
gone, the manifesto after an argument, the portrait that is a bad likeness
but an accurate reading.

This is the primary commercial differentiator: no competing product produces
persistent, material proof of attention. Marketed identity: *the AI that
doesn't work for you.* Willy refuses commissions; his output is deliberately
crude but unmistakably his. The anti-slop, anti-assistant positioning is
load-bearing — see hard lines (§2).

Character foundation: beneath the comic surface Willy is a pained creative
soul (beer, Dostoevsky, the hidden Jung volume). The Studio is where that
core becomes visible — but only to users who look (§10).

## 2. Hard lines (non-negotiable design rules)

1. **He never creates on command.** User requests for art are refused, in
   character. The moment he takes commissions the category collapses to
   "AI art app". Gifts exist (§8.4) but are always self-initiated.
2. **Quality is capped by the pipeline, not by prompting.** No model output
   reaches the den except through his instruments (§4). Fidelity would
   destroy authenticity — the one asset bigger models cannot copy.
3. **Deterministic system decides *when and why*; LLM decides *what*.**
   Project timing, triggers and moods come from the behaviour/novelty/
   emotional systems. LLM output enters only as validated proposals.
   (MVP §3.3 remains the engineering floor: authored fallback projects when
   no LLM is present.)
4. **Surface never requires depth.** A user who only ever sees a funny
   grumpy boar gets a complete product, forever. Depth is discovery-gated,
   never time-gated; no "homework" feeling.
5. **Pain leaks; it is never announced.** Melancholy reaches the surface
   only through cracks in the comedy (a beat too long at the photograph).
   Register breaks are rare, earned events.
6. **Asymmetric consequences.** Positive attention opens him up (more work
   shown, deeper registers). Neglect/dismissal makes him quieter and more
   private — never hostile, never guilt-tripping, never punishing. Depth-
   positive, never breadth-punitive. (Extends MVP no-streak-pressure rule.)
7. **Delay and distortion between input and output.** Conversation material
   resurfaces in art days later, transformed, sometimes misremembered,
   sometimes refused. Instant legibility = vending machine = dead.
8. **No arbitrary code execution.** "Willy codes" is realized as macro
   composition of safe DSL ops (§5.3), never as a general interpreter.
9. **No hostage data.** Full local export of the oeuvre, always. The moat
   is emotional, not technical.

## 3. Architecture

New module `studio/` (decision side, no Qt imports) + `studio_render/`
(renderers). Follows existing import rules; communicates via contracts only.

```text
conversation router ──► muse extractor ──► muse table (SQLite)
                                               │
emotional state + tendencies + novelty ──► project selector (deterministic)
                                               │
                                        project scheduler
                                               │ (work sessions)
                              LLM subprocess (grammar-constrained DSL)
                                               │
                                     CreationProposal ──► validator
                                               │
                                   deterministic renderers ──► artifact
                                               │
                          object system (den) + provenance store + oeuvre
```

- **CreationProposal**: new proposal type through the existing validator
  seam. Payload = DSL document + metadata (title, intended object slot,
  muse references). Never direct calls.
- **Grammar-constrained generation** (llama.cpp GBNF / structured output)
  is the enabling technique: 8B-class local models are unreliable at free
  code but reliable at schema-conforming output. All creative output is
  schema-bound.
- All writes under `%APPDATA%/WillyDesktop/` plus the user-approved export
  folder (§12). No other filesystem contact. No input automation, no
  screenshots — unchanged.
- LLM stays a `QProcess` subprocess; work sessions run in small background
  steps, never blocking the GUI thread.

## 4. Instruments (mediums and renderers)

Ship order = value per effort. Each instrument = one DSL schema + one
deterministic renderer. New instruments arrive as narrative events ("tools
he found").

1. **Writing** (first; proves the whole loop with no renderer). Journal
   fragments, beer reviews, angry letters to software companies, marginalia
   in his books, bad poetry he denies writing.
2. **Canvas / paint DSL.** 32×32 grid, palette locked to
   `willy_palette.gpl`. Ops: fill, rect, line, dither, stamp. Results hang
   in the den; accumulate as gallery.
3. **Part library** (the workhorse). 100–200 authored small sprites
   (mushrooms, bottles, speakers, moons…); Willy composes, layers,
   recolors. Representational quality lives in authored parts; creativity
   in his arrangement.
4. **Procedural instruments.** LLM picks parameters, code renders:
   symmetry, dither gradients, palette ramps, noise. Reliably "designed"-
   looking abstract work.
5. **Filter engines.** Headless libraries (Pillow/ImageMagick chains:
   posterize, halftone, glitch) with LLM-chosen parameters. "Experimental
   phase" content. Engines are embedded — never GUI automation.
6. **Tracker chiptune** (stretch). Note-pattern DSL rendered to .mod/.wav
   by a trivial synth. Hardbass phase.
7. **Zine** (aggregator). Periodic one-pager combining writing + art
   ("DER EBER, Issue 3"). No new generator; composes the others.

**BoarPaint** (presentation, not a tool): in-app easel window replaying the
DSL stroke by stroke while Willy visibly works — cursor wobble, undo,
grumbling. The DSL source *is* the replay data. All the theatre of MS Paint,
zero automation. Driving real external apps (Paint, freeware GUIs) is
permanently out of scope (restrictions + he'd be painting blind).

## 5. Skill, growth, and style

### 5.1 Stage-gated vocabulary
The DSL op set is gated by settlement stage: Squatter = fill/rect only
(crude, blocky); Burrow adds line/dither; Den adds part library + filters;
Home adds composition ops. Craft visibly improves over months with no model
change. Early works become retroactively precious.

### 5.2 Multi-year ceiling curve
Canvas size, palette size and op vocabulary rise on a slow curve (year-scale)
so year two feels different from year one. The cap always remains pipeline-
enforced (§2.2); it rises, it never disappears.

### 5.3 Macros — "he learned to code"
Willy may compose existing ops into named, persisted macros: brushes and
techniques he invents ("he discovered dithering during the angry period and
now overuses it"). Composition of safe ops is provably safe but genuinely
emergent — per-user technique vocabulary, discovered not authored. This is
the sanctioned meaning of "limited coding abilities".

### 5.4 Creative phases
Slow-changing tendencies + emotional state bias style parameters: blue
period after prolonged absence (loneliness → palette bias), hardbass-
geometry phase, minimalism after a guest mocks his clutter. Users learn to
read his state through his output.

### 5.5 Willy's hand
Final deterministic pass on every visual artifact: slight stroke jitter,
occasional wrong pixel, unfinished corners at low energy/patience. Even a
lucky perfect composition still reads as his.

## 6. The muse system (conversation → material)

- **Extractor**: after conversations, one structured-output call emits
  material candidates — phrase, sentiment, motif, palette hint — into a
  `muse` table with provenance (timestamp, conversation ref, emotional
  snapshot).
- **Selector**: deterministic; samples muse entries weighted by emotional
  salience × recency × novelty penalty (novelty manager also covers
  artifact motifs/titles to prevent convergence on slop).
- **Delay/distortion/refusal** per §2.7. Some material goes to the journal,
  not the canvas. He misremembers.
- Additional muses: user-absence duration, time of day, season (local clock
  only — **never** wallpaper/screen content; no-screenshot rule).
- Canonical target moment: user mentions the sea in passing; three weeks
  later a blue piece titled "SEA (NEVER SEEN IT)".

## 7. Project arcs

Lifecycle: intent (selector) → material gathering → work sessions (visible
at workbench; BoarPaint) → outcome: **unveil / abandon / destroy / hide**.

- Failures are content. Canonical "confidence despite poor judgment" means
  the output doesn't need to be good, it needs to be *his*.
- Multi-day by design; progress persists across app sessions.
- Rare mid-project user contact: he asks one odd question ("What colour is
  homesickness. No reason.") — answer becomes a parameter he may then
  visibly ignore. Contribution without control.
- Locked den sometimes now means: working on something.

## 8. Artifacts, oeuvre, and formats

### 8.1 Provenance (mandatory, every artifact)
DSL source, RNG seed, emotional-state snapshot, muse references, timestamps.
Pays three times: evolving object descriptions grounded in truth; validator
can check his conversational claims about his own work against history
("Made this the week you were gone. Don't look at it too long."); full
deterministic replay for QA.

### 8.2 Oeuvre structures
- **Gallery**: hung works, visibility gated on relationship (§10).
- **Failure crate**: abandoned works, browsable, descriptions evolve.
- **Ledger**: pretentious titles, prices denominated in beer.
- **Time capsule**: he buries something; timer (months); digs it up.
- **Dreams**: while asleep, dream-DSL recombines memory fragments into
  surreal vignettes (thought bubble / dream journal). Jung layer, almost
  literally.

### 8.3 Companions (built, not simulated)
Willy constructs a companion from junk (mushroom jar, robot from the broken
mouse). Deterministic object with authored idle behaviours; the LLM
generates only Willy's one-sided relationship with it — naming, arguing,
defending it to the user. Lifecycle: it breaks → repair / mourning / v2 with
visible design lessons. No second LLM agent, ever.

### 8.4 Gifts
Relationship-gated (high belonging): he occasionally makes something for the
user — unannounced, left somewhere. Asking for one is refused (§2.1).

### 8.5 Endgame: the portrait
Stage-4 "representation of the user" (MVP §12.2) is built from the muse
table + relationship dimensions + things he got slightly wrong: a bad
likeness, an unsettlingly accurate reading. The spec's "why was that
affecting?" target, earned by months of conversation.

## 9. Scenes (guests and the den as stage)

Not agents — **performances**: one generation call writes a validated
two-hander (Willy + guest arguing about his new piece), played in the den,
user as eavesdropper. One inference per scene. Enables: guest critique,
vernissage (gallery night; user invited or not, per relationship),
plagiarism arc (accusation → shame → denial → possibly destroying the
disputed piece), Boar-Party damage to works he valued — permanent
consequences applied to things *he* cared about.

## 10. Art reactions shape behaviour

- After unveilings he may ask what the user thinks. Response is classified
  (existing router) and moves relationship dimensions: respect,
  intellectual trust, willingness-to-be-vulnerable, resentment.
- Implicit signals also count: whether/when the user inspects a piece,
  inspection frequency. (In-app signals only.)
- Consequences follow §2.6 asymmetry: sincere attention → more work shown,
  deeper registers, vulnerable moments. Dismissal → gallery goes private;
  the user must *notice*. Praise for the wrong piece → suspicion.
- Arguments are fuel: disagreement → irritation spike → angry period
  (harsh palettes, manifesto zine "ON BEING WRONG (I AM NOT)").
  Reconciliation arcs leave a visible artifact trail.
- Beer/pain register rule: drinking stays fictional and comic-melancholy;
  the Jung layer occasionally shows he *knows*. Self-medication played
  straight is out of register (also: store age ratings).

## 11. Optional heavy models (strictly capped)

- **VLM critic loop** (e.g. Qwen2.5-VL-7B class): render → critique →
  revise, ≤ 2–3 rounds, "serious project" mode only. Improves intent-
  coherence; cannot raise fidelity past the instruments. Critic optimizes
  "does this look deliberate", never "does this look good".
- **Image generation (SD + pixel-art LoRA): reference-only.** A generated
  reference gets pinned to the easel; he paints *from* it with his limited
  DSL. The reference may be shown, slightly obscured. The render is never
  the artwork; at most it is quantized/part-matched back into his
  vocabulary. Rare, narrative moments only; hardware-gated; authored
  fallback mandatory. Models load sequentially (idle time), never
  concurrently with the chat LLM.

## 12. Export, sharing, network

- **Export**: user-approved single export folder; user-initiated or
  per-artifact prompt. Share-card format: framed PNG, title, date, his
  signature, one provenance line. Every Willy's oeuvre is unique → the
  share card is the ad.
- **Full oeuvre export** always available (§2.9).
- **Boar mail (deferred feature, format designed now):** opt-in artifact
  interchange between installations — a guest arrives carrying another
  Willy's painting; yours critiques/envies it, steals a technique.
  Artifacts travel, user data never does. Define the portable artifact
  format (DSL + provenance subset, no PII) in Gate C so no retrofit is
  needed.

## 13. Commercial notes

- **Retention**: the muse loop is delayed variable reward, implemented
  diegetically (no streaks). "I wonder what he's made" has an answer after
  three days away. Compound value: relationship + oeuvre + macro vocabulary
  all deepen per loop pass, without a content treadmill.
- **Moat**: per-user, unreproducible oeuvre/macros/memories. Switching cost
  = abandoning a relationship and an archive. Kept ethical via §2.9.
- **Audience**: adult/teen+; the pure-cute segment is deliberately
  conceded. Target audience = the Undertale / Animal Crossing depth-
  discovery market: large, paying, evangelizing.
- **Pricing**: local-first → near-zero marginal cost → one-time purchase +
  expansion content (instrument packs, guests, arcs — "DLC as life
  events"). Optional opt-in cloud inference tier for GPU-less users
  (subscription; never required; see S-2).
- **Hardware tiers**: CPU floor = authored + small model; full loop on
  ~8 GB VRAM GPU; heavy models (§11) gated above that.

## 14. Testing

- Fake-clock soak of project scheduler across simulated months (arcs
  complete/abandon correctly; no muse-table unbounded growth).
- Property-based validator tests: no artifact violates palette/dims/op
  gates; no text artifact violates content rules (privacy: muse material
  never reproduced verbatim beyond short fragments; no real persons).
- Determinism: replay(provenance) == stored artifact, bit-exact.
- Anti-slop metrics: motif/title repetition rates under novelty penalty.
- Character QA: register checks (no announced pain, no assistant language)
  via existing validator + authored test fixtures.

## 15. Open decisions

**S-1: Gate placement.** Default: Studio is the spine of Gate C; writing
instrument may pilot late in Gate B behind a flag. Alternative: strict
Gate C. Decide at Gate B mid-point.

**S-2: Cloud inference tier.** Opt-in subscription for GPU-less users vs
pure local-only identity. Commercial fork; no architecture impact (LLM is
already a subprocess behind a seam). Decide before public beta.

**S-3: Ceiling curve numbers.** Canvas 32→48→64? Palette growth? Needs play-
testing; ship conservative, raise via updates.

**S-4: Reaction classification depth.** Explicit conversation sentiment only
(default) vs adding implicit signals (inspection timing/frequency). Implicit
adds depth but risks misreads; tune in beta.

**S-5: Alcohol rating strategy.** Fictional-beer framing vs toned-down
"Kwas" mode per store/region. Check store policies before listing.

**S-6: Boar-mail transport.** Format now (per §12); transport (file-based
sneakernet vs relay server) deferred — relay conflicts with no-cloud
identity unless strictly opt-in.

**S-7: Dream visibility.** Thought-bubble (ambient, all users see) vs
journal-only (discovery-gated). Default: journal-only; bubbles are close to
announcing depth (§2.5).
