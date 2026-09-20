# USER STORY US-PAR-02: Rollback-Safe Exception Logging for PAR Form (Platform Event Pattern)

**Persona:** Salesforce Developer, Operations / Network Management QC Lead, Credentialing Intake Specialist
**Priority:** P0 — observability prerequisite for US-PAR-01 and US-PAR-05; today **92 total rows** in `PRM_ExceptionLog__c` across only **5 distinct process names** for PAR-pipeline failures in 30 days, despite 277 cumulative HCPT duplicate-junction pairs and 36 monthly `updatePPLAddresesForPAR()` throws
**Vertical:** Provider Network Management (PNM)
**Apex (impacted):**
- `PRM_OmniUtils.cls` — `logTryCatchException()` (line 272), `updatePPLAddresesForPAR()` (line 5104) — refactor catch blocks to publish event instead of direct DML
- `PRM_ExceptionLogger.cls` — add `logExceptionViaEvent()` method (mirrors the design in `US_PractitionerCreation_QueueableRefactor.md` § "Apex Class Specifications")
- `PRM_HCProviderTriggerHandler.cls` — `populateSourceSystemIdentifier()` catch blocks (already throws; we just need to log the throw before it escapes)
- `PRM_PracFacilityTriggerHandler.cls` — same pattern
- `PRM_ParFormSubmissionBatch.cls` (new — from US-PAR-01) — catch block writes events, not direct DML

**Integration Procedures (impacted):**
- `PRM_CreateParFormRecordsContainer_Procedure_1` v1 → v2 — TryCatchBlock `remoteMethod` swap (only relevant if v1 stays live during the 30-day backstop window from US-PAR-01)
- `PRM_ExceptionLogger_Procedure_1` (the shared exception-logger IP) — confirm it can route `caseManagerId` end-to-end

**Custom Object / Platform Event (impacted):**
- `PRM_ExceptionLogEvent__e` — add 2 missing fields: `PRM_RecordId__c`, `PRM_RecordObjectName__c` (these exist on `PRM_ExceptionLog__c` but **not on the event** as of the May 2026 snapshot)
- `PRM_ExceptionLog__c` — add 1 missing field: `PRM_IndividualApplication__c` (Lookup to IndividualApplication) — for navigable related-list on Case Manager record
- `PRM_ExceptionLogEventTrigger` — NEW Apex trigger that subscribes to `PRM_ExceptionLogEvent__e (after insert)` and inserts the corresponding `PRM_ExceptionLog__c` rows

**Related stories:** `00_Overview_PARForm_BatchRefactor_Roadmap.md`, `US-PAR-01`, `US_PractitionerCreation_QueueableRefactor.md` (overlapping schema work — coordinate)

---

## Story

**As a** Salesforce Developer or Operations Lead investigating a failed PAR submission,
**I want** every exception thrown inside the PAR pipeline — whether from an OmniStudio sub-IP, an Apex remote action, or a before-insert trigger — to be logged in `PRM_ExceptionLog__c` with the correct `PRM_ProcessName__c`, full stack trace, and a navigable lookup to the originating Case Manager record, **even when the containing transaction has `rollbackOnError=true` and the failure rolls back all DML**,
**So that** I can triage failures within minutes (not hours) by opening the Case Manager and clicking through to the linked Exception Log, instead of waiting for a user report and reproducing locally.

**Why it matters:** Today, when the PAR `TryCatchBlock` calls `PRM_OmniUtils.logTryCatchException`, that method does a direct `insert PRM_ExceptionLog__c` — but the outer IP has `rollbackOnError=true`, so the log row is **rolled back with everything else**. This is why the 30-day org-wide exception log has 166,559 rows but only **92** are tagged to the PAR pipeline (across 5 distinct process names), despite the 277 HCPT duplicate-junction pairs and 36 monthly downstream null-input throws. We are flying blind. The Delegated Practitioner team solved this exact problem in their `US_PractitionerCreation_QueueableRefactor.md` design by publishing a Platform Event from the catch block — Platform Events have their own commit boundary independent of Apex DML transactions, so the log row survives every rollback. This story applies that pattern to PAR.

---

## Scope

| Layer | Component | Change |
|---|---|---|
| Platform Event | `PRM_ExceptionLogEvent__e` | Add `PRM_RecordId__c` (Text 18), `PRM_RecordObjectName__c` (Text 255) |
| Custom Object | `PRM_ExceptionLog__c` | Add `PRM_IndividualApplication__c` (Lookup to IndividualApplication, DeleteConstraint=SetNull) |
| Trigger | `PRM_ExceptionLogEventTrigger` | NEW. Subscribes to the event, inserts the log row, populates the lookup. |
| Apex | `PRM_ExceptionLogger.cls` | Add `logExceptionViaEvent()` method; mark the existing direct-DML method `@deprecated-for-async` |
| Apex | `PRM_OmniUtils.cls` | Update `logTryCatchException()` to use `logExceptionViaEvent`; update the existing 24 catch blocks that log via direct DML to use the event method when invoked from async / `rollbackOnError=true` contexts |
| Apex | `PRM_HCProviderTriggerHandler.cls`, `PRM_PracFacilityTriggerHandler.cls` | When the trigger throws a `DUPLICATE_VALUE` or NPE, publish a `PRM_ExceptionLogEvent__e` BEFORE the throw so the catch path upstream still has a logged trail |
| Apex | `PRM_ParFormSubmissionBatch.cls` (from US-PAR-01) | Catch block calls `logExceptionViaEvent` (not direct DML) |
| OmniStudio | `PRM_CreateParFormRecordsContainer_Procedure_1` v1 (if kept alive during US-PAR-01 backstop) | TryCatchBlock's Remote Action `methodName` swaps from `logTryCatchException` (direct DML) to `logTryCatchExceptionViaEvent` (event publish) |
| OmniStudio | `PRM_ExceptionLogger_Procedure_1` | Ensure `additionalInput.caseManagerId` is wired into both Remote Action steps (`CallLogException`, `CallLogExceptionReturnId`) so it carries through to the event |
| Permission Set | `PRM_CredentialingUser` (or equivalent) | Grant Create/Read on `PRM_ExceptionLogEvent__e`; Read on `PRM_ExceptionLog__c` |

---

## Current State

### `PRM_OmniUtils.logTryCatchException` (line 272)

```apex
private void logTryCatchException(Map<String, Object> inputs){
    Map<String, Object> errorlogger = (Map<String, Object>)inputs.get('SV_SourceIPDetails');
    Map<String, Object> sourceIpOptions = (Map<String, Object>)inputs.get('options');
    // … extracts ProcessName, ErrorMessage from inputs ...
    if(log.containsKey('ErrorMessage')){
        String errorMessage = (String) log.get('ErrorMessage');
        String stackTrace = (String) log.get('StackTrace');
        String processName = (String) log.get('ProcessName');
        String integrationType = (String) log.get('IntegrationType');
        PRM_ExceptionLogger.logException(processName, integrationType, 'Error', stackTrace,
                                         errorMessage, '', 0, '', '', '', '', '');
    }
}
```

Problems:
1. `PRM_ExceptionLogger.logException` is a direct `insert` — rolled back when `rollbackOnError=true` fires.
2. `SV_SourceIPDetails.SourceIPName` is hardcoded to `PRM_CreateParFormRecords` in the container's SetValues step — never overwritten by the failing child sub-IP. So even when a log survives, it says `PRM_CreateParFormRecords` failed, with no granularity on which of the 7 children actually blew up.
3. `caseManagerId` is not in the `inputs` payload at the point `logTryCatchException` reads it, so the log cannot be linked to the IA for navigation.

### `PRM_ExceptionLogEvent__e` (current schema in repo)

Has: `PRM_TargetSystem__c`, `PRM_StackTrace__c`, `PRM_SourceSystem__c`, `PRM_SeverityLevel__c`, `PRM_RequestPayload__c`, `PRM_ProcessName__c`, `PRM_LineNumber__c`, `PRM_IntegrationType__c`, `PRM_ExceptionType__c`, `PRM_ErrorMessage__c`, `PRM_ErrorCode__c`, `PRM_CorrelationID__c`.

**Missing:** `PRM_RecordId__c`, `PRM_RecordObjectName__c` (these exist on `PRM_ExceptionLog__c` but were not added to the event yet).

### `PRM_ExceptionLog__c` (current schema in repo)

Has all the fields above PLUS `PRM_RecordId__c`, `PRM_RecordObjectName__c`, `PRM_AsyncProcess__c`.

**Missing:** `PRM_IndividualApplication__c` (lookup) — without it, ops cannot navigate from a Case Manager record to its related exception logs via a related list.

### Existing subscribers

Search for `PRM_ExceptionLogEvent__e` triggers / flows — current snapshot shows **no `*Trigger.trigger` file** subscribing to this event. The event today appears unused. **Confirm with the team** before deploying a new trigger (Clarification #1) — but most likely we are first.

---

## Proposed Architecture

```
Any failure inside any "rollbackOnError=true" boundary
  │
  ├── (Apex) catch (Exception e) {
  │       PRM_ExceptionLogger.logExceptionViaEvent(
  │           'PRM_ParFormSubmissionBatch.execute',  // exact failing scope
  │           'ASYNC', 'Error', e.getStackTraceString(), e.getMessage(),
  │           e.getTypeName(), e.getLineNumber(),
  │           bc.getJobId(), '', 'Salesforce', 'Salesforce',
  │           JSON.serialize(envelope).abbreviate(30000),
  │           envelope.caseManagerId);   // ← NEW: caseManagerId for lookup
  │   }
  │
  └── (OmniStudio) Try/Catch element → Remote Action
        remoteClass = PRM_OmniUtils
        remoteMethod = logTryCatchExceptionViaEvent  // ← NEW remote entry
        additionalInput.caseManagerId = '%CaseManagerId%'  // ← NEW
        additionalInput.processName   = '<sub-IP identity>'  // ← from per-sub-IP SetValues

  ↓ EventBus.publish(...)        ← survives ANY downstream rollback

  ↓ async event bus delivery (typically <5 s)

  PRM_ExceptionLogEventTrigger (after insert) {
      List<PRM_ExceptionLog__c> logs = new List<PRM_ExceptionLog__c>();
      for (PRM_ExceptionLogEvent__e evt : Trigger.new) {
          PRM_ExceptionLog__c log = new PRM_ExceptionLog__c(...);
          if (evt.PRM_RecordObjectName__c == 'IndividualApplication'
              && String.isNotBlank(evt.PRM_RecordId__c)
              && ((String)evt.PRM_RecordId__c).startsWith('0iT')) {
              log.PRM_IndividualApplication__c = evt.PRM_RecordId__c;
          }
          logs.add(log);
      }
      if (!logs.isEmpty()) insert logs;
  }
```

The new `PRM_IndividualApplication__c` lookup gives every Case Manager record a navigable "Exception Logs" related list — open the IA, see what failed, click in, read the stack.

---

## Technical Section (For Developers)

### A. Platform Event field additions

**`PRM_ExceptionLogEvent__e`** — new fields:

| API Name | Type | Length | Required | Description |
|---|---|---|---|---|
| `PRM_RecordId__c` | Text | 18 | No | Id of the related record (typically the CaseManagerId for PAR / Practitioner Creation; could be any record id for cross-cutting reuse) |
| `PRM_RecordObjectName__c` | Text | 255 | No | API name of the related object (e.g., `IndividualApplication`). The trigger uses this to decide which lookup to populate. |

These mirror the fields already on `PRM_ExceptionLog__c`.

### B. `PRM_ExceptionLog__c` field addition

| API Name | Type | Label | Required | Delete Constraint | Description |
|---|---|---|---|---|---|
| `PRM_IndividualApplication__c` | Lookup (IndividualApplication) | Case Manager | No | Set Null | Links the exception to the originating Case Manager so it appears in the IA's "Exception Logs" related list. |

**Page Layout impact:** Add an "Exception Logs" related list to the IndividualApplication / Case Manager page layout, displaying `Name`, `PRM_ProcessName__c`, `PRM_ErrorMessage__c`, `CreatedDate`.

### C. `PRM_ExceptionLogger.cls` — new methods

```apex
/**
 * Rollback-safe exception logging via Platform Event.
 * ALWAYS use this method when inside:
 *   - A Queueable, Batchable, or Scheduled job
 *   - An OmniStudio IP with rollbackOnError = true
 *   - A trigger that may roll back
 *   - Any other "could roll back" context
 *
 * The Platform Event has its own publish-immediately commit, so the
 * resulting PRM_ExceptionLog__c row survives any Apex transaction
 * rollback that follows.
 */
public static void logExceptionViaEvent(
    String processName, String integrationType,
    String severityLevel, String stackTrace,
    String errorMessage, String exceptionType,
    Integer lineNumber, String correlationId,
    String errorCode, String sourceSystem,
    String targetSystem, String payload,
    String caseManagerId
) {
    PRM_ExceptionLogEvent__e evt = new PRM_ExceptionLogEvent__e(
        PRM_ProcessName__c      = processName,
        PRM_IntegrationType__c  = integrationType,
        PRM_SeverityLevel__c    = severityLevel,
        PRM_StackTrace__c       = stackTrace,
        PRM_ErrorMessage__c     = errorMessage,
        PRM_ExceptionType__c    = exceptionType,
        PRM_LineNumber__c       = lineNumber,
        PRM_CorrelationID__c    = correlationId,
        PRM_ErrorCode__c        = errorCode,
        PRM_SourceSystem__c     = sourceSystem,
        PRM_TargetSystem__c     = targetSystem,
        PRM_RequestPayload__c   = String.isBlank(payload) ? null : payload.abbreviate(131072),
        PRM_RecordId__c         = caseManagerId,
        PRM_RecordObjectName__c = String.isNotBlank(caseManagerId) ? 'IndividualApplication' : null
    );
    Database.SaveResult sr = EventBus.publish(evt);
    if (!sr.isSuccess()) {
        // Best-effort fallback: direct DML insert. Will be rolled back if we are inside
        // rollbackOnError, but at least we tried. System.debug for sandbox visibility.
        System.debug(LoggingLevel.ERROR, 'PRM_ExceptionLogger: EventBus.publish failed: '
            + sr.getErrors()[0].getMessage());
    }
}

/**
 * Direct DML insert — NOT rollback-safe. Only call from synchronous, non-rollback contexts
 * (e.g., the synchronous PRM_*Helper.enqueue methods, which never throw and never roll back).
 * @deprecated-for-async use logExceptionViaEvent() instead.
 */
public static void logExceptionDirect(
    String processName, String integrationType,
    String severityLevel, String stackTrace,
    String errorMessage, String exceptionType,
    Integer lineNumber, String correlationId,
    String errorCode, String sourceSystem,
    String targetSystem, String payload,
    String caseManagerId
) {
    PRM_ExceptionLog__c log = new PRM_ExceptionLog__c(
        PRM_ProcessName__c      = processName,
        PRM_IntegrationType__c  = integrationType,
        PRM_SeverityLevel__c    = severityLevel,
        PRM_StackTrace__c       = stackTrace,
        PRM_ErrorMessage__c     = errorMessage,
        PRM_ExceptionType__c    = exceptionType,
        PRM_LineNumber__c       = lineNumber,
        PRM_CorrelationID__c    = correlationId,
        PRM_ErrorCode__c        = errorCode,
        PRM_SourceSystem__c     = sourceSystem,
        PRM_TargetSystem__c     = targetSystem,
        PRM_RequestPayload__c   = payload == null ? null : payload.abbreviate(131072),
        PRM_RecordId__c         = caseManagerId,
        PRM_RecordObjectName__c = String.isNotBlank(caseManagerId) ? 'IndividualApplication' : null
    );
    if (String.isNotBlank(caseManagerId) && caseManagerId.startsWith('0iT')) {
        log.PRM_IndividualApplication__c = caseManagerId;
    }
    insert log;
}
```

> **Backwards compatibility:** Keep the existing `logException(...)` overloads as wrappers that call `logExceptionDirect(...)`. Audit each existing caller — if it is inside any `Database.Batchable`, `Queueable`, `Schedulable`, or any IP with `rollbackOnError=true`, switch the caller to `logExceptionViaEvent`. **Do NOT silently route every caller through the event** — that would change the latency profile of every log write in the org. Migrate caller-by-caller.

#### C.1 Bulk overload — REQUIRED by AC-MAX

At max PAR scale, a single submission inserts 150 `ContactPointAddress` rows, 55 `HealthcareFacility` rows, 50 `HealthcarePractitionerFacility` rows in single bulk DML statements. If a trigger calls `addError()` on, say, 50 PPL rows, calling `logExceptionViaEvent()` once per record would publish 50 platform events from one transaction — wasteful noise, and at scale across many concurrent submissions it could pressure the org's PE quota.

```apex
/**
 * Bulk-publish ONE PRM_ExceptionLogEvent__e covering all failed records of a given object type.
 * Packs the failed record Ids into PRM_RecordId__c as a comma-separated list. The
 * PRM_ExceptionLogEventTrigger writes ONE PRM_ExceptionLog__c row with the same packed Ids.
 *
 * REQUIRED by AC-MAX. Use this in any trigger handler that processes >5 records.
 *
 * @param processName   e.g., 'PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier'
 * @param sObjectName   e.g., 'HealthcarePractitionerFacility'
 * @param failedRecordIds  Up to 50 record Ids; comma-joined into the event payload (≈ 900 chars max)
 * @param ex            The catching exception
 * @param individualAppId Optional — the originating IndividualApplication (for the lookup)
 */
public static void logBulkExceptionViaEvent(
    String processName, String sObjectName,
    Set<Id> failedRecordIds, Exception ex, Id individualAppId
) {
    PRM_ExceptionLogEvent__e evt = new PRM_ExceptionLogEvent__e(
        PRM_ProcessName__c = processName,
        PRM_RecordObjectName__c = sObjectName,
        PRM_RecordId__c = String.join((Iterable<Id>) failedRecordIds, ','),  // up to 50 × 19 chars
        PRM_IntegrationType__c = 'ASYNC',
        PRM_SeverityLevel__c = 'Error',
        PRM_StackTrace__c = ex.getStackTraceString(),
        PRM_ErrorMessage__c = ex.getMessage() + ' [bulk: ' + failedRecordIds.size() + ' records]',
        PRM_TypeOfException__c = ex.getTypeName(),
        PRM_LineNumber__c = ex.getLineNumber(),
        PRM_CaseManagerId__c = individualAppId
    );
    Database.SaveResult sr = EventBus.publish(evt);
    if (!sr.isSuccess()) {
        System.debug(LoggingLevel.ERROR, 'logBulkExceptionViaEvent publish failed: ' + sr.getErrors());
    }
}
```

### D. `PRM_ExceptionLogEventTrigger` (NEW Apex trigger)

```apex
trigger PRM_ExceptionLogEventTrigger on PRM_ExceptionLogEvent__e (after insert) {
    List<PRM_ExceptionLog__c> logs = new List<PRM_ExceptionLog__c>();
    for (PRM_ExceptionLogEvent__e evt : Trigger.new) {
        PRM_ExceptionLog__c log = new PRM_ExceptionLog__c(
            PRM_ProcessName__c      = evt.PRM_ProcessName__c,
            PRM_IntegrationType__c  = evt.PRM_IntegrationType__c,
            PRM_SeverityLevel__c    = evt.PRM_SeverityLevel__c,
            PRM_StackTrace__c       = evt.PRM_StackTrace__c,
            PRM_ErrorMessage__c     = evt.PRM_ErrorMessage__c,
            PRM_ExceptionType__c    = evt.PRM_ExceptionType__c,
            PRM_LineNumber__c       = evt.PRM_LineNumber__c,
            PRM_CorrelationID__c    = evt.PRM_CorrelationID__c,
            PRM_ErrorCode__c        = evt.PRM_ErrorCode__c,
            PRM_SourceSystem__c     = evt.PRM_SourceSystem__c,
            PRM_TargetSystem__c     = evt.PRM_TargetSystem__c,
            PRM_RequestPayload__c   = evt.PRM_RequestPayload__c,
            PRM_RecordId__c         = evt.PRM_RecordId__c,
            PRM_RecordObjectName__c = evt.PRM_RecordObjectName__c
        );
        if (evt.PRM_RecordObjectName__c == 'IndividualApplication'
                && String.isNotBlank(evt.PRM_RecordId__c)
                && ((String)evt.PRM_RecordId__c).startsWith('0iT')) {
            log.PRM_IndividualApplication__c = (Id) evt.PRM_RecordId__c;
        }
        logs.add(log);
    }
    if (!logs.isEmpty()) {
        Database.SaveResult[] results = Database.insert(logs, false);
        for (Integer i = 0; i < results.size(); i++) {
            if (!results[i].isSuccess()) {
                // Cannot publish another event — would loop. Fall back to debug log.
                System.debug(LoggingLevel.ERROR,
                    'PRM_ExceptionLogEventTrigger insert failed for event '
                    + Trigger.new[i].PRM_ProcessName__c + ': '
                    + results[i].getErrors()[0].getMessage());
            }
        }
    }
}
```

Includes a guard against infinite event loops if the log insert itself fails (do **NOT** publish another event from the trigger).

### E. `PRM_OmniUtils.cls` — refactors

#### E.1 `logTryCatchException` body

Change the body to publish an event. Extract `caseManagerId` from the inputs map (the calling IP step must pass it via `additionalInput.caseManagerId`):

```apex
private void logTryCatchException(Map<String, Object> inputs){
    Map<String, Object> errorlogger = (Map<String, Object>) inputs.get('SV_SourceIPDetails');
    Map<String, Object> sourceIpOptions = (Map<String, Object>) inputs.get('options');
    // … existing extraction of processName, errorMessage, stackTrace, integrationType ...

    String caseManagerId = (String) inputs.get('caseManagerId');
    // Fallback: try to extract from the IP variable graph
    if (String.isBlank(caseManagerId) && sourceIpOptions != null) {
        caseManagerId = (String) sourceIpOptions.get('caseManagerId');
    }

    if (log != null && log.containsKey('ErrorMessage')) {
        PRM_ExceptionLogger.logExceptionViaEvent(
            (String) log.get('ProcessName'),
            (String) log.get('IntegrationType'),
            'Error',
            (String) log.get('StackTrace'),
            (String) log.get('ErrorMessage'),
            '', 0, '', '', '', '',
            JSON.serialize(inputs).abbreviate(30000),
            caseManagerId
        );
    }
}
```

#### E.2 `updatePPLAddresesForPAR` catch (line 5249)

Change the catch from `PRM_ExceptionLogger.logException` (direct DML) to `PRM_ExceptionLogger.logExceptionViaEvent`, passing the `individualAppId` as `caseManagerId`:

```apex
} catch (Exception ex) {
    PRM_ExceptionLogger.logExceptionViaEvent(
        'PRM_OmniUtils.updatePPLAddresesForPAR()',
        'SYNC', 'Error',
        ex.getStackTraceString(), ex.getMessage(),
        ex.getTypeName(), ex.getLineNumber(),
        '', '', 'Salesforce', '',
        JSON.serialize(inputMap).abbreviate(30000),
        individualAppId   // ← was missing; now available since we already read it
    );
    outMap.put('showError', true);
    outMap.put('error', ex.getMessage());
    outMap.put('errorCode', ex.getTypeName());
}
```

### F. Trigger-handler changes — `PRM_HCProviderTriggerHandler` and `PRM_PracFacilityTriggerHandler`

Before-insert triggers that `addError()` to block a row don't actually throw an exception, but the resulting `DUPLICATE_VALUE` / `FIELD_INTEGRITY_EXCEPTION` propagates to the calling DR / Apex. Currently these are caught by the OmniScript catch-all that masks the error. Two enhancements:

1. **Inside the trigger**, BEFORE calling `addError()`, publish a `PRM_ExceptionLogEvent__e` so we have a server-side breadcrumb of the collision (process name, the colliding identifier, the parent record id).
2. **The `caseManagerId` is not directly available** in the trigger context — workaround: add a `@TestVisible private static Id PRM_TriggerCaseManagerContext` static on `PRM_OmniUtils` that the calling IP / Apex sets before the DML; trigger reads it. This is mildly ugly but matches the pattern used by `PRM_OmniProcessUtils` for cross-method context. **Confirm pattern with Apex lead** (Clarification #5).

### G. OmniStudio change — per-sub-IP SetValues injection

Even though US-PAR-01 deactivates the seven sub-IPs in the long term, during the 30-day backstop window the original chain may still fire. To make logs useful during that window, in `PRM_CreateParFormRecords_Procedure_29` add an empty SetValues element after each IP Action that overwrites `SV_SourceIPDetails`:

```
seq 2.1: SetValues SV_SourceIPDetails_PostStep2
    SV_SourceIPDetails.SourceIPName = "PRM_PractitionerScreenRecordCreation"
    SV_SourceIPDetails.SourceIPElementName = "PRM_PractitionerScreenRecordCreation"
    SV_SourceIPDetails.caseManagerId = %CaseManagerId%
seq 4.1: SetValues SV_SourceIPDetails_PostStep4
    SV_SourceIPDetails.SourceIPName = "PRM_CreateGroupScreenRecord"
    SV_SourceIPDetails.SourceIPElementName = "PRM_CreateGroupScreenRecord"
    SV_SourceIPDetails.caseManagerId = %CaseManagerId%
…
```

That way the TryCatchBlock's logger writes the correct failing sub-IP name and the Case Manager link.

This change is **optional if US-PAR-01 ships within the same sprint** — once the IP chain is deactivated, there's no more logger to feed.

---

## Acceptance Criteria

**AC1 — Event published from rollback-bound context survives the rollback.**
**Given** Apex code inside a `Database.Batchable` (`rollbackOnError`-equivalent) execution that catches an exception and calls `PRM_ExceptionLogger.logExceptionViaEvent(...)`,
**When** the catch block returns and the batch's per-row Savepoint is rolled back,
**Then** the corresponding `PRM_ExceptionLog__c` row is present in the database (queryable via SOQL within 30 seconds of the rollback) with the correct `PRM_ProcessName__c`, `PRM_ErrorMessage__c`, and `PRM_IndividualApplication__c` lookup populated.

**AC2 — OmniStudio TryCatchBlock writes a per-sub-IP log.**
**Given** an in-flight OmniScript session running through `PRM_CreateParFormRecordsContainer_Procedure_1` v1 with the per-sub-IP `SV_SourceIPDetails` injection from §G,
**When** `PRM_CreateGroupScreenRecord` (sub-IP 4) throws,
**Then** an exception log row exists with `PRM_ProcessName__c = "PRM_CreateGroupScreenRecord"` (not "PRM_CreateParFormRecords") and `PRM_IndividualApplication__c` linked to the originating IA.

**AC3 — Trigger-induced duplicate-error has a server-side breadcrumb.**
**Given** `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` blocks a row with a duplicate `SourceSystemIdentifier`,
**When** the trigger's `addError()` fires,
**Then** an exception log row exists with `PRM_ProcessName__c = "PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier"`, `PRM_ExceptionType__c = "DuplicateValue"`, the colliding `SourceSystemIdentifier` value in `PRM_ErrorMessage__c`, and (if context is available) `PRM_IndividualApplication__c` linked.

**AC4 — Navigable from Case Manager.**
**Given** an exception log exists with `PRM_IndividualApplication__c` populated,
**When** a Credentialing Specialist opens the linked Case Manager record,
**Then** they see the exception log entry in the "Exception Logs" related list, can click into it, and view `PRM_ErrorMessage__c`, `PRM_ProcessName__c`, `PRM_StackTrace__c`, and `PRM_RequestPayload__c` without writing a SOQL query or opening a separate list view.

**AC5 — Direct-DML and event-based methods do not double-log.**
**Given** the new `logExceptionViaEvent` method and the legacy `logExceptionDirect` method coexist,
**When** an Apex method that has been migrated to `logExceptionViaEvent` is invoked,
**Then** exactly **one** `PRM_ExceptionLog__c` row is created (not two). The migration MUST switch the call site, not call both methods.

**AC6 — Event trigger handles bulk events without governor breaches.**
**Given** 200 `PRM_ExceptionLogEvent__e` events published in a single transaction (e.g., a large batch fails 200 rows in one chunk),
**When** `PRM_ExceptionLogEventTrigger` fires,
**Then** all 200 events produce log rows in a single `insert` call, with no SOQL / DML / CPU governor breaches.

**AC7 — Event trigger failure does NOT cascade.**
**Given** a `PRM_ExceptionLog__c` insert from the trigger fails (e.g., a required field is somehow null on one event),
**When** `Database.insert(logs, false)` returns mixed results,
**Then** the trigger logs the failure via `System.debug(LoggingLevel.ERROR, ...)` but **does NOT publish another `PRM_ExceptionLogEvent__e` from the trigger** (which would loop). Successful rows still commit.

**AC8 — Permission set audit.**
**Given** the permission set `PRM_CredentialingUser` (or equivalent) is updated,
**When** an intake user runs a PAR form,
**Then** the user has Create + Read on `PRM_ExceptionLogEvent__e` so the event can publish from their session; **and** the user has Read on `PRM_ExceptionLog__c` so they can see the related-list entry on the Case Manager.

**AC-MAX — One max-scale submission publishes ≤ 20 platform events even when many records fail.**
**Given** a maximum-scale PAR submission (5 groups × 10 locations → 50 PPL rows, ~150 CPA rows, ~60 Address rows, ~55 HF rows — see `US_PAR_ScaleAudit_5Groups_10Locations.md`) experiences a failure inside `processSubmission()`,
**When** the batch's outer `catch` block fires and the trigger-handlers' bulk `addError()` paths run,
**Then** the total number of `PRM_ExceptionLogEvent__e` events published per submission is **≤ 20** (one per failed object type / one per outer-catch / one per trigger), **NOT** one-per-failing-record. At 150 CPA rows or 55 HF rows, publishing one event per row would inflate noise without adding signal — the structured error message in a single bulk event must carry the comma-separated list of failed row identifiers (up to 50 × 18 chars = 900 chars fits comfortably in the `PRM_RecordId__c` `Long Text Area` field). Implementation uses the new `PRM_ExceptionLogger.logBulkExceptionViaEvent(process, sObjectName, failedRecordIds, ex, individualAppId)` method that publishes ONE event with packed identifiers.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Is there an existing subscriber (trigger, flow, Apex CometD listener) on `PRM_ExceptionLogEvent__e` that we must coexist with? | If yes, our new trigger must not double-insert. | Apex Lead |
| 2 | Is `US_PractitionerCreation_QueueableRefactor.md` already shipped (it proposes the same `PRM_RecordId__c` / `PRM_RecordObjectName__c` field additions on the event, and the `PRM_IndividualApplication__c` lookup on the log)? If shipped, US-PAR-02 just uses the existing infrastructure. If not, US-PAR-02 ships those schema changes itself. | Determines whether US-PAR-02 is a 3-day or 5-day story. | Release Manager |
| 3 | What is the IndividualApplication record-id prefix in production / QA — confirm `0iT` (we see `0iT` in QA; production may differ for sandbox refresh reasons)? | Used in the trigger lookup-population guard. | Technical Lead |
| 4 | Does `PRM_ExceptionLogger.cls` need a third overload that returns the new log Id (for callers that want to chain a staging-row insert via `PRM_FailedRecordStaging__c.PRM_ExceptionLog__c`)? The event pattern is fire-and-forget, so a return Id is tricky — see Clarification #5 in `US_PractitionerCreation_QueueableRefactor.md`. | Affects US-PAR-05 (staging-row linkage). | Apex Lead |
| 5 | For the trigger-handler enhancement (§F), how does the trigger get `caseManagerId`? Options: (a) a `@TestVisible private static Id PRM_TriggerCaseManagerContext` static on a context class; (b) a transient field on the SObject (won't survive trigger boundary); (c) accept that the log won't be IA-linked when fired from a trigger. | Determines AC3 wording. | Apex Lead |
| 6 | Are we OK with the event's `PRM_RequestPayload__c` being abbreviated to 131,072 chars (matches `PRM_FailedRecordStaging__c` field length)? Some PAR payloads are large. | If payload truncation hurts triage, we may need to also stage the full payload to a related `PRM_FailedRecordStaging__c` row. | Operations Lead |
| 7 | Should the helper `enqueueParFormSubmission` (sync path from US-PAR-01) use `logExceptionViaEvent` too, even though it doesn't run inside a rollback context? Pro: uniform code style. Con: small extra latency for log writes that don't need event semantics. | Affects the "migrate caller-by-caller" guidance in §C. | Apex Lead |
| 8 | Do we want field-history tracking on `PRM_ExceptionLog__c.PRM_IndividualApplication__c`? | Likely no — exception logs are immutable. Confirm. | Compliance |

---

## Impact Analysis

| Component | Type | Impact | Description |
|---|---|---|---|
| `PRM_ExceptionLogEvent__e` | Platform Event | **MEDIUM** | Two new fields — additive, no break |
| `PRM_ExceptionLog__c` | Custom Object | **MEDIUM** | One new lookup — additive; related-list configuration needed on IA page layout |
| `PRM_ExceptionLogEventTrigger` | Apex Trigger | **HIGH** | NEW trigger — must coordinate with any existing event subscribers (Clarification #1) |
| `PRM_ExceptionLogger.cls` | Apex (existing) | **MEDIUM** | Two new methods; legacy `logException` overloads remain as wrappers |
| `PRM_OmniUtils.cls` | Apex (existing) | **HIGH** | `logTryCatchException` body change; `updatePPLAddresesForPAR` catch change; ~24 direct-DML log callers may need migration (audit first) |
| `PRM_HCProviderTriggerHandler.cls` | Apex (existing) | **MEDIUM** | Add event-publish before `addError()`; introduces trigger-context static (Clarification #5) |
| `PRM_PracFacilityTriggerHandler.cls` | Apex (existing) | **MEDIUM** | Same as above |
| `PRM_CreateParFormRecords_Procedure_29` | IP (existing — short-lived) | **LOW** | Per-sub-IP SetValues injection (§G). Only relevant for 30-day backstop window. |
| `PRM_ExceptionLogger_Procedure_1` | IP (existing) | **LOW** | Add `caseManagerId` to `additionalInput` of both Remote Action steps |
| `PRM_CredentialingUser` permission set | Permission Set | **LOW** | Add Create on event, Read on log |
| Case Manager page layout | Page Layout | **LOW** | Add Exception Logs related list |

---

## Estimated Effort

| Component | Type | Effort | Notes |
|---|---|---|---|
| `PRM_ExceptionLogEvent__e` field additions | Schema | **S** | Two fields, additive |
| `PRM_ExceptionLog__c.PRM_IndividualApplication__c` | Field | **S** | One lookup |
| `PRM_ExceptionLogEventTrigger` + test class | Apex | **L** (4–8 hrs) | Trigger logic is simple; test must cover bulk + failure-mode + coexistence |
| `PRM_ExceptionLogger.cls` new methods + test updates | Apex | **M** (2–4 hrs) | Two methods + regression on existing test |
| `PRM_OmniUtils.cls` `logTryCatchException` refactor | Apex | **M** (2–4 hrs) | Body swap + caller audit |
| `PRM_OmniUtils.cls` ~24 direct-DML log-call migrations | Apex | **L** (1 day) | Per-call audit: is it inside a rollback context? Migrate where yes |
| `PRM_HCProviderTriggerHandler` + `PRM_PracFacilityTriggerHandler` event publish | Apex | **M** (2–4 hrs) | Pre-throw event + trigger context wiring |
| `PRM_CreateParFormRecords_Procedure_29` per-sub-IP SetValues (§G) | IP config | **M** (2–4 hrs) | 5–6 SetValues elements wired |
| `PRM_ExceptionLogger_Procedure_1` additionalInput | IP config | **S** | One field on two steps |
| Permission set + page layout | Config | **S** | Standard config |
| Sandbox verification (8 ACs) | QA | **L** (4–8 hrs) | Each AC has a forced-failure scenario |

**Total Estimated Effort:** **~4–6 person-days** — overall **L** sprint slice. The largest unknown is whether `US_PractitionerCreation_QueueableRefactor.md` is already in flight (in which case half of this story is already deploying).

---

## Deployment Checklist

**Pre-requisites:**
- [ ] Confirm with Apex Lead: no existing subscriber on `PRM_ExceptionLogEvent__e` (Clarification #1)
- [ ] Coordinate with `US_PractitionerCreation_QueueableRefactor.md` owner (Clarification #2)

**Metadata (deploy in order):**
- [ ] `PRM_ExceptionLogEvent__e` field additions (`PRM_RecordId__c`, `PRM_RecordObjectName__c`)
- [ ] `PRM_ExceptionLog__c.PRM_IndividualApplication__c`
- [ ] `PRM_ExceptionLogger.cls` (with new methods + tests)
- [ ] `PRM_ExceptionLogEventTrigger` + test (90%+ coverage required for Apex trigger)
- [ ] `PRM_OmniUtils.cls` (refactored `logTryCatchException` + `updatePPLAddresesForPAR` catch) + regression tests
- [ ] `PRM_HCProviderTriggerHandler` / `PRM_PracFacilityTriggerHandler` event-publish additions
- [ ] `PRM_ExceptionLogger_Procedure_1` additionalInput updates
- [ ] (if v1 backstop kept) `PRM_CreateParFormRecords_Procedure_29` per-sub-IP SetValues injection
- [ ] Permission set updates
- [ ] Case Manager page layout — add Exception Logs related list

**Verification in Sandbox:**
- [ ] AC1: force a per-row failure in `PRM_NetworkCreationBatch` (existing live batch) — confirm new exception log appears with lookup populated
- [ ] AC2: open the existing PAR form, force sub-IP 4 failure via a known duplicate-collision NPI — confirm log has correct sub-IP name
- [ ] AC3: trigger `populateSourceSystemIdentifier` collision — confirm breadcrumb event
- [ ] AC4: navigate from Case Manager record → Exception Logs related list → log detail
- [ ] AC5: spot-check 10 migrated call sites — confirm only one log per failure
- [ ] AC6: synthetic test: publish 200 events at once, confirm trigger handles in bulk
- [ ] AC7: synthetic test: force trigger's `Database.insert` to fail on one row, confirm no loop

**Post-Deployment Monitoring (first 14 days):**
- [ ] Daily query: `SELECT COUNT(Id) FROM PRM_ExceptionLog__c WHERE PRM_ProcessName__c LIKE '%ParFormSubmission%' AND CreatedDate=LAST_N_DAYS:1` — confirm logs are appearing
- [ ] Spot-check 5 Case Managers with logs — confirm `PRM_IndividualApplication__c` lookup is populated
- [ ] Audit: zero entries in `System.debug(LoggingLevel.ERROR, ...)` from `PRM_ExceptionLogEventTrigger` failure-mode

---

## Related Stories

| Story | Priority | Relationship |
|---|---|---|
| `US-PAR-01` (Batch Refactor) | P0 | **Hard consumer** — batch catch block requires this story's `logExceptionViaEvent` |
| `US-PAR-05` (Failed Record Staging + Retry UX) | P1 | **Consumer** — staging rows link to exception logs via `PRM_ExceptionLog__c.Id` |
| `US_PractitionerCreation_QueueableRefactor.md` | P0 (in flight) | **Strong overlap** — same schema additions. Coordinate. |
| `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` | P0 (in flight) | **Sibling** — Item #6 (trigger idempotency) overlaps with §F. Coordinate. |
