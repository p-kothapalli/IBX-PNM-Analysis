# USER STORY US-PAR-01: PAR Form — Move Record Creation to Batch (Sub-3s Submit + Atomic Per-Submission + Navigate to Case Manager)

**Persona:** Credentialing Intake Specialist, Sr. Data Reporting Analyst, Salesforce Developer
**Priority:** P0 — partial-data accumulation (36 `updatePPLAddresesForPAR()` throws / 30 d), 16 documented production failures, ~13% of practitioner Accounts have ≥ 2 PAR submissions (re-submit storm)
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_PractitionerParticipationForm_English` v111 (Final Submit step) → planned v112
**Integration Procedures (impacted):**
- `PRM_CreateParFormRecordsContainer_Procedure_1` (v1, current) — entry point invoked from the OmniScript Final Submit → **new v2** replaces the body with one Remote Action
- `PRM_CreateParFormRecords_Procedure_29` (the orchestrator with 7 sub-IPs) — **deactivate** (kept `isActive=false` for 30 days as a session backstop)
- The 6 child sub-IPs (`PRM_PractitionerScreenRecordCreation`, `PRM_PractitionerScreenExistingNPIRecordUpdation`, `PRM_CreateGroupScreenRecord`, `PRM_CreatePractitionerAddressRecords`, `PRM_CreateProviderScreenRecords`, `PRM_CreateContactScreenRecords`) — **logic absorbed into `PRM_ParFormSubmissionBatch.execute()`**; the IPs themselves go `isActive=false`

**Apex (reference pattern to clone):** `PRM_NetworkCreationEnvelope.cls`, `PRM_NetworkCreationRow.cls`, `PRM_NetworkCreationHelper.cls`, `PRM_NetworkCreationBatch.cls`, `PRM_OmniProcessUtils.cls` (route registration), `PRM_NotificationHelper.cls`
**Related stories (must ship first or in parallel):**
- `US-PAR-02` — Exception Logging via Platform Event (logging in catch block depends on it)
- `US-PAR-03` — Pre-Submit Callout Phase (batch cannot do callout-after-DML)
- `US-PAR-04` — Trigger Idempotency (batch must be safe to retry)
**Relevant requirements:** `00_Overview_PARForm_BatchRefactor_Roadmap.md`, `PAR_Form_PartialDataRollback_Investigation_FixPlan.md`, `PRM_Batch_Rollback_Strategies.md`, `US_DelegatedPractitioner_AddressCreation_BatchRefactor.md` (the blueprint)

---

## Story

**As a** Credentialing Intake Specialist submitting a new PAR (Practitioner Participation Request) form,
**I want** the Submit button to return in **under 3 seconds** and automatically navigate me to the Case Manager record, with practitioner / vendor / NPI / taxonomy / address / contact creation continuing atomically in the background,
**So that** I can move on to the next intake immediately — without staring at a spinner, without double-submitting (which today produces the duplicate-error symptoms documented in `PAR_Form_DuplicateErrors_DataFix_Runbook.md`), and without leaving orphaned partial records behind when one of the seven sub-steps fails.

**Why it matters:** Today the PAR form runs 7 OmniStudio sub-IPs synchronously under the OmniScript HTTP turn. The chain is configured with `chainOnStep: false` on every sub-IP, so each one commits in its own Apex transaction; if sub-IP 4/5/6/7 fails, the records created by sub-IP 2 are **permanently stranded** (verified in production via the 36 `updatePPLAddresesForPAR()` null-input throws / 30 d and the 277 HCPT duplicate-junction pairs accumulated to date). The user has no way to tell whether their submission worked — so they re-submit, which triggers the duplicate-collision symptoms in `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md`. The Delegated Practitioner team solved exactly this problem in April–May 2026 with `PRM_NetworkCreationBatch`; this story applies that same architectural pattern to PAR.

---

## Scope

| Flow | OmniScript | Affected IP / Element | Apex |
|------|------------|----------------------|------|
| PAR Submit | `PRM_PractitionerParticipationForm_English` v111 → v112 — Final Submit element | `PRM_CreateParFormRecordsContainer_Procedure_1` v1 → v2 | `PRM_OmniProcessUtils.callMethod('enqueueParFormSubmission', …)` → `PRM_ParFormSubmissionHelper.enqueue(...)` → `Database.executeBatch(new PRM_ParFormSubmissionBatch(envelope), 1)` |
| Per-submission DML | n/a (async) | `PRM_CreateParFormRecords_Procedure_29` (deactivate); child sub-IPs (deactivate) | `PRM_ParFormSubmissionBatch.execute()` — replaces all six sub-IP bodies inside a single Savepoint per submission |
| Post-submit status | OmniScript Navigate Action | Container v2 Response Action returns `caseManagerId`, `jobId`, `success`, `message` | `PRM_ParFormSubmissionBatch.finish()` updates `IA.PRM_ParFormSubmissionStatus__c` and sends bell notification |

---

## Current State (verified from codebase)

### `PRM_CreateParFormRecordsContainer_Procedure_1` (current v1)

```
Container (rollbackOnError: true)
└── TryCatchBlock (failOnBlockError: true, remoteClass: PRM_OmniUtils.logTryCatchException)
       └── IP Action: IP_CreateParFormRecords
              └── PRM_CreateParFormRecords_Procedure_29 (rollbackOnError: true)
                     ├── seq 1: GetFeatureConfigSetting (DR Turbo, chainOnStep=true)
                     ├── seq 2: PRM_PractitionerScreenRecordCreation     (chainOnStep=false)  [IsExistingNPI==false]
                     ├── seq 3: PRM_PractitionerScreenExistingNPIRecordUpdation (chainOnStep=false) [IsExistingNPI==true]
                     ├── seq 4: PRM_CreateGroupScreenRecord              (chainOnStep=false)
                     ├── seq 5: PRM_CreatePractitionerAddressRecords     (chainOnStep=false)   ← does Precisely callout
                     ├── seq 6: PRM_CreateProviderScreenRecords          (chainOnStep=false)
                     ├── seq 7: PRM_CreateContactScreenRecords           (chainOnStep=false)
                     ├── seq 8: SetValues SV_PractitionerIds
                     └── seq 9: Response Action
```

Failure mode:
- 36 `PRM_OmniUtils.updatePPLAddresesForPAR()` null-input throws / 30 days — direct evidence that upstream sub-IPs are failing partway through, leaving downstream sub-IPs without the expected ids
- 48 `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` NPEs / 30 days
- 277 cumulative HCPT duplicate `(AccountId, TaxonomyId)` pairs from collision-then-retry cycles
- ~13% of practitioner accounts have ≥ 2 PAR IAs (re-submit storm)

The `chainOnStep: false` choice was **deliberate** to avoid Salesforce's "callout-after-DML" rule (sub-IP 5 calls Precisely; 1,007 `PRM_ValidateCAQH` "uncommitted work pending" exceptions / 30 d across the org demonstrate the rule is binding). We must preserve that separation — see **US-PAR-03**.

### `PRM_NetworkCreationBatch.cls` (the reference pattern, lines 1–193)

The Delegated team's pattern, ported here, applies 1:1:

```apex
public with sharing class PRM_NetworkCreationBatch implements Database.Batchable<SObject>, Database.Stateful {
    @TestVisible private final PRM_NetworkCreationEnvelope envelope;
    @TestVisible private Integer successCount = 0;
    @TestVisible private Integer failureCount = 0;
    // Stateful memoization — recovers ~60% SOQL across chunks
    @TestVisible private Map<String, Id> cachedHfNameToId = null;
    // …
    public void execute(Database.BatchableContext bc, List<SObject> scope) {
        Integer chunkSizeAtStart = scope == null ? 0 : scope.size();
        try {
            // … per-row processing, Database.insert(..., false) …
        } catch (Exception e) {
            // CRITICAL: bump in-memory accounting BEFORE any DML so the count
            // survives a secondary governor unwind (IA-0000150602, 2026-05-20).
            failureCount += chunkSizeAtStart;
            // … best-effort exception log + staging …
        }
    }
}
```

We will mirror every architectural decision (envelope, Stateful, memoized lookups, per-row staging, governor-unwind guard, `finish()` updates IA status + bell notification).

---

## Proposed Architecture (After)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ TX1 — synchronous UI turn (target P95 ≤ 3 s, P99 ≤ 5 s)                       │
│                                                                                │
│ OmniScript Final Submit                                                       │
│   ├── (US-PAR-03) Pre-Submit Callout step: Precisely address standardization  │
│   │              + any MuleSoft pre-validation. Output flows into the next     │
│   │              IP as fully-canonicalized address payload.                    │
│   │                                                                            │
│   ├── PRM_CreateParFormRecordsContainer v2                                    │
│   │     └── Remote Action: PRM_OmniProcessUtils.callMethod                    │
│   │           additionalInput.methodName = 'enqueueParFormSubmission'          │
│   │           additionalInput.<full PAR payload>                              │
│   │           → PRM_ParFormSubmissionHelper.enqueueParFormSubmission(input)    │
│   │               • idempotency guard: query AsyncApexJob for same             │
│   │                 caseManagerId enqueued in last 60s; return existing jobId │
│   │               • validate inputs (npi, taxId, addresses present)           │
│   │               • build PRM_ParFormSubmissionEnvelope                       │
│   │               • Database.executeBatch(new PRM_ParFormSubmissionBatch(env)) │
│   │               • return { jobId, success: true, message,                   │
│   │                          caseManagerId, individualApplicationId }         │
│   │     └── Response Action returns those keys                                │
│   │                                                                            │
│   ├── Show Toast (variant=info):                                              │
│   │     "Your PAR submission is being processed. We'll notify you when         │
│   │      it's complete (typically <2 min). Case # {{caseManagerName}}"        │
│   │                                                                            │
│   └── Navigate Action: Target=SObject, Record Id={{caseManagerId}}            │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ (Database.executeBatch)
┌────────────────────────────────────────────────────────────────────────────────┐
│ TX2 — Batchable, Stateful, separate Apex transaction(s)                        │
│                                                                                │
│ PRM_ParFormSubmissionBatch.execute(scope = 1 submission per chunk)             │
│                                                                                │
│   for each PRM_ParFormSubmissionRow row in this chunk:                        │
│     Savepoint sp = Database.setSavepoint();                                   │
│     try {                                                                      │
│       Ctx ctx = createPractitionerRecords(row);   // replaces sub-IP 2/3      │
│       ctx.group   = createGroupRecords(row, ctx); // replaces sub-IP 4         │
│       ctx.address = createAddressAndPPLRecords(row, ctx); // sub-IP 5 (DML)    │
│       ctx.provider = createProviderRecords(row, ctx); // sub-IP 6              │
│       ctx.contact  = createContactRecords(row, ctx);  // sub-IP 7              │
│       activateRecords(ctx, row);                                              │
│       linkCaseManager(ctx, row);                                              │
│       successCount++;                                                          │
│     } catch (Exception e) {                                                    │
│       Database.rollback(sp);                                                   │
│       failureCount++;                                                          │
│       stageFailure(row, e);                       // US-PAR-05                │
│       publishExceptionEvent(row, e);              // US-PAR-02                │
│     }                                                                          │
│                                                                                │
│   On governor-unwind out of the outer try-catch:                              │
│     failureCount += chunkSizeAtStart;   ← Pattern D, IA-0000150602 lesson     │
│                                                                                │
│ PRM_ParFormSubmissionBatch.finish()                                            │
│   • update IndividualApplication.PRM_ParFormSubmissionStatus__c                │
│       = (failureCount==0 ? Success : (successCount==0 ? Failed : Partial))    │
│   • PRM_NotificationHelper.sendBellNotification(...)                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Why a Batchable, not a Queueable, not a single Apex transaction

| Option | Why we say no |
|---|---|
| Single sync Apex (Apex orchestrator with one Savepoint) | Works for 1 submission but hits CPU / heap caps on PARs with many vendors / taxonomies. Already known from the IA-0000150602 incident on the Network side. |
| Queueable | No per-chunk SOQL/CPU budget; no `Database.Stateful` memoization; harder to retry one submission of many. |
| Platform-Event-driven (Pattern from `PRM_NetworkCreation_BatchImplementation_Guide.md` Feb 2026) | One extra hop; harder to observe in `AsyncApexJob`; the Delegated team explicitly rejected it in favour of the Helper → executeBatch route in May 2026. |
| **`Database.Batchable<SObject>, Database.Stateful`** ← chosen | Per-chunk budget, Stateful memoization, well-understood ops surface, mirrors `PRM_NetworkCreationBatch` line-for-line. |

### Why one submission per chunk (chunkSize=1)

A single PAR submission **at the maximum scale supported by the OmniScript today (5 groups × 10 locations per group)** creates approximately **~490 DML rows across ~15 object types**:

| Object | Worst-case count (5×10) | Source |
|---|---|---|
| `Account` (Practitioner Person + Vendor / Group) | 1 + 5 = 6 | Per-group from `GroupInformation` repeat |
| `HealthcareProvider` (HCP) | 1 + 5 = 6 | One per NPI (practitioner + each group) |
| `HealthcareProviderNpi` (HCNPI) | 1 + 5 = 6 | One per NPI |
| `HealthcareProviderTaxonomy` (HCPT) | ~20 (typical) — up to ~50 (uncapped multi-select) | Practitioner specialties + per-group specialties |
| `HealthcareFacility` (HF) | 5 (group) + 50 (location) = 55 | One per group, one per location |
| `Schema.Location` | 50 | One per location |
| `Schema.Address` | ~60 | One per location + group billing/mailing |
| `HealthcarePractitionerFacility` (PPL / HPF) | 50 | One per (practitioner × location) — this is the largest single bulk insert |
| `ContactPointAddress` (CPA) | ~150 | Phone / fax / email per location |
| `Contact` | 2 | Primary + secondary |
| `HealthcarePractitionerLicense` | 4 | `AddLicenseBlock.repeatLimit = 3` → 4 max |
| `IndividualApplication` (Case Manager) | 1 | One per submission |
| `Case` (PRM) | 1 | One per submission |
| `ProviderFeatureAssignment` (PFA) | ~10 | Telehealth / concierge / etc. per group |
| `PRM_Identifier*__c` (trigger-inserted) | ~70 | One per HCP / HCNPI / HF / PPL / Account |
| **TOTAL** | **~490** | |

Bundling N submissions per chunk multiplies all of the above by N and breaks the per-transaction SOQL=200 / DML=150 ceiling. With `chunkSize=1`, one submission's atomicity per chunk fits comfortably inside Apex async transaction limits (estimated 15 of 150 DML statements, 490 of 10,000 DML rows, ~30 of 100 SOQL queries with full memoization, ~3–6s CPU of 60s budget). `Database.Stateful` still memoizes cross-chunk lookups (Taxonomy Id by code, RecordType Ids, FeatureConfigSetting, **plus** the expanded memoization set required for max scale — see "Stateful memoization fields" below).

**`chunkSize=1` is mandatory.** Do not tune up. Document in `PRM_ParFormSubmissionHelper`:

```apex
// chunkSize must remain 1. A single PAR submission at the maximum form scale
// (5 groups × 10 locations) creates ~490 DML rows across ~15 object types;
// see US_PAR_ScaleAudit_5Groups_10Locations.md for the line-by-line accounting.
// Bundling N submissions per chunk breaks the per-transaction governor limits.
Id jobId = Database.executeBatch(new PRM_ParFormSubmissionBatch(env), 1);
```

### Stateful memoization fields (required for max scale)

At 50 PPL rows / 150 CPA rows / 60 Address rows per submission, any per-row SOQL is fatal. The batch's `Database.Stateful` instance variables must include the following lookup caches:

```apex
// Existing memoization (from the Network Creation pattern)
@TestVisible Map<String, Id> taxonomyIdByCode      = new Map<String, Id>();
@TestVisible Map<String, Id> recordTypeIdByDevName = new Map<String, Id>();
@TestVisible Map<String, Id> featureConfigByName   = new Map<String, Id>();

// NEW — required because the existing pipeline re-queries these per location
// (50 lookups per submission today). See US_PAR_ScaleAudit §3.4.
@TestVisible Map<String, Id> hfIdBySourceSystemId  = new Map<String, Id>();   // HealthcareFacility lookup
@TestVisible Map<String, Id> accountIdByNpi        = new Map<String, Id>();   // Vendor / Practitioner Account by NPI
@TestVisible Map<String, Id> addressIdByDigest     = new Map<String, Id>();   // Schema.Address by (line1, city, zip) hash
@TestVisible Map<String, Id> locationIdByDigest    = new Map<String, Id>();   // Schema.Location by (addressId, npi)
```

---

## Technical Section (For Developers)

### A. New Apex artifacts

| Component | Type | Change |
|---|---|---|
| **`PRM_ParFormSubmissionEnvelope.cls`** | New POJO | Fields: `Id caseManagerId; Id individualApplicationId; Id caseDataManagerId; Id caseId; Id practitionerAccountId; Id personContactId; Date effectiveFrom; Date effectiveTo; Boolean isActive; Boolean isPending; String practitionerCreationType; String pncFlag; String flowType; String featureConfigSettingId; List<PRM_ParFormSubmissionRow> rows;` — one row per submission since the form is one-practitioner-at-a-time today, but the POJO supports bulk for future BulkPractitioner Creation reuse. |
| **`PRM_ParFormSubmissionRow.cls`** | New POJO | The full payload that the seven sub-IPs need today, flattened. Fields drawn from `PRM_CreateParFormRecords` sample input + the six sub-IPs' DR inputs. Sub-groups: `PractitionerScreen` (firstName, lastName, gender, npi, taxonomyIds, …), `GroupScreen` (vendorTaxId, vendorName, vendorAddresses, …), `AddressScreen` (standardizedAddresses from US-PAR-03 — DML-ready), `ProviderScreen` (languages, pronouns, providerRole, …), `ContactScreen` (primaryContact, secondaryContact, …). |
| **`PRM_ParFormSubmissionHelper.cls`** | New Apex class | `public static Map<String,Object> enqueueParFormSubmission(Map<String,Object> input, Map<String,Object> outMap)` — the sync entry point. Validates input, builds envelope, applies idempotency guard (see **§B**), enqueues batch. **Must NEVER throw** — wraps everything in try/catch and logs via `PRM_ExceptionLogger.logException` (sync log is fine here — no rollback risk in this method). |
| **`PRM_ParFormSubmissionBatch.cls`** | New Apex class — `implements Database.Batchable<SObject>, Database.Stateful` | The heavy lift. See **§C** for skeleton. Replicates the logic of all 6 child sub-IPs in Apex DML form, inside a per-submission Savepoint. |
| **`PRM_ParFormSubmissionHelperTest.cls`** | New Apex test | ≥ 90% coverage; null caseManagerId guard, idempotency guard returns existing jobId, happy path enqueues, malformed payload returns success=false. |
| **`PRM_ParFormSubmissionBatchTest.cls`** | New Apex test | ≥ 90% coverage; happy path, per-row partial failure (force one row to violate a unique constraint), governor-unwind path (force SOQL>200 in execute), idempotency on retry (re-run on a Failed Record Staging row — must not duplicate). |
| **`PRM_OmniProcessUtils.cls`** | Apex (existing class) | Add new route alongside line 111: `if (methodName == 'enqueueParFormSubmission') { return PRM_ParFormSubmissionHelper.enqueueParFormSubmission(inputMap, outMap); }`. **No removal of existing routes.** |
| **`PRM_FailedRecordStaging__c`** | Custom Object (existing — confirm) | Add picklist value `PRM_ParFormSubmissionBatch` to `PRM_SourceFlow__c`. (US-PAR-05 will heavily use this.) |
| **`IndividualApplication`** | New custom field | `PRM_ParFormSubmissionStatus__c` — Picklist (restricted): `Not Started` (default), `Queued`, `Processing`, `Success`, `Partial Failure`, `Failed`. |

### B. Idempotency guard — what it looks like

Mirrors AC-5 from `US_DelegatedPractitioner_AddressCreation_BatchRefactor.md`. Inside `PRM_ParFormSubmissionHelper.enqueueParFormSubmission`:

```apex
Id caseManagerId = toId(input.get('caseManagerId'));
if (caseManagerId != null) {
    List<AsyncApexJob> recent = [
        SELECT Id, CreatedDate, Status
        FROM AsyncApexJob
        WHERE ApexClass.Name = 'PRM_ParFormSubmissionBatch'
          AND CreatedDate > :Datetime.now().addSeconds(-60)
          AND Status IN ('Queued', 'Holding', 'Preparing', 'Processing')
          AND JobItemsProcessed = 0
        ORDER BY CreatedDate DESC
        LIMIT 5
    ];
    // Optional: filter by envelope.caseManagerId via a custom field on AsyncApexJob
    //           OR query staging by caseManagerId to confirm prior in-flight run
    if (!recent.isEmpty()) {
        result.put('jobId', recent[0].Id);
        result.put('success', true);
        result.put('message', 'Submission already queued. You will be notified when it completes.');
        if (outMap != null) outMap.putAll(result);
        return result;
    }
}
```

### C. `PRM_ParFormSubmissionBatch` — implementation skeleton

```apex
public with sharing class PRM_ParFormSubmissionBatch
    implements Database.Batchable<SObject>, Database.Stateful {

    @TestVisible private final PRM_ParFormSubmissionEnvelope envelope;
    @TestVisible private Integer successCount = 0;
    @TestVisible private Integer failureCount = 0;
    @TestVisible private Integer inputRowsProcessed = 0;
    @TestVisible private List<String> failureMessages = new List<String>();

    // Stateful memoization — recovered SOQL per chunk after the first.
    // Identical pattern to PRM_NetworkCreationBatch.cachedHfNameToId.
    @TestVisible private Map<String, Id> cachedTaxonomyCodeToId = null;
    @TestVisible private Map<String, Id> cachedAccountByExternalIdToId = null;
    @TestVisible private Map<String, Id> cachedRecordTypeByDevName = null;
    @TestVisible private Id cachedFeatureConfigSettingId = null;

    public PRM_ParFormSubmissionBatch(PRM_ParFormSubmissionEnvelope envelope) {
        this.envelope = envelope;
    }

    public Iterable<SObject> start(Database.BatchableContext bc) {
        // One placeholder per submission row (envelope.rows). Real work reads
        // from envelope.rows; placeholders are never inserted. Same pattern
        // as PRM_NetworkCreationBatch.start() (lines 23-34).
        List<Account> placeholders = new List<Account>();
        if (envelope == null || envelope.rows == null) return placeholders;
        for (Integer i = 0; i < envelope.rows.size(); i++) placeholders.add(new Account());
        return placeholders;
    }

    public void execute(Database.BatchableContext bc, List<SObject> scope) {
        Integer chunkInputRowsAtStart = inputRowsProcessed;
        Integer chunkSizeAtStart = scope == null ? 0 : scope.size();
        try {
            // Slice envelope.rows into chunk (mirror PRM_NetworkCreationBatch.execute lines 50-59).
            Integer sliceStart = inputRowsProcessed;
            Integer sliceEnd = Math.min(sliceStart + chunkSizeAtStart, envelope.rows.size());
            List<PRM_ParFormSubmissionRow> slice = new List<PRM_ParFormSubmissionRow>();
            for (Integer i = sliceStart; i < sliceEnd; i++) slice.add(envelope.rows.get(i));
            inputRowsProcessed = sliceEnd;
            if (slice.isEmpty()) return;

            // Warm memoized lookups (first chunk only).
            if (cachedTaxonomyCodeToId == null) cachedTaxonomyCodeToId = warmTaxonomyCache(slice);
            if (cachedRecordTypeByDevName == null) cachedRecordTypeByDevName = warmRecordTypeCache();
            if (cachedFeatureConfigSettingId == null) cachedFeatureConfigSettingId = warmFeatureConfigSetting();

            for (PRM_ParFormSubmissionRow row : slice) {
                Savepoint sp = Database.setSavepoint();
                try {
                    ParFormCtx ctx = new ParFormCtx();
                    ctx.row = row;

                    // === The six sub-IP phases, in order ===
                    createPractitionerRecords(ctx);   // replaces seq 2 / seq 3 of the orchestrator
                    createGroupRecords(ctx);          // replaces seq 4
                    createAddressAndPPLRecords(ctx);  // replaces seq 5 DML (callouts already done in TX1)
                    createProviderRecords(ctx);       // replaces seq 6
                    createContactRecords(ctx);        // replaces seq 7
                    activateRecords(ctx);
                    linkCaseManager(ctx);

                    successCount++;
                } catch (Exception rowEx) {
                    Database.rollback(sp);
                    failureCount++;
                    failureMessages.add('Row failed: ' + row.npi + ' - ' + rowEx.getMessage());

                    // US-PAR-05: staging
                    insertStagingRow(row, rowEx, bc);
                    // US-PAR-02: rollback-safe exception event
                    publishExceptionLogEvent('PRM_ParFormSubmissionBatch.execute.row', rowEx, row, bc);
                }
            }
        } catch (Exception e) {
            // Pattern D — IA-0000150602 lesson: bump count BEFORE any DML.
            failureCount += chunkSizeAtStart;
            failureMessages.add('execute() threw: ' + e.getTypeName() + ' - ' + e.getMessage());
            try {
                publishExceptionLogEvent('PRM_ParFormSubmissionBatch.execute', e, null, bc);
                stageUnprocessedSlice(scope, e, bc);
            } catch (Exception loggerEx) {
                failureMessages.add('logger blocked: ' + loggerEx.getMessage());
            }
        }
    }

    public void finish(Database.BatchableContext bc) {
        String jobId = bc == null ? '' : String.valueOf(bc.getJobId());
        if (failureCount > 0) {
            publishExceptionLogEvent(
                'PRM_ParFormSubmissionBatch.finish', null, null, bc,
                'Batch completed with ' + failureCount + ' failure(s) and '
                + successCount + ' success(es). First failures: '
                + String.join(failureMessages, ' | ').abbreviate(4000)
            );
        }
        updateIndividualApplicationStatusAndNotify();
    }

    private void updateIndividualApplicationStatusAndNotify() {
        if (envelope == null || envelope.caseManagerId == null) return;
        try {
            String newStatus = (failureCount == 0)
                ? 'Success'
                : (successCount == 0 ? 'Failed' : 'Partial Failure');
            update new IndividualApplication(
                Id = envelope.caseManagerId,
                PRM_ParFormSubmissionStatus__c = newStatus
            );
            if (successCount == 0 && failureCount == 0) return; // skip noise — Pattern D

            // Bell notification — copy structure verbatim from
            // PRM_NetworkCreationBatch.updateCaseManagerStatusAndNotify().
            // …
        } catch (Exception e) {
            publishExceptionLogEvent('PRM_ParFormSubmissionBatch.finish.notify', e, null, bc);
        }
    }

    // Helpers — see implementation guide for full bodies.
    private void createPractitionerRecords(ParFormCtx ctx) { /* … */ }
    private void createGroupRecords(ParFormCtx ctx)         { /* … */ }
    private void createAddressAndPPLRecords(ParFormCtx ctx) { /* … */ }
    private void createProviderRecords(ParFormCtx ctx)      { /* … */ }
    private void createContactRecords(ParFormCtx ctx)       { /* … */ }
    private void activateRecords(ParFormCtx ctx)            { /* … */ }
    private void linkCaseManager(ParFormCtx ctx)            { /* … */ }

    private void publishExceptionLogEvent(String processName, Exception ex, PRM_ParFormSubmissionRow row, Database.BatchableContext bc, String overrideMessage) { /* US-PAR-02 */ }
    private void insertStagingRow(PRM_ParFormSubmissionRow row, Exception ex, Database.BatchableContext bc) { /* US-PAR-05 */ }
}
```

**Hard constraints (from the Delegated team's lessons):**

1. **`failureCount += chunkSizeAtStart`** before any DML in the outer catch — survives the SOQL=201 secondary unwind that killed IA-0000150602.
2. **Skip the bell notification when both counters are zero** (IA-0000150329 / IA-0000150310 noise fix).
3. **`PRM_FailedRecordStaging__c.PRM_SourceFlow__c = 'PRM_ParFormSubmissionBatch'`** so the Network Management QC list view can filter PAR-form failures separately.
4. **All memoized SOQL goes on instance variables** in the `Database.Stateful` batch — same as `cachedHfNameToId`.
5. **Per-row Savepoint** — atomic per submission. Multiple submissions in one chunk are still independently atomic.
6. **Catch-block logging via `PRM_ExceptionLogEvent__e`** (US-PAR-02), not direct DML — survives rollback.

### D. OmniStudio changes

#### D.1 `PRM_CreateParFormRecordsContainer_Procedure_1` v1 → v2

Replace the entire TryCatchBlock + IP_CreateParFormRecords subtree with **one Remote Action** + **one Response Action**:

| Seq | Element | Type | Notes |
|---:|---|---|---|
| 1.0 | `EnqueueParFormSubmission` (NEW) | Remote Action | `remoteClass=PRM_OmniProcessUtils`, `remoteMethod=callMethod`, `additionalInput.methodName='enqueueParFormSubmission'`, plus the full PAR payload from the OmniScript step JSON. Output node `ParFormBatch` → captures `jobId`, `success`, `message`, `caseManagerId`. |
| 2.0 | `Response` | Response Action | Passes `caseManagerId`, `individualApplicationId`, `jobId`, `success`, `message` to the OmniScript. |

Container `propertySetConfig`:
- `rollbackOnError = false` (was `true`). Container does no DML now, so rollback at this scope is irrelevant.
- `chainableCpuLimit` reduced from 2,000 to default — container body is one Remote Action.

#### D.2 `PRM_CreateParFormRecords_Procedure_29`

Set `isActive=false`. Keep the IP in the org for 30 days as a session backstop for any in-flight OmniScript sessions started against v1 of the container. Delete after 30 days.

Same disposition for the six child sub-IPs (`PRM_PractitionerScreenRecordCreation`, `PRM_PractitionerScreenExistingNPIRecordUpdation`, `PRM_CreateGroupScreenRecord`, `PRM_CreatePractitionerAddressRecords`, `PRM_CreateProviderScreenRecords`, `PRM_CreateContactScreenRecords`).

#### D.3 OmniScript `PRM_PractitionerParticipationForm_English` v111 → v112

| Element | Change |
|---|---|
| Final Submit IP Action (calls `PRM_CreateParFormRecordsContainer`) | No structural change — but now returns in <3 s. |
| **Show Toast** (immediately after Submit) | NEW. `variant=info`, `message="{{message}}"`. Sourced from container response. |
| **Navigate Action** (immediately after Show Toast) | NEW. `Target Type=SObject`, `Record Id={{caseManagerId}}`, `Action Name=view`. |
| Error path | If `success == false` → show sticky error toast with `message`, **do NOT navigate**. |

---

## Acceptance Criteria

**AC1 — Sub-3-second Submit.**
**Given** I am on `PRM_PractitionerParticipationForm_English` for a new practitioner submitting against 1 vendor with 3 practice locations and 2 taxonomies,
**When** I click **Submit**,
**Then** the Submit IP returns within **3 seconds (P95)** / **5 seconds (P99)**, **and** the OmniScript navigates me to the `IndividualApplication` (Case Manager) record page automatically.

**AC2 — Background batch completes atomically per submission.**
**Given** the batch has been enqueued,
**When** I refresh the Case Manager record ~60–120 s later,
**Then** `IA.PRM_ParFormSubmissionStatus__c = 'Success'`, **and** all six categories of records (practitioner Account + HCNPI + HCP + HCPT + Identifier; vendor Account + vendor HCP; HealthcareFacility + HPF + ContactPointAddress; provider features; contact records; case data manager) appear in their related lists, **and** I receive a bell notification titled "PAR Submission Complete" with the practitioner and vendor name in the body.

**AC3 — Atomic rollback on per-submission failure.**
**Given** the batch is processing a submission, and the `createGroupRecords` step throws a `DUPLICATE_VALUE` error (simulating a Cat B trigger collision — see US-PAR-04),
**When** the batch's per-row `Database.rollback(sp)` fires,
**Then** **NO** records from this submission exist in the database — no practitioner Account, no HCNPI, no HCP, no HCPT, no vendor Account, no HF, no HPF, no contact records — verified by querying `SELECT COUNT() FROM Account WHERE HealthCloudGA__SourceSystemId__c = :npi AND CreatedDate >= :batchStart` and confirming zero rows.

**AC4 — Partial-failure status when multiple submissions in one batch.**
**Given** a hypothetical 5-submission batch (future bulk-create scenario) where submission #3 fails and #1, #2, #4, #5 succeed,
**When** `finish()` runs,
**Then** the surviving 4 Case Managers have `PRM_ParFormSubmissionStatus__c='Success'`, submission #3's Case Manager has `'Failed'`, and a row exists in `PRM_FailedRecordStaging__c` for submission #3 with `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` and a populated `PRM_ExceptionLog__c` link.

**AC5 — Governor-unwind defence (the IA-0000150602 lesson).**
**Given** `execute()` exhausts SOQL or DML inside the per-row try block (e.g., a downstream trigger storm consuming all 200 SOQL),
**When** the outer catch fires,
**Then** `failureCount += chunkSizeAtStart` runs **before** any DML attempt, so even if subsequent staging / exception-event DML also fails, the `finish()` method sees `failureCount > 0` and sets `PRM_ParFormSubmissionStatus__c='Failed'` (not `'Success'`).

**AC6 — Idempotent re-submit guard.**
**Given** I accidentally hit Submit twice within 2 seconds,
**When** the second invocation reaches `PRM_ParFormSubmissionHelper.enqueueParFormSubmission`,
**Then** the helper detects a recently enqueued job for the same `CaseManagerId` (AsyncApexJob lookup within last 60 s) and returns `{ success: true, jobId: <existing>, message: 'Already queued' }` without enqueueing a second batch.

**AC7 — Cross-batch overall status roll-up.**
**Given** a PAR submission whose downstream `PRM_NetworkCreationBatch` is also expected to run (when the practitioner has network assignments),
**Then** `IA.PRM_ProcessingStatus__c` is `Success` only if BOTH `PRM_ParFormSubmissionStatus__c='Success'` AND `PRM_NetworkCreationStatus__c='Success'`. Otherwise it reflects the worst of the two (Failed > Partial Failure > Success > Queued). Roll-up logic mirrors the AC6 of `US_DelegatedPractitioner_AddressCreation_BatchRefactor.md`.

**AC8 — Backwards compatibility on in-flight sessions.**
**Given** I open an in-flight OmniScript session that was started against `PRM_CreateParFormRecordsContainer` v1 (the previous synchronous behaviour),
**When** I submit,
**Then** v1 is still active (`isActive=true`) for 30 days post-deployment as a fallback. The OmniScript v111 sessions continue to work; new sessions use v112 → v2 container.

**AC-MAX — Maximum-scale single submission completes in one chunk inside governor limits.**
**Given** a PAR submission with the maximum payload supported by the OmniScript today (5 groups × 10 locations per group, 4 licenses, 2 contacts — see `US_PAR_ScaleAudit_5Groups_10Locations.md` for the exact entity-count breakdown of ~490 records across ~15 object types),
**When** `PRM_ParFormSubmissionBatch.execute(scope = [thisSubmission])` runs,
**Then** the transaction completes within **6 seconds CPU**, with `Limits.getDMLStatements() ≤ 20`, `Limits.getDMLRows() ≤ 600`, `Limits.getQueries() ≤ 50`, `Limits.getCallouts() == 0`, no `LimitException` raised, and `IA.PRM_ParFormSubmissionStatus__c = 'Success'`. A `Limits.*` snapshot is logged at the end of `execute()` via `System.debug(LoggingLevel.INFO, ...)` so this AC can be verified from QA debug logs.

**AC9 — No new partial-data accumulators.**
**Given** the new batch is live for 14 calendar days post-deployment,
**Then**:
- New `PRM_OmniUtils.updatePPLAddresesForPAR()` null-input throws: **0**
- New HCPT duplicate `(AccountId, TaxonomyId)` pairs created: **0** (assuming US-PAR-04 has shipped — without it this AC slips)
- New `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` NPEs: **0** (same caveat)
- Practitioners with multiple PAR IAs created within 60 s of each other: **0** (AC6 prevents)

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | What is the **average** and **P95** number of vendors / practice locations / taxonomies per PAR submission in production today? | Determines chunkSize tuning and CPU budgeting. | Product / Operations |
| 2 | Is `IA.PRM_ProcessingStatus__c` already deployed via the Delegated stories, or do we need to add it? Same question for `PRM_AddressCreationStatus__c` and `PRM_NetworkCreationStatus__c`. | If not deployed yet, US-PAR-01 either adds it or blocks on those stories. | Technical Lead |
| 3 | For PAR (intake) submissions, who should receive the bell notification — `UserInfo.getUserId()` (the intake user) or the `OwnerId` of the Case Manager (often a queue)? | Affects AC2 wording. | Operations Lead |
| 4 | Should the batch support **partial-rollback** (delete submission #N's already-created records if a later step in that same submission fails)? Current design uses a per-submission Savepoint, which IS partial rollback — confirm. | Confirms the Savepoint approach is acceptable. | Apex Lead |
| 5 | Are there any out-of-process consumers (real-time API, DDP feed) that today read `Account` / `HealthcareProvider` records **during** the OmniScript turn, before our refactor would have moved that DML to async? | Could break when work moves async (records appear 30–120 s later). | API / Integrations Lead |
| 6 | Does the OmniScript Navigate Action work cleanly across all the user surfaces PAR is launched from today (Experience Cloud portal, internal Lightning app, etc.)? | If portal users see a different navigation experience, AC1 wording needs to adapt. | UX Lead |
| 7 | Should the helper's idempotency guard window be 60 s (mirrors Delegated) or longer (some users hit Submit again 5+ minutes later when nothing visibly happened)? | Trade-off between blocking a legitimate re-submit-after-failure and preventing accidental duplicates. Could be a Custom Metadata setting. | Product / Operations |
| 8 | How do we want to handle `PractitionerCreationType='IBC Professional Staff'` (per `PRMDRCreateCaseCaseManagerAndAccount` line 379, this branch sets `CredentialingStatus='Credentialed'` and may need to set `IsActive=true` at creation time)? Does that path even go through PAR? | Determines whether the batch needs branch-specific logic. | PNM SME |
| 9 | What is the chunk size that proved stable for `PRM_NetworkCreationBatch` in production (default is 50)? Address Creation proposes 5. PAR is heavier — propose 1. Validate via sandbox load test. | AC1 (perf), AC5 (governor unwind). | Performance / Apex Lead |
| 10 | Should we ALSO keep the existing IPs as fallback (`isActive=true`) and add a Custom Metadata toggle to switch between the IP chain and the batch (canary rollout)? Or hard cutover? | Risk management for production deployment. | Release Manager |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_ParFormSubmissionEnvelope.cls` / `Row.cls` | Apex POJO (NEW) | **MEDIUM** | ~30 fields between them; modelled on `PRM_NetworkCreationEnvelope/Row`. |
| `PRM_ParFormSubmissionHelper.cls` | Apex (NEW) | **HIGH** | Sole entry from OmniStudio; idempotency guard. |
| `PRM_ParFormSubmissionBatch.cls` | Apex (NEW) | **VERY HIGH** | Replaces the bodies of 6 sub-IPs. Single biggest piece of new code in the roadmap. |
| `PRM_ParFormSubmissionBatchTest.cls` + helper test | Apex tests (NEW) | **HIGH** | ≥ 90% coverage; 5 path scenarios. |
| `PRM_OmniProcessUtils.cls` | Apex (existing) | **LOW** | One new `if`-branch. |
| `PRM_CreateParFormRecordsContainer_Procedure_1` v2 | IP version (NEW) | **HIGH** | Body collapses from TryCatchBlock + IP_CreateParFormRecords tree to one Remote Action. |
| `PRM_CreateParFormRecords_Procedure_29` | IP (existing) | **HIGH** | `isActive=false`; the six child sub-IPs same disposition. |
| `PRM_PractitionerParticipationForm_English` v112 | OmniScript (NEW version) | **MEDIUM** | Add Show Toast + Navigate Action; error branch. |
| `IndividualApplication.PRM_ParFormSubmissionStatus__c` | Custom Field (NEW) | **MEDIUM** | Picklist + page layout + list view filter. |
| `PRM_FailedRecordStaging__c.PRM_SourceFlow__c` | Picklist value add | **LOW** | One new value `PRM_ParFormSubmissionBatch`. |
| Cross-batch roll-up of `IA.PRM_ProcessingStatus__c` (AC7) | Apex update | **MEDIUM** | Edit to `PRM_NetworkCreationBatch.finish()` AND new logic in `PRM_ParFormSubmissionBatch.finish()`. |
| QTA / FIT regression updates | Tests | **MEDIUM** | Submit-timing + navigate assertions. |
| Out-of-process consumers of Account/HCP/HCNPI within OmniScript turn | External | **MEDIUM** | Now records appear async — see Clarification #5. |

---

## Estimated Effort

| Component | Type | Effort | Notes |
|---|---|---|---|
| `PRM_ParFormSubmissionEnvelope.cls` | Apex POJO (NEW) | **S** (< 1 hr) | Clone of `PRM_NetworkCreationEnvelope`. |
| `PRM_ParFormSubmissionRow.cls` | Apex POJO (NEW) | **M** (2–4 hrs) | ~30 fields; map from OmniScript step JSON. |
| `PRM_ParFormSubmissionHelper.cls` | Apex (NEW) | **L** (4–8 hrs) | Parse + idempotency guard + executeBatch. |
| `PRM_ParFormSubmissionBatch.cls` | Apex (NEW) | **XXL** (5+ days) | The XL piece. Replicates 6 sub-IPs of OmniStudio DML in Apex. Per-row Savepoint, governor-unwind guard, memoized lookups, partial-failure staging. |
| `PRM_ParFormSubmissionHelperTest.cls` | Apex tests (NEW) | **M** (2–4 hrs) | Idempotency + null-guard + happy path. |
| `PRM_ParFormSubmissionBatchTest.cls` | Apex tests (NEW) | **XL** (1.5–2 days) | 5 scenarios incl. governor-unwind, partial failure, rollback verification, retry idempotency. |
| `PRM_OmniProcessUtils.cls` route add | Apex (existing) | **S** (< 1 hr) | One `if`. |
| `PRM_CreateParFormRecordsContainer_Procedure_1` v2 | IP version (NEW) | **L** (4–8 hrs) | Strip body to one Remote Action + Response. |
| Deactivate `PRM_CreateParFormRecords_Procedure_29` + 6 child sub-IPs | IP config | **S** (< 1 hr) | Set `isActive=false` + 30-day deletion calendar entry. |
| `PRM_PractitionerParticipationForm_English` v112 | OmniScript version (NEW) | **L** (4–8 hrs) | Navigate + Show Toast + error branch. |
| `IA.PRM_ParFormSubmissionStatus__c` | Custom Field (NEW) | **S** (< 1 hr) | Picklist + permission set. |
| `PRM_FailedRecordStaging__c.PRM_SourceFlow__c` picklist value | Config | **S** (< 1 hr) | One value. |
| Cross-batch roll-up logic for `PRM_ProcessingStatus__c` | Apex update | **L** (4–8 hrs) | Two batch finish() updates OR new `PRM_PostSubmitStatusEvaluator` queueable. |
| Sandbox + UAT smoke + perf (1/3/10 location variants) | QA / Perf | **L** (4–8 hrs) | Capture P50/P95/P99 + governor usage. |
| QTA / FIT updates | Tests | **M** (2–4 hrs) | Submit timing + navigate assertions. |

**Total Estimated Effort:** **~12–15 person-days** — overall **XL** sprint slice (one developer over ~3 weeks, or two developers in parallel over ~1.5 weeks). The `PRM_ParFormSubmissionBatch.cls` line item is the single largest unknown; size depends on how cleanly the existing DR + Apex remote actions inside sub-IPs 2–7 can be ported to Apex DML.

---

## Deployment Checklist

**Pre-requisites (must be live BEFORE this story can ship):**
- [ ] **US-PAR-04** (Trigger Idempotency) deployed — batch retries must not duplicate
- [ ] **US-PAR-02** (Exception Logging via Platform Event) deployed — batch catch block depends on it
- [ ] **US-PAR-03** (Pre-Submit Callout Phase) deployed — batch must be pure DML (no callouts)
- [ ] `IndividualApplication.PRM_ParFormSubmissionStatus__c` deployed
- [ ] `PRM_FailedRecordStaging__c.PRM_SourceFlow__c` includes value `PRM_ParFormSubmissionBatch`
- [ ] (If not already live) `IA.PRM_ProcessingStatus__c` from Delegated stories deployed

**Metadata (deploy in order):**
- [ ] Apex POJOs (`Envelope`, `Row`)
- [ ] Apex `Helper` + `HelperTest`
- [ ] Apex `Batch` + `BatchTest`
- [ ] `PRM_OmniProcessUtils.cls` route addition (with full regression test pass)
- [ ] `PRM_CreateParFormRecordsContainer_Procedure_1` v2
- [ ] `PRM_PractitionerParticipationForm_English` v112
- [ ] Deactivate `PRM_CreateParFormRecords_Procedure_29` and 6 child sub-IPs

**Verification in Sandbox:**
- [ ] 1-vendor / 1-location / 1-taxonomy happy path — P95 < 3 s
- [ ] 1-vendor / 3-location / 3-taxonomy happy path — P95 < 5 s
- [ ] **Max-scale load test (AC-MAX): 5 groups × 10 locations × 4 licenses × 2 contacts** — single submission. Build `TestDataFactory.buildMaxScaleEnvelope()`, run `Database.executeBatch(new PRM_ParFormSubmissionBatch(env), 1)`, scrape `Limits.*` snapshot from debug log. Verify CPU ≤ 6 s, DML statements ≤ 20, DML rows ≤ 600, SOQL ≤ 50, callouts == 0. Run this **weekly** in QA as a regression backstop — if any limit creeps above threshold, alarm and triage before production deploy.
- [ ] Force `DUPLICATE_VALUE` mid-submission — verify atomic rollback (AC3)
- [ ] Force SOQL=201 in execute — verify `failureCount += chunkSizeAtStart` works (AC5)
- [ ] Double-Submit within 2 s — verify idempotency guard returns existing jobId (AC6)
- [ ] Cross-batch status roll-up — submit with both PAR + Network in scope, verify AC7
- [ ] Backwards compatibility: open OmniScript v111 session, submit, verify v1 container still works (AC8)

**Post-Deployment Monitoring (first 30 days):**
- [ ] Daily run of `scripts/apex/parform_orphan_detect.apex` (v2) — confirm `updatePPLAddresesForPAR()` throws drop to 0
- [ ] Daily check of `PRM_FailedRecordStaging__c WHERE PRM_SourceFlow__c='PRM_ParFormSubmissionBatch' AND CreatedDate=LAST_N_DAYS:1` — confirm trend
- [ ] Weekly check of new HCPT duplicate junctions — target 0 (depends on US-PAR-04 also being live)
- [ ] Weekly count of `IA.PRM_ParFormSubmissionStatus__c IN ('Failed','Partial Failure')` — analyse causes

---

## Related Stories

| Story | Priority | Relationship |
|---|---|---|
| `US-PAR-02` (Exception Logging via Platform Event) | P0 | **Hard pre-req** — batch catch block uses `EventBus.publish()` |
| `US-PAR-03` (Pre-Submit Callout Phase) | P0 | **Hard pre-req** — batch cannot violate no-callout-after-DML |
| `US-PAR-04` (Trigger Idempotency) | P0 | **Hard pre-req** — batch retries collide otherwise |
| `US-PAR-05` (Failed Record Staging + Retry UX) | P1 | **Co-deliverable** — batch writes the staging rows; this story builds the UX on top |
| `US_DelegatedPractitioner_AddressCreation_BatchRefactor.md` | P0 (in flight) | **Blueprint** — direct architectural reference |
| `US_PractitionerCreation_QueueableRefactor.md` | P0 (in flight) | **Blueprint** — exception event infrastructure |
| `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` | P0 (in flight) | **Sibling** — same underlying duplicate-error symptoms; this story is the long-term arch fix while that one cleans the existing 16 cases |
