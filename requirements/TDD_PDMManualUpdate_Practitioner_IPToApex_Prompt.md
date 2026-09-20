You are a senior Salesforce architect with deep expertise in OmniStudio Integration Procedures, Batch Apex, Platform Events, and governor limit engineering. Your task is to write a complete, self-contained High Level Technical Design Document for the following work item:

**Title:** PDM Manual Update - Practitioner: Full IP-to-Apex Migration & Large Data Optimization

**Stakeholder direction (verbatim):** "not sure keeping the IPs will work, we have to move away from the IPs and have them in batches / future processing and use the framework that we are building for practitioner creation. Re-check and redesign in detail on what will take it to move it to Apex from IPs."

---

## STEP 1 — READ THESE FILES FIRST (in order)

Before writing a single word of the document, read all of the following files. They are the authoritative source of truth. Do not invent architecture, class names, field names, or component details — derive everything from these files.

1. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/PRM_NetworkCreation_BatchImplementation_Guide.md`
   — The full Batch Apex framework being built for Practitioner Creation. Contains class names, field names, batch chain sequence, and the IP-to-Apex pattern to reuse.

2. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/PRM_NetworkCreation_Issue_Summary.md`
   — Root cause analysis of why IPs fail (280+ operations, governor limits, specific numbers). Use this as the technical foundation for Section 2.

3. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/TDD_PractitionerCreation.txt`
   — The Queueable-only TDD. **CRITICAL INSTRUCTION: This approach is now considered superseded and insufficient.** Do NOT use it as a solution model. Use it only to understand the current IP chain structure — the IP step names, sequence numbers, what each step does, and what parameters flow between IPs. The Queueable approach has been formally rejected in favor of the Batch Apex framework.

4. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/TDD_Gap_Analysis.md`
   — Formal analysis of why the Queueable approach alone is insufficient. Read this to understand exactly why the Queueable path was rejected and how to explain that in Section 1 and Section 2.

5. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/US_PractitionerCreation_Complete_Implementation.md`
   — Full implementation user stories for Practitioner Creation including the batch framework, staging, and exception handling. Use this to understand what is already being built so you can correctly identify zero-effort reuse.

6. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/PRM_FailedRecordStaging_Object_Specification.md`
   — Complete specification for `PRM_FailedRecordStaging__c`. This object is already being built for Practitioner Creation and must be reused as-is for PDM Manual Update.

7. `/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/PractitionerCreationPerformance/US_DataAdmin_NetworkError_ListViewAndQCRouting.md`
   — Data Admin tooling (list views, QC routing) being built once for Practitioner Creation. PDM Manual Update reuses this tooling at zero additional effort.

---

## STEP 2 — CONTEXT YOU MUST INTERNALIZE

### The Practitioner Creation Batch Framework (already being built)

The IP chain `PRM_AddressLogicContainer` handles synchronous work via IP1 (`PRM_PractitionerAddressCreation`) for address/facility/location creation and IP2 (`PRM_ExistingPrimaryPracticeLocationLogicDelg`) for primary practice location logic. Instead of calling IP3 (`PRM_CreateDelegatedHFNRecords`), the IP now publishes a Platform Event `NetworkCreationRequested__e` via a Remote Action class `PRM_NetworkCreationRemote`. The UI returns immediately (under 3 seconds) with a "Processing..." message. IP3 is completely retired.

The Platform Event triggers `PRM_NetworkCreationEventTrigger` → `PRM_NetworkCreationOrchestrator` → starts a chain of three Batch Apex classes:
- `PRM_TaxonomyNetworkBatch` — creates taxonomy network records (9 records per 3-location practitioner), queries `PRM_PractitionerPracticeLocation__c`, chains to next batch on `finish()`
- `PRM_PayerNetworkBatch` — creates payer network records (45 records), chains to next batch on `finish()`
- `PRM_IFCRecordBatch` — creates IFC records (15 records), sends email notification on completion

Each batch class implements `Database.Batchable<SObject>` and `Database.Stateful`. Each carries: `caseManagerId`, `personContactId`, `requestId`, `isActive`, `isPending`, `effectiveFrom`, `effectiveTo`, `recordsToUpdate`. Each updates `PRM_NetworkCreationStatus__c` on CaseManager through this progression: `Not Started → Queued → Processing Taxonomies → Processing Payer Networks → Processing IFC → Completed / Failed`. Each uses `Database.insert(records, false)` for partial-success DML and populates `PRM_FailedRecordStaging__c` for per-row failures. Each fires `PRM_ExceptionLogEvent__e` (a Platform Event with `publishBehavior = PublishImmediately`) for transaction-level exceptions so they survive rollback.

The `NetworkCreationRequested__e` Platform Event carries: `CaseManagerId__c`, `PersonContactId__c`, `FacilityPractitionerTxNw__c`, `IsActive__c`, `IsPending__c`, `EffectiveFrom__c`, `EffectiveTo__c`, `RecordsToUpdate__c`, `RequestId__c`.

### The following infrastructure is being built for Practitioner Creation and costs zero additional effort for PDM Manual Update:
- `NetworkCreationRequested__e` Platform Event and all its fields
- `PRM_NetworkCreationEventTrigger`
- `PRM_NetworkCreationOrchestrator` (with `handleEvent()` and `queueNetworkCreation()`)
- `PRM_NetworkCreationRemote.publishNetworkCreationEvent()`
- `PRM_ExceptionLogEvent__e` schema (with `PRM_RecordId__c`, `PRM_RecordObjectName__c`)
- `PRM_ExceptionLogEventTrigger`
- `PRM_ExceptionLogger.logExceptionViaEvent()`
- `PRM_OmniUtils` caseManagerId routing
- `PRM_FailedRecordStaging__c` custom object and all its fields
- `PRM_NetworkCreationStatus__c` picklist on CaseManager/IndividualApplication
- `PRM_NetworkCreationError__c` long text field on CaseManager
- Data Admin list views and the "Mark Resolved" Quick Action

### The PDM Manual Update problem you are designing for

PDM Manual Update - Practitioner is a separate OmniScript and IP chain that handles manual updates to existing practitioner records. It has the same structural shape as the Creation chain (a container IP invoking child IPs in sequence) but operates in upsert/update mode. It hits the same governor limits for the same reasons. The stakeholder has directed that the IP-based approach — including any Queueable IP variant — will not work at scale, and the design must migrate fully to Batch Apex using the framework already being built.

### Key UPDATE-mode differences you must address explicitly

1. **DML mode is upsert, not insert.** Records are keyed by external IDs (NPI, composite keys). The batch `execute()` methods must issue `Database.upsert(records, externalIdField, false)` rather than `Database.insert`.

2. **Stale record cleanup is required.** After updating a practitioner's networks, network records that no longer apply (e.g., a payer network association removed in the update) must be deactivated or deleted. The batch classes must compute a delta between the incoming desired state and existing records before performing DML.

3. **UPDATE batches are more idempotent than CREATE batches.** A re-run of the update batch converges on the same end state without creating duplicates. This is a meaningful advantage for retry safety that must be called out in exception handling design.

4. **Existing record queries add SOQL cost before DML.** Each `execute()` call must first query existing records to compute the delta. This SOQL cost is the primary reason Queueable IPs cannot handle this — they hit SOQL 100 before the DML even starts. Batch Apex's per-execute() governor reset is the solution.

5. **Mode parameter decision.** You must make and document one of the following architectural decisions:
   - **Option A:** Add a `mode` parameter (`INSERT` vs `UPSERT`) to the existing Practitioner Creation batch classes (`PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`) and branch DML logic internally. This minimizes class proliferation and keeps the framework unified.
   - **Option B:** Create separate PDM-specific batch classes (`PDM_TaxonomyNetworkUpdateBatch`, `PDM_PayerNetworkUpdateBatch`, `PDM_IFCRecordUpdateBatch`) that extend or mirror the Creation classes but contain update-specific logic cleanly.
   Document the trade-offs of each (code reuse vs. separation of concerns, complexity in shared class vs. duplication risk in separate classes, testing surface area) and make a clear recommendation with rationale. Do not leave this as an open question.

---

## STEP 3 — WRITE THE DOCUMENT

Save the output to:
`/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/TDD_PDMManualUpdate_Practitioner_IPToApex.md`

The document must be a High Level Technical Design Document in Markdown. It must contain exactly these 12 sections, in order. Do not skip or merge any section.

---

### Section 1: Executive Summary

Explain in plain terms why the IP-based approach — including the Queueable IP variant documented in `TDD_PractitionerCreation.txt` — is insufficient for PDM Manual Update at scale. Explain what the full migration to Batch Apex achieves. Explain how the Practitioner Creation batch framework is the foundation being leveraged, and how this document designs the PDM-specific layer on top of it. Keep to 3–5 paragraphs. No bullet lists in this section.

---

### Section 2: Why IPs Cannot Handle This

This section must be a detailed technical argument, not marketing language. Cover:
- Specific governor limits that are breached: SOQL 100 (synchronous), SOQL 200 (async/Queueable), CPU 60s async, Heap 12MB async
- The specific operation count for PDM Manual Update: the existing record queries (to compute delta) add SOQL cost on top of the creation cost, making the total per-transaction operation count exceed even the elevated Queueable limits
- Why OmniStudio has no native partial-success DML (all-or-none rollback by default under `rollbackOnError = true`) and why this is worse for update mode than for create mode (a failed update with rollback leaves stale data that looks valid)
- Why Queueable chaining (the TX2 → TX3 pattern from the old TDD) cannot be integration-tested in sandbox and creates an untestable blind spot
- Why the Batch Apex context (fresh governor limits per `execute()` call, up to 50 million records via `QueryLocator`, stateful accumulation via `Database.Stateful`) resolves every one of these problems

Include a table: Constraint | Queueable IP Limit | Batch Apex Context | PDM Manual Update Need

---

### Section 3: Scope

Define clearly:
- Which OmniScript is affected (the PDM Manual Update - Practitioner OmniScript)
- The IP chain structure: container IP name, child IP names, sequence, current invocation mode of each
- What each IP currently does (address/facility upserts, primary location logic, network/taxonomy/IFC record upserts) — derive this from reading `TDD_PractitionerCreation.txt` for the structural reference even though that TDD's solution is superseded
- What objects are read and written by each IP
- What is explicitly out of scope (the Practitioner Creation flow, the IP1/IP2 synchronous work that stays in the IP chain, other OmniScripts)

---

### Section 4: IP-to-Apex Migration Map

This is the critical section. Produce a detailed table with columns:

| IP Step | Step Name | What It Does | Current Location | Migration Decision | Target Class / Method | Rationale |

Populate every logical operation in the PDM Manual Update IP chain. For each row, the Migration Decision must be one of:
- **STAYS IN IP** — fast, synchronous, low-SOQL (address lookup, input validation, UI response assembly, Platform Event publish)
- **MOVES TO BATCH APEX** — heavy DML, large delta queries, network/taxonomy/IFC upsert or deactivation
- **MOVES TO @future / Queueable** — only if there is a genuine single lightweight async operation that does not need batch; justify explicitly

After the table, write a short narrative paragraph explaining the overall split: what IP now does (synchronous fast work + Platform Event publish), and what batch now does (all delta-heavy data work).

---

### Section 5: Proposed Batch Architecture

Provide a full architecture description including an ASCII or Mermaid diagram showing:
- The trimmed PDM Manual Update IP chain (container → synchronous child IPs → Platform Event publish via `PRM_NetworkCreationRemote`)
- The Platform Event `NetworkCreationRequested__e` (reused as-is, with a `mode` field or a separate event if your Section 4 decision requires it — be explicit)
- `PRM_NetworkCreationEventTrigger` → `PRM_NetworkCreationOrchestrator`
- The batch chain: Taxonomy batch → Payer Network batch → IFC batch
- The status progression on CaseManager
- Email notification on completion or failure

If you chose Option A (mode parameter), show how the orchestrator passes the mode through. If you chose Option B (separate classes), show the parallel class hierarchy. Be consistent with your Section 4 decision.

---

### Section 6: Batch Class Designs

For each batch class needed for PDM Manual Update, provide a full design specification. If you chose Option A, document the mode-extended version of each existing class. If you chose Option B, document each new class in full.

For each class, cover:
- **Class name** and whether it is new or a mode-extended version of a Practitioner Creation class
- **`start()` SOQL query** — what it queries, why, and how it scopes to the right practitioner/case manager
- **`execute()` logic** — delta computation (existing records query, set difference, deactivation list vs. upsert list), upsert DML with `Database.upsert(records, externalIdField, false)`, stale record deactivation or deletion logic, per-row failure handling
- **`finish()` logic** — status update on CaseManager, chain to next batch via `Database.executeBatch()`, or send email notification on final batch
- **Batch size recommendation** — provide a specific number and show your reasoning (e.g., at batch size 5, the execute() call processes N locations × M networks = P DML rows, plus Q delta queries, well within the 200-query and 10,000-DML-row-per-execute limits)
- **How `PRM_FailedRecordStaging__c` is populated** — show the exact fields set for a failed upsert row (TargetObject, Payload as JSON of the failed sObject, ParentRecordId, ErrorMessage, StatusCode, FieldName, SourceProcess, BatchJobId, TransactionId)

---

### Section 7: IP Simplification Plan

Show the before and after state of the PDM Manual Update IP chain as two explicit element lists.

**Before (current state):** List every active IP element in the container and child IPs, with sequence number, element type, and what it does.

**After (trimmed state):** List every active IP element that remains, with sequence number, element type, and what it does. The trimmed IP should contain only: synchronous address/facility/location upsert work, input validation steps, and the Remote Action call to `PRM_NetworkCreationRemote.publishNetworkCreationEvent()`. All heavy data work must be absent from this list.

Explicitly mark the element that replaces the old network creation call with: "NEW — Remote Action: `PRM_NetworkCreationRemote.publishNetworkCreationEvent()` — publishes `NetworkCreationRequested__e`, returns immediately with Processing status."

---

### Section 8: Reuse From Practitioner Creation

Produce a table with columns:

| Component | Reuse Type | Effort for PDM | Notes |

Populate every shared component. Reuse Type values:
- **Direct** — used exactly as built, zero changes
- **Mode-Extended** — same class, new parameter branch (if Option A was chosen)
- **Reference** — PDM writes to the same object or calls the same method but does not modify the component

Effort values: **0** (zero effort, already built), **S** (small, hours), **M** (medium, days).

After the table, add a sentence summarizing the total effort saved by reusing the framework (e.g., "X of Y components are zero-effort reuse, saving an estimated Z story points compared to building PDM from scratch.").

---

### Section 9: Exception Handling

Cover exception handling for the PDM Manual Update batch classes specifically. Address:
- Per-row failures: how `Database.upsert(records, false)` results are inspected, and how each failed row produces a `PRM_FailedRecordStaging__c` record with full payload JSON and error detail
- Transaction-level exceptions (uncaught Apex exceptions in `execute()`): how `PRM_ExceptionLogEvent__e` is fired via `PRM_ExceptionLogger.logExceptionViaEvent()` so the log survives any implicit rollback
- Status field progression on failure: `PRM_NetworkCreationStatus__c = "Failed"` and `PRM_NetworkCreationError__c` populated
- Email notification to the submitting user when the final batch completes (success or failure)
- **UPDATE-specific retry safety**: explain why upsert-mode batch classes are intrinsically safer to retry than insert-mode classes (idempotency — re-running an update batch converges on the correct end state, whereas re-running an insert batch without deduplication creates duplicate records). Call out what the delta-computation logic in `execute()` does that makes retry safe.
- How the Data Admin list views and "Mark Resolved" Quick Action already being built for Practitioner Creation apply unchanged to PDM Manual Update failures

---

### Section 10: Implementation Timeline

Present a sprint-by-sprint plan using 2-week sprints.

Hard dependency to state explicitly: The Practitioner Creation batch framework (`NetworkCreationRequested__e`, `PRM_NetworkCreationOrchestrator`, `PRM_TaxonomyNetworkBatch`, `PRM_PayerNetworkBatch`, `PRM_IFCRecordBatch`, `PRM_FailedRecordStaging__c`) must be deployed to QA and pass integration tests before PDM net-new development begins. Any sprint plan that ignores this dependency is invalid.

Structure the timeline as:
- Sprint N (or "Pre-requisite"): Practitioner Creation framework deployment to QA
- Sprint N+1: [PDM work]
- Sprint N+2: [PDM work]
- etc.

Include a total elapsed weeks row at the end.

---

### Section 11: Effort Estimation Table

Produce a table with columns:

| Component | Category | Story Points | Est. Days | Owner Role |

Categories: **Reused (0 effort)**, **Mode-Extended**, **New Development**, **Testing**, **Configuration / Metadata**.

Include a Totals row. Below the table, add a paragraph explicitly calling out how much effort is saved by framework reuse (compare net-new story points vs. total if built from scratch). Reference the specific components in Section 8 that are zero-effort.

---

### Section 12: Definition of Done

A bulleted checklist. Every item must be a verifiable, binary pass/fail criterion. The checklist must include at minimum:

- All PDM Manual Update IP chain elements that previously called network/taxonomy/IFC creation logic have been removed or deactivated
- The trimmed IP chain contains only synchronous address/facility/location upsert work and the Platform Event publish step
- The Platform Event publish returns to the UI in under 3 seconds for a practitioner with 5+ practice locations
- All heavy DML (taxonomy network upsert, payer network upsert, IFC record upsert, stale record deactivation) executes in Batch Apex, not in any IP or Queueable
- Unit test coverage is 90% or higher on all new or mode-extended batch classes
- Integration tests pass for single-location update, 3-location update, and 5+ location update
- Delta computation correctly identifies and deactivates stale records (test: update a practitioner removing one network association, verify the stale record is deactivated after batch completes)
- Failure injection tests pass: forced DML failure in `execute()` produces `PRM_FailedRecordStaging__c` records and fires `PRM_ExceptionLogEvent__e`
- `PRM_NetworkCreationStatus__c` on CaseManager correctly progresses through all states and lands on `Completed` or `Failed`
- Email notification is sent to the submitting user on batch chain completion
- UAT sign-off obtained from Network Maintenance team
- No regression in Practitioner Creation flow (shared components must pass both creation and update integration tests)
- Data Admin list views surface PDM Manual Update failures with the same tooling used for Practitioner Creation failures

---

## STYLE AND QUALITY REQUIREMENTS

- Write in precise technical English. No marketing language. No filler.
- All class names, field names, object names, and IP names must match exactly what appears in the source files you read. Do not invent names.
- All governor limit numbers must match the source files exactly (SOQL 100 synchronous, SOQL 200 async, CPU 60,000ms async, Heap 12MB async, per-batch execute limits).
- The mode parameter decision (Option A vs. Option B) must be made once and held consistently across Sections 4, 5, 6, 7, 8, and 11. Do not waffle or say "either approach could work."
- The document should be long enough to be actionable — a developer should be able to open it and start building without needing to ask questions. But do not pad. Every sentence must carry information.
- Format: Markdown. Use `##` for sections, `###` for subsections, fenced code blocks for any Apex sketches or SOQL, and pipe tables for all tables.

---

## OUTPUT

Write the complete document and save it to:
`/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/TDD_PDMManualUpdate_Practitioner_IPToApex.md`

Do not produce any other output. Do not summarize what you are about to do. Read the files, make your decisions, write the document, save it.
