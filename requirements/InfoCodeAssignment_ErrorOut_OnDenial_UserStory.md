# User Story: Error Out Info Code Assignments When a Case Manager Is Denied

**Story ID:** PNM-INFOCODE-DENIAL-001
**Type:** Bug / Defect
**Vertical:** PNM (Provider Network Management)
**Epic:** Credentialing Denial Handling
**Persona:** Credentialing Reviewer / Senior Reporting User
**Priority:** High
**Generated via:** User Story Architect (session 20260630_140032_69497c94)

## Story

**As a** credentialing reviewer who denies a practitioner application,
**I want** the practitioner's Info Code Assignments to be errored out automatically when the Case Manager is denied,
**So that** denied applications leave no active or pending Info Codes behind, consistent with every other related record.

## Scope

In scope: erroring out `PRM_InfoCodeAssignment__c` records when a Case Manager (`IndividualApplication`) is denied, across every denial entry point that routes through `PRM_CaseManagerDenialUtility` — Application Review, Close Case button, Committee Review, PSV, and the Case Manager Closure flow.

Out of scope: approve/activation flows, future-dated processing, and any change to the other 14 related object types already handled on denial.

## Reproduction (from QA)

1. As a Cred user, submit a **Practitioner Participation Form** (role PCP; concierge questions YES/YES; new group, Practice Type PCP; 2 concierge Practice Locations).
2. Complete **App Review**, **PSV**, and **QC Review**.
3. As a **Senior Reporting** user, **remove the record**, add deny reason *Denied at Committee Review*, click **Done**.
4. Observe the related records.

**Actual:** Info Code Assignments remain Pending (`PRM_Pending__c = true`).
**Expected:** Info Code Assignments are errored out (`PRM_IsErrorRecord__c = true`, `PRM_Pending__c = false`, `PRM_Active__c = false`).

## Acceptance Criteria

Scenario: Denial during Application Review errors out Info Codes
Given a PAR practitioner application with pending Info Code Assignments
When the application is denied during Application Review
Then each related Info Code Assignment is set to PRM_Pending__c = false
And each related Info Code Assignment is set to PRM_IsErrorRecord__c = true
And each related Info Code Assignment is set to PRM_Active__c = false

Scenario: Denial via the Close Case button errors out Info Codes
Given a Case with pending Info Code Assignments
When the case is denied via the Close Case button
Then all related Info Code Assignments are errored out

Scenario: Denial at Committee Review errors out Info Codes
Given a practitioner application at Committee Review
When a Senior Reporting user removes the record, adds a deny reason, and clicks Done
Then all related Info Code Assignments are errored out

Scenario: Concierge and non-concierge Info Codes are both errored out
Given a denied Case Manager with concierge and non-concierge Info Code Assignments
When the denial completes
Then both concierge and non-concierge Info Code Assignments are errored out

Scenario: Shared records are preserved
Given an Info Code Assignment tied to a group or practice location shared by another in-progress pre-NMQC application
When the current Case Manager is denied
Then that shared Info Code Assignment remains pending

Scenario: Bulk denial stays within governor limits
Given a Case Manager with 200 or more pending Info Code Assignments
When the Case Manager is denied
Then all Info Code Assignments are errored out in a single bulk DML with no governor limit errors

## Technical Section

**Root cause:** `PRM_CaseManagerDenialUtility.updatePendingCheckboxOnDenial` flips `PRM_Pending__c = false` on 14 related object types but never queries or updates `PRM_InfoCodeAssignment__c`; `getIndividualApplication` has no `Info_Code_Assignments` subquery.

**Fix:** In `PRM_CaseManagerDenialUtility`, gather the Case Manager's pending, non-errored Info Code Assignments via `PRM_CaseManager__c` (lookup to `IndividualApplication`, relationship `Info_Code_Assignments`) plus the denied practitioner/PL/PPL ids already collected in the method (`PRM_Account__c`, `PRM_HealthcareFacility__c`, `PRM_HealthcarePractitionerFacility__c`). Filter `PRM_IsErrorRecord__c = false AND PRM_Pending__c = true`. Set `PRM_Pending__c = false`, `PRM_IsErrorRecord__c = true`, `PRM_Active__c = false` and run one bulk `Database.update(..., AccessLevel.SYSTEM_MODE)` alongside the existing DML blocks (one DML per object type).

- Honor the shared-record guard `getRecordsSharedByOtherInProgressApps` (story 1443813): do not error out an Info Code tied to a group/PL still referenced by another in-progress (pre-NMQC) application.
- Reusable DataRaptors `PRMDRGetInfoCodeForDenialFlow` and `PRMDRLoadInfoCodeUpdateForDenailFlow` already implement this exact field flip (concierge-only today) — declarative alternative if preferred, but the Apex-central fix is preferred because all paths already share the utility.
- Update `PRM_CaseManagerDenialUtilityTest` to >=85% coverage incl. bulk (200) and shared-record paths.

## Impact Analysis

The fix is central, so all denial entry points sharing `PRM_CaseManagerDenialUtility` are corrected at once:

| Path | Entry point (active) | Status today |
|---|---|---|
| Application Review | `PRM_InitialCredentialAppReview` → `PRM_ReviewParCaseRecordsUpdate_Procedure_15` → `PRM_CaseManagerDenialUtility.offCycleDenial` | Only concierge ICAs errored |
| Close Case button | Case WebLink `PRM_CloseCase` → `PRM_CloseCaseGuidedFlow_English_5` → same utility | Only concierge ICAs errored |
| Committee Review | `prmCommitteeReview` LWC → `PRM_PARReCredCommitteeReviewDenialBatch` (and legacy `PRM_PARRequestDenialUtility`) → utility | No ICAs errored |
| PSV (found via dependency scan) | `PRM_ReviewPSVCaseRecordsUpdate_Procedure_27` → utility | No ICAs errored |
| Case Manager Closure flow (found via dependency scan) | `PRM_CaseManagerClosureFlow` → `PRM_CaseManagerDenialUtility.updatePendingCheckboxFlow` | No ICAs errored |

Verify the `PRM_InfoCodeAssTrigger` concierge rollup and future-dated processing do not regress when ICAs flip to errored. Reconcile the now-redundant concierge-only branch in `PRM_ConceirgeCloseCaseHelper`.

## Clarification Questions

1. Should every Info Code on the practitioner be errored, or only those created/updated by this Case Manager (`PRM_CaseManager__c = caseManagerId`)? Recommendation: scope to this Case Manager plus the denied PL/PPL/practitioner records, honoring the shared-record guard.
2. After the central fix, should the concierge-only branch in `PRM_ConceirgeCloseCaseHelper` be removed (avoid double processing) or kept as idempotent?
3. Confirm terminal field state: `PRM_IsErrorRecord__c = true` AND `PRM_Active__c = false` AND `PRM_Pending__c = false`.

## Estimated Effort

**3 story points** — one Apex method change + bulk DML + reuse of the existing shared-record guard, plus test class updates. Low risk, central change, no schema changes. _AI-estimated — validate with team._

## Components in Scope

- **Fix:** `force-app/main/default/classes/PRM_CaseManagerDenialUtility.cls` (+ `PRM_CaseManagerDenialUtilityTest.cls`)
- **Verify/regression:** `PRM_PARReCredCommitteeReviewDenialBatch.cls`, `PRM_PARRequestDenialUtility.cls`, `PRM_DenialSharedPendingGuard.cls`, `PRM_InfoCodeAssTrigger*`, IP `PRM_ReviewParCaseRecordsUpdate_Procedure_15`, IP `PRM_ReviewPSVCaseRecordsUpdate_Procedure_27`, sub-IP `PRM_ConceirgeCloseCaseHelper`, `PRM_CaseManagerClosureFlow`
- **Reusable denial logic:** `PRMDRGetInfoCodeForDenialFlow`, `PRMDRLoadInfoCodeUpdateForDenailFlow`

---

## Revision History

| Version | Date | Summary |
|---------|------|---------|
| cfd1dae7b1d4 | 2026-06-30 | Regenerated in User Story Architect format (PNM): added Persona, Gherkin ACs, Scope, Technical Section, Impact Analysis, Clarification Questions, Estimated Effort; added PSV + Case Manager Closure denial entry points found via dependency scan. |
