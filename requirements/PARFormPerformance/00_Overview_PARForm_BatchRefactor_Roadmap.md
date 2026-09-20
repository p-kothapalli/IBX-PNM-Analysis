# PAR Form — Performance & Partial-Data Fix Roadmap

**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_PractitionerParticipationForm_English` (v111)
**Container IP:** `PRM_CreateParFormRecordsContainer` → `PRM_CreateParFormRecords_Procedure_29`
**Last updated:** May 28, 2026 (scale audit added)
**Companion documents:**
- `requirements/PAR_Form_PartialDataRollback_Investigation_FixPlan.md` — root-cause investigation
- `requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` — 16 documented production failures
- `requirements/PAR_Form_DuplicateErrors_DataFix_Runbook.md` — one-off data-fix runbook for those 16
- `requirements/PractitionerCreationPerformance/US_DelegatedPractitioner_AddressCreation_BatchRefactor.md` — the **architectural blueprint** we are cloning
- **`US_PAR_ScaleAudit_5Groups_10Locations.md`** — maximum-scale audit (5 groups × 10 locations = ~490 rows/submission). All five US-PAR stories have AC-MAX criteria derived from this audit.

---

## 1. Why we are doing this

The PAR Form (new-practitioner self-service application) suffers from the **same class of architectural problem** the Delegated Practitioner team already solved on the credentialing side in the April–May 2026 sprints. Specifically:

| Symptom | PAR Form (today) | Delegated Practitioner (before May 2026) |
|---|---|---|
| Synchronous IP chain timing out / UI spinning | 5–15 sec for typical submissions | 5+ min, browser hang for 3+ locations |
| Partial data when intermediate IPs fail | 36 confirmed `updatePPLAddresesForPAR()` null-input throws / 30 d, 48 `setPracFacilityIdentifier` NPEs / 30 d, 277 HCPT duplicate-junction pairs accumulated | 15–20 partial-creation tickets / week |
| Silent failures (no exception log) | `TryCatchBlock.logTryCatchException` writes nothing because `SV_SourceIPDetails` is never overwritten by child sub-IPs | `PRM_ExceptionLog__c` rows lost to `rollbackOnError=true` |
| Duplicate / re-submission cycle | ~13% of practitioner accounts have ≥2 PAR submissions; 16 documented production failures | Frequent double-submits ("did it work?") |
| User does not know if work succeeded | OmniScript final response gives no status, no Case Manager redirect | Same |

The Delegated team **fixed every one of these** using a single architectural pattern. This roadmap applies that exact pattern to the PAR Form. We are not inventing anything new — every piece below already exists in production for Delegated Practitioner Creation and Network Creation, has been load-tested, and survived the IA-0000150602 governor-unwind incident that hardened the design.

---

## 2. The proven architectural pattern (what they did for Delegated)

### 2.1 Pattern A — Envelope / Helper / Batch (the core)

> **Reference code in production:** `PRM_NetworkCreationEnvelope.cls`, `PRM_NetworkCreationRow.cls`, `PRM_NetworkCreationHelper.cls`, `PRM_NetworkCreationBatch.cls`

```
TX1 (synchronous UI turn, returns in <100 ms after enqueue):
  OmniScript Submit
    → Container IP (just a Remote Action wrapper)
      → PRM_OmniProcessUtils.callMethod('enqueueXxx', input, outMap)
        → PRM_XxxHelper.enqueue(input)
            • validate inputs
            • build PRM_XxxEnvelope { caseManagerId, …, List<Row> rows }
            • Database.executeBatch(new PRM_XxxBatch(envelope), chunkSize)
            • return { jobId, success, message }       ← NEVER throws
    → Response Action returns CaseManagerId, jobId  to the OmniScript
    → OmniScript Navigate Action → SObject view (CaseManagerId)

TX2..N (Batchable, Stateful, separate Apex transactions):
  PRM_XxxBatch.execute(scope = one chunk of rows)
    • memoized lookups (cachedHfNameToId style — saves ~60% SOQL/chunk)
    • per-row DML with Database.insert(..., false)  ← allOrNone=false
    • on row failure: stage to PRM_FailedRecordStaging__c + publish exception event
  PRM_XxxBatch.finish()
    • update IndividualApplication.PRM_*Status__c (Success / Failed / Partial)
    • PRM_NotificationHelper.sendBellNotification(...)
```

### 2.2 Pattern B — Rollback-safe exception logging via Platform Event

> **Reference design:** `US_PractitionerCreation_QueueableRefactor.md` §B / §C

`PRM_ExceptionLog__c` direct inserts are unsafe inside any IP with `rollbackOnError=true` — they get rolled back along with the failure. The team's fix:

```
IP catch block / Apex catch
  → EventBus.publish(new PRM_ExceptionLogEvent__e(...))   ← survives rollback
  → PRM_ExceptionLogEventTrigger (after insert)
    → insert PRM_ExceptionLog__c (with PRM_IndividualApplication__c lookup)
```

Platform Events have their own publish-immediately commit, so they survive any Apex transaction rollback that follows. The PAR `TryCatchBlock` calling `PRM_OmniUtils.logTryCatchException` (which does a direct DML insert) currently fails this rule — that's why our 30-day PAR exception log has only 92 rows across 5 distinct process names.

### 2.3 Pattern C — Per-row failure staging

> **Reference spec:** `requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md`

`PRM_FailedRecordStaging__c` is the **shared retry queue** for all PNM async work. The Delegated/Network team writes to it on every per-row DML failure with `PRM_SourceFlow__c='PRM_NetworkCreationBatch'`. Network Management QC analysts have a list-view filtered by `PRM_SourceFlow__c` to triage failures.

PAR will write with `PRM_SourceFlow__c='PRM_ParFormSubmissionBatch'` and reuse the same staging + retry UX.

### 2.4 Pattern D — Hard counter discipline (governor-unwind defence)

From `PRM_NetworkCreationBatch.execute()` lines 161–166 (the IA-0000150602 fix, 2026-05-20):

```apex
} catch (Exception e) {
    // CRITICAL: bump in-memory accounting BEFORE any DML so the count
    // survives a secondary governor unwind. Without this, SOQL=201
    // killed the inner DML, finish() saw failureCount=0, and marked
    // the IA "Success" when it should have been "Failed".
    failureCount += chunkSizeAtStart;
    failureMessages.add('execute() threw: ' + e.getTypeName() + ' - ' + e.getMessage());
    // … best-effort exception log + staging follow ...
}
```

Every batch in this roadmap must obey this rule.

### 2.5 Pattern E — IA status field + Bell notification

The Network Management QC team needs to know **without polling** whether async work landed. The pattern:

| Object | Field | Used by |
|---|---|---|
| `IndividualApplication` | `PRM_ProcessingStatus__c` (overall, picklist: Queued / Processing / Success / Failed / Partial Failure) | All batches roll up to this |
| `IndividualApplication` | `PRM_AddressCreationStatus__c` | `PRM_AddressCreationBatch` (in flight per `US_DelegatedPractitioner_AddressCreation_BatchRefactor`) |
| `IndividualApplication` | `PRM_NetworkCreationStatus__c` | `PRM_NetworkCreationBatch` (live) |
| `IndividualApplication` | `PRM_ParFormSubmissionStatus__c` (NEW) | `PRM_ParFormSubmissionBatch` (this roadmap) |

Each batch's `finish()` calls `PRM_NotificationHelper.sendBellNotification(owner, 'PRM_CustomNotitficationtoCaseOwner', title, body, caseManagerId)`. The user sees a bell ping titled "Practitioner Application Submitted" or "...Action Needed", clicks, lands on the Case Manager.

### 2.6 Pattern F — Idempotency guard (anti-double-submit)

In `PRM_*Helper.enqueue()`, before calling `Database.executeBatch`, query `AsyncApexJob` for the same `CaseManagerId` enqueued within the last 60 seconds. If found, return the existing job id with `success: true, message: 'Already queued'`. Prevents the double-click-Submit storm we currently see.

### 2.7 Pattern G — Trigger idempotency (anti-collision)

Before-insert triggers that compute external-style unique identifiers (`PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier`, `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier`) must:
1. Query existing records with the computed key
2. If found, set `Id` on the incoming record to convert the insert into an update
3. Never let the platform throw a generic `DUPLICATE_VALUE` error that the OmniScript catch-all masks

The 277 HCPT duplicate-junction pairs we see in QA today are the direct symptom of these triggers NOT being idempotent.

---

## 2.5 Scale ceiling and cross-cutting invariants (added 2026-05-28)

After auditing the OmniScript metadata, the form supports the following maximums in one submission:

| Repeatable | Max | Evidence |
|---|---|---|
| Groups (`GroupInformation` block) | **5** | Main form v111 line 2608: `repeatLimit = 4` (initial + 4 clones) |
| Locations per group (`AdditionalAddress` block) | **10** | Address sub-form v54 line 2003: `repeatLimit = 9` (primary office + 9 additional) |
| Licenses (`AddLicenseBlock`) | **4** | Main form v111 line 3202: `repeatLimit = 3` |
| Contacts | 2 | Primary + secondary booleans |

**Worst-case data volume per submission:** **~490 database rows across ~15 object types.** Detailed breakdown lives in `US_PAR_ScaleAudit_5Groups_10Locations.md`. Highlights:

- 50 `HealthcarePractitionerFacility` (PPL) rows, ~150 `ContactPointAddress`, ~60 `Schema.Address`, ~55 `HealthcareFacility`, ~70 trigger-inserted Identifier rows, plus the practitioner/group/case/IA singletons.
- One submission fits comfortably in one async batch chunk (~20 of 150 DML statements, ~600 of 10,000 DML rows, ~50 of 100 SOQL, ~6 of 60 s CPU).
- The pre-callout phase at this scale would need **50 Precisely callouts** if done naively, which is **infeasible** (25–75 s UI wait). US-PAR-03 must use a bulk endpoint + dedup; see audit doc §4 and US-PAR-03 §G.

### Cross-cutting invariants (every story enforces these)

1. **Per-submission entity ceiling: ~500 rows / ~15 object types.** Any future PAR-form feature that adds a new repeatable (e.g., "6 groups", "20 specialties per location") must re-run the scale audit and update AC-MAX in every story.
2. **`chunkSize = 1` is mandatory for `PRM_ParFormSubmissionBatch`.** Bundling N submissions per chunk multiplies the 490 rows by N and breaks per-transaction governor limits.
3. **Zero callouts inside `execute()`.** Unit-test `execute_makesNoCallouts` (US-PAR-03 §F) is the permanent guardrail.
4. **One SOQL per trigger per `Trigger.new` invocation, regardless of size.** AC-MAX-BULK in US-PAR-04 is the contract; bulk-safety tests at 50 PPL / 55 HF / 150 CPA rows are mandatory.
5. **Auto-retry concurrency capped at 3 parallel batches.** Prevents the org's 5-batch slot from being exhausted by a PAR backlog flush; AC-RETRY-THROTTLE in US-PAR-05.
6. **In-flight retry guard.** A staging row whose previous retry is still `Processing` is skipped — AC-RETRY-IDEMPOTENT in US-PAR-05.

---

## 3. The five PAR-Form user stories

Each story below is a **standalone deliverable** with its own AC, scope, and effort, but they layer on each other. The recommended sprint sequencing is in §4.

| # | Title | One-line scope | Mirror of |
|---|---|---|---|
| **US-PAR-01** | **Move PAR Form Record Creation to Batch (sub-3s Submit + Navigate to Case Manager)** | Replace the 7-sub-IP synchronous chain with `PRM_ParFormSubmissionBatch`; OmniScript returns in <3s and navigates to Case Manager. | `US_DelegatedPractitioner_AddressCreation_BatchRefactor.md` |
| **US-PAR-02** | **Rollback-Safe Exception Logging for PAR Form (Platform Event Pattern)** | Wire `PRM_ExceptionLogEvent__e` into PAR; survive `rollbackOnError=true`; link each log to the Case Manager. | `US_PractitionerCreation_QueueableRefactor.md` §B–§C |
| **US-PAR-03** | **Pre-Submit Callout Phase — Address Standardization Before DML** | Solve the historical `chainOnStep:false` rationale by running Precisely + MuleSoft callouts in TX1 (UI turn) before the batch starts; batch becomes pure DML. | (new, but follows the Salesforce "no callout after DML" guidance referenced in `PRM_NetworkCreation_BatchImplementation_Guide.md`) |
| **US-PAR-04** | **Trigger Idempotency for HCProvider + PracFacility Identifiers** | Make `populateSourceSystemIdentifier` and `setPracFacilityIdentifier` idempotent so the batch is safe to retry. Drops 48 NPEs/month + Cat B duplicate-errors to zero. | `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` Item #6 (HCProvider) + analogous fix on PracFacility |
| **US-PAR-05** | **Per-Row Failure Staging + Analyst Retry UX for PAR Form** | Connect `PRM_ParFormSubmissionBatch` partial-failures to `PRM_FailedRecordStaging__c`; add Quick Action on Case Manager for one-click retry. | `PRM_FailedRecordStaging_Object_Specification.md` + retry pattern from `US_DataAdmin_NetworkError_ListViewAndQCRouting.md` |

---

## 4. Sprint sequencing and dependencies

```
                     ┌──────────────────────────────────────────────────┐
Sprint 1 (P0)        │ US-PAR-04: Trigger Idempotency                   │
                     │   (≈3 days; lowest risk; immediate Cat B/C win)  │
                     └──────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────────┐
Sprint 1 (P0)        │ US-PAR-02: Exception Logging via Platform Event  │
                     │   (≈3 days; unlocks observability for the rest)  │
                     │   Depends on US-PR-Queueable shipping the        │
                     │   ExceptionLogEvent field updates first, OR      │
                     │   this story ships them itself.                  │
                     └──────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────────┐
Sprint 2 (P0)        │ US-PAR-03: Pre-Submit Callout Phase              │
                     │   (≈4–6 days; isolates the Precisely + MuleSoft  │
                     │   callout dependency to before any DML)          │
                     └──────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────────┐
Sprint 2–3 (P0)      │ US-PAR-01: Batch Refactor (THE main story)       │
                     │   (≈10–14 days; the heavy Apex lift; XL)         │
                     │   Hard-depends on US-PAR-04 (batch retries),     │
                     │   US-PAR-02 (catch-block logging), US-PAR-03     │
                     │   (no callouts in batch).                        │
                     └──────────────────┬───────────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────────────────┐
Sprint 3 (P1)        │ US-PAR-05: Failed-Record Staging + Analyst Retry │
                     │   (≈4–6 days; analyst-facing UX polish)          │
                     └──────────────────────────────────────────────────┘
```

**Why this order?**
- **US-PAR-04 first** is the smallest, lowest-risk story and immediately reduces the partial-data accumulation rate even before the batch ships. It also makes the batch safe to retry, which is mandatory before US-PAR-01.
- **US-PAR-02 second** gives us observability. Without it we can't tell whether US-PAR-01 actually fixed anything because the failures are invisible today.
- **US-PAR-03 third** because the batch refactor cannot ship until the callout-after-DML constraint is structurally satisfied. Doing it as part of US-PAR-01 doubles the scope.
- **US-PAR-01 fourth** ships the core architectural fix once its dependencies are in place.
- **US-PAR-05 last** is the UX polish on top of the staging records that US-PAR-01 already writes.

---

## 5. End-to-end target behaviour (after all five stories ship)

```
User clicks Submit on PAR form
  ↓ (TX1, synchronous, target ≤ 3 s)
  • Pre-Submit Callout Phase
      - Precisely API standardizes addresses (US-PAR-03)
      - MuleSoft pre-validates Tax-Id / NPI (US-PAR-03)
  • Trigger idempotency converts would-be duplicates into upserts (US-PAR-04)
  • PRM_ParFormSubmissionHelper.enqueueParFormSubmission(...)
      - duplicate-guard via AsyncApexJob lookup (Pattern F)
      - Database.executeBatch(new PRM_ParFormSubmissionBatch(...))
      - returns { jobId, success: true, caseManagerId }
  ↓
  OmniScript Show Toast: "Submission queued — we'll notify you."
  OmniScript Navigate Action: SObject view → Case Manager record
  ↓
  ━━━ User is free to move on ━━━
  ↓ (TX2..N, Batchable, separate transactions, 30–120 s)
  PRM_ParFormSubmissionBatch.execute(chunk = 1 submission):
    Savepoint sp = Database.setSavepoint()
    try {
      createPractitionerRecords(envelope)    ← sub-IP 2/3 work
      createGroupRecords(envelope)            ← sub-IP 4 work
      createAddressAndPPLRecords(envelope)    ← sub-IP 5 DML half (callouts ALREADY done)
      createProviderRecords(envelope)         ← sub-IP 6 work
      createContactRecords(envelope)          ← sub-IP 7 work
      activateAll(envelope)
      successCount++
    } catch (Exception e) {
      Database.rollback(sp)                   ← atomic — no partial data
      failureCount++
      stage to PRM_FailedRecordStaging__c     ← US-PAR-05
      EventBus.publish(PRM_ExceptionLogEvent__e) ← US-PAR-02 (rollback-safe)
    }
  ↓
  PRM_ParFormSubmissionBatch.finish():
    update IA.PRM_ParFormSubmissionStatus__c = (failureCount==0 ? Success : Failed)
    PRM_NotificationHelper.sendBellNotification(...)
  ↓
  User sees bell: "PAR Submission Complete" → clicks → Case Manager record
  If failed: Case Manager has Failed Record Staging related list (US-PAR-05)
             with a "Retry" Quick Action that re-enqueues the same envelope.
```

**Key guarantees:**

| Guarantee | Mechanism |
|---|---|
| **Atomic per-submission** — no orphan Practitioner Account if vendor creation fails | Single Savepoint inside `PRM_ParFormSubmissionBatch.execute()` (US-PAR-01) |
| **Sub-3s submit** | All heavy DML moves to async batch (US-PAR-01) |
| **Observable failures** | Every catch publishes a Platform Event that survives rollback (US-PAR-02) |
| **No callout-after-DML errors** | Callouts run in TX1 before any DML (US-PAR-03) |
| **No duplicate-collision errors on retry** | Idempotent triggers convert dup-inserts to updates (US-PAR-04) |
| **One-click analyst recovery** | Failed Record Staging row + Retry Quick Action (US-PAR-05) |

---

## 6. Reference — what stays unchanged

The PAR form is a **net additive** workstream — it does not regress anything live. Specifically:

- `PRM_NetworkCreationBatch` (live for Delegated/Initial cred network creation) is unchanged
- `PRM_AddressCreationBatch` (in flight per `US_DelegatedPractitioner_AddressCreation_BatchRefactor`) is unchanged
- `PRM_FailedRecordStaging__c` schema is unchanged — we only add a new picklist value `PRM_ParFormSubmissionBatch` to `PRM_SourceFlow__c`
- `PRM_ExceptionLog__c` and `PRM_ExceptionLogEvent__e` field set may need 2 fields added (per US-PAR-02) but no schema removals
- The OmniScript stays the same except for the Submit IP step and a new Navigate Action

The container IP `PRM_CreateParFormRecordsContainer` and the orchestrator IP `PRM_CreateParFormRecords_Procedure_29` will be **versioned forward** (Container v2 / Procedure v30), and the older versions stay in the org `isActive=false` for 30 days as a session backstop, then deleted. Same disposition pattern as `PRM_PractitionerAddressCreation_Procedure_5` in the Delegated refactor.

---

## 7. Open architectural questions (cross-cutting — answer once for the suite)

| # | Question | Affects |
|---|---|---|
| 1 | Does the existing `PRM_ExceptionLogEvent__e` Platform Event need to add `PRM_RecordId__c` and `PRM_RecordObjectName__c` fields, or is the Queueable Refactor story shipping them first? | US-PAR-02 dependency graph |
| 2 | Does `PRM_ExceptionLog__c.PRM_IndividualApplication__c` (lookup to IndividualApplication) ship with the Queueable Refactor or do we add it here? | US-PAR-02 dependency graph |
| 3 | Does `PRM_FailedRecordStaging__c` exist in QA today as a deployed object? (Spec is in `requirements/PractitionerCreationPerformance/`; we don't see the object metadata in `force-app/main/default/objects/`.) | US-PAR-05 prerequisite |
| 4 | Is `IndividualApplication.PRM_ProcessingStatus__c` already in the org, or only proposed in `US_DelegatedPractitioner_AddressCreation_BatchRefactor`? | US-PAR-01 / US-PAR-05 acceptance criteria |
| 5 | For PAR submissions, who is the "owner" for the bell notification — `UserInfo.getUserId()` (the analyst who submitted), the Case Manager `OwnerId`, or both? | US-PAR-01 AC2 |
| 6 | What is the production chunk size used by `PRM_NetworkCreationBatch` (default 50; `US_DelegatedPractitioner_AddressCreation_BatchRefactor` proposes 5 for address)? PAR is heavier than Network and lighter than Address — start at 1 (one full submission per chunk) and tune. | US-PAR-01 §B |
| 7 | Should the batch support partial-submission rollback (delete records from a failed `execute()` of submission #N while keeping submissions #1..#N-1 successful)? Salesforce best practice is yes via per-row Savepoint, but `PRM_Batch_Rollback_Strategies.md` Option 1 is also valid. | US-PAR-01 design choice |
| 8 | **BLOCKER FOR US-PAR-03.** Does Precisely's `verify` endpoint (used by `PRM_IPPreciselyAPICall`) accept a batch payload of up to 50 addresses per HTTP request? If **yes**, US-PAR-03 §G.1–§G.3 (bulk wrapper + dedup + Continuation + fail-fast) is sufficient and effort is +1 day. If **no**, US-PAR-03 must implement §G.4 (`@future(callout=true)` fan-out fallback) and effort is +3 days. **Current state:** `PRM_AddressValidationService.validateAddress()` is single-address only (confirmed via inspection 2026-05-28); no `PRM_IPPreciselyAPICallBulk` IP exists today. **Owner:** Integrations team + Precisely vendor contact. **Cannot ship US-PAR-03 without this answer; cannot ship US-PAR-01 without US-PAR-03.** | US-PAR-03 path choice; whole roadmap timeline |

These should be resolved **before** Sprint 1 estimation is finalized. **Question 8 is the gating clarification — work to resolve in parallel with Sprint 1 (US-PAR-04) so US-PAR-03 can start in Sprint 2 unblocked.**

---

## 8. Acceptance metrics (post-deployment monitoring — first 30 days)

| Metric | Target | Today |
|---|---:|---:|
| PAR Submit response time (P95, typical 1×3) | ≤ 3 s | 5–15 s |
| PAR Submit response time (P95, **max scale 5×10**) | ≤ 15 s end-to-end (pre-callout + enqueue + navigate) | Unknown (sync IP would hit 120 s ceiling — see scale audit §4) |
| Max-scale batch `execute()` CPU | ≤ 6 s | n/a (no batch today) |
| Max-scale batch `execute()` DML statements / DML rows / SOQL | ≤ 20 / ≤ 600 / ≤ 50 (of 150 / 10,000 / 100) | n/a |
| `PRM_OmniUtils.updatePPLAddresesForPAR()` null-input throws / 30 d | **0** | 36 |
| `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` NPEs / 30 d | **0** | 48 |
| New HCPT duplicate `(AccountId, TaxonomyId)` pairs / 30 d | **0** | ~10/month (extrapolating from 277 cumulative) |
| Trigger SOQL count at 50 PPL / 55 HF / 150 CPA bulk insert | ≤ 3 additional SOQLs (one bulk lookup) | Unknown — current loops likely 50/55/150 single-row SOQLs |
| Precisely callouts per submission (pre-callout phase) | ≤ 2 bulk HTTP calls at max scale | 50 single-address callouts at max scale (today's pattern) |
| `PRM_ExceptionLog__c` rows with the correct failing sub-process name | **100%** of failed PAR submissions | < 10% |
| Platform events published per failed submission at max scale | ≤ 20 (one per failed object type) | n/a — direct DML pattern today |
| Concurrent `PRM_ParFormSubmissionBatch` jobs during auto-retry backlog drain | ≤ 3 | n/a |
| PAR Cat A/B/C/D production failures (the 16 historical) | **0** new cases | 16 cumulative, still recurring |
| User-reported "I don't know if it worked" tickets | **0** | 15–20 / week |

Each user story has its own AC tied to a subset of these metrics; the roadmap-level definition of done is hitting all of them simultaneously for two consecutive sprints.
