# IBX GameChanger — Adoption Plan

**Status:** ⚠️ **partially superseded** · **Date:** 2026-08-29 · **Author:** Prashanth Kothapalli

> **Superseded 2026-09-07.** GameChanger **3.0** is now available locally, so **D1 ("wait for 3.0
> access") is resolved and the port is no longer paused.** §4 (phases), §6 (effort) and §7 (decisions)
> of this document are replaced by [`02_IBC_Integration_Plan.md`](02_IBC_Integration_Plan.md), which is
> grounded in the 3.0 tree rather than the 2.0 clone. Two material differences: 3.0 ships
> **customer-neutral** (placeholder `Acme` identity, not Insulet), and **`hls-delivery-architect` no
> longer exists** in 3.0. §2 and §3 below describe **2.0** and are retained for history only.
> For the system explanation, see [`01_GameChanger_System_Explained.md`](01_GameChanger_System_Explained.md).

> **Current state (as written, 2026-08-29).** Decisions D1–D5 are settled (§7). The **port is paused** pending
> GameChanger 3.0 access (D1). The **guide site proceeds now** (§5), scoped as a reusable
> adoption guide for any delivery team, with the IBX adaptation kept separate as the worked
> example rather than the subject.

Bringing the GameChanger multi-agentic SDLC into the IBX (PRM Modernization) project, and
publishing an architect-facing guide that explains what every agent does and how to run it.

---

## 0. Executive summary

GameChanger is a **control plane for agentic Salesforce delivery**: a ten-stage generation
pipeline (`00-intake` → `09-docs`), a set of fourteen foundation agents that sit around it
(pre-pipeline architecture, evidence, governance, QA, self-improvement), and a governance
layer (stage critics, councils, OPA policies, CAAG) that decides whether generated work is
allowed to proceed.

IBX already owns three of the pieces GameChanger provides, built independently:

| GameChanger capability | What IBX already has |
|---|---|
| `hls-delivery-architect` (pre-pipeline solution design) | `.cursor/skills/user-story-architect` + `lsc-user-story-architect` |
| `knowledge-agent` (grounding against org + tickets) | `code-review-graph` MCP knowledge graph + `requirements/` |
| Stage critics (quality gates on generated artifacts) | Ten verifier agents in `docs/build-verification/01_Agent_Catalog.md` |

So this is **not** a greenfield port. The work is to vendor the GameChanger control plane,
strip its Insulet-specific grounding, and wire IBX's existing architect skill, knowledge
graph, and verifier catalog into the slots GameChanger already has for them.

---

## 1. Blocking issue — repository access

The repository named in the request, `sbalakrushnan_sfemu/GameChanger3.0-multi-agentic-SDLC`,
**cannot be cloned**. Both an anonymous clone and an authenticated `gh` lookup fail:

```
remote: Repository not found.
GraphQL: Could not resolve to a Repository with the name
         'sbalakrushnan_sfemu/GameChanger3.0-multi-agentic-SDLC'. (repository)
```

The `_sfemu` account suffix indicates a Salesforce **Enterprise Managed User** account. Repos
owned by EMU accounts live inside the Salesforce-EMU enterprise and are invisible to ordinary
`github.com` identities — the authenticated account here is `p-kothapalli`, which is not an
EMU member. Access requires either an EMU identity or an explicit collaborator invite.

**What we do have:** GameChanger **2.0** is already cloned locally at
`/Users/pkothapalli/storm-b2111773b5b61c/gamechanger`, tracking
`github.com/sbalakrushnanSFDC/GameChanger2.0-agentic-SDLC`, currently on branch
`feature/hls-delivery-architect-integration` (HEAD `614d7793`, 2026-08-29). It is complete and
current, and it is the substrate this plan assumes.

**Decision required (D1):** proceed on 2.0 now, or pause until 3.0 access is granted. The
recommendation is to proceed — 2.0 contains the full agent set, and the delta to 3.0 (by name,
"multi-agentic") is most likely additive agents rather than a different architecture. If 3.0
access lands mid-flight, we rebase.

---

## 2. What GameChanger actually contains

Two distinct layers both get called "agents". The guide must keep them separate, because they
are invoked completely differently.

### 2.1 Layer A — the ten stage agents (`control-plane/execution/stages/`)

These run in a fixed order and each writes one markdown artifact into the story run directory.
Defined by `STAGE_ORDER` / `STAGE_AGENT_MAP` in `control-plane/execution/contracts.ts`.

| Stage ID | Agent | Artifact |
|---|---|---|
| `00-intake` | `orchestrator` | `00-intake.md` |
| `01-plan` | `planner` | `01-plan.md` |
| `02-architecture` | `architect` | `02-architecture.md` |
| `03-tdd` | `tdd-guide` | `03-tdd.md` |
| `04-code-review` | `code-reviewer` | `04-code-review.md` |
| `05-build-fix` | `build-error-resolver` | `05-build-fix.md` |
| `06-e2e` | `e2e-runner` | `06-e2e.md` |
| `07-security` | `security-reviewer` | `07-security.md` |
| `08-refactor` | `refactor-cleaner` | `08-refactor.md` |
| `09-docs` | `doc-updater` | `09-docs.md` |

Failures at stages `04`–`07` rework back to `03-tdd` (`REWORK_TRIGGERS`).

### 2.2 Layer B — the fourteen foundation agents (`control-plane/agents/`)

These are not stages. They run before, beside, or after the pipeline.

| Agent | When it runs | Keep for IBX? |
|---|---|---|
| `hls-delivery-architect` | Pre-pipeline; seeds stages 00–02 | **Replace** with IBX story architect |
| `knowledge-agent` | Pre-pipeline grounding (Jira/Confluence/org) | **Re-target** to code-review-graph |
| `ba-context` | Expert review step 1 | Keep |
| `sf-tech-reviewer` | Expert review step 2 | Keep |
| `gov-risk` | Expert review step 3 | Keep |
| `refinement` | Expert review step 4 | Keep |
| `evidence-auditor` | Assurance step 1b | Keep |
| `scoring-agent` | Assurance step 2a (deprecated → ScoreCardV2) | Keep, note deprecation |
| `policy-router-agent` | Assurance step 2b (OPA) | Phase 3 |
| `packet-synthesizer` | Assurance step 4 (board packets) | Phase 3 |
| `qa-e2e-tcoe-tester` | Post stage `06-e2e` | Keep |
| `self-improvement` | Post-run, out of band | Keep |
| `sia-fixer` | Post-SIA, HITL-gated remediation | Keep |
| `afls-agent` | Agentforce for Life Sciences design harness | **Drop** — not IBX scope |

### 2.3 Governance

- **Stage critics** (`control-plane/critic/`) — one per stage for `01`–`07`, plus
  `10-caag-critique`. A critic can return `REFINE_AGAIN` up to `maxIterationsPerStep`.
- **Councils** (`control-plane/councils/`) — DAB and governance specialist panels.
- **OPA policies** (`control-plane/policies/*.rego`) — evidence completeness, risk escalation,
  score thresholds, waiver validity, approval routing.
- **CAAG** (`control-plane/caag/`) — chief-architect governance, injects at `02-architecture`.
- **Trust ladder** (`knowledge-prep/context-pack.ts`) —
  `authoritative > scoping > guidance > persona > background`. Live org metadata is
  authoritative; a pre-pipeline architect pack is only `scoping` and always loses to it.

### 2.4 How a run is actually executed

Three phases, driven by `control-plane/scripts/run-production.sh`:

1. **Context assembly** — `--phase context-assembly`. Feature intelligence + knowledge-prep
   bundle + a 12-point preflight, then writes one `cursor-tasks/<stage>.task.json` per
   stage × story and an `orchestration/cursor-completion-manifest.json`.
2. **Generation** — human step, no CLI. Cursor AI reads each task file, runs any
   `pendingVerifications` SOQL through the Salesforce DX MCP, writes the stage `.md`.
3. **Extraction** — `--phase extract-only`. Validates no artifact is a placeholder, emits
   `story-extraction-packet.json`, updates `execution-manifest.json`.

---

## 3. What has to change for IBX

Everything project-specific in GameChanger is Insulet/NextGen. These are the files that encode it.

| File | Insulet assumption | IBX change |
|---|---|---|
| `control-plane/org-registry.json` | Orgs `devint2`, `orgsyncng`, `r2devint`, `r2sales`, `r2service`, `international-dev-som`; `*@insulet.com.*` usernames; Omnipod instance URLs | Rewrite with IBX org aliases and trust levels |
| `atlassian-mcp-guardrails/.env` | Jira base URL `jira.prod.insulet.com`; projects `NGASIM`, `NGOMCT`, `NGPSTE`, `NGCRMI`, `NGONDL`, `NGMC`, `NGCCB` | Re-point or **replace with a requirements-file intake** (see D3) |
| `control-plane/.env.production` | Feature flags + org aliases; not committed | New IBX profile |
| `.cursor/mcp.json` | Absolute paths, Atlassian + Salesforce DX servers | Add `code-review-graph`, `salesforce-docs` |
| `hls-delivery-architect/contracts.ts` | Brand overlay enum includes `insulet-omnipod` | Add IBX brand |
| `control-plane/source-trust-registry.json` | Non-org source trust classes | Add `requirements/`, `docs/reference/` |

Note: `PIPELINE.md` and `run-production.sh` both reference `.env.production.example`, but that
file does not exist in the tree — only `control-plane/.env.example`. We will create a real
`.env.ibx.example` as part of this work.

---

## 4. Phases

### Phase 1 — Vendor and neutralize (≈2 days)

1. Copy `control-plane/`, `pipeline/`, `scripts/`, `.cursor/hooks/` into `IBXQA/gamechanger/`.
   Vendored, not a submodule — we are going to diverge immediately (see D2 for alternatives).
2. Delete `afls-agent`, the Insulet outcomes-lab path, and Insulet-only cron installers.
3. Replace `org-registry.json` with IBX orgs; strip all `insulet.com` strings.
4. Author `control-plane/.env.ibx.example` with the real flag surface.
5. `npm install && npm run typecheck` must pass before anything else starts.

**Exit:** the control plane type-checks with zero Insulet references.

### Phase 2 — Ground to IBX (≈3 days)

1. **Intake.** IBX plans work in `requirements/*.md`, not Jira. Write a requirements-file
   intake adapter that produces the same shape `knowledge-agent` produces from Jira, so nothing
   downstream changes. (Depends on D3.)
2. **Knowledge.** Re-target grounding from `retrieve_metadata`/`run_soql_query` on DevInt2 to
   the `code-review-graph` MCP plus the IBX org, and register `docs/reference/` as a
   `guidance`-class source.
3. **Architect.** Swap `hls-delivery-architect` for an IBX story architect that wraps the
   existing `.cursor/skills/user-story-architect` contract, emitting the same
   `handoff/to-gamechanger.json` ContextPack at trust class `scoping`.

**Exit:** `--phase context-assembly` produces valid task files for one real IBX story.

### Phase 3 — Wire IBX verifiers as critics (≈3 days)

IBX's ten verifier agents already have the shape of GameChanger critics — a deterministic
check, an LLM reasoning layer, and a `PASS / NEEDS-FIX / BLOCKED` verdict. Map them onto the
critic slots:

| IBX verifier | GameChanger critic slot |
|---|---|
| Parity Auditor | `02-arch-critique` |
| Branch-Coverage | `03-tdd-critique` |
| Contract-Conformance | `04-review-critique` |
| Governor-Safety | `04-review-critique` |
| Async-Reliability | `06-e2e-critique` |
| Service-Boundary | `02-arch-critique` |
| Test-Adequacy | `03-tdd-critique` |
| Clarification-Log Gate | gate on every stage |
| Critic / Cross-Validator | `critic-orchestrator` |
| DoD Verifier (router) | stage routing |

**Exit:** a stage artifact that violates a known IBX trap (for example creating
`HealthcarePractitionerFacilityNetwork`, which CL-3 forbids) is caught by a critic and returns
`REFINE_AGAIN`.

### Phase 4 — Pilot (≈2 days)

Run all three phases end-to-end on one real, already-understood IBX story. Recommended:
an Epic E service, because the parity ledger and field maps already exist for it, so the
verifiers have ground truth to check against.

**Exit:** ten stage artifacts, a passing critic loop, and a signed extraction packet.

### Phase 5 — The guide site (≈2 days)

See §5.

---

## 5. The guide site

Modelled on `https://p-kothapalli.github.io/lsc-delivery-architect/` — one self-contained
`index.html`, no build step, no dependencies, tab navigation with arrow keys and `F` for
fullscreen.

**Location:** `pages/gamechanger/index.html`, published to GitHub Pages (D4).

**Information architecture:**

| Tab | Contents |
|---|---|
| **Why It Exists** | The delivery problem GameChanger solves, and why a ten-stage pipeline beats one long prompt |
| **The Two Layers** | Stage agents vs foundation agents — the distinction everything else depends on; the trust ladder |
| **Agent Directory** | The centrepiece. One expandable card per agent |
| **Run It Yourself** | The three phases with copyable commands, a checkpoint after each, and a repair table |
| **Adopt for IBX** | What changed from stock GameChanger, the verifier-to-critic mapping, and the config surface |

**Every agent card carries the same six fields**, so the reader learns one format and reuses it:

1. **One line** — what it is, in business terms.
2. **When it runs** — pre-pipeline, in-stage, post-stage, or out of band.
3. **Journey** — a numbered sequence of the steps the agent actually takes, rendered as a
   left-to-right rail. This is the "journey path" the request asks for.
4. **Reads / Writes** — concrete input and output file paths, not abstractions.
5. **How to invoke** — the exact copyable command.
6. **When it blocks you** — the failure mode and the sentence that repairs it.

Worked example, `hls-delivery-architect`:

> **Journey:** flag check (`HLS_DELIVERY_ARCHITECT_ENABLED`) → mode dispatch → four-phase
> discovery interview → solution plan → grounded prototype → stories → assemble
> `handoff/to-gamechanger.json` → `HdaPackAdapter` registers it as a `scoping` pack with a
> 2000-token budget and 7-day decay → stages 00/01/02 read it.

---

## 6. Effort

| Phase | Days |
|---|---|
| 1 — Vendor and neutralize | 2.0 |
| 2 — Ground to IBX | 3.0 |
| 3 — Verifiers as critics | 3.0 |
| 4 — Pilot | 2.0 |
| 5 — Guide site | 2.0 |
| **Total** | **12.0** |

Phase 5 is independent of 1–4 and can run in parallel, since it documents GameChanger's
architecture rather than the IBX adaptation. Doing so shortens the calendar to about eight days.

---

## 7. Decisions required

All five are settled.

| ID | Decision | Outcome |
|---|---|---|
| **D1** | Base version | **Wait for GameChanger 3.0 access.** Phases 1–4 are on hold. Phase 5 (the guide) proceeds now against the 2.0 clone, since it documents architecture that 3.0 is expected to extend rather than replace. |
| **D2** | Where the control plane lives | **Vendored into `IBXQA/gamechanger/`** when the port starts. Not a submodule — the IBX adaptation will diverge immediately. |
| **D3** | Intake source | **`requirements/*.md`.** Phase 2 builds a requirements-file intake adapter emitting the same shape `knowledge-agent` produces from Jira, so nothing downstream changes. |
| **D4** | Guide hosting | **A new public GitHub Pages repo**, matching the `lsc-delivery-architect` pattern. |
| **D5** | Guide scope | **Both**, but reframed: the guide is a **reusable adoption guide for any delivery team**, and the IBX adaptation is the worked example in its own tab — not the subject. |

### What D5 changes

The guide is no longer "how IBX uses GameChanger." It is "how any team adopts GameChanger,
proven on IBX." That inverts the emphasis: the Agent Directory and the run instructions
describe stock GameChanger with no IBX assumptions, and the final tab shows the port pattern
using IBX as evidence that it works. A team on another project should be able to read tabs 1–4,
ignore tab 5 entirely, and still be able to run the pipeline.

---

## 8. Sources

Everything above is grounded in files, not inference:

- `gamechanger/PIPELINE.md` — three-phase execution, legacy steps 1–11
- `gamechanger/control-plane/execution/contracts.ts` — `STAGE_ORDER`, `STAGE_AGENT_MAP`, `REWORK_TRIGGERS`
- `gamechanger/control-plane/critic/critic-orchestrator.ts` — critic IDs and tiers
- `gamechanger/control-plane/orchestrator/master-orchestrator.ts` — `CP_RUN_MODE` routing
- `gamechanger/control-plane/knowledge-prep/context-pack.ts` — `TRUST_CLASS_PRECEDENCE`
- `gamechanger/control-plane/org-registry.json` — Insulet org and trust configuration
- `gamechanger/control-plane/agents/*/` — the fourteen agent implementations
- `IBXQA/docs/build-verification/01_Agent_Catalog.md` — the ten IBX verifier agents
- `IBXQA/CLAUDE.md` — IBX architecture, epics, and Clarification Log
