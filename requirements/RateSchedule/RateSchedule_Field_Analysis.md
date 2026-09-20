# Rate Schedule — Field Analysis & Update Flow Documentation

**Project:** IBXQA / Provider Relationship Management (PRM)
**Date:** 2026-04-23
**Scope:** Full codebase scan covering objects, OmniScripts, DataRaptors, Integration Procedures, Apex, Layouts, and Flows

---

## 1. Overview

`PRM_RateSchedule__c` is a restricted picklist field that determines the rate schedule for **Capitated Programs**. It is maintained on three objects and is updated exclusively through OmniStudio-driven guided flows (OmniScripts + DataRaptors + Integration Procedures) and Apex utility classes. No standard Salesforce Flows or LWC/Aura components touch this field.

---

## 2. Objects That Maintain `PRM_RateSchedule__c`

| Object | Field Type | Controlling Field | Key Notes |
|--------|-----------|-------------------|-----------|
| **`PRM_Program__c`** | Restricted Picklist, history-tracked | `PRM_ProgramSubType__c` | ~60 picklist values filtered by sub-type (PCP, Lab, Radiology, PT, Vision, Dental codes). Description: *"Determines the Rate Schedule for Capitated Programs."* |
| **`PRM_ProgramParticipation__c`** | Restricted Picklist, history-tracked | None (unrestricted at field level) | Same ~60 values. Validation rule enforces it is required for CAP/CAPV capitated programs. |
| **`PRM_HealthcareFacilityBundle__c`** | Restricted Picklist, history-tracked | None | Subset of values — only Lab, Radiology, and Physical Therapy codes (bundle-centric service types). Description: *"This Field will store rate schedule of a bundle."* |

### 2.1 Picklist Value Categories (examples)

| Sub-Type Code | Sample Values |
|---------------|--------------|
| `PC` (PCP) | `100000/PA PCP`, `J10000/JEFFERSON`, `MER100` |
| `LB` (Lab) | Lab-specific codes |
| `RD` (Radiology) | Radiology codes |
| `PT` (Physical Therapy) | `PTH710`, `PTH714/CROZER/DE CNTY PT` |
| `TG` | `TDM001/Tandigm Enhanced` |
| `VI` (Vision) | `VIS001/Vision Vendor Schedule` |
| `DE` (Dental) | `DEN001/Dental` |

### 2.2 Validation Rule

**Rule Name:** `PRM_rateScheduledRequired` on `PRM_ProgramParticipation__c`

**Logic:** If all of the following are true → Error: *"Rate Schedule is required for Capitated Program Participation."*
- Related Program's `PRM_ProgramType__c` = `CAP` or `CAPV`
- `PRM_AgreementType__c` = `Capitated` or `Both`
- `PRM_RateSchedule__c` is blank

---

## 3. Guided Flows & OmniScripts

### 3.1 Write Paths (User Can Update Rate Schedule)

---

#### 3.1.1 `PRM_PDMManualChanges` — PDM Manual Changes

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_PDMManualChanges` |
| **Element Name** | `prgrmRateSchedule` |
| **Element Type** | Select (editable picklist) |
| **Parent Block** | `ProgramParticipation` (Edit Block) |
| **Option Source** | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` |
| **Show Condition** | Shown when `ShowProgramParticipationTable` is set |
| **Writes To** | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` (direct sObject mapping) |
| **DataRaptor (future time slots)** | `PRMDRUpdateProgPartProvFutureLocTimeSlot` |
| **Purpose** | Editing existing Program Participation data in the PDM Manual Changes process |

---

#### 3.1.2 `PRM_PDMManualUpdate` — PDM Manual Update (Practice Location Flow)

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_PDMManualUpdate` / `PRM_PDMManualUpdatePracticeLocation` |
| **Element Name** | `CapRateSchedule` |
| **Element Type** | Select (editable picklist) |
| **Parent Block** | `PracTxCapBlk` (Edit Block — Capitated Taxonomy block) |
| **Option Source** | `PRM_Program__c.PRM_RateSchedule__c` |
| **Controlling Field** | `ProgramSubTypeFormula` (mirrors `PRM_Program__c.PRM_ProgramSubType__c`) — filters picklist by sub-type |
| **Show Condition** | `CapSelect = true` AND `CapAgreementType = Capitated` OR `Both` |
| **Writes To** | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` |
| **DataRaptors** | `PRMDRTransProgramParticipation`, `PRMLoadManualUpdateProgamParticpations` |
| **Also Contains** | `ProgramRateSchedulePl` (read-only Text in `ProgramParticipationRemBlk`) — displays label via `PRMDrExtractProgParticipationForLoc` |

---

#### 3.1.3 `PRM_PracticeLocationBundles` — Practice Location Bundles (Create/Manage)

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_PracticeLocationBundles` |
| **Element Name** | `RateSchedule` |
| **Element Type** | Select (editable picklist) |
| **Parent Step** | `BundleCreation` |
| **Option Source** | `PRM_Program__c.PRM_RateSchedule__c` |
| **Controlling Field** | `ServiceTypeFormula` (mirrors `PRM_Program__c.PRM_ProgramSubType__c`) |
| **Show Condition** | Only when `BundleCreation:BundleType = Capitated Bundle` |
| **Writes To** | `PRM_HealthcareFacilityBundle__c.PRM_RateSchedule__c` |
| **Save Mechanism** | `SV_RecordsToCreate` element → `PRM_PLBundleRecordCreation` IP |
| **Also Contains** | `taxonomyRateSchedule` (read-only Text in `Taxonomy` Edit Block) — displays combined rate schedules for taxonomy/capitated program participation |

---

#### 3.1.4 `PRM_CreatePracticeLocationBundle` — Create Practice Location Bundle

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_CreatePracticeLocationBundle` |
| **Element Name** | `CreatePLBRateSchedule` (Formula combining `CreatePLBRateSchedule_Req` and `CreatePLBRateSchedule_NotReq`) |
| **Element Type** | Formula (hidden); two child Selects — one required, one optional |
| **Option Source** | `PRM_Program__c.PRM_RateSchedule__c` |
| **Writes To** | `PRM_HealthcareFacilityBundle__c.PRM_RateSchedule__c` |
| **Save Mechanism** | `SV_RecordsToCreate` → `PRM_PLBundleRecordCreation` IP |
| **Also Contains** | `taxonomyRateSchedule` (read-only) in the taxonomy block |

---

#### 3.1.5 `PRM_SelectPracticeLocationBundle` — Select Practice Location Bundle

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_SelectPracticeLocationBundle` |
| **Element Name** | `RateSchedule` (inside `SelectedPLBundleBlock`) |
| **Element Type** | Select (editable) |
| **Writes To** | Via `SV_PDMRecordsToCreate` — passed to IP for record creation |
| **Also Contains** | `RateScheduleRead` (read-only display of existing bundle's rate schedule) |

---

### 3.2 Read-Only Display Paths

---

#### 3.2.1 `PRM_ManualUpdatesQCReview3` — QC Review Screen

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_ManualUpdatesQCReview3` / `PRM_ManualUpdatesQC` |
| **Element Name** | `PP_RateSchedule__c` |
| **Element Type** | Text (read-only) |
| **Parent Block** | `ProgramParticipationBlock` (Edit Block) |
| **Data Source** | `PRMDRExtractPDMProgramParticipation` → reads `PRM_RateSchedule__c` → outputs as `PP_RateSchedule__c` |
| **Purpose** | QC reviewer sees the rate schedule label; cannot edit in this flow |

---

#### 3.2.2 `PRM_AddToExistingPracticeLocationBundle`

| Attribute | Detail |
|-----------|--------|
| **OmniScript** | `PRM_AddToExistingPracticeLocationBundle` |
| **Elements** | `RateSchedule` (existing bundle display), `RateScheduleCap` (in `TaxonomyCapBlk`) |
| **Element Type** | Read-only display |
| **Data Source** | `PRM_GetBundleDetailsService` Apex class |

---

## 4. DataRaptors

### 4.1 Extract (Read) DataRaptors

| DataRaptor | Source Field | Output Field | Used By |
|------------|-------------|--------------|---------|
| `PRMDRExtractPrgPartProvFutLocAssoc` | `PrgrmParticipation:PRM_RateSchedule__c` | `PrgrmParticipation:prgrmRateSchedule` | PDM Manual Changes OS |
| `PRMDrExtractProgParticipationForLoc` | `ProgramParticpation:PRM_RateSchedule__c` | `Program:ProgramRateSchedulePl` | PDM Manual Update OS (removal block display) |
| `PRMDRExtractPDMProgramParticipation` | `ProgramParticipationDetails:PRM_RateSchedule__c` | `ProgramParticipationDetails:PP_RateSchedule__c` | QC Review OS |
| `PRMGetPracticeLocationBundles` | `HCBundles:PRM_RateSchedule__c` | `HCFBundles:RateSchedule` | Bundle display to users |
| `PRMDRTurboHCFBundleAssociations` | `PRM_HealthcareFacilityBundle__r.PRM_RateSchedule__c` | — | Bundle association processing |
| `PRMDRPracticeTaxonomyCapitated` | `HealthCareTaxonomy:PPDetails:PRM_RateSchedule__c` | `HealthCareTaxonomy:taxonomyRateSchedule` | PracticeLocationBundles & CreatePracticeLocationBundle OS — calls `PRM_OmniUtils.fetchProgramParticipationRateScheduleLabels` to convert codes to labels |

### 4.2 Transform/Load (Write) DataRaptors

| DataRaptor | Input Field | Writes To | Used By |
|------------|------------|-----------|---------|
| `PRMDRTransProgramParticipation` | `NewProgParticipations:CapRateSchedule` | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` | PDM Manual Update OS |
| `PRMLoadManualUpdateProgamParticpations` | `NewProgramParts:CapRateSchedule` | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` | PDM Manual Update OS |
| `PRMDRUpdateProgPartProvFutureLocTimeSlot` | `ProgramParticipation:prgrmRateSchedule` | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` | PDM Manual Changes OS (future time slots) |
| `PRMDRTranformBundleLocData` | `getRelatedLocData:SelPracTaxonomiesStep:TaxonomyCapBlk:RateScheduleCap` | `Taxonomy:taxonomyRateSchedule` | Bundle location data intermediate transform |
| `PRMDRCreateBundleAssociationRecs` | `RateScheduleCap` (sample data) | Bundle association records | Bundle creation IPs |
| `PRMDRTransSelectTermPLBAssociations` | `PRM_RateSchedule__c` (via bundle relationship) | — | Bundle termination selection |
| `PRMDRValidateExistingBundle` | `RateScheduleCap` (sample data) | — | Bundle validation |

---

## 5. Integration Procedures

| Integration Procedure | Rate Schedule Role |
|-----------------------|--------------------|
| `PRM_ManageHCFBundleAndAssociations` (v1, v3, v4) | Passes `RateScheduleCap` through bundle association creation payload; writes to `PRM_HealthcareFacilityBundle__c` |
| `PRM_ManageHCFBundleAssParents` | Receives `RateSchedule` in `SelectedPLBundle` context |
| `PRM_PLBundleRecordCreation` | Receives `Bundle.RateSchedule`; **writes** `PRM_HealthcareFacilityBundle__c.PRM_RateSchedule__c` |
| `PRM_VerifyCreateBundleSelections` | Receives `BundleInfo.RateSchedule` for bundle selection validation |
| `PRM_VerifyBundleSelections` | Receives `RateSchedule` and `taxonomyRateSchedule` for bundle association verification |
| `PRM_FetchHCFAssociations` | Receives `RateSchedule` on `SelectedPLBundle` (sample: `"RateSchedule":"PTH710"`) |
| `PRM_FetchPDMSelectedFacilityDetails` (v5–v8) | Calls `PRM_OmniUtils.getProgramMappedData` to resolve `ProgramRateSchedulePl` API value → human label |
| `PRM_ManualChangePDAUpdates` (v4, v5) | Contains `prgrmRateSchedule` in sample data (PDM manual change for program participation) |

---

## 6. Apex Classes

### 6.1 `PRM_OmniUtils.cls`

Two methods handle Rate Schedule label resolution:

**`fetchProgramParticipationRateScheduleLabels(inputs, outMap)`**
- Entry points: called from OmniStudio via `methodName = 'fetchProgramParticipationRateScheduleLabels'` **and** as a DataRaptor formula function: `FUNCTION('PRM_OmniUtils','fetchProgramParticipationRateScheduleLabels', %HealthCareTaxonomy:PPDetails:Id%)`
- Queries `PRM_ProgramParticipation__c` using `toLabel(PRM_RateSchedule__c)` for given record IDs
- **Purpose:** Converts stored API value (e.g. `PTH714`) → display label (e.g. `CROZER/DE CNTY PT`)

**`getProgramMappedData(inputMap, outMap)`**
- Called via `methodName = 'getProgramMappedData'`
- Iterates `ProgramRecords` list; if a record has key `ProgramRateSchedulePl`, looks it up in the `PRM_ProgramParticipation__c.PRM_RateSchedule__c` picklist describe to convert API value → label
- Called by `PRM_FetchPDMSelectedFacilityDetails` IP (versions 5, 6, 7, 8)

---

### 6.2 `PRM_GetBundleDetailsService.cls`

- Queries `PRM_ProgramParticipation__c.PRM_RateSchedule__c` as part of a SOQL filtered by `PRM_HealthcareFacilityNetwork__c`
- Uses `Schema.DescribeFieldResult` on `PRM_ProgramParticipation__c.PRM_RateSchedule__c` to build a value-to-label map
- Returns the **label** as `RateScheduleCap` inside a `taxonomyCapBlk` map
- Data is consumed by `PRM_AddToExistingPracticeLocationBundle` OmniScript to display the rate schedule label in the taxonomy capitated block

---

### 6.3 `PRM_HCFBundleAssociationBatch.cls`

- Queries `PRM_HealthcareFacilityBundle__r.PRM_RateSchedule__c` through a relationship from `PRM_HealthcareFacilityBundleAssociation__c`
- Reads the bundle's rate schedule during batch processing of bundle association records

---

### 6.4 Test Classes

| Class | Usage |
|-------|-------|
| `PRM_TestDataFactory.cls` | Sets `PRM_RateSchedule__c = '100000'` in test data setup |
| `PRM_ProgramParticipationTriggerTest.cls` | Sets `PRM_RateSchedule__c = 'CHA200'` |
| `PRM_CrossRefBatchTest.cls` | Sets `PRM_RateSchedule__c` to `'100000'` or `'PTH714'`; tests `ProgramRateSchedulePl` key |
| `PRM_OmniUtilsTest.cls` | `testfetchProgramParticipationRateScheduleLabels` test method |
| `PRM_PracLocNetworkAutomationServiceTest.cls` | Sets `PRM_RateSchedule__c = '100000'` |
| `PRM_GetBundleDetailsServiceTest.cls` | Sets `PRM_RateSchedule__c = 'PTH714'` |

---

## 7. Standard Salesforce Flows & LWC

| Component Type | Rate Schedule Usage |
|----------------|---------------------|
| **Standard Flows (.flow-meta.xml)** | **None** — no standard flows reference rate schedule |
| **LWC / Aura Components** | **None** — no LWC or Aura components reference rate schedule |

All guided-flow functionality is handled entirely within OmniStudio (OmniScripts, DataRaptors, IPs) and Apex.

---

## 8. UI Surfaces (Layouts & Pages)

### Page Layouts

| Layout File | Presence |
|-------------|----------|
| `PRM_ProgramParticipation__c-Program Participation Layout.layout-meta.xml` | `PRM_RateSchedule__c` included |
| `PRM_HealthcareFacilityBundle__c-Practice Location Bundle Layout.layout-meta.xml` | `PRM_RateSchedule__c` included |

### Lightning Record Pages (FlexiPage)

| FlexiPage | Presence |
|-----------|----------|
| `PRM_ProgramParticipationRecordPage.flexipage-meta.xml` | `RecordPRM_RateSchedule_cField` — directly rendered as a field item |

### Permission Sets (Field-Level Security)

All key permission sets grant appropriate access:

| Permission Set | Access Level |
|----------------|-------------|
| `PRM_DataModifyAll` | Edit on all 3 objects |
| `PRM_DataViewAll` | Read on all 3 objects |
| `PRM_NetworkManagementQC` | Access on `PRM_ProgramParticipation__c` |
| `PRM_ProviderDataAdmin` | Access on all 3 objects |
| `PRM_CredentialingUser` | Access on all 3 objects |

### Object Translation Files

- `PRM_Program__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`
- `PRM_ProgramParticipation__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`
- `PRM_HealthcareFacilityBundle__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`

### Custom Metadata — Data Migration

`PRM_RateSchedule__c` is included in `PRM_DataMigrationSettings` for all three objects, confirming it is part of data migration/seeding processes.

---

## 9. End-to-End Update Flow Summary

### Path 1 — Updating Program Participation via PDM Manual Changes

```
User opens PRM_PDMManualChanges OmniScript
    └─► ProgramParticipation Edit Block
        └─► prgrmRateSchedule Select element (visible when ShowProgramParticipationTable is set)
            └─► Option source: PRM_ProgramParticipation__c.PRM_RateSchedule__c
                └─► WRITES PRM_ProgramParticipation__c.PRM_RateSchedule__c (direct sObject mapping)
                    └─► (Future time slots) PRMDRUpdateProgPartProvFutureLocTimeSlot DataRaptor
                            └─► WRITES PRM_ProgramParticipation__c.PRM_RateSchedule__c
```

### Path 2 — Adding/Updating Program Participation via PDM Manual Update

```
User opens PRM_PDMManualUpdate OmniScript
    └─► PracTxCapBlk Edit Block (CAP/CAPV programs)
        └─► CapRateSchedule Select element
            Conditions: CapSelect = true AND CapAgreementType = Capitated/Both
            Controlled by: ProgramSubTypeFormula
            └─► PRMDRTransProgramParticipation DataRaptor
                OR PRMLoadManualUpdateProgamParticpations DataRaptor
                    └─► WRITES PRM_ProgramParticipation__c.PRM_RateSchedule__c
                        └─► Validation: PRM_rateScheduledRequired enforces non-blank
```

### Path 3 — Creating a Capitated Practice Location Bundle

```
User opens PRM_PracticeLocationBundles or PRM_CreatePracticeLocationBundle OmniScript
    └─► BundleCreation Step
        └─► RateSchedule (or CreatePLBRateSchedule) Select element
            Condition: BundleType = Capitated Bundle
            Controlled by: ServiceTypeFormula
            └─► SV_RecordsToCreate element
                └─► PRM_PLBundleRecordCreation Integration Procedure
                        └─► WRITES PRM_HealthcareFacilityBundle__c.PRM_RateSchedule__c
```

### Path 4 — Selecting a Practice Location Bundle

```
User opens PRM_SelectPracticeLocationBundle OmniScript
    └─► SelectedPLBundleBlock
        └─► RateSchedule Select element
            └─► SV_PDMRecordsToCreate
                └─► IP for record creation
                        └─► PRM_HealthcareFacilityBundle__c.PRM_RateSchedule__c (or PRM_ProgramParticipation__c)
```

### Path 5 — QC Review Display (Read-Only)

```
User opens PRM_ManualUpdatesQCReview3 OmniScript
    └─► ProgramParticipationBlock
        └─► PP_RateSchedule__c Text element (read-only)
            └─► PRMDRExtractPDMProgramParticipation DataRaptor
                    reads PRM_RateSchedule__c → outputs PP_RateSchedule__c
                        └─► QC reviewer sees label — cannot edit
```

### Path 6 — Taxonomy Rate Schedule Display (Read-Only, Bundle Association Flows)

```
PRM_PracticeLocationBundles / PRM_CreatePracticeLocationBundle OmniScript
    └─► Taxonomy Edit Block
        └─► taxonomyRateSchedule Text element (read-only)
            └─► PRMDRPracticeTaxonomyCapitated DataRaptor
                    reads all PRM_ProgramParticipation__c.PRM_RateSchedule__c for taxonomy
                    joins values with commas
                    calls PRM_OmniUtils.fetchProgramParticipationRateScheduleLabels()
                        └─► Returns human-readable combined label

PRM_AddToExistingPracticeLocationBundle OmniScript
    └─► TaxonomyCapBlk
        └─► RateScheduleCap Text element (read-only)
            └─► PRM_GetBundleDetailsService Apex class
                    queries PRM_ProgramParticipation__c.PRM_RateSchedule__c
                    uses Schema.DescribeFieldResult to build value → label map
                        └─► Returns RateScheduleCap label
```

---

## 10. Component Inventory Summary

| Category | Count | Components |
|----------|-------|-----------|
| Objects | 3 | `PRM_Program__c`, `PRM_ProgramParticipation__c`, `PRM_HealthcareFacilityBundle__c` |
| OmniScripts (write) | 5 | `PRM_PDMManualChanges`, `PRM_PDMManualUpdate`, `PRM_PracticeLocationBundles`, `PRM_CreatePracticeLocationBundle`, `PRM_SelectPracticeLocationBundle` |
| OmniScripts (read-only display) | 2 | `PRM_ManualUpdatesQCReview3`, `PRM_AddToExistingPracticeLocationBundle` |
| DataRaptors (read) | 6 | See Section 4.1 |
| DataRaptors (write) | 7 | See Section 4.2 |
| Integration Procedures | 8 | See Section 5 |
| Apex Classes (production) | 3 | `PRM_OmniUtils`, `PRM_GetBundleDetailsService`, `PRM_HCFBundleAssociationBatch` |
| Validation Rules | 1 | `PRM_rateScheduledRequired` on `PRM_ProgramParticipation__c` |
| Page Layouts | 2 | Program Participation Layout, Practice Location Bundle Layout |
| Lightning Record Pages | 1 | `PRM_ProgramParticipationRecordPage` |
| Standard Flows | 0 | N/A |
| LWC/Aura Components | 0 | N/A |
