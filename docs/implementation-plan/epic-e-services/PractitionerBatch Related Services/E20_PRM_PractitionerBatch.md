# E20 · `PRM_PractitionerBatch` — Batch Design *(PractitionerBatch · seq 1)*

> **Parent:** `Epic_E_Practitioner_Services.md` (Part 1 — PractitionerBatch). **Framework:** `Epic_C_Async_Framework.md` (batch‑class contract **C4**, orchestrator **C3**, kickoff **C2**). **Schema:** `Epic_A_Environment_Setup.md` (`PRM_AsyncJob__c`, `PRM_AsyncJobRecords__c`, `PRM_AsyncJobDetails__c`).
> **Role:** the **sequence‑1 batch** of the async pipeline. It reads the Job's payload JSON, correlates each practitioner to its E1 Case Manager + Account, **prepares the input for the practitioner services and invokes them**, then chains the next step.
>
> **🎯 Scope of this doc (per request):** **This iteration wires the record services `E2 · PRM_PractitionerService`, `E5 · PRM_LicenseService`, `E6 · PRM_EducationService`, plus the two cross‑cutting services `E19 · PRM_CMAService` (Case Manager Associations) and `E16 · PRM_CaseDataManagerService` (the per‑case CDM manifest).** `E7/E8/E10/E11` are **deferred** (their source data — `boardCertifications`/practitioner‑grain `infoCodes`/`providerInformation`/`languages` — is **not in the current payload**); their `execute()` seams are left in place (§9).
>
> **Sample payload:** `docs/reference/JSON structure.json` (the source intake shape consumed here).
>
> **Tags:** **[CONFIRMED]** (grounded in C3/C4/E02) · **[OPEN]** (needs confirmation) · **[RECOMMENDATION]**.

---

## 1. Role & cardinality

- **One batch per Job step.** The orchestrator dispatches `PRM_PractitionerBatch` once for the Job's sequence‑1 step (`PRM_AsyncJobConfig__mdt`: `Practitioner Creation` / seq 1 / `PRM_BatchSize__c = 1`). It processes **all** the Job's Case Managers (per C3/C4 — a step runs the whole job).
- **Reads, does not create directly.** Business writes happen **inside the services — E2 → E5 → E6 → E19 (CMA) → E16 (CDM)** this iteration (E7/E8/E10/E11 later). The batch's job is **orchestration + input preparation**: parse JSON → correlate → transform → invoke (record services, then CMA, then CDM) → status/chain.
- **E19 (CMA) + E16 (CDM) run after the record services, in the same chunk transaction.** E19 needs the created record Ids (Identifier/Taxonomy/License); E16 (one CDM per Case Manager) needs to know **what was actually created** (per the decided "set on creation"). The **Practitioner CMA is created by E1** at intake — E20 does not re‑create it.
- **`Database.Batchable<Object>, Database.Stateful`** — the **iteration unit is the practitioner node from the Job JSON** (not an SObject). Case Manager ↔ practitioner is **1:1**, so each node is **one practitioner = one Case Manager = one CDM**; no grouping is needed (a Case Manager maps to a single work‑item and can't be split across chunks — OQ‑E16‑1). `start()` returns an **`Iterable<Object>`** of correlated practitioner work‑items; the platform splits them into chunks by `PRM_BatchSize__c` (e.g. up to **10** → up to 10 Case Managers/practitioners per chunk). *(Enabled by the §2.1 **per‑branch dispatch** — `invokeJob` calls `Database.executeBatch` on the concrete batch type, so a non‑SObject `Iterable` batch is fine.)*
- **Halt‑on‑failure (F‑15a).** Any failure in the step → step `Failed` → job `Failed` → chain halts (no notification); recovered via the per‑step **Retry** (C5). The batch is **idempotent** (E2 upserts by `PRM_RecordKey__c`), so a retry re‑runs the whole step safely.

---

## 2. Batch contract (honours Epic C · C4)

| Method | Responsibility |
|---|---|
| *constructor* `(Id jobId, Id stepDetailId)` | Context is **passed in** by the orchestrator (see §2.1) — held in `final` members; no DB resolution. |
| `start(bc)` | Read the Job's **single payload `ContentVersion`** once (`jsonFileParser(jobId)`); derive `flow`; parse to **practitioner nodes**; **correlate each node to its Case Manager + Account (§3)**; **return an `Iterable<Object>`** of the (correlated) practitioner work‑items. The platform splits them into chunks by `PRM_BatchSize__c`. |
| `execute(bc, scope)` | Receives a **chunk (`List<Object>`)**; invoke **E2 → E5 (gated) → E6 (gated)**; aggregate **E19 CMA** requests (Identifier/Taxonomy from E2, Business_License from E5) → one CMA call; then **E16 CDM** once (manifest per Case Manager, created+exception flags). Track per‑practitioner created/failed for E16. Capture failure (bulk‑first, F‑17). |
| `finish(bc)` | Per **F‑19**: `statusUpdate(stepDetailId, Completed|Failed)` **first**, **then** `PRM_AsyncOrchestrator.findNextJob(jobId)`. |

### 2.1 Context via constructor parameters — **no interface, no new field**

**The batch takes its context as constructor arguments** — `new PRM_PractitionerBatch(jobId, stepDetailId)` — held in `final` members. `start/execute/finish` use them directly. **No `resolveContext`, no `PRM_AsyncApexJobId__c` field, no shared interface.**

```apex
private final Id jobId;
private final Id stepDetailId;
public PRM_PractitionerBatch(Id jobId, Id stepDetailId) {
    this.jobId = jobId;
    this.stepDetailId = stepDetailId;
}
```

**Epic C implication (required change).** `PRM_AsyncOrchestrator.invokeJob` must construct the batch **with arguments** — Apex's `Type.forName(name).newInstance()` only supports the **no‑arg** constructor, so it can't pass `jobId`. Replace that one line with a small **per‑class construction** (the five batch class names are a fixed, known set; the MDT still drives sequence / mode / batch size):

```apex
// PRM_AsyncOrchestrator.invokeJob — set Running, then construct + dispatch the named batch WITH context.
// Dispatch INSIDE the switch (one executeBatch per branch) so each concrete batch is passed with its own type.
Id jobId = step.PRM_AsyncJob__c, stepId = step.Id;
Integer size = (Integer) step.PRM_BatchSize__c;
statusUpdate(jobId, 'Running', null);
statusUpdate(stepId, 'Running', null);
switch on cfg.PRM_ServiceClassName__c {
    when 'PRM_PractitionerBatch'             { Database.executeBatch(new PRM_PractitionerBatch(jobId, stepId), size); }
    when 'PRM_PracticeLocationAndGroupBatch' { Database.executeBatch(new PRM_PracticeLocationAndGroupBatch(jobId, stepId), size); }
    when 'PRM_PLRelatedBatch'                { Database.executeBatch(new PRM_PLRelatedBatch(jobId, stepId), size); }
    when 'PRM_Level4Batch'     { Database.executeBatch(new PRM_Level4Batch(jobId, stepId), size); }
    when else { statusUpdate(stepId, 'Failed', 'Unknown batch: ' + cfg.PRM_ServiceClassName__c);
                statusUpdate(jobId, 'Failed', null); }   // guarded failure
}
```

> **Why this is safe / acceptable (validation):**
> - **Deterministic.** Context is set at construction in the orchestrator transaction and carried into the run (instance members serialize with the batch); no DB round‑trip, no per‑run token, no timing dependency.
> - **Concurrency‑safe by construction.** Each instance owns its own `jobId`/`stepDetailId`, so concurrent Jobs running the same step never collide (unlike the rejected `Running`‑status self‑discovery).
> - **No typing conflict.** Dispatching **inside** the switch (one `executeBatch` per branch) means each concrete batch is passed to `executeBatch` directly — so E20 can be a **`Batchable<Object>` iterable** (JSON practitioner nodes) while QueryLocator‑based batches stay `Batchable<SObject>`; there is **no common `Batchable<SObject>` cast** to break.
> - **No schema change** (no `PRM_AsyncApexJobId__c`) and **no shared interface/base class** (no `PRM_AsyncBatchContext`).
> - **Trade‑off:** `invokeJob` now **knows the concrete batch class names** (a `switch`) instead of pure `Type.forName` dynamic dispatch. Accepted: the five batch classes are a closed, framework‑owned set, the MDT still owns sequencing/mode/size, and an unknown name is a guarded failure.
>
> **OQ‑E20‑6:** confirm this `invokeJob` change in Epic C (replace the no‑arg `Type.forName().newInstance()` with the per‑class `newBatch(...)`).

---

## 3. Correlation — JSON node ↔ Case Manager ↔ Account

The practitioner node (JSON) is the iteration unit, but the services need per practitioner the **Account Id** (`practitionerInfo.id`), **`PersonContactId`** (E5/E6 `ContactId`), the **`npi`**, and the **`caseManagerId`**. The node alone has `individualNpi` — the rest come from the Job's Case Manager rows. **`start()` correlates once** and **attaches `accountId` + `practitionerId` (PersonContactId) + `caseManagerId` onto each node** before returning the iterable (so the services do no lookups — per the `prm-service-class-boundaries` rule):

- `PRM_AsyncJobRecords__c.PRM_CaseManager__c` → **IndividualApplication** (the Case Manager).
- `IndividualApplication.AccountId` → the **practitioner Account** (created by E1); `Account.PersonContactId` → the **PersonContact** (E5/E6 `ContactId`).
- `Account.HealthCloudGA__SourceSystemId__c` = the **NPI** (E1 stamps it from `practitionerInfo.npi`).
- *(`healthcareProviderId` is **not** resolvable here — E2 creates it; it's threaded from E2's output in `execute()` into E6.)*

**✅ DECIDED (OQ‑E20‑1): correlate by NPI** (no payload‑enrichment dependency). In `start()`, one relationship query over the Job's Case Manager rows resolves Account Id, PersonContactId **and** NPI per Case Manager —

```apex
SELECT PRM_CaseManager__c, PRM_CaseManager__r.AccountId,
       PRM_CaseManager__r.Account.PersonContactId,
       PRM_CaseManager__r.Account.HealthCloudGA__SourceSystemId__c
FROM PRM_AsyncJobRecords__c WHERE PRM_AsyncJob__c = :jobId
```

— build `Map<npi → {accountId, practitionerId, caseManagerId}>`, then stamp each practitioner node by its `individualNpi`. NPI is **business‑confirmed unique** (E02 §8 CL‑E2), so this is a safe key. A node with no match is a **correlation miss** (skip + flag — OQ‑E20‑1). **✓ Org‑validated (IBXDEV01):** `PRM_CaseManager__c` → IndividualApplication (rel `PRM_CaseManager__r`), `IndividualApplication.AccountId` → Account, `Account.HealthCloudGA__SourceSystemId__c` (NPI) all exist — the traversal compiles.

> **Not chosen (Option A):** the EPIC F intake could enrich the stored JSON with `accountId`/`caseManagerId` per practitioner (OQ‑E2‑3), removing the correlation query — but **NPI correlation is the decision** (OQ‑E20‑1) since it avoids the cross‑epic enrichment dependency.

---

## 4. Preparing E2's input (transform: source node → `params`)

E2's contract (E02 §4/§5): `params = { flow, practitioners:[ { practitionerInfo, taxonomies[], identifiers[] } ] }`, where `practitionerInfo.id` = Account Id and `caseManagerId` is supplied by the batch. The batch maps each **source** practitioner node (`JSON structure.json`) to that shape:

| E2 field | Source (`JSON structure.json`) | Status |
|---|---|---|
| `practitionerInfo.id` | resolved **Account Id** (via §3) | [CONFIRMED] |
| `practitionerInfo.npi` | `individualNpi` | [CONFIRMED] |
| `practitionerInfo.firstName` / `lastName` | `firstName` / `lastName` | [CONFIRMED] |
| `practitionerInfo.effectiveFrom` | **`effectiveDate`** (source field name — §4.1) | [CONFIRMED] |
| `practitionerInfo.formType` | `formType` (per‑practitioner **IBC vs Delegated** branch — §4.1) | [CONFIRMED] |
| `caseManagerId` (sibling of `practitionerInfo`) | resolved CM Id (via §3) | [CONFIRMED] |
| `practitionerInfo.npiType` | ⟲ `'Individual'` (literal, set in batch — OQ‑E20‑3) | **[CONFIRMED]** ✓ org (NpiType = Individual/Organization) |
| `practitionerInfo.isActive` | ⟲ `true` (set in batch — OQ‑E20‑3) | **[CONFIRMED]** |
| `practitionerInfo.effectiveTo` | ⟲ `null` (set in batch — OQ‑E20‑3) | **[CONFIRMED]** |
| `practitionerInfo.hcpEffectiveFrom` / `hcpEffectiveTo` | — *(not in source)* | **[OPEN]** OQ‑E20‑3b |
| `practitionerInfo.existingHcpNpiId` | — *(blank → new‑NPI path)* | [CONFIRMED] (blank) |
| `taxonomies[].taxonomyCode` | `taxonomies[].careTaxonomyCode` | [CONFIRMED] |
| `taxonomies[].isPrimary` | `taxonomies[].isPrimarySpecialty` | [CONFIRMED] |
| `taxonomies[].providerType` | ⚠ org field is **`PRM_ProviderType__c` (a lookup)** — `practitionerType` ("Physician") is a label, not an Id | **[OPEN]** OQ‑E20‑4 |
| `taxonomies[].name` | `primarySpecialty` (primary only)? — `Taxonomy.Name` is **required** (org) | **[OPEN]** OQ‑E20‑4 |
| `taxonomies[].careTaxonomyId` | *(resolved inside E2 via `PRM_TaxonomySelector`)* | [CONFIRMED] |
| `identifiers[]` | `caqhNumber` → `{ type:'CAQH', name:caqhNumber }` — **org‑valid** (`Identifier.PRM_Type__c` includes `CAQH`; `ParentRecordId` accepts Account) | **[OPEN]** OQ‑E20‑5 (confirm) |

> **✅ OQ‑E20‑3 — the batch fills these** (decision): `npiType = 'Individual'` (literal), `isActive = true`, `effectiveTo = null`, `effectiveFrom` ← the source **`effectiveDate`**. **Still open:** `hcpEffectiveFrom`/`hcpEffectiveTo` (OQ‑E20‑3b), taxonomy `providerType`/`name` (OQ‑E20‑4), identifiers (OQ‑E20‑5). The remaining gaps could still be normalized at **EPIC F intake** rather than defaulted in the batch.

> **🔎 Org validation (IBXDEV01, 2026‑06‑26):**
> - **NpiType** picklist = `Individual` / `Organization` → `'Individual'` is valid ✓. **IsActive** required boolean ✓. **EffectiveFrom/EffectiveTo** = date, **nullable** → leaving `hcpEffectiveFrom`/`hcpEffectiveTo` null is allowed (OQ‑E20‑3b).
> - **Identifier**: `PRM_Type__c` is a **required picklist** incl. **`CAQH`** (also EIN, Document, NABP, BSPA, MCRE, HR); `IdValue` nullable; `Name` **required**; `ParentRecordId` accepts **Account** → `caqhNumber → {type:'CAQH', name/IdValue:caqhNumber}` is feasible (OQ‑E20‑5).
> - **⚠ HealthcareProviderTaxonomy has NO `ProviderType`** — the field is **`PRM_ProviderType__c` (a lookup/reference)** and `Name` is **required**. So `practitionerType` ("Physician") cannot populate it as a string; it needs a `ProviderType` record Id (resolution) or another source (OQ‑E20‑4). *(This also corrects E02 §6, which lists a non‑existent `ProviderType`.)*
> - **Correlation fields all valid:** `Account.HealthCloudGA__SourceSystemId__c` (NPI), `IndividualApplication.AccountId` (→ Account), `PRM_AsyncJobRecords__c.PRM_CaseManager__c` (→ IndividualApplication, rel **`PRM_CaseManager__r`**) → the §7 `start()` traversal compiles.

### 4.1 `flow` (application/process name) vs branch (`formType`) — **✅ clarified**

Two **distinct** concepts (previously conflated):

- **`flow` = the application / process name** — it comes from the **Async Job record** (`PRM_AsyncJob__c.PRM_ProcessName__c`, e.g. `Practitioner Creation`), **not** IBC/Delegated. The batch reads it once in `start()` and passes the same `flow` to every service.
- **Branch (IBC vs Delegated) = per‑practitioner `formType`** (analogous to creationType). It is carried on **each practitioner node** and drives E2's internal IBC/Delegated branching **and** the gating of the Delegated‑only services (E6 now; E7/E10/E11 later). Because `formType` varies **per practitioner within one message** (the sample has `AmeriHealth - CAQH` and `IBC` together), the branch is evaluated **per node**, never per chunk.

> **OQ‑E20‑2 (narrowed):** confirm the `formType` value → branch mapping. Source values seen: `IBC`, `AmeriHealth - CAQH`, `AmeriHealth - Universal` → working assumption **`IBC` → IBC; `AmeriHealth - *` → Delegated**.

---

## 5. Idempotency, DML & governor

- **Idempotency is delegated to E2** — `upsert` by `PRM_RecordKey__c` (NPI‑anchored) + the `Npi` pre‑check. A step **Retry** re‑runs the whole batch; re‑processing the same practitioners produces no duplicates (E2 §2). The batch itself holds no creation logic.
- **DML:** the batch does **no business DML** — only `PRM_AsyncOrchestrator.statusUpdate`/`logFailure`. All record creation is E2's bulk DML.
- **Governor:** the **correlation query runs once in `start()`** (1 SOQL over the Job's Case Manager rows). Each `execute` chunk then consumes only what **E2** uses internally (E2 ≈ 2 SOQL + 4 bulk DML) — **no per‑chunk lookup**. With `PRM_BatchSize__c = 1`, each `execute` handles one practitioner — safe, but see the recommendation below.
- **`start` reads the JSON once** (F‑18); `flow` is held in a `Stateful` member; the correlated practitioner nodes are returned as the iterable (each node is a serializable `Map`).

> **[RECOMMENDATION] Batch size.** Seed config is `BatchSize = 1` (Epic C C1, to be LDV‑tuned). E2 is **bulk‑capable**, so once governor headroom is measured, raise `PRM_BatchSize__c` so each `execute` hands E2 a **chunk** of practitioners (fewer transactions, same 4 bulk DML). Keep `=1` only until load‑tested.

---

## 6. Failure semantics (F‑15a)

- Each service should **throw** (or return `success=false`) on failure. The batch sets a `Stateful` `anyFailure` flag (+ first error) and, on exception, calls `PRM_AsyncOrchestrator.logFailure(stepDetail, e, payload)` → DLQ row linked to the **step‑detail** (no `PRM_CaseManager__c`, per C3).
- `finish()` → `statusUpdate(stepDetailId, anyFailure ? 'Failed' : 'Completed')` **then** `findNextJob(jobId)`. A `Failed` step halts the chain (job `Failed`, no notification).
- **⚠ No full‑chunk rollback (supersedes the earlier savepoint idea).** Because **E16's CDM manifest must record `*Exception__c` flags on failure**, the batch does **not** roll back the chunk on a service failure: it captures per‑type success/failure, aggregates **CMA for what was created**, **always writes the CDM** (created + exception flags), **then** sets the step status. Partial writes persist; **idempotent retry** re‑runs safely (service upserts + CMA pre‑check + CDM update‑by‑Case‑Manager). *(If E2 itself fails, E5/E6/CMA are skipped — the graph is incomplete — but the CDM still records the exception flags.)*

---

## 7. Reference skeleton (illustrative — not final)

> Depends on `PRM_PractitionerService` (E2), `PRM_LicenseService` (E5), `PRM_EducationService` (E6), `PRM_AsyncOrchestrator` (C3 + the §2.1 constructor‑arg `invokeJob` change), and the Epic A objects. Correlation uses **NPI** (§3). `flow` = the Job's process name (§4.1); branch = per‑node `formType`. Transform gaps (§4) are marked. **No interface, no new field** — context is a constructor parameter (§2.1). E5/E6 are the **rule‑aligned** versions (batch injects `practitionerId`/`healthcareProviderId`; services do no SOQL).

```apex
public with sharing class PRM_PractitionerBatch
        implements Database.Batchable<Object>, Database.Stateful {

    // ── context passed by PRM_AsyncOrchestrator.invokeJob (constructor params — §2.1) ──
    private final Id jobId;
    private final Id stepDetailId;
    public PRM_PractitionerBatch(Id jobId, Id stepDetailId) {
        this.jobId = jobId;
        this.stepDetailId = stepDetailId;
    }

    // ── stateful state ──
    private String flow;                         // application/process name (PRM_AsyncJob__c.PRM_ProcessName__c) — §4.1
    private Boolean anyFailure = false;
    private String  firstError;

    // 1) start: flow = the Job's process name; read JSON once; correlate CM -> Account/Contact/NPI (§3);
    //    stamp accountId/practitionerId/caseManagerId on each node; return the iterable (chunked by BatchSize)
    public Iterable<Object> start(Database.BatchableContext bc) {
        PRM_AsyncJob__c job = [SELECT Id, PRM_ProcessName__c FROM PRM_AsyncJob__c WHERE Id = :jobId WITH USER_MODE];
        this.flow = job.PRM_ProcessName__c;                                             // application name (NOT IBC/Delegated)

        Map<String, Object> payload =
            (Map<String, Object>) new PRM_AsyncOrchestrator().jsonFileParser(jobId);    // F-18: read once
        List<Object> nodes = (List<Object>) payload.get('practitioners');

        // correlate by NPI: CM -> Account Id + PersonContactId + NPI (ONE query — §3)
        Map<String, Map<String, Id>> ctxByNpi = new Map<String, Map<String, Id>>();
        for (PRM_AsyncJobRecords__c r : [
                SELECT PRM_CaseManager__c, PRM_CaseManager__r.AccountId,
                       PRM_CaseManager__r.Account.PersonContactId,
                       PRM_CaseManager__r.Account.HealthCloudGA__SourceSystemId__c
                FROM PRM_AsyncJobRecords__c WHERE PRM_AsyncJob__c = :jobId WITH USER_MODE]) {
            String npi = r.PRM_CaseManager__r.Account.HealthCloudGA__SourceSystemId__c;
            if (npi != null) ctxByNpi.put(npi, new Map<String, Id>{
                'accountId'      => r.PRM_CaseManager__r.AccountId,
                'practitionerId' => r.PRM_CaseManager__r.Account.PersonContactId,   // PersonContactId (E5/E6 ContactId)
                'caseManagerId'  => r.PRM_CaseManager__c });
        }

        List<Object> workItems = new List<Object>();
        if (nodes != null) {
            for (Object o : nodes) {
                Map<String, Object> node = (Map<String, Object>) o;
                Map<String, Id> ctx = ctxByNpi.get((String) node.get('individualNpi'));
                if (ctx == null) continue;                                   // correlation miss (OQ-E20-1)
                node.put('accountId', ctx.get('accountId'));
                node.put('practitionerId', ctx.get('practitionerId'));
                node.put('caseManagerId', ctx.get('caseManagerId'));
                workItems.add(node);
            }
        }

        // reference-data resolution is the BATCH's job (rule): resolve E6 degree/institution NAME -> Id
        // once for the whole job and stamp the resolved Ids onto each education row (OQ-E20-10).
        // (educationLevel is already in the source.)
        resolveEducationRefs(workItems);

        return workItems;                                                    // chunked by PRM_BatchSize__c
    }

    // resolve degree/institution names -> Ids (bulk, once) and inject into each education row
    private void resolveEducationRefs(List<Object> workItems) {
        Set<String> degreeCodes = new Set<String>();        // PRM_Degree__c matched by PRM_DegreeCode__c
        Set<String> institutionNames = new Set<String>();   // PRM_Institution__c matched by Name
        for (Object o : workItems) {
            Map<String, Object> n = (Map<String, Object>) o;
            if (n.get('education') == null) continue;
            for (Object eo : (List<Object>) n.get('education')) {
                Map<String, Object> e = (Map<String, Object>) eo;
                if (e.get('degree') != null)      degreeCodes.add((String) e.get('degree'));       // source 'degree' = degree code
                if (e.get('institution') != null) institutionNames.add((String) e.get('institution'));
            }
        }
        Map<String, Id> degreeIdByCode      = idByField(PRM_Degree__c.SObjectType,      'PRM_DegreeCode__c', degreeCodes);
        Map<String, Id> institutionIdByName = idByField(PRM_Institution__c.SObjectType, 'Name',              institutionNames);
        for (Object o : workItems) {
            Map<String, Object> n = (Map<String, Object>) o;
            if (n.get('education') == null) continue;
            for (Object eo : (List<Object>) n.get('education')) {
                Map<String, Object> e = (Map<String, Object>) eo;
                e.put('degreeId', degreeIdByCode.get((String) e.get('degree')));        // unmatched -> null (no create — decided)
                e.put('institutionId', institutionIdByName.get((String) e.get('institution')));
            }
        }
    }

    // 2) execute: per chunk -> E2 -> E5 -> E6 -> E19 (CMA, aggregated) -> E16 (CDM manifest, always)
    public void execute(Database.BatchableContext bc, List<Object> scope) {
        try {
            Map<Id, Id> cmByAccount = new Map<Id, Id>();                 // accountId -> caseManagerId (CMA/CDM)
            for (Object o : scope) { Map<String, Object> n = (Map<String, Object>) o;
                cmByAccount.put((Id) n.get('accountId'), (Id) n.get('caseManagerId')); }

            List<Object> cmaRequests = new List<Object>();              // E19 — aggregated association requests
            Map<Id, Set<String>> created = new Map<Id, Set<String>>();  // E16 — flags to set TRUE per account
            Map<Id, Set<String>> failedTypes = new Map<Id, Set<String>>(); // E16 — *Exception__c per account

            // E2 — practitioner core (always)
            List<Object> e2 = new List<Object>();
            for (Object o : scope) e2.add(toE2Practitioner((Map<String, Object>) o));
            Map<String, Object> e2Resp = new PRM_PractitionerService().execute(
                new Map<String, Object>{ 'flow' => flow, 'practitioners' => e2 });
            if (failed(e2Resp)) {                                       // E2 failed -> graph incomplete; skip E5/E6/CMA
                recordFailure(e2Resp);
                markTypes(failedTypes, cmByAccount.keySet(),
                    new Set<String>{ 'HealthcareProvider','HealthcareProviderNpi','Identifier','Taxonomy' });
                writeCdm(scope, cmByAccount, created, failedTypes);     // E16 still records the exception
                return;
            }
            Map<Id, Id> hcpByAccount = hcpFromResponse(e2Resp);
            collectE2(e2Resp, cmByAccount, cmaRequests, created);       // CMA: Identifier + Taxonomy; CDM created flags

            // E5 — BusinessLicense (BOTH; gated licenses[])
            List<Object> e5 = new List<Object>();
            for (Object o : scope) { Map<String, Object> n = (Map<String, Object>) o;
                if (hasItems(n.get('licenses'))) e5.add(toE5Practitioner(n)); }
            if (!e5.isEmpty()) {
                Map<String, Object> r = new PRM_LicenseService().execute(
                    new Map<String, Object>{ 'flow' => flow, 'practitioners' => e5 });
                if (failed(r)) { recordFailure(r); markTypes(failedTypes, accountsOf(e5), new Set<String>{ 'BusinessLicense' }); }
                else collectE5(r, cmByAccount, cmaRequests, created);   // CMA: Business_License; CDM flag
            }

            // E6 — PersonEducation (DELEGATED; gated education[]); needs HCP. NO CMA record type.
            List<Object> e6 = new List<Object>();
            for (Object o : scope) { Map<String, Object> n = (Map<String, Object>) o;
                if (isDelegated(n) && hasItems(n.get('education'))) e6.add(toE6Practitioner(n, hcpByAccount)); }
            if (!e6.isEmpty()) {
                Map<String, Object> r = new PRM_EducationService().execute(
                    new Map<String, Object>{ 'flow' => flow, 'practitioners' => e6 });
                if (failed(r)) { recordFailure(r); markTypes(failedTypes, accountsOf(e6), new Set<String>{ 'PersonEducation' }); }
                else markTypes(created, accountsOf(e6), new Set<String>{ 'PersonEducation' });
            }

            // E7 / E8 / E10 / E11 — DEFERRED (no source data); wire here following the same pattern.

            // E19 — CMA: ONE call with all aggregated requests (Practitioner CMA already by E1). Pre-check = idempotent.
            if (!cmaRequests.isEmpty()) {
                Map<String, Object> r = new PRM_CMAService().execute(new Map<String, Object>{ 'associations' => cmaRequests });
                if (failed(r)) recordFailure(r);
            }

            // E16 — CDM manifest: ALWAYS one per Case Manager (created + exception flags). No rollback (§6).
            writeCdm(scope, cmByAccount, created, failedTypes);

        } catch (Exception e) {
            anyFailure = true; firstError = e.getMessage();
            new PRM_AsyncOrchestrator().logFailure(stepDetailRef(), e, null);
        }
    }

    // 3) finish: status FIRST, then chain (F-19)
    public void finish(Database.BatchableContext bc) {
        PRM_AsyncOrchestrator orch = new PRM_AsyncOrchestrator();
        orch.statusUpdate(stepDetailId, anyFailure ? 'Failed' : 'Completed', firstError);
        orch.findNextJob(jobId);
    }

    // ── per-service transforms (pure; read batch-injected Ids) ──
    private Map<String, Object> toE2Practitioner(Map<String, Object> src) {
        return new Map<String, Object>{
            'practitionerInfo' => new Map<String, Object>{
                'id'            => (Id) src.get('accountId'),
                'npi'           => src.get('individualNpi'),
                'npiType'       => 'Individual',                  // OQ-E20-3 (type literal)
                'firstName'     => src.get('firstName'),
                'lastName'      => src.get('lastName'),
                'isActive'      => true,                          // OQ-E20-3 default
                'effectiveFrom' => src.get('effectiveDate'),      // source field is 'effectiveDate' (§4.1)
                'effectiveTo'   => null,                          // OQ-E20-3
                'formType'      => src.get('formType')            // IBC vs Delegated branch (§4.1)
            },
            'caseManagerId' => (Id) src.get('caseManagerId'),
            'taxonomies'    => buildTaxonomies(src),              // careTaxonomyId resolution: batch/intake (OQ-E20-4)
            'identifiers'   => new List<Object>()                 // caqh -> Identifier deferred (OQ-E20-5)
        };
    }

    private Map<String, Object> toE5Practitioner(Map<String, Object> src) {
        return new Map<String, Object>{
            'practitionerInfo' => new Map<String, Object>{ 'id' => (Id) src.get('accountId'), 'npi' => src.get('individualNpi') },
            'practitionerId'   => (Id) src.get('practitionerId'),   // ContactId (rule-injected)
            'caseManagerId'    => (Id) src.get('caseManagerId'),
            'businessLicenses' => src.get('licenses')              // ⚠ licenseType missing in source (E5 key) — OQ-E20-9
        };
    }

    private Map<String, Object> toE6Practitioner(Map<String, Object> src, Map<Id, Id> hcpByAccount) {
        return new Map<String, Object>{
            'practitionerInfo'     => new Map<String, Object>{ 'id' => (Id) src.get('accountId'), 'npi' => src.get('individualNpi') },
            'practitionerId'       => (Id) src.get('practitionerId'),         // ContactId (rule-injected)
            'caseManagerId'        => (Id) src.get('caseManagerId'),
            'healthcareProviderId' => hcpByAccount.get((Id) src.get('accountId')),   // from E2 output (rule-injected)
            'education'            => src.get('education')         // enriched in start() with degreeId/institutionId (+ source educationLevel) — OQ-E20-10
        };
    }

    private List<Object> buildTaxonomies(Map<String, Object> src) {
        List<Object> taxes = new List<Object>();
        if (src.get('taxonomies') != null) {
            for (Object o : (List<Object>) src.get('taxonomies')) {
                Map<String, Object> t = (Map<String, Object>) o;
                taxes.add(new Map<String, Object>{
                    'taxonomyCode' => t.get('careTaxonomyCode'),
                    'isPrimary'    => t.get('isPrimarySpecialty')
                    // providerType -> PRM_ProviderType__c is a LOOKUP; name required -> resolve/source (OQ-E20-4)
                });
            }
        }
        return taxes;
    }

    // ── helpers ──
    private Boolean isDelegated(Map<String, Object> node) {
        // OQ-E20-2: formType -> branch; 'IBC' = IBC, 'AmeriHealth - *' = Delegated
        return !'IBC'.equalsIgnoreCase((String) node.get('formType'));
    }
    private Boolean hasItems(Object o) { return o != null && !((List<Object>) o).isEmpty(); }
    // generic <matchField value> -> Id resolver (Institution by Name, Degree by PRM_DegreeCode__c;
    // reusable/extendable to taxonomy/infocode/etc.). Unmatched values simply have no entry (no create).
    private Map<String, Id> idByField(Schema.SObjectType sot, String matchField, Set<String> values) {
        Map<String, Id> m = new Map<String, Id>();
        if (values == null || values.isEmpty()) return m;
        String obj = sot.getDescribe().getName();
        for (SObject s : Database.query(
                'SELECT Id, ' + matchField + ' FROM ' + obj + ' WHERE ' + matchField + ' IN :values WITH USER_MODE')) {
            Object k = s.get(matchField);
            if (k != null) m.put(String.valueOf(k), (Id) s.get('Id'));
        }
        return m;
    }
    private Boolean failed(Map<String, Object> r) { return r != null && r.get('success') == false; }
    private void recordFailure(Map<String, Object> r) {
        anyFailure = true; if (firstError == null) firstError = (String) r.get('error');
    }
    private Map<Id, Id> hcpFromResponse(Map<String, Object> r) {
        Map<Id, Id> m = new Map<Id, Id>();
        if (r != null && r.get('practitioners') != null) {
            for (Object o : (List<Object>) r.get('practitioners')) {
                Map<String, Object> p = (Map<String, Object>) o;
                if (p.get('accountId') != null && p.get('healthcareProviderId') != null) {
                    m.put((Id) p.get('accountId'), (Id) p.get('healthcareProviderId'));
                }
            }
        }
        return m;
    }
    private PRM_AsyncJobDetails__c stepDetailRef() {
        return new PRM_AsyncJobDetails__c(Id = stepDetailId, PRM_AsyncJob__c = jobId, PRM_ProcessName__c = flow);
    }

    // ── E19 (CMA) aggregation + E16 (CDM) outcome tracking ──────────────────────────

    // From E2's response: CDM flags (HCP/NPI/Identifier/Taxonomy) + CMA rows (Identifier, Taxonomy).
    // Practitioner / HCP / NPI CMAs are owned by E1 — not re-created here.
    private void collectE2(Map<String, Object> resp, Map<Id, Id> cmByAccount,
                           List<Object> cmaRequests, Map<Id, Set<String>> created) {
        for (Object o : ids(resp.get('practitioners'))) {
            Map<String, Object> p = (Map<String, Object>) o;
            Id acct = (Id) p.get('accountId'); Id cm = cmByAccount.get(acct);
            markTypes(created, new Set<Id>{ acct },
                new Set<String>{ 'HealthcareProvider','HealthcareProviderNpi','Identifier','Taxonomy' });
            for (Object x : ids(p.get('identifierIds')))
                cmaRequests.add(cma(cm, 'Identifier', 'PRM_Identifier__c', (Id) x));
            for (Object x : ids(p.get('taxonomyIds')))
                cmaRequests.add(cma(cm, 'Healthcare_Provider_Taxonomy', 'PRM_HealthcareProviderTaxonomy__c', (Id) x));
        }
    }

    // From E5's response: CDM flag (BusinessLicense) + CMA rows (Business_License).
    private void collectE5(Map<String, Object> resp, Map<Id, Id> cmByAccount,
                           List<Object> cmaRequests, Map<Id, Set<String>> created) {
        for (Object o : ids(resp.get('practitioners'))) {
            Map<String, Object> p = (Map<String, Object>) o;
            Id acct = (Id) p.get('accountId'); Id cm = cmByAccount.get(acct);
            markTypes(created, new Set<Id>{ acct }, new Set<String>{ 'BusinessLicense' });
            for (Object x : ids(p.get('businessLicenseIds')))
                cmaRequests.add(cma(cm, 'Business_License', 'PRM_BusinessLicense__c', (Id) x));
        }
    }

    private Map<String, Object> cma(Id cmId, String recordType, String primaryField, Id primaryId) {
        return new Map<String, Object>{ 'caseManagerId' => cmId, 'recordType' => recordType,
            'lookups' => new Map<String, Object>{ primaryField => primaryId } };
    }

    // E16 — one call: service inits all flags FALSE, sets created->TRUE, failed->*Exception__c TRUE,
    //                 idempotently updating the CDM by Case Manager.
    private void writeCdm(List<Object> scope, Map<Id, Id> cmByAccount,
                          Map<Id, Set<String>> created, Map<Id, Set<String>> failedTypes) {
        List<Object> cdm = new List<Object>();
        for (Object o : scope) {
            Id acct = (Id) ((Map<String, Object>) o).get('accountId');
            Set<String> createdTypes = new Set<String>(orEmpty(created.get(acct)));
            createdTypes.add('PersonAccount');                              // OQ-E16-3: Person Account created by E1 at intake
            cdm.add(new Map<String, Object>{
                'caseManagerId' => cmByAccount.get(acct),
                'created' => new List<String>(createdTypes),
                'failed'  => new List<String>(orEmpty(failedTypes.get(acct)))
            });
        }
        Map<String, Object> r = new PRM_CaseDataManagerService().execute(
            new Map<String, Object>{ 'flow' => flow, 'practitioners' => cdm });
        if (failed(r)) recordFailure(r);
    }

    private void markTypes(Map<Id, Set<String>> m, Set<Id> accts, Set<String> types) {
        for (Id a : accts) { if (!m.containsKey(a)) m.put(a, new Set<String>()); m.get(a).addAll(types); }
    }
    private List<Object> ids(Object o) { return o == null ? new List<Object>() : (List<Object>) o; }
    private Set<String> orEmpty(Set<String> s) { return s == null ? new Set<String>() : s; }
    // accountId is carried on each transformed request's practitionerInfo.id (set by toE2/E5/E6Practitioner).
    private Set<Id> accountsOf(List<Object> reqs) {
        Set<Id> s = new Set<Id>();
        for (Object o : reqs) {
            Map<String, Object> info = (Map<String, Object>) ((Map<String, Object>) o).get('practitionerInfo');
            if (info != null && info.get('id') != null) s.add((Id) info.get('id'));
        }
        return s;
    }
}
```

---

## 8. Sequence (end‑to‑end)

```
EPIC F intake → PRM_AsyncOrchestrator.start(jobId)
  → createDetails (seq 1..n) → findNextJob → invokeJob(step seq 1)
      → Database.executeBatch(new PRM_PractitionerBatch(jobId, stepDetailId), BatchSize)   [§2.1 — ctor param, per-branch dispatch]
        (batch runs post-commit:)
          start()   : flow = Job.PRM_ProcessName__c; jsonFileParser once; correlate CM→Account/Contact/NPI; stamp accountId/practitionerId/caseManagerId → Iterable<nodes>
          execute() : chunk → E2 (core) → thread healthcareProviderId → E5 (gated licenses[]) → E6 (gated Delegated + education[])
                            → E19 CMA (one call: Identifier+Taxonomy from E2, Business_License from E5; Practitioner CMA already by E1)
                            → E16 CDM (always: one manifest per Case Manager; created→flags TRUE, failed→*Exception__c TRUE) → aggregate failures
          finish()  : statusUpdate(step, Completed|Failed) → findNextJob(jobId)
  → (next step seq 2: PracticeLocationAndGroupBatch …) or job Completed → notify submitter
```

---

## 9. Service wiring — E2/E5/E6 + E19/E16 now; E7/E8/E10/E11 deferred

All PractitionerBatch services run inside the **same** seq‑1 step, called **sequentially in `execute()`**, reusing prior services' in‑memory outputs (no extra queries). Gating = **data present** AND (for Delegated‑only services) **per‑node `formType` = Delegated** (§4.1). The two cross‑cutting services run **after** the record services: **E19 (CMA)** once with aggregated requests, then **E16 (CDM)** always.

| Order | Service | Branch | Needs from prior | Gated on | This iteration |
|---|---|---|---|---|---|
| 1 | **E2 `PRM_PractitionerService`** | BOTH (internal) | — | always | ✅ wired |
| 2 | **E5 `PRM_LicenseService`** | BOTH | — (accountId/Contact from E1) | `licenses[]` | ✅ wired |
| 3 | **E6 `PRM_EducationService`** | DELEGATED | **`healthcareProviderId`** (E2) | `education[]` | ✅ wired |
| 4 | E7 `PRM_BoardCertificationService` | DELEGATED | **`healthcareProviderId`** (E2) | `boardCertifications[]` | ⏸ deferred (no source data) |
| 5 | E8 `PRM_InfoCodeService` (practitioner‑grain) | BOTH | — | `infoCodes[]` | ⏸ deferred (no source data) |
| 6 | E10 `PRM_ContactService` | DELEGATED | — (accountId + Contact) | `providerInformation` | ⏸ deferred (no source data) |
| 7 | E11 `PRM_LanguageService` | DELEGATED | **`healthcareProviderId`** (E2) | `languages[]` | ⏸ deferred (no source data) |
| 8 | **E19 `PRM_CMAService`** | BOTH | **created Ids** (E2 Identifier/Taxonomy, E5 Business_License) | any CMA rows aggregated | ✅ wired |
| 9 | **E16 `PRM_CaseDataManagerService`** | BOTH | **created/failed type set** (E2/E5/E6) | always (one per Case Manager) | ✅ wired |

- **Output threading:** E2 returns per‑practitioner `{ accountId, healthcareProviderId, identifierIds, taxonomyIds, … }`; E5 returns `{ accountId, businessLicenseIds }`. The batch keys these by `accountId` and (a) injects `healthcareProviderId` into E6, (b) **aggregates CMA requests** for E19, (c) **tracks created/failed record‑types** for E16 — services do **not** re‑query (rule).
- **E19 (CMA) — one call per chunk.** The batch builds an `associations[]` of `{ caseManagerId, recordType, lookups }` from the created Ids: **Identifier** (`PRM_Identifier__c`) + **Healthcare_Provider_Taxonomy** (`PRM_HealthcareProviderTaxonomy__c`) from E2, **Business_License** (`PRM_BusinessLicense__c`) from E5, then calls `PRM_CMAService.execute()` once. E19's **existence pre‑check** (`CaseManager + RecordType + primary lookup`) makes it idempotent on retry. **Practitioner / HCP / NPI CMAs are owned by E1** — E20 does not re‑create them. E6 (PersonEducation) has **no CMA** record type.
- **E16 (CDM) — always, one manifest per Case Manager (= per practitioner, 1:1), runs last.** The batch passes **batch‑supplied created/failed outcomes** (not payload presence): for each Case Manager, the set of record‑types **actually created** (E2: HCP/NPI/Identifier/Taxonomy; E5: BusinessLicense; E6: PersonEducation; **always `PersonAccount`** — created by E1 at intake, OQ‑E16‑3) and the set that **failed**. E16 inserts/updates `PRM_CaseDataManager__c` (idempotent by existing `PRM_CaseManager__c`), initialising all required boolean flags `false`, setting created‑type flags `true` and failed‑type `*Exception__c` `true`. *(See §6: no rollback — the CDM must capture exception flags.)*
- **E16 concurrency (OQ‑E16‑1) — not an issue under 1:1.** Because Case Manager ↔ practitioner is **1:1**, each Case Manager is a **single** work‑item and can't be split across chunks → per‑practitioner iteration already guarantees E16's "one CDM per Case Manager". A chunk simply holds up to `PRM_BatchSize__c` (e.g. 10) **distinct** Case Managers, each written once. No grouping / unique constraint needed.
- **⏸ Deferred services have no source data today** — `boardCertifications` / practitioner‑grain `infoCodes` / `providerInformation` / `languages` are **absent** from `PRM_MultiPractitioner_lowvolume.json`. *(Location‑grain `selectedInfoCodes` + `networkTaxonomyRoles` + `groups` belong to **PracticeLocationAndGroupBatch (seq 2)/PLRelated/Level4**, not E20.)* Wire E7/E8/E10/E11 here when an updated JSON adds their data — feeding their created Ids into E19 and their type flags into E16 the same way.
- **E6 reference‑data resolution (OQ‑E20‑10 — RESOLVED):** `educationLevel` is now in the source; the **batch resolves the Ids** in `start()` (bulk, via the generic `idByField(...)` helper) and stamps `degreeId`/`institutionId` onto each education row before calling E6 — **`PRM_Institution__c` by `Name`**, **`PRM_Degree__c` by `PRM_DegreeCode__c`** (source `degree` = the code). **No create for unmatched values** → an unmatched code/name yields a **null Id** (leaves the E6 lookup blank and that token empty in the key).
- **E5 source gap (OQ‑E20‑9):** `licenses[]` still lacks **`licenseType`** (E5's dedupe‑key component) — supply at intake or derive before E5 can dedupe correctly.

---

## 10. Open items / clarifications

- ✅ **OQ‑E20‑1 — Correlation key — RESOLVED: use NPI** (IA→Account.`HealthCloudGA__SourceSystemId__c`), correlated in `start()` (§3).
- ✅ **OQ‑E20‑2 — `flow` vs branch — RESOLVED.** `flow` = the **application/process name** from `PRM_AsyncJob__c.PRM_ProcessName__c` (not IBC/Delegated); the **IBC‑vs‑Delegated branch is per‑practitioner `formType`** (§4.1). *(Remaining sub‑confirm: the exact `formType` value → branch mapping — working assumption `IBC` → IBC, `AmeriHealth - *` → Delegated.)*
- **OQ‑E20‑9 — E5 `licenseType` (source gap).** `licenses[]` has only `licenseNumber`/`licenseState` — `licenseType` (E5's `PRM_RecordKey__c` component + `LicenseClass`) is **absent**. Supply at intake or derive before E5 can dedupe correctly.
- ✅ **OQ‑E20‑10 — E6 degree/institution Ids + `educationLevel` — RESOLVED.** `educationLevel` is now in the source. The **batch** resolves Ids in `start()` (bulk, generic `idByField(...)`) and injects `degreeId`/`institutionId` per education row before calling E6 (per the rule): **`PRM_Institution__c` by `Name`**, **`PRM_Degree__c` by `PRM_DegreeCode__c`**. **No create for unmatched** → unmatched → null Id (decided).
- ✅ **OQ‑E20‑3 — `practitionerInfo` defaults — RESOLVED (batch‑filled):** `npiType = 'Individual'` (literal), `isActive = true`, `effectiveTo = null`, `effectiveFrom` ← the source **`effectiveDate`**.
- **OQ‑E20‑3b — HCP NPI effective dates.** `hcpEffectiveFrom`/`hcpEffectiveTo` are not in the source. ✓ **Org:** `HealthcareProviderNpi.EffectiveFrom/EffectiveTo` are **nullable**, so leaving them null is safe. *(Decision: mirror `effectiveFrom` vs leave null.)*
- **OQ‑E20‑4 — Taxonomy `providerType` / `name`.** ⚠ **Org:** there is **no `ProviderType`** — the field is **`PRM_ProviderType__c` (a lookup)** and `Name` is **required**. `practitionerType` ("Physician") is a label, not an Id → decide how `PRM_ProviderType__c` is populated (resolve to a `ProviderType` Id, or leave null) and what `Name` is set to. **Also correct E02 §6** (it lists a non‑existent `ProviderType`).
- **OQ‑E20‑5 — Identifiers.** ✓ **Org:** `Identifier.PRM_Type__c` includes **`CAQH`**; `ParentRecordId` accepts **Account**; `Name` is **required**. Confirm whether `caqhNumber` → an `Identifier {type:'CAQH'}` (feasible) and that E2 sets the required `Name`.
- **OQ‑E20‑6 — Context via constructor (§2.1).** Confirm the Epic C `invokeJob` change: construct the batch with `new <Batch>(jobId, stepDetailId)` (a small `switch`/`newBatch` over the MDT class names) instead of the no‑arg `Type.forName().newInstance()`. **No new field, no interface.**
- **OQ‑E20‑7 — E2 failure signalling.** Confirm E2 throws (or returns `success=false`) on failure so the batch can set the step `Failed` (the skeleton handles both).
- **OQ‑E20‑8 — Target org / `PRM_BatchSize__c`.** Confirm the org and the (re‑tuned) batch size before LDV. **Governor:** E19 adds ~1 SOQL (pre‑check) + 1 DML; E16 adds ~1 SOQL + 1 DML — both **per chunk** (bulk across the chunk), so they're flat regardless of practitioner count.
- ✅ **OQ‑E20‑11 — E19 (CMA) wiring — RESOLVED.** Batch aggregates `associations[]` from created Ids — **Identifier + Taxonomy (E2)**, **Business_License (E5)** — and calls `PRM_CMAService` **once per chunk**; idempotent via E19's existence pre‑check. **Practitioner CMA owned by E1** (not re‑created). E6 has no CMA. *(Prereq: `PRM_AsyncJob_Access` needs CRUD on `PRM_CaseManagerAssociation__c` + FLS on its lookups — E19 §3.)*
- ✅ **OQ‑E20‑12 — E16 (CDM) wiring — RESOLVED.** Batch supplies **created/failed outcomes** (option‑a, not payload presence); E16 runs **last, always** (one manifest per Case Manager), initialising flags `false`, setting created→`true` and failed→`*Exception__c true`; idempotent by existing `PRM_CaseManager__c`. *(Prereq: `PRM_AsyncJob_Access` needs CRUD/FLS on `PRM_CaseDataManager__c` + its flags.)*
- ✅ **OQ‑E20‑13 — Failure policy — RESOLVED: no rollback** (supersedes the earlier savepoint idea). Partial writes persist; CMA covers what was created; CDM records exception flags; **idempotent retry** re‑runs safely (§6).
- ✅ **OQ‑E16‑1 — E16 concurrency — RESOLVED (1:1 model).** Case Manager ↔ practitioner is **1:1** (confirmed), so each CM is a single work‑item that can't be split across chunks → per‑practitioner iteration already yields one CDM per Case Manager. **No grouping, no unique constraint.** `PRM_BatchSize__c` up to **10** → up to 10 Case Managers per chunk.
- ✅ **OQ‑E16‑3 — `PersonAccount` token — RESOLVED in the batch.** `writeCdm()` **always adds `PersonAccount`** to each practitioner's `created[]` (the Person Account is guaranteed by **E1 at intake**), so `PRM_PersonAccount__c` is set `true` (§7).
- **CL — E2/E5 response shape.** E2 must return per‑practitioner `{ accountId, healthcareProviderId, identifierIds[], taxonomyIds[] }` and E5 `{ accountId, businessLicenseIds[] }` (correlated by `accountId`) so the batch can build CMA requests and CDM flags. Confirm/extend the service response contracts.
- **CL — E16 input contract.** E16 must accept the batch's `{ caseManagerId, created[], failed[] }` per practitioner (record‑type tokens) rather than deriving presence from the payload. Confirm/extend E16 §contract.

*(Resolved upstream: scope = whole job per step; halt‑on‑failure F‑15a; JSON read once in `start` F‑18; `finish` order F‑19; idempotency via E2 upserts.)*

---

## 11. Recommendations (summary)

1. **Context via constructor (§2.1).** `PRM_PractitionerBatch(Id jobId, Id stepDetailId)`; `invokeJob` constructs it with args via a small per‑class `newBatch(...)` switch (replacing no‑arg `Type.forName().newInstance()`). **No interface, no new field, no DB resolution.** *(Highest priority — required Epic C change.)*
2. **`flow` = process name; branch = per‑node `formType`.** Read `flow` from `PRM_AsyncJob__c.PRM_ProcessName__c`; gate Delegated‑only services (E6 now) on each node's `formType`. *(§4.1.)*
3. **The batch resolves & injects all context + reference data (rule).** Correlate by NPI → inject `accountId` + **`practitionerId` (PersonContactId)** + `caseManagerId`; thread E2's `healthcareProviderId` into E6; **resolve E6 Ids in `start()`** via the generic **`idByField(SObjectType, matchField, values)`** helper — `PRM_Institution__c` by `Name`, `PRM_Degree__c` by `PRM_DegreeCode__c` (no create for unmatched; reusable for taxonomy/infocode — consider promoting to a shared `PRM_*Selector`/utility). Services do **no SOQL**. *(§3/§7.)*
4. **Keep the batch a thin orchestrator** — parse, correlate, transform, invoke (E2→E5→E6→E19→E16), chain. **No business DML** in the batch (all writes in the services). *(§5.)*
4a. **Run E19 (CMA) then E16 (CDM) after the record services.** E19 once per chunk with aggregated created Ids (Identifier/Taxonomy from E2, Business_License from E5; Practitioner CMA owned by E1); E16 always, last, fed **batch‑supplied created/failed outcomes** (option‑a). Both idempotent (E19 pre‑check; E16 by existing `PRM_CaseManager__c`). *(§9.)*
5. **Normalize the source payload at intake (EPIC F)** — fill the gaps the services need (E5 `licenseType`; E6 degree/institution Ids + `educationLevel`; taxonomy `careTaxonomyId`/`PRM_ProviderType__c`; identifiers) — so the batch transform stays a near 1:1 mapping and the services don't default silently. *(§4 / OQ‑E20‑4/9/10.)*
6. **Iterate the JSON practitioners** — `Database.Batchable<Object>`; `start()` returns an `Iterable<Object>` of correlated practitioner nodes, chunked by `PRM_BatchSize__c`; `execute()` invokes E2→E5→E6 with the chunk. The per‑branch `executeBatch` (§2.1) makes the non‑SObject iterable safe. *(§1/§2/§7.)*
7. **Raise `PRM_BatchSize__c` after LDV** so the services receive real chunks (all bulk‑built); keep `=1` only until measured — note ~6+ bulk DML/chunk once E5/E6 are added. *(§5.)*
8. **Build/keep the §9 seams** for E7/E8/E10/E11 so adding them when the source JSON includes their data is additive (feed their created Ids into E19 and type flags into E16), not a rewrite.
9. **Idempotent retry, no rollback** — rely on each service's `PRM_RecordKey__c` upserts + E19's pre‑check + E16's update‑by‑Case‑Manager; the whole step re‑runs safely on Retry (no compensating logic in the batch). **Do not** wrap the chunk in a savepoint — the CDM must persist its `*Exception__c` flags on partial failure. *(§6.)*
10. **Confirm prerequisite access + response contracts** — `PRM_AsyncJob_Access` CRUD/FLS for `PRM_CaseManagerAssociation__c` (E19) and `PRM_CaseDataManager__c` (E16); E2/E5 must return per‑practitioner created Ids correlated by `accountId`; E16 must accept `{ caseManagerId, created[], failed[] }`. *(§10.)*

---

## 12. Definition of Done (this iteration — E2 / E5 / E6 / E19 / E16)

- [ ] `PRM_PractitionerBatch implements Database.Batchable<Object>, Database.Stateful` with constructor `(Id jobId, Id stepDetailId)` (**no** interface, **no** new field, **no** `resolveContext`).
- [ ] Epic C: `invokeJob` constructs the batch with `new <Batch>(jobId, stepDetailId)` (per‑class `newBatch` switch) instead of no‑arg `newInstance()` (OQ‑E20‑6).
- [ ] `start()`: `flow` = `PRM_AsyncJob__c.PRM_ProcessName__c`; reads the Job JSON once; **correlates CM→Account/Contact/NPI in one query**; stamps `accountId`/`practitionerId`/`caseManagerId` on each node; returns an **`Iterable<Object>`** (chunked by `PRM_BatchSize__c`).
- [ ] `execute(List<Object> scope)` invokes **E2**, threads `healthcareProviderId`, then **E5** (gated `licenses[]`) and **E6** (gated Delegated + `education[]`), then **E19 (CMA)** once and **E16 (CDM)** always; aggregates failures.
- [ ] **E19 (CMA):** batch aggregates `associations[]` from created Ids — Identifier + Taxonomy (E2), Business_License (E5) — one `PRM_CMAService` call; Practitioner CMA skipped (owned by E1); idempotent via pre‑check (OQ‑E20‑11).
- [ ] **E16 (CDM):** batch passes per‑practitioner `{ caseManagerId, created[], failed[] }` (always incl. the `PersonAccount` token — OQ‑E16‑3); E16 runs last, one manifest per Case Manager (= per practitioner, 1:1), flags `false`→`true` for created and `*Exception__c true` for failed; idempotent by existing `PRM_CaseManager__c` (OQ‑E20‑12). No grouping needed (1:1 — OQ‑E16‑1).
- [ ] **No rollback** of the chunk on service failure; partial writes persist; CDM records exception flags; idempotent retry (OQ‑E20‑13 / §6).
- [ ] Branch (IBC/Delegated) read from each node's **`formType`**; `effectiveFrom` mapped from **`effectiveDate`**.
- [ ] `finish()` sets step status **then** `findNextJob` (F‑19); any service failure → step `Failed` + DLQ (halt).
- [ ] Batch resolves E6 Ids in `start()` (generic `idByField`): `PRM_Institution__c` by `Name`, `PRM_Degree__c` by `PRM_DegreeCode__c` (no create); source `educationLevel` (OQ‑E20‑10); E5 `licenseType` supplied (OQ‑E20‑9); taxonomy resolution (OQ‑E20‑4).
- [ ] E2/E5 return per‑practitioner created Ids correlated by `accountId`; E16 accepts the `{caseManagerId, created[], failed[]}` contract (§10 CLs).
- [ ] `PRM_AsyncJob_Access` updated: CRUD/FLS on `PRM_CaseManagerAssociation__c` (E19) and `PRM_CaseDataManager__c` + flags (E16).
- [ ] Idempotent: re‑running the step creates no duplicates (service upserts + E19 pre‑check + E16 update‑by‑Case‑Manager).
- [ ] `<Class>Test` ≥ 85% incl. a multi‑Case‑Manager job (mixed `formType`), a correlation‑miss path, E5/E6 gating, a CMA aggregation + CDM created/failed‑flag path, and a failure→halt path (stub the services).
- [ ] Field/relationship API names validated against the org (`Account.PersonContactId`, `Account.HealthCloudGA__SourceSystemId__c`, `IndividualApplication.AccountId`).
- [ ] E7/E8/E10/E11 seams left in `execute()` for when the source JSON adds their data — feeding E19/E16 the same way (§9).
