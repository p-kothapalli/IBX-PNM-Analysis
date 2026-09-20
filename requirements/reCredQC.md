# ReCredQC Omniscript - Editable Review Fields & Notes Analysis

## Executive Summary
Business has requested that review fields in the ReCredQC Omniscript be made editable on each step, with the ability to add notes similar to the PrimarySourceVerificationReview (PSV) omniscript. This document provides a deep-dive analysis comparing the two omniscripts and outlines required changes.

---

## Current State Analysis

### ReCredQC Omniscript - Current Implementation

#### 1. CAQH Signature & Attestation Step
**Element:** `CAQHSignatureAttestRD`
- **Type:** Radio
- **Current Status:** `"readOnly": true` ❌
- **Options:** 
  - "Data Looks Good"
  - "Missing Information"
- **Default Value:** `%CaseManager:PRM_CAQHAttestation__c%`
- **Note Field:** ❌ **NOT PRESENT**

#### 2. Service Area Verification Step  
**Element:** `ReCredServiceAreaVerification`
- **Type:** Radio
- **Current Status:** `"readOnly": true` ❌
- **Options:**
  - "Data Looks Good"
  - "Provider Outreach Needed"
  - "Moved State"
  - "Missing Information"
- **Default Value:** null (not pre-populated)
- **Note Field:** ❌ **NOT PRESENT**

#### 3. Data Saving Mechanism
**SetRecord Actions:** `SetRecordRecredQC_CR`, `SetRecordRecredQC_MDR`, `SetRecordRecredQC_FD`
- **ContentNote:** Creates a single note with `%ReCredQCNote%`
- **IndividualApplication:** Updates only high-level fields like:
  - `MedicalDirectorReview`
  - `PRM_RecredTerm__c`
  - `PRM_RoutineCommittee__c`
  - `PRM_Stage__c`
  - `Status`

**❌ MISSING:** Individual verification step responses (CAQH Signature, Service Area, License, Specialty, etc.) are **NOT** saved to IndividualApplication fields

---

### PrimarySourceVerificationReview (PSV) - Reference Implementation

#### 1. Service Area Verification Step (Sub-OmniScript: PSVSubOsTxnyRole)
**Radio Element:** `ServiceAreaVerificationRD`
- **Type:** Radio
- **Current Status:** `"readOnly": true` (initially)
- **Options:**
  - "Data Looks Good"
  - "Missing Information"
- **Default Value:** `%CaseManager:PRM_ServiceAreaPSV__c%`
- **Conditional Visibility:** Shows only when `CaseType = "QC Review"` AND `IsRecredentialing = false`

**Note Element:** `ServiceAreaNote`
- **Type:** Text Area ✅
- **Status:** `"readOnly": false` ✅
- **Required:** true
- **Max Length:** 5000
- **Label:** "Service Area Note"

#### 2. Specialty Verification Step
**Radio Element:** `SpecialtyVerificationRD`
- **Type:** Radio
- **Options:**
  - "Data Looks Good"
  - "Missing Information"
  - "Unable to Proceed"
- **Default Value:** `%CaseManager:PRM_SpecialityPSV__c%`

**Note Element:** `NoteSpecialty`
- **Type:** Text Area ✅
- **Status:** `"readOnly": false` ✅
- **Required:** true
- **Max Length:** 5000
- **Label:** "Specialty Note"

#### 3. Data Saving Mechanism
**SetRecord Actions:** `SetRecordPSVQC`, `SetRecordReCredPSV`

**For Initial Credentialing (SetRecordPSVQC):**
```json
"IndividualApplication": {
    "CAQHSignatureAttestation": "%CAQHSignatureAttestationFormula%",
    "ServiceAreaVerification": "%ServiceAreaVerificationFormula%",
    "LicenseVerification": "%LicenseVerificationFormula%",
    "SpecialtyVerification": "%SpecialtyVerificationFormula%",
    "AdmittingPrivilegesReview": "%AdmittingPrivilegesReviewFormula%",
    "InsuranceVerification": "%InsuranceVerificationFormula%",
    "WorkHistoryVerification": "%WorkHistoryVerificationFormula%",
    "DEAVerification": "%DEAVerificationFormula%",
    "CDSVerification": "%CDSVerificationFormula%",
    "DisclosureReview": "%DisclosureReviewFormula%",
    "BoardCertificationVerification": "%BoardCertificationVerificationFormula%",
    "FSMBVerification": "%FSMBVerificationFormula%",
    "MedicareOptOutReview": "%MedicareOptOutReviewFormula%",
    "SAMReview": "%SAMReviewFormula%",
    "NPDBVerified": "%NPDBVerifiedFormula%",
    "NPDBVerifiedOn": "%NPDBVerifiedOnFormula%",
    "EducationVerification": "%EducationVerificationFormula%",
    ...
}
```

**For Re-Credentialing (SetRecordReCredPSV):**
```json
"IndividualApplication": {
    "CAQHSignatureAttestation": "%ReCredCAQHSignatureFRML%",
    "ServiceAreaVerification": "%ReCredServiceAreaVeriFRML%",
    "LicenseVerification": "%ReCredLicenseVeriFRML%",
    "SpecialtyVerification": "%ReCredSpecialtyVeriFRML%",
    "AdmittingPrivilegesReview": "%ReCredAdmitPrivilegeFRML%",
    "InsuranceVerification": "%ReCredInsuranceVeriFRML%",
    "WorkHistoryVerification": "%ReCredWHVeriFRML%",
    "DEAVerification": "%ReCredDEAVeriFRML%",
    "CDSVerification": "%ReCredCDSVeriFRML%",
    "DisclosureReview": "%ReCredDisclosureReviewFRML%",
    "BoardCertificationVerification": "%ReCredBoardVeriFRML%",
    "FSMBVerification": "%ReCredFSMBVeriFRML%",
    "MedicareOptOutReview": "%ReCredMediCareReviewFRML%",
    "SAMReview": "%ReCredSAMReviewFRML%",
    "NPDBVerified": "%ReCredNPDBVerifiedFRML%",
    "NPDBVerifiedOn": "%ReCredNPDBVerifiedOnFRML%",
    ...
}
```

**ContentNote:**
```json
"ContentNote": {
    "content": "=%ProceedToNote%",  // or "%ReCredNote%" for recred
    "entityId": "%CaseManager:Id%",
    "title": "PSV to QC Review"
}
```

**MissingInfoNote:**
```json
"MissingInfoNote": "%MissingInfoNote%"
```

---

## Gap Analysis

### 🔴 Critical Gaps in ReCredQC

| Step/Field | ReCredQC Status | PSV Status | Gap |
|------------|----------------|------------|-----|
| **Radio Button Editability** | Read-Only | Read-Only (but with edit capability) | Need to make editable |
| **Note Fields** | Missing | Present (Text Area, required) | Need to add notes |
| **Save to IndividualApplication** | Only saves high-level fields | Saves all verification responses | Need to save all step responses |
| **Individual Step Notes** | Missing | Saved per step | Need step-specific notes |
| **Conditional Visibility** | Not configured | Configured based on case type | May need conditional logic |

### Verification Steps Requiring Changes

Based on the ReCredQC DataPack, the following verification steps need editable radio buttons and note fields:

1. **CAQH Signature & Attestation** - `CAQHSignatureAttestRD`
2. **Service Area Verification** - `ReCredServiceAreaVerification`
3. **License Verification** - `LicenseVerifcationRD`
4. **Specialty Verification** - `SpecialtyVerificationRD`
5. **Admitting Privileges** - `Radio6`
6. **Insurance Verification** - `Radio7` / `ReCredInsVerification`
7. **Work History** - `Radio8`
8. **Education Verification** - `Radio9` / `EducationVerificationOutcome`
9. **DEA Verification** - `DEAVerificationRadio`
10. **CDS Verification** - `CDSVerificationRadio`
11. **Disclosure Questions** - `DisclosureRadio`
12. **Board Certifications** - `BoardCertificationRadio`
13. **Medicare Opt Out** - `Radio14`
14. **NPDB Review** - (Checkbox-based, may need radio option)

---

## Recommended Changes

### Phase 1: Add Note Fields to Each Verification Step

For each verification step, add a **Text Area** element immediately after the radio button:

#### Example 1: CAQH Signature & Attestation Step

**New Element:** `CAQHSignatureAttestNote`
```json
{
    "Name": "CAQHSignatureAttestNote",
    "ParentElementName": "CAQHSignatureAttestionStep",
    "ParentElementType": "Step",
    "Type": "Text Area",
    "PropertySetConfig": {
        "label": "CAQH Signature & Attestation Note",
        "readOnly": false,
        "required": true,
        "maxLength": 5000,
        "controlWidth": 6,
        "inputWidth": 12,
        "show": null
    }
}
```

#### Example 2: Service Area Verification Step

**New Element:** `ServiceAreaVerificationNote`
```json
{
    "Name": "ServiceAreaVerificationNote",
    "ParentElementName": "ServiceAreaVerificationStep",
    "ParentElementType": "Step",
    "Type": "Text Area",
    "PropertySetConfig": {
        "label": "Service Area Verification Note",
        "readOnly": false,
        "required": true,
        "maxLength": 5000,
        "controlWidth": 6,
        "inputWidth": 12,
        "show": null
    }
}
```

**Apply the same pattern for all 14 verification steps listed above.**

---

### Phase 2: Make Radio Buttons Editable

For each radio button element, change:
- `"readOnly": true` → `"readOnly": false`

#### Files to Modify:
- `PRM_RecredQC_English_Element_CAQHSignatureAttestRD.json`
- `PRM_RecredQC_English_Element_ReCredServiceAreaVerification.json`
- `PRM_RecredQC_English_Element_LicenseVerifcationRD.json`
- `PRM_RecredQC_English_Element_SpecialtyVerificationRD.json`
- `PRM_RecredQC_English_Element_Radio6.json` (Admitting Privileges)
- `PRM_RecredQC_English_Element_Radio7.json` (Insurance)
- `PRM_RecredQC_English_Element_Radio8.json` (Work History)
- `PRM_RecredQC_English_Element_Radio9.json` (Education)
- `PRM_RecredQC_English_Element_DEAVerificationRadio.json`
- `PRM_RecredQC_English_Element_CDSVerificationRadio.json`
- `PRM_RecredQC_English_Element_DisclosureRadio.json`
- `PRM_RecredQC_English_Element_BoardCertificationRadio.json`
- `PRM_RecredQC_English_Element_Radio14.json` (Medicare Opt Out)

---

### Phase 3: Update SetRecord Actions

Update the `SetRecordRecredQC_CR`, `SetRecordRecredQC_MDR`, and `SetRecordRecredQC_FD` to save all verification responses to the IndividualApplication object.

#### Add to IndividualApplication section:
```json
"IndividualApplication": {
    "Id": "%CaseManagerId%",
    
    // Add these new fields:
    "CAQHSignatureAttestation": "%ReCredCAQHSignatureFRML%",
    "ServiceAreaVerification": "%ReCredServiceAreaVeriFRML%",
    "LicenseVerification": "%ReCredLicenseVeriFRML%",
    "SpecialtyVerification": "%ReCredSpecialtyVeriFRML%",
    "AdmittingPrivilegesReview": "%ReCredAdmitPrivilegeFRML%",
    "InsuranceVerification": "%ReCredInsuranceVeriFRML%",
    "WorkHistoryVerification": "%ReCredWHVeriFRML%",
    "EducationVerification": "%ReCredEducationVeriFRML%",
    "DEAVerification": "%ReCredDEAVeriFRML%",
    "CDSVerification": "%ReCredCDSVeriFRML%",
    "DisclosureReview": "%ReCredDisclosureReviewFRML%",
    "BoardCertificationVerification": "%ReCredBoardVeriFRML%",
    "FSMBVerification": "%ReCredFSMBVeriFRML%",
    "MedicareOptOutReview": "%ReCredMediCareReviewFRML%",
    "SAMReview": "%ReCredSAMReviewFRML%",
    "NPDBVerified": "%ReCredNPDBVerifiedFRML%",
    "NPDBVerifiedOn": "%ReCredNPDBVerifiedOnFRML%",
    "CMSPreclusionReview": "%ReCredCMSPreclusionFRML%",
    
    // Existing fields:
    "MedicalDirectorReview": "=IF(%ReCredProceedTo% == 'Medical Director Review', true, NULL)",
    "PRM_RecredTerm__c": "=IF(%ReCredProceedTo% == 'Route to Final Development', true, NULL)",
    "PRM_RoutineCommittee__c": "=IF(%ReCredProceedTo% == 'Committee Review', true, NULL)",
    "PRM_Stage__c": "...",
    "Status": "..."
}
```

#### Update ContentNote to include step-specific notes:
```json
"ContentNote": {
    "content": "=%ReCredQCNoteCompiled%",  // This should be a compiled note of all step notes
    "entityId": "%CaseManager:Id%",
    "title": "Recred QC to [Destination]"
}
```

**Create Formula Fields** to compile all step notes into a single content note or save them individually.

---

### Phase 4: Create Formula Fields for Review Responses

Similar to PSV, create formula fields for each verification step. These formulas likely exist in ReCredQC DataPack already (e.g., `%ReCredCAQHSignatureFRML%`). Verify they are correctly mapping the radio button values.

#### Pattern for Formula Fields:
- `CAQHSignatureAttestRD` → `%ReCredCAQHSignatureFRML%`
- `ReCredServiceAreaVerification` → `%ReCredServiceAreaVeriFRML%`
- `LicenseVerifcationRD` → `%ReCredLicenseVeriFRML%`
- etc.

**Check if these formulas exist and are active:**
- `PRM_RecredQC_English_Element_ReCredCAQHSignatureFRML.json`
- `PRM_RecredQC_English_Element_ReCredServiceAreaVeriFRML.json`
- etc.

---

## Data Flow Comparison

### PSV Data Flow (Reference)
1. User selects radio option (e.g., "Data Looks Good", "Missing Information")
2. User enters note in Text Area field (required)
3. User proceeds through steps
4. On submission:
   - Radio values saved to `IndividualApplication.[FieldName]` (e.g., `ServiceAreaVerification`)
   - Notes compiled and saved to `ContentNote.content`
   - Case status updated
   - New case created if needed

### ReCredQC Data Flow (Current - Gaps Identified)
1. User **CANNOT** edit radio options (read-only) ❌
2. No note field available ❌
3. On submission:
   - Only high-level fields saved to IndividualApplication ❌
   - Single `ReCredQCNote` saved to ContentNote ✅
   - Individual step responses **NOT** saved ❌

### ReCredQC Data Flow (Proposed - After Changes)
1. User selects radio option (editable) ✅
2. User enters note in Text Area field (required) ✅
3. User proceeds through steps
4. On submission:
   - Radio values saved to `IndividualApplication.[FieldName]` ✅
   - Step-specific notes compiled and saved to `ContentNote.content` ✅
   - All verification responses tracked in IndividualApplication ✅
   - Case status updated
   - New case created if needed

---

## Radio Button Options Per Step

| Step | Radio Options | Notes |
|------|---------------|-------|
| **CAQH Signature & Attestation** | • Data Looks Good<br>• Missing Information | 2 options |
| **Service Area Verification** | • Data Looks Good<br>• Provider Outreach Needed<br>• Moved State<br>• Missing Information | 4 options - Most comprehensive |
| **License Verification** | (TBD - need to check element) | |
| **Specialty Verification** | • Data Looks Good<br>• Missing Information<br>• Unable to Proceed | 3 options |
| **Admitting Privileges** | (TBD) | |
| **Insurance Verification** | (TBD) | |
| **Work History** | (TBD) | |
| **Education** | (TBD) | |
| **DEA** | (TBD) | |
| **CDS** | (TBD) | |
| **Disclosure** | (TBD) | |
| **Board Certification** | (TBD) | |
| **Medicare Opt Out** | (TBD) | |

**Action:** Review all radio button elements to document current options and ensure they align with business requirements.

---

## Implementation Checklist

### ✅ Configuration Changes Required

- [ ] **Add Text Area (Note) fields** to all 14 verification steps
- [ ] **Change `readOnly: false`** for all radio button elements (14 elements)
- [ ] **Update SetRecord actions** (SetRecordRecredQC_CR, SetRecordRecredQC_MDR, SetRecordRecredQC_FD) to save:
  - Individual step verification responses to IndividualApplication
  - Step-specific notes (either compiled or individual)
- [ ] **Verify Formula Fields** exist and are active for all verification steps
- [ ] **Test conditional visibility** logic if needed (based on case type)
- [ ] **Update DataPack** with new elements and ordering

### ✅ Testing Requirements

- [ ] Verify radio buttons are editable on each step
- [ ] Verify note fields appear and accept input (5000 char limit)
- [ ] Verify notes are required before proceeding
- [ ] Verify data saves correctly to:
  - `Case` record
  - `IndividualApplication` record
  - `ContentNote` records
- [ ] Verify correct field values when:
  - "Data Looks Good" selected
  - "Missing Information" selected  
  - "Provider Outreach Needed" selected
  - "Moved State" selected
  - Other options per step
- [ ] Verify backward compatibility with existing records
- [ ] Verify performance (no slowdowns with additional fields)

---

## Salesforce Object Fields to Verify

Ensure the following fields exist on the **IndividualApplication** (Case Manager) object:

- `PRM_CAQHAttestation__c`
- `PRM_ServiceAreaPSV__c`
- `PRM_LicensePSV__c`
- `PRM_SpecialityPSV__c`
- `PRM_AdmittingPrivilegesPSV__c`
- `PRM_InsurancePSV__c`
- `PRM_WorkHistoryPSV__c`
- `PRM_EducationPSV__c`
- `PRM_DEAPSV__c`
- `PRM_CDSPSV__c`
- `PRM_DisclosurePSV__c`
- `PRM_BoardCertificationPSV__c`
- `PRM_FSMBPSV__c`
- `PRM_MedicareOptOutPSV__c`
- `PRM_SAMPSV__c`
- `PRM_NPDBPSV__c`
- `PRM_NPDBVerifiedOn__c`
- `PRM_CMSPreclusionPSV__c`

**Action:** Verify these fields exist and have appropriate field types (picklist or text).

---

## Summary of Findings

### Current State:
- ReCredQC radio buttons are **read-only**
- ReCredQC has **NO note fields** on individual steps
- ReCredQC **does not save** individual step responses to IndividualApplication
- Only a single, consolidated QC note is saved

### Desired State (Matching PSV):
- Radio buttons should be **editable**
- Each step should have a **Text Area note field** (required, 5000 char limit)
- All step responses should be **saved to IndividualApplication** fields
- Step notes should be **saved to ContentNote** (either compiled or individually)

### Effort Estimate:
- **Configuration Changes:** ~14 new Text Area elements + 14 radio button updates + 3 SetRecord action updates
- **Testing:** Comprehensive testing of all 14 verification steps
- **Timeline:** 2-3 sprints (depending on complexity and testing requirements)

---

## Next Steps

1. **Review this analysis** with the business team and confirm requirements
2. **Validate radio button options** for each step against business needs
3. **Create detailed design specifications** for each verification step
4. **Implement changes** in a sandbox environment
5. **Conduct thorough testing** (functional, integration, regression)
6. **Document changes** for end users
7. **Deploy to production** with appropriate change management

---

## Questions for Business Stakeholders

1. Should all 14 verification steps have editable radio buttons and notes, or only specific ones?
2. Should the note fields be **required** or **optional**?
3. Should notes be visible in a compiled format (single ContentNote) or individual notes per step?
4. Are the current radio button options sufficient, or do any need additional choices?
5. Should certain options trigger specific actions (e.g., "Provider Outreach Needed" → create follow-up task)?
6. Do we need conditional logic (e.g., hide certain steps based on prior selections)?
7. What is the priority order if we need to implement in phases?

---

**Document Version:** 1.0  
**Date:** 2026-04-08  
**Author:** Claude Code Analysis
