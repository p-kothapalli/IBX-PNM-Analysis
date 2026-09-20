# Integrating GameChanger 3.0 into the IBC PRM Modernization Project

**Status:** audited · **Date:** 2026-09-07 · **Revised:** 2026-09-09 · **Author:** Prashanth Kothapalli
**Reads with:** [`01_GameChanger_System_Explained.md`](01_GameChanger_System_Explained.md) (what the system is)
**Audited by:** [`04_Integration_Plan_Audit.md`](04_Integration_Plan_Audit.md) — **conditional go.** The corrections from that audit are folded in below and marked **[audit 2026-09-09]**.
**Supersedes:** §1, §4, §6 and §7 of [`IBX_GameChanger_Adoption_Plan.md`](IBX_GameChanger_Adoption_Plan.md) (2026-08-29), whose blocking issue is now resolved.

---

## 0. Executive summary

**Three things changed since the 2026-08-29 adoption plan, and together they turn a paused port into a
ready one.**

1. **GameChanger 3.0 is now on disk** at `/Users/pkothapalli/storm-b2111773b5b61c/gamechanger3.0`. Decision **D1** ("wait for 3.0 access") is answered. Phases 1–4 of the old plan are unblocked.
2. **3.0 arrives already customer-neutral.** Where 2.0 was full of `insulet.com` strings, 3.0 ships with placeholder `Acme Corporation` identity and **role-based org aliases** (`sourceprimary` = read-only, `deploytarget` = the single writable org). There is no customer identity to strip out — only placeholders to fill in. That removes roughly half of the old Phase 1.
3. **IBC's ten verifier agents now exist as real skills**, not a spec. `.cursor/skills/verifying-*/SKILL.md` — all ten of them, each emitting a deterministic verdict. The old plan called the critic mapping "the highest-value step, and the one teams skip." **We are not going to have to build it from nothing.** *[audit 2026-09-09] Five of the ten are three-valued (`PASS`/`NEEDS-FIX`/`BLOCKED`); five are two-valued (`PASS`/`NEEDS-FIX`). Closing that gap is new **Phase 5.0**.*

### The one-sentence version

GameChanger gives IBC a **ten-stage generation assembly line with a human in the middle**; IBC gives
GameChanger **ten domain-specific inspectors and two ground-truth ledgers** that GameChanger's generic
critics cannot match. The integration is mostly *plumbing two halves of the same idea together*, plus
one genuinely new piece of engineering: an intake adapter, because **IBC plans its work in
`requirements/*.md`, not in Jira.**

### Why the timing is unusually good

**The PRM Modernization build has barely started.** Epics A→G are fully designed and about
**60 engineer-days** of Apex, LWC, objects and metadata are still to author. **We can point the
pipeline at the build that is about to happen**, on stories where the Parity Ledger already holds the
right answer — rather than retrofitting it onto finished code.

> **[audit 2026-09-09] Corrected premise.** An earlier draft claimed `force-app/main/default/` was an
> *empty scaffold*. It is not: a full brownfield retrieve has since landed — **28,271 files, 714 Apex
> classes (644 `PRM_*`), 914 object directories, 198 LWCs, 32 triggers, 461 custom metadata records,
> 41 permission sets.** The conclusion above survives, but three consequences follow:
>
> 1. ~~Indexing the estate for `code-review-graph` is now real work (**Phase 3.0**).~~ **Void** — it cannot
>    parse Apex or XML at all; see Phase 3.0.
> 2. `retrieve_metadata` grounding partly duplicates what is already on disk.
> 3. **Critics will meet 644 pre-existing `PRM_*` classes that were never held to these standards.**
>    Expect a false-positive surge in Phase 6 and budget for it.

> ### ⛔ Second correction — 2026-09-09, measured against `HEAD` and the live org
>
> **"The build has barely started" is false for authorship and true for deployment.** Both earlier
> measurements read the **working tree**, where `force-app/` sits outside the git **sparse-checkout cone** and
> 127 committed files carry `skip-worktree` and never materialize. The frontier table below is therefore wrong.
>
> **The frontier has two axes:**
>
> | Epic | In git `HEAD` | Deployed to `ibx-qa` |
> |---|---|---|
> | **A** — 5 async objects, `PRM_AsyncJobConfig__mdt`, permission set, 4 config rows | ✅ committed | **✗** |
> | **B** — foundation | ✅ committed | ✅ |
> | **C** — `PRM_AsyncOrchestrator`, cleanup batch, progress controller, 2 LWCs + Jest | ✅ committed | **✗** |
> | **E** — `PRM_PractitionerBatch` + E1/E2/E5/E6/E7/E10/E11/E16, each with tests | ✅ committed | **✗** |
> | **E19** — `PRM_CMAService` | ✅ committed | ✅ |
> | **F** — `PRM_JsonJobUploadService` / `Controller` | ✅ committed | **✗** |
>
> **The pipeline's opportunity changes shape, and mostly survives.** We are no longer pointing it at a build
> "about to happen" — Epics A–F are authored, so for those the pipeline's role is **review and deployment
> verification**, not generation. What remains genuinely unbuilt (four of five batch classes, E3/E8/E9/E12–E18
> services, Epics D and G) is still ahead of us and is where generation applies.
>
> **A discarded `HVP_` spike** in the org (96 classes, 2026-09-07) is not a target, but it does settle
> **CL-15** and **CL-13** empirically. Full evidence: `docs/gamechanger/05_Org_Reconciliation.md`.

**The real Epic frontier — SUPERSEDED, see the correction above:**

| Epic | State on disk |
|---|---|
| **A** — async objects, `PRM_AsyncJobConfig__mdt`, `PRM_AsyncJob_Access` | **not built** |
| **B** — foundation | **built** — `PRM_ServiceBase`, `PRM_FormSubUtility` (+ tests) |
| **C** — async framework (`PRM_AsyncOrchestrator`, cleanup batch) | **not built** |
| **E** — services | only `PRM_CMAService` (+ test); no `PRM_CaseService`, no `PRM_CaseDataManagerService`, none of the five batch classes |
| Reuse targets (confirming CL-5 / CL-8 / CL-9) | `PRM_ExceptionLogger`, `PRM_AddressSelector`, `PRM_PractitionerCreationValidator` all **present** |

Note that **Epic B was built ahead of A and C**, out of the documented dependency order.

### Effort and shape

| Phase | Theme | Days |
|---|---|---|
| 0 | Provenance and decision gate | 0.5 |
| 1 | Vendor and configure | 1.75 |
| 2 | **Requirements-file intake adapter** | 3.5 |
| **3.0** | **Build and prove the knowledge graph** *[audit]* | **2.0** |
| 3 | Knowledge grounding (guidance sources, allowlist fixes) | 2.0 |
| 4 | Scoping pack from the story architect | 1.0 |
| **4.5** | **Author the E19 pilot story through the architect** *[audit]* ✅ done | **0.5** |
| **5.0** | **Give the five two-valued verifiers a `BLOCKED` state** *[audit]* | **0.5** |
| 5 | **IBC verifiers → GameChanger critics** | 3.5 |
| 6 | Eval corpus and critic calibration (incl. brownfield noise) | 3.0 |
| 7 | Pilot on a story we already understand | 2.0 |
| 8 | Turn optional agents on, one at a time | 1.0 |
| | **Total** | **21.25** |

Phase 3.0 is wall-clock work that blocks nothing else early — **start it in parallel with Phase 1.**
Phases 3 and 4 can run in parallel with 2. Phase 4.5 depends on Phase 4. Phase 5.0 gates Phase 5.2.
Phase 6 gates any move from advisory to blocking. Epic A is **excluded** from this total.

> *[audit 2026-09-09] The original estimate was 16.5 days. The additions are the graph build (B1), the
> registry/alias correction (B2/B3), the missing `BLOCKED` states (M2), Atlassian neutralisation across
> four stages rather than one (M3), authoring the pilot's intake story (B4), and brownfield
> calibration noise (M1).*

---

## 1. What IBC already has — the asset inventory

This is the part that makes the port cheap. **Read the right-hand column as "already done."**

| GameChanger slot | What IBC already owns | Port action | Fit |
|---|---|---|---|
| Stage critics (8 slots) | **Ten verifier skills** in `.cursor/skills/verifying-*/` — five three-valued (`PASS`/`NEEDS-FIX`/`BLOCKED`), **five two-valued** (`PASS`/`NEEDS-FIX`) | Map onto critic slots; add `BLOCKED` to the five (Phase 5.0) | **near one-to-one** |
| `critic-orchestrator` aggregation | **DoD Verifier** (`verifying-practitioner-build`) — classifies the artifact, routes the subset, aggregates deterministically | Map onto orchestrator | **near one-to-one** |
| Critic scoring bands | **Critic / Cross-Validator** risk score 0–100 with fixed weights, tiers `auto` / `architect` / `owner-block` | Replaces GameChanger's keyword-match heuristics | **IBC's is better** |
| Evidence bundle | **Verification State** — shared, append-only, with `evidence[]`, `contradictions[]`, `reasoning_chain[]` | Map onto `EvidenceBundle` | strong |
| Knowledge grounding | `Salesforce DX` MCP + `salesforce-docs` (both live) · **`code-review-graph` ⛔ cannot parse Apex/XML — replaced by `scripts/dependency-graph/sf_deps.py` over the org's dependency index** | Re-target `knowledge-agent` at `sf_deps.py` (Phase 3.0 ✅ done) | strong |
| `scoping` context pack | **`user-story-architect` skill** (+ its own MCP with session/lint/version tools) | Emit its scope section as the pack | strong |
| `guidance` sources | **`docs/implementation-plan/`** (TDD, Epic guides), **`CLAUDE.md`** | Register at trust class `guidance` | direct |
| ~~`docs/reference/` (legacy parity spec)~~ | **⚠ the directory does not exist** — none of its three named files is anywhere under `docs/` | **Recover it, or drop it (Phase 3.4)** | *[audit] dead source* |
| Ground truth for parity | **`docs/build-verification/02_Parity_Ledger.md`** and **`02b_Validation_Rule_Ledger.md`** | Wire as critic inputs | **no GameChanger equivalent** |
| Intake | **412 `requirements/**/*.md`** (191 top-level) — not tickets | **Build an adapter** (Phase 2) | gap |
| Org registry + write guard | Nothing. `.cursor/hooks/` does not exist here; `sf` target org is `ibx-qa`, to be aliased `deploytarget` (D12) | **Build it** (Phase 1) | gap |
| Critic calibration | `06_Agent_Eval_Harness.md` **spec exists, corpus is empty** (`docs/build-verification/eval/` does not exist) | **Build the corpus** (Phase 6) | gap |

### The verdict vocabularies line up almost perfectly

This is the single most important technical finding in this plan.

> **[audit 2026-09-09] With one correction.** The mapping below is exact — but only **five of the ten**
> verifiers actually define `BLOCKED` today:
>
> | Three-valued (define `BLOCKED`) | Two-valued (`PASS`/`NEEDS-FIX` only) |
> |---|---|
> | `verifying-parity` | `verifying-async-reliability` |
> | `verifying-contract-conformance` | `verifying-branch-coverage` |
> | `verifying-clarification-log` | `verifying-governor-safety` |
> | `verifying-cross-validation` | `verifying-service-boundary` |
> | `verifying-practitioner-build` | `verifying-test-adequacy` |
>
> **Consequence:** the §5.2 bridge rule *any `BLOCKED` → `ESCALATE_TO_HUMAN`* **can never fire for the
> right-hand five.** They loop to the iteration cap instead of escalating — which is exactly what D11
> is trying to prevent. **Phase 5.0** closes this before the bridge is written.

| IBC verifier verdict | GameChanger critic verdict | Notes |
|---|---|---|
| `PASS` | `ACCEPT` | direct |
| `NEEDS-FIX` | `REFINE_AGAIN` | direct — a concrete, citable defect |
| `BLOCKED` | `ESCALATE_TO_HUMAN` | direct — **an upstream input is open, so I cannot certify either way** |
| *(no equivalent)* | `ACCEPT_WITH_CAVEATS` | **fill from the risk tier**: `PASS` + risk 21–60 → `ACCEPT_WITH_CAVEATS` |

And IBC's risk score maps straight onto the band structure GameChanger's critics only approximate:

| IBC risk score | IBC review tier | GameChanger verdict |
|---|---|---|
| 0–20 | `auto` | `ACCEPT` |
| 21–60 | `architect` | `ACCEPT_WITH_CAVEATS` |
| 61–100 | `owner-block` | `REFINE_AGAIN` → `ESCALATE_TO_HUMAN` if any `BLOCKED` |

> **Why this matters.** GameChanger's critic scores come from keyword-match heuristics
> (`uncoveredCount > 5`, `content.length < 300`). IBC's come from **deterministic weights over cited
> evidence** (`BLOCKED` = 40, unresolved contradiction = 25, `NEEDS-FIX` = 15, uncited claim = 10). We
> are not degrading GameChanger's critics by substituting ours — **we are upgrading them.**

### The transferable lesson, restated for IBC

> IBC's verifiers were designed with **no knowledge of GameChanger** and still landed on the same
> shape: a deterministic scan, a reasoning layer over it, and a **three-valued verdict where the third
> value means "an upstream input is still open, so I cannot certify this either way."** That third
> state is what makes a critic useful rather than merely strict. **If your team already argues about
> the same defect every sprint, you already have a critic** — it's written down somewhere as a
> checklist item. Adoption is mostly recognising which of your existing standards are critics that
> haven't been given a slot to run in.

---

## 2. The five real gaps

Everything else is configuration. These five are engineering.

### Gap 1 — Intake: IBC has no Jira for the PRM build

`00-intake` is built around `jira_get_issue`, `jira_search`, `atlassian_health_check`, and a **story
status gate** on `Blocked` / `Cancelled` / `Won't Do` / `Technical Refinement`. IBC's PRM
Modernization work lives in **412 markdown files** under `requirements/`, with a
**`user-story-architect`** contract governing their structure.

**Consequence:** without an adapter, `00-intake` fails its pre-flight health check on every run.

> **[audit 2026-09-09] The coupling is wider than `00-intake`.** Measured from the stage allowlists,
> Atlassian tools appear in **four** stages, not one:
>
> | Stage | Atlassian/Jira tools in `tools.yaml` |
> |---|---|
> | `00-intake` | `atlassian_health_check`, `jira_get_issue`, `jira_search` |
> | `01-plan` | `atlassian_health_check`, `jira_get_issue`, `jira_search` |
> | `02-architecture` | `atlassian_health_check`, `jira_get_issue` |
> | `04-code-review` | `atlassian_health_check`, `jira_get_issue` |
>
> Tasks 2.5 and 2.6 must cover all four. Phase 2 is re-estimated to **3.5 days**.

### Gap 2 — No org registry, no write guard

GameChanger's safety model rests on exactly one writable org and a shell hook that enforces it.
IBXQA has **no `.cursor/hooks/` directory and no `hooks.json`**. `sf` config points at `ibx-qa`.

**Consequence:** until this is built, nothing stops a generated `sf project deploy` from hitting the
wrong org. **This is the one gap I would not defer.**

### Gap 3 — Knowledge grounding points at the wrong things, **and the graph is empty**

`knowledge-agent` and the verification ladder both assume an org alias `sourceprimary` and a
Confluence wiki. IBC's equivalents are the `code-review-graph` MCP, `salesforce-docs`, and
`docs/reference/`.

> **[audit 2026-09-09] `code-review-graph` indexes nothing.** `list_graph_stats` returns **2 files,
> 2 nodes, 0 edges, 0 embeddings, languages `javascript`** — against an estate of **28,271** files. A
> search for `PRM_CaseDataManagerService` returns **0 results.**
>
> This is worse than a missing tool. `SUB_BUDGET.authoritative = Infinity`
> (`knowledge-prep/pack-compactor.ts:38`), so an `authoritative` pack bypasses the 4000-token budget
> and **wins every conflict by construction.** An authoritative source that silently returns nothing
> becomes unfalsifiable — precisely the failure the trust ladder exists to prevent.
>
> **Therefore:** new **Phase 3.0** builds and proves the graph, and it is registered at **`guidance`**
> — *not* `authoritative` — until its recall is measured in Phase 6.
>
> This also explains why prior sessions fell back to Grep despite the graph-first workspace rule: the
> rule has been unenforceable because the graph was never built.

### Gap 4 — No scoping pack emitter

`user-story-architect` produces excellent markdown but **no machine-readable handoff of the story
itself**. The `scoping` slot needs a file the adapter can read, reduced to headings/bullets/tables and
capped at **800 tokens**.

### Gap 5 — No eval corpus, so critics cannot be calibrated

`06_Agent_Eval_Harness.md` specifies a labelled corpus (P01–P03, D01–D10, T01–T03) and a promotion
path Advisory → Soft-gate → Hard-gate. **The corpus directory is empty.** Until it exists, every
verifier-as-critic is advisory by definition, because we cannot prove it doesn't false-positive.

---

## 3. Target architecture for IBC

```
┌─ AUTHORING (already exists) ─────────────────────────────────────────────────┐
│  user-story-architect skill  →  requirements/<Story>.md                     │
│  (+ its MCP: create_session · lint_story · version_story · dependency graph) │
└──────────────────────┬───────────────────────────────────────────────────────┘
                       │  ① scoping-pack emitter   (Phase 4, ≤800 tokens, 24h decay)
                       ▼
┌─ PHASE 1 · CONTEXT ASSEMBLY (CLI, deterministic) ───────────────────────────┐
│  requirements-file intake adapter  (Phase 2 — replaces jira_get_issue)      │
│  knowledge-prep → deploytarget org snapshot  (4h cache)                     │
│  code-review-graph MCP → OmniStudio/Apex structural grounding  (Phase 3)    │
│  guidance packs: docs/reference · docs/implementation-plan · CLAUDE.md      │
│  feature-intelligence → pendingVerifications SOQL   ◀── maps to CL-11       │
│                                                                             │
│  writes: runs/<epic>/story-runs/<story>/cursor-tasks/00…09.task.json        │
└──────────────────────┬───────────────────────────────────────────────────────┘
                       ▼
┌─ PHASE 2 · GENERATION (you, in Cursor) ─────────────────────────────────────┐
│  10 stage agents, in order, each writing one artifact                       │
│    00-intake → 01-plan → 02-architecture → 03-tdd → 04-code-review          │
│    → 05-build-fix (check-only to deploytarget) → 06-e2e → 07-security       │
│    → 08-refactor → 09-docs                                                  │
│                                                                             │
│  next to each stage:  IBC VERIFIER AS CRITIC        (Phase 5)               │
│    parity · branch · contract · governor · async · boundary · test          │
│    aggregated by DoD Verifier → risk score → ACCEPT / REFINE_AGAIN / ESCALATE│
│                                                                             │
│  across every stage:  CLARIFICATION-LOG GATE        (Phase 5)               │
│    open CL contradiction → BLOCKED → ESCALATE_TO_HUMAN                      │
└──────────────────────┬───────────────────────────────────────────────────────┘
                       ▼
┌─ PHASE 3 · EXTRACTION (CLI) ────────────────────────────────────────────────┐
│  story-extraction-packet.json · execution-manifest.json · traceability.json │
└──────────────────────┬───────────────────────────────────────────────────────┘
                       ▼
        ┌─ OPTIONAL, FLAG-GATED, LATER ────────────────────────┐
        │  qa-e2e-tcoe-tester → maps onto Epic G G2/G3         │
        │  self-improvement + sia-fixer (human-gated)          │
        │  expert-review quartet (EXPERT_REVIEW_V2=1)          │
        │  assurance chain → board packet                      │
        └──────────────────────────────────────────────────────┘

        ┌─ SAFETY (Phase 1, non-negotiable) ──────────────────┐
        │  org-registry.json: deploytarget = write-allowed    │
        │                     everything else = read-only     │
        │  .cursor/hooks/before-shell-execution-sf-guard.js   │
        └─────────────────────────────────────────────────────┘
```

### What we deliberately do **not** take in v1

| Component | Why not |
|---|---|
| `afls-agent` | Life-sciences domain harness. Not IBC scope. **Delete the directory.** |
| Temporal workflows | Needs a Temporal server. The three-phase Cursor pipeline doesn't require it. Defer. |
| Neo4j graph sync | No-op without `NEO4J_URI`, and IBC already has `code-review-graph`. Leave off. |
| Councils (DAB, Governance) | 16 specialist personas is a governance apparatus IBC doesn't have a forum for yet. Phase 8+ at the earliest. |
| CAAG | Program-memory governance. Genuinely interesting for the Clarification Log (§5.4) but too large for v1. Evaluate in Phase 8. |
| `scoring-agent` v1 | `@deprecated`. If we score at all, use ScoreCardV2. |
| `atlassian-mcp-guardrails` | Only if IBC decides to also route GUS/Jira stories (D3b). |

---

## 4. The integration, phase by phase

### Phase 0 — Provenance and decision gate · 0.5 day

**The local 3.0 tree is not a git repository** — `git remote -v` returns "not a git repository." It is
a copied directory. Before we vendor anything into a customer repo, that needs resolving.

| # | Task |
|---|---|
| 0.1 | Confirm with the GameChanger owner (`sbalakrushnan`) that the local 3.0 tree is the intended sharable artifact, and get its licence/provenance in writing. |
| 0.2 | Ask for read access to the upstream repo (EMU enterprise) so we can rebase later, or accept a hard fork with a recorded snapshot date. **Still non-blocking** — an interim escalation to blocking on 2026-09-09 was reverted the same day when report finding F1 was retracted (the "missing modules" were a scrub-induced filename mismatch, repaired locally). Two things do make the ask worth including alongside 0.1: **R9** wants a rebase path, and `adapters/adapter-registry.ts` is genuinely absent. Also worth reporting upstream: the scrub renamed identifiers and import specifiers **but not filenames**, and it corrupted six files by replacing tokens *inside* identifiers. |
| 0.3 | Take the decisions in §7. Nothing after this phase should be blocked on a decision. |

**Exit:** provenance recorded in `docs/gamechanger/`; D1–D10 answered.

> ⚠️ Do not skip 0.1. Vendoring an unlicensed internal tree into a client-adjacent repo is a real risk,
> not a formality.

---

### Phase 1 — Vendor and configure · 1.75 days · ⚠️ **8/10 DONE, BLOCKED — see `06_Phase1_Vendoring_Report.md`**

**Do not edit the framework.** Fill in the configuration surface and nothing else.

> **[executed 2026-09-09]** **Phase 1 is complete — 10/10.** Tasks 1.0–1.8 done; **1.9 and 1.10 were
> re-scoped** (they could not pass as originally written) and both now pass. The vendored tree arrived **corrupted by the upstream scrub in two distinct ways**, both
> repaired here: it replaced a token *inside identifiers*, yielding 63 syntax errors (**F2**, repaired in
> 11 positions), and it rewrote import **specifiers without renaming the files**, breaking the import graph
> tree-wide (**F1**, repaired by `scripts/repair-vendored-import-map.sh`). Typecheck now stands at **543
> errors, 0 parse errors, 11 unresolved imports** — all 11 off the pipeline's executed path, and the
> residual 543 are upstream strict-null/`exactOptionalPropertyTypes` debt.
>
> ⚠️ **An earlier version of this note claimed the artifact was "incomplete — 23 missing modules". That was
> wrong and is retracted** (see the report's F1 banner): the modules existed under their pre-scrub names.
> **D16** is re-opened with option (b) recommended, and **Phase 0.2 reverts to non-blocking**. **D15**
> (grounding source == deploy target) is resolved-with-caveat.
>
> **1.10's gate is now `bash scripts/verify-gc-gate.sh`** (D16 option b): the executed path is computed by
> TypeScript from the CLI entry points — **189 files, 0 parse errors, 0 unresolved imports, 87 strictness
> errors held at baseline** — and it is negative-tested against both scrub bug classes.
>
> Two plan defects were found in execution: **1.2 as written breaks the build**, and the **write guard
> fails open to Acme's aliases** from a root install. Full evidence:
> `docs/gamechanger/06_Phase1_Vendoring_Report.md`.

| # | Task | Detail |
|---|---|---|
| 1.1 | Vendor the tree | Copy `control-plane/`, `pipeline/`, `scripts/`, `shared/`, `config/`, **`agentic-sdlc-framework/`, `optional-skills/`, `jest-mocks/`, `jest.config.js`, root `package.json`**, and the whole `.cursor/` (`hooks/`, **`hooks.json`**, `rules/`, `skills/`, `mcp.json.example`) into `IBXQA/gamechanger/`. **Vendored, not a submodule** — we will diverge immediately (D2). *[audit] The root `package.json` / `jest.config.js` / `jest-mocks/` are needed by the test suite later phases rely on; `hooks.json` already exists upstream — copy it rather than authoring it in 1.4.* |
| 1.2 | Delete out-of-scope | ~~`control-plane/agents/afls-agent/`, `control-plane/afls/`~~, `rag-python/` (unless D10 says otherwise), any scheduled-job installers. **[amended 2026-09-09]** Do **not** remove the two `afls` directories: `control-plane/commands/afls.ts` imports them directly and three npm scripts target them, so removing them breaks the 1.10 typecheck and forces framework edits. Dead code that compiles and is never invoked is cheaper than that. Actually removed: `rag-python/` + 5 cron installers. |
| 1.3 | **Overwrite the org registry** | Copy `org-registry.template.json` → `org-registry.json`. **Never edit the shipped one in place** — it arrives populated with `acme--*.sandbox.my.salesforce.com` placeholders and the write guard reads it at runtime. **[audit] Honour the real schema (§6.3): `orgs` is a keyed map, not an array, the map key must equal the entry's `alias`, and every entry needs all fifteen fields.** |
| 1.4 | **Wire the write guard** | Create `IBXQA/.cursor/hooks/before-shell-execution-sf-guard.js` and `IBXQA/.cursor/hooks.json` with the `beforeShellExecution` binding. Verify it exits `2` on a blocked command. **[audit 2026-09-09] The shipped guard FAILS OPEN from a root install** — it resolves the registry as `../../control-plane/org-registry.json`, which from the repo root does not exist, then falls back to two of *Acme's* org names, protecting nothing real while still logging as active. Our copy fixes the path and the fallback. The guard is also a **denylist**: unlisted orgs *and unlisted aliases of a listed org* are unguarded, so all 13 orgs are registered — including another client's sandboxes. Verified by `scripts/verify-sf-guard.sh`, 19/19. Known trade-off: matching is on the alias token anywhere in the command, so shell commands that merely *mention* a protected alias alongside a write verb are blocked too. |
| 1.5 | Customer profile | `config/customer-profile.json` from `.example`. IBX identity, My Domain, no Jira projects for the PRM build (D3). |
| 1.6 | Env profile | `control-plane/.env.production` — **copy `.env.example`, not `.env.production.example`, which does not exist** despite what `PIPELINE.md` says. |
| 1.7 | Source trust registry | Register the IBC guidance sources (see §6.4). |
| 1.8 | MCP config | **[audit] Already done — verify only.** `.cursor/mcp.json` already registers `code-review-graph`, `salesforce-docs`, `docsearch`, `user-story-architect` and `Salesforce DX`. |
| 1.9 | Scrub the placeholders | Grep and replace the full `Acme` list (§6.5). **[amended 2026-09-09] Not achievable as scoped** — 151 `acme` hits across 81 code/config files, where §6.5 lists 7; nearly all sit in unused CAAG / SOW / Jira paths. Re-scoped to **zero `acme` in live configuration, and no reachable Acme endpoint in any enabled code path**. Live configs are clean. §6.5's list also misses the genuinely dangerous cases (a hardcoded deploy-target username, the QA-tester host, three JMX perf hosts, the self-improvement repo URL) — see report F11, which is effectively a Phase 8 pre-flight checklist. |
| 1.10 | Green build | **[audit] `cd gamechanger/control-plane && npm install && npm run typecheck`.** The `typecheck` script exists **only** in `control-plane/package.json` — the root `package.json` has no such script. |

**Exit:** the control plane type-checks with zero `acme` references; the pre-flight check passes; the
org registry resolves; **and a write aimed at a read-only alias is refused.**

#### The org registry for IBC

| Alias | Access mode | Role |
|---|---|---|
| **`deploytarget`** → the IBX QA org | **`write-allowed`** | The one and only deploy target. `defaultTargetOrg`. |
| IBC production | `read-only` | Grounding truth for the verification ladder |
| Any other sandbox | `read-only` | Reference |

> **[audit 2026-09-09] Alias decision — D12.** An earlier draft named the write alias `ibx-qa`, while
> §6.5 said to keep `deploytarget` "as the role name". **Those contradict**, and the framework does not
> tolerate ambiguity here: `org-registry.ts` states the alias is *"the ONLY identifier used in paths,
> manifests, and API calls"*, and `getOrgConfig()` throws on an unregistered alias. `deploytarget` is
> hardcoded in at least `scripts/run-production.sh:183`, `critic/stages/05-build-fix-critique/agent.ts`,
> `commands/qa-tcoe.ts` and `tests/regression/sf-guard-hook.test.ts`.
>
> **Resolution for v1: keep the framework alias `deploytarget`** and point it at the IBX QA org:
>
> ```bash
> sf alias set deploytarget=<ibx-qa-username>
> ```
>
> Zero framework edits, so R9 (rebaseability) stays intact. **D6's "one name for one org" is
> explicitly deferred**, not silently dropped. Revisit if we ever stop rebasing.

The verifier skills run `sf apex run test -n <Class>Test --target-org <alias> --code-coverage`; point
them at the same alias so there is one write path, not two.

---

### Phase 2 — The requirements-file intake adapter · 3.5 days

**This is the one genuinely new piece of engineering.** Everything else is configuration or mapping.

**The contract:** emit the *same shape* `knowledge-agent` produces from Jira, so **nothing downstream
needs to change.**

| # | Task | Detail |
|---|---|---|
| 2.1 | Parse the architect contract | Read `requirements/<Story>.md` per the `user-story-architect` canonical section order: Header (Persona, Priority, OmniScript, IPs) → Story → Why it matters → Scope → Current State → **Acceptance Criteria** → **Technical Implementation (high-level)** → Definition of Done → Clarification Questions → Impact Analysis → Estimated Effort. |
| 2.2 | Map to `Requirement` | `## Acceptance Criteria` → the AC field (highest field priority in `00-intake`). `## Story` → description. Header `Persona` → the persona context. `Relevant Requirements` → parent/related. |
| 2.3 | Synthesise a story key | Markdown files have no `DEMOASIM-162`. Derive a stable key from the filename, e.g. `PRM-E19-CMASERVICE`. **It must be stable across runs** — the run directory and the manifests key off it. |
| 2.4 | Replace the status gate | There is no Jira status. Substitute a **front-matter or header-derived status** and preserve the gate's semantics: a story with unanswered `## Clarification Questions` marked blocking behaves like `Blocked`. |
| 2.5 | Neutralise the health check | `atlassian_health_check` must not fail the run when Atlassian isn't in play. Return a healthy no-op, or stub the connector. |
| 2.6 | Map the wiki search | `search_confluence_pages` → a `requirements/` + `docs/` search. The **fallback path** in `00-intake` step 3 must still work when a context pack is judged irrelevant. |
| 2.7 | Round-trip test | Pick five real requirements files across categories (`*_UserStory.md`, `*_BugFix*`, `*_Architecture.md`, `*_Analysis.md`, an `Epic_*` guide) and assert a valid `00-intake.task.json` for each. |

**Exit:** `--phase context-assembly` produces valid task files for **one real IBC story** taken
straight out of `requirements/`.

> **Design note.** Resist the temptation to "just use the description field." `00-intake`'s field
> priority (**AC → high-level design → description → parent → comments**) is load-bearing — it's what
> makes `01-plan`'s formalised ACs traceable. The architect contract already has all five; map them
> properly.

---

### Phase 3.0 — Structural grounding · ✅ **DONE 2026-09-09** (re-scoped from "build the knowledge graph")

> **This phase was attempted as written and the premise failed.** `code-review-graph` does not merely hold
> 2 nodes — it **cannot parse Apex or Salesforce metadata at all**.
> `code_review_graph.parser.EXTENSION_TO_LANGUAGE` covers 30 languages; `.cls`, `.trigger` and `.xml` are all
> absent. A `full_rebuild` parsed **2 files**, 0 edges, while 7 `.cls` files sat materialized on disk. For an
> estate of 714 Apex classes, 914 object dirs and 4,091 OmniStudio files, no amount of building fixes this.
>
> **Superseded by the org's own dependency index.** Decision **D14 is void**; the graph is **not** registered
> as a grounding source for Apex or metadata at any trust class. Evidence and measurements:
> `docs/gamechanger/05_Org_Reconciliation.md`.

**What was delivered instead:** `scripts/dependency-graph/sf_deps.py`, over the Tooling API object
`MetadataComponentDependency`. It covers ApexClass, ApexTrigger, ApexPage, LWC, Aura, Flow, FlexiPage, Layout,
CustomObject, CustomField, ValidationRule, QuickAction, **OmniScript** and **OmniIntegrationProcedure**, and it
is **`authoritative`** because it is the org's own index — top rung of the Verification Ladder, not a parsed
approximation of it.

| # | Task | State |
|---|---|---|
| 3.0.1 | Establish an Apex-capable structural source | ✅ `sf_deps.py` on `MetadataComponentDependency` |
| 3.0.2 | Expose `callers_of` / `callees_of` / `tests_for` / `impact` | ✅ `callers` · `callees` · `tests` · `impact -d N` · `survey --prefix` |
| 3.0.3 | **Prove recall** on the fixed probe set | ✅ `PRM_ServiceBase` (2 callers) · `PRM_FormSubUtility` (3) · `PRM_ExceptionLogger` (**164**, corroborating CL-5) · `PRM_CMAService` (2). `PRM_CaseDataManagerService` / `PRM_PractitionerService` correctly **fail to resolve** — they are committed but not deployed. |
| 3.0.4 | Spot-check against hand-verified answers | ✅ `callers_of PRM_CMAService` → `PRM_CMAServiceTest`, `PRM_ParFormCmaBatch`; `callees_of` → `PRM_ServiceBase`, `PRM_FormSubUtility`, `PRM_CaseManagerAssociation`, `PRM_CaseManager`, `PRM_RequestType`. Both match a hand-run SOQL query exactly. |
| 3.0.5 | Record limits so the trust class is honest | ✅ see the two traps below |

**Two traps, both load-bearing:**

1. **Never bulk-export `MetadataComponentDependency` — it misreports completeness.** `MetadataComponentType='ApexClass'` returns 1,213 rows over **72** distinct classes while reporting `done: true`; adding `RefMetadataComponentType='ApexClass'` returns 1,686 rows over **624**; unfiltered returns ~1,900 rows with **zero Apex**. A first implementation bulk-cached 6,365 edges and was discarded after `PRM_CMAService` came back empty from it. The tool now queries **per component Id**, which is accurate.
2. **Edges are deploy-time references, not runtime call paths.** The orchestrator's `Type.forName` dispatch to batch classes from `PRM_AsyncJobConfig__mdt` is **invisible** here — read the Custom Metadata rows for that.

**Also note:** this source only sees **deployed** components. Since Epics A, C, E and F are committed but *not*
deployed (§0), critics reviewing that code need `HEAD`, not the org.

**Exit:** ✅ probe set verified, limits recorded, registered **`authoritative`**, and both workspace rules
(`.cursorrules`, `code-review-graph-first.mdc`) rewritten to route Apex/metadata here and keep
`code-review-graph` for JS/TS only.

---

### Phase 3 — Knowledge grounding · 2.0 days

**Like this:** teach it to look at *our* org and *our* documents, in the right order of authority.

| # | Task | Trust class |
|---|---|---|
| 3.1 | Point knowledge-prep at IBC | `run_soql_query` / `retrieve_metadata` against the **read-only** IBC org. Keep the **4-hour** cache window and set `FRESHNESS_GATE_ENABLED=1`. | **`authoritative`** |
| 3.2 | Register **`scripts/dependency-graph/sf_deps.py`** as the structural grounding tool *[revised 2026-09-09]* | `callers` / `callees` / `tests` / `impact` over the org's own dependency index. **`code-review-graph` is NOT registered for Apex or metadata — it cannot parse `.cls`/`.trigger`/`.xml`** (D14 void). Keep it for LWC `.js` only. Add to the stage `tools.yaml` allowlists for `01`–`04`. | **`authoritative`** (it is the org) |
| 3.3 | **Fix the allowlist gaps while you're in there** | `00-intake`'s `tools.yaml` grants **no Salesforce tools** despite its rules requiring SOQL; `05-build-fix` lacks `get_username`/`retrieve_metadata`/`run_soql_query`; `01-plan` lacks `retrieve_metadata`. Grant them, or the verification ladder degrades silently. | — |
| 3.4 | ⚠ **`docs/reference/` DOES NOT EXIST** *[audit]* — the three named legacy-parity files are absent from the repo. **Recover them, or drop this registration** and state that parity ground truth is the two ledgers (3.6) alone. Do not register an empty source. | — |
| 3.5 | Register `docs/implementation-plan/` | The TDD, the Implementation Plan, Epic guides A/B/C/E. | `guidance` |
| 3.6 | Register `docs/build-verification/` | The Parity Ledger and Validation Rule Ledger — **ground truth for the critics.** | `guidance` |
| 3.7 | Register `CLAUDE.md` §6 | Org coding standards (bulkification, `with sharing`, `PRM_` prefix, trigger bypass, `PRM_ExceptionLogger`, RT-by-describe). | `guidance` |
| 3.8 | Register `requirements/` corpus | 412 files. Searchable, never decisive. | `background` |

**Exit:** a `pendingVerifications` list generated for an IBC story resolves real `PRM_*__c` fields
against the IBC org, and a fabricated field comes back labelled `[Inferred: UNVERIFIED]`.

> **Respect the golden hierarchy.** `CLAUDE.md` §0 already declares one: live org metadata > Epic A >
> Implementation Plan > TDD > Epic guides > `docs/reference/`. **That is the same idea as
> GameChanger's trust ladder, and it must not end up contradicting it.** Map `CLAUDE.md`'s hierarchy
> *inside* the `guidance` class as an ordering, with live org metadata alone at `authoritative`.

---

### Phase 4 — Scoping pack from the story architect · 1.0 day

| # | Task |
|---|---|
| 4.1 | Add a scope-pack emitter to the `user-story-architect` flow: after `finalize_session`, write `handoff/to-gamechanger.json`. |
| 4.2 | Reduce it to **headings, bullets and tables only**, capped at **800 tokens** (`SUB_BUDGET.scoping`). |
| 4.3 | Register it at trust class **`scoping`** with the standard **24-hour linear decay**. |
| 4.4 | Declare stage affinity: relevant to `00-intake`, `01-plan`, `02-architecture` only. |
| 4.5 | Verify it **loses every conflict** with live org metadata. Write a test that proves it. |

**Exit:** a story authored through the architect seeds stages `00`–`02`, **and cannot state a platform
fact.**

> **The rule to internalise:** a scoping pack **bounds what is in scope. It never states a platform
> fact.** If the architect's story says a field exists and the org says otherwise, **the org wins**,
> and the pack's claim is discarded — not averaged.

---

### Phase 4.5 — Author the E19 pilot story · 0.5 day · ✅ **DONE** **[audit 2026-09-09, new]**

**The pilot had no intake artifact.** Phase 7 runs `--story-keys PRM-E19-CMASERVICE` and the Phase 2
adapter reads `requirements/<Story>.md` — but **no pilot story existed** anywhere in the corpus
(191 top-level, 412 recursive markdown files). *(Originally scoped to E16; retargeted to E19 per D9.)* The
Epic E service specifications live in `docs/implementation-plan/Epic_E_Practitioner_Services*.md`, which
this plan registers at `guidance`, **not** as intake — hence the need to author a real story.

| # | Task |
|---|---|
| 4.5.1 | ✅ **Done** — `requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md` authored through the **`user-story-architect`** skill (E19, per the revised D9). |
| 4.5.2 | ✅ **Done** — grounded on Parity Ledger row 20 + §6 rule 9 and the live `PRM_CaseManagerAssociation__c` metadata (19 record types, 18 fields). Deliberately **not** grounded on the existing implementation, so it stays a valid answer key. |
| 4.5.3 | Run `lint_story` and `finalize_session`, which **emits the Phase 4 scope pack** — this is the emitter's first real test. |
| 4.5.4 | Round-trip it through the Phase 2 adapter and assert a valid `00-intake.task.json` with story key `PRM-E19-CMASERVICE`. |

**Exit:** one real requirements file that the adapter ingests cleanly and that carries a scope pack.

> **D13 ✅ resolved (2026-09-09):** scope the pilot to the **service in isolation**. No Epic A deployment
> is required — E19's whole dependency set is already live in `ibx-qa`, including the existing consumer
> `PRM_ParFormCmaBatch`. The original premise that the batch class and Epic A "do not exist" was also
> wrong: both are committed in `HEAD`, merely undeployed.

---

### Phase 5.0 — Give the five two-valued verifiers a `BLOCKED` state · 0.5 day · **[audit 2026-09-09, new]**

**Blocks §5.2.** The bridge rule *any `BLOCKED` → `ESCALATE_TO_HUMAN`* cannot fire for five of the ten
critics, because those five never emit `BLOCKED`. Each has an obvious third state:

| Skill | Proposed `BLOCKED` condition |
|---|---|
| `verifying-governor-safety` | the perf harness has not been run, so budget numbers are unavailable |
| `verifying-test-adequacy` | coverage is unobtainable because the class does not deploy |
| `verifying-branch-coverage` | the IBC/Delegated branch matrix is itself an open CL item (CL-15) |
| `verifying-async-reliability` | the batch↔service mapping is unresolved, so the chain cannot be traced (CL-15) |
| `verifying-service-boundary` | the owning batch is undecided, so "belongs in the batch" is unanswerable (CL-15) |

Note the shape: **four of the five reduce to "an upstream Clarification Log item is open"** — the same
semantic the three-valued verifiers already use. This is a consistency fix, not new invention.

**Exit:** all ten verifiers document a three-valued verdict, and each new `BLOCKED` condition has a
case in the Phase 6 corpus.

---

### Phase 5 — IBC verifiers as GameChanger critics · 3.5 days

**The highest-value phase, and the one teams skip.** Do not skip it.

#### 5.1 The mapping

| # | IBC verifier | Skill | Critic slot(s) | What it adds that GameChanger lacks |
|:--:|---|---|---|---|
| 1 | **Parity Auditor** | `verifying-parity` | `02-arch-critique` (design) + `05-build-fix-critique` (delivery) | Legacy DR→object ground truth. GameChanger has **no parity concept at all.** |
| 2 | **Branch-Coverage** | `verifying-branch-coverage` | `03-tdd-critique` + `02-arch-critique` | IBC vs Delegated branch gates. Domain-specific; unmatched. |
| 3 | **Contract Conformance** | `verifying-contract-conformance` | `04-review-critique` | Payload round-trip + **every eligibility rule needs a server-side check *and* a negative test.** |
| 4 | **Governor & Bulk-Safety** | `verifying-governor-safety` | `04-review-critique` | Overlaps GameChanger's bulkification rules but adds `sf code-analyzer` + **real budget numbers**. |
| 5 | **Async / Reliability** | `verifying-async-reliability` | `06-e2e-critique` | Halt-on-failure chain, idempotency, DLQ, **no whole-submission savepoint**. Unmatched. |
| 6 | **Service-Boundary** | `verifying-service-boundary` | `02-arch-critique` | Enforces `prm-service-class-boundaries.mdc`. Unmatched. |
| 7 | **Test-Adequacy** | `verifying-test-adequacy` | `03-tdd-critique` | ≥85% **plus** bulk/single/empty/negative **plus** outcome assertions, not just coverage. |
| 8 | **Clarification-Log Gate** | `verifying-clarification-log` | **cross-stage** — see §5.4 | **No GameChanger equivalent.** The most interesting piece of the whole port. |
| 9 | **Critic / Cross-Validator** | `verifying-cross-validation` | `critic-orchestrator` aggregation | Cross-agent contradictions + deterministic risk score. **Upgrades GameChanger's heuristics.** |
| 10 | **DoD Verifier (router)** | `verifying-practitioner-build` | `critic-orchestrator` routing + `09-docs` traceability | Artifact classification and the routing matrix. |

#### 5.2 The verdict bridge

Write one small adapter, used by every mapped critic:

```
IBC verifier finding set  ──▶  CriticVerdict
  any BLOCKED                  → ESCALATE_TO_HUMAN
  any unresolved contradiction
    or any NEEDS-FIX           → REFINE_AGAIN
  all PASS, risk 21–60         → ACCEPT_WITH_CAVEATS
  all PASS, risk 0–20          → ACCEPT
```

**Keep IBC's aggregation rule, not GameChanger's.** IBC's is deterministic and stated: *"the verdict
is computed from the State — the LLM never decides it."* That property is worth more than matching
GameChanger's score bands.

> **[audit 2026-09-09] Prerequisite: Phase 5.0.** The first line of the bridge is dead code for five of
> the ten critics until they can emit `BLOCKED`. Do not write the adapter first and discover this in
> testing — an unresolvable input at `governor-safety` or `test-adequacy` would loop to the iteration
> cap and then be quietly accepted, which is the exact failure mode D11 exists to prevent.

#### 5.3 Reconcile the iteration cap

GameChanger's `maxIterationsPerStep` defaults to **1** in code, and **the documented promotion to
`ACCEPT_WITH_CAVEATS` at the cap is not implemented** — a stage can simply end on `REFINE_AGAIN`. IBC
should:

- set the cap explicitly (recommend **2**) rather than inheriting an ambiguous default, and
- **implement the promotion**, or make an unresolved `REFINE_AGAIN` at the cap route to IBC's `owner-block` tier so it is visibly parked rather than quietly accepted.

#### 5.4 The Clarification-Log Gate — the interesting problem

IBC's Clarification Log (**CL-1 … CL-15**) is a **project-wide register of open decisions**.
GameChanger has nothing like it. It has per-story `HARD_BLOCKER` open questions, which is a narrower
idea.

The mapping is genuinely elegant in one place:

| IBC | GameChanger | Fit |
|---|---|---|
| **CL-11** — "no `*__c` left inferred before that service's tests" | **`pendingVerifications`** + the `[Inferred: UNVERIFIED]` label | **This is the same rule, independently invented.** Wire CL-11 directly onto the verification ladder. |
| **CL-15** — `GroupRelatedBatch` blocked until the batch↔service mapping lands | `HARD_BLOCKER` → `PLACEHOLDER` in `01-plan`/`02-architecture` | direct |
| **CL-3** — must **not** create `HealthcarePractitionerFacilityNetwork` | *nothing* | needs a real gate |
| **CL-6** — `NetworkMember`/`NetworkMemberChunk` are out of pilot scope | *nothing* | needs a real gate |
| **CL-5** — use `PRM_ExceptionLog__c`, not `PRM_Exception_Log__c` | *nothing* | needs a real gate |

**Recommended implementation (D8):** two touch points, not one.

1. **A Phase 1 preflight check.** The strict preflight already refuses to proceed on warnings. Add a check that reads the Clarification Log and **refuses to schedule a story whose delivery would touch an open CL item** — the cheapest possible place to catch it.
2. **A per-stage contract check.** Extend `contractCheck()` so *every* stage — including the three lightweight ones — scans its artifact for the known CL traps. A hit returns `BLOCKED` → `ESCALATE_TO_HUMAN`.

This is exactly the Phase 3 exit criterion the old adoption plan named, and it remains the right test:

> **Exit:** a stage artifact that proposes creating `HealthcarePractitionerFacilityNetwork` — which
> CL-3 forbids — is caught by a critic and returns `REFINE_AGAIN` (or `ESCALATE_TO_HUMAN`), **without a
> human noticing first.**

---

### Phase 6 — Eval corpus and calibration · 3.0 days

**You cannot hard-gate on a critic you haven't measured.** `06_Agent_Eval_Harness.md` specifies the
corpus; the directory is empty.

| # | Task |
|---|---|
| 6.1 | Build `docs/build-verification/eval/` — labelled cases per the spec: **P01–P03** (parity), **D01–D10** (delivery), **T01–T03** (test). |
| 6.2 | Include deliberate defects: a missing object, a wrong record type, a `HealthcarePractitionerFacilityNetwork` creation, a per-record DML in a loop, an assertion-free test, an unported eligibility rule. |
| 6.3 | Run the expected-vs-actual matrix. Verdicts: `PASS` / `NEEDS-FIX` / `BLOCKED` / **`INCONCLUSIVE`**. |
| 6.4 | Tune the risk-score weights and tier thresholds against the matrix. Pin them. |
| 6.5 | Promote per the harness path: **Advisory → Soft-gate → Hard-gate.** No critic goes to hard-gate without a clean matrix. |

**Exit:** every mapped critic has a measured false-positive rate, and at least the parity, governor and
test-adequacy critics are promoted to soft-gate.

---

### Phase 7 — Pilot · 2.0 days

**You cannot judge output on a story whose right answer you do not know.** Pick something where ground
truth already exists — **you are grading the pipeline, not the story.**

> **[revised 2026-09-09] Both prerequisites are now closed.**
> 1. **Phase 4.5 ✅** — `requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md` is authored
>    (E19, per the revised D9). The adapter has a real file to ingest.
> 2. **D13 ✅ resolved — scope the pilot to the service in isolation, and no Epic A deployment is needed.**
>    The original concern was that `PractitionerBatch` and Epic A were unbuilt. Measured against `HEAD`
>    they *are* built (merely undeployed), and more to the point **E19's entire dependency set is already
>    live in `ibx-qa`**: `PRM_CMAService`, `PRM_ServiceBase`, `PRM_FormSubUtility`, `PRM_CMAServiceTest`,
>    `PRM_CaseManagerAssociation__c` and the existing consumer `PRM_ParFormCmaBatch`. `PRM_AsyncJob__c` is
>    **not** deployed and E19 never touches it. Isolation is therefore correct rather than a compromise.
>
> **This makes the pilot stronger than isolation implies.** `PRM_ParFormCmaBatch` is a *deployed consumer*
> of `PRM_CMAService`, so the Phase 7 exit criterion — a check-only deploy to `deploytarget` — becomes a
> genuine **backward-compatibility gate**: if the pipeline regenerates the service with a changed
> signature, PAR's batch fails to compile and the deploy fails. That is real integration evidence, not a
> synthetic check.

**Pilot: `PRM_CMAService` (E19)** *[revised 2026-09-09 per D9 — was E16 `PRM_CaseDataManagerService`]*.

Why this one:

- **Ground truth exists and is clean.** Parity Ledger **row 20** plus §6 rule 9 hold the CMA subset rule, and E19 carries **no open clarifications** — unlike E16, whose open CL‑E2‑12 would have caused the CL gate to block the pipeline's own pilot.
- The ledger holds a **sharp, checkable trap**: only *some* object kinds get a CMA record type. A critic either catches an association written for an ineligible kind or it doesn't.
- **The answer key already ships.** `PRM_CMAService` (+ test) is deployed, so the pipeline's output can be diffed against real shipped code. The story was deliberately grounded on the ledger and live metadata rather than on the class, keeping it a valid key.
- **It has a live deployed consumer** (`PRM_ParFormCmaBatch`), which turns the check-only deploy into a real compile-compatibility test.
- It is small enough that ten artifacts are reviewable in an afternoon, and it still exercises parity, governor, service-boundary, test-adequacy and the CL gate.

**Run all three phases end to end:**

```bash
cd IBXQA/gamechanger/control-plane

./scripts/run-production.sh \
  --feature PRM-EPIC-E \
  --story-keys PRM-E19-CMASERVICE \
  --filter ALL \
  --sequencing dependency-first \
  --phase context-assembly \
  --runs-dir ../../runs

# … Phase 2 in Cursor: work the ten job cards …

./scripts/run-production.sh \
  --feature PRM-EPIC-E \
  --story-keys PRM-E19-CMASERVICE \
  --phase extract-only \
  --runs-dir ../../runs
```

**Exit:** ten stage artifacts, a critic loop that **settles** (doesn't oscillate), an extraction packet
that validates, and a `05-build-fix` check-only deploy that reaches the `deploytarget` org and nowhere else.

**Grade it against ground truth**, not against how good it reads:

| Check | Pass condition |
|---|---|
| Parity | The objects/fields in `02-architecture.md` match **Parity Ledger row 20** (CMA), and the subset rule in §6 rule 9 is respected — no association written for an ineligible object kind |
| Verification | Every `PRM_*__c` in the artifacts carries `[Verified: …]` or `[Inferred: UNVERIFIED]` |
| Governor | `03-tdd.md` specifies the bulk-200 case; `04-code-review.md` flags any per-record DML |
| Async | E19 is invoked *inside* batches rather than owning async itself, so `06-e2e.md` should either assert the caller's halt-on-failure/DLQ path or honestly mark it **NOT RUN** — an invented async assertion here is itself a finding |
| CL gate | No artifact silently resolves an open CL item |
| Honesty | No fabricated test pass; the readiness table and blocker registry are both present |

---

### Phase 8 — Turn the optional agents on, one at a time · 1.0 day

**Every flag is off by default. Keep it that way until each one proves itself.**

Recommended order, and why:

| Order | Agent | Flag | Why here | IBC hook |
|:--:|---|---|---|---|
| 1 | `qa-e2e-tcoe-tester` | `QA_TCOE_ENABLED=1` `QA_TCOE_TEMPLATE_ENABLED=1` | Makes weak testing visible immediately, and template mode has **no write side-effects** | Maps onto Epic G **G2** (integration) and **G3** (perf regression) |
| 2 | `self-improvement` | `SELF_IMPROVE_ENABLED=1` | Needs run history before it has anything to learn from — so it goes after a few real runs | Feeds the Clarification Log with recurring defects |
| 3 | Expert-review quartet | `EXPERT_REVIEW_V2=1` | Improves the *input* to everything else, but needs a human answering gap questions to be worth anything | Complements `user-story-architect`, doesn't replace it |
| 4 | `sia-fixer` | `SIA_FIXER_ENABLED=1` | **Last.** It is the only agent that writes to source. Only turn it on once the ledger has `PROPOSED` entries you agree with | Requires `--confirm-id` per entry |
| — | CAAG · councils · assurance chain | — | Evaluate only if IBC establishes a governance forum that wants board packets | — |

**Exit:** each enabled agent has produced one useful artifact on a real IBC story, and each is
individually switchable back off.

---

## 5. Stage-by-stage: what GameChanger produces for one IBC story

Concretely, for the pilot story **E19 `PRM_CMAService`** *[retargeted 2026-09-09 per D9; the CDM references below are illustrative of the same stage shapes]*:

| Stage | Artifact | What it contains for this story | IBC critic on duty |
|---|---|---|---|
| `00-intake` | `00-intake.md` | The CDM requirement pulled from `requirements/`, ACs, dependency diagram, org reconnaissance of `PRM_CaseDataManager__c` fields with `[Verified: …]` markers | CL gate (contract check) |
| `01-plan` | `01-plan.md` | Formalised `AC-01…AC-NN`, OOB-first decisions, phases with sizes, risk register naming **P3 `UNABLE_TO_LOCK_ROW` contention** | — |
| `02-architecture` | `02-architecture.md` | ADRs, component diagram, `erDiagram` for CDM ↔ `IndividualApplication`, metadata inventory, **the coalesced-write design** | **Parity · Service-Boundary · Branch** |
| `03-tdd` | `03-tdd.md` | Test spec per AC — positive, negative, **bulk 200** — SOQL validation queries, `PRM_TestDataFactory` design, red/green/refactor walkthrough | **Test-Adequacy · Branch** |
| `04-code-review` | `04-code-review.md` | Numbered findings on bulkification, one-DML-per-object, `with sharing`, FLS, no hardcoded Ids; gate decision | **Governor · Contract** |
| `05-build-fix` | `05-build-fix.md` | The actual `PRM_CaseDataManagerService.cls` + test class + metadata; **check-only deploy to `deploytarget`**; error classification | **Parity (delivery)** |
| `06-e2e` | `06-e2e.md` | Executive readiness verdict (8+ RAG dimensions), blocker registry, execution matrix traced to ACs, halt-on-failure and DLQ evidence | **Async / Reliability** |
| `07-security` | `07-security.md` | CRUD/FLS matrix for CDM and `IndividualApplication`, OWASP walk, secret scan | — |
| `08-refactor` | `08-refactor.md` | Constants extracted, naming aligned, **behavioural change explicitly `false`**, config debt flagged | CL gate |
| `09-docs` | `09-docs.md` + `traceability.json` | Deployment runbook targeting `deploytarget` only, permission model (`PRM_AsyncJob_Access`), full evidence→AC→artifact traceability | DoD Verifier |

**Then:** `PRM_CaseDataManagerServiceTest` runs, `PRM_CaseDataManagerService` is compared against the
Parity Ledger row, and the DoD Verifier renders one report with one verdict and one risk score.

**That is the whole value proposition in one row of a table:** the thing you review is not a wall of
generated Apex. It is **ten short documents, each with a named owner and a critic's score**, plus a
verdict that a machine computed from cited evidence.

---

## 6. The exact configuration surface for IBC

### 6.1 Files to create

| Path | Tracked? | Template ships? | IBC values |
|---|---|---|---|
| `config/customer-profile.json` | gitignored | ✅ `.example` | IBX name/slug, My Domain, **no Jira projects for the PRM build** |
| `control-plane/org-registry.json` | ⚠️ **tracked and pre-populated** | ✅ `.template.json` | **`deploytarget` = `write-allowed`; everything else `read-only`** (keyed map — see §6.3) |
| `control-plane/org-registry.local.json` | gitignored | ✗ | optional local override |
| `control-plane/.env.production` | gitignored | ⚠️ **only `.env.example`** | the IBC flag profile |
| `control-plane/.env.local` | gitignored | ✅ `.env.example` | local dev flags |
| `.cursor/mcp.json` | gitignored | ✅ `.example` | + `code-review-graph`, `salesforce-docs`, `docsearch`, `user-story-architect` |
| `.cursor/hooks.json` | **create** | ✗ | `beforeShellExecution` → the SF guard |
| `.cursor/hooks/before-shell-execution-sf-guard.js` | **create** | ✗ (copy from 3.0) | the write guard |
| `control-plane/source-trust-registry.json` | tracked | ⚠️ **already ships populated** | **edit**, don't create — register IBC guidance sources (§6.4) |
| `atlassian-mcp-guardrails/.env` | gitignored | ✅ `.env.example` | **only if D3b says yes** |
| `MEMORY.md` | tracked | seed | IBC engagement decisions |

### 6.2 The IBC flag profile (`.env.production`)

```bash
# ── core ─────────────────────────────────────────────────────────────
CP_RUN_MODE=shadow                    # promote later
CP_KILL_SWITCH=0

# ── knowledge grounding (turn these ON — they are the point) ────────
KNOWLEDGE_PREP_ENABLED=1
STRUCTURED_CONTEXT_ENABLED=1
FRESHNESS_GATE_ENABLED=1              # 4h cache window
ORG_METADATA_RETRIEVAL_ENABLED=1
DELTA_REFRESH_ENABLED=1
MULTI_SOURCE_CONTEXT_ENABLED=1        # the ContextPack registry
ARCH_GUIDANCE_ENABLED=1               # docs/reference + implementation-plan
STAGE_AFFINITY_FILTER_ENABLED=1
TRUST_POLICY_ENABLED=1                # writes policy-log.jsonl — keep the audit trail

# ── gates ────────────────────────────────────────────────────────────
RUN_APEX_GATE=1
APEX_GATE_PCT=85                      # IBC standard, not the shipped 80
APEX_GATE_FATAL=0                     # advisory first (raise in Phase 6)

# ── optional agents: all OFF in v1, enable per Phase 8 ──────────────
# QA_TCOE_ENABLED=1
# QA_TCOE_TEMPLATE_ENABLED=1
# SELF_IMPROVE_ENABLED=1
# SIA_FIXER_ENABLED=1
# EXPERT_REVIEW_V2=1
# CAAG_ENABLED=1

# ── explicitly NOT used ─────────────────────────────────────────────
# AFLS_ENABLED — deleted
# NEO4J_URI    — code-review-graph covers this
# TEMPORAL_ADDRESS — deferred
# PYTHON_RAG_ENABLED — deferred
```

> **Note `APEX_GATE_PCT=85`.** The framework ships `80`; IBC's standard in `CLAUDE.md` §6 is **≥85%**
> (deploy gate 75%). **Set it to your standard, not the framework's** — this is exactly the kind of
> local quality bar the adoption pattern says belongs in the gates.

### 6.3 The org registry, concretely

> **[audit 2026-09-09] Corrected shape.** An earlier draft showed `orgs` as an **array** of three-field
> objects. That would fail to load. The real contract (`control-plane/org-registry.ts`) is a **keyed
> map**, `loadRegistry()` enforces that **the map key equals the entry's `alias` field**, and each entry
> carries fifteen fields. A registry that fails to load means `getReadOnlyOrgs()` cannot build the
> blocked-alias list — so **Phase 1's exit criterion silently cannot be met.**

Top-level keys are `orgs · defaultSourceOrg · defaultTargetOrg · _note · _safety`.

```jsonc
{
  "orgs": {
    "deploytarget": {                                  // key MUST equal .alias
      "displayName": "IBX QA (deploy target)",
      "alias": "deploytarget",
      "username": "<ibx-qa-username>",
      "instanceUrl": "https://<ibx-qa>.sandbox.my.salesforce.com",
      "accessMode": "write-allowed",
      "required": true,
      "mcpServer": "Salesforce DX",
      "allowedOperations": ["retrieve_metadata", "run_soql_query", "deploy_metadata",
                            "run_apex_test", "get_username", "open_org", "list_all_orgs"],
      "forbiddenOperations": ["create_scratch_org", "delete_org"],
      "stagingDir": "staging-deploytarget",
      "description": "IBX QA sandbox — the one and only write target",
      "refreshCadence": "daily",
      "purpose": ["deploy-target", "apex-test-gate"],
      "caagRole": { "trustLevel": "authoritative" },
      "metadataPriority": 1
    },
    "ibcprod": {
      "displayName": "IBC Production (grounding truth)",
      "alias": "ibcprod",
      "accessMode": "read-only",
      "required": true,
      "mcpServer": "Salesforce DX",
      "allowedOperations": ["retrieve_metadata", "run_soql_query", "get_username", "open_org"],
      "forbiddenOperations": ["deploy_metadata", "run_apex_test", "create_scratch_org",
                              "delete_org", "assign_permission_set"],
      "stagingDir": "staging-ibcprod",
      "description": "Grounding truth for the verification ladder",
      "refreshCadence": "daily",
      "purpose": ["metadata-baseline"],
      "caagRole": { "trustLevel": "authoritative" },
      "metadataPriority": 0
      // username / instanceUrl filled at Phase 1
    }
  },
  "defaultSourceOrg": "ibcprod",
  "defaultTargetOrg": "deploytarget"
}
```

**Grant write access to exactly one org.** Every other alias stays read-only, and the shell hook
enforces it at runtime rather than trusting anyone to remember.

**Verify the shape before moving on:** `node -e "require('./org-registry.ts')"` equivalent, or simply
run the pre-flight — a key/alias mismatch throws with a named error.

### 6.4 Source trust registry entries

| Source | Trust class | Rationale |
|---|---|---|
| IBC org metadata / SOQL | `authoritative` | wins everything |
| `sf_deps.py` structural results (Apex, OmniStudio, objects, fields) | **`authoritative`** *[revised 2026-09-09]* | it is the org's own dependency index. Caveats: deploy-time edges only (no `Type.forName` dispatch), and deployed components only |
| `code-review-graph` structural results | **not registered for Apex/metadata** | cannot parse `.cls`/`.trigger`/`.xml`; usable for LWC `.js` only |
| `handoff/to-gamechanger.json` (architect) | `scoping` | bounds scope; never states a fact; 800-token cap, 24h decay |
| `docs/build-verification/02_Parity_Ledger.md` | `guidance` | parity ground truth |
| `docs/build-verification/02b_Validation_Rule_Ledger.md` | `guidance` | eligibility-rule ground truth |
| ~~`docs/reference/*`~~ | — | **[audit] directory absent — do not register until recovered** |
| `docs/implementation-plan/*` | `guidance` | Epic guides, TDD, plan |
| `CLAUDE.md` | `guidance` | org coding standards + Clarification Log |
| `requirements/*.md` (the other 400) | `background` | searchable, never decisive |

### 6.5 Strings to scrub

| String | Where |
|---|---|
| `operator@acme.com.nextgen.sourceprimary`, `operator@acme.com.gcx.acmedev`, `operator@acme.com.deploytarget` | `control-plane/org-registry.json` |
| `https://acme--sourceprimary.sandbox.my.salesforce.com`, `acme--*.sandbox.my.salesforce.com` | `org-registry.json`, `RUNBOOK.md` |
| `Acme Corporation`, `acme`, `https://acme.atlassian.net` | `config/customer-profile.example.json` |
| `DEMOOMCT`, `DEMOASIM`, `DEMOPSTE`, `DEMOCCB` | customer profile, `caag/flags.ts` defaults |
| `CAAG_DEMOCCB_JIRA_BASE_URL ?? 'https://jira.prod.acme.com'` | `control-plane/caag/flags.ts` |
| `/Users/operator/SomGoogleDrive/.../GameChanger2.0` | `RUNBOOK.md`, `docs/operations/new-environment-bootstrap.md` |
| `project-0-GameChanger2.0-cortex-mcp` | `RUNBOOK.md` |
| `HCP_Login__c`, `CareRegisteredDevice` (domain examples) | `RUNBOOK.md` KP prompts |
| Example story keys `DEMOASIM-162`, `DEMOOMCT-1064` | `PIPELINE.md`, docs |
| Git remotes for GameChanger 2.0 / outcomes-lab | `README.md`, `REPRODUCIBILITY.md`, ledger drafts |
| Hardcoded `'deploytarget'` write alias in QA/AFLS runners | keep as the role name; **must match the registry** |

---

## 7. Decisions required

| ID | Decision | Recommendation | Status |
|---|---|---|---|
| **D1** | Base version | **GameChanger 3.0** — now available locally. Supersedes the 2026-08-29 "wait" decision. | ✅ resolved |
| **D1b** | **Provenance of the local 3.0 tree** | It is **not a git repo** and has no remote. **Get licence/provenance in writing from the owner before vendoring** (Phase 0.1). | ⛔ **open — blocks Phase 1** |
| **D2** | Where the control plane lives | **Vendored into `IBXQA/gamechanger/`.** Not a submodule — the IBC adaptation diverges immediately. | ✅ carried forward |
| **D3** | Intake source | **`requirements/*.md`.** Build the adapter in Phase 2. | ✅ carried forward |
| **D3b** | Also wire Jira/GUS? | **No, not in v1.** Keep `atlassian-mcp-guardrails` unconfigured and stub the health check. Revisit if PRM work moves into a tracker. | 🔶 open |
| **D4** | Guide hosting | **Already delivered** — the public guide is live. No further action. | ✅ done |
| **D5** | Guide scope | **Already delivered** as a reusable adoption guide with IBX as the worked example. | ✅ done |
| **D6** | Which org is the deploy target | The IBX QA org — **registered under the framework alias `deploytarget`** (see D12). One write path, one org. | ✅ resolved by D12 |
| **D7** | Verdict mapping | **Adopt the 3-way + risk-tier bridge in §5.2.** Keep IBC's deterministic aggregation. | 🔶 open, recommend accept |
| **D8** | Where the Clarification-Log Gate lives | **Both**: a Phase 1 strict-preflight check *and* a per-stage `contractCheck` extension. | 🔶 open, recommend accept |
| **D9** | Pilot story | ~~E16 `PRM_CaseDataManagerService`~~ → **E19 `PRM_CMAService`** *[audit, revised 2026-09-09]*. E16 carries the **open CL‑E2‑12**, so the CL gate would correctly block its own pilot and Phase 7 could never reach ten artifacts. E19 has a Parity Ledger row (20), **no open clarifications**, an equally sharp trap (only some object kinds have a CMA record type), and — uniquely — **already exists on disk** (228-line class + 168-line test), so the pipeline's output can be diffed against real shipped code. Story authored at `requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md`. | ✅ **resolved** |
| **D10** | CAAG / councils / Temporal in v1 | **No.** Re-evaluate in Phase 8 if a governance forum materialises that wants board packets. | 🔶 open, recommend accept |
| **D11** | Iteration cap | **Set it explicitly to 2** and implement the missing cap-promotion, or route an unresolved `REFINE_AGAIN` to `owner-block`. | 🔶 open, recommend accept |
| **D12** | **Write-alias identity** *[audit]* | **Keep the framework alias `deploytarget`** and point it at the IBX QA org (`sf alias set`). `deploytarget` is hardcoded in ≥4 framework files and the alias is the only identifier the framework uses. Zero edits, preserves R9. D6's "one name" goal is **deferred, not dropped**. | 🔶 open, recommend accept |
| **D13** | **Pilot scope vs Epic A** *[audit]* | **Resolved 2026-09-09: (a) service in isolation — and no Epic A deployment is required.** E19's whole dependency set is already deployed to `ibx-qa` (`PRM_CMAService`, `PRM_ServiceBase`, `PRM_FormSubUtility`, `PRM_CMAServiceTest`, `PRM_CaseManagerAssociation__c`, plus the live consumer `PRM_ParFormCmaBatch`); `PRM_AsyncJob__c` is undeployed and E19 never touches it. The premise that Epic A was *unbuilt* was also wrong — it is committed, just undeployed. | ✅ **resolved** |
| **D15** | **Grounding source == deploy target** *[Phase 1]* | `defaultSourceOrg` is set to `deploytarget` (ibx--qa) because that is where the PRM verification baseline actually lives, and both `sf_deps.py` and `CLAUDE.md` ground on it. This departs from the framework's assumption of a *separate read-only* grounding org, so **grounding truth is mutable by our own deploys** — a `[Verified: …]` marker could be validated against metadata the pipeline itself just wrote. Also forced by fact: **no IBC production org is authenticated**, so the plan's "IBC production = grounding truth" registry row cannot be populated at all. **Resolved 2026-09-09: accepted knowingly for the pilot.** The consequence is carried explicitly rather than fixed: a `[Verified: …]` marker means *"present in ibx--qa at the time of the query"*, **not** "independently confirmed against an immutable baseline". Two obligations follow — (i) Phase 3's exit test must resolve its probe field **before** the pipeline deploys anything in that run, so the check cannot be satisfied by the pipeline's own write; (ii) if a read-only IBC org is ever authenticated, re-point `defaultSourceOrg` and re-run the Phase 3 exit test. Tolerable now because E19's dependency set was already deployed **before** this pipeline existed (D13), so for the pilot specifically the baseline is genuinely independent. | ✅ **resolved — accepted with caveat** |
| **D16** | **What the green-build gate means** *[Phase 1]* | ~~The vendored artifact cannot type-check: 33 missing modules … obtain a complete artifact (option a), which promotes Phase 0.2 to blocking.~~ **REVISED 2026-09-09 — the premise was wrong.** Report finding **F1 is retracted**: the scrub rewrote import *specifiers* without renaming *files*, so the "missing" modules were present under pre-scrub names. Repaired locally (`scripts/repair-vendored-import-map.sh`, 6 renames + 2 stale paths) → **`TS2307` 33 → 11, total 569 → 543, 0 parse errors**. The 11 survivors sit in **7 files, none on the executed path**: `adapter-registry.ts` is reached only via **Temporal (out by D10)**, `cortex-mcp`'s 5 imports are a boundary test plus a **Jira script (neutralised by D3)** — the bridge the routines use is in-tree — and `vitest`'s 4 are **orphan files no runner references**. The residual 543 are upstream strict-null / `exactOptionalPropertyTypes` debt, identical on the pristine copy. **Resolved 2026-09-09 as option (b), and Phase 0.2 reverts to non-blocking** (still wanted for **R9** rebase and for `adapter-registry.ts`). **The gate means: the executed path is loadable and its module graph is intact** — implemented as `tsconfig.gate.json` + `scripts/verify-gc-gate.sh`, with the path **computed** by TypeScript from the three CLI entry points (189 first-party files) rather than hand-listed, so off-path code drops out by construction instead of via exclusion lists that rot. Two assertions: **hard** — zero parse errors and zero unresolved imports, the exact two things the scrub broke; **ratchet** — strictness errors may not exceed a recorded baseline of **87**, so upstream's debt is neither inherited as our fault nor allowed to grow. `tsconfig.gate.json` inherits every strictness flag **unchanged**; loosening it to manufacture a pass is the R10 failure mode. Negative-tested: injecting an unresolved import and injecting a spaced identifier each fail the gate. | ✅ **resolved — option (b), gate implemented and passing** |
| **D14** | **Graph trust class** *[audit]* | ~~Register `code-review-graph` at `guidance`, promote on measured recall.~~ **VOID 2026-09-09** — it cannot parse Apex or XML, so no trust class applies. Superseded by `sf_deps.py` at `authoritative`. | ⛔ void |

---

## 8. Risks

| # | Risk | Likelihood | Mitigation |
|:--:|---|---|---|
| R1 | **Provenance/licence of the vendored tree** is never clarified and we've embedded it in a client-adjacent repo | Medium | **Phase 0.1 is a hard gate.** Do not *commit* before D1b closes — as of 2026-09-09 the tree is vendored to a **gitignored** `/gamechanger/`, which unblocks Phases 1–6 at zero legal exposure. The tree also arrived **corrupted by the upstream scrub** — identifiers broken in six files (F2) and the import graph broken tree-wide (F1) — both repaired locally, so Phase 0.2 (upstream access) stays **optional but worth asking**, since R9 still wants a rebase path. |
| R2 | **The intake adapter drifts from the architect contract** as `user-story-architect` evolves (it's at v1.10+ and moving) | High | Pin the section contract in the adapter and add the round-trip test (2.7) to CI. Use `lint_story` as the upstream guard. |
| R3 | **Tool-allowlist gaps make verification silently degrade** — this is a live defect in the shipped tree | **High** | Phase 3.3 fixes it explicitly. Add an assertion that `00-intake` actually executed its `pendingVerifications`. |
| R4 | **Critics false-positive and the team routes around them**, which is how gates die | High | **Phase 6 exists for this.** Advisory → soft-gate → hard-gate, and nothing is promoted without a clean eval matrix. |
| R5 | **Phase 2 is human time, not machine time.** People expect a batch job | Medium | Say it out loud in the rollout comms: **the pipeline does not call a model API.** Budget the editor time. |
| R6 | **A generated deploy hits the wrong org** before the write guard exists | Medium | Phase 1.4 is non-deferrable. Test that a blocked command exits `2`. |
| R7 | **The Clarification Log and the trust ladder contradict each other** — two golden hierarchies | Medium | Phase 3 maps `CLAUDE.md` §0 *inside* the `guidance` class, with only live org metadata at `authoritative`. |
| R8 | **We adopt 23 agents because 23 sounds impressive**, and the surface area buries the value | Medium | Ten stages plus IBC's critics is the whole v1. Everything else stays flag-off until it earns its place. |
| R9 | **Upstream 3.0 moves and we can't rebase** (hard fork, no remote) | Medium | Record the snapshot date; keep IBC changes confined to the config surface and the five adapter/critic files so a future rebase is tractable. **D12 (keep `deploytarget`) exists partly to protect this.** |
| **R10** | **A structural source that silently returns nothing is trusted as ground truth** *[audit; re-scoped 2026-09-09]* | **High** | Realised for `code-review-graph`: it returns 0 edges on Apex because it cannot parse it, which is exactly the unfalsifiable failure the trust ladder exists to prevent. Mitigated by removing it from the Apex path entirely and replacing it with `sf_deps.py`, whose *own* completeness trap is documented and worked around by per-component queries. **A zero result from a parser that cannot read the language is not evidence of absence.** |
| **R11** | **Brownfield false-positive surge** — critics meet 644 pre-existing `PRM_*` classes never held to these standards, the team concludes the critics are noisy, and routes around them (this is how gates die) *[audit]* | **High** | Phase 6 is re-estimated to 3.0 days for exactly this. **Scope critics to changed artifacts in the run, not the whole estate**, and calibrate thresholds against the brownfield baseline before any soft-gate promotion. |
| **R12** | **The pilot is scheduled before its intake story or async context exists** *[audit]* | ~~Medium~~ **closed** | Phase 4.5 authored the E19 story, and D13 resolved: E19's dependency set is fully deployed, so no async context is missing. |

---

## 9. Definition of done for the integration

The integration is complete when **all** of these are true:

- [ ] Provenance for the vendored tree is recorded, and D1b is closed.
- [x] ~~`npm run typecheck` **(run from `gamechanger/control-plane/`)** passes with **zero** `acme` references in the vendored tree.~~ **Re-scoped 2026-09-09 and now met.** Replaced by `bash scripts/verify-gc-gate.sh` (**D16** option b), which passes: **189-file executed path, 0 parse errors, 0 unresolved imports, 87 strictness errors at baseline.** Whole-tree typecheck is 543 and deliberately not the gate — chasing it would mean editing upstream code. ~~The artifact is missing 23 modules~~ — **retracted** (report F1). The zero-`acme` half is unachievable without editing the framework, so it is re-scoped to live configuration only — which *is* clean. See `06_Phase1_Vendoring_Report.md` F1 and F11.
- [x] `org-registry.json` **loads** — keyed map, every key equal to its entry's `alias`, all fifteen fields present. *(2026-09-09: 13 orgs, exactly one `write-allowed`, zero `acme`.)*
- [ ] A write aimed at any org other than the `deploytarget` alias is **refused by the hook**, exit code `2`.
- [x] **`sf_deps.py` returns correct callers/callees/tests for the Phase 3.0 probe set**, verified against hand-run SOQL, with its limits recorded. *(`code-review-graph` is excluded from the Apex path — D14 void.)*
- [ ] **All ten verifiers document a three-valued verdict** — the five two-valued ones have a `BLOCKED` condition and a corpus case for it.
- [x] **The E19 requirements story exists** (`requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md`); round-trip through the intake adapter still to be asserted (4.5.3/4.5.4).
- [ ] `--phase context-assembly` produces ten valid task files from a real `requirements/*.md` story, with no Atlassian dependency.
- [ ] A `pendingVerifications` query resolves a real `PRM_*__c` field against the IBC org, and a fabricated field returns `[Inferred: UNVERIFIED]`.
- [ ] A story-architect scope pack seeds stages `00`–`02`, is capped at 800 tokens, decays over 24 hours, and **loses** a conflict with live org metadata in a test.
- [ ] All ten IBC verifiers are wired into critic slots and return the mapped `CriticVerdict` values.
- [ ] An artifact proposing `HealthcarePractitionerFacilityNetwork` (CL-3) is **caught by a critic**, not by a human.
- [ ] `docs/build-verification/eval/` holds the labelled corpus, and at least three critics are promoted to soft-gate on a clean matrix.
- [ ] The E19 pilot produced ten artifacts, a settling critic loop, and a validated extraction packet.
- [ ] `05-build-fix` reached the `deploytarget` org check-only, and nowhere else.
- [ ] Every optional agent is **off**, and each one that gets turned on has produced one useful artifact first.

---

## 10. What I would tell the team on day one

Three things, and nothing else.

1. **This is not a magic story-to-code button.** It is an assembly line that makes failure *loud* — at a named stage, in a file you can read. The value is not speed. **The value is that when something is wrong, you can point at which of twenty-three things did it.**

2. **You are Phase 2.** The pipeline writes job cards and stops. You open Cursor and do the work with the real org in front of you — **because a detached model call cannot verify its own claims**, and verification is the entire point.

3. **We already built a third of this without knowing it.** Ten verifier agents, two ground-truth ledgers, a story architect, a knowledge graph. GameChanger's contribution is the assembly line and the harness. **IBC's contribution is the inspectors** — and ours know things about PRM that no generic critic ever will.

> The measure of a good adoption is not how many agents you turn on. **It is whether, six months in,
> someone can still point at a bad artifact and name the stage that produced it.**

---

## 11. Sources

Everything above is grounded in files, not inference.

**GameChanger 3.0** (`/Users/pkothapalli/storm-b2111773b5b61c/gamechanger3.0`):

| Claim | Source |
|---|---|
| Stage order, agent map, rework map, iteration cap default | `control-plane/execution/contracts.ts` |
| Cursor-only generation, task-file shape | `control-plane/execution/context-bridge/llm-provider.ts`, `commands/feature-orchestrate.ts` |
| Three-phase flags, freshness window | `control-plane/scripts/run-production.sh`, `PIPELINE.md` |
| Critic ids, tiers, verdict enum, critical thresholds | `control-plane/critic/`, `critic/verdict-schema.ts`, `execution/generator-pipeline.ts` |
| Trust ladder, token budgets, decay | `control-plane/knowledge-prep/context-pack.ts`, `pack-registry.ts`, `pack-compactor.ts` |
| Thirteen foundation agents, flags, `hls-delivery-architect` absence | `control-plane/agents/*/`, `control-plane/config/flags.ts`, `control-plane/qa/flags.ts` |
| Org registry, write guard, `deploytarget` | `control-plane/org-registry.json`, `org-registry.ts`, `.cursor/hooks/before-shell-execution-sf-guard.js` |
| Placeholder identity to scrub | `config/customer-profile.example.json`, `control-plane/caag/flags.ts`, `RUNBOOK.md` |
| Scoring deprecation | `control-plane/schema/score-card.ts`, `docs/architecture/DEPRECATED-MAP.md` |
| Config surface, gitignore status | `docs/CUSTOMER-ONBOARDING.md`, `control-plane/.env.example` |

**IBC** (`/Users/pkothapalli/Documents/IBXQA/IBXQA`):

| Claim | Source |
|---|---|
| Ten verifier agents, verdicts, routing matrix, risk weights, tiers | `docs/build-verification/01_Agent_Catalog.md`, `.cursor/skills/verifying-*/SKILL.md` |
| Verification architecture, Verification State | `docs/build-verification/00_Architecture.md` |
| Eval harness spec (corpus empty) | `docs/build-verification/06_Agent_Eval_Harness.md` |
| Parity + eligibility ground truth | `docs/build-verification/02_Parity_Ledger.md`, `02b_Validation_Rule_Ledger.md` |
| Story contract, personas, hard blockers | `.cursor/skills/user-story-architect/SKILL.md` |
| Epics A–G, Clarification Log CL-1…CL-15, coding standards, milestones | `CLAUDE.md` |
| Async design, batch classes, object model | `docs/implementation-plan/PRM_IBC_HighVolume_TDD.md`, `Epic_A_Environment_Setup.md`, `Epic_C_Async_Framework.md` |
| Target org `ibx-qa`; no `.cursor/hooks/` | `.sf/config.json`, `.sfdx/sfdx-config.json`, filesystem |
| MCP servers configured | `.cursor/mcp.json` |
| 411-file requirements corpus | `requirements/` |
| Prior decisions D1–D5 | `docs/gamechanger/IBX_GameChanger_Adoption_Plan.md` |

**External:** the published [GameChanger agent guide](https://p-kothapalli.github.io/gamechanger-agent-guide/).
The upstream repository `sbalakrushnan_sfemu/GameChanger3.0-multi-agentic-SDLC` is inside the
Salesforce-EMU enterprise and **is not reachable** from a non-EMU GitHub identity — hence D1b.
