# UPHS Mass Load: Practitioner-Location Linking Solutions

**Date:** April 13, 2026 (Updated: Deep-dive analysis vs PDM OmniScript)  
**Status:** Solution Design — Field-Level Analysis Complete  
**Business Requirement:** Link practitioners to respective locations via mass load  
**Excel Source:** `/Users/pkothapalli/Downloads/UPHS.xlsx`  
**Data Volume:** 107 practitioner records (107 rows + header)  
**Reference Flow:** `PRM_PDMManualUpdate_English` → "Practice Location: Add/Remove Practitioner → Add Practitioner"


---

## 📊 Excel File Analysis

### **File Structure**

| Attribute | Value |
|-----------|-------|
| **Sheet Name** | "UPHS Pg 1" |
| **Total Rows** | 108 (1 header + 107 data rows) |
| **Total Columns** | 133 |
| **Key Linking Fields** | Provider NPI (Col 8), Group NPI (Col 31), TaxID/TIN (Col 28), Taxonomy (Cols 9-10), Address (Cols 33-37) |

### **Complete Column Mapping: Excel → Salesforce**

> This table maps every relevant column from the UPHS Excel file to the exact Salesforce field used by the PDM OmniScript "Add Practitioner" flow.

| Excel Col | Header | Maps To (Salesforce Object.Field) | OmniScript Element | Notes |
|-----------|--------|-----------------------------------|--------------------|-------|
| 0 | CSR | — | — | Internal reference only |
| 1 | **Group BSPA** | `HealthcarePractitionerFacility.PRM_BSPA__c` (Group) | `addFacilityBSPA` | BSPA at group level |
| 2 | **Provider BSPA** | `HealthcarePractitionerFacility.PRM_BSPA__c` (Practitioner override) | `addFacilityBSPA` | Practitioner-level BSPA — use if present |
| 3 | Comments | `HealthcarePractitionerFacility` internal note | — | Not submitted to SF; useful in error log |
| 4 | **Last Name** | `Contact.LastName` / `HealthcareProvider.Name` | `LastnameAdd` | Lookup practitioner — also `Practitioner:LastName` in DR |
| 5 | **First Name** | `Contact.FirstName` / `HealthcareProvider.Name` | `FirstnameAdd` | Lookup practitioner — also `Practitioner:FirstName` in DR |
| 6 | **Middle Name** | `Contact.MiddleName` | `MiddlenameAdd` | Optional, used in dup check |
| 7 | Degree | `Contact.Suffix` / credential | — | Informational; used in display name |
| 8 | **Provider NPI** ⭐ | `HealthcareProviderNpi.Name` / `HealthcareProvider.NPI__c` | `NPIAdd` | **PRIMARY LOOKUP KEY** — used as `Practitioner:NPI` |
| 9 | **Taxonomy 1** | `HealthcareProviderTaxonomy.TaxonomyCode__c` / `HealthcareFacilityNetwork` | `addFacilityTaxonomy` | Care taxonomy — maps to `Practitioner:Specialty` |
| 10 | **Taxonomy 2** | `HealthcareProviderTaxonomy.TaxonomyCode__c` (secondary) | `addFacilityTaxonomy` (2nd pass) | Secondary taxonomy row |
| 11 | DOB | `Contact.Birthdate` | — | Not in Add Practitioner flow |
| 12 | Gender | `Contact.Gender__c` | — | Not in Add Practitioner flow |
| 15 | Affiliations | Multiple `HealthcareFacility` look-ups | — | Hospital affiliation codes (PPMC, HUP) |
| 25 | **Specialist or PCP** | `HealthcareFacilityNetwork.PRM_Role__c` | `addFacilityRole` | Values: `"PCP"` or `"Specialist"` |
| 26 | Legal Business Name | `Account.Name` (Group/Facility) | Facility search | Used to find `HealthcareFacility` by group account |
| 28 | **TIN / Tax ID** ⭐ | `Account.PRM_TaxId__c` on HealthcareFacility account | Facility lookup | **Secondary facility lookup key** |
| 29 | **Specialty** | `HealthcareProviderTaxonomy.SpecialtyCode__c` / `HealthcareFacilityNetwork.SpecialtyId` | `SpecialtyNameAddPract` | Specialty name — maps to `Practitioner:Specialty` |
| 30 | Group Number | `Account.PRM_GroupNumber__c` | — | Informational |
| 31 | **Group NPI** ⭐ | `HealthcareFacility.PRM_NPI__c` / `HealthcareProviderNpi` on facility account | Facility lookup | **Primary facility lookup key** |
| 32 | Group Name | `Account.Name` (Group) | Facility search fallback | Fallback if Group NPI not found |
| 33 | **Address Line 1** | `Location.Street` / `Address.Street` | Facility address match | Verify matched facility address |
| 34 | **Address Line 2** | `Location.Street` (continuation) | — | Suite/unit number |
| 35 | **City** | `Location.City` | — | Confirm facility city |
| 36 | **State** | `Location.State` | — | Confirm facility state |
| 37 | **Zip** | `Location.PostalCode` | — | Confirm zip match |
| 38 | County | `Location.County__c` | — | Informational |
| 39 | **Phone** | `HealthcareFacility.Phone` / `Location.Phone` | — | Location phone — verify match |
| 40 | Fax | `HealthcareFacility.Fax` | — | Informational |
| 41 | Handicap | `HealthcareFacility.PRM_Accessible__c` | — | Facility-level flag |
| 42 | Print Suppress | `HealthcareFacility.PRM_PrintSuppress__c` | — | Directory suppress flag |
| 43-46 | Billing Address | `Address` (Billing type) | — | Billing address block |
| 89 | ORG ID | Internal reference | — | Penn Medicine internal ID |
| 90 | Plan Code | `HealthcareFacilityNetwork.PRM_Network__c` plan | — | Network plan association |
| 91 | Provider ID | `HealthcareProvider.PRM_ProviderId__c` | — | Penn Medicine internal provider ID |
| 93 | Provider Number or PAR | `HealthcarePractitionerFacility.PRM_PAR__c` | — | PAR (Participating) status |

### **Data Observations**

✅ **Strengths:**
- Provider NPI present (100% of rows) → direct `HealthcareProvider` lookup
- Group NPI present (Col 31) → direct `HealthcareFacility` account lookup (more reliable than name LIKE search)
- TIN/Tax ID (Col 28) → secondary facility lookup
- Taxonomy 1 & 2 (Cols 9-10) → creates `HealthcareProviderTaxonomy` records
- PCP/Specialist (Col 25) → sets `Role` on `HealthcareFacilityNetwork`
- Specialty (Col 29) → mapped to `SpecialtyNameAddPract` in OmniScript
- BSPA (Cols 1-2) → sets `PRM_BSPA__c` on HCPF
- Full address in Cols 33-37 → used to **verify** correct facility was matched

⚠️ **Challenges:**
- Some rows have multiple affiliations (3-5 groups per practitioner) — each row becomes one HCPF record per group NPI
- Data formatting inconsistent (trim whitespace from all columns)
- Taxonomy codes in Cols 9-10 are NUCC codes (`208D00000X`) — need to map to `HealthcareProviderTaxonomy` by code to get the Salesforce Id
- Role column (Col 25) values may need normalization to `"PCP"` / `"Specialist"` picklist values
- Col 90 Plan Code and Col 91 Provider ID are Penn Medicine internal — needed for `HealthcareFacilityNetwork` network association

---

## 🔍 PDM OmniScript Deep-Dive: "Add Practitioner to Practice Location"

> **Business uses:** `PRM_PDMManualUpdate_English` → Select Practice Location → "Add/Remove a Practitioner" → Add Practitioner  
> The mass load batch MUST replicate every field and every record this flow creates.

---

### **Step 1: Facility Lookup (GroupSelectionFlexCard)**

The user first searches for a Practice Location. The OmniScript uses `SearchResults:GroupSelectionFlexCard:SelectedFacility:Facility` to populate `HCFRecordsToUpdate.FacilityInfo`.

**`FacilityInfo` structure returned (actual sample):**

```json
{
  "AccountId":        "001Ov000013WvnKIAS",   // Account.Id of the group
  "AccountName":      "ALEX WARREN LLC",
  "Active":           true,
  "AddLine1":         "10209 Shiloh Dr",
  "AddLine2":         null,
  "AddressId":        "130Ov0000099t4vIAA",
  "AddressType":      "Primary;Mailing;Billing",
  "CaseManagerId":    "0iTOv0000008K1ZMAU",
  "City":             "Festus",
  "FacilityId":       "0klOv0000007uiDIAQ",   // HealthcareFacility.Id  ← USE THIS
  "Fax":              "...",
  "FullAddress":      "10209 Shiloh Dr  Festus MO 63028-4718",
  "LocationId":       "131Ov000003ZA7dIAG",   // Location.Id
  "LocationName":     "ALEX WARREN LLC (10209 Shiloh Dr-3242)",
  "LocationPractRole":"PCP",
  "Npi":              "1285461566",            // Group NPI  ← LOOKUP BY THIS
  "PLTaxId":          "128546156",             // TIN  ← SECONDARY LOOKUP
  "PracLocDelegated": false,
  "PracLocationNumber":"30000009116",
  "PracticeType":     "PCP",
  "PrimaryFacility":  true,
  "Phone":            "...",
  "State":            "MO",
  "Zip":              "63028"
}
```

**Batch lookup logic (to replicate facility search):**

```apex
// PRIMARY: look up by Group NPI (Col 31)
HealthcareFacility facility = [
    SELECT Id, AccountId, LocationId, Name, PRM_NPI__c, PRM_TaxId__c
    FROM HealthcareFacility
    WHERE PRM_NPI__c = :groupNpi              // Col 31
    AND PRM_Active__c = true
    LIMIT 1
];

// SECONDARY FALLBACK: by TIN (Col 28)
if (facility == null) {
    facility = [
        SELECT Id, AccountId, LocationId, Name
        FROM HealthcareFacility
        WHERE Account.PRM_TaxId__c = :taxId   // Col 28
        AND PRM_Active__c = true
        LIMIT 1
    ];
}

// TERTIARY FALLBACK: by Group Name (Col 32) + address zip (Col 37)
if (facility == null) {
    facility = [
        SELECT Id, AccountId, LocationId, Name
        FROM HealthcareFacility
        WHERE Account.Name LIKE :('%' + groupName + '%')
        AND PRM_Zip__c = :zip                 // Col 37
        AND PRM_Active__c = true
        LIMIT 1
    ];
}
```

---

### **Step 2: Add Practitioner Block — All OmniScript Fields**

These are the **exact form fields** shown to the user in the `AddPractitionerBlock` (shown when `ActionType = "Add2"`).

| OmniScript Element | Type | Label / Purpose | Required | UPHS Excel Source | Salesforce Target Field |
|-------------------|------|-----------------|----------|--------------------|------------------------|
| `FirstnameAdd` | Text | Practitioner First Name | ✅ Yes | Col 5 (First Name) | `Contact.FirstName` / lookup only |
| `LastnameAdd` | Text | Practitioner Last Name | ✅ Yes | Col 4 (Last Name) | `Contact.LastName` / lookup only |
| `MiddlenameAdd` | Text | Practitioner Middle Name | No | Col 6 (Middle Name) | `Contact.MiddleName` / lookup only |
| `NPIAdd` | Text | Practitioner NPI | ✅ Yes | Col 8 (Provider NPI) | `HealthcareProviderNpi.Name` → lookup `Contact.Id` |
| `SpecialtyNameAddPract` | Select | Specialty Name | ✅ Yes | Col 29 (Specialty) | `HealthcareFacilityNetwork.PRM_Specialty__c` / taxonomy name |
| `addFacilityTaxonomy` | Select | Care Taxonomy | ✅ Yes | Cols 9–10 (Taxonomy 1/2) | `HealthcareProviderTaxonomy.TaxonomyCode__c` → Id |
| `addFacilityPrimaryTaxonomy` | Checkbox | Is Primary Taxonomy | No | Determine from Col 9 vs 10 | `HealthcareProviderTaxonomy.IsPrimary__c` / `PRM_Primary__c` |
| `addFacilityRole` | Multi-select | Role: PCP / Specialist | ✅ Yes | Col 25 (Specialist or PCP) | `HealthcareFacilityNetwork.PRM_Role__c` |
| `addFacilityDispinDir` | Checkbox | Display in Directory | No | Col 42 (Print Suppress) → invert | `HealthcareFacilityNetwork.PRM_ShowInDirectory__c` |
| `addFacilityMemSelPCP` | Checkbox | Member Selectable PCP | No | Not in Excel — default `false` | `HealthcareFacilityNetwork.PRM_MemberSelectablePCP__c` |
| `addFacilityBSPA` | Text | BSPA Number | No | Col 1 (Group BSPA) or Col 2 (Provider BSPA) | `HealthcarePractitionerFacility.PRM_BSPA__c` |
| `EffectiveDatePractitioner` | Date | Effective Date of Change | ✅ Yes | Cols 16-24 (Appt/Creds dates) or today | `HealthcarePractitionerFacility.EffectiveFrom` / `StartDate` |
| `addPracticeClasification` | Radio | Practice Classification | ✅ Yes | Col 25 (PCP / Specialist role) | `HealthcareFacilityNetwork.PRM_PracticeClassification__c` |
| `addPracticeType` | Formula | Practice Type | Auto | Derived from role | `HealthcareFacilityNetwork.PRM_PracticeType__c` |
| `addPractionerTeleheathQ` | Radio | Telehealth / In-Person / Hybrid | No | Not in Excel — default `"In-Person"` | `HealthcarePractitionerFacility.PRM_TelehealthType__c` |
| `addLocDelegatedCheck` | Radio | Is this location delegated? | No | Not in Excel — default `false` | `HealthcarePractitionerFacility.PRM_Delegated__c` |
| `isPrimary` | Checkbox | Is Primary Taxonomy | No | Col 9 = primary, Col 10 = secondary | `HealthcareProviderTaxonomy.PRM_Primary__c` |

#### **Key Transformation: DataRaptor `PRMDRTransfromAddPracBlockPDM`**

This DR runs when the user fills in the Add Practitioner block. It transforms form data into a structured JSON that is then passed to `PRM_VerifyPractitionerDetailsParent` and subsequently to `PRM_PDMRecordsCreationParent`.

**Input → Output Mappings (from `_Items.json`):**

| DR Input Path | DR Output Path | Meaning |
|---------------|----------------|---------|
| `Add or Remove a Practitioner:Practitioner:ActionType` | `TransformedPractitioner:ActionType` | `"Add"` |
| `Add or Remove a Practitioner:Practitioner:NPIAdd2-Block:FirstnameAdd2` | `TransformedPractitioner::AddPractitionerBlock:FirstnameAdd` | First name |
| `Add or Remove a Practitioner:Practitioner:NPIAdd2-Block:LastnameAdd2` | `TransformedPractitioner::AddPractitionerBlock:LastnameAdd` | Last name |
| `Add or Remove a Practitioner:Practitioner:NPIAdd2-Block:NPIAdd2` | `TransformedPractitioner:AddPractitionerBlock:NPIAdd` | Provider NPI |
| `Add or Remove a Practitioner:Practitioner:EffectiveDataofChangePrac` | `TransformedPractitioner:AddPractitionerBlock:EffectiveDatePractitioner` | Effective date |
| `Add or Remove a Practitioner:Practitioner:NPIAdd2-Block:SpecialtySelectedName` | `TransformedPractitioner:AddPractitionerBlock:SpecialtyNameAddPract` | Specialty name |
| `Add or Remove a Practitioner:Practitioner:AddressPractitioner` | `TransformedPractitioner:AddressPractitioner` | Location address |

**Formula in DR:**
```
IsPractitionerAdded = IF(
    ISNOTBLANK(FILTER(LIST(%Add or Remove a Practitioner:Practitioner%), "ActionType=='Add'")),
    true, false
)
```

#### **Key Transformation: DataRaptor `PRMTransformPractitionerForExtract`**

Runs inside `PRM_VerifyPractitionerDetails`. Maps the `AddPractitionerBlock` fields into the `Practitioner` node consumed by the IP record creation chain:

| DR Input | DR Output | Notes |
|----------|-----------|-------|
| `Practitioner:AddPractitionerBlock:FirstnameAdd` | `Practitioner:FirstName` | First Name |
| `Practitioner:AddPractitionerBlock:LastnameAdd` | `Practitioner:LastName` | Last Name |
| `Practitioner:AddPractitionerBlock:MiddlenameAdd` | `Practitioner:MiddleName` | Middle Name |
| `Practitioner:AddPractitionerBlock:NPIAdd` | `Practitioner:NPI` | Provider NPI |
| `Practitioner:AddPractitionerBlock:EffectiveDatePractitioner` | `Practitioner:EffectiveDate` | Effective Date |
| `Practitioner:SpecialtyFormula` (from `SpecialtyNameAddPract`) | `Practitioner:Specialty` | Specialty (first `~` delimited value) |
| — | `Practitioner:Pending` = `true` | Always set Pending = true |

---

### **Step 3: IP Payload — `PRM_PDMRecordsCreationParent`**

The OmniScript element `IPCreatePDMRecords` sends the following payload to trigger all record creation:

```json
{
  "ActionType": "Add/Remove a Practitioner",
  "HCFRecordsToUpdate": {
    "ActionType":               "",
    "AddRemovePractitioner":    "<full TransformedPractitioner list>",
    "FacilityInfo":             "<FacilityInfo object from facility search>",
    "OfficeHoursStep":          "",
    "PracLocationManualChange": "Add/Remove a Practitioner",
    "PracticeLocationNameStep": "",
    "PractitionerFacilityToRemove": "",
    "PractitionerFinalListToRemove": "",
    "PractitionerLocationToLoad": "<populated by IPVerifyPractitionerDetails>",
    "RolesAndNetworkOfficeCOI": "",
    "UpdateDirStep":            "",
    "NetworkFacilitiesToLoad":  "<populated by IPVerifyPractitionerDetails>",
    "NetworkFacilitiesToLoadCOI": ""
  },
  "PractitionerLocationToLoad": "<HealthcarePractitionerFacility records to upsert>",
  "ProviderNPI":                "<practitioner's NPI from search>"
}
```

**`IndividualApplication` created (from SampleInput):**
```json
{
  "AccountId":          "<HealthcareFacility.AccountId>",
  "ApplicationType":    "Organization",
  "Category":           "Provider Data Management",
  "CorporateReceiptDate": "<today>",
  "FHNaticCaseNum":     "<sequence number>",
  "FormType":           "AmeriHealth",
  "PracticeLocation":   "<HealthcareFacility.Id>",
  "PracticeLocationName": "<HealthcareFacility.Name>",
  "Stage":              "Network Management QC",
  "Status":             "In Progress"
}
```

**`Case` created:**
```json
{
  "AccountId": "<HealthcareFacility.AccountId>",
  "Status":    "New",
  "Type":      "Network Management QC",
  "RecordType": "Network Management QC",
  "PRM_IsRoundRobinLogic__c": true
}
```

**`PRM_CaseDataManager__c` created (links Case to Change Type):**
```json
{
  "PRM_CaseManager__c":              "<IndividualApplication.Id>",
  "PRM_HealthcareFacilityNetwork__c": true,
  "PRM_Address__c":                  false,
  "PRM_HealthCareFacility__c":       false,
  "PRM_ProgramParticipation__c":     false
}
```

---

### **Step 4: Records Created by `PRM_PDMRecordsCreationHelper`**

The helper IP `CB_AddRemovePractitioner` fires when `HCFRecordsToUpdate:AddRemovePractitioner` is not blank **AND** `PracLocationManualChange != "Add/Remove Network"` **AND** `SV_ActionType:TermCOI == false`.

#### **Record 1: `HealthcarePractitionerFacility` (PPL Record)**

Object: `HealthcarePractitionerFacility`  
DR: `PRMLoadPPLPDM` → creates/updates via `DRLoadPPLPDM` DataRaptor Post Action

| Salesforce Field | Source | Value / Logic |
|-----------------|--------|---------------|
| `RecordTypeId` | System | `PRM_PractitionerLocationAffiliation` record type |
| `PractitionerId` | `Practitioner:NPI` lookup | `Contact.Id` (practitioner Contact) |
| `AccountId` | `FacilityInfo.AccountId` | Group Account Id |
| `EffectiveFrom` | `EffectiveDatePractitioner` | From Excel date or today |
| `EffectiveTo` | — | Blank (open-ended) |
| `IsActive` | Formula: `EffectiveFrom <= TODAY() && (blank EffectiveTo OR EffectiveTo > TODAY())` | Computed |
| `PRM_CaseManager__c` | `DRCreateCaseCaseMgr:IndividualApplication_2:Id` | IndividualApplication.Id |
| `Name` | Computed | `"<PractitionerName> at <FacilityName>"` |

> ⚠️ **Important:** `CB_AddRemovePractitionerHCPF` fires when `PractitionerLocationToLoad` OR `PractitionerFacilityToRemove` is populated. The batch job must pre-populate `PractitionerLocationToLoad` correctly.

#### **Record 2: `HealthcareProviderTaxonomy` (Taxonomy Assignment)**

Object: `HealthcareProviderTaxonomy`  
DR: `PRMDRAddPracticeLocationTaxonomy` → bundle `PRMDRCreatePracticeLocationTaxonomy`  
Fires when: `HCFRecordsToUpdate:ActionType == "Add Practice Location Taxonomy"`

> For "Add Practitioner", one `HealthcareProviderTaxonomy` record is created **per taxonomy** in Cols 9 and 10.

| Salesforce Field | Source | Value |
|-----------------|--------|-------|
| `RecordTypeId` | System | `PRM_FacilityTx` (Practitioner at Practice Location Taxonomy and Network) |
| `HealthcareProviderId` | `Contact.Id` lookup | Practitioner Contact Id |
| `HealthcareFacilityId` | `FacilityInfo.FacilityId` | HealthcareFacility.Id |
| `TaxonomyCode__c` / `Code__c` | `addFacilityTaxonomy` → lookup | NUCC taxonomy code (e.g., `208D00000X`) |
| `Name` | `addFacilityTaxonomy` label | Taxonomy display name |
| `PRM_Primary__c` | `addFacilityPrimaryTaxonomy` checkbox | `true` for Taxonomy 1 (Col 9), `false` for Taxonomy 2 (Col 10) |
| `EffectiveFrom` | `EffectiveDatePractitioner` | Same as HCPF start date |
| `PRM_Active__c` | Computed | `true` |
| `PRM_Pending__c` | — | `true` initially |

#### **Record 3: `HealthcareFacilityNetwork` (Network/Role Assignment)**

Object: `HealthcareFacilityNetwork`  
DR: `PRMDRAddPracticeLocationTaxonomy` (same) + `RAClonePPLTaxForRoles` + `RAClonePPLTaxForPayerNetworks`  
Fires for each network the practitioner is being added to at this location.

> One `HealthcareFacilityNetwork` record per **taxonomy × network × role** combination. For UPHS batch load, networks come from the plan codes (Col 90) or from existing networks on the facility.

| Salesforce Field | Source | Value |
|-----------------|--------|-------|
| `RecordTypeId` | System | `Practitioner at Practice Location Taxonomy and Network` |
| `HealthcareFacilityId` | `FacilityInfo.FacilityId` | HealthcareFacility.Id |
| `PractitionerId` | Contact Id lookup | Practitioner Contact.Id |
| `PRM_Role__c` | `addFacilityRole` | `"PCP"` or `"Specialist"` (Col 25) |
| `PRM_ShowInDirectory__c` | `addFacilityDispinDir` | `true`/`false` (inverse of Col 42 Print Suppress) |
| `PRM_MemberSelectablePCP__c` | `addFacilityMemSelPCP` | `true`/`false` — default `false` |
| `PRM_BSPA__c` | `addFacilityBSPA` | Col 1 (Group BSPA) or Col 2 (Provider BSPA) |
| `PRM_PracticeClassification__c` | `addPracticeClasification` | Derived from role |
| `PRM_Specialty__c` | `SpecialtyNameAddPract` lookup Id | `HealthcareSpecialty.Id` from Col 29 |
| `PRM_TaxonomyId__c` | `addFacilityTaxonomy` | `HealthcareProviderTaxonomy.Id` |
| `PRM_Primary__c` | `addFacilityPrimaryTaxonomy` | Primary taxonomy flag |
| `EffectiveFrom` | `EffectiveDatePractitioner` | Col 16-24 date or today |
| `PRM_Active__c` | Computed | `true` |
| `PRM_Pending__c` | Hardcoded | `true` (always set on creation via PDM) |
| `AccountId` | `FacilityInfo.AccountId` | Group Account.Id |

#### **Record 4: `IndividualApplication` (Case Manager)**

Object: `IndividualApplication`  
RecordType: `PRM_OrganizationalCredential` or equivalent PDM type  
DR: `DRCreateCaseCaseMgr`

| Salesforce Field | Source | Value |
|-----------------|--------|-------|
| `AccountId` | `FacilityInfo.AccountId` | Group Account.Id |
| `ApplicationType` | Hardcoded | `"Organization"` |
| `Category` | Hardcoded | `"Provider Data Management"` |
| `PRM_HealthcareFacility__c` | `FacilityInfo.FacilityId` | HealthcareFacility.Id |
| `PRM_CorporateReceiptDate__c` | Today | `Date.today()` |
| `PRM_Stage__c` | Hardcoded | `"Network Management QC"` |
| `Status` | Hardcoded | `"In Progress"` |
| `PRM_FormType__c` | Config | `"AmeriHealth"` |
| `PRM_FHNaticCaseNumber__c` | Auto-sequence | Sequential case number |
| `RecordTypeId` | System | PDM Organization record type |

#### **Record 5: `Case` (QC Case)**

Object: `Case`  
RecordType: `Network Management QC`

| Salesforce Field | Source | Value |
|-----------------|--------|-------|
| `AccountId` | `FacilityInfo.AccountId` | Group Account.Id |
| `Status` | Hardcoded | `"New"` |
| `Type` | Hardcoded | `"Network Management QC"` |
| `RecordTypeId` | System | `Network Management QC` record type |
| `PRM_CaseManager__c` | `IndividualApplication.Id` | Linked to case manager |
| `PRM_IsRoundRobinLogic__c` | Hardcoded | `true` |

#### **Record 6: `PRM_CaseDataManager__c`**

Object: `PRM_CaseDataManager__c`  
Created by: `DRCreateCaseDatamanager`

| Salesforce Field | Source | Value |
|-----------------|--------|-------|
| `PRM_CaseManager__c` | `IndividualApplication.Id` | Links to case manager |
| `PRM_HealthcareFacilityNetwork__c` | Hardcoded | `true` (for Add Practitioner) |
| `PRM_Address__c` | Hardcoded | `false` |
| `PRM_HealthCareFacility__c` | Hardcoded | `false` |
| `PRM_ProgramParticipation__c` | Hardcoded | `false` |

---

### **Step 5: Fields NOT in UPHS Excel — Defaults Required**

These fields are required by the OmniScript but have no corresponding Excel column. The batch job must supply defaults:

| Field | OmniScript Element | Default Value | Rationale |
|-------|-------------------|---------------|-----------|
| `addPractionerTeleheathQ` (Telehealth type) | Radio | `"In-Person"` | Assume in-person unless specified |
| `addLocDelegatedCheck` (Is Delegated?) | Radio | `false` | UPHS is not delegated |
| `addFacilityMemSelPCP` (Member Selectable PCP) | Checkbox | `false` unless `addFacilityRole = "PCP"` | Only PCP-designated practitioners |
| `addFacilityDispinDir` (Display in Directory) | Checkbox | `true` unless Col 42 = "Y" (Print Suppress) | Invert print suppress flag |
| `addFacilityPrimaryTaxonomy` (Primary Taxonomy) | Checkbox | `true` for Taxonomy 1 (Col 9), `false` for Taxonomy 2 (Col 10) | First taxonomy = primary |
| `PRM_PracticeClassification__c` | Radio | `"Group"` or derived from role | Default Group Practice |
| `PRM_FormType__c` (on IndividualApplication) | Config | `"AmeriHealth"` | Standard for IBX |
| `PRM_Stage__c` | Config | `"Network Management QC"` | Standard PDM stage |
| `CorporateReceiptDate` | Date | `Date.today()` | Batch submission date |

---

## 🏗️ Salesforce Record Creation Chain (Full End-to-End)

```
UPHS Excel Row
    │
    ├─ [1] LOOKUP: HealthcareProvider by NPI (Col 8)
    │         → Contact.Id (PractitionerId)
    │
    ├─ [2] LOOKUP: HealthcareFacility by Group NPI (Col 31) OR TaxId (Col 28)
    │         → HealthcareFacility.Id (FacilityId)
    │         → HealthcareFacility.AccountId (GroupAccountId)
    │         → HealthcareFacility.LocationId (LocationId)
    │
    ├─ [3] LOOKUP: HealthcareProviderTaxonomy (for Taxonomy 1 & 2, Cols 9-10)
    │         → HealthcareProviderTaxonomy.Id (TaxonomyId) per NUCC code
    │
    ├─ [4] LOOKUP: HealthcareSpecialty by name (Col 29)
    │         → HealthcareSpecialty.Id (SpecialtyId)
    │
    ├─ [5] LOOKUP: Existing HFN records on facility (to avoid duplicates)
    │         → HealthcareFacilityNetwork WHERE FacilityId = X AND PractitionerId = Y
    │
    ├─ [6] CREATE: IndividualApplication
    │         AccountId, Category="Provider Data Management",
    │         Stage="Network Management QC", Status="In Progress"
    │
    ├─ [7] CREATE: Case
    │         AccountId, Type="Network Management QC", Status="New"
    │
    ├─ [8] UPDATE: Case.PRM_CaseManager__c = IndividualApplication.Id
    │
    ├─ [9] CREATE: PRM_CaseDataManager__c
    │         PRM_CaseManager__c = IndividualApplication.Id
    │         PRM_HealthcareFacilityNetwork__c = true
    │
    ├─ [10] CREATE: HealthcarePractitionerFacility (HCPF)
    │          RecordType = PRM_PractitionerLocationAffiliation
    │          PractitionerId = Contact.Id
    │          AccountId = FacilityInfo.AccountId
    │          EffectiveFrom = EffectiveDate (Col date or today)
    │          PRM_BSPA__c = BSPA (Col 1 or 2)
    │          PRM_CaseManager__c = IndividualApplication.Id
    │
    ├─ [11] CREATE: HealthcareProviderTaxonomy (per taxonomy in Cols 9-10)
    │          RecordType = PRM_FacilityTx
    │          HealthcareProviderId = Contact.Id
    │          HealthcareFacilityId = FacilityId
    │          TaxonomyCode = NUCC code (Col 9 or 10)
    │          PRM_Primary__c = true (Col 9) / false (Col 10)
    │          EffectiveFrom = EffectiveDate
    │          PRM_Pending__c = true
    │
    └─ [12] CREATE: HealthcareFacilityNetwork (per taxonomy × network × role)
               RecordType = Practitioner at Practice Location Taxonomy and Network
               HealthcareFacilityId = FacilityId
               PractitionerId = Contact.Id
               PRM_Role__c = "PCP" or "Specialist" (Col 25)
               PRM_ShowInDirectory__c = true (unless Col 42 = "Y")
               PRM_Specialty__c = HealthcareSpecialty.Id (from Col 29)
               PRM_TaxonomyId__c = HealthcareProviderTaxonomy.Id
               PRM_BSPA__c = BSPA (Col 1 or 2)
               EffectiveFrom = EffectiveDate
               PRM_Pending__c = true
               PRM_Active__c = true
```

---

## 🏗️ Salesforce Data Model Context

### **Key Objects Summary**

1. **Contact / Account (Practitioner)**
   - Person Account for each practitioner
   - `HealthcareProvider` links `Contact.Id` → NPI lookup
   - Lookup: `SELECT Id FROM Contact WHERE ...HealthcareProviderNpi.Name = :npi`

2. **HealthcareFacility**
   - The Practice Location
   - `PRM_NPI__c` = Group NPI (Col 31) ← primary lookup
   - `PRM_TaxId__c` = TIN (Col 28) ← secondary lookup
   - `AccountId` = Group Account
   - `LocationId` = related Location record

3. **HealthcarePractitionerFacility** ← Main junction record
   - `RecordType = PRM_PractitionerLocationAffiliation`
   - Links `Contact` (practitioner) ↔ `HealthcareFacility`
   - Contains: BSPA, EffectiveFrom, CaseManagerId, Active flag

4. **HealthcareProviderTaxonomy**
   - One per taxonomy per practitioner-facility combination
   - `RecordType = PRM_FacilityTx`
   - Contains: TaxonomyCode, IsPrimary, EffectiveFrom, Pending

5. **HealthcareFacilityNetwork**
   - One per taxonomy × network × role
   - `RecordType = Practitioner at Practice Location Taxonomy and Network`
   - Contains: Role (PCP/Specialist), ShowInDirectory, MemberSelectablePCP, Specialty, Taxonomy, BSPA

6. **IndividualApplication** (Case Manager)
   - Category = "Provider Data Management"
   - Stage = "Network Management QC"
   - Links to HealthcareFacility

7. **Case** (QC Work Item)
   - Type = "Network Management QC"
   - Links to Account (Group)
   - `PRM_CaseManager__c` = IndividualApplication.Id

8. **PRM_CaseDataManager__c**
   - Tracks what data changed in the case
   - `PRM_HealthcareFacilityNetwork__c = true` for Add Practitioner

---

## 💡 Three Recommended Solutions

### **OPTION 1: Apex Batch Job (Recommended — Best Match to PDM Flow)**

**Overview:**  
Create a batch Apex class that reads staging data and replicates **every** record the PDM OmniScript creates, in the correct order, with all required fields.

**Advantages:**
✅ Runs asynchronously (no UI timeout)  
✅ Handles 107 records easily in batch  
✅ Can be re-run for failed records  
✅ Scheduling support for future loads  
✅ Error logging per record  
✅ Matches exact PDM field structure  

**Disadvantages:**
❌ Requires 2-3 days to develop + test  
❌ Cannot call OmniScript IP directly — must replicate DML logic  
❌ Requires Excel → CSV conversion before staging  

**Implementation:**

#### **Step 1: Staging Object Fields**

```
PRM_MassLoadStagingData__c
├── Status__c              (Picklist: Pending | Processed | Error | Skipped)
├── Error_Message__c       (Long Text)
├── Source_Row__c          (Number)
│
│── PRACTITIONER FIELDS ─────────────────────────────────────────────────
├── Provider_NPI__c        (Text 10) ← Col 8  [PRIMARY KEY]
├── First_Name__c          (Text)    ← Col 5
├── Last_Name__c           (Text)    ← Col 4
├── Middle_Name__c         (Text)    ← Col 6
├── Degree__c              (Text)    ← Col 7
├── DOB__c                 (Date)    ← Col 11  [optional]
├── Gender__c              (Text)    ← Col 12  [optional]
│
│── TAXONOMY FIELDS ──────────────────────────────────────────────────────
├── Taxonomy_1__c          (Text 20) ← Col 9  (NUCC code)
├── Taxonomy_2__c          (Text 20) ← Col 10 (NUCC code, secondary)
├── Specialty__c           (Text)    ← Col 29
│
│── ROLE & DIRECTORY FIELDS ──────────────────────────────────────────────
├── Role__c                (Text)    ← Col 25 (PCP / Specialist)
├── Print_Suppress__c      (Checkbox)← Col 42 (Y=suppress = NOT shown in dir)
├── Is_Delegated__c        (Checkbox)← default false
├── Telehealth_Type__c     (Text)    ← default "In-Person"
│
│── BSPA FIELDS ──────────────────────────────────────────────────────────
├── Group_BSPA__c          (Text)    ← Col 1
├── Provider_BSPA__c       (Text)    ← Col 2
│
│── FACILITY FIELDS ──────────────────────────────────────────────────────
├── Group_NPI__c           (Text 10) ← Col 31 [PRIMARY FACILITY KEY]
├── Tax_ID__c              (Text 20) ← Col 28 [SECONDARY FACILITY KEY]
├── Group_Name__c          (Text)    ← Col 32 [TERTIARY FACILITY KEY]
├── Address_Line_1__c      (Text)    ← Col 33
├── Address_Line_2__c      (Text)    ← Col 34
├── City__c                (Text)    ← Col 35
├── State__c               (Text)    ← Col 36
├── Zip__c                 (Text)    ← Col 37
├── County__c              (Text)    ← Col 38
├── Phone__c               (Text)    ← Col 39
├── Fax__c                 (Text)    ← Col 40
│
│── EFFECTIVE DATE FIELDS ────────────────────────────────────────────────
├── Effective_Date__c      (Date)    ← Col 16-24 (use earliest appt/creds date)
├── Corporate_Receipt_Date__c (Date) ← today (batch run date)
│
│── RESULT FIELDS ────────────────────────────────────────────────────────
├── HCPF_Id__c             (Text 18) ← created HealthcarePractitionerFacility.Id
├── Case_Manager_Id__c     (Text 18) ← created IndividualApplication.Id
├── Case_Id__c             (Text 18) ← created Case.Id
└── HFN_Ids__c             (Long Text) ← comma-separated HealthcareFacilityNetwork Ids
```

#### **Step 2: Batch Class**

```apex
/**
 * @ClassName: PRM_UPHSPractitionerLocationBatch
 * @Description: Replicates the PDM OmniScript "Add Practitioner to Practice Location"
 *               flow for the UPHS mass load.
 * @Mirrors: PRM_PDMManualUpdate_English → Add/Remove a Practitioner → Add
 */
public class PRM_UPHSPractitionerLocationBatch
    implements Database.Batchable<PRM_MassLoadStagingData__c>, Database.Stateful {

    private Integer successCount = 0;
    private Integer errorCount   = 0;
    private List<String> errorLog = new List<String>();

    // ──────────────────────────────────────────────────────────────
    // start: query pending staging records
    // ──────────────────────────────────────────────────────────────
    public Iterable<PRM_MassLoadStagingData__c> start(Database.BatchableContext bc) {
        return [
            SELECT Id, Source_Row__c,
                   Provider_NPI__c, First_Name__c, Last_Name__c, Middle_Name__c,
                   Taxonomy_1__c, Taxonomy_2__c, Specialty__c,
                   Role__c, Print_Suppress__c, Is_Delegated__c, Telehealth_Type__c,
                   Group_BSPA__c, Provider_BSPA__c,
                   Group_NPI__c, Tax_ID__c, Group_Name__c,
                   Address_Line_1__c, City__c, State__c, Zip__c,
                   Effective_Date__c, Corporate_Receipt_Date__c
            FROM PRM_MassLoadStagingData__c
            WHERE Status__c = 'Pending'
            ORDER BY Source_Row__c ASC
        ];
    }

    // ──────────────────────────────────────────────────────────────
    // execute: process each batch
    // ──────────────────────────────────────────────────────────────
    public void execute(Database.BatchableContext bc,
                        List<PRM_MassLoadStagingData__c> scope) {

        // ── Collect lookup keys ────────────────────────────────────
        Set<String> providerNPIs  = new Set<String>();
        Set<String> groupNPIs     = new Set<String>();
        Set<String> taxIds        = new Set<String>();
        Set<String> taxCodes      = new Set<String>();
        Set<String> specialtyNames= new Set<String>();

        for (PRM_MassLoadStagingData__c s : scope) {
            if (String.isNotBlank(s.Provider_NPI__c))  providerNPIs.add(s.Provider_NPI__c.trim());
            if (String.isNotBlank(s.Group_NPI__c))     groupNPIs.add(s.Group_NPI__c.trim());
            if (String.isNotBlank(s.Tax_ID__c))        taxIds.add(s.Tax_ID__c.trim());
            if (String.isNotBlank(s.Taxonomy_1__c))    taxCodes.add(s.Taxonomy_1__c.trim());
            if (String.isNotBlank(s.Taxonomy_2__c))    taxCodes.add(s.Taxonomy_2__c.trim());
            if (String.isNotBlank(s.Specialty__c))     specialtyNames.add(s.Specialty__c.trim());
        }

        // ── LOOKUP 1: Practitioners by NPI ───────────────────────
        // HealthcareProviderNpi links NPI → Contact (Practitioner)
        Map<String, Id> npiToContactId = new Map<String, Id>();
        for (HealthcareProviderNpi hpn : [
            SELECT Name, HealthcareProviderId,
                   HealthcareProvider.RelatedPersonId
            FROM HealthcareProviderNpi
            WHERE Name IN :providerNPIs
            AND PRM_Active__c = true
        ]) {
            // RelatedPersonId = Contact.Id (person account / practitioner)
            npiToContactId.put(hpn.Name, hpn.HealthcareProvider.RelatedPersonId);
        }

        // ── LOOKUP 2: Facilities by Group NPI ────────────────────
        // HealthcareFacility.PRM_NPI__c = Group NPI (Col 31)
        Map<String, HealthcareFacility> groupNpiToFacility = new Map<String, HealthcareFacility>();
        for (HealthcareFacility hf : [
            SELECT Id, AccountId, LocationId, Name,
                   PRM_NPI__c, PRM_TaxId__c
            FROM HealthcareFacility
            WHERE PRM_NPI__c IN :groupNPIs
            AND PRM_Active__c = true
        ]) {
            groupNpiToFacility.put(hf.PRM_NPI__c, hf);
        }

        // ── LOOKUP 2b: Facilities by TaxId (fallback) ─────────────
        Map<String, HealthcareFacility> taxIdToFacility = new Map<String, HealthcareFacility>();
        for (HealthcareFacility hf : [
            SELECT Id, AccountId, LocationId, Name,
                   PRM_NPI__c, PRM_TaxId__c
            FROM HealthcareFacility
            WHERE Account.PRM_TaxId__c IN :taxIds
            AND PRM_Active__c = true
            AND PRM_NPI__c NOT IN :groupNPIs
        ]) {
            taxIdToFacility.put(hf.PRM_TaxId__c, hf);
        }

        // ── LOOKUP 3: Taxonomy codes ──────────────────────────────
        // HealthcareProviderTaxonomy at facility level by NUCC code
        Map<String, Id> taxCodeToHCPTId = new Map<String, Id>();
        for (HealthcareProviderTaxonomy hpt : [
            SELECT Id, PRM_TaxonomyCode__c
            FROM HealthcareProviderTaxonomy
            WHERE PRM_TaxonomyCode__c IN :taxCodes
            AND RecordType.DeveloperName = 'PRM_TaxonomyCode'
            LIMIT 500
        ]) {
            if (!taxCodeToHCPTId.containsKey(hpt.PRM_TaxonomyCode__c)) {
                taxCodeToHCPTId.put(hpt.PRM_TaxonomyCode__c, hpt.Id);
            }
        }

        // ── LOOKUP 4: Specialties ─────────────────────────────────
        Map<String, Id> specialtyNameToId = new Map<String, Id>();
        for (HealthcareSpecialty hs : [
            SELECT Id, Name
            FROM HealthcareSpecialty
            WHERE Name IN :specialtyNames
        ]) {
            specialtyNameToId.put(hs.Name, hs.Id);
        }

        // ── RecordType IDs ────────────────────────────────────────
        Id hcpfRecordTypeId = Schema.getGlobalDescribe()
            .get('HealthcarePractitionerFacility').getDescribe()
            .getRecordTypeInfosByDeveloperName()
            .get('PRM_PractitionerLocationAffiliation').getRecordTypeId();

        Id hptRecordTypeId = Schema.getGlobalDescribe()
            .get('HealthcareProviderTaxonomy').getDescribe()
            .getRecordTypeInfosByDeveloperName()
            .get('PRM_FacilityTx').getRecordTypeId();

        Id hfnRecordTypeId = Schema.getGlobalDescribe()
            .get('HealthcareFacilityNetwork').getDescribe()
            .getRecordTypeInfosByDeveloperName()
            .get('PRM_PractitionerAtPLTaxAndNetwork').getRecordTypeId();

        Id caseRecordTypeId = Schema.getGlobalDescribe()
            .get('Case').getDescribe()
            .getRecordTypeInfosByDeveloperName()
            .get('Network_Management_QC').getRecordTypeId();

        Id iaRecordTypeId = Schema.getGlobalDescribe()
            .get('IndividualApplication').getDescribe()
            .getRecordTypeInfosByDeveloperName()
            .get('PRM_OrganizationalCredential').getRecordTypeId();

        // ── Process each staging record ────────────────────────────
        List<PRM_MassLoadStagingData__c> toUpdate = new List<PRM_MassLoadStagingData__c>();

        for (PRM_MassLoadStagingData__c s : scope) {
            try {
                // Step 1: Resolve practitioner Contact
                Id contactId = npiToContactId.get(s.Provider_NPI__c?.trim());
                if (contactId == null) {
                    throw new BatchException('Practitioner NPI not found: ' + s.Provider_NPI__c);
                }

                // Step 2: Resolve facility
                HealthcareFacility facility = groupNpiToFacility.get(s.Group_NPI__c?.trim());
                if (facility == null && String.isNotBlank(s.Tax_ID__c)) {
                    facility = taxIdToFacility.get(s.Tax_ID__c?.trim());
                }
                if (facility == null) {
                    throw new BatchException('HealthcareFacility not found. Group NPI: '
                        + s.Group_NPI__c + ', TaxId: ' + s.Tax_ID__c);
                }

                // Step 3: Resolve effective date
                Date effectiveDate = s.Effective_Date__c != null
                    ? s.Effective_Date__c
                    : Date.today();
                Date receiptDate = s.Corporate_Receipt_Date__c != null
                    ? s.Corporate_Receipt_Date__c
                    : Date.today();

                // Step 4: Resolve BSPA (Provider BSPA takes priority over Group BSPA)
                String bspa = String.isNotBlank(s.Provider_BSPA__c)
                    ? s.Provider_BSPA__c.trim()
                    : (String.isNotBlank(s.Group_BSPA__c) ? s.Group_BSPA__c.trim() : null);

                // Step 5: CREATE IndividualApplication (Case Manager)
                // Mirrors: DRCreateCaseCaseMgr in PRM_PDMRecordsCreationHelper
                IndividualApplication ia = new IndividualApplication(
                    AccountId                  = facility.AccountId,
                    ApplicationType            = 'Organization',
                    Category                   = 'Provider Data Management',
                    PRM_HealthcareFacility__c   = facility.Id,
                    PRM_CorporateReceiptDate__c = receiptDate,
                    PRM_Stage__c               = 'Network Management QC',
                    PRM_FormType__c            = 'AmeriHealth',
                    Status                     = 'In Progress',
                    RecordTypeId               = iaRecordTypeId
                );
                insert ia;

                // Step 6: CREATE Case (QC Work Item)
                // Mirrors: DRCreateCaseCaseMgr → Case_1 upsert
                Case qcCase = new Case(
                    AccountId               = facility.AccountId,
                    Status                  = 'New',
                    Type                    = 'Network Management QC',
                    RecordTypeId            = caseRecordTypeId,
                    PRM_IsRoundRobinLogic__c = true
                );
                insert qcCase;

                // Step 7: UPDATE Case to link CaseManager
                // Mirrors: DRCreateCaseDatamanager → Case_2 upsert
                qcCase.PRM_CaseManager__c = ia.Id;
                update qcCase;

                // Step 8: CREATE PRM_CaseDataManager__c
                // Mirrors: DRCreateCaseDatamanager → PRM_CaseDataManager__c_1
                PRM_CaseDataManager__c cdm = new PRM_CaseDataManager__c(
                    PRM_CaseManager__c              = ia.Id,
                    PRM_HealthcareFacilityNetwork__c = true,
                    PRM_Address__c                  = false,
                    PRM_HealthCareFacility__c        = false,
                    PRM_ProgramParticipation__c      = false
                );
                insert cdm;

                // Step 9: CREATE HealthcarePractitionerFacility (HCPF / PPL)
                // Mirrors: PRMLoadPPLPDM DataRaptor Post Action
                // RecordType: PRM_PractitionerLocationAffiliation
                HealthcarePractitionerFacility hcpf = new HealthcarePractitionerFacility(
                    RecordTypeId      = hcpfRecordTypeId,
                    PractitionerId    = contactId,          // Contact.Id
                    AccountId         = facility.AccountId,
                    EffectiveFrom     = effectiveDate,
                    PRM_CaseManager__c = ia.Id,
                    PRM_Active__c     = true,
                    PRM_Pending__c    = true,
                    PRM_BSPA__c       = bspa
                    // NOTE: PRM_Delegated__c, PRM_TelehealthType__c populated below
                );

                // Telehealth type (addPractionerTeleheathQ)
                hcpf.PRM_TelehealthType__c = String.isNotBlank(s.Telehealth_Type__c)
                    ? s.Telehealth_Type__c
                    : 'In-Person';

                // Delegated (addLocDelegatedCheck)
                hcpf.PRM_Delegated__c = s.Is_Delegated__c == true;

                insert hcpf;

                // Step 10: CREATE HealthcareProviderTaxonomy records (per taxonomy)
                // Mirrors: PRMDRAddPracticeLocationTaxonomy
                // RecordType: PRM_FacilityTx
                List<HealthcareProviderTaxonomy> taxonomiesToCreate
                    = new List<HealthcareProviderTaxonomy>();

                if (String.isNotBlank(s.Taxonomy_1__c)) {
                    taxonomiesToCreate.add(new HealthcareProviderTaxonomy(
                        RecordTypeId          = hptRecordTypeId,
                        HealthcareProviderId  = contactId,
                        HealthcareFacilityId  = facility.Id,
                        PRM_TaxonomyCode__c   = s.Taxonomy_1__c.trim(),
                        PRM_Primary__c        = true,               // addFacilityPrimaryTaxonomy
                        EffectiveFrom         = effectiveDate,
                        PRM_Active__c         = true,
                        PRM_Pending__c        = true
                    ));
                }
                if (String.isNotBlank(s.Taxonomy_2__c)) {
                    taxonomiesToCreate.add(new HealthcareProviderTaxonomy(
                        RecordTypeId          = hptRecordTypeId,
                        HealthcareProviderId  = contactId,
                        HealthcareFacilityId  = facility.Id,
                        PRM_TaxonomyCode__c   = s.Taxonomy_2__c.trim(),
                        PRM_Primary__c        = false,              // secondary taxonomy
                        EffectiveFrom         = effectiveDate,
                        PRM_Active__c         = true,
                        PRM_Pending__c        = true
                    ));
                }
                if (!taxonomiesToCreate.isEmpty()) {
                    insert taxonomiesToCreate;
                }

                // Step 11: CREATE HealthcareFacilityNetwork records
                // Mirrors: RAClonePPLTaxForRoles / RAClonePPLTaxForPayerNetworks
                // RecordType: PRM_PractitionerAtPLTaxAndNetwork (Practitioner at Practice Location Taxonomy and Network)
                Boolean showInDir   = !(s.Print_Suppress__c == true);  // invert suppress flag
                String  role        = String.isNotBlank(s.Role__c)
                                      ? s.Role__c.trim()
                                      : 'Specialist';
                Boolean memSelPCP   = role == 'PCP';  // default: PCP = selectable
                Id      specialtyId = specialtyNameToId.get(s.Specialty__c?.trim());

                List<HealthcareFacilityNetwork> hfnToCreate
                    = new List<HealthcareFacilityNetwork>();

                for (HealthcareProviderTaxonomy tax : taxonomiesToCreate) {
                    HealthcareFacilityNetwork hfn = new HealthcareFacilityNetwork(
                        RecordTypeId              = hfnRecordTypeId,
                        HealthcareFacilityId      = facility.Id,
                        PractitionerId            = contactId,       // addFacilityRole context
                        PRM_Role__c               = role,            // addFacilityRole
                        PRM_ShowInDirectory__c    = showInDir,       // addFacilityDispinDir
                        PRM_MemberSelectablePCP__c = memSelPCP,      // addFacilityMemSelPCP
                        PRM_BSPA__c               = bspa,            // addFacilityBSPA
                        PRM_Specialty__c          = specialtyId,     // SpecialtyNameAddPract
                        PRM_TaxonomyId__c         = tax.Id,          // addFacilityTaxonomy
                        PRM_Primary__c            = tax.PRM_Primary__c, // addFacilityPrimaryTaxonomy
                        EffectiveFrom             = effectiveDate,
                        AccountId                 = facility.AccountId,
                        PRM_Active__c             = true,
                        PRM_Pending__c            = true,
                        PRM_CaseManager__c        = ia.Id
                    );
                    hfnToCreate.add(hfn);
                }
                if (!hfnToCreate.isEmpty()) {
                    insert hfnToCreate;
                }

                // Mark staging record as processed
                s.Status__c        = 'Processed';
                s.HCPF_Id__c       = hcpf.Id;
                s.Case_Manager_Id__c = ia.Id;
                s.Case_Id__c       = qcCase.Id;
                successCount++;

            } catch (Exception e) {
                s.Status__c       = 'Error';
                s.Error_Message__c = e.getMessage();
                errorLog.add('Row ' + s.Source_Row__c + ' | NPI: ' + s.Provider_NPI__c
                    + ' | Group NPI: ' + s.Group_NPI__c + ' | Error: ' + e.getMessage());
                errorCount++;
            }
            toUpdate.add(s);
        }

        Database.update(toUpdate, false);
    }

    // ──────────────────────────────────────────────────────────────
    // finish: email summary
    // ──────────────────────────────────────────────────────────────
    public void finish(Database.BatchableContext bc) {
        Messaging.SingleEmailMessage mail = new Messaging.SingleEmailMessage();
        mail.setToAddresses(new List<String>{ UserInfo.getUserEmail() });
        mail.setSubject('UPHS PDM Mass Load Batch — Job Complete');
        mail.setPlainTextBody(
            'UPHS Practitioner-Location Mass Load Batch Complete\n\n'
            + '✅ Success: ' + successCount + '\n'
            + '❌ Errors:  ' + errorCount  + '\n\n'
            + 'Error Details:\n'
            + String.join(errorLog, '\n')
        );
        Messaging.sendEmail(new List<Messaging.SingleEmailMessage>{ mail });
    }

    public class BatchException extends Exception {}
}
```

#### **Step 3: Execute the Batch**

```apex
// Execute batch — 10 records per batch (1 row = multiple DML ops; keep small)
PRM_UPHSPractitionerLocationBatch batch = new PRM_UPHSPractitionerLocationBatch();
Database.executeBatch(batch, 10);

// Or use Anonymous Apex to run immediately:
Database.executeBatch(new PRM_UPHSPractitionerLocationBatch(), 10);
```

#### **Step 4: Pre-flight Data Validation Query**

Before running, verify all practitioners and facilities exist in Salesforce:

```soql
-- Validate NPIs exist:
SELECT Id, Name, PRM_NPI__c
FROM HealthcareProviderNpi
WHERE Name IN ('1234567890', '0987654321', ...)  -- paste all 107 NPIs
AND PRM_Active__c = true

-- Validate Group NPIs resolve to HealthcareFacility:
SELECT Id, Name, PRM_NPI__c, Account.Name, PRM_Active__c
FROM HealthcareFacility
WHERE PRM_NPI__c IN ('1285461566', ...)  -- paste all Group NPIs (Col 31)

-- Check for existing HCPF records (avoid duplicates):
SELECT Id, PractitionerId, AccountId, EffectiveFrom, PRM_Active__c
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
AND PractitionerId IN (
    SELECT HealthcareProvider.RelatedPersonId
    FROM HealthcareProviderNpi
    WHERE Name IN ('1234567890', ...)
)
AND PRM_Active__c = true
```

**Timeline:** 2-3 days  
**Complexity:** Medium  
**Risk Level:** Low (matches exact PDM field structure)

---

### **OPTION 2: Data Integration Cloud / Mulesoft (Recommended for Recurring Loads)**

**Overview:**  
Use Salesforce Data Integration Cloud or Mulesoft API-led approach to ingest CSV and create records via REST API calls to custom Apex endpoint.

**Advantages:**
✅ Enterprise-grade data integration  
✅ Repeatable/scheduled loads  
✅ Data transformation via flows  
✅ Built-in error handling & retry  
✅ Native Salesforce solution (no external tools)  
✅ Audit trail of all imports  

**Disadvantages:**
❌ Requires DIC or Mulesoft licensing  
❌ Steeper learning curve  
❌ Higher initial setup (3-5 days)  
❌ Overkill if load is one-time  

**Architecture:**

```
Excel File (UPHS.xlsx)
    ↓ (Upload to data cloud)
Salesforce Data Integration Cloud
    ├─ Data Parser (CSV/Excel reader)
    ├─ Data Transformer (column mapping per table above)
    ├─ Validation Rules (NPI exists, facility exists)
    └─ Sync Job → calls PRM_UPHSMassLoadAPI endpoint
        ↓
    REST API Endpoint (Custom Apex)
        ├─ Receives JSON payload
        ├─ Calls PRM_UPHSPractitionerLocationBatch
        └─ Returns batchJobId + status
```

**Custom REST Endpoint:**

```apex
@RestResource(urlMapping='/api/v1/uphs/mass-load')
global class PRM_UPHSMassLoadAPI {
    @HttpPost
    global static void loadPractitioners() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        // Parse incoming records
        Map<String, Object> payload = (Map<String, Object>)
            JSON.deserializeUntyped(req.requestBody.toString());

        // Insert into staging object
        List<PRM_MassLoadStagingData__c> stagingRecords
            = buildStagingRecords(payload);
        insert stagingRecords;

        // Fire batch
        Id jobId = Database.executeBatch(
            new PRM_UPHSPractitionerLocationBatch(), 10
        );

        res.addHeader('Content-Type', 'application/json');
        res.responseBody = Blob.valueOf(JSON.serialize(
            new Map<String, Object>{ 'batchJobId' => jobId, 'status' => 'QUEUED' }
        ));
    }

    private static List<PRM_MassLoadStagingData__c> buildStagingRecords(
            Map<String, Object> payload) {
        List<PRM_MassLoadStagingData__c> result = new List<PRM_MassLoadStagingData__c>();
        List<Object> records = (List<Object>) payload.get('records');
        Integer rowNum = 1;
        for (Object r : records) {
            Map<String, Object> row = (Map<String, Object>) r;
            result.add(new PRM_MassLoadStagingData__c(
                Source_Row__c    = rowNum++,
                Provider_NPI__c  = String.valueOf(row.get('providerNPI')),
                First_Name__c    = String.valueOf(row.get('firstName')),
                Last_Name__c     = String.valueOf(row.get('lastName')),
                Middle_Name__c   = String.valueOf(row.get('middleName')),
                Group_NPI__c     = String.valueOf(row.get('groupNPI')),
                Tax_ID__c        = String.valueOf(row.get('taxId')),
                Taxonomy_1__c    = String.valueOf(row.get('taxonomy1')),
                Taxonomy_2__c    = String.valueOf(row.get('taxonomy2')),
                Specialty__c     = String.valueOf(row.get('specialty')),
                Role__c          = String.valueOf(row.get('role')),
                Group_BSPA__c    = String.valueOf(row.get('groupBSPA')),
                Provider_BSPA__c = String.valueOf(row.get('providerBSPA')),
                Effective_Date__c = Date.valueOf(String.valueOf(row.get('effectiveDate'))),
                Status__c        = 'Pending'
            ));
        }
        return result;
    }
}
```

**Timeline:** 3-5 days  
**Complexity:** High  
**Risk Level:** Medium

---

### **OPTION 3: Manual Upload via Lightning Web Component (Fastest MVP)**

**Overview:**  
LWC component that accepts Excel/CSV upload and processes records in UI with immediate feedback.

**Advantages:**
✅ Fastest to implement (1-2 days)  
✅ Interactive user feedback  
✅ Good for one-time or small batches  

**Disadvantages:**
❌ Limited to ~100 records per upload (UI timeout with complex DML chain)  
❌ Not ideal for 107-row UPHS load with 6 DML objects per row  
❌ No built-in retry mechanism  

**Key difference from original:** The LWC component must call the full batch endpoint, not just create HCPF. The PDM flow creates 6 objects per row: HCPF + HPT (×2 taxonomies) + HFN (×2) + IndividualApplication + Case + CaseDataManager.

**Recommended approach:** LWC as a **trigger interface** that calls the batch job, not as a direct DML processor.

---

## 📋 Decision Matrix

| Criteria | Option 1: Batch | Option 2: DIC | Option 3: LWC |
|----------|-----------------|---------------|---------------|
| **Data Volume (107 rows)** | ✅ Perfect | ✅ Overkill | ⚠️ Risky (6 DML/row) |
| **Matches PDM OmniScript** | ✅✅ Full match | ✅ Via API | ⚠️ Partial |
| **Setup Time** | ⏱️ 2-3 days | ⏱️ 3-5 days | ⏱️ 1-2 days |
| **DML Accuracy** | ✅✅ HCPF+HPT+HFN+IA+Case | ✅ Via batch | ⚠️ Batch trigger only |
| **Recurring Loads** | ✅ Scheduler | ✅✅ Native | ❌ Manual |
| **Error Recovery** | ✅ Re-run Pending | ✅ DIC retry | ❌ Manual |
| **Real-time Feedback** | ⚠️ Email on finish | ⚠️ Job log | ✅ Live UI |
| **Cost** | ✅ Free | ⚠️ License cost | ✅ Free |
| **Best For** | **THIS USE CASE** | Enterprise, recurring | Fast demo |

---

## 🎯 Recommendation

### **Primary Approach: OPTION 1 (Batch Job)**

**Why this is the right choice:**

1. ✅ **Complete field parity** — Batch creates all 6 record types the PDM OmniScript creates
2. ✅ **Correct lookup chain** — Group NPI → TaxID → Group Name fallbacks match actual OS lookup
3. ✅ **107 records** — Perfect batch size (process 10 at a time = 11 batches)
4. ✅ **Reusable staging object** — Can be loaded via Data Import Wizard or CSV
5. ✅ **Full audit trail** — Every created record ID stored back in staging object
6. ✅ **Error isolation** — One bad row doesn't fail the whole batch

**Implementation Steps:**
1. **Day 1 AM:** Create `PRM_MassLoadStagingData__c` custom object (all fields above)
2. **Day 1 PM:** Deploy batch class `PRM_UPHSPractitionerLocationBatch`
3. **Day 1 PM:** Create test class (min 80% coverage)
4. **Day 2 AM:** Convert UPHS.xlsx → CSV, map columns → staging object, import via Data Import Wizard
5. **Day 2 PM:** Run pre-flight SOQL queries to validate all NPIs and Group NPIs exist
6. **Day 2 PM:** Execute batch in Sandbox, review results
7. **Day 3:** Fix errors, re-run failed records, promote to UAT then Production

---

## 📝 Implementation Checklist

### **Phase 1: Setup (Day 1)**
- [ ] Create staging object: `PRM_MassLoadStagingData__c` (all fields listed above)
- [ ] Create batch class: `PRM_UPHSPractitionerLocationBatch`
- [ ] Create test class with 80%+ coverage
- [ ] Validate record type exists: `HealthcarePractitionerFacility.PRM_PractitionerLocationAffiliation`
- [ ] Validate record type exists: `HealthcareProviderTaxonomy.PRM_FacilityTx`
- [ ] Validate record type exists: `HealthcareFacilityNetwork.PRM_PractitionerAtPLTaxAndNetwork`
- [ ] Validate record type exists: `Case.Network_Management_QC`
- [ ] Validate record type exists: `IndividualApplication.PRM_OrganizationalCredential`

### **Phase 2: Data Preparation (Day 2)**
- [ ] Convert UPHS.xlsx → CSV
- [ ] Map Excel columns to staging object fields (per table above)
- [ ] Normalize Role column (Col 25) → `"PCP"` / `"Specialist"`
- [ ] Normalize Taxonomy codes (Cols 9-10) → NUCC format (e.g., `208D00000X`)
- [ ] Set `Print_Suppress__c = TRUE` where Col 42 = "Y"
- [ ] Set `Effective_Date__c` from earliest date in Cols 16-24
- [ ] Import CSV via Salesforce Data Import Wizard into staging object

### **Phase 3: Validation (Day 2 PM)**
- [ ] Run pre-flight query: confirm 107/107 Provider NPIs found in `HealthcareProviderNpi`
- [ ] Run pre-flight query: confirm all Group NPIs found in `HealthcareFacility.PRM_NPI__c`
- [ ] Run pre-flight query: confirm all NUCC taxonomy codes found in `HealthcareProviderTaxonomy`
- [ ] Run pre-flight query: confirm all specialty names found in `HealthcareSpecialty`
- [ ] Check for existing active HCPF records (avoid duplicates)

### **Phase 4: Execution (Day 2-3)**
- [ ] Run batch in Sandbox: `Database.executeBatch(new PRM_UPHSPractitionerLocationBatch(), 10)`
- [ ] Review staging records: Status = Processed / Error
- [ ] Fix error rows (update staging records, re-set `Status__c = 'Pending'`, re-run)
- [ ] UAT: Business team verifies created records in Salesforce
- [ ] Deploy to Production

### **Phase 5: Documentation**
- [ ] Document all error codes and recovery steps
- [ ] Document column mapping for future reference
- [ ] Archive staging data (after processing, change status to `Archived`)
- [ ] Create runbook for any future UPHS or similar loads

---

## 🚀 Pre-flight SOQL Queries (Run Before Batch)

```soql
-- 1. Count how many Provider NPIs are found (expect 107):
SELECT COUNT()
FROM HealthcareProviderNpi
WHERE Name IN (/* paste 107 NPIs */)
AND PRM_Active__c = true

-- 2. List any Provider NPIs NOT found:
SELECT Name FROM HealthcareProviderNpi
WHERE Name NOT IN (SELECT Name FROM HealthcareProviderNpi WHERE PRM_Active__c = true)
LIMIT 200

-- 3. Verify all Group NPIs resolve to HealthcareFacility:
SELECT Id, Name, PRM_NPI__c, Account.Name
FROM HealthcareFacility
WHERE PRM_NPI__c IN (/* paste Group NPIs from Col 31 */)
AND PRM_Active__c = true

-- 4. Check duplicate HCPF records would be created:
SELECT PractitionerId, AccountId, EffectiveFrom
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
AND PRM_Active__c = true
AND PractitionerId IN (
    SELECT HealthcareProvider.RelatedPersonId
    FROM HealthcareProviderNpi
    WHERE Name IN (/* paste 107 NPIs */)
)

-- 5. Verify taxonomy codes exist:
SELECT Id, PRM_TaxonomyCode__c, Name
FROM HealthcareProviderTaxonomy
WHERE PRM_TaxonomyCode__c IN (/* paste all NUCC codes from Cols 9-10 */)
AND RecordType.DeveloperName = 'PRM_TaxonomyCode'

-- 6. Verify specialty names exist:
SELECT Id, Name
FROM HealthcareSpecialty
WHERE Name IN (/* paste unique specialty names from Col 29 */)
```

---

## ⚠️ Known Gaps vs. Full PDM OmniScript

The batch job above covers the core record creation chain. The following advanced features of the PDM flow are **not included** (confirm with business if needed):

| Feature | PDM OmniScript Element | Batch Handling |
|---------|----------------------|----------------|
| Duplicate NPI validation | `CBAddPracDuplicateCheckSF` | ❌ Pre-flight query covers this instead |
| Office Hours assignment | `OfficeHoursStep` | ❌ Not in UPHS Excel — skip |
| Admitting Privileges | `CB_AdmittingPrivileges` | ❌ Not applicable for UPHS |
| IBC Professional Staff | `CB_IBCProfessionalStaff` | ❌ Not applicable for UPHS |
| COI (Change of Information) | `TermCOI` path | ❌ N/A — this is ADD, not update |
| Delegated Network cloning | `CB_DelegatedPPLTxNtwrk` | ❌ Not delegated (default false) |
| Kyruus provider directory sync | `EnableKyruus` | ❌ Separate automated sync post-load |
| LMS (Location Management) flag | `IsLMSPracticeLocation` | ❌ Not applicable for UPHS |
| Program Participation | `CB_AddProgramPartcipation` | ❌ Not in UPHS scope |
| Identifier/License records | `DRTIdentifier` | ❌ Not in UPHS scope |
| Cross-reference networks | `IPCrossReferencePDMManualUpdate` | ❌ Post-load network sync |

---

*End of UPHS Mass Load Solutions Document*
*Last Updated: Based on deep-dive of PRM_PDMManualUpdate_English OmniScript, PRMDRTransfromAddPracBlockPDM DataRaptor, PRMTransformPractitionerForExtract DataRaptor, PRM_PDMRecordsCreationParent → PRM_PDMRecordsCreationHelper Integration Procedures, and PRM_PDMRecordsPractitionerCreationHelper Integration Procedure SampleInputs.*
