# USER STORY 3a: IBC Professional Staff Verification — Guided Verification Flow (Verification Complete & Manager Review)

**Persona:** Credentialing Specialist
**Priority:** P1 (AI-estimated — validate with team)
**OmniScript:** New `PRM_ProfStaffVerification_English` (naming per PNM convention — confirm)
**Integration Procedures:** New submit IP for the record updates (naming per PNM convention — confirm); reuse the org's Reusable Document Upload component
**Relevant Requirements:** `requirements/IBC_ProfStaffVerification_Config_UserStory.md` (Story 1), `requirements/IBC_ProfStaffVerification_Batch_UserStory.md` (Story 2), `requirements/IBC_ProfStaffVerification_Termination_UserStory.md` (Story 3b — the **Term Professional Staff** outcome)

> **Split note:** This story builds the verification button, the guided flow, and the **Verification Complete** and **Manager Review** outcomes. The **Term Professional Staff** outcome — including the Termination Date field, its validation rules, and the full deactivation cascade across the practitioner's records — is specified separately in **Story 3b** so it can be estimated and tested independently. The two stories deliver **one** OmniScript; 3a builds the shell + two outcomes, 3b adds the third outcome branch.

---

## Story

**As a** Credentialing Specialist,
**I want** a "Prof Staff Verification" button on the professional-staff verification Case that launches a guided flow to record the license, OIG, and SAM review results, derive an outcome, optionally upload documentation, and update the records on completion,
**So that** I can complete a professional staff's yearly verification in one guided pass and have the Case Manager, Case, and practitioner updated correctly.

**Why it matters:** Professional staff verification is a lightweight yearly check. A guided flow that auto-populates prior review values, defaults the outcome from the individual review results, and writes the record updates in one submit removes manual data entry and keeps the verification consistent and auditable.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Professional Staff Verification | `PRM_ProfStaffVerification_English` | Verification review step | Auto-populated from the Case Manager (License Verification, OIG Review Outcome, SAM Review) |
| Professional Staff Verification | `PRM_ProfStaffVerification_English` | Upload Documentation step | Reusable Document Upload (optional) |
| Professional Staff Verification | `PRM_ProfStaffVerification_English` | Done (submit) | Submit IP → record updates per outcome |

**In scope (this story):** the button, the flow, the review step, the Upload Documentation step, and the **Verification Complete** and **Manager Review** Done branches.
**Out of scope:** the **Term Professional Staff** Done branch and termination cascade (Story 3b); config (Story 1); batch creation (Story 2).

---

## Acceptance Criteria

**AC-1 — "Prof Staff Verification" button on the Case** *(Pattern A)*

**Given** a Case with Type = Prof Staff Verification,
**When** a Credentialing Specialist views the Case,
**Then** a button titled "Prof Staff Verification" is displayed,
**And** the button is not shown on Cases of other types.

**AC-2 — Guided flow launches and displays the review step** *(Pattern A)*

**Given** a Credentialing Specialist clicks the "Prof Staff Verification" button,
**When** the guided flow launches,
**Then** the first step displays License Verification, OIG Review Outcome, and SAM Review — each offering "Data Looks Good" (with its review date) or "Review Needed",
**And** each of those three fields is auto-populated from its current value on the Case Manager,
**And** the Professional Staff Verification Outcome and a Notes field are displayed,
**And** all four starred fields (License Verification, OIG Review Outcome, SAM Review, Professional Staff Verification Outcome) are required.

**AC-3 — Outcome defaults from the review results** *(Pattern A)*

**Given** the Credentialing Specialist is on the review step,
**When** the three review results are set,
**Then** the Professional Staff Verification Outcome defaults to "Verification Complete" if all three reviews = "Data Looks Good",
**And** defaults to "Manager Review" if any of the three reviews = "Review Needed",
**And** the specialist can override the defaulted outcome (including selecting "Term Professional Staff" — behaviour delivered in Story 3b).

**AC-4 — Upload Documentation step** *(Pattern A)*

**Given** the Credentialing Specialist clicks "Next" from the review step,
**When** the next step loads,
**Then** the step is titled "Upload Documentation" and displays the Reusable Document Upload component,
**And** uploading a document is optional (the flow can be completed without a file).

**AC-5 — Done, outcome = Verification Complete (behaviour)** *(Pattern A)*

**Given** the outcome is "Verification Complete",
**When** the Credentialing Specialist clicks "Done",
**Then** the Case Manager is marked complete and approved with today's decision date and the captured review values,
**And** the Case is closed,
**And** the practitioner's Re-Cred Due Date is advanced by one year (minus one day),
**And** a completion note is added to the Case Manager.

**AC-6 — Records updated on Done, outcome = Verification Complete (field specification)** *(Pattern E)*

**Given** the Professional Staff Verification Outcome = Verification Complete,
**When** the Credentialing Specialist clicks "Done",
**Then** the following records are updated exactly as specified:

**Case Manager (`IndividualApplication`) — Update**

| Field | Value | Notes |
|---|---|---|
| Stage | Complete | |
| Status | Approved | |
| Decision Date | {TODAY} | |
| License Verification | {License Verification} | from the flow |
| SAM Review | {SAM Review} | from the flow |
| OIG Review Outcome | {OIG Review Outcome} | from the flow |
| Professional Staff Verification Outcome | Verification Complete | from the flow |

**Case — Update**

| Field | Value | Notes |
|---|---|---|
| Status | Closed | |

**Practitioner (`Account`) — Update**

| Field | Value | Notes |
|---|---|---|
| Re-Cred Due Date | {TODAY} + 1 Year − 1 Day | next yearly verification cadence |

**Note — Create (on the Case Manager)**

| Field | Value | Notes |
|---|---|---|
| Title | Professional Staff Verification Complete | |
| Body | {Note Body} | from the flow's Notes field |

**AC-7 — Done, outcome = Manager Review (behaviour)** *(Pattern A)*

**Given** the outcome is "Manager Review",
**When** the Credentialing Specialist clicks "Done",
**Then** the Case Manager keeps the captured review values and is set to a "Manager Review" status (Stage is not completed),
**And** the Case is placed On Hold,
**And** a Manager Review note is added to the Case Manager,
**And** the practitioner's Re-Cred Due Date is **not** changed.

**AC-8 — Records updated on Done, outcome = Manager Review (field specification)** *(Pattern E)*

**Given** the Professional Staff Verification Outcome = Manager Review,
**When** the Credentialing Specialist clicks "Done",
**Then** the following records are updated exactly as specified:

**Case Manager (`IndividualApplication`) — Update**

| Field | Value | Notes |
|---|---|---|
| License Verification | {License Verification} | from the flow |
| SAM Review | {SAM Review} | from the flow |
| OIG Review Outcome | {OIG Review Outcome} | from the flow |
| Professional Staff Verification Outcome | Manager Review | from the flow |
| Status | Manager Review | Stage is **not** set to Complete |

**Case — Update**

| Field | Value | Notes |
|---|---|---|
| Status | On Hold | Dev note: On-Hold Start Date/Time logic is **not** triggered |

**Note — Create (on the Case Manager)**

| Field | Value | Notes |
|---|---|---|
| Title | Professional Staff Verification - Manager Review | |
| Body | {Note Body} | from the flow's Notes field |

**AC-9 — Auto-populated values persist when unchanged (edge case)** *(Pattern A)*

**Given** the specialist accepts the auto-populated License Verification, OIG Review Outcome, and SAM Review without editing them,
**When** they click "Done",
**Then** those same current values are written back to the Case Manager unchanged,
**And** no field is blanked as a side effect of the submit.

**AC-10 — Required field enforcement (negative)** *(Pattern A)*

**Given** any of the four starred fields is empty,
**When** the specialist attempts to proceed past the review step,
**Then** the flow blocks progression and prompts for the missing required field.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| Case button "Prof Staff Verification" | New action/button (LWC action or OmniScript launcher) | Visible only when `Case.Type = 'Prof Staff Verification'`; launches the OmniScript with Case + Case Manager context | Drives AC-1 |
| `PRM_ProfStaffVerification_English` | New OmniScript | Review step (License/OIG/SAM + Outcome + Notes), Upload Documentation step | Drives AC-2–AC-4, AC-9, AC-10 |
| Outcome default formula | OmniScript logic | Default `Professional Staff Verification Outcome` from the three review results (all Good → Verification Complete; any Review Needed → Manager Review); overridable | Drives AC-3 |
| Auto-populate (load) | DataRaptor Extract / IP load | Fetch current License Verification, OIG Review Outcome, SAM Review from the Case Manager | Drives AC-2, AC-9 |
| Reusable Document Upload | Reused component | Optional upload on the Upload Documentation step | Drives AC-4 |
| Submit IP (Verification Complete & Manager Review branches) | New IP | Branch on outcome; write the AC-6 / AC-8 record updates; create the note | Drives AC-5–AC-8 |
| Note creation | IP/Apex | Create a Note (or ContentNote) on the Case Manager with the branch-specific Title + Body | Drives AC-6, AC-8 |

> The **Term Professional Staff** outcome branch of the submit IP (and the Termination Date field + validation) is added by **Story 3b**; this story wires only the Verification Complete and Manager Review branches.

---

## Definition of done

- [ ] "Prof Staff Verification" button shows only on Prof Staff Verification Cases and launches the flow (AC-1, AC-2).
- [ ] Review step auto-populates the three review fields from the Case Manager and defaults the outcome per AC-3.
- [ ] Upload Documentation step is optional (AC-4).
- [ ] Verification Complete Done writes every field in AC-6 (Case Manager, Case, Practitioner, Note) — verified.
- [ ] Manager Review Done writes every field in AC-8 (Case Manager, Case On Hold, Note) and does **not** change the Re-Cred Due Date — verified.
- [ ] Unchanged auto-populated values persist (AC-9); required-field enforcement works (AC-10).
- [ ] New OmniScript version activated and deployed; verified by a Credentialing Specialist.
- [ ] ≥85% Apex coverage on the submit IP's Apex actions incl. both branches + negative paths, if Apex is used.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the target names: OmniScript `PRM_ProfStaffVerification_English` and the submit IP name (per PNM convention). | Naming / component resolution | Technical |
| 2 | "License Verification" and "OIG Review Outcome" auto-populate "from value on Case Manager" — confirm the exact Case Manager fields feeding these (and that "License Verification" ↔ "License Review" naming is the same field). | Load mapping (AC-2, AC-9) | BA / Technical |
| 3 | Which Reusable Document Upload component is the standard (LWC name / where files link)? | AC-4 reuse | Technical |
| 4 | For "Data Looks Good", where is the review **date** stored (License Verification Date, OIG Review Date, SAM Review Date) — existing Case Manager fields? | Field mapping | Technical |
| 5 | Should the note be a classic Note, a ContentNote, or a Chatter post? Confirm the org's standard for verification notes. | AC-6/AC-8 note type | BA / Technical |
| 6 | Manager Review sets Case to On Hold with "On-Hold Start Date/Time logic not triggered" — confirm how to suppress that automation (bypass flag / permission). | AC-8 correctness | Technical |
| 7 | After Manager Review, what re-opens/re-routes the case for the manager to act? Is there a follow-up path (out of scope here but needed end-to-end)? | Process completeness | BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| `PRM_ProfStaffVerification_English` | OmniScript | HIGH | New guided flow |
| Submit IP | IP | HIGH | New record-update logic (two branches here, third in 3b) |
| Case button/action | UI | MEDIUM | New launcher, type-gated visibility |
| `IndividualApplication`, `Case`, `Account`, Note | Objects | MEDIUM | Records updated/created on Done |
| Reusable Document Upload | Component | LOW | Reused as-is |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Case button/action | UI config/LWC | M | Type-gated visibility + launch |
| OmniScript (review + upload steps, defaulting) | OmniScript | XL | Multi-step flow, outcome defaulting, auto-populate |
| Load DataRaptor/IP | DR/IP | M | Fetch current review values |
| Submit IP (Verification Complete + Manager Review branches) | IP | XL | Two branch record recipes + note creation |
| Test coverage | Apex/OmniScript test | L | Both branches + negative + persistence |

**Total Estimated Effort:** **XL** (AI-estimated — validate with team). The single OmniScript is shared with Story 3b.
