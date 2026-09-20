# E15 · `PRM_ProviderFeatureService` — Comprehensive Execution Plan

> **Source design (authoritative):** `E15_PRM_ProviderFeatureService.md` (this folder). **Batch:** `E22_PRM_PLRelatedBatch.md` (seq 4). **Conventions:** `Epic_E_Practitioner_Services.md` §E0.1–E0.2 / §E0.4; rule `prm-service-class-boundaries`. **Base class:** `PRM_ServiceBase` (`execute(Map<String,Object>) : Map<String,Object>`, protected `response`). **Shared util:** `PRM_FormSubUtility.recordTypeId(SObjectType, devName)`.
>
> **⚠ Ground rule:** nothing is assumed. Tags — **[CONFIRMED]** (documented/org‑verified), **[OPEN — Pending Clarification]** (needs a decision), **[RISK]**, **[RECOMMENDATION]**. Where a decision blocks code, §7 implements the **recommended** option behind a marked seam and the task is **Pending Clarification**.
>
> **Target org:** IBXDEV01 (design §3.1; confirm — OQ‑E15‑9). **Effort:** design says 1.0 d but the doc header is 1.5 d (ACC added) — re‑estimated in §6.

---

## 1. Confirmed requirements (extracted from the epic)

| # | Requirement | Evidence |
|---|---|---|
| R1 | **Single service, two record types.** `PRM_ProviderFeatureService` builds **`PRM_AssistiveAid`** *and* **`PRM_AffirmingCareCategory` (ACC)** rows on `PRM_ProviderFeature__c` in **one mixed‑RT bulk DML**. | design §1, §4, §7 (OQ‑E15‑10 resolved) |
| R2 | **Grain = per location.** Both DRs set **only `PRM_HealthcareFacility__c`** — never `PRM_Practitioner__c`/`PRM_HealthcarePractitionerFacility__c`. One row per **(location × record type)**. | design §1, §3.1 (OQ‑E15‑1 resolved, org) |
| R3 | **`extends PRM_ServiceBase`**, `execute(Map) : Map`; input `params.features[]`, output `response.features[]` `{ healthcareFacilityId, featureType, providerFeatureId }`. | design §4; `PRM_ServiceBase.cls` |
| R4 | **Batch‑injected context** (SOQL‑free service): `featureType`, `healthcareFacilityId`, `caseManagerId`, `values[]` (**already‑mapped** codes for AsstAid / labels for ACC), `isActive`, `effectiveFrom`, `effectiveTo`, `shareInDirectory?` (ACC), `existingFeatureId?`. | design §4/§4.1 |
| R5 | **Idempotency = Id‑based update‑in‑place** (org‑verified legacy). Pre‑check `(PRM_HealthcareFacility__c + RecordTypeId)` → matched Id ⇒ **update the multipicklist in place**; else insert. **No end‑dating / `OldCapabilities`.** | design §2, §7 (OQ‑E15‑2/3 resolved) |
| R6 | **Field map — AssistiveAid (§6.1):** RT `PRM_AssistiveAid`; `Name='Assistive Aid'`; `PRM_AssistiveAids__c` (`;`‑joined codes); `PRM_HealthcareFacility__c`; `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c`; `PRM_CaseManager__c`. | design §6.1 (DR `0jIOv0000000UNtMAM`) |
| R7 | **Field map — ACC (§6.2):** RT `PRM_AffirmingCareCategory`; `Name='Affirming Care Categories'`; `PRM_AffirmingCareCategory__c` (`;`‑joined labels); `PRM_IsDirectoryPrint__c ← shareInDirectory`; same facility/CM/dates. | design §6.2 (DR `0jIOv0000000R6fMAE`) |
| R8 | **REQUIRED booleans (org, `nillable=false`):** **`PRM_Active__c`** (← `isActive`, **no default → MUST set**), `PRM_Pending__c` (default `false`), `PRM_IsErrorRecord__c` (default `false`), `PRM_IsDirectoryPrint__c` (ACC ← `shareInDirectory`, else default `false`). | design §3.1 |
| R9 | **Gating:** AsstAid excluded when the location label == `"Does Not Apply"`; ACC created when `affirmingCareCategory` non‑blank. **Gating is done in the batch**; the service skips a feature with empty `values[]`. | design §1, §5 |
| R10 | **No new field / no metadata.** `PRM_ExternalId__c` exists but is **unused** (Id‑based idempotency). | design §2, §3 |
| R11 | **Bulk only** — build in memory, one bulk DML; no SOQL/DML in loops. | design §1, §7 |
| R12 | **Runs in `PLRelatedBatch` (seq 4, E22).** Returns `providerFeatureId` per (location × type) to feed **E19 CMA** (`Provider_Feature`). E15 does **not** build CMA/CDM itself (E22 does). | design §1, §7; E22 §9 |

> **Org‑verified field facts (this session):** on `PRM_ProviderFeature__c` — `PRM_Active__c` (boolean, nillable=false, **default=None**), `PRM_Pending__c`/`PRM_IsDirectoryPrint__c`/`PRM_IsErrorRecord__c` (boolean, nillable=false, default=false), `PRM_AssistiveAids__c` + `PRM_AffirmingCareCategory__c` (multipicklist), `PRM_HealthcareFacility__c`/`PRM_CaseManager__c` (reference), `PRM_EffectiveFrom__c`/`PRM_EffectiveTo__c` (date), `PRM_ExternalId__c` (extId, **not** unique), `Name` (nullable).

---

## 2. Open questions — **Pending Clarification**

| ID | Question | Options / trade‑offs | Recommendation |
|---|---|---|---|
| **OQ‑E15‑1b** | **Who runs the idempotency pre‑check** — service or batch? | (a) **Service** self‑pre‑checks (one bulk `SELECT`), consistent with E14/E16/E19. (b) **Batch** pre‑checks and injects `existingFeatureId` (contract already allows it) → pure build+DML. | **(a) service‑side pre‑check**, and **honor `existingFeatureId` if the batch supplies it** (skip the query for those). Coded in §7 behind `resolveExisting()`. |
| **OQ‑E15‑1c** *(new)* | **DML shape for insert+update** — single `upsert` vs split insert/update. Field‑mutability of `RecordTypeId`/`PRM_HealthcareFacility__c` on **update** is **not verified in‑org**; an `UPSERTABLE` strip could drop a createable‑only field from *insert* rows too (the E16 problem). | (a) **Split** insert (full rows) + update (mutable subset only: multipicklist, `PRM_Active__c`, dates, `PRM_Pending__c`, `PRM_IsDirectoryPrint__c`) — safe, no strip risk. (b) Single `upsert` on `Id` — simpler but risks the strip issue if any field is createable‑only. | **(a) split insert/update** (mirrors E16). Coded in §7. Validate updateable flags in Phase 4. |
| **OQ‑E15‑7** | **Effective‑date source.** DR maps `EffectiveDate`/`EffectiveTo` from IP set‑values. Confirm the batch injects the **practitioner `effectiveFromDate`** (like E13). | Batch‑injected either way; only the source needs confirming. | Batch injects practitioner `effectiveFromDate`/`effectiveTo` per E13's pattern — **confirm with BA**. |
| **OQ‑E15‑5** | **CMA for both RTs.** Confirm both `PRM_AssistiveAid` and `PRM_AffirmingCareCategory` features feed E19's `Provider_Feature` CMA (context `PRM_Account__c` group + `PRM_HealthcareFacility__c`). | Owned by **E22/E19**, not E15. | E22 emits one `Provider_Feature` CMA per feature Id (both RTs). Not an E15 code item — track on E22. |
| **OQ‑E15‑4a** *(data, not code)* | **`Wheelchair Accessible` label→code.** No exact `PRM_AssistiveAids__c` label (closest `Handicapped Accessible`=`HA`). | Map to `HA`, or add a new picklist value, or drop. | BA to finalize **one** mapping‑table row. This is a **batch/mapping** concern (E15 receives already‑mapped codes) — does not block E15 code. |
| **OQ‑E15‑9** | **Target org / batch size / effort.** | — | Confirm **IBXDEV01**; batch size per E22 (rec `1`); effort ~1.5 d. |

> **Confirmed‑and‑closed (design §8):** OQ‑E15‑1 (grain=location), OQ‑E15‑2 (Id‑based idempotency), OQ‑E15‑3 (no end‑dating / replace‑in‑place), OQ‑E15‑4 (batch maps label→code), OQ‑E15‑6 (`showInDirectory` not needed for AsstAid; ACC uses it), OQ‑E15‑10 (ACC in scope), OQ‑E15‑11 (`affirmingCareCategory` added to intake).

---

## 3. Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RK‑1 | **Field mutability unknown** (OQ‑E15‑1c) — mixed `upsert` could drop createable‑only fields. | DML/data error. | **Split** insert/update; validate updateable flags (Phase 4). |
| RK‑2 | **`PRM_Active__c` has no default** — if unset on insert → `REQUIRED_FIELD_MISSING`. | Insert fails. | Always set `PRM_Active__c = isActive` (R8); unit test asserts it. |
| RK‑3 | **Label→code mapping lives in the batch** — if the batch sends **labels** (not codes) or an unmapped label, the multipicklist insert fails (invalid picklist value). | Insert fails. | Contract = `values[]` are **already codes** (AsstAid) / **exact labels** (ACC). Service validates non‑blank; batch owns the map (OQ‑E15‑4/4a). |
| RK‑4 | **Update‑in‑place replaces the multipicklist** — a re‑submit with fewer capabilities **removes** the missing ones (replace, not merge). | Data loss vs intended. | This is the **legacy semantics** (design §2/§7 — replace full set). Confirm with BA it's intended (it is per the DR). |
| RK‑5 | **HCF Id resolution upstream** (E22 §3.1) — if `healthcareFacilityId` is null, the feature can't be created. | Missing features. | E22 resolves via shared `computeHcfExternalId`; E15 skips + reports null‑facility features. |
| RK‑6 | **Halt‑on‑failure vs per‑record capture** — `insert(rows, true)` throws on any bad row → step fails. | One bad feature fails the chunk. | Acceptable per Epic C (retry). Switch to `false` + capture only if per‑record grain is required (CL‑E16‑A) — confirm. |

---

## 4. Dependencies & prerequisites

- **[CONFIRMED]** `PRM_ProviderFeature__c` + RTs `PRM_AssistiveAid`, `PRM_AffirmingCareCategory` (org §3.1); field facts org‑verified (R1 note).
- **[CONFIRMED]** `PRM_ServiceBase`, `PRM_FormSubUtility.recordTypeId(...)` deployed (in repo).
- **[CONFIRMED]** Upstream by seq 4: `HealthcareFacility` (E13/seq2), Case Manager (E1 intake). `affirmingCareCategory` present in intake JSON (added).
- **[OPEN]** **E22** injects `featureType`, `values[]` (**mapped**), `healthcareFacilityId`, `caseManagerId`, dates, `shareInDirectory` (ACC), optional `existingFeatureId`; owns gating + label→code map. E15 is unit‑testable in isolation with a stub payload; integration needs E22.
- **[OPEN]** **FLS** on `PRM_AsyncJob_Access` for every field E15 writes (WI‑2) — confirm/grant.
- **[CONFIRMED — no metadata]** No new fields/RT/objects.

---

## 5. Phased execution plan

### Phase 0 — Pre‑build clarifications (gate)
Resolve **OQ‑E15‑1b, OQ‑E15‑1c, OQ‑E15‑7** and confirm **OQ‑E15‑9**. (OQ‑E15‑5 and OQ‑E15‑4a are E22/BA items, not blockers to E15 code.) **No code** until OQ‑E15‑1c (split vs upsert) is decided — it changes the DML section.

### Phase 1 — Contract & scaffolding
| Field | Detail |
|---|---|
| **Purpose** | Lock the `features[]` contract; class skeleton. |
| **Expected outcome** | `PRM_ProviderFeatureService extends PRM_ServiceBase` compiles; empty input → empty response. |
| **Dependencies** | Phase 0. |
| **Prerequisites** | `PRM_ServiceBase` deployed. |
| **Impacted files** | `classes/PRM_ProviderFeatureService.cls` (+ `-meta.xml`). |
| **Validation** | Compiles; empty‑input returns empty. |
| **Testing** | null/empty `features` → empty response. |
| **Risks** | — |
| **Completion** | Deploys; empty‑path test green. |

### Phase 2 — RT resolution + row builder (both RTs)
| Field | Detail |
|---|---|
| **Purpose** | Build mixed‑RT `PRM_ProviderFeature__c[]` with all §6.1/§6.2 derivations. |
| **Expected outcome** | Per feature: correct RT + `Name`; multipicklist from `values[]`; `PRM_HealthcareFacility__c` set; `PRM_Active__c` = isActive; `PRM_Pending__c=false`; ACC sets `PRM_IsDirectoryPrint__c`. |
| **Dependencies** | Phase 1. |
| **Prerequisites** | `recordTypeId` for `PRM_ProviderFeature__c`. |
| **Impacted files** | `PRM_ProviderFeatureService.cls`. |
| **Validation** | Field‑by‑field unit asserts per RT (in‑memory). |
| **Testing** | AsstAid row, ACC row, required‑booleans non‑null, `PRM_Active__c` set, ACC `IsDirectoryPrint`. |
| **Risks** | RK‑2, RK‑3. |
| **Completion** | Builder tests green. |

### Phase 3 — Idempotency pre‑check + split DML
| Field | Detail |
|---|---|
| **Purpose** | Pre‑check `(facility + RT)` (OQ‑E15‑1b service, honor injected `existingFeatureId`); **split** insert (new) + update (mutable subset, replace multipicklist) — OQ‑E15‑1c. |
| **Expected outcome** | Re‑run updates in place, creates no duplicate; one feature per (location × RT). |
| **Dependencies** | Phase 2. |
| **Prerequisites** | FLS (WI‑2). |
| **Impacted files** | `PRM_ProviderFeatureService.cls`. |
| **Validation** | Two runs → one row per (facility,RT); second run updates (multipicklist replaced), inserts 0. |
| **Testing** | Bulk (200+ mixed), re‑run idempotency, update‑in‑place replaces multipicklist. |
| **Risks** | RK‑1, RK‑4, RK‑6. |
| **Completion** | Idempotency + bulk tests green. |

### Phase 4 — FLS, tests ≥85%, org validation
| Field | Detail |
|---|---|
| **Purpose** | Confirm/grant FLS; `PRM_ProviderFeatureServiceTest` ≥85%; validate field API names + **updateable flags** (OQ‑E15‑1c) against IBXDEV01. |
| **Expected outcome** | Deployable, covered, org‑validated. |
| **Dependencies** | Phases 1–3. |
| **Prerequisites** | Org access (OQ‑E15‑9). |
| **Impacted files** | `PRM_ProviderFeatureServiceTest.cls`; `permissionsets/PRM_AsyncJob_Access` (FLS only, if a gap). |
| **Validation** | `sf apex run test`; `sf sobject describe`. |
| **Testing** | ≥85%; both RTs; empty‑values skip; negative (missing facility). |
| **Risks** | RK‑1, RK‑5. |
| **Completion** | Design DoD (§9) met; tests green; evidence captured. |

### Phase 5 — Integration with E22 (post‑E22)
| Field | Detail |
|---|---|
| **Purpose** | Wire E15 into `PRM_PLRelatedBatch.execute()`; verify per‑location features + `providerFeatureId` feeds E19 CMA. |
| **Expected outcome** | Seq‑4 run creates AsstAid + ACC features; CMA (E19) created by E22. |
| **Dependencies** | E22 built; label→code map (OQ‑E15‑4a). |
| **Prerequisites** | E22, E19, E13 outputs. |
| **Impacted files** | `PRM_PLRelatedBatch.cls` (E22 owns). |
| **Validation** | End‑to‑end async run. |
| **Testing** | Integration: multi‑location practitioner with capabilities + ACC. |
| **Risks** | RK‑4, RK‑5. |
| **Completion** | E2E features + CMA correct; halt‑on‑failure honored. |

---

## 6. Effort (re‑estimate)

| Item | d |
|---|---|
| Phase 0 clarifications | 0.25 |
| Phases 1–3 (build) | 0.75 |
| Phase 4 (FLS + tests + org validation) | 0.5 |
| Phase 5 (E22 integration) | with E22 |
| **Total** | **~1.5 d** (matches the doc header; the older "1.0 d" predates ACC) |

---

## 7. Reference implementation (confirmed design; open items behind marked seams)

> **Pending Clarification seams:** service‑side `resolveExisting()` honoring injected `existingFeatureId` (OQ‑E15‑1b) · **split** insert/update (OQ‑E15‑1c). **Do not deploy until Phase 0 decisions are ratified + updateable flags validated (RK‑1).**

```apex
/*
* @ClassName    : PRM_ProviderFeatureService
* @TestClassName: PRM_ProviderFeatureServiceTest
* @StoryNumber  : E15
* @CreatedBy    : Salesforce
* @Description  : EPIC E E15 "Provider Feature Service" — runs in PLRelatedBatch (seq 4). Builds PRM_ProviderFeature__c
*                 per location in TWO record types (PRM_AssistiveAid + PRM_AffirmingCareCategory) in ONE mixed-RT bulk
*                 DML. Batch-injected, SOQL-free except the idempotency pre-check (OQ-E15-1b). Id-based update-in-place
*                 (replace the multipicklist; no end-dating). PRM_Active__c has no default -> always set from isActive.
*/
public with sharing class PRM_ProviderFeatureService extends PRM_ServiceBase {

    public class PRM_ProviderFeatureException extends Exception {}

    private static final String TYPE_ASSISTIVE = 'AssistiveAid';
    private static final String TYPE_ACC        = 'AffirmingCareCategory';
    private static final String RT_ASSISTIVE = 'PRM_AssistiveAid';
    private static final String RT_ACC        = 'PRM_AffirmingCareCategory';
    private static final String NAME_ASSISTIVE = 'Assistive Aid';
    private static final String NAME_ACC        = 'Affirming Care Categories';

    /** Correlated build unit (one per input feature, input order preserved). */
    private class Feat {
        String featureType;        // AssistiveAid | AffirmingCareCategory
        Id healthcareFacilityId;
        Id caseManagerId;
        List<String> values;       // codes (AsstAid) | labels (ACC) — already mapped by the batch
        Boolean isActive;
        Boolean shareInDirectory;  // ACC only
        Date effectiveFrom;
        Date effectiveTo;
        Id existingFeatureId;      // injected by batch OR set by resolveExisting()
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'features' => new List<Map<String, Object>>() };
        List<Object> raw = (params == null) ? null : (List<Object>) params.get('features');
        if (raw == null || raw.isEmpty()) { return response; }

        // 1) parse + validate (no SOQL/DML in loop)
        List<Feat> items = new List<Feat>();
        for (Object o : raw) { items.add(toFeat((Map<String, Object>) o)); }

        // 2) idempotency pre-check (OQ-E15-1b: service-side; honor injected existingFeatureId)
        resolveExisting(items);

        // 3) build rows; split insert (new) vs update (mutable subset) — OQ-E15-1c
        Id rtAssistive = PRM_FormSubUtility.recordTypeId(PRM_ProviderFeature__c.SObjectType, RT_ASSISTIVE);
        Id rtAcc       = PRM_FormSubUtility.recordTypeId(PRM_ProviderFeature__c.SObjectType, RT_ACC);

        List<PRM_ProviderFeature__c> toInsert = new List<PRM_ProviderFeature__c>();
        List<Feat> insertOrder = new List<Feat>();
        List<PRM_ProviderFeature__c> toUpdate = new List<PRM_ProviderFeature__c>();

        for (Feat f : items) {
            if (f.values == null || f.values.isEmpty()) { continue; }   // gated no-op (R9)
            if (f.existingFeatureId == null) {
                toInsert.add(buildInsert(f, rtAssistive, rtAcc));
                insertOrder.add(f);
            } else {
                toUpdate.add(buildUpdate(f));                            // replace-in-place, mutable subset
            }
        }

        // 4) bulk DML (FLS-safe; all-or-nothing per Epic C — RK-6)
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision d = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            List<SObject> safe = d.getRecords();
            insert safe;
            for (Integer i = 0; i < safe.size(); i++) {
                insertOrder.get(i).existingFeatureId = safe.get(i).Id;
            }
        }
        if (!toUpdate.isEmpty()) {
            SObjectAccessDecision d = Security.stripInaccessible(AccessType.UPDATABLE, toUpdate);
            update d.getRecords();
        }

        // 5) response in input order
        List<Map<String, Object>> out = new List<Map<String, Object>>();
        for (Feat f : items) {
            out.add(new Map<String, Object>{
                'healthcareFacilityId' => f.healthcareFacilityId,
                'featureType' => f.featureType,
                'providerFeatureId' => f.existingFeatureId
            });
        }
        response.put('features', out);
        return response;
    }

    /** OQ-E15-1b: one bulk SOQL keyed on (facility + RT); stamps existingFeatureId for rows the batch didn't pre-resolve. */
    private void resolveExisting(List<Feat> items) {
        Set<Id> facilityIds = new Set<Id>();
        Boolean needQuery = false;
        for (Feat f : items) {
            if (f.existingFeatureId == null && f.healthcareFacilityId != null) {
                facilityIds.add(f.healthcareFacilityId);
                needQuery = true;
            }
        }
        if (!needQuery) { return; }
        Id rtAssistive = PRM_FormSubUtility.recordTypeId(PRM_ProviderFeature__c.SObjectType, RT_ASSISTIVE);
        Id rtAcc       = PRM_FormSubUtility.recordTypeId(PRM_ProviderFeature__c.SObjectType, RT_ACC);
        Map<String, Id> byKey = new Map<String, Id>();
        for (PRM_ProviderFeature__c p : [
            SELECT Id, PRM_HealthcareFacility__c, RecordTypeId
            FROM PRM_ProviderFeature__c
            WHERE PRM_HealthcareFacility__c IN :facilityIds
              AND RecordTypeId IN (:rtAssistive, :rtAcc)
            WITH USER_MODE
        ]) {
            byKey.put(p.PRM_HealthcareFacility__c + '|' + p.RecordTypeId, p.Id);
        }
        for (Feat f : items) {
            if (f.existingFeatureId != null) { continue; }
            Id rtId = TYPE_ACC.equals(f.featureType) ? rtAcc : rtAssistive;
            f.existingFeatureId = byKey.get(String.valueOf(f.healthcareFacilityId) + '|' + String.valueOf(rtId));
        }
    }

    private PRM_ProviderFeature__c buildInsert(Feat f, Id rtAssistive, Id rtAcc) {
        Boolean isAcc = typeGuard(f.featureType);
        PRM_ProviderFeature__c p = new PRM_ProviderFeature__c();
        p.RecordTypeId = isAcc ? rtAcc : rtAssistive;
        p.Name = isAcc ? NAME_ACC : NAME_ASSISTIVE;
        p.PRM_HealthcareFacility__c = f.healthcareFacilityId;
        p.PRM_CaseManager__c = f.caseManagerId;
        p.put(isAcc ? 'PRM_AffirmingCareCategory__c' : 'PRM_AssistiveAids__c', String.join(f.values, ';'));
        p.PRM_Active__c = (f.isActive == true);                 // REQUIRED, no default
        p.PRM_Pending__c = false;                               // REQUIRED default
        p.PRM_IsErrorRecord__c = false;                         // REQUIRED default
        p.PRM_IsDirectoryPrint__c = isAcc ? (f.shareInDirectory == true) : false;  // ACC sets it
        p.PRM_EffectiveFrom__c = f.effectiveFrom;
        p.PRM_EffectiveTo__c = f.effectiveTo;
        return p;
    }

    /** Update-in-place: replace the multipicklist + refresh the mutable subset only (RecordTypeId/facility/Name unchanged). */
    private PRM_ProviderFeature__c buildUpdate(Feat f) {
        Boolean isAcc = typeGuard(f.featureType);
        PRM_ProviderFeature__c p = new PRM_ProviderFeature__c(Id = f.existingFeatureId);
        p.put(isAcc ? 'PRM_AffirmingCareCategory__c' : 'PRM_AssistiveAids__c', String.join(f.values, ';'));
        p.PRM_Active__c = (f.isActive == true);
        p.PRM_Pending__c = false;
        if (isAcc) { p.PRM_IsDirectoryPrint__c = (f.shareInDirectory == true); }
        p.PRM_EffectiveFrom__c = f.effectiveFrom;
        p.PRM_EffectiveTo__c = f.effectiveTo;
        return p;
    }

    private Boolean typeGuard(String t) {
        if (TYPE_ACC.equals(t)) { return true; }
        if (TYPE_ASSISTIVE.equals(t)) { return false; }
        throw new PRM_ProviderFeatureException('E15: unknown featureType "' + t + '"');
    }

    private Feat toFeat(Map<String, Object> m) {
        Feat f = new Feat();
        f.featureType          = (String) m.get('featureType');
        f.healthcareFacilityId = (Id) m.get('healthcareFacilityId');
        f.caseManagerId        = (Id) m.get('caseManagerId');
        f.values               = toStrList(m.get('values'));
        f.isActive             = asBool(m.get('isActive'));
        f.shareInDirectory     = asBool(m.get('shareInDirectory'));
        f.effectiveFrom        = asDate(m.get('effectiveFrom'));
        f.effectiveTo          = asDate(m.get('effectiveTo'));
        f.existingFeatureId    = (Id) m.get('existingFeatureId');
        if (String.isBlank(f.featureType)) { throw new PRM_ProviderFeatureException('E15: featureType required'); }
        if (f.healthcareFacilityId == null) { throw new PRM_ProviderFeatureException('E15: healthcareFacilityId required'); }
        return f;
    }

    private List<String> toStrList(Object o) {
        List<String> out = new List<String>();
        if (o == null) { return out; }
        for (Object v : (List<Object>) o) { if (v != null) { out.add(String.valueOf(v)); } }
        return out;
    }
    private Boolean asBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date asDate(Object o) {
        if (o == null) { return null; }
        if (o instanceof Date) { return (Date) o; }
        return Date.valueOf(String.valueOf(o));
    }
}
```

> **Field‑name confirmation (Phase 4):** all `PRM_*` field API names above are org‑verified this session (R1 note). Re‑run `sf sobject describe PRM_ProviderFeature__c` to confirm **updateable** flags before enabling the update path (RK‑1). Multipicklist values must be **valid picklist API values** — the batch owns the label→code map (RK‑3).

---

## 8. Test class (outline — bring to ≥85%)

```apex
@IsTest
private class PRM_ProviderFeatureServiceTest {
    // Factory: group Account; HealthcareFacility; IndividualApplication (CM).
    // NOTE: assert RTs PRM_AssistiveAid / PRM_AffirmingCareCategory exist (Phase 4); use valid picklist values
    //       (AsstAid codes e.g. 'AS','BM'; ACC labels e.g. 'Anxiety Disorder Treatment').

    @IsTest static void emptyInput_returnsEmpty() {}
    @IsTest static void buildsAssistiveAid_activeSet_pendingFalse() {
        // RT=PRM_AssistiveAid, Name='Assistive Aid', PRM_AssistiveAids__c='AS;BM',
        // PRM_HealthcareFacility__c set, PRM_Active__c=isActive, PRM_Pending__c=false, IsDirectoryPrint=false.
    }
    @IsTest static void buildsAcc_setsDirectoryPrint() {
        // RT=PRM_AffirmingCareCategory, Name='Affirming Care Categories',
        // PRM_AffirmingCareCategory__c set, PRM_IsDirectoryPrint__c=shareInDirectory.
    }
    @IsTest static void bulk_mixedRt_oneInsert() {
        // 200+ mixed AsstAid/ACC; assert Limits.getDmlStatements() (1 insert; +1 update only if updates present) + 1 pre-check SOQL.
    }
    @IsTest static void idempotent_rerunUpdatesInPlace() {
        // run twice; second run inserts 0, updates the multipicklist in place; one row per (facility,RT).
    }
    @IsTest static void replaceMultipicklist_removesDropped() { /* RK-4: fewer values on re-run -> replaced set */ }
    @IsTest static void emptyValues_skipped() {}
    @IsTest static void unknownFeatureType_throws() {}
    @IsTest static void missingFacility_throws() {}
}
```

**Coverage:** empty‑path, AsstAid build, ACC build, bulk one‑DML, re‑run update‑in‑place, replace semantics, empty‑values skip, negatives. Assert **outcomes** (org rule §6).

---

## 9. FLS / permission set (no object metadata)

- **WI‑2 (confirm/grant):** on `PRM_AsyncJob_Access`, **Edit** FLS for the fields E15 writes on `PRM_ProviderFeature__c`: `Name`, `RecordTypeId`, `PRM_HealthcareFacility__c`, `PRM_CaseManager__c`, `PRM_AssistiveAids__c`, `PRM_AffirmingCareCategory__c`, `PRM_Active__c`, `PRM_Pending__c`, `PRM_IsErrorRecord__c`, `PRM_IsDirectoryPrint__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c` + **Read** on `RecordTypeId` (pre‑check). **No new fields/RT/objects.** If already provisioned elsewhere (as with E16), only **verify**.

---

## 10. Deploy & validation commands

```bash
# Org schema validation (Phase 4 — confirm field API names + updateable flags for OQ-E15-1c/RK-1)
sf sobject describe --sobject PRM_ProviderFeature__c --target-org IBXDEV01 --json > providerfeature-describe.json

# Deploy the service + test (after Phase 0 sign-off)
sf project deploy start \
  -d "force-app/main/default/classes/PRM_ProviderFeatureService.cls" \
  -d "force-app/main/default/classes/PRM_ProviderFeatureService.cls-meta.xml" \
  -d "force-app/main/default/classes/PRM_ProviderFeatureServiceTest.cls" \
  -d "force-app/main/default/classes/PRM_ProviderFeatureServiceTest.cls-meta.xml" \
  --target-org IBXDEV01

# Run tests with coverage (gate >=85%)
sf apex run test -n PRM_ProviderFeatureServiceTest -r human -c -w 20 --target-org IBXDEV01
```

---

## 11. Definition of Done (execution‑plan level)

- [ ] **Phase 0** decided: OQ‑E15‑1b, OQ‑E15‑1c, OQ‑E15‑7, OQ‑E15‑9.
- [ ] `PRM_ProviderFeatureService` built per §7 (single service, two RTs, one bulk insert + optional update, service‑side pre‑check honoring `existingFeatureId`, replace‑in‑place).
- [ ] Field API names + **updateable flags** validated against IBXDEV01 (RK‑1).
- [ ] FLS confirmed on `PRM_AsyncJob_Access` (WI‑2) — no new metadata.
- [ ] `PRM_ProviderFeatureServiceTest` ≥ 85% incl. both RTs, bulk one‑DML, re‑run update‑in‑place, replace semantics, empty‑values skip, negatives.
- [ ] Design‑doc DoD (§9 of `E15_PRM_ProviderFeatureService.md`) satisfied.
- [ ] Integration with **E22** (Phase 5) verified once E22 is built; `providerFeatureId` feeds E19 CMA; label→code map finalized (OQ‑E15‑4a).

---

## 12. Recommendations (summary)

1. **Decide Phase 0 first** — OQ‑E15‑1c (split vs upsert) changes the DML; don't code before it's ratified.
2. **Service‑side pre‑check honoring `existingFeatureId`** (OQ‑E15‑1b) — matches E14/E16/E19 and lets E22 optionally pre‑resolve.
3. **Split insert/update** (OQ‑E15‑1c) — safe against the unverified field‑mutability (RK‑1); update path only touches the mutable subset and **replaces the multipicklist in place** (legacy semantics, RK‑4 — confirm intended).
4. **Always set `PRM_Active__c`** (no default) — the single most likely insert failure (RK‑2).
5. **Keep the label→code map in the batch** (E15 receives codes/labels); finalize the `Wheelchair Accessible` row (OQ‑E15‑4a) — a data task, not E15 code.
6. **Keep CMA/CDM out of E15** — E22/E19 own them; confirm both RTs are CMA‑tracked (OQ‑E15‑5).
