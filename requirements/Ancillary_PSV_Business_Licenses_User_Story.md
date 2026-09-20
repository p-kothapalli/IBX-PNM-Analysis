# User Story: Display Business Licenses on Ancillary PSV – Verify Licensure Step

**Persona:** Credentialing Specialist  
**Priority:** P1  
**OmniScripts:** PRM_AncillaryPSVForm_English, PRM_AncillaryReassessmentPSV_English  
**Integration Procedures:** PRM_AncillaryPSVFormDataRetrievalIP, PRM_FetchAncillaryReassessmentPSV

---

## Story

**As a** Credentialing Specialist,  
**I want** to see all Business License records for the ancillary facility on the Verify Licensure step in both the Ancillary PSV form and the Ancillary Reassessment PSV form, **and** add new licenses via an "Add New" button with a Practice Location dropdown and validation to prevent duplicates,  
**So that** I can verify licensure details (license number, state, effective date, expiration date, status, verified date) before completing primary source verification, and add new licenses when needed without creating duplicates.

**Why it matters:** Business licenses are required for ancillary credentialing. Without proper display of existing licenses on the Verify Licensure step, specialists cannot efficiently review and verify licensure status. The ability to add new licenses with duplicate prevention ensures data integrity.

---

## Scope

| Flow | OmniScript | Verify Licensure Step | Data Source |
|------|------------|----------------------|-------------|
| **Ancillary PSV (Initial)** | PRM_AncillaryPSVForm_English | VerifyLicensure | PRM_AncillaryPSVFormDataRetrievalIP → PRMDRExtractCaseRelatedDataforAncillaryPSVForm |
| **Ancillary Reassessment PSV** | PRM_AncillaryReassessmentPSV_English | VerifyLicensure | PRM_FetchAncillaryReassessmentPSV → DRExtractAncAssessNpiLocDetails:BL |

---

## Current State (from codebase)

### Ancillary PSV Form (Initial)

- **VerifyLicensure** step contains **VerifyLicensureBusinessLicense** Edit Block.
- **PRM_AncillaryPSVFormDataRetrievalIP** does **not** map `VerifyLicensure:VerifyLicensureBusinessLicense` in its Response Action.
- **PRMDRExtractCaseRelatedDataforAncillaryPSVForm** does not appear to output Business License data.

### Ancillary Reassessment PSV

- **VerifyLicensure** step contains **VerifyLicensureBusinessLicense** Edit Block and **NewBusinessLicenseBlk** for adding new licenses.
- **PRM_FetchAncillaryReassessmentPSV** maps `VerifyLicensure:VerifyLicensureBusinessLicense` = `%DRExtractAncAssessNpiLocDetails:BL%`.
- **BlPresent** controls visibility: `ISNOTBLANK(DRExtractAncAssessNpiLocDetails:BL)`.
- **DRExtractAncAssessNpiLocDetails** returns BL (Business License list) for the ancillary assessment.
- **NewBusinessLicenseBlk** exists but may need Practice Location dropdown and validation rules added.

### Common Configuration Issue

Both forms use **VerifyLicensureBusinessLicense** Edit Block with:
- `selectSobject: "HierCondHlthRskAdjFctrFeed"` (likely incorrect; should be `BusinessLicense` or custom mapping).
- `sobjectMapping: []` (empty).
- Business licenses for ancillary are linked via `BusinessLicense.PRM_HealthcareFacility__c` to the facility.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **PRM_AncillaryPSVFormDataRetrievalIP** | Integration Procedure | Add Business License extraction (e.g., via DR or Apex) for the facility and map `VerifyLicensure:VerifyLicensureBusinessLicense` in AncillaryResponseAction. |
| **PRMDRExtractCaseRelatedDataforAncillaryPSVForm** | DataRaptor | If not present, add output for Business License records (BL) linked to the ancillary facility. Query by `PRM_HealthcareFacility__c` on the facility. |
| **VerifyLicensureBusinessLicense** (Ancillary PSV) | OmniScript Edit Block | Update `selectSobject` to `BusinessLicense` and configure `sobjectMapping` for fields: LicenseNumber, PRM_LicenseState__c, PRM_ProviderLicenseEffectiveDate__c, PRM_ProviderLicenseExpirationDate__c, PRM_Status__c, PRM_VerifiedOn__c, PRM_LicenseClass__c, PRM_HealthcareFacility__c. Enable **Add New** (`allowNew: true`), set `newLabel` to "Add New". |
| **VerifyLicensureBusinessLicense** (Ancillary Reassessment) | OmniScript Edit Block | Same as above: correct `selectSobject` and `sobjectMapping`; enable Add New button. |
| **New Business License Block** | OmniScript | Add/configure New Business License block with: License Number*, License State*, Provider License Effective Date, Provider License Expiration Date, Status*, Verified On, License Class, Account Name (read-only), **Practice Location dropdown** (PRM_HealthcareFacility__c). |
| **Validation** | Apex / OmniScript / DR | Implement duplicate check: same License State + License Number + License Class + Practice Location. Return user-friendly error on save. |
| **ReviewLicensure** (Ancillary Reassessment) | OmniScript | Ensure `VerifyLicensure:LicensureReview` is populated and displayed on ReviewScreen. |

### Business License Fields to Display (Table)

| Field | API Name | Notes |
|-------|----------|-------|
| License Number | LicenseNumber | |
| License State | PRM_LicenseState__c | |
| Effective Date | PRM_ProviderLicenseEffectiveDate__c | |
| Expiration Date | PRM_ProviderLicenseExpirationDate__c | |
| Status | PRM_Status__c | |
| Verified On | PRM_VerifiedOn__c | |
| License Class | PRM_LicenseClass__c | |
| Account Name | (via Account) | For display context |

### Add New Button & New Entry Form

The Business License table shall include an **"Add New"** button. When clicked, a new row/form shall open with the following fields (per screenshot):

| Field | API Name | Required | Type | Notes |
|-------|----------|----------|------|-------|
| *License Number | LicenseNumber | Yes | Text | |
| *License State | PRM_LicenseState__c | Yes | Dropdown | |
| Provider License Effective Date | PRM_ProviderLicenseEffectiveDate__c | No | Date | Date picker |
| Provider License Expiration Date | PRM_ProviderLicenseExpirationDate__c | No | Date | Date picker |
| *Status | PRM_Status__c | Yes | Dropdown | |
| Verified On | PRM_VerifiedOn__c | No | Date | Date picker |
| License Class | PRM_LicenseClass__c | No | Dropdown/Text | May be pre-filled (e.g., SBRD) |
| Account Name | (via Account) | No | Read-only | Display only; grayed out |
| **Practice Location** | PRM_HealthcareFacility__c | Yes | **Dropdown** | **New field** – select the practice location (HealthcareFacility) for this license |

### Validation Rules

**Duplicate Prevention:** The system shall prevent adding a Business License when a record already exists with the **same combination** of:
- **License State** (PRM_LicenseState__c)
- **License Number** (LicenseNumber)
- **License Class** (PRM_LicenseClass__c)
- **Practice Location** (PRM_HealthcareFacility__c)

**Implementation options:**
- **Client-side:** Validate before submit; show error message if duplicate detected.
- **Server-side:** Apex/Integration Procedure validates on save; return error if duplicate.
- **Salesforce:** Duplicate Rule or Validation Rule on BusinessLicense object (if applicable).

**Error message (example):** *"A license with this License Number, License State, and License Class already exists for the selected Practice Location."*

### Data Flow for Ancillary Reassessment (Reference)

```
DRExtractAncAssessNpiLocDetails (BL)
→ PRM_FetchAncillaryReassessmentPSV: AncillaryAssessmentResponse
→ VerifyLicensure:VerifyLicensureBusinessLicense
```

### Data Flow for Ancillary PSV Initial (To Be Implemented)

```
PRMDRExtractCaseRelatedDataforAncillaryPSVForm (or new DR)
→ PRM_AncillaryPSVFormDataRetrievalIP: AncillaryResponseAction
→ VerifyLicensure:VerifyLicensureBusinessLicense
```

---

## Acceptance Criteria

### Ancillary PSV Form (Initial)

**Given** the Credentialing Specialist opens the Ancillary PSV form for an ancillary case with Business License records linked to the facility,  
**When** they navigate to the Verify Licensure step,  
**Then** all Business License records for the ancillary facility shall be displayed in a table or list.  
**And** each record shall show License Number, License State, Effective Date, Expiration Date, Status, and Verified On (where applicable).  
**And** the specialist can use "View More" to see full details when applicable.

### Ancillary Reassessment PSV

**Given** the Credentialing Specialist opens the Ancillary Reassessment PSV form for an ancillary case with Business License records,  
**When** they navigate to the Verify Licensure step,  
**Then** all Business License records for the ancillary facility shall be displayed in a table or list.  
**And** each record shall show License Number, License State, Effective Date, Expiration Date, Status, and Verified On (where applicable).  
**And** when BlPresent is true, the Business License block shall be visible.  
**And** on the Review screen, the Licensure Review value shall reflect the verification outcome.

### Add New Button & New Entry Form

**Given** the Credentialing Specialist is on the Verify Licensure step,  
**When** they click the **"Add New"** button on the Business License table,  
**Then** a new entry form shall open with the following fields (per design):  
- **License Number** (required, text)  
- **License State** (required, dropdown)  
- **Provider License Effective Date** (date picker)  
- **Provider License Expiration Date** (date picker)  
- **Status** (required, dropdown)  
- **Verified On** (date picker)  
- **License Class** (dropdown/text)  
- **Account Name** (read-only, display)  
- **Practice Location** (required, dropdown) – select the practice location (HealthcareFacility) for this license  

**And** the specialist can save the new license after filling required fields.

### Validation Rules

**Given** the specialist attempts to add a new Business License with License State = "PA", License Number = "12345", License Class = "SBRD", and Practice Location = "Facility A",  
**When** a record already exists with the same License State, License Number, License Class, and Practice Location,  
**Then** the system shall reject the save and display an error message: *"A license with this License Number, License State, and License Class already exists for the selected Practice Location."*  

**And** the specialist can correct the duplicate (e.g., change License Number or select a different Practice Location) and proceed.

### Both Flows

**Given** the ancillary facility has no Business License records,  
**When** the specialist reaches the Verify Licensure step,  
**Then** the Business License block shall be hidden or show an appropriate message (e.g., "No licenses on file").  
**And** the specialist can add new licenses via the **"Add New"** button on the Business License table.

---

## Dependencies

- Business License records must be linked to `HealthcareFacility` via `PRM_HealthcareFacility__c`.
- Facility context must be available from the Case Manager / Ancillary Assessment.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `vlocity_export/OmniScript/PRM_AncillaryPSVForm_English/PRM_AncillaryPSVForm_English_Element_VerifyLicensureBusinessLicense.json` | Edit Block for initial Ancillary PSV |
| `vlocity_export/OmniScript/PRM_AncillaryReassessmentPSV_English/PRM_AncillaryReassessmentPSV_English_Element_VerifyLicensureBusinessLicense.json` | Edit Block for Ancillary Reassessment |
| `vlocity_export/OmniScript/PRM_AncillaryReassessmentPSV_English/PRM_AncillaryReassessmentPSV_English_Element_NewBusinessLicenseBlk.json` | New Business License block (Ancillary Reassessment) – add Practice Location dropdown, validation |
| `vlocity_export/IntegrationProcedure/PRM_AncillaryPSVFormDataRetrievalIP/PRM_AncillaryPSVFormDataRetrievalIP_Element_AncillaryResponseAction.json` | Response mapping for initial Ancillary PSV |
| `vlocity_export/IntegrationProcedure/PRM_FetchAncillaryReassessmentPSV/PRM_FetchAncillaryReassessmentPSV_Element_AncillaryAssessmentResponse.json` | Response mapping for Ancillary Reassessment |
| `force-app/main/default/objects/BusinessLicense/` | BusinessLicense object – PRM_HealthcareFacility__c (Practice Location) |

---

*Source: Codebase analysis. PRM_AncillaryPSVForm_English, PRM_AncillaryReassessmentPSV_English, PRM_AncillaryPSVFormDataRetrievalIP, PRM_FetchAncillaryReassessmentPSV.*
