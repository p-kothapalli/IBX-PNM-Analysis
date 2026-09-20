# Epic C — Comprehensive Execution Plan (for review)

> **STATUS: PROPOSAL — awaiting review. No components, code, scripts, configuration, commands, or other implementation artifacts have been or will be generated until this plan is reviewed and the Open Questions (§7) are answered.**
>
> **Source of truth:** `Epic_C_Async_Framework.md` (C0–C11). This plan restates and expands only what that guide explicitly defines; the design decisions are recorded in its **Validation log §C11 (F-1…F-21)**. Anything not stated is **UNKNOWN** and surfaced as an Open Question — not assumed.
>
> **Tags:** **[CONFIRMED]** (documented), **[OPEN]** (needs a decision), **[RISK]**, **[RECOMMENDATION]**. Tasks blocked by an unresolved [OPEN] item are **⛔ Pending Clarification**.

---

## 1. Confirmed requirements (extracted from Epic C)

### 1.1 Scope & components
- **[CONFIRMED]** Epic C builds the **metadata-driven async execution framework** behind the OmniStudio path. Deliverables: C1 config + Custom Notification Type, C2 `start()` kickoff, C3 `PRM_AsyncOrchestrator`, C4 batch-class **contract** (classes themselves are EPIC E), C5 `prmAsyncJobProgress` LWC + controller, C6 cleanup batch + retention CMDT + scheduler. **C6b sweeper is deferred to a future enhancement (OQ-C6) — not in pilot scope.**
- **[CONFIRMED]** **No dispatch trigger** (Pattern A, F-1): the EPIC F intake wrapper calls `PRM_AsyncOrchestrator.start(jobId)` as its last step, after the unit of work commits.
- **[CONFIRMED]** Execution model: 1 `PRM_AsyncJob__c` per submission; `PRM_AsyncJobDetails__c` = one per MDT step (M-D child of the Job); `PRM_AsyncJobRecords__c` = per Case Manager (sibling child). The orchestrator chains the step-details by `PRM_Sequence__c`, **halt-on-failure**; each step's batch processes all Case Managers (F-2/F-3).
- **[CONFIRMED]** `PRM_AsyncOrchestrator` surface: `start` · `createDetails` · `findNextJob` · `invokeJob` · `statusUpdate` · `retry` · `jsonFileParser` · `logFailure` · `notifyOnFinish` + private helpers (`configForStep`, `recipientFor`, `isFlexQueueNearCap`, `payloadTitle`) (C3).
- **[CONFIRMED]** `invokeJob` resolves the **named batch class** via `Type.forName(cfg.PRM_ServiceClassName__c)` → `Database.executeBatch`; sets the job `Running` on first dispatch; dispatches **directly** (no flex-queue depth-guard for the pilot — a full Flex Queue surfaces as a retryable step failure) (F-4/F-5/F-6).
- **[CONFIRMED]** Failure handling: any step failure → step `Failed` → **job `Failed`**, chain halts, **no notification** (F-15a). `logFailure` writes `PRM_ExceptionLogger` + a `PRM_FailedRecordStaging__c` DLQ row **linked to the step-detail** (no `PRM_CaseManager__c`).
- **[CONFIRMED]** `notifyOnFinish` is **success-only**, to the **submitter** (`CreatedById`), via the existing `PRM_NotificationHelper` (F-11).
- **[CONFIRMED]** `retry` (manual, uncapped, LWC, **per-row only — no bulk**) resets the failed step + job and re-dispatches the **whole failed batch step** (idempotent re-run) (F-9/F-10).
- **[CONFIRMED]** `jsonFileParser` reads the **single** payload `ContentVersion` by known Title; the read happens **inside the batch** (F-8/F-18).
- **[CONFIRMED]** LWC `prmAsyncJobProgress` on the `IndividualApplication` page; `getProgress(caseManagerId)` resolves Records → Job → step-details (+ DLQ linked to those steps) (C5, F-12).
- **[CONFIRMED]** C6 cleanup deletes jobs (M-D cascade removes both child objects) + payload files older than retention; retention from **`PRM_AsyncJobSetting__mdt.PRM_RetentionDays__c`** (`Default`=90, fallback 90) — CMDT built in C6 (F-20/F-21).
- **[DEFERRED]** C6b **sweeper** (`PRM_AsyncJobSweeper`) — **deferred to a future enhancement (OQ-C6); not built for the pilot.** Stranded/stuck steps are recovered **manually** via per-step Retry (C5). See F-16.

### 1.2 Conventions & reuse
- **[CONFIRMED]** `PRM_` prefix, `with sharing`, one class per file, ≥ 85% coverage, `<Class>Test` (C0).
- **[CONFIRMED]** **Reuse existing org classes** — `PRM_ExceptionLogger` (logging) and `PRM_NotificationHelper` (notifications); no new logger/notifier (C0/C3).
- **[CONFIRMED]** Custom Notification Type `PRM_AsyncJobNotification` (new declarative metadata) (C1).

### 1.3 Dependencies
- **[CONFIRMED]** **Depends on:** EPIC A (objects/config/permission set) **and** EPIC B (`PRM_ServiceBase`) merged to `main` first. **Blocks:** EPIC E (the five batch classes) and EPIC F (intake wrapper calling `start()`) (C0/C9).

### 1.4 Effort (documented)
- **[CONFIRMED]** C1 1.0 · C2 0.5 · C3 4.0 · C4 0.5 · C5 2.5 · C6 1.5 → **~10.0 engineer-days** (C7). *(C6b sweeper deferred — OQ-C6.)*

---

## 2. Constraints (documented)

- **[CONFIRMED]** Apex Batch/Queueable enqueued in a transaction runs **only post-commit** — the basis for the Pattern-A kickoff (F-1).
- **[CONFIRMED]** Flex Queue: 5 active/queued, 100 holding — **accepted trade-off**; one batch active per job (F-6).
- **[CONFIRMED]** Strict halt: one failure halts the whole job's chain (F-15a).
- **[CONFIRMED]** DLQ row links to the step-detail; `PRM_CaseManager__c` not populated.

---

## 3. Acceptance criteria (from Epic C)

- **[CONFIRMED]** Config rows + `PRM_AsyncJobNotification` deployable (C1).
- **[CONFIRMED]** Orchestrator: `start`→`createDetails`→`findNextJob` chains steps, halt-on-failure with correct job rollup; `invokeJob` resolves + dispatches the batch class; `retry` restarts the failed step; `jsonFileParser` round-trips; `logFailure` step-linked DLQ + exception log; `notifyOnFinish` success-only to submitter (C3).
- **[CONFIRMED]** C4 contract honoured by the EPIC E batches (start/execute/finish, idempotent) (C4).
- **[CONFIRMED]** LWC renders step status, **per-row** Retry restarts the failed batch step, refresh reflects new status (C5).
- **[CONFIRMED]** Cleanup purges past **configured** retention (default 90) (C6). *(Sweeper-based recovery deferred — OQ-C6; manual Retry covers it.)*
- **[CONFIRMED]** Apex ≥ 85% per class; LWC Jest; UI/E2E for the progress LWC; Test Evidence Report + human sign-off (Epic A §A7, referenced by C8/C9).

---

## 4. Phases, milestones & task breakdown

> Build order (C7): C1 → C2/C3 → C4 → C5 → C6. *(C6b sweeper deferred — OQ-C6.)* Each task: Purpose · Expected outcome · Dependencies · Prerequisites · Impacted areas · Validation · Testing · Risks · Completion.

### Phase 0 — Setup *(milestone M0)*

**T0.1 — Branch**
- Purpose: isolate Epic C work (C9). Outcome: `epic-c/*` branches per C9 cut from `main`.
- Dependencies: **EPIC A + EPIC B merged to `main`**. Prerequisites: clean `main`.
- Impacted areas: VCS. Validation: branches exist. Testing: n/a.
- Risks: **[RISK]** remote push blocked (SSH auth, prior). Completion: branches created.

**T0.2 — Confirm prerequisites ⛔ Pending Clarification (OQ-C1, OQ-C7)**
- Purpose: ensure the framework can deploy + run.
- Outcome: confirmed **target org** (OQ-C1); confirmed the existing org classes **`PRM_ExceptionLogger` + `PRM_NotificationHelper`** exist with the documented signatures (OQ-C7); EPIC A objects/permset + EPIC B `PRM_ServiceBase` present.
- Dependencies: OQ-C1, OQ-C7. Prerequisites: org access.
- Impacted areas: none (read-only). Validation: classes/objects resolve. Testing: n/a.
- Risks: **[RISK]** `PRM_NotificationHelper.sendBellNotification` signature differs → `notifyOnFinish` rework.
- Completion: all confirmed.

### Phase 1 — Config & notification (C1) *(milestone M1)*

**T1.1 — Seed `PRM_AsyncJobConfig__mdt` rows**
- Purpose: define the ordered batch pipeline (C1).
- Expected outcome: **4 records** for `Practitioner Creation` — seq 1 `PractitionerBatch`, 2 `PracticeLocationAndGroupBatch`, 4 `PLRelatedBatch`, 5 `Level4RecordCreationBatch`; **`PRM_BatchSize__c = 1`** each (OQ-C2 resolved; `GroupRelatedBatch`/seq 3 omitted — CL-15).
- Dependencies: EPIC A CMDT. Prerequisites: EPIC E class names (wired when E lands).
- Impacted areas: `customMetadata/`.
- Validation: rows deploy; query returns 4 ordered by `PRM_Sequence__c` (1,2,4,5).
- Testing: deploy + row order.
- Risks: **[RISK]** BatchSize=1 is a placeholder — re-tune via LDV before go-live (R-C9).
- Completion: 4 rows deploy.

**T1.2 — Custom Notification Type `PRM_AsyncJobNotification`**
- Purpose: the bell notification channel (C1).
- Expected outcome: `customNotificationTypes/PRM_AsyncJobNotification` — **defined in Epic C** (OQ-C3 resolved: kept here with the `notifyOnFinish` feature, not moved to Epic A).
- Dependencies: none. Prerequisites: T0.
- Impacted areas: `customNotificationTypes/`.
- Validation: deploys; visible in Setup; `PRM_NotificationHelper` resolves it by DeveloperName.
- Testing: deploy.
- Risks: low.
- Completion: type deploys.

### Phase 2 — Orchestrator + kickoff (C2 + C3) *(milestone M2)*

**T2.1 — `PRM_AsyncOrchestrator` + `start()`**
- Purpose: central controller + Pattern-A kickoff (C2/C3).
- Expected outcome: the documented method surface (§1.1) with the F-resolved behaviour (halt-on-failure → job Failed no notify; job Running on dispatch; retry resets step + job; success-only notify; step-linked DLQ).
- Dependencies: EPIC A objects + CMDT; EPIC B `PRM_ServiceBase`; reused `PRM_ExceptionLogger`/`PRM_NotificationHelper`. Prerequisites: T0, T1.
- Impacted areas: `classes/PRM_AsyncOrchestrator.cls`.
- Validation: compiles; unit tests cover chaining, halt, retry, rollup, parser, logFailure, notify.
- Testing: Apex ≥ 85% with a `@isTest` stub `Database.Batchable` (test without EPIC E) — C8.
- Risks: **[RISK]** chaining a batch from `finish()` + flex-queue interplay; **[RISK]** `Type.forName` of an EPIC-E class not yet present (use a test stub).
- Completion: class + tests green; behaviour per C3 acceptance.

### Phase 3 — Batch-class contract (C4) *(milestone M2)*

**T3.1 — Define + test the batch-class contract (classes built in EPIC E)**
- Purpose: lock the start/execute/finish + idempotency contract `PRM_AsyncOrchestrator` dispatches (C4).
- Expected outcome: a documented contract + a **test stub** batch class proving dispatch/chain/halt without EPIC E.
- Dependencies: T2.1. Prerequisites: T2.1.
- Impacted areas: test classes (the five real batches are **EPIC E**).
- Validation: stub batch resolves + runs + chains via the orchestrator.
- Testing: covered with T2.1.
- Risks: **[RISK]** the real batches (EPIC E) must honour the contract (idempotency, finish ordering F-19, JSON↔CM correlation F-14) — cross-epic discipline.
- Completion: contract documented + stub-tested.

### Phase 4 — Progress LWC + controller (C5) *(milestone M3)*

**T4.1 — `PRM_AsyncJobProgressController`**
- Purpose: read progress + drive retry (C5).
- Expected outcome: `getProgress(caseManagerId)` (Records→Job→step-details + DLQ) and `retryFailed(stepDetailId)` → `PRM_AsyncOrchestrator.retry`; CRUD/FLS enforced. **Excludes** the schema-caveat columns (OQ-C4 resolved).
- Dependencies: T2.1. Prerequisites: T2.1.
- Impacted areas: `classes/PRM_AsyncJobProgressController.cls`.
- Validation: DTO shape; FLS; retry delegates.
- Testing: Apex ≥ 85%.
- Risks: low.
- Completion: controller + tests green.

**T4.2 — `prmAsyncJobProgress` LWC**
- Purpose: per-Case-Manager progress UI + **per-row** Retry (C5).
- Expected outcome: bundle on `IndividualApplication`; step grid; Refresh; **per-row Retry only (no bulk)**; finish via Custom Notification bell.
- Dependencies: T4.1. Prerequisites: T4.1.
- Impacted areas: `lwc/prmAsyncJobProgress/`.
- Validation: renders; Retry restarts the failed step + refreshes.
- Testing: Jest; UI/E2E scenario (A7).
- Risks: **[RISK]** UI/E2E needs a reachable org + browser driver (A7 boundary).
- Completion: LWC + Jest green; permset Apex-class access added (Epic A A5).

### Phase 5 — Cleanup + retention CMDT (C6) *(milestone M4)*

**T5.1 — `PRM_AsyncJobSetting__mdt` (retention config)**
- Purpose: externally configurable retention (F-21).
- Expected outcome: CMDT + `PRM_RetentionDays__c` + `Default` record = 90. **Only this field now** — sweeper cadence / flex-queue cap are a **future enhancement** (OQ-C5 deferred).
- Dependencies: none. Prerequisites: T0.
- Impacted areas: `objects/PRM_AsyncJobSetting__mdt/`, `customMetadata/`.
- Validation: deploys; `getInstance('Default')` returns 90.
- Testing: deploy.
- Risks: low.
- Completion: CMDT + record deploy.

**T5.2 — `PRM_AsyncJobCleanupBatch` + scheduler**
- Purpose: purge old jobs + files (C6).
- Expected outcome: batch reads `configuredRetention()` (fallback 90); deletes jobs (cascade both children) + payload `ContentDocument`s; monthly schedule.
- Dependencies: T5.1, EPIC A objects. Prerequisites: those.
- Impacted areas: `classes/PRM_AsyncJobCleanupBatch.cls`.
- Validation: only `Completed`/`Failed` past retention deleted; cascade verified; files deleted.
- Testing: Apex ≥ 85%; schedulable registers.
- Risks: **[RISK]** deleting `ContentDocument` removes the file for all links (safe: one file/job — confirm).
- Completion: batch + scheduler + tests green.

### Phase 6 — Evidence & governance *(milestone M5)* (Epic A §A7)
- Purpose: Test Evidence Report (Apex + LWC coverage + **UI/E2E screenshots** of the progress LWC) + human sign-off.
- Dependencies: Phases 2–5. Prerequisites: passing suites + a reachable org/driver for UI.
- Impacted areas: `docs/test-evidence/Epic_C_<date>/`.
- Validation: report assembled; sign-off on the PR.
- Testing: per C8 matrix.
- Risks: **[RISK]** no org/driver → UI section stubbed (A7 boundary).
- Completion: evidence + sign-off before `main`→`master`.

### Phase 7 — Version control *(milestone M5)*
- Purpose: integrate per C9/A8. Outcome: `[C*]` commits; PRs into `main`; squash-merge.
- Dependencies: Phase 6. Validation: merged; promote at milestone. Risks: SSH push. Completion: merged.

---

## 5. Challenge / review of the proposed approach

- **[RECOMMENDATION] Operational knobs on `PRM_AsyncJobSetting__mdt`** (sweeper cadence F-16, flex-queue cap F-6) — **deferred to a future enhancement** per OQ-C5; retention only for now.
- **[DECISION] C6b sweeper deferred** (OQ-C6) — the entire `PRM_AsyncJobSweeper` is a future enhancement (not built for the pilot); manual per-step Retry (C5) covers stranded/stuck steps.
- **[RISK] Strict halt + LDV.** One bad practitioner halts the whole submission's chain (F-15a, accepted). Monitor; retry restarts the step.
- **[RISK] Cross-epic contract.** The EPIC E batches must honour the C4 contract (idempotency, `finish()` ordering, JSON↔CM correlation) — enforce in EPIC E reviews.

---

## 6. Gaps & hidden dependencies

- **Target org** (OQ-C1) — external; gates deploy/test.
- **Reused classes' real signatures** (OQ-C7).
- **EPIC E batch classes / EPIC F intake wrapper + payload-file/correlation contract** — downstream owners (F-8/F-14).

---

## 7. Open Questions & decisions

### 7.0 Decisions confirmed (this review)
- **✅ OQ-C2 — C1 seed config:** **4 rows + `BatchSize = 1`** (matches Epic A; `GroupRelatedBatch` omitted). **Epic C C1 updated.**
- **✅ OQ-C4 — LWC extra columns** (Queue Position / ETA / Duration / Records): **excluded** for the pilot.
- **✅ OQ-C5 — `PRM_AsyncJobSetting__mdt` scope:** **`PRM_RetentionDays__c` only**; sweeper cadence + flex-queue cap → **future enhancement**.
- **✅ OQ-C3 — `PRM_AsyncJobNotification` home:** **kept in Epic C** (defined alongside the `notifyOnFinish` feature; not moved to Epic A).
- **✅ OQ-C6 — C6b sweeper:** **the entire `PRM_AsyncJobSweeper` is deferred to a future enhancement** (not built for the pilot). The `invokeJob` flex-queue depth-guard is also dropped (dispatch directly; a full queue → retryable step failure). Stranded/stuck steps are recovered **manually** via the per-step Retry button (C5) for the pilot.
- **◻ OQ-C1 — Target org:** **to be confirmed later** — gates deploy/test only.

### 7.1 Parked — pending org receipt (gated on OQ-C1)
- **OQ-C1 — Target org:** to be provided later.
- **OQ-C7 — Reused-class signatures:** confirm `PRM_ExceptionLogger.logExceptionReturnId(...)` and `PRM_NotificationHelper.sendBellNotification(...)` **against the org once received**; adjust `logFailure`/`notifyOnFinish` only if they differ.

---

## 8. Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-C1 | No target org → can't deploy/test | Medium | High | OQ-C1 (later) |
| R-C2 | Reused-class signature mismatch | Medium | Medium | OQ-C7 verify before T2.1 |
| R-C4 | Strict halt blocks a whole submission on one bad record | Medium | Medium | Accepted (F-15a); retry restarts the step |
| R-C5 | Flex Queue saturation under concurrency | Low–Med | Medium | Accepted trade-off (F-6); pilot dispatches directly → full queue = retryable step failure (manual Retry, C5). Depth-guard + sweeper deferred (OQ-C6) |
| R-C6 | Batch chaining from `finish()` / governor interplay | Low | Medium | sequential chain; test with stub batch |
| R-C7 | EPIC E batches don't honour the C4 contract | Medium | High (downstream) | enforce in EPIC E reviews; stub-test the contract |
| R-C8 | UI/E2E needs org + driver | Medium | Low | A7 boundary: stub UI section if unavailable |
| R-C9 | LDV batch-size unset (BatchSize=1 placeholder) | Confirmed | Medium | measure + seed before go-live |
| R-C10 | Remote push blocked (SSH) | Confirmed | Low | resolve credentials before Phase 8 |

---

## 9. What happens after sign-off

Resolved: OQ-C2 (4 rows / BatchSize 1), OQ-C4 (exclude columns), OQ-C5 (retention-only now), OQ-C3 (notification type kept in Epic C), OQ-C6 (entire C6b sweeper deferred to a future enhancement). Remaining (both gated on the org, to be provided later): OQ-C1 (target org), OQ-C7 (confirm reused-class signatures against the org). Once those are set, I will author the Epic C components in build order (C1 → C2/C3 → C4 stub/contract → C5 → C6; C6b sweeper deferred — OQ-C6) per the §C11 resolutions, run the Apex/LWC suites, assemble the Test Evidence Report, and pause for the human governance sign-off (A7) before any `main`→`master`. **No artifacts will be created until you confirm the org (OQ-C1) and the remaining items.**
