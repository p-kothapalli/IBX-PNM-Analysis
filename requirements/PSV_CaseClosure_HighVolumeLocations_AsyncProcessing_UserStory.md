# USER STORY 5: PSV Case Closure — Process High-Volume Practice Location Sets Asynchronously

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScript:** `PRM_PrimarySourceVerificationReview_English` (PSV review — case closure), `PRM_RecredQC_English` (re-cred QC routing that follows)
**Integration Procedures:** `PRM_ReviewPSVCaseRecordsUpdate_Procedure` (v27, active)
**Relevant Requirements:** `requirements/primarysourceverification/SOLUTION_SUMMARY.md`, `README.md`, `Integration_Procedure_Modifications.md`, draft `PracticeLocationBatchProcessor.apex` (all dated 2026-04-09, **never deployed**); `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §4 P3; **complements** `PSV_ServiceAreaVerification_CAQHBulkLocation_DataMapper_BugFix_UserStory.md` (different bottleneck — see Scope)

---

## Story

**As a** Credentialing Specialist,
**I want** to close a Primary Source Verification review for a practitioner with a large number of practice locations without the submission timing out,
**So that** high-volume providers can be credentialed through the guided flow instead of being routed to a manual email process.

**Why it matters:** This is the original reason the business stopped using the PSV route to add locations for re-credentialing. When a practitioner has roughly 100 or more practice locations, closing the PSV case exceeds platform processing limits and the submission fails — losing the specialist's work and leaving the case stuck. A designed fix has existed in the requirements folder since April 2026 but **was never built or deployed**, so every high-volume provider still has to be handled by email. Until this ships, re-enabling the re-cred location route at volume is not safe.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Primary Source Verification (PSV) — case closure | `PRM_PrimarySourceVerificationReview_English` | Submit / close case | `PRM_ReviewPSVCaseRecordsUpdate` — creates practice locations, addresses, and practitioner-at-location affiliations |

**In scope:** the case-closure record creation path when the practice-location count is large; job status visibility; recovery when the background work fails.

**Explicitly out of scope — and NOT the same defect:** the mid-flow **Service Area Verification display/transform** bottleneck documented in `PSV_ServiceAreaVerification_CAQHBulkLocation_DataMapper_BugFix_UserStory.md`. That story addresses a transform cross-join that fails **while the screen loads**, at roughly 115 locations. This story addresses the **case-closure record creation** that fails later and independently. Both are triggered by high CAQH location counts and both must ship for a high-volume provider to get all the way through, but they are different code paths and neither fixes the other.

---

## Current State (from codebase)

### Case closure creates all records synchronously

Practice locations, location addresses, and practitioner-at-location affiliations are all created inside the single case-closure transaction. The referenced design notes identify the affiliation creation step as the heaviest part of that work.

- **Location:** `force-app/main/default/omniIntegrationProcedures/PRM_ReviewPSVCaseRecordsUpdate_Procedure_27.oip-meta.xml`

### The designed fix was never deployed

None of the designed components exist in the deployable source tree:

| Designed component | Present in `force-app`? |
|---|---|
| `PracticeLocationBatchProcessor` (Apex) | **Absent** |
| `PRM_ProcessPracticeLocationsAsync` (Integration Procedure) | **Absent** |
| `PRM_PracticeLocationProcessingStatus__c` and its sibling tracking fields on the Case Manager | **Absent** |

The design's own implementation checklist in `requirements/primarysourceverification/README.md` is entirely unchecked (create fields, deploy Apex, modify IP, create IP, test, deploy to production).

### Existing async framework to reuse

The org already has established asynchronous patterns and an exception-logging utility that this work should reuse rather than reinvent (see Technical Implementation).

---

## Acceptance Criteria

**AC-1 — Low-volume cases still close immediately**

**Given** a Credentialing Specialist is closing a PSV review for a practitioner with a small number of practice locations,
**When** they submit the case closure,
**Then** all practice locations, addresses and affiliations are created within the submission as they are today,
**And** the specialist sees the same immediate confirmation they see today,
**And** the case moves to the next stage without any change in behaviour.

**AC-2 — High-volume cases are accepted immediately and completed in the background**

**Given** a Credentialing Specialist is closing a PSV review for a practitioner with a large number of practice locations,
**When** they submit the case closure,
**Then** the submission is accepted without a timeout or error,
**And** the specialist is told the location processing is continuing in the background,
**And** the remaining locations, addresses and affiliations are created in batches until all are complete.

**AC-3 — Case Manager shows the processing status**

**Given** a high-volume case closure is being processed in the background,
**When** a Credentialing Specialist views the Case Manager,
**Then** they can see whether location processing is in progress, complete, or failed,
**And** they can see when it started and when it finished,
**And** if it failed they can see the reason.

**AC-4 — Records created for a high-volume case match a low-volume case**

**Given** a high-volume PSV case closure has finished processing in the background,
**When** a Credentialing Specialist reviews the practitioner's locations,
**Then** the following records exist for **every** practice location submitted:

**Practice Location — Create (one per submitted location)**

| Field | Value | Notes |
|---|---|---|
| Name | {location name from the submission} | |
| Account | {group / vendor account} | lookup |
| Location | {linked location record} | lookup |
| Active | TRUE | |
| Pending | FALSE | |
| Case Manager | {this case's Case Manager} | |

**Location Address — Create (one per submitted location)**

| Field | Value | Notes |
|---|---|---|
| Address | {address from the submission} | street, city, state, postal code |
| Location | {the practice location's linked location} | lookup |
| Active | TRUE | |

**Practitioner-to-Practice-Location affiliation — Create (one per submitted location)**

| Field | Value | Notes |
|---|---|---|
| Practitioner | {the practitioner on the case} | |
| Practice Location | {the created practice location} | |
| Effective From | {effective date from the submission} | |
| Effective To | {empty} | not terminated at creation |
| Active | TRUE | |
| Pending | FALSE | |
| Case Manager | {this case's Case Manager} | |

**And** no duplicate practice location, address, or affiliation is created for any submitted location.

**AC-5 — Re-running a partly processed case does not duplicate records**

**Given** a high-volume case closure failed partway through after creating some locations,
**When** the processing is retried,
**Then** the locations already created are not created again,
**And** only the outstanding locations are processed,
**And** the case reaches a complete processing status.

**AC-6 — Failure is visible and recoverable, not silent**

**Given** background location processing fails for a high-volume case,
**When** the failure occurs,
**Then** the Case Manager shows a failed processing status with the reason,
**And** the failure is logged for support to investigate,
**And** the case is not left appearing successfully closed with locations missing,
**And** a Credentialing Specialist or support user can retry the processing without re-entering the review.

**AC-7 — Stalled processing is detectable**

**Given** a case has been showing in-progress location processing for an unusually long time,
**When** support reviews outstanding processing,
**Then** the stalled case is identifiable by its processing status and start time,
**And** it can be retried.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PracticeLocationProcessingStatus__c` + start / completed / error tracking fields | New custom fields on `IndividualApplication` | Track background processing state, timestamps, and failure reason | Drives AC-3, AC-6, AC-7 |
| `PracticeLocationBatchProcessor` (or a `PRM_`-prefixed equivalent) | New Apex Queueable/Batchable | Chunked creation of practice locations, location addresses and practitioner-at-location affiliations; idempotent via external-id upserts | Drives AC-2, AC-4, AC-5 |
| `PRM_ProcessPracticeLocationsAsync` | New Integration Procedure | Hand the location payload to the async processor | Drives AC-2 |
| `PRM_ReviewPSVCaseRecordsUpdate_Procedure` | New IP version | Branch on location count: below the threshold process synchronously (unchanged), at or above it enqueue the async job | Drives AC-1, AC-2 |
| External Id fields for idempotency | New / verify custom fields | Location, address and affiliation external ids so a retry upserts rather than duplicates | Drives AC-5 |
| `PRM_ExceptionLogger` | Reuse | Log failures through the org's existing logger — do not build a new one | Drives AC-6 |
| Retry entry point | New Apex-invocable action or admin action | Allow reprocessing an outstanding or failed case | Drives AC-5, AC-6, AC-7 |

**Naming note:** the draft class in `requirements/primarysourceverification/` is named `PracticeLocationBatchProcessor` without the org's `PRM_` prefix. It should be renamed to follow convention before deployment (see Clarification 4).

**Threshold and batch size:** the April design proposes a threshold of 20 locations and a batch size of 50. Both should be confirmed against the ~115-location cliff measured in the sibling Service Area Verification story (see Clarification 1).

---

## Definition of done

- [ ] AC-1 verified: a low-volume case closes synchronously with unchanged behaviour and timing
- [ ] AC-2 verified with a provider carrying **100+** practice locations: submission is accepted and all locations are eventually created
- [ ] AC-3 verified: processing status, start time, completion time and error reason are all visible on the Case Manager
- [ ] AC-4 verified by record count and field inspection: a high-volume case produces the same records as a low-volume case, with no duplicates
- [ ] AC-5 verified by deliberately failing mid-run and retrying: no duplicate records created
- [ ] AC-6 verified: an induced failure surfaces on the Case Manager and in the exception log, and is retryable
- [ ] AC-7 verified: a stalled in-progress case is identifiable and retryable
- [ ] ≥ 85% Apex coverage on the new processor including bulk (200+), single, empty and negative/failure paths
- [ ] New fields deployed with field-level access applied to the Credentialing and PDA permission sets
- [ ] No regression to the Service Area Verification step, the re-cred QC routing that follows PSV closure, or the PDA lane
- [ ] Reconciled with `PSV_ServiceAreaVerification_CAQHBulkLocation_DataMapper_BugFix_UserStory.md` — both paths proven on the same high-volume provider

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Is the April design's threshold of 20 locations and batch size of 50 still right, given the measured failure cliff is around 115 locations in the sibling story? | A threshold of 20 sends many ordinary cases down the async path unnecessarily, changing the specialist experience for the majority | Technical / BA |
| 2 | Should the specialist be **blocked** from advancing the case until background processing completes, or may the case proceed while locations are still being created? | Determines whether downstream QC can start on an incomplete location set | BA / Product |
| 3 | Who monitors and retries failed or stalled processing — the Credentialing Specialist, PDM, or support? | Determines whether the retry entry point needs a user-facing button or an admin-only action | Ops / Product |
| 4 | Confirm the class is renamed to the `PRM_` convention before deployment, and confirm the required external-id fields exist. | Off-convention naming and missing external ids both block the idempotency requirement in AC-5 | Technical |
| 5 | Does this story ship before, with, or after the Service Area Verification transform fix? | A high-volume provider cannot complete PSV until **both** are live; shipping one alone does not restore the route | Product |
| 6 | Should the re-cred location route be re-enabled for the business as part of this story, or held until the PDA removal defects (US-1, US-2) also ship? | Determines the release gate and the communication to the Credentialing team | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_ReviewPSVCaseRecordsUpdate` | Integration Procedure | **HIGH** | Case-closure path branches on volume |
| New async processor | Apex | **HIGH** | Net-new component creating provider records at volume |
| `IndividualApplication` | Object | MEDIUM | New tracking fields plus field-level access |
| `PRM_PrimarySourceVerificationReview_English` | OmniScript | MEDIUM | Closure confirmation messaging changes for the async path |
| Re-cred QC / PDA lane | Downstream flows | MEDIUM | May start while locations are still being created (Clarification 2) |
| Provider directory | Data | **HIGH** | Missing or duplicated locations directly affect the directory |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Tracking fields on the Case Manager | Custom fields + FLS | **M** | Four fields plus permission sets |
| Async processor | New Apex | **XL** | Chunked, idempotent, restartable |
| `PRM_ProcessPracticeLocationsAsync` | New IP | **L** | Payload hand-off |
| `PRM_ReviewPSVCaseRecordsUpdate` volume branch | Modified IP | **L** | Threshold branch, new version |
| External-id fields for idempotency | Custom fields | **M** | Three objects |
| Retry entry point | New Apex / action | **L** | |
| Apex tests to ≥85% incl. bulk + failure | Apex tests | **XL** | Bulk and mid-run failure paths |
| High-volume test data + regression | QA | **XL** | Needs a 100+ location provider in QA |

**Total Estimated Effort:** **XXL** (roughly 5–8 days) — AI-estimated, validate with team.
