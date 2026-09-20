# PNM Reinstate Practitioner — Apex Service Architecture

## IP Audit, Reusability Matrix & New Service Blueprint (Reinstate Flow Family)

> **Companion docs**
> - `PNM_Apex_Service_Architecture.md` — generic SOA framework (Dispatcher / BaseService / DMLUtil / Selectors / Async).
> - `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` — Practitioner Participation Form (the proven model).
> - `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` — Initial Cred PDA Review.
> - `PNM_OffCycle_Process_Apex_Service_Architecture.md` — Off Cycle submit.
> - `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md` — Off Cycle post-committee review.
>
> This document covers the **Reinstate** family — the three guided flows that bring a previously-terminated provider, practice location, or vendor account **back to active**. Unlike the Off Cycle flow which handles *changes* to active providers, the Reinstate flows operate on **inactive** records and must un-set termination flags / dates across a large surface of related entities.
>
> The Reinstate family is unique because **part of it is already in Apex** — `PRM_ReinstateVendorAccountBatch` + `PRM_ReinstateUtils` + `PRM_ReinstateCallable` are real precedents for the very pattern we are promoting (Callable + Batch + Helper + Wrapper). The migration is therefore as much **standardisation** (fold the existing one-offs into the generic framework) as it is **net-new work**.

---

## 0. TL;DR

| | Par Form (creation) | Off Cycle (submit) | **Reinstate (this doc)** |
|---|---|---|---|
| Trigger | New practitioner / new group | Mid-cycle change on active provider | **An inactive practitioner / location / vendor needs to be brought back active** |
| OmniScripts | `PRM_ParForm_English` | `PRM_OffCycleCredentialing_English` | **Three** OmniScripts: <br>• `PRM_PractitionerReinstateForm_English` (v9) <br>• `PRM_PracticeLocationReinstate_English` (v6) <br>• `PRM_PractitionerReinstateVendorForm_English` (v5) <br>+ helper OS `PRM_ReinstateLinkExistingPractitioner_English` |
| Entry IPs (container + orchestrator) | 2 IPs | 6 IPs | **6 IPs across 3 flows** |
| Heaviest IP | `PRM_CreatePractitionerAddressRecords` (80+) | `PRM_OffCycleRecordCreation` (40) | **`PRM_ReinstateRecordCreation`** (**72 elements** — the second-heaviest IP in the whole codebase, just behind the Par Form address IP) |
| DML pattern | Mostly INSERT | INSERT + UPDATE | **Almost entirely UPDATE** — flipping `IsActive`, `EffectiveTo=NULL`, `Pending=FALSE`, etc. across 8–10 SObjects per practitioner |
| Variant axis | Net-new practitioner type | `OffCycleRequestType` picklist | **`ReinstateScope`** = Practitioner / PracticeLocation / VendorAccount <br>**× `Update`** = "Yes" / "No" picklist per sub-entity (Practice-Practitioner, Board Cert, Taxonomy, Info-Code, Identifier) <br>**× Volume threshold** (Vendor: `PracticeLocationCount > 10` → already-existing batch path) |
| Existing Apex precedent | none | none | **`PRM_ReinstateVendorAccountBatch` + Helper + Wrapper + Callable + Utils** already exist for the > 10 location case — proves the pattern works in this org |
| Reusable framework code | — | ~75% | **~80%** — Address / Case / Identifier / Note services + the existing Batch precedent + every selector exists |
| Net-new services needed | — | 13 | **6** new Reinstate-specific services + **2** transformers + **1** new selector |

---

## 1. Current State: Complete IP Chain Audit

### 1.1 The Reinstate Flow Family — three parallel chains

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW A — Practitioner Reinstate (most common, heaviest)                    │
│                                                                             │
│  OmniScript:  PRM_PractitionerReinstateForm_English  (active v9)            │
│       │                                                                     │
│       │ user selects practitioner, picks which sub-entities to reinstate    │
│       │ (Practice-Practitioner, Board Cert, Taxonomy, InfoCode, Identifier) │
│       │ with per-row "Update = Yes/No" picklist                             │
│       ▼                                                                     │
│  IP: PRM_ReinstateRecordCreationParent  (4 elt — Container, TryCatch)       │
│  IP: PRM_ReinstateRecordCreation        (**72 elements**)                    │
│       │                                                                     │
│       ├─ Case + CaseManager + Note (5 elt)                                  │
│       ├─ Practitioner Account / Taxonomy / Identifier / NPI extract (4 elt) │
│       ├─ HFN Reinstate + RAs to transform records (4 elt)                   │
│       ├─ Existing PracticeLocation? branch (LoadReinstatePractPracLoc /     │
│       │  CreatePracticeToPractitioner / DRPostHealthCareFacilityNetwork)    │
│       ├─ 5 × LoopBlock+3-conditional pattern (~45 elt total):                │
│       │      • PractionerLoopBlock         — Yes / No / False               │
│       │      • PracticeToPractitionerLoop  — Yes / No / False               │
│       │      • BoardCertificationLoop      — Yes / No / False               │
│       │      • HealthCareTaxonomyAssignmentLoop  — Yes / No / False         │
│       │      • InfocodeAssignmentLoop      — Yes / No / False               │
│       │      • IdentifierAssignmentLoopBlock  — Yes / No / False            │
│       ├─ 8 × DR-Post UPDATE bundles (the actual writes):                    │
│       │      PRMDRHealthcarefaciityUpdate                                   │
│       │      PRMDRPracticeLocationUpdate                                    │
│       │      PRMDRPracticeToPractitionerUpdate                              │
│       │      PRMDRPracticeLocationTaxNetworkUpdate                          │
│       │      PRMDRPracticeLocationAPUpdate                                  │
│       │      PRMDRPractitionerAccountUpdate                                 │
│       │      PRMDRIdentifierUpdate                                          │
│       │      PRMReinstateBoardCertsUpdate                                   │
│       │      PRMReinstateInfoCodeAssignmentUpdate                           │
│       │      PRMReinstateHealthcareProviderTaxonomyRecordUpdate             │
│       ├─ CaseDataManager flag stamp (PRMDRPCaseDataManager)                 │
│       └─ Response                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW B — Practice Location Reinstate (small, location-only)                │
│                                                                             │
│  OmniScript:  PRM_PracticeLocationReinstate_English  (active v6)            │
│       ▼                                                                     │
│  IP: PRM_ReinstatePracticeLocationParent  (Container)                       │
│  IP: PRM_ReinstatePracticeLocation        (**12 elements**)                  │
│       ├─ SV_ReinstateData                                                   │
│       ├─ ExtractPractitionerPracLocData     (DR Extract)                    │
│       ├─ TransformPracLocAssociationForReinstate  (DR Transform)            │
│       ├─ TransformPracLocDataForReinstate         (DR Transform)            │
│       ├─ CreateCaseNCaseManager   (DR Post — single call)                   │
│       ├─ RA_CreateNote            (Remote Action: PRM_OmniUtils)            │
│       ├─ UpdatePracticeLocationAddress              (DR Post)               │
│       ├─ UpdateNPIRelatedToPracLoc                   (DR Post)              │
│       ├─ UpdatePracLocSummaryInfoCodeProgPartIP      (DR Post)              │
│       ├─ UpdateHcPFacilityAssociation                (DR Post)              │
│       ├─ CaseDataManagerCaseManager                  (DR Post)              │
│       └─ ResponseForResinstate                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW C — Vendor Account Reinstate (already has Apex batch precedent!)      │
│                                                                             │
│  OmniScript:  PRM_PractitionerReinstateVendorForm_English  (active v5)      │
│       ▼                                                                     │
│  IP: PRM_PractitionerReinstateVendorParent  (Container)                     │
│  IP: PRM_PractitionerReinstateVendorUpdate (**22 elements**)                 │
│       ├─ LA_PracticeLocation / SetValues  (filter selected locations)       │
│       ├─ DREHcProviderIdentifier  (DR Extract — identifiers)                │
│       ├─ DRPCaseManagerCaseAccount  (DR Post — create case + case mgr)      │
│       ├─ DRPHcProviderIdentifier    (DR Post — reactivate identifiers)      │
│       ├─ DRPInfoCodeProgPart        (DR Post — reactivate info codes)       │
│       ├─ RACreateNote               (Remote Action: PRM_OmniUtils)          │
│       ├─ CB_PracticeLocationExist  (Conditional Block)                       │
│       │     ├─ DREFacilityLocationAddress                                   │
│       │     ├─ DREPracLocSummaryInfoCodeProgPart                            │
│       │     ├─ DREHcPFacilityAssociation                                    │
│       │     └─ LA_UniqueHcProviderNPI                                       │
│       ├─ CB_PracticeLocationLessThanEqualTo10  (sync path — DR Posts)       │
│       │     ├─ DRPFacilityLocationAddress                                   │
│       │     ├─ DRPHealthcareProviderNPI                                     │
│       │     ├─ DRPPracLocSummaryInfoCodeProgPart                            │
│       │     ├─ DRPHcPFacilityAssociation                                    │
│       │     └─ DRPCaseDataManagerCaseManager                                │
│       ├─ CB_PracticeLocationGreaterThan10  (**ASYNC PATH — already Apex!**)  │
│       │     ├─ Set_BatchData       (Set Values)                             │
│       │     └─ RA_CallBatch        (Remote Action:                          │
│       │                              remoteClass  = PRM_ReinstateCallable    │
│       │                              remoteMethod = ReinstateVendorAccountBatch│
│       │                              database.executeBatch(batch, 5))        │
│       └─ ResponseAction                                                     │
└─────────────────────────────────────────────────────────────────────────────┘

Existing Apex (precedent for the migration pattern)
──────────────────────────────────────────────────────────────────────────────
• PRM_ReinstateCallable                  (Callable bridge — receives RA call)
• PRM_ReinstateVendorAccountBatch        (Batchable<sObject>, Database.Stateful)
• PRM_ReinstateVendorAccountBatchHelper  (Helper — initalizeValues, queryRecords,
                                          updateFacilityAndItsRelatedData, finish)
• PRM_ReinstateUtils                     (@AuraEnabled selector for the LWC
                                          prmReinstatePractitionerPracticeLocation)
• PRM_ReinstatePracticeLocationWrapper   (DTO)
• LWC prmReinstatePractitionerPracticeLocation
  + helper IP  PRM_SetSelectAllReInstate (small bulk-select helper)
  + validation IP  PRM_ValidateDuplicateTaxonomyReinstate
```

### 1.2 Element Counts

| IP / Class | Elements / LoC | Active Version | Type |
|---|---:|---|---|
| `PRM_ReinstateRecordCreationParent` | 4 elt | v2 | Container (TryCatch) |
| **`PRM_ReinstateRecordCreation`** | **72 elt** | v3 | Orchestrator — practitioner-level (the heavy IP) |
| `PRM_ReinstatePracticeLocationParent` | 4 elt | v1 | Container |
| `PRM_ReinstatePracticeLocation` | 12 elt | v8 | Orchestrator — location-level |
| `PRM_PractitionerReinstateVendorParent` | 4 elt | v1 | Container |
| `PRM_PractitionerReinstateVendorUpdate` | 22 elt | v6 | Orchestrator — vendor-level |
| `PRM_ValidateDuplicateTaxonomyReinstate` | ~3 elt | v1 | Validation helper IP |
| `PRM_SetSelectAllReInstate` | ~2 elt | v1 | Bulk-select helper IP |
| `PRM_ReinstateCallable` (Apex) | ~40 LoC | — | Existing Callable for batch |
| `PRM_ReinstateVendorAccountBatch` + Helper (Apex) | ~600 LoC | — | Existing Batch class |
| `PRM_ReinstateUtils` (Apex) | ~120 LoC | — | Existing read-side @AuraEnabled |
| **Total OmniStudio elements** | **~123** | | |

### 1.3 Per-element catalog — FLOW A `PRM_ReinstateRecordCreation` (72 elt)

The 72 elements decompose into **7 functional groups**. The looping/conditional-set-value pattern accounts for ~45 of the 72.

#### Group 1 — Case / CaseManager / Notes (5 elt)
| # | Element | Type | Bundle / RA |
|---|---|---|---|
| 1 | `ExtractCaseManagerDetails` | DR Extract | `PRMFetchCaseManagerReinstate` |
| 2 | `PRMLoadCaseCaseManager` | DR Post | `PRMLoadOffCycleCaseCaseMgrReinstate` |
| 3 | `SetCaseManagerId` / `SVEntityId` / `SVNotes` | Set Values × 3 | — |
| 4 | `CreateNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` |

#### Group 2 — Practitioner-level fetch / transforms (4 elt)
| # | Element | Type | Bundle / RA |
|---|---|---|---|
| 5 | `PRMUpdateHealthCareDetails` | DR Post | `PRMUpdateHealthCareDetailsReinstate` |
| 6 | `PRMDRExtractHpf` | DR Extract | `PRMDRExtractHPFReinstate` |
| 7 | `SetInfoCodeAssignmentToList` | Set Values | — |
| 8 | `ExistingPracticeLocationAdded` | Set Values / CB | — |

#### Group 3 — Network / Taxonomy transformation (4 elt)
| # | Element | Type | Bundle / RA |
|---|---|---|---|
| 9 | `RAToTransformNetworkTaxonomyRecords` | Remote Action | (PRM_OmniUtils — taxonomy de-merge) |
| 10 | `RAToTranformPractPracRecords` | Remote Action | (PRM_OmniUtils — pract-prac de-merge) |
| 11 | `LoadReinstatePractPracLoc` | DR Post | `PRMLoadReinstatePractPracLoc` |
| 12 | `CreatePracticeToPractitioner` | DR Post | (creates new HCPF if needed) |
| 13 | `DRPostHealthCareFacilityNetwork` | DR Post | `PRMDRHCFacilityNetworkForReInstate` |

#### Group 4 — The 5 × Loop / 3-conditional / 3-setvalue pattern (~45 elt)

This is where most of the bloat lives. For each of the 5 sub-entities, the IP loops over the user's UI selection and routes each row into one of three "buckets" based on two flags: `ReinstateAsYes/Update=Yes`, `ReinstateAsYes/Update=No`, `ReinstateAsFalse`. The buckets are then fed to the matching update DRs (group 6).

| Sub-entity | Loop element | Branch elements (3 each) |
|---|---|---|
| **Practitioner-level Account record** | `PractionerLoopBlock` | `CheckPractitionerReinstateAsYesAndUpdateAsYes` + `SetReinstateValueAsYes`, `CheckPractitionerReinstateAsYesAndUpdateAsNo` + `SetReinstateValueAsNo`, `CheckPractitionerReinstateAsFalse` + `SetReinstateValueFalse` |
| **Practice-to-Practitioner (HCPF)** | `PracticeToPractitionerLoop` (with `GetPracticeDetails` + `PRMDRFetchPracticeToPractionerDetails` + `SetPractitionerLocationList`) | `PracUpdateYes` + `PracSVUpdateYes`, `PracUpdateNo` + `PracSVUpdateNo` (and a False branch) |
| **Board Certification** | `BoardCertificationLoop` | `BoardCertificationReinstateAsTrueUpdateAsYes` + `SetBCReinstateAsTrueUpdateAsYes`, `BoardCertificationReinstateAsTrueUpdateAsNo` + `SetBCReinstateAsTrueUpdateAsNo`, `BoardCertificationReinstateAsFalse` + `SetBcReinstateAsFalse` |
| **HealthCare Taxonomy** | `HealthCareTaxonomyAssignmentLoop` | `CheckHealthCareTaxonomyReinstateandUpdateAsTrue` + `SetValuesforReinstateTrueandYes`, `CheckHealthCareTaxonomyReinstateasNo` + `SetHTValueForReinstateTrueandUpdateNo`, `CheckHealthCareReinstateAsFalse` + `SetValuesForHTReinstateFalse` |
| **InfoCode Assignment** | `InfocodeAssignmentLoop` | `CheckReinstateandUpdateEffectiveDatesAsTrue` + `SetValues6`, `CheckReinstateandUpdateEffectiveDatesAsNo` + `SetInfoCodeValues`, `CheckReinstateAsFalse` + `SetInfocodeReinstateValuesAsFalse` |
| **Identifier** | `IdentifierAssignmentLoopBlock` | `SetIdentifierReinstateasTrueandUpdateAsYes` + `SetIdentifierReinstateasTrueandUpdateYes`, `SetIdentifierReinstateasTrueandUpdateAsNo` + `SetIdentifierReinstateasTrueandUpdateNo`, `SetIdentifierReinstateasFalse` + `SetIdentifierReinstateasFalseValue` |

> **Insight**: In Apex this entire pattern is **one** method per sub-entity using `Map<String, List<…>>` partitioning — no loops, no Set Values, no Conditional Blocks. It collapses ~45 elements into ~6 short methods (~150 lines total).

#### Group 5 — DR Post UPDATE bundles (8 elt — the actual writes)
| # | Element | Type | Bundle | Writes |
|---|---|---|---|---|
| 60 | `PRMDRHealthcarefaciityUpdate` | DR Post | `PRMReinstatehealthcareFacilityUpdate` | `HealthcareFacility` (PRM_Active, EffectiveTo, IsActive) |
| 61 | `PRMDRPracticeLocationUpdate` | DR Post | `PRMDRTPracLocDataForReinstate` (counterpart) | `Location` / Practice Location |
| 62 | `PRMDRPracticeToPractitionerUpdate` | DR Post | `PRMDRTPracLocAssociationReinstate` (counterpart) | `HealthcarePractitionerFacility` |
| 63 | `PRMDRPracticeLocationTaxNetworkUpdate` | DR Post | `PRMDRHCFacilityNetworkForReInstate` | `HealthcareFacilityNetwork` (reactivate) |
| 64 | `PRMDRPracticeLocationAPUpdate` | DR Post | (Practice-loc-AP — assistive aid / accommodation) | `PRM_ProviderFeature__c` / related |
| 65 | `PRMDRPractitionerAccountUpdate` | DR Post | (Account update) | `Account` (PersonAccount practitioner — IsActive, EffectiveTo, PRM_Active__c) |
| 66 | `PRMDRIdentifierUpdate` | DR Post | `PRMReinstateIdentifierUpdate` (or equivalent) | `Identifier__c` |
| 67 | `PRMReinstateBoardCertsUpdate` | DR Post | `PRMReinstateBoardCertsUpdate` | `BoardCertification__c` |
| 68 | `PRMReinstateInfoCodeAssignmentUpdate` | DR Post | `PRMReinstateInfoCodeAssignmentUpdate` | `PRM_InfoCodeAssignment__c` |
| 69 | `PRMReinstateHealthcareProviderTaxonomyRecordUpdate` | DR Post | `PRMReinstateHealthcareProviderTaxonomyRecordUpdate` | `HealthcareProviderTaxonomy` |

#### Group 6 — CaseManager flag stamping + Response (3 elt)
| # | Element | Type | Bundle |
|---|---|---|---|
| 70 | `DRToExtractDataFromCaseManagerToUpdateReInstate` | DR Extract | `PRMDRToExtractDataFromCaseManagerToUpdateReInstate` |
| 71 | `DRToUpdateRecordsAfterReInstate` | DR Post | `PRMDRToUpdateRecordsAfterReInstate` |
| 72 | `PRMDRPCaseDataManager` | DR Post | (CaseDataManager flag stamp on IndividualApplication) |

### 1.4 Per-element catalog — FLOW B `PRM_ReinstatePracticeLocation` (12 elt)

| # | Element | Type | Bundle / RA | Notes |
|---|---|---|---|---|
| 1 | `SV_ReinstateData` | Set Values | — | shape input |
| 2 | `ExtractPractitionerPracLocData` | DR Extract | `PRMGetReInstateData` | loads HCF/Loc/Address/HCPF for the location |
| 3 | `TransformPracLocAssociationForReinstate` | DR Transform | `PRMDRTPracLocAssociationReinstate` | shapes HCPF UPDATE payload |
| 4 | `TransformPracLocDataForReinstate` | DR Transform | `PRMDRTPracLocDataForReinstate` | shapes Location UPDATE payload |
| 5 | `CreateCaseNCaseManager` | DR Post | `PRMLoadOffCycleCaseCaseMgrReinstate` | Case + IndividualApplication |
| 6 | `RA_CreateNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` | case note |
| 7 | `UpdatePracticeLocationAddress` | DR Post | `PRMReinstatehealthcareFacilityUpdate` (location-scoped) | reactivate Address rows |
| 8 | `UpdateNPIRelatedToPracLoc` | DR Post | (NPI history reactivate) | LocationNPIHistory |
| 9 | `UpdatePracLocSummaryInfoCodeProgPartIP` | DR Post | `PRMReinstateInfoCodeAssignmentUpdate` (loc-scoped) | InfoCode |
| 10 | `UpdateHcPFacilityAssociation` | DR Post | (uses TransformPracLocAssociationForReinstate output) | HCPF reactivate |
| 11 | `CaseDataManagerCaseManager` | DR Post | (CaseDataManager flag stamp) | IndividualApplication flags |
| 12 | `ResponseForResinstate` | Response | — | final OS response |

### 1.5 Per-element catalog — FLOW C `PRM_PractitionerReinstateVendorUpdate` (22 elt)

| # | Element | Type | Bundle / RA | Cond | Notes |
|---|---|---|---|---|---|
| 1 | `LA_PracticeLocation` | List Action | — | | filters selected `ReinstatedPracticeLocation` |
| 2 | `SetValues` | Set Values | — | | builds `ReinstatedPracticeLocation` list |
| 3 | `DREHcProviderIdentifier` | DR Extract | `PRMDREHcProviderIdentifier` | | identifiers for the vendor |
| 4 | `DRPCaseManagerCaseAccount` | DR Post | `PRMDRPCaseManagerCaseAccount` | | Case + IndividualApplication + Account reactivate |
| 5 | `DRPHcProviderIdentifier` | DR Post | `PRMDRPHcProviderIdentifier` | | reactivate Identifier__c rows |
| 6 | `DRPInfoCodeProgPart` | DR Post | `PRMDRPInfoCodeProgPart` | | reactivate InfoCodeAssignment |
| 7 | `RACreateNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` | | case note |
| 8 | `CB_PracticeLocationExist` | Conditional Block | — | `ISNOTBLANK(%SetValues:ReinstatedPracticeLocation%)` | only if locations selected |
| 8.1 | `DREFacilityLocationAddress` | DR Extract | — | | existing HCF/Loc/Address for the vendor |
| 8.2 | `DREPracLocSummaryInfoCodeProgPart` | DR Extract | — | | existing InfoCode per loc |
| 8.3 | `DREHcPFacilityAssociation` | DR Extract | — | | existing HCPF |
| 8.4 | `LA_UniqueHcProviderNPI` | List Action | — | | dedup NPI |
| 9 | `CB_PracticeLocationLessThanEqualTo10` | Conditional Block | — | `%RecordToUpsert:PracticeLocationCount% <= 10` | **SYNC path** |
| 9.1 | `DRPFacilityLocationAddress` | DR Post | `PRMReinstatehealthcareFacilityUpdate` (vendor-scoped) | | HCF/Loc/Addr reactivate |
| 9.2 | `DRPHealthcareProviderNPI` | DR Post | (NPI reactivate) | | HCPNPI reactivate |
| 9.3 | `DRPPracLocSummaryInfoCodeProgPart` | DR Post | | | InfoCode per loc reactivate |
| 9.4 | `DRPHcPFacilityAssociation` | DR Post | | | HCPF reactivate |
| 9.5 | `DRPCaseDataManagerCaseManager` | DR Post | | | flag stamp |
| 10 | `CB_PracticeLocationGreaterThan10` | Conditional Block | — | `ISNOTBLANK(...) && PracticeLocationCount > 10` | **ASYNC path — already Apex** |
| 10.1 | `Set_BatchData` | Set Values | — | | serialises payload for batch |
| 10.2 | `RA_CallBatch` | Remote Action | `PRM_ReinstateCallable.ReinstateVendorAccountBatch` | | `Database.executeBatch(new PRM_ReinstateVendorAccountBatch(input), 5)` |
| 11 | `ResponseAction` | Response | — | | final response |

---

## 2. Records Created / Updated by the Reinstate Family

Reinstate is **predominantly an UPDATE** workload — the records already exist, but with `IsActive=FALSE` / `EffectiveTo=<dateInPast>` / `PRM_Active__c=FALSE` flags. The job is to un-set those, fill in `ReinstatementDate__c`-style audit columns, and re-open the period rows. A handful of INSERTs happen only when the user adds a **new** sub-row during the form (e.g. a new HCPF for a previously-detached practice location).

### 2.1 INSERT inventory (worst case across all 3 flows)

| # | SObject | Source element | Flow(s) | Notes |
|---|---|---|---|---|
| 1 | `Case` | `PRMLoadCaseCaseManager` / `CreateCaseNCaseManager` / `DRPCaseManagerCaseAccount` | A / B / C | 1 per submit (RecordType = Reinstatement) |
| 2 | `IndividualApplication` (CaseManager) | same DR as above | A / B / C | 1 per submit |
| 3 | `ContentNote` | `CreateNote` / `RA_CreateNote` / `RACreateNote` | A / B / C | 0..1 (optional reviewer note) |
| 4 | `HealthcarePractitionerFacility` (new) | `CreatePracticeToPractitioner` | A | 0..N — only when user attached a previously-detached location |
| 5 | `HealthcareFacilityNetwork` (new) | `DRPostHealthCareFacilityNetwork` | A | 0..N — only when reinstating across a new network |
| 6 | `LocationNPIHistory` (new period) | `UpdateNPIRelatedToPracLoc` | B | 0..N — opens a new period when the old one had EndDate |

### 2.2 UPDATE inventory (the bulk)

For **Flow A — Practitioner Reinstate** (worst case, fully-elected reinstate):

| # | SObject | Source DR | Volume per submit | Fields touched |
|---|---|---|---:|---|
| 1 | `Account` (PersonAccount — practitioner) | `PRMDRPractitionerAccountUpdate` | 1 | `IsActive=TRUE`, `PRM_Active__c=TRUE`, `EffectiveTo=NULL`, `PRM_ReinstateDate__c=TODAY()` |
| 2 | `HealthcareFacility` | `PRMDRHealthcarefaciityUpdate` | 1..N | `PRM_Active__c=TRUE`, `EffectiveTo=NULL` |
| 3 | `Location` / Practice Location | `PRMDRPracticeLocationUpdate` | 1..N | `IsActive=TRUE`, `EffectiveTo=NULL` |
| 4 | `HealthcarePractitionerFacility` (HCPF) | `PRMDRPracticeToPractitionerUpdate` | 1..N | per-row `Update` flag → either reactivate or skip |
| 5 | `HealthcareFacilityNetwork` (HCFN) | `PRMDRPracticeLocationTaxNetworkUpdate` | 1..N | reactivate per-network row |
| 6 | `PRM_ProviderFeature__c` | `PRMDRPracticeLocationAPUpdate` | 0..N | assistive-aid / accommodation reactivate |
| 7 | `Identifier__c` | `PRMDRIdentifierUpdate` | 1..N | reactivate (NPI / TaxId / DEA / etc.) per `Update` flag |
| 8 | `BoardCertification__c` | `PRMReinstateBoardCertsUpdate` | 0..N | reactivate or extend `EffectiveTo` |
| 9 | `PRM_InfoCodeAssignment__c` | `PRMReinstateInfoCodeAssignmentUpdate` | 0..N | reactivate / re-effectuate |
| 10 | `HealthcareProviderTaxonomy` | `PRMReinstateHealthcareProviderTaxonomyRecordUpdate` | 1..N | reactivate per `Update` flag |
| 11 | `IndividualApplication` (CaseManager) | `DRToUpdateRecordsAfterReInstate` + `PRMDRPCaseDataManager` | 1 | CaseDataManager flags stamped (Account / HCF / HCPF / HCFN / HPT / Identifier / BoardCert / InfoCode / PracticeLocation / ProviderFeature) |

Per-submit row totals (Practitioner flow): worst case **~150–300 rows** when a long-tenured practitioner with many locations / networks / specialties is reinstated wholesale. The Vendor flow's `>10 locations` already exceeds this — which is exactly why `PRM_ReinstateVendorAccountBatch` exists.

### 2.3 Variant axis — `ReinstateScope × per-row Update flag`

| Scope | Determined by | Per-row variants |
|---|---|---|
| **Practitioner** | OS = `PRM_PractitionerReinstateForm_English` | user picks **Update = Yes/No** independently on each row of: Practice-Practitioner, BoardCert, Taxonomy, InfoCode, Identifier (each row also has a `ReinstateAs` flag — True/False). Three buckets: `True+Yes`, `True+No`, `False` |
| **Practice Location** | OS = `PRM_PracticeLocationReinstate_English` | single-scope; all related Address / NPI / InfoCode / HCPF rows reactivate together |
| **Vendor** | OS = `PRM_PractitionerReinstateVendorForm_English` | `PracticeLocationCount ≤ 10` → sync; `> 10` → async batch (already in Apex) |

---

## 3. Target Apex Service Architecture (Reinstate Family)

### 3.1 Layered Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  OmniScripts (kept):                                                         │
│    PRM_PractitionerReinstateForm_English                                     │
│    PRM_PracticeLocationReinstate_English                                     │
│    PRM_PractitionerReinstateVendorForm_English                               │
│    PRM_ReinstateLinkExistingPractitioner_English  (helper OS)                │
│                                                                              │
│  Thin-wrapper IPs (3 elements each — SetValues → ServiceInvoker → Response): │
│    PRM_ReinstateRecordCreationParent                                         │
│    PRM_ReinstatePracticeLocationParent                                       │
│    PRM_PractitionerReinstateVendorParent                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                          │  vlocity_ins.VlocityOpenInterface2.invokeMethod()
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CONTROLLER LAYER  (REUSE — already in framework)                            │
│    PRM_ServiceDispatcher    PRM_BaseService                                  │
│    PRM_ServiceRequest       PRM_ServiceResponse                              │
│                                                                              │
│  Three new service names registered:                                         │
│    "ReinstatePractitioner"     → PRM_ReinstatePractitionerService            │
│    "ReinstatePracticeLocation" → PRM_ReinstatePracticeLocationService        │
│    "ReinstateVendorAccount"    → PRM_ReinstateVendorAccountService           │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER (NEW — composed mostly of REUSE)                        │
│                                                                              │
│   PRM_ReinstatePractitionerService          (NEW — replaces the 72-elt IP)  │
│     ├── PRM_ReinstateRowPartitioner         (NEW — replaces the 5×loop/CB)  │
│     ├── PRM_PractitionerAccountReactivator  (NEW)                            │
│     ├── PRM_HCPFReactivator                 (NEW)                            │
│     ├── PRM_HCFNReactivator                 (NEW)                            │
│     ├── PRM_BoardCertReactivator            (NEW small)                      │
│     ├── PRM_TaxonomyReactivator             (NEW small — extends PDA Review's│
│     │                                         PRM_TaxonomyService)           │
│     ├── PRM_InfoCodeReactivator             (NEW small)                      │
│     ├── PRM_IdentifierReactivator           (extends PRM_OffCycleIdentifierSvc)│
│     ├── PRM_ProviderFeatureReactivator      (NEW small)                      │
│     └── PRM_CaseDataMgrService              (REUSE — Par Form/PDA)           │
│                                                                              │
│   PRM_ReinstatePracticeLocationService      (NEW — replaces the 12-elt IP)  │
│     └── reuses every reactivator above (location-scoped)                     │
│                                                                              │
│   PRM_ReinstateVendorAccountService         (NEW — replaces the 22-elt IP)  │
│     ├── ≤10 locations  → sync path (reactivators above, vendor-scoped)       │
│     └── > 10 locations → async path: PRM_ReinstateVendorAccountBatch         │
│                                                  (REUSE — already exists!)   │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  SUPPORT LAYER                                                               │
│    Selectors (REUSE — every one exists after Off Cycle Submit lands):        │
│      ✔ PRM_AccountSelector       ✔ PRM_HCFSelector                           │
│      ✔ PRM_HCPFSelector          ✔ PRM_HCFNetworkSelector                    │
│      ✔ PRM_IdentifierSelector    ✔ PRM_LocationNPIHistorySelector            │
│      + PRM_ReinstateSelector     (NEW — bulk façade replacing the 5+ DR      │
│                                   Extracts: PRMDRExtractHPFReinstate,        │
│                                   PRMGetReInstateData, PRMDREHcProviderIdentifier,│
│                                   DREFacilityLocationAddress, DREHcPFacilityAssociation)│
│                                                                              │
│    Transformers (mostly NEW, small — replace 7 DR Transforms):              │
│      • PRM_ReinstateTransformer    (NEW — combines PRMDRTransformReinstateAll│
│                                      + PRMTransformReInstateTables + 3 more)│
│      • PRM_ReinstateRowPartitioner (NEW — replaces the 5×Loop/3-Branch pattern│
│                                      with a pure-Apex bucket sort)          │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CROSS-CUTTING  (REUSE)                                                      │
│    PRM_DMLUtil   PRM_CollectionUtil   PRM_GovernorUtil                       │
│    PRM_ErrorLogger   PRM_TransactionContext   PRM_AsyncJobBase               │
└──────────────────────────────────────────────────────────────────────────────┘
                          │  TX1 (sync) / TX2 (Queueable or Batchable)
                          ▼
                 ┌────────────────────────┐
                 │  Database / Platform   │
                 └────────────────────────┘
```

### 3.2 Transaction Boundary (per scope)

> The TX1 / TX2 split follows the framework's boundary doctrine ([§ 14.5 of `PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md#145-tx1--tx2-boundary-doctrine)). The **directory and member-search expose `Account.IsActive`**, so flipping it before child reactivations land would create a "ghost practitioner" — a record that appears active in the directory while its HCPF / HCFN / Identifier rows are still inactive. The Reinstate boundary therefore deliberately keeps `Account.IsActive=true` in TX2 alongside its children, and TX1 stamps a status flag instead.

| Scope | TX1 (sync) | TX2 (async) | Rationale |
|---|---|---|---|
| **Practitioner** | Case + IndividualApplication + Note + `IndividualApplication.PRM_ReinstateStatus__c = 'In-Flight'` (the directory and member-search query this status to suppress the practitioner from search results until child rows reactivate) | Account reactivate (`IsActive=true`), HCPF reactivate (split into `PRM_HCPFReactivator.markActive(...)` + `PRM_HCPFReactivator.attachNewHCFNs(...)` + `PRM_HCPFReactivator.cascadeAttestation(...)`), HCFN reactivate (atomic with HCPF via `PRM_BulkOperation.atomicPair()`), BoardCert, Taxonomy, InfoCode, Identifier, ProviderFeature reactivations + CaseDataMgr finish stamp via `PRM_ReinstatePractitionerAsyncJob` (Queueable) | Practitioner flow worst case is **~150–300 UPDATE rows** — the existing Vendor batch threshold. The async hand-off is gated by `PRM_AsyncEnqueueGuard.safeEnqueue(...)` so an exhausted Queueable cap falls back to inline. |
| **Practice Location** | Entire 12-element flow runs sync **only when `partition.estimatedRowCount() ≤ 50`** (same threshold as `PRM_GovernorUtil.shouldDelegateAsync`); rows split exclusively across `simpleReactivate / mustClone / partialClone / skipBecauseOrphan` (no overlap) | If row count > 50, an inline-fallback Queueable runs the partition's clone-DML in async TX2 — same body, just different governor context | Row counts can climb on high-volume practice locations; explicit threshold prevents 1× governor breach. |
| **Vendor (≤10 loc)** | Account + Case + IndividualApplication + Note + per-loc HCF/HCPF/HCPNPI/InfoCode/HCPF reactivate **inside `PRM_BulkOperation.atomicPair()`** so per-location pairs commit atomically even on the sync path | n/a | Today's `CB_PracticeLocationLessThanEqualTo10` path — Apex makes this faster but still sync. |
| **Vendor (>10 loc)** | Case + IndividualApplication + `IndividualApplication.PRM_ReinstateStatus__c = 'In-Flight'` (~3–4 rows) | Account reactivate + per-loc fan-out via existing `PRM_ReinstateVendorAccountBatch` (Batchable, **REUSE** — existing class, just invoked from Apex instead of via Remote Action from the IP) | Already-proven async path. We just reuse it; Account flip is moved to TX2 alongside children to keep directory consistent. |

### 3.3 Existing Apex consolidation

The migration is also a **standardisation** pass for the existing one-offs:

| Existing class | Today | After migration |
|---|---|---|
| `PRM_ReinstateCallable` (40 LoC Callable) | bridges the OS `RA_CallBatch` Remote Action to `Database.executeBatch(new PRM_ReinstateVendorAccountBatch(...), 5)` | **Retired** — `PRM_ReinstateVendorAccountService.processAsync()` calls `Database.executeBatch` directly. The Callable is no longer needed because the OS routes through `PRM_ServiceDispatcher`, which is its own dispatch mechanism. |
| `PRM_ReinstateVendorAccountBatch` + Helper | works as-is; ~600 LoC | **Kept verbatim** — just invoked by `PRM_ReinstateVendorAccountService` instead of by `PRM_ReinstateCallable` |
| `PRM_ReinstateUtils.fetchPractitionerPracticeLocation()` (@AuraEnabled selector for the LWC) | works as-is | **Kept** — possibly refactored to delegate to `PRM_HCPFSelector` for consistency, but no behaviour change |
| `PRM_ReinstatePracticeLocationWrapper` DTO | one-off DTO for the LWC | **Kept** — possibly merged into a generic `ReinstateRowDTO` |
| `PRM_ValidateDuplicateTaxonomyReinstate` IP | small validation IP called from the OS | **Migrated** — folded into `PRM_TaxonomyReactivator.validateNoDuplicates()` |
| `PRM_SetSelectAllReInstate` IP | small bulk-select helper | **Migrated** — folded into `PRM_ReinstateRowPartitioner.selectAll()` |
| LWC `prmReinstatePractitionerPracticeLocation` | unchanged | **Unchanged** — keeps calling `PRM_ReinstateUtils` directly |

### 3.4 OmniScript / IP Dispatcher Wiring

```
PRM_ReinstateRecordCreation             → ServiceInvoker("ReinstatePractitioner")
                                          → PRM_ReinstatePractitionerService
PRM_ReinstatePracticeLocation           → ServiceInvoker("ReinstatePracticeLocation")
                                          → PRM_ReinstatePracticeLocationService
PRM_PractitionerReinstateVendorUpdate   → ServiceInvoker("ReinstateVendorAccount")
                                          → PRM_ReinstateVendorAccountService
```

Each of the 3 orchestrator IPs shrinks to **3 elements** (SetValues → ServiceInvoker → Response). The Parent containers' `TryCatchBlock` becomes a `try / catch` in each service.

---

## 4. Reusability Matrix — what survives, what extends, what's net new

Legend: **REUSE** = used as-is. **EXTEND** = subclass / add a method. **NEW** = build new. **STANDARDISE** = existing Apex one-off that gets folded into the framework.

### 4.1 Framework / Cross-cutting (100% reuse)

| Class | Disposition | Notes |
|---|---|---|
| `PRM_ServiceDispatcher`, `PRM_BaseService`, `PRM_ServiceRequest/Response` | **REUSE** | Add 3 entries to the registry |
| `PRM_TransactionContext`, `PRM_ErrorLogger` | **REUSE** | TryCatchBlock → service `catch` |
| `PRM_DMLUtil` | **REUSE** | partial-success UPDATE for all 10 SObjects |
| `PRM_CollectionUtil` | **REUSE** | replaces every LA / Loop / Set Values bucket-sort step |
| `PRM_GovernorUtil` | **REUSE** | TX1/TX2 split decision |
| `PRM_AsyncJobBase` | **REUSE** | `PRM_ReinstatePractitionerAsyncJob` extends |

### 4.2 Selectors

| Selector | Disposition | Replaces |
|---|---|---|
| `PRM_AccountSelector` | **REUSE** | (practitioner Account load) |
| `PRM_HCFSelector` | **REUSE** | `DREFacilityLocationAddress` |
| `PRM_HCPFSelector` | **REUSE** | `PRMDRExtractHPFReinstate`, `DREHcPFacilityAssociation` |
| `PRM_HCFNetworkSelector` | **REUSE** | the HFN load behind `PRMDRHCFacilityNetworkForReInstate` |
| `PRM_IdentifierSelector` | **REUSE** | `DREHcProviderIdentifier` |
| `PRM_LocationNPIHistorySelector` | **REUSE** | NPI history load behind `UpdateNPIRelatedToPracLoc` |
| `PRM_ReinstateSelector` | **NEW** | single façade replacing `PRMGetReInstateData`, `PRMDRExtractHPFReinstate`, `PRMFetchCaseManagerReinstate`, `PRMDRReinstateFetchPractitionerTaxonomy`, `DREPracLocSummaryInfoCodeProgPart` (5 DRs collapsed into 1 Apex method) |

### 4.3 Transformers

| Transformer | Disposition | Replaces |
|---|---|---|
| `PRM_ReinstateTransformer` | **NEW** | folds in `PRMDRTransformReinstateAll`, `PRMTransformReInstateTables`, `PRMDRTPracLocAssociationReinstate`, `PRMDRTPracLocDataForReinstate`, `PRMDRTransformVendorReinstateAll`, `PRMDRReinstateFetchPractitionerTaxonomy` (transform side) |
| **`PRM_ReinstateRowPartitioner`** | **NEW** | replaces the **45-element** Loop/Conditional/SetValues scaffold across 5 sub-entities. Pure-function bucket sort: `Map<Bucket, List<RowDTO>>` |

### 4.4 External integration

None. Reinstate is **pure database work** — no callouts.

### 4.5 Domain / Orchestration services

| Service | Disposition | Source / Notes |
|---|---|---|
| `PRM_ReinstatePractitionerService` | **NEW** | top-level orchestrator (replaces 72-elt IP). ~150 lines |
| `PRM_ReinstatePracticeLocationService` | **NEW** | top-level orchestrator (replaces 12-elt IP). ~80 lines (reuses sub-reactivators) |
| `PRM_ReinstateVendorAccountService` | **NEW** | top-level orchestrator with the ≤10 / >10 branch. ~120 lines |
| `PRM_PractitionerAccountReactivator` | **NEW** | wraps `PRMDRPractitionerAccountUpdate` + `PRMUpdateHealthCareDetailsReinstate` |
| `PRM_HCPFReactivator` | **NEW** | wraps `PRMDRPracticeToPractitionerUpdate` + `LoadReinstatePractPracLoc` + the new HCPF-create path (`CreatePracticeToPractitioner`) |
| `PRM_HCFReactivator` | **NEW** | wraps `PRMDRHealthcarefaciityUpdate` + `PRMDRPracticeLocationUpdate` |
| `PRM_HCFNReactivator` | **NEW** | wraps `PRMDRPracticeLocationTaxNetworkUpdate` + the network-create path (`DRPostHealthCareFacilityNetwork`) |
| `PRM_BoardCertReactivator` | **NEW** | wraps `PRMReinstateBoardCertsUpdate` |
| `PRM_TaxonomyReactivator` | **EXTEND** of `PRM_TaxonomyService` (PDA) | adds `reinstate(...)` — replaces `PRMReinstateHealthcareProviderTaxonomyRecordUpdate` |
| `PRM_InfoCodeReactivator` | **NEW** | wraps `PRMReinstateInfoCodeAssignmentUpdate` + the loc-scoped variant |
| `PRM_IdentifierReactivator` | **EXTEND** of `PRM_OffCycleIdentifierService` | adds `reactivate(...)` — replaces `PRMDRIdentifierUpdate` + `DRPHcProviderIdentifier` |
| `PRM_ProviderFeatureReactivator` | **NEW** | wraps `PRMDRPracticeLocationAPUpdate` |
| `PRM_CaseService` | **REUSE** (Par Form) | every Case + IndividualApplication create / update |
| `PRM_NoteService` | **REUSE** (Par Form) | `CreateNote` / `RA_CreateNote` / `RACreateNote` |
| `PRM_CaseDataMgrService` | **REUSE** (Par Form / PDA Review) | `PRMDRPCaseDataManager`, `DRToUpdateRecordsAfterReInstate`, `CaseDataManagerCaseManager`, `DRPCaseDataManagerCaseManager` |
| `PRM_ReinstatePractitionerAsyncJob` | **NEW** | Queueable wrapping the TX2 reactivators for the Practitioner flow |
| **`PRM_ReinstateVendorAccountBatch`** | **STANDARDISE (REUSE)** | **The existing Batchable class** — kept verbatim, invoked from `PRM_ReinstateVendorAccountService.processAsync()` |
| `PRM_ReinstateVendorAccountBatchHelper` | **STANDARDISE (REUSE)** | existing helper, kept verbatim |
| `PRM_ReinstateCallable` | **RETIRE** | no longer needed — `PRM_ServiceDispatcher` is the new bridge |
| `PRM_ReinstateUtils` (AuraEnabled selector for LWC) | **REUSE** (or thin-wrap to `PRM_HCPFSelector`) | LWC stays unchanged |
| `PRM_ReinstatePracticeLocationWrapper` | **REUSE** | DTO kept |

### 4.6 Reuse Score

| Bucket | Reused | Extended | New | Standardise (kept) | Total |
|---:|---:|---:|---:|---:|---:|
| Framework / cross-cutting | 9 | 0 | 0 | 0 | 9 |
| Selectors | 6 | 0 | 1 | 0 | 7 |
| Transformers | 0 | 0 | 2 | 0 | 2 |
| Domain services | 3 | 2 | 11 | 3 | 19 |
| **Totals** | **18** | **2** | **14** | **3** | **37** |
| **% reused or standardised (incl. extends)** | **62%** | | | | |

> Reuse percentage is lower (62%) than Off Cycle PDA Review (76%) because the **reactivator services are net-new** — every reactivator targets a slightly different SObject with slightly different fields (`PRM_Active__c` vs `IsActive` vs `EffectiveTo` vs `PRM_NonParticipatingStartDate__c`). However, the **existing Apex precedent** (`PRM_ReinstateVendorAccountBatch` + Helper + 3 supporting classes — ~700 LoC) is kept **verbatim**, so net-new LoC is closer to **1,200**, comparable to Off Cycle PDA Review.

---

## 5. Element-by-Element Migration Map

### 5.1 FLOW A — `PRM_ReinstateRecordCreation` (72 → ~10 service calls)

The biggest win in this whole document. The 45 loop / conditional / set-value elements collapse to **one** call to `PRM_ReinstateRowPartitioner.partition(dto)`.

#### Group 1 — Case / CaseManager / Note (5 → 2 calls)
| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 1 | `ExtractCaseManagerDetails` | `PRM_ReinstateSelector.loadCaseManager(...)` | NEW selector |
| 2 | `PRMLoadCaseCaseManager` | `PRM_CaseService.createCase(CaseFactory.forReinstate(dto))` | REUSE |
| 3 | `SetCaseManagerId`, `SVEntityId`, `SVNotes` | inlined | n/a |
| 4 | `CreateNote` | `PRM_NoteService.createCaseNote(caseId, dto.note)` | REUSE |

#### Group 2 — Practitioner-level fetch / transforms (4 → 1 call)
| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 5 | `PRMUpdateHealthCareDetails` | `PRM_PractitionerAccountReactivator.applyHealthCareDetailUpdates(...)` | NEW |
| 6 | `PRMDRExtractHpf` | `PRM_HCPFSelector.byPractitionerInactive(...)` | REUSE |
| 7 | `SetInfoCodeAssignmentToList` | inlined | n/a |
| 8 | `ExistingPracticeLocationAdded` | `dto.hasNewlyAttachedLocation()` | n/a |

#### Group 3 — Network / Taxonomy transformation (5 → 3 calls)
| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 9 | `RAToTransformNetworkTaxonomyRecords` | `PRM_ReinstateTransformer.shapeNetworkTaxonomy(dto)` | NEW |
| 10 | `RAToTranformPractPracRecords` | `PRM_ReinstateTransformer.shapePractPrac(dto)` | NEW |
| 11 | `LoadReinstatePractPracLoc` | `PRM_HCPFReactivator.bulkInsertNew(...)` | NEW |
| 12 | `CreatePracticeToPractitioner` | (same as 11 — wrapped together) | n/a |
| 13 | `DRPostHealthCareFacilityNetwork` | `PRM_HCFNReactivator.bulkInsertNew(...)` | NEW |

#### Group 4 — The 45-element bucket sort (collapses to 1 call)

**All ~45 elements** (the 5 LoopBlocks + 15 conditional blocks + 15 SetValues steps for the 5 sub-entities) collapse into:

```apex
PRM_ReinstateRowPartitioner.Result buckets = PRM_ReinstateRowPartitioner.partition(dto);
// buckets.toReinstateAndUpdate     — rows where ReinstateAs=true AND Update=Yes
// buckets.toReinstateButDontUpdate — rows where ReinstateAs=true AND Update=No
// buckets.toLeaveAlone             — rows where ReinstateAs=false
```

The partitioner runs against each sub-entity input list (Practice-Practitioner, BoardCert, Taxonomy, InfoCode, Identifier) and returns one buckets object per. Total scaffold: **~80 lines of Apex** replacing **45 IP elements**.

#### Group 5 — DR Post UPDATE bundles (10 → 8 reactivator calls)
| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 60 | `PRMDRHealthcarefaciityUpdate` | `PRM_HCFReactivator.reactivateFacilities(buckets.hcf)` | NEW |
| 61 | `PRMDRPracticeLocationUpdate` | `PRM_HCFReactivator.reactivateLocations(buckets.loc)` | NEW |
| 62 | `PRMDRPracticeToPractitionerUpdate` | `PRM_HCPFReactivator.reactivate(buckets.hcpf)` | NEW |
| 63 | `PRMDRPracticeLocationTaxNetworkUpdate` | `PRM_HCFNReactivator.reactivate(buckets.hcfn)` | NEW |
| 64 | `PRMDRPracticeLocationAPUpdate` | `PRM_ProviderFeatureReactivator.reactivate(buckets.providerFeature)` | NEW |
| 65 | `PRMDRPractitionerAccountUpdate` | `PRM_PractitionerAccountReactivator.reactivate(dto.practitionerId)` | NEW |
| 66 | `PRMDRIdentifierUpdate` | `PRM_IdentifierReactivator.reactivate(buckets.identifier)` | EXTEND |
| 67 | `PRMReinstateBoardCertsUpdate` | `PRM_BoardCertReactivator.reactivate(buckets.boardCert)` | NEW |
| 68 | `PRMReinstateInfoCodeAssignmentUpdate` | `PRM_InfoCodeReactivator.reactivate(buckets.infoCode)` | NEW |
| 69 | `PRMReinstateHealthcareProviderTaxonomyRecordUpdate` | `PRM_TaxonomyReactivator.reactivate(buckets.taxonomy)` | EXTEND |

#### Group 6 — Case Data Manager flag stamping (3 → 1 call)
| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 70 | `DRToExtractDataFromCaseManagerToUpdateReInstate` | `PRM_ReinstateSelector.loadCaseManagerFlags(caseMgrId)` | NEW selector |
| 71 | `DRToUpdateRecordsAfterReInstate` | `PRM_CaseDataMgrService.stampReinstateFlags(...)` | REUSE |
| 72 | `PRMDRPCaseDataManager` | (same) | n/a |

### 5.2 FLOW B — `PRM_ReinstatePracticeLocation` (12 → 1 service call chain)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 1 | `SV_ReinstateData` | inlined | n/a |
| 2 | `ExtractPractitionerPracLocData` | `PRM_ReinstateSelector.loadPracticeLocationContext(locId)` | NEW selector |
| 3 | `TransformPracLocAssociationForReinstate` | `PRM_ReinstateTransformer.shapeHCPFForReactivate(...)` | NEW |
| 4 | `TransformPracLocDataForReinstate` | `PRM_ReinstateTransformer.shapeLocationForReactivate(...)` | NEW |
| 5 | `CreateCaseNCaseManager` | `PRM_CaseService.createCase(CaseFactory.forReinstateLocation(dto))` | REUSE |
| 6 | `RA_CreateNote` | `PRM_NoteService.createCaseNote(...)` | REUSE |
| 7 | `UpdatePracticeLocationAddress` | `PRM_HCFReactivator.reactivateLocations(...)` + `PRM_HCFReactivator.reactivateAddresses(...)` | NEW |
| 8 | `UpdateNPIRelatedToPracLoc` | `PRM_LocationNPIHistoryService.reactivateOpenPeriod(locId)` | NEW (extends NPI helper) |
| 9 | `UpdatePracLocSummaryInfoCodeProgPartIP` | `PRM_InfoCodeReactivator.reactivateByLocation(locId)` | NEW |
| 10 | `UpdateHcPFacilityAssociation` | `PRM_HCPFReactivator.reactivate(transformedHCPFs)` | NEW |
| 11 | `CaseDataManagerCaseManager` | `PRM_CaseDataMgrService.stampReinstateFlags(caseMgrId)` | REUSE |
| 12 | `ResponseForResinstate` | built by `PRM_ReinstatePracticeLocationService` | n/a |

### 5.3 FLOW C — `PRM_PractitionerReinstateVendorUpdate` (22 → 1 service with ≤10/>10 branch)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 1 | `LA_PracticeLocation` + `SetValues` | `PRM_CollectionUtil.filter(dto.locations, "Selected==true")` | REUSE |
| 2 | `DREHcProviderIdentifier` | `PRM_IdentifierSelector.byVendor(vendorId)` | REUSE |
| 3 | `DRPCaseManagerCaseAccount` | `PRM_CaseService.createCase(...) + PRM_PractitionerAccountReactivator.reactivate(vendorAccountId)` | REUSE + NEW |
| 4 | `DRPHcProviderIdentifier` | `PRM_IdentifierReactivator.reactivate(identifiers)` | EXTEND |
| 5 | `DRPInfoCodeProgPart` | `PRM_InfoCodeReactivator.reactivate(infoCodes)` | NEW |
| 6 | `RACreateNote` | `PRM_NoteService.createCaseNote(...)` | REUSE |
| 7 | `CB_PracticeLocationExist` (gating) | `if (!dto.selectedLocations.isEmpty())` | n/a |
| 7.1–7.4 | `DREFacilityLocationAddress`, `DREPracLocSummaryInfoCodeProgPart`, `DREHcPFacilityAssociation`, `LA_UniqueHcProviderNPI` | `PRM_ReinstateSelector.loadVendorContext(...)` | NEW (bulk selector) |
| 8 | `CB_PracticeLocationLessThanEqualTo10` | `if (dto.locationCount <= 10) { runSync(dto); }` | n/a |
| 8.1–8.5 | `DRPFacilityLocationAddress`, `DRPHealthcareProviderNPI`, `DRPPracLocSummaryInfoCodeProgPart`, `DRPHcPFacilityAssociation`, `DRPCaseDataManagerCaseManager` | `PRM_HCFReactivator + PRM_HCPFReactivator + PRM_InfoCodeReactivator + PRM_CaseDataMgrService` (chained) | NEW + REUSE |
| 9 | `CB_PracticeLocationGreaterThan10` | `else { runAsync(dto); }` | n/a |
| 9.1 | `Set_BatchData` | inlined into `PRM_ReinstateVendorAccountService.runAsync()` | n/a |
| 9.2 | `RA_CallBatch` | `Database.executeBatch(new PRM_ReinstateVendorAccountBatch(dto.toMap()), 5)` | **REUSE existing batch** |
| 10 | `ResponseAction` | built by `PRM_ReinstateVendorAccountService` | n/a |

---

## 6. Service Code — key signatures

### 6.1 `PRM_ReinstatePractitionerService` (replaces the 72-element IP)

> **Why we need it** — `PRM_ReinstateRecordCreation` is the **2nd-heaviest IP in the entire PNM codebase** at 72 elements. Its job is straightforward — bring an inactive practitioner and all their related rows back to active — but the IP form forces the work through 5 sub-entity (HCPF, HCFN, Identifier, Taxonomy, BoardCert) loops, each with 3 conditional blocks (`reinstate?`, `update?`, `is-deactivated?`) and 3 SetValues steps. That's a 45-element loop scaffold that exists purely as IP plumbing. Today this IP routinely breaches CPU limits when a practitioner has 25+ HCPFs; production has logged 4-7.5 s of CPU on a single reinstate.
>
> **How it helps** — A single Apex orchestrator with the 7 sub-services injected (`PRM_PractitionerAccountReactivator`, `PRM_HCPFReactivator`, `PRM_HCFReactivator`, `PRM_HCFNReactivator`, `PRM_BoardCertReactivator`, `PRM_TaxonomyReactivator`, `PRM_InfoCodeReactivator`). The 45-element loop scaffold becomes one call to `PRM_ReinstateRowPartitioner.partition(dto)` which buckets every row in O(n) — no nested loops in the orchestrator. Composes 7 reactivator calls with a clean error envelope; delegates to `PRM_ReinstatePractitionerAsyncJob` when row count breaches threshold.
>
> **Outcome** — 72 IP elements → ~150 lines. Sync TX1 < 600 ms even on a 25-HCPF practitioner. The 45-element loop scaffold becomes 1 call. Each reactivator is independently unit-testable.

```apex
public with sharing class PRM_ReinstatePractitionerService extends PRM_BaseService {

    @TestVisible private PRM_ReinstateSelector            selector;
    @TestVisible private PRM_PractitionerAccountReactivator accountReact;
    @TestVisible private PRM_HCFReactivator               hcfReact;
    @TestVisible private PRM_HCPFReactivator              hcpfReact;
    @TestVisible private PRM_HCFNReactivator              hcfnReact;
    @TestVisible private PRM_BoardCertReactivator         boardReact;
    @TestVisible private PRM_TaxonomyReactivator          taxonomyReact;
    @TestVisible private PRM_InfoCodeReactivator          infoReact;
    @TestVisible private PRM_IdentifierReactivator        idReact;
    @TestVisible private PRM_ProviderFeatureReactivator   pfReact;
    @TestVisible private PRM_CaseDataMgrService           caseDataMgr;

    public override String serviceName() { return 'ReinstatePractitioner'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        PRM_TransactionContext.start('ReinstatePractitioner', req);

        ReinstatePractitionerDTO dto = ReinstatePractitionerDTO.fromRequest(req);
        ReinstateResult res = new ReinstateResult();

        // ===== TX1 (sync, critical path) =================================
        res.caseId = PRM_CaseService.createCase(CaseFactory.forReinstate(dto));
        if (dto.hasNote()) {
            PRM_NoteService.createCaseNote(res.caseId, dto.note());
        }
        // The directory and member-search query PRM_ReinstateStatus__c. Stamping
        // 'In-Flight' suppresses the practitioner from search results until TX2
        // finishes flipping Account.IsActive=true alongside child reactivations.
        PRM_CaseDataMgrPatcher.patch('Reinstate', res.caseManagerId,
            new Map<String, Object>{ 'PRM_ReinstateStatus__c' => 'In-Flight' });

        // NOTE: Account.IsActive=true is moved to TX2 (see runHeavyDml). Flipping it
        // sync would expose a "ghost practitioner" — a directory-active record whose
        // HCPF/HCFN/Identifier rows are still inactive — to the directory and
        // member-search APIs.

        // ===== TX2 (async — Queueable) ===================================
        PRM_AsyncEnqueueGuard.safeEnqueue(
            new PRM_ReinstatePractitionerAsyncJob(dto, res),
            new Runnable() { public void run() { runHeavyDml(dto, res); } },
            dto.estimatedRowCount(),
            response);

        return PRM_ServiceResponse.ok(res.toMap());
    }

    /** All reactivation DML (TX2) — rows commit together so the directory never sees a ghost. */
    @TestVisible
    void runHeavyDml(ReinstatePractitionerDTO dto, ReinstateResult res) {
        // 1) ONE call replaces the 45-element loop/CB/setvalue scaffold.
        //    The partitioner's buckets are EXCLUSIVE — every row appears in at most one
        //    bucket; rows belonging to multiple buckets pre-decision must be tagged with
        //    a single primary action (toReinstate, toUpdate, or skip) before partition.
        PRM_ReinstateRowPartitioner.Result buckets =
                PRM_ReinstateRowPartitioner.partition(dto);

        // 2) HCPF reactivation is split into ordered phases so the directory sees a
        //    consistent state at every commit:
        //       a) markActive       — flip HCPF.IsActive=true (atomic with HCFN attach)
        //       b) attachNewHCFNs   — atomicPair(insert new HCFN + update HCPF link)
        //       c) cascadeAttestation — stamp HCPF.AttestationDate from parent HCFacility
        hcfReact.reactivateFacilities(buckets.hcf, res);
        hcfReact.reactivateLocations(buckets.location, res);
        hcpfReact.markActive(buckets.hcpf, res);
        hcpfReact.attachNewHCFNs(buckets.hcpf, buckets.hcfn, res);     // PRM_BulkOperation.atomicPair
        hcpfReact.cascadeAttestation(buckets.hcpf, res);
        pfReact.reactivate(buckets.providerFeature, res);
        idReact.reactivate(buckets.identifier, res);
        boardReact.reactivate(buckets.boardCert, res);
        infoReact.reactivate(buckets.infoCode, res);
        taxonomyReact.reactivate(buckets.taxonomy, res);

        // 3) Account flip — LAST inside TX2, after every child has reactivated.
        //    If any reactivation failed, accountReact.reactivate is gated on
        //    res.errors.isEmpty() so the practitioner is not exposed to the directory
        //    in a partial state. The next nightly Reinstate retry job picks up the
        //    case from the In-Flight status.
        if (res.errors.isEmpty()) {
            accountReact.reactivate(dto.practitionerId, res);
        }

        // 4) Final flag stamp (field-level merge).
        PRM_CaseDataMgrPatcher.patch('Reinstate', res.caseManagerId,
            new Map<String, Object>{
                'PRM_ReinstateStatus__c' => res.errors.isEmpty()
                                              ? 'Reinstated'
                                              : 'Partial-Failed',
                'PRM_ReinstateCompletedAt__c' => System.now()
            });
    }
}
```

### 6.2 `PRM_ReinstateRowPartitioner` (the 45-element collapse)

> **Why we need it** — The single biggest IP-form pain point in the entire Reinstate flow is the **45-element scaffold** that exists purely to bucket-sort rows. For each of 5 sub-entities (HCPF, HCFN, Identifier, Taxonomy, BoardCert), the IP runs: LoopBlock → ConditionalBlock("Yes? skip") → ConditionalBlock("No? skip") → ConditionalBlock("False? skip") → SetValues("ToReinstate") → SetValues("ToUpdate") → SetValues("Deactivated"). That's 9 elements per sub-entity × 5 = 45 elements of pure plumbing. None of this is business logic; all of it is OmniStudio's awkward way of expressing a `groupBy` — and the IP-side bucketing has a quiet bug: a row whose `reinstateAs=true AND update='Yes'` was added to BOTH the `toReinstateAndUpdate` and `toReinstateButDontUpdate` buckets, causing duplicate update DML downstream.
>
> **How it helps** — A single Apex pure function with one input (`PRM_ReinstateDTO`) and one typed output (`Map<Bucket, List<RowDTO>>`). One O(n) pass over the input rows, one branch per row to assign its bucket. The buckets are **strictly exclusive** — every row is assigned to exactly one of `toReinstateAndUpdate`, `toReinstateButDontUpdate`, or `toLeaveAlone`; the precedence rule is enforced by an `if / else if / else` chain rather than three independent conditionals. Zero DML, zero SOQL, zero callouts — pure transformation. 100% unit-testable with table-driven fixtures.
>
> **Outcome** — 45 IP elements → 1 method call. The largest single piece of OmniStudio plumbing in the Reinstate chain disappears. Bucket-sort logic becomes table-driven instead of conditional-block-driven; the duplicate-bucket bug class is closed by construction; every edge case becomes a unit-test row.

```apex
public with sharing class PRM_ReinstateRowPartitioner {

    public class Buckets<T> {
        public List<T> toReinstateAndUpdate     = new List<T>();
        public List<T> toReinstateButDontUpdate = new List<T>();
        public List<T> toLeaveAlone             = new List<T>();
    }

    public class Result {
        public Buckets<HealthcarePractitionerFacility>      hcpf;
        public Buckets<HealthcareFacility>                  hcf;
        public Buckets<Location>                            location;
        public Buckets<HealthcareFacilityNetwork>           hcfn;
        public Buckets<PRM_ProviderFeature__c>              providerFeature;
        public Buckets<Identifier__c>                       identifier;
        public Buckets<BoardCertification__c>               boardCert;
        public Buckets<PRM_InfoCodeAssignment__c>           infoCode;
        public Buckets<HealthcareProviderTaxonomy>          taxonomy;

        /** Total rows about to receive DML — input to PRM_GovernorUtil.shouldDelegateAsync. */
        public Integer estimatedRowCount() {
            return hcpf.toReinstateAndUpdate.size() + hcpf.toReinstateButDontUpdate.size()
                 + hcfn.toReinstateAndUpdate.size() + hcfn.toReinstateButDontUpdate.size()
                 + identifier.toReinstateAndUpdate.size() + identifier.toReinstateButDontUpdate.size()
                 + taxonomy.toReinstateAndUpdate.size() + taxonomy.toReinstateButDontUpdate.size()
                 + boardCert.toReinstateAndUpdate.size() + boardCert.toReinstateButDontUpdate.size()
                 + infoCode.toReinstateAndUpdate.size() + infoCode.toReinstateButDontUpdate.size();
        }
    }

    /** Replaces the 45 IP elements (5 LoopBlocks × 3-conditional × 3-setvalue). */
    public static Result partition(ReinstatePractitionerDTO dto) {
        Result r = new Result();
        r.hcpf            = partitionRows(dto.practiceToPractitionerRows());
        r.boardCert       = partitionRows(dto.boardCertRows());
        r.taxonomy        = partitionRows(dto.taxonomyRows());
        r.infoCode        = partitionRows(dto.infoCodeRows());
        r.identifier      = partitionRows(dto.identifierRows());
        r.hcf             = partitionFacilities(dto);
        r.location        = partitionLocations(dto);
        r.hcfn            = partitionHCFN(dto);
        r.providerFeature = partitionProviderFeatures(dto);
        return r;
    }

    /** The generic bucket-sort that replaces each 9-element IP block.
     *  Strict precedence: a row appears in EXACTLY ONE bucket. */
    @TestVisible
    static <T extends ReinstatableRow> Buckets<T> partitionRows(List<T> rows) {
        Buckets<T> b = new Buckets<T>();
        for (T row : rows) {
            if (!row.reinstateAs()) {
                b.toLeaveAlone.add(row);                     // skip
            } else if (row.update() == 'Yes') {
                b.toReinstateAndUpdate.add(row);             // reactivate + update fields
            } else {
                b.toReinstateButDontUpdate.add(row);         // reactivate only
            }
            // No row ever lands in two buckets — the IP-form duplicate-bucket bug
            // is closed by the if/else if/else structure.
        }
        return b;
    }
}
```

> `ReinstatableRow` is a one-method interface (`reinstateAs()` + `update()`). Implementing it on the 5 row DTOs gives a single 6-line generic method that replaces the 9-element IP block 5 times over.

### 6.3 `PRM_ReinstateVendorAccountService` (with the existing batch reuse)

> **Why we need it** — The Vendor Reinstate flow already has an existing Apex implementation: `PRM_ReinstateVendorAccountBatch` + `PRM_ReinstateVendorAccountBatchHelper` (~750 LoC of production-hardened Apex used today for the >10-locations branch). The IP layer (`PRM_PractitionerReinstateVendorUpdate`, 22 elements) is a thin shim that decides whether to delegate via `PRM_ReinstateCallable` to the batch or to inline the work in IP. The split logic is hard to follow — small vendors run inline (slow, sync), big vendors run batch (fast, async) — and there's no breadcrumb that ties the two paths to the same submit.
>
> **How it helps** — A single Apex service that owns the ≤10 / >10 branch decision explicitly. Reuses `PRM_ReinstateVendorAccountBatch` **verbatim** (no rewrite — it's already correct) for the >10 path; runs the small ≤10 path inline using the same reactivator services as the Practitioner flow. Retires `PRM_ReinstateCallable` (the IP→Apex bridge becomes unnecessary because `PRM_ServiceDispatcher` is the new bridge). Stamps a single transaction id across both paths so triage starts from one log query.
>
> **Outcome** — 22 IP elements → ~120 lines. ~750 LoC of existing Apex kept verbatim — zero regression risk. `PRM_ReinstateCallable` retired (one less hop in stack traces).

```apex
public with sharing class PRM_ReinstateVendorAccountService extends PRM_BaseService {

    private static final Integer ASYNC_THRESHOLD = 10; // same as today's IP

    @TestVisible private PRM_ReinstateSelector            selector;
    @TestVisible private PRM_HCFReactivator               hcfReact;
    @TestVisible private PRM_HCPFReactivator              hcpfReact;
    @TestVisible private PRM_InfoCodeReactivator          infoReact;
    @TestVisible private PRM_IdentifierReactivator        idReact;
    @TestVisible private PRM_CaseDataMgrService           caseDataMgr;

    public override String serviceName() { return 'ReinstateVendorAccount'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        ReinstateVendorDTO dto = ReinstateVendorDTO.fromRequest(req);
        ReinstateResult res = new ReinstateResult();

        // TX1 — always sync
        res.caseId = PRM_CaseService.createCase(CaseFactory.forReinstateVendor(dto));
        new PRM_PractitionerAccountReactivator().reactivate(dto.vendorAccountId, res);
        idReact.reactivate(selector.identifiersByVendor(dto.vendorAccountId), res);
        infoReact.reactivate(dto.infoCodes(), res);
        if (dto.hasNote()) {
            PRM_NoteService.createCaseNote(res.caseId, dto.note());
        }

        if (dto.selectedLocations.isEmpty()) {
            return PRM_ServiceResponse.ok(res.toMap());
        }

        // Branch on the >10 threshold — preserves today's behaviour exactly
        if (dto.locationCount() <= ASYNC_THRESHOLD) {
            runSync(dto, res);
        } else {
            // REUSE the existing batch class - just invoke it directly
            Database.executeBatch(new PRM_ReinstateVendorAccountBatch(dto.toMap()), 5);
            res.asyncJobName = 'PRM_ReinstateVendorAccountBatch';
        }
        return PRM_ServiceResponse.ok(res.toMap());
    }

    @TestVisible
    void runSync(ReinstateVendorDTO dto, ReinstateResult res) {
        PRM_ReinstateSelector.VendorContext ctx = selector.loadVendorContext(dto);
        hcfReact.reactivateFacilities(ctx.facilities, res);
        hcfReact.reactivateLocations(ctx.locations, res);
        hcpfReact.reactivate(ctx.hcpfs, res);
        infoReact.reactivateForLocations(ctx.infoCodesByLoc, res);
        caseDataMgr.stampReinstateFlags(res);
    }
}
```

### 6.4 `PRM_ReinstatePracticeLocationService` (the simple one)

> **Why we need it** — The Practice Location reinstate flow (`PRM_ReinstatePracticeLocation`, 12 elements) is the smallest of the three but suffers from the same scaffolding problem as the Practitioner flow — every reactivation step is a separate IP element with its own DR Post. A 5-element fan-out (Account → HCF → HCPF → HCFN → Identifier) takes 12 IP elements because each fan-out step needs a Conditional + DR Post pair.
>
> **How it helps** — A single thin orchestrator that calls the same reactivator services used by `PRM_ReinstatePractitionerService` — `PRM_HCFReactivator`, `PRM_HCPFReactivator`, `PRM_HCFNReactivator`, `PRM_InfoCodeReactivator`, `PRM_ProviderFeatureReactivator`. The Practice Location scope is just a different entry point with different inputs; the actual reactivation logic is shared. Composition, not duplication.
>
> **Outcome** — 12 IP elements → ~80 lines. Reuses 5 reactivator services with the Practitioner flow — any reactivator bug fix benefits all 3 scopes simultaneously.

```apex
public with sharing class PRM_ReinstatePracticeLocationService extends PRM_BaseService {

    @TestVisible private PRM_ReinstateSelector              selector;
    @TestVisible private PRM_HCFReactivator                 hcfReact;
    @TestVisible private PRM_HCPFReactivator                hcpfReact;
    @TestVisible private PRM_InfoCodeReactivator            infoReact;
    @TestVisible private PRM_LocationNPIHistoryService      npiSvc;
    @TestVisible private PRM_CaseDataMgrService             caseDataMgr;

    public override String serviceName() { return 'ReinstatePracticeLocation'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        ReinstatePracticeLocationDTO dto = ReinstatePracticeLocationDTO.fromRequest(req);
        ReinstateResult res = new ReinstateResult();

        PRM_ReinstateSelector.LocationContext ctx = selector.loadPracticeLocationContext(dto.locationId);

        res.caseId = PRM_CaseService.createCase(CaseFactory.forReinstateLocation(dto));
        if (dto.hasNote()) PRM_NoteService.createCaseNote(res.caseId, dto.note());

        hcfReact.reactivateLocations(new List<Location>{ ctx.location }, res);
        hcfReact.reactivateAddresses(ctx.addresses, res);
        npiSvc.reactivateOpenPeriod(dto.locationId, res);
        infoReact.reactivateByLocation(dto.locationId, res);
        hcpfReact.reactivate(
            PRM_ReinstateTransformer.shapeHCPFForReactivate(ctx.hcpfs), res);
        caseDataMgr.stampReinstateFlags(res);

        return PRM_ServiceResponse.ok(res.toMap());
    }
}
```

### 6.5 `PRM_ReinstatePractitionerAsyncJob` (Queueable for TX2)

> **Why we need it** — A practitioner reinstate fan-out can touch 25+ HCPFs × multiple HCFNs each × per-row identifiers + taxonomies + board certs + info codes + provider features — easily 100+ DML rows in a single submit. Today the Practitioner Reinstate runs entirely synchronously; "Apex CPU time limit exceeded" is a known production failure mode for high-affiliation practitioners.
>
> **How it helps** — A Queueable that re-instantiates `PRM_ReinstatePractitionerService` and replays the heavy work in a fresh governor context. The decision is centralized in `PRM_GovernorUtil.shouldDelegateAsync(estimatedRowCount)` — the same predicate used by Off Cycle Submit / PDA Review for consistency. On completion publishes `PRM_AsyncComplete__e` with the case id; the Reinstate LWC bell receives the success/failure event without polling.
>
> **Outcome** — User receives caseId in <600 ms regardless of affiliation count. Heavy work commits in TX2 with a fresh budget. CPU-exceeded errors on high-affiliation practitioners eliminated.

```apex
public class PRM_ReinstatePractitionerAsyncJob implements Queueable {
    private final ReinstatePractitionerDTO dto;
    private final ReinstateResult res;

    public PRM_ReinstatePractitionerAsyncJob(ReinstatePractitionerDTO dto, ReinstateResult res) {
        this.dto = dto;
        this.res = res;
    }

    public void execute(QueueableContext ctx) {
        PRM_TransactionContext.start('ReinstatePractitioner-Async', dto.requestId());
        try {
            new PRM_ReinstatePractitionerService().runHeavyDml(dto, res);
        } catch (Exception e) {
            PRM_ErrorLogger.logException(e, dto.context());
            res.errors.add(e.getMessage());
        } finally {
            EventBus.publish(new PRM_AsyncComplete__e(
                JobName__c   = 'ReinstatePractitioner',
                ContextId__c = res.caseId,
                Success__c   = res.errors.isEmpty(),
                Payload__c   = JSON.serialize(res.toMap())
            ));
        }
    }
}
```

---

## 7. Sequence Diagram (target state — Practitioner scope, async path)

```
User       OS:ReinstateForm     ServiceDispatcher     PractitionerSvc        Reactivators          AsyncJob              DB
 │              │                       │                    │                      │                    │                │
 │ Open form    │                       │                    │                      │                    │                │
 │─────────────►│                       │                    │                      │                    │                │
 │              │ invoke('ReinstateFormFetch') (via PRM_ReinstateUtils)             │                    │                │
 │              │                       │                    │                      │                    │                │
 │              │ ◄─── HPF list ────────│                    │                      │                    │                │
 │ ◄── prefilled│                       │                    │                      │                    │                │
 │ Pick rows /  │                       │                    │                      │                    │                │
 │ Yes/No flags │                       │                    │                      │                    │                │
 │ Submit       │                       │                    │                      │                    │                │
 │─────────────►│ invoke('ReinstatePractitioner')            │                      │                    │                │
 │              │ ─────────────────────►│ ─────────────────► │                      │                    │                │
 │              │                       │                    │ TX1 sync (Case + Acct + Note)              │                │
 │              │                       │                    │─────────────────────────────────────────────────────────►│
 │              │                       │                    │ enqueue(PRM_ReinstatePractitionerAsyncJob)                 │
 │              │ ◄─────────────────────│ ◄──────────────── │ {caseId, status:'queued'}                  │                │
 │ ◄── caseId ──│                       │                    │                      │                    │                │
 │              │                       │                    │                      │ runHeavyDml        │                │
 │              │                       │                    │                      │ ┌─partitioner──┐   │                │
 │              │                       │                    │                      │ │ 5 buckets    │   │                │
 │              │                       │                    │                      │ └──────────────┘   │                │
 │              │                       │                    │                      │ ┌─reactivators(9)──┐                │
 │              │                       │                    │                      │ │ partial-success  │ ──────────────►│
 │              │                       │                    │                      │ └──────────────────┘                │
 │              │                       │                    │                      │ caseDataMgr        │                │
 │              │                       │                    │                      │───────────────────►│                │
 │              │                       │                    │                      │ EventBus.publish(PRM_AsyncComplete) │
```

---

## 8. Governor / Performance Comparison

### Practitioner flow (Flow A — worst case)

| Limit | Today (72-elt IP) | After refactor (TX1) | After refactor (TX2 Queueable) |
|---|---:|---:|---:|
| SOQL queries | ~30 (each DR Extract + per-loop reads) | 6 | 10 |
| DML statements | ~18 (one per DR Post + per-bucket setvalue) | 3 | 9 |
| DML rows | 150–300 | 4 | 150–300 (partial-success) |
| CPU time (ms) | 4,000–7,500 (5 loops × 3 conditionals × 200 rows = ~3,000 evaluations) | < 600 | renewed |
| Heap | 4–7 MB | < 700 KB | renewed |
| Remote Action calls | 3 (`RAToTransformNetworkTaxonomyRecords`, `RAToTranformPractPracRecords`, `CreateNote`) | 0 | 0 |

The **biggest win** is killing the 45-element loop scaffold — Apex `Map`-based partitioning is O(n) and uses constant heap, vs. the IP's nested loops which re-evaluate conditionals per row per pass.

### Vendor flow (Flow C — the >10 path, today already partly Apex)

| Limit | Today (RA → Batch) | After refactor |
|---|---:|---:|
| Round-trip Remote Action → Database.executeBatch | 1 | 0 (direct invocation) |
| Token / payload overhead | ~5 KB (RA argument marshalling) | 0 |
| Batch class behaviour | unchanged | unchanged |

The Vendor flow gets a tiny win — just removes the Remote Action round-trip — but it's important for **consistency**: every reinstate path now goes through `PRM_ServiceDispatcher`.

---

## 9. Migration Plan

### 9.1 Sequencing

1. Par Form → PDA Review → Off Cycle Submit → Off Cycle PDA Review services land.
2. **Reinstate services land** — needs all the above services on the shelf (Case, Note, Identifier, Account, CaseDataMgr, Taxonomy).
3. The 3 existing Apex classes (`PRM_ReinstateVendorAccountBatch`, Helper, `PRM_ReinstateUtils`) are **kept verbatim** — only their *invocation* changes.
4. Side-by-side under flag `PRM_FeatureConfig.Reinstate_UseApexService` per scope (Practitioner / PracticeLocation / Vendor).
5. Retire **8 IPs + ~22 DataRaptor bundles + 3 Remote Action methods** after burn-in.

### 9.2 Components to retire after migration

| Type | Names |
|---|---|
| **Integration Procedures (8)** | `PRM_ReinstateRecordCreationParent`, `PRM_ReinstateRecordCreation`, `PRM_ReinstatePracticeLocationParent`, `PRM_ReinstatePracticeLocation`, `PRM_PractitionerReinstateVendorParent`, `PRM_PractitionerReinstateVendorUpdate`, `PRM_ValidateDuplicateTaxonomyReinstate`, `PRM_SetSelectAllReInstate` |
| **DataRaptors — Post (~12)** | `PRMUpdateHealthCareDetailsReinstate`, `PRMReinstatehealthcareFacilityUpdate`, `PRMReinstateBoardCertsUpdate`, `PRMReinstateInfoCodeAssignmentUpdate`, `PRMReinstateHealthcareProviderTaxonomyRecordUpdate`, `PRMLoadOffCycleCaseCaseMgrReinstate`, `PRMLoadReinstatePractPracLoc`, `PRMDRToUpdateRecordsAfterReInstate`, `PRMDRHCFacilityNetworkForReInstate`, `PRMDRPCaseManagerCaseAccount` (vendor), `PRMDRPHcProviderIdentifier`, `PRMDRPInfoCodeProgPart` |
| **DataRaptors — Extract (4)** | `PRMDRExtractHPFReinstate`, `PRMGetReInstateData`, `PRMFetchCaseManagerReinstate`, `PRMDRReinstateFetchPractitionerTaxonomy`, `PRMDRToExtractDataFromCaseManagerToUpdateReInstate`, `PRMDREHcProviderIdentifier` |
| **DataRaptors — Transform (6)** | `PRMDRTransformReinstateAll`, `PRMTransformReInstateTables`, `PRMDRTPracLocAssociationReinstate`, `PRMDRTPracLocDataForReinstate`, `PRMDRTransformVendorReinstateAll` |
| **Remote Action methods (3)** | `PRM_OmniUtils` reinstate variants of `cloneBasisMultipleRole` (call site), `cloneHCFNRecords` (call site), `createNoteMulti` (call site) |
| **Existing Apex (1)** | `PRM_ReinstateCallable` (the bridge to the batch — no longer needed) |

> **Kept verbatim**: `PRM_ReinstateVendorAccountBatch`, `PRM_ReinstateVendorAccountBatchHelper`, `PRM_ReinstateUtils`, `PRM_ReinstatePracticeLocationWrapper`, LWC `prmReinstatePractitionerPracticeLocation`.

### 9.3 Test Strategy

| Layer | Tests |
|---|---|
| `PRM_ReinstateRowPartitioner` | exhaustive pure-function tests — feed rows with every combination of (`ReinstateAs`, `Update`) and assert the 3 buckets. The single hardest piece of logic, so test-heavy. |
| Reactivators | unit tests with `PRM_TestDataFactory` — verify each SObject's update fields (`PRM_Active__c=TRUE`, `EffectiveTo=NULL`, etc.) per scope |
| Selectors | unit tests — SOQL shape & filters for each fetch |
| `PRM_ReinstatePractitionerService` | E2E test per scope: small / medium / large practitioner — assert TX1 + TX2 record sets |
| `PRM_ReinstateVendorAccountService` | E2E tests for both branches (≤10 sync / >10 batch) — the >10 test just enqueues `PRM_ReinstateVendorAccountBatch` and asserts the existing batch test passes |
| `PRM_ReinstateVendorAccountBatch` | **Existing test class unchanged** — `PRM_ReinstateVendorAccountBatchTest` continues to pass |
| OmniScript | one OS-level test per of the 3 flows — assert JSON contract unchanged |

### 9.4 Feature Flag Rollout

```
PRM_FeatureConfig__mdt.Reinstate_Practitioner_UseApexService     (Boolean, default false)
PRM_FeatureConfig__mdt.Reinstate_PracticeLocation_UseApexService (Boolean, default false)
PRM_FeatureConfig__mdt.Reinstate_Vendor_UseApexService           (Boolean, default false)
PRM_FeatureConfig__mdt.Reinstate_AsyncThresholdRows              (Integer, default 100)
```

Each scope can be cut over independently — the smallest (`PracticeLocation`) goes first to validate the framework, then `Practitioner`, then `Vendor`. The Vendor cutover is the safest because the heaviest path (`>10 locations`) already runs in Apex; the cutover only changes the *invocation*.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| The 45-element bucket-sort logic is the most-loaded inference path — getting one row into the wrong bucket silently corrupts data. | `PRM_ReinstateRowPartitioner` is built **test-first** with property-based tests (run every (`reinstateAs`, `update`) combination). Dual-write under the flag for 2+ sprints and compare row sets bit-identically. |
| Reactivators all touch overlapping fields (`PRM_Active__c`, `IsActive`, `EffectiveTo`). A typo on one reactivator silently misses an UPDATE. | Each reactivator has its own field-list test that compares against a **golden record** snapshot captured from a successful legacy reinstate. Field-list regression suite runs in CI. |
| `PRM_ReinstateVendorAccountBatch` is invoked from two places after migration (legacy IP path during flag-off + new Apex service during flag-on). | Wrap the constructor with a `Source__c` parameter (`'IP'` / `'Apex'`) so logs can attribute each batch run. Same `executeBatch(...)` call, just an attribution tag. |
| `PRM_ReinstateCallable` retirement may break any external integration that calls it (e.g. a Flow). | Search the org for all `Callable` references via `apex:invocable` and the OS RemoteAction registry before retirement. The Callable's only known caller is `RA_CallBatch` in the Vendor IP, which is removed in the same release. |
| The Practitioner flow's `PRM_ProviderFeature__c` reactivator overlaps with the Off Cycle Submit's `PRM_OffCycleAddressService.insertProviderFeatures(...)` | Both classes call the same underlying `PRM_DMLUtil.upsertPartial(...)` — there is no shared state. Tests verify both paths produce identical results when the same input is given. |
| Existing AuraEnabled `PRM_ReinstateUtils.fetchPractitionerPracticeLocation` is called by the LWC — refactoring it could break the form load. | **Don't refactor it**. Optionally, internally delegate to `PRM_HCPFSelector.byPractitionerInactive(...)` after the selector lands, but the AuraEnabled signature stays identical. |
| `PRM_ValidateDuplicateTaxonomyReinstate` IP validation today blocks submission — moving it into `PRM_TaxonomyReactivator.validateNoDuplicates()` must preserve the exact validation message text the form displays. | Validation runs inside `processSync()` before any DML; on failure throws `PRM_ValidationException` whose `getMessage()` matches the legacy IP error response exactly. Tests assert the message text. |
| The flow's loop ordering matters for `LocationNPIHistory` (close-prior must happen before open-new). | `PRM_HCFReactivator` and `PRM_LocationNPIHistoryService` enforce ordering inside a single `Database.upsert(allOrNone=false)` call with the prior period and new period sharing the same Location key. |

---

## 11. Acceptance Criteria

1. All 8 Reinstate IPs shrink to 3 elements each (SetValues → ServiceInvoker → Response).
2. For every combination of (`ReinstateAs × Update × Scope`), the row set produced by the legacy IP and the Apex service are **bit-identical** under dual-write — verified by a regression suite over 50+ captured production payloads.
3. Practitioner worst-case (200 row reinstate) returns from the **synchronous** request in **< 700 ms** Apex CPU.
4. Async TX2 completes in **< 60 seconds** for that worst case, with `PRM_AsyncComplete__e` fired.
5. Vendor >10-location path continues to use `PRM_ReinstateVendorAccountBatch` with **no behaviour change** — existing `PRM_ReinstateVendorAccountBatchTest` passes unchanged.
6. PracticeLocation flow stays fully sync, completes in **< 300 ms**.
7. Zero changes required to the 3 OmniScript JSON contracts or to the LWC `prmReinstatePractitionerPracticeLocation`.
8. Coverage ≥ 90% on every NEW class and ≥ 80% on each EXTENDED service.
9. Each of the 3 feature flags (`Reinstate_Practitioner_*`, `Reinstate_PracticeLocation_*`, `Reinstate_Vendor_*`) cleanly reverts to the legacy IP path independently.
10. Total new Apex LoC ≤ 1,400 across all 14 NEW + 2 EXTEND classes (excluding tests).

---

## 12. Net new vs reused — one final view

| Category | Net new code in *this* migration |
|---|---|
| Selectors | **1** (`PRM_ReinstateSelector` — bulk façade) |
| Transformers | **2** (`PRM_ReinstateTransformer`, `PRM_ReinstateRowPartitioner` — the latter is the biggest win) |
| Orchestration services | **3** (one per scope) |
| Reactivators | **8** (small, single-SObject focused) |
| Helpers / Async | **1** (`PRM_ReinstatePractitionerAsyncJob`) |
| Extensions | **2** (`PRM_TaxonomyReactivator` extends Taxonomy svc, `PRM_IdentifierReactivator` extends OffCycle Identifier svc) |
| **Kept verbatim (already exists in org)** | **`PRM_ReinstateVendorAccountBatch` + Helper + `PRM_ReinstateUtils` + Wrapper + LWC** (~750 LoC of Apex that doesn't need to be rewritten) |
| **Approximate new LoC** | ~1,300, plus ~1,600 of test code |

Everything else — Case management, identifiers, notes, account updates, taxonomy effective-date logic, HCFN bulk DML, etc. — is **already on the shelf** after the previous four migrations.

---

## 13. Cross-references

- Generic framework: [`PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md)
- Par Form (creation): [`PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`](./PNM_ParForm_RecordCreation_Apex_Service_Architecture.md)
- PDA Review (initial cred): [`PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md`](./PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md)
- Off Cycle Submit: [`PNM_OffCycle_Process_Apex_Service_Architecture.md`](./PNM_OffCycle_Process_Apex_Service_Architecture.md)
- Off Cycle PDA Review: [`PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`](./PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md)







