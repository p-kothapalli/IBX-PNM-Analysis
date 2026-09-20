# TDD Gap Analysis: Practitioner Creation Performance
## `TDD_PractitionerCreation.txt` vs. Research Requirements

---

## Background

The research documents (`PRM_NetworkCreation_Issue_Summary.md`, `PRM_Performance_Issues_Analysis_UserStories.md`, `PRM_NetworkCreation_BatchImplementation_Guide.md`) identified that `PRM_AddressLogicContainer` was silently failing during delegated practitioner creation with multiple practice locations — hitting Salesforce governor limits (SOQL 100, CPU 60s async, Heap 12MB) and leaving the UI spinning indefinitely.

---

## Architectural Approach: Research vs. TDD

The research documents recommended a **full event-driven Batch Apex architecture**. The TDD takes a **lighter Queueable restructuring approach**.

| Dimension | Research Recommendation | TDD Implementation |
|---|---|---|
| Core strategy | Replace IP3 with 3 Batch Apex classes triggered via Platform Event | Keep IP chain intact; change IP2 to Queueable, move IP3 invocation into IP2 as nested Queueable |
| New infrastructure | `NetworkCreationRequested__e`, 3 Batch classes, Orchestrator, Remote Action class | `PRM_ExceptionLogEventTrigger`, updated `PRM_ExceptionLogger.cls` + `PRM_OmniUtils.cls`, new fields on exception objects |
| UI response | < 3 seconds; returns immediately with "Processing..." | User still waits for TX1 (Container + IP1 synchronously) |
| User notification | Email on completion or failure | No email; no user-facing status |
| Status tracking | Granular: Processing Taxonomies → Payer Networks → IFC → Completed | One new flag: `IsNetworkRecordsCreated` on CaseDataManager |
| Rollback | Full rollback via `RequestId__c` on all created records | `rollbackOnError = true` per transaction scope only; manual retry recommended |
| Complexity | Higher — new Batch Apex, Platform Event, Orchestrator | Lower — IP configuration changes + Apex class updates |

Both approaches address governor limits. The TDD is pragmatic and lower-risk. However, there are meaningful gaps and several implementation risks described below.

---

## Differences in Detail

### 1. User Experience — Largest Business Gap

The research acceptance criteria explicitly required:
- UI returns in < 3 seconds with a "Processing..." message
- Status visible on the Case Manager record while processing
- Email notification on completion and failure
- Timestamps: Queued At, Started At, Completed At

**TDD delivers none of these.** TX1 (Container + IP1 chainable) is still synchronous — for practitioners with 5+ locations, users could still wait minutes before the UI returns. The original complaint was "silent failure with no user feedback" — this is only partially resolved. If IP2 or IP3 fails asynchronously, the user has no way to know unless they happen to check the Exception Log related list.

---

### 2. New Transaction Boundaries

The TDD introduces three independent Apex transactions:

```
TX1 (Synchronous/Chainable):
  Container + IP1 (PRM_PractitionerAddressCreation)
  → rollbackOnError = true (full rollback if IP1 fails)

TX2 (Queueable — first async hop):
  IP2 (PRM_ExistingPrimaryPracticeLocationLogicDelg)
  → rollbackOnError = true within IP2's scope only

TX3 (Queueable — second async hop from IP2):
  IP3 (PRM_CreateDelegatedHFNRecords)
  → rollbackOnError = true within IP3's scope only
```

TX1 commits before TX2 starts. TX2 commits before TX3 starts. There is **no cross-transaction rollback**. If TX2 or TX3 fails, all records from earlier transactions persist as orphans.

---

### 3. Data Threading: IP3 Inputs Through IP2

Currently, the Container passes `RecordsToUpdate` and `FacilityPractitionerTxNw` directly to IP3. Under the TDD, IP3 is invoked from IP2, so these two fields must be:

1. Added to the Container's `ExistingPrimaryAddressLogic` `additionalInput` (to forward them to IP2)
2. Forwarded by IP2 to IP3 via the new `AddTaxNetworkLogicFromDelg` element's `additionalInput`

This is documented in section 4.2.3 of the TDD but is a configuration step that is easy to miss. If either field is omitted, IP3 will receive null values and fail silently or produce incomplete records.

---

## Issues in the TDD Implementation

### Issue 1 — `logException` vs `logExceptionViaEvent` Routing Bug (High Risk)

**Section 5.4.1** of the TDD states:
> "Exception logs MUST be written via `PRM_ExceptionLogEvent__e`, NOT via direct DML insert to `PRM_ExceptionLog__c`, because `rollbackOnError = true` on IP2 and IP3 means the entire transaction rolls back on failure."

But **section 5.4.2.D** introduces a new overloaded `logException()` that ends with:
```apex
insert log;  // ← This will be rolled back inside IP2's failing transaction
```

If a developer calls this overload from IP2's or IP3's Catch block instead of `logExceptionViaEvent()`, the exception log will be silently rolled back — the exact failure mode they are trying to prevent. The two methods are not clearly differentiated in the TDD, and `PRM_OmniUtils.logException()` (section 5.4.2.E) routes to the direct-DML overload by default.

**Mitigation:** Rename the unsafe overload to `logExceptionDirect()` and add a clear comment that it is not safe in rollback contexts. Route all IP2/IP3 Catch blocks to `logExceptionViaEvent()` only.

---

### Issue 2 — IP3 Placement in IP2 Is Ambiguous (High Risk)

Section 4.2.2 gives two options for where to place the new `AddTaxNetworkLogicFromDelg` element in IP2:

```
Option A: level 1.0, seq 18.0 — inside ExistingPrimaryPractice conditional block
Option B: level 0.0, seq 6.0  — top-level, after ResponseForIp
```

The `ExistingPrimaryPractice` conditional block checks whether the practitioner has an existing primary practice location. **If that condition evaluates to false, Option A means IP3 never runs** — no taxonomy, payer network, or IFC records are created for the practitioner, with no error.

IP3 creates records needed in all scenarios, not just when an existing primary practice exists. **Option B (level 0, top-level) is almost certainly correct.** The TDD must resolve this before implementation begins.

---

### Issue 3 — TX1 Still Blocks the UI for Large Practitioners (Medium Risk)

The research identified that IP1 (`PRM_PractitionerAddressCreation`) with 100+ steps can hit governor limits for practitioners with 5+ locations even with elevated queueable overrides (200 queries / 60,000ms CPU). The TDD raises the Container's chainable limits but IP1 remains **chainable (synchronous)**. The OmniScript user waits for TX1 before the UI returns. For large practitioners, this is still a multi-minute synchronous wait — the original silent failure problem is partially deferred, not eliminated.

---

### Issue 4 — Queueable Chain Depth Cannot Be Tested in Sandbox (Medium Risk)

Salesforce Developer/Sandbox environments enforce a **1-level Queueable chaining limit** during test execution. The TX2 → TX3 hop (IP2 Queueable enqueueing IP3 as another Queueable) will not fire inside `Test.startTest()/stopTest()` in sandbox unit tests. This means:
- The TX3 behavior will not be covered by standard unit tests
- The integration can appear to work in sandbox while the TX2→TX3 handoff is entirely untested

A specific sandbox testing strategy using anonymous Apex with real data is required to validate the full chain before production deployment.

---

### Issue 5 — Try/Catch Scope in IP2 Is Too Narrow (Medium Risk)

The TDD wraps only the `ExistingPrimaryPractice` conditional block (seq 4) in a Try/Catch. IP2 has steps at seq 1–3 that run before this block. Any failure in those earlier steps propagates without:
- Exception log event being published
- `PRM_ExceptionLog__c` record being created
- Any visibility for the support team

The partial state from TX1 (addresses, facilities, locations, HC practitioners) will exist in the database with no associated error record and no retry path.

**Mitigation:** Wrap the entirety of IP2's logic starting at seq 1, not just the `ExistingPrimaryPractice` block.

---

### Issue 6 — `sendOnlyAdditionalInput: true` May Cut Off IP3 Data (Medium Risk)

The TDD specifies `sendOnlyAdditionalInput: true` for the new IP3 call within IP2. This means IP3 receives **only the 6 explicitly listed fields**:
```
PersonContactId, IsActive, RecordsToUpdate, CaseManagerId, IsPending, FacilityPractitionerTxNw
```

If IP3 currently relies on any data generated during IP2's execution (e.g., updated HCPF record IDs, practitioner facility references created by IP2's DML steps), those values will be absent.

**Mitigation:** Audit IP3's full input expectations against what IP2's execution context generates before setting this flag. Add any missing fields to `additionalInput` explicitly.

---

### Issue 7 — Retry Mechanism Is Recommended but Not Scoped (High Risk)

The TDD recommends Option 1 (Manual Retry) for Scenario B/C (partial state after TX2 or TX3 failure), which requires:
- A status value like "Error - Incomplete Processing" on IndividualApplication/CaseManager *(not scoped)*
- A Quick Action or OmniScript button on the Case Manager record that re-invokes only the failed IP *(not scoped)*

Without this, when partial state occurs (which it will), the operations team has no defined recovery path beyond manual investigation and record creation — the original workaround that was generating 15-20 support tickets per week.

---

### Issue 8 — `PRM_OmniUtils.logException` Change Affects All Callers (Low-Medium Risk)

Section 5.4.2.E updates `PRM_OmniUtils.logException()` globally to extract `caseManagerId` from the `inputMap` and pass it to `PRM_ExceptionLogger.logException()` — the direct DML overload. This change affects every IP that uses `logException` via `PRM_OmniUtils`, not just IP2 and IP3. Any of those IPs that run inside a rollback-able transaction could have their exception logs silently dropped.

---

## Improvements Without Major Changes

These are incorporated into `US_PractitionerCreation_QueueableRefactor.md` as required delivery items. Each can be implemented within the TDD's existing design without restructuring the core Queueable approach.

---

### Improvement 1 — Add Processing Status Field to CaseManager

**What:** Add `PRM_AsyncProcessingStatus__c` (picklist: `Not Started | Processing | Completed | Failed`) to the CaseManager / IndividualApplication object.

**How:**
- The Container's last step in TX1 (after IP1 completes) sets it to `Processing` via a DataRaptor Load or Remote Action.
- IP2's final step (happy path, before `AddTaxNetworkLogicFromDelg`) sets it to `Processing` (still in flight — IP3 is next).
- IP3's final step sets it to `Completed`.
- Each Catch block in IP2 and IP3 sets it to `Failed` via the same Remote Action that fires `logExceptionViaEvent`.

**Why it matters:** The original complaint was "the UI spins with no feedback." Even with the Queueable refactor, users have no way to know whether the async portions finished. This field — visible on the Case Manager record page — gives credentialing staff and ops a one-glance status check without querying exception logs. It is also the prerequisite for the follow-on retry story.

**Effort:** S (field + picklist + 4–5 IP step additions)

---

### Improvement 2 — Fix `logException` Naming and Routing

**What:** The TDD introduces two methods that serve different purposes but are named similarly, creating a real bug risk. Rename and route them clearly.

**How:**
1. Rename the direct-DML overload in `PRM_ExceptionLogger.cls` from `logException(... caseManagerId)` to `logExceptionDirect(... caseManagerId)`.
2. Add a header comment: `// NOT rollback-safe. Do not call from IP2, IP3, or any Queueable context.`
3. Update `PRM_OmniUtils.logException()` to route to `logExceptionViaEvent()` — not `logExceptionDirect()` — when the `inputMap` contains a `caseManagerId` key. This ensures all IP2/IP3 Catch blocks that go through `PRM_OmniUtils` land on the Platform Event path.
4. In the IP2 and IP3 Catch block Remote Action configurations, explicitly reference `logExceptionViaEvent` (not the generic `logException` endpoint).

**Why it matters:** Section 5.4.1 of the TDD states exception logs must use Platform Events. Section 5.4.2.D then shows the new `logException` overload using `insert log` — direct DML that will be rolled back. If a developer wires the Catch block to the wrong method, the exception log disappears silently. This is the exact failure mode being fixed.

**Effort:** M (Apex class changes + test coverage + IP configuration wiring)

---

### Improvement 3 — Lock In IP3 Placement at Level 0 (Top-Level in IP2)

**What:** The TDD gives two placement options for the `AddTaxNetworkLogicFromDelg` element — level 1 (inside the `ExistingPrimaryPractice` conditional block) or level 0 (top-level after `ResponseForIp`). The correct answer must be decided and locked before implementation begins.

**Decision:** Place at **level 0, top-level, after `ResponseForIp` (approximately seq 6.1)**. Do not place inside the `ExistingPrimaryPractice` conditional.

**Rationale:** `PRM_CreateDelegatedHFNRecords` creates taxonomy networks, payer networks, and IFC records that are required for all delegated practitioners — not just those with an existing primary practice location. Placing IP3 inside the conditional means it only fires when `ExistingPrimaryPractice` evaluates to true. For any practitioner where that condition is false (new primary practice), IP3 never runs: no taxonomy records, no payer networks, no IFC records — with no error.

**How:** Set `sequenceNumber: 6.1`, `level: 0` in the `AddTaxNetworkLogicFromDelg` element JSON. Add a description note in the IP: `"IP3 is placed at top-level to ensure execution regardless of ExistingPrimaryPractice condition."`.

**Effort:** S (configuration decision — zero additional code once decided)

---

### Improvement 4 — Widen Try/Catch Coverage in IP2 to Seq 1

**What:** The TDD wraps only the `ExistingPrimaryPractice` conditional block (seq 4) in a Try/Catch. Widen the Try block to start at seq 1 — covering all of IP2's execution.

**How:** In OmniStudio IP designer, move the Try Block's `fromSequence` property to encompass seq 1 (the first step in IP2) rather than seq 4 (the `ExistingPrimaryPractice` conditional). The Catch block Remote Action configuration is unchanged.

**Why it matters:** IP2 has steps at seq 1–3 before the conditional. Any validation query, DataRaptor Extract, or list manipulation that fails in those early steps would:
- Roll back IP2's DML
- Leave TX1 records as orphans with no associated error record
- Provide zero visibility to the support team

The ops team would see partial records in the database with no exception log and no `PRM_AsyncProcessingStatus__c = Failed` to alert them.

**Effort:** S (IP configuration only — expand the existing Try/Catch wrapper)

---

### Improvement 5 — Add `IsNetworkRecordsCreated__c` Flag and Enforce It in Delivery

**What:** Create `IsNetworkRecordsCreated__c` (Checkbox, default false) on CaseDataManager / IndividualApplication. IP3 must set it to `true` as its final step on the happy path.

**How:**
- Create the custom field.
- In `PRM_CreateDelegatedHFNRecords`, add a DataRaptor Load step (or Remote Action) as the final element on the success path: `IsNetworkRecordsCreated__c = true`.
- Add to the Case Manager record page layout alongside `PRM_AsyncProcessingStatus__c`.
- Add an admin SOQL query to the monitoring documentation: `SELECT Id, Name, IsNetworkRecordsCreated__c, PRM_AsyncProcessingStatus__c FROM IndividualApplication WHERE PRM_AsyncProcessingStatus__c = 'Failed' OR (PRM_AsyncProcessingStatus__c = 'Completed' AND IsNetworkRecordsCreated__c = false)` — this surfaces cases where IP2 completed but IP3 was silently skipped.

**Why it matters:** Section 5.5 of the TDD lists this as an "approach" without committing it to the delivery checklist. Without this flag, there is no query-able way to identify practitioners where IP2 succeeded but IP3 never ran (a silent scenario if the `AddTaxNetworkLogicFromDelg` element is misconfigured). It is also the data source for any future automated retry scheduler.

**Effort:** S (field + 1 IP step + layout)

---

### Improvement 6 — Audit IP3 Input Requirements Before Setting `sendOnlyAdditionalInput: true`

**What:** Before setting `sendOnlyAdditionalInput: true` on the `AddTaxNetworkLogicFromDelg` element, verify that `PRM_CreateDelegatedHFNRecords` only requires the 6 explicitly listed inputs.

**How (pre-build validation step):**
1. Open `PRM_CreateDelegatedHFNRecords` in OmniStudio.
2. List every input variable referenced in its steps (DataRaptor inputs, Remote Action inputs, conditional formula references, Loop Block source variables).
3. Map each one to the 6 fields: `PersonContactId`, `IsActive`, `RecordsToUpdate`, `CaseManagerId`, `IsPending`, `FacilityPractitionerTxNw`.
4. If any referenced variable is absent → add it to `additionalInput` in the `AddTaxNetworkLogicFromDelg` element.
5. If all 6 map cleanly → proceed with `sendOnlyAdditionalInput: true`.

**Why it matters:** IP3 was previously invoked by the Container, which had a different (and likely larger) input context than IP2. Any field IP3 read from the Container's context that is not in the 6-field list will be null when invoked from IP2 with `sendOnlyAdditionalInput: true`. This could cause silent data omissions (records created with null fields) or explicit failures depending on validation rules.

**Effort:** S (analysis only — 1–2 hours; any missing fields add S per field)

---

### Improvement 7 — Define Sandbox Test Strategy for the TX2 → TX3 Queueable Chain

**What:** Document and execute a specific manual integration test procedure for the TX2 → TX3 hop (IP2 Queueable enqueueing IP3 as another Queueable), which cannot be validated through standard sandbox unit tests.

**Why it matters:** Salesforce Developer/Sandbox environments enforce a **1-level Queueable chaining limit** during Apex test execution (`Test.startTest()/stopTest()`). When IP2 (TX2) runs as a Queueable and attempts to enqueue IP3 (TX3), that second enqueue fires in production but is suppressed in test contexts. A standard unit test will show IP2 succeeding with no evidence that IP3 was or was not enqueued — giving a false green.

**Recommended test procedure:**
1. In a full sandbox (not Developer edition) with real-like data, create a test practitioner with 3 practice locations.
2. Trigger the OmniScript submission manually.
3. After the UI returns (TX1 complete), query `AsyncApexJob` for `JobType = 'Queueable'` with the IP2 class name — confirm IP2 is enqueued.
4. Once IP2 shows `Status = Completed`, re-query for IP3's Queueable job — confirm it is enqueued and ultimately completes.
5. Verify `IsNetworkRecordsCreated__c = true` and `PRM_AsyncProcessingStatus__c = Completed` on the Case Manager.
6. Run the forced-failure scenario: temporarily introduce a validation rule on a record IP2 creates, re-trigger, confirm exception log is created and linked.

**Effort:** M (documentation + 2–3 hours of manual execution in a full sandbox environment)

---

> All 7 improvements are captured as required delivery items in  
> `US_PractitionerCreation_QueueableRefactor.md` (Deployment Checklist + Technical Section).

---

## Risk Summary

| # | Issue | Severity | Effort to Fix |
|---|---|---|---|
| 1 | `logException` vs `logExceptionViaEvent` routing bug | **High** | Low — rename + routing change |
| 2 | IP3 placement ambiguity in IP2 | **High** | Low — one-line config decision |
| 7 | Retry mechanism not scoped | **High** | Medium — Quick Action or OmniScript button |
| 3 | TX1 still blocks UI for large practitioners | Medium | High — would require IP1 restructuring |
| 4 | Queueable chain untestable in sandbox | Medium | Low — documentation + manual test plan |
| 5 | Try/Catch scope too narrow in IP2 | Medium | Low — expand Try/Catch start point |
| 6 | `sendOnlyAdditionalInput` may cut off IP3 data | Medium | Low — input audit + additionalInput additions |
| 8 | `PRM_OmniUtils.logException` affects all callers | Low-Medium | Medium — routing audit across all calling IPs |

---

## Recommendation

The TDD's Queueable restructuring approach is pragmatic and appropriate for an initial release. The exception logging design is solid. However, **three items should be resolved before implementation begins**:

1. **Decide and document IP3 placement** (Issue 2) — level 0 top-level is almost certainly correct
2. **Fix the `logException` vs `logExceptionViaEvent` routing** (Issue 1) — otherwise the exception logging will silently fail in the rollback scenario it was designed to handle
3. **Scope the retry mechanism** (Issue 7) — without it, any partial-state failure has no recovery path for the operations team

And **one item should be added to the delivery checklist** regardless of approach:
- A minimal user-facing status field on CaseManager so users know whether async processing is running, completed, or failed
