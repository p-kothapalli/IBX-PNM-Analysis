# USER STORY: Practitioner Creation — Queueable Refactor & Exception Logging

**Persona:** Credentialing Specialist, Salesforce Developer  
**Priority:** P0 — Production silent failure; 15–20 support tickets/week  
**Vertical:** Provider Network Management (PNM)  
**OmniScript:** `PRM_DelegatedPractitionerReviewScreen` (entry point)  
**Integration Procedures:** `PRM_AddressLogicContainer`, `PRM_ExistingPrimaryPracticeLocationLogicDelg`, `PRM_CreateDelegatedHFNRecords`  
**Relevant Requirements:** `PRM_NetworkCreation_Issue_Summary.md`, `PRM_Performance_Issues_Analysis_UserStories.md`, `TDD_PractitionerCreation.txt`, `TDD_Gap_Analysis.md`  

---

## Story

**As a** Credentialing Specialist,  
**I want** the delegated practitioner creation process to complete reliably without timing out, and to surface a clear error record linked to the Case Manager when any background step fails,  
**So that** I can onboard practitioners with multiple practice locations without manual intervention, and so that the operations team has immediate, navigable visibility into any failure — without checking system logs.

**Why it matters:** The current `PRM_AddressLogicContainer` IP chain silently hangs when creating practitioners with 3+ practice locations. The UI spins indefinitely (5+ minutes), the process fails against Salesforce governor limits, and no error record is created. Credentialing staff cannot tell whether the submission worked or failed, leading to duplicate submissions, partial data states, and 15–20 support tickets per week requiring manual record creation (2–3 hours per practitioner).

---

## Scope

| Flow | Integration Procedure | Role in Chain | Current Execution Mode |
|---|---|---|---|
| Delegated Practitioner Creation | `PRM_AddressLogicContainer` | Container orchestrator | Synchronous/Chainable |
| Address & Facility Creation | `PRM_PractitionerAddressCreation` | Child IP 1 — creates addresses, facilities, locations, HC practitioners, identifiers, provider features | Chainable (no change) |
| Existing Primary Location Logic | `PRM_ExistingPrimaryPracticeLocationLogicDelg` | Child IP 2 — creates HCPF records, provider features (ACC/AA), practice-to-practitioner affiliations, CDM update | Chainable → **changing to Queueable** |
| Delegated HFN Record Creation | `PRM_CreateDelegatedHFNRecords` | Child IP 3 — creates taxonomy networks, payer networks, IFC records | Queueable from Container → **moving to Queueable from IP2** |

---

## Current State

### Transaction Boundaries (Before)

```
TX1 (Synchronous/Chainable):
  Container → IP1 → IP2
  rollbackOnError = true on all three.
  UI waits for full completion before returning.

TX2 (Queueable, separate transaction):
  IP3 (PRM_CreateDelegatedHFNRecords)
  Invoked from Container via useQueueable = true.
  Commits independently; failure does not roll back TX1.
```

### Governor Limits (Current — Insufficient)

| IP | Queries | CPU (ms) | Heap (MB) |
|---|---|---|---|
| `PRM_AddressLogicContainer` | 50 | 2,000 | — |
| `PRM_PractitionerAddressCreation` (IP1) | 100 | 10,000 | 6 |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` (IP2) | 50 | 2,000 | — |
| `PRM_CreateDelegatedHFNRecords` (IP3) | 120 (queueable) | 40,000 (queueable) | 6 (queueable) |

### Failure Modes (Current)

- **IP1 limit breach:** Container's chainable limit of 50 queries/2,000ms CPU is exhausted before IP1 completes for practitioners with multiple locations.
- **IP3 silent timeout:** IP3 runs as Queueable but the Container waits for it (`chainOnStep = false` but no disconnect from the UI response). CPU hits 40,000ms limit for 3+ locations (9 taxonomy + 45 payer network + 15 IFC records = ~280 operations).
- **No exception logging:** When any IP fails with `rollbackOnError = true`, the direct DML insert to `PRM_ExceptionLog__c` is rolled back along with everything else. The failure leaves no record.

---

## Proposed Architecture (After)

### New Transaction Boundaries

```
TX1 (Synchronous/Chainable):
  Container + IP1 (PRM_PractitionerAddressCreation)
  rollbackOnError = true — full rollback if IP1 fails.
  UI waits only for TX1.

TX2 (Queueable — first async hop):
  IP2 (PRM_ExistingPrimaryPracticeLocationLogicDelg)
  Runs in its own Apex transaction.
  rollbackOnError = true within IP2 scope only.
  Elevated governor limits (Queueable context).

TX3 (Queueable — second async hop, invoked from IP2):
  IP3 (PRM_CreateDelegatedHFNRecords)
  Runs in its own Apex transaction.
  rollbackOnError = true within IP3 scope only.
  Elevated governor limits (Queueable context).
```

### Exception Logging Strategy

Because `rollbackOnError = true` rolls back all DML in a failing transaction — including any `PRM_ExceptionLog__c` records inserted in that same transaction — exception logs **must be written via `PRM_ExceptionLogEvent__e`** (Platform Event with `publishBehavior = PublishImmediately`). Platform Events are committed independently of the DML transaction and survive rollback.

```
IP2/IP3 Catch Block
  → Remote Action: PRM_OmniUtils.logExceptionViaEvent()
  → EventBus.publish(PRM_ExceptionLogEvent__e)   ← survives rollback
  → PRM_ExceptionLogEventTrigger (after insert)
  → insert PRM_ExceptionLog__c (with CaseManager lookup)
```

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|---|---|---|
| `PRM_AddressLogicContainer_English_3` | Integration Procedure (propertySetConfig) | Increase chainable governor limits (see section below) |
| `PRM_AddressLogicContainer` — `ExistingPrimaryAddressLogic` element | IP Element (propertySetConfig) | Change from `chainOnStep: true` to Queueable invocation; add `RecordsToUpdate` and `FacilityPractitionerTxNw` to `additionalInput` |
| `PRM_AddressLogicContainer` — `AddTaxNetworkLogic` element | IP Element | Set `isActive: false` — IP3 now invoked from IP2 |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` | Integration Procedure (propertySetConfig) | Add queueable governor limit overrides; increase base chainable limits |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — new element `AddTaxNetworkLogicFromDelg` | IP Element (IP Action) | New element invoking `PRM_CreateDelegatedHFNRecords` as Queueable, at **level 0 (top-level)** after `ResponseForIp` |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — Try/Catch | IP Element | Wrap **all steps from seq 1 onward** in a Try/Catch; Catch block calls `logExceptionViaEvent` |
| `PRM_CreateDelegatedHFNRecords` | Integration Procedure | Wrap `CB_LogicExecuteTxNetwork`, `CB_LogicExecuteLocNetwork`, `CB_ExecuteIFCLogic` blocks in Try/Catch; Catch block calls `logExceptionViaEvent` |
| `PRM_ExceptionLog__c` | Custom Field | New Lookup field: `PRM_IndividualApplication__c` (Lookup to IndividualApplication, DeleteConstraint = SetNull) |
| `PRM_ExceptionLogEvent__e` | Custom Fields | New `PRM_RecordId__c` (Text 18) and `PRM_RecordObjectName__c` (Text 255) |
| `PRM_ExceptionLogEventTrigger` | Apex Trigger | New trigger on `PRM_ExceptionLogEvent__e` (after insert); creates `PRM_ExceptionLog__c` records and populates `PRM_IndividualApplication__c` lookup |
| `PRM_ExceptionLogger.cls` | Apex Class | Add new `logExceptionViaEvent()` method; add overloaded `logExceptionDirect()` (safe only outside rollback contexts) |
| `PRM_OmniUtils.cls` | Apex Class | Add `logExceptionViaEvent()` remote method; update `logException()` to extract `caseManagerId` from `inputMap`; update `logTryCatchException()` similarly |
| `PRM_ExceptionLogger_Procedure_1` | Integration Procedure | Add `"caseManagerId": "%caseManagerId%"` to `additionalInput` on both `CallLogException` and `CallLogExceptionReturnId` Remote Action steps |
| `CaseDataManager` / `IndividualApplication` | Custom Field | New boolean flag: `IsNetworkRecordsCreated__c` — set by IP3 on successful completion |
| `PRM_AsyncProcessingStatus__c` | Custom Field on CaseManager | New picklist: `Not Started | Processing | Completed | Failed` — set at TX1 start and updated by IP2/IP3 (see Improvements) |

---

### Integration Procedure Specifications

#### 4.1 — `PRM_AddressLogicContainer` (Version 4)

**propertySetConfig changes:**

| Property | Before | After |
|---|---|---|
| `chainableQueriesLimit` | 50 | 120 |
| `chainableCpuLimit` | 2,000 | 10,000 |
| `chainableHeapSizeLimit` | null | 6 |
| `chainableDMLStatementsLimit` | null | 150 |
| `chainableDMLRowsLimit` | null | 10,000 |
| `chainableQueryRowsLimit` | null | 50,000 |

**`ExistingPrimaryAddressLogic` element changes:**

```json
// BEFORE
{
  "disableChainable": false,
  "chainOnStep": true
}

// AFTER
{
  "disableChainable": true,
  "chainOnStep": false,
  "remoteOptions": { "useQueueable": true },
  "additionalInput": {
    "PersonContactId":          "=%PersonContactId%",
    "IsActive":                 "=%IsActive%",
    "CaseManagerId":            "=%CaseManagerId%",
    "IsPending":                "=%IsPending%",
    "RecordsToUpdate":          "=%RecordsToUpdate%",
    "FacilityPractitionerTxNw": "=%FacilityPractitionerTxNw%"
  }
}
```

> **Note:** `RecordsToUpdate` and `FacilityPractitionerTxNw` are **new additions** to this `additionalInput`. Without them, IP2 cannot forward these fields to IP3. Verify field names against the Container's current output context before deploying.

**`AddTaxNetworkLogic` element:**
```json
{ "isActive": false }
```

---

#### 4.2 — `PRM_ExistingPrimaryPracticeLocationLogicDelg` (Version 2)

**propertySetConfig changes:**

| Property | Before | After |
|---|---|---|
| `chainableQueriesLimit` | 50 | 100 |
| `chainableCpuLimit` | 2,000 | 10,000 |
| `chainableHeapSizeLimit` | null | 6 |
| `queueableChainableQueriesLimit` | — | 150 |
| `queueableChainableCpuLimit` | — | 60,000 |
| `queueableChainableHeapSizeLimit` | — | 12 |

**New element — `AddTaxNetworkLogicFromDelg`:**

```json
{
  "name": "AddTaxNetworkLogicFromDelg",
  "type": "Integration Procedure Action",
  "sequenceNumber": 6.1,
  "level": 0,
  "propertySetConfig": {
    "sendOnlyAdditionalInput": true,
    "remoteOptions": { "useQueueable": true },
    "returnOnlyAdditionalOutput": false,
    "failOnStepError": false,
    "isActive": true,
    "disableChainable": true,
    "chainOnStep": false,
    "integrationProcedureKey": "PRM_CreateDelegatedHFNRecords",
    "additionalInput": {
      "PersonContactId":          "=%PersonContactId%",
      "IsActive":                 "=%IsActive%",
      "RecordsToUpdate":          "=%RecordsToUpdate%",
      "CaseManagerId":            "=%CaseManagerId%",
      "IsPending":                "=%IsPending%",
      "FacilityPractitionerTxNw": "=%FacilityPractitionerTxNw%"
    },
    "useFormulas": true
  }
}
```

> **Placement:** `level: 0` (top-level), placed after `ResponseForIp` (seq 6.0). **Do NOT place inside the `ExistingPrimaryPractice` conditional block (level 1)**. IP3 must fire regardless of whether the practitioner has an existing primary practice location.
>
> **`failOnStepError: false`:** IP3 is Queueable and runs asynchronously. Its enqueue should not roll back IP2's already-committed DML. The IP3 failure path is handled by IP3's own Try/Catch + exception event.

**Try/Catch configuration in IP2:**

```
Try Block: Wrap ALL steps from seq 1 onward (not just the ExistingPrimaryPractice block)
  → All existing steps 1–17 + new AddTaxNetworkLogicFromDelg at seq 6.1

Catch Block:
  → Remote Action: PRM_OmniUtils.logExceptionViaEvent
  → additionalInput:
      processName:     "PRM_ExistingPrimaryPracticeLocationLogicDelg"
      integrationType: "ASYNC"
      severityLevel:   "Error"
      errorMessage:    "%error%"  (or OmniStudio error capture variable)
      caseManagerId:   "%CaseManagerId%"
      payload:         (serialized input context)
  → IMPORTANT: Do NOT use logException (direct DML) — it will be rolled back
```

---

#### 4.3 — `PRM_CreateDelegatedHFNRecords` (No Structural Change — Add Try/Catch Only)

IP3 internal logic and inputs are unchanged. Add Try/Catch blocks around:
- `CB_LogicExecuteTxNetwork`
- `CB_LogicExecuteLocNetwork`
- `CB_ExecuteIFCLogic`

Each Catch block: Remote Action → `PRM_OmniUtils.logExceptionViaEvent` with:
```
processName:     "PRM_CreateDelegatedHFNRecords"
integrationType: "ASYNC"
caseManagerId:   "%CaseManagerId%"
```

IP3 must also update `IsNetworkRecordsCreated__c = true` on the CaseDataManager record upon successful completion (add a DataRaptor Load or Remote Action step at the end of the happy path).

---

### Apex Class Specifications

#### `PRM_ExceptionLogger.cls` — New Methods

```apex
/**
 * Rollback-safe exception logging via Platform Event.
 * ALWAYS use this method when inside a Queueable or any transaction
 * with rollbackOnError = true.
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
        PRM_RequestPayload__c   = payload,
        PRM_RecordId__c         = caseManagerId,
        PRM_RecordObjectName__c = 'IndividualApplication'
    );
    EventBus.publish(evt);
}

/**
 * Direct DML insert — NOT rollback-safe.
 * Only call from synchronous contexts where no rollback is possible.
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
    PRM_ExceptionLog__c log = validateParams(
        processName, integrationType, severityLevel,
        stackTrace, errorMessage, exceptionType,
        lineNumber, correlationId, errorCode,
        sourceSystem, targetSystem, payload
    );
    log.PRM_RecordId__c         = caseManagerId;
    log.PRM_RecordObjectName__c = 'IndividualApplication';
    if (String.isNotBlank(caseManagerId) && caseManagerId.startsWith('0iT')) {
        log.PRM_IndividualApplication__c = caseManagerId;
    }
    insert log;
}
```

#### `PRM_ExceptionLogEventTrigger` (New Apex Trigger)

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
                && String.isNotBlank(evt.PRM_RecordId__c)) {
            log.PRM_IndividualApplication__c = evt.PRM_RecordId__c;
        }
        logs.add(log);
    }
    if (!logs.isEmpty()) {
        insert logs;
    }
}
```

---

### New Custom Fields

**`PRM_ExceptionLog__c` — New Field:**

| Property | Value |
|---|---|
| Field Name | `PRM_IndividualApplication__c` |
| Type | Lookup (IndividualApplication) |
| Label | Case Manager |
| Required | No |
| Delete Constraint | Set Null |
| Description | Links the exception log entry to the IndividualApplication (Case Manager) record for related list display and reporting |

**`PRM_ExceptionLogEvent__e` — New Fields:**

| Field Name | Type | Length | Description |
|---|---|---|---|
| `PRM_RecordId__c` | Text | 18 | Id of the related record (CaseManagerId) |
| `PRM_RecordObjectName__c` | Text | 255 | API name of the related object (e.g., IndividualApplication) |

**`IndividualApplication` (CaseManager) — New Fields:**

| Field Name | Type | Default | Description |
|---|---|---|---|
| `IsNetworkRecordsCreated__c` | Checkbox | false | Set to true by IP3 upon successful creation of all taxonomy/payer network/IFC records |
| `PRM_AsyncProcessingStatus__c` | Picklist | Not Started | `Not Started \| Processing \| Completed \| Failed` — updated at each transaction boundary |

---

## Acceptance Criteria

**AC-1: IP1 Failure — Clean Rollback**

**Given** a practitioner creation submission is in progress,  
**When** `PRM_PractitionerAddressCreation` (IP1) fails mid-execution,  
**Then** all DML from the Container and IP1 is rolled back (no address, facility, location, or HC practitioner records persist), IP2 is never enqueued, IP3 is never enqueued, and a `PRM_ExceptionLog__c` record is created (via Platform Event) linked to the IndividualApplication.

---

**AC-2: IP2 Failure — Exception Log Survives Rollback**

**Given** IP1 has completed successfully (TX1 committed),  
**When** `PRM_ExistingPrimaryPracticeLocationLogicDelg` (IP2) fails at any step (including steps before the `ExistingPrimaryPractice` conditional block),  
**Then**:
- IP2's own DML (HCPF records, provider features, practice-to-practitioner affiliations) is rolled back
- IP3 is never enqueued
- A `PRM_ExceptionLog__c` record is created with:
  - `PRM_ProcessName__c = "PRM_ExistingPrimaryPracticeLocationLogicDelg"`
  - `PRM_IntegrationType__c = "ASYNC"`
  - `PRM_IndividualApplication__c` = the relevant CaseManager Id (lookup populated)
  - `PRM_ErrorMessage__c` = the captured error message
- The exception log appears in the "Exception Logs" related list on the Case Manager record
- `PRM_AsyncProcessingStatus__c` on the CaseManager is set to `Failed`

---

**AC-3: IP3 Failure — Exception Log Survives Rollback**

**Given** IP1 and IP2 have completed successfully (TX1 and TX2 committed),  
**When** `PRM_CreateDelegatedHFNRecords` (IP3) fails during taxonomy, payer network, or IFC creation,  
**Then**:
- IP3's own DML (taxonomy networks, payer networks, IFC records) is rolled back
- A `PRM_ExceptionLog__c` record is created with:
  - `PRM_ProcessName__c = "PRM_CreateDelegatedHFNRecords"`
  - `PRM_IndividualApplication__c` = the relevant CaseManager Id (lookup populated)
- `PRM_AsyncProcessingStatus__c` on the CaseManager is set to `Failed`
- `IsNetworkRecordsCreated__c` remains `false`

---

**AC-4: Happy Path — All Three Transactions Complete**

**Given** a delegated practitioner with 3 practice locations, 3 taxonomies each, and 15 payer networks each,  
**When** the submission is processed end-to-end,  
**Then**:
- All address, facility, location, HCPF, provider feature, taxonomy network, payer network, and IFC records are created
- No governor limit exceptions are logged
- `IsNetworkRecordsCreated__c = true` on the CaseDataManager
- `PRM_AsyncProcessingStatus__c = Completed` on the CaseManager
- No `PRM_ExceptionLog__c` records are created for this submission

---

**AC-5: IP3 Is Invoked Regardless of ExistingPrimaryPractice Condition**

**Given** a delegated practitioner whose `ExistingPrimaryPractice` conditional in IP2 evaluates to **false** (new primary practice, not existing),  
**When** IP2 completes successfully,  
**Then** IP3 (`PRM_CreateDelegatedHFNRecords`) is still enqueued and executes, creating the required taxonomy/network/IFC records.

---

**AC-6: Exception Log Is Linked to Case Manager (Navigable)**

**Given** an exception log is created for a failed IP2 or IP3 execution,  
**When** a Credentialing Specialist opens the Case Manager record,  
**Then** they can see the exception log entry in the "Exception Logs" related list, click into it, and see the `PRM_ErrorMessage__c`, `PRM_ProcessName__c`, and `PRM_StackTrace__c` fields without opening a separate list view or writing a SOQL query.

---

**AC-7: Governor Limit Compliance — 3-Location Practitioner**

**Given** a delegated practitioner with 3 locations × 3 taxonomies × 15 payer networks,  
**When** the full IP chain executes,  
**Then** no SOQL query limit, CPU time limit, heap size limit, or DML limit exceptions are thrown in TX1, TX2, or TX3.

---

**AC-8: Exception Logger — Direct DML Method Is Not Used in Async Context**

**Given** IP2 or IP3 fails and the Catch block fires,  
**When** the exception is logged,  
**Then** `PRM_ExceptionLogger.logExceptionViaEvent()` is called (not `logExceptionDirect()`), and the Platform Event is visible in the event bus within 5 seconds of the failure even when the IP transaction is fully rolled back.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Does `PRM_ExistingPrimaryPracticeLocationLogicDelg` have any steps at seq 1–3 (before the `ExistingPrimaryPractice` block) that could fail? What are they? | Determines whether widening the Try/Catch to seq 1 is needed or if wrapping seq 4+ is sufficient | Technical |
| 2 | What is the exact OmniStudio variable name for capturing the error message inside a Try/Catch Catch block? Is it `%error%`, `%errorMessage%`, or another pattern used in this org? | Required to wire the Catch block's Remote Action `additionalInput` correctly | Technical |
| 3 | Does `PRM_CreateDelegatedHFNRecords` currently read any data from IP2's execution context beyond the 6 fields listed in `additionalInput`? (e.g., facility IDs or practitioner record IDs created by IP2's DML) | If yes, `sendOnlyAdditionalInput: true` will break IP3 and those fields must be added to `additionalInput` | Technical |
| 4 | Is there an existing trigger or Flow subscriber on `PRM_ExceptionLogEvent__e`? If yes, the new `PRM_ExceptionLogEventTrigger` must be compatible with it or replace it. | Deployment risk — duplicate processing or conflict with existing subscriber | Technical |
| 5 | What is the IndividualApplication (CaseManager) Id prefix for this org? (TDD assumes `0iT` — confirm.) | Used in `logExceptionDirect()` to conditionally populate the lookup; wrong prefix = lookup never populated | Technical |
| 6 | Should `failOnStepError` on the new `AddTaxNetworkLogicFromDelg` element (IP3 call from IP2) be `true` or `false`? If `true` and IP3 fails to enqueue (not fails during execution), IP2's TX2 transaction will be rolled back. | Determines whether an IP3 enqueue failure also rolls back IP2's committed work | Product / Technical |
| 7 | Is there a Quick Action, OmniScript button, or retry mechanism being planned for the "partial state" scenario (TX1 committed, TX2 or TX3 failed)? This story does not scope the retry — confirm it is a separate story. | Without retry, partial-state recoveries require manual record creation. This should be tracked as a follow-on P0. | Product |
| 8 | Does the `PRM_ExceptionLogger_Procedure_1` IP already receive `CaseManagerId` in its input context from all calling IPs, or will some callers need to be updated to pass it? | Scope of `PRM_ExceptionLogger IP` version 2 changes may be broader than 2 Remote Action steps | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_AddressLogicContainer` | Integration Procedure | HIGH | Governor limits raised; IP2 invocation mode changed to Queueable; IP3 element deactivated; additionalInput expanded |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` | Integration Procedure | HIGH | Queueable limits added; new IP3 element added; Try/Catch added; this IP now runs in its own transaction |
| `PRM_CreateDelegatedHFNRecords` | Integration Procedure | MEDIUM | Try/Catch added; `IsNetworkRecordsCreated__c` update step added; invocation context changes from Container to IP2 |
| `PRM_ExceptionLogger.cls` | Apex Class | HIGH | New methods added; naming change of direct DML overload; existing callers must be audited |
| `PRM_OmniUtils.cls` | Apex Class | HIGH | New `logExceptionViaEvent` remote entry point; `logException()` and `logTryCatchException()` updated to extract `caseManagerId` |
| `PRM_ExceptionLogEvent__e` | Platform Event | MEDIUM | Two new fields; all existing event publishers unaffected (additive change) |
| `PRM_ExceptionLog__c` | Custom Object | MEDIUM | New lookup field; existing records unaffected; related list configuration needed on Case Manager page layout |
| `PRM_ExceptionLogEventTrigger` | Apex Trigger | HIGH | New trigger — must not conflict with existing `PRM_ExceptionLogEvent__e` subscribers |
| `IndividualApplication` (CaseManager) | Custom Fields | LOW | Two new fields: `IsNetworkRecordsCreated__c`, `PRM_AsyncProcessingStatus__c` |
| `PRM_ExceptionLogger_Procedure_1` | Integration Procedure | LOW | additionalInput addition on 2 steps |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_AddressLogicContainer` propertySetConfig | IP Config | S | JSON property updates only |
| `PRM_AddressLogicContainer` — `ExistingPrimaryAddressLogic` element | IP Element | S | Mode change + 2 additionalInput fields |
| `PRM_AddressLogicContainer` — `AddTaxNetworkLogic` deactivation | IP Config | S | `isActive: false` |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` propertySetConfig | IP Config | S | Limit property additions |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — `AddTaxNetworkLogicFromDelg` element | IP Element | M | New IP Action element with 6 additionalInput fields; placement must be verified |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — Try/Catch + Catch Remote Action | IP Element | M | Requires OmniStudio Try/Catch Block pattern; Catch block wiring to `logExceptionViaEvent` |
| `PRM_CreateDelegatedHFNRecords` — Try/Catch additions | IP Elements (×3) | M | 3 blocks to wrap; Catch block wiring each |
| `PRM_CreateDelegatedHFNRecords` — `IsNetworkRecordsCreated__c` update step | IP Element | S | DataRaptor Load or Remote Action |
| `PRM_ExceptionLog__c` — `PRM_IndividualApplication__c` field | Custom Field | S | Field creation + page layout update |
| `PRM_ExceptionLogEvent__e` — 2 new fields | Custom Fields | S | Additive, no impact on existing |
| `PRM_ExceptionLogEventTrigger` | Apex Trigger | L | New trigger + test class (90%+ coverage) |
| `PRM_ExceptionLogger.cls` — new methods | Apex Class | M | 2 new methods + test coverage additions |
| `PRM_OmniUtils.cls` — updates | Apex Class | L | `logException`, `logTryCatchException`, new `logExceptionViaEvent` entry point; requires careful regression testing |
| `PRM_ExceptionLogger_Procedure_1` | IP Config | S | additionalInput on 2 Remote Action steps |
| CaseManager fields (`IsNetworkRecordsCreated__c`, `PRM_AsyncProcessingStatus__c`) | Custom Fields + Picklist | S | 2 fields + picklist definition + page layout |
| End-to-end integration testing (3-location practitioner) | QA | L | Full TX1→TX2→TX3 chain; sandbox Queueable depth limitation requires manual test plan |

**Total Estimated Effort:** ~7–9 days — **XL**  
*(AI-estimated — validate with team. Apex trigger test class and `PRM_OmniUtils` regression are the highest-variance items.)*

---

## Deployment Checklist

**Metadata (deploy in order — dependencies exist):**
- [ ] `PRM_ExceptionLogEvent__e` — new fields (`PRM_RecordId__c`, `PRM_RecordObjectName__c`)
- [ ] `PRM_ExceptionLog__c` — new lookup field (`PRM_IndividualApplication__c`)
- [ ] `IndividualApplication` — new fields (`IsNetworkRecordsCreated__c`, `PRM_AsyncProcessingStatus__c`)
- [ ] `PRM_ExceptionLogger.cls` — new methods (with test class)
- [ ] `PRM_OmniUtils.cls` — updated methods (with test class)
- [ ] `PRM_ExceptionLogEventTrigger` — new trigger (with test class, 90%+ coverage)
- [ ] `PRM_ExceptionLogger_Procedure_1` — additionalInput additions
- [ ] `PRM_CreateDelegatedHFNRecords` — Try/Catch additions + `IsNetworkRecordsCreated__c` update
- [ ] `PRM_ExistingPrimaryPracticeLocationLogicDelg` — limits + new element + Try/Catch
- [ ] `PRM_AddressLogicContainer` — limits + IP2 mode change + IP3 deactivation

**Verification in Sandbox:**
- [ ] Confirm `PRM_ExceptionLogEvent__e` has no existing trigger that conflicts with `PRM_ExceptionLogEventTrigger`
- [ ] Confirm IndividualApplication Id prefix is `0iT` (or update `logExceptionDirect()`)
- [ ] Audit IP3 input requirements against the 6 fields in `additionalInput`
- [ ] Manual execution test: 1-location practitioner (happy path)
- [ ] Manual execution test: 3-location practitioner (governor limit validation)
- [ ] Manual execution test: forced IP2 failure → verify exception log created + linked to Case Manager
- [ ] Manual execution test: forced IP3 failure → verify exception log created + linked to Case Manager
- [ ] Manual execution test: IP2 step before `ExistingPrimaryPractice` block forced to fail → verify exception log captures this (not just the conditional block)
- [ ] Verify IP3 fires when `ExistingPrimaryPractice` condition evaluates to false
- [ ] Page layout: add "Exception Logs" related list to Case Manager record page
- [ ] Page layout: add `PRM_AsyncProcessingStatus__c` and `IsNetworkRecordsCreated__c` to Case Manager record page

**Post-Deployment Monitoring (First 48 Hours):**
- [ ] Monitor `AsyncApexJob` for IP2/IP3 Queueable jobs — confirm no failures
- [ ] Monitor `PRM_ExceptionLog__c` for new records — confirm none from normal processing
- [ ] Spot-check 3 completed Case Managers — confirm `IsNetworkRecordsCreated__c = true`

---

## Related Stories / Follow-Ons

| Story | Priority | Status | Dependency |
|---|---|---|---|
| Retry mechanism for partial-state (Scenario B/C): Quick Action or OmniScript button to re-invoke IP2 or IP3 for a given Case Manager | P0 | Not scoped — **create immediately** | Requires `PRM_AsyncProcessingStatus__c` field from this story |
| User-facing processing status (Processing → Completed/Failed) visible on Case Manager record page | P1 | Not scoped | Requires `PRM_AsyncProcessingStatus__c` field from this story |
| IBC Professional Practitioner Address Creation performance refactor (`PRM_PractitionerAddressCreation` — 100+ steps) | P0 | Not scoped | Independent; same governor limit pattern |
| PDA Review Network Update timeout (`PRM_InitialCredPDAReviewUpdateSubIPInsert`) | P1 | Not scoped | Independent |
