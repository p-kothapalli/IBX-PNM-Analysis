# E21 · `PRM_PracticeLocationAndGroupBatch` — Batch Design *(PracticeLocationAndGroupBatch · seq 2)*

> **Parent:** `Epic_E_Practitioner_Services_Part2.md` (Part 2). **Framework:** `Epic_C_Async_Framework.md` (batch contract **C4**, orchestrator **C3**). **Sibling:** `E20_PRM_PractitionerBatch.md` (seq 1) — E21 mirrors its patterns (constructor‑arg context §2.1, NPI correlation §3, no‑rollback CDM §6). **Schema:** Epic A async objects.
> **Role:** the **sequence‑2 batch**. After `PractitionerBatch` (seq 1) built the practitioner graph + CDM, E21 reads the same Job JSON, correlates each practitioner to its Case Manager + Account, and **prepares input for the group/location services and invokes them**, then chains the next step.
>
> **🎯 Scope (per request):** wires **`E3 · PRM_GroupService` → `E13 · PRM_HealthcareFacilityCreationService` → `E8 · PRM_InfoCodeService` (facility‑grain) → `E19 · PRM_CMAService` → `E16 · PRM_CaseDataManagerService`.** *(E14/E15/E17 (affiliations, features, networks) are `PLRelatedBatch` seq 4; E18 is `Level4RecordCreationBatch` — not here.)*
>
> **Decisions:** grain = **per GROUP** (⚠ **UPDATED 2026‑07‑09** — was per practitioner). `start()` explodes each correlated practitioner into **one work item per group**, so the iteration/chunking scope tracks the **group count** (a practitioner with 5 groups → 5 work items) — a practitioner's many groups/locations are no longer packed into a single chunk. Records still dedupe via E03/E13 external‑id (shared groups appear once per owning practitioner so per‑CM CMA/CDM stays correct). **`PRM_BatchSize__c = 1`** for seq‑2 (avoid parallel races on **shared groups** — now = one group per chunk). **E12 (`PRM_HealthcareProviderNpiService`) logic is folded into E13** (E13 owns the location NPI); CMA/CDM scope from the org (§9).
>
> **Sample payload:** `docs/sampleInputs/PractitionerCreation/PRM_MultiPractitioner_lowvolume.json`.
> **Tags:** **[CONFIRMED]** · **[OPEN]** · **[RECOMMENDATION]** · **Pending Clarification**.

---

## 1. Role & cardinality

- **One batch per Job step** (seq 2). Dispatched by the orchestrator (`PRM_AsyncJobConfig__mdt`: seq 2 / `PRM_ServiceClassName__c='PRM_PracticeLocationAndGroupBatch'` / **`PRM_BatchSize__c = 1`**). Runs **after** seq‑1 completes (halt‑on‑failure chain).
- **Reads, does not create directly.** All writes happen **inside the services — E3 → E13 → E8 → E19 (CMA) → E16 (CDM)**. The batch = **orchestration + input preparation**: parse JSON → correlate → transform → invoke → status/chain.
- **`Database.Batchable<Object>, Database.Stateful`** — the **iteration unit is the GROUP** (⚠ UPDATED — was the practitioner node). `start()` correlates each practitioner (NPI → CM/Account) then emits **one work item per group**, each a single‑group node carrying the practitioner's context (`caseManagerId`/`accountId`/`practitionerId` + effective dates) and exactly that one group's `locations[]`. This spreads a high‑group practitioner across group‑sized chunks (easier on the E13 facility‑trigger cascade). Case Manager ↔ practitioner is 1:1, and each group node still carries its owning practitioner's CM, so CMA/CDM stay per‑CM clean.
- **⚠ Shared groups → `BatchSize = 1` (decision).** A group (`{taxId}-{groupName}`) can be referenced by **multiple practitioners**; it therefore appears as **one work item per owning practitioner** (needed so each CM gets its own CMA/CDM). E03/E13 dedupe the actual records by external id (`upsert`/existence gate), but **parallel** chunks touching the same group could race — so **seq‑2 runs `BatchSize = 1`** (now one *group* per chunk). *(Re‑tune only if a `start()`‑level global dedupe is added — OQ‑E21‑1.)*
- **Halt‑on‑failure (F‑15a).** Any failure → step `Failed` → job `Failed` → chain halts; recovered via **Retry**. Idempotent (E03 upserts by external id; E13 gate on HCF existence; E19 pre‑check; E16 update‑by‑CM) → retry re‑runs safely.

---

## 2. Batch contract (honours Epic C · C4)

| Method | Responsibility |
|---|---|
| *constructor* `(Id jobId, Id stepDetailId)` | Context passed in by the orchestrator — **identical to E20 §2.1** (constructor args, `final` members; the `invokeJob` switch already dispatches `new PRM_PracticeLocationAndGroupBatch(jobId, stepId)`). |
| `start(bc)` | Read the Job payload once (`jsonFileParser`); derive `flow`; **correlate each practitioner to its CM + Account by NPI (§3)**; **explode into one work item per group** (each a single‑group node stamped with `accountId`/`practitionerId`/`caseManagerId` + effective dates); **resolve reference data** (info‑code codes → Ids — §4); return an **`Iterable<Object>`** of **group** nodes (chunked by `PRM_BatchSize__c = 1` → one group per chunk). |
| `execute(bc, scope)` | For the chunk: build + invoke **E3 (groups)** → **E13 (locations)** (threading the group `AccountId`) → **E8 (facility info codes, gated)** → **E19 (CMA)** once → **E16 (CDM)** once. Track created/failed per CM. Capture failure (no rollback — §6). |
| `finish(bc)` | **F‑19:** `statusUpdate(stepDetailId, Completed|Failed)` first, then `findNextJob(jobId)`. |

> **Constructor / `invokeJob`** — no change beyond E20 §2.1; the per‑class switch already includes `PRM_PracticeLocationAndGroupBatch`. **No interface, no new field.**

---

## 3. Correlation — same as E20 (§3)

Identical NPI correlation to E20: one relationship query over `PRM_AsyncJobRecords__c` → `Map<npi → {accountId, practitionerId, caseManagerId}>`. `start()` then stamps this context onto **each exploded group node** (one per group of the practitioner). The owning practitioner's `caseManagerId` is the CM used for that group's locations' CMA + CDM. *(Groups are the work items; each carries its single group's `locations[]` — no separate correlation.)*

> **⚠ [OPEN — OQ‑E21‑2] `HealthcareFacility.AccountId` + `Account.SourceSystemIdentifier`.** E13 sets `HealthcareFacility.AccountId` = the **group Vendor Account** (created by E3, threaded in `execute()`), and the HCF trigger's external id reads **`Account.SourceSystemIdentifier`** on that group Account — so **E3 must populate `Account.SourceSystemIdentifier = {taxId}-{groupName}`** (E13 OQ‑E13‑18; likely an E3 fix). Confirm.

---

## 4. Preparing service inputs (transform: source → `params`)

**E3 `PRM_GroupService`** — one call per chunk with the deduped groups:

| E3 field | Source | Status |
|---|---|---|
| `groups[].taxId` / `groupName` | `groups[].taxId` / `groupName` | [CONFIRMED] |
| `groups[].caseManagerId` | the practitioner's CM (§3) | [CONFIRMED] |
| `groups[].isActive` / `effectiveFrom` / `effectiveTo` | practitioner context (`effectiveDate`?) | **[OPEN]** OQ‑E3‑7 |
| `groups[].vendorType` (`Type`/`PRM_VendorType__c`) | — | **[OPEN]** OQ‑E3‑10 |

**E13 `PRM_HealthcareFacilityCreationService`** — one call per chunk with the locations (threaded from E3's group `AccountId`):

| E13 field | Source | Status |
|---|---|---|
| `locations[].accountId` | **group Vendor Account Id** (from E3 output) | [CONFIRMED] |
| `locations[].caseManagerId` | the practitioner's CM (§3) | [CONFIRMED] |
| `locations[].locationNpi` | `locations[].locationNpi` (E13 resolves/creates the NPI internally — E12 folded in) | [CONFIRMED] |
| `locations[].practiceName` / `practiceClassification` / `telehealthOnly` / `primaryPracticeLoc` | source | [CONFIRMED] |
| `locations[].effectiveFrom` | practitioner `effectiveFromDate` | [CONFIRMED] (OQ‑E13‑8) |
| `locations[].locationType` | — (required, not in source) | **[OPEN]** OQ‑E13‑6 |
| `locations[].addresses[]` | `locations[].addresses[]` | [CONFIRMED] |

**E8 `PRM_InfoCodeService` (facility‑grain, `prepareBulkForLocations`)** — gated on `selectedInfoCodes`:

| E8 field | Source | Status |
|---|---|---|
| `infoCodes[]` (resolved InfoCode Ids) | `locations[].selectedInfoCodes` (`"Delegated;Par"` → split `;` → resolve code→InfoCode Id in `start()`) | **[OPEN]** OQ‑E21‑3 (resolution + facility‑grain contract) |
| `accountId` / `healthcareFacilityId` / `caseManagerId` | group Account / E13 HCF / CM | **[OPEN]** OQ‑E21‑3 (E8 facility‑grain input shape) |

> **E12 folded into E13 (decision):** the location NPI (`HealthcareProviderNpi`, `NpiType='Organization'`) is created **inside E13** (former `PRM_HealthcareProviderNpiService` logic) — E21 does **not** call a separate NPI service. *(Update E13 §1/§7 to reflect E12‑absorbed — OQ‑E21‑4.)*

---

## 5. Idempotency, DML & governor

- **Idempotency delegated to the services:** E03 `upsert` by `Account.HealthCloudGA__SourceSystemId__c` + `Identifier/HCP` `PRM_RecordKey__c`; E13 **existence gate** on `HealthcareFacility.PRM_ExternalId__c` (create Location/Address/HCF only if new); E19 existence pre‑check; E16 update‑by‑CM. Retry re‑runs safely.
- **DML:** batch does **no business DML** — only `statusUpdate`/`logFailure`. The **HCF trigger** fires additional automations (Location NPI History, networks, alternate contact, `updateCaseDataManager`) — factor into the governor budget (E13 OQ‑E13‑19).
- **Governor / `BatchSize = 1`:** one **group** per `execute` → E03 + E13 (+ trigger) + E8 + E19 + E16 for that single group's locations. Chunking by group (not practitioner) keeps a high‑group practitioner's location/trigger work bounded per chunk. Keep `=1` for seq‑2 (shared‑group race avoidance); re‑tune only with a `start()` global dedupe (OQ‑E21‑1).

---

## 6. Failure semantics (F‑15a) — same as E20 §6

Services throw / return `success=false`; batch sets `anyFailure` + first error; `finish()` sets step status then `findNextJob`. **No full‑chunk rollback** — the CDM (E16) must record `*Exception__c` flags; partial writes persist; idempotent retry recovers. If **E3 fails**, E13/E8/CMA are skipped for that group (graph incomplete) but E16 still records the exceptions.

---

## 7. Reference skeleton (illustrative — not final)

> Depends on `PRM_GroupService` (E3), `PRM_HealthcareFacilityCreationService` (E13, E12‑absorbed), `PRM_InfoCodeService` (E8 facility‑grain), `PRM_CMAService` (E19), `PRM_CaseDataManagerService` (E16), `PRM_AsyncOrchestrator` (C3). Correlation + constructor pattern reuse E20 (§2.1/§3). CMA/CDM scope per §9.

```apex
public with sharing class PRM_PracticeLocationAndGroupBatch
        implements Database.Batchable<Object>, Database.Stateful {

    private final Id jobId;
    private final Id stepDetailId;
    public PRM_PracticeLocationAndGroupBatch(Id jobId, Id stepDetailId) {
        this.jobId = jobId; this.stepDetailId = stepDetailId;
    }

    private String flow;
    private Boolean anyFailure = false;
    private String firstError;

    // 1) start: flow + NPI correlation, then EXPLODE each practitioner into one work item PER GROUP
    public Iterable<Object> start(Database.BatchableContext bc) {
        PRM_AsyncJob__c job = [SELECT Id, PRM_ProcessName__c FROM PRM_AsyncJob__c WHERE Id = :jobId WITH USER_MODE];
        this.flow = job.PRM_ProcessName__c;
        Map<String, Object> payload = (Map<String, Object>) new PRM_AsyncOrchestrator().jsonFileParser(jobId);
        Map<String, Map<String,Object>> ctxByNpi = correlateByNpi();          // NPI -> {accountId, practitionerId, caseManagerId}
        List<Object> workItems = new List<Object>();
        for (Object pObj : (List<Object>) payload.get('practitioners')) {
            Map<String,Object> p = (Map<String,Object>) pObj;
            Map<String,Object> ctx = ctxByNpi.get((String) p.get('individualNpi'));
            if (ctx == null || !(p.get('groups') instanceof List<Object>)) continue;
            for (Object g : (List<Object>) p.get('groups')) {                 // one work item per GROUP
                workItems.add(new Map<String,Object>{
                    'individualNpi'=>p.get('individualNpi'), 'effectiveFromDate'=>p.get('effectiveFromDate'),
                    'effectiveToDate'=>p.get('effectiveToDate'), 'accountId'=>ctx.get('accountId'),
                    'practitionerId'=>ctx.get('practitionerId'), 'caseManagerId'=>ctx.get('caseManagerId'),
                    'groups'=>new List<Object>{ g } });
            }
        }
        return workItems;                                     // BatchSize = 1 -> one group per chunk
    }

    // 2) execute: per (single) GROUP -> E3 -> E13 -> E8 -> E19 -> E16
    public void execute(Database.BatchableContext bc, List<Object> scope) {
        try {
            List<Object> cmaRequests = new List<Object>();
            Map<Id, Set<String>> created = new Map<Id, Set<String>>();      // per caseManagerId
            Map<Id, Set<String>> failedTypes = new Map<Id, Set<String>>();

            // gather the group + its locations from the chunk (one group per work item)
            List<Object> groupReqs = new List<Object>();                    // deduped E3 inputs
            for (Object o : scope) buildGroupReqs((Map<String,Object>) o, groupReqs);

            // ── E3: group graph (Account/Identifier/HCP) ──
            Map<String, Object> e3Resp = groupReqs.isEmpty() ? null
                : new PRM_GroupService().execute(new Map<String,Object>{ 'flow'=>flow, 'groups'=>groupReqs });
            if (e3Resp != null) {
                if (failed(e3Resp)) { recordFailure(e3Resp); markFailedGroups(scope, failedTypes); }
                else collectE3(e3Resp, scope, cmaRequests, created);        // CMA: PRM_Vendor + Identifier; CDM: Account/Identifier/HealthcareProvider
            }
            Map<String, Id> groupAccountByKey = groupAccountFromResponse(e3Resp);   // {taxId}-{groupName} -> vendor Account Id

            // ── E13: location graph (Location/Address/HCF; NPI + gate internal; trigger -> NPI History + external id) ──
            List<Object> locationReqs = new List<Object>();
            for (Object o : scope) buildLocationReqs((Map<String,Object>) o, groupAccountByKey, locationReqs);
            Map<String, Object> e13Resp = locationReqs.isEmpty() ? null
                : new PRM_HealthcareFacilityCreationService().execute(new Map<String,Object>{ 'flow'=>flow, 'locations'=>locationReqs });
            if (e13Resp != null) {
                if (failed(e13Resp)) { recordFailure(e13Resp); markFailedLocations(scope, failedTypes); }
                else collectE13(e13Resp, scope, cmaRequests, created);      // CMA: PRM_PracticeLocation + Practice_Location_Address; CDM: Location/Address/HealthcareProviderNpi/LocationNPIHistory
            }

            // ── E8: facility-grain info codes (gated selectedInfoCodes) ──
            List<Object> infoReqs = buildInfoCodeReqs(scope, e13Resp);
            if (!infoReqs.isEmpty()) {
                Map<String, Object> r = new PRM_InfoCodeService().execute(new Map<String,Object>{ 'flow'=>flow, 'locations'=>infoReqs });
                if (failed(r)) { recordFailure(r); markInfoCodeFailed(scope, failedTypes); }
                else markCreatedInfoCode(scope, created);                   // CDM: InfoCodeAssignment
            }

            // ── E19: CMA (one call; group + location associations) ──
            if (!cmaRequests.isEmpty()) {
                Map<String, Object> r = new PRM_CMAService().execute(new Map<String,Object>{ 'associations'=>cmaRequests });
                if (failed(r)) recordFailure(r);
            }

            // ── E16: CDM update (per CM; seq-2 tokens). HealthCareFacility flag is trigger-set (updateCaseDataManager). ──
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

    // ── helpers (correlateByNpi, resolveInfoCodeIds, buildGroupReqs, buildLocationReqs, buildInfoCodeReqs,
    //     collectE3/E13 (CMA rows + CDM tokens), writeCdm, failed/recordFailure, etc.) — see §9 for the CMA/CDM mapping ──
}
```

---

## 8. Sequence (end‑to‑end)

```
seq 1 (PractitionerBatch) Completed → findNextJob → invokeJob(step seq 2)
  → Database.executeBatch(new PRM_PracticeLocationAndGroupBatch(jobId, stepId), 1)
      start()   : flow; NPI-correlate practitioners; EXPLODE into one work item PER GROUP; resolve selectedInfoCodes -> InfoCode Ids → Iterable<groupNodes> (BatchSize=1 → one group/chunk)
      execute() : per GROUP →
                    E3  (group: Account/Identifier/HCP)
                    E13 (location: Location/Address/HCF; NPI+gate internal; trigger → Location NPI History + external id + HCF CDM flag)
                    E8  (facility info codes, gated selectedInfoCodes)
                    E19 (CMA: Vendor + Identifier + PracticeLocation + Practice_Location_Address)
                    E16 (CDM: group + location + infoCode tokens; HealthCareFacility flag already trigger-set)
      finish()  : statusUpdate(step) → findNextJob(jobId)
  → (next step seq 3/4 …) or job Completed → notify
```

---

## 9. Service wiring + proposed CMA / CDM scope (org‑grounded — confirm)

**Order in `execute()`:** E3 → E13 → E8 → E19 → E16. E13 needs E3's group `AccountId`; E19/E16 need E3+E13 created Ids.

### 9.1 CMA (E19) — proposed record types (from `PRM_FormSubUtility.cmaFieldSets`)

| Created record | CMA record type | primary lookup | context |
|---|---|---|---|
| **Group Vendor Account** (E3) | `PRM_Vendor` | `PRM_Account__c` | — |
| **Group EIN Identifier** (E3) | `Identifier` | `PRM_Identifier__c` | — |
| **HealthcareFacility** (E13) | `PRM_PracticeLocation` | `PRM_HealthcareFacility__c` | — |
| **Address** (E13) | `Practice_Location_Address` | `PRM_Address__c` | `PRM_HealthcareFacility__c` |

- **Not CMA'd** (no `cmaFieldSets` entry): group `HealthcareProvider`, group/location `HealthcareProviderNpi`, `Location`, `PRM_InfoCodeAssignment__c`. ⚠ `PRM_Info_Code_Assignment` **record type exists but isn't in the mapped 14** — **[OPEN OQ‑E21‑5]** add an `Info_Code_Assignment` field‑set to `PRM_FormSubUtility` if facility info codes must be CMA‑tracked.
- **Network/affiliation CMAs** (`Practice_Location_Network`, `Practitioner_Practice_Location`, `Practice_Location_Taxonomy`, `Practitioner_at_Practice_Location_Taxonomy_and_Network`, `Provider_Feature`) → **PLRelatedBatch (seq 4)** — not E21.
- caseManagerId = the owning practitioner's CM, carried on each group work item. Under `BatchSize=1`, one group (and its practitioner's CM) per chunk.

### 9.2 CDM (E16) — proposed tokens E21 sets on the CM's CDM

| Grain | Token → CDM flag | Source |
|---|---|---|
| Group | `Account` → `PRM_Account__c`; `Identifier` → `PRM_Identifier__c`; `HealthcareProvider` → `PRM_HealthCareProvider__c` | E3 |
| Location | `Location` → `PRM_Location__c`; `Address` → `PRM_Address__c`; `HealthcareProviderNpi` → `PRM_HealthCareProviderNPI__c`; `LocationNPIHistory` → `PRM_LocationNPIHistory__c` | E13 (+ trigger) |
| Info code | `InfoCodeAssignment` → `PRM_InfoCodeAssignment__c` | E8 |

- **⚠ `HealthCareFacility` (`PRM_HealthCareFacility__c`) is set by the HCF trigger** (`updateCaseDataManager` → `PRM_HealthCareFacility__c=true`) — E21/E16 **need not** set it (harmless if it does; idempotent). **[OPEN OQ‑E21‑6]** confirm E16 skips it to avoid contention.
- These tokens already exist in E16's `FIELDS_BY_TOKEN` vocabulary. Shared flags (`Account`/`Identifier`/`HealthcareProvider`) may already be `true` from seq‑1 for the same CM — re‑setting `true` is idempotent.
- Failed types → `*Exception__c` per E16.

---

## 10. Open items / clarifications

- ✅ **OQ‑E21 grain — RESOLVED: per GROUP** (⚠ UPDATED 2026‑07‑09 — was per practitioner). `start()` emits one work item per group so chunking tracks the group count; records dedupe via E03/E13 external id; shared groups appear once per owning practitioner (per‑CM CMA/CDM stays correct).
- ✅ **OQ‑E21‑1 — shared‑group concurrency — RESOLVED: `BatchSize = 1`** for seq‑2 (now one *group* per chunk; avoids parallel races). *(Alt: `start()` global dedupe — deferred.)*
- ✅ **E12 — RESOLVED: folded into E13** (no separate NPI service). **[OPEN OQ‑E21‑4]** update E13 §1/§7 to reflect the absorbed NPI logic + gate.
- **🔑 OQ‑E21‑2 — `Account.SourceSystemIdentifier` on the group Account** (E3) — the HCF external id/gate prefix reads it (E13 OQ‑E13‑18). **Likely an E3 fix** (E3 currently sets `HealthCloudGA__SourceSystemId__c`).
- **OQ‑E21‑3 — E8 facility‑grain contract** — `selectedInfoCodes` (`;`‑delimited codes) → resolve to InfoCode Ids in `start()`; confirm E8's `prepareBulkForLocations` input shape (accountId/healthcareFacilityId/caseManagerId + `infoCodes[]`) and how codes resolve (CL‑E9).
- **OQ‑E21‑5 — Facility InfoCode CMA** — `PRM_Info_Code_Assignment` record type isn't in `cmaFieldSets`; add a field‑set if facility info codes must be CMA‑tracked, else no CMA.
- **OQ‑E21‑6 — CDM `HealthCareFacility` flag** — trigger‑set (`updateCaseDataManager`); confirm E16 skips it.
- **Inherited (unchanged):** E3 OQ‑E3‑5/7/10 (group active/effective/credentialing + vendor type), E13 OQ‑E13‑6/7/9/12/19 (LocationType, BillingType, address dedupe, misc fields, trigger cascade).
- **CL — Service response shapes.** E3 returns `{ taxId, groupAccountId, groupIdentifierId, groupHealthcareProviderId }`; E13 returns `{ locationId, addressIds, healthcareFacilityId, locationNpiId }` (+ trigger‑made Location NPI History, queried if needed). E8 returns `{ infoCodeAssignmentIds }`. Confirm E8 facility‑grain response.

---

## 11. Recommendations (summary)

1. **Reuse E20's frame** — constructor‑arg context (§2.1), NPI correlation (§3), no‑rollback CDM (§6). Only the `execute()` orchestration differs.
2. **`BatchSize = 1` for seq‑2** until a `start()`‑level group/location dedupe is built — prevents shared‑group upsert races.
3. **Thread E3 → E13** — the group Vendor Account Id feeds `HealthcareFacility.AccountId`; **ensure E3 sets `Account.SourceSystemIdentifier`** (OQ‑E21‑2) so the HCF trigger's external id/gate works.
4. **Let the HCF trigger do its cascade** (Location NPI History, `HealthCareFacility` CDM flag, networks) — E21 must not duplicate (E13 OQ‑E13‑19); factor its SOQL/DML into the batch budget.
5. **Confirm the CMA/CDM scope (§9)** — 4 CMA record types (Vendor, Identifier, PracticeLocation, Practice_Location_Address); CDM tokens for group/location/infoCode; `HealthCareFacility` trigger‑set.
6. **Resolve reference data in `start()`** — `selectedInfoCodes` code→Id (reuse E20's `idByField` helper); no service SOQL.

---

## 12. Definition of Done

- [ ] `PRM_PracticeLocationAndGroupBatch implements Database.Batchable<Object>, Database.Stateful` with `(Id jobId, Id stepDetailId)` (E20 §2.1 pattern; `invokeJob` switch already includes it).
- [ ] `start()`: flow + NPI correlation + **explode into one work item per group** + `selectedInfoCodes` code→Id resolution; `Iterable<Object>` of group nodes (BatchSize=1 → one group/chunk).
- [ ] `execute()`: per **group** → **E3 → E13 → E8 (gated) → E19 → E16**; thread group `AccountId` into E13; aggregate CMA; track created/failed per CM.
- [ ] **E13** invoked with the group `AccountId`; E13 owns the location NPI (E12 folded) + HCF existence gate; trigger creates Location NPI History + external id + `HealthCareFacility` CDM flag.
- [ ] **E19 (CMA):** Vendor + Identifier (E3) + PracticeLocation + Practice_Location_Address (E13); one call; idempotent pre‑check (§9.1).
- [ ] **E16 (CDM):** group + location + infoCode tokens per CM; **not** `HealthCareFacility` (trigger‑set); no rollback; idempotent (§9.2).
- [ ] `Account.SourceSystemIdentifier` set by E3 (OQ‑E21‑2); E8 facility‑grain contract confirmed (OQ‑E21‑3).
- [ ] `finish()` sets status then `findNextJob` (F‑19); failure → step `Failed` + DLQ (halt).
- [ ] Idempotent: re‑run creates no duplicates (E03 upserts, E13 gate, E19 pre‑check, E16 update‑by‑CM).
- [ ] `<Class>Test` ≥ 85% incl. multi‑group/multi‑location, a shared‑group case, gating (no info codes), and a failure→halt path (stub the services).
- [ ] Field/relationship API names validated against the org (CMA record types + field sets, CDM flags).
