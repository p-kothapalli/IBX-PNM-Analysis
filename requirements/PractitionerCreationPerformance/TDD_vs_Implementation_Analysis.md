# Technical Design Analysis: Practitioner Creation Performance Fix
## Comparison of Proposed TDD vs. Current Implementation Plan

**Date:** 2026-04-22  
**Author:** Technical Analysis  
**Purpose:** Evaluate whether the new Technical Design Document (TDD) addresses the identified performance issues and gaps

---

## Executive Summary

### The Problem
- **Current State:** Practitioner creation with 3+ practice locations causes 5+ minute UI freeze, governor limit failures, and silent data corruption
- **Volume:** 54-69 records created per practitioner (9 taxonomy + 45 payer networks + 15 IFC records)
- **Impact:** 15-20 support tickets/week, 2-3 hours manual remediation per case

### What's Been Documented So Far

**1. Original Research** (`PRM_NetworkCreation_Issue_Summary.md`)
- Recommended: Full event-driven Batch Apex architecture
- Platform Event → 3 chained batch classes → email notifications
- UI returns immediately (< 3 seconds)
- User-visible progress tracking

**2. Current Implementation Approach** (TDD + User Story)
- Queueable-based refactoring (lighter approach)
- Split transaction: Container+IP1 → Queueable IP2 → Queueable IP3
- Exception logging via Platform Events to survive rollbacks
- Status tracking via `IsNetworkRecordsCreated__c` flag

**3. Gap Analysis** (`TDD_Gap_Analysis.md`)
- Identified 8 critical implementation risks
- Proposed 7 improvements to bridge gaps
- Highlighted missing retry mechanism

---

## Does the TDD Fix the Core Performance Problem?

### ✅ YES — Governor Limits Will Be Resolved

The TDD's transaction splitting approach **will solve the governor limit issue**:

| Metric | Before | After (TDD) | Result |
|--------|--------|-------------|--------|
| **SOQL Queries** | 100 limit (hitting) | TX1: 120, TX2: 150, TX3: 120 (renewable) | ✅ **FIXED** |
| **CPU Time** | 60,000ms (hitting) | TX1: 10,000ms, TX2: 60,000ms, TX3: 60,000ms | ✅ **FIXED** |
| **Heap Size** | 12MB (approaching) | TX1: 6MB, TX2: 12MB, TX3: 12MB (renewable) | ✅ **FIXED** |
| **Transaction Scope** | Single synchronous transaction | 3 independent async transactions | ✅ **FIXED** |

**Reasoning:**
- Breaking the 280+ operations across 3 separate Apex transactions gives each its own governor limit budget
- IP2 and IP3 run as Queueables with elevated async limits (200 queries, 60s CPU)
- For 3 locations (current failure scenario): TX1 handles addresses/facilities, TX2 handles HCPF records, TX3 handles 54 network records
- Each transaction scope is now well within limits

---

## Does the TDD Fix the User Experience Problem?

### ⚠️ PARTIALLY — UI Still Waits for TX1 to Complete

**What Users See Today:**
- Submit form → UI spins 5+ minutes → timeout/no feedback

**What Users Will See With TDD:**
- Submit form → **UI still waits for TX1 (Container + IP1)** → TX1 completes → UI returns
- For 3+ locations, IP1 alone can take **2-4 minutes** (creates 90-120 records: addresses, facilities, locations, HCPF base records, identifiers, provider features)
- User still stares at buffering screen for minutes

**Why TX1 Is Still Slow:**
- `PRM_PractitionerAddressCreation` (IP1) has **100+ sequential steps**
- Per the `PRM_Performance_Issues_Analysis_UserStories.md`:
  - 2-3 locations: 60-100 records in TX1 → 3-6 minutes
  - 5 locations: 150-250 records in TX1 → 10-20+ minutes
- IP1 remains chainable (synchronous) — the OmniScript won't return until TX1 commits

**Gap from Original Recommendation:**
- Original research: "UI returns in < 3 seconds with 'Processing...' message"
- TDD: User still waits for full TX1 completion before seeing anything

### ❌ NO — Missing User Notification & Status Visibility

**What the Original Requirements Called For:**
1. ✅ Immediate UI response (< 3 seconds) — **NOT delivered by TDD**
2. ❌ "Processing..." banner visible while async work runs — **NOT in TDD**
3. ❌ Email notification on completion/failure — **NOT in TDD**
4. ❌ Status field showing "Processing Taxonomies → Payer Networks → IFC" — **NOT in TDD**
5. ❌ Timestamps (Queued At, Started At, Completed At) — **NOT in TDD**

**What the TDD Delivers for UX:**
- `IsNetworkRecordsCreated__c` checkbox (true/false) — binary, not progress
- `PRM_AsyncProcessingStatus__c` picklist (via gap improvements) — static status, no real-time updates
- Exception logs linked to Case Manager — good for debugging, not user communication

**User Impact:**
- Users still have no in-flow feedback that processing is happening
- Must manually check Case Manager record after submission to see if network records were created
- No notification if IP2 or IP3 fails — user has to remember to check back
- Original complaint was "UI spins with no feedback" — TDD reduces spin time but doesn't add feedback

---

## Does the TDD Fix the Data Consistency Problem?

### ✅ YES — Exception Logging Will Capture Failures

**Before:**
- `rollbackOnError = true` + direct DML insert to `PRM_ExceptionLog__c` → rolled back together
- Silent failures: no error record, no visibility, no recovery path

**After (TDD):**
- Exception logs written via `PRM_ExceptionLogEvent__e` (Platform Event)
- `publishBehavior = PublishImmediately` → survives transaction rollback
- `PRM_ExceptionLogEventTrigger` creates `PRM_ExceptionLog__c` in separate transaction
- Lookup field links exception log to Case Manager → visible in related list

**Result:**
- ✅ No more silent failures
- ✅ Operations team can query failed cases
- ✅ Exception logs contain full error message, stack trace, payload

### ⚠️ PARTIAL — No Automated Retry, Manual Recovery Required

**What Happens When IP2 or IP3 Fails:**

**Scenario A: IP1 Fails (TX1)**
- ✅ Full rollback of Container + IP1 DML
- ✅ Exception log created (via Platform Event)
- ✅ No orphaned records

**Scenario B: IP2 Fails (TX2)**
- ❌ TX1 records (addresses, facilities, locations, HC practitioners) **persist as orphans**
- ✅ IP2's DML (HCPF records, provider features) rolls back
- ✅ Exception log created
- ❌ **No automated recovery path** — requires manual intervention

**Scenario C: IP3 Fails (TX3)**
- ❌ TX1 + TX2 records persist
- ✅ IP3's DML (taxonomy networks, payer networks, IFC records) rolls back
- ✅ Exception log created
- ❌ **No automated recovery path** — requires manual intervention

**Gap:**
- The TDD explicitly states: "Option 1 (Manual Retry) recommended for Scenario B/C"
- But **Option 1 is not scoped in the delivery** (see Issue #7 in Gap Analysis)
- Without retry mechanism:
  - Operations team must manually create 54 network records per failed practitioner
  - Original workaround (2-3 hours) still required for partial failures
  - Silent failure replaced with **loud failure requiring manual cleanup**

**From the Gap Analysis:**
> "Retry orchestration is intentionally **out of scope for this phase**. For now, we are doing one thing well: capturing failed processing data in `PRM_FailedRecordStaging__c` so nothing is lost and users have a clear queue of what needs attention."

**But:** The TDD **does not implement `PRM_FailedRecordStaging__c`** — it only logs to `PRM_ExceptionLog__c`. The new technical design document you provided **does** propose staging (`PRM_FailedRecordStaging__c`), but the current implementation user story does not include it.

---

## Key Differences: New TDD vs. Current Implementation

### Architecture

| Dimension | Current Implementation (User Story) | New TDD (Your Document) |
|-----------|-------------------------------------|------------------------|
| **Core Strategy** | Queueable refactor (3 transactions) | Queueable refactor + **Staging object** |
| **UI Response** | Waits for TX1 (2-4 min for 3 locations) | Immediate navigation + "Processing..." banner |
| **Status Tracking** | `IsNetworkRecordsCreated__c` (binary) + `PRM_AsyncProcessingStatus__c` (static) | `PRM_ProcessingStatus__c` (In Progress → Succeed/Failed) + refresh event |
| **Failure Handling** | Exception log only | Exception log + **`PRM_FailedRecordStaging__c`** (business-friendly queue) |
| **Partial Success** | `allOrNone = true` (full rollback per TX) | `allOrNone = false` (partial-success DML) |
| **User Notification** | None | Email on completion/failure |
| **Retry Mechanism** | Not scoped (manual) | Future phase (staging prepares for it) |
| **Rollback Scope** | Per-transaction only | Per-transaction + staging for failed records |

### What the New TDD Adds (Not in Current Implementation)

**1. Failed Record Staging (`PRM_FailedRecordStaging__c`)**
- **Purpose:** Business-friendly queue for operations team to review/fix/retry failed records
- **Fields:** Original payload, target object, parent record, Case Manager, source flow, exception log link, lifecycle status (Pending → Fixed)
- **Why it matters:** `PRM_ExceptionLog__c` is for engineering diagnostics — not practical for business remediation

**2. Partial-Success DML (`allOrNone = false`)**
- **Purpose:** Allow IP3 to create as many network records as possible, stage the failed ones, rather than rolling back all 54 records if one fails
- **Impact:** Better data outcome — if 53 of 54 networks succeed, user gets 53 networks + 1 staged failure record, not 0 networks

**3. UX Improvements**
- **Immediate Navigation:** User gets Case Manager Id and is routed immediately (TX1 no longer blocks UI return)
- **Progress Banner:** Shows `PRM_ProcessingStatus__c` value while `In Progress`
- **Duplicate Prevention:** Blocks repeated submissions while `In Progress`
- **Notifications:** Email on `Succeed` or `Failed`

**4. Processing Status Field Contract**
- `PRM_ProcessingStatus__c` (Picklist on CaseDataManager):
  - Default: `Succeed` (for all other flows)
  - Set to `In Progress` when IP1 starts (in Container)
  - Set to `Failed` if IP2/IP3 async processing errors
  - Set to `Succeed` when IP3 completes successfully
- Platform event (`PRM_RecordStagingEvent__e`) refreshes UI when status changes

---

## Critical Questions: Which Design Should Be Implemented?

### Option A: Current User Story (Queueable Refactor Only)

**Pros:**
- ✅ Lower complexity (no Batch Apex, no staging object, no events beyond exception logging)
- ✅ Fixes governor limit issue (primary technical blocker)
- ✅ No silent failures (exception logs survive rollback)
- ✅ Faster to implement (~7-9 days estimated)

**Cons:**
- ❌ UI still waits 2-4 minutes (TX1 synchronous)
- ❌ No user notification (users must check Case Manager manually)
- ❌ No retry path (manual cleanup still required for partial failures)
- ❌ No staging queue (operations team has no actionable work queue)
- ❌ Doesn't meet original acceptance criteria ("UI returns in < 3 seconds")

**When to Choose:**
- Need to deploy a fix **immediately** to stop production failures
- Operations team is willing to manually retry partial failures from exception logs
- UX improvement can be deferred to Phase 2

---

### Option B: New TDD (Queueable + Staging + UX)

**Pros:**
- ✅ Fixes governor limit issue
- ✅ Immediate UI return (< 3 seconds) — meets original requirement
- ✅ User-facing status and notifications
- ✅ Business-friendly staging queue for failed records
- ✅ Partial-success DML reduces all-or-nothing rollback impact
- ✅ Prepares foundation for automated retry (future phase)
- ✅ Reusable staging pattern for other flows (Issue #2-#5 in performance analysis)

**Cons:**
- ❌ Higher complexity (staging object, processing status, platform events, banner component)
- ❌ Longer implementation time (~2-3 weeks estimated)
- ❌ Requires UX/UI work (banner component, status display)
- ❌ Retry mechanism still future-phased (manual cleanup in Phase 1)

**When to Choose:**
- Have 2-3 sprint capacity to implement properly
- Want to meet original acceptance criteria (< 3s UI response)
- Operations team needs a work queue (not just exception logs)
- Planning to implement retry in next sprint (staging is prerequisite)

---

## Does the New TDD Fix the Problem? — Final Verdict

### ✅ **YES** — If You Implement the Full New TDD Design

**What It Fixes:**
1. ✅ **Governor limits** — same as Option A (Queueable split)
2. ✅ **UI responsiveness** — immediate return (< 3s) — **NEW**
3. ✅ **Silent failures** — exception logging (same as Option A)
4. ✅ **User visibility** — status field + notifications — **NEW**
5. ✅ **Partial data loss** — staging captures failed records for future retry — **NEW**
6. ⚠️ **Automated recovery** — not in Phase 1, but staging prepares for Phase 2

**What It Doesn't Fix (Yet):**
- ❌ Automated retry (explicitly out of scope for Phase 1 in both designs)
- ❌ TX1 still heavy for large practitioners (5+ locations) — IP1 refactor needed (separate story)

---

### ⚠️ **PARTIALLY** — If You Implement Only the Current User Story

**What It Fixes:**
1. ✅ **Governor limits** — yes
2. ❌ **UI responsiveness** — no (TX1 still blocks UI for 2-4 minutes)
3. ✅ **Silent failures** — yes (exception logging)
4. ❌ **User visibility** — minimal (no notifications, no progress updates)
5. ❌ **Partial data loss** — no staging queue (manual cleanup from exception logs)
6. ❌ **Automated recovery** — not scoped

**Result:**
- Production crashes stop (governor limits fixed)
- But user experience is still poor (long waits, no feedback)
- Operations team still does manual work (from exception logs instead of no logs)

---

## Recommendation

### Immediate Action (Next Sprint)
**Implement the New TDD Design (Option B)** with these phases:

**Phase 1A (Sprint 1 — 2 weeks): Core Performance + Staging**
- Queueable refactor (TX1 / TX2 / TX3 split)
- Exception logging via Platform Event (rollback-safe)
- `PRM_FailedRecordStaging__c` object + lifecycle status (Pending/Fixed)
- `PRM_ProcessingStatus__c` field on CaseManager (In Progress / Succeed / Failed)
- Immediate UI return (< 3 seconds) — IP1 must also become Queueable or Container must commit+enqueue
- **Partial-success DML** (`allOrNone = false` in IP3) — stage failures instead of full rollback

**Phase 1B (Sprint 2 — 1 week): User Notification**
- Email templates (success / failure)
- Platform event for UI refresh (`PRM_RecordStagingEvent__e`)
- Progress banner component (reads `PRM_ProcessingStatus__c`)
- Duplicate submission prevention (while `In Progress`)

**Phase 2 (Sprint 3 — 2 weeks): Retry Mechanism**
- Quick Action or OmniScript button on CaseManager: "Retry Failed Processing"
- Reads from `PRM_FailedRecordStaging__c` where Status = Pending
- Re-invokes IP2 or IP3 with staged payload
- Updates staging record to Fixed on success

---

### Critical Implementation Fixes (Must Address Before Deploy)

From the Gap Analysis, these **must** be resolved regardless of which option you choose:

**1. Fix `logException` Routing (Issue #1 — HIGH RISK)**
- Rename `logExceptionDirect()` to make it clear it's not rollback-safe
- Route all IP2/IP3 Catch blocks to `logExceptionViaEvent()` only
- **Why:** Otherwise exception logs will silently disappear (the bug you're trying to fix)

**2. Lock IP3 Placement at Level 0 in IP2 (Issue #2 — HIGH RISK)**
- Place `AddTaxNetworkLogicFromDelg` at **top-level (level 0)**, not inside `ExistingPrimaryPractice` conditional
- **Why:** If inside conditional, IP3 won't run when condition is false → no network records created, no error

**3. Widen Try/Catch in IP2 to Seq 1 (Issue #5 — MEDIUM RISK)**
- Wrap **all steps from seq 1 onward**, not just seq 4+ (ExistingPrimaryPractice block)
- **Why:** Steps 1-3 can fail and leave orphaned records with no exception log

**4. Add Processing Status Field (Gap Improvement #1)**
- `PRM_AsyncProcessingStatus__c` on CaseDataManager
- Set by Container (→ Processing), IP2 (→ Processing), IP3 (→ Completed or → Failed)
- **Why:** Without this, users have no way to check if async work finished

**5. Audit IP3 Inputs Before `sendOnlyAdditionalInput: true` (Issue #6)**
- Verify IP3 doesn't read any fields beyond the 6 explicitly listed in `additionalInput`
- **Why:** Missing fields will be null → silent data loss or validation failures

**6. Define Sandbox Test Strategy (Issue #4)**
- Manual integration test in full sandbox (not Developer edition)
- **Why:** Queueable chaining doesn't fire in `Test.startTest()/stopTest()`

**7. Scope Retry Mechanism (Issue #7 — HIGH PRIORITY)**
- Create follow-on user story for Quick Action or OmniScript button
- Link it to Phase 2 roadmap
- **Why:** Without retry, partial failures still require 2-3 hours manual work

---

## Summary Table: What Each Option Delivers

| Requirement | Current State | Option A (User Story Only) | Option B (New TDD) |
|-------------|---------------|---------------------------|-------------------|
| **Governor limits resolved** | ❌ Hitting limits | ✅ Fixed | ✅ Fixed |
| **UI response time** | 5+ min freeze | 2-4 min wait | < 3 sec ✅ |
| **Silent failures eliminated** | ❌ No logs | ✅ Exception logs | ✅ Exception logs + staging |
| **User notification** | ❌ None | ❌ None | ✅ Email + banner |
| **Progress visibility** | ❌ None | ⚠️ Static flag | ✅ Live status |
| **Failed record queue** | ❌ None | ❌ None | ✅ Staging object |
| **Partial-success handling** | ❌ All-or-nothing | ❌ All-or-nothing | ✅ Partial DML + staging |
| **Retry mechanism** | ❌ Manual (2-3 hrs) | ❌ Manual (from logs) | ⚠️ Manual (Phase 1) → ✅ Automated (Phase 2) |
| **Duplicate prevention** | ❌ None | ❌ None | ✅ While In Progress |
| **Implementation time** | Current: broken | ~7-9 days | ~3-4 weeks |
| **Meets original acceptance criteria** | ❌ No | ⚠️ Partially | ✅ Yes |

---

## Final Answer

**Does the new TDD fix the problem?**

**YES — the new TDD (your PDF document) comprehensively addresses the performance issue:**

1. ✅ **Solves governor limits** (primary technical blocker)
2. ✅ **Delivers the UX that users need** (< 3s response, notifications, progress)
3. ✅ **Eliminates silent failures** (exception logging + staging queue)
4. ✅ **Prepares for automated retry** (staging object is foundation)
5. ✅ **Reusable pattern** (can apply to Issues #2-#5 in performance analysis)

**The current implementation user story (queueable refactor only) fixes the immediate production crash but leaves major UX and operational gaps unresolved.**

### Recommended Path Forward

1. **Adopt the new TDD design** (Option B)
2. **Implement in 2 phases**: Core performance + staging (Sprint 1-2) → Retry mechanism (Sprint 3)
3. **Address the 7 critical fixes** from Gap Analysis before any deployment
4. **Manual test strategy** for Queueable chain validation (sandbox limitation)
5. **Create follow-on story immediately** for retry mechanism (don't defer past Phase 2)

This gives you a production-ready solution that stops the crashes AND meets the original business requirements for user experience and operational visibility.
