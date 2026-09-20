# USER STORY: Mass Upload — Intake: Import — Delegated Practitioner

**Persona:** PDM Specialist
**Priority:** P1
**GUS Requirement:** #1488089 — *Mass Upload - Intake: Import - Delegated Practitioner* (Proposed) · Area: IHG\BTS EIM\Provider Network Management\Mass Updates
**OmniScript:** N/A — Mass Upload is an LWC experience
**Integration Procedures:** N/A
**Architecture source:** the PRM async framework in `pkothapalli/IBXEnhancements` — `PRM_CSVConversionBatch`, `PRM_CSVJobCreationQueueable`, `PRM_JsonJobUploadService`, `PRM_AsyncOrchestrator`, `PRM_AsyncJob__c` / `PRM_AsyncJobRecords__c` / `PRM_AsyncJobDetails__c` / `PRM_AsyncJobConfig__mdt` / `PRM_AsyncJobSetting__mdt`
**Relevant Requirements:** #1486103 (*Initial Validation*), #1487020 (*API Validation*), #1487028 (*System Validation*), #1490648 (*Add Location / All Location*) — all run **before** this story; `docs/implementation-plan/Epic_C_Async_Framework.md`
**Story boundary:** the validation stories decide which practitioners are eligible. **This story packs the eligible ones into payloads and creates one Queued Async Job per payload — and deliberately stops there**, so nothing in the practitioner graph is written until the specialist confirms.

---

## Story

**As a** PDM Specialist,
**I want** the validated practitioners in my uploaded file converted into Async Jobs I can review before anything runs,
**So that** a large roster is processed in manageable jobs and nothing is written to the practitioner graph until I confirm the conversion.

**Why it matters:** A delegated roster can carry several hundred practitioners across thousands of rows. Creating all of them in one transaction exceeds the async governor budget, and creating them without a review checkpoint means a bad file is only discovered after the provider graph has already been written.

---

## Scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Upload — Delegated Practitioner | CSV upload experience | Validation → **Conversion & Import (payloads + Queued Async Jobs)** → *specialist review* → manual launch | Validated rows from the upload |

**In scope:** grouping validated rows into one practitioner each; packing practitioners into payloads on configured thresholds; creating one Queued Async Job per payload with its payload file, per–Case Manager job records and sequenced step records; per-payload failure isolation; the review-then-launch checkpoint.

**Out of scope:** the validation that precedes this; the batch execution that follows a manual launch (Epic C/E); retry of a launched job; the practitioner graph itself.

---

## Current State (from the architecture repo)

**Most of this story is already built.** The three-tier conversion pipeline exists and implements the majority of the acceptance criteria; the work is closing two concrete defects and confirming the review gate.

| Tier | Component | What it does |
|---|---|---|
| Tier 1 | `prmCsvJobUpload` → `PRM_CSVJobUploadController.saveShard` | The LWC splits the CSV into line-aligned shards client-side (`PRM_CsvShardMaxBytes__c`) and persists each as a ContentVersion |
| Tier 2 | `PRM_CSVConversionBatch` | One shard per execute (fresh governor budget). Accumulates every data row into a **stateful Map keyed by the mapper's grouping key** (Provider NPI), so aggregation is independent of shard order — a practitioner whose rows span shards is still emitted once |
| Tier 3 | `PRM_CSVConversionBatch.finish()` | Builds one practitioner per key in first-seen order, groups them into canonical `{ messageHeader, practitioners[] }` payloads on the configured **byte and count thresholds**, persists each payload as a temp ContentVersion (one DML row per payload), then enqueues the job-creation chain |
| Job creation | `PRM_CSVJobCreationQueueable` | **One payload per transaction**, chaining itself for the next. Deletes the temp payload file. On failure, logs to `PRM_ExceptionLogger` + `PRM_FailedRecordStaging__c` and **still chains**, so one bad payload does not stop the rest |
| Per job | `PRM_JsonJobUploadService.createJob` | Runs `PRM_CaseService` (E1) to create the Case Managers, inserts `PRM_AsyncJob__c` (Status `Queued`, Sub Type `Delegated`), attaches the payload as a ContentVersion, seeds one `PRM_AsyncJobRecords__c` per Case Manager, then hands the job to the orchestrator |
| Step records | `PRM_AsyncOrchestrator.createDetails` | Inserts one `PRM_AsyncJobDetails__c` per `PRM_AsyncJobConfig__mdt` step for the job's process and sub-type, ordered by sequence |
| Review gate | `PRM_CSVJobUploadController.getPendingJobs` / `startPractitionerCreation` | "Conversion only GENERATES the jobs (Queued, deferred); the user then reviews them and manually launches the practitioner-creation chain — a review-then-launch checkpoint" |

**Configuration** (`PRM_AsyncJobSetting__mdt`): `PRM_CsvShardMaxBytes__c`, `PRM_CsvConversionBatchSize__c`, `PRM_MaxPractitionersPerJob__c`, `PRM_MaxPayloadFileBytes__c`, `PRM_RetentionDays__c`.

### Two defects this story must close

**Defect 1 — the job-creation path does not compile.** `PRM_CSVJobCreationQueueable` line 42 calls:

```apex
new PRM_JsonJobUploadService().intakeDeferred(payload, PRM_Constants.PROCESS_PRACTITIONER_CREATION, partName);
```

`PRM_JsonJobUploadService` defines only `process(jsonBody, templateKey, fileName)` and a four-argument overload. **`intakeDeferred` is defined nowhere in the repository** — only referenced in the call and in three doc comments. As committed on `main`, the CSV import path has a broken reference.

**Defect 2 — the obvious fix would break the review gate.** Simply re-pointing that call at `process` would auto-start processing, because `createJob` ends with:

```apex
new PRM_AsyncOrchestrator().start(asyncJob.Id);   // start() = createDetails() + findNextJob()
```

`findNextJob` dispatches the first batch step. That directly violates the requirement that nothing runs until the specialist asks. The deferred variant must call the **already-public** `PRM_AsyncOrchestrator.createDetails(jobId)` and stop there.

**Defect 3 — a failed payload orphans its temp file.** In `PRM_CSVJobCreationQueueable.execute`, `deleteTempPayload` sits inside the `try` *after* the job-creation call, so an exception skips it and the temp ContentVersion is left behind — which AC-11 explicitly forbids.

---

## Acceptance Criteria

> Pattern A (behavioural) unless marked. AC-6 is Pattern E (records created per job); AC-5 and AC-12 are Pattern D (rules).

### Eligibility and the review gate

**AC-1 — Jobs are created only from practitioners that passed validation**

**Given** a file whose mapped rows have completed practitioner, group and address field validation, Initial Validation, and the in-scope registry and address-standardization steps,
**When** conversion and job creation run,
**Then** Async Jobs are created only from practitioners that passed every one of those steps.

**AC-2 — A row that failed validation never becomes a job**

**Given** a file in which some rows failed validation and others passed,
**When** conversion and job creation run,
**Then** no Async Job, job record, step record or work item is created for a failed row,
**And** the practitioners that passed still produce jobs.

**AC-3 — Conversion does not start until the submitter asks**

**Given** a mapped file that has passed validation,
**When** the submitter has not yet started processing,
**Then** no conversion runs, no payload is assembled, and no Async Job is created.

**AC-4 — One practitioner in the file becomes one practitioner in one job**

**Given** validated rows that share an Individual NPI across one or more rows, including rows that fall in different parts of the file,
**When** conversion runs,
**Then** those rows are grouped into a single practitioner in the payload,
**And** that practitioner appears in exactly one Async Job,
**And** grouping does not depend on the rows being adjacent or on the order the file is processed in.

### Payload packing

**AC-5 — How practitioners are packed into payloads** *(Pattern D — rules)*

- Practitioners are packed in **first-seen order** from the file.
- A payload closes when it reaches **either** the configured maximum practitioners per job **or** the configured maximum payload size in bytes, whichever comes first.
- Both thresholds are configuration, not code, and are changeable without a deployment.
- **A practitioner is never split across payloads** — all of a practitioner's locations travel together in one payload.
- Each payload is a complete canonical envelope carrying its own header and only its own practitioners.
- A file that yields fewer practitioners than the threshold produces exactly one payload.

### Job creation

**AC-6 — Records created for each payload** *(Pattern E)*

**Given** a payload assembled from validated practitioners,
**When** job creation runs for that payload,
**Then** the following records are created exactly as specified, in this order:

**Case Manager set — Create (one set per practitioner in the payload)**

| Field | Value | Notes |
|---|---|---|
| — | one Account, Case, Case Manager and practitioner Case Manager Association per practitioner | Created by the existing Case Manager service; its per-field recipe is owned by that service's specification, not redefined here |

**Async Job — Create (one per payload)**

| Field | Value | Notes |
|---|---|---|
| Process Name | Practitioner Creation | |
| Sub Type | Delegated | blank is treated as Delegated by the orchestrator; the upload sets it explicitly |
| Status | Queued | **not dispatched** — see AC-7 |

**Payload File — Create (one per Async Job)**

| Field | Value | Notes |
|---|---|---|
| Content | {The payload envelope for this job} | the orchestrator reads the payload from this file |
| Title | {Source file name} [part {n}] | identifies which part of the upload produced this job |
| Linked to | {Async Job} | |

**Async Job Record — Create (one per Case Manager in the payload)**

| Field | Value | Notes |
|---|---|---|
| Async Job | {Async Job} | master-detail |
| Case Manager | {Case Manager for that practitioner} | the correlation the progress view and fallout join on |

**Async Job Detail — Create (one per configured step, in sequence)**

| Field | Value | Notes |
|---|---|---|
| Async Job | {Async Job} | master-detail |
| Process Name | Practitioner Creation | |
| Mode | {Configured dispatch mode for the step} | |
| Batch Size | {Configured batch size for the step} | |
| Sequence | {Configured step sequence} | drives ordering and halt-on-failure |
| Status | Queued | |
| Retry Count | 0 | |

**And** the temp payload file used to carry the payload between conversion and job creation is removed once the job exists.

**AC-7 — Jobs are created Queued and are not dispatched**

**Given** job creation has completed for every payload,
**When** the specialist views the generated jobs,
**Then** every job is Queued with its step records created but none started,
**And** no batch step has run,
**And** nothing has been written to the practitioner graph beyond the Case Managers.

**AC-8 — The specialist reviews and launches**

**Given** a set of Queued jobs generated from an upload,
**When** the specialist selects jobs and starts processing,
**Then** only the selected jobs begin their step chain,
**And** jobs that were not selected remain Queued and untouched.

### Resilience

**AC-9 — One payload is created per transaction**

**Given** a file that produced several payloads,
**When** job creation runs,
**Then** each payload's job is created in its own transaction,
**And** no single transaction exceeds the async governor budget regardless of how many payloads the file produced.

**AC-10 — One payload failing job creation does not stop the others**

**Given** conversion produced several payloads and creating the job for one of them fails,
**When** job creation continues,
**Then** the failed payload is recorded as a failure with its error detail,
**And** the remaining payloads still become Async Jobs.

**AC-11 — A failed payload leaves nothing orphaned**

**Given** job creation failed for a payload,
**When** the failure is recorded,
**Then** that payload's temp file is removed rather than left behind,
**And** no partially-created Async Job remains for that payload,
**And** the specialist can see which practitioners were affected.

**AC-12 — Governor and ordering rules** *(Pattern D — rules)*

- **Conversion reads one shard per execute**, so parsing a large file never exhausts a single transaction's budget.
- **Practitioner aggregation is order-independent** — rows are collected by grouping key, not by position, so shard order and execute order cannot split a practitioner (AC-4).
- **Payload assembly writes one row per payload**, never one per practitioner.
- **Job creation is one payload per transaction** (AC-9), because creating the Case Managers for every payload in a single transaction would exceed the async DML and SOQL limits.
- **Job creation never dispatches** — it creates the step records and stops (AC-7).
- **A failure in one payload is contained**: it is logged, its temp file removed, and the chain continues (AC-10, AC-11).

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_JsonJobUploadService` | Modified Apex class | **Add the missing `intakeDeferred(payload, templateKey, fileName)`** — same as `createJob` but calling `PRM_AsyncOrchestrator.createDetails(jobId)` instead of `start(jobId)`, so the job is left Queued with step records and is never dispatched | Closes Defect 1 and 2. Drives AC-6, AC-7. `createDetails` is already public |
| `PRM_CSVJobCreationQueueable` | Modified Apex class | Move `deleteTempPayload` into a `finally` so a job-creation exception cannot orphan the temp file; record the affected part in the failure detail | Closes Defect 3. Drives AC-10, AC-11 |
| `PRM_CSVConversionBatch` | Existing | Tier-2 keyed aggregation and Tier-3 payload packing already implement AC-4 and AC-5 | Verify thresholds are honoured, no change expected |
| `PRM_AsyncOrchestrator` | Existing | `createDetails` used standalone by the deferred path; `start` remains for the manual launch | Implements AC-6's step records |
| `PRM_CSVJobUploadController` | Existing | `getPendingJobs` + `startPractitionerCreation` provide the review-then-launch gate | Implements AC-3, AC-8 |
| `PRM_AsyncJobSetting__mdt` | Config | `PRM_MaxPractitionersPerJob__c` and `PRM_MaxPayloadFileBytes__c` drive packing; confirm seeded values | Drives AC-5 |
| `PRM_AsyncJobConfig__mdt` | Config | One row per batch step for Practitioner Creation / Delegated; step records are created from these | Drives AC-6 |
| `prmCsvJobUpload` | Existing LWC | Shows generated jobs and the launch action | Implements AC-8 |
| `PRM_FailedRecordStaging__c` + `PRM_ExceptionLogger` | Existing | Per-payload failure capture | Implements AC-10 |

**Object mapping for the Pattern E block:** Async Job = `PRM_AsyncJob__c` (`PRM_ProcessName__c`, `PRM_SubType__c`, `PRM_Status__c`); Payload File = `ContentVersion` linked to the job; Async Job Record = `PRM_AsyncJobRecords__c` (`PRM_AsyncJob__c`, `PRM_CaseManager__c` → `IndividualApplication`); Async Job Detail = `PRM_AsyncJobDetails__c` (`PRM_AsyncJob__c`, `PRM_ProcessName__c`, `PRM_Mode__c`, `PRM_BatchSize__c`, `PRM_Sequence__c`, `PRM_Status__c`, `PRM_RetryCount__c`); Case Manager = `IndividualApplication` with `Account`, `Case` and `PRM_CaseManagerAssociation__c`, created by `PRM_CaseService`.

---

## Definition of done

- [ ] `PRM_CSVJobCreationQueueable` compiles against a real `intakeDeferred` method and the CSV import path deploys
- [ ] A converted file produces jobs that are Queued with step records created and **no batch step started** (AC-7)
- [ ] Nothing beyond the Case Managers is written to the practitioner graph before a manual launch (AC-7)
- [ ] Selecting a subset of jobs launches only those; the rest stay Queued (AC-8)
- [ ] A practitioner whose rows are split across shards and appear out of order still produces exactly one practitioner in exactly one job (AC-4)
- [ ] A file that exceeds the practitioner-per-job threshold produces multiple payloads, and no practitioner is split across them (AC-5)
- [ ] Each Async Job carries its payload file, one job record per Case Manager, and one step record per configured step in sequence (AC-6)
- [ ] Each payload's job is created in its own transaction; a file producing many payloads never exceeds the async limits (AC-9)
- [ ] Forcing a failure on one payload leaves the other payloads' jobs created and the failure recorded (AC-10)
- [ ] After a forced failure, no temp payload file and no partial Async Job remain (AC-11)
- [ ] A file whose rows all fail validation produces no jobs at all (AC-2)
- [ ] Packing thresholds are changed in configuration and take effect without a deployment (AC-5)
- [ ] ≥ 85% Apex coverage on the changed service and queueable, including the failure path, the multi-payload path and the deferred (non-dispatch) assertion

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Was `intakeDeferred` removed in a merge, or never written? If an earlier version exists, it should be recovered rather than rewritten. | Determines whether this is a restore or new work | Technical |
| 2 | Case Managers are created at **job creation**, before the specialist launches. Is that acceptable, or should they too be deferred until launch? | AC-7 currently allows Case Manager creation pre-launch; deferring it would be a larger architectural change | BA / Technical |
| 3 | What are the intended seeded values for maximum practitioners per job and maximum payload bytes? | Determines how many jobs a typical roster produces | Product / Technical |
| 4 | If a specialist never launches the generated jobs, how long do they and their payload files persist before cleanup? | Interacts with the retention setting and the cleanup batch | Product |
| 5 | Should a failed payload be re-creatable from the upload without re-running the whole file? | Decides whether AC-11 needs a recovery path | Product / BA |
| 6 | Should jobs generated from one upload be visibly grouped, so a specialist can launch "all jobs from this file" in one action? | Affects the review surface in AC-8 | Product |
| 7 | The grouping key is the Individual NPI. For an IBC row with no NPI, what key groups the practitioner? | AC-4 depends on a grouping key existing for every row | Technical / BA |
| 8 | Should conversion be blocked entirely when any row failed validation, or proceed with the passing rows as AC-2 describes? | Confirms partial processing at the import stage | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_JsonJobUploadService` | Apex | **HIGH** | New deferred entry point; the existing `process` path is shared with the JSON upload and must not regress |
| `PRM_CSVJobCreationQueueable` | Apex | **MEDIUM** | Failure-path change to guarantee cleanup |
| `PRM_AsyncOrchestrator` | Apex | LOW | `createDetails` used standalone; no change |
| `PRM_CSVConversionBatch` | Apex | LOW | Already implements packing and aggregation |
| `PRM_AsyncJobSetting__mdt` / `PRM_AsyncJobConfig__mdt` | Config | MEDIUM | Packing thresholds and step rows must be seeded for Practitioner Creation / Delegated |
| Preceding validation stories | Requirements | **HIGH** | This story consumes their eligibility outcome |
| Epic C batch execution | Apex | MEDIUM | Consumes the jobs this story leaves Queued |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_JsonJobUploadService.intakeDeferred` | Modified Apex | **L** | Mirrors `createJob` but stops at `createDetails` |
| `PRM_CSVJobCreationQueueable` cleanup guarantee | Modified Apex | **M** | `finally` block plus richer failure detail |
| Configuration seeding and verification | Config | **S** | Thresholds and step rows |
| Verification of packing and aggregation | Test / analysis | **M** | Confirm AC-4 and AC-5 hold on a real multi-shard roster |
| Apex tests | New tests | **L** | Deferred (non-dispatch) assertion, multi-payload, forced failure, no-orphan |

**Total Estimated Effort:** ~3–4 engineer-days — **L** overall. Small because the architecture already implements most of the requirement; the work is closing the broken reference, preserving the review gate, and guaranteeing cleanup.
