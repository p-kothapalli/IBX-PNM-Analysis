# Org Reconciliation — measured state vs. the documents

**Date:** 2026-09-09
**Org:** `ibx-qa` (`prashanth.kothapalli@ibx.com.pie.qa`)
**Method:** Tooling API queries via `scripts/dependency-graph/sf_deps.py` plus `git ls-tree` against `HEAD`.
**Why:** Phase 3.0 of `02_IBC_Integration_Plan.md` assumed a knowledge graph that cannot exist for Apex.
Replacing it surfaced material contradictions between the documents and both the repo and the org.

> **House Rule applied.** Where a document and the org disagree, the org wins. Everything below is measured,
> not inferred; the query used is named so any claim can be re-checked.

---

## 1. `code-review-graph` cannot see Salesforce code

`code_review_graph.parser.EXTENSION_TO_LANGUAGE` covers 30 languages. Apex and Salesforce metadata are not
among them:

| Extension | Supported? |
|---|---|
| `.cls`, `.trigger` | **No** |
| `.xml` (objects, fields, OmniStudio, FlexiPages, permission sets) | **No** |
| `.js`, `.ts`, `.java`, `.py`, … | Yes (30 languages) |

A `full_rebuild` over this repo parsed **2 files** (the root JS configs) producing 2 nodes, 0 edges and 0
embeddings, while 7 `.cls` files sat materialized on disk and were skipped.

**Consequences.**

| Affected | Correction |
|---|---|
| Plan **Phase 3.0** ("build and prove the knowledge graph") | **Infeasible as written.** Replaced by the Tooling API resolver in §2. |
| Plan decision **D14** ("promote the graph to `authoritative` on measured recall") | Unsatisfiable for Apex. Void. |
| Audit blocker **B1** ("graph is empty → downgrade to `guidance`") | Too generous. It is not merely empty, it is structurally incapable for this estate at any trust class. |
| `.cursorrules` and `.cursor/rules/code-review-graph-first.mdc` | Both mandate graph-first exploration and call Grep-before-`semantic_search_nodes` a "hard violation". On a repo that is ~99% Apex and XML this cannot be complied with. The note in that rule about the 2026-04-16 session using Grep throughout describes a necessity, not a lapse. |

---

## 2. Replacement: `scripts/dependency-graph/sf_deps.py`

The Tooling API object `MetadataComponentDependency` is the org's own dependency index. It covers ApexClass,
ApexTrigger, ApexPage, LWC, Aura, Flow, FlexiPage, Layout, CustomObject, CustomField, ValidationRule,
QuickAction, **OmniScript** and **OmniIntegrationProcedure** — i.e. exactly the estate the graph cannot parse —
and it is authoritative because it comes from the org (top rung of the Verification Ladder).

```
./sf_deps.py callers PRM_CMAService     # -> PRM_CMAServiceTest, PRM_ParFormCmaBatch
./sf_deps.py callees PRM_CMAService     # -> PRM_ServiceBase, PRM_FormSubUtility, PRM_CaseManagerAssociation, ...
./sf_deps.py tests   PRM_CMAService     # -> PRM_CMAServiceTest
./sf_deps.py impact  PRM_ServiceBase -d 3
./sf_deps.py survey  --prefix HVP_
```

### The completeness trap (why this queries per component)

`MetadataComponentDependency` **misreports completeness**. Measured 2026-09-09:

| Query | Rows | Distinct source classes |
|---|---|---|
| no filter | 1,933 | **zero Apex** (all Layout) |
| `MetadataComponentType='ApexClass'` | 1,213 | **72** |
| `… AND RefMetadataComponentType='ApexClass'` | 1,686 | **624** |

The broad query returned fewer rows and far fewer sources than the narrower one, while reporting
`done: true` with a matching `totalSize`. A first version of this tool bulk-exported 6,365 edges and was
**discarded**: `PRM_CMAService` had zero rows in that export despite a targeted query returning its edges
correctly.

Queries filtered to a specific component Id are accurate, so every lookup resolves a name to an Id and asks a
bounded question. Also note the `*Name` fields are **not filterable** in SOQL, and `COUNT()` is unsupported.

**Residual limit:** edges are deploy-time metadata references, not runtime call paths. Dynamic dispatch —
`Type.forName` resolution of batch classes from `PRM_AsyncJobConfig__mdt` — is invisible here and must be read
from the Custom Metadata rows instead.

Queries archived in `requirements/SOQL/2026-09-09_MetadataComponentDependency.md`.

---

## 3. The real Epic frontier is two-axis

The documents track one axis ("built" / "not built"). The actual state needs two, because **committed in git
is not the same as present in the org**, and they disagree for most of the build.

`force-app/` is **outside this repo's git sparse-checkout cone** (`git sparse-checkout list` returns
`.cursor/rules`, `.cursor/skills`, `.vscode`, `docs/build-verification`, `docs/implementation-plan`,
`pages/gamechanger`). 127 of the 134 committed files under `force-app/` are flagged `skip-worktree` and never
materialize. Nothing is lost — `PRM_AsyncOrchestrator.cls` is 251 lines in `HEAD` — but any measurement taken
from the working tree is wrong. The 28,248 files physically present under `force-app/` are **untracked**: a
separate org retrieve, i.e. the legacy estate (714 Apex classes, 196 LWCs, 914 object dirs, 4,091 OmniStudio
files), which is the parity source, not the build.

| Component | In git `HEAD` | In org `ibx-qa` |
|---|---|---|
| `PRM_ServiceBase`, `PRM_FormSubUtility`, `PRM_Constants` (Epic B) | ✅ | ✅ |
| `PRM_CMAService` (E19) | ✅ | ✅ |
| `PRM_ExceptionLogger` | ✗ (pre-existing org class) | ✅ |
| `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c`, `PRM_AsyncJobConfig__mdt`, `PRM_AsyncJobSetting__mdt` (Epic A) | ✅ | **✗** |
| `PRM_AsyncOrchestrator`, `PRM_AsyncJobCleanupBatch`, `PRM_AsyncJobProgressController` (Epic C) | ✅ | **✗** |
| `PRM_PractitionerBatch` + E1/E2/E5/E6/E7/E10/E11/E16 services (Epic E) | ✅ | **✗** |
| `PRM_JsonJobUploadService`, `PRM_JsonJobUploadController` (Epic F intake) | ✅ | **✗** |
| `PRM_ServiceException` | ✗ | ✗ |

**Reading:** Epic B and E19 are deployed. Epics A, C, E and F are **written, tested and committed but never
deployed** to this org. The only async object in the org under the `PRM_` prefix is the legacy
`PRM_AsyncProcess__c` (roster-sync, explicitly out of scope).

### Corrections this forces

- **Audit finding M1** claimed Epics A and C were "not built". Wrong — they are committed. The error came from
  measuring the working tree, where the sparse cone hides them.
- **Audit blocker B4** claimed the pilot had "no E16 and no Epic A context". Void — `PRM_CaseDataManagerService`
  is committed, as is the full Epic A schema. (The *story file* was genuinely missing; that part stood.)
- The **E16 → E19 pilot switch still holds**, because it rested on CL‑E2‑12 being open, which is independent of
  build state.
- **Plan §0** ("the PRM Modernization build has barely started") is right about deployment and wrong about
  authorship. Most of Epics A–F exists in source.

---

## 4. The `HVP_` spike — status and what it settles

The org contains **96 `HVP_` Apex classes (52 implementation + 44 tests)** created **2026-09-07**, against
`PRM_` classes created 2026-09-01 and last modified 2026-09-04. `HVP_` is a **spike / experiment and is to be
discarded** — `PRM_` remains the intended direction (decision recorded 2026-09-09).

**It is retained here as evidence, not as a target.** A spike's value is that it resolves design questions
empirically, and this one resolves two the documents call open and blocking.

Also present and beyond anything in the plan: `HVP_AsyncBatchBase`, `HVP_IAsyncBatch`,
`HVP_AsyncJobKickoffQueueable`, `HVP_AsyncTelemetry`, an 18-class CSV intake subsystem,
`HVP_AttributeValidationEngine`, and objects `HVP_AsyncJob__c` / `HVP_AsyncJobDetails__c` /
`HVP_AsyncJobRecords__c` / `HVP_AsyncJobConfig__mdt` / `HVP_AsyncJobSetting__mdt` /
`HVP_CSVColumnMapping__c` / `HVP_FieldValidationRule__mdt` / `HVP_SpecialtyAlias__mdt`.

### CL-15 — batch ↔ service mapping · **evidence available, recommend closing**

Measured with `sf_deps.py callees` on each batch class:

| Batch | Services it calls |
|---|---|
| `HVP_PractitionerBatch` | Practitioner (E2), License (E5), Education (E6), BoardCertification (E7), InfoCode (E8), Contact (E10), Language (E11), **HPF (E14)**, CaseDataManager (E16), **CMA (E19)** |
| `HVP_PracticeLocationAndGroupBatch` | Group (E3), HealthcareFacilityCreation (E13), CaseDataManager (E16), **CMA (E19)** |
| `HVP_PLRelatedBatch` | **InfoCode (E8)**, HPF (E14), ProviderFeature (E15), CaseDataManager (E16), **CMA (E19)** |
| `HVP_Level4Batch` | Level4RecordCreation (E18) |

Every batch also depends on `HVP_AsyncBatchBase`, `HVP_AsyncOrchestrator`, `HVP_AsyncTelemetry` and
`HVP_Constants`. `HVP_PLRelatedBatch` additionally reuses the legacy `PRM_CommonServiceHelper`,
`PRM_GlobalConstant` and `PRM_Utility` — corroborating **CL-8** ("reuse, don't rebuild").

**Where this contradicts the provisional mapping in `CLAUDE.md` §4.2:**

1. **E16 CaseDataManager and E19 CMA are cross-cutting** — called by *every* batch, not just `PractitionerBatch`.
   The provisional mapping placed E16 in step 1 only and omitted E19 entirely. This is the most consequential
   delta: two services are shared infrastructure, not step-local.
2. **`GroupRelatedBatch` was eliminated.** The plan lists it as step 3 with services "TBD"; the spike folds that
   work into `HVP_PracticeLocationAndGroupBatch` + `HVP_GroupService`. Only **four** batches exist.
3. **E14 HPF and E8 InfoCode each span two batches**, where the plan assigned each to one.
4. **No separate E9 File, E12 NPI or E17 FacilityNetwork service** exists in the spike.

> Because `GroupRelatedBatch` disappears and E16/E19 become cross-cutting, the seeded
> `PRM_AsyncJobConfig__mdt` sequence (five rows, `GroupRelatedBatch` at 3) needs revisiting whichever
> mapping is adopted.

### CL-13 — home of the removed Foundation helpers · **evidence available, recommend closing**

`HVP_ServiceException` exists as a standalone class, depended on by `HVP_ServiceBase`. The spike's answer is a
dedicated exception class beside the service base, with error logging delegated to the pre-existing
`PRM_ExceptionLogger` (which is in the org and has **164 callers**, strongly corroborating **CL-5**'s
"reuse the existing logger, don't build a new one"). No `PRM_ServiceException` exists yet on the `PRM_` side.

### CL-6 — async target scope · still open, but narrowable

`HVP_Level4Batch` calls exactly one service (`HVP_Level4RecordCreationService`), and no `NetworkMember`-related
class appears anywhere in the `HVP_` family. This is consistent with Epic A's A7 resolution
(`HealthcareFacilityNetwork` only; `NetworkMember` belongs to roster-sync and is out of scope) but does not by
itself close the item.

---

## 5. Other measured corrections

- **`docs/reference/` does not exist** (audit B5) — confirmed still absent. Parity ground truth is the two
  ledgers only.
- **Alias collision (audit B3 / decision D12)** — confirmed. Six aliases resolve to the same QA org
  (`ibx-qa`, `IBXQA`, `myOrg`, `qa-sandbox`, `salesforce-y4nsdz`, `salesforce-7y19gr`), and the framework's
  hardcoded **`deploytarget` resolves to nothing**. Fix is one command:
  `sf alias set deploytarget=prashanth.kothapalli@ibx.com.pie.qa`.
- **`sf` CLI is off a sandboxed `PATH`** (`/usr/local/bin/sf`) and cannot write `~/.sf/*.log` under sandbox;
  export `SF_DISABLE_LOG_FILE=true`. Handled inside `sf_deps.py`.
- **Uncommitted drift on 7 files** — the on-disk copies of `PRM_CMAService`, `PRM_Constants`,
  `PRM_FormSubUtility` and their tests differ from `HEAD` (+142/−23). This is **work in progress, not a
  clobber**: `PRM_Constants` gains CMA record types and lookups for the PracticeLocation/PLRelated batches, and
  `PRM_FormSubUtility` gains `computeHcfExternalId`. The only regression is cosmetic — `PRM_CMAService` lost its
  `@StoryNumber: E19` tag, an `F-11` reference and its trailing newline. Left untouched.
- **E19 story, Clarification Question 7 — answerable.** `sf_deps.py callers PRM_CMAService` returns
  `PRM_ParFormCmaBatch`, proving the PAR flow **already** calls `PRM_CMAService`. A shared write path onto
  `PRM_CaseManagerAssociation__c` exists in the org today, so the question is not whether to share a service but
  whether the existing sharing is correct.

---

## 6. Recommended follow-ups

| # | Action | Rationale |
|---|---|---|
| 1 | Replace plan Phase 3.0 with "adopt `sf_deps.py` as the structural grounding source, registered `authoritative`" | The graph cannot do this; the org can |
| 2 | Void decision D14; rewrite audit B1 | Both assume a graph that can parse Apex |
| 3 | Rewrite `.cursorrules` + `code-review-graph-first.mdc` to mandate `sf_deps.py` for Apex/metadata and keep graph-first only for JS/TS | The current rules mandate an impossible workflow |
| 4 | Model the frontier on two axes (committed / deployed) in `CLAUDE.md` §7 | One axis produced two wrong audit findings |
| 5 | Close CL-15 and CL-13 using §4, and re-seed `PRM_AsyncJobConfig__mdt` for four batches | Evidence now exists; `GroupRelatedBatch` should not be seeded |
| 6 | Decide whether E16/E19 become explicit shared services in the `PRM_` design | The spike found them cross-cutting; the plan does not model that |
| 7 | Bind the `deploytarget` alias before Phase 1 | Framework write-guard currently points at nothing |
