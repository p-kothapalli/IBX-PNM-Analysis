# USER STORY: Mass Upload — Delegated Practitioner Fallout Report

**Persona:** PDM Specialist
**Priority:** P1
**GUS Requirement:** TBD — Mass Updates / PDM swimlane
**OmniScript:** N/A for delivery. **Parity source:** `PRM_PractitionerCreation_English` v27 (Delegated) and its validation rules
**Integration Procedures:** N/A
**Grounding:** `PRM_StandardDelegatedRosterImportTemplate.xlsx` (Import Template · Request Types · Field Dictionary), `Validation-PractitionerCreation.xlsx` (11 sheets), `docs/implementation-plan/PRM_RosterUpload_UI_DesignPlan.md`
**Relevant Requirements:** #1486103 (*Initial Validation*), #1487020 (*API Validation — NPPES, Precisely*), #1487028 (*System Validation*), #1488089 (*Import*), #1490648 (*Add Location / All Location*)
**Story boundary:** each upstream story decides **whether** a row proceeds. **This story is the single place a specialist learns why a row did not**, across every stage, in a form they can correct and re-upload.

---

## Story

**As a** PDM Specialist,
**I want** a Case raised under the Async Job whenever an upload has fallout, with the fallen-out practitioner details and their reasons attached as a CSV in the layout of the file I submitted,
**So that** the fallout is owned, assignable and worked like any other Case, and I can correct the roster and re-submit it without reconstructing what happened from job records — and rows that need a different process, such as a terminated location needing reinstatement, are routed rather than silently lost.

**Why it matters:** A delegated roster can fail at any of five stages, each currently reporting somewhere different. Without one consolidated report the specialist cannot tell whether a practitioner is missing because a field was malformed, the registry rejected the NPI, the group was ambiguous, the location is terminated, or a batch step failed — and a partially-loaded roster silently under-reports the network.

---

## Scope

| Flow | Surface | Affected Step | Data Source |
|------|---------|--------------|-------------|
| Mass Upload — Delegated Practitioner | **Fallout Case under the Async Job, with the fallout CSV attached** | After validation and after async execution | Fallout records captured at every stage |

**Request types in scope (12):** `CREATE_PROVIDER`, `CREATE_GROUP`, `ADD_TO_LOCATION`, `ADD_TO_ALL_LOCATIONS`, `REMOVE_FROM_LOCATION`, `ADD_NETWORK`, `TERM_NETWORK`, `CHANGE_DEMOGRAPHIC`, `CHANGE_SPECIALTY`, `CHANGE_GROUP`, `CHANGE_TIN`, `CHANGE_ADDRESS`.

**In scope:** capturing a fallout reason at every stage; the reason-code taxonomy; the terminated-location routing case; **the Case raised under the Async Job and the CSV attached to it**; the report in the import-template layout; the correction round-trip.

**Out of scope:** the validation rules themselves (they belong to the upstream stories); automatic reinstatement; automatic retry of a failed batch step; the in-wizard pre-submit triage grid, which is the design plan's §6.1 surface and the live counterpart to this post-run report.

---

## Current State (from the template, the rules workbook and the codebase)

### The import template

106 columns across three sheets. Fifteen are control columns — Request Type, Request Notes, Termination Scope, Termination Date, Termination Reason, Network(s), Change Field, Old Value, New Value, Practitioner Ref, Group Ref, Practice Location Ref, Vendor Ref, Contract / PO, Group Parent — and the remaining 91 carry practitioner, group, address, credential and inclusive-care data. The Ref columns accept an IBX internal id (PIE/BSPA) **or the literal `CREATE`**. The dictionary sets the grain: *"One row = one operation; a provider at N locations = N rows."*

> **Gap:** the Request Types sheet defines **11** types. `ADD_NETWORK` is in scope for this story but is **not** defined there — the Field Dictionary references it only as "ADD_* (optional network apply)" on the Network(s) column (Clarification Q1).

### The validation rules workbook

| Sheet | Contributes |
|---|---|
| Practitioner Rules | 9 rules with final message text, e.g. *"The NPI entered is already associated with a Practitioner, please update Practitioner through PDM Manual Updates guided flow."* and *"The Practitioner is currently being Credentialed. Case Manager %ExistingCaseManagerNumber%"* |
| Group | Practice Location NPI `^\d{10}$`; Tax ID `^\d{9}$`; Account Name resolved by `PRM_PractitionerCreationUtility.getGroupData` on NPI + Tax ID; *"Please input a valid Group NPI Number associated with the Group Name provided."* |
| Address | ~50 field specs plus duplicate-practice-location, Precisely-unavailable, delegated-info-code, accessibility-capability and patient-age-range rules |
| Normalize Value | Canonical shapes — NPI 10 digits, Tax ID 9, Zip 5, Zip+4 4, phone up to 10 with a leading US 1 dropped, extension optional hyphen plus 1–6 digits |
| RequiredSections | Which sections are required per scenario (New / New Group+Location / New Location) |
| Roles & Networks | Role is PCP or Specialist; *"Please select networks to proceed."* |

Two rules are marked **"Need to discuss"** in the sheet — *NPI already has a practitioner* and *Practitioner mid-credentialing*. #1487028 already resolved mid-credentialing as **proceed with a Warning**, so this story follows #1487028 and the sheet is treated as superseded (Clarification Q2).

The sheet also self-reports two defective specs: the Mailing Phone Extension pattern is *"unsatisfiable"* and the Group NPI message is *"placeholder text"*. Neither can produce a usable fallout reason as written (Clarification Q3).

### Why a terminated location cannot be handled in bulk

Reinstatement is a **separate guided process** with its own OmniScripts — `PRM_PracticeLocationReinstate_English`, `PRM_PractitionerReinstateForm_English`, `PRM_PractitionerReinstateVendorForm_English`, `PRM_ReinstateLinkExistingPractitioner_English` — plus the `prmReinstatePractitionerPracticeLocation` component. A roster row pointing at a terminated location therefore cannot be completed by the upload; it must fall out with an explicit pointer to that process.

### What already exists to build on

`PRM_FailedRecordStaging__c` carries the fields a fallout store needs: `PRM_SourceFlow__c`, `PRM_Status__c`, `PRM_ErrorMessage__c`, `PRM_ExceptionLog__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_CaseManager__c`, `PRM_AsyncJobDetails__c`, `PRM_RequestPayload__c`, `PRM_RetryCount__c`, `PRM_LastRetriedAt__c`. It is already written to by `PRM_CSVJobCreationQueueable` on a payload failure. It has **no file-row-number field**, which this story adds (AC-3).

### The Case under the Async Job — what exists and what does not

**There is no relationship between Case and the Async Job today.** `PRM_AsyncJob__c` has only four custom fields — `PRM_ProcessName__c`, `PRM_Status__c`, `PRM_SubType__c`, `PRM_TotalRecordsCreated__c` — and `Case` carries no async-job, upload or roster lookup. Raising a Case "under the Async Job" therefore requires a **new lookup** (AC-4, Clarification Q4).

The **file-attachment pattern is already established** and should be reused verbatim. `PRM_JsonJobUploadService.attachPayload` inserts a `ContentVersion` (Title, PathOnClient, VersionData), re-queries it for its `ContentDocumentId`, then inserts a `ContentDocumentLink` with `LinkedEntityId` set to the record, `ShareType = 'V'` and `Visibility = 'AllUsers'`. The fallout CSV is attached to the Case the same way.

---

## Acceptance Criteria

> Pattern A (behavioural) unless marked. AC-4 is Pattern E (the fallout record); AC-5, AC-7 and AC-13 are Pattern D (rules); AC-2 is Pattern B (report columns).

### The report

**AC-1 — A Case is raised under the Async Job with the fallout CSV attached**

**Given** an upload in which at least one row did not process,
**When** the upload reaches its end state,
**Then** a Case is created and related to that upload's Async Job,
**And** the fallout practitioner details and their reasons are attached to that Case as a CSV file,
**And** the CSV contains one row for every source row that did not process, with rows that processed successfully absent,
**And** the Case is reachable from the Async Job and the Async Job from the Case.

**AC-1a — One Case per upload, not per failure**

**Given** an upload whose rows failed at several different stages,
**When** the fallout Case is raised,
**Then** exactly one Case exists for that upload carrying every fallen-out row in one attached CSV,
**And** a later processing failure on the same upload updates that Case and its attachment rather than raising a second Case.

**AC-2 — Columns of the attached fallout CSV** *(Pattern B — report specification)*

The CSV attached to the fallout Case has these columns, in order:

- **Source Row Number** — the row's position in the uploaded file, so the specialist can find it in their own sheet
- **Request Type** — as supplied on the row
- **Practitioner** — first and last name as supplied
- **Individual NPI** — as supplied
- **Group Name / Group NPI / Tax ID** — as supplied
- **Practice Location** — the address or location reference as supplied
- **Stage** — where it fell out: Field Validation, Registry Validation, Address Standardization, System Validation, Import, or Processing
- **Reason Code** — the controlled code (AC-5)
- **Reason** — the business message
- **Matched Record** — the existing record involved, where there is one
- **Next Action** — what the specialist should do, including the process to use when it is not this one
- **Every original column from the import template**, unchanged, so the file can be corrected and re-uploaded (AC-13)

**AC-3 — Original values are preserved exactly**

**Given** a row that fell out after its values were normalized or standardized,
**When** the fallout report is produced,
**Then** the report shows the values **as the specialist supplied them**, not the normalized or standardized forms,
**And** where a value was changed before the failure, the changed value is shown alongside for reference.

**AC-4 — Records created when an upload has fallout** *(Pattern E)*

**Given** any row that fails at any stage,
**When** the failure is captured and the upload reaches its end state,
**Then** the following records are created exactly as specified, in this order:

**Fallout Record — Create (one per failed source row per stage)**

| Field | Value | Notes |
|---|---|---|
| Source Flow | Mass Upload — Delegated Practitioner | identifies the originating process |
| Status | Failed | |
| Upload / Job reference | {The upload's Async Job, where one exists} | blank for pre-import failures |
| Job Step | {The step that failed} | blank unless the failure occurred during processing |
| Source Row Number | {Row position in the uploaded file} | **new field** — the object has no row-number field today |
| Request Type | {Request Type on the row} | |
| Stage | {Field Validation / Registry Validation / Address Standardization / System Validation / Import / Processing} | |
| Reason Code | {Controlled reason code} | per AC-5 |
| Error Message | {Business message} | text from the validation rules |
| Target Object | {The record type the row was trying to create or change} | |
| Parent Record | {The resolved existing record, where one was found} | |
| Case Manager | {Case Manager for the practitioner, where one exists} | correlation for the progress view |
| Request Payload | {The row as submitted} | supports the corrected-file export |
| Exception Log | {Link to the technical log, for processing failures} | blank for validation failures |
| Retry Count | 0 | |

**Fallout Case — Create (one per upload that has any fallout)**

| Field | Value | Notes |
|---|---|---|
| Record Type | Mass Upload Fallout | new record type — see Clarification Q4 |
| Async Job | {The upload's Async Job} | **new lookup** — no Case-to-Async-Job relationship exists today |
| Subject | Mass Upload fallout — {Source file name} — {N} of {M} rows | counts reconcile with AC-12 |
| Description | {Per-stage and per-reason-code summary of the fallout} | the same counts shown on screen |
| Status | New | |
| Origin | Mass Upload | |
| Owner | {Queue or user per the assignment rule} | see Clarification Q4 |
| Priority | {Derived from the fallout volume} | see Clarification Q11 |

**Fallout CSV — Create (one per fallout Case)**

| Field | Value | Notes |
|---|---|---|
| Title | Mass Upload Fallout — {Source file name} — {Upload date} | |
| Path On Client | {Same title}.csv | |
| Content | {The fallout rows and their reasons, columns per AC-2} | supplied values, not normalized (AC-3) |
| Linked To | {The fallout Case} | attached with the same share and visibility settings the framework already uses for the job payload |

**And** the CSV is attached to the Case, not to the Async Job, so the specialist works the fallout from the Case.

### Reasons

**AC-5 — Reason-code taxonomy** *(Pattern D — rules)*

Every fallout carries a controlled reason code alongside the business message, so reasons can be counted and trended across uploads. Codes are grouped by stage:

- **Field Validation** — a required field is missing; a value fails its format rule (NPI not 10 digits, Tax ID not 9, ZIP not 5); a value does not resolve to a known list entry (specialty, degree, practitioner type, role); a conditional section required for the row's scenario is absent.
- **Registry Validation** — the NPI is not found in the national registry; the registry name does not match the row; the registry was unreachable.
- **Address Standardization** — the address could not be standardized; the standardization confidence was below the threshold; the standardization service was unavailable.
- **System Validation** — the NPI already belongs to a practitioner; the group could not be resolved; the group resolved ambiguously and was not confirmed; the location resolved ambiguously; a value conflicts with the existing record; the same value conflicts across rows in the file.
- **Import** — the row's practitioner could not be packed into a payload; job creation failed for the payload containing this row.
- **Processing** — a batch step failed for this record; the chain halted before this record's step ran.
- **Not Supported In Bulk** — the requested operation exists but must be performed in another process (AC-6).

Each code carries a fixed business message and a fixed Next Action. Codes are held in configuration so a new reason does not require a deployment.

**AC-6 — A terminated location is reported as routable, not as a generic error**

**Given** a row whose target practice location is terminated,
**When** the row is evaluated,
**Then** it falls out with the reason code for an operation that cannot be completed in bulk,
**And** the reason names the terminated location and states that a terminated location cannot be reinstated through an upload,
**And** the Next Action directs the specialist to the reinstatement process,
**And** the row is not counted as a data error, so genuine data defects remain distinguishable in the reason counts.

**AC-7 — Request-type-specific reasons** *(Pattern D — rules)*

A row is evaluated against the rules for its own Request Type, and the fallout reason reflects that type.

| Request Type | Reasons specific to it |
|---|---|
| `CREATE_PROVIDER` | practitioner already exists; credentialing already in flight; required credential section missing |
| `CREATE_GROUP` | group already exists for the Tax ID and Group NPI; Primary, Billing or Mailing address missing |
| `ADD_TO_LOCATION` | practitioner, group or location reference does not resolve; location terminated |
| `ADD_TO_ALL_LOCATIONS` | group does not exist; group has no active location; a location reference was supplied and ignored |
| `REMOVE_FROM_LOCATION` | no active affiliation to end; Termination Scope, Date or Reason missing or invalid |
| `ADD_NETWORK` / `TERM_NETWORK` | network not recognised; no active membership to end; network already present |
| `CHANGE_DEMOGRAPHIC` / `CHANGE_SPECIALTY` / `CHANGE_GROUP` / `CHANGE_TIN` / `CHANGE_ADDRESS` | Change Field, Old Value or New Value missing; Old Value does not match the stored value; the target of the change does not resolve |

- A Request Type not recognised by the template falls out with a Field Validation reason naming the supplied value.
- A row is never evaluated against another type's required fields.

**AC-8 — A row with several problems reports all of them**

**Given** a source row that fails more than one rule,
**When** the fallout report is produced,
**Then** every distinct reason for that row is reported,
**And** the row still appears once in the report, with its reasons listed together,
**And** the stage shown is the earliest stage at which it failed.

### Coverage across stages

**AC-9 — Failures from every stage reach the report**

**Given** an upload in which rows failed at field validation, at registry or address validation, at system validation, at import, and during processing,
**When** the fallout report is produced,
**Then** every one of those rows appears with its correct stage and reason,
**And** no stage's failures are reported only in job records or logs.

**AC-10 — A held practitioner's other rows are reported too**

**Given** a practitioner blocked at any stage who appears on several rows of the file,
**When** the fallout report is produced,
**Then** every row for that practitioner appears,
**And** the rows held only because the practitioner was blocked state that as their reason rather than repeating the original error as though each row failed independently.

**AC-11 — A wholly successful upload raises no Case**

**Given** an upload in which every row processed,
**When** the upload reaches its end state,
**Then** no fallout Case is created and no CSV is attached,
**And** the upload is shown as fully processed with its row count.

**AC-12 — Counts reconcile**

**Given** any completed upload,
**When** the specialist views its summary or the fallout Case,
**Then** the rows processed plus the rows in the attached CSV equal the rows submitted,
**And** the Case subject states the same counts,
**And** the summary shows a count per stage and per reason code.

### Correction round-trip

**AC-13 — The report is a correctable file** *(Pattern D — rules)*

- The export carries **every column of the import template in its original order**, so a corrected copy can be re-uploaded without re-keying.
- The diagnostic columns (Source Row Number, Stage, Reason Code, Reason, Matched Record, Next Action) are **additional** and positioned so they do not disturb the template's column order.
- The upload accepts a file that still carries the diagnostic columns and **ignores them**, so the specialist can correct and re-submit the downloaded file directly.
- The export preserves the supplied values, not the normalized ones (AC-3), so re-uploading an uncorrected file reproduces the same fallout rather than silently changing behaviour.
- Rows that are informational only — for example a practitioner held because another row blocked them — are included, so the corrected file is complete.

**AC-14 — A corrected file is a new upload**

**Given** a specialist re-uploads a corrected fallout export,
**When** it is submitted,
**Then** it is processed as a new upload with its own validation, jobs and fallout report,
**And** the original upload's fallout report is unchanged,
**And** rows that already processed successfully in the original upload are not duplicated, because they are absent from the corrected file.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FailedRecordStaging__c` | Modified object | Add **Source Row Number**, **Request Type**, **Stage**, **Reason Code**, **Upload reference**, **Next Action** | Drives AC-4. The object has none of these today |
| `PRM_MassUploadReasonCode__mdt` | **New** Custom Metadata | Reason code → stage, business message, Next Action, bulk-supported flag | Drives AC-5, AC-6. Configuration so new reasons need no deployment |
| `PRM_CSVFalloutRecorder` | **New** Apex class | Single entry point every stage calls to record a fallout, ensuring consistent stage and reason capture | Drives AC-4, AC-9 |
| `PRM_CSVFalloutCaseService` | **New** Apex class | Raises the one fallout Case under the Async Job, builds the CSV, attaches it, and updates both on a later failure | Drives AC-1, AC-1a, AC-4, AC-11. Reuses the `attachPayload` ContentVersion + ContentDocumentLink pattern |
| `Case.PRM_AsyncJob__c` | **New** field | Lookup from Case to `PRM_AsyncJob__c` | Drives AC-1. **No Case-to-Async-Job relationship exists today** |
| Case record type + assignment | **New** config | A Mass Upload Fallout record type, page layout and owner/queue assignment | Drives AC-4; see Clarification Q4 |
| `PRM_CSVFalloutReportController` | **New** Apex class | Assembles the report for an upload: joins fallout records to their source rows and returns the export | Drives AC-2, AC-3, AC-12 |
| `PRM_CSVFalloutExportBuilder` | **New** Apex class | Emits the import-template column set plus the diagnostic columns as the attached CSV | Drives AC-2, AC-13 |
| `PRM_CSVRowValidator` / API validation / System validation / create-vs-reuse | Modified Apex | Each records fallout through the recorder rather than its own shape | Drives AC-9 |
| `PRM_CSVJobCreationQueueable` | Modified Apex | Already writes to the staging object; extend it to carry row number, stage and reason code | Drives AC-9 (Import stage) |
| Batch step failure handling | Modified Apex | Processing-stage failures recorded per affected record, not only per job | Drives AC-9 (Processing stage) |
| `PRM_CSVStandardTemplate` | Modified Apex | Add `ADD_NETWORK` to the recognised Request Types alongside the other 11 | Drives AC-7; see Clarification Q1 |
| `prmCsvJobUpload` | Modified LWC | Surface the fallout summary, per-stage and per-reason counts, and the download action | Drives AC-11, AC-12 |

**Grounding notes for the developer:** the terminated-location Next Action points at the reinstatement OmniScripts named in Current State. Group resolution messages come from `PRM_PractitionerCreationUtility.getGroupData` behaviour as specified in #1487028. Normalized versus supplied values follow the Normalize Value sheet — the report must retain the supplied form.

---

## Definition of done

- [ ] An upload with fallout raises exactly one Case related to its Async Job, with the fallout CSV attached to that Case (AC-1)
- [ ] The Case is reachable from the Async Job and the Async Job from the Case (AC-1)
- [ ] A later processing failure on the same upload updates the existing Case and attachment instead of raising a second Case (AC-1a)
- [ ] Every row in the attached CSV carries the source file's row number and matches that row in the uploaded sheet (AC-1, AC-2)
- [ ] Rows that fell out after normalization show the values as supplied, not normalized (AC-3)
- [ ] A row failing at each of the six stages appears with the correct stage and reason (AC-9)
- [ ] A row with several problems appears once with all its reasons and the earliest stage (AC-8)
- [ ] A terminated-location row reports the bulk-unsupported reason code, names the location, and points to the reinstatement process (AC-6)
- [ ] A terminated-location row is excluded from the data-error counts (AC-6)
- [ ] Each of the 12 request types produces its own type-specific reasons, and an unrecognised type falls out naming the supplied value (AC-7)
- [ ] A blocked practitioner's other rows are reported as held rather than each repeating the original error (AC-10)
- [ ] Rows processed plus rows in the fallout report equal rows submitted, for every upload (AC-12)
- [ ] An upload with no failures raises no Case and attaches no CSV (AC-11)
- [ ] The Case subject's counts match the attached CSV's row count and the upload's processed count (AC-12)
- [ ] The exported file re-uploads without editing the column layout, and the diagnostic columns are ignored on re-upload (AC-13)
- [ ] Re-uploading an uncorrected export reproduces the same fallout (AC-3, AC-13)
- [ ] A new reason code is added in configuration and appears in the report without a deployment (AC-5)
- [ ] ≥ 85% Apex coverage on the recorder, controller and export builder, including a multi-stage upload, a multi-reason row and an empty-fallout upload

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | `ADD_NETWORK` is in scope but absent from the template's Request Types sheet. Should the template be updated, and what are its required fields? | AC-7 cannot specify its reasons without them | BA / Product |
| 2 | The validation sheet marks *mid-credentialing* as blocking with "Need to discuss", while #1487028 decided it proceeds with a Warning. Confirming #1487028 supersedes the sheet. | Changes whether those rows appear in fallout at all | BA |
| 3 | The sheet flags two defective specs — the Mailing Phone Extension pattern is "unsatisfiable" and the Group NPI message is "placeholder text". What are the intended values? | Neither can produce a usable fallout reason as written | BA / Technical |
| 4 | **What Case record type, owner/queue and assignment rule should the fallout Case use?** No Case-to-Async-Job relationship exists, so the lookup, record type and layout are all new. | Blocks AC-1 and AC-4 — the Case cannot be created without them | BA / Ops / Technical |
| 4a | Should the fallout Case follow an existing PDM case lifecycle (status values, closure rules), or its own minimal lifecycle? | Determines the Case status model and when it closes | BA / Ops |
| 4b | When a corrected file is re-uploaded, should the original fallout Case be closed automatically, linked to the new upload's Case, or left to the specialist? | Connects AC-14 to the Case lifecycle | BA / Ops |
| 5 | Should the fallout Case notify its owner on creation, or only appear in the queue? | Adds a notification path | Product |
| 6 | How long are fallout records and their reports retained, and does the existing cleanup batch cover them? | Interacts with the retention setting | Product / Technical |
| 7 | Should fallout be reported at the practitioner level as well as the row level, matching the design plan's triage grid? | Affects whether a second grouping view is needed | Product |
| 8 | For `REMOVE_FROM_LOCATION` with scope GROUP or CONTRACT, is a last-man-standing outcome a fallout reason or an informational one? | Determines whether those rows block | BA / Ops |
| 9 | Should the report distinguish a row that was never attempted (the chain halted earlier) from one that was attempted and failed? | Affects the Processing-stage reasons in AC-9 | BA / Technical |
| 10 | Who owns the reason-code list, and what is the process for adding one? | Determines whether AC-5's configurability is usable | Ops / BA |
| 11 | Should a terminated-location row optionally create the reinstatement case automatically rather than only pointing at the process? | Would extend AC-6 beyond reporting | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `Case` + new Async Job lookup | Object | **HIGH** | New lookup, record type, layout and assignment on a core object shared by every credentialing flow |
| `PRM_FailedRecordStaging__c` | Object | **HIGH** | New fields on an object already used as the async DLQ by other flows |
| Every upstream validation stage | Apex | **HIGH** | Each must record fallout through one recorder for AC-9 to hold |
| Batch step failure handling | Apex | **HIGH** | Processing failures must be attributable to a source row, not just a job |
| `PRM_CSVStandardTemplate` | Apex | MEDIUM | New request type recognised |
| `prmCsvJobUpload` | LWC | MEDIUM | Summary, counts and download |
| Reinstatement flows | OmniScript | LOW | Referenced as the Next Action; unchanged |
| Existing DLQ consumers | Apex | MEDIUM | Must tolerate the new fields and the new source flow value |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_FailedRecordStaging__c` field additions | Object | **M** | Six fields plus FLS on the access permission set |
| `PRM_MassUploadReasonCode__mdt` + seeded codes | CMDT | **L** | Taxonomy across six stages and 12 request types |
| `Case` lookup, record type, layout, assignment | Object + config | **L** | New relationship to `PRM_AsyncJob__c` on a core object |
| `PRM_CSVFalloutCaseService` | New Apex | **L** | Raise-or-update one Case, build and attach the CSV |
| `PRM_CSVFalloutRecorder` | New Apex | **L** | One capture path used by every stage |
| `PRM_CSVFalloutReportController` | New Apex | **L** | Assembly, counts, reconciliation |
| `PRM_CSVFalloutExportBuilder` | New Apex | **XL** | 106 template columns plus diagnostics, re-upload safe |
| Wiring each stage to the recorder | Modified Apex | **XL** | Five stages, each with its own current shape |
| Processing-stage attribution | Modified Apex | **L** | Map a batch failure back to its source row |
| `prmCsvJobUpload` summary + download | Modified LWC | **M** | Counts and export action |
| Apex tests | New tests | **XL** | Multi-stage, multi-reason, held-rows, empty-fallout, round-trip |

**Total Estimated Effort:** ~13–16 engineer-days — **XXL** overall. The cost is concentrated in wiring five differently-shaped stages into one consistent capture, and in an export that round-trips a 106-column template.
