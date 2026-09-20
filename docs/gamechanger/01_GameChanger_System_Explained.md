# GameChanger 3.0 — The Multi-Agentic System Explained, Step by Step

**Audience:** anyone on the IBC delivery team who has never seen GameChanger. No prior knowledge assumed.
**Date:** 2026-09-07 · **Author:** Prashanth Kothapalli
**Grounded in:** the GameChanger 3.0 source tree at `/Users/pkothapalli/storm-b2111773b5b61c/gamechanger3.0`, cross-checked against the published [GameChanger guide](https://p-kothapalli.github.io/gamechanger-agent-guide/).

> **How to read this.** Every agent gets the same five-field card. **Like this:** is the
> five-year-old version — one sentence, plain words, no jargon. **What it actually does** is the
> real, grounded sequence taken from the agent's own source and rule files. If you only have ten
> minutes, read §1, §2 and §3 and stop.

---

## Table of contents

| § | Section | What you get |
|---|---|---|
| 1 | [The whole thing in one page](#1-the-whole-thing-in-one-page) | The factory analogy |
| 2 | [Twelve words you need](#2-twelve-words-you-need) | Vocabulary |
| 3 | [How a run actually executes](#3-how-a-run-actually-executes) | The three phases |
| 4 | [The trust ladder](#4-the-trust-ladder--why-the-model-never-outranks-the-org) | Why it can't invent a field |
| 5 | [Layer A — the ten stage agents](#5-layer-a--the-ten-stage-agents) | 10 cards |
| 6 | [Layer B — the thirteen foundation agents](#6-layer-b--the-thirteen-foundation-agents) | 13 cards |
| 7 | [The governance layer](#7-the-governance-layer--critics-policies-councils-caag) | Critics, OPA, councils, CAAG |
| 8 | [The plumbing (the "tools")](#8-the-plumbing--every-tool-that-is-not-an-agent) | 11 subsystems |
| 9 | [Every file the system writes](#9-every-file-the-system-writes) | Artifact map |
| 10 | [The feature-flag surface](#10-the-feature-flag-surface) | What's on, what's off |
| 11 | [Where the docs and the code disagree](#11-where-the-docs-and-the-code-disagree) | Honest caveats |
| — | [Glossary](#glossary) | A–Z |

---

## 1. The whole thing in one page

### The problem it exists to solve

You hand an AI a story and say "build this." You get back something that **looks** right. It reads
well, it compiles, and it references a field called `PRM_PractitionerStatus__c` that **does not exist
in your org**. Nobody notices until deploy day. And here is the worst part: **nothing failed.**
There was no step that went wrong, because there were never any steps. There was one big answer, and
you either trust all of it or throw all of it away.

GameChanger takes the opposite bet.

### The factory analogy (this is the whole system)

Imagine you want to build a car, and instead of asking one very clever person to "make me a car,"
you build a **factory**.

> **1. The assembly line has ten stations.** Station 1 reads the customer's order. Station 2 writes
> the plan. Station 3 draws the blueprint. Station 4 writes the test checklist. And so on, to
> Station 10, which packs the manual in the glovebox. **Each station does exactly one job and writes
> exactly one note** about what it did. If the car is wrong, you can walk down the line and point at
> the station that did it.
>
> **2. Next to eight of the stations stands an inspector with a clipboard.** The inspector doesn't
> build anything. It scores the note the station wrote, and if the score is too low it says
> "**do it again**" and hands the note back with the reasons circled in red. That's a *critic*.
>
> **3. Thirteen more people work in the building but are not on the line.** One walks out to the car
> park with a tape measure and writes down what the *real* cars actually look like, so nobody designs
> against a fantasy. Three read the customer's order and argue about whether it even makes sense
> before a single bolt is turned. Five gather all the paperwork, check it's complete, score it, decide
> who needs to sign it off, and staple it into a folder for the board. Three work *after* the car
> rolls off: one road-tests it properly, one writes down every mistake the factory made this month,
> and one — only with a human's explicit say-so — actually goes and fixes the machines. And one is a
> specialist for a completely different kind of vehicle, who stays home unless you call him.
>
> **4. There is one rule above all others: if the blueprint and the real car disagree, the real car
> wins.** Always. A two-week-old planning document does not get to overrule what the org actually
> contains today.
>
> **5. And the twist:** the stations don't run themselves. The factory prints a **job card** for each
> station and hangs it up. Then *you* walk in — in Cursor — and the AI in your editor works through
> the job cards, with live access to the real org so it can check its own claims. Then the factory
> collects the finished notes and validates them.

That's it. That's GameChanger. Ten stations, eight inspectors, thirteen specialists, one trust rule,
and a human in the middle.

### The two questions this design answers

| Question | Answer |
|---|---|
| *"How do I know it didn't invent that field?"* | Every stage must climb a fixed **verification ladder** — knowledge bundle first, then live SOQL against the read-only org, then Jira/Confluence. Only if all three miss may it write the field, and then it **must** label it `[Inferred: UNVERIFIED]` and raise an open question. The system even pre-computes the likely misses and hands the agent the exact SOQL to run (`pendingVerifications`). |
| *"What happens when a stage gets it wrong?"* | A **critic** scores it. A critical finding, or a score in the middle band, returns `REFINE_AGAIN` and the stage re-runs with the critic's feedback attached — up to the iteration cap. |

### The count: why 23 agents

```
10 stage agents      (the assembly line — you never call these individually)
+ 13 foundation agents (standalone tools with their own commands and flags)
= 23 agents
```

Plus a governance layer that is *not* counted as agents: **8 stage critics**, **3 lightweight
contract checks**, **7 OPA policy files**, **2 councils** (16 specialist personas between them), and
**CAAG** (a program-memory governance layer with 18 modes). Those are covered in §7.

> **The point of 23 agents is not that 23 is better than 1.** It is that when something goes wrong,
> you get to ask *which one*.

---

## 2. Twelve words you need

| Word | Plain meaning |
|---|---|
| **Stage** | One station on the assembly line. Ten of them, `00-intake` through `09-docs`. |
| **Artifact** | The one markdown note a stage writes, e.g. `03-tdd.md`. |
| **Stage agent** | The worker at a station. You never call it directly. |
| **Foundation agent** | A worker who isn't on the line. Has its own command and its own on/off switch. |
| **Critic** | The inspector. Scores an artifact and can send it back. |
| **Verdict** | What the inspector says: `ACCEPT`, `ACCEPT_WITH_CAVEATS`, `REFINE_AGAIN`, or `ESCALATE_TO_HUMAN`. |
| **Task file** | The job card: `cursor-tasks/03-tdd.task.json`. Carries the prompt and the hints. |
| **Trust class** | How much a piece of context is allowed to be believed. Five levels (§4). |
| **Knowledge bundle (KP)** | A cached snapshot of what's really in the org. Refreshed every 4 hours. |
| **`pendingVerifications`** | Pre-written SOQL handed to the agent to prove a field is real before it writes about it. |
| **Evidence bundle** | The folder of everything gathered about one feature — requirements, risks, findings, scores. |
| **Feature flag** | An on/off switch, almost always **off** by default. |

---

## 3. How a run actually executes

This is the part that surprises everyone, so read it slowly.

**You would expect** the TypeScript pipeline to call a model API for each of the ten stages. **It does
not.** The pipeline writes a job card per stage and then *stops*.

The source says so plainly. From `control-plane/execution/context-bridge/llm-provider.ts`:

> Default: CursorTaskProvider (writes task files for Cursor AI to fulfill). For v1, Cursor AI is the
> only supported generation runtime.

And from `control-plane/commands/feature-orchestrate.ts`:

> `No API-key fallback is supported.`

So a run is **three phases with a human step in the middle**.

### Phase 1 — Context assembly (a CLI command)

**Like this:** the factory prints the job cards and hangs them up.

```bash
cd control-plane

./scripts/run-production.sh \
  --feature <FEATURE-KEY> \
  --story-keys <STORY-1>,<STORY-2> \
  --filter ALL \
  --sequencing dependency-first \
  --phase context-assembly \
  --runs-dir ../runs
```

| Flag | What it means |
|---|---|
| `--feature` | The parent feature key. Required. |
| `--story-keys` | Comma-separated story keys. Required. |
| `--filter` | `READY` (default) · `READY_AND_REFINEMENT` · `ALL` |
| `--sequencing` | `dependency-first` (default) · `risk-first` · `arch-first` · `ai-reasoned` |
| `--phase` | `context-assembly` or `extract-only` |
| `--runs-dir` | Where output goes. Defaults to repo-root `/runs`. |
| `--dry-run` | Print the sequencing plan and stop. |
| `--allow-degraded` | Tolerate degraded stages. |
| `--skip-preflight` | Emergency bypass. `run-production.sh` always injects `--strict-preflight`, so this is the only way past a warning. |
| `--force-full-fetch` | Ignore the cache: sets `FRESHNESS_GATE_ENABLED=0` and `DELTA_REFRESH_ENABLED=0`. |
| `--max-stories <n>` | Default `50`. |
| `--rework-from-cycle <n>` | Copy a prior cycle's artifacts into the live story run. |

**Before it starts** it reports how fresh the knowledge bundle is. Under **4 hours** old
(`FRESHNESS_TTL_HOURS = 4`, or 14400 seconds in the shell check) is a cache hit. Older triggers an
incremental delta refresh, or a full re-seed if delta refresh is disabled.

**What it writes:**

```
runs/<feature>/orchestration/cursor-completion-manifest.json
runs/<feature>/story-runs/<story>/cursor-tasks/00-intake.task.json
                                                01-plan.task.json  … one per stage
runs/org/sourceprimary/knowledge-prep/<snapshotId>/bundle.json
runs/<feature>/preflight-<runId>.md
```

**Checkpoint:** open `cursor-completion-manifest.json`. It should list one pending task per stage per
story, each with a task path and an expected output path. **An empty pending list means no work was
scheduled** — usually a story key that doesn't resolve.

### Phase 2 — Generation (the human step; there is no command)

**Like this:** you walk in and do the work at each station, with the real car in front of you.

You open the workspace in Cursor, and **Cursor's own agent** works through the job cards. For each one it should:

1. Read `cursor-tasks/<stage>.task.json` — it carries `systemPrompt`, `userPrompt`, and `contextHints` pointing at prior artifacts and the knowledge bundle.
2. **Run every `pendingVerifications` query against the read-only org *before* writing any field-level claim.**
3. Write the artifact to the task's `expectedOutputPath` — which is the *story run* directory.

The job card's exact shape, from `CursorTaskProvider.generate()`:

```json
{
  "stageId": "03-tdd",
  "storyKey": "…",
  "featureKey": "…",
  "expectedOutputPath": "<storyRunDir>/03-tdd.md",
  "systemPrompt": "…",
  "userPrompt": "…",
  "contextHints": {
    "priorArtifacts": ["…"],
    "kpBundlePath": "…",
    "runsDir": "…",
    "storyRunDir": "…",
    "pendingVerifications": [ { "type": "…", "objectName": "…", "fieldName": "…", "soql": "…", "reason": "…" } ]
  },
  "createdAt": "…"
}
```

**Checkpoint:** every stage file exists and none still contains its placeholder marker. A stage
sitting at status `cursor_pending` is **waiting, not broken** — it means the job card is written and
Phase 2 hasn't reached it. A placeholder that survives into Phase 3 *fails extraction*.

**Why it works this way:** the generating agent needs live tool access — it must run SOQL, retrieve
metadata, and read the repo *while* it writes. A detached model API call could not verify its own
claims, which would defeat the entire verification ladder the design rests on.

### Phase 3 — Extraction (a CLI command)

**Like this:** the factory collects the notes, checks none are blank, and closes the job out.

```bash
./scripts/run-production.sh \
  --feature <FEATURE-KEY> \
  --story-keys <STORY-1>,<STORY-2> \
  --phase extract-only \
  --runs-dir ../runs
```

It validates all ten stage files (missing or placeholder → fail) and writes:

```
runs/<feature>/story-runs/<story>/story-extraction-packet.json
runs/<feature>/orchestration/execution-manifest.json
```

**Checkpoint:** a `story-extraction-packet.json` exists per story and the execution manifest is
updated. If extraction rejects a file as a placeholder, go back to Phase 2 **for that one stage** —
you do not need to re-run Phase 1.

---

## 4. The trust ladder — why the model never outranks the org

**Like this:** if the drawing and the real thing disagree, the real thing wins. Always. And old
drawings slowly stop counting at all.

When two sources of context disagree, **precedence decides** — not recency, not specificity, and
certainly not which one the model found more convincing.

From `control-plane/knowledge-prep/context-pack.ts`:

| Rank | Trust class | What lives here | Can it state a platform fact? |
|:--:|---|---|---|
| 0 | **`authoritative`** | Live org metadata and SOQL results | **Yes — wins everything** |
| 1 | `scoping` | Contract / statement-of-work packs | No. Bounds what's in scope only |
| 2 | `guidance` | Architecture standards, reference docs | No |
| 3 | `persona` | Role profiles shaping tone and audience | No |
| 4 | `background` | Narrative colour | Never decisive |

`TRUST_CLASS_PRECEDENCE = { authoritative: 0, scoping: 1, guidance: 2, persona: 3, background: 4 }`
— **lower number = higher authority.**

### Context packs also decay and compete for a budget

| Constant | Value | Meaning |
|---|---|---|
| `DEFAULT_TOKEN_BUDGET` | **4000** | Shared budget for *everything below authoritative* |
| `SUB_BUDGET.authoritative` | `Infinity` | Authoritative packs are admitted regardless of what's left |
| `SUB_BUDGET.scoping` | **800** | A scoping pack is capped hard |
| `SUB_BUDGET.guidance` | **1200** | |
| `SUB_BUDGET.persona` | **600** | |
| `SUB_BUDGET.background` | **400** | |
| `FRESHNESS_DECAY_HOURS` | **24** | Freshness falls **linearly** over 24 hours, then resolves to nothing |

That decay rule is the important one: **a scoping pack does not linger as stale influence on a later
build.** After 24 hours it is worth zero, not "a bit less."

### The verification ladder (the per-claim version of the same idea)

Every stage that asserts an object or field exists must climb this, in order:

1. **KP bundle** — the cached org snapshot → label `[Verified: KP Bundle <snapshotId>]`
2. **Live org** — `run_soql_query` against the read-only alias (`FieldDefinition` / `EntityDefinition` / platform-event `LIKE`) → the architecture stage may also `retrieve_metadata`
3. **Jira / Confluence** → `[Verified: Jira]` / `[Verified: Cortex]`
4. **`[Inferred: UNVERIFIED]`** — last resort, and it **must** raise an open question if anything downstream depends on it

There is no fifth option. **Every claim is traceable to something outside the model, or explicitly
admitted as unverified.**

### A wrinkle worth knowing: there are *two* trust vocabularies

`control-plane/source-trust-registry.json` uses a **different, wider enum** than the context-pack
ladder: it adds `high-trust`, `advisory`, and `experimental`. They are **not the same enum** — do not
map one onto the other by name.

---

## 5. Layer A — the ten stage agents

**Like this:** the ten stations on the line. You never call one. You start a run and all ten get a
job card, in order.

Defined in `control-plane/execution/contracts.ts`:

```ts
export const STAGE_ORDER: StageId[] = [
  '00-intake', '01-plan', '02-architecture', '03-tdd',
  '04-code-review', '05-build-fix', '06-e2e',
  '07-security', '08-refactor', '09-docs',
];
```

| Stage | Agent | Artifact | Critic tier | Rework target |
|---|---|---|---|---|
| `00-intake` | `orchestrator` | `00-intake.md` | lightweight | — |
| `01-plan` | `planner` | `01-plan.md` | standard | — |
| `02-architecture` | `architect` | `02-architecture.md` | **full** | — |
| `03-tdd` | `tdd-guide` | `03-tdd.md` | standard | — |
| `04-code-review` | `code-reviewer` | `04-code-review.md` | standard | **`03-tdd`** |
| `05-build-fix` | `build-error-resolver` | `05-build-fix.md` | standard | **`03-tdd`** |
| `06-e2e` | `e2e-runner` | `06-e2e.md` | standard | **`03-tdd`** |
| `07-security` | `security-reviewer` | `07-security.md` | **full** | **`03-tdd`** |
| `08-refactor` | `refactor-cleaner` | `08-refactor.md` | lightweight | — |
| `09-docs` | `doc-updater` | `09-docs.md` | lightweight | — |

Every stage agent lives in the same place, with the same four files:

```
control-plane/execution/stages/<stageId>/
    SKILL.md      ← what to do (the rubric)
    RULES.md      ← what you must never do (the hard gates)
    tools.yaml    ← which tools you are allowed to call
    agent.ts      ← the wiring
```

### The rework map, and a caveat

```ts
export const REWORK_TRIGGERS: Record<StageId, StageId | null> = {
  '04-code-review': '03-tdd',
  '05-build-fix':   '03-tdd',
  '06-e2e':         '03-tdd',
  '07-security':    '03-tdd',
  // all others: null
};
```

The reasoning is sound: **if the tests were wrong, everything built on them is suspect.** But know
this before you rely on it — **the map is declared and not yet executed.** The critic loop as it ships
re-runs the *failing* stage in place. So today the jump back to `03-tdd` is a call *you* make, not one
the pipeline makes for you.

Stage status values: `complete` · `cursor_pending` · `degraded` · `failed`.

---

### `00-intake` → agent `orchestrator`

> **Like this:** the person at the front desk who reads the customer's order, checks it's actually a
> real order, and writes down what was asked for — going and *looking* at the real thing rather than
> guessing.

**What it actually does:**

1. Apply the **story status gate** *first*. A story that is `Blocked`, `Cancelled`, `Won't Do`, or in `Technical Refinement` stops here rather than generating content nobody will use. `Won't Do`/`Cancelled` → `PIPELINE_SKIP`. `Blocked` with no named blocker → `HARD_BLOCKER` pause.
2. Pre-flight the ticket connection (`atlassian_health_check`).
3. Pull the Jira issue and its parent, then run a **quality check on the context pack**. If the pack is irrelevant to the story, fall back to a Confluence search rather than using it.
4. Extract requirements and acceptance criteria using a **fixed field priority**: the AC field → the high-level design → the description → the parent → comments.
5. Execute the supplied `contextHints.pendingVerifications` SOQL **before** writing the reconnaissance section.
6. Record legacy identifier touchpoints, risks, references, and a **mandatory Mermaid `flowchart TD`** dependency diagram; label anything unproven `[Inferred: UNVERIFIED]` with an open question attached.
7. Write the handoff section the planner will consume.

**Reads:** Jira issue + parent · KP bundle · context pack · `pendingVerifications` · Confluence on fallback
**Writes:** `00-intake.md` + `00-intake.meta.json`
**Mandatory sections:** Feature Metadata · Requirements · AC · Dependency Map · §4a Org Reconnaissance · §4b Legacy Id Touchpoints · Risks · References · Handoff to PLAN

**When it blocks you:** a story failing the status gate produces a stub *by design* — fix the Jira
status, don't fight the agent. And note a real defect: **its rule file requires SOQL while its
`tools.yaml` grants no Salesforce tools at all.** If verification silently degrades, that mismatch is
the first place to look.

---

### `01-plan` → agent `planner`

> **Like this:** turns "I want a car that's good in snow" into a numbered list of things you can
> actually tick off, and an honest guess at how big the job is.

**What it actually does:**

1. Consume the intake brief — requirements, acceptance criteria, risks, open questions.
2. Reconnoitre the org: profiles, permission sets, apps, objects and fields — **bundle first, live SOQL second** (max 5 SOQL queries).
3. Record **Decisions Made** explicitly, using an **out-of-the-box-first ladder**: validation rule → flow → formula → Apex. Middleware-first where integration constraints apply.
4. Rewrite the acceptance criteria into **formalised, testable** form (`AC-NN`, with a testable flag). **This is the version every later stage traces against.**
5. Break the work into phases with T-shirt sizes (S/M/L/XL); build the dependency list and risk register.
6. For integration stories, define the **Error Response Contract** — status codes, payload schema, fault handlers — or raise an open question if it can't be determined.
7. Emit a mandatory Mermaid diagram.

**Reads:** `00-intake.md` · KP bundle · live SOQL · context pack
**Writes:** `01-plan.md` + `.meta.json`

**When it blocks you:** the plan critic returns `REFINE_AGAIN` when requirements are untraced. **If
the plan keeps bouncing, the requirements in intake were too vague to trace — fix the story, not the
plan.** It must never invent an answer to a `HARD_BLOCKER` open question; it writes `PLACEHOLDER`
instead.

---

### `02-architecture` → agent `architect` · **strictest critic**

> **Like this:** draws the blueprint. But before it draws a single box it goes and *checks that every
> part it's about to draw actually exists in the warehouse*.

**What it actually does:**

1. Read the plan and intake; leave `HARD_BLOCKER` open questions as explicit `PLACEHOLDER`s rather than guessing past them.
2. Run the **§0 pre-flight verification** — confirm every platform event, object and field exists via the bundle, `run_soql_query`, or `retrieve_metadata`, **before** designing against it. Platform events get a three-outcome gate.
3. Author the architecture decision records (ADRs), the component diagram (`flowchart TD`), and the object model with its **mandatory `erDiagram`**.
4. Build the **metadata inventory** (plus legacy-sync touchpoints) and note the automation paradigm the org is locked into.
5. Where the design calls out to an external system, produce the **integration handoff packet** (mandatory when a remote-call-in pattern is selected).
6. Walk **anti-pattern gates 1–12** by name.
7. Write the test-design instructions stage `03` will turn into specifications.

**Reads:** `01-plan.md` · `00-intake.md` · live SOQL + metadata retrieve · optional CAAG injection
**Writes:** `02-architecture.md` + `.meta.json` · ADRs · object model · metadata inventory

**When it blocks you:** this stage gets the **full-tier** critic. A hallucinated field or object is
`CRITICAL`. Both Mermaid diagrams are mandatory. **Diagram syntax errors are the most common and most
annoying failure** — they fail the stage even when the design itself is sound. (Caveat: the *critical*
Mermaid parse gate is written in the critic's `SKILL.md` but is **not implemented** in its `agent.ts`.)

---

### `03-tdd` → agent `tdd-guide` · **the declared rework destination**

> **Like this:** writes the test checklist *before* anyone builds anything, so "done" means something
> specific instead of "looks fine to me."

**What it actually does:**

1. Take the formalised acceptance criteria from the plan and the design from architecture.
2. Write a **test specification per criterion** — positive, negative and bulk — with naming, steps, expected results and priority.
3. Add the SOQL validation queries that prove the expected data state; estimate coverage against targets (**≥75% Salesforce, ≥80% harness**).
4. Design the **test data factory** so tests never depend on org data.
5. Write the **red → green → refactor** walkthrough the build stage will follow, plus a mandatory TDD-cycle diagram.
6. Hand off to code review.

**Reads:** `01-plan.md` formalised criteria · `02-architecture.md` design
**Writes:** `03-tdd.md` + `.meta.json`

**When it blocks you:** more than **4** uncovered acceptance criteria triggers `CRITICAL`. This is
also the stage that stages `04`–`07` name as their rework target — so **a weak TDD artifact doesn't
fail once, it comes back at you four stages later.** On rework it must *preserve and add* tests, never
remove passing ones.

---

### `04-code-review` → agent `code-reviewer` · declares `03-tdd` rework

> **Like this:** reads everything written so far and marks it up in red pen, then decides whether the
> job is allowed to move to the next station.

**What it actually does:**

1. Load artifacts `00` through `03`. **A missing artifact is itself a critical finding** — the gate will not pass on partial input.
2. Review against the platform rule set: bulkification, governor limits, sharing and field-level security, error handling, trigger patterns.
3. Emit numbered **findings with severities** and a checklist (minimum 7 checks) marked pass / fail / pending.
4. Apply the **gate decision**: no critical or high findings → proceed; a critical finding blocks and sets status `degraded`; a missing or inadequate TDD artifact blocks back to `03-tdd`.
5. Write prioritised recommendations and hand off to build-fix.

**Reads:** all prior artifacts · implementation files where they exist · ADRs
**Writes:** `04-code-review.md` + `.meta.json` · findings · `canProceed` · optional rework target

**When it blocks you:** its own critic checks whether **severities were assigned honestly** — a high
or critical finding that contradicts the approved architecture is itself a critical finding *against
the reviewer*. **Understating severity to get through the gate does not work.**

---

### `05-build-fix` → agent `build-error-resolver` · **the only stage that deploys**

> **Like this:** actually builds the parts, tries to fit them, and when something doesn't fit, works
> out *why* before changing anything — and only ever test-fits, never ships.

**What it actually does:**

1. Treat the architecture decisions plus the code-review findings as the **fix backlog**.
2. Generate the metadata — objects, fields, Apex, and the rest (API 62.0 in this tree).
3. **Classify every error by kind** — compile, metadata, dependency, governor, or test failure — because the fix strategy differs by class.
4. Apply the **minimal fix**, re-run the **check-only** deploy, and confirm that specific error is gone.
5. Run the validation checklist and record deploy and test counts.
6. On a critic refine, **patch in place** rather than regenerating from scratch; **escalate after three identical failures** instead of looping.

**Reads:** `02-architecture.md` · `04-code-review.md` findings · SF DX deploy/test tools
**Writes:** `05-build-fix.md` · metadata files · build errors · check-only deploy result

**When it blocks you:** this is **the one stage with write access, and it is check-only, to the single
designated deploy-target alias only**. If deploys fail on permissions, verify the target alias before
touching the metadata — **the guard is deliberate.** (Caveat: its rules require `get_username`,
`retrieve_metadata` and `run_soql_query`, none of which are in its `tools.yaml`.)

---

### `06-e2e` → agent `e2e-runner` · declares `03-tdd` rework

> **Like this:** actually road-tests the car — and if it couldn't test the brakes, it *writes down
> that it couldn't test the brakes* instead of ticking the box.

**What it actually does:**

1. Build the test plan from the TDD specification and **map coverage back to each acceptance criterion**.
2. Identify the critical flows: happy path, error path, boundary, bulk, permissions.
3. Lead the artifact with an **Executive Readiness Verdict** — at least **eight** red/amber/green dimensions plus an overall line. **This table is mandatory.**
4. Maintain a **blocker registry** for every scenario not run or blocked — or state explicitly that there are none.
5. Execute what can be executed against the deploy-target sandbox and mark the rest **NOT RUN**. **Fabricated passes are the exact failure mode this stage exists to prevent.**
6. Fill the execution matrix with criterion links and hand off to security.

**Reads:** `03-tdd.md` · build-fix deploy status · Apex tests / SOQL on the deploy target
**Writes:** `06-e2e.md` · execution matrix · blockers · traceability entries

**When it blocks you:** more than **3** acceptance criteria with no end-to-end path is `CRITICAL`.
**Marking a test *not run* is acceptable and expected; claiming it passed when it did not is the thing
the critic hunts for.** (Caveat: the "missing readiness table = CRITICAL" rule is in the critic's
`SKILL.md` but not in its `agent.ts`.)

---

### `07-security` → agent `security-reviewer` · **full-tier critic**

> **Like this:** asks "who can open which door, and what happens if a bad person tries?" — and refuses
> to shrug about the answer.

**What it actually does:**

1. Review the architecture and plan alongside whatever build and test evidence exists.
2. Build the **object and field permission matrix** (CRUD/FLS), naming the preferred enforcement method for each entry.
3. Walk the **OWASP top ten**, plus the mobile list where the story warrants it.
4. Review connected-app OAuth scopes — an unjustified **`full` scope is a critical finding on its own**.
5. Run the **secret detection** scan across generated artifacts.
6. Classify every finding critical → low, and **update** the matrix on each refine iteration rather than restating it.
7. Emit a mandatory security-posture diagram.

**Reads:** architecture and plan · implementation claims · policy context packs
**Writes:** `07-security.md` · permission matrix · OWASP checklist · secret scan result

**When it blocks you:** zero tolerance on critical. Unencrypted PII, unjustified `full` OAuth scope,
HTTP-not-TLS, injection risk, detected secrets, and permission gaps are all `CRITICAL` → status
`degraded` + human flag. Note: **this stage has no org access in its allowlist**, so it reasons from
the artifacts — if they're vague, its findings will be too.

---

### `08-refactor` → agent `refactor-cleaner`

> **Like this:** tidies up — sweeps the floor, puts tools back. It is **not allowed to change how the
> car drives.**

**What it actually does:**

1. Identify dead code and unused imports; remove them **only where the tests still pass afterwards**.
2. Extract repeated literals into constants, custom labels, or custom metadata as the situation warrants.
3. Align naming with platform conventions; apply DRY.
4. Log every entry with **behavioural change explicitly `false`**. Anything that *would* change behaviour gets **flagged for a separate story** instead of being done here.
5. Document configuration debt with priorities — flag it, don't fix it.
6. If the critic flags a behavioural change, **revert it** and re-validate.

**Reads:** prior artifacts and the implementation they describe
**Writes:** `08-refactor.md` · refactoring log · configuration-debt register

**When it blocks you:** only a hard generation failure returns `REFINE_AGAIN` here — this stage is
checked **lightly**. **The real risk is the opposite of a block: a behavioural change slipping through
labelled as cleanup.**

---

### `09-docs` → agent `doc-updater`

> **Like this:** writes the owner's manual and the delivery note, so the person who has to actually
> install this thing on Friday night knows exactly what to type.

**What it actually does:**

1. Synthesise every prior stage — status, security findings, test results, architecture decisions.
2. Write the **deployment runbook**: pre-deploy, deploy, and post-deploy commands, targeting the **deploy-target sandbox only**, with wait and test settings.
3. Document the **permission model** — which sets, which objects, which personas, and which stage each requirement came from.
4. Build full **traceability** linking evidence → acceptance criteria → artifacts, and emit it as a machine-readable `traceability.json` alongside the prose.
5. Produce a summary that can be pasted straight into the ticket.
6. Cross-reference architecture decisions and security findings so a reviewer can navigate without opening all ten files. **List degraded stages honestly.**

**Reads:** all prior `NN-*.md` artifacts
**Writes:** `09-docs.md` · `traceability.json` · runbook and permission sections

**When it blocks you:** lightly checked, so it rarely blocks. **But it is only as good as its inputs —
if earlier stages left placeholders, the runbook inherits them.**

---

## 6. Layer B — the thirteen foundation agents

**Like this:** the people in the building who aren't on the line. Each has its own door and its own
light switch — and **almost every switch is off when the building is handed to you.** An installation
that never sets a flag behaves exactly as if these agents did not exist.

> **A correction worth flagging:** GameChanger 2.0 had a fourteenth agent, `hls-delivery-architect`,
> which produced a pre-pipeline solution design. **It is absent from 3.0** — no directory, no skill,
> no identifier match anywhere in the tree. Its job (seeding stages `00`–`02` with a `scoping` pack)
> is now done by the context-pack adapters. Don't plan around it.

They come in four groups.

---

### Group 1 — Expert review (4 agents, strictly ordered)

**Like this:** four people read the customer's order and argue about it *before* anyone builds. In a
fixed order, because there's no point technically reviewing a story you've misunderstood.

Gated by **`EXPERT_REVIEW_V2=1`** (default **off**; not even present in `.env.example`). Pipeline:
`control-plane/temporal/expert-review-pipeline.ts` — header reads `BA → Tech → Gov → Refinement → optional rerun`.

#### `ba-context` (id `ba-context-analyst`) · expert review **step 1**

> **Like this:** works out the actual human story — who wants this, what changes for them, and how
> anyone would know it worked.

1. Analyse the **user journey** the story sits inside.
2. Establish the **business goal and outcome** — what changes for whom, and how anyone would know.
3. Run the **readiness and gap** pass, producing **explicit questions rather than assumptions**.
4. Layer in customer context.
5. Infer the assumptions the story depends on but does not state.
6. Derive a verdict: **`NOT READY`** / **`CONDITIONALLY READY`** / **`READY FOR DEV`**.

**Reads:** evidence bundle · requirements · story description · project/governance context
**Writes:** `story-gap-analysis.md` (stage `02-ba`) · journey and goal summaries · gap questions · assumption records
**Blocks:** a missing evidence bundle makes **the whole quartet return nothing** — run the knowledge agent first. Individual skill failures degrade to warnings and still produce a verdict.

#### `sf-tech-reviewer` · expert review **step 2**

> **Like this:** the engineer who reads the story *as the analyst understood it* and asks "what will
> actually break?"

1. Infer which platform objects the story touches from its text and acceptance criteria.
2. Build its input from the analyst's gaps, assumptions, journey and goal — **it reviews the story as understood, not as written.**
3. Run four domain reviews: **code (Apex)**, **declarative automation (Flow/Omni)**, **data model**, and **test quality**.
4. Scan for **cross-cutting concerns** no single domain owns.
5. Compute a verdict, recording which domains were reviewed and which were **skipped**.

**Writes:** `technical-review.md` (stage `03-technical`) · findings · domains reviewed/skipped
**Blocks:** if every domain skips, the verdict is **`INSUFFICIENT EVIDENCE`** rather than a pass. **That is a signal the story lacks technical substance, not that the agent failed.**

#### `gov-risk` (id `gov-risk-analyst`) · expert review **step 3**

> **Like this:** the person who decides whether this is safe to say yes to — and it's advice, not a
> substitute for an actual board.

1. Combine the analyst and technical reviewer outputs into one governance input.
2. Run the **risk assessment** across the combined findings.
3. Evaluate **readiness** against what governance requires, not just what engineering wants.
4. Map **dependency exposure** — what else breaks if this ships wrong.
5. Assess **change impact** on adjacent systems and processes.
6. Derive the recommendation: **`approve`** / **`defer`** / **`reject`**.

**Writes:** `governance-risk-summary.md` (stage `04-governance`) · risk signals · decision records
**Blocks:** with **no** reject or defer decisions recorded, the recommendation **defaults to `approve`**. **Treat a clean approve on a thin evidence bundle with suspicion rather than relief.**

#### `refinement` (id `refinement-challenge`) · expert review **step 4**

> **Like this:** the person who reads the other three reviews and says "half of this would be true of
> any story — that isn't a finding." Then decides what needs re-doing.

1. Run **genericity detection** across the prior outputs — **findings that would be true of any story are not findings.**
2. Process the **assumption lifecycle**, folding in human answers to the analyst's questions.
3. Process explicit human **overrides** as decision records, **so a disagreement is recorded rather than silently applied**.
4. Determine the **rerun scope** from the sessions and the human input: `none` · `ba-only` · `ba-tech` · `gov-only` · `full-replay`.
5. Emit a delta record describing what changed and why. **It does not mutate prior agent outputs.**

**Writes:** `refinement-delta.md` (stage `05-refinement`)
**Blocks:** with no human input, scope stays `none` and the agent is close to a no-op. **Its value is entirely in the answers you give it — run it after a human has responded to the gaps, not before.**

---

### Group 2 — Assurance review (5 agents: gather → audit → score → route → package)

**Like this:** the paperwork chain. Somebody collects the evidence, somebody checks it's complete,
somebody scores it, somebody decides who has to sign, and somebody staples it into a folder for the
board. **Every step degrades gracefully** — a failure lowers the confidence of the result rather than
stopping the review.

Orchestrated by `control-plane/temporal/workflows/assurance-review-v2.ts`, with a CLI mirror at
`tsx commands/dab-review.ts <STORY-KEY>`. **No master feature flag.** Step labels are in the code:

| Step | Agent | Activity |
|---|---|---|
| **1a** | `knowledge-agent` | `enrichKnowledgeActivity` |
| 1b | *(legacy intake — not an `agents/` agent)* | `intakeActivity` |
| **1c** | `evidence-auditor` | `auditCompletenessActivity` |
| **2a** | `scoring-agent` | `scoreEvidenceActivity` |
| **2b** | `policy-router-agent` | `routePoliciesActivity` |
| 3 | *(approval wait — Temporal signals)* | 48h review / 24h escalate timeouts |
| **4** | `packet-synthesizer` | `synthesizePacketActivity` |

#### `knowledge-agent` · assurance **step 1a** · strictly read-only everywhere

> **Like this:** the one who walks out to the car park with a tape measure. It reads the real world and
> writes nothing to it.

1. **Health-check** the ticket system connection before attempting anything else.
2. Deep-fetch the issue and convert it into a structured **`Requirement`**.
3. Search the wiki, **capped at 3 results**, and convert relevant pages into **`DecisionRecord`s**.
4. **Infer which platform objects the acceptance criteria imply**, and retrieve their metadata from the read-only org.
5. Update the **evidence bundle** with every object identifier gathered.

**Reads:** Jira + Confluence over the guardrail connector · read-only org metadata (`run_soql_query`, `retrieve_metadata`)
**Writes:** evidence objects + an updated bundle · a **`degraded` flag with reasons**
**Blocks:** **it does not block.** Every external failure marks the run `degraded` and continues — **which means a bundle can look present while being nearly empty.** Check the degraded reasons before trusting any downstream score.
**Known defect:** its `index.ts` re-exports `./sourceprimary-connector.js`, but **that file does not exist** on disk (the real file is `devint2-connector.ts`).

#### `evidence-auditor` · assurance **step 1c**

> **Like this:** checks the folder is actually complete before anyone pretends to review it.

1. Load the evidence bundle. **If it is absent, raise a `CRITICAL` finding and escalate immediately.**
2. Apply the **completeness rules** for the review type, separating required from optional fields.
3. Evaluate the completeness policy **through the OPA policy engine** rather than by hand-coded logic.
4. Attach the resulting finding identifiers back onto the bundle.
5. Return an outcome of **`pass`** / **`review`** / **`escalate`**. Completeness means **no high-severity findings remain**.

**Writes:** findings · updated bundle · `complete` flag · policy outcome
**Blocks:** incomplete evidence does **not** stop the workflow — it flows through as findings. **If a board packet reads thin, this agent already told you why; read its findings before blaming the packet.**

#### `scoring-agent` · assurance **step 2a** · ⚠️ **deprecated**

> **Like this:** gives the folder a mark out of ten. **But there are two markers in the building using
> different scales — check which one your install uses before you quote a number to a board.**

1. Load findings, policy traces and risk signals from the bundle.
2. Compute four dimensions: **AMI** architecture maturity (weight `0.30`) · **PHI** policy health (`0.25`) · **ECI** evidence completeness (`0.25`) · **RRI** risk readiness (`0.20`).
3. Combine into a weighted aggregate — architecture weighted highest, risk lowest.
4. Convert to a recommendation: **`approve` ≥ 0.8** · **`defer` ≥ 0.6** · **`reject` < 0.6**.
5. Persist the scorecard and link it to the bundle so policy routing can read it.

**Blocks:** it **throws** without a bundle, and the workflow catches that and continues *unscored*.
**Deprecation, quoted from `control-plane/schema/score-card.ts`:**

```
@deprecated ScoreCard v1 (4-dimension) is superseded by ScoreCardV2 (8-dimension).
New code should use ScoreCardV2Schema from score-card-v2.ts.
```

The live successor is `services/scoring/multi-dimensional-scorer.ts` — see §7.4.

#### `policy-router-agent` · assurance **step 2b**

> **Like this:** decides whether this can go through on the nod, needs a person to look at it, or needs
> escalating — and to whom. Runs *after* scoring so it can use the score.

1. Evaluate the **evidence completeness** policy.
2. Where risk signals exist, evaluate **risk escalation**.
3. **Validate each waiver** — an expired or improper waiver **does not silence the finding it was meant to cover**.
4. Read the aggregate score and evaluate **approval routing** against the thresholds (`auto_approve` 0.8, `l2_review` 0.6) → target `auto-approved` / `L2-orchestrator` / `L3-human`.
5. Roll the individual outcomes up to the **worst** result — **one `escalate` escalates the whole review.**
6. Persist the **policy traces** so the decision is auditable after the fact.

**Blocks:** it **throws** without a bundle (the workflow falls back to a legacy `policyActivity`). It does **not** wait for humans itself — the workflow does that on its behalf, **auto-deferring if nobody responds within the escalation window**.

#### `packet-synthesizer` · assurance **step 4**

> **Like this:** staples everything into one folder a busy executive can read in five minutes.

1. **Hydrate** everything the bundle points at — requirements, decisions, risks, findings, policy traces, scorecard.
2. Map the **human decision**, or the router's decision if there was no human, into `approve` / `defer` / `reject`.
3. Build the executive summary and the body sections from the chosen template.
4. Create the `BoardPacket` record and write it out as **both prose and structured data**.
5. Mark the bundle's pipeline status **complete**.

**Writes (exact):** `runs/<featureId>/boardpacket-v2.md` and `boardpacket-v2.json`; with a `runId`, `runs/<runId>/06-board-packet/boardpacket-v2.md`
**Blocks:** it **throws** without a bundle — a harder failure than upstream agents.
**Note the filename:** some workflow comments still say `board-packet.md`, but **the implementation writes `boardpacket-v2.*`**. Look for the latter.

---

### Group 3 — Post-run (3 agents)

**Like this:** deep road-testing after the car is built, plus a monthly "what did we get wrong?"
meeting — and one person who is allowed to actually fix the machines, but **only** when a human says so.

#### `qa-e2e-tcoe-tester` · wraps stage `06-e2e` · flag `QA_TCOE_ENABLED`

> **Like this:** the proper test garage. It doesn't just say "drove fine" — it takes photographs.

1. **Check the flag.** Without it the agent reports **`failed`** rather than silently skipping, **so a missing test pack is never mistaken for a passing one.**
2. Dispatch on mode: `template-only` · `ui-only` · `data-only` · `perf-only` · `regression` · `full` · `cohort-post-run` · `preflight` · `dry-run`.
3. In **template mode**, parse the stage `06` artifact into a structured **test pack**, a **five-pillar gap analysis**, a **traceability matrix**, and a **handoff document**.
4. Where live modes are enabled, **capture real evidence** — UI before/action/after triplets, generated data, performance results.
5. Write the artifacts into the story's `qa/` directory and the run's evidence directory.
6. Report status: `complete` · `degraded` · `failed` · `pending` · `blocked` — **`blocked` carries remediation steps.**

**Sub-flags** (all AND-gated with the master, all default off): `QA_TCOE_TEMPLATE_ENABLED`, `QA_TCOE_UI_ENABLED`, `QA_TCOE_DATA_ENABLED`, `QA_TCOE_PERF_ENABLED`, `QA_TCOE_REGRESSION_ENABLED`, `QA_TCOE_VERBOSE`.

```bash
QA_TCOE_ENABLED=1 npm run qa:tcoe -- --mode template-only --feature <FEATURE>
```

**Blocks:** a missing stage `06` artifact leaves it `pending`. **Pointing it at any org alias other than the designated deploy target is a hard error, not a warning** — that guard is intentional. The UI step refuses to proceed without before/action/after evidence.
**Can write:** yes — to the deploy-target org, when the write sub-flags are on.

#### `self-improvement` (id `self-improvement-agent`) · flag `SELF_IMPROVE_ENABLED` · **proposes only, never applies**

> **Like this:** the person who writes down every mistake the factory made this month and works out
> which ones are actually the *same* mistake wearing different clothes.

1. **Ingest** — issues from the repository (`gh`), prior run retrospectives (`auto-retro-*.md`), the memory file, and board packets.
2. **Classify** each item into one of seven categories.
3. **Root-cause** it, rather than recording the symptom as the problem.
4. **Detect patterns** across items — **the same root cause appearing three times is a different problem from three unrelated bugs.**
5. **Plan** improvements and write them to the ledger as **`PROPOSED`**.
6. **Draft** issue responses, **held back** until the corresponding fix is applied and verified.

```bash
SELF_IMPROVE_ENABLED=1 npm run self-improve -- --refresh-issues
```

**Writes:** `improvement-ledger/ledger.json` · `ledger.md` · `reports/` · `issue-responses/<n>-draft.md` · optionally appends `MEMORY.md`
**Blocks:** **processing zero issues is an invalid run, not an empty one** — usually an unauthenticated repository client. Refresh the issues or supply them from a file. It **never** auto-applies a structural source fix.

#### `sia-fixer` · flag `SIA_FIXER_ENABLED` · **requires explicit human confirmation**

> **Like this:** the only person allowed to pick up a spanner and change the machines. And the door is
> locked unless you personally hand over the key.

1. **SCAN** the ledger for `PROPOSED` entries and write a **fix plan** describing exactly what would change.
2. **HITL GATE — stop.** Without an explicit confirmation flag it **prints instructions and exits**. There is no way to run it accidentally.
3. **FIX** — apply targeted edits to the named files and move those ledger entries to **`APPLIED`**.
4. **PIPELINE RERUN** — re-run the extraction phase to confirm nothing regressed.
5. **SIA RERUN** — re-run the improvement agent, **which is what promotes an entry to `VERIFIED`.** *The fixer never marks its own work verified.*
6. **POST** the drafted responses to issues, **but only for entries that reached a verified state.**

```bash
npm run sia-fix:dry-run
SIA_FIXER_ENABLED=1 npm run sia-fix -- --confirm-id <ENTRY-ID>
```

**Blocks:** this is the **only** agent that writes to source *and* to external issues. Some root causes — workflow design and tooling gaps — are **deliberately skipped as unfixable by automation** and need a human.

**The ledger lifecycle, once:**

```
PROPOSED ──(fixer, after human confirmation)──▶ APPLIED
         ──(improvement agent, on re-run)─────▶ VERIFIED
         ──(pattern returns)─────────────────▶ REGRESSED

Issue responses, in parallel:  DRAFT ▶ READY ▶ POSTED ▶ CLOSED
```

**The separation matters: the agent that applies a fix is never the agent that certifies it.**

---

### Group 4 — Domain harness (1 agent, entirely optional)

#### `afls-agent` · flag `AFLS_ENABLED` · runs *beside* the pipeline, never inside it

> **Like this:** a specialist for a completely different kind of vehicle. He has his own workshop and
> his own door. Leave the light off and the factory behaves exactly as if he weren't there.

It exists as a **worked example of how an industry vertical bolts onto the framework without modifying
it** — its own command, its own flag, and no place in `STAGE_ORDER`.

1. **Stamp the start time and capture the current flag state**, so the run records the conditions it executed under.
2. Build an empty result envelope — a run id, the mode, and empty slots for artifacts, evidence links and findings.
3. **Enforce the gate.** With the flag unset and no `--force`, it returns **`failed`** immediately and does nothing further.
4. Dispatch on the requested **mode**.
5. A `preflight` or `dry-run` validates the wiring and returns `complete` **with no side effects**.
6. A capability mode — `visit-planning`, `benefits-reverification`, or `site-selection` — **loads its module on demand** (each behind its own sub-flag).
7. Because the platform is **licensed but not activated**, that capability returns **`degraded` with one grounded recommendation, rather than inventing a result it cannot produce.**
8. Every finding is labelled **fact / inference / recommendation / open question**, and carries its **source and trust level**.

```bash
npm run afls -- --mode preflight --force
```

**Blocks:** its compliance rules are **hard stops, not warnings** — off-label claims, unbalanced
efficacy claims, patient data beyond the minimum necessary, and any attempt to suppress an
adverse-event escalation. **Thin grounding makes it refuse to conclude** and emit a context-gap report
instead of guessing. It refuses any write outside the single nominated deploy target, **and it cannot
deploy or activate anything at all.**

---

## 7. The governance layer — critics, policies, councils, CAAG

**Like this:** this is the inspectors and the rule book. None of these are counted in the 23 agents,
but **this is where "it can't quietly get away with it" actually lives.**

### 7.1 The critics

Eight scoring critics live in `control-plane/critic/stages/`. Three stages get a structural contract
check instead.

**Verdict enum** (`critic/verdict-schema.ts`):

```ts
verdict: z.enum(['ACCEPT', 'ACCEPT_WITH_CAVEATS', 'REFINE_AGAIN', 'ESCALATE_TO_HUMAN'])
```

Aggregation priority: `ESCALATE_TO_HUMAN` > `REFINE_AGAIN` > `ACCEPT_WITH_CAVEATS` > `ACCEPT`.

| Critic id | Scores | Tier | Bands → verdict |
|---|---|---|---|
| `01-plan-critique` | `01-plan` | standard | `≥1.0` ACCEPT · `≥0.8` CAVEATS · else REFINE · ESCALATE if coverage **and** testability both fail |
| `02-arch-critique` | `02-architecture` | **full** | CRITICAL→REFINE · `≥1.0` ACCEPT · `≥0.8` CAVEATS · `≥0.5` REFINE · else ESCALATE |
| `03-tdd-critique` | `03-tdd` | standard | as arch (`≥0.8` caveats) |
| `04-review-critique` | `04-code-review` | standard | CRITICAL→REFINE · `≥1.0` ACCEPT · `≥0.75` CAVEATS · `≥0.5` REFINE · else ESCALATE |
| `05-build-fix-critique` | `05-build-fix` | standard | as `04` |
| `06-e2e-critique` | `06-e2e` | standard | as `04` |
| `07-security-critique` | `07-security` | **full** | as `04` |
| `10-caag-critique` | reads CAAG disk output, maps to `02-architecture` | standard (optional) | CAAG-driven; gated by `isCaagEnabled()` |
| *contract check* | `00-intake`, `08-refactor`, `09-docs` | **lightweight** | `<100` chars → HIGH · `status==='failed'` → CRITICAL→REFINE. Scores: critical `0.3`, findings `0.7`, clean `1.0` |

**The concrete critical-finding numbers** (this is what actually fails you):

| Critic | Condition | Number |
|---|---|---|
| `01-plan` | untraced requirements | `> 5` uncovered → CRITICAL (keyword match `< 0.4`) |
| `02-arch` | SOQL-in-loop language | CRITICAL |
| `02-arch` | artifact too short | `< 300` chars → CRITICAL |
| `03-tdd` | uncovered acceptance criteria | `> 4` → CRITICAL (match `< 0.3`) |
| `05-build-fix` | unresolved HIGH/CRITICAL review findings | `> 4` → CRITICAL; also failing tests or explicit regression |
| `06-e2e` | acceptance criteria with no e2e path | `> 3` → CRITICAL |
| `07-security` | no CRUD matrix when objects present | CRITICAL |
| `07-security` | unjustified `"full"` OAuth scope | CRITICAL |
| orchestrator | Health Cloud story with no HIPAA section in security | CRITICAL (`domainGovernanceCheck`) |

**The iteration cap.** `defaultPipelineConfig.maxIterationsPerStep = 1` in
`execution/contracts.ts`. (`critic/README.md` documents `2`; the `dab-review` CLI path uses
`maxIterations ?? 3`.) When the cap is hit, the loop **stops and returns the last verdict unchanged** —
which may still be `REFINE_AGAIN`. The loop also stops early if the score fails to improve.

> ⚠️ **The README claims the verdict is *promoted* to `ACCEPT_WITH_CAVEATS` when the cap is hit. That
> is not implemented** in `generator-pipeline.ts`. Don't rely on it.

### 7.2 The OPA policies

Seven `.rego` files in `control-plane/policies/`, with shared numbers in `policies/data/thresholds.json`.

| File | Decides | Outcomes |
|---|---|---|
| `score-thresholds.rego` | which band the aggregate score falls in | `pass` / `review` / `escalate` (default escalate) |
| `approval-routing.rego` | **who** reviews it | `auto-approved` / `L2-orchestrator` / `L3-human` |
| `evidence-completeness.rego` | is the bundle complete enough (`min_requirements` 1) | `allow` bool + pass/review/escalate |
| `risk-escalation.rego` | unmitigated risk (`max_unmitigated_critical/high` = **0**) | pass / review / escalate |
| `waiver-validity.rego` | is this waiver still valid | `valid` true/false |
| `caag-readiness.rego` | context sufficiency, source trust, KP freshness (`max_stale_ratio` 0.34) | pass / review / escalate |
| `caag-deviation-promotion.rego` | may a deviation be promoted (`rationale_min_length` 50) | `promote` / `hold` / **`reject` (default)** |

### 7.3 The councils

**Like this:** two standing panels of specialists you can convene over a feature. Not part of the
assembly line.

**DAB — Design Assurance Board** (`councils/dab/`): **8 domain specialists run in parallel** —
`business`, `data`, `integration`, `application`, `security`, `devops`, `testing`,
`governance-change`. A domain router picks the relevant subset from the evidence. Emits consolidated
`Finding`s into a `ReviewRun` in the evidence store, which feeds scoring and the board packet.

**Governance council** (`councils/governance/`): **8 cadence domains** — `pi-planning`, `scope`,
`risk`, `dependency`, `ccb`, `sprint-intel`, `weekly-review`, `compliance`. The cadence router decides
who convenes:

| Cadence | Who convenes |
|---|---|
| `sprint-close` | sprint-intel · risk · scope · compliance |
| `weekly-review` | **all eight** |
| `ccb-review` | ccb · risk · dependency · compliance |

### 7.4 CAAG — Chief Architect Agent Governance

**Like this:** the chief architect's memory. It remembers what the *programme* decided across all
features, and it will not let one story quietly contradict it.

An **additive** program-memory governance layer sitting above feature intelligence, the ten stages,
the councils and OPA. Enabled by `CAAG_ENABLED=1`; otherwise a complete no-op.

- **Pre-run:** injects a **Feature Context Synthesis Pack** into stages — especially `00`, `01`, `02`, `07`.
- **Post-run:** runs reviewers and quality gates, writing to `runs/<feature>/caag/`.
- **Critic hook:** `10-caag-critique` reads `caag-quality-gate-results.json` + `caag-review-comments.json`.
- **18 modes** including HITL, board-packet, KP promotion, source preflight, SOW/CCB/sandbox checks.
- **Its three gates:** Context Sufficiency · Source Trust · **No-Evidence-No-Claim** — each `PASS` / `WARN` / `FAIL`.

**Writes:** `feature-context-synthesis-pack.md` · `caag-review-comments.md`/`.json` ·
`caag-quality-gate-results.json` · HITL ledger · KP candidates · execution traces.

### 7.5 The scoring models (there are two, plus a third for something else)

| Model | Status | Shape |
|---|---|---|
| **ScoreCard v1** | ⚠️ **deprecated** | 4 dims — AMI `0.30` · PHI `0.25` · ECI `0.25` · RRI `0.20`; approve ≥0.8 / defer ≥0.6 / reject |
| **ScoreCardV2** | ✅ **canonical** | 8 core dims + 3 optional (below) |
| FI health score | separate concern | 11 dimensions; GREEN/AMBER/RED at **0.70 / 0.50** |

**ScoreCardV2** (`services/scoring/score-dimensions.ts`):

| Dimension | Weight | Pass |
|---|:--:|:--:|
| `groundingQuality` | 0.15 | 0.8 |
| `evidenceCompleteness` | 0.10 | 0.6 |
| `storyReadiness` | 0.15 | 0.7 |
| `technicalReadiness` | 0.20 | 0.6 |
| `governanceReadiness` | 0.15 | 0.6 |
| `assumptionRisk` | 0.10 | 0.7 |
| `refinementQuality` | 0.10 | 0.8 |
| `divergenceStability` | 0.05 | 0.9 |
| *(opt)* `expertCalibrationDepth` | 0.10 | 0.50 |
| *(opt)* `crossCloudCoverage` | 0.08 | 0.50 |
| *(opt)* `antiPatternCompliance` | 0.10 | 0.60 |

Promotion guidance: aggregate **≥0.8 with all dimensions passing** → promotion candidate. Board packet
v2: GREEN ≥0.8 + all passing, YELLOW ≥0.6.

---

## 8. The plumbing — every tool that is not an agent

**Like this:** the building itself. Wiring, filing cabinets, the locked door on the tool cupboard.

### 8.1 Knowledge-prep (KP) — the org snapshot

Pulls a structured snapshot of what's really in the org and caches it. Canonical path:
`runs/org/sourceprimary/knowledge-prep/`, with `latest.txt` pointing at the current
`<snapshotId>/bundle.json`.

| Rule | Value |
|---|---|
| Cache-hit window | **4 hours** (`FRESHNESS_TTL_HOURS = 4`) |
| Stale → | delta probe if `DELTA_REFRESH_ENABLED=1` |
| Full re-seed | `knowledge-prep/scripts/full-org-seed.ts`, or `--force-full-fetch` |
| Score decay | `FRESHNESS_DECAY_HOURS = 24`, linear; a FAIL validation forces `0.0` |

### 8.2 Feature intelligence (FI) + `pendingVerifications`

`control-plane/feature-intelligence/` scores feature health across 11 dimensions.
`buildPendingVerifications()` in `orchestrator/fi-orchestrator.ts` scans the story text against the KP
`lookupIndex` and emits `PendingVerification[]` — `{ type, objectName, fieldName?, searchPattern?, soql, reason }` — which flow into every task file. **This is the mechanism that hands an agent the exact query it needs to prove a field is real.**

### 8.3 Context packs and adapters

`control-plane/adapters/` register external context at a declared trust class. Flags:
`MULTI_SOURCE_CONTEXT_ENABLED` (the registry), `SOW_CONTEXT_ENABLED` (statement-of-work → `scoping`),
`ARCH_GUIDANCE_ENABLED` (→ `guidance`), `DD_CONTEXT_ENABLED` (data dictionary),
`IDS_REFERENCE_ENABLED`, plus per-org packs. **Packs may also declare which stages they're relevant to,
and that filter is itself opt-in** (`STAGE_AFFINITY_FILTER_ENABLED`).

### 8.4 The evidence store

`control-plane/.evidence/`:

```
.evidence/objects/{EvidenceTypeName}/{id}.json
.evidence/bundles/{featureId}.json
.evidence/audit/YYYY-MM-DD.jsonl        ← append-only
.evidence/rag/                          ← chunks.jsonl, documents.json
```

An `EvidenceBundle` holds **ID references only**: `requirementIds`, `decisionRecordIds`,
`riskSignalIds`, `waiverRecordIds`, `findingIds`, `reviewRunIds`, `policyTraceIds`, plus optional
`scoreCardId`, `boardPacketId`, `generatedArtifactBundleId`, `pipelineStatus`.

Persisted types include: Requirement · DecisionRecord · RiskSignal · WaiverRecord · Finding ·
ReviewRun · BoardPacket · PolicyTrace · ScoreCard · **ScoreCardV2** · EvidenceBundle ·
UserJourneySummary · BusinessGoalSummary · GapQuestionRecord · AssumptionRecord ·
RefinementDeltaRecord · InputConsiderationRecord · PatternReference · PriorFinding · ReviewSession ·
GeneratedArtifact(+Bundle) · ArtifactContext/Trace/ReviewLink · ScoreContributionTrace ·
Skill/Tool/RuleApplicationTrace.

### 8.5 RAG (retrieval)

`control-plane/rag/` + optional `rag-python/`. Chunks documents (size **500**, overlap **80**) into
`.evidence/rag/`. Query: `retrieve(query, { topK=5, filterFeatureId, filterSourceType, filterTrustLevels, crossFeature })`
— OpenAI `text-embedding-3-small`, or term-overlap fallback. `PYTHON_RAG_ENABLED=1` routes to an
`e2ema-rag` MCP server. Indexes board packets, Confluence pages, and generic markdown.

### 8.6 Knowledge graph (Neo4j)

`control-plane/graph/`. **A complete no-op if `NEO4J_URI` is unset.** Nodes: Feature · Requirement ·
DecisionRecord · RiskSignal · Finding · ReviewRun · BoardPacket · WaiverRecord · PolicyTrace ·
ScoreCard · JiraIssue · ConfluencePage · SalesforceObject · Sprint · Story. Queries: feature
summaries, ADR lineage, unmitigated high risks, cross-feature Salesforce dependencies, trace chains.

### 8.7 Temporal (durable workflows)

`control-plane/temporal/` — the assurance chain and the expert-review quartet run as Temporal
workflows when `TEMPORAL_ADDRESS` is set, including the **48h review / 24h escalate** approval
timeouts. **This is a separate path from the v3 three-phase Cursor pipeline**, not a replacement for it.

### 8.8 The org registry and the write guard

**Like this:** the locked tool cupboard. Exactly one org may be written to. Everything else is
look-only, and a hook at the door checks your hands.

`control-plane/org-registry.json` declares every org alias with an `accessMode`. **The sole
`write-allowed` alias is `deploytarget`**; `defaultTargetOrg: "deploytarget"`. Every other alias
(`sourceprimary`, `sourcesecondary`, `refsales`, `refservice`, `refinternational`) is `read-only`.

Enforcement: `.cursor/hooks/before-shell-execution-sf-guard.js`, wired via `.cursor/hooks.json` on
`beforeShellExecution`. It loads the registry **dynamically**, protects every `read-only` alias *and
its instance hostnames*, blocks write CLI patterns (`project deploy`, `data import`, `apex run`, …)
and **exits with code 2**. If the registry can't be read, it falls back to protecting
`['sourceprimary', 'refinternational']`.

> ⚠️ **The trap to know about.** A fully populated org registry **ships already committed**, filled
> with placeholder organisations (`acme--sourceprimary.sandbox.my.salesforce.com`,
> `operator@acme.com.*`). The write guard reads that file at runtime to decide which orgs are
> read-only — **so an installation that forgets to overwrite it is busy enforcing rules about orgs
> that do not exist.** Replace it from `org-registry.template.json` before the first run rather than
> editing around it.

### 8.9 MCP servers

The agents reach the outside world through MCP: **Salesforce DX** (`run_soql_query`,
`retrieve_metadata`, `deploy_metadata`, `run_apex_test`, `get_username`), **Atlassian** via
`atlassian-mcp-guardrails/` (`jira_get_issue`, `jira_search`, `search_confluence_pages`,
`atlassian_health_check`), and **Cortex** (`get_context_pack_for_story`, `list_evidence_records`,
`get_policy_context_pack`, `get_validated_context_pack`, `search_files`,
`find_relevant_files_for_task`, `detect_staleness_or_supersession`, `extract_glossary_from_file`,
`get_project_background_pack`). Configured in `.cursor/mcp.json` (gitignored; `.example` ships).

### 8.10 Telemetry and audit

OpenTelemetry tracer `e2ema-assurance-control-plane` with `ecc.*` attributes
(`telemetry/tracer.ts`, `otel-setup.ts`, `spans.ts`); CAAG wraps every mode in `withSpan`. Audit is
append-only JSONL under `.evidence/audit/`.

### 8.11 The preflight

`run-production.sh` always injects `--strict-preflight`, which **refuses to proceed on warnings**.
(Cosmetic inconsistency: the shell script advertises a "13-point" preflight while `run-preflight.ts`
and `PIPELINE.md` say "12-point".)

---

## 9. Every file the system writes

```
runs/
├── org/sourceprimary/knowledge-prep/
│   ├── latest.txt
│   └── <snapshotId>/bundle.json                    ← the org snapshot
└── <feature>/
    ├── preflight-<runId>.md
    ├── boardpacket-v2.md · boardpacket-v2.json     ← packet-synthesizer
    ├── caag/
    │   ├── feature-context-synthesis-pack.md
    │   ├── caag-review-comments.md · .json
    │   └── caag-quality-gate-results.json
    ├── orchestration/
    │   ├── cursor-completion-manifest.json         ← Phase 1 output
    │   ├── execution-manifest.json                 ← Phase 3 output
    │   └── synthesis/cursor-tasks/fs-0N-*.task.json
    └── story-runs/<story>/
        ├── cursor-tasks/00-intake.task.json … 09-docs.task.json   ← the job cards
        ├── 00-intake.md      + 00-intake.meta.json
        ├── 01-plan.md        + .meta.json
        ├── 02-architecture.md + .meta.json
        ├── 03-tdd.md         + .meta.json
        ├── 04-code-review.md + .meta.json
        ├── 05-build-fix.md
        ├── 06-e2e.md
        ├── 07-security.md
        ├── 08-refactor.md
        ├── 09-docs.md · traceability.json
        ├── story-extraction-packet.json            ← Phase 3 output
        └── qa/                                     ← qa-e2e-tcoe-tester
            (test pack · gap analysis · traceability matrix · handoff)

control-plane/
├── .evidence/{objects,bundles,audit,rag}/          ← the evidence store
└── improvement-ledger/
    ├── ledger.json · ledger.md
    ├── fix-plan.md
    ├── reports/
    └── issue-responses/<n>-draft.md

Expert review (when EXPERT_REVIEW_V2=1):
  02-ba/story-gap-analysis.md
  03-technical/technical-review.md
  04-governance/governance-risk-summary.md
  05-refinement/refinement-delta.md
```

> **Path caveat:** some agents still reference a legacy *feature-root* path while task files use the
> *story-run* directory. **The task file's `expectedOutputPath` is authoritative.**

---

## 10. The feature-flag surface

**Like this:** almost every switch in the building is off when it's handed to you, and that's the
point. **An installation that never sets a flag runs the ten stages and nothing else** — and its
context assembly is byte-identical to baseline.

Authoritative template: `control-plane/.env.example`. Code treats unset or non-`'1'` as **off**.

| Group | Flags |
|---|---|
| **Core routing** | `CP_RUN_MODE` (default `shadow`) · `CP_KILL_SWITCH` · `CP_TEST_FEATURES` · `E2EMA_HOOK_PROFILE` (`standard`) · `E2EMA_DISABLED_HOOKS` |
| **Knowledge / context** | `KNOWLEDGE_PREP_ENABLED` · `STRUCTURED_CONTEXT_ENABLED` · `SEMANTIC_CONTEXT_ENABLED` · `FRESHNESS_GATE_ENABLED` · `ORG_METADATA_RETRIEVAL_ENABLED` · `ORG_LEVEL_KNOWLEDGE_ENABLED` · `HYBRID_CONTEXT_ENABLED` · `EMBEDDING_INDEXING_ENABLED` · `DELTA_REFRESH_ENABLED` · `TRUST_POLICY_ENABLED` · `MULTI_SOURCE_CONTEXT_ENABLED` · `SOW_CONTEXT_ENABLED` · `ARCH_GUIDANCE_ENABLED` · `DD_CONTEXT_ENABLED` · `IDS_REFERENCE_ENABLED` · `STAGE_AFFINITY_FILTER_ENABLED` |
| **Agents** | `EXPERT_REVIEW_V2` · `QA_TCOE_ENABLED` (+5 sub-flags) · `SELF_IMPROVE_ENABLED` · `SIA_FIXER_ENABLED` · `AFLS_ENABLED` (+3 capability flags) |
| **Governance** | `CAAG_ENABLED` + the `CAAG_*` family |
| **Gates** | `RUN_APEX_GATE` · `APEX_GATE_PCT` (default **80**) · `APEX_GATE_FATAL` |
| **Infra (not booleans)** | `TEMPORAL_ADDRESS` · `NEO4J_*` · `OPENAI_API_KEY` · `OTEL_*` · `PYTHON_RAG_ENABLED` |

**Optional passes, after a run:**

| To do this | Run | First set |
|---|---|---|
| Check the domain harness is wired | `npm run afls -- --mode preflight --force` | `AFLS_ENABLED=1` |
| Build a full test pack from stage `06` | `npm run qa:tcoe -- --mode template-only --feature <F>` | `QA_TCOE_ENABLED=1` |
| Harvest lessons into the ledger | `npm run self-improve -- --refresh-issues` | `SELF_IMPROVE_ENABLED=1` |
| Apply an approved improvement | `npm run sia-fix -- --confirm-id <ID>` | `SIA_FIXER_ENABLED=1` |
| Run the expert review quartet | Temporal workflow, or `scripts/phase7-pilot-driver.ts` | `EXPERT_REVIEW_V2=1` |
| Run the assurance chain for one story | `tsx commands/dab-review.ts <STORY-KEY>` | *no master flag* |

> Note: `dab-review`, `story-readiness`, `gov-weekly-pack`, `ccb-packet` and `board-packet-v2` are
> command *files* under `control-plane/commands/` but are **not** named npm scripts.

---

## 11. Where the docs and the code disagree

**Like this:** the manual and the machine don't match in a few places. Better you hear it from us now
than discover it at 2am.

Read this section before you trust any single claim in the published guide or the repo READMEs.

| # | Issue | Why it matters |
|---|---|---|
| 1 | **The pipeline does not call a model API.** Generation happens in the editor with a human present. | Budget for that. **It is not a fire-and-forget batch job.** |
| 2 | **`REWORK_TRIGGERS` is declared but not executed.** The shipping critic loop re-runs the failing stage in place. | The jump back to `03-tdd` is **your** call, not the pipeline's. |
| 3 | **Tool allowlists and rule files disagree.** `00-intake` is instructed to run SOQL; its `tools.yaml` grants **no** Salesforce tools. `05-build-fix` needs `get_username`/`retrieve_metadata`/`run_soql_query`; none are allowlisted. `01-plan` is told `retrieve_metadata` is allowed; it isn't. | **Reconcile the two when verification degrades silently.** |
| 4 | **Two scoring models coexist.** v1 (4-dim) is `@deprecated` in favour of ScoreCardV2 (8-dim). | **Confirm which one your installation routes through before quoting a number to a board.** |
| 5 | **Two trust vocabularies exist.** Context packs use a 5-class ladder; `source-trust-registry.json` adds `high-trust`, `advisory`, `experimental`. | **Do not map one onto the other by name.** |
| 6 | **Artifact paths differ between layers.** Some agents reference a legacy feature-root path. | **The task file's `expectedOutputPath` is authoritative.** |
| 7 | **Critic SKILL vs `agent.ts` gaps.** The Mermaid-parse-failure CRITICAL (`02-arch`) and the missing-readiness-table CRITICAL (`06-e2e`) are in `SKILL.md` only — **not implemented**. `01-plan` SKILL says 3+ untraced → REFINE; the agent uses `>5` for CRITICAL. | Some documented gates **will not actually fire.** |
| 8 | **Iteration cap disagreement.** Code default `1`; `critic/README.md` says `2`; `dab-review` CLI uses `3`. And the README's "promote to `ACCEPT_WITH_CAVEATS` at the cap" is **not coded**. | A stage may end on `REFINE_AGAIN` and simply stop. |
| 9 | **`.env.production.example` does not exist**, though `PIPELINE.md` and `run-production.sh` reference it. Copy `.env.example` instead. | First-run friction. |
| 10 | **`knowledge-agent/index.ts` re-exports a file that isn't there** (`sourceprimary-connector.js`; the real file is `devint2-connector.ts`). | Import-time failure risk. |
| 11 | **The org registry ships populated with placeholders** and the write guard reads it at runtime. | **Overwrite it before the first run** (§8.8). |
| 12 | **`control-plane/README.md` says "9 agents"** and the tree has 13. `hls-delivery-architect` from 2.0 is **gone**. | Stale counts in docs. |
| 13 | **Preflight point-count mismatch** — "13-point" in the shell, "12-point" in the TS and `PIPELINE.md`. | Cosmetic only. |
| 14 | **Placeholder customer identity is `Acme Corporation`** throughout (`acme.atlassian.net`, `DEMOOMCT`/`DEMOASIM`/`DEMOPSTE`/`DEMOCCB`, `jira.prod.acme.com`), plus absolute operator paths in `RUNBOOK.md`. | These must all be replaced — see the integration plan. |

### The repair table (when output misses)

**Editing a bad artifact by hand hides the failure and it recurs on the next story.** Naming the
problem back to the agent repairs it — and tells you whether the contract loaded at all.

| Symptom | What it actually means, and what to do |
|---|---|
| A stage cites a field you don't recognise | The verification ladder degraded. Check whether it's labelled `[Inferred: UNVERIFIED]`. **If it isn't, the agent skipped verification** — confirm the KP bundle is fresh and the org connection is live, then re-run that stage. |
| The same stage refines repeatedly and never settles | **The fault is upstream.** Critic feedback cannot fix a stage whose input was wrong — look at the artifact it *consumed*, not the one that keeps failing. |
| Architecture fails on a diagram error | **Diagram syntax, not design.** Fix the syntax and it passes. |
| End-to-end reports everything passing on a story that was never deployed | **Fabricated results.** The readiness table and blocker registry exist to make this visible — check both are present, and re-run if either is missing. |
| Extraction rejects a file as a placeholder | Phase 2 never completed for that stage. Return to Cursor **for that one task**; Phase 1 does not need re-running. |
| The improvement agent processed zero issues | **Not an empty backlog — an invalid run.** Usually an unauthenticated repository client. |
| An optional agent seems to do nothing | **Its flag is unset. That is the designed default, not a failure.** |

---

## Glossary

| Term | Meaning |
|---|---|
| **AC** | Acceptance criterion. Formalised as `AC-NN` by `01-plan`; every later stage traces against that version. |
| **ADR** | Architecture Decision Record. Written by `02-architecture`. |
| **AFLS** | Agentforce for Life Sciences — the optional domain harness. |
| **AMI / PHI / ECI / RRI** | The four deprecated ScoreCard v1 dimensions (architecture maturity, policy health, evidence completeness, risk readiness). |
| **CAAG** | Chief Architect Agent Governance — the program-memory layer. |
| **CCB** | Change Control Board. A governance council cadence and a board-packet type. |
| **Critic** | A scoring inspector attached to a stage. |
| **DAB** | Design Assurance Board — the 8-specialist council. |
| **`degraded`** | A stage or run that completed but with reduced confidence. Not a failure. |
| **DLQ / dead-letter** | Not a GameChanger term; in IBC it's `PRM_FailedRecordStaging__c`. |
| **Evidence bundle** | The per-feature index of every evidence object. |
| **FI** | Feature Intelligence — feature-level health scoring and `pendingVerifications`. |
| **HITL** | Human In The Loop — an explicit human confirmation gate. |
| **KP** | Knowledge Prep — the cached org metadata snapshot. |
| **OPA / rego** | Open Policy Agent; `.rego` is its policy language. |
| **`pendingVerifications`** | Pre-computed SOQL handed to an agent to prove a field exists. |
| **`REFINE_AGAIN`** | Critic verdict: re-run this stage with my feedback attached. |
| **SIA** | Self-Improvement Agent. |
| **Story run directory** | `runs/<feature>/story-runs/<story>/` — where the ten artifacts live. |
| **Task file** | `cursor-tasks/<stage>.task.json` — the job card for Phase 2. |
| **TCoE** | Testing Centre of Excellence — the deep QA agent. |
| **Temporal** | The durable workflow engine used for the assurance and expert-review chains. |
| **Trust class** | One of `authoritative` / `scoping` / `guidance` / `persona` / `background`. |

---

## Where this came from

Everything above is grounded in files, not inference:

| Claim area | Source |
|---|---|
| Stage order, agent map, rework map, status enums | `control-plane/execution/contracts.ts` |
| Per-stage journeys, gates, mandatory sections | `control-plane/execution/stages/<id>/{SKILL.md,RULES.md,tools.yaml,agent.ts}` |
| Task file shape, Cursor-only generation | `control-plane/execution/context-bridge/llm-provider.ts` |
| `pendingVerifications` generation | `control-plane/orchestrator/fi-orchestrator.ts` |
| Critic ids, tiers, bands, iteration cap | `control-plane/critic/`, `control-plane/execution/generator-pipeline.ts`, `refinement-handler.ts` |
| Trust ladder, budgets, decay | `control-plane/knowledge-prep/context-pack.ts`, `pack-registry.ts`, `pack-compactor.ts`, `freshness-manifest.ts` |
| Foundation agent journeys and flags | `control-plane/agents/*/`, `control-plane/config/flags.ts`, `control-plane/qa/flags.ts` |
| Assurance and expert-review ordering | `control-plane/temporal/workflows/assurance-review-v2.ts`, `control-plane/temporal/expert-review-pipeline.ts` |
| Ledger lifecycles | `control-plane/agents/self-improvement/contracts.ts` |
| OPA policies and thresholds | `control-plane/policies/*.rego`, `policies/data/thresholds.json` |
| Councils | `control-plane/councils/dab/dab-orchestrator.ts`, `councils/governance/{gov-orchestrator,cadence-router}.ts` |
| CAAG | `control-plane/caag/README.md`, `caag-orchestrator.ts`, `caag/flags.ts` |
| Scoring models + deprecation | `control-plane/schema/score-card.ts`, `services/scoring/score-dimensions.ts`, `agents/scoring-agent/scoring-models.ts`, `docs/architecture/DEPRECATED-MAP.md` |
| Evidence store paths and types | `control-plane/store/persistence.ts`, `schema/index.ts`, `schema/evidence-bundle.ts` |
| Execution phases and flags | `control-plane/scripts/run-production.sh`, `commands/feature-orchestrate.ts`, `PIPELINE.md` |
| Org registry and write guard | `control-plane/org-registry.json`, `org-registry.ts`, `.cursor/hooks/before-shell-execution-sf-guard.js` |
| Flag surface | `control-plane/.env.example`, `docs/operations/configuration-guide.md` |

**Next:** [`02_IBC_Integration_Plan.md`](02_IBC_Integration_Plan.md) — how we wire this into the IBC
PRM Modernization project.
