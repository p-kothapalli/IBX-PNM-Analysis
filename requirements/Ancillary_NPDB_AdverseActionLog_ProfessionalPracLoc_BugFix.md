# USER STORY: Fix Ancillary NPDB Manual Button — Adverse Action Log Not Created for Professional Practice Locations

**Persona:** Credentialing Specialist, Developer
**Priority:** P0
**OmniScript:** `PRM_CallNPDB_English`
**Integration Procedures:** `PRM_GetAncNpdbDetails`, `PRM_IPCreateAdverseActionLogParent`, `PRM_IPCreateAdverseActionLog`
**Relevant Requirements:** Bug — Ancillary Case Manager Manual NPDB Button (no defect ID provided)

---

## Story

**As a** Credentialing Specialist working on an Ancillary case,
**I want** the manual NPDB button to correctly create an Adverse Action Log record when the practice location on the case has a Professional practice classification,
**So that** the NPDB query is actually submitted and tracked, and the success message shown to me reflects a real record creation rather than a silent no-op.

**Why it matters:** When a Credentialing Specialist clicks the NPDB button on an Ancillary case whose practice location is classified as `Professional` (rather than `Facility`), the system shows a success toast but no `PRM_AdverseActionLog__c` record is created. The NPDB query is never queued. This is a silent data integrity failure with compliance implications — the provider appears reviewed when they were not.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Ancillary | `PRM_CallNPDB_English` | `PracLoc` (practice location selection) | `PRM_GetAncNpdbDetails` IP → `PRM_OmniProcessUtils.PRMDRExtractPracLocAncNpdb` Remote Action |
| Ancillary | `PRM_CallNPDB_English` | `CreateAdverseActionLog` | `PRM_IPCreateAdverseActionLogParent` → `PRM_IPCreateAdverseActionLog` → `CreateAdverseActionAncillary` Remote Action |

---

## Current State (from codebase)

### Root Cause 1 — Practice Location Query Excludes `Professional` Classification

**`PRM_OmniProcessUtilsHelper.PRMDRExtractPracLocAncNpdb` (Active Path)**
- **Location:** `force-app/main/default/classes/PRM_OmniProcessUtilsHelper.cls`, line 1919
- **Current behavior:** The SOQL hard-codes `AND PRM_PracticeClassification__c = 'Facility'` when querying `HealthcareFacility` records for the case's account. When the case has a `Professional`-classified practice location, this query returns zero rows. The `PracLocStep.PracticeLocationBlock` array sent downstream is empty.

```apex
List<HealthcareFacility> facilities = [
    SELECT Id, Name, LocationId, AccountId, Account.Name, PRM_DoingBusinessAsName__c, PRM_NpiId__c, PRM_NpiId__r.Npi
    FROM HealthcareFacility
    WHERE AccountId = :accountId
    AND PRM_PracticeClassification__c = 'Facility'   // ← BUG: excludes Professional
    WITH SECURITY_ENFORCED
    LIMIT 50000
];
```

**`PRMDRExtractPracLocAncNpdb` DataRaptor (Backup / Consistency path)**
- **Location:** `force-app/main/default/omniDataTransforms/PRMDRExtractPracLocAncNpdb_1.rpt-meta.xml`, lines 156–171
- **Current behavior:** Same `= 'Facility'` filter on `HealthcareFacility.PRM_PracticeClassification__c`. While the IP currently routes through the Remote Action rather than this DataRaptor directly, both need to be consistent.

---

### Root Cause 2 — Batch Silently Exits When Practice Location Block is Empty

**`PRM_CreateAdverseActionNpdbBatch.execute()`**
- **Location:** `force-app/main/default/classes/PRM_CreateAdverseActionNpdbBatch.cls`, lines 38–45
- **Current behavior:** `extractPracticeLocationBlocks()` returns an empty `List<Map<String, Object>>` when `PracticeLocationBlock` is absent or null. The batch's `execute()` method immediately returns on `scope.isEmpty()` — no `PRM_AdverseActionLog__c` records are inserted. No error is raised or logged.

```apex
public void execute(Database.BatchableContext bc, List<Map<String, Object>> scope) {
    try {
        if (scope == null || scope.isEmpty()) {
            return;   // ← silent no-op: 0 records inserted
        }
```

---

### Root Cause 3 — IP Always Returns `isExists = true` for Ancillary Regardless of Batch Outcome

**`PRM_IPCreateAdverseActionLog` — `AdverseAction_ResponseAction` (seq 19)**
- **Location:** `force-app/main/default/omniIntegrationProcedures/PRM_IPCreateAdverseActionLog_Procedure_9.oip-meta.xml`, lines 19–44
- **Current behavior:** `additionalOutput.isExists = "=true"` is set **unconditionally** — no execution condition. Regardless of whether `CreateAdverseActionAncillary` (seq 18) dispatched a batch with valid practice locations or an empty array, this element always fires and always returns `isExists = true`. The OmniScript receives `isExists=true` and displays the success message: _"Your request has been submitted. We will alert you when the file is received."_

```json
{
  "name": "AdverseAction_ResponseAction",
  "sequenceNumber": 19,
  "executionConditionalFormula": "",   // ← no condition: always fires
  "additionalOutput": {
    "isExists": "=true"
  }
}
```

---

### Call Chain (End-to-End)

```
User clicks NPDB button
  → PRM_CallNPDB_English OmniScript
    → PRMGetAncNpdbDetails (IP Action, seq 1) → PRM_GetAncNpdbDetails IP
        → ExtractPracLocAncNpdb (Remote Action) → PRM_OmniProcessUtils.PRMDRExtractPracLocAncNpdb
            → PRM_OmniProcessUtilsHelper line 1919
                SOQL: WHERE PRM_PracticeClassification__c = 'Facility'  ← BUG: returns 0 rows for Professional
        → Returns empty PracticeLocationBlock
    → PracLoc step (LWC pRMPracLocAncNpdb renders empty table)
    → User clicks Submit (noRowSelected validation doesn't fire — nothing to select)
    → CreateAdverseActionLog (IP Action, seq 4) → PRM_IPCreateAdverseActionLogParent → PRM_IPCreateAdverseActionLog
        → CreateAdverseActionAncillary (seq 18, Remote Action) → PRM_OmniProcessUtils.createAdverseActionNpdb
            → Database.executeBatch(new PRM_CreateAdverseActionNpdbBatch(inputMap))
                → start() returns empty list
                → execute() exits immediately: scope.isEmpty()  ← 0 records inserted
        → AdverseAction_ResponseAction (seq 19) always sets isExists=true  ← BUG: always succeeds
    → ShowMessage step shows successMessage  ← FALSE SUCCESS
```

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **`PRM_OmniProcessUtilsHelper.PRMDRExtractPracLocAncNpdb`** | Apex (Remote Action) | Change SOQL filter at line 1919 from `AND PRM_PracticeClassification__c = 'Facility'` to `AND PRM_PracticeClassification__c IN ('Facility', 'Professional')` |
| **`PRMDRExtractPracLocAncNpdb`** | DataRaptor Extract | Change filter item `filterValue` from `'Facility'` to `'Facility','Professional'`; update `filterOperator` to `IN` on the `PRM_PracticeClassification__c` filter (filterGroup 0, inputObjectQuerySequence 2) |
| **`PRM_IPCreateAdverseActionLog`** | Integration Procedure — `AdverseAction_ResponseAction` (seq 19) | Add an `executionConditionalFormula` so `isExists=true` is only returned when `CreateAdverseActionAncillary` fired against a non-empty block. Add a new Response Action (see below) for the empty-block Ancillary case. |
| **`PRM_IPCreateAdverseActionLog`** | Integration Procedure — new `RA_NoPracLocAncillary` element | Add a new Response Action at seq 17.5 with condition: CM type is Ancillary AND `PracticeLocationBlock` is blank → return `noAddressFound=true` to exit early with a user-visible error. |
| **`PRM_OmniProcessUtilsHelper.fetchAncillaryPLs`** | Apex (if confirmed in scope) | Change SOQL at line 1708 from `= 'Facility'` to `IN ('Facility', 'Professional')` if this method is also invoked during the NPDB button flow |

---

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| `PRMDRExtractPracLocAncNpdb` | DataRaptor Extract | `CaseManagerId` → resolves `IndividualApplication.AccountId` → `HealthcareFacility` | `PracLocStep.PracticeLocationBlock[]` | Change `filterOperator` from `=` to `IN` and `filterValue` from `'Facility'` to `'Facility','Professional'` on the `PRM_PracticeClassification__c` filter item |
| `PRM_IPCreateAdverseActionLog` | Integration Procedure | `cmRecTypeName`, `PracLocStep` | `isExists`, `noAddressFound` | Add new Response Action at seq 17.5 for Ancillary + empty block case; adjust `AdverseAction_ResponseAction` (seq 19) execution condition |

---

### Code Example — Fix for `PRM_OmniProcessUtilsHelper` (line 1915–1922)

```apex
// BEFORE (line 1919)
List<HealthcareFacility> facilities = [
    SELECT Id, Name, LocationId, AccountId, Account.Name, PRM_DoingBusinessAsName__c, PRM_NpiId__c, PRM_NpiId__r.Npi
    FROM HealthcareFacility
    WHERE AccountId = :accountId
    AND PRM_PracticeClassification__c = 'Facility'
    WITH SECURITY_ENFORCED
    LIMIT 50000
];

// AFTER
List<HealthcareFacility> facilities = [
    SELECT Id, Name, LocationId, AccountId, Account.Name, PRM_DoingBusinessAsName__c, PRM_NpiId__c, PRM_NpiId__r.Npi
    FROM HealthcareFacility
    WHERE AccountId = :accountId
    AND PRM_PracticeClassification__c IN ('Facility', 'Professional')
    WITH SECURITY_ENFORCED
    LIMIT 50000
];
```

### IP JSON Example — New `RA_NoPracLocAncillary` Response Action

```json
{
  "name": "RA_NoPracLocAncillary",
  "type": "Response Action",
  "sequenceNumber": 17.5,
  "propertySetConfig": {
    "isActive": true,
    "returnOnlyAdditionalOutput": true,
    "executionConditionalFormula": "(%cmRecTypeName% == 'PRM_AncillaryAssessment' || %cmRecTypeName% == 'PRM_AncillaryReAssessment') && ISBLANK(%PracLocStep:PracticeLocationBlock%)",
    "additionalOutput": {
      "noAddressFound": "=true"
    }
  }
}
```

---

## Acceptance Criteria

**Scenario 1 — Happy Path: Professional-Classified Practice Location**

**Given** an Ancillary case manager (`PRM_AncillaryAssessment`) whose associated provider account has a `HealthcareFacility` record with `PRM_PracticeClassification__c = 'Professional'`,
**When** the Credentialing Specialist clicks the manual NPDB button (`PRM_CallNPDB_English`),
**Then** the `PracLoc` step displays the professional practice location in the selection table, and upon submission, a `PRM_AdverseActionLog__c` record with `PRM_Status__c = 'Ready To Process'`, `PRM_AdHoc__c = true`, `RecordTypeId = PRM_Organization`, and `PRM_CaseManager__c` populated is created.

---

**Scenario 2 — Happy Path: Facility-Classified Practice Location (Regression)**

**Given** an Ancillary case manager whose associated provider account has a `HealthcareFacility` record with `PRM_PracticeClassification__c = 'Facility'`,
**When** the Credentialing Specialist clicks the manual NPDB button,
**Then** existing behavior is unchanged — the facility location displays in the selection table and the Adverse Action Log record is created as before.

---

**Scenario 3 — Edge Case: No Practice Locations Found**

**Given** an Ancillary case manager whose associated provider account has no active `HealthcareFacility` records matching either `Facility` or `Professional` classification,
**When** the Credentialing Specialist clicks the manual NPDB button,
**Then** the OmniScript displays the "No Active Location Found" message (via `noAddressFoundMessage` element) instead of showing a false success.

---

**Scenario 4 — Negative: No Row Selected**

**Given** the `PracLoc` step is displayed with at least one practice location,
**When** the Credentialing Specialist clicks Next without checking any location checkbox,
**Then** the `NoRowSelectedMsg` validation fires and the user cannot proceed.

---

**Scenario 5 — Idempotency: Duplicate Request Within 24 Hours**

**Given** an Adverse Action Log for the same Ancillary case was submitted within the last 24 hours,
**When** the Credentialing Specialist clicks the NPDB button again,
**Then** the `isSuccessReqExists = true` path is honored and the "already submitted within 24 hours" message is displayed.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the fix include **all** non-Facility classifications (e.g., just `Professional`) or should the classification filter be removed entirely? Are there other `PRM_PracticeClassification__c` values that should be excluded (e.g., NCPDP)? | Scope of the SOQL `IN` clause | Technical / BA |
| 2 | For Ancillary cases with `Professional`-classified practice locations, should the `PRM_AdverseActionLog__c` `RecordTypeId` remain `PRM_Organization`? The DR formula always queries for `PRM_Organization` — confirm this is correct for professional-type ancillary providers. | RecordType on the created log record | BA / Ops |
| 3 | Should the `fetchAncillaryPLs` method in `PRM_OmniProcessUtilsHelper` (line 1708) also be updated? This method also filters `= 'Facility'` and may affect related flows. Confirm whether it is in scope. | Apex change scope | Technical |
| 4 | When no practice locations are found for Ancillary (Scenario 3), should the OmniScript show the existing `noAddressFoundMessage` or a new Ancillary-specific message? | UX / message copy | BA / UX |
| 5 | Is the `PRMDRExtractPracLocAncNpdb` DataRaptor still invoked in any active flow, or has it been fully replaced by the Remote Action in `PRM_GetAncNpdbDetails`? If still active, it must also be updated. | Whether DR update is required | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_OmniProcessUtilsHelper` | Apex | HIGH | Primary fix — SOQL filter at line 1919 is the direct cause of empty practice location block |
| `PRMDRExtractPracLocAncNpdb` | DataRaptor Extract | HIGH | Same classification filter exists; must be updated for consistency even if not the current active path |
| `PRM_IPCreateAdverseActionLog` | Integration Procedure | MEDIUM | `AdverseAction_ResponseAction` always returns `isExists=true` for Ancillary — a new guard Response Action is needed for the empty-block scenario |
| `PRM_CallNPDB_English` | OmniScript | LOW | No element changes required if IP returns `noAddressFound=true` properly; `noAddressFoundMessage` element already exists |
| `PRM_CreateAdverseActionNpdbBatch` | Apex Batch | LOW | No code change needed; empty-scope handling is correct. Fix upstream ensures it receives populated data |
| `pRMPracLocAncNpdb` LWC | LWC | LOW | No change needed — renders whatever `PracticeLocationBlock` is provided. Readiness/lock logic queries by facility ID, not classification |
| `PRM_GetAncNpdbDetails` | Integration Procedure | LOW | No element changes needed — the `ExtractPracLocAncNpdb` Remote Action call signature is unchanged |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_OmniProcessUtilsHelper` | Apex SOQL filter change (1 line) | S | Change `= 'Facility'` to `IN ('Facility', 'Professional')` at line 1919 |
| `PRMDRExtractPracLocAncNpdb` DataRaptor | DataRaptor filter operator + value | S | Update `filterOperator` and `filterValue` on `PRM_PracticeClassification__c` item |
| `PRM_IPCreateAdverseActionLog` IP | New Response Action element + adjust seq 19 | M | Add `RA_NoPracLocAncillary` element and add execution condition to `AdverseAction_ResponseAction` |
| `PRM_OmniProcessUtilsHelper.fetchAncillaryPLs` | Apex SOQL filter (if confirmed in scope) | S | Same 1-line change at line 1708 if needed |
| Unit tests + deployment validation | Testing | M | Test both `Facility` and `Professional` paths; regression test existing Facility flow |

**Total Estimated Effort:** ~1 day — **M** overall
*(AI-estimated — validate with team)*
