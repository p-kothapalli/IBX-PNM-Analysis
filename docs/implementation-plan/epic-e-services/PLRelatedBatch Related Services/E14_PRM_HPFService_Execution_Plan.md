# E14 · `PRM_HPFService` — Comprehensive Execution Plan

> **Source design (authoritative):** `E14_PRM_HPFService.md` (this folder). **Batch:** `E22_PRM_PLRelatedBatch.md` (seq 4). **Conventions:** `Epic_E_Practitioner_Services.md` §E0.1–E0.2 / §E0.4; rule `prm-service-class-boundaries`. **Base class:** `PRM_ServiceBase` (`execute(Map<String,Object>) : Map<String,Object>`, protected `response`). **Shared util:** `PRM_FormSubUtility.recordTypeId(SObjectType, devName)`, `NameNormalize(...)`.
>
> **⚠ Ground rule for this plan:** nothing is assumed. Every item is tagged **[CONFIRMED]** (documented in the design/org), **[OPEN — Pending Clarification]** (needs a decision before/at build), **[RISK]**, or **[RECOMMENDATION]**. Where a decision blocks code, the reference implementation (§7) implements the **recommended** option behind a clearly marked seam and the corresponding task is **Pending Clarification**.
>
> **Target org:** IBXDEV01 (per design §3.1; confirm — OQ‑E14‑7). **Effort:** 1.5 d (design) — re‑estimated in §6.

---

## 1. Confirmed requirements (extracted from the epic)

| # | Requirement | Evidence |
|---|---|---|
| R1 | **Single service, two record types.** `PRM_HPFService` builds **both** `PRM_PractitionerLocationAffiliation` (PLA) and `PRM_PractitionerPracticeAffiliation` (PPA) rows on `HealthcarePractitionerFacility` in **one mixed‑RT bulk DML**. No separate class; `PractionerPracticeLocationService` is an internal builder. | design §1, §2 (OQ‑E14‑2a/2b resolved) |
| R2 | **PLA grain** = one row per **(practitioner × location)**; `HealthcareFacilityId` set. | design §1 |
| R3 | **PPA grain** = one row per **(practitioner × practice/group Account)**; `AccountId` set, **`HealthcareFacilityId` blank** (DR `PRMDRCreateHCPFForPractitionerPracAffiliation[Delg/DelgZ2]`). | design §1, §6.1 (org‑confirmed) |
| R4 | **`extends PRM_ServiceBase`**, `execute(Map<String,Object>) : Map<String,Object>`; input `params.affiliations[]`, output `response.affiliations[]` (input order) `{ practitionerId, healthcareFacilityId, hcpfId }`. | design §4; `PRM_ServiceBase.cls` |
| R5 | **Batch‑injected context** (per `prm-service-class-boundaries`): `practitionerId`, `healthcareFacilityId`, `accountId`, `caseManagerId`, `isPrimary`, `isActive`, `effectiveFrom`, `effectiveTo`, `recordType`. Service does **no correlation SOQL**. | design §4.1 |
| R6 | **Idempotent (re‑run safe).** No duplicate affiliations on batch retry. PLA key `(PractitionerId + HealthcareFacilityId + RecordTypeId)`; PPA key `(PractitionerId + AccountId + RecordTypeId)`. | design §2 |
| R7 | **Required booleans never null:** `IsPrimaryFacility`, `IsActive`, `PRM_Pending__c`. `Name` required. | design §3.1 |
| R8 | **Field derivations:** `IsPrimaryFacility = (recordType == PPA) ? false : isPrimary`; `HealthcareFacilityId = (recordType == PPA) ? null : healthcareFacilityId`; `PRM_AttestationDate__c = Date.today()`; `PRM_Pending__c` default; `Name` = `CONCAT(practitionerName,' @ ',facility/practiceName)`. PPA `HealthcareProviderId = null`. | design §6, §6.1 |
| R9 | **No new field / no metadata.** Idempotency via existence pre‑check on the natural key (object has no `PRM_RecordKey__c`/`PRM_ExternalId__c`; `SourceSystemIdentifier` is Unique but not an extId). | design §2, §3 |
| R10 | **Bulk only** — build all rows in memory, one bulk DML; no SOQL/DML in loops. | design §1, §7 |
| R11 | **Runs in `PLRelatedBatch` (seq 4)** — not in‑process in E13 (CL‑E2‑13 resolved). Returns `hcpfId` per affiliation to feed **E19 CMA** (`Practitioner_Practice_Location`) + **E15**. E14 does **not** build CMA/CDM itself (E22 does). | design §1, §7; E22 §9 |

---

## 2. Open questions — **Pending Clarification** (decide before/at build)

> Each blocks or shapes code. The reference implementation (§7) codes the **recommended** option behind a marked seam.

| ID | Question | Options / trade‑offs | Recommendation |
|---|---|---|---|
| **OQ‑E14‑1b** | **Who runs the idempotency pre‑check** — the **service** or the **batch (E22)**? | (a) **Service** does one bulk `SELECT` on `HealthcarePractitionerFacility` (consistent with E15/E16/E19, which self‑pre‑check). Simpler contract; one small deviation from "zero‑SOQL". (b) **Batch** pre‑checks and injects `existingHcpfId`/`isNew` per affiliation → service is pure build+DML. Purer boundary; more batch plumbing + a wider input contract. | **(a) service‑side pre‑check** — matches the sibling idempotent services; keep E22 lean. Coded in §7 behind `resolveExisting()`. |
| **OQ‑E14‑5** | **`Name` source.** `Name` is required; the service is SOQL‑free, so the name components must be **injected**. The current input contract (design §4) has **no** `practitionerName` / `facilityPracticeName` / `practiceName`. | (a) Batch injects `practitionerName` + `facilityName` (PLA) / `practiceName` (PPA); service concatenates. (b) Service queries Account/HCF for names (violates the rule). | **(a)** — extend the input contract with the name components; batch supplies them (it already resolves the HCF + Account). **Gap:** design §4 contract must add these fields. |
| **OQ‑E14‑9** *(new)* | **Update‑existing semantics + field mutability.** The DR updates on `HPFId` present. For a **create‑flow retry**, the matched row's values are unchanged, so **skip** is equivalent and avoids touching createable‑only fields. Whether `PractitionerId`/`AccountId`/`HealthcareFacilityId`/`RecordTypeId` are **updateable** on `HealthcarePractitionerFacility` is **not yet verified in‑org**. | (a) **Skip existing** (insert misses only) — safe, no field‑mutability risk, fully idempotent for the create flow. (b) **Insert + update** the mutable subset (IsActive/EffectiveFrom/EffectiveTo/PRM_Pending__c/IsPrimaryFacility/PRM_AttestationDate__c) — matches legacy refresh; requires an org describe of updateable flags first. | **(a) skip‑existing for the pilot**; add an update pass only if business needs effective‑date refresh on re‑submit (then do the describe first). Coded as skip in §7 with an `// UPDATE-PASS (OQ-E14-9)` seam. |
| **OQ‑E14‑4** | **CMA context lookup** `PRM_HealthcareFacilityNetwork__c` for `Practitioner_Practice_Location`. | Owned by **E22/E19**, not E14. But E14's contribution (which HFN Id, if any) must be defined. Since HFN is a **trigger side‑effect of E18 (seq 5)** — *after* E14 — the network context likely **isn't available** at seq 4. | **Leave the HFN context null in E22's CMA for PLA** (HFN doesn't exist yet at seq 4); revisit if CMA must be (re)written in seq 5. Not an E14 code item — track on E22. |
| **OQ‑E14‑1** | **Idempotency mechanism** — natural‑key pre‑check (recommended) vs. writing the Unique `SourceSystemIdentifier` to a composite + pre‑check on it. | Composite `SourceSystemIdentifier` gives a single Unique guard but the legacy value is populated by other flows → collision/overwrite risk. | **Natural‑key pre‑check** (R6). Do **not** repurpose `SourceSystemIdentifier`. |
| **OQ‑E14‑7** | **Target org / batch size / effort.** | — | Confirm **IBXDEV01**; batch size per E22 (rec. `1` for shared‑location races); effort ~1.5 d + 0.25 d for the contract change (OQ‑E14‑5). |
| **OQ‑E14‑10** *(new)* | **PPA cardinality — how many PPA per practitioner?** Design says "one per practice/group Account referenced". A practitioner can reference **multiple groups** across `groups[]`. | Emit **one PPA per distinct (practitioner × group Account)**. | **One PPA per distinct group Account** the practitioner is affiliated with (dedupe in the batch). Confirm with BA. |

> **Confirmed‑and‑closed (from design §8):** OQ‑E14‑2a/2b (single service, both RTs, PPA Account‑grain), OQ‑E14‑3 (`HealthcareProviderId` null for PPA), OQ‑E14‑6 (runs in PLRelatedBatch), OQ‑E14‑8 (new PPA inserts set `Name` + `IsPrimaryFacility=false`).

---

## 3. Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RK‑1 | **Field mutability unknown** (OQ‑E14‑9) — a mixed insert/update `upsert` could fail if createable‑only fields are set on the update path. | DML error at runtime. | Pilot = **skip existing** (insert‑only). If update needed, describe updateable flags first + strip to the mutable subset. |
| RK‑2 | **`Name` components not in the contract** (OQ‑E14‑5). | Insert fails (`Name` required) or Name is wrong. | Extend the input contract; batch injects names. Test asserts Name format. |
| RK‑3 | **Shared‑location concurrency** — same HCF across practitioners in parallel chunks (E22 OQ‑E22‑1). PLA is practitioner‑grain (safe); PPA is per‑group (shared group). | Duplicate PPA under parallel chunks. | E22 runs **`BatchSize=1`** (design decision); pre‑check + single‑threaded avoids races. |
| RK‑4 | **HCF Id resolution upstream** (E22 §3.1) — if E22 can't resolve `healthcareFacilityId`, PLA rows are skipped. | Missing PLA affiliations. | Depends on E3 `Account.SourceSystemIdentifier` + shared `computeHcfExternalId`. Track as E22/E3 prerequisite; E14 handles null‑facility PLA gracefully (skip + report). |
| RK‑5 | **`IsPrimaryFacility` semantics** — if multiple locations are flagged primary, multiple PLA rows get `true`. | Data quality. | Out of E14 scope (source‑driven); note for BA. E14 applies the per‑row formula faithfully. |
| RK‑6 | **Partial‑success DML vs halt‑on‑failure** — `Database.insert(rows, true)` throws on any bad row → whole step fails. | One bad affiliation fails the chunk. | Per Epic C halt‑on‑failure this is acceptable (retry). If per‑record capture is needed (CL‑E16‑A), switch to `false` + collect errors — confirm. |

---

## 4. Dependencies & prerequisites

- **[CONFIRMED]** `HealthcarePractitionerFacility` object + RTs `PRM_PractitionerLocationAffiliation`, `PRM_PractitionerPracticeAffiliation` (org §3.1).
- **[CONFIRMED]** `PRM_ServiceBase`, `PRM_FormSubUtility.recordTypeId(...)`, `NameNormalize(...)` deployed (in repo).
- **[CONFIRMED]** Upstream Ids exist by seq 4: practitioner PersonContact (E2/seq1), HealthcareFacility + group Account (E13/E3, seq2), Case Manager (E1 intake).
- **[OPEN]** **E22** must inject `recordType`, name components (OQ‑E14‑5), and resolve `healthcareFacilityId`/`accountId` (E22 §3.1). E14 can't be integration‑tested without E22 (unit‑testable in isolation with a stub payload).
- **[OPEN]** **FLS** on `PRM_AsyncJob_Access` for every field E14 writes (WI‑2) — confirm/grant.
- **[CONFIRMED — no metadata]** No new fields, no RT, no permission‑set *object* changes (only FLS confirmation).

---

## 5. Phased execution plan

### Phase 0 — Pre‑build clarifications (gate)
Resolve **OQ‑E14‑1b, OQ‑E14‑5, OQ‑E14‑9, OQ‑E14‑10** and confirm **OQ‑E14‑7**. **No code** until OQ‑E14‑5 (Name contract) and OQ‑E14‑9 (skip vs update) are decided — they change the class shape.

### Phase 1 — Contract & scaffolding
| Field | Detail |
|---|---|
| **Purpose** | Lock the input/output contract (incl. the OQ‑E14‑5 name fields) and create the class skeleton. |
| **Expected outcome** | `PRM_HPFService extends PRM_ServiceBase` compiles; `execute` returns empty `affiliations` for empty input. |
| **Dependencies** | Phase 0 decisions. |
| **Prerequisites** | `PRM_ServiceBase` deployed. |
| **Impacted files** | `classes/PRM_HPFService.cls` (+ `-meta.xml`); design §4 contract update (add name fields). |
| **Validation** | Compiles; empty‑input returns empty. |
| **Testing** | Unit: null/empty `affiliations` → empty response. |
| **Risks** | RK‑2. |
| **Completion** | Class deploys; empty‑path test green. |

### Phase 2 — RT resolution + row builder (PLA + PPA)
| Field | Detail |
|---|---|
| **Purpose** | Build the mixed‑RT `HealthcarePractitionerFacility[]` in memory with all §6/§6.1 derivations. |
| **Expected outcome** | For each affiliation: correct RT, `Name`, required booleans, PLA facility vs PPA blank‑facility, `HealthcareProviderId` null for PPA, `PRM_AttestationDate__c=today`. |
| **Dependencies** | Phase 1. |
| **Prerequisites** | `PRM_FormSubUtility.recordTypeId` for `HealthcarePractitionerFacility`. |
| **Impacted files** | `PRM_HPFService.cls`. |
| **Validation** | Unit assertions per RT (field‑by‑field). |
| **Testing** | PLA row, PPA row, primary‑flag formula, PPA facility‑blank, required booleans non‑null. |
| **Risks** | RK‑2, RK‑5. |
| **Completion** | Builder unit tests green (no DML yet — assert in‑memory). |

### Phase 3 — Idempotency pre‑check + DML
| Field | Detail |
|---|---|
| **Purpose** | Existence pre‑check (OQ‑E14‑1b = service) → insert misses (OQ‑E14‑9 = skip existing); one bulk DML; return `hcpfId` per affiliation (input order). |
| **Expected outcome** | Re‑run creates no duplicates; existing rows are matched (Id returned) and **skipped** for insert. |
| **Dependencies** | Phase 2. |
| **Prerequisites** | FLS (WI‑2). |
| **Impacted files** | `PRM_HPFService.cls`. |
| **Validation** | Two consecutive runs → one row per key; second run inserts 0. |
| **Testing** | Bulk (200+ mixed PLA/PPA), re‑run idempotency, existing‑match returns prior Id. |
| **Risks** | RK‑1, RK‑3, RK‑6. |
| **Completion** | Idempotency + bulk tests green. |

### Phase 4 — FLS, tests to ≥85%, org validation
| Field | Detail |
|---|---|
| **Purpose** | Confirm/grant FLS; finalize `PRM_HPFServiceTest` ≥85%; validate field API names/types against IBXDEV01. |
| **Expected outcome** | Deployable, covered, org‑validated. |
| **Dependencies** | Phases 1–3. |
| **Prerequisites** | Target org access (OQ‑E14‑7). |
| **Impacted files** | `PRM_HPFServiceTest.cls`; `permissionsets/PRM_AsyncJob_Access` (FLS only, if a gap is found). |
| **Validation** | `sf apex run test`; `sf sobject describe` spot‑check. |
| **Testing** | Coverage ≥85%; bulk + negative (missing Name component / missing facility for PLA). |
| **Risks** | RK‑2, RK‑4. |
| **Completion** | DoD (§9 of design) met; tests green; evidence captured. |

### Phase 5 — Integration with E22 (post‑E22)
| Field | Detail |
|---|---|
| **Purpose** | Wire E14 into `PRM_PLRelatedBatch.execute()`; verify affiliations created end‑to‑end + `hcpfId` feeds E19 CMA. |
| **Expected outcome** | Seq‑4 run creates PLA + PPA; CMA rows (E19) created by E22. |
| **Dependencies** | E22 built. |
| **Prerequisites** | E22, E19, E13/E3 outputs. |
| **Impacted files** | `PRM_PLRelatedBatch.cls` (E22 owns). |
| **Validation** | End‑to‑end async run in a scratch/sandbox. |
| **Testing** | Integration test with a multi‑location, multi‑group practitioner. |
| **Risks** | RK‑3, RK‑4. |
| **Completion** | E2E affiliations + CMA correct; halt‑on‑failure honored. |

---

## 6. Effort (re‑estimate)

| Item | d |
|---|---|
| Phase 0 clarifications | 0.25 (BA/TL time) |
| Phases 1–3 (build) | 0.75 |
| Phase 4 (FLS + tests + org validation) | 0.5 |
| Phase 5 (E22 integration) | with E22 |
| Contract change for names (OQ‑E14‑5) | 0.25 |
| **Total** | **~1.5–1.75 d** (design 1.5 d; +0.25 if OQ‑E14‑5 contract work counts here) |

---

## 7. Reference implementation (confirmed design; open items behind marked seams)

> **Pending Clarification seams:** `resolveExisting()` (OQ‑E14‑1b service‑side pre‑check) · skip‑existing (OQ‑E14‑9) · name components from input (OQ‑E14‑5). **Do not deploy until Phase 0 decisions are ratified.**

```apex
/*
* @ClassName    : PRM_HPFService
* @TestClassName: PRM_HPFServiceTest
* @StoryNumber  : E14
* @CreatedBy    : Salesforce
* @Description  : EPIC E E14 "HPF Service" — runs in PLRelatedBatch (seq 4). Builds HealthcarePractitionerFacility
*                 affiliations in ONE mixed-RT bulk DML: PLA (PRM_PractitionerLocationAffiliation, facility-linked)
*                 + PPA (PRM_PractitionerPracticeAffiliation, Account-linked, facility blank). Batch-injected,
*                 SOQL-free except the idempotency pre-check (OQ-E14-1b). Idempotent: pre-check the natural key,
*                 insert misses only (skip existing — OQ-E14-9). Required booleans never null.
*/
public with sharing class PRM_HPFService extends PRM_ServiceBase {

    public class PRM_HPFException extends Exception {}

    private static final String RT_PLA = 'PRM_PractitionerLocationAffiliation';
    private static final String RT_PPA = 'PRM_PractitionerPracticeAffiliation';

    /** Correlated build unit (one per input affiliation, input order preserved). */
    private class Aff {
        Id practitionerId;
        Id healthcareFacilityId;   // PLA only
        Id accountId;              // group (PLA + PPA)
        Id healthcareProviderId;   // PLA optional; null for PPA
        Id caseManagerId;
        Boolean isPrimary;
        Boolean isActive;
        Date effectiveFrom;
        Date effectiveTo;
        String recordType;         // RT_PLA | RT_PPA
        String practitionerName;   // OQ-E14-5 (batch-injected)
        String facilityName;       // OQ-E14-5 (PLA name component)
        String practiceName;       // OQ-E14-5 (PPA name component)
        Id existingHcpfId;         // set by resolveExisting() when a duplicate is found
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'affiliations' => new List<Map<String, Object>>() };
        List<Object> raw = (params == null) ? null : (List<Object>) params.get('affiliations');
        if (raw == null || raw.isEmpty()) { return response; }

        // 1) parse + validate (no SOQL/DML in loop)
        List<Aff> items = new List<Aff>();
        Set<Id> practitionerIds = new Set<Id>();
        for (Object o : raw) {
            Aff a = toAff((Map<String, Object>) o);
            items.add(a);
            if (a.practitionerId != null) { practitionerIds.add(a.practitionerId); }
        }

        // 2) idempotency pre-check (OQ-E14-1b: service-side). Mark existing rows.
        resolveExisting(items, practitionerIds);

        // 3) build the mixed-RT rows for the MISSES only (OQ-E14-9: skip existing)
        Id rtPlaId = PRM_FormSubUtility.recordTypeId(HealthcarePractitionerFacility.SObjectType, RT_PLA);
        Id rtPpaId = PRM_FormSubUtility.recordTypeId(HealthcarePractitionerFacility.SObjectType, RT_PPA);

        List<HealthcarePractitionerFacility> toInsert = new List<HealthcarePractitionerFacility>();
        List<Aff> insertOrder = new List<Aff>();
        for (Aff a : items) {
            if (a.existingHcpfId != null) { continue; }         // skip — already present
            toInsert.add(buildRow(a, rtPlaId, rtPpaId));
            insertOrder.add(a);
        }

        // 4) ONE bulk insert (all-or-nothing; halt-on-failure per Epic C — RK-6)
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision d = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            List<SObject> safe = d.getRecords();
            insert safe;
            for (Integer i = 0; i < safe.size(); i++) {
                insertOrder.get(i).existingHcpfId = safe.get(i).Id;   // map new Id back
            }
        }

        // 5) response in input order
        List<Map<String, Object>> out = new List<Map<String, Object>>();
        for (Aff a : items) {
            out.add(new Map<String, Object>{
                'practitionerId' => a.practitionerId,
                'healthcareFacilityId' => a.healthcareFacilityId,
                'hcpfId' => a.existingHcpfId
            });
        }
        response.put('affiliations', out);
        return response;
    }

    /** OQ-E14-1b (service-side pre-check). One bulk SOQL; builds a natural-key set and stamps existingHcpfId. */
    private void resolveExisting(List<Aff> items, Set<Id> practitionerIds) {
        if (practitionerIds.isEmpty()) { return; }
        Map<String, Id> byKey = new Map<String, Id>();
        for (HealthcarePractitionerFacility h : [
            SELECT Id, PractitionerId, HealthcareFacilityId, AccountId, RecordTypeId
            FROM HealthcarePractitionerFacility
            WHERE PractitionerId IN :practitionerIds
            WITH USER_MODE
        ]) {
            byKey.put(keyFor(h.PractitionerId, h.RecordTypeId, h.HealthcareFacilityId, h.AccountId), h.Id);
        }
        Id rtPlaId = PRM_FormSubUtility.recordTypeId(HealthcarePractitionerFacility.SObjectType, RT_PLA);
        Id rtPpaId = PRM_FormSubUtility.recordTypeId(HealthcarePractitionerFacility.SObjectType, RT_PPA);
        for (Aff a : items) {
            Id rtId = (RT_PPA.equals(a.recordType)) ? rtPpaId : rtPlaId;
            Id facForKey = (RT_PPA.equals(a.recordType)) ? null : a.healthcareFacilityId;
            Id accForKey = (RT_PPA.equals(a.recordType)) ? a.accountId : null;
            a.existingHcpfId = byKey.get(keyFor(a.practitionerId, rtId, facForKey, accForKey));
        }
        // ── UPDATE-PASS (OQ-E14-9): if legacy refresh semantics are required, add a bulk UPDATE here
        //    over the matched rows for the mutable subset ONLY (needs org describe of updateable flags). ──
    }

    private String keyFor(Id practitionerId, Id rtId, Id facilityId, Id accountId) {
        return String.valueOf(practitionerId) + '|' + String.valueOf(rtId)
             + '|' + String.valueOf(facilityId) + '|' + String.valueOf(accountId);
    }

    private HealthcarePractitionerFacility buildRow(Aff a, Id rtPlaId, Id rtPpaId) {
        Boolean isPpa = RT_PPA.equals(a.recordType);
        if (!isPpa && !RT_PLA.equals(a.recordType)) {
            throw new PRM_HPFException('E14: unknown recordType "' + a.recordType + '"');
        }
        HealthcarePractitionerFacility h = new HealthcarePractitionerFacility();
        h.RecordTypeId          = isPpa ? rtPpaId : rtPlaId;
        h.PractitionerId        = a.practitionerId;
        h.AccountId             = a.accountId;                                   // group (both RTs per design §6)
        h.HealthcareFacilityId  = isPpa ? null : a.healthcareFacilityId;        // §6 formula
        h.HealthcareProviderId  = isPpa ? null : a.healthcareProviderId;        // §6.1 (null for PPA)
        h.Name                  = buildName(a, isPpa);                          // OQ-E14-5
        h.IsPrimaryFacility     = isPpa ? false : (a.isPrimary == true);        // §6 formula; REQUIRED
        h.IsActive              = (a.isActive == true);                        // REQUIRED
        h.PRM_Pending__c        = false;                                       // REQUIRED default
        h.EffectiveFrom         = a.effectiveFrom;
        h.EffectiveTo           = a.effectiveTo;
        h.PRM_AttestationDate__c = Date.today();
        h.PRM_CaseManager__c    = a.caseManagerId;
        return h;
    }

    /** OQ-E14-5: Name = practitionerName @ (facilityName for PLA | practiceName for PPA). */
    private String buildName(Aff a, Boolean isPpa) {
        String left = PRM_FormSubUtility.NameNormalize(a.practitionerName);
        String right = isPpa ? a.practiceName : a.facilityName;
        if (String.isBlank(left) || String.isBlank(right)) {
            throw new PRM_HPFException('E14: Name components missing (OQ-E14-5) for practitioner ' + a.practitionerId);
        }
        return (left + ' @ ' + right).abbreviate(255);
    }

    private Aff toAff(Map<String, Object> m) {
        Aff a = new Aff();
        a.practitionerId       = (Id) m.get('practitionerId');
        a.healthcareFacilityId = (Id) m.get('healthcareFacilityId');
        a.accountId            = (Id) m.get('accountId');
        a.healthcareProviderId = (Id) m.get('healthcareProviderId');
        a.caseManagerId        = (Id) m.get('caseManagerId');
        a.isPrimary            = asBool(m.get('isPrimary'));
        a.isActive             = asBool(m.get('isActive'));
        a.effectiveFrom        = asDate(m.get('effectiveFrom'));
        a.effectiveTo          = asDate(m.get('effectiveTo'));
        a.recordType           = (String) m.get('recordType');
        a.practitionerName     = (String) m.get('practitionerName');  // OQ-E14-5
        a.facilityName         = (String) m.get('facilityName');      // OQ-E14-5
        a.practiceName         = (String) m.get('practiceName');      // OQ-E14-5
        if (a.practitionerId == null) { throw new PRM_HPFException('E14: practitionerId is required'); }
        if (String.isBlank(a.recordType)) { throw new PRM_HPFException('E14: recordType is required'); }
        return a;
    }

    private Boolean asBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date asDate(Object o) {
        if (o == null) { return null; }
        if (o instanceof Date) { return (Date) o; }
        return Date.valueOf(String.valueOf(o));   // ISO yyyy-MM-dd
    }
}
```

> **Field‑name caveats to validate at build (§Phase 4):** `PRM_AttestationDate__c`, `PRM_Pending__c`, `PRM_CaseManager__c` API names are from design §3.1/§6 (org‑stated) — confirm via `sf sobject describe HealthcarePractitionerFacility`. `IsPrimaryFacility`, `IsActive`, `EffectiveFrom`, `EffectiveTo`, `HealthcareProviderId`, `AccountId`, `HealthcareFacilityId`, `PractitionerId`, `Name` are standard HC fields (design §3.1).

---

## 8. Test class (outline — bring to ≥85%)

```apex
@IsTest
private class PRM_HPFServiceTest {
    // Test-data factory: Person Account (practitioner) → PersonContact; group Account; HealthcareFacility; IndividualApplication (CM).
    // NOTE: HealthcarePractitionerFacility is a standard HC object — assert RTs PRM_PractitionerLocationAffiliation /
    //       PRM_PractitionerPracticeAffiliation exist in the org before running (Phase 4).

    @IsTest static void emptyInput_returnsEmpty() { /* null + empty affiliations → empty response */ }

    @IsTest static void buildsPla_setsFacilityAndPrimary() {
        // one PLA affiliation → RT=PLA, HealthcareFacilityId set, IsPrimaryFacility = isPrimary,
        // Name = 'Practitioner @ Facility', PRM_Pending__c=false, PRM_AttestationDate__c=today.
    }

    @IsTest static void buildsPpa_facilityBlank_hcpNull_primaryFalse() {
        // one PPA affiliation → RT=PPA, HealthcareFacilityId null, HealthcareProviderId null,
        // AccountId set, IsPrimaryFacility=false, Name='Practitioner @ Practice'.
    }

    @IsTest static void bulk_mixedRt_oneDml() {
        // 200+ mixed PLA/PPA across several practitioners; assert Limits.getDmlStatements() == 1 (+ pre-check SOQL == 1).
    }

    @IsTest static void idempotent_rerunNoDuplicate() {
        // run twice with the same input → second run inserts 0; hcpfId returned matches the first run's Id.
    }

    @IsTest static void missingNameComponent_throws() { /* OQ-E14-5 guard */ }
    @IsTest static void unknownRecordType_throws() { /* buildRow guard */ }
    @IsTest static void nullFacilityForPla_reportsGracefully() { /* RK-4: PLA with null facility */ }
}
```

**Coverage targets:** empty‑path, PLA build, PPA build, bulk one‑DML, re‑run idempotency, negative (missing name, unknown RT), null‑facility PLA. **Assert outcomes**, not just "no exception" (org rule §6).

---

## 9. FLS / permission set (no object metadata)

- **WI‑2 (confirm/grant):** on `PRM_AsyncJob_Access`, **Edit** FLS for every field E14 writes on `HealthcarePractitionerFacility`: `PractitionerId`, `AccountId`, `HealthcareFacilityId`, `HealthcareProviderId`, `Name`, `RecordTypeId`, `IsPrimaryFacility`, `IsActive`, `PRM_Pending__c`, `EffectiveFrom`, `EffectiveTo`, `PRM_AttestationDate__c`, `PRM_CaseManager__c` + **Read** on `SourceSystemIdentifier` (pre‑check). **No new fields / RTs / objects.**
- If FLS is already provisioned via another permission set (as with E16), only **verify** — do not duplicate.

---

## 10. Deploy & validation commands

```bash
# Org schema validation (Phase 4 — confirm field API names + required/updateable flags for OQ-E14-9)
sf sobject describe --sobject HealthcarePractitionerFacility --target-org IBXDEV01 --json > hpf-describe.json

# Deploy the service + test (after Phase 0 sign-off)
sf project deploy start \
  -d "force-app/main/default/classes/PRM_HPFService.cls" \
  -d "force-app/main/default/classes/PRM_HPFService.cls-meta.xml" \
  -d "force-app/main/default/classes/PRM_HPFServiceTest.cls" \
  -d "force-app/main/default/classes/PRM_HPFServiceTest.cls-meta.xml" \
  --target-org IBXDEV01

# Run tests with coverage (gate ≥85%)
sf apex run test -n PRM_HPFServiceTest -r human -c -w 20 --target-org IBXDEV01
```

---

## 11. Definition of Done (execution‑plan level)

- [ ] **Phase 0** open questions decided: OQ‑E14‑1b, OQ‑E14‑5, OQ‑E14‑9, OQ‑E14‑10, OQ‑E14‑7.
- [ ] Design §4 contract updated with the OQ‑E14‑5 **name components** (`practitionerName`, `facilityName`, `practiceName`).
- [ ] `PRM_HPFService` built per §7 (single service, both RTs, one bulk DML, service‑side pre‑check, skip‑existing).
- [ ] Field API names/types + required/updateable flags validated against IBXDEV01 (`sf sobject describe`).
- [ ] FLS confirmed on `PRM_AsyncJob_Access` (WI‑2) — no new metadata.
- [ ] `PRM_HPFServiceTest` ≥ 85% incl. bulk (one DML), re‑run idempotency, PLA + PPA, primary‑flag formula, negatives.
- [ ] Design‑doc DoD (§9 of `E14_PRM_HPFService.md`) satisfied.
- [ ] Integration with **E22** (Phase 5) verified once E22 is built; `hcpfId` feeds E19 CMA.

---

## 12. Recommendations (summary)

1. **Decide the four open questions first (Phase 0)** — OQ‑E14‑5 (name contract) and OQ‑E14‑9 (skip vs update) change the class shape; don't code before they're ratified.
2. **Service‑side pre‑check + skip‑existing** for the pilot (OQ‑E14‑1b/OQ‑E14‑9) — matches the sibling idempotent services (E15/E16/E19) and avoids the unverified field‑mutability risk (RK‑1). Add an update pass only if effective‑date refresh on re‑submit is a business rule.
3. **Extend the input contract with name components** (OQ‑E14‑5) rather than letting E14 query — preserves the SOQL‑free boundary.
4. **Keep CMA/CDM out of E14** — E22 owns them; note the seq‑4 HFN‑context caveat (OQ‑E14‑4: HFN doesn't exist until seq 5).
5. **Validate updateable flags in‑org** before ever enabling the update pass; until then, insert‑only is the safe, idempotent default.
