# USER STORY 1: Backfill Practitioner PNC from Updated Account PNC Data

**Persona:** PNM Specialist, Developer  
**Priority:** P0  
**OmniScript:** N/A  
**Integration Procedures:** N/A  
**Relevant Requirements:** PNM PNC backfill request

---

## Story

**As a** PNM Specialist,  
**I want** a one-time manual batch script to backfill practitioner `PNC` values after the business provides an updated list of `Account` records to mark as `PNC = true`,  
**So that** practitioner PNC status is recalculated correctly based on the updated account-level data and remains aligned with the active practitioner practice-location affiliations.

**Why it matters:** The business needs a controlled data correction after load to ensure practitioner PNC reflects the updated account PNC source data. This is a one-time remediation, not an ongoing automation.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| PNC Backfill | N/A | One-time Apex batch/script execution | Updated Account list provided by business; active `HealthcarePractitionerFacility` location affiliations; existing PNC rollup logic |

---

## Current State (from codebase)

### PNC rollup behavior

- Practitioner `Account.PRM_PNC__c` is currently maintained through existing PNC update logic.
- Existing logic evaluates practitioner practice-location affiliations and updates practitioner PNC based on related location/account data.
- This story does not introduce a new UI or new data model.

### Data correction need

- Business will provide the list of accounts that must be set to `PNC = true`.
- After those account updates are loaded, a backfill process is needed to recalculate practitioner PNC for active location affiliations only.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **New backfill batch/script** | Apex Batch / Script | Create a one-time manual batch that processes the business-provided list of accounts marked `PNC = true` and recalculates linked practitioner PNC values |
| **PNC rollup evaluation** | Apex logic | Ensure practitioner PNC is set to `true` only when **all active linked practice-location affiliations** are PNC |
| **Inactive affiliation handling** | Apex logic | Ignore inactive `HealthcarePractitionerFacility` location affiliations during the rollup |
| **No-affiliation handling** | Apex logic | If a practitioner has no active practice-location affiliations, set practitioner `PNC = false` |
| **Validation output** | Batch reporting | Log counts for updated accounts, processed practitioners, practitioners set to `true`, practitioners set to `false`, and failures |
| **Error handling** | Batch reporting / retry support | Capture failed records and summary details so the run can be reviewed and rerun if needed |

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|-------|
| N/A | N/A | N/A | N/A | No OmniStudio change required for this story |

### Example logic

```apex
// High-level intent only
// 1. Load business-provided Account Ids
// 2. Update Account.PRM_PNC__c = true for the provided list
// 3. Query active HealthcarePractitionerFacility location affiliations
// 4. For each practitioner, set PNC true only if all active linked locations are PNC
// 5. If no active affiliations exist, set PNC false
// 6. Write execution summary and failures to logs
```

---

## Acceptance Criteria

**Given** the business has provided a list of Account records to be updated to `PNC = true`,  
**When** the one-time manual backfill batch is executed after the data load,  
**Then** the script shall update only the specified Account records and then recalculate practitioner PNC using the existing PNC rollup rules.

**Given** a practitioner has one or more active `HealthcarePractitionerFacility` location affiliations,  
**When** the backfill script evaluates that practitioner,  
**Then** practitioner `PNC` shall be set to `true` only if **all** active linked practice-location affiliations are PNC.

**Given** a practitioner has any active linked practice-location affiliation that is not PNC,  
**When** the backfill script evaluates that practitioner,  
**Then** practitioner `PNC` shall be set to `false`.

**Given** a practitioner has no active practice-location affiliations after the load,  
**When** the backfill script evaluates that practitioner,  
**Then** practitioner `PNC` shall be set to `false`.

**Given** the backfill batch completes successfully,  
**When** the run summary is reviewed,  
**Then** it shall report the number of accounts updated, practitioners processed, practitioners set to `true`, practitioners set to `false`, and any failures.

**Given** one or more records fail during batch processing,  
**When** the script finishes,  
**Then** the failure details shall be captured in the run output or logs so the failed records can be reviewed and rerun manually.

**Given** this is a one-time manual remediation,  
**When** the batch is deployed,  
**Then** it shall not run on a schedule and shall only execute when manually invoked.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What exact account list format will business provide for the backfill input? | Determines whether the batch reads from a CSV, custom object, static list, or manual parameter | Business / Technical |
| 2 | Where should the execution summary and failures be stored? | Affects whether logs are written to debug logs, a custom object, or a file export | Technical |
| 3 | Should the batch update only practitioner `Account.PRM_PNC__c`, or also write any audit field / timestamp? | Impacts data traceability and rollback support | Technical |
| 4 | What batch size should be used for the manual run? | Impacts performance and governor limit safety | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| Backfill batch/script | Apex | HIGH | New one-time remediation logic required |
| Practitioner PNC rollup | Apex | HIGH | Must enforce “all active locations PNC” rule |
| Account PNC data load | Data load / config | MEDIUM | Business-provided Account list must be updated before the batch runs |
| Logging / validation | Apex | MEDIUM | Needed to verify results and capture failures |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Backfill batch/script | Apex batch | L | One-time manual batch with input handling and summary reporting |
| Practitioner rollup evaluation | Apex logic | M | Reuse existing logic pattern but enforce active-location-only and “all” rule |
| Error handling and logging | Apex / config | M | Capture failures and execution summary |
| Validation support | Apex / reporting | S | Counts and post-run verification summary |

**Total Estimated Effort:** AI-estimated — validate with team — **L**

