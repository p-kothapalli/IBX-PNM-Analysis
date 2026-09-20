# Bug Fix Story: Ancillary Assessment Guided Flow — Practice Location Classification Blindly Overridden to "Facility"

---

## Story ID
`BUG-PRM-ANCILLARY-001`

---

## Story Title
Fix: Ancillary Assessment Guided Flow Overwrites "Professional Practice" Classification with "Facility" on All Saved Practice Locations

---

## User Story

As a **Provider Network Management credentialing coordinator**,
I want the Ancillary Assessment guided flow to preserve the practice location classification I select (e.g., "Professional Practice" or "Facility"),
So that the `HealthcareFacility` records created during onboarding accurately reflect the provider's actual practice type and downstream workflows — including NPDB adverse action queries, provider searches, and credentialing reviews — operate on correct data.

---

## Background / Context

The **Ancillary Assessment Guided Flow** (`PRM_AncillaryProviderForm_English`) is the primary onboarding path for ancillary providers in the Provider Network Management (PNM) module of Salesforce Health Cloud. During the flow, coordinators select a practice location classification — either **"Facility"** or **"Professional Practice"** — for both the primary practice location and any additional/satellite locations.

The `PRM_PracticeClassification__c` field on the `HealthcareFacility` object is a critical data point used by:

- **NPDB adverse action queries** that filter query scope by classification type
- **Provider directory searches** that surface location type to members and internal staff
- **Credentialing workflows** that apply different verification rules based on Facility vs. Professional Practice designations
- **Network adequacy reporting** that segments capacity by classification

The field must accurately reflect what the coordinator selected during data entry.

---

## Problem Statement

When a coordinator selects **"Professional Practice"** as the location classification in the Ancillary Assessment guided flow, the persisted `HealthcareFacility` record is saved with `PRM_PracticeClassification__c = "Facility"`. The user-selected value is silently discarded. This happens for both the primary practice location and any additional/satellite locations added in the same flow session.

The bug is invisible at data entry time — no error or warning is shown — and only surfaces when downstream systems consume the corrupted classification value.

---

## Technical Root Cause Analysis

The defect has three interacting failure points across two DataRaptors and one Integration Procedure.

### Root Cause 1 — DataRaptor: `PRMDRCreateAncillaryHCFacilityLocationAddress`

**File:** `PRMDRCreateAncillaryHCFacilityLocationAddress_Items.json`

The mapping item responsible for writing `PRM_PracticeClassification__c` to the `HealthcareFacility` object is configured as follows:

```json
{
    "DefaultValue": "Facility",
    "OutputFieldName": "PRM_PracticeClassification__c",
    "OutputObjectName": "HealthcareFacility",
    "InputFieldName": ""
}
```

The `InputFieldName` is blank. In OmniStudio DataRaptor Load behavior, when `InputFieldName` is empty, no runtime value is evaluated — the `DefaultValue` fires unconditionally on every execution, regardless of what the user selected. The DataRaptor has no mechanism to receive or apply the user's actual classification choice.

### Root Cause 2 — DataRaptor: `PRMDRCreateAncillaryAdditionalAddressRecords`

**File:** `PRMDRCreateAncillaryAdditionalAddressRecords_Items.json`

The same misconfiguration exists for the additional/satellite locations DataRaptor:

```json
{
    "DefaultValue": "Facility",
    "OutputFieldName": "PRM_PracticeClassification__c",
    "OutputObjectName": "HealthcareFacility",
    "InputFieldName": ""
}
```

Identical behavior: `DefaultValue: "Facility"` fires unconditionally because `InputFieldName` is missing.

### Root Cause 3 — Integration Procedure: `PRM_AncillaryFormRecordsCreation`

Even if the DataRaptors were corrected to read from an `InputFieldName` of `practiceClassification`, the value would never arrive because neither IP element passes it downstream.

- The `DRCreateLocationAddressPracLocationRecords` element passes `additionalInput` containing `FacilityId`, `LocationId`, `LocationType`, `VendorAccountId`, and related fields — but **does not include `practiceClassification`**.
- The `DRCreateAdditionalAddressesRecords` element has the same gap.

The OmniScript (`PRM_AncillaryProviderForm_English`) does capture the user's selection via the `PracticeLocationType` element, but that value is never forwarded through the IP to the DataRaptors. The data is available in the OmniScript node JSON at invocation time but falls off the wire between the IP input and the DataRaptor calls.

### Summary of Failure Chain

```
OmniScript captures practiceClassification
    |
    v
PRM_AncillaryFormRecordsCreation (Integration Procedure)
    |
    +-- DRCreateLocationAddressPracLocationRecords
    |       additionalInput: { FacilityId, LocationId, LocationType, VendorAccountId }
    |       MISSING: practiceClassification                        <-- Gap 3
    |           |
    |           v
    |       PRMDRCreateAncillaryHCFacilityLocationAddress (DataRaptor Load)
    |           InputFieldName: ""  --> DefaultValue "Facility" fires unconditionally  <-- Gap 1
    |
    +-- DRCreateAdditionalAddressesRecords
            additionalInput: { ... }
            MISSING: practiceClassification                        <-- Gap 3
                |
                v
            PRMDRCreateAncillaryAdditionalAddressRecords (DataRaptor Load)
                InputFieldName: ""  --> DefaultValue "Facility" fires unconditionally  <-- Gap 2
```

---

## Acceptance Criteria

### AC-1: Primary Practice Location — Professional Practice Classification Preserved

**Given** a coordinator is completing the Ancillary Assessment guided flow (`PRM_AncillaryProviderForm_English`)
**And** the coordinator selects **"Professional Practice"** as the classification for the primary practice location
**When** the coordinator completes the flow and the form is submitted
**Then** the `HealthcareFacility` record created for the primary practice location has `PRM_PracticeClassification__c = "Professional Practice"`
**And** the value is not overridden to "Facility"

---

### AC-2: Primary Practice Location — Facility Classification Continues to Work

**Given** a coordinator is completing the Ancillary Assessment guided flow
**And** the coordinator selects **"Facility"** as the classification for the primary practice location
**When** the coordinator completes the flow and the form is submitted
**Then** the `HealthcareFacility` record created for the primary practice location has `PRM_PracticeClassification__c = "Facility"`
**And** no regression is introduced for the previously working "Facility" path

---

### AC-3: Additional/Satellite Practice Locations — Professional Practice Classification Preserved

**Given** a coordinator has added one or more additional/satellite practice locations in the Ancillary Assessment guided flow
**And** at least one of those locations is designated **"Professional Practice"**
**When** the coordinator completes the flow and the form is submitted
**Then** each additional `HealthcareFacility` record has `PRM_PracticeClassification__c` equal to the classification that was selected for that specific location
**And** a "Professional Practice" selection is not overridden to "Facility"

---

### AC-4: Additional/Satellite Practice Locations — Facility Classification Continues to Work

**Given** a coordinator has added one or more additional/satellite practice locations designated as **"Facility"**
**When** the form is submitted
**Then** each of those `HealthcareFacility` records has `PRM_PracticeClassification__c = "Facility"`

---

### AC-5: Mixed Classifications in a Single Session

**Given** a coordinator adds both a **"Professional Practice"** location and a **"Facility"** location (primary + additional, or multiple additional locations of different types) in a single flow session
**When** the form is submitted
**Then** each `HealthcareFacility` record reflects the individual classification chosen for that location
**And** no classification value bleeds over from one location to another

---

### AC-6: DefaultValue Retained as True Fallback Only

**Given** the `InputFieldName` is now mapped to `practiceClassification` in both DataRaptors
**When** the `practiceClassification` input value is blank or null (edge case — e.g., legacy data replay or non-standard invocation)
**Then** the `DefaultValue: "Facility"` applies as a safe fallback
**And** this fallback does not fire when a valid classification value is present

---

### AC-7: Downstream Systems Reflect Correct Classification

**Given** a `HealthcareFacility` record has been saved with `PRM_PracticeClassification__c = "Professional Practice"` via the corrected flow
**When** an NPDB adverse action query, provider directory search, or credentialing workflow evaluates the record
**Then** the record is treated as a Professional Practice location, not a Facility
**And** no incorrect filtering, routing, or verification rule is applied based on a stale "Facility" value

---

## Implementation Steps / Technical Tasks

### Task 1 — Fix DataRaptor `PRMDRCreateAncillaryHCFacilityLocationAddress`

**Component Type:** DataRaptor Load
**File to Modify:** `PRMDRCreateAncillaryHCFacilityLocationAddress_Items.json`

Locate the output mapping item where:
- `OutputObjectName = "HealthcareFacility"`
- `OutputFieldName = "PRM_PracticeClassification__c"`

Change the item from:

```json
{
    "DefaultValue": "Facility",
    "OutputFieldName": "PRM_PracticeClassification__c",
    "OutputObjectName": "HealthcareFacility",
    "InputFieldName": ""
}
```

To:

```json
{
    "InputFieldName": "practiceClassification",
    "DefaultValue": "Facility",
    "OutputFieldName": "PRM_PracticeClassification__c",
    "OutputObjectName": "HealthcareFacility"
}
```

The `DefaultValue: "Facility"` is intentionally retained as a fallback for null/blank input. The key change is populating `InputFieldName` so the runtime value takes precedence when present.

**Verification:** Activate the updated DataRaptor version. Confirm the mapping item has a non-empty `InputFieldName` in the activated definition.

---

### Task 2 — Fix DataRaptor `PRMDRCreateAncillaryAdditionalAddressRecords`

**Component Type:** DataRaptor Load
**File to Modify:** `PRMDRCreateAncillaryAdditionalAddressRecords_Items.json`

Apply the same change as Task 1 to the equivalent mapping item in this DataRaptor:

```json
{
    "InputFieldName": "practiceClassification",
    "DefaultValue": "Facility",
    "OutputFieldName": "PRM_PracticeClassification__c",
    "OutputObjectName": "HealthcareFacility"
}
```

**Verification:** Activate the updated DataRaptor version.

---

### Task 3 — Fix Integration Procedure `PRM_AncillaryFormRecordsCreation`

**Component Type:** Integration Procedure
**Elements to Modify:**
- `DRCreateLocationAddressPracLocationRecords`
- `DRCreateAdditionalAddressesRecords`

For each element, open the `additionalInput` configuration and add the `practiceClassification` key-value pair.

**For `DRCreateLocationAddressPracLocationRecords`:**

Add to `additionalInput`:
```
"practiceClassification": "%practiceClassification|n%"
```

Where `%practiceClassification|n%` is the OmniScript merge syntax referencing the `PracticeLocationType` element value from the OmniScript node. Confirm the exact OmniScript element name and node path by inspecting `PRM_AncillaryProviderForm_English` — the element may be named `PracticeLocationType`, `LocationClassification`, or similar. Use the correct node path (e.g., `%Step1:PracticeLocationType|n%`) as required by the OmniScript structure.

**For `DRCreateAdditionalAddressesRecords`:**

Add to `additionalInput`:
```
"practiceClassification": "%practiceClassification|n%"
```

For additional/satellite locations, the classification may be stored per-iteration if the locations are collected in a repeat block. Confirm the correct merge path for the classification value within that repeat context (e.g., `%AdditionalLocationsStep:additionalPracticeClassification|n%`). Ensure the path resolves correctly for each iteration.

**Verification:** Activate the updated Integration Procedure version. Use IP Debug / Preview mode to confirm `practiceClassification` appears in the runtime input context reaching each DataRaptor call.

---

### Task 4 — Confirm OmniScript Element Name and Node Path

**Component:** OmniScript `PRM_AncillaryProviderForm_English`

Before finalizing the IP `additionalInput` syntax in Task 3, verify:

1. The exact element name used to capture practice location classification for the primary location (likely `PracticeLocationType` or `LocationClassification`).
2. The step/group nesting for the additional locations repeat block and the element name used for classification within it.
3. Confirm the OmniScript properly passes its full JSON node to the IP call. If the IP is invoked via a `SetValues` or `DataJSON` action, verify the classification field is included in the payload passed to the IP.

No OmniScript changes are expected unless the classification field is confirmed to be missing from the IP input payload — in which case a `SetValues` action or merge field addition to the IP invocation step may be required.

---

### Task 5 — Data Remediation Assessment (Separate Track)

Identify all `HealthcareFacility` records created via the Ancillary Assessment flow after the bug was introduced where `PRM_PracticeClassification__c = "Facility"` but the coordinator's intent was "Professional Practice".

This task is **scoped separately** (see Out of Scope below) but must be triaged before this story is closed. A SOQL audit query should be provided to the data team to quantify the impact:

```sql
SELECT Id, Name, PRM_PracticeClassification__c, CreatedDate
FROM HealthcareFacility
WHERE PRM_PracticeClassification__c = 'Facility'
  AND CreatedDate >= :bugIntroductionDate
  -- AND additional filter to identify Ancillary-flow-created records
ORDER BY CreatedDate DESC
```

The data remediation story (correction of existing records) should be created as a follow-on.

---

## Files to Change

| File | Component Type | Change Description |
|---|---|---|
| `PRMDRCreateAncillaryHCFacilityLocationAddress_Items.json` | DataRaptor Load | Add `InputFieldName: "practiceClassification"` to the `PRM_PracticeClassification__c` mapping item |
| `PRMDRCreateAncillaryAdditionalAddressRecords_Items.json` | DataRaptor Load | Add `InputFieldName: "practiceClassification"` to the `PRM_PracticeClassification__c` mapping item |
| `PRM_AncillaryFormRecordsCreation` (Integration Procedure) | Integration Procedure | Add `practiceClassification` to `additionalInput` of `DRCreateLocationAddressPracLocationRecords` and `DRCreateAdditionalAddressesRecords` elements |
| `PRM_AncillaryProviderForm_English` (OmniScript) | OmniScript | Verify only — confirm element name and node path for classification field; change only if the value is not already reachable by the IP |

---

## Testing Notes

### Unit Testing — DataRaptor Preview

1. Open `PRMDRCreateAncillaryHCFacilityLocationAddress` in DataRaptor Preview.
2. Supply input: `{ "practiceClassification": "Professional Practice", "FacilityId": "<test_id>", ... }`.
3. Verify the preview output shows `PRM_PracticeClassification__c = "Professional Practice"`.
4. Repeat with `{ "practiceClassification": "Facility" }` — confirm output is `"Facility"`.
5. Repeat with `{ "practiceClassification": "" }` or omit the key — confirm `DefaultValue "Facility"` is applied.
6. Repeat all three tests for `PRMDRCreateAncillaryAdditionalAddressRecords`.

### Integration Procedure Debug

1. Open `PRM_AncillaryFormRecordsCreation` in IP Debug / Preview mode.
2. Supply a test input JSON that includes `"practiceClassification": "Professional Practice"` alongside the standard required inputs.
3. Confirm that the `DRCreateLocationAddressPracLocationRecords` and `DRCreateAdditionalAddressesRecords` steps each receive `practiceClassification` in their resolved input context.
4. Confirm the DataRaptor calls within those steps produce the correct `PRM_PracticeClassification__c` value.

### End-to-End Flow Testing

1. **Scenario A — Professional Practice, Primary Location Only:**
   - Complete the Ancillary Assessment flow selecting "Professional Practice" for the primary location.
   - After submission, query the created `HealthcareFacility` record.
   - Assert: `PRM_PracticeClassification__c = "Professional Practice"`.

2. **Scenario B — Facility, Primary Location Only:**
   - Complete the flow selecting "Facility".
   - Assert: `PRM_PracticeClassification__c = "Facility"`.

3. **Scenario C — Mixed Additional Locations:**
   - Add two additional locations: one "Facility", one "Professional Practice".
   - Assert each `HealthcareFacility` record has the correct individual classification.

4. **Scenario D — Null/Blank Classification (Edge Case):**
   - If possible to submit with no classification selected, verify `DefaultValue "Facility"` applies and no error is thrown.

5. **Scenario E — Regression Check:**
   - Run any existing automated test suite for the Ancillary Assessment flow.
   - Confirm no previously passing tests now fail.

### Downstream Impact Verification

1. Confirm NPDB adverse action query logic correctly scopes queries using the now-accurate `PRM_PracticeClassification__c` values.
2. Spot-check provider directory search results for a newly created "Professional Practice" facility — verify it appears in Professional Practice-filtered searches and does not appear in Facility-only searches.
3. Confirm credentialing workflow routing for a newly created "Professional Practice" record follows the Professional Practice verification path.

---

## Out of Scope

The following items are explicitly excluded from this story and should be addressed in follow-on work items:

1. **Historical data remediation** — Correcting existing `HealthcareFacility` records that were incorrectly stamped with `PRM_PracticeClassification__c = "Facility"` due to this bug. A separate data fix story should be created after the scope of corruption is quantified (see Task 5 above).
2. **Other guided flows** — Investigation of whether the same `InputFieldName` omission pattern exists in other OmniScripts or DataRaptors (e.g., re-credentialing flows, PAR forms, or the standard provider onboarding flow) is out of scope for this fix but should be added to the technical debt backlog as a targeted audit.
3. **UI validation / field-level enforcement** — Adding front-end validation in the OmniScript to require a classification selection before proceeding is a separate UX enhancement story.
4. **Classification picklist value changes** — Any changes to the allowed values in the `PRM_PracticeClassification__c` picklist are out of scope.
5. **Permission and sharing changes** — No changes to field-level security, profiles, or sharing rules are included in this fix.

---

## Dependencies

| Dependency | Type | Notes |
|---|---|---|
| OmniScript `PRM_AncillaryProviderForm_English` | Read-only inspection | Must confirm element name and merge path for `practiceClassification` before finalizing IP `additionalInput` syntax. No change expected, but confirmation required before Task 3 is finalized. |
| Sandbox with representative test data | Environment | A sandbox with active `HealthcareFacility` and `PracticeLocation` test records is required for end-to-end testing. |
| DataRaptor activation permissions | Access | Developer must have OmniStudio DataRaptor activation rights in the target sandbox. |
| Integration Procedure activation permissions | Access | Developer must have IP activation rights in the target sandbox. |

---

## Effort Estimate

| Task | Estimate |
|---|---|
| Task 1 — Fix DataRaptor `PRMDRCreateAncillaryHCFacilityLocationAddress` | 1 story point |
| Task 2 — Fix DataRaptor `PRMDRCreateAncillaryAdditionalAddressRecords` | 1 story point |
| Task 3 — Fix Integration Procedure `PRM_AncillaryFormRecordsCreation` | 2 story points |
| Task 4 — OmniScript element name / node path verification | 1 story point |
| Task 5 — Data remediation assessment (SOQL audit, scoping) | 1 story point |
| QA / Testing (unit, IP debug, E2E, downstream verification) | 2 story points |
| **Total** | **8 story points** |

The fix itself is low-code and targeted (three configuration changes across two DataRaptors and one IP), but the verification surface is moderate given the downstream systems affected.

---

## Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OmniScript merge path for `practiceClassification` does not match assumed element name | Medium | Medium | Complete Task 4 (OmniScript inspection) before implementing Task 3. Coordinate with the original flow developer if naming is ambiguous. |
| Additional location classification is stored per-iteration in a repeat block and the merge path differs from the primary location path | Medium | Medium | Inspect the repeat block structure in the OmniScript during Task 4. Test Scenario C explicitly covers mixed additional locations. |
| Historical data corruption is larger than anticipated, creating stakeholder pressure to rush remediation | Low | High | Scope data remediation as a separate story with its own timeline. Do not conflate the code fix with the data fix. |
| The bug was introduced with a specific version of the DataRaptor or IP; rolling back to that version in another sandbox may mask the fix | Low | Low | Deploy the fix to a clean sandbox from the current version, not a rollback. |
| Downstream NPDB query behavior changes after fix, surfacing previously hidden adverse action results | Low | High | Notify compliance and credentialing operations teams before deploying to production. They should be prepared for potential NPDB query result changes on newly created "Professional Practice" facilities. |

---

## Definition of Done

- [ ] `InputFieldName: "practiceClassification"` is set in the `PRMDRCreateAncillaryHCFacilityLocationAddress` DataRaptor mapping item for `PRM_PracticeClassification__c` and the DataRaptor is activated.
- [ ] `InputFieldName: "practiceClassification"` is set in the `PRMDRCreateAncillaryAdditionalAddressRecords` DataRaptor mapping item for `PRM_PracticeClassification__c` and the DataRaptor is activated.
- [ ] `practiceClassification` is included in `additionalInput` for both `DRCreateLocationAddressPracLocationRecords` and `DRCreateAdditionalAddressesRecords` in the `PRM_AncillaryFormRecordsCreation` IP, and the IP is activated.
- [ ] DataRaptor Preview tests pass for "Professional Practice", "Facility", and blank input scenarios for both DataRaptors.
- [ ] Integration Procedure Debug confirms `practiceClassification` is present in the DataRaptor input context for both elements.
- [ ] End-to-end flow tests (Scenarios A through D) pass in a sandbox environment.
- [ ] No regression in existing Ancillary Assessment flow automated tests.
- [ ] Data remediation scoping query (Task 5) has been run and findings handed off to the data team.
- [ ] Credentialing operations team has been notified of the fix and any NPDB query behavioral implications.
- [ ] Change deployed to production via standard release process.
