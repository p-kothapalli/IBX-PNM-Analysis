# E18 · `PRM_Level4RecordCreationService` — Comprehensive Execution Plan

> **Source design (authoritative):** `E18_PRM_Level4RecordCreationService.md` (this folder). **Batch:** `E23_PRM_Level4Batch.md` (seq 5, class `PRM_Level4Batch`). **Conventions:** `Epic_E_Practitioner_Services.md` §E0.1–E0.2 / §E0.4; rule `prm-service-class-boundaries`. **Base class:** `PRM_ServiceBase` (`execute(Map<String,Object>) : Map<String,Object>`, protected `response`). **Shared util:** `PRM_FormSubUtility.recordTypeId(SObjectType, devName)`.
>
> **⚠ Ground rule:** nothing is assumed. Tags — **[CONFIRMED]** (documented/org‑verified), **[OPEN — Pending Clarification]**, **[RISK]**, **[RECOMMENDATION]**. Where a decision blocks code, §7 implements the **recommended** option behind a marked seam and the task is **Pending Clarification**.
>
> **Target org:** IBXDEV01 (confirm — OQ‑E18‑7). **Effort:** 2.0 d (design) — re‑estimated in §6.

---

## 1. Confirmed requirements (extracted from the epic)

| # | Requirement | Evidence |
|---|---|---|
| R1 | **Writes `HealthcareFacilityNetwork` in TWO record types: `PRM_FacilityPractitionerTxNw`** (Level‑4, one per atomic practitioner×location×network×taxonomy×role) **AND `PRM_FacilityNw`** (Practice Location Network, one per `facility×network`, deduped + existence‑checked). **⚠ CORRECTED (org‑verified 2026‑07‑07):** the HFN trigger does **NOT** reliably cascade `PRM_FacilityNw` from a TxNw insert — the handler's `afterInsert` only does rollups/SSID/CDM. E18 must **create `PRM_FacilityNw` explicitly** (mirrors legacy `PRM_NetworkCreationBatch.insertFacilityNwRecords`). `PRM_FacilityTx` is still **not** created by E18 (trigger/other‑owned). | design §1, §8 (OQ‑E18‑2 corrected); legacy `PRM_NetworkCreationBatch`; org trigger scan |
| R2 | **Grain = one TxNw per (network × taxonomy × role) combination, per practitioner.** E18 receives **atomic** `networks[]` rows (one network/taxonomy/role each); **E23** owns the `;`‑split + cross‑product. | design §1 (OQ‑E18‑8) |
| R3 | **`extends PRM_ServiceBase`**, `execute(Map) : Map`; input `params.networks[]`, output `response.networks[]` `{ healthcareFacilityId, payerNetworkId, careTaxonomyCode, role, healthcareFacilityNetworkId }` (input order). | design §4; `PRM_ServiceBase.cls` |
| R4 | **Batch‑injected context** (SOQL‑free service): `practitionerId`, `practitionerName`, `healthcareFacilityId`, `facilityName`, `accountId`, `payerNetworkId`, `careTaxonomyId`, `careTaxonomyCode`, `careTaxonomyName`, `role`, `isPrimarySpecialty`, `isActive`, `effectiveFrom`, `effectiveTo`, `caseManagerId`. | design §4/§4.1 |
| R5 | **Idempotency = deterministic Unique `SourceSystemIdentifier` + pre‑check + insert‑misses.** `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}`. `Database.insert(rows, false)`; tolerate `DUPLICATE_VALUE` as already‑exists. **Not `upsert`** (field Unique but `externalId=False`). | design §2 (OQ‑E18‑1) |
| R6 | **Field map (§6, DR‑grounded):** RT via describe; `Name = CONCAT(practitionerName,' - ',networkName,' - ',careTaxonomyName,' - ',role,' at ',facilityName)` ≤80; `HealthcareFacilityId`, `AccountId`, `PractitionerId`, `PayerNetworkId`, `PRM_Taxonomy__c`, `PRM_PractitionerRole__c`, `PRM_Primary__c`←`isPrimarySpecialty`, `IsActive`, `EffectiveFrom/To`, `PRM_CaseManager__c`, `PRM_Pending__c=false`. | design §6 |
| R7 | **REQUIRED booleans never null** (org `nillable=false`): `IsActive`, `PRM_Pending__c`, `PRM_Primary__c`. `Name` required. | design §3.1 |
| R8 | **The HFN trigger MUST fire** (bulk‑context OFF) so `PRM_HealthcareFacilityNetworkTrigger` stamps the `SourceSystemIdentifier` on the `PRM_FacilityNw` rows E18 inserts + runs its rollups (participation, effective‑range, GUID, CDM). **CORRECTED:** it does not *create* `PRM_FacilityNw` — E18 does (R1). | design §1, §7; org trigger scan |
| R9 | **Bulk only** — build in memory, one bulk insert; no SOQL/DML in loops (trigger's own SOQL is separate + budgeted). | design §1, §7 |
| R10 | **No new field / no metadata.** Reuse existing Unique `SourceSystemIdentifier`. | design §3 |
| R11 | **No CMA / no CDM** for this service (decided). | design §7 |
| R12 | **Runs in `PRM_Level4Batch` (seq 5)** at `BatchSize=1`; returns `healthcareFacilityNetworkId` per row. | design §1; E23 |

> **Org‑verified field facts (this session):** `HealthcareFacilityNetwork` — `SourceSystemIdentifier` (string, `unique=True`, `externalId=False`, `idLookup=True`, len 255); `PRM_Taxonomy__c` → `CareTaxonomy`; `PayerNetworkId` → `HealthcarePayerNetwork`; `PractitionerId` → `Contact`; `PRM_PractitionerRole__c` picklist `PCP`/`Specialist`; `IsActive`/`PRM_Pending__c`/`PRM_Primary__c` `nillable=false`; RTs incl. `PRM_FacilityPractitionerTxNw` + `PRM_FacilityNw`. **⚠ CORRECTED:** the trigger (`PRM_HealthcareFacilityNetworkTrigger` → `PRM_HCFacilityNetworkTriggerHandler`) `afterInsert` runs rollups/`updateCaseDataManager`/`updateGUID`/etc. and `beforeInsert` **populates** the `SourceSystemIdentifier` for `PRM_FacilityNw`/`PRM_FacilityTx` rows in the insert set — but it does **NOT create** `PRM_FacilityNw` from a TxNw insert. So E18 inserts the `PRM_FacilityNw` rows itself (bulk context OFF → the trigger stamps their SSID). The `CareTaxonomy` code field is **`TaxonomyCode`** (OQ‑E18‑4 resolved).

---

## 2. Open questions — **Pending Clarification**

| ID | Question | Options / trade‑offs | Recommendation |
|---|---|---|---|
| **OQ‑E18‑1b** | **Who runs the idempotency pre‑check** — service or batch? | (a) **Service** self‑pre‑checks by `SourceSystemIdentifier` (consistent with E14/E15/E16/E19). (b) Batch pre‑checks + injects `existingHfnId`. | **(a) service‑side** (§7 `resolveExisting()`); honor an injected `existingHfnId` if the batch supplies it. |
| **✅ OQ‑E18‑4 (RESOLVED)** | **`CareTaxonomy` code field API name** (E23's `careTaxonomyCode`→Id lookup). | — | **`TaxonomyCode`** (org‑verified; also what `PRM_PractitionerBatch.resolveCareTaxonomyIds` uses). E23 queries `SELECT Id, Name, TaxonomyCode FROM CareTaxonomy WHERE TaxonomyCode IN :codes`. |
| **OQ‑E18‑5** | **`role` picklist match.** Source `role` must be exactly `PCP`/`Specialist`. | Intake sends exact values vs needs a label→value map. | Confirm intake sends exact picklist values; else E23 maps (not E18). |
| **OQ‑E18‑6** | **Effective dates / `IsActive` / `PRM_Pending__c` source.** | Batch injects practitioner `effectiveFromDate`/`effectiveTo`, `isActive`; `PRM_Pending__c=false` (legacy default). | Confirm with BA; E18 uses injected values + `PRM_Pending__c=false`. |
| **OQ‑E18‑9** *(new)* | **`DUPLICATE_VALUE` row → response Id.** On the rare race where pre‑check missed and the insert hits the Unique constraint, the `SaveResult` does **not** return the existing Id. | (a) Leave `healthcareFacilityNetworkId=null` for that row (treated as success/exists). (b) Re‑query the duplicates by `SourceSystemIdentifier` to backfill the Id (extra SOQL). | **(a)** for the pilot (rare at `BatchSize=1`); the row exists and downstream doesn't need its Id (no CMA/CDM). Revisit if an Id is required. |
| **OQ‑E18‑7** | **Target org / batch size / effort.** | — | Confirm IBXDEV01; `BatchSize=1` (E23); ~2.0 d. |

> **Confirmed‑and‑closed (design §8):** OQ‑E18‑1 (idempotency SSID composite), OQ‑E18‑2 (**CORRECTED** — E18 creates TxNw **and** `PRM_FacilityNw` explicitly; the trigger does not cascade FacilityNw; `PRM_FacilityTx` remains trigger/other‑owned), OQ‑E18‑3 (`isPrimarySpecialty` from practitioner taxonomy), OQ‑E18‑4 (`CareTaxonomy.TaxonomyCode`), OQ‑E18‑8 (E23 `;`‑split + cross‑product; E18 atomic).

---

## 3. Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RK‑1 | **~~Bulk‑context bypass silently skips the cascade~~ — SUPERSEDED.** The original risk assumed the trigger *creates* `PRM_FacilityNw`. It does **not** — E18 creates it explicitly (R1). Bulk context OFF is still required so the trigger *stamps* the `PRM_FacilityNw.SourceSystemIdentifier` (Unique) + runs rollups. `PRM_TriggerContextControl.isBulkContext` defaults `false` and nothing in the async path enables it (only test scaffolds do) → verified OFF at runtime. | If bulk context were ON, FacilityNw SSID would be null (no rollups). | E18 self‑creates FacilityNw (deduped + existence‑checked). Runtime bulk‑context OFF confirmed. Unit tests isolate with bulk‑context ON (FacilityNw still inserted by E18; SSID null in‑test only). |
| RK‑2 | **Trigger governor at scale.** The HFN trigger runs rollups/dedupe SOQL + related DML on every TxNw/FacilityNw insert. A practitioner with a large cross‑product (many networks×taxonomies×roles×locations) → many rows in one chunk → trigger SOQL/DML can approach limits. Plus E18's own two pre‑check SOQLs (TxNw by SSID, FacilityNw by facility). | Governor failure on a big practitioner. | `BatchSize=1` (E23); **POC** the worst‑case cross‑product (OQ‑E23‑4); if still tight, chunk E18's inserts. |
| RK‑3 | **`Name` > 80 chars** (concat of 5 parts). | Insert fails (`Name` len). | `abbreviate(80)` (legacy behavior). |
| RK‑4 | **`PRM_Primary__c` non‑nillable, no injected value.** If `isPrimarySpecialty` correlation misses (taxonomy not in `practitioner.taxonomies[]`), null → `REQUIRED_FIELD_MISSING`. | Insert fails. | Default `PRM_Primary__c=false` when `isPrimarySpecialty` is null; unit test the miss. |
| RK‑5 | **Reference‑Id resolution miss** (E23) — unknown `networkName`/`careTaxonomyCode` → null `payerNetworkId`/`careTaxonomyId`. `PayerNetworkId`/`PRM_Taxonomy__c` are nullable, so a null wouldn't fail the insert but would create a **bad Level‑4 row**. | Silent data quality gap. | E18 **validates required references non‑null** and DLQs the row (per OQ‑E23‑2) rather than inserting an incomplete TxNw. |
| RK‑6 | **`DUPLICATE_VALUE` Id gap** (OQ‑E18‑9). | Response Id null for raced rows. | Accept (a); pre‑check makes it rare at `BatchSize=1`. |
| RK‑7 | **Test complexity** — the cascade test needs `HealthcarePayerNetwork` + `CareTaxonomy` + `HealthcareFacility` + Contact + IndividualApplication, and the trigger active. | Slow/fragile tests. | Test‑data factory; assert cascade with the trigger enabled; a separate test may stub via bulk‑context to isolate E18‑only logic. |

---

## 4. Dependencies & prerequisites

- **[CONFIRMED]** `HealthcareFacilityNetwork` + RT `PRM_FacilityPractitionerTxNw`; field targets/types (R1 note).
- **[CONFIRMED]** `PRM_ServiceBase`, `PRM_FormSubUtility.recordTypeId(...)` deployed.
- **[CONFIRMED]** Active `PRM_HealthcareFacilityNetworkTrigger` — E18 relies on it to stamp `PRM_FacilityNw.SourceSystemIdentifier` + run rollups (NOT to create FacilityNw; E18 creates it). `PRM_FacilityTx` remains trigger/other‑owned.
- **[OPEN]** **E23** injects all resolved Ids + names + split atomic rows; owns `computeHcfExternalId`, PayerNetwork/CareTaxonomy lookups, cross‑product. E18 is unit‑testable in isolation with a stub `networks[]`; integration needs E23.
- **[OPEN]** **FLS** on `PRM_AsyncJob_Access` for the fields E18 writes (WI‑2).
- **[RESOLVED]** `PRM_TriggerContextControl.isBulkContext` defaults `false`; only test scaffolds enable it, so the trigger fires (bulk context OFF) at runtime — stamping `PRM_FacilityNw` SSID.
- **[CONFIRMED — no metadata]** No new fields/RT/objects.

---

## 5. Phased execution plan

### Phase 0 — Pre‑build clarifications (gate)
Confirm **OQ‑E18‑1b, OQ‑E18‑4, OQ‑E18‑5, OQ‑E18‑6, OQ‑E18‑7, OQ‑E18‑9** and **RK‑1** (bulk‑context control). None change the class shape drastically (insert‑only), but RK‑1 is decisive for correctness.

### Phase 1 — Contract & scaffolding
| Field | Detail |
|---|---|
| **Purpose** | Lock the `networks[]` contract; class skeleton. |
| **Expected outcome** | `PRM_Level4RecordCreationService extends PRM_ServiceBase` compiles; empty input → empty response. |
| **Dependencies** | Phase 0. |
| **Prerequisites** | `PRM_ServiceBase` deployed. |
| **Impacted files** | `classes/PRM_Level4RecordCreationService.cls` (+ `-meta.xml`). |
| **Validation** | Compiles; empty‑input returns empty. |
| **Testing** | null/empty `networks` → empty response. |
| **Risks** | — |
| **Completion** | Deploys; empty‑path test green. |

### Phase 2 — Row builder + SourceSystemIdentifier
| Field | Detail |
|---|---|
| **Purpose** | Build `HealthcareFacilityNetwork` (RT TxNw) atomic rows with all §6 derivations + the SSID composite. |
| **Expected outcome** | Correct RT, `Name` ≤80, SSID, all FKs, `PRM_Primary__c`(←isPrimarySpecialty, default false), required booleans non‑null. |
| **Dependencies** | Phase 1. |
| **Prerequisites** | `recordTypeId` for `HealthcareFacilityNetwork`. |
| **Impacted files** | `PRM_Level4RecordCreationService.cls`. |
| **Validation** | Field‑by‑field unit asserts (in‑memory). |
| **Testing** | Row build, SSID format, Name truncation, `PRM_Primary__c` default when null, required‑refs validation (RK‑5). |
| **Risks** | RK‑3, RK‑4, RK‑5. |
| **Completion** | Builder tests green. |

### Phase 3 — Idempotency pre‑check + insert (TxNw) + explicit FacilityNw
| Field | Detail |
|---|---|
| **Purpose** | Pre‑check by `SourceSystemIdentifier` (OQ‑E18‑1b service; honor injected `existingHfnId`) → insert TxNw misses; `Database.insert(false)` tolerating `DUPLICATE_VALUE`; then **`writeFacilityNetworks`** inserts one `PRM_FacilityNw` per facility×network (deduped + existence‑checked). Trigger fires on both (stamps FacilityNw SSID + rollups). |
| **Expected outcome** | Re‑run creates no duplicate TxNw or FacilityNw; existing TxNw return their Id; one FacilityNw per (facility×network). |
| **Dependencies** | Phase 2. |
| **Prerequisites** | FLS (WI‑2); bulk‑context OFF (RK‑1). |
| **Impacted files** | `PRM_Level4RecordCreationService.cls`. |
| **Validation** | Two runs → one TxNw per SSID + one FacilityNw per (facility×network); second run inserts 0. |
| **Testing** | Bulk (200+), re‑run idempotency, DUPLICATE_VALUE tolerance, FacilityNw dedup. |
| **Risks** | RK‑1, RK‑2, RK‑6. |
| **Completion** | Idempotency + bulk + FacilityNw tests green. |

### Phase 4 — FLS, tests ≥85%, org validation
| Field | Detail |
|---|---|
| **Purpose** | Confirm/grant FLS; `PRM_Level4RecordCreationServiceTest` ≥85%; validate field API names (esp. `CareTaxonomy` code — OQ‑E18‑4) + `SourceSystemIdentifier` behavior against IBXDEV01. |
| **Expected outcome** | Deployable, covered, org‑validated. |
| **Dependencies** | Phases 1–3. |
| **Prerequisites** | Org access (OQ‑E18‑7). |
| **Impacted files** | `PRM_Level4RecordCreationServiceTest.cls`; `permissionsets/PRM_AsyncJob_Access` (FLS only, if a gap). |
| **Validation** | `sf apex run test`; `sf sobject describe`. |
| **Testing** | ≥85%; required‑ref DLQ path; negative (missing role/taxonomy). |
| **Risks** | RK‑1, RK‑7. |
| **Completion** | Design DoD (§9) met; tests green; evidence captured. |

### Phase 5 — Integration with E23 (post‑E23)
| Field | Detail |
|---|---|
| **Purpose** | Wire E18 into `PRM_Level4Batch.execute()`; verify per‑combination TxNw + per‑(facility×network) `PRM_FacilityNw` end‑to‑end (trigger stamps FacilityNw SSID). |
| **Expected outcome** | Seq‑5 run creates the Level‑4 graph; idempotent on retry. |
| **Dependencies** | E23 built. |
| **Prerequisites** | E23, `computeHcfExternalId`, PayerNetwork/CareTaxonomy data. |
| **Impacted files** | `PRM_Level4Batch.cls` (E23 owns). |
| **Validation** | End‑to‑end async run; governor check (RK‑2). |
| **Testing** | Integration: multi‑location, `;`‑cross‑product practitioner. |
| **Risks** | RK‑1, RK‑2. |
| **Completion** | E2E TxNw + FacilityNw correct (FacilityNw SSID stamped by trigger); halt‑on‑failure honored. |

---

## 6. Effort (re‑estimate)

| Item | d |
|---|---|
| Phase 0 clarifications (+ RK‑1 bulk‑context check) | 0.25 |
| Phases 1–3 (build) | 1.0 |
| Phase 4 (FLS + tests + org validation; cascade test complexity RK‑7) | 0.75 |
| Phase 5 (E23 integration) | with E23 |
| **Total** | **~2.0 d** (matches design) |

---

## 7. Reference implementation (confirmed design; open items behind marked seams)

> **Pending Clarification seams:** service‑side `resolveExisting()` honoring injected `existingHfnId` (OQ‑E18‑1b) · `DUPLICATE_VALUE` → Id‑null (OQ‑E18‑9) · required‑ref validation → DLQ vs skip (RK‑5/OQ‑E23‑2). **Do not deploy until Phase 0 + RK‑1 (bulk‑context) are confirmed.**
>
> **⚠ CORRECTED (as built):** after the TxNw insert, E18 also runs **`writeFacilityNetworks(items)`** — builds one `PRM_FacilityNw` per unique `{healthcareFacilityId}|{payerNetworkId}` (in‑chunk dedup via a `seenKeys` set + a `resolveExistingFacilityNetworks` bulk pre‑check over the chunk's facilities), then `Database.insert(rows, false)` tolerating `DUPLICATE_VALUE`. `PRM_FacilityNw` fields: RT `PRM_FacilityNw`; `Name = "{networkName} - {facilityName}"` (≤80); `AccountId`; `HealthcareFacilityId`; `PayerNetworkId`; `IsActive`; `PRM_Pending__c=false`; `EffectiveFrom/To`; `PRM_CaseManager__c` — **no** `PractitionerId`/`PRM_Taxonomy__c`/`PRM_PractitionerRole__c` (facility‑level). `SourceSystemIdentifier` is left for the trigger's `populateSourceSystemIdentifierNw`. The `Net` inner class already carries `networkName`, `facilityName`, `accountId` so no contract change is needed. The §7 skeleton below shows the TxNw path only; the FacilityNw step is appended after step 4.

```apex
/*
* @ClassName    : PRM_Level4RecordCreationService
* @TestClassName: PRM_Level4RecordCreationServiceTest
* @StoryNumber  : E18
* @CreatedBy    : Salesforce
* @Description  : EPIC E E18 "Level-4 Record Creation" — runs in PRM_Level4Batch (seq 5). Creates ONLY the Level-4
*                 HealthcareFacilityNetwork rows (RT PRM_FacilityPractitionerTxNw); the HFN trigger cascades
*                 PRM_FacilityNw + PRM_FacilityTx. Batch-injected, SOQL-free except the idempotency pre-check.
*                 Idempotent: deterministic Unique SourceSystemIdentifier + pre-check + insert-misses (Database.insert
*                 partial; DUPLICATE_VALUE tolerated). Rows are atomic (E23 owns the ';'-split + cross-product).
*/
public with sharing class PRM_Level4RecordCreationService extends PRM_ServiceBase {

    public class PRM_Level4Exception extends Exception {}
    private static final String RT_TXNW = 'PRM_FacilityPractitionerTxNw';

    /** Correlated build unit (one per input network row, input order preserved). */
    private class Net {
        Id practitionerId;
        String practitionerName;
        Id healthcareFacilityId;
        String facilityName;
        Id accountId;
        Id payerNetworkId;
        Id careTaxonomyId;
        String careTaxonomyCode;
        String careTaxonomyName;
        String networkName;          // for Name (batch may inject; else derive from lookup upstream)
        String role;
        Boolean isPrimarySpecialty;
        Boolean isActive;
        Date effectiveFrom;
        Date effectiveTo;
        Id caseManagerId;
        String ssid;                 // computed SourceSystemIdentifier
        Id existingHfnId;            // injected by batch OR set by resolveExisting()
    }

    public override Map<String, Object> execute(Map<String, Object> params) {
        response = new Map<String, Object>{ 'networks' => new List<Map<String, Object>>() };
        List<Object> raw = (params == null) ? null : (List<Object>) params.get('networks');
        if (raw == null || raw.isEmpty()) { return response; }

        // 1) parse + validate; compute SourceSystemIdentifier (no SOQL/DML in loop)
        List<Net> items = new List<Net>();
        for (Object o : raw) { items.add(toNet((Map<String, Object>) o)); }

        // 2) idempotency pre-check (OQ-E18-1b: service-side; honor injected existingHfnId)
        resolveExisting(items);

        // 3) build TxNw rows for the MISSES only (insert-only; existing return their Id)
        Id rtTxNw = PRM_FormSubUtility.recordTypeId(HealthcareFacilityNetwork.SObjectType, RT_TXNW);
        List<HealthcareFacilityNetwork> toInsert = new List<HealthcareFacilityNetwork>();
        List<Net> insertOrder = new List<Net>();
        for (Net n : items) {
            if (n.existingHfnId != null) { continue; }              // already present -> skip
            toInsert.add(buildRow(n, rtTxNw));
            insertOrder.add(n);
        }

        // 4) ONE bulk insert (partial-success; tolerate DUPLICATE_VALUE). ⚡ HFN trigger cascades FacilityNw/FacilityTx.
        if (!toInsert.isEmpty()) {
            SObjectAccessDecision decision = Security.stripInaccessible(AccessType.CREATABLE, toInsert);
            List<SObject> safe = decision.getRecords();
            Database.SaveResult[] results = Database.insert(safe, false);
            for (Integer i = 0; i < results.size(); i++) {
                Database.SaveResult r = results[i];
                if (r.isSuccess()) {
                    insertOrder.get(i).existingHfnId = r.getId();
                } else if (isDuplicate(r)) {
                    // OQ-E18-9: raced duplicate -> row exists; Id unknown (left null). Idempotent no-op.
                } else {
                    throw new PRM_Level4Exception('E18 insert failed: ' + firstError(r));  // step fails -> DLQ/retry (Epic C)
                }
            }
        }

        // 5) response in input order
        List<Map<String, Object>> out = new List<Map<String, Object>>();
        for (Net n : items) {
            out.add(new Map<String, Object>{
                'healthcareFacilityId' => n.healthcareFacilityId,
                'payerNetworkId' => n.payerNetworkId,
                'careTaxonomyCode' => n.careTaxonomyCode,
                'role' => n.role,
                'healthcareFacilityNetworkId' => n.existingHfnId
            });
        }
        response.put('networks', out);
        return response;
    }

    /** OQ-E18-1b: one bulk SOQL keyed on SourceSystemIdentifier; stamps existingHfnId for rows the batch didn't pre-resolve. */
    private void resolveExisting(List<Net> items) {
        Set<String> ssids = new Set<String>();
        for (Net n : items) { if (n.existingHfnId == null && String.isNotBlank(n.ssid)) { ssids.add(n.ssid); } }
        if (ssids.isEmpty()) { return; }
        Id rtTxNw = PRM_FormSubUtility.recordTypeId(HealthcareFacilityNetwork.SObjectType, RT_TXNW);
        Map<String, Id> byKey = new Map<String, Id>();
        for (HealthcareFacilityNetwork h : [
            SELECT Id, SourceSystemIdentifier
            FROM HealthcareFacilityNetwork
            WHERE SourceSystemIdentifier IN :ssids AND RecordTypeId = :rtTxNw
            WITH USER_MODE
        ]) {
            byKey.put(h.SourceSystemIdentifier, h.Id);
        }
        for (Net n : items) {
            if (n.existingHfnId == null) { n.existingHfnId = byKey.get(n.ssid); }
        }
    }

    private HealthcareFacilityNetwork buildRow(Net n, Id rtTxNw) {
        // required-reference validation (RK-5) — a null network/taxonomy would create a bad Level-4 row
        if (n.payerNetworkId == null || n.careTaxonomyId == null || n.healthcareFacilityId == null || n.practitionerId == null) {
            throw new PRM_Level4Exception('E18: missing required reference for SSID ' + n.ssid);   // -> DLQ/step (OQ-E23-2)
        }
        String name = String.join(new List<String>{
            nz(n.practitionerName), nz(n.networkName), nz(n.careTaxonomyName), nz(n.role)
        }, ' - ') + ' at ' + nz(n.facilityName);
        return new HealthcareFacilityNetwork(
            RecordTypeId = rtTxNw,
            Name = name.abbreviate(80),
            SourceSystemIdentifier = n.ssid,
            HealthcareFacilityId = n.healthcareFacilityId,
            AccountId = n.accountId,
            PractitionerId = n.practitionerId,
            PayerNetworkId = n.payerNetworkId,
            PRM_Taxonomy__c = n.careTaxonomyId,
            PRM_PractitionerRole__c = n.role,
            PRM_Primary__c = (n.isPrimarySpecialty == true),     // REQUIRED (default false)
            IsActive = (n.isActive == true),                    // REQUIRED
            PRM_Pending__c = false,                             // REQUIRED default
            EffectiveFrom = n.effectiveFrom,
            EffectiveTo = n.effectiveTo,
            PRM_CaseManager__c = n.caseManagerId
        );
    }

    private Net toNet(Map<String, Object> m) {
        Net n = new Net();
        n.practitionerId       = (Id) m.get('practitionerId');
        n.practitionerName     = (String) m.get('practitionerName');
        n.healthcareFacilityId = (Id) m.get('healthcareFacilityId');
        n.facilityName         = (String) m.get('facilityName');
        n.accountId            = (Id) m.get('accountId');
        n.payerNetworkId       = (Id) m.get('payerNetworkId');
        n.careTaxonomyId       = (Id) m.get('careTaxonomyId');
        n.careTaxonomyCode     = (String) m.get('careTaxonomyCode');
        n.careTaxonomyName     = (String) m.get('careTaxonomyName');
        n.networkName          = (String) m.get('networkName');
        n.role                 = (String) m.get('role');
        n.isPrimarySpecialty   = asBool(m.get('isPrimarySpecialty'));
        n.isActive             = asBool(m.get('isActive'));
        n.effectiveFrom        = asDate(m.get('effectiveFrom'));
        n.effectiveTo          = asDate(m.get('effectiveTo'));
        n.caseManagerId        = (Id) m.get('caseManagerId');
        n.existingHfnId        = (Id) m.get('existingHfnId');
        if (n.practitionerId == null) { throw new PRM_Level4Exception('E18: practitionerId required'); }
        if (String.isBlank(n.role)) { throw new PRM_Level4Exception('E18: role required'); }
        // SSID = practitionerId _ healthcareFacilityId _ payerNetworkId _ careTaxonomyCode _ role
        n.ssid = String.join(new List<String>{
            String.valueOf(n.practitionerId), String.valueOf(n.healthcareFacilityId),
            String.valueOf(n.payerNetworkId), nz(n.careTaxonomyCode), n.role
        }, '_');
        return n;
    }

    private Boolean isDuplicate(Database.SaveResult r) {
        for (Database.Error e : r.getErrors()) {
            if (e.getStatusCode() == StatusCode.DUPLICATE_VALUE) { return true; }
        }
        return false;
    }
    private String firstError(Database.SaveResult r) {
        return r.getErrors().isEmpty() ? 'Unknown error' : r.getErrors()[0].getMessage();
    }
    private String nz(String s) { return s == null ? '' : s; }
    private Boolean asBool(Object o) { return o == null ? false : (Boolean) o; }
    private Date asDate(Object o) {
        if (o == null) { return null; }
        if (o instanceof Date) { return (Date) o; }
        return Date.valueOf(String.valueOf(o));
    }
}
```

> **Field‑name confirmation (Phase 4):** all `PRM_*` + standard field API names above are org‑verified this session. Re‑run `sf sobject describe HealthcareFacilityNetwork` to confirm; validate the `CareTaxonomy` code field for E23 (OQ‑E18‑4). **`networkName`** is needed for `Name` — E23 must inject it alongside `payerNetworkId` (add to the §4 contract if not already).

---

## 8. Test class (outline — bring to ≥85%)

```apex
@IsTest
private class PRM_Level4RecordCreationServiceTest {
    // Factory: Contact (practitioner) ; group Account ; HealthcareFacility ; HealthcarePayerNetwork ; CareTaxonomy ;
    //          IndividualApplication (CM). Trigger PRM_HealthcareFacilityNetworkTrigger ACTIVE (bulk-context OFF).

    @IsTest static void emptyInput_returnsEmpty() {}
    @IsTest static void buildsTxNw_ssidAndRequiredFields() {
        // RT=PRM_FacilityPractitionerTxNw; SSID = ids_code_role; Name<=80; PRM_Primary__c/IsActive/PRM_Pending__c set.
    }
    @IsTest static void primaryDefaultsFalse_whenNullIsPrimary() { /* RK-4 */ }
    @IsTest static void missingRequiredRef_throws() { /* RK-5: null payerNetworkId/careTaxonomyId -> exception */ }
    @IsTest static void triggerCascade_createsFacilityNwAndTx() {
        // after insert, assert PRM_FacilityNw + PRM_FacilityTx exist for the facility+network (trigger side-effect, RK-1).
    }
    @IsTest static void bulk_oneInsert() {
        // 200+ atomic rows; assert Limits.getDmlStatements() for E18's own insert == 1 (+ pre-check SOQL == 1).
    }
    @IsTest static void idempotent_rerunNoDuplicate() {
        // run twice; second run inserts 0; existing Id returned; one TxNw per SSID.
    }
    @IsTest static void unknownRole_or_taxonomy_reported() {}
}
```

**Coverage:** empty‑path, build+SSID, primary default, required‑ref validation, **trigger cascade** (FacilityNw+FacilityTx), bulk one‑insert, re‑run idempotency. Assert **outcomes** (org rule §6). *(A bulk‑context‑ON test can isolate E18‑only insert counts, but the cascade test must run with the trigger firing.)*

---

## 9. FLS / permission set (no object metadata)

- **WI‑2 (confirm/grant):** on `PRM_AsyncJob_Access`, **Edit** FLS for the fields E18 writes on `HealthcareFacilityNetwork`: `Name`, `RecordTypeId`, `SourceSystemIdentifier`, `HealthcareFacilityId`, `AccountId`, `PractitionerId`, `PayerNetworkId`, `PRM_Taxonomy__c`, `PRM_PractitionerRole__c`, `PRM_Primary__c`, `IsActive`, `PRM_Pending__c`, `EffectiveFrom`, `EffectiveTo`, `PRM_CaseManager__c` + **Read** on `SourceSystemIdentifier`/`RecordTypeId` (pre‑check). **No new fields/RT/objects.** *(The trigger‑created FacilityNw/FacilityTx run in the trigger's context — ensure the batch user can create `HealthcareFacilityNetwork` broadly.)* If already provisioned elsewhere, only **verify**.

---

## 10. Deploy & validation commands

```bash
# Org schema validation (Phase 4)
sf sobject describe --sobject HealthcareFacilityNetwork --target-org IBXDEV01 --json > hfn-describe.json
sf sobject describe --sobject CareTaxonomy --target-org IBXDEV01 --json > caretaxonomy-describe.json   # OQ-E18-4 (code field)

# Deploy the service + test (after Phase 0 sign-off)
sf project deploy start \
  -d "force-app/main/default/classes/PRM_Level4RecordCreationService.cls" \
  -d "force-app/main/default/classes/PRM_Level4RecordCreationService.cls-meta.xml" \
  -d "force-app/main/default/classes/PRM_Level4RecordCreationServiceTest.cls" \
  -d "force-app/main/default/classes/PRM_Level4RecordCreationServiceTest.cls-meta.xml" \
  --target-org IBXDEV01

# Run tests with coverage (gate >=85%)
sf apex run test -n PRM_Level4RecordCreationServiceTest -r human -c -w 20 --target-org IBXDEV01
```

---

## 11. Definition of Done (execution‑plan level)

- [ ] **Phase 0** confirmed: OQ‑E18‑1b, 4 (`TaxonomyCode`), 5, 6, 7, 9 + **RK‑1** (bulk‑context OFF so the trigger stamps the E18‑created `PRM_FacilityNw` SSID).
- [ ] `E18` contract includes **`networkName`** (needed for `Name`) — reconcile design §4 if missing.
- [ ] `PRM_Level4RecordCreationService` built per §7 — writes TxNw (service‑side pre‑check; insert‑misses; `DUPLICATE_VALUE` tolerated; required‑ref skip) **AND `PRM_FacilityNw`** (`writeFacilityNetworks`: one per facility×network, in‑chunk dedup + existence pre‑check, `DUPLICATE_VALUE` tolerated).
- [ ] Field API names/types validated against IBXDEV01 (incl. `CareTaxonomy` code = **`TaxonomyCode`** — OQ‑E18‑4 resolved).
- [ ] FLS confirmed on `PRM_AsyncJob_Access` (WI‑2) — no new metadata.
- [ ] `PRM_Level4RecordCreationServiceTest` ≥85% incl. build+SSID, primary default, required‑ref skip, **explicit `PRM_FacilityNw` creation + per‑(facility×network) dedup**, bulk one‑insert, re‑run idempotency.
- [ ] Design‑doc DoD (§9 of `E18_PRM_Level4RecordCreationService.md`) satisfied.
- [ ] Integration with **E23** (Phase 5) verified once E23 is built; governor validated at `BatchSize=1` (RK‑2).

---

## 12. Recommendations (summary)

1. **E18 creates `PRM_FacilityNw` explicitly (RK‑1/R1 corrected)** — the "E17 is a trigger side‑effect" assumption was wrong; the trigger only *stamps* FacilityNw SSID + rollups, it does not create it. Keep bulk context OFF (verified default) so the SSID is stamped; assert one FacilityNw per (facility×network).
2. **Service‑side pre‑check + insert‑only** (OQ‑E18‑1b) — matches E14/E15/E16/E19; no update path (Level‑4 is create‑only), so no field‑mutability concern.
3. **Validate required references before insert** (RK‑5) — a null `payerNetworkId`/`careTaxonomyId` should DLQ the row, not create an incomplete Level‑4 record.
4. **Add `networkName` to the injected contract** — required for the `Name` concat (design §4 lists it in §6 source but not in the §4 input row; reconcile).
5. **POC the trigger governor cost at `BatchSize=1`** for a large cross‑product practitioner (RK‑2) before scale.
