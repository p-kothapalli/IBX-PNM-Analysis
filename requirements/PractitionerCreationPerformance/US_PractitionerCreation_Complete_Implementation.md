# USER STORIES: Practitioner Creation Performance & Failed Record Management
## Complete Implementation — Async Processing, Staging, & Case Routing

**Epic:** Practitioner Creation Reliability & Performance  
**Vertical:** Provider Network Management (PNM)  
**OmniScript:** `PRM_DelegatedPractitionerReviewScreen`  
**Priority:** P0 — Production blocking; 15-20 support tickets/week  
**Based On:** New TDD (Async Processing + Staging + UX)

---

## Epic Overview

### Problem Statement
The Practitioner Creation flow causes 5+ minute UI freeze when creating practitioners with 3+ practice locations, hitting Salesforce governor limits (SOQL 100, CPU 60s, Heap 12MB). When failures occur, they are silent — no exception log survives the rollback, leaving partial data and no recovery path. Operations team spends 2-3 hours per case manually creating 54+ network records.

### Business Impact
- **User Experience:** 5+ minute unresponsive UI → users don't know if submission worked
- **Data Integrity:** Partial record creation with no error visibility
- **Support Load:** 15-20 tickets/week × 2-3 hours remediation = 30-60 hours/week lost
- **Workaround:** Manual network record creation (54 records per practitioner)

### Solution Overview
1. **Async Transaction Split:** Break IP chain into 3 independent transactions (TX1/TX2/TX3) with Queueable execution
2. **Exception Logging:** Platform Event-based logging survives rollbacks
3. **Failed Record Staging:** Business-friendly queue for operations team review/retry
4. **User Visibility:** Processing status field, email notifications, progress banner
5. **Case Routing:** Automatic routing to specialized queues based on processing outcome
6. **Partial Success:** `allOrNone = false` DML with per-record error staging
7. **Retry Mechanism:** Quick Action to replay failed processing from staging queue

---

## User Story #1: Async Transaction Split & Exception Logging

### Story
**As a** Credentialing Specialist,  
**I want** the delegated practitioner creation process to complete reliably without timing out,  
**So that** I can onboard practitioners with 3+ practice locations without UI freeze or silent failures.

**As a** Salesforce Developer,  
**I want** exception logs to survive transaction rollbacks,  
**So that** we have full visibility into async processing failures.

### Priority: P0 — Critical

### Scope
- Container + IP1 synchronous (TX1)
- IP2 as Queueable (TX2)
- IP3 as Queueable from IP2 (TX3)
- Platform Event-based exception logging
- Exception log linked to Case Manager

### Acceptance Criteria

**AC 1.1: Governor Limits — No Failures for 3-Location Practitioner**

**Given** a delegated practitioner with 3 practice locations, 3 taxonomies each, 15 networks each (54-69 total records),  
**When** the submission is processed end-to-end,  
**Then**:
- No SOQL query limit exceptions (TX1: 120 limit, TX2: 150, TX3: 120)
- No CPU time limit exceptions (TX1: 10,000ms, TX2: 60,000ms, TX3: 60,000ms)
- No heap size exceptions (TX1: 6MB, TX2: 12MB, TX3: 12MB)
- All transactions complete successfully

---

**AC 1.2: IP1 Failure — Clean Rollback**

**Given** a practitioner creation submission is in progress,  
**When** `PRM_PractitionerAddressCreation` (IP1) fails mid-execution (e.g., validation rule, required field missing),  
**Then**:
- All DML from Container + IP1 is rolled back (no orphaned records)
- IP2 is never enqueued
- IP3 is never enqueued
- A `PRM_ExceptionLog__c` record is created via Platform Event
- Exception log is linked to IndividualApplication (Case Manager) via `PRM_IndividualApplication__c` lookup
- Exception log contains: process name, error message, stack trace, payload

---

**AC 1.3: IP2 Failure — Exception Log Survives Rollback**

**Given** IP1 has completed successfully (TX1 committed),  
**When** `PRM_ExistingPrimaryPracticeLocationLogicDelg` (IP2) fails at any step (including steps before seq 4),  
**Then**:
- IP2's own DML (HCPF records, provider features, affiliations) is rolled back
- TX1 records (addresses, facilities, locations, HC practitioners) **remain committed** (orphaned state)
- IP3 is never enqueued
- A `PRM_ExceptionLog__c` record is created with:
  - `PRM_ProcessName__c = "PRM_ExistingPrimaryPracticeLocationLogicDelg"`
  - `PRM_IntegrationType__c = "ASYNC"`
  - `PRM_IndividualApplication__c` = Case Manager Id (lookup populated)
  - `PRM_SeverityLevel__c = "Error"`
- Exception log appears in "Exception Logs" related list on Case Manager record

---

**AC 1.4: IP3 Failure — Exception Log Survives Rollback**

**Given** IP1 and IP2 have completed successfully (TX1 and TX2 committed),  
**When** `PRM_CreateDelegatedHFNRecords` (IP3) fails during taxonomy, payer network, or IFC creation,  
**Then**:
- IP3's own DML (all network records) is rolled back
- TX1 + TX2 records **remain committed** (orphaned state)
- A `PRM_ExceptionLog__c` record is created with:
  - `PRM_ProcessName__c = "PRM_CreateDelegatedHFNRecords"`
  - `PRM_IndividualApplication__c` = Case Manager Id
- Exception log appears in related list on Case Manager record

---

**AC 1.5: IP3 Executes Regardless of ExistingPrimaryPractice Condition**

**Given** a delegated practitioner whose `ExistingPrimaryPractice` conditional in IP2 evaluates to **false**,  
**When** IP2 completes successfully,  
**Then**:
- IP3 (`PRM_CreateDelegatedHFNRecords`) is **still enqueued**
- IP3 executes and creates taxonomy/payer network/IFC records
- (Validates IP3 is placed at level 0, not inside conditional block)

---

**AC 1.6: Exception Log Is Navigable from Case Manager**

**Given** an exception log is created for a failed IP2 or IP3 execution,  
**When** a Credentialing Specialist opens the Case Manager record,  
**Then**:
- They see the exception log in the "Exception Logs" related list
- They can click into the exception log and view:
  - `PRM_ProcessName__c` (which IP failed)
  - `PRM_ErrorMessage__c` (user-readable error)
  - `PRM_StackTrace__c` (technical details)
  - `PRM_RequestPayload__c` (input data)
  - CreatedDate (timestamp of failure)

---

### Technical Requirements

**Integration Procedure Changes:**

| Component | Change Type | Details |
|-----------|-------------|---------|
| `PRM_AddressLogicContainer` | IP Config | Increase chainable limits: queries 50→120, CPU 2000→10000ms, heap →6MB |
| `PRM_AddressLogicContainer` — `ExistingPrimaryAddressLogic` element | IP Element | Change to Queueable invocation; add `RecordsToUpdate`, `FacilityPractitionerTxNw` to additionalInput |
| `PRM_AddressLogicContainer` — `AddTaxNetworkLogic` element | IP Element | Set `isActive: false` (IP3 now called from IP2) |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` | IP Config | Add queueable limits: queries 150, CPU 60000ms, heap 12MB |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — new `AddTaxNetworkLogicFromDelg` | IP Element | New IP Action at **level 0, seq 6.1** (after ResponseForIp); invokes IP3 as Queueable |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` — Try/Catch | IP Element | Wrap **all steps from seq 1**; Catch calls `logExceptionViaEvent` |
| `PRM_CreateDelegatedHFNRecords` | IP | Add Try/Catch around `CB_LogicExecuteTxNetwork`, `CB_LogicExecuteLocNetwork`, `CB_ExecuteIFCLogic` |

**Apex Class Changes:**

| Class | Change |
|-------|--------|
| `PRM_ExceptionLogger.cls` | Add `logExceptionViaEvent()` method (Platform Event); rename direct DML method to `logExceptionDirect()` with deprecation warning |
| `PRM_OmniUtils.cls` | Add `logExceptionViaEvent()` remote method; update `logException()` to extract caseManagerId from inputMap |
| `PRM_ExceptionLogEventTrigger` (NEW) | Trigger on `PRM_ExceptionLogEvent__e` (after insert); creates `PRM_ExceptionLog__c` with lookup to IndividualApplication |

**Custom Fields:**

| Object | Field | Type | Purpose |
|--------|-------|------|---------|
| `PRM_ExceptionLog__c` | `PRM_IndividualApplication__c` | Lookup(IndividualApplication) | Links exception log to Case Manager |
| `PRM_ExceptionLogEvent__e` | `PRM_RecordId__c` | Text(18) | Case Manager Id |
| `PRM_ExceptionLogEvent__e` | `PRM_RecordObjectName__c` | Text(255) | Object API name (IndividualApplication) |

### Definition of Done
- [ ] All 6 Acceptance Criteria pass in sandbox
- [ ] TX1/TX2/TX3 split implemented with correct governor limits
- [ ] Platform Event-based exception logging survives rollback
- [ ] Exception logs linked to Case Manager (navigable related list)
- [ ] IP3 placed at level 0 (not inside conditional)
- [ ] Try/Catch in IP2 covers seq 1 onward (not just seq 4)
- [ ] Apex test coverage > 90% (`PRM_ExceptionLogger`, `PRM_ExceptionLogEventTrigger`)
- [ ] Manual integration test completed (see "Sandbox Test Strategy" below)

### Effort Estimate: **L (7-9 days)**

---

## User Story #2: Failed Record Staging & Work Queue

### Story
**As an** Operations Manager,  
**I want** a business-friendly queue of failed practitioner processing records that my team can review, correct, and retry,  
**So that** we don't have to manually create 54 network records per failure or rely on engineering to debug exception logs.

**As a** Credentialing Specialist,  
**I want** to see which specific network records failed to create (not just "IP3 failed"),  
**So that** I can identify data quality issues (e.g., invalid payer codes, missing taxonomy mappings) and fix them at the source.

### Priority: P0 — Critical (same sprint as Story #1)

### Scope
- `PRM_FailedRecordStaging__c` object with lifecycle status
- Partial-success DML (`allOrNone = false`) in IP3
- Staging record created per failed network record (not per IP failure)
- Link to exception log and Case Manager
- Operations team list views

### Acceptance Criteria

**AC 2.1: Failed Network Records Are Staged (Not Rolled Back)**

**Given** IP3 is creating 54 network records (9 taxonomy + 45 payer + 15 IFC),  
**When** 3 payer network records fail validation (e.g., invalid HealthcarePlanNetworkId),  
**Then**:
- The 51 valid network records are inserted successfully
- The 3 failed records are **not** inserted
- 3 `PRM_FailedRecordStaging__c` records are created with:
  - `PRM_Status__c = "Pending"`
  - `PRM_TargetObject__c = "HealthcarePlanNetwork"`
  - `PRM_Payload__c` = JSON serialization of failed record
  - `PRM_CaseManager__c` = Case Manager Id (lookup)
  - `PRM_ExceptionLog__c` = Exception log Id (lookup)
  - `PRM_ErrorMessage__c` = SaveResult error message (e.g., "Invalid HealthcarePlanNetworkId")
  - `PRM_SourceFlow__c = "PRM_CreateDelegatedHFNRecords"`

---

**AC 2.2: Staging Record Contains Full Payload for Replay**

**Given** a failed payer network record is staged,  
**When** an Operations user opens the staging record,  
**Then**:
- `PRM_Payload__c` field contains full JSON: `{ "Name": "...", "HealthcarePlanNetworkId": "...", "HealthcareFacilityId": "...", "EffectiveDate": "..." }`
- Payload is deserializable back to `HealthcarePlanNetwork` sObject
- All required fields for retry are present

---

**AC 2.3: Staging Records Are Linked to Case Manager & Exception Log**

**Given** 3 staging records are created for failed networks,  
**When** an Operations user navigates to the Case Manager record,  
**Then**:
- They see "Failed Records" related list with 3 rows
- Each row shows:
  - `PRM_Status__c` (Pending)
  - `PRM_TargetObject__c` (HealthcarePlanNetwork)
  - `PRM_ErrorMessage__c` (truncated)
  - CreatedDate
- They can click the exception log lookup to see full stack trace

---

**AC 2.4: Operations Work Queue — "Pending Failed Records" List View**

**Given** multiple practitioners have failed network records in staging,  
**When** an Operations user opens the "Failed Records" tab,  
**Then**:
- They see a list view: "Pending Failed Records" filtered by `PRM_Status__c = "Pending"`
- Columns: Case Manager Name, Target Object, Error Message, Created Date, Owner
- Records are grouped by Case Manager (so all 3 failures for same practitioner appear together)
- List view is sortable by Created Date (most recent first)

---

**AC 2.5: Staging Record Status Lifecycle**

**Given** an Operations user has corrected the data issue (e.g., created missing payer network in master data),  
**When** they mark the staging record as "Fixed" (via Quick Action or manual edit),  
**Then**:
- `PRM_Status__c` changes from "Pending" to "Fixed"
- Record moves out of "Pending Failed Records" list view
- Record appears in "Fixed - Ready for Retry" list view
- (Future: automated retry job picks up "Fixed" records)

---

**AC 2.6: No Staging Records Created for Full Success**

**Given** IP3 creates 54 network records and all succeed,  
**When** IP3 completes,  
**Then**:
- Zero `PRM_FailedRecordStaging__c` records are created
- No exception log is created
- Case Manager shows "Completed" status (from Story #3)

---

### Technical Requirements

**New Custom Object: `PRM_FailedRecordStaging__c`**

| Field | Type | Description |
|-------|------|-------------|
| `Name` | Auto-Number | FST-{0000} |
| `PRM_Status__c` | Picklist | `Pending` (default), `Fixed`, `Retried`, `Failed - Terminal` |
| `PRM_TargetObject__c` | Text(255) | API name of target object (e.g., HealthcarePlanNetwork) |
| `PRM_Payload__c` | Long Text Area(32,000) | JSON serialization of failed record |
| `PRM_CaseManager__c` | Lookup(IndividualApplication) | Parent Case Manager |
| `PRM_ExceptionLog__c` | Lookup(PRM_ExceptionLog__c) | Linked exception log (optional) |
| `PRM_ErrorMessage__c` | Text(255) | SaveResult error message |
| `PRM_SourceFlow__c` | Text(255) | IP/Flow that attempted creation (e.g., PRM_CreateDelegatedHFNRecords) |
| `PRM_RetryCount__c` | Number | Count of retry attempts (default 0) |
| `PRM_FailureType__c` | Text(100) | Validation / Missing Reference / Duplicate / Other |

**IP3 Modification:**

```apex
// In PRM_CreateDelegatedHFNRecords (pseudo-code)
List<HealthcarePlanNetwork> networksToInsert = ...; // 54 records

// Use partial-success DML
Database.SaveResult[] results = Database.insert(networksToInsert, false); // allOrNone = false

List<PRM_FailedRecordStaging__c> stagingRecords = new List<PRM_FailedRecordStaging__c>();

for (Integer i = 0; i < results.size(); i++) {
    if (!results[i].isSuccess()) {
        // Failed record — stage it
        PRM_FailedRecordStaging__c staging = new PRM_FailedRecordStaging__c();
        staging.PRM_Status__c = 'Pending';
        staging.PRM_TargetObject__c = 'HealthcarePlanNetwork';
        staging.PRM_Payload__c = JSON.serialize(networksToInsert[i]);
        staging.PRM_CaseManager__c = caseManagerId;
        staging.PRM_ErrorMessage__c = results[i].getErrors()[0].getMessage();
        staging.PRM_SourceFlow__c = 'PRM_CreateDelegatedHFNRecords';
        staging.PRM_FailureType__c = classifyError(results[i].getErrors()[0]);
        stagingRecords.add(staging);
    }
}

if (!stagingRecords.isEmpty()) {
    insert stagingRecords;
    // Link to exception log (if one was created)
    if (exceptionLogId != null) {
        for (PRM_FailedRecordStaging__c s : stagingRecords) {
            s.PRM_ExceptionLog__c = exceptionLogId;
        }
        update stagingRecords;
    }
}
```

**List Views:**

| List View | Filter | Columns |
|-----------|--------|---------|
| Pending Failed Records | `PRM_Status__c = "Pending"` | Case Manager, Target Object, Error Message, Created Date, Owner |
| Fixed - Ready for Retry | `PRM_Status__c = "Fixed"` | Case Manager, Target Object, Fixed Date, Retry Count |
| All Failed Records | (no filter) | Case Manager, Status, Target Object, Created Date |

**Page Layout:**

- Add "Failed Records" related list to IndividualApplication (Case Manager) record page
- Add "Exception Log" related list to IndividualApplication record page

### Definition of Done
- [ ] `PRM_FailedRecordStaging__c` object created with all fields
- [ ] IP3 modified to use `Database.insert(records, false)` (partial-success DML)
- [ ] Staging records created per failed record (not per IP failure)
- [ ] Staging records linked to Case Manager and Exception Log
- [ ] 3 list views created and tested
- [ ] Related lists added to Case Manager page layout
- [ ] AC 2.1 - 2.6 pass in sandbox
- [ ] Test scenario: 3 of 54 records fail → verify 51 inserted, 3 staged

### Effort Estimate: **M (5-6 days)**

---

## User Story #3: User-Facing Status & Notifications

### Story
**As a** Credentialing Specialist,  
**I want** to see the processing status of my practitioner submission in real-time,  
**So that** I know whether async work is still running, has completed successfully, or has failed — without checking system logs or asking IT.

**As a** Credentialing Manager,  
**I want** my team to receive email notifications when practitioner processing completes or fails,  
**So that** they can immediately follow up on failures instead of discovering them hours later.

### Priority: P0 — Critical (same sprint as Story #1 & #2)

### Scope
- `PRM_ProcessingStatus__c` field on Case Manager
- Status updated at each transaction boundary
- Email notifications (success / failure)
- Platform event to refresh UI
- Progress banner component (optional — can be Phase 1B)
- Duplicate submission prevention

### Acceptance Criteria

**AC 3.1: Processing Status Field Transitions Correctly**

**Given** a practitioner creation submission,  
**When** the submission progresses through TX1 → TX2 → TX3,  
**Then** the `PRM_ProcessingStatus__c` field on the Case Manager record transitions as follows:

| Phase | Status Value | Updated By |
|-------|-------------|------------|
| Initial | `Succeed` (default for all other flows) | System default |
| TX1 starts (Container, first step) | `In Progress` | Container (DataRaptor Load or Remote Action) |
| TX1 fails (IP1 error) | `Failed` | Container Catch block |
| TX1 completes, TX2 enqueued | `In Progress` | (no change — TX2 not started yet) |
| TX2 completes, TX3 enqueued | `In Progress` | (no change — TX3 not started yet) |
| TX3 completes successfully | `Succeed` | IP3 final step (DataRaptor Load or Remote Action) |
| TX2 fails | `Failed` | IP2 Catch block (via Remote Action) |
| TX3 fails | `Failed` | IP3 Catch block (via Remote Action) |

---

**AC 3.2: Email Notification on Success (No Failures)**

**Given** a practitioner submission completes successfully (all 54 network records created),  
**When** IP3 sets `PRM_ProcessingStatus__c = "Succeed"`,  
**Then**:
- An email is sent to the record owner (Credentialing Specialist)
- Email subject: "Practitioner Creation Completed - [Practitioner Name]"
- Email body includes:
  - Practitioner name
  - Case Manager record link
  - Summary: "X addresses, Y facilities, Z network records created"
  - Completion timestamp
- Email template: `PRM_PractitionerCreation_Success`

---

**AC 3.3: Email Notification on Failure (With Staging Records)**

**Given** a practitioner submission fails during IP2 or IP3 (with some records staged),  
**When** the Catch block sets `PRM_ProcessingStatus__c = "Failed"`,  
**Then**:
- An email is sent to the record owner
- Email subject: "Action Required - Practitioner Creation Failed - [Practitioner Name]"
- Email body includes:
  - Practitioner name
  - Case Manager record link
  - Error summary: "X records failed during [IP name]"
  - Link to "Failed Records" related list
  - Link to Exception Log
  - Failure timestamp
  - Next steps: "Please review failed records and correct data issues"
- Email template: `PRM_PractitionerCreation_Failure`

---

**AC 3.4: Progress Banner Shows Current Status (Optional — Phase 1B)**

**Given** a user is viewing the Case Manager record page,  
**When** `PRM_ProcessingStatus__c = "In Progress"`,  
**Then**:
- A banner component at the top of the page displays:
  - "⏳ Practitioner processing in progress... Please check back in 5-10 minutes."
  - Auto-refresh: Banner polls `PRM_ProcessingStatus__c` every 30 seconds
  - Banner dismisses when status changes to "Succeed" or "Failed"
- (If Phase 1B) Banner shows granular status: "Processing Addresses... Processing Networks... Processing IFC..."

---

**AC 3.5: Duplicate Submission Prevention**

**Given** a practitioner submission is in progress (`PRM_ProcessingStatus__c = "In Progress"`),  
**When** the user attempts to submit the same practitioner again via OmniScript,  
**Then**:
- OmniScript displays validation error: "Processing already in progress. Please wait for current submission to complete."
- Submit button is disabled
- User cannot create duplicate async jobs

---

**AC 3.6: Failed Status Does Not Block Retry**

**Given** a practitioner submission has failed (`PRM_ProcessingStatus__c = "Failed"`),  
**When** an Operations user initiates a manual retry (via Quick Action or OmniScript button),  
**Then**:
- Retry is allowed (no validation error)
- Status resets to `In Progress` when retry starts
- If retry succeeds, status updates to `Succeed`

---

### Technical Requirements

**New Custom Field:**

| Object | Field | Type | Values | Default |
|--------|-------|------|--------|---------|
| `IndividualApplication` (CaseManager) | `PRM_ProcessingStatus__c` | Picklist | `Not Started`, `In Progress`, `Succeed`, `Failed` | `Succeed` |

**Status Update Implementation:**

| Location | Action | How |
|----------|--------|-----|
| Container (first step) | Set to `In Progress` | DataRaptor Load: `PRM_ProcessingStatus__c = "In Progress"` |
| Container (Catch block) | Set to `Failed` | Remote Action: `updateProcessingStatus(caseManagerId, "Failed")` |
| IP2 (Catch block) | Set to `Failed` | Remote Action: `PRM_OmniUtils.updateProcessingStatus(inputMap)` |
| IP3 (Catch block) | Set to `Failed` | Remote Action: `PRM_OmniUtils.updateProcessingStatus(inputMap)` |
| IP3 (final step, happy path) | Set to `Succeed` | DataRaptor Load: `PRM_ProcessingStatus__c = "Succeed"` |

**Email Templates:**

1. **PRM_PractitionerCreation_Success** (Text + HTML)
```
Subject: Practitioner Creation Completed - {!IndividualApplication__c.Practitioner_Name__c}

Hi {!IndividualApplication__c.Owner.FirstName},

Good news! The practitioner creation for {!IndividualApplication__c.Practitioner_Name__c} has completed successfully.

Summary:
- Addresses created: {!IndividualApplication__c.Address_Count__c}
- Facilities created: {!IndividualApplication__c.Facility_Count__c}
- Network records created: {!IndividualApplication__c.Network_Count__c}
- Completion time: {!IndividualApplication__c.Processing_Completed_At__c}

View Case Manager: [link]

No further action required.
```

2. **PRM_PractitionerCreation_Failure** (Text + HTML)
```
Subject: ⚠️ Action Required - Practitioner Creation Failed - {!IndividualApplication__c.Practitioner_Name__c}

Hi {!IndividualApplication__c.Owner.FirstName},

The practitioner creation for {!IndividualApplication__c.Practitioner_Name__c} encountered errors and requires your attention.

Error Details:
- Failed during: {!IndividualApplication__c.Failed_Process__c}
- Records failed: {!IndividualApplication__c.Failed_Record_Count__c}
- Error message: {!PRM_ExceptionLog__c.PRM_ErrorMessage__c}

Next Steps:
1. Review failed records: [link to Case Manager > Failed Records related list]
2. Review exception log: [link]
3. Correct data issues and retry

If you need assistance, please contact the PRM support team.
```

**Apex Class: `PRM_OmniUtils` (new method)**

```apex
@AuraEnabled
public static void updateProcessingStatus(Map<String, Object> inputMap) {
    String caseManagerId = (String) inputMap.get('caseManagerId');
    String status = (String) inputMap.get('status'); // "In Progress" / "Succeed" / "Failed"
    
    if (String.isBlank(caseManagerId) || String.isBlank(status)) {
        return;
    }
    
    IndividualApplication caseManager = [SELECT Id, PRM_ProcessingStatus__c 
                                         FROM IndividualApplication 
                                         WHERE Id = :caseManagerId LIMIT 1];
    caseManager.PRM_ProcessingStatus__c = status;
    update caseManager;
    
    // Optionally publish platform event to refresh UI
    PRM_RecordStagingEvent__e evt = new PRM_RecordStagingEvent__e(
        PRM_CaseManagerId__c = caseManagerId,
        PRM_Status__c = status
    );
    EventBus.publish(evt);
}
```

**OmniScript Validation (Duplicate Prevention):**

In `PRM_DelegatedPractitionerReviewScreen`, add a Set Values step before submit:
```json
{
  "type": "Set Values",
  "name": "CheckProcessingStatus",
  "propertySetConfig": {
    "query": "SELECT PRM_ProcessingStatus__c FROM IndividualApplication WHERE Id = :caseManagerId",
    "failureMessage": "Processing already in progress. Please wait for current submission to complete.",
    "failCondition": "PRM_ProcessingStatus__c = 'In Progress'"
  }
}
```

**Progress Banner Component (Optional — Phase 1B):**

- LWC component: `prmProcessingStatusBanner`
- Placed on Case Manager record page (lightning:appBuilder)
- Polls `PRM_ProcessingStatus__c` via `getRecord` every 30 seconds
- Shows/hides based on status value
- Auto-dismisses when status changes to "Succeed" or "Failed"

### Definition of Done
- [ ] `PRM_ProcessingStatus__c` field created on IndividualApplication
- [ ] Field added to Case Manager page layout
- [ ] Status updates implemented at all 5 locations (Container start, IP1 fail, IP2 fail, IP3 fail, IP3 success)
- [ ] 2 email templates created and tested
- [ ] Email sending implemented (Process Builder / Flow / Apex)
- [ ] Duplicate submission prevention tested
- [ ] AC 3.1 - 3.6 pass in sandbox
- [ ] (Optional Phase 1B) Progress banner component deployed

### Effort Estimate: **M (4-5 days)**  
**Phase 1B (Banner Component): +2 days**

---

## User Story #4: Case Routing & Queue Management

### Story
**As an** Operations Manager,  
**I want** practitioner cases to be automatically routed to specialized queues based on processing outcome (success vs. error type),  
**So that** my team can prioritize urgent failures, track completion rates, and assign work efficiently.

**As a** Data Quality Analyst,  
**I want** to see which types of errors are most common (validation errors, missing references, duplicate records),  
**So that** I can identify upstream data quality issues and fix them at the source.

### Priority: P1 — High (Sprint 2 / Phase 1B)

### Scope
- Queue-based routing via Process Builder or Flow
- Specialized queues: "PRM - Network Creation Success", "PRM - Network Creation Failed", "PRM - Validation Errors"
- Auto-assignment rules based on error type
- Dashboard for Operations Manager

### Acceptance Criteria

**AC 4.1: Successful Cases Routed to Success Queue**

**Given** a practitioner submission completes successfully (`PRM_ProcessingStatus__c = "Succeed"` and no staging records),  
**When** the status is updated by IP3,  
**Then**:
- Case Manager record owner is changed to Queue: "PRM - Network Creation Success"
- Case status is updated to "Completed - Network Creation"
- Record appears in "Completed Practitioners" list view
- No further action required

---

**AC 4.2: Failed Cases Routed to Failed Queue**

**Given** a practitioner submission fails (`PRM_ProcessingStatus__c = "Failed"` and staging records exist),  
**When** the status is updated by IP2 or IP3 Catch block,  
**Then**:
- Case Manager record owner is changed to Queue: "PRM - Network Creation Failed"
- Case status is updated to "Error - Requires Review"
- Record appears in "Failed Practitioners - Action Required" list view
- (Future) Case is auto-assigned to available Operations user based on round-robin or workload

---

**AC 4.3: Validation Errors Routed to Data Quality Queue**

**Given** a practitioner submission fails with validation errors (e.g., required field missing, invalid picklist value),  
**When** staging records are created with `PRM_FailureType__c = "Validation"`,  
**Then**:
- Case Manager record owner is changed to Queue: "PRM - Data Quality Issues"
- Case status is updated to "Error - Data Quality"
- Record appears in "Data Quality Issues" list view
- Data Quality Analyst is notified via email

---

**AC 4.4: Missing Reference Errors Routed to Data Quality Queue**

**Given** a practitioner submission fails with missing reference errors (e.g., invalid HealthcarePlanNetworkId, missing payer master record),  
**When** staging records are created with `PRM_FailureType__c = "Missing Reference"`,  
**Then**:
- Case Manager record owner is changed to Queue: "PRM - Data Quality Issues"
- Case status is updated to "Error - Missing Reference Data"
- Record appears in "Missing Reference Data" list view
- Data Quality Analyst is notified to create missing master records

---

**AC 4.5: Duplicate Record Errors Routed to Operations Queue**

**Given** a practitioner submission fails with duplicate record errors (e.g., unique constraint violation on network record),  
**When** staging records are created with `PRM_FailureType__c = "Duplicate"`,  
**Then**:
- Case Manager record owner is changed to Queue: "PRM - Network Creation Failed"
- Case status is updated to "Error - Duplicate Record"
- Record appears in "Duplicate Record Errors" list view
- Operations user reviews to determine if existing record can be used

---

**AC 4.6: Operations Dashboard Shows Success & Failure Metrics**

**Given** an Operations Manager opens the "PRM Operations Dashboard",  
**When** they view the dashboard,  
**Then** they see:
- Total practitioners processed (last 7 days, last 30 days)
- Success rate (%)
- Failure rate (%)
- Breakdown by error type: Validation (%), Missing Reference (%), Duplicate (%), Other (%)
- Average processing time (TX1 + TX2 + TX3)
- Top 5 most common error messages
- Aging report: staging records pending > 7 days

---

### Technical Requirements

**New Queues:**

| Queue Name | Supported Objects | Members |
|------------|-------------------|---------|
| PRM - Network Creation Success | IndividualApplication | Operations Managers, Reporting Users |
| PRM - Network Creation Failed | IndividualApplication | Operations Team, Data Quality Analysts |
| PRM - Data Quality Issues | IndividualApplication | Data Quality Analysts, Operations Managers |

**Process Builder / Flow: "PRM Case Routing on Status Change"**

| Trigger | Object | Field | Condition |
|---------|--------|-------|-----------|
| Record Updated | IndividualApplication | `PRM_ProcessingStatus__c` | `ISCHANGED(PRM_ProcessingStatus__c)` |

**Decision Logic:**

```
IF PRM_ProcessingStatus__c = "Succeed" AND Failed_Record_Count__c = 0:
  → Owner = Queue: "PRM - Network Creation Success"
  → Status = "Completed - Network Creation"

ELSE IF PRM_ProcessingStatus__c = "Failed" AND FailureType__c = "Validation":
  → Owner = Queue: "PRM - Data Quality Issues"
  → Status = "Error - Data Quality"

ELSE IF PRM_ProcessingStatus__c = "Failed" AND FailureType__c = "Missing Reference":
  → Owner = Queue: "PRM - Data Quality Issues"
  → Status = "Error - Missing Reference Data"

ELSE IF PRM_ProcessingStatus__c = "Failed" AND FailureType__c = "Duplicate":
  → Owner = Queue: "PRM - Network Creation Failed"
  → Status = "Error - Duplicate Record"

ELSE IF PRM_ProcessingStatus__c = "Failed":
  → Owner = Queue: "PRM - Network Creation Failed"
  → Status = "Error - Requires Review"
```

**Helper Formula Field on IndividualApplication:**

| Field | Type | Formula |
|-------|------|---------|
| `FailureType__c` | Formula(Text) | `IF(Failed_Record_Count__c > 0, TEXT(PRM_FailedRecordStaging__r[0].PRM_FailureType__c), "")` (Note: may need custom Apex to aggregate) |
| `Failed_Record_Count__c` | Roll-Up Summary | COUNT(PRM_FailedRecordStaging__r) |
| `Processing_Duration__c` | Formula(Number) | `(Processing_Completed_At__c - Processing_Started_At__c) * 24 * 60` (minutes) |

**List Views:**

| List View | Filter | Owner |
|-----------|--------|-------|
| Completed Practitioners | `PRM_ProcessingStatus__c = "Succeed"` | Operations Managers |
| Failed Practitioners - Action Required | `PRM_ProcessingStatus__c = "Failed"` | Operations Team |
| Data Quality Issues | `Status = "Error - Data Quality"` OR `Status = "Error - Missing Reference Data"` | Data Quality Analysts |
| Duplicate Record Errors | `Status = "Error - Duplicate Record"` | Operations Team |
| Aging - Pending > 7 Days | `PRM_ProcessingStatus__c = "Failed"` AND `CreatedDate < LAST_N_DAYS:7` | Operations Managers |

**Dashboard: "PRM Operations Dashboard"**

| Component | Type | Report | Metrics |
|-----------|------|--------|---------|
| Processing Success Rate | Gauge | Practitioners by Status (Succeed vs Failed) | % Success |
| Error Type Breakdown | Donut Chart | Failed Records by Failure Type | Validation, Missing Ref, Duplicate, Other |
| Average Processing Time | Metric | AVG(Processing_Duration__c) | In minutes |
| Aging Report | Table | Staging records pending > 7 days | Case Manager, Days Pending, Error |
| Top 5 Error Messages | Table | Group by PRM_ErrorMessage__c, count | Most common errors |

### Definition of Done
- [ ] 3 queues created with appropriate members
- [ ] Process Builder / Flow deployed for case routing
- [ ] 6 list views created
- [ ] Helper formula fields created on IndividualApplication
- [ ] Dashboard created with 5 components
- [ ] AC 4.1 - 4.6 pass in sandbox
- [ ] Routing tested for all error types

### Effort Estimate: **M (4-5 days)**

---

## User Story #5: Retry Mechanism for Failed Records

### Story
**As an** Operations Specialist,  
**I want** a Quick Action button on the Case Manager record to retry failed processing,  
**So that** after fixing data issues, I can re-run IP2 or IP3 without manual record creation.

**As a** System Administrator,  
**I want** an automated retry job that picks up "Fixed" staging records and replays them,  
**So that** Operations team doesn't have to manually click retry for each case.

### Priority: P0 — Critical (Phase 2 — Sprint 3)

### Scope
- Quick Action: "Retry Failed Processing" on Case Manager
- Retry logic reads from staging records
- Automated retry job (Scheduled Apex Batch)
- Retry count and terminal status handling

### Acceptance Criteria

**AC 5.1: Quick Action — Manual Retry**

**Given** a practitioner submission has failed (`PRM_ProcessingStatus__c = "Failed"` and 3 staging records with `PRM_Status__c = "Pending"`),  
**When** an Operations user clicks the "Retry Failed Processing" Quick Action on the Case Manager record,  
**Then**:
- User is prompted: "Are you sure? This will retry all pending failed records."
- Upon confirmation:
  - All staging records with `PRM_Status__c = "Pending"` are read
  - Payloads are deserialized back to sObjects
  - `Database.insert(records, false)` is executed
  - Successful records: staging record `PRM_Status__c → "Retried"`, `PRM_RetryCount__c++`
  - Failed records (again): staging record remains `PRM_Status__c = "Pending"`, `PRM_RetryCount__c++`, new exception log created
- If all succeed: `PRM_ProcessingStatus__c → "Succeed"`, success email sent
- If any fail: `PRM_ProcessingStatus__c → "Failed"`, failure email sent with updated staging records

---

**AC 5.2: Automated Retry Job — Scheduled Batch**

**Given** 20 practitioner cases have failed with staging records marked `PRM_Status__c = "Fixed"` by Operations team,  
**When** the scheduled batch job `PRM_FailedRecordRetryBatch` runs (daily at 2 AM),  
**Then**:
- Batch queries: `SELECT Id, PRM_Payload__c, PRM_CaseManager__c FROM PRM_FailedRecordStaging__c WHERE PRM_Status__c = 'Fixed' AND PRM_RetryCount__c < 3`
- For each batch chunk (200 records):
  - Deserialize payloads to sObjects
  - Group by `PRM_CaseManager__c` (process all failures for same practitioner together)
  - Execute `Database.insert(records, false)` per Case Manager
  - Update staging records: `PRM_Status__c → "Retried"` (success) or remain `"Fixed"` (failure), increment `PRM_RetryCount__c`
- After batch completes: send summary email to Operations Manager (X retried successfully, Y failed again, Z terminal failures)

---

**AC 5.3: Retry Count Limit — Terminal Status**

**Given** a staging record has failed retry 3 times (`PRM_RetryCount__c = 3`),  
**When** the automated retry job runs again,  
**Then**:
- The record is **not** included in the retry batch (WHERE clause excludes `PRM_RetryCount__c >= 3`)
- Record status is manually or automatically changed to `PRM_Status__c = "Failed - Terminal"`
- Operations Manager is notified via email: "3 records require manual intervention (terminal failures)"
- Data Quality Analyst investigates root cause (likely systemic issue, not transient error)

---

**AC 5.4: Retry Re-invokes IP2 or IP3 (Not Just DML)**

**Given** a practitioner submission failed during IP2 (HCPF creation) with TX1 records orphaned,  
**When** an Operations user clicks "Retry Failed Processing",  
**Then**:
- The retry logic determines which IP failed (IP2 vs IP3) from `PRM_SourceFlow__c` in staging record
- If IP2 failed: re-invoke IP2 as Queueable with original input payload from exception log
- If IP3 failed: re-invoke IP3 as Queueable with original input payload
- `PRM_ProcessingStatus__c → "In Progress"` during retry
- Upon completion: status updates to "Succeed" or "Failed" as normal

---

**AC 5.5: Retry Success — Staging Records Deleted**

**Given** a practitioner submission is retried and all staging records are successfully created,  
**When** the retry completes,  
**Then**:
- All staging records for that Case Manager are deleted (or archived to separate object)
- `PRM_ProcessingStatus__c → "Succeed"`
- Success email sent
- Case routed to "PRM - Network Creation Success" queue

---

**AC 5.6: Partial Retry Success**

**Given** a practitioner submission is retried and 2 of 3 staging records succeed, 1 fails again,  
**When** the retry completes,  
**Then**:
- 2 successful staging records: `PRM_Status__c → "Retried"`, archived
- 1 failed staging record: `PRM_Status__c → "Pending"`, `PRM_RetryCount__c = 1`, remains in "Pending Failed Records" list view
- `PRM_ProcessingStatus__c → "Failed"` (still has pending failures)
- Failure email sent with updated count: "1 record still pending"

---

### Technical Requirements

**Quick Action: "Retry Failed Processing"**

| Type | Target Object | Action Type | Apex Class |
|------|---------------|-------------|------------|
| Quick Action | IndividualApplication | Invoke Apex | `PRM_RetryFailedProcessingController.retryFromCaseManager(Id caseManagerId)` |

**Apex Class: `PRM_RetryFailedProcessingController.cls`**

```apex
public class PRM_RetryFailedProcessingController {
    
    @AuraEnabled
    public static Map<String, Object> retryFromCaseManager(Id caseManagerId) {
        // Query staging records
        List<PRM_FailedRecordStaging__c> stagingRecords = [
            SELECT Id, PRM_Payload__c, PRM_TargetObject__c, PRM_SourceFlow__c, 
                   PRM_RetryCount__c, PRM_CaseManager__c
            FROM PRM_FailedRecordStaging__c
            WHERE PRM_CaseManager__c = :caseManagerId 
            AND PRM_Status__c = 'Pending'
            AND PRM_RetryCount__c < 3
        ];
        
        if (stagingRecords.isEmpty()) {
            return new Map<String, Object>{ 'success' => false, 'message' => 'No pending failed records to retry.' };
        }
        
        // Determine which IP failed
        String sourceFlow = stagingRecords[0].PRM_SourceFlow__c;
        
        if (sourceFlow == 'PRM_CreateDelegatedHFNRecords') {
            // Retry IP3 only — replay network record creation
            return retryIP3(caseManagerId, stagingRecords);
        } else if (sourceFlow == 'PRM_ExistingPrimaryPracticeLocationLogicDelg') {
            // Retry IP2 — more complex, needs full IP2 re-invocation
            return retryIP2(caseManagerId);
        }
        
        return new Map<String, Object>{ 'success' => false, 'message' => 'Unknown source flow: ' + sourceFlow };
    }
    
    private static Map<String, Object> retryIP3(Id caseManagerId, List<PRM_FailedRecordStaging__c> stagingRecords) {
        List<SObject> recordsToInsert = new List<SObject>();
        
        for (PRM_FailedRecordStaging__c staging : stagingRecords) {
            // Deserialize payload
            Type targetType = Type.forName(staging.PRM_TargetObject__c);
            SObject record = (SObject) JSON.deserialize(staging.PRM_Payload__c, targetType);
            recordsToInsert.add(record);
        }
        
        // Partial-success DML
        Database.SaveResult[] results = Database.insert(recordsToInsert, false);
        
        // Update staging records
        Integer successCount = 0;
        Integer failCount = 0;
        
        for (Integer i = 0; i < results.size(); i++) {
            PRM_FailedRecordStaging__c staging = stagingRecords[i];
            staging.PRM_RetryCount__c = (staging.PRM_RetryCount__c == null ? 0 : staging.PRM_RetryCount__c) + 1;
            
            if (results[i].isSuccess()) {
                staging.PRM_Status__c = 'Retried';
                successCount++;
            } else {
                // Failed again
                staging.PRM_ErrorMessage__c = results[i].getErrors()[0].getMessage();
                failCount++;
                
                // Check terminal status
                if (staging.PRM_RetryCount__c >= 3) {
                    staging.PRM_Status__c = 'Failed - Terminal';
                }
            }
        }
        
        update stagingRecords;
        
        // Update Case Manager status
        IndividualApplication caseManager = [SELECT Id, PRM_ProcessingStatus__c FROM IndividualApplication WHERE Id = :caseManagerId];
        if (failCount == 0) {
            caseManager.PRM_ProcessingStatus__c = 'Succeed';
            // Send success email
        } else {
            caseManager.PRM_ProcessingStatus__c = 'Failed';
            // Send failure email
        }
        update caseManager;
        
        return new Map<String, Object>{
            'success' => true,
            'message' => successCount + ' records retried successfully. ' + failCount + ' failed again.'
        };
    }
    
    private static Map<String, Object> retryIP2(Id caseManagerId) {
        // More complex — re-invoke entire IP2 as Queueable
        // Read original payload from Exception Log
        PRM_ExceptionLog__c log = [SELECT PRM_RequestPayload__c FROM PRM_ExceptionLog__c 
                                    WHERE PRM_IndividualApplication__c = :caseManagerId 
                                    AND PRM_ProcessName__c = 'PRM_ExistingPrimaryPracticeLocationLogicDelg'
                                    ORDER BY CreatedDate DESC LIMIT 1];
        
        Map<String, Object> inputMap = (Map<String, Object>) JSON.deserializeUntyped(log.PRM_RequestPayload__c);
        
        // Enqueue IP2
        System.enqueueJob(new PRM_ExistingPrimaryPracticeLocationLogicDelgQueueable(inputMap));
        
        // Update status to In Progress
        IndividualApplication caseManager = [SELECT Id, PRM_ProcessingStatus__c FROM IndividualApplication WHERE Id = :caseManagerId];
        caseManager.PRM_ProcessingStatus__c = 'In Progress';
        update caseManager;
        
        return new Map<String, Object>{
            'success' => true,
            'message' => 'IP2 retry enqueued. Processing status set to In Progress.'
        };
    }
}
```

**Scheduled Apex Batch: `PRM_FailedRecordRetryBatch.cls`**

```apex
global class PRM_FailedRecordRetryBatch implements Database.Batchable<SObject>, Schedulable {
    
    global Database.QueryLocator start(Database.BatchableContext BC) {
        return Database.getQueryLocator([
            SELECT Id, PRM_Payload__c, PRM_TargetObject__c, PRM_CaseManager__c, 
                   PRM_RetryCount__c, PRM_SourceFlow__c
            FROM PRM_FailedRecordStaging__c
            WHERE PRM_Status__c = 'Fixed'
            AND PRM_RetryCount__c < 3
            ORDER BY PRM_CaseManager__c
        ]);
    }
    
    global void execute(Database.BatchableContext BC, List<PRM_FailedRecordStaging__c> scope) {
        // Group by Case Manager
        Map<Id, List<PRM_FailedRecordStaging__c>> byCaseManager = new Map<Id, List<PRM_FailedRecordStaging__c>>();
        
        for (PRM_FailedRecordStaging__c staging : scope) {
            if (!byCaseManager.containsKey(staging.PRM_CaseManager__c)) {
                byCaseManager.put(staging.PRM_CaseManager__c, new List<PRM_FailedRecordStaging__c>());
            }
            byCaseManager.get(staging.PRM_CaseManager__c).add(staging);
        }
        
        // Retry each Case Manager's failed records
        for (Id caseManagerId : byCaseManager.keySet()) {
            PRM_RetryFailedProcessingController.retryFromCaseManager(caseManagerId);
        }
    }
    
    global void finish(Database.BatchableContext BC) {
        // Send summary email to Operations Manager
    }
    
    global void execute(SchedulableContext SC) {
        Database.executeBatch(new PRM_FailedRecordRetryBatch(), 200);
    }
}
```

**Schedule the Batch:**
```apex
// Run daily at 2 AM
System.schedule('PRM Failed Record Retry - Daily', '0 0 2 * * ?', new PRM_FailedRecordRetryBatch());
```

### Definition of Done
- [ ] Quick Action "Retry Failed Processing" created and tested
- [ ] `PRM_RetryFailedProcessingController.cls` deployed with test coverage > 90%
- [ ] `PRM_FailedRecordRetryBatch.cls` deployed with test coverage > 90%
- [ ] Scheduled batch job configured (daily at 2 AM)
- [ ] AC 5.1 - 5.6 pass in sandbox
- [ ] Retry tested for IP2 failure, IP3 failure, partial success, terminal failure

### Effort Estimate: **L (8-10 days)**

---

## Implementation Roadmap

### Phase 1A: Core Performance Fix (Sprint 1 — 2 weeks)
**Goal:** Stop production crashes, eliminate silent failures

| Story | Tasks | Owner | Days |
|-------|-------|-------|------|
| **US #1: Async Transaction Split & Exception Logging** | IP configuration, Platform Event trigger, Apex classes, exception logging | Dev Team | 7-9 |
| **US #2: Failed Record Staging** | Custom object, partial-success DML, list views | Dev Team | 5-6 |
| **US #3: Processing Status & Notifications** | Status field, email templates, status update logic | Dev Team | 4-5 |

**Total: 16-20 days (2-3 weeks with parallel work)**

**Deliverables:**
- ✅ Governor limits resolved
- ✅ Exception logs survive rollbacks
- ✅ Failed records staged for retry
- ✅ Users receive email notifications
- ✅ Processing status visible on Case Manager

---

### Phase 1B: UX & Operations Tools (Sprint 2 — 1-1.5 weeks)
**Goal:** Improve user visibility and operations team efficiency

| Story | Tasks | Owner | Days |
|-------|-------|-------|------|
| **US #3 (Phase 1B): Progress Banner** | LWC component, platform event refresh | Dev Team | 2-3 |
| **US #4: Case Routing & Queue Management** | Queues, Process Builder, list views, dashboard | Admin + Dev | 4-5 |

**Total: 6-8 days**

**Deliverables:**
- ✅ Real-time progress banner
- ✅ Automatic case routing
- ✅ Operations dashboard
- ✅ Specialized work queues

---

### Phase 2: Retry Mechanism (Sprint 3 — 2 weeks)
**Goal:** Eliminate manual remediation work

| Story | Tasks | Owner | Days |
|-------|-------|-------|------|
| **US #5: Retry Mechanism** | Quick Action, Apex controller, scheduled batch, retry logic | Dev Team | 8-10 |

**Total: 8-10 days**

**Deliverables:**
- ✅ Manual retry via Quick Action
- ✅ Automated retry job (daily)
- ✅ Terminal failure handling
- ✅ Full recovery path for all failure types

---

## Total Effort Estimate

| Phase | Duration | Stories | Developer Days |
|-------|----------|---------|----------------|
| **Phase 1A** | 2-3 weeks | US #1, #2, #3 | 16-20 |
| **Phase 1B** | 1-1.5 weeks | US #3B, #4 | 6-8 |
| **Phase 2** | 2 weeks | US #5 | 8-10 |
| **TOTAL** | **5-7 weeks** | **5 stories** | **30-38 days** |

**Team:** 2 developers (parallel work) = **3-4 sprints (6-8 weeks calendar time)**

---

## Critical Pre-Implementation Fixes

These **must** be addressed before any deployment (from Gap Analysis):

| # | Issue | Fix | Risk | Owner |
|---|-------|-----|------|-------|
| 1 | `logException` routing bug | Rename `logExceptionDirect()`, route async to `logExceptionViaEvent()` only | HIGH | Dev |
| 2 | IP3 placement ambiguity | Lock at **level 0** in IP2 (not inside conditional) | HIGH | Dev |
| 3 | Try/Catch scope too narrow | Wrap IP2 from seq 1 (not seq 4) | MEDIUM | Dev |
| 4 | Missing status field | Add `PRM_AsyncProcessingStatus__c` (delivered in US #3) | HIGH | Admin |
| 5 | IP3 input audit | Verify 6 `additionalInput` fields are complete | MEDIUM | Dev |
| 6 | Sandbox test strategy | Manual Queueable chain test (documented below) | MEDIUM | QA |
| 7 | Retry mechanism not scoped | Now scoped in US #5 (Phase 2) | HIGH | PM |

---

## Sandbox Test Strategy (Manual Integration Testing)

**Why Manual Testing Required:**
- Salesforce Developer/Sandbox environments enforce **1-level Queueable chaining limit** during `Test.startTest()/stopTest()`
- TX2 → TX3 hop (IP2 Queueable enqueueing IP3 Queueable) will not fire in unit tests
- Must validate full chain in sandbox with real data execution

**Test Procedure:**

### Test 1: Happy Path — 3-Location Practitioner

1. **Setup:** Create test practitioner with 3 practice locations, 3 taxonomies each, 15 payer networks each
2. **Execute:** Trigger OmniScript submission via UI
3. **Verify TX1:**
   - Query `AsyncApexJob` WHERE `JobType = 'Queueable'` AND `ApexClass.Name LIKE '%PRM_ExistingPrimary%'`
   - Confirm IP2 job enqueued (Status = Queued or Processing)
   - UI should return control to user (TX1 committed)
4. **Verify TX2:**
   - Wait for IP2 job to complete (Status = Completed)
   - Query for IP3 Queueable job: `ApexClass.Name LIKE '%PRM_CreateDelegated%'`
   - Confirm IP3 job enqueued
5. **Verify TX3:**
   - Wait for IP3 job to complete
   - Query Case Manager: `PRM_ProcessingStatus__c = "Succeed"`, `IsNetworkRecordsCreated__c = true`
   - Verify 54 network records created (9 taxonomy + 45 payer + 15 IFC)
   - Verify no staging records created
   - Verify success email sent

**Expected Duration:** 8-15 minutes (TX1: 2-4min, TX2: 2-5min, TX3: 4-8min)

---

### Test 2: IP2 Failure — Exception Log Survives Rollback

1. **Setup:** Create test practitioner, introduce validation rule on HCPF object to force IP2 failure
2. **Execute:** Trigger OmniScript submission
3. **Verify:**
   - TX1 completes (addresses/facilities created)
   - IP2 job shows Status = Failed
   - TX2 DML rolled back (no HCPF records)
   - `PRM_ExceptionLog__c` record **exists** (lookup to Case Manager populated)
   - `PRM_ProcessingStatus__c = "Failed"`
   - Failure email sent
4. **Verify No Silent Failure:**
   - Exception log visible in "Exception Logs" related list on Case Manager
   - Error message contains validation rule text

---

### Test 3: IP3 Failure — Partial Success with Staging

1. **Setup:** Create test practitioner, introduce invalid HealthcarePlanNetworkId on 3 of 45 payer networks
2. **Execute:** Trigger OmniScript submission
3. **Verify:**
   - TX1 and TX2 complete successfully
   - IP3 executes `Database.insert(records, false)` (partial-success DML)
   - 51 network records created (9 taxonomy + 42 valid payer + 15 IFC)
   - 3 staging records created with `PRM_Status__c = "Pending"`, `PRM_TargetObject__c = "HealthcarePlanNetwork"`
   - `PRM_ProcessingStatus__c = "Failed"` (because staging records exist)
   - Failure email sent with count: "3 records failed"
   - Exception log created
4. **Verify Staging Records:**
   - Open Case Manager → "Failed Records" related list shows 3 rows
   - `PRM_Payload__c` contains full JSON (deserializable)
   - `PRM_ErrorMessage__c` shows "Invalid HealthcarePlanNetworkId"

---

### Test 4: Retry — Manual Quick Action

1. **Setup:** Use test from Test 3 (3 staging records pending)
2. **Fix Data:** Create missing HealthcarePlanNetwork master records
3. **Execute:** Click "Retry Failed Processing" Quick Action on Case Manager
4. **Verify:**
   - 3 network records created successfully
   - 3 staging records updated: `PRM_Status__c = "Retried"`, `PRM_RetryCount__c = 1`
   - `PRM_ProcessingStatus__c = "Succeed"`
   - Success email sent
   - Case routed to "PRM - Network Creation Success" queue

---

### Test 5: Queueable Chain Depth (Critical)

1. **Execute:** Test 1 (Happy Path) in Full Sandbox (not Developer Edition)
2. **Monitor:** Query `AsyncApexJob` every 30 seconds during execution
3. **Verify:**
   - IP2 Queueable appears in queue (TX2 started)
   - IP2 completes (Status = Completed)
   - **IP3 Queueable appears in queue** (TX3 started) ← CRITICAL CHECK
   - IP3 completes (Status = Completed)
4. **If IP3 Never Appears:**
   - Queueable chaining is broken (configuration issue or IP2 not enqueueing IP3)
   - Check: `AddTaxNetworkLogicFromDelg` element exists in IP2 at level 0
   - Check: `useQueueable: true` set on element
   - Check: IP2 Try/Catch is not preventing IP3 enqueue

---

## Success Metrics

### Before Implementation (Current State)

| Metric | Current Value |
|--------|---------------|
| UI response time (3 locations) | 5+ minutes (timeout) |
| Governor limit failures | 40-60% of submissions |
| Silent failures (no exception log) | 100% of async failures |
| Manual remediation time per case | 2-3 hours |
| Support tickets per week | 15-20 |
| Operations team workload | 30-60 hours/week |

### After Implementation (Target)

| Metric | Target Value | Story |
|--------|--------------|-------|
| UI response time (3 locations) | < 3 seconds (TX1 async) | US #1 |
| Governor limit failures | 0% | US #1 |
| Silent failures | 0% (all logged) | US #1 |
| Failed records staged for retry | 100% | US #2 |
| User notification on completion | 100% (email) | US #3 |
| Processing status visibility | 100% (status field) | US #3 |
| Automatic case routing | 100% | US #4 |
| Manual remediation time per case | < 30 minutes (retry) | US #5 |
| Support tickets per week | < 5 (70% reduction) | All |
| Operations team workload | < 10 hours/week (80% reduction) | All |

---

## Dependencies & Risks

### Dependencies

| Dependency | Type | Impact if Missing | Mitigation |
|------------|------|-------------------|------------|
| Full Sandbox access | Infrastructure | Cannot test Queueable chaining | Reserve sandbox 2 weeks before Phase 1A deployment |
| Platform Event limits | Salesforce Limits | 10,000 events/day; 1,000/hour (may hit with high volume) | Monitor event usage; add throttling if needed |
| Email deliverability | Infrastructure | Notifications won't reach users | Test email templates in sandbox; verify DKIM/SPF |
| OmniStudio license | Licensing | Cannot modify IPs | Confirm licenses active for dev team |
| Queueable depth limit | Salesforce Limits | TX2 → TX3 chain may fail in Dev orgs | Use Full Sandbox for testing |

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Queueable chaining breaks in production (configuration error) | Medium | HIGH — TX3 never runs, no network records | Manual sandbox test (Test 5); deployment runbook includes monitoring for 48 hours |
| Platform Event delivery delay (> 5 minutes) | Low | MEDIUM — Exception logs delayed | Monitor `EventBusSubscriber` metrics; acceptable delay up to 10 minutes |
| Staging object grows unbounded (not cleaned up) | Medium | MEDIUM — Storage limits hit | Phase 2 includes automated retry + archival; add scheduled job to archive records > 90 days |
| TX1 still slow for 5+ locations (IP1 not refactored) | HIGH | MEDIUM — UI still waits 4-8 minutes | Separate story to refactor IP1 (Issue #2 in performance analysis); Phase 1 fixes 3-location scenario only |
| Retry mechanism creates duplicate records (no idempotency check) | Medium | MEDIUM — Duplicate network records | Add unique external ID to network records (e.g., hash of key fields); Database.upsert instead of insert |

---

## Appendix: Field Specifications

### IndividualApplication (Case Manager)

| Field API Name | Type | Values | Default | Description |
|----------------|------|--------|---------|-------------|
| `PRM_ProcessingStatus__c` | Picklist | Not Started, In Progress, Succeed, Failed | Succeed | Processing status for async workflows |
| `IsNetworkRecordsCreated__c` | Checkbox | true/false | false | Set by IP3 on successful network creation |
| `Failed_Record_Count__c` | Roll-Up Summary | COUNT(PRM_FailedRecordStaging__r) | 0 | Count of pending failed records |
| `Processing_Started_At__c` | DateTime | — | — | Timestamp when Container starts TX1 |
| `Processing_Completed_At__c` | DateTime | — | — | Timestamp when IP3 completes |
| `Processing_Duration__c` | Formula(Number) | (Completed - Started) * 24 * 60 | — | Duration in minutes |

### PRM_ExceptionLog__c

| Field API Name | Type | Description |
|----------------|------|-------------|
| `PRM_IndividualApplication__c` | Lookup(IndividualApplication) | Links to Case Manager (delete constraint: Set Null) |

### PRM_ExceptionLogEvent__e

| Field API Name | Type | Length | Description |
|----------------|------|--------|-------------|
| `PRM_RecordId__c` | Text | 18 | Case Manager Id |
| `PRM_RecordObjectName__c` | Text | 255 | Object API name (IndividualApplication) |

### PRM_FailedRecordStaging__c (NEW)

| Field API Name | Type | Length | Description |
|----------------|------|--------|-------------|
| `Name` | Auto-Number | — | FST-{0000} |
| `PRM_Status__c` | Picklist | — | Pending, Fixed, Retried, Failed - Terminal |
| `PRM_TargetObject__c` | Text | 255 | API name of target object |
| `PRM_Payload__c` | Long Text Area | 32,000 | JSON serialization of failed record |
| `PRM_CaseManager__c` | Lookup(IndividualApplication) | — | Parent Case Manager |
| `PRM_ExceptionLog__c` | Lookup(PRM_ExceptionLog__c) | — | Linked exception log |
| `PRM_ErrorMessage__c` | Text | 255 | SaveResult error message |
| `PRM_SourceFlow__c` | Text | 255 | IP/Flow that attempted creation |
| `PRM_RetryCount__c` | Number | — | Count of retry attempts (default 0) |
| `PRM_FailureType__c` | Text | 100 | Validation / Missing Reference / Duplicate / Other |

---

## Appendix: Deployment Checklist

### Pre-Deployment (Sandbox)

- [ ] All 5 user stories pass acceptance criteria
- [ ] Manual integration tests completed (Test 1-5)
- [ ] Apex test coverage > 90% for all classes
- [ ] Platform Event subscriber tested (exception log creation)
- [ ] Email templates tested (success / failure)
- [ ] Case routing tested (all queues)
- [ ] Retry mechanism tested (manual + automated)
- [ ] Performance validated: 3-location practitioner completes in < 15 minutes
- [ ] Governor limits validated: no exceptions in debug logs
- [ ] Page layouts updated (related lists, status field visible)
- [ ] List views created and tested
- [ ] Dashboard tested (Operations Manager can view metrics)

### Deployment to Production

**Order:**

1. Custom Fields (IndividualApplication, PRM_ExceptionLog__c, PRM_ExceptionLogEvent__e)
2. Custom Object (PRM_FailedRecordStaging__c)
3. Apex Classes (PRM_ExceptionLogger, PRM_OmniUtils, PRM_RetryFailedProcessingController, PRM_FailedRecordRetryBatch)
4. Apex Trigger (PRM_ExceptionLogEventTrigger)
5. Integration Procedures (Container, IP2, IP3 — in order)
6. Process Builder / Flow (Case Routing)
7. Queues, List Views, Page Layouts
8. Email Templates
9. Quick Action
10. Schedule Batch Job

### Post-Deployment (48 Hours)

- [ ] Monitor `AsyncApexJob` for IP2/IP3 Queueable jobs (no failures)
- [ ] Monitor `PRM_ExceptionLog__c` for new records (should be zero from normal processing)
- [ ] Spot-check 5 completed Case Managers: `IsNetworkRecordsCreated__c = true`, `PRM_ProcessingStatus__c = "Succeed"`
- [ ] Verify no governor limit exceptions in debug logs
- [ ] Confirm email notifications sent (check email logs)
- [ ] Verify case routing (successful cases in "Success" queue, failed cases in "Failed" queue)
- [ ] Check staging records: if any exist, verify they are in "Pending" status with correct payload

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-22  
**Next Review:** After Phase 1A completion
