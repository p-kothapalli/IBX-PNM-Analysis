# Provider Change Form OmniScript – PNC Deep Dive Analysis

**Document Purpose:** Deep dive analysis of the Provider Change Form OmniScript (PRM_ProviderChangeForm_English) with respect to PNC (Par Non Cred) usage, including business explanation, technical data flow, and business/technical user requirements.

**Related AC:** AC3 (User Story 10) – Provider Change Form – PNC and DelegatedValid logic

---

## 1. Executive Summary

The **Provider Change Form** is a guided flow used by PDM Specialists to submit provider change requests (e.g., add/remove practitioners, update office information, change addresses). The **PNC flag** is used in **2 of 5 request types** to validate practitioners before submission. The facility PNC value drives **PNCValid** and **DelegatedValid** formulas in `PRM_VerifyPractitionerDetails`, ensuring that:
- Non-PNC locations have at least one PNC practitioner
- Non-credentialed, non-PNC practitioners cannot be in delegated groups

**Current source:** `Facility:Account.PRM_PNC__c` (Vendor Account)  
**Target source (post-migration):** `HealthcareFacility.PRM_PNC__c` (practice location)

> **Scope note — the ALL/ANY switch does NOT change this flow.** The new per-practitioner `Account.PRM_PNCAnyLocation__c` switch only governs how the **practitioner-level** `PRM_PNC__c` rollup is computed (US4/US5). The Provider Change Form uses **facility-level** PNC (`HealthcareFacility.PRM_PNC__c`) for `PNCValid`, and the practitioner rollup (already computed) for `DelegatedValid`. No switch-related change is required here — only the source path change (Account → HealthcareFacility). The rollup value this form consumes will already reflect each practitioner's ALL/ANY setting.

---

## 2. Provider Change Form Structure

### 2.1 Request Types (FormType / ProviderChangeRequest)

| Request Type | OmniScript Element | Uses PNC? | Calls PRM_VerifyPractitionerDetails? |
|--------------|--------------------|-----------|-------------------------------------|
| **Add or Remove a Practitioner** | AddOrRemovePractioner | **Yes** | Yes (IPVerifyPractitionerDetails) |
| **Update/Add/Terminate Current Office Information** | Update/Add/TerminateCOI | **Yes** | Yes (IPVerifyPractitionerDetailsParentCOI) |
| **Update Billing and/or Mailing Address** | UpdateBillingMailingaddress | No | No |
| **Patient Accept Status** | PatientAcceptStatus | No | No |
| **Capitation Site** | CapitationSite | No | No (sub-flow: PRM_ProviderChangeFormCapitationSite_English) |

### 2.2 High-Level Flow

```
Provider Search (NPI, Tax ID, Group) 
  → ProviderSearchIP (PRM_ProviderSearchParent → PRM_ProviderSearchIP)
  → PRMExtractPracticeLocationsProvChange (Provider Change Form path)
  → Facility[] with Facility:ProviderDetails (includes PNC)
  → User selects facility (GroupSelectionFlexCard)
  → SetSelectedFacility → ProviderDetails (including PNC)
  → User selects Request Type
  → [If Add/Remove Practitioner or COI] IPVerifyPractitionerDetails / IPVerifyPractitionerDetailsParentCOI
  → PRM_VerifyPractitionerDetailsParent → PRM_VerifyPractitionerDetails
  → SetDelegatedPNC (PNCValid, DelegatedValid formulas)
  → Practitioner validation (PractitionerMissing, etc.)
```

---

## 3. Where the PNC Flag Is Used

### 3.1 Data Source (Current vs. Target)

| Component | Current Path | Target Path (Post-Migration) |
|-----------|--------------|------------------------------|
| **PRMExtractPracticeLocationsProvChange** (DataRaptor) | `Facility:Account.PRM_PNC__c` → `Facility:ProviderDetails:PNC` | `Facility:PRM_PNC__c` → `Facility:ProviderDetails:PNC` |
| **SetSelectedFacility** (OmniScript) | `ProviderDetails` = Facility:ProviderDetails (from DataRaptor output) | No change – formula unchanged |
| **IPVerifyPractitionerDetails** (extraPayload) | `PNC`: `%ProviderDetails:PNC%` | No change – passes through |
| **IPVerifyPractitionerDetailsParentCOI** (extraPayload) | `PNC`: `%ProviderDetails:PNC%` | No change – passes through |

**Key file:** `PRMExtractPracticeLocationsProvChange_Items.json` (lines 616–628):

```json
"InputFieldName": "Facility:Account.PRM_PNC__c",
"OutputFieldName": "Facility:ProviderDetails:PNC"
```

**Change required:** Update to `Facility:PRM_PNC__c` (HealthcareFacility.PRM_PNC__c).

### 3.2 Single vs. Multiple Facility Scenarios

| Scenario | ProviderDetails Source | PNC Source |
|----------|------------------------|------------|
| **Multiple facilities** (FacilitySize > 1) | `MainGroupSelection:GroupSelectionFlexCard:SelectedFacility:Facility:ProviderDetails` | From PRMExtractPracticeLocationsProvChange output |
| **Single facility** (FacilitySize = 1) | `FacilityDetails|1:ProviderDetails` | From PRMExtractPracticeLocationsProvChange (or equivalent path in Provider Search) |

Both paths ultimately derive ProviderDetails (and PNC) from the DataRaptor that extracts practice locations for the Provider Change Form flow.

### 3.3 SetValues2 – Default PNC for New Practitioners

The **SetValues2** element contains sample/default data for new practitioners being added. It sets `"PNC": false` as the default for practitioner records in the PractitionerList. This is **practitioner-level** PNC (rollup), not facility PNC. No change required for the PNC migration.

---

## 4. Business Explanation

### 4.1 What Is PNC?

**PNC = Par Non Cred (Participating Non-Credentialed).** A practice location or practitioner participates in the network without full individual credentialing, typically through a group/vendor affiliation.

### 4.2 Why PNC Matters in the Provider Change Form

1. **Practitioner validation (PNCValid):**
   - If the **selected facility is PNC** → validation passes regardless of practitioner PNC status.
   - If the **selected facility is NOT PNC** → at least one practitioner with PNC = true must be present. This ensures non-PNC locations have a designated PNC practitioner for compliance.

2. **Delegated group validation (DelegatedValid):**
   - **Delegated groups** allow non-credentialed practitioners to participate under the group’s credentialing.
   - Non-credentialed, **non-PNC** practitioners cannot be in delegated groups.
   - Non-credentialed, **PNC** practitioners can be in delegated groups.

3. **Impact of wrong PNC source:**
   - If facility PNC comes from the Vendor Account instead of the practice location:
     - Locations within the same group may show the same PNC even when they differ.
     - Validation can pass or fail incorrectly.
     - Incorrect PractitionerMissing errors may block valid submissions.

### 4.3 Which Request Types Use PNC?

| Request Type | Business Reason PNC Is Used |
|--------------|-----------------------------|
| **Add or Remove a Practitioner** | Validates that practitioners being added/removed comply with PNC and Delegated rules for the selected location. |
| **Update/Add/Terminate Current Office Information** | Validates practitioners associated with the location (e.g., when adding a new address or updating office info) against PNC/Delegated rules. |

**Request types that do NOT use PNC:** Update Billing/Mailing Address, Patient Accept Status, Capitation Site – these do not invoke practitioner verification.

---

## 5. Technical Data Flow

### 5.1 End-to-End PNC Flow

```
1. User enters NPI/Tax ID → ProviderSearchIP
2. PRM_ProviderSearchParent → PRM_ProviderSearchIP (CallProviderSearchIP)
3. PRMExtractPracticeLocationsProvChange runs when:
   - Flow == "Provider Change Form"
   - ProviderDetails:IsAncillary == false (or blank)
   - ProviderDetails:AdditionalFilters == blank
4. DataRaptor queries HealthcareFacility (by AccountId from ProviderDetails)
   - Maps Facility:Account.PRM_PNC__c → Facility:ProviderDetails:PNC  [CHANGE: Facility:PRM_PNC__c]
5. Output: Facility[] with Facility:ProviderDetails (AccountId, AccountName, PNC, ParticipationStatus, etc.)
6. User selects facility → SetSelectedFacility sets ProviderDetails
7. User selects "Add or Remove a Practitioner" or "Update/Add/Terminate Current Office Information"
8. IPVerifyPractitionerDetails or IPVerifyPractitionerDetailsParentCOI runs
   - extraPayload includes: PNC: %ProviderDetails:PNC%
9. PRM_VerifyPractitionerDetailsParent → PRM_VerifyPractitionerDetails
10. SetDelegatedPNC element:
    - PNCValid = IF(%PNC% = true, true, ...)  // facility PNC
    - DelegatedValid = ... (uses practitioner PNC from rollup)
11. PractitionerMissing = ... || PNCValid == false || DelegatedValid == false
```

### 5.2 Components to Update

| Component | Type | Change |
|-----------|------|--------|
| **PRMExtractPracticeLocationsProvChange** | DataRaptor (OmniDataTransform) | `InputFieldName`: `Facility:Account.PRM_PNC__c` → `Facility:PRM_PNC__c` |
| **PRM_VerifyPractitionerDetails** | Integration Procedure | No formula change – receives PNC from OmniScript; ensure OmniScript passes correct value |
| **PRM_ProviderChangeForm_English** | OmniScript | No direct change – ProviderDetails:PNC flows from DataRaptor via SetSelectedFacility |

### 5.3 Dependency: PRM_FetchFacilityDetailsParent

When the user selects a facility, **IPFetchFacilityDetailsParent** may run to load additional facility details (e.g., for single-facility or refresh). If FacilityDetails is populated by this IP, ensure any ProviderDetails/PNC returned also uses `HealthcareFacility.PRM_PNC__c`. The primary PNC path for Provider Change Form is **PRMExtractPracticeLocationsProvChange**; verify FetchFacilityDetails does not override ProviderDetails:PNC with an incorrect source.

---

## 6. Business User Requirements

### BR1: Correct PNC Display
**As a** PDM Specialist using the Provider Change Form,  
**I want** the facility PNC status to reflect the selected practice location’s actual PNC value,  
**So that** I can trust the validation and avoid incorrect rejections or approvals.

### BR2: Validation Behavior
**As a** PDM Specialist,  
**When** I add or remove practitioners, or update/add/terminate current office information,  
**I want** validation to use the selected facility’s PNC (not the vendor’s),  
**So that** locations with different PNC status within the same group are validated correctly.

### BR3: Delegated Group Rules
**As a** PDM Specialist,  
**When** the selected facility is in a delegated group,  
**I want** only credentialed or PNC practitioners to be allowed,  
**So that** we comply with delegated credentialing rules.

### BR4: PNC Practitioner Requirement
**As a** PDM Specialist,  
**When** the selected facility is NOT PNC,  
**I want** at least one PNC practitioner to be required,  
**So that** the location meets compliance requirements.

---

## 7. Technical User Requirements

### TR1: DataRaptor Update
**Given** the PRMExtractPracticeLocationsProvChange DataRaptor,  
**When** the developer updates the PNC field mapping,  
**Then** `InputFieldName` shall change from `Facility:Account.PRM_PNC__c` to `Facility:PRM_PNC__c`, and `OutputFieldName` shall remain `Facility:ProviderDetails:PNC`.

### TR2: ProviderDetails:PNC Source
**Given** the Provider Change Form OmniScript,  
**When** SetSelectedFacility sets ProviderDetails,  
**Then** ProviderDetails:PNC shall come from the selected facility’s HealthcareFacility.PRM_PNC__c (via DataRaptor output).

### TR3: IP Input
**Given** IPVerifyPractitionerDetails and IPVerifyPractitionerDetailsParentCOI,  
**When** they pass extraPayload to PRM_VerifyPractitionerDetailsParent,  
**Then** the PNC value shall be `%ProviderDetails:PNC%`, which reflects HealthcareFacility.PRM_PNC__c for the selected facility.

### TR4: PNCValid Formula
**Given** PRM_VerifyPractitionerDetails runs with SetDelegatedPNC,  
**When** %PNC% (facility PNC) = true,  
**Then** PNCValid shall evaluate to true (validation passes).  
**When** %PNC% = false,  
**Then** PNCValid shall require at least one practitioner with PNC = true in the practitioner list.

### TR5: DelegatedValid Formula
**Given** PRM_VerifyPractitionerDetails runs with SetDelegatedPNC,  
**When** the group is delegated,  
**Then** DelegatedValid shall fail if any practitioner is non-credentialed AND non-PNC. Practitioner PNC comes from the practitioner Account rollup.

### TR6: Request Type Conditioning
**Given** the Provider Change Form,  
**When** the user selects "Add or Remove a Practitioner",  
**Then** IPVerifyPractitionerDetails shall run (show condition: AddOrRemovePractioner = "Add or Remove a Practitioner").  
**When** the user selects "Update/Add/Terminate Current Office Information",  
**Then** IPVerifyPractitionerDetailsParentCOI shall run (show condition: Update/Add/TerminateCOI = "Update/Add/Terminate Current Office Information").

---

## 8. Verification Checklist for QA

- [ ] **Add or Remove a Practitioner – PNC facility:** Select a facility with HealthcareFacility.PRM_PNC__c = true → Add practitioner → Validation passes even with no PNC practitioners.
- [ ] **Add or Remove a Practitioner – Non-PNC facility:** Select a facility with HealthcareFacility.PRM_PNC__c = false → Add only non-PNC practitioners → Validation fails (PractitionerMissing or equivalent).
- [ ] **Add or Remove a Practitioner – Non-PNC facility with PNC practitioner:** Select non-PNC facility → Add at least one PNC practitioner → Validation passes.
- [ ] **Update/Add/Terminate COI – Same scenarios** as above for the COI request type.
- [ ] **Delegated group:** Select delegated facility → Add non-credentialed, non-PNC practitioner → Validation fails.
- [ ] **Delegated group with PNC practitioner:** Select delegated facility → Add non-credentialed, PNC practitioner → Validation passes.
- [ ] **Other request types:** Update Billing/Mailing Address, Patient Accept Status, Capitation Site – confirm no PNC validation errors; these flows do not call PRM_VerifyPractitionerDetails.
- [ ] **Single vs. multiple facility:** Test both single-facility and multi-facility scenarios; ProviderDetails:PNC must reflect the selected facility’s HealthcareFacility.PRM_PNC__c in both cases.

---

## 9. Summary Table

| Aspect | Detail |
|--------|--------|
| **OmniScript** | PRM_ProviderChangeForm_English |
| **Request types using PNC** | Add or Remove a Practitioner, Update/Add/Terminate Current Office Information |
| **Request types NOT using PNC** | Update Billing/Mailing Address, Patient Accept Status, Capitation Site |
| **PNC data source (current)** | Facility:Account.PRM_PNC__c (Vendor Account) |
| **PNC data source (target)** | Facility:PRM_PNC__c (HealthcareFacility) |
| **DataRaptor to update** | PRMExtractPracticeLocationsProvChange |
| **IPs using PNC** | PRM_VerifyPractitionerDetails (via PRM_VerifyPractitionerDetailsParent) |
| **OmniScript elements** | SetSelectedFacility, IPVerifyPractitionerDetails, IPVerifyPractitionerDetailsParentCOI |
| **Validation formulas** | PNCValid, DelegatedValid (in SetDelegatedPNC) |
