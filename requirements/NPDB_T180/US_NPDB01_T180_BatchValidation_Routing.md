# US-NPDB-01 — T-180 Recred Batch: Route Practitioners With Incomplete Data to "NPDB Action Needed"

**Status:** Draft for business sign-off
**Created:** 2026-06-01
**Updated:**
- *2026-06-01 (v1)* — Initial draft (pre-template format).
- *2026-06-03 (v2)* — Rewrite to IBXQA 11-section template + linter-conformant appendix.
- *2026-06-03 (v3)* — Rewrite to **User Story Solution Architect v1.6** skill: business-language ACs (Pattern A/B/C), separate **Technical Implementation (high-level)** section, canonical workspace persona.
- *2026-06-08 (v4)* — Added **AC-1.7a** (validator returns `detailText` — a ready-to-display, link-free message) and a `Callable.call('validateForOmni', …)` entry point, so the US-NPDB-02 manual NPDB paths can render detailed in-OmniScript text messages instead of deep-link banners. Based on a component audit of `PRM_CallNPDB_English` and `PRM_IPCreateAdverseActionLog`.
**Author:** AI agent (with QA-sandbox evidence)
**Background investigation:** `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md`, `01_Architecture_Diagrams.md`
**Primary persona:** **Credentialing Specialist** — the credentialing operations role who triages recredentialing Case Managers in PIE. For Ancillary record types, the **Ancillary Cred Specialist** carries the same expectations.
**Sibling stories:** **US-NPDB-02** (manual NPDB request paths) and **US-NPDB-03** (operational report) consume the data model and behaviour delivered here.

> **How to read this story.**
>
> - **Business sign-off audience** — read Story, Why it matters, Preconditions, Acceptance Criteria. Stop at the Technical Implementation header.
> - **Developer audience** — same sections + Technical Implementation block + Definition of done.
> - **QA audience** — the Acceptance Criteria are the test scripts. Each Pattern-A AC has a Given/When/Then you can execute step-by-step; each Pattern-B/C AC is a schema or permission spec you can validate via Setup.

---

## Header

**Persona:** Credentialing Specialist (primary); Ancillary Cred Specialist (for Ancillary record types)
**Priority:** P0
**OmniScript:** N/A — batch-only story
**Integration Procedures:** N/A
**Relevant Requirements:** US-NPDB-02 (consumes the validator + new fields), US-NPDB-03 (reports on the new status); business NPDB-error backlog (May 2026)

---

## Story

**As a** Credentialing Specialist (or Ancillary Cred Specialist for Ancillary cases),
**I want** the nightly recredentialing batch to spot every practitioner whose underlying data is incomplete and route their Case Manager to a clearly-named **NPDB Action Needed** status on day one of the recredentialing window — instead of letting an NPDB request go out, fail at the integration 24 hours later, and silently sit in *Pending NPDB* for weeks,
**So that** my team can fix the underlying data problem the moment the recredentialing cycle opens, the NPDB integration never wastes a call on a practitioner we cannot complete, and our operational reports surface every blocked practitioner instead of hiding them behind a generic *Pending NPDB* label.

**Why it matters:** Today, the nightly recredentialing batch creates a Case Manager, a Case, and an Adverse Action Log for every Account whose recredentialing-due date falls inside the 180-day window — *whether or not the practitioner's Address, NPI, Business License, or Education data is even present*. The Adverse Action Log lands in *Ready To Process*, the NPDB integration polls it within 24 hours, the call fails, and the Case Manager sits in *Pending NPDB* for weeks. Operations only discovers the problem when a downstream report happens to be run, by which point the recredentialing window has shrunk. The existing in-flow null-address guard is silent and only covers one of the seven field groups, so it cannot be the system of record for "blocked because of data".

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|---|---|---|---|
| Recredentialing (T-180) nightly batch | N/A (batch) | Inside `processAccount` between CAQH-active check and `createActiveCAQHRecords` | `PRM_NpdbDataValidator` reading Account + Address + HealthcareProviderNpi + BusinessLicense + PersonEducation + (Ancillary) HealthcarePractitionerFacility |
| Recredentialing (T-180) nightly batch | N/A | Adverse Action Log insertion path | Suppressed for `NPDB Action Needed` Case Managers (existing `PRM_CheckCAQHExecuteHelper.initializeAdvActionLogRecord` not called) |
| Case Manager record page (post-batch) | N/A | Status field + linked Case status | New picklist value `NPDB Action Needed` on `IndividualApplication.Status` and `Case.Status` |
| Case Manager update (manual data fix) | N/A | After-update branch of `PRM_IndividualApplicationTriggerHandler` | New `PRM_NpdbActionNeededReleaseQueueable` re-runs the validator and auto-flips back to `Pending NPDB` when clean |

---

## Preconditions

- The Account is a practitioner (record type `PRM_Practitioner` or one of the Ancillary record types) whose recredentialing-due date falls inside the existing 180-day batch window.
- The Account is CAQH-active (no change to today's existing CAQH-active check).
- The nightly recredentialing batch is running on its existing schedule.

---

## Acceptance Criteria

> **Format reminder.** Pattern A (Given/When/Then) for behaviour. Pattern B (bulleted spec) for new fields, picklist values, and Custom Metadata Types. Pattern C (bulleted spec) for permission sets. No Apex class names, no SOQL, no picklist API values inside Given/When/Then — those move to the Technical Implementation table below.

### Nightly routing decision

**AC-1.1 — Routing happens silently inside the nightly batch**

**Given** the nightly recredentialing batch is running on its existing schedule,
**When** it picks up a practitioner whose recredentialing-due date is 180 days out and whose CAQH status is active,
**Then** the system silently decides, based on the practitioner's data on file, exactly one routing outcome,
**And** no Case Manager, Case, or Adverse Action Log is created or modified until that routing decision is made,
**And** the Credentialing Specialist sees no popup, no email, and no notification before the routing happens.

---

**AC-1.2 — Routing produces exactly one of three outcomes per practitioner**

**Given** the batch is evaluating a single practitioner,
**When** it inspects the practitioner's data on file,
**Then** the routing outcome is exactly one of the following and the system performs the listed actions atomically inside the batch transaction:

| Outcome | Trigger | What gets created / set | What does NOT happen |
|---|---|---|---|
| **Clean practitioner — proceed to NPDB** | All NPDB-required data is present per the field contract in §AC-1.7 | A new Case Manager is created in **Pending NPDB**. A matching Case is created in **Pending NPDB**. An Adverse Action Log is inserted in **Ready To Process** (today's existing flow, unchanged). | n/a |
| **Practitioner has incomplete data — block NPDB** | One or more NPDB-required fields are missing per §AC-1.7 | A new Case Manager is created in **NPDB Action Needed**. A matching Case is created in **NPDB Action Needed**. The Case Manager is stamped with a human-readable list of every missing field (which record, which field, severity). The "validation last run" timestamp is stamped on the Case Manager. | **No Adverse Action Log is inserted.** The NPDB integration never sees this practitioner this cycle. |
| **Batch-side exception on one practitioner** | The validator throws an unexpected exception on this practitioner | The Case Manager / Case / AAL state for this practitioner is rolled back. An error log row is written for Ops. The batch continues to the next practitioner. | The remaining practitioners in the same batch scope are unaffected. |

**And** in every outcome above, the batch returns to evaluate the next practitioner without any manual intervention.

---

**AC-1.3 — Status badge tells the story without the user opening anything**

**Given** the nightly batch has just routed a practitioner to **NPDB Action Needed**,
**When** a Credentialing Specialist opens that Case Manager record page the next morning,
**Then** the Status field shows **NPDB Action Needed** as the badge value,
**And** the Case linked to that Case Manager shows the same status,
**And** the existing recredentialing record-page layout does not regress (no field hidden, no button moved, no validation broken).

> _The field-level "fix this and this" banner ships in **US-NPDB-02**; this story only delivers the status itself and the underlying machine-readable findings._

---

**AC-1.4 — Newly-routed Cases route through the same queue as Pending NPDB Cases**

**Given** a new Case has just been created in **NPDB Action Needed** by the batch,
**When** the Case trigger fires for that Case,
**Then** the Case is routed to the same round-robin queue and applies the same ownership rules that today's *Pending NPDB* Cases follow,
**And** no new queue, no new owner-assignment rule, and no new approval-process entry is introduced.

---

### Auto-release when the underlying data is fixed

**AC-1.5 — Fixing the missing data releases the practitioner the same day**

**Given** a Case Manager is in **NPDB Action Needed** because (for example) the practitioner's primary Address Line 1 was blank,
**When** a Credentialing Specialist (or any other internal user with edit access) populates that missing field on the source record and saves,
**Then** within roughly five seconds the system re-runs the field check on its own — the Credentialing Specialist does not need to click any button — and if every NPDB-required field is now present, the Case Manager Status flips from **NPDB Action Needed** to **Pending NPDB**, the human-readable findings list on the Case Manager is cleared, and a fresh Adverse Action Log is inserted in **Ready To Process** so the NPDB integration picks it up on its next poll,
**And** if any required field is still missing, the Case Manager stays in **NPDB Action Needed** and the findings list is refreshed to reflect what's left.

---

**AC-1.6 — Idempotent re-release — duplicate Adverse Action Logs cannot be created**

**Given** an auto-release has just inserted an Adverse Action Log for a Case Manager and flipped its status,
**When** a second save lands on the same Case Manager before the next batch run (e.g., the user opens another field and saves a no-op),
**Then** no second Adverse Action Log is created,
**And** the Status stays at **Pending NPDB**,
**And** no error message is shown to the Credentialing Specialist.

---

### NPDB-required field contract (validation rules, business confirmed)

**AC-1.7 — NPDB-required data per record type (rule table — Pattern D)**

**Given** the system is evaluating whether a practitioner is ready for an NPDB call,
**When** it inspects the data on file for that practitioner,
**Then** the practitioner is considered **NPDB-ready** only when ALL of the following are populated per the rules below, and **NPDB Action Needed** otherwise:

- **Practitioner identity**
  - Date of birth (Person Account birthdate)
  - Legal name
- **NPI**
  - The practitioner has at least one active Healthcare Provider NPI record
  - The NPI number itself is populated on that record
- **Primary Address**
  - Address Line 1 — required
  - City — required
  - State — required
  - ZIP — required
  - County — *warning only* (NPDB allows blank but Ops prefers to know)
- **Licensure (SBRD class)**
  - At least one Business License with license class = SBRD linked to the practitioner
  - License number populated
  - License state populated
- **Education**
  - At least one Person Education record linked to the practitioner
- **Ancillary additions** (when record type is Ancillary Assessment or Ancillary Re-Assessment)
  - At least one practice facility selected
  - The facility's practice NPI is populated
  - For each selected facility: street address, city, state, ZIP populated on the affiliation block

The list above is the business contract. It is implemented as a **metadata-driven table** so that Operations can swap field rules in and out without a code release (see Technical Implementation §1).

---

### Validator output — machine-readable findings AND ready-to-display text

**AC-1.7a — The validator returns both a findings list and a pre-formatted business message** (Pattern B — service contract)

**Given** the validator has evaluated a practitioner,
**When** it returns its result,
**Then** the result carries all three of the following so every downstream consumer (the batch, the US-NPDB-02 OmniScript messages, the US-NPDB-03 report) reads from one source of truth:

- **`isValid`** — boolean; `true` only when no Error-severity finding remains.
- **`findings[]`** — structured list; each finding has: source-record group (e.g., *Primary Address*, *NPI*, *SBRD License*, *Education*, *Facility — {{name}}*), the friendly field label, the severity (`Error` / `Warning`), and the plain-English fix instruction.
- **`detailText`** — a single **human-readable, multi-line string** built from the findings, grouped by source record, with one bullet per missing item and its fix instruction (no hyperlinks, no record IDs). This is the exact text the US-NPDB-02 OmniScript renders in its Message elements and the record-page surface, so the wording lives in one place.

**And** the `detailsJson` (stored in `PRM_NPDBValidationDetails__c`) and the `detailText` are generated from the same `findings[]` list — they never drift.

**Example `detailText`:**

```
Cannot request NPDB until the following are fixed:

Primary Address
  • Street Address Line 1 is blank — add it on the practitioner's primary Address record.
  • ZIP is blank — add the ZIP on the primary Address record.

NPI
  • No active Healthcare Provider NPI found — add an NPI record for this practitioner.

SBRD License
  • No active SBRD-class Business License found — add an SBRD license with license number and state.
```

---

### New field — *Validation Details*

**AC-1.8 — Create the *Validation Details* field on Case Manager** (Pattern B)

- **API Name:** `PRM_NPDBValidationDetails__c`
- **Object:** `IndividualApplication` (Case Manager)
- **Type:** Long Text Area (32,768)
- **Label:** Validation Details
- **Default:** (blank)
- **Help text:** "JSON list of NPDB-required fields that were missing the last time the validator ran on this Case Manager. Cleared automatically when the Case Manager returns to Pending NPDB."
- **Description:** "Set automatically by the recredentialing batch (US-NPDB-01) and the manual-NPDB validator (US-NPDB-02). Consumed by the US-NPDB-02 banner and the US-NPDB-03 report. Not editable by end users; the system manages it."
- **Track History:** False (regenerable; native field-history would balloon)
- **Required:** False

---

### New field — *Validation Last Run*

**AC-1.9 — Create the *Validation Last Run* field on Case Manager** (Pattern B)

- **API Name:** `PRM_NPDBValidationLastRun__c`
- **Object:** `IndividualApplication` (Case Manager)
- **Type:** DateTime
- **Label:** Validation Last Run
- **Default:** (blank)
- **Help text:** "Timestamp of the last time the NPDB validator ran for this Case Manager."
- **Description:** "Set automatically by the validator on every run, regardless of outcome."
- **Track History:** False
- **Required:** False

---

### New picklist value — Status = "NPDB Action Needed"

**AC-1.10 — Add picklist value "NPDB Action Needed" on Case Manager Status and Case Status** (Pattern B)

- **Picklist value:** `NPDB Action Needed`
- **Active on objects:**
  - `IndividualApplication.Status` — active for record types `PRM_Practitioner`, `PRM_ReCredentialing`, `PRM_PractitionerParticipationRequest`, `PRM_AncillaryAssessment`, `PRM_AncillaryReAssessment`
  - `Case.Status` — active for `PRM Cred Recred`, `PRM Ancillary`, `PRM PAR`
- **Default:** No (not set as the default value on any record type)
- **Sort order:** Immediately after `Pending NPDB`
- **Color (if status-bar coloring is configured):** Amber / warning

---

### Field-level access & permission sets

**AC-1.11 — Field Access & Permission Sets for the new fields** (Pattern C)

- **System Administrator:**
  - Object level: Read, Create, Edit, Delete, View All Records, Modify All Records (no change to existing)
  - Field level (new fields): Read, Edit
- **PRM_DataModifyAll:**
  - Object level: Read, Create, Edit, View All Records
  - Field level (new fields): Read, Edit
- **PRM_CredentialingUser, PRM_AncillaryCredSpecialist, PRM_NetworkManagementQC:**
  - Object level: Read (no change)
  - Field level (new fields): Read only (no Edit — the system manages these fields)
- **All other permission sets / profiles:** No access to the new fields.
- **CMT read access:** `PRM_CredentialingUser`, `PRM_AncillaryCredSpecialist`, `PRM_NetworkManagementQC`, `PRM_DataViewAll`, `PRM_DataModifyAll`, `PRM_Base` — all granted read on the new `PRM_NpdbValidationFieldConfig__mdt` Custom Metadata Type.

---

### Resilience

**AC-1.12 — One bad practitioner does not kill the rest of the batch**

**Given** the nightly batch is processing a scope of practitioners (typical scope size: 50),
**When** the validator throws an unexpected exception on one of those practitioners,
**Then** that practitioner is skipped, an error log entry is recorded for Ops with enough context to reproduce the problem (Account Id, recredentialing-due date, validator step that failed),
**And** the remaining practitioners in the scope are processed normally,
**And** the batch finishes the scope without rolling back the work done for healthy practitioners.

---

### Non-functional

**AC-1.13 — Validator adds no measurable latency to the nightly batch**

**Given** the nightly batch runs at its existing schedule with its existing scope size of 50 practitioners per chunk,
**When** the new validator runs inside the batch,
**Then** the validator does not issue extra database queries on top of what the batch already fetches for each practitioner — it consumes the same data the batch already has in memory,
**And** the overall batch-finish time is no more than five percent slower than today's baseline on the same scope size.

---

## Technical Section — Technical Implementation (high-level)

> Concise — one table or short list. Cross-references the AC numbers it implements. Deep notes live in linked architecture docs, not here.

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_NpdbDataValidator.cls` | New Apex Callable | Pure service; given an Account + already-fetched related data + record-type developer name, returns a `ValidationResult` (`isValid`, `findings[]`, `detailsJson`, **`detailText`**). Inner classes `ValidationResult` and `MissingFieldFinding`. `@AuraEnabled validateNpdbReadyForCm(Id)` for US-NPDB-02 to consume. `validateForAal(aal, recordTypeDevName)` for the US-NPDB-02 trigger gate. **`Callable.call('validateForOmni', {caseManagerId})`** entry point so OmniStudio Integration Procedures (the manual NPDB paths in US-NPDB-02) can invoke it from a Remote/Action element without an LWC. Reads the metadata-driven contract from `PRM_NpdbValidationFieldConfig__mdt`. | AC-1.2, 1.7, 1.7a |
| `PRM_NpdbValidationFieldConfig__mdt` | New Custom Metadata Type | Per-rule row: `PRM_RecordTypeDevName__c`, `PRM_GroupName__c`, `PRM_SourceObject__c`, `PRM_SourceField__c`, `PRM_FriendlyLabel__c`, `PRM_Severity__c` (`Error` / `Warning`), `PRM_IsActive__c`, `PRM_Order__c`. Seed rows: one per row of §AC-1.7 (Practitioner + Ancillary, ~20 rows total). Ops can toggle `PRM_IsActive__c` without a code release. | AC-1.7 + future field changes |
| `PRM_CheckCAQHExecuteHelper.cls` | Modify existing helper | In `processAccount`, after the existing CAQH-active check and before `createActiveCAQHRecords`, call the validator. If `isValid = true` → unchanged code path. If `isValid = false` → call new `createNpdbActionNeededRecords` (stamps Status = NPDB Action Needed on Case Manager + Case, writes `detailsJson` + last-run timestamp on the Case Manager, **does not call** `initializeAdvActionLogRecord`). Extract `insertAalForCm(IndividualApplication cm)` so the release queueable can reuse the existing init path without duplicating logic. | AC-1.2, 1.6 |
| `PRM_GlobalConstant.cls` | Modify | Add `STS_NPDB_ACTION_NEEDED = 'NPDB Action Needed'` next to the existing status constants. | AC-1.10 |
| `PRM_CaseTriggerHandler.cls` | Modify (line 12 — `caseStatuses` set) | Add `'NPDB Action Needed'` so the new Case routes through the same round-robin queue assignment as a Pending NPDB Case. | AC-1.4 |
| `PRM_IndividualApplicationTriggerHandler.cls` | Modify (after-update branch) | When a Case Manager exits `NPDB Action Needed` (or when a referenced source field on the practitioner graph is touched), enqueue `PRM_NpdbActionNeededReleaseQueueable` with the CM Id. Guard with a static `Set<Id>` per transaction to prevent re-entrance. | AC-1.5, 1.6 |
| `PRM_NpdbActionNeededReleaseQueueable.cls` | New Queueable | Re-runs the validator. If still invalid → updates the findings JSON and exits. If valid → flips Status to `Pending NPDB`, clears findings, stamps last-run, calls `PRM_CheckCAQHExecuteHelper.insertAalForCm(cm)`. Idempotent (no-op if status already `Pending NPDB`). | AC-1.5, 1.6 |
| `IndividualApplication.PRM_NPDBValidationDetails__c` | New custom field | Long Text Area(32768) per §AC-1.8 | AC-1.8 |
| `IndividualApplication.PRM_NPDBValidationLastRun__c` | New custom field | DateTime per §AC-1.9 | AC-1.9 |
| `IndividualApplication.Status` + `Case.Status` picklists | Modify | Add picklist value `NPDB Action Needed` per §AC-1.10. | AC-1.10 |
| Permission set updates (5 perm sets) | Modify | FLS on the two new fields and read on the new CMT per §AC-1.11. | AC-1.11 |
| `PRM_ExceptionLogger.logException('PRM_NpdbDataValidator', 'Validation', ...)` | Log emitter | Info-level log on per-practitioner validator failure inside the batch. | AC-1.12 |
| `PRM_NpdbDataValidatorTest.cls` | New Apex test | Aim ≥95 % coverage. Methods per record type, per missing-field group, bulk 200, and exception resilience. | Quality gate |
| `PRM_NpdbActionNeededReleaseQueueableTest.cls` | New Apex test | Idempotent re-enqueue; still-invalid path; happy-flip path. | Quality gate |
| `PRM_CheckCAQHAccessOnDueAccountsTest.cls` | Modify | Add three integration scenarios: clean → Pending NPDB + AAL inserted (no regression); missing data → NPDB Action Needed + no AAL; fix → release queueable flips back. | Quality gate |

> **One-time backfill (optional, treat as a separate sprint task).** A read-only DFX script can scan currently-stuck Case Managers in *Pending NPDB* whose AAL has been in `Error` for > 7 days and route them to `NPDB Action Needed` via the validator. Not in scope for this story; left to Ops to schedule after the live batch run has stabilised.

---

## Definition of done

- [ ] New picklist value `NPDB Action Needed` deployed on `IndividualApplication.Status` and `Case.Status` for every record type in §AC-1.10.
- [ ] New fields `PRM_NPDBValidationDetails__c` and `PRM_NPDBValidationLastRun__c` deployed with the FLS in §AC-1.11.
- [ ] New `PRM_NpdbValidationFieldConfig__mdt` Custom Metadata Type deployed with all rows from §AC-1.7 seeded and `PRM_IsActive__c = true`.
- [ ] New Apex classes (validator, queueable, tests) deployed; modified classes (`PRM_CheckCAQHExecuteHelper`, `PRM_GlobalConstant`, `PRM_CaseTriggerHandler`, `PRM_IndividualApplicationTriggerHandler`) deployed.
- [ ] Permission set updates deployed.
- [ ] Test classes pass at ≥85 % overall and ≥95 % on `PRM_NpdbDataValidator`.
- [ ] QA-sandbox smoke test: 1 clean practitioner + 1 missing-data practitioner processed through the nightly batch with the expected outcomes per §AC-1.2.
- [ ] Operations confirms the new status surfaces on the Case Manager record page and in the existing Case list views.

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_CheckCAQHAccessOnDueAccountsBatch` + `PRM_CheckCAQHExecuteHelper` | Apex (batch + helper) | HIGH | Modifying the critical nightly recredentialing path. Touch must preserve today's clean-data flow exactly while adding the new branch. |
| `PRM_IndividualApplicationTriggerHandler` + `PRM_CaseTriggerHandler` | Apex (triggers) | MEDIUM | New after-update branch + new status added to existing queue-routing set. Re-entrance guard is critical. |
| `IndividualApplication.Status` + `Case.Status` picklists | Data model (picklist) | MEDIUM | Adding `NPDB Action Needed` value across multiple record types. Standard picklist deploy. |
| `IndividualApplication.PRM_NPDBValidationDetails__c` + `PRM_NPDBValidationLastRun__c` | Data model (custom fields) | LOW | Additive — no existing field is changed. |
| `PRM_NpdbValidationFieldConfig__mdt` Custom Metadata Type | Data model (CMT) | LOW | Brand-new metadata type with seed rows. |
| Permission sets (5) | Config (FLS + CMT read) | LOW | Additive read access — no existing access removed. |
| Operational reports / dashboards | Reporting | MEDIUM | New status drives a new operational queue (consumed by US-NPDB-03). Ops workflow shifts. |
| NPDB integration | External | LOW | Reduces noise (fewer failed calls). No protocol change. |

---

## Clarification Questions (before implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| Q1 | Does `NPDB Action Needed` route to the **same** round-robin queue as `Pending NPDB`, or to a new dedicated queue? | Determines whether the Case trigger handler one-line set extension in §AC-1.4 is sufficient, or whether we need a new queue + assignment rule. Default: same queue. | Ops Lead |
| Q2 | Should `PRM_LetterRecredBatch` send the standard recred letter while a Case Manager is in `NPDB Action Needed`? | If yes, no change needed. If no, we need to gate the letter batch on Status ≠ `NPDB Action Needed`. Default: no — letter waits until the CM flips back to `Pending NPDB`. | BA / Recred Ops |
| Q3 | Auto-release on field fix — synchronous (trigger + queueable per §AC-1.5) or wait until the next nightly batch? | Sync is cheaper than rerunning the batch and matches operator expectation; nightly delays the release by up to 24 hours. Default: sync. | Tech Lead |
| Q4 | Does the PAR record type (`PRM_PractitionerParticipationRequest`) share the Practitioner field contract in §AC-1.7? | If yes, no extra metadata rows needed. If stricter / looser, we add PAR-specific rules. Default: identical to ReCred. | BA |
| Q5 | Should we run the optional one-time backfill (route currently-stuck CMs to `NPDB Action Needed`) in QA before prod, or skip the backfill? | Backfill cleans up the existing operational debt visible in the report (US-NPDB-03). Default: yes — run once in QA, validate, then prod. | Ops Lead |

---

## Estimated Effort

> AI-estimated — validate with team. Sizing per the v1.6 effort table (S < 1h, M 2–4h, L 4–8h, XL 1–2 days, XXL 3+ days).

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| `PRM_NpdbDataValidator.cls` (+ inner classes + CMT lookup with static cache) | New Apex service | **XL** | Pure service, metadata-driven, bulkified. |
| `PRM_NpdbActionNeededReleaseQueueable.cls` | New Queueable | **L** | Idempotency guard + happy-flip + invalid-stay. |
| `PRM_CheckCAQHExecuteHelper.cls` modifications | Modify chokepoint helper | **L** | Adds the branch + `createNpdbActionNeededRecords` + extract `insertAalForCm`. Touch existing critical path — code-review heavy. |
| `PRM_CaseTriggerHandler.cls` + `PRM_GlobalConstant.cls` modifications | Modify | **S** | One-line set extension + one constant. |
| `PRM_IndividualApplicationTriggerHandler.cls` after-update branch | Modify | **M** | Re-entrance guard + enqueue. |
| `PRM_NpdbValidationFieldConfig__mdt` + seed records | New CMT | **L** | Schema + ~20 seed rows per record type. |
| 2 new fields + 1 new picklist value on IA + Case | Data model | **M** | Standard deploy. |
| Permission set FLS updates × 5 | Config | **M** | Repetitive. |
| Test classes (validator, queueable, helper integration, IA trigger, Case trigger) | New + modify | **XL** | ≥95 % on validator, ≥85 % overall. |
| Deployment + QA smoke (clean / missing / bulk) | Deploy + QA | **M** | See Definition of done. |
| **Total** | | **~XL (combined ≈ 5–6 dev-days incl. testing + code review)** | **8 story points** (Fibonacci) — confidence Medium-High. Biggest risk: bulk CPU profile across the 50-record batch scope; mitigate by caching CMT reads in a static per-transaction map. |

---

## Revision History

| Version | Date | Summary |
|---------|------|---------|
| v1 | 2026-06-01 | Initial draft (pre-template format). |
| v2 | 2026-06-03 | Rewrite to IBXQA Pre-Development Story Analysis Template (11 sections) + Linter-Conformant Summary appendix. Session `20260603_080755_816da8bf`. |
| v3 | 2026-06-03 | Rewrite to **User Story Solution Architect v1.6** skill. ACs converted to Pattern A (business-language Given/When/Then) and Pattern B/C (field + perm-set structured bullets). All Apex class names, IP version numbers, SOQL, and API field names removed from Given/When/Then lines and consolidated into the single **Technical Implementation (high-level)** table. Persona switched from "Credentialing Operations user" to canonical **Credentialing Specialist** per the v1.6 Workspace Persona Cheatsheet. |
| v4 | 2026-06-08 | Added **AC-1.7a** — validator now returns a pre-formatted, link-free `detailText` string (plus the existing `findings[]` and `detailsJson`) and exposes a `Callable.call('validateForOmni', …)` entry point. This supports the US-NPDB-02 redesign (detailed in-OmniScript text messages instead of Fix/Add deep links), keeping the message wording in a single source of truth. Driven by a component audit of the `PRM_CallNPDB_English` OmniScript + `PRM_IPCreateAdverseActionLog` IP. |
