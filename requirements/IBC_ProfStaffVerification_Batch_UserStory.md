# USER STORY 2: IBC Professional Staff Verification — Re-Cred Due Date & Daily Case-Creation Batch

**Persona:** Credentialing Specialist
**Priority:** P1 (AI-estimated — validate with team)
**OmniScript:** N/A (Practitioner Creation record write + Apex batch)
**Integration Procedures:** Practitioner Creation IBC Professional Staff record-creation chain (confirm active IP/DR — see Clarification #1)
**Apex (reference / reuse candidates):** `PRM_RecredDuePractitionersReportBatch` (recred-due query pattern), existing recredentialing case-creation batch (see Clarification #2)
**Relevant Requirements:** `requirements/IBC_ProfStaffVerification_Config_UserStory.md` (Story 1 — provides record type, queue, Case Type value), `requirements/IBC_ProfStaffVerification_Flow_UserStory.md` (Story 3a), `requirements/IBC_ProfStaffVerification_Termination_UserStory.md` (Story 3b)

> **Depends on Story 1** for the `PRM_ProfessionalStaffVerification` record type, the `Prof Staff Verification` Case Type value, and the `PRM_ProfessionalStaffVerificationQueue`.

---

## Story

**As a** Credentialing Specialist,
**I want** IBC Professional Staff practitioners to get a Re-Cred Due Date at creation, be excluded from the standard recredentialing batch, and instead have a Professional Staff Verification Case Manager and Case auto-created a configurable lead time (default 90 days) before their Re-Cred Due Date,
**So that** professional staff are verified yearly through the lightweight verification flow instead of the full re-credentialing process, the verification cases land in my queue with enough runway to complete before the due date, and the lead time can be tuned with a metadata change (no code deploy).

**Why it matters:** Professional staff do not go through full re-credentialing; they require a yearly verification. Today they would either be swept into the recredentialing batch (wrong process) or missed entirely. This story sets the yearly cadence (Re-Cred Due Date), removes professional staff from the recred batch, and stands up a dedicated daily batch that manufactures the verification work — 90 days ahead of the due date so my team has time to work it — with correct routing. Making the 90-day lead time a Custom Metadata value means Ops can shorten/lengthen the runway without a release.

---

## Scope

| Trigger | Object(s) written | Change |
|---------|-------------------|--------|
| Practitioner Creation (IBC Professional Staff) | Practitioner (`Account`) | Set Re-Cred Due Date = Effective From + 1 Year − 1 Day |
| Recredentialing batch | — | Exclude Professional Staff from selection |
| Daily batch (configurable lead days, default 90, before Re-Cred Due Date) | Case Manager (`IndividualApplication`) + Case | Create verification records, route to PSV queue (round-robin) |
| Custom Metadata | `PRM_Constant__mdt` (or equivalent) | Configurable lead-days value driving the batch window |

**In scope:** the Re-Cred Due Date write at creation, the recred-batch exclusion, the configurable lead-days Custom Metadata value, and the new daily creation batch with duplicate check and round-robin.
**Out of scope:** the verification guided flow (Stories 3a/3b) and all config (Story 1).

---

## Current State (from codebase)

- **`Account.PRM_ReCredDueDate__c`**, **`IndividualApplication.PRM_ReCredDueDate__c`**, and **`Case.PRM_ReCredDueDate__c`** already exist — "Practitioner Re-Cred Due Date" maps to `Account.PRM_ReCredDueDate__c`.
- **`PRM_RecredDuePractitionersReportBatch`** already queries recred-due Case Managers (`RecordType.DeveloperName = 'PRM_ReCredentialing'`, `PRM_ReCredDueDate__c` between start/end) — a reusable pattern for date-window selection, but it only reports.
- **`PRM_Constant__mdt.PRM_RecredDueDays__c`** already exists — a Custom Metadata "days before due date" value used by recred logic. The PSV lead time should follow the same pattern (reuse this field if it is process-agnostic, or add a dedicated `PRM_ProfStaffVerificationLeadDays__c` — see Clarification #8).
- The recredentialing case-creation batch that generates recred Case Managers exists in the recred batch family (`PRM_Recred*`) — its exact selection query must be updated to exclude professional staff (Clarification #2).

---

## Acceptance Criteria

**AC-1 — Practitioner Creation sets the Re-Cred Due Date for IBC Professional Staff** *(Pattern A)*

**Given** a Credentialing Specialist creates an IBC Professional Staff practitioner,
**When** the practitioner record is created,
**Then** the practitioner's Re-Cred Due Date is set to one year minus one day from the Effective From date.

**AC-1b — Re-Cred Due Date field specification on creation** *(Pattern E)*

**Given** an IBC Professional Staff practitioner is being created with an Effective From date,
**When** the practitioner record is created,
**Then** the following field is set exactly as specified:

**Practitioner (`Account`) — Update (during creation)**

| Field | Value | Notes |
|---|---|---|
| Re-Cred Due Date | {Effective From} + 1 Year − 1 Day | e.g. Effective From 2026-03-01 → Re-Cred Due Date 2027-02-28 |

**AC-2 — Recredentialing batch excludes Professional Staff** *(Pattern A)*

**Given** the standard recredentialing batch runs,
**When** it selects practitioners due for re-credentialing,
**Then** IBC Professional Staff practitioners are **not** selected,
**And** no recredentialing Case Manager or recred case is created for them.

**AC-3 — Daily batch creates PSV records at the configurable lead time before the Re-Cred Due Date** *(Pattern A)*

**Given** an IBC Professional Staff practitioner whose Re-Cred Due Date is exactly the configured lead time away from today (default 90 days),
**When** the daily batch runs,
**Then** a Professional Staff Verification Case Manager and its Case are created for the practitioner,
**And** both are owned by the Professional Staff Verification Queue via round-robin assignment,
**And** the practitioner appears in the Professional Staff Verification list view (from Story 1).

**AC-3b — Lead time is Custom-Metadata configurable (no code change)** *(Pattern A)*

**Given** an administrator changes the configured lead-days value in Custom Metadata (e.g. from 90 to 60),
**When** the daily batch next runs,
**Then** it creates the PSV records that many days before each practitioner's Re-Cred Due Date instead,
**And** no code deployment is required for the change to take effect.

**AC-4 — Records created by the daily batch (field specification)** *(Pattern E)*

**Given** the daily batch selects an eligible IBC Professional Staff practitioner whose Re-Cred Due Date is the configured lead time (default 90 days) away,
**When** the batch creates the verification records,
**Then** the following records are created exactly as specified (Case created first, then Case Manager references it — confirm order in Clarification #4):

**Case Manager (`IndividualApplication`) — Create**

| Field | Value | Notes |
|---|---|---|
| Record Type | Professional Staff Verification | `PRM_ProfessionalStaffVerification` |
| Status | New | |
| Stage | Professional Staff Verification | |
| Application Type | Individual | |
| Category | Credentialing | |
| Applied Date | {Current date/time} | |
| Latest Case | {Case created below} | lookup to the Case |
| Account | {Practitioner} | the practitioner Account |
| Owner | Professional Staff Verification Queue | round-robin assignment |

**Case — Create**

| Field | Value | Notes |
|---|---|---|
| Record Type | PRM | |
| Type | Prof Staff Verification | new value from Story 1 |
| Status | New | |
| Account Name | {Practitioner} | |
| Owner | Professional Staff Verification Queue | |
| Case Manager | {Case Manager} | lookup to the Case Manager above |
| IsRoundRobin | true | drives round-robin ownership |

**AC-5 — Duplicate check (edge case / negative)** *(Pattern A)*

**Given** an IBC Professional Staff practitioner who already has an open (not Complete) Professional Staff Verification Case Manager,
**When** the daily batch runs,
**Then** no second Professional Staff Verification Case Manager or Case is created for that practitioner,
**And** the existing open verification case is left unchanged.

**AC-6 — Round-robin distribution** *(Pattern A)*

**Given** multiple Professional Staff Verification cases are created by a single daily batch run,
**When** ownership is assigned,
**Then** the cases are distributed across the Professional Staff Verification Queue members via round-robin (`IsRoundRobin = true`),
**And** no single member receives all of the batch's cases when more than one member is active.

**AC-7 — No eligible practitioners (edge case)** *(Pattern A)*

**Given** a day on which no IBC Professional Staff practitioner has a Re-Cred Due Date exactly the configured lead time away,
**When** the daily batch runs,
**Then** no verification Case Manager or Case is created,
**And** the batch completes successfully without error.

**AC-8 — Configurable lead-days Custom Metadata value** *(Pattern B)*

- **Custom Metadata Type:** `PRM_Constant__mdt` (reuse) — or a dedicated PSV setting (Clarification #8)
- **Field:** `PRM_ProfStaffVerificationLeadDays__c` (or reuse `PRM_RecredDueDays__c` if process-agnostic)
- **Type:** Number(4,0)
- **Default value:** 90
- **Description:** Number of days before a professional staff practitioner's Re-Cred Due Date that the Professional Staff Verification Case Manager and Case are auto-created by the daily batch.
- **Consumed by:** the daily PSV creation batch selection window (`PRM_ReCredDueDate__c = TODAY + {lead days}`)

**AC-9 — Missing/blank configuration falls back to default (edge case)** *(Pattern A)*

**Given** the lead-days Custom Metadata value is missing or blank,
**When** the daily batch runs,
**Then** it falls back to the default of 90 days,
**And** it does not fail or skip eligible practitioners.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| Practitioner Creation IBC Professional Staff record write | Modified IP/DR step (or Apex service) | Set `Account.PRM_ReCredDueDate__c = {Effective From} + 1 Year − 1 Day` | Drives AC-1/AC-1b; confirm the active creation component in Clarification #1 |
| Recredentialing case-creation batch | Modified Apex batch | Add exclusion so professional staff are not selected (e.g. by practitioner type / record type filter) | Drives AC-2; confirm class + filter in Clarification #2 |
| New `PRM_ProfStaffVerificationCreationBatch` (name TBD) | New Apex `Database.Batchable` + Scheduler | Selects IBC Professional Staff practitioners whose `PRM_ReCredDueDate__c = TODAY + {lead days}`; creates Case + Case Manager per AC-4; bulk DML (one per object type); duplicate guard | Drives AC-3–AC-9 |
| Lead-days Custom Metadata | New/reused CMDT field (`PRM_Constant__mdt`) | `PRM_ProfStaffVerificationLeadDays__c` (default 90); read in the batch `start` query with a 90-day fallback | Drives AC-3, AC-3b, AC-8, AC-9 |
| Duplicate guard | Apex query in batch `start`/`execute` | Skip practitioners with an existing open PSV Case Manager (Stage ≠ Complete) | Drives AC-5 |
| Round-robin assignment | Queue + `IsRoundRobin = true` | Reuse the org's existing round-robin mechanism used by other round-robin case types | Drives AC-6; confirm mechanism in Clarification #3 |
| Scheduler | Schedulable/CRON | Runs **daily**; each run selects the exact `TODAY + {lead days}` due-date cohort (the lead time comes from CMDT, not a hard-coded date) | Drives AC-3 |

---

## Definition of done

- [ ] IBC Professional Staff practitioners get `Re-Cred Due Date = Effective From + 1 Year − 1 Day` at creation (AC-1/AC-1b) — verified with a boundary date (leap-year and month-end).
- [ ] The recredentialing batch no longer selects professional staff (AC-2) — verified no recred CM/case is produced for them.
- [ ] The daily batch creates the Case Manager + Case exactly per AC-4 at the configured lead time before the due date, routed round-robin to the PSV queue (AC-3, AC-6).
- [ ] Changing the lead-days Custom Metadata value shifts the creation window with no code deploy (AC-3b, AC-8); missing/blank config falls back to 90 (AC-9).
- [ ] Duplicate check prevents a second open PSV case per practitioner (AC-5).
- [ ] Empty-day run completes with no records created and no error (AC-7).
- [ ] ≥85% Apex coverage incl. bulk (200+ practitioners), single, empty, duplicate, and config-fallback paths; assertions on all AC-4 field values.
- [ ] Batch stays within governor limits on a large daily cohort (one bulk DML per object type).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which active Practitioner Creation component (IP/DataRaptor/Apex service) writes the IBC Professional Staff practitioner, and where should the Re-Cred Due Date be set? | Where AC-1 change lands | Technical |
| 2 | What is the exact recredentialing case-creation batch class and its selection query, and how is "Professional Staff" identified (practitioner type field? account record type? staff category?) so it can be excluded? | AC-2 correctness | Technical / BA |
| 3 | What round-robin mechanism does the org use for `IsRoundRobin = true` cases (assignment rules, a round-robin batch/trigger, or a custom counter)? Reuse the same for PSV. | AC-6 implementation | Technical |
| 4 | Creation order — should the Case be created first (so `Latest Case` on the Case Manager can reference it) or the Case Manager first (so `Case Manager` on the Case can reference it)? Both lookups are cross-referencing. | DML sequencing / two-pass update | Technical |
| 5 | "Professional Staff" — is there a distinct practitioner type/flag on the Account set during IBC Professional Staff creation that both the recred exclusion (AC-2) and the daily batch selection (AC-3) key off? | Selection criteria for both batches | BA / Technical |
| 6 | Should the batch match the due date **exactly** (`PRM_ReCredDueDate__c = TODAY + lead days`) or use a **catch-up window** (`≤ TODAY + lead days` and no open PSV case yet) so a practitioner missed on their exact trigger day (batch failure, holiday, lead-time change) is still picked up? A window is safer against gaps. | Selection window robustness | BA / Technical |
| 7 | Confirm `Application Type = Individual` and `Category = Credentialing` are existing picklist values on the Case Manager (no new values needed). | Deployability | Technical |
| 8 | Reuse the existing `PRM_Constant__mdt.PRM_RecredDueDays__c`, or add a dedicated `PRM_ProfStaffVerificationLeadDays__c` so PSV lead time is independent of recred settings? | CMDT design (AC-8) | Technical / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|--------------|-------------|
| Practitioner Creation (IBC Professional Staff) | IP/DR/Apex | MEDIUM | New field write for Re-Cred Due Date |
| Recredentialing case-creation batch | Apex | HIGH | Selection query change (must not affect non-professional-staff recred) |
| New PSV creation batch + scheduler | Apex | HIGH | New batch, duplicate guard, round-robin, scheduler |
| `PRM_Constant__mdt` (lead-days value) | CMDT | LOW | New/reused configurable lead-days field |
| `IndividualApplication`, `Case`, `Account` | Objects | MEDIUM | Records created/updated |
| Professional Staff Verification Queue | Routing | LOW | Receives round-robin ownership |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Re-Cred Due Date write at creation | IP/DR/Apex | M | Single formula field write + boundary handling |
| Recred batch exclusion | Apex | M | Query filter + regression tests |
| New PSV creation batch | Apex batch | XL | CMDT-driven selection window, duplicate guard, cross-referenced Case/CM creation, round-robin |
| Lead-days Custom Metadata | Config | S | New/reused CMDT field + default 90 + fallback |
| Scheduler | Apex | S | Daily CRON |
| Test coverage | Apex test | L | Bulk + duplicate + empty + config-fallback + boundary dates |

**Total Estimated Effort:** **XL** (AI-estimated — validate with team).
