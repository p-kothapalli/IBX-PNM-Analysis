# PNM Practitioner Participation Form - Record Creation Apex Service Architecture

## IP Audit & Apex Migration Blueprint

---

## 1. Current State: Complete IP Chain Audit

### 1.1 Full IP Orchestration Chain (As-Is)

```
OmniScript: PRM_PractitionerParticipationForm_English
  │
  └─► Submit Action
        │
        ▼
IP: PRM_CreateParFormRecordsContainer (Container - v1)
  ├── SV_SourceIPDetails .................... Set Values: source tracking
  ├── TryCatchBlock ......................... Error boundary
  │     └── IP_CreateParFormRecords ......... Calls child IP ──────────────────────────┐
  └── ResponseAction ........................ Final response to OmniScript            │
                                                                                      │
┌─────────────────────────────────────────────────────────────────────────────────────┘
│
▼
IP: PRM_CreateParFormRecords (Orchestrator - v20, active: v29)
  ├── [1] GetFeatureConfigSetting ........... DR Turbo: PRMGetFeatureConfigSetting
  │                                          (reads PNM feature flags/toggles)
  │
  ├── [2] IP_PractitionerScreenRecordCreation ... CONDITIONAL: IsExistingNPI == false ──────┐
  │                                                                                         │
  ├── [3] IP_PractitionerScreenExistingNPIRecordsUpdate ... CONDITIONAL: IsExistingNPI == true ──┐
  │                                                                                              │
  ├── [4] IP_CreateGroupScreenRecord ........ Group/Practice association records ──────────────┐ │
  │                                                                                            │ │
  ├── [5] IP_CreatePractitionerAddress ...... Location/Address/Facility records ────────────┐  │ │
  │                                                                                         │  │ │
  ├── [6] IP_CreateProviderScreenRecords .... Provider info (pronouns, language) ─────────┐ │  │ │
  │                                                                                       │ │  │ │
  ├── [7] IP_CreateContactScreenRecords ..... Primary/Secondary contacts ───────────────┐ │ │  │ │
  │                                                                                     │ │ │  │ │
  ├── [8] SV_PractitionerIds ................ Set Values: consolidate IDs              │ │ │  │ │
  └── [9] ResponseAction .................... Return to Container                      │ │ │  │ │
                                                                                       │ │ │  │ │
┌──────────────────────────────────────────────────────────────────────────────────────┘ │ │  │ │
│  IP: PRM_CreateContactScreenRecords (v5)                                               │ │  │ │
│  ├── SetValueContactRecordCreation ..... Prepare contact data                          │ │  │ │
│  ├── DRPCreatePrimaryContact ........... DR Post: PRMDRCreateContactRecords            │ │  │ │
│  │     Creates: Contact + ContactContactRelation (Primary)                             │ │  │ │
│  ├── DRPCreateSecondaryContact ......... DR Post: PRMDRCreateContactRecords            │ │  │ │
│  │     Creates: Contact + ContactContactRelation (Secondary)                           │ │  │ │
│  ├── DRUpdatePractitionerRecordIfPrimary .. DR Post: Update practitioner fields        │ │  │ │
│  ├── DRUpdatePractitionerRecordIfSecondary  DR Post: Update practitioner fields        │ │  │ │
│  ├── DRUpdatePrimarySecondary .......... DR Post: PRMDRPUpdatePrimarySecondaryContact  │ │  │ │
│  ├── DRUpdatecasedatamanager ........... DR Post: PRMDRPCaseDataManager                │ │  │ │
│  └── ResponseAction                                                                    │ │  │ │
│                                                                                        │ │  │ │
┌────────────────────────────────────────────────────────────────────────────────────────┘ │  │ │
│  IP: PRM_CreateProviderScreenRecords (v8)                                                │  │ │
│  ├── CreateContactProfileRecords ....... DR Post: PRMDRCreateContactProfileRecords       │  │ │
│  │     Creates: ContactProfile (Hispanic, Race, Ethnicity, Gender Identity)              │  │ │
│  ├── PersonLanguageBlock (Conditional Block)                                             │  │ │
│  │     ├── DRTransformPersonLanguage ... DR Transform: PRMDRTransformPersonLanguage      │  │ │
│  │     └── DRCreatePersonlanguage ...... DR Post: PRMDRCreatePersonLanguage              │  │ │
│  │           Creates: PersonLanguage records                                             │  │ │
│  └── PRMDRPCaseDataManager ............. DR Post: PRMDRPCaseDataManager                  │  │ │
│                                                                                          │  │ │
┌──────────────────────────────────────────────────────────────────────────────────────────┘  │ │
│  IP: PRM_CreatePractitionerAddressRecords (v40) *** MOST COMPLEX - 80+ ELEMENTS ***        │ │
│  (Full breakdown in Section 1.2 below)                                                     │ │
│                                                                                            │ │
┌────────────────────────────────────────────────────────────────────────────────────────────┘ │
│  IP: PRM_CreateGroupScreenRecord (v5)                                                       │
│  ├── DRCreateGroupScreenRecords ........ DR Post: PRMCreateGroupRecords                     │
│  │     Creates: HealthcareFacility (Group), HealthcareProviderNpi (Group NPI),              │
│  │              HealthcareFacilityNetwork, ProgramParticipation                             │
│  └── ResponseAction                                                                         │
│                                                                                              │
┌──────────────────────────────────────────────────────────────────────────────────────────────┘
│
│  BRANCH A: NEW NPI (IsExistingNPI == false)
│  IP: PRM_PractitionerScreenRecordCreation (v15)
│  ├── RA_TitleCase ...................... Remote Action: Title case names
│  ├── SV_PNCFlag ....................... Set Values: PNC flag logic
│  ├── DRPAccountCaseCaseManagerCreation  DR Post: PRMDRCreateCaseCaseManagerAndAccount
│  │     Creates: Account (Person Account) + Case + IndividualApplication (Case Manager)
│  ├── CreateFileForCaseMgr ............. Creates file/document attachment
│  ├── DRPProviderIdentifierAndProviderNPICreation  DR Post: PRMDRCreateProviderIdentifierNPI
│  │     Creates: HealthcareProvider + HealthcareProviderNpi + Identifier
│  ├── DRExtractTaxonomyData ............ DR Extract: Taxonomy lookup
│  ├── DRTTaxonomyData .................. DR Transform: Map taxonomies
│  ├── DRTDegreeData .................... DR Transform: Map degrees
│  ├── DRTBusinessLicenseData ........... DR Transform: Map licenses
│  ├── DRPEducationTaxanomyLicense ...... DR Post: PRMDRCreateEducationTaxanomyAndLicense
│  │     Creates: PersonEducation + BusinessLicense + CareProviderFacilitySpecialty (Taxonomy)
│  ├── PRMDRPCaseDataManager ............ DR Post: Update Case Data Manager
│  └── Response
│
│  BRANCH B: EXISTING NPI (IsExistingNPI == true)
│  IP: PRM_PractitionerScreenExistingNPIRecordUpdation (v12)
│  ├── DRExtractCaseManager ............. DR Extract: Get existing case manager
│  ├── DRPCaseCaseManagerCreationExistingNPI  DR Post: Create Case + IndividualApplication
│  ├── CreateFileForCaseMgr ............. Creates file/document
│  ├── DRPUddateProviderIdentifier ...... DR Post: Update existing identifier (CAQH)
│  ├── DRPProviderIdentifier ............ DR Post: Create new identifiers
│  ├── DRPExistingProviderIdentifier .... DR Post: Update existing provider identifiers
│  ├── DRPCaseManagerUpdate ............. DR Post: Update case manager fields
│  ├── DRPractitionerAccountUpdate ...... DR Post: Update Account fields
│  ├── RA_checkSpecialtyRecords ......... Remote Action: Check existing specialties
│  ├── RA_checkDegreeRecords ............ Remote Action: Check existing degrees
│  ├── RA_checkLicenseRecords ........... Remote Action: Check existing licenses
│  ├── DRExtractExistingTaxonomyData .... DR Extract: Get existing taxonomies
│  ├── DRExtractTaxonomyData ............ DR Extract: Get new taxonomy data
│  ├── DRTTaxonomyData .................. DR Transform: New taxonomies
│  ├── DRTTaxonomyDataExisting .......... DR Transform: Existing taxonomies
│  ├── DRTDegreeData .................... DR Transform: New degrees
│  ├── DRTDegree ........................ DR Transform: Existing degrees
│  ├── DRTBusinessLicenseData ........... DR Transform: New licenses
│  ├── DRTExistingBusinessLicenseData ... DR Transform: Existing licenses
│  ├── DRPEducation ..................... DR Post: Create/Update PersonEducation
│  ├── DRPExistingDegree ................ DR Post: Update existing degrees
│  ├── DRPBusinessLicense ............... DR Post: Create new BusinessLicense
│  ├── DRPExistingBusinessLicense ....... DR Post: Update existing licenses
│  ├── DRPTaxonomy ...................... DR Post: Create new taxonomies
│  ├── DRPExistingTaxonomy .............. DR Post: Update existing taxonomies
│  ├── DRPHealthcareProviderNPI ......... DR Post: Update HealthcareProviderNpi
│  ├── PRMDRPCaseDataManager ............ DR Post: Update Case Data Manager
│  ├── DRPRemovePrimaryFlag ............. DR Post: Remove primary from old records
│  └── Response
```

### 1.2 PRM_CreatePractitionerAddressRecords - Full Element Breakdown

This is the **most complex IP** with **80+ elements** handling multiple scenarios:

```
IP: PRM_CreatePractitionerAddressRecords (v40)
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION A: MANUALLY ENTERED ADDITIONAL ADDRESSES (Same NPI)
│ ═══════════════════════════════════════════════════════════════════
├── SV_EffectiveDate ........................... Set effective date
├── SV_ExistingGroupAddressList ................ Set existing group data
├── LA_FilterManuallyEneterdAddAddressListSameNPI  List Action: Filter
├── SV_ManuallyEneteredAddAddressListSameNPI ..... Set Values
├── ManuallyAddressToCreateWithSameNPI ......... Transform address data
├── CreateManuallyEnteredAdditionalAddressForExistingGroupSameNPI
│     DR Post: PRMDRCreatePractitionerAddressRecordswithNPI
│     Creates: Location + Address + HealthcareProviderNpi + HealthcareFacility + HCPF
├── TransformFacilityData ...................... DR Transform: Map facility
├── TransformProviderFeatureData ............... DR Transform: Map features
├── CreateProviderFeatureManuallyAddWithSameNPI  DR Post: ProviderFeature records
├── TransformAffirmingCareCategoryWithSameNPI .. DR Transform
├── CreateAffirmingCareCategoryWithSameNPI ..... DR Post: ACC records
├── TransformPFAAData .......................... DR Transform: PFAA data
├── CreatePFAAManuallAddWithSameNPI ............ DR Post: PFAA records
├── CreatePracFacilityNetworkManuallyAddWithSameNPI  DR Post: Network records
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION B: NEW PRACTICE LOCATION FOR EXISTING GROUP
│ ═══════════════════════════════════════════════════════════════════
├── SV_NewPracticeLocationForExistingGroup ..... Set Values
├── SV_ExistingGroupData ....................... Set existing group data
├── LB_NewPracticeLocationForExistingGroup ..... Loop Block (iterate locations)
│     ├── LB_Locations ........................ Nested Loop
│     ├── LA_FilterPracticeLoc ................ List Action: Filter
│     ├── SV_Locations ........................ Set Values per iteration
│     └── SV_FinalNewPracticeLocationsForExistingGroup
├── NewAdditionalPracticeLocationForExistingGroup
│     DR Post: PRMDRCreatePractitionerNewAddressRecords
│     Creates: Location + Address + HealthcareProviderNpi + HealthcareFacility + HCPF
├── CreatePracAddAddressNewPractice ............ DR Post: Additional address records
├── CheckIfPracticeToPractitionerAlreadyExist .. DR Extract: Dedup check
├── PracticeToPractitionerListMergeExisting .... Merge lists
├── FilterPracticeToPractitioner ............... Filter existing
├── CreateHCPFForPractitionerPracAffiliation ... DR Post: HCPF junction (existing practice)
├── UpdateHCPFForPractitonerPracAffiliation .... DR Post: Update existing HCPF
├── CreatePractitionerPracticeLocation ......... DR Post: Practice location link
├── TransformHCFacData ......................... DR Transform: HCFac for network
├── TransformProviderFeatureACC ................ DR Transform: ACC features
├── CreateProviderFeatureACC ................... DR Post: ProviderFeature (ACC)
├── TransformAffirmingCareCategory ............. DR Transform
├── CreateAffirmingCareCategory ................ DR Post: ACC records
├── TransformPFAA .............................. DR Transform: PFAA
├── CreateProviderFeatureAssitiveAids .......... DR Post: Assistive aids
├── CreatePractitionerFacilityNetwork .......... DR Post: HC Facility Network
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION C: MANUALLY ENTERED ADDITIONAL ADDRESSES (Different NPI)
│ ═══════════════════════════════════════════════════════════════════
├── LA_ManualluEnteredAddAddessslistWithDiffNPI  List Action: Filter
├── SV_ManuallyEneteredAddAddressListDiffNPI ... Set Values
├── ManuallyAddressToCreateWithDiffNPI ......... Transform
├── CreateManuallyEnteredAdditionalAddressForExistingGroupDiffNPI
│     DR Post: PRMDRCreatePractitionerAddressRecordswithNPIDelg
│     Creates: Location + Address + HealthcareProviderNpi + HealthcareFacility + HCPF
├── TransformFacilityDataWithDiffNPI ........... DR Transform
├── TransformProviderFeatureWithDiffNPI ........ DR Transform
├── CreateProviderFeatureManuallyAddWithDiffNPI  DR Post: ProviderFeature
├── TranformAffirmCareCatWithDiffNPI ........... DR Transform
├── CreateAffCareCatWithDiffNPI ................ DR Post: ACC
├── TranformPFAAWithDiffNPI .................... DR Transform: PFAA
├── CreatePFAAWithDiffNPI ...................... DR Post: PFAA
├── CreatePracFacilityNetworkManuallyAddWithDiffNPI  DR Post: Network
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION D: EXISTING ADDRESSES (NOT Manually Entered)
│ ═══════════════════════════════════════════════════════════════════
├── UpdateCaseManager .......................... DR Post: Update case data
├── LA_ExistingAddressManuallyEntered .......... List Action: Filter
├── SV_ExistingAddressNotManuallyEntered ....... Set Values
├── NotManuallyEneteredAddAddressList .......... Transform address list
├── CreateParHealthCareFacilityNetworkAddaddress  DR Post: HC Fac Network
├── CreateHealthCarePractitionerFacility ....... DR Post: HCPF link
│     Creates: HealthcarePractitionerFacility (junction)
├── TransformPFDataExistingAddPractice ......... DR Transform: Provider feature
├── CreatePracProviderFeatureExistingAddPrac ... DR Post: ProviderFeature
├── TansformAffCareCatExistingAddPractice ...... DR Transform: ACC
├── CreateAffCareCatExistingAddPractice ........ DR Post: ACC
├── TransformPFAADataExistingAddPractice ....... DR Transform: PFAA
├── CreatePFAAExistingAddPractice .............. DR Post: PFAA
├── UpdateCaseManager2 ......................... DR Post: Update case
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION E: NEW GROUP ADDRESSES
│ ═══════════════════════════════════════════════════════════════════
├── SV_NewGroupAddressList ..................... Set Values
├── NewGroupAddress ............................ Transform new group address
├── MergeGroupIdWithNewGroupAddressList ........ Merge group IDs
├── PRMDRCreatePractitionerAddressRecords ...... DR Post: PRMDRCreatePractitionerNewAddressRecords
│     Creates: Location + Address + HealthcareProviderNpi + HealthcareFacility + HCPF
├── DRCreateHCPFForPractitionerPracAffiliation  DR Post: Additional HCPF
├── TransformFacilityDataWithNewGroup .......... DR Transform
├── TransformProviderFeatureNewAddress ......... DR Transform: Feature
├── CreateProviderFeatureNewAddress ............ DR Post: ProviderFeature
├── TransformAffCareCatNewAddress .............. DR Transform: ACC
├── CreateAffCareCatNewAddress ................. DR Post: ACC
├── TransformPFAANewAddress .................... DR Transform: PFAA
├── CreatePFANewAddress ........................ DR Post: PFAA
├── CreateParHCFacilityNetwork ................. DR Post: Network
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION F: TELEHEALTH & INFO CODES
│ ═══════════════════════════════════════════════════════════════════
├── LATelehealthFacilities1 .................... List Action: Filter telehealth
├── DRLoadInfoCodeAssigned1 .................... DR Post: Info code for facilities
├── LATelehealthFacilities2 .................... List Action: Filter telehealth
├── DRLoadInfoCodeAssigned2 .................... DR Post: Info code for facilities
├── LATelehealthPracFacilities1 ................ List Action: Filter prac facilities
├── DRLoadInfoCodeAssignedPracFacilities1 ...... DR Post: Info code
├── LATelehealthPracFacilities2 ................ List Action: Filter prac facilities
├── DRLoadInfoCodeAssignedPracFacilities2 ...... DR Post: Info code
│
│ ═══════════════════════════════════════════════════════════════════
│ SECTION G: CASE MANAGER & PROVIDER FEATURE FINALIZATION
│ ═══════════════════════════════════════════════════════════════════
├── UpdateCaseDataManager ...................... DR Post: Final case data update
└── CreatePractitionerProviderFeature .......... DR Post: Final provider features
```

---

## 2. Complete Record Inventory (What Gets Created/Updated)

### 2.1 SObjects Touched by the PAR Form IP Chain

| # | SObject | Operation | IP Source | Scenario |
|---|---------|-----------|-----------|----------|
| 1 | **Account** (Person Account) | INSERT | PractitionerScreenRecordCreation | New NPI |
| 2 | **Case** | INSERT | PractitionerScreenRecordCreation | Always |
| 3 | **IndividualApplication** (Case Manager) | INSERT | PractitionerScreenRecordCreation | Always |
| 4 | **HealthcareProvider** | INSERT | PractitionerScreenRecordCreation | New NPI |
| 5 | **HealthcareProviderNpi** (Individual) | INSERT | PractitionerScreenRecordCreation | New NPI |
| 6 | **Identifier** (CAQH) | INSERT | PractitionerScreenRecordCreation | New NPI |
| 7 | **PersonEducation** | INSERT | PractitionerScreenRecordCreation | New NPI |
| 8 | **BusinessLicense** | INSERT | PractitionerScreenRecordCreation | New NPI |
| 9 | **CareProviderFacilitySpecialty** (Taxonomy) | INSERT | PractitionerScreenRecordCreation | New NPI |
| 10 | **ContentVersion** (File) | INSERT | PractitionerScreenRecordCreation | Always |
| 11 | **HealthcareFacility** (Group) | INSERT | CreateGroupScreenRecord | New Group |
| 12 | **HealthcareProviderNpi** (Group NPI) | INSERT | CreateGroupScreenRecord | New Group |
| 13 | **HealthcareFacilityNetwork** (Group) | INSERT | CreateGroupScreenRecord | New Group |
| 14 | **PRM_ProgramParticipation__c** | INSERT | CreateGroupScreenRecord | New Group |
| 15 | **Location** | INSERT | CreatePractitionerAddressRecords | New Address |
| 16 | **Address** | INSERT | CreatePractitionerAddressRecords | New Address |
| 17 | **HealthcareProviderNpi** (Location) | INSERT | CreatePractitionerAddressRecords | New Address |
| 18 | **HealthcareFacility** (Location) | INSERT | CreatePractitionerAddressRecords | New Address |
| 19 | **HealthcarePractitionerFacility** (HCPF) | INSERT | CreatePractitionerAddressRecords | Always |
| 20 | **HealthcareFacilityNetwork** (Location) | INSERT | CreatePractitionerAddressRecords | New Address |
| 21 | **PractitionerFacilityAffiliation** (PFAA) | INSERT | CreatePractitionerAddressRecords | Conditional |
| 22 | **AffirmingCareCategory** (ACC) | INSERT | CreatePractitionerAddressRecords | Conditional |
| 23 | **ProviderFeature** | INSERT | CreatePractitionerAddressRecords | Conditional |
| 24 | **ProviderFeature** (Assistive Aids) | INSERT | CreatePractitionerAddressRecords | Conditional |
| 25 | **ProviderFeature** (ACC-linked) | INSERT | CreatePractitionerAddressRecords | Conditional |
| 26 | **InformationCodeAssigned** (Telehealth) | INSERT | CreatePractitionerAddressRecords | Telehealth |
| 27 | **ContactProfile** | INSERT | CreateProviderScreenRecords | Always |
| 28 | **PersonLanguage** | INSERT | CreateProviderScreenRecords | Has languages |
| 29 | **Contact** (Primary) | INSERT | CreateContactScreenRecords | Has contact |
| 30 | **Contact** (Secondary) | INSERT | CreateContactScreenRecords | Has contact |
| 31 | **ContactContactRelation** | INSERT | CreateContactScreenRecords | Has contact |
| 32 | **Account** | UPDATE | ExistingNPIRecordUpdation | Existing NPI |
| 33 | **Identifier** | UPDATE | ExistingNPIRecordUpdation | Existing NPI |
| 34 | **PersonEducation** | UPDATE | ExistingNPIRecordUpdation | Existing NPI |
| 35 | **BusinessLicense** | UPDATE | ExistingNPIRecordUpdation | Existing NPI |
| 36 | **CareProviderFacilitySpecialty** | UPDATE | ExistingNPIRecordUpdation | Existing NPI |
| 37 | **IndividualApplication** | UPDATE | Multiple IPs | Case data updates |

### 2.2 Estimated Record Counts Per Submission

| Scenario | Min Records | Max Records | DML Statements |
|----------|-------------|-------------|----------------|
| New NPI + 1 New Location (simple) | 18 | 22 | 15-18 |
| New NPI + 3 Locations (complex) | 30 | 45 | 25-35 |
| Existing NPI + 1 New Location | 12 | 18 | 12-15 |
| Existing NPI + 3 Existing Addresses | 8 | 15 | 10-12 |
| New NPI + New Group + 5 Locations | 45 | 70+ | 40-55 |

---

## 3. Architecture Overview - Apex Service Layer Diagram (To-Be)

```
+====================================================================================+
|                         OMNISTUDIO PRESENTATION LAYER                                |
|  OmniScript: PRM_PractitionerParticipationForm_English                              |
|  OmniScript: PRM_PractitionerParticipationAddressForm_English                       |
|  OmniScript: PRM_PractitionerParticipationReviewScreen_English                      |
+====================================================================================+
         |
         | Remote Action (single call replaces entire IP chain)
         v
+====================================================================================+
|                    CONTROLLER / DISPATCHER LAYER                                     |
|                                                                                      |
|  PRM_ParFormServiceDispatcher                                                        |
|    implements vlocity_ins.VlocityOpenInterface2                                      |
|    - Receives full OmniScript JSON payload                                           |
|    - Routes to PRM_ParFormRecordCreationService                                      |
|    - Returns PRM_ServiceResponse (success + batchJobId + summary)                    |
+====================================================================================+
         |
         v
+====================================================================================+
|                         SERVICE LAYER (Business Logic)                                |
|                                                                                      |
|  PRM_ParFormRecordCreationService  (extends PRM_BaseService)                         |
|    │                                                                                 |
|    ├── SYNC: Transaction 1 (TX1) - Critical Path Records                            |
|    │   ├── PRM_PractitionerScreenService                                             |
|    │   │     (Account, Case, IndividualApplication, HealthcareProvider,               |
|    │   │      HealthcareProviderNpi, Identifier, File upload)                         |
|    │   ├── PRM_GroupScreenService                                                    |
|    │   │     (HealthcareFacility-Group, HealthcareProviderNpi-Group,                  |
|    │   │      HealthcareFacilityNetwork, ProgramParticipation)                        |
|    │   └── PRM_AddressRecordService (Core records ONLY)                              |
|    │         (Location, Address, HealthcareProviderNpi-Location,                      |
|    │          HealthcareFacility-Location, HealthcarePractitionerFacility)             |
|    │                                                                                 |
|    └── ASYNC: Transaction 2 (TX2) - Level 4 Batch                                   |
|        └── PRM_ParFormLevel4Batch (Database.Batchable + Database.Stateful)           |
|              ├── ProviderFeature records                                              |
|              ├── AffirmingCareCategory records                                        |
|              ├── PractitionerFacilityAffiliation (PFAA) records                       |
|              ├── HealthcareFacilityNetwork (per location)                             |
|              ├── InformationCodeAssigned (Telehealth)                                 |
|              ├── ContactProfile + PersonLanguage                                      |
|              ├── Contact (Primary/Secondary) + ContactContactRelation                 |
|              ├── PersonEducation + BusinessLicense + Taxonomy                         |
|              └── Final Case Data Manager updates                                      |
|                                                                                      |
+====================================================================================+
         |                    |                     |                    |
         v                    v                     v                    v
+===============+ +================+ +==================+ +==================+
| SELECTOR      | | UTILITY        | | TRANSFORM        | | ASYNC FRAMEWORK  |
| LAYER         | | LAYER          | | LAYER            | |                  |
+===============+ +================+ +==================+ +==================+
|               | |                | |                  | |                  |
| PRM_Pract     | | PRM_DMLUtil    | | PRM_ParForm      | | PRM_ParForm      |
|  Selector     | |  .bulkInsert() | |  DataTransformer | |  Level4Batch     |
|               | |  .bulkUpsert() | |                  | |                  |
| PRM_Facility  | |  .bulkUpdate() | | - mapToPerson    | | PRM_ParForm      |
|  Selector     | |                | |   Account()      | |  QueueableChain  |
|               | | PRM_Collection | | - mapToLocation  | |                  |
| PRM_Address   | |  Util          | |   Address()      | | PRM_Async        |
|  Selector     | |  .chunk()      | | - mapToHCPF()    | |  Complete__e     |
|               | |  .mapByField() | | - mapToACC()     | |  (Platform Event)|
| PRM_Network   | |  .groupBy()    | | - mapToPFAA()    | |                  |
|  Selector     | |  .pluckIds()   | | - mapToProvider  | |                  |
|               | |                | |   Feature()      | |                  |
| PRM_Case      | | PRM_Governor   | | - mapToNetwork() | |                  |
|  Selector     | |  Util          | | - mapToTelehealt | |                  |
|               | |  .canQuery()   | |   hInfoCode()    | |                  |
|               | |  .canDML()     | | - mapToLanguage  | |                  |
|               | |  .hasHeap()    | |   ()             | |                  |
|               | |                | | - mapToContact() | |                  |
+===============+ +================+ +==================+ +==================+
         |                    |                     |                    |
         v                    v                     v                    v
+====================================================================================+
|                         CROSS-CUTTING CONCERNS                                       |
|                                                                                      |
|  PRM_ErrorLogger ......... Platform Event → PRM_ExceptionLog__c                      |
|  PRM_TransactionContext ... Transaction ID correlation                                |
|  PRM_FeatureConfig ........ Custom Metadata (PRMGetFeatureConfigSetting equivalent)   |
|  PRM_TitleCaseUtil ........ Name formatting (replaces RA_TitleCase Remote Action)     |
|  PRM_DeduplicationUtil .... Checks existing records before insert                    |
+====================================================================================+
         |
         v
+====================================================================================+
|                         SALESFORCE DATA MODEL                                        |
|                                                                                      |
|  LEVEL 1 (Practitioner Core):                                                        |
|    Account (Person), Case, IndividualApplication, HealthcareProvider,                 |
|    HealthcareProviderNpi (Individual), Identifier, ContentVersion                     |
|                                                                                      |
|  LEVEL 2 (Group/Practice):                                                           |
|    HealthcareFacility (Group), HealthcareProviderNpi (Group),                         |
|    HealthcareFacilityNetwork, PRM_ProgramParticipation__c                             |
|                                                                                      |
|  LEVEL 3 (Location/Address):                                                         |
|    Location, Address, HealthcareProviderNpi (Location),                               |
|    HealthcareFacility (Location), HealthcarePractitionerFacility (HCPF)               |
|                                                                                      |
|  LEVEL 4 (Ancillary - via Batch):                                                    |
|    ProviderFeature, AffirmingCareCategory, PractitionerFacilityAffiliation,           |
|    HealthcareFacilityNetwork (per location), InformationCodeAssigned,                  |
|    ContactProfile, PersonLanguage, Contact, ContactContactRelation,                   |
|    PersonEducation, BusinessLicense, CareProviderFacilitySpecialty                    |
|                                                                                      |
|  UPDATES (Existing Records):                                                         |
|    Account, Identifier, PersonEducation, BusinessLicense,                             |
|    CareProviderFacilitySpecialty, IndividualApplication, HealthcareProviderNpi         |
+====================================================================================+
```

---

## 4. Detailed IP-to-Service Migration Mapping

### 4.1 What Stays in the Thin IP (Router Only)

```
THIN IP: PRM_CreateParFormRecordsContainer (KEEP - simplified)
  Step 1: Set Values (prepare input)
  Step 2: Remote Action → PRM_ParFormServiceDispatcher
  Step 3: Response Action (map output)
```

### 4.2 Migration Matrix: IP Element → Apex Service Method

| IP | Element Name | Type | DataRaptor Bundle | Apex Service Method |
|---|---|---|---|---|
| **PRM_CreateParFormRecords** | GetFeatureConfigSetting | DR Turbo | PRMGetFeatureConfigSetting | `PRM_FeatureConfig.getSettings()` |
| | | | | |
| **PRM_PractitionerScreenRecordCreation** | RA_TitleCase | Remote Action | — | `PRM_TitleCaseUtil.formatNames()` |
| | SV_PNCFlag | Set Values | — | `PRM_PractitionerScreenService.determinePNCFlag()` |
| | DRPAccountCaseCaseManagerCreation | DR Post | PRMDRCreateCaseCaseManagerAndAccount | `PRM_PractitionerScreenService.createAccountCaseCaseManager()` |
| | CreateFileForCaseMgr | File Upload | — | `PRM_PractitionerScreenService.createDocumentFile()` |
| | DRPProviderIdentifierAndProviderNPICreation | DR Post | PRMDRCreateProviderIdentifierNPI | `PRM_PractitionerScreenService.createProviderIdentifierNPI()` |
| | DRExtractTaxonomyData | DR Extract | — | `PRM_PractitionerSelector.getTaxonomyData()` |
| | DRTTaxonomyData | DR Transform | — | `PRM_ParFormDataTransformer.mapToTaxonomy()` |
| | DRTDegreeData | DR Transform | — | `PRM_ParFormDataTransformer.mapToDegree()` |
| | DRTBusinessLicenseData | DR Transform | — | `PRM_ParFormDataTransformer.mapToBusinessLicense()` |
| | DRPEducationTaxanomyLicense | DR Post | PRMDRCreateEducationTaxanomyAndLicense | `PRM_PractitionerScreenService.createEducationTaxonomyLicense()` |
| | PRMDRPCaseDataManager | DR Post | PRMDRPCaseDataManager | `PRM_CaseDataManagerService.updateCaseData()` |
| | | | | |
| **PRM_PractitionerScreenExistingNPIRecordUpdation** | DRExtractCaseManager | DR Extract | — | `PRM_CaseSelector.getExistingCaseManager()` |
| | DRPCaseCaseManagerCreationExistingNPI | DR Post | — | `PRM_PractitionerScreenService.createCaseForExistingNPI()` |
| | DRPUddateProviderIdentifier | DR Post | — | `PRM_PractitionerScreenService.updateProviderIdentifier()` |
| | DRPProviderIdentifier | DR Post | — | `PRM_PractitionerScreenService.createNewIdentifiers()` |
| | DRPExistingProviderIdentifier | DR Post | — | `PRM_PractitionerScreenService.updateExistingIdentifiers()` |
| | DRPCaseManagerUpdate | DR Post | — | `PRM_CaseDataManagerService.updateCaseManager()` |
| | DRPractitionerAccountUpdate | DR Post | — | `PRM_PractitionerScreenService.updatePractitionerAccount()` |
| | RA_checkSpecialtyRecords | Remote Action | — | `PRM_DeduplicationUtil.checkExistingSpecialties()` |
| | RA_checkDegreeRecords | Remote Action | — | `PRM_DeduplicationUtil.checkExistingDegrees()` |
| | RA_checkLicenseRecords | Remote Action | — | `PRM_DeduplicationUtil.checkExistingLicenses()` |
| | DRExtractExistingTaxonomyData | DR Extract | — | `PRM_PractitionerSelector.getExistingTaxonomies()` |
| | DRPEducation/DRPExistingDegree | DR Post | — | `PRM_PractitionerScreenService.upsertEducation()` |
| | DRPBusinessLicense/Existing | DR Post | — | `PRM_PractitionerScreenService.upsertBusinessLicenses()` |
| | DRPTaxonomy/Existing | DR Post | — | `PRM_PractitionerScreenService.upsertTaxonomies()` |
| | DRPHealthcareProviderNPI | DR Post | — | `PRM_PractitionerScreenService.updateHealthcareProviderNPI()` |
| | DRPRemovePrimaryFlag | DR Post | — | `PRM_PractitionerScreenService.removePreviousPrimaryFlag()` |
| | | | | |
| **PRM_CreateGroupScreenRecord** | DRCreateGroupScreenRecords | DR Post | PRMCreateGroupRecords | `PRM_GroupScreenService.createGroupRecords()` |
| | | | | |
| **PRM_CreatePractitionerAddressRecords** | (ALL - See Section E below) | Various | Various | `PRM_AddressRecordService.*` + `PRM_ParFormLevel4Batch.*` |
| | | | | |
| **PRM_CreateProviderScreenRecords** | CreateContactProfileRecords | DR Post | PRMDRCreateContactProfileRecords | `PRM_ProviderScreenService.createContactProfile()` |
| | DRTransformPersonLanguage | DR Transform | PRMDRTransformPersonLanguage | `PRM_ParFormDataTransformer.mapToPersonLanguage()` |
| | DRCreatePersonlanguage | DR Post | PRMDRCreatePersonLanguage | `PRM_ProviderScreenService.createPersonLanguage()` |
| | | | | |
| **PRM_CreateContactScreenRecords** | DRPCreatePrimaryContact | DR Post | PRMDRCreateContactRecords | `PRM_ContactScreenService.createPrimaryContact()` |
| | DRPCreateSecondaryContact | DR Post | PRMDRCreateContactRecords | `PRM_ContactScreenService.createSecondaryContact()` |
| | DRUpdatePractitionerRecordIfPrimary | DR Post | — | `PRM_ContactScreenService.updatePractitionerContactLink()` |
| | DRUpdatePrimarySecondary | DR Post | PRMDRPUpdatePrimarySecondaryContact | `PRM_ContactScreenService.updatePrimarySecondaryRelation()` |

---

## 5. Apex Service Classes - Detailed Responsibility Breakdown

### 5.1 PRM_ParFormRecordCreationService (Orchestrator)

> **Why we need it** — The Par Form is the heaviest IP chain in PNM (7 IPs, 130+ elements, peak CPU 5–7 s) and routinely brushes governor limits in production. Without a single orchestrator that owns the sync-vs-async split, each downstream service would have to make its own delegation decisions and the critical path would still breach limits on a 5+ location practitioner.
>
> **How it helps** — Owns the high-level flow: load feature config, branch on `IsExistingNPI`, call `PRM_PractitionerScreenService`, `PRM_GroupScreenService`, `PRM_AddressRecordService`, `PRM_ProviderScreenService`, and `PRM_ContactScreenService` for the sync TX1 critical path (everything the next OmniScript screen displays — see § 7). Then it enqueues `PRM_ParFormLevel4Batch` via `PRM_AsyncEnqueueGuard.safeEnqueue(...)` for the async TX2 fan-out records, so an exhausted Queueable cap falls back to inline execution rather than silently dropping the work. Returns to the OmniScript with the `caseId` immediately.
>
> **Outcome** — Sync TX1 < 1 s on a 5-location new-NPI submission. The TX1/TX2 split it owns becomes the template every later orchestrator (PDA, Off Cycle, Reinstate) reuses.

```java
/**
 * Main orchestrator for Par Form record creation.
 * Replaces: PRM_CreateParFormRecords IP
 *
 * SYNC (TX1): every record the next OmniScript screen reads (see § 7).
 * ASYNC (TX2): per-facility / per-network fan-out only.
 */
public class PRM_ParFormRecordCreationService extends PRM_BaseService {

    { ASYNC_RECORD_THRESHOLD = 50; }

    @TestVisible private PRM_PractitionerScreenService practitionerService;
    @TestVisible private PRM_GroupScreenService        groupService;
    @TestVisible private PRM_AddressRecordService      addressService;
    @TestVisible private PRM_ProviderScreenService     providerService;
    @TestVisible private PRM_ContactScreenService      contactService;

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest request) {

        // 1. Load feature config (replaces GetFeatureConfigSetting DR Turbo)
        Map<String, Object> featureConfig = PRM_FeatureConfig.getSettings();

        // 2. New NPI vs Existing NPI
        Boolean isExistingNPI = (Boolean) request.parameters.get('IsExistingNPI');
        PRM_PractitionerScreenResult practResult = isExistingNPI
            ? practitionerService.updateExistingPractitioner(request, featureConfig)
            : practitionerService.createNewPractitioner(request, featureConfig);

        // 3. Group screen records (HCFacility(Group), Group NPI, HCFN, ProgramParticipation)
        PRM_GroupScreenResult groupResult = groupService.createGroupRecords(
            request, practResult.caseManagerId,
            (Boolean) request.parameters.get('multipleGroupNPIS')
        );

        // 4. Address core records — Level 3 — via PRM_BulkOperation.chain()
        PRM_AddressRecordResult addressResult = addressService.createCoreAddressRecords(
            request, practResult, groupResult
        );

        // 5. User-visible records (the next OmniScript screen renders these)
        providerService.createContactProfile(practResult, request.parameters);  // TX1
        providerService.createPersonLanguages(practResult, request.parameters); // TX1
        contactService.createContacts(practResult, request.parameters);         // TX1

        // 6. Telehealth InformationCodeAssigned for the new HCFacilities — TX1
        addressService.createTelehealthInfoCodes(addressResult);

        // 7. Stamp owned CM flags for the in-flight phase
        PRM_CaseDataMgrPatcher.patch('ParForm', practResult.caseManagerId,
            new Map<String, Object>{
                'PRM_AccountFlag__c'         => true,
                'PRM_HCFFlag__c'             => true,
                'PRM_HCPFFlag__c'            => true,
                'PRM_ContentVersionFlag__c'  => true
            });

        // 8. Hand off the per-facility fan-out (ProviderFeature, ACC, PFAA, HCFN ...) to TX2.
        //    Guard the enqueue: if the Queueable cap is exhausted, run the batch inline.
        PRM_ParFormLevel4Batch batch = new PRM_ParFormLevel4Batch();
        batch.setContext(request, practResult, groupResult, addressResult, featureConfig);
        Integer estimatedRows = batch.estimateRowCount();

        PRM_AsyncEnqueueGuard.Result async = PRM_AsyncEnqueueGuard.safeEnqueue(
            batch,
            new Runnable() { public void run() { batch.executeInline(); } },
            estimatedRows,
            response   // PRM_ServiceResult
        );

        // 9. Return summary
        return buildResponse(request, practResult, groupResult, addressResult, async);
    }
}
```

### 5.2 PRM_PractitionerScreenService

> **Why we need it** — Today the Practitioner screen logic lives in two of the heaviest IPs in the chain: `PRM_PractitionerScreenRecordCreation` (12 elements, new-NPI path) and `PRM_PractitionerScreenExistingNPIRecordUpdation` (28 elements, existing-NPI path). The branching logic ("did the user enter an NPI we already have?") is duplicated across both, and the existing-NPI path silently mutates Account/HealthcareProvider/Identifier records with no audit trail.
>
> **How it helps** — One service, two methods (`createNewPractitioner` and `updateExistingPractitioner`), share the same data transforms (via `PRM_ParFormDataTransformer`), the same dedup checks (via `PRM_DeduplicationUtil`), and the same DML (via `PRM_DMLUtil`). The orchestrator picks the right method based on `IsExistingNPI` instead of re-implementing the routing inside the service. Returns a typed `PRM_PractitionerScreenResult` so downstream services don't have to re-query the new ids.
>
> **Outcome** — 40 IP elements collapse into ~250 lines of testable Apex. New-NPI vs existing-NPI behaviour is now visible in one diff during code review.

```
Replaces:
  - PRM_PractitionerScreenRecordCreation (entire IP, 12 elements)
  - PRM_PractitionerScreenExistingNPIRecordUpdation (entire IP, 28 elements)

Methods:
  createNewPractitioner(request, featureConfig)
    → Account (Person Account)
    → Case
    → IndividualApplication (Case Manager)
    → HealthcareProvider
    → HealthcareProviderNpi (Individual)
    → Identifier (CAQH)
    → ContentVersion (File upload)
    → PersonEducation (degrees)
    → BusinessLicense (licenses)
    → CareProviderFacilitySpecialty (taxonomies)
    Returns: PRM_PractitionerScreenResult { accountId, caseId, caseManagerId, 
             healthcareProviderId, healthcareProviderNpiId, personContactId }

  updateExistingPractitioner(request, featureConfig)
    → Case (new)
    → IndividualApplication (new Case Manager)
    → Identifier (insert new CAQH)         ← MUST succeed before next step
    → Account (update person account fields)
    → PersonEducation (upsert)
    → BusinessLicense (upsert)
    → CareProviderFacilitySpecialty (upsert - with dedup check)
    → HealthcareProviderNpi (update)
    → Remove previous primary identifier flag
        ── runs LAST and is gated on a non-null newPrimaryCaqhId.
        ── If the new identifier insert above failed (newPrimaryCaqhId == null),
           the legacy primary stays active. Surface the failure to the user;
           never leave the practitioner with zero active primary identifier.
    Returns: PRM_PractitionerScreenResult { same structure }

Internal utilities called:
  - PRM_TitleCaseUtil.formatNames(firstName, middleName, lastName)
  - PRM_DeduplicationUtil.checkExistingSpecialties(providerId)
  - PRM_DeduplicationUtil.checkExistingDegrees(accountId)
  - PRM_DeduplicationUtil.checkExistingLicenses(accountId)
  - PRM_PractitionerSelector.getTaxonomyData(specialtyCodes)
  - PRM_ParFormDataTransformer.mapToTaxonomy(rawData)
  - PRM_ParFormDataTransformer.mapToDegree(rawData)
  - PRM_ParFormDataTransformer.mapToBusinessLicense(rawData)
  - PRM_DMLUtil.bulkInsert(records, 200)
```

### 5.3 PRM_GroupScreenService

> **Why we need it** — The Group screen is small in element count (only 2 elements in `PRM_CreateGroupScreenRecord`) but it owns critical Group-level records — `HealthcareFacility(Group)`, `HealthcareProviderNpi(Group)`, `HealthcareFacilityNetwork`, `PRM_ProgramParticipation__c` — that every downstream service depends on. The "MultipleGroupNPIS" case forks the row count, and that branching has no test coverage today.
>
> **How it helps** — One method (`createGroupRecords`) creates all four Group SObjects via `PRM_BulkOperation.chain()` (Group HCFacility ➜ Group NPI ➜ HCFN, FK-linked) and accepts an explicit `multipleGroupNPIS` flag from the orchestrator so the multi-NPI fork is a typed parameter, not implicit IP-level branching. The transformer is split into `mapToGroupNPI.single(...)` and `mapToGroupNPI.multiple(groupInfo.groupNpis[])` with a fixture per case. Returns `PRM_GroupScreenResult` with the new ids for `PRM_AddressRecordService` to consume.
>
> **Outcome** — Group records ship in a single chained DML round-trip with junction-orphan elimination by construction. The multi-NPI case is now exercised by unit tests rather than discovered in production.

```
Replaces:
  - PRM_CreateGroupScreenRecord (entire IP, 2 elements)

Methods:
  createGroupRecords(request, caseManagerId, Boolean multipleGroupNPIS)
    PRM_BulkOperation.chain()
      .insertParents(groupHCFacility)                           // 1
      .bindChildFK(groupNpi[],   'HealthcareFacilityId')        // 2  one or many
      .bindChildFK(groupHCFN[],  'HealthcareFacilityId')        // 3
      .insertChildren(...)
      .execute(res);
    + PRM_ProgramParticipation__c (insert, FK to Group HCFacility)
    Returns: PRM_GroupScreenResult { groupFacilityId, groupFacilityIds[], groupNetworkIds[] }

Internal utilities called:
  - PRM_ParFormDataTransformer.mapToGroupFacility(groupInfo, caseManagerId)
  - PRM_ParFormDataTransformer.mapToGroupNPI.single(groupInfo)        // multipleGroupNPIS == false
  - PRM_ParFormDataTransformer.mapToGroupNPI.multiple(groupInfo.groupNpis[]) // == true
  - PRM_BulkOperation.chain()    (replaces a raw bulkInsert; junction-orphan-safe)
```

### 5.4 PRM_AddressRecordService

> **Why we need it** — `PRM_CreatePractitionerAddressRecords` is the single largest IP in PNM at **80+ elements** and accounts for the majority of the Par Form's CPU and DML footprint. It branches across **5 distinct address scenarios** (Same NPI manual, New location existing group, Different NPI manual, Existing address linked, New group address) and each branch creates a different combination of Location / Address / HCProviderNpi(Location) / HealthcareFacility / HealthcarePractitionerFacility records. Today that scenario logic is encoded in conditional blocks scattered across the IP — almost impossible to reason about, impossible to unit-test. On top of that, `Location → Address → HCFacility → HCPF` is an FK chain: a partial-success failure at any tier without the right plumbing leaves orphan junction rows in the database.
>
> **How it helps** — A single `createCoreAddressRecords` method categorises incoming addresses into scenarios A–E using `PRM_CollectionUtil.groupByField`, runs the dedup check via `PRM_DeduplicationUtil.checkExistingPracticeLink` once (returning a typed `Map<HCFacilityId, existing HCPF Id>` for insert-vs-update routing), and writes the FK chain via `PRM_BulkOperation.chain()` so a `Location[2]` insert failure drops `Address[2]`, `HCFacility[2]`, and `HCPF[2]` from the DML before they create orphans. Returns a `PRM_AddressRecordResult` with a `scenarioMap` so the caller knows which records belong to which scenario. A separate `createTelehealthInfoCodes(addressResult)` method runs in TX1 to stamp `InformationCodeAssigned` rows for the new HCFacilities — these are user-visible on the next OmniScript screen.
>
> **Outcome** — The 80+ element monster IP collapses to ~400 lines of Apex with explicit scenario routing. Each of the 5 scenarios gets its own unit test. Production CPU on this leg drops from 3-4 s to under 500 ms. Junction orphans become impossible by construction. Resubmission is idempotent: scenario B/D dedup hits route to `bulkUpdate`, not duplicate `bulkInsert`.

```
Replaces:
  - PRM_CreatePractitionerAddressRecords (PARTIAL - Level 3 core records only)
  - Specifically: Location + Address + HCProviderNpi + HCFacility + HCPF creation
  - PLUS: Telehealth InformationCodeAssigned rows for new HCFacilities (TX1)

Handles ALL 5 Scenarios:
  A. Manually entered additional address (Same NPI)
  B. New practice location for existing group        ← dedup-aware: insert OR update
  C. Manually entered additional address (Different NPI)
  D. Existing address (not manually entered) - just link HCPF  ← dedup-aware: update only
  E. New group address

Methods:
  createCoreAddressRecords(request, practResult, groupResult)
    → Categorize addresses into scenarios A-E
    → Run dedup once: PRM_DeduplicationUtil.checkExistingPracticeLink(...)
        returns Map<HCFacilityId, existing HCPF Id>
    → For each new address (Scenarios A, C, E and B-without-existing-link):
        PRM_BulkOperation.chain()
          .insertParents(locations)                       // 1
          .bindChildFK(addresses, 'LocationId')           // 2
          .bindChildFK(locationNpis, 'LocationId')        // 3
          .insertChildren(...)                            // 4
        + Second chain:
          .insertParents(facilities)                      // 5  FK = LocationId + GroupAccountId
          .bindChildFK(hcpfNew, 'HealthcareFacilityId')   // 6
          .insertChildren(...)
    → For Scenarios B (with existing link) and D (existing address):
        bulkUpdate(hcpfExisting, [...]);                  // route to UPDATE not INSERT
    Returns: PRM_AddressRecordResult {
      locationIds[], addressIds[], facilityIds[], hcpfIds[],
      scenarioMap (which IDs belong to which scenario)
    }

  createTelehealthInfoCodes(addressResult)        ← TX1, called by orchestrator after the chain
    → InformationCodeAssigned (Telehealth) per new HCFacility
    → User-visible on the confirmation screen, so this stays sync.

Internal utilities called:
  - PRM_AddressSelector.getExistingPracticeLocations(practitionerId)
  - PRM_DeduplicationUtil.checkExistingPracticeLink(addresses, practitionerId)
  - PRM_CollectionUtil.groupByField(addresses, 'scenario')
  - PRM_ParFormDataTransformer.mapToLocation(addressData)
  - PRM_ParFormDataTransformer.mapToAddress(addressData, locationId)
  - PRM_ParFormDataTransformer.mapToLocationNPI(npiData, locationId)
  - PRM_ParFormDataTransformer.mapToFacility(facilityData, locationId, groupAccountId)
  - PRM_ParFormDataTransformer.mapToHCPF(practitionerId, facilityId, groupAccountId)
  - PRM_BulkOperation.chain()         (junction-orphan-safe parent ➜ child DML)
  - PRM_DMLUtil.bulkUpdate            (for dedup-hit Scenarios B / D)
```

### 5.5 PRM_ParFormLevel4Batch (Async TX2 — per-facility fan-out only)

> **Why we need it** — A 5-location new-NPI submission generates 60+ fan-out records: `ProviderFeature` (per facility per scenario), `AffirmingCareCategory`, `PractitionerFacilityAffiliation` (PFAA), `HealthcareFacilityNetwork` (per location per network), `ProviderFeature - Assistive Aids`, plus per-existing-NPI upserts (`PersonEducation`, `BusinessLicense`, `CareProviderFacilitySpecialty`). Doing this in the user's sync transaction is the single largest contributor to "Apex CPU time limit exceeded" exceptions on Par Form today. Doing it in a Trigger couples it to the Case insert and inherits all of that transaction's other DML.
>
> **How it helps** — A `Database.Batchable<SObject>` invoked from the orchestrator via `PRM_AsyncEnqueueGuard.safeEnqueue(...)`, which falls back to inline execution if the per-transaction Queueable cap is exhausted (no silent drops). The `setContext` method snapshots the ids the batch needs (practitioner result, group result, address result, feature config) so the user's submit returns immediately with `caseId` and a `batchJobId`. Each batch chunk has its own governor budget; partial-success DML via `PRM_DMLUtil` and `PRM_BulkOperation.chain()` means one bad row doesn't block the other 59. `start()` opens a `PRM_AsyncJobStatus__c` row (status `RUNNING`); `finish()` updates it to `COMPLETED` / `FAILED`, calls `PRM_CaseDataMgrPatcher.patch('ParForm', caseManagerId, ...)` to stamp owned flags, and publishes `PRM_AsyncComplete__e` — the LWC bell uses the Platform Event by default and falls back to polling the status row if the event is missed.
>
> **Outcome** — User receives `caseId` in <1 s. Heavy fan-out DML completes invisibly within 30-60 s. Per-row failures become tickets, not full rollbacks. No silent async drop. No permanent spinner.

```
Replaces:
  - PRM_CreatePractitionerAddressRecords (REMAINING fan-out elements):
    → ProviderFeature (per facility, per scenario)
    → AffirmingCareCategory (per facility)
    → PractitionerFacilityAffiliation (PFAA)
    → HealthcareFacilityNetwork (per location)
    → ProviderFeature - Assistive Aids

  Existing-NPI upserts that aren't on the next-screen critical path:
    → PersonEducation        (upsert)
    → BusinessLicense        (upsert)
    → CareProviderFacilitySpecialty (upsert)

  TX1 records that DO NOT belong here (see § 5.6, 5.7, and § 7):
    × Contact (Primary / Secondary)         ← TX1, user-visible on next screen
    × ContactContactRelation                ← TX1
    × ContactProfile                        ← TX1
    × PersonLanguage                        ← TX1
    × InformationCodeAssigned (Telehealth)  ← TX1, attached to new HCFacilities

Lifecycle:
  start():   Insert PRM_AsyncJobStatus__c { JobName, ContextId=caseId, Status='RUNNING' }
             Return Database.QueryLocator over the snapshot ids.
  execute(): Process one chunk (scope=200) per scenario bucket.
             Use PRM_BulkOperation.chain() for parent ➜ junction inserts (HCFN per location).
             Use PRM_DMLUtil.bulkInsert / bulkUpsert with allOrNone=false for fan-out leaves.
  finish():  PRM_CaseDataMgrPatcher.patch('ParForm', caseManagerId, ownedFlagMap);
             Update PRM_AsyncJobStatus__c → Status='COMPLETED' or 'FAILED' + RowsProcessed/Failed.
             EventBus.publish(new PRM_AsyncComplete__e(caseId=..., status=...));
```

### 5.6 PRM_ProviderScreenService

> **Why we need it** — `PRM_CreateProviderScreenRecords` (5 elements) creates demographic / language records — `ContactProfile` (Hispanic, Race, Ethnicity, Gender Identity, Personal Pronouns) and `PersonLanguage`. The next OmniScript screen displays the practitioner's demographic summary, so these rows must exist by the time TX1 returns; TX2 fan-out is too late.
>
> **How it helps** — Two pure-functional methods (`createContactProfile`, `createPersonLanguages`) that map the OmniScript JSON into typed SObjects via `PRM_ParFormDataTransformer`, persist via `PRM_DMLUtil.bulkInsert`, and surface per-row failures into `PRM_ExceptionLog__c`. Called from the orchestrator on the TX1 critical path.
>
> **Outcome** — Demographic data lands cleanly before the next screen renders. Per-row failures generate tracked tickets instead of silent loss.

```
Replaces:
  - PRM_CreateProviderScreenRecords (5 elements)

Methods (called by PRM_ParFormRecordCreationService.processSync — TX1):
  createContactProfile(practResult, providerInformation)
    → ContactProfile (Hispanic, Race, Ethnicity, Gender Identity, Personal Pronouns)

  createPersonLanguages(practResult, languageData)
    → PersonLanguage records (multiple)

Internal utilities:
  - PRM_ParFormDataTransformer.mapToContactProfile()
  - PRM_ParFormDataTransformer.mapToPersonLanguage()
  - PRM_DMLUtil.bulkInsert()
```

### 5.7 PRM_ContactScreenService

> **Why we need it** — `PRM_CreateContactScreenRecords` (7 elements) creates the practitioner's primary and secondary `Contact` records plus the `ContactContactRelation` junctions linking them, then updates the practitioner record itself. The conditional ("only create primary if not same as practitioner") is implemented as IP-level branching today — fragile and untested. The next OmniScript screen renders the contact names, so these rows must commit before TX1 returns. Failure here would otherwise leave practitioners without contact information, blocking outbound credentialing communication.
>
> **How it helps** — One `createContacts` method handles the conditional cleanly in Apex, builds primary/secondary `Contact` records via `PRM_ParFormDataTransformer.mapToContact(data, role)`, and runs both `bulkInsert` (for new contacts and relations) and `bulkUpdate` (for the practitioner record) via `PRM_DMLUtil`. Runs on the TX1 critical path.
>
> **Outcome** — Contact creation is now a 60-line method with 4 unit tests, instead of 7 untested IP elements. The next screen renders with primary / secondary contact names already in place.

```
Replaces:
  - PRM_CreateContactScreenRecords (7 elements)

Methods (called by PRM_ParFormRecordCreationService.processSync — TX1):
  createContacts(practResult, contactInformation)
    → Contact (Primary) - conditional: not same as practitioner
    → Contact (Secondary)
    → ContactContactRelation (link contacts to practitioner)
    → Update practitioner record with primary/secondary contact

Internal utilities:
  - PRM_ParFormDataTransformer.mapToContact(contactData, role)
  - PRM_DMLUtil.bulkInsert()
  - PRM_DMLUtil.bulkUpdate() (practitioner record)
```

---

## 6. Data Transformer - Field-Level Mapping

### 6.1 PRM_ParFormDataTransformer

> **Why we need it** — Today the JSON-to-SObject mapping is spread across **20+ DataRaptor Transform** elements, each defined inside an OmniStudio bundle that lives outside the Apex codebase, has no unit tests, and can only be reviewed via the OmniStudio designer. A field-rename in `Account` (e.g. `PRM_NPI__c` → `PRM_PractitionerNPI__c`) requires touching every DataRaptor that references it, with no compile-time check. Drift between transforms is inevitable.
>
> **How it helps** — One stateless Apex class with focused mapping methods — `mapToPersonAccount`, `mapToTaxonomy`, `mapToDegree`, `mapToBusinessLicense`, `mapToLocation`, `mapToAddress`, `mapToHCPF`, `mapToContact`, `mapToContactProfile`, `mapToPersonLanguage`, etc. Pure functions: input is `Map<String, Object>` (OmniScript JSON), output is a typed SObject. No DML, no SOQL — trivially unit-testable. Field renames are caught by the Apex compiler.
>
> **Outcome** — 20+ DataRaptor bundles become one source-controlled, code-reviewed, compile-checked Apex class. Field renames produce build errors instead of silent production data corruption. Transforms are unit-tested; today they aren't.

```java
/**
 * Stateless transformer that replaces ALL DataRaptor Transform elements.
 * Maps OmniScript JSON structures to typed SObject records.
 */
public class PRM_ParFormDataTransformer {

    // === PRACTITIONER SCREEN TRANSFORMS ===
    
    public static Account mapToPersonAccount(Map<String, Object> practForm, String formattedName) {
        Account acct = new Account();
        acct.RecordTypeId = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName()
            .get('PersonAccount').getRecordTypeId();
        acct.FirstName = (String) practForm.get('firstName');
        acct.LastName = (String) practForm.get('lastName');
        acct.MiddleName = (String) practForm.get('middleName');
        acct.Suffix = (String) practForm.get('suffix');
        acct.PersonEmail = (String) practForm.get('email');
        acct.Type = 'Medical Service Vendor';
        acct.PRM_NPI__c = (String) practForm.get('PractitionerIndividualNPI');
        acct.PersonBirthdate = parseDate((String) practForm.get('PractitionerDOB'));
        acct.PRM_Gender__c = (String) practForm.get('PractitionerGender');
        acct.PRM_ProviderRole__c = (String) practForm.get('ProviderRole');
        return acct;
    }
    
    public static List<CareProviderFacilitySpecialty> mapToTaxonomy(
            List<Map<String, Object>> taxonomyData, Id providerId) {
        List<CareProviderFacilitySpecialty> records = new List<CareProviderFacilitySpecialty>();
        for (Map<String, Object> t : taxonomyData) {
            CareProviderFacilitySpecialty spec = new CareProviderFacilitySpecialty();
            spec.PractitionerId = providerId;
            spec.PRM_TaxonomyCode__c = (String) t.get('TaxonomyCode');
            spec.PRM_TaxonomyDescription__c = (String) t.get('TaxonomyDescription');
            spec.IsPrimarySpecialty = t.get('IsPrimary') == true;
            spec.PRM_Pending__c = true;
            spec.PRM_IsErrorRecord__c = false;
            records.add(spec);
        }
        return records;
    }
    
    public static List<PersonEducation> mapToDegree(
            List<Map<String, Object>> degreeData, Id accountId) {
        List<PersonEducation> records = new List<PersonEducation>();
        for (Map<String, Object> d : degreeData) {
            PersonEducation edu = new PersonEducation();
            edu.PersonId = accountId;
            edu.PRM_DegreeType__c = (String) d.get('DegreeType');
            edu.PRM_SchoolName__c = (String) d.get('SchoolName');
            edu.PRM_GraduationYear__c = (String) d.get('GraduationYear');
            edu.PRM_Pending__c = true;
            records.add(edu);
        }
        return records;
    }
    
    public static List<BusinessLicense> mapToBusinessLicense(
            List<Map<String, Object>> licenseData, Id accountId) {
        List<BusinessLicense> records = new List<BusinessLicense>();
        for (Map<String, Object> l : licenseData) {
            BusinessLicense bl = new BusinessLicense();
            bl.AccountId = accountId;
            bl.PRM_LicenseType__c = (String) l.get('LicenseType');
            bl.LicenseNumber = (String) l.get('LicenseNumber');
            bl.PRM_State__c = (String) l.get('State');
            bl.ExpirationDate = parseDate((String) l.get('ExpirationDate'));
            bl.PRM_Pending__c = true;
            records.add(bl);
        }
        return records;
    }

    // === ADDRESS SCREEN TRANSFORMS ===
    
    public static Location mapToLocation(Map<String, Object> addressData) {
        Location loc = new Location();
        loc.Name = (String) addressData.get('facilityName');
        loc.LocationType = 'Site';
        loc.PRM_EffectiveFrom__c = parseDate((String) addressData.get('effectiveDate'));
        loc.PRM_Pending__c = true;
        loc.PRM_TelehealthOnly__c = addressData.get('isTelehealthOnly') == true;
        return loc;
    }
    
    public static Address mapToAddress(Map<String, Object> addressData, Id locationId) {
        Address addr = new Address();
        addr.ParentId = locationId;
        addr.PRM_AddressLine1__c = (String) addressData.get('addressLine1');
        addr.PRM_AddressLine2__c = (String) addressData.get('addressLine2');
        addr.PRM_City__c = (String) addressData.get('city');
        addr.PRM_State__c = (String) addressData.get('state');
        addr.PRM_Zip__c = (String) addressData.get('zip');
        addr.PRM_Zip4__c = (String) addressData.get('zip4');
        addr.PRM_County__c = (String) addressData.get('county');
        addr.PRM_Phone__c = (String) addressData.get('phone');
        addr.PRM_PhoneExtension__c = (String) addressData.get('phoneExtension');
        addr.PRM_Fax__c = (String) addressData.get('fax');
        addr.PRM_IsErrorRecord__c = false;
        addr.PRM_Active__c = false;
        addr.PRM_Pending__c = true;
        return addr;
    }
    
    public static HealthcareProviderNpi mapToLocationNPI(
            Map<String, Object> npiData, Id locationId) {
        HealthcareProviderNpi hpn = new HealthcareProviderNpi();
        hpn.Name = 'NPI - ' + (String) npiData.get('npiNumber');
        hpn.ParentRecordId = locationId;
        hpn.PRM_Type__c = (String) npiData.get('npiType'); // 'Group' or 'Individual'
        hpn.IdValue = (String) npiData.get('npiNumber');
        hpn.EffectiveDate = parseDate((String) npiData.get('effectiveDate'));
        hpn.PRM_IsErrorRecord__c = false;
        return hpn;
    }
    
    public static HealthcareFacility mapToFacility(
            Map<String, Object> facilityData, Id locationId, Id groupAccountId, Id caseManagerId) {
        HealthcareFacility hcf = new HealthcareFacility();
        hcf.Name = (String) facilityData.get('facilityName');
        hcf.AccountId = groupAccountId;
        hcf.LocationId = locationId;
        hcf.PRM_CaseManager__c = caseManagerId;
        hcf.PRM_Primary__c = facilityData.get('isPrimary') == true;
        hcf.PRM_Active__c = false;
        hcf.PRM_Pending__c = true;
        hcf.PRM_IsErrorRecord__c = false;
        hcf.PRM_TelehealthOnly__c = facilityData.get('isTelehealthOnly') == true;
        return hcf;
    }
    
    public static HealthcarePractitionerFacility mapToHCPF(
            Id practitionerId, Id facilityId, Id groupAccountId, Id caseManagerId,
            Map<String, Object> data) {
        HealthcarePractitionerFacility hpf = new HealthcarePractitionerFacility();
        hpf.RecordTypeId = Schema.SObjectType.HealthcarePractitionerFacility
            .getRecordTypeInfosByDeveloperName()
            .get('PRM_PractitionerLocationAffiliation').getRecordTypeId();
        hpf.PractitionerId = practitionerId;
        hpf.HealthcareFacilityId = facilityId;
        hpf.AccountId = groupAccountId;
        hpf.PRM_CaseManager__c = caseManagerId;
        hpf.IsActive = false;
        hpf.IsPrimaryFacility = data.get('isPrimary') == true;
        hpf.EffectiveFrom = parseDate((String) data.get('effectiveDate'));
        hpf.PRM_AttestationDate__c = Date.today();
        hpf.PRM_IsErrorRecord__c = false;
        hpf.PRM_Pending__c = true;
        return hpf;
    }

    // === LEVEL 4 TRANSFORMS ===
    
    public static ProviderFeature mapToProviderFeature(
            Map<String, Object> featureData, Id facilityId) { ... }
    
    public static AffirmingCareCategory__c mapToACC(
            Map<String, Object> accData, Id facilityId) { ... }
    
    public static PractitionerFacilityAffiliation__c mapToPFAA(
            Map<String, Object> pfaaData, Id hcpfId) { ... }
    
    public static HealthcareFacilityNetwork mapToFacilityNetwork(
            Id facilityId, Id networkId, Date effectiveDate) { ... }
    
    public static InformationCodeAssigned__c mapToTelehealthInfoCode(
            Id facilityId, Boolean isTelehealth) { ... }
    
    public static ContactProfile mapToContactProfile(
            Map<String, Object> providerInfo, Id contactId) { ... }
    
    public static PersonLanguage mapToPersonLanguage(
            Map<String, Object> langData, Id contactId) { ... }
    
    public static Contact mapToContact(
            Map<String, Object> contactData, String role) { ... }
    
    private static Date parseDate(String dateStr) {
        if (String.isBlank(dateStr)) return null;
        try { return Date.valueOf(dateStr); }
        catch (Exception e) { return null; }
    }
}
```

---

## 7. Transaction Boundary Design

> The TX1 / TX2 split follows the framework's boundary doctrine ([§ 14.5 of `PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md#145-tx1--tx2-boundary-doctrine)): every record the next OmniScript screen renders, every record another flow reads on its critical path within the next 5 minutes, and every record the directory exposes commits in TX1. Only true per-facility / per-network fan-out belongs in TX2.

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTION 1 (SYNC)                          │
│            OmniScript waits for this to complete                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_PractitionerScreenService                              │ │
│  │   • Account (Person Account)         ← MUST exist first    │ │
│  │   • Case                                                    │ │
│  │   • IndividualApplication                                   │ │
│  │   • HealthcareProvider                                      │ │
│  │   • HealthcareProviderNpi (Individual)                      │ │
│  │   • Identifier (CAQH)  ← new identifier MUST insert before  │ │
│  │     the legacy primary flag is removed (existing-NPI path)  │ │
│  │   • ContentVersion + ContentDocumentLink (file)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼ (needs AccountId, CaseManagerId)      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_GroupScreenService — PRM_BulkOperation.chain()         │ │
│  │   • HealthcareFacility (Group)  ──┐                         │ │
│  │   • HealthcareProviderNpi (Group) ├─ FK-linked, orphan-safe │ │
│  │   • HealthcareFacilityNetwork  ──┘                          │ │
│  │   • PRM_ProgramParticipation__c                             │ │
│  │     multipleGroupNPIS flag is an explicit method parameter  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼ (needs GroupFacilityId)               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_AddressRecordService — PRM_BulkOperation.chain()       │ │
│  │   Builder 1:  Location ➜ Address (FK Location)              │ │
│  │   Builder 2:  HCFacility ➜ HCPF  (FK HCFacility)            │ │
│  │   Dedup-aware: Scenarios B/D route to bulkUpdate, not       │ │
│  │   bulkInsert (re-submit is idempotent — no duplicate HCPFs) │ │
│  │   + InformationCodeAssigned (Telehealth) for new HCFs       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼ (user-visible records the NEXT screen │
│                            renders — must commit in TX1)         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PRM_ProviderScreenService                                  │ │
│  │   • ContactProfile  (Hispanic, Race, Ethnicity, GI, Pronoun)│ │
│  │   • PersonLanguage                                          │ │
│  │ PRM_ContactScreenService                                   │ │
│  │   • Contact (Primary, conditional)                          │ │
│  │   • Contact (Secondary)                                     │ │
│  │   • ContactContactRelation                                  │ │
│  │   • Practitioner contact link update                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│                          ▼                                       │
│   PRM_CaseDataMgrPatcher.patch('ParForm', cmId, ownedFlags)      │
│                          │                                       │
│  COMMIT POINT ──────────────────────────────────────────────────│
└─────────────────────────────────────────────────────────────────┘
         │
         │ PRM_AsyncEnqueueGuard.safeEnqueue(batch, inlineFallback,
         │                                   estimatedRowCount, res)
         │   → ENQUEUED  (Queueable accepted)
         │   → RAN_INLINE (cap exhausted → ran inline; same correctness)
         │   → DEFERRED   (cap exhausted + too large for inline →
         │                 PRM_AsyncJobStatus__c row + LWC banner)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTION 2 (ASYNC - BATCH)                 │
│            User sees "Processing..." with Job ID                 │
│                                                                  │
│  PRM_ParFormLevel4Batch — fan-out per-facility records ONLY      │
│                                                                  │
│  start():   open PRM_AsyncJobStatus__c (status=RUNNING)          │
│  execute(): per practitioner / scenario chunk —                  │
│   • ProviderFeature   (per facility, per scenario)               │
│   • AffirmingCareCategory                                        │
│   • PractitionerFacilityAffiliation (PFAA)                       │
│   • HealthcareFacilityNetwork (per location, fan-out)            │
│   • ProviderFeature — Assistive Aids                             │
│   • [existing-NPI] PersonEducation / BusinessLicense /           │
│     CareProviderFacilitySpecialty (upserts not on next screen)   │
│  finish():                                                       │
│   • PRM_CaseDataMgrPatcher.patch('ParForm', cmId, finalFlags)    │
│   • update PRM_AsyncJobStatus__c (status=COMPLETED / FAILED)     │
│   • EventBus.publish(PRM_AsyncComplete__e)                       │
│                                                                  │
│  LWC subscribes to the Platform Event by default;                │
│  if the event is missed, the LWC polls PRM_AsyncJobStatus__c —   │
│  no permanent spinner.                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Address Scenario Decision Matrix

The `PRM_AddressRecordService` must handle 5 distinct scenarios that the IP currently processes with different element branches:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ADDRESS SCENARIO ROUTING LOGIC                                 │
│                                                                                  │
│  Input: locationsToUpsert[] from OmniScript                                     │
│                                                                                  │
│  For each location entry:                                                        │
│    ├─ Is it a NEW address manually entered?                                      │
│    │    ├─ YES → Is the NPI same as practitioner's individual NPI?               │
│    │    │         ├─ YES → SCENARIO A: Manually Add, Same NPI                    │
│    │    │         │         Creates: Location + Address + HCProviderNpi +         │
│    │    │         │                  HCFacility + HCPF + Network                  │
│    │    │         │         DR: PRMDRCreatePractitionerAddressRecordswithNPI      │
│    │    │         │                                                               │
│    │    │         └─ NO  → SCENARIO C: Manually Add, Different NPI               │
│    │    │                   Creates: Location + Address + HCProviderNpi +         │
│    │    │                            HCFacility + HCPF + Network                  │
│    │    │                   DR: PRMDRCreatePractitionerAddressRecordswithNPIDelg  │
│    │    │                                                                         │
│    │    └─ NO  → Is it a NEW practice location for EXISTING group?               │
│    │              ├─ YES → SCENARIO B: New Location, Existing Group               │
│    │              │         Creates: Location + Address + HCProviderNpi +         │
│    │              │                  HCFacility + HCPF                            │
│    │              │         DR: PRMDRCreatePractitionerNewAddressRecords          │
│    │              │         + Dedup check + Existing HCPF merge                   │
│    │              │                                                               │
│    │              └─ NO  → Is it a NEW GROUP address?                             │
│    │                        ├─ YES → SCENARIO E: New Group Address                │
│    │                        │         Creates: Location + Address + HCProviderNpi │
│    │                        │                  + HCFacility + HCPF               │
│    │                        │         DR: PRMDRCreatePractitionerNewAddressRecords│
│    │                        │                                                    │
│    │                        └─ NO  → SCENARIO D: Existing Address, Just Link     │
│    │                                  Creates: HCPF only (junction)              │
│    │                                  + HC Facility Network                       │
│    │                                  DR: PRMDRCreateHealthCarePractitionerFac    │
│    │                                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Complete Class Inventory for Par Form Migration

| Class | Layer | Replaces (IP/Element) | Records Owned |
|---|---|---|---|
| `PRM_ParFormServiceDispatcher` | Controller | PRM_CreateParFormRecordsContainer | — (routing only) |
| `PRM_ParFormRecordCreationService` | Service | PRM_CreateParFormRecords | — (orchestration) |
| `PRM_PractitionerScreenService` | Service | PRM_PractitionerScreenRecordCreation + ExistingNPIRecordUpdation | Account, Case, IndividualApp, HC Provider, HC ProviderNpi, Identifier, File |
| `PRM_GroupScreenService` | Service | PRM_CreateGroupScreenRecord | HC Facility(Group), HCProviderNpi(Group), HCFacilityNetwork, ProgramParticipation |
| `PRM_AddressRecordService` | Service | PRM_CreatePractitionerAddressRecords (core) | Location, Address, HCProviderNpi(Loc), HCFacility(Loc), HCPF |
| `PRM_ProviderScreenService` | Service | PRM_CreateProviderScreenRecords | ContactProfile, PersonLanguage |
| `PRM_ContactScreenService` | Service | PRM_CreateContactScreenRecords | Contact, ContactContactRelation |
| `PRM_CaseDataManagerService` | Service | PRMDRPCaseDataManager (all instances) | IndividualApplication (updates) |
| `PRM_ParFormLevel4Batch` | Async | All Level 4 elements across all IPs | ProviderFeature, ACC, PFAA, HCFacNetwork, InfoCode, + all Provider/Contact screen records |
| `PRM_ParFormDataTransformer` | Transform | All DR Transform elements (20+) | — (maps data to SObjects) |
| `PRM_TitleCaseUtil` | Utility | RA_TitleCase Remote Action | — (name formatting) |
| `PRM_DeduplicationUtil` | Utility | RA_checkSpecialty/Degree/License + CheckIfPracticeToPractitionerExist | — (dedup queries) |
| `PRM_FeatureConfig` | Utility | GetFeatureConfigSetting (DR Turbo) | — (reads custom metadata) |
| `PRM_PractitionerSelector` | Selector | DRExtractTaxonomyData, DRExtractExistingTaxonomyData, DRExtractCaseManager | — (SOQL) |
| `PRM_AddressSelector` | Selector | CheckIfPracticeToPractitionerAlreadyExist | — (SOQL) |
| `PRM_CaseSelector` | Selector | DRExtractCaseManager | — (SOQL) |
| `PRM_DMLUtil` | Utility | All DR Post Actions (40+) | — (generic DML) |
| `PRM_CollectionUtil` | Utility | All List Actions (Filter, Merge) + Set Values | — (collection ops) |
| `PRM_GovernorUtil` | Utility | — (new) | — (limit checks) |
| `PRM_ErrorLogger` | Cross-cutting | TryCatchBlock | PRM_ExceptionLog__c |
| `PRM_TransactionContext` | Cross-cutting | SV_SourceIPDetails | — (correlation) |
| `PRM_ServiceRequest` | Model | — (new) | — (input wrapper) |
| `PRM_ServiceResponse` | Model | ResponseAction (all IPs) | — (output wrapper) |
| `PRM_PractitionerScreenResult` | Model | SV_PractitionerIds / additionalOutput | — (inter-service data) |
| `PRM_GroupScreenResult` | Model | GroupRecordIds output | — (inter-service data) |
| `PRM_AddressRecordResult` | Model | — (new) | — (inter-service data) |

---

## 10. Governor Limit Comparison

| Metric | Current (IP Chain) | After (Apex Service) |
|--------|-------------------|---------------------|
| **SOQL Queries** | 50-80+ (each DR Extract = 1+) | 8-12 (consolidated selectors) |
| **DML Statements** | 40-55 (each DR Post = 1) | 5-8 (batched DML) |
| **DML Rows** | Same | Same (but chunked safely) |
| **CPU Time** | 45-60s (approaching limit) | 3-5s sync + async for rest |
| **Heap** | Approaches 12MB | ~4MB sync (rest offloaded) |
| **Execution Context** | Single sync transaction | TX1 sync + TX2 batch |
| **Failure Mode** | All-or-nothing rollback | Partial success with logging |

---

## 11. DataRaptor Bundles Referenced (Complete List)

These are the DataRaptor bundles currently in use that will be replaced by the Transformer + DMLUtil pattern:

| DataRaptor Bundle | Type | IP Source | Replaced By |
|---|---|---|---|
| PRMGetFeatureConfigSetting | Turbo Extract | CreateParFormRecords | `PRM_FeatureConfig.getSettings()` |
| PRMDRCreateCaseCaseManagerAndAccount | Multi-Object Load | PractitionerScreenRecordCreation | `PRM_PractitionerScreenService.createAccountCaseCaseManager()` |
| PRMDRCreateProviderIdentifierNPI | Multi-Object Load | PractitionerScreenRecordCreation | `PRM_PractitionerScreenService.createProviderIdentifierNPI()` |
| PRMDRCreateEducationTaxanomyAndLicense | Multi-Object Load | PractitionerScreenRecordCreation | `PRM_PractitionerScreenService.createEducationTaxonomyLicense()` |
| PRMDRPCaseDataManager | Load | Multiple IPs | `PRM_CaseDataManagerService.updateCaseData()` |
| PRMCreateGroupRecords | Multi-Object Load | CreateGroupScreenRecord | `PRM_GroupScreenService.createGroupRecords()` |
| PRMDRCreatePractitionerNewAddressRecords | Multi-Object Load | CreatePractitionerAddressRecords | `PRM_AddressRecordService.createCoreAddressRecords()` |
| PRMDRCreatePractitionerAddressRecordswithNPI | Multi-Object Load | CreatePractitionerAddressRecords | `PRM_AddressRecordService.createCoreAddressRecords()` |
| PRMDRCreatePractitionerAddressRecordswithNPIDelg | Multi-Object Load | CreatePractitionerAddressRecords | `PRM_AddressRecordService.createCoreAddressRecords()` |
| PRMDRCreateContactProfileRecords | Load | CreateProviderScreenRecords | `PRM_ProviderScreenService.createContactProfile()` |
| PRMDRCreatePersonLanguage | Load | CreateProviderScreenRecords | `PRM_ProviderScreenService.createPersonLanguages()` |
| PRMDRTransformPersonLanguage | Transform | CreateProviderScreenRecords | `PRM_ParFormDataTransformer.mapToPersonLanguage()` |
| PRMDRCreateContactRecords | Multi-Object Load | CreateContactScreenRecords | `PRM_ContactScreenService.createContacts()` |
| PRMDRPUpdatePrimarySecondaryContact | Load | CreateContactScreenRecords | `PRM_ContactScreenService.updatePrimarySecondaryRelation()` |
| PRMDRCheckIfPracticeToPractitionerExist | Extract | CreatePractitionerAddressRecords | `PRM_DeduplicationUtil.checkExistingPracticeLink()` |
| PRMDRCreateHFNPractitionerNetworkRecords | Load | CreatePractitionerAddressRecords | `PRM_ParFormLevel4Batch` (Network records) |
| PRMDRCreatePractitionerFacilityNetwork | Load | CreatePractitionerAddressRecords | `PRM_ParFormLevel4Batch` (Network records) |

---

## 12. Summary: What Moves Where

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     MIGRATION SUMMARY                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAYS IN OMNISTUDIO (Thin):                                                 │
│    • OmniScript UI (no change)                                               │
│    • 1 thin Container IP (routes to Remote Action)                           │
│                                                                              │
│  MOVES TO APEX SYNC (TX1):                                                   │
│    • Feature Config read (1 SOQL)                                            │
│    • Account + Case + IndividualApplication creation                         │
│    • HealthcareProvider + NPI + Identifier creation                          │
│    • File/ContentVersion creation                                            │
│    • Group HC Facility + Group NPI + Network + ProgramParticipation          │
│    • Location + Address + HC ProviderNpi(Loc) + HC Facility(Loc) + HCPF      │
│                                                                              │
│  MOVES TO APEX BATCH (TX2):                                                  │
│    • PersonEducation / BusinessLicense / Taxonomy (create or upsert)         │
│    • ContactProfile + PersonLanguage                                         │
│    • Contact (Primary/Secondary) + ContactContactRelation                    │
│    • ProviderFeature (all scenarios x all facilities)                        │
│    • AffirmingCareCategory (all scenarios)                                   │
│    • PractitionerFacilityAffiliation / PFAA (all scenarios)                  │
│    • HealthcareFacilityNetwork (per location)                                │
│    • ProviderFeature - Assistive Aids                                        │
│    • Final IndividualApplication updates (via PRM_CaseDataMgrPatcher)        │
│                                                                              │
│  TOTAL IP ELEMENTS BEING REPLACED: ~130+ elements across 7 IPs              │
│  TOTAL APEX CLASSES NEEDED: ~20 classes                                      │
│  TOTAL DATARAPTORS BEING RETIRED: 16+ bundles                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

