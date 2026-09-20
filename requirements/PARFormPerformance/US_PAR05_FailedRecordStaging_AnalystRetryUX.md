# USER STORY US-PAR-05: PAR Form — Per-Row Failure Staging + Analyst Retry UX

**Persona:** Sr. Data Reporting Analyst, Operations Lead, Network Management QC Analyst
**Priority:** P1 — UX polish that sits on top of US-PAR-01; without it, US-PAR-01's per-row failures end up as untriaged exception logs with no clear retry path; **co-deliverable** with US-PAR-01 ideally
**Vertical:** Provider Network Management (PNM)
**OmniScript / UI:**
- `IndividualApplication` (Case Manager) page — add Failed Record Staging related list + Retry Quick Action
- NEW `PRM_ParFormRetryAction` Quick Action on Case Manager (calls a new IP that re-enqueues the original envelope)
- (Optional) NEW LWC `prmParFormFailureRetryPanel` — displays the structured error and the "Retry" / "Mark Terminal" buttons

**Apex (impacted):**
- `PRM_ParFormSubmissionBatch.cls` (from US-PAR-01) — its per-row catch block writes the staging rows (this story finalises the contract on what those rows contain)
- NEW `PRM_ParFormRetryService.cls` — encapsulates the retry logic (reads a staging row, rebuilds the envelope, calls the helper)
- `PRM_FailedRecordStagingTriggerHandler.cls` (existing or NEW) — when staging row transitions to `PRM_Status__c='Fixed'`, optionally auto-retry (or wait for manual retry — configurable)
- `PRM_AccessControlUtils.cls` (or equivalent) — check that the user invoking the retry has the right permission

**Integration Procedures (impacted):**
- NEW `PRM_ParFormRetryFromStaging_Procedure_1` — invoked by the Quick Action; calls `PRM_ParFormRetryService.retryFromStaging(stagingId)`

**Custom Object (impacted):**
- `PRM_FailedRecordStaging__c` — confirm `PRM_SourceFlow__c` picklist includes `PRM_ParFormSubmissionBatch` (from US-PAR-01); confirm `PRM_ExceptionLog__c` lookup field is present; confirm `PRM_RetryCount__c` is increment-only

**Permission Sets:**
- `PRM_CredentialingUser`, `PRM_DataAdmin`, or whichever sets need retry privilege

**Relevant requirements:** `00_Overview_PARForm_BatchRefactor_Roadmap.md`, `US-PAR-01`, `US-PAR-04`, `requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md`, `US_DataAdmin_NetworkError_ListViewAndQCRouting.md` (the analogous retry UX for the Network/Delegated team)

---

## Story

**As a** Sr. Data Reporting Analyst handling escalations from `PRM_ParFormSubmissionBatch` per-row failures,
**I want** every per-row failure inside the PAR batch to produce a `PRM_FailedRecordStaging__c` row linked to the originating Case Manager, with the full envelope payload preserved, the structured error message from the trigger or downstream code captured, and a one-click "Retry" Quick Action on the Case Manager record,
**So that** I can triage failed PAR submissions from the Case Manager record without writing SOQL, fix the underlying data issue (correct an NPI, fix an address, merge a duplicate vendor), and re-submit the original envelope through the same batch — no need to ask the user to fill out the form again, no need to manually re-create the records.

**Why it matters:** US-PAR-01 ships the batch and writes per-row failure rows to `PRM_FailedRecordStaging__c`. Without US-PAR-05, those rows are just inert audit records — the analyst sees the failure existed but has no path forward. The Network Management QC team already operates this pattern for `PRM_NetworkCreationBatch` failures (see `US_DataAdmin_NetworkError_ListViewAndQCRouting.md`): list-view filtered by `PRM_SourceFlow__c='PRM_NetworkCreationBatch'`, click a Retry button, the batch re-runs against the original envelope. We are extending that pattern to PAR. **The architectural infrastructure already exists** — `PRM_FailedRecordStaging__c` object, `PRM_Status__c` lifecycle (Pending → Under Review → Fixed → Retried → Failed-Terminal), `PRM_RetryCount__c` — we just need to wire PAR into it.

---

## Scope

| Layer | Component | Change |
|---|---|---|
| Apex | `PRM_ParFormRetryService.cls` (NEW) | Reads a staging row, reconstructs the envelope from `PRM_RequestPayload__c`, calls `PRM_ParFormSubmissionHelper.enqueueParFormSubmission(...)` with an `isRetry=true` flag |
| Apex | `PRM_ParFormSubmissionHelper.cls` (from US-PAR-01) | Accepts `isRetry` parameter; on retry, skips the idempotency-guard time window (analyst-initiated retries should not be blocked by the 60-second guard) |
| Apex | `PRM_FailedRecordStagingTriggerHandler.cls` | When a staging row transitions to `PRM_Status__c='Fixed'` AND `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'`, optionally auto-enqueue a retry. Behind a Custom Metadata toggle. |
| OmniStudio | `PRM_ParFormRetryFromStaging_Procedure_1` (NEW) | Wraps the Apex retry service for the Quick Action |
| UI | Quick Action on `IndividualApplication` | `Retry PAR Submission` — invokes the new IP, shows a confirmation modal |
| UI | Quick Action on `PRM_FailedRecordStaging__c` | `Retry from Staging` — same backend, action runs from the staging row level |
| UI | Page Layouts | Add `PRM_FailedRecordStaging__c` related list to `IndividualApplication` page layout (Case Manager) — display Status, Error Message, Retry Count, Last Retry Date |
| UI | LWC (optional) | `prmParFormFailureRetryPanel` — embeddable panel on the Case Manager page that surfaces the most recent failure with a "Retry" button |
| Permission Sets | `PRM_CredentialingUser`, etc. | Read on `PRM_FailedRecordStaging__c`; Edit on `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_ErrorMessage__c`; Execute on the Quick Action |
| Tests | `PRM_ParFormRetryServiceTest.cls` (NEW) | ≥ 90% coverage: happy-path retry, retry exceeds max attempts (3), permission denied path, envelope rebuild integrity |

---

## Current State (verified)

### `PRM_FailedRecordStaging__c` (per spec at `requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md`)

Fields relevant here:
- `Name` — auto-number `FST-{00000}`
- `PRM_Status__c` — Pending / Under Review / Fixed / Retried / Failed - Terminal / Archived / Cancelled
- `PRM_RetryCount__c` — Number(2,0), max 99, Terminal at 3
- `PRM_NextRetryDate__c` — DateTime, scheduled retry
- `PRM_LastRetryDate__c` — DateTime
- `PRM_TargetObject__c` — string (e.g., `IndividualApplication`)
- `PRM_ParentRecordId__c` — string Id of the parent record (e.g., CaseManagerId)
- `PRM_CaseManager__c` — lookup to IA (per existing `PRM_NetworkCreationBatch.buildStagingRow` line 566)
- `PRM_SourceFlow__c` — picklist; existing values include `PRM_NetworkCreationBatch`; **NEW value `PRM_ParFormSubmissionBatch` added by US-PAR-01**
- `PRM_RequestPayload__c` — LongTextArea(131072) — full envelope JSON
- `PRM_ErrorMessage__c` — LongTextArea(32768) — captured error
- `PRM_ExceptionLog__c` — lookup to PRM_ExceptionLog__c (from US-PAR-02)

`PRM_NetworkCreationBatch.buildStagingRow` (line 559–573) is the reference implementation we will mirror.

### `US_DataAdmin_NetworkError_ListViewAndQCRouting.md` (the Network team's analogous story)

The Network team already built the list-view + retry-routing UX for `PRM_NetworkCreationBatch` failures. Their pattern:
1. List view on `PRM_FailedRecordStaging__c` filtered by `PRM_SourceFlow__c='PRM_NetworkCreationBatch' AND PRM_Status__c IN ('Pending', 'Under Review', 'Fixed')`
2. Quick Action on the list view rows for "Retry Selected"
3. Quick Action on individual staging records for "Retry This"
4. Auto-retry via a Schedulable Apex job when `PRM_NextRetryDate__c <= NOW`

We are copying that pattern.

### What is NOT in scope (out-of-scope)

- A general "PAR submission history" timeline view on the Case Manager (could be a follow-on story)
- Bulk-retry-all-pending across an entire vendor / day (could be a follow-on; the Network team has it via list-view Quick Action; PAR can defer)
- Email notifications on auto-retry results (could be a follow-on)

---

## Proposed Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. PRM_ParFormSubmissionBatch.execute()'s per-row catch (from US-PAR-01)│
│    On failure of submission row N:                                     │
│       PRM_FailedRecordStaging__c stagingRow = new PRM_FailedRecordStaging__c(
│         PRM_Status__c          = 'Pending',
│         PRM_TargetObject__c    = 'IndividualApplication',
│         PRM_ParentRecordId__c  = envelope.caseManagerId,
│         PRM_CaseManager__c     = envelope.caseManagerId,
│         PRM_SourceFlow__c      = 'PRM_ParFormSubmissionBatch',
│         PRM_RequestPayload__c  = JSON.serialize(envelope).abbreviate(131072),
│         PRM_ErrorMessage__c    = ex.getMessage().abbreviate(32768),
│         PRM_ExceptionLog__c    = exceptionLogId,   // from US-PAR-02
│         PRM_RetryCount__c      = 0
│       );
│    insert stagingRow;                                                  │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Case Manager record page                                            │
│    "Failed Record Staging" related list shows the staging row.         │
│    User clicks "Retry PAR Submission" Quick Action on the IA OR clicks │
│    the row → "Retry from Staging" Quick Action.                        │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. Quick Action → OmniScript modal:                                    │
│    "You are about to retry PAR submission for Dr. Smith (NPI ...).      │
│     Retry count: 1 of 3.                                                │
│     [Show structured error: PRM_HCPROVIDER_EXISTS::0bSUW...::...]       │
│     [Cancel]  [Retry Now]"                                              │
│    → invokes PRM_ParFormRetryFromStaging_Procedure_1                    │
│      → PRM_OmniProcessUtils.callMethod('retryParFormFromStaging', ...)  │
│        → PRM_ParFormRetryService.retryFromStaging(stagingId)            │
│            • SELECT staging row (validate not Archived/Terminal/Retried) │
│            • Increment PRM_RetryCount__c                                │
│            • Update PRM_LastRetryDate__c = NOW                          │
│            • Update PRM_Status__c = 'Under Review' (interim)            │
│            • Deserialize PRM_RequestPayload__c → PRM_ParFormSubmissionEnvelope │
│            • PRM_ParFormSubmissionHelper.enqueueParFormSubmission(envelope, isRetry=true) │
│            • Update PRM_Status__c = 'Retried' (after enqueue success)   │
│            • Return { success, jobId, retryCount, message }             │
│      → OmniScript shows toast: "Retry enqueued. Job: <id>. We'll notify │
│         you when it completes."                                         │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. Batch completes (success / partial / failure) — bell notification    │
│    from PRM_ParFormSubmissionBatch.finish() — same as the original      │
│    submission. If successful, the staging row stays at 'Retried'. If    │
│    the retry fails AGAIN, a NEW staging row is created by the batch's   │
│    per-row catch (the original row remains at 'Retried' for audit; the  │
│    new row starts at 'Pending'). The new row links back to the original │
│    via a self-lookup PRM_ParentStaging__c (NEW field on staging).       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Section (For Developers)

### A. `PRM_ParFormRetryService.cls` (NEW)

```apex
public with sharing class PRM_ParFormRetryService {

    public class RetryResult {
        public Boolean success;
        public Id jobId;
        public Integer retryCount;
        public String message;
    }

    /**
     * Retry a PAR submission from its staging row. Increments retry count,
     * updates lifecycle status, and enqueues the batch with the original
     * envelope.
     *
     * @param stagingId The PRM_FailedRecordStaging__c.Id to retry.
     * @return RetryResult containing success/jobId/retryCount/message.
     */
    public static RetryResult retryFromStaging(Id stagingId) {
        RetryResult result = new RetryResult();
        result.success = false;
        try {
            // 1. Fetch staging row
            List<PRM_FailedRecordStaging__c> rows = [
                SELECT Id, PRM_Status__c, PRM_RetryCount__c,
                       PRM_SourceFlow__c, PRM_RequestPayload__c,
                       PRM_CaseManager__c, PRM_ErrorMessage__c
                FROM PRM_FailedRecordStaging__c
                WHERE Id = :stagingId
                LIMIT 1
                FOR UPDATE
            ];
            if (rows.isEmpty()) {
                result.message = 'Staging row not found: ' + stagingId;
                return result;
            }
            PRM_FailedRecordStaging__c row = rows[0];

            // 2. Guards
            if (row.PRM_SourceFlow__c != 'PRM_ParFormSubmissionBatch') {
                result.message = 'Staging row source flow ' + row.PRM_SourceFlow__c
                    + ' is not PRM_ParFormSubmissionBatch; cannot retry via this service.';
                return result;
            }
            if (row.PRM_Status__c == 'Retried' || row.PRM_Status__c == 'Archived'
                || row.PRM_Status__c == 'Cancelled') {
                result.message = 'Staging row in terminal/closed state: ' + row.PRM_Status__c;
                return result;
            }
            Integer currentCount = (row.PRM_RetryCount__c == null) ? 0 : row.PRM_RetryCount__c.intValue();
            if (currentCount >= 3) {
                row.PRM_Status__c = 'Failed - Terminal';
                update row;
                result.message = 'Retry count exceeded (3 attempts). Marked Failed - Terminal.';
                return result;
            }

            // 3. Permission check
            if (!Schema.sObjectType.PRM_FailedRecordStaging__c.isUpdateable()
                || !Schema.sObjectType.PRM_FailedRecordStaging__c.fields.PRM_RetryCount__c.isUpdateable()) {
                result.message = 'Insufficient permissions to update staging row.';
                return result;
            }

            // 4. Increment + interim status
            row.PRM_RetryCount__c = currentCount + 1;
            row.PRM_LastRetryDate__c = Datetime.now();
            row.PRM_Status__c = 'Under Review';
            update row;

            // 5. Deserialize envelope
            PRM_ParFormSubmissionEnvelope envelope =
                (PRM_ParFormSubmissionEnvelope) JSON.deserialize(
                    row.PRM_RequestPayload__c,
                    PRM_ParFormSubmissionEnvelope.class
                );

            // 6. Re-enqueue (bypass idempotency guard — analyst-initiated)
            Map<String, Object> input = new Map<String, Object>{
                'envelope' => envelope,
                'isRetry'  => true,
                'parentStagingId' => row.Id
            };
            Map<String, Object> outMap = new Map<String, Object>();
            Map<String, Object> enqueueResult = PRM_ParFormSubmissionHelper.enqueueParFormSubmission(input, outMap);
            Boolean enqueueOk = (Boolean) enqueueResult.get('success');
            Id jobId = (Id) enqueueResult.get('jobId');

            // 7. Update staging row to Retried (or back to Pending if enqueue failed)
            if (enqueueOk) {
                row.PRM_Status__c = 'Retried';
                update row;
                result.success = true;
                result.jobId = jobId;
                result.retryCount = (Integer) row.PRM_RetryCount__c;
                result.message = 'Retry enqueued. Job ' + jobId
                    + '. You will be notified when it completes.';
            } else {
                row.PRM_Status__c = 'Pending';   // revert to allow another retry
                row.PRM_ErrorMessage__c = String.valueOf(enqueueResult.get('errorMessage')).abbreviate(32768);
                update row;
                result.message = 'Retry enqueue failed: '
                    + enqueueResult.get('errorMessage');
            }
        } catch (Exception e) {
            PRM_ExceptionLogger.logExceptionViaEvent(
                'PRM_ParFormRetryService.retryFromStaging', 'SYNC', 'Error',
                e.getStackTraceString(), e.getMessage(), e.getTypeName(),
                e.getLineNumber(), '', '', 'Salesforce', 'Salesforce', '',
                null);
            result.message = 'Retry service error: ' + e.getMessage();
        }
        return result;
    }
}
```

### B. `PRM_FailedRecordStaging__c` field additions

| API Name | Type | Description |
|---|---|---|
| `PRM_ParentStaging__c` | Lookup (self, to `PRM_FailedRecordStaging__c`) | When a retry creates a NEW staging row (because the retry itself failed), this lookup links back to the original row so the audit chain is preserved. Optional / nullable. |
| `PRM_RetriedByUserId__c` | Lookup (User) | Who clicked Retry. Useful for audit. |

These are the only schema additions on top of the existing spec.

### C. `PRM_ParFormSubmissionHelper.cls` (extension from US-PAR-01)

Adds an `isRetry` mode:

```apex
public static Map<String, Object> enqueueParFormSubmission(Map<String, Object> input, Map<String, Object> outMap) {
    // ... existing logic ...
    Boolean isRetry = input.get('isRetry') == true;
    Id caseManagerId = ...;
    if (!isRetry && caseManagerId != null) {
        // Apply 60-second idempotency guard (Pattern F)
        // ...
    }
    // For retries, skip the guard — analyst explicitly clicked retry.
    // ...
}
```

### D. `PRM_FailedRecordStagingTriggerHandler.cls` — optional auto-retry

If Custom Metadata `PRM_FailedRecordRetry__mdt.AutoRetryEnabled__c = true` for the `PRM_ParFormSubmissionBatch` source flow, then when a staging row transitions from `Under Review` to `Fixed`, automatically enqueue a retry via the `PRM_ParFormRetryService.retryFromStaging` method.

#### D.0 Throttle and in-flight guard (REQUIRED by AC-RETRY-THROTTLE + AC-RETRY-IDEMPOTENT)

Auto-retry MUST throttle and guard against in-flight duplication, because at max PAR scale (~490 rows per submission) any unbounded fan-out exhausts the org's 5-batch concurrent slot in seconds. New fields on `PRM_FailedRecordStaging__c` for the guard:

| Field | Type | Purpose |
|---|---|---|
| `PRM_RetryJobId__c` | Lookup to `AsyncApexJob` (or Text(18) if Lookup not permitted) | The most recent batch job spawned by an auto-retry of this row. Used by the in-flight guard. |
| `PRM_RetryJobStatus__c` | Picklist `Queued, Processing, Completed, Failed, Aborted, Holding` | Cached AsyncApexJob.Status — refreshed by an `after update` on AsyncApexJob (or polled). |

Throttled scheduled retry job:

```apex
public class PRM_ParFormAutoRetryScheduled implements Schedulable {
    // AC-RETRY-THROTTLE: cap is 3 — leaves 2 of the org's 5 concurrent-batch slots
    // for PRM_NetworkCreationBatch and other batches.
    private static final Integer MAX_PARALLEL_BATCHES = 3;

    public void execute(SchedulableContext sc) {
        Integer inFlight = [
            SELECT COUNT() FROM AsyncApexJob
            WHERE ApexClass.Name = 'PRM_ParFormSubmissionBatch'
              AND Status IN ('Queued', 'Processing', 'Preparing', 'Holding')
        ];
        if (inFlight >= MAX_PARALLEL_BATCHES) return;  // wait for next window
        Integer slots = MAX_PARALLEL_BATCHES - inFlight;

        // AC-RETRY-IDEMPOTENT: filter out rows whose retry is still running
        List<PRM_FailedRecordStaging__c> rows = [
            SELECT Id, PRM_EnvelopePayload__c, PRM_IndividualApplication__c, PRM_RetryJobId__c
            FROM PRM_FailedRecordStaging__c
            WHERE PRM_Status__c = 'Awaiting Retry'
              AND PRM_SourceFlow__c = 'PRM_ParFormSubmissionBatch'
              AND (PRM_RetryJobId__c = NULL
                   OR PRM_RetryJobStatus__c IN ('Completed','Failed','Aborted'))
            ORDER BY CreatedDate ASC
            LIMIT :slots
        ];
        for (PRM_FailedRecordStaging__c row : rows) {
            PRM_ParFormSubmissionEnvelope env = (PRM_ParFormSubmissionEnvelope)
                JSON.deserialize(row.PRM_EnvelopePayload__c, PRM_ParFormSubmissionEnvelope.class);
            Id jobId = PRM_ParFormSubmissionHelper.enqueue(env);
            row.PRM_RetryJobId__c = jobId;
            row.PRM_RetryJobStatus__c = 'Queued';
            row.PRM_Status__c = 'Retry In Flight';
        }
        update rows;
    }
}
```

The manual Quick Action `PRM_ParFormRetryService.retryFromStaging(stagingId)` also honors the in-flight guard — if `PRM_RetryJobId__c` is populated and its `AsyncApexJob.Status` is not terminal, the service throws a clear `AuraHandledException("Retry already in flight (job " + jobId + "); refresh in 30 s")` rather than enqueuing a second batch.

```apex
public class PRM_FailedRecordStagingTriggerHandler {
    public static void handleAfterUpdate(List<PRM_FailedRecordStaging__c> newList, Map<Id, PRM_FailedRecordStaging__c> oldMap) {
        // ... existing logic if any ...
        List<Id> toAutoRetry = new List<Id>();
        for (PRM_FailedRecordStaging__c row : newList) {
            PRM_FailedRecordStaging__c oldRow = oldMap.get(row.Id);
            if (oldRow == null) continue;
            if (row.PRM_Status__c == 'Fixed'
                && oldRow.PRM_Status__c != 'Fixed'
                && row.PRM_SourceFlow__c == 'PRM_ParFormSubmissionBatch') {
                if (PRM_FailedRecordRetry__mdt.getInstance(row.PRM_SourceFlow__c)?.AutoRetryEnabled__c == true) {
                    toAutoRetry.add(row.Id);
                }
            }
        }
        if (!toAutoRetry.isEmpty()) {
            System.enqueueJob(new PRM_ParFormAutoRetryQueueable(toAutoRetry));
        }
    }
}

public with sharing class PRM_ParFormAutoRetryQueueable implements Queueable {
    private List<Id> stagingIds;
    public PRM_ParFormAutoRetryQueueable(List<Id> stagingIds) { this.stagingIds = stagingIds; }
    public void execute(QueueableContext qc) {
        for (Id stagingId : stagingIds) {
            PRM_ParFormRetryService.retryFromStaging(stagingId);
        }
    }
}
```

The Queueable hop is necessary because the trigger is in an after-update context and `Database.executeBatch` cannot be called directly from a trigger.

### E. Quick Action on `IndividualApplication`

| Property | Value |
|---|---|
| Label | Retry PAR Submission |
| Type | OmniScript Quick Action (LWC OmniScript launcher) |
| OmniScript | `PRM_ParFormRetryConfirmation_English` (NEW; simple 1-step modal) |
| Conditional Visibility | Only when at least one related `PRM_FailedRecordStaging__c` exists with `PRM_Status__c IN ('Pending','Under Review','Fixed') AND PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` |

The OmniScript displays the most recent failure's structured error, asks confirmation, then invokes `PRM_ParFormRetryFromStaging_Procedure_1`.

### F. Quick Action on `PRM_FailedRecordStaging__c`

| Property | Value |
|---|---|
| Label | Retry from Staging |
| Type | OmniScript Quick Action OR Apex Quick Action |
| Behavior | Identical to the IA-level action but scoped to a specific staging row |
| Conditional Visibility | Only when `PRM_Status__c IN ('Pending','Under Review','Fixed') AND PRM_RetryCount__c < 3 AND PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` |

### G. List View

Network Management QC's list view for `PRM_FailedRecordStaging__c` already exists for the `PRM_NetworkCreationBatch` filter. Add a parallel list view filtered by `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` with the same columns: `Name`, `PRM_CaseManager__c`, `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_LastRetryDate__c`, `PRM_ErrorMessage__c (truncated)`, `CreatedDate`.

### H. Tests

`PRM_ParFormRetryServiceTest.cls`:
1. `happyPath_retryFromStaging` — staging row in Pending, retryCount=0 → after retry: row Retried, retryCount=1, jobId returned
2. `retryCount_exceedsMax_marksTerminal` — staging row retryCount=3 → service returns failure with "Failed - Terminal", row updated to Failed - Terminal
3. `wrongSourceFlow_rejected` — staging row source=PRM_NetworkCreationBatch → service rejects with clear message
4. `terminalState_rejected` — staging row Status=Archived → service rejects
5. `enqueueFailed_revertsToPending` — mock helper.enqueue returns success=false → row reverts to Pending, retryCount NOT incremented... wait, design choice: do we increment regardless or only on successful enqueue? See Clarification #3.
6. `envelopeDeserialization_preservesAllFields` — staging row with full envelope JSON → after retry, the batch sees the same envelope

---

## Acceptance Criteria

**AC1 — Staging row created on per-row batch failure.**
**Given** `PRM_ParFormSubmissionBatch.execute()` rolls back submission #3 due to a structured trigger error,
**When** the per-row catch fires,
**Then** a new `PRM_FailedRecordStaging__c` row exists with `PRM_Status__c='Pending'`, `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'`, `PRM_CaseManager__c` populated, `PRM_RequestPayload__c` containing the full envelope JSON (deserializable back into `PRM_ParFormSubmissionEnvelope`), `PRM_ErrorMessage__c` containing the structured error, `PRM_ExceptionLog__c` linked, and `PRM_RetryCount__c=0`.

**AC2 — Retry from Case Manager Quick Action.**
**Given** I am on the Case Manager record page and there is one Pending PAR staging row,
**When** I click "Retry PAR Submission",
**Then** a confirmation modal shows the structured error and retry-count, I click "Retry Now", `PRM_ParFormRetryService.retryFromStaging(stagingId)` is invoked, `PRM_FailedRecordStaging__c.PRM_RetryCount__c` is incremented to 1, `PRM_Status__c` becomes `Retried`, `PRM_LastRetryDate__c` is set, a new batch job is enqueued, and I see a toast: "Retry enqueued. Job: <id>. We'll notify you when it completes."

**AC3 — Retry count limit enforced.**
**Given** a staging row already at `PRM_RetryCount__c=3`,
**When** I click Retry,
**Then** the service returns failure with message "Retry count exceeded (3 attempts). Marked Failed - Terminal.", the row is updated to `PRM_Status__c='Failed - Terminal'`, and the Retry Quick Action becomes hidden / disabled on subsequent views.

**AC4 — Retry uses the original envelope verbatim.**
**Given** a staging row whose envelope contains the original NPI, vendor TaxId, and standardized addresses (no user changes),
**When** I click Retry,
**Then** the batch's `PRM_ParFormSubmissionRow` for the retry contains identical data to the original — verified by serializing the envelope post-retry and comparing JSON to the pre-retry payload.

**AC5 — Failed retry creates a new staging row, links to the original.**
**Given** a staging row #FST-123 is retried and the retry batch also fails,
**When** the retry batch's per-row catch fires,
**Then** a NEW staging row #FST-124 is created with `PRM_ParentStaging__c = #FST-123`, `PRM_Status__c='Pending'`, `PRM_RetryCount__c=0` (the new row's count starts fresh), and #FST-123 retains its `PRM_Status__c='Retried'` for audit history.

**AC6 — Permission gating.**
**Given** a user without `PRM_DataAdmin` or `PRM_CredentialingUser` permission set assignment,
**When** they navigate to a Case Manager record,
**Then** the "Retry PAR Submission" Quick Action is not visible to them.

**AC7 — Auto-retry on Fixed (when configured).**
**Given** a Custom Metadata setting `PRM_FailedRecordRetry__mdt.PRM_ParFormSubmissionBatch.AutoRetryEnabled__c = true`,
**When** an analyst updates a staging row from `Under Review` to `Fixed`,
**Then** the trigger handler enqueues a Queueable that calls `PRM_ParFormRetryService.retryFromStaging`, and the staging row transitions to `Retried` without manual button-click.

**AC8 — List view filter exists.**
**Given** the Network Management QC team's "Failed Record Staging" tab,
**When** they select the new "PAR Submissions" list view,
**Then** it shows only `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` rows, sorted by `CreatedDate DESC`, with columns Name, Case Manager, Status, Retry Count, Last Retry Date, Error Message (truncated), Created Date.

**AC9 — End-to-end: failure → fix → retry → success.**
**Given** a PAR submission fails because the analyst's vendor TaxId had a typo,
**When** the analyst (a) opens the Case Manager → Failed Record Staging related list → row, (b) reads the structured error, (c) opens the related Vendor Account, (d) corrects the TaxId, (e) returns to the staging row, (f) clicks Retry,
**Then** the batch reprocesses the submission, all records are created cleanly (no DUPLICATE_VALUE thanks to US-PAR-04 trigger idempotency), `IA.PRM_ParFormSubmissionStatus__c='Success'`, the original staging row is `Retried`, and the analyst receives a bell notification "PAR Submission Complete".

**AC-RETRY-THROTTLE — Auto-retry caps concurrent batch enqueues to prevent backlog floods.**
**Given** N `PRM_FailedRecordStaging__c` rows with `PRM_Status__c='Awaiting Retry'` exist when the scheduled or trigger-driven auto-retry job runs (e.g., 200 PAR submissions failed overnight during a Precisely outage and recovered the next morning),
**When** the auto-retry mechanism executes,
**Then** it enqueues at most **3 `PRM_ParFormSubmissionBatch` jobs in parallel** (under the org's hard cap of 5 concurrent batch jobs), monitors via `[SELECT COUNT() FROM AsyncApexJob WHERE ApexClass.Name='PRM_ParFormSubmissionBatch' AND Status IN ('Queued','Processing','Preparing','Holding')]`, and proceeds to the next staging row only when there's room in the queue. Remaining rows wait for the next schedule window. **The 5-batch slot is never exhausted by PAR auto-retry alone**, leaving capacity for `PRM_NetworkCreationBatch` and other batches in the org. At max PAR scale (~490 rows per submission), this means a 200-submission backlog (~98,000 rows total) drains over ~10 minutes wall-clock without ever blocking other workloads.

**AC-RETRY-IDEMPOTENT — Auto-retry never re-enqueues a staging row whose retry is already in flight.**
**Given** a staging row was picked up by a previous auto-retry invocation 30 seconds ago and the batch it spawned is still in `AsyncApexJob.Status='Processing'`,
**When** the next auto-retry invocation fires (or a manual analyst-clicked Retry on the same row races with the scheduled job),
**Then** the staging row is **skipped** (recognized via `PRM_RetryJobId__c` lookup → `AsyncApexJob.Status NOT IN ('Completed','Failed','Aborted')`), the analyst receives a UI toast "Retry already in flight (job 707XX...); refresh in 30 s to see the result", and **no second batch is enqueued for the same envelope**. This guard prevents double-writing all ~490 records of a max-scale submission when two retry triggers overlap.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | What is the production list view UX today for `PRM_NetworkCreationBatch` staging rows? We want to replicate it exactly for PAR. | UX consistency. | Operations Lead |
| 2 | Should the Retry Quick Action be available at both the IA level AND the staging-row level, or only one of the two? | UI design choice. | UX Lead |
| 3 | When the helper's `enqueue` returns `success=false` during a retry, should we (a) revert the staging row to Pending and NOT count this as a retry attempt (allowing the analyst to try again without burning a count), or (b) count it and increment retryCount? | Affects AC3 wording + service implementation. | Product / Operations |
| 4 | Should auto-retry (AC7) ship as default-on or default-off? Auto-retry-on-Fixed is convenient but risks runaway loops if the underlying issue is not actually fixed. | UX safety. | Operations Lead |
| 5 | What is the timezone for `PRM_LastRetryDate__c` display in the UI — user local, org default, or UTC? | UI display. | UX Lead |
| 6 | The retry service is invoked synchronously from the OmniScript Quick Action. The actual batch enqueue takes <100 ms (it just calls `Database.executeBatch`), but if the user has a slow connection, the Quick Action could feel slow. Should we wrap the service in a Queueable so the action returns instantly? | UX latency. | Architecture Lead |
| 7 | Are there scenarios where the original envelope might be stale (e.g., a referenced TaxonomyId no longer exists)? Should the retry service re-validate the envelope before enqueueing? | Defensive design. | Apex Lead |
| 8 | Do we need a "Cancel Retry" / "Mark as Will Not Fix" Quick Action for staging rows that genuinely should be abandoned (not Failed - Terminal, but `Cancelled`)? | Workflow completeness. | Operations Lead |
| 9 | What is the SLA for the analyst-action loop — i.e., how quickly are they expected to triage a Pending staging row? This drives whether we need email escalation. | Process design. | Operations Lead |
| 10 | Is the staging row payload (max 131,072 chars LongTextArea) large enough for the typical PAR envelope? Worst case ~30 KB serialized for a 1-practitioner / 1-vendor / 3-location form. Comfortable. Validate. | Schema constraint. | Apex Lead |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_ParFormRetryService.cls` | Apex (NEW) | **HIGH** | Core retry logic |
| `PRM_ParFormRetryServiceTest.cls` | Apex test (NEW) | **MEDIUM** | 6 scenarios, ≥ 90% coverage |
| `PRM_ParFormSubmissionHelper.cls` | Apex (existing — from US-PAR-01) | **LOW** | Add `isRetry` parameter handling |
| `PRM_FailedRecordStagingTriggerHandler.cls` | Apex (NEW or existing) | **MEDIUM** | Auto-retry on Fixed status transition |
| `PRM_ParFormAutoRetryQueueable.cls` | Apex (NEW) | **LOW** | Queueable wrapper for trigger-context auto-retry |
| `PRM_FailedRecordRetry__mdt` | Custom Metadata Type (existing or NEW) | **LOW** | Config toggle for auto-retry per source flow |
| `PRM_ParFormRetryFromStaging_Procedure_1` | Integration Procedure (NEW) | **MEDIUM** | Wraps the Apex service for the Quick Action |
| `PRM_ParFormRetryConfirmation_English` | OmniScript (NEW) | **MEDIUM** | Simple confirmation modal |
| Quick Action on `IndividualApplication` | Config (NEW) | **MEDIUM** | "Retry PAR Submission" |
| Quick Action on `PRM_FailedRecordStaging__c` | Config (NEW) | **MEDIUM** | "Retry from Staging" |
| `PRM_FailedRecordStaging__c.PRM_ParentStaging__c` | Field (NEW) | **LOW** | Self-lookup for audit chain |
| `PRM_FailedRecordStaging__c.PRM_RetriedByUserId__c` | Field (NEW) | **LOW** | User lookup |
| List view "PAR Submissions" on `PRM_FailedRecordStaging__c` | List View (NEW) | **LOW** | Config |
| IA page layout — Failed Record Staging related list | Page Layout | **LOW** | Add related list |
| Permission set updates | Config | **LOW** | Grant Edit / Quick-Action-Execute on relevant components |
| (Optional) `prmParFormFailureRetryPanel` LWC | LWC (NEW) | **MEDIUM** | Embeddable retry panel |

---

## Estimated Effort

| Component | Type | Effort | Notes |
|---|---|---|---|
| `PRM_ParFormRetryService.cls` + test | Apex (NEW) | **L** (6–8 hrs) | Service logic + 6 test scenarios |
| `PRM_ParFormSubmissionHelper.cls` `isRetry` extension | Apex (existing, edit) | **S** (< 1 hr) | One parameter + branch |
| `PRM_FailedRecordStagingTriggerHandler.cls` auto-retry path | Apex | **M** (2–4 hrs) | Trigger handler + Queueable + Custom Metadata reader |
| `PRM_ParFormAutoRetryQueueable.cls` + test | Apex (NEW) | **M** (2–4 hrs) | Wrapper class + Queueable test |
| `PRM_FailedRecordStaging__c` two new fields | Schema | **S** (< 1 hr) | Self-lookup + user lookup |
| `PRM_ParFormRetryFromStaging_Procedure_1` | IP (NEW) | **M** (2–4 hrs) | One Remote Action + Response |
| `PRM_ParFormRetryConfirmation_English` | OmniScript (NEW) | **M** (2–4 hrs) | 1-step modal with structured error display |
| Two Quick Actions (IA + Staging) | Config | **M** (2–4 hrs) | Including conditional visibility rules |
| List view + page layout updates | Config | **S** (< 1 hr) | Standard config |
| Permission set updates | Config | **S** (< 1 hr) | Field + action permissions |
| (Optional) `prmParFormFailureRetryPanel` LWC + test | LWC | **L** (1 day) | If we choose embeddable panel over Quick Action only |
| Sandbox UAT (9 ACs) | QA | **L** (4–8 hrs) | Each AC has a forced-failure / retry scenario |

**Total Estimated Effort:** **~5–7 person-days** without LWC, **~7–9 person-days** with the optional LWC. Overall **L** sprint slice.

---

## Deployment Checklist

**Pre-requisites:**
- [ ] **US-PAR-01** deployed (staging rows must exist for retry to operate)
- [ ] **US-PAR-04** deployed (retry safety requires idempotent triggers)
- [ ] **US-PAR-02** deployed (catch-block logging — non-blocking, soft dependency)
- [ ] `PRM_FailedRecordStaging__c` confirmed deployed in QA + production (via Clarification #3 in roadmap overview)

**Metadata (deploy in order):**
- [ ] Two new fields on `PRM_FailedRecordStaging__c`
- [ ] `PRM_FailedRecordRetry__mdt` Custom Metadata (if not already present)
- [ ] `PRM_ParFormRetryService.cls` + test
- [ ] `PRM_ParFormAutoRetryQueueable.cls` + test
- [ ] `PRM_FailedRecordStagingTriggerHandler.cls` update (auto-retry path)
- [ ] `PRM_ParFormSubmissionHelper.cls` `isRetry` extension + regression test
- [ ] `PRM_ParFormRetryFromStaging_Procedure_1`
- [ ] `PRM_ParFormRetryConfirmation_English`
- [ ] Two Quick Actions + conditional visibility
- [ ] List view "PAR Submissions" on `PRM_FailedRecordStaging__c`
- [ ] IA page layout: add related list
- [ ] Permission set updates

**Verification in Sandbox:**
- [ ] AC1: force per-row batch failure, confirm staging row populated correctly
- [ ] AC2: click Retry from IA, confirm modal + service flow + toast
- [ ] AC3: pre-set retryCount=3, confirm Terminal transition
- [ ] AC4: deserialize envelope after retry, byte-compare JSON
- [ ] AC5: chain two failures, confirm parent-staging lookup populated
- [ ] AC6: log in as user without permission, confirm Quick Action hidden
- [ ] AC7: with auto-retry on, mark a staging row Fixed, confirm auto-enqueue
- [ ] AC8: open list view, confirm filter + columns
- [ ] AC9: end-to-end failure → fix → retry → success

**Post-Deployment Monitoring (first 30 days):**
- [ ] Daily: count staging rows by status — confirm `Pending`/`Under Review` does not grow unbounded
- [ ] Weekly: average time from staging-row creation to `Retried` or `Failed - Terminal` — target < 48 hours
- [ ] Weekly: success rate of retries (`Retried` AND associated batch run produced `Success` IA status) — target ≥ 70%
- [ ] Monthly: list rows older than 14 days still in `Pending` — flag for escalation

---

## Related Stories

| Story | Priority | Relationship |
|---|---|---|
| `US-PAR-01` (Batch Refactor) | P0 | **Hard pre-req** — staging rows are produced by US-PAR-01's batch |
| `US-PAR-02` (Exception Logging via Platform Event) | P0 | **Strong companion** — `PRM_ExceptionLog__c` linked from staging row provides the structured error |
| `US-PAR-04` (Trigger Idempotency) | P0 | **Hard pre-req** — retry must not collide on the partial data |
| `US_DataAdmin_NetworkError_ListViewAndQCRouting.md` | P0 (Network team) | **Blueprint** — the same UX pattern the Network team built for `PRM_NetworkCreationBatch` |
| `PRM_FailedRecordStaging_Object_Specification.md` | Reference | **Spec** — defines the staging object schema this story consumes |
