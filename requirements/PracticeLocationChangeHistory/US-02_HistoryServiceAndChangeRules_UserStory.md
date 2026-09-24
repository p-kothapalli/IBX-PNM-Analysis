# USER STORY 02: Practice Location History Service and Change Rules

**Persona:** PDM Specialist (secondary: Network Management QC Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-01](US-01_HistoryConfigurationMetadata_UserStory.md) · [Design prompt](../PracticeLocation_ChangeHistory_LWC_DesignPrompt.md) §5, §8 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) §3.3, §4 · Business feedback 0.4 items 1–3
**Build status:** ✅ Built in POC (QA) v0.4 · Remaining gaps: error-log context truncated (AC-12), noisy fields (Clarification Question 1)

---

## Story

**As a** PDM Specialist,
**I want** every change to a practice location and to the records beneath it translated into a plain-English event, showing who made it, when, under which Case Manager and FHNatic case, and the record's effective dates,
**So that** I can tell at a glance whether a practitioner, network or taxonomy was added, removed, reinstated or updated, without opening child records or asking for a report.

**Why it matters:** At Hospitalists Pottstown, one save on 9/17 end-dated 140 practitioners, 13 networks and 14 taxonomies, and none of it is visible on the location's History tab today. This service is the engine behind every view in US-05 to US-08.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Practice Location record page | N/A | History component load | Field history (live) of the location and every active category in US-01 |

---

## Acceptance Criteria

**AC-1 — A practitioner added to a location is shown in plain English**

**Given** a PDM Specialist added Dr. Jane Doe as a PCP at a practice location last week,
**When** a PDM Specialist opens that location's change history,
**Then** they see "Practitioner Jane Doe (PCP) added",
**And** it shows who added her, the date and time, and the practitioner link's effective-from date.

**AC-2 — Change types are derived by these rules**

**Given** a tracked change exists on the location or on any record in an active category,
**When** the history is loaded,
**Then** each change is labelled per the rules below:

- **Added** = the record was created
- **Removed** = end date set to the day of the change or earlier; *or* end date moved from a later day to that day or earlier
- **Scheduled removal** = end date set to a day after the day of the change
- **Reinstated** = end date cleared; *or* end date moved from on/before the day of the change to after it
- **End date changed** / **Start date changed** = any other end-date / start-date change
- **Deactivated** / **Reactivated** = Active switched off / on
- **Marked as error** / **Error cleared** = Error Record flag switched on / off
- **Pending** / **Pending cleared** = Pending flag switched on / off
- **Primary changed** = Primary (facility, taxonomy or location) flag changed
- **Panel status changed** = Panel Status changed
- **Updated** = any other tracked field (shown as *field: old → new*)
- "Added", "Removed", "Scheduled removal", "Reinstated", "Deactivated" and "Reactivated" count as **adds and removes**; everything else counts as an **update**.

**AC-3 — Immediate and future removals are told apart**

**Given** on 9/17 a PDM Specialist set one practitioner's end date to 9/10 and another's to 9/18,
**When** the history is loaded,
**Then** the first reads "Practitioner … removed, effective 9/10/2026",
**And** the second reads "Practitioner … scheduled for removal, effective 9/18/2026".

**AC-4 — Changed references show names, not record Ids**

**Given** a location network's Case Manager was changed from one Case Manager to another,
**When** the history is loaded,
**Then** the change shows the old and new Case Manager numbers (e.g. "IA-0000033655"),
**And** it never shows raw record Ids,
**And** it appears once, not twice.

**AC-5 — Each change shows the Case Manager and FHNatic case in effect at the time**

**Given** a practitioner link was added under Case Manager A and later moved to Case Manager B,
**When** the history is loaded,
**Then** the "added" change shows Case Manager A and A's FHNatic case number,
**And** changes made after the move show Case Manager B and B's FHNatic case number.

**AC-6 — Every change shows the record's effective-from date, on the correct day**

**Given** a practitioner link's effective-from date is 2/14/2021,
**When** the history is loaded by a user in any US time zone,
**Then** every change for that link shows "Effective from Feb 14, 2021", not the day before,
**And** removals also show their end date.

**AC-7 — Changes saved together are grouped as one change**

**Given** a PDM Specialist end-dated 14 records in one submission under one Case Manager,
**When** the history is loaded,
**Then** those 14 changes are marked as one change,
**And** changes by a different person, under a different Case Manager, or more than a minute apart are separate changes.

**AC-8 — Integration accounts are identified**

**Given** changes were made by the MuleSoft Integration User and by a PDM Specialist,
**When** the history is loaded,
**Then** the MuleSoft changes are flagged "Integration",
**And** the PDM Specialist's changes are not.

**AC-9 — Users who can't see FHNatic case numbers still see the history**

**Given** a Network Management QC Specialist has no access to the FHNatic case number,
**When** they open a practice location's history,
**Then** the history loads normally with Case Manager numbers,
**And** no FHNatic case number is shown.

**AC-10 — Very large categories are capped and flagged**

**Given** a practice location has more than 2,000 records in one category,
**When** the history is loaded,
**Then** changes for the 2,000 most recent records in that category are shown,
**And** the category is flagged as "showing the most recent records only".

**AC-11 — Nothing is revealed for a location the user can't see**

**Given** a user opens the component with a record they have no access to, or a record that isn't a practice location,
**When** the history is requested,
**Then** an empty history is returned,
**And** no record names or changes are revealed.

**AC-12 — An unexpected failure shows a clear message and is logged**

**Given** the history can't be built because of an unexpected error,
**When** a PDM Specialist opens the history,
**Then** they see "Unable to load change history" with the reason,
**And** an exception log record is created for support.

**AC-13 — Exception log record created on failure (Pattern E)**

**Given** AC-12's failure occurs,
**When** the history request fails,
**Then** the following record is created exactly as specified:

**Exception Log — Create**

| Field | Value | Notes |
|---|---|---|
| Process Name | PRM_PracticeLocationHistoryController | |
| Integration Type | SYNC | |
| Severity Level | Error | |
| Stack Trace | {exception stack trace} | truncated to 131,071 chars by the logger |
| Error Message | {exception message} | truncated to 254 chars |
| Exception Type | {exception type} | |
| Line Number | {exception line number} | 0 if blank or > 99,999 |
| Correlation ID | {Practice Location Id} | **Gap:** the POC passes "practiceLocationId: {Id}, archive: {true/false}", which the logger truncates to 31 characters. Pass the Id only. |
| Error Code | (blank) | |
| Source System | Salesforce | logger default |
| Target System | Salesforce | logger default |
| Request Payload | practiceLocationId: {Id}, archive: {true/false} | **Gap:** empty in the POC; move the context here |

**AC-14 — History loads promptly for a large group location**

**Given** a practice location with about 140 practitioners and 750+ tracked changes,
**When** a PDM Specialist opens its history,
**Then** the history is shown within 5 seconds.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PracticeLocationHistoryController` | New Apex (`with sharing`) | `getHistory(practiceLocationId)`; returns empty for null or non-`HealthcareFacility` Ids; logs via `PRM_ExceptionLogger`. **Not `cacheable`**, because the logger inserts a record. | AC-11, AC-12, AC-13 (fix Correlation ID / payload) |
| `PRM_PracticeLocationHistoryService` | New Apex | Per active category: read child records (cap = Max Records or 2000, +1 to detect a cap), **one history query per object**, build events, resolve users and Case Managers, sort, group | AC-1, AC-10, AC-14 |
| `PRM_PracticeLocationHistorySelector` (virtual) | New Apex | Dynamic SOQL in `AccessLevel.USER_MODE`; `<Object>History` (FK `<Object>Id`) vs `<Obj>__History` (FK `ParentId`); 5,000 history rows per object; Case Managers read `Name` plus `PRM_FHNaticCaseNumber__c` **only if `isAccessible()`** | AC-9, AC-11 |
| `PRM_PracticeLocationHistoryDeriver` | New Apex (pure) | Classification rules (AC-2) judged against the change date; sentence templates; lookup Id/name row collapse (value-based, because archive rows have no DataType); Case Manager at time of change; 60-second grouping; integration = config list or `UserType` in `CloudIntegrationUser` / `AutomatedProcess` | AC-2–AC-5, AC-7, AC-8 |
| `PRM_PracticeLocationHistoryModel` | New Apex | `HistoryEvent` includes `recordEffectiveFrom`, `effectiveDate`, `caseManagerName`, `fhnaticCaseNumber`, `isIntegration`, `groupKey` | AC-5, AC-6 |
| Date handling | Apex | Check `instanceof Date` **before** `Datetime`: in Apex a Date is also `instanceof Datetime`, and converting it shifts it a day west of GMT (fixed in 0.4) | AC-6 |
| Tests: `…DeriverTest` (9), `…ServiceTest` (9, stub selector), `…SelectorTest` (4) | Apex tests | Stub needed: the platform writes no field history in tests | 95.5% coverage |

---

## Definition of done

- [ ] AC-1–AC-8 verified in QA on Hospitalists Pottstown (`0klUW0000001SpbYAE`): 772 events, 187 groups, 206 with FHNatic, 730 with effective-from.
- [ ] Removed vs Scheduled removal verified (AC-3) and effective-from shows the correct day (AC-6).
- [ ] A user without FHNatic field access loads the history without error (AC-9).
- [ ] Correlation ID / payload gap fixed and verified in an exception log record (AC-13).
- [ ] ≥ 85% Apex coverage including bulk (200), empty, no-access and failure paths.
- [ ] Load under 5 s and under 30 queries for the reference location (AC-14).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Hide noisy system fields (Count of Active Practitioners, Source System Identifier)? | Needs an exclude list (US-01 Clarification Question 1) | Product |
| 2 | A reinstatement that sets a new future end date currently reads just "reinstated". Should it read "reinstated until {date}"? | Sentence template | Product |
| 3 | Is a one-minute grouping window right for PDM submissions and batch loads? | Group sizes in US-05 | BA |
| 4 | Should a "Case Manager changed" line appear as its own change, or be folded into its group? | Noise in cards | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_ExceptionLogger` | Apex (existing) | LOW | Reused; not modified |
| `PRM_CaseManagerHistoryController` | Apex (existing) | NONE | Pattern reference only. It has the same latent cacheable+logger issue (change log F8). |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Controller | Apex | M | incl. AC-13 fix |
| Service | Apex | XL | orchestration, caps, grouping inputs |
| Selector | Apex | L | dynamic SOQL, USER_MODE, FLS-aware Case Manager read |
| Deriver (rules) | Apex | XL | AC-2 rule table, lookup collapse, Case Manager at time |
| Tests (3 classes) | Apex tests | XL | stub selector |

**Total Estimated Effort:** XXL (about 5–6 days)
