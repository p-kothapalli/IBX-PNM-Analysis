# Audit — `02_IBC_Integration_Plan.md`

**Date:** 2026-09-09 · **Reviewer role:** senior technical architect · **Verdict:** **conditional go**
**Audited against:** the live `gamechanger3.0` tree at `/Users/pkothapalli/storm-b2111773b5b61c/gamechanger3.0`
and the live IBXQA working tree — not against the plan's own citations.

Roughly thirty specific technical claims were re-derived from source. **Most are exactly right**,
including several subtle ones the plan deserves credit for. Four findings block Phase 1, five more
must close before the phase that depends on them, and one framing premise in §0 is now false.

---

## 1. Blocking — resolve before Phase 1 starts

### B1 · `code-review-graph` is empty, and the plan trusts it at `authoritative`

| Evidence | Value |
|---|---|
| `list_graph_stats_tool` | Files **2** · nodes **2** · edges **0** · embeddings **0** · languages `javascript` |
| `semantic_search_nodes_tool("PRM_CaseDataManagerService")` | **0 results** |
| Actual estate | **28,271** files under `force-app/` |

The plan rates this asset "strong" (§1), registers it at trust class **`authoritative`** for structure
(Phase 3.2), and asserts "it indexes the real estate" (§6.4). **It indexes two JavaScript files.**

This is worse than a missing tool. `SUB_BUDGET.authoritative = Infinity`
(`knowledge-prep/pack-compactor.ts:38`), so authoritative packs bypass the 4000-token budget and win
every conflict by construction. An authoritative source that silently returns nothing becomes
unfalsifiable — exactly the failure the trust ladder exists to prevent.

> ### ⛔ B1 SUPERSEDED — 2026-09-09, after attempting the fix
>
> The fix below was attempted and **failed for a reason that invalidates the finding's framing**. The graph is
> not empty *pending a build* — it is **structurally incapable of parsing Apex**.
> `code_review_graph.parser.EXTENSION_TO_LANGUAGE` covers 30 languages; `.cls`, `.trigger` and `.xml` are
> **all absent**. A `full_rebuild` parsed **2 files** and produced 0 edges while 7 `.cls` files sat
> materialized on disk.
>
> So this is not a trust-class problem to be solved by demotion to `guidance`. For an estate of 714 Apex
> classes, 914 object dirs and 4,091 OmniStudio files, the graph cannot be a structural grounding source **at
> any trust class**. Plan **Phase 3.0 is infeasible as written** and decision **D14** ("promote to
> `authoritative` on measured recall") is **void**.
>
> **Actual resolution.** Replaced by `scripts/dependency-graph/sf_deps.py` over the Tooling API object
> `MetadataComponentDependency` — the org's own dependency index, covering Apex, LWC, Flow, FlexiPage,
> OmniScript and Integration Procedures, and authoritative because it comes from the org. Validated:
> `callers_of PRM_CMAService` → `PRM_CMAServiceTest`, `PRM_ParFormCmaBatch`. Full evidence, including the
> object's **completeness misreporting** trap, in `docs/gamechanger/05_Org_Reconciliation.md`.
>
> The closing note below was also wrong about cause: the graph-first workspace rule was unenforceable not
> because the graph was unbuilt, but because it can never parse this repo's languages. Both rules have been
> rewritten accordingly.

**Fix (attempted, superseded — retained for the record).** Insert **Phase 3.0 — build and prove the graph**:
run `build_or_update_graph_tool` + `embed_graph_tool` over `force-app/`, then assert non-zero recall on a set
of known classes (`PRM_ServiceBase`, `PRM_ExceptionLogger`, `PRM_AddressSelector`). Register at **`guidance`**,
and only promote to `authoritative` once recall is measured in Phase 6. Estimated **1.5–2.5 days**, currently
unbudgeted.

### B2 · The org-registry JSON in §6.3 is structurally invalid

The plan shows `orgs` as an **array** of three-field objects. The real contract
(`control-plane/org-registry.ts`, shipped `org-registry.json`) is a **keyed map** with a load-time
integrity check that the map key equals the entry's `alias` field, and fifteen fields per entry:

```
displayName · alias · username · instanceUrl · accessMode · required · mcpServer
allowedOperations · forbiddenOperations · stagingDir · description · refreshCadence
purpose · caagRole · metadataPriority
```

Top-level keys are `orgs · defaultSourceOrg · defaultTargetOrg · _note · _safety`.

As written, Phase 1.3 produces a registry that fails to load, `getReadOnlyOrgs()` cannot build the
blocked-alias list, and **Phase 1's own exit criterion — "a write aimed at a read-only alias is
refused" — cannot be met.** Replace §6.3 with a full-shape example derived from
`org-registry.template.json`.

### B3 · Alias collision: `ibx-qa` versus the hardcoded `deploytarget`

`org-registry.ts` states the alias is "the ONLY identifier used in paths, manifests, and API calls",
and `getOrgConfig()` throws on an unregistered alias. `deploytarget` is hardcoded in at least:

- `scripts/run-production.sh:183` — `sf-test-gate.sh --target-org deploytarget`
- `critic/stages/05-build-fix-critique/agent.ts` (and its `SKILL.md`)
- `commands/qa-tcoe.ts`
- `tests/regression/sf-guard-hook.test.ts`

§6.3 and **D6** say the write alias is `ibx-qa`; §6.5 says keep `deploytarget` "as the role name".
**These contradict each other**, and the plan never resolves it.

**Recommendation.** For v1, register the org under alias **`deploytarget`** and point the local SF
alias at the IBX QA org (`sf alias set deploytarget=<ibx-qa username>`). Zero framework edits, keeps
R9 (rebaseability) intact. Record explicitly that D6's "one name for one org" is deferred, rather than
leaving two readings of the same decision in the document.

### B5 · `docs/reference/` does not exist — one of the five guidance sources is empty

Phase 3.4 registers `docs/reference/` at trust class `guidance` and names three files as "**the legacy
parity spec**". §1 rates the fit "direct". §6.4 lists `docs/reference/*` in the source trust registry.
`CLAUDE.md` §2.3 and §0's golden hierarchy both cite it.

**The directory does not exist.** None of the named files is anywhere under `docs/`:

| Named file | Found |
|---|---|
| `PRM_PractitionerCreationContainer_Process.md` | **no** |
| `PRM_PractitionerCreation_Apex_Service_Flow.md` | **no** |
| `PRM_PractitionerCreation_Hierarchy.md` | **no** |
| `prmAsyncJobProgress_Mockup.html` (Epic C5 UI target) | **no** |

`docs/` contains only `build-verification/`, `demos/`, `gamechanger/`, `implementation-plan/`,
`interviews/`.

**Consequence.** The legacy-parity ground truth the critics lean on is **only** the Parity Ledger and
the Validation Rule Ledger — both of which are real and populated. The deeper behavioural spec that
Phase 3.4 promises is absent, so Phase 3.4 registers an empty source and the Parity Auditor's
"citations to the underlying legacy DR table" have no document behind them.

**Fix.** Either recover the three documents, or drop `docs/reference/` from Phase 3.4 and §6.4 and
state plainly that parity ground truth = the two ledgers. Do not leave a dead `guidance` registration
in the trust registry — an empty source that is *believed* to exist is how a critic ends up silently
unable to cite anything.

### B4 · The pilot has no intake artifact and no async context to run in

Phase 7 executes `--story-keys PRM-E16-CDMSERVICE`, and the Phase 2 adapter reads
`requirements/<Story>.md`.

- **No E16/CDM story exists in `requirements/`** — no filename matches `cdm`, `casedata` or `E16`
  across 191 top-level and 412 recursive markdown files. The E16 specification lives in
  `docs/implementation-plan/Epic_E_Practitioner_Services.md`, which the plan registers at `guidance`,
  **not** as intake.
- The plan frames the pilot as E16 "inside a `PractitionerBatch` step". Neither exists:

| Artifact | State as audited | **Corrected 2026-09-09** |
|---|---|---|
| `PRM_CaseDataManagerService` | absent | **committed in `HEAD`** (with tests) |
| `PractitionerBatch` and the other four batch classes | absent | `PRM_PractitionerBatch` **committed**; the other four not authored |
| `PRM_AsyncOrchestrator`, `PRM_AsyncJobCleanupBatch` | absent | **committed** (with tests) |
| `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c` | absent | **committed** |
| `PRM_AsyncJobConfig__mdt`, `PRM_AsyncJob_Access` | absent | **committed** (+ 4 config rows) |

> ### ⛔ B4 PARTIALLY VOID — 2026-09-09
>
> The "absent" column was measured from the **working tree**, where `force-app/` sits outside the git
> **sparse-checkout cone** and 127 committed files are `skip-worktree`. Measured against `HEAD` instead,
> almost all of it is authored and tested — see `docs/gamechanger/05_Org_Reconciliation.md` §3.
>
> **What stands:** no E16 story file existed in `requirements/`. That was real, and it was the actual blocker.
> **What is void:** "no async context to run in". Epic A and Epic C are committed. They are, however, **not
> deployed** to `ibx-qa` (only Epic B and `PRM_CMAService` are), so a *deployment* prerequisite remains — a
> materially different and much smaller problem than "does not exist".
>
> The **E16 → E19 pilot switch still holds**: it rested on CL‑E2‑12 being open, which is independent of build
> state.

**Fix.** Add a task before Phase 7 to author the pilot story through `user-story-architect` — which
conveniently also exercises the Phase 4 scope-pack emitter on a real case — and decide explicitly
whether the pilot is scoped to the service in isolation or waits on Epic A **being deployed**.

---

## 2. Major — fix before the dependent phase

### M1 · The "empty scaffold" premise is false

§0 ("Why the timing is unusually good") states that `force-app/main/default/` is an empty scaffold and
that "we are not retrofitting a pipeline onto finished code." Actual contents:

| | Count |
|---|---:|
| Files under `force-app/` | 28,271 |
| Apex classes | 714 (**644** `PRM_*`) |
| Object directories | 914 |
| LWC components | 198 |
| Triggers | 32 |
| Custom metadata records | 461 |
| Permission sets | 41 |

A full brownfield retrieve has landed since the plan was written. The **conclusion** survives — the PRM
Modernization target build genuinely hasn't happened — but the **reasoning** must be rewritten, and
three consequences follow: graph indexing is now expensive (B1), `retrieve_metadata` grounding partly
duplicates what is already on disk, and **critics will meet 644 pre-existing `PRM_*` classes that were
never held to these standards.** Expect a false-positive surge in Phase 6 and budget for it.

> ### ⛔ The frontier table below is WRONG — corrected 2026-09-09
>
> It was measured from the **working tree**. `force-app/` is outside this repo's git **sparse-checkout cone**,
> so 127 committed files carry `skip-worktree` and never materialize on disk. Reading `HEAD` instead reverses
> the verdict on Epics A, C and E.
>
> **The frontier is two-axis** — authored and deployed are different, and they disagree:
>
> | Epic | In git `HEAD` | Deployed to `ibx-qa` |
> |---|---|---|
> | A — async objects / MDT / permission set | ✅ committed (+ 4 config rows) | **✗** |
> | B — foundation | ✅ committed | ✅ |
> | C — async framework (+ 2 LWCs, Jest tests) | ✅ committed | **✗** |
> | E — `PRM_PractitionerBatch` + E1/E2/E5/E6/E7/E10/E11/E16 | ✅ committed, each with tests | **✗** |
> | E19 — `PRM_CMAService` | ✅ committed | ✅ |
> | F — `PRM_JsonJobUploadService` / `Controller` | ✅ committed | **✗** |
>
> So the claim "the PRM Modernization target build genuinely hasn't happened" is **false for authorship** and
> **true for deployment**. Milestones M0–M2 are largely delivered in source. The out-of-order observation is
> also void: A, B and C were all authored together. Evidence:
> `docs/gamechanger/05_Org_Reconciliation.md` §3.
>
> The rest of M1 stands: 28,271 files are on disk, the brownfield false-positive surge (R11) is real, and the
> 644 pre-existing `PRM_*` classes will meet critics that never held them to these standards.

**Actual Epic frontier — SUPERSEDED, see the correction above:**

| Epic | State |
|---|---|
| A — async objects/metadata/permset | **not built** |
| B — foundation | **built** — `PRM_ServiceBase`, `PRM_FormSubUtility` (+ tests) |
| C — async framework | **not built** |
| E — services | only `PRM_CMAService` (+ test) |
| Reuse targets (confirm CL-5/CL-8/CL-9) | `PRM_ExceptionLogger`, `PRM_AddressSelector`, `PRM_PractitionerCreationValidator` all **present** |

Epic B was built ahead of A and C, which is out of the documented dependency order.

### M2 · Half the verifiers are two-valued, not three-valued

§1 asserts all ten verifiers emit `PASS`/`NEEDS-FIX`/`BLOCKED` and calls the three-valued verdict "the
single most important technical finding in this plan." Read from the skills themselves:

| Three-valued (define `BLOCKED`) | Two-valued (`PASS`/`NEEDS-FIX` only) |
|---|---|
| `verifying-parity` | `verifying-async-reliability` |
| `verifying-contract-conformance` | `verifying-branch-coverage` |
| `verifying-clarification-log` | `verifying-governor-safety` |
| `verifying-cross-validation` | `verifying-service-boundary` |
| `verifying-practitioner-build` | `verifying-test-adequacy` |

Example, `verifying-governor-safety` §Verdict: *"**NEEDS-FIX** on any SOQL/DML-in-loop … **PASS**
otherwise."* No third state.

**Consequence.** The §5.2 bridge rule `any BLOCKED → ESCALATE_TO_HUMAN` **can never fire for five of
the ten critics.** They can only return `ACCEPT` / `ACCEPT_WITH_CAVEATS` / `REFINE_AGAIN`, so an
unresolvable upstream input at those stations loops to the iteration cap instead of escalating — which
is precisely the behaviour D11 is trying to eliminate.

**Fix.** Add **Phase 5.0**: define a `BLOCKED` condition for each of the five. Each has an obvious one
(governor-safety when the perf harness has not been run; test-adequacy when coverage is unobtainable
because the class will not deploy; branch-coverage when the IBC/Delegated branch matrix is itself an
open CL item). ~0.5 day, and it is a prerequisite for the bridge rather than a refinement.

### M3 · Jira coupling is wider than `00-intake`

Gap 1 and Phase 2.5 treat Atlassian as a `00-intake` problem. Measured from the stage allowlists:

| Stage | Atlassian/Jira tools in `tools.yaml` |
|---|---|
| `00-intake` | `atlassian_health_check`, `jira_get_issue`, `jira_search` |
| `01-plan` | `atlassian_health_check`, `jira_get_issue`, `jira_search` |
| `02-architecture` | `atlassian_health_check`, `jira_get_issue` |
| `04-code-review` | `atlassian_health_check`, `jira_get_issue` |

Health-check neutralisation and the `search_confluence_pages` remap must cover **four** stages.
Phase 2 is scoped for one.

### M4 · Phase 1.10's green-build gate cannot run as written

`npm run typecheck` does **not** exist in the GameChanger root `package.json` — its only scripts are
`test:lwc*`. `typecheck` (`tsc --noEmit`) exists solely in `control-plane/package.json`. The exit
criterion must specify `cd gamechanger/control-plane && npm install && npm run typecheck`.

### M5 · Phase 1.1's vendor list is incomplete

It names `control-plane/ · pipeline/ · scripts/ · shared/ · config/ · .cursor/hooks/`. The tree also
contains `agentic-sdlc-framework/ · optional-skills/ · jest-mocks/ · jest.config.js · package.json ·
sfdx-project.json · atlassian-mcp-guardrails/ · docs/`, and `.cursor/` additionally holds `rules/`,
`skills/`, `hooks.json` and `mcp.json.example`. At minimum the root `package.json`, `jest.config.js`
and `jest-mocks/` are needed for the test suite later phases rely on. Note `hooks.json` already exists
upstream and can be copied rather than authored (Phase 1.4).

---

## 3. Minor / stale

| # | Finding |
|:--:|---|
| m1 | **Phase 1.8 is already done.** `.cursor/mcp.json` already registers `code-review-graph`, `docsearch`, `salesforce-docs`, `user-story-architect` and `Salesforce DX`. Downgrade to "verify". |
| m2 | Requirements corpus is **412** recursive markdown files (191 top-level), not 411. Cosmetic. |
| m3 | `control-plane/source-trust-registry.json` **already ships**; §6.1's "template ships ✗" reads as "must create". It is an edit, not a creation. |
| m4 | `docs/build-verification/reports/` exists and is absent from the §11 source table. |
| m5 | §5.1 maps ten verifiers onto six critic slots; `01-plan-critique`, `07-security-critique` and `10-caag-critique` keep GameChanger's generic critics. That is a reasonable choice but should be stated, since the DoD reads as though all eight slots get IBC coverage. |

---

## 4. Confirmed accurate — do not re-litigate

Every item below was re-derived from source and matches the plan.

| Claim | Evidence |
|---|---|
| `maxIterationsPerStep` defaults to **1**; cap-promotion not implemented | `execution/contracts.ts:445` |
| Verdict enum is exactly `ACCEPT · ACCEPT_WITH_CAVEATS · REFINE_AGAIN · ESCALATE_TO_HUMAN` | `critic/verdict-schema.ts:25` |
| Trust budgets: authoritative ∞ · **scoping 800** · guidance 1200 · persona 600 · background 400 | `knowledge-prep/pack-compactor.ts:37-43` |
| Shared non-authoritative budget **4000** | `knowledge-prep/pack-registry.ts:29` |
| `APEX_GATE_PCT` ships at **80**; IBC standard is 85 | `scripts/run-production.sh:182-183` |
| `00-intake` has **no** Salesforce tools despite its rules requiring SOQL | `execution/stages/00-intake/tools.yaml` |
| `01-plan` lacks `retrieve_metadata`; `05-build-fix` has only `deploy_metadata` + `run_apex_test` | respective `tools.yaml` |
| **8** critic stages; `00`, `08`, `09` uncovered → "8 critics + 3 contract checks" | `critic/stages/`, `critic/critic-orchestrator.ts:44-52` |
| Stage order `00-intake … 09-docs` | `execution/contracts.ts:23-25, 454-456` |
| `.env.production.example` genuinely does not exist — only `.env.example` | filesystem |
| All **21** env flags named in §6.2 exist in the tree | grep across `control-plane/` |
| All **6** CLI flags in the Phase 7 commands exist | `scripts/run-production.sh` |
| The 3.0 tree is genuinely **not a git repository** → D1b is real | `git remote -v` |
| IBC risk weights `BLOCKED 40 · contradiction 25 · NEEDS-FIX 15 · uncited 10`; tiers 0–20 / 21–60 / 61–100 | `verifying-cross-validation/SKILL.md:31-34` |
| Parity Ledger is **real and populated** (175 lines, 40 rows) and row 19 + §6 trap 3 hold the CDM coalesced-write trap exactly as described | `docs/build-verification/02_Parity_Ledger.md:87, 137-140` |
| Eval corpus directory genuinely absent | no `docs/build-verification/eval/` |
| `.cursor/hooks/` genuinely absent in IBXQA; target org is `ibx-qa` | filesystem, `.sf/config.json` |
| Ten `verifying-*` skills exist, each with a `SKILL.md` | `.cursor/skills/` |
| `prm-service-class-boundaries.mdc` exists | `.cursor/rules/` |

**D9's ground truth is sound.** The Parity Ledger trap the pilot depends on is real and sharp — the
pilot's problem is intake and sequencing (B4), not the choice of story.

---

## 5. Effort — 16.5 days is understated

| Addition | Days |
|---|---:|
| Build, embed and prove the knowledge graph (B1) | +1.5–2.5 |
| Correct org registry shape and alias decision (B2, B3) | +0.25 |
| Define `BLOCKED` for five two-valued verifiers (M2) | +0.5 |
| Atlassian neutralisation across four stages, not one (M3) | +0.5 |
| Author the E16 story for intake (B4) | +0.5 |
| Brownfield false-positive calibration on 644 existing classes (M1) | +1.0 |
| **Revised total** | **≈ 21–22** |

Excludes Epic A, if the pilot is judged to need the async objects.

---

## 6. Sequencing corrections

1. **Phase 0 stays a hard gate.** D1b (provenance) is correctly identified and correctly blocking.
2. **New Phase 3.0** — build and prove the graph. Blocks 3.2 and §6.4's `authoritative` registration.
3. **New Phase 5.0** — add `BLOCKED` verdicts. Blocks the §5.2 bridge.
4. **Phase 4 before Phase 7.** The pilot's story must be authored through the architect, which is the
   scope-pack emitter's first real test.
5. **Decide Epic A's position** relative to the pilot before Phase 7 is scheduled.

---

## 6a. Post-audit actions taken (2026-09-09)

| # | Action |
|---|---|
| 1 | **Plan corrected** — §0 premise rewritten with the real Epic frontier; §1 asset inventory and verdict claim fixed; §5.2 gated on Phase 5.0; §6.3 replaced with the real registry schema; §6.4 graph downgraded to `guidance`; Phases **3.0**, **4.5**, **5.0** added; effort re-baselined to **21.25 days**; **D12/D13/D14** and **R10/R11/R12** added. |
| 2 | **Pilot switched, D9 resolved** — from E16 `PRM_CaseDataManagerService` to **E19 `PRM_CMAService`**. E16 carries the open **CL‑E2‑12** (CDM manifest timing), so the Clarification-Log Gate would correctly block the pilot and Phase 7 could never produce ten artifacts. E19 has clean ground truth, an equally sharp trap, and an existing implementation to diff against. |
| 3 | **Pilot story authored** — `requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md`, written through the User Story Architect contract and grounded on the Parity Ledger plus live metadata **only**, so the shipped class remains a valid answer key. |
| 4 | **B5 raised** — `docs/reference/` does not exist; Phase 3.4 and §6.4 corrected. |

### Two findings that surfaced while authoring the pilot story

**F1 — The Parity Ledger contradicts live metadata.** §6 rule 9 states there are **14** CMA record
types and that *"Education / BoardCert / InfoCode / NPI / File / Contact / Language have none — do not
flag their absence from CMA as missing parity."* The org has **19** record types, including
`PRM_Person_Education`, `PRM_Info_Code_Assignment`, `PRM_Healthcare_Provider_NPI`,
`PRM_Contact_Profile` and `PRM_Person_Language` — five of the seven the ledger says have none.

Either the ledger is scoped to Practitioner Creation and the extra types belong to other flows, or it
is stale. **Until that is settled, rule 9 may be instructing the Parity Auditor to suppress genuine
findings** — a false-negative source in a document the plan registers as critic ground truth. Raised
as Clarification Question 1 on the story. This is also a good early demonstration of why the House
Rule puts live metadata above every document.

**F2 — Two write paths are being designed for one object.**
`requirements/PAR_CaseManager_Association_CMA_Redesign_User_Stories.md` (1,252 lines, User Story 6)
creates `PRM_CaseManagerAssociation__c` rows from the **PAR** flow, while the new story creates them
from **Practitioner Creation** via a common service. If both ship independently the object gets two
dedup semantics and two category-routing maps. Raised as Clarification Question 7.

---

## 7. Recommendation

**Conditional go.** The strategy is sound and unusually well grounded — the plan's hardest technical
claims (trust budgets, verdict enums, iteration-cap defect, tool-allowlist gaps, the parity trap) all
survive independent verification, which is rare. The weaknesses are concentrated in three places:

1. **Two premises have gone stale** since authoring — the empty scaffold (M1) and the usable knowledge
   graph (B1). Both were true-ish assumptions rather than verified facts.
2. **Two integration contracts were described from documentation rather than from the schema** — the
   org registry shape (B2) and the alias identity (B3).
3. **One central claim was generalised from a sample** — that all ten verifiers are three-valued (M2).
   Five are.

None is fatal. All are cheap to fix now and expensive to discover during Phase 5.

**Proposed immediate sequence:** close D1b, correct §0 / §6.3 / §5.2 / §1 in the plan, then start
Phase 3.0 (graph) in parallel with Phase 1 (vendor and configure), since the graph build is wall-clock
work that blocks nothing else early.

---

## 8. Post-implementation addendum — 2026-09-09

Phase 3.0 was executed. **The verdict holds at conditional go**, but three of this audit's own findings
did not survive contact with the org, and the reason is worth recording: **this audit measured the
working tree, and the working tree is not the build.** `force-app/` is outside the git sparse-checkout
cone, so 127 committed files never materialize on disk. Anything inferred from `ls` was wrong.

| Finding | Status after implementation |
|---|---|
| **B1** — graph empty, downgrade to `guidance` | ⛔ **Superseded.** The graph cannot parse `.cls`/`.trigger`/`.xml` **at all**. Not a trust-class problem. Phase 3.0 re-scoped to `scripts/dependency-graph/sf_deps.py`; **D14 void**. |
| **B4** — pilot has no async context | ⛔ **Mostly void.** Epics A/C/E/F are committed with tests. The real gap is that they are **not deployed** to `ibx-qa`. The missing story file was the genuine blocker. |
| **M1** — Epic frontier | ⛔ **Reversed.** A and C are built, not "not built". The frontier needs **two axes** — authored vs deployed — which this audit did not model. |
| **B2, B3, B5, M2, M3, M4** | ✅ Stand. B3 further confirmed: six aliases resolve to the same org and `deploytarget` resolves to nothing. |
| **R10** | ✅ Stand, and **realised** — an authoritative-looking source silently returning nothing is exactly what happened. |

**New finding this audit could not have seen.** A `HVP_` family of 96 classes (2026-09-07) exists in the
org — a discarded spike, but it empirically settles **CL-15** (batch↔service mapping; `GroupRelatedBatch`
does not exist, and E16/E19 are cross-cutting) and **CL-13** (`HVP_ServiceException`). Both were logged as
open and blocking.

**Lesson for the next audit of this repo:** ground build-state claims in `git ls-tree HEAD` and
`sf_deps.py`, never in the filesystem. Full evidence: `docs/gamechanger/05_Org_Reconciliation.md`.
