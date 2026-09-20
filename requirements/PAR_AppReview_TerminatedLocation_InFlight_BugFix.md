# PAR App Review — "Required Fields Missing" When Practice Location Terminated Mid-Credentialing: Bug Fix User Story

**Document Version:** 1.0
**Created Date:** April 16, 2026
**Environment:** Prod
**Reported By:** Heather
**Vertical:** Provider Network Management (PNM)
**Guided Flow:** PAR — App Review (`PRM_InitialCredentialAppReview_English`)
**Related Documents:**
- `PAR_DeniedTerminated_RecordReuse_User_Stories.md`
- `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`

---

## Executive Summary

A practitioner submits a PAR form with one or more practice locations. While the case is still in-flight (App Review stage), one of those practice locations is **terminated externally** via a Provider Change Request — setting `HealthcareFacility.PRM_Active__c = false`. When the credentialing specialist then opens App Review, the flow throws a **"Required Fields Missing"** error and cannot proceed.

**Root cause (from codebase analysis):**

The App Review update IP (`PRM_ReviewPSVCaseRecordsUpdate`) contains a "deleted practice location" handler that detects locations where `HealthcareFacility.PRM_Active__c = false` and flags those HCPF affiliations as `EligibleForUpdate = true`. It then calls `PRMDRPPractitionerDataUpdate` to mark those HCPF records as `Active=false`, `Error=true`, `Pending=false` — the same path used when a user intentionally removes a location in App Review.

Because the terminated location was not intentionally removed by the App Review user (it was terminated externally), the in-flight HCPF records for that case (which still have `PRM_Pending__c = true`) are incorrectly processed as error records. The attempt to write `PRM_IsErrorRecord__c = true` and `PRM_Pending__c = false` to those records fails with a required-fields validation error because the linked `HealthcareFacility` is now inactive, leaving required fields unresolvable.

**The lifecycle reality this story must preserve:**

Even when a practice location is terminated externally during credentialing, the practitioner participation workflow must be allowed to continue:
```
PAR Form → App Review → PSV Review → QC → Committee Review → PDA Review & Update
                                                                      ↓
                                                         Location Reactivated Here
```
The credentialing decision is made independent of whether the `HealthcareFacility.PRM_Active__c` flag was temporarily set to false by a parallel Provider Change. Blocking App Review at this stage is both a workflow and a business logic error.

---

## Use Case Matrix

| # | Scenario | HCPF `PRM_Pending__c` | `HealthcareFacility.PRM_Active__c` | Expected App Review Behavior |
|---|----------|----------------------|-------------------------------------|-------------------------------|
| UC-1 | Location active during entire credentialing | true | true | Normal App Review — no change |
| UC-2 | **Location terminated via Provider Change WHILE case is in-flight** | **true** | **false** | **App Review must NOT block; continue credentialing** |
| UC-3 | User intentionally removes location in App Review | true → false | true or false | Mark HCPF as deleted/error — existing behavior |
| UC-4 | Location was already terminated BEFORE PAR submitted | false | false | Separate scenario (covered in PAR_DeniedTerminated story) |

---

---

# USER STORY 4: App Review — Guard Against False "Deleted Location" Trigger When Practice Location Terminated via Provider Change During In-Flight Credentialing

**Persona:** Credentialing Specialist, Developer
**Priority:** P0
**OmniScript:** `PRM_InitialCredentialAppReview_English` (v28)
**Integration Procedures:** `PRM_ReviewPSVCaseRecordsUpdate` (v23), `PRM_ValidateCAQHAppReview`
**DataRaptors:** `PRMDREGetPracticeLocation`, `PRMDREGetPLToPractitioner`, `PRMDRPPractitionerDataUpdate`
**Relevant Requirements:** Use Case UC-2 above; `PAR_DeniedTerminated_RecordReuse_User_Stories.md` (US1–US3)

---

## Story

**As a** Credentialing Specialist completing an App Review for a practitioner participation request,
**I want** the App Review flow to continue processing the case even when one of the submitted practice locations has been externally terminated (via a Provider Change Request) while the case was in-flight,
**So that** credentialing review is not blocked by a parallel operational event that will be resolved at the PDA stage, and the practitioner's participation decision can proceed without manual data correction.

**Why it matters:** When a practice location is terminated via Provider Change while a PAR case is simultaneously in App Review, the two workflows collide in Salesforce: the Provider Change sets `HealthcareFacility.PRM_Active__c = false`, and App Review's deleted-location handler interprets that flag as "the user removed this location." The result is a `Required Fields Missing` error that halts App Review entirely, requiring a Salesforce admin to manually correct the HCPF records before the credentialing specialist can proceed. This is a production blocker.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR — App Review | `PRM_InitialCredentialAppReview_English` v28 | Submit / Save step (calls `PRM_ReviewPSVCaseRecordsUpdate`) | `PRMDREGetPracticeLocation` → `PRMDREGetPLToPractitioner` → `PRMDRPPractitionerDataUpdate` |

---

## Current State (from codebase)

### `PRMDREGetPracticeLocation` (DataRaptor Extract)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDREGetPracticeLocation_1.rpt-meta.xml`
- **Input:** `PPL` (a PractitionerPracticeLocation / HCPF record)
- **Queries `HealthcarePractitionerFacility`** WHERE:
  - `RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'`
  - `HealthcareFacility.PRM_Active__c = false` ← **the flag that catches externally-terminated locations**
  - `HealthcareFacilityId = PPL:HealthcareFacilityId`
- **`EligibleForUpdate` formula:**
  ```
  IF(COUNTQUERY("SELECT Count() FROM HealthcarePractitionerFacility
    WHERE HealthcareFacilityId = '{0}'
    AND PRM_Pending__c = true
    AND HealthcareFacility.PRM_Active__c = false",
    %HealthcarePractitionerFacility:HealthcareFacilityId%) == 1, true, false)
  ```
  - Returns `EligibleForUpdate = true` when: a **pending** HCPF exists for an **inactive** location
  - **Gap:** This formula correctly fires for intentional App Review removals — but it also fires for locations terminated externally via Provider Change, because it uses ONLY `HealthcareFacility.PRM_Active__c = false` as the signal, without checking whether the termination originated from the current case's App Review session.

### `PRM_ReviewPSVCaseRecordsUpdate` (Integration Procedure, v23)

- **Location:** `force-app/main/default/omniIntegrationProcedures/PRM_ReviewPSVCaseRecordsUpdate_Procedure_23.oip-meta.xml`
- **Calls** `PRMDREGetPLToPractitioner` with input `PPL = %RA_GetDeletedData:DeletedRecords%`
- **Calls** `PRMDREGetPracticeLocation` with input `PPL = %RA_GetDeletedData:DeletedRecords%`
- **Execution condition for `PRMDRPPractitionerDataUpdate`:**
  ```
  ISNOTBLANK(%PRMDREGetPLToPractitioner:PracticeToPracticeLocation%) ||
  ISNOTBLANK(%PRMDREGetPLToPractitioner:PracticeLocationTaxNtwrk%)
  ```
- **`PRMDRPPractitionerDataUpdate` input:**
  ```json
  {
    "Active": "False",
    "Error": "True",
    "Pending": "False",
    "HealthcarePractitionerFacility": "%PRMDREGetPLToPractitioner:PracticeToPracticeLocation%",
    "FacilityTaxonomyNetwork": "%PRMDREGetPLToPractitioner:PracticeLocationTaxNtwrk%"
  }
  ```
- **Gap:** When `EligibleForUpdate = true`, the IP unconditionally fires `PRMDRPPractitionerDataUpdate` with `Error=true, Pending=false` — even for in-flight HCPF records (`PRM_Pending__c = true`) that were terminated externally, not intentionally removed in App Review.

### `PRMDRGetPractionerPracticeLocation` (DataRaptor Extract — Admitting Privileges)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDRGetPractionerPracticeLocation_1.rpt-meta.xml`
- **Filter Group 0:** `PRM_CaseManager__c = CaseManagerId` (fetches by case / IndividualApplication Id)
- **Filter Group 1:** `PractitionerId = PractitionerId` (fetches by practitioner)
- **RecordType:** `PRM_AdmittingPrivileges` — this DR handles admitting privileges, not practice location affiliations
- **Note:** This DR's case-manager-based filter is specifically for admitting privileges. The practice location affiliation path goes through `PRMDREGetPLToPractitioner` and `PRMDREGetPracticeLocation`. Both sets of DRs should be guarded with the same case-ownership check when detecting "deleted" records.

### `PRMDREGetPLToPractitioner` (DataRaptor Extract)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDREGetPLToPractitioner_1.rpt-meta.xml`
- **Input:** `PPL` (the practice location record — contains `PRM_CaseManager__c`, `HealthcareFacilityId`, `PractitionerId`)
- **Queries:**
  - Query Sequence 1 (`PracticeToPracticeLocation`): HCPF WHERE `AccountId = PPL:AccountId` AND `Id = PPL:HCPFId` AND `RecordType.Name != 'Admitting Privileges'`
  - Query Sequence 2 (`PracticeToPractitioner`): HCPF WHERE `PractitionerId = PPL:PractitionerId` AND `AccountId = PTPAccountIds` AND `RecordType.Name = 'Practice to Practitioner'`
- **No active/pending filter on HCPF records** — the DR returns records regardless of `IsActive` or `PRM_Pending__c` state on the HCPF itself.
- **Gap:** Because no `PRM_Pending__c = false` filter is applied, an in-flight HCPF with `PRM_Pending__c = true` is returned and then passed to `PRMDRPPractitionerDataUpdate` for the error/deactivation path.

---

## Technical Section (For Developers)

### Root Cause Diagram

```
Provider Change Request → HealthcareFacility.PRM_Active__c = false
        ↓
App Review opens for the same practitioner's in-flight case
        ↓
PRM_ReviewPSVCaseRecordsUpdate runs
        ↓
PRMDREGetPracticeLocation: EligibleForUpdate formula fires
  (COUNTQUERY finds HCPF where PRM_Pending__c=true AND HealthcareFacility.PRM_Active__c=false)
  → EligibleForUpdate = true  ← FALSE POSITIVE
        ↓
PRMDRPPractitionerDataUpdate runs:
  Active=false, Error=true, Pending=false
  → Tries to update the in-flight HCPF with PRM_IsErrorRecord__c=true
  → REQUIRED FIELDS MISSING ERROR (linked HealthcareFacility is inactive)
```

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRMDREGetPracticeLocation`** | DataRaptor Extract | Update `EligibleForUpdate` formula to add a case-ownership guard: only return `true` if the HCPF's `PRM_CaseManager__c` does NOT match the current case's `IndividualApplicationId`. If `PRM_CaseManager__c = currentIndividualAppId`, the record is owned by this case and still in active credentialing — do NOT flag it as deleted. |
| **`PRM_ReviewPSVCaseRecordsUpdate`** (v23) | Integration Procedure | Add an If-Else Conditional Block before the `PRMDRPPractitionerDataUpdate` step: check if `PRMDREGetPracticeLocation:EligibleForUpdate = true` AND the HCPF has `PRM_CaseManager__c != currentCaseManagerId`. If the HCPF belongs to the current case (same `PRM_CaseManager__c`), route to a new **Bypass Path** that surfaces a warning to the user instead of marking the record as an error. |
| **New Warning Element in App Review OmniScript** | OmniScript Text Block / Set Errors | When a practice location is found to be externally terminated (belongs to current case, `HealthcareFacility.PRM_Active__c = false`, `PRM_CaseManager__c = currentIndividualAppId`), display a non-blocking informational message: *"One or more practice locations were terminated via a Provider Change Request. The credentialing review will continue. The location will be evaluated for reactivation at the PDA stage."* |
| **`PRMDRGetPractionerPracticeLocation`** (Admitting Privileges) | DataRaptor Extract — Review | Confirm that Filter Group 0 (`PRM_CaseManager__c = CaseManagerId`) correctly scopes admitting privilege HCPF records to the current case. No change expected if the filter already limits to the current case. Verify that the DR does not inadvertently load HCPF records from other cases. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDREGetPracticeLocation` | DR Extract | `PPL` (includes `PRM_CaseManager__c`, `HealthcareFacilityId`) | `Facility:EligibleForUpdate` | **Modify `EligibleForUpdate` formula** — add `AND PRM_CaseManager__c != currentIndividualAppId` guard to the COUNTQUERY (or add a second formula that checks case ownership before returning true) |
| `PRM_ReviewPSVCaseRecordsUpdate` v23 | IP | `PRMDREGetPracticeLocation:EligibleForUpdate`, `currentCaseManagerId` | Routes to `PRMDRPPractitionerDataUpdate` or new Bypass Path | **Add conditional branch** before `PRMDRPPractitionerDataUpdate`: if `EligibleForUpdate=true` AND HCPF belongs to current case, redirect to Bypass Path instead of error-marking path |
| **New IP step: `WarnTerminatedLocationBypass`** | IP Set Values / Response Action | `TerminatedLocationCount`, `TerminatedLocationNames` | Warning payload to OmniScript | New step that sets a warning flag for the OmniScript to display non-blocking message |

### Recommended Formula Update for `EligibleForUpdate` in `PRMDREGetPracticeLocation`

**Current formula:**
```
IF(COUNTQUERY("SELECT Count() FROM HealthcarePractitionerFacility
  WHERE HealthcareFacilityId = '{0}'
  AND PRM_Pending__c = true
  AND HealthcareFacility.PRM_Active__c = false",
  %HealthcarePractitionerFacility:HealthcareFacilityId%) == 1, true, false)
```

**Proposed formula:**
```
IF(COUNTQUERY("SELECT Count() FROM HealthcarePractitionerFacility
  WHERE HealthcareFacilityId = '{0}'
  AND PRM_Pending__c = true
  AND HealthcareFacility.PRM_Active__c = false
  AND PRM_CaseManager__c != '{1}'",
  %HealthcarePractitionerFacility:HealthcareFacilityId%,
  %currentIndividualAppId%) == 1, true, false)
```

> **Note:** `currentIndividualAppId` must be passed into the DR as a new input parameter. The calling IP (`PRM_ReviewPSVCaseRecordsUpdate`) must pass `IndividualApplicationId` (or `CaseManagerId`) when invoking this DR.

### Alternative Approach (If Formula Change Is Not Feasible)

If the COUNTQUERY cannot be extended with an additional bind variable, add the guard at the IP level:

```
In PRM_ReviewPSVCaseRecordsUpdate, before calling PRMDRPPractitionerDataUpdate:

Step: CheckTerminatedLocationOwnership
  Type: If/Else Conditional
  Condition: %PRMDREGetPracticeLocation:Facility:EligibleForUpdate% == "true"
             AND %PRMDREGetPLToPractitioner:PracticeToPracticeLocation:PRM_CaseManager__c% == %RecordsToUpdate:CaseManagerID%
  If TRUE → Route to WarnTerminatedLocationBypass (skip error-marking)
  If FALSE → Route to PRMDRPPractitionerDataUpdate (existing deletion path)
```

---

## Acceptance Criteria

**Scenario 1 — Happy Path: App Review completes when location terminated via Provider Change (UC-2)**

**Given** a practitioner's PAR case is in the App Review stage (`HCPF.PRM_Pending__c = true`, `HCPF.PRM_CaseManager__c = currentIndividualAppId`),
**AND** the practice location was terminated via Provider Change after the PAR was submitted (`HealthcareFacility.PRM_Active__c = false`),
**When** the credentialing specialist completes the App Review and submits,
**Then** the `PRM_ReviewPSVCaseRecordsUpdate` IP does NOT mark those HCPF records as `PRM_IsErrorRecord__c = true` or `PRM_Pending__c = false`,
**AND** the App Review completes without a "Required Fields Missing" error,
**AND** the case advances to the next stage (PSV Review).

---

**Scenario 2 — Warning displayed for terminated location**

**Given** the App Review detects that a submitted practice location has `HealthcareFacility.PRM_Active__c = false` and `HCPF.PRM_CaseManager__c = currentIndividualAppId`,
**When** the credentialing specialist is on the App Review submit step,
**Then** a non-blocking informational message is displayed: *"One or more practice locations were terminated via a Provider Change Request. The credentialing review will continue. The location will be evaluated for reactivation at the PDA stage."*,
**AND** the specialist can still proceed to submit the App Review.

---

**Scenario 3 — Intentional removal in App Review still works (regression)**

**Given** a credentialing specialist intentionally removes a practice location during App Review (the user marks it for removal),
**When** the specialist submits the App Review,
**Then** the removed location's HCPF record IS correctly marked `Active=false, Error=true, Pending=false` (existing behavior preserved),
**AND** `PRMDRPPractitionerDataUpdate` runs normally for the intentionally removed location.

---

**Scenario 4 — Active locations are not affected (regression)**

**Given** a practitioner's PAR case has two practice locations, one active and one terminated via Provider Change,
**When** the App Review is submitted,
**Then** the active location's HCPF record is updated normally (reviewed, not deleted),
**AND** the terminated location's HCPF record is NOT marked as an error record,
**AND** both locations remain associated with the case (`PRM_CaseManager__c = currentIndividualAppId`).

---

**Scenario 5 — Admitting privileges fetch by CaseManager is not affected (regression)**

**Given** a practitioner has admitting privilege HCPF records (`RecordType = PRM_AdmittingPrivileges`),
**When** `PRMDRGetPractionerPracticeLocation` is called during App Review with `CaseManagerId`,
**Then** only admitting privilege records for the current case are returned (no records from other cases or other record types),
**AND** no error is triggered by admitting privilege records where the associated facility was externally terminated.

---

**Scenario 6 — Case advances to PSV after App Review with externally-terminated location**

**Given** Scenario 1 above (App Review completes without error for terminated location),
**When** the case moves to the PSV Review stage,
**Then** the PSV Review displays the terminated practice location with a status indicator: *"Location currently inactive — pending reactivation at PDA stage."*,
**AND** the PSV reviewer can still review and verify other data (license, education, etc.) without being blocked by the inactive location.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | In `PRM_ReviewPSVCaseRecordsUpdate` v23, what is the `RA_GetDeletedData` step exactly? Does it get ONLY the practice locations the user explicitly removed in the App Review UI, or does it also include locations where `HealthcareFacility.PRM_Active__c = false`? This determines whether the bug is in `RA_GetDeletedData` or in `PRMDREGetPracticeLocation`. | Determines the precise fix location — IP step vs. DR formula | Technical |
| 2 | Can the `PRMDREGetPracticeLocation` COUNTQUERY be extended with a second bind variable for `currentIndividualAppId`? OmniStudio DataRaptor COUNTQUERY formula syntax must be verified. | Determines whether the DR formula fix is feasible or whether the guard must be added at the IP level | Technical |
| 3 | When the App Review encounters a terminated location that is NOT intentionally removed, should the HCPF record's `HealthcareFacilityId` be preserved (pointing to the now-terminated `HealthcareFacility`)? Or should the App Review use a placeholder/null until PDA reactivation? | Affects data integrity of the HCPF record during the in-between state | BA / Technical |
| 4 | Is there an existing field on `HealthcarePractitionerFacility` or `IndividualApplication` that tracks whether a location was "terminated by Provider Change" vs. "removed in App Review"? If so, this can be used as the discriminator instead of the case-ownership check. | Could simplify the fix if a dedicated flag already exists | Technical |
| 5 | During PSV, QC, and Committee Review, do those flows also query HCPF records by `HealthcareFacility.PRM_Active__c`? If yes, they may have the same blocking issue and need the same guard. Verify which downstream flows use `PRMDREGetPracticeLocation` or similar queries. | Blast radius — may require the same fix in PSV, QC, Committee IPs | Technical |
| 6 | What is the expected behavior at PDA Review when the location is to be reactivated? Is there a specific PDA step that sets `HealthcareFacility.PRM_Active__c = true` back, and does that step require the HCPF to have `PRM_Pending__c = true` (which is why we must NOT set it to false prematurely)? | Confirms that preserving `PRM_Pending__c = true` through App Review is the correct approach | BA / Technical |
| 7 | Should the non-blocking warning in Scenario 2 be surfaced as an OmniScript `Set Errors` (warning severity) element, or as a Text Block with conditional display? | UX implementation approach for the warning | BA / UX |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMDREGetPracticeLocation` | DataRaptor Extract | HIGH | Core formula change to `EligibleForUpdate` — must be tested for all location-deletion scenarios |
| `PRM_ReviewPSVCaseRecordsUpdate` v23 | Integration Procedure | HIGH | New conditional branch before the error-marking step; must preserve existing intentional-removal behavior |
| `PRMDRPPractitionerDataUpdate` | DataRaptor Post | LOW | No change; just guarded by a new condition in the calling IP |
| `PRMDREGetPLToPractitioner` | DataRaptor Extract | LOW | Read-only review to confirm no independent active/pending filter; no change expected |
| `PRMDRGetPractionerPracticeLocation` | DataRaptor Extract | LOW | Admitting privilege path — confirm CaseManagerId filter correctly scopes to current case; verify no regression |
| `PRM_InitialCredentialAppReview_English` v28 | OmniScript | MEDIUM | New warning Text Block / Set Errors element for terminated-but-in-flight location scenario |
| PSV, QC, Committee Review IPs | Integration Procedure | MEDIUM | Must audit each downstream flow's DR calls for the same `HealthcareFacility.PRM_Active__c` false-positive pattern |
| `HealthcarePractitionerFacility` trigger (`PRM_HealthcarePractitionerFacilityTrigger`) | Apex Trigger | LOW | Verify the trigger does not re-fire validation logic that causes required-field errors when App Review attempts to update HCPF records for terminated locations |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRMDREGetPracticeLocation` — update `EligibleForUpdate` formula with case-ownership guard | DR formula change | M | Read current formula; verify COUNTQUERY syntax supports second bind variable; test in sandbox |
| `PRM_ReviewPSVCaseRecordsUpdate` v23 — add If/Else conditional before `PRMDRPPractitionerDataUpdate` | IP conditional block | M | Add `PRM_CaseManager__c` check; map new `WarnTerminatedLocationBypass` path |
| `PRM_InitialCredentialAppReview_English` v28 — add non-blocking warning element | OmniScript Text Block + conditional show | S | Conditional display when `TerminatedLocationWarning = true` |
| Audit downstream flows (PSV, QC, Committee IPs) for same pattern | Investigation + fixes | L | Each flow may have its own `PRMDREGetPracticeLocation` call; apply same guard pattern |
| `PRMDRGetPractionerPracticeLocation` — review CaseManagerId scoping | Investigation | S | Read DR XML; confirm no regression risk |
| Regression testing — 6 AC scenarios × 3 location types (active / externally terminated / intentionally removed) | QA | L | Full matrix across App Review + PSV entry validation |

**Total Estimated Effort:** AI-estimated — validate with team — **XL** (formula change + IP branch + downstream flow audit + regression suite)

---

## Story Dependencies

| Story | Depends On | Blocks |
|-------|-----------|--------|
| **US4 (this story)** — App Review guard for externally-terminated locations | None — standalone fix | PSV / QC / Committee guards (same pattern should be applied to downstream flows once App Review fix is validated) |
| **US1** (PAR_DeniedTerminated — IP routing for denied/terminated reuse) | None | US4 is independent but complementary |
| **US3** (PAR_DeniedTerminated — clear ExternalId on denial) | None | US4 is independent |

**Recommended Implementation Order:**
1. **US4 (this story)** — Unblock the immediate production error; P0
2. Audit and apply the same guard to PSV, QC, Committee Review IPs
3. US3 (clear External ID on denial — prevents accumulation of new stale IDs)
4. US1 (IP routing for resubmission path)

---

## Appendix: Key DataRaptor Filter Summary

| DR Name | Object Queried | Key Filter | Used For | Gap |
|---------|---------------|-----------|---------|-----|
| `PRMDREGetPracticeLocation` | `HealthcarePractitionerFacility` | `HealthcareFacility.PRM_Active__c = false` | Detect "deleted" locations in App Review | Also catches externally-terminated locations — no case-ownership check |
| `PRMDREGetPLToPractitioner` | `HealthcarePractitionerFacility` | `AccountId = PPL:AccountId`, `Id = PPL:HCPFId` | Fetch practice-to-practitioner and practice-to-location HCPF records | No `PRM_Pending__c` filter — returns in-flight records |
| `PRMDRGetPractionerPracticeLocation` | `HealthcarePractitionerFacility` | `PRM_CaseManager__c = CaseManagerId` (Group 0) OR `PractitionerId = PractitionerId` (Group 1) | Fetch admitting privileges for App Review | Only admitting privileges (RecordType = `PRM_AdmittingPrivileges`) — confirm scoping |

---

*End of Document*
