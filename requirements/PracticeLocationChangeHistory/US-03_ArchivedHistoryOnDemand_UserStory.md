# USER STORY 03: Load Older (Archived) Changes on Demand

**Persona:** PDM Specialist (secondary: Network Management QC Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [US-02](US-02_HistoryServiceAndChangeRules_UserStory.md) · [Design prompt](../PracticeLocation_ChangeHistory_LWC_DesignPrompt.md) §8.5 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) 0.2 · Decision D2 (Field Audit Trail licensed)
**Build status:** ✅ Built in POC (QA) v0.2 · Remaining gap: retention policies unconfirmed (Clarification Question 1)

---

## Story

**As a** PDM Specialist,
**I want** to pull older changes into a practice location's history when I need them,
**So that** I can trace a directory or claims issue back to a change made more than 18 months ago, without slowing down the everyday view.

**Why it matters:** IBX licenses Field Audit Trail, so changes are retained well beyond standard field history. The archive is a separate store with its own query rules. Loading it on demand keeps the first view fast.

---

## Acceptance Criteria

**AC-1 — Older changes are merged into the current view**

**Given** a PDM Specialist is viewing a practice location's history,
**When** they click "Load older changes (archive)",
**Then** archived changes appear in date order alongside the recent ones,
**And** archived changes are tagged "Archived",
**And** the button is no longer shown.

**AC-2 — No change appears twice**

**Given** some changes exist both in recent history and in the archive,
**When** the archive is loaded,
**Then** each change appears exactly once,
**And** the recent copy is kept.

**AC-3 — Archived changes read the same as recent ones**

**Given** a "Pending cleared" change on a provider feature exists only in the archive,
**When** the archive is loaded,
**Then** it reads "Provider feature …: pending cleared", with the same wording, labels and change type as a recent change,
**And** it never shows technical field names.

**AC-4 — The user is told when the archive adds nothing**

**Given** every archived change for the location is already shown,
**When** the PDM Specialist loads the archive,
**Then** a message says "The archive has no additional changes for this location",
**And** the view is unchanged.

**AC-5 — An archive failure doesn't break the page**

**Given** the archive can't be read,
**When** the PDM Specialist clicks "Load older changes (archive)",
**Then** an error message says "Could not load archived history" with the reason,
**And** the recent history stays on screen.

**AC-6 — Refresh starts again from recent history**

**Given** the archive has been loaded,
**When** the PDM Specialist clicks Refresh,
**Then** only recent history is shown,
**And** "Load older changes (archive)" is offered again.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PracticeLocationHistoryController.getArchivedHistory` | Apex | Same service with `fromArchive = true` | AC-1 |
| `PRM_PracticeLocationHistorySelector.selectArchivedHistory` | Apex | `FieldHistoryArchive WHERE FieldHistoryType = :object AND ParentId IN :ids` in USER_MODE (index order; no ORDER BY, so sort in Apex); 5,000 rows per object | AC-1 |
| `…Selector.toArchivedRow` | Apex | Takes a field map (big-object rows can't be built in tests) and **strips the object prefix** from custom field names (`HealthcarePractitionerFacility.PRM_Pending__c` → `PRM_Pending__c`), fixed in 0.2 | AC-3 |
| `PRM_PracticeLocationHistoryDeriver.mergeRows` | Apex | De-duplicates on `HistoryId` (equal to the live history row Id; verified 326/326); live wins | AC-2 |
| `prmPracticeLocationHistory.handleLoadArchive` | LWC | Merges by event id, shows a toast when nothing was added, and hides the button once loaded | AC-1, AC-4–AC-6 |

---

## Definition of done

- [ ] Archive load merges and removes duplicates on the reference location (AC-1, AC-2).
- [ ] Archived Pending / Error / Active changes are classified the same as live ones (AC-3).
- [ ] The "no additional changes" message is shown when the archive only duplicates live history (AC-4).
- [ ] An archive error leaves the recent view intact (AC-5).
- [ ] Retention policy per object confirmed (Clarification Question 1).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which objects have a Field Audit Trail **retention policy** set, and after how long do rows leave live history? | Until rows are archived, the button returns only duplicates | Salesforce Admin |
| 2 | Should the archive load **automatically** when the date filter is "All time"? | UX in US-06 | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Archive selector + prefix normalisation | Apex | L | |
| Controller method + tests | Apex | M | |
| LWC archive load and merge | LWC | M | |

**Total Estimated Effort:** L–XL (about 1.5 days)
