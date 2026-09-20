# E16 · `PRM_CaseDataManagerService` — *1.5 d* · Branch: BOTH · *(PractitionerBatch)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1). Shared conventions in **Part 1 §E0.1–E0.2**.
> **Batch:** runs inside **`PractitionerBatch`** (seq 1), **last** in `execute()` (after E2/E5/E6/E19). **Writes:** `PRM_CaseDataManager__c` (the per‑case **manifest** of which object types were created / failed).
> **Legacy (coalesced):** `PRMDRCreateCDM` + `PRMDRCreateCDMForPractitioner` + `PRMDRPCDMCaseManagerLink` — **2–4 separate CDM DMLs** → **one coalesced INSERT + one UPDATE**.

> **⚠ CONTRACT CHANGE (supersedes CL‑E2‑3):** E16 no longer derives flags from **payload presence**. Per the ratified §8 decision (**option a — set on creation**) and the wired **E20** (`writeCdm`), the **batch supplies the outcomes**: each practitioner element is `{ caseManagerId, created[], failed[] }` where `created`/`failed` are **record‑type tokens** for what was actually created / failed. E16 maps tokens → CDM flag / `*Exception__c` fields.

---

## 0. Review — gaps found & resolved (2026‑06‑29)

| # | Gap (before) | Resolution (this revision) |
|---|---|---|
| G‑1 | **Input contract stale.** §4/§5/§6/§7 derived flags from the raw practitioner payload (presence) — contradicts §8 (set‑on‑creation) and the wired E20 (`{caseManagerId, created[], failed[]}`). | Input rewritten to **`practitioners[] = [{ caseManagerId, created[], failed[] }]`** (§4/§5). |
| G‑2 | **Exception flags missing** from the contract & skeleton, although §8 requires `*Exception__c` on failure. | `failed[]` tokens → `*Exception__c` writes; full token→exception map (§6). |
| G‑3 | **"Initialize all flags false" not implementable** as written — org has **64 non‑nillable booleans**; on **update** we must *not* reset other batches' flags. | Insert path sets **all 64** false (cached describe); **update path touches only this batch's flags** (§4.2/§7). |
| G‑4 | **No token→field map**, and record‑flag→exception is **not** a string transform (`PRM_HealthCareProvider__c`→`PRM_HealthcareProviderException__c`; `…BundleAssociation__c`→`PRM_BundleAssociationException__c`). | Explicit `FIELDS_BY_TOKEN` map, org‑grounded (§4.2/§6). |
| G‑5 | **Identity field type/behaviour** undocumented. Org: `PRM_CaseManager__c` = **lookup to `IndividualApplication`**, required, **createable but NOT updateable** → blind `upsert` can strip it. | **Split insert/update** (not `upsert`); identity set on insert only; FLS assert (§4.2/§7). |
| G‑6 | **Concurrency.** Could the same Case Manager be split across two parallel chunks → **two CDMs**? | ✅ **Resolved (1:1):** Case Manager ↔ practitioner is **1:1** (confirmed), so each CM is a single work‑item — it can't be split across chunks. Per‑practitioner iteration yields one CDM per CM; no grouping / unique constraint needed (§8 OQ‑E16‑1). |
| G‑7 | **Skeleton only.** | **Complete reference implementation** (§4.2). |
| G‑8 | 4 record flags (`PRM_RacialIdentity__c`, `PRM_CultureIdentity__c`, `PRM_HispanicOrigin__c`, `PRM_PersonalPronoun__c`) have **no `*Exception__c` counterpart**. | Map allows a **null exception**; a failed token with no exception field is a no‑op (§6). |
| G‑9 | **`PersonAccount`/`Account` flags** — who sets them true? E1 creates the Person Account at intake; no batch updates the CDM for it. | ✅ **Resolved (E20):** `writeCdm()` **always emits the `PersonAccount` token** in `created[]` (account guaranteed by E1 at intake) → `PRM_PersonAccount__c` set `true` (§8 OQ‑E16‑3). |

---

## 1. Role & cardinality

- Runs **inside `PractitionerBatch`** (seq 1), **BOTH** branches, **last** in `execute()` (so the created/failed outcomes of E2/E5/E6 are known).
- Maintains **exactly one `PRM_CaseDataManager__c` per Case Manager** — a manifest of which record types were created / failed. Case Manager ↔ practitioner is **1:1**, so this is effectively **one CDM per practitioner**.
- Identity is the **Case Manager** (`PRM_CaseManager__c`, a lookup to **`IndividualApplication`**) — one CDM per Case Manager (see §2).

> **Bulkification.** Processes the whole chunk in one pass — input is a **`practitioners[]`** array of outcomes. Resolve existing CDMs in **one bulk query**, build/merge **one record per Case Manager**, then **one bulk INSERT + one bulk UPDATE**.

---

## 2. Idempotency (re-run safe) — **required**

> **No `PRM_RecordKey__c` for E16.** Because there is **exactly one CDM per Case Manager**, the **Case Manager (`PRM_CaseManager__c`) is the identity** — find the existing CDM by it and update, else insert. (Matches legacy `getCDMByCaseManager`.)

**Mechanism (bulk, existence‑based):**
1. Collect the chunk's `caseManagerId`s (from each outcome element; sourced from the stable `PRM_AsyncJobRecords__c` row — §4.1).
2. **One bulk query:** `SELECT Id, PRM_CaseManager__c FROM PRM_CaseDataManager__c WHERE PRM_CaseManager__c IN :caseManagerIds` → `Map<Id caseManagerId, PRM_CaseDataManager__c>`.
3. Per Case Manager: reuse the existing CDM (carry its `Id`) or `new PRM_CaseDataManager__c(PRM_CaseManager__c = caseManagerId)`; **merge** the tokens of every practitioner under that Case Manager.
4. **One bulk INSERT (new) + one bulk UPDATE (existing)** — split because `PRM_CaseManager__c` is **createable‑only** (can't be on an UPDATE/UPSERTABLE strip).

Re-run safe: a second run finds the same CDM by `caseManagerId` and updates it (no duplicate); flags are monotonic (a `true` stays `true`).

> **🔎 Org validation (IBXDEV01, re‑verified 2026‑06‑29):**
> - **Object exists** (~9.9k records). `Name` is **auto‑number** (not createable). `PRM_CaseManager__c` is a **required lookup → `IndividualApplication`**, **createable but NOT updateable** (set on insert only).
> - **64 custom boolean fields, ALL non‑nillable** → **every one must be set on INSERT** (no null). **34 record‑type flags + 30 `*Exception__c` flags.**
> - Record‑flag → exception names are **not** a uniform transform — they must be mapped explicitly (§6).
> - **4 record flags have no exception counterpart:** `PRM_RacialIdentity__c`, `PRM_CultureIdentity__c`, `PRM_HispanicOrigin__c`, `PRM_PersonalPronoun__c` (demographics sub‑flags of ContactProfile).

---

## 3. Prerequisite work items — schema + access

**No `PRM_RecordKey__c`.** Build‑time prerequisites:

| # | Item | Detail |
|---|---|---|
| WI‑1 | **FLS on `PRM_AsyncJob_Access`** | Grant **edit** on `PRM_CaseManager__c` **and all 64 boolean flags** E16 may write. Because every flag is non‑nillable, an FLS‑stripped flag on INSERT → `REQUIRED_FIELD_MISSING`. (E16 asserts the identity field explicitly; the flags surface via the DML error.) |
| WI‑2 | **CRUD on `PRM_CaseDataManager__c`** | Create + Read + Edit on the permission set used by the batch user. |
| WI‑3 | *(optional)* **Unique `PRM_CaseManager__c`** | Concurrency guard (§8 G‑6). **Not required** under the confirmed **1:1** model (each CM is a single work‑item, so no split/duplicate). |

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `params` carries `**flow**` + `**practitioners**` — the chunk of **outcomes**.

| | |
|---|---|
| **Input `params.flow`** | `String` (process name; informational) |
| **Input `params.practitioners`** | `List<Object>` — each `{ caseManagerId: Id, created: List<String>, failed: List<String> }` |
| **Output `response.practitioners`** | `List<Map<String,Object>>` (input order): `{ caseManagerId, caseDataManagerId }` |

- **`created[]` / `failed[]`** are **record‑type tokens** (see §6 vocabulary). The batch emits a token in `created[]` when that record type was successfully written for the practitioner, and in `failed[]` when its service failed (DLQ path).
- Multiple practitioners may share a `caseManagerId` → their tokens **merge** into the single CDM for that Case Manager.

### 4.1 Correlation & Id resolution

`caseManagerId` is supplied by the batch from the **`PRM_AsyncJobRecords__c`** row (stable; the batch scope) — **not** the mutable `Account.PRM_CaseManager__c`. Existing CDMs are resolved by the §2 bulk query keyed on `PRM_CaseManager__c`.

### 4.2 Reference implementation (complete)

```apex
/*
* @ClassName    : PRM_CaseDataManagerService
* @TestClassName: PRM_CaseDataManagerServiceTest
* @StoryNumber  : E16
* @CreatedBy    : Salesforce
* @Description  : EPIC E E16 "Case Data Manager Service" — runs LAST inside PractitionerBatch (seq 1). Maintains exactly one
*                 PRM_CaseDataManager__c manifest per Case Manager (IndividualApplication). Batch-supplied outcomes drive it:
*                 params.practitioners[] = { caseManagerId, created[], failed[] } where created/failed are record-type tokens.
*                 created -> record-type flag = true; failed -> *Exception__c = true. Idempotent (one CDM per Case Manager):
*                 INSERT new with all 64 non-nillable booleans defaulted false (then this batch's flags set true); UPDATE
*                 existing touching only this batch's flags. One bulk SOQL + one bulk INSERT + one bulk UPDATE. FLS-safe.
*/
public with sharing class PRM_CaseDataManagerService extends PRM_ServiceBase {
    private static final String CDM_OBJECT = 'PRM_CaseDataManager__c';
    private static final String FIELD_CASE_MANAGER = 'PRM_CaseManager__c';

    /** Thrown for an invalid request (missing caseManagerId / unknown token) or when FLS strips the identity field. */
    public class PRM_CaseDataManagerException extends Exception {}

    /** Record-type flag field + its *Exception__c field (null when the org has no exception counterpart). */
    private class FlagFields {
        String flag;
        String exception;
        FlagFields(String flag, String exception) {
            this.flag = flag;
            this.exception = exception;
        }
    }

    // Token -> (flag field, exception field). Org-grounded (IBXDEV01). Tokens are the vocabulary the batches emit in
    // created[]/failed[]. PractitionerBatch (E20) uses the first block; later batches reuse the rest.
    private static final Map<String, FlagFields> FIELDS_BY_TOKEN = new Map<String, FlagFields>{
        // ── PractitionerBatch (seq 1) — practitioner-grain (E1/E2/E5/E6/E7/E8/E10/E11) ──
        'PersonAccount'          => new FlagFields('PRM_PersonAccount__c',                  'PRM_PersonAccountException__c'),
        'Account'                => new FlagFields('PRM_Account__c',                        'PRM_AccountException__c'),
        'HealthcareProvider'     => new FlagFields('PRM_HealthCareProvider__c',            'PRM_HealthcareProviderException__c'),
        'HealthcareProviderNpi'  => new FlagFields('PRM_HealthCareProviderNPI__c',         'PRM_HealthcareProviderNPIException__c'),
        'Identifier'             => new FlagFields('PRM_Identifier__c',                     'PRM_IdentifierException__c'),
        'Taxonomy'               => new FlagFields('PRM_HealthCareProviderTaxonomy__c',     'PRM_HealthcareProviderTaxonomyException__c'),
        'BusinessLicense'        => new FlagFields('PRM_BusinessLicense__c',                'PRM_BusinessLicenseException__c'),
        'PersonEducation'        => new FlagFields('PRM_PersonEducation__c',                'PRM_PersonEducationException__c'),
        'BoardCertification'     => new FlagFields('PRM_BoardCertification__c',             'PRM_BoardCertificationException__c'),
        'InfoCodeAssignment'     => new FlagFields('PRM_InfoCodeAssignment__c',             'PRM_InfoCodeAssignmentException__c'),
        'ContactProfile'         => new FlagFields('PRM_ContactProfile__c',                 'PRM_ContactProfileException__c'),
        'PersonLanguage'         => new FlagFields('PRM_PersonLanguage__c',                 'PRM_PersonLanguageException__c'),
        // demographics sub-flags (E10) — no exception counterpart in the org
        'RacialIdentity'         => new FlagFields('PRM_RacialIdentity__c',                 null),
        'CultureIdentity'        => new FlagFields('PRM_CultureIdentity__c',                null),
        'HispanicOrigin'         => new FlagFields('PRM_HispanicOrigin__c',                 null),
        'PersonalPronoun'        => new FlagFields('PRM_PersonalPronoun__c',                null),
        // ── later batches (PracticeLocationAndGroupBatch / PLRelated / Level4) — vocabulary for reuse ──
        'ProviderFeature'                   => new FlagFields('PRM_ProviderFeature__c',                  'PRM_ProviderFeatureException__c'),
        'HealthcareFacilityNetwork'         => new FlagFields('PRM_HealthcareFacilityNetwork__c',        'PRM_HealthcareFacilityNetworkException__c'),
        'HealthCarePractitionerFacility'    => new FlagFields('PRM_HealthCarePractitionerFacility__c',   'PRM_HCPractitionerFacilityException__c'),
        'HealthCareFacility'                => new FlagFields('PRM_HealthCareFacility__c',               'PRM_HealthcareFacilityException__c'),
        'Location'                          => new FlagFields('PRM_Location__c',                         'PRM_LocationException__c'),
        'LocationNPIHistory'                => new FlagFields('PRM_LocationNPIHistory__c',               'PRM_LocationNPIHistoryException__c'),
        'Address'                           => new FlagFields('PRM_Address__c',                          'PRM_AddressException__c'),
        'AlternativeContactMethod'          => new FlagFields('PRM_AlternativeContactMethod__c',         'PRM_AlternativeContactMethodException__c'),
        'OperatingHours'                    => new FlagFields('PRM_OperatingHours__c',                   'PRM_OperatingHoursException__c'),
        'TimeSlot'                          => new FlagFields('PRM_TimeSlot__c',                         'PRM_TimeSlotException__c'),
        'ContentVersion'                    => new FlagFields('PRM_ContentVersion__c',                   'PRM_ContentVersionException__c'),
        'ProgramParticipation'              => new FlagFields('PRM_ProgramParticipation__c',             'PRM_ProgramParticipationException__c'),
        'PracticeLocationAssociation'       => new FlagFields('PRM_PracticeLocationAssociation__c',      'PRM_PracticeLocationAssociationException__c'),
        'PracticeLocationBundle'            => new FlagFields('PRM_PracticeLocationBundle__c',           'PRM_PracticeLocationBundleException__c'),
        'PracticeLocationBundleAssociation' => new FlagFields('PRM_PracticeLocationBundleAssociation__c','PRM_BundleAssociationException__c'),
        'AccountContractEntity'             => new FlagFields('PRM_AccountContractEntity__c',            'PRM_AccountContractEntityException__c'),
        'AccountToAccountRelationship'      => new FlagFields('PRM_AccountToAccountRelationship__c',     'PRM_AccountAccountRelationshipException__c'),
        'ContractHierarchy'                 => new FlagFields('PRM_ContractHierarchy__c',                'PRM_ContractHierarchyException__c')
    };

    /** Cached list of every custom boolean (record-type + exception) — defaulted false on INSERT only. */
    private static List<String> allBooleanFlagFieldsCache;

    /** One outcome element per practitioners[] entry. */
    private class Outcome {
        Id caseManagerId;
        Set<String> created;
        Set<String> failed;
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'practitioners' => new List<Map<String, Object>>() };
        List<Object> practitioners = (params == null) ? null : (List<Object>) params.get('practitioners');
        if (practitioners == null || practitioners.isEmpty()) {
            return response;
        }

        // 1) parse outcomes; collect caseManagerIds (no SOQL/DML in loop)
        List<Outcome> outcomes = new List<Outcome>();
        Set<Id> caseManagerIds = new Set<Id>();
        for (Object practitionerObject : practitioners) {
            Map<String, Object> node = (Map<String, Object>) practitionerObject;
            Id caseManagerId = (Id) node.get('caseManagerId');
            if (caseManagerId == null) {
                throw new PRM_CaseDataManagerException('CDM: caseManagerId is required for every practitioner');
            }
            Outcome outcome = new Outcome();
            outcome.caseManagerId = caseManagerId;
            outcome.created = toStringSet(node.get('created'));
            outcome.failed = toStringSet(node.get('failed'));
            outcomes.add(outcome);
            caseManagerIds.add(caseManagerId);
        }

        // 2) ONE bulk query: existing CDMs by Case Manager
        Map<Id, PRM_CaseDataManager__c> existingByCaseManager = new Map<Id, PRM_CaseDataManager__c>();
        for (PRM_CaseDataManager__c existing : [
            SELECT Id, PRM_CaseManager__c
            FROM PRM_CaseDataManager__c
            WHERE PRM_CaseManager__c IN :caseManagerIds
            WITH SECURITY_ENFORCED
        ]) {
            existingByCaseManager.put(existing.PRM_CaseManager__c, existing);
        }

        // 3) build/merge ONE CDM per Case Manager (tokens of all practitioners of that CM merge in)
        Map<Id, PRM_CaseDataManager__c> workingByCaseManager = new Map<Id, PRM_CaseDataManager__c>();
        for (Outcome outcome : outcomes) {
            PRM_CaseDataManager__c cdm = workingByCaseManager.get(outcome.caseManagerId);
            if (cdm == null) {
                PRM_CaseDataManager__c existing = existingByCaseManager.get(outcome.caseManagerId);
                if (existing != null) {
                    cdm = existing;                                  // UPDATE — do NOT touch other batches' flags
                } else {
                    cdm = new PRM_CaseDataManager__c(PRM_CaseManager__c = outcome.caseManagerId);
                    initAllFlagsFalse(cdm);                         // INSERT — every non-nillable boolean must be set
                }
                workingByCaseManager.put(outcome.caseManagerId, cdm);
            }
            applyTokens(cdm, outcome.created, true);                // created -> flag = true
            applyTokens(cdm, outcome.failed, false);               // failed  -> *Exception__c = true
        }

        // 4) split + FLS-safe DML (PRM_CaseManager__c is createable-only -> cannot go through an UPDATABLE strip)
        List<PRM_CaseDataManager__c> toInsert = new List<PRM_CaseDataManager__c>();
        List<PRM_CaseDataManager__c> toUpdate = new List<PRM_CaseDataManager__c>();
        for (PRM_CaseDataManager__c cdm : workingByCaseManager.values()) {
            if (cdm.Id == null) {
                toInsert.add(cdm);
            } else {
                toUpdate.add(cdm);
            }
        }
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            assertIdentityAccessible(decision);
            List<SObject> safeRows = decision.getRecords();
            insert safeRows;
            for (SObject safeRow : safeRows) {                      // map new Ids back onto the working records
                PRM_CaseDataManager__c saved = (PRM_CaseDataManager__c) safeRow;
                workingByCaseManager.get(saved.PRM_CaseManager__c).Id = saved.Id;
            }
        }
        if (!toUpdate.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.UPDATABLE, toUpdate);
            update decision.getRecords();
        }

        // 5) response in input order
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        for (Outcome outcome : outcomes) {
            results.add(new Map<String, Object>{
                'caseManagerId' => outcome.caseManagerId,
                'caseDataManagerId' => workingByCaseManager.get(outcome.caseManagerId).Id
            });
        }
        response.put('practitioners', results);
        return response;
    }

    /** created -> flag true; failed -> *Exception__c true (no-op when the token has no exception field). */
    private void applyTokens(PRM_CaseDataManager__c cdm, Set<String> tokens, Boolean isCreated) {
        for (String token : tokens) {
            FlagFields flagFields = FIELDS_BY_TOKEN.get(token);
            if (flagFields == null) {
                throw new PRM_CaseDataManagerException('CDM: unknown record-type token "' + token + '"');
            }
            if (isCreated) {
                cdm.put(flagFields.flag, true);
            } else if (flagFields.exception != null) {
                cdm.put(flagFields.exception, true);
            }
        }
    }

    /** INSERT only: every non-nillable custom boolean must carry a value. */
    private void initAllFlagsFalse(PRM_CaseDataManager__c cdm) {
        for (String apiName : allBooleanFlagFields()) {
            cdm.put(apiName, false);
        }
    }

    /** Cached describe of every createable custom boolean on the object. */
    private static List<String> allBooleanFlagFields() {
        if (allBooleanFlagFieldsCache == null) {
            allBooleanFlagFieldsCache = new List<String>();
            Map<String, Schema.SObjectField> fieldMap = PRM_CaseDataManager__c.SObjectType.getDescribe().fields.getMap();
            for (Schema.SObjectField field : fieldMap.values()) {
                Schema.DescribeFieldResult fieldDescribe = field.getDescribe();
                if (fieldDescribe.getType() == Schema.DisplayType.BOOLEAN
                    && fieldDescribe.isCustom()
                    && fieldDescribe.isCreateable()) {
                    allBooleanFlagFieldsCache.add(fieldDescribe.getName());
                }
            }
        }
        return allBooleanFlagFieldsCache;
    }

    /** Fail loudly if FLS stripped the identity lookup rather than silently inserting an orphan manifest. */
    private void assertIdentityAccessible(SObjectAccessDecision decision) {
        Set<String> removedFields = decision.getRemovedFields().get(CDM_OBJECT);
        if (removedFields != null && removedFields.contains(FIELD_CASE_MANAGER)) {
            throw new PRM_CaseDataManagerException(
                'CDM: insufficient field access (FLS) for "' + FIELD_CASE_MANAGER + '" - grant it via PRM_AsyncJob_Access'
            );
        }
    }

    private Set<String> toStringSet(Object listObject) {
        Set<String> values = new Set<String>();
        if (listObject == null) {
            return values;
        }
        for (Object item : (List<Object>) listObject) {
            if (item != null) {
                values.add(String.valueOf(item));
            }
        }
        return values;
    }
}
```

> **Governor cost:** 1 bulk SOQL (existing CDMs) + 1 INSERT + 1 UPDATE — constant regardless of chunk size. The `getDescribe()` is **describe**, not a query/DML — free of limits and cached statically.

---

## 5. Expected input format

E16 consumes **batch‑supplied outcomes** — *not* the raw practitioner payload. Each `practitioners[]` element:

```json
{
  "caseManagerId": "0P8...",            // IndividualApplication Id (from PRM_AsyncJobRecords__c)
  "created": ["HealthcareProvider", "HealthcareProviderNpi", "Identifier", "Taxonomy", "BusinessLicense", "PersonEducation"],
  "failed":  ["BusinessLicense"]         // record types whose service failed (DLQ path) — sets *Exception__c
}
```

> **Service‑computed:** the CDM flags (from tokens). **Batch‑supplied:** `caseManagerId`, `created[]`, `failed[]`. A token may appear in **both** `created` (for one practitioner under the Case Manager) and `failed` (for another) — both the flag and its `*Exception__c` end up `true`.

---

## 6. Token → flag / exception mapping (org‑grounded, IBXDEV01)

> A token in **`created[]`** sets its **flag** `true`; a token in **`failed[]`** sets its **`*Exception__c`** `true`. On INSERT, all 64 booleans are first defaulted `false`. On UPDATE, only the affected fields change (other batches' flags untouched). **Record‑flag → exception is mapped explicitly** (names differ).

**PractitionerBatch (seq 1) — the subset E16 owns this iteration (emitted by E20):**

| Token | Flag field | `*Exception__c` field | Source service |
| --- | --- | --- | --- |
| `PersonAccount` | `PRM_PersonAccount__c` | `PRM_PersonAccountException__c` | E1 (intake) — see OQ‑E16‑3 |
| `Account` | `PRM_Account__c` | `PRM_AccountException__c` | E1/E2 |
| `HealthcareProvider` | `PRM_HealthCareProvider__c` | `PRM_HealthcareProviderException__c` | E2 |
| `HealthcareProviderNpi` | `PRM_HealthCareProviderNPI__c` | `PRM_HealthcareProviderNPIException__c` | E2 |
| `Identifier` | `PRM_Identifier__c` | `PRM_IdentifierException__c` | E2 |
| `Taxonomy` | `PRM_HealthCareProviderTaxonomy__c` | `PRM_HealthcareProviderTaxonomyException__c` | E2 |
| `BusinessLicense` | `PRM_BusinessLicense__c` | `PRM_BusinessLicenseException__c` | E5 |
| `PersonEducation` | `PRM_PersonEducation__c` | `PRM_PersonEducationException__c` | E6 |
| `BoardCertification` | `PRM_BoardCertification__c` | `PRM_BoardCertificationException__c` | E7 *(deferred)* |
| `InfoCodeAssignment` | `PRM_InfoCodeAssignment__c` | `PRM_InfoCodeAssignmentException__c` | E8 *(deferred)* |
| `ContactProfile` | `PRM_ContactProfile__c` | `PRM_ContactProfileException__c` | E10 *(deferred)* |
| `RacialIdentity` / `CultureIdentity` / `HispanicOrigin` / `PersonalPronoun` | `PRM_RacialIdentity__c` / `PRM_CultureIdentity__c` / `PRM_HispanicOrigin__c` / `PRM_PersonalPronoun__c` | *(none)* | E10 *(deferred)* |
| `PersonLanguage` | `PRM_PersonLanguage__c` | `PRM_PersonLanguageException__c` | E11 *(deferred)* |

**Later batches — vocabulary present in `FIELDS_BY_TOKEN` for reuse (default `false` here):** `ProviderFeature`, `HealthcareFacilityNetwork`, `HealthCarePractitionerFacility`, `HealthCareFacility`, `Location`, `LocationNPIHistory`, `Address`, `AlternativeContactMethod`, `OperatingHours`, `TimeSlot`, `ContentVersion`, `ProgramParticipation`, `PracticeLocationAssociation`, `PracticeLocationBundle`, `PracticeLocationBundleAssociation` (→ `PRM_BundleAssociationException__c`), `AccountContractEntity`, `AccountToAccountRelationship` (→ `PRM_AccountAccountRelationshipException__c`), `ContractHierarchy`.

> **Identity:** `PRM_CaseManager__c` is set on INSERT only (createable‑only lookup → `IndividualApplication`).

---

## 7. DML / order (idempotent)

One bulk query (existing CDMs by `PRM_CaseManager__c`) → build/merge one record per Case Manager → **one bulk INSERT** (new, all 64 booleans defaulted false then this batch's set true) **+ one bulk UPDATE** (existing, only this batch's flags touched). Replaces the legacy 2–4 CDM writes (no `UNABLE_TO_LOCK_ROW` under load). Returns `caseDataManagerId` per practitioner (shared when practitioners share a Case Manager).

> **Why not `upsert`?** `PRM_CaseManager__c` is **createable‑but‑not‑updateable**; an `AccessType.UPSERTABLE` strip would drop it, and a single `upsert` list can't apply different field sets to insert vs update. Split insert/update keeps both FLS‑safe and correct.

---

## 8. Open items / clarifications

- ✅ **Idempotency — identity = `PRM_CaseManager__c`** (one CDM per Case Manager); existence query + split insert/update; **no `PRM_RecordKey__c`**.
- ✅ **CL‑E2‑12 — option (a) per‑batch update.** E16 (seq‑1) **inserts** the CDM with all 64 required booleans `false`, setting the practitioner‑grain flags `true`/exceptions; later batches **update** the same CDM for their flags. Safe + idempotent (one CDM per CM).
- ✅ **Flag‑setting — set on actual creation (batch‑supplied tokens), not payload presence** (G‑1). `*Exception__c` set `true` on that type's failure (DLQ path).
- ✅ **`caseManagerId` FK source** — from `PRM_AsyncJobRecords__c` (stable), not the mutable Account back‑link.
- ✅ **Org validation (IBXDEV01, 2026‑06‑29)** — object exists; `PRM_CaseManager__c` required lookup → `IndividualApplication`, createable‑only; **64 non‑nillable booleans** (34 record‑type + 30 exception); 4 record flags have no exception counterpart.
- ✅ **OQ‑E16‑1 (G‑6) — concurrency — RESOLVED (1:1 model).** Case Manager ↔ practitioner is **1:1** (confirmed), so each Case Manager corresponds to exactly **one** practitioner work‑item and can't be split across chunks. E20 iterates **per practitioner** (no grouping); each chunk holds up to `PRM_BatchSize__c` (e.g. **10**) distinct Case Managers, each written once. No unique constraint required (WI‑3 stays optional). *(E20 §1/§9/§10.)*
- ⚠ **OQ‑E16‑2 — failed‑token grain.** A service failure in E20 is **whole‑call** (e.g. all E5 practitioners) → the batch marks the failed type for **every** practitioner in that call. Confirm the CM‑grain exception flag (any failure under the CM ⇒ `*Exception__c = true`) is acceptable.
- ✅ **OQ‑E16‑3 (G‑9) — `PersonAccount`/`Account` — RESOLVED in the batch orchestrator (E20).** The Person Account is created by **E1 at intake** before the batch; **E20 `writeCdm()` always adds the `PersonAccount` token** to each practitioner's `created[]`, so `PRM_PersonAccount__c` is set `true`. *(E20 §7/§9.)* *(`Account` (non‑person business account) is not emitted this iteration — owned by a later batch when applicable.)*
- ◻ **Remaining (build‑time):** map **every** later‑batch token to its owning batch/service node (vocabulary is already in `FIELDS_BY_TOKEN`; the *emit* lives in each batch). Optional: unique `PRM_CaseManager__c`.

---

## 9. Definition of Done

- [x] Org check (§2/§8) done; object + 64 flags + identity confirmed; **CL‑E2‑12 (option a)** decided; **input contract = batch outcomes** (G‑1).
- [ ] `PRM_CaseDataManagerService extends PRM_ServiceBase`; `execute(params)` consuming `practitioners[] = {caseManagerId, created[], failed[]}`.
- [ ] Bulk over the chunk; **one bulk SOQL + one INSERT + one UPDATE**; no DML/SOQL in loops.
- [ ] `caseManagerId` from the batch (job record); existing CDM resolved by `PRM_CaseManager__c`.
- [ ] **INSERT** path sets **all 64 non‑nillable booleans** `false` (cached describe) then this batch's flags `true`/exceptions; **UPDATE** path touches only this batch's flags.
- [ ] `created` token → flag `true`; `failed` token → `*Exception__c` `true` (no‑op when no exception field); **unknown token throws**.
- [ ] FLS‑safe (`stripInaccessible`); identity asserted; `PRM_AsyncJob_Access` grants edit on identity + all writable flags (WI‑1).
- [ ] **Idempotent:** re‑run produces **no duplicate CDM**; flags monotonic.
- [x] Concurrency handled (OQ‑E16‑1): **1:1 CM↔practitioner**, so each CM is a single work‑item (no split, no grouping); E20 iterates per practitioner (batch size up to 10).
- [x] `PersonAccount` flag set (OQ‑E16‑3): **E20 always emits the `PersonAccount` token** in `created[]`.
- [ ] Returns `caseDataManagerId` per practitioner (shared across practitioners of one Case Manager).
- [ ] `PRM_CaseDataManagerServiceTest` ≥ 85% incl.: bulk (multiple distinct Case Managers in one call, 1:1); **re‑run/idempotency** (one CDM after two runs); **created→flag** + **failed→exception**; defensive same‑CM token merge; unknown‑token error; FLS‑strip error.
- [ ] Field API names/types validated against the org.
