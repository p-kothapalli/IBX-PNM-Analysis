# E19 · `PRM_CMAService` — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review.** This plan now includes a **complete reference implementation** of `PRM_CMAService` (**Appendix A**) plus the `PRM_FormSubUtility` additions (E19 §4.1), for review. **Nothing is deployed** until this plan is reviewed, the Open Questions (§7) are answered, and the target org (OQ‑3) is confirmed.
>
> **Source of truth:** `E19_PRM_CMAService.md` (the CMA service design + §10 Validation Log F‑1…F‑12). This plan restates and expands only what that doc explicitly defines; anything not stated is **UNKNOWN** and surfaced as an Open Question — not assumed.
>
> **Tags:** **[CONFIRMED]** (documented/decided), **[OPEN]** (needs a decision), **[RISK]**, **[RECOMMENDATION]**. Tasks blocked by an unresolved [OPEN] item are **⛔ Pending Clarification**.

---

## 1. Confirmed requirements (from `E19_PRM_CMAService.md`)

- **[CONFIRMED]** A **common service** `PRM_CMAService` that writes `PRM_CaseManagerAssociation__c` (junction linking created/updated records → the Case Manager). Invoked by the **relevant** record‑creating services (those whose object has a CMA record type).
- **[CONFIRMED]** **Base‑class contract:** `extends PRM_ServiceBase`; `execute(Map<String,Object>) : Map<String,Object>`, reading `params.associations` (a `List` of requests). Each request: `{ caseManagerId, recordType, lookups{field→Id}, requestType? }`.
- **[CONFIRMED]** **`caseManagerId` is invoker‑supplied** — CMA does not resolve it from any object.
- **[CONFIRMED]** **Object facts (org‑verified, IBXDEV01):** `PRM_CaseManager__c` (→ IndividualApplication) **required**; `Name` **autonumber** (not set); `PRM_RequestType__c` **left null** (F‑10); **no External Id/Unique** field → idempotency by pre‑check; **14 active record types**; 12 business lookups, all **nullable** (so contextual lookups are best‑effort).
- **[CONFIRMED]** **One CMA row per "primary" created/updated record, per Case Manager**, RecordType set, **all available contextual lookups** populated (multi‑FK rows). Primary = the record type's own most‑specific record (unique per association).
- **[CONFIRMED]** **Idempotency = existence pre‑check** by natural key **(`PRM_CaseManager__c` + RecordType + primary lookup Id)** → key `cm_rtId_primaryId`; insert only missing. No new field.
- **[CONFIRMED]** **Insert mode = all‑or‑nothing**; a request missing its **primary** lookup or with an **unknown/inactive `recordType`** → **fail the request** (→ step failure/DLQ).
- **[CONFIRMED]** **Invocation:** the **batch aggregates** all CMA requests for its chunk and calls `execute` **once, in the same transaction** as record creation (CMA failure fails the step); **E1 (sync intake) calls CMA directly** for the Practitioner CMA. Same `execute` for both.
- **[CONFIRMED]** **Created AND updated/reused** records get a CMA (pre‑check keeps it duplicate‑safe).
- **[CONFIRMED]** **Network vs Taxonomy RT** chosen by the HFN record's own RT (`PRM_FacilityNw`→`Practice_Location_Network`; `PRM_FacilityTx`→`Practice_Location_Taxonomy`).
- **[CONFIRMED]** **Mapping + RT helper on `PRM_FormSubUtility`** (new methods — `cmaFieldSets()` and the general cached `recordTypeId(SObjectType, devName)`), **specified in E19 §4.1** because **Epic B is already generated** (don't reopen Epic B).
- **[CONFIRMED]** **RT→lookup map** (14 RTs) per E19 §6, incl. `Healthcare_Provider_Taxonomy → PRM_HealthcareProviderTaxonomy__c` (confirmed) and Level‑4 contextual `PRM_Identifier__c` = CAQH (best‑effort).
- **[CONFIRMED]** **Scope:** all 14 record types mapped. `Program_Participation` / `Practice_Location_Association` have no E1–E18 producer → mapping kept, exercised later.
- **[CONFIRMED]** **Effort:** ~1.0 engineer‑day (Plan §8 catalog). **Depends on:** EPIC B (`PRM_ServiceBase`, `PRM_FormSubUtility`), EPIC A (`PRM_AsyncJob_Access`), the existing `PRM_CaseManagerAssociation__c`.

---

## 2. Constraints

- **[CONFIRMED]** No new fields on `PRM_CaseManagerAssociation__c` (pre‑check idempotency).
- **[CONFIRMED]** Bulk‑safe: **one pre‑check SOQL + one bulk insert** per invocation; no DML/SOQL/describe in loops; RT Ids cached.
- **[CONFIRMED]** Runs in the **caller's transaction** (batch step / intake) — CMA does not open its own async context.
- **[CONFIRMED]** `with sharing`; enforce CRUD/FLS on insert (F‑12).
- **[CONFIRMED]** `PRM_RequestType__c` not set.

---

## 3. Acceptance criteria

- **[CONFIRMED]** `PRM_CMAService.execute({associations})` builds one CMA row per request (RT + `PRM_CaseManager__c` + primary + available contextual lookups), pre‑checks existing, inserts only new — **all‑or‑nothing**.
- **[CONFIRMED]** Re‑running with the same inputs creates **no duplicate** CMA rows (idempotent).
- **[CONFIRMED]** A request missing its primary lookup or with an unknown/inactive RT **fails** (surfaced to the caller / step).
- **[CONFIRMED]** `PRM_FormSubUtility.cmaFieldSets()` returns the 14‑RT map; `recordTypeId(...)` resolves & caches RT Ids.
- **[CONFIRMED]** Governor: constant SOQL/DML regardless of request count; bulk test passes.
- **[CONFIRMED]** Apex ≥ 85% per class incl. a bulk test + a re‑run/idempotency test; Test Evidence Report + human sign‑off (Epic A §A7) before `main`→`master`.

---

## 4. Phases, milestones & task breakdown

> Build order: Phase 0 (confirm) → Phase 1 (utility) → Phase 2 (access) → Phase 3 (service) → Phase 4 (caller contract/stub) → Phase 5 (tests) → Phase 6 (evidence) → Phase 7 (VCS). Each task: Purpose · Outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion.

### Phase 0 — Prerequisites & confirmations *(M0)* ⛔ Pending Clarification (OQ‑1, OQ‑2, OQ‑3)
- **T0.1 — Confirm target org** (scratch/sandbox) for deploy + tests (OQ‑3). Outcome: org confirmed. Risk: none functional. Completion: org set.
- **T0.2 — Verify prerequisites in the org:** `PRM_CaseManagerAssociation__c` + the 14 RTs + 12 lookups present (already validated on IBXDEV01); `PRM_ServiceBase` + `PRM_FormSubUtility` exist; `PRM_AsyncJob_Access` exists. Validation: describe/deploy dry‑run. Completion: all present.
- **T0.3 — Resolve impl decisions:** F‑11 pre‑check query shape (OQ‑1) + F‑12 CRUD/FLS enforcement approach (OQ‑2). Completion: both decided.

### Phase 1 — Utility methods on `PRM_FormSubUtility` *(M1)*
- **T1.1 — `cmaFieldSets()` (+ `cmaFieldSet(recordType)`)**
  - Purpose: centralize the RT→{primary, contextual} map (E19 §6) outside the service.
  - Outcome: returns the 14‑RT map; accessor returns one set.
  - Dependencies: EPIC B `PRM_FormSubUtility` (exists). Prerequisites: T0.2.
  - Impacted: `classes/PRM_FormSubUtility.cls` (add methods; Epic B not reopened — change is additive).
  - Validation: unit test asserts each RT maps to the expected primary + contextual list (matches E19 §6).
  - Testing: Apex unit (map contents). Risks: **[RISK]** map drift vs the object's actual lookups — covered by T5.4 org‑describe assertion.
  - Completion: method returns the full map; tests green.
- **T1.2 — `recordTypeId(SObjectType, devName)` cached helper**
  - Purpose: general cached RT‑by‑DeveloperName (resolves CL‑E5; reused by E‑services).
  - Outcome: cached describe lookup; O(1) after first call.
  - Dependencies: none. Prerequisites: T0.2.
  - Impacted: `PRM_FormSubUtility.cls`.
  - Validation: returns the active RT Id for a known DeveloperName; cached on 2nd call (no extra describe).
  - Testing: Apex unit. Risks: **[RISK]** unknown/inactive devName → null → caller must handle (see T3.3). Completion: tests green.

### Phase 2 — Permission‑set access *(M1)*
- **T2.1 — `PRM_AsyncJob_Access` FLS/CRUD for CMA** (E19 §3 WI‑1)
  - Purpose: let the batch/intake user insert CMA rows.
  - Outcome: object Create/Read on `PRM_CaseManagerAssociation__c` + Edit FLS on `PRM_CaseManager__c`, `RecordTypeId`, `PRM_RequestType__c`, and all §6 lookup fields, added to `PRM_AsyncJob_Access`.
  - Dependencies: EPIC A permission set. Prerequisites: T0.2.
  - Impacted: `permissionsets/PRM_AsyncJob_Access.permissionset-meta.xml`.
  - Validation: deploy; running user `isCreateable`/`isUpdateable` true for the fields.
  - Testing: deploy + a permission assertion in tests. Risks: **[RISK]** missing a lookup field's FLS → insert drops it silently (or fails under stripInaccessible). Completion: permset deploys; access verified.

### Phase 3 — `PRM_CMAService` *(M2)* — build the **complete class** (Appendix A), not a skeleton
- **T3.1 — Complete class + contract (Appendix A)**
  - Purpose: implement the **full** `PRM_CMAService` (`extends PRM_ServiceBase`; `execute(Map)` reading `params.associations`) exactly per **Appendix A** — parse → build → validate → pre‑check → all‑or‑nothing FLS‑safe insert → response. T3.2–T3.5 are the internal breakdown of that one class.
  - Outcome: deployable, fully‑implemented class (not a stub).
  - Dependencies: T1.x. Prerequisites: Phase 0–2.
  - Impacted: `classes/PRM_CMAService.cls` (+ inner `PRM_CMAException`). Validation: compiles; behaviour matches Appendix A + E19 §4/§7. Completion: full class + tests green.
- **T3.2 — Build candidate rows**
  - Purpose: per request, resolve RT Id (`recordTypeId`), look up the RT field set (`cmaFieldSet`), set `PRM_CaseManager__c` + primary (required) + available contextual lookups; `PRM_RequestType__c` left null.
  - Outcome: in‑memory `PRM_CaseManagerAssociation__c[]` (no DML).
  - Dependencies: T1.1/T1.2. Validation: a request → a correctly‑shaped row (RT + lookups). Testing: per‑RT unit cases (incl. multi‑FK e.g. Level‑4, Network). Risks: **[RISK]** network/taxonomy RT must match the HFN record's RT (caller‑supplied `recordType`) — covered by contract (T4.1). Completion: builder unit‑tested for all 14 RTs.
- **T3.3 — Request validation**
  - Purpose: missing **primary** lookup or unknown/inactive `recordType` → **fail the request** (all‑or‑nothing).
  - Outcome: invalid request raises/propagates an error (no partial commit).
  - Dependencies: T3.2. Validation: negative tests (missing primary; bad RT). Risks: **[RISK]** error type/handling must integrate with the batch's DLQ/step‑failure path (Epic C) — confirm the exception contract. Completion: negative tests green.
- **T3.4 — Idempotent pre‑check + bulk insert**
  - Purpose: one bulk query for existing rows (by `PRM_CaseManager__c` IN + `RecordTypeId` IN), build `Set<String>` of `cm_rtId_primaryId`, insert only new — **all‑or‑nothing** (`Database.insert(rows, true)`).
  - Outcome: no duplicates on re‑run; constant SOQL/DML.
  - Dependencies: T3.2/T3.3, T0.3 (F‑11 query shape). Prerequisites: T2.1 (FLS).
  - Impacted: `PRM_CMAService.cls`. Validation: re‑run test → counts unchanged; query selects per‑RT primary fields and keys per row's RT (F‑11).
  - Testing: bulk + idempotency tests. Risks: **[RISK]** building keys requires reading the *correct primary field per RT* from existing rows (F‑11); **[RISK]** selectivity — query filtered by `PRM_CaseManager__c` (indexed) is selective. Completion: idempotent + bulk tests green.
- **T3.5 — CRUD/FLS enforcement (F‑12)**
  - Purpose: enforce object/field access on insert per standards (`with sharing` + `Security.stripInaccessible` or explicit checks — per T0.3/OQ‑2).
  - Outcome: insert respects FLS/CRUD.
  - Dependencies: T0.3. Validation: test as a least‑privileged user. Risks: **[RISK]** stripInaccessible could silently drop a lookup if FLS missing (ties to T2.1). Completion: enforced + tested.

### Phase 4 — Caller integration contract *(M2)*
- **T4.1 — Define the caller contract + test stub** ⛔ Pending Clarification (OQ‑4)
  - Purpose: lock how callers assemble `associations` — **E1 calls directly** (Practitioner CMA, done in E01 §5.1); **batches aggregate** all per‑chunk requests and call once (Plan C4). Each E‑service doc adds a "CMA association" note (its RT + lookups).
  - Outcome: a documented per‑service request spec + a **test stub** caller (so CMA is testable without the real batches/E‑services).
  - Dependencies: T3.x. Prerequisites: agreement on the per‑service RT/lookup contributions (OQ‑4).
  - Impacted: each E‑service doc (CMA note); the batch wrappers (EPIC E) — **out of this task's build**, contract only.
  - Validation: stub caller drives `execute` for representative RTs. Risks: **[RISK]** cross‑epic — the actual aggregation lives in EPIC E batches; if not wired, CMA rows won't be created in production. Completion: contract documented + stub test.

### Phase 5 — Testing *(M3)*
- **T5.1 — Unit:** per‑RT build (all 14), incl. multi‑FK (Level‑4, Network, Address, Provider_Feature).
- **T5.2 — Idempotency/re‑run:** execute twice → no duplicate CMA rows.
- **T5.3 — Bulk/governor:** large request set (e.g. 200+) → constant 1 SOQL + 1 DML; assert limits.
- **T5.4 — Mapping‑vs‑org guard:** assert each `cmaFieldSets()` lookup field & RT exists on `PRM_CaseManagerAssociation__c` (describe) — catches map drift.
- **T5.5 — Negative:** missing primary; unknown/inactive RT → request fails (all‑or‑nothing, no partial insert).
- **T5.6 — FLS:** least‑privileged user via `PRM_AsyncJob_Access`.
  - Dependencies: Phase 1–3. Completion: ≥ 85% coverage; all suites green.

### Phase 6 — Evidence & governance *(M4)* (Epic A §A7)
- **T6.1 —** Test Evidence Report (Apex coverage + org spot‑check of CMA rows: correct RT/lookups, no dup on re‑run) + human sign‑off. Risks: **[RISK]** no org → can't run; ties to OQ‑3. Completion: evidence + sign‑off.

### Phase 7 — Version control *(M4)* (E19 §11 / Epic A §A8)
- **T7.1 —** Branch `epic-e/cma-service`; PR into `main` (green CI + 1 review); squash‑merge; promote at the Epic E milestone + tag. Single‑owner rule on `PRM_FormSubUtility` (land its new methods first / coordinate). Commit prefix `[E19]`.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] F‑11 pre‑check key construction.** Recommend: from the chunk, collect distinct `(rtId → primaryField)` via `cmaFieldSets()`; one SOQL selecting **all** those primary fields + `PRM_CaseManager__c` + `RecordTypeId` over `PRM_CaseManager__c IN :cms`; per existing row, read the primary field that matches its RT to build `cm_rtId_primaryId`. Keeps it one query.
- **[RECOMMENDATION] F‑12 enforcement.** Recommend `Security.stripInaccessible(AccessType.CREATABLE, rows)` before insert + a clear failure if required fields get stripped (paired with T2.1 FLS).
- **[RECOMMENDATION] Cross‑epic wiring (T4.1).** CMA is only *useful* if the batches/E‑services actually call it. Recommend each E‑service doc carries a small "CMA association" note (RT + lookups), and the batch wrappers (EPIC E) own the aggregation — track as an EPIC E deliverable so CMA isn't built but left uninvoked.
- **[RISK] Map drift.** `cmaFieldSets()` hardcodes field API names; if the object changes, the service silently mis‑maps. Mitigated by T5.4 (describe assertion).
- **[RISK] Same‑transaction failure blast radius.** Because CMA runs in the caller's transaction (all‑or‑nothing), a CMA failure rolls back that batch step / intake. Intended (atomic), but means a CMA mapping bug blocks the whole step until fixed/retried.

---

## 6. Gaps & hidden dependencies

- **Target org** (OQ‑3) — gates deploy/test.
- **Impl decisions** F‑11 (query shape) + F‑12 (FLS enforcement) — OQ‑1/OQ‑2.
- **Caller wiring (cross‑epic)** — the EPIC E batches must aggregate + call CMA; E1 already specced (E01 §5.1). Without it CMA is dead code in prod.
- **Exception contract** with Epic C DLQ/step‑failure (T3.3) — how a failed CMA surfaces as a step failure.
- **`PRM_FormSubUtility` single‑owner** — its new methods are shared (CL‑E5); coordinate the branch.

---

## 7. Open Questions (must be answered before/along build)

- **OQ‑1 (F‑11) — pre‑check query shape.** Confirm the "select per‑RT primary fields, key per row's RT" approach (§5 recommendation) vs an alternative. *Recommendation:* as in §5.
- **OQ‑2 (F‑12) — CRUD/FLS enforcement** mechanism (`stripInaccessible` vs explicit checks). *Recommendation:* `stripInaccessible`.
- **OQ‑3 — Target org** for deploy/test. *(Gates Phases 6–7.)*
- **OQ‑4 — Per‑service CMA request contributions** (which RT + which created Id → which lookup, for each E‑service) + confirmation that the **batch** owns aggregation. *Recommendation:* add a "CMA association" note to each E‑service doc; batches aggregate (Plan C4).

*(All design‑level questions from E19 §10 are already resolved/decided; the above are execution/wiring items.)*

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R‑1 | Map drift vs object schema | Medium | Medium | T5.4 describe assertion; mapping in one utility method |
| R‑2 | Missing lookup FLS on permset → fields dropped/insert fails | Medium | Medium | T2.1 covers all §6 lookups; T5.6 FLS test |
| R‑3 | Pre‑check key built from wrong primary field per RT | Medium | High (dupes/over‑skip) | T3.4 + F‑11 design; idempotency test T5.2 |
| R‑4 | CMA not invoked by batches (cross‑epic) | Medium | High (no associations in prod) | T4.1 contract + EPIC E deliverable tracking |
| R‑5 | Same‑txn CMA failure blocks the step | Low–Med | Medium | Accepted (atomic); idempotent retry after fix |
| R‑6 | No target org | Medium | High | OQ‑3 |
| R‑7 | `PRM_FormSubUtility` parallel edits (shared) | Low | Medium | Single‑owner rule; land utility methods first |

---

## 9. Sequencing & effort

- **Order:** Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7. Utility (Phase 1) + permset (Phase 2) before the service (Phase 3); caller contract (Phase 4) can run parallel to tests.
- **Effort (indicative, within the ~1.0 d catalog estimate):** utility methods ~0.25 · permset ~0.1 · service (build + pre‑check + validation + FLS) ~0.4 · tests ~0.25 · evidence/VCS folded in. *(Re‑confirm after OQ‑1/OQ‑2.)*
- **Depends on:** EPIC B (`PRM_ServiceBase`, `PRM_FormSubUtility`) + EPIC A (`PRM_AsyncJob_Access`) on `main`; the existing `PRM_CaseManagerAssociation__c`.
- **Blocks:** the EPIC E batches/E‑services that aggregate and call CMA (and E1's Practitioner‑CMA call).

---

## 10. What happens after sign‑off

Resolve OQ‑1…OQ‑4 (esp. the target org and the caller‑wiring contract). Then build in order: `PRM_FormSubUtility` methods → permset FLS → `PRM_CMAService` (**complete class — Appendix A**) → caller stub → tests (unit/idempotency/bulk/map‑guard/negative/FLS) → Test Evidence Report → human governance sign‑off (A7) before any `main`→`master`. **Nothing is deployed until the org (OQ‑3) and the remaining items are confirmed.**

---

## Appendix A — Complete reference implementation

> Full, deployable `PRM_CMAService`. Pairs with the `PRM_FormSubUtility` additions in **E19 §4.1** (`cmaFieldSets()`, `cmaFieldSet(...)`, `recordTypeId(...)`). Implements F‑11 (per‑RT primary key in the pre‑check) and F‑12 (FLS via `stripInaccessible`). `response` is the protected `PRM_ServiceBase` field.

```apex
public with sharing class PRM_CMAService extends PRM_ServiceBase {

    /** Thrown for an invalid request (missing primary / unknown-inactive RT / missing caseManagerId). */
    public class PRM_CMAException extends Exception {}

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>();
        List<Object> associations = (params == null) ? null : (List<Object>) params.get('associations');
        if (associations == null || associations.isEmpty()) {
            response.put('caseManagerAssociationIds', new List<Id>());
            return response;
        }

        // ── 1) parse requests → build candidate rows + dedupe keys (no DML/SOQL in loop) ──
        List<PRM_CaseManagerAssociation__c> candidates = new List<PRM_CaseManagerAssociation__c>();
        List<String> candidateKeys = new List<String>();
        Set<Id> cmIds = new Set<Id>();
        Set<Id> rtIds = new Set<Id>();
        Map<Id, String> rtIdToPrimary = new Map<Id, String>();   // rtId -> primary lookup field (for the pre-check, F-11)

        for (Object o : associations) {
            Map<String, Object> req = (Map<String, Object>) o;
            Id     caseManagerId = (Id) req.get('caseManagerId');
            String recordType    = (String) req.get('recordType');
            Map<String, Object> lookups = (Map<String, Object>) req.get('lookups');

            if (caseManagerId == null)        throw new PRM_CMAException('CMA: caseManagerId is required');
            if (String.isBlank(recordType))   throw new PRM_CMAException('CMA: recordType is required');

            PRM_FormSubUtility.CMAFieldSet fs = PRM_FormSubUtility.cmaFieldSet(recordType);
            if (fs == null)                   throw new PRM_CMAException('CMA: unknown recordType "' + recordType + '"');

            Id rtId = PRM_FormSubUtility.recordTypeId(PRM_CaseManagerAssociation__c.SObjectType, recordType);
            if (rtId == null)                 throw new PRM_CMAException('CMA: inactive/unknown recordType "' + recordType + '"');

            Id primaryId = (lookups == null) ? null : (Id) lookups.get(fs.primary);
            if (primaryId == null)            throw new PRM_CMAException('CMA: missing primary lookup "' + fs.primary + '" for "' + recordType + '"');

            PRM_CaseManagerAssociation__c row = new PRM_CaseManagerAssociation__c();
            row.PRM_CaseManager__c = caseManagerId;     // required
            row.RecordTypeId       = rtId;
            row.put(fs.primary, primaryId);             // primary lookup
            for (String ctx : fs.context) {             // contextual lookups — best-effort (set when provided)
                Object cid = (lookups == null) ? null : lookups.get(ctx);
                if (cid != null) row.put(ctx, (Id) cid);
            }
            // PRM_RequestType__c left null (F-10); set only if a caller explicitly provides one
            Object reqType = req.get('requestType');
            if (reqType != null) row.PRM_RequestType__c = (String) reqType;

            candidates.add(row);
            candidateKeys.add(buildKey(caseManagerId, rtId, primaryId));
            cmIds.add(caseManagerId);
            rtIds.add(rtId);
            rtIdToPrimary.put(rtId, fs.primary);
        }

        // ── 2) one bulk pre-check → existing keys ──
        Set<String> existing = existingKeys(cmIds, rtIds, rtIdToPrimary);

        // ── 3) keep only new candidates ──
        List<PRM_CaseManagerAssociation__c> toInsert = new List<PRM_CaseManagerAssociation__c>();
        for (Integer i = 0; i < candidates.size(); i++) {
            if (!existing.contains(candidateKeys[i])) toInsert.add(candidates[i]);
        }

        // ── 4) FLS-safe, all-or-nothing insert ──
        List<Id> createdIds = new List<Id>();
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            List<SObject> safeRows = decision.getRecords();
            insert safeRows;                              // allOrNone = true (default) — F-4
            for (SObject s : safeRows) createdIds.add(s.Id);
        }

        response.put('caseManagerAssociationIds', createdIds);
        return response;
    }

    /** Dedupe discriminator: Case Manager + RecordType + primary lookup Id. */
    private String buildKey(Id caseManagerId, Id rtId, Id primaryId) {
        return caseManagerId + '_' + rtId + '_' + primaryId;
    }

    /** One bulk SOQL over the chunk's Case Managers + RecordTypes → set of existing dedupe keys (F-11). */
    private Set<String> existingKeys(Set<Id> cmIds, Set<Id> rtIds, Map<Id, String> rtIdToPrimary) {
        Set<String> keys = new Set<String>();
        if (cmIds.isEmpty() || rtIds.isEmpty()) return keys;

        // select the DISTINCT primary lookup fields used across the RTs in this chunk
        Set<String> primaryFields = new Set<String>(rtIdToPrimary.values());
        String soql = 'SELECT PRM_CaseManager__c, RecordTypeId, ' + String.join(new List<String>(primaryFields), ', ')
                    + ' FROM PRM_CaseManagerAssociation__c'
                    + ' WHERE PRM_CaseManager__c IN :cmIds AND RecordTypeId IN :rtIds';

        for (PRM_CaseManagerAssociation__c r : (List<PRM_CaseManagerAssociation__c>) Database.query(soql)) {
            String primaryField = rtIdToPrimary.get(r.RecordTypeId);   // per-row primary, by its RT
            if (primaryField == null) continue;
            Id primaryId = (Id) r.get(primaryField);
            if (primaryId == null) continue;
            keys.add(buildKey(r.PRM_CaseManager__c, r.RecordTypeId, primaryId));
        }
        return keys;
    }
}
```

> **Notes:** (1) `Database.query` is used so the pre‑check can include the per‑RT primary fields dynamically (F‑11); inputs are bound (`:cmIds`, `:rtIds`) — no injection. (2) `stripInaccessible(CREATABLE)` enforces FLS (F‑12); ensure the §3 permission‑set FLS covers every lookup or those fields are dropped. (3) All‑or‑nothing `insert` (F‑4) → a bad row throws and the caller's transaction (batch step / intake) rolls back. (4) Idempotent: re‑run skips existing keys. (5) `caseManagerId` is invoker‑supplied.
