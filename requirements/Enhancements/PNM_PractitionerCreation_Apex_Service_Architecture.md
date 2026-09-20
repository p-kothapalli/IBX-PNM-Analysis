# PNM Practitioner Creation — Apex Service Architecture
## IP Audit, Reusability Matrix & New Service Blueprint (`PRM_PractitionerCreationContainer` — both `IBC Professional Staff` and `Delegated Credentialing` branches)

(placeholder — populated by chunked StrReplace per `prompt.md` §7.1)

---

> **Companion docs**
> - Framework — `PNM_Apex_Service_Architecture.md`
> - Practitioner Participation Form — `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`
> - Initial Cred PDA Review — `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md`
> - Off Cycle Submit — `PNM_OffCycle_Process_Apex_Service_Architecture.md`
> - Off Cycle PDA Review — `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`
> - Reinstate (Practitioner / Loc / Vendor) — `PNM_Reinstate_Apex_Service_Architecture.md`
> - Interactive mind map — `PNM_Modernization_MindMap.html` (this flow is rendered as the `practitioner-creation` tab)
> - Authoring methodology — `prompt.md`

---

## 0. TL;DR

| | Par Form (Submit) | PDA Review (Initial Cred) | **THIS FLOW — Practitioner Creation** |
|---|---|---|---|
| Trigger | OS submit on `PRM_ParForm_English` (per-practitioner add to existing vendor) | OS submit on `PRM_InitialCredPDA_English` (committee outcome) | OS submit on `PRM_PractitionerCreation_English` v23 — **brand-new practitioner record** entering the network |
| Entry OS | `PRM_ParForm_English` | `PRM_InitialCredPDA_English` v25–30 | `PRM_PractitionerCreation_English` v23 |
| Entry IP | `PRM_CreateParFormRecordsContainer` | `PRM_InitialCredPDAReviewUpdateParent` | `PRM_PractitionerCreationContainer_Procedure_5` (5 elt) |
| Orchestrator IP | `PRM_CreateParFormRecords` (9 elt, fans out to 7 sub-IPs / 130+ elt total) | `PRM_InitialCredPDAReviewUpdate` (10 elt) | `PRM_PractitionerCreation_Procedure_3` (11 elt, IBC) **or** `PRM_DelegatedPractitionerCreation_Procedure_6` (23 elt, Delegated) |
| Heaviest IP | `PRM_CreatePractitionerAddressRecords` (80+ elt) | `PRM_InitialCredPDAReviewUpdateSubIPInsert` (28 elt) | `PRM_DelegatedPractitionerCreation_Procedure_6` (23 elt) + sub-IP `PRM_DelegatedCreateProviderScreenRecords` (4 elt) = **27 elt active in delegated chain**, plus inactive sub-IPs deferred to later OmniScripts (`PRM_CreateDelegatedPractitionerPracticeLocationsRecords` 13 elt, `PRM_CreateDelegatedHFNRecords` 25 elt) |
| Variant axis | Scenario A/B/C/D (single vs multi NPI Group × new vs existing practitioner) | `PDAOutCome` × `ChangeRequested` × volume | `PractitionerCreationType` — **`"IBC Professional Staff"` vs `"Delegated Credentialing"`** (routes through the same container IP) |
| DML pattern | Big-bang DR Post per SObject family, partial success implicit | Insert + update split, partial success implicit | DR Posts wrap **multi-SObject FK chains** in each call (Account+Case+CM, HCProvider+Taxonomy+License, HCPNPI+BoardCert+Identifier, Identifier+ContentVersion+CDL). No atomic guard today. |
| Reusable framework code | ~78% (after PDA + OffCycle migrations) | ~83% | **~75%** — heavy reuse of `PRM_BaseService` + framework primitives + `PRM_CaseService` + `PRM_TaxonomyService` + `PRM_IdentifierService` + `PRM_PersonEducationService`, but 16 net-new services for HCProvider/BusinessLicense/Group/HCPF-pair/HCPNPI/BoardCert/PersonLanguage/ContactProfile/InfoCode plumbing |
| Net-new services | 14 (Par Form was the first) | 5 | **16** (see §4.5) |
| Existing Apex precedent | None | None | **3 classes** (`PRM_PractitionerCreationValidator` — May 2026, `PRM_PractitionerCreationHelper` — LWC AuraEnabled helper, `PRM_PractitionerCreationUtility` — Callable for `getGroupData`). All STANDARDISE. |
| Async (TX2) row budget | ~200 (multi-NPI + multi-loc) | ~150 (HCFN reshape per facility) | **~80** (delegated: per-location PracticeAffiliation + ProviderFeature + Education + Languages — runs sync today; should TX2-delegate via `PRM_AsyncEnqueueGuard` when delegated payload has > 80 rows estimated) |
| Critical-path UX | Vendor submit → Case ID returned, screen advances | Reviewer submits → next screen renders pre-fetched | **Practitioner Intake → Case ID returned, navigation to subsequent OS (`PRM_DelegatedPractitionerAddressForm` or `PRM_DelegatedPractitionerReviewScreen`) depends on returned `CaseManagerId`, `GroupRecordIds`, `PractitionerScreenRecordIds`, `locationsToUpsert`** — every output in the container's `ResponseAction` is consumed downstream, so the boundary is unforgiving |

**Bottom line.** Practitioner Creation is the **front door** of the entire PNM cred-intake journey: it creates the `Account` (PersonAccount practitioner), the `Case`, the `IndividualApplication` (Case Manager), the `PRM_CaseDataManager__c` and a long FK chain of child records that every downstream guided flow (Par Form, PDA Review, Off Cycle, Reinstate) operates on. The migration replaces 16–32 IP elements (depending on branch) with one dispatcher service and ~16 net-new domain services, while preserving the OmniScript JSON contract and the three existing production-hardened Apex classes (`PRM_PractitionerCreationValidator`, `PRM_PractitionerCreationHelper`, `PRM_PractitionerCreationUtility`) verbatim.

---

## 1. Current State: Complete IP Chain Audit

### 1.1 Full IP orchestration chain

```
PRM_PractitionerCreation_English (v23) — OmniScript
   │
   └── IP_RecordCreation (IP Action element)
         │
         ▼
   PRM_PractitionerCreationContainer_Procedure_5  (5 elt — TryCatch wrapper)
         │
         ├── C1  SV_SourceIPDetails        — sets SourceIPName for error logging
         │
         ├── C2  TryCatchBlock             — wraps the two child IP Actions
         │        │  (remoteClass=PRM_OmniUtils, remoteMethod=logTryCatchException)
         │        │
         │        ├── C3  IP Action: PractitionerCreation
         │        │       cond: %PractitionerCreationType% == "IBC Professional Staff"
         │        │       → PRM_PractitionerCreation_Procedure_3 (11 elt)
         │        │
         │        └── C4  IP Action: DelegatedPractitionerCreation
         │                cond: %PractitionerCreationType% == "Delegated Credentialing"
         │                → PRM_DelegatedPractitionerCreation_Procedure_6 (23 elt)
         │
         └── C5  Response                  — returns CaseManagerId + delegated outputs


  ┌────────────────────────────────────────────────────────────────────────┐
  │  STANDARD branch — PRM_PractitionerCreation_Procedure_3  (11 elements) │
  └────────────────────────────────────────────────────────────────────────┘
   ├── S1   RA_TitleCase                                  → PRM_OmniUtils.titleCase
   ├── S2   SV_RecordTypeIds                              → QUERY("SELECT Id FROM RecordType WHERE
   │                                                            SobjectType='HealthcarePractitionerFacility'
   │                                                            AND DeveloperName IN ('PRM_PractitionerPracticeAffiliation',
   │                                                                                  'PRM_PractitionerLocationAffiliation')")
   ├── S3   DRPAccountCaseCaseManagerCreation             → bundle: PRMDRCreateCaseCaseManagerAndAccount
   │           creates: Account_1 (PersonAccount), Case_3, IndividualApplication_2
   ├── S4   PRMDRCreateCDM                                → bundle: PRMDRPCDMCaseManagerLink
   │           cond: %DRPAccountCaseCaseManagerCreation:CaseManagerId% != null
   ├── S5   DRPHCProviderHCProviderTaxonomyAndBusineessLicense
   │           → bundle: PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense
   │           creates: HealthcareProvider_1, HealthcareProviderTaxonomy, BusinessLicense (Identifier)
   ├── S6   RA_GetInfoCodesList                           → PRM_OmniUtils.convertToListSobjects
   ├── S7   DRPCreateInfoCodeAssignments                  → bundle: PRMDRPCreateInfoCodeAssignments
   │           cond: ISNOTBLANK(%RecordsToUpdate:InfoCodeIds%) && LISTSIZE(%RecordsToUpdate:InfoCodeIds%) > 0
   ├── S8   RA_GetRecordTypeList                          → PRM_OmniUtils.convertToListSobjects
   ├── S9   DRPPractionerPracticeLocations                → bundle: PRMDRPPractionerPracticeLocations
   │           creates: HealthcarePractitionerFacility × 2 (Primary Practice Affiliation + Location Affiliation)
   ├── S10  PRMDRCreateCDMForPractitioner                 → bundle: PRMDRCreateCDMForPractitioner
   │           stamps: Account, BusinessLicense, Hcp, HcpTaxonomy, InfoCodeAssignment,
   │                   PersonAccount, PracticeLocationPract on the CaseDataManager
   └── S11  ResponseAction                                → returns CaseManagerId


  ┌────────────────────────────────────────────────────────────────────────┐
  │  DELEGATED branch — PRM_DelegatedPractitionerCreation_Procedure_6     │
  │                                                  (23 elements)         │
  └────────────────────────────────────────────────────────────────────────┘
   ├── D1   GetFeatureConfigSetting                       → DR Turbo: PRMGetFeatureConfigSetting
   ├── D2   RA_TitleCase                                  → PRM_OmniUtils.titleCase
   ├── D2.5 [NEW seq 2.5, May 2026] Remote Action
   │           → PRM_PractitionerCreationValidator.validate (Callable)
   │           Fail-fast EffectiveDate precheck — mirrors PRM_EffectiveDateValidation
   │           on HCPF + HFN. Blocks submit BEFORE first DML when dates would reject.
   │           (US 1416807 — AC5 Error Handling & Rollback)
   ├── D3   DRPAccountCaseCaseManagerCreation             → bundle: PRMDRCreateCaseCaseManagerAndAccount
   │           additionalInput.Delegated = true; extra fields (PersonGenderIdentity,
   │           CredentialingStatus, ProviderRole, IsRoundRobinLogic, etc.)
   ├── D4   DRCreateGroupRecords                          → bundle: PRMPostGroupPractitionerCreation
   │           creates: Vendor Account + Group HCFNPI + Group Identifier (TIN)
   │           additionalInput: ParticipationStatus="Participating", PRM_Pending__c=false,
   │                            npiType="Organization"
   ├── D5   PRMDRCreateCDM                                → bundle: PRMDRPCDMCaseManagerLink
   │           cond: %DRPAccountCaseCaseManagerCreation:CaseManagerId% != null
   ├── D6   SV_PractitionerScreenRecordIds                — stashes AccountId / CaseId /
   │           CaseManagerId / PersonContactId / CDMId for downstream sub-IPs and the response
   ├── D7   DRExtractTaxonomyData                         → DR Turbo: PRMDRExtractTaxonomyData
   │           reads CareTaxonomy rows by Name list (RecordsToUpdate.AdditionalSpecialties)
   ├── D8   DRTTaxonomyData                               → DR Transform: PRMDRTransDelegatedTaxonomyData
   │           merges extracted taxonomies + flags primary specialty
   ├── D9   DRTransformDelegatedBusinessLicense           → DR Transform: PRMDRTransformDelegatedBusinessLicense
   │           reshapes SBRD vs DEA/CDS license rows for merge
   ├── D10  LA_MergeBusinessLicense                       — List Merge by PractitionerLicenseNumber
   │           order: DEACDSBusinessLicense, RecordsToUpdate:BusinessLicense
   ├── D11  DRPHCProviderHCProviderTaxonomyAndBusineessLicense
   │           → bundle: PRMDRPHCPHCPTaxonomyAndBusineessLicense
   │           creates: HealthcareProvider_1 + multi-Taxonomy + multi-BusinessLicense
   ├── D12  TransformAddEducation                         → DR Transform: PRMDRTransformAddEducation
   ├── D13  DRPCreateEducation                            → bundle: PRMDRPCreateEducation
   │           creates: PersonEducation rows
   ├── D14  DRPHCPNPIBoardCretIdentifier                  → bundle: PRMDRPHCPNPIBoardCretIdentifier
   │           creates: HealthcareProviderNpi + BoardCertification + Identifier (NPI / Medicare / etc.)
   ├── D15  SV_AdditionalNodesToFileData                  — List Merge that stamps
   │           updateFieldValue: { FormProcess="Practitioner Participation",
   │                               TargetLocation="SF PDM" }
   │           cond: ISNOTBLANK(%FileData%)
   ├── D16  DRCreateIdentiferAndDocument                  → bundle: PRMDRCreateIdentiferAndDocument
   │           cond: ISNOTBLANK(%FileData%)
   │           creates: Identifier + ContentVersion + ContentDocumentLink chain
   ├── D17  RA_GetInfoCodesList                           → PRM_OmniUtils.convertToListSobjects
   ├── D18  DRPCreateInfoCodeAssignments                  → bundle: PRMDRPCreateInfoCodeAssignments
   │           cond: ISNOTBLANK(%RecordsToUpdate:InfoCodeIds%) && LISTSIZE > 0
   ├── D19  SV_FilterLocations                            — Set Values: TempLoctions cache
   ├── D20  IP Action: IP_CreatePractitionerPracticeLocation
   │           integrationProcedureKey: PRM_CreateDelegatedPractitionerPracticeLocationsRecords
   │           ** IsActive = false ** — physically present, never executed in production
   │           (practitioner-location creation happens in a later OmniScript stage)
   ├── D21  IP Action: IP_CreateProviderScreenRecords
   │           integrationProcedureKey: PRM_DelegatedCreateProviderScreenRecords  (4 elements — see below)
   ├── D22  PRMDRCreateCDMForPractitioner                 → bundle: PRMDRCreateCDMForPractitioner
   │           stamps 12+ CDM flags (Account, BoardCertification, BusinessLicense,
   │           ContactProfile, Education, Hcp, HcpTaxonomy, Hfn, Identifier,
   │           InfoCodeAssignment, Language, Npi, PersonAccount, PracticeLocationPract,
   │           ProivderFeature)
   └── D23  ResponseAction                                → returns CaseManagerId,
              FeatureConfigSetting, GroupRecordIds, PractitionerEffectiveDate,
              PractitionerRole, PractitionerScreenRecordIds,
              ProviderInformationAffirmingCategory, locationsToUpsert


  ┌────────────────────────────────────────────────────────────────────────┐
  │  SUB-IP — PRM_DelegatedCreateProviderScreenRecords_Procedure_1        │
  │                                                  (4 elements)          │
  └────────────────────────────────────────────────────────────────────────┘
   ├── P1   CreateContactProfileRecords                   → bundle: PRMDRCreateContactProfileRecords
   │           cond: %IsCPDetailsFound%
   ├── P2   PersonLanguageBlock                           — Conditional Block
   │           cond: %IsPLanguageFound%
   │           ├── P3   DRTransformPersonLanguage         → DR Transform: PRMDRTransformProviderInformationData
   │           └── P4   DRCreatePersonlanguage            → bundle: PRMDRCreatePersonLanguage


  ┌────────────────────────────────────────────────────────────────────────┐
  │  RELATED IPs (called from DOWNSTREAM OmniScripts in the broader        │
  │  Delegated Practitioner journey — out of scope for this migration,     │
  │  documented here for completeness)                                     │
  └────────────────────────────────────────────────────────────────────────┘
     PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_2  (13 elt)
        → fan-out: HCPF Location Affiliation × Network × Taxonomy + ProviderFeature
        (Assistive Aids). Called from PRM_DelegatedPractitionerAddressForm OS.
     PRM_CreateDelegatedHFNRecords_Procedure_3                            (25 elt)
        → HCFN reshape: payer-network + info-code merge, similar to Off-Cycle PDA's
        HFN transformer. Called from PRM_DelegatedPractitionerReviewScreen OS.
     PRM_VerifyPractitionerDetailsForDelegated_Procedure_1                (85+ elt — heaviest)
        → diff engine: existing-practitioner vs payload, terminations, telehealth,
        timeslot rollover. Called from PRM_DelegatedPractitionerAddressForm OS.
     PRM_GetDelegatedGroup_Procedure_1                                    (3 elt)
        → form-load helper for the Group lookup on the delegated intake form.
     PRM_ValidateDelegatedInfoCodeSelection_English_1                     (7 elt)
        → screen-level validation that the delegated InfoCode picklist is set.
```

### 1.2 Element counts table

| IP | Elements | Active Version | Type | In scope (LIVE chain) |
|---|---|---|---|---|
| `PRM_PractitionerCreationContainer` | 5 | v5 | Container (TryCatch routing) | **Yes** |
| `PRM_PractitionerCreation` | 11 | v3 | Orchestrator (standard) | **Yes** |
| `PRM_DelegatedPractitionerCreation` | 23 | v6 (xml shows v7 — DataPack lags by one) | Orchestrator (delegated) | **Yes** |
| `PRM_DelegatedCreateProviderScreenRecords` | 4 | v1 | Sub-IP (delegated — active) | **Yes** |
| `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` | 13 | v2 | Sub-IP (delegated — referenced but `IsActive=false` here) | No (later OS) |
| `PRM_CreateDelegatedHFNRecords` | 25 | v3 | Sub-IP (called from Review screen OS) | No (later OS) |
| `PRM_VerifyPractitionerDetailsForDelegated` | 85+ | v1 | Sub-IP (called from Address form OS) | No (later OS) |
| `PRM_GetDelegatedGroup` | 3 | v1 | Form-load helper | No (form-load) |
| `PRM_ValidateDelegatedInfoCodeSelection_English` | 7 | v1 | Screen validation | No (screen) |

LIVE chain totals — **IBC Professional Staff path: 5 + 11 = 16 elements** ; **Delegated Credentialing path: 5 + 23 + 4 = 32 elements**.

### 1.3 Per-element catalog (grouped by orchestrator IP)

**Container — `PRM_PractitionerCreationContainer_Procedure_5`**

| # | Element | Type | Bundle / RA | Cond | Purpose |
|---|---|---|---|---|---|
| C1 | `SV_SourceIPDetails` | Set Values | — | — | Sets `SourceIPName` + `SourceIPElementName` via `IF(PractitionerCreationType == "IBC Professional Staff", ...)` for error logging context |
| C2 | `TryCatchBlock` | Try Catch Block | `PRM_OmniUtils.logTryCatchException` | — | Catches any exception thrown by C3 or C4 and writes a structured log |
| C3 | `PractitionerCreation` | IP Action | calls `PRM_PractitionerCreation` | `%PractitionerCreationType% == "IBC Professional Staff"` | Standard branch — IBX Professional Staff intake |
| C4 | `DelegatedPractitionerCreation` | IP Action | calls `PRM_DelegatedPractitionerCreation` | `%PractitionerCreationType% == "Delegated Credentialing"` | Delegated branch — vendor / delegate roster |
| C5 | `Response` | Response Action | — | — | Merged response: `CaseManagerId`, `FeatureConfigSetting`, `GroupRecordIds`, `PractitionerEffectiveDate`, `PractitionerRole`, `PractitionerScreenRecordIds`, `ProviderInformationAffirmingCategory`, `locationsToUpsert` |

**Standard branch — `PRM_PractitionerCreation_Procedure_3` (11 elt)**

| # | Element | Type | Bundle / RA | Cond | Purpose |
|---|---|---|---|---|---|
| S1 | `RA_TitleCase` | Remote Action | `PRM_OmniUtils.titleCase` | — | Title-case `FirstName` / `LastName` / `MiddleName` + concat `providerName` |
| S2 | `SV_RecordTypeIds` | Set Values (`QUERY()`) | `SELECT Id FROM RecordType WHERE SobjectType = 'HealthcarePractitionerFacility' AND (DeveloperName = 'PRM_PractitionerPracticeAffiliation' OR DeveloperName = 'PRM_PractitionerLocationAffiliation') ORDER BY DeveloperName` | — | Cache HCPF RecordType Ids |
| S3 | `DRPAccountCaseCaseManagerCreation` | DR Post | `PRMDRCreateCaseCaseManagerAndAccount` | — | Creates `Account_1` (PersonAccount practitioner), `Case_3`, `IndividualApplication_2`. Sends 22 input fields (name, DOB, NPI, IndividualApplication metadata, EffectiveFrom/To, etc.) |
| S4 | `PRMDRCreateCDM` | DR Post | `PRMDRPCDMCaseManagerLink` | `%DRPAccountCaseCaseManagerCreation:CaseManagerId% != null` | Creates `PRM_CaseDataManager__c` linked to the IA |
| S5 | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` | DR Post | `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` | — | Creates `HealthcareProvider` + 1 `HealthcareProviderTaxonomy` (primary) + 1 `BusinessLicense` (Identifier) |
| S6 | `RA_GetInfoCodesList` | Remote Action | `PRM_OmniUtils.convertToListSobjects` | — | Wraps a `List<Id>` into a `List<SObject>` shape so the next DR can map it |
| S7 | `DRPCreateInfoCodeAssignments` | DR Post | `PRMDRPCreateInfoCodeAssignments` | `ISNOTBLANK(%RecordsToUpdate:InfoCodeIds%) && LISTSIZE(%RecordsToUpdate:InfoCodeIds%) > 0` | Creates `PRM_InfoCodeAssignment__c` rows linked to the Account + CM |
| S8 | `RA_GetRecordTypeList` | Remote Action | `PRM_OmniUtils.convertToListSobjects` | — | Shapes the QUERY result from S2 into a list of `{ Id }` objects |
| S9 | `DRPPractionerPracticeLocations` | DR Post | `PRMDRPPractionerPracticeLocations` | — | Creates **2 HCPF rows** — Row 1: `IsPrimary=true`, RecordType `PRM_PractitionerPracticeAffiliation`, `PracticeLocationId=…`. Row 2: `IsPrimary=false`, RecordType `PRM_PractitionerLocationAffiliation`, `PracticeLocationId=""` |
| S10 | `PRMDRCreateCDMForPractitioner` | DR Post | `PRMDRCreateCDMForPractitioner` | — | Sets boolean flags on the CDM: `Account`, `BusinessLicense`, `Hcp`, `HcpTaxonomy`, `InfoCodeAssignment`, `PersonAccount`, `PracticeLocationPract` |
| S11 | `ResponseAction` | Response Action | — | — | Returns `{ CaseManagerId }` |

**Delegated branch — `PRM_DelegatedPractitionerCreation_Procedure_6` (23 elt)**

| # | Element | Type | Bundle / RA | Cond | Purpose |
|---|---|---|---|---|---|
| D1 | `GetFeatureConfigSetting` | DR Turbo | `PRMGetFeatureConfigSetting` | — | Read feature-config metadata into `FeatureConfigSetting` (returned in the response) |
| D2 | `RA_TitleCase` | Remote Action | `PRM_OmniUtils.titleCase` | — | Title-case names |
| D2.5 | **`PRM_PractitionerCreationValidator.validate`** | Remote Action (Callable) | `PRM_PractitionerCreationValidator.validate` | — | **NEW May 2026** (US 1416807 — AC5). Fail-fast precheck that mirrors `PRM_EffectiveDateValidation` on HCPF + HFN. Returns `{ valid, errors, errorsByCategory, errorCount, combinedMessage }`. If invalid, the IP halts before D3 |
| D3 | `DRPAccountCaseCaseManagerCreation` | DR Post | `PRMDRCreateCaseCaseManagerAndAccount` | — | Like standard S3 + extra fields: `Delegated=true`, `PRM_CredentialingStatus__c`, `PersonGenderIdentity`, `PRM_ProviderRole__c`, `PRM_IsRoundRobinLogic__c`, `email`, `gender` |
| D4 | `DRCreateGroupRecords` | DR Post | `PRMPostGroupPractitionerCreation` | — | Creates **Vendor Account** + **Group HCFNPI** + **Group Identifier (TIN)**. Sets `ParticipationStatus="Participating"`, `PRM_Pending__c=false`, `npiType="Organization"` |
| D5 | `PRMDRCreateCDM` | DR Post | `PRMDRPCDMCaseManagerLink` | `%DRPAccountCaseCaseManagerCreation:CaseManagerId% != null` | Creates `PRM_CaseDataManager__c` |
| D6 | `SV_PractitionerScreenRecordIds` | Set Values | — | — | Builds the `{AccountId, CaseDataManagerId, CaseId, CaseManagerId, PersonContactId}` map used by D21 and the response |
| D7 | `DRExtractTaxonomyData` | DR Turbo | `PRMDRExtractTaxonomyData` | — | Reads `CareTaxonomy` by Name list (`RecordsToUpdate.AdditionalSpecialties`) |
| D8 | `DRTTaxonomyData` | DR Transform | `PRMDRTransDelegatedTaxonomyData` | — | Merge extracted taxonomies with the primary `HCPTaxonomy:Name` mark |
| D9 | `DRTransformDelegatedBusinessLicense` | DR Transform | `PRMDRTransformDelegatedBusinessLicense` | — | Reshape SBRD vs DEA/CDS license rows for the merge step |
| D10 | `LA_MergeBusinessLicense` | List Merge | — | — | Merge `DEACDSBusinessLicense` + `RecordsToUpdate:BusinessLicense` by `PractitionerLicenseNumber`. `allowMergeNulls=true` |
| D11 | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` | DR Post | `PRMDRPHCPHCPTaxonomyAndBusineessLicense` | — | Creates `HealthcareProvider` + multiple Taxonomies + multiple BusinessLicenses. Returns `HealthCareProviderId` |
| D12 | `TransformAddEducation` | DR Transform | `PRMDRTransformAddEducation` | — | Shape PersonEducation input — adds `HealthcareProviderId`, `PRM_CaseManager__c`, `PersonContactId` |
| D13 | `DRPCreateEducation` | DR Post | `PRMDRPCreateEducation` | — | Creates `PersonEducation` rows |
| D14 | `DRPHCPNPIBoardCretIdentifier` | DR Post | `PRMDRPHCPNPIBoardCretIdentifier` | — | Creates `HealthcareProviderNpi` (HCPNPI) + `BoardCertification` (list) + `Identifier` (list). Conditional: `Identifiers = IF(ISNOTBLANK(Identifiers|1:Name), Identifiers, '')` |
| D15 | `SV_AdditionalNodesToFileData` | List Merge | — | `ISNOTBLANK(%FileData%)` | Stamps `FormProcess="Practitioner Participation"`, `TargetLocation="SF PDM"`, and copies `CaseManagerId` + `ParentRecordId` onto every `FileData` row |
| D16 | `DRCreateIdentiferAndDocument` | DR Post | `PRMDRCreateIdentiferAndDocument` | `ISNOTBLANK(%FileData%)` | Creates `Identifier` + `ContentVersion` + `ContentDocumentLink` chain for license documents |
| D17 | `RA_GetInfoCodesList` | Remote Action | `PRM_OmniUtils.convertToListSobjects` | — | Shape InfoCodeIds |
| D18 | `DRPCreateInfoCodeAssignments` | DR Post | `PRMDRPCreateInfoCodeAssignments` | `ISNOTBLANK(%RecordsToUpdate:InfoCodeIds%) && LISTSIZE > 0` | Creates `PRM_InfoCodeAssignment__c` rows |
| D19 | `SV_FilterLocations` | Set Values | — | — | Caches `RecordsToUpdate:Locations:Locations` into `TempLoctions` |
| D20 | `IP_CreatePractitionerPracticeLocation` | IP Action | `PRM_CreateDelegatedPractitionerPracticeLocationsRecords` | **`IsActive=false`** | Documented as the practitioner-location fan-out, but **physically inactive** in the IP today (deferred to a later OmniScript stage). Filter formula: `FILTER(LIST(SV_FilterLocations:TempLoctions.Locations), 'AccountId != NULL && AccountId != ""')` |
| D21 | `IP_CreateProviderScreenRecords` | IP Action | `PRM_DelegatedCreateProviderScreenRecords` | — | Invokes the ProviderScreen sub-IP (4 elt — see below). Inputs: `IsCPDetailsFound`, `IsPLanguageFound`, `PractitionerScreenRecordIds`, `ProviderInformation*` |
| D22 | `PRMDRCreateCDMForPractitioner` | DR Post (advancedMerge) | `PRMDRCreateCDMForPractitioner` | — | Stamps 12+ CDM flags. `advancedMergeMap` joins on `DRCreateGroupRecords:Account_1.Id` |
| D23 | `ResponseAction` | Response Action | — | — | Returns the full response object |

**Sub-IP — `PRM_DelegatedCreateProviderScreenRecords_Procedure_1` (4 elt)**

| # | Element | Type | Bundle / RA | Cond | Purpose |
|---|---|---|---|---|---|
| P1 | `CreateContactProfileRecords` | DR Post | `PRMDRCreateContactProfileRecords` | `%IsCPDetailsFound%` | Creates ContactProfile rows (cultural identity, racial identity, Hispanic origin, pronouns, etc.) |
| P2 | `PersonLanguageBlock` | Conditional Block | — | `%IsPLanguageFound%` | Wraps the PersonLanguage path |
| P3 | `DRTransformPersonLanguage` (child of P2) | DR Transform | `PRMDRTransformProviderInformationData` | — | Shape PersonLanguage rows. Filters out `value != "TESTVALUE"` |
| P4 | `DRCreatePersonlanguage` (child of P2) | DR Post | `PRMDRCreatePersonLanguage` | — | Creates `PersonLanguage` rows |

### 1.4 Existing Apex precedent (STANDARDISE candidates)

| Class | Lines | Role today | Disposition |
|---|---|---|---|
| `PRM_PractitionerCreationValidator` (May 2026) | 235 | `global Callable` — invoked as a Remote Action from `PRM_DelegatedPractitionerCreation_Procedure_6` between seq=2 (`RA_TitleCase`) and seq=3 (`DRPAccountCaseCaseManagerCreation`). Reads the OS payload, queries existing `HealthcareFacility` rows by `FacilityId`, mirrors `PRM_EffectiveDateValidation` on HCPF + HFN, and returns `{valid, errors, errorsByCategory, errorCount, combinedMessage}` so the OS halts before any DML when dates would reject downstream | **STANDARDISE** — keep verbatim; only the invocation hop changes (dispatcher calls `validator.call('validate', args)` directly inside the new `PRM_PractitionerCreationDelegatedService` between Account-create and DML, instead of via Remote Action) |
| `PRM_PractitionerCreationHelper` | 314 | LWC AuraEnabled controller — `getPracticeLocation(accountId, npi)` powers an LWC tile that shows the practitioner's delegated practice locations on the intake form. Has heavyweight Schema.Address shaping for billing / mailing / primary practice | **STANDARDISE** — keep verbatim. Used by the OmniScript-adjacent LWC, not the IP. Document the latent bug (`PRM_AddressLine1__c` referenced twice in the `FullAddress` concat instead of `PRM_AddressLine2__c`) as a separate deferred user story; do not fix as part of this migration |
| `PRM_PractitionerCreationUtility` | 32 | `global Callable` — wraps `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId(npi, taxId)` and exposes it as `getGroupData` Remote Action | **STANDARDISE** — keep verbatim; can later be folded into the dispatcher's selector layer but not in this migration |

---

## 2. Records Created / Updated

### 2.1 INSERT inventory

| SObject | Source DR / RA | Volume per submit | Notes |
|---|---|---|---|
| `Account` (PersonAccount practitioner) | `DRPAccountCaseCaseManagerCreation` (S3 / D3) | **1** | Standard: 22 input fields. Delegated: + `PersonGenderIdentity`, `PRM_CredentialingStatus__c`, `PRM_ProviderRole__c`, `email`, `gender`, `Delegated=true` |
| `Case` (the credentialing case) | `DRPAccountCaseCaseManagerCreation` (S3 / D3) — `Case_3` | **1** | RecordType `PRM`, Type `Network Management QC`, Status `New`. Delegated: `PRM_IsRoundRobinLogic__c=true` |
| `IndividualApplication` (Case Manager) | `DRPAccountCaseCaseManagerCreation` (S3 / D3) — `IndividualApplication_2` | **1** | RecordType `PDM Manual Change`, Category `Provider Data Management`, Stage `Network Management QC` |
| `PRM_CaseDataManager__c` (CDM root) | `PRMDRCreateCDM` (S4 / D5) bundle `PRMDRPCDMCaseManagerLink` | **1** | Conditional: `CaseManagerId != null` |
| `Account` (Vendor / Group, business RT) | `DRCreateGroupRecords` (D4) bundle `PRMPostGroupPractitionerCreation` | **0–1** (delegated only) | `ParticipationStatus="Participating"`, `PRM_Pending__c=false` |
| `HealthcareProviderNpi` (Group NPI) | `DRCreateGroupRecords` (D4) | **0–1** (delegated only) | `npiType="Organization"` |
| `Identifier__c` (Group TIN) | `DRCreateGroupRecords` (D4) | **0–1** (delegated only) | EIN identifier for the Vendor |
| `HealthcareProvider` (HCP — practitioner-side) | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` (S5 / D11) | **1** | Delegated returns `HealthCareProviderId` for downstream Education / Languages / Affiliations linkage |
| `HealthcareProviderTaxonomy` (HPT) | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` (S5) | **1** (standard) | Primary taxonomy only |
| `HealthcareProviderTaxonomy` (HPT, multi) | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` (D11) | **1–N** (delegated) | Primary + additional specialties from `RecordsToUpdate.AdditionalSpecialties` |
| `Identifier__c` (BusinessLicense — SBRD) | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` (S5 / D11) | **0–1** (standard) / **0–N** (delegated, merged with DEA/CDS) | License number + state + dates |
| `Identifier__c` (DEA / CDS license) | `LA_MergeBusinessLicense` (D10) → `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` (D11) | **0–N** (delegated only) | Merged by `PractitionerLicenseNumber` with the SBRD set |
| `PRM_InfoCodeAssignment__c` | `DRPCreateInfoCodeAssignments` (S7 / D18) | **0–N** | Conditional: `ISNOTBLANK(InfoCodeIds) && LISTSIZE > 0` |
| `HealthcarePractitionerFacility` (HCPF — Primary Practice Affiliation) | `DRPPractionerPracticeLocations` (S9) | **1** (standard only) | `IsPrimary=true`, `PracticeLocationId=PracticeLocationDetails:Id`, RecordType `PRM_PractitionerPracticeAffiliation`, `AttestationDate=TODAY()` |
| `HealthcarePractitionerFacility` (HCPF — Location Affiliation template) | `DRPPractionerPracticeLocations` (S9) | **1** (standard only) | `IsPrimary=false`, `PracticeLocationId=""`, RecordType `PRM_PractitionerLocationAffiliation` |
| `PersonEducation` | `DRPCreateEducation` (D13) | **0–N** (delegated only) | Linked to `HealthcareProviderId` + `PRM_CaseManager__c` |
| `HealthcareProviderNpi` (HCPNPI — practitioner) | `DRPHCPNPIBoardCretIdentifier` (D14) | **0–1** (delegated only) | Linked to HCP via `HealthcareProviderId` |
| `BoardCertification__c` | `DRPHCPNPIBoardCretIdentifier` (D14) | **0–N** (delegated only) | Wrapped in `LIST(%RecordsToUpdate:BoardCertifications%)` |
| `Identifier__c` (NPI / Medicare / etc.) | `DRPHCPNPIBoardCretIdentifier` (D14) | **0–N** (delegated only) | Conditional: `IF(ISNOTBLANK(Identifiers|1:Name), Identifiers, '')` — first-row sentinel pattern |
| `Identifier__c` + `ContentVersion` + `ContentDocumentLink` | `DRCreateIdentiferAndDocument` (D16) | **0–N** rows + content files (delegated only) | Conditional: `ISNOTBLANK(%FileData%)`. `FormProcess="Practitioner Participation"`, `TargetLocation="SF PDM"` |
| `ContactProfile` | `CreateContactProfileRecords` (P1 sub-IP) | **0–1** (delegated only) | Conditional: `%IsCPDetailsFound%`. Captures cultural / racial / Hispanic / pronouns |
| `PersonLanguage` | `DRCreatePersonlanguage` (P4 sub-IP, inside P2 Conditional Block) | **0–N** (delegated only) | Conditional: `%IsPLanguageFound%` |

### 2.2 UPDATE inventory

| SObject | Source | When | Fields touched |
|---|---|---|---|
| `PRM_CaseDataManager__c` (CDM flag stamp) | `PRMDRCreateCDMForPractitioner` (S10 / D22) bundle `PRMDRCreateCDMForPractitioner` | After all child inserts in both branches | **Standard (S10):** `Account`, `BusinessLicense`, `Hcp`, `HcpTaxonomy`, `InfoCodeAssignment`, `PersonAccount`, `PracticeLocationPract` (each set true / false based on payload presence). **Delegated (D22):** all of standard **plus** `BoardCertification`, `ContactProfile`, `Education`, `Hfn`, `Identifier`, `Language`, `Npi`, `ProivderFeature` |

> Note — the CDM-stamp is the only `UPDATE` in either branch. Everything else is `INSERT`. There is no partial update of the practitioner or any child record inside this flow (updates to those records happen in **Off Cycle PDA Review** or **PDA Review** downstream).

### 2.3 Variant axis

| `PractitionerCreationType` | Container route | Standard branch runs | Delegated branch runs | Sub-IPs called |
|---|---|---|---|---|
| `"IBC Professional Staff"` | `PRM_PractitionerCreationContainer` → `PRM_PractitionerCreation` | S1 → S11 (11 elt) | — | none |
| `"Delegated Credentialing"` | `PRM_PractitionerCreationContainer` → `PRM_DelegatedPractitionerCreation` | — | D1 → D23 (23 elt) **incl. NEW D2.5 validator gate** | `PRM_DelegatedCreateProviderScreenRecords` (4 elt) — always called; the P1 / P3+P4 children gate on `IsCPDetailsFound` / `IsPLanguageFound` |

**Secondary axes (within Delegated):**

| Variant condition | Effect |
|---|---|
| `IsCPDetailsFound = true` | P1 fires (ContactProfile row inserted) |
| `IsPLanguageFound = true` | P3 + P4 fire (PersonLanguage rows shaped + inserted) |
| `ISNOTBLANK(InfoCodeIds) && LISTSIZE > 0` | S7 / D18 fires (InfoCodeAssignments inserted) |
| `ISNOTBLANK(FileData)` | D15 + D16 fire (Identifier + ContentVersion + CDL inserted) |
| `Identifiers|1:Name` present | D14 sends the full Identifier list; otherwise it sends `''` (skip identifier insert) |
| `BoardCertifications` present | D14 inserts BoardCertification rows |
| `AdditionalSpecialties` present | D7 + D8 + D11 create additional `HealthcareProviderTaxonomy` rows alongside the primary one |
| `BusinessLicense` + `DEACDSBusinessLicense` both present | D9 + D10 merge the two license lists by `PractitionerLicenseNumber` before D11 inserts both as `Identifier__c` license rows |
| Practitioner submitted by a Vendor / Group already in PNM | D4 reuses the existing Vendor Account via `PRMPostGroupPractitionerCreation` (the DR handles the existing-vs-new branch implicitly) |
| Practitioner submitted by a brand-new Vendor / Group | D4 inserts new Account + GroupNPI + Group Identifier |

**Volume profile for the worst-case Delegated submit** (1 practitioner, 1 vendor, ~3 additional specialties, 2 DEA/CDS + 1 SBRD license, 4 education rows, 3 board certs, 5 identifiers, 5 file attachments, 2 InfoCodes):

| SObject | Rows |
|---|---|
| Account (PersonAccount) | 1 |
| Account (Vendor) | 1 |
| Case | 1 |
| IndividualApplication | 1 |
| PRM_CaseDataManager__c | 1 (+ 1 update at the end) |
| HealthcareProvider | 1 |
| HealthcareProviderTaxonomy | 4 (1 primary + 3 additional) |
| HealthcareProviderNpi | 2 (1 practitioner + 1 group) |
| Identifier__c (TIN + 3 licenses + 5 NPI/Medicare/etc. + 5 file licenses) | 14 |
| ContentVersion + ContentDocumentLink | 5 + 5 = 10 |
| PersonEducation | 4 |
| BoardCertification__c | 3 |
| PRM_InfoCodeAssignment__c | 2 |
| ContactProfile | 1 |
| PersonLanguage | ~4 |
| **TOTAL DML rows (worst case)** | **~50** |

This puts the Delegated branch comfortably under the 80-row TX1 default threshold from §6 of `prompt.md`, but **only because** the practitioner-location fan-out (`IP_CreatePractitionerPracticeLocation`) is `IsActive=false` — once that is re-enabled or moved into this flow, the row count will jump to 200+ and TX2 delegation becomes mandatory. The new architecture must support both shapes from day one.

---

## 3. Target Apex Service Architecture

### 3.1 Layered diagram

```
 ┌────────────────────────────────────────────────────────────────────────────┐
 │  OmniScript (kept)                                                         │
 │   PRM_PractitionerCreation_English v23                                     │
 │      └── IP Action element "IP_RecordCreation"                             │
 │            ↓ (JSON contract unchanged)                                     │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  Thin-wrapper IPs (kept, shrunk to 3 elements each)                        │
 │   PRM_PractitionerCreationContainer (3 elt):                               │
 │     SV_SourceIPDetails → IP_Action(PRM_ServiceInvoker) → Response          │
 │       serviceName = "PractitionerCreationDispatcher"                       │
 │       payload     = %ContextPayload%                                       │
 │                                                                            │
 │   PRM_PractitionerCreation (3 elt — only when the OS still pings it):      │
 │     SV → IP_Action(PRM_ServiceInvoker) → Response                          │
 │       serviceName = "PractitionerCreationIBC"                              │
 │   PRM_DelegatedPractitionerCreation (3 elt):                               │
 │     SV → IP_Action(PRM_ServiceInvoker) → Response                          │
 │       serviceName = "PractitionerCreationDelegated"                        │
 │   PRM_DelegatedCreateProviderScreenRecords (3 elt):                        │
 │     SV → IP_Action(PRM_ServiceInvoker) → Response                          │
 │       serviceName = "PractitionerCreationDelegatedProviderScreen"          │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  CONTROLLER LAYER  (reused — framework)                                    │
 │   PRM_ServiceDispatcher                                                    │
 │   PRM_BaseService                                                          │
 │   PRM_ServiceRequest / PRM_ServiceResponse                                 │
 │   PRM_TransactionContext                                                   │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  ORCHESTRATION LAYER  (NEW for THIS flow)                                  │
 │                                                                            │
 │   PRM_PractitionerCreationDispatcherService                                │
 │     └─→ routes on PractitionerCreationType                                 │
 │           ├─→ PRM_PractitionerCreationIBCService          (standard)       │
 │           └─→ PRM_PractitionerCreationDelegatedService    (delegated)      │
 │                  └─→ (composes) PRM_PractitionerCreationDelegatedSubIPService │
 │                                                                            │
 │  DOMAIN SERVICES (NEW + EXTEND)                                            │
 │   PRM_HCProviderRecordService    (NEW — HCProvider+Taxonomy+License atomic)│
 │   PRM_BusinessLicenseService     (NEW — DEA/CDS + SBRD merge)              │
 │   PRM_GroupAccountService        (NEW — Vendor + GroupNPI + Group TIN)     │
 │   PRM_PractitionerPracticeAffiliationService (NEW — HCPF pair create)      │
 │   PRM_HCPNPIBoardCertService     (NEW — HCPNPI + BoardCert + Identifier)   │
 │   PRM_PersonLanguageService      (NEW)                                     │
 │   PRM_ContactProfileService      (NEW)                                     │
 │   PRM_InfoCodeAssignmentService  (NEW — shared with all flows post-this)   │
 │   PRM_PractitionerCreationFileAttachmentService (NEW — File→Id+CV+CDL)     │
 │   PRM_PractitionerCreationCaseDataMgrService    (NEW — CDM flag stamp)     │
 │   PRM_CaseService.createPractitionerCreationCase(...)   (EXTEND Par Form)  │
 │   PRM_AccountUpsertHelper.createPractitionerAccount(...)(EXTEND Par Form)  │
 │   PRM_TaxonomyService.createMultiTaxonomyWithPrimary(...) (EXTEND PDA)     │
 │   PRM_IdentifierService.attachLicenseDocuments(...)     (EXTEND Par Form)  │
 │   PRM_PersonEducationService.createDelegatedEducation(...) (EXTEND ParForm)│
 │   PRM_CaseDataMgrPatcher.patchPractitionerCreation(...) (EXTEND framework) │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  SUPPORT LAYER                                                             │
 │   PRM_PractitionerCreationSelector  (NEW — bulk read façade for             │
 │     existing-HF dates, vendor-by-NPI+TIN lookup, RecordType cache)         │
 │   PRM_PractitionerCreationTransformer (NEW — taxonomy merge + license      │
 │     reshape; mirrors DRTTaxonomyData + DRTransformDelegatedBusinessLicense │
 │     + LA_MergeBusinessLicense)                                             │
 │   PRM_AccountSelector, PRM_HCFSelector, PRM_HCPFSelector,                  │
 │     PRM_IdentifierSelector, PRM_HCFNetworkSelector  (REUSE)                │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  CROSS-CUTTING (REUSE — framework)                                         │
 │   PRM_DMLUtil, PRM_CollectionUtil, PRM_GovernorUtil, PRM_ErrorLogger,      │
 │   PRM_AsyncJobBase, PRM_FeatureConfig, PRM_RecordTypeUtil,                 │
 │   PRM_BulkOperation, PRM_AsyncEnqueueGuard, PRM_CaseDataMgrPatcher         │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  STANDARDISE (existing Apex — kept verbatim)                               │
 │   PRM_PractitionerCreationValidator  (Callable — invoked SYNCHRONOUSLY     │
 │     by PRM_PractitionerCreationDelegatedService between Account-create     │
 │     and the first child DML; same call signature, dispatch path changes    │
 │     from "Remote Action wired into seq=2.5" to "inline Apex method call")  │
 │   PRM_PractitionerCreationHelper  (LWC AuraEnabled — untouched)            │
 │   PRM_PractitionerCreationUtility (Callable for getGroupData — untouched)  │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  TX1 (sync) — runs in the dispatcher request                               │
 │   ┌──────────────────────────────────────────────────────────────────────┐ │
 │   │ 1.  PractitionerCreationValidator.validate (delegated only)          │ │
 │   │ 2.  Account (PersonAccount) + Case + IndividualApplication           │ │
 │   │ 3.  PRM_CaseDataManager__c                                           │ │
 │   │ 4.  HealthcareProvider + Taxonomy (1..N) + BusinessLicense (1..N)    │ │
 │   │ 5.  Vendor Account + GroupNPI + Group Identifier  (delegated only)   │ │
 │   │ 6.  HealthcarePractitionerFacility × 2  (standard only)              │ │
 │   │ 7.  PRM_InfoCodeAssignment__c rows                                   │ │
 │   │ 8.  PRMDRCreateCDMForPractitioner flag stamp (UPDATE)                │ │
 │   │ 9.  Return response (CaseManagerId + PractitionerScreenRecordIds +   │ │
 │   │     locationsToUpsert + GroupRecordIds + ...)                        │ │
 │   └──────────────────────────────────────────────────────────────────────┘ │
 │                                                                            │
 │  TX2 (async — Queueable) — fires ONLY when delegated payload > async      │
 │                            threshold OR file attachments > 5              │
 │   ┌──────────────────────────────────────────────────────────────────────┐ │
 │   │ a.  PersonEducation rows                                             │ │
 │   │ b.  HCPNPI + BoardCertification + Identifier list                    │ │
 │   │ c.  Identifier + ContentVersion + ContentDocumentLink (file uploads) │ │
 │   │ d.  ContactProfile + PersonLanguage rows                             │ │
 │   │ e.  Fire PRM_AsyncComplete__e platform event                         │ │
 │   └──────────────────────────────────────────────────────────────────────┘ │
 ├────────────────────────────────────────────────────────────────────────────┤
 │  DATABASE + PLATFORM                                                       │
 │   SObjects (per §5.7 of prompt.md) + ContentVersion + ContentDocumentLink │
 │   PRM_AsyncComplete__e (Platform Event)                                    │
 │   PRM_ExceptionLog__c                                                      │
 └────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Transaction Boundary table (TX1 / TX2)

| Phase | TX | Scope | Rationale |
|---|---|---|---|
| 1 | TX1 | `PRM_PractitionerCreationValidator.validate(input)` — delegated only | Already production-hardened; must run BEFORE any DML to honor AC5 "all-or-nothing" |
| 2 | TX1 | `Account` (PersonAccount practitioner) + `Case` + `IndividualApplication` | Required for CaseId / CaseManagerId; OS uses these on the next screen |
| 3 | TX1 | `PRM_CaseDataManager__c` | One row; FK target for the flag-stamp update at the end of TX1 |
| 4 | TX1 | `HealthcareProvider` + `HealthcareProviderTaxonomy` (1..N) + `BusinessLicense` rows | Single bulk insert via `PRM_BulkOperation.chain()` — HCP → Taxonomy/License children. HCP returns `HealthCareProviderId` required by downstream Education + HCPNPI + BoardCert |
| 5 | TX1 | `Account` (Vendor) + `HealthcareProviderNpi` (Group) + `Identifier__c` (Group TIN) — **delegated only** | OS Response embeds `GroupRecordIds` — downstream screens (Address Form, Review Screen) need them. Cannot defer |
| 6 | TX1 | `HealthcarePractitionerFacility` × 2 — **standard only** | OS uses returned IDs for the Practice/Location toggle on the next screen |
| 7 | TX1 | `PRM_InfoCodeAssignment__c` rows | Tiny payload (0–N rows, usually < 5); user sees the resulting "Selected Info Codes" on the next screen |
| 8 | TX1 | `PRM_CaseDataManager__c` flag stamp (UPDATE) | One row; closes the create-loop atomically so downstream queries against CDM see correct flags |
| 9 | TX2 | `PersonEducation` rows | 0–N rows; not consumed by the next OS screen — safe to defer |
| 10 | TX2 | `HealthcareProviderNpi` (practitioner) + `BoardCertification__c` (list) + `Identifier__c` (NPI / Medicare / etc. list) | Not consumed by next screen until later in the cred journey |
| 11 | TX2 | `Identifier__c` + `ContentVersion` + `ContentDocumentLink` (file attachments) | Files can be heavy; defer via `PRM_AsyncEnqueueGuard` if `LISTSIZE(FileData) > 5` |
| 12 | TX2 | `ContactProfile` + `PersonLanguage` | Display-only on later screens; not blocking |
| 13 | TX2 | Publish `PRM_AsyncComplete__e` | Notify downstream listeners (the OS polls via subscribed LWC for the "all child records ready" signal — see Reinstate doc §3.4) |

**Threshold:** `PRM_FeatureConfig__mdt.PractitionerCreation_AsyncThresholdRows = 80` (default). When the delegated payload's estimated row count (calculated by `PRM_PractitionerCreationDelegatedService.estimateRowCount(input)`) exceeds 80, phases 9–12 split into TX2. Below 80, everything runs inline in TX1 (preserves today's behaviour for typical loads).

### 3.3 OmniScript / IP Dispatcher wiring

After migration, all four IPs collapse to a uniform 3-element shape:

```
PRM_PractitionerCreationContainer (3 elt — replaces today's 5-elt container):

  SV_SourceIPDetails               ← unchanged (keeps the SourceIPName for error logging)
        ↓
  IP_Action (PRM_ServiceInvoker)
     serviceName = "PractitionerCreationDispatcher"
     payload     = %ContextPayload%   ← the whole RecordsToUpdate JSON
        ↓
  ResponseAction                    ← unchanged
     additionalOutput = %ServiceResponse:data%
```

`PRM_ServiceInvoker` (already shipped — the same generic IP used by every prior migration) calls `PRM_ServiceDispatcher.invokeMethod('PractitionerCreationDispatcher', input, output, options)`. The dispatcher then routes on `input.PractitionerCreationType`:

| `PractitionerCreationType` | Routed service |
|---|---|
| `"IBC Professional Staff"` | `PRM_PractitionerCreationIBCService` |
| `"Delegated Credentialing"` | `PRM_PractitionerCreationDelegatedService` |
| anything else | `PRM_ServiceResponse.failure("Unknown PractitionerCreationType: " + value)` |

The standard / delegated / ProviderScreen orchestrator IPs each shrink to the same 3-element shape with their own service name. **No OmniScript JSON contract change.** Every output field in today's `ResponseAction` (CaseManagerId, FeatureConfigSetting, GroupRecordIds, PractitionerEffectiveDate, PractitionerRole, PractitionerScreenRecordIds, ProviderInformationAffirmingCategory, locationsToUpsert) is produced by the new orchestration service and surfaced via `PRM_ServiceResponse.data`.

### 3.4 Existing Apex preservation (STANDARDISE)

Three classes already exist in production. They are kept verbatim; only the **invocation hop** changes:

| Class | Today | After migration |
|---|---|---|
| `PRM_PractitionerCreationValidator` | Remote Action wired between seq=2 and seq=3 of `PRM_DelegatedPractitionerCreation_Procedure_6` | `PRM_PractitionerCreationDelegatedService.validatePreconditions(input)` calls `new PRM_PractitionerCreationValidator().call('validate', args)` inline before the first DML in TX1. Same Callable surface, same return shape, same business logic |
| `PRM_PractitionerCreationHelper` | LWC AuraEnabled controller (`getPracticeLocation`, `getUniqueAccountForNPITaxId`) | Unchanged. The LWC continues to call it directly. The migration does NOT consolidate this into the service layer in this user story — that is deferred (the Helper has a known latent bug at line 184/263 where `PRM_AddressLine1__c` is referenced where `PRM_AddressLine2__c` should be; documented as a separate user story) |
| `PRM_PractitionerCreationUtility` | `global Callable` for `getGroupData` Remote Action | Unchanged. Future work may fold this into `PRM_PractitionerCreationSelector` but it stays as-is in this migration |

---

## 4. Reusability Matrix

### 4.1 Framework / Cross-cutting (REUSE)

| Class | Disposition | Why this flow needs it |
|---|---|---|
| `PRM_ServiceDispatcher` | REUSE | Routes the `PractitionerCreationDispatcher` registry key to the new orchestrator |
| `PRM_BaseService` | REUSE | All three new orchestrators (`Dispatcher`, `IBC`, `Delegated`) extend it for the template-method TX1/TX2 split |
| `PRM_ServiceRequest` / `PRM_ServiceResponse` | REUSE | DTO wrappers passed across the dispatch hop |
| `PRM_TransactionContext` | REUSE | Per-request correlation ID used in every log line and async job |
| `PRM_DMLUtil` | REUSE | Partial-success inserts on all 16+ SObject families touched here |
| `PRM_CollectionUtil` | REUSE | LA-merge / filter / dedup / indexBy / flatten — replaces every `LA_*` element and the `LIST(FILTER(...))` expressions in D20 |
| `PRM_GovernorUtil` | REUSE | `shouldDelegateAsync(estimatedRowCount > 80)` decides TX1 vs TX2 |
| `PRM_ErrorLogger` | REUSE | Writes `PRM_ExceptionLog__c`; replaces every `PRM_OmniUtils.logTryCatchException` Remote Action invocation in the container's TryCatch wrapper |
| `PRM_AsyncJobBase` | REUSE | Parent class for the Queueable wrapper that handles phases 9–12 |
| `PRM_FeatureConfig` | REUSE | Reads `PractitionerCreation_UseApexService` + `PractitionerCreation_AsyncThresholdRows` cut-over flags. Also reads the `FeatureConfigSetting` payload that today's D1 DR Turbo returns into the response |
| `PRM_RecordTypeUtil` | REUSE | RecordType ID cache — exactly what S2 (`SV_RecordTypeIds`) does with a SOQL `QUERY()` Set Values today |
| `PRM_BulkOperation` | REUSE | Atomic insert + update pairs (used for HCP → Taxonomy + License chain in step 4 and HCPNPI → BoardCert + Identifier chain in step 10) |
| `PRM_AsyncEnqueueGuard` | REUSE | Wraps `System.enqueueJob` so an overrun `LimitException` falls back to inline execution (delegated payload with attachments > 5 path) |
| `PRM_CaseDataMgrPatcher` | REUSE | Generic CDM-flag merge primitive; extended below with a `patchPractitionerCreation` method |

### 4.2 Selectors

| Selector | Disposition | Notes |
|---|---|---|
| `PRM_AccountSelector` | REUSE | Practitioner / Vendor PersonAccount lookups |
| `PRM_HCFSelector` | REUSE | Existing-HF date checks (used by `PRM_PractitionerCreationValidator` today, kept verbatim) |
| `PRM_HCPFSelector` | REUSE | (Used downstream; not directly inside this flow) |
| `PRM_IdentifierSelector` | REUSE | Group TIN existence check before insert |
| `PRM_HCFNetworkSelector` | REUSE | (Used downstream by `PRM_VerifyPractitionerDetailsForDelegated`; mentioned here for chain continuity) |
| `PRM_PractitionerCreationSelector` | **NEW** | Bulk façade: HCF dates for the validator, RecordType cache for HCPF, Vendor-by-NPI+TIN lookup, FeatureConfigSetting read |

### 4.3 Transformers

| Transformer | Disposition | Notes |
|---|---|---|
| `PRM_PractitionerCreationTransformer` | **NEW** | Three responsibilities folded into one Apex class: (a) merge extracted CareTaxonomy rows with the primary-specialty mark (replaces `DRTTaxonomyData` + `PRMDRTransDelegatedTaxonomyData`); (b) reshape SBRD vs DEA/CDS license rows and merge by `PractitionerLicenseNumber` (replaces `DRTransformDelegatedBusinessLicense` + `LA_MergeBusinessLicense` + `PRMDRTransformDelegatedBusinessLicense`); (c) shape `PersonEducation` rows with FK joins to HCP / CaseManager / PersonContact (replaces `TransformAddEducation` + `PRMDRTransformAddEducation`) |
| `PRM_PersonLanguageTransformer` | **NEW** | Shape PersonLanguage rows with the `value != "TESTVALUE"` filter and the `ShareInDir` / `LastUpdatedOn` stamps (replaces `DRTransformPersonLanguage` + `PRMDRTransformProviderInformationData`) |
| `PRM_ParFormDataTransformer` | REUSE | Already used by Par Form for similar payload shaping — referenced where field paths overlap |

### 4.4 External integration

n/a — this flow has no external callouts. (Precisely address validation, NPDB lookups, and CAQH sync happen in adjacent flows — Off Cycle Submit, Par Form, PDA Review — never here.)

### 4.5 Domain / Orchestration services

| Service | Disposition | Note |
|---|---|---|
| `PRM_PractitionerCreationDispatcherService` | **NEW** | Top-level orchestrator; switches on `PractitionerCreationType` |
| `PRM_PractitionerCreationIBCService` | **NEW** | IBC Professional Staff orchestrator (covers S1 → S11) |
| `PRM_PractitionerCreationDelegatedService` | **NEW** | Delegated orchestrator (covers D1 → D23, fans out to ProviderScreen sub-service) |
| `PRM_PractitionerCreationDelegatedSubIPService` | **NEW** | Sub-IP collapse: ContactProfile + PersonLanguage (P1 → P4); called from `PRM_PractitionerCreationDelegatedService` and registered separately at `"PractitionerCreationDelegatedProviderScreen"` so the OS sub-IP can call it directly during a phased rollout |
| `PRM_CaseService.createPractitionerCreationCase(...)` | **EXTEND** (Par Form) | New method on the shared service — takes the practitioner-creation-specific Case + IndividualApplication payload (RecordType `PDM Manual Change`, Category `Provider Data Management`, Stage `Network Management QC`) |
| `PRM_AccountUpsertHelper.createPractitionerAccount(...)` | **EXTEND** (Par Form) | New method that handles both standard (`Delegated=false`) and delegated (`Delegated=true` + extra fields) variants |
| `PRM_HCProviderRecordService` | **NEW** | Atomic insert of HealthcareProvider + Taxonomy children + BusinessLicense children. Returns `{ hcpId, taxonomyIds, licenseIds }` |
| `PRM_BusinessLicenseService` | **NEW** | DEA/CDS + SBRD merge logic (composes `PRM_PractitionerCreationTransformer`) |
| `PRM_GroupAccountService` | **NEW** | Vendor Account + Group NPI + Group TIN creation — delegated only. Handles new-vs-existing-vendor branch by Vendor-by-NPI+TIN selector lookup |
| `PRM_PractitionerPracticeAffiliationService` | **NEW** | Creates the HCPF pair (Primary Practice Affiliation + Location Affiliation) — standard only. Uses `PRM_BulkOperation.chain()` so both rows are inserted in one DML |
| `PRM_HCPNPIBoardCertService` | **NEW** | Atomic insert of HCPNPI + BoardCertification + Identifier — delegated only. Mirrors the DRPHCPNPIBoardCretIdentifier bundle's all-or-nothing semantics |
| `PRM_PersonLanguageService` | **NEW** | PersonLanguage rows — delegated sub-IP |
| `PRM_ContactProfileService` | **NEW** | ContactProfile rows — delegated sub-IP |
| `PRM_InfoCodeAssignmentService` | **NEW** | Shared service (extracted now so PDA Review, Off Cycle PDA, Reinstate can all call it instead of having local DR-Post equivalents). Mirrors `PRMDRPCreateInfoCodeAssignments` bundle |
| `PRM_TaxonomyService.createMultiTaxonomyWithPrimary(hcpId, list, primary)` | **EXTEND** (PDA Review) | New method that creates 1..N taxonomy rows with exactly one `IsPrimary=true` |
| `PRM_IdentifierService.attachLicenseDocuments(licenseDocs, accountId, caseManagerId)` | **EXTEND** (Par Form) | New method that creates `Identifier__c` + `ContentVersion` + `ContentDocumentLink` together (replaces `DRCreateIdentiferAndDocument` bundle) |
| `PRM_PersonEducationService.createDelegatedEducation(...)` | **EXTEND** (Par Form) | New method that builds the FK-stamped PersonEducation insert; composes the existing single-row factory |
| `PRM_PractitionerCreationFileAttachmentService` | **NEW** | Bulk file-upload variant; defers to TX2 via `PRM_AsyncEnqueueGuard` when `LISTSIZE(FileData) > 5` |
| `PRM_PractitionerCreationCaseDataMgrService` | **NEW** | CDM flag stamper (extends `PRM_CaseDataMgrPatcher`); has separate `stampStandard(cmId, flags)` and `stampDelegated(cmId, flags)` methods because the flag sets differ (delegated stamps 12+ flags incl. BoardCertification / ContactProfile / Education / Hfn / Identifier / Language / Npi / ProivderFeature; standard stamps 7) |
| `PRM_PractitionerCreationAsyncJob` | **NEW** | Queueable wrapper for TX2 (extends `PRM_AsyncJobBase`); handles phases 9–12 |
| `PRM_PractitionerCreationValidator` | **STANDARDISE** | Existing Callable — kept verbatim, only invocation changes from Remote Action to inline `validator.call('validate', args)` |
| `PRM_PractitionerCreationHelper` | **STANDARDISE** | Existing LWC controller — untouched |
| `PRM_PractitionerCreationUtility` | **STANDARDISE** | Existing Callable for `getGroupData` — untouched |
| `PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, branch, flags)` | **EXTEND** (framework) | Adds the practitioner-creation flag-merge method to the shared patcher |

### 4.6 Reuse Score

| Bucket | Reused | Extended | New | Standardise | Total |
|---|---|---|---|---|---|
| Framework / Cross-cutting | 14 | 1 | 0 | 0 | 15 |
| Selectors | 5 | 0 | 1 | 0 | 6 |
| Transformers | 1 | 0 | 2 | 0 | 3 |
| Domain / Orchestration | 2 | 5 | 13 | 3 | 23 |
| **Totals** | **22** | **6** | **16** | **3** | **47** |

**Reuse % = (Reused + Extended + Standardise) / Total = (22 + 6 + 3) / 47 = 66.0%** (28 classes already exist verbatim or with a thin method extension; 16 net-new classes; 3 existing Apex preserved without change). The new-only ratio is 16/47 = **34%**, which is consistent with the prediction in §0 ("middleweight" migration — heavier than PDA Review's 5 new but lighter than Par Form's 14).

---

## 5. Element-by-Element Migration Map

### 5.1 Container (`PRM_PractitionerCreationContainer_Procedure_5`, 5 elt → 3 elt)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| C1 | `SV_SourceIPDetails` | Inlined into `PRM_TransactionContext.start(sourceIp)` | NEW (one-liner inside dispatcher) |
| C2 | `TryCatchBlock` | `try { ... } catch (Exception ex) { PRM_ErrorLogger.logException(ex, ctx); throw; }` inside `PRM_PractitionerCreationDispatcherService.processSync()` | REUSE (framework) |
| C3 | `PractitionerCreation` IP Action (cond: `PractitionerCreationType=="IBC Professional Staff"`) | `if (type == 'IBC Professional Staff') return ibcService.process(req);` | NEW (route inside dispatcher) |
| C4 | `DelegatedPractitionerCreation` IP Action (cond: `PractitionerCreationType=="Delegated Credentialing"`) | `if (type == 'Delegated Credentialing') return delegatedService.process(req);` | NEW (route inside dispatcher) |
| C5 | `Response` | `PRM_ServiceResponse` built by the routed service; container's Response Action element just emits `%ServiceResponse:data%` | REUSE (framework) |

### 5.2 Standard branch (`PRM_PractitionerCreation_Procedure_3`, 11 elt)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| S1 | `RA_TitleCase` | `PRM_StringUtil.titleCase(first, mid, last)` (already exists in `PRM_CollectionUtil` as a helper, or trivially inlined) | REUSE |
| S2 | `SV_RecordTypeIds` (SOQL `QUERY()`) | `PRM_RecordTypeUtil.idFor('HealthcarePractitionerFacility', 'PRM_PractitionerPracticeAffiliation')` + same for Location | REUSE |
| S3 | `DRPAccountCaseCaseManagerCreation` | `PRM_AccountUpsertHelper.createPractitionerAccount(input, false)` + `PRM_CaseService.createPractitionerCreationCase(accountId, caseDto, iaDto, false)` | EXTEND × 2 |
| S4 | `PRMDRCreateCDM` (cond: `CaseManagerId != null`) | `PRM_PractitionerCreationCaseDataMgrService.createCDM(cmId)` | NEW |
| S5 | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` | `PRM_HCProviderRecordService.createBundle(accountId, personContactId, cmId, taxonomyDto, licenseDto)` | NEW |
| S6 | `RA_GetInfoCodesList` | `PRM_CollectionUtil.wrapAsSObjectList(infoCodeIds, 'Id')` | REUSE |
| S7 | `DRPCreateInfoCodeAssignments` (cond: `ISNOTBLANK(InfoCodeIds) && LISTSIZE > 0`) | `PRM_InfoCodeAssignmentService.create(accountId, cmId, infoCodeIds, effFrom, effTo, isActive)` (guarded by the same emptiness check) | NEW |
| S8 | `RA_GetRecordTypeList` | `PRM_RecordTypeUtil.idsFor('HealthcarePractitionerFacility', new List<String>{'PRM_PractitionerPracticeAffiliation','PRM_PractitionerLocationAffiliation'})` | REUSE |
| S9 | `DRPPractionerPracticeLocations` | `PRM_PractitionerPracticeAffiliationService.createPair(accountId, personContactId, practiceLocationDto, recordTypeIds, effFrom, effTo)` | NEW |
| S10 | `PRMDRCreateCDMForPractitioner` | `PRM_PractitionerCreationCaseDataMgrService.stampStandard(cmId, flags)` (delegates to `PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, 'IBC', flags)`) | NEW + EXTEND |
| S11 | `ResponseAction` | `PRM_ServiceResponse.success(new Map{'CaseManagerId' => cmId})` | REUSE |

### 5.3 Delegated branch (`PRM_DelegatedPractitionerCreation_Procedure_6`, 23 elt)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| D1 | `GetFeatureConfigSetting` (DR Turbo) | `PRM_FeatureConfig.getSetting('Practitioner Creation')` | REUSE |
| D2 | `RA_TitleCase` | as S1 | REUSE |
| D2.5 | `PRM_PractitionerCreationValidator.validate` (Callable via RA) | `new PRM_PractitionerCreationValidator().call('validate', new Map{'input'=>input,'output'=>new Map<String,Object>()})` — called inline from `PRM_PractitionerCreationDelegatedService.validatePreconditions()` | **STANDARDISE** |
| D3 | `DRPAccountCaseCaseManagerCreation` | `PRM_AccountUpsertHelper.createPractitionerAccount(input, true)` + `PRM_CaseService.createPractitionerCreationCase(accountId, caseDto, iaDto, true)` | EXTEND × 2 |
| D4 | `DRCreateGroupRecords` | `PRM_GroupAccountService.createOrAttach(groupInfo, cmId, effFrom, effTo)` | NEW |
| D5 | `PRMDRCreateCDM` (cond: `CaseManagerId != null`) | as S4 | NEW |
| D6 | `SV_PractitionerScreenRecordIds` | Inlined into `PRM_PractitionerCreationDelegatedService.buildScreenContext(state)` | NEW (one-liner) |
| D7 | `DRExtractTaxonomyData` (DR Turbo) | `PRM_TaxonomyService.findByNames(additionalSpecialties)` | EXTEND |
| D8 | `DRTTaxonomyData` (DR Transform) | `PRM_PractitionerCreationTransformer.mergeTaxonomies(extracted, primaryName)` | NEW |
| D9 | `DRTransformDelegatedBusinessLicense` | `PRM_PractitionerCreationTransformer.reshapeLicenses(sbrd, deacds)` | NEW |
| D10 | `LA_MergeBusinessLicense` (List Merge by `PractitionerLicenseNumber`, `allowMergeNulls=true`) | `PRM_CollectionUtil.mergeListsBy('PractitionerLicenseNumber', sbrdList, deacdsList, /*allowNulls*/ true)` | REUSE |
| D11 | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense` | `PRM_HCProviderRecordService.createDelegatedBundle(accountId, personContactId, cmId, mergedTaxonomies, mergedLicenses, providerType)` | NEW |
| D12 | `TransformAddEducation` (DR Transform) | `PRM_PractitionerCreationTransformer.shapeEducation(addEducationRows, hcpId, cmId, personContactId)` | NEW |
| D13 | `DRPCreateEducation` | `PRM_PersonEducationService.createDelegatedEducation(shapedRows)` | EXTEND |
| D14 | `DRPHCPNPIBoardCretIdentifier` | `PRM_HCPNPIBoardCertService.createBundle(accountId, personContactId, hcpId, cmId, hcpNpi, boardCerts, identifiers, effFrom, effTo)` | NEW |
| D15 | `SV_AdditionalNodesToFileData` (List Merge w/ stamp) | `PRM_CollectionUtil.stampFields(fileData, new Map{'FormProcess'=>'Practitioner Participation','TargetLocation'=>'SF PDM','CaseManagerId'=>cmId,'ParentRecordId'=>accountId})` | REUSE |
| D16 | `DRCreateIdentiferAndDocument` (cond: `ISNOTBLANK(FileData)`) | `PRM_IdentifierService.attachLicenseDocuments(stampedFileData, accountId, cmId)` | EXTEND |
| D17 | `RA_GetInfoCodesList` | as S6 | REUSE |
| D18 | `DRPCreateInfoCodeAssignments` (cond as S7) | as S7 | NEW |
| D19 | `SV_FilterLocations` | Inlined into `PRM_PractitionerCreationDelegatedService.cacheLocations(input)` | NEW (one-liner) |
| D20 | `IP_CreatePractitionerPracticeLocation` (**IsActive=false** — deferred) | No-op in this migration; documented at `PRM_PractitionerCreationDelegatedService.processSync(...)` JavaDoc comment that the path was intentionally inactive at migration time. The downstream OmniScript-driven flow keeps its own service (`PRM_DelegatedPractitionerAddressFormService`, future user story) | n/a |
| D21 | `IP_CreateProviderScreenRecords` | `PRM_PractitionerCreationDelegatedSubIPService.process(input, screenCtx)` — called inline by `PRM_PractitionerCreationDelegatedService`; also registered as a standalone dispatcher key so the OS sub-IP keeps working during phased rollout | NEW |
| D22 | `PRMDRCreateCDMForPractitioner` (advancedMerge) | `PRM_PractitionerCreationCaseDataMgrService.stampDelegated(cmId, flags)` | NEW + EXTEND |
| D23 | `ResponseAction` | `PRM_ServiceResponse.success(...)` populated by `PRM_PractitionerCreationDelegatedService.buildResponse(...)` | REUSE |

### 5.4 Sub-IP — `PRM_DelegatedCreateProviderScreenRecords_Procedure_1` (4 elt)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| P1 | `CreateContactProfileRecords` (cond: `IsCPDetailsFound`) | `PRM_ContactProfileService.create(screenCtx, providerInformation, pronouns)` (guarded by `IsCPDetailsFound`) | NEW |
| P2 | `PersonLanguageBlock` (Conditional Block, cond: `IsPLanguageFound`) | `if (input.IsPLanguageFound) { ... }` inside `PRM_PractitionerCreationDelegatedSubIPService` | REUSE (framework — `if`) |
| P3 | `DRTransformPersonLanguage` (DR Transform) | `PRM_PersonLanguageTransformer.shape(languageSpoken, screenCtx)` | NEW |
| P4 | `DRCreatePersonlanguage` | `PRM_PersonLanguageService.createBulk(shapedLanguages)` | NEW |

### 5.5 Container TryCatch Remote Actions (retired)

| Today | After |
|---|---|
| `PRM_OmniUtils.logTryCatchException` (called from container's TryCatchBlock) | `PRM_ErrorLogger.logException(ex, ctx)` (called from `PRM_PractitionerCreationDispatcherService.processSync` try/catch) |
| `PRM_OmniUtils.titleCase` (S1, D2) | `PRM_CollectionUtil.titleCase(...)` |
| `PRM_OmniUtils.convertToListSobjects` (S6, S8, D17) | `PRM_CollectionUtil.wrapAsSObjectList(...)` |
| `PRM_PractitionerCreationValidator.validate` (D2.5) | unchanged (STANDARDISE — kept verbatim, invocation hop changes) |

---

## 6. Service Code — key signatures

Apex skeletons for the orchestrators, the heaviest sub-services, the extension methods, the Queueable, and every service that has unique branching logic. Each heading carries the mandatory four-callout block (Why / How / Outcome / Replaces) per `prompt.md` §3.A.

### 6.1 `PRM_PractitionerCreationDispatcherService` (top-level orchestrator, registered as `"PractitionerCreationDispatcher"`)

> **Why we need it** — Today, `PRM_PractitionerCreationContainer_Procedure_5` does the routing in OmniStudio: 5 elements (`SV_SourceIPDetails`, `TryCatchBlock`, two IP Actions with conditional formulas on `PractitionerCreationType`, `Response`). The conditional formulas (`%PractitionerCreationType% == "IBC Professional Staff"`, `%PractitionerCreationType% == "Delegated Credentialing"`) are interpreted per submit, and the TryCatch invokes a Remote Action (`PRM_OmniUtils.logTryCatchException`) for error logging. None of this is testable in isolation and the container has zero unit-test coverage.
>
> **How it helps** — Single Apex entry point that uses the Registry-Dispatcher pattern (`PRM_ServiceDispatcher`). The two branches become simple `if`/`else` in a `processSync()` method, the TryCatch becomes idiomatic Apex `try`/`catch` with `PRM_ErrorLogger.logException(ex, ctx)`, and the `SV_SourceIPDetails` cache becomes a `PRM_TransactionContext.start("PRM_PractitionerCreationContainer")` call. The service can be tested with mocked sub-services and the dispatcher key (`"PractitionerCreationDispatcher"`) is the only thing the OS needs to know.
>
> **Outcome** — 5 IP elements → 3 (`SV` + `IP_Action` + `Response`). One Remote Action retired (`PRM_OmniUtils.logTryCatchException` — replaced by `PRM_ErrorLogger`). Zero conditional-formula evaluation per request. 100% unit-testable dispatcher with mocked sub-services. Per-request `PRM_TransactionContext` correlation ID flowing through all log lines and async jobs.
>
> **Replaces** — `PRM_PractitionerCreationContainer_Procedure_5` (5 elements), `PRM_OmniUtils.logTryCatchException` Remote Action.

```apex
public with sharing class PRM_PractitionerCreationDispatcherService extends PRM_BaseService {

    public override String serviceName() { return 'PractitionerCreationDispatcher'; }

    public override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        PRM_TransactionContext ctx = PRM_TransactionContext.start('PRM_PractitionerCreationContainer');
        try {
            String type = String.valueOf(req.input.get('PractitionerCreationType'));
            if (String.isBlank(type)) {
                return PRM_ServiceResponse.failure('PractitionerCreationType is required.');
            }
            if (type == 'IBC Professional Staff') {
                return new PRM_PractitionerCreationIBCService().processSync(req);
            }
            if (type == 'Delegated Credentialing') {
                return new PRM_PractitionerCreationDelegatedService().processSync(req);
            }
            return PRM_ServiceResponse.failure('Unknown PractitionerCreationType: ' + type);
        } catch (Exception ex) {
            PRM_ErrorLogger.logException(ex, ctx, 'PRM_PractitionerCreationDispatcherService');
            return PRM_ServiceResponse.failure(ex.getMessage());
        } finally {
            ctx.end();
        }
    }
}
```

### 6.2 `PRM_PractitionerCreationDelegatedService` (heaviest sub-service — 23-element IP collapse)

> **Why we need it** — `PRM_DelegatedPractitionerCreation_Procedure_6` is the heaviest IP in this flow at **23 elements** (D1–D23) plus a 4-element sub-IP (`PRM_DelegatedCreateProviderScreenRecords`). It chains 10+ DR Posts that each create multi-SObject bundles (Account+Case+CM, Vendor+GroupNPI+TIN, HCP+Taxonomy+License, HCPNPI+BoardCert+Identifier, Identifier+ContentVersion+CDL), 3 DR Transforms, 2 List Merges, 3 Remote Actions, and 2 sub-IP calls. The IP-level conditional formulas re-evaluate on every step (`ISNOTBLANK(FileData)`, `LISTSIZE(InfoCodeIds) > 0`, `CaseManagerId != null`) and the TryCatch is at the container level only, so a failure in D11 (HCP+Taxonomy+License) leaves D3 (Account+Case+CM) and D4 (Vendor) committed in a partially-credentialed state with no rollback.
>
> **How it helps** — Single Apex orchestrator that drives the TX1/TX2 split deterministically. The Validator gate (D2.5, NEW May 2026 STANDARDISE) runs first and short-circuits the whole submit if EffectiveDates would reject downstream. The TX1 phase composes 7 atomic sub-services (`PRM_AccountUpsertHelper`, `PRM_CaseService`, `PRM_PractitionerCreationCaseDataMgrService`, `PRM_HCProviderRecordService`, `PRM_GroupAccountService`, `PRM_BulkOperation.atomicPair()` for HCP→Taxonomy/License, `PRM_InfoCodeAssignmentService`) using `PRM_DMLUtil` for partial-success semantics. Anything not consumed by the next OS screen (Education, HCPNPI/BoardCert, file uploads, ContactProfile, PersonLanguage) is deferred to TX2 via `PRM_AsyncEnqueueGuard.enqueue(new PRM_PractitionerCreationAsyncJob(state))` when `PRM_GovernorUtil.shouldDelegateAsync(estimateRowCount(input) > 80)`. The advancedMerge in D22 becomes `PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, 'Delegated', flagMap)`.
>
> **Outcome** — 23 IP elements + 4 sub-IP elements = 27 elements → ~250 lines of Apex. Worst-case Delegated submit: ~50 DML rows, ~12 SOQL queries → 4 SOQL + 8 DML statements. TX1 sync time projected < 800 ms (vs. 2.5–4 s today on a typical delegated submit). 3 Remote Actions retired. 2 List Merge elements collapsed into `PRM_CollectionUtil.mergeListsBy(...)`. Validator runs inline → save ~1 round-trip. Race condition between OS-advance and CDM-flag-stamp eliminated by stamping inside TX1 phase 8 (no advancedMerge needed because we already hold the Group Account ID in memory).
>
> **Replaces** — `PRM_DelegatedPractitionerCreation_Procedure_6` (23 elements: D1–D23), `PRM_DelegatedCreateProviderScreenRecords_Procedure_1` (4 elements: P1–P4 — folded into a separately-registered sub-service), DR bundles `PRMDRCreateCaseCaseManagerAndAccount`, `PRMPostGroupPractitionerCreation`, `PRMDRPCDMCaseManagerLink`, `PRMDRExtractTaxonomyData`, `PRMDRTransDelegatedTaxonomyData`, `PRMDRTransformDelegatedBusinessLicense`, `PRMDRPHCPHCPTaxonomyAndBusineessLicense`, `PRMDRTransformAddEducation`, `PRMDRPCreateEducation`, `PRMDRPHCPNPIBoardCretIdentifier`, `PRMDRCreateIdentiferAndDocument`, `PRMDRPCreateInfoCodeAssignments`, `PRMDRCreateContactProfileRecords`, `PRMDRTransformProviderInformationData`, `PRMDRCreatePersonLanguage`, `PRMDRCreateCDMForPractitioner`, Remote Actions `PRM_OmniUtils.titleCase` + `PRM_OmniUtils.convertToListSobjects` (×2).

```apex
public with sharing class PRM_PractitionerCreationDelegatedService extends PRM_BaseService {

    private final PRM_PractitionerCreationValidator validator = new PRM_PractitionerCreationValidator();
    private final PRM_PractitionerCreationTransformer transformer = new PRM_PractitionerCreationTransformer();
    private final PRM_PractitionerCreationSelector selector = new PRM_PractitionerCreationSelector();

    public override String serviceName() { return 'PractitionerCreationDelegated'; }

    public override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        // D2.5 — fail-fast precheck (STANDARDISE)
        Map<String, Object> vArgs = new Map<String, Object>{
            'input' => req.input, 'output' => new Map<String, Object>()
        };
        Map<String, Object> vResult = (Map<String, Object>) validator.call('validate', vArgs);
        if (vResult.get('valid') != true) {
            return PRM_ServiceResponse.failure((String) vResult.get('combinedMessage'), vResult);
        }

        // D2 — title case
        Map<String, String> name = PRM_CollectionUtil.titleCase(req.input);

        // TX1 phases 2–8 (per §3.2)
        Id accountId = PRM_AccountUpsertHelper.createPractitionerAccount(req.input, /*delegated*/ true, name);
        Map<String, Id> caseIds = PRM_CaseService.createPractitionerCreationCase(accountId, req.input, /*delegated*/ true);
        Id cmId = caseIds.get('IndividualApplicationId');
        Id cdmId = new PRM_PractitionerCreationCaseDataMgrService().createCDM(cmId);

        // D7–D11 — HCP + multi-Taxonomy + multi-License atomic
        List<HealthcareProviderTaxonomy> taxonomies = transformer.mergeTaxonomies(
            selector.findTaxonomiesByName(req.input.get('AdditionalSpecialties')),
            (String) ((Map<String, Object>) req.input.get('HCPTaxonomy')).get('Name')
        );
        List<Identifier> licenses = transformer.reshapeAndMergeLicenses(
            (Map<String, Object>) req.input.get('BusinessLicense'),
            (Map<String, Object>) req.input.get('DEACDSBusinessLicense')
        );
        Map<String, Object> hcpBundle = new PRM_HCProviderRecordService().createDelegatedBundle(
            accountId, caseIds.get('PersonContactId'), cmId, taxonomies, licenses, req.input.get('ProviderType')
        );
        Id hcpId = (Id) hcpBundle.get('hcpId');

        // D4 — Vendor + GroupNPI + Group TIN
        Map<String, Object> groupResult = new PRM_GroupAccountService()
            .createOrAttach((Map<String, Object>) req.input.get('PractionerGroup'), cmId, req.input);

        // D17–D18 — InfoCodes
        List<Id> infoCodeIds = (List<Id>) req.input.get('InfoCodeIds');
        if (infoCodeIds != null && !infoCodeIds.isEmpty()) {
            new PRM_InfoCodeAssignmentService().create(accountId, cmId, infoCodeIds, req.input);
        }

        // D22 — flag stamp UPDATE
        new PRM_PractitionerCreationCaseDataMgrService().stampDelegated(cmId, computeDelegatedFlags(req.input, hcpBundle));

        // TX2 fan-out (phases 9–12) — defer when row count is large
        Map<String, Object> tx2State = buildTx2State(req.input, accountId, cmId, hcpId, caseIds, groupResult);
        if (PRM_GovernorUtil.shouldDelegateAsync(estimateAsyncRowCount(req.input))) {
            PRM_AsyncEnqueueGuard.enqueue(new PRM_PractitionerCreationAsyncJob(tx2State));
        } else {
            processTx2Inline(tx2State);
        }

        return PRM_ServiceResponse.success(buildResponse(cmId, accountId, hcpId, caseIds, groupResult, req.input));
    }

    @TestVisible
    private Integer estimateAsyncRowCount(Map<String, Object> input) {
        return PRM_CollectionUtil.size(input.get('AddEducation'))
             + PRM_CollectionUtil.size(input.get('BoardCertifications'))
             + PRM_CollectionUtil.size(input.get('Identifiers'))
             + (PRM_CollectionUtil.size(input.get('FileData')) * 3)  // Identifier + CV + CDL
             + (Boolean.valueOf(input.get('IsCPDetailsFound')) ? 1 : 0)
             + (Boolean.valueOf(input.get('IsPLanguageFound')) ? PRM_CollectionUtil.size(((Map<String,Object>)input.get('ProviderInformationLanguageSpoken')).get('LangaugesSpoken RecordCreation')) : 0);
    }

    // ... 80 more lines: buildTx2State, processTx2Inline, computeDelegatedFlags, buildResponse, cacheLocations
}
```

### 6.3 `PRM_PractitionerCreationIBCService` (standard branch — 11-element IP collapse)

> **Why we need it** — `PRM_PractitionerCreation_Procedure_3` is the lighter of the two branches at 11 elements, but it carries the same FK chain (Account → Case → IndividualApplication → CDM → HCP+Taxonomy+License → 2 HCPF rows → InfoCodeAssignments → CDM flag stamp). Today every step is a DR Post or Remote Action, each emitting its own SOQL queries and its own DML statement (no bulk batching across steps), and a failure mid-chain leaves orphaned parent records with no compensating rollback. The IP also relies on a SOQL `QUERY()` Set Values element (S2) to cache 2 RecordType Ids — repeated on every submit instead of being cached per-transaction.
>
> **How it helps** — Single orchestrator that composes the same shared services as the delegated branch (`PRM_AccountUpsertHelper`, `PRM_CaseService`, `PRM_HCProviderRecordService`, `PRM_InfoCodeAssignmentService`, `PRM_CaseDataMgrPatcher`) plus one branch-specific service (`PRM_PractitionerPracticeAffiliationService` for the HCPF pair). RecordType lookup is delegated to `PRM_RecordTypeUtil` which uses Apex describe-call caching (1 describe per transaction, not 1 SOQL per submit). The HCPF pair is built using `PRM_BulkOperation.chain()` so the Primary Practice Affiliation and the Location Affiliation are inserted in a single DML statement with the right FK ordering — no orphan possible.
>
> **Outcome** — 11 IP elements → ~120 lines of Apex. 9 DML statements today → 4 DML statements (Account+Case+IA bundle / CDM / HCP+Taxonomy+License bundle / HCPF pair + InfoCodes + flag stamp via `Database.update` UPDATE). 3 Remote Actions retired (`titleCase`, two `convertToListSobjects`). SOQL `QUERY()` Set Values retired. Sync time projected < 500 ms.
>
> **Replaces** — `PRM_PractitionerCreation_Procedure_3` (11 elements: S1–S11), DR bundles `PRMDRCreateCaseCaseManagerAndAccount`, `PRMDRPCDMCaseManagerLink`, `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense`, `PRMDRPCreateInfoCodeAssignments`, `PRMDRPPractionerPracticeLocations`, `PRMDRCreateCDMForPractitioner`, Remote Actions `PRM_OmniUtils.titleCase` + `PRM_OmniUtils.convertToListSobjects` (×2).

```apex
public with sharing class PRM_PractitionerCreationIBCService extends PRM_BaseService {

    public override String serviceName() { return 'PractitionerCreationIBC'; }

    public override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        Map<String, String> name = PRM_CollectionUtil.titleCase(req.input);

        Id practiceRT  = PRM_RecordTypeUtil.idFor('HealthcarePractitionerFacility', 'PRM_PractitionerPracticeAffiliation');
        Id locationRT  = PRM_RecordTypeUtil.idFor('HealthcarePractitionerFacility', 'PRM_PractitionerLocationAffiliation');

        Id accountId = PRM_AccountUpsertHelper.createPractitionerAccount(req.input, /*delegated*/ false, name);
        Map<String, Id> caseIds = PRM_CaseService.createPractitionerCreationCase(accountId, req.input, /*delegated*/ false);
        Id cmId = caseIds.get('IndividualApplicationId');
        new PRM_PractitionerCreationCaseDataMgrService().createCDM(cmId);

        Map<String, Object> hcpBundle = new PRM_HCProviderRecordService().createBundle(
            accountId, caseIds.get('PersonContactId'), cmId,
            (Map<String, Object>) req.input.get('HCPTaxonomy'),
            (Map<String, Object>) req.input.get('BusinessLicense')
        );

        List<Id> infoCodeIds = (List<Id>) req.input.get('InfoCodeIds');
        if (infoCodeIds != null && !infoCodeIds.isEmpty()) {
            new PRM_InfoCodeAssignmentService().create(accountId, cmId, infoCodeIds, req.input);
        }

        new PRM_PractitionerPracticeAffiliationService().createPair(
            accountId, caseIds.get('PersonContactId'),
            (Map<String, Object>) req.input.get('PracticeLocationDetails'),
            new Map<String, Id>{ 'practice' => practiceRT, 'location' => locationRT },
            req.input
        );

        new PRM_PractitionerCreationCaseDataMgrService().stampStandard(cmId, computeStandardFlags(req.input));

        return PRM_ServiceResponse.success(new Map<String, Object>{ 'CaseManagerId' => cmId });
    }

    @TestVisible
    private Map<String, Boolean> computeStandardFlags(Map<String, Object> input) {
        return new Map<String, Boolean>{
            'Account' => input.get('PractionerDetails') != null,
            'BusinessLicense' => input.get('BusinessLicense') != null && !((Map<String, Object>) input.get('BusinessLicense')).isEmpty(),
            'Hcp' => input.get('HCPTaxonomy') != null,
            'HcpTaxonomy' => input.get('HCPTaxonomy') != null,
            'InfoCodeAssignment' => input.get('InfoCodeIds') != null,
            'PersonAccount' => input.get('PractionerDetails') != null,
            'PracticeLocationPract' => input.get('PracticeLocationDetails') != null
        };
    }
}
```

### 6.4 `PRM_HCProviderRecordService` (NEW — atomic HCP + Taxonomy + License bundle)

> **Why we need it** — The DR Post bundles `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (standard) and `PRMDRPHCPHCPTaxonomyAndBusineessLicense` (delegated) create up to three SObject families in a single bundle, but the DataRaptor framework does not enforce atomicity — if HealthcareProvider inserts and HealthcareProviderTaxonomy fails the FK validation, the HCP is committed without its taxonomy. The IBX QC team has flagged this as a real production gap (CDM stamps `Hcp=true` and `HcpTaxonomy=true` after the fact, but the actual taxonomy row is missing). The delegated branch makes this worse because it inserts multiple taxonomies and multiple licenses with merged DEA/CDS rows.
>
> **How it helps** — Single Apex service that uses `PRM_BulkOperation.chain()` to insert HCP first, then stamp `HealthCareProviderId` into the child Taxonomy + License rows in memory, then insert both child lists in one bulk DML. If any child fails, `PRM_DMLUtil.insertWithRollback` rolls the whole bundle back via a savepoint and the orchestrator re-throws so the dispatcher's try/catch returns a clean `PRM_ServiceResponse.failure(...)` to the OS. The two call signatures (`createBundle` for standard, `createDelegatedBundle` for delegated multi-taxonomy / merged-license) share the same internal `_insertBundle` private method.
>
> **Outcome** — Zero orphaned HCP rows. 3 DML statements → 2 DML statements (HCP / Taxonomy+License combined). Atomicity guaranteed via savepoint. Delegated worst case (4 taxonomies + 3 licenses) → still 2 DML.
>
> **Replaces** — DR bundles `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (standard) + `PRMDRPHCPHCPTaxonomyAndBusineessLicense` (delegated).

```apex
public with sharing class PRM_HCProviderRecordService {

    public Map<String, Object> createBundle(Id accountId, Id personContactId, Id cmId,
                                            Map<String, Object> hcpTaxonomyDto,
                                            Map<String, Object> licenseDto) {
        HealthcareProvider hcp = buildHcp(accountId, personContactId, cmId, hcpTaxonomyDto);
        return _insertBundle(hcp,
            new List<HealthcareProviderTaxonomy>{ buildTaxonomy(null, hcpTaxonomyDto, /*primary*/ true) },
            buildLicenseList(null, accountId, cmId, licenseDto)
        );
    }

    public Map<String, Object> createDelegatedBundle(Id accountId, Id personContactId, Id cmId,
                                                     List<HealthcareProviderTaxonomy> taxonomies,
                                                     List<Identifier> licenses,
                                                     Object providerType) {
        HealthcareProvider hcp = buildHcp(accountId, personContactId, cmId, null);
        hcp.PRM_ProviderType__c = String.valueOf(providerType);
        return _insertBundle(hcp, taxonomies, licenses);
    }

    private Map<String, Object> _insertBundle(HealthcareProvider hcp,
                                              List<HealthcareProviderTaxonomy> taxonomies,
                                              List<Identifier> licenses) {
        Savepoint sp = Database.setSavepoint();
        try {
            PRM_DMLUtil.insertWithRollback(new List<SObject>{ hcp });
            for (HealthcareProviderTaxonomy t : taxonomies) t.HealthcareProviderId = hcp.Id;
            for (Identifier i : licenses) i.HealthcareProviderId__c = hcp.Id;
            List<SObject> children = new List<SObject>();
            children.addAll((List<SObject>) taxonomies);
            children.addAll((List<SObject>) licenses);
            PRM_DMLUtil.insertWithRollback(children);
            return new Map<String, Object>{
                'hcpId' => hcp.Id,
                'taxonomyIds' => PRM_CollectionUtil.ids(taxonomies),
                'licenseIds' => PRM_CollectionUtil.ids(licenses)
            };
        } catch (Exception ex) {
            Database.rollback(sp);
            throw ex;
        }
    }

    // ... buildHcp, buildTaxonomy, buildLicenseList (60+ lines)
}
```

### 6.5 `PRM_BusinessLicenseService` (NEW — DEA/CDS + SBRD merge)

> **Why we need it** — Delegated submits carry two license lists: `BusinessLicense` (SBRD — state board licenses) and `DEACDSBusinessLicense` (federal DEA + Controlled Drug Substance licenses). Today, the merge happens across three IP elements (`DRTransformDelegatedBusinessLicense`, `LA_MergeBusinessLicense`, `DRPHCProviderHCProviderTaxonomyAndBusineessLicense`) using DR Transform + List Merge with `mergeListsOrder`, `primaryListKey: "PractitionerLicenseNumber"`, `allowMergeNulls: true`. The reshape semantics live in a DataRaptor bundle (`PRMDRTransformDelegatedBusinessLicense`) that is hard to test and not callable from any other flow. Off-Cycle Submit's roadmap calls for the same DEA-vs-SBRD merge.
>
> **How it helps** — Pure-Apex service composing `PRM_CollectionUtil.mergeListsBy()` and `PRM_PractitionerCreationTransformer.reshapeAndMergeLicenses()`. The reshape rules (DEA-only fields → Identifier with `Type=DEA`, CDS-only fields → `Type=CDS`, state-license fields → `Type=License`) live in one well-tested Apex class. The merge key (`PractitionerLicenseNumber`) is parameterized so the same service can serve Off-Cycle Submit and PDA Review.
>
> **Outcome** — 3 IP elements (D9 + D10 + the license-input section of D11) → 1 service method call. 100% unit-test coverage on the reshape rules. Shareable with future Off-Cycle, PDA Review, Reinstate use cases.
>
> **Replaces** — DR Transform `PRMDRTransformDelegatedBusinessLicense`, List Merge `LA_MergeBusinessLicense`, and the license-merge portion of bundle `PRMDRPHCPHCPTaxonomyAndBusineessLicense`.

```apex
public with sharing class PRM_BusinessLicenseService {

    public List<Identifier> mergeAndBuild(Map<String, Object> sbrdRaw, Map<String, Object> deacdsRaw,
                                          Id accountId, Id caseManagerId, Date effFrom, Date effTo) {
        List<Map<String, Object>> sbrd = PRM_CollectionUtil.wrapList(sbrdRaw);
        List<Map<String, Object>> deacds = new PRM_PractitionerCreationTransformer()
            .reshapeDEACDS(deacdsRaw);
        List<Map<String, Object>> merged = PRM_CollectionUtil.mergeListsBy(
            'PractitionerLicenseNumber', sbrd, deacds, /*allowNulls*/ true
        );
        List<Identifier> rows = new List<Identifier>();
        for (Map<String, Object> row : merged) {
            rows.add(toIdentifier(row, accountId, caseManagerId, effFrom, effTo));
        }
        return rows;
    }

    @TestVisible
    private Identifier toIdentifier(Map<String, Object> row, Id accountId, Id cmId, Date effFrom, Date effTo) {
        Identifier i = new Identifier();
        i.ParentRecordId = accountId;
        i.PRM_CaseManager__c = cmId;
        i.PRM_EffectiveFrom__c = effFrom;
        i.PRM_EffectiveTo__c = effTo;
        i.PRM_Type__c = (String) row.get('LicenseType');  // 'License' / 'DEA' / 'CDS'
        i.IdValue = (String) row.get('PractitionerLicenseNumber');
        i.PRM_State__c = (String) row.get('PractitionerState');
        i.PRM_IssuedDate__c = PRM_DateUtil.parse(row.get('LicenseIssuedDate'));
        i.PRM_ExpirationDate__c = PRM_DateUtil.parse(row.get('LicenseExpirationDate'));
        return i;
    }
}
```

### 6.6 `PRM_GroupAccountService` (NEW — Vendor + Group NPI + Group TIN — delegated only)

> **Why we need it** — `DRCreateGroupRecords` (D4, bundle `PRMPostGroupPractitionerCreation`) creates a Vendor Account, a GroupNPI (`HealthcareProviderNpi` with `npiType="Organization"`), and a Group TIN (`Identifier__c` of type EIN) in one bundle. It has implicit behaviour: if an existing Vendor already has the NPI+TIN combination, the DR reuses the existing rows; otherwise it inserts new ones. There is no Apex equivalent today, so other flows (Par Form, Off Cycle) re-implement this logic locally.
>
> **How it helps** — Extracted as its own service so Par Form / Off Cycle / Reinstate Vendor can all use the same Vendor-by-NPI+TIN selector + create logic. Uses `PRM_AccountSelector.findVendorByNpiAndTin()` and `PRM_IdentifierSelector.findEinByValue()` to detect existing vendors and only inserts when the group is brand-new. Returns `{ vendorAccountId, groupNpiId, groupTinId, isNew }` so callers can branch on first-vs-repeat group submissions.
>
> **Outcome** — 1 IP element + 1 DR bundle + implicit existing-vs-new logic → 1 Apex service method. Eliminates duplicate vendor inserts (today a delegated submit with the wrong NPI silently creates a brand-new vendor instead of reusing the existing one). Shareable with 3 other flows.
>
> **Replaces** — DR bundle `PRMPostGroupPractitionerCreation` and the implicit existing-vendor detection logic embedded in it.

```apex
public with sharing class PRM_GroupAccountService {

    public Map<String, Object> createOrAttach(Map<String, Object> groupInfo, Id cmId, Map<String, Object> input) {
        Map<String, Object> g = (Map<String, Object>) groupInfo.get('GroupInformation');
        String npi = (String) g.get('GroupNPI');
        String tin = (String) g.get('GroupTaxId');
        Id existingVendorId = new PRM_AccountSelector().findVendorByNpiAndTin(npi, tin);
        if (existingVendorId != null) {
            return new Map<String, Object>{
                'vendorAccountId' => existingVendorId,
                'isNew' => false
            };
        }
        Account vendor = buildVendor(g, cmId, input);
        PRM_DMLUtil.insertWithRollback(new List<SObject>{ vendor });
        HealthcareProviderNpi npiRow = buildGroupNpi(vendor.Id, npi, cmId);
        Identifier tinRow = buildGroupTin(vendor.Id, tin, cmId);
        PRM_DMLUtil.insertWithRollback(new List<SObject>{ npiRow, tinRow });
        return new Map<String, Object>{
            'vendorAccountId' => vendor.Id,
            'groupNpiId' => npiRow.Id,
            'groupTinId' => tinRow.Id,
            'isNew' => true
        };
    }
    // ... buildVendor, buildGroupNpi, buildGroupTin (40 lines)
}
```

### 6.7 `PRM_PractitionerPracticeAffiliationService` (NEW — HCPF pair create — standard only)

> **Why we need it** — `DRPPractionerPracticeLocations` (S9, bundle `PRMDRPPractionerPracticeLocations`) creates **2 HCPF rows** in one DR Post: Row 1 is the Primary Practice Affiliation (`IsPrimary=true`, RecordType `PRM_PractitionerPracticeAffiliation`, `PracticeLocationId=…`), Row 2 is the Location Affiliation template (`IsPrimary=false`, RecordType `PRM_PractitionerLocationAffiliation`, blank `PracticeLocationId`). The 2-row insert is bundled but not atomic; if Row 2 fails the FK validation, Row 1 commits as a primary-only orphan with no location-affiliation companion. The RecordType lookup runs as a SOQL `QUERY()` (S2) re-evaluated per submit.
>
> **How it helps** — Apex service composing `PRM_RecordTypeUtil` (cached describe-call) + `PRM_BulkOperation.chain()` for the 2-row insert wrapped in a savepoint. The method signature is explicit (`createPair(accountId, personContactId, practiceLocationDto, recordTypeIds, input)`) so all required FK targets are passed in, and the result is `{ practiceAffiliationId, locationAffiliationId }`.
>
> **Outcome** — Atomic insert: either both HCPF rows commit or neither does. RecordType SOQL eliminated (Apex describe cache). 100% unit-test coverage on the IsPrimary / RecordType / blank-PracticeLocationId rules.
>
> **Replaces** — DR bundle `PRMDRPPractionerPracticeLocations`, plus the SOQL `QUERY()` in `SV_RecordTypeIds` (S2) and the Remote Action wrapping it (`RA_GetRecordTypeList`, S8).

```apex
public with sharing class PRM_PractitionerPracticeAffiliationService {

    public Map<String, Id> createPair(Id accountId, Id personContactId,
                                      Map<String, Object> practiceLocationDto,
                                      Map<String, Id> recordTypeIds,
                                      Map<String, Object> input) {
        Savepoint sp = Database.setSavepoint();
        try {
            HealthcarePractitionerFacility primary = new HealthcarePractitionerFacility();
            primary.RecordTypeId = recordTypeIds.get('practice');
            primary.IsPrimary = true;
            primary.AccountId = accountId;
            primary.PRM_PractitionerContact__c = personContactId;
            primary.LocationId = (Id) practiceLocationDto.get('Id');
            primary.PRM_EffectiveFrom__c = PRM_DateUtil.parse(input.get('EffectiveFrom'));
            primary.PRM_EffectiveTo__c = PRM_DateUtil.parse(input.get('EffectiveTo'));
            primary.PRM_AttestationDate__c = Date.today();
            primary.PRM_Active__c = (Boolean) input.get('IsRecordActive');

            HealthcarePractitionerFacility location = new HealthcarePractitionerFacility();
            location.RecordTypeId = recordTypeIds.get('location');
            location.IsPrimary = false;
            location.AccountId = accountId;
            location.PRM_PractitionerContact__c = personContactId;
            location.PRM_EffectiveFrom__c = primary.PRM_EffectiveFrom__c;
            location.PRM_EffectiveTo__c = primary.PRM_EffectiveTo__c;
            location.PRM_Active__c = primary.PRM_Active__c;

            PRM_DMLUtil.insertWithRollback(new List<SObject>{ primary, location });
            return new Map<String, Id>{
                'practiceAffiliationId' => primary.Id,
                'locationAffiliationId' => location.Id
            };
        } catch (Exception ex) {
            Database.rollback(sp);
            throw ex;
        }
    }
}
```

### 6.8 `PRM_HCPNPIBoardCertService` (NEW — HCPNPI + BoardCert + Identifier atomic — delegated only)

> **Why we need it** — `DRPHCPNPIBoardCretIdentifier` (D14, bundle `PRMDRPHCPNPIBoardCretIdentifier`) creates a `HealthcareProviderNpi`, a list of `BoardCertification__c` rows, and a list of `Identifier__c` rows (Medicare number, etc.) in one bundle. The bundle has the same first-row sentinel pattern as elsewhere (`Identifiers = IF(ISNOTBLANK(Identifiers|1:Name), Identifiers, '')`) — if the first identifier is blank, the whole identifier list is dropped, which silently swallows real identifier rows in malformed payloads.
>
> **How it helps** — Apex service that takes explicit lists (no sentinel hack) and inserts in two phases inside a savepoint: phase 1 inserts the HCPNPI (parent), phase 2 stamps `PRM_HealthcareProviderNpi__c` onto the children (BoardCerts) and inserts both child lists in one DML. Explicit empty-list handling (the caller decides; the service does not silently skip).
>
> **Outcome** — Atomic insert (savepoint rollback on any child failure). Sentinel hack retired (no more silently-dropped identifier rows). 1 DML → 2 DML (HCPNPI then children). 100% unit-test coverage on FK stamping.
>
> **Replaces** — DR bundle `PRMDRPHCPNPIBoardCretIdentifier`.

```apex
public with sharing class PRM_HCPNPIBoardCertService {

    public Map<String, Object> createBundle(Id accountId, Id personContactId, Id hcpId, Id cmId,
                                            String npi, List<Map<String, Object>> boardCertRows,
                                            List<Map<String, Object>> identifierRows,
                                            Date effFrom, Date effTo) {
        Savepoint sp = Database.setSavepoint();
        try {
            HealthcareProviderNpi npiRow = buildHcpnpi(accountId, hcpId, npi, cmId, effFrom, effTo);
            PRM_DMLUtil.insertWithRollback(new List<SObject>{ npiRow });

            List<SObject> children = new List<SObject>();
            for (Map<String, Object> bc : boardCertRows) children.add(buildBoardCert(bc, hcpId, cmId));
            for (Map<String, Object> id : identifierRows) children.add(buildIdentifier(id, accountId, cmId));
            if (!children.isEmpty()) {
                PRM_DMLUtil.insertWithRollback(children);
            }
            return new Map<String, Object>{
                'hcpNpiId' => npiRow.Id,
                'boardCertIds' => PRM_CollectionUtil.idsByType(children, BoardCertification__c.SObjectType),
                'identifierIds' => PRM_CollectionUtil.idsByType(children, Identifier.SObjectType)
            };
        } catch (Exception ex) {
            Database.rollback(sp);
            throw ex;
        }
    }
    // ... buildHcpnpi, buildBoardCert, buildIdentifier (40 lines)
}
```

### 6.9 `PRM_PractitionerCreationAsyncJob` (NEW — Queueable for TX2 fan-out)

> **Why we need it** — When the Delegated payload exceeds the `PractitionerCreation_AsyncThresholdRows` cut-over (default 80), inserting Education + HCPNPI/BoardCert + file attachments + ContactProfile + PersonLanguage all in TX1 risks exceeding governor limits and stretching the user-facing latency past 3 seconds. Today, that whole list runs sync inside the IP and either succeeds slowly or throws halfway through, leaving partial child records with no compensation.
>
> **How it helps** — Queueable wrapper extending `PRM_AsyncJobBase` (which provides the try/catch + `PRM_AsyncComplete__e` platform event publication). Receives a serialised state map from the orchestrator (account ID, CM ID, HCP ID, child payloads), re-instantiates the sub-services, and runs phases 9–12 (Education / HCPNPI / FileAttachments / ContactProfile / PersonLanguage) in a separate transaction. `PRM_AsyncEnqueueGuard.enqueue()` wraps the `System.enqueueJob` call so a `LimitException` (no async slots left) falls back to inline execution with a logged warning instead of failing the whole submit.
>
> **Outcome** — TX1 latency stays under 800 ms even on the largest delegated submits. Async slot exhaustion never fails a submit (graceful fallback). Downstream LWC subscribers receive `PRM_AsyncComplete__e` and refresh the screen when TX2 finishes.
>
> **Replaces** — n/a (net-new — today's flow runs everything sync).

```apex
public with sharing class PRM_PractitionerCreationAsyncJob extends PRM_AsyncJobBase {

    private final Map<String, Object> state;

    public PRM_PractitionerCreationAsyncJob(Map<String, Object> state) {
        super('PractitionerCreationAsync', (Id) state.get('cmId'));
        this.state = state;
    }

    public override void run() {
        Id accountId = (Id) state.get('accountId');
        Id cmId = (Id) state.get('cmId');
        Id hcpId = (Id) state.get('hcpId');
        Id personContactId = (Id) state.get('personContactId');

        // Phase 9 — Education
        Object addEducation = state.get('addEducation');
        if (addEducation != null) {
            new PRM_PersonEducationService().createDelegatedEducation(
                new PRM_PractitionerCreationTransformer().shapeEducation(addEducation, hcpId, cmId, personContactId)
            );
        }
        // Phase 10 — HCPNPI + BoardCert + Identifier
        new PRM_HCPNPIBoardCertService().createBundle(
            accountId, personContactId, hcpId, cmId,
            (String) state.get('hcpNpi'),
            (List<Map<String, Object>>) state.get('boardCerts'),
            (List<Map<String, Object>>) state.get('identifiers'),
            PRM_DateUtil.parse(state.get('effFrom')),
            PRM_DateUtil.parse(state.get('effTo'))
        );
        // Phase 11 — File attachments
        Object fileData = state.get('fileData');
        if (fileData != null) {
            new PRM_PractitionerCreationFileAttachmentService().uploadAll(
                (List<Map<String, Object>>) fileData, accountId, cmId
            );
        }
        // Phase 12 — ContactProfile + PersonLanguage
        if (Boolean.valueOf(state.get('isCpDetailsFound'))) {
            new PRM_ContactProfileService().create(
                (Map<String, Object>) state.get('screenCtx'),
                (Map<String, Object>) state.get('providerInformation'),
                (Map<String, Object>) state.get('pronouns')
            );
        }
        if (Boolean.valueOf(state.get('isPLanguageFound'))) {
            new PRM_PersonLanguageService().createBulk(
                new PRM_PersonLanguageTransformer().shape(
                    (Map<String, Object>) state.get('languageSpoken'),
                    (Map<String, Object>) state.get('screenCtx')
                )
            );
        }
    }
}
```

### 6.10 `PRM_PractitionerCreationCaseDataMgrService` (NEW — CDM stamper, extends `PRM_CaseDataMgrPatcher`)

> **Why we need it** — Both branches end with a CDM flag stamp (`PRMDRCreateCDMForPractitioner` — S10 standard, D22 delegated). The delegated D22 uses `advancedMerge` with a `matchingPath` join on `DRCreateGroupRecords:Account_1.Id`, which is fragile (depends on the upstream DR returning an `Account_1` key) and untestable in isolation. The flag set also differs between branches (standard sets 7 flags, delegated sets 12+) — having one DR bundle handle both via implicit branching is fragile.
>
> **How it helps** — Apex service with two explicit methods (`stampStandard(cmId, flags)`, `stampDelegated(cmId, flags)`) that compose `PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, branch, flagMap)`. The patcher does field-level merging on the existing CDM row (we already hold its ID from the create step in TX1), so no `advancedMerge` is needed and no upstream-key dependency exists.
>
> **Outcome** — One DML statement per submit for the flag stamp. Zero advancedMerge dependency. 100% unit-test coverage on the flag-mapping logic. The patcher method (`patchPractitionerCreation`) is added to the shared `PRM_CaseDataMgrPatcher` so PDA Review, Off Cycle, and Reinstate flows can compose it identically.
>
> **Replaces** — DR bundle `PRMDRCreateCDMForPractitioner` (both branches), plus the `advancedMergeMap` join logic in D22.

```apex
public with sharing class PRM_PractitionerCreationCaseDataMgrService {

    public Id createCDM(Id cmId) {
        PRM_CaseDataManager__c cdm = new PRM_CaseDataManager__c(PRM_CaseManager__c = cmId);
        PRM_DMLUtil.insertWithRollback(new List<SObject>{ cdm });
        return cdm.Id;
    }

    public void stampStandard(Id cmId, Map<String, Boolean> flags) {
        PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, 'IBC', flags);
    }

    public void stampDelegated(Id cmId, Map<String, Boolean> flags) {
        PRM_CaseDataMgrPatcher.patchPractitionerCreation(cmId, 'Delegated', flags);
    }
}
```

### 6.11 EXTEND `PRM_AccountUpsertHelper.createPractitionerAccount(...)` (Par Form)

> **Why we need it** — Both branches' `DRPAccountCaseCaseManagerCreation` (S3, D3, bundle `PRMDRCreateCaseCaseManagerAndAccount`) creates a PersonAccount with 22–30 input fields. Today, the field-mapping lives in a DataRaptor bundle (no Apex equivalent) and the two branches differ on ~8 fields (Delegated adds `PersonGenderIdentity`, `PRM_CredentialingStatus__c`, `PRM_ProviderRole__c`, `email`, `gender`, `Delegated=true` etc.). Par Form has a similar Account creation but without the Delegated flag — there is no shared Apex method today, so the two flows re-implement the same logic.
>
> **How it helps** — Extends `PRM_AccountUpsertHelper` (which already handles PersonAccount + Vendor Account upsert for Par Form) with `createPractitionerAccount(Map<String, Object> input, Boolean delegated, Map<String, String> titleCasedName)`. The method composes the existing `_buildPersonAccount` private logic with the new delegated-specific fields.
>
> **Outcome** — Single Apex method handles both branches. Par Form, Off Cycle Submit, and Reinstate Practitioner can all reuse it. ~30 lines net new in the existing helper.
>
> **Replaces** — The Account-portion of DR bundle `PRMDRCreateCaseCaseManagerAndAccount` for both branches (Case + IndividualApplication portions go to `PRM_CaseService.createPractitionerCreationCase`).

```apex
// EXTEND — in PRM_AccountUpsertHelper.cls
public static Id createPractitionerAccount(Map<String, Object> input,
                                            Boolean delegated,
                                            Map<String, String> name) {
    Map<String, Object> pd = (Map<String, Object>) input.get('PractionerDetails');
    Account a = _buildPersonAccount(pd, name);
    a.PRM_PractitionerCreationType__c = delegated ? 'Delegated Credentialing' : 'IBC Professional Staff';
    if (delegated) {
        a.PersonGenderIdentity = (String) pd.get('PersonGenderIdentity');
        a.PRM_CredentialingStatus__c = (String) pd.get('PRM_CredentialingStatus__c');
        a.PRM_ProviderRole__c = (String) pd.get('PRM_ProviderRole__c');
        a.PersonEmail = (String) pd.get('PersonEmail');
        a.PRM_Delegated__c = true;
    }
    PRM_DMLUtil.insertWithRollback(new List<SObject>{ a });
    return a.Id;
}
```

### 6.12 EXTEND `PRM_CaseService.createPractitionerCreationCase(...)` (Par Form)

> **Why we need it** — The Case + IndividualApplication portion of `DRPAccountCaseCaseManagerCreation` differs by branch: standard uses `Type="Network Management QC"`, RecordType `PRM`, Status `New`; delegated adds `PRM_IsRoundRobinLogic__c=true` and a different `PDMManualUpdateType`. The IndividualApplication metadata (RecordType `PDM Manual Change`, Category `Provider Data Management`, Stage `Network Management QC`) is identical across both.
>
> **How it helps** — Extends the existing `PRM_CaseService` with a flow-specific factory. Internally composes `_buildCase` and `_buildIndividualApplication` (already used by Par Form) with practitioner-creation-specific defaults and the `delegated` toggle.
>
> **Outcome** — Single Apex method for both branches. Returns `{CaseId, IndividualApplicationId, PersonContactId}` so the orchestrator gets all three FK targets in one call. ~25 lines net new.
>
> **Replaces** — The Case + IndividualApplication portions of DR bundle `PRMDRCreateCaseCaseManagerAndAccount`.

```apex
// EXTEND — in PRM_CaseService.cls
public static Map<String, Id> createPractitionerCreationCase(Id accountId,
                                                              Map<String, Object> input,
                                                              Boolean delegated) {
    Map<String, Object> caseDto = (Map<String, Object>) input.get('Case');
    Map<String, Object> iaDto = (Map<String, Object>) input.get('IndividualApplication');

    Case c = _buildCase(accountId, caseDto);
    if (delegated && caseDto.containsKey('PRM_IsRoundRobinLogic__c')) {
        c.PRM_IsRoundRobinLogic__c = (Boolean) caseDto.get('PRM_IsRoundRobinLogic__c');
    }
    PRM_DMLUtil.insertWithRollback(new List<SObject>{ c });

    IndividualApplication ia = _buildIndividualApplication(c.Id, iaDto);
    PRM_DMLUtil.insertWithRollback(new List<SObject>{ ia });

    return new Map<String, Id>{
        'CaseId' => c.Id,
        'IndividualApplicationId' => ia.Id,
        'PersonContactId' => [SELECT ContactId FROM Case WHERE Id = :c.Id LIMIT 1].ContactId
    };
}
```

### 6.13 EXTEND `PRM_TaxonomyService.createMultiTaxonomyWithPrimary(...)` (PDA Review)

> **Why we need it** — The delegated branch creates 1..N `HealthcareProviderTaxonomy` rows in `D11` (`DRPHCProviderHCProviderTaxonomyAndBusineessLicense`), with exactly one row flagged as primary (matched against `RecordsToUpdate.HCPTaxonomy.Name`). Today the merge + primary-mark logic spans D7 + D8 (`DRExtractTaxonomyData` + `DRTTaxonomyData`). `PRM_TaxonomyService` already exists (from PDA Review migration) for single-taxonomy create / update / effective-date, but has no method that accepts a list + a primary marker.
>
> **How it helps** — Adds one method to the existing `PRM_TaxonomyService`. The method validates that exactly one row has `IsPrimary=true`, stamps the parent HCP ID, and bulk inserts via `PRM_DMLUtil`.
>
> **Outcome** — D7 + D8 + the taxonomy portion of D11 collapse into one Apex method call. Shareable with Off Cycle Submit and PDA Review (both have similar multi-taxonomy create paths today). ~20 lines net new.
>
> **Replaces** — DR Turbo `PRMDRExtractTaxonomyData`, DR Transform `PRMDRTransDelegatedTaxonomyData`, and the taxonomy portion of bundle `PRMDRPHCPHCPTaxonomyAndBusineessLicense`.

```apex
// EXTEND — in PRM_TaxonomyService.cls
public static List<Id> createMultiTaxonomyWithPrimary(Id hcpId,
                                                      List<HealthcareProviderTaxonomy> rows,
                                                      String primaryTaxonomyName) {
    Integer primaryCount = 0;
    for (HealthcareProviderTaxonomy t : rows) {
        t.HealthcareProviderId = hcpId;
        t.IsPrimary = (t.Name == primaryTaxonomyName);
        if (t.IsPrimary) primaryCount++;
    }
    if (primaryCount != 1) {
        throw new IllegalArgumentException('Expected exactly 1 primary taxonomy, got ' + primaryCount);
    }
    PRM_DMLUtil.insertWithRollback(new List<SObject>(rows));
    return PRM_CollectionUtil.ids(rows);
}
```

---

## 7. Sequence Diagram (target state — worst-case Delegated submit)

```
OmniScript                Container IP        ServiceDispatcher      DelegatedService    Validator       AccountHelper / CaseService    HCProviderRecord    GroupAccount    BulkOperation   InfoCode    CDMService     AsyncEnqueueGuard   Queueable (TX2)   Database / Platform Event
   │                          │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │── IP_RecordCreation ─────►│                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │     %ContextPayload%      │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │── ServiceInvoker ──►│                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │   serviceName=      │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │   "PractitionerCre  │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │    ationDispatcher" │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │── route(type=         │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │   "Delegated…") ─────►│                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── validate ──────►│                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │── HCFs by      │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │   FacilityId ──┼──────────────────────────────►│                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │   SELECT…      │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │◄────────────────┤  HFs                          │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │◄──{valid:true}───┤                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                  │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── createPract   │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │   Account ──────┼─────────────────►│                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │   (delegated)   │                 │── INSERT Account ───────────►│                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │◄────────────────┼─────────────────┤  accountId                    │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── createCase ────┼─────────────────►│                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │── INSERT Case + IA ─────────►│                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │◄────────────────┼─────────────────┤  {caseId, iaId,              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │   personContactId}            │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── createCDM ─────┼─────────────────┼──────────────────────────────┼─────────────────►│                 │             │           │                 │                  │                  │
   │                          │                     │                       │◄────────────────┼─────────────────┼──────────────────────────────┤  cdmId           │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── mergeTaxon ────┼─────────────────┼──────────────────────────────┼──────────────────┤                 │             │           │                 │                  │                  │
   │                          │                     │                       │── mergeLicenses ─┼─────────────────┼──────────────────────────────┼──────────────────┤                 │             │           │                 │                  │                  │
   │                          │                     │                       │── createDeleg   │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │   atedBundle ──►│                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │   (HCP + Tax + │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │    License)    │                 │                              │── BulkOp.chain ─►│                 │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │── INSERT HCP    │                 │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │── INSERT Tax+L ►│                 │             │           │                 │                  │                  │
   │                          │                     │                       │◄────────────────┼─────────────────┼──────────────────────────────┤  {hcpId, ids}    │                 │             │           │                 │                  │                  │
   │                          │                     │                       │── createOrAtt   │                 │                              │                  │                 │             │           │                 │                  │                  │
   │                          │                     │                       │   ach Group ───►│                 │                              │                  │── selectorLkp ──┤             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │                  │  isExistingVend│             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │                  │── INSERT Vend  │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │                  │── INSERT NPI+ │             │           │                 │                  │                  │
   │                          │                     │                       │                 │                 │                              │                  │   TIN          │             │           │                 │                  │                  │
   │                          │                     │                       │◄────────────────┼─────────────────┼──────────────────────────────┼──────────────────┤  groupResult   │             │           │                 │                  │                  │
   │                          │                     │                       │── create InfoCo │                 │                              │                  │                 │── INSERT IFCs│           │                 │                  │                  │
   │                          │                     │                       │   deAssignments ─────────────────────────────────────────────────────────────────────►│             │           │                 │                  │                  │
   │                          │                     │                       │── stampDeleg    │                 │                              │                  │                 │             │── UPDATE CDM │                 │                  │                  │
   │                          │                     │                       │   ated (flags) ─────────────────────────────────────────────────────────────────────────────────────►│                 │                  │                  │
   │                          │                     │                       │                                                                                                                       │                 │                  │                  │
   │                          │                     │                       │ ── shouldDelegateAsync(rows > 80)? ──── yes ─────────────────────────────────────────────────────────────────────────►│── enqueueJob ─►│                  │                  │
   │                          │                     │                       │                                                                                                                                           │                  │                  │
   │                          │                     │                       │── PRM_ServiceResponse.success(CaseManagerId, FeatureConfigSetting, GroupRecordIds, ...)                                                  │                  │                  │
   │                          │                     │◄──────────────────────┤                                                                                                                                           │                  │                  │
   │                          │◄────────────────────┤                       │                                                                                                                                           │                  │                  │
   │◄──── ResponseAction ─────┤                                                                                                                                                                                          │                  │                  │
   │      (CaseManagerId, ...)│                                                                                                                                                                                          │                  │                  │
   │                                                                                                                                                                                                                      │                  │                  │
   │                                                                                                                                                                                                                      │── run() ────────►│                  │
   │                                                                                                                                                                                                                      │                  │── INSERT Educ ──►│
   │                                                                                                                                                                                                                      │                  │── INSERT HCPNPI▼ │
   │                                                                                                                                                                                                                      │                  │── INSERT Files ─►│
   │                                                                                                                                                                                                                      │                  │── INSERT CP+PL ─►│
   │                                                                                                                                                                                                                      │                  │── publish ──────►│ PRM_AsyncComplete__e
```

---

## 8. Governor / Performance Comparison

| Metric | Today (Delegated, worst case) | After (TX1) | After (TX2) | Today (Standard) | After (TX1, Standard) |
|---|---|---|---|---|---|
| SOQL queries | ~12 (incl. RecordType QUERY, HCF dates from Validator, FeatureConfig DR Turbo, Taxonomy DR Turbo, Group lookup, existing-identifier checks) | 4 (1× existing-HF dates, 1× FeatureConfig, 1× Taxonomy by Name, 1× Vendor by NPI+TIN) | 1 (existing rows for upsert disambiguation) | ~6 | 2 (RecordType cache miss = 0 after first call, 1× existing-license / 1× existing-identifier) |
| DML statements | ~13 (each DR Post = its own DML, plus 2 List Merge intermediate writes) | 8 (Account / Case+IA / CDM / HCP+Tax+License bulk / Vendor / GroupNPI+TIN / InfoCodes / CDM-update) | 4 (Education / HCPNPI+BoardCert+Identifier / Files / CP+PL) | ~9 | 4 (Account / Case+IA / CDM+HCP+Tax+License / HCPF pair + InfoCodes + CDM-update combined where possible) |
| DML rows | ~50 (delegated worst case from §2.3) | ~30 in TX1 | ~20 in TX2 | ~8 | ~8 |
| CPU (ms) — sync | ~2,500–4,000 (DR Post overhead, OmniStudio compile per element, RecordType QUERY each submit) | ~400–700 | ~300–500 (separate transaction) | ~1,200–2,000 | ~250–400 |
| Heap (KB) | ~6,000 (full nested payload retained across 23 elements + sub-IP) | ~1,800 (orchestrator + DTO + result map only) | ~1,200 | ~3,500 | ~900 |
| External callouts | 0 (this flow does no external integration) | 0 | 0 | 0 | 0 |

---

## 9. Migration Plan

### 9.1 Sequencing

This is the **6th flow** in the global migration sequence:

1. ✅ **Par Form (Submit)** — `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`
2. ✅ **PDA Review (Initial Cred)** — `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md`
3. ✅ **Off Cycle Submit** — `PNM_OffCycle_Process_Apex_Service_Architecture.md`
4. ✅ **Off Cycle PDA Review** — `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md`
5. ✅ **Reinstate (Practitioner / PracticeLoc / Vendor)** — `PNM_Reinstate_Apex_Service_Architecture.md`
6. ▶ **Practitioner Creation (THIS doc — IBC + Delegated)** — `PNM_PractitionerCreation_Apex_Service_Architecture.md`
7. ☐ **Delegated Practitioner Address Form** (uses `PRM_VerifyPractitionerDetailsForDelegated_Procedure_1` 85+ elt — heaviest IP in the whole codebase)
8. ☐ **Delegated Practitioner Review Screen** (uses `PRM_CreateDelegatedHFNRecords_Procedure_3` 25 elt + `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_2` 13 elt)

Reusable services available from prior migrations: **all of §5.1–§5.6 of `prompt.md`**. This flow extends 5 of them (per §4.5) and introduces 16 new services. The flow does **not** require any new framework primitives — every cross-cutting pattern (BulkOperation, AsyncEnqueueGuard, CaseDataMgrPatcher) was added by prior migrations.

### 9.2 Components to retire

**Integration Procedures** (shrunk to 3-element thin wrappers, not deleted — keeps OmniStudio Studio happy):
- `PRM_PractitionerCreationContainer_Procedure_5` (5 → 3 elt)
- `PRM_PractitionerCreation_Procedure_3` (11 → 3 elt)
- `PRM_DelegatedPractitionerCreation_Procedure_6` (23 → 3 elt)
- `PRM_DelegatedCreateProviderScreenRecords_Procedure_1` (4 → 3 elt)

**DataRaptor bundles** (retired after cut-over):
- `PRMDRCreateCaseCaseManagerAndAccount`
- `PRMDRPCDMCaseManagerLink`
- `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (standard)
- `PRMDRPHCPHCPTaxonomyAndBusineessLicense` (delegated)
- `PRMDRPCreateInfoCodeAssignments`
- `PRMDRPPractionerPracticeLocations`
- `PRMDRCreateCDMForPractitioner`
- `PRMPostGroupPractitionerCreation`
- `PRMDRExtractTaxonomyData`
- `PRMDRTransDelegatedTaxonomyData`
- `PRMDRTransformDelegatedBusinessLicense`
- `PRMDRTransformAddEducation`
- `PRMDRPCreateEducation`
- `PRMDRPHCPNPIBoardCretIdentifier`
- `PRMDRCreateIdentiferAndDocument`
- `PRMDRCreateContactProfileRecords`
- `PRMDRTransformProviderInformationData`
- `PRMDRCreatePersonLanguage`

**DataRaptor Turbo / Read-side bundles** (folded into selectors):
- `PRMGetFeatureConfigSetting`

**Remote Action methods** (retired):
- `PRM_OmniUtils.titleCase` (used by all 5 prior flows too — coordinate retirement)
- `PRM_OmniUtils.convertToListSobjects` (same)
- `PRM_OmniUtils.logTryCatchException` (same)

**Existing Apex** (preserved verbatim — STANDARDISE):
- `PRM_PractitionerCreationValidator` (Callable — keep)
- `PRM_PractitionerCreationHelper` (LWC controller — keep)
- `PRM_PractitionerCreationUtility` (Callable for `getGroupData` — keep)

### 9.3 Test Strategy

| Layer | Tests |
|---|---|
| Dispatcher | `PRM_PractitionerCreationDispatcherServiceTest` — routes IBC vs Delegated vs unknown; verifies `PRM_TransactionContext.start` + `PRM_ErrorLogger` invocation on exceptions |
| IBC Service | `PRM_PractitionerCreationIBCServiceTest` — sample-payload-driven; verifies row counts per §2.1, HCPF pair atomicity, RecordType lookups cached |
| Delegated Service | `PRM_PractitionerCreationDelegatedServiceTest` — sample-payload-driven; verifies validator-failure short-circuits, multi-taxonomy with primary, DEA+SBRD license merge, async-threshold delegation, sync-fallback when async slot exhausted |
| Sub-IP Service | `PRM_PractitionerCreationDelegatedSubIPServiceTest` — verifies IsCPDetailsFound / IsPLanguageFound gates |
| HCProvider bundle | `PRM_HCProviderRecordServiceTest` — verifies savepoint rollback when Taxonomy or License insert fails |
| Group | `PRM_GroupAccountServiceTest` — verifies new-vs-existing-vendor branch via mocked selector |
| HCPF Pair | `PRM_PractitionerPracticeAffiliationServiceTest` — verifies atomic 2-row insert + RecordType caching |
| HCPNPI Bundle | `PRM_HCPNPIBoardCertServiceTest` — verifies the sentinel-hack removal: empty identifier list does NOT silently drop rows |
| Business License | `PRM_BusinessLicenseServiceTest` — DEA / CDS / SBRD reshape + merge by `PractitionerLicenseNumber`, with and without `allowNulls` |
| Transformer | `PRM_PractitionerCreationTransformerTest` — taxonomies primary-flagging, license reshape, education FK stamping |
| CDM stamper | `PRM_PractitionerCreationCaseDataMgrServiceTest` — standard 7-flag set vs delegated 12-flag set, no advancedMerge dependency |
| Async Job | `PRM_PractitionerCreationAsyncJobTest` — runs as `Test.startTest()` + `Test.stopTest()` to flush the queue; verifies `PRM_AsyncComplete__e` published |
| Validator preservation | `PRM_PractitionerCreationValidatorTest` (existing — unchanged) — verifies the inline-vs-Remote-Action invocation paths produce identical results |
| Helper preservation | `PRM_PractitionerCreationHelperTest` (existing — unchanged) |
| Dual-write parity | `PRM_PractitionerCreationDualWriteTest` — runs both the legacy DR-Post path and the new Apex path against the same sample payloads (`PRM_PractitionerCreation_SampleInput.json`, `PRM_DelegatedPractitionerCreation_SampleInput.json`), diffs the resulting record-set per SObject family, and asserts identical row counts + field values |
| Performance smoke | `PRM_PractitionerCreationPerfTest` — runs against a 50-row Delegated payload; asserts TX1 < 800 ms, TX2 < 60 s |

### 9.4 Feature Flag Rollout

`PRM_FeatureConfig__mdt` entries:

| Developer Name | Type | Default | Purpose |
|---|---|---|---|
| `PractitionerCreation_UseApexService` | Boolean | `false` | Master cut-over flag. When `true`, OS dispatches to the new Apex service. When `false`, falls back to the legacy DR-Post path (kept as fallback for 1 sprint after cut-over) |
| `PractitionerCreation_AsyncThresholdRows` | Integer | `80` | When estimated payload row count exceeds this, TX2 fan-out fires |
| `PractitionerCreation_ValidatorMode` | Picklist | `Inline` | `Inline` = Apex-inline call (new). `RemoteAction` = legacy hop (fallback during cut-over) |
| `PractitionerCreation_StampOnTx2Complete` | Boolean | `false` | When `true`, the CDM flag stamp moves to TX2 (after async children commit); when `false` (default), TX1 stamps in phase 8 |

Rollout sequence:
1. Deploy all new Apex + extension methods with `PractitionerCreation_UseApexService = false`. No functional change.
2. Deploy thin IP wrappers (3-element shape) **next to** the legacy IPs (different `UniqueName` — `_Procedure_8` for example).
3. Update the OmniScript IP Action element to call the new IP. Toggle `PractitionerCreation_UseApexService = true` per sandbox → UAT → prod sandbox → prod.
4. After 1 sprint clean, retire the legacy IP versions + DR bundles + Remote Action methods listed in §9.2.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Coordination with prior migrations on shared utils** — `PRM_OmniUtils.titleCase`, `PRM_OmniUtils.convertToListSobjects`, `PRM_OmniUtils.logTryCatchException` are referenced by Par Form, PDA Review, Off Cycle, Reinstate, and this flow. They cannot be retired until every flow's cut-over completes | Track in a shared retirement spreadsheet (`requirements/Enhancements/utility-retirement.md`). Defer the actual deletion to a final cleanup user story after all 6 flows are toggled on. |
| **DEA / CDS license merge correctness** — the legacy List Merge has subtle behaviour (`allowMergeNulls=true` means a null from the SBRD list does not overwrite a non-null in the DEA/CDS list). Misimplementing this drops real license rows | Test-first: build `PRM_BusinessLicenseServiceTest` with `PRM_DelegatedPractitionerCreation_SampleInput.json`-derived fixtures covering all 4 quadrants (SBRD-only, DEA/CDS-only, both with same license-number, both with different license-numbers). Dual-write parity test (§9.3) asserts identical `Identifier__c` rows across legacy + new |
| **HCProvider bundle atomicity** — today's DR Post pretends to be atomic but is not; the new service IS atomic via savepoint. If callers expect "partial HCP without taxonomy", the new behaviour breaks them | Audit downstream consumers (specifically PDA Review's `PRM_HCFNetworkSelector` and Off Cycle PDA's `PRM_OffCyclePDAHFNTransformer`) for queries that assume partial HCP. None expected — confirm in code review |
| **CDM flag-stamp race condition** — today the OS advances to the next screen as soon as TX1 returns; downstream queries (LWC tiles on the next screen) read the CDM. If the new flow defers the flag stamp to TX2 (`PractitionerCreation_StampOnTx2Complete=true`), the next screen renders empty | Default the flag (`StampOnTx2Complete=false`) so TX1 stamps inline. Document the tradeoff for future flows that want async-only stamping (Reinstate does this; this flow does not) |
| **Async slot exhaustion in TX2** — `PRM_AsyncEnqueueGuard` falls back to inline execution; this stretches TX1 past 800 ms on the worst case | Add a Splunk dashboard query for `PRM_AsyncEnqueueGuard.fallbackInvoked=true` events. Alert at > 0.5% of submits/day. If alert fires, investigate org-wide async queue saturation rather than rolling back this flow |
| **Feature-flag isolation per environment** — the two `_AsyncThresholdRows` and `_StampOnTx2Complete` flags must be independently set per sandbox / UAT / prod | Use `PRM_FeatureConfig.getSetting(...)` (already supports per-org defaults) instead of hardcoding. Document the per-env values in `requirements/Enhancements/feature-flag-matrix.md` |
| **Existing Apex preservation** — `PRM_PractitionerCreationValidator` is brand-new (May 2026) and was recently wired into the Delegated IP at seq=2.5. The new dispatch must call it via the same Callable contract, not re-implement | Code review checklist item: confirm `PRM_PractitionerCreationDelegatedService.processSync()` calls `new PRM_PractitionerCreationValidator().call('validate', args)` and asserts `result.get('valid') == true`. Existing test class (`PRM_PractitionerCreationValidatorTest`) MUST still pass unchanged |
| **OmniScript JSON contract preservation** — the OS sends `RecordsToUpdate.PractionerDetails.SourceIdentifier`, `RecordsToUpdate.HCPNPI`, etc. and expects exactly those response keys back. Any drift breaks the OS | Treat the response shape from `ResponseAction` (D23) as the contract. Snapshot the `ResponseAction.additionalOutput` map and assert byte-identical output in `PRM_PractitionerCreationDualWriteTest` |
| **Picklist semantics for `PractitionerCreationType`** — values are `"IBC Professional Staff"` and `"Delegated Credentialing"` (exact, case-sensitive, no leading/trailing whitespace) | Dispatcher uses `==` comparison, not `LIKE` or `equalsIgnoreCase`. Fail loudly on any unknown value (`PRM_ServiceResponse.failure("Unknown PractitionerCreationType: " + value)`) so misconfigurations surface during dual-write rather than silently routing to the wrong branch |
| **Latent `PRM_PractitionerCreationHelper` bug** (line 184: `PRM_AddressLine1__c` referenced twice in `FullAddress` concat instead of `PRM_AddressLine2__c`) | Documented in §1.4 and §10. Do not fix as part of this migration — file as a separate user story to keep the migration's blast radius small |
| **Inactive `IP_CreatePractitionerPracticeLocation` element (D20)** — currently dead code; could be reactivated later, dropping ~50 more rows into the chain | The new service has a `PRM_FeatureConfig__mdt.PractitionerCreation_IncludePracticeLocationFanout` flag (default `false`). When reactivated, set the flag, and the new `PRM_PractitionerCreationDelegatedService` composes `PRM_PractitionerPracticeAffiliationService.createBulkForLocations(locations)` inside TX2 |

---

## 11. Acceptance Criteria

1. All four IPs (`PRM_PractitionerCreationContainer`, `PRM_PractitionerCreation`, `PRM_DelegatedPractitionerCreation`, `PRM_DelegatedCreateProviderScreenRecords`) shrink to **3 elements each** (SV → IP_Action → Response).
2. Dual-write test passes: for the standard `PRM_PractitionerCreation_SampleInput.json` (1 PersonAccount, 1 Case, 1 IA, 1 CDM, 1 HCP, 1 Taxonomy, 1 BusinessLicense, 1 InfoCodeAssignment, 2 HCPF, 1 CDM-update) and the delegated `PRM_DelegatedPractitionerCreation_SampleInput.json` (~50 DML rows), the new Apex path produces a **bit-identical record set** vs. the legacy DR-Post path.
3. **Sync request < 800 ms** for the worst-case Delegated submit (~50 DML rows) measured in QA sandbox.
4. **Sync request < 500 ms** for the standard IBC Professional Staff submit (~8 DML rows).
5. **Async TX2 < 60 s** for the largest realistic Delegated submit (200 child rows).
6. **Zero changes to OmniScript JSON contract**: every output key in today's `ResponseAction` (`CaseManagerId`, `FeatureConfigSetting`, `GroupRecordIds`, `PractitionerEffectiveDate`, `PractitionerRole`, `PractitionerScreenRecordIds`, `ProviderInformationAffirmingCategory`, `locationsToUpsert`) is produced byte-identically by `PRM_ServiceResponse.data`.
7. **Apex test coverage ≥ 90%** on new classes (orchestrators, domain services, transformer, selector), **≥ 80%** on extension methods. `PRM_PractitionerCreationValidatorTest` and `PRM_PractitionerCreationHelperTest` (existing) pass without modification.
8. **`PRM_FeatureConfig__mdt.PractitionerCreation_UseApexService = false`** cleanly reverts the flow to the legacy DR-Post path with no data loss (validated via end-to-end manual test in QA sandbox).
9. **`PRM_PractitionerCreationValidator` invocation path preserved**: legacy Remote Action invocation and new inline Apex invocation produce identical `{valid, errors, errorsByCategory, errorCount, combinedMessage}` outputs on all 6 fixture payloads from `PRM_PractitionerCreationValidatorTest`.
10. **HCProvider bundle atomicity**: chaos test that injects a savepoint failure on `HealthcareProviderTaxonomy.insert()` confirms the parent HealthcareProvider is rolled back (no orphan).
11. **Multi-taxonomy primary-mark invariant**: dual-write tests assert exactly 1 taxonomy row has `IsPrimary=true` per submit; service throws `IllegalArgumentException` if the payload has 0 or > 1 primary marks (no silent acceptance).

---

## 12. Net new vs reused — one final view

| Category | Reused (LoC) | Extended (LoC net new) | New (LoC) | Standardise (LoC kept) | Total |
|---|---|---|---|---|---|
| Framework + Cross-cutting | ~3,500 (already shipped) | +40 (`PRM_CaseDataMgrPatcher.patchPractitionerCreation`) | 0 | 0 | 3,540 |
| Selectors | ~1,200 (already shipped) | 0 | ~150 (`PRM_PractitionerCreationSelector`) | 0 | 1,350 |
| Transformers | ~250 (`PRM_ParFormDataTransformer` partial reuse) | 0 | ~280 (`PRM_PractitionerCreationTransformer` + `PRM_PersonLanguageTransformer`) | 0 | 530 |
| Domain / Orchestration | ~1,400 (`PRM_AccountUpsertHelper`, `PRM_CaseService`, `PRM_TaxonomyService`, `PRM_IdentifierService`, `PRM_PersonEducationService` already shipped) | +180 (5 extension methods) | ~1,650 (13 new services + Queueable) | ~580 (3 existing Apex preserved) | 3,810 |
| **Totals** | **~6,350** | **+220** | **~2,080** | **~580** | **~9,230** |

Net new code for this flow: ~2,080 LoC across 16 new classes. Total LoC delta (incl. extension methods): ~2,300. Compared to retiring **18 DataRaptor bundles + 4 Remote Action methods + ~62 IP elements + 4 IP definitions**, the new code is well under the legacy footprint.

---

## 13. Cross-references

- **Framework** — `PNM_Apex_Service_Architecture.md` (§14 Cross-cutting Framework Patterns for `PRM_BulkOperation`, `PRM_AsyncEnqueueGuard`, `PRM_CaseDataMgrPatcher`)
- **Par Form** — `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` (extension targets: `PRM_AccountUpsertHelper`, `PRM_CaseService`, `PRM_IdentifierService`, `PRM_PersonEducationService`)
- **PDA Review (Initial Cred)** — `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` (extension target: `PRM_TaxonomyService.createMultiTaxonomyWithPrimary`)
- **Off Cycle Submit** — `PNM_OffCycle_Process_Apex_Service_Architecture.md` (`PRM_OffCycleGroupService` — sibling of the new `PRM_GroupAccountService`; coordinate as a future refactor to merge the two)
- **Off Cycle PDA Review** — `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md` (HCFN reshape patterns — similar to the `PRM_PractitionerCreationTransformer.mergeTaxonomies` pattern used here)
- **Reinstate (Practitioner / PracticeLoc / Vendor)** — `PNM_Reinstate_Apex_Service_Architecture.md` (`PRM_ReinstateRowPartitioner` — analogue of the IBC vs Delegated branching in the dispatcher)
- **Authoring methodology** — `prompt.md`
- **Interactive mind map** — `PNM_Modernization_MindMap.html` (this flow appears as the `practitioner-creation` tab)
- **Future migrations directly chained from this flow** —
  - Delegated Practitioner Address Form (`PRM_DelegatedPractitionerAddressForm_English_9` OS, `PRM_VerifyPractitionerDetailsForDelegated_Procedure_1` 85+ elt IP, `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_2` 13 elt sub-IP)
  - Delegated Practitioner Review Screen (`PRM_DelegatedPractitionerReviewScreen_English_5` OS, `PRM_CreateDelegatedHFNRecords_Procedure_3` 25 elt sub-IP, `PRM_ValidateDelegatedInfoCodeSelection_Procedure_1` 7 elt validation, `PRM_GetDelegatedGroup_Procedure_1` 3 elt form-load)

