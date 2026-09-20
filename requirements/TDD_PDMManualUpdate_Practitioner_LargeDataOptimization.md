# High Level Technical Design Document
## PDM Manual Update - Practitioner Large Data Optimization

**Vertical:** Provider Network Management (PNM) - Provider Data Management (PDM)
**Program:** Large-Volume Governor Limit Remediation (Wave 2)
**Predecessor Effort:** Practitioner Creation Performance (Wave 1 - in-flight)
**Document Owner:** Salesforce Architecture
**Audience:** Senior Salesforce Developer, QA Lead, Project Manager
**Status:** Draft for IBX review
**Date:** 2026-04-23

---

## 1. Executive Summary

### 1.1 Problem Statement

The **PDM Manual Update - Practitioner** guided flow suffers from the same class of Salesforce governor limit failures that previously brought down the **Delegated Practitioner Creation** flow. When a Credentialing or Network Maintenance user performs a manual update against a practitioner record with 3 or more practice locations, the underlying Integration Procedure (IP) chain executes the entire update path inside a single synchronous Apex transaction. That transaction approaches or breaches:

- SOQL query limit (100 synchronous, 200 async)
- CPU time limit (10,000 ms chainable, 60,000 ms async)
- Apex heap size (6-12 MB depending on context)
- DML statements and rows

When the ceiling is hit, the OmniScript UI freezes for 3-8 minutes, partial data is written to the database with no error surfaced to the user, and the Credentialing team files a support ticket. The same failure mode that generated 15-20 tickets per week for the Creation flow is now the fastest-growing source of PDM operational incidents.

### 1.2 Business Impact

| Dimension | Observed Impact |
|---|---|
| UI freeze duration | 3-8 minutes for practitioners with 3+ locations; effective timeout at 10 minutes |
| Support ticket volume | Trending upward; currently combined with Creation tickets in the same queue |
| Data integrity risk | Update flow is partially idempotent (upserts); however, cross-object partial state (e.g., affiliations refreshed but network records stale) still produces credentialing-quality defects downstream |
| Operational cost | 1-2 hours per incident for Data Admin to manually reconcile; QC downstream picks up inconsistent data |
| Reputational risk | Network Maintenance teams have begun rejecting PDM updates with many locations, routing them through Creation-flow workarounds |

### 1.3 Proposed Approach

Apply the **Queueable Transaction Splitting** pattern designed and (as of Wave 1) substantially built for Practitioner Creation to the PDM Manual Update IP chain:

- **TX1 (Synchronous / Chainable):** Container IP + first child IP (address/facility/location upserts) executes inside the user-facing OmniScript transaction.
- **TX2 (Queueable):** Existing primary practice location upsert logic (HCPF, provider features, affiliations, CDM update) executes in a separate Apex transaction.
- **TX3 (Queueable chained from TX2):** Taxonomy network, payer network, and IFC upsert records execute in a third Apex transaction with elevated async governor limits.

The design **reuses** - without modification where possible - the shared infrastructure already being delivered by the Practitioner Creation effort:

- `PRM_ExceptionLogEvent__e` Platform Event (with `PRM_RecordId__c` / `PRM_RecordObjectName__c` fields)
- `PRM_ExceptionLogEventTrigger`
- `PRM_ExceptionLogger.logExceptionViaEvent()`
- `PRM_OmniUtils` caseManagerId routing
- `PRM_FailedRecordStaging__c` custom object and list views
- `PRM_AsyncProcessingStatus__c` and `IsNetworkRecordsCreated__c` fields on IndividualApplication
- Data Admin "Network Creation Errors - Needs Review" list view and the "Mark Resolved & Route to QC" Quick Action

Because updates are more idempotent than creates, the rollback strategy is simpler and the retry story is meaningfully cheaper. Net new development is limited to the PDM-specific Integration Procedures, a small number of update-mode Apex adapters, and the UI plumbing required to surface async status on the PDM record page.

---

## 2. Scope

### 2.1 OmniScript and Integration Procedures In Scope

> **Assumption requiring IBX confirmation:** The PDM Manual Update flow is presumed to follow the same Container IP -> 3 child IP pattern as Delegated Practitioner Creation, with the only structural difference being that each child IP performs **upsert** rather than **insert** DML. Exact OmniScript key and IP keys must be confirmed by the IBX OmniStudio team before implementation begins. Names used below are working placeholders.

| Component | Working Key (to confirm) | Role |
|---|---|---|
| OmniScript | `PRM_PDMManualUpdatePractitioner` | Entry point; captures user edits to an existing practitioner record |
| Container IP | `PRM_PDMUpdateLogicContainer` | Orchestrator; calls three child IPs in sequence |
| Child IP 1 | `PRM_PractitionerAddressUpdate` | Address, healthcare facility, location, HC practitioner base record upserts |
| Child IP 2 | `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` | HCPF, provider feature (ACC / AA), practice-to-practitioner affiliation, CDM update |
| Child IP 3 | `PRM_CreateOrUpdateDelegatedHFNRecords` | Taxonomy network, payer network, IFC record upserts |

### 2.2 Objects Touched During a Manual Update

- `IndividualApplication` (Case Manager / CDM anchor)
- `CaseDataManager` custom object
- `Address__c`, `Location__c`, `HealthcareFacility`, `HealthcarePractitioner`
- `HealthcarePractitionerFacility` (HCPF)
- `ProviderFeature__c`, `AffirmingCareCategory__c`, `ProviderFeatureAssistiveAid__c`
- Practice-to-Practitioner affiliation object(s)
- `HealthcarePlanNetwork`, `PracticeLocationNetwork__c`, `TaxonomyNetworkAssignment__c`, `PayerNetworkAssignment__c`, `IFCCodeAssignment__c` (or the IBX-specific equivalents)

### 2.3 Out of Scope

- Restructuring `PRM_PractitionerAddressUpdate` (IP1) into smaller IPs - tracked separately as "IBC Professional / PDM Address IP decomposition" and will not be attempted in this effort.
- User-facing progress banner LWC, email success/failure templates, queue-based case routing, and the automated daily retry batch - these are Wave 1 Phase 1B / Phase 2 items for Practitioner Creation and will be inherited once delivered, not rebuilt here.
- PDM **Manual Update for Account / Facility** (non-practitioner) flows - separate governor-limit remediation story.
- Any changes to Precisely address validation, PAR provider search, or upstream data sourcing integrations.
- Automated retry scheduler. Manual retry via the existing Data Admin Quick Action is sufficient for Wave 2.

---

## 3. Current Architecture

### 3.1 Presumed IP Chain Structure (to confirm)

```
PRM_PDMManualUpdatePractitioner (OmniScript)
  |
  v
PRM_PDMUpdateLogicContainer (Container IP)  --- rollbackOnError = true
  |
  |-- Seq 1: PRM_PractitionerAddressUpdate                (Chainable)
  |          upserts Address / Location / Facility / HCPractitioner / Identifiers
  |
  |-- Seq 2: PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate   (Chainable)
  |          upserts HCPF, Provider Features, Affiliations, updates CDM
  |
  |-- Seq 3: PRM_CreateOrUpdateDelegatedHFNRecords        (Queueable but awaited)
             upserts Taxonomy Network, Payer Network, IFC
```

### 3.2 Presumed Governor Limits (pre-remediation)

Based on direct parallels to the Creation chain:

| IP | Queries | CPU (ms) | Heap (MB) |
|---|---|---|---|
| `PRM_PDMUpdateLogicContainer` | 50 | 2,000 | default |
| `PRM_PractitionerAddressUpdate` (IP1) | 100 | 10,000 | 6 |
| `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` (IP2) | 50 | 2,000 | default |
| `PRM_CreateOrUpdateDelegatedHFNRecords` (IP3) | 120 async | 40,000 async | 6 async |

### 3.3 Failure Modes

| Mode | Trigger | UI Symptom | Support Ticket Symptom |
|---|---|---|---|
| SOQL 100 breach in IP1 | Practitioner has >=3 locations with historical address/facility refactoring | OmniScript returns a generic "Save failed" after 2-3 minutes; partial address updates | "Updated practitioner X, but only some addresses saved" |
| CPU 10,000 ms breach in the chainable window | IP2 recomputes affiliations for many locations synchronously | UI freeze; eventually fails with `UNEXPECTED_SCRIPT_ERROR` or OmniScript timeout | "Update spun for 5+ minutes, had to refresh" |
| Heap 12 MB in IP3 | Large network refresh (45-90 `HealthcarePlanNetwork` upserts plus existing-record SOQL payload) | OmniScript returns but network records are inconsistent | "Missing payer networks after PDM update" |
| Async Queueable CPU 60s in IP3 | Practitioner has >=5 locations | IP3 throws inside the Queueable; DML is rolled back; **no exception log persisted** because direct-DML logging rolls back with the transaction | Silent failure; discovered only when downstream PSV catches missing records |

### 3.4 Parallels and Distinctions vs. the Creation Chain

**Parallels:**
- Same object graph, same IP chain shape, same OmniStudio runtime constraints.
- Same silent-failure pattern caused by direct-DML exception logging inside a transaction with `rollbackOnError = true`.
- Same dependency on Case Manager / IndividualApplication as the anchor record.

**Distinctions:**
- IP1/IP2/IP3 in the update flow perform **upserts** (keyed by external IDs, NPI, or record Id) rather than inserts. A re-execution generally converges on the same end state rather than producing duplicates.
- The initial record set is non-empty. IP2 and IP3 must refresh or delete stale child records (for example, payer network rows that no longer apply after a plan change), not merely insert new ones.
- The update flow is invoked multiple times over the lifetime of a practitioner, so any performance or data-integrity defect compounds.
- Users triggering PDM updates are typically Network Maintenance, not Credentialing - a different persona than Wave 1, but the same support channel.

---

## 4. Proposed Architecture

### 4.1 Transaction Split

Apply the Wave 1 TX1/TX2/TX3 pattern directly:

- **TX1 (Synchronous / Chainable):** `PRM_PDMUpdateLogicContainer` + `PRM_PractitionerAddressUpdate` (IP1). Governor ceilings elevated on the container as in Wave 1. `rollbackOnError = true` provides full rollback for TX1.
- **TX2 (Queueable):** `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` (IP2) is invoked from the container with `useQueueable: true` and `disableChainable: true`. Runs in its own Apex transaction with `queueableChainable*` limits (150 queries / 60,000 ms CPU / 12 MB heap).
- **TX3 (Queueable chained from IP2):** `PRM_CreateOrUpdateDelegatedHFNRecords` (IP3) is invoked from **inside IP2 at level 0 (top-level, not inside any conditional block)** with `useQueueable: true`. Runs in its own Apex transaction with `queueableChainable*` limits (120 queries / 40,000 ms CPU / 6 MB heap).

The IP3 invocation from within the container is **deactivated** - IP3 runs only from IP2, matching the Wave 1 decision.

### 4.2 Before / After Diagram

```
BEFORE (single transaction - fails at scale):

+------------------+
|   OmniScript     |
|  (UI blocking)   |
+--------+---------+
         |
         v
+--------+------------------------------------------------+
|                  Container IP (chainable)              |
|                                                        |
|  IP1 (upserts)  ->  IP2 (upserts)  ->  IP3 (upserts)   |
|  rollbackOnError = true for entire chain               |
|                                                        |
|  SOQL/CPU/Heap budget shared across all three IPs      |
|  -> exceeds limits when 3+ locations                   |
+--------------------------------------------------------+
         |
         v
  (UI waits 5-8 minutes, then times out or partial state)


AFTER (three Apex transactions - each within limits):

+------------------+
|   OmniScript     |
|  (waits for TX1  |
|  only)           |
+--------+---------+
         |
         v
+--------+-------------------------------+     ======== TX1 (sync) ========
|  Container IP (chainable, elevated)   |      governor budget: dedicated
|                                       |
|  IP1 (upserts)                        |      rollbackOnError = true
|  rollbackOnError = true               |      (full rollback on TX1 fail)
|                                       |
|  enqueues IP2 via useQueueable        |
+--------+------------------------------+
         | (UI returns here)
         |                                    [async hop - new transaction]
         v
+--------+------------------------------+     ======== TX2 (queueable) ====
|  IP2 (PDM update)                     |      governor budget: renewed
|                                       |
|  upserts HCPF / features / affils     |      rollbackOnError = true
|  updates CDM                          |      (rollback within TX2 only)
|                                       |
|  enqueues IP3 via useQueueable        |
|  Try/Catch wraps seq 1+               |      Catch -> logExceptionViaEvent
+--------+------------------------------+
         |                                    [async hop - new transaction]
         v
+--------+------------------------------+     ======== TX3 (queueable) ====
|  IP3 (PDM HFN update)                 |      governor budget: renewed
|                                       |
|  upserts Taxonomy / Payer / IFC       |      rollbackOnError = true
|                                       |      (rollback within TX3 only)
|  Try/Catch wraps core logic           |      Catch -> logExceptionViaEvent
|                                       |
|  Sets IsNetworkRecordsCreated = true  |
|  Sets PRM_AsyncProcessingStatus__c    |
|        = 'Completed'                  |
+---------------------------------------+
```

### 4.3 Surfacing Async Status Back to the UI

The UI-side contract is **reused** from Wave 1:

- `PRM_AsyncProcessingStatus__c` on IndividualApplication: set to `Processing` by the Container as the first step of TX1; to `Failed` by the IP2/IP3 Catch block; to `Completed` by IP3 on its happy-path final step.
- `IsNetworkRecordsCreated__c` on IndividualApplication: set to `true` by IP3 on its happy-path final step.
- Any progress banner LWC or email notification delivered as part of Wave 1 Phase 1B will pick up the PDM flow automatically because the status field and event contract are the same. No additional LWC work is required in this Wave.
- Duplicate-submission guard: the OmniScript's pre-submit validation reads `PRM_AsyncProcessingStatus__c` and blocks re-submission while it equals `Processing`. Reused from Wave 1.

---

## 5. Reuse From Practitioner Creation

Every component delivered by Wave 1 has been classified below. Components marked **Direct** require **zero additional engineering effort** for Wave 2 and consume the Wave 1 deployment as-is.

| Component | Reuse Type | Notes |
|---|---|---|
| `PRM_ExceptionLogEvent__e` Platform Event | Direct | Same publisher contract. No new fields required. |
| `PRM_ExceptionLogEvent__e` new fields `PRM_RecordId__c`, `PRM_RecordObjectName__c` | Direct | PDM IPs populate them identically (CaseManagerId, "IndividualApplication"). |
| `PRM_ExceptionLogEventTrigger` (Apex trigger) | Direct | No change. Trigger processes all publishers indifferently. |
| `PRM_ExceptionLog__c` custom object + `PRM_IndividualApplication__c` lookup | Direct | Reused as-is. |
| `PRM_ExceptionLog__c` fields `PRM_NetworkErrorResolutionStatus__c`, `PRM_AssignedTo__c`, `PRM_ResolutionNotes__c` | Direct | Reused as-is. |
| `PRM_ExceptionLogger.logExceptionViaEvent()` | Direct | Same signature. Called from PDM IP2 / IP3 Catch blocks. |
| `PRM_ExceptionLogger.logExceptionDirect()` (rollback-unsafe variant) | Reference | Do NOT call from PDM IP2 / IP3. Documentation reminder only. |
| `PRM_OmniUtils.logException` / `logTryCatchException` caseManagerId extraction | Direct | Reused as-is for `PRM_ExceptionLogger_Procedure_1`. |
| `PRM_ExceptionLogger_Procedure_1` IP (with `caseManagerId` passthrough) | Direct | PDM IPs supply `caseManagerId` the same way. |
| `PRM_FailedRecordStaging__c` object + all 42 fields + validation rules | Direct | Reused as-is. `PRM_SourceProcess__c` accepts the PDM IP keys without schema change. |
| `PRM_FailedRecordStaging__c` list views (All Failed Records, Pending - Awaiting Fix, Stale Records, By Process, etc.) | Adapted | Existing "By Process - Practitioner Creation" list view is widened to include PDM IP keys in its filter. "By Process - PDM Manual Update" new list view added (trivial clone). |
| `PRM_FailedRecordStaging__c` permission sets | Direct | Same operations teams. No new personas. |
| `IndividualApplication.PRM_AsyncProcessingStatus__c` picklist | Direct | Same value set. No new picklist values. |
| `IndividualApplication.IsNetworkRecordsCreated__c` checkbox | Direct | Reused as the "done" flag on the PDM path too. |
| "Network Creation Errors - Needs Review" list view on `PRM_ExceptionLog__c` | Adapted | Filter widened: `PRM_ProcessName__c IN (..., 'PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate', 'PRM_CreateOrUpdateDelegatedHFNRecords')`. |
| "Mark Resolved & Route to QC" Quick Action / Screen Flow on IndividualApplication | Direct | Fires on `PRM_AsyncProcessingStatus__c = 'Failed'` regardless of which flow produced the failure. No change. |
| Case Manager "Exception Logs" related list and "Failed Records" related list | Direct | Same related lists surface PDM failures automatically because the lookup field is populated identically. |
| Data Admin permission set | Direct | Same team is responsible for PDM failures as for Creation failures. |
| IP configuration pattern: container governor ceiling bump + IP2 `useQueueable` + IP3-from-IP2 at level 0 + wide Try/Catch + `logExceptionViaEvent` in Catch | Adapted | Pattern is transplanted to the PDM IPs; configuration values differ only where measured load differs. |
| Sandbox test procedure for the TX2 -> TX3 Queueable hop | Direct | Same runbook. Only the test data set changes (update of an existing practitioner vs. creation of a new one). |

**Effort savings estimate:** Direct reuse accounts for **approximately 70-75% of the total infrastructure** that would otherwise be required if this Wave were being built standalone. Quantified in Section 9.

---

## 6. Net New Development

Items that must be built or configured specifically for PDM Manual Update:

### 6.1 Integration Procedures

| IP | Change | Notes |
|---|---|---|
| `PRM_PDMUpdateLogicContainer` | Elevate chainable governor limits (queries 50 -> 120, CPU 2,000 -> 10,000 ms, heap default -> 6 MB, plus DML statements / rows / query rows). Change the IP2 invocation element from chainable to `useQueueable: true`, `disableChainable: true`. Deactivate any direct IP3 invocation from the container. Extend `additionalInput` on the IP2 invocation to include all data that IP3 will need (RecordsToUpdate, FacilityPractitionerTxNw, and any update-specific fields such as original-value maps required for delta detection). Add a Remote Action or DataRaptor Load at the first step that sets `PRM_AsyncProcessingStatus__c = 'Processing'`. | Mirrors Wave 1 4.1. |
| `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` (IP2) | Add `queueableChainable*` governor overrides (150 / 60,000 / 12). Raise chainable limits. Add a new top-level `AddTaxNetworkLogicFromPDMUpdate` element at `level: 0`, `sequenceNumber: 6.1` (after `ResponseForIp`) that invokes IP3 via `useQueueable: true`. Wrap all steps from seq 1 onward in a Try/Catch; Catch block Remote Action calls `PRM_OmniUtils.logExceptionViaEvent` with `caseManagerId` and sets `PRM_AsyncProcessingStatus__c = 'Failed'`. | Mirrors Wave 1 4.2 but uses update semantics (IP2's internal DML is upsert). |
| `PRM_CreateOrUpdateDelegatedHFNRecords` (IP3) | Wrap main logic blocks (`CB_LogicExecuteTxNetwork`, `CB_LogicExecuteLocNetwork`, `CB_ExecuteIFCLogic` or their PDM equivalents) in Try/Catch. Catch calls `logExceptionViaEvent`. Final step on the happy path updates `PRM_AsyncProcessingStatus__c = 'Completed'` and `IsNetworkRecordsCreated__c = true` on the CaseDataManager / IndividualApplication. Optionally run DML in partial-success mode (`allOrNone = false`) with `PRM_FailedRecordStaging__c` rows produced per failed sObject - matching the Wave 1 approach for network records. | IP3 for PDM may already exist as a distinct IP or may be a shared IP across Create / Update - confirm with IBX before implementation. If shared, add a mode parameter to avoid branching. |

### 6.2 Apex

| Class / Method | Change Type | Description |
|---|---|---|
| `PRM_OmniUtils.cls` | Minor addition (optional) | Add a method overload or input flag so the PDM IPs can annotate the exception event with a `sourceFlow` hint of `PDM_MANUAL_UPDATE`. This makes the Data Admin list views trivially filterable without schema changes. |
| Update-mode upsert helpers in IP2 | New | If IP2 needs a bulkified upsert utility that respects external IDs, add it to `PRM_ExistingPractitionerUpdateService.cls` (new class). If the Wave 1 equivalents are already sufficient, skip. |
| Update-mode delta detection | Potentially new | If IP2 or IP3 compares incoming values to existing values to decide whether to DML, a small helper class `PRM_UpdateDeltaComputer.cls` may be warranted to keep the IPs deterministic and testable. Confirm after inspecting the actual IP bodies. |

No new Platform Events. No new Triggers. No new Queueable Apex classes beyond what OmniStudio synthesizes for `useQueueable: true`.

### 6.3 DataRaptors

| DataRaptor | Reuse Status |
|---|---|
| Any DataRaptor that produces **insert** payloads in Wave 1 must be inspected for upsert equivalence in PDM. If the existing DataRaptor uses insert-by-default and cannot be safely upserted, a parallel DataRaptor with `operation: upsert` and the appropriate external ID must be created. | Likely M effort: 2-4 new DataRaptors, depending on how much Wave 1 re-used existing PDM DataRaptors in the other direction. |

### 6.4 Custom Fields / Objects

**None required.** Every field introduced by Wave 1 is sufficient:

- `PRM_AsyncProcessingStatus__c` (IndividualApplication) - reused
- `IsNetworkRecordsCreated__c` (IndividualApplication) - reused
- `PRM_IndividualApplication__c` (PRM_ExceptionLog__c) - reused
- `PRM_RecordId__c` / `PRM_RecordObjectName__c` (PRM_ExceptionLogEvent__e) - reused
- `PRM_FailedRecordStaging__c` and all of its fields - reused

### 6.5 List Views / Page Layout Touches

| Item | Change |
|---|---|
| `PRM_ExceptionLog__c` list view "Network Creation Errors - Needs Review" | Add the two PDM IP keys to the `PRM_ProcessName__c IN (...)` filter. |
| `PRM_FailedRecordStaging__c` list view "By Process - Practitioner Creation" | Either widen the filter to include PDM IP keys, or clone to a new "By Process - PDM Manual Update" list view. Recommend the clone to preserve Wave 1 semantics. |
| PDM record page | Add `PRM_AsyncProcessingStatus__c` and `IsNetworkRecordsCreated__c` to the same Lightning page that Wave 1 modified for Credentialing users. Minor page layout task. |

### 6.6 Configuration and Runbook

- Sandbox verification of the TX2 -> TX3 hop against a PDM update scenario (see Testing Strategy).
- Deployment checklist update to include PDM IP deployments in the order defined in Wave 1's checklist.

---

## 7. Exception Handling and Rollback Strategy

### 7.1 Adapted From Wave 1 Section 5

The exception-handling design from `TDD_PractitionerCreation.txt` Section 5 applies with three adjustments:

1. `PRM_ProcessName__c` values in the exception log will be the PDM IP keys, not the Creation IP keys.
2. The Try/Catch in IP2 must wrap all steps from seq 1 forward (Wave 1 Improvement #4 - do not repeat Wave 1's initial mistake of wrapping only the conditional block).
3. The `logExceptionViaEvent` route must be used everywhere. The `logExceptionDirect` variant is never called from the PDM IPs. This is the single largest regression risk because both methods have similar signatures; the Wave 1 rename and comments are preserved to enforce the contract.

### 7.2 Why Updates Are More Idempotent Than Creates

- IP1 (address / facility / location) uses upsert keyed on NPI, external IDs, or record Id. A re-run of a failed IP1 converges on the same row rather than creating a duplicate address.
- IP2 (HCPF, provider feature, affiliation) uses upsert keyed on composite external IDs (practitioner + facility + effective date). Re-running a failed IP2 refreshes the existing rows.
- IP3 (taxonomy / payer / IFC) uses upsert keyed on network + facility + practitioner. Re-running a failed IP3 writes the same rows.

The practical implication: if TX2 commits and TX3 fails, a manual retry of TX3 alone is generally safe. There is no duplication risk analogous to the Creation flow's "two sets of taxonomy records" failure mode. This materially simplifies the operations team's remediation playbook.

### 7.3 Partial State Recovery Matrix

| Scenario | TX1 | TX2 | TX3 | State After Failure | Recommended Recovery |
|---|---|---|---|---|---|
| A | fail | not enqueued | not enqueued | Clean - TX1 rolled back automatically | None. Exception log informs user. |
| B | commit | fail | not enqueued | IP1 upserts committed; IP2 upserts rolled back; IP3 never ran | **Retry IP2 alone** via manual re-submission or the "Mark Resolved & Route to QC" workflow. Because IP2 is upsert-based, the retry is safe. |
| C | commit | commit | fail | IP1 + IP2 committed; IP3 upserts rolled back | **Retry IP3 alone** via the same mechanism. Because IP3 is upsert-based and its external IDs are stable, the retry is safe. |
| D | commit | commit | commit | Happy path | None. |

The retry mechanism does **not** have to be automated for Wave 2. Manual retry via the existing Data Admin workflow is acceptable because:

- Idempotent upserts remove the most expensive failure mode (duplicate records).
- The "Mark Resolved & Route to QC" Quick Action already handles Scenario B/C triage.
- Downstream PSV / QC checks catch any remaining drift before credentialing is finalized.

### 7.4 Use of PRM_FailedRecordStaging__c for Retry

When IP3 runs DML in partial-success mode (`allOrNone = false`), each failed sObject is serialized into a `PRM_FailedRecordStaging__c` row with:

- `PRM_Status__c = 'Pending'`
- `PRM_TargetObject__c = <API name>` (for example `HealthcarePlanNetwork`)
- `PRM_Payload__c` = JSON of the failed sObject (full record for deterministic replay)
- `PRM_CaseManager__c` = IndividualApplication Id
- `PRM_ExceptionLog__c` = lookup to the Wave 1 exception log, if one was created
- `PRM_SourceProcess__c = 'PRM_CreateOrUpdateDelegatedHFNRecords'`
- `PRM_ErrorMessage__c` and `PRM_StatusCode__c` from the SaveResult

Operations triage the staging rows through the Wave 1 list views. Because upserts are idempotent, a replay of the stored payload is safe even after manual data correction upstream - no deduplication logic is required in the retry path.

### 7.5 Exception Logging Integration Points

Same Try/Catch + `logExceptionViaEvent` pattern as Wave 1:

```
IP2 Catch Block:
  processName     = "PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate"
  integrationType = "ASYNC"
  severityLevel   = "Error"
  errorMessage    = <captured>
  caseManagerId   = %CaseManagerId%
  payload         = <serialized input context>

IP3 Catch Block:
  processName     = "PRM_CreateOrUpdateDelegatedHFNRecords"
  integrationType = "ASYNC"
  caseManagerId   = %CaseManagerId%
```

Both flow to the same `PRM_ExceptionLogEventTrigger` and produce `PRM_ExceptionLog__c` rows linked to IndividualApplication via the lookup.

---

## 8. Implementation Timeline

**Precondition:** Wave 1 (Practitioner Creation) shared infrastructure is in its final sprint when this plan starts. Specifically, the following must be merged and deployed at least to QA before PDM Manual Update net-new work begins:

- `PRM_ExceptionLogEvent__e` schema changes
- `PRM_ExceptionLogEventTrigger`
- `PRM_ExceptionLogger.logExceptionViaEvent()`
- `PRM_OmniUtils` caseManagerId routing
- `PRM_FailedRecordStaging__c` object
- `IndividualApplication.PRM_AsyncProcessingStatus__c` and `IsNetworkRecordsCreated__c`
- Data Admin list view and Quick Action

This is treated as a **hard dependency**. PDM work is not scheduled to run in parallel with shared-infra build.

### 8.1 Sprint Plan (2-week sprints)

| Sprint | Window | Focus | Deliverables | Exit Criteria |
|---|---|---|---|---|
| Sprint 0 | Weeks 1-2 | Discovery and confirmation | IBX OmniStudio team confirms exact PDM OmniScript and IP keys, current IP step counts, and whether IP3 is shared with Creation. IP input/output contract audit. Identify any update-mode DataRaptors that need to be cloned. | Signed-off IP inventory and assumption list. |
| Sprint 1 | Weeks 3-4 | Container + IP1 (TX1) | Governor limit elevation on `PRM_PDMUpdateLogicContainer`. Set `PRM_AsyncProcessingStatus__c = 'Processing'` at the first step. Change IP2 invocation to `useQueueable`. Deactivate any direct IP3 invocation. Extend additionalInput. Update-mode DataRaptor clones if any are required. | TX1 passes happy path and forced-failure sandbox tests. Exception log produced on failure. |
| Sprint 2 | Weeks 5-6 | IP2 (TX2) | Queueable governor overrides. Wide Try/Catch from seq 1. Catch -> `logExceptionViaEvent`. Add `AddTaxNetworkLogicFromPDMUpdate` element at level 0 after `ResponseForIp`. Status-field update in Catch. | TX1 -> TX2 hop fires correctly in sandbox with real data. Exception log produced on forced IP2 failure. |
| Sprint 3 | Weeks 7-8 | IP3 (TX3) and staging integration | Try/Catch wrappers in IP3. `allOrNone = false` for bulk upserts (taxonomy, payer, IFC). Populate `PRM_FailedRecordStaging__c` on per-row failure. Final-step status-field update on happy path. Clone "By Process - PDM Manual Update" list view. Widen the "Network Creation Errors" list view filter. | TX1 -> TX2 -> TX3 hop validated end-to-end in full sandbox with 1, 3, and 5 location test data. Failed records correctly appear in staging and in the exception log list view. |
| Sprint 4 | Weeks 9-10 | Hardening, UAT, deployment | Full regression pass on Creation flow to confirm no regression from shared-infra re-touch. Integration tests with Wave 1's Data Admin Quick Action on PDM-produced failures. Documentation update. UAT with Network Maintenance team. Production deployment with 48-hour post-deploy monitoring playbook. | Production deploy complete; monitoring dashboard shows TX2 / TX3 Queueable jobs running without governor-limit exceptions. |

**Total elapsed time: 10 weeks (5 sprints of 2 weeks, including a discovery sprint).** Net-new implementation work alone is 6-8 weeks (Sprints 1-3 plus hardening).

---

## 9. Effort Estimation Table

Units: Story Points (SP) on a Fibonacci scale, calibrated against Wave 1 actuals. Secondary column expresses person-days at roughly 0.6 days / SP.

| # | Component / Story | Category | SP | Days | Owner |
|---|---|---|---|---|---|
| 1 | IBX assumption audit (OmniScript, IP keys, IP3 sharing) | New | 3 | 2 | Dev + BA |
| 2 | `PRM_PDMUpdateLogicContainer` governor ceiling updates | Adapted | 2 | 1 | Dev |
| 3 | `PRM_PDMUpdateLogicContainer` IP2 invocation mode change + additionalInput extension | Adapted | 3 | 2 | Dev |
| 4 | `PRM_PDMUpdateLogicContainer` set `PRM_AsyncProcessingStatus__c` at first step | Adapted | 1 | 0.5 | Dev |
| 5 | `PRM_PDMUpdateLogicContainer` deactivate direct IP3 invocation | Adapted | 1 | 0.5 | Dev |
| 6 | `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` queueable governor overrides | Adapted | 1 | 0.5 | Dev |
| 7 | IP2 add `AddTaxNetworkLogicFromPDMUpdate` element at level 0 | Adapted | 3 | 2 | Dev |
| 8 | IP2 wide Try/Catch from seq 1 + `logExceptionViaEvent` in Catch + status Failed | Adapted | 3 | 2 | Dev |
| 9 | IP3 Try/Catch around core logic blocks + `logExceptionViaEvent` | Adapted | 3 | 2 | Dev |
| 10 | IP3 happy-path final step (`PRM_AsyncProcessingStatus__c = Completed`, `IsNetworkRecordsCreated__c = true`) | Adapted | 1 | 0.5 | Dev |
| 11 | IP3 partial-success DML (`allOrNone = false`) + `PRM_FailedRecordStaging__c` row creation | Adapted | 5 | 3 | Dev |
| 12 | Update-mode DataRaptor clones (estimated 2-4 new DRs) | New | 5 | 3 | Dev |
| 13 | Optional `PRM_ExistingPractitionerUpdateService.cls` upsert helpers | New | 3 | 2 | Dev |
| 14 | Optional `PRM_UpdateDeltaComputer.cls` delta helpers | New | 2 | 1 | Dev |
| 15 | `PRM_OmniUtils` optional `sourceFlow` annotation | New | 1 | 0.5 | Dev |
| 16 | Widen "Network Creation Errors - Needs Review" list view filter | Adapted | 1 | 0.5 | Admin |
| 17 | Clone "By Process - PDM Manual Update" list view on staging object | Adapted | 1 | 0.5 | Admin |
| 18 | Add `PRM_AsyncProcessingStatus__c` / `IsNetworkRecordsCreated__c` to PDM record page | Reused | 1 | 0.5 | Admin |
| 19 | `PRM_ExceptionLogEvent__e`, trigger, logger, OmniUtils, staging object, fields, Quick Action, Data Admin perm set, related lists | Reused | 0 | 0 | (Wave 1) |
| 20 | Unit test coverage for new service/helper classes (items 13, 14) | New | 3 | 2 | Dev |
| 21 | Integration test scripts for 1 / 3 / 5 location PDM updates | New | 5 | 3 | QA |
| 22 | Forced-failure test scripts (TX1 / TX2 / TX3 each) | New | 3 | 2 | QA |
| 23 | UAT coordination with Network Maintenance team | New | 3 | 2 | QA + PM |
| 24 | Deployment runbook update + production cutover monitoring | New | 3 | 2 | Dev + Admin |
| **Total** | | | **57 SP** | **~33 days** | |

**Comparison to a standalone (no shared-infra reuse) build:** The Wave 1 build consumed approximately 30-38 developer days across shared infrastructure plus Creation-specific work (per `US_PractitionerCreation_Complete_Implementation.md`). If PDM Manual Update had to rebuild the Platform Event, trigger, logger, staging object, status fields, list views, and Quick Action from scratch, the estimate would be approximately **+20 days** (~33 SP). Reuse therefore saves **approximately 35-40%** of the total effort that would otherwise be required.

---

## 10. Key Risks and Mitigations

Adapted from the 8-risk register in `TDD_Gap_Analysis.md`, augmented with update-specific risks.

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | `logException` vs `logExceptionViaEvent` routing bug - a developer accidentally uses the direct-DML variant in a PDM Catch block, causing silent failure | High | Wave 1 rename (`logExceptionDirect` with deprecation comment) is already in place. Code-review checklist item. Unit tests assert that no PDM IP's configured Catch block references the direct variant. |
| 2 | IP3 placement inside IP2's conditional block (not at level 0) - causes IP3 to never run for updates that don't touch the existing primary practice | High | Lock placement at `level: 0`, `sequenceNumber: 6.1`, after `ResponseForIp` in IP2. Sandbox test case: a PDM update that modifies only secondary locations must still trigger IP3. |
| 3 | Retry mechanism not scoped - operations team has no defined path for partial-state recovery | High (mitigated for updates) | The Wave 1 Data Admin "Mark Resolved & Route to QC" Quick Action + manual re-submission is accepted as the Wave 2 retry path. The idempotent upsert semantics of the PDM flow make this a meaningfully lower risk than the same gap would be for the Creation flow. |
| 4 | TX1 still blocks the UI for very large PDM updates (>=5 locations) because IP1 remains synchronous | Medium | Out of scope for this Wave (noted in Scope). IP1 decomposition is tracked as a separate effort. Monitor post-deploy; if P95 TX1 duration exceeds 4 minutes, initiate that story. |
| 5 | Queueable chain depth cannot be validated in sandbox unit tests | Medium | Sandbox test strategy inherited from Wave 1. Manual integration test runbook executed against a full sandbox with real PDM data before production cutover. Not relying on `Test.startTest` / `stopTest` coverage for the TX2 -> TX3 hop. |
| 6 | Try/Catch scope in IP2 too narrow - errors in pre-conditional steps leave orphaned TX1 state with no exception log | Medium | Enforce wrapping from seq 1 onward, same as Wave 1 Improvement #4. Code review verifies `fromSequence = 1`. |
| 7 | `sendOnlyAdditionalInput: true` on the `AddTaxNetworkLogicFromPDMUpdate` element may strip PDM-specific inputs that IP3 depends on | Medium | Pre-build audit (Sprint 0 / Sprint 1 discovery) of IP3's read set. Any input IP3 reads must be explicitly listed in `additionalInput`. If IP3 is shared across Create / Update and differs in inputs between modes, parameterize. |
| 8 | `PRM_OmniUtils.logException` change has wide blast radius - any existing IP that uses it inside a rollback-able context could have its logs dropped | Low-Medium | Wave 1 absorbed this risk. Wave 2 changes limited to optional `sourceFlow` annotation; no caller-visible signature changes. |
| 9 | **Update-specific: Dirty-read window between TX1 and TX2 on records another process may concurrently update** | Medium | Between TX1 commit and TX2 start, another integration (for example a nightly credentialing batch) could modify HCPF or affiliation rows that IP2 was about to upsert. If IP2 reads stale data into its payload during TX1 and then DMLs during TX2, it can overwrite a concurrent update. Mitigations: (a) have IP2 re-query critical rows inside its own transaction rather than trusting payload passed from TX1; (b) document the concurrency window in the runbook; (c) add a "last updated timestamp" guard in the upsert payload when the target object supports it. |
| 10 | **Update-specific: Partial state is harder for the user to distinguish visually on a PDM update** | Medium | A PDM update that partially succeeds can look identical on screen to a completed update because the existing data masks the missing rows. Mitigate via: `PRM_AsyncProcessingStatus__c` visible on the record page; the `IsNetworkRecordsCreated__c` flag; and the Data Admin list views surfacing any exception log. |
| 11 | **Update-specific: `allOrNone = false` on upserts can leave a payer-network roster partially refreshed** | Medium | If IP3 is refreshing a roster (deleting stale payer-network rows and upserting current ones) and the DML is split into "delete old" and "upsert new" batches with partial-success semantics, a failure mid-way can leave a roster that is neither the before nor the after state. Mitigate by: either keeping the roster refresh inside a single `allOrNone = true` DML within TX3 (accepting the rollback cost) or staging all intended row-level deletions into `PRM_FailedRecordStaging__c` with status `Pending` so the Data Admin can complete the cleanup explicitly. Recommendation: start with `allOrNone = true` for delete DML and `allOrNone = false` only for upsert DML. |
| 12 | IP3 may be shared between Create and Update flows; changes risk regressing Creation | High if shared | Sprint 0 confirms whether IP3 is shared. If shared, add a mode switch or fork the IP. Regression pass on Creation flow during Sprint 4 hardening. |

---

## 11. Testing Strategy

### 11.1 Unit Tests

- **Apex classes:** `PRM_ExistingPractitionerUpdateService.cls` and any other new helpers require >=90% line coverage. Bulk assertions must cover the same-insert / same-update / mixed scenarios.
- **Queueable coverage limitation (Wave 1 Gap Analysis Issue #4):** Salesforce enforces a 1-level Queueable chaining limit during `Test.startTest()` / `Test.stopTest()`. The TX2 -> TX3 hop from IP2's Queueable to IP3's Queueable cannot be exercised in a standard unit test. Unit tests will verify that IP2 publishes its `System.enqueueJob` instruction (via indirect observation of `AsyncApexJob` creation inside `Test.stopTest()`) but will **not** assert that IP3's Queueable runs to completion within the same test. End-to-end coverage is supplied by the integration tests below.
- **Exception logging:** Assert that `logExceptionViaEvent` is invoked in each forced-failure path and that the resulting `PRM_ExceptionLogEvent__e` carries the correct `PRM_RecordId__c` / `PRM_RecordObjectName__c`. Because the event publishes independently of DML rollback, these assertions are robust.

### 11.2 Integration Test Scenarios

All executed in a full sandbox (not a Developer edition org).

| ID | Scenario | Expected |
|---|---|---|
| INT-1 | Update practitioner with **1 location** (light payload) | TX1 completes synchronously in < 30 s. TX2 and TX3 complete in < 2 min total. `PRM_AsyncProcessingStatus__c = 'Completed'`, `IsNetworkRecordsCreated__c = true`. No staging or exception rows. |
| INT-2 | Update practitioner with **3 locations** (current failure threshold) | Full chain completes in 8-15 min end-to-end. No governor limit exceptions anywhere. Status `Completed`. |
| INT-3 | Update practitioner with **5+ locations** (stress) | Full chain completes within 20 min. TX2 and TX3 each renew governor limits; no single transaction exceeds its budget. Status `Completed`. |
| INT-4 | Update against a practitioner where `ExistingPrimaryPractice` conditional in IP2 evaluates **false** | TX3 still fires (validates IP3 placement at level 0). Network records upserted successfully. |
| INT-5 | Repeat INT-2 twice against the same practitioner | Idempotency check. Second run produces identical final state. No duplicate HCPF / network rows. No duplicate staging rows. |

### 11.3 Failure Injection Tests (per TX boundary)

| ID | Injection Point | Method | Expected |
|---|---|---|---|
| INJ-1 | TX1 (IP1) | Temporary validation rule on `Address__c` that fails for a specific test value | Clean rollback. TX2 never enqueued. Exception log row created with `PRM_ProcessName__c = "PRM_PractitionerAddressUpdate"`. `PRM_AsyncProcessingStatus__c = 'Failed'` (set by Container Catch block or by the OmniScript error path). |
| INJ-2 | TX2 (IP2) seq 1 (earliest step) | Temporary validation rule on `HealthcarePractitionerFacility` | TX1 persists. TX2 DML rolled back. TX3 never enqueued. Exception log row created via Platform Event (survives rollback). Status `Failed`. This test specifically validates that the Try/Catch covers seq 1, not only the conditional block. |
| INJ-3 | TX2 (IP2) mid-execution | Temporary validation rule on affiliation object | Same as INJ-2 but validates mid-IP capture. |
| INJ-4 | TX3 (IP3) bulk DML | Introduce 3 invalid `HealthcarePlanNetworkId` values in the upsert payload (partial-success mode) | Valid rows upsert successfully. 3 `PRM_FailedRecordStaging__c` rows created with `PRM_Status__c = 'Pending'`, `PRM_TargetObject__c = 'HealthcarePlanNetwork'`, `PRM_Payload__c` containing the full sObject JSON. `PRM_AsyncProcessingStatus__c = 'Failed'`. |
| INJ-5 | TX3 (IP3) total failure | Temporary validation rule that fails for all rows | TX3 DML rolled back. Exception log row created via Platform Event. Status `Failed`. `IsNetworkRecordsCreated__c` remains false. |

### 11.4 UAT Acceptance Criteria

- Network Maintenance team executes the 5 standard test fixtures (1 / 3 / 5 location; both primary-only and secondary-location-only edits) and reports no UI freeze longer than 30 seconds on TX1.
- Data Admin team validates that any failure produced during UAT surfaces correctly in the "Network Creation Errors - Needs Review" list view with the PDM `PRM_ProcessName__c` values visible.
- The "Mark Resolved & Route to QC" Quick Action on the IndividualApplication record successfully routes at least one UAT-produced failure to the QC queue with Chatter notification.
- For each successful UAT fixture, the IndividualApplication record displays `PRM_AsyncProcessingStatus__c = 'Completed'` and `IsNetworkRecordsCreated__c = true` within 15 minutes of submission.
- QC reviewer confirms that end-state data on a successful PDM update is indistinguishable from data produced by the pre-change synchronous flow (reached via restore from snapshot for comparison).

---

## 12. Definition of Done

- [ ] IBX OmniStudio team has signed off on the PDM OmniScript and IP keys used in this document.
- [ ] `PRM_PDMUpdateLogicContainer` governor limits elevated; IP2 invocation mode changed to `useQueueable`; IP3 direct invocation deactivated; additionalInput extended.
- [ ] `PRM_ExistingPrimaryPracticeLocationLogicPDMUpdate` has queueable governor overrides, a Try/Catch wrapping all steps from seq 1, and a Catch block that calls `PRM_OmniUtils.logExceptionViaEvent` and sets `PRM_AsyncProcessingStatus__c = 'Failed'`.
- [ ] IP2 contains a new `AddTaxNetworkLogicFromPDMUpdate` IP Action element at `level: 0`, `sequenceNumber: 6.1`, after `ResponseForIp`, invoking IP3 with `useQueueable: true`.
- [ ] `PRM_CreateOrUpdateDelegatedHFNRecords` has Try/Catch wrappers around its main logic blocks; bulk DML runs in partial-success mode with failures staged to `PRM_FailedRecordStaging__c`; final happy-path step sets `PRM_AsyncProcessingStatus__c = 'Completed'` and `IsNetworkRecordsCreated__c = true`.
- [ ] No PDM IP Catch block references `logExceptionDirect`; only `logExceptionViaEvent`.
- [ ] "Network Creation Errors - Needs Review" list view filter widened to include PDM `PRM_ProcessName__c` values.
- [ ] "By Process - PDM Manual Update" list view on `PRM_FailedRecordStaging__c` created.
- [ ] PDM record page layout includes `PRM_AsyncProcessingStatus__c` and `IsNetworkRecordsCreated__c`.
- [ ] Unit test coverage >=90% on any new Apex classes introduced by this Wave.
- [ ] Integration tests INT-1 through INT-5 pass in a full sandbox.
- [ ] Failure-injection tests INJ-1 through INJ-5 pass in a full sandbox.
- [ ] UAT acceptance criteria signed off by Network Maintenance and Data Admin.
- [ ] Regression pass completed on the Practitioner Creation flow to confirm no regression from any shared-infrastructure re-touch.
- [ ] Deployment runbook updated with PDM IP deployment order and 48-hour post-deploy monitoring playbook (AsyncApexJob queries, exception log spot-checks, staging row spot-checks).
- [ ] Production deployment completed and monitored for 48 hours with zero governor-limit exceptions in debug logs and zero silent failures in async jobs.
- [ ] Post-deployment KPI baseline captured: TX1 P50 / P95 duration, TX2 + TX3 P50 / P95 duration, exception log rate, staging row rate, support ticket volume (measured at week 1, week 2, week 4).
