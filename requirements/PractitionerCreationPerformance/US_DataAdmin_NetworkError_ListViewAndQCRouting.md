# USER STORY: Data Admin Network Record Creation Error Management

**Persona:** Data Admin, QC Specialist, Salesforce Administrator  
**Priority:** P0 — Operational gap; no visibility into async network creation failures; no recovery path without manual log inspection  
**Vertical:** Provider Network Management (PNM)  
**OmniScript:** `PRM_DelegatedPractitionerReviewScreen` (upstream trigger)  
**Integration Procedures:** `PRM_CreateDelegatedHFNRecords` (IP3), `PRM_ExistingPrimaryPracticeLocationLogicDelg` (IP2)  
**Relevant Requirements:** `US_PractitionerCreation_QueueableRefactor.md`, `PRM_Performance_Issues_Analysis_UserStories.md`, `TDD_Gap_Analysis.md`

---

# USER STORY 1: Data Admin List View for Network Record Creation Failures

## Story

**As a** Data Admin,  
**I want** a dedicated Salesforce List View on `PRM_ExceptionLog__c` that surfaces only network record creation failures (IP2 and IP3 batch errors) linked to Case Manager records,  
**So that** I can immediately identify which practitioners have failed network creation jobs without navigating individual Case Manager records or querying the database manually.

**Why it matters:** When `PRM_ExistingPrimaryPracticeLocationLogicDelg` (IP2) or `PRM_CreateDelegatedHFNRecords` (IP3) fail asynchronously, the Credentialing Specialist has no visibility — the UI has already returned. Exception logs are created via Platform Event on `PRM_ExceptionLog__c`, but there is no curated entry point for the Data Admin team to triage these failures. Without this list view, errors accumulate silently until a Credentialing Specialist notices missing network records on a Case Manager record.

---

## Scope

| Flow | Object | Affected Component | Data Source |
|------|--------|--------------------|-------------|
| Delegated Practitioner Creation | `PRM_ExceptionLog__c` | List View — filter on `PRM_ProcessName__c` | `PRM_ExceptionLogEventTrigger` (creates log records via Platform Event) |
| Delegated Practitioner Creation | `IndividualApplication` | `PRM_AsyncProcessingStatus__c` field | IP2/IP3 queueable transactions |
| Delegated Practitioner Creation | Case Manager record page | "Exception Logs" related list | `PRM_IndividualApplication__c` lookup on `PRM_ExceptionLog__c` |

---

## Current State (from codebase)

### `PRM_ExceptionLog__c`

- **`PRM_ProcessName__c`** (Text): Captures which IP failed — `PRM_ExistingPrimaryPracticeLocationLogicDelg` or `PRM_CreateDelegatedHFNRecords`
- **`PRM_IndividualApplication__c`** (Lookup → IndividualApplication): New field added in `US_PractitionerCreation_QueueableRefactor.md` — links exception log to Case Manager
- **`PRM_SeverityLevel__c`** (Text): `Error` for IP2/IP3 failures; `Warning` for non-critical issues
- **`PRM_ErrorMessage__c`** (Text): Human-readable error from the Catch block
- **`PRM_IntegrationType__c`** (Text): `ASYNC` for IP2/IP3 queueable failures
- **`PRM_StackTrace__c`** (Long Text): Full Apex stack trace
- **No existing List View** exists for the Data Admin persona — no curated, filtered view to triage network creation failures
- **Location:** `PRM_ExceptionLog__c` object (custom object in org)

### `IndividualApplication` (Case Manager)

- **`PRM_AsyncProcessingStatus__c`** (Picklist): `Not Started | Processing | Completed | Failed` — set to `Failed` by IP2/IP3 Catch block via Platform Event
- **`IsNetworkRecordsCreated__c`** (Checkbox): `false` when IP3 has not successfully completed
- **Location:** `IndividualApplication` custom fields (added in `US_PractitionerCreation_QueueableRefactor.md`)

### Data Admin Access

- **Current state:** No permission set or profile configuration targets the Data Admin team for `PRM_ExceptionLog__c` — access is not scoped to this persona
- **No List View:** Data Admins cannot self-serve triage; they must rely on Credentialing Specialists or developers to pull logs

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_ExceptionLog__c` — "Network Creation Errors" | List View | New list view filtered to `PRM_ProcessName__c IN ('PRM_CreateDelegatedHFNRecords', 'PRM_ExistingPrimaryPracticeLocationLogicDelg')` AND `PRM_SeverityLevel__c = 'Error'`, visible to Data Admin profile/permission set |
| `PRM_ExceptionLog__c` — List View columns | List View Config | Columns: `PRM_IndividualApplication__c` (Case Manager link), `PRM_ProcessName__c`, `PRM_ErrorMessage__c`, `PRM_SeverityLevel__c`, `PRM_IntegrationType__c`, `CreatedDate`, `PRM_NetworkErrorResolutionStatus__c` (new picklist — see below) |
| `PRM_ExceptionLog__c` — `PRM_NetworkErrorResolutionStatus__c` | Custom Field (Picklist) | New field: `Open \| In Review \| Resolved` — default `Open`; set to `In Review` when Data Admin opens record; set to `Resolved` when Data Admin confirms fix |
| `PRM_ExceptionLog__c` — `PRM_AssignedTo__c` | Custom Field (Lookup → User) | New lookup field to track which Data Admin is working the error |
| `PRM_ExceptionLog__c` — `PRM_ResolutionNotes__c` | Custom Field (Long Text) | New field for Data Admin to document what corrective action was taken |
| `PRM_ExceptionLog__c` page layout | Page Layout | Expose `PRM_IndividualApplication__c`, `PRM_NetworkErrorResolutionStatus__c`, `PRM_AssignedTo__c`, `PRM_ResolutionNotes__c` prominently; add "Go to Case Manager" button linking to `PRM_IndividualApplication__c` record |
| Data Admin Permission Set | Permission Set | Grant Read/Edit on `PRM_ExceptionLog__c`; Read on `IndividualApplication` (`PRM_AsyncProcessingStatus__c`, `IsNetworkRecordsCreated__c`) |
| Case Manager record page | Page Layout / App Builder | Add "Exception Logs" related list showing `PRM_ExceptionLog__c` records via `PRM_IndividualApplication__c` lookup; columns: `PRM_ProcessName__c`, `PRM_ErrorMessage__c`, `PRM_NetworkErrorResolutionStatus__c`, `CreatedDate` |

### List View Specification

**List View API Name:** `Network_Creation_Errors`  
**Label:** "Network Creation Errors — Needs Review"  
**Object:** `PRM_ExceptionLog__c`  
**Visibility:** Data Admin permission set or profile (do not set to "All Users")

**Filter Logic:**
```
(1) PRM_ProcessName__c IN ('PRM_CreateDelegatedHFNRecords', 'PRM_ExistingPrimaryPractitionerLocationLogicDelg')
AND
(2) PRM_SeverityLevel__c = 'Error'
AND
(3) PRM_NetworkErrorResolutionStatus__c != 'Resolved'
```

**Columns (in order):**

| Column | Field API Name | Notes |
|--------|---------------|-------|
| Case Manager | `PRM_IndividualApplication__c` | Hyperlink to IndividualApplication record |
| Process Failed | `PRM_ProcessName__c` | Shows IP2 vs. IP3 |
| Error Message | `PRM_ErrorMessage__c` | Truncated; full detail on record |
| Status | `PRM_NetworkErrorResolutionStatus__c` | Open / In Review / Resolved |
| Assigned To | `PRM_AssignedTo__c` | Data Admin responsible |
| Error Date | `CreatedDate` | Sorted descending by default |

**Default sort:** `CreatedDate` descending (newest errors first).

### New Custom Fields

| Object | Field Name | Type | Length / Values | Description |
|--------|-----------|------|-----------------|-------------|
| `PRM_ExceptionLog__c` | `PRM_NetworkErrorResolutionStatus__c` | Picklist | `Open; In Review; Resolved` | Tracks Data Admin remediation progress for network creation errors |
| `PRM_ExceptionLog__c` | `PRM_AssignedTo__c` | Lookup (User) | — | Data Admin assigned to investigate/resolve this error |
| `PRM_ExceptionLog__c` | `PRM_ResolutionNotes__c` | Long Text Area | 32,768 | Free-text notes documenting what was fixed |

---

## Acceptance Criteria

**AC-1: List View Is Accessible to Data Admin**

**Given** a user with the Data Admin permission set,  
**When** they navigate to the `PRM_ExceptionLog__c` tab and select the "Network Creation Errors — Needs Review" list view,  
**Then** they see only exception log records where `PRM_ProcessName__c` is `PRM_CreateDelegatedHFNRecords` or `PRM_ExistingPrimaryPracticeLocationLogicDelg`, `PRM_SeverityLevel__c` is `Error`, and `PRM_NetworkErrorResolutionStatus__c` is not `Resolved`.

---

**AC-2: List View Shows Case Manager Link**

**Given** a network creation failure has occurred and a `PRM_ExceptionLog__c` record was created by `PRM_ExceptionLogEventTrigger` with `PRM_IndividualApplication__c` populated,  
**When** the Data Admin views the "Network Creation Errors" list view,  
**Then** the Case Manager column displays a clickable link that navigates directly to the `IndividualApplication` record associated with the failed practitioner creation.

---

**AC-3: Error Count Is Accurate — Resolved Errors Are Excluded**

**Given** 10 network creation errors exist — 7 with `PRM_NetworkErrorResolutionStatus__c = Open`, 3 with `Resolved`,  
**When** the Data Admin loads the "Network Creation Errors — Needs Review" list view,  
**Then** exactly 7 records are displayed (the 3 Resolved errors are excluded by the list view filter).

---

**AC-4: Related List on Case Manager**

**Given** a Case Manager (`IndividualApplication`) record where `PRM_AsyncProcessingStatus__c = 'Failed'` and at least one `PRM_ExceptionLog__c` record is linked via `PRM_IndividualApplication__c`,  
**When** a Credentialing Specialist or Data Admin opens the Case Manager record,  
**Then** the "Exception Logs" related list is visible and shows the linked error records with `PRM_ProcessName__c`, `PRM_ErrorMessage__c`, `PRM_NetworkErrorResolutionStatus__c`, and `CreatedDate` columns.

---

**AC-5: Data Admin Cannot Delete Exception Log Records**

**Given** the Data Admin permission set,  
**When** the Data Admin views a `PRM_ExceptionLog__c` record,  
**Then** there is no "Delete" button available — only Edit is permitted (to update `PRM_NetworkErrorResolutionStatus__c`, `PRM_AssignedTo__c`, and `PRM_ResolutionNotes__c`).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Does a `PRM_ExceptionLog__c` tab already exist in the app? If not, should it be added to the PRM app's navigation bar? | Determines whether a tab creation step is needed | Technical / Product |
| 2 | What is the name of the Data Admin permission set or profile in this org? (e.g., `PRM_Data_Admin`) | Required to scope list view visibility and field permissions correctly | Technical / Ops |
| 3 | Should the "Network Creation Errors" list view also include IBC Professional failures (`PRM_PractitionerAddressCreation`) when that refactor is completed? | Future-proofing the filter — may need `PRM_PractitionerAddressCreation` added to the `IN` list | Product |
| 4 | Should `PRM_AssignedTo__c` be auto-populated (e.g., assigned to the logged-in user when they first open the record) via a Flow or screen action, or is manual assignment sufficient? | Determines whether a Record-Triggered Flow or Quick Action is needed for assignment | Product / Technical |
| 5 | Is there an existing `PRM_ExceptionLog__c` tab or list view that the Data Admin team currently uses? If yes, should the new list view be added alongside it or replace it? | Avoids creating a duplicate tab that confuses users | Technical / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_ExceptionLog__c` | Custom Object | HIGH | 3 new fields added; new list view created; page layout updated |
| Data Admin Permission Set | Permission Set | HIGH | New read/edit access to `PRM_ExceptionLog__c` and read access to key Case Manager fields |
| Case Manager (`IndividualApplication`) record page | Page Layout / App Builder | MEDIUM | "Exception Logs" related list added |
| `PRM_ExceptionLogEventTrigger` | Apex Trigger | LOW | No code change — existing trigger already populates `PRM_IndividualApplication__c`; this story depends on it deploying first |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_NetworkErrorResolutionStatus__c` picklist field | Custom Field | S | 3 values; default = Open |
| `PRM_AssignedTo__c` lookup field | Custom Field | S | Lookup to User |
| `PRM_ResolutionNotes__c` long text field | Custom Field | S | Simple additive field |
| "Network Creation Errors" list view | List View | S | Filter + column config; visibility scoping to permission set |
| `PRM_ExceptionLog__c` page layout update | Page Layout | S | Expose 3 new fields; add "Go to Case Manager" button |
| Data Admin Permission Set — field access | Permission Set | S | Field-level security on 3 new fields + existing `PRM_ExceptionLog__c` |
| Case Manager page layout — related list | Page Layout | S | Add "Exception Logs" related list with 4 columns |

**Total Estimated Effort:** ~0.5–1 day — **M**  
*(AI-estimated — validate with team. Depends on `US_PractitionerCreation_QueueableRefactor.md` deploying first — specifically `PRM_ExceptionLogEventTrigger` and the `PRM_IndividualApplication__c` lookup field.)*

---
---

# USER STORY 2: Data Admin Error Resolution & QC Team Routing

## Story

**As a** Data Admin,  
**I want** a Quick Action on the Case Manager (`IndividualApplication`) record that lets me confirm I have resolved the network record creation error and route the case to the QC team for review,  
**So that** the QC team is notified automatically when network records have been manually corrected, and the case proceeds through the credentialing workflow without the Credentialing Specialist manually tracking which cases were fixed.

**Why it matters:** When IP2 or IP3 fails asynchronously, the Case Manager is left in a `PRM_AsyncProcessingStatus__c = 'Failed'` state with `IsNetworkRecordsCreated__c = false`. There is currently no structured handoff mechanism — Data Admins fix records manually but have no way to signal that the fix is complete, which means cases sit unrouted and QC work stalls. Without a formal routing action, the QC team may pick up cases before network records are corrected, or never pick them up at all.

---

## Scope

| Flow | OmniScript / Component | Affected Step | Data Source |
|------|----------------------|---------------|-------------|
| Delegated Practitioner Creation — Error Recovery | `PRM_DataAdminRouteToQC` (new Quick Action) | Case Manager record action | `IndividualApplication` (`PRM_AsyncProcessingStatus__c`, `IsNetworkRecordsCreated__c`) |
| Case Lifecycle — QC Stage | `IndividualApplication` status field | Case status transition | Existing case status picklist |
| Error Log Closure | `PRM_ExceptionLog__c` | `PRM_NetworkErrorResolutionStatus__c` | Data Admin update (from US 1) |

---

## Current State (from codebase)

### `IndividualApplication` (Case Manager)

- **`PRM_AsyncProcessingStatus__c`** (Picklist): Set to `Failed` by IP2/IP3 Catch block; no mechanism exists to update it to a "Resolved" or "Ready for QC" state post-manual fix
- **`IsNetworkRecordsCreated__c`** (Checkbox): Remains `false` after failure; IP3 sets it to `true` only on successful async completion — if IP3 fails, there is no path to set it manually without developer intervention
- **No Quick Action or Flow** exists on the Case Manager record to transition a `Failed` async processing case to QC routing
- **Case Status field:** Cases in `Failed` async state are not progressed through the standard case lifecycle (Application Review → PSV → QC) — they are stuck at the creation stage

### Routing to QC — Current Behavior

- QC team receives cases through the standard case lifecycle managed by Credentialing Specialists via the `PRM_DelegatedPractitionerReviewScreen` OmniScript
- There is **no exception path** for Data Admin-resolved cases to re-enter the lifecycle and reach QC without Credentialing Specialist re-submission
- Data Admins currently resolve records manually and notify QC via email or Slack — no Salesforce-native handoff

---

## Proposed Design

### Quick Action: "Mark Resolved & Route to QC"

A Salesforce Quick Action (Screen Flow or OmniScript) on the `IndividualApplication` (Case Manager) object that:

1. **Validates** that all linked open `PRM_ExceptionLog__c` records for this Case Manager are marked `Resolved` (prevents premature routing)
2. **Updates** `IsNetworkRecordsCreated__c = true` on the Case Manager
3. **Updates** `PRM_AsyncProcessingStatus__c = 'Completed'` on the Case Manager
4. **Transitions** the Case Manager to the QC stage (updates the case status field to the appropriate QC stage value)
5. **Assigns** the Case Manager to the QC team queue
6. **Marks** all linked open `PRM_ExceptionLog__c` records as `Resolved` (bulk update)
7. **Sends** an in-app notification or Chatter post to the QC team queue/group alerting them a case is ready for review

The Quick Action is only available (visible) when `PRM_AsyncProcessingStatus__c = 'Failed'` — it should not appear on cases that are processing normally.

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| `PRM_RouteToQC_QuickAction` | Screen Flow (Quick Action) | New Screen Flow invoked as a Quick Action on `IndividualApplication`; validates error resolution, updates case status, routes to QC queue |
| `IndividualApplication` — Quick Action Button | Page Layout | Add "Mark Resolved & Route to QC" button to Case Manager record page, visible only when `PRM_AsyncProcessingStatus__c = 'Failed'` (use Dynamic Actions on Lightning page) |
| `IndividualApplication` — `PRM_AsyncProcessingStatus__c` | Picklist | Add new value: `Resolved — Routed to QC` (to distinguish Data Admin-resolved cases from normally-completed async cases) |
| `PRM_ExceptionLog__c` — bulk `PRM_NetworkErrorResolutionStatus__c` update | Flow DML | Quick Action flow bulk-updates all linked Open/In Review exception log records to `Resolved` when routing is confirmed |
| QC Team Queue | Salesforce Queue | Case Manager record's owner/queue field updated to QC team queue upon routing; confirm API name of the existing QC queue |
| Chatter / In-App Notification | Flow Action | Flow posts a Chatter message on the Case Manager record tagging the QC team group, OR triggers an in-app notification to the QC queue members |
| `IndividualApplication` page layout — Dynamic Actions | App Builder | Add condition: show "Mark Resolved & Route to QC" button ONLY when `PRM_AsyncProcessingStatus__c = 'Failed'` |

### Screen Flow Specification — `PRM_RouteToQC_QuickAction`

**Flow Type:** Screen Flow (launched as Quick Action from Case Manager record)  
**Entry Object:** `IndividualApplication`

**Step 1 — Validation Screen:**
- Query `PRM_ExceptionLog__c` WHERE `PRM_IndividualApplication__c = {recordId}` AND `PRM_NetworkErrorResolutionStatus__c != 'Resolved'`
- If unresolved exception logs exist → Display warning screen: "There are {N} unresolved error log(s) linked to this Case Manager. Please resolve all errors before routing to QC. [View Errors] [Cancel]"
- If zero unresolved exception logs → Proceed to Step 2

**Step 2 — Confirmation Screen:**
- Display: "You are about to route this Case Manager to the QC team. This confirms all network records have been manually corrected."
- Show summary: Case Manager Name, Practitioner Name, number of exception logs resolved
- Buttons: [Confirm & Route to QC] [Cancel]

**Step 3 — Updates (on confirmation):**

```
1. Update IndividualApplication:
   - IsNetworkRecordsCreated__c = true
   - PRM_AsyncProcessingStatus__c = 'Resolved — Routed to QC'
   - OwnerId = [QC Team Queue Id]
   - [Case status field] = [QC stage picklist value — confirm with team]

2. Bulk Update PRM_ExceptionLog__c:
   - WHERE PRM_IndividualApplication__c = {recordId}
     AND PRM_NetworkErrorResolutionStatus__c IN ('Open', 'In Review')
   - SET PRM_NetworkErrorResolutionStatus__c = 'Resolved'

3. Chatter Post on IndividualApplication:
   - Body: "Network records have been manually corrected by {Data Admin Name}.
             This case has been routed to QC for review.
             Exception log(s) resolved: {N}.
             @[QC Team Group]"
```

**Step 4 — Success Screen:**
- "Case Manager has been routed to the QC team. The QC team has been notified."
- [Close] button

### New Picklist Value

| Object | Field | New Value | Notes |
|--------|-------|-----------|-------|
| `IndividualApplication` | `PRM_AsyncProcessingStatus__c` | `Resolved — Routed to QC` | Distinct from `Completed` (which means async processing finished normally) — signals a Data Admin manually resolved a failure |

---

## Acceptance Criteria

**AC-1: Quick Action Visibility — Only When Status Is Failed**

**Given** a Case Manager record where `PRM_AsyncProcessingStatus__c = 'Processing'` or `'Completed'` or `'Not Started'`,  
**When** a Data Admin opens the record,  
**Then** the "Mark Resolved & Route to QC" Quick Action button is NOT visible on the record page.

**Given** a Case Manager record where `PRM_AsyncProcessingStatus__c = 'Failed'`,  
**When** a Data Admin opens the record,  
**Then** the "Mark Resolved & Route to QC" button IS visible in the record's action bar.

---

**AC-2: Validation Blocks Routing When Unresolved Errors Exist**

**Given** a Case Manager with `PRM_AsyncProcessingStatus__c = 'Failed'` and 2 linked `PRM_ExceptionLog__c` records where `PRM_NetworkErrorResolutionStatus__c = 'Open'`,  
**When** the Data Admin clicks "Mark Resolved & Route to QC",  
**Then** the flow displays a warning screen listing the unresolved error count and does NOT proceed to update the Case Manager or route to QC until all linked errors are marked `Resolved`.

---

**AC-3: Successful Routing Updates All Fields**

**Given** a Case Manager with `PRM_AsyncProcessingStatus__c = 'Failed'` and all linked `PRM_ExceptionLog__c` records already set to `Resolved`,  
**When** the Data Admin confirms routing via the Quick Action,  
**Then**:
- `IsNetworkRecordsCreated__c = true` on the Case Manager
- `PRM_AsyncProcessingStatus__c = 'Resolved — Routed to QC'` on the Case Manager
- Case Manager `OwnerId` is updated to the QC team queue
- Case Manager status field is updated to the QC-stage picklist value
- A Chatter post appears on the Case Manager record confirming the routing and tagging the QC team group

---

**AC-4: Bulk Exception Log Closure on Routing**

**Given** a Case Manager with 3 linked `PRM_ExceptionLog__c` records (2 `Resolved`, 1 `In Review`),  
**When** the Data Admin confirms the "Mark Resolved & Route to QC" action,  
**Then** the `In Review` exception log record is automatically updated to `Resolved` — no manual cleanup required by the Data Admin after routing.

---

**AC-5: QC Team Receives Notification**

**Given** the Quick Action routing completes successfully,  
**When** the Chatter post is published on the Case Manager record,  
**Then** the QC team group members receive a Chatter notification, and the Case Manager record appears in the QC team queue's list view.

---

**AC-6: Data Admin Cannot Route Without Prior Fix Confirmation**

**Given** a Case Manager where network records are still missing (verified by the Data Admin opening the Case Manager and confirming the records exist),  
**When** the Data Admin has NOT marked any linked exception log records as `Resolved`,  
**Then** the validation screen in step 1 of the flow blocks routing and displays: "There are N unresolved error log(s) linked to this Case Manager."

*(Note: The flow cannot programmatically verify that records were actually fixed in the org — it validates that the Data Admin has explicitly marked all exception logs as Resolved, which serves as a process acknowledgment.)*

---

**AC-7: Routing Is Idempotent — Cannot Double-Route**

**Given** a Case Manager already in `PRM_AsyncProcessingStatus__c = 'Resolved — Routed to QC'`,  
**When** a Data Admin opens the record,  
**Then** the "Mark Resolved & Route to QC" button is NOT visible (Dynamic Action condition no longer met — status is not `Failed`).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What is the API name and picklist value of the QC stage on the Case Manager status field? (e.g., is it `Status__c` with value `QC Review`?) | Required for Step 3 of the flow to set the correct status value | Technical / BA |
| 2 | What is the Salesforce Queue API name for the QC team? | Required for the `OwnerId` assignment step in the flow | Technical / Ops |
| 3 | Is there an existing Chatter group for the QC team? If not, should the notification be an in-app notification (`CustomNotificationType`) instead of Chatter? | Affects notification mechanism in Step 3 | Product / Ops |
| 4 | Should the "Mark Resolved & Route to QC" action be a Screen Flow Quick Action, an OmniScript, or a Lightning Web Component? The Screen Flow is the lowest-effort option but OmniScript would be consistent with other PRM guided actions. | Affects build time by 1–2 days if OmniScript is preferred | Technical / Product |
| 5 | Are there any existing validation rules or triggers on `IndividualApplication` that prevent status transitions outside the normal OmniScript-driven flow? If yes, the Quick Action flow may need to bypass them via a custom setting or Apex method. | Risk of flow failure during the status update step | Technical |
| 6 | Should the QC team be able to see *which* specific network records were missing (e.g., taxonomy vs. payer network vs. IFC) from the Chatter post or notification? If yes, the `PRM_ProcessName__c` from the exception log should be included in the Chatter message. | Enriches QC team context but adds complexity to the Chatter post template | Product |
| 7 | Is a "Re-trigger IP3" path also needed (to re-run `PRM_CreateDelegatedHFNRecords` rather than fixing records manually), per the follow-on story noted in `US_PractitionerCreation_QueueableRefactor.md`? If so, should that be a separate button or part of this same Quick Action? | Scope creep risk if included here — recommend separate story | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_RouteToQC_QuickAction` (Screen Flow) | Flow | HIGH | New multi-step Screen Flow with validation, bulk DML, Chatter post — central to the story |
| `IndividualApplication` | Custom Object | MEDIUM | New picklist value on `PRM_AsyncProcessingStatus__c`; Quick Action added to page layout with Dynamic Actions |
| `PRM_ExceptionLog__c` | Custom Object | LOW | Bulk update of `PRM_NetworkErrorResolutionStatus__c` — additive DML from within the flow |
| QC Team Queue | Queue / Assignment | MEDIUM | Case Manager ownership transferred; QC team sees new records in their queue |
| Chatter / Notification | Platform Feature | LOW | Chatter post or in-app notification to QC group — no code change to existing components |
| `US_PractitionerCreation_QueueableRefactor.md` | Dependency | HIGH | The `PRM_AsyncProcessingStatus__c` field and `IsNetworkRecordsCreated__c` field must be deployed before this story can be built |
| US 1 (List View story) | Dependency | HIGH | `PRM_NetworkErrorResolutionStatus__c` field on `PRM_ExceptionLog__c` must exist for the routing validation step to query it |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_RouteToQC_QuickAction` Screen Flow | Flow (new, multi-step) | L | 4-step flow with subflow-style validation, bulk DML, Chatter post, and confirmation screen |
| `IndividualApplication` Quick Action configuration | Quick Action / Page Layout | S | Attach flow to Quick Action; add to page layout with Dynamic Action condition |
| `PRM_AsyncProcessingStatus__c` new picklist value | Picklist | S | Add `Resolved — Routed to QC` value |
| Dynamic Actions — button visibility condition | App Builder | S | Condition: `PRM_AsyncProcessingStatus__c = 'Failed'` |
| QA testing — end-to-end scenario | QA | M | Force IP3 failure → Data Admin resolves → routes → confirm QC queue receipt + Chatter notification |

**Total Estimated Effort:** ~1–2 days — **L**  
*(AI-estimated — validate with team. Effort is higher if an OmniScript is preferred over Screen Flow, or if existing validation rules on `IndividualApplication` require Apex workarounds.)*

---

## Dependency Chain

These two stories must deploy in this order:

```
1. US_PractitionerCreation_QueueableRefactor.md  (P0 — must be live first)
   ↳ Deploys: PRM_ExceptionLog__c lookup, PRM_AsyncProcessingStatus__c, IsNetworkRecordsCreated__c,
              PRM_ExceptionLogEventTrigger

2. USER STORY 1 — Data Admin List View  (this file, US 1)
   ↳ Deploys: PRM_NetworkErrorResolutionStatus__c, PRM_AssignedTo__c, PRM_ResolutionNotes__c,
              "Network Creation Errors" list view, Data Admin permission set updates

3. USER STORY 2 — Data Admin Routing Quick Action  (this file, US 2)
   ↳ Deploys: PRM_RouteToQC_QuickAction flow, Quick Action button, new picklist value,
              Dynamic Actions config, QC queue assignment
```

---

## Related Stories

| Story | Priority | Status | Relationship |
|-------|----------|--------|--------------|
| `US_PractitionerCreation_QueueableRefactor.md` | P0 | In progress | **Prerequisite** — must deploy before either story in this file |
| Re-trigger IP3 Quick Action (retry failed network creation without manual record creation) | P0 | Not scoped | Follow-on to US 2 — separate story; referenced in `US_PractitionerCreation_QueueableRefactor.md` related stories |
| IBC Professional Practitioner Address Creation performance refactor | P0 | Not scoped | Independent — same error logging pattern will apply once `PRM_PractitionerAddressCreation` is refactored |
| User-facing processing status indicator on Case Manager (Processing → Completed / Failed toast or banner) | P1 | Not scoped | Complements this story; improves Credentialing Specialist visibility |
