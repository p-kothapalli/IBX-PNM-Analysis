# E01 · `PRM_CaseService` — *2.5 d* · Branch: BOTH · *(sync intake — BULK)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1 — intake + PractitionerBatch). Shared conventions (ServiceBase signature, in-memory build + one bulk DML/type, selectors, `NameNormalize`, RecordType-by-describe) are in **Part 1 §E0.1–E0.2** and apply here unchanged.
> **Batch:** none — runs at **synchronous intake** (the "Case Manager Service"). **Writes:** `Account` (Practitioner), `Case`, `IndividualApplication` (= the "Case Manager" record) — one set per application.
> **Legacy:** `PRMDRCreateCaseCaseManagerAndAccount` (Load).

---

## 1. Role & cardinality

> **🔄 E1 runs at SYNCHRONOUS intake and is BULK.** Unlike E2–E18, `PRM_CaseService` is **not** hosted in a batch. The IP intake wrapper (EPIC F) calls it **once per submission**, passing an **array of applications** (a submission can carry **N practitioners** — form or CSV). The service creates **one Case Manager (`IndividualApplication`) per practitioner** in **bulk** (one DML per object type across all N) and returns the created `caseManagerId`s; the wrapper seeds **one `PRM_AsyncJobRecords__c` row per Case Manager**. Only after this does the wrapper insert `PRM_AsyncJob__c` and let the batches run. It still `extends PRM_ServiceBase` / `execute(params)`, so it's reusable from a batch if ever needed — but in this design it executes at intake.

> **⚠ Bulkification is mandatory (no DML/SOQL in loops).** A single invocation processes the whole `applications[]` array: build all in-memory records across every application first, then do **one bulk DML per object type** (and per back-link update). Record-type/describe lookups are cached once (not per row). The circular-FK back-links (§5) are correlated per-application via an index/wrapper so the bulk updates stay aligned.

---

## 2. Method signature & contract

`extends PRM_ServiceBase`; input and output are both `Map<String,Object>`. The input map carries `**flow**` (routing/context — a top-level map element) and `**jsonInput**` (the business payload as a JSON string). `jsonInput` holds an **`applications[]` array**; each element has the two nodes `**caseManagerInfo**` + `**practitionerInfo**`. All formula fields (record types, `caseType`, `CredentialingStatusVal`, gender, `AppliedDate`) are computed **inside the service**, per application, not supplied.

| | |
|---|---|
| **Input `params.flow`** | `String` — routing/context (e.g. `'PractitionerCreation'`); used by `caseType`/RT/gender formulas |
| **Input `params.jsonInput`** | `String` (JSON) — `{ "applications": [ { caseManagerInfo, practitionerInfo }, … ] }` |
| **Output `response.applications`** | `List<Map<String,Object>>` — one per input element, **input order preserved**: `{ practitionerAccountId, caseId, caseManagerId }` |
| **Output `response.caseManagerIds`** | `List<Id>` — flat list of `IndividualApplication` Ids (= Case Managers) for the wrapper to seed `PRM_AsyncJobRecords__c` |

> **Return is what the wrapper needs for the async records (F‑10):** per practitioner, **`AccountId` + `CaseManagerId`** — the wrapper uses them to create `PRM_AsyncJob__c` + one `PRM_AsyncJobRecords__c` per Case Manager and to **enrich the stored payload** so the batches' `practitionerInfo.id` = the E1 Account Id. **`PersonContactId` is not returned** (E2 resolves it from the Account).

### 2.1 Correlation — keeping each `caseManagerInfo` with its `practitionerInfo` across the 5 DMLs

The records for one application land in **different** bulk DMLs (Account, IA, Case, + 2 back-link updates). They are kept aligned with a **per-application unit-of-work wrapper that holds the three record _references_** — no index math, no re-queries.

> **Why references work:** Apex DML writes the resulting `Id` back onto the **exact object instances** passed to `insert`/`update` (in list order). Because the wrapper holds those same instances, `u.acc.Id` / `u.ia.Id` / `u.cse.Id` become available to the next step automatically — the wrapper *is* the correlation key. (List order is a secondary guarantee.)

### 2.2 Reference implementation

```apex
public with sharing class PRM_CaseService extends PRM_ServiceBase {

    // one per applications[] element, built in input order — holds the 3 record references
    @TestVisible
    private class AppUow {
        Account acc;
        IndividualApplication ia;
        Case cse;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        String flow      = (String) params.get('flow');
        String jsonInput = (String) params.get('jsonInput');
        Map<String, Object> input = (Map<String, Object>) JSON.deserializeUntyped(jsonInput);
        List<Object> applications = (List<Object>) input.get('applications');

        // 1) cache record-type Ids ONCE (never per row) — via PRM_FormSubUtility.recordTypeId (CL-E5 resolved)
        Id accRt  = PRM_FormSubUtility.recordTypeId(Account.SObjectType, 'PRM_Practitioner');
        Id caseRt = PRM_FormSubUtility.recordTypeId(Case.SObjectType, 'PRM_PRM');   // IA RT resolved per-app (PNC/flow)

        // 2) build one UoW per application, in input order (no DML in this loop)
        List<AppUow> uows = new List<AppUow>();
        for (Object o : applications) {
            Map<String, Object> app = (Map<String, Object>) o;
            Map<String, Object> cm  = (Map<String, Object>) app.get('caseManagerInfo');
            Map<String, Object> p   = (Map<String, Object>) app.get('practitionerInfo');

            AppUow u = new AppUow();
            u.acc = buildAccount(p, cm, accRt, flow);
            u.ia  = buildIndividualApplication(cm, flow);
            u.cse = buildCase(cm, caseRt, flow);
            uows.add(u);
        }

        // 3) BULK DML — wrapper references carry Ids forward, so no re-correlation/re-query

        // 3a Accounts — all insert (existing-practitioner path is out of scope for now; see §6)
        List<Account> accIns = new List<Account>();
        for (AppUow u : uows) accIns.add(u.acc);
        insert accIns;   // populates Id on the SAME instances held by the UoWs

        // 3b IndividualApplications — FK from the now-populated Account reference
        List<IndividualApplication> iaIns = new List<IndividualApplication>();
        for (AppUow u : uows) { u.ia.AccountId = u.acc.Id; iaIns.add(u.ia); }
        insert iaIns;

        // 3c Cases — FK to Account + IA (the Case Manager)
        List<Case> caseIns = new List<Case>();
        for (AppUow u : uows) { u.cse.AccountId = u.acc.Id; u.cse.PRM_CaseManager__c = u.ia.Id; caseIns.add(u.cse); }
        insert caseIns;

        // 3d back-link: IA.ApplicationCaseId = Case.Id
        List<IndividualApplication> iaBack = new List<IndividualApplication>();
        for (AppUow u : uows) { u.ia.ApplicationCaseId = u.cse.Id; iaBack.add(u.ia); }
        update iaBack;

        // 3e back-link: Account.PRM_CaseManager__c = IA.Id
        List<Account> accBack = new List<Account>();
        for (AppUow u : uows) { u.acc.PRM_CaseManager__c = u.ia.Id; accBack.add(u.acc); }
        update accBack;

        // 3f) CMA — one "Practitioner CMA" per practitioner (Account ↔ Case Manager), in the SAME intake transaction (§5.1)
        List<Object> cmaRequests = new List<Object>();
        for (AppUow u : uows) {
            cmaRequests.add(new Map<String, Object>{
                'caseManagerId' => u.ia.Id,                                   // → PRM_CaseManager__c (required)
                'recordType'    => 'PRM_Practitioner',                        // CMA RecordType
                'lookups'       => new Map<String, Object>{ 'PRM_Account__c' => u.acc.Id }
            });
        }
        new PRM_CMAService().execute(new Map<String, Object>{ 'associations' => cmaRequests });
        // CMA = idempotent pre-check + all-or-nothing → a CMA failure rolls back the whole intake (atomic)

        // 4) response — input order preserved
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        List<Id> caseManagerIds = new List<Id>();
        for (AppUow u : uows) {
            results.add(new Map<String, Object>{
                'practitionerAccountId' => u.acc.Id,
                'caseId'                => u.cse.Id,
                'caseManagerId'         => u.ia.Id
            });
            caseManagerIds.add(u.ia.Id);
        }
        response = new Map<String, Object>{ 'applications' => results, 'caseManagerIds' => caseManagerIds };
        return response;
    }

    // ── builders (pure in-memory; formulas computed here — see §4) ──

    // Builds the Practitioner Person Account from practitionerInfo (+ PNC flag from caseManagerInfo).
    // All formula fields are computed here; no DML/SOQL/describe (rt is pre-resolved & passed in).
    private Account buildAccount(Map<String, Object> p, Map<String, Object> cm, Id rt, String flow) {
        Account a = new Account();
        a.RecordTypeId = rt;                                                   // RT 'PRM_Practitioner'

        // names — normalized (replaces legacy RA_TitleCase / PRM_OmniUtils.titleCase)
        a.FirstName  = PRM_FormSubUtility.NameNormalize((String) p.get('firstName'));
        a.MiddleName = PRM_FormSubUtility.NameNormalize((String) p.get('middleName'));
        a.LastName   = PRM_FormSubUtility.NameNormalize((String) p.get('lastName'));
        a.Suffix     = PRM_FormSubUtility.NameNormalize((String) p.get('suffix'));

        a.PersonEmail     = (String) p.get('email');
        a.PersonBirthdate = parseDate((String) p.get('dob'));

        // gender formulas (null for the PractitionerCreation flow — legacy parity)
        String gender = (String) p.get('gender');
        a.PersonGenderIdentity      = genderIdentity(gender, flow);            // M / F / Prefer not to share / U
        a.HealthCloudGA__Gender__pc = genderIdentityPc(gender, flow);         // Male / Female / Other

        a.HealthCloudGA__SourceSystemId__c = (String) p.get('npi');
        a.PRM_ProviderRole__c = (String) p.get('providerRole');               // UI label: 'title'
        a.PRM_CredentialingStatus__c = credentialingStatus((String) p.get('practitionerCreationType'));

        a.PRM_PNC__c   = toBool(cm.get('PNCFlag'));
        a.Type         = (String) p.get('accountType');
        a.IsActive     = toBool(p.get('isActive'));
        a.PRM_EffectiveFrom__c = parseDate((String) p.get('effectiveFrom'));
        a.PRM_EffectiveTo__c   = parseDate((String) p.get('effectiveTo'));
        a.PRM_DelegatedOnly__c = toBool(p.get('delegated'));                  // Boolean checkbox (verified IBXDEV01, required)
        return a;
    }

    // Builds the IndividualApplication (= "Case Manager") from caseManagerInfo.
    // RT varies per application (PNC / flow) — resolved via the cached PRM_FormSubUtility.recordTypeId (O(1), no SOQL per row).
    private IndividualApplication buildIndividualApplication(Map<String, Object> cm, String flow) {
        String  flowType = String.isNotBlank(flow) ? flow : (String) cm.get('flowType');
        Boolean pnc      = toBool(cm.get('PNCFlag'));

        IndividualApplication ia = new IndividualApplication();
        ia.RecordTypeId = iaRecordTypeId(pnc, flowType);                       // individualAppRecordTypeId formula

        Datetime applied = parseDateTime((String) cm.get('AppliedDate'));
        ia.AppliedDate = (applied != null) ? applied : System.now();          // AppliedDate is Datetime (verified IBXDEV01)

        ia.Status          = (String) cm.get('Status');
        ia.PRM_Stage__c    = (String) cm.get('Stage');                        // API name PRM_Stage__c (verified IBXDEV01)
        ia.Category        = (String) cm.get('Category');                     // ⚠ REQUIRED picklist (nillable=false) — must be a valid value
        ia.ApplicationType = (String) cm.get('ApplicationType');

        ia.PRM_FormCompletedBy__c = (String) cm.get('FormCompletedBy');
        ia.PRM_FormType__c        = (String) cm.get('FormType');
        ia.PRM_PNC__c             = pnc;

        ia.PRM_CorporateReceiptDate__c = parseDate((String) cm.get('CorporateReceiptDate'));
        ia.PRM_FHNaticCaseNumber__c    = (String) cm.get('FHnaticCaseNumber');
        ia.PRM_DisplayCapSites__c      = toBool(cm.get('HasCapSites'));
        ia.PRM_ProcessingStatus__c     = (String) cm.get('processingStatus');
        ia.PRM_PDMManualUpdateType__c  = (String) cm.get('PDMManualUpdateType');
        // AccountId + ApplicationCaseId FKs are set in execute() (steps 3b / 3d)
        return ia;
    }

    // Builds the Case from caseManagerInfo (rt = pre-resolved 'PRM_PRM').
    private Case buildCase(Map<String, Object> cm, Id rt, String flow) {
        String flowType = String.isNotBlank(flow) ? flow : (String) cm.get('flowType');
        Case c = new Case();
        c.RecordTypeId = rt;                                                   // RT 'PRM_PRM'
        c.Type = caseType(flowType, toBool(cm.get('PNCFlag')));               // caseType formula
        c.PRM_IsRoundRobinLogic__c = toBool(cm.get('isRoundRobinLogic'));
        // AccountId + PRM_CaseManager__c FKs are set in execute() (step 3c)
        return c;
    }

    // ── formula helpers (see §4 "Formulas → Apex") ──

    // individualAppRecordTypeId: PNC → 'PRM_PNC'; else PractitionerCreation flow → 'PRM_PDMManualChange';
    // else → 'PRM_PractitionerParticipationRequest' (CL-E2 — verify the flow→RT mapping during build)
    private Id iaRecordTypeId(Boolean pnc, String flowType) {
        if (pnc) return PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PNC');
        return (flowType == 'PractitionerCreation')
            ? PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PDMManualChange')
            : PRM_FormSubUtility.recordTypeId(IndividualApplication.SObjectType, 'PRM_PractitionerParticipationRequest');
    }

    // caseType: PractitionerCreation flow → 'Network Management QC'; else PNC → 'PNC'; else 'Application Review'
    private String caseType(String flowType, Boolean pnc) {
        if (String.isNotBlank(flowType) && flowType == 'PractitionerCreation') return 'Network Management QC';
        return pnc ? 'PNC' : 'Application Review';
    }

    // CredentialingStatusVal
    private String credentialingStatus(String type) {
        if (type == 'IBC Professional Staff')   return 'Credentialed';
        if (type == 'Delegated Credentialing')  return null;
        return 'Credentialing In Progress';
    }

    // PersonGenderIdentity — null for the PractitionerCreation flow; else mapped code
    private String genderIdentity(String gender, String flow) {
        if (flow == 'PractitionerCreation') return null;
        if (gender == 'Male')   return 'M';
        if (gender == 'Female') return 'F';
        if (gender == 'Prefer not to share') return 'Prefer not to share';
        return 'U';
    }

    // PersonGenderIdentityPc — null for the PractitionerCreation flow; else mapped label
    private String genderIdentityPc(String gender, String flow) {
        if (flow == 'PractitionerCreation') return null;
        if (gender == 'Male')   return 'Male';
        if (gender == 'Female') return 'Female';
        if (gender == 'Prefer not to share') return 'Prefer not to share';
        return 'Other';
    }

    // ── small parse utilities ──
    private Boolean toBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date parseDate(String s) { return String.isBlank(s) ? null : Date.parse(s); }          // ⚠ format = org locale (CL-E1b)
    private Datetime parseDateTime(String s) { return String.isBlank(s) ? null : Datetime.parse(s); } // ⚠ format = org locale (CL-E1b)
}
```

> **`buildAccount` notes:**
> - **No describe/SOQL in the builder** — the `PRM_Practitioner` record-type Id (`rt`) is resolved once in `execute()` and passed in.
> - **`flow`** drives the two gender formulas (both return `null` for the `PractitionerCreation` flow — legacy parity; confirm this is intended for the pilot flow).
> - **`Date.parse` / `Datetime.parse`** use the running user's locale. If the payload date format is fixed (e.g. `MM/dd/yyyy`), replace with an explicit parser in `PRM_FormSubUtility` to avoid locale drift (**CL-E1b**).
> - **`PRM_DelegatedOnly__c`** — ✅ verified on IBXDEV01 as a **Boolean checkbox** (`nillable=false`); mapped via `toBool(practitionerInfo.delegated)` (**CL-E1a resolved**).
> - **Required-at-insert booleans** (`IsActive`, `PRM_PNC__c`, `PRM_DelegatedOnly__c`) are `nillable=false` on the org — `toBool` defaults them to `false`, so the insert is safe.

> **DML count is constant** regardless of N (it does **not** grow with the number of practitioners): **5 statements** for Case/IA/Account — Account `insert`, IA `insert`, Case `insert`, IA `update` (back-link), Account `update` (back-link) — **plus the CMA call** (1 pre‑check SOQL + 1 bulk insert in `PRM_CMAService`, §5.1). No DML, SOQL, or describe inside any loop. *(Existing-practitioner path is out of scope for now — see §6.)*

---

## 3. Expected `jsonInput` format

An **`applications[]`** array; each element has the two nodes `**caseManagerInfo**` (Case + IndividualApplication fields) and `**practitionerInfo**` (Account/practitioner fields). `flow` is **not** in the JSON — it is a separate element of the `params` map. Formula-derived fields are computed in the service (per application) and are **not** supplied.

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

---

## 4. Field map (grounded — applies per `applications[]` element)


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
| Account               | `PRM_DelegatedOnly__c` *(**Boolean**, required)*                                                                                                | `practitionerInfo.delegated` (→ `toBool`)                                                                 |
| Account               | `Id`                                                                                                                                             | `practitionerInfo.id` (existing-NPI path)                                                                 |
| Case                  | `RecordTypeId`                                                                                                                                   | ⟲ formula (RT `PRM_PRM`)                                                                                  |
| Case                  | `Type`                                                                                                                                           | ⟲ formula `caseType` (from `flow`/`caseManagerInfo.flowType`, `PNCFlag`)                                  |
| Case                  | `PRM_IsRoundRobinLogic__c`                                                                                                                       | `caseManagerInfo.isRoundRobinLogic`                                                                       |
| Case                  | `AccountId`                                                                                                                                      | ← Account.Id (FK, in-service)                                                                             |
| IndividualApplication | `RecordTypeId`                                                                                                                                   | ⟲ formula `individualAppRecordTypeId`                                                                     |
| IndividualApplication | `AccountId` / `ApplicationCaseId`                                                                                                                | ← Account.Id / Case.Id (FK)                                                                               |
| IndividualApplication | `AppliedDate` *(**Datetime**)*                                                                                                                  | ⟲ formula `System.now()` (or `caseManagerInfo.AppliedDate` if supplied)                                   |
| IndividualApplication | `Status` / `PRM_Stage__c` / `Category` *(**required**)* / `ApplicationType`                                                                      | `caseManagerInfo.Status/Stage/Category/ApplicationType` (note: **`Stage` → field API `PRM_Stage__c`**)    |
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

---

## 5. DML / order (BULK across all `applications[]` — circular FK, insert then back-link)

Build the in-memory records for **every** application first (correlated by **reference** via the `AppUow` wrapper — see §2.1), then run **one bulk DML per step** over the whole set:

1. **Insert all `Account`s** (one per application, from each `practitionerInfo`) — single bulk insert.
2. **Insert all `IndividualApplication`s** — FK `AccountId` → the corresponding Account.Id — single bulk insert.
3. **Insert all `Case`s** — FK `AccountId` → Account.Id **and** `PRM_CaseManager__c` → the corresponding IndividualApplication.Id — single bulk insert.
4. **Update all `IndividualApplication`s** — `ApplicationCaseId` → the corresponding Case.Id — single bulk update.
5. **Update all `Account`s** — `PRM_CaseManager__c` → the corresponding IndividualApplication.Id — single bulk update.
6. **Invoke `PRM_CMAService`** — build one **Practitioner CMA** request per practitioner (`recordType='PRM_Practitioner'`, `PRM_Account__c` → Account.Id, `caseManagerId` → IA.Id) and call `execute({associations})` **once** → CMA does its own **1 pre‑check SOQL + 1 bulk insert** in this same transaction (§5.1). Requires steps 1–2 (Account + IA Ids).

Account, Case, and IndividualApplication reference each other (Case→Account, Case→IA, IA→Case, Account→IA), so the back-links require the two trailing bulk updates. **Per-application correlation is by reference:** the `AppUow` holds the same record instances passed to each DML, so each insert stamps the `Id` back onto the instance the next step reads (`u.acc.Id` / `u.ia.Id` / `u.cse.Id`) — never re-query inside the loop, and never match by position across lists.

> **⚠ Schema prerequisite (validate):** the two **back-linked** fields are populated *after* their record is inserted, so they must be **nullable at insert (not required)** for this order to work:
> - `IndividualApplication.ApplicationCaseId` (set in step 4, after the IA is inserted in step 2)
> - `Account.PRM_CaseManager__c` (set in step 5, after the IA exists in step 2)
>
> `Case.PRM_CaseManager__c` and `Case.AccountId` are set **at insert** (step 3), so they may be required. If either back-linked field is required-at-insert, this insert-then-back-link sequence will fail — confirm against the object schema (Epic A).

**Returns** a per-application result list `applications[] = [ { practitionerAccountId, caseId, caseManagerId (= IndividualApplication.Id) }, … ]` (input order preserved) plus a flat `caseManagerIds` list for the wrapper to seed one `PRM_AsyncJobRecords__c` row per practitioner.

> **Partial-failure note:** with one bulk DML across N applications, decide the failure policy at intake — all-or-nothing (a single bad row rolls back the whole submission) vs. `Database.insert(records, false)` with per-row error capture. Recommended for intake: **all-or-nothing** (so a malformed submission is rejected atomically before any async job is queued); confirm during EPIC F build.

---

## 5.1 CMA invocation — **Practitioner CMA** (added)

After the records are created, E1 invokes the common **`PRM_CMAService`** (E19) to create the **Practitioner Case Manager Association** linking each practitioner **Account → its Case Manager**:

- **Per practitioner:** one CMA request — `recordType = 'PRM_Practitioner'`, `lookups = { PRM_Account__c: accountId }`, `caseManagerId = the IA Id` (→ `PRM_CaseManager__c`).
- **Bulk:** E1 builds the list for **all** practitioners and calls `PRM_CMAService.execute({ associations })` **once** (one pre‑check + one bulk insert in CMA).
- **Same transaction (atomic intake):** the CMA call runs in the **same intake transaction** as the Account/Case/IA DML — a CMA failure **rolls back the whole submission** (consistent with intake atomicity; no job is queued). CMA is idempotent (pre‑check), so an intake re‑submission won't duplicate the association.
- **Scope:** E1 creates **only the Practitioner CMA**. Other CMA record types (Identifier, Business_License, Healthcare_Provider_Taxonomy, Vendor, location/network, …) are created by their owning services in the batches (E2/E3/E5/E13/E14/E15/E17/E18) — see `E19_PRM_CMAService.md` §6.

> **Invocation pattern note:** E1 (sync intake) calls CMA **directly** (it's not a batch). E2–E18 are batch‑hosted, where the **batch aggregates** CMA requests and calls once (E19 §4 / Plan C4). Both go through the same `PRM_CMAService.execute`.

---

## 6. Open items / clarifications

### Resolved by org schema validation (IBXDEV01, 2026-06-24)
- ✅ **Back-link nullability** — `Account.PRM_CaseManager__c` and `IndividualApplication.ApplicationCaseId` are both `nillable=true`; the insert-then-back-link order (§5) is valid.
- ✅ **CL‑E1a** — `Account.PRM_DelegatedOnly__c` is a **Boolean checkbox** (`nillable=false`) → mapped via `toBool(...)`.
- ✅ **`AppliedDate` type** — it's **`Datetime`** → builder uses `System.now()` / `parseDateTime`.
- ✅ **IA `Stage`** — actual API name is **`PRM_Stage__c`** (picklist) → builder/field-map corrected.
- ✅ **Record types exist & active** — Account `PRM_Practitioner`, Case `PRM_PRM`, IA `PRM_PNC` / `PRM_PDMManualChange` / `PRM_PractitionerParticipationRequest`.

### Still open
- ✅ **`IndividualApplication.Category`** — always supplied in `caseManagerInfo.Category`; the **intake validator (EPIC F) guarantees** a valid value (F‑3).
- ⚠ **`PRM_PDMManualUpdateType__c` is a multipicklist** — if multiple values, the payload string must be `;`-joined. Confirm the payload shape.
- ⚠ **Picklist value validity** — verify the payload values for `Account.PersonGenderIdentity` / `HealthCloudGA__Gender__pc` (gender formula outputs `M/F/U` and `Male/Female/Other`), `IndividualApplication.Status/PRM_Stage__c/Category/ApplicationType/PRM_ProcessingStatus__c`, and `Case.Type` (`caseType` outputs) are **active picklist entries** on the org.
- **CL‑E2** — IA flow→RecordType mapping (`PRM_PDMManualChange` vs `PRM_PractitionerParticipationRequest`) is *logic* (the RTs exist) — confirm the business rule during build.
- **CL‑E1b** — date format of `dob`/`effectiveFrom`/`effectiveTo`/`AppliedDate`/`CorporateReceiptDate` — `Date.parse`/`Datetime.parse` are locale-dependent; use an explicit parser if the payload format is fixed.
- **Gender for PractitionerCreation flow** — both gender formulas return `null` for `flow == 'PractitionerCreation'` (legacy parity); confirm intended for the pilot.
- ✅ **`flowType` source** — `params.flow` is authoritative; `caseManagerInfo.flowType` is the fallback (F‑5).
- **Existing-practitioner path deferred** — every Account is **inserted** for now; reintroduce the new-vs-existing partition when the existing-NPI/PDM case is in scope (the `AppUow` correlation already supports it).
- ✅ **CL‑E5 — resolved.** Cached describe helper is **`PRM_FormSubUtility.recordTypeId(SObjectType, devName)`** (general, reusable; defined in `E19_PRM_CMAService.md` §4.1) — no separate `PRM_RecordTypeUtil`.
- ✅ **Partial-failure policy** — **all-or-nothing** at intake (F‑7); the whole submission is rejected atomically if any row is invalid.

---

## 7. Definition of Done

- [ ] `PRM_CaseService extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`.
- [ ] Parses `jsonInput.applications[]`; processes N practitioners in one invocation.
- [ ] No DML/SOQL/describe in loops; record-type Ids cached once.
- [ ] One bulk DML per object type + the two back-link bulk updates (5 statements total, regardless of N).
- [ ] Returns per-application result list (input order) + flat `caseManagerIds`.
- [ ] Formula fields computed in-service (RTs, `caseType`, `CredentialingStatusVal`, gender, `AppliedDate`).
- [ ] **Invokes `PRM_CMAService` to create the Practitioner CMA** (Account ↔ Case Manager), bulk, **same transaction** (§5.1).
- [ ] `<Class>Test` ≥ 85% incl. a **bulk** test (e.g. 200 applications) asserting governor-safe DML counts **and the Practitioner CMA rows**.

---

## 8. Validation log — gaps & issues (findings)

| # | Finding | Type | Status |
|---|---|---|---|
| F‑1 | **Bulk + circular‑FK correlation** via `AppUow` references; back‑links (`IA.ApplicationCaseId`, `Account.PRM_CaseManager__c`) are schema‑nullable (org‑verified) → insert‑then‑back‑link order valid. | validation | ✅ resolved |
| F‑2 | **CMA invocation (Practitioner CMA)** added — E1 calls `PRM_CMAService` (Account ↔ Case Manager), bulk, same transaction (§5.1). | gap | ✅ resolved |
| F‑3 | **`IndividualApplication.Category` is REQUIRED** (picklist). | gap | ✅ resolved — always supplied in `caseManagerInfo.Category`; the **intake validator (EPIC F) guarantees** a present, valid value, and the service maps it as‑is |
| F‑4 | **Picklist value validity** — values the service writes/forwards must be **active picklist entries**: gender outputs (`M/F/U`, `Male/Female/Other`), `Case.Type` (`caseType` outputs), `IndividualApplication.Status/PRM_Stage__c/Category/ApplicationType/PRM_ProcessingStatus__c`. | gap | ⚠ open |
| F‑5 | **`flowType` source.** | gap | ✅ resolved — **`params.flow` is authoritative**; `caseManagerInfo.flowType` is only a fallback (matches the code) |
| F‑6 | **Gender null for PractitionerCreation flow** — both gender formulas return `null` when `flow == 'PractitionerCreation'` (legacy parity). Confirm intended (i.e. gender not stored for this flow). | gap | ⚠ confirm |
| F‑7 | **Partial‑failure policy at intake.** | decision | ✅ resolved — **all‑or‑nothing**: any bad row rolls back the whole submission (rejected atomically before the job is queued) |
| F‑8 | **CL‑E2** — IA flow→RecordType business rule (`PRM_PDMManualChange` vs `PRM_PractitionerParticipationRequest`); RTs exist, logic to confirm. | gap | ⚠ open |
| F‑9 | **CL‑E1b** — date/datetime parsing is locale‑dependent (`Date.parse`/`Datetime.parse`); use an explicit format if the payload format is fixed. | impl | ◻ note |
| F‑10 | **Return shape for the wrapper.** | decision | ✅ resolved — E1 returns, **per practitioner, `AccountId` + `CaseManagerId`** (the wrapper needs them to create `PRM_AsyncJob__c` + `PRM_AsyncJobRecords__c` and to enrich the payload for the batches). **PersonContactId is NOT returned** — E2 resolves it from the Account. |
| F‑11 | **E1 is not part of batch retry** (sync intake, runs once). An intake **re‑submission** creates **new** Accounts (existing‑practitioner path deferred); the Practitioner CMA pre‑check still prevents duplicate associations. | note | ◻ accepted |

---

## 9. Review / merge

Follows the canonical branch model in **Epic A §A8** (`master` ← `main` ← short‑lived `epic-*/<component>` branches).

- **Branch:** `epic-e/case-service` cut from `main`. Scope: `PRM_CaseService` (`execute` + `buildAccount`/`buildIndividualApplication`/`buildCase` + formula helpers) and its **Practitioner‑CMA invocation** (§3f/§5.1).
- **Dependencies on shared classes (single‑owner rule, Epic A §A8):** consumes `PRM_ServiceBase` (EPIC B), `PRM_FormSubUtility` (`NameNormalize`, `recordTypeId` — the latter added with E19), and **`PRM_CMAService` (E19)**. Land/rebase those first; don't edit the shared classes in parallel on this branch.
- **PR into `main`** — require **green CI** (lint · LWC Jest · Apex ≥ 85%) + **1 review**.
- **Evidence (Epic A §A7):** attach the Test Evidence Report — Apex coverage incl. the **bulk** test (e.g. 200 applications, governor‑safe DML counts) **and** the **Practitioner CMA rows** (one per practitioner, no duplicate on re‑run); org spot‑check of Account/Case/IndividualApplication + CMA. **Human sign‑off** before promotion.
- **Squash‑merge** into `main` (readable history); promote `main` → `master` at the Epic E milestone and **tag**.
- **Rollback** = revert the merge commit, or re‑point the deploy to the previous release tag on `master`.
- **Commit convention:** `[E1] PRM_CaseService …`.

> **Note:** E1 runs at **synchronous intake** (EPIC F wrapper), not in a batch — so its review pairs with the **EPIC F** intake wrapper that calls it; coordinate the two PRs if landed together.
