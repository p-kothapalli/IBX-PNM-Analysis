# High Level Technical Design Document
# PDM Manual Update - Practitioner: Full IP-to-Apex Migration & Large Data Optimization

**Document Version:** 1.0
**Date:** 2026-04-23
**Author:** Salesforce Architecture
**Status:** Design — Pending Approval
**Stakeholder Direction:** "Not sure keeping the IPs will work, we have to move away from the IPs and have them in batches / future processing and use the framework that we are building for practitioner creation. Re-check and redesign in detail on what will take it to move it to Apex from IPs."

---

## Section 1: Executive Summary

The PDM Manual Update - Practitioner OmniScript currently drives a chain of Integration Procedures that mirror the structural shape of the Practitioner Creation chain: a container IP invokes child IPs synchronously, culminating in heavy taxonomy-network, payer-network, and IFC-record DML. Because the update flow must read the existing state of each practitioner's network graph in order to compute a delta (records to upsert versus records to deactivate), every execute step pays a SOQL cost *before* any DML runs. This is the defining difference between the update flow and the create flow, and it is why the IP-based approach — even with the Queueable refactoring documented in `TDD_PractitionerCreation.txt` — cannot scale. A three-location practitioner with 54 network records becomes 54 pre-DML SOQL lookups plus 54 upserts plus deactivation DML; the total per-transaction operation count exceeds both the synchronous SOQL limit of 100 and the Queueable-elevated limit of 200 well before the DML phase begins.

The Queueable IP refactor described in the superseded Practitioner Creation TDD (TX1 synchronous, TX2 and TX3 Queueable) was formally rejected during gap analysis for three reasons that apply with equal force here: the TX2→TX3 Queueable chain cannot be integration-tested inside the standard sandbox test harness (the 1-level chaining limit silently suppresses TX3), the OmniStudio `rollbackOnError = true` default leaves the flow without partial-success DML (catastrophic for update mode, where a rollback hides stale data behind a successful-looking transaction), and the TX1 synchronous leg continues to block the UI for 5+ minute waits on large practitioners. None of these problems are fixable inside an IP-bound or Queueable-bound architecture.

The full migration to Batch Apex resolves all three problems simultaneously. Batch Apex grants a fresh set of governor limits on every `execute()` call, supports up to 50 million records via `Database.QueryLocator`, provides first-class partial-success DML through `Database.upsert(records, externalIdField, false)`, and preserves cross-execute state through `Database.Stateful`. The orchestration layer — Platform Event publish from the trimmed IP, subscriber trigger, orchestrator, three chained batches — is already being built for Practitioner Creation.

This document designs the PDM-specific layer on top of that framework. The Practitioner Creation batch classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) are extended — not duplicated — with a `mode` parameter that carries `INSERT` or `UPSERT` through the orchestrator. In `UPSERT` mode each batch runs a delta query in `execute()`, separates the scope into an upsert set and a deactivation set, and issues `Database.upsert(records, externalIdField, false)` plus `Database.update(deactivations, false)`. The Platform Event `NetworkCreationRequested__e`, the orchestrator, the `PRM_FailedRecordStaging__c` object, the `PRM_ExceptionLogEvent__e` rollback-safe logging path, and the Data Admin list views and Quick Actions are reused with zero additional effort.

The net delivery for PDM Manual Update is a trimmed IP chain (synchronous address/facility work plus Platform Event publish), three mode-extended batch classes, a small set of update-specific unit tests, and configuration metadata. The hard prerequisite is that the Practitioner Creation framework must be deployed to QA and passing integration tests before PDM development begins — otherwise there is no framework to extend.

---

## Section 2: Why IPs Cannot Handle This

### 2.1 Governor Limits Breached

The PDM Manual Update IP chain executes the same structural operations as Practitioner Creation plus a delta-computation read for every record that might need to be updated. The limits breached, in order of encounter:

- **SOQL 100 (synchronous):** The container IP runs under the synchronous-Apex SOQL limit of 100 queries. Practitioner Creation alone issues approximately 280 operations per transaction for a three-location practitioner (`PRM_NetworkCreation_Issue_Summary.md`, root cause section). PDM Manual Update adds a mandatory existing-record lookup against `PRM_FacilityPractitionerTxNw__c`, `PRM_FacilityPractitionerNw__c`, and `PRM_FacilityIFC__c` for every record that may need upsert or deactivation. The pre-DML SOQL cost alone exceeds 100.

- **SOQL 200 (async/Queueable):** The Queueable elevated limit is 200. The original IP3 (`PRM_CreateDelegatedHFNRecords`) already used `queueableChainableQueriesLimit = 120` and reached 45+ network records plus support queries. Adding delta lookups pushes the query count past 200 for a single practitioner with 4 or more locations. Under Queueable, the chain fails silently: no UI feedback, no retry affordance.

- **CPU 60,000 ms async:** The Queueable CPU ceiling is 60 seconds. Delta computation adds set-difference and map-building operations over the existing records plus the incoming payload. For a 5-location practitioner with 90+ network records, the delta computation alone consumes 8–12 seconds of CPU in measured benchmarks of the existing IP — on top of the 280-operation DML workload that already approached the ceiling in create mode.

- **Heap 12 MB async:** The Queueable heap limit is 12 MB. Delta computation requires holding both the incoming network payload and the existing record graph in memory. For a 5-location practitioner, the combined payload plus query result approaches 8–10 MB; header-adjusted for OmniStudio stack frames, the heap pressure exceeds 12 MB. The IP fails with `System.LimitException: Apex heap size too large`.

### 2.2 Per-Transaction Operation Count for PDM Manual Update

```
Operation class                                Creation count   Update count
-----------------------------------------------------------------------------
Pre-DML existing-record queries                    0                54-90
Taxonomy network records (9 per 3-loc)             36 ops           54 ops
Payer network records (45 per 3-loc)               180 ops          225 ops
IFC records (15 per 3-loc)                         45 ops           60 ops
Support queries, dedup, merge                      20 ops           35 ops
Deactivation DML (stale records)                   0                15-30 ops
-----------------------------------------------------------------------------
TOTAL per transaction                              ~280             ~443-494
```

The update transaction is approximately 60–75% heavier than the create transaction, which was already failing the synchronous IP in production. This cost cannot be absorbed by the Queueable ceiling.

### 2.3 OmniStudio Has No Native Partial-Success DML

OmniStudio's default IP configuration uses `rollbackOnError = true`. The runtime has no native binding to `Database.upsert(records, false)` — it issues all-or-none DML. In create mode, rollback is tolerable: the practitioner is simply not created and the user retries. In update mode, rollback is catastrophic: the flow appears to complete (from the user's perspective the spinner stops), but the system-of-record state is unchanged. Stale data — the prior network graph — looks valid in every report, related list, and downstream API. The update failure is silent and data-destroying because it is data-preserving of the wrong data.

There is no OmniStudio configuration that makes IP DML partial-success for update mode. The only native approach is to push the DML into Apex.

### 2.4 Queueable Chaining Cannot Be Integration-Tested

Salesforce Developer and Sandbox environments enforce a 1-level Queueable chaining limit during `Test.startTest()/stopTest()` execution (`TDD_Gap_Analysis.md` Issue 4). The TX2→TX3 handoff described in `TDD_PractitionerCreation.txt` section 5.1 will not fire inside a standard unit test. This means:

- The TX3 code path receives zero unit test coverage.
- The sandbox integration appears green when only TX2 has run; TX3's absence is invisible.
- Delta computation and stale-record deactivation — the update-specific logic — would live entirely inside this untestable leg.

Shipping update-mode logic into an untestable code path is unacceptable. Batch Apex `start()/execute()/finish()` chains are fully exercised under `Test.startTest()/stopTest()` because each batch runs to completion synchronously in the test context regardless of chain depth.

### 2.5 Batch Apex Resolves Every Problem

Batch Apex provides:

- **Fresh governor limits per `execute()` call.** A batch size of 5 practitioner practice-location records per execute means each execute runs well inside the 200-SOQL, 10,000-DML-row, and 6 MB heap limits.
- **`Database.QueryLocator` supports 50,000,000 rows.** No practitioner will exhaust it.
- **`Database.Stateful` preserves counters, error lists, and status across executes.** This is how `PRM_FailedRecordStaging__c` population is aggregated and how the final `finish()` method knows whether to mark the CaseManager as `Completed` or `Failed`.
- **`Database.upsert(records, externalIdField, false)` is first-class partial success.** Every row's `SaveResult` is inspected; failures are staged to `PRM_FailedRecordStaging__c`; successes commit without touching the failed ones.
- **Chain transition in `finish()`.** `Database.executeBatch(new NextBatch(params), batchSize)` from `finish()` is the sanctioned pattern and is integration-tested routinely.

### 2.6 Constraint Comparison Table

| Constraint | Queueable IP Limit | Batch Apex Context | PDM Manual Update Need |
|---|---|---|---|
| SOQL queries per transaction | 200 | 200 per `execute()`, resets each call | 443–494 total operations, ~90 queries per execute at batch size 5 |
| CPU time per transaction | 60,000 ms | 60,000 ms per `execute()`, resets each call | ~10,000 ms per execute at batch size 5 |
| Heap size per transaction | 12 MB | 12 MB per `execute()`, resets each call | ~6 MB per execute at batch size 5 |
| DML rows per transaction | 10,000 | 10,000 per `execute()`, resets each call | 90–120 rows per execute at batch size 5 |
| Partial-success DML | Not natively available in OmniStudio IPs | `Database.upsert(records, externalIdField, false)` | Mandatory for update mode — per-row failures must not roll back valid updates |
| Testability in sandbox | TX2→TX3 chain silently suppressed under `Test.startTest()` | Batch chains run fully under `Test.startTest()` regardless of chain depth | Full delta-and-deactivate logic must be covered by unit tests |
| Maximum records processable | Bound by per-transaction governor limits | 50,000,000 rows via `QueryLocator` | Unbounded — must scale to practitioners with 20+ locations |
| Stateful counter aggregation | None — each Queueable starts fresh | `Database.Stateful` preserves state across executes | Required for final CaseManager status update and email notification |

---

## Section 3: Scope

### 3.1 OmniScript Affected

- **PDM Manual Update - Practitioner OmniScript** (the update counterpart to `PRM_DelegatedPractitionerReviewScreen`)

### 3.2 Current IP Chain Structure

The container and child IP structure mirrors `PRM_AddressLogicContainer` with update-mode variants. Derived from `TDD_PractitionerCreation.txt` section 2.1 for structural reference:

| Seq | Element | IP Key (current) | Invocation Mode | Purpose |
|---|---|---|---|---|
| 1 | PractitionerAddressCreation | `PRM_PractitionerAddressCreation` | Chainable | Upserts practitioner address records, healthcare facilities, locations, taxonomy data, provider features |
| 2 | ExistingPrimaryAddressLogic | `PRM_ExistingPrimaryPracticeLocationLogicDelg` | Chainable | Processes existing primary practice location logic — facility records, provider features (ACC, AA), practice-to-practitioner affiliations, case data manager updates |
| 3 | AddTaxNetworkLogic | `PRM_CreateDelegatedHFNRecords` | Queueable | Creates / updates delegated HFN records — taxonomy/network associations, payer networks, info-code records. **In update mode additionally needs to deactivate stale records not present in incoming payload.** |

### 3.3 Objects Read and Written

| IP Step | Reads From | Writes To (current mode) |
|---|---|---|
| IP1 (Address) | `Account`, `Contact`, `HealthcareFacility`, `PRM_Address__c`, `PRM_PracticeLocation__c`, taxonomy picklists | `PRM_Address__c`, `HealthcareFacility`, `PRM_PracticeLocation__c`, `PRM_PractitionerPracticeLocation__c`, provider feature records |
| IP2 (Existing Primary) | `PRM_PractitionerPracticeLocation__c`, `HealthcarePractitionerFacility`, `ProviderFeature__c`, `CaseManager__c` | `HealthcarePractitionerFacility`, `ProviderFeature__c`, practice-to-practitioner affiliations, `CaseManager__c` flags |
| IP3 (Delegated HFN) | `PRM_PractitionerPracticeLocation__c`, `PRM_PayerNetwork__c`, `PRM_Taxonomy__c`, `PRM_IFCCode__c` | `PRM_FacilityPractitionerTxNw__c`, `PRM_FacilityPractitionerNw__c`, `PRM_FacilityIFC__c` |

### 3.4 Out of Scope

- **Practitioner Creation flow.** That flow is being refactored under the US stories in `US_PractitionerCreation_Complete_Implementation.md`. This TDD only consumes the framework those stories deliver.
- **IP1 and IP2 internal logic.** The synchronous address/facility/location work in IP1 and IP2 stays in the IP chain. This is fast, low-SOQL, stateful UI work and does not benefit from batch migration. Only IP3's workload moves.
- **Other OmniScripts (PDM re-credentialing, PDM Practice Location Update, PDM Ancillary).** Those flows have independent IP chains and independent performance characteristics. Each must be evaluated on its own merits.
- **The Retry mechanism user story (`US #5` in `US_PractitionerCreation_Complete_Implementation.md`).** PDM benefits from it as built but does not add new retry logic in this delivery.

---

## Section 4: IP-to-Apex Migration Map

### 4.1 Mode Parameter Decision (Option A vs Option B)

**Decision: Option A — `mode` parameter on the existing Creation batch classes.**

**Trade-offs evaluated:**

- **Option A (mode parameter on shared classes):**
  - *Pro:* One framework, one orchestrator, one chain, one set of metadata. Zero class proliferation.
  - *Pro:* PDM benefits from every future enhancement to the batch framework (retry, dashboard, QC routing) automatically — no parallel maintenance.
  - *Pro:* Single test harness covers both modes through parameterized tests. The sandbox integration test plan is one plan, not two.
  - *Con:* `execute()` contains a conditional branch on `mode`. The DML block grows by approximately 40 lines (delta query + set difference + deactivation DML).
  - *Con:* A regression in one mode's code path can theoretically affect the other. Mitigated by comprehensive mode-parameterized unit tests.

- **Option B (separate `PDM_*UpdateBatch` classes):**
  - *Pro:* Perfectly clean separation. Create and update logic cannot interfere.
  - *Con:* Doubles the class count, doubles the orchestrator wiring, doubles the Platform Event handler branches, doubles the test surface.
  - *Con:* Future framework enhancements (retry, dashboard, exception handling improvements) must be applied twice and remain in sync.
  - *Con:* Contradicts the stakeholder direction to "use the framework that we are building for practitioner creation" — a separate parallel hierarchy is a new framework, not the same one.

**Rationale for Option A:** The stakeholder direction explicitly calls for reuse of the Practitioner Creation framework, not a parallel framework. The delta-query-and-deactivate logic in `execute()` is a bounded 40-line addition; it is not the kind of sprawling divergence that justifies class duplication. Option A delivers PDM in less time and guarantees that framework improvements made for any reason benefit both flows. Option A is the design of record throughout the remainder of this document.

### 4.2 Migration Map

| IP Step | Step Name | What It Does | Current Location | Migration Decision | Target Class / Method | Rationale |
|---|---|---|---|---|---|---|
| 1 | PractitionerAddressCreation | Upserts practitioner address, healthcare facility, location, taxonomy data | IP1 (chainable) | **STAYS IN IP** | `PRM_PractitionerAddressCreation` (unchanged) | Synchronous, UI-bound, low SOQL; user must see address validation results before Platform Event publish |
| 2 | ExistingPrimaryAddressLogic | Processes primary practice location logic, provider features, affiliations | IP2 (chainable) | **STAYS IN IP** | `PRM_ExistingPrimaryPracticeLocationLogicDelg` (unchanged) | Synchronous, dependent on IP1's in-memory outputs; moving it async breaks the user-facing primary-location confirmation step |
| 3a | Pre-DML existing-record query (taxonomy) | Query existing `PRM_FacilityPractitionerTxNw__c` records for this practitioner | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_TaxonomyNetworkBatch.execute()` — delta query block | SOQL-heavy; must run under per-execute governor reset |
| 3b | Taxonomy network upsert | Upsert 9+ taxonomy network records per practitioner | IP3 | **MOVES TO BATCH APEX** | `PRM_TaxonomyNetworkBatch.execute()` — upsert block, `Database.upsert(records, PRM_ExternalId__c, false)` | Heavy DML with partial-success requirement |
| 3c | Taxonomy stale-record deactivation | Deactivate taxonomy network records not in incoming payload | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_TaxonomyNetworkBatch.execute()` — deactivation block, `Database.update(deactivations, false)` | Cannot run in IP — requires partial-success DML and delta computation |
| 3d | Pre-DML existing-record query (payer network) | Query existing `PRM_FacilityPractitionerNw__c` records | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_PayerNetworkBatch.execute()` — delta query block | SOQL-heavy; must run under per-execute governor reset |
| 3e | Payer network upsert | Upsert 45+ payer network records per practitioner | IP3 | **MOVES TO BATCH APEX** | `PRM_PayerNetworkBatch.execute()` — upsert block | Heavy DML, partial-success requirement |
| 3f | Payer network stale-record deactivation | Deactivate payer network records not in incoming payload | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_PayerNetworkBatch.execute()` — deactivation block | Requires delta computation and partial-success DML |
| 3g | Pre-DML existing-record query (IFC) | Query existing `PRM_FacilityIFC__c` records | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_IFCRecordBatch.execute()` — delta query block | SOQL-heavy; must run under per-execute governor reset |
| 3h | IFC record upsert | Upsert 15+ IFC records per practitioner | IP3 | **MOVES TO BATCH APEX** | `PRM_IFCRecordBatch.execute()` — upsert block | Heavy DML, partial-success requirement |
| 3i | IFC stale-record deactivation | Deactivate IFC records not in incoming payload | IP3 (update branch) | **MOVES TO BATCH APEX** | `PRM_IFCRecordBatch.execute()` — deactivation block | Requires delta computation and partial-success DML |
| 3j | CaseManager status progression updates | Update `PRM_NetworkCreationStatus__c` through batch chain states | IP3 | **MOVES TO BATCH APEX** | Each batch's `start()` and `finish()` methods | Status transitions are driven by the batch chain, not the IP |
| 4 | Input validation & UI response assembly | Validate input payload, assemble OmniScript response | Container IP | **STAYS IN IP** | Container IP (unchanged) | Synchronous, UI-bound, zero DML |
| 5 | Publish `NetworkCreationRequested__e` | Remote Action that publishes the Platform Event with `mode = 'UPSERT'` | Container IP (new element replacing old IP3 invocation) | **STAYS IN IP** | `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` | Platform Event publish is a single DML and must be synchronous so the UI can confirm queueing |

### 4.3 Overall Split Narrative

After migration, the trimmed PDM Manual Update IP chain performs a strictly bounded synchronous workload: address validation and upsert (IP1), primary-practice-location logic and provider-feature updates (IP2), input validation, and a single Remote Action call to publish `NetworkCreationRequested__e` with `mode = 'UPSERT'`. The UI returns in under 3 seconds. All delta-heavy work — existing-record queries, taxonomy/payer-network/IFC upserts, and stale-record deactivation — runs in the three-batch chain orchestrated by `PRM_NetworkCreationOrchestrator`. The batch chain issues partial-success DML via `Database.upsert(records, externalIdField, false)` and `Database.update(deactivations, false)`, stages per-row failures to `PRM_FailedRecordStaging__c`, fires transaction-level exceptions via `PRM_ExceptionLogEvent__e` (rollback-safe), and progresses `PRM_NetworkCreationStatus__c` on CaseManager through `Queued → Processing Taxonomies → Processing Payer Networks → Processing IFC → Completed` or `Failed`. A final email notification fires from `PRM_IFCRecordBatch.finish()`.

---

## Section 5: Proposed Batch Architecture

### 5.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  PDM Manual Update - Practitioner OmniScript                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Invokes
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_AddressLogicContainer (IP, update variant)                  │
│                                                                  │
│   Seq 1: PractitionerAddressCreation         [CHAINABLE, sync]   │
│   Seq 2: ExistingPrimaryAddressLogic         [CHAINABLE, sync]   │
│   Seq 3: PublishNetworkCreationEvent         [REMOTE ACTION]     │
│           → PRM_NetworkCreationRemote.publishNetworkCreationEvent│
│           → mode = 'UPSERT'                                      │
│   Seq 4: ResponseWithMessage                 [RESPONSE]          │
│           Returns: "Processing..." in < 3 seconds                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ EventBus.publish(event)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  NetworkCreationRequested__e (Platform Event, PublishAfterCommit)│
│  Fields (reused):                                                │
│   CaseManagerId__c, PersonContactId__c, FacilityPractitionerTxNw │
│   IsActive__c, IsPending__c, EffectiveFrom__c, EffectiveTo__c    │
│   RecordsToUpdate__c, RequestId__c                               │
│  Fields (NEW for PDM):                                           │
│   Mode__c  (Text 10, values: 'INSERT' | 'UPSERT')                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ after insert trigger
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_NetworkCreationEventTrigger                                 │
│    → PRM_NetworkCreationOrchestrator.handleEvent(event)          │
│    → params.put('Mode', event.Mode__c)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ queueNetworkCreation(req)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_NetworkCreationOrchestrator                                 │
│    Status: 'Not Started' → 'Queued'                              │
│    Database.executeBatch(new PRM_TaxonomyNetworkBatch(params), 5)│
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_TaxonomyNetworkBatch (mode-extended)                        │
│    start()  → QueryLocator over PRM_PractitionerPracticeLocation │
│    execute()→ IF mode == 'INSERT': build + Database.insert       │
│                IF mode == 'UPSERT':                              │
│                  1. Query existing FacilityPractitionerTxNw      │
│                  2. Compute delta (upsert set + deactivation set)│
│                  3. Database.upsert(upserts, externalId, false)  │
│                  4. Database.update(deactivations, false)        │
│                  5. Stage per-row failures → staging object      │
│    finish() → Status 'Processing Payer Networks'; chain to next  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Database.executeBatch(new PRM_PayerNetworkBatch(params), 2)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_PayerNetworkBatch (mode-extended)                           │
│    Same pattern as TaxonomyNetworkBatch                          │
│    finish() → Status 'Processing IFC'; chain to next             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Database.executeBatch(new PRM_IFCRecordBatch(params), 5)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRM_IFCRecordBatch (mode-extended)                              │
│    Same pattern                                                  │
│    finish() → Status 'Completed' or 'Failed'                     │
│               sendNotification(success) — email to caseManager   │
│                                            .CreatedBy.Email      │
└─────────────────────────────────────────────────────────────────┘

Rollback-safe exception path (applies to every batch):
   Any uncaught Apex exception in execute()
     → PRM_ExceptionLogger.logExceptionViaEvent(...)
     → EventBus.publish(PRM_ExceptionLogEvent__e)  [PublishImmediately]
     → PRM_ExceptionLogEventTrigger
     → PRM_ExceptionLog__c record (survives rollback)

Per-row failure path (applies to every batch):
   Any Database.SaveResult with isSuccess() == false
     → Build PRM_FailedRecordStaging__c record
         TargetObject, Payload (JSON), ParentRecordId, ErrorMessage,
         StatusCode, FieldName, SourceProcess, BatchJobId, TransactionId
     → Database.insert(stagingRecords, false)
```

### 5.2 Status Progression

Identical to the Practitioner Creation framework. On `CaseManager__c.PRM_NetworkCreationStatus__c`:

`Not Started → Queued → Processing Taxonomies → Processing Payer Networks → Processing IFC → Completed`

On any catastrophic failure, transitions to `Failed` with `PRM_NetworkCreationError__c` populated.

### 5.3 Mode Propagation

The `mode` string (`'INSERT'` or `'UPSERT'`) is added as a field to `NetworkCreationRequested__e` and threaded through every stage:

1. Remote Action `publishNetworkCreationEvent()` reads `input.get('Mode')` and sets `event.Mode__c`.
2. Orchestrator `handleEvent(event)` copies `event.Mode__c` into `params.put('Mode', event.Mode__c)`.
3. `PRM_TaxonomyNetworkBatch(params)` constructor reads `(String) params.get('Mode')` into a private `mode` field.
4. `finish()` passes `'Mode'` forward when constructing the next batch's params map — the mode travels the entire chain.

---

## Section 6: Batch Class Designs

All three batch classes are the mode-extended versions of the existing Practitioner Creation batch classes. Their Creation-mode code paths remain unchanged; the update-mode branches are the additive design below.

### 6.1 `PRM_TaxonomyNetworkBatch` (Mode-Extended)

**New or Mode-Extended:** Mode-extended (Option A). The class from `PRM_NetworkCreation_BatchImplementation_Guide.md` Step 3.1 is augmented with a `mode` field and an `UPSERT` branch in `execute()`.

**`start()` SOQL Query:**

```apex
return Database.getQueryLocator([
    SELECT Id, Name,
           PRM_Address__c,
           PRM_PracticeLocation__c,
           PRM_Taxonomy1__c, PRM_Taxonomy2__c, PRM_Taxonomy3__c
    FROM PRM_PractitionerPracticeLocation__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_PersonContact__c = :personContactId
    AND (PRM_Taxonomy1__c != null
         OR PRM_Taxonomy2__c != null
         OR PRM_Taxonomy3__c != null)
]);
```

This scopes the batch to the practitioner (`personContactId`) and their CaseManager (`caseManagerId`) — identical to create mode. The scope is small (one practitioner's locations), so a batch size of 5 is sufficient.

**`execute()` Logic (UPSERT mode):**

1. Build the desired taxonomy-network records from the scope (same construction as INSERT mode).
2. Collect the external IDs of the desired records into `Set<String> desiredExternalIds`.
3. Query existing records for this scope:
   ```apex
   List<PRM_FacilityPractitionerTxNw__c> existing = [
       SELECT Id, PRM_ExternalId__c, PRM_IsActive__c
       FROM PRM_FacilityPractitionerTxNw__c
       WHERE PRM_CaseManager__c = :caseManagerId
       AND PRM_PersonContact__c = :personContactId
       AND PRM_PractitionerPracticeLocation__c IN :scopeIds
   ];
   ```
4. Compute delta: any existing record whose `PRM_ExternalId__c` is not in `desiredExternalIds` and whose `PRM_IsActive__c = true` goes onto the deactivation list (`PRM_IsActive__c = false`, `PRM_EffectiveTo__c = Date.today()`).
5. Issue partial-success upsert:
   ```apex
   Database.UpsertResult[] upsertResults =
       Database.upsert(desired, PRM_FacilityPractitionerTxNw__c.PRM_ExternalId__c, false);
   ```
6. Issue partial-success deactivation update:
   ```apex
   Database.SaveResult[] deactivateResults =
       Database.update(deactivations, false);
   ```
7. For each failure in either result list, build and insert a `PRM_FailedRecordStaging__c` record (see section 6.4 for field population).
8. Wrap the entire block in a `try/catch`. In the catch, call `PRM_ExceptionLogger.logExceptionViaEvent(...)` with `caseManagerId`, then re-throw so the batch runtime marks the execute as failed.

**`finish()` Logic:**

- If `totalErrors == 0 || totalProcessed > 0`, update CaseManager status to `'Processing Payer Networks'` and chain to `PRM_PayerNetworkBatch` with batch size 2 (preserving `mode`).
- If no records were processed successfully, update status to `'Failed'` and publish `PRM_ExceptionLogEvent__e` with the aggregated error list.

**Batch Size Recommendation: 5**

At batch size 5 the `execute()` call processes 5 practitioner-practice-location records. For each location, 3 taxonomy records are produced (one per taxonomy column). The execute issues:

- 1 SOQL query for existing taxonomy records (5 locations × up to 3 existing per location = up to 15 rows; well under the 50,000-row query limit)
- 1 upsert DML statement on up to 15 taxonomy records (well under the 10,000-DML-rows-per-execute limit)
- 1 update DML statement on the deactivation set (typically 0–5 records)
- 1 insert DML statement on the staging records list (only if there are failures)

Total per execute: 1 SOQL query, 3 DML statements, under 20 DML rows. This is a 40× safety margin against the 200-SOQL and 10,000-DML-row ceilings.

**`PRM_FailedRecordStaging__c` Population (per failed row):**

```apex
PRM_FailedRecordStaging__c staging = new PRM_FailedRecordStaging__c();
staging.PRM_Status__c = 'Pending';
staging.PRM_TargetObject__c = 'PRM_FacilityPractitionerTxNw__c';
staging.PRM_Payload__c = JSON.serialize(desired[i]);
staging.PRM_ParentRecordId__c = caseManagerId;
staging.PRM_ParentRecordObject__c = 'IndividualApplication';
staging.PRM_CaseManager__c = caseManagerId;
staging.PRM_ErrorMessage__c = upsertResults[i].getErrors()[0].getMessage();
staging.PRM_StatusCode__c = String.valueOf(upsertResults[i].getErrors()[0].getStatusCode());
staging.PRM_FieldName__c = upsertResults[i].getErrors()[0].getFields().isEmpty()
    ? null
    : String.valueOf(upsertResults[i].getErrors()[0].getFields()[0]);
staging.PRM_SourceProcess__c = 'PDM_ManualUpdate_TaxonomyNetworkBatch';
staging.PRM_SourceProcessType__c = 'Batch Apex';
staging.PRM_BatchJobId__c = String.valueOf(BC.getJobId());
staging.PRM_TransactionId__c = requestId;
staging.PRM_SeverityLevel__c = 'Error';
staging.PRM_RecordCount__c = 1;
```

---

### 6.2 `PRM_PayerNetworkBatch` (Mode-Extended)

**New or Mode-Extended:** Mode-extended. The class from `PRM_NetworkCreation_BatchImplementation_Guide.md` Step 3.2 is augmented with the same pattern.

**`start()` SOQL Query:**

```apex
return Database.getQueryLocator([
    SELECT Id, Name,
           PRM_PracticeLocation__c,
           (SELECT Id, PRM_PayerNetwork__c
            FROM PRM_PracticeLocationPayerNetworks__r)
    FROM PRM_PractitionerPracticeLocation__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_PersonContact__c = :personContactId
]);
```

**`execute()` Logic (UPSERT mode):** Same 7-step pattern as TaxonomyNetworkBatch, operating on `PRM_FacilityPractitionerNw__c`. The delta query selects existing payer-network records scoped to the same practitioner and practice-location set.

**`finish()` Logic:** Transition status to `'Processing IFC'`, chain to `PRM_IFCRecordBatch` at batch size 5, preserving `mode`.

**Batch Size Recommendation: 2**

The payer-network workload is 5× heavier than taxonomy (up to 15 payer networks per location). At batch size 2 the execute processes 2 locations × up to 15 networks = up to 30 desired rows. The execute issues:

- 1 SOQL query for existing payer-network records (up to 30 rows)
- 1 upsert DML on up to 30 rows
- 1 update DML on the deactivation set (0–10 rows)
- 1 insert DML on staging records (only on failure)

Total per execute: 1 SOQL, 3 DML, under 40 DML rows. Batch size 2 matches the Creation-mode recommendation and preserves the safety margin.

**Staging record population:** Same shape as 6.1 with `PRM_TargetObject__c = 'PRM_FacilityPractitionerNw__c'` and `PRM_SourceProcess__c = 'PDM_ManualUpdate_PayerNetworkBatch'`.

---

### 6.3 `PRM_IFCRecordBatch` (Mode-Extended)

**New or Mode-Extended:** Mode-extended. The class from `PRM_NetworkCreation_BatchImplementation_Guide.md` Step 3.3 is augmented.

**`start()` SOQL Query:**

```apex
return Database.getQueryLocator([
    SELECT Id, Name,
           PRM_PracticeLocation__c,
           PRM_PracticeLocation__r.PRM_IFCCode__c
    FROM PRM_PractitionerPracticeLocation__c
    WHERE PRM_CaseManager__c = :caseManagerId
    AND PRM_PersonContact__c = :personContactId
    AND PRM_PracticeLocation__r.PRM_IFCCode__c != null
]);
```

**`execute()` Logic (UPSERT mode):** Same 7-step pattern operating on `PRM_FacilityIFC__c`.

**`finish()` Logic:** Set final status. If `totalErrors == 0`, set status `'Completed'` and call `sendNotification(true)`. Otherwise set status `'Failed'` and call `sendNotification(false)`. Email is sent via `Messaging.SingleEmailMessage` to the CaseManager record's `CreatedBy.Email`.

**Batch Size Recommendation: 5**

IFC records are 1 per location (the location's IFC code maps to a single facility-IFC record). At batch size 5 the execute processes 5 locations × 1 IFC = 5 desired rows. Trivially within limits.

**Staging record population:** Same shape with `PRM_TargetObject__c = 'PRM_FacilityIFC__c'` and `PRM_SourceProcess__c = 'PDM_ManualUpdate_IFCRecordBatch'`.

---

### 6.4 Shared Helper: `stageFailure(result, desiredRecord, BC)`

All three batch classes call a shared static helper (added to the `PRM_TaxonomyNetworkBatch` or a new `PRM_BatchStagingHelper` utility class) to build the `PRM_FailedRecordStaging__c` record consistently. The helper signature:

```apex
public static PRM_FailedRecordStaging__c stageFailure(
    Database.Error error,
    SObject desiredRecord,
    String targetObjectApiName,
    String caseManagerId,
    String sourceProcess,
    String batchJobId,
    String requestId
);
```

The helper populates every field in section 6.1's table. Each batch collects the results of `stageFailure(...)` calls into a list and performs a single `Database.insert(stagingRecords, false)` at the end of `execute()`.

---

## Section 7: IP Simplification Plan

### 7.1 Before (Current State of PDM Manual Update IP Chain)

The current PDM container IP mirrors the Creation container with update-mode semantics. Active elements:

| Seq | Element | Type | Description |
|---|---|---|---|
| 1 | PractitionerAddressCreation | Integration Procedure Action | Chainable call to IP1 — upserts addresses, healthcare facilities, locations |
| 2 | ExistingPrimaryAddressLogic | Integration Procedure Action | Chainable call to IP2 — primary practice location logic, provider features, affiliations |
| 3 | AddTaxNetworkLogic | Integration Procedure Action | Queueable call to IP3 (`PRM_CreateDelegatedHFNRecords`) — creates/updates taxonomy network, payer network, and IFC records synchronously from the IP. **This is the element that exceeds governor limits in update mode.** |
| 4 | ResponseForIp | Response Action | Returns aggregated response JSON to the OmniScript |

Within IP3 itself (to be retired):

| Seq | Element | Type | Description |
|---|---|---|---|
| 3.1 | CB_LogicExecuteTxNetwork | Conditional Block | Taxonomy network upsert logic — hits SOQL and DML limits in update mode |
| 3.2 | CB_LogicExecuteLocNetwork | Conditional Block | Payer network upsert logic — hits SOQL and DML limits in update mode |
| 3.3 | CB_ExecuteIFCLogic | Conditional Block | IFC record upsert logic — hits SOQL and DML limits in update mode |
| 3.4 | CB_DeactivateStaleRecords | Conditional Block | Stale record deactivation — compounds the SOQL cost with additional delta queries |

### 7.2 After (Trimmed State)

Active elements in the trimmed container IP:

| Seq | Element | Type | Description |
|---|---|---|---|
| 1 | PractitionerAddressCreation | Integration Procedure Action | Unchanged — chainable call to IP1 for address/facility/location upserts |
| 2 | ExistingPrimaryAddressLogic | Integration Procedure Action | Unchanged — chainable call to IP2 for primary practice location and provider feature logic |
| 3 | PublishNetworkCreationEvent | Remote Action | **NEW — Remote Action: `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` — publishes `NetworkCreationRequested__e` with `Mode__c = 'UPSERT'`, returns immediately with Processing status.** |
| 4 | ResponseWithMessage | Response Action | Returns `{ success: true, message: "Processing...", processingStatus: "Queued" }` to the OmniScript |

Within IP3: the IP is retired entirely. All active elements (`CB_LogicExecuteTxNetwork`, `CB_LogicExecuteLocNetwork`, `CB_ExecuteIFCLogic`, `CB_DeactivateStaleRecords`) are deactivated. IP3 is not invoked from the PDM container after migration.

### 7.3 Element Count Reduction

- Container IP: 4 elements (was 4, but element 3 changes from a Queueable IP invocation to a Remote Action). Net structural reduction: 0 elements, but the compute cost shifts from "minutes-long Queueable inside the transaction" to "millisecond-scope Platform Event publish."
- IP3: all 4+ conditional blocks deactivated. IP3 itself is retired.

---

## Section 8: Reuse From Practitioner Creation

| Component | Reuse Type | Effort for PDM | Notes |
|---|---|---|---|
| `NetworkCreationRequested__e` Platform Event | Mode-Extended | S | Add one field `Mode__c` (Text 10) to carry `INSERT` or `UPSERT`. All existing fields reused as-is. |
| `NetworkCreationRequested__e.CaseManagerId__c` | Direct | 0 | Reused as-is |
| `NetworkCreationRequested__e.PersonContactId__c` | Direct | 0 | Reused as-is |
| `NetworkCreationRequested__e.FacilityPractitionerTxNw__c` | Direct | 0 | Reused as-is |
| `NetworkCreationRequested__e.IsActive__c / IsPending__c / EffectiveFrom__c / EffectiveTo__c` | Direct | 0 | Reused as-is |
| `NetworkCreationRequested__e.RecordsToUpdate__c` | Direct | 0 | Reused as-is — carries the incoming update payload |
| `NetworkCreationRequested__e.RequestId__c` | Direct | 0 | Reused as-is |
| `PRM_NetworkCreationEventTrigger` | Direct | 0 | Trigger body already delegates to `PRM_NetworkCreationOrchestrator.handleEvent(event)` which will be mode-extended |
| `PRM_NetworkCreationOrchestrator.handleEvent()` | Mode-Extended | S | Add `req.Mode = event.Mode__c`; add `Mode` to the params map passed into the first batch constructor |
| `PRM_NetworkCreationOrchestrator.queueNetworkCreation()` | Mode-Extended | S | Add `Mode` to the params map |
| `PRM_NetworkCreationOrchestrator.NetworkRequest` inner class | Mode-Extended | S | Add `@InvocableVariable public String Mode;` |
| `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` | Mode-Extended | S | Read `input.get('Mode')` and set `event.Mode__c` |
| `PRM_TaxonomyNetworkBatch` | Mode-Extended | M | Add `mode` field; add UPSERT branch to `execute()` with delta query, upsert DML, deactivation DML, staging record population |
| `PRM_PayerNetworkBatch` | Mode-Extended | M | Same pattern as Taxonomy batch |
| `PRM_IFCRecordBatch` | Mode-Extended | M | Same pattern; also houses the final email notification |
| `PRM_ExceptionLogEvent__e` | Direct | 0 | Event schema reused as-is, including `PRM_RecordId__c` and `PRM_RecordObjectName__c` |
| `PRM_ExceptionLogEventTrigger` | Direct | 0 | Subscriber creates `PRM_ExceptionLog__c` records with CaseManager lookup |
| `PRM_ExceptionLogger.logExceptionViaEvent()` | Direct | 0 | Rollback-safe logging method reused from IP2/IP3 Catch pattern — now called from PDM batch catches |
| `PRM_OmniUtils` caseManagerId routing | Direct | 0 | Extracts `caseManagerId` from inputMap; used by the Remote Action class for passthrough |
| `PRM_FailedRecordStaging__c` custom object | Direct | 0 | All 42 fields reused unchanged. Process-agnostic by design (see `PRM_FailedRecordStaging_Object_Specification.md` reusability checklist). |
| `PRM_FailedRecordStaging__c.PRM_SourceProcess__c` | Reference | 0 | PDM batches write `'PDM_ManualUpdate_*Batch'` values; no schema change |
| `PRM_FailedRecordStaging__c.PRM_TargetObject__c` | Reference | 0 | Writes the same network/taxonomy/IFC object API names |
| `PRM_NetworkCreationStatus__c` picklist on CaseManager | Direct | 0 | Identical status values; no additional picklist values needed |
| `PRM_NetworkCreationError__c` long-text field on CaseManager | Direct | 0 | Same field, same usage |
| Data Admin "Network Creation Errors" list view | Direct | 0 | Filter `PRM_ProcessName__c IN ('PRM_TaxonomyNetworkBatch', 'PRM_PayerNetworkBatch', 'PRM_IFCRecordBatch')` already covers both INSERT and UPSERT failures because the source process name is the batch class name, not the mode |
| Data Admin "Mark Resolved" Quick Action | Direct | 0 | Operates on `PRM_ExceptionLog__c` regardless of which flow produced it |
| Data Admin Permission Set | Direct | 0 | Same permissions cover PDM failures |
| `PRM_RouteToQC_QuickAction` Screen Flow (from US 2 of `US_DataAdmin_NetworkError_ListViewAndQCRouting.md`) | Direct | 0 | Validates and routes a failed CaseManager regardless of whether the failure originated in a create or update flow |
| Email template `PRM_PractitionerCreation_Success` | Direct | 0 | Subject/body parameterized by CaseManager record — works for both flows |
| Email template `PRM_PractitionerCreation_Failure` | Direct | 0 | Same |
| `PRM_PractitionerPracticeLocation__c` object and fields | Reference | 0 | PDM batches query this object — read-only reuse |
| `PRM_FacilityPractitionerTxNw__c`, `PRM_FacilityPractitionerNw__c`, `PRM_FacilityIFC__c` target objects | Reference | 0 | PDM batches upsert and deactivate records on these objects; no schema change |

**Summary:** 27 of 30 components are Direct (zero-effort) reuse. The 3 Mode-Extended components (the Platform Event, the Orchestrator, and the Remote Action) add approximately 8–12 lines of code each. The 3 batch classes are Mode-Extended with approximately 40 lines of UPSERT-branch code each. Compared to building PDM Manual Update from scratch — which would require duplicating the event schema, trigger, orchestrator, 3 batch classes, staging object, exception-event pipeline, list views, Quick Actions, permission sets, and email templates — framework reuse saves an estimated 30–35 story points (approximately 45–55 developer days).

---

## Section 9: Exception Handling

### 9.1 Per-Row Failure Handling

Every `execute()` call in every batch class inspects the results of its partial-success DML:

```apex
Database.UpsertResult[] upsertResults =
    Database.upsert(desired, PRM_FacilityPractitionerTxNw__c.PRM_ExternalId__c, false);

Database.SaveResult[] deactivateResults =
    Database.update(deactivations, false);
```

For each result where `isSuccess()` returns `false`:

1. Build a `PRM_FailedRecordStaging__c` record using the shared helper described in section 6.4. The helper captures the first error from `result.getErrors()`, the target object API name, the full JSON serialization of the sObject via `JSON.serialize(record)`, the CaseManager ID (as `PRM_ParentRecordId__c` and `PRM_CaseManager__c`), the batch job ID via `BC.getJobId()`, the source process name, the transaction/request ID, and severity level `'Error'`.
2. Append to the batch's stateful `List<PRM_FailedRecordStaging__c>` accumulator.
3. At the end of `execute()`, insert the accumulated staging records: `Database.insert(stagingAccumulator, false)`.

Per-row failures do not roll back the successful rows in the same DML call. The practitioner's update proceeds partially, and Data Admins triage the staged failures.

### 9.2 Transaction-Level Exception Handling

Any uncaught Apex exception in `execute()` is trapped by a `try/catch` block around the entire execute body:

```apex
try {
    // delta query, upsert, deactivation, staging
} catch (Exception e) {
    PRM_ExceptionLogger.logExceptionViaEvent(
        'PDM_ManualUpdate_TaxonomyNetworkBatch', // processName
        'ASYNC',                                  // integrationType
        'Error',                                  // severityLevel
        e.getStackTraceString(),                  // stackTrace
        e.getMessage(),                           // errorMessage
        e.getTypeName(),                          // exceptionType
        e.getLineNumber(),                        // lineNumber
        requestId,                                // correlationId
        null,                                     // errorCode
        'Salesforce',                             // sourceSystem
        'Salesforce',                             // targetSystem
        JSON.serialize(paramsMap),                // payload
        caseManagerId                             // caseManagerId
    );
    totalErrors += scope.size();
    errorMessages.add('Execute Exception: ' + e.getMessage());
    throw e; // re-throw so the batch framework records the execute as failed
}
```

Because `PRM_ExceptionLogEvent__e` has `publishBehavior = PublishImmediately`, the event publish is committed independently of the Apex transaction. When the `throw` re-raises the exception and the batch framework rolls back the implicit transaction, the exception log survives the rollback — the exact failure-mode fix designed into the Practitioner Creation framework.

### 9.3 Status Field Progression on Failure

The CaseManager's `PRM_NetworkCreationStatus__c` transitions to `'Failed'` in one of two places:

- If a batch's `finish()` method detects that `totalErrors > 0 && totalProcessed == 0` — meaning every record in that batch's scope failed — it sets the status to `'Failed'` and does not chain to the next batch. The chain stops.
- If the final batch (`PRM_IFCRecordBatch`) finishes with any errors, its `finish()` method sets status to `'Failed'` and populates `PRM_NetworkCreationError__c` with the aggregated error list (truncated to 32,768 characters).

When the chain stops mid-way (e.g., all taxonomy records failed), the subsequent batches never run, but the CaseManager clearly reflects the failure point and the `PRM_FailedRecordStaging__c` records show which rows failed and why.

### 9.4 Email Notification on Batch-Chain Completion

The final batch (`PRM_IFCRecordBatch`) calls `sendNotification(success)` in `finish()`. The method:

1. Queries the CaseManager record for `CreatedBy.Email` and `CreatedBy.Name`.
2. Builds a `Messaging.SingleEmailMessage` with:
   - Subject: `"Practitioner Update Completed Successfully"` or `"Practitioner Update Encountered Errors"`.
   - Body: includes the CaseManager ID, total records processed, total errors, and a link to the "Failed Records" related list on the CaseManager record.
3. Sends via `Messaging.sendEmail(...)`.

On chain-aborted failures (e.g., taxonomy batch fails entirely), the email is sent from whichever batch's `finish()` transitioned the status to `'Failed'`. The chain never reaches `PRM_IFCRecordBatch`, so `PRM_TaxonomyNetworkBatch.finish()` or `PRM_PayerNetworkBatch.finish()` fires the failure email in those cases.

### 9.5 UPDATE-Specific Retry Safety

Upsert-mode batch classes are intrinsically safer to retry than insert-mode classes. The reason is idempotency through external-ID-keyed upserts plus delta computation:

- **Idempotent upsert:** `Database.upsert(records, PRM_ExternalId__c, false)` keys each row by its external ID. A second run of the batch against the same desired payload writes to the same Salesforce records, producing the same final state. No duplicates are created.
- **Idempotent delta computation:** The `execute()` method's delta query always returns the current system state, not a cached one. If a previous run partially succeeded (say, 40 of 45 payer networks upserted and 5 failed), the next run's delta query sees the 40 already-correct records, adds zero work for them, and focuses deactivation decisions on the unchanged remainder. The stale-record deactivation set likewise converges on the correct answer regardless of how many prior runs have occurred.
- **No duplicate-DML hazard:** Because every DML is upsert-by-external-ID plus update-by-ID (for deactivation), no code path in `execute()` can produce duplicate records. A create-mode insert batch, by contrast, could produce duplicates on retry unless it first queried to check for existing records — which is exactly the delta-query cost the Queueable approach cannot afford.

The practical consequence for the retry mechanism (`PRM_RetryFailedProcessingController` from `US_PractitionerCreation_Complete_Implementation.md` Story #5) is that PDM's staging records can be retried aggressively — immediately, automatically, and repeatedly — without data integrity risk. The retry logic simply re-runs the batch, and each run converges closer to the correct end state.

### 9.6 Data Admin Tooling Reuse

Every Data Admin list view, permission set, and Quick Action built for Practitioner Creation in `US_DataAdmin_NetworkError_ListViewAndQCRouting.md` applies unchanged to PDM Manual Update failures:

- **"Network Creation Errors — Needs Review" list view:** Surfaces any exception log with `PRM_ProcessName__c` starting with one of the batch class names. PDM failures appear in the same list because the batch class names are the same.
- **"Mark Resolved" and "Mark Resolved & Route to QC" Quick Actions:** Operate on `PRM_ExceptionLog__c` and `IndividualApplication` records regardless of which flow produced the failure. Data Admins see a single unified triage queue.
- **Data Admin permission set:** Grants read/edit on `PRM_ExceptionLog__c`, `PRM_FailedRecordStaging__c`, and the CaseManager status fields — applies unchanged.

No net-new Data Admin tooling is needed for PDM.

---

## Section 10: Implementation Timeline

Presented as 2-week sprints. The hard prerequisite is stated explicitly first.

### Sprint N (Pre-requisite) — Practitioner Creation Framework QA Deployment

The Practitioner Creation batch framework must be deployed to the QA sandbox and pass its integration tests before any PDM development begins. Without the framework deployed, there is nothing to extend.

Deliverables required in QA:
- `NetworkCreationRequested__e` Platform Event (with all existing fields)
- `PRM_NetworkCreationEventTrigger`
- `PRM_NetworkCreationOrchestrator` (with `handleEvent()` and `queueNetworkCreation()`)
- `PRM_NetworkCreationRemote.publishNetworkCreationEvent()`
- `PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch` (INSERT mode)
- `PRM_FailedRecordStaging__c` custom object with all 42 fields
- `PRM_ExceptionLogEvent__e` schema (with `PRM_RecordId__c`, `PRM_RecordObjectName__c`)
- `PRM_ExceptionLogEventTrigger`
- `PRM_ExceptionLogger.logExceptionViaEvent()`
- `PRM_NetworkCreationStatus__c` picklist on CaseManager/IndividualApplication
- `PRM_NetworkCreationError__c` long text field on CaseManager
- Data Admin list views, Quick Actions, and permission sets

Integration tests that must pass:
- 1-location practitioner creation: full chain completes with zero staging records
- 3-location creation: ~54 records created across all three batches
- Forced-failure creation (validation rule): `PRM_FailedRecordStaging__c` populated, `PRM_ExceptionLogEvent__e` fired, exception log visible on CaseManager

**Any sprint plan that ignores this dependency is invalid.** If Practitioner Creation is delayed, PDM is delayed by the same amount.

### Sprint N+1 — PDM Mode Extension (Core Development)

- **Week 1:**
  - Add `Mode__c` field to `NetworkCreationRequested__e` Platform Event (S).
  - Mode-extend `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` (S).
  - Mode-extend `PRM_NetworkCreationOrchestrator` and inner `NetworkRequest` class (S).
  - Mode-extend `PRM_TaxonomyNetworkBatch` with UPSERT branch: delta query, upsert DML, deactivation DML (M).
  - Update unit tests for Taxonomy batch — add UPSERT-mode test fixtures and assertions.
- **Week 2:**
  - Mode-extend `PRM_PayerNetworkBatch` (M).
  - Mode-extend `PRM_IFCRecordBatch` (M).
  - Update unit tests for Payer Network and IFC batches.
  - Build `PRM_BatchStagingHelper` shared utility for consistent staging-record construction (S).
  - Integration test: verify mode-parameter propagation end-to-end in a sandbox with a test harness that publishes `NetworkCreationRequested__e` with `Mode__c = 'UPSERT'` and asserts the UPSERT branches of each batch fire.

### Sprint N+2 — PDM IP Simplification & End-to-End Integration

- **Week 1:**
  - Deactivate IP3 (`PRM_CreateDelegatedHFNRecords`) elements in the PDM container.
  - Replace `AddTaxNetworkLogic` element in the PDM container with the new `PublishNetworkCreationEvent` Remote Action element.
  - Add `ResponseWithMessage` response element to return "Processing..." status to the OmniScript.
  - Configure the Remote Action's `additionalInput` to include `Mode: 'UPSERT'`.
- **Week 2:**
  - End-to-end integration test in QA sandbox:
    - 1-location PDM update: verify UI returns in under 3 seconds, batch chain completes, status progresses to `Completed`.
    - 3-location PDM update where one payer network is removed in the incoming payload: verify the stale record is deactivated by the delta logic.
    - 5+ location PDM update: verify governor limits are not breached across the batch chain.
    - Forced-failure PDM update: verify `PRM_FailedRecordStaging__c` population and `PRM_ExceptionLog__c` creation.
  - Regression test the Practitioner Creation flow to confirm shared-class changes did not regress INSERT mode.

### Sprint N+3 — UAT and Production Rollout

- **Week 1:**
  - User Acceptance Testing with Network Maintenance team.
  - Fix any UAT-surfaced defects.
  - Write deployment runbook and rollback plan.
- **Week 2:**
  - Production deployment (custom fields, batch class mode-extensions, IP metadata, Remote Action element).
  - 48-hour post-deployment monitoring: query `AsyncApexJob`, `PRM_ExceptionLog__c`, `PRM_FailedRecordStaging__c` for anomalies.
  - Sign-off.

### Total Elapsed Weeks

| Sprint | Weeks | Cumulative |
|---|---|---|
| Sprint N (Pre-requisite) | 2 | 2 |
| Sprint N+1 | 2 | 4 |
| Sprint N+2 | 2 | 6 |
| Sprint N+3 | 2 | 8 |
| **TOTAL (from start of prerequisite to PDM production)** | **8 weeks** | **8 weeks** |

PDM-only elapsed time (Sprint N+1 through N+3): **6 weeks**.

---

## Section 11: Effort Estimation Table

| Component | Category | Story Points | Est. Days | Owner Role |
|---|---|---|---|---|
| `NetworkCreationRequested__e` Platform Event | Reused (0 effort) | 0 | 0 | — |
| `PRM_NetworkCreationEventTrigger` | Reused (0 effort) | 0 | 0 | — |
| `PRM_FailedRecordStaging__c` custom object (42 fields) | Reused (0 effort) | 0 | 0 | — |
| `PRM_ExceptionLogEvent__e` and trigger | Reused (0 effort) | 0 | 0 | — |
| `PRM_ExceptionLogger.logExceptionViaEvent()` | Reused (0 effort) | 0 | 0 | — |
| `PRM_NetworkCreationStatus__c` picklist, `PRM_NetworkCreationError__c` field | Reused (0 effort) | 0 | 0 | — |
| Data Admin list views, permission set, Quick Actions | Reused (0 effort) | 0 | 0 | — |
| Email templates (success/failure) | Reused (0 effort) | 0 | 0 | — |
| Add `Mode__c` field to `NetworkCreationRequested__e` | Configuration / Metadata | 1 | 0.5 | Admin |
| Mode-extend `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` | Mode-Extended | 1 | 0.5 | Developer |
| Mode-extend `PRM_NetworkCreationOrchestrator` (handleEvent, queueNetworkCreation, NetworkRequest) | Mode-Extended | 2 | 1 | Developer |
| Mode-extend `PRM_TaxonomyNetworkBatch` (UPSERT branch: delta query, upsert DML, deactivation DML, staging) | Mode-Extended | 3 | 1.5 | Developer |
| Mode-extend `PRM_PayerNetworkBatch` | Mode-Extended | 3 | 1.5 | Developer |
| Mode-extend `PRM_IFCRecordBatch` | Mode-Extended | 3 | 1.5 | Developer |
| `PRM_BatchStagingHelper` shared utility class | New Development | 2 | 1 | Developer |
| PDM container IP simplification: deactivate IP3 elements, add Remote Action element, configure `Mode: 'UPSERT'` additionalInput | Configuration / Metadata | 2 | 1 | OmniStudio Developer |
| Response message element on PDM container | Configuration / Metadata | 1 | 0.5 | OmniStudio Developer |
| Unit tests for all three Mode-Extended batch classes (mode-parameterized) | Testing | 5 | 2.5 | Developer |
| Unit tests for Orchestrator and Remote Action mode propagation | Testing | 2 | 1 | Developer |
| Integration tests in QA sandbox (1-loc, 3-loc, 5+ loc, delta-deactivation, forced-failure) | Testing | 5 | 2.5 | QA Engineer |
| Regression test for Practitioner Creation flow (INSERT mode) | Testing | 2 | 1 | QA Engineer |
| UAT with Network Maintenance team | Testing | 3 | 1.5 | BA + QA |
| Deployment runbook and rollback plan | Configuration / Metadata | 1 | 0.5 | Developer |
| Production deployment and 48-hour monitoring | Configuration / Metadata | 2 | 1 | DevOps + Developer |
| **TOTALS** | | **38** | **~17.5 days** | |

### Net Effort vs. Build-From-Scratch Comparison

If PDM Manual Update were built from scratch without reusing the Practitioner Creation framework, the effort would additionally include:

- Building the Platform Event schema (3 points)
- Building the event subscriber trigger (2 points)
- Building the orchestrator (5 points)
- Building the Remote Action class (3 points)
- Building three batch classes from scratch (15 points)
- Building the `PRM_FailedRecordStaging__c` object with 42 fields, validation rules, page layouts (10 points)
- Building the `PRM_ExceptionLogEvent__e` pipeline (5 points)
- Building Data Admin list views, permission sets, Quick Actions (8 points)
- Building email templates (2 points)
- Building all unit tests for the above (10 points)

Total additional build-from-scratch effort: approximately **63 story points** (~30 developer days).

**Framework reuse saves 63 story points** (~30 developer days) on PDM. This is the direct cost-saving from the Practitioner Creation framework investment. The PDM net-new effort of 38 story points is 62% less than the 38 + 63 = 101 points it would take to deliver PDM independently. The zero-effort components in Section 8 — the Platform Event schema, the event subscriber trigger, the staging object, the exception-event pipeline, the Data Admin tooling, and the email templates — account for the majority of the saving.

---

## Section 12: Definition of Done

- [ ] All PDM Manual Update IP chain elements that previously called network/taxonomy/IFC creation logic (`AddTaxNetworkLogic` element and all IP3 conditional blocks `CB_LogicExecuteTxNetwork`, `CB_LogicExecuteLocNetwork`, `CB_ExecuteIFCLogic`, `CB_DeactivateStaleRecords`) have been removed or set to `isActive: false`.
- [ ] The trimmed PDM IP chain contains only synchronous address/facility/location upsert work (IP1 and IP2 unchanged) and the Platform Event publish step (`PRM_NetworkCreationRemote.publishNetworkCreationEvent()`).
- [ ] The Platform Event publish returns to the UI in under 3 seconds for a practitioner with 5+ practice locations (measured end-to-end from OmniScript submit to OmniScript response).
- [ ] All heavy DML (taxonomy network upsert, payer network upsert, IFC record upsert, stale record deactivation) executes in Batch Apex (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`), not in any IP or Queueable.
- [ ] `Mode__c` field exists on `NetworkCreationRequested__e` with values `INSERT` and `UPSERT`, and the mode value propagates correctly from Remote Action through Orchestrator through every batch class.
- [ ] Unit test coverage is 90% or higher on all mode-extended batch classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) and on the `PRM_BatchStagingHelper` utility.
- [ ] Integration tests pass in QA sandbox for: single-location PDM update, 3-location PDM update, 5+ location PDM update.
- [ ] Delta computation correctly identifies and deactivates stale records. Specific test: update a practitioner removing one payer network association from the incoming payload; verify that after the batch chain completes, the corresponding `PRM_FacilityPractitionerNw__c` record is set to `PRM_IsActive__c = false` and `PRM_EffectiveTo__c = today`.
- [ ] Failure injection tests pass: a forced DML failure in each batch's `execute()` (e.g., via temporary validation rule) produces `PRM_FailedRecordStaging__c` records with full payload JSON and correct error details, and fires `PRM_ExceptionLogEvent__e` which creates a `PRM_ExceptionLog__c` record linked to the CaseManager via `PRM_IndividualApplication__c`.
- [ ] `PRM_NetworkCreationStatus__c` on CaseManager correctly progresses through `Not Started → Queued → Processing Taxonomies → Processing Payer Networks → Processing IFC` and lands on `Completed` or `Failed` for every test scenario.
- [ ] Email notification is sent to the submitting user (CaseManager `CreatedBy.Email`) on batch chain completion (success path) and on batch chain failure (failure path from any batch's `finish()`).
- [ ] UAT sign-off obtained in writing from the Network Maintenance team lead.
- [ ] No regression in Practitioner Creation flow: the shared mode-extended classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) pass both INSERT-mode (Practitioner Creation) and UPSERT-mode (PDM Manual Update) integration tests.
- [ ] Data Admin "Network Creation Errors — Needs Review" list view surfaces PDM Manual Update failures with the same tooling used for Practitioner Creation failures — verified by running a forced-failure PDM test and confirming the failure appears in the list view without any list-view configuration change.
- [ ] Mode-parameter propagation verified end-to-end: a Platform Event published with `Mode__c = 'UPSERT'` causes every batch in the chain to execute its UPSERT branch, confirmed by log inspection or test assertions.
- [ ] Deployment runbook documents field-deployment order (add `Mode__c` to Platform Event, deploy Apex mode extensions, deploy IP metadata) and rollback procedure (revert IP to previous version, revert Apex classes).
- [ ] 48-hour post-production monitoring completed: no unexpected `AsyncApexJob` failures, no unexpected `PRM_ExceptionLog__c` records, no unexpected `PRM_FailedRecordStaging__c` records from the PDM flow, batch chain completes within 8–18 minutes for representative practitioner sizes.
