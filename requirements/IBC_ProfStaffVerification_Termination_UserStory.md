# USER STORY 3b: IBC Professional Staff Verification — Term Professional Staff Outcome (Termination Cascade)

**Persona:** Credentialing Specialist
**Priority:** P1 (AI-estimated — validate with team)
**OmniScript:** `PRM_ProfStaffVerification_English` (the same OmniScript built in Story 3a — this story adds the **Term Professional Staff** outcome branch)
**Integration Procedures:** The verification submit IP (Story 3a) — add the Term branch
**Apex (reuse — do NOT rebuild):** `PRM_PractitionerTerminationUtility`, `PRM_RCATTerminationBatchHelper.resolveEffectivity` (effectivity/error-record rule), practice-location term helpers (`PRM_PracLocTermHelper`, `PRM_AccountTerminationBatchHelper`), the existing **PDM Manual Update — Remove Professional Staff** termination logic
**Relevant Requirements:** `requirements/IBC_ProfStaffVerification_Flow_UserStory.md` (Story 3a), `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` (effectivity-rule parity), `requirements/IBC_ProfStaffVerification_Config_UserStory.md` (Story 1)

> **Split from Story 3a.** Stories 3a and 3b deliver **one** OmniScript. 3a builds the flow shell + the Verification Complete and Manager Review outcomes; **this story adds the Term Professional Staff outcome**: the Termination Date field, its validation, and the full deactivation cascade across the practitioner's records. Per the requirement, this mirrors **"PDM Manual, Remove Professional Staff"** — reuse that termination cascade rather than building new.

---

## Story

**As a** Credentialing Specialist,
**I want** the Professional Staff Verification flow's "Term Professional Staff" outcome to close the verification and terminate the professional staff — deactivating the practitioner and all of their related records as of the termination date,
**So that** a professional staff member who fails verification is fully removed from the network in one guided submit, with correct effective-dating and audit, instead of a manual multi-object cleanup.

**Why it matters:** When a professional staff member should no longer participate, every downstream record (provider, taxonomy, licenses, info codes, practice-location links) must be effective-dated closed consistently. Doing this by hand is error-prone and leaves stale, still-active records — a directory-accuracy and claims-integrity risk. Reusing the proven PDM/RCAT termination cascade guarantees parity with how terminations already work elsewhere.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Professional Staff Verification | `PRM_ProfStaffVerification_English` | Review step — Termination Date field (shown when outcome = Term Professional Staff) | User entry + validation |
| Professional Staff Verification | `PRM_ProfStaffVerification_English` | Done (submit) — Term branch | Submit IP → termination cascade |

**In scope:** the Term Professional Staff Done branch — Case Manager/Case/Note updates plus the termination cascade across the practitioner's related records, with the shared effectivity/error-record rule and Termination Date validation.
**Out of scope:** Verification Complete / Manager Review branches (Story 3a); the flow shell, button, and Upload step (Story 3a); config (Story 1); batch (Story 2).

---

## Preconditions & Assumptions

- The outcome selected is **Term Professional Staff** (a `PRM_ProfessionalStaffVerificationOutcome__c` value from Story 1).
- **Assumption (per requirement):** the practitioner is associated to **exactly 1 Account** (IBX) and **1 Practice Location** (e.g. 1901 Market St). Multi-account / multi-location handling is a clarification (see Clarification #5).
- The termination cascade reuses the existing **PDM Manual — Remove Professional Staff** logic and the RCAT effectivity helper.

---

## Acceptance Criteria

**AC-1 — Termination Date field & validation (Term Professional Staff)** *(Pattern A)*

**Given** a Credentialing Specialist sets the Professional Staff Verification Outcome to "Term Professional Staff",
**When** the review step evaluates,
**Then** a required Termination Date field is displayed,
**And** the flow enforces the Termination Date validation rules before allowing "Done" (see Clarification #2 for the exact rules),
**And** a Notes entry is captured.

**AC-2 — Term Professional Staff Done (behaviour)** *(Pattern A)*

**Given** the outcome is "Term Professional Staff" with a valid Termination Date,
**When** the Credentialing Specialist clicks "Done",
**Then** the Case Manager is marked complete and denied with today's decision date and the captured review values,
**And** the Case is closed,
**And** the practitioner and all of their related records are effective-dated closed as of the Termination Date,
**And** a termination note is added to the Case Manager.

**AC-3 — Case Manager / Case / Note updates on Term (field specification)** *(Pattern E)*

**Given** the Professional Staff Verification Outcome = Term Professional Staff,
**When** the Credentialing Specialist clicks "Done",
**Then** the following records are updated exactly as specified:

**Case Manager (`IndividualApplication`) — Update**

| Field | Value | Notes |
|---|---|---|
| Stage | Complete | |
| Status | Denied | |
| Decision Date | {TODAY} | |
| License Verification | {License Verification} | from the flow |
| SAM Review | {SAM Review} | from the flow |
| OIG Review Outcome | {OIG Review Outcome} | from the flow |
| Professional Staff Verification Outcome | Term Professional Staff | from the flow |

**Case — Update**

| Field | Value | Notes |
|---|---|---|
| Status | Closed | Dev note: same as PDM Manual, Remove Professional Staff |

**Note — Create (on the Case Manager)**

| Field | Value | Notes |
|---|---|---|
| Title | Term Professional Staff | |
| Body | {Note Body} | from the flow's Notes field |

**AC-4 — Practitioner-record termination cascade (field specification)** *(Pattern E, dates per AC-5)*

**Given** the outcome is Term Professional Staff with Termination Date = {Termination Date},
**When** "Done" is clicked,
**Then** each of the following records is updated exactly as specified. Effective To, Active/Status, and the error-record handling follow the shared rule in **AC-5**; Case Manager is stamped on every record.

**Practitioner (`Account`) — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Active | per AC-5 (Active/Inactive resolution) | |
| Case Manager | {Case Manager} | |

**Healthcare Provider (`HealthcareProvider`) — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Status | per AC-5, resolving to "Active" / "Inactive" | this record uses a Status text, not a boolean |

**Healthcare Provider Taxonomy (`HealthcareProviderTaxonomy`) — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Active | per AC-5 | |
| Case Manager | {Case Manager} | |

**Business License (`BusinessLicense`) — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Active | per AC-5 | |
| Case Manager | {Case Manager} | |

**Info Code Assignment (`PRM_InfoCodeAssignment__c`) — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Case Manager | {Case Manager} | |

**Practitioner Practice Location — Record Type = Practice Location to Practitioner — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Active | per AC-5 | |
| Case Manager | {Case Manager} | |

**Practitioner Practice Location — Record Type = Practice to Practitioner — Update**

| Field | Value | Notes |
|---|---|---|
| Effective To | {Termination Date} | |
| Active | per AC-5 | |
| Case Manager | {Case Manager} | |

**AC-5 — Effective-date, Active/Status & error-record rule (shared)** *(Pattern D)*

**Given** any record touched by AC-4,
**When** the termination processing computes its dates,
**Then** the following rules are applied uniformly:

- **Effective To =** {Termination Date}
- **Active (boolean) / Status (text) =**
  - If Effective From ≤ TODAY **and** Effective To > TODAY → Active (Status = "Active")
  - If Effective To = NULL → if Effective From ≤ TODAY → Active (Status = "Active")
  - Else → Inactive / FALSE (Status = "Inactive")
- **Case Manager =** {Case Manager}
- **Error-record handling (per requirement dev note):** for records with Effective To = NULL or Effective To > {Termination Date}, when the Termination Date precedes the record's Effective From (i.e. terminating before the record began):
  - Effective From = TODAY
  - Is Error = TRUE
  - Active = FALSE

> **Parity note:** this rule is the same one already implemented by `PRM_RCATTerminationBatchHelper.resolveEffectivity` (see `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` AC-6). Route the cascade through that helper so termination effectivity is identical across PSV, RCAT, and PDM. The exact error-record comparison (`Effective From ≥ Termination Date`) is confirmed in Clarification #1.

**AC-6 — Reuse of PDM/RCAT termination cascade (no rebuild)** *(Pattern A)*

**Given** the Term Professional Staff branch runs,
**When** it terminates the practitioner's records,
**Then** it invokes the existing PDM Manual "Remove Professional Staff" / RCAT termination cascade (same objects, same effectivity helper),
**And** no parallel/duplicate termination logic is introduced for Professional Staff.

**AC-7 — Practitioner remains inactive after termination (verification)** *(Pattern A)*

**Given** the termination completed with a Termination Date on or before today,
**When** the practitioner and related records are queried,
**Then** the practitioner (Account), Healthcare Provider, taxonomy, business license, and practice-location links all resolve to Inactive/closed as of the Termination Date,
**And** each carries the verification Case Manager as its Case Manager.

**AC-8 — Termination before record start = error record (edge case)** *(Pattern A)*

**Given** a related record whose Effective From is on or after the entered Termination Date,
**When** the termination cascade processes it,
**Then** that record is flagged as an error record (Effective From = TODAY, Is Error = TRUE, Active = FALSE) per AC-5,
**And** it is not left in an inconsistent active state.

**AC-9 — Partial-failure isolation (negative)** *(Pattern A)*

**Given** one related record fails to update during the cascade,
**When** "Done" processing runs,
**Then** the failure is logged with the standard exception logger,
**And** the Case Manager is not silently marked complete on a failed run,
**And** the specialist is informed the termination did not fully complete.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_ProfStaffVerification_English` | Modified OmniScript | Add Termination Date field (conditional on outcome = Term Professional Staff) + validation | Drives AC-1 |
| Verification submit IP (from Story 3a) | Modified IP | Add the Term Professional Staff branch: Case Manager/Case/Note updates (AC-3) + invoke the termination cascade (AC-4) | Drives AC-2–AC-4 |
| `PRM_PractitionerTerminationUtility` + PDM "Remove Professional Staff" cascade | Reused Apex | Terminate Account, HealthcareProvider, HealthcareProviderTaxonomy, BusinessLicense, `PRM_InfoCodeAssignment__c`, and the two practice-location-link record types | Drives AC-4, AC-6 |
| `PRM_RCATTerminationBatchHelper.resolveEffectivity` | Reused Apex | Single source of truth for Effective To / Active / error-record (AC-5) | Drives AC-5, AC-8 |
| Note creation | IP/Apex | Create the "Term Professional Staff" note on the Case Manager | Drives AC-3 |
| Exception logging | Reused (`PRM_ExceptionLogger`) | Log partial failures | Drives AC-9 |

> **Reuse-first:** the requirement explicitly says the termination is the **same as PDM Manual, Remove Professional Staff**. The work is to *invoke* that cascade from the PSV submit branch (scoped to this practitioner) and pass the verification Case Manager + Termination Date — not to fork a new cascade.

---

## Definition of done

- [ ] Termination Date field appears and validates only when outcome = Term Professional Staff (AC-1).
- [ ] Term Professional Staff Done writes every field in AC-3 (Case Manager Complete/Denied, Case Closed, Note) — verified.
- [ ] Every object in AC-4 is effective-dated closed with the Termination Date, Active/Status resolved per AC-5, and stamped with the Case Manager — verified.
- [ ] Effectivity/error-record rule is routed through the shared RCAT helper (AC-5); error-record edge case behaves per AC-8.
- [ ] Termination reuses the PDM/RCAT cascade — no duplicate logic (AC-6).
- [ ] Practitioner and related records resolve to Inactive/closed post-run (AC-7).
- [ ] Partial-failure isolation + logging verified (AC-9).
- [ ] ≥85% Apex coverage incl. single practitioner, error-record, and partial-failure paths; real assertions on Effective To, Active/Status, Is Error, and Case Manager.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | The requirement's dev note reads "If Termination Date > Effective From then Effective From = TODAY, Is Error = TRUE" — this appears inverted (it would error most records). Confirm the intended rule is the standard "**Effective From ≥ Termination Date → error record**" (matching `resolveEffectivity`). | Correct error-record logic (AC-5, AC-8) | BA / Technical |
| 2 | What are the exact Termination Date validation rules ("add validation rules" in the requirement)? e.g. not in the past beyond X, not before Effective From, required non-null. | AC-1 validation | BA |
| 3 | Confirm the object/API mapping for "Practitioner" (Account vs. a practitioner-link object), and for the two "Practitioner Practice Location" record types ("Practice Location to Practitioner" and "Practice to Practitioner") — are both on `HealthcarePractitionerFacility`, or is one `PRM_PracticeToPractitioner__c`? | Cascade target correctness (AC-4) | Technical |
| 4 | Does the PDM "Remove Professional Staff" cascade already terminate this exact object set, or must any object be added for PSV parity (e.g. Provider Feature, Contact Method, NPI, Identifier, Boards, Program Participation)? | Reuse gap vs. extension (AC-6) | Technical |
| 5 | The assumption is 1 Account + 1 Practice Location. How should the cascade behave if a professional staff is later found on multiple accounts/locations (terminate all, or only the verification's account)? | Scope / last-remaining handling | BA / Technical |
| 6 | Should the termination run synchronously in the submit, or be offloaded to a batch/async for governor safety on practitioners with many related records? | Performance / architecture | Technical |
| 7 | "HealthcareProvider" uses a Status text ("Active"/"Inactive") while others use an Active boolean — confirm the field names/types for each object so the shared rule maps correctly. | Field mapping (AC-4, AC-5) | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_ProfStaffVerification_English` | OmniScript | MEDIUM | Termination Date field + validation on the Term branch |
| Verification submit IP | IP | HIGH | New Term branch invoking the termination cascade |
| `PRM_PractitionerTerminationUtility` / PDM Remove Professional Staff cascade | Apex | HIGH | Reused (possibly extended) for the PSV termination |
| `PRM_RCATTerminationBatchHelper` | Apex | MEDIUM | Reused effectivity/error-record rule |
| `Account`, `HealthcareProvider`, `HealthcareProviderTaxonomy`, `BusinessLicense`, `PRM_InfoCodeAssignment__c`, `HealthcarePractitionerFacility` (both RTs) | Objects | HIGH | Records terminated/closed |
| `IndividualApplication`, `Case`, Note | Objects | MEDIUM | Completed/closed + note |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Termination Date field + validation | OmniScript | M | Conditional field + validation rules |
| Submit IP Term branch (CM/Case/Note + cascade invocation) | IP | L–XL | Branch recipe + wire to cascade |
| Reuse/extend PDM/RCAT termination cascade | Apex | L | L if reused as-is; higher if objects must be added (Clarification #4) |
| Route effectivity through shared helper | Apex | S–M | Reuse `resolveEffectivity` |
| Test coverage | Apex test | L | Term branch + error-record + partial-failure |

**Total Estimated Effort:** **XL** (AI-estimated — validate with team). Trends lower if the PDM "Remove Professional Staff" cascade is reused as-is; higher if it must be extended for PSV parity.
