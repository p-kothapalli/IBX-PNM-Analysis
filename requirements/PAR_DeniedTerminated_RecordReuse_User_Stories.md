# PAR Form — Denied & Terminated Practitioner Re-Submission: Record Reuse User Stories

**Document Version:** 1.0
**Created Date:** April 16, 2026
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_PractitionerParticipationForm_English`
**Related Documents:**
- `PAR_Form_PNC_Path_User_Stories.md`
- `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`

---

## Executive Summary

Three user stories address the root causes of duplicate record errors when a previously denied or terminated practitioner resubmits a New Practitioner Participation (PAR) request.

**The core problem:** When a PAR request is denied (or a practitioner is terminated), the related `HealthcarePractitionerFacility` (HCPF) records are set to `PRM_Pending__c = false` and `IsActive = false`. On resubmission, the system collides with these orphaned records in two distinct ways:

1. **DR routing gap** — `PRMDRCheckIfPracticeToPractitionerExist` correctly sets `Update = true` for denied/terminated records, but the consuming IPs (`PRM_ExistingPrimaryPracticeLocationLogic_English`, `PRM_PractitionerAddressCreation`) may not route the update path consistently, causing the OS to surface a duplicate error.
2. **PAR form UX gap** — The group search on the PAR form does not present denied/terminated HCPF records as selectable/editable; the user cannot indicate intent to reuse them.
3. **External ID staleness** — On denial/closure, the `ExternalId` (Source System ID) on HCPF and related records is not cleared. Future requests that build the same composite key collide with the stale External ID even if the record was legitimately denied.

---

## Use Case Matrix

| # | Scenario | Pending | Active | Expected System Behavior |
|---|----------|---------|--------|--------------------------|
| UC-1 | Active participation in progress | true | false | Skip (hard block — already in progress) |
| UC-2 | Active, effective participation | N/A | true | Skip (hard block — already active) |
| UC-3 | **Denied request resubmission** | **false** | **false** | **Reuse record (Update = true path)** |
| UC-4 | **Terminated practitioner reapplying** | **false** | **false** | **Reuse record (Update = true path)** |
| UC-5 | Error record from prior failed run | false | false | `PRM_IsErrorRecord__c = true` — create new, skip error record |

---

---

# USER STORY 1: PAR Form Group Search — Surface and Enable Reuse of Denied/Terminated Practice-to-Practitioner Records

**Persona:** Sr. Data Reporting Analyst, Developer
**Priority:** P0
**OmniScript:** `PRM_PractitionerParticipationForm_English` (v112)
**Integration Procedures:** `PRM_ExistingPrimaryPracticeLocationLogic_English`, `PRM_PractitionerAddressCreation`, `PRM_CreateParFormRecords`
**DataRaptors:** `PRMDRCheckIfPracticeToPractitionerExist`, `PRMUpdatePracticeToPractitioner`
**Relevant Requirements:** Use Cases UC-3, UC-4 above; `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`

---

## Story

**As a** Sr. Data Reporting Analyst submitting a New Practitioner Participation request,
**I want** the PAR form's group/practice location search to display previously denied or terminated records as selectable (editable) options and route them through the update path instead of a duplicate block,
**So that** I can resubmit a participation request for a denied or terminated practitioner without hitting a "duplicate record" error and without requiring manual admin data correction.

**Why it matters:** Denied and terminated cases are a normal part of the credentialing lifecycle. Every resubmission currently requires a manual intervention by a Salesforce admin to clear the stale HCPF record state before the form can proceed, creating significant operational overhead and delay in the credentialing workflow.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR (Practitioner Participation) | `PRM_PractitionerParticipationForm_English` | `PractionerGroup` + `PracticeLocations` | `PRMDRCheckIfPracticeToPractitionerExist` → `PRM_ExistingPrimaryPracticeLocationLogic_English` → `PRMUpdatePracticeToPractitioner` |

---

## Current State (from codebase)

### `PRMDRCheckIfPracticeToPractitionerExist` (DataRaptor Extract)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDRCheckIfPracticeToPractitionerExist_1.rpt-meta.xml`
- **Query:** `HealthcarePractitionerFacility` WHERE `AccountId = Locations:Id` AND `PractitionerId = PractitionerId` AND `RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'`
- **`Skip` formula:**
  ```
  IF(HCPF:IsActive || (HCPF:IsActive == false && HCPF:PRM_Pending__c == true), true, false)
  ```
  - Skip = `true` when record is **active** OR when record is **inactive but still pending**
  - Skip = `false` for denied/terminated records (`IsActive=false`, `Pending=false`) → record IS returned in output
- **`Update` formula:**
  ```
  IF((HCPF:IsActive == false && HCPF:PRM_IsErrorRecord__c == false && HCPF:PRM_EffectiveToday__c == false), true, false)
  ```
  - Update = `true` for denied/terminated records where `IsErrorRecord = false` and `EffectiveToday = false`
  - **The DR correctly identifies denied/terminated records as candidates for update.** The gap is in the consuming IP.

### `PRM_ExistingPrimaryPracticeLocationLogic_English` (Integration Procedure)

- **Location:** `force-app/main/default/omniIntegrationProcedures/PRM_ExistingPrimaryPracticeLocationLogic_English_4.oip-meta.xml`
- **Called by:** `PRM_PractitionerAddressCreation` (procedures 1, 2, 3) and `PRM_CreatePractitionerAddressRecords` (procedures 39, 40)
- **Calls:** `PRMDRCheckIfPracticeToPractitionerExist`
- **Gap:** Logic after the DR needs to be confirmed: when `Skip = false` AND `Update = true`, the IP must route to `PRMUpdatePracticeToPractitioner` (the load DR). If instead it routes to an error/block path, denied/terminated records trigger a duplicate error.

### `PRMUpdatePracticeToPractitioner` (DataRaptor Load)

- **Location:** `force-app/main/default/omniDataTransforms/PRMUpdatePracticeToPractitioner_1.rpt-meta.xml`
- **Action:** Updates existing HCPF record with:
  - `PRM_Pending__c = true` (re-activates pending state)
  - `PRM_CaseManager__c = IndividualAppId` (links new case manager)
  - `EffectiveTo = null` (clears termination date)
  - `RecordTypeId = PRM_PractitionerPracticeAffiliation`
- **Note:** `EffectiveFrom` mapping is currently **disabled** (`<disabled>true</disabled>`) — the effective from date is NOT being re-set when a record is reused.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_ExistingPrimaryPracticeLocationLogic_English`** (v4) | Integration Procedure | Verify the conditional block after `PRMDRCheckIfPracticeToPractitionerExist`: if `HCPF:Skip == false AND HCPF:Update == true`, route to `PRMUpdatePracticeToPractitioner`. If a duplicate-error response action fires when `Skip=false` without checking `Update`, add an If/Else Conditional Block to split the two paths. |
| **`PRMUpdatePracticeToPractitioner`** | DataRaptor Load | Re-enable the `EffectiveFrom` mapping item (currently `<disabled>true</disabled>`). Map `EffectiveFrom = EffectiveDate` input field so the new effective date is written when reusing the record. |
| **`PRM_PractitionerAddressCreation`** (v3) | Integration Procedure | Confirm it passes `IndividualAppId` and `EffectiveDate` downstream so `PRMUpdatePracticeToPractitioner` can correctly set `PRM_CaseManager__c` and `EffectiveFrom` on the reused record. |
| **`PRM_CreateParFormRecords`** (v29) | Integration Procedure | Confirm that when `ExistingPrimaryPracticeLocationLogic` returns `Update=true` for a practice location, the parent IP skips the "create new HCPF" path and routes to the "update existing HCPF" path only. |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRCheckIfPracticeToPractitionerExist` | DR Extract | `Locations:Id` (AccountId), `PractitionerId` | `HCPF:Skip`, `HCPF:Update`, `HCPF:HCPFID`, `HCPF:IsActive`, `HCPF:PRM_Pending__c` | No change to DR; confirm output values pass correctly to parent IP |
| `PRMUpdatePracticeToPractitioner` | DR Load | `UpdateList:HCPFID`, `IndividualAppId`, `EffectiveDate` | Updates `HealthcarePractitionerFacility` | Re-enable `EffectiveFrom` field mapping; confirm `EffectiveTo` is explicitly cleared to null |
| `PRM_ExistingPrimaryPracticeLocationLogic_English` | IP | `HCPF:Skip`, `HCPF:Update`, `HCPF:HCPFID` | `UpdateList` (list of HCPFIDs to update) | Add/verify If-Else branch: `IF Update == true → add HCPFID to UpdateList; ELSE IF Skip == false → fire duplicate error` |

### Routing Logic Target State

```
PRMDRCheckIfPracticeToPractitionerExist result per location:
  ├─ Skip = true                      → Duplicate block (active or pending-in-progress)
  ├─ Skip = false AND Update = true   → Route to PRMUpdatePracticeToPractitioner (REUSE path)
  └─ Skip = false AND Update = false  → Error record; create new HCPF record
```

---

## Acceptance Criteria

**Scenario 1 — Happy Path: Denied practitioner resubmits (UC-3)**

**Given** a practitioner previously had a PAR request denied (HCPF: `IsActive=false`, `PRM_Pending__c=false`, `PRM_IsErrorRecord__c=false`),
**When** the Sr. Data Reporting Analyst enters the same NPI + Tax ID on the PAR form and selects the same group,
**Then** the system does NOT surface a duplicate record error,
**AND** the existing HCPF record is updated via `PRMUpdatePracticeToPractitioner`: `PRM_Pending__c=true`, `PRM_CaseManager__c=<new case Id>`, `EffectiveFrom=<new effective date>`, `EffectiveTo=null`,
**AND** the form proceeds to the next step normally.

---

**Scenario 2 — Happy Path: Terminated practitioner reapplying (UC-4)**

**Given** a practitioner was previously terminated (HCPF: `IsActive=false`, `PRM_Pending__c=false`),
**When** the analyst enters the same NPI + Tax ID and selects the same group on a new PAR form,
**Then** the system routes to the REUSE path (not the create-new path),
**AND** the HCPF record is updated with the new case manager and effective dates,
**AND** no duplicate error is shown.

---

**Scenario 3 — Block preserved: Active participation (UC-2)**

**Given** a practitioner has an active HCPF record (`IsActive=true`) for the same group,
**When** the analyst attempts to submit a new PAR for the same practitioner + group,
**Then** `PRMDRCheckIfPracticeToPractitionerExist` sets `Skip=true`,
**AND** the form surfaces the existing duplicate error/block message (no regression).

---

**Scenario 4 — Block preserved: In-progress pending request (UC-1)**

**Given** a practitioner has a pending (in-progress) HCPF record (`IsActive=false`, `PRM_Pending__c=true`),
**When** the analyst attempts to submit a new PAR for the same practitioner + group,
**Then** `Skip=true` is set and the duplicate error is shown (no regression).

---

**Scenario 5 — Error record: Create new (UC-5)**

**Given** a practitioner has an HCPF record where `PRM_IsErrorRecord__c=true` (a prior failed run),
**When** the analyst submits a new PAR for the same practitioner + group,
**Then** `Update=false` is set for the error record,
**AND** a new HCPF record is created (bypassing the error record),
**AND** no duplicate error is shown.

---

**Scenario 6 — Effective date is set on reuse**

**Given** a denied HCPF record is being reused via `PRMUpdatePracticeToPractitioner`,
**When** the analyst enters a new effective date on the PAR form,
**Then** the reused HCPF record's `EffectiveFrom` is updated to the new date entered,
**AND** `EffectiveTo` is cleared to null.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | In `PRM_ExistingPrimaryPracticeLocationLogic_English` v4, what is the current conditional after the `PRMDRCheckIfPracticeToPractitionerExist` call? Does it check `HCPF:Update` before firing a duplicate response, or does any `Skip=false` result go to a block? | Determines whether the IP needs a new branch or just a condition fix | Technical |
| 2 | The `EffectiveFrom` mapping in `PRMUpdatePracticeToPractitioner` is disabled. Was this intentional? If re-enabled, what input key must the IP provide (is it `EffectiveDate` or something else from the PAR form data JSON)? | Required to correctly set effective date on reused HCPF records | Technical |
| 3 | When a HCPF record is reused (Update path), should the `PRM_TerminationDate__c` field be explicitly cleared to null in `PRMUpdatePracticeToPractitioner`? | Prevents stale termination date from showing on reactivated records | BA / Technical |
| 4 | Is there a separate duplicate check inside `PRM_CreateParFormRecords` (v29) that fires before `PRM_ExistingPrimaryPracticeLocationLogic_English` is called? If so, does it also need the same `Update` routing logic? | Determines scope of IP changes | Technical |
| 5 | For the terminated reapplication scenario: when a practitioner terminates, is the HCPF record set to `IsActive=false` and `PRM_Pending__c=false` via the same IP/flow as denials? Confirm the field update path for termination vs. denial to ensure this story covers both. | Confirms UC-4 shares same record state as UC-3 | BA / Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_ExistingPrimaryPracticeLocationLogic_English` v4 | Integration Procedure | HIGH | Core routing IP; must add/verify Update=true branch to avoid duplicate error |
| `PRMDRCheckIfPracticeToPractitionerExist` | DataRaptor Extract | LOW | No change needed; formulas correctly compute Skip and Update flags |
| `PRMUpdatePracticeToPractitioner` | DataRaptor Load | MEDIUM | Re-enable EffectiveFrom mapping; confirm EffectiveTo null-clear |
| `PRM_PractitionerAddressCreation` v3 | Integration Procedure | MEDIUM | Confirm IndividualAppId and EffectiveDate are passed through correctly |
| `PRM_CreateParFormRecords` v29 | Integration Procedure | MEDIUM | Confirm parent IP does not independently block when Update=true is downstream |
| `PRM_PractitionerParticipationForm_English` v112 | OmniScript | LOW | No OS-level change expected if IP routing is corrected |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_ExistingPrimaryPracticeLocationLogic_English` v4 — add Update branch | IP conditional block | M | Read current logic; add If-Else condition; test 5 routing combinations |
| `PRMUpdatePracticeToPractitioner` — re-enable EffectiveFrom, verify EffectiveTo null | DR Load config | S | Re-enable one disabled mapping item; add EffectiveTo null mapping |
| `PRM_PractitionerAddressCreation` v3 — trace IndividualAppId/EffectiveDate | IP review | S | Confirm data pass-through; no change if already present |
| `PRM_CreateParFormRecords` v29 — confirm no secondary block | IP review | S | Read-only review; fix if block found |
| Regression testing (5 AC scenarios × 2 use cases) | QA | L | Full matrix: Active/Pending/Denied/Terminated/Error × same-group / new-group |

**Total Estimated Effort:** AI-estimated — validate with team — **L** (primarily testing and IP logic review)

---

---

# USER STORY 2: PAR Form — Show Denied/Terminated Practice Location Records in Group Search with Edit Capability

**Persona:** Sr. Data Reporting Analyst, Developer
**Priority:** P0
**OmniScript:** `PRM_PractitionerParticipationForm_English` (v112)
**Integration Procedures:** `PRM_FetchExistingNPIInfo`, `PRM_IPExtractGroupNameBasedOnTINNPI` (group type-ahead)
**DataRaptors:** `PRMDREGetPLToPractitioner`, `PRMDRExtractPracLocNetworkandPracticeToPractitioner`
**Relevant Requirements:** Use Cases UC-3, UC-4 above; AC1 notes (show Pending=false/Active=false records; allow edit; validate Case Manager and effective dates)

---

## Story

**As a** Sr. Data Reporting Analyst submitting a New Practitioner Participation request,
**I want** the PAR form's existing group and practice location search results to include previously denied or terminated records (where `PRM_Pending__c=false` AND `IsActive=false`), and to allow me to select and edit those records as the basis for the new request,
**So that** I can clearly see the full history of the practitioner's participation and choose to reuse a prior record — confirming the Case Manager and effective dates — rather than creating a confusing "invisible" record collision.

**Why it matters:** Currently, when a denied/terminated HCPF record exists, the system silently collides with it during form submission. Surfacing these records in the search UI gives the analyst transparency and explicit intent to reuse, which also satisfies audit requirements for knowing when a record was re-activated from a prior denied state.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PAR | `PRM_PractitionerParticipationForm_English` v112 | `PractionerGroup` (Step 2) + Practice Location lookup steps | Group type-ahead via `PRM_IPExtractGroupNameBasedOnTINNPI`; existing locations via `PRMDREGetPLToPractitioner` / `PRMDRExtractPracLocNetworkandPracticeToPractitioner` |

---

## Current State (from codebase)

### Group Search — `PractionerGroup` Step

- The `GroupTypeAhead` type-ahead in `PractionerGroup` calls `PRM_IPExtractGroupNameBasedOnTINNPI` passing `NPI`, `TaxId`, and `IsPNC` flags.
- This IP returns groups matching the NPI/TaxId. It likely filters for groups with active HCPF relationships. **Confirm whether the IP excludes groups that only have denied/terminated HCPF records.**
- If the IP filters `IsActive=true` on the HCPF sub-query, denied/terminated groups will not appear in search results → analyst cannot select them to reuse.

### Practice Location Display — `PracticeLocations` Step

- After the group is selected, the OmniScript loads existing practice locations for the practitioner-group pair.
- The DR `PRMDREGetPLToPractitioner` (or `PRMDRExtractPracLocNetworkandPracticeToPractitioner`) fetches these records.
- **Current behavior:** If these DRs filter on `IsActive=true` or `PRM_Pending__c=true`, denied/terminated practice-to-practitioner records will not be displayed → analyst cannot see or select prior denied locations.
- **Required behavior:** Records with `PRM_Pending__c=false AND IsActive=false` must appear in the results, flagged visually as "Previously Denied" or "Previously Terminated", with an **Edit** / **Select to Reuse** action available.

### Effective Dates and Case Manager Validation

- When an analyst selects a denied/terminated record for reuse, the form must require:
  1. A new **Effective Date** (cannot be blank or the original denied date)
  2. A new **Case Manager** (linked `IndividualApplication` Id) — or confirm the current one is correct
- These validations do not currently exist because the reuse path is not exposed to the analyst.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_IPExtractGroupNameBasedOnTINNPI`** | Integration Procedure | Verify the SOQL/DR query for group records: if `HealthcarePractitionerFacility.IsActive = true` is a filter, broaden to also return groups where `IsActive=false AND PRM_Pending__c=false`. Return a `ReusableRecord` flag (`true` when `IsActive=false AND PRM_Pending__c=false`) in the type-ahead response so the OmniScript can render it differently. |
| **`PRMDREGetPLToPractitioner`** | DataRaptor Extract | Add or loosen filter to include `PRM_Pending__c=false AND IsActive=false` records. Add output field `PRM_RecordStatus__c` (or derived formula: `IF(IsActive, 'Active', IF(PRM_Pending__c, 'Pending', 'Denied/Terminated'))`) so the OmniScript can conditionally show an Edit button. |
| **`PractionerGroup` step** (OmniScript) | OmniScript Type Ahead Block | Update `GroupTypeAhead` result display template: when `ReusableRecord=true`, show a secondary label "Previously Denied/Terminated — Select to Reuse" alongside the group name. |
| **Practice Locations display** (OmniScript) | OmniScript Block / Text Block | Add conditional `Edit` button on denied/terminated location rows. Button visible only when `PRM_Pending__c=false AND IsActive=false`. Clicking Edit routes to the effective date + case manager validation section. |
| **New Validation — Effective Date on Reuse** | OmniScript Validation Element | When a denied/terminated record is selected for reuse, add a `Required` validation on the `EffectiveDate` field. Add a `Set Errors` element that fires if `EffectiveDate <= today` (effective date must be today or future). |
| **New Validation — Case Manager on Reuse** | OmniScript Validation Element | When a denied/terminated record is selected for reuse, validate that `IndividualAppId` (Case Manager reference) is not blank. Display error: "Please confirm or update the Case Manager before reactivating this record." |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRM_IPExtractGroupNameBasedOnTINNPI` | IP (type-ahead) | `NPI`, `TaxId`, `IsPNC` | Group records + `ReusableRecord` flag | Add `IsActive=false AND PRM_Pending__c=false` to HCPF join; return `ReusableRecord` boolean in response |
| `PRMDREGetPLToPractitioner` | DR Extract | `PractitionerId`, `AccountId` | HCPF records | Remove/loosen `IsActive=true` filter; add derived `RecordStatus` output field |
| New `SetValues` element — Reuse Intent | OmniScript Set Values | User selects denied record | Sets `IsReusingDeniedRecord=true`, `SelectedHCPFId`, `SelectedHCPFStatus` in OS data JSON | New element in PracticeLocations step |

### Example: Reuse Record Selection State

```json
{
  "IsReusingDeniedRecord": true,
  "SelectedHCPFId": "a1X...",
  "SelectedHCPFStatus": "Denied/Terminated",
  "EffectiveDate": "<required — entered by analyst>",
  "CaseManagerId": "<required — confirmed or updated by analyst>"
}
```

---

## Acceptance Criteria

**Scenario 1 — Denied group appears in type-ahead results**

**Given** a practitioner has a prior denied PAR request for Group A (HCPF: `IsActive=false`, `PRM_Pending__c=false`),
**When** the analyst enters the Tax ID + NPI and types Group A's name in the type-ahead,
**Then** Group A appears in the suggestion list,
**AND** it is labeled/flagged as "Previously Denied/Terminated — Select to Reuse",
**AND** it is selectable by the analyst.

---

**Scenario 2 — Denied practice location shows Edit button**

**Given** a denied HCPF record exists for the selected practitioner-group pair,
**When** the practice locations list is rendered in the OmniScript,
**Then** the denied/terminated location row is visible in the list,
**AND** an "Edit / Reuse" button is visible on that row (not shown for Active or Pending records),
**AND** Active/Pending records continue to display as read-only (no regression).

---

**Scenario 3 — Effective date validation on reuse**

**Given** the analyst clicks "Edit / Reuse" on a denied location record,
**When** the analyst attempts to proceed without entering a new effective date,
**Then** a Required validation fires: "Effective Date is required when reusing a previously denied/terminated record.",
**AND** the form cannot advance until a valid future or current date is entered.

---

**Scenario 4 — Case Manager validation on reuse**

**Given** the analyst has selected a denied location for reuse and entered an effective date,
**When** the analyst attempts to proceed with no Case Manager linked,
**Then** a validation error fires: "Please confirm or update the Case Manager before reactivating this record.",
**AND** the form cannot advance until a Case Manager (IndividualApplication) is confirmed.

---

**Scenario 5 — Active records are not affected**

**Given** a practitioner has both an active HCPF record and a denied HCPF record for different groups,
**When** the practice locations list renders,
**Then** the active record displays without an Edit/Reuse button (read-only, no change),
**AND** only the denied record shows the Edit/Reuse button.

---

**Scenario 6 — In-progress pending records are not editable**

**Given** a practitioner has an in-progress HCPF record (`IsActive=false`, `PRM_Pending__c=true`),
**When** the practice locations list renders,
**Then** the pending record displays as read-only (no Edit/Reuse button),
**AND** a label "Credentialing in Progress" is shown (or existing pending indicator, no regression).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Does `PRM_IPExtractGroupNameBasedOnTINNPI` currently filter the HCPF sub-query on `IsActive=true`? If so, denied groups are invisible in the type-ahead. Confirm by reading the IP's DR or SOQL step. | Determines whether IP change is required for group search visibility | Technical |
| 2 | Which DR feeds the practice locations list on the PAR form after group selection? Is it `PRMDREGetPLToPractitioner`, `PRMDRExtractPracLocNetworkandPracticeToPractitioner`, or another? Confirm the exact DR used in the latest OS version (v112). | Determines which DR to modify for location visibility | Technical |
| 3 | Should the "Previously Denied/Terminated" label use a specific visual treatment (e.g., a warning icon, different text color, badge)? Or a plain text label? | UX fidelity of the denied record indicator | BA / UX |
| 4 | When the analyst confirms reuse of a denied record, should the old Effective Date field be pre-populated with the original date (for reference) or left blank to force entry? | UX for the effective date field default behavior | BA |
| 5 | Is Case Manager a lookup to `IndividualApplication` or to a User/Contact? Confirm the field API name on `HealthcarePractitionerFacility` that stores the Case Manager reference (`PRM_CaseManager__c`). | Validation rule target field | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_IPExtractGroupNameBasedOnTINNPI` | Integration Procedure | HIGH | Must include denied groups in type-ahead results |
| `PRMDREGetPLToPractitioner` | DataRaptor Extract | HIGH | Must include denied/terminated HCPF records in output |
| Practice Locations display block | OmniScript Block | HIGH | New Edit/Reuse button; conditional show logic per record status |
| Effective Date validation | OmniScript Validation | MEDIUM | New required field validation triggered by reuse intent |
| Case Manager validation | OmniScript Validation | MEDIUM | New required field validation triggered by reuse intent |
| `PractionerGroup` type-ahead | OmniScript Type Ahead | MEDIUM | Display enhancement for denied group indicator |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_IPExtractGroupNameBasedOnTINNPI` — broaden HCPF filter | IP / DR change | M | Add denied record path; add ReusableRecord flag to response |
| `PRMDREGetPLToPractitioner` — loosen filter + add RecordStatus | DR Extract config | M | Add IsActive=false/Pending=false path; add derived status field |
| OmniScript — Edit/Reuse button on denied location rows | OmniScript element | M | Conditional show on button; SetValues for reuse intent |
| OmniScript — Effective Date required validation | OmniScript Validation | S | Conditional Required validation + date range check |
| OmniScript — Case Manager required validation | OmniScript Validation | S | Conditional Required validation |
| `PractionerGroup` type-ahead — denied label | OmniScript Type Ahead | S | Display template update for ReusableRecord flag |
| Regression + new scenario testing | QA | L | 6 AC scenarios + full matrix with existing active/pending paths |

**Total Estimated Effort:** AI-estimated — validate with team — **XL** (UI changes + IP/DR changes + validation layer + full regression)

---

---

# USER STORY 3: App Review Denial — Clear Source System ID on Related HCPF Records to Prevent External ID Collision on Resubmission

**Persona:** Sr. Data Reporting Analyst, Developer
**Priority:** P1
**OmniScript:** `PRM_ApplicationReview_English` (App Review close/deny flow) — confirm exact name
**Integration Procedures:** App Review denial/close IP (confirm name — likely `PRM_CloseCase_Procedure_*` or embedded in App Review OmniScript)
**DataRaptors:** DR that updates HCPF records on denial (confirm); `PRMDRCreateHealthcarePractitionerFacility`, `PRMUpdatePracticeToPractitioner`
**Relevant Requirements:** Use Case — "Error out Source System ID for Denied"; `PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md` (Root Cause A)

---

## Story

**As a** Sr. Data Reporting Analyst (and the system on behalf of the credentialing team),
**I want** the App Review denial flow to null out (clear) the Source System ID (External ID) on the related `HealthcarePractitionerFacility` records when a Practitioner Participation request is denied and closed,
**So that** a future resubmission by the same practitioner for the same group does not collide with the stale External ID and generate a false duplicate error.

**Why it matters:** The `HealthcarePractitionerFacility` External ID is a composite key built from NPI + Group + address components at creation time. When a request is denied and the HCPF record remains with `IsActive=false` / `Pending=false`, its External ID is still present. If the same practitioner resubmits, the creation DR tries to upsert using the same External ID key, finds the denied record, and either hard-blocks or silently updates the wrong record. Clearing the External ID on denial severs this stale linkage and allows clean creation on resubmission.

**Why it matters:** This is the declarative complement to Story 1 (IP routing fix). Even with the routing fix in place, the stale External ID creates a risk of silent upsert conflicts in edge cases. Clearing it on denial is low-risk and additive.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| App Review — Deny/Close | `PRM_ApplicationReview_English` (confirm) | Denial / Case Close step | IP that updates related records on denial; DR that writes HCPF fields |

---

## Current State (from codebase)

### Denial / Close Flow

- When a PAR request is denied in App Review, the related records are updated:
  - `HealthcarePractitionerFacility.IsActive = false`
  - `HealthcarePractitionerFacility.PRM_Pending__c = false`
- **Gap:** The `ExternalId` field on `HealthcarePractitionerFacility` is **not cleared** at denial. The composite key (e.g., `{NPI}-{GroupName}-{PIE}-{AddressLine1}-{Zip}-{Phone}`) remains set.
- When a new PAR submission calls `PRMDRCreateHealthcarePractitionerFacility` (or `PRMUpdatePracticeToPractitioner`) and builds the same composite External ID for the same practitioner-group-address combination, it finds the denied record via the External ID upsert key and may either:
  - Block with a duplicate error (if an explicit guard exists), OR
  - Silently update the denied record's fields (if the upsert proceeds) without properly resetting the record to Pending=true state.

### `PRMDRCreateHealthcarePractitionerFacility` (DataRaptor Load)

- **Location:** `force-app/main/default/omniDataTransforms/PRMDRCreateHealthcarePractitionerFacility_1.rpt-meta.xml`
- **Action:** Creates or upserts `HealthcarePractitionerFacility` records.
- **Upsert key:** Confirm whether this DR uses `ExternalId` as the upsert key. If yes, a denied record with the same External ID will be matched and updated (not created fresh).

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **App Review Denial IP** (confirm name) | Integration Procedure | Add a `DataRaptor Post` step **after** the existing `IsActive=false / PRM_Pending__c=false` update step. This new step executes a load DR that sets `ExternalId = null` (or a flag value) on all `HealthcarePractitionerFacility` records linked to the denied `IndividualApplication` (Case Manager). |
| **New DR: `PRMDRClearHCPFExternalIdOnDenial`** | DataRaptor Load (new) | `UPDATE HealthcarePractitionerFacility SET ExternalId = null WHERE PRM_CaseManager__c = :IndividualAppId AND IsActive = false AND PRM_Pending__c = false`. To be created and called by the denial IP. |
| **`PRMDRCreateHealthcarePractitionerFacility`** | DataRaptor Load | Confirm whether this DR uses `ExternalId` as upsert key. If yes, add a fallback: if the matched record has `IsActive=false AND PRM_Pending__c=false`, do not block — treat as a new record creation (or rely on ExternalId being null from the denial step above). |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRClearHCPFExternalIdOnDenial` (NEW) | DR Load | `IndividualAppId` (the denied case's Case Manager Id) | Updates HCPF: `ExternalId = null` | New DR; CREATE this component |
| App Review Denial IP | IP | `IndividualAppId` | Triggers `PRMDRClearHCPFExternalIdOnDenial` | Add new `DataRaptor Post` step after existing deny/close update steps |

### Example: New DR Post Step in Denial IP

```
Step: DRClearHCPFExternalIdOnDenial
  Type: DataRaptor Post Action
  Bundle: PRMDRClearHCPFExternalIdOnDenial
  Input:
    IndividualAppId: %IndividualAppId%
  Execution condition: [none — always run when denial is confirmed]
  Fail on error: false (non-blocking; log error but do not halt denial)
```

---

## Acceptance Criteria

**Scenario 1 — External ID cleared on denial**

**Given** a PAR request is denied and closed in the App Review stage,
**When** the denial IP completes and `IsActive=false`, `PRM_Pending__c=false` are set on the related HCPF records,
**Then** the `ExternalId` field on all `HealthcarePractitionerFacility` records linked to the denied `IndividualApplication` (via `PRM_CaseManager__c`) is set to `null`,
**AND** the denial confirmation screen is shown to the user (no regression to App Review UX).

---

**Scenario 2 — Resubmission creates clean record after denial**

**Given** a practitioner's prior PAR was denied and the HCPF External ID was cleared per Scenario 1,
**When** the analyst submits a new PAR for the same practitioner + group + address,
**Then** `PRMDRCreateHealthcarePractitionerFacility` (or the upsert equivalent) does NOT find a matching External ID on the denied record,
**AND** the new submission proceeds without a duplicate External ID collision,
**AND** a new (or properly updated) HCPF record is created via the Story 1 REUSE routing.

---

**Scenario 3 — Active records are not affected**

**Given** a practitioner has an active HCPF record and a separate denied HCPF record,
**When** the denial IP clears External IDs,
**Then** only the records linked to the denied `IndividualApplication` (`PRM_CaseManager__c = denied case Id`) have their External IDs cleared,
**AND** the active HCPF record's External ID is unchanged.

---

**Scenario 4 — Denial flow completes even if External ID clear step fails**

**Given** `PRMDRClearHCPFExternalIdOnDenial` encounters an error (e.g., HCPF record locked),
**When** the denial IP runs,
**Then** the denial step (`IsActive=false`, `PRM_Pending__c=false`) still completes successfully,
**AND** the error is logged (or surfaced as a non-blocking warning),
**AND** the App Review denial confirmation is shown to the user.

---

**Scenario 5 — Source System ID history visible to admin**

**Given** an admin views a denied HCPF record after the denial flow,
**When** the admin checks the record detail,
**Then** the `ExternalId` field is blank (null),
**AND** a custom field `PRM_DeniedDate__c` (if exists) or the record's Last Modified Date reflects the denial action date.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What is the exact API name of the App Review denial/close Integration Procedure? (Likely in `PRM_ApplicationReview_English` OmniScript or a dedicated close IP.) Confirm by reading the App Review OS's Save/Submit step. | Determines where to add the new DR Post step | Technical |
| 2 | Does `PRMDRCreateHealthcarePractitionerFacility` use `ExternalId` as its upsert key? If the DR uses a different upsert key (e.g., record Id), the External ID collision is via a different mechanism and the fix must target that key instead. | Confirms whether ExternalId clearing is the correct fix or if a different field is the collision source | Technical |
| 3 | The `ExternalId` field on `HealthcarePractitionerFacility` — is this Salesforce's standard `ExternalId` field or a custom field (e.g., `PRM_SourceSystemId__c`)? Confirm the API name. | Required to correctly map the field in the new DR Load | Technical |
| 4 | Should the denial flow set `ExternalId = null` or set it to a "DENIED-{timestamp}" placeholder value (to preserve audit history of the original key)? Setting null is cleaner; a placeholder preserves forensics. | Data retention / audit requirement | BA / Ops |
| 5 | Are there any downstream reports or FlexCards that query `HealthcarePractitionerFacility` by `ExternalId`? Clearing it may break those queries. | Blast radius of clearing the ExternalId | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| App Review Denial IP (confirm name) | Integration Procedure | MEDIUM | Add one new DR Post step; denial flow must remain intact |
| `PRMDRClearHCPFExternalIdOnDenial` (NEW) | DataRaptor Load | MEDIUM | New DR to create; targets HCPF records by CaseManager Id |
| `PRMDRCreateHealthcarePractitionerFacility` | DataRaptor Load | LOW | Read-only review to confirm upsert key mechanism |
| Any FlexCard / Report querying HCPF ExternalId | FlexCard / Report | LOW | Potential blast radius if ExternalId is used in downstream queries — confirm |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Identify App Review denial IP (read existing) | Investigation | S | Read App Review OmniScript Save step to find IP name |
| `PRMDRClearHCPFExternalIdOnDenial` — new DR Load | New DR | M | Simple UPDATE DR; single object, single filter, single field update |
| App Review denial IP — add DR Post step | IP config | S | One new step in existing IP; add input mapping |
| Confirm `PRMDRCreateHealthcarePractitionerFacility` upsert key | Investigation | S | Read DR XML to confirm ExternalId usage |
| Regression testing (denial + resubmission flow) | QA | M | Denial scenario + resubmission + active record protection |

**Total Estimated Effort:** AI-estimated — validate with team — **M**

---

## Story Dependencies

| Story | Depends On | Blocks |
|-------|-----------|--------|
| US1 — IP routing fix for denied/terminated reuse | None — can be done independently | US2 (OmniScript changes can be built in parallel but reuse path must work for edit intent to be testable) |
| US2 — PAR form UX: show denied records + Edit button | US1 must be complete and tested before US2 UX changes are tested end-to-end | None |
| US3 — Clear External ID on denial | None — independent; apply as quick win | US1 (US3 removes Root Cause A; US1 removes the routing gap; together they fully resolve the duplicate error) |

**Recommended Implementation Order:**
1. US3 (quick win — prevents new External ID collisions from accumulating)
2. US1 (fix the IP routing — resolves the runtime duplicate error for existing stale records)
3. US2 (UX visibility — surfaces the reuse intent clearly to the analyst; depends on US1 being correct)

---

*End of Document*
