# Recred PDA Guided Flow / PSV Add-Location Route / PAR Form — Readiness Audit

**Date:** 2026-06-08
**Prepared for:** Business (Recredentialing operations)
**Question being answered:** *"In production we paused the Recred PDA guided flow and told the Recred team NOT to add new practice locations via the PSV route (use email instead). Can we resume? What is pending, what is implemented, and what still needs to be fixed?"*

> **Method & caveat.** This audit reconciles (a) the requirement/design docs in `requirements/` against (b) what actually exists as deployable metadata in `force-app/main/default/` and the OmniStudio export. The local `force-app` source is the source of truth for *code that exists*; it is **not** a guarantee of what is **active in the production org**. Items marked "Implemented (code present)" still need a production-org confirmation (active OmniScript version, field deployed, batch scheduled) before business resumes. Where the on-the-ground state diverges from the docs, the on-the-ground state is reported.

---

## 1. Bottom line (read this first)

**Recommendation: DO NOT resume adding new practice locations via the PSV route in production yet.** The specific defect that caused the team to stop — and several related production data-integrity defects on the PAR form and recred pipeline — are **still open**. Most have been *analyzed and designed in detail*, but the *fixes are not deployed*.

| Question | Answer |
|---|---|
| Was the root cause of the PSV-route pause fixed? | **No.** The async practice-location processor that prevents the PSV/Service-Area timeout exists only as draft `.apex` files in `requirements/primarysourceverification/`. It is **not** in `force-app` and **not** deployed. |
| Is it safe to resume the PSV add-location route as-is? | **No.** Same timeout risk on high-volume CAQH locations, plus open terminated-location and effective-date defects. |
| Is anything safe to resume? | The **low-volume** path (≤ ~20 practice locations) has the same behavior it always had. The pause was about high-volume and data-integrity risk, both still unaddressed. |
| What HAS been built? | Substantial backend foundations: the Case Manager Association (CMA) **creation** layer, the Concierge Info Code backend + rollup, a tactical terminated-location **alert** banner, and continued iteration on the recred/PSV OmniScripts. |
| Single biggest blocker to resuming | The PSV high-volume async processor is not deployed **and** the "Required Fields Missing" terminated-location production bug (e.g. case IA-0000096229) is not fixed. |
| Are the QA-reported Re-Cred PDA Update defects still present? | **Yes — both confirmed in the live metadata** (Bug 1216120 and Bug 1216121). See §5A. The location-removal logic still cascades termination to **all** practitioners at the location, and the QC review still shows the "Removed Practitioner…" table in the Errors-Found path. |

---

## 2. Background — what was paused and why

The **PSV route for adding locations** is the Service-Area-Verification step inside the PSV / Re-Cred PSV guided flow (`PRM_PrimarySourceVerificationReview_English`, and the recred guided OmniScript `PRM_RecredQC_English`). On case closure it creates/updates `HealthcarePractitionerFacility` (practitioner↔location), `HealthcareFacility`, `Location`, and address records for **every** CAQH practice location.

Two failure modes drove the pause:

1. **High-volume timeout.** When a practitioner has 100+ CAQH locations, the synchronous Integration Procedure (`PRM_ReviewPSVCaseRecordsUpdate`) hits JSON-size / DML / CPU limits and the OmniScript times out or partially fails. (`requirements/primarysourceverification/PSV_Case_Closure_Field_Updates.md` — "THIS IS THE PROBLEM AREA".)
2. **Data-integrity defects** around terminated locations, effective/back-dating, and partial record creation that produce the "Required Fields Missing" error and orphaned records.

Because of this, the Recred team was asked to stop using the guided PSV add-location path and email requests instead.

---

## 3. What IS implemented on the ground (code present in `force-app`)

These are real, deployable components found in the repo. Treat them as "built locally — confirm active in prod."

### 3.1 Case Manager Association (CMA) — **creation layer built & wired**
The CMA junction was introduced to stop review flows from breaking when `HealthcarePractitionerFacility.PRM_CaseManager__c` is overwritten by PDM / Provider-Change.

- **Object:** `PRM_CaseManagerAssociation__c` with 14 record types (incl. `Practitioner_Practice_Location`, `Practice_Location_Address`, `Practice_Location_Network`, `Identifier`, `Business_License`, `Healthcare_Provider_Taxonomy`, `PRM_Vendor`, etc.) and lookups incl. `PRM_HealthcarePractitionerFacility__c`, `PRM_HealthcareFacility__c`, `PRM_Address__c`, `PRM_CaseManager__c`, `PRM_RequestType__c`.
- **Apex (present):** `PRM_CaseManagerAssociationService` (`createCaseManagerAssociation`), `PRM_CaseManagerAssociationDirectBuilder`, `PRM_CaseManagerAssociationAddressBuilder`, `PRM_CaseManagerAssociationNetworkBuilder`, `PRM_CaseManagerAssociationBatch` (+ test).
- **Wired into:** `PRM_CreatePractitionerAddressRecords_Procedure_41..44`, `PRM_ReviewPSVCaseRecordsUpdate_Procedure_26`, the PDM record-creation IPs, `PRM_InitManualUpdatesQC`, and case-detail fetch IPs.

> **Gap (see §5):** Only the **write/create** half is built. The **read/resolve-via-CMA** half — `PRM_CaseManagerAssociationFetchService` and DataRaptor `PRMDREGetPARCaseHCPFViaCMA` (US7/US14 of the CMA v3 stories) — was **not found**. Review flows therefore still resolve HCPF by `PRM_CaseManager__c`, which is the exact field the redesign was meant to stop depending on. **CMA is half-deployed.**

### 3.2 Concierge Medicine — **backend & rollup built; user-facing capture partial**
- **Objects/fields (present):** `PRM_InfoCode__c`, `PRM_InfoCodeAssignment__c` with all three assignment levels (`PRM_Account__c` = practitioner, `PRM_HealthcareFacility__c` = location, `PRM_HealthcarePractitionerFacility__c` = practitioner-practice-location), plus `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`, `PRM_Active__c`, `PRM_Pending__c`, `PRM_IsErrorRecord__c`. Validation rules present: `PRM_EffectiveDateValidation`, `PRM_EndDateValidation`, `PRM_RestrictAssignments`, `PRM_RestrictICAToSaveOneAccPLOrTaxonomy`.
- `PRM_IsConciergeProvider__c` exists on **Account, HealthcareFacility, and HealthcarePractitionerFacility**; `PRM_ConciergeMedicineIndicator__c` on `IndividualApplication`.
- **Apex (present):** `PRM_InfoCodeAssTrigger` + `PRM_InfoCodeAssTriggerHandler` + `PRM_InfoCodeAssTriggerHelper`, `PRM_ConciergeRollupHelper`, `PRM_ConciergeProviderRollupQueueable` (+ tests).
- **DataRaptor (present):** `PRMLoadInfoCodeConciergeForPractitioner`.

> **Gap:** The **PAR-form-facing** concierge question (`RadioConciergeMedicine`, optional-fee, attestation warning) and the per-location recred PSV concierge question were **not confirmed** in the OmniScript export — the **old** patient-fee question element (`PractitionerPatientFeeQuestion1Error`) is still present. The concierge *backend/rollup* is built; the *capture-on-the-form* (Epics 2/3 and Story 6.3) and the add-location/denial/termination wiring (`PRM_InfoCodeAssignmentUtility`) are **not** evidenced as deployed.

### 3.3 Terminated-location tactical alert — **built & on the page**
- LWC `prmTerminatedLocationAlert` (html/js/css/meta all present) is referenced in `PRM_CaseManagerRecordPage.flexipage`. This is the "quick-win" red banner that warns a specialist of terminated locations **before** they open a review flow. **Detection only — it does not fix the underlying data.**

### 3.4 Recred / PSV guided flow OmniScripts — **actively maintained**
- `PRM_RecredQC_English` (through v13), `PRM_PrimarySourceVerificationReview_English` (through v50), `PRM_ReCredUpdate_English`, `PRM_ReCredQCUpdate_English`, `PRM_PractitionerParticipationForm_English` (through v106), `PRM_PractitionerParticipationAddressForm_English` (through v54). The guided flows exist and are being iterated; the **LWC tile redesign** of these flows is **draft only** (see §5).

### 3.5 Effective-date & termination infrastructure (partial)
- `PRM_HCPFTriggerHelper` exists and propagates HCPF `EffectiveFrom`/`EffectiveTo` to affiliation / `PRM_ProviderFeature__c` records on insert/update.
- Future-dated processing batch infrastructure exists (`PRM_FutureDatedProcessingBatchHandler`).
- A one-time effective-from data-fix was run previously (`DFX_RevertEffFromDateExec*`).

> **Gap:** This is **not** the centralized "P2P EffectiveFrom = oldest active PPL" fix (§5/§6).

---

## 4. What is PENDING (designed / specified but NOT built)

These are fully specced in `requirements/` but have **no corresponding deployable code** in `force-app`.

| # | Item | Spec doc(s) | Evidence it's not built |
|---|------|-------------|--------------------------|
| P1 | **Async PSV practice-location processor** (the PSV-route timeout fix) | `primarysourceverification/SOLUTION_SUMMARY.md`, `Integration_Procedure_Modifications.md` | `PracticeLocationBatchProcessor` exists only as `.apex` files in `requirements/`; no `PRM_ProcessPracticeLocationsAsync` IP; no `PRM_PracticeLocationProcessingStatus__c`/`...Started__c`/`...Error__c` fields on IndividualApplication |
| P2 | **CMA read/resolve path** (resolve review-flow HCPF via CMA) | `PAR_CaseManager_Association_CMA_User_Stories_v3.md` (US7, US14) | `PRM_CaseManagerAssociationFetchService` and `PRMDREGetPARCaseHCPFViaCMA` not found |
| P3 | **P2P EffectiveFrom = oldest-active-PPL sync** + backfill | `P2P_EffectiveFrom_Fix_*` (5 docs) | No `syncP2PEffectiveFromOldestActivePPL`, no `PRM_EnableP2PEffectiveFromAutoSync__c` flag, no `PRM_BackfillP2PEffectiveFromBatch` |
| P4 | **Future-dated termination push-out fix** | `FutureDated_Termination_PushOut_*` (3 docs) | No `PRM_TerminationDateUtility` / `computeEffectiveTo` |
| P5 | **PAR partial-rollback orchestrator** | `PAR_Form_PartialDataRollback_Investigation_FixPlan.md` | No `PRM_ParFormOrchestrator`; no `PRM_FailedRecordStaging__c` write-path |
| P6 | **PAR-form Concierge capture + add-location/denial/termination wiring** | `Concierge_Medicine_PAR_Form_Changes_*`, `Concierge_InfoCodeAssignment_All_Flows_Summary.md`, `Concierge_Off_Cycle_*` | `RadioConciergeMedicine` not confirmed in OmniScript; no `PRM_InfoCodeAssignmentUtility` |
| P7 | **Recred → PAR batch conversion** | `Recred_to_PAR_Batch_Programmatic_Implementation_Plan.md` | Plan only; no batch class; "Next Steps: review & approve with business" |
| P8 | **Recred → Initial-Cred conversion flag/routing** | `ReCred_to_InitialCred_Conversion_Plan.md` | Field `PRM_ReCredToInitialCredConversion__c` and routing changes proposed; US-7 "Pending business confirmation" |
| P9 | **Credentialing-flow LWC tile redesign** (6 flows) | `ReDesignCredFlows/*` | All docs "Status: DRAFT — Awaiting Stakeholder Feedback"; no `prm_psvAddressVerification`/`prm_verificationDashboard` components |
| P10 | **ReCredQC editable fields + per-step notes** | `ReCredQC_EditableReview_Analysis.md` / `reCredQC.md` | Analysis only; checklist all unchecked |
| P11 | **New-primary-when-active-primary-exists staging** | `PAR_NewPrimaryPracticeLocation_ExistingActivePrimary_UserStories.md` | No `PRM_HCPractitionerFacilityActivationService` |
| P12 | **PAR Notes-optional; PNC-path UI fixes; Par-form UI field gaps** | `PAR_Notes_*`, `PAR_Form_PNC_Path_*`, `Par_Form_vs_Our_Implementation_UI_Comparison.md` | Pending |

---

## 5. What NEEDS FIXING (open production defects)

Every item below is documented as a **current production problem** with a root cause identified and a fix designed but **not deployed**.

1. **"Required Fields Missing" on terminated locations (P0 — active prod blocker).** Traced end-to-end to case **IA-0000096229** (`PractitionerForm/PAR_AppReview_TerminatedLocation_DailyScript_Analysis.md`). Three combined gaps: App-Review false positive (US4), re-submit doesn't create affiliation (US1), and a **daily script (bug 1331370)** that stamps a new Case Manager + `PRM_Pending__c=true` onto a stale HCPF tied to a *terminated* location (US5 — "NOT COVERED — NEW GAP"). The tactical alert (§3.3) only *detects*; the fix is not deployed.

2. **PAR partial data / orphaned records (P0, "recurring and growing").** PAR sub-IPs commit in separate transactions; a failure mid-chain leaves orphaned `HealthcareProviderNpi` (AccountId=NULL), duplicate `HealthcareProviderTaxonomy`, NPEs in `setPracFacilityIdentifier`. Fix = single-transaction `PRM_ParFormOrchestrator` (not built).

3. **Duplicate-record errors on existing-record re-submit.** 19 provider/vendor combinations blocked. Some rows are data-fixable via `PAR_Form_DuplicateErrors_DataFix_Runbook.md`; **Categories B & D are "recurring bug / blocked on code fix"** (trigger idempotency + upsert keys — not built).

4. **P2P `EffectiveFrom` drift (data-integrity).** No flow recomputes Practice-to-Practitioner `EffectiveFrom` to the oldest active PPL; ~**230K** P2P rows need a backfill. Fix designed and feature-flagged; **not deployed.**

5. **Future-dated termination "push-out" silently ignored (P0 data-integrity).** Re-terminating with a *later* date does nothing (monotonic pull-in only); billing/mailing edits on a future-terminated location leave inconsistent open-ended records. Fix = `PRM_TerminationDateUtility` (not built).

6. **PNC-path PAR-form bug.** `SetErrorNonPNCGroup` has an incorrect show-condition/error-map; credentialed non-PNC practitioners can't take the PNC path. Not fixed.

7. **Denied/terminated record reuse blocked.** Orphaned HCPF (`PRM_Pending__c=false`, `IsActive=false`) + stale ExternalIds cause collisions on re-submission. Fix (incl. `PRMDRClearHCPFExternalIdOnDenial`) not built.

8. **Re-Cred PDA Update — location removal mass-terminates practitioners (Bug 1216121, P0 data-integrity).** Removing a practice location in the Recred Update flow lists/stamps **all** practitioners at that location with an Effective-To (`%CaseManager:ApprovedDate%`) instead of only the affiliation being removed. Confirmed in `PRM_ReCredUpdate_English` + `PRMFetchRecredUpdateData`. See §5A. Not fixed.

9. **Re-Cred PDA Update QC — "Removed Practitioner…" table leaks into Errors-Found path (Bug 1216120).** The `RemovePPLTxNtwk` Edit Block in `PRM_ReCredQCUpdate_English` has no QC-outcome guard, so it displays even when the QC outcome is "Errors Found". See §5A. Not fixed.

---

## 5A. QA-reported open defects — Re-Cred PDA Update guided flow (verified against code)

The QA team (Harikishan Nagireddy) reported the following two defects against the **Re-Cred "Recred Update" review** and **"Recred Update QC"** flow. I traced both directly to the as-built OmniStudio metadata. **Both are confirmed still present in the repo.** This is the same "Recred PDA guided flow" referenced in the original business question — the guided OmniScripts are `PRM_ReCredUpdate_English` (review/update) and `PRM_ReCredQCUpdate_English` (QC), persisting via IP `PRM_RecredPDAUpdateRecordsParent`.

### Bug 1216121 (MAJOR) — Removing a Practice Location terminates / lists **all** practitioners with an Effective-To date
**QA report:** *"the 'Recred Update' review is displaying all the Practitioners with Effective To date when a Practice Location is removed … it was removing all the practitioner when we remove Location in Re-cred. I believe this was the major issue."*

**Confirmed — root cause in code:**
- The "Removed Practitioner at Practice Location Taxonomy and Network" table (Edit Block `RemovePPLTxNtwk` in `PRM_ReCredUpdate_English`) is bound to the `RemovePPLS` data node, and its **Effective-To field (`RemovePPLEffTo`) hard-defaults to `%CaseManager:ApprovedDate%` for every row in the block** — so every listed practitioner gets stamped with an Effective-To.
- That row set is built by DataRaptor **`PRMFetchRecredUpdateData`**, which extracts `PPLTaxonomyNetwork` from `HealthcareFacilityNetwork` (record type `PRM_FacilityPractitionerTxNw`) filtered by **`HealthcareFacilityId = <removed facility>` (and `PRM_CaseManager__c`)** — i.e., it pulls **every practitioner-at-location network/taxonomy row for that facility**, not just the practitioner being acted on.
- The flow's own warning element `PLTermWarningMsg` confirms the cascade is intended only at the boundary case: it fires when `ActivePractitioners = 1` with text *"…will also be terminated, please review before proceeding."* The defect is that the removal/Effective-To is being applied to the whole location's practitioner set rather than scoped to the single affiliation being removed (and the active-practitioner guard isn't preventing the broad stamping).
- **Status: OPEN / not fixed.** Persistence runs through `PRM_RecredPDAUpdateRecordsParent_Procedure_1` (deployed). No fix doc exists for bug 1216121 in `requirements/`.

> Note: `PRMFetchRecredUpdateData` is currently `active=false` in the repo export — so the exact data-load wiring (this DR vs. the fetch IP `PRM_FetchFormRecredUpdate`) must be confirmed against the **active** version in the org, but the table binding, the facility-scoped query pattern, and the blanket Effective-To default all reproduce the reported behavior.

### Bug 1216120 — "Removed Practitioner…" table shown incorrectly when QC outcome = "Errors Found"
**QA report:** *"the 'Recred Update review' is displaying incorrect table as 'Removed Practitioner at Practice Location Taxonomy and Network' when the 'Recred Update QC' outcome is selected as 'Errors Found'."*

**Confirmed — root cause in code:**
- In `PRM_ReCredQCUpdate_English`, the `RemovePPLTxNtwk` Edit Block's **show condition is only `RemovePPLS|1:RemovePPLPLName <> null`** — there is **no condition tied to the QC outcome / "Errors Found"** path. (The `PRM_ReCredUpdate_English` twin keys on `RemovePPLS|1:RemovePPLPrac <> null`, also with no outcome guard.)
- Therefore, whenever removed-PPL data exists in the case, the table renders in QC regardless of the selected outcome — including the Errors-Found branch where it should be suppressed.
- **Status: OPEN / not fixed.** Fix is a conditional-display change (add an outcome/Errors-Found guard to the `show` group on the QC `RemovePPLTxNtwk` block, and review the related summary blocks).

### "Errors Found scenario" general concern
QA also flagged *"there might be some issues with the flow when the errors-found scenario etc."* The Errors-Found path elements exist in the flow (`SetRecordsErrorsResolved`, `ErrorReasonsReadOnly`, `PDAReturnOutcome`, `QCReturnToPDA`, `ErrorStep`, `TBError`). Given Bug 1216120 shows the removal table leaking into the Errors-Found branch, the conditional rendering across the whole Errors-Found path should be re-validated as part of the same fix.

**Bottom line:** Both QA defects are reproducible from the current metadata and are **unfixed**. Because Bug 1216121 causes incorrect mass-termination of practitioners when a location is removed during recred, it is a **data-integrity P0** and reinforces the recommendation **not** to resume the guided Recred add/remove-location path until fixed.

---

## 6. Component implementation matrix (quick reference)

| Capability | Designed | Code in `force-app` | Wired/active | Notes |
|---|:---:|:---:|:---:|---|
| PSV high-volume async location processing | ✅ | ❌ | ❌ | **The pause's root cause — unfixed** |
| CMA object + creation service | ✅ | ✅ | ✅ | Creation broadly wired (PAR/PSV/PDM) |
| CMA resolve-via-CMA read path | ✅ | ❌ | ❌ | Review still keys on `PRM_CaseManager__c` |
| Terminated-location alert (detect) | ✅ | ✅ | ✅ | Banner on Case Manager page; detection only |
| Terminated-location "Required Fields Missing" fix | ✅ | ❌ | ❌ | US1/US3/US4/US5 not deployed |
| Concierge Info Code backend + rollup | ✅ | ✅ | ✅ (backend) | Objects/trigger/rollup/fields present |
| Concierge PAR/recred capture question | ✅ | ❌/partial | ❌ | Old fee question still present |
| Concierge add-location/denial/term wiring | ✅ | ❌ | ❌ | No `PRM_InfoCodeAssignmentUtility` |
| P2P EffectiveFrom oldest-PPL sync + backfill | ✅ | ❌ | ❌ | 230K rows need backfill |
| Future-dated termination push-out fix | ✅ | ❌ | ❌ | P0 data-integrity |
| PAR partial-rollback orchestrator | ✅ | ❌ | ❌ | Orphans "recurring & growing" |
| Duplicate-record code fix | ✅ | ❌ | ❌ | Data-fix runbook partial only |
| Recred guided OmniScripts | ✅ | ✅ | ✅ | Iterating (RecredQC v13, PSV v50) |
| Recred location-removal scoped to one practitioner (Bug 1216121) | ✅ | ❌ | ❌ | **P0** — cascades Effective-To to all practitioners at the location |
| Recred QC "Removed Practitioner" table hidden on Errors-Found (Bug 1216120) | ✅ | ❌ | ❌ | No QC-outcome guard on `RemovePPLTxNtwk` show condition |
| Cred-flow LWC tile redesign | ✅ (draft) | ❌ | ❌ | All "DRAFT — awaiting feedback" |
| Recred→PAR batch / Recred→InitialCred conversion | ✅ (plan) | ❌ | ❌ | Awaiting business approval |

Legend: ✅ yes · ❌ no/not found · partial = some pieces present.

---

## 7. Recommendation & suggested sequencing

**Do not lift the "no PSV add-location / email instead" hold yet.** To get to a safe resume, the minimum bar is:

**Gate 1 — Stop the bleeding (must-fix before resuming the PSV add-location route)**
1. Deploy the **async practice-location processor** (P1) so high-volume CAQH location sets no longer time out.
2. Deploy the **terminated-location "Required Fields Missing" fix** set: US4 guard + US5 daily-script active-location check + US1/US3 (defect #5.1).
3. Deploy the **PAR partial-rollback** hardening (P5 / defect #5.2) so a mid-chain failure cannot leave orphans.
4. **Fix the Re-Cred PDA Update location-removal defect (Bug 1216121, defect #5.8)** so removing a location only terminates the intended affiliation — this is a P0 in the exact guided flow business wants to resume.
5. **Fix the Re-Cred QC Errors-Found display defect (Bug 1216120, defect #5.9)** and re-validate the Errors-Found branch conditional rendering.

**Gate 2 — Data correctness (before relying on dates/reporting)**
6. Deploy **P2P EffectiveFrom sync + run the 230K-row backfill** (P3 / defect #5.4).
7. Deploy the **future-dated termination push-out fix** (P4 / defect #5.5).
8. Complete the **CMA resolve-via-CMA read path** (P2) so review flows stop depending on the overwritten `PRM_CaseManager__c`.

**Gate 3 — Feature completeness (can follow once Gates 1–2 are stable)**
9. Duplicate-record code fix (defect #5.3); PNC-path fix (#5.6); denied/terminated reuse (#5.7).
10. Concierge PAR/recred capture + add-location wiring (P6) if concierge tracking is in scope for this resume.
11. Recred→PAR batch / Recred→Initial-Cred conversion and the LWC tile redesign are strategic, not prerequisites for resuming.

**Before flipping the switch in prod, confirm in the production org (not just the repo):**
- The async processor IP + fields are deployed and the volume threshold is set.
- The relevant OmniScript versions (`PRM_PrimarySourceVerificationReview_English`, `PRM_RecredQC_English`, `PRM_ReCredUpdate_English`, `PRM_ReCredQCUpdate_English`) that contain the fixes are the **active** versions, and the active data-load (`PRMFetchRecredUpdateData` vs. the fetch IP) is confirmed for Bug 1216121.
- A monitoring query is in place for stuck async jobs and for orphaned HCPF/HCNPI rows.

---

## 8. Open questions for business (decisions that gate the build)

1. Resume scope: **all** recred locations, or only **low-volume** (≤ ~20 locations) initially while the async processor is hardened?
2. Is **Concierge** capture in scope for this resume, or deferred? (Backend is built; the form question is not.)
3. Recred migration direction: **Recred→PAR batch** (P7) vs **Recred→Initial-Cred conversion** (P8) — these are competing approaches and only one should proceed.
4. Confirm ownership/schedule of the **daily script (bug 1331370)** so the US5 fix can be applied to the right job.

---

*Generated from a reconciliation of `requirements/` specifications against `force-app/main/default/` and the OmniStudio export. "Code present" reflects the repo; production-active status must be verified in-org before resuming.*
