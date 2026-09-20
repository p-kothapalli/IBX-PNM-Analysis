# PNM PDA Review & Update Flow - Apex Service Architecture

## IP Audit, Reusability Matrix & New Service Blueprint

> **Companion docs**
> - `PNM_Apex_Service_Architecture.md` — generic SOA framework (Dispatcher / BaseService / DMLUtil / etc.)
> - `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` — Practitioner Participation Form migration (the proven model)
>
> This document does the same element-by-element audit for the **PDA Review and Update** guided flow that runs **after the committee review** (a.k.a. **Initial Cred PDA Review/Update** + the `PRM_PNC` flow that shares the same Subroutines). The focus is **reuse first, build new only where the domain genuinely differs**.

---

## 0. TL;DR

| | Par Form (creation flow) | PDA Review/Update (post-committee flow) |
|---|---|---|
| Purpose | **CREATE** the whole practitioner footprint | **REVIEW & UPDATE** an existing practitioner footprint after committee outcome |
| Entry IP | `PRM_CreateParFormRecordsContainer` | `PRM_InitialCredPDAReviewUpdateParent` |
| Orchestrator IP | `PRM_CreateParFormRecords` | `PRM_InitialCredPDAReviewUpdate` |
| Heaviest IP | `PRM_CreatePractitionerAddressRecords` (80+ elements) | `PRM_InitialCredPDAReviewUpdateSubIPInsert` (29 elements) + `PRM_InitialCredPDAReviewUpdateSubIPUpdate` (21 elements) |
| Companion fetch IP | `PRM_FetchFormParForm*` | `PRM_FetchFormPDAReview` / `PRM_FetchFormPDAReviewParent` |
| Async hook | (planned) `PRM_ParFormLevel4Batch` | Existing `PRM_InitialCredPDAReviewHFN` sub-IP already runs as **Queueable** |
| DML pattern | Mostly **INSERT** | Mix of **INSERT (PNC/HCFN/InfoCode)** + **UPDATE (~12 SObjects)** |
| Reusable framework code | — | **~70%** of Par Form classes carry over with zero changes |
| New services needed | — | **~6 PDA-specific services** + **1 transformer** + **3 selectors** |

---

## 1. Current State: Complete IP Chain Audit

### 1.1 Full IP Orchestration Chain (As-Is)

```
OmniScript: PRM_InitialCredPDA_English  (also: PRM_InitialCredPDAQC_English,
                                                PRM_ProviderChangePDAUpdate_English)
  │
  │  Step 1 (Load):  IP_FetchFormPDAReviewParent  ──► PRM_FetchFormPDAReview
  │                     (loads everything the form needs in one shot)
  │
  │  Step 2 (Submit): IP_InitialCredPDAReviewUpdateParent
        │
        ▼
IP: PRM_InitialCredPDAReviewUpdateParent (Container - v1)
  ├── SV_SourceIPDetails ...................... Set Values (source tracking
  │                                              SourceIPName='PRM_ CreateAdverseActionLog',
  │                                              SourceIPElementName='IP CreateAdverseActionLog')
  ├── TryCatchBlock ............................ Error boundary
  │     └── IP_InitialCredPDAReviewUpdate ...... Calls child orchestrator ─────────────┐
  │           failureConditionalFormula:                                                │
  │              %success% == false                                                    │
  │     remoteClass: PRM_OmniUtils                                                     │
  │     remoteMethod: logTryCatchException                                             │
  └── ResponseAction ............................ Final response                       │
                                                                                       │
┌──────────────────────────────────────────────────────────────────────────────────────┘
│
▼
IP: PRM_InitialCredPDAReviewUpdate (Orchestrator - active v23)
  ├── [1]  DRCreateNewCase ....................... DR Post: PRMCreateNewCase
  │             Creates: Case (NEW, when CM-driven retry)
  │             Owner logic: provider change → query latest PDA Case OwnerId
  │             Cond: ISNOTBLANK(%RecordsToUpdate:NewCase:PRM_CaseManager__c%)
  │
  ├── [2]  setPDMManualUpdateType ................ Set Values
  │             Maps PDMManualUpdateType from screen → IndividualApplication
  │             ("Reinstate Practitioner" → "reinstate" else "not reinstate")
  │
  ├── [3]  DRUpdateCaseCaseManager ............... DR Post: PRMUpdateIDCaseCaseMgr
  │             Updates: Case + IndividualApplication (Case Manager record)
  │             Sets Pending=FALSE, links new Case Id if LatestCase=="NewCase"
  │             Cond: Case.Id OR IndividualApplication.Id is set
  │
  ├── [4]  SVEntityId ............................ Set Values: pick Account/Case id
  │
  ├── [5]  SVNotes ............................... Set Values: builds ProceedToNote payload
  │
  ├── [6]  RACreateNote .......................... Remote Action
  │             remoteClass: PRM_OmniUtils
  │             remoteMethod: createNoteMulti
  │             Cond: SVNotes:ProceedToNote:Content is not blank
  │
  ├── [7]  CBLogicForPDARecordsInsertionIP ....... IP Action ──┐
  │             integrationProcedureKey:                       │
  │                 PRM_InitialCredPDAReviewUpdateSubIPInsert  │  branches to INSERT path
  │             Cond:                                          │
  │              ISNOTBLANK(PracticeLocationTable) &&          │
  │              ISNOTBLANK(PractitionerPracticeLocationBlock) &&
  │              CaseType = 'PDA Review and Update'            │
  │                                                            │
  ├── [8]  PRMDRCreateIdentiferAndDocument ....... DR Post: PRMDRCreateIdentiferAndDocument
  │             Creates: Identifier + ContentDocument/ContentVersion
  │             (Rebuttal / re-upload attachments)
  │             TargetLocation="SF PDM", FormProcess="Practitioner Participation"
  │             Cond: ISNOTBLANK(%FileData%)
  │
  ├── [9]  CBLogicForRecordUpdationIP ............ IP Action ──┐
  │             integrationProcedureKey:                       │
  │                 PRM_InitialCredPDAReviewUpdateSubIPUpdate  │  branches to UPDATE path
  │             Cond:                                          │
  │              ISNOTBLANK(PracticeLocationTable) &&          │
  │              ISNOTBLANK(PractitionerPracticeLocationBlock) │
  │                                                            │
  └── [10] RAActionSucess ......................... Remote Action (final return)


┌──────────────────────────────────────────────────────────────────────────┐
│ IP: PRM_InitialCredPDAReviewUpdateSubIPInsert   (active v6, 29 elements) │
│ Purpose: build & insert NEW PNC/HCFN/InfoCode records on top of existing │
│          practitioner footprint after committee approval                 │
└──────────────────────────────────────────────────────────────────────────┘
  ├── [1]  RASetRecords ............................ RA: PRM_OmniUtils.comparePayerInfoCodesRecords
  │            Compares screen edits to existing payer/info-code state,
  │            returns errorOutIACRecordsIds / errorOutPayerRecords (what already exists)
  ├── [2]  SVRecordsToUpdateAsList ................. Set Values (normalize input lists)
  ├── [3]  LMInfoCodes ............................. List Merge (PracticeLoc + Practitioner info codes)
  ├── [4]  DRTPNCRecords ........................... DR Transform: PRMTransPNCPDARecords
  │            Transform raw screen data → InfoCodes / Networks / TxnyNtwk SObject shapes
  ├── [5]  LBSetInfoCodeAsSObject .................. Loop Block (List → SObject array)
  ├── [6]  RA_ConvertToListSobjects_1 .............. Remote Action (shape conversion)
  ├── [7]  LBSetNetworksAsSObject .................. Loop Block
  ├── [8]  RA_ConvertToListSobjects_2 .............. Remote Action
  ├── [9]  LBSetNetworksAsSObject_2 ................ Loop Block
  ├── [10] RA_ConvertToListSobjects_3 .............. Remote Action
  ├── [11] LMNames ................................. List Merge (network names)
  ├── [12] DRGetHCPNByName ......................... DR Extract: PRMGetHCPNByName
  │            Lookup HealthcarePayerNetwork by Name (dedup)
  ├── [13] DRTFinalPNCRecords ...................... DR Transform: PRMTransPNCPDARecords
  │            Final PNC record shaping (merges ErrorOut* with new records)
  ├── [14] LMInfoCodeAssignment .................... List Merge
  ├── [15] DRLoadInfoCodesAssignmnet ............... DR Post: PRMLoadInfoPDA
  │            INSERT: InformationCodeAssigned (PNC info codes)
  │            Sets Pending=FALSE on insert
  ├── [16] LMPracticeLocationNetworks .............. List Merge
  ├── [17] SV_VendorTypeList ....................... Set Values
  ├── [18] DRTransformHCFN ......................... DR Transform (HCFacilityNetwork shaping)
  ├── [19] LMPracticeLocTxnyNtwk ................... List Merge
  ├── [20] SVFinalRecords .......................... Set Values
  │            FacilityPractitionerTxNwRecords, PracLocRecords, ErrorOutICA, ErrorOutPayer
  ├── [21] LMPracLocNetworkWithDir ................. List Merge (with directory data)
  ├── [22] LMPracLocTxNtwrkWithDir ................. List Merge (with directory data)
  ├── [23] LMHCFNRecordsToCreate ................... List Merge
  │            Merges: LMPracLocNetworkWithDir + LMPracLocTxNtwrkWithDir +
  │                    SVFinalRecords.ErrorOutPayer
  ├── [24] GetExistingPLDetails .................... DR Extract: PRMGetHCFDetails
  │            Get existing HealthcareFacility detail for practice locations
  ├── [25] LMHCFDetails ............................ List Merge (PL + PracticeLocDirTable, key=HCFId)
  ├── [26] DRLoadHCFRecords ........................ DR Post: PRMLoadHCFPDAReview
  │            UPSERT: HealthcareFacility (PracticeLocation directory edits)
  │            Cond: LMHCFDetails not blank;  failOnStepError=false
  ├── [27] InitialCredPDAReviewHFN ................. IP Action (Queueable! useQueueable: true)
  │            integrationProcedureKey: PRM_InitialCredPDAReviewHFN
  │            Cond: ISNOTBLANK(LMHCFNRecordsToCreate);  failOnStepError=false
  │            ──► async HCFN write (see helper IP below)
  ├── [28] DRLoadHCFNRecords (INACTIVE in active v6)  DR Post: PRMDRUpdateHCFNetworksReview
  │            Was: HCFN write inline (now done in the Queueable above)
  └── [29] RAResult ................................. Remote Action (return)


┌──────────────────────────────────────────────────────────────────────────┐
│ IP: PRM_InitialCredPDAReviewHFN              (helper, 2 elements, async) │
│ Called Queueable from SubIPInsert step 27                                │
└──────────────────────────────────────────────────────────────────────────┘
  ├── DRLoadHCFNRecords .......................... DR Post: PRMDRUpdateHCFNetworksReview
  │            INSERT/UPDATE: HealthcareFacilityNetwork records
  │            Cond: ISNOTBLANK(%HCFNRecordsToCreate%)
  └── RAResult


┌──────────────────────────────────────────────────────────────────────────┐
│ IP: PRM_InitialCredPDAReviewUpdateSubIPUpdate    (active v5, 21 elements)│
│ Purpose: UPDATE the practitioner footprint per committee decision        │
└──────────────────────────────────────────────────────────────────────────┘
  ├── [1]  SV_RecordsToUpdate ..................... Set Values
  │            Normalizes PracticeLocNtwkDirTable, PracticeLocTxnyDirTable
  ├── [2]  DRGetNPITaxIDHCFNforPNC ................ DR Extract: PRMDRGetNPITaxIDforPNC
  │            Fetch NPI, Identifier, oldCaqh for the facility set
  ├── [3]  DRGetPractitionerLocationPNC ........... DR Extract: PRMDRGetPractitionerLocationPNC
  │            Returns: HCPF + Address + Provider
  ├── [4]  DRGetAccountTaxForPNC .................. DR Extract: PRMDRGetAccountTaxForPNC
  │            Returns: Account + BoardCertification
  ├── [5]  LMHCFNRecords .......................... List Merge
  │            Merges directory variants (PracticeLocationNetworksDir + Tx)
  ├── [6]  PRMLoadOldCaqhRecord ................... DR Post: PRMLoadOldCaqhRecord
  │            UPDATE: old CAQH identifier (when replaced)
  │            Cond: oldCaqh present
  ├── [7]  DRLoadNPITaxHCFNPNC .................... DR Post: PRMDRLoadNPITaxHCFNPNC
  │            UPDATE: HealthcareProviderNpi + Identifier + HCFN
  │            Inputs: Account, NPI, Identifier, HCFN, ShowInDirectory
  │            Cond: DRGetNPITaxIDHCFNforPNC has data
  ├── [8]  PRMDRGetVendorAccountForPDA ............ DR Extract: PRMDRGetVendorAccountForPDA
  │            Returns: InactiveAccounts, Identifier (for vendor account)
  ├── [9]  DRGetLocationNPIHistory ................ DR Extract: PRMDRGetLocationNPIHistory
  │            Pull historic location-NPI deltas for the PL
  ├── [10] DRUptLocationHistoryNPI ................ DR Post: PRMUptLocationHistoryNPI
  │            UPDATE: HealthcareProviderNpi history rows
  │            Cond: LocationNPIHistory present
  ├── [11] DRLoadRelatedRecordsForPNC .............. DR Post: PRMLoadRelatedRecordsForPNC
  │            UPDATE: HCF + HCPF + Provider (mass status flip after committee)
  │            CaseManagerAPDate stamped as attestation timestamp
  ├── [12] DRExtractFacilityAddress ............... DR Extract: PRMExtractFacilityPDA
  │            Pulls Address for the merged HCF list (PL + history)
  ├── [13] DRLoadAddressForPNC .................... DR Post: PRMDRLoadAddressForPNC
  │            UPDATE: Address (PNC effective)
  │            Cond: DRGetPractitionerLocationPNC:Address present
  ├── [14] DRLoadBoardCertification ............... DR Post: PRMUptBoardCertiication
  │            UPDATE: BoardCertification (with attestation date)
  │            Cond: DRGetAccountTaxForPNC:BoardCertification present
  ├── [15] DRUptInfoCodeAssign .................... DR Post: PRMUptInfoCodeAssign
  │            UPDATE: InformationCodeAssigned (Pending=FALSE for ErrorOut set)
  │            Cond: SVFinalRecords:ErrorOutICA present
  ├── [16] DRUpdateProviderFeature ................ DR Post: PRMDRUpdateProviderFeature
  │            UPDATE: ProviderFeature
  │            Cond: ProviderFeatureData|1:Id present
  ├── [17] DRUpdateAFCC ........................... DR Post: PRMDRUpdateProviderFeature
  │            UPDATE: AffirmingCareCategory (uses the same bundle)
  │            Cond: AffirmCareCategory|1:Id present
  ├── [18] DRUpdateAttestationDatePracLoc ......... DR Post: PRMDRUpdateAttestationDatePracLoc
  │            UPDATE: HealthcareFacility (PracticeLocation attestation date)
  │            Cond: CaseType = "PDA Review and Update"
  ├── [19] DRUpdateAttestationDatePractitionerPracLocation
  │             ............................. DR Post: PRMDRUAttestationDatePractitionerPracLoc
  │            UPDATE: HealthcarePractitionerFacility (attestation date)
  ├── [20] PRMDRUpdateVendorAccountIdentifier ..... DR Post: PRMDRUpdateVendorAccountIdentifier
  │            UPDATE: Account (Vendor) + Identifier
  │            Cond: InactiveAccounts present
  └── [21] RAActionSucess ......................... Remote Action (return)
```

### 1.2 Fetch IP Chain (Pre-load for the form)

```
IP: PRM_FetchFormPDAReviewParent (Container)
  └── IP_FetchFormPDAReview ──────────────────────────────────┐
                                                              │
IP: PRM_FetchFormPDAReview (active v24, 25 elements)          │
  ├── [1]  GetFeatureConfigSetting   DR Turbo: PRMGetFeatureConfigSetting
  │            (Kyruus toggle + other feature flags)
  ├── [2]  DRExtractCaseDetails      DR Extract: PRMExtractCaseDetails
  │            Returns: Case, CaseManager (with RecordType DeveloperName),
  │            CaseManagerId, CDM (capability flags), PractitionerId
  ├── [3]  PRMExtractContact         DR Extract: PRMExtractContact
  │            Cond: RC = PRM_PractitionerParticipationRequest OR PRM_PNC
  ├── [4]  DRExtractProvider         DR Turbo: PRMExtractProvider
  ├── [5]  DRExtractPractitionerFacility  DR Turbo: PRMExtractPracticeLocationToPractitionerFacility
  │            Returns: HCPF list with HealthcareFacilityId
  │            RecordTypeDeveloperName = PRM_PractitionerLocationAffiliation
  ├── [6]  DRExtractFacility         DR Turbo: PRMExtractFacility
  ├── [7]  DRGetRelatedRecForPractitioner   DR Extract: PRMGetRelatedRecordForPractitioner
  │            CaseRecTypeName = PRM_PractitionerParticipationRequest
  │            Cond: RC = PRM_PractitionerParticipationRequest
  ├── [8]  DRGetHCFNetworks          DR Extract: PRMGetHCFNForReviewScreensPDAPNC
  │            Returns: HCFN records (incl. "Practitioner at Practice Location Taxonomy and Network")
  ├── [9]  setHCFNData               Set Values
  │            HCFNetworks = FILTER on RecordTypeName
  ├── [10] TransRelatedRecordForPractitioner   DR Transform: PRMTransRelatedRecordForPractitioner
  │            Cond: DRGetRelatedRecForPractitioner:CaseManagers not blank
  ├── [11] DRFetchExistingHCFNPNC    DR Extract: PRMFetchExistingHCFNPNC
  │            Cond: RC = PRM_PNC OR PRM_PractitionerParticipationRequest
  ├── [12] DRFetchAddress            DR Extract: PRMDRGetAddressPDA
  │            Returns address records linked to HCF
  ├── [13] LAMergePLWithAddress      List Merge (on LocationId)
  ├── [14] DRFetchFacilityPractitionerTxNw   DR Extract: PRMFetchFacilityPractitionerTxNwPNC
  │            Cond: RC = PRM_PNC OR PRM_PractitionerParticipationRequest
  ├── [15] RAGetPayerNetworks        RA: PRM_OmniUtils.setPayerRecordsForNwTxRecords
  │            Cond: RC = PRM_PNC OR PRM_PractitionerParticipationRequest
  ├── [16] DRExtractPracticeLocationDataForCapitationSite
  │                                   DR Extract: PRMDRExtractPracticeLocationDataForCapitationSite
  ├── [17] DRFetchPracLocationForCapitatedSites
  │                                   DR Extract: PRMDRFetchPracLocationForCapitatedSites
  ├── [18] DRExtractNetworkData      DR Extract: PRMGetHealthCarePayerNetwork
  ├── [19] RAGetContentNote          RA: PRM_OmniUtils.getContentNotes
  │            Cond: Case.Status == 'Returned' OR 'Rebuttal'
  ├── [20] PRMExtractIdentifierDocuments  DR Extract: PRMExtractIdentifierDocumentsByCaseManagerNTrgtLocation
  │            Cond: Case.Status == 'Rebuttal'
  │            Inputs: CaseManagerId, TargetLocation='SF PDM'
  ├── [21] ExtractProviderFeature    DR Turbo: PRMFetchProviderFeatureUpdate
  │            Cond: FeatureConfig PRM_EnableKyruus__c == false  (legacy path)
  ├── [22] ExtractProviderFeatureKyruus  DR Extract: PRMFetchPFUpdate
  │            Cond: FeatureConfig PRM_EnableKyruus__c == true  (Kyruus path)
  ├── [23] DRTransformFacilityIds    DR Transform: PRMDRTransHCFIdsAFC
  ├── [24] ExtractAFCCKyruus         DR Extract: PRMFetchAFCUpdate
  │            Cond: FeatureConfig PRM_EnableKyruus__c == true
  └── [25] Response                  ResponseAction (single hydrated payload to OmniScript)
```

---

## 2. Complete Record Inventory (What Gets Created/Updated)

### 2.1 SObjects Touched by the PDA Review/Update IP Chain

| # | SObject | Operation | IP Source | Scenario |
|---|---------|-----------|-----------|----------|
| **CREATE side (SubIPInsert)** ||||||
| 1  | **Case** (new PDA cycle) | INSERT | Orchestrator: DRCreateNewCase | Reinstate / Provider Change retry |
| 2  | **IndividualApplication** (Case Manager) | UPDATE | Orchestrator: DRUpdateCaseCaseManager | Always |
| 3  | **ContentVersion** / **ContentDocumentLink** | INSERT | Orchestrator: PRMDRCreateIdentiferAndDocument | Has FileData |
| 4  | **Identifier** (PNC artifact link) | INSERT | Orchestrator: PRMDRCreateIdentiferAndDocument | Has FileData |
| 5  | **InformationCodeAssigned** (PNC info codes) | INSERT | SubIPInsert: DRLoadInfoCodesAssignmnet | PracticeLocation + Practitioner info codes |
| 6  | **HealthcareFacility** (PracticeLocation directory updates) | UPSERT | SubIPInsert: DRLoadHCFRecords | Directory edits |
| 7  | **HealthcareFacilityNetwork** (PNC) | INSERT/UPDATE | SubIPInsert → InitialCredPDAReviewHFN (Queueable) | Network changes |
| **UPDATE side (SubIPUpdate)** ||||||
| 8  | **Identifier** (old CAQH) | UPDATE | PRMLoadOldCaqhRecord | CAQH replacement |
| 9  | **HealthcareProviderNpi** (Practitioner NPI) | UPDATE | DRLoadNPITaxHCFNPNC | Always |
| 10 | **Identifier** (Tax/CAQH refresh) | UPDATE | DRLoadNPITaxHCFNPNC | Always |
| 11 | **HealthcareFacilityNetwork** (HCFN PNC) | UPDATE | DRLoadNPITaxHCFNPNC | Always |
| 12 | **HealthcareProviderNpi** (Location NPI history) | UPDATE | DRUptLocationHistoryNPI | History present |
| 13 | **HealthcareFacility** (related records) | UPDATE | DRLoadRelatedRecordsForPNC | Always |
| 14 | **HealthcarePractitionerFacility** (related) | UPDATE | DRLoadRelatedRecordsForPNC | Always |
| 15 | **HealthcareProvider** | UPDATE | DRLoadRelatedRecordsForPNC | Always |
| 16 | **Address** (PNC effective) | UPDATE | DRLoadAddressForPNC | Address present |
| 17 | **BoardCertification** | UPDATE | DRLoadBoardCertification | Certification present |
| 18 | **InformationCodeAssigned** (clear Pending) | UPDATE | DRUptInfoCodeAssign | ErrorOutICA present |
| 19 | **ProviderFeature** | UPDATE | DRUpdateProviderFeature | ProviderFeatureData has Id |
| 20 | **AffirmingCareCategory** (via same DR bundle) | UPDATE | DRUpdateAFCC | AffirmCareCategory has Id |
| 21 | **HealthcareFacility** (attestation date) | UPDATE | DRUpdateAttestationDatePracLoc | CaseType = PDA Review and Update |
| 22 | **HealthcarePractitionerFacility** (attestation) | UPDATE | DRUpdateAttestationDatePractitionerPracLocation | Always |
| 23 | **Account** (Vendor - inactivate) | UPDATE | PRMDRUpdateVendorAccountIdentifier | InactiveAccounts present |
| 24 | **Identifier** (Vendor) | UPDATE | PRMDRUpdateVendorAccountIdentifier | InactiveAccounts present |

**Net total**: ~7 INSERT targets + ~17 UPDATE targets = **24 distinct DML operations** across ~14 SObjects (some hit twice with different semantics).

### 2.2 Estimated Record Counts Per Submission

| Scenario | Min Records | Max Records | DML Statements (today) |
|----------|-------------|-------------|------------------------|
| Approve - no network changes (vanilla PDA) | 6 (updates only) | 12 | 8-10 |
| Approve - 1 network change + 1 info code | 10 | 18 | 12-15 |
| Reinstate Practitioner (new Case + updates) | 14 | 28 | 16-20 |
| Rebuttal (new Identifier + file + updates) | 18 | 35 | 18-24 |
| Complex PNC (multi-network + capitation + Kyruus on) | 30 | 60+ | 24-30 |

> Compared with Par Form (creation), PDA Review touches **fewer SObjects** but the **proportion of UPDATEs is dramatically higher**. The redesign needs to optimize for partial-success UPDATE batching, not insert chains.

---

## 3. Architecture Overview - Apex Service Layer Diagram (To-Be)

```
+====================================================================================+
|                         OMNISTUDIO PRESENTATION LAYER                                |
|  OmniScript: PRM_InitialCredPDA_English                                              |
|  OmniScript: PRM_InitialCredPDAQC_English        (QC review variant)                 |
|  OmniScript: PRM_ProviderChangePDAUpdate_English (Provider Change variant)           |
+====================================================================================+
         |                                                  ^
         | Remote Action (single Apex call replaces IP chain)|  hydrated payload
         v                                                  |
+====================================================================================+
|                    CONTROLLER / DISPATCHER LAYER  (REUSED)                            |
|                                                                                      |
|  PRM_ServiceDispatcher  (already exists - extend, do not duplicate)                  |
|    implements vlocity_ins.VlocityOpenInterface2                                      |
|    actionName='InitialCredPDAReview.update'  ──► PRM_PDAReviewUpdateService          |
|    actionName='InitialCredPDAReview.load'    ──► PRM_PDAReviewFetchService           |
+====================================================================================+
         |
         v
+====================================================================================+
|                         SERVICE LAYER (Business Logic)                                |
|                                                                                      |
|  PRM_PDAReviewUpdateService  (extends PRM_BaseService)            *** NEW ***        |
|    │                                                                                 |
|    ├── SYNC (TX1) - Critical UPDATE path                                            |
|    │   ├── PRM_PDAOrchestratorService                            (NEW)               |
|    │   │     replaces: PRM_InitialCredPDAReviewUpdate (orchestrator)                 |
|    │   │     - Drives the 10-step workflow, conditional branching                   |
|    │   │     - Calls PRM_CaseDataManagerService.createOrUpdateCase()  (REUSED)       |
|    │   │     - Calls PRM_NoteService.createNotes()                  (NEW small util)|
|    │   │     - Calls PRM_IdentifierDocumentService.createForCase()  (NEW)            |
|    │   │                                                                             |
|    │   ├── PRM_PDARecordUpdateService                            (NEW)               |
|    │   │     replaces: PRM_InitialCredPDAReviewUpdateSubIPUpdate (21 elements)       |
|    │   │     Bulk UPDATE: NPI, Identifier, HCFN, HCF, HCPF, Address, BoardCert,     |
|    │   │                  InfoCode, ProviderFeature, AFCC, Account                   |
|    │   │                                                                             |
|    │   └── PRM_PDANetworkInsertService                           (NEW)               |
|    │         replaces: PRM_InitialCredPDAReviewUpdateSubIPInsert (29 elements)       |
|    │         Bulk INSERT: InformationCodeAssigned (PNC), HCF directory upserts       |
|    │         Hands the HCFN batch off to async router                                |
|    │                                                                                 |
|    └── ASYNC (TX2) - HCFN heavy lift                                                |
|        └── PRM_PDAHCFNetworkQueueable (System.Queueable)         (NEW)               |
|              replaces: PRM_InitialCredPDAReviewHFN (already Queueable IP)            |
|              Bulk INSERT/UPDATE: HealthcareFacilityNetwork                           |
|                                                                                      |
|  PRM_PDAReviewFetchService  (extends PRM_BaseService)             *** NEW ***        |
|    replaces: PRM_FetchFormPDAReview (25 elements)                                    |
|    - Hydrates the entire PDA Review screen in one Apex call                          |
|    - Branches on CaseManager.RC DeveloperName & FeatureConfig.PRM_EnableKyruus__c    |
+====================================================================================+
         |                    |                     |                    |
         v                    v                     v                    v
+===============+  +================+  +==================+  +==================+
| SELECTOR      |  | UTILITY        |  | TRANSFORM        |  | ASYNC FRAMEWORK  |
| LAYER         |  | LAYER          |  | LAYER            |  | (REUSED)         |
+===============+  +================+  +==================+  +==================+
| PRM_Case      |  | PRM_DMLUtil    |  | PRM_PDAData      |  | PRM_PDAHCFNet    |
|  Selector     |  |  .bulkUpdate() |  |  Transformer     |  |   workQueueable  |
|  (REUSED)     |  |  .bulkInsert() |  |  (NEW)           |  |   (NEW - extends |
|               |  |  (REUSED)      |  |                  |  |    PRM_BaseQueue |
| PRM_Pract     |  |                |  | - mapToInfoCode  |  |    able)         |
|  Selector     |  | PRM_Collection |  |   PNC()          |  |                  |
|  (REUSED)     |  |  Util (REUSED) |  | - mapToHCFNet    |  | PRM_BaseQueue    |
|               |  |  .listMerge()  |  |   workForPDA()   |  |  able (REUSED)   |
| PRM_PDA       |  |  .pluck()      |  | - mapToHCFAttest |  |                  |
|  PNCSelector  |  |                |  |   ationUpdate()  |  | PRM_AsyncRouter  |
|  (NEW)        |  | PRM_Governor   |  | - mapToHCPF      |  |  (REUSED)        |
|               |  |  Util (REUSED) |  |   AttestUpdate() |  |                  |
| PRM_PDA       |  |                |  | - mapToProvider  |  | PRM_AsyncComplete|
|  HCFNSelector |  | PRM_PayerNet   |  |   FeatureUpdate()|  |  __e (REUSED PE) |
|  (NEW)        |  |  Util (NEW)    |  | - mapToAFCC      |  |                  |
|               |  |   - compare    |  |   Update()       |  |                  |
| PRM_Capit     |  |     PayerInfo  |  | - mapToAddress   |  |                  |
|  ationSel     |  |     Codes()    |  |   PNCUpdate()    |  |                  |
|   ector       |  |                |  | - mapToBoardCert |  |                  |
|  (NEW)        |  | PRM_NoteUtil   |  | - mapToOldCaqh() |  |                  |
|               |  |  (NEW small)   |  | - mapToVendor    |  |                  |
+===============+  +================+  +==================+  +==================+
         |                    |                     |                    |
         v                    v                     v                    v
+====================================================================================+
|                         CROSS-CUTTING CONCERNS  (ALL REUSED)                         |
|                                                                                      |
|  PRM_ErrorLogger ......... Platform Event → PRM_ExceptionLog__c    (REUSED)          |
|  PRM_TransactionContext ... Transaction ID correlation              (REUSED)         |
|  PRM_FeatureConfig ........ Custom Metadata reader                  (REUSED)         |
|  PRM_ServiceRequest/Resp .. Wrappers                                (REUSED)         |
+====================================================================================+
         |
         v
+====================================================================================+
|                         SALESFORCE DATA MODEL                                        |
|                                                                                      |
|  INSERT TARGETS (sync TX1):                                                          |
|    Case (rare - reinstate retry), Identifier (rebuttal doc),                         |
|    ContentVersion/ContentDocumentLink, InformationCodeAssigned (PNC),                |
|    HealthcareFacility (directory upserts)                                            |
|                                                                                      |
|  INSERT TARGETS (async TX2):                                                         |
|    HealthcareFacilityNetwork (PNC)                                                   |
|                                                                                      |
|  UPDATE TARGETS (sync TX1):                                                          |
|    Account (vendor), Identifier (CAQH/Tax/Vendor),                                   |
|    HealthcareProviderNpi (NPI + history), HealthcareFacilityNetwork,                 |
|    HealthcareFacility (related + attestation), HealthcarePractitionerFacility,       |
|    HealthcareProvider, Address, BoardCertification,                                  |
|    InformationCodeAssigned, ProviderFeature, AffirmingCareCategory,                  |
|    IndividualApplication (case manager)                                              |
+====================================================================================+
```

---

## 4. REUSABILITY MATRIX  (the heart of this document)

Legend:
- 🟢 **REUSE AS-IS** — class already exists in the Par Form framework, no change needed
- 🟡 **REUSE + EXTEND** — class exists, but you must add a new method or new scenario branch
- 🔴 **NEW** — must be built fresh for PDA Review (does not exist in Par Form framework)

### 4.1 Framework / Cross-cutting layer

| Class | Layer | Status | Notes |
|-------|-------|--------|-------|
| `PRM_ServiceDispatcher` | Controller | 🟡 REUSE + EXTEND | Add `actionName` routes: `InitialCredPDAReview.update`, `InitialCredPDAReview.load`. Implementation already supports the `Callable`/`VlocityOpenInterface2` contract. |
| `PRM_BaseService` | Service base | 🟢 REUSE | Template Method (`processSync`/`processAsync`), governor checks, error capture all unchanged. |
| `PRM_ServiceRequest` | Model | 🟢 REUSE | Same JSON envelope - PDA payload sits in `parameters['RecordsToUpdate']`. |
| `PRM_ServiceResponse` | Model | 🟢 REUSE | Same shape (success, summary, errors, asyncJobId). |
| `PRM_TransactionContext` | Cross-cutting | 🟢 REUSE | Tracks SOQL/DML/CPU across the whole chain. |
| `PRM_ErrorLogger` | Cross-cutting | 🟢 REUSE | Platform Event publisher already general-purpose. |
| `PRM_FeatureConfig` | Utility | 🟢 REUSE | Same `PRMGetFeatureConfigSetting` DR Turbo is the source — the Apex reader already pulls `PRM_EnableKyruus__c` and the rest. PDA fetch service reads the same thing. |
| `PRM_AsyncRouter` | Async | 🟢 REUSE | Decides Queueable vs Batchable from row count - we need Queueable for HCFN. |
| `PRM_BaseQueueable` | Async | 🟢 REUSE | Provides stateful chaining + completion Platform Event. |
| `PRM_AsyncComplete__e` | Platform Event | 🟢 REUSE | Same event signals OmniScript on async completion. |
| `PRM_ExceptionLog__c` | Custom Object | 🟢 REUSE | Same logging table; SourceIPName just becomes `PRM_PDAReviewUpdateService`. |

### 4.2 Utility layer (mostly reused)

| Class | Layer | Status | Notes |
|-------|-------|--------|-------|
| `PRM_DMLUtil` | Utility | 🟢 REUSE | `bulkInsert`/`bulkUpdate`/`bulkUpsert` with partial success - generic. PDA uses mostly `bulkUpdate`. |
| `PRM_CollectionUtil` | Utility | 🟡 REUSE + EXTEND | Need one more helper: `listMergeWithDirectory(List<X>, List<Y>, mergeField)` to mirror the `LMHCFDetails` / `LMPracLocNetworkWithDir` patterns. |
| `PRM_GovernorUtil` | Utility | 🟢 REUSE | `canQuery`/`canDML`/`hasHeap` unchanged. |
| `PRM_DeduplicationUtil` | Utility | 🟡 REUSE + EXTEND | Already has `checkExisting*` helpers; add `checkExistingPayerNetworkByName()` to replace `DRGetHCPNByName`. |
| `PRM_TitleCaseUtil` | Utility | 🟢 REUSE (if needed) | Not needed in main PDA flow but stays available for note titles, etc. |
| `PRM_PayerNetworkUtil` | Utility | 🔴 NEW | Encapsulates the comparison logic currently in `PRM_OmniUtils.comparePayerInfoCodesRecords` (the `RASetRecords` remote action). Returns `{errorOutIACRecordsIds, errorOutPayerRecords}`. |
| `PRM_NoteUtil` | Utility | 🔴 NEW (small) | Tiny wrapper replacing `PRM_OmniUtils.createNoteMulti` and `getContentNotes`. Could stay in `PRM_OmniUtils` and just be repackaged — either works. |

### 4.3 Selector layer (split between reused & new)

| Class | Layer | Status | Notes |
|-------|-------|--------|-------|
| `PRM_CaseSelector` | Selector | 🟢 REUSE | Already exists for Par Form (fetches Case + IndividualApplication + Case Manager record type). Powers `DRExtractCaseDetails`. |
| `PRM_PractitionerSelector` | Selector | 🟡 REUSE + EXTEND | Add `getProviderForReview(caseManagerId)` (today's `DRExtractProvider` Turbo) and `getContactForReview(accountId)` (today's `PRMExtractContact`). |
| `PRM_FacilitySelector` | Selector | 🟡 REUSE + EXTEND | Add `getFacilitiesForReview(caseManagerId, hcfIdList)` (today's `DRExtractFacility` Turbo). |
| `PRM_AddressSelector` | Selector | 🟡 REUSE + EXTEND | Add `getAddressesForHCFList(hcfIds)` (today's `DRFetchAddress`). |
| `PRM_PDAPNCSelector` | Selector | 🔴 NEW | Wraps all PNC-specific extracts: `PRMDRGetNPITaxIDforPNC`, `PRMDRGetPractitionerLocationPNC`, `PRMDRGetAccountTaxForPNC`, `PRMFetchExistingHCFNPNC`, `PRMFetchFacilityPractitionerTxNwPNC`, `PRMExtractFacilityPDA`, `PRMDRGetLocationNPIHistory`, `PRMDRGetVendorAccountForPDA`. |
| `PRM_PDAHCFNSelector` | Selector | 🔴 NEW | `PRMGetHCFNForReviewScreensPDAPNC`, `PRMGetHCPNByName`, `PRMGetHealthCarePayerNetwork`, `PRMGetHCFDetails`. |
| `PRM_PDACapitationSelector` | Selector | 🔴 NEW | `PRMDRExtractPracticeLocationDataForCapitationSite` + `PRMDRFetchPracLocationForCapitatedSites`. |
| `PRM_PDAKyruusSelector` | Selector | 🔴 NEW | `PRMFetchProviderFeatureUpdate`, `PRMFetchPFUpdate`, `PRMFetchAFCUpdate`, `PRMDRTransHCFIdsAFC`. (Could collapse into `PRM_PDAPNCSelector` if you prefer fewer classes; kept separate because of the Kyruus feature flag branch.) |
| `PRM_RelatedRecordSelector` | Selector | 🔴 NEW | `PRMGetRelatedRecordForPractitioner` + transform (used by both PDA and ProviderChange). |
| `PRM_IdentifierDocumentSelector` | Selector | 🟡 REUSE + EXTEND | Add `getIdentifierDocumentsByCM(caseManagerId, targetLocation)` (today's `PRMExtractIdentifierDocumentsByCaseManagerNTrgtLocation`). |

### 4.4 Service layer (the new lift)

| Class | Layer | Status | Notes |
|-------|-------|--------|-------|
| `PRM_PDAReviewUpdateService` | Service (orchestrator) | 🔴 NEW | Top-level for the submit path. Mirrors `PRM_ParFormRecordCreationService`. |
| `PRM_PDAOrchestratorService` | Service | 🔴 NEW | Replaces `PRM_InitialCredPDAReviewUpdate` (10 elements) — Case create/update, set values, notes, identifier doc, branching to Insert/Update subroutines. |
| `PRM_PDANetworkInsertService` | Service | 🔴 NEW | Replaces `PRM_InitialCredPDAReviewUpdateSubIPInsert` (29 elements). Builds & inserts PNC records. |
| `PRM_PDARecordUpdateService` | Service | 🔴 NEW | Replaces `PRM_InitialCredPDAReviewUpdateSubIPUpdate` (21 elements). Mass UPDATE service for the post-committee path. |
| `PRM_PDAHCFNetworkQueueable` | Async service | 🔴 NEW | Replaces `PRM_InitialCredPDAReviewHFN`. Implements `Queueable, Database.AllowsCallouts` (only callout if pushing to downstream payer; otherwise plain Queueable). |
| `PRM_PDAReviewFetchService` | Service (data load) | 🔴 NEW | Replaces `PRM_FetchFormPDAReview` (25 elements). Single Apex call returns hydrated payload. Internally branches on `CaseManager.RecordType.DeveloperName` (`PRM_PractitionerParticipationRequest`, `PRM_PNC`, `PRM_OffCycleRequest`, `PRM_ProviderChangeRequest`) and on `FeatureConfig.PRM_EnableKyruus__c`. |
| `PRM_CaseDataManagerService` | Service | 🟢 REUSE | Already created for Par Form for `PRMDRPCaseDataManager` updates. Exact same `IndividualApplication` update needed here (`PRMUpdateIDCaseCaseMgr`). Just add the `pDMManualUpdateType` mapping if not present. Tag: 🟡 if the method signature needs the reinstate flag - else 🟢. |
| `PRM_IdentifierDocumentService` | Service | 🟡 REUSE + EXTEND | Par Form has `createDocumentFile`; here we add `createIdentifierAndDocument(caseManagerId, parentRecordId, fileData, targetLocation='SF PDM', formProcess='Practitioner Participation')` to mirror `PRMDRCreateIdentiferAndDocument`. |
| `PRM_NoteService` | Service | 🔴 NEW (thin) | Thin wrapper around `PRM_OmniUtils.createNoteMulti` so the Service layer doesn't reach into `PRM_OmniUtils` directly. |

### 4.5 Transformer layer (split)

| Class | Layer | Status | Notes |
|-------|-------|--------|-------|
| `PRM_ParFormDataTransformer` | Transformer | 🟢 REUSE methods | Existing `mapToInfoCodeAssigned`, `mapToHealthcareFacility`, `mapToAddress` are reused unchanged. |
| `PRM_PDADataTransformer` | Transformer | 🔴 NEW | All UPDATE-shaped mappers that don't exist in Par Form: `mapToNPIHistoryUpdate`, `mapToCAQHReplacementUpdate`, `mapToBoardCertUpdate`, `mapToAttestationDateUpdate`, `mapToProviderFeatureUpdate` (note: same bundle handles both ProviderFeature and AFCC at the IP layer — keep it that way in Apex with one method `mapToProviderFeatureLike()` taking a discriminator), `mapToVendorAccountUpdate`, `mapToHCPFAttestationUpdate`, `mapToAddressPNCUpdate`. |
| `PRM_PNCRecordBuilder` | Transformer | 🔴 NEW | Centralizes the PNC build pipeline (info-code list merge → HCF/HCFN/InfoCode SObject shaping). Replaces the entire `DRTPNCRecords` + `DRTFinalPNCRecords` + `DRTransformHCFN` + `LBSetInfoCodeAsSObject` + `LBSetNetworksAsSObject` + `RA_ConvertToListSobjects*` chain. |
| `PRM_RelatedRecordTransformer` | Transformer | 🔴 NEW | Replaces `PRMTransRelatedRecordForPractitioner`. |

### 4.6 Aggregate counts

| Bucket | 🟢 As-is | 🟡 Extend | 🔴 New | Total |
|--------|--------|---------|------|-------|
| Controller / Base / Framework / Cross-cutting | 10 | 1 | 0 | 11 |
| Utility | 4 | 2 | 2 | 8 |
| Selector | 1 | 5 | 5 | 11 |
| Service | 1 | 1 | 7 | 9 |
| Transformer | 1 | 0 | 3 | 4 |
| **TOTAL** | **17** | **9** | **17** | **43** |

> **17 of 43 classes (40%) are full reuse, another 9 (21%) are small extensions of existing Par Form classes, and 17 (40%) are genuinely new.** The new ones cluster in PNC-specific selectors, the Update service, and the PNC transformer — exactly the parts that did not exist in the creation flow.

---

## 5. Detailed IP-to-Service Migration Mapping

### 5.1 What stays in the Thin IP (Router only)

```
THIN IP: PRM_InitialCredPDAReviewUpdateParent (KEEP - simplified)
  Step 1: Set Values (source tracking)
  Step 2: Remote Action → PRM_ServiceDispatcher (actionName='InitialCredPDAReview.update')
  Step 3: Response Action (map output)

THIN IP: PRM_FetchFormPDAReviewParent (KEEP - simplified)
  Step 1: Remote Action → PRM_ServiceDispatcher (actionName='InitialCredPDAReview.load')
  Step 2: Response Action

Everything else (PRM_InitialCredPDAReviewUpdate, *SubIPInsert, *SubIPUpdate,
PRM_InitialCredPDAReviewHFN, PRM_FetchFormPDAReview) gets RETIRED.
```

### 5.2 Migration Matrix - Orchestrator (`PRM_InitialCredPDAReviewUpdate`)

| # | Element | Type | DataRaptor / Remote Method | Apex Replacement |
|---|---------|------|----------------------------|------------------|
| 1 | `DRCreateNewCase` | DR Post | `PRMCreateNewCase` | `PRM_CaseDataManagerService.createNewCaseForRetry(request)` 🟡 |
| 2 | `setPDMManualUpdateType` | Set Values | — | Inline assignment in `PRM_PDAOrchestratorService` 🔴 |
| 3 | `DRUpdateCaseCaseManager` | DR Post | `PRMUpdateIDCaseCaseMgr` | `PRM_CaseDataManagerService.updateCaseAndCaseManager(request, newCaseId, pDMManualUpdateType)` 🟢 |
| 4 | `SVEntityId` | Set Values | — | Inline 🔴 |
| 5 | `SVNotes` | Set Values | — | Inline 🔴 |
| 6 | `RACreateNote` | RA | `PRM_OmniUtils.createNoteMulti` | `PRM_NoteService.createMulti(notes)` 🔴 (thin) |
| 7 | `CBLogicForPDARecordsInsertionIP` | IP Action | `PRM_InitialCredPDAReviewUpdateSubIPInsert` | `PRM_PDANetworkInsertService.execute(request)` 🔴 |
| 8 | `PRMDRCreateIdentiferAndDocument` | DR Post | `PRMDRCreateIdentiferAndDocument` | `PRM_IdentifierDocumentService.createIdentifierAndDocument(...)` 🟡 |
| 9 | `CBLogicForRecordUpdationIP` | IP Action | `PRM_InitialCredPDAReviewUpdateSubIPUpdate` | `PRM_PDARecordUpdateService.execute(request)` 🔴 |
| 10 | `RAActionSucess` | RA | — | Response build in `PRM_PDAOrchestratorService` 🔴 |

### 5.3 Migration Matrix - SubIPInsert (`PRM_InitialCredPDAReviewUpdateSubIPInsert`)

| # | Element | Type | DR / Remote Method | Apex Replacement |
|---|---------|------|--------------------|------------------|
| 1 | `RASetRecords` | RA | `PRM_OmniUtils.comparePayerInfoCodesRecords` | `PRM_PayerNetworkUtil.comparePayerInfoCodes(request)` 🔴 |
| 2 | `SVRecordsToUpdateAsList` | Set Values | — | Inline in `PRM_PDANetworkInsertService` 🔴 |
| 3 | `LMInfoCodes` | List Merge | — | `PRM_CollectionUtil.listMerge(...)` 🟢 |
| 4 | `DRTPNCRecords` | DR Transform | `PRMTransPNCPDARecords` | `PRM_PNCRecordBuilder.buildPNCRecords()` 🔴 |
| 5 | `LBSetInfoCodeAsSObject` | Loop Block | — | `PRM_PNCRecordBuilder.toInfoCodeSObjects()` 🔴 |
| 6 | `RA_ConvertToListSobjects_1` | RA | (Apex helper - dynamic) | folded into `PRM_PNCRecordBuilder` 🔴 |
| 7 | `LBSetNetworksAsSObject` | Loop Block | — | `PRM_PNCRecordBuilder.toNetworkSObjects()` 🔴 |
| 8 | `RA_ConvertToListSobjects_2` | RA | (Apex helper) | folded into `PRM_PNCRecordBuilder` 🔴 |
| 9 | `LBSetNetworksAsSObject_2` | Loop Block | — | `PRM_PNCRecordBuilder.toTxNetworkSObjects()` 🔴 |
| 10 | `RA_ConvertToListSobjects_3` | RA | (Apex helper) | folded into `PRM_PNCRecordBuilder` 🔴 |
| 11 | `LMNames` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 12 | `DRGetHCPNByName` | DR Extract | `PRMGetHCPNByName` | `PRM_PDAHCFNSelector.getHealthcarePayerNetworksByName(names)` 🔴 |
| 13 | `DRTFinalPNCRecords` | DR Transform | `PRMTransPNCPDARecords` | `PRM_PNCRecordBuilder.finalizePNCRecords()` 🔴 |
| 14 | `LMInfoCodeAssignment` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 15 | `DRLoadInfoCodesAssignmnet` | DR Post | `PRMLoadInfoPDA` | `PRM_PDANetworkInsertService.insertInfoCodes(records)` → `PRM_DMLUtil.bulkInsert()` 🟢 |
| 16 | `LMPracticeLocationNetworks` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 17 | `SV_VendorTypeList` | Set Values | — | Inline 🔴 |
| 18 | `DRTransformHCFN` | DR Transform | — | `PRM_PNCRecordBuilder.transformHCFN()` 🔴 |
| 19 | `LMPracticeLocTxnyNtwk` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 20 | `SVFinalRecords` | Set Values | — | Inline (build ErrorOut* + FacilityPractitionerTxNw + PracLoc lists) 🔴 |
| 21 | `LMPracLocNetworkWithDir` | List Merge | — | `PRM_CollectionUtil.listMergeWithDirectory()` 🟡 (extended helper) |
| 22 | `LMPracLocTxNtwrkWithDir` | List Merge | — | `PRM_CollectionUtil.listMergeWithDirectory()` 🟡 |
| 23 | `LMHCFNRecordsToCreate` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 24 | `GetExistingPLDetails` | DR Extract | `PRMGetHCFDetails` | `PRM_PDAHCFNSelector.getHCFDetailsForPracticeLocations()` 🔴 |
| 25 | `LMHCFDetails` | List Merge | — | `PRM_CollectionUtil.listMerge(mergeField='HealthcareFacilityId')` 🟢 |
| 26 | `DRLoadHCFRecords` | DR Post | `PRMLoadHCFPDAReview` | `PRM_PDANetworkInsertService.upsertHCFDirectoryRecords()` → `PRM_DMLUtil.bulkUpsert()` 🟢 |
| 27 | `InitialCredPDAReviewHFN` | IP Action (Queueable) | `PRM_InitialCredPDAReviewHFN` | `System.enqueueJob(new PRM_PDAHCFNetworkQueueable(payload))` 🔴 |
| 28 | `DRLoadHCFNRecords` | DR Post (INACTIVE) | `PRMDRUpdateHCFNetworksReview` | absorbed into `PRM_PDAHCFNetworkQueueable` 🔴 |
| 29 | `RAResult` | RA | — | Service return value 🔴 |

### 5.4 Migration Matrix - SubIPUpdate (`PRM_InitialCredPDAReviewUpdateSubIPUpdate`)

| # | Element | Type | DR Bundle | Apex Replacement |
|---|---------|------|-----------|------------------|
| 1 | `SV_RecordsToUpdate` | Set Values | — | Inline 🔴 |
| 2 | `DRGetNPITaxIDHCFNforPNC` | DR Extract | `PRMDRGetNPITaxIDforPNC` | `PRM_PDAPNCSelector.getNPITaxIDHCFNforPNC()` 🔴 |
| 3 | `DRGetPractitionerLocationPNC` | DR Extract | `PRMDRGetPractitionerLocationPNC` | `PRM_PDAPNCSelector.getPractitionerLocationPNC()` 🔴 |
| 4 | `DRGetAccountTaxForPNC` | DR Extract | `PRMDRGetAccountTaxForPNC` | `PRM_PDAPNCSelector.getAccountTaxForPNC()` 🔴 |
| 5 | `LMHCFNRecords` | List Merge | — | `PRM_CollectionUtil.listMerge()` 🟢 |
| 6 | `PRMLoadOldCaqhRecord` | DR Post | `PRMLoadOldCaqhRecord` | `PRM_PDARecordUpdateService.updateOldCaqh()` → `PRM_DMLUtil.bulkUpdate(Identifier)` 🟢 |
| 7 | `DRLoadNPITaxHCFNPNC` | DR Post | `PRMDRLoadNPITaxHCFNPNC` | `PRM_PDARecordUpdateService.updateNPITaxHCFN()` 🔴 |
| 8 | `PRMDRGetVendorAccountForPDA` | DR Extract | `PRMDRGetVendorAccountForPDA` | `PRM_PDAPNCSelector.getVendorAccountForPDA()` 🔴 |
| 9 | `DRGetLocationNPIHistory` | DR Extract | `PRMDRGetLocationNPIHistory` | `PRM_PDAPNCSelector.getLocationNPIHistory()` 🔴 |
| 10 | `DRUptLocationHistoryNPI` | DR Post | `PRMUptLocationHistoryNPI` | `PRM_PDARecordUpdateService.updateLocationNPIHistory()` 🔴 |
| 11 | `DRLoadRelatedRecordsForPNC` | DR Post | `PRMLoadRelatedRecordsForPNC` | `PRM_PDARecordUpdateService.updateRelatedRecordsForPNC()` 🔴 |
| 12 | `DRExtractFacilityAddress` | DR Extract | `PRMExtractFacilityPDA` | `PRM_PDAPNCSelector.getFacilityAddressForPDA()` 🔴 |
| 13 | `DRLoadAddressForPNC` | DR Post | `PRMDRLoadAddressForPNC` | `PRM_PDARecordUpdateService.updateAddressForPNC()` 🔴 |
| 14 | `DRLoadBoardCertification` | DR Post | `PRMUptBoardCertiication` | `PRM_PDARecordUpdateService.updateBoardCertification()` 🔴 |
| 15 | `DRUptInfoCodeAssign` | DR Post | `PRMUptInfoCodeAssign` | `PRM_PDARecordUpdateService.clearInfoCodePending()` → `PRM_DMLUtil.bulkUpdate(InformationCodeAssigned)` 🟢 |
| 16 | `DRUpdateProviderFeature` | DR Post | `PRMDRUpdateProviderFeature` | `PRM_PDARecordUpdateService.updateProviderFeature()` 🔴 |
| 17 | `DRUpdateAFCC` | DR Post | `PRMDRUpdateProviderFeature` (same bundle!) | `PRM_PDARecordUpdateService.updateAffirmingCareCategory()` 🔴 |
| 18 | `DRUpdateAttestationDatePracLoc` | DR Post | `PRMDRUpdateAttestationDatePracLoc` | `PRM_PDARecordUpdateService.updateAttestationDateForHCF()` 🔴 |
| 19 | `DRUpdateAttestationDatePractitionerPracLocation` | DR Post | `PRMDRUAttestationDatePractitionerPracLoc` | `PRM_PDARecordUpdateService.updateAttestationDateForHCPF()` 🔴 |
| 20 | `PRMDRUpdateVendorAccountIdentifier` | DR Post | `PRMDRUpdateVendorAccountIdentifier` | `PRM_PDARecordUpdateService.inactivateVendorAccount()` 🔴 |
| 21 | `RAActionSucess` | RA | — | Service return 🔴 |

### 5.5 Migration Matrix - Fetch (`PRM_FetchFormPDAReview`)

| # | Element | Type | DR Bundle / Remote | Apex Replacement |
|---|---------|------|--------------------|------------------|
| 1 | `GetFeatureConfigSetting` | DR Turbo | `PRMGetFeatureConfigSetting` | `PRM_FeatureConfig.getSettings()` 🟢 |
| 2 | `DRExtractCaseDetails` | DR Extract | `PRMExtractCaseDetails` | `PRM_CaseSelector.getCaseDetailsForReview(contextId)` 🟢 |
| 3 | `PRMExtractContact` | DR Extract | `PRMExtractContact` | `PRM_PractitionerSelector.getContactByAccount(accountId)` 🟡 |
| 4 | `DRExtractProvider` | DR Turbo | `PRMExtractProvider` | `PRM_PractitionerSelector.getProviderForReview(caseManagerId, accountId)` 🟡 |
| 5 | `DRExtractPractitionerFacility` | DR Turbo | `PRMExtractPracticeLocationToPractitionerFacility` | `PRM_PractitionerSelector.getPractitionerFacilities(caseManagerId, practitionerId)` 🟡 |
| 6 | `DRExtractFacility` | DR Turbo | `PRMExtractFacility` | `PRM_FacilitySelector.getFacilitiesByIds(caseManagerId, facilityIds)` 🟡 |
| 7 | `DRGetRelatedRecForPractitioner` | DR Extract | `PRMGetRelatedRecordForPractitioner` | `PRM_RelatedRecordSelector.getRelatedRecords(caseManagerId, recType)` 🔴 |
| 8 | `DRGetHCFNetworks` | DR Extract | `PRMGetHCFNForReviewScreensPDAPNC` | `PRM_PDAHCFNSelector.getHCFNForReview(caseManagerId, practitionerId, facilityIds)` 🔴 |
| 9 | `setHCFNData` | Set Values | — | Inline (filter by RecordTypeName) 🔴 |
| 10 | `TransRelatedRecordForPractitioner` | DR Transform | `PRMTransRelatedRecordForPractitioner` | `PRM_RelatedRecordTransformer.transform(...)` 🔴 |
| 11 | `DRFetchExistingHCFNPNC` | DR Extract | `PRMFetchExistingHCFNPNC` | `PRM_PDAPNCSelector.getExistingHCFNPNC()` 🔴 |
| 12 | `DRFetchAddress` | DR Extract | `PRMDRGetAddressPDA` | `PRM_AddressSelector.getAddressesForHCF(hcfList)` 🟡 |
| 13 | `LAMergePLWithAddress` | List Merge | — | `PRM_CollectionUtil.listMerge(mergeField='LocationId')` 🟢 |
| 14 | `DRFetchFacilityPractitionerTxNw` | DR Extract | `PRMFetchFacilityPractitionerTxNwPNC` | `PRM_PDAPNCSelector.getFacilityPractitionerTxNw()` 🔴 |
| 15 | `RAGetPayerNetworks` | RA | `PRM_OmniUtils.setPayerRecordsForNwTxRecords` | `PRM_PayerNetworkUtil.setPayerRecordsForNwTxRecords()` 🔴 |
| 16 | `DRExtractPracticeLocationDataForCapitationSite` | DR Extract | `PRMDRExtractPracticeLocationDataForCapitationSite` | `PRM_PDACapitationSelector.getPracticeLocationData()` 🔴 |
| 17 | `DRFetchPracLocationForCapitatedSites` | DR Extract | `PRMDRFetchPracLocationForCapitatedSites` | `PRM_PDACapitationSelector.getCapitatedSites()` 🔴 |
| 18 | `DRExtractNetworkData` | DR Extract | `PRMGetHealthCarePayerNetwork` | `PRM_PDAHCFNSelector.getAllHealthcarePayerNetworks()` 🔴 |
| 19 | `RAGetContentNote` | RA | `PRM_OmniUtils.getContentNotes` | `PRM_NoteService.getContentNotes(linkedEntityId, title, status)` 🔴 (thin) |
| 20 | `PRMExtractIdentifierDocuments` | DR Extract | `PRMExtractIdentifierDocumentsByCaseManagerNTrgtLocation` | `PRM_IdentifierDocumentSelector.getDocumentsByCM(caseManagerId, targetLocation)` 🟡 |
| 21 | `ExtractProviderFeature` | DR Turbo | `PRMFetchProviderFeatureUpdate` | `PRM_PDAKyruusSelector.getProviderFeatureLegacy()` (Kyruus OFF) 🔴 |
| 22 | `ExtractProviderFeatureKyruus` | DR Extract | `PRMFetchPFUpdate` | `PRM_PDAKyruusSelector.getProviderFeatureKyruus()` (Kyruus ON) 🔴 |
| 23 | `DRTransformFacilityIds` | DR Transform | `PRMDRTransHCFIdsAFC` | `PRM_PDADataTransformer.extractFacilityIds()` 🔴 |
| 24 | `ExtractAFCCKyruus` | DR Extract | `PRMFetchAFCUpdate` | `PRM_PDAKyruusSelector.getAFCCForKyruus()` 🔴 |
| 25 | `Response` | Response | — | `PRM_PDAReviewFetchService` returns `PRM_PDAReviewFetchResult` 🔴 |

---

## 6. Apex Service Classes - Detailed Responsibility Breakdown

### 6.1 PRM_PDAReviewUpdateService (Top-level orchestrator) — NEW

> **Why we need it** — The post-committee PDA Review submit is a multi-branch transaction: optional new-Case creation (reinstate retry), CaseManager update, document upload, conditional PNC insert (when CaseType = "PDA Review and Update" + practice-location data present), conditional 12-SObject update batch. Today this is spread across the `PRM_InitialCredPDAReviewUpdateParent` container + the `PRM_InitialCredPDAReviewUpdate` orchestrator IP — branching logic encoded in CBLogic Conditional Blocks that reset on every retry attempt.
>
> **How it helps** — Single Apex orchestrator owns the branching (`shouldInsertPNC`, `shouldUpdateRecords`) as named methods with unit tests, composes `PRM_PDAOrchestratorService` for the always-on path, and short-circuits to `PRM_PDANetworkInsertService` and `PRM_PDARecordUpdateService` only when the screen state demands it. Inputs are typed DTOs — retries are idempotent.
>
> **Outcome** — A PDA Review is now reproducible from a transactionId in the log. CBLogic block re-runs that lose state in production are eliminated; the orchestrator is replayable with the same input.

```apex
/**
 * Main entry point for PDA Review & Update submit.
 * Replaces: PRM_InitialCredPDAReviewUpdateParent (Container)
 *
 * Single Apex call covers:
 *   1. Optional new Case creation (reinstate retry)
 *   2. IndividualApplication (Case Manager) update
 *   3. Notes
 *   4. Identifier & Document (rebuttal file)
 *   5. PNC INSERT batch  (sync TX1)
 *   6. PNC UPDATE batch  (sync TX1)
 *   7. HCFN large write   (async TX2 - Queueable)
 */
public class PRM_PDAReviewUpdateService extends PRM_BaseService {

    @TestVisible private PRM_PDAOrchestratorService orchestratorService;
    @TestVisible private PRM_PDANetworkInsertService insertService;
    @TestVisible private PRM_PDARecordUpdateService updateService;

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest request) {
        PRM_TransactionContext.start('PDAReviewUpdate', request);

        Map<String, Object> rec = (Map<String, Object>) request.parameters.get('RecordsToUpdate');
        String caseType = (String) rec.get('CaseType');

        // === Orchestrator (Case + CM + Notes + Identifier) ===
        PRM_PDAOrchestratorResult orchResult = orchestratorService.run(request);

        // === Branch A: PNC insertion path (matches CBLogicForPDARecordsInsertionIP) ===
        PRM_PDAInsertResult insertResult = null;
        if (shouldInsertPNC(rec, caseType)) {
            insertResult = insertService.execute(request, orchResult);
        }

        // === Branch B: Update path (matches CBLogicForRecordUpdationIP) ===
        // The insert service hands its newly-inserted InfoCodeAssigned ids to the update
        // service so clearInfoCodePending() does not double-write rows from this same
        // transaction. When insertResult is null (Branch A skipped), an empty Set is passed.
        PRM_PDAUpdateResult updateResult = null;
        if (shouldUpdateRecords(rec)) {
            Set<Id> insertedICAIds = insertResult != null
                ? insertResult.insertedInfoCodeIds
                : new Set<Id>();
            updateResult = updateService.execute(request, orchResult, insertResult, insertedICAIds);
        }

        // Stamp owned CM flags via field-level merge (framework §14.4).
        PRM_CaseDataMgrPatcher.patch('PDAReview', orchResult.caseManagerId,
            new Map<String, Object>{
                'PRM_HCFNFlag__c'              => updateResult != null,
                'PRM_HCFFlag__c'               => insertResult != null,
                'PRM_IdentifierFlag__c'        => orchResult.identifierCreated,
                'PRM_BoardCertFlag__c'         => updateResult != null && updateResult.perObjectCounts.get('BoardCertification') > 0,
                'PRM_AttestationStampedAt__c'  => System.now()
            });

        return buildResponse(orchResult, insertResult, updateResult);
    }

    private static Boolean shouldInsertPNC(Map<String, Object> rec, String caseType) {
        return isNotBlank(rec, 'PracticeLocationTable')
            && isNotBlank(rec, 'PractitionerPracticeLocationBlock')
            && caseType == 'PDA Review and Update';
    }
    private static Boolean shouldUpdateRecords(Map<String, Object> rec) {
        return isNotBlank(rec, 'PracticeLocationTable')
            && isNotBlank(rec, 'PractitionerPracticeLocationBlock');
    }
}
```

### 6.2 PRM_PDAOrchestratorService — NEW

> **Why we need it** — `PRM_InitialCredPDAReviewUpdate` (10 IP elements) wires together: optional new-Case for retry, the `pDMManualUpdateType` decision (Reinstate vs not), CaseManager update, EntityId resolution (Account vs Case), Notes creation, and Identifier+Document creation. Today these run as 10 separate IP steps with `failOnStepError=true` — one Remote Action timeout rolls back the whole submit.
>
> **How it helps** — One Apex method (`run`) executes the always-on path with explicit error handling per step. Computes `pDMManualUpdateType` in code (no IP SetValues drift), reuses `PRM_CaseDataManagerService` and `PRM_NoteService` across PDA / Off Cycle PDA / Reinstate, returns a typed `PRM_PDAOrchestratorResult` for downstream services to consume. Failure of one step is caught, logged to `PRM_ExceptionLog__c`, and either rethrown or recovered — explicitly chosen, not implicit.
>
> **Outcome** — 10 IP steps collapse to ~120 lines of Apex with 6 unit tests (one per branch). Notes and Identifier-Document creation become reusable across every flow that needs them.

```
Replaces: PRM_InitialCredPDAReviewUpdate (10 elements)

Methods:
  run(request)
    1. (Optional) Create new Case if NewCase.PRM_CaseManager__c is set
         → PRM_CaseDataManagerService.createNewCaseForRetry()
    2. Compute pDMManualUpdateType from screen (Reinstate vs not)
    3. Update Case + IndividualApplication
         → PRM_CaseDataManagerService.updateCaseAndCaseManager(newCaseId, pDMManualUpdateType)
    4. Resolve EntityId (Account vs Case)
    5. Build ProceedToNote payload
    6. If notes content present → PRM_NoteService.createMulti(notes)
    7. Hand back PRM_PDAOrchestratorResult { newCaseId, entityId, caseManagerId,
       proceedNotesCreated }

Internal collaborators:
  - PRM_CaseDataManagerService (REUSE+EXTEND)
  - PRM_NoteService (NEW thin)
```

### 6.3 PRM_PDANetworkInsertService — NEW

> **Why we need it** — `PRM_InitialCredPDAReviewUpdateSubIPInsert` is **29 elements** of mixed read/transform/write logic that builds Healthcare Payer Network records, Information Code Assigned rows, and HCF directory upserts — and then enqueues a separate IP for the HCFN heavy-write. The element-by-element execution pattern means: fan-out reads happen serially (8 SOQL bundles, one DR Extract at a time), partial failures crash the whole sub-IP, and the HCFN async hand-off is wired in OmniStudio config that no Apex test can cover.
>
> **How it helps** — One service runs the PNC insert path explicitly: `PRM_PayerNetworkUtil.comparePayerInfoCodes` resolves the comparison output, `PRM_PNCRecordBuilder` shapes the records (delegating the "what fields go where" knowledge to a single transformer), `PRM_PDAHCFNSelector` looks up payer networks by name in one query, `PRM_DMLUtil.bulkInsert` / `bulkUpsert` writes InfoCodeAssigned and HCF directory updates with partial-success, and `System.enqueueJob(new PRM_PDAHCFNetworkQueueable(payload))` hands off the HCFN heavy write to async TX2.
>
> **Outcome** — 29 sub-IP elements collapse to ~250 lines of Apex with explicit step-by-step error handling. The HCFN async hand-off is now type-checked at compile time. Re-running the insert is idempotent.

```
Replaces: PRM_InitialCredPDAReviewUpdateSubIPInsert (29 elements)

Methods:
  execute(request, orchResult)
    1. PRM_PayerNetworkUtil.comparePayerInfoCodes(input)
         → returns { errorOutIACRecordsIds, errorOutPayerRecords }
    2. PRM_PNCRecordBuilder.buildPNCRecords(screenData, comparisonOutput)
         → returns ShapedPNC { infoCodes[], networks[], txnyNtwks[] }
    3. PRM_PDAHCFNSelector.getHealthcarePayerNetworksByName(networkNames)
    4. PRM_PNCRecordBuilder.finalizePNCRecords(shaped, hpnLookup)
    5. INSERT InformationCodeAssigned records via PRM_DMLUtil.bulkInsert
         (replaces DRLoadInfoCodesAssignmnet, bundle PRMLoadInfoPDA)
    6. UPSERT HealthcareFacility directory updates via Database.upsert(records,
         HealthcareFacility.PRM_DirectoryKey__c, false)
         (replaces DRLoadHCFRecords, bundle PRMLoadHCFPDAReview;
          PRM_DirectoryKey__c is the explicit external-id match field)
    7. HCFN heavy lift → PRM_AsyncEnqueueGuard.safeEnqueue(
         new PRM_PDAHCFNetworkQueueable(payload), inlineFallback,
         estimatedRows, response);
         If the per-transaction Queueable cap is exhausted, the work runs
         inline rather than silently dropping. The decision is logged.
         (replaces InitialCredPDAReviewHFN sub-IP)

  Returns PRM_PDAInsertResult { infoCodeIds[], hcfUpsertIds[], asyncJobId,
    insertedInfoCodeIds[],   ← passed to PRM_PDARecordUpdateService so the
                                update service does NOT clear-pending on rows
                                that were just inserted in this transaction
    errorOutICA[], errorOutPayer[] }

Internal collaborators:
  - PRM_PayerNetworkUtil (NEW)
  - PRM_PNCRecordBuilder (NEW)
  - PRM_PDAHCFNSelector (NEW)
  - PRM_DMLUtil (REUSE)
  - PRM_CollectionUtil (REUSE)
  - PRM_AsyncEnqueueGuard (REUSE — framework §14.2)
  - PRM_PDAHCFNetworkQueueable (NEW)
```

### 6.4 PRM_PDARecordUpdateService — NEW

> **Why we need it** — `PRM_InitialCredPDAReviewUpdateSubIPUpdate` is **21 elements** that updates 12 distinct SObjects: Identifier (CAQH), NPI, HealthcareFacilityNetwork, Location NPI History, HCF, HCPF, HealthcareProvider, Address, BoardCertification, InformationCodeAssigned, ProviderFeature, AffirmingCareCategory, plus attestation dates on HCF and HCPF, and inactivation of vendor accounts. Today every UPDATE is a separate DR Post Action — 12+ DML statements, no partial-success handling, every read happens inside its own DR Extract instead of being bulkified. Three additional pitfalls hide in this IP: (1) `updateOldCaqh` ran before the new CAQH identifier was confirmed inserted, (2) `updateRelatedRecordsForPNC` split a single 3-SObject update into three independent `bulkUpdate` calls so partial success could leave HCF active while HCPF stayed pending, and (3) `clearInfoCodePending` could no-op or double-write rows that the same transaction's insert service had just created.
>
> **How it helps** — One service executes 6 selectors *in parallel* (`getNPITaxIDHCFNforPNC`, `getPractitionerLocationPNC`, `getAccountTaxForPNC`, `getLocationNPIHistory`, `getVendorAccountForPDA`, `getFacilityAddressForPDA`), each capturing `LastModifiedDate` for optimistic-lock predicates. The 12 update steps map 1:1 to 12 named methods. Three of those methods carry hard contracts: `updateOldCaqh(Id newPrimaryCaqhId)` is a no-op if `newPrimaryCaqhId == null` (called only after the new CAQH is confirmed); `updateRelatedRecordsForPNC` writes HCF + HCPF + HealthcareProvider via `PRM_BulkOperation.atomicPair()` so partial success on the trio is impossible; `clearInfoCodePending(Set<Id> insertedInfoCodeIds)` filters out the ids the insert service just created in this transaction. `updateAttestationDateForHCF` is gated on `CaseType == 'PDA Review and Update'`; `updateAttestationDateForHCPF` runs whenever HCPF rows are present.
>
> **Outcome** — DML statements: 12 → 6 (consolidated; the trio is one atomic write, the feature bundle is one). SOQL queries: 21 (one per DR Extract) → 6 (parallel selectors). Per-row failures don't roll back the whole submit. Concurrent edits surface as conflicts, not silent overwrites. Re-running the update is idempotent.

```
Replaces: PRM_InitialCredPDAReviewUpdateSubIPUpdate (21 elements)

Methods (each maps 1:1 to a DR Post):
  execute(request, orchResult, insertResult)

  // SELECTORS (fan-out reads, fired in parallel — capture LastModifiedDate per row)
  npiTaxHCFN  = PRM_PDAPNCSelector.getNPITaxIDHCFNforPNC(input)
  practLoc    = PRM_PDAPNCSelector.getPractitionerLocationPNC(input)
  acctTax     = PRM_PDAPNCSelector.getAccountTaxForPNC(input)
  npiHistory  = PRM_PDAPNCSelector.getLocationNPIHistory(input)
  vendorAcct  = PRM_PDAPNCSelector.getVendorAccountForPDA(practLoc.HCPF)
  facAddress  = PRM_PDAPNCSelector.getFacilityAddressForPDA(input, npiHistory.PLUpdate)

  // TRANSFORMS (build update SObject sets)
  PRM_PDADataTransformer.buildAllUpdates(input, practLoc, acctTax, npiTaxHCFN, npiHistory,
                                          vendorAcct, facAddress, insertResult.errorOutICA);

  // DML — explicit ordering and atomicity
  updateNPITaxHCFN                 → NPI, Identifier, HCFN  (bulkUpdate, optimistic-lock)
  updateLocationNPIHistory         → NPI history rows
  updateRelatedRecordsForPNC       → HCF + HCPF + HealthcareProvider
                                     ── PRM_BulkOperation.atomicPair() (allOrNone=true).
                                        All three roll back together if any fails.
  updateAddressForPNC              → Address
  updateBoardCertification         → BoardCertification
  updateFeatureBundle              → ProviderFeature + AffirmingCareCategory
                                     ── concatenated into a single typed List<SObject>;
                                        ONE bulkUpdate restores per-SObject DML budget to 1.
  clearInfoCodePending(insertedInfoCodeIds)
                                   → InformationCodeAssigned (Pending=FALSE)
                                     ── filters out Ids that this transaction's insert
                                        service just created (passed in as a Set<Id>).
  updateAttestationDateForHCF      → HealthcareFacility (PracticeLocation)
                                     ── asserts CaseType == 'PDA Review and Update'
  updateAttestationDateForHCPF     → HealthcarePractitionerFacility
                                     ── runs whenever HCPF rows are present (no CaseType filter)
  inactivateVendorAccount          → Account + Identifier
  updateOldCaqh(newPrimaryCaqhId)  → Identifier (deactivate legacy CAQH)
                                     ── runs LAST among CAQH operations and is gated:
                                        if (newPrimaryCaqhId == null) skip + log.
                                        Never leaves practitioner with zero active primary.

  All bulkUpdates use PRM_OptimisticUpdater.update(records, asOfMap)
  with WHERE LastModifiedDate = :asOf semantics. Stale rows return as conflicts;
  the LWC surfaces "another reviewer changed this — please re-open".

  Returns PRM_PDAUpdateResult { perObjectCounts, partialFailureLog, conflictedRowIds[] }

Internal collaborators:
  - PRM_PDAPNCSelector  (NEW)
  - PRM_PDADataTransformer (NEW)
  - PRM_DMLUtil (REUSE)
  - PRM_BulkOperation (REUSE — framework §14.1, .atomicPair())
  - PRM_OptimisticUpdater (NEW — optimistic-lock helper)
```

### 6.5 PRM_PDAHCFNetworkQueueable — NEW

> **Why we need it** — `PRM_InitialCredPDAReviewHFN` is *already* a Queueable in IP form (`useQueueable=true`), which is the right idea — but it's a separate IP that has to be re-implemented per flow that needs HCFN bulk inserts (PDA, Off Cycle, Reinstate all create HealthcareFacilityNetworks). Each IP version has slightly different error handling, no shared logging shape, and the legacy `failOnStepError=false` posture means a failed insert silently disappears with no operator-visible signal.
>
> **How it helps** — Single Apex Queueable that extends `PRM_BaseQueueable` to inherit standardized error logging, completion Platform Event publishing (`PRM_AsyncComplete__e`), and the deterministic-poll backup channel (`PRM_AsyncJobStatus__c` row written at start with `RUNNING`, updated at finish with `COMPLETED` / `FAILED` and per-row counts). Per-row failures are written to `PRM_ExceptionLog__c`. The nightly `PRM_AsyncJobReconciler` flags any row stuck in `RUNNING` for > 30 min as `STUCK`. The payload is a typed `PRM_PDAQueuePayload` — no JSON-string round-trip.
>
> **Outcome** — HCFN async writes are uniform across PDA / Off Cycle / Reinstate. Failures are observable. The LWC bell uses the Platform Event by default and falls back to polling `PRM_AsyncJobStatus__c` if the event is missed — no permanent spinner.

```apex
/**
 * Async HCFN writer — replaces PRM_InitialCredPDAReviewHFN (already Queueable in IP form).
 * Extends PRM_BaseQueueable to inherit:
 *   - PRM_AsyncJobStatus__c row writing (start/finish)
 *   - per-row failure logging to PRM_ExceptionLog__c
 *   - completion Platform Event (PRM_AsyncComplete__e)
 *   - chained-job pattern.
 */
public class PRM_PDAHCFNetworkQueueable extends PRM_BaseQueueable {
    private List<HealthcareFacilityNetwork> hcfnToCreate;
    private Id caseManagerId;
    private String transactionId;

    public PRM_PDAHCFNetworkQueueable(PRM_PDAQueuePayload payload) {
        super('PRM_PDAHCFNetworkQueueable', payload.contextId);   // base writes the status row
        this.hcfnToCreate  = payload.records;
        this.caseManagerId = payload.caseManagerId;
        this.transactionId = payload.transactionId;
    }

    protected override void doExecute() {
        // Bundle: PRMDRUpdateHCFNetworksReview
        Database.SaveResult[] res = PRM_DMLUtil.bulkInsertWithPartialSuccess(hcfnToCreate, 200);
        recordRowCounts(res);                  // base updates PRM_AsyncJobStatus__c counters
        logRowFailures(res, hcfnToCreate);     // base writes PRM_ExceptionLog__c
        publishComplete(transactionId, 'PDA_HCFN_INSERT', hcfnToCreate.size());
    }
}
```

### 6.6 PRM_PDAReviewFetchService — NEW

> **Why we need it** — `PRM_FetchFormPDAReview` is **25 elements** that hydrates the PDA review form on screen-open. It runs 14+ DataRaptor extracts serially, branches on `RecordType.DeveloperName` (PRM_PractitionerParticipationRequest / PRM_PNC / PRM_OffCycleRequest / PRM_ProviderChangeRequest), conditionally pulls notes/documents based on case status (Returned / Rebuttal), and forks again on the Kyruus feature toggle. Today the user sees a perceptible 2-3s spinner before the form renders — every extra DR Extract adds ~150 ms.
>
> **How it helps** — Single service executes the always-on reads in **parallel** (Apex aggregate query / Promise-style fan-out via separate selectors that the JIT optimizer batches), then conditionally runs the branch-specific reads. `PRM_FeatureConfig.getSettings()` reads the Kyruus toggle once. Returns a single hydrated `PRM_PDAReviewFetchResult` DTO that the OmniScript binds directly. The 8+ DR Extracts that fetch the same Case repeatedly are deduped — Case is read once.
>
> **Outcome** — Form-open SOQL: 28-45 → 8-12. Form-open CPU: 2-3s → <500ms. The Kyruus on/off branch is now testable independent of the form.

```
Replaces: PRM_FetchFormPDAReview (25 elements)

Methods:
  load(contextId, optional Title)
    1. featureConfig = PRM_FeatureConfig.getSettings()
    2. caseDetails   = PRM_CaseSelector.getCaseDetailsForReview(contextId)
    3. Decide flow path from caseDetails.CaseManager.RC.DeveloperName:
         - PRM_PractitionerParticipationRequest → full hydrate
         - PRM_PNC                              → PNC hydrate
         - PRM_OffCycleRequest / PRM_ProviderChangeRequest → trimmed hydrate
    4. contact   = PRM_PractitionerSelector.getContactByAccount(caseDetails.Case.AccountId)
    5. provider  = PRM_PractitionerSelector.getProviderForReview(caseManagerId, accountId)
    6. hcpfList  = PRM_PractitionerSelector.getPractitionerFacilities(...)
    7. hcfList   = PRM_FacilitySelector.getFacilitiesByIds(...)
    8. PNC bundle (if RC matches):
         existingHCFN  = PRM_PDAPNCSelector.getExistingHCFNPNC()
         addresses     = PRM_AddressSelector.getAddressesForHCF()
         pracLocWithAddr = PRM_CollectionUtil.listMerge(...)
         facilityPracTxNw = PRM_PDAPNCSelector.getFacilityPractitionerTxNw()
         payerNetworks    = PRM_PayerNetworkUtil.setPayerRecordsForNwTxRecords(...)
         capitationData   = PRM_PDACapitationSelector.getPracticeLocationData(...)
         capitatedSites   = PRM_PDACapitationSelector.getCapitatedSites(...)
         allNetworks      = PRM_PDAHCFNSelector.getAllHealthcarePayerNetworks()
    9. If case status in {'Returned', 'Rebuttal'}:
         notes = PRM_NoteService.getContentNotes(caseManagerId, title, status)
    10. If case status = 'Rebuttal':
         docs = PRM_IdentifierDocumentSelector.getDocumentsByCM(caseManagerId, 'SF PDM')
    11. Kyruus branch (FeatureConfig.PRM_EnableKyruus__c):
         OFF → providerFeature = PRM_PDAKyruusSelector.getProviderFeatureLegacy()
         ON  → providerFeature = PRM_PDAKyruusSelector.getProviderFeatureKyruus()
              → afcc = PRM_PDAKyruusSelector.getAFCCForKyruus()
    12. Return PRM_PDAReviewFetchResult (single hydrated payload)

Internal collaborators: everything in §4.3 + PRM_RelatedRecordSelector + PRM_PDACapitationSelector
```

---

## 7. Transaction Boundary Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTION 1 (SYNC)                          │
│            OmniScript waits for this to complete                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_PDAOrchestratorService                                 │ │
│  │   • (optional) Case INSERT  (Reinstate retry)              │ │
│  │   • IndividualApplication UPDATE                           │ │
│  │   • ContentVersion + ContentDocumentLink INSERT (rebuttal) │ │
│  │   • Identifier INSERT (rebuttal)                            │ │
│  │   • Note creation (via PRM_NoteService)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_PDANetworkInsertService (if PDA Review & Update)        │ │
│  │   • InformationCodeAssigned INSERT  (PNC)                  │ │
│  │   • HealthcareFacility UPSERT       (directory edits)      │ │
│  │   • Hand off HCFN payload to Queueable                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_PDARecordUpdateService                                  │ │
│  │   • Identifier UPDATE (oldCAQH replacement)                │ │
│  │   • HealthcareProviderNpi UPDATE (NPI + history rows)      │ │
│  │   • Identifier UPDATE (Tax/CAQH)                            │ │
│  │   • HealthcareFacilityNetwork UPDATE                        │ │
│  │   • HealthcareFacility UPDATE (related + attestation)       │ │
│  │   • HealthcarePractitionerFacility UPDATE (related + attest)│ │
│  │   • HealthcareProvider UPDATE                              │ │
│  │   • Address UPDATE                                          │ │
│  │   • BoardCertification UPDATE                              │ │
│  │   • InformationCodeAssigned UPDATE (clear Pending)         │ │
│  │   • ProviderFeature UPDATE                                  │ │
│  │   • AffirmingCareCategory UPDATE                           │ │
│  │   • Account (Vendor) UPDATE + Identifier UPDATE            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  OUTPUT: PRM_ServiceResponse { success, summary, asyncJobId }    │
│                                                                  │
│  COMMIT POINT ─────────────────────────────────────────────────  │
└─────────────────────────────────────────────────────────────────┘
         │
         │ System.enqueueJob()
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTION 2 (ASYNC - QUEUEABLE)              │
│            User sees "Processing..." with Job ID                 │
│                                                                  │
│  PRM_PDAHCFNetworkQueueable                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ • HealthcareFacilityNetwork INSERT/UPDATE  (PNC bulk)      │ │
│  │   - Uses bundle equivalent of PRMDRUpdateHCFNetworksReview │ │
│  │   - bulkInsertWithPartialSuccess(records, 200)             │ │
│  │ • Publish PRM_AsyncComplete__e Platform Event              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  OmniScript subscribes to event → flips UI to "Done"            │
└─────────────────────────────────────────────────────────────────┘
```

**Why Queueable not Batchable here?**
HCFN row counts in PDA are bounded (10–200 rows typically, peaks at ~500), well within a single Queueable's limits. The current IP already uses `useQueueable: true`. Batch is overkill until volumes consistently exceed ~5,000 rows. Switch to Batchable later via the existing `PRM_AsyncRouter` decision (no code change to caller).

---

## 8. Flow-path Decision Matrix (mirrors the existing Conditional Blocks)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    PDA SCENARIO ROUTING LOGIC                                    │
│                                                                                  │
│  Input:                                                                          │
│    rec = request.parameters.RecordsToUpdate                                      │
│    caseRC = caseManager.RecordType.DeveloperName                                 │
│                                                                                  │
│  STEP 1 — Orchestrator always runs:                                              │
│     • Case retry (if NewCase.PRM_CaseManager__c set)                             │
│     • CaseManager update                                                         │
│     • Notes (if SVNotes.ProceedToNote.Content present)                           │
│     • Identifier+Doc (if FileData present)                                       │
│                                                                                  │
│  STEP 2 — PNC INSERT path (PRM_PDANetworkInsertService):                         │
│     Runs only if:                                                                │
│        rec.PracticeLocationTable not blank                                       │
│        AND rec.PractitionerPracticeLocationBlock not blank                       │
│        AND rec.CaseType = 'PDA Review and Update'                                │
│     ➜ Inserts InfoCode, HCF, hands off HCFN to async                             │
│                                                                                  │
│  STEP 3 — UPDATE path (PRM_PDARecordUpdateService):                              │
│     Runs only if:                                                                │
│        rec.PracticeLocationTable not blank                                       │
│        AND rec.PractitionerPracticeLocationBlock not blank                       │
│     ➜ Fans out all mass UPDATEs (matches CBLogicForRecordUpdationIP)             │
│                                                                                  │
│  FETCH path branches (PRM_PDAReviewFetchService):                                │
│     • caseRC = PRM_PractitionerParticipationRequest → full PNC hydrate           │
│     • caseRC = PRM_PNC                              → full PNC hydrate           │
│     • caseRC = PRM_OffCycleRequest                  → minimal hydrate            │
│     • caseRC = PRM_ProviderChangeRequest            → provider-change hydrate    │
│     • FeatureConfig.PRM_EnableKyruus__c = true      → Kyruus selectors           │
│     • Case.Status in {Returned, Rebuttal}           → load notes                 │
│     • Case.Status = Rebuttal                        → load identifier docs       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Complete Class Inventory for PDA Review Migration

| # | Class | Layer | Status | Replaces (IP/Element) | Notes |
|---|---|---|---|---|---|
| 1  | `PRM_ServiceDispatcher` | Controller | 🟡 EXTEND | `PRM_InitialCredPDAReviewUpdateParent`, `PRM_FetchFormPDAReviewParent` | Add 2 new `actionName` routes |
| 2  | `PRM_BaseService` | Service base | 🟢 REUSE | — | unchanged |
| 3  | `PRM_BaseQueueable` | Async base | 🟢 REUSE | — | unchanged |
| 4  | `PRM_PDAReviewUpdateService` | Service | 🔴 NEW | `PRM_InitialCredPDAReviewUpdateParent` (logic) | Top entry |
| 5  | `PRM_PDAOrchestratorService` | Service | 🔴 NEW | `PRM_InitialCredPDAReviewUpdate` | 10 elements |
| 6  | `PRM_PDANetworkInsertService` | Service | 🔴 NEW | `PRM_InitialCredPDAReviewUpdateSubIPInsert` | 29 elements |
| 7  | `PRM_PDARecordUpdateService` | Service | 🔴 NEW | `PRM_InitialCredPDAReviewUpdateSubIPUpdate` | 21 elements |
| 8  | `PRM_PDAHCFNetworkQueueable` | Async | 🔴 NEW | `PRM_InitialCredPDAReviewHFN` | HCFN bulk async |
| 9  | `PRM_PDAReviewFetchService` | Service | 🔴 NEW | `PRM_FetchFormPDAReview` | 25 elements |
| 10 | `PRM_CaseDataManagerService` | Service | 🟡 EXTEND | DRUpdateCaseCaseManager + DRCreateNewCase | Add `createNewCaseForRetry`, `updateCaseAndCaseManager(reinstateFlag)` |
| 11 | `PRM_IdentifierDocumentService` | Service | 🟡 EXTEND | PRMDRCreateIdentiferAndDocument | Add identifier+doc combo |
| 12 | `PRM_NoteService` | Service | 🔴 NEW (thin) | RACreateNote, RAGetContentNote | Wraps existing PRM_OmniUtils |
| 13 | `PRM_PDAPNCSelector` | Selector | 🔴 NEW | DRGetNPITaxID*, DRGetPractitionerLocationPNC, DRGetAccountTaxForPNC, DRFetchExistingHCFNPNC, DRFetchFacilityPractitionerTxNw, DRExtractFacilityAddress, DRGetLocationNPIHistory, DRGetVendorAccountForPDA | 8 SOQL bundles |
| 14 | `PRM_PDAHCFNSelector` | Selector | 🔴 NEW | DRGetHCFNetworks, DRGetHCPNByName, DRExtractNetworkData, GetExistingPLDetails | 4 SOQL bundles |
| 15 | `PRM_PDACapitationSelector` | Selector | 🔴 NEW | DRExtractPracticeLocationDataForCapitationSite, DRFetchPracLocationForCapitatedSites | 2 SOQL bundles |
| 16 | `PRM_PDAKyruusSelector` | Selector | 🔴 NEW | ExtractProviderFeature, ExtractProviderFeatureKyruus, ExtractAFCCKyruus | Kyruus on/off |
| 17 | `PRM_RelatedRecordSelector` | Selector | 🔴 NEW | DRGetRelatedRecForPractitioner | Shared with ProviderChange |
| 18 | `PRM_CaseSelector` | Selector | 🟢 REUSE | DRExtractCaseDetails | already exists |
| 19 | `PRM_PractitionerSelector` | Selector | 🟡 EXTEND | DRExtractProvider, DRExtractPractitionerFacility, PRMExtractContact | add Review-specific signatures |
| 20 | `PRM_FacilitySelector` | Selector | 🟡 EXTEND | DRExtractFacility | add `getFacilitiesByIds` |
| 21 | `PRM_AddressSelector` | Selector | 🟡 EXTEND | DRFetchAddress | add `getAddressesForHCF` |
| 22 | `PRM_IdentifierDocumentSelector` | Selector | 🟡 EXTEND | PRMExtractIdentifierDocuments | add `getDocumentsByCM` |
| 23 | `PRM_PDADataTransformer` | Transformer | 🔴 NEW | All UPDATE-shaped DR Posts in SubIPUpdate | 12+ mappers |
| 24 | `PRM_PNCRecordBuilder` | Transformer | 🔴 NEW | DRTPNCRecords, DRTFinalPNCRecords, DRTransformHCFN, LBSetInfoCodeAsSObject, LBSetNetworksAsSObject*, RA_ConvertToListSobjects* | The "PNC factory" |
| 25 | `PRM_RelatedRecordTransformer` | Transformer | 🔴 NEW | TransRelatedRecordForPractitioner | Shared with ProviderChange |
| 26 | `PRM_ParFormDataTransformer` | Transformer | 🟢 REUSE | `mapToAddress`, `mapToHCF`, `mapToInfoCodeAssigned` | Same field shapes |
| 27 | `PRM_PayerNetworkUtil` | Utility | 🔴 NEW | RASetRecords (PRM_OmniUtils.comparePayerInfoCodesRecords), RAGetPayerNetworks | Compare + payer set |
| 28 | `PRM_DMLUtil` | Utility | 🟢 REUSE | All DR Post Actions | unchanged |
| 29 | `PRM_CollectionUtil` | Utility | 🟡 EXTEND | All List Merge / Loop Block / RA_ConvertToListSobjects | add `listMergeWithDirectory` |
| 30 | `PRM_GovernorUtil` | Utility | 🟢 REUSE | — | unchanged |
| 31 | `PRM_DeduplicationUtil` | Utility | 🟡 EXTEND | DRGetHCPNByName (network dedup) | add `checkExistingPayerNetworkByName` |
| 32 | `PRM_FeatureConfig` | Utility | 🟢 REUSE | GetFeatureConfigSetting | Kyruus toggle reader |
| 33 | `PRM_ErrorLogger` | Cross-cutting | 🟢 REUSE | TryCatchBlock (PRM_OmniUtils.logTryCatchException) | unchanged |
| 34 | `PRM_TransactionContext` | Cross-cutting | 🟢 REUSE | SV_SourceIPDetails | unchanged |
| 35 | `PRM_ServiceRequest` | Model | 🟢 REUSE | — | unchanged |
| 36 | `PRM_ServiceResponse` | Model | 🟢 REUSE | ResponseAction (all IPs) | unchanged |
| 37 | `PRM_AsyncRouter` | Async framework | 🟢 REUSE | useQueueable on InitialCredPDAReviewHFN | unchanged |
| 38 | `PRM_AsyncComplete__e` | Platform Event | 🟢 REUSE | — | unchanged |
| 39 | `PRM_ExceptionLog__c` | Custom Object | 🟢 REUSE | — | unchanged |
| 40 | `PRM_PDAOrchestratorResult` | Model | 🔴 NEW | — | inter-service DTO |
| 41 | `PRM_PDAInsertResult` | Model | 🔴 NEW | — | inter-service DTO |
| 42 | `PRM_PDAUpdateResult` | Model | 🔴 NEW | — | inter-service DTO |
| 43 | `PRM_PDAReviewFetchResult` | Model | 🔴 NEW | — | inter-service DTO |

---

## 10. Governor Limit Comparison

| Metric | Current (IP Chain) | After (Apex Service) |
|--------|-------------------|---------------------|
| **SOQL Queries** | 28-45 (each DR Extract ≥1, some bundled) | 8-12 (consolidated selectors) |
| **DML Statements** | 15-22 (each DR Post = 1) | 6-9 (one bulk per SObject) |
| **DML Rows** | Same | Same (chunked at 200) |
| **CPU Time** | 35-50s (heavy List Merge + Loop Block + nested IP) | 2-4s sync + async for HCFN |
| **Heap** | 8-12 MB (the OmniProcess DOM + intermediate JSON) | ~3 MB sync (rest offloaded) |
| **Execution Context** | Single sync transaction (with 1 nested Queueable for HFN) | TX1 sync + TX2 Queueable (cleanly bounded) |
| **Failure Mode** | Element fails → whole IP rolls back (failOnStepError=true) | Partial success per bulk DML, error log per record |
| **Conditional re-runs** | Hard - IP state lost between attempts | Idempotent - inputs are typed DTOs |

---

## 11. DataRaptor Bundles Referenced (Complete List)

These are the DataRaptor bundles currently in use that the Apex service framework retires.

| DataRaptor Bundle | Type | IP Source | Replaced By |
|---|---|---|---|
| `PRMGetFeatureConfigSetting` | Turbo Extract | FetchFormPDAReview | `PRM_FeatureConfig.getSettings()` 🟢 |
| `PRMExtractCaseDetails` | Extract | FetchFormPDAReview | `PRM_CaseSelector.getCaseDetailsForReview()` 🟢 |
| `PRMExtractContact` | Extract | FetchFormPDAReview | `PRM_PractitionerSelector.getContactByAccount()` 🟡 |
| `PRMExtractProvider` | Turbo Extract | FetchFormPDAReview | `PRM_PractitionerSelector.getProviderForReview()` 🟡 |
| `PRMExtractPracticeLocationToPractitionerFacility` | Turbo Extract | FetchFormPDAReview | `PRM_PractitionerSelector.getPractitionerFacilities()` 🟡 |
| `PRMExtractFacility` | Turbo Extract | FetchFormPDAReview | `PRM_FacilitySelector.getFacilitiesByIds()` 🟡 |
| `PRMGetRelatedRecordForPractitioner` | Extract | FetchFormPDAReview | `PRM_RelatedRecordSelector.getRelatedRecords()` 🔴 |
| `PRMGetHCFNForReviewScreensPDAPNC` | Extract | FetchFormPDAReview | `PRM_PDAHCFNSelector.getHCFNForReview()` 🔴 |
| `PRMTransRelatedRecordForPractitioner` | Transform | FetchFormPDAReview | `PRM_RelatedRecordTransformer.transform()` 🔴 |
| `PRMFetchExistingHCFNPNC` | Extract | FetchFormPDAReview / SubIPInsert | `PRM_PDAPNCSelector.getExistingHCFNPNC()` 🔴 |
| `PRMDRGetAddressPDA` | Extract | FetchFormPDAReview | `PRM_AddressSelector.getAddressesForHCF()` 🟡 |
| `PRMFetchFacilityPractitionerTxNwPNC` | Extract | FetchFormPDAReview / SubIPInsert | `PRM_PDAPNCSelector.getFacilityPractitionerTxNw()` 🔴 |
| `PRMDRExtractPracticeLocationDataForCapitationSite` | Extract | FetchFormPDAReview | `PRM_PDACapitationSelector.getPracticeLocationData()` 🔴 |
| `PRMDRFetchPracLocationForCapitatedSites` | Extract | FetchFormPDAReview | `PRM_PDACapitationSelector.getCapitatedSites()` 🔴 |
| `PRMGetHealthCarePayerNetwork` | Extract | FetchFormPDAReview | `PRM_PDAHCFNSelector.getAllHealthcarePayerNetworks()` 🔴 |
| `PRMExtractIdentifierDocumentsByCaseManagerNTrgtLocation` | Extract | FetchFormPDAReview | `PRM_IdentifierDocumentSelector.getDocumentsByCM()` 🟡 |
| `PRMFetchProviderFeatureUpdate` | Turbo Extract | FetchFormPDAReview | `PRM_PDAKyruusSelector.getProviderFeatureLegacy()` 🔴 |
| `PRMFetchPFUpdate` | Extract | FetchFormPDAReview | `PRM_PDAKyruusSelector.getProviderFeatureKyruus()` 🔴 |
| `PRMDRTransHCFIdsAFC` | Transform | FetchFormPDAReview | `PRM_PDADataTransformer.extractFacilityIds()` 🔴 |
| `PRMFetchAFCUpdate` | Extract | FetchFormPDAReview | `PRM_PDAKyruusSelector.getAFCCForKyruus()` 🔴 |
| `PRMCreateNewCase` | Multi-Object Load | InitialCredPDAReviewUpdate | `PRM_CaseDataManagerService.createNewCaseForRetry()` 🟡 |
| `PRMUpdateIDCaseCaseMgr` | Multi-Object Load | InitialCredPDAReviewUpdate | `PRM_CaseDataManagerService.updateCaseAndCaseManager()` 🟢 |
| `PRMDRCreateIdentiferAndDocument` | Multi-Object Load | InitialCredPDAReviewUpdate | `PRM_IdentifierDocumentService.createIdentifierAndDocument()` 🟡 |
| `PRMTransPNCPDARecords` | Transform | SubIPInsert (used twice) | `PRM_PNCRecordBuilder.{buildPNCRecords, finalizePNCRecords}` 🔴 |
| `PRMGetHCPNByName` | Extract | SubIPInsert | `PRM_PDAHCFNSelector.getHealthcarePayerNetworksByName()` 🔴 |
| `PRMLoadInfoPDA` | Load | SubIPInsert | `PRM_PDANetworkInsertService.insertInfoCodes()` → `PRM_DMLUtil.bulkInsert()` 🟢 |
| `PRMGetHCFDetails` | Extract | SubIPInsert | `PRM_PDAHCFNSelector.getHCFDetailsForPracticeLocations()` 🔴 |
| `PRMLoadHCFPDAReview` | Load | SubIPInsert | `PRM_PDANetworkInsertService.upsertHCFDirectoryRecords()` 🟢 |
| `PRMDRUpdateHCFNetworksReview` | Load | InitialCredPDAReviewHFN | `PRM_PDAHCFNetworkQueueable.doExecute()` 🔴 |
| `PRMDRGetNPITaxIDforPNC` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getNPITaxIDHCFNforPNC()` 🔴 |
| `PRMDRGetPractitionerLocationPNC` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getPractitionerLocationPNC()` 🔴 |
| `PRMDRGetAccountTaxForPNC` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getAccountTaxForPNC()` 🔴 |
| `PRMLoadOldCaqhRecord` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateOldCaqh()` → `PRM_DMLUtil.bulkUpdate` 🟢 |
| `PRMDRLoadNPITaxHCFNPNC` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateNPITaxHCFN()` 🔴 |
| `PRMDRGetVendorAccountForPDA` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getVendorAccountForPDA()` 🔴 |
| `PRMDRGetLocationNPIHistory` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getLocationNPIHistory()` 🔴 |
| `PRMUptLocationHistoryNPI` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateLocationNPIHistory()` 🔴 |
| `PRMLoadRelatedRecordsForPNC` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateRelatedRecordsForPNC()` 🔴 |
| `PRMExtractFacilityPDA` | Extract | SubIPUpdate | `PRM_PDAPNCSelector.getFacilityAddressForPDA()` 🔴 |
| `PRMDRLoadAddressForPNC` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateAddressForPNC()` 🔴 |
| `PRMUptBoardCertiication` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateBoardCertification()` 🔴 |
| `PRMUptInfoCodeAssign` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.clearInfoCodePending()` 🟢 |
| `PRMDRUpdateProviderFeature` | Load | SubIPUpdate (used twice: PF + AFCC) | `PRM_PDARecordUpdateService.{updateProviderFeature, updateAffirmingCareCategory}` 🔴 |
| `PRMDRUpdateAttestationDatePracLoc` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateAttestationDateForHCF()` 🔴 |
| `PRMDRUAttestationDatePractitionerPracLoc` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.updateAttestationDateForHCPF()` 🔴 |
| `PRMDRUpdateVendorAccountIdentifier` | Load | SubIPUpdate | `PRM_PDARecordUpdateService.inactivateVendorAccount()` 🔴 |

**Total: 45 DataRaptor bundles retired** (compared to the 16 retired in the Par Form migration).

---

## 12. Remote Actions Referenced (Complete List)

| Remote Action (class.method) | IP Source | Replaced By |
|---|---|---|
| `PRM_OmniUtils.logTryCatchException` | Container (TryCatchBlock) | `PRM_ErrorLogger.logException()` 🟢 |
| `PRM_OmniUtils.createNoteMulti` | Orchestrator (RACreateNote) | `PRM_NoteService.createMulti()` 🔴 (thin) |
| `PRM_OmniUtils.comparePayerInfoCodesRecords` | SubIPInsert (RASetRecords) | `PRM_PayerNetworkUtil.comparePayerInfoCodes()` 🔴 |
| `PRM_OmniUtils.setPayerRecordsForNwTxRecords` | FetchFormPDAReview (RAGetPayerNetworks) | `PRM_PayerNetworkUtil.setPayerRecordsForNwTxRecords()` 🔴 |
| `PRM_OmniUtils.getContentNotes` | FetchFormPDAReview (RAGetContentNote) | `PRM_NoteService.getContentNotes()` 🔴 (thin) |
| `RA_ConvertToListSobjects_1/2/3` (anonymous shape helpers) | SubIPInsert | folded into `PRM_PNCRecordBuilder` 🔴 |
| `RAActionSucess`/`RAResult` (return signals) | Orchestrator / Sub-IPs | Service return values 🟢 |

> Most of these methods **already exist in `PRM_OmniUtils`** — the migration is mostly about re-targeting callers from "IP element" to "Apex service" without rewriting the Apex logic itself.

---

## 13. Summary: What Moves Where

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     PDA REVIEW & UPDATE MIGRATION SUMMARY                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAYS IN OMNISTUDIO (Thin):                                                 │
│    • OmniScript UI (no change)                                               │
│    • 2 thin Container IPs (one for load, one for submit)                     │
│                                                                              │
│  MOVES TO APEX SYNC (TX1):                                                   │
│    • Feature Config read                                                     │
│    • Case + Case Manager INSERT/UPDATE                                       │
│    • Notes creation                                                          │
│    • Identifier + Document (rebuttal upload)                                 │
│    • PNC InformationCodeAssigned INSERT                                      │
│    • HCF directory UPSERT                                                    │
│    • Mass UPDATEs (~12 SObjects from SubIPUpdate)                            │
│                                                                              │
│  MOVES TO APEX QUEUEABLE (TX2):                                              │
│    • HealthcareFacilityNetwork bulk write                                    │
│      (matches today's PRM_InitialCredPDAReviewHFN useQueueable=true)         │
│                                                                              │
│  REUSE FROM PAR FORM FRAMEWORK:                                              │
│    • PRM_ServiceDispatcher / BaseService / BaseQueueable                     │
│    • PRM_DMLUtil / CollectionUtil / GovernorUtil / DeduplicationUtil         │
│    • PRM_ErrorLogger / TransactionContext / FeatureConfig                    │
│    • PRM_CaseDataManagerService (extended)                                   │
│    • PRM_IdentifierDocumentService (extended)                                │
│    • PRM_CaseSelector / PractitionerSelector / FacilitySelector /            │
│      AddressSelector / IdentifierDocumentSelector (each extended)            │
│    • PRM_AsyncRouter / PRM_AsyncComplete__e / PRM_ExceptionLog__c            │
│    • PRM_ParFormDataTransformer (the address/HCF/InfoCode mappers)           │
│                                                                              │
│  NEW SERVICES TO BUILD (PDA-specific):                                       │
│    • PRM_PDAReviewUpdateService           — top entry point                  │
│    • PRM_PDAOrchestratorService           — 10-step orchestrator             │
│    • PRM_PDANetworkInsertService          — replaces SubIPInsert (29 elems)  │
│    • PRM_PDARecordUpdateService           — replaces SubIPUpdate (21 elems)  │
│    • PRM_PDAHCFNetworkQueueable           — replaces HFN sub-IP (async)       │
│    • PRM_PDAReviewFetchService            — replaces FetchFormPDAReview      │
│    • PRM_NoteService                      — thin wrapper                     │
│    • PRM_PayerNetworkUtil                 — compare/set payer info codes     │
│    • PRM_PDAPNCSelector                   — 8 PNC SOQL bundles               │
│    • PRM_PDAHCFNSelector                  — HCFN/payer network selectors     │
│    • PRM_PDACapitationSelector            — capitation reads                 │
│    • PRM_PDAKyruusSelector                — Kyruus on/off branch             │
│    • PRM_RelatedRecordSelector            — shared with ProviderChange flow  │
│    • PRM_PDADataTransformer               — UPDATE-shape mappers (12+)       │
│    • PRM_PNCRecordBuilder                 — PNC factory (replaces 7 IP elems)│
│    • PRM_RelatedRecordTransformer         — shared with ProviderChange flow  │
│    • PRM_PDAOrchestratorResult/InsertResult/UpdateResult/FetchResult — DTOs  │
│                                                                              │
│  TOTAL IP ELEMENTS BEING REPLACED: ~85 elements across 6 IPs                 │
│    (Orchestrator 10 + SubIPInsert 29 + SubIPUpdate 21 + HFN 2 +              │
│     Fetch 25 + Parents 4 ≈ 91 — but ~6 collapse into service returns)        │
│  TOTAL APEX CLASSES NEEDED: ~26 PDA-specific + reuse of 17 framework         │
│                              = 43 classes total in the inventory             │
│  TOTAL DATARAPTORS BEING RETIRED: 45 bundles                                 │
│  TOTAL REMOTE ACTIONS REPOINTED: 5 (all PRM_OmniUtils methods stay)          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Suggested Build Order (Sequencing recommendation)

Because the Update flow has the most UPDATE-DML risk (governor limits in committee-day spikes), build it first and prove the pattern, then layer in the Insert and Async pieces.

| Phase | Focus | Classes | Risk |
|-------|-------|---------|------|
| **P0** (1 sprint) | Foundation re-use validation | Extend `PRM_ServiceDispatcher`, add the 4 new Result DTOs, add the 1 new method on `PRM_CollectionUtil` (`listMergeWithDirectory`) and the 1 new method on `PRM_DeduplicationUtil` (`checkExistingPayerNetworkByName`). Sanity-test the existing framework against a no-op stub of `PRM_PDAReviewUpdateService`. | Very low |
| **P1** (1 sprint) | Selectors first | `PRM_PDAPNCSelector`, `PRM_PDAHCFNSelector`, `PRM_PDACapitationSelector`, `PRM_PDAKyruusSelector`, `PRM_RelatedRecordSelector`, plus the `PRM_*Selector` extensions in Par Form classes. Unit-test each against fixture data — they're side-effect-free. | Low |
| **P2** (2 sprints) | The UPDATE service | `PRM_PDARecordUpdateService` + `PRM_PDADataTransformer`. This is the hottest path (~12 SObjects updated). Land it behind a feature flag (`PRM_ParFormBypass__c` style) that flips `CBLogicForRecordUpdationIP` to call the new dispatcher. | Medium-High |
| **P3** (1.5 sprints) | The INSERT + Async | `PRM_PDANetworkInsertService` + `PRM_PNCRecordBuilder` + `PRM_PayerNetworkUtil` + `PRM_PDAHCFNetworkQueueable`. | Medium |
| **P4** (1 sprint) | The Orchestrator + Top entry | `PRM_PDAOrchestratorService` + `PRM_PDAReviewUpdateService` + `PRM_NoteService` + `PRM_IdentifierDocumentService` extension + `PRM_CaseDataManagerService` extension. Wire the OmniScript to call the new dispatcher route. | Medium |
| **P5** (1 sprint) | The Fetch path | `PRM_PDAReviewFetchService` + `PRM_RelatedRecordTransformer`. Lower-risk because it's read-only. | Low |
| **P6** | Retire | Delete `PRM_InitialCredPDAReviewUpdate*` IPs and their DataRaptors once the feature flag has been on in QA for two committee cycles. | Cleanup |

---

## 15. Side-by-side comparison: Par Form ↔ PDA Review

The whole point of doing PDA Review **second** is that we should be able to look at it through the lens of Par Form and see what's familiar.

| Capability | Par Form pattern | PDA Review pattern | Reuse cost |
|---|---|---|---|
| Thin Container IP → Apex Dispatcher | `PRM_CreateParFormRecordsContainer` calls `PRM_ParFormServiceDispatcher` | `PRM_InitialCredPDAReviewUpdateParent` calls **same** `PRM_ServiceDispatcher` (new actionName) | 🟢 0 |
| Try/catch + exception logging | `TryCatchBlock` → `PRM_ErrorLogger` | identical | 🟢 0 |
| Source IP tracking | `SV_SourceIPDetails` → `PRM_TransactionContext` | identical | 🟢 0 |
| Generic request/response wrapper | `PRM_ServiceRequest`/`Response` | identical | 🟢 0 |
| Feature flag read | `PRM_FeatureConfig.getSettings()` | identical (same `PRMGetFeatureConfigSetting` bundle source) | 🟢 0 |
| Per-record file create | `PRM_PractitionerScreenService.createDocumentFile` | extend → `PRM_IdentifierDocumentService.createIdentifierAndDocument` | 🟡 small extension |
| Case + CM creation/update | `PRM_CaseDataManagerService.updateCaseData` | extend → `createNewCaseForRetry` + reinstate flag | 🟡 small extension |
| Address selector / HCF selector / Practitioner selector | Already exist | extend with `getForReview` variants | 🟡 method additions |
| Multi-list merge (List Merge Action) | `PRM_CollectionUtil.listMerge` | add `listMergeWithDirectory` | 🟡 method addition |
| Bulk DML w/ partial success | `PRM_DMLUtil.bulkInsert/Update/Upsert` | identical | 🟢 0 |
| Loop Block → SObject conversion | not needed in Par Form (already SObject-shaped) | folded into `PRM_PNCRecordBuilder` | 🔴 new (PDA-specific) |
| Network/payer comparison (RA) | not needed in Par Form | `PRM_PayerNetworkUtil` | 🔴 new (PDA-specific) |
| Async heavy lift | `PRM_ParFormLevel4Batch` (Batchable) | `PRM_PDAHCFNetworkQueueable` (Queueable, mirrors today's IP) | 🔴 new flavor of existing pattern |
| PNC info code / HCF directory / vendor account flows | not in Par Form scope | `PRM_PDAPNCSelector`, `PRM_PDARecordUpdateService`, `PRM_PDADataTransformer` | 🔴 new |
| Kyruus on/off branch | not in Par Form scope | `PRM_PDAKyruusSelector` | 🔴 new (but isolated) |
| Capitation site reads | not in Par Form scope | `PRM_PDACapitationSelector` | 🔴 new |

**Read this as: every 🟢 row is engineering effort saved by having built Par Form first. Every 🔴 row is the genuinely new domain logic.**

---

## 16. Key Risks / Decisions Still Open

1. **Queueable vs Batchable for HCFN**. Today's IP already runs Queueable. Stay on Queueable as long as max HCFN rows per submission stays under ~2,500. `PRM_AsyncRouter` should compute this at runtime and silently switch if a single committee day produces an outlier.
2. **`PRMDRUpdateProviderFeature` bundle is shared by two elements (ProviderFeature + AFCC)**. Decision: keep two methods (`updateProviderFeature`, `updateAffirmingCareCategory`) that both ultimately call `PRM_DMLUtil.bulkUpdate` — same SObject `ProviderFeature` end target, but distinct payload shapes. Don't collapse them into one to avoid hidden polymorphism.
3. **Provider Change variant** (`PRM_ProviderChangePDAUpdate_English`) shares the Subroutines but uses a different Case owner lookup (the QUERY inside `DRCreateNewCase`). Cover it in `PRM_CaseDataManagerService.createNewCaseForRetry` via a `caseManagerRecordType` parameter — same method, branch internally on `Flow == 'Provider Change Form'`.
4. **QC variant** (`PRM_InitialCredPDAQC_English`) uses the **same** `PRM_FetchFormPDAReview` IP and a different submit path. Likely a Phase-2 service (`PRM_PDAQCService`) reusing all the same selectors. Keep that in mind so we don't accidentally bake "PDA Review & Update" assumptions into selectors.
5. **`failOnStepError: false` on `DRLoadHCFRecords` and `InitialCredPDAReviewHFN`** — these are tolerated soft-failures today. Replicate with `bulkUpsert/insertWithPartialSuccess` and log to `PRM_ExceptionLog__c` rather than throwing.
6. **`PRM_OmniUtils.comparePayerInfoCodesRecords`** is invoked twice in the chain (in the RA + downstream in DRTPNCRecords through `RASetRecords:result`). Audit the existing Apex method to make sure it's idempotent before factoring into `PRM_PayerNetworkUtil`.

---

## 17. Done-Definition

We will consider the migration complete when:

- [ ] `PRM_PDAReviewUpdateService` + 6 new services + 7 selectors + 2 transformers + 2 utilities deployed
- [ ] `PRM_ServiceDispatcher` advertises `InitialCredPDAReview.update` and `InitialCredPDAReview.load`
- [ ] Thin `PRM_InitialCredPDAReviewUpdateParent` and `PRM_FetchFormPDAReviewParent` IPs route to the dispatcher (3 elements each, no business logic)
- [ ] Feature flag `PRM_PDAReviewApexEnabled__c` toggles between IP-chain and Apex path
- [ ] All 45 retiring DataRaptors marked inactive (but not deleted) and excluded from package.xml
- [ ] Regression suite covers all 4 entry OmniScripts (PDA Review/Update, PDA QC, Provider Change PDA, and the PNC variant)
- [ ] After two committee cycles in QA, IPs and DataRaptors can be removed entirely

