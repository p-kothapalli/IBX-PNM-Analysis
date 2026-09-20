# User Story 5: HealthcareFacility Trigger for PNC Rollup – OmniScript / Guided Flow Impact Analysis

## Executive Summary

**User Story 5** creates a new **HealthcareFacility trigger** that fires when `HealthcareFacility.PRM_PNC__c` is inserted or changed. The trigger rolls up PNC to practitioner accounts using the **switch-aware** rule: **ALL** participating locations PNC by default, or **ANY** location PNC when the practitioner's `Account.PRM_PNCAnyLocation__c = true`. A companion Account-trigger recompute (US5 §5.1a) also fires when `PRM_PNCAnyLocation__c` itself changes.

> **Note on logic direction:** this is **not** an unconditional "any" rollup. The default remains "all"; "any" applies only to practitioners flagged with `PRM_PNCAnyLocation__c`. See `PRM_PNC_Logic_Change_Implementation_Plan.md` US4/US5.

This analysis identifies which **OmniScripts (guided flows)** are impacted by this change, either directly (triggering the new HealthcareFacility trigger) or indirectly (displaying/using data that the trigger updates).

---

## Impact Categories

| Category | Description | OmniScripts Affected |
|----------|-------------|----------------------|
| **Direct – Trigger Fires** | Flows that update `HealthcareFacility.PRM_PNC__c` (after migration) | 1 |
| **Indirect – Requires Flow Changes** | Flows that currently update Account PNC and must switch to HealthcareFacility | 1 |
| **Indirect – Display/Validation** | Flows that display PNC or use it for validation; rely on trigger-rolled-up data | 4 |
| **DataRaptor/IP Changes** | Flows that use DataRaptors or IPs that read/write PNC | 10+ |

---

## 1. Direct Impact – OmniScripts That Will Fire the HealthcareFacility Trigger

### 1.1 PRM_PDMManualUpdate_English – Add/Remove PNC

**Impact Level:** HIGH – Direct

**Current Behavior:**
- User selects **Add/Remove PNC** as the manual update type (Vendor path).
- User selects a practice location from search results.
- User checks/unchecks PNC (CBPNCCkd / CBPNCUnCkd).
- **SV_PNC** sets `AccountToUpdate.RecordId = SelectedVendorAccount:Id` (Vendor Account).
- **PRMDRUpdateAccountPDM** updates Account.PRM_PNC__c (vendor) with `isPNC`.

**After Migration (User Story 5 + US 6/7):**
- PNC must be written to **HealthcareFacility.PRM_PNC__c** instead of Account.PRM_PNC__c.
- The selected practice location is `SelectedFacilityId` (HealthcareFacilityId) from `SetSelectedFacility`.
- A new or modified DataRaptor must update **HealthcareFacility.PRM_PNC__c** for the selected facility.
- The **HealthcareFacility trigger (US5)** will fire when this update occurs.
- The trigger will roll up to all practitioners affiliated with that practice location.

**Required Changes:**
- Replace or augment `PRMDRUpdateAccountPDM` usage for Add/Remove PNC with a DataRaptor that updates **HealthcareFacility** (e.g., new `PRMDRUpdateHealthcareFacilityPNC` or add to `PRMLoadFacilityLocAddUpdate`).
- Change `SV_PNC` to pass `SelectedFacilityId` (HealthcareFacility Id) instead of `SelectedVendorAccount:Id` when PDMManualUpdateType = "Add/Remove PNC".
- `PRM_PDMRecordsCreation` IP `DRUpdateAccount` execution condition: keep Add/Remove PNC but route to different logic (DataRaptor that updates HealthcareFacility).

**Elements Involved:**
- `PRM_PDMManualUpdate_English_Element_AddOrRemovePNCRecords` (Step)
- `PRM_PDMManualUpdate_English_Element_SV_PNC` (Set Values)
- `PRM_PDMManualUpdate_English_Element_CBPNCCkd`, `CBPNCUnCkd` (checkboxes)
- `PRM_PDMManualUpdate_English_Element_SelectedPLPNC`, `PracPNC` (display)
- `PRM_PDMManualUpdate_English_Element_ProcessMedicareNumbersAndPncData` (IP)
- `PRM_PDMManualUpdate_English_Element_IPCreatePDMRecords` → `PRM_PDMRecordsCreationParent` → `PRM_PDMRecordsCreation` → `DRUpdateAccount` (PRMDRUpdateAccountPDM)

---

## 2. Indirect Impact – OmniScripts That Display or Validate PNC

These flows rely on PNC data (practitioner rollup or facility-level). After the trigger runs, the practitioner Account.PRM_PNC__c will be correct. The **DataRaptors** that supply PNC to these flows must change per User Story 7 (Facility:Account.PRM_PNC__c → Facility:PRM_PNC__c). The OmniScripts themselves may need minimal or no changes if the DataRaptor output structure remains the same.

### 2.1 PRM_OffCycleCredentialing_English

**Impact Level:** MEDIUM

**Usage:**
- Displays PNC for group and facility in provider search results.
- **SetErrorsWhenPracTrueandAccFalse** – validation when practitioner PNC = true but facility PNC = false.
- **TextBlock14**, **TextBlock15** – error messages for PNC consistency.

**Data Source:** DataRaptors that return facility PNC (e.g., `PRMFetchVendorAndHCFWithNPI`, `PRMExtractPracticeLocationsProvChange`) – use `Facility:Account.PRM_PNC__c` today.

**Change:** DataRaptors updated per US7 → `Facility:PRM_PNC__c`. OmniScript validation logic unchanged; only data source path changes.

---

### 2.2 PRM_PractitionerTerminationForm_English

**Impact Level:** MEDIUM

**Usage:**
- **PracLocPNC** – displays practice location PNC for termination.

**Data Source:** DataRaptors that return `HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c` → `HealthcarePractitionerFacility:HealthcareFacility.PRM_PNC__c`.

**Change:** DataRaptor path update per US7.

---

### 2.3 PRM_PractitionerTerminationRecredForm_English

**Impact Level:** MEDIUM

**Usage:**
- **PracLocPNC** – displays practice location PNC for recred termination.

**Change:** Same as 2.2.

---

### 2.4 PRM_ProviderChangeForm_English

**Impact Level:** MEDIUM

**Usage:**
- **PRM_VerifyPractitionerDetailsParent** / **PRM_VerifyPractitionerDetails** – SetDelegatedPNC, PNCValid validation.
- PNCValid: when selected facility is PNC, validation passes; otherwise at least one PNC practitioner required.
- Facility PNC comes from DataRaptors.

**Change:** DataRaptors updated; IP `PRM_VerifyPractitionerDetails` updated per US8.

---

## 3. PNC-Specific OmniScripts (Display/Update Practitioner PNC)

### 3.1 PRM_PNCReview_English

**Impact Level:** MEDIUM

**Usage:**
- PNC case review flow.
- **IPPNCRecordsUpdate** → `PRM_PNCRecordsUpdateParent` – updates practitioner/case records.
- Displays practitioner PNC, practice location data.

**Note:** `PRM_PNCRecordsUpdateParent` likely updates **practitioner Account.PRM_PNC__c** (rollup) or IndividualApplication. The practitioner PNC is the **rollup** value – the trigger (US5) keeps it in sync when HealthcareFacility.PRM_PNC__c changes. No direct OmniScript change for the trigger; DataRaptors that supply PNC data need updates.

---

### 3.2 PRM_PNCQC_English

**Impact Level:** MEDIUM

**Usage:**
- **PractitionerPNC** – displays practitioner PNC.
- **IPPNCRecordsUpdate** → `PRM_PNCPDAReviewUpdateParent`.

**Change:** DataRaptor/IP updates for PNC data source.

---

### 3.3 PRM_PNCPDA_English

**Impact Level:** MEDIUM

**Usage:**
- **PractitionerPNC** – displays practitioner PNC.
- **IPPNCRecordsUpdate** → `PRM_PNCPDAReviewUpdateParent`.

**Change:** Same as 3.2.

---

## 4. Practitioner Participation Form (User Story 3 – Separate Scope)

### 4.1 PRM_PractitionerParticipationForm_English

**Impact Level:** LOW for US5

**Note:** This flow is covered in **User Story 3**. It does **not** use `getPIdToHCPFList` or `updateAccountPNCHelper`. It uses:
- `PRM_RecordQueryServiceUtils.getGroupDataForTaxIdNPI` (Apex)
- `PRM_PractitionerScreenRecordCreation` (SV_PNCFlag, PNCFlag)
- `PRMDRCreateCaseCaseManagerAndAccount`

The Practitioner Participation flow determines PNC at **creation time** (onboarding). It does not update HealthcareFacility.PRM_PNC__c. The HealthcareFacility trigger (US5) fires when **existing** HealthcareFacility records are updated. New practitioner onboarding may create HCPF records but typically does not update HealthcareFacility.PRM_PNC__c directly in this flow.

**Conclusion:** No direct impact from US5 trigger. Covered in US3 for PNC determination logic change.

---

## 5. Integration Procedures and DataRaptors Used by OmniScripts

| Component | Used By | PNC Change |
|-----------|---------|------------|
| **PRM_PDMRecordsCreation** | PRM_PDMManualUpdate_English | DRUpdateAccount (PRMDRUpdateAccountPDM) – for Add/Remove PNC, must switch to update HealthcareFacility |
| **PRM_ProcessMedicareNumbersAndPncData** | PRM_PDMManualUpdate_English | Transforms PNC data; feeds AccountToUpdate |
| **PRM_VerifyPractitionerDetails** | PRM_PDMManualUpdate_English, PRM_ProviderChangeForm_English | SetDelegatedPNC – facility PNC from DataRaptor |
| **PRM_RecredTerminationLetter** | RCAT / Recred flows | FilterHCPFRecords – `Account:PRM_PNC__c != true` → `HealthcareFacility:PRM_PNC__c != true` |
| **PRM_GetRelatedDataforPNCAndDelegatedRCATReview** | PRM_ReviewRCAT_English | DataRaptor filter `Account.PRM_PNC__c == false` → `HealthcareFacility.PRM_PNC__c == false` |
| **PRM_FetchPractitionerDemographics** | FlexCards, demographics | PractitionerData:PNC from Account.PRM_PNC__c (rollup – no change) |

---

## 6. DataRaptors Referencing PNC (User Story 7)

These DataRaptors feed OmniScripts. Path changes required:

| DataRaptor | Path Change | Feeds OmniScript |
|------------|-------------|------------------|
| PRMExtractPracticeLocationsProvChange | Facility:Account.PRM_PNC__c → Facility:PRM_PNC__c | Provider Change flows |
| PRMExtractPracticeLocationsAncillaryChange | Same | Ancillary flows |
| PRMExtractPracticeLocationsPARChange | Same | PAR flows |
| PRMFetchVendorAndHCFWithNPI | Facility:Account.PRM_PNC__c → Facility:PRM_PNC__c | PDM Manual Update, Off-Cycle |
| PRMDRExtractVendorPracticeLocations | Same | PDM, Provider Change |
| PRMExtractLocationsforHCPNPI | HealthcarePractitionerFacility:HealthcareFacility.Account.PRM_PNC__c → HealthcareFacility.PRM_PNC__c | Termination, Recred |
| PRMDRGetLocationTerminationData | Same | Termination |
| PRMDRExtractHCPFDetails | Account.PRM_PNC__c (HCPF context) | Recred Termination Letter |
| PRMGetRelatedDataforPNCAndDelegatedRCATReview | Account.PRM_PNC__c → HealthcareFacility.PRM_PNC__c | Review RCAT |

---

## 7. Summary Table – OmniScripts Impacted by User Story 5

| OmniScript | Impact Type | Change Required |
|------------|-------------|-----------------|
| **PRM_PDMManualUpdate_English** | Direct | Add/Remove PNC path: Update HealthcareFacility.PRM_PNC__c instead of Account; new/modified DataRaptor; SV_PNC to pass FacilityId |
| **PRM_OffCycleCredentialing_English** | Indirect | DataRaptor path updates (US7); validation logic unchanged |
| **PRM_PractitionerTerminationForm_English** | Indirect | DataRaptor path for PracLocPNC |
| **PRM_PractitionerTerminationRecredForm_English** | Indirect | DataRaptor path for PracLocPNC |
| **PRM_ProviderChangeForm_English** | Indirect | PRM_VerifyPractitionerDetails IP + DataRaptors |
| **PRM_PNCReview_English** | Indirect | DataRaptor path for PNC display |
| **PRM_PNCQC_English** | Indirect | DataRaptor path for PractitionerPNC |
| **PRM_PNCPDA_English** | Indirect | DataRaptor path for PractitionerPNC |
| **PRM_ReviewRCAT_English** | Indirect | PRM_GetRelatedDataforPNCAndDelegatedRCATReview DataRaptor |
| **PRM_PractitionerParticipationForm_English** | None (US3) | Covered in User Story 3 |

---

## 8. Implementation Order for OmniScript/Flow Changes

1. **User Story 5** – Create HealthcareFacility trigger (Apex).
2. **User Story 7** – Update DataRaptors (Facility:Account.PRM_PNC__c → Facility:PRM_PNC__c).
3. **User Story 8** – Update Integration Procedures (PRM_RecredTerminationLetter, PRM_VerifyPractitionerDetails, etc.).
4. **PDM Add/Remove PNC Flow** – Create/modify DataRaptor to update HealthcareFacility.PRM_PNC__c; update PRM_PDMManualUpdate_English and PRM_PDMRecordsCreation to use it for Add/Remove PNC.
5. **User Stories 9 & 10** – Validate Credentialing and PDM flows end-to-end.

---

## 9. Key Takeaway

**User Story 5** (HealthcareFacility trigger) does not modify OmniScripts directly. The trigger is **Apex-only**. However:

- **One OmniScript** (**PRM_PDMManualUpdate_English** – Add/Remove PNC) must be changed to **write** to HealthcareFacility.PRM_PNC__c instead of Account.PRM_PNC__c. That write will cause the new trigger to fire.
- **Several OmniScripts** display PNC or use it for validation. They are impacted **indirectly** via DataRaptor and IP changes (User Stories 7 and 8). The trigger ensures practitioner Account.PRM_PNC__c stays in sync when practice locations change.
