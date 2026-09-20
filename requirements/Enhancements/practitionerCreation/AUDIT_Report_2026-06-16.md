# Practitioner Creation — Backend Framework Audit Report

**Date:** 2026-06-16
**Reviewer role:** Senior Principal Salesforce Architect (independent audit)
**Scope:** every file under `requirements/Enhancements/practitionerCreation/`
**Method:** each claim was ground-truthed against the actual repo metadata (Apex classes, objects, OmniStudio DataRaptor/IP exports). Findings are evidence-based, not stylistic.

> **Tooling note:** verification was done by direct repo grounding (Glob/Grep over `force-app/` + `vlocity_export/`), which is the authoritative source for an audit. The internal `falcon.devhub` MCP catalog and `agentexchange` agents are not reachable from this environment, so they were not used; nothing here depends on them.

---

## 0. Files audited

| # | File | Type | Maturity |
|---|------|------|----------|
| 1 | `PRM_IBC_HighVolume_TDD.md` | Parent TDD | High — minor drift |
| 2 | `Epic_A_Environment_Setup.md` | Declarative schema | High |
| 3 | `Epic_B_Foundation_Framework.md` | Apex scaffolding | High |
| 4 | `Epic_C_Async_Framework.md` | Async engine | High — 3 code bugs |
| 5 | `Epic_E_Practitioner_Services.md` (Part 1, E1–E8) | Domain services | Highest — well grounded |
| 6 | `prmAsyncJobProgress_Mockup.html` | UI reference | Good (mockup) |
| 7 | `PractitionerCreation_FileUpload_DesignPlan.md` | Roster ingestion | Now inconsistent with framework |

---

## 1. Cross-cutting findings (apply across the set)

### C-1 · Dangling document graph (Severity: HIGH — governance)
The Epics and TDD repeatedly cite parent/sibling docs as "source of truth" and as hard dependencies, but these files **do not exist anywhere in the repo**:

- `PRM_Implementation_Plan.md` — cited by the TDD §11 and every Epic as *"the source of truth"*.
- `PRM_Apex_Reference_Implementation.md` — cited by Epic B.
- `PRM_Service_JSON_Contracts.md` — cited by Epic B/E as the authority for OmniScript payload keys.
- `PRM_PractitionerCreation_Apex_Service_Flow.md` — cited by the TDD (CL-3, CL-10).
- `Epic_D_Selectors.md`, `Epic_F_Orchestration.md`, `Epic_E_Practitioner_Services_Part2.md` — referenced as build dependencies (E2/E6/E7 consume EPIC D selectors; E1 blocks EPIC F; E8 facility-grain method "detailed in Part 2").

**Impact:** Epic E cannot be built as written — it depends on EPIC D selectors and a JSON-contracts doc that aren't here, and half of EPIC E (E9–E17, including the async `PRM_Level4RecordCreationService` that EPIC C's seed config points at) lives in a missing Part 2. The "source of truth" plan being absent means the §11 effort numbers can't be reconciled.
**Action:** either commit these docs to the repo or change the citations to wherever they actually live (Quip/Confluence). Until then, treat D, F, and E-Part-2 as **not yet authored**, not merely "out of scope."

### C-2 · "Existing asset" claims unverified in the repo (Severity: MEDIUM)
The TDD reduces effort and de-risks EPIC D on the basis that selectors and batch patterns already exist (CL-8, G-4, Epic C C6). In the repo I can only confirm **`PRM_AddressSelector`**. Not present: `PractitionerDetailsSelector`, `PRM_UpdateDirectorySelector`, `PRM_NCPDP_Selector`, `PRM_DeleteExceptionLogBatch`, and the `NetworkMember`/`NetworkMemberChunk` objects (CL-6/G-5 lean heavily on these).
**Most likely cause:** this repo is a *partial* SFDX retrieval. But "grounded to in-source metadata" is then overstated for these specific items.
**Action:** run a targeted `sf project retrieve` (or `sf data query` against the org) to confirm each before sign-off. If any are genuinely absent, EPIC D effort (currently reduced to 3.0 d on the reuse assumption) and Epic C's C6 "mirror the existing batch" claim must be re-baselined.

### C-3 · TDD ↔ Epic decision drift (Severity: MEDIUM)
The child Epics ratified several decisions that the parent TDD still contradicts. The Epics carry "reconcile parent docs later" notes, but the drift is real and will mislead a builder who reads the TDD first:

| Topic | TDD says | Epics ratified |
|---|---|---|
| Retry | §6.3/§8: **auto-retry** + retries-exhausted → DLQ; "sweeper re-enqueues stuck Running jobs" | Epic C: **manual-only, uncapped**, no sweeper, no auto-retry |
| Back-pressure | §6.3: check Flex Queue depth (cap 100) before enqueue | Epic C `invokeJob`: **not implemented** |
| Per-chunk savepoint / circuit breaker | §6.3/§8 promise both | Epic C: neither built (circuit breaker = manual disable) |
| Object names | `Async_Job__c` (unprefixed) in §11.4 | `PRM_AsyncJob__c` (Epic A "wins") |
| Orchestrator entry | `execute(Map)` | Epic B: `run(Map)` |

**Action:** the TDD is the doc most likely to be read by reviewers/architects; update §6.3, §8, and §11.4 to match the ratified Epic decisions, or explicitly mark them "superseded by Epic C/A/B."

### C-4 · Effort numbers don't tie out (Severity: LOW)
- TDD §11.7 EPIC C = **12.5 d**; Epic C doc total = **12.0 d** (C1 is 1.5 in the TDD, 1.0 in Epic C).
- TDD §11.6 EPIC E = **24.0 d**; Epic E says grand total (Part 1 + Part 2) ≈ **22.5 d**.
- Epic E: E2 header *"2.0 d"* but the E.Effort table lists **2.5**.
**Action:** pick one source of truth for estimates (the missing `PRM_Implementation_Plan.md`?) and regenerate the rollups.

### C-5 · FileUpload plan is now architecturally stale (Severity: HIGH for that file)
See file-7 audit. In short: it targets the **legacy IP** that this whole framework is built to **replace**.

---

## 2. File 1 — `PRM_IBC_HighVolume_TDD.md`

**Verdict:** Strong, honest, well-structured parent TDD. The problem framing (P1–P5), layered HLD, and the Clarification Log are exactly what a principal review wants to see — open items are tracked with owners rather than hidden.

**What it gets right (verified):**
- The pilot decomposition is accurate: `PRM_PractitionerCreationContainer` v6 → 3 sub-IPs (`PRM_PractitionerCreation` v3, `PRM_DelegatedPractitionerCreation` v7, `PRM_AddressLogicContainer`). All three IPs and the version numbers exist in `omniIntegrationProcedures/`.
- CDM contention (G-6) is real: `PRMDRCreateCDMForPractitioner` + `PRMDRPCDMCaseManagerLink` do run in both creation sub-IPs — the single `PRM_CaseDataManagerService.commit()` is the correct fix.
- Reuse of `PRM_FailedRecordStaging__c` as DLQ and `PRM_ExceptionLogger` for logging is grounded — both exist with the cited fields/signature.
- CL-1 "build new, don't reuse `PRM_AsyncProcess__c`" — `PRM_AsyncProcess__c` does exist, so the divergence is a real, defensible decision.

**Findings:**
- **T1-HIGH (doc graph):** §1/§5 cite `PRM_Implementation_Plan.md` as source of truth and `PRM_PractitionerCreation_Apex_Service_Flow.md` for DML counts — both missing (C-1).
- **T2-MEDIUM (drift):** §6.3 and §8 still describe auto-retry, per-chunk savepoint, back-pressure guard, and a stuck-job sweeper. None are in Epic C (manual/uncapped, no sweeper). The reader is left believing in resiliency features that won't ship in v1 (C-3).
- **T3-MEDIUM (unverified):** CL-6/G-5 make `NetworkMember`/`NetworkMemberChunk` a gating decision for the whole async sizing model, but those objects aren't in the repo to inspect (C-2). This is the single biggest open architectural question (is the "high volume" really HCFN, or network-membership chunking?) and it's still unresolved — it should block EPIC C/E start, as the doc says.
- **T4-LOW:** effort drift (C-4); `Async_Job__c` vs `PRM_AsyncJob__c` naming inconsistency within §11.4.
- **T5-LOW (idempotency):** §6.3 claims idempotency "via External-Id upserts + status guards," but none of the new async objects define an External Id field (Epic A), and the domain services (Epic E) mostly do blind `insert`. Idempotency on re-run is therefore **not actually guaranteed** today. Either add External-Id keys or downgrade the guarantee to "status-guard only (a Completed child is not reprocessed)."

**Recommendation:** keep the TDD as the conceptual anchor but add a one-line "ratified decisions supersede §6.3/§8 where they differ — see Epic A/C" banner, resolve CL-6 against the org, and reconcile the effort table.

---

## 3. File 2 — `Epic_A_Environment_Setup.md`

**Verdict:** Clean, buildable, declarative-only. The naming-convention rationale (PRM_-prefixed, PascalCase, no inter-word underscores, grounded to existing `PRM_RetryCount__c`/`PRM_RequestPayload__c`) is sound and the right call.

**What it gets right (verified):**
- `PRM_AsyncJob__c`/`PRM_AsyncJobDetails__c`/`PRM_AsyncJobConfig__mdt` are genuinely new (not in repo).
- `PRM_FailedRecordStaging__c` reuse (A4) is correct — every field listed exists, and adding a single `PRM_AsyncJobDetails__c` lookup is a minimal, safe change.
- "Case Manager = IndividualApplication" is grounded (`PRM_CaseDataManager__c.PRM_CaseManager__c` and `PRM_FailedRecordStaging__c.PRM_CaseManager__c` are both Lookup→IndividualApplication).
- ContentVersion-as-payload (no `PRM_InputJson__c`/`PRM_Response__c`) correctly sidesteps the Long Text 131,072-char ceiling (TDD R4).

**Findings:**
- **A1-MEDIUM (config drift risk):** `PRM_AsyncJobConfig__mdt.PRM_ProcessName__c` and both objects' `PRM_ProcessName__c` are independent **Picklists**. Three picklists that must stay value-synchronised will drift. Use a **Global Value Set** shared by all three (and by the CMDT) so `Practitioner Creation`/`PAR` are defined once.
- **A2-MEDIUM (retention is now code, not config):** A7 moved `PRM_MaxRetries__c`/`PRM_Active__c`/`PRM_RetentionDays__c` out of the CMDT into Apex constants. That contradicts the "metadata-driven" selling point and means changing retention or disabling a process is a **redeploy**, not a config edit. For `PRM_Active__c` especially (the manual circuit-breaker / "halt a ProcessName"), keeping it on the CMDT is worth it — a per-process kill-switch you can flip in Setup during an incident is valuable. Recommend restoring at least `PRM_Active__c` to the CMDT.
- **A3-LOW (permission set):** A5 ships only a partial XML sample ("repeat for…"). Also note `permissionsets/` is empty today, so this introduces the folder — make sure the deploy order includes the perm set *after* the objects (it does, A6).
- **A4-LOW (Master-Detail consequence):** child is Master-Detail to the parent with `reparent=false`; good for cascade-delete cleanup, but it also means a child **cannot exist before** the parent and the parent **cannot be deleted** while you want to keep child history. Fine for this design (cleanup deletes both), just call it out so no one later expects to retain details after purging jobs.
- **A5-LOW (reconciliation):** the doc itself flags that the parent TDD still uses `Async_Job__c` — good awareness, but the reconciliation is a tracked debt, not done.

**Recommendation:** adopt a Global Value Set for `ProcessName`; keep `PRM_Active__c` on the CMDT; otherwise this Epic is ready to build.

---

## 4. File 3 — `Epic_B_Foundation_Framework.md`

**Verdict:** Appropriately minimal. Dropping the over-engineered `FlowContext`/`PRM_PayloadValidator`/`PRM_RecordTypes`/`PRM_ValidationException` from B and flowing state through the `params` map is a good simplification.

**Findings:**
- **B1-MEDIUM (homeless dependencies, CL-13):** B removed `PRM_ExceptionLogger`, `PRM_ValidationException`, `PRM_PayloadValidator`, `PRM_RecordTypes` but C/E/F still consume them. Good news the audit can add: **`PRM_ExceptionLogger` already exists** in the org and its `logExceptionReturnId(...)` 12-arg signature matches Epic C exactly — so that one is "reuse existing," resolved. The still-open ones are the **RecordType cache helper** (needed by E1/E2/E3/E5 to replace `QUERY(...RecordType...)`) and the validation exception type. Decide the RecordType helper's home **before E1** — it's on the critical path for 5 services.
- **B2-LOW (naming convention):** `NameNormalize(String)` uses PascalCase; Apex method convention is camelCase (`nameNormalize`). `toSObjectList` is correct. Minor, but this is a brand-new shared utility that every service calls — get the casing right before it proliferates.
- **B3-MEDIUM (under-specified core helper):** `toSObjectList(List<Object>, SObjectType)` is the replacement for `PRM_OmniUtils.convertToListSobjects` and its body is a stub. Generic map→SObject reshaping is exactly where type coercion bites (date/datetime strings, numeric vs text, polymorphic FKs). This "1.0 d" task carries more risk than the estimate implies; specify the coercion rules and test them against a real DR payload, or just delegate to the proven `PRM_OmniUtils` method instead of reimplementing.
- **B4-LOW (contract drift):** B3 defines the orchestrator entry as `run(Map)`, TDD says `execute(Map)` (C-3).

**Recommendation:** confirm `PRM_ExceptionLogger` reuse (done — it exists), pin the RecordType-helper home, fix method casing, and de-risk `toSObjectList`.

---

## 5. File 4 — `Epic_C_Async_Framework.md`

**Verdict:** The most detailed Epic and the closest to implementation-ready. The trigger→handler→orchestrator→executor→chain flow is correct, the diagrams are good, and the code is largely sound. The grounding is real: the one-liner trigger + `FeatureManagement.checkPermission('PRM_TriggerBypassPermission')` pattern matches the existing `PRM_AccountAccountRelationTrigger`, and the `PRM_ExceptionLogger.logExceptionReturnId(...)` call matches the real signature. **But there are three concrete code defects in the pseudocode that will ship as bugs if copied verbatim.**

**Code defects (Severity: HIGH — correctness):**

- **C-BUG-1 · `findNextJob` mis-marks a job "Completed" when a child Failed.**
  `findNextJob` selects the next `Queued` child; if none remain it rolls the parent up to `Completed` and fires a "Completed" notification. But a child in `Failed` state is also not `Queued`, so a job with one failed child and no queued children is reported as **Completed/success**. Fix: when no `Queued` children remain, check for any `Failed` child → set parent `Failed` and notify `Failed`; only `Completed` if all children are `Completed`.

- **C-BUG-2 · Soft failures (`success=false`) never notify and feed C-BUG-1.**
  In `PRM_AsyncQueueable.execute`, when the service returns `success=false` (no thrown exception), the code does `statusUpdate('Failed')` + `logFailure()` + `findNextJob()` but **does not** call `notifyOnFinish('Failed')`. Only the `catch` block notifies. Combined with C-BUG-1, a soft-failed child chains forward and the job can still end up "Completed." Fix: treat soft-fail and hard-fail identically for notification/terminal-state purposes.

- **C-BUG-3 · `LAST_N_DAYS:RETENTION_DAYS` will not compile.**
  C6 `start()` uses `WHERE CreatedDate < LAST_N_DAYS:RETENTION_DAYS`. The `LAST_N_DAYS:n` date literal requires an **integer literal**, not a bound variable/constant — you cannot interpolate the `RETENTION_DAYS` Apex constant there. Fix: `Date cutoff = Date.today().addDays(-RETENTION_DAYS);` then `WHERE CreatedDate < :cutoff`.

**Design findings:**
- **C-1-MEDIUM (promised but absent):** TDD §6.3 promised a Flex-Queue depth/back-pressure check before enqueue. `invokeJob` has none — at peak it will happily exceed the 100 flex-queue cap and throw. Either implement the guard (check `[SELECT count() FROM AsyncApexJob WHERE JobType='Queueable' AND Status IN ('Queued','Processing')]` / `Holding`) or remove the promise from the TDD.
- **C-2-MEDIUM (`retry` enqueue limits):** `retry(List<Id>)` loops `invokeJob` per failed child. From the LWC controller (synchronous) you can enqueue up to 50 Queueables, fine — but for `Mode='Batch'` children it loops `Database.executeBatch`, and only **5** batch jobs can be active/queued at once. Bulk-retrying many failed Batch children will hit `LimitException`. Cap the per-call batch dispatch or queue them.
- **C-3-MEDIUM (batch-from-trigger):** the doc correctly flags (C9) that `Database.executeBatch` from the after-insert trigger context needs a one-shot Queueable hop, but the C2/C3 pseudocode calls `invokeJob` (which can `executeBatch`) directly from `onJobInserted`. Make the deferral explicit in the code, not just the open-items table.
- **C-4-LOW (staging field):** snippet writes `PRM_FailedRecordStaging__c.PRM_ProcessName__c`, which doesn't exist (only `PRM_SourceFlow__c` does). Self-caught in C9 — just apply it.
- **C-5-LOW (notification target):** `setTargetId(IndividualApplication.Id)` — confirm a Custom Notification can target a custom/standard record the recipient can open; otherwise target the `PRM_AsyncJob__c` record.
- **C-6-LOW (LWC schema caveat):** the mockup columns Queue Position / ETA / Scheduled / Duration / Records aren't in schema; correctly excluded from T1/T2. Keep them out of v1 to avoid scope creep.

**Recommendation:** fix the three code defects before any build ticket is cut from this doc; decide back-pressure (implement vs drop from TDD); add the batch-retry cap.

---

## 6. File 5 — `Epic_E_Practitioner_Services.md` (Part 1, E1–E8)

**Verdict:** The strongest document in the set. The "grounding" claim is **true** — I verified every legacy DataRaptor it cites (`PRMDRCreateCaseCaseManagerAndAccount`, `PRMDRPHCPHCPTaxonomyAndBusineessLicense`, `PRMDRPHCPNPIBoardCretIdentifier`, `PRMPostGroupPractitionerCreation`, `PRMDRPracCreateHCFacilityNetworkRecordNewGroup`) exists in `omniDataTransforms/` + `vlocity_export/`, and the IP versions (IBC v3, Delegated v7) are real. The field maps, formula→Apex translations, DML ordering, and the circular-FK back-link sequence in E1 are careful and correct. The Clarification Log (E.CL) is excellent.

**Findings:**
- **E-1-HIGH (missing return Id breaks the chain):** E2, E5, E6, E7 all require `params.practitionerId` (= the **PersonContact Id**) sourced from E1. But E1's documented response returns only `practitionerAccountId`, `caseId`, `caseManagerId` — **not** `practitionerId`. For a Person Account the PersonContactId is only knowable after the Account insert (re-query `Account.PersonContactId`). E1 must explicitly query and return it, or every downstream service breaks. Add `practitionerId` to E1's response contract.
- **E-2-MEDIUM (IBC NPI/Identifier gap, CL-E1):** correctly flagged — the active IBC IP creates HCP/Taxonomy but has **no** DR for HealthcareProviderNpi/Identifier, yet E2 will create them for both branches. This is a behavioural change vs legacy IBC (new records that legacy didn't create). Confirm with business that IBC practitioners *should* now get NPI/Identifier rows — this isn't just a field-value question, it's a data-footprint change.
- **E-3-MEDIUM (dependency on missing EPIC D):** E2/E6 reads (`PRM_TaxonomySelector.getTaxonomyRefs`, FK resolution) route through EPIC D selectors that aren't authored/committed (C-1). E1–E8 are blocked on D.
- **E-4-LOW (effort inconsistency):** E2 header says 2.0 d; the E.Effort table says 2.5 (C-4).
- **E-5-LOW (Person Account dependency):** the field maps assume Person Accounts (`PersonEmail`, `PersonBirthdate`, `PersonGenderIdentity`, `HealthCloudGA__Gender__pc`). That's correct for this Health Cloud org, but state it as a prerequisite so the services aren't unit-tested in a non-Person-Account scratch org.
- **E-6-LOW (Part 2 absent):** E8's `prepareBulkForLocations` and the async `PRM_Level4RecordCreationService` (which EPIC C's seed config `PRM_ServiceClassName__c` points at) are deferred to a Part 2 that doesn't exist. EPIC C's pilot config therefore points at a class with **no design doc** yet.

**Recommendation:** add `practitionerId` to E1's output contract (blocking); get business sign-off on the IBC NPI/Identifier footprint change; author/commit EPIC D and Epic E Part 2 before scheduling E-build.

---

## 7. File 6 — `prmAsyncJobProgress_Mockup.html`

**Verdict:** A faithful, well-crafted SLDS-styled static mockup — good for stakeholder alignment and as a build reference. The Epic C C5.1 mapping from mockup elements to `lightning-*` base components is the right way to consume it.

**Findings:**
- **M-1-MEDIUM (scope creep risk):** the mockup shows Queue Position, Estimated/Scheduled Execution, Duration, and Records columns that **don't exist** in the Epic A schema. Epic C correctly excludes them from v1, but the polished mockup will set stakeholder expectations that those columns ship. Add a visible "v2 / not in scope" treatment in the mockup, or remove them, to avoid a "where's the ETA column?" conversation at UAT.
- **M-2-LOW (accessibility — for the real LWC):** status is conveyed by color + badge. Ensure the production LWC pairs color with text/icon (it does in C5 T7) and meets WCAG contrast; don't rely on the hand-rolled hex palette — inherit SLDS theme classes so contrast/focus states come for free.
- **M-3-LOW:** it's inline-styled standalone HTML — correct for a mockup; just make sure no one mistakes it for a deployable asset (it lives in a requirements folder, so fine).

**Recommendation:** annotate the out-of-scope columns; otherwise good to hand to the LWC builder alongside C5.

---

## 8. File 7 — `PractitionerCreation_FileUpload_DesignPlan.md`

**Verdict:** This file (rewritten in the prior session) is internally solid for **roster/vendor-file ingestion**, but it is now **architecturally out of step with the framework the team is building**, because the framework's premise changed.

**The core conflict (Severity: HIGH):**
- The FileUpload plan's backend strategy is *"reuse the existing IP `PRM_PractitionerCreationContainer` via `IntegrationProcedureService.runIntegrationService`, looped per row."*
- The entire TDD + Epics A–F exist precisely to **replace that IP** with layered Apex services (EPIC E) behind a new orchestrator (EPIC F) and a metadata-driven async engine (EPIC C). The IP is on the deprecation path ("deprecate legacy IPs/sub-IPs after stable").
- So the FileUpload plan would build a new consumer **on top of the component being retired**, and it would loop a synchronous IP per row — exactly the governor-limit / non-transactional failure mode (P1/P2) the framework is designed to eliminate.

**Reconciliation (recommended target state):**
- Roster ingestion should be re-cast as a **producer for the new async framework**: the LWC parses/normalizes vendor files → builds the canonical envelope → writes it as the `ContentVersion` payload on a `PRM_AsyncJob__c` with `ProcessName='Practitioner Creation'`. The Epic C engine then fans out and the EPIC E services do the record creation — one row = one async work unit, retryable and observable via `prmAsyncJobProgress`. This is a near-perfect fit: bulk rosters are the canonical "high volume" case the async engine was built for.
- Net: delete the "loop the IP per row" backend section; point the plan's backend at "enqueue to the EPIC C async framework via the EPIC F orchestrator." Keep the front-end (format adapters, canonical schema, triage grid) — that part is still correct and complementary.
- Also reconcile the **canonical intake schema** in the FileUpload plan with the `jsonInput` contracts now spelled out in Epic E (E1 `caseManagerInfo`/`practitionerInfo`, E2 `taxonomies`/`identifiers`, E5 `businessLicenses`, etc.) and the missing `PRM_Service_JSON_Contracts.md`. There must be **one** payload contract, not two.

**Other findings:** the SheetJS CVE/CDN-pinning and PapaParse-for-CSV decisions remain valid and are independent of the backend change.

**Recommendation:** revise the backend section of this plan to consume the EPIC C/F framework, and make its canonical schema reference (not duplicate) the Epic E `jsonInput` contracts.

---

## 9. Prioritized action list

| Priority | Action | Files | Severity |
|---|---|---|---|
| P0 | Commit/locate the missing source docs (`PRM_Implementation_Plan`, `PRM_Service_JSON_Contracts`, `Epic_D`, `Epic_F`, `Epic_E_Part2`) or fix the citations | TDD, B, C, E | HIGH |
| P0 | Re-point the FileUpload roster plan at the async framework, not the legacy IP; unify the payload contract | File 7, E | HIGH |
| P0 | Resolve CL-6 (`NetworkMember(Chunk)` vs HCFN) against the org — it gates async sizing/mode | TDD, C, A | HIGH |
| P1 | Fix Epic C code defects: `findNextJob` failed-child roll-up, soft-fail notification, `LAST_N_DAYS` literal | C | HIGH |
| P1 | Add `practitionerId` (PersonContactId) to E1's response contract | E | HIGH |
| P1 | Verify "existing" selectors/batch/objects against the org (only `PRM_AddressSelector` confirmed in repo) | TDD, C, D | MEDIUM |
| P2 | Reconcile TDD §6.3/§8 (auto-retry/sweeper/back-pressure) with the manual-only Epic C decisions | TDD, C | MEDIUM |
| P2 | Decide RecordType-cache helper home before E1; confirm `PRM_ExceptionLogger` reuse (exists) | B, E | MEDIUM |
| P2 | Use a Global Value Set for `ProcessName`; keep `PRM_Active__c` on the CMDT kill-switch | A | MEDIUM |
| P3 | Tie out effort numbers; fix `NameNormalize` casing; annotate out-of-scope mockup columns | TDD, B, mockup | LOW |

---

*End of report.*

