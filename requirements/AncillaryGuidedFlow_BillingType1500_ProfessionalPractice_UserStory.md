# USER STORY: Billing Type "1500" in the Ancillary Guided Flow Creates a Professional Practice Practice Location

**Persona:** Ancillary Cred Specialist
**Priority:** P1
**OmniScript:** `PRM_AncillaryProviderForm_English` (embeds `PRM_AccountCreation_English`)
**Integration Procedures:** `PRM_AncillaryFormRecordsCreation`
**DataRaptors:** `PRMDRCreateAncillaryHCFacilityLocationAddress`, `PRMDRCreateAncillaryAdditionalAddressRecords`
**Relevant Requirements:**
- `AncillaryAssessment_BillingType_UserStories.md` (ENH-PRM-ANCILLARY-002 — Multi-select → single-select Picklist; ENH-PRM-ANCILLARY-003 — classification-based default)
- `BugFix_AncillaryAssessment_PracticeClassification_Override.md` (BUG-PRM-ANCILLARY-001 — classification hardcoded to "Facility")
- `AncillaryAssessment_GroupModalFilter_BillingTypeOptional_UserStory.md` (ENH-PRM-ANCILLARY-005 — Professional Practice filtered out of group modal; Billing Type optional)

## Story ID
`ENH-PRM-ANCILLARY-006`

---

## Story

**As an** Ancillary Cred Specialist,
**I want** to create a practice location in the Ancillary guided flow by selecting Billing Type **1500**, and have that location saved as a **Professional Practice** location billing on **1500**,
**So that** I can onboard professional-practice ancillary providers through the same guided flow instead of routing them to a separate process, and the location's classification and biller stay consistent for downstream credentialing, directory, and claims routing.

**Why it matters:** Billing Type was recently converted to a single-select Picklist (`UB` / `1500`), but the ancillary record-creation chain still hardcodes every location's classification to `Facility`. Selecting `1500` today produces a contradictory record — a "Facility" location that bills on the professional `1500` form — which corrupts NPDB scoping, network-adequacy reporting, and provider-directory display. Business wants the `1500` selection to deterministically produce a Professional Practice location.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Ancillary Assessment guided flow | `PRM_AncillaryProviderForm_English` → `PRM_AccountCreation_English` | Billing Type selection on primary + additional practice-location blocks | `BillingType` / `BillingTypeAdditional` (and `BillingTypePrimary` in `PRM_AccountCreation_English`) elements |
| Ancillary record creation | n/a (IP) | `DRCreateLocationAddressPracLocationRecords`, `DRCreateAdditionalAddressesRecords` | `PRM_AncillaryFormRecordsCreation` |
| HealthcareFacility write | n/a (DataRaptor Load) | `PRM_PracticeClassification__c` + `PRM_BillingType__c` mapping items | `PRMDRCreateAncillaryHCFacilityLocationAddress`, `PRMDRCreateAncillaryAdditionalAddressRecords` |

---

## Current State (from codebase)

### `PRMDRCreateAncillaryHCFacilityLocationAddress` (DataRaptor Load — primary location)
- **`PRM_BillingType__c`** mapping item: `inputFieldName = "BillingType"` → the specialist's selected billing value already flows through and is saved.
- **`PRM_PracticeClassification__c`** mapping item: `DefaultValue = "Facility"`, **no** `inputFieldName` → classification fires `"Facility"` unconditionally on every save, regardless of the billing type chosen.
- **Location:** `force-app/main/default/omniDataTransforms/PRMDRCreateAncillaryHCFacilityLocationAddress_1.rpt-meta.xml` (billing item ~line 1183; classification item ~line 1083).

### `PRMDRCreateAncillaryAdditionalAddressRecords` (DataRaptor Load — additional/satellite locations)
- Same pattern: classification hardcoded to `"Facility"` (per `BugFix_AncillaryAssessment_PracticeClassification_Override.md`, Root Cause 2).

### Billing Type elements
- `PRM_DelegatedPractitionerAddressForm_English_Element_BillingType.json` / `_BillingTypeAdditional.json` and `PRM_AccountCreation_English_Element_BillingTypePrimary.json` — options `UB` / `1500`, bound to `HealthcareFacility.PRM_BillingType__c`. (Export still shows `"Type": "Multi-select"`; single-select conversion from ENH-PRM-ANCILLARY-002 is the "recent change" referenced by business and may not yet be retrieved into `vlocity_export/`.)

### Practice Classification
- `HealthcareFacility.PRM_PracticeClassification__c` picklist values include `Facility`, `Professional Practice` (and `Ancillary`). The Ancillary flow has historically excluded/forced Professional Practice (see ENH-PRM-ANCILLARY-005, BUG-PRM-ANCILLARY-001).

---

## Acceptance Criteria

**AC-1 — Selecting Billing Type 1500 creates a Professional Practice primary location**

**Given** an Ancillary Cred Specialist is creating a new primary practice location in the Ancillary guided flow,
**When** they select Billing Type **1500** for that location and submit the form,
**Then** the practice location is saved as a **Professional Practice** location billing on **1500**,
**And** the location is not saved as Facility.

**AC-2 — Selecting Billing Type UB continues to create a Facility/Ancillary location**

**Given** an Ancillary Cred Specialist is creating a new primary practice location in the Ancillary guided flow,
**When** they select Billing Type **UB** and submit the form,
**Then** the practice location is saved as a **Facility/Ancillary** location billing on **UB**,
**And** the previously working UB path shows no regression.

**AC-3 — Additional/satellite locations follow the same rule per location**

**Given** an Ancillary Cred Specialist adds one or more additional practice locations in the same flow session,
**When** they select Billing Type **1500** on one additional location and **UB** on another and submit,
**Then** each saved location independently reflects its own selection — the `1500` location is Professional Practice and the `UB` location is Facility/Ancillary,
**And** no billing type or classification value bleeds from one location to another.

**AC-4 — Classification and biller stay consistent on the saved record (derivation rules)**

**Given** the specialist makes a Billing Type selection for a practice location,
**When** the location record is created,
**Then** the following are set together so classification and biller never contradict:

- **Practice Classification =**
  - When Billing Type = `1500` → `Professional Practice`
  - When Billing Type = `UB` → `Facility` (or `Ancillary` per the flow's existing Facility/Ancillary handling — see Clarification Q2)
- **Billing Type =** the value the specialist selected (`UB` or `1500`), persisted as-is.

**AC-5 — Billing Type left blank falls back to the classification-based default (no contradiction)**

**Given** the specialist leaves Billing Type unselected for a location (Billing Type is optional per ENH-PRM-ANCILLARY-005),
**When** the location record is created,
**Then** the location is **not** forced to a contradictory state,
**And** the system applies the agreed fallback (see Clarification Q1) — either a classification-driven biller default or a defined default classification — and the saved classification and biller remain consistent with each other.

**AC-6 — Downstream systems treat a 1500 ancillary location as Professional Practice**

**Given** a practice location was created via the Ancillary guided flow with Billing Type `1500`,
**When** NPDB adverse-action scoping, provider-directory search, or credentialing routing evaluates the location,
**Then** it is treated as a Professional Practice location billing on `1500`,
**And** no logic keys off a stale "Facility" classification for that record.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRMDRCreateAncillaryHCFacilityLocationAddress` | DataRaptor Load | Derive `PRM_PracticeClassification__c` from the billing value: when `BillingType = 1500` → `Professional Practice`, else `Facility`/`Ancillary`. Replace the unconditional `DefaultValue "Facility"` (use a formula/translation on the `BillingType` input or accept a resolved `practiceClassification` input). | Drives AC-1, AC-2, AC-4. Coordinate with BUG-PRM-ANCILLARY-001 (which maps classification from the OmniScript classification element) — pick one source of truth (see Clarification Q3). |
| `PRMDRCreateAncillaryAdditionalAddressRecords` | DataRaptor Load | Same derivation for additional/satellite locations, evaluated per iteration. | Drives AC-3. |
| `PRM_AncillaryFormRecordsCreation` | Integration Procedure | Ensure the per-location billing value (and/or resolved classification) is passed in `additionalInput` to `DRCreateLocationAddressPracLocationRecords` and `DRCreateAdditionalAddressesRecords`. | Required for the DataRaptor derivation to receive a runtime value rather than firing the default. |
| `PRM_AccountCreation_English` / `PRM_DelegatedPractitionerAddressForm_English` | OmniScript | Confirm Billing Type renders as single-select `UB`/`1500` and is selectable for Professional Practice creation in the ancillary path; reconcile with the ENH-005 Professional Practice group-modal filter so a 1500 location can still be created. | Verify-and-adjust; depends on Clarification Q4. |
| `PRM_AncillaryProviderUtilsPDAService` (if defaulting lives in Apex) | Apex | If billing/classification defaulting is applied server-side instead of the DataRaptor, implement the same `1500 → Professional Practice` derivation there. | Confirm where the canonical defaulting executes (Clarification Q3). |

Deeper design (exact merge paths, IP step edits, DataRaptor translation-map syntax) should follow the same pattern documented in `BugFix_AncillaryAssessment_PracticeClassification_Override.md` Tasks 1–4.

---

## Definition of Done

- [ ] Selecting `1500` in the Ancillary guided flow saves the primary location as Professional Practice / `1500` (AC-1).
- [ ] Selecting `UB` saves the primary location as Facility/Ancillary / `UB` with no regression (AC-2).
- [ ] Additional/satellite locations each honor their own Billing Type selection (AC-3).
- [ ] Saved classification and biller never contradict each other (AC-4).
- [ ] Blank Billing Type resolves to the agreed, non-contradictory fallback (AC-5).
- [ ] DataRaptor Preview tests pass for `1500`, `UB`, and blank inputs on both DataRaptors.
- [ ] IP Debug confirms the per-location billing/classification value reaches both DataRaptor calls.
- [ ] End-to-end flow tests pass in a sandbox; downstream NPDB/directory/credentialing spot-checks confirm Professional Practice treatment (AC-6).
- [ ] No regression in existing Ancillary Assessment flow automated tests.
- [ ] Updated DataRaptors / IP / OmniScript versions activated and deployed via standard release process.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| Q1 | When Billing Type is left **blank**, what is the fallback — default biller from classification (`Facility/Ancillary → UB`, `Professional Practice → 1500`, per ENH-003), or a default classification (e.g., Facility) then biller? | Defines AC-5 behavior and avoids a contradictory record. | Product / BA |
| Q2 | When Billing Type = `UB`, should the derived classification be `Facility`, `Ancillary`, or remain whatever the specialist selected on the existing classification element? | Determines the non-1500 branch of the AC-4 derivation table. | Product / BA |
| Q3 | This story derives classification **from Billing Type**, while BUG-PRM-ANCILLARY-001 maps classification **from the OmniScript classification element**. Which is the single source of truth when both are present (do they ever conflict)? | Prevents two competing classification rules; sets the authoritative mapping. | Technical / BA |
| Q4 | ENH-PRM-ANCILLARY-005 filters Professional Practice locations out of the ancillary group-selection modal. Does allowing **creation** of a `1500` Professional Practice location conflict with that filter, and should newly created 1500 locations be findable later in that modal? | Reconciles "create Professional Practice" with "hide Professional Practice"; avoids orphaned records. | Product / BA |
| Q5 | Does this apply only to the Ancillary Assessment guided flow, or also to Ancillary Re-Assessment / Add Sub-Service / PSV flows that share these components? | Scope and regression surface. | BA / Product |
| Q6 | Should "Professional Practice" / "1500" be sourced from a constant/custom metadata rather than a hardcoded literal in the DataRaptor? | Maintainability if labels change. | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRMDRCreateAncillaryHCFacilityLocationAddress` | DataRaptor | **HIGH** | Changes classification written for every ancillary primary location; core of the fix. |
| `PRMDRCreateAncillaryAdditionalAddressRecords` | DataRaptor | **HIGH** | Same for additional locations. |
| `PRM_AncillaryFormRecordsCreation` | Integration Procedure | MEDIUM | Must forward per-location billing/classification to the DataRaptors. |
| `PRM_AccountCreation_English` / `PRM_DelegatedPractitionerAddressForm_English` | OmniScript | MEDIUM | Billing Type must be selectable and reconciled with the ENH-005 filter. |
| Existing HealthcareFacility records | Data | LOW | Read-time logic unaffected; historical mis-stamped "Facility" records are a separate remediation (see BUG-001 Task 5). |
| Downstream NPDB / directory / credentialing | Process | MEDIUM | Newly correct Professional Practice classifications may change query/routing results; notify credentialing ops. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRMDRCreateAncillaryHCFacilityLocationAddress` derivation | DataRaptor formula/translation | M (2–4 hrs) | Replace unconditional default with `1500 → Professional Practice` logic. |
| `PRMDRCreateAncillaryAdditionalAddressRecords` derivation | DataRaptor formula/translation | M (2–4 hrs) | Per-iteration. |
| `PRM_AncillaryFormRecordsCreation` input pass-through | IP step edit | M (2–4 hrs) | `additionalInput` on two elements. |
| OmniScript verify/adjust + reconcile with ENH-005 filter | OmniScript config | M (2–4 hrs) | Pending Q4. |
| QA — DR Preview, IP Debug, E2E, downstream spot-checks | Manual QTA | M (2–4 hrs) | Mixed UB/1500 multi-location session. |

**Total Estimated Effort:** ~10–18 engineering hours → **5 story points (M/L)** — AI-estimated, validate with team.

---

> **Note on process:** Per the User Story Solution Architect contract this story would normally start with a clarifying-question round; because the request asked to draft it directly from the recent changes, key open decisions are captured in the Clarification Questions table above and should be confirmed before implementation kickoff.
