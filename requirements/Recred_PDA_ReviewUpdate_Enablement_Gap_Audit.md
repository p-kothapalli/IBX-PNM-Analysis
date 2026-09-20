# ReCred PDA Review & Update — Enablement Gap Audit

**Date:** 2026-08-18
**Scope:** What is still **pending / broken** before the business can turn the **ReCred PDA Review and Update** lane back on (the `Recred Updates` stage worked by a Provider Data Admin after committee approval, through `Network Management QC` to `Complete`).
**Method:** Requirements in `requirements/` reconciled **against deployed metadata** in `force-app/main/default/` (active OmniScript/IP versions parsed from XML, Apex existence and field reads grepped, queues/permission sets/picklists confirmed). Companion to `Recred_GuidedFlow_to_ReCredPDA_Routing_Audit_2026-06-08.md` (routing) and `Recred_PDA_PSV_Route_PAR_Form_Audit_2026-06-08.md` (broader PSV/PAR audit).

> **Repo-vs-org caveat.** Everything below is evidence from the **source repo**. Source can lag the org. Items marked **[CONFIRM IN ORG]** need a 5-minute check in the target org before they are treated as final.

---

## 1. Verdict

**The lane is structurally complete and wired end-to-end — it is not blocked by missing plumbing. It is blocked by three data-correctness defects, one of which (over-broad termination scope) can damage provider data at scale.**

| Layer | State |
|---|---|
| OmniScripts (PDA Update, PDA QC) | **Built and active** (v7 / v3) |
| Integration Procedures (fetch, persist, termination) | **Built and active** |
| Stage picklist values, queues, permission sets | **All present** |
| Apex termination/RCAT services | **Present** (18 of 21 expected classes) |
| **Data correctness (removal scope, effective-to, error reasons)** | **DEFECTIVE — blocking** |
| **High-volume (100+ locations) handling** | **Not built** |
| **Test coverage vs ≥85% DoD** | **Not met on the highest-risk classes** |

**Recommendation:** do not re-enable location *removal* through the PDA lane until G1–G3 below are fixed. Re-enabling *add-only*, low-volume PDA updates is a materially smaller risk and could be gated separately (see §6).

---

## 2. What is built and verified working (no action needed)

Verified present and active in `force-app`:

| Component | Version / evidence |
|---|---|
| `PRM_ReCredUpdate_English` (PDA Update) | **v7, `isActive=true`** |
| `PRM_ReCredQCUpdate_English` (Network Mgmt QC) | **v3, `isActive=true`** |
| `PRM_RecredQC_English` (upstream review) | v13 active |
| `PRM_NonRoutineCommitteeReview_English` (PDA entry point) | v4 active |
| `PRM_ReviewRCAT_English` | v10 active |
| `PRM_FetchFormRecredUpdate_Procedure` | **v5 active** (+ Parent v1 active) |
| `PRM_RecredPDAUpdateRecords_Procedure` / `…Parent` | **v1 active** (persistence) |
| `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` | **v11 active** (+ Parent v1) |
| `PRM_RecredPDAHelper_Procedure` | v9 active |
| Stage picklist `PRM_Stage__c` | contains **`Recred Updates`**, **`Network Management QC`**, `Complete` |
| Queues | `PRM_PDAInitialCredQueue`, `PRM_NetworkManagementQCQueue`, `PRM_PDAQueue`, `PRM_PDAAdminQueue` all exist |
| Permission sets | `PRM_ProviderDataAdmin`, `PRM_NetworkManagementQC` exist |
| Fields | `HealthcareFacility.PRM_PNC__c`, `PRM_NonParLocation__c`, `PRM_NonParticipatingStartDate__c`, `IndividualApplication.PRM_RecredUpdate__c` / `PRM_RecredTerm__c` / `PRM_Decision_Date__c` / `PRM_TerminationReason__c` / `PRM_ErrorReasons__c` all exist |
| Apex | `PRM_FullPracTermRecredBatchService`, `PRM_FullPracTerminationRecredBatch`, `PRM_PractitionerTerminationUtility`, `PRM_PractitionerTerminationBatchHelper`, `PRM_RCATProcessingService/Controller`, `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch`, `PRM_RCATTerminationBatchHelper`, `PRM_RCATTerminationEffectivityHelper`, `PRM_PracticeLocationTerminationBatch`, `PRM_PracLocTermHelper/Utility`, `PRM_CommitteeReviewHelper` |

### Correction to the earlier audit
`Recred_PDA_PSV_Route_PAR_Form_Audit_2026-06-08.md` flagged `PRMFetchRecredUpdateData` as notable because the export showed `active=false`. **That signal is meaningless in this repo:** of **1,432** DataRaptor files in `force-app/main/default/omniDataTransforms/`, **0 have `<active>true</active>` and all 1,432 have `<active>false</active>`**. The flag is a source-format artifact, not org state. **No DataRaptor should be treated as disabled on the basis of that tag.** The DataRaptor is referenced by the active IP v5 and is in use.

---

## 3. BLOCKING GAPS (must fix before enabling removal)

### G1 — Location removal is not scoped to the practitioner (Bug 1216121) — **P0, data-damaging**

**Confirmed at the metadata level.** In `PRMFetchRecredUpdateData_1`, the `PPLTaxonomyNetwork` extract (query sequence 2, object `HealthcareFacilityNetwork`) has exactly **three** filters:

```
PRM_CaseManager__c      =  CaseManagerId
HealthcareFacilityId    =  PractitionerFacility:HealthcareFacilityId
PRM_RecordTypeName__c   =  'PRM_FacilityPractitionerTxNw'
```

There is **no `PractitionerId` filter.** `PPLTaxonomyNetwork:PractitionerId` appears in the DataRaptor **only as an output mapping**, never as a filter. Because `PRM_FacilityPractitionerTxNw` rows are per-practitioner-at-facility, the removal set is "every practitioner-taxonomy-network row **at that facility** carrying this Case Manager" rather than "this practitioner's rows."

The only thing limiting blast radius today is the `PRM_CaseManager__c` filter — which is precisely the field that the known nightly-script defect (**Bug 1331370**, stamping a new Case Manager onto stale `HealthcarePractitionerFacility` rows at terminated locations) **over-stamps**. So G1 and 1331370 compound: the more the nightly script over-stamps, the wider a single location removal reaches.

The live UI already tells the user this is happening — `PLTermWarningMsg` (active in **both** v7 and v3) shows when `ActivePractitioners = 1`, warning the location will also be terminated. The cascade is intentional; **the scope is wrong**.

**Fix:** add a practitioner-scope filter to the removal extract (and re-validate against the CM-stamping defect). **Do not enable removal until this is done.**

---

### G2 — Effective-To on removal still hard-defaults to the approval date (Bug 1216121, second half) — **P0**

Verified in the **active** versions:

| Script (active) | `RemovePPLEffTo` default | Assessment |
|---|---|---|
| `PRM_ReCredQCUpdate_English` **v3** (QC) | **`null`** | **fixed** — no longer force-stamped |
| `PRM_ReCredUpdate_English` **v7** (PDA Update) | **`%CaseManager:ApprovedDate%`** | **still defective** |

So the fix landed on the QC side but **not** on the PDA Update side, where the removal is actually authored. `RemovePPLEffTo` is `readOnly: true`, so the PDA specialist **cannot correct it** — whatever the approval date is becomes the termination date for every row in the removal block.

A new element `EffectiveToDateValidFrmla` **was** added in v7 — but it only validates the **added** location:

```
IF(%EffectiveToNew|n% > %EffectiveFromNew|n% || %EffectiveToNew|n% == NULL, true, false)
```

It references `EffectiveToNew` / `EffectiveFromNew` (the add path) and **never touches `RemovePPLEffTo`**. The removal path has no date validation at all.

**Fix:** make `RemovePPLEffTo` either user-editable with validation, or derived per-row from the actual termination decision rather than `CaseManager.ApprovedDate`.

---

### G3 — QC "Errors Found" table renders on the wrong outcome (Bug 1216120) — **P2/medium, still open**

Verified in **active QC v3**. `RemovePPLTxNtwk` show condition:

```
RemovePPLS|1:RemovePPLPLName  <>  null
```

Still **no guard on `NtwkMgmtQCReviewOutcome`**, so the "Removed Practitioner at Practice Location Taxonomy and Network" block renders regardless of whether the reviewer chose `QC Completed` or `Errors Found`. The element was iterated since the earlier audit (the keyed field changed from `RemovePPLPrac` to `RemovePPLPLName`), but the missing outcome guard was **not** addressed.

**Fix:** add `NtwkMgmtQCReviewOutcome = 'QC Completed'` (or `<> 'Errors Found'`) to the show group.

---

### G4 — NEW FINDING: QC-completed error reasons are silently dropped — **P2, previously undocumented**

The two QC persist elements write **different key names** for the same data:

| Element (active v3) | Key written | Maps to field? |
|---|---|---|
| `SetRecordsErrorsFound` | `ErrorReasons` (plural) | **Yes** → `PRM_ErrorReasons__c` |
| `SetRecordQCCompleted` | `ErrorReason` (**singular**) | **No mapping exists** |

The persistence DataRaptor `PRMUpdateIDCaseCaseMgr_1` maps only:

```
inputFieldName : IndividualApplication:ErrorReasons
outputFieldName: PRM_ErrorReasons__c
```

`IndividualApplication.PRM_ErrorReasons__c` is a **MultiselectPicklist** and there is **no** `PRM_ErrorReason__c` (singular) field on the object. So on the **QC Completed** path, `%PPLStep:SelectedErrorReasons%` is written to an unmapped key and **never persists** — QC error reasons captured on a completed review are lost, breaking QC reporting/trend analysis.

**Fix:** rename the key in `SetRecordQCCompleted` from `ErrorReason` to `ErrorReasons`. Low effort, isolated.

---

## 4. PENDING REQUIREMENTS — approved stories not yet built

Reconciled from the requirement docs against code:

| ID | Requirement (source doc) | Code reality (verified) | Status |
|---|---|---|---|
| **P1** | **PNC re-point to location-level PNC** — `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md` (**P0**). DoD: *"No `hcf.Account.PRM_PNC__c` (vendor) read remains in the recred termination path (grep clean)"* | **Partially done.** `PRM_FullPracTermRecredBatchService.cls:372` correctly uses `hcf.PRM_PNC__c` (location). But **vendor PNC reads remain**: `PRM_PractitionerTerminationBatchHelper.cls:20` (SOQL selects `Account.PRM_PNC__c`) and `:782`, plus `PRM_RCATTerminationBatchHelper.cls:726`. **Grep is not clean.** | **PENDING** |
| **P2** | **Non-Par / Full-Term Practice Location termination** — `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` (P1, XXL). Doc states the gap: *"neither the auto-batch path … nor the PDM Recred-Updates Non-Par branch … performs a Non-Par Practice Location Termination"* | Proposed new class **`PRM_RCATPracticeLocTerminationBatch` is ABSENT**. `PRM_NonParLocation__c` / `PRM_NonParticipatingStartDate__c` fields exist and are written by other paths (`PRM_AccountTerminationBatchHelper`, `PRM_PracticeLocationTerminationBatch`, `PRM_FutureDatedProcessingBatchHandler`, …) but not from the recred PDA path. Build home (Path A vs Path B) is **still an open clarification (#9)**. | **PENDING — blocked on a decision** |
| **P3** | **High-volume location processing (async)** — `primarysourceverification/SOLUTION_SUMMARY.md`; the original reason the PSV add-location route was paused (100+ CAQH locations time out) | **`PracticeLocationBatchProcessor` ABSENT**, **`PRM_ProcessPracticeLocationsAsync` ABSENT**, **`IndividualApplication.PRM_PracticeLocationProcessingStatus__c` ABSENT**. Exists only as draft `.apex` in `requirements/`. README checklist fully unchecked. | **NOT BUILT** |
| **P4** | **Close Case sets `PRM_RecredTerm__c`** — `CloseCase_RecredTerm_PSV_QC_UserStory.md`. Without it, closed re-cred PSV/QC cases never reach RCAT (and therefore never reach `Recred Updates`) | Requires new version of `PRM_CloseCaseGuidedFlow_English` element `SetRecordsOtherType`. Manual workaround today is `scripts/ReCredPSVToRCAT.apex`. DoD unchecked; P0-vs-P1 still an open clarification. | **PENDING** |
| **P5** | **ReCredQC editable review + per-step notes** — `ReCredQC_EditableReview_Analysis.md` / `reCredQC.md` (duplicate docs) | Radios still `readOnly: true`; per-step notes absent; 2–3 sprint estimate; checklist unchecked. Upstream of PDA — quality-of-input issue, not a PDA blocker. | **PENDING (not blocking)** |
| **P6** | **PDA QC LWC redesign** — `PDA_QC_Review_LWC_Redesign_Detailed_Design.md` | Document status **"DRAFT – Awaiting Stakeholder Feedback"**; 7 open questions; proposed objects `PRM_VerificationSession__c` / `PRM_VerificationTileStatus__c` not built. | **DESIGN ONLY (not blocking)** |
| **P7** | **Apex service migration for PDA Review/Update** — `Enhancements/PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` (+ Off-Cycle variant) | "To-Be" blueprint; Done-Definition fully unchecked; feature flag `PRM_PDAReviewApexEnabled__c` not present. Strategic, not required for enablement. | **DESIGN ONLY (not blocking)** |

---

## 5. NON-BLOCKING FINDINGS (hygiene / risk)

### H1 — Test coverage does not meet the ≥85% DoD on the riskiest classes

No test class references these at all (grep across `classes/*Test.cls`):

| Class | Size | Test references |
|---|---|---|
| `PRM_FullPracTermRecredBatchService` | 628 lines | **0** |
| `PRM_RCATTerminationEffectivityHelper` | 219 lines | **0** |
| `PRM_PracticeLocationTerminationBatch` | 466 lines | **0** |

These are exactly the classes that execute recred terminations. Every cited user story carries a *"≥85% Apex coverage"* DoD item. `PRM_FullPracTermRecredBatchService` is also the class carrying the already-completed half of the PNC re-point (P1), so it is being modified without a safety net.

### H2 — Two versions of the same OmniScript are marked active in source — **deployment hazard**

| OmniScript | Active versions in repo |
|---|---|
| `PRM_RecredQC_English` | **v8 AND v13** (same `type=PRM`, `subType=RecredQC`, `language=English`) |
| `PRM_ReviewRCAT_English` | **v8 AND v10** (same type/subType/language) |

OmniStudio permits only one active version per type/subType/language, so this is a **committed-source artifact**, not org state. The risk is real at deploy time: deploying the repo as-is can activate the wrong (older) version and silently regress the recred review or the RCAT screen. **[CONFIRM IN ORG]** which version is genuinely active, then deactivate the stale one in source.

### H3 — Duplicate requirement documents
`requirements/reCredQC.md` and `requirements/ReCredQC_EditableReview_Analysis.md` are the same document (same title, executive summary, phases, checklist, version 1.0, dated 2026-04-08). Consolidate to one to avoid divergent edits.

---

## 6. Enablement gates

**Gate 1 — Safe to work location REMOVALS (currently blocked)**
- [ ] **G1** practitioner-scope filter added to `PRMFetchRecredUpdateData` removal extract; verified on a facility with several practitioners under one Case Manager
- [ ] **G2** `RemovePPLEffTo` no longer hard-defaults to `%CaseManager:ApprovedDate%` in `PRM_ReCredUpdate_English`; removal-path date validation added
- [ ] **Bug 1331370** Case Manager over-stamping resolved or bounded (it widens G1's blast radius)
- [ ] Regression proof: remove one location for one practitioner at a multi-practitioner facility → **only that practitioner's** rows are terminated

**Gate 2 — Safe to work at volume**
- [ ] **P3** async location processing built and deployed (not just designed)
- [ ] **P1** PNC re-point grep-clean across `PRM_PractitionerTerminationBatchHelper` and `PRM_RCATTerminationBatchHelper`
- [ ] **H1** tests for the three untested termination classes, ≥85%

**Gate 3 — Complete functional parity**
- [ ] **P2** Non-Par / Full-Term PL termination (after the Path A/B decision)
- [ ] **P4** Close Case stamps `PRM_RecredTerm__c`
- [ ] **G3** QC display guard; **G4** `ErrorReasons` key fix
- [ ] **H2** stale active OmniScript versions cleaned in source

**Lower-risk interim option:** G3, G4, P1 and H1 are independent of the removal defects. If the business needs partial capability sooner, an **add-only / no-removal** PDA lane (removal block hidden) clears Gate 1 without waiting on G1/G2 — but that needs an explicit product decision, because `PLTermWarningMsg` shows termination is an expected part of the flow.

---

## 7. Decisions needed

1. **P2 build home** — RCAT batch (Path A), the PDM Recred-Updates IP branch (Path B), or both? Story clarification #9 is unanswered and blocks an XXL item.
2. **P4 priority** — the story asks P1 vs P0; today closed re-cred PSV/QC cases silently strand in `Pending Closure` and require the manual `ReCredPSVToRCAT.apex` script.
3. **Ownership of Bug 1331370** (nightly Case Manager stamping) — it is a dependency of G1, and prior audits list it as unowned.
4. **Interim add-only enablement** — acceptable, or hold the whole lane until Gate 1 completes?
5. **PNC fallback** — if location-level `PRM_PNC__c` is not fully backfilled, hard cutover or fall back to vendor PNC? (Story clarification #3.)

---

## 8. Stories written from this audit

Each gap below has a written user story. Build in the order shown — US-7 first (it makes the other deployments predictable), then US-6 (safety net), then the P0 defects.

| Order | Story file | Covers | Priority |
|---|---|---|---|
| 1 | `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md` | H2 — stale active versions | P1 |
| 2 | `RecredTermination_ApexTestCoverage_UserStory.md` | H1 — no coverage on termination classes | P1 |
| 3 | `RecredPDA_LocationRemoval_PractitionerScope_BugFix_UserStory.md` | G1 — Bug 1216121 scope | **P0** |
| 4 | `RecredPDA_LocationRemoval_EffectiveToDate_BugFix_UserStory.md` | G2 — Bug 1216121 date | **P0** |
| 5 | `PSV_CaseClosure_HighVolumeLocations_AsyncProcessing_UserStory.md` | P3 — high-volume async | **P0** |
| 6 | `RecredPDA_QC_ErrorReasons_Persistence_BugFix_UserStory.md` | G4 — error reasons dropped | P2 |
| 7 | `RecredPDA_QC_RemovedPractitionerTable_DisplayGuard_BugFix_UserStory.md` | G3 — Bug 1216120 display | P2 |

**Already covered by existing stories (not rewritten):** P1 PNC re-point → `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md` · P2 Non-Par/Full-Term location termination → `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` · P4 Close Case stamping → `CloseCase_RecredTerm_PSV_QC_UserStory.md`.

---

## 9. Evidence appendix

Reproduce the key checks:

```bash
cd force-app/main/default

# Active OmniScript versions
for f in omniScripts/PRM_ReCredUpdate_English_*.os-meta.xml \
         omniScripts/PRM_ReCredQCUpdate_English_*.os-meta.xml; do
  echo "$f -> $(grep -o '<isActive>[a-z]*</isActive>' $f | head -1)"
done

# DataRaptor <active> flag is meaningless (expect 0 true / 1432 false)
grep -l "<active>true</active>"  omniDataTransforms/*.rpt-meta.xml | wc -l
grep -l "<active>false</active>" omniDataTransforms/*.rpt-meta.xml | wc -l

# G1: no PractitionerId FILTER on the removal extract
grep -B3 -A3 PractitionerId omniDataTransforms/PRMFetchRecredUpdateData_1.rpt-meta.xml

# P1: vendor PNC reads that must disappear
grep -n "Account.PRM_PNC__c" classes/PRM_PractitionerTerminationBatchHelper.cls \
                             classes/PRM_RCATTerminationBatchHelper.cls

# G4: singular vs plural error-reason key
grep -o "IndividualApplication:ErrorReasons" omniDataTransforms/PRMUpdateIDCaseCaseMgr_1.rpt-meta.xml

# P3: async processor absence
ls classes/PracticeLocationBatchProcessor.cls 2>/dev/null || echo "ABSENT"
```

Active-version element inspection (defect verification for G1–G4) was done by parsing
`omniScripts/PRM_ReCredUpdate_English_7.os-meta.xml` and
`omniScripts/PRM_ReCredQCUpdate_English_3.os-meta.xml` — the `propertySetConfig` of each
element is HTML-escaped JSON inside the XML, so `show`, `defaultValue` and
`elementValueMap` must be read from the parsed JSON rather than by grepping the raw file.
