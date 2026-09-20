# Adverse Action Log: DataRaptor vs Batch Class Cross-Verification Report

## Executive Summary

This document cross-verifies the **PRMDRCreateOrgAdverseActionLog** DataRaptor (DR) and **PRM_CreateAdverseActionNpdbBatch** batch class that both create `PRM_AdverseActionLog__c` records for **Organization** type. It identifies field mapping gaps, mismatches, and fallout.

---

## 1. Context: Two Creation Paths

| Path | Component | Record Type | Use Case |
|------|-----------|-------------|----------|
| **Path A** | PRMDRCreateOrgAdverseActionLog (DataRaptor) | PRM_Organization | IPCreateAdverseActionLog – Ancillary form records creation |
| **Path B** | PRM_CreateAdverseActionNpdbBatch (Batch) | PRM_Organization | Ad-hoc NPDB flow – Practice location selection (PracLocStep.PracticeLocationBlock) |

Both create Organization-type adverse action logs but from different input structures.

---

## 2. DataRaptor (PRMDRCreateOrgAdverseActionLog) – Field Mappings

**Source:** `vlocity_export/DataRaptor/PRMDRCreateOrgAdverseActionLog/PRMDRCreateOrgAdverseActionLog_Items.json`

| Output Field (PRM_AdverseActionLog__c) | Input Source |
|--------------------------------------|-------------|
| RecordTypeId | AdverseActionRecordType |
| PRM_AdHoc__c | PRM_Adhoc__c |
| PRM_AffiliationCity__c | AffiliationAddress:PRM_City__c |
| PRM_AffiliationName__c | AffiliationAddress:PRM_CorporateHospitalAffiliationName__c |
| PRM_AffiliationState__c | AffiliationAddress:PRM_State__c |
| PRM_AffiliationStreetAddress2__c | AffiliationAddress:PRM_AddressLine2__c |
| PRM_AffiliationStreetAddress__c | AffiliationAddress:PRM_AddressLine1__c |
| PRM_AffiliationZip__c | AffiliationAddress:PRM_Zip__c |
| PRM_Birthdate__c | PersonBirthdate |
| PRM_CaseManager__c | CaseManagerId |
| PRM_IndividualNpiId__c | ProviderNPIId |
| PRM_IndividualNpi__c | ProviderNPI |
| PRM_Licensure__c | Licensure |
| PRM_MedicareNumber__c | Medicarelst\|1:IDValue |
| PRM_OrganizationName__c | AccountName or OrgName |
| PRM_OrganizationType__c | OrgType |
| PRM_OtherLicensure__c | OtherLicensure |
| PRM_OtherName__c | Account:PRM_DoingBusinessAsName__c |
| PRM_OtherOrgType__c | OtherOrgType (formula: IF OrgType==999) |
| PRM_PrimaryAddressId__c | PrimaryAddress:Id |
| PRM_PrimaryCity__c | PrimaryAddress:PRM_City__c |
| PRM_PrimaryCounty__c | PrimaryAddress:PRM_StateCounty__c |
| PRM_PrimaryState__c | PrimaryAddress:PRM_State__c |
| PRM_PrimaryStreetAddress2__c | PrimaryAddress:PRM_AddressLine2__c |
| PRM_PrimaryStreetAddress__c | PrimaryAddress:PRM_AddressLine1__c |
| PRM_PrimaryZip__c | PrimaryAddress:PRM_Zip__c |
| PRM_ProfessionalSchool__c | ProfessionalSchool |
| PRM_ProviderId__c | ProviderId |
| PRM_Status__c | DefaultValue: "Ready To Process" |
| PRM_TaxID__c | TaxIdlst\|1:IDValue |

---

## 3. Batch Class (PRM_CreateAdverseActionNpdbBatch) – Field Mappings

**Source:** `force-app/main/default/classes/PRM_CreateAdverseActionNpdbBatch.cls`

| Output Field (PRM_AdverseActionLog__c) | Input Source |
|--------------------------------------|-------------|
| RecordTypeId | practiceLocation.AaRecId |
| PRM_OrganizationName__c | practiceLocation.PracName |
| PRM_OtherName__c | practiceLocation.DbaName |
| PRM_OrganizationType__c | requestMap.OrgType |
| PRM_PrimaryAddressId__c | practiceLocation.PrimaryAddrId |
| PRM_PrimaryStreetAddress__c | practiceLocation.PracAddLine1 |
| PRM_PrimaryStreetAddress2__c | practiceLocation.PracAddLine2 |
| PRM_PrimaryCity__c | practiceLocation.PracCity |
| PRM_PrimaryState__c | practiceLocation.PracState |
| PRM_PrimaryZip__c | practiceLocation.PracZip |
| PRM_PrimaryCounty__c | practiceLocation.PracCounty |
| PRM_MedicareNumber__c | requestMap.MedId |
| PRM_TaxID__c | requestMap.TaxId |
| PRM_AffiliationName__c | practiceLocation.AffName |
| PRM_AffiliationStreetAddress__c | practiceLocation.AffAddLine1 |
| PRM_AffiliationStreetAddress2__c | practiceLocation.AffAddLine2 |
| PRM_AffiliationCity__c | practiceLocation.AffCity |
| PRM_AffiliationState__c | practiceLocation.AffState |
| PRM_AffiliationZip__c | practiceLocation.AffZip |
| PRM_CaseManager__c | requestMap.CaseManagerId |
| PRM_AdHoc__c | Hardcoded: true |
| PRM_HealthcareFacility__c | practiceLocation.Id |
| PRM_Licensure__c | From BusinessLicense (stampLicensureFields) |
| PRM_OtherLicensure__c | From BusinessLicense (stampLicensureFields) |

---

## 4. Fallout Analysis

### 4.1 Fields in DR but NOT in Batch

| Field | Impact |
|-------|--------|
| **PRM_Birthdate__c** | Not set in batch. Ad-hoc NPDB flow is Organization-centric; birthdate may not apply. If NPDB expects it for org records, it will be blank. |
| **PRM_IndividualNpiId__c** | Not set in batch. Individual NPI Id not passed in PracLocStep. |
| **PRM_IndividualNpi__c** | Not set in batch. Individual NPI not passed in PracLocStep. |
| **PRM_OtherOrgType__c** | Not set in batch. When OrgType=999, DR uses OtherOrgTypeName (first 40 chars). Batch does not handle this. |
| **PRM_ProfessionalSchool__c** | Not set in batch. Education data not in PracticeLocationBlock. |
| **PRM_ProviderId__c** | Not set in batch. Provider/Account Id not in PracticeLocationBlock. |
| **PRM_Status__c** | Not set in batch. DR defaults to "Ready To Process". Batch leaves it null (or org default). |

### 4.2 Fields in Batch but NOT in DR

| Field | Impact |
|-------|--------|
| **PRM_HealthcareFacility__c** | Batch sets this (practice location Id). DR does not map it. DR uses PrimaryAddress/Account context; batch explicitly links to HealthcareFacility. |

### 4.3 Field-Level Differences

| Field | DR | Batch | Notes |
|-------|----|-------|-------|
| **PRM_AdHoc__c** | From input (conditional) | Always `true` | Batch always marks as ad-hoc; DR can vary. |
| **PRM_Status__c** | Default "Ready To Process" | Not set | Batch may rely on org default; DR explicitly sets status. |
| **PRM_OrganizationName__c** | AccountName or OrgName (formula) | PracName | Different sources; both are org/practice names. |
| **PRM_OtherName__c** | Account:PRM_DoingBusinessAsName__c | DbaName | Same concept; different source paths. |
| **PRM_Licensure__c / PRM_OtherLicensure__c** | From Licensure/OtherLicensure input | From BusinessLicense query by facility | Batch derives from DB; DR from IP input. Logic differs but both populate licensure. |

### 4.4 County Field Mapping

| Component | Primary County Source |
|-----------|------------------------|
| DR | PrimaryAddress:PRM_StateCounty__c |
| Batch | PracCounty |

DR uses `PRM_StateCounty__c`; batch uses `PracCounty`. Both map to `PRM_PrimaryCounty__c` but from different structures.

---

## 5. Summary of Fallout

### High Priority

1. **PRM_Status__c** – Batch does not set status. If "Ready To Process" is required for NPDB processing, batch-created records may not progress.
2. **PRM_ProviderId__c** – Not set in batch. May affect linking to practitioner/account for reporting or downstream logic.
3. **PRM_OtherOrgType__c** – When OrgType=999, batch does not set OtherOrgType. NPDB may require this for "Other" org types.

### Medium Priority

4. **PRM_IndividualNpi__c / PRM_IndividualNpiId__c** – Not set in batch. May matter if org records need NPI context.
5. **PRM_Birthdate__c** – Not set in batch. May be optional for org records.
6. **PRM_ProfessionalSchool__c** – Not set in batch. Education not in ad-hoc flow.

### Low Priority

7. **PRM_HealthcareFacility__c** – Batch sets it; DR does not. Batch provides explicit facility linkage; DR relies on address/account context.

---

## 6. Recommendations

1. **Add PRM_Status__c** in batch: Set to `"Ready To Process"` to align with DR and NPDB expectations.
2. **Evaluate PRM_ProviderId__c**: If the ad-hoc flow has access to a provider/account Id (e.g., from Case Manager context), add it to the batch input and mapping.
3. **Handle OrgType=999**: If `OrgType` can be 999, add `PRM_OtherOrgType__c` mapping (e.g., from a new input field or formula).
4. **Confirm NPDB requirements**: Validate which fields NPDB actually requires for org adverse action logs and adjust batch mappings accordingly.
5. **Document flow differences**: DR is used for ancillary form creation; batch is for ad-hoc practice location selection. Some field gaps may be intentional due to different data availability.

---

## 7. Files Referenced

| File | Purpose |
|------|---------|
| `vlocity_export/DataRaptor/PRMDRCreateOrgAdverseActionLog/PRMDRCreateOrgAdverseActionLog_Items.json` | DR field mappings |
| `force-app/main/default/classes/PRM_CreateAdverseActionNpdbBatch.cls` | Batch class implementation |
| `force-app/main/default/lwc/pRMPracLocAncNpdb/pRMPracLocAncNpdb.js` | LWC that uses PracLocStep.PracticeLocationBlock |
| `vlocity_export/IntegrationProcedure/PRM_IPCreateAdverseActionLog/PRM_IPCreateAdverseActionLog_Element_DRCreateOrgAdverseActionLogForAncillary.json` | DR invocation in IP |

---

*Report generated from codebase analysis. Last verified: March 2025.*
