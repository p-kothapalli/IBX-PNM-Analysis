# E22 · `PRM_PLRelatedBatch` — Batch Design *(PLRelatedBatch · seq 4)*

> **Parent:** `Epic_E_Practitioner_Services_Part3.md` (Part 3). **Framework:** `Epic_C_Async_Framework.md` (batch contract **C4**, orchestrator **C3**). **Siblings:** `E20_PRM_PractitionerBatch.md` (seq 1) · `E21_PRM_PracticeLocationAndGroupBatch.md` (seq 2) — E22 mirrors their patterns (constructor‑arg context §2, NPI correlation §3, aggregated CMA/CDM §9, no‑rollback failure §6).
> **Role:** the **sequence‑4 batch**. After `PracticeLocationAndGroupBatch` (seq 2) built the **group + HealthcareFacility** graph, E22 reads the same Job JSON, correlates each practitioner to its Case Manager + Account + the seq‑2 HealthcareFacility Ids, and **prepares input for the practice‑location‑related services and invokes them**, then chains the next step.
>
> **🎯 Scope (this request):** wires **`E14 · PRM_HPFService` → `E15 · PRM_ProviderFeatureService` → `E19 · PRM_CMAService` → `E16 · PRM_CaseDataManagerService`.**
>
> **✅ E17 DROPPED (decided) — facility-grain `HealthcareFacilityNetwork` is a trigger side‑effect, not a batch service.** When **E18** (`Level4RecordCreationBatch`, seq 5) inserts the **Level‑4 `HealthcareFacilityNetwork` rows (RT `PRM_FacilityPractitionerTxNw`, "Practitioner at Practice Location Taxonomy and Network")**, the **HealthcareFacilityNetwork trigger (`PRM_HealthcareFacilityNetworkTrigger`) auto‑creates the `PRM_FacilityNw` (network) + `PRM_FacilityTx` (taxonomy) records**. *(This is the HealthcareFacilityNetwork object — `HealthcarePractitionerFacility` has no such RT.)* So `E17_PRM_HealthcareFacilityNetworkService` is **not** a separate service/step — its records (and their CMA/CDM) belong to the **Level‑4 flow (E18)**, not to E22. E22 therefore wires only **E14 → E15 → E19 → E16**.
>
> **✅ CMA + CDM applicability (org‑verified, IBXDEV01) — the answer to "are CMA/CDM applicable to E14/E15":**
> - **E14 (`HealthcarePractitionerFacility`)** → **CMA** RT `Practitioner_Practice_Location` (active) + **CDM** token `HealthCarePractitionerFacility`. **Both apply.**
> - **E15 (`PRM_ProviderFeature__c`)** → **CMA** RT `Provider_Feature` (active) + **CDM** token `ProviderFeature`. **Both apply.**
> - **⚠ No trigger sets these** (`PRM_HCPFTriggerHelper` / `PRM_ProviderFeatureTriggerHandler` have **no CDM/CMA writes** — org‑scanned) — unlike seq‑2's `HealthCareFacility` (HCF‑trigger‑set). **So E22 must emit the CMA rows (E19) and CDM tokens (E16) itself** (matching the legacy `PRMDRPCaseDataManager` DR in the `PRMPractitionerAddressCreation` IP).
>
> **Sample payload:** `docs/sampleInputs/PractitionerCreation/PRM_MultiPractitioner_lowvolume.json`.
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RECOMMENDATION]** · **Pending Clarification**.

---

## 1. Role & cardinality

- **One batch per Job step** (seq 4). Dispatched by the orchestrator (`PRM_AsyncJobConfig__mdt`: seq 4 / `PRM_ServiceClassName__c='PRM_PLRelatedBatch'` / `PRM_BatchSize__c`). Runs **after** seq‑2 completes (halt‑on‑failure chain). *(If a seq‑3 GroupRelatedBatch is introduced, E22 remains the practice‑location‑related step; sequence numbers are config‑driven.)*
- **Reads, does not create directly.** All writes happen **inside the services — E14 → E15 → E19 (CMA) → E16 (CDM)**. The batch = **orchestration + input preparation**: parse JSON → correlate → resolve seq‑2 Ids → transform → invoke → status/chain. *(No E17 — networks are created by the HCPF trigger during E18/Level‑4.)*
- **`Database.Batchable<Object>, Database.Stateful`** — the **iteration unit is the GROUP** (mirrors E21, **not** E20's practitioner grain). `start()` explodes each correlated practitioner into **one work item per group** (a practitioner with 5 groups → 5 work items), so chunking scales with the **group count** rather than the practitioner count — a practitioner with many groups no longer packs all its locations/affiliations/features into a single chunk. Each work item is a single‑group node still shaped as a practitioner (carrying `caseManagerId`/`practitionerId` + name + effective dates + exactly one `groups[]` entry). Case Manager ↔ practitioner is **1:1** (E20 §1), so per‑group work items still resolve to the correct CM, keeping CMA/CDM per‑CM clean (E16 is an update‑by‑CM manifest, so a CM seen across several group chunks accumulates tokens safely).
- **⚠ Shared locations → concurrency (OQ‑E22‑1).** A `HealthcareFacility` can be **shared across practitioners**. **E15** (per‑location feature) is location‑grain → **parallel chunks could race** on the same location's feature. **E14** (PLA per practitioner×location; PPA per practitioner×group) is practitioner‑grain → no race. **Recommendation: `PRM_BatchSize__c = 1`** for seq‑4 (mirror E21) until a `start()`‑level location dedupe is added. **[OPEN — OQ‑E22‑1]**.
- **Halt‑on‑failure (F‑15a).** Any failure → step `Failed` → job `Failed` → chain halts; recovered via **Retry**. Idempotent (E14 pre‑check by natural key; E15 pre‑check by `(facility+RT)`; E19 pre‑check; E16 update‑by‑CM) → retry re‑runs safely.

---

## 2. Batch contract (honours Epic C · C4)

| Method | Responsibility |
|---|---|
| *constructor* `(Id jobId, Id stepDetailId)` | Context passed in by the orchestrator — **identical to E20 §2.1 / E21 §2** (constructor args, `final` members; the `invokeJob` switch dispatches `new PRM_PLRelatedBatch(jobId, stepId)`). |
| `start(bc)` | Read the Job payload once (`jsonFileParser`); derive `flow`; **correlate each practitioner to its CM + Account by NPI (§3)**; **explode each practitioner into one work item per group** (group‑grain iteration, mirrors E21); **resolve the seq‑2 HealthcareFacility Ids** for each location + the **group Account Ids** (§3.1, OQ‑E22‑2) across all work items; return an **`Iterable<Object>`** of single‑group nodes (chunked by `PRM_BatchSize__c` = **group count**). |
| `execute(bc, scope)` | For the chunk: build + invoke **E14 (affiliations)** → **E15 (features)** → aggregate **E19 (CMA)** once → **E16 (CDM)** once. Track created/failed per CM. Capture failure (no rollback — §6). |
| `finish(bc)` | **F‑19:** `statusUpdate(stepDetailId, Completed\|Failed)` first, then `findNextJob(jobId)`. |

> **Constructor / `invokeJob`** — add `PRM_PLRelatedBatch` to the per‑class `newBatch` switch (Epic C · C3), same shape as E20/E21. **No interface, no new field.**

---

## 3. Correlation — same as E20/E21 (§3)

Identical NPI correlation: one relationship query over `PRM_AsyncJobRecords__c` → `Map<npi → {accountId, practitionerId, caseManagerId}>`; stamp each practitioner node by `individualNpi`. The practitioner's `caseManagerId` is the CM used for **all** its locations' affiliations + features + CMA/CDM.

> **⚠ Two distinct accounts — don't conflate.** §3's `accountId` = the **practitioner's person Account** (source of `practitionerId` = PersonContact for E14). The **group/vendor `AccountId`** used by E14's **PPA** affiliation and E15's `Provider_Feature` CMA context comes from **§3.1** (E3's group Account, also = `HealthcareFacility.AccountId`). E14 needs both: PersonContact (§3) + group Account (§3.1).

### 3.1 Resolving the exact practice‑location (HealthcareFacility) Id (OQ‑E22‑2)

E14/E15 need the **`HealthcareFacilityId`** (created by E13 in seq 2) and the **group `AccountId`** (E3) — but the services are **SOQL‑free**, so the **batch resolves them in `start()`**. There is no simple natural key on the JSON location node; the authoritative handle is the **Unique `HealthcareFacility.PRM_ExternalId__c`** — the composite the HCF trigger builds (`PRM_HCFacilityTriggerHelper.populatePRMExternalId`, the same gate E13 uses):

```apex
PRM_ExternalId__c =
    Account.SourceSystemIdentifier + '-' +
    (PRM_NpiId__c != null ? PRM_NpiId__c : '') + '-' +          // HealthcareProviderNpi RECORD Id (not the NPI number)
    (PRM_PracticeClassification__c != null ? PRM_PracticeClassification__c : '') + '-' +
    addr.PRM_AddressLine1__c + '-' + addr.PRM_AddressLine2__c + '-' + addr.PRM_Zip__c + '-' + addr.PRM_Phone__c   // primary address
```

**✅ DECIDED — (a) recompute the composite + query it back, via a SHARED helper** (reuses E13's logic, deterministic because E22 reads the **same** JSON). The composite formula lives **once** in **`PRM_FormSubUtility.computeHcfExternalId(...)`** and is called by **both E13 (create/gate) and E22 (lookup)** — single source of truth, no drift.

1. Flatten `practitioner.groups[].locations[]` from the Job JSON.
2. **Bulk‑resolve the group Account** → `Account.SourceSystemIdentifier` (by `HealthCloudGA__SourceSystemId__c = {taxId}-{groupName}`, from E3). ⚠ depends on **`SourceSystemIdentifier` being populated** (OQ‑E21‑2 / OQ‑E13‑18).
3. **Bulk‑resolve the location NPI record Id** → `SELECT Id, Npi FROM HealthcareProviderNpi WHERE Npi IN :npis AND NpiType='Organization'` (the `PRM_NpiId__c` segment; same E12 lookup E13 did).
4. **Compute the composite** per location via a **shared helper** — `PRM_FormSubUtility.computeHcfExternalId(...)` called by **both E13 (create) and E22 (lookup)** so the strings can't drift — using `practiceClassification` + the **primary** address strings from the same JSON (byte‑for‑byte match).
5. **One bulk query:** `SELECT Id, AccountId, PRM_ExternalId__c FROM HealthcareFacility WHERE PRM_ExternalId__c IN :keys` → `Map<composite → {healthcareFacilityId, accountId}>` (finds both E13‑created and pre‑existing facilities).
6. Inject `healthcareFacilityId` (+ group `accountId`) into each location node → E14/E15 stay SOQL‑free.

**Alternative — (b) persist a seq‑2 → seq‑4 handoff.** Have E13/E21 write the `{location → HealthcareFacility Id}` mapping into `PRM_AsyncJobDetails__c` (keyed by the composite or `{taxId}+locationNpi+addr}`); E22 reads it. More plumbing, but avoids the address‑string/NPI‑Id recompute fragility.

**✅ Decision: (a)** with the **shared formula helper** (single source of truth). Prerequisites: (i) E3 sets `Account.SourceSystemIdentifier` (OQ‑E21‑2/OQ‑E13‑18); (ii) the composite formula is extracted into **`PRM_FormSubUtility.computeHcfExternalId(...)`** and reused by E13 + E22 (replaces E13's inline replica).

> **⚠ Fragility note.** The composite embeds free‑text address fields + the NPI **record Id**. If E3's `SourceSystemIdentifier` is missing, or E13 and E22 compute the string differently, the lookup misses and E14/E15 get no facility → their records are skipped. The shared helper (4) + the E3 prerequisite (2) mitigate this; otherwise prefer (b).

---

## 4. Preparing service inputs (transform: source → `params`)

**E14 `PRM_HPFService`** — one call per chunk with the affiliations (PLA + PPA), threaded from §3.1 Ids:

| E14 field | Source | Status |
|---|---|---|
| `affiliations[].practitionerId` | correlated PersonContact (§3) | [CONFIRMED] |
| `affiliations[].healthcareFacilityId` | seq‑2 HCF Id (§3.1) — **PLA only** | [CONFIRMED] |
| `affiliations[].accountId` | seq‑2 group Account Id (§3.1) — **PPA only** | [CONFIRMED] |
| `affiliations[].caseManagerId` | the practitioner's CM (§3) | [CONFIRMED] |
| `affiliations[].recordType` | `PRM_PractitionerLocationAffiliation` (per location) + `PRM_PractitionerPracticeAffiliation` (per group) | [CONFIRMED] (E14 §1) |
| `affiliations[].isPrimary` / `isActive` / `effectiveFrom` / `effectiveTo` | `location.primaryPracticeLoc` / practitioner context | [CONFIRMED] |

**E15 `PRM_ProviderFeatureService`** — one call per chunk with the features (AssistiveAid + ACC), gated per type:

| E15 field | Source | Status |
|---|---|---|
| `features[].featureType` | `AssistiveAid` (from `capabilitiesAtLocation`) / `AffirmingCareCategory` (from `affirmingCareCategory`) | [CONFIRMED] (E15 §1) |
| `features[].healthcareFacilityId` | seq‑2 HCF Id (§3.1) | [CONFIRMED] |
| `features[].values[]` | AsstAid: **label→code mapped** `capabilitiesAtLocation`; ACC: `affirmingCareCategory` labels | [CONFIRMED] (E15 OQ‑E15‑4/11) |
| `features[].caseManagerId` / `isActive` / `effectiveFrom` / `effectiveTo` | practitioner context (§3) | [CONFIRMED] |
| `features[].shareInDirectory` | ACC only | [CONFIRMED] |

**E17 `PRM_HealthcareFacilityNetworkService`** — **DROPPED.** The facility-grain `HealthcareFacilityNetwork` rows (`PRM_FacilityNw` + `PRM_FacilityTx`) are **auto‑created by the `PRM_HealthcareFacilityNetworkTrigger`** when **E18** inserts the **Level‑4 `HealthcareFacilityNetwork` rows (RT `PRM_FacilityPractitionerTxNw`)** in `Level4RecordCreationBatch` (seq 5). No E22 input needed; `location.networkTaxonomyRoles[]` is consumed by the **Level‑4 flow (E18)**, which also owns the HFN CMA/CDM.

---

## 5. Idempotency, DML & governor

- **Idempotency delegated to the services:** **E14** pre‑check by `(PractitionerId + HealthcareFacilityId + RT)` (PLA) / `(PractitionerId + AccountId + RT)` (PPA) → matched Id updates (DR `HPFId` pattern); **E15** pre‑check by `(PRM_HealthcareFacility__c + RecordTypeId)` → update‑in‑place; **E19** existence pre‑check; **E16** update‑by‑CM. Retry re‑runs safely.
- **DML:** batch does **no business DML** — only `statusUpdate`/`logFailure`. The **HPF/ProviderFeature triggers** fire (rollup/effective‑date sync) but **do not** write CDM/CMA (org‑scanned) — factor their SOQL/DML into the governor budget.
- **Governor / `BatchSize`:** each `execute` runs E14 + E15 + E19 + E16. Keep **`= 1`** for seq‑4 (shared‑location race avoidance, OQ‑E22‑1) unless a `start()` global location dedupe is built.

---

## 6. Failure semantics (F‑15a) — same as E20/E21 §6

Services throw / return `success=false`; batch sets `anyFailure` + first error; `finish()` sets step status then `findNextJob`. **No full‑chunk rollback** — the CDM (E16) records `*Exception__c` flags; partial writes persist; idempotent retry recovers. If **E14 fails**, E15/CMA proceed for the independent records but E16 records the `HealthCarePractitionerFacility` exception.

---

## 7. Reference skeleton (illustrative — not final)

> Depends on `PRM_HPFService` (E14), `PRM_ProviderFeatureService` (E15), `PRM_CMAService` (E19), `PRM_CaseDataManagerService` (E16), `PRM_AsyncOrchestrator` (C3). Correlation + constructor pattern reuse E20/E21 (§2/§3). CMA/CDM scope per §9. *(No E17 — HFN is a trigger side‑effect of E18/Level‑4.)*

```apex
public with sharing class PRM_PLRelatedBatch
        implements Database.Batchable<Object>, Database.Stateful {

    private final Id jobId;
    private final Id stepDetailId;
    public PRM_PLRelatedBatch(Id jobId, Id stepDetailId) {
        this.jobId = jobId; this.stepDetailId = stepDetailId;
    }

    private String flow;
    private Boolean anyFailure = false;
    private String firstError;

    // 1) start: flow + NPI correlation (E20 §3) + explode per group (group-grain, mirrors E21) + seq-2 Id resolution (HCF + group Account, §3.1)
    public Iterable<Object> start(Database.BatchableContext bc) {
        PRM_AsyncJob__c job = [SELECT Id, PRM_ProcessName__c FROM PRM_AsyncJob__c WHERE Id = :jobId WITH USER_MODE];
        this.flow = job.PRM_ProcessName__c;
        Map<String, Object> payload = (Map<String, Object>) new PRM_AsyncOrchestrator().jsonFileParser(jobId);
        List<Object> nodes = (List<Object>) payload.get('practitioners');
        List<Object> workItems = explodePerGroup(nodes);      // one single-group node per group (correlated via E20 §3)
        resolveSeq2Ids(workItems);                            // HCF Id by composite extId + group Account (§3.1, OQ-E22-2)
        return workItems;                                     // chunked by group count (BatchSize per config, rec: 1 — OQ-E22-1)
    }

    // 2) execute: per group work item -> E14 -> E15 -> E19 -> E16  (no E17: HFN is trigger-created in E18/Level-4)
    public void execute(Database.BatchableContext bc, List<Object> scope) {
        try {
            List<Object> cmaRequests = new List<Object>();
            Map<Id, Set<String>> created = new Map<Id, Set<String>>();      // per caseManagerId
            Map<Id, Set<String>> failedTypes = new Map<Id, Set<String>>();

            // ── E14: affiliations (PLA + PPA) ──
            List<Object> affReqs = new List<Object>();
            for (Object o : scope) buildAffiliationReqs((Map<String,Object>) o, affReqs);
            Map<String, Object> e14Resp = affReqs.isEmpty() ? null
                : new PRM_HPFService().execute(new Map<String,Object>{ 'flow'=>flow, 'affiliations'=>affReqs });
            if (e14Resp != null) {
                if (failed(e14Resp)) { recordFailure(e14Resp); markFailed(scope,'HealthCarePractitionerFacility',failedTypes); }
                else collectE14(e14Resp, scope, cmaRequests, created);      // CMA: Practitioner_Practice_Location; CDM: HealthCarePractitionerFacility
            }

            // ── E15: provider features (AssistiveAid + ACC) ──
            List<Object> featReqs = new List<Object>();
            for (Object o : scope) buildFeatureReqs((Map<String,Object>) o, featReqs);
            Map<String, Object> e15Resp = featReqs.isEmpty() ? null
                : new PRM_ProviderFeatureService().execute(new Map<String,Object>{ 'flow'=>flow, 'features'=>featReqs });
            if (e15Resp != null) {
                if (failed(e15Resp)) { recordFailure(e15Resp); markFailed(scope,'ProviderFeature',failedTypes); }
                else collectE15(e15Resp, scope, cmaRequests, created);      // CMA: Provider_Feature; CDM: ProviderFeature
            }

            // ── (no E17: HealthcareFacilityNetwork is trigger-created during E18/Level-4; its CMA/CDM owned there) ──

            // ── E19: CMA (one call; all associations gathered above) ──
            if (!cmaRequests.isEmpty()) {
                Map<String, Object> r = new PRM_CMAService().execute(new Map<String,Object>{ 'associations'=>cmaRequests });
                if (failed(r)) recordFailure(r);
            }

            // ── E16: CDM update (per CM; seq-4 tokens: HealthCarePractitionerFacility, ProviderFeature) ──
            writeCdm(scope, created, failedTypes);

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

    // ── helpers (correlateByNpi, resolveSeq2Ids, buildAffiliationReqs, buildFeatureReqs,
    //     collectE14/E15 (CMA rows + CDM tokens), writeCdm, failed/recordFailure, etc.) — see §9 for the CMA/CDM mapping ──
}
```

---

## 8. Sequence (end‑to‑end)

```
seq 2 (PracticeLocationAndGroupBatch) Completed → findNextJob → invokeJob(step seq 4)
  → Database.executeBatch(new PRM_PLRelatedBatch(jobId, stepId), 1)
      start()   : flow; NPI-correlate practitioners; explode into one work item PER GROUP (group-grain, mirrors E21);
                  resolve seq-2 HCF Ids + group Account Ids → Iterable<single-group nodes> (chunk = group count)
      execute() : per group work item →
                    E14 (affiliations: HPF · RT PLA + PPA)
                    E15 (features: PRM_ProviderFeature__c · RT AssistiveAid + ACC)
                    E19 (CMA: Practitioner_Practice_Location + Provider_Feature)
                    E16 (CDM: HealthCarePractitionerFacility + ProviderFeature)
      finish()  : statusUpdate(step) → findNextJob(jobId)
  → seq 5 (Level4RecordCreationBatch / E18): inserts Level-4 HealthcareFacilityNetwork (RT PRM_FacilityPractitionerTxNw)
       → HFN trigger auto-creates PRM_FacilityNw + PRM_FacilityTx; E18 owns any HFN CMA/CDM
  → (next step) or job Completed → notify
```

---

## 9. Service wiring + CMA / CDM scope (✅ org‑grounded — IBXDEV01)

**Order in `execute()`:** E14 → E15 → E19 → E16.

### 9.1 CMA (E19) — record types (from `PRM_FormSubUtility.cmaFieldSets` · verified active + fields present)

| Created record | CMA record type | primary lookup | contextual lookups | Owner |
|---|---|---|---|---|
| **HealthcarePractitionerFacility** (E14) | `Practitioner_Practice_Location` | `PRM_HealthcarePractitionerFacility__c` | `PRM_HealthcareFacility__c` | **E14** |
| **PRM_ProviderFeature__c** (E15) | `Provider_Feature` | `PRM_ProviderFeature__c` | `PRM_Account__c`, `PRM_HealthcareFacility__c` | **E15** |

- ✅ **Org‑verified:** RTs `Practitioner_Practice_Location` + `Provider_Feature` are **active**; all lookup fields (`PRM_HealthcarePractitionerFacility__c`, `PRM_ProviderFeature__c`, `PRM_HealthcareFacility__c`, `PRM_Account__c`, `PRM_CaseManager__c`) exist on `PRM_CaseManagerAssociation__c`.
- **Contextual lookups are best‑effort** (E19 F‑1: only `PRM_CaseManager__c` is required). For E15, `PRM_Account__c` = the group Account (§3.1). *(The `Practitioner_Practice_Location` context `PRM_HealthcareFacilityNetwork__c` is only relevant once the HFN exists — created later in E18/Level‑4 — so it's left null here.)*
- **Network/Taxonomy CMA** (`Practice_Location_Network` / `Practice_Location_Taxonomy`) is **owned by the Level‑4 flow (E18)**, not E22 (E17 dropped).
- caseManagerId = the practitioner's CM (§3). Aggregate all requests → **one `PRM_CMAService.execute`** per chunk.

### 9.2 CDM (E16) — tokens E22 sets on the CM's CDM (✅ verified present, non‑nillable booleans)

| Grain | Token → CDM flag / exception | Source |
|---|---|---|
| Affiliation | `HealthCarePractitionerFacility` → `PRM_HealthCarePractitionerFacility__c` / `PRM_HCPractitionerFacilityException__c` | E14 |
| Feature | `ProviderFeature` → `PRM_ProviderFeature__c` / `PRM_ProviderFeatureException__c` | E15 |

- ✅ **Both tokens already exist in E16's `FIELDS_BY_TOKEN` vocabulary** (the "later batches" block) — **no E16 change needed**; E22 just emits them.
- ⚠ **No trigger sets these** (`PRM_HCPFTriggerHelper` / `PRM_ProviderFeatureTriggerHandler` org‑scanned: no CDM/CMA writes) — **E22 owns emitting them** (unlike seq‑2's `HealthCareFacility`, which is HCF‑trigger‑set). Legacy parity: the `PRMPractitionerAddressCreation` IP did this via the `PRMDRPCaseDataManager` DR.
- **`HealthcareFacilityNetwork` CDM token is owned by the Level‑4 flow (E18)** — the HFN records are trigger‑created there, so E18 (or its trigger) sets that flag, not E22.
- E16 runs **UPDATE** here (the CDM row already exists from seq‑1/seq‑2 for the same CM) — touches only E22's flags; monotonic; idempotent. Failed types → `*Exception__c`.

---

## 10. Open items / clarifications

- **🔑 OQ‑E22‑1 — shared‑location concurrency / `BatchSize`.** E15 (per‑location feature) can race across parallel chunks on a shared `HealthcareFacility`. **Recommend `PRM_BatchSize__c = 1`** (mirror E21) unless a `start()`‑level location dedupe is built. *(With `=1`, a shared location seen by a later practitioner hits E15's pre‑check → update‑in‑place, no duplicate.)*
- **✅ OQ‑E22‑2 — practice‑location (HCF) Id resolution — DECIDED (a) + shared helper (§3.1).** E22 recomputes `HealthcareFacility.PRM_ExternalId__c` via **`PRM_FormSubUtility.computeHcfExternalId(...)`** (the single shared helper, reused by E13), then bulk‑queries it back. **Remaining prerequisite:** E3 must populate `Account.SourceSystemIdentifier` (OQ‑E21‑2/OQ‑E13‑18) so the composite prefix matches.
- **✅ OQ‑E22‑3 — E17 — RESOLVED: DROPPED.** The facility-grain `HealthcareFacilityNetwork` rows (`PRM_FacilityNw` + `PRM_FacilityTx`) are **auto‑created by the `PRM_HealthcareFacilityNetworkTrigger`** when **E18** inserts the **Level‑4 `HealthcareFacilityNetwork` rows (RT `PRM_FacilityPractitionerTxNw`)** in `Level4RecordCreationBatch` (seq 5). E22 does **not** invoke E17; the HFN CMA (`Practice_Location_Network`/`Taxonomy`) + CDM (`HealthcareFacilityNetwork`) are owned by the **Level‑4 flow (E18)**.
- **OQ‑E22‑4 — `invokeJob` switch + `PRM_AsyncJobConfig__mdt` seq‑4 row.** Register `PRM_PLRelatedBatch` (class switch + config: seq, batch size, service class name).
- **Inherited:** E14 OQ‑E14‑1b (pre‑check owner), E15 OQ‑E15‑4 `Wheelchair Accessible` mapping row.

---

## 11. Recommendations (summary)

1. **Reuse E20/E21's frame** — constructor‑arg context (§2), NPI correlation (§3), aggregated CMA + no‑rollback CDM (§6/§9). Only the `execute()` orchestration differs.
2. **`BatchSize = 1` for seq‑4** until a `start()`‑level location dedupe exists — prevents shared‑location feature/network races (OQ‑E22‑1).
3. **Resolve seq‑2 Ids in `start()`** by composite external id (OQ‑E22‑2) — keeps services SOQL‑free.
4. **E22 emits CMA (E19) + CDM (E16) for E14/E15** — verified applicable and **not** trigger‑covered.
5. **Drop E17 from E22** — `HealthcareFacilityNetwork` is a trigger side‑effect of E18/Level‑4; its CMA/CDM belong to that flow.

---

## 12. Definition of Done

- [ ] `PRM_PLRelatedBatch implements Database.Batchable<Object>, Database.Stateful` with `(Id jobId, Id stepDetailId)` (E20 §2.1 pattern); `invokeJob` switch + `PRM_AsyncJobConfig__mdt` seq‑4 row added (OQ‑E22‑4).
- [ ] `start()`: flow + NPI correlation (E20 §3) + **explode into one work item per group** (group‑grain iteration, mirrors E21 — chunk scales with group count) + seq‑2 HCF/group‑Account Id resolution via **shared `PRM_FormSubUtility.computeHcfExternalId(...)`** + bulk query (§3.1); `Iterable<Object>` (BatchSize per config, rec 1).
- [ ] **Shared composite helper** `PRM_FormSubUtility.computeHcfExternalId(...)` extracted (single source of truth) and **E13 refactored to call it** (replaces its inline replica); E3 populates `Account.SourceSystemIdentifier` (OQ‑E21‑2).
- [ ] `execute()`: per group work item → **E14 → E15 → E19 → E16**; aggregate CMA; track created/failed per CM. *(No E17 — HFN trigger‑created in E18/Level‑4.)*
- [ ] **E14** invoked with PLA + PPA affiliations (§4); **E15** with AssistiveAid + ACC features (§4).
- [ ] **E19 (CMA):** `Practitioner_Practice_Location` (E14) + `Provider_Feature` (E15); one call; idempotent pre‑check (§9.1).
- [ ] **E16 (CDM):** tokens `HealthCarePractitionerFacility` (E14) + `ProviderFeature` (E15) per CM; UPDATE path; no rollback; idempotent (§9.2).
- [ ] `finish()` sets status then `findNextJob` (F‑19); failure → step `Failed` (halt).
- [ ] Idempotent: re‑run creates no duplicates (E14/E15 pre‑checks, E19 pre‑check, E16 update‑by‑CM).
- [ ] `<Class>Test` ≥ 85% incl. multi‑location, a shared‑location case, gating (no features), and a failure→halt path (stub the services).
- [ ] Field/relationship + CMA record types + CDM flags validated against the org (✅ done for E14/E15).
