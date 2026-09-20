# Ancillary Assessment Guided Flow — Group Modal Professional Practice Filter & Billing Type Optional User Story

> **Source:** Stakeholder request captured 2026-05-21
> **Scope:** Ancillary Assessment guided flow group selection modal + Billing Type element across Assessment and PSV guided flows
> **Related artifacts:**
> - `AncillaryAssessment_BillingType_UserStories.md` (parent feature — supersedes Story `ENH-PRM-ANCILLARY-003` decision gate)
> - `BugFix_AncillaryAssessment_PracticeClassification_Override.md` (related classification fidelity fix)
> - `AncillaryGuidedFlow_ProviderTypesServices_UserStories.md`

---

## Story ID
`ENH-PRM-ANCILLARY-005`

## Story Title
Filter Professional Practice Locations from Ancillary Assessment Group Selection Modal & Make Billing Type Optional in Assessment and PSV Guided Flows

---

## User Story

**As an** Ancillary Credentialing Specialist,
**I want** the Ancillary Assessment guided flow to filter out Professional Practice locations from the group selection modal **and** the Billing Type field to be non-required in both the Ancillary Assessment and Ancillary PSV guided flows,
**So that** the `HealthcareFacility` records I create accurately reflect Facility / Ancillary practice classification (no accidental linking to Professional Practice locations) and Billing Type values are not forced into the wrong bucket — letting downstream defaulting logic route UB-04 vs. CMS-1500 correctly based on practice classification.

**Why it matters:**
- Today the group modal indiscriminately shows every `HealthcareFacility` record on the selected group `Account`, including locations classified as `Professional Practice`. An ancillary specialist can accidentally link a Professional Practice location to an ancillary assessment, which corrupts downstream NPDB adverse-action queries, network adequacy reports, and PSV scoping.
- Today multiple Billing Type elements in the Ancillary Assessment and Ancillary PSV flows are marked `"required": true`, which forces the specialist to make a decision even when the business intent is to let downstream defaults apply (`UB` for Facility/Ancillary, `1500` for Professional Practice — see `AncillaryAssessment_BillingType_UserStories.md` Story 003).

---

## Background / Context

### Current Group Selection Modal Behavior

The Ancillary Assessment record page (`PRM_AncillaryAssessmentRecordPage.flexipage`) hosts the **`prmAddressGroupManager`** LWC. When a specialist:

1. Enters NPI/Tax ID to find a group → `PRM_AddressManagementService.findAccountsByNpiAndTaxId()`
2. Clicks "Find Existing Locations" → opens the group selection modal powered by `PRM_AddressManagementService.searchFacilitiesForGroup()` (file `PRM_AddressManagementService.cls`, lines **517–724**).

The current Apex query in `searchFacilitiesForGroup()` selects from `HealthcareFacility` with the following filters only:

```apex
SELECT LocationId
FROM HealthcareFacility
WHERE AccountId = :groupAccountId
  AND PRM_IsErrorRecord__c = false
  AND LocationId != null
```

There is **no `PRM_PracticeClassification__c` filter**. All locations on the group surface in the modal, regardless of classification. The same gap exists in the `OmniScript` typeahead variant `PRM_AncillaryProviderForm_English_Element_GroupTypeAhead`, which is powered by `PRMDRExtractGroupNameBasedOnTINNPI` DataRaptor.

### Current Billing Type Element Configuration

The Billing Type element appears with `"required": true` in the following OmniScript element JSON files (verified in `vlocity_export/`):

| OmniScript | Element | Path Block | Current `required` |
|---|---|---|---|
| `PRM_AccountCreation_English` | `BillingTypePrimary` | `PrimaryAddress > NoPrimaryCrossRef` | `true` |
| `PRM_AccountCreation_English` | `BillingTypeAdditional` | `AdditionalAddressReview` | `true` |
| `PRM_AccountCreation_English` | `CRPNPIBillingType` | Cross-Reference NPI block | `true` |
| `PRM_AccountCreation_English` | `CRPPIEBillingType` | Cross-Reference PIE block | `true` |
| `PRM_DelegatedPractitionerAddressForm_English` | `BillingType` | `PrimaryOfficeAddressBlock` | `false` (already correct) |
| `PRM_DelegatedPractitionerAddressForm_English` | `BillingTypeAdditional` | `AdditionalAddress` | `false` (already correct) |

The underlying field `HealthcareFacility.PRM_BillingType__c` is a single-value picklist (`UB` / `1500`). When left blank, downstream services (`PRM_AncillaryProviderUtilsPDAService.processPracticeLocations()`) are expected to default `UB` for Facility/Ancillary and `1500` for Professional Practice (per existing Story 003 in `AncillaryAssessment_BillingType_UserStories.md`).

---

## Scope

| Flow | Component | Affected Surface | Data Source |
|------|-----------|------------------|-------------|
| Ancillary Assessment guided flow | `prmAddressGroupManager` (LWC) | Group selection modal — "Find Existing Locations" results table | `PRM_AddressManagementService.searchFacilitiesForGroup` (Apex) |
| Ancillary Assessment guided flow | `PRM_AncillaryProviderForm_English` (OmniScript) | `GroupTypeAhead` block on Provider step (if used) | `PRMDRExtractGroupNameBasedOnTINNPI` (DataRaptor Extract) |
| Ancillary Assessment guided flow | `PRM_AccountCreation_English` (OmniScript) | `BillingTypePrimary`, `BillingTypeAdditional`, `CRPNPIBillingType`, `CRPPIEBillingType` | Element JSON `"required"` property |
| Ancillary PSV guided flow | `PRM_AncillaryPSVForm_English` / `PRM_AncillaryReassessmentPSV_English` (OmniScript) | Any Billing Type element rendered for PSV review (see Clarification Q3) | Element JSON `"required"` property |

---

## Acceptance Criteria

### AC1 — Filter Out Professional Practice Locations from Group Selection Modal

**Given** I am an Ancillary Credentialing Specialist on the Ancillary Assessment record page,
**And** I have selected a group `Account` (via NPI/Tax ID search) that has multiple `HealthcareFacility` child locations,
**When** I open the group selection modal (click "Find Existing Locations") in `prmAddressGroupManager`,
**Then** the results table renders **only** `HealthcareFacility` records where `PRM_PracticeClassification__c != 'Professional Practice'`,
**And** `HealthcareFacility` records where `PRM_PracticeClassification__c = 'Professional Practice'` are excluded from the result list and from the `totalCount` returned by `searchFacilitiesForGroup`,
**And** the existing filters (`AccountId`, `PRM_IsErrorRecord__c = false`, address/city/state/zip filters) continue to operate alongside the new classification filter.

**Edge case:** When a `HealthcareFacility` has `PRM_PracticeClassification__c = NULL`, the record **is shown** (treated as Facility/Ancillary by default). The filter excludes only the explicit `Professional Practice` value.

### AC2 — Group Typeahead in OmniScript Also Excludes Professional Practice Groups (Optional Sub-Filter)

**Given** I am in the Ancillary Assessment guided flow OmniScript (`PRM_AncillaryProviderForm_English`),
**When** the `GroupTypeAhead` element queries for groups via `PRMDRExtractGroupNameBasedOnTINNPI`,
**Then** the returned `Account` list excludes groups whose `Account.PRM_PracticeClassification__c` (or equivalent classification field on the group `Account`, see Clarification Q1) is `Professional Practice`,
**And** existing filters (`IsActive = true`, `PRM_ParticipationStatus__c <> 'Administrative'`, `RecordType.DeveloperName = 'PRM_Vendor'`) are preserved.

*Note: AC2 is conditional on Clarification Q1. If the business confirms the modal is the only surface in scope, AC2 is dropped from this story.*

### AC3 — Billing Type Not Required in `PRM_AccountCreation_English` (Ancillary Assessment Flow)

**Given** I am stepping through the Ancillary Assessment guided flow that uses `PRM_AccountCreation_English`,
**When** the Billing Type element renders on the `PrimaryAddress`, `AdditionalAddressReview`, or Cross-Reference (NPI/PIE) blocks,
**Then** I am **not** blocked from advancing to the next step when Billing Type is left unselected,
**And** the OmniScript element JSON for each affected element has `"required": false`:
- `PRM_AccountCreation_English_Element_BillingTypePrimary.json`
- `PRM_AccountCreation_English_Element_BillingTypeAdditional.json`
- `PRM_AccountCreation_English_Element_CRPNPIBillingType.json`
- `PRM_AccountCreation_English_Element_CRPPIEBillingType.json`

### AC4 — Billing Type Not Required in `PRM_AncillaryPSVForm_English` (PSV Guided Flow)

**Given** I am stepping through the Ancillary PSV guided flow,
**When** any Billing Type-related element renders (see Clarification Q3 — confirm exact element names),
**Then** I am **not** blocked from advancing to the next step when Billing Type is left unselected,
**And** the corresponding element JSON files are updated with `"required": false`.

### AC5 — Saved `HealthcareFacility.PRM_BillingType__c` Reflects Specialist's Selection OR Downstream Default

**Given** the specialist leaves Billing Type unselected and submits the flow,
**When** the `PRM_AncillaryFormRecordsCreation` Integration Procedure / `PRM_AncillaryProviderUtilsPDAService` saves the `HealthcareFacility`,
**Then** the system applies the classification-based default:
- `PRM_PracticeClassification__c = 'Facility'` (or `'Ancillary'`) → `PRM_BillingType__c = 'UB'`
- `PRM_PracticeClassification__c = 'Professional Practice'` → `PRM_BillingType__c = '1500'`

**And** if the specialist explicitly selected `UB` or `1500`, the explicit selection is persisted (overrides the default).

*Note: AC5 carries the deferred dependency from `AncillaryAssessment_BillingType_UserStories.md` Story 003. Confirm IP / Apex defaulting logic is implemented in the same release.*

### AC6 — No Regression on Existing Group Modal Use Cases

**Given** a group with mixed `HealthcareFacility` classifications (Facility, Ancillary, Professional Practice),
**When** the specialist opens the group modal,
**Then** Facility and Ancillary locations continue to display correctly (existing behavior preserved for the in-scope classifications),
**And** address filters, pagination, primary-flag display, and "linked to practitioner" indicators all continue to function as before.

---

## Current State (from codebase)

### `PRM_AddressManagementService.searchFacilitiesForGroup` (Apex)

- **File:** `force-app/main/default/classes/PRM_AddressManagementService.cls`, lines 517–724
- **Current WHERE clause** for `HealthcareFacility`:

```
WHERE AccountId = :groupAccountId
  AND PRM_IsErrorRecord__c = false
  AND LocationId != null
```

- **Missing:** No `PRM_PracticeClassification__c != 'Professional Practice'` predicate.

### `PRMDRExtractGroupNameBasedOnTINNPI` (DataRaptor Extract)

- **File:** `vlocity_export/DataRaptor/PRMDRExtractGroupNameBasedOnTINNPI/PRMDRExtractGroupNameBasedOnTINNPI_Items.json`
- **Current Account filters:** `IsActive = true`, `PRM_ParticipationStatus__c <> 'Administrative'`, `RecordType.DeveloperName = 'PRM_Vendor'`
- **Missing:** No Practice Classification filter.

### Billing Type Elements (OmniScript)

- **`PRM_AccountCreation_English_Element_BillingTypePrimary.json`** (line 66): `"required": true`
- **`PRM_AccountCreation_English_Element_BillingTypeAdditional.json`** (line 66): `"required": true`
- **`PRM_AccountCreation_English_Element_CRPNPIBillingType.json`** (line 66): `"required": true`
- **`PRM_AccountCreation_English_Element_CRPPIEBillingType.json`** (line 66): `"required": true`
- **`PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json`** (line 56): `"required": false` (already correct, no change needed)
- **`PRM_DelegatedPractitionerAddressForm_English_Element_BillingTypeAdditional.json`** (line 56): `"required": false` (already correct, no change needed)

---

## Technical Section (For Developers)

### Changes Required

| # | Component | Type | Change |
|---|-----------|------|--------|
| 1 | `PRM_AddressManagementService.cls` → `searchFacilitiesForGroup()` | Apex | Add `AND PRM_PracticeClassification__c != 'Professional Practice'` to the `HealthcareFacility` `WHERE` clause used by `allAccountFacilities` (line ~542) and the dynamic `countQuery` / `facilityQuery` strings (lines ~615, ~622). Bind the literal as a constant or `Schema` reference rather than a magic string. |
| 2 | `PRM_AddressManagementService.cls` test class | Apex Test | Add unit test in `PRM_AddressManagementServiceTest.cls` that seeds 3 HealthcareFacility records (Facility, Ancillary, Professional Practice) and asserts the Professional Practice one is excluded from `searchFacilitiesForGroup` results. |
| 3 | `PRMDRExtractGroupNameBasedOnTINNPI` | DataRaptor Extract | *(Conditional on Clarification Q1)* Add a filter item: `Account.PRM_PracticeClassification__c <> "Professional Practice"` to both FilterGroup 0 and FilterGroup 1 of the DataRaptor. |
| 4 | `PRM_AccountCreation_English_Element_BillingTypePrimary.json` | OmniScript element | `"required": true` → `"required": false` |
| 5 | `PRM_AccountCreation_English_Element_BillingTypeAdditional.json` | OmniScript element | `"required": true` → `"required": false` |
| 6 | `PRM_AccountCreation_English_Element_CRPNPIBillingType.json` | OmniScript element | `"required": true` → `"required": false` |
| 7 | `PRM_AccountCreation_English_Element_CRPPIEBillingType.json` | OmniScript element | `"required": true` → `"required": false` |
| 8 | `PRM_AccountCreation_English` | OmniScript | Activate new version after element changes |
| 9 | PSV Billing Type elements (see Clarification Q3) | OmniScript elements | `"required": true` → `"required": false` once exact element names are confirmed |
| 10 | `PRM_AncillaryFormRecordsCreation` (Integration Procedure) | IP | Add conditional Set Values step: if `BillingType` blank AND `PRM_PracticeClassification__c = 'Professional Practice'` → set `'1500'`; else → set `'UB'`. *(Inherits from Story 003 — verify exists before this story closes.)* |

### Apex Snippet (Illustrative)

```apex
// PRM_AddressManagementService.searchFacilitiesForGroup (around line 542)

private static final String PROFESSIONAL_PRACTICE_CLASSIFICATION = 'Professional Practice';

List<HealthcareFacility> allAccountFacilities = [
    SELECT LocationId
    FROM HealthcareFacility
    WHERE AccountId = :groupAccountId
      AND PRM_IsErrorRecord__c = false
      AND LocationId != null
      AND (PRM_PracticeClassification__c = null
           OR PRM_PracticeClassification__c != :PROFESSIONAL_PRACTICE_CLASSIFICATION)
    WITH USER_MODE
];

// Update the dynamic countQuery / facilityQuery (~lines 615, 622) similarly:
String countQuery =
    'SELECT COUNT() FROM HealthcareFacility ' +
    'WHERE AccountId = :groupAccountId ' +
    '  AND PRM_IsErrorRecord__c = false ' +
    '  AND (PRM_PracticeClassification__c = null ' +
    '       OR PRM_PracticeClassification__c != :PROFESSIONAL_PRACTICE_CLASSIFICATION)';
```

### DataRaptor Filter Snippet (Illustrative — Item to add to `PRMDRExtractGroupNameBasedOnTINNPI_Items.json`)

```json
{
    "FilterGroup": 0,
    "FilterOperator": "<>",
    "FilterValue": "\"Professional Practice\"",
    "InputFieldName": "PRM_PracticeClassification__c",
    "InputObjectName": "Account",
    "InputObjectQuerySequence": 2,
    "Name": "PRMDRExtractGroupNameBasedOnTINNPI",
    "OutputFieldName": "Account",
    "OutputObjectName": "json"
}
```

### Element JSON Diff (Illustrative)

```diff
// PRM_AccountCreation_English_Element_BillingTypePrimary.json
-        "required": true,
+        "required": false,
         "show": {
             "group": {
```

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| Q1 | Does the Professional Practice filter apply only to the **`HealthcareFacility` location list** inside the group modal (AC1), or also to the **group `Account` typeahead** (AC2 in `PRM_AncillaryProviderForm_English_Element_GroupTypeAhead`)? The latter requires confirming the classification field on the `Account` object (or a derived field). | Defines whether DataRaptor `PRMDRExtractGroupNameBasedOnTINNPI` is also in scope (Task 3). | Product / BA |
| Q2 | When `HealthcareFacility.PRM_PracticeClassification__c` is `NULL`, should the record be **shown** (treated as default Facility/Ancillary) or **hidden** (treated as ambiguous)? | Filter semantics: `!= 'Professional Practice'` includes NULLs; `= 'Facility'` excludes them. | Product / BA |
| Q3 | Which exact OmniScript element(s) render Billing Type in the PSV guided flow (`PRM_AncillaryPSVForm_English` and/or `PRM_AncillaryReassessmentPSV_English`)? Neither OmniScript export currently contains an element named `BillingType*`. Possible the PSV flow displays Billing Type only as read-only review (in which case `required` is irrelevant). | Determines whether AC4 has any concrete element changes, or whether the requirement is N/A for PSV. | Technical / BA |
| Q4 | Is the classification-based default logic (AC5 — `UB` for Facility/Ancillary, `1500` for Professional Practice) already implemented in `PRM_AncillaryFormRecordsCreation` IP, or does this story need to deliver it (dependency on `ENH-PRM-ANCILLARY-003`)? | Determines whether this story includes IP modifications or just relies on existing logic. | Technical |
| Q5 | Should "Professional Practice" be sourced from a custom metadata constant, picklist value-set, or hardcoded literal? Recommend custom label or constant to avoid magic strings if business changes the label. | Maintainability. | Technical |
| Q6 | Does this change apply to **only** the Ancillary Assessment + Ancillary PSV flows, or should the same Professional Practice filter apply to the standard Practitioner Account Creation flow and PDM Manual Update flow that also embed `PRM_DelegatedPractitionerAddressForm_English`? | Scope expansion / regression risk for non-Ancillary flows. | BA / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_AddressManagementService.searchFacilitiesForGroup` | Apex method | **HIGH** | Adding a `WHERE` filter changes result sets for every consumer of this method (currently `prmAddressGroupManager` LWC). Must verify no other LWC/IP consumes this method without also wanting the filter. |
| `prmAddressGroupManager` LWC | LWC | MEDIUM | Behavior change visible to specialist — fewer rows returned. Update help text / empty-state copy if needed. |
| `PRMDRExtractGroupNameBasedOnTINNPI` DataRaptor | DataRaptor | MEDIUM | *(If AC2 in scope)* Filter applies to all OmniScripts that consume this DR — confirm only Ancillary flow consumes it, or scope the filter via a new DR variant. |
| `PRM_AccountCreation_English` (4 Billing Type elements) | OmniScript | LOW | Pure configuration change; new OmniScript version activation required. |
| PSV OmniScript(s) | OmniScript | LOW | Same as above, pending Clarification Q3. |
| `PRM_AncillaryFormRecordsCreation` IP | Integration Procedure | MEDIUM | If AC5 default logic must be added here, this is a meaningful logic change. Dependency on Story 003. |
| `PRM_AddressManagementServiceTest` | Apex Test | LOW | Add 2–3 test methods covering the new filter behavior. |
| Existing HealthcareFacility records | Data | LOW | No data migration needed — query change is read-only. Records mis-classified in past (per `BugFix_AncillaryAssessment_PracticeClassification_Override.md`) may surface as a side-effect once that bug is fixed. |

---

## Estimated Effort

| # | Component | Change Type | Effort | Notes |
|---|-----------|-------------|--------|-------|
| 1 | `PRM_AddressManagementService.searchFacilitiesForGroup` | Apex query update | **M** (2–4 hrs) | Two query sites to update + constant declaration. |
| 2 | `PRM_AddressManagementServiceTest` | Apex test additions | **M** (2–4 hrs) | 3 fixtures (Facility, Ancillary, Professional Practice) + 2 assertion methods. |
| 3 | `PRMDRExtractGroupNameBasedOnTINNPI` filter | DataRaptor config | **S** (< 1 hr) | *(Conditional on Q1)* Add filter item to 2 FilterGroups. |
| 4–7 | 4 × `PRM_AccountCreation_English` Billing Type element edits | OmniScript element config | **S** (< 1 hr total) | Single property flip per element. |
| 8 | `PRM_AccountCreation_English` activation | OmniStudio activation | **S** (< 1 hr) | Standard version increment + deploy. |
| 9 | PSV Billing Type elements (pending Q3) | OmniScript element config | **S** (< 1 hr) | Once elements identified. |
| 10 | `PRM_AncillaryFormRecordsCreation` IP default logic | IP step addition | **M** (2–4 hrs) | *(Inherited from Story 003 — skip if already done.)* |
| 11 | Regression QA in QA sandbox | Manual QTA | **M** (2–4 hrs) | Walk full Ancillary Assessment + PSV flow end-to-end with a multi-classification group. |

**Total Estimated Effort:** ~10–18 engineering hours → **5 story points** (M / L overall) — AI-estimated, validate with team.

---

## Test Plan (Happy Path + Edge Cases)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| T1 | Group with 1 Facility + 1 Ancillary + 1 Professional Practice location | Modal shows 2 rows (Facility + Ancillary); `totalCount = 2` |
| T2 | Group with only Professional Practice locations | Modal shows 0 rows; "No locations found" empty state |
| T3 | Group with only Facility locations | Modal shows all rows (no behavioral change vs. pre-filter) |
| T4 | `HealthcareFacility.PRM_PracticeClassification__c = NULL` | Record **displayed** (treated as default) — confirms Q2 assumption |
| T5 | Apply address filter + classification filter together | Both filters AND-combined; results respect both |
| T6 | Submit Ancillary Assessment with Billing Type left blank | No validation error; record saves with downstream default applied (`UB` for Facility, `1500` for Professional Practice) |
| T7 | Submit Ancillary Assessment with Billing Type explicitly set to `1500` for a Facility location | Explicit `1500` value persisted (no override) |
| T8 | Submit Ancillary PSV with Billing Type left blank | No validation error; PSV completes (assuming Q3 element changes are made) |
| T9 | Group modal pagination with classification filter | Page 1 / Page 2 / "Load more" continue to work correctly; `hasMore` boolean accurate |

---

## Dependencies

- **Blocks:** None (this is an additive enhancement)
- **Blocked by:**
  - Clarification Q1, Q2, Q3 (must be answered before implementation kickoff)
  - `BUG-PRM-ANCILLARY-001` (Practice Classification override fix) — should land **before** this story so the `PRM_PracticeClassification__c` field actually carries meaningful values when the new filter executes. Otherwise the filter will see only `Facility` values and the change will appear to have no effect.
  - `ENH-PRM-ANCILLARY-003` (classification-based default logic) — AC5 inherits from this story
- **Related:**
  - `AncillaryAssessment_BillingType_UserStories.md` (parent feature set)
  - `OffCycle_GroupSelection_Filter_Redesign_User_Stories.md` (parallel filter work on Off-Cycle flow — verify no shared component conflicts)

---

## Deployment Notes

- Deploy via `./TEST_DEPLOYMENT_COMMANDS.sh` (per CLAUDE.md project conventions)
- Run `npm run test:unit` for any LWC test updates
- Required permission set: `PRM_CredentialingUser` (verify field-level read on `HealthcareFacility.PRM_PracticeClassification__c`)
- After deployment, validate `searchFacilitiesForGroup` via:
  ```bash
  sf apex run --target-org qa-sandbox -f scripts/apex/test-search-facilities.apex
  ```
  (Create script if not present.)

---

## Combined Story Summary (Quick Reference)

| Acceptance Criterion | Component | Change Size |
|---|---|---|
| AC1 — Modal filter | `PRM_AddressManagementService.searchFacilitiesForGroup` | M |
| AC2 — Typeahead filter *(conditional)* | `PRMDRExtractGroupNameBasedOnTINNPI` | S |
| AC3 — Billing Type optional (Assessment) | 4 elements in `PRM_AccountCreation_English` | S |
| AC4 — Billing Type optional (PSV) | PSV element(s) TBD | S |
| AC5 — Downstream default logic | `PRM_AncillaryFormRecordsCreation` IP | M (inherited) |
| AC6 — No regression | All consumers of modal & flow | Test-only |
