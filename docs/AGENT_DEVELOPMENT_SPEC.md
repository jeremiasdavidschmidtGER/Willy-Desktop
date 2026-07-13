# Willy the Boar

## Multi-Agent Development and Orchestration Specification

---

# 1. Purpose

This document defines how multiple AI coding agents should collaborate on the Willy Desktop project.

It covers:

* agent roles;
* repository ownership;
* task assignment;
* Git workflow;
* use of Claude Code and optional Hermes coordination;
* testing and review;
* permissions;
* escalation rules;
* architectural decision-making;
* acceptance evidence;
* human approval points.

This specification supplements the main Desktop MVP specification.

The product specification defines:

> What Willy should become.

This agent specification defines:

> How AI agents may build him without creating architectural chaos.

---

# 2. Core development principle

The project should use:

> One human product owner, one architectural source of truth, several narrowly scoped specialist agents, and Git as the authoritative record.

Agents must not collaborate by freely editing the same files or by relying on undocumented conversational context.

They collaborate through:

* specifications;
* typed interfaces;
* Git branches and worktrees;
* task briefs;
* tests;
* pull requests or reviewed commits;
* architecture decision records.

---

# 3. Human role

The human project owner retains final authority over:

* product scope;
* character design;
* visual identity;
* humour;
* dialogue quality;
* interruption frequency;
* philosophical tone;
* privacy boundaries;
* feature priority;
* acceptance of generated artwork;
* merging to the main branch;
* release approval.

Agents may make technical recommendations, but they must not independently redefine Willy's character or product direction.

The human project owner should not need to implement every feature manually, but must inspect:

* task plans;
* important diffs;
* test evidence;
* user-visible behaviour;
* architectural changes;
* release builds.

---

# 4. Tooling model

## 4.1 Initial toolset

The initial development workflow should use:

* Claude Code;
* Git;
* GitHub private repository;
* Git worktrees or isolated Claude Code workspaces;
* VS Code;
* Python;
* pytest;
* Ruff;
* PySide6;
* SQLite.

## 4.2 Optional orchestration layer

Hermes may later be added as a coordinator.

Hermes should be responsible for:

* backlog inspection;
* dependency-aware task selection;
* implementation-brief creation;
* delegation to Claude Code;
* scheduling reviews;
* reporting test evidence;
* recurring maintenance tasks.

Hermes should not initially:

* merge to `main`;
* independently redesign architecture;
* directly implement large production features;
* work outside the Willy repository;
* approve its own changes;
* bypass dangerous-command approvals.

## 4.3 Recommended progression

### Early Gate A

Use Claude Code directly.

### After the repository and tests are stable

Use multiple Claude Code worktrees.

### After the backlog and module interfaces are mature

Add Hermes as the persistent orchestration layer.

---

# 5. Agent hierarchy

Recommended structure:

```text
Human Product Owner
        │
        ▼
Lead Architect Agent
        │
 ┌──────┼───────────────┬───────────────┐
 ▼      ▼               ▼               ▼
Platform Animation   Character       Den/Folder
Agent    Agent         Agent           Agent
        │
        └──────────┬─────────────┐
                   ▼             ▼
             Conversation      QA/Release
                Agent             Agent
```

The QA agent should remain independent from implementation agents whenever practical.

---

# 6. Required agent roles

## 6.1 Lead Architect Agent

### Purpose

Maintain architectural coherence and translate the product specification into bounded technical work.

### Responsibilities

* maintain the architecture document;
* maintain shared interfaces;
* maintain the issue backlog;
* define module boundaries;
* define event and command contracts;
* review cross-module changes;
* manage dependency ordering;
* resolve architectural conflicts;
* update architecture decision records;
* verify Gate A and Gate B scope;
* prevent premature CS2 work;
* approve specialist implementation plans before coding begins.

### Owned paths

```text
/docs/
/src/willy/app/
/src/willy/contracts/
/pyproject.toml
AGENTS.md
CLAUDE.md
```

Ownership of `pyproject.toml` may be shared with QA, but changes require review.

### Must not

* implement large feature sets by default;
* silently change product scope;
* merge unreviewed specialist work;
* bypass tests;
* start Gate C or CS2 work before earlier gates pass.

### Required outputs

For each milestone:

* architecture update;
* issue breakdown;
* interface definitions;
* dependency graph;
* integration plan;
* remaining risks.

---

## 6.2 Desktop Platform Agent

### Purpose

Build the reliable Windows application shell in which Willy lives.

### Responsibilities

* transparent frameless PySide6 window;
* window focus handling;
* dragging and dropping;
* always-on-top behaviour;
* click-through mode;
* high-DPI handling;
* multiple-monitor support;
* monitor-disconnection recovery;
* tray icon and menu;
* show, hide, pause and exit;
* startup and shutdown;
* settings integration;
* Windows-specific APIs;
* presentation and quiet-mode hooks;
* packaging support.

### Owned paths

```text
/src/willy/platform/
/src/willy/ui/window/
/src/willy/ui/tray/
/tests/platform/
```

### Must not

* implement personality logic;
* directly modify memory or relationship values;
* add LLM code;
* decide when Willy performs behaviours;
* inspect user files;
* modify shared contracts without approval.

### Initial acceptance target

A static Willy can:

* launch;
* appear transparently;
* be dragged;
* move between monitors;
* retain position;
* be hidden and restored;
* exit cleanly;
* run without stealing focus.

---

## 6.3 Animation and Asset Runtime Agent

### Purpose

Convert approved artwork into stable runtime animations.

### Responsibilities

* PNG loading;
* frame-sequence loading;
* sprite-sheet support;
* animation manifests;
* frame timing;
* transition rules;
* animation interruption;
* return-to-idle behaviour;
* right-facing canonical assets;
* automatic mirroring;
* mirrored anchors;
* nearest-neighbour scaling;
* accessory layers;
* effect layers;
* sprite caching;
* asset validation;
* missing-asset fallback.

### Owned paths

```text
/src/willy/animation/
/src/willy/assets_runtime/
/assets/manifests/
/tests/animation/
```

### Must not

* determine behavioural motivations;
* select dialogue;
* modify the database directly;
* generate production artwork automatically;
* alter approved visual canon;
* enable smoothing or blurry scaling.

### Required asset contract

Each directional asset should declare:

```json
{
  "asset_id": "willy_walk",
  "source_direction": "right",
  "mirror_allowed": true,
  "loop": true,
  "frames": [],
  "anchors": {}
}
```

### Anchor responsibilities

Mirroring must correctly transform:

* body pivot;
* ground point;
* mouth;
* eyes;
* headset;
* front hoof;
* rear effect point;
* folder contact point;
* click region.

---

## 6.4 Character and Persistence Agent

### Purpose

Build deterministic Willy before the local LLM is introduced.

### Responsibilities

* Willy state model;
* emotional state;
* relationship dimensions;
* behaviour eligibility;
* behaviour scoring;
* scheduler;
* cooldowns;
* novelty management;
* routines;
* authored dialogue selection;
* delayed reactions;
* memory summaries;
* SQLite schema;
* repositories;
* settlement inputs;
* private activity scheduling;
* deterministic simulations.

### Owned paths

```text
/src/willy/core/
/src/willy/personality/
/src/willy/memory/
/src/willy/persistence/
/tests/core/
/tests/persistence/
```

### Must not

* directly render sprites;
* move the desktop window;
* inspect file contents;
* call cloud services;
* allow health-advice behaviours;
* permit generated text to execute actions.

### Required output model

The character system should create proposals such as:

```json
{
  "behaviour_id": "late_work_stare",
  "animation_id": "willy_disapprove_work",
  "dialogue_intent": "question_excessive_work",
  "audio_id": null,
  "state_changes": {
    "irritation": 2,
    "familiarity": 1
  }
}
```

It should not directly invoke arbitrary UI methods.

---

## 6.5 Den and Folder Agent

### Purpose

Build Willy's virtual home, settlement system and safe folder presence.

### Responsibilities

#### Den

* den window;
* layered den rendering;
* settlement stages;
* furniture and prop state;
* object histories;
* den lighting;
* den activities;
* object inspection;
* private or locked states;
* persistent aftermath.

#### Folder system

* approved root permissions;
* virtual folder locations;
* safe metadata;
* folder depth;
* locating Willy;
* recalling Willy;
* folder-entry events;
* spatial audio distance;
* folder incidents;
* no real file modification.

#### Interactive incidents

* Truffle Signal;
* later Folder Trail;
* event outcomes;
* persistent object rewards.

### Owned paths

```text
/src/willy/den/
/src/willy/folders/
/src/willy/incidents/
/tests/den/
/tests/folders/
/tests/incidents/
```

### Must not

* modify real files;
* create files to represent fictional objects;
* open private directories without permission;
* store raw file contents;
* directly alter relationship state;
* generate unvalidated narrative arcs.

### Virtual-location contract

```python
@dataclass(frozen=True)
class VirtualFolderLocation:
    root_id: str
    relative_path: PurePath
    entered_at: datetime
    activity: FolderActivity
```

This object represents fictional presence only.

---

## 6.6 Conversation and Local-LLM Agent

### Purpose

Allow Willy to converse while remaining safe, concise and in character.

### Start condition

This agent should begin implementation only after:

* deterministic Willy works;
* authored dialogue works;
* state and memory systems exist;
* the den exists;
* fallback behaviour is established.

### Responsibilities

* local-model process;
* prompt construction;
* character constitution;
* topic routing;
* conversational registers;
* conversation willingness;
* planner output;
* writer output;
* canon validation;
* safety validation;
* current-information limitations;
* anti-generic-assistant detection;
* prompt-injection resistance;
* health-advice rejection;
* conversation summaries;
* authored fallback;
* timeouts and model failure handling.

### Owned paths

```text
/src/willy/conversation/
/src/willy/llm/
/src/willy/dialogue/generated/
/tests/conversation/
/tests/llm/
```

### Required pipeline

```text
User message
     │
     ▼
Topic router
     │
     ▼
Conversation planner
     │
     ▼
Character writer
     │
     ▼
Canon and safety validator
     │
     ▼
Deterministic action proposal
```

### Must not

* directly move the window;
* directly play animations;
* modify files;
* execute commands;
* control mouse or keyboard;
* invent live facts;
* provide health advice;
* rewrite Willy's permanent character constitution;
* produce unlimited conversation by default.

### Required structured output

```json
{
  "intent": "deflect_after_sincerity",
  "register": "reflective",
  "line": "Silence remembers what noise negotiates away.",
  "animation_id": "look_away",
  "end_conversation": true
}
```

The deterministic system may accept, modify or reject the proposal.

---

## 6.7 QA and Release Agent

### Purpose

Independently verify that agents did what they claim.

### Responsibilities

* test architecture;
* unit tests;
* integration tests;
* fake clock;
* fake desktop events;
* temporary databases;
* asset-manifest tests;
* animation-transition tests;
* position-persistence tests;
* monitor edge-case tests;
* long-running simulations;
* soak tests;
* CPU and memory profiling;
* installer validation;
* clean uninstall;
* version stamping;
* private-beta packaging;
* regression reports;
* bug-report templates.

### Owned paths

```text
/tests/
/tools/test_harness/
/.github/workflows/
/packaging/
/docs/testing/
```

Small testability changes in production code require the owning agent's review.

### Must not

* silently redesign implementation;
* approve its own feature work;
* alter character behaviour to make tests easier;
* suppress failures;
* treat unexecuted tests as passing.

### Required evidence

Every review should include:

* commands executed;
* test results;
* warnings;
* untested assumptions;
* reproduced defects;
* performance observations.

---

## 6.8 Optional Content Agent

### Purpose

Maintain authored character content independently from application logic.

### Responsibilities

* authored lines;
* dialogue intents;
* object descriptions;
* den observations;
* beer excuses;
* philosophical remarks;
* incident outcomes;
* refusal lines;
* lore consistency;
* rarity metadata.

### Owned paths

```text
/content/dialogue/
/content/objects/
/content/incidents/
/content/lore/
```

### Output format

Prefer structured data:

```yaml
- line_id: beer_denial_004
  intent: deny_drinking
  register: comic
  text: "Bottle predates tenancy."
  rarity: uncommon
  cooldown_group: beer_denial
  allowed_moods:
    - defensive
    - embarrassed
```

### Must not

* write executable code;
* change state schemas;
* create health advice;
* fabricate quotations;
* introduce copyrighted lyrics;
* redefine Willy's moral code without human approval.

---

# 7. Repository structure

Recommended structure:

```text
willy-desktop/
│
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── pyproject.toml
│
├── docs/
│   ├── MVP_SPEC.md
│   ├── AGENT_DEVELOPMENT_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   ├── TESTING.md
│   └── decisions/
│
├── assets/
│   ├── source/
│   ├── exports/
│   └── manifests/
│
├── content/
│   ├── dialogue/
│   ├── objects/
│   ├── incidents/
│   └── lore/
│
├── src/willy/
│   ├── app/
│   ├── contracts/
│   ├── platform/
│   ├── ui/
│   ├── animation/
│   ├── core/
│   ├── personality/
│   ├── persistence/
│   ├── memory/
│   ├── den/
│   ├── folders/
│   ├── incidents/
│   ├── conversation/
│   └── llm/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── simulation/
│   └── regression/
│
├── tools/
└── packaging/
```

---

# 8. Source-of-truth hierarchy

When documents disagree, use this order:

1. explicit human instruction;
2. latest approved MVP specification;
3. latest approved architecture document;
4. architecture decision records;
5. interface contracts;
6. task brief;
7. module-specific agent instructions;
8. agent assumptions.

Agents must not resolve important contradictions silently.

They should stop and report the conflict.

---

# 9. Global agent rules

All agents must:

* read `AGENTS.md`;
* read the relevant specification;
* inspect existing interfaces;
* stay within owned paths;
* produce a plan before large changes;
* add tests;
* run standard checks;
* summarize changed files;
* state remaining risks;
* avoid unsupported success claims;
* preserve local-first privacy;
* avoid premature CS2 work.

All agents must not:

* edit outside the repository;
* modify user documents;
* install unrelated software without approval;
* disable safety prompts;
* merge to `main` autonomously;
* bypass failing tests;
* rewrite history on shared branches;
* expose secrets;
* commit API keys;
* create cloud dependencies without approval.

---

# 10. Task specification format

Every implementation task should contain:

## Title

A concise identifier.

Example:

```text
Gate A-05: Runtime sprite mirroring
```

## Goal

What the user should observe.

## Context

Relevant specification sections and dependencies.

## Owned paths

Directories the agent may edit.

## Forbidden paths

Directories the agent must not edit.

## Requirements

Concrete implementation requirements.

## Exclusions

Features deliberately outside the task.

## Acceptance criteria

Observable completion conditions.

## Required tests

Tests that must be written and run.

## Deliverables

Code, documentation, manifests or reports.

## Escalation conditions

Situations requiring lead or human input.

---

# 11. Example task brief

```markdown
# Gate A-05: Runtime sprite mirroring

## Goal

Allow one right-facing canonical sprite to be displayed facing left
without requiring a second production asset.

## Owned paths

- src/willy/animation/
- assets/manifests/
- tests/animation/

## Forbidden paths

- src/willy/core/
- src/willy/persistence/
- src/willy/conversation/

## Requirements

- Load right-facing PNG.
- Produce exact horizontal mirror.
- Preserve alpha transparency.
- Use nearest-neighbour rendering.
- Transform all x-coordinate anchors.
- Cache both directions.
- Do not mirror direction-neutral sprites.
- Validate manifest values.

## Acceptance criteria

- Mirrored image is pixel-exact.
- Ground anchor remains correct.
- Mouth and rear-effect anchors are transformed.
- Mirroring occurs only once per load.
- No blurry scaling is introduced.
- Existing right-facing display remains unchanged.

## Tests

- image mirror equality;
- anchor transformation;
- neutral-asset behaviour;
- cache reuse;
- invalid manifest rejection.

## Exclusions

- behaviour selection;
- artwork creation;
- UI redesign;
- new animations.
```

---

# 12. Branch and worktree strategy

## 12.1 Main branch

`main` should always represent the latest reviewed and stable integration state.

Agents must not work directly on `main`.

## 12.2 Feature branches

Naming pattern:

```text
feature/gate-a-transparent-window
feature/runtime-mirroring
feature/den-stage-one
fix/monitor-recovery
test/animation-soak-harness
```

## 12.3 Worktrees

Each active implementation agent should use a separate worktree.

Example:

```text
C:\Projects\willy-desktop
C:\Projects\willy-platform
C:\Projects\willy-animation
C:\Projects\willy-qa
```

## 12.4 Commit rules

Commits should be:

* small;
* descriptive;
* related to one task;
* free of generated junk files;
* tested where possible.

Example:

```text
Add runtime sprite mirroring and anchor transforms
```

Avoid:

```text
misc changes
updates
agent work
fix everything
```

---

# 13. Parallel-work rules

Parallel work is allowed only when tasks are genuinely independent.

Good parallel combination:

* transparent window;
* animation manifest;
* QA fixtures.

Bad parallel combination:

* three agents redesigning the event bus;
* den agent and character agent independently changing settlement state;
* platform and animation agents both owning drag logic;
* multiple agents editing the same database schema.

Maximum recommended early parallelism:

* two implementation agents;
* one QA agent;
* one lead reviewer.

More parallelism may be added after module interfaces stabilize.

---

# 14. Shared interface rules

Subsystems should communicate through:

* typed events;
* typed commands;
* repository interfaces;
* immutable data transfer objects;
* documented result objects.

Avoid direct cross-module mutation.

Example:

```text
Platform emits:
USER_DRAGGED_WILLY

Character system decides:
irritation +2
select dragged reaction

Animation receives:
PLAY_ANIMATION dragged_annoyed

Persistence receives:
STORE_MEANINGFUL_EVENT only if threshold is met
```

The platform layer must not directly set `irritation`.

The conversation layer must not directly play an animation.

---

# 15. Architecture decision records

Important decisions should be stored under:

```text
docs/decisions/
```

Suggested format:

```text
ADR-001-event-bus.md
ADR-002-sprite-direction.md
ADR-003-local-llm-process.md
ADR-004-folder-permission-model.md
```

Each record should include:

* decision;
* context;
* alternatives;
* consequences;
* date;
* status;
* approving authority.

Agents must not reverse an accepted decision without creating a new proposal.

---

# 16. Standard commands

The repository should expose stable commands:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m willy
```

Optional later:

```powershell
python -m tools.simulate_day
python -m tools.validate_assets
python -m tools.run_soak_test
python -m build
```

Agents should use documented commands rather than inventing new workflows.

---

# 17. Completion-report format

Every implementation agent must return:

## Summary

What was changed.

## Changed files

List of modified and created files.

## Commands run

Exact commands.

## Test results

Passes, failures and skipped tests.

## Manual checks

What was actually launched or observed.

## Risks

Known issues and untested assumptions.

## Scope confirmation

What was deliberately not implemented.

## Commit

Branch and commit identifier.

Agents must not say "done" without this evidence.

---

# 18. Review workflow

## Step 1: implementation review

Check:

* task scope;
* changed paths;
* interface compliance;
* tests;
* error handling;
* documentation.

## Step 2: QA review

QA agent runs:

* unit tests;
* integration tests;
* regressions;
* task-specific checks;
* manual smoke test where possible.

## Step 3: lead review

Lead agent checks:

* architectural compliance;
* dependency impact;
* scope;
* Gate criteria;
* documentation.

## Step 4: human review

Human checks:

* user-visible behaviour;
* character;
* art;
* annoyance level;
* product direction.

## Step 5: merge

Only approved work is merged to `main`.

---

# 19. Defect-handling process

When QA finds a problem:

1. record reproducible steps;
2. identify owning module;
3. create a bounded fix task;
4. assign it to the owning agent;
5. add a regression test;
6. rerun relevant and full tests;
7. review before merge.

QA should not silently make broad changes in another agent's module.

---

# 20. Escalation rules

Agents must stop and escalate when:

* the specification is contradictory;
* a task requires editing forbidden paths;
* a shared interface must change;
* a privacy rule may be violated;
* real user files might be altered;
* a new dependency is required;
* a Windows behaviour cannot be reliably tested;
* acceptance criteria appear impossible;
* artwork assumptions are missing;
* a model is asked to provide health advice;
* generated dialogue would need live factual information;
* the task depends on unfinished work;
* tests expose an architectural problem rather than a local bug.

Escalation report:

```text
Problem
Affected task
Why local resolution is unsafe
Options
Recommended option
Blocked work
```

---

# 21. Security and permission rules

## 21.1 Repository scope

Agents should have access only to the Willy project directory where practical.

## 21.2 Command approval

Dangerous commands require human approval.

Examples:

* deleting directories;
* changing system settings;
* installing system-wide software;
* modifying registry values;
* running unsigned installers;
* disabling security tools;
* force-pushing;
* deleting branches with unmerged work.

## 21.3 Secrets

Never store:

* API keys;
* passwords;
* private tokens;
* signing credentials;
* personal paths;
* sensitive tester data.

Use environment variables and ignored local configuration.

## 21.4 File safety

Folder-related testing must use:

* temporary directories;
* fixture data;
* test sandboxes.

Do not test folder features against important personal directories.

---

# 22. Hermes coordinator specification

## 22.1 When to introduce Hermes

Hermes should be introduced only after:

* repository scaffold exists;
* standard commands work;
* module ownership is documented;
* issue backlog exists;
* shared interfaces are stable;
* at least one multi-agent workflow has been completed manually.

## 22.2 Hermes responsibilities

Hermes may:

* inspect open issues;
* select unblocked tasks;
* draft task briefs;
* create or assign worktrees;
* invoke Claude Code;
* invoke a read-only reviewer;
* schedule test runs;
* summarize results;
* maintain project coordination memory;
* produce daily or weekly status reports.

## 22.3 Hermes restrictions

Hermes must not:

* merge to `main`;
* approve its own work;
* rewrite the MVP specification;
* modify files outside the repository;
* bypass command approvals;
* start CS2 work early;
* delegate vague "continue building" instructions;
* run more concurrent agents than configured;
* treat agent claims as test evidence.

## 22.4 Hermes task cycle

```text
Read backlog
     │
     ▼
Check dependencies
     │
     ▼
Select bounded task
     │
     ▼
Create implementation brief
     │
     ▼
Delegate to Claude Code worktree
     │
     ▼
Collect implementation report
     │
     ▼
Delegate independent review
     │
     ▼
Run tests
     │
     ▼
Report to human
     │
     ▼
Wait for merge approval
```

## 22.5 Hermes coordinator prompt

```text
You are the technical coordinator for Willy Desktop.

Read:

- AGENTS.md
- docs/MVP_SPEC.md
- docs/AGENT_DEVELOPMENT_SPEC.md
- docs/ARCHITECTURE.md
- docs/INTERFACES.md
- current issue backlog

Your role is coordination, not unrestricted implementation.

For every development cycle:

1. Select only an issue whose dependencies are complete.
2. Create a bounded implementation brief.
3. State owned and forbidden paths.
4. Define observable acceptance criteria.
5. Delegate implementation to Claude Code in an isolated worktree.
6. Require tests and linting.
7. Delegate a read-only review to a separate agent.
8. Verify claims against test output.
9. Report changed files, test evidence, risks and blockers.
10. Never merge to main without explicit human approval.
11. Never modify files outside the Willy repository.
12. Prioritize the current development gate.
13. Do not begin den, LLM, narrative or CS2 work before their dependencies pass.
14. Escalate architectural conflicts rather than resolving them silently.
```

---

# 23. Claude Code project instructions

The repository should include `CLAUDE.md`.

Recommended content:

```markdown
# Willy Desktop Development Rules

Read these documents before making changes:

- docs/MVP_SPEC.md
- docs/AGENT_DEVELOPMENT_SPEC.md
- docs/ARCHITECTURE.md
- docs/INTERFACES.md

## Current priority

Follow the current gate identified in the issue brief.

Do not implement CS2 features before Gate B is approved.

## Product restrictions

- Never modify real user files.
- Never automate mouse or keyboard input.
- Never collect screenshots or keystrokes.
- Never provide health advice.
- Willy must function without an LLM.
- Generated text cannot directly execute application actions.

## Engineering restrictions

- Stay within owned paths.
- Do not change shared interfaces without approval.
- Add tests for behaviour changes.
- Run pytest and Ruff before completion.
- Do not claim success without test evidence.
- Keep GUI work non-blocking.
- Keep Windows-specific code isolated.
- Preserve pixel-art nearest-neighbour rendering.
- Do not introduce cloud dependencies without approval.

## Completion report

Include:

- summary;
- changed files;
- commands run;
- test output;
- manual checks;
- remaining risks;
- branch and commit.
```

Module-specific `CLAUDE.md` files may provide narrower rules.

---

# 24. Quality gates

## Gate A agent readiness

Before Gate A is accepted:

* platform module works;
* animation runtime works;
* drag and drop works;
* basic tests exist;
* soak-test harness exists;
* no LLM module is required;
* no folder system is required;
* no CS2 code exists.

## Gate B agent readiness

Before Gate B is accepted:

* deterministic character system works;
* den works;
* settlement persists;
* folder permissions work;
* memory is bounded;
* anti-productivity behaviour is controllable;
* one interactive incident works;
* local LLM failure is safe;
* privacy controls work;
* all memories can be erased.

## Conversation readiness

Before longer LLM conversations:

* topic router exists;
* character constitution is immutable;
* health-advice rejection exists;
* serious-topic register exists;
* current-information limitation exists;
* authored fallback works;
* adversarial tests pass.

## CS2 readiness

Before CS2 development:

* Gate B is human-approved;
* desktop Willy is enjoyable independently;
* event contracts are stable;
* performance baseline exists;
* local LLM can be paused;
* Windows packaging is stable.

---

# 25. Simulation requirements

The project should support simulations for:

* eight hours of desktop activity;
* repeated dragging;
* repeated clicking;
* long work sessions;
* Willy sleeping and waking;
* den settlement;
* memory accumulation;
* cooldown behaviour;
* folder permission revocation;
* unavailable model;
* unavailable audio;
* corrupted settings;
* database interruption;
* repeated conversation attempts;
* serious-topic routing;
* prompt injection.

Simulations should use a fake clock so several days can be tested quickly.

---

# 26. Private beta workflow

## Build preparation

QA agent produces:

* versioned executable;
* changelog;
* known-issues list;
* tester instructions;
* local log location;
* feedback form.

## Build naming

```text
Willy Desktop Alpha 0.1.0
Willy Desktop Alpha 0.2.0
```

Optional tester identifier:

```text
WILLY-ALPHA-FRIEND-03
```

## Tester privacy

Private beta builds should:

* avoid cloud telemetry;
* store diagnostics locally;
* require explicit permission before logs are shared;
* contain no source code;
* contain no full design specification;
* display a no-redistribution notice.

## Agent role

Agents may prepare builds and reports.

The human decides:

* who receives builds;
* which bugs block distribution;
* when the beta expands.

---

# 27. Recommended initial agent setup

## First milestone

Use:

```text
Human
├── Lead Architect Claude Code session
├── Platform Claude Code worktree
├── Animation Claude Code worktree
└── QA Claude Code worktree
```

## Second milestone

Use:

```text
Human
├── Lead Architect
├── Character + Persistence
├── Den + Folder
└── QA
```

## Third milestone

Use:

```text
Human
├── Lead Architect
├── Conversation + LLM
├── Narrative
└── QA
```

Hermes may coordinate these sessions after the manual process is understood.

---

# 28. Agent-performance evaluation

Agents should be evaluated on:

* scope discipline;
* correctness;
* test quality;
* architectural compliance;
* clarity of reports;
* honesty about uncertainty;
* number of regressions;
* amount of unnecessary code;
* ability to preserve existing behaviour.

Do not evaluate agents primarily by:

* amount of code produced;
* speed alone;
* number of files changed;
* confidence of written summaries.

A smaller correct change is better than a large speculative implementation.

---

# 29. Common failure modes

## Too many agents

Result:

* conflicts;
* duplicated systems;
* inconsistent assumptions;
* excessive review burden.

Response:

* reduce parallelism;
* stabilize interfaces;
* split tasks more narrowly.

## Vague tasks

Result:

* scope expansion;
* architectural redesign;
* untestable output.

Response:

* rewrite task brief with owned paths and acceptance criteria.

## Agent trusts another agent's claims

Result:

* features reported as working without being run.

Response:

* require independent test evidence.

## Shared-file conflicts

Result:

* repeated merge conflicts;
* lost changes.

Response:

* assign explicit ownership;
* move shared types into approved contracts;
* serialize shared-interface work.

## Premature LLM work

Result:

* chatbot exists before Willy exists.

Response:

* block conversation implementation until deterministic personality works.

## Premature orchestration

Result:

* more time managing agents than building the application.

Response:

* return to one or two Claude Code sessions until workflow stabilizes.

---

# 30. Final operating rule

The multi-agent system should optimize for:

> Reliable, reviewable progress toward a coherent Willy.

It should not optimize for:

> Maximum number of autonomous agents running simultaneously.

The project succeeds when agents behave like disciplined specialists working from shared contracts—not like several enthusiastic programmers independently inventing different boars.
