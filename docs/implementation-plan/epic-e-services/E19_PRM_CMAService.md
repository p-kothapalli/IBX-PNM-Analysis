# CMA · `PRM_CMAService` — Case Manager Association (common service)

> **Parent:** `Epic_E_Practitioner_Services.md`. Shared conventions in **Part 1 §E0.1–E0.2**.
> **Cross‑cutting:** invoked by the **relevant** record‑creating services (those whose object has a CMA record type — see §6). **Writes:** `PRM_CaseManagerAssociation__c` (junction linking created/updated records → the Case Manager).
> **Object:** `PRM_CaseManagerAssociation__c` — **already exists** in the org (IBXDEV01). No new fields needed (idempotency via pre‑check).

---

## 1. Role & cardinality

- A **common service**: each **batch** collects the CMA requests for all its services (created **or updated/reused** records + the Case Manager Id) and calls `PRM_CMAService` **once, in the same transaction** as record creation (F‑2/F‑3/F‑6). A CMA failure **fails the step** (→ DLQ/retry).
- **One CMA row per "primary" created/updated record, per Case Manager**, with **RecordType** set and **all the contextual lookups** for that record type populated (§6). E.g. 3 Identifiers → 3 `Identifier` CMA rows.
- **Required field:** `PRM_CaseManager__c` (→ IndividualApplication). `Name` is **autonumber** (not set). `PRM_RequestType__c` = optional change‑request **action type** — **left null for now** (F‑10).
- **Bulk:** accepts a list of association requests across the chunk → **one pre‑check query + one bulk insert**.

> **Mapping lives on `PRM_FormSubUtility`** (the existing EPIC B utility) via a **new method** — defined **here in §4.1** because **Epic B is already generated** (don't reopen Epic B). It returns the **RecordType → {primary lookup, contextual lookups}** map; `PRM_CMAService` consumes it and does the pre‑check + DML.

---

## 2. Idempotency (re-run safe) — **required**

> **Decision: existence pre‑check (no new field).** `PRM_CaseManagerAssociation__c` has **no External Id/Unique field**, and we will not add one. Dedupe by the natural key **(`PRM_CaseManager__c` + RecordType + primary lookup Id)**.

**Mechanism (bulk):**
1. Build the candidate CMA rows in memory (one per primary record).
2. **One bulk query** for existing rows over the chunk's Case Managers + record types: `SELECT PRM_CaseManager__c, RecordTypeId, <all primary lookup fields> FROM PRM_CaseManagerAssociation__c WHERE PRM_CaseManager__c IN :cmIds AND RecordTypeId IN :rtIds` → build a `Set<String>` of existing keys `cm_rtId_primaryId`.
3. **Insert only** the candidates whose key isn't already present.

Re-run safe: an already‑created association is skipped. *(Single‑threaded batch → query‑then‑insert is sufficient; no unique constraint needed.)*

> **Primary lookup per RT** (the dedupe discriminator) is the record type's namesake object — see the **Primary** column in §6.

---

## 3. Prerequisite work items — access (no schema)

No new fields. Only **permission‑set access** for the batch‑running user:

| WI | Task | Target | Done when |
|---|---|---|---|
| **WI‑1** | Grant **object CRUD (Create/Read)** on `PRM_CaseManagerAssociation__c` + **FLS (Edit)** on `PRM_CaseManager__c`, `RecordTypeId`, `PRM_RequestType__c`, and all lookup fields in §6, to **`PRM_AsyncJob_Access`** (Epic A §A5) | `PRM_AsyncJob_Access` | running user can insert CMA rows with the needed fields |

---

## 4. Method signature & contract (BULK)

`extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>` — the **EPIC B base‑class contract** (same as every other service). The input map carries `**associations**` — a list of association requests the **invoker** has assembled; each request provides the **`caseManagerId`** (the invoker supplies it), the `recordType`, the `lookups` map, and optional `requestType`.

```apex
public with sharing class PRM_CMAService extends PRM_ServiceBase {
    public override Map<String, Object> execute(Map<String, Object> params) {
        List<Object> associations = (List<Object>) params.get('associations');
        if (associations == null || associations.isEmpty()) { response = new Map<String,Object>(); return response; }

        // each element: { caseManagerId, recordType, lookups: {field->Id}, requestType }
        // 1) resolve CMA RecordType Ids once (cached describe via PRM_FormSubUtility.recordTypeId — §4.1)
        // 2) build candidate PRM_CaseManagerAssociation__c[] via PRM_FormSubUtility.cmaFieldSets() RT->field map (§4.1)
        //    (PRM_CaseManager__c = caseManagerId from the request; primary + contextual lookups; PRM_RequestType__c)
        // 3) ONE bulk pre-check query (existing by cm + rtId + primary lookup) -> Set<String> existingKeys
        // 4) ONE bulk insert of new candidates

        response = new Map<String, Object>();   // e.g. { caseManagerAssociationIds: [...] }
        return response;
    }
}
```

> **`caseManagerId` is supplied by the invoker** (the batch or calling service that already holds it) — **CMA does not resolve it** from `PRM_AsyncJobRecords__c` or any object. It's just an input on each request.

> The **RecordType → {primary, contextual} field map** is provided by a **new `PRM_FormSubUtility` method** (§4.1); `PRM_CMAService` uses it to validate each request's `lookups` and compute the dedupe key (`cm_rtId_primaryId`).

> **RecordTypeId resolution.** The request carries the **`recordType` DeveloperName** (not the Id). The service resolves the Id **once per record type** via a **general cached describe helper on `PRM_FormSubUtility`** (`recordTypeId(...)` — §4.1; reusable by all services; **there is no `PRM_RecordTypeUtil`** — resolves CL‑E5). **No per‑row describe/SOQL.** All 14 CMA record types are **active** (org‑verified). If `recordType` is unknown/inactive, fail that request (or skip with an error) rather than inserting without a RecordType (avoids the legacy null‑RT rows — §8).

### 4.1 Utility — new `PRM_FormSubUtility` methods (define here; Epic B already generated)

Add to the existing `PRM_FormSubUtility`: (1) `cmaFieldSets()` returning the per‑record‑type CMA field set (encodes the §6 mapping), and (2) a **general, reusable** cached `recordTypeId(...)` helper. `PRM_CMAService` reads both (no hardcoded map in the service, no new CMDT).

```apex
// PRM_FormSubUtility — NEW for CMA (specified here since Epic B is already built)
public class CMAFieldSet {
    public String primary;            // dedupe discriminator lookup (required)
    public List<String> context;      // additional lookups to populate when provided
    public CMAFieldSet(String p, List<String> c) { primary = p; context = c; }
}

// RecordType DeveloperName -> CMAFieldSet  (full set per §6)
public static Map<String, CMAFieldSet> cmaFieldSets() {
    return new Map<String, CMAFieldSet>{
        'PRM_Practitioner'        => new CMAFieldSet('PRM_Account__c', new List<String>()),
        'PRM_Vendor'              => new CMAFieldSet('PRM_Account__c', new List<String>()),
        'Identifier'              => new CMAFieldSet('PRM_Identifier__c', new List<String>()),
        'Business_License'        => new CMAFieldSet('PRM_BusinessLicense__c', new List<String>()),
        'Healthcare_Provider_Taxonomy' => new CMAFieldSet('PRM_HealthcareProviderTaxonomy__c', new List<String>()), // ⚠ inferred (§8)
        'PRM_PracticeLocation'    => new CMAFieldSet('PRM_HealthcareFacility__c', new List<String>()),
        'Practice_Location_Address' => new CMAFieldSet('PRM_Address__c', new List<String>{ 'PRM_HealthcareFacility__c' }),
        'Practice_Location_Association' => new CMAFieldSet('PRM_HealthcareFacilityAssociation__c', new List<String>()),
        'Practice_Location_Network' => new CMAFieldSet('PRM_HealthcareFacilityNetwork__c', new List<String>{ 'PRM_Account__c','PRM_HealthcareFacility__c' }),
        'Practice_Location_Taxonomy' => new CMAFieldSet('PRM_HealthcareFacilityNetwork__c', new List<String>{ 'PRM_Account__c','PRM_HealthcareFacility__c' }),
        'Practitioner_Practice_Location' => new CMAFieldSet('PRM_HealthcarePractitionerFacility__c', new List<String>{ 'PRM_HealthcareFacility__c','PRM_HealthcareFacilityNetwork__c' }),
        'Practitioner_at_Practice_Location_Taxonomy_and_Network' => new CMAFieldSet('PRM_HealthcareFacilityNetwork__c', new List<String>{ 'PRM_Account__c','PRM_HealthcareFacility__c','PRM_Identifier__c' }),
        'Provider_Feature'        => new CMAFieldSet('PRM_ProviderFeature__c', new List<String>{ 'PRM_Account__c','PRM_HealthcareFacility__c' }),
        'Program_Participation'   => new CMAFieldSet('PRM_ProgramParticipation__c', new List<String>())
    };
}

// convenience accessor
public static CMAFieldSet cmaFieldSet(String recordType) { return cmaFieldSets().get(recordType); }

// GENERAL cached RecordType-Id-by-DeveloperName helper (reusable by ALL services) — resolves CL-E5
private static Map<String, Id> RT_CACHE = new Map<String, Id>();
public static Id recordTypeId(SObjectType sot, String devName) {
    String key = String.valueOf(sot) + '.' + devName;
    if (!RT_CACHE.containsKey(key)) {
        RT_CACHE.put(key, sot.getDescribe().getRecordTypeInfosByDeveloperName().get(devName).getRecordTypeId());
    }
    return RT_CACHE.get(key);
}
// CMA usage: PRM_FormSubUtility.recordTypeId(PRM_CaseManagerAssociation__c.SObjectType, recordType)
```

> **CL‑E5 resolved:** the cached `recordTypeId(...)` is a **general `PRM_FormSubUtility` method** (reusable by all E‑services), **not** a separate `PRM_RecordTypeUtil`. Other service docs that referenced `PRM_RecordTypeUtil` should use `PRM_FormSubUtility.recordTypeId(...)`.

> The service: for each request, looks up `cmaFieldSet(recordType)` → sets `PRM_CaseManager__c` + the `primary` (required; from `lookups`) + any `context` fields present in `lookups`; builds the dedupe key `cm_rtId_lookups[primary]`.

**Invoker pattern (example):** the invoker (batch/service) assembles all CMA requests for its chunk and calls `execute` **once**:
```apex
new PRM_CMAService().execute(new Map<String,Object>{
  'associations' => new List<Object>{
     new Map<String,Object>{
        'caseManagerId' => cmId,
        'recordType'    => 'PRM_Practitioner',
        'lookups'       => new Map<String,Object>{ 'PRM_Account__c' => accountId }
        // requestType omitted — PRM_RequestType__c left null for now (F-10)
     }
  }
});
```

> **Governor cost:** 1 bulk SOQL (pre‑check) + 1 bulk DML (insert) per invocation — the invoker aggregates all requests for the chunk and calls `execute` once.

---

## 5. Input format (per request)

| Field | Meaning |
|---|---|
| `caseManagerId` | the Case Manager (IndividualApplication) — `PRM_CaseManager__c` |
| `recordType` | CMA RecordType DeveloperName (§6) |
| `lookups` | map of CMA lookup field → record Id (must include the **primary**; include **contextual** per §6) |
| `requestType` | optional change‑request **action type** → `PRM_RequestType__c` — **left null for now** (F‑10) |

---

## 6. Record type → lookup mapping (grounded from data) + invoking service

> **Primary** = dedupe discriminator (the record type's namesake). **Contextual** = additional FKs the existing data also populates (set when available).

| Record Type (DeveloperName) | Primary lookup | Contextual lookups | Invoked by |
|---|---|---|---|
| `PRM_Practitioner` | `PRM_Account__c` | — | E1/E2 (practitioner Account) |
| `PRM_Vendor` | `PRM_Account__c` | — | E3 (group/vendor Account) |
| `Identifier` | `PRM_Identifier__c` | — | E2 |
| `Business_License` | `PRM_BusinessLicense__c` | — | E5 |
| `Healthcare_Provider_Taxonomy` | `PRM_HealthcareProviderTaxonomy__c` | — | E2 *(⚠ no org data — inferred; confirm §8)* |
| `PRM_PracticeLocation` | `PRM_HealthcareFacility__c` | — | E13 |
| `Practice_Location_Address` | `PRM_Address__c` | `PRM_HealthcareFacility__c` | E13 |
| `Practice_Location_Association` | `PRM_HealthcareFacilityAssociation__c` | — | E13 *(confirm owner §8)* |
| `Practice_Location_Network` | `PRM_HealthcareFacilityNetwork__c` | `PRM_Account__c`, `PRM_HealthcareFacility__c` | E17 |
| `Practice_Location_Taxonomy` | `PRM_HealthcareFacilityNetwork__c` | `PRM_Account__c`, `PRM_HealthcareFacility__c` | E17 |
| `Practitioner_Practice_Location` | `PRM_HealthcarePractitionerFacility__c` | `PRM_HealthcareFacility__c`, `PRM_HealthcareFacilityNetwork__c` | E14 |
| `Practitioner_at_Practice_Location_Taxonomy_and_Network` | `PRM_HealthcareFacilityNetwork__c` | `PRM_Account__c`, `PRM_HealthcareFacility__c`, `PRM_Identifier__c` | E18 |
| `Provider_Feature` | `PRM_ProviderFeature__c` | `PRM_Account__c`, `PRM_HealthcareFacility__c` | E15 |
| `Program_Participation` | `PRM_ProgramParticipation__c` | — | *(owner TBD §8)* |

> **Services with NO CMA record type** (do **not** call CMA): E6 Education, E7 BoardCertification, E8 InfoCode, E9 File, E10 ContactProfile, E11 Language, E12 NPI. *(Confirm this is intended — §8.)*

Every row also sets the required `PRM_CaseManager__c` and (optional) `PRM_RequestType__c`.

---

## 7. DML / order (idempotent)

1. Resolve CMA RecordType Ids once (cached describe).
2. Build candidate rows (RT + `PRM_CaseManager__c` + primary/contextual lookups + `PRM_RequestType__c`).
3. **One bulk pre‑check** (existing by `PRM_CaseManager__c` + RecordTypeId + primary lookup) → existing‑key set.
4. **One bulk insert** of new candidates only — **all‑or‑nothing** (`Database.insert(rows, true)`); a request missing its primary or with an unknown/inactive RT fails the request → the step fails → DLQ/retry (F‑4).

Runs in the **same transaction** as the batch's record creation (F‑3). No updates needed (associations are immutable links). Returns the created CMA Ids (optional).

---

## 8. Open items / clarifications

- ✅ **Decisions:** `extends PRM_ServiceBase`/`execute(Map)` contract; all contextual lookups per RT (multi‑FK rows accepted); mapping via a **new `PRM_FormSubUtility` method** (§4.1, defined here — Epic B not reopened); idempotency via pre‑check (no new field); all 14 RTs in scope.
- ✅ **`caseManagerId` is invoker‑supplied** — CMA does not resolve it (the batch/service passes it per request).
- ✅ **Services‑without‑CMA‑RT** (Education/BoardCert/InfoCode/NPI/File/Contact/Language) intentionally create **no** CMA association (no matching record type).
- ✅ **`Healthcare_Provider_Taxonomy` → `PRM_HealthcareProviderTaxonomy__c`** (confirmed, F‑8).
- ✅ **`Program_Participation` / `Practice_Location_Association`** — out of current E1–E18 scope; mapping stays defined, revisit when those flows are built (F‑9).
- ✅ **`PRM_RequestType__c` left null for now** (F‑10) — change‑request action type, not set by Practitioner Creation.
- ✅ **Contextual lookups best‑effort (schema‑confirmed, F‑1)** — only `PRM_CaseManager__c` is required on the object; all business lookups are nullable, so setting whatever Ids the invoker provides is safe.
- ✅ **Invocation aggregation (F‑2/F‑3)** — each batch **collects all CMA requests for its chunk and calls `execute` once**, in the **same transaction** as record creation (one pre‑check + one insert; CMA failure fails the step). Each E‑service doc adds a "CMA association" note (its RT + lookups).
- ✅ **Insert mode (F‑4):** all‑or‑nothing; missing primary / unknown RT → fail request. ✅ **Created+updated (F‑6).** ✅ **Network/Taxonomy RT by HFN RT (F‑5).**
- ⚠ **Data quality (FYI):** 278 existing rows have a **null RecordType** (only `PRM_HealthcareFacility__c` set) — legacy; our service always sets a RecordType.

---

## 10. Validation log — gaps & issues (findings)

> Architectural/implementation review of this design. **F‑x** items are flagged; resolved ones noted, open ones need a decision (§ questions to you below).

| # | Finding | Type | Status |
|---|---|---|---|
| F‑1 | **Contextual lookups are schema‑nullable** — org describe shows only `PRM_CaseManager__c` is `nillable=false`; every business lookup is nullable. So "best‑effort contextual" is **schema‑safe** (no insert failure if a contextual Id is absent). | validation | ✅ resolved (schema‑confirmed) |
| F‑2 | **Per‑service request construction.** The RT→field *map* is centralized; each calling service builds its request(s) with the correct `recordType` + Ids. | gap | ✅ resolved — the **batch aggregates** each service's requests (invoker‑built RT+lookups); **each E‑service doc adds a "CMA association" note** specifying its RT(s) + which created Id → which lookup |
| F‑3 | **Aggregation + transaction boundary.** | decision | ✅ resolved — the **batch collects all CMA requests for its chunk and calls `execute` once, in the SAME transaction** as record creation; a CMA failure **fails the step** → DLQ/retry |
| F‑4 | **Insert mode + request validation.** | decision | ✅ resolved — **all‑or‑nothing** insert (`Database.insert(..., true)`); a request **missing its primary** lookup or with an **unknown/inactive `recordType`** → **fail the request** (step failure/DLQ) |
| F‑5 | **Network vs Taxonomy RT ambiguity** (both → HFN). | gap | ✅ resolved — invoker maps the **HFN record's RecordType** to the CMA RT (`PRM_FacilityNw` → `Practice_Location_Network`; `PRM_FacilityTx` → `Practice_Location_Taxonomy`) |
| F‑6 | **Created vs updated records.** | gap | ✅ resolved — CMA is invoked for **created AND updated/reused** records (pre‑check keeps it duplicate‑safe) |
| F‑7 | **Level‑4 contextual `PRM_Identifier__c`** = a **CAQH** identifier (org data), and **extremely sparse — 1 of 1,301** Level‑4 rows. | gap | ✅ resolved (data) — treat as **best‑effort/optional**: set only when a CAQH identifier Id is available; otherwise omit |
| F‑8 | **`Healthcare_Provider_Taxonomy` mapping** = `PRM_HealthcareProviderTaxonomy__c`. | gap | ✅ confirmed |
| F‑9 | **Owners of `Program_Participation` & `Practice_Location_Association`** CMA RTs — not produced by any E1–E18 service. | gap | ✅ accepted — out of current scope; the mapping stays defined, revisit when those flows are built |
| F‑10 | **`PRM_RequestType__c` is a change‑request *action type*, not the flow name** (mostly null in org data). | gap | ✅ decided — **leave `PRM_RequestType__c` null for now** (do not set it) |
| F‑11 | **Pre‑check query shape.** Must `SELECT` the **distinct primary lookup fields** for the RTs in the chunk and, per existing row, read the primary field **for that row's RT** (via the utility map) to build the `cm_rtId_primaryId` key. (Implementation note.) | impl | ◻ note |
| F‑12 | **CRUD/FLS enforcement.** `with sharing` + enforce object/field access on insert (e.g. `Security.stripInaccessible`) per standards. | impl | ◻ note |

> **Dedupe correctness (validated):** the **primary** must always be the record type's **own most‑specific created record** (HFN row for network/taxonomy, HPF row for PPL, etc.) — which is unique per association — so `cm_rtId_primaryId` won't collapse distinct rows. The §6 mapping already uses the namesake record as primary. ✅

---

## 9. Definition of Done

- [ ] Permission‑set access (§3) deployed (`PRM_CaseManagerAssociation__c` CRUD + field FLS on `PRM_AsyncJob_Access`).
- [ ] `PRM_CMAService extends PRM_ServiceBase` with `execute(Map<String,Object>)` (reads `params.associations`); **new `PRM_FormSubUtility` methods** (§4.1): `cmaFieldSets()` (RT→field‑set map) + general cached `recordTypeId(SObjectType, devName)` (reusable; resolves CL‑E5).
- [ ] RecordType Ids resolved via cached describe; per‑request validated against the map (primary required).
- [ ] **Bulk:** one pre‑check query + one bulk insert per chunk; no DML/SOQL in loops.
- [ ] **Idempotent:** pre‑check by (`PRM_CaseManager__c` + RecordType + primary lookup); re‑run creates **no duplicate** CMA rows.
- [ ] All 14 record types mapped (with the inferred/owner items in §8 confirmed).
- [ ] Relevant services (§6) call CMA after creating their records (ideally aggregated per batch).
- [ ] `<Class>Test` ≥ 85% incl. a bulk test + a **re‑run/idempotency test**; mapping validated against the org.

---

## 11. Review / merge

Follows the canonical branch model in **Epic A §A8** (`master` ← `main` ← short‑lived `epic-*/<component>` branches).

- **Branch:** `epic-e/cma-service` cut from `main`. Scope: `PRM_CMAService` + the new `PRM_FormSubUtility` methods (`cmaFieldSets()`, `recordTypeId(...)`) + the `PRM_AsyncJob_Access` FLS for `PRM_CaseManagerAssociation__c` (§3).
- **Single‑owner rule (Epic A §A8):** `PRM_FormSubUtility.recordTypeId(...)` is a **shared helper reused by other E‑services** — land it on this branch first (or coordinate), so no two branches edit `PRM_FormSubUtility` in parallel. CMA itself is a **common service invoked by the batches**, so merge it before/with the services that call it.
- **PR into `main`** — require **green CI** (lint · LWC Jest · Apex ≥ 85%) + **1 review**.
- **Evidence (Epic A §A7):** attach the Test Evidence Report — Apex coverage incl. the **bulk** + **re‑run/idempotency** tests, and an org spot‑check of `PRM_CaseManagerAssociation__c` rows (correct RT + lookups, no duplicates on re‑run). **Human sign‑off** before promotion.
- **Squash‑merge** into `main` (readable history); promote `main` → `master` at the Epic E milestone and **tag**.
- **Rollback** = revert the merge commit, or re‑point the deploy to the previous release tag on `master`.
- **Commit convention:** `[E19] PRM_CMAService …` / `[E19] PRM_FormSubUtility cmaFieldSets + recordTypeId`.
