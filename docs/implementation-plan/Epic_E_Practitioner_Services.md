# Epic E — Practitioner Creation Services (Implementation Guide) · Part 1 · Intake + PractitionerBatch

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.6) · `PRM_Implementation_Plan.md` (§8 EPIC E)
> **Goal:** re-implement the Practitioner Creation record-creation logic (currently OmniStudio IPs + DataRaptors) as layered Apex services. **This part covers synchronous intake (E1) + the `PractitionerBatch` services** (seq 1): **E2 · E5 · E6 · E7 · E8 · E10 · E11**, plus the two cross-cutting services **E19 `PRM_CMAService` (CMA)** and **E16 `PRM_CaseDataManagerService` (CDM manifest)**. `PracticeLocationAndGroupBatch` services are in **Part 2**; `PLRelatedBatch` / `Level4RecordCreationBatch` (and the TBD `GroupRelatedBatch`) are in **Part 3**.

> **🔄 Build contracts are now in the per-service folder docs (authoritative — see §E0.4).** The detailed, build-ready specs for the `PractitionerBatch` services live under **`epic-e-services/PractitionerBatch Related Services/`** (E02/E05/E06/E07/E08/E10/E11 + `PRM_PractitionerBatch` E20) and **`epic-e-services/`** (E16, E19), each with a companion `*_Execution_Plan.md`. Where those differ from the legacy-grounded snippets below, **the folder docs win** — the sections here retain the legacy DR grounding for traceability.
> **Estimate (Part 1):** ~10.5 engineer-days (E4 merged into E2) · **Depends on:** EPIC A (objects), EPIC B (`PRM_ServiceBase`, `PRM_FormSubUtility`), EPIC D (selectors). · **Blocks:** EPIC F (intake wrapper).

> **🔄 Reorganized by batch (sequential build).** Epic E is now split **by the batch a service runs in**, so each batch can be built and shipped end-to-end before the next, rather than waiting for all 18 services. **Part 1 = intake + `PractitionerBatch`; Part 2 = `PracticeLocationAndGroupBatch`; Part 3 = `PLRelatedBatch` + `Level4RecordCreationBatch` (+ `GroupRelatedBatch` TBD).** E‑numbers and Clarification‑Log ref IDs are unchanged across the move so existing cross‑references still resolve. **Shared conventions & the legacy entry path (E0–E0.3) live here in Part 1** and are referenced by Parts 2–3.

> **🔄 Async-only model (services run inside batch classes, except E1):** there is **no synchronous orchestrator**. **E1 `PRM_CaseService` runs at synchronous intake** (the "Case Manager Service" — one Case Manager per practitioner; see E1 below). **E2–E18** are unchanged in *what they build* but are invoked **inside the five concrete batch classes** — `PractitionerBatch`, `PracticeLocationAndGroupBatch`, `GroupRelatedBatch`, `PLRelatedBatch`, `Level4RecordCreationBatch` — which `PRM_AsyncOrchestrator` sequences from Custom Metadata (`PRM_Sequence__c`) with **halt-on-failure**. Each batch handles **IBC vs Delegated branching internally** and calls back `findNextJob` in `finish()`. **Batch ↔ service mapping: see Plan §8.1.** Residual open (CL-15): `GroupRelatedBatch` services TBD. EPIC E delivery also includes authoring the five batch wrappers.

> **Grounding:** every field map, formula, and record-type below was extracted from the **active** (`isActive=true`) OmniStudio metadata in this repo — not invented. Source artifacts are cited per service. Where the active metadata contradicts the plan, it is flagged in the **Clarification Log (§E.CL)**.

### Batch ↔ service mapping (CL-15)

Sequenced by `PRM_AsyncOrchestrator` from `PRM_AsyncJobConfig__mdt.PRM_Sequence__c`, halt-on-failure; each batch branches IBC vs Delegated internally. The **Part** column shows which guide documents each batch's services.

| Seq | Batch | Part | Services |
|---|---|---|---|
| — | *(sync intake)* | **Part 1** | **E1** `PRM_CaseService` — one Case Manager (`IndividualApplication`) per practitioner |
| 1 | `PractitionerBatch` | **Part 1** | **E2** `PRM_PractitionerService` · **E5** `PRM_LicenseService` · **E6** `PRM_EducationService` · **E7** `PRM_BoardCertificationService` · **E8** `PRM_InfoCodeService` · **E10** `PRM_ContactService` · **E11** `PRM_LanguageService` · **E19** `PRM_CMAService` (CMA) · **E16** `PRM_CaseDataManagerService` (CDM) |
| 2 | `PracticeLocationAndGroupBatch` | **Part 2** | **E3** `PRM_GroupService` · **E13** `PRM_HealthcareFacilityCreationService` · **E9** `PRM_FileService` · **E12** `PRM_HealthcareProviderNpiService` |
| 3 | `GroupRelatedBatch` | **Part 3** | **TBD** (CL-15) |
| 4 | `PLRelatedBatch` (batch **E22** `PRM_PLRelatedBatch`) | **Part 3** | **E14** `PRM_HPFService` (PLA + PPA, single service) · **E15** `PRM_ProviderFeatureService` (AssistiveAid + ACC) · **E19** CMA · **E16** CDM. *(~~E17~~ dropped — HFN is a trigger side-effect of E18.)* |
| 5 | `Level4RecordCreationBatch` (batch **E23**) | **Part 3** | **E18** `PRM_Level4RecordCreationService` (creates `HealthcareFacilityNetwork` RT `PRM_FacilityPractitionerTxNw`; HFN trigger cascades `PRM_FacilityNw`/`PRM_FacilityTx`) |

> Service legend: E2 `PRM_PractitionerService` · E3 `PRM_GroupService` · E5 `PRM_LicenseService` · E6 `PRM_EducationService` · E7 `PRM_BoardCertificationService` · E8 `PRM_InfoCodeService` · E9 `PRM_FileService` · E10 `PRM_ContactService` · E11 `PRM_LanguageService` · E12 `PRM_HealthcareProviderNpiService` · E13 `PRM_HealthcareFacilityCreationService` · E14 `PRM_HPFService` · E15 `PRM_ProviderFeatureService` · E16 `PRM_CaseDataManagerService` · ~~E17 `PRM_HealthcareFacilityNetworkService`~~ (dropped — HFN is a trigger side-effect of E18) · E18 `PRM_Level4RecordCreationService` · E19 `PRM_CMAService` (cross-cutting CMA) · batch designs E20/E21/E22. (Mirrors Plan §8.1.)

---

## E0. Entry path & how the legacy flow is structured (grounded)

### Legacy DR → service map (active DRs only)


| Service                                                                   | Legacy active DR(s)                                                                                                                                                                                                                  | DR type                          | Objects the DR writes                                                                 |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------------------------------------- |
| **E1** `PRM_CaseService`                                                  | `PRMDRCreateCaseCaseManagerAndAccount`                                                                                                                                                                                               | Load                             | Account, Case, IndividualApplication                                                  |
| **E2** `PRM_PractitionerService`                                          | Delg: `PRMDRPHCPHCPTaxonomyAndBusineessLicense` (HCP+Taxonomy) + `PRMDRPHCPNPIBoardCretIdentifier` (NPI+Identifier) + `PRMDRCreateIdentiferAndDocument`; IBC: `PRMDRPHCProviderHCProviderTaxonomyAndBusineessLicense` (HCP+Taxonomy) | Load                             | HealthcareProvider, HealthcareProviderNpi, Identifier, **HealthcareProviderTaxonomy** |
| **E3** `PRM_GroupService` *(Part 2)*                                      | `PRMPostGroupPractitionerCreation` (via `PRM_DelegatedPractitionerCreation` v7 element `DRCreateGroupRecords`)                                                                                                                       | Load                             | Account(Vendor), Identifier, HealthcareProviderNpi, HealthcareProvider                |
| **E4** `PRM_TaxonomyService` *(folded into E2 for Practitioner Creation)* | `PRMDRExtractTaxonomyData` + `PRMDRTransDelegatedTaxonomyData` (transform) + Taxonomy part of the fused HCP DR                                                                                                                       | Turbo Extract / Transform / Load | HealthcareProviderTaxonomy                                                            |
| **E5** `PRM_LicenseService`                                               | `PRMDRTransformDelegatedBusinessLicense` (transform) + BusinessLicense part of the fused HCP DR                                                                                                                                      | Transform / Load                 | BusinessLicense                                                                       |
| **E6** `PRM_EducationService`                                             | `PRMDRTransformAddEducation` (transform) + `PRMDRPCreateEducation` (Load)                                                                                                                                                            | Transform / Load                 | PersonEducation                                                                       |
| **E7** `PRM_BoardCertificationService`                                    | `PRMDRPHCPNPIBoardCretIdentifier` (BoardCertification part)                                                                                                                                                                          | Load                             | BoardCertification                                                                    |
| **E8** `PRM_InfoCodeService`                                              | `PRMDRPCreateInfoCodeAssignments` (Load)                                                                                                                                                                                             | Load                             | PRM_InfoCodeAssignment__c                                                             |


> **DR "fusion" note:** `PRMDRPHCP…TaxonomyAndBusineessLicense` writes **HealthcareProvider + HealthcareProviderTaxonomy + BusinessLicense** in one DR, and `PRMDRPHCPNPIBoardCretIdentifier` writes **HealthcareProviderNpi + BoardCertification + Identifier** in one DR. In the new design those columns are split across E2/E4/E5/E7; the field maps below are partitioned accordingly.

---

## E0.1 Conventions (apply to every service — Parts 1–3)

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
| Account               | `PRM_Vendor`                           | E3 (group/vendor — Part 2) |
| Case                  | `PRM_PRM`                              | E1 (`caseRecordTypeId`) |
| IndividualApplication | `PRM_PractitionerParticipationRequest` | E1 (practitioner flow)  |
| IndividualApplication | `PRM_PDMManualChange`                  | E1 (PDM flow)           |
| IndividualApplication | `PRM_PNC`                              | E1 (`PNCFlag` true)     |
| Identifier            | `PRM_Practitioner`                     | E2                      |
| Identifier            | `PRM_Vendor`                           | E3 (Part 2)             |
| Identifier            | `PRM_Document`                         | E9 (file — Part 2)      |


> **✅ CL‑E5 resolved:** use the shared cached helper **`PRM_FormSubUtility.recordTypeId(SObjectType, devName)`** (a general method on the existing `PRM_FormSubUtility`, reusable by all E-services) to replace every `QUERY(...RecordType...)` formula — **not** a separate `PRM_RecordTypeUtil`. Removes 4+ SOQL/describe round-trips per submission.

---

## E0.4 PractitionerBatch build contract (AUTHORITATIVE — supersedes the per-service `jsonInput` snippets below)

> The E2–E11 / E16 sections below were authored against the **legacy DR grounding** and show a **single-record `jsonInput`** shape for traceability. The **build-ready contracts** now live in the per-service folder docs + execution plans (see the header note). **Where they differ, the folder docs win.** The conventions established there and applied across all `PractitionerBatch` services:

- **Bulk chunk input.** Each service's `execute(params)` receives **`params.practitioners[]`** — the batch chunk (one element per practitioner) — **not** a `jsonInput` JSON string. The service builds all records in memory and does **one bulk DML per object type** (no DML/SOQL in loops).
- **Batch-injected, SOQL-free services (`prm-service-class-boundaries` rule).** The batch (E20 `PRM_PractitionerBatch`) resolves and injects **all** context per node — `accountId`, `practitionerId` (PersonContactId), `caseManagerId`, `healthcareProviderId` (threaded from E2's output), and any reference Ids (e.g. E6 `degreeId`/`institutionId`, resolved in the batch by name/code). **Services do ZERO SOQL / no correlation / no source-format branching.** *(E2 keeps only the minimal lookups it owns; the E05–E08 service-side queries shown below are reconciled to this rule at E20 build.)*
- **Idempotency = NPI-anchored `PRM_RecordKey__c` upsert.** Retry re-runs the whole batch, so the record services are idempotent via a **`PRM_RecordKey__c`** External Id (Text(255), **Unique**, case-insensitive) built from **stable, NPI-anchored** inputs with a **`_`** delimiter → `upsert … PRM_RecordKey__c`. `HealthcareProviderNpi` uses an existence pre-check on the standard `Npi` (no new field); **E16 / E19 use existence pre-checks** (no `PRM_RecordKey__c`). NPI is **business-confirmed unique**.
- **E20 orchestration.** `start()` correlates by **NPI** and stamps context onto each node; it iterates **per practitioner** (Case Manager ↔ practitioner is **1:1**; `PRM_BatchSize__c` up to ~10 → up to 10 Case Managers per chunk). `execute()` runs **E2 → E5 (gated) → E6 (gated) → E19 (CMA) → E16 (CDM)**. **E7/E8/E10/E11 are deferred** until the source payload carries their data. **No rollback** on a service failure — the CDM records `*Exception__c`; idempotent retry recovers.
- **CMA (E19) + CDM (E16) wiring.** E20 aggregates CMA requests from **E2** (Identifier, Taxonomy) + **E5** (BusinessLicense) → **one** `PRM_CMAService` call; the **Practitioner CMA is created by E1** at intake. E16 receives **batch-supplied outcomes** `{caseManagerId, created[], failed[]}` and writes **one CDM manifest per Case Manager** (created→flag `true`, failed→`*Exception__c` `true`), running **last**.

---

## E1 · `PRM_CaseService` — *2.5 d* · Branch: BOTH · *(sync intake — BULK)*

> **🔄 Async-only revision — E1 runs at SYNCHRONOUS intake (the "Case Manager Service") and is BULK.** Unlike E2–E18, `PRM_CaseService` is **not** hosted in a batch. The IP intake wrapper (EPIC F) calls it **once per submission**, passing an **array of applications** (a submission can carry **N practitioners** — form or CSV). The service creates **one Case Manager (`IndividualApplication`) per practitioner** in **bulk** (one DML per object type across all N), and returns the created `caseManagerId`s; the wrapper seeds **one `PRM_AsyncJobRecords__c` row per Case Manager**. Only after this does the wrapper insert `PRM_AsyncJob__c` and let the batches run. It still `extends PRM_ServiceBase` / `execute(params)`, so it's reusable from a batch if ever needed — but in this design it executes at intake.

> **⚠ Bulkification is mandatory (no DML/SOQL in loops).** A single invocation processes the whole `applications[]` array: build all in-memory records across every application first, then do **one bulk DML per object type** (and per back-link update). Record-type/describe lookups are cached once (not per row). The circular-FK back-links (below) are correlated per-application via an index/wrapper so the bulk updates stay aligned.

**Legacy:** `PRMDRCreateCaseCaseManagerAndAccount` (Load). **Writes:** `Account` (Practitioner), `Case`, `IndividualApplication` (= the "Case Manager" record) — **one set per application**.

**Method signature** — `extends PRM_ServiceBase`; input and output are both `Map<String,Object>`. The input map carries `**flow`** (routing/context — a top-level map element) and `**jsonInput**` (the business payload as a JSON string). `jsonInput` holds an **`applications[]` array**; each element has the two nodes `**caseManagerInfo`** + `**practitionerInfo**`. All formula fields (record types, `caseType`, `CredentialingStatusVal`, gender, `AppliedDate`) are computed **inside the service**, per application, not supplied.

```apex
public with sharing class PRM_CaseService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');         // separate map element, e.g. 'PractitionerCreation'
        String jsonInput = (String) params.get('jsonInput');    // business payload (JSON string)
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        List<Object> applications = (List<Object>) input.get('applications');   // N practitioners

        // cache record-type Ids ONCE (Account/Case/IA) — never per row
        // accumulators across ALL applications (bulk):
        List<Account> accounts = new List<Account>();
        List<IndividualApplication> ias = new List<IndividualApplication>();
        List<Case> cases = new List<Case>();

        for (Object o : applications) {
            Map<String, Object> app = (Map<String, Object>) o;
            Map<String, Object> caseManagerInfo  = (Map<String, Object>) app.get('caseManagerInfo');
            Map<String, Object> practitionerInfo = (Map<String, Object>) app.get('practitionerInfo');
            // compute per-application formulas (caseType, credentialingStatus, gender, appliedDate, RTs)
            // build Account + IndividualApplication + Case in memory; track them per index for back-links
        }

        // ONE bulk DML per object type, in FK order + back-link updates (see "DML / order")

        response = new Map<String, Object>();                   // protected base field
        // response.put('applications', [ { practitionerAccountId, caseId, caseManagerId }, ... ]);
        // response.put('caseManagerIds', <List<Id>>);   // seeds one PRM_AsyncJobRecords__c per practitioner
        return response;
    }
}
```

**Expected `jsonInput` format** — an **`applications[]`** array; each element has the two nodes `**caseManagerInfo`** (Case + IndividualApplication fields) and `**practitionerInfo**` (Account/practitioner fields). `flow` is **not** in the JSON — it is a separate element of the `params` map. Formula-derived fields are computed in the service (per application) and are **not** supplied.

```json
{
  "applications": [
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
  ]
}
```

> The array carries **one element per practitioner**; the service iterates `applications[]` and produces one Account + Case + IndividualApplication per element, all committed in bulk.

> **Service-computed (do NOT send):** `Account.RecordTypeId` / `Case.RecordTypeId` / `IndividualApplication.RecordTypeId` (resolved by DeveloperName), `Case.Type` (`caseType`), `Account.PRM_CredentialingStatus__c` (`CredentialingStatusVal` from `practitionerInfo.practitionerCreationType`), `Account.PersonGenderIdentity` / `HealthCloudGA__Gender__pc` (from `practitionerInfo.gender`), `IndividualApplication.AppliedDate` (defaults to `NOW()` if blank). FK fields (`Case.AccountId`, `Case.PRM_CaseManager__c`, `IndividualApplication.AccountId`/`ApplicationCaseId`, `Account.PRM_CaseManager__c`) are set **in-service** across the insert + back-link steps.

> **Field coverage check (every JSON attribute maps to a Field-map row):** `caseManagerInfo.*` → IndividualApplication + Case fields; `practitionerInfo.*` → Account fields; `flow` → `params` element (used by `caseType`/RT/gender formulas as `flowType` too). `title` is the UI label for `providerRole` → `Account.PRM_ProviderRole__c`; `id` = existing practitioner Account (existing-NPI path).

**Field map (grounded — applies per `applications[]` element):**


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

**DML / order (BULK across all `applications[]` — circular FK, insert then back-link):**

Build the in-memory records for **every** application first (correlated per index via a wrapper), then run **one bulk DML per step** over the whole set:

1. **Insert all `Account`s** (one per application, from each `practitionerInfo`) — single bulk insert.
2. **Insert all `IndividualApplication`s** — FK `AccountId` → the corresponding Account.Id — single bulk insert.
3. **Insert all `Case`s** — FK `PRM_CaseManager__c` → the corresponding IndividualApplication.Id — single bulk insert.
4. **Update all `IndividualApplication`s** — `ApplicationCaseId` → the corresponding Case.Id — single bulk update.
5. **Update all `Account`s** — `PRM_CaseManager__c` → the corresponding IndividualApplication.Id — single bulk update.

Account, Case, and IndividualApplication reference each other (Case→IA, IA→Case, Account→IA), so the back-links require the two trailing bulk updates. **Per-application correlation:** keep a wrapper/index list (e.g. `List<AppRecords{ acc; ia; cse }>`) so each insert result feeds the right FK in the next step — never re-query inside the loop. **Returns** a per-application result list `applications[] = [ { practitionerAccountId, caseId, caseManagerId (= IndividualApplication.Id) }, … ]` (input order preserved) plus a flat `caseManagerIds` list for the wrapper to seed one `PRM_AsyncJobRecords__c` row per practitioner.

> **Partial-failure note:** with one bulk DML across N applications, decide the failure policy at intake — all-or-nothing (a single bad row rolls back the whole submission) vs. `Database.insert(records, false)` with per-row error capture. Recommended for intake: **all-or-nothing** (so a malformed submission is rejected atomically before any async job is queued); confirm during EPIC F build.

---

## E2 · `PRM_PractitionerService` — *2.5 d* · Branch: BOTH · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E02_PRM_PractitionerService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; batch-injected context; **NPI-anchored `PRM_RecordKey__c` upsert** for HCP/Identifier/Taxonomy (`{npi}`, `{npi}_{type}_{idValue}`, `{npi}_{taxonomyCode}`), existence pre-check on `Npi` for HealthcareProviderNpi. The legacy field maps below remain valid.

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

## E4 · `PRM_TaxonomyService` — **merged into E2** (removed)

`HealthcareProviderTaxonomy` is created by the same fused DR that E2 owns (`PRMDRPHCP…TaxonomyAndBusineessLicense`), so for Practitioner Creation there is **no standalone taxonomy service** — see the **HealthcareProviderTaxonomy field map + transform formulas in E2**. The `PRM_TaxonomySelector.getTaxonomyRefs(Set<String> codes)` (EPIC D) is still used inside E2 to resolve `TaxonomyId` from codes. (Reintroduce a standalone E4 only if a future flow needs taxonomy-only creation.)

---

## E5 · `PRM_LicenseService` — *0.5 d* · Branch: BOTH · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E05_PRM_LicenseService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; batch-injected context; **NPI-anchored `PRM_RecordKey__c` upsert** on `BusinessLicense`. ⚠ `licenseType` is a key component still missing from the source payload (OQ-E5/OQ-E20-9). The legacy field map below remains valid.

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

## E6 · `PRM_EducationService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E06_PRM_EducationService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; **NPI-anchored `PRM_RecordKey__c` upsert** on `PersonEducation`. The **batch resolves `degreeId`/`institutionId`** in `start()` (`PRM_Degree__c` by `PRM_DegreeCode__c`, `PRM_Institution__c` by `Name`; no create for unmatched) and injects them — the service does no lookup. The legacy field map below remains valid.

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

## E7 · `PRM_BoardCertificationService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E07_PRM_BoardCertificationService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; batch-injected context; **NPI-anchored `PRM_RecordKey__c` upsert** on `BoardCertification`. **Deferred in E20** until the source payload carries `boardCertifications`. The legacy field map below remains valid.

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

## E8 · `PRM_InfoCodeService` — *1.5 d* · Branch: BOTH (gated) · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E08_PRM_InfoCodeService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; batch-injected context; **NPI-anchored `PRM_RecordKey__c` upsert** on `PRM_InfoCodeAssignment__c`. **Deferred in E20** (practitioner-grain `infoCodes` not in the current payload). The legacy field map below remains valid.

**Legacy:** `PRMDRPCreateInfoCodeAssignments` (Load — straight map, no formulas). **Writes:** `PRM_InfoCodeAssignment__c`. Two methods per plan: `createIfPresent(infoCodes)` (practitioner-grain, here) and `prepareBulkForLocations(addresses)` (facility-grain — Part 3 §E14 sibling).

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


**Gating / DML:** runs only when `infoCodes` is non-empty (gated no-op otherwise); single bulk insert. Returns `infoCodeAssignmentIds`. *(The facility-grain `prepareBulkForLocations(addresses)` method is detailed alongside §E14 in Part 3.)*

---

## E10 · `PRM_ContactService` — *1.0 d* · Branch: DELEGATED · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E10_PRM_ContactService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; **strictly batch-injected, SOQL-free** (`accountId`/`practitionerId`/`caseManagerId` injected); **NPI-anchored `PRM_RecordKey__c` upsert** on `ContactProfile`. **Deferred in E20** (`providerInformation` not in the current payload). The legacy field map below remains valid.

> **⚠ CL‑E2‑1:** the active DR writes the `**ContactProfile`** object (HC data model), **not** `Contact`. The map below is the grounded `ContactProfile` shape; reconcile the plan/flow docs.

**Legacy:** `PRMDRCreateContactProfileRecords` (Load) + `PRMDRTransformProviderInformationData` — element `CreateContactProfileRecords` in `PRM_DelegatedCreateProviderScreenRecords` v1. **Writes:** `ContactProfile`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput`**, and the FK Ids `accountId` (→ `PRM_PersonAccount__c`), `practitionerId` (→ `ContactId`), `caseManagerId`.

```apex
public with sharing class PRM_ContactService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        Map<String, Object> providerInformation = (Map<String, Object>) input.get('providerInformation');
        Map<String, Object> pronouns = (Map<String, Object>) input.get('providerInformationPersonalPronouns');
        // FK Ids from params; build ContactProfile (demographic defaults); upsert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format:**

```json
{
  "providerInformation": {
    "RacialIdentity": "", "CulturalIdentityAPI": "", "IdentifyasHispanic": "", "HispanicOriginAPI": "",
    "RacialIdentityConfirmation": "", "CulturalIdentityConfirmation": "", "HispanicOriginConfirmation": "", "ConfirmationQuestion1": ""
  },
  "providerInformationPersonalPronouns": { "PersonalPronouns": "", "PronounNotListed": "" }
}
```

### (`PRM_DelegatedCreateProviderScreenRecords` → `CreateContactProfileRecords`)


| DR input                              | IP source                                     | E10 mapping                           |
| ------------------------------------- | --------------------------------------------- | ------------------------------------- |
| `PersonAccountId`                     | `PractitionerScreenRecordIds:AccountId`       | `params.accountId`                    |
| `ContactId`                           | `PractitionerScreenRecordIds:PersonContactId` | `params.practitionerId`               |
| `CaseManagerId`                       | `PractitionerScreenRecordIds:CaseManagerId`   | `params.caseManagerId`                |
| `ProviderInformation`                 | `ProviderInformation` node                    | `providerInformation`                 |
| `ProviderInformationPersonalPronouns` | `ProviderInformationPersonalPronouns` node    | `providerInformationPersonalPronouns` |


**Field map (grounded):**


| ContactProfile field                                                                                                                                   | Source                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PRM_PersonAccount__c`                                                                                                                                 | `params.accountId` **[upsert KEY]**                                                                                                                       |
| `ContactId`                                                                                                                                            | `params.practitionerId` **[upsert KEY]**                                                                                                                  |
| `PRM_CaseManager__c`                                                                                                                                   | `params.caseManagerId`                                                                                                                                    |
| `Race`                                                                                                                                                 | `providerInformation.RacialIdentity`                                                                                                                      |
| `PRM_Ethnicity__c`                                                                                                                                     | `providerInformation.CulturalIdentityAPI` (⟲ default `"Prefer not to share"`)                                                                             |
| `PRM_HispanicLatino__c`                                                                                                                                | `providerInformation.IdentifyasHispanic`                                                                                                                  |
| `PRM_HispanicOrigin__c`                                                                                                                                | `providerInformation.HispanicOriginAPI`                                                                                                                   |
| `PRM_PersonalPronoun__c` / `PRM_PersonalPronounNotListed__c`                                                                                           | `providerInformationPersonalPronouns.PersonalPronouns` / `PronounNotListed`                                                                               |
| `PRM_RaceIsDirectoryPrint__c` / `PRM_EthnicityIsDirectoryPrint__c` / `PRM_HispanicOriginIsDirectoryPrint__c` / `PRM_HispanicLatinoIsDirectoryPrint__c` | ⟲ `IF(ISNOTBLANK(x), x, false)` on `RacialIdentityConfirmation` / `CulturalIdentityConfirmation` / `HispanicOriginConfirmation` / `ConfirmationQuestion1` |
| `PRM_LastUpdatedByProvider__c`                                                                                                                         | ⟲ formula `NOW()` → `System.now()`                                                                                                                        |


**Formulas → Apex:** confirmation flags default blanks to `false` (`x != null ? x : false`); `CulturalIdentityAPI` defaults to `"Prefer not to share"`. **DML:** single upsert by (`PRM_PersonAccount__c`, `ContactId`). Returns `contactProfileId`.

---

## E11 · `PRM_LanguageService` — *0.5 d* · Branch: DELEGATED (gated) · *(PractitionerBatch)*

> **🔄 Build spec (authoritative):** `PractitionerBatch Related Services/E11_PRM_LanguageService.md` (+ `_Execution_Plan.md`). Per §E0.4: bulk `practitioners[]` chunk; **strictly batch-injected, SOQL-free** (`healthcareProviderId`/`caseManagerId` injected); **NPI-anchored `PRM_RecordKey__c` upsert** (`{npi}_{language}`) on `PersonLanguage`. ⚠ `Language` is a required **ISO-code** picklist → map name→code at batch/intake (OQ-E11-3). **Deferred in E20** (`languages` not in the current payload). The legacy field map below remains valid.

**Legacy:** `PRMDRCreatePersonLanguage` (Load) — element `DRCreatePersonlanguage` in `PRM_DelegatedCreateProviderScreenRecords` v1. **Writes:** `PersonLanguage`.

**Method signature** — `extends PRM_ServiceBase`; `Map<String,Object>` in/out. `params` carries `**flow`**, `**jsonInput`**, and the FK Ids `accountId` (→ `IndividualId`), `healthcareProviderId` (from E2 → `PRM_HealthcareProvider__c`), `caseManagerId`.

```apex
public with sharing class PRM_LanguageService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped((String) params.get('jsonInput'));
        List<Object> languages = (List<Object>) input.get('languages');
        if (languages == null || languages.isEmpty()) { response = new Map<String,Object>(); return response; }
        // FK Ids from params; build PersonLanguage[]; bulk insert.
        response = new Map<String, Object>();
        return response;
    }
}
```

**Expected `jsonInput` format:**

```json
{
  "languages": [
    { "value": "English", "shareInDir": true, "lastUpdatedOn": "" }
  ]
}
```

### (`PRM_DelegatedCreateProviderScreenRecords` v1 → `DRCreatePersonlanguage`)

`Languages` ← the `Languages` node (each row pre-enriched in the legacy with `AccountId` / `HealthCareProviderId` / `CaseManagerId`). In the new design those FK Ids come from `params` (not the row).

**Field map (grounded):**


| PersonLanguage field            | Source                                                                  |
| ------------------------------- | ----------------------------------------------------------------------- |
| `IndividualId`                  | `params.accountId` (legacy `Languages:AccountId`)                       |
| `PRM_HealthcareProvider__c`     | `params.healthcareProviderId` (legacy `Languages:HealthCareProviderId`) |
| `Language` / `Name`             | `languages[].value`                                                     |
| `Rank`                          | ⟲ formula (sequence)                                                    |
| `PRM_ShareInPublicDirectory__c` | `languages[].shareInDir`                                                |
| `PRM_LastUpdatedByProvider__c`  | `languages[].lastUpdatedOn`                                             |
| `PRM_CaseManager__c`            | `params.caseManagerId` (legacy `Languages:CaseManagerId`)               |


**Gating / DML:** only when `languages` non-empty; single bulk insert. Returns `personLanguageIds`.

---

## E19 · `PRM_CMAService` — Branch: BOTH · *(PractitionerBatch — cross-cutting; runs after E2/E5/E6)*

> **🔄 Build spec (authoritative):** `E19_PRM_CMAService.md` (+ `_Execution_Plan.md`). Cross-cutting service **wired into `PractitionerBatch` by E20** (built; class exists). **Writes:** `PRM_CaseManagerAssociation__c` — already exists in the org; **no new fields** (idempotency via pre-check).

- **Purpose:** create the junction rows that link created/updated records to their **Case Manager** — one row per primary record per Case Manager, carrying the **record type** + available contextual lookups.
- **Invoked once per chunk by E20** with an aggregated `associations[]` built from **E2's** output (Identifier, Taxonomy) and **E5's** output (BusinessLicense). The **Practitioner CMA is created by E1** at intake — E20 does **not** re-create it; **E6 (PersonEducation) has no CMA** record type.
- **Idempotency = existence pre-check** on `(PRM_CaseManager__c + RecordType + primary lookup Id)`; bulk-safe (one pre-check SOQL + one FLS-safe, all-or-nothing insert). Record-type→field-set mapping and cached `RecordType` resolution live on `PRM_FormSubUtility` (`cmaFieldSet` / `recordTypeId`).
- **Input:** `params.associations[]` of `{ caseManagerId, recordType, lookups{field→Id}, requestType? }`. **Output:** `{ caseManagerAssociationIds: [...] }`.
- **Access:** CRUD on `PRM_CaseManagerAssociation__c` + FLS on its lookups via `PRM_AsyncJob_Access` (E19 §3).

---

## E16 · `PRM_CaseDataManagerService` — *1.5 d* · Branch: BOTH · *(PractitionerBatch — runs LAST)*

> **🔄 Updated design (authoritative): `E16_PRM_CaseDataManagerService.md` (+ `_Execution_Plan.md`).** The legacy **payload-presence** model is **superseded** — E16 now consumes **batch-supplied outcomes** and writes a per-Case-Manager manifest. The legacy flag-derivation grounding is retained below for traceability only.

**Legacy (coalesced):** `PRMDRCreateCDM` + `PRMDRCreateCDMForPractitioner` + `PRMDRPCDMCaseManagerLink` — **2–4 separate CDM DMLs** → **one bulk INSERT + one bulk UPDATE.** **Writes:** `PRM_CaseDataManager__c` — the per-case **manifest** of which record types were created / failed.

**Updated contract (folder doc — supersedes the legacy model):**

- **Input = batch-supplied outcomes (not payload presence).** `params.practitioners[]`, each `{ caseManagerId, created[], failed[] }` where `created`/`failed` are **record-type tokens**. Runs **last** in `PractitionerBatch` (after E2/E5/E6/E19), so the actual created/failed outcomes are known.
- **Idempotency = existence on `PRM_CaseManager__c`** — the identity (a **required** lookup → `IndividualApplication`, **createable-only**); **no `PRM_RecordKey__c`**. One bulk query of existing CDMs → reuse (**UPDATE**) or new (**INSERT**). Re-run safe; **one CDM per Case Manager** (= per practitioner; CM ↔ practitioner is **1:1**).
- **64 non-nillable booleans** (34 record-type + 30 `*Exception__c`, org-validated). **INSERT** defaults **all 64** to `false` then sets this batch's flags; **UPDATE** touches **only** this batch's flags (later batches own theirs). A token in `created[]` → its flag `true`; in `failed[]` → its `*Exception__c` `true` (4 demographics flags have **no** exception → no-op). The token→field map is **explicit** (names differ) — see the E16 doc §6.
- **DML split (not `upsert`).** `PRM_CaseManager__c` is createable-only, so a blind `upsert`/`UPSERTABLE` strip would drop it → **one bulk INSERT + one bulk UPDATE**, FLS-safe (`stripInaccessible` + identity assert).
- **E20-owned decisions (resolved):** **1:1** → no chunk-grouping needed (OQ-E16-1); E20 **always emits the `PersonAccount` token** (OQ-E16-3); **per-record** exception grain required → depends on E20 + E2/E5/E6 capturing per-record failures (**CL-E16-A**).
- **Output:** `response.practitioners[]` (input order) `{ caseManagerId, caseDataManagerId }`.

> Full reference implementation (token map, init-all-false, split insert/update, FLS asserts) + execution plan are in the E16 folder docs.

### (Legacy `PRMDRCreateCDMForPractitioner` flag derivation — IBC v3 & Delegated v7 — grounding only)

> **Superseded** by the batch-supplied token model above; kept to trace which payload node historically drove each flag. Each legacy flag was `IF(<payload node present>, true, null)`:


| CDM flag                                                                                                                                  | Set true when (IP source)                                            | Derive from                    |
| ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------ |
| `PRM_Account__c` / `PRM_PersonAccount__c`                                                                                                 | `RecordsToUpdate:PractionerDetails` present                          | `practitionerInfo` (E1/E2)     |
| `PRM_HealthCareProvider__c` (`Hcp`) / `PRM_HealthCareProviderTaxonomy__c`                                                                 | `RecordsToUpdate:HCPTaxonomy` present                                | `taxonomies` (E2)              |
| `PRM_HealthCareProviderNPI__c` (`Npi`)                                                                                                    | `RecordsToUpdate:HCPNPI` present                                     | `practitionerInfo.npi` (E2)    |
| `PRM_Identifier__c`                                                                                                                       | `RecordsToUpdate:Identifiers` present                                | `identifiers` (E2)             |
| `PRM_BusinessLicense__c`                                                                                                                  | `ISNOTBLANK(RecordsToUpdate:BusinessLicense)`                        | `businessLicenses` (E5)        |
| `PRM_PersonEducation__c`                                                                                                                  | `LISTSIZE(RecordsToUpdate:AddEducation) >= 1`                        | `education` (E6)               |
| `PRM_BoardCertification__c`                                                                                                               | `RecordsToUpdate:BoardCertifications` present                        | `boardCertifications` (E7)     |
| `PRM_InfoCodeAssignment__c`                                                                                                               | `RecordsToUpdate:InfoCodeIds` present                                | `infoCodes` (E8)               |
| `PRM_ContactProfile__c`                                                                                                                   | any `ProviderInformation:*Confirmation` present                      | `providerInformation` (E10)    |
| `PRM_PersonLanguage__c` (`Language`)                                                                                                      | `…LanguageConfirmQuestion` present                                   | `languages` (E11)              |
| `PRM_ProviderFeature__c` / `PRM_HealthcareFacilityNetwork__c` (`Hfn`) / `PRM_HealthCarePractitionerFacility__c` (`PracticeLocationPract`) | `RecordsToUpdate:Locations` present (IBC: `PracticeLocationDetails`) | `locations` (E12–E15)          |
| `PRM_CaseManager__c`                                                                                                                      | `DRPAccountCaseCaseManagerCreation:CaseManagerId`                    | `params.caseManagerId`         |
| `CDMId` (existing)                                                                                                                        | `PRMDRCreateCDM:CDMId`                                               | selector `getCDMByCaseManager` |


> `PRMDRPCaseDataManager` additionally exposes `Is*Upsert` booleans (`PRM_Address__c`, `PRM_Location__c`, `PRM_HealthCareFacility__c`, `PRM_ContentVersion__c`, vendor `PRM_Account__c`, …) for the locations/async sub-blocks — set the same way (presence/created).

**Existing-vs-new (updated):** resolved by a **bulk existence query** on `PRM_CaseManager__c` (the chunk's Case Managers) → reuse the found CDM (UPDATE) or build a new one (INSERT). *(Supersedes the legacy single-record `getCDMByCaseManager` lookup.)*

**DML (updated):** **one bulk INSERT + one bulk UPDATE** of `PRM_CaseDataManager__c` per chunk (eliminates the legacy 2–4 CDM writes → no `UNABLE_TO_LOCK_ROW` under load). Returns `caseDataManagerId` per practitioner. See the E16 folder doc for the complete reference implementation.

---

## E.Effort (Part 1 — intake + PractitionerBatch)


| Service                                                         | Est (d)            |
| --------------------------------------------------------------- | ------------------ |
| E1 `PRM_CaseService` *(sync intake — bulk, array of applications)* | 2.5            |
| E2 `PRM_PractitionerService` (incl. HealthcareProviderTaxonomy) | 2.5                |
| E4 `PRM_TaxonomyService`                                        | — (merged into E2) |
| E5 `PRM_LicenseService`                                         | 0.5                |
| E6 `PRM_EducationService`                                       | 0.5                |
| E7 `PRM_BoardCertificationService`                              | 0.5                |
| E8 `PRM_InfoCodeService`                                        | 1.5                |
| E10 `PRM_ContactService`                                        | 1.0                |
| E11 `PRM_LanguageService`                                       | 0.5                |
| E19 `PRM_CMAService` *(cross-cutting CMA; wired into PractitionerBatch)* | see `E19_PRM_CMAService.md` |
| E16 `PRM_CaseDataManagerService`                                | 1.5                |
| **Total (Part 1)**                                              | **11.0** (+ E19 — see E19 doc) |


> **EPIC E grand total (Part 1 + Part 2 + Part 3) ≈ 23.5 d** — Part 1 11.0 · Part 2 6.5 · Part 3 6.0.

---

## E.CL — Clarification Log (Part 1 services)

> CL ref IDs are preserved from the pre-reorg layout so existing cross-references resolve. Entries for services that moved into Part 1 from the old Part 2 (E10, E16) keep their `CL‑E2‑*` IDs.


| Ref   | Item                                                                                                                                                                                                                                                                                                                     | Evidence                                                                                                                                                  | Action                                                                                                                                                                                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL‑E1 | **IBC NPI/Identifier source.** Active IBC IP (`PRM_PractitionerCreation` v3) creates HealthcareProvider but **no** NPI/Identifier DR. Decision: keep E2 creating them for both branches.                                                                                                                                 | IBC IP DR set = CaseCaseManagerAndAccount, HCProviderHCProviderTaxonomyAndBusineessLicense, PCreateInfoCodeAssignments, PPractionerPracticeLocations, CDM | Confirm IBC NPI/Identifier field values during E2 build (default: reuse Delegated map) — Tech Lead                                                                                                          |
| CL‑E2 | **IA RecordType ordinal mapping.** Legacy uses `recordTypeList                                                                                                                                                                                                                                                           | 3/                                                                                                                                                        | 4`after`ORDER BY SobjectType ASC, DeveloperName DESC`. New design resolves by DeveloperName; the Practitioner-flow IA RT (`PRM_PDMManualChange`vs`PRM_PractitionerParticipationRequest`) must be confirmed. |
| CL‑E3 | **Education "Completed" picklist field API.** DR formula alias `CompletedPicklist`; target field API not in the map.                                                                                                                                                                                                     | `PRMDRPCreateEducation`                                                                                                                                   | Confirm `PersonEducation` picklist API name — Eng                                                                                                                                                           |
| CL‑E4 | **Legacy DR fusion vs services.** HCP+Taxonomy+License and NPI+BoardCert+Identifier are each one DR; new design splits them. Field maps partitioned here.                                                                                                                                                                | fused DRs                                                                                                                                                 | Confirmed: keep fine-grained split (ratified)                                                                                                                                                               |
| CL‑E5 | `**RecordType` helper home.** Replacing `QUERY(...)` formulas needs a cached describe helper; its class home is TBD.                                                                                                                                                                                                     | TDD CL‑13                                                                                                                                                 | Decide helper home before E1 — Tech Lead                                                                                                                                                                    |
| CL‑E8 | **License payload shape.** E5 uses one unified `businessLicenses[]` (with `licenseType`), collapsing the legacy two-block (`DEACDS`/`SBRD`) + `PRMDRTransformDelegatedBusinessLicense` + `LA_MergeBusinessLicense`. Confirm the OmniScript emits a single array (else normalize the two blocks in `PRM_FormSubUtility`). | `PRMDRTransformDelegatedBusinessLicense`                                                                                                                  | Confirm payload shape in EPIC F — Eng                                                                                                                                                                       |
| CL‑E9 | **InfoCode id resolution.** E8's `infoCodes[].id` are resolved InfoCode record Ids (legacy `%InfoCodeIds%` from a prior step). Confirm whether the payload sends resolved Ids or codes needing selector resolution.                                                                                                      | element `DRPCreateInfoCodeAssignments`                                                                                                                    | Confirm/resolve via selector before E8 — Eng                                                                                                                                                                |
| CL‑E2‑1 | **Contact vs ContactProfile.** Active DR writes `ContactProfile`, not `Contact`.                                                                                                                                                                                                                                  | `PRMDRCreateContactProfileRecords` (objs=`ContactProfile`)                           | Reconcile plan/flow docs to `ContactProfile`; confirm object — Tech Lead                                                                           |
| CL‑E2‑3 | **CDM derivation — RESOLVED.** Superseded by **batch-supplied outcomes**: E16 sets flags from the batch's `created[]`/`failed[]` tokens (created→flag, failed→`*Exception__c`), **not** payload presence. Org-validated: 64 non-nillable booleans. | `E16_PRM_CaseDataManagerService.md` §2/§4/§6 | ✅ Resolved — outcomes contract; token→field map in E16 doc |
| CL‑E2‑12 | **CDM timing across batches — RESOLVED.** E16 runs **last in each batch** (PractitionerBatch first), inserting the CDM with all flags `false` + its own flags, later batches **update** their own flags (option a). One CDM per Case Manager (CM↔practitioner 1:1). | `E16…md` §8 (option a); E20 §9 | ✅ Resolved — per-batch update accumulation |
| CL‑E16‑A | **Per-record failure capture (dependency).** E16's `failed[]` is per practitioner; the confirmed **per-record** exception grain requires **E20 + E2/E5/E6** to capture per-record failures (partial-success DML) rather than a whole-call throw. **Not an E16 code task.** | `E16…_Execution_Plan.md` §5/§6; E20 | Raise/track against E20 + E2/E5/E6 designs — Tech Lead |


---

> **Part 2 (PracticeLocationAndGroupBatch — E3 · E13 · E9 · E12):** see `**Epic_E_Practitioner_Services_Part2.md`**.
> **Part 3 (PLRelatedBatch + Level4RecordCreationBatch + GroupRelatedBatch TBD — E14 · E15 · E18; ~~E17~~ dropped):** see `**Epic_E_Practitioner_Services_Part3.md`**.
