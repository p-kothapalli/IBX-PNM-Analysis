# BUILD SPEC: QC Edit Mode — PSV OmniScript Enhancement

## Document Information

| Field | Value |
|-------|-------|
| **Feature** | QC Edit Mode for PSV OmniScript |
| **Date** | 2026-05-13 |
| **Status** | Ready for Development |
| **Priority** | High |
| **Estimated Effort** | 41 Story Points (~205 hours) |

---

## 1. EXECUTIVE SUMMARY

### Problem Statement
QC reviewers currently cannot edit PSV source-of-truth fields during QC Review. When they find data errors, they must "Return to PSV" which adds cycle time and re-work. The QC team wants the same edit functionality that exists in the PSV guided flow.

### Solution
Introduce a `QC_EditMode` flag that, when enabled, removes the read-only restriction on PSV fields while retaining all QC verification fields and QC-specific routing. This allows QC reviewers to fix minor data issues directly without returning the case to PSV.

### Approach
- Add `QC_EditMode` boolean flag (passed as URL parameter or set via toggle)
- Modify read-only conditions: `Read Only IF CaseType = "QC Review" AND QC_EditMode != true`
- Keep QC verification radio buttons and notes fields visible
- Keep QC routing (Approved / Return to PSV / Needs More Info)
- Update IP to save source-of-truth fields when `QC_EditMode = true`

---

## 2. FLAG DEFINITION & PROPAGATION

### 2.1 Flag: `QC_EditMode`

| Property | Value |
|----------|-------|
| **Name** | `QC_EditMode` |
| **Type** | Boolean |
| **Default** | `false` |
| **Set By** | URL parameter on OmniScript launch OR toggle in Step 1 |
| **Scope** | Session-level (not persisted to Salesforce) |
| **Passed To** | Main OS → Sub-OmniScripts → Integration Procedure |

### 2.2 How the Flag Enters the OmniScript

**Option A: URL Parameter**
```
/apex/vlocity_ins__OmniScriptUniversalPage?OmniScriptType=PRM&OmniScriptSubType=PrimarySourceVerificationReview&OmniScriptLang=English&CaseId={!CaseId}&CaseType=QC Review&QC_EditMode=true
```

**Option B: Toggle in OmniScript Step 1 (Recommended)**
Add a Radio/Toggle element in the first step:
- Element Name: `QC_EditMode_Selector`
- Label: "Review Mode"
- Options: "Standard Review (Read-Only)" / "Edit Mode (Can Modify PSV Data)"
- Default: "Standard Review (Read-Only)"
- Visibility: `%CaseType% == "QC Review"`
- Maps to: `%QC_EditMode%` (true/false)

### 2.3 Flag Propagation to Sub-OmniScripts

Each Sub-OmniScript element must pass `QC_EditMode` as an input parameter:

| Sub-OmniScript Element | Input Parameter to Add |
|------------------------|----------------------|
| `PRM_PSVSubOsTxnyRole_English` | `QC_EditMode` = `%QC_EditMode%` |
| `PRM_PSVSubOsWSNPDB_English` | `QC_EditMode` = `%QC_EditMode%` |
| `PRM_PSVSubOsSummary_English` | `QC_EditMode` = `%QC_EditMode%` |

### 2.4 Flag Propagation to Integration Procedure

The IP call (DataRaptor Post Action or Remote Action) must include:
```json
{
  "CaseType": "%CaseType%",
  "QC_EditMode": "%QC_EditMode%",
  ...existing parameters
}
```

---

## 3. OMNISCRIPT CHANGES — MAIN OS

### Component: `PRM_PrimarySourceVerificationReview_English`
### Current Version: v50
### New Version: v51

### 3.1 Read-Only Formula Change (Global Pattern)

**Current Formula (on ~126 elements):**
```
%CaseType% == "QC Review"
```

**New Formula:**
```
%CaseType% == "QC Review" AND %QC_EditMode% != true
```

This single formula change applies to ALL elements listed below. Each element's "Read Only If True" property must be updated.

---

### 3.2 Section: Practitioner Information

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `PractitionerFirstName` | Text | IndividualApplication.FirstName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerLastName` | Text | IndividualApplication.LastName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerMiddleName` | Text | IndividualApplication.MiddleName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerSuffix` | Text | IndividualApplication.Suffix__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerNPI` | Text | IndividualApplication.PractitionerNPI__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerDOB` | Date | IndividualApplication.DateOfBirth__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerGender` | Select | IndividualApplication.Gender__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PractitionerSSN` | Text | IndividualApplication.SSN__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `TaxonomyCode` | Text | IndividualApplication.TaxonomyCode__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE — keep visible when CaseType = "QC Review"):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_PractitionerInfo_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_PractitionerInfo_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.3 Section: Group / Practice Information

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `GroupName` | Text | IndividualApplication.GroupName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `GroupNPI` | Text | IndividualApplication.GroupNPI__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `GroupTaxID` | Text | IndividualApplication.GroupTaxID__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PracticeName` | Text | IndividualApplication.PracticeName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PracticeType` | Select | IndividualApplication.PracticeType__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PracticeTIN` | Text | IndividualApplication.PracticeTIN__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_GroupPractice_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_GroupPractice_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.4 Section: Addresses

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `AddressLine1` | Text | PractitionerAddress.AddressLine1__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `AddressLine2` | Text | PractitionerAddress.AddressLine2__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `City` | Text | PractitionerAddress.City__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `State` | Select | PractitionerAddress.State__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ZipCode` | Text | PractitionerAddress.ZipCode__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `AddressType` | Select | PractitionerAddress.AddressType__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `IsPrimary` | Checkbox | PractitionerAddress.IsPrimary__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `Phone` | Text | PractitionerAddress.Phone__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `Fax` | Text | PractitionerAddress.Fax__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**Edit Block (Add/Remove Rows):**
| Element Name | Property | Current Condition | New Condition |
|---|---|---|---|
| `AddressEditBlock` | Allow Add Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |
| `AddressEditBlock` | Allow Remove Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_Address_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_Address_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.5 Section: Demographics

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `Ethnicity` | Select | IndividualApplication.Ethnicity__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `Race` | Multi-Select | IndividualApplication.Race__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PrimaryLanguage` | Select | IndividualApplication.PrimaryLanguage__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `SecondaryLanguage` | Select | IndividualApplication.SecondaryLanguage__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_Demographics_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_Demographics_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.6 Section: Languages

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `SpokenLanguages` | Multi-Select | IndividualApplication.SpokenLanguages__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WrittenLanguages` | Multi-Select | IndividualApplication.WrittenLanguages__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `InterpreterNeeded` | Checkbox | IndividualApplication.InterpreterNeeded__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_Languages_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_Languages_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.7 Section: Contact Information

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `ContactEmail` | Email | IndividualApplication.ContactEmail__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ContactPhone` | Phone | IndividualApplication.ContactPhone__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ContactFax` | Phone | IndividualApplication.ContactFax__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `EmergencyContactName` | Text | IndividualApplication.EmergencyContactName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `EmergencyContactPhone` | Phone | IndividualApplication.EmergencyContactPhone__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_Contact_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_Contact_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.8 Section: Board Certification

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `BoardCertification` | Select | IndividualApplication.BoardCertification__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `BoardCertSpecialty` | Select | IndividualApplication.BoardCertificationSpecialty__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `BoardCertExpDate` | Date | IndividualApplication.BoardCertificationExpDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `BoardCertIssueDate` | Date | IndividualApplication.BoardCertificationIssueDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `BoardName` | Text | IndividualApplication.BoardName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_BoardCert_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_BoardCert_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.9 Section: Contract / Malpractice Insurance

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `MalpracticeCarrier` | Text | IndividualApplication.MalpracticeInsuranceCarrier__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MalpracticePolicyNumber` | Text | IndividualApplication.MalpracticeInsurancePolicyNumber__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MalpracticeExpDate` | Date | IndividualApplication.MalpracticeInsuranceExpDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MalpracticeCoverageAmount` | Currency | IndividualApplication.MalpracticeInsuranceCoverageAmount__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MalpracticeAggregateCoverage` | Currency | IndividualApplication.MalpracticeAggregateCoverage__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC Verification Fields (NO CHANGE):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_Contract_Status` | `%CaseType% == "QC Review"` | No change |
| `QC_Contract_Notes` | `%CaseType% == "QC Review"` | No change |

---

### 3.10 Section: Sanctions / Exclusions

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `OIGExclusionCheck` | Select | IndividualApplication.OIGExclusionCheck__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `OIGExclusionDate` | Date | IndividualApplication.OIGExclusionDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `SAMExclusionCheck` | Select | IndividualApplication.SAMExclusionCheck__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `SAMExclusionDate` | Date | IndividualApplication.SAMExclusionDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MedicareOptOut` | Checkbox | IndividualApplication.MedicareOptOut__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `MedicaidSanction` | Checkbox | IndividualApplication.MedicaidSanction__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `CMSPreclusionCheck` | Select | IndividualApplication.CMSPreclusionListCheck__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `CMSPreclusionDate` | Date | IndividualApplication.CMSPreclusionListDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

---

### 3.11 Section: Education & Training

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `EducationVerified` | Checkbox | IndividualApplication.EducationVerified__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `EducationInstitution` | Text | IndividualApplication.EducationInstitution__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `EducationGradDate` | Date | IndividualApplication.EducationGraduationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `EducationDegree` | Select | IndividualApplication.EducationDegree__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ResidencyVerified` | Checkbox | IndividualApplication.ResidencyVerified__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ResidencyInstitution` | Text | IndividualApplication.ResidencyInstitution__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ResidencyCompletionDate` | Date | IndividualApplication.ResidencyCompletionDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ECFMGCertified` | Checkbox | IndividualApplication.ECFMGCertified__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `ECFMGCertDate` | Date | IndividualApplication.ECFMGCertificationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

---

## 4. SUB-OMNISCRIPT CHANGES

### 4.1 Sub-OmniScript: `PRM_PSVSubOsTxnyRole_English`
**Current Version:** v5 → **New Version:** v6

**Purpose:** License and Taxonomy/Role verification

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `LicenseNumber` | Text | PractitionerLicense.LicenseNumber__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `LicenseState` | Select | PractitionerLicense.LicenseState__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `LicenseType` | Select | PractitionerLicense.LicenseType__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `LicenseStatus` | Select | PractitionerLicense.LicenseStatus__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `LicenseIssueDate` | Date | PractitionerLicense.IssueDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `LicenseExpDate` | Date | PractitionerLicense.ExpirationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `DisciplinaryAction` | Select | PractitionerLicense.DisciplinaryAction__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `DisciplinaryDetails` | Text Area | PractitionerLicense.DisciplinaryActionDetails__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `DEANumber` | Text | IndividualApplication.DEANumber__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `DEAExpDate` | Date | IndividualApplication.DEAExpirationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `DEAState` | Select | IndividualApplication.DEAState__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `CDSNumber` | Text | IndividualApplication.CDSNumber__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `CDSExpDate` | Date | IndividualApplication.CDSExpirationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `CDSState` | Select | IndividualApplication.CDSState__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**Edit Block (Add/Remove License Rows):**
| Element Name | Property | Current Condition | New Condition |
|---|---|---|---|
| `LicenseEditBlock` | Allow Add Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |
| `LicenseEditBlock` | Allow Remove Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |

**Input Parameter Addition:**
```json
{
  "name": "QC_EditMode",
  "source": "%QC_EditMode%",
  "type": "Boolean"
}
```

---

### 4.2 Sub-OmniScript: `PRM_PSVSubOsWSNPDB_English`
**Current Version:** v6 → **New Version:** v7

**Purpose:** Work History and NPDB verification

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `WorkHistoryVerified` | Checkbox | IndividualApplication.WorkHistoryVerified__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryGapExplanation` | Text Area | IndividualApplication.WorkHistoryGapExplanation__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryEmployer` | Text | WorkHistory.EmployerName__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryStartDate` | Date | WorkHistory.StartDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryEndDate` | Date | WorkHistory.EndDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryPosition` | Text | WorkHistory.Position__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `WorkHistoryReasonLeaving` | Text | WorkHistory.ReasonForLeaving__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `NPDBVerificationDate` | Date | IndividualApplication.NPDBVerificationDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `NPDBQueryDate` | Date | IndividualApplication.NPDBQueryDate__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `NPDBAdverseAction` | Select | IndividualApplication.NPDBAdverseAction__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `NPDBAdverseDetails` | Text Area | IndividualApplication.NPDBAdverseDetails__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**Edit Block (Add/Remove Work History Rows):**
| Element Name | Property | Current Condition | New Condition |
|---|---|---|---|
| `WorkHistoryEditBlock` | Allow Add Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |
| `WorkHistoryEditBlock` | Allow Remove Row | `%CaseType% != "QC Review"` | `%CaseType% != "QC Review" OR %QC_EditMode% == true` |

**Input Parameter Addition:**
```json
{
  "name": "QC_EditMode",
  "source": "%QC_EditMode%",
  "type": "Boolean"
}
```

---

### 4.3 Sub-OmniScript: `PRM_PSVSubOsSummary_English`
**Current Version:** v6 → **New Version:** v7

**Purpose:** MDR Summary / Sign-off (also contains QC final step)

| Element Name | Element Type | Field Mapped To | Current Read-Only Condition | New Read-Only Condition |
|---|---|---|---|---|
| `MDRSummaryNotes` | Text Area | IndividualApplication.MDRSummaryNotes__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |
| `PSVCompletionNotes` | Text Area | IndividualApplication.PSVCompletionNotes__c | `%CaseType% == "QC Review"` | `%CaseType% == "QC Review" AND %QC_EditMode% != true` |

**QC-Specific Elements (NO CHANGE — these are QC's own fields):**
| Element Name | Visibility Condition | Change? |
|---|---|---|
| `QC_FinalDecision` | `%CaseType% == "QC Review"` | No change |
| `QC_FinalNotes` | `%CaseType% == "QC Review"` | No change |
| `QC_ReturnReason` | `%CaseType% == "QC Review" AND %QC_FinalDecision% == "Return to PSV"` | No change |

**Input Parameter Addition:**
```json
{
  "name": "QC_EditMode",
  "source": "%QC_EditMode%",
  "type": "Boolean"
}
```

---

## 5. INTEGRATION PROCEDURE CHANGES

### Component: `PRM_ReviewPSVCaseRecordsUpdate`
### Current Version: v12 → New Version: v13

### 5.1 New Input Parameter

| Parameter Name | Type | Required | Source |
|---|---|---|---|
| `QC_EditMode` | Boolean | No (defaults to `false`) | OmniScript payload |

### 5.2 Revised IP Element Flow

```
Element Order | Element Name                        | Type              | Condition
-------------------------------------------------------------------------------------------------------------------------------------
1            | SetValues_DefaultQCEditMode          | Set Values        | Always
2            | Cond_SaveSourceData                  | Conditional Block | %CaseType% == "PSV" OR %QC_EditMode_Resolved% == true
3            |   > DR_LoadIndividualAppPSV          | DataRaptor Load   | (inside conditional)
4            |   > DR_LoadPractitionerLicense       | DataRaptor Load   | (inside conditional)
5            |   > DR_LoadPractitionerAddress       | DataRaptor Load   | (inside conditional)
6            |   > DR_LoadWorkHistory               | DataRaptor Load   | (inside conditional)
7            |   > DR_LoadEducation                 | DataRaptor Load   | (inside conditional)
8            |   > DR_LoadBoardCertification        | DataRaptor Load   | (inside conditional)
9            | Cond_SaveQCVerification              | Conditional Block | %CaseType% == "QC Review"
10           |   > DR_LoadQCVerificationData        | DataRaptor Load   | (inside conditional)
11           | Cond_StatusRouting_PSV               | Conditional Block | %CaseType% == "PSV" AND %QC_EditMode_Resolved% != true
12           |   > SetValues_CaseStatusPSVComplete  | Set Values        | (inside conditional)
13           |   > DR_UpdateCaseStatus_PSV          | DataRaptor Load   | (inside conditional)
14           | Cond_StatusRouting_QC                 | Conditional Block | %CaseType% == "QC Review"
15           |   > SetValues_CaseStatusQCComplete   | Set Values        | (inside conditional)
16           |   > DR_UpdateCaseStatus_QC           | DataRaptor Load   | (inside conditional)
17           | ResponseAction_Success               | Response Action   | Always
```

---

### 5.3 Element Details

#### Element 1: `SetValues_DefaultQCEditMode`
| Property | Value |
|----------|-------|
| Type | Set Values |
| Order | 1 |
| Condition | None (always runs) |

**Values Set:**
| Name | Value |
|------|-------|
| `QC_EditMode_Resolved` | `IF(%QC_EditMode% == null, false, %QC_EditMode%)` |

---

#### Element 2: `Cond_SaveSourceData`
| Property | Value |
|----------|-------|
| Type | Conditional Block |
| Order | 2 |
| Condition Formula | `%CaseType% == "PSV" OR %QC_EditMode_Resolved% == true` |
| Group Name | `SaveSourceDataGroup` |

**Purpose:** This block fires for normal PSV saves AND for QC Edit Mode saves.

---

#### Element 3: `DR_LoadIndividualAppPSV`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 3 |
| DataRaptor Name | `PRMLoadIndividualApplicationPSV` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping (from OmniScript JSON to DR Input):**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `PractitionerInfo.PractitionerNPI` | `PractitionerNPI` | `IndividualApplication.PractitionerNPI__c` |
| `PractitionerInfo.TaxonomyCode` | `TaxonomyCode` | `IndividualApplication.TaxonomyCode__c` |
| `PractitionerInfo.PractitionerFirstName` | `FirstName` | `IndividualApplication.FirstName__c` |
| `PractitionerInfo.PractitionerLastName` | `LastName` | `IndividualApplication.LastName__c` |
| `PractitionerInfo.PractitionerMiddleName` | `MiddleName` | `IndividualApplication.MiddleName__c` |
| `PractitionerInfo.PractitionerSuffix` | `Suffix` | `IndividualApplication.Suffix__c` |
| `PractitionerInfo.PractitionerDOB` | `DateOfBirth` | `IndividualApplication.DateOfBirth__c` |
| `PractitionerInfo.PractitionerGender` | `Gender` | `IndividualApplication.Gender__c` |
| `GroupPractice.GroupName` | `GroupName` | `IndividualApplication.GroupName__c` |
| `GroupPractice.GroupNPI` | `GroupNPI` | `IndividualApplication.GroupNPI__c` |
| `GroupPractice.GroupTaxID` | `GroupTaxID` | `IndividualApplication.GroupTaxID__c` |
| `GroupPractice.PracticeName` | `PracticeName` | `IndividualApplication.PracticeName__c` |
| `GroupPractice.PracticeType` | `PracticeType` | `IndividualApplication.PracticeType__c` |
| `GroupPractice.PracticeTIN` | `PracticeTIN` | `IndividualApplication.PracticeTIN__c` |
| `BoardCert.BoardCertification` | `BoardCertification` | `IndividualApplication.BoardCertification__c` |
| `BoardCert.BoardCertSpecialty` | `BoardCertSpecialty` | `IndividualApplication.BoardCertificationSpecialty__c` |
| `BoardCert.BoardCertExpDate` | `BoardCertExpDate` | `IndividualApplication.BoardCertificationExpDate__c` |
| `BoardCert.BoardCertIssueDate` | `BoardCertIssueDate` | `IndividualApplication.BoardCertificationIssueDate__c` |
| `BoardCert.BoardName` | `BoardName` | `IndividualApplication.BoardName__c` |
| `License.DEANumber` | `DEANumber` | `IndividualApplication.DEANumber__c` |
| `License.DEAExpDate` | `DEAExpDate` | `IndividualApplication.DEAExpirationDate__c` |
| `License.DEAState` | `DEAState` | `IndividualApplication.DEAState__c` |
| `License.CDSNumber` | `CDSNumber` | `IndividualApplication.CDSNumber__c` |
| `License.CDSExpDate` | `CDSExpDate` | `IndividualApplication.CDSExpirationDate__c` |
| `License.CDSState` | `CDSState` | `IndividualApplication.CDSState__c` |
| `NPDB.NPDBVerificationDate` | `NPDBVerificationDate` | `IndividualApplication.NPDBVerificationDate__c` |
| `NPDB.NPDBQueryDate` | `NPDBQueryDate` | `IndividualApplication.NPDBQueryDate__c` |
| `NPDB.NPDBAdverseAction` | `NPDBAdverseAction` | `IndividualApplication.NPDBAdverseAction__c` |
| `WorkHistory.WorkHistoryVerified` | `WorkHistoryVerified` | `IndividualApplication.WorkHistoryVerified__c` |
| `WorkHistory.WorkHistoryGapExplanation` | `WorkHistoryGapExplanation` | `IndividualApplication.WorkHistoryGapExplanation__c` |
| `Sanctions.OIGExclusionCheck` | `OIGExclusionCheck` | `IndividualApplication.OIGExclusionCheck__c` |
| `Sanctions.OIGExclusionDate` | `OIGExclusionDate` | `IndividualApplication.OIGExclusionDate__c` |
| `Sanctions.SAMExclusionCheck` | `SAMExclusionCheck` | `IndividualApplication.SAMExclusionCheck__c` |
| `Sanctions.SAMExclusionDate` | `SAMExclusionDate` | `IndividualApplication.SAMExclusionDate__c` |
| `Sanctions.MedicareOptOut` | `MedicareOptOut` | `IndividualApplication.MedicareOptOut__c` |
| `Sanctions.MedicaidSanction` | `MedicaidSanction` | `IndividualApplication.MedicaidSanction__c` |
| `Sanctions.CMSPreclusionCheck` | `CMSPreclusionCheck` | `IndividualApplication.CMSPreclusionListCheck__c` |
| `Sanctions.CMSPreclusionDate` | `CMSPreclusionDate` | `IndividualApplication.CMSPreclusionListDate__c` |
| `Education.EducationVerified` | `EducationVerified` | `IndividualApplication.EducationVerified__c` |
| `Education.EducationInstitution` | `EducationInstitution` | `IndividualApplication.EducationInstitution__c` |
| `Education.EducationGradDate` | `EducationGradDate` | `IndividualApplication.EducationGraduationDate__c` |
| `Education.ResidencyVerified` | `ResidencyVerified` | `IndividualApplication.ResidencyVerified__c` |
| `Education.ResidencyInstitution` | `ResidencyInstitution` | `IndividualApplication.ResidencyInstitution__c` |
| `Education.ResidencyCompletionDate` | `ResidencyCompletionDate` | `IndividualApplication.ResidencyCompletionDate__c` |
| `Education.ECFMGCertified` | `ECFMGCertified` | `IndividualApplication.ECFMGCertified__c` |
| `Education.ECFMGCertDate` | `ECFMGCertDate` | `IndividualApplication.ECFMGCertificationDate__c` |
| `Contract.MalpracticeCarrier` | `MalpracticeCarrier` | `IndividualApplication.MalpracticeInsuranceCarrier__c` |
| `Contract.MalpracticePolicyNumber` | `MalpracticePolicyNumber` | `IndividualApplication.MalpracticeInsurancePolicyNumber__c` |
| `Contract.MalpracticeExpDate` | `MalpracticeExpDate` | `IndividualApplication.MalpracticeInsuranceExpDate__c` |
| `Contract.MalpracticeCoverageAmount` | `MalpracticeCoverageAmount` | `IndividualApplication.MalpracticeInsuranceCoverageAmount__c` |
| `Demographics.Ethnicity` | `Ethnicity` | `IndividualApplication.Ethnicity__c` |
| `Demographics.Race` | `Race` | `IndividualApplication.Race__c` |
| `Demographics.PrimaryLanguage` | `PrimaryLanguage` | `IndividualApplication.PrimaryLanguage__c` |
| `Demographics.SecondaryLanguage` | `SecondaryLanguage` | `IndividualApplication.SecondaryLanguage__c` |
| `Contact.ContactEmail` | `ContactEmail` | `IndividualApplication.ContactEmail__c` |
| `Contact.ContactPhone` | `ContactPhone` | `IndividualApplication.ContactPhone__c` |
| `Contact.ContactFax` | `ContactFax` | `IndividualApplication.ContactFax__c` |

**Record Identifier:** `IndividualApplicationId` (passed from OmniScript)

---

#### Element 4: `DR_LoadPractitionerLicense`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 4 |
| DataRaptor Name | `PRMLoadPractitionerLicense` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping (multi-row — Edit Block data):**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `Licenses[n].LicenseId` | `Id` | `PractitionerLicense__c.Id` (update key) |
| `Licenses[n].LicenseNumber` | `LicenseNumber` | `PractitionerLicense__c.LicenseNumber__c` |
| `Licenses[n].LicenseState` | `LicenseState` | `PractitionerLicense__c.LicenseState__c` |
| `Licenses[n].LicenseType` | `LicenseType` | `PractitionerLicense__c.LicenseType__c` |
| `Licenses[n].LicenseStatus` | `LicenseStatus` | `PractitionerLicense__c.LicenseStatus__c` |
| `Licenses[n].LicenseIssueDate` | `IssueDate` | `PractitionerLicense__c.IssueDate__c` |
| `Licenses[n].LicenseExpDate` | `ExpirationDate` | `PractitionerLicense__c.ExpirationDate__c` |
| `Licenses[n].DisciplinaryAction` | `DisciplinaryAction` | `PractitionerLicense__c.DisciplinaryAction__c` |
| `Licenses[n].DisciplinaryDetails` | `DisciplinaryDetails` | `PractitionerLicense__c.DisciplinaryActionDetails__c` |

**Note:** Uses Upsert. If `LicenseId` is present, updates; if new row added by QC, inserts.

---

#### Element 5: `DR_LoadPractitionerAddress`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 5 |
| DataRaptor Name | `PRMLoadPractitionerAddress` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping (multi-row):**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `Addresses[n].AddressId` | `Id` | `PractitionerAddress__c.Id` (update key) |
| `Addresses[n].AddressLine1` | `AddressLine1` | `PractitionerAddress__c.AddressLine1__c` |
| `Addresses[n].AddressLine2` | `AddressLine2` | `PractitionerAddress__c.AddressLine2__c` |
| `Addresses[n].City` | `City` | `PractitionerAddress__c.City__c` |
| `Addresses[n].State` | `State` | `PractitionerAddress__c.State__c` |
| `Addresses[n].ZipCode` | `ZipCode` | `PractitionerAddress__c.ZipCode__c` |
| `Addresses[n].AddressType` | `AddressType` | `PractitionerAddress__c.AddressType__c` |
| `Addresses[n].IsPrimary` | `IsPrimary` | `PractitionerAddress__c.IsPrimary__c` |
| `Addresses[n].Phone` | `Phone` | `PractitionerAddress__c.Phone__c` |
| `Addresses[n].Fax` | `Fax` | `PractitionerAddress__c.Fax__c` |

---

#### Element 6: `DR_LoadWorkHistory`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 6 |
| DataRaptor Name | `PRMLoadWorkHistory` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping (multi-row):**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `WorkHistory[n].WorkHistoryId` | `Id` | `WorkHistory__c.Id` (update key) |
| `WorkHistory[n].Employer` | `EmployerName` | `WorkHistory__c.EmployerName__c` |
| `WorkHistory[n].StartDate` | `StartDate` | `WorkHistory__c.StartDate__c` |
| `WorkHistory[n].EndDate` | `EndDate` | `WorkHistory__c.EndDate__c` |
| `WorkHistory[n].Position` | `Position` | `WorkHistory__c.Position__c` |
| `WorkHistory[n].ReasonLeaving` | `ReasonForLeaving` | `WorkHistory__c.ReasonForLeaving__c` |

---

#### Element 7: `DR_LoadEducation`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 7 |
| DataRaptor Name | `PRMLoadEducation` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping:**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `Education.EducationId` | `Id` | `Education__c.Id` (update key) |
| `Education.EducationInstitution` | `InstitutionName` | `Education__c.InstitutionName__c` |
| `Education.EducationGradDate` | `GraduationDate` | `Education__c.GraduationDate__c` |
| `Education.EducationDegree` | `Degree` | `Education__c.Degree__c` |
| `Education.ResidencyId` | `Id` | `Residency__c.Id` (update key) |
| `Education.ResidencyInstitution` | `InstitutionName` | `Residency__c.InstitutionName__c` |
| `Education.ResidencyCompletionDate` | `CompletionDate` | `Residency__c.CompletionDate__c` |

---

#### Element 8: `DR_LoadBoardCertification`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 8 |
| DataRaptor Name | `PRMLoadBoardCertification` |
| Condition | Inside `Cond_SaveSourceData` |

**Input Mapping:**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `BoardCert.BoardCertId` | `Id` | `BoardCertification__c.Id` (update key) |
| `BoardCert.BoardCertification` | `CertificationStatus` | `BoardCertification__c.CertificationStatus__c` |
| `BoardCert.BoardCertSpecialty` | `Specialty` | `BoardCertification__c.Specialty__c` |
| `BoardCert.BoardCertExpDate` | `ExpirationDate` | `BoardCertification__c.ExpirationDate__c` |
| `BoardCert.BoardCertIssueDate` | `IssueDate` | `BoardCertification__c.IssueDate__c` |
| `BoardCert.BoardName` | `BoardName` | `BoardCertification__c.BoardName__c` |

---

#### Element 9: `Cond_SaveQCVerification`
| Property | Value |
|----------|-------|
| Type | Conditional Block |
| Order | 9 |
| Condition Formula | `%CaseType% == "QC Review"` |
| Group Name | `SaveQCVerificationGroup` |

**Purpose:** Saves QC verification status and notes. Fires REGARDLESS of QC_EditMode (QC always records verification).

---

#### Element 10: `DR_LoadQCVerificationData`
| Property | Value |
|----------|-------|
| Type | DataRaptor Load |
| Order | 10 |
| DataRaptor Name | `PRMLoadQCVerificationData` |
| Condition | Inside `Cond_SaveQCVerification` |

**Input Mapping:**

| OS JSON Path | DR Input Field | Salesforce Field |
|---|---|---|
| `QC.PractitionerInfo_Status` | `QCPractInfoStatus` | `IndividualApplication.PSV_QC_PractitionerInfo_Status__c` |
| `QC.PractitionerInfo_Notes` | `QCPractInfoNotes` | `IndividualApplication.PSV_QC_PractitionerInfo_Notes__c` |
| `QC.GroupPractice_Status` | `QCGroupStatus` | `IndividualApplication.PSV_QC_GroupPractice_Status__c` |
| `QC.GroupPractice_Notes` | `QCGroupNotes` | `IndividualApplication.PSV_QC_GroupPractice_Notes__c` |
| `QC.Address_Status` | `QCAddressStatus` | `IndividualApplication.PSV_QC_Address_Status__c` |
| `QC.Address_Notes` | `QCAddressNotes` | `IndividualApplication.PSV_QC_Address_Notes__c` |
| `QC.Demographics_Status` | `QCDemoStatus` | `IndividualApplication.PSV_QC_Demographics_Status__c` |
| `QC.Demographics_Notes` | `QCDemoNotes` | `IndividualApplication.PSV_QC_Demographics_Notes__c` |
| `QC.Languages_Status` | `QCLangStatus` | `IndividualApplication.PSV_QC_Languages_Status__c` |
| `QC.Languages_Notes` | `QCLangNotes` | `IndividualApplication.PSV_QC_Languages_Notes__c` |
| `QC.Contact_Status` | `QCContactStatus` | `IndividualApplication.PSV_QC_Contact_Status__c` |
| `QC.Contact_Notes` | `QCContactNotes` | `IndividualApplication.PSV_QC_Contact_Notes__c` |
| `QC.BoardCert_Status` | `QCBoardStatus` | `IndividualApplication.PSV_QC_BoardCert_Status__c` |
| `QC.BoardCert_Notes` | `QCBoardNotes` | `IndividualApplication.PSV_QC_BoardCert_Notes__c` |
| `QC.Contract_Status` | `QCContractStatus` | `IndividualApplication.PSV_QC_Contract_Status__c` |
| `QC.Contract_Notes` | `QCContractNotes` | `IndividualApplication.PSV_QC_Contract_Notes__c` |

**Record Identifier:** `IndividualApplicationId`

---

#### Element 11: `Cond_StatusRouting_PSV`
| Property | Value |
|----------|-------|
| Type | Conditional Block |
| Order | 11 |
| Condition Formula | `%CaseType% == "PSV" AND %QC_EditMode_Resolved% != true` |
| Group Name | `PSVRoutingGroup` |

**Purpose:** Only fires for normal PSV completion (NOT QC Edit Mode).

---

#### Element 14: `Cond_StatusRouting_QC`
| Property | Value |
|----------|-------|
| Type | Conditional Block |
| Order | 14 |
| Condition Formula | `%CaseType% == "QC Review"` |
| Group Name | `QCRoutingGroup` |

**Purpose:** Fires for ALL QC scenarios (both read-only and edit mode). QC routing is always QC routing.

---

### 5.4 IP Logic Summary Diagram

```
START
  |
  v
[1] Set Defaults (QC_EditMode -> false if null)
  |
  v
[2] CaseType = "PSV" OR QC_EditMode = true?
  |-- YES -->
  |          [3] Save IndividualApplication source fields
  |          [4] Save PractitionerLicense records
  |          [5] Save PractitionerAddress records
  |          [6] Save WorkHistory records
  |          [7] Save Education records
  |          [8] Save BoardCertification records
  |
  v
[9] CaseType = "QC Review"?
  |-- YES -->
  |          [10] Save QC Verification Status/Notes (16 fields)
  |
  v
[11] CaseType = "PSV" AND QC_EditMode != true?
  |-- YES -->
  |          [12-13] Set Status -> "PSV Complete", Route to PDA/Committee
  |
  v
[14] CaseType = "QC Review"?
  |-- YES -->
  |          [15-16] Set Status -> "QC Complete", Route per QC Decision
  |
  v
[17] Return Success Response
  |
  v
END
```

---

## 6. DATARAPTOR EXTRACT CHANGES

### Component: `PRMTransQCDataNoCAQH`
### Current Version: v7 → New Version: v8

**Current State:** Only fetches QC verification status/notes fields for QC mode.
**Change:** Add ALL source-of-truth fields so QC Edit Mode can pre-populate editable fields.

### 6.1 Existing Fields (No Change)

| Extract Field | Salesforce Object | Salesforce Field | Purpose |
|---|---|---|---|
| `QCPractInfoStatus` | IndividualApplication | PSV_QC_PractitionerInfo_Status__c | QC status |
| `QCPractInfoNotes` | IndividualApplication | PSV_QC_PractitionerInfo_Notes__c | QC notes |
| `QCGroupStatus` | IndividualApplication | PSV_QC_GroupPractice_Status__c | QC status |
| `QCGroupNotes` | IndividualApplication | PSV_QC_GroupPractice_Notes__c | QC notes |
| `QCAddressStatus` | IndividualApplication | PSV_QC_Address_Status__c | QC status |
| `QCAddressNotes` | IndividualApplication | PSV_QC_Address_Notes__c | QC notes |
| `QCDemoStatus` | IndividualApplication | PSV_QC_Demographics_Status__c | QC status |
| `QCDemoNotes` | IndividualApplication | PSV_QC_Demographics_Notes__c | QC notes |
| `QCLangStatus` | IndividualApplication | PSV_QC_Languages_Status__c | QC status |
| `QCLangNotes` | IndividualApplication | PSV_QC_Languages_Notes__c | QC notes |
| `QCContactStatus` | IndividualApplication | PSV_QC_Contact_Status__c | QC status |
| `QCContactNotes` | IndividualApplication | PSV_QC_Contact_Notes__c | QC notes |
| `QCBoardStatus` | IndividualApplication | PSV_QC_BoardCert_Status__c | QC status |
| `QCBoardNotes` | IndividualApplication | PSV_QC_BoardCert_Notes__c | QC notes |
| `QCContractStatus` | IndividualApplication | PSV_QC_Contract_Status__c | QC status |
| `QCContractNotes` | IndividualApplication | PSV_QC_Contract_Notes__c | QC notes |

### 6.2 NEW Fields to Add (Source-of-Truth for QC Edit Mode)

#### IndividualApplication Fields (55 new field mappings)

| Extract Field | Salesforce Field | Output JSON Path |
|---|---|---|
| `PractitionerNPI` | PractitionerNPI__c | `PractitionerInfo.PractitionerNPI` |
| `TaxonomyCode` | TaxonomyCode__c | `PractitionerInfo.TaxonomyCode` |
| `FirstName` | FirstName__c | `PractitionerInfo.PractitionerFirstName` |
| `LastName` | LastName__c | `PractitionerInfo.PractitionerLastName` |
| `MiddleName` | MiddleName__c | `PractitionerInfo.PractitionerMiddleName` |
| `Suffix` | Suffix__c | `PractitionerInfo.PractitionerSuffix` |
| `DateOfBirth` | DateOfBirth__c | `PractitionerInfo.PractitionerDOB` |
| `Gender` | Gender__c | `PractitionerInfo.PractitionerGender` |
| `SSN` | SSN__c | `PractitionerInfo.PractitionerSSN` |
| `GroupName` | GroupName__c | `GroupPractice.GroupName` |
| `GroupNPI` | GroupNPI__c | `GroupPractice.GroupNPI` |
| `GroupTaxID` | GroupTaxID__c | `GroupPractice.GroupTaxID` |
| `PracticeName` | PracticeName__c | `GroupPractice.PracticeName` |
| `PracticeType` | PracticeType__c | `GroupPractice.PracticeType` |
| `PracticeTIN` | PracticeTIN__c | `GroupPractice.PracticeTIN` |
| `BoardCertification` | BoardCertification__c | `BoardCert.BoardCertification` |
| `BoardCertSpecialty` | BoardCertificationSpecialty__c | `BoardCert.BoardCertSpecialty` |
| `BoardCertExpDate` | BoardCertificationExpDate__c | `BoardCert.BoardCertExpDate` |
| `BoardCertIssueDate` | BoardCertificationIssueDate__c | `BoardCert.BoardCertIssueDate` |
| `BoardName` | BoardName__c | `BoardCert.BoardName` |
| `DEANumber` | DEANumber__c | `License.DEANumber` |
| `DEAExpDate` | DEAExpirationDate__c | `License.DEAExpDate` |
| `DEAState` | DEAState__c | `License.DEAState` |
| `CDSNumber` | CDSNumber__c | `License.CDSNumber` |
| `CDSExpDate` | CDSExpirationDate__c | `License.CDSExpDate` |
| `CDSState` | CDSState__c | `License.CDSState` |
| `NPDBVerificationDate` | NPDBVerificationDate__c | `NPDB.NPDBVerificationDate` |
| `NPDBQueryDate` | NPDBQueryDate__c | `NPDB.NPDBQueryDate` |
| `NPDBAdverseAction` | NPDBAdverseAction__c | `NPDB.NPDBAdverseAction` |
| `WorkHistoryVerified` | WorkHistoryVerified__c | `WorkHistory.WorkHistoryVerified` |
| `WorkHistoryGapExplanation` | WorkHistoryGapExplanation__c | `WorkHistory.WorkHistoryGapExplanation` |
| `OIGExclusionCheck` | OIGExclusionCheck__c | `Sanctions.OIGExclusionCheck` |
| `OIGExclusionDate` | OIGExclusionDate__c | `Sanctions.OIGExclusionDate` |
| `SAMExclusionCheck` | SAMExclusionCheck__c | `Sanctions.SAMExclusionCheck` |
| `SAMExclusionDate` | SAMExclusionDate__c | `Sanctions.SAMExclusionDate` |
| `MedicareOptOut` | MedicareOptOut__c | `Sanctions.MedicareOptOut` |
| `MedicaidSanction` | MedicaidSanction__c | `Sanctions.MedicaidSanction` |
| `CMSPreclusionCheck` | CMSPreclusionListCheck__c | `Sanctions.CMSPreclusionCheck` |
| `CMSPreclusionDate` | CMSPreclusionListDate__c | `Sanctions.CMSPreclusionDate` |
| `EducationVerified` | EducationVerified__c | `Education.EducationVerified` |
| `EducationInstitution` | EducationInstitution__c | `Education.EducationInstitution` |
| `EducationGradDate` | EducationGraduationDate__c | `Education.EducationGradDate` |
| `ResidencyVerified` | ResidencyVerified__c | `Education.ResidencyVerified` |
| `ResidencyInstitution` | ResidencyInstitution__c | `Education.ResidencyInstitution` |
| `ResidencyCompletionDate` | ResidencyCompletionDate__c | `Education.ResidencyCompletionDate` |
| `ECFMGCertified` | ECFMGCertified__c | `Education.ECFMGCertified` |
| `ECFMGCertDate` | ECFMGCertificationDate__c | `Education.ECFMGCertDate` |
| `MalpracticeCarrier` | MalpracticeInsuranceCarrier__c | `Contract.MalpracticeCarrier` |
| `MalpracticePolicyNumber` | MalpracticeInsurancePolicyNumber__c | `Contract.MalpracticePolicyNumber` |
| `MalpracticeExpDate` | MalpracticeInsuranceExpDate__c | `Contract.MalpracticeExpDate` |
| `MalpracticeCoverageAmount` | MalpracticeInsuranceCoverageAmount__c | `Contract.MalpracticeCoverageAmount` |
| `Ethnicity` | Ethnicity__c | `Demographics.Ethnicity` |
| `Race` | Race__c | `Demographics.Race` |
| `PrimaryLanguage` | PrimaryLanguage__c | `Demographics.PrimaryLanguage` |
| `SecondaryLanguage` | SecondaryLanguage__c | `Demographics.SecondaryLanguage` |
| `SpokenLanguages` | SpokenLanguages__c | `Languages.SpokenLanguages` |
| `WrittenLanguages` | WrittenLanguages__c | `Languages.WrittenLanguages` |
| `InterpreterNeeded` | InterpreterNeeded__c | `Languages.InterpreterNeeded` |
| `ContactEmail` | ContactEmail__c | `Contact.ContactEmail` |
| `ContactPhone` | ContactPhone__c | `Contact.ContactPhone` |
| `ContactFax` | ContactFax__c | `Contact.ContactFax` |
| `EmergencyContactName` | EmergencyContactName__c | `Contact.EmergencyContactName` |
| `EmergencyContactPhone` | EmergencyContactPhone__c | `Contact.EmergencyContactPhone` |

#### PractitionerAddress Fields (Child Relationship Query)

| Extract Field | Salesforce Field | Output JSON Path |
|---|---|---|
| `AddressId` | Id | `Addresses[n].AddressId` |
| `AddressLine1` | AddressLine1__c | `Addresses[n].AddressLine1` |
| `AddressLine2` | AddressLine2__c | `Addresses[n].AddressLine2` |
| `City` | City__c | `Addresses[n].City` |
| `State` | State__c | `Addresses[n].State` |
| `ZipCode` | ZipCode__c | `Addresses[n].ZipCode` |
| `AddressType` | AddressType__c | `Addresses[n].AddressType` |
| `IsPrimary` | IsPrimary__c | `Addresses[n].IsPrimary` |
| `Phone` | Phone__c | `Addresses[n].Phone` |
| `Fax` | Fax__c | `Addresses[n].Fax` |

#### PractitionerLicense Fields (Child Relationship Query)

| Extract Field | Salesforce Field | Output JSON Path |
|---|---|---|
| `LicenseId` | Id | `Licenses[n].LicenseId` |
| `LicenseNumber` | LicenseNumber__c | `Licenses[n].LicenseNumber` |
| `LicenseState` | LicenseState__c | `Licenses[n].LicenseState` |
| `LicenseType` | LicenseType__c | `Licenses[n].LicenseType` |
| `LicenseStatus` | LicenseStatus__c | `Licenses[n].LicenseStatus` |
| `IssueDate` | IssueDate__c | `Licenses[n].LicenseIssueDate` |
| `ExpirationDate` | ExpirationDate__c | `Licenses[n].LicenseExpDate` |
| `DisciplinaryAction` | DisciplinaryAction__c | `Licenses[n].DisciplinaryAction` |
| `DisciplinaryDetails` | DisciplinaryActionDetails__c | `Licenses[n].DisciplinaryDetails` |

#### WorkHistory Fields (Child Relationship Query)

| Extract Field | Salesforce Field | Output JSON Path |
|---|---|---|
| `WorkHistoryId` | Id | `WorkHistory[n].WorkHistoryId` |
| `EmployerName` | EmployerName__c | `WorkHistory[n].Employer` |
| `StartDate` | StartDate__c | `WorkHistory[n].StartDate` |
| `EndDate` | EndDate__c | `WorkHistory[n].EndDate` |
| `Position` | Position__c | `WorkHistory[n].Position` |
| `ReasonForLeaving` | ReasonForLeaving__c | `WorkHistory[n].ReasonLeaving` |

---

## 7. DATARAPTOR LOAD VERIFICATION

### 7.1 Existing DataRaptor Loads (Verify — No New DRs Needed)

| DataRaptor Load Name | Object | Action | Verified? |
|---|---|---|---|
| `PRMLoadIndividualApplicationPSV` | IndividualApplication | Update | [ ] |
| `PRMLoadPractitionerLicense` | PractitionerLicense__c | Upsert | [ ] |
| `PRMLoadPractitionerAddress` | PractitionerAddress__c | Upsert | [ ] |
| `PRMLoadWorkHistory` | WorkHistory__c | Upsert | [ ] |
| `PRMLoadEducation` | Education__c | Update | [ ] |
| `PRMLoadBoardCertification` | BoardCertification__c | Update | [ ] |
| `PRMLoadQCVerificationData` | IndividualApplication | Update | [ ] |

### 7.2 Key Point: No New DataRaptor Loads Needed

The existing PSV DataRaptor Loads can be **reused** by the QC Edit Mode branch in the IP. The IP simply calls the same DR Loads from a different conditional block. No duplication needed.

---

## 8. TESTING SCENARIOS

### 8.1 Scenario Matrix

| # | Scenario | CaseType | QC_EditMode | Fields | Save | Status | Routing |
|---|---|---|---|---|---|---|---|
| TS-001 | Normal PSV | PSV | N/A | Editable | Source fields | PSV Complete | PDA/Committee |
| TS-002 | QC Read-Only | QC Review | false | Read-Only | QC notes only | QC Complete | Per QC decision |
| TS-003 | QC Edit Mode | QC Review | true | Editable | Source + QC notes | QC Complete | Per QC decision |
| TS-004 | QC Edit Approved | QC Review | true | Editable | Both saved | QC Complete | Approved |
| TS-005 | QC Edit Return | QC Review | true | Editable | Both saved | QC Complete | Return to PSV |
| TS-006 | QC Edit Info | QC Review | true | Editable | Both saved | QC Complete | Needs More Info |
| TS-007 | QC Add License | QC Review | true | Add Row visible | New license | QC Complete | Per decision |
| TS-008 | QC Add Address | QC Review | true | Add Row visible | New address | QC Complete | Per decision |
| TS-009 | QC No Changes | QC Review | true | Editable untouched | QC notes only | QC Complete | Per decision |
| TS-010 | PSV Regression | PSV | false | Editable | Source fields | PSV Complete | PDA/Committee |
| TS-011 | Null EditMode | QC Review | null | Read-Only | QC notes only | QC Complete | Per decision |
| TS-012 | Sub-OS License | QC Review | true | Editable | License updated | - | - |
| TS-013 | Sub-OS WorkHx | QC Review | true | Editable | WorkHx updated | - | - |
| TS-014 | PSV Routing OK | PSV | N/A | - | - | PSV Complete | NOT QC |
| TS-015 | QC Routing OK | QC Review | true | - | - | QC Complete | NOT PSV |

---

## 9. ROLLBACK PLAN

### Quick Rollback (< 10 minutes)

1. Deactivate OmniScript v51 → Reactivate v50
2. Deactivate Sub-OS new versions → Reactivate previous versions
3. Reactivate DataRaptor Extract previous version
4. Reactivate IP previous version
5. Smoke test PSV mode + QC read-only mode

### Partial Rollback (Disable Edit Mode Only)

If PSV mode works fine but QC Edit Mode has issues:
1. Edit OmniScript v51 → Hide the `QC_EditMode_Selector` element (set Visibility = `false`)
2. This defaults `QC_EditMode` to `false/null`
3. All QC users get read-only mode (existing behavior)
4. No IP/DR changes needed (conditions safely handle `QC_EditMode = false`)

---

## 10. CHANGE SUMMARY CHECKLIST

| # | Component | Action | New Version | Done? |
|---|---|---|---|---|
| 1 | `PRM_PrimarySourceVerificationReview_English` | Update read-only conditions on ~70+ elements | v51 | [ ] |
| 2 | `PRM_PrimarySourceVerificationReview_English` | Add `QC_EditMode_Selector` toggle element | v51 | [ ] |
| 3 | `PRM_PrimarySourceVerificationReview_English` | Update Edit Block conditions (Add/Remove rows) | v51 | [ ] |
| 4 | `PRM_PrimarySourceVerificationReview_English` | Pass `QC_EditMode` to all 3 Sub-OmniScripts | v51 | [ ] |
| 5 | `PRM_PSVSubOsTxnyRole_English` | Add input param + update read-only conditions | v6 | [ ] |
| 6 | `PRM_PSVSubOsWSNPDB_English` | Add input param + update read-only conditions | v7 | [ ] |
| 7 | `PRM_PSVSubOsSummary_English` | Add input param + update read-only conditions | v7 | [ ] |
| 8 | `PRMTransQCDataNoCAQH` (DR Extract) | Add ~55 source-of-truth field mappings | v8 | [ ] |
| 9 | `PRM_ReviewPSVCaseRecordsUpdate` (IP) | Add `QC_EditMode` input param | v13 | [ ] |
| 10 | `PRM_ReviewPSVCaseRecordsUpdate` (IP) | Add `SetValues_DefaultQCEditMode` element | v13 | [ ] |
| 11 | `PRM_ReviewPSVCaseRecordsUpdate` (IP) | Modify Conditional Block for source data save | v13 | [ ] |
| 12 | `PRM_ReviewPSVCaseRecordsUpdate` (IP) | Split Status/Routing into mutually exclusive blocks | v13 | [ ] |
| 13 | Verify existing DR Loads | Confirm field mappings correct | - | [ ] |
| 14 | Permission Set (optional) | Create `PSV_QC_Edit_Mode_Access` | - | [ ] |
| 15 | Regression Testing | PSV mode unaffected | - | [ ] |
| 16 | Integration Testing | QC Edit Mode full flow | - | [ ] |

---

## 11. FORMULA QUICK REFERENCE

| Purpose | Formula | Used In |
|---------|---------|---------|
| Make field read-only in QC (unless edit mode) | `%CaseType% == "QC Review" AND %QC_EditMode% != true` | All source-of-truth field elements |
| Allow Add/Remove rows | `%CaseType% != "QC Review" OR %QC_EditMode% == true` | Edit Block elements |
| Show QC verification fields | `%CaseType% == "QC Review"` | QC radio + notes elements (UNCHANGED) |
| Show QC Mode Selector | `%CaseType% == "QC Review"` | QC_EditMode_Selector element only |
| IP: Save source data | `%CaseType% == "PSV" OR %QC_EditMode_Resolved% == true` | IP Conditional Block |
| IP: Save QC verification | `%CaseType% == "QC Review"` | IP Conditional Block |
| IP: PSV routing | `%CaseType% == "PSV" AND %QC_EditMode_Resolved% != true` | IP Conditional Block |
| IP: QC routing | `%CaseType% == "QC Review"` | IP Conditional Block |

---

## 12. EFFORT ESTIMATION

| Task Category | Story Points | Hours |
|---|---|---|
| OmniScript Main OS changes (186 elements) | 8 | 40 |
| Sub-OmniScript changes (3 sub-OS) | 5 | 25 |
| DataRaptor Extract changes | 3 | 15 |
| DataRaptor Load verification | 2 | 10 |
| Integration Procedure changes | 8 | 40 |
| Unit testing | 3 | 15 |
| Integration testing | 5 | 25 |
| UAT support | 2 | 10 |
| Documentation | 2 | 10 |
| Training | 2 | 10 |
| Deployment | 1 | 5 |
| **TOTAL** | **41** | **205 hours** |

**Timeline:** 4-5 sprints (2-week sprints)
**Team:** 3 Developers + 1 QA + 1 BA

---

*End of Build Spec*
