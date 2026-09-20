# PNM Off Cycle Process — Apex Service Architecture

## IP Audit, Reusability Matrix & New Service Blueprint (Submit Flow)

> **Companion docs**
> - `PNM_Apex_Service_Architecture.md` — generic SOA framework (Dispatcher / BaseService / DMLUtil / Selectors / Async).
> - `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` — Practitioner Participation Form migration (the proven model — most reusable services originate here).
> - `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` — Initial Cred PDA Review/Update migration (where the post-committee patterns originate).
>
> This document does the same element-by-element audit for the **Off Cycle Submit** guided flow (`PRM_OffCycleCredentialing_English`) — i.e. the path the user takes when an existing practitioner needs an out-of-cycle change such as **Role Change**, **Specialty Change**, **New Region**, **New State**, **Demographics / Name Change**, **Address Change**, **Add Group / NPI**, **Reinstate**, or **Term**. The focus is **reuse first, build new only where the Off Cycle domain genuinely differs**.
>
> The post-committee path (PDA Review of an Off Cycle case) is a separate document: `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`.

---

## 0. TL;DR

| | Par Form (creation) | PDA Review (post-commit) | **Off Cycle Submit** |
|---|---|---|---|
| Trigger | New practitioner / new group | Committee outcome on an open case | An *already-credentialed* practitioner needs a mid-cycle change |
| Entry IP | `PRM_CreateParFormRecordsContainer` | `PRM_InitialCredPDAReviewUpdateParent` | **`PRM_OffCycleRecordCreationParent`** |
| Orchestrator IP | `PRM_CreateParFormRecords` | `PRM_InitialCredPDAReviewUpdate` | **`PRM_OffCycleRecordCreation`** (40 elements) |
| Heaviest IP | `PRM_CreatePractitionerAddressRecords` (80+) | `PRM_InitialCredPDAReviewUpdateSubIPInsert` (29) | **`PRM_OffCycleRecordCreation`** (40) + **`PRM_FetchOffCycleDetails`** (34) for read |
| Companion fetch IP | `PRM_FetchFormParForm*` | `PRM_FetchFormPDAReview` | **`PRM_FetchOffCycleDetails` / `PRM_FetchOffCycleDetailsParent`** |
| Address validation | Inline DR Transforms | (reuse Par Form transforms) | **`PRM_OffCycleAddressPrep`** (7) + **`PRM_OffCyclePreciselyAPI`** (11) — same Precisely contract as Par Form |
| Variant axis | Net-new practitioner type | PDA Outcome (Approve / Reroute / NetworkQC) | **`OffCycleRequestType`** picklist (Role / Specialty / New State / New Region / Name / Demographics / Address / Reinstate / Term / Group-NPI) |
| DML pattern | Mostly **INSERT** | INSERT (PNC/HCFN/InfoCode) + UPDATE (~12 SObjects) | **Mixed** — INSERT new HCF/HFN/HCPF/HCPT for changes, UPDATE Account/Identifier/HCPF for demographics, plus historical NPI rows |
| Reusable framework code | — | ~70% from Par Form | **~75%** from Par Form + PDA Review combined |
| Net-new services needed | — | ~6 PDA-specific | **~7 Off-Cycle-specific** services + **2 selectors** + **1 Precisely adapter reuse** |

---

## 1. Current State: Complete IP Chain Audit

### 1.1 Full IP Orchestration Chain (As-Is)

```
OmniScript: PRM_OffCycleCredentialing_English   (active v58 — main submit flow)
            PRM_OffCycleVerification_English    (active v36 — internal verification mid-flow)
   │
   │  Step 1 (Load):  IP_FetchOffCycleDetailsParent ──► PRM_FetchOffCycleDetails
   │                     (loads HCF / HCPF / HFN / Address / Identifier in one shot
   │                      — used by the OS to hydrate the form)
   │
   │  Step 2 (Address validation, called multiple times during the flow):
   │                  IP_OffCycleAddressPrep ──► (DR Transforms × 4 + LA merge)
   │                  IP_OffCyclePreciselyAPI ──► Precisely USPS callout (loops
   │                                              over Primary + Mailing + Billing
   │                                              + each Additional Address)
   │
   │  Step 3 (Submit): IP_OffCycleRecordCreationParent
        │
        ▼
IP: PRM_OffCycleRecordCreationParent  (Container — v1)
  ├── SV_SourceIPDetails ........................ Set Values (source tracking)
  ├── TryCatchBlock ............................. Error boundary
  │     remoteClass = PRM_OmniUtils
  │     remoteMethod = logTryCatchException
  │     └── IP_OffCycleRecordCreation .......... Calls child orchestrator ─────────┐
  │           failureConditionalFormula:                                            │
  │              %success% == false                                                 │
  └── ResponseAction ............................ Final response                    │
                                                                                    │
┌──────────────────────────────────────────────────────────────────────────────────┘
│
▼
IP: PRM_OffCycleRecordCreation  (Orchestrator — active v18, 40 elements)
  ├── [01] DRLoadOffCycleCaseCaseMgr ............ DR Post: PRMLoadOffCycleCaseCaseMgr
  │            Creates IndividualApplication (case manager) row + links Case
  │            Always runs (no executionConditionalFormula).
  │
  ├── [02] DRCreateIdentiferAndDocument ......... DR Post: PRMDRCreateIdentiferAndDocument
  │            Inserts Identifier + ContentDocumentLink for the uploaded file
  │            FormProcess = "Off-Cycle Request",  DocumentType = "Role Change"
  │            Cond: ISNOTBLANK(%ContentDocumentId%)
  │
  ├── [03] ContactsToUpdate ...................... Set Values
  │            Filters %ContactInfo% to only contacts whose name / phone /
  │            email / role / website / contact-person-role changed.
  │
  ├── [04] DRLoadAccountDetails .................. DR Post: PRMLoadAccountDetails
  │            UPSERTS contact-side Account rows (PersonAccount of type
  │            "Medical Service Vendor") for the changed contacts.
  │            Cond: ISNOTBLANK(%ContactsToUpdate:ContactList%)
  │
  ├── [05] DREExistingNPI ........................ DR Extract: PRMDRGetExistingGroupNPI
  │            Looks up an existing Group NPI to detect dup before creating.
  │            Cond: ISNOTBLANK(%PractitionerGroup:GroupInformation:GroupNPI%)
  │
  ├── [06] DRCreateGroupRecords .................. DR Post: PRMCreateGroupRecordsForOffCycle
  │            Creates Vendor Account + Group Identifier + HealthcareProviderNpi
  │            (the practitioner GROUP — not the practitioner-level NPI).
  │            Cond: ISNOTBLANK(%PractitionerGroup:GroupInformation%)
  │
  ├── [07] SpecialtyChange ....................... CB (Conditional Block)
  │     Cond: ISNOTBLANK(%CollectAndVerifyNewInformation:Additional Specialties%)
  │     │
  │     └── [07.1] DRLoadPersonEducations ........ DR Post: PRMLoadPersonEducations
  │                  Creates PersonEducation rows for the new degree(s)
  │                  Cond: ISNOTBLANK(%PersonEducation:Degree%)
  │
  ├── [08] AdditionalAddressBlock ................ CB
  │     Cond: ISNOTBLANK(%AdditionalAddress|1:AddLine1%)
  │            || ISNOTBLANK(%NewPracticeForExisitingGrp%)
  │     │
  │     ├── [08.1] LAAdditionalAddressToCreate ... List Action (filter NewAdditionalAddress=true)
  │     │           merges AdditionalAddress + NewPracticeForExisitingGrp
  │     │
  │     └── [08.2] TransformOffCycleAddressForCreation ... DR Transform:
  │                  PRMTransformOffCycleAddressForCreation
  │                  Converts the merged additional addresses into
  │                  Location/HCF/HCPF/Address-shaped objects.
  │
  ├── [09] TransformPrimaryAddressForCreation .... DR Transform:
  │            PRMTransformPrimaryAddressForOffCycle
  │            Same shape transform for the Primary Practice address.
  │            Cond: ISNOTBLANK(%PrimaryPractice%)
  │
  ├── [10] LAMergePrimaryAdditionalAddresses ..... List Action
  │            Merges Primary + Additional into one address list (the
  │            payload for the big DR below).
  │
  ├── [11] DRExtractHealthcareProviderNPIData .... DR Turbo (INACTIVE — kept
  │            for legacy lookup; new flow gets NPI from upstream wrapper)
  │
  ├── [12] DRPHCPractFacHCFacilityLocationAddress  DR Post:
  │            PRMDRPHCPractFacHCFacilityLocationAddress
  │            **The big one** — for each new address row creates:
  │                Location, HealthcareFacility, HealthcarePractitionerFacility,
  │                Address (PRM_AddressLine1, PRM_City, ...), and links them
  │                to VendorAccount + PractitionerAccount.
  │            Picks payload based on whether group is existing or new:
  │              IF ExistingGroupId  → TransformOffCycleAddressForCreation
  │              ELSE                → LAMergePrimaryAdditionalAddresses
  │            Cond: complex (see element JSON)
  │
  ├── [13] TransformAddressDataForHFNRecordsCreation ... DR Transform:
  │            PRMDRTransformHCFData (shapes HCF/HCFN payload)
  │
  ├── [14] TransformPFAAData ..................... DR Transform: PRMDRTransformPFAA
  │            Converts CapabilitiesAtLocation → ProviderFeature payload
  │            Cond: ISNOTBLANK(%TransformAddressDataForHFNRecordsCreation
  │                              :FacilityNetworkData:CapabilitiesAtLocation%)
  │
  ├── [15] CreatePFAssitiveAids .................. DR Post:
  │            PRMDRCreateProviderFeatureAssitiveAids
  │            Inserts PRM_ProviderFeature__c rows for the practice
  │            location's assistive-aid capabilities.
  │            Cond: ISNOTBLANK(%TransformPFAAData:ProviderFeature%)
  │
  ├── [16] PracFacilitiesForExistingAddresses .... CB
  │     Cond: %PractitionerGroup:GroupInformation:ExistingGroupSelected% == true
  │     │
  │     ├── [16.1] SetPrimaryFacilityFlag ........ Set Values (IsPrimary)
  │     ├── [16.2] SVAdditionalAddress ........... Set Values
  │     │            wraps AdditionalFacilityDetails into a list
  │     ├── [16.3] LAExistingAddressMerge ........ List Action
  │     │            merges PrimaryFacilityDetails + AdditionalFacility
  │     │
  │     ├── [16.4] DRLoadPractitionerFacilities .. DR Post: PRMLoadPractitionerFacilities
  │     │            Inserts NEW HealthcarePractitionerFacility rows linking
  │     │            the existing locations to the practitioner.
  │     │            Cond: ISNOTBLANK(%LAExistingAddressMerge|1:AddLine1%)
  │     │
  │     ├── [16.5] PRMDREOffcycleNPIHistory ...... DR Extract: PRMDREOffcycleNPIHistory
  │     │            Loads the latest LocationNPIHistory rows for the merged
  │     │            facilities so we can update them.
  │     │
  │     └── [16.6] PRMDRPOffCycleExistingFacilityNPIUpdate ... DR Post:
  │                  PRMDRPOffCycleExistingFacilityNPIUpdate
  │                  Updates existing HCF + LocationNPIHistory with the
  │                  new NPI / EffectiveDate the user picked.
  │
  ├── [17] RoleSpecialtyNewStateRegionChangeBlock  CB
  │     Cond: OffCycleRequestType LIKE
  │              "Role Change" | "Specialty Change" | "New State" | "New Region"
  │     │
  │     ├── [17.1] DRTNewRegionStateData ......... DR Transform: PRMDRTNewStateRegion
  │     │            Builds NRSNetworkList payload (Pending=TRUE, IsActive=FALSE)
  │     │            Cond: NewState | NewRegion
  │     │
  │     ├── [17.2] DRTSpecialtyData .............. DR Transform: PRMDRTSpecialtyData
  │     │            Builds SpecialtyRoleList payload from
  │     │            %SpecialtyNetworkList%
  │     │            Cond: SpecialtyChange
  │     │
  │     ├── [17.3] RA_CloneBasisMultipleRole ..... Remote Action
  │     │            remoteClass = PRM_OmniUtils
  │     │            remoteMethod = cloneBasisMultipleRole
  │     │            For Specialty / New State / New Region — explodes
  │     │            multi-role rows into one row per role.
  │     │            Cond: SpecialtyChange | NewState | NewRegion
  │     │
  │     ├── [17.4] SetValues ..................... Set Values
  │     │            HFNetworkList = MERGE(RC list, SP/NRS list)
  │     │
  │     ├── [17.5] GetHFNTaxonomy ................ DR Turbo: PRMGetHCFacilityNetworks
  │     │            Loads existing HCFN by RecordType into FacilityTaxonomy
  │     │            and FacilityTxnNetwork buckets.
  │     │            Cond: ISNOTBLANK(FILTER(SetValues:HFNetworkList,
  │     │                                    'ISNOTBLANK(PracticeLocationId)'))
  │     │
  │     ├── [17.6] RA_CloneHCFNPractitionerFacTxnNw ... Remote Action
  │     │            remoteClass = PRM_OmniUtils
  │     │            remoteMethod = cloneHCFNRecords
  │     │            Clones existing HCFN rows for the practitioner so we
  │     │            can produce the practitioner-side network rows.
  │     │
  │     ├── [17.7] PRMDRPHCFNetwork .............. DR Post: PRMDRPHCFNetwork
  │     │            Inserts the cloned HCFN rows (Pending=true).
  │     │            Cond: ISNOTBLANK(%PractFacilityTxnNw%)
  │     │
  │     ├── [17.8] RACreateTaxonomy .............. Remote Action
  │     │            remoteClass = PRM_FetchOffCycleCredUtility
  │     │            remoteMethod = CreateHealthCareProvTaxonomy
  │     │            Inserts HealthcareProviderTaxonomy rows for the
  │     │            practitioner's new taxonomies (per role/specialty).
  │     │
  │     └── [17.9] PRMDREExpediatedAccount ....... DR Turbo: PRMDREExpediatedAccount
  │                  Side-effect: marks Account as Expedited if applicable.
  │
  ├── [18] CBForDuplicateHCPF .................... CB
  │     Cond: ISNOTBLANK(%PractitionerGroup:GroupInformation%)
  │     │
  │     ├── [18.1] DRExtractExistingHCPF ......... DR Turbo: PRMDRExtractExistingHCPF
  │     │            Looks up existing HCPF for (Practitioner × Vendor) to
  │     │            decide if we need to insert / reactivate.
  │     │
  │     └── [18.2] DRCreateHCPFForPractitionerPracAffiliation ... DR Post:
  │                  PRMDRCreateHCPFForPractitionerPracAffiliation
  │                  Inserts the **practitioner-to-vendor** affiliation row
  │                  (or reactivates the existing inactive one).
  │                  Cond: existing.IsActive == false || existing is blank
  │
  ├── [19] DRLoadOffCycleCaseMgrDatMgr ........... DR Post: PRMLoadOffCycleCaseMgrDatMgr
  │            Updates IndividualApplication (CaseManager) with all the
  │            CaseDataManager flags telling downstream PDA which entities
  │            were touched (Account, Address, ContentVersion, HCF, HCFN,
  │            HCPF, HCPNPI, HPT, Identifier, Location, PersonAccount,
  │            PersonEducation, ProviderFeature). Also captures Primary
  │            and Secondary Contact Ids for the case.
  │
  └── [20] Response .............................. Final OS response

────────────────────────────────────────────────────────────────────────
SIBLING IPs (called from the OmniScript directly, not via the orchestrator):
────────────────────────────────────────────────────────────────────────

IP: PRM_OffCycleAddressPrep (active v5, 7 elements)
  ├── SetAddresses ............................... Set Values: pre-shapes
  │     PrimaryAddress / MailingAddress / BillingAddress / AdditionalAddress
  ├── DRTransformOffCycleAddressPrimary .......... DR Transform: PRMTransformOffCycleAddressTable
  ├── DRTransformOffCycleAddressBilling .......... DR Transform: PRMTransformOffCycleAddressTable
  ├── DRTransformOffCycleAddressMailing .......... DR Transform: PRMTransformOffCycleAddressTable
  ├── DRTransformOffCycleAddressAddtnl ........... DR Transform: PRMTransformOffCycleAddressTable
  ├── LAMergeAddresses ........................... merges all 4 lists
  └── ResponseAction
            (called BEFORE PRM_OffCyclePreciselyAPI — its job is to bring
             every address the user filled in into a single shape)

IP: PRM_OffCyclePreciselyAPI (active v5, 11 elements)
  ├── ConvertAdditionalAddresses ................. Set Values
  ├── DREnteredAddress ........................... DR Extract  (PRMDRNonParAddress)
  ├── AddressInput ............................... Set Values: builds the
  │                                                 Locations[].Addresses[]
  │                                                 payload for Precisely
  ├── PRMDRNonParAddress ......................... DR Post (?) NonParAddress
  ├── PreciselyAPICallout ........................ IP Action → PRM_IPContainerPreciselyAPICall
  │                                                 (the shared Precisely IP)
  ├── SetCounter ................................. Set Values
  ├── AdditionAdressLoop ......................... Loop Block over PreciselyAPICallout:Output
  │     ├── AdditionalAddressList ............... Set Values
  │     └── CountList ............................ Set Values
  ├── PRMDRAdditionAddressAPIResponse ............ DR Post (final shape)
  └── RAPreciselyResponse ........................ Remote Action (returns to OS)

IP: PRM_FetchOffCycleDetails / PRM_FetchOffCycleDetailsParent
    (active v18 / v1, 34 elements)
    Single-shot read used by the form on load:
      • FetchFormDetails (PRMFetchOffCycleDetails — bundles many SOQLs)
      • DRExtractAddressByLocation, DRExtractAssisstiveAids
      • Address bucket builders (LAAllAddress, LAPrimaryCheck, LABillAddress*,
        LAMailAddress*, SVFinalBillingMailingAddr)
      • DRTransformOffCycleAddressToVerify
      • LA_FacilityNetworkInfoCodes / DREFacilityNetworkInfoCodesData
      • DRTRoleSpecialtyNewRegionState (CB_RoleSpecialtyNewRegionStateChange)
      • RA_MergedBasisNetworks (PRM_OmniUtils.cloneBasisMultipleRole — for UI)
      • ExtractActiveIdentifierWithType
      • RAGetContentNote (PRM_OmniUtils.getContentNote)
```

### 1.2 Element Counts

| IP | Elements | Active Version | Type |
|---|---:|---|---|
| `PRM_OffCycleRecordCreationParent` | 4 | v1 | Container (TryCatch) |
| `PRM_OffCycleRecordCreation` | **40** | v18 | Orchestrator + the 80% of writes |
| `PRM_OffCycleAddressPrep` | 7 | v5 | Address shaping (sync helper) |
| `PRM_OffCyclePreciselyAPI` | 11 | v5 | Precisely USPS callout wrapper |
| `PRM_FetchOffCycleDetails` | 34 | v18 | Read-side aggregator |
| `PRM_FetchOffCycleDetailsParent` | 4 | v1 | Container (TryCatch) for the fetch |
| **Total** | **~100** | | |

---

## 2. Records Created / Updated by the Off Cycle Submit

The set is **mixed** (insert + update) and is driven by the `OffCycleRequestType` picklist. The orchestrator unconditionally writes Case + IndividualApplication + Identifier + ContentDocumentLink; everything else is conditional.

### 2.1 INSERT inventory (worst-case)

| # | SObject | Source DR / RA | Volume per submit | Notes |
|---|---|---|---:|---|
| 1 | `Case` | DRLoadOffCycleCaseCaseMgr | 1 | RecordType = OffCycleRequest |
| 2 | `IndividualApplication` (CaseManager) | DRLoadOffCycleCaseCaseMgr | 1 | one per case |
| 3 | `Identifier__c` | PRMDRCreateIdentiferAndDocument | 1 | FormProcess = "Off-Cycle Request" |
| 4 | `ContentDocumentLink` | PRMDRCreateIdentiferAndDocument | 1 | links uploaded ContentVersion |
| 5 | `Account` (PersonAccount — Contact) | PRMLoadAccountDetails | 0..N | only changed contacts |
| 6 | `Account` (Vendor — Group) | PRMCreateGroupRecordsForOffCycle | 0..1 | only when GroupInformation present and not existing |
| 7 | `Identifier__c` (Group NPI) | PRMCreateGroupRecordsForOffCycle | 0..1 | the new Group NPI |
| 8 | `HealthcareProviderNpi` (Group level) | PRMCreateGroupRecordsForOffCycle | 0..1 | |
| 9 | `PersonEducation` | PRMLoadPersonEducations | 0..N | only when SpecialtyChange has new degrees |
| 10 | `Location` | PRMDRPHCPractFacHCFacilityLocationAddress | 0..N | one per new practice address |
| 11 | `HealthcareFacility` | PRMDRPHCPractFacHCFacilityLocationAddress | 0..N | one per new practice address |
| 12 | `HealthcarePractitionerFacility` (HCPF) | PRMDRPHCPractFacHCFacilityLocationAddress | 0..N | links practitioner ↔ new HCF |
| 13 | `Address` | PRMDRPHCPractFacHCFacilityLocationAddress | 0..N | embedded in the same payload |
| 14 | `PRM_ProviderFeature__c` | PRMDRCreateProviderFeatureAssitiveAids | 0..N | one row per assistive-aid capability |
| 15 | `HealthcarePractitionerFacility` (existing-loc path) | PRMLoadPractitionerFacilities | 0..N | when GroupInformation is existing |
| 16 | `HealthcareFacilityNetwork` (HCFN) | PRMDRPHCFNetwork | 0..N | one per Role/Specialty/State/Region row, Pending=true |
| 17 | `HealthcareProviderTaxonomy` (HCPT) | RACreateTaxonomy (PRM_FetchOffCycleCredUtility.CreateHealthCareProvTaxonomy) | 0..N | one per (taxonomy × role × specialty) |
| 18 | `HealthcarePractitionerFacility` (PNC affiliation) | PRMDRCreateHCPFForPractitionerPracAffiliation | 0..1 | the practitioner ↔ vendor affiliation |
| 19 | `Note` (ContentNote) | (created via OS step + RA_GetContentNote on read) | 0..1 | optional case note |

### 2.2 UPDATE inventory

| # | SObject | Source | When | Notes |
|---|---|---|---|---|
| 1 | `Account` (PersonAccount — practitioner) | PRMDREExpediatedAccount | Expedite flag set | sets Expedited fields on practitioner Account |
| 2 | `Account` (Contact PersonAccount) | PRMLoadAccountDetails | Demographics / contact change | upserts |
| 3 | `Case` (link CaseManager) | DRLoadOffCycleCaseCaseMgr | always | populates IndividualApplicationId on Case |
| 4 | `IndividualApplication` (CaseManager) | PRMLoadOffCycleCaseMgrDatMgr | always (final element) | sets the 14 CaseDataManager flags |
| 5 | `HealthcareFacility` | PRMDRPOffCycleExistingFacilityNPIUpdate | existing-group path | NPI / EffectiveDate update |
| 6 | `LocationNPIHistory` | PRMDRPOffCycleExistingFacilityNPIUpdate | existing-group path | closes prior NPI period |
| 7 | `HealthcareFacility` (Pending flag) | PRMDRPHCFNetwork | Role / Specialty / State / Region | Pending=true / IsActive=false on related HCF |
| 8 | `HealthcareFacilityNetwork` (existing) | RA_CloneHCFNPractitionerFacTxnNw + PRMDRPHCFNetwork | when network rows already exist | clones + flags pending |

### 2.3 Off Cycle Request Types (variant axis)

| Request Type | Trigger condition (raw) | Drives elements |
|---|---|---|
| **Role Change** | `OffCycleRequestType` contains `"Role Change"` | [17.x] block, RoleChange list, taxonomy create |
| **Specialty Change** | `OffCycleRequestType` LIKE `"Specialty Change"` | [07] PersonEducation block, [17.2] DRTSpecialtyData, [17.3] cloneBasisMultipleRole, [17.6/17.7] HCFN clone+insert, RACreateTaxonomy |
| **New State** | `OffCycleRequestType` LIKE `"New State"` | [17.1] DRTNewRegionStateData, [17.6/17.7] HCFN clone+insert, RACreateTaxonomy |
| **New Region** | `OffCycleRequestType` LIKE `"New Region"` | same as New State |
| **Name Change / Demographics** | `CollectAndVerifyNewInformation` has changed name/contact rows | [03] ContactsToUpdate filter, [04] PRMLoadAccountDetails, Identifier rows for legal name |
| **Address Change** | new address rows in `AdditionalAddress` or `NewPracticeForExisitingGrp` | [08]/[09]/[10] address transforms, [12] big DR, [16] existing-facility branch |
| **Add Group / NPI** | `PractitionerGroup:GroupInformation` present | [05] DREExistingNPI, [06] PRMCreateGroupRecordsForOffCycle, [18] CBForDuplicateHCPF |
| **Reinstate** | RoleChange row with EffectiveDate present + practitioner currently inactive | reactivation path inside [16.6] / [17.7] (Pending=true) and Account un-Expedite |
| **Term** | RoleChange row with TerminationDate | UPDATE path on HCFN / HCPF (no insert) — handled in PDA review post-committee |

> Term is largely a **flag** at submit; the actual row deactivation happens in the **Off Cycle PDA Review** flow (separate doc).

---

## 3. Target Apex Service Architecture (Off Cycle Submit)

### 3.1 Layered Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│   OmniScript: PRM_OffCycleCredentialing_English / PRM_OffCycleVerification    │
│   Header IPs (kept as thin wrappers):                                         │
│       PRM_FetchOffCycleDetailsParent  → PRM_FetchOffCycleDetails              │
│       PRM_OffCycleAddressPrep                                                 │
│       PRM_OffCyclePreciselyAPI                                                │
│       PRM_OffCycleRecordCreationParent → PRM_OffCycleRecordCreation           │
└──────────────────────────────────────────────────────────────────────────────┘
                          │ vlocity_ins.VlocityOpenInterface2.invokeMethod()
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CONTROLLER LAYER  (REUSE — already in framework)                             │
│   • PRM_ServiceDispatcher              (registry: serviceName → BaseService)  │
│   • PRM_BaseService (Template Method, sync/async delegate)                    │
│   • PRM_ServiceRequest / PRM_ServiceResponse (DTO wrappers)                   │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER  (NEW — Off-Cycle-specific)                              │
│   • PRM_OffCycleSubmitService              (top-level orchestrator)           │
│       ├── PRM_OffCycleCaseService          (Case + IndividualApplication)     │
│       ├── PRM_OffCycleIdentifierService    (Identifier + ContentDocLink)      │
│       ├── PRM_OffCycleContactService       (Demographics / Name Change)       │
│       ├── PRM_OffCycleGroupService         (Vendor Account + Group NPI)       │
│       ├── PRM_OffCycleAddressService       (Location/HCF/HCPF/Address)        │
│       ├── PRM_OffCycleNetworkService       (HCFN + Taxonomy + clones)         │
│       ├── PRM_OffCycleAffiliationService   (HCPF practitioner-vendor link)    │
│       └── PRM_OffCycleCaseDataMgrService   (final flag stamping)              │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  SUPPORT LAYER  (mostly REUSE)                                                │
│   READ-side selectors (reuse from PDA + Par Form, plus 2 new):                │
│     ✔ PRM_AccountSelector            (REUSE)                                  │
│     ✔ PRM_HCFSelector                (REUSE)                                  │
│     ✔ PRM_HCPFSelector               (REUSE)                                  │
│     ✔ PRM_HCFNetworkSelector         (REUSE)                                  │
│     ✔ PRM_IdentifierSelector         (REUSE)                                  │
│     + PRM_LocationNPIHistorySelector (NEW — for [16.5])                       │
│     + PRM_OffCycleFormSelector       (NEW — single-shot form load)            │
│                                                                               │
│   Transformers (NEW — Off Cycle DTO shaping; replaces 7 DR Transforms):       │
│     • PRM_OffCycleAddressTransformer    (Primary + Additional + Mailing/Bill) │
│     • PRM_OffCycleNetworkTransformer    (NRS + SP + role explosion)           │
│     • PRM_OffCyclePFAATransformer       (capabilities → ProviderFeature)      │
│                                                                               │
│   External adapter:                                                           │
│     ✔ PRM_PreciselyAdapter            (REUSE — same as Par Form)              │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CROSS-CUTTING  (REUSE — framework)                                           │
│   • PRM_DMLUtil          (partial-success DML, allOrNone=false)               │
│   • PRM_CollectionUtil   (LA-merge / filter equivalents)                      │
│   • PRM_GovernorUtil     (sync / async decision)                              │
│   • PRM_ErrorLogger      (PRM_ExceptionLog__c + PRM_AsyncComplete__e)         │
│   • PRM_TransactionContext                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                          │  TX1 (sync)  /  TX2 (Queueable)
                          ▼
                 ┌────────────────────────┐
                 │  Database / Platform   │
                 └────────────────────────┘
```

### 3.2 Transaction Boundary

> The TX1 / TX2 split follows the framework's boundary doctrine ([§ 14.5 of `PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md#145-tx1--tx2-boundary-doctrine)): every record the next OmniScript screen reads, every record an Off-Cycle PDA reviewer reads on its critical path, and every record the directory exposes commits in TX1. Only true per-facility / per-network / per-role fan-out belongs in TX2.

| Phase | Transaction | Scope | Rationale |
|---|---|---|---|
| **TX1 — sync** | OS request | `Case`, `IndividualApplication`, `Identifier`, `ContentDocumentLink`, contact-side `Account` upsert, the Group `Account/Identifier/HCPNPI`, **`Location` + `Address` + `HealthcareFacility` + `HCPF`** (the 5-SObject "big DR" replacement, written via two stacked `PRM_BulkOperation.chain()` builders), existing-facility NPI rollover, and the TX1 CM-flag stamp `Status__c='Async-In-Flight'` via `PRM_CaseDataMgrPatcher`. | The Off-Cycle PDA reviewer reads `Location`/`HCFacility`/`HCPF`/`Address` on its critical path within minutes of submit; if those rows lived in TX2 the reviewer would see stale state. They commit sync. |
| **TX2 — async (Queueable)** | `PRM_OffCycleAsyncJob` | per-facility / per-network / per-role fan-out only — `PRM_ProviderFeature__c` (Assistive Aids), `HealthcareFacilityNetwork` (after role-explosion), `HealthcareProviderTaxonomy`, `Account.Expedited` flag, Affiliation HCPF clones (CBForDuplicateHCPF), and the TX2 CM-flag stamp `Status__c='Async-Complete'` with full per-bucket counts. | These rows balloon when Specialty/State/Region/Address combine (10s–100s of HCFN rows after role-explosion). Splitting protects the interactive request from the 200-row chunking. The async hand-off is gated by `PRM_AsyncEnqueueGuard.safeEnqueue(...)` so an exhausted Queueable cap falls back to inline rather than silently dropping. |

> **Pattern alignment**: Same TX-boundary doctrine as Par Form — TX1 owns everything the next reader (user or downstream flow) sees on its critical path; TX2 owns true fan-out.

### 3.3 OmniScript Dispatcher Wiring

`PRM_OffCycleRecordCreation` (the IP) is **kept as a 3-element shell**:

```
SetValues  →  IP Action: PRM_ServiceInvoker  →  ResponseAction
                 serviceName  = "OffCycleSubmit"
                 payload      = %ContextPayload%
```

`PRM_ServiceInvoker` is the existing generic IP that bridges into `PRM_ServiceDispatcher.invokeMethod('OffCycleSubmit', input, output, options)`. Same wiring used by Par Form and PDA Review.

The fetch IP becomes:
```
PRM_FetchOffCycleDetails  →  PRM_ServiceInvoker (serviceName="OffCycleFormFetch")
                                                 → PRM_OffCycleFormFetchService
```

The address IPs collapse into one Apex façade as well:
```
PRM_OffCycleAddressPrep + PRM_OffCyclePreciselyAPI  →  PRM_ServiceInvoker
                                                       (serviceName = "OffCycleAddressValidate")
                                                       → PRM_OffCycleAddressValidationService
                                                         (uses existing PRM_PreciselyAdapter)
```

---

## 4. Reusability Matrix — what survives, what extends, what's net new

Legend: **REUSE** = used as-is. **EXTEND** = subclass / add a method. **NEW** = build new.

### 4.1 Framework / Cross-cutting

| Class | Off Cycle disposition | Notes |
|---|---|---|
| `PRM_ServiceDispatcher` | **REUSE** | Add `OffCycleSubmit`, `OffCycleFormFetch`, `OffCycleAddressValidate` to registry |
| `PRM_BaseService` | **REUSE** | |
| `PRM_ServiceRequest` / `PRM_ServiceResponse` | **REUSE** | |
| `PRM_TransactionContext` | **REUSE** | |
| `PRM_DMLUtil` | **REUSE** | partial-success insert/update for HCFN, HCPF, Address, ProviderFeature |
| `PRM_CollectionUtil` | **REUSE** | replaces every LA Merge / Filter element |
| `PRM_GovernorUtil` | **REUSE** | governs the TX1→TX2 split |
| `PRM_ErrorLogger` | **REUSE** | the parent's TryCatchBlock collapses to a `try { ... } catch (Exception e) { PRM_ErrorLogger.logException(...); }` in `PRM_OffCycleSubmitService` |
| `PRM_AsyncJobBase` (Queueable parent) | **REUSE** | new `PRM_OffCycleAsyncJob` extends this |

### 4.2 Read-side Selectors

| Selector | Disposition | Replaces |
|---|---|---|
| `PRM_AccountSelector` | **REUSE** | the `PRMDREExpediatedAccount` lookup, contact-side Account fetch |
| `PRM_HCFSelector` | **REUSE** | `PRMDRExtractAddressByLocation`, the existing-facility lookups in the form fetch |
| `PRM_HCPFSelector` | **REUSE** | `PRMDRExtractExistingHCPF` |
| `PRM_HCFNetworkSelector` | **REUSE** | `PRMGetHCFacilityNetworks` |
| `PRM_IdentifierSelector` | **REUSE** | `ExtractActiveIdentifierWithType`, the active Group NPI lookup |
| `PRM_PersonEducationSelector` | **REUSE** | (from Par Form) |
| `PRM_LocationNPIHistorySelector` | **NEW** | replaces `PRMDREOffcycleNPIHistory` — small selector returning latest NPI period per Location |
| `PRM_OffCycleFormSelector` | **NEW** | one bulk façade that calls the above selectors in a single Apex transaction (replaces 18 of the 34 fetch-IP elements) |

### 4.3 Transformers (replace DR Transforms)

| New Apex transformer | Replaces |
|---|---|
| `PRM_OffCycleAddressTransformer` | `PRMTransformOffCycleAddressTable` (×4 in AddressPrep), `PRMTransformPrimaryAddressForOffCycle`, `PRMTransformOffCycleAddressForCreation`, `PRMDRTransformHCFData`, `LAMergeAddresses`, `LAMergePrimaryAdditionalAddresses` |
| `PRM_OffCycleNetworkTransformer` | `PRMDRTNewStateRegion`, `PRMDRTSpecialtyData`, the merge step `SetValues:HFNetworkList` |
| `PRM_OffCyclePFAATransformer` | `PRMDRTransformPFAA` |
| `PRM_OffCycleContactDeltaTransformer` | the `ContactsToUpdate` Set Values step (filters changed contact rows) |

### 4.4 External integration

| Class | Disposition | Notes |
|---|---|---|
| `PRM_PreciselyAdapter` | **REUSE** | the same callout used by Par Form. The Off Cycle flow's loop over Primary + Mailing + Billing + Additional collapses into a single `validateAddresses(List<AddressDTO>)` call. |
| `PRM_PreciselyResponseMapper` | **REUSE** | response decoder |

### 4.5 Domain / Orchestration services

| Service | Disposition | Source / replaces |
|---|---|---|
| `PRM_OffCycleSubmitService` | **NEW** | top-level orchestrator (replaces `PRM_OffCycleRecordCreation`) |
| `PRM_OffCycleCaseService` | **EXTEND** of `PRM_CaseService` (Par Form) | replaces `PRMLoadOffCycleCaseCaseMgr` + the final `PRMLoadOffCycleCaseMgrDatMgr` update |
| `PRM_OffCycleIdentifierService` | **EXTEND** of `PRM_IdentifierService` | replaces `PRMDRCreateIdentiferAndDocument`. Adds the FormProcess="Off-Cycle Request" branch. |
| `PRM_OffCycleContactService` | **NEW** | wraps `PRMLoadAccountDetails` for contact rows. Reuses `PRM_AccountUpsertHelper`. |
| `PRM_OffCycleGroupService` | **NEW** | wraps `PRMCreateGroupRecordsForOffCycle` (Vendor Account + Group Identifier + Group HCPNPI). Reuses `PRM_DMLUtil`. |
| `PRM_OffCycleAddressService` | **EXTEND** of `PRM_AddressService` (Par Form) | replaces `PRMDRPHCPractFacHCFacilityLocationAddress` (the big one), `PRMLoadPractitionerFacilities`, `PRMDRPOffCycleExistingFacilityNPIUpdate` |
| `PRM_OffCycleNetworkService` | **NEW** | replaces `cloneBasisMultipleRole`, `cloneHCFNRecords`, `PRMDRPHCFNetwork`, `CreateHealthCareProvTaxonomy`. The "role explosion" logic moves entirely into Apex. |
| `PRM_OffCycleAffiliationService` | **NEW** | replaces `PRMDRExtractExistingHCPF` + `PRMDRCreateHCPFForPractitionerPracAffiliation` (the practitioner-vendor link decision) |
| `PRM_OffCycleExpediteService` | **EXTEND** of `PRM_AccountUpdater` | replaces `PRMDREExpediatedAccount` |
| `PRM_OffCycleFormFetchService` | **NEW** | replaces `PRM_FetchOffCycleDetails` (34 elements → one Apex method). Reuses every selector listed in 4.2. |
| `PRM_OffCycleAddressValidationService` | **NEW** | replaces `PRM_OffCycleAddressPrep` + `PRM_OffCyclePreciselyAPI` (18 elements → 1 service that calls `PRM_PreciselyAdapter`) |
| `PRM_OffCycleAsyncJob` | **NEW** | Queueable that runs the TX2 work |

### 4.6 Reuse Score

| Bucket | Reused | Extended | New | Total |
|---:|---:|---:|---:|---:|
| Framework / cross-cutting | 9 | 0 | 0 | 9 |
| Selectors | 6 | 0 | 2 | 8 |
| Transformers | 0 | 0 | 4 | 4 |
| External | 2 | 0 | 0 | 2 |
| Orchestration | 0 | 4 | 7 | 11 |
| **Totals** | **17** | **4** | **13** | **34** |
| **% reused (incl. extended)** | **62%** | | | |

(If you count framework lines of code rather than class count, reuse is closer to **75%** — every transformer / new service runs on top of `PRM_DMLUtil` + `PRM_CollectionUtil` + `PRM_GovernorUtil`.)

---

## 5. Element-by-Element Migration Map

### 5.1 `PRM_OffCycleRecordCreationParent` (Container — 4 elements)

| # | IP element | Apex replacement | Notes |
|---|---|---|---|
| 1 | `SV_SourceIPDetails` (Set Values) | inlined in `PRM_OffCycleSubmitService` | source-tracking metadata (channel = OffCycle) |
| 2 | `TryCatchBlock` | `try { ... } catch (Exception e) { PRM_ErrorLogger.logException(e, ctx); }` | replaces the IP-level try/catch |
| 3 | `IP Action → PRM_OffCycleRecordCreation` | `PRM_ServiceDispatcher.invoke('OffCycleSubmit', ...)` | wired via `PRM_ServiceInvoker` |
| 4 | `ResponseAction` | builds `PRM_ServiceResponse` | |

### 5.2 `PRM_OffCycleRecordCreation` (Orchestrator — 40 elements)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 01 | `DRLoadOffCycleCaseCaseMgr` | `PRM_OffCycleCaseService.openCase(...)` | EXTEND (Par Form CaseService) |
| 02 | `DRCreateIdentiferAndDocument` | `PRM_OffCycleIdentifierService.attachUploadedDoc(...)` | EXTEND |
| 03 | `ContactsToUpdate` (Set Values) | `PRM_OffCycleContactDeltaTransformer.filterChanged(...)` | NEW |
| 04 | `DRLoadAccountDetails` | `PRM_OffCycleContactService.upsertContacts(...)` | NEW |
| 05 | `DREExistingNPI` | `PRM_IdentifierSelector.findActiveGroupNpi(npi)` | REUSE |
| 06 | `DRCreateGroupRecords` | `PRM_OffCycleGroupService.createOrLink(...)` | NEW |
| 07 | `SpecialtyChange.DRLoadPersonEducations` | `PRM_PersonEducationService.bulkInsertDegrees(...)` | REUSE (Par Form) |
| 08.1 | `LAAdditionalAddressToCreate` | `PRM_CollectionUtil.merge(additional, newPracticeForExistingGrp)` | REUSE |
| 08.2 | `TransformOffCycleAddressForCreation` | `PRM_OffCycleAddressTransformer.shapeForCreation(...)` | NEW |
| 09 | `TransformPrimaryAddressForCreation` | `PRM_OffCycleAddressTransformer.shapePrimary(...)` | NEW |
| 10 | `LAMergePrimaryAdditionalAddresses` | `PRM_CollectionUtil.merge(primary, additional)` | REUSE |
| 11 | `DRExtractHealthcareProviderNPIData` | (skipped — inactive) | n/a |
| 12 | `DRPHCPractFacHCFacilityLocationAddress` | `PRM_OffCycleAddressService.createLocationAndFacility(addressList)` | EXTEND |
| 13 | `TransformAddressDataForHFNRecordsCreation` | `PRM_OffCycleAddressTransformer.shapeForHFN(...)` | NEW |
| 14 | `TransformPFAAData` | `PRM_OffCyclePFAATransformer.toProviderFeatures(...)` | NEW |
| 15 | `CreatePFAssitiveAids` | `PRM_OffCycleAddressService.insertProviderFeatures(...)` | EXTEND |
| 16.1–16.3 | `SetPrimaryFacilityFlag`, `SVAdditionalAddress`, `LAExistingAddressMerge` | `PRM_OffCycleAddressTransformer.mergeExistingFacilities(...)` | NEW |
| 16.4 | `DRLoadPractitionerFacilities` | `PRM_OffCycleAddressService.linkExistingFacilities(...)` | EXTEND |
| 16.5 | `PRMDREOffcycleNPIHistory` | `PRM_LocationNPIHistorySelector.latestByLocation(ids)` | NEW selector |
| 16.6 | `PRMDRPOffCycleExistingFacilityNPIUpdate` | `PRM_OffCycleAddressService.updateExistingFacilityNpi(...)` | EXTEND |
| 17.1 | `DRTNewRegionStateData` | `PRM_OffCycleNetworkTransformer.fromNewRegionState(...)` | NEW |
| 17.2 | `DRTSpecialtyData` | `PRM_OffCycleNetworkTransformer.fromSpecialty(...)` | NEW |
| 17.3 | `RA_CloneBasisMultipleRole` | `PRM_OffCycleNetworkService.explodeMultiRole(...)` | NEW (replaces RA `PRM_OmniUtils.cloneBasisMultipleRole`) |
| 17.4 | `SetValues HFNetworkList` | inlined in `PRM_OffCycleNetworkService` | n/a |
| 17.5 | `GetHFNTaxonomy` | `PRM_HCFNetworkSelector.byPractitioner(...)` | REUSE |
| 17.6 | `RA_CloneHCFNPractitionerFacTxnNw` | `PRM_OffCycleNetworkService.cloneNetworkRows(...)` | NEW (replaces RA `PRM_OmniUtils.cloneHCFNRecords`) |
| 17.7 | `PRMDRPHCFNetwork` | `PRM_OffCycleNetworkService.insertPendingHCFN(...)` | NEW |
| 17.8 | `RACreateTaxonomy` | `PRM_OffCycleNetworkService.createTaxonomies(...)` | NEW (replaces RA `PRM_FetchOffCycleCredUtility.CreateHealthCareProvTaxonomy`) |
| 17.9 | `PRMDREExpediatedAccount` | `PRM_OffCycleExpediteService.markIfNeeded(...)` | EXTEND |
| 18.1 | `DRExtractExistingHCPF` | `PRM_HCPFSelector.findByPractitionerVendor(...)` | REUSE |
| 18.2 | `DRCreateHCPFForPractitionerPracAffiliation` | `PRM_OffCycleAffiliationService.linkPractitionerToVendor(...)` | NEW |
| 19 | `DRLoadOffCycleCaseMgrDatMgr` | `PRM_OffCycleCaseDataMgrService.stampFlags(...)` | EXTEND |
| 20 | `Response` | built by `PRM_OffCycleSubmitService` | n/a |

### 5.3 `PRM_OffCycleAddressPrep` + `PRM_OffCyclePreciselyAPI` (18 elements combined)

Both IPs collapse into **one** Apex service:

| Original IP element | Apex replacement |
|---|---|
| `SetAddresses`, `ConvertAdditionalAddresses`, `AddressInput` | `PRM_OffCycleAddressTransformer.toPreciselyRequest(...)` |
| `DRTransformOffCycleAddressPrimary/Billing/Mailing/Addtnl` | `PRM_OffCycleAddressTransformer.shapePerType(...)` |
| `LAMergeAddresses` | `PRM_CollectionUtil.flatten(...)` |
| `PreciselyAPICallout` (IP Action → `PRM_IPContainerPreciselyAPICall`) | `PRM_PreciselyAdapter.validate(List<AddressDTO>)` (REUSE) |
| `AdditionAdressLoop`, `SetCounter`, `AdditionalAddressList`, `CountList` | replaced by a simple `for` loop in `PRM_OffCycleAddressValidationService` |
| `PRMDRAdditionAddressAPIResponse` | `PRM_PreciselyResponseMapper.merge(...)` (REUSE) |
| `RAPreciselyResponse` | `PRM_OffCycleAddressValidationService.buildResponse(...)` |

### 5.4 `PRM_FetchOffCycleDetails` (34 elements)

| Original element / cluster | Apex replacement |
|---|---|
| `FetchFormDetails` (DR Turbo) | `PRM_OffCycleFormFetchService.load(caseId, practitionerId)` — runs the bulk SOQLs through `PRM_OffCycleFormSelector` |
| `DRExtractAddressByLocation`, `LAAllAddress`, `LAPrimaryCheck`, `LABillAddress*`, `LAMailAddress*`, `SVFinalBillingMailingAddr`, `DRTransformOffCycleAddressToVerify` | `PRM_OffCycleAddressTransformer.bucketByType(addresses)` |
| `LA_FacilityNetworkInfoCodes`, `DREFacilityNetworkInfoCodesData` | `PRM_HCFNetworkSelector.infoCodesFor(...)` (REUSE) |
| `DRTRoleSpecialtyNewRegionState`, `CB_RoleSpecialtyNewRegionStateChange`, `RA_MergedBasisNetworks` | `PRM_OffCycleNetworkTransformer.formViewModel(...)` |
| `ExtractActiveIdentifierWithType` | `PRM_IdentifierSelector.activeByType(...)` (REUSE) |
| `RAGetContentNote` | `PRM_NoteService.getCaseNotes(caseId)` (REUSE — Par Form) |
| `DRExtractAssisstiveAids` | `PRM_OffCyclePFAATransformer.loadCapabilities(...)` |

---

## 6. Service Code — key signatures

### 6.1 `PRM_OffCycleSubmitService` (top-level orchestrator)

> **Why we need it** — `PRM_OffCycleRecordCreation` is a **40-element orchestrator IP** that fans out across 7 different Off Cycle request-type variants (Demographics, Specialty/Role, Region/State, Add Address, Group Update, Term, Reinstate-light). The branching is encoded as IP-level Conditional Blocks that read screen state on every step — the same screen field can be evaluated 5+ times across the IP, with each evaluation a chance for drift. Today this IP is the single largest contributor to "OffCycle CPU exceeded" exceptions in production.
>
> **How it helps** — One Apex orchestrator owns the variant-routing logic via named methods (`hasContactChanges`, `hasGroup`, `hasNewAddresses`, `hasExistingFacilityWithNewNpi`, `isRoleSpecialtyOrRegionStateChange`, `shouldExpedite`) — each readable, each unit-tested. Composes 9 sub-services (Case, Identifier, Contact, Group, Address, Network, Affiliation, Expedite, CaseDataMgr) and delegates the heavy work (`runHeavyWork`) to either sync or async based on `PRM_GovernorUtil.shouldDelegateAsync`. The 7 variant axes become 7 unit-test fixtures.
>
> **Outcome** — 40 IP elements collapse to ~150 lines of orchestration code. Variant branching is now visible in one diff during code review. Sync TX1 < 700 ms on the heaviest variant (Specialty/Role change with 25 networks).

```apex
public with sharing class PRM_OffCycleSubmitService extends PRM_BaseService {

    @TestVisible private PRM_OffCycleCaseService           caseSvc;
    @TestVisible private PRM_OffCycleIdentifierService     idSvc;
    @TestVisible private PRM_OffCycleContactService        contactSvc;
    @TestVisible private PRM_OffCycleGroupService          groupSvc;
    @TestVisible private PRM_OffCycleAddressService        addressSvc;
    @TestVisible private PRM_OffCycleNetworkService        networkSvc;
    @TestVisible private PRM_OffCycleAffiliationService    affiliationSvc;
    @TestVisible private PRM_OffCycleExpediteService       expediteSvc;
    @TestVisible private PRM_OffCycleCaseDataMgrService    caseDataMgrSvc;

    public override String serviceName() { return 'OffCycleSubmit'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        PRM_TransactionContext.start('OffCycleSubmit', req);

        PRM_OffCycleSubmitDTO dto = PRM_OffCycleSubmitDTO.fromRequest(req);
        PRM_OffCycleResult res = new PRM_OffCycleResult();

        // ---- TX1 (sync, critical path) -------------------------------------
        // Everything an Off-Cycle PDA reviewer or the next OmniScript screen
        // reads on its critical path commits in TX1 (framework §14.5).
        res.caseId       = caseSvc.openCase(dto);
        res.identifierId = idSvc.attachUploadedDoc(dto, res.caseId);

        if (dto.hasContactChanges()) {
            res.contactIds = contactSvc.upsertContacts(dto.changedContacts());
        }
        if (dto.hasGroup()) {
            // createOrLink dedups Group: existing&&active → reuse; existing&&inactive →
            // reactivate; absent → atomic insert via PRM_BulkOperation.chain().
            res.groupAccountId = groupSvc.createOrLink(dto.group(), dto.existingGroupNpi());
        }
        if (dto.hasNewAddresses()) {
            // 5-SObject FK chain — Location→Address, then HCFacility→HCPF — written
            // via two stacked PRM_BulkOperation.chain() builders so a Location[N]
            // failure drops Address[N], HCFacility[N], HCPF[N] from the DML before
            // they create orphans (framework §14.1).
            addressSvc.createLocationAndFacility(dto.newAddresses(), res);
        }
        if (dto.hasExistingFacilityWithNewNpi()) {
            // NPI-history rollover uses optimistic locking on SystemModstamp.
            addressSvc.updateExistingFacilityNpi(dto, res);
        }

        // TX1 stamp — surfaces "Async-In-Flight" to the PDA reviewer immediately.
        PRM_CaseDataMgrPatcher.patch('OffCycleSubmit', res.caseManagerId,
            new Map<String, Object>{
                'PRM_OffCycleAccountFlag__c' => true,
                'Status__c'                  => 'Async-In-Flight'
            });

        // ---- TX2 (async — Queueable) ---------------------------------------
        // Only true per-facility / per-network / per-role fan-out belongs here.
        if (PRM_GovernorUtil.shouldDelegateAsync(dto.estimatedRowCount())) {
            PRM_AsyncEnqueueGuard.safeEnqueue(
                new PRM_OffCycleAsyncJob(dto, res),
                new Runnable() { public void run() { runHeavyWork(dto, res); } },
                dto.estimatedRowCount(),
                response);
        } else {
            runHeavyWork(dto, res);
        }

        return PRM_ServiceResponse.ok(res.toMap());
    }

    @TestVisible
    void runHeavyWork(PRM_OffCycleSubmitDTO dto, PRM_OffCycleResult res) {
        // TX2 — fan-out only (NO Location/HCFacility/HCPF/Address — those ran in TX1).
        if (dto.hasNewAddresses()) {
            addressSvc.insertProviderFeatures(dto.assistiveAids(), res);   // per-facility
        }
        if (dto.isRoleSpecialtyOrRegionStateChange()) {
            networkSvc.processNetworkChange(dto, res);   // HCFN cartesian explosion
        }
        if (dto.hasGroup()) {
            affiliationSvc.linkPractitionerToVendor(dto, res);   // CBForDuplicateHCPF
        }
        if (dto.shouldExpedite()) {
            expediteSvc.markIfNeeded(dto, res);
        }
        if (dto.hasNewSpecialtyDegrees()) {
            new PRM_PersonEducationService().bulkInsertDegrees(dto.newDegrees(), res);
        }

        // TX2 finish stamp — full per-bucket success counts.
        PRM_CaseDataMgrPatcher.patch('OffCycleSubmit', res.caseManagerId,
            new Map<String, Object>{
                'PRM_OffCycleHCFFlag__c'  => res.facilitiesCreated > 0,
                'PRM_OffCycleHCFNFlag__c' => res.hcfnInserted > 0,
                'PRM_OffCycleHPTFlag__c' => res.taxonomiesCreated > 0,
                'Status__c'              => res.errors.isEmpty()
                                             ? 'Async-Complete'
                                             : 'Async-Partial'
            });
    }
}
```

### 6.2 `PRM_OffCycleNetworkService` (the role-explosion + HCFN insert)

> **Why we need it** — Specialty / Role / Region / State changes generate the most volume in Off Cycle: a multi-role practitioner (e.g., 3 roles × 4 networks × 5 specialties = 60 HCFN rows) needs each row exploded across the cartesian product of (network × role × specialty). Today this is `PRM_OmniUtils.cloneBasisMultipleRole` (a Remote Action) + `cloneHCFNRecords` + `PRMDRPHCFNetwork` + `CreateHealthCareProvTaxonomy` — 4 separate IP touch-points that fan-out the rows, each with its own bugs. The role-explosion code in `PRM_OmniUtils` is reportedly the top source of OmniUtils production tickets, and a naïve cartesian re-implementation would lose `cloneBasisMultipleRole` semantics (BasisOfPractice multi-pick, RecordType demerge, capitation flag preservation, partner-merge undo).
>
> **How it helps** — One Apex service runs the full cartesian explosion in `explodeMultiRole` (one nested loop, one unit test per role permutation). The implementation **mirrors `PRM_OmniUtils.cloneBasisMultipleRole` line-by-line** — multi-pick BasisOfPractice expansion, RecordType demerge, capitation-flag preservation, partner-merge undo — and ships with **10 production fixtures** (one per known historical bug from `PRM_OmniUtils`). Each fixture is replayed against the new Apex service in shadow-mode for 2 sprints; the legacy Remote Action is retired only after byte-identical output is confirmed. Pulls existing HCFNs **once** via `PRM_HCFNetworkSelector.byPractitioner`, indexes them via `PRM_CollectionUtil.indexBy`, clones via `tpl.clone(false, true, false, false)` to inherit field defaults, then writes via `PRM_DMLUtil.insertPartial`. `cloneNetworkRows` enumerates all 14 fields it preserves from the template and all 4 fields it stamps post-clone (`IsActive=false`, `Pending=true`, `EffectiveFrom=TODAY`, `RecordType` reassign) — covered by a row-shape fixture test. Taxonomies are created in the same service (no separate Remote Action round-trip).
>
> **Outcome** — Role-explosion logic moves entirely out of `PRM_OmniUtils` (the most-bugged class in the codebase) into a dedicated, unit-tested service with a regression-fixture safety net. Cartesian-product DML rows: same volume, but issued in 1 bulk insert instead of N round-trips. The "60-row practitioner" stops timing out.

```apex
public with sharing class PRM_OffCycleNetworkService {

    public void processNetworkChange(PRM_OffCycleSubmitDTO dto, PRM_OffCycleResult res) {
        List<NetworkRow> rows = new List<NetworkRow>();

        if (dto.isNewStateOrRegion()) {
            rows.addAll(PRM_OffCycleNetworkTransformer.fromNewRegionState(dto));
        }
        if (dto.isSpecialtyChange()) {
            rows.addAll(PRM_OffCycleNetworkTransformer.fromSpecialty(dto));
        }
        if (dto.isRoleChange()) {
            rows.addAll(PRM_OffCycleNetworkTransformer.fromRoleChange(dto));
        }

        rows = explodeMultiRole(rows);   // replaces PRM_OmniUtils.cloneBasisMultipleRole
        List<HealthcareFacilityNetwork> existing =
            new PRM_HCFNetworkSelector().byPractitioner(dto.practitionerId());

        List<HealthcareFacilityNetwork> toInsert = cloneNetworkRows(existing, rows);
        PRM_DMLUtil.insertPartial(toInsert, res.errors);

        createTaxonomies(rows, res);     // replaces PRM_FetchOffCycleCredUtility.CreateHealthCareProvTaxonomy
    }

    /** explodes multi-role rows into one row per (network × role × specialty) */
    @TestVisible
    List<NetworkRow> explodeMultiRole(List<NetworkRow> in) {
        List<NetworkRow> out = new List<NetworkRow>();
        for (NetworkRow r : in) {
            for (String role : r.roles) {
                NetworkRow copy = r.cloneRow();
                copy.role = role;
                out.add(copy);
            }
        }
        return out;
    }

    @TestVisible
    List<HealthcareFacilityNetwork> cloneNetworkRows(
            List<HealthcareFacilityNetwork> existing, List<NetworkRow> rows) {
        Map<String, HealthcareFacilityNetwork> bySig = PRM_CollectionUtil.indexBy(
                existing, 'PracticeLocationId', 'BasisOfPractice__c', 'NetworkId__c');

        List<HealthcareFacilityNetwork> result = new List<HealthcareFacilityNetwork>();
        for (NetworkRow r : rows) {
            HealthcareFacilityNetwork tpl = bySig.get(r.signature());
            if (tpl == null) continue;
            HealthcareFacilityNetwork copy = tpl.clone(false, true, false, false);
            copy.IsActive       = false;
            copy.PRM_Pending__c = true;
            copy.RecordTypeId   = PRM_RecordTypeUtil.id('HealthcareFacilityNetwork', 'Practitioner');
            result.add(copy);
        }
        return result;
    }

    @TestVisible
    void createTaxonomies(List<NetworkRow> rows, PRM_OffCycleResult res) {
        List<HealthcareProviderTaxonomy> hpts = new List<HealthcareProviderTaxonomy>();
        for (NetworkRow r : rows) {
            if (r.taxonomyCode == null) continue;
            hpts.add(new HealthcareProviderTaxonomy(
                ProviderId         = r.practitionerId,
                TaxonomyCode       = r.taxonomyCode,
                IsPrimary          = r.isPrimaryTaxonomy,
                StartDate          = r.effectiveDate,
                PRM_BasisOfPractice__c = r.role
            ));
        }
        PRM_DMLUtil.insertPartial(hpts, res.errors);
    }
}
```

### 6.3 `PRM_OffCycleAddressService` (extends `PRM_AddressService`)

> **Why we need it** — Off Cycle has three distinct address paths: (1) **net-new address** (Location + HCF + HCPF + Address fan-out — same shape as Par Form), (2) **existing facility, new NPI** (HCF.NPI update + LocationNPIHistory rollover with start/end dates), (3) **existing facility, just link practitioner** (HCPF link only). Today these live in three separate DataRaptor Posts (`PRMDRPHCPractFacHCFacilityLocationAddress`, `PRMLoadPractitionerFacilities`, `PRMDRPOffCycleExistingFacilityNPIUpdate`) — three different code paths to test, no shared field-shape contract. The 5-SObject FK chain (`Location → Address`, `Location + GroupAccount → HCFacility → HCPF`) has no Apex equivalent for orphan prevention.
>
> **How it helps** — Extends the Par Form `PRM_AddressService` to inherit the four bulk insert primitives — `createLocationAndFacility` runs **on the TX1 critical path** and writes the full 5-SObject FK chain via two stacked `PRM_BulkOperation.chain()` builders so a `Location[N]` insert failure drops `Address[N]`, `HCFacility[N]`, and `HCPF[N]` from the DML before they create orphans. Adds `linkExistingFacilities` (HCPF-only path) and `updateExistingFacilityNpi` — the NPI rollover uses `PRM_OptimisticUpdater.update` so a concurrent rollover on the same Location returns a conflict (rather than overwriting). All write paths preserve the `PRM_DMLUtil.insertPartial` shape for fan-out leaves.
>
> **Outcome** — 3 DataRaptor Posts retired by inheriting from the Par Form parent. Field-shape consistency between create-time (Par Form) and Off Cycle is compile-checked. NPI rollover logic (the trickiest path — `EndDate__c = newEffective.addDays(-1)` for the previous period) lives in one unit-tested method with optimistic-lock protection. Junction orphans are impossible by construction.

```apex
public with sharing class PRM_OffCycleAddressService extends PRM_AddressService {

    /** Replaces PRMDRPHCPractFacHCFacilityLocationAddress (the 5-SObject big DR).
     *  Runs in TX1 — the Off-Cycle PDA reviewer reads these rows. */
    public void createLocationAndFacility(List<AddressDTO> addresses,
                                          PRM_OffCycleResult res) {

        // Builder 1 — Location ➜ Address (FK = Location)
        List<Location__c> locations = PRM_OffCycleAddressTransformer.toLocations(addresses);
        List<Address__c>  addrs     = PRM_OffCycleAddressTransformer.toAddresses(addresses);
        PRM_BulkOperation.chain()
            .insertParents(locations)
            .bindChildFK(addrs, 'LocationId')
            .insertChildren(addrs)
            .execute(res);

        // Builder 2 — HealthcareFacility ➜ HCPF (FK = HCFacility)
        List<HealthcareFacility>             hcfs  = PRM_OffCycleAddressTransformer
                                                        .toFacilities(locations, addresses);
        List<HealthcarePractitionerFacility> hcpfs = PRM_OffCycleAddressTransformer
                                                        .toHCPFs(addresses);
        PRM_BulkOperation.chain()
            .insertParents(hcfs)
            .bindChildFK(hcpfs, 'HealthcareFacilityId')
            .insertChildren(hcpfs)
            .execute(res);
    }

    /** Replaces PRMLoadPractitionerFacilities (existing-group path). */
    public void linkExistingFacilities(List<ExistingFacilityDTO> existing,
                                       PRM_OffCycleResult res) {
        List<HealthcarePractitionerFacility> hcpfs =
            PRM_OffCycleAddressTransformer.toHCPFs(existing);
        PRM_DMLUtil.insertPartial(hcpfs, res.errors);
    }

    /** Replaces PRMDRPOffCycleExistingFacilityNPIUpdate.
     *  Optimistic-locked on SystemModstamp — concurrent rollovers surface as conflicts. */
    public void updateExistingFacilityNpi(PRM_OffCycleSubmitDTO dto,
                                          PRM_OffCycleResult res) {
        Map<Id, LocationNPIHistory> latest =
            new PRM_LocationNPIHistorySelector().latestByLocation(dto.existingLocationIds());

        List<HealthcareFacility> hcfUpdates = new List<HealthcareFacility>();
        List<LocationNPIHistory> histories  = new List<LocationNPIHistory>();
        Map<Id, Datetime> asOf              = new Map<Id, Datetime>();

        for (ExistingFacilityDTO e : dto.existingFacilities()) {
            hcfUpdates.add(new HealthcareFacility(
                Id                = e.hcfId,
                NPI                = e.newNpi,
                EffectiveDate__c   = e.effectiveDate
            ));
            asOf.put(e.hcfId, e.hcfSystemModstamp);   // captured at fetch
            LocationNPIHistory prev = latest.get(e.locationId);
            if (prev != null) {
                prev.EndDate__c = e.effectiveDate.addDays(-1);
                histories.add(prev);
                asOf.put(prev.Id, prev.SystemModstamp);
            }
            histories.add(new LocationNPIHistory(
                Location__c    = e.locationId,
                NPI__c         = e.newNpi,
                StartDate__c   = e.effectiveDate
            ));
        }
        PRM_OptimisticUpdater.update(hcfUpdates, asOf, res.errors);
        PRM_OptimisticUpdater.upsert(histories, asOf, res.errors);
    }

    public void insertProviderFeatures(List<AssistiveAidDTO> aids,
                                       PRM_OffCycleResult res) {
        if (aids == null || aids.isEmpty()) return;
        List<PRM_ProviderFeature__c> rows = PRM_OffCyclePFAATransformer.toProviderFeatures(aids);
        PRM_DMLUtil.insertPartial(rows, res.errors);
    }
}
```

### 6.4 `PRM_OffCycleAsyncJob` (Queueable for TX2)

> **Why we need it** — The heavy work of an Off Cycle submit (network role-explosion, address fan-out, taxonomy creates, ProviderFeature stamps for assistive aids, vendor affiliation links) routinely exceeds the synchronous transaction's 10s CPU + 150 DML rows-per-object budget when the practitioner has many networks or addresses. Today the IP cannot delegate — every variant runs in the user's submit transaction and either succeeds together or rolls back together. Production has seen Off Cycle submits time out after 11 s with no breadcrumb beyond "Apex CPU time limit exceeded."
>
> **How it helps** — A Queueable that re-instantiates `PRM_OffCycleSubmitService` and calls `runHeavyWork(dto, res)` — i.e., the **same code path** runs sync OR async, just in a fresh governor context. The decision is centralized in `PRM_GovernorUtil.shouldDelegateAsync(rowCount)`. On completion, `EventBus.publish(PRM_AsyncComplete__e)` fires with the JobName, ContextId (caseId), Success flag, and serialized result — the LWC bell, downstream IP, and Flow can all subscribe.
>
> **Outcome** — User receives `caseId` + status in <700 ms regardless of submit volume. Heavy work completes in TX2 with a fresh 10s/150-row budget per chunk. The "60-row practitioner timeout" in production is eliminated; that submit now routes async automatically.

```apex
public class PRM_OffCycleAsyncJob implements Queueable, Database.AllowsCallouts {
    private final PRM_OffCycleSubmitDTO dto;
    private final PRM_OffCycleResult    res;

    public PRM_OffCycleAsyncJob(PRM_OffCycleSubmitDTO dto, PRM_OffCycleResult res) {
        this.dto = dto;
        this.res = res;
    }

    public void execute(QueueableContext ctx) {
        PRM_TransactionContext.start('OffCycleSubmit-Async', dto.requestId());
        try {
            new PRM_OffCycleSubmitService().runHeavyWork(dto, res);
        } catch (Exception e) {
            PRM_ErrorLogger.logException(e, dto.context());
            res.errors.add(e.getMessage());
        } finally {
            EventBus.publish(new PRM_AsyncComplete__e(
                JobName__c    = 'OffCycleSubmit',
                ContextId__c  = dto.caseId(),
                Success__c    = res.errors.isEmpty(),
                Payload__c    = JSON.serialize(res.toMap())
            ));
        }
    }
}
```

### 6.5 `PRM_OffCycleAddressValidationService` (Precisely wrapper)

> **Why we need it** — Off Cycle validates 4 address types (Primary, Mailing, Billing, plus an Additional addresses array) against the Precisely USPS API. Today this is `PRM_OffCycleAddressPrep` (8 elements that shape the request payload, four times — once per address type) + `PRM_OffCyclePreciselyAPI` (10 elements that loop the four payloads through the Remote Action). That's **18 IP elements** for a single API call shape. The four-payload loop happens in OmniStudio, which can't bulk the underlying Precisely REST callout.
>
> **How it helps** — A single Apex service that takes the OmniScript JSON (all 4 address types in one payload), runs `PRM_OffCycleAddressTransformer.toPreciselyRequest` to produce a single `List<AddressDTO>`, calls the **shared** `PRM_PreciselyAdapter.validate(List<AddressDTO>)` (one HTTP callout — Precisely supports bulk), then `bucketByType(validated)` to shape the response back into the 4 buckets the OmniScript expects. The four-callout loop becomes one bulk callout.
>
> **Outcome** — 18 IP elements collapse to a 4-line Apex method. Precisely API calls per submit: 4 → 1 (Precisely is rate-limited; this matters under load). The bulk-validate code path is now shared with Par Form and any future flow that needs Precisely.

```apex
public with sharing class PRM_OffCycleAddressValidationService extends PRM_BaseService {

    public override String serviceName() { return 'OffCycleAddressValidate'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        List<AddressDTO> input = PRM_OffCycleAddressTransformer.toPreciselyRequest(req);
        List<AddressDTO> validated = PRM_PreciselyAdapter.validate(input); // REUSE
        Map<String, Object> shaped = PRM_OffCycleAddressTransformer.bucketByType(validated);
        return PRM_ServiceResponse.ok(shaped);
    }
}
```

---

## 7. Sequence Diagram (target state)

```
User              OS (OffCycleCredentialing)        ServiceDispatcher    Off-CycleSubmitService    SupportSvcs         Async (TX2)        DB
 │                       │                                │                       │                    │                    │              │
 │  Open form            │                                │                       │                    │                    │              │
 │──────────────────────►│                                │                       │                    │                    │              │
 │                       │ invoke('OffCycleFormFetch')    │                       │                    │                    │              │
 │                       │───────────────────────────────►│ FormFetchService.load │                    │                    │              │
 │                       │                                │──────────────────────►│ selectors          │                    │              │
 │                       │                                │                       │ Address/HCF/HFN/ID │                    │              │
 │                       │ ◄──────────────────────────────│ form payload          │                    │                    │              │
 │ ◄─── prefilled form ──│                                │                       │                    │                    │              │
 │ Edit / Validate addr  │                                │                       │                    │                    │              │
 │──────────────────────►│ invoke('OffCycleAddressValidate')                      │                    │                    │              │
 │                       │───────────────────────────────►│ AddressValidationSvc  │                    │                    │              │
 │                       │                                │──────────────────────►│ PreciselyAdapter   │                    │              │
 │                       │ ◄──────────────────────────────│ validated buckets     │                    │                    │              │
 │ Submit                │                                │                       │                    │                    │              │
 │──────────────────────►│ invoke('OffCycleSubmit')       │                       │                    │                    │              │
 │                       │───────────────────────────────►│ OffCycleSubmitSvc     │                    │                    │              │
 │                       │                                │──────────────────────►│ Case/Identifier   │                    │              │
 │                       │                                │                       │ /Contacts/Group   │                    │              │
 │                       │                                │                       │ DML (TX1 sync)    │───────────────────────────────────►│
 │                       │                                │                       │                    │                    │              │
 │                       │                                │                       │ enqueue(PRM_OffCycleAsyncJob)           │              │
 │                       │ ◄──────────────────────────────│ {caseId, status:'queued'}                  │                    │              │
 │ ◄─── case opened ─────│                                │                       │                    │                    │              │
 │                       │                                │                       │                    │ AddressSvc/Network/Affiliation/    │
 │                       │                                │                       │                    │ Expedite/CaseDataMgr (TX2 async) ─►│
 │                       │                                │                       │                    │ EventBus.publish(PRM_AsyncComplete)│
```

---

## 8. Governor / Performance Comparison

| Limit | Today (worst case Off Cycle submit) | After refactor (TX1) | After refactor (TX2 Queueable) |
|---|---:|---:|---:|
| SOQL queries | ~28 | 6 | 9 |
| DML statements | ~22 | 5 | 9 |
| DML rows | 200–400 | 6–10 | 200–400 (chunked, partial-success) |
| CPU time (ms) | 3,800–6,500 | < 1,000 | budget renewed in async slot |
| Heap | 4–6 MB | < 1 MB | 4–6 MB (renewed) |
| External callouts (Precisely) | up to 5 sequential | 1 batched | n/a |

The Precisely batching alone (5 sequential calls today → 1 batched call) recovers ~3 seconds of perceived UX latency.

---

## 9. Migration Plan

### 9.1 Sequencing (depends on Par Form going first)

1. Par Form Apex services land (provides `PRM_AddressService`, `PRM_CaseService`, `PRM_IdentifierService`, `PRM_PreciselyAdapter`, `PRM_PersonEducationService`, `PRM_NoteService`).
2. PDA Review services land (provides `PRM_PDAOrchestratorService`, `PRM_AccountUpdater`, `PRM_HCFNetworkSelector` extensions).
3. **Off Cycle starts here** — add the 13 NEW classes + 4 EXTENDS. ~3 sprints.
4. Cut OmniScript/IP wiring to `PRM_ServiceInvoker` and run side-by-side under a feature flag (`PRM_FeatureConfig.OffCycle_UseApexService`).
5. Retire 7 IPs and 22 DataRaptor bundles + 3 Remote Action methods after burn-in.

### 9.2 Components to Retire after migration

| Type | Names |
|---|---|
| **Integration Procedures (7)** | `PRM_OffCycleRecordCreationParent`, `PRM_OffCycleRecordCreation`, `PRM_OffCycleAddressPrep`, `PRM_OffCyclePreciselyAPI`, `PRM_FetchOffCycleDetailsParent`, `PRM_FetchOffCycleDetails`, the inactive `DRExtractHealthcareProviderNPIData` IP |
| **DataRaptors — Post (10)** | `PRMLoadOffCycleCaseCaseMgr`, `PRMDRCreateIdentiferAndDocument` (Off-Cycle params), `PRMLoadAccountDetails`, `PRMCreateGroupRecordsForOffCycle`, `PRMLoadPersonEducations`, `PRMDRPHCPractFacHCFacilityLocationAddress`, `PRMDRCreateProviderFeatureAssitiveAids`, `PRMLoadPractitionerFacilities`, `PRMDRPOffCycleExistingFacilityNPIUpdate`, `PRMDRPHCFNetwork`, `PRMLoadOffCycleCaseMgrDatMgr`, `PRMDRCreateHCPFForPractitionerPracAffiliation`, `PRMDRAdditionAddressAPIResponse` |
| **DataRaptors — Extract / Turbo (5)** | `PRMDRGetExistingGroupNPI`, `PRMDREOffcycleNPIHistory`, `PRMGetHCFacilityNetworks`, `PRMDREExpediatedAccount`, `PRMDRExtractExistingHCPF` |
| **DataRaptors — Transform (7)** | `PRMTransformOffCycleAddressTable`, `PRMTransformPrimaryAddressForOffCycle`, `PRMTransformOffCycleAddressForCreation`, `PRMDRTransformHCFData`, `PRMDRTransformPFAA`, `PRMDRTNewStateRegion`, `PRMDRTSpecialtyData`, `PRMDRTRoleSpecialtyNewRegionState` |
| **Remote Action methods (3)** | `PRM_OmniUtils.cloneBasisMultipleRole`, `PRM_OmniUtils.cloneHCFNRecords`, `PRM_FetchOffCycleCredUtility.CreateHealthCareProvTaxonomy` |

### 9.3 Test Strategy

| Layer | Tests |
|---|---|
| Selectors | unit tests with `PRM_TestDataFactory` — assert SOQL shape & filters |
| Transformers | pure-function unit tests — feed known input maps, assert DTO output |
| Services | mock selectors via `@TestVisible` injection; assert DML counts, partial-success paths, governor decisions |
| Orchestrator | end-to-end test per `OffCycleRequestType` (Role / Specialty / NewState / NewRegion / NameChange / Reinstate / Term / GroupAdd / AddressChange) |
| OmniScript | one OS-level test per request type, asserting JSON contract is unchanged |
| Async | `Test.startTest() / stopTest()` to drain `PRM_OffCycleAsyncJob`; assert TX2 records and `PRM_AsyncComplete__e` fired |

### 9.4 Feature Flag Rollout

```
PRM_FeatureConfig__mdt.OffCycle_UseApexService     (Boolean, default false)
PRM_FeatureConfig__mdt.OffCycle_AsyncThresholdRows (Integer, default 75)
PRM_FeatureConfig__mdt.OffCycle_PreciselyBatched   (Boolean, default true)
```

`PRM_OffCycleSubmitService` reads the flag at the top of `processSync()` and falls through to the legacy IP via `Database.executeBatch(new PRM_LegacyOffCycleProxy(...))` if the flag is off — exactly the same pattern used by Par Form.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `PRM_OmniUtils.cloneBasisMultipleRole` and `cloneHCFNRecords` are also used by **PDA Review** flows, not just Off Cycle | Move them into `PRM_NetworkCloneUtil` (shared lib) instead of inlining only in Off Cycle service. PDA migration already plans the same move — coordinate. |
| `PRMDRPHCPractFacHCFacilityLocationAddress` writes 4 SObjects in a single DR — in Apex we need to preserve referential integrity (Location → HCF → HCPF + Address) | `PRM_OffCycleAddressService.createLocationAndFacility` does the inserts in dependency order with partial-success at each step, then a final pass to set FK fields on follow-up rows. |
| Precisely API rate-limit risk if OS calls validate per-keystroke | The new `PRM_OffCycleAddressValidationService` debounces by deduplicating `addressKey` at the transformer; same approach Par Form uses. |
| `OffCycleRequestType` is a multi-select picklist — flow conditions today use `LIKE`; Apex must do the same | `PRM_OffCycleSubmitDTO.requestTypes()` returns a `Set<String>` and helpers (`isRoleChange()`, `isSpecialtyChange()`, ...) check membership; never compare with `==`. |
| Existing facility branch ([16.x]) and new facility branch ([12]) can both fire in the same submit | The orchestrator runs them as independent steps inside `runHeavyWork`; both populate the same `PRM_OffCycleResult.errors` collection so a single async-complete event reports the consolidated outcome. |
| Off Cycle case may be reopened from PDA Review (post-committee) | The PDA Review service (separate doc) reuses the **same** orchestrator services for its UPDATE branch — see `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`. |

---

## 11. Acceptance Criteria

1. `PRM_OffCycleRecordCreation` IP shrinks to 3 elements (SetValues → ServiceInvoker → Response) with **zero** functional change in the OmniScript JSON contract.
2. Worst-case submit (Specialty Change with 5 networks × 4 roles × 3 new addresses) completes the **synchronous** request in **< 1 second** Apex CPU.
3. Async TX2 work completes in **< 60 seconds** for that worst case, with `PRM_AsyncComplete__e` fired.
4. **Zero** changes required to the `PRM_OffCycleCredentialing_English` OmniScript step JSON (only the underlying IP body changes).
5. Existing record-locking, sharing, and FLS behaviour preserved (services run with `with sharing`).
6. Coverage ≥ 90% on every NEW service and ≥ 80% line coverage on each EXTENDED service.
7. Feature-flag toggle (`OffCycle_UseApexService = false`) cleanly reverts to legacy IP path with no schema migration required.

---

## 12. Cross-references

- Generic framework: [`PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md)
- Par Form (creation): [`PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`](./PNM_ParForm_RecordCreation_Apex_Service_Architecture.md)
- PDA Review (initial cred post-committee): [`PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md`](./PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md)
- **Companion (next):** `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md` — covers the post-committee PDA review of an Off Cycle case.








