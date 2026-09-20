# Epic E — Practitioner Creation Services (Implementation Guide) · Part 1 (E1–E8)

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.6) · `PRM_Implementation_Plan.md` (§8 EPIC E)
> **Goal:** re-implement the Practitioner Creation record-creation logic (currently OmniStudio IPs + DataRaptors) as layered Apex services. This part covers **E1–E8**; E9–E17 follow in Part 2.
> **Estimate (E1–E8):** ~9.0 engineer-days (E4 merged into E2) · **Depends on:** EPIC A (objects), EPIC B (`PRM_ServiceBase`, `PRM_FormSubUtility`), EPIC D (selectors). · **Blocks:** EPIC F (orchestrator).

> **Grounding:** every field map, formula, and record-type below was extracted from the **active** (`isActive=true`) OmniStudio metadata in this repo — not invented. Source artifacts are cited per service. Where the active metadata contradicts the plan, it is flagged in the **Clarification Log (§E.CL)**.

---

## E0. Entry path & how the legacy flow is structured (grounded)

### Legacy DR → service map (active DRs only)


| Service                                                                   | Legacy active DR(s)                                                                                                                                                                                                                  | DR type                          | Objects the DR writes                                                                 |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------------------------------------- |
| **E1** `PRM_CaseService`                                                  | `PRMDRCreateCaseCaseManagerAndAccount`                                                                                                                                                                                               | Load                             | Account, Case, IndividualApplication                                                  |
| **E2** `PRM_PractitionerService`                                          | Delg: `PRMDRPHCPHCPTaxonomyAndBusineessLicense` (HCP+Taxonomy) + `PRMDRPHCPNPIBoardCretIdentifier` (NPI+Identifier) + `PRMDRCreateIdentiferAndDocument`; IBC: `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (HCP+Taxonomy) | Load                             | HealthcareProvider, HealthcareProviderNpi, Identifier, **HealthcareProviderTaxonomy** |
| **E3** `PRM_GroupService`                                                 | `PRMPostGroupPractitionerCreation` (via `PRM_DelegatedPractitionerCreation` v7 element `DRCreateGroupRecords`)                                                                                                                       | Load                             | Account(Vendor), Identifier, HealthcareProviderNpi, HealthcareProvider                |
| **E4** `PRM_TaxonomyService` *(folded into E2 for Practitioner Creation)* | `PRMDRExtractTaxonomyData` + `PRMDRTransDelegatedTaxonomyData` (transform) + Taxonomy part of the fused HCP DR                                                                                                                       | Turbo Extract / Transform / Load | HealthcareProviderTaxonomy                                                            |
| **E5** `PRM_LicenseService`                                               | `PRMDRTransformDelegatedBusinessLicense` (transform) + BusinessLicense part of the fused HCP DR                                                                                                                                      | Transform / Load                 | BusinessLicense                                                                       |
| **E6** `PRM_EducationService`                                             | `PRMDRTransformAddEducation` (transform) + `PRMDRPCreateEducation` (Load)                                                                                                                                                            | Transform / Load                 | PersonEducation                                                                       |
| **E7** `PRM_BoardCertificationService`                                    | `PRMDRPHCPNPIBoardCretIdentifier` (BoardCertification part)                                                                                                                                                                          | Load                             | BoardCertification                                                                    |
| **E8** `PRM_InfoCodeService`                                              | `PRMDRPCreateInfoCodeAssignments` (Load)                                                                                                                                                                                             | Load                             | PRM_InfoCodeAssignment__c                                                             |


> **DR "fusion" note:** `PRMDRPHCP…TaxonomyAndBusineessLicense` writes **HealthcareProvider + HealthcareProviderTaxonomy + BusinessLicense** in one DR, and `PRMDRPHCPNPIBoardCretIdentifier` writes **HealthcareProviderNpi + BoardCertification + Identifier** in one DR. In the new design those columns are split across E2/E4/E5/E7; the field maps below are partitioned accordingly.

---

## E0.1 Conventions (apply to every service)

- **Signature:** `public with sharing class PRM_XxxService extends PRM_ServiceBase { public override Map<String,Object> execute(Map<String,Object> params) { ... } }` (EPIC B contract).
- **Each service performs its own DML.** It builds records in memory, then does the DML itself in FK/dependency order (including any back-link updates), and returns the created Ids in the response map for downstream services. Parent Ids needed from earlier services arrive via `params`.
- **One bulk DML per object type.** No DML in loops.
- **Reads** go through the EPIC D selectors (`PRM_*Selector`), never inline SOQL in a loop.
- **Name normalization:** `PRM_FormSubUtility.NameNormalize(...)` on person names (replaces legacy `PRM_OmniUtils.titleCase` / `RA_TitleCase`).
- **Record types:** resolve by **DeveloperName via cached describe** (see §E0.2) — do **not** port the legacy ordinal `recordTypeList|N` indexing.
- `**params` keys** mirror the OmniScript payload keys (see `PRM_Service_JSON_Contracts.md`); each service documents the inputs it consumes and the Ids it returns.

### E0.2 Formula-translation patterns (legacy DR formula → Apex)


| Legacy DR formula idiom                                                          | Apex equivalent                                                                                                                         |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `QUERY("SELECT Id FROM RecordType WHERE DeveloperName='X' AND SobjectType='Y'")` | `Schema.SObjectType.Y.getRecordTypeInfosByDeveloperName().get('X').getRecordTypeId()` — wrap in a cached helper; **no SOQL per record** |
| `NOW()` / `TODAY()`                                                              | `System.now()` / `Date.today()`                                                                                                         |
| `IF(cond, a, b)` (nested)                                                        | Apex `if`/ternary                                                                                                                       |
| `ISBLANK(%x%)` / `ISNOTBLANK(%x%)`                                               | `String.isBlank(x)` / `String.isNotBlank(x)`                                                                                            |
| `CONCAT(a,"-",b)`                                                                | `a + '-' + b`                                                                                                                           |
| `%x% == "literal"`                                                               | `String` equals comparison                                                                                                              |
| `list                                                                            | N` (ordinal index)                                                                                                                      |


### E0.3 Record types referenced by E1–E3 (from DR `QUERY` formulas)


| SObject               | DeveloperName                          | Used by                 |
| --------------------- | -------------------------------------- | ----------------------- |
| Account               | `PRM_Practitioner`                     | E1 (`accRecordTypeId`)  |
| Account               | `PRM_Vendor`                           | E3 (group/vendor)       |
| Case                  | `PRM_PRM`                              | E1 (`caseRecordTypeId`) |
| IndividualApplication | `PRM_PractitionerParticipationRequest` | E1 (practitioner flow)  |
| IndividualApplication | `PRM_PDMManualChange`                  | E1 (PDM flow)           |
| IndividualApplication | `PRM_PNC`                              | E1 (`PNCFlag` true)     |
| Identifier            | `PRM_Practitioner`                     | E2                      |
| Identifier            | `PRM_Vendor`                           | E3                      |
| Identifier            | `PRM_Document`                         | E9 (file — Part 2)      |


> Build a small cached `PRM_RecordTypeUtil.id(SObjectType, devName)` (home TBD — see TDD CL‑13) to replace every `QUERY(...RecordType...)` formula. This removes 4+ SOQL/describe round-trips per submission.

---

## E1 · `PRM_CaseService` — *2.0 d* · Branch: BOTH

**Legacy:** `PRMDRCreateCaseCaseManagerAndAccount` (Load). **Writes:** `Account` (Practitioner), `Case`, `IndividualApplication` (= the "Case Manager" record).

**Method signature** — `extends PRM_ServiceBase`; input and output are both `Map<String,Object>`. The input map carries `**flow`** (routing/context — a top-level map element) and `**jsonInput**` (the business payload as a JSON string). All formula fields (record types, `caseType`, `CredentialingStatusVal`, gender, `AppliedDate`) are computed **inside the service**, not supplied.

```apex
public with sharing class PRM_CaseService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');         // separate map element, e.g. 'PractitionerCreation'
        String jsonInput = (String) params.get('jsonInput');    // business payload (JSON string)
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        Map<String, Object> caseManagerInfo  = (Map<String, Object>) input.get('caseManagerInfo');
        Map<String, Object> practitionerInfo = (Map<String, Object>) input.get('practitionerInfo');

        // 1. compute formula fields in Apex (see "Formulas → Apex" below)
        //    recordTypeIds (Account/Case/IA), caseType, credentialingStatus, gender, appliedDate ...
        // 2. build Account, Case, IndividualApplication in memory from the two nodes
        // 3. service performs the DML in FK order + back-link updates (see "DML / order")

        response = new Map<String, Object>();                   // protected base field
        // response.put('practitionerAccountId', ...); caseId; caseManagerId; records to insert
        return response;
    }
}
```

**Expected `jsonInput` format** — two nodes only: `**caseManagerInfo`** (Case + IndividualApplication fields) and `**practitionerInfo**` (Account/practitioner fields). `flow` is **not** in the JSON — it is a separate element of the `params` map. Formula-derived fields are computed in the service and are **not** supplied.

```json
{
  "caseManagerInfo": {
    "FormType": "",
    "ApplicationType": "",
    "Status": "",
    "AppliedDate": "",
    "Category": "",
    "PDMManualUpdateType": "",
    "CorporateReceiptDate": "",
    "FHnaticCaseNumber": "",
    "FormCompletedBy": "",
    "Stage": "",
    "PNCFlag": false,
    "HasCapSites": false,
    "processingStatus": "",
    "flowType": "PractitionerCreation",
    "isRoundRobinLogic": false
  },
  "practitionerInfo": {
    "practitionerCreationType": "IBC Professional Staff",
    "npi": "1234567893",
    "firstName": "Jane",
    "lastName": "Smith",
    "middleName": "A",
    "suffix": "MD",
    "dob": "",
    "title": "Attending Physician",
    "providerRole": "",
    "email": "",
    "gender": "",
    "accountType": "",
    "isActive": false,
    "effectiveFrom": "",
    "effectiveTo": "",
    "delegated": "",
    "id": ""
  }
}
```

> **Service-computed (do NOT send):** `Account.RecordTypeId` / `Case.RecordTypeId` / `IndividualApplication.RecordTypeId` (resolved by DeveloperName), `Case.Type` (`caseType`), `Account.PRM_CredentialingStatus__c` (`CredentialingStatusVal` from `practitionerInfo.practitionerCreationType`), `Account.PersonGenderIdentity` / `HealthCloudGA__Gender__pc` (from `practitionerInfo.gender`), `IndividualApplication.AppliedDate` (defaults to `NOW()` if blank). FK fields (`Case.AccountId`, `Case.PRM_CaseManager__c`, `IndividualApplication.AccountId`/`ApplicationCaseId`, `Account.PRM_CaseManager__c`) are set **in-service** across the insert + back-link steps.

> **Field coverage check (every JSON attribute maps to a Field-map row):** `caseManagerInfo.*` → IndividualApplication + Case fields; `practitionerInfo.*` → Account fields; `flow` → `params` element (used by `caseType`/RT/gender formulas as `flowType` too). `title` is the UI label for `providerRole` → `Account.PRM_ProviderRole__c`; `id` = existing practitioner Account (existing-NPI path).

**Field map (grounded):**


| Target                | Field                                                                                                                                            | Source                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Account               | `RecordTypeId`                                                                                                                                   | ⟲ formula (RT `PRM_Practitioner`)                                                                         |
| Account               | `FirstName` / `MiddleName` / `LastName` / `Suffix`                                                                                               | `practitionerInfo.firstName/middleName/lastName/suffix` (→ `NameNormalize`)                               |
| Account               | `PersonEmail`                                                                                                                                    | `practitionerInfo.email`                                                                                  |
| Account               | `PersonBirthdate`                                                                                                                                | `practitionerInfo.dob`                                                                                    |
| Account               | `PersonGenderIdentity`                                                                                                                           | ⟲ formula (from `practitionerInfo.gender`)                                                                |
| Account               | `HealthCloudGA__Gender__pc`                                                                                                                      | ⟲ formula `PersonGenderIdentityPc` (from `practitionerInfo.gender`)                                       |
| Account               | `HealthCloudGA__SourceSystemId__c`                                                                                                               | `practitionerInfo.npi`                                                                                    |
| Account               | `PRM_ProviderRole__c`                                                                                                                            | `practitionerInfo.providerRole` (UI: `title`)                                                             |
| Account               | `PRM_CredentialingStatus__c`                                                                                                                     | ⟲ formula `CredentialingStatusVal` (from `practitionerInfo.practitionerCreationType`)                     |
| Account               | `PRM_PNC__c`                                                                                                                                     | `caseManagerInfo.PNCFlag`                                                                                 |
| Account               | `Type`                                                                                                                                           | `practitionerInfo.accountType`                                                                            |
| Account               | `IsActive`                                                                                                                                       | `practitionerInfo.isActive`                                                                               |
| Account               | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c`                                                                                                    | `practitionerInfo.effectiveFrom` / `effectiveTo`                                                          |
| Account               | `PRM_DelegatedOnly__c`                                                                                                                           | `practitionerInfo.delegated`                                                                              |
| Account               | `Id`                                                                                                                                             | `practitionerInfo.id` (existing-NPI path)                                                                 |
| Case                  | `RecordTypeId`                                                                                                                                   | ⟲ formula (RT `PRM_PRM`)                                                                                  |
| Case                  | `Type`                                                                                                                                           | ⟲ formula `caseType` (from `flow`/`caseManagerInfo.flowType`, `PNCFlag`)                                  |
| Case                  | `PRM_IsRoundRobinLogic__c`                                                                                                                       | `caseManagerInfo.isRoundRobinLogic`                                                                       |
| Case                  | `AccountId`                                                                                                                                      | ← Account.Id (FK, in-service)                                                                             |
| IndividualApplication | `RecordTypeId`                                                                                                                                   | ⟲ formula `individualAppRecordTypeId`                                                                     |
| IndividualApplication | `AccountId` / `ApplicationCaseId`                                                                                                                | ← Account.Id / Case.Id (FK)                                                                               |
| IndividualApplication | `AppliedDate`                                                                                                                                    | ⟲ formula `NOW()` (or `caseManagerInfo.AppliedDate` if supplied)                                          |
| IndividualApplication | `Status` / `Stage` / `Category` / `ApplicationType`                                                                                              | `caseManagerInfo.Status/Stage/Category/ApplicationType`                                                   |
| IndividualApplication | `PRM_FormCompletedBy__c` / `PRM_FormType__c` / `PRM_PNC__c`                                                                                      | `caseManagerInfo.FormCompletedBy/FormType/PNCFlag`                                                        |
| IndividualApplication | `PRM_CorporateReceiptDate__c` / `PRM_FHNaticCaseNumber__c` / `PRM_DisplayCapSites__c` / `PRM_ProcessingStatus__c` / `PRM_PDMManualUpdateType__c` | `caseManagerInfo.CorporateReceiptDate/FHnaticCaseNumber/HasCapSites/processingStatus/PDMManualUpdateType` |


**Formulas → Apex:**

- `CredentialingStatusVal` = `IF(PractitionerCreationType=="IBC Professional Staff",'Credentialed', IF(=="Delegated Credentialing", null, 'Credentialing In Progress'))`
→ `String cs = type=='IBC Professional Staff' ? 'Credentialed' : (type=='Delegated Credentialing' ? null : 'Credentialing In Progress');`
- `caseType` = `IF(ISNOTBLANK(FlowType) && FlowType=="PractitionerCreation", "Network Management QC", IF(PNCFlag, "PNC", "Application Review"))`.
- `PersonGenderIdentity` = `IF(PractitionerCreation flow, NULL, map Male→"M", Female→"F", "Prefer not to share"→same, else "U")`. `PersonGenderIdentityPc` = same but Male→"Male", Female→"Female", else "Other".
- `AppliedDate` = `System.now()`.
- **Record types** (replace the `recordTypeList` QUERY + ordinal `|N`): resolve `PRM_Practitioner`(Account), `PRM_PRM`(Case), and IA RT by rule:
  - `individualAppRecordTypeId = PNCFlag ? RT(IA,'PRM_PNC') : individualAppRecordTypeIdPrac`
  - `individualAppRecordTypeIdPrac = (FlowType=='PractitionerCreation') ? RT(IA,'PRM_PDMManualChange') : RT(IA,'PRM_PractitionerParticipationRequest')`
    > ⚠ The legacy ordinal mapping (`recordTypeList|3/|4`) is fragile; the rule above reflects the QUERY's `ORDER BY SobjectType ASC, DeveloperName DESC`. **Verify the IA RT for the Practitioner-creation flow during build** (CL‑E2).

**DML / order (circular FK — insert then back-link):**

1. **Insert `Account`** (from `practitionerInfo`).
2. **Insert `IndividualApplication`** — FK `AccountId` → Account.Id.
3. **Insert `Case`** — FK `PRM_CaseManager__c` → IndividualApplication.Id.
4. **Update `IndividualApplication`** with the latest case — `ApplicationCaseId` → Case.Id.
5. **Update `Account`** with the latest IA association — `PRM_CaseManager__c` → IndividualApplication.Id.

Account, Case, and IndividualApplication reference each other (Case→IA, IA→Case, Account→IA), so the back-links require the two trailing updates. Returns `practitionerAccountId`, `caseId`, `caseManagerId` (= IndividualApplication.Id) in the response.

---

## E2 · `PRM_PractitionerService` — *2.0 d* · Branch: BOTH

**Legacy:** `PRMDRPHCPHCPTaxonomyAndBusineessLicense` / IBC `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (HealthcareProvider + HealthcareProviderTaxonomy columns) + `PRMDRPHCPNPIBoardCretIdentifier` (HealthcareProviderNpi + Identifier columns) + `PRMDRCreateIdentiferAndDocument`. **Writes:** `HealthcareProvider`, `HealthcareProviderNpi`, `Identifier`, `HealthcareProviderTaxonomy`.

> **Scope note:** E2 now owns `HealthcareProviderTaxonomy` (matching the fused legacy DR). For Practitioner Creation this **supersedes the standalone E4 `PRM_TaxonomyService*`* — keep E4 only if a taxonomy-only reuse is needed elsewhere; otherwise treat E4 as covered here.
> **⚠ CL‑E1 (IBC gap):** the active IBC IP (`PRM_PractitionerCreation` v3) creates HealthcareProvider/Taxonomy (fused DR) but has **no DR creating HealthcareProviderNpi / Identifier**. Per your decision, E2 still creates NPI + Identifier for **both** branches; the IBC source DR is a **gap** — confirm IBC NPI/Identifier field values during build (default: reuse the map below).

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**` (business payload JSON), and the **upstream Ids from E1**: `accountId` (Practitioner Account), `practitionerId` (PersonContact Id = the DR's `Practitioner`/`PractitionerId`), `caseManagerId` (IndividualApplication Id = `CaseManager`/`IndividualAppId`). All formula fields are computed in the service.

```apex
public with sharing class PRM_PractitionerService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Id accountId      = (Id) params.get('accountId');        // from E1
        Id practitionerId = (Id) params.get('practitionerId');   // PersonContact from E1
        Id caseManagerId  = (Id) params.get('caseManagerId');    // IndividualApplication from E1
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        Map<String, Object> practitionerInfo = (Map<String, Object>) input.get('practitionerInfo');
        List<Object> taxonomies = (List<Object>) input.get('taxonomies');
        List<Object> identifiers = (List<Object>) input.get('identifiers');

        // build HealthcareProvider, HealthcareProviderNpi, Identifier[], HealthcareProviderTaxonomy[]
        // compute formulas (HCPStatus, NPI gating, Identifier RT/Pending, taxonomy primary/providerType)
        // DML in FK order (see "DML / order"); return created Ids

        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format** — `practitionerInfo` (HCP + NPI) + `taxonomies[]` + `identifiers[]`. Upstream Ids come via `params` (not the JSON). Formula fields are service-computed:

```json
{
  "practitionerInfo": {
    "firstName": "Jane",
    "lastName": "Smith",
    "npi": "1234567893",
    "npiType": "",
    "existingHcpNpiId": "",
    "isActive": false,
    "effectiveFrom": "",
    "effectiveTo": "",
    "hcpEffectiveFrom": "",
    "hcpEffectiveTo": ""
  },
  "taxonomies": [
    { "careTaxonomyId": "", "taxonomyCode": "207R00000X", "name": "", "isPrimary": true, "providerType": "" }
  ],
  "identifiers": [
    { "name": "", "type": "" }
  ]
}
```

> **Service-computed (do NOT send):** `HealthcareProvider.Status` (`HCPStatus`), `HealthcareProviderNpi.IsActive`/`EffectiveFrom`/`EffectiveTo` (new-NPI gating), `Identifier.RecordTypeId` (RT `PRM_Practitioner`), `Identifier.PRM_Pending__c`, `HealthcareProviderTaxonomy.ProviderType` (primary-only) and the `FinalName` taxonomy name. FK fields (`AccountId`, `PractitionerId`, `ParentRecordId`, `PRM_CaseManager__c`) are set **in-service** from the `params` Ids.

> **Field coverage check (every JSON attribute → a Field-map row):** `practitionerInfo.*` → HealthcareProvider + HealthcareProviderNpi; `taxonomies[].*` → HealthcareProviderTaxonomy; `identifiers[].*` → Identifier; `params.{accountId, practitionerId, caseManagerId}` → the FK columns. `existingHcpNpiId` drives the new-vs-existing NPI gating.

**HealthcareProvider field map** (from fused DR):


| Field                           | Source                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------ |
| `AccountId`                     | `params.accountId` (FK, in-service)                                                  |
| `PractitionerId`                | `params.practitionerId`                                                              |
| `Name`                          | ⟲ `CONCAT(NameNormalize(firstName), ' ', NameNormalize(lastName))` (not a raw input) |
| `Status`                        | ⟲ formula `HCPStatus = IF(IsActive,"Active","InActive")`                             |
| `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.effectiveFrom` / `effectiveTo`                                     |
| `PRM_CaseManager__c`            | `params.caseManagerId`                                                               |


**HealthcareProviderNpi field map** (from `PRMDRPHCPNPIBoardCretIdentifier`):


| Field                           | Source                                                               |
| ------------------------------- | -------------------------------------------------------------------- |
| `AccountId`                     | `params.accountId`                                                   |
| `PractitionerId`                | `params.practitionerId`                                              |
| `Npi` / `Name`                  | `practitionerInfo.npi`                                               |
| `NpiType`                       | `practitionerInfo.npiType`                                           |
| `IsActive`                      | ⟲ formula `IF(ISBLANK(existingHcpNpiId), isActive, null)`            |
| `EffectiveFrom` / `EffectiveTo` | ⟲ formula `IF(ISBLANK(existingHcpNpiId), hcpEffectiveFrom/To, null)` |
| `PRM_CaseManager__c`            | `params.caseManagerId`                                               |


> New-vs-existing NPI: when `existingHcpNpiId` is supplied the DR sets `Id = existingHcpNpiId` and **nulls** active/effective → `npi.IsActive = String.isBlank(existingHcpNpiId) ? isActive : null;` etc.

**Identifier field map** (from `PRMDRPHCPNPIBoardCretIdentifier` + `PRMDRCreateIdentiferAndDocument`):


| Field                                         | Source                                                 |
| --------------------------------------------- | ------------------------------------------------------ |
| `RecordTypeId`                                | ⟲ formula RT `PRM_Practitioner` (Identifier)           |
| `IdValue`                                     | `identifiers[].name`                                   |
| `PRM_Type__c`                                 | `identifiers[].type`                                   |
| `ParentRecordId`                              | `params.accountId`                                     |
| `PRM_Active__c`                               | `practitionerInfo.isActive`                            |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | `practitionerInfo.hcpEffectiveFrom` / `hcpEffectiveTo` |
| `PRM_CaseManager__c`                          | `params.caseManagerId`                                 |
| `PRM_Pending__c`                              | ⟲ formula `IF(type!="Document", true, false)`          |


**HealthcareProviderTaxonomy field map** (from fused DR + `PRMDRTransDelegatedTaxonomyData`):


| Field                           | Source                                                                                 |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `AccountId`                     | `params.accountId`                                                                     |
| `PractitionerId`                | `params.practitionerId`                                                                |
| `TaxonomyId`                    | `taxonomies[].careTaxonomyId` (resolve from `taxonomyCode` via `PRM_TaxonomySelector`) |
| `Name`                          | `taxonomies[].name` ⟲ or `FinalName = name + " - " + taxonomyCode`                     |
| `IsPrimaryTaxonomy`             | `taxonomies[].isPrimary` (⟲ `isPrimary = FinalName == primaryTaxonomy`)                |
| `IsActive`                      | `practitionerInfo.isActive`                                                            |
| `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.effectiveFrom` / `effectiveTo`                                       |
| `PRM_CaseManager__c`            | `params.caseManagerId`                                                                 |


### IP grounding (active IP → DR input mappings)

Verified from the active IPs. Upstream Ids (both branches) come from the **E1 element `DRPAccountCaseCaseManagerCreation`** → these are the `params` Ids; business data comes from the `**RecordsToUpdate**` payload node; names are normalized via `RA_TitleCase` → `PRM_FormSubUtility.NameNormalize`.

**IBC — `PRM_PractitionerCreation` v3 → `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense`:**


| DR input                                     | IP source                                                          | E2 mapping                                       |
| -------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------ |
| `Account`                                    | `DRPAccountCaseCaseManagerCreation:AccountId`                      | `params.accountId`                               |
| `Practitioner`                               | `DRPAccountCaseCaseManagerCreation:PersonContactId`                | `params.practitionerId`                          |
| `CaseManager`                                | `DRPAccountCaseCaseManagerCreation:CaseManagerId`                  | `params.caseManagerId`                           |
| `HCPName`                                    | `CONCAT(RA_TitleCase:firstName,' ',RA_TitleCase:lastName)`         | ⟲ `NameNormalize(first)+' '+NameNormalize(last)` |
| `HCPTaxonomyName` / `CareTaxonomy`           | `RecordsToUpdate:HCPTaxonomy:Name` / `:CareTaxonomy`               | `taxonomies[].name` / `careTaxonomyId`           |
| `BusinessLicense`                            | `RecordsToUpdate:BusinessLicense` (direct)                         | E5                                               |
| `IsActive` / `EffectiveFrom` / `EffectiveTo` | `RecordsToUpdate:IsRecordActive` / `EffectiveFrom` / `EffectiveTo` | `practitionerInfo.*`                             |


**Delegated — `PRM_DelegatedPractitionerCreation` v7:**

`PRMDRPHCPHCPTaxonomyAndBusineessLicense` — same as IBC **except**: `BusinessLicense` ← `LA_MergeBusinessLicense` (DEA/CDS + SBRD merge — E5), `TaxonomyData` ← `DRTTaxonomyData` (transform `PRMDRTransDelegatedTaxonomyData` output — E4), plus `ProviderType` ← `RecordsToUpdate:ProviderType`.

`PRMDRPHCPNPIBoardCretIdentifier`:


| DR input                                           | IP source                                                                                 | E2 mapping                                             |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `HCPNPI`                                           | `RecordsToUpdate:HCPNPI`                                                                  | `practitionerInfo.npi`                                 |
| `HCPNPIId`                                         | `RecordsToUpdate:HCPNPIId`                                                                | `practitionerInfo.existingHcpNpiId` (gating)           |
| `HCPEffectiveFrom` / `HCPEffectiveTo`              | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`                                           | `practitionerInfo.hcpEffectiveFrom` / `hcpEffectiveTo` |
| `IsActive`                                         | `RecordsToUpdate:IsRecordActive`                                                          | `practitionerInfo.isActive`                            |
| `AccountId` / `PractitionerId` / `IndividualAppId` | `DRPAccountCaseCaseManagerCreation:AccountId` / `PersonContactId` / `CaseManagerId`       | `params.*`                                             |
| `HealthcareProviderId`                             | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId` (HCP DR output) | ← created HCP Id (E7 BoardCert)                        |
| `Identifiers`                                      | `IF(ISNOTBLANK(Identifiers                                                                | 1:Name), RecordsToUpdate:Identifiers, '')`             |
| `BoardCertifications`                              | `LIST(RecordsToUpdate:BoardCertifications)`                                               | E7                                                     |


> **Branch differences:** IBC feeds taxonomy/license **directly** from the payload (no transform); Delegated routes taxonomy through the `**DRTTaxonomyData` transform** and license through the `**LA_MergeBusinessLicense`** merge, and adds `ProviderType`, `Identifiers`, `BoardCertifications`. **Ordering:** the NPI/Identifier/BoardCert DR consumes `HealthCareProviderId` from the HCP DR output → **HCP must be inserted before NPI/Identifier**.

**Formulas → Apex:**

- `HCPName` = `PRM_FormSubUtility.NameNormalize(firstName) + ' ' + PRM_FormSubUtility.NameNormalize(lastName)`.
- `HCPStatus` = `isActive ? 'Active' : 'InActive'`.
- NPI gating = `String.isBlank(existingHcpNpiId) ? value : null` (IsActive / EffectiveFrom / EffectiveTo).
- Identifier `RecordTypeId` via cached describe (`PRM_Practitioner`); `PRM_Pending__c = !'Document'.equals(type)`; Identifiers gated on first element having a `name`.
- Taxonomy: IBC direct; Delegated via transform — `FinalName = name + ' - ' + taxonomyCode`; `IsPrimaryTaxonomy = (FinalName == primaryTaxonomy)`; `ProviderType = isPrimary ? providerType : null`.

**DML / order:** Account/Practitioner/CaseManager exist (E1, via `params`). Insert in dependency order, **one bulk DML per object type**:

1. **Insert `HealthcareProvider`** (FK `AccountId`, `PractitionerId`).
2. **Insert `HealthcareProviderNpi`** (FK `AccountId`, `PractitionerId`).
3. **Insert `Identifier[]`** (FK `ParentRecordId` = Account).
4. **Insert `HealthcareProviderTaxonomy[]`** (FK `AccountId`, `PractitionerId`).

No circular FKs here (all reference E1 records). Returns `healthcareProviderId`, `healthcareProviderNpiId`, `identifierIds`, `taxonomyIds` in the response.

---

## E3 · `PRM_GroupService` — *1.5 d* · Branch: DELEGATED

**Legacy:** `PRMPostGroupPractitionerCreation` (Load) — invoked by element `**DRCreateGroupRecords*`* in IP `PRM_DelegatedPractitionerCreation` v7. **Writes:** `Account` (Vendor/Group), `Identifier` (Vendor), `HealthcareProviderNpi` (group), `HealthcareProvider` (group).

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, and the `**caseManagerId**` from E1. Constants set by the service: `npiType = "Organization"`, `ParticipationStatus = "Participating"`. All `…Val` fields are formula-derived (new-vs-existing gating).

```apex
public with sharing class PRM_GroupService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Id caseManagerId = (Id) params.get('caseManagerId');     // from E1
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        Map<String, Object> groupInfo = (Map<String, Object>) input.get('groupInfo');

        // resolve new-vs-existing (groupInfo.existingGroupId), compute *Val formulas,
        // build Account(Vendor) + Identifier + HealthcareProviderNpi + HealthcareProvider, then DML.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format** — a `groupInfo` node + shared effective/active context (constants & `…Val` fields are service-computed):

```json
{
  "groupInfo": {
    "groupTypeAhead": "Acme Medical Group",
    "groupTaxId": "12-3456789",
    "groupNPI": "9876543210",
    "credentialingStatus": "",
    "existingGroupId": "",
    "existingGroupNPIId": "",
    "tinId": ""
  },
  "isActive": false,
  "effectiveFrom": "",
  "effectiveTo": ""
}
```

> **Service-set constants (do NOT send):** `HealthcareProviderNpi.NpiType = "Organization"`, `Account.PRM_ParticipationStatus__c = "Participating"`, `PRM_Pending__c` default per gating. **Formula-derived (do NOT send):** `…Val` fields (`EffectiveFromVal`, `EffectiveToVal`, `IsActiveVal`, `CaseManagerIdVal`, `PendingVal`, `CredentialingStatusVal`, `HPStatus`), `SourceSystemId` / `SourceSystemIdentifier`, vendor record types.

### IP grounding (`PRM_DelegatedPractitionerCreation` v7 → element `DRCreateGroupRecords` → `PRMPostGroupPractitionerCreation`)


| DR input                               | IP source                                         | E3 mapping                      |
| -------------------------------------- | ------------------------------------------------- | ------------------------------- |
| `GroupInformation`                     | `PractionerGroup:GroupInformation`                | `groupInfo` node                |
| `CaseManagerId`                        | `DRPAccountCaseCaseManagerCreation:CaseManagerId` | `params.caseManagerId`          |
| `IsActive`                             | `RecordsToUpdate:IsRecordActive`                  | `isActive`                      |
| `EffectiveDate` / `EffectiveTo`        | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`   | `effectiveFrom` / `effectiveTo` |
| `npiType`                              | `"Organization"` (constant)                       | service constant                |
| `GroupInformation:ParticipationStatus` | `"Participating"` (constant)                      | service constant                |
| `PRM_Pending__c`                       | `False` (constant)                                | service constant                |


**Field map (grounded):**


| Target                | Field                                         | Source                                               |
| --------------------- | --------------------------------------------- | ---------------------------------------------------- |
| Account               | `RecordTypeId`                                | ⟲ RT `PRM_Vendor` (Account)                          |
| Account               | `Name` / `accName`                            | `groupInfo.groupTypeAhead`                           |
| Account               | `Id`                                          | `groupInfo.existingGroupId` (existing)               |
| Account               | `Type` / `PRM_VendorType__c`                  | ⟲ formula (vendor)                                   |
| Account               | `HealthCloudGA__SourceSystemId__c`            | ⟲ `SourceSystemId` (new only)                        |
| Account               | `PRM_ParticipationStatus__c`                  | `"Participating"` (constant)                         |
| Account               | `PRM_CredentialingStatus__c`                  | ⟲ `CredentialingStatusVal`                           |
| Account               | `IsActive`                                    | ⟲ `IsActiveVal`                                      |
| Account               | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| Account               | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| Account               | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| Identifier            | `RecordTypeId`                                | ⟲ RT `PRM_Vendor` (Identifier)                       |
| Identifier            | `IdValue`                                     | `groupInfo.groupTaxId`                               |
| Identifier            | `Id`                                          | `groupInfo.tinId` (existing)                         |
| Identifier            | `ParentRecordId` / `PRM_Type__c`              | ⟲ formula (← Account)                                |
| Identifier            | `PRM_Active__c`                               | ⟲ `IsActiveVal`                                      |
| Identifier            | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| Identifier            | `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| Identifier            | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| HealthcareProviderNpi | `Npi` / `Name`                                | `groupInfo.groupNPI` (`Npi` **[KEY]**)               |
| HealthcareProviderNpi | `Id`                                          | `groupInfo.existingGroupNPIId` (existing)            |
| HealthcareProviderNpi | `NpiType`                                     | `"Organization"` (constant)                          |
| HealthcareProviderNpi | `EffectiveFrom` / `EffectiveTo`               | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| HealthcareProviderNpi | `PRM_Pending__c`                              | ⟲ `PendingVal`                                       |
| HealthcareProviderNpi | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |
| HealthcareProvider    | `Name`                                        | `groupInfo.groupTypeAhead`                           |
| HealthcareProvider    | `AccountId`                                   | ⟲ formula (← Account)                                |
| HealthcareProvider    | `Status`                                      | ⟲ `HPStatus`                                         |
| HealthcareProvider    | `SourceSystemIdentifier`                      | ⟲ `SourceSystemIdentifier` (existing only) **[KEY]** |
| HealthcareProvider    | `EffectiveFrom` / `EffectiveTo`               | ⟲ `EffectiveFromVal` / `EffectiveToVal`              |
| HealthcareProvider    | `PRM_CaseManager__c`                          | ⟲ `CaseManagerIdVal`                                 |


**Formulas → Apex** (all gate on `String.isBlank(groupInfo.existingGroupId)` = **new group**):

- `EffectiveFromVal` / `EffectiveToVal` / `IsActiveVal` / `CaseManagerIdVal` = `isNew ? <value> : null` (suppressed for existing groups).
- `CredentialingStatusVal` = `isNew ? groupInfo.credentialingStatus : null`.
- `PendingVal` = `isNew ? false : null`.
- `HPStatus` = `isNew ? (isActive ? 'Active' : 'Inactive') : null`.
- `SourceSystemId` (Account) = `isNew ? groupTaxId + '-' + groupTypeAhead : null` (**new** only).
- `SourceSystemIdentifier` (HealthcareProvider) = `!isNew ? groupTaxId + '-' + groupTypeAhead : null` (**existing** only — the inverse).
- Vendor RTs (Account + Identifier) via cached describe (`PRM_Vendor`).

> **New-vs-existing:** when `existingGroupId`/`tinId`/`existingGroupNPIId` are supplied the service **reuses** them (sets `Id`) and the `…Val` fields go null; `SourceSystemIdentifier` (HCP) is set only for the existing path, `SourceSystemId` (Account) only for the new path.

**DML / order:** insert **Account (Vendor)** → then **Identifier** (FK `ParentRecordId` = Account), **HealthcareProviderNpi**, **HealthcareProvider** (FK `AccountId` = Account) — one bulk DML per type. Returns `groupAccountId`, `groupIdentifierId`, `groupNpiId`, `groupHealthcareProviderId`.

---

## E4 · `PRM_TaxonomyService` — **merged into E2** (removed)

`HealthcareProviderTaxonomy` is created by the same fused DR that E2 owns (`PRMDRPHCP…TaxonomyAndBusineessLicense`), so for Practitioner Creation there is **no standalone taxonomy service** — see the **HealthcareProviderTaxonomy field map + transform formulas in E2**. The `PRM_TaxonomySelector.getTaxonomyRefs(Set<String> codes)` (EPIC D) is still used inside E2 to resolve `TaxonomyId` from codes. (Reintroduce a standalone E4 only if a future flow needs taxonomy-only creation.)

---

## E5 · `PRM_LicenseService` — *0.5 d* · Branch: BOTH

**Legacy:** `PRMDRTransformDelegatedBusinessLicense` (Transform — Delegated DEA/CDS + SBRD merge) + the **BusinessLicense columns** of the fused HCP DR (`PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` IBC / `PRMDRPHCPHCPTaxonomyAndBusineessLicense` Delegated). **Writes:** `BusinessLicense`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, and the **E1 FK Ids** `accountId` (→ `AccountId`) and `practitionerId` (→ `ContactId`), `caseManagerId` (→ `PRM_CaseManager__c`). `VerifiedDate` is service-computed.

```apex
public with sharing class PRM_LicenseService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Id accountId      = (Id) params.get('accountId');
        Id practitionerId = (Id) params.get('practitionerId');   // PersonContact
        Id caseManagerId  = (Id) params.get('caseManagerId');
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        List<Object> businessLicenses = (List<Object>) input.get('businessLicenses'); // unified shape
        // build BusinessLicense[] (VerifiedDate = Date.today()), then bulk insert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format** — a **single unified `businessLicenses[]`** array (each element carries its own `licenseType`). The legacy two-array split (`DEACDSBusinessLicense` / `SBRDBusinessLicense`) and its normalize-and-merge transform are **collapsed** here — see the note below.

```json
{
  "businessLicenses": [
    { "practitionerLicenseNumber": "3232323", "licenseType": "SBRD", "practitionerState": "PA", "licenseIssuedDate": "12/30/2024", "licenseExpirationDate": "02/01/2025" },
    { "practitionerLicenseNumber": "232323",  "licenseType": "DEA",  "practitionerState": "PA" }
  ]
}
```

> **Why one node now (not two):** in the legacy OmniScript, DEA/CDS and SBRD licenses came from two separate blocks with *different field names*, so `PRMDRTransformDelegatedBusinessLicense` existed only to **rename DEA/CDS fields to the SBRD shape and stamp `licenseType="SBRD"`**, then `LA_MergeBusinessLicense` merged the two arrays. In Apex the payload can supply **one `businessLicenses[]`** already in the unified shape (with `licenseType` per element), so the transform + merge are unnecessary. Confirm the OmniScript still emits two blocks (then normalize in `PRM_FormSubUtility`) vs. one unified array — **CL‑E8**.

### IP grounding (BusinessLicense input to the fused HCP DR)


| Branch                                             | IP source of `BusinessLicense`                                                                       | New design                                                                                   |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| IBC (`PRM_PractitionerCreation` v3)                | `RecordsToUpdate:BusinessLicense` (already unified)                                                  | `businessLicenses[]` directly                                                                |
| Delegated (`PRM_DelegatedPractitionerCreation` v7) | `LA_MergeBusinessLicense` = `PRMDRTransformDelegatedBusinessLicense` (normalized DEA/CDS) **+** SBRD | `businessLicenses[]` (single array; normalize only if the OmniScript still sends two blocks) |


**Field map (grounded — fused DR `BusinessLicense` columns → `businessLicenses[]`):**


| BusinessLicense field                  | Source                                         |
| -------------------------------------- | ---------------------------------------------- |
| `AccountId`                            | `params.accountId` (FK, in-service)            |
| `ContactId`                            | `params.practitionerId`                        |
| `Name` / `LicenseNumber`               | `businessLicenses[].practitionerLicenseNumber` |
| `LicenseClass`                         | `businessLicenses[].licenseType`               |
| `PRM_LicenseState__c`                  | `businessLicenses[].practitionerState`         |
| `PRM_ProviderLicenseEffectiveDate__c`  | `businessLicenses[].licenseIssuedDate`         |
| `PRM_ProviderLicenseExpirationDate__c` | `businessLicenses[].licenseExpirationDate`     |
| `VerifiedDate`                         | ⟲ formula `TODAY()` → `Date.today()`           |
| `PRM_CaseManager__c`                   | `params.caseManagerId`                         |
| `Status`                               | payload (optional)                             |


> **Coverage check:** every fused-DR `BusinessLicense.*` column maps to a `businessLicenses[]` attribute or a `params` Id. `licenseType` distinguishes DEA / CDS / SBRD (replacing the legacy two-block + transform).

**DML / order:** Account/Practitioner/CaseManager exist (E1, via `params`). Single **bulk insert** of `BusinessLicense[]` (FK `AccountId`, `ContactId`). Returns `businessLicenseIds`.

---

## E6 · `PRM_EducationService` — *0.5 d* · Branch: DELEGATED (gated)

**Legacy:** `PRMDRTransformAddEducation` (Transform — enriches each row with FK Ids) + `PRMDRPCreateEducation` (Load). **Writes:** `PersonEducation`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, and the E1/E2 FK Ids: `practitionerId` (→ `ContactId`), `healthcareProviderId` (from E2 → `HealthcareProviderId`), `caseManagerId`.

```apex
public with sharing class PRM_EducationService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow = (String) params.get('flow');
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        List<Object> education = (List<Object>) input.get('education');
        Id practitionerId = (Id) params.get('practitionerId');
        Id hcpId          = (Id) params.get('healthcareProviderId');   // from E2
        Id caseManagerId  = (Id) params.get('caseManagerId');
        // build PersonEducation[] from `education` + FK Ids, then bulk insert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format:**

```json
{
  "education": [
    { "practitionerDegree": "", "degreeId": "", "institutionId": "", "educationLevel": "", "educationStartDate": "", "educationEndDate": "", "educationCompleted": false, "primaryPersonEdu": false }
  ]
}
```

### IP grounding (`PRM_DelegatedPractitionerCreation` v7)

The transform element `TransformAddEducation` injects the FK Ids into each row, then `DRPCreateEducation` loads it:


| DR input                         | IP source                                                                 | E6 mapping                    |
| -------------------------------- | ------------------------------------------------------------------------- | ----------------------------- |
| `AddEducationTransformed` (rows) | `RecordsToUpdate:AddEducation`                                            | `education[]`                 |
| `PersonContactId`                | `DRPAccountCaseCaseManagerCreation:PersonContactId`                       | `params.practitionerId`       |
| `HealthcareProviderId`           | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId` | `params.healthcareProviderId` |
| `PRM_CaseManager__c`             | `DRPAccountCaseCaseManagerCreation:CaseManagerId`                         | `params.caseManagerId`        |
| (Load) `AddEducationDRInput`     | `TransformAddEducation:AddEducationTransformed`                           | the enriched rows             |


**Field map (grounded — `AddEducationDRInput:*`):**


| PersonEducation field                            | Source                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `ContactId`                                      | `params.practitionerId`                                            |
| `HealthcareProviderId`                           | `params.healthcareProviderId`                                      |
| `Name`                                           | `education[].practitionerDegree` (`PractitionerDegree-Block:Name`) |
| `PRM_Degree__c`                                  | `education[].degreeId` (`PractitionerDegree-Block:Id`)             |
| `PRM_Institution__c`                             | `education[].institutionId` (`InstitutionName-Block:Id`)           |
| `EducationLevel`                                 | `education[].educationLevel`                                       |
| `PRM_StartDate__c` / `PRM_EndDate__c`            | `education[].educationStartDate` / `educationEndDate`              |
| `PRM_Completed__c`                               | `education[].educationCompleted` (boolean)                         |
| `PRM_Completed_picklist` *(`CompletedPicklist`)* | ⟲ formula `educationCompleted ? "Yes" : "No"`                      |
| `PRM_Primary__c`                                 | `education[].primaryPersonEdu`                                     |
| `PRM_CaseManager__c`                             | `params.caseManagerId`                                             |


> Confirm the "Completed" picklist field API name (`CompletedPicklist` is the DR formula alias) — **CL‑E3**.

**Gating / DML:** runs only when `education` is non-empty; single bulk insert. Returns `personEducationIds`.

---

## E7 · `PRM_BoardCertificationService` — *0.5 d* · Branch: DELEGATED (gated)

**Legacy:** BoardCertification columns of `PRMDRPHCPNPIBoardCretIdentifier` (Load — shared with E2's NPI/Identifier). **Writes:** `BoardCertification`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, and the FK Ids: `accountId`, `practitionerId`, `healthcareProviderId` (from E2), `caseManagerId`, plus `effectiveFrom`/`effectiveTo`.

```apex
public with sharing class PRM_BoardCertificationService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        List<Object> boardCertifications = (List<Object>) input.get('boardCertifications');
        // FK Ids from params; build BoardCertification[]; upsert by BoardName.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format:**

```json
{
  "boardCertifications": [
    { "boardName": "ABIM", "boardCertificationName": "Internal Medicine", "certificationType": "", "boardExpires": "", "boardOriginal": "", "boardRecret": "" }
  ]
}
```

### IP grounding (`PRM_DelegatedPractitionerCreation` v7 → element `DRPHCPNPIBoardCretIdentifier`)


| DR input                                           | IP source                                                                           | E7 mapping                              |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------- |
| `BoardCertifications`                              | `LIST(RecordsToUpdate:BoardCertifications)`                                         | `boardCertifications[]`                 |
| `AccountId` / `PractitionerId` / `IndividualAppId` | `DRPAccountCaseCaseManagerCreation:AccountId` / `PersonContactId` / `CaseManagerId` | `params.*`                              |
| `HealthcareProviderId`                             | `DRPHCProviderHCProviderTaxonomyAndBusineessLicense:HealthCareProviderId`           | `params.healthcareProviderId` (from E2) |
| `HCPEffectiveFrom` / `HCPEffectiveTo`              | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`                                     | `params.effectiveFrom` / `effectiveTo`  |


**Field map (grounded):**


| BoardCertification field                      | Source                                             |
| --------------------------------------------- | -------------------------------------------------- |
| `AccountId`                                   | `params.accountId`                                 |
| `HealthcareProviderId`                        | `params.healthcareProviderId`                      |
| `PractitionerId`                              | `params.practitionerId`                            |
| `Name`                                        | `boardCertifications[].boardCertificationName`     |
| `BoardName`                                   | `boardCertifications[].boardName` **[upsert KEY]** |
| `CertificationType`                           | `boardCertifications[].certificationType`          |
| `ExpirationDate`                              | `boardCertifications[].boardExpires`               |
| `PRM_BoardOriginal__c`                        | `boardCertifications[].boardOriginal`              |
| `PRM_BoardReCert__c`                          | `boardCertifications[].boardRecret`                |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | `params.effectiveFrom` / `effectiveTo`             |
| `PRM_CaseManager__c`                          | `params.caseManagerId`                             |


> `BoardName` is the DR's **upsert key** — use `upsert … BoardName` (or dedupe by BoardName) rather than blind insert. Since this object is part of E2's NPI/Identifier DR, ensure E7 runs **after** E2 (it needs `healthcareProviderId`).

**Gating / DML:** runs only when `boardCertifications` is non-empty; single bulk insert/upsert by `BoardName`. Returns `boardCertificationIds`.

---

## E8 · `PRM_InfoCodeService` — *1.5 d* · Branch: BOTH (gated)

**Legacy:** `PRMDRPCreateInfoCodeAssignments` (Load — straight map, no formulas). **Writes:** `PRM_InfoCodeAssignment__c`. Two methods per plan: `createIfPresent(infoCodes)` (practitioner-grain, here) and `prepareBulkForLocations(addresses)` (facility-grain — Part 2 §E14 sibling).

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput**`, the FK Ids `accountId`, `caseManagerId`, `isActive`, `effectiveFrom`/`effectiveTo`.

```apex
public with sharing class PRM_InfoCodeService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        List<Object> infoCodes = (List<Object>) input.get('infoCodes'); // resolved InfoCode Ids
        if (infoCodes == null || infoCodes.isEmpty()) { response = new Map<String,Object>(); return response; }
        // build PRM_InfoCodeAssignment__c[] from infoCodes + params; bulk insert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format:**

```json
{
  "infoCodes": [ { "id": "" } ],
  "isActive": true,
  "effectiveFrom": "",
  "effectiveTo": ""
}
```

> `infoCodes[].id` are **resolved InfoCode record Ids** (the legacy IP passes `%InfoCodeIds%`, a list resolved by a prior step). Resolve them via a selector before this service if only codes are available — **CL‑E9**.

### IP grounding (element `DRPCreateInfoCodeAssignments` — IBC v3 & Delegated v7)


| DR input                        | IP source                                         | E8 mapping                             |
| ------------------------------- | ------------------------------------------------- | -------------------------------------- |
| `Account`                       | `DRPAccountCaseCaseManagerCreation:AccountId`     | `params.accountId`                     |
| `CaseManager`                   | `DRPAccountCaseCaseManagerCreation:CaseManagerId` | `params.caseManagerId`                 |
| `InfoCodeIds`                   | `%InfoCodeIds%` (resolved list)                   | `infoCodes[]`                          |
| `EffectiveFrom` / `EffectiveTo` | `RecordsToUpdate:EffectiveFrom` / `EffectiveTo`   | `params.effectiveFrom` / `effectiveTo` |
| `IsActive`                      | `%IsActive%` (Delegated only)                     | `params.isActive`                      |


**Field map (grounded — practitioner-grain):**


| PRM_InfoCodeAssignment__c field               | Source                                 |
| --------------------------------------------- | -------------------------------------- |
| `PRM_Account__c`                              | `params.accountId`                     |
| `PRM_InfoCode__c`                             | `infoCodes[].id`                       |
| `PRM_Active__c`                               | `params.isActive`                      |
| `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` | `params.effectiveFrom` / `effectiveTo` |
| `PRM_CaseManager__c`                          | `params.caseManagerId`                 |


**Gating / DML:** runs only when `infoCodes` is non-empty (gated no-op otherwise); single bulk insert. Returns `infoCodeAssignmentIds`. *(The facility-grain `prepareBulkForLocations(addresses)` method is detailed alongside §E14 in Part 2.)*

---

## E.Effort (E1–E8)


| Service                                                         | Est (d)            |
| --------------------------------------------------------------- | ------------------ |
| E1 `PRM_CaseService`                                            | 2.0                |
| E2 `PRM_PractitionerService` (incl. HealthcareProviderTaxonomy) | 2.5                |
| E3 `PRM_GroupService`                                           | 1.5                |
| E4 `PRM_TaxonomyService`                                        | — (merged into E2) |
| E5 `PRM_LicenseService`                                         | 0.5                |
| E6 `PRM_EducationService`                                       | 0.5                |
| E7 `PRM_BoardCertificationService`                              | 0.5                |
| E8 `PRM_InfoCodeService`                                        | 1.5                |
| **Total**                                                       | **9.0**            |


---

## E.CL — Clarification Log (E1–E8)


| Ref   | Item                                                                                                                                                                                                                                                                                                                     | Evidence                                                                                                                                                  | Action                                                                                                                                                                                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL‑E1 | **IBC NPI/Identifier source.** Active IBC IP (`PRM_PractitionerCreation` v3) creates HealthcareProvider but **no** NPI/Identifier DR. Decision: keep E2 creating them for both branches.                                                                                                                                 | IBC IP DR set = CaseCaseManagerAndAccount, HCProviderHCProviderTaxonomyAndBusineessLicense, PCreateInfoCodeAssignments, PPractionerPracticeLocations, CDM | Confirm IBC NPI/Identifier field values during E2 build (default: reuse Delegated map) — Tech Lead                                                                                                          |
| CL‑E2 | **IA RecordType ordinal mapping.** Legacy uses `recordTypeList                                                                                                                                                                                                                                                           | 3/                                                                                                                                                        | 4`after`ORDER BY SobjectType ASC, DeveloperName DESC`. New design resolves by DeveloperName; the Practitioner-flow IA RT (`PRM_PDMManualChange`vs`PRM_PractitionerParticipationRequest`) must be confirmed. |
| CL‑E3 | **Education "Completed" picklist field API.** DR formula alias `CompletedPicklist`; target field API not in the map.                                                                                                                                                                                                     | `PRMDRPCreateEducation`                                                                                                                                   | Confirm `PersonEducation` picklist API name — Eng                                                                                                                                                           |
| CL‑E4 | **Legacy DR fusion vs services.** HCP+Taxonomy+License and NPI+BoardCert+Identifier are each one DR; new design splits them. Field maps partitioned here.                                                                                                                                                                | fused DRs                                                                                                                                                 | Confirmed: keep fine-grained split (ratified)                                                                                                                                                               |
| CL‑E5 | `**RecordType` helper home.** Replacing `QUERY(...)` formulas needs a cached describe helper; its class home is TBD.                                                                                                                                                                                                     | TDD CL‑13                                                                                                                                                 | Decide helper home before E1 — Tech Lead                                                                                                                                                                    |
| CL‑E6 | **Group DR source (resolved).** E3 is grounded to `PRMPostGroupPractitionerCreation` via the Delegated IP element `DRCreateGroupRecords` (not the standalone `PRM_CreateGroupScreenRecord` lineage).                                                                                                                     | `PRM_DelegatedPractitionerCreation` v7                                                                                                                    | Resolved — use `PRMPostGroupPractitionerCreation`                                                                                                                                                           |
| CL‑E7 | **Group typeahead inputs.** `groupInfo` maps the `GroupInformation:GroupTypeAhead-Block:*` keys (`groupTypeAhead`, `tinId`, `existingGroupId`, `existingGroupNPIId`); confirm the OmniScript `PractionerGroup:GroupInformation` payload contract.                                                                        | `PRMPostGroupPractitionerCreation`                                                                                                                        | Map to `GroupPayload` in EPIC F — Eng                                                                                                                                                                       |
| CL‑E8 | **License payload shape.** E5 uses one unified `businessLicenses[]` (with `licenseType`), collapsing the legacy two-block (`DEACDS`/`SBRD`) + `PRMDRTransformDelegatedBusinessLicense` + `LA_MergeBusinessLicense`. Confirm the OmniScript emits a single array (else normalize the two blocks in `PRM_FormSubUtility`). | `PRMDRTransformDelegatedBusinessLicense`                                                                                                                  | Confirm payload shape in EPIC F — Eng                                                                                                                                                                       |
| CL‑E9 | **InfoCode id resolution.** E8's `infoCodes[].id` are resolved InfoCode record Ids (legacy `%InfoCodeIds%` from a prior step). Confirm whether the payload sends resolved Ids or codes needing selector resolution.                                                                                                      | element `DRPCreateInfoCodeAssignments`                                                                                                                    | Confirm/resolve via selector before E8 — Eng                                                                                                                                                                |


---

> **Part 2 (E9–E17):** see `**Epic_E_Practitioner_Services_Part2.md`** — covers `PRM_FileService`, `PRM_ContactService`, `PRM_LanguageService`, `PRM_AddressService` ⚡, `PRM_FacilityNetworkService` ⚡, `PRM_ProviderFeatureService`, `PRM_ExistingPrimaryPracticeService`, `PRM_CaseDataManagerService`, and the async `PRM_Level4RecordCreationService`, grounded the same way. **EPIC E grand total (E1–E17) ≈ 22.5 d** (Part 1 9.0 + Part 2 13.5).

