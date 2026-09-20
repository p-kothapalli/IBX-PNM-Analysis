# E23 · `PRM_Level4Batch` — Batch Design *(Level4RecordCreationBatch · seq 5)*

> **Parent:** `Epic_E_Practitioner_Services_Part3.md` (Part 3). **Framework:** `Epic_C_Async_Framework.md` (batch contract **C4**, orchestrator **C3**). **Siblings:** `E20_PRM_PractitionerBatch.md` (seq 1) · `E21_PRM_PracticeLocationAndGroupBatch.md` (seq 2) · `E22_PRM_PLRelatedBatch.md` (seq 4) — E23 mirrors their patterns (constructor‑arg context §2, NPI correlation §3, no‑rollback failure §6, shared `computeHcfExternalId` HCF resolution).
> **Role:** the **final (seq‑5) batch**. After `PLRelatedBatch` (seq 4) created the affiliations/features, E23 reads the same Job JSON, correlates + resolves reference Ids, and **prepares input for `E18 · PRM_Level4RecordCreationService` and invokes it** to create the **Level‑4 `HealthcareFacilityNetwork` (`PRM_FacilityPractitionerTxNw`)** rows.
>
> **🎯 Scope (this request):** wires **`E18 · PRM_Level4RecordCreationService`** only. **No CMA, no CDM, no IFC loader** (decisions). The HFN trigger cascades `PRM_FacilityNw` + `PRM_FacilityTx` from E18's inserts.
>
> **Decisions (this session):** grain = **per location** (`start()` explodes each practitioner into one work item per location — mirrors E21/E22's non‑practitioner grain); **`PRM_BatchSize__c = 1`** (the HFN **trigger must fire** on each TxNw insert to cascade FacilityNw/FacilityTx → keep its dedupe‑SOQL/DML within budget; one location per chunk bounds that cascade); **new** batch+service (not reusing `PRM_NetworkCreationBatch`); idempotency via a Unique `SourceSystemIdentifier` set by E18.
>
> **Sample payload:** `docs/sampleInputs/PractitionerCreation/PRM_MultiPractitioner_lowvolume.json` (`groups[].locations[].networkTaxonomyRoles[]`).
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RECOMMENDATION]**.

---

## 1. Role & cardinality

- **One batch per Job step** (seq 5). Dispatched by the orchestrator (`PRM_AsyncJobConfig__mdt`: seq 5 / `PRM_ServiceClassName__c='PRM_Level4Batch'` / **`PRM_BatchSize__c = 1`**). Runs **after** seq 4 (halt‑on‑failure chain).
- **Reads, does not create directly.** The write happens **inside E18**; the batch = **orchestration + input preparation**: parse JSON → correlate → resolve reference Ids → transform → invoke → status/chain.
- **`Database.Batchable<Object>, Database.Stateful`** — iteration unit = the **LOCATION** (mirrors E21/E22, **not** E20's practitioner grain). `start()` explodes each correlated practitioner into **one work item per location** (a practitioner with 3 groups × 4 locations → 12 work items), so chunking scales with the **location count**. Each work item is a single‑location node still shaped as a practitioner (practitioner context + `taxonomies` + exactly one group carrying exactly one location → `networkTaxonomyRoles[]`), so `execute()`/`buildNetworkRequests` are unchanged.
- **⚡ The HFN trigger must fire.** E18's TxNw insert triggers `PRM_HealthcareFacilityNetworkTrigger` → creates `PRM_FacilityNw` + `PRM_FacilityTx` (deduped) + sets their `SourceSystemIdentifier`. The trigger early‑returns under `PRM_TriggerContextControl.inBulkContext()` → **E23/E18 run with bulk‑context OFF**. Its dedupe SOQL + inserts consume budget → **`BatchSize = 1`** (one **location** per `execute`, bounding the cascade to a single location's networkTaxonomyRoles).
- **Halt‑on‑failure (F‑15a).** Any failure → step `Failed` → job `Failed` → chain halts; recovered via Retry. Idempotent (E18 `SourceSystemIdentifier` pre‑check) → retry re‑runs safely.

---

## 2. Batch contract (honours Epic C · C4)

| Method | Responsibility |
|---|---|
| *constructor* `(Id jobId, Id stepDetailId)` | Context injected by the orchestrator — **identical to E20/E21/E22** (constructor args, `final` members; `invokeJob` switch dispatches `new PRM_Level4Batch(jobId, stepId)`). |
| `start(bc)` | Read the Job payload once (`jsonFileParser`); derive `flow`; **NPI‑correlate** each practitioner → `{accountId, practitionerId, practitionerName, caseManagerId}` (§3); **explode each practitioner into one work item per location** (location‑grain iteration, mirrors E21/E22); **resolve reference Ids** (§3.1): HCF Ids (shared `computeHcfExternalId`), `HealthcarePayerNetwork` Ids (by name), `CareTaxonomy` Ids (by code); return an **`Iterable<Object>`** of single‑location nodes (chunked by `PRM_BatchSize__c = 1` = one location). |
| `execute(bc, scope)` | For the (single) location work item: build `networks[]` from its one `location.networkTaxonomyRoles[]` (§4) → invoke **E18** once. Capture failure (no rollback — §6). |
| `finish(bc)` | **F‑19:** `statusUpdate(stepDetailId, Completed\|Failed)` first, then `findNextJob(jobId)`. |

> **Constructor / `invokeJob`** — add `PRM_Level4Batch` to the per‑class `newBatch` switch (Epic C · C3), same shape as E20/E21/E22. **No interface, no new field.**

---

## 3. Correlation — same as E20/E21/E22 (§3)

Identical NPI correlation: one relationship query over `PRM_AsyncJobRecords__c` → `Map<npi → {accountId, practitionerId, caseManagerId}>`; stamp each practitioner node by `individualNpi`. Also resolve the **practitioner name** (from the Account) for the TxNw `Name`. The practitioner's `caseManagerId` stamps every Level‑4 row.

### 3.1 Reference‑Id resolution in `start()` (batch‑owned; keeps E18 SOQL‑free)

Per the `prm-service-class-boundaries` rule, E23 resolves and injects all Ids:

| Id | Resolution | Notes |
|---|---|---|
| `healthcareFacilityId` (+ `facilityName`, `accountId`) | **Shared `PRM_FormSubUtility.computeHcfExternalId(...)`** → bulk `SELECT Id, Name, AccountId, PRM_ExternalId__c FROM HealthcareFacility WHERE PRM_ExternalId__c IN :keys` | Same mechanism as E22 §3.1 (single source of truth). Prereq: E3 sets `Account.SourceSystemIdentifier` (OQ‑E21‑2). |
| `payerNetworkId` | **split `networkName` on `;`** → bulk `SELECT Id, Name FROM HealthcarePayerNetwork WHERE Name IN :networkNames` | **Exact match** per split name (OQ‑E18‑5). Unknown name → that combination fails (staged). |
| `careTaxonomyId` (+ `careTaxonomyName`) | **split `careTaxonomyCode` on `;`** → bulk `SELECT Id, Name, Code FROM CareTaxonomy WHERE Code IN :codes` | **Confirm the `CareTaxonomy` code field API name** (OQ‑E18‑4). |
| `isPrimarySpecialty` | correlate each split `careTaxonomyCode` → `practitioner.taxonomies[].isPrimarySpecialty` | in‑memory (from the same JSON node). |
| `practitionerId` / `practitionerName` / `caseManagerId` / `accountId` | §3 correlation | |

> **⚠ [OPEN — OQ‑E23‑1]** Confirm the `CareTaxonomy` code field (OQ‑E18‑4) and that `HealthcarePayerNetwork.Name` matches intake `networkName` exactly.

---

## 4. Preparing service input (transform: source → `params.networks`)

For the practitioner, flatten `groups[].locations[].networkTaxonomyRoles[]`. **⚡ Each entry's `networkName`, `careTaxonomyCode`, and `role` may each be `;`‑separated → split all three on `;`, trim, and emit the full cross‑product** (`network × taxonomy × role`) — **one E18 `networks[]` row per combination** (each atomic). *(e.g. `networkName="A;B"`, `careTaxonomyCode="X;Y"`, `role="PCP;Specialist"` → 8 rows: A‑X‑PCP, A‑X‑Specialist, A‑Y‑PCP, … B‑Y‑Specialist.)*

| E18 field | Source | Status |
|---|---|---|
| `practitionerId` / `practitionerName` / `caseManagerId` / `accountId` | §3 correlation / group Account | [CONFIRMED] |
| `healthcareFacilityId` / `facilityName` | §3.1 (`computeHcfExternalId`) | [CONFIRMED] |
| `payerNetworkId` | §3.1 (`networkName` → `HealthcarePayerNetwork`) | [CONFIRMED] |
| `careTaxonomyId` / `careTaxonomyName` | §3.1 (`careTaxonomyCode` → `CareTaxonomy`) | [CONFIRMED] (OQ‑E18‑4) |
| `role` | `networkTaxonomyRoles[].role` | [CONFIRMED] (picklist PCP/Specialist — OQ‑E18‑5) |
| `isPrimarySpecialty` | correlated practitioner taxonomy | [CONFIRMED] (OQ‑E18‑3) |
| `isActive` / `effectiveFrom` / `effectiveTo` | practitioner context | [CONFIRMED] (OQ‑E18‑6) |

---

## 5. Idempotency, DML & governor

- **Idempotency delegated to E18:** Unique `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` → pre‑check + insert‑misses (`DUPLICATE_VALUE` tolerated). Retry re‑runs safely.
- **DML:** batch does **no business DML** — only `statusUpdate`/`logFailure`. **The HFN trigger** fires on E18's insert → creates `PRM_FacilityNw` + `PRM_FacilityTx` (deduped) + sets their SSID — factor its SOQL/DML into the governor budget.
- **Governor / `BatchSize = 1`:** one **location** per `execute` → E18 inserts N TxNw (N = that single location's networkTaxonomyRoles cross‑product) → one bounded trigger cascade. Location‑grain iteration means a practitioner's many locations no longer pile into one chunk; keep `= 1` so the trigger's dedupe queries stay well under limits. *(The old `PRM_NetworkCreationBatch` used chunkSize 50 by suppressing the trigger; we keep the trigger, so we go smaller.)*

---

## 6. Failure semantics (F‑15a) — same as E20/E21/E22 §6

E18 throws / returns `success=false`; batch sets `anyFailure` + first error; `finish()` sets step status then `findNextJob`. **No rollback** — partial writes persist; idempotent retry recovers. Unknown `payerNetworkId`/`careTaxonomyId` → that row fails (staged to DLQ) but the step continues per E18's partial‑insert policy; confirm whether a resolution miss should fail the step or be DLQ‑only (OQ‑E23‑2).

---

## 7. Reference skeleton (illustrative — not final)

> Depends on `PRM_Level4RecordCreationService` (E18), `PRM_AsyncOrchestrator` (C3), `PRM_FormSubUtility.computeHcfExternalId` + `recordTypeId`. Correlation + constructor reuse E20/E21/E22.

```apex
public with sharing class PRM_Level4Batch
        implements Database.Batchable<Object>, Database.Stateful {

    private final Id jobId;
    private final Id stepDetailId;
    public PRM_Level4Batch(Id jobId, Id stepDetailId) {
        this.jobId = jobId; this.stepDetailId = stepDetailId;
    }

    private String flow;
    private Boolean anyFailure = false;
    private String firstError;

    // 1) start: flow + NPI correlation (E20 §3) + explode per location (location-grain, mirrors E21/E22) + reference-Id resolution (§3.1)
    public Iterable<Object> start(Database.BatchableContext bc) {
        PRM_AsyncJob__c job = [SELECT Id, PRM_ProcessName__c FROM PRM_AsyncJob__c WHERE Id = :jobId WITH USER_MODE];
        this.flow = job.PRM_ProcessName__c;
        Map<String, Object> payload = (Map<String, Object>) new PRM_AsyncOrchestrator().jsonFileParser(jobId);
        List<Object> nodes = (List<Object>) payload.get('practitioners');
        List<Object> workItems = explodePerLocation(nodes); // one single-location node per location (correlated via E20 §3)
        resolveReferenceIds(workItems);                      // HCF (computeHcfExternalId), PayerNetwork, CareTaxonomy (§3.1)
        return workItems;                                    // chunked by location count (BatchSize = 1)
    }

    // 2) execute: per (single) location work item -> build networks[] -> E18 (trigger cascades FacilityNw + FacilityTx)
    public void execute(Database.BatchableContext bc, List<Object> scope) {
        try {
            List<Object> networkReqs = new List<Object>();
            for (Object o : scope) buildNetworkReqs((Map<String,Object>) o, networkReqs);   // split networkName/careTaxonomyCode/role on ';' + cross-product -> one row per combination
            if (!networkReqs.isEmpty()) {
                Map<String, Object> r = new PRM_Level4RecordCreationService()
                    .execute(new Map<String,Object>{ 'flow'=>flow, 'networks'=>networkReqs });
                if (failed(r)) { recordFailure(r); }
            }
        } catch (Exception e) {
            anyFailure = true; firstError = e.getMessage();
            new PRM_AsyncOrchestrator().logFailure(stepDetailRef(), e, null);
        }
    }

    public void finish(Database.BatchableContext bc) {
        PRM_AsyncOrchestrator orch = new PRM_AsyncOrchestrator();
        orch.statusUpdate(stepDetailId, anyFailure ? 'Failed' : 'Completed', firstError);
        orch.findNextJob(jobId);
    }

    // helpers: correlateByNpi, resolveReferenceIds (HCF/PayerNetwork/CareTaxonomy — over split values),
    //          buildNetworkReqs (split networkName/careTaxonomyCode/role on ';' -> cross-product; correlate isPrimarySpecialty),
    //          splitAndTrim, failed/recordFailure
}
```

---

## 8. Sequence (end‑to‑end)

```
seq 4 (PLRelatedBatch) Completed → findNextJob → invokeJob(step seq 5)
  → Database.executeBatch(new PRM_Level4Batch(jobId, stepId), 1)
      start()   : flow; NPI-correlate; explode into one work item PER LOCATION (location-grain, mirrors E21/E22);
                  resolve HCF/PayerNetwork/CareTaxonomy Ids → Iterable<single-location nodes> (chunk = location count, BatchSize=1)
      execute() : per location work item → build networks[] (split networkName/careTaxonomyCode/role on ';' + cross-product) → E18
                    E18 inserts HealthcareFacilityNetwork (PRM_FacilityPractitionerTxNw) + SourceSystemIdentifier
                    ⚡ HFN trigger → creates PRM_FacilityNw + PRM_FacilityTx (deduped) + their SSID
      finish()  : statusUpdate(step) → findNextJob(jobId)
  → job Completed → notifyOnFinish
```

---

## 9. Open items / clarifications

- **✅ Decisions:** new batch+service; grain **per location** (`start()` explodes per location — mirrors E21/E22); `BatchSize=1`; idempotency via Unique `SourceSystemIdentifier` (E18); no CMA/CDM; no IFC loader; trigger cascades FacilityNw+FacilityTx.
- **OQ‑E23‑1 (= OQ‑E18‑4/5):** confirm `CareTaxonomy` code field API name + `HealthcarePayerNetwork.Name` exact‑match to `networkName`.
- **OQ‑E23‑2 — resolution‑miss policy.** If a `networkName`/`careTaxonomyCode` doesn't resolve, fail the **step** (halt) or DLQ the **row** and continue? *(Legacy `PRM_NetworkCreationBatch` DLQ‑ed the row and continued.)* **Recommend: DLQ the row + continue**, step `Completed` unless all rows fail — confirm.
- **OQ‑E23‑3 — `invokeJob` switch + `PRM_AsyncJobConfig__mdt` seq‑5 row.** Register `PRM_Level4Batch`.
- **OQ‑E23‑4 — Trigger governor headroom.** Validate the HFN trigger cascade (dedupe SOQL + FacilityNw/FacilityTx inserts) stays within limits at `BatchSize=1` for a **location** with a high‑`networkTaxonomyRoles` cross‑product (POC). *(Location‑grain iteration bounds each chunk to one location.)*
- **Inherited:** E3 `Account.SourceSystemIdentifier` (OQ‑E21‑2) for the shared `computeHcfExternalId`.

---

## 10. Recommendations (summary)

1. **Reuse E20/E21/E22's frame** — constructor‑arg context (§2), NPI correlation (§3), **location‑grain explosion in `start()` (mirrors E21/E22)**, shared `computeHcfExternalId` (§3.1), no‑rollback failure (§6). Only `execute()` (single‑service E18) differs.
2. **`BatchSize = 1` + location‑grain** — the HFN trigger must fire (to cascade FacilityNw/FacilityTx); one location per chunk keeps that cascade within governor limits.
3. **Let the trigger own FacilityNw + FacilityTx** — E18 creates only the TxNw; do not duplicate the trigger's output (E17 is a trigger side‑effect, not a service).
4. **Resolve all reference Ids in `start()`** (HCF/PayerNetwork/CareTaxonomy) — keep E18 SOQL‑free.
5. **DLQ resolution misses + continue** (OQ‑E23‑2) — matches legacy; avoids failing a whole submission for one bad network name.

---

## 11. Definition of Done

- [ ] `PRM_Level4Batch implements Database.Batchable<Object>, Database.Stateful` with `(Id jobId, Id stepDetailId)`; `invokeJob` switch + `PRM_AsyncJobConfig__mdt` seq‑5 row (OQ‑E23‑3).
- [ ] `start()`: flow + NPI correlation (E20 §3) + **explode into one work item per location** (location‑grain, mirrors E21/E22) + HCF/PayerNetwork/CareTaxonomy resolution (§3.1); `Iterable<Object>` (BatchSize=1 = one location).
- [ ] `execute()`: per location work item → build `networks[]` — **split `networkName`/`careTaxonomyCode`/`role` on `;` + cross‑product** (one row per combination; correlate `isPrimarySpecialty` per split code) → **E18**.
- [ ] **E18** creates only TxNw (RT `PRM_FacilityPractitionerTxNw`) with Unique `SourceSystemIdentifier`; **bulk‑context OFF** so the HFN trigger cascades `FacilityNw`+`FacilityTx`.
- [ ] **No CMA/CDM/IFC** (decisions).
- [ ] `finish()` sets status then `findNextJob` (F‑19); failure → step `Failed` (halt).
- [ ] Idempotent: re‑run creates no duplicates (E18 `SourceSystemIdentifier` pre‑check); resolution‑miss policy per OQ‑E23‑2.
- [ ] Governor validated at `BatchSize=1` incl. the trigger cascade (OQ‑E23‑4).
- [ ] `<Class>Test` ≥ 85% incl. multi‑location/multi‑network practitioner, **`;`‑separated cross‑product** (e.g. 2 networks × 2 taxonomies → 4 rows), re‑run idempotency, resolution‑miss (DLQ), failure→halt (stub E18).
- [ ] Field/relationship + RT + `CareTaxonomy`/`HealthcarePayerNetwork` lookups validated against the org.
